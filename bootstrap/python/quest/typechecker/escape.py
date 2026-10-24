"""Path-Type Escape Analysis and Closedness Validation."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Sequence
from typing import Any, Optional

from quest.diagnostics import QuestTypeError
from quest.types.env import Environment
from quest.typechecker.typed_ast import TypedExpr
from quest.types import (
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QFunType,
    QType,
    QTypeVar,
    find_path_types,
    strip_aliases,
    unalias,
)


def inspected_auto_type(target: TypedExpr, env: Environment) -> Optional[QAutoType]:
    """The auto type of an inspect target."""
    target_type = target.type_val.evaluate_lazily(env)
    return target_type if isinstance(target_type, QAutoType) else None


def is_auto_type(t: QType) -> bool:
    """Returns True if t (stripped of aliases) is an auto type."""
    return isinstance(unalias(t), QAutoType)


def check_dynamic_type_args(
    all_type: QAllType,
    type_args: Sequence[QType],
    offset: int,
    check: Callable[[QType, str, int], None],
) -> None:
    """Checks with `check` (the closedness check) the type argument of a function shaped like dynamic.new
    (A::TYPE a:A): T or dynamic.be (A::TYPE d:T): A for an auto type T, which record or test the type argument at
    run time (inside the function it is a type parameter, which the closedness check allows)."""
    body = all_type.body
    if len(all_type.quantifiers) != 1 or not isinstance(body, QFunType) or len(body.params) != 1 or not type_args:
        return
    a_id = all_type.quantifiers[0].symbol_id

    def is_a(t: QType) -> bool:
        t = unalias(t)
        return isinstance(t, QTypeVar) and t.symbol_id == a_id

    param_t = body.params[0].type_val
    if (is_a(param_t) and is_auto_type(body.result_type)) or (
        is_auto_type(param_t) and is_a(body.result_type)
    ):
        check(type_args[0], "The type of a dynamic value", offset)


def check_no_package_types(t: QType, what: str, offset: int) -> None:
    """Rejects a type that mentions an abstract type projected from a package value (t.A): its identity is the
    package's hidden type, which is not known at run time."""
    paths = find_path_types(strip_aliases(t))
    if paths:
        names = ", ".join(sorted({f"{p.root_name}.{p.field_name}" for p in paths}))
        raise QuestTypeError(
            f"{what} cannot mention {names}, an abstract type of a package value, because its identity is not "
            f"known at run time",
            offset=offset,
        )


def mutable_type_vars_with_ids(t: Any, ids: set[int]) -> list[Any]:
    """The type variables in t (a type stripped of aliases) whose symbol ids are in ids and that occur inside
    mutable data: an array's elements, a var component or field, or a var or out parameter."""
    found: list[Any] = []
    seen: set[tuple[int, bool]] = set()

    def visit(node: Any, mutable: bool) -> None:
        if (id(node), mutable) in seen:
            return
        seen.add((id(node), mutable))
        if isinstance(node, (QTypeVar, QAbstractType)) and node.symbol_id in ids and mutable:
            found.append(node)
        if isinstance(node, (tuple, list)):
            for item in node:
                visit(item, mutable)
        elif dataclasses.is_dataclass(node) and not isinstance(node, type):
            inner = (
                mutable
                or isinstance(node, QArrayType)
                or bool(getattr(node, "is_var", False))
                or bool(getattr(node, "is_out", False))
            )
            for f in dataclasses.fields(node):
                visit(getattr(node, f.name), inner)

    visit(t, False)
    return found


def type_vars_with_ids(t: Any, ids: set[int]) -> list[Any]:
    """The type variables in t (a type stripped of aliases) whose symbol ids are in ids."""
    found: list[Any] = []
    seen: set[int] = set()

    def visit(node: Any) -> None:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, (QTypeVar, QAbstractType)) and node.symbol_id in ids:
            found.append(node)
        if isinstance(node, (tuple, list)):
            for item in node:
                visit(item)
        elif dataclasses.is_dataclass(node) and not isinstance(node, type):
            for f in dataclasses.fields(node):
                visit(getattr(node, f.name))

    visit(t)
    return found


def check_no_escaping_path_types(
    typ: QType,
    local_symbol_ids: set[int],
    context_desc: str,
    offset: int = 0,
) -> None:
    """Ensures that no abstract path-dependent types rooted at local variables escape."""
    for p in find_path_types(typ):
        if p.root_symbol_id in local_symbol_ids:
            raise QuestTypeError(
                f"Abstract type '{p.root_name}.{p.field_name}' cannot escape {context_desc} "
                f"in type '{typ}'",
                offset=offset,
            )
