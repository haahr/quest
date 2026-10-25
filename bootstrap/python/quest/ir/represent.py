"""Representation (docs/ir.md §8.3): inserts `convert` wherever a value's representation differs from the one its use
requires.

A value's representation is its type's (codegen/layout.py: the runtime's, shared by every backend): a type
parameter's values are held as QVal words (a bounded one's viewed at its bound), and other types natively. A use
requires the representation of the type it expects: a call's argument, its callee's parameter type (in a polymorphic
callee, mentioning the callee's type parameters, so a QVal where the parameter is one); a call's result, its callee's
result type; a component of a tuple, record, variant, option, or array being made or stored into, the component's
type; a component read, as its aggregate's type gives it; a let's copy, a return, a jump's argument, and an
assignment, the type of what they bind or assign. Where the two differ, the value is converted by the plan of the
pair (`plan`).

The plans box and unbox between QVal and native values, view records at supertypes, remap variants' tags, cast or
copy aggregates whose components convert, adapt closures, and convert by descriptor at run time; any other change of
representation is reported as unsupported, rather than printed wrong.

Every decision is made on shapes (ir/shapes.py). The variables the pass makes have types as written, with their alias
names, which the IR prints (docs/ir.md §5): the types of the components of a type as written (written_structure), and
the signatures of function types as written, whose type parameters' symbols are those the call's type arguments and
the callee's parts refer to (a shape's are its canonical form's, named afresh).
"""

from __future__ import annotations

from typing import Optional

from quest.codegen.layout import (
    generic_layout_agrees,
    is_boxed_in_slots,
    generic_layout_copies_mutable_data,
    resolved_shape,
    shape_representation,
    shape_slot_representation,
    signature_representation,
)
from quest.ir import nodes as ir
from quest.ir.shapes import Shape, shape
from quest.ir.walk import statement_bodies
from quest.types.canonical import collect_fun_quantifiers, normalize_type, resolve_type_bound
from quest.types import (
    QAbstractType,
    QFunType,
    QOutType,
    QType,
    QTypeVar,
    QVarType,
    auto_payload_type,
    is_type_equal,
)


class UnsupportedConversion(Exception):
    """A change of representation the represent pass does not handle."""


# The kinds of shapes whose values a type parameter bounded by one holds viewed at its bound
_VIEWED_KINDS = ("record", "variant", "option")


def held_shape(t: QType, kind: str) -> Optional[Shape]:
    """The shape of t's values as they are held, if it is of the kind ("record", "variant", or "option"): t's own, or
    for a type parameter bounded by a type of the kind, its bound's, at which it is viewed."""
    held = resolved_shape(shape(t))
    return held if held.kind == kind else None


def written_structure(t: QType, kind: str) -> Optional[QType]:
    """t as written with its outermost constructor exposed, if t's shape is of the kind ("tuple", "array",
    "exception", or one of the kinds a type parameter is viewed at its bound at, for which it is the bound): None
    otherwise. The types of its components, with their alias names, are the types of the variables the pass makes for
    them, which the IR prints; a shape's components have only their canonical types."""
    s = shape(t)
    held = resolved_shape(s) if kind in _VIEWED_KINDS else s
    if held.kind != kind:
        return None
    return normalize_type(resolve_type_bound(t) if held is not s else t)


def array_element(t: QType) -> QType:
    """The element type, as written, of an array type."""
    written = written_structure(t, "array")
    if written is None:
        raise UnsupportedConversion(f"an array operation on a value of type {t}")
    return written.element_type


def may_be_stored_as_subtype(s: Shape) -> bool:
    """Whether a value of shape s may be laid out as a subtype's value, and so need converting when read at s's type
    (records, variants, options, nonempty tuples, and functions)."""
    if s.kind == "tuple":
        return bool(s.components)
    return s.kind in ("fun", "all") or resolved_shape(s).kind in _VIEWED_KINDS


def _bounded_view(s: Shape) -> bool:
    """Whether s is a type parameter's bounded by a record, variant, or option type, held viewed at its bound."""
    return s.kind not in _VIEWED_KINDS and resolved_shape(s).kind in _VIEWED_KINDS


def _equal(a: QType, b: QType) -> bool:
    return a is b or is_type_equal(a, b)


