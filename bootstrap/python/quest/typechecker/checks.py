"""Checks the type checker's construct families share: distinct names in a
group of declarations, type arguments' kinds, joins of the types of branches,
and subtype assertions. A failed check raises QuestTypeError (KindError for
a type argument's kind) at the offset given.

The self-hosted counterpart is questlang/typechecker/checks."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Optional

import quest.syntax.ast as ast
from quest.common.diagnostics import QuestCompilerError, QuestTypeError
from quest.types.env import Environment
from quest.typechecker.typed_ast import (
    TypedBlock,
    TypedCase,
    TypedExit,
    TypedExpr,
    TypedIf,
    TypedInspect,
    TypedRaise,
    TypedTry,
)
from quest.types import (
    KindError,
    OK_TYPE,
    QKind,
    QPowerKind,
    QType,
    is_subkind,
    is_subtype,
    synth_kind,
)


def check_binder(name: Optional[str], offset: int) -> None:
    """Raises a type error if name, a value being bound (a let, a parameter, a
    tuple's component, a signature's field or quantifier), is a built-in infix
    operator's: the type checker elaborates those itself wherever they are
    written infix, so a binding of one would never be used there. mod, on the
    list but never infix, is a function's name (word.mod, bignum.mod)."""
    from quest.syntax.desugar import BUILTIN_INFIX_OPERATORS

    if name is not None and name in BUILTIN_INFIX_OPERATORS and not name[0].isalpha():
        raise QuestTypeError(
            f"'{name}' is a built-in operator and cannot be bound; give the operator a name of its own, such as <+>",
            offset=offset,
        )


def check_distinct_names(members: Any) -> None:
    """Rejects a simultaneous declaration (members joined by and) that declares
    one name twice."""
    seen: set[str] = set()
    for member in members:
        if member.name in seen:
            raise QuestTypeError(
                f"'{member.name}' is declared more than once in one simultaneous declaration",
                offset=member.offset,
            )
        seen.add(member.name)


def describe_kind(k: QKind) -> str:
    """Formats a kind as written in a HasKind clause: <: T for POWER(T), :: K
    otherwise."""
    if isinstance(k, QPowerKind):
        return f"<: {k.bound}"
    return f":: {k}"


def check_type_arg_kind(what: str, targ: QType, bound: QKind, env: Environment, offset: int) -> None:
    """Checks that a type argument (explicit or inferred) has a kind within its
    quantifier's bound."""
    bound_lazy = bound.evaluate_lazily(env)
    if isinstance(bound_lazy, QPowerKind):
        if not is_subtype(targ, bound_lazy.bound, env):
            raise KindError(f"{what} '{targ}' is not a subtype of bound '{bound_lazy.bound}'", offset=offset)
        return
    kind = synth_kind(targ, env)
    if not is_subkind(kind, bound_lazy, env):
        raise KindError(
            f"{what} '{targ}' has kind '{kind}', which is not a subkind of '{bound_lazy}'",
            offset=offset,
        )


def join_types(
    types: list[QType] | tuple[QType, ...],
    env: Environment,
    offset: int,
    error_msg: Optional[str] = None,
) -> QType:
    """Computes the least common supertype of a collection of types under
    subtyping."""
    if not types:
        return OK_TYPE
    join_type = types[0]
    for bt in types[1:]:
        if is_subtype(join_type, bt, env):
            join_type = bt
        elif is_subtype(bt, join_type, env):
            pass
        else:
            msg = error_msg or f"Cannot find common supertype join for branch types '{join_type}' and '{bt}'"
            if "{t1}" in msg:
                msg = msg.format(t1=join_type, t2=bt)
            raise QuestTypeError(msg, offset=offset)
    return join_type


