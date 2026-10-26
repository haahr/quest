"""Specialization (docs/ir.md §8.1): clones polymorphic functions for calls
whose type arguments call for it.

A call of a function bound by a funs statement (top-level, local, or a member of
one of the unit's modules), with type arguments for all of its type parameters,
is specialized when the arguments are closed (they mention no type parameter of
the functions enclosing the call, for which the clone would have no descriptor)
and the selective trigger holds (`should_specialize`). The clone is the function
with its type parameters substituted and fresh binders, bound by the same funs
statement as the original (so that it is in scope wherever the original is, and
sees the same free variables), and the call is redirected to it. A clone of a
module's function is also a member of the module, so that calls from outside the
module can name it. Clones are specialized in turn, and specializations are
shared by function and type arguments (by symbol and type identity, never by
name).
"""

from __future__ import annotations

from typing import Any, Optional

from quest.codegen.layout import type_identity_key
from quest.ir import nodes as ir
from quest.ir.shapes import Shape, shape
from quest.ir.walk import fields_of, rebuild, statement_bodies
from quest.ir.written import is_type_operator, quantified
from quest.types import QFunType, QParam, QType

# The depth of clones made for calls in clones, beyond which calls stay generic:
# polymorphic recursion (a function of A calling itself at List(A)) would
# otherwise specialize without end, each clone calling for the next
MAX_DEPTH = 16


def holds_record_or_variant(s: Shape, seen: Optional[set[int]] = None) -> bool:
    """Whether values of shape s are, or hold (in tuples, options, arrays, and
    cells), records or variants: values that generic code holds boxed, and
    generic layouts box (a type parameter bounded by a record is viewed as its
    bound, a record)."""
    seen = seen if seen is not None else set()
    if id(s) in seen:
        return False
    seen.add(id(s))
    match s.kind:
        case "record" | "variant":
            return True
        case "typevar":
            return s.bound is not None and holds_record_or_variant(s.bound, seen)
        case "tuple":
            return any(holds_record_or_variant(c.shape, seen) for c in s.components)
        case "option":
            return any(c.shape is not None and holds_record_or_variant(c.shape, seen) for c in s.cases)
        case "array" | "cell" | "out":
            return holds_record_or_variant(s.element, seen)
    return False


def should_specialize(f: ir.Function, type_args: tuple[QType, ...]) -> bool:
    """The selective trigger (docs/c-representation.md §6.4.3): a type argument
    that is or holds a record or variant, which generic code would box; or a var
    or out parameter, or a tuple parameter or result (however its type is
    written: through an alias or a type operator's application too), over the
    function's type parameters, whose generic layout may differ from the
    caller's (a closure among its components whose C signature changes, a
    location of another representation), and so convert at every call."""
    # A type operator (the argument of a higher-kinded type parameter) is not
    # the type of values, and has no shape
    if any(not is_type_operator(t) and holds_record_or_variant(shape(t)) for t in type_args):
        return True
    ids = {tp.symbol_id for tp in f.type_params}

    def mentions(t: QType) -> bool:
        return bool(t._fv & ids)

    for var, mode in f.params:
        if mode != "value" and mentions(var.type):
            return True
        if shape(var.type).kind == "tuple" and mentions(var.type):
            return True
    return shape(f.result_type).kind == "tuple" and mentions(f.result_type)


class _Definition:
    """A function bound by a funs statement, and where: its statement, the
    module whose member it is (if any), and the type parameters of the functions
    enclosing it."""

    __slots__ = ("function", "funs", "module", "enclosing")

    def __init__(self, function: ir.Function, funs: ir.Funs, module: Optional[ir.Module],
                 enclosing: frozenset[int]) -> None:
        self.function = function
        self.funs = funs
        self.module = module
        self.enclosing = enclosing


class _Specializer:
    def __init__(self) -> None:
        self.definitions: dict[int, _Definition] = {}
        self.clones: dict[tuple[int, tuple[str, ...]], ir.Function] = {}
        self.counts: dict[int, int] = {}
        # Clones whose bodies are still to be specialized, and their depths; the
        # depth of the body being specialized
        self.pending: list[tuple[ir.Function, frozenset[int], int]] = []
        self.depth = 0

    # Finding functions

    def collect(self, body: ir.Body, module: Optional[ir.Module], enclosing: frozenset[int]) -> None:
        for s in body.statements:
            if isinstance(s, ir.Funs):
                for f in s.functions:
                    self.definitions[id(f.var)] = _Definition(f, s, module, enclosing)
                    self.collect(f.body, None, enclosing | {tp.symbol_id for tp in f.type_params})
            else:
                for b in statement_bodies(s):
                    self.collect(b, module, enclosing)

    # Specializing calls

    def body(self, body: ir.Body, enclosing: frozenset[int]) -> None:
        for s in body.statements:
            match s:
                case ir.Let(value=ir.Call() as call) | ir.Do(value=ir.Call() as call):
                    self.call(call, enclosing)
                case ir.Funs(functions=functions):
                    for f in functions:
                        self.body(f.body, enclosing | {tp.symbol_id for tp in f.type_params})
                case _:
                    for b in statement_bodies(s):
                        self.body(b, enclosing)

    def call(self, call: ir.Call, enclosing: frozenset[int]) -> None:
        if not call.type_args:
            return
        if call.callee is not None:
            definition = self.definitions.get(id(call.callee))
        elif isinstance(call.module, ir.Module):
            member = call.module.members.get(call.member)
            definition = self.definitions.get(id(member)) if member is not None else None
        else:
            # A function of another unit, whose IR this unit does not have
            return
        if definition is None:
            return
        f = definition.function
        if len(call.type_args) != len(f.type_params):
            return
        if any(t._fv & enclosing for t in call.type_args) or not should_specialize(f, call.type_args):
            return
        clone = self.clone(definition, call.type_args)
        if clone is None:
            return
        if call.callee is not None:
            call.callee = clone.var
        else:
            call.member = next(name for name, v in definition.module.members.items() if v is clone.var)
        call.type_args = ()

    def clone(self, definition: _Definition, type_args: tuple[QType, ...]) -> Optional[ir.Function]:
        f = definition.function
        key = (id(f), tuple(type_identity_key(t) for t in type_args))
        if key in self.clones:
            return self.clones[key]
        if self.depth >= MAX_DEPTH:
            return None
        n = self.counts.get(id(f), 0)
        self.counts[id(f)] = n + 1
        subst = {tp.symbol_id: t for tp, t in zip(f.type_params, type_args)}
        clone = _Cloner(subst).function(f)
        self.clones[key] = clone
        definition.funs.functions = definition.funs.functions + (clone,)
        if definition.module is not None:
            name = f"{_member_name(definition.module, f.var)}_spec{n + 1}"
            definition.module.members[name] = clone.var
        self.definitions[id(clone.var)] = _Definition(clone, definition.funs, definition.module, definition.enclosing)
        # The clone's local functions are definitions too, whose calls (in the
        # clone) may be specialized
        self.collect(clone.body, None, definition.enclosing)
        self.pending.append((clone, definition.enclosing, self.depth + 1))
        return clone

    def run(self, unit: ir.Unit) -> None:
        tops = [(m.init, m) for m in unit.modules] + [(unit.main, None)]
        for body, module in tops:
            self.collect(body, module, frozenset())
        for body, _ in tops:
            self.body(body, frozenset())
        while self.pending:
            clone, enclosing, self.depth = self.pending.pop()
            self.body(clone.body, enclosing)


