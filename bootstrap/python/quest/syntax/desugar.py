"""Desugaring: rewrites the parser's syntactic sugar into the core forms the
type checker elaborates.

The pass runs between parsing and type checking (the pipeline's `desugar` phase,
and every other path that parses a unit and checks it), so that the type checker
never rewrites syntax. It is purely syntactic: it needs neither types nor
scopes, and it keeps the offsets of the syntax it replaces, so that errors point
at the source as written (docs/syntax.md §5, docs/pipeline.md §2).

- `a andif b` becomes `if a then b else false end`, and `a orif b` becomes `if a
  then true else b end`, marked short_circuit: the type checker checks their
  operands against Bool and gives them type Bool.
- An infix operator that is not built in, `a op b`, becomes the call `op(a, b)`.
- `a[i] := v` becomes `ExprIndexAssign` (other assignments stay infix: their
  targets are told apart by scope).
- `if c1 then e1 elsif c2 then e2 ... [else e] end` becomes conditionals nested
  in the else branches, each at its elsif's condition; a chain without an else
  branch ends with `ok`. A conditional with neither elsif nor else branches is
  left alone: it is a statement, of type Ok.
- `let f(params): T = e`, not recursive and not external, becomes `let f =
  fun(params): T e`. A recursive one keeps its parameters and result annotation,
  which declare its type before any value is checked; so does an external one,
  whose parameters declare the external function's type.

The rewrite is bottom up and returns its input unchanged (the same object) when
there is nothing to desugar, so it can be applied to any AST node, including a
phrase, a type, or a kind.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, TypeVar

import quest.syntax.ast as ast

# Infix operators the type checker elaborates itself; every other infix operator
# is a call. The arithmetic, relational, concatenation, and eager boolean
# operators are those typed by quest.types.env.INFIX_OPERATORS, which maps them
# to their operand and result types (test_desugar checks that the two agree); ==
# and != are rejected with a suggestion. The table stays with the types it
# names, so that syntax does not depend on types.
BUILTIN_INFIX_OPERATORS = frozenset((
    "+", "-", "*", "/", "%", "mod", "<", "<=", ">", ">=",
    "++", "--", "**", "//", "^^", "<<", "<<=", ">>", ">>=",
    "<>", "/\\", "\\/",
    ":=", "is", "isnot", "==", "!=",
))

N = TypeVar("N")


def desugar(node: N) -> N:
    """Returns node (an AST node, or a tuple of them) with its syntactic sugar
    rewritten into core forms."""
    return _walk(node)


def _walk(value: Any) -> Any:
    if isinstance(value, tuple):
        walked = tuple(_walk(item) for item in value)
        return value if all(new is old for new, old in zip(walked, value)) else walked
    parts = ast.ast_fields(value)
    if parts is None:
        return value
    walked = tuple(_walk(part) for part in parts)
    if any(new is not old for new, old in zip(walked, parts)):
        value = ast.rebuild_ast(value, walked)
    return _rewrite(value)


def _rewrite(node: ast.ASTNode) -> ast.ASTNode:
    """Rewrites one node whose children are already desugared."""
    match node:
        case ast.ExprInfix(left=left, op="andif", right=right, offset=off):
            false = ast.ExprBool(value=False, offset=off)
            return ast.ExprIf(cond=left, then_branch=right, else_branch=false, short_circuit=True, offset=off)
        case ast.ExprInfix(left=left, op="orif", right=right, offset=off):
            true = ast.ExprBool(value=True, offset=off)
            return ast.ExprIf(cond=left, then_branch=true, else_branch=right, short_circuit=True, offset=off)
        case ast.ExprInfix(left=ast.ExprIndex(target=target, index=index), op=":=", right=right, offset=off):
            return ast.ExprIndexAssign(target=target, index=index, value=right, offset=off)
        case ast.ExprInfix(left=left, op=op, right=right, offset=off) if op not in BUILTIN_INFIX_OPERATORS:
            return ast.ExprApp(func=ast.ExprId(name=op, offset=off), args=(left, right), offset=off)
        case ast.ExprIf(elsifs=elsifs) if elsifs:
            nested: ast.Expr = node.else_branch if node.else_branch is not None else ast.ExprOk(offset=node.offset)
            for cond, then_branch in reversed(elsifs):
                nested = ast.ExprIf(cond=cond, then_branch=then_branch, else_branch=nested, offset=cond.offset)
            return replace(node, elsifs=(), else_branch=nested)
        case ast.LetValueBinding(params=params, value=value, is_rec=False) if params and not isinstance(
            value, ast.ExprExternal
        ):
            fun = ast.ExprFun(params=params, return_type=node.type_annot, body=value, offset=node.offset)
            return replace(node, value=fun, params=(), type_annot=None)
        case _:
            return node
