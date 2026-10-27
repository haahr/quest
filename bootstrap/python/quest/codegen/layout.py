"""How values are laid out, for every backend (docs/c-representation.md),
computed from shapes (ir/shapes.py) and cached per shape: each type's layout tag
(which names its struct and descriptor), digests and identity keys of types, and
its representation, the runtime's (runtime/quest_runtime.h): a scalar, a QVal
word, a 16-byte record or variant value, or a pointer (to a tuple's or option's
struct, a closure, an array, ...), and its slot representation, as an aggregate
slot or a QVal word holds it (slot_representation): a record or variant as a
pointer to an immutable 16-byte box, a Bool or Char in a word of its own, and
anything else as its representation, so that every slot is one word and native
and generic layouts agree in memory. Representations are named by the runtime's
C types, which a native backend lays out as C does, to share the runtime and
link with C units. Also whether generic code's layout of a type agrees with the
native one (generic_layout_agrees), and whether a value of a tuple or option
type may be a proxy, a view of an object of a subtype (may_be_proxied)."""

from __future__ import annotations

import hashlib
from typing import Any, Optional

from quest.codegen.syntax import c_int, joined
from quest.ir.shapes import Shape, shape
from quest.types.canonical import is_rec_self_symbol, rec_self_level, rec_self_var
from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAliasType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
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
    QTypeVar,
    QVarType,
    QVariantField,
    QVariantType,
    auto_payload_type,
    is_type_equal,
    pruned,
)
from quest.modules.abstract_types import is_abstract_type_symbol


# ============================================================================
# Layouts of shapes
# ============================================================================
#
# A type's layout (its tag and representation) depends only on its shape, and
# shapes are built once per canonical type, so each layout is computed once per
# shape and kept for the whole process.


_UNSET = object()


class Layout:
    """The layout of one shape; each part is computed on first use."""

    __slots__ = ("shape", "_tag", "_representation", "_slot", "_proxied")

    def __init__(self, s: Shape) -> None:
        self.shape = s
        self._tag = self._representation = self._slot = self._proxied = _UNSET

    @property
    def tag(self) -> str:
        if self._tag is _UNSET:
            raw = _shape_tag(self.shape)
            if len(raw) > 64:
                digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
                raw = f"{raw[:24]}_{digest}"
            self._tag = raw
        return self._tag

    @property
    def representation(self) -> str:
        if self._representation is _UNSET:
            self._representation = _shape_representation(self.shape)
        return self._representation

    @property
    def proxied(self) -> bool:
        if self._proxied is _UNSET:
            self._proxied = _may_be_proxied(self.shape, set())
        return self._proxied

    @property
    def slot(self) -> str:
        if self._slot is _UNSET:
            self._slot = _SLOT_REPRESENTATIONS.get(self.representation, self.representation)
        return self._slot


# Layouts by the id of their shape (shapes are kept for the whole process, so
# ids are not reused)
_LAYOUTS: dict[int, Layout] = {}


def layout_of(s: Shape) -> Layout:
    """The layout of a shape, shared by every type of that shape."""
    entry = _LAYOUTS.get(id(s))
    if entry is None:
        entry = _LAYOUTS[id(s)] = Layout(s)
    return entry


def resolved_shape(s: Shape) -> Shape:
    """s, or for a type variable or abstract type bounded by POWER(T), the shape
    its bounds resolve to: generic code holds a value of a bounded type
    parameter as a value of its bound."""
    seen: set[int] = set()
    while s.kind in ("typevar", "abstract") and s.bound is not None and id(s) not in seen:
        seen.add(id(s))
        s = s.bound
    return s


def held_at_bound(s: Shape) -> bool:
    """Whether values of shape s, of a type with a bound, are held viewed at the
    bound: a module's abstract type (as code outside the module holds it), an
    abstract type elaborated as such, or a path type. Generic code holds the
    values of a bounded type parameter at their own view, their type argument's,
    in the representation of the bound (docs/c-representation.md §5.1)."""
    if s.bound is None or s.kind not in ("typevar", "abstract"):
        return False
    if s.kind == "abstract":
        return True

    return is_abstract_type_symbol(s.symbol_id)


