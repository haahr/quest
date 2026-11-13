"""Reduced types: type operator applications reduced and recursive types
unfolded at a type's head, a bounded type's bound followed, and the queries on
option types the backends make (an option's cases in order, how is compares its
values). The checker keeps types as written and uses none of these
(docs/type-system.md §2.2); canonical.py builds canonical forms on them.

The self-hosted counterpart is questlang/types/reduce.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from quest.types import (
    QAbstractType,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QFunType,
    QOptionType,
    QOutType,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeVar,
    QVariantType,
    QVarType,
    strip_aliases,
    pruned,
)


MAX_BETA_STEPS = 1000


def beta_reduce_head(t: QType) -> QType:
    """Beta-reduces type operator applications at the head of t, without
    unfolding recursive types."""
    for _ in range(MAX_BETA_STEPS):
        t = pruned(t)
        if not isinstance(t, QTypeApp):
            return t
        ctor = beta_reduce_head(t.constructor)
        if isinstance(ctor, QExceptionType) and len(t.arguments) == 1:
            return QExceptionType(payload_type=t.arguments[0])
        if not isinstance(ctor, QTypeFun) or len(ctor.params) != len(t.arguments):
            return t
        t = ctor.body.substitute({formal.symbol_id: arg for formal, arg in zip(ctor.params, t.arguments)})
    return t


# Values of a recursive type are represented like values of its unfolding (a
# tuple's values by a pointer to its struct, a function's by a closure pointer),
# so that the two, being equal, share a representation. Its tag is that of its
# unfolding too, except for unfoldings whose tags are built from their parts'
# tags: these would contain the tag being defined, so such a recursive type is
# named by its body instead (_recursive_tag).
_UNFOLDED_REPRESENTATION = (
    QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QAutoType,
    QFunType, QAllType, QExceptionType,
)


SELF_NAMED = (QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QAutoType)


def unfold_recursive(
    t: QType,
    kinds: Optional[tuple[type, ...]] = _UNFOLDED_REPRESENTATION,
) -> Optional[QType]:
    """Returns the unfolding of a recursive type (or an application reducing to
    one) if it is a constructed type (one of kinds), or None otherwise. With
    kinds None, any unfolding that is neither recursive nor an application is
    returned (a recursive type that does not use its variable, such as a member
    of a group that does not refer to the group, is the type it unfolds to)."""
    if isinstance(t, QTypeApp):
        t = beta_reduce_head(t)
    for _ in range(MAX_BETA_STEPS):
        if not isinstance(t, (QRecType, QRecGroupType)):
            break
        t = t.unfold_lazily()
        t = pruned(t)
        if isinstance(t, QTypeApp):
            t = beta_reduce_head(t)
    if kinds is None:
        return None if isinstance(t, (QRecType, QRecGroupType, QTypeApp)) else t
    return t if isinstance(t, kinds) else None


# Reduced forms by the id of the type node, kept with the node so that its id is
# not reused
_NORMALIZED: dict[int, tuple[QType, QType]] = {}


def normalize_type(t: QType) -> QType:
    """t with its outermost constructor exposed, which shapes are built from
    (repr/shapes.py): aliases stripped, a recursive type replaced by its
    unfolding, and an application of a type operator by its reduction. An
    application that reduces to a recursive type is replaced by the unfolding
    when that is a constructed type, and otherwise by the application's lazy
    evaluation when that is a tuple or record type; an application of an
    abstract type operator stays as it is."""
    t = pruned(t)
    if t._has_meta:
        return _normalize_uncached(t)
    entry = _NORMALIZED.get(id(t))
    if entry is None or entry[0] is not t:
        entry = (t, _normalize_uncached(t))
        _NORMALIZED[id(t)] = entry
    return entry[1]


def _normalize_uncached(t: QType) -> QType:
    t = strip_aliases(t)
    if isinstance(t, (QRecType, QRecGroupType)):
        unfolded = unfold_recursive(t, None)
        if unfolded is not None:
            return unfolded
    if isinstance(t, QTypeApp):
        unfolded = unfold_recursive(t)
        if unfolded is not None:
            return unfolded
        reduced = beta_reduce_head(t)
        if not isinstance(reduced, (QTypeApp, QRecType, QRecGroupType)):
            return reduced
        evaled = t.evaluate_lazily()
        if evaled is not t and isinstance(evaled, (QTupleType, QRecordType)):
            return evaled
    return t


def resolve_type_bound(t: QType) -> QType:
    """t, or for a type variable, abstract type, or path type bounded by
    POWER(T), the type its bounds resolve to."""
    curr = strip_aliases(pruned(t))
    visited = set()
    while isinstance(curr, (QTypeVar, QAbstractType, QPathType)) and isinstance(curr.bound, QPowerKind):
        # (A path type is told apart by itself, not by a symbol of its own)
        sym_id = id(curr) if isinstance(curr, QPathType) else curr.symbol_id
        if sym_id in visited:
            break
        visited.add(sym_id)
        curr = curr.bound.bound
        curr = pruned(curr)
    return curr


def option_case_names(t: QType) -> tuple[str, ...]:
    """The names of the cases of an option type as written, in order (for a type
    parameter bounded by one, its bound's): the order an option's ordinal counts
    in at t (docs/type-system.md §6.6), whatever the order of the type its value
    was made at, or of t's shape (repr/shapes.py, which orders cases by name)."""
    curr = normalize_type(t)
    while not isinstance(curr, QOptionType):
        exposed = normalize_type(resolve_type_bound(curr))
        if exposed is curr:
            raise ValueError(f"{t} is not an option type")
        curr = exposed
    return tuple(o.name for o in curr.options)


@dataclass(frozen=True)
class OptionIdentity:
    """How `is` compares options of an option type (docs/extensions.md,
    Options as Values): its cases without components compare by case; and
    if the type is single-word, its one case with components (`single`)
    compares by its one component, of type `component`."""
    empty: frozenset[str]
    single: Optional[str] = None
    component: Optional[QType] = None


def option_identity(t: QType) -> Optional[OptionIdentity]:
    """t's option identity, or None if t is not an option type: for a module's
    abstract type, its representation's, since is compares an abstract type's
    values as their representation's; for a type parameter bounded by an option
    type, its bound's."""
    from quest.modules.abstract_types import abstract_type_by_symbol
    curr = normalize_type(t)
    while not isinstance(curr, QOptionType):
        reps = {}
        for symbol_id in curr._fv:
            entry = abstract_type_by_symbol(symbol_id)
            if entry is not None and entry.rep is not None:
                reps[symbol_id] = entry.rep
        exposed = normalize_type(curr.substitute(reps)) if reps else curr
        if exposed is curr:
            exposed = normalize_type(resolve_type_bound(curr))
        if exposed is curr:
            return None
        curr = exposed
    empty: set[str] = set()
    with_components: list[tuple[str, tuple[Any, ...]]] = []
    for o in curr.options:
        payload = normalize_type(o.payload_type) if o.payload_type is not None else None
        fields = payload.fields if isinstance(payload, QTupleType) else ()
        if not fields:
            empty.add(o.name)
        else:
            with_components.append((o.name, fields))
    if len(with_components) == 1:
        name, fields = with_components[0]
        if len(fields) == 1 and isinstance(fields[0], QTupleField) and not fields[0].is_var:
            return OptionIdentity(frozenset(empty), name, fields[0].type_val)
    return OptionIdentity(frozenset(empty))


def collect_fun_quantifiers(fun_type: QType) -> tuple[tuple[QQuantifier, ...], QType]:
    """The universal quantifiers wrapping a function type (a recursive one,
    through its unfolding), and the type they quantify, as written: their
    symbols are those the type's own parts refer to, where a shape's are those
    of its canonical form (repr/shapes.py)."""
    quants: tuple[QQuantifier, ...] = ()
    curr = normalize_type(fun_type)
    while isinstance(curr, QAllType):
        quants = quants + curr.quantifiers
        curr = normalize_type(curr.body)
    return quants, curr
