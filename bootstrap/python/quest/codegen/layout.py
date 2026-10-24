"""How values are laid out, for every backend (docs/c-representation.md): each type's normalized form, its layout's
tag (which names its struct and descriptor), digests and identity keys of types, and its representation, the
runtime's (runtime/quest_runtime.h): a scalar, a QVal word, a 16-byte record or variant value, or a pointer (to a
tuple's or option's struct, a closure, an array, ...). Representations are named by the runtime's C types, which a
native backend lays out as C does, to share the runtime and link with C units. Also whether generic code's layout of
a type agrees with the native one (generic_layout_agrees)."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from quest.types.canonical import (
    SELF_NAMED,
    beta_reduce_head,
    canonical_type,
    is_rec_self_symbol,
    rec_self_level,
    rec_self_var,
    unfold_recursive,
)
from quest.types import (
    QAliasType,
    strip_aliases,
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAbstractType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionField,
    QOptionType,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
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
    QTypeVar,
    QVarType,
    QOutType,
    QVariantField,
    QVariantType,
    resolve_record_bound,
    resolve_variant_bound,
    resolve_option_bound,
    is_type_equal,
    auto_payload_type,
    QParam,
)


def _normalize_type_raw(t: QType) -> QType:
    t = t.prune() if hasattr(t, "prune") else t
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
    """Unwraps upper bounds for path types and type variables bounded by POWER(T)."""
    curr = t.prune() if hasattr(t, "prune") else t
    curr = strip_aliases(curr)
    visited = set()
    while isinstance(curr, (QTypeVar, QAbstractType, QPathType)) and isinstance(curr.bound, QPowerKind):
        sym_id = getattr(curr, "symbol_id", id(curr))
        if sym_id in visited:
            break
        visited.add(sym_id)
        curr = curr.bound.bound
        curr = curr.prune() if hasattr(curr, "prune") else curr
    return curr


def _is_word_type_raw(t: QType) -> bool:
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = _normalize_type_raw(t)
    if isinstance(t, QTypeVar) and t.name in ("Word.T", "word.T"):
        return True
    if isinstance(t, QPathType) and t.field_name == "T" and t.root_name in ("Word", "word"):
        return True
    if isinstance(t, QExternalType) and (t.name in ("Word.T", "word.T") or t.c_type == "uint64_t"):
        return True
    return False


def _type_tag_uncached(t: QType) -> str:
    raw = _type_tag_raw(t)
    if len(raw) > 64:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{raw[:24]}_{digest}"
    return raw


def _recursive_tag(t: QType) -> Optional[str]:
    """Returns the tag of a recursive type whose unfolding's tag is built from its parts' tags (SELF_NAMED), or None
    otherwise.

    The tag names the recursive type itself rather than its unfolding, whose tag would contain the tag being defined.
    """
    if unfold_recursive(t, SELF_NAMED) is None:
        return None
    if isinstance(t, QTypeApp):
        t = beta_reduce_head(t)
    level = sum(1 for sym in t._fv if is_rec_self_symbol(sym))
    if isinstance(t, QRecType):
        body = t.body.substitute({t.symbol_id: rec_self_var(level)})
        return f"Rec{level}_{type_tag(body)}"
    if isinstance(t, QRecGroupType):
        subst = {b[1]: rec_self_var(level + i) for i, b in enumerate(t.bindings)}
        tags = [type_tag(b[3].substitute(subst)) for b in t.bindings]
        return f"RecGroup{level}_{t.active_index}_" + "_".join(tags)
    return None


_AGGREGATE_TAG_PREFIXES = ("QTuple_", "QRecord_", "QVariant_", "QOption_", "Auto_")


def _element_tag(t: QType) -> str:
    """The tag of a component type inside another type's tag: an aggregate's tag, which lists its own components,
    is closed with _end, so that tags of different nestings differ (Tuple (Tuple A Int) end and Tuple (Tuple A) Int
    end)."""
    tag = type_tag(t)
    if tag.startswith(_AGGREGATE_TAG_PREFIXES) and not tag.endswith("_empty"):
        return f"{tag}_end"
    return tag


def _type_tag_raw(t: QType) -> str:
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    t = resolve_type_bound(t)
    if (self_level := rec_self_level(t)) is not None:
        return f"Self{self_level}"
    if (canonical := canonical_type(t)) is not None:
        # Equal types share a tag: a type containing recursion is named by its canonical form
        return type_tag(canonical)
    if (rec_tag := _recursive_tag(t)) is not None:
        return rec_tag
    t = _normalize_type_raw(t)
    if _is_word_type_raw(t):
        return "Word"
    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if isinstance(t, QExternalType):
        return t.name.replace(".", "_") if t.name else t.c_type.replace("*", "").strip()
    if isinstance(t, QTypeVar) and t.name in ("Writer.T", "writer.T"):
        return "QWriter"
    if isinstance(t, QTypeVar) and t.name in ("Reader.T", "reader.T"):
        return "QReader"
    if isinstance(t, QTupleType):
        tags = [_element_tag(f.type_val) for f in t.value_fields]
        return "QTuple_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, QRecordType):
        sorted_fields = sorted(t.fields, key=lambda f: f.name)
        tags = [f"{f.name}_{_element_tag(f.type_val)}" for f in sorted_fields]
        return "QRecord_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, (QFunType, QAllType)):
        return "QClosure"
    if isinstance(t, (QVarType, QOutType)):
        return f"Ref_{_element_tag(t.element_type)}"
    if isinstance(t, (QTypeVar, QAbstractType, QPathType)):
        return "QVal"
    if isinstance(t, QArrayType):
        return f"QArray_{_element_tag(t.element_type)}"
    if isinstance(t, QVariantType):
        tags = []
        for v in t.variants:
            if v.type_val:
                tags.append(f"{v.name}_{_element_tag(v.type_val)}")
            else:
                tags.append(v.name)
        return "QVariant_" + ("_".join(tags) if tags else "empty")
    if isinstance(t, QExceptionType):
        return "QException"
    if isinstance(t, QAutoType):
        return "Auto_" + type_tag(auto_payload_type(t))
    if isinstance(t, QOptionType) or (opt_bound := resolve_option_bound(t)) is not None:
        opt_t = t if isinstance(t, QOptionType) else opt_bound
        tags = []
        for o in opt_t.options:
            if o.payload_type:
                tags.append(f"{o.name}_{_element_tag(o.payload_type)}")
            else:
                tags.append(o.name)
        return "QOption_" + ("_".join(tags) if tags else "empty")
    return "QVal"


def type_digest(t: QType) -> str:
    """A short digest of a type's printed text, telling apart types that type_tag conflates (see printed)."""
    t = normalize_type(strip_aliases(t.prune() if hasattr(t, "prune") else t))
    if (canonical := canonical_type(t)) is not None:
        t = normalize_type(canonical)
    return printed(t)[1][:16]