def own_view(s: Shape) -> bool:
    """Whether s is a bounded type parameter's shape, whose values generic code
    holds at their own view (their type argument's) and reads through the bound
    by a view map (ir.ViewMapParam) when the bound is a record, variant, or
    option type."""
    return s.kind == "typevar" and s.bound is not None and not held_at_bound(s)


def is_word_type(t: QType) -> bool:
    """Returns True if t is the standard library Word.T type."""
    return shape(t).kind == "word"


def representation(t: QType) -> str:
    """The representation of a value of t, named by the runtime's C type for it
    (`QInt`, `QVal`, `QRecordVal`, a tuple's struct pointer `QTuple_Int_Real *`,
    ...): values of types with the same representation are laid out alike."""
    return layout_of(shape(t)).representation


def slot_representation(t: QType) -> str:
    """The C type of a value of t in an aggregate slot (a tuple component,
    option payload, record field, array element, or auto payload) or a QVal
    word: a record or variant is a pointer to an immutable 16-byte box
    (QRecordVal *, QVariantVal *), a Bool or Char a word of its own (QBoolSlot,
    QCharSlot), and any other value as it is (docs/c-representation.md §5).
    Every slot is one word, so a slot of a type parameter (a QVal) agrees in
    memory with a slot of its type argument."""
    return layout_of(shape(t)).slot


def shape_slot_representation(s: Shape) -> str:
    """The slot representation of the values of shape s (see
    slot_representation)."""
    return layout_of(s).slot


def location_representation(t: QType) -> str:
    """The C type of the location a var or out parameter points to (or a Var
    cell is): a record or variant boxed, as a slot holds it, so that the address
    of a slot can be passed, and a generic parameter's location (a QVal) agrees
    with it; any other value as its representation."""
    return shape_location_representation(shape(t))


def shape_location_representation(s: Shape) -> str:
    """The location representation of the values of shape s (see
    location_representation)."""
    return layout_of(s).slot if is_boxed_in_slots(s) else layout_of(s).representation


def may_be_proxied(s: Shape) -> bool:
    """Whether a value of shape s, a tuple or option, may be a proxy
    (docs/c-representation.md §5.8): a view of an object of a subtype at which
    some component changes view, so that reading a component may have to convert
    it. A tuple may be when one of its components may change view (see
    changes_view); an option when it has two or more cases (a subtype numbers
    them differently) or one of its payloads' components may change view. Code
    reading a component of such a value checks for a proxy; a value of any other
    type is never one."""
    return s.kind in ("tuple", "option") and layout_of(s).proxied


def changes_view(s: Shape) -> bool:
    """Whether a component of shape s may change view when its tuple or option
    is upcast: it is view-sensitive (see _view_sensitive), or an aggregate a
    subtype's value of which may be a proxy where a value of s is never one (see
    _holds_proxies). One that may not is read through a proxy from the
    original's slot as it is (every slot being a word, at the same offset)."""
    return _component_changes_view(s, set())


def _holds_proxies(s: Shape) -> bool:
    """Whether a component of shape s may hold a proxy as a subtype's value,
    though a value of s itself may not be a proxy: a tuple (a prefix of a tuple
    with a component that changes view), or an option with a payload (whose
    payload's components may be subtypes'). Upcasting a tuple or option holding
    such a component to a type at which it is never a proxy converts it, so its
    tuple or option may be a proxy too."""
    return s.kind == "tuple" or (s.kind == "option" and any(c.shape is not None for c in s.cases))


def _component_changes_view(s: Shape, seen: set[int]) -> bool:
    return _holds_proxies(s) or _view_sensitive(s, seen)


def _view_sensitive(s: Shape, seen: set[int]) -> bool:
    """Whether values of subtypes of s may be represented differently at s (so
    that a component of this shape may change view when its tuple or option is
    upcast): records and variants (offset tables, tags), options of several
    cases, tuples and options that may be proxies, type variables (whose
    arguments may be any of these, or which are viewed at their bounds), and
    functions whose signatures mention any of these (adapted)."""
    kind = s.kind
    if kind in ("record", "variant", "typevar", "abstract", "auto", "operator"):
        return True
    if kind in ("tuple", "option"):
        return _may_be_proxied(s, seen)
    if kind in ("fun", "all"):
        if id(s) in seen:
            return False
        seen.add(id(s))
        if kind == "all":
            return True
        return any(_view_sensitive(p.shape, seen) for p in s.params) or _view_sensitive(s.result, seen)
    return False


