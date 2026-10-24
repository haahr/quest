"""Runtime type descriptors' type-level forms, for every backend (docs/c-representation.md §6.4): the placeholders
for bound type parameters and template holes, the canonical forms of function and auto types that descriptors
compare, and descriptor tags."""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from quest.codegen.layout import type_digest
from quest.types.canonical import normalize_type
from quest.types import (
    strip_aliases,
    QAllType,
    QAutoType,
    QFunType,
    QQuantifier,
    QRecordField,
    QType,
    QTypeVar,
    reserved_symbol_id,
    reserved_symbol_index,
    ReservedSymbolUse,
    QParam,
    QKind,
)


def module_abstract_type_name(t: QType) -> Optional[str]:
    """The global name of a module's abstract type (docs/dynamic.md §2.3), or None for any other type."""
    from quest.modules.abstract_types import abstract_type_by_symbol

    if not isinstance(t, QTypeVar):
        return None
    entry = abstract_type_by_symbol(t.symbol_id)
    return entry.global_name if entry is not None and entry.linked else None


def fun_descriptor_tag(t: QType) -> str:
    """The tag of the runtime descriptor of a function type (QFunType or QAllType).

    type_tag is QClosure for every function type, which suits struct naming (all closures are represented
    alike) but not descriptors, which must tell function types apart. Equal types that differ only in the names
    of their type and value parameters share a tag (see canonical_fun_type).
    """
    return "fun_" + type_digest(canonical_fun_type(t))


# ----------------------------------------------------------------------------
# Runtime type descriptors
# ----------------------------------------------------------------------------

# Bound type parameters of polymorphic function types are described by placeholders: type variables with reserved
# symbol ids (ReservedSymbolUse.BOUND_VAR) that stand for de Bruijn indices (quest_type_bound_vars in the runtime).


def bound_var(index: int, bound: Optional[QKind]) -> QTypeVar:
    """The placeholder for the type parameter with de Bruijn index `index`, keeping its bound (which determines
    its C representation)."""
    return QTypeVar(name=f"#{index}", symbol_id=reserved_symbol_id(ReservedSymbolUse.BOUND_VAR, index), bound=bound)


def bound_var_index(t: QType) -> Optional[int]:
    """The de Bruijn index of a bound type parameter placeholder, or None for any other type."""
    if isinstance(t, QTypeVar):
        return reserved_symbol_index(t.symbol_id, ReservedSymbolUse.BOUND_VAR)
    return None


def hole_var(index: int, bound: Optional[QKind]) -> QTypeVar:
    """The hole for the `index`-th type parameter of a descriptor template, keeping the parameter's bound (which
    determines its C representation, and so the template's layout)."""
    return QTypeVar(name=f"?{index}", symbol_id=reserved_symbol_id(ReservedSymbolUse.HOLE, index), bound=bound)


def hole_index(t: QType) -> Optional[int]:
    """The position of a template's hole, or None for any other type."""
    if isinstance(t, QTypeVar):
        return reserved_symbol_index(t.symbol_id, ReservedSymbolUse.HOLE)
    return None


def _bound_vars_in(t: Any) -> list[QTypeVar]:
    """The bound type parameter placeholders occurring in t."""
    found: dict[int, QTypeVar] = {}
    seen: set[int] = set()

    def visit(node: Any) -> None:
        if id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, QTypeVar) and bound_var_index(node) is not None:
            found.setdefault(node.symbol_id, node)
        if isinstance(node, (tuple, list)):
            for item in node:
                visit(item)
        elif dataclasses.is_dataclass(node) and not isinstance(node, type):
            for f in dataclasses.fields(node):
                visit(getattr(node, f.name))

    visit(t)
    return list(found.values())


def _shift_bound_vars(t: Any, by: int) -> Any:
    """t with each bound type parameter placeholder's index raised by `by` (moving t under `by` more binders)."""
    present = _bound_vars_in(t)
    if not present or by == 0:
        return t
    subst = {bv.symbol_id: bound_var(bound_var_index(bv) + by, bv.bound) for bv in present}
    return t.substitute_types(subst) if isinstance(t, QKind) else t.substitute(subst)


def canonical_fun_type(t: QType) -> QType:
    """The canonical form of a function type, which equal types share: value parameters lose their names, and the
    type parameters of a polymorphic function type are replaced by placeholders (de Bruijn indices, counting binders
    outward from the reference; within one All, the last parameter is 0 in the body and the k-th parameter's bound
    sees the earlier ones). Nested polymorphic function types are canonicalized when they are described."""
    t = normalize_type(strip_aliases(t.prune() if hasattr(t, "prune") else t))
    if isinstance(t, QFunType):
        return QFunType(
            params=tuple(QParam(name="", type_val=p.type_val, is_var=p.is_var, is_out=p.is_out) for p in t.params),
            result_type=t.result_type,
        )
    if not isinstance(t, QAllType):
        return t
    quants = t.quantifiers
    n = len(quants)
    new_quants: list[QQuantifier] = []
    placeholders: list[QTypeVar] = []
    for k, q in enumerate(quants):
        bound = _shift_bound_vars(q.bound, k)
        subst = {quants[j].symbol_id: bound_var(k - 1 - j, new_quants[j].bound) for j in range(k)}
        bound = bound.substitute_types(subst)
        quant_id = reserved_symbol_id(ReservedSymbolUse.CANONICAL_QUANTIFIER, k)
        new_quants.append(QQuantifier(name=f"${k}", symbol_id=quant_id, bound=bound))
    body = _shift_bound_vars(t.body, n)
    for k, q in enumerate(quants):
        placeholders.append(bound_var(n - 1 - k, new_quants[k].bound))
    body = body.substitute({q.symbol_id: placeholders[k] for k, q in enumerate(quants)})
    body = canonical_fun_type(body) if isinstance(body, QFunType) else body
    return QAllType(quantifiers=tuple(new_quants), body=body)


def canonical_auto_type(t: QAutoType) -> QAutoType:
    """The canonical form of an auto type, which equal types share: its type parameter is the placeholder with de
    Bruijn index 0 (see canonical_fun_type)."""
    kind_bound = _shift_bound_vars(t.kind_bound, 1) if t.kind_bound is not None else t.kind_bound
    placeholder = bound_var(0, kind_bound)
    signature = tuple(
        QRecordField(
            name=f.name,
            type_val=_shift_bound_vars(f.type_val, 1).substitute({t.symbol_id: placeholder}),
            is_var=f.is_var,
        )
        for f in t.signature
    )
    return QAutoType(type_param="$0", symbol_id=placeholder.symbol_id, kind_bound=kind_bound, signature=signature)
