"""Desugaring: rewrites the parser's syntactic sugar into the core forms the type checker elaborates.

The pass runs between parsing and type checking (the pipeline's `desugar` phase, and every other path that parses a
unit and checks it), so that the type checker never rewrites syntax. It is purely syntactic: it needs neither types
nor scopes, and it keeps the offsets of the syntax it replaces, so that errors point at the source as written
([type-system.md](../../../../docs/type-system.md) §6.2, [pipeline.md](../../../../docs/pipeline.md) §2).

- `a andif b` becomes `if a then b else false end`, and `a orif b` becomes `if a then true else b end`.
- An infix operator that is not built in, `a op b`, becomes the call `op(a, b)`.
- `a[i] := v` becomes `ExprIndexAssign` (other assignments stay infix: their targets are told apart by scope).
- `if c1 then e1 elsif c2 then e2 ... [else e] end` becomes conditionals nested in the else branches, each at its
  elsif's condition; a chain without an else branch ends with `ok`. A conditional with neither elsif nor else
  branches is left alone: it is a statement, of type Ok.
- `let f(params): T = e`, not recursive and not external, becomes `let f = fun(params): T e`. A recursive one keeps
  its parameters and result annotation, which declare its type before any value is checked; so does an external one,
  whose parameters declare the external function's type.

The rewrite is bottom up and returns its input unchanged (the same object) when there is nothing to desugar, so it
can be applied to any AST node, including a phrase, a type, or a kind.
"""

from __future__ import annotations

from dataclasses import fields, replace
from typing import Any, TypeVar

import quest.syntax.ast as ast
from quest.types.kinds import INFIX_OPERATORS

# Infix operators the type checker elaborates itself; every other infix operator is a call
BUILTIN_INFIX_OPERATORS = frozenset((*INFIX_OPERATORS, ":=", "is", "isnot", "==", "!="))

N = TypeVar("N")


def desugar(node: N) -> N:
    """Returns node (an AST node, or a tuple of them) with its syntactic sugar rewritten into core forms."""
    return _walk(node)


def _walk(value: Any) -> Any:
    if isinstance(value, tuple):
        walked = tuple(_walk(item) for item in value)
        return value if all(new is old for new, old in zip(walked, value)) else walked
    if not isinstance(value, ast.ASTNode):
        return value
    changes: dict[str, Any] = {}
    for field in fields(value):
        if field.name == "offset":
            continue
        old = getattr(value, field.name)
        new = _walk(old)
        if new is not old:
            changes[field.name] = new
    if changes:
        value = replace(value, **changes)
    return _rewrite(value)


def _rewrite(node: ast.ASTNode) -> ast.ASTNode:
    """Rewrites one node whose children are already desugared."""
    match node:
        case ast.ExprIf(elsifs=elsifs) if elsifs:
            else_branch: ast.Expr = node.else_branch if node.else_branch is not None else ast.ExprOk(offset=node.offset)
            for cond, then_branch in reversed(elsifs):
                else_branch = ast.ExprIf(
                    cond=cond, then_branch=then_branch, else_branch=else_branch, offset=cond.offset
                )
            return replace(node, elsifs=(), else_branch=else_branch)
        case _:
            return node
