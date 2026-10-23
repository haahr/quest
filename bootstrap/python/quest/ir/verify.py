"""The IR verifier (docs/ir.md §9): checks a unit's invariants for its stage, after every pass, in tests.

Core invariants, checked here:

- every operation's arguments are atoms (variables or constants);
- every variable is bound by exactly one binder, and used only in its scope: after its let or declaration in the
  same body (or a body within it), within its function, case, handler, or join point's continuation; a declared
  variable (declare) is bound by one let in its scope, and is in scope from its declaration;
- a function does not use a mutable variable of an enclosing function (closures do not capture mutable locals;
  mutable variables of a unit's or module's top level are globals, which any function may use);
- a jump names a join point whose body encloses it, and passes as many values as the join point has parameters; a
  break or continue names an enclosing loop; neither crosses a function's boundary;
- a return occurs only in a function's body;
- a terminator is the last statement of its body.

verify_unit returns the problems found; check_unit raises if there are any. The verifier runs when
QUEST_CHECK_IR=1, which the test runners set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, fields, is_dataclass

from quest.ir import nodes as ir


def ir_checks_enabled() -> bool:
    return os.environ.get("QUEST_CHECK_IR") == "1"


@dataclass(frozen=True)
class _Scope:
    """What is in scope at a point: variables, join points (label to arity), loops, and the enclosing function."""
    vars: frozenset[int]
    joins: tuple[tuple[str, int], ...] = ()
    loops: tuple[str, ...] = ()
    in_function: bool = False
    # Mutable variables of enclosing functions, which a nested function must not use
    outer_mutables: frozenset[int] = frozenset()
    # Mutable variables of the current function (or top level), and whether this is a top level (unit or module)
    local_mutables: frozenset[int] = frozenset()
    top_level: bool = True

    def with_vars(self, *vs: ir.Var) -> _Scope:
        mutables = self.local_mutables | {id(v) for v in vs if v.mutable}
        return _Scope(self.vars | {id(v) for v in vs}, self.joins, self.loops, self.in_function, self.outer_mutables,
                      mutables, self.top_level)


class _Verifier:
    def __init__(self) -> None:
        self.problems: list[str] = []
        self.bound: set[int] = set()
        # Variables declared, and not yet bound by their let
        self.declared: set[int] = set()

    def problem(self, text: str) -> None:
        self.problems.append(text)

    def bind(self, var: ir.Var, where: str) -> None:
        if id(var) in self.bound:
            self.problem(f"{where}: variable '{var.hint}' is bound more than once")
        self.bound.add(id(var))
        if var.shape is None:
            self.problem(f"{where}: variable '{var.hint}' has no shape")

    def use(self, a: ir.Atom, scope: _Scope, where: str) -> None:
        if isinstance(a, ir.Const):
            return
        if not isinstance(a, ir.Var):
            self.problem(f"{where}: an argument is not an atom: {type(a).__name__}")
            return
        if id(a) not in scope.vars:
            self.problem(f"{where}: variable '{a.hint}' is used outside its scope")
        elif id(a) in scope.outer_mutables:
            self.problem(f"{where}: function uses mutable variable '{a.hint}' of an enclosing function")

    def operation(self, o, scope: _Scope, where: str) -> None:
        if isinstance(o, (ir.Var, ir.Const)):
            self.use(o, scope, where)
            return
        if not is_dataclass(o) or isinstance(o, (ir.Body, ir.Function)):
            self.problem(f"{where}: not an operation: {type(o).__name__}")
            return
        for f in fields(o):
            v = getattr(o, f.name)
            if f.name == "type_components":
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

    def function(self, f: ir.Function, scope: _Scope) -> None:
        where = f"function '{f.var.hint}'"
        # A nested function may use the enclosing functions' values but not their mutable variables; the top level's
        # mutable variables are globals
        outer_mutables = scope.outer_mutables | (frozenset() if scope.top_level else scope.local_mutables)
        inner = _Scope(scope.vars, (), (), True, outer_mutables, frozenset(), False)
        for v, mode in f.params:
            self.bind(v, where)
            if mode not in ("value", "var", "out"):
                self.problem(f"{where}: parameter '{v.hint}' has mode '{mode}'")
            if (mode != "value") != v.mutable:
                self.problem(f"{where}: parameter '{v.hint}' is {mode} but {'' if v.mutable else 'not '}mutable")
        inner = inner.with_vars(*(v for v, _ in f.params))
        self.body(f.body, inner, where)

    def body(self, body: ir.Body, scope: _Scope, where: str) -> _Scope:
        for i, s in enumerate(body.statements):
            if isinstance(s, ir.TERMINATORS) and i != len(body.statements) - 1:
                self.problem(f"{where}: a {type(s).__name__.lower()} is followed by other statements")
            scope = self.statement(s, scope, where)
        return scope

    def statement(self, s, scope: _Scope, where: str) -> _Scope:
        match s:
            case ir.Let(var=var, value=value):
                self.operation(value, scope, where)
                if id(var) in self.declared:
                    self.declared.discard(id(var))
                    if id(var) not in scope.vars:
                        self.problem(f"{where}: declared variable '{var.hint}' is bound outside its scope")
                else:
                    self.bind(var, where)
                if var.mutable:
                    self.problem(f"{where}: let binds mutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.Declare(var=var):
                self.bind(var, where)
                self.declared.add(id(var))
                if var.mutable:
                    self.problem(f"{where}: declare of mutable variable '{var.hint}'")
                return scope.with_vars(var)
            case ir.VarDecl(var=var, init=init):
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
            case ir.Store():
                self.operation(s, scope, where)
            case ir.Do(value=value):
                self.operation(value, scope, where)
            case ir.Funs(functions=functions, recursive=recursive):
                for f in functions:
                    self.bind(f.var, where)
                inner = scope.with_vars(*(f.var for f in functions)) if recursive else scope
                for f in functions:
                    self.function(f, inner)
                return scope.with_vars(*(f.var for f in functions))
            case ir.LetRec(vars=vars_, body=body):
                # The body computes the variables' values (binding them with lets), and closures it makes may refer
                # to them; they are in scope after it
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
                inner = _Scope(scope.vars, scope.joins, scope.loops + (label,), scope.in_function,
                               scope.outer_mutables, scope.local_mutables, scope.top_level)
                self.body(body, inner, where)
            case ir.Try(body=body, exception=exception, handler=handler):
                self.body(body, scope, where)
                self.bind(exception, where)
                self.body(handler, scope.with_vars(exception), where)
            case ir.Join(label=label, params=params, continuation=continuation, body=body):
                if any(lbl == label for lbl, _ in scope.joins):
                    self.problem(f"{where}: join label '{label}' is already in use")
                for p in params:
                    self.bind(p, where)
                self.body(continuation, scope.with_vars(*params), where)
                inner = _Scope(scope.vars, scope.joins + ((label, len(params)),), scope.loops, scope.in_function,
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
            case ir.Unreachable():
                pass
            case _:
                self.problem(f"{where}: not a statement: {type(s).__name__}")
        return scope


def verify_unit(unit: ir.Unit) -> list[str]:
    """The problems of a unit at the Core stage (empty when it satisfies every invariant)."""
    v = _Verifier()
    top = _Scope(frozenset())
    # A module's members are visible to the code after its definition (by name, through the module), not as
    # variables; each module's initializer is its own top level
    for m in unit.modules:
        v.body(m.init, top, f"module '{m.name}'")
    v.body(unit.main, top, "main")
    # A declared exception made only on a path the lowering never reached would be left unbound
    if v.declared:
        v.problem(f"{len(v.declared)} declared variable(s) never bound")
    return v.problems


def check_unit(unit: ir.Unit) -> None:
    """Raises if the unit violates an invariant."""
    problems = verify_unit(unit)
    if problems:
        raise AssertionError("internal: the IR is not well formed:\n  " + "\n  ".join(problems[:20]))