def _variant_subtype(s: Shape, t: Shape) -> bool:
    """Whether every case of the variant shape s is a case of t, with an equal payload."""
    payloads = {c.name: c.shape for c in t.cases}
    for c in s.cases:
        if c.name not in payloads:
            return False
        other = payloads[c.name]
        if c.shape is not other and (c.shape is None or other is None or not is_type_equal(c.shape.type, other.type)):
            return False
    return True


class RejectedConversion(Exception):
    """A conversion that would copy mutable data laid out differently, which would then not share its updates: a
    compile-time error (docs/c-representation.md §5.1, Polymorphic Calls)."""


def layout_plan(source: QType, target: QType, layout: tuple[dict[int, QType], bool]) -> Optional[ir.Plan]:
    """How a value passed to or returned from a polymorphic callee converts between the callee's generic layout of
    its type and the native layout at the call's type arguments (layout: the instantiation, and whether the value goes
    to the generic layout, target being the callee's type, or comes from it, source being)."""
    instantiation, to_generic = layout
    generic_t = target if to_generic else source
    native_t = generic_t.substitute(instantiation)
    generic_s, native_s = shape(generic_t), shape(native_t)
    generic_c, native_c = shape_representation(generic_s), shape_representation(native_s)
    if generic_s.kind in ("fun", "all"):
        return None
    is_record = generic_c == native_c == "QRecordVal"
    if not is_record and (not generic_c.endswith("*") or not native_c.endswith("*")):
        return None
    if generic_layout_agrees(generic_t, instantiation):
        return None if generic_c == native_c else ir.Plan("cast", source, target)
    if generic_layout_copies_mutable_data(generic_t, instantiation):
        raise RejectedConversion(
            f"C code generation cannot pass a value of type '{native_t}' to or from a polymorphic function that lays "
            f"it out as '{generic_t}': the layouts differ, and converting the value would copy mutable data, which "
            f"would then not share its updates"
        )
    return ir.Plan("runtime", source, target, layout=layout)


def shared_signatures(source: QType, target: QType) -> tuple[tuple, QType, tuple, QType]:
    """Two (possibly polymorphic) function types' parameters and results as written, target's type parameters renamed
    to source's, so that they can be compared."""
    s_quants, s_inner = collect_fun_quantifiers(source)
    t_quants, t_inner = collect_fun_quantifiers(target)
    if s_quants and len(s_quants) == len(t_quants):
        t_inner = t_inner.substitute({
            tq.symbol_id: QTypeVar(name=sq.name, symbol_id=sq.symbol_id, bound=sq.bound)
            for sq, tq in zip(s_quants, t_quants)
        })
    s_params = s_inner.params if isinstance(s_inner, QFunType) else ()
    t_params = t_inner.params if isinstance(t_inner, QFunType) else ()
    s_result = s_inner.result_type if isinstance(s_inner, QFunType) else s_inner
    t_result = t_inner.result_type if isinstance(t_inner, QFunType) else t_inner
    return tuple(s_params), s_result, tuple(t_params), t_result


_ADAPTING: set[tuple] = set()


def adapt_plan(source: QType, target: QType, layout) -> Optional[ir.Plan]:
    """How a closure of type source is used at type target: as it is, when the C signatures agree and no argument or
    result converts, or else wrapped in a thunk of target's signature (`adapt`), which converts each argument from
    target's parameter type to source's (the other way from the closure) and the result from source's to target's,
    by the plans in `fields` (the parameters', then the result's)."""
    if _equal(source, target) and not (layout is not None and layout[0]):
        return None
    # Recursive function types are compared coinductively: a pair being compared needs no conversion of its own
    key = (id(shape(source)), id(shape(target)), layout is not None and layout[1])
    if key in _ADAPTING:
        return None
    s_params, s_result, t_params, t_result = shared_signatures(source, target)
    if len(s_params) != len(t_params):
        raise UnsupportedConversion(f"converting a function of type {source} to {target}")
    flipped = (layout[0], not layout[1]) if layout is not None else None
    _ADAPTING.add(key)
    try:
        fields = tuple(
            None if tp.is_var or tp.is_out else plan(tp.type_val, sp.type_val, flipped)
            for sp, tp in zip(s_params, t_params)
        ) + (plan(s_result, t_result, layout),)
    finally:
        _ADAPTING.discard(key)
    if all(p is None for p in fields) and signature_representation(source) == signature_representation(target):
        return None
    return ir.Plan("adapt", source, target, fields, layout)


