"""Representation (docs/ir.md §8.3): inserts `convert` wherever a value's representation differs from the one its use
requires.

A value's representation is its type's C representation (codegen/c_types.py): a type parameter's values are held as
QVal words, and other types natively. A use requires the representation of the type it expects: a call's argument,
its callee's parameter type (in a polymorphic callee, mentioning the callee's type parameters, so a QVal where the
parameter is one); a call's result, its callee's result type; a let's copy, a return, a jump's argument, and a store,
the type of what they bind or store into. Where the two differ, the value is converted by the plan of the pair
(`plan`).

Built a slice at a time with the C printer (docs/ir.md §12, step 5): the plans so far box and unbox between QVal
and a scalar or pointer; any other change of representation is reported as not yet supported, rather than printed
wrong.
"""

from __future__ import annotations

from typing import Optional

from quest.codegen.c_types import RecordNamingContext, collect_fun_quantifiers, normalize_type, qtype_to_c_type
from quest.ir import nodes as ir
from quest.ir.walk import statement_bodies
from quest.types import (
    OK_TYPE,
    QAllType,
    QFunType,
    QOptionType,
    QRecordType,
    QTupleType,
    QType,
    QVariantType,
    is_type_equal,
    resolve_option_bound,
    resolve_record_bound,
    resolve_variant_bound,
)


class UnsupportedConversion(Exception):
    """A change of representation the represent pass does not handle yet (a later slice's)."""


_CTX = RecordNamingContext()


def c_type(t: QType) -> str:
    return qtype_to_c_type(t, _CTX)


def _may_be_stored_as_subtype(t: QType) -> bool:
    """Whether a value of type t may be laid out as a subtype of t, and so need converting when used at t."""
    t = normalize_type(t)
    if isinstance(t, QTupleType):
        return bool(t.value_fields)
    return (
        isinstance(t, (QRecordType, QVariantType, QOptionType, QFunType, QAllType))
        or resolve_record_bound(t) is not None
        or resolve_variant_bound(t) is not None
        or resolve_option_bound(t) is not None
    )


def plan(source: QType, target: QType) -> Optional[ir.Plan]:
    """How a value of type source is converted to be used at type target (None when it is used as it is)."""
    if source is target or source is OK_TYPE or target is OK_TYPE:
        return None
    cs, ct = c_type(source), c_type(target)
    if cs == ct:
        if not _may_be_stored_as_subtype(target) or is_type_equal(source, target):
            return None
        raise UnsupportedConversion(f"converting a value of type {source} to {target} (as {ct})")
    # A value of a type parameter, held as a QVal word: a scalar or pointer in its bits, a record or variant boxed
    if ct == "QVal":
        return ir.Plan("box", source, target)
    if cs == "QVal":
        return ir.Plan("unbox", source, target)
    raise UnsupportedConversion(f"converting a value of type {source} ({cs}) to {target} ({ct})")


def fun_signature(t: QType) -> tuple[tuple, QType]:
    """The parameters and result type of a (possibly polymorphic) function type, its type parameters' symbols
    standing for themselves."""
    _, inner = collect_fun_quantifiers(t)
    if isinstance(inner, QFunType):
        return tuple(inner.params), inner.result_type
    return (), inner


class _Representer:
    def __init__(self, unit: ir.Unit) -> None:
        self.unit = unit
        self.joins: dict[str, tuple[ir.Var, ...]] = {}

    def convert(self, a: ir.Atom, target: QType, before: list) -> ir.Atom:
        """a, converted to be used at target (by a let added to before), or a itself."""
        source = a.type if isinstance(a, ir.Var) else a.shape.type
        p = plan(source, target)
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

    def statement(self, s, function: Optional[ir.Function]) -> list:
        """The statements s becomes: conversions of its operands, s, and a conversion of its result."""
        before: list = []
        after: list = []
        match s:
            case ir.Let(var=var, value=ir.Var() | ir.Const() as a):
                s.value = self.convert(a, var.type, before)
            case ir.Let(var=var, value=ir.Call() as call):
                result_t = self.call(call, before)
                p = plan(result_t, var.type)
                if p is not None:
                    result = ir.Var(var.hint, result_t)
                    after.append(ir.Let(var, ir.Convert(result, p)))
                    s.var = result
            case ir.Do(value=ir.Call() as call):
                self.call(call, before)
            case ir.VarDecl(var=var, init=init):
                s.init = self.convert(init, var.type, before)
            case ir.Assign(var=var, value=value):
                s.value = self.convert(value, var.type, before)
            case ir.Return(value=value) if function is not None:
                s.value = self.convert(value, function.result_type, before)
            case ir.Jump(label=label, args=args):
                params = self.joins[label]
                s.args = tuple(self.convert(a, p.type, before) for a, p in zip(args, params))
        return before + [s] + after

    def call(self, call: ir.Call, before: list) -> QType:
        """Converts a call's arguments to its callee's parameter types, returning its callee's result type."""
        callee_t = call.callee.type if call.callee is not None else call.callee_type
        if callee_t is None:
            raise UnsupportedConversion(f"a call of {call.member} whose type is unknown")
        params, result_t = fun_signature(callee_t)
        args = []
        for i, a in enumerate(call.args):
            if i < len(params) and not (params[i].is_var or params[i].is_out):
                a = self.convert(a, params[i].type_val, before)
            args.append(a)
        call.args = tuple(args)
        return result_t

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
