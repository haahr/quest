"""Representation (docs/ir.md §8.3): inserts `convert` wherever a value's representation differs from the one its use
requires.

A value's representation is its type's C representation (codegen/c_types.py): a type parameter's values are held as
QVal words (a bounded one's viewed at its bound), and other types natively. A use requires the representation of the
type it expects: a call's argument, its callee's parameter type (in a polymorphic callee, mentioning the callee's
type parameters, so a QVal where the parameter is one); a call's result, its callee's result type; a component of a
tuple, record, variant, option, or array being made or stored into, the component's type; a component read, as its
aggregate's type gives it; a let's copy, a return, a jump's argument, and an assignment, the type of what they bind
or assign. Where the two differ, the value is converted by the plan of the pair (`plan`).

Built a slice at a time with the C printer (docs/ir.md §12, step 5): the plans so far box and unbox between QVal and
native values, view records at supertypes, remap variants' tags, and cast or copy tuples whose components convert;
any other change of representation is reported as not yet supported, rather than printed wrong.
"""

from __future__ import annotations

from typing import Optional

from quest.codegen.c_types import RecordNamingContext, collect_fun_quantifiers, normalize_type, qtype_to_c_type
from quest.ir import nodes as ir
from quest.ir.walk import statement_bodies
from quest.types import (
    OK_TYPE,
    QAllType,
    QArrayType,
    QExceptionType,
    QFunType,
    QOptionType,
    QOutType,
    QRecordType,
    QTupleType,
    QType,
    QVariantType,
    QVarType,
    is_type_equal,
    resolve_option_bound,
    resolve_record_bound,
    resolve_variant_bound,
    strip_aliases,
)


class UnsupportedConversion(Exception):
    """A change of representation the represent pass does not handle yet (a later slice's)."""


_CTX = RecordNamingContext()


def c_type(t: QType) -> str:
    return qtype_to_c_type(t, _CTX)


def _held(t: QType, kind, resolve) -> Optional[QType]:
    """t as a type of the kind (QRecordType, ...), or the bound a type parameter of t's type is held viewed at."""
    n = normalize_type(t)
    if isinstance(n, kind):
        return n
    bound = resolve(n)
    return normalize_type(bound) if bound is not None else None


def record_type(t: QType) -> Optional[QRecordType]:
    return _held(t, QRecordType, resolve_record_bound)


def variant_type(t: QType) -> Optional[QVariantType]:
    return _held(t, QVariantType, resolve_variant_bound)


def option_type(t: QType) -> Optional[QOptionType]:
    return _held(t, QOptionType, resolve_option_bound)


def tuple_type(t: QType) -> Optional[QTupleType]:
    n = normalize_type(t)
    return n if isinstance(n, QTupleType) else None


def array_element(t: QType) -> QType:
    n = normalize_type(t)
    if not isinstance(n, QArrayType):
        raise UnsupportedConversion(f"an array operation on a value of type {t}")
    return n.element_type


def _may_be_stored_as_subtype(t: QType) -> bool:
    """Whether a value of type t may be laid out as a subtype of t, and so need converting when read as t (records,
    variants, options, nonempty tuples, and functions)."""
    t = normalize_type(t)
    if isinstance(t, QTupleType):
        return bool(t.value_fields)
    return (
        isinstance(t, (QRecordType, QVariantType, QOptionType, QFunType, QAllType))
        or resolve_record_bound(t) is not None
        or resolve_variant_bound(t) is not None
        or resolve_option_bound(t) is not None
    )


def _equal(a: QType, b: QType) -> bool:
    return a is b or is_type_equal(a, b)


def plan(source: QType, target: QType) -> Optional[ir.Plan]:
    """How a value of type source is converted to be used at type target (None when it is used as it is)."""
    if source is target or strip_aliases(source) is OK_TYPE or strip_aliases(target) is OK_TYPE:
        return None
    cs, ct = c_type(source), c_type(target)
    # A value of a type parameter, held as a QVal word: a scalar or pointer in its bits, a record or variant boxed
    if ct == "QVal" and cs != "QVal":
        return ir.Plan("box", source, target)
    if cs == "QVal" and ct != "QVal":
        return ir.Plan("unbox", source, target)
    if cs == "QVal" or _equal(source, target):
        return None
    if (t_rec := record_type(target)) is not None and (s_rec := record_type(source)) is not None:
        return None if _equal(s_rec, t_rec) else ir.Plan("record_view", source, target)
    if (t_var := variant_type(target)) is not None and (s_var := variant_type(source)) is not None:
        index = {case.name: i for i, case in enumerate(t_var.variants)}
        if all(index.get(case.name) == i for i, case in enumerate(s_var.variants)):
            return None
        return ir.Plan("variant_tags", source, target)
    if (t_tup := tuple_type(target)) is not None and (s_tup := tuple_type(source)) is not None:
        if len(s_tup.value_fields) < len(t_tup.value_fields):
            raise UnsupportedConversion(f"converting a tuple of type {source} to {target}")
        pairs = list(zip(s_tup.value_fields, t_tup.value_fields))
        fields = tuple(plan(sf.type_val, tf.type_val) for sf, tf in pairs)
        if all(p is None for p in fields) and all(c_type(sf.type_val) == c_type(tf.type_val) for sf, tf in pairs):
            return None if cs == ct else ir.Plan("cast", source, target)
        return ir.Plan("copy", source, target, fields)
    if cs == ct and not isinstance(normalize_type(target), (QFunType, QAllType, QOptionType, QArrayType)):
        return None
    raise UnsupportedConversion(f"converting a value of type {source} ({cs}) to {target} ({ct})")