def type_identity_key(t: QType) -> str:
    """A key telling types apart where type_tag does not (all function types are QClosure): the tag and a
    digest of the canonical type's text. Equal types elaborated separately get the same key; Python == is not
    defined on types, so this stands in for them in dictionaries."""
    return f"{type_tag(t)}#{type_digest(t)}"


def text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# Digests of types stand for their printed text (str), which is the same in every compilation, but printing
# shares nothing, so a large recursive type prints as megabytes. A type whose text is at most this long is
# digested from its text; a longer one from the text of its outermost node with the digests of its parts
# in place of theirs, computed once per hash-consed node. Either way types that print differently get
# different digests.
PRINTED_TEXT_LIMIT = 1024


def _printed_parts(node: Any) -> list[Any]:
    """The text of str(node) as a list of literal strings and the parts (types, components, kinds) printed
    in between. It mirrors the __str__ methods in quest.types; a node not listed prints as one string."""

    def joined(items: Any) -> list[Any]:
        out: list[Any] = []
        for i, item in enumerate(items):
            if i:
                out.append(" ")
            out.append(item)
        return out

    def framed(head: str, items: Any) -> list[Any]:
        return [f"{head} ", *joined(items), " end"] if items else [f"{head} end"]

    if isinstance(node, QExceptionType):
        return ["Exception"] if node.payload_type is OK_TYPE else ["Exception(", node.payload_type, ")"]
    if isinstance(node, QTupleField):
        prefix = "var " if node.is_var else ""
        return [f"{prefix}{node.name}: " if node.name else f"{prefix}:", node.type_val]
    if isinstance(node, QTupleTypeFormal):
        return [f"{node.name}::", node.bound]
    if isinstance(node, QTupleTypeBinding):
        bound = ["::", node.bound, " "] if node.bound else []
        return [f"Let {node.name}", *bound, "= ", node.type_val]
    if isinstance(node, QTupleType):
        return framed("Tuple", node.fields)
    if isinstance(node, QRecordField):
        return [f"{'var ' if node.is_var else ''}{node.name}: ", node.type_val]
    if isinstance(node, QRecordType):
        if node.provenance:
            return [f"Module '{node.provenance}'"]
        return framed("Record", node.fields)
    if isinstance(node, QVariantField):
        prefix = "var " if node.is_var else ""
        return [f"{prefix}{node.name}: ", node.type_val] if node.type_val else [f"{prefix}{node.name}"]
    if isinstance(node, QVariantType):
        return framed("Variant", node.variants)
    if isinstance(node, QOptionField):
        return [f"{node.name} with ", node.payload_type] if node.payload_type else [node.name]
    if isinstance(node, QOptionType):
        return framed("Option", node.options)
    if isinstance(node, QParam):
        prefix = "var " if node.is_var else ("out " if node.is_out else "")
        return [f"{prefix}{node.name}: ", node.type_val]
    if isinstance(node, QFunType):
        return ["Fun(", *joined(node.params), "): ", node.result_type]
    if isinstance(node, QVarType):
        return ["Var(", node.element_type, ")"]
    if isinstance(node, QArrayType):
        return ["Array(", node.element_type, ")"]
    if isinstance(node, QOutType):
        return ["Out(", node.element_type, ")"]
    if isinstance(node, QQuantifier):
        if isinstance(node.bound, QPowerKind):
            return [f"{node.name} <: ", node.bound.bound]
        return [f"{node.name} :: ", node.bound]
    if isinstance(node, QAllType):
        return ["All(", *joined(node.quantifiers), ") ", node.body]
    if isinstance(node, QAutoType):
        if isinstance(node.kind_bound, QPowerKind):
            head = [f"Auto {node.type_param} <: ", node.kind_bound.bound, " with "]
        else:
            head = [f"Auto {node.type_param} :: ", node.kind_bound, " with "]
        return [*head, *joined(node.signature), " end"]
    if isinstance(node, QTypeFormal):
        return [f"{node.name} :: ", node.bound]
    if isinstance(node, QTypeFun):
        return ["Fun(", *joined(node.params), ") ", node.body]
    if isinstance(node, QTypeApp):
        return [node.constructor, "(", *joined(node.arguments), ")"]
    if isinstance(node, QRecType):
        return [f"Rec({node.var_name} :: ", node.bound, ") ", node.body]
    if isinstance(node, QPowerKind):
        return ["<: ", node.bound]
    if isinstance(node, QAllKind):
        return [f"ALL({node.param_name} :: ", node.param_kind, ") ", node.result_kind]
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
    return length, hashlib.sha256(("\1" + "".join(pieces)).encode("utf-8")).hexdigest()


