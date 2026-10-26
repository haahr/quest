"""The IR's types as written (docs/ir.md §4.1): the one place below lowering that looks inside them.

Every IR variable has a Quest type as the program wrote it, with its alias names, so that IR dumps and echo show the
program's names (`let p: Point`, not `let p: Tuple x: Int y: Int end`). Shapes (ir/shapes.py) are what passes decide
by; they keep no alias names, and name the type parameters of polymorphic types afresh. So where a pass makes a
variable of a component's type, plans a closure's conversion by its signature, or echoes a value, it needs the
written type's structure, which this module exposes:

- the outermost constructor of a type as written (written_structure, array_element), whose components' types keep
  their alias names;
- the type parameters, parameters, and result of a function type as written (quantified, fun_signature), whose
  symbols are those the type's parts, and a call's type arguments, refer to;
- whether a type argument is a type operator (is_type_operator);
- what echo writes from a type as written: a package's text (package_text), the structure a value is written by
  (echo_head, echo_children, recursive_identity), and a tuple's type components (tuple_type_components).

The passes and the C printer use these and shapes, not the type checker's normalizing functions.
"""

from __future__ import annotations

from typing import Optional

from quest.codegen.layout import resolved_shape
from quest.ir.shapes import shape
from quest.types.canonical import collect_fun_quantifiers, normalize_type, resolve_type_bound
from quest.types import (
    QAliasType,
    QAllType,
    QArrayType,
    QFunType,
    QOptionType,
    QPathType,
    QQuantifier,
    QRecGroupType,
    QRecType,
    QRecordType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeFun,
    QTypeVar,
    QVariantType,
    strip_aliases,
    unalias,
)

# The kinds of shapes in whose representation a type parameter bounded by one holds its values
_VIEWED_KINDS = ("record", "variant", "option")


def written_structure(t: QType, kind: str) -> Optional[QType]:
    """t as written with its outermost constructor exposed, if t's shape is of the kind ("tuple", "array",
    "exception", or one of the kinds a type parameter bounded by one is held in the representation of, for which it
    is the bound): None otherwise. Its components' types keep their alias names; a shape's components have only their
    canonical types."""
    s = shape(t)
    held = resolved_shape(s) if kind in _VIEWED_KINDS else s
    if held.kind != kind:
        return None
    return normalize_type(resolve_type_bound(t) if held is not s else t)


def array_element(t: QType) -> Optional[QType]:
    """The element type, as written, of an array type (None if t is not one)."""
    written = written_structure(t, "array")
    return written.element_type if written is not None else None


def quantified(t: QType) -> tuple[tuple[QQuantifier, ...], QType]:
    """The universal quantifiers wrapping a function type as written (a recursive one, through its unfolding), and
    the type they quantify."""
    return collect_fun_quantifiers(t)


def fun_signature(t: QType) -> tuple[tuple, QType]:
    """The parameters and result type, as written, of a (possibly polymorphic) function type, its type parameters'
    symbols standing for themselves."""
    _, inner = quantified(t)
    if isinstance(inner, QFunType):
        return tuple(inner.params), inner.result_type
    return (), inner


def is_type_operator(t: QType) -> bool:
    """Whether t (a type argument) is a type operator (Fun(X::K) T), the argument of a higher-kinded type parameter,
    which is not the type of values and has no shape."""
    return isinstance(strip_aliases(t), QTypeFun)


def package_text(t: QType) -> Optional[str]:
    """How echo writes a value of t, if t is an existential tuple type (a package), whose components are hidden: as
    the interpreter prints it, known statically. None for any other type."""
    bare = strip_aliases(t)
    if not (isinstance(bare, QTupleType) and bare.is_existential):
        return None
    parts: list[str] = []
    for comp in bare.components:
        match comp:
            case QTupleTypeFormal():
                parts.append(f"<Hidden>::{comp.bound}")
            case QTupleTypeBinding():
                parts.append(f"Let {comp.name} = {comp.type_val}")
            case QTupleField():
                if isinstance(comp.type_val, (QPathType, QTypeVar)):
                    elem = "<hidden>"
                elif isinstance(comp.type_val, (QFunType, QAllType)):
                    elem = "<fun>"
                else:
                    elem = "<val>"
                parts.append(f"{comp.name}={elem}" if comp.name else elem)
    return f"tuple {' '.join(parts)} end" if parts else "tuple end"


def tuple_type_components(t: QTupleType) -> list[tuple[int, str]]:
    """A tuple type's type components as echo writes them, as the interpreter does (_format_aggregate), each with
    the number of value elements before it."""
    components: list[tuple[int, str]] = []
    position = 0
    for comp in t.components:
        match comp:
            case QTupleTypeFormal():
                components.append((position, f"<Hidden>::{comp.bound}"))
            case QTupleTypeBinding():
                components.append((position, f"Let {comp.name} = {comp.type_val}"))
            case _:
                position += 1
    return components


def echo_head(t: QType) -> QType:
    """The type whose structure echo writes a value of type t by: a recursive type unfolded, through its alias if it
    has one, so that its recursive occurrences and the aliases in it keep their names, as the interpreter unfolds
    recursive types as it goes (_exposed_type in interpreter/treewalk.py)."""
    t = t.prune() if hasattr(t, "prune") else t
    if isinstance(t, QAliasType) and isinstance(t.target, (QRecType, QRecGroupType)):
        t = t.unfold_lazily()
    t = unalias(t)
    if isinstance(t, QRecType):
        t = t.unfold_lazily()
    return unalias(t)


def recursive_identity(t: QType) -> Optional[int]:
    """What tells recursive types apart for echo: the recursive type t is or names, or None if it is not one."""
    t = t.prune() if hasattr(t, "prune") else t
    while isinstance(t, QAliasType):
        if isinstance(t.target, (QRecType, QRecGroupType)):
            return id(t.target)
        t = t.target
    return id(t) if isinstance(t, QRecType) else None


def echo_children(t: QType) -> dict[str, QType]:
    """The types of the parts of a value of type t that echo writes through descriptors of their own, keyed as the
    emitted descriptor of t refers to them: a tuple's value elements by index, a record's fields, options', and
    variants' cases by name, and an array's elements by "". A recursive type's are its unfolding's (echo_head); a
    type application has none here: its unfolding is described by its shared descriptor."""
    t = echo_head(t)
    match t:
        case QTupleType():
            return {str(i): f.type_val for i, f in enumerate(t.value_fields)}
        case QRecordType():
            return {f.name: f.type_val for f in t.fields}
        case QArrayType():
            return {"": t.element_type}
        case QOptionType():
            return {o.name: o.payload_type for o in t.options if o.payload_type is not None}
        case QVariantType():
            return {v.name: v.type_val for v in t.variants if v.type_val is not None}
        case _:
            return {}
