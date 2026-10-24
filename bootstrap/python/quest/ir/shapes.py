"""Shapes: the backend's view of Quest types (docs/ir.md §4.1).

A shape says what a type is structurally, with everything that does not matter to a backend removed: aliases are
stripped, applications of type operators reduced, and recursion made explicit. Code that lowers a program asks
questions of shapes, never of types: a structural test on a type (isinstance(t, QTupleType)) silently misses the
same type reached through an alias or an operator (Box(A)), where a shape cannot.

shape(t) is computed from the canonical form of t (codegen/canonical.py), in which equal recursive types, however
written, are one type; shapes are cached per canonical type, so equal types have the same shape object. A recursive
type's shape is a cycle: the shape of List(Int) is an option whose cons payload's tail is that same shape. Shapes are
built once and not changed afterwards.

Each shape keeps the canonical type it describes (`type`), from which later stages take C names and descriptors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from quest.codegen.canonical import canonical_type
from quest.codegen.layout import is_word_type, normalize_type
from quest.types import (
    QAbstractType,
    QAliasType,
    QAllType,
    QArrayType,
    QAutoType,
    QBottomType,
    QExceptionType,
    QExternalType,
    QFunType,
    QKind,
    QOkType,
    QOptionType,
    QOutType,
    QPathType,
    QPowerKind,
    QRecGroupType,
    QRecordType,
    QRecType,
    QTupleType,
    QType,
    QTypeApp,
    QTypeVar,
    QVariantType,
    QVarType,
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    strip_aliases,
)

# The kinds of shapes
SCALAR_KINDS = ("int", "real", "bool", "char", "string", "ok", "word", "bottom")
KINDS = SCALAR_KINDS + (
    "tuple", "record", "variant", "option", "array", "cell", "out", "fun", "all", "auto", "exception", "typevar",
    "abstract", "external",
)


@dataclass(eq=False)
class Component:
    """A named component of a tuple, record, or auto value's signature, or a case of a variant or option."""
    name: Optional[str]
    shape: Optional[Shape]  # None for a case without a payload
    is_var: bool = False


@dataclass(eq=False)
class Param:
    """A parameter of a function shape: its shape and mode ('value', 'var', or 'out')."""
    name: str
    shape: Shape
    mode: str = "value"


@dataclass(eq=False)
class TypeParam:
    """A type parameter (of an `all` shape, or the type component of an `auto` shape): its symbol and bound. The
    bound is the shape of T for a parameter bounded by POWER(T), and None otherwise (its kind is in `kind`)."""
    name: str
    symbol_id: int
    kind: QKind
    bound: Optional[Shape] = None


class Shape:
    """The backend's view of a type. Which fields are set depends on `kind` (one of KINDS):

    - `components`: tuple (value components; type components are erased), record (fields), auto (signature);
    - `cases`: variant (one payload shape each, or None) and option (a tuple shape each, or None);
    - `element`: array, cell (Var), out (Out), exception (payload);
    - `params` and `result`: fun; `type_params` and `body`: all; `type_params` (one) and `components`: auto;
    - `symbol_id`, `name`, and `bound`: typevar, a type variable: a type parameter in scope or an abstract type of a
      module or interface (m.T, declared T::K in the interface), which have the same representation and are told
      apart by symbol where it matters (a type parameter's descriptor is passed to its function); `bound` is the
      shape of its POWER bound, if any;
    - `name`: abstract (an abstract type of a module, an application of an abstract operator, or a path type) and
      external (an opaque C type).
    """

    __slots__ = (
        "kind", "type", "components", "cases", "element", "params", "result", "type_params", "body", "symbol_id",
        "bound", "name",
    )

    def __init__(self, kind: str, t: QType) -> None:
        self.kind = kind
        self.type = t
        self.components: tuple[Component, ...] = ()
        self.cases: tuple[Component, ...] = ()
        self.element: Optional[Shape] = None
        self.params: tuple[Param, ...] = ()
        self.result: Optional[Shape] = None
        self.type_params: tuple[TypeParam, ...] = ()
        self.body: Optional[Shape] = None
        self.symbol_id: Optional[int] = None
        self.bound: Optional[Shape] = None
        self.name: Optional[str] = None

    @property
    def is_scalar(self) -> bool:
        return self.kind in SCALAR_KINDS

    def component(self, name: str) -> Optional[Component]:
        return next((c for c in self.components if c.name == name), None)

    def case(self, name: str) -> Optional[Component]:
        return next((c for c in self.cases if c.name == name), None)

    def sorted_components(self) -> tuple[Component, ...]:
        """A record's fields in name order (the order of its payload's layout)."""
        return tuple(sorted(self.components, key=lambda c: c.name or ""))

    def children(self) -> Iterator[Shape]:
        """The shapes this one refers to directly."""
        for c in self.components + self.cases:
            if c.shape is not None:
                yield c.shape
        for s in (self.element, self.result, self.body, self.bound):
            if s is not None:
                yield s
        for p in self.params:
            yield p.shape
        for tp in self.type_params:
            if tp.bound is not None:
                yield tp.bound

    def __repr__(self) -> str:
        return f"<Shape {self.kind} {self.type}>"


_SCALARS = {
    id(INT_TYPE): "int", id(REAL_TYPE): "real", id(BOOL_TYPE): "bool", id(CHAR_TYPE): "char", id(STRING_TYPE): "string",
}