def _member_name(module: ir.Module, var: ir.Var) -> str:
    return next(name for name, v in module.members.items() if v is var)


class _Cloner:
    """Copies a function with types substituted: every variable it binds is a
    fresh one, and every other node is copied, except module references (which
    keep their identity) and the free variables it uses."""

    def __init__(self, subst: dict[int, QType]) -> None:
        self.subst = subst
        self.vars: dict[int, ir.Var] = {}

    def type(self, t: QType) -> QType:
        return t.substitute(self.subst) if t._fv else t

    def fresh(self, var: ir.Var, hint: Optional[str] = None) -> ir.Var:
        new = ir.Var(hint if hint is not None else var.hint, self.type(var.type), var.mutable)
        self.vars[id(var)] = new
        return new

    def function(self, f: ir.Function) -> ir.Function:
        """The clone of a function the substitution instantiates (its type
        parameters are substituted away)."""
        self.bind_all(f.body)
        params = tuple((self.fresh(v), mode) for v, mode in f.params)
        result_t = self.type(f.result_type)
        # The clone's type is made from its parameters and result: the type of
        # the variable naming the original may be elaborated with quantifiers of
        # other symbols than the function's own type parameters
        _, inner = quantified(f.var.type)
        names = [p.name for p in inner.params] if isinstance(inner, QFunType) else []
        if isinstance(inner, QFunType) or params:
            clone_t: QType = QFunType(
                params=tuple(
                    QParam(name=names[i] if i < len(names) else v.hint, type_val=v.type, is_var=mode == "var",
                           is_out=mode == "out")
                    for i, (v, mode) in enumerate(params)
                ),
                result_type=result_t,
            )
        else:
            clone_t = result_t
        var = ir.Var(f"{f.var.hint}_spec", clone_t, f.var.mutable)
        return ir.Function(var, (), params, result_t, self.copy(f.body), trace_name=f.trace_name)

    def bind_all(self, body: ir.Body) -> None:
        """Makes fresh variables for every binder in body (and in the functions
        it binds)."""
        for s in body.statements:
            match s:
                case ir.Let(var=v) | ir.VarDecl(var=v):
                    if id(v) not in self.vars:
                        self.fresh(v)
                case ir.Funs(functions=functions):
                    for f in functions:
                        self.fresh(f.var)
                        for v, _ in f.params:
                            self.fresh(v)
                        self.bind_all(f.body)
                case ir.LetRec(vars=vars_):
                    for v in vars_:
                        self.fresh(v)
                case ir.Switch(cases=cases):
                    for c in cases:
                        if c.binder is not None:
                            self.fresh(c.binder)
                case ir.Inspect(cases=cases):
                    for c in cases:
                        for b in c.binders:
                            self.fresh(b)
                case ir.Try(exception=e):
                    self.fresh(e)
                case ir.Join(params=params):
                    for p in params:
                        self.fresh(p)
            for b in statement_bodies(s):
                self.bind_all(b)

    def copy(self, node: Any) -> Any:
        match node:
            case ir.Var():
                return self.vars.get(id(node), node)
            case ir.Body(statements=statements):
                return ir.Body([self.copy(s) for s in statements])
            case ir.Module() | ir.Import():
                return node
            case QType():
                return self.type(node)
            case tuple():
                return tuple(self.copy(x) for x in node)
            case list():
                return [self.copy(x) for x in node]
            case ir.Function():
                return ir.Function(self.copy(node.var), node.type_params, self.copy(node.params),
                                   self.type(node.result_type), self.copy(node.body), trace_name=node.trace_name)
        parts = fields_of(node)
        if parts is not None:
            return rebuild(node, tuple(self.copy(part) for part in parts))
        # Constants' values, names, labels, tags, modes, shapes
        return node


def specialize_unit(unit: ir.Unit) -> ir.Unit:
    """Specializes the unit's calls in place, returning it."""
    _Specializer().run(unit)
    unit.stage = "specialized"
    return unit
