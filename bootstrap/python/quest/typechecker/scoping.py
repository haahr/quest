"""A check that a typed program is well scoped: every variable refers to a binder in scope, and every use of a
function's type parameter is inside that function.

Symbols, not names, identify binders (docs/ir.md §2), so a pass that re-elaborates a declaration with fresh symbols, or
a transformation that moves code out of a binder's scope, leaves references that no binder in scope declares. The
typed AST does not show this: names still match. This check finds it. It runs after type checking when
QUEST_CHECK_SCOPES=1, which the test runners set; production builds skip it.

What it checks:

- **Local values.** A variable bound locally (a parameter, a block's let, a for variable, a case, try, or inspect
  binder) is used only within the binder's scope: after a let in its block (or within it, for let rec), within its
  function, branch, or loop body. Variables of top-level and module bindings, imports, and builtins are global.
- **Type parameters.** A polymorphic function's type_param_ids are the quantifiers of its own type, and a type
  mentioning a function's type parameter occurs only inside that function.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Any, Iterator, Optional

from quest.env import ValueSymbol
from quest.typechecker.typed_ast import (
    TypedBlock,
    TypedCase,
    TypedFor,
    TypedFun,
    TypedInspect,
    TypedLetValue,
    TypedLetValueGroup,
    TypedModule,
    TypedNode,
    TypedProgram,
    TypedTry,
    TypedTuple,
    TypedVar,
)
from quest.types import QAllType, QType


def scope_checks_enabled() -> bool:
    return os.environ.get("QUEST_CHECK_SCOPES") == "1"


def _quantifier_ids(fun: TypedFun) -> tuple[int, ...]:
    t = fun.type_val
    return tuple(q.symbol_id for q in t.quantifiers) if isinstance(t, QAllType) else ()


def _local_binders(node: Any) -> Iterator[tuple[ValueSymbol, str]]:
    """The local binders in node (not top-level or module bindings), with what binds them."""
    seen: set[int] = set()

    def walk(n: Any, top: bool) -> Iterator[tuple[ValueSymbol, str]]:
        if n is None or isinstance(n, (str, int, float, bool, QType)) or id(n) in seen:
            return
        seen.add(id(n))
        if isinstance(n, TypedFun):
            for p in n.params:
                yield p.symbol, "parameter"
            yield from walk(n.body, False)
            return
        if isinstance(n, TypedBlock):
            for b in n.bindings:
                for member in (b.members if isinstance(b, TypedLetValueGroup) else (b,)):
                    if isinstance(member, TypedLetValue):
                        yield member.symbol, "let"
            # fall through to the children
        if isinstance(n, TypedFor):
            yield n.symbol, "for variable"
        if isinstance(n, (TypedCase, TypedTry)):
            for br in n.branches:
                if br.binder is not None:
                    yield br.binder, "binder"
        if isinstance(n, TypedInspect):
            for br in n.branches:
                for b in br.binders:
                    yield b, "binder"
        if isinstance(n, TypedModule):
            for b in n.bindings:
                yield from walk(b, True)
            return
        if isinstance(n, (list, tuple)):
            for item in n:
                yield from walk(item, top)
        elif isinstance(n, TypedNode):
            for f in dataclasses.fields(n):
                yield from walk(getattr(n, f.name), top)

    yield from walk(node, True)


class _Checker:
    def __init__(self, prog: TypedProgram) -> None:
        self.problems: list[str] = []
        self.local_ids = {sym.symbol_id for sym, _ in _local_binders(prog)}
        self.param_ids: set[int] = set()
        self._collect_type_params(prog, set())

    def _collect_type_params(self, n: Any, seen: set[int]) -> None:
        if n is None or isinstance(n, (str, int, float, bool, QType)) or id(n) in seen:
            return
        seen.add(id(n))
        if isinstance(n, TypedFun):
            quants = _quantifier_ids(n)
            self.param_ids.update(quants)
            self.param_ids.update(n.type_param_ids)
            if n.type_param_ids and tuple(n.type_param_ids) != quants:
                self.problems.append(
                    f"function at offset {n.offset}: type_param_ids {n.type_param_ids} are not the quantifiers "
                    f"{quants} of its type {n.type_val}"
                )
        if isinstance(n, (list, tuple)):
            for item in n:
                self._collect_type_params(item, seen)
        elif isinstance(n, TypedNode):
            for f in dataclasses.fields(n):
                self._collect_type_params(getattr(n, f.name), seen)

    def _check_type(self, t: QType, type_scope: frozenset[int], where: Any) -> None:
        stray = (set(getattr(t, "_fv", ()) or ()) & self.param_ids) - type_scope
        if stray:
            self.problems.append(
                f"{type(where).__name__} at offset {getattr(where, 'offset', 0)}: type {t} mentions type parameters "
                f"{sorted(stray)} outside their function"
            )

    def _check_var(self, var: TypedVar, values: frozenset[int]) -> None:
        sym_id = var.symbol.symbol_id
        if sym_id in self.local_ids and sym_id not in values:
            self.problems.append(
                f"variable '{var.name}' (#{sym_id}) at offset {var.offset} is used outside the scope of its binder"
            )

    def walk(self, n: Any, values: frozenset[int], types: frozenset[int]) -> None:
        if n is None or isinstance(n, (str, int, float, bool)):
            return
        if isinstance(n, QType):
            return
        if isinstance(n, ValueSymbol):
            return
        if isinstance(n, (list, tuple)):
            for item in n:
                self.walk(item, values, types)
            return
        if not isinstance(n, TypedNode):
            return
        for f in dataclasses.fields(n):
            v = getattr(n, f.name)
            if isinstance(v, QType):
                self._check_type(v, types, n)
            elif isinstance(v, ValueSymbol):
                self._check_type(v.type_val, types, n)
        match n:
            case TypedVar():
                self._check_var(n, values)
            case TypedFun(params=params, body=body):
                # The function's type parameters are the quantifiers of its own type (checked against type_param_ids)
                inner_types = types | set(_quantifier_ids(n) or n.type_param_ids)
                inner_values = values | {p.symbol.symbol_id for p in params}
                for p in params:
                    self._check_type(p.type_val, frozenset(inner_types), p)
                self.walk(body, frozenset(inner_values), frozenset(inner_types))
            case TypedBlock(bindings=bindings, result=result):
                scope = set(values)
                for b in bindings:
                    members = b.members if isinstance(b, TypedLetValueGroup) else (b,)
                    lets = [m for m in members if isinstance(m, TypedLetValue)]
                    if any(m.is_rec for m in lets):
                        # Recursive members see one another
                        scope |= {m.symbol.symbol_id for m in lets}
                        self.walk(b, frozenset(scope), types)
                    else:
                        # The values see the bindings in scope before the declaration, not its members
                        self.walk(b, frozenset(scope), types)
                        scope |= {m.symbol.symbol_id for m in lets}
                self.walk(result, frozenset(scope), types)
            case TypedFor(symbol=symbol, start=start, stop=stop, body=body):
                self.walk(start, values, types)
                self.walk(stop, values, types)
                self.walk(body, values | {symbol.symbol_id}, types)
            case TypedCase(target=target, branches=branches, else_branch=else_branch):
                self.walk(target, values, types)
                for br in branches:
                    inner = values | ({br.binder.symbol_id} if br.binder is not None else set())
                    self.walk(br.body, frozenset(inner), types)
                self.walk(else_branch, values, types)
            case TypedTry(body=body, branches=branches, else_branch=else_branch):
                self.walk(body, values, types)
                for br in branches:
                    self.walk(br.exc_pattern, values, types)
                    inner = values | ({br.binder.symbol_id} if br.binder is not None else set())
                    self.walk(br.body, frozenset(inner), types)
                self.walk(else_branch, values, types)
            case TypedInspect(target=target, branches=branches, else_branch=else_branch):
                self.walk(target, values, types)
                for br in branches:
                    self._check_type(br.match_type, types, br)
                    self.walk(br.body, values | {b.symbol_id for b in br.binders}, types)
                self.walk(else_branch, values, types)
            case _:
                for f in dataclasses.fields(n):
                    self.walk(getattr(n, f.name), values, types)


def check_well_scoped(prog: TypedProgram) -> list[str]:
    """The scoping problems of a typed program (empty when it is well scoped)."""
    checker = _Checker(prog)
    checker.walk(prog, frozenset(), frozenset())
    return checker.problems
