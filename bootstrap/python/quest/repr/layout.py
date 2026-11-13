"""How values are laid out, for every backend (docs/c-representation.md),
computed from shapes (repr/shapes.py) and cached per shape: each type's layout
tag (which names its struct and descriptor; digests.py's digests tell apart the
types it conflates), and its representation, the runtime's
(runtime/quest_runtime.h): a scalar, a QVal word, a 16-byte record or variant
value, or a pointer (to a tuple's or option's struct, a closure, an array, ...),
and its slot representation, as an aggregate slot or a QVal word holds it
(slot_representation): a record or variant as a pointer to an immutable 16-byte
box, a Bool or Char in a word of its own, and anything else as its
representation, so that every slot is one word and native and generic layouts
agree in memory. Representations are named by the runtime's C types, which a
native backend lays out as C does, to share the runtime and link with C units.
Also whether a value of a tuple or option type may be a proxy, a view of an
object of a subtype (may_be_proxied). Whether generic code's layout of a type
agrees with the native one is generic_layout.py's.

The self-hosted counterpart is questlang/repr/layout."""

from __future__ import annotations

import hashlib
from quest.repr.syntax import c_int, joined
from quest.repr.shapes import Shape, shape
from quest.types.canonical import is_rec_self_symbol, rec_self_level, rec_self_var
from quest.types import (
    QRecType,
    QType,
    auto_payload_type,
)
from quest.modules.abstract_types import is_abstract_type_symbol


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
    QCharSlot), an Ok the word Q_OK_VAL (a QVal, since an Ok value has no C
    type of its own: a function returning Ok returns void), and any other
    value as it is (docs/c-representation.md §5).
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
    "void": "QVal",
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


def tuple_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QTupleType."""
    return type_tag(t)


def option_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QOptionType."""
    return type_tag(t)