def _may_be_proxied(s: Shape, seen: set[int]) -> bool:
    if id(s) in seen:
        return False
    seen.add(id(s))
    if s.kind == "tuple":
        return any(_component_changes_view(c.shape, seen) for c in s.components)
    if s.kind == "option":
        if len(s.cases) >= 2:
            return True
        return any(
            c.shape is not None and any(_component_changes_view(pc.shape, seen) for pc in c.shape.components)
            for c in s.cases if c.shape is not None and c.shape.kind == "tuple"
        )
    return False


def is_boxed_in_slots(s: Shape) -> bool:
    """Whether a slot holds values of shape s boxed: records and variants (a
    bounded type parameter's, viewed at its bound, among them)."""
    return layout_of(s).representation in ("QRecordVal", "QVariantVal")


def type_tag(t: QType) -> str:
    """Produces a deterministic, valid C identifier component for a QType."""
    return layout_of(shape(t)).tag


def shape_tag(s: Shape) -> str:
    """The tag of the types of shape s (see type_tag)."""
    return layout_of(s).tag


def shape_representation(s: Shape) -> str:
    """The representation of the values of shape s (see representation)."""
    return layout_of(s).representation


_SLOT_REPRESENTATIONS = {
    "QRecordVal": "QRecordVal *", "QVariantVal": "QVariantVal *", "QBool": "QBoolSlot", "QChar": "QCharSlot",
}

_SCALAR_TAGS = {"int": "Int", "real": "Real", "bool": "Bool", "char": "Char", "string": "String", "ok": "Ok"}
_SCALAR_REPRESENTATIONS = {
    "int": "QInt", "real": "QReal", "bool": "QBool", "char": "QChar", "string": "QString *", "ok": "void",
}


def _recursive_tag(s: Shape) -> str:
    """The tag of a recursive type whose unfolding's tag is built from its
    parts' tags (a tuple, record, variant, option, array, cell, or auto type).

    The tag names the recursive type itself rather than its unfolding, whose tag
    would contain the tag being defined: its body, its variable replaced by a
    placeholder numbered by nesting depth, so that the tag is finite and the
    same for alpha-equivalent types.
    """
    t = s.type
    level = sum(1 for sym in t._fv if is_rec_self_symbol(sym))
    if isinstance(t, QRecType):
        body = t.body.substitute({t.symbol_id: rec_self_var(level)})
        return f"Rec{c_int(level)}_{type_tag(body)}"
    subst = {b[1]: rec_self_var(level + i) for i, b in enumerate(t.bindings)}
    tags = [type_tag(b[3].substitute(subst)) for b in t.bindings]
    return f"RecGroup{c_int(level)}_{c_int(t.active_index)}_" + joined("_", tags)


_SELF_NAMED_KINDS = ("tuple", "record", "variant", "option", "array", "cell", "out", "auto")
_AGGREGATE_TAG_PREFIXES = ("QTuple_", "QRecord_", "QVariant_", "QOption_", "Auto_")


def _element_tag(s: Shape) -> str:
    """The tag of a component's shape inside another type's tag: an aggregate's
    tag, which lists its own components, is closed with _end, so that tags of
    different nestings differ (Tuple (Tuple A Int) end and Tuple (Tuple A) Int
    end)."""
    tag = _component_tag(s)
    if tag.startswith(_AGGREGATE_TAG_PREFIXES) and not tag.endswith("_empty"):
        return f"{tag}_end"
    return tag


def _component_tag(s: Shape) -> str:
    # A component is named as its type is: a type containing recursion by its
    # own canonical form, which a part of another type's canonical form need not
    # be
    return shape_tag(shape(s.type))


