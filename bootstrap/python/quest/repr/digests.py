"""Digests of types, which stand for their printed text, the same in every
compilation: what names structs, descriptors, and layouts where type_tag
(layout.py) conflates types.

The self-hosted counterpart is questlang/repr/digests.
"""

from __future__ import annotations

import hashlib
from typing import Any
from quest.repr.syntax import joined
from quest.repr.shapes import shape
from quest.types import (
    OK_TYPE,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QFunType,
    QOptionField,
    QOptionType,
    QOutType,
    QParam,
    QPowerKind,
    QQuantifier,
    QRecType,
    QRecordField,
    QRecordType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QVarType,
    QVariantField,
    QVariantType,
    pruned,
)
from quest.repr.layout import type_tag


def type_digest(t: QType) -> str:
    """A short digest of a type's printed text, telling apart types that
    type_tag conflates (see printed): the text of the structure of its canonical
    form (the unfolding of a recursive type)."""
    return printed(shape(t).structure)[1][:16]


def type_identity_key(t: QType) -> str:
    """A key telling types apart where type_tag does not (all function types are
    QClosure): the tag and a digest of the canonical type's text. Equal types
    elaborated separately get the same key; Python == is not defined on types,
    so this stands in for them in dictionaries."""
    return f"{type_tag(t)}#{type_digest(t)}"


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# Digests of types stand for their printed text (str), which is the same in
# every compilation, but printing shares nothing, so a large recursive type
# prints as megabytes. A type whose text is at most this long is digested from
# its text; a longer one from the text of its outermost node with the digests of
# its parts in place of theirs, computed once per hash-consed node. Either way
# types that print differently get different digests.
PRINTED_TEXT_LIMIT = 1024


def _printed_parts(node: Any) -> list[Any]:
    """The text of str(node) as a list of literal strings and the parts (types,
    components, kinds) printed in between. It mirrors the __str__ methods in
    quest.types; a node not listed prints as one string."""

    def spaced(items: Any) -> list[Any]:
        out: list[Any] = []
        for i, item in enumerate(items):
            if i:
                out.append(" ")
            out.append(item)
        return out

    def framed(head: str, items: Any) -> list[Any]:
        return [f"{head} ", *spaced(items), " end"] if items else [f"{head} end"]

    match node:
        case QExceptionType():
            return ["Exception"] if node.payload_type is OK_TYPE else ["Exception(", node.payload_type, ")"]
        case QTupleField():
            prefix = "var " if node.is_var else ""
            return [f"{prefix}{node.name}: " if node.name else f"{prefix}:", node.type_val]
        case QTupleTypeFormal():
            return [f"{node.name}::", node.bound]
        case QTupleTypeBinding():
            bound = ["::", node.bound] if node.bound else []
            return [f"Let {node.name}", *bound, " = ", node.type_val]
        case QTupleType():
            return framed("Tuple", node.fields)
        case QRecordField():
            return [f"{'var ' if node.is_var else ''}{node.name}: ", node.type_val]
        case QRecordType():
            if node.provenance:
                return [f"Module '{node.provenance}'"]
            return framed("Record", node.fields)
        case QVariantField():
            prefix = "var " if node.is_var else ""
            return [f"{prefix}{node.name}: ", node.type_val] if node.type_val else [f"{prefix}{node.name}"]
        case QVariantType():
            return framed("Variant", node.variants)
        case QOptionField():
            return [f"{node.name} with ", node.payload_type] if node.payload_type else [node.name]
        case QOptionType():
            return framed("Option", node.options)
        case QParam():
            prefix = "var " if node.is_var else ("out " if node.is_out else "")
            return [f"{prefix}{node.name}: ", node.type_val]
        case QFunType():
            return ["Fun(", *spaced(node.params), "): ", node.result_type]
        case QVarType():
            return ["Var(", node.element_type, ")"]
        case QArrayType():
            return ["Array(", node.element_type, ")"]
        case QOutType():
            return ["Out(", node.element_type, ")"]
        case QQuantifier():
            if isinstance(node.bound, QPowerKind):
                return [f"{node.name} <: ", node.bound.bound]
            return [f"{node.name} :: ", node.bound]
        case QAllType():
            return ["All(", *spaced(node.quantifiers), ") ", node.body]
        case QAutoType():
            if isinstance(node.kind_bound, QPowerKind):
                head = [f"Auto {node.type_param} <: ", node.kind_bound.bound, " with "]
            else:
                head = [f"Auto {node.type_param} :: ", node.kind_bound, " with "]
            return [*head, *spaced(node.signature), " end"]
        case QTypeFormal():
            return [f"{node.name} :: ", node.bound]
        case QTypeFun():
            return ["Fun(", *spaced(node.params), ") ", node.body]
        case QTypeApp():
            return [node.constructor, "(", *spaced(node.arguments), ")"]
        case QRecType():
            return [f"Rec({node.var_name} :: ", node.bound, ") ", node.body]
        case QPowerKind():
            return ["<: ", node.bound]
        case QAllKind():
            return [f"ALL({node.param_name} :: ", node.param_kind, ") ", node.result_kind]
        case _:
            return [str(node)]


def _printed_uncached(node: Any) -> tuple[int, str]:
    length = 0
    pieces: list[str] = []
    for part in _printed_parts(node):
        if isinstance(part, str):
            length += len(part)
            pieces.append(part)
        else:
            part_length, part_digest = printed(part)
            length += part_length
            pieces.append("\0" + part_digest)
    if length <= PRINTED_TEXT_LIMIT:
        return length, hashlib.sha256(str(node).encode("utf-8")).hexdigest()
    return length, hashlib.sha256(("\1" + joined("", pieces)).encode("utf-8")).hexdigest()


# The printed lengths and digests of hash-consed nodes (types, components,
# kinds) without metavariables, by id, kept with the node so that its id is not
# reused
_PRINTED_PARTS: dict[int, tuple[Any, tuple[int, str]]] = {}


def printed(node: Any) -> tuple[int, str]:
    """The length of str(node) and a digest of that text, for a type, type
    component, or kind."""
    node = pruned(node)
    if node._has_meta:
        return _printed_uncached(node)
    entry = _PRINTED_PARTS.get(id(node))
    if entry is None or entry[0] is not node:
        entry = (node, _printed_uncached(node))
        _PRINTED_PARTS[id(node)] = entry
    return entry[1]
