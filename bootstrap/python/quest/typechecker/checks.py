"""Kind Bound, Distinct Name, Type Join, and Subtype Assertion Checks."""

from __future__ import annotations

from typing import Any, Optional

import quest.syntax.ast as ast
from quest.diagnostics import QuestTypeError
from quest.env import Environment
from quest.typed_ast import TypedExpr
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


def check_distinct_names(members: Any) -> None:
    """Rejects a simultaneous declaration (members joined by and) that declares one name twice."""
    seen: set[str] = set()
    for member in members:
        if member.name in seen:
            raise QuestTypeError(
                f"'{member.name}' is declared more than once in one simultaneous declaration",
                offset=member.offset,
            )
        seen.add(member.name)


def describe_kind(k: QKind) -> str:
    """Formats a kind as written in a HasKind clause: <: T for POWER(T), :: K otherwise."""
    if isinstance(k, QPowerKind):
        return f"<: {k.bound}"
    return f":: {k}"


def check_type_arg_kind(what: str, targ: QType, bound: QKind, env: Environment, offset: int) -> None:
    """Checks that a type argument (explicit or inferred) has a kind within its quantifier's bound."""
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
    """Computes the least common supertype of a collection of types under subtyping."""
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


def require_subtype(
    expr: ast.Expr,
    typed: TypedExpr,
    expected_type: QType,
    env: Environment,
    type_desc: Optional[str] = None,
) -> TypedExpr:
    """Asserts that the type of an elaborated expression is a subtype of expected_type."""
    if not is_subtype(typed.type_val, expected_type, env):
        prefix = "Type mismatch: synthesized" if type_desc is None else f"{type_desc}"
        raise QuestTypeError(
            f"{prefix} type '{typed.type_val}' is not a subtype of expected type '{expected_type}'",
            offset=expr.offset,
        )
    return typed