def fun_signature(t: QType) -> tuple[tuple, QType]:
    """The parameters and result type of a (possibly polymorphic) function type, its type parameters' symbols
    standing for themselves."""
    _, inner = collect_fun_quantifiers(t)
    if isinstance(inner, QFunType):
        return tuple(inner.params), inner.result_type
    return (), inner


def _type_of(a: ir.Atom) -> QType:
    return a.type if isinstance(a, ir.Var) else a.shape.type


class _Representer:
    def __init__(self, unit: ir.Unit) -> None:
        self.unit = unit
        self.joins: dict[str, tuple[ir.Var, ...]] = {}
        self.generic_results: list[tuple[QType, QType]] = []

    def convert(self, a: ir.Atom, target: QType, before: list) -> ir.Atom:
        """a, converted to be used at target (by a let added to before), or a itself."""
        p = plan(_type_of(a), target)
        if p is None:
            return a
        converted = ir.Var(a.hint if isinstance(a, ir.Var) else "", target)
        before.append(ir.Let(converted, ir.Convert(a, p)))
        return converted

    def body(self, body: ir.Body, function: Optional[ir.Function]) -> None:
        statements = []
        for s in body.statements:
            if isinstance(s, ir.Join):
                self.joins[s.label] = s.params
            for b in statement_bodies(s):
                self.body(b, function)
            statements.extend(self.statement(s, function))
        body.statements = statements

    def result(self, s: ir.Let, result_t: QType, after: list) -> None:
        """Converts the result of s's operation, of type result_t, to s's variable's type."""
        p = plan(result_t, s.var.type)
        if p is not None:
            result = ir.Var(s.var.hint, result_t)
            after.append(ir.Let(s.var, ir.Convert(result, p)))
            s.var = result

    def statement(self, s, function: Optional[ir.Function]) -> list:
        """The statements s becomes: conversions of its operands, s, and a conversion of its result."""
        before: list = []
        after: list = []
        match s:
            case ir.Let(var=var, value=ir.Var() | ir.Const() as a):
                s.value = self.convert(a, var.type, before)
            case ir.Let(var=var, value=ir.Call() as call):
                writebacks: list = []
                self.generic_results = []
                result_t = self.call(call, before, writebacks)
                if self.generic_results:
                    # The callee's generic result, converted to its type at the type arguments, then to the let's
                    generic_t, instantiated_t = self.generic_results[0]
                    step = plan(generic_t, instantiated_t)
                    if step is not None:
                        instantiated = ir.Var(var.hint, instantiated_t)
                        generic = ir.Var(var.hint, generic_t)
                        after.append(ir.Let(instantiated, ir.Convert(generic, step)))
                        s.var = generic
                        final = plan(instantiated_t, var.type)
                        if final is None:
                            after.append(ir.Let(var, instantiated))
                        else:
                            after.append(ir.Let(var, ir.Convert(instantiated, final)))
                    else:
                        self.result(s, result_t, after)
                else:
                    self.result(s, result_t, after)
                after.extend(writebacks)
            case ir.Do(value=ir.Call() as call):
                self.call(call, before, after)
            case ir.Let(var=var, value=value):
                result_t = self.operation(value, var.type, before)
                if result_t is not None:
                    self.result(s, result_t, after)
            case ir.VarDecl(var=var, init=init):
                s.init = self.convert(init, var.type, before)
            case ir.Assign(var=var, value=value):
                s.value = self.convert(value, var.type, before)
            case ir.Store():
                target_t = self.stored_type(s)
                if target_t is not None:
                    s.value = self.convert(s.value, target_t, before)
            case ir.Return(value=value) if function is not None:
                s.value = self.convert(value, function.result_type, before)
            case ir.Jump(label=label, args=args):
                params = self.joins[label]
                s.args = tuple(self.convert(a, p.type, before) for a, p in zip(args, params))
            case ir.Raise(exception=e, payload=p) if p is not None:
                exc_t = normalize_type(_type_of(e))
                if isinstance(exc_t, QExceptionType) and exc_t.payload_type is not None:
                    s.payload = self.convert(p, exc_t.payload_type, before)
        return before + [s] + after

    def operation(self, o, result_t: QType, before: list) -> Optional[QType]:
        """Converts an operation's operands to the types it stores them at, returning the type of its result as the
        operation gives it (None when that is the let's own)."""
        match o:
            case ir.MakeTuple(args=args):
                t = tuple_type(result_t)
                if t is not None:
                    o.args = tuple(self.convert(a, f.type_val, before) for a, f in zip(args, t.value_fields))
            case ir.MakeVariant(tag=tag, payload=payload) if payload is not None:
                t = variant_type(result_t)
                case = t.get_variant(tag) if t is not None else None
                if case is not None and case.type_val is not None:
                    o.payload = self.convert(payload, case.type_val, before)
            case ir.MakeOption(tag=tag, payload=payload) if payload is not None and tag is not None:
                t = option_type(result_t)
                case = t.get_option(tag) if t is not None else None
                if case is not None and case.payload_type is not None:
                    o.payload = self.convert(payload, case.payload_type, before)
            case ir.MakeArray(args=args):
                elem = array_element(result_t)
                o.args = tuple(self.convert(a, elem, before) for a in args)
            case ir.ArrayRep(init=init):
                o.init = self.convert(init, array_element(result_t), before)
            case ir.TupleField(tuple=t, index=index):
                tt = tuple_type(_type_of(t))
                return tt.value_fields[index].type_val if tt is not None else None
            case ir.RecordField(record=r, name=name):
                rt = record_type(_type_of(r))
                field = next((f for f in rt.fields if f.name == name), None) if rt is not None else None
                return field.type_val if field is not None else None
            case ir.Index(array=a):
                return array_element(_type_of(a))
            case ir.ModuleMember(module=ir.Module() as m, member=member) if member is not None:
                return m.members[member].type
            case ir.Payload(value=v, tag=tag):
                vt = variant_type(_type_of(v))
                if vt is not None:
                    case = vt.get_variant(tag)
                    return case.type_val if case is not None and case.type_val is not None else None
        return None

    def stored_type(self, s: ir.Store) -> Optional[QType]:
        """The type of the location a store stores into."""
        if s.address is not None:
            return None
        base_t = _type_of(s.base)
        if s.name is not None:
            rt = record_type(base_t)
            field = next((f for f in rt.fields if f.name == s.name), None) if rt is not None else None
            return field.type_val if field is not None else None
        if isinstance(s.index, int):
            tt = tuple_type(base_t)
            return tt.value_fields[s.index].type_val if tt is not None else None
        return array_element(base_t)

    def call(self, call: ir.Call, before: list, after: list) -> QType:
        """Converts a call's arguments to its callee's parameter types, returning its callee's result type. An out
        argument whose location's type is a supertype of the parameter's, laid out differently, is a temporary of the
        parameter's type, converted into the location after the call (added to after)."""
        if call.callee is not None:
            callee_t = call.callee.type
        elif isinstance(call.module, ir.Module):
            # A member of one of the unit's modules, called from outside it at its interface's types (abstract
            # types among them), works at the module's own: its arguments and result convert at the boundary
            callee_t = call.module.members[call.member].type
        else:
            callee_t = call.callee_type
        if callee_t is None:
            raise UnsupportedConversion(f"a call of {call.member} whose type is unknown")
        params, result_t = fun_signature(callee_t)
        # A polymorphic callee's parameters at the call's type arguments: an argument is converted to its parameter's
        # type there (a record viewed at the type argument), then to the parameter's generic representation
        quants, _ = collect_fun_quantifiers(callee_t)
        instantiation = {q.symbol_id: t for q, t in zip(quants, call.type_args)}
        args = []
        for i, a in enumerate(call.args):
            if i < len(params) and params[i].is_out:
                a = self.out_argument(a, params[i].type_val, before, after)
            elif i < len(params) and not params[i].is_var:
                if instantiation:
                    a = self.convert(a, params[i].type_val.substitute(instantiation), before)
                a = self.convert(a, params[i].type_val, before)
            args.append(a)
        call.args = tuple(args)
        if instantiation:
            self.generic_results.append((result_t, result_t.substitute(instantiation)))
        return result_t

    def out_argument(self, address: ir.Atom, param_t: QType, before: list, after: list) -> ir.Atom:
        location_t = _type_of(address)
        if isinstance(location_t, (QVarType, QOutType)):
            location_t = location_t.element_type
        p = plan(param_t, location_t)
        if p is None:
            return address
        temp = ir.Var("out", param_t, mutable=True)
        temp_address = ir.Var("", _type_of(address))
        before.append(ir.VarDecl(temp, None))
        before.append(ir.Let(temp_address, ir.Addr(var=temp)))
        written = ir.Var("", param_t)
        converted = ir.Var("", location_t)
        after.append(ir.Let(written, temp))
        after.append(ir.Let(converted, ir.Convert(written, p)))
        after.append(ir.Store(converted, address=address))
        return temp_address

    def run(self) -> None:
        for m in self.unit.modules:
            self.body(m.init, None)
        self.body(self.unit.main, None)
        for f in self.unit.functions:
            self.body(f.body, f)


def represent_unit(unit: ir.Unit) -> ir.Unit:
    """Inserts the unit's conversions, in place, returning it."""
    _Representer(unit).run()
    unit.stage = "represented"
    return unit