_PRINTED_PARTS: dict[int, tuple[Any, tuple[int, str]]] = {}


def printed(node: Any) -> tuple[int, str]:
    """The length of str(node) and a digest of that text, for a type, type component, or kind."""
    if isinstance(node, QType):
        return lower_type(node).printed
    if getattr(node, "_has_meta", True):
        return _printed_uncached(node)
    entry = _PRINTED_PARTS.get(id(node))
    if entry is None or entry[0] is not node:
        entry = (node, _printed_uncached(node))
        _PRINTED_PARTS[id(node)] = entry
    return entry[1]


def tuple_struct_name(t: QTupleType) -> str:
    """Returns the C struct tag name for a given QTupleType."""
    return type_tag(t)


def option_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QOptionType."""
    return type_tag(t)


def _representation_raw(t: QType) -> str:
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    t = resolve_type_bound(t)
    t = _normalize_type_raw(t)
    if _is_word_type_raw(t):
        return "uint64_t"
    if t is INT_TYPE:
        return "QInt"
    if t is REAL_TYPE:
        return "QReal"
    if t is BOOL_TYPE:
        return "QBool"
    if t is CHAR_TYPE:
        return "QChar"
    if t is STRING_TYPE:
        return "QString *"
    if t is OK_TYPE:
        return "void"
    if isinstance(t, QAutoType):
        # An auto value (including a dynamic value): its type component's descriptor and its payload
        return "QAuto *"
    if isinstance(t, QExternalType):
        return t.c_type
    if isinstance(t, QTypeVar) and t.name in ("Writer.T", "writer.T"):
        return "QWriter *"
    if isinstance(t, QTypeVar) and t.name in ("Reader.T", "reader.T"):
        return "QReader *"
    if isinstance(t, QTupleType):
        return f"{tuple_struct_name(t)} *"
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return "QRecordVal"
    if isinstance(t, (QFunType, QAllType)):
        return "QClosure *"
    if isinstance(t, QArrayType):
        elem = t.element_type
        if isinstance(elem, QRecordType) or resolve_record_bound(elem) is not None:
            return "QArrayWideRecord *"
        if isinstance(elem, QVariantType) or resolve_variant_bound(elem) is not None:
            return "QArrayWideVariant *"
        return "QArray *"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return "QVariantVal"
    if isinstance(t, QExceptionType):
        return "const QException *"
    if isinstance(t, QOptionType) or (opt_bound := resolve_option_bound(t)) is not None:
        opt_t = t if isinstance(t, QOptionType) else opt_bound
        return f"{option_struct_name(opt_t)} *"
    if isinstance(t, (QVarType, QOutType)):
        return f"{representation(t.element_type)} *"
    if isinstance(t, (QTypeVar, QAbstractType, QPathType)):
        return "QVal"
    return "QVal"


# ============================================================================
# Representation lowering
# ============================================================================
#
# A type's layout (its normalized form, tag, representation, and whether it is Word.T)
# depends only on the type node: the steps that choose it (alias stripping, bound resolution,
# beta reduction, unfolding) read nothing but the node and its children, and the bounds of type
# variables and path types are fields of those nodes. Because types are hash-consed, each
# representation is computed once per canonical node and kept for the whole process. Nodes
# containing a metavariable are lowered afresh every time, since a later solution can change them.


_UNSET = object()


class TypeLayout:
    """The layout of one type; each part is computed on first use."""

    __slots__ = ("type", "_normalized", "_tag", "_representation", "_is_word", "_printed")

    def __init__(self, t: QType) -> None:
        self.type = t
        self._normalized = self._tag = self._representation = self._is_word = self._printed = _UNSET

    @property
    def normalized(self) -> QType:
        if self._normalized is _UNSET:
            self._normalized = _normalize_type_raw(self.type)
        return self._normalized

    @property
    def tag(self) -> str:
        if self._tag is _UNSET:
            self._tag = _type_tag_uncached(self.type)
        return self._tag

    @property
    def representation(self) -> str:
        if self._representation is _UNSET:
            self._representation = _representation_raw(self.type)
        return self._representation

    @property
    def is_word(self) -> bool:
        if self._is_word is _UNSET:
            self._is_word = _is_word_type_raw(self.type)
        return self._is_word

    @property
    def printed(self) -> tuple[int, str]:
        """The length of str(type) and a digest of it (see printed)."""
        if self._printed is _UNSET:
            self._printed = _printed_uncached(self.type)
        return self._printed


_LOWERED: dict[int, TypeLayout] = {}


def lower_type(t: QType) -> TypeLayout:
    """Returns the layout of t, shared by every use of the same canonical type."""
    t = t.prune() if hasattr(t, "prune") else t
    if getattr(t, "_has_meta", True):
        return TypeLayout(t)
    entry = _LOWERED.get(id(t))
    if entry is None or entry.type is not t:
        entry = TypeLayout(t)
        _LOWERED[id(t)] = entry
    return entry


def normalize_type(t: QType) -> QType:
    """Reduces type operator applications so that representations are chosen from the reduced type.

    Applications whose head reduces to a non-recursive type are replaced by that type; applications that
    reduce to a recursive type are only unfolded when the unfolding is a concrete tuple or record type. A recursive
    type whose unfolding is a tuple type is replaced by that unfolding.
    """
    return lower_type(t).normalized


# The C types of values that a QVal holds in its own bits (pointers aside): stored as generic code stores a type
# parameter's value, they agree in memory with the native value, and in registers only for integers
_WORD_SCALARS = frozenset({"QInt", "QReal", "QBool", "QChar", "QVal", "void"})


_REGISTER_WORDS = frozenset({"QInt", "QVal"})


def generic_layout_agrees(t: QType, subst: dict[int, QType]) -> bool:
    """Whether a value of t.substitute(subst), laid out natively, is laid out as generic code lays out t, where each
    variable in subst is a type parameter of that code: so that the value can be used there as it is, through a
    pointer cast, and a value made there can be used natively.

    Generic code stores a value of an unbounded type parameter as a QVal, and one of a bounded parameter as a value of
    the bound. A QVal agrees with a native scalar or pointer in memory, but not with a 16-byte record or variant, and
    in registers (function parameters and results) only with integers and pointers. Aggregates agree when their
    components do; recursive types are compared coinductively. This mirrors quest_layout_equivalent in the runtime,
    conservatively: False means only that the value may need converting.
    """
    if not subst:
        return True
    return _generic_layout_agrees(t, subst, False, set())


def _stored_value_agrees(var: QTypeVar, arg: QType, in_register: bool) -> bool:
    """Whether a native value of arg agrees with a value of the type parameter var as generic code stores it."""
    arg_c = representation(arg)
    bound = var.bound.bound if isinstance(var.bound, QPowerKind) else None
    if bound is not None:
        # Stored as a value of the bound, which agrees with one of arg only when both are the same scalar
        return arg_c == representation(bound) and arg_c in _WORD_SCALARS and (
            not in_register or arg_c in _REGISTER_WORDS
        )
    if arg_c in ("QRecordVal", "QVariantVal"):
        return False
    if in_register:
        return arg_c in _REGISTER_WORDS or arg_c.endswith("*")
    return True


def _generic_layout_agrees(t: QType, subst: dict[int, QType], in_register: bool, seen: set[int]) -> bool:
    if not (getattr(t, "_fv", None) or frozenset()) & subst.keys():
        return True
    if isinstance(t, QTypeVar):
        return _stored_value_agrees(t, subst[t.symbol_id], in_register) if t.symbol_id in subst else True
    if isinstance(t, (QRecType, QRecGroupType, QAliasType)):
        if id(t) in seen:
            return True
        seen.add(id(t))
        if isinstance(t, QAliasType):
            target = t.unfold_lazily() if isinstance(t.target, (QRecType, QRecGroupType)) else t.target
        else:
            target = t.unfold_lazily()
        return _generic_layout_agrees(target, subst, in_register, seen)
    if isinstance(t, QTypeApp):
        reduced = t.evaluate_lazily()
        if reduced is t or isinstance(reduced, QTypeApp):
            # An application of an abstract operator, whose values are opaque pointers
            return True
        return _generic_layout_agrees(reduced, subst, in_register, seen)

    def slot(component: QType) -> bool:
        return _generic_layout_agrees(component, subst, False, seen)

    if isinstance(t, QTupleType):
        return all(slot(f.type_val) for f in t.value_fields)
    if isinstance(t, QRecordType):
        return all(slot(f.type_val) for f in t.fields)
    if isinstance(t, QVariantType):
        return all(v.type_val is None or slot(v.type_val) for v in t.variants)
    if isinstance(t, QOptionType):
        return all(o.payload_type is None or slot(o.payload_type) for o in t.options)
    if isinstance(t, (QArrayType, QVarType, QOutType)):
        return slot(t.element_type)
    if isinstance(t, QFunType):
        return all(
            _generic_layout_agrees(p.type_val, subst, not (p.is_var or p.is_out), seen) for p in t.params
        ) and _generic_layout_agrees(t.result_type, subst, True, seen)
    if isinstance(t, QAllType):
        return _generic_layout_agrees(t.body, subst, in_register, seen)
    # Anything else that mentions a type parameter (auto types, exception types, path types) may differ
    return False


def generic_layout_copies_mutable_data(t: QType, subst: dict[int, QType]) -> bool:
    """Whether converting a value of t between the generic layout and the native one at subst (see
    generic_layout_agrees) would copy mutable data whose layouts differ: an array, a Var cell, or a var component
    holding a value that does not agree. The copy would not share the original's updates."""
    seen: set[int] = set()

    def disagrees(component: QType) -> bool:
        return not _generic_layout_agrees(component, subst, False, set())

    def visit(node: QType) -> bool:
        if not (getattr(node, "_fv", None) or frozenset()) & subst.keys():
            return False
        if isinstance(node, (QRecType, QRecGroupType, QAliasType)):
            if id(node) in seen:
                return False
            seen.add(id(node))
            if isinstance(node, QAliasType) and not isinstance(node.target, (QRecType, QRecGroupType)):
                return visit(node.target)
            return visit(node.unfold_lazily())
        if isinstance(node, QTypeApp):
            reduced = node.evaluate_lazily()
            return reduced is not node and not isinstance(reduced, QTypeApp) and visit(reduced)
        if isinstance(node, (QArrayType, QVarType, QOutType)):
            return disagrees(node.element_type) or visit(node.element_type)
        if isinstance(node, QTupleType):
            return any((f.is_var and disagrees(f.type_val)) or visit(f.type_val) for f in node.value_fields)
        if isinstance(node, QRecordType):
            return any((f.is_var and disagrees(f.type_val)) or visit(f.type_val) for f in node.fields)
        if isinstance(node, QVariantType):
            return any(v.type_val is not None and ((v.is_var and disagrees(v.type_val)) or visit(v.type_val))
                       for v in node.variants)
        if isinstance(node, QOptionType):
            return any(o.payload_type is not None and visit(o.payload_type) for o in node.options)
        # Closures are adapted rather than copied
        return False

    return visit(t)