def _shape_tag(s: Shape) -> str:
    """The tag of shape s, before Layout.tag shortens it: a C identifier made
    from the structure of its type, which names the type's struct, descriptor,
    and tables in C. A tag longer than 64 characters is shortened to its first
    24, an underscore, and 16 hex digits of its SHA-256 digest.

    A tag depends only on the type, not on the unit or the order in which
    types are met, so that separately compiled units name a type alike and
    agree on its struct. Equal types have one tag: a type containing recursion
    is named by its canonical form, and cases and record fields are listed in
    the order of their names. For example,

        Tuple :Int :Int end               QTuple_Int_Int
        Tuple end                         QTuple_empty
        Record y: Bool x: Int end         QRecord_x_Int_y_Bool
        Variant red: Ok green: Int end    QVariant_green_Int_red_Ok
        Array(String)                     QArray_String
        All(x: Int) Int                   QClosure
        List(Int)
            Rec0_QOption_cons_QTuple_Int_Self0_end_nil
        Tuple :Tuple :Int :Bool end :String end
            QTuple_QTuple_Int_Bool_end_String
        Tuple :Tuple :Int end :Bool :String end
            QTuple_QTuple_Int_end_Bool_String

    A tuple's tag lists its components' tags but not their names, which do not
    change its layout: Tuple x: Int y: Int end is QTuple_Int_Int too. An
    aggregate's tag nested in another's ends with _end, so that the last two
    tuples above, which nest differently, have different tags. A
    recursive tuple, record, variant, option, array, or auto type is named by
    its body, with Self and its nesting depth for its recursion variable
    (_recursive_tag), so that its tag is finite. Every function type is
    QClosure, since every closure has one representation, and a type it does
    not otherwise name is QVal."""
    s = resolved_shape(s)
    if s.kind == "typevar" and (self_level := rec_self_level(s.type)) is not None:
        return f"Self{c_int(self_level)}"
    if (canonical := shape(s.type)) is not s:
        # Equal types share a tag: a type containing recursion is named by its
        # canonical form
        return shape_tag(canonical)
    if s.is_recursive and s.kind in _SELF_NAMED_KINDS:
        return _recursive_tag(s)
    kind = s.kind
    if kind == "word":
        return "Word"
    if kind in _SCALAR_TAGS:
        return _SCALAR_TAGS[kind]
    if kind == "external":
        t = s.type
        return t.name.replace(".", "_") if t.name else t.c_type.replace("*", "").strip()
    if kind == "typevar" and s.name in ("Writer.T", "writer.T"):
        return "QWriter"
    if kind == "typevar" and s.name in ("Reader.T", "reader.T"):
        return "QReader"
    if kind == "tuple":
        tags = [_element_tag(c.shape) for c in s.components]
        return "QTuple_" + (joined("_", tags) if tags else "empty")
    if kind == "record":
        tags = [f"{c.name}_{_element_tag(c.shape)}" for c in s.sorted_components()]
        return "QRecord_" + (joined("_", tags) if tags else "empty")
    if kind in ("fun", "all"):
        return "QClosure"
    if kind in ("cell", "out"):
        return f"Ref_{_element_tag(s.element)}"
    if kind == "array":
        return f"QArray_{_element_tag(s.element)}"
    if kind in ("variant", "option"):
        tags = [f"{c.name}_{_element_tag(c.shape)}" if c.shape is not None else c.name for c in s.cases]
        return ("QVariant_" if kind == "variant" else "QOption_") + (joined("_", tags) if tags else "empty")
    if kind == "exception":
        return "QException"
    if kind == "auto":
        return "Auto_" + type_tag(auto_payload_type(s.structure))
    return "QVal"