def plan(source: QType, target: QType, layout: Optional[tuple[dict[int, QType], bool]] = None) -> Optional[ir.Plan]:
    """How a value of type source is converted to be used at type target (None when it is used as it is). layout is
    set for a value passed to or returned from a polymorphic callee (see layout_plan)."""
    if source is target:
        return None
    ss, ts = shape(source), shape(target)
    if ss.kind == "ok" or ts.kind == "ok":
        return None
    cs, ct = shape_representation(ss), shape_representation(ts)
    if cs != "QVal" and ct != "QVal" and ss.kind in ("fun", "all") and ts.kind in ("fun", "all"):
        return adapt_plan(source, target, layout)
    if layout is not None and layout[0] and cs != "QVal" and ct != "QVal":
        lp = layout_plan(source, target, layout)
        # A value of a bounded type parameter is held viewed at its bound, whatever the layouts: a record or variant
        # of another type converts to the bound's view (and back), as below
        if lp is not None or not (_bounded_view(ss) or _bounded_view(ts)):
            return lp
    # A value of a type parameter, held as a QVal word: a scalar or pointer in its bits, a record or variant boxed
    if ct == "QVal" and cs != "QVal":
        return ir.Plan("box", source, target)
    if cs == "QVal" and ct != "QVal":
        return ir.Plan("unbox", source, target)
    if cs == "QVal" or _equal(source, target):
        return None
    s_held, t_held = resolved_shape(ss), resolved_shape(ts)
    if s_held.kind == t_held.kind == "record":
        return None if _equal(s_held.type, t_held.type) else ir.Plan("record_view", source, target)
    if s_held.kind == t_held.kind == "variant":
        index = {case.name: i for i, case in enumerate(t_held.cases)}
        if all(index.get(case.name) == i for i, case in enumerate(s_held.cases)):
            return None
        if _variant_subtype(s_held, t_held):
            return ir.Plan("variant_tags", source, target)
        # From a bounded type parameter's view at its bound back to the type the caller holds it at: by the runtime,
        # between the two views' descriptors (no static tag map relates them)
        return ir.Plan("view", s_held.structure, t_held.structure)
    if s_held.kind == t_held.kind == "option" and (_bounded_view(ss) or _bounded_view(ts)) \
            and not _equal(s_held.type, t_held.type):
        return ir.Plan("view", s_held.structure, t_held.structure)
    if ss.kind == ts.kind == "tuple":
        if len(ss.components) < len(ts.components):
            raise UnsupportedConversion(f"converting a tuple of type {source} to {target}")
        pairs = list(zip(ss.components, ts.components))
        fields = tuple(plan(sc.shape.type, tc.shape.type) for sc, tc in pairs)
        same = all(shape_slot_representation(sc.shape) == shape_slot_representation(tc.shape) for sc, tc in pairs)
        if all(p is None for p in fields) and same:
            return None if cs == ct else ir.Plan("cast", source, target)
        return ir.Plan("copy", source, target, fields)
    if cs == ct and ts.kind not in ("fun", "all", "option", "array"):
        return None
    raise UnsupportedConversion(f"converting a value of type {source} ({cs}) to {target} ({ct})")


def is_type_variable(t: QType, symbol_id: int) -> bool:
    """Whether t is the type variable (or abstract type) of the symbol."""
    var = shape(t).type
    return isinstance(var, (QTypeVar, QAbstractType)) and var.symbol_id == symbol_id


def _slots_agree(source: Shape, target: Shape) -> bool:
    """Whether a slot of shape source holds its value as a slot of shape target does: the same slot representation,
    or a QVal word (a value's QVal form, which every slot holds)."""
    s_c, t_c = shape_slot_representation(source), shape_slot_representation(target)
    return s_c == t_c or (t_c == "QVal" and s_c != "void")


