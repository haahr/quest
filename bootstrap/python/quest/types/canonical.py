"""Reduced and canonical forms of types, which the backends use: type operator
applications reduced (beta_reduce_head), recursive types unfolded
(unfold_recursive), and the canonical form of a recursive type, its minimal
graph (canonical_type), so that equal types have one representation however they
are written."""

from __future__ import annotations

import dataclasses
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

from quest.types import (
    is_type_equal,
    QAbstractType,
    QAliasType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QFunType,
    QKind,
    QOptionField,
    QOptionType,
    QOutType,
    QParam,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QTypeKind,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
    reserved_symbol_id,
    reserved_symbol_index,
    ReservedSymbolUse,
    short_type_name,
    strip_aliases,
    type_fields,
    TYPE_KIND,
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
    (ir/shapes.py): aliases stripped, a recursive type replaced by its
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
    was made at, or of t's shape (ir/shapes.py, which orders cases by name)."""
    curr = normalize_type(t)
    while not isinstance(curr, QOptionType):
        exposed = normalize_type(resolve_type_bound(curr))
        if exposed is curr:
            raise ValueError(f"{t} is not an option type")
        curr = exposed
    return tuple(o.name for o in curr.options)


def collect_fun_quantifiers(fun_type: QType) -> tuple[tuple[QQuantifier, ...], QType]:
    """The universal quantifiers wrapping a function type (a recursive one,
    through its unfolding), and the type they quantify, as written: their
    symbols are those the type's own parts refer to, where a shape's are those
    of its canonical form (ir/shapes.py)."""
    quants: tuple[QQuantifier, ...] = ()
    curr = normalize_type(fun_type)
    while isinstance(curr, QAllType):
        quants = quants + curr.quantifiers
        curr = normalize_type(curr.body)
    return quants, curr


# ============================================================================
# Canonical forms of recursive types
# ============================================================================
#
# Recursive types are equi-recursive: a type stands for the regular tree of its
# unfoldings, and types with the same tree are equal however they are written:
# as a recursive type, as an unfolding written out (to any depth), or with a
# different period (`Rec(L) Option nil cons with head: Int tail: L end end` and
# the same type unrolled twice inside its Rec). Equal types share one C
# representation, so tags and descriptors are computed from a canonical form of
# each type that contains recursion: the graph of its nodes is minimized by
# partition refinement (as dynamic_json does for its type table), and the
# minimal graph is written back as a type whose recursion variables and type
# parameters have reserved ids (ReservedSymbolUse.CANONICAL_REC and
# CANONICAL_BINDER). Types are hash-consed, so the canonical form of a type in
# canonical form is that type itself.
#
# Nodes of the graph are tuples (with or without type components), records,
# variants, options, arrays, var and out types, function types (polymorphic or
# not), exception types, auto types, type operators and applications of abstract
# ones, type variables and abstract and path types (with their kinds), and the
# kinds TYPE, <: T, and ALL(X::K) K'. External types and kind variables, which
# contain no types, are leaves, compared by identity.
#
# Binders are written by name, so they are compared up to renaming: a node that
# binds type parameters (a polymorphic function type, an auto type, a tuple with
# type components, a type operator, an operator kind) is a node like any other,
# and an occurrence of one of its parameters is a node with a scope edge back to
# it. A type object means different things under different binders, so a node is
# keyed by its object together with the binder nodes its free variables refer
# to. Refinement follows scope edges, so two occurrences are equivalent when
# their binders are, and the minimal graph is written back with each occurrence
# naming the nearest enclosing binder of its binder's class. Merging binders
# could in principle mix up scopes, so canonical_type uses a canonical form only
# if it is equal to the type it stands for (is_type_equal), and otherwise falls
# back to the type as written.

_MAX_CANONICAL_NODES = 100_000


_GRAPH_NODES = (
    QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QFunType, QAllType,
    QExceptionType, QAutoType,
)


def _check_canonical() -> bool:
    """Whether a canonical form not equal to its type, or not a fixed point, is
    an error rather than a warning (as in the tests: run_tests.py and the unit
    tests set QUEST_CHECK_CANONICAL=1)."""
    return os.environ.get("QUEST_CHECK_CANONICAL") == "1"


def _canonical_structure(t: QType) -> QType:
    """t with aliases, solved metavariables, type operator applications, and
    recursive types whose unfoldings are graph nodes reduced down to its outer
    constructor."""
    for _ in range(MAX_BETA_STEPS):
        t = strip_aliases(pruned(t))
        if not isinstance(t, (QRecType, QRecGroupType, QTypeApp)):
            return t
        if (unfolded := unfold_recursive(t, _GRAPH_NODES)) is not None:
            return unfolded
        if isinstance(t, QTypeApp):
            reduced = beta_reduce_head(t)
            if not isinstance(reduced, (QTypeApp, QRecType, QRecGroupType)):
                t = reduced
                continue
        return t
    return t


_BINDER_NODES = ("all", "auto", "xtuple", "tfun", "kALL")


# Recursion variables bind tuples, records, variants, and options where every
# cycle passes through one, and otherwise any node that a recursive type may
# unfold to
_AGGREGATE_SHAPES = ("tuple", "record", "variant", "option", "xtuple")


_UNFOLDABLE_SHAPES = _AGGREGATE_SHAPES + ("array", "var", "out", "fun", "all", "exception", "auto")


@dataclass
class _NodeInfo:
    """A node of a canonical graph before its parts are resolved: its shape
    (constructor and labels), its parts, the type parameters it binds (in
    order), and for an occurrence of a parameter, that parameter's symbol id."""
    shape: tuple[Any, ...]
    parts: list[QType]
    binds: tuple[int, ...] = ()
    occurrence_of: Optional[int] = None


def _canonical_node(s: Any, bound: Any) -> Optional[_NodeInfo]:
    """The node for the structure s (a type or a kind), whose free variables in
    `bound` are parameters of enclosing binder nodes; None for a leaf."""
    match s:
        case QTypeKind():
            return _NodeInfo(("kTYPE",), [])
        case QPowerKind():
            return _NodeInfo(("kPOWER",), [s.bound])
        case QAllKind():
            return _NodeInfo(("kALL",), [s.param_kind, s.result_kind], (s.param_id,))
        case QKind():
            return None
        case QTypeVar() | QAbstractType():
            cls_name = "var" if isinstance(s, QTypeVar) else "abstract"
            kinds = [s.bound] if s.bound is not None else []
            if s.symbol_id in bound:
                return _NodeInfo(("bound", cls_name, bound[s.symbol_id][1], bool(kinds)), kinds,
                                 occurrence_of=s.symbol_id)
            return _NodeInfo(("free", cls_name, s.symbol_id, s.name, bool(kinds)), kinds)
        case QPathType():
            return _NodeInfo(("path", s.root_name, s.root_symbol_id, s.field_name), [s.bound])
        case QTupleType():
            if len(s.value_fields) == len(s.fields):
                fields = s.value_fields
                return _NodeInfo(("tuple", tuple((f.name, f.is_var) for f in fields)), [f.type_val for f in fields])
            comps: list[tuple[Any, ...]] = []
            parts: list[Any] = []
            for f in s.fields:
                match f:
                    case QTupleTypeFormal(name=f_name, bound=f_bound):
                        comps.append(("formal", f_name))
                        parts.append(f_bound)
                    case QTupleTypeBinding(name=f_name, type_val=type_val, bound=f_bound):
                        comps.append(("binding", f_name, f_bound is not None))
                        parts.append(type_val)
                        if f_bound is not None:
                            parts.append(f_bound)
                    case QTupleField(name=f_name, is_var=is_var, type_val=type_val):
                        comps.append(("field", f_name, is_var))
                        parts.append(type_val)
            binds = tuple(f.symbol_id for f in s.fields if isinstance(f, QTupleTypeFormal))
            return _NodeInfo(("xtuple", tuple(comps)), parts, binds)
        case QRecordType():
            fields = sorted(s.fields, key=lambda f: f.name)
            return _NodeInfo(("record", s.provenance, tuple((f.name, f.is_var) for f in fields)),
                             [f.type_val for f in fields])
        # Variants and options are compared by their cases' names, unordered, so
        # their canonical forms order cases by name, as records' fields are
        # ordered: equal types then have one layout and one numbering of tags
        case QVariantType():
            variants = sorted(s.variants, key=lambda v: v.name)
            labels = tuple((v.name, v.is_var, v.type_val is not None) for v in variants)
            return _NodeInfo(("variant", labels), [v.type_val for v in variants if v.type_val is not None])
        case QOptionType():
            options = sorted(s.options, key=lambda o: o.name)
            labels = tuple((o.name, o.payload_type is not None) for o in options)
            return _NodeInfo(("option", labels), [o.payload_type for o in options if o.payload_type is not None])
        case QArrayType():
            return _NodeInfo(("array",), [s.element_type])
        case QVarType():
            return _NodeInfo(("var",), [s.element_type])
        case QOutType():
            return _NodeInfo(("out",), [s.element_type])
        case QFunType():
            modes = tuple((p.is_var, p.is_out) for p in s.params)
            return _NodeInfo(("fun", modes), [p.type_val for p in s.params] + [s.result_type])
        case QExceptionType():
            return _NodeInfo(("exception",), [s.payload_type])
        case QAllType():
            parts = [q.bound for q in s.quantifiers] + [s.body]
            return _NodeInfo(("all", len(s.quantifiers)), parts, tuple(q.symbol_id for q in s.quantifiers))
        case QAutoType():
            labels = tuple((f.name, f.is_var) for f in s.signature)
            return _NodeInfo(("auto", labels), [s.kind_bound] + [f.type_val for f in s.signature], (s.symbol_id,))
        case QTypeFun():
            parts = [p.bound for p in s.params] + [s.body]
            return _NodeInfo(("tfun", len(s.params)), parts, tuple(p.symbol_id for p in s.params))
        case QTypeApp():
            # An application of an abstract type operator (one that does not
            # reduce)
            return _NodeInfo(("app", len(s.arguments)), [s.constructor, *s.arguments])
        case _:
            return None


def _rebuild_node(shape: tuple[Any, ...], parts: list[QType]) -> QType:
    """The type (or kind) with the given shape (from _canonical_node) and parts,
    for a node that binds nothing and is not an occurrence of a parameter."""
    kind = shape[0]
    if kind == "tuple":
        return QTupleType(tuple(QTupleField(name=n, type_val=p, is_var=v) for (n, v), p in zip(shape[1], parts)))
    if kind == "record":
        fields = tuple(QRecordField(name=n, type_val=p, is_var=v) for (n, v), p in zip(shape[2], parts))
        return QRecordType(fields, provenance=shape[1])
    if kind == "variant":
        remaining = iter(parts)
        return QVariantType(tuple(
            QVariantField(name=n, type_val=next(remaining) if has else None, is_var=v) for n, v, has in shape[1]
        ))
    if kind == "option":
        remaining = iter(parts)
        return QOptionType(tuple(
            QOptionField(name=n, payload_type=next(remaining) if has else None) for n, has in shape[1]
        ))
    if kind == "array":
        return QArrayType(element_type=parts[0])
    if kind == "var":
        return QVarType(element_type=parts[0])
    if kind == "out":
        return QOutType(element_type=parts[0])
    if kind == "fun":
        # Parameter names are not part of a function type's identity; canonical
        # ones keep equal types identical
        params = tuple(
            QParam(name=f"x{i + 1}", type_val=p, is_var=is_var, is_out=is_out)
            for i, ((is_var, is_out), p) in enumerate(zip(shape[1], parts))
        )
        return QFunType(params=params, result_type=parts[-1])
    if kind == "app":
        return QTypeApp(constructor=parts[0], arguments=tuple(parts[1:]))
    if kind == "free":
        bound = parts[0] if shape[4] else None
        if shape[1] == "var":
            return QTypeVar(name=shape[3], symbol_id=shape[2], bound=bound)
        return QAbstractType(name=shape[3], symbol_id=shape[2], bound=bound)
    if kind == "path":
        return QPathType(root_name=shape[1], root_symbol_id=shape[2], field_name=shape[3], bound=parts[0])
    if kind == "kTYPE":
        return TYPE_KIND
    if kind == "kPOWER":
        return QPowerKind(parts[0])
    return QExceptionType(payload_type=parts[0])


@dataclass(frozen=True)
class _Leaf:
    """A leaf of a canonical graph: a type compared by identity, with the binder
    nodes (or classes) and positions of its free variables that are parameters
    of enclosing binders, as (symbol id, binder, position)."""
    type: QType
    bound: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class _Param:
    """A type parameter of a binder as written back: its symbol id, name, and
    kind."""
    symbol_id: int
    name: str
    kind: Optional[QKind]

    def var(self) -> QTypeVar:
        return QTypeVar(name=self.name, symbol_id=self.symbol_id, bound=self.kind)


@dataclass(frozen=True)
class _BuildContext:
    """Where a part of a canonical form is written: the recursive type being
    written (its root class, component, and variables, by class), the parameters
    of the enclosing binders (by class, the nearest one of each), and the number
    of enclosing parameters (which numbers the next binder's)."""
    rec_root: int = -1
    rec_comp: int = -1
    rec_vars: Any = None
    scope: Any = None
    depth: int = 0


_EMPTY_CONTEXT = _BuildContext(scope={})


class _NotCanonicalizable(Exception):
    """A type's graph is too large to canonicalize (its unfoldings do not
    repeat), or cannot be written back."""


_Ref = Any  # a class of a canonical graph (an int) or a _Leaf


class _CanonicalGraph:
    """The graph of a type's parts, minimized so that equal types have the same
    graph, from which their canonical form is written (docs/c-representation.md
    §5.7).

    Recursive types are equal to their unfoldings, so one type can be written in
    many ways. These two are equal, the second unrolled once inside its Rec:

        Rec(L::TYPE) Option nil cons with head: Int tail: L end end
        Rec(L::TYPE)
          Option nil
            cons with head: Int
                      tail: Option nil cons with head: Int tail: L end end
                 end
          end

    The C backend must give both one tag (the name of its C struct) and one
    descriptor (its description at run time), so it computes them from a
    canonical form, which every type equal to these has:

        Rec(Rec.0::TYPE)
          Option cons with Tuple head: Int tail: Rec.0 end nil end

    The graph is built in three steps:

    1. The constructor walks the type, making a node for each part it meets (an
       option, a tuple, a function type, and so on; _canonical_node lists them)
       with an edge to each of the part's own parts. A recursive type is not a
       node: it is replaced by its unfolding, so recursion becomes a cycle. The
       first type above has two nodes, the option and its payload tuple, the
       tuple's tail an edge back to the option; the second has four in a cycle.
       Types without parts, such as Int, are leaves, compared by identity.

    2. The nodes are partitioned into classes that cannot be told apart, the
       coarsest partition in which nodes of a class have the same shape (the
       constructor and its labels) and parts in the same classes. As in DFA
       minimization, classes start as one per shape and are split until no
       class splits. The second type's two options end in one class and its two
       tuples in another, so both types have the same two-class graph, the
       quotient, in which each class is a node.

    3. build() writes a class back as a type, with a Rec wherever the quotient
       has a cycle (_find_components finds them, _recursive_term writes them).

    Type parameters add one twist. A node that binds parameters (a polymorphic
    function type, a type operator, an auto type) is a node like any other, and
    an occurrence of a parameter is a node whose shape holds the parameter's
    position, not its name, with a scope edge to its binder node, which
    refinement follows like any edge. So binders that differ only in their
    parameters' names fall into one class. Since one type object can mean
    different things under different binders, a node is the object together
    with the binder nodes its free variables refer to. Written back, parameters
    get reserved ids numbered by depth, so that no binder captures another's."""

    def __init__(self, root: QType) -> None:
        index: dict[Any, int] = {}
        self.objects: list[QType] = []  # the structure of each node (kept so that ids stay unique)
        self.closed: list[bool] = []  # whether a node's free variables are all free in the root
        shapes: list[tuple[Any, ...]] = []
        children: list[list[_Ref]] = []
        scope: list[int] = []  # for an occurrence of a parameter, its binder node; otherwise -1
        pending: list[tuple[list[QType], dict[int, tuple[int, int]]]] = []

        def ref(t: Any, bound: dict[int, tuple[int, int]]) -> _Ref:
            s = t if isinstance(t, QKind) else _canonical_structure(t)
            free = tuple((sid, *bound[sid]) for sid in sorted(s._fv) if sid in bound)
            info = _canonical_node(s, bound)
            if info is None:
                return _Leaf(s, free)
            key = (id(s), free)
            i = index.get(key)
            if i is not None:
                return i
            if len(self.objects) >= _MAX_CANONICAL_NODES:
                raise _NotCanonicalizable()
            i = index[key] = len(self.objects)
            self.objects.append(s)
            self.closed.append(not free)
            shapes.append(info.shape)
            children.append([])
            scope.append(bound[info.occurrence_of][0] if info.occurrence_of is not None else -1)
            inner = bound
            if info.binds:
                inner = dict(bound)
                inner.update({sid: (i, pos) for pos, sid in enumerate(info.binds)})
            pending.append((info.parts, inner))
            return i

        self.root = ref(root, {})
        done = 0
        while done < len(self.objects):
            parts, inner = pending[done]
            children[done] = [ref(p, inner) for p in parts]
            done += 1

        # Partition refinement to the coarsest bisimulation, starting from each
        # node's shape, following scope edges
        shape_ids: dict[Any, int] = {}
        cls = [shape_ids.setdefault(shape, len(shape_ids)) for shape in shapes]
        count = len(shape_ids)

        def child_sig(c: _Ref) -> Any:
            if isinstance(c, int):
                return cls[c]
            return ("leaf", id(c.type), tuple((cls[node], pos) for _, node, pos in c.bound))

        while True:
            sigs: dict[Any, int] = {}
            refined = [
                sigs.setdefault(
                    (cls[i], tuple(child_sig(c) for c in kids), cls[scope[i]] if scope[i] >= 0 else -1), len(sigs)
                )
                for i, kids in enumerate(children)
            ]
            if len(sigs) == count:
                break
            cls, count = refined, len(sigs)
        self.cls = cls

        # The quotient graph, one node per class
        self.shapes: list[tuple[Any, ...]] = [()] * count
        self.children: list[list[_Ref]] = [[]] * count
        self.scope: list[int] = [-1] * count
        for i, k in enumerate(cls):
            self.shapes[k] = shapes[i]
            self.children[k] = [
                cls[c] if isinstance(c, int) else _Leaf(c.type, tuple((sid, cls[n], pos) for sid, n, pos in c.bound))
                for c in children[i]
            ]
            self.scope[k] = cls[scope[i]] if scope[i] >= 0 else -1
        self._find_components()
        self.terms: dict[int, Optional[QType]] = {}
        self._built: dict[Any, QType] = {}
        self._aggregate_cycle_memo: dict[int, bool] = {}

    def _find_components(self) -> None:
        """Finds the strongly connected components of the quotient graph
        (Tarjan's algorithm, iteratively, along structural edges only), whether
        each is cyclic, whether each class reaches a cyclic one, and the binder
        classes that each refers to (by occurrences of their parameters) and
        reaches."""
        count = len(self.shapes)
        self.component = [-1] * count
        cyclic: list[bool] = []
        reaches_cycle: list[bool] = []
        refers: list[frozenset[int]] = []
        order = [-1] * count
        low = [0] * count
        stack: list[int] = []
        on_stack = [False] * count
        counter = 0
        for start in range(count):
            if order[start] >= 0:
                continue
            work = [(start, 0)]
            order[start] = low[start] = counter
            counter += 1
            stack.append(start)
            on_stack[start] = True
            while work:
                k, pos = work[-1]
                kids = [c for c in self.children[k] if isinstance(c, int)]
                if pos < len(kids):
                    work[-1] = (k, pos + 1)
                    c = kids[pos]
                    if order[c] < 0:
                        order[c] = low[c] = counter
                        counter += 1
                        stack.append(c)
                        on_stack[c] = True
                        work.append((c, 0))
                    elif on_stack[c]:
                        low[k] = min(low[k], order[c])
                    continue
                work.pop()
                if work:
                    parent = work[-1][0]
                    low[parent] = min(low[parent], low[k])
                if low[k] != order[k]:
                    continue
                # k roots a component; the components it reaches were all
                # completed before it
                members = []
                while True:
                    m = stack.pop()
                    on_stack[m] = False
                    self.component[m] = len(cyclic)
                    members.append(m)
                    if m == k:
                        break
                comp = len(cyclic)
                is_cyclic = len(members) > 1 or any(isinstance(c, int) and c == k for c in self.children[k])
                reaches = is_cyclic
                referred: set[int] = set()
                for m in members:
                    if self.scope[m] >= 0:
                        referred.add(self.scope[m])
                    for c in self.children[m]:
                        if isinstance(c, int):
                            if self.component[c] != comp:
                                reaches = reaches or reaches_cycle[self.component[c]]
                                referred |= refers[self.component[c]]
                        else:
                            referred.update(node for _, node, _ in c.bound)
                cyclic.append(is_cyclic)
                reaches_cycle.append(reaches)
                refers.append(frozenset(referred))
        self.cyclic = cyclic
        self.reaches_cycle = reaches_cycle
        self.refers = refers

    def term(self, k: int) -> Optional[QType]:
        """The canonical form of class k, or None if no recursion is reachable
        from it."""
        if k not in self.terms:
            self.terms[k] = self.build(k, _EMPTY_CONTEXT) if self.reaches_cycle[self.component[k]] else None
        return self.terms[k]

    def _is_rec_shape(self, k: int, comp: int) -> bool:
        """Whether a node of a cyclic component may be bound by a recursion
        variable (see _UNFOLDABLE_SHAPES)."""
        return self.shapes[k][0] in (_AGGREGATE_SHAPES if self._aggregate_cycles(comp) else _UNFOLDABLE_SHAPES)

    def _aggregate_cycles(self, comp: int) -> bool:
        """Whether every cycle of a cyclic component passes through a tuple,
        record, variant, or option, tested by looking for a cycle among its
        other nodes.

        If every cycle does, recursion variables bind only those nodes
        (_is_rec_shape), so that every Rec in a canonical form unfolds to a
        tuple, record, variant, or option, as recursive types are usually
        written. A stream of integers has a cycle through a tuple and a function
        type:

            Rec(S::TYPE) Tuple head: Int tail: All() S end

        Its canonical form is a recursive tuple, and the canonical form of its
        tail's type, All() S, has one as its result, though the function type
        is on the same cycle:

            All() Rec(Rec.0::TYPE) Tuple head: Int tail: All() Rec.0 end

        not Rec(F::TYPE) All() Tuple head: Int tail: F end. Only when some cycle
        passes through none of them, as in Rec(F::TYPE) All() F, may a
        recursion variable bind any node that a recursive type may unfold to."""
        if comp in self._aggregate_cycle_memo:
            return self._aggregate_cycle_memo[comp]
        others = [k for k in range(len(self.shapes))
                  if self.component[k] == comp and self.shapes[k][0] not in _AGGREGATE_SHAPES]
        state: dict[int, int] = {}  # 1 while on the walk's path, 2 when done
        acyclic = True
        for start in others:
            if start in state:
                continue
            state[start] = 1
            work = [(start, 0)]
            while work and acyclic:
                k, pos = work[-1]
                kids = [
                    c for c in self.children[k]
                    if isinstance(c, int) and self.component[c] == comp and self.shapes[c][0] not in _AGGREGATE_SHAPES
                ]
                if pos == len(kids):
                    state[k] = 2
                    work.pop()
                    continue
                work[-1] = (k, pos + 1)
                c = kids[pos]
                if c not in state:
                    state[c] = 1
                    work.append((c, 0))
                elif state[c] == 1:
                    acyclic = False
            if not acyclic:
                break
        self._aggregate_cycle_memo[comp] = acyclic
        return acyclic

    def build(self, c: _Ref, ctx: _BuildContext) -> QType:
        """Writes back class (or leaf) c in context ctx."""
        if not isinstance(c, int):
            if not c.bound:
                return c.type
            subst = {}
            for sid, binder, pos in c.bound:
                params = ctx.scope.get(binder)
                if params is None or pos >= len(params):
                    raise _NotCanonicalizable()
                subst[sid] = params[pos].var()
            return c.type.substitute(subst)
        comp = self.component[c]
        in_rec = ctx.rec_comp == comp
        if in_rec and c in ctx.rec_vars:
            return ctx.rec_vars[c]
        if not in_rec:
            refers = self.refers[comp]
            ctx = _BuildContext(scope={b: p for b, p in ctx.scope.items() if b in refers},
                                depth=ctx.depth if refers else 0)
        scope_key = tuple(sorted((b, tuple(p.symbol_id for p in params)) for b, params in ctx.scope.items()
                                 if b in self.refers[comp]))
        key = (c, ctx.rec_root if in_rec else -1, scope_key, ctx.depth)
        built = self._built.get(key)
        if built is not None:
            return built
        if in_rec or not self.cyclic[comp] or not self._is_rec_shape(c, comp):
            # Inside the recursive type being written, not in a cycle, or a node
            # that recursion variables do not bind (such as a function type on
            # cycles that all pass through tuples, records, variants, or
            # options, which are preferred as recursive types): the node is
            # written with each of its parts
            built = self._build_node(c, ctx)
        else:
            built = self._recursive_term(c, ctx)
        self._built[key] = built
        return built

    def _build_node(self, k: int, ctx: _BuildContext) -> QType:
        shape = self.shapes[k]
        kids = self.children[k]
        kind = shape[0]
        if kind == "bound":
            params = ctx.scope.get(self.scope[k])
            if params is None or shape[2] >= len(params):
                raise _NotCanonicalizable()  # the occurrence's binder does not enclose it as written back
            param = params[shape[2]]
            kind_val = self.build(kids[0], ctx) if shape[3] else None
            if shape[1] == "var":
                return QTypeVar(name=param.name, symbol_id=param.symbol_id, bound=kind_val)
            return QAbstractType(name=param.name, symbol_id=param.symbol_id, bound=kind_val)
        if kind not in _BINDER_NODES:
            return _rebuild_node(shape, [self.build(c, ctx) for c in kids])

        # A binder: its parameters are numbered by the number of enclosing ones,
        # so that no two enclosing each other share an id; each parameter's kind
        # may refer to the parameters before it
        params: list[_Param] = []
        scope = dict(ctx.scope)
        scope[k] = params
        count = (shape[1] if kind in ("all", "tfun") else 1 if kind in ("auto", "kALL")
                 else sum(1 for comp in shape[1] if comp[0] == "formal"))
        inner = dataclasses.replace(ctx, scope=scope, depth=ctx.depth + count)
        remaining = iter(kids)

        def next_part() -> Any:
            return self.build(next(remaining), inner)

        def new_param(name: str = "") -> _Param:
            index = ctx.depth + len(params)
            param = _Param(reserved_symbol_id(ReservedSymbolUse.CANONICAL_BINDER, index),
                           name if name else f"T{index}", next_part())
            params.append(param)
            return param

        if kind == "all":
            quantifiers = []
            for _ in range(shape[1]):
                param = new_param()
                quantifiers.append(QQuantifier(name=param.name, symbol_id=param.symbol_id, bound=param.kind))
            return QAllType(quantifiers=tuple(quantifiers), body=next_part())
        if kind == "tfun":
            formals = []
            for _ in range(shape[1]):
                param = new_param()
                formals.append(QTypeFormal(name=param.name, symbol_id=param.symbol_id, bound=param.kind))
            return QTypeFun(params=tuple(formals), body=next_part())
        if kind == "kALL":
            param = new_param()
            return QAllKind(param_name=param.name, param_id=param.symbol_id, param_kind=param.kind,
                            result_kind=next_part())
        if kind == "auto":
            param = new_param()
            signature = tuple(QRecordField(name=name, type_val=next_part(), is_var=is_var) for name, is_var in shape[1])
            return QAutoType(type_param=param.name, symbol_id=param.symbol_id, kind_bound=param.kind,
                             signature=signature)
        components: list[Any] = []
        for comp in shape[1]:
            if comp[0] == "formal":
                # A tuple's type components are selected by name, so formals
                # keep their names
                param = new_param(comp[1])
                components.append(QTupleTypeFormal(name=param.name, symbol_id=param.symbol_id, bound=param.kind))
            elif comp[0] == "binding":
                type_val = next_part()
                components.append(QTupleTypeBinding(name=comp[1], type_val=type_val,
                                                    bound=next_part() if comp[2] else None))
            else:
                components.append(QTupleField(name=comp[1], type_val=next_part(), is_var=comp[2]))
        return QTupleType(tuple(components))

    def _recursive_term(self, root: int, ctx: _BuildContext) -> QType:
        """The canonical form of a class on a cycle: a recursive type whose
        variables stand for the targets of the back edges of a depth-first walk
        of its component from root, through the nodes that recursion variables
        may bind (_is_rec_shape; other nodes are passed through, so that each
        recursive type unfolds to such a node)."""
        comp = self.component[root]
        binders: list[int] = []
        state: dict[int, int] = {}  # 1 while on the walk's path, 2 when done

        def successors(k: int) -> list[int]:
            out: list[int] = []

            def through(c: _Ref) -> None:
                if not isinstance(c, int) or self.component[c] != comp:
                    return
                if self._is_rec_shape(c, comp):
                    out.append(c)
                else:
                    for g in self.children[c]:
                        through(g)

            for c in self.children[k]:
                through(c)
            return out

        work = [(root, successors(root), 0)]
        state[root] = 1
        while work:
            k, succ, pos = work[-1]
            if pos == len(succ):
                state[k] = 2
                work.pop()
                continue
            work[-1] = (k, succ, pos + 1)
            c = succ[pos]
            if c not in state:
                state[c] = 1
                work.append((c, successors(c), 0))
            elif state[c] == 1 and c not in binders:
                binders.append(c)
        binders.sort(key=lambda b: b != root)  # the root's variable first, the rest in the order they were found
        variables = {
            b: QTypeVar(name=f"Rec.{i}", symbol_id=reserved_symbol_id(ReservedSymbolUse.CANONICAL_REC, i),
                        bound=TYPE_KIND)
            for i, b in enumerate(binders)
        }
        inner = dataclasses.replace(ctx, rec_root=root, rec_comp=comp, rec_vars=variables)
        if len(binders) == 1:
            var = variables[root]
            return QRecType(var_name=var.name, symbol_id=var.symbol_id, bound=TYPE_KIND,
                            body=self._build_node(root, inner))
        bindings = tuple((v.name, v.symbol_id, TYPE_KIND, self._build_node(b, inner)) for b, v in variables.items())
        return QRecGroupType(bindings=bindings, active_index=0)


# The canonical form found for each type (None if it has none), kept with the
# type so that its id is not reused
_CANONICAL: dict[int, tuple[QType, Optional[QType]]] = {}


# The graph and class of each node of a canonical graph whose free variables are
# all free in the graph's root
_CANONICAL_NODES: dict[int, tuple[QType, _CanonicalGraph, int]] = {}


def canonical_type(t: QType) -> Optional[QType]:
    """Returns the canonical form of t if t contains recursion and is not in
    canonical form, or None otherwise.

    Equal types containing recursion have the same canonical form, which
    therefore has their tag and descriptor.
    """
    t = pruned(t)
    if t._has_meta:
        return None
    entry = _CANONICAL.get(id(t))
    if entry is None or entry[0] is not t:
        entry = (t, _canonical_type_uncached(t))
        _CANONICAL[id(t)] = entry
    return entry[1]


# Whether each type may contain recursion (a recursive type, or an application
# that may reduce to one), kept with the type so that its id is not reused
_MAY_RECUR: dict[int, tuple[Any, bool]] = {}


def _may_recur(node: Any) -> bool:
    """Whether a type (or a part of one, such as a field or a kind) may contain
    recursion: if not, its graph has no cycle, and it has no canonical form."""
    if isinstance(node, (QRecType, QRecGroupType, QTypeApp, QAliasType)):
        return True
    if isinstance(node, (tuple, list)):
        return any(_may_recur(item) for item in node)
    parts = type_fields(node)
    if parts is None:
        return False
    entry = _MAY_RECUR.get(id(node))
    if entry is not None and entry[0] is node:
        return entry[1]
    result = any(_may_recur(part) for part in parts)
    _MAY_RECUR[id(node)] = (node, result)
    return result


def _canonical_type_uncached(t: QType) -> Optional[QType]:
    if not _may_recur(t):
        return None
    if any(is_rec_self_symbol(sym) for sym in t._fv):
        # A body of a recursive type being named (_recursive_tag), its variables
        # replaced by placeholders: the recursive type is in canonical form
        # already (or is named as written), and so are the body's parts
        return None
    s = _canonical_structure(t)
    node = _CANONICAL_NODES.get(id(s))
    if node is not None and node[0] is s:
        _, graph, k = node
    else:
        graph = _register_graph(s)
        if graph is None:
            return None
        k = graph.cls[graph.root]
    try:
        canonical = graph.term(k)
    except _NotCanonicalizable:
        canonical = None
    if canonical is None or canonical is t:
        return None
    # Merging binders could in principle mix up scopes: a canonical form is used
    # only if it is equal to the type
    if not is_type_equal(canonical, strip_aliases(t)):
        message = f"canonical form of the type {short_type_name(t)} is not equal to it"
        if _check_canonical():
            raise AssertionError(message)
        # The type is named as written, as before canonical forms compared
        # binders; the program is still compiled
        sys.stderr.write(f"quest: warning: internal: {message}; naming it as written (please report this)\n")
        return None
    # Tags and descriptors ask next for the parts of the canonical form and of
    # its unfoldings: its graph has them
    if id(canonical_structure := _canonical_structure(canonical)) not in _CANONICAL_NODES:
        _register_graph(canonical_structure)
    if _check_canonical() and canonical_type(canonical) is not None:
        raise AssertionError(f"canonical form of {short_type_name(t)} is not a fixed point")
    return canonical


def _register_graph(s: QType) -> Optional[_CanonicalGraph]:
    """Builds the canonical graph of a structure and records the graph and class
    of each of its nodes whose free variables are all free in s; returns None if
    s has no graph (it is a leaf, or its graph is too large)."""
    try:
        graph = _CanonicalGraph(s)
    except _NotCanonicalizable:
        return None
    if not isinstance(graph.root, int):
        return None
    for i, obj in enumerate(graph.objects):
        if graph.closed[i] and id(obj) not in _CANONICAL_NODES:
            _CANONICAL_NODES[id(obj)] = (obj, graph, graph.cls[i])
    return graph


# A recursive type's tag is built from its body with each recursive variable
# replaced by one of these placeholders, numbered by nesting depth, so that the
# tag is finite and the same for alpha-equivalent types. Their symbol ids are
# reserved (ReservedSymbolUse.REC_SELF), indexed by depth.


def is_rec_self_symbol(symbol_id: int) -> bool:
    return reserved_symbol_index(symbol_id, ReservedSymbolUse.REC_SELF) is not None


def rec_self_var(level: int) -> QTypeVar:
    return QTypeVar(name=f"Rec.Self{level}", symbol_id=reserved_symbol_id(ReservedSymbolUse.REC_SELF, level))


def rec_self_level(t: QType) -> Optional[int]:
    if isinstance(t, QTypeVar):
        return reserved_symbol_index(t.symbol_id, ReservedSymbolUse.REC_SELF)
    return None