def _shape_representation(s: Shape) -> str:
    s = resolved_shape(s)
    kind = s.kind
    if kind == "word":
        return "uint64_t"
    if kind in _SCALAR_REPRESENTATIONS:
        return _SCALAR_REPRESENTATIONS[kind]
    if kind == "auto":
        # An auto value (including a dynamic value): its type component's
        # descriptor and its payload
        return "QAuto *"
    if kind == "external":
        return s.name
    if kind == "typevar" and s.name in ("Writer.T", "writer.T"):
        return "QWriter *"
    if kind == "typevar" and s.name in ("Reader.T", "reader.T"):
        return "QReader *"
    if kind in ("tuple", "option"):
        return f"{shape_tag(s)} *"
    if kind == "record":
        return "QRecordVal"
    if kind in ("fun", "all"):
        return "QClosure *"
    if kind == "array":
        return "QArray *"
    if kind == "variant":
        return "QVariantVal"
    if kind == "exception":
        return "const QException *"
    if kind in ("cell", "out"):
        return f"{shape_location_representation(s.element)} *"
    return "QVal"


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


def tuple_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QTupleType."""
    return type_tag(t)


def option_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QOptionType."""
    return type_tag(t)


# The C types of scalar values, which a slot holds in a word of its own: stored
# as a bounded type parameter's value (of the same scalar bound), they agree
# with the native value in memory, and in registers only for integers
_WORD_SCALARS = frozenset({"QInt", "QReal", "QBool", "QChar", "QVal", "void"})


_REGISTER_WORDS = frozenset({"QInt", "QVal"})

# The C types of native values that a QVal cell holds in the same eight bytes (a
# var or out parameter points to one)
_CELL_WORDS = frozenset({"QInt", "QReal", "QVal", "uint64_t"})

# Where a value is held: in an aggregate slot, in a register (a function's
# parameter or result), or in a cell that a var or out parameter points to (a
# local variable natively, of its location representation: a record or variant
# boxed, as in a slot)
_SLOT, _REGISTER, _CELL = "slot", "register", "cell"


def generic_layout_agrees(t: QType, subst: dict[int, QType]) -> bool:
    """Whether a value of t.substitute(subst), laid out natively, is laid out as
    generic code lays out t, where each variable in subst is a type parameter of
    that code: so that the value can be used there as it is, through a pointer
    cast, and a value made there can be used natively.

    Generic code stores a value of an unbounded type parameter as a QVal, and
    one of a bounded parameter as its type argument's own value, in the
    representation of the bound. Every slot is one word (slot_representation),
    so in memory a QVal agrees with any native value: a scalar or pointer in its
    bits, a record or variant boxed. In registers (function parameters and
    results) it agrees only with integers and pointers, and in the cell a var or
    out parameter points to (natively a variable of the value's representation)
    only with eight-byte scalars and pointers. A value of a bounded parameter
    agrees with the native value (which has the bound's representation). A
    module's abstract type's value is held viewed at its bound, which agrees
    with a native value only when both are the same scalar. Aggregates agree
    when their components do; recursive types are compared coinductively. This
    mirrors quest_layout_equivalent in the runtime, conservatively: False means
    only that the value may need converting.
    """
    if not subst:
        return True
    return _generic_layout_agrees(shape(t), subst, _SLOT, set())


def _mentions(s: Shape, subst: dict[int, QType]) -> bool:
    """Whether the type of shape s mentions one of the type parameters in subst
    (free type variables keep their symbols in canonical forms)."""
    return bool(s.type._fv & subst.keys())


def _stored_value_agrees(var: Shape, arg: QType, place: str) -> bool:
    """Whether a native value of arg agrees with a value of the type parameter
    of shape var as generic code holds it in the place (_SLOT, _REGISTER, or
    _CELL)."""
    arg_c = representation(arg)
    if var.bound is not None and own_view(var):
        # Held as arg's own value, in the representation of the bound, which
        # arg's is (a pointer to another struct holds the same object)
        bound_c = shape_representation(var.bound)
        return arg_c == bound_c or (arg_c.endswith("*") and bound_c.endswith("*"))
    if var.bound is not None:
        # Held as a value of the bound, viewed at it, which agrees with one of
        # arg only when both are the same scalar
        return arg_c == shape_representation(var.bound) and arg_c in _WORD_SCALARS and (
            place != _REGISTER or arg_c in _REGISTER_WORDS
        )
    if place == _REGISTER:
        return arg_c in _REGISTER_WORDS or arg_c.endswith("*")
    if place == _CELL:
        # A cell holds a record or variant boxed, as a QVal does
        return arg_c in _CELL_WORDS or arg_c.endswith("*") or arg_c in ("QRecordVal", "QVariantVal")
    return True


