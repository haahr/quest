"""Generic layouts: whether generic code's layout of a value agrees with the
native one, which decides where values are converted between them
(docs/c-representation.md §6.4), and the layouts of module abstract types'
applications, over layout.py.

The self-hosted counterpart is questlang/repr/genericlayout.
"""

from __future__ import annotations

from typing import Optional
from quest.repr.shapes import Shape, shape
from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    QAliasType,
    QExternalType,
    QRecordType,
    QType,
    QTypeApp,
    QTypeFun,
    QTypeVar,
    is_type_equal,
    pruned,
)
from quest.modules.abstract_types import abstract_type_by_symbol, is_abstract_type_symbol
from quest.repr.layout import own_view, is_word_type, representation, shape_location_representation, shape_representation


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
    if kind in ("array", "exception"):
        # An exception's payload is raised in a QVal word, read as a slot
        return slot(s.element)
    if kind in ("cell", "out"):
        return _generic_layout_agrees(s.element, subst, _CELL, seen)
    if kind == "fun":
        return all(
            _generic_layout_agrees(p.shape, subst, _REGISTER if p.mode == "value" else _CELL, seen) for p in s.params
        ) and _generic_layout_agrees(s.result, subst, _REGISTER, seen)
    if kind == "all":
        return _generic_layout_agrees(s.body, subst, place, seen)
    # Anything else that mentions a type parameter (auto types, path types) may
    # differ
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


def abstract_instance(t: QType) -> Optional[tuple[QType, dict[int, QType]]]:
    """For an application of a module's abstract type operator whose
    representation is known (the module was elaborated from its source): the
    representation's body, generic in the operator's parameters, and the
    arguments substituted for them. Outside the module, its values are laid out
    as the body is by generic code (docs/c-representation.md §5.1)."""
    t = pruned(t)
    if not isinstance(t, QTypeApp):
        return None
    symbol_id = getattr(pruned(t.constructor), "symbol_id", None)
    if symbol_id is None or not is_abstract_type_symbol(symbol_id):
        return None
    entry = abstract_type_by_symbol(symbol_id)
    if entry is None or entry.rep is None:
        return None
    rep = shape(entry.rep).type
    if not isinstance(rep, QTypeFun) or len(rep.params) != len(t.arguments):
        return None
    return rep.body, {p.symbol_id: a for p, a in zip(rep.params, t.arguments)}


def abstract_layouts_differ(t: QType) -> bool:
    """Whether a value of type t is or holds an application of an abstract type
    operator laid out at its arguments otherwise than generically: the module's
    code at those arguments and the code outside it lay it out differently, as a
    closure whose C signature changes with them."""
    seen: set[int] = set()

    def visit(s: Optional[Shape]) -> bool:
        if s is None or id(s) in seen:
            return False
        seen.add(id(s))
        if s.kind == "abstract":
            instance = abstract_instance(s.type)
            if instance is not None:
                return not generic_layout_agrees(*instance)
        inner = [c.shape for c in s.components] + [c.shape for c in s.cases] + [p.shape for p in s.params]
        return any(visit(x) for x in inner + [s.element, s.result, s.body])

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
