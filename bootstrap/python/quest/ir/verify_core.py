"""The IR's core invariants, which every stage keeps (docs/ir.md §9), and the
scopes they are checked in: verify.py adds the later stages' and runs them all.
The core invariants are listed in verify.py's docstring.

The self-hosted counterpart is questlang/ir/verifycore.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quest.ir import nodes as ir

from quest.ir.walk import contents
from quest.repr.layout import resolved_shape
from quest.repr.shapes import shape


@dataclass(frozen=True)
class Scope:
    """What is in scope at a point: variables, join points (label to arity),
    loops, and the enclosing function."""
    vars: frozenset[int]
    joins: tuple[tuple[str, int], ...] = ()
    loops: tuple[str, ...] = ()
    in_function: bool = False
    # Mutable variables of enclosing functions, which a nested function must not
    # use
    outer_mutables: frozenset[int] = frozenset()
    # Mutable variables of the current function (or top level), and whether this
    # is a top level (unit or module)
    local_mutables: frozenset[int] = frozenset()
    top_level: bool = True

    def with_vars(self, *vs: ir.Var) -> Scope:
        mutables = self.local_mutables | {id(v) for v in vs if v.mutable}
        return Scope(self.vars | {id(v) for v in vs}, self.joins, self.loops, self.in_function, self.outer_mutables,
                      mutables, self.top_level)


class Verifier:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.bound: set[int] = set()
        # The modules the unit defines and imports, which module references must
        # be
        self.modules: set[int] = set()
        # After closure conversion, the unit's functions, which closures must be
        # of (None before)
        self.functions: Optional[set[int]] = None
        self.represented = False

    def problem(self, text: str) -> None:
        self.problems.append(text)

    def bind(self, var: ir.Var, where: str) -> None:
        if id(var) in self.bound:
            self.problem(f"{where}: variable '{var.hint}' is bound more than once")
        self.bound.add(id(var))
        if var.shape is None:
            self.problem(f"{where}: variable '{var.hint}' has no shape")

    def use(self, a: ir.Atom, scope: Scope, where: str) -> None:
        if isinstance(a, ir.Const):
            return
        if not isinstance(a, ir.Var):
            self.problem(f"{where}: an argument is not an atom: {type(a).__name__}")
            return
        if id(a) not in scope.vars:
            self.problem(f"{where}: variable '{a.hint}' is used outside its scope")
        elif id(a) in scope.outer_mutables:
            self.problem(f"{where}: function uses mutable variable '{a.hint}' of an enclosing function")

    def operation(self, o, scope: Scope, where: str) -> None:
        if isinstance(o, (ir.Var, ir.Const)):
            self.use(o, scope, where)
            return
        if contents(o) is None or isinstance(o, (ir.Body, ir.Function)):
            self.problem(f"{where}: not an operation: {type(o).__name__}")
            return
        if isinstance(o, ir.Convert) and not self.represented:
            self.problem(f"{where}: convert before the represent pass")
        if isinstance(o, (ir.MakeClosure, ir.EnvField)) and self.functions is None:
            self.problem(f"{where}: {type(o).__name__} before closure conversion")
        if isinstance(o, ir.MakeClosure) and self.functions is not None and id(o.code) not in self.functions:
            self.problem(f"{where}: a closure of a function that is not the unit's")
        for v in contents(o):
            if isinstance(v, (ir.Module, ir.Import)):
                if id(v) not in self.modules:
                    self.problem(f"{where}: reference to a module that is not the unit's or imported by it")
                continue
            if isinstance(v, (ir.Var, ir.Const)):
                self.use(v, scope, where)
            elif isinstance(v, tuple):
                for item in v:
                    if isinstance(item, (ir.Var, ir.Const)):
                        self.use(item, scope, where)
                    elif isinstance(item, tuple):
                        # Record fields: (name, atom, is_var)
                        for part in item:
                            if isinstance(part, (ir.Var, ir.Const)):
                                self.use(part, scope, where)

    def option_cases(self, o, var: ir.Var, where: str) -> None:
        """Checks the cases an option operation counts ordinals in (ir.Ordinal,
        ir.MakeOption, ir.Payload)."""
        def option_shape(t):
            s = resolved_shape(shape(t)) if t is not None else None
            return s if s is not None and s.kind == "option" else None

        def check(cases: tuple[str, ...], t) -> None:
            s = option_shape(t)
            if s is not None and sorted(cases) != sorted(c.name for c in s.cases):
                self.problem(f"{where}: an ordinal counts in cases ({' '.join(cases)}) of an option of type {t}")

        match o:
            case ir.Ordinal(value=v, cases=cases):
                check(cases, v.type if isinstance(v, ir.Var) else None)
            case ir.MakeOption(ordinal=ordinal, cases=cases) if ordinal is not None:
                check(cases, var.type)
            case ir.Payload(value=ir.Var() as v, tag=tag, ordinal=ordinal):
                if option_shape(v.type) is not None and ordinal is None:
                    self.problem(f"{where}: the payload of option case {tag} without its ordinal")

    def function(self, f: ir.Function, scope: Scope) -> None:
        where = f"function '{f.var.hint}'"
        # A nested function may use the enclosing functions' values but not
        # their mutable variables; the top level's mutable variables are globals
        outer_mutables = scope.outer_mutables | (frozenset() if scope.top_level else scope.local_mutables)
        inner = Scope(scope.vars, (), (), True, outer_mutables, frozenset(), False)
        if f.env is not None:
            self.bind(f.env, where)
            inner = inner.with_vars(f.env)
        for v, mode in f.params:
            self.bind(v, where)
            if mode not in ("value", "var", "out"):
                self.problem(f"{where}: parameter '{v.hint}' has mode '{mode}'")
            if (mode != "value") != v.mutable:
                self.problem(f"{where}: parameter '{v.hint}' is {mode} but {'' if v.mutable else 'not '}mutable")
        inner = inner.with_vars(*(v for v, _ in f.params))
        self.body(f.body, inner, where)

    def body(self, body: ir.Body, scope: Scope, where: str) -> Scope:
        for i, s in enumerate(body.statements):
            if isinstance(s, ir.TERMINATORS) and i != len(body.statements) - 1:
                self.problem(f"{where}: a {type(s).__name__.lower()} is followed by other statements")
            scope = self.statement(s, scope, where)
        return scope

    def statement(self, s, scope: Scope, where: str) -> Scope:
        match s:
            case ir.Let(var=var, value=value):
                self.operation(value, scope, where)
                self.option_cases(value, var, where)
                self.bind(var, where)
                if var.mutable:
                    self.problem(f"{where}: let binds mutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.VarDecl(var=var, init=init):
                if init is not None:
                    self.use(init, scope, where)
                self.bind(var, where)
                if not var.mutable:
                    self.problem(f"{where}: var declares immutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.Assign(var=var, value=value):
                self.use(var, scope, where)
                self.use(value, scope, where)
                if not var.mutable:
                    self.problem(f"{where}: assignment to immutable variable '{var.hint}'")
            case ir.StoreAt() | ir.StoreField() | ir.StoreComponent() | ir.StoreElement():
                self.operation(s, scope, where)
            case ir.Do(value=value):
                self.operation(value, scope, where)
            case ir.Funs(functions=functions, recursive=recursive):
                if self.functions is not None:
                    self.problem(f"{where}: a funs statement after closure conversion")
                for f in functions:
                    self.bind(f.var, where)
                inner = scope.with_vars(*(f.var for f in functions)) if recursive else scope
                for f in functions:
                    self.function(f, inner)
                return scope.with_vars(*(f.var for f in functions))
            case ir.LetRec(vars=vars_, body=body):
                # The body computes the variables' values (binding them with
                # lets), and closures it makes may refer to them; they are in
                # scope after it
                inner = scope.with_vars(*vars_)
                self.body(body, inner, where)
                return scope.with_vars(*vars_)
            case ir.If(cond=cond, then_body=then_body, else_body=else_body):
                self.use(cond, scope, where)
                self.body(then_body, scope, where)
                self.body(else_body, scope, where)
            case ir.Switch(value=value, cases=cases, else_body=else_body):
                self.use(value, scope, where)
                for c in cases:
                    inner = scope
                    if c.binder is not None:
                        self.bind(c.binder, where)
                        inner = scope.with_vars(c.binder)
                    self.body(c.body, inner, where)
                if else_body is not None:
                    self.body(else_body, scope, where)
            case ir.Inspect(value=value, cases=cases, else_body=else_body):
                self.use(value, scope, where)
                for c in cases:
                    for b in c.binders:
                        self.bind(b, where)
                    self.body(c.body, scope.with_vars(*c.binders), where)
                if else_body is not None:
                    self.body(else_body, scope, where)
            case ir.Loop(label=label, body=body):
                if label in scope.loops:
                    self.problem(f"{where}: loop label '{label}' is already in use")
                inner = Scope(scope.vars, scope.joins, scope.loops + (label,), scope.in_function,
                               scope.outer_mutables, scope.local_mutables, scope.top_level)
                self.body(body, inner, where)
            case ir.Try(body=body, exception=exception, handler=handler, catches=catches):
                for c in catches:
                    self.use(c, scope, where)
                self.body(body, scope, where)
                self.bind(exception, where)
                self.body(handler, scope.with_vars(exception), where)
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                if any(lbl == label for lbl, _ in scope.joins):
                    self.problem(f"{where}: join label '{label}' is already in use")
                for p in params:
                    self.bind(p, where)
                self.body(continuation, scope.with_vars(*params), where)
                inner = Scope(scope.vars, scope.joins + ((label, len(params)),), scope.loops, scope.in_function,
                               scope.outer_mutables, scope.local_mutables, scope.top_level)
                self.body(body, inner, where)
            case ir.Echo(value=value):
                self.use(value, scope, where)
            case ir.EchoText():
                pass
            case ir.Return(value=value):
                self.use(value, scope, where)
                if not scope.in_function:
                    self.problem(f"{where}: return outside a function")
            case ir.Jump(label=label, args=args):
                for a in args:
                    self.use(a, scope, where)
                arity = next((n for lbl, n in scope.joins if lbl == label), None)
                if arity is None:
                    self.problem(f"{where}: jump to '{label}', which is not an enclosing join point")
                elif arity != len(args):
                    self.problem(f"{where}: jump to '{label}' passes {len(args)} values for {arity} parameters")
            case ir.Break(label=label) | ir.Continue(label=label):
                if label not in scope.loops:
                    self.problem(f"{where}: {type(s).__name__.lower()} of '{label}', which is not an enclosing loop")
            case ir.Raise(exception=e, payload=p):
                self.use(e, scope, where)
                if p is not None:
                    self.use(p, scope, where)
            case ir.Reraise(exception=e):
                self.use(e, scope, where)
            case ir.Unreachable():
                pass
            case _:
                self.problem(f"{where}: not a statement: {type(s).__name__}")
        return scope