def _type_parameter(s: Shape) -> Optional[int]:
    """The symbol of the type variable s is the shape of (a type parameter
    bounded by Word.T is a word shape), or None."""
    return s.type.symbol_id if isinstance(s.type, QTypeVar) else None


def _generic_layout_agrees(s: Shape, subst: dict[int, QType], place: str, seen: set[int]) -> bool:
    if not _mentions(s, subst):
        return True
    if (symbol := _type_parameter(s)) is not None:
        return _stored_value_agrees(s, subst[symbol], place) if symbol in subst else True
    if s.is_recursive:
        if id(s) in seen:
            return True
        seen.add(id(s))

    def slot(component: Shape) -> bool:
        return _generic_layout_agrees(component, subst, _SLOT, seen)

    kind = s.kind
    if kind == "abstract" and isinstance(s.type, QTypeApp):
        # An application of an abstract operator, whose values are opaque
        # pointers
        return True
    if kind in ("tuple", "record"):
        return all(slot(c.shape) for c in s.components)
    if kind in ("variant", "option"):
        return all(c.shape is None or slot(c.shape) for c in s.cases)
    if kind == "array":
        return slot(s.element)
    if kind in ("cell", "out"):
        return _generic_layout_agrees(s.element, subst, _CELL, seen)
    if kind == "fun":
        return all(
            _generic_layout_agrees(p.shape, subst, _REGISTER if p.mode == "value" else _CELL, seen) for p in s.params
        ) and _generic_layout_agrees(s.result, subst, _REGISTER, seen)
    if kind == "all":
        return _generic_layout_agrees(s.body, subst, place, seen)
    # Anything else that mentions a type parameter (auto types, exception types,
    # path types) may differ
    return False


def generic_layout_copies_mutable_data(t: QType, subst: dict[int, QType]) -> bool:
    """Whether converting a value of t between the generic layout and the native
    one at subst (see generic_layout_agrees) would copy mutable data whose
    layouts differ: an array, a Var cell, or a var component holding a value
    that does not agree. The copy would not share the original's updates."""
    seen: set[int] = set()

    def disagrees(component: Shape, place: str = _SLOT) -> bool:
        return not _generic_layout_agrees(component, subst, place, set())

    def visit(s: Shape) -> bool:
        if not _mentions(s, subst):
            return False
        if s.is_recursive:
            if id(s) in seen:
                return False
            seen.add(id(s))
        kind = s.kind
        if kind == "array":
            return disagrees(s.element) or visit(s.element)
        if kind in ("cell", "out"):
            return disagrees(s.element, _CELL) or visit(s.element)
        if kind == "tuple":
            # A tuple is converted through a proxy, which reads and writes its
            # original's components
            return any(visit(c.shape) for c in s.components)
        if kind == "record":
            return any((c.is_var and disagrees(c.shape)) or visit(c.shape) for c in s.components)
        if kind == "variant":
            return any(c.shape is not None and ((c.is_var and disagrees(c.shape)) or visit(c.shape)) for c in s.cases)
        if kind == "option":
            return any(c.shape is not None and visit(c.shape) for c in s.cases)
        # Closures are adapted rather than copied
        return False

    return visit(shape(t))


def signature_representation(t: QType) -> tuple:
    """The representation of a function type's calls: its result's and its
    parameters' representations (pointers for var and out parameters) and its
    number of type parameters, which closures of types with the same signature
    representation are called by alike."""
    s = shape(t)
    count = 0
    while s.kind == "all":
        count += len(s.type_params)
        s = s.body
    params = s.params if s.kind == "fun" else ()
    result = s.result if s.kind == "fun" else s
    return (
        shape_representation(result),
        count,
        tuple(f"{shape_location_representation(p.shape)} *" if p.mode != "value"
              else "QVal" if p.shape.kind == "ok" else shape_representation(p.shape) for p in params),
    )


def qtype_to_name_str(t: QType) -> str:
    """Returns the human-readable Quest type name string for runtime diagnostics
    and printing (with its alias name, which only the type as written has)."""
    t = pruned(t)
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