def is_word_type(t: QType) -> bool:
    """Returns True if t is the standard library Word.T type."""
    return lower_type(t).is_word


def representation(t: QType) -> str:
    """The representation of a value of t, named by the runtime's C type for it (`QInt`, `QVal`, `QRecordVal`, a
    tuple's struct pointer `QTuple_Int_Real *`, ...): values of types with the same representation are laid out
    alike."""
    return lower_type(t).representation


def signature_representation(t: QType) -> tuple:
    """The representation of a function type's calls: its result's and its parameters' representations (pointers
    for var and out parameters) and its number of type parameters, which closures of types with the same signature
    representation are called by alike."""
    quantifiers, inner = collect_fun_quantifiers(t)
    params = inner.params if isinstance(inner, QFunType) else ()
    result_t = inner.result_type if isinstance(inner, QFunType) else inner

    def rep(p_t: QType) -> str:
        if p_t is OK_TYPE:
            return "void"
        return "QRecordVal" if isinstance(p_t, QRecordType) else representation(p_t)

    return (
        rep(result_t),
        len(quantifiers),
        tuple(f"{representation(p.type_val)} *" if p.is_var or p.is_out
              else "QVal" if p.type_val is OK_TYPE else representation(p.type_val) for p in params),
    )


def type_tag(t: QType) -> str:
    """Produces a deterministic, valid C identifier component for a QType."""
    return lower_type(t).tag


