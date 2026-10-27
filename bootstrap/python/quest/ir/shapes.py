"""Shapes: the backend's view of Quest types (docs/ir.md §4.1).

A shape says what a type is structurally, with everything that does not matter
to a backend removed: aliases are stripped, applications of type operators
reduced, and recursion made explicit. Code that lowers a program asks questions
of shapes, never of types: a structural test on a type (isinstance(t,
QTupleType)) silently misses the same type reached through an alias or an
operator (Box(A)), where a shape cannot.

shape(t) is computed from the canonical form of t (types/canonical.py), in which
equal recursive types, however written, are one type; shapes are cached per
canonical type, so equal types have the same shape object. A recursive type's
shape is a cycle: the shape of List(Int) is an option whose cons payload's tail
is that same shape. Shapes are built once and not changed afterwards.

Each shape keeps the canonical type it describes (`type`), from which later
stages take C names and descriptors, and the type whose outermost constructor it
describes (`structure`: the unfolding of a recursive type, and otherwise `type`
itself). Canonical forms name their binders afresh (types/canonical.py), so the
type parameters of a shape's polymorphic function or auto type are not those of
the type it was asked for, whose parts refer to its own.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from quest.types.canonical import canonical_type, normalize_type, resolve_type_bound
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
    QTypeFun,
    QTypeVar,
    QVariantType,
    QVarType,
    BOOL_TYPE,
    CHAR_TYPE,
    INT_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    resolve_metas,
    short_type_name,
    strip_aliases,
    pruned,
)

# The kinds of shapes
SCALAR_KINDS = ("int", "real", "bool", "char", "string", "ok", "word", "bottom")
KINDS = SCALAR_KINDS + (
    "tuple", "record", "variant", "option", "array", "cell", "out", "fun", "all", "auto", "exception", "typevar",
    "abstract", "external", "operator",
)


@dataclass(eq=False)
class Component:
    """A named component of a tuple, record, or auto value's signature, or a
    case of a variant or option."""
    name: Optional[str]
    shape: Optional[Shape]  # None for a case without a payload
    is_var: bool = False


@dataclass(eq=False)
class Param:
    """A parameter of a function shape: its shape and mode ('value', 'var', or
    'out')."""
    name: str
    shape: Shape
    mode: str = "value"


@dataclass(eq=False)
class TypeParam:
    """A type parameter (of an `all` shape, or the type component of an `auto`
    shape): its symbol and bound. The bound is the shape of T for a parameter
    bounded by POWER(T), and None otherwise (its kind is in `kind`)."""
    name: str
    symbol_id: int
    kind: QKind
    bound: Optional[Shape] = None


class Shape:
    """The backend's view of a type. Which fields are set depends on `kind` (one
    of KINDS):

    - `components`: tuple (value components; type components are erased), record
      (fields), auto (signature);
    - `cases`: variant (one payload shape each, or None) and option (a tuple
      shape each, or None);
    - `element`: array, cell (Var), out (Out), exception (payload);
    - `params` and `result`: fun; `type_params` and `body`: all; `type_params`
      (one) and `components`: auto;
    - `symbol_id`, `name`, and `bound`: typevar, a type variable: a type
      parameter in scope or an abstract type of a module or interface (m.T,
      declared T::K in the interface), which have the same representation and
      are told apart by symbol where it matters (a type parameter's descriptor
      is passed to its function); `bound` is the shape of its POWER bound, if
      any;
    - `name`: abstract (an abstract type of a module, an application of an
      abstract operator, or a path type, by its short name) and external (an
      opaque C type).

    An `operator` shape is a type operator's (Fun(X::K) T), passed for a
    higher-kinded type parameter: opaque.
    """

    __slots__ = (
        "kind", "type", "structure", "components", "cases", "element", "params", "result", "type_params", "body",
        "symbol_id", "bound", "name",
    )

    def __init__(self, kind: str, t: QType) -> None:
        self.kind = kind
        self.type = t
        self.structure = t
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

    def fill_from(self, other: Shape) -> None:
        """Fills this shape in from another's fields, but its type (a recursive
        type's, from its unfolding's)."""
        self.kind = other.kind
        self.structure = other.structure
        self.components = other.components
        self.cases = other.cases
        self.element = other.element
        self.params = other.params
        self.result = other.result
        self.type_params = other.type_params
        self.body = other.body
        self.symbol_id = other.symbol_id
        self.bound = other.bound
        self.name = other.name

    @property
    def is_scalar(self) -> bool:
        return self.kind in SCALAR_KINDS

    @property
    def is_recursive(self) -> bool:
        """Whether this is the shape of a recursive type (whose structure is its
        unfolding's)."""
        return isinstance(self.type, (QRecType, QRecGroupType))

    def component(self, name: str) -> Optional[Component]:
        return next((c for c in self.components if c.name == name), None)

    def case(self, name: str) -> Optional[Component]:
        return next((c for c in self.cases if c.name == name), None)

    def sorted_components(self) -> tuple[Component, ...]:
        """A record's fields in name order (the order of its payload's
        layout)."""
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

# Shapes by the id of the type node they were built from (canonical forms, their
# unfoldings and parts), kept with the node so that its id is not reused
_SHAPES: dict[int, tuple[QType, Shape]] = {}

# The shapes of the types asked for (shape), by the id of the type node
_ASKED: dict[int, tuple[QType, Shape]] = {}


def shape(t: QType) -> Shape:
    """The shape of a type (which must not contain unsolved metavariables)."""
    t = pruned(t)
    entry = _ASKED.get(id(t))
    if entry is not None and entry[0] is t:
        return entry[1]
    if t._has_meta:
        # Solved metavariables stand for their solutions, which are cached; the
        # type itself is not
        resolved = resolve_metas(t)
        if resolved._has_meta:
            raise ValueError(f"the type {t} has unsolved metavariables and no shape")
        return shape(resolved)
    stripped = strip_aliases(t)
    canonical = canonical_type(stripped)
    s = _shape(canonical if canonical is not None else stripped)
    _ASKED[id(t)] = (t, s)
    return s


def is_word_type(t: QType) -> bool:
    """Whether t is the standard library's Word.T (or a type parameter bounded
    by it), whose values are held in a uint64_t."""
    t = normalize_type(resolve_type_bound(t))
    match t:
        case QTypeVar() if t.name in ("Word.T", "word.T"):
            return True
        case QPathType() if t.field_name == "T" and t.root_name in ("Word", "word"):
            return True
        case QExternalType() if t.name in ("Word.T", "word.T") or t.c_type == "uint64_t":
            return True
        case _:
            return False


def _cached(t: QType) -> Optional[Shape]:
    entry = _SHAPES.get(id(t))
    return entry[1] if entry is not None and entry[0] is t else None


def _uses_recursion(t: QRecType | QRecGroupType) -> bool:
    """Whether a recursive type refers to itself: its body mentions its
    variable, or for a group's member, its own variable is reachable from its
    body through the members' bodies (a member that refers only to members that
    do not refer back to it is not recursive)."""
    if isinstance(t, QRecType):
        return t.symbol_id in t.body._fv
    ids = [b[1] for b in t.bindings]

    def mentioned(index: int) -> list[int]:
        fv = t.bindings[index][3]._fv
        return [j for j, sym in enumerate(ids) if sym in fv]

    seen: set[int] = set()
    pending = mentioned(t.active_index)
    while pending:
        index = pending.pop()
        if index == t.active_index:
            return True
        if index not in seen:
            seen.add(index)
            pending.extend(mentioned(index))
    return False


def _shape(t: QType) -> Shape:
    """The shape of t, made once for each type object and cached by its
    identity. shape calls it on a type it has stripped of aliases and put in
    canonical form, and _build on the parts of the type it is building, which
    may be aliases.

    Most types are built by _build, one constructor at a time, from the shapes
    of their parts. The cases handled here are those where the shape is some
    other type's:

    - an alias (Let Point = Tuple x: Int y: Int end) has its meaning's;
    - a Rec whose body never mentions its variable, such as
      Rec(X::TYPE) Tuple a: Int end, has the shape of the type it unfolds to,
      as does a member of a group of mutually recursive types that does not
      refer back to itself;
    - an application of a type operator (List(Int)) has the shape of the type
      it reduces to;
    - a variant or option type has the shape of the same type with its cases
      sorted by name, since Option b a end and Option a b end are equal types
      and so must share a shape and a C representation.

    A recursive type's shape is a cycle. The shape of

        Rec(L::TYPE) Option nil cons with head: Int tail: L end end

    is an option shape whose cons case is a tuple shape whose tail is that
    same option shape object. To build it, a placeholder shape (kind
    "pending") is cached for t before t's unfolding is shaped: when the
    unfolding reaches t again at the tail, the lookup finds the placeholder,
    and the tail points to it. The placeholder is then filled in from the
    unfolding's shape (fill_from), keeping t as its type.

    The cache is keyed by id(t), and an entry is used only if it holds t
    itself, since an id can be reused once its object is gone."""
    if (s := _cached(t)) is not None:
        return s
    match t:
        case QAliasType(target=target):
            s = _shape(target)
        case QRecType() | QRecGroupType() if not _uses_recursion(t):
            # A recursive type that does not use its variables (a member of a
            # group that does not refer to the group) is the type it unfolds to,
            # and has its shape, so that its values are its unfolding's however
            # its type is written
            s = _shape(t.unfold_lazily())
        case QRecType() | QRecGroupType():
            # The recursive type's shape is its unfolding's, whose recursive
            # occurrences are this node: enter the shape before building the
            # unfolding's, so that they refer to it, and fill it in from the
            # unfolding's
            s = Shape("pending", t)
            _SHAPES[id(t)] = (t, s)
            s.fill_from(_shape(t.unfold_lazily()))
            return s
        case QTypeApp() if (reduced := normalize_type(t)) is not t:
            s = _shape(reduced)
        case QVariantType() | QOptionType() if (ordered := cases_by_name(t)) is not t:
            # Equal types whose cases are listed in different orders have one
            # shape, its cases ordered by name
            s = _shape(ordered)
        case _:
            s = _build(t)
    _SHAPES[id(t)] = (t, s)
    return s


def cases_by_name(t: QType) -> QType:
    """A variant or option type with its cases ordered by name: t itself if they
    are already."""
    if isinstance(t, QVariantType):
        variants = tuple(sorted(t.variants, key=lambda v: v.name))
        return t if all(a is b for a, b in zip(variants, t.variants)) else QVariantType(variants)
    if isinstance(t, QOptionType):
        options = tuple(sorted(t.options, key=lambda o: o.name))
        return t if all(a is b for a, b in zip(options, t.options)) else QOptionType(options)
    return t


def _kind_bound(kind: QKind) -> Optional[Shape]:
    return _shape(kind.bound) if isinstance(kind, QPowerKind) else None


def _build(t: QType) -> Shape:
    # Scalars are singletons, recognized by identity: value patterns would
    # compare types with ==, which types refuse
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
            # An abstract type elaborated as such, or a path type (x.T): opaque,
            # with its bound
            s = Shape("abstract", t)
            s.name = short_type_name(t)
            s.bound = _kind_bound(bound)
        case QTypeApp():
            # An application of an abstract type operator (normalize_type
            # reduced every other): opaque
            s = Shape("abstract", t)
            s.name = short_type_name(t)
        case QExternalType(c_type=c_type):
            s = Shape("external", t)
            s.name = c_type
        case QTypeFun():
            s = Shape("operator", t)
        case _:
            raise ValueError(f"the type {t} ({type(t).__name__}) has no shape")
    return s


def shapes_reachable(s: Shape) -> list[Shape]:
    """Every shape reachable from s, once each (shapes of recursive types are
    cycles)."""
    seen: dict[int, Shape] = {}
    stack = [s]
    while stack:
        n = stack.pop()
        if id(n) in seen:
            continue
        seen[id(n)] = n
        stack.extend(n.children())
    return list(seen.values())