def auto_payload_plan(payload_t: QType, stored_t: QType, auto_t) -> Optional[ir.Plan]:
    """How an auto value's components are stored, in the auto type's witness-independent layout: a component of the
    type component's type keeps its own representation (a bounded parameter's value is not viewed at the bound, as
    inspect reads it by the stored type component's descriptor), in its QVal form where the layout holds a QVal,
    which its slot already holds; the others convert to their stored types."""
    source = shape(payload_t).components
    target = shape(stored_t).components
    fields = []
    for sig_f, sc, tc in zip(auto_t.signature, source, target):
        if is_type_variable(sig_f.type_val, auto_t.symbol_id) and _slots_agree(sc.shape, tc.shape):
            fields.append(None)
        else:
            fields.append(plan(sc.shape.type, tc.shape.type))
    if all(p is None for p in fields) and all(_slots_agree(sc.shape, tc.shape) for sc, tc in zip(source, target)):
        if shape_representation(shape(payload_t)) == shape_representation(shape(stored_t)):
            return None
        return ir.Plan("cast", payload_t, stored_t)
    return ir.Plan("copy", payload_t, stored_t, tuple(fields))


def fun_signature(t: QType) -> tuple[tuple, QType]:
    """The parameters and result type, as written, of a (possibly polymorphic) function type, its type parameters'
    symbols standing for themselves."""
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
        self.generic_results: list[tuple[QType, QType, dict]] = []
        # The addresses of slots holding records or variants boxed (by variable), which have no address of the
        # value's representation: a var or out argument of one is a temporary, read from and stored back into the
        # slot (slot_argument), and its let is removed
        self.slot_addresses: dict[int, tuple[ir.Let, ir.Addr]] = {}
        self.removed: set[int] = set()

    def convert(self, a: ir.Atom, target: QType, before: list, layout=None) -> ir.Atom:
        """a, converted to be used at target (by a let added to before), or a itself."""
        p = plan(_type_of(a), target, layout)
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
        body.statements = [s for s in statements if id(s) not in self.removed]

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
            case ir.Let(var=var, value=ir.Addr(base=base) as addr) if base is not None and isinstance(
                var.type, (QVarType, QOutType)
            ) and is_boxed_in_slots(shape(var.type.element_type)):
                self.slot_addresses[id(var)] = (s, addr)
            case ir.Let(var=var, value=ir.Var() | ir.Const() as a):
                s.value = self.convert(a, var.type, before)
            case ir.Let(var=var, value=ir.Call() as call):
                writebacks: list = []
                self.generic_results = []
                result_t = self.call(call, before, writebacks)
                if self.generic_results:
                    # The callee's generic result, converted to its type at the type arguments, then to the let's
                    generic_t, instantiated_t, instantiation = self.generic_results[0]
                    step = plan(generic_t, instantiated_t, (instantiation, False))
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
                        # The generic result is laid out as the native one at the type arguments
                        self.result(s, instantiated_t, after)
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
                exc_t = written_structure(_type_of(e), "exception")
                if exc_t is not None and exc_t.payload_type is not None:
                    s.payload = self.convert(p, exc_t.payload_type, before)
        return before + [s] + after

    def operation(self, o, result_t: QType, before: list) -> Optional[QType]:
        """Converts an operation's operands to the types it stores them at, returning the type of its result as the
        operation gives it (None when that is the let's own)."""
        match o:
            case ir.MakeTuple(args=args):
                t = written_structure(result_t, "tuple")
                if t is not None:
                    o.args = tuple(self.convert(a, f.type_val, before) for a, f in zip(args, t.value_fields))
            case ir.MakeVariant(tag=tag, payload=payload) if payload is not None:
                t = written_structure(result_t, "variant")
                case = t.get_variant(tag) if t is not None else None
                if case is not None and case.type_val is not None:
                    o.payload = self.convert(payload, case.type_val, before)
            case ir.MakeOption(tag=tag, payload=payload) if payload is not None and tag is not None:
                t = written_structure(result_t, "option")
                case = t.get_option(tag) if t is not None else None
                if case is not None and case.payload_type is not None:
                    o.payload = self.convert(payload, case.payload_type, before)
            case ir.MakeArray(args=args):
                elem = array_element(result_t)
                o.args = tuple(self.convert(a, elem, before) for a in args)
            case ir.ArrayRep(init=init):
                o.init = self.convert(init, array_element(result_t), before)
            case ir.MakeAuto(auto_type=auto_t, payload=payload):
                stored_t = auto_payload_type(auto_t)
                p = auto_payload_plan(_type_of(payload), stored_t, auto_t)
                if p is not None:
                    stored = ir.Var("payload", stored_t)
                    before.append(ir.Let(stored, ir.Convert(payload, p)))
                    o.payload = stored
            case ir.TupleField(tuple=t, index=index):
                tt = written_structure(_type_of(t), "tuple")
                return tt.value_fields[index].type_val if tt is not None else None
            case ir.RecordField(record=r, name=name):
                rt = written_structure(_type_of(r), "record")
                field = next((f for f in rt.fields if f.name == name), None) if rt is not None else None
                return field.type_val if field is not None else None
            case ir.Index(array=a):
                return array_element(_type_of(a))
            case ir.ModuleMember(module=ir.Module() as m, member=member) if member is not None:
                return m.members[member].type
            case ir.Payload(value=v, tag=tag):
                vt = written_structure(_type_of(v), "variant")
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
            rt = written_structure(base_t, "record")
            field = next((f for f in rt.fields if f.name == s.name), None) if rt is not None else None
            return field.type_val if field is not None else None
        if isinstance(s.index, int):
            tt = written_structure(base_t, "tuple")
            return tt.value_fields[s.index].type_val if tt is not None else None
        return array_element(base_t)

    def call(self, call: ir.Call, before: list, after: list) -> QType:
        """Converts a call's arguments to its callee's parameter types, returning its callee's result type. A var or
        out argument whose location is laid out differently from the parameter is a temporary of the parameter's
        type, converted into the location after the call (added to after)."""
        self.generic_results = []
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
            if i < len(params) and (params[i].is_out or params[i].is_var):
                a = self.ref_argument(a, params[i], instantiation, before, after)
            elif i < len(params):
                if instantiation:
                    a = self.convert(a, params[i].type_val.substitute(instantiation), before)
                a = self.convert(a, params[i].type_val, before, (instantiation, True))
            args.append(a)
        call.args = tuple(args)
        if instantiation:
            self.generic_results.append((result_t, result_t.substitute(instantiation), instantiation))
        return result_t

    def ref_argument(self, address: ir.Atom, param, instantiation: dict, before: list, after: list) -> ir.Atom:
        """The address passed for a var or out argument: the location's own, or that of a temporary of the
        parameter's representation (a shadow cell of a generic parameter's QVal, or a cell of an out parameter's type
        where the location's is a supertype laid out differently), copied in from the location (for var) and out to
        it after the call. A slot holding a record or variant boxed has no address of the record's or variant's
        representation, so its argument is always such a temporary, read from the slot and stored back into it."""
        location_t = _type_of(address)
        if isinstance(location_t, (QVarType, QOutType)):
            location_t = location_t.element_type
        param_t = param.type_val
        layout_out = (instantiation, False) if instantiation else None
        p_out = plan(param_t, location_t, layout_out)
        p_in = None if param.is_out else plan(location_t, param_t, (instantiation, True) if instantiation else None)
        slot = self.slot_addresses.get(id(address)) if isinstance(address, ir.Var) else None
        if p_out is None and p_in is None and slot is None:
            return address
        if slot is not None:
            # A slot holding a record or variant boxed: read from and stored back into the slot itself
            self.removed.add(id(slot[0]))
            addr = slot[1]
            if addr.name is not None:
                read, store = ir.RecordField(addr.base, addr.name), dict(base=addr.base, name=addr.name)
            elif isinstance(addr.index, int):
                read, store = ir.TupleField(addr.base, addr.index), dict(base=addr.base, index=addr.index)
            else:
                read = ir.Index(addr.base, addr.index, addr.offset)
                store = dict(base=addr.base, index=addr.index, offset=addr.offset)
        temp = ir.Var("cell", param_t, mutable=True)
        temp_address = ir.Var("", QOutType(element_type=param_t) if param.is_out else QVarType(element_type=param_t))
        init = None
        if not param.is_out:
            current = ir.Var("", location_t)
            before.append(ir.Let(current, read if slot is not None else ir.Load(address)))
            init = current
            if p_in is not None:
                init = ir.Var("", param_t)
                before.append(ir.Let(init, ir.Convert(current, p_in)))
        before.append(ir.VarDecl(temp, init))
        before.append(ir.Let(temp_address, ir.Addr(var=temp)))
        written = ir.Var("", param_t)
        after.append(ir.Let(written, temp))
        if p_out is not None:
            converted = ir.Var("", location_t)
            after.append(ir.Let(converted, ir.Convert(written, p_out)))
            written = converted
        after.append(ir.Store(written, **store) if slot is not None else ir.Store(written, address=address))
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