def qtype_to_name_str(t: QType) -> str:
    """Returns the human-readable Quest type name string for runtime diagnostics and printing."""
    t = t.prune() if hasattr(t, "prune") else t
    if isinstance(t, QAliasType):
        return t.name
    if is_word_type(t):
        return "word.T"
    if t is INT_TYPE:
        return "Int"
    if t is REAL_TYPE:
        return "Real"
    if t is BOOL_TYPE:
        return "Bool"
    if t is CHAR_TYPE:
        return "Char"
    if t is STRING_TYPE:
        return "String"
    if t is OK_TYPE:
        return "Ok"
    if isinstance(t, QExternalType):
        return t.name or t.c_type
    return str(t)


def is_record_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QRecordType) or not isinstance(t, QRecordType):
        return False
    s_fields = {f.name: f.type_val for f in s.fields}
    for f in t.fields:
        if f.name not in s_fields:
            return False
        s_f_type = s_fields[f.name]
        if s_f_type is not f.type_val and not is_type_equal(s_f_type, f.type_val):
            return False
    return True


def is_tuple_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QTupleType) or not isinstance(t, QTupleType):
        return False
    if len(s.value_fields) < len(t.value_fields):
        return False
    for i in range(len(t.value_fields)):
        s_c = representation(s.value_fields[i].type_val)
        t_c = representation(t.value_fields[i].type_val)
        if s_c != t_c:
            return False
    return True


def is_variant_subtype(s: QType, t: QType) -> bool:
    if not isinstance(s, QVariantType) or not isinstance(t, QVariantType):
        return False
    t_map = {v.name: v.type_val for v in t.variants}
    for v in s.variants:
        if v.name not in t_map:
            return False
        t_v_type = t_map[v.name]
        if v.type_val is not t_v_type and not is_type_equal(v.type_val, t_v_type):
            return False
    return True


def collect_fun_quantifiers(fun_type: QType) -> tuple[tuple[QQuantifier, ...], QType]:
    """Extracts any universal quantifiers wrapping a function type (a recursive one, through its unfolding)."""
    quants: tuple[QQuantifier, ...] = ()
    curr = normalize_type(fun_type)
    while isinstance(curr, QAllType):
        quants = quants + curr.quantifiers
        curr = normalize_type(curr.body)
    return quants, curr