# Shapes by the id of the type node they were built from (canonical forms, their unfoldings and parts), kept with the
# node so that its id is not reused
_SHAPES: dict[int, tuple[QType, Shape]] = {}


def shape(t: QType) -> Shape:
    """The shape of a type (which must not contain unsolved metavariables)."""
    t = t.prune() if hasattr(t, "prune") else t
    if getattr(t, "_has_meta", False):
        raise ValueError(f"the type {t} has unsolved metavariables and no shape")
    t = strip_aliases(t)
    canonical = canonical_type(t)
    return _shape(canonical if canonical is not None else t)


def _cached(t: QType) -> Optional[Shape]:
    entry = _SHAPES.get(id(t))
    return entry[1] if entry is not None and entry[0] is t else None


def _shape(t: QType) -> Shape:
    if (s := _cached(t)) is not None:
        return s
    match t:
        case QAliasType(target=target):
            s = _shape(target)
        case QRecType() | QRecGroupType():
            # The recursive type's shape is its unfolding's, whose recursive occurrences are this node: enter the
            # shape before building the unfolding's, so that they refer to it, and fill it in from the unfolding's
            s = Shape("pending", t)
            _SHAPES[id(t)] = (t, s)
            unfolded = _shape(t.unfold_lazily())
            for slot in Shape.__slots__:
                if slot != "type":
                    setattr(s, slot, getattr(unfolded, slot))
            return s
        case QTypeApp() if (reduced := normalize_type(t)) is not t:
            s = _shape(reduced)
        case _:
            s = _build(t)
    _SHAPES[id(t)] = (t, s)
    return s


def _kind_bound(kind: QKind) -> Optional[Shape]:
    return _shape(kind.bound) if isinstance(kind, QPowerKind) else None


def _build(t: QType) -> Shape:
    # Scalars are singletons, recognized by identity: value patterns would compare types with ==, which types refuse
    if id(t) in _SCALARS:
        return Shape(_SCALARS[id(t)], t)
    if is_word_type(t):
        return Shape("word", t)
    match t:
        case QOkType():
            return Shape("ok", t)
        case QBottomType():
            return Shape("bottom", t)
        case QTupleType():
            s = Shape("tuple", t)
            s.components = tuple(Component(f.name, _shape(f.type_val), f.is_var) for f in t.value_fields)
        case QRecordType(fields=fields):
            s = Shape("record", t)
            s.components = tuple(Component(f.name, _shape(f.type_val), f.is_var) for f in fields)
        case QVariantType(variants=variants):
            s = Shape("variant", t)
            s.cases = tuple(
                Component(v.name, _shape(v.type_val) if v.type_val is not None else None, v.is_var) for v in variants
            )
        case QOptionType(options=options):
            s = Shape("option", t)
            s.cases = tuple(
                Component(o.name, _shape(o.payload_type) if o.payload_type is not None else None) for o in options
            )
        case QArrayType(element_type=element) | QVarType(element_type=element) | QOutType(element_type=element):
            s = Shape({QArrayType: "array", QVarType: "cell", QOutType: "out"}[type(t)], t)
            s.element = _shape(element)
        case QExceptionType(payload_type=payload):
            s = Shape("exception", t)
            s.element = _shape(payload)
        case QFunType(params=params, result_type=result):
            s = Shape("fun", t)
            s.params = tuple(
                Param(p.name, _shape(p.type_val), "var" if p.is_var else "out" if p.is_out else "value") for p in params
            )
            s.result = _shape(result)
        case QAllType(quantifiers=quantifiers, body=body):
            s = Shape("all", t)
            s.type_params = tuple(TypeParam(q.name, q.symbol_id, q.bound, _kind_bound(q.bound)) for q in quantifiers)
            s.body = _shape(body)
        case QAutoType(type_param=name, symbol_id=symbol_id, kind_bound=bound, signature=signature):
            s = Shape("auto", t)
            s.type_params = (TypeParam(name, symbol_id, bound, _kind_bound(bound)),)
            s.components = tuple(Component(f.name, _shape(f.type_val), f.is_var) for f in signature)
        case QTypeVar(name=name, symbol_id=symbol_id, bound=bound):
            s = Shape("typevar", t)
            s.symbol_id = symbol_id
            s.name = name
            s.bound = _kind_bound(bound) if bound is not None else None
        case QAbstractType(bound=bound) | QPathType(bound=bound):
            # An abstract type elaborated as such, or a path type (x.T): opaque, with its bound
            s = Shape("abstract", t)
            s.name = str(t)
            s.bound = _kind_bound(bound)
        case QTypeApp():
            # An application of an abstract type operator (normalize_type reduced every other): opaque
            s = Shape("abstract", t)
            s.name = str(t)
        case QExternalType(c_type=c_type):
            s = Shape("external", t)
            s.name = c_type
        case _:
            raise ValueError(f"the type {t} ({type(t).__name__}) has no shape")
    return s


def shapes_reachable(s: Shape) -> list[Shape]:
    """Every shape reachable from s, once each (shapes of recursive types are cycles)."""
    seen: dict[int, Shape] = {}
    stack = [s]
    while stack:
        n = stack.pop()
        if id(n) in seen:
            continue
        seen[id(n)] = n
        stack.extend(n.children())
    return list(seen.values())
