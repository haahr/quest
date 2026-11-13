"""Lowering's pre-pass over a typed program: the local var variables that
functions nested in their scope use, which lowering holds in boxes the closures
share (lower.py).

The self-hosted counterpart is questlang/ir/captures.
"""

from __future__ import annotations

from quest.typechecker.typed_ast import (
    typed_fields,
    TypedFun,
    TypedLetValue,
    TypedLetValueGroup,
    TypedModule,
    TypedProgram,
    TypedVar,
)


def captured_mutables(prog: TypedProgram) -> set[int]:
    """The symbols of the local var variables that functions nested in their
    scope use: a let var anywhere but directly at a unit's or a module's top
    level (where it is global), used inside a function within its scope."""
    declared: dict[int, int] = {}
    captured: set[int] = set()
    seen: set[int] = set()

    def walk(n, depth: int, top: bool) -> None:
        if isinstance(n, (list, tuple)):
            for item in n:
                walk(item, depth, top)
            return
        if id(n) in seen:
            return
        fields = typed_fields(n)
        if fields is None:
            return
        seen.add(id(n))
        if isinstance(n, TypedLetValue) and n.symbol.is_var and not top:
            declared[n.symbol.symbol_id] = depth
        elif isinstance(n, TypedVar) and declared.get(n.symbol.symbol_id, depth) < depth:
            captured.add(n.symbol.symbol_id)
        inner = depth + 1 if isinstance(n, TypedFun) else depth
        # A unit's phrases, a module's bindings, and a group's members are at
        # the top level their parent is at
        inner_top = top and isinstance(n, (TypedProgram, TypedModule, TypedLetValueGroup))
        for part in fields:
            walk(part, inner, inner_top)

    walk(prog, 0, True)
    return captured
