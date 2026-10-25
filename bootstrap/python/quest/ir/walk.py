"""Traversals of the IR shared by the passes and the verifier: the bodies a statement contains, the variables it
binds, the atoms it uses, and the global variables of a unit."""

from __future__ import annotations

from dataclasses import fields
from typing import Iterator

from quest.ir import nodes as ir


def statement_bodies(s) -> list[ir.Body]:
    """The bodies a statement contains (not those of the functions a funs statement binds)."""
    match s:
        case ir.If(then_body=t, else_body=e):
            return [t, e]
        case ir.Switch(cases=cases, else_body=e) | ir.Inspect(cases=cases, else_body=e):
            return [c.body for c in cases] + ([e] if e is not None else [])
        case ir.Loop(body=b) | ir.LetRec(body=b):
            return [b]
        case ir.Try(body=b, handler=h):
            return [b, h]
        case ir.Join(continuation=c, body=b):
            return [c, b]
    return []


def statement_binders(s) -> list[ir.Var]:
    """The variables a statement binds itself (not those bound in the bodies it contains)."""
    match s:
        case ir.Let(var=v) | ir.VarDecl(var=v):
            return [v]
        case ir.Funs(functions=functions):
            return [f.var for f in functions]
        case ir.LetRec(vars=vars_):
            return list(vars_)
        case ir.Switch(cases=cases):
            return [c.binder for c in cases if c.binder is not None]
        case ir.Inspect(cases=cases):
            return [b for c in cases for b in c.binders]
        case ir.Try(exception=e):
            return [e]
        case ir.Join(params=params):
            return list(params)
    return []


def _atoms_of(node) -> Iterator[ir.Atom]:
    """The atoms an operation or a statement uses directly (not in the bodies or functions it contains)."""
    if isinstance(node, (ir.Var, ir.Const)):
        yield node
        return
    for f in fields(node):
        if f.name in ("type_components", "module", "code") or f.name in ir.DESCRIPTOR_FIELDS:
            continue
        v = getattr(node, f.name)
        if isinstance(v, (ir.Var, ir.Const)):
            yield v
        elif isinstance(v, tuple):
            for item in v:
                if isinstance(item, (ir.Var, ir.Const)):
                    yield item
                elif isinstance(item, tuple):
                    # Record fields: (name, atom, is_var)
                    yield from (part for part in item if isinstance(part, (ir.Var, ir.Const)))


def statement_uses(s) -> list[ir.Atom]:
    """The atoms a statement uses directly: its operation's, or its own (a condition, a value, a jump's arguments);
    not those of the bodies or functions it contains, nor its binders."""
    match s:
        case ir.Let(value=value) | ir.Do(value=value):
            return list(_atoms_of(value))
        case ir.VarDecl(init=init):
            return [init] if init is not None else []
        case ir.Assign(var=var, value=value):
            return [var, value]
        case ir.Store():
            return list(_atoms_of(s))
        case ir.If(cond=a) | ir.Switch(value=a) | ir.Inspect(value=a) | ir.Echo(value=a) | ir.Return(value=a):
            return [a]
        case ir.Jump(args=args):
            return list(args)
        case ir.Raise(exception=e, payload=p):
            return [e] if p is None else [e, p]
        case ir.Reraise(exception=e):
            return [e]
        case ir.Try(catches=catches) if isinstance(catches, tuple):
            return list(catches)
    return []


def walk_statements(body: ir.Body, into_functions: bool = True) -> Iterator:
    """Every statement in body and the bodies it contains (and in the functions funs statements bind, unless
    into_functions is false), in order."""
    for s in body.statements:
        yield s
        if into_functions and isinstance(s, ir.Funs):
            for f in s.functions:
                yield from walk_statements(f.body, into_functions)
        for b in statement_bodies(s):
            yield from walk_statements(b, into_functions)


def global_variables(unit: ir.Unit) -> set[int]:
    """The variables (by identity) a unit's main body and its modules' initializers bind outside loops and functions:
    each is bound at most once in a run, and is a global, which functions use rather than capture."""
    found: set[int] = set()

    def visit(body: ir.Body) -> None:
        for s in body.statements:
            found.update(id(v) for v in statement_binders(s))
            if not isinstance(s, ir.Loop):
                for b in statement_bodies(s):
                    visit(b)

    for m in unit.modules:
        visit(m.init)
    visit(unit.main)
    return found
