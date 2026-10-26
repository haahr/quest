"""Metavariable Resolution over Typed ASTs."""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from quest.typechecker.typed_ast import TypedNode
from quest.types import QType, resolve_metas


def resolve_typed_metas(node: Any, memo: Optional[dict[int, Any]] = None) -> Any:
    """Rebuilds a typed AST with solved metavariables in its types replaced by their solutions."""
    if memo is None:
        memo = {}
    key = id(node)
    if key in memo:
        return memo[key]
    result = node
    match node:
        case QType():
            result = resolve_metas(node)
        case tuple():
            items = tuple(resolve_typed_metas(item, memo) for item in node)
            if any(a is not b for a, b in zip(items, node)):
                result = items
        case TypedNode():
            changes = {}
            for f in dataclasses.fields(node):
                if f.init:
                    old = getattr(node, f.name)
                    new = resolve_typed_metas(old, memo)
                    if new is not old:
                        changes[f.name] = new
            if changes:
                result = dataclasses.replace(node, **changes)
    memo[key] = result
    return result