def is_divergent(typed: TypedExpr) -> bool:
    """Whether an expression cannot finish normally, as its form shows: a
    raise or an exit, a block whose result is divergent, or a conditional,
    case, inspect, or try whose branches (and body) all are. A call of a
    function that always raises is not: its type says what it returns."""
    match typed:
        case TypedRaise() | TypedExit():
            return True
        case TypedBlock(result=result):
            return is_divergent(result)
        case TypedIf(then_branch=then_branch, else_branch=else_branch):
            return is_divergent(then_branch) and is_divergent(else_branch)
        case TypedCase(branches=branches, else_branch=else_branch) | TypedInspect(
            branches=branches, else_branch=else_branch
        ):
            bodies = [b.body for b in branches] + ([else_branch] if else_branch is not None else [])
            return bool(bodies) and all(is_divergent(b) for b in bodies)
        case TypedTry(body=body, branches=branches, else_branch=else_branch):
            parts = [body] + [b.body for b in branches] + ([else_branch] if else_branch is not None else [])
            return all(is_divergent(p) for p in parts)
        case _:
            return False


def retype_divergent(typed: TypedExpr, t: QType) -> TypedExpr:
    """A divergent expression (is_divergent) given type t, as checking it
    against t would have typed it: the raise or exit it ends in, and each
    block, conditional, case, inspect, and try on the way to it, have type
    t."""
    match typed:
        case TypedRaise() | TypedExit():
            return replace(typed, type_val=t)
        case TypedBlock(result=result):
            return replace(typed, result=retype_divergent(result, t), type_val=t)
        case TypedIf(then_branch=then_branch, else_branch=else_branch):
            return replace(
                typed,
                then_branch=retype_divergent(then_branch, t),
                else_branch=retype_divergent(else_branch, t),
                type_val=t,
            )
        case TypedCase(branches=branches, else_branch=else_branch) | TypedInspect(
            branches=branches, else_branch=else_branch
        ):
            return replace(
                typed,
                branches=tuple(replace(b, body=retype_divergent(b.body, t)) for b in branches),
                else_branch=retype_divergent(else_branch, t) if else_branch is not None else None,
                type_val=t,
            )
        case TypedTry(body=body, branches=branches, else_branch=else_branch):
            return replace(
                typed,
                body=retype_divergent(body, t),
                branches=tuple(replace(b, body=retype_divergent(b.body, t)) for b in branches),
                else_branch=retype_divergent(else_branch, t) if else_branch is not None else None,
                type_val=t,
            )
        case _:
            raise QuestCompilerError(f"retyping {type(typed).__name__}, which is not divergent")


def join_branches(
    parts: list[TypedExpr],
    env: Environment,
    offset: int,
    error_msg: Optional[str] = None,
) -> tuple[QType, list[TypedExpr]]:
    """Joins the types of a construct's parts (its branches, or an array's
    elements) when it has no expected type, leaving out the divergent ones
    (is_divergent), which never produce a value; if all are divergent, it
    joins them all. Returns the joined type and the parts, the divergent ones
    retyped to it, as checking them against it would have typed them
    (docs/type-system.md §6.1)."""
    live = [p for p in parts if not is_divergent(p)]
    if not live:
        return join_types([p.type_val for p in parts], env, offset, error_msg), parts
    t = join_types([p.type_val for p in live], env, offset, error_msg)
    return t, [retype_divergent(p, t) if is_divergent(p) else p for p in parts]


def require_subtype(
    expr: ast.Expr,
    typed: TypedExpr,
    expected_type: QType,
    env: Environment,
    type_desc: Optional[str] = None,
) -> TypedExpr:
    """Asserts that the type of an elaborated expression is a subtype of
    expected_type."""
    if not is_subtype(typed.type_val, expected_type, env):
        prefix = "Type mismatch: synthesized" if type_desc is None else f"{type_desc}"
        raise QuestTypeError(
            f"{prefix} type '{typed.type_val}' is not a subtype of expected type '{expected_type}'",
            offset=expr.offset,
        )
    return typed


def not_desugared(node: ast.ASTNode) -> QuestCompilerError:
    """The internal error for syntactic sugar that reached the type checker:
    every path that parses a unit and checks it desugars it first
    (quest/syntax/desugar.py)."""
    return QuestCompilerError(
        f"internal: {type(node).__name__} reached the type checker without desugaring", offset=node.offset
    )
