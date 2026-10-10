"""C Type mapping, identifier mangling, and operator dispatch for Quest C Transpiler."""

from __future__ import annotations

import dataclasses
import hashlib
import os
import sys
from dataclasses import dataclass
from typing import Any, Optional

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
    QTypeKind,
    QTypeVar,
    QVarType,
    QOutType,
    QVariantField,
    QVariantType,
    resolve_record_bound,
    resolve_variant_bound,
    resolve_option_bound,
    is_type_equal,
    reserved_symbol_id,
    reserved_symbol_index,
    ReservedSymbolUse,
    auto_payload_type,
    QParam,
    QKind,
    TYPE_KIND,
    unalias,
)

SYMBOL_MANGLE_MAP: dict[str, str] = {
    "+": "plus",
    "-": "minus",
    "*": "star",
    "/": "slash",
    "=": "equals",
    "<": "lt",
    ">": "gt",
    "!": "bang",
    "?": "question",
    ":": "colon",
    "@": "at",
    "#": "hash",
    "$": "dollar",
    "%": "percent",
    "^": "caret",
    "&": "amp",
    "|": "pipe",
    "~": "tilde",
    "\\": "backslash",
    ".": "dot",
    "'": "prime",
}


def is_symbolic_name(name: str) -> bool:
    """Returns True if the identifier contains symbolic operator characters (excluding simple module dots)."""
    return any(ch in SYMBOL_MANGLE_MAP and ch != "." for ch in name)


def mangle_symbolic_ident(name: str) -> str:
    """Mangles an identifier containing symbolic operator characters into a C-safe identifier."""
    parts: list[str] = []
    curr: list[str] = []
    for ch in name:
        if ch in SYMBOL_MANGLE_MAP and ch != ".":
            if curr:
                s = "".join(curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
            parts.append(SYMBOL_MANGLE_MAP[ch])
        elif ch == ".":
            if curr:
                s = "".join(curr).strip("_")
                if s:
                    parts.append(s)
                curr.clear()
        else:
            curr.append(ch)
    if curr:
        s = "".join(curr).strip("_")
        if s:
            parts.append(s)
    return "qv_sym_" + "_".join(parts)


def mangle_ident(name: str) -> str:
    """Mangles a Quest identifier into a C-safe identifier prefixed with qv_."""
    if is_symbolic_name(name):
        return mangle_symbolic_ident(name)
    clean = name.replace(".", "_")
    return f"qv_{clean}"


def mangle_module_name(module_name: str) -> str:
    """Mangles a hierarchical module name into a C-safe identifier using __ for slashes."""
    return module_name.lower().replace("/", "__").replace(".", "_")


def module_record_ident(clean_mod: str) -> str:
    """Returns the C identifier of a module's record value, given its mangled module name.

    Module records use their own qm_ prefix: under qv_, the record of module m would be qv_m, which is
    also the mangling of a user identifier m (for example, a top-level 'let real' and module 'real').
    """
    return f"qm_{clean_mod}"


def mangle_module_ident(module_name: str, name: str) -> str:
    """Mangles a module-scoped Quest identifier into a C-safe identifier prefixed with qv_<mod>_."""
    clean_mod = mangle_module_name(module_name)
    if is_symbolic_name(name):
        sym_suffix = mangle_symbolic_ident(name)[3:]  # strip leading 'qv_'
        return f"qv_{clean_mod}_{sym_suffix}"
    clean_name = name.replace(".", "_")
    return f"qv_{clean_mod}_{clean_name}"


_MAX_BETA_STEPS = 1000


def _beta_reduce_head(t: QType) -> QType:
    """Beta-reduces type operator applications at the head of t, without unfolding recursive types."""
    for _ in range(_MAX_BETA_STEPS):
        t = t.prune() if hasattr(t, "prune") else t
        if not isinstance(t, QTypeApp):
            return t
        ctor = _beta_reduce_head(t.constructor)
        if isinstance(ctor, QExceptionType) and len(t.arguments) == 1:
            return QExceptionType(payload_type=t.arguments[0])
        if not isinstance(ctor, QTypeFun) or len(ctor.params) != len(t.arguments):
            return t
        t = ctor.body.substitute({formal.symbol_id: arg for formal, arg in zip(ctor.params, t.arguments)})
    return t


# Values of a recursive type are represented like values of its unfolding (a tuple's values by a pointer to its
# struct, a function's by a closure pointer), so that the two, being equal, share a representation. Its tag is that
# of its unfolding too, except for unfoldings whose tags are built from their parts' tags: these would contain the
# tag being defined, so such a recursive type is named by its body instead (_recursive_tag).
_UNFOLDED_REPRESENTATION = (
    QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QAutoType,
    QFunType, QAllType, QExceptionType,
)
_SELF_NAMED = (QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QAutoType)


def _unfold_recursive(t: QType, kinds: tuple[type, ...] = _UNFOLDED_REPRESENTATION) -> Optional[QType]:
    """Returns the unfolding of a recursive type (or an application reducing to one) if it is a constructed type
    (one of kinds), or None otherwise."""
    if isinstance(t, QTypeApp):
        t = _beta_reduce_head(t)
    for _ in range(_MAX_BETA_STEPS):
        if not isinstance(t, (QRecType, QRecGroupType)):
            break
        t = t.unfold_lazily()
        t = t.prune() if hasattr(t, "prune") else t
        if isinstance(t, QTypeApp):
            t = _beta_reduce_head(t)
    return t if isinstance(t, kinds) else None


# ============================================================================
# Canonical forms of recursive types
# ============================================================================
#
# Recursive types are equi-recursive: a type stands for the regular tree of its unfoldings, and types with the
# same tree are equal however they are written: as a recursive type, as an unfolding written out (to any depth),
# or with a different period (`Rec(L) Option nil cons with head: Int tail: L end end` and the same type unrolled
# twice inside its Rec). Equal types share one C representation, so tags and descriptors are computed from a
# canonical form of each type that contains recursion: the graph of its nodes is minimized by partition refinement
# (as dynamic_json does for its type table), and the minimal graph is written back as a type whose recursion
# variables and type parameters have reserved ids (ReservedSymbolUse.CANONICAL_REC and CANONICAL_BINDER). Types
# are hash-consed, so the canonical form of a type in canonical form is that type itself.
#
# Nodes of the graph are tuples (with or without type components), records, variants, options, arrays, var and out
# types, function types (polymorphic or not), exception types, auto types, applications of abstract type
# operators, and occurrences of the type parameters these bind. Every other type (a free type variable, an
# abstract, path, or external type, a type operator) is a leaf, compared by identity.
#
# Binders are written by name, so they are compared up to renaming: a node that binds type parameters (a
# polymorphic function type, an auto type, a tuple with type components) is a node like any other, and an
# occurrence of one of its parameters is a node with a scope edge back to it. A type object means different things
# under different binders, so a node is keyed by its object together with the binder nodes its free variables
# refer to. Refinement follows scope edges, so two occurrences are equivalent when their binders are, and the
# minimal graph is written back with each occurrence naming the nearest enclosing binder of its binder's class.
# Merging binders could in principle mix up scopes, so _canonical_type uses a canonical form only if it is equal to
# the type it stands for (is_type_equal), and otherwise falls back to the type as written.

_MAX_CANONICAL_NODES = 100_000

_GRAPH_NODES = (
    QTupleType, QRecordType, QVariantType, QOptionType, QArrayType, QVarType, QOutType, QFunType, QAllType,
    QExceptionType, QAutoType,
)



def _check_canonical() -> bool:
    """Whether a canonical form not equal to its type, or not a fixed point, is an error rather than a warning (as
    in the tests: run_tests.py and the unit tests set QUEST_CHECK_CANONICAL=1)."""
    return os.environ.get("QUEST_CHECK_CANONICAL") == "1"


def _canonical_structure(t: QType) -> QType:
    """t with aliases, solved metavariables, type operator applications, and recursive types whose unfoldings are
    graph nodes reduced down to its outer constructor."""
    for _ in range(_MAX_BETA_STEPS):
        t = strip_aliases(t.prune() if hasattr(t, "prune") else t)
        if not isinstance(t, (QRecType, QRecGroupType, QTypeApp)):
            return t
        if (unfolded := _unfold_recursive(t, _GRAPH_NODES)) is not None:
            return unfolded
        if isinstance(t, QTypeApp):
            reduced = _beta_reduce_head(t)
            if not isinstance(reduced, (QTypeApp, QRecType, QRecGroupType)):
                t = reduced
                continue
        return t
    return t


# Kinds other than TYPE and POWER(T) (operator kinds, kind variables) are compared by identity
_OPAQUE_KINDS: dict[int, QKind] = {}


def _kind_parts(k: Optional[QKind]) -> tuple[tuple[Any, ...], list[QType]]:
    """The shape and parts of a kind, as for a node."""
    if k is None:
        return ("none",), []
    if isinstance(k, QTypeKind):
        return ("TYPE",), []
    if isinstance(k, QPowerKind):
        return ("POWER",), [k.bound]
    _OPAQUE_KINDS[id(k)] = k
    return ("kind", id(k)), []


def _kind_part_count(shape: tuple[Any, ...]) -> int:
    return 1 if shape[0] == "POWER" else 0


def _rebuild_kind(shape: tuple[Any, ...], parts: list[QType]) -> Optional[QKind]:
    if shape[0] == "none":
        return None
    if shape[0] == "TYPE":
        return TYPE_KIND
    if shape[0] == "POWER":
        return QPowerKind(parts[0])
    return _OPAQUE_KINDS[shape[1]]


_BINDER_NODES = ("all", "auto", "xtuple")


@dataclass
class _NodeInfo:
    """A node of a canonical graph before its parts are resolved: its shape (constructor and labels), its parts,
    the type parameters it binds (in order), and for an occurrence of a parameter, that parameter's symbol id."""
    shape: tuple[Any, ...]
    parts: list[QType]
    binds: tuple[int, ...] = ()
    occurrence_of: Optional[int] = None


def _canonical_node(s: QType, bound: Any) -> Optional[_NodeInfo]:
    """The node for the structure s, whose free variables in `bound` are parameters of enclosing binder nodes; None
    for a leaf."""
    if isinstance(s, (QTypeVar, QAbstractType)) and s.symbol_id in bound:
        kind_shape, kind_parts = _kind_parts(s.bound)
        cls_name = "var" if isinstance(s, QTypeVar) else "abstract"
        return _NodeInfo(("bound", cls_name, bound[s.symbol_id][1], kind_shape), kind_parts,
                         occurrence_of=s.symbol_id)
    if isinstance(s, QTupleType):
        if len(s.value_fields) == len(s.fields):
            fields = s.value_fields
            return _NodeInfo(("tuple", tuple((f.name, f.is_var) for f in fields)), [f.type_val for f in fields])
        comps: list[tuple[Any, ...]] = []
        parts: list[QType] = []
        for f in s.fields:
            if isinstance(f, QTupleTypeFormal):
                kind_shape, kind_parts = _kind_parts(f.bound)
                comps.append(("formal", f.name, kind_shape))
                parts.extend(kind_parts)
            elif isinstance(f, QTupleTypeBinding):
                kind_shape, kind_parts = _kind_parts(f.bound) if f.bound is not None else (None, [])
                comps.append(("binding", f.name, kind_shape))
                parts.append(f.type_val)
                parts.extend(kind_parts)
            else:
                comps.append(("field", f.name, f.is_var))
                parts.append(f.type_val)
        binds = tuple(f.symbol_id for f in s.fields if isinstance(f, QTupleTypeFormal))
        return _NodeInfo(("xtuple", tuple(comps)), parts, binds)
    if isinstance(s, QRecordType):
        fields = sorted(s.fields, key=lambda f: f.name)
        return _NodeInfo(("record", s.provenance, tuple((f.name, f.is_var) for f in fields)),
                         [f.type_val for f in fields])
    if isinstance(s, QVariantType):
        labels = tuple((v.name, v.is_var, v.type_val is not None) for v in s.variants)
        return _NodeInfo(("variant", labels), [v.type_val for v in s.variants if v.type_val is not None])
    if isinstance(s, QOptionType):
        labels = tuple((o.name, o.payload_type is not None) for o in s.options)
        return _NodeInfo(("option", labels), [o.payload_type for o in s.options if o.payload_type is not None])
    if isinstance(s, QArrayType):
        return _NodeInfo(("array",), [s.element_type])
    if isinstance(s, QVarType):
        return _NodeInfo(("var",), [s.element_type])
    if isinstance(s, QOutType):
        return _NodeInfo(("out",), [s.element_type])
    if isinstance(s, QFunType):
        modes = tuple((p.is_var, p.is_out) for p in s.params)
        return _NodeInfo(("fun", modes), [p.type_val for p in s.params] + [s.result_type])
    if isinstance(s, QExceptionType):
        return _NodeInfo(("exception",), [s.payload_type])
    if isinstance(s, QAllType):
        kind_shapes = []
        parts = []
        for q in s.quantifiers:
            kind_shape, kind_parts = _kind_parts(q.bound)
            kind_shapes.append(kind_shape)
            parts.extend(kind_parts)
        parts.append(s.body)
        return _NodeInfo(("all", tuple(kind_shapes)), parts, tuple(q.symbol_id for q in s.quantifiers))
    if isinstance(s, QAutoType):
        kind_shape, kind_parts = _kind_parts(s.kind_bound)
        labels = tuple((f.name, f.is_var) for f in s.signature)
        return _NodeInfo(("auto", kind_shape, labels), kind_parts + [f.type_val for f in s.signature], (s.symbol_id,))
    if isinstance(s, QTypeApp):
        # An application of an abstract type operator (one that does not reduce)
        return _NodeInfo(("app", len(s.arguments)), [s.constructor, *s.arguments])
    return None


def _rebuild_node(shape: tuple[Any, ...], parts: list[QType]) -> QType:
    """The type with the given shape (from _canonical_node) and parts, for a node that binds nothing."""
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
        # Parameter names are not part of a function type's identity; canonical ones keep equal types identical
        params = tuple(
            QParam(name=f"x{i + 1}", type_val=p, is_var=is_var, is_out=is_out)
            for i, ((is_var, is_out), p) in enumerate(zip(shape[1], parts))
        )
        return QFunType(params=params, result_type=parts[-1])
    if kind == "app":
        return QTypeApp(constructor=parts[0], arguments=tuple(parts[1:]))
    return QExceptionType(payload_type=parts[0])


@dataclass(frozen=True)
class _Leaf:
    """A leaf of a canonical graph: a type compared by identity, with the binder nodes (or classes) and positions
    of its free variables that are parameters of enclosing binders, as (symbol id, binder, position)."""
    type: QType
    bound: tuple[tuple[int, int, int], ...]


@dataclass(frozen=True)
class _Param:
    """A type parameter of a binder as written back: its symbol id, name, and kind."""
    symbol_id: int
    name: str
    kind: Optional[QKind]

    def var(self) -> QTypeVar:
        return QTypeVar(name=self.name, symbol_id=self.symbol_id, bound=self.kind)


@dataclass(frozen=True)
class _BuildContext:
    """Where a part of a canonical form is written: the recursive type being written (its root class, component,
    and variables, by class), the parameters of the enclosing binders (by class, the nearest one of each), and
    the number of enclosing parameters (which numbers the next binder's)."""
    rec_root: int = -1
    rec_comp: int = -1
    rec_vars: Any = None
    scope: Any = None
    depth: int = 0


_EMPTY_CONTEXT = _BuildContext(scope={})


class _NotCanonicalizable(Exception):
    """A type's graph is too large to canonicalize (its unfoldings do not repeat), or cannot be written back."""


_Ref = Any  # a class of a canonical graph (an int) or a _Leaf


class _CanonicalGraph:
    """The minimized graph of the nodes reachable from a type, from which canonical forms are written."""

    def __init__(self, root: QType) -> None:
        index: dict[Any, int] = {}
        self.objects: list[QType] = []  # the structure of each node (kept so that ids stay unique)
        self.closed: list[bool] = []  # whether a node's free variables are all free in the root
        shapes: list[tuple[Any, ...]] = []
        children: list[list[_Ref]] = []
        scope: list[int] = []  # for an occurrence of a parameter, its binder node; otherwise -1
        pending: list[tuple[list[QType], dict[int, tuple[int, int]]]] = []

        def ref(t: QType, bound: dict[int, tuple[int, int]]) -> _Ref:
            s = _canonical_structure(t)
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

        # Partition refinement to the coarsest bisimulation, starting from each node's shape, following scope edges
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
        """Finds the strongly connected components of the quotient graph (Tarjan's algorithm, iteratively, along
        structural edges only), whether each is cyclic, whether each class reaches a cyclic one, and the binder
        classes that each refers to (by occurrences of their parameters) and reaches."""
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
                # k roots a component; the components it reaches were all completed before it
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
        """The canonical form of class k, or None if no recursion is reachable from it."""
        if k not in self.terms:
            self.terms[k] = self.build(k, _EMPTY_CONTEXT) if self.reaches_cycle[self.component[k]] else None
        return self.terms[k]

    def _is_binder_shape(self, k: int) -> bool:
        return self.shapes[k][0] in ("tuple", "record", "variant", "option", "xtuple")

    def _aggregate_cycles(self, comp: int) -> bool:
        """Whether every cycle of a cyclic component passes through a tuple, record, variant, or option: whether
        its other nodes have no cycle among themselves."""
        if comp in self._aggregate_cycle_memo:
            return self._aggregate_cycle_memo[comp]
        others = [k for k in range(len(self.shapes)) if self.component[k] == comp and not self._is_binder_shape(k)]
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
                    if isinstance(c, int) and self.component[c] == comp and not self._is_binder_shape(c)
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
        if in_rec or not self.cyclic[comp] or (self._aggregate_cycles(comp) and not self._is_binder_shape(c)):
            # Inside the recursive type being written, not in a cycle, or a node (such as a function type) on
            # cycles that all pass through tuples, records, variants, or options, which are preferred as recursive
            # types: the node is written with each of its parts
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
            kind_val = _rebuild_kind(shape[3], [self.build(c, ctx) for c in kids])
            if shape[1] == "var":
                return QTypeVar(name=param.name, symbol_id=param.symbol_id, bound=kind_val)
            return QAbstractType(name=param.name, symbol_id=param.symbol_id, bound=kind_val)
        if kind not in _BINDER_NODES:
            return _rebuild_node(shape, [self.build(c, ctx) for c in kids])

        # A binder: its parameters are numbered by the number of enclosing ones, so that no two enclosing each
        # other share an id; each parameter's kind may refer to the parameters before it
        params: list[_Param] = []
        scope = dict(ctx.scope)
        scope[k] = params
        count = (len(shape[1]) if kind == "all" else 1 if kind == "auto"
                 else sum(1 for comp in shape[1] if comp[0] == "formal"))
        inner = dataclasses.replace(ctx, scope=scope, depth=ctx.depth + count)
        remaining = iter(kids)

        def kind_of(kind_shape: Optional[tuple[Any, ...]]) -> Optional[QKind]:
            if kind_shape is None:
                return None
            return _rebuild_kind(kind_shape, [self.build(next(remaining), inner)
                                              for _ in range(_kind_part_count(kind_shape))])

        def new_param(name: str, kind_shape: tuple[Any, ...]) -> _Param:
            index = ctx.depth + len(params)
            param = _Param(reserved_symbol_id(ReservedSymbolUse.CANONICAL_BINDER, index),
                           name if name else f"T{index}", kind_of(kind_shape))
            params.append(param)
            return param

        if kind == "all":
            quantifiers = []
            for kind_shape in shape[1]:
                param = new_param("", kind_shape)
                quantifiers.append(QQuantifier(name=param.name, symbol_id=param.symbol_id, bound=param.kind))
            return QAllType(quantifiers=tuple(quantifiers), body=self.build(next(remaining), inner))
        if kind == "auto":
            param = new_param("", shape[1])
            signature = tuple(
                QRecordField(name=name, type_val=self.build(next(remaining), inner), is_var=is_var)
                for name, is_var in shape[2]
            )
            return QAutoType(type_param=param.name, symbol_id=param.symbol_id, kind_bound=param.kind,
                             signature=signature)
        components: list[Any] = []
        for comp in shape[1]:
            if comp[0] == "formal":
                # A tuple's type components are selected by name, so formals keep their names
                param = new_param(comp[1], comp[2])
                components.append(QTupleTypeFormal(name=param.name, symbol_id=param.symbol_id, bound=param.kind))
            elif comp[0] == "binding":
                type_val = self.build(next(remaining), inner)
                components.append(QTupleTypeBinding(name=comp[1], type_val=type_val, bound=kind_of(comp[2])))
            else:
                components.append(QTupleField(name=comp[1], type_val=self.build(next(remaining), inner),
                                              is_var=comp[2]))
        return QTupleType(tuple(components))

    def _recursive_term(self, root: int, ctx: _BuildContext) -> QType:
        """The canonical form of a class on a cycle: a recursive type whose variables stand for the targets of the
        back edges of a depth-first walk of its component from root. If every cycle of the component passes through
        a tuple, record, variant, or option, the walk goes through those only (other nodes are passed through, so
        that each recursive type unfolds to one); otherwise it goes through every node."""
        comp = self.component[root]
        aggregates_only = self._aggregate_cycles(comp)
        binders: list[int] = []
        state: dict[int, int] = {}  # 1 while on the walk's path, 2 when done

        def successors(k: int) -> list[int]:
            out: list[int] = []

            def through(c: _Ref) -> None:
                if not isinstance(c, int) or self.component[c] != comp:
                    return
                if self._is_binder_shape(c) or not aggregates_only:
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


# The canonical form found for each type (None if it has none), kept with the type so that its id is not reused
_CANONICAL: dict[int, tuple[QType, Optional[QType]]] = {}
# The graph and class of each node of a canonical graph whose free variables are all free in the graph's root
_CANONICAL_NODES: dict[int, tuple[QType, _CanonicalGraph, int]] = {}


def _canonical_type(t: QType) -> Optional[QType]:
    """Returns the canonical form of t if t contains recursion and is not in canonical form, or None otherwise.

    Equal types containing recursion have the same canonical form, which therefore has their tag and descriptor.
    """
    t = t.prune() if hasattr(t, "prune") else t
    if getattr(t, "_has_meta", True):
        return None
    entry = _CANONICAL.get(id(t))
    if entry is None or entry[0] is not t:
        entry = (t, _canonical_type_uncached(t))
        _CANONICAL[id(t)] = entry
    return entry[1]


# Whether each type may contain recursion (a recursive type, or an application that may reduce to one), kept with
# the type so that its id is not reused
_MAY_RECUR: dict[int, tuple[Any, bool]] = {}


def _may_recur(node: Any) -> bool:
    """Whether a type (or a part of one, such as a field or a kind) may contain recursion: if not, its graph has no
    cycle, and it has no canonical form."""
    if isinstance(node, (QRecType, QRecGroupType, QTypeApp, QAliasType)):
        return True
    if isinstance(node, (tuple, list)):
        return any(_may_recur(item) for item in node)
    if not dataclasses.is_dataclass(node) or isinstance(node, type):
        return False
    entry = _MAY_RECUR.get(id(node))
    if entry is not None and entry[0] is node:
        return entry[1]
    result = any(_may_recur(getattr(node, f.name)) for f in dataclasses.fields(node))
    _MAY_RECUR[id(node)] = (node, result)
    return result


def _canonical_type_uncached(t: QType) -> Optional[QType]:
    if not _may_recur(t):
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
    # Merging binders could in principle mix up scopes: a canonical form is used only if it is equal to the type
    if not is_type_equal(canonical, strip_aliases(t)):
        message = f"canonical form of the type {descriptor_display_name(t)} is not equal to it"
        if _check_canonical():
            raise AssertionError(message)
        # The type is named as written, as before canonical forms compared binders; the program is still compiled
        sys.stderr.write(f"quest: warning: internal: {message}; naming it as written (please report this)\n")
        return None
    if _check_canonical() and _canonical_type(canonical) is not None:
        raise AssertionError(f"canonical form of {descriptor_display_name(t)} is not a fixed point")
    return canonical


def _register_graph(s: QType) -> Optional[_CanonicalGraph]:
    """Builds the canonical graph of a structure and records the graph and class of each of its nodes whose free
    variables are all free in s; returns None if s has no graph (it is a leaf, or its graph is too large)."""
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


def _normalize_type_raw(t: QType) -> QType:
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    if isinstance(t, (QRecType, QRecGroupType)):
        unfolded = _unfold_recursive(t)
        if unfolded is not None:
            return unfolded
    if isinstance(t, QTypeApp):
        unfolded = _unfold_recursive(t)
        if unfolded is not None:
            return unfolded
        reduced = _beta_reduce_head(t)
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


def _type_to_c_tag_uncached(t: QType) -> str:
    raw = _type_to_c_tag_raw(t)
    if len(raw) > 64:
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        return f"{raw[:24]}_{digest}"
    return raw


# A recursive type's tag is built from its body with each recursive variable replaced by one of these
# placeholders, numbered by nesting depth, so that the tag is finite and the same for alpha-equivalent types.
# Their symbol ids are reserved (ReservedSymbolUse.REC_SELF), indexed by depth.


def _is_rec_self_symbol(symbol_id: int) -> bool:
    return reserved_symbol_index(symbol_id, ReservedSymbolUse.REC_SELF) is not None


def _rec_self_var(level: int) -> QTypeVar:
    return QTypeVar(name=f"Rec.Self{level}", symbol_id=reserved_symbol_id(ReservedSymbolUse.REC_SELF, level))


def _rec_self_level(t: QType) -> Optional[int]:
    if isinstance(t, QTypeVar):
        return reserved_symbol_index(t.symbol_id, ReservedSymbolUse.REC_SELF)
    return None


def _recursive_tag(t: QType) -> Optional[str]:
    """Returns the tag of a recursive type whose unfolding's tag is built from its parts' tags (_SELF_NAMED), or None
    otherwise.

    The tag names the recursive type itself rather than its unfolding, whose tag would contain the tag being defined.
    """
    if _unfold_recursive(t, _SELF_NAMED) is None:
        return None
    if isinstance(t, QTypeApp):
        t = _beta_reduce_head(t)
    level = sum(1 for sym in t._fv if _is_rec_self_symbol(sym))
    if isinstance(t, QRecType):
        body = t.body.substitute({t.symbol_id: _rec_self_var(level)})
        return f"Rec{level}_{type_to_c_tag(body)}"
    if isinstance(t, QRecGroupType):
        subst = {b[1]: _rec_self_var(level + i) for i, b in enumerate(t.bindings)}
        tags = [type_to_c_tag(b[3].substitute(subst)) for b in t.bindings]
        return f"RecGroup{level}_{t.active_index}_" + "_".join(tags)
    return None


_AGGREGATE_TAG_PREFIXES = ("QTuple_", "QRecord_", "QVariant_", "QOption_", "Auto_")


def _element_tag(t: QType) -> str:
    """The tag of a component type inside another type's tag: an aggregate's tag, which lists its own components,
    is closed with _end, so that tags of different nestings differ (Tuple (Tuple A Int) end and Tuple (Tuple A) Int
    end)."""
    tag = type_to_c_tag(t)
    if tag.startswith(_AGGREGATE_TAG_PREFIXES) and not tag.endswith("_empty"):
        return f"{tag}_end"
    return tag


def _type_to_c_tag_raw(t: QType) -> str:
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    t = resolve_type_bound(t)
    if (self_level := _rec_self_level(t)) is not None:
        return f"Self{self_level}"
    if (canonical := _canonical_type(t)) is not None:
        # Equal types share a tag: a type containing recursion is named by its canonical form
        return type_to_c_tag(canonical)
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
    if isinstance(t, QTypeVar) and t.name == "Writer.T":
        return "QWriter"
    if isinstance(t, QTypeVar) and t.name == "Reader.T":
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
        return "Auto_" + type_to_c_tag(auto_payload_type(t))
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


def _type_digest(t: QType) -> str:
    """A short digest of a type's printed text, telling apart types that type_to_c_tag conflates (see _printed)."""
    t = normalize_type(strip_aliases(t.prune() if hasattr(t, "prune") else t))
    if (canonical := _canonical_type(t)) is not None:
        t = normalize_type(canonical)
    return _printed(t)[1][:16]


def _text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# Digests of types stand for their printed text (str), which is the same in every compilation, but printing
# shares nothing, so a large recursive type prints as megabytes. A type whose text is at most this long is
# digested from its text; a longer one from the text of its outermost node with the digests of its parts
# in place of theirs, computed once per hash-consed node. Either way types that print differently get
# different digests.
_PRINTED_TEXT_LIMIT = 1024


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
            part_length, part_digest = _printed(part)
            length += part_length
            pieces.append("\0" + part_digest)
    if length <= _PRINTED_TEXT_LIMIT:
        return length, hashlib.sha256(str(node).encode("utf-8")).hexdigest()
    return length, hashlib.sha256(("\1" + "".join(pieces)).encode("utf-8")).hexdigest()


_PRINTED_PARTS: dict[int, tuple[Any, tuple[int, str]]] = {}


def _printed(node: Any) -> tuple[int, str]:
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


def _opaque_name(t: QType) -> str:
    """The name of an opaque descriptor, by which descriptors are compared: the type as printed, or for a type that
    prints longer than _PRINTED_TEXT_LIMIT, the start of it followed by the digest of the whole."""
    length, digest = _printed(t)
    if length <= _PRINTED_TEXT_LIMIT:
        return str(t)
    return f"{descriptor_display_name(t)}#{digest[:16]}"


def fun_descriptor_tag(t: QType) -> str:
    """The tag of the runtime descriptor of a function type (QFunType or QAllType).

    type_to_c_tag is QClosure for every function type, which suits struct naming (all closures are represented
    alike) but not descriptors, which must tell function types apart. Equal types that differ only in the names
    of their type and value parameters share a tag (see canonical_fun_type).
    """
    return "fun_" + _type_digest(canonical_fun_type(t))


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
        bound = bound.substitute_types({quants[j].symbol_id: bound_var(k - 1 - j, new_quants[j].bound) for j in range(k)})
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


class MissingDescriptorError(Exception):
    """A type has no runtime type descriptor (such as Var(T) or a type operator)."""


@dataclass(frozen=True)
class DescriptorForm:
    """How a type is described at run time.

    kind is one of base and bound_var (expr is the descriptor expression), or record, tuple, variant, option,
    array, exception, fun, auto, opaque, and hole (the descriptor is quest_type_<tag>, describing `type`; an opaque
    descriptor is compared by `name` and, for an application of an abstract type operator (`type` is a QTypeApp),
    its arguments; a hole's `name` is its index).
    """
    kind: str
    tag: str = ""
    type: Optional[QType] = None
    name: str = ""
    expr: str = ""
    struct: str = ""  # the C struct laid out as `type`, when its name is not derived from `type` itself

    @property
    def c_expr(self) -> str:
        return self.expr if self.expr else f"(&quest_type_{self.tag})"


_BASE_DESCRIPTORS: dict[int, str] = {}


_DISPLAY_NAME_LIMIT = 80


class _DisplayNameFull(Exception):
    """The display name being printed has reached its limit."""


def descriptor_display_name(t: QType) -> str:
    """A short name for a type's descriptor, used only in diagnostics: the type as printed, cut off at 80 characters.

    Descriptors are compared structurally and serialized from their structure, so the name need not identify the
    type (printing a large recursive type in full can take megabytes). A recursive type prints as its variable.
    """
    parts: list[str] = []
    size = 0

    def emit(text: str) -> None:
        nonlocal size
        parts.append(text)
        size += len(text)
        if size > _DISPLAY_NAME_LIMIT:
            raise _DisplayNameFull()

    def walk(t: Optional[QType]) -> None:
        if t is None:
            return
        t = unalias(t.prune() if hasattr(t, "prune") else t)
        if isinstance(t, QRecordType):
            emit("Record")
            for f in t.fields:
                emit(f" {'var ' if f.is_var else ''}{f.name}: ")
                walk(f.type_val)
            emit(" end")
        elif isinstance(t, QTupleType):
            emit("Tuple")
            for f in t.value_fields:
                emit(f" {'var ' if f.is_var else ''}{f.name}: " if f.name else " :")
                walk(f.type_val)
            emit(" end")
        elif isinstance(t, (QVariantType, QOptionType)):
            emit("Variant" if isinstance(t, QVariantType) else "Option")
            cases = (
                [(v.name, v.type_val) for v in t.variants] if isinstance(t, QVariantType)
                else [(o.name, o.payload_type) for o in t.options]
            )
            for name, payload in cases:
                emit(f" {name}")
                if payload is not None:
                    emit(": ")
                    walk(payload)
            emit(" end")
        elif isinstance(t, QArrayType):
            emit("Array(")
            walk(t.element_type)
            emit(")")
        elif isinstance(t, QExceptionType):
            emit("Exception(")
            walk(t.payload_type)
            emit(")")
        elif isinstance(t, QFunType):
            emit("Fun(")
            for i, p in enumerate(t.params):
                emit(f"{' ' if i else ''}{'var ' if p.is_var else 'out ' if p.is_out else ''}{p.name}: ")
                walk(p.type_val)
            emit(") ")
            walk(t.result_type)
        elif isinstance(t, QAllType):
            emit("All(" + " ".join(q.name for q in t.quantifiers) + ") ")
            walk(t.body)
        elif isinstance(t, QAutoType):
            emit(f"Auto {t.type_param} with")
            for f in t.signature:
                emit(f" {'var ' if f.is_var else ''}{f.name}: ")
                walk(f.type_val)
            emit(" end")
        elif isinstance(t, QRecType):
            emit(t.var_name)
        elif isinstance(t, QTypeApp):
            walk(t.constructor)
            emit("(")
            for i, a in enumerate(t.arguments):
                if i:
                    emit(" ")
                walk(a)
            emit(")")
        elif isinstance(t, (QRecGroupType, QTypeFun)):
            emit(type(t).__name__)
        else:
            emit(str(t))

    try:
        walk(t)
    except _DisplayNameFull:
        return "".join(parts)[:_DISPLAY_NAME_LIMIT] + "..."
    return "".join(parts)


def descriptor_form(t: QType, ctx: Optional["RecordNamingContext"] = None) -> DescriptorForm:
    """Decides the runtime descriptor of a closed type (type parameters in scope are the emitter's business).

    Each distinct type gets its own tag: tags of compound types include a digest of the type, because C tags
    conflate types with the same representation (every closure is a QClosure, every type variable a QVal).
    Recursive types are described by their unfoldings, which refer back to them by tag, so their descriptors are
    cyclic. Raises MissingDescriptorError for types that have none.
    """
    t = t.prune() if hasattr(t, "prune") else t
    t = strip_aliases(t)
    if (index := hole_index(t)) is not None:
        # A template's hole (before normalization, which would replace a bounded hole by its bound)
        bound = t.bound
        tag = f"hole_{index}_{_type_digest(bound.bound)}" if isinstance(bound, QPowerKind) else f"hole_{index}"
        return DescriptorForm("hole", tag=tag, type=t, name=str(index))
    t = normalize_type(t)
    if (canonical := _canonical_type(t)) is not None:
        # Equal types share a descriptor: a type containing recursion is described by its canonical form
        t = normalize_type(canonical)
    if not _BASE_DESCRIPTORS:
        _BASE_DESCRIPTORS.update({
            id(INT_TYPE): "&quest_type_Int", id(REAL_TYPE): "&quest_type_Real", id(BOOL_TYPE): "&quest_type_Bool",
            id(CHAR_TYPE): "&quest_type_Char", id(STRING_TYPE): "&quest_type_String", id(OK_TYPE): "&quest_type_Ok",
        })
    if id(t) in _BASE_DESCRIPTORS:
        return DescriptorForm("base", expr=_BASE_DESCRIPTORS[id(t)])
    if (index := bound_var_index(t)) is not None:
        return DescriptorForm("bound_var", expr=f"(&quest_type_bound_vars[{index}])")
    if isinstance(t, QTupleType) and not t.fields:
        return DescriptorForm("base", expr="&quest_type_EmptyTuple")
    if isinstance(t, QRecordType) or (rec_b := resolve_record_bound(t)) is not None:
        rec_t = t if isinstance(t, QRecordType) else rec_b
        return DescriptorForm("record", tag=record_struct_name(rec_t, ctx), type=rec_t)
    if isinstance(t, QTupleType):
        return DescriptorForm("tuple", tag=f"{tuple_struct_name(t)}_{_type_digest(t)}", type=t)
    if isinstance(t, QVariantType) or (var_b := resolve_variant_bound(t)) is not None:
        var_t = t if isinstance(t, QVariantType) else var_b
        return DescriptorForm("variant", tag=f"{type_to_c_tag(var_t)}_{_type_digest(var_t)}", type=var_t)
    if isinstance(t, QOptionType) or (opt_b := resolve_option_bound(t)) is not None:
        opt_t = t if isinstance(t, QOptionType) else opt_b
        return DescriptorForm(
            "option",
            tag=f"{option_struct_name(opt_t)}_{_type_digest(opt_t)}",
            type=opt_t,
            struct=option_struct_name(opt_t),
        )
    # Records, variants, and options above resolve as the C type mapping does (their structs are named that
    # way); other recursive types and type applications are described by their unfoldings
    if isinstance(t, (QRecType, QRecGroupType)) or isinstance(t, QTypeApp):
        unfolded = t.evaluate_lazily()
        if unfolded is not t and not isinstance(unfolded, QTypeApp):
            return descriptor_form(unfolded, ctx)
        if isinstance(t, QTypeApp):
            # An application of an abstract type operator (list.T(Int)): opaque, compared by the operator's name
            # and the arguments
            name = _opaque_name(t.constructor)
            return DescriptorForm("opaque", tag=f"opaque_{_type_digest(t)}", name=name, type=t)
        raise MissingDescriptorError(f"no runtime type descriptor for the recursive type '{t}'")
    if isinstance(t, QArrayType):
        return DescriptorForm("array", tag=f"array_{_type_digest(t)}", type=t)
    if isinstance(t, QExceptionType):
        return DescriptorForm("exception", tag=f"exception_{_type_digest(t)}", type=t)
    if isinstance(t, (QFunType, QAllType)):
        canonical = canonical_fun_type(t)
        return DescriptorForm("fun", tag=f"fun_{_type_digest(canonical)}", type=canonical)
    if isinstance(t, QExternalType):
        name = t.name or t.c_type
        return DescriptorForm("opaque", tag=f"opaque_{mangle_ident(name)}", name=name)
    if isinstance(t, (QTypeVar, QAbstractType)):
        return DescriptorForm("opaque", tag=f"opaque_{mangle_ident(t.name)}", name=t.name)
    if isinstance(t, QPathType):
        # An abstract type of a package value (t.A): opaque, and distinct for each binding of t
        name = f"{t.root_name}.{t.field_name}#{t.root_symbol_id}"
        return DescriptorForm("opaque", tag=f"opaque_{_text_digest(name)}", name=name)
    if isinstance(t, QAutoType):
        canonical = canonical_auto_type(t)
        return DescriptorForm("auto", tag=f"auto_{_type_digest(canonical)}", type=canonical)
    if isinstance(t, (QVarType, QOutType)):
        # The type of a var or out parameter: described by its element type
        return descriptor_form(t.element_type, ctx)
    if isinstance(t, QTypeFun):
        # A type operator, passed for a higher-kinded type parameter: opaque, compared by name
        name = _opaque_name(t)
        return DescriptorForm("opaque", tag=f"opaque_{_text_digest(name)}", name=name)
    raise MissingDescriptorError(f"no runtime type descriptor for type '{t}'")



def tuple_struct_name(t: QTupleType) -> str:
    """Returns the C struct tag name for a given QTupleType."""
    return type_to_c_tag(t)


def record_struct_name(t: QRecordType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Returns the C struct tag name for a given QRecordType."""
    if ctx is not None:
        name = ctx.get_or_create_name(t)
        return f"QT_{name}"
    return type_to_c_tag(t)


def option_struct_name(t: QType) -> str:
    """Returns the C struct tag name for a given QOptionType."""
    return type_to_c_tag(t)


class RecordNamingContext:
    """Maintains sequential and alias-based naming for record types and evidence dictionaries."""

    def __init__(self) -> None:
        self.alias_by_shape: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.seq_by_shape: dict[tuple[tuple[str, str, str], ...], str] = {}
        self.shape_to_canonical_name: dict[tuple[tuple[str, str, str], ...], str] = {}
        self._record_counter = 0

    def _shape_key(self, t: QRecordType) -> tuple[tuple[str, str, str], ...]:
        # Records share a struct (and so a descriptor) only if their fields have the same types, not merely the same
        # C representations: type_to_c_tag is QClosure for every function type and QVal for every type variable.
        sorted_fields = sorted(t.fields, key=lambda f: f.name)
        return tuple((f.name, type_to_c_tag(f.type_val), _type_digest(f.type_val)) for f in sorted_fields)

    def register_alias(self, alias_name: str, t: QRecordType) -> None:
        key = self._shape_key(t)
        if key not in self.alias_by_shape:
            self.alias_by_shape[key] = alias_name
            self.shape_to_canonical_name[key] = alias_name

    def get_or_create_name(self, t: QRecordType, module_name: Optional[str] = None) -> str:
        key = self._shape_key(t)
        if key in self.shape_to_canonical_name:
            return self.shape_to_canonical_name[key]
        self._record_counter += 1
        prefix = f"{module_name}_" if module_name else ""
        name = f"{prefix}record{self._record_counter}"
        self.seq_by_shape[key] = name
        self.shape_to_canonical_name[key] = name
        return name

    def record_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"QT_{name}"

    def offset_dict_struct_name(self, t: QRecordType) -> str:
        name = self.get_or_create_name(t)
        return f"OffsetDict_{name}"

    def offset_dict_instance_name(self, target: QRecordType, source: QRecordType) -> str:
        tgt_name = self.get_or_create_name(target)
        src_name = self.get_or_create_name(source)
        return f"offsetdict_{tgt_name}_{src_name}"


def _qtype_to_c_type_raw(t: QType) -> str:
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
    if isinstance(t, QTypeVar) and t.name == "Writer.T":
        return "QWriter *"
    if isinstance(t, QTypeVar) and t.name == "Reader.T":
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
        return f"{qtype_to_c_type(t.element_type)} *"
    if isinstance(t, (QTypeVar, QAbstractType, QPathType)):
        return "QVal"
    return "QVal"


# ============================================================================
# Representation lowering
# ============================================================================
#
# A type's C representation (its normalized form, struct tag, C type, and whether it is Word.T)
# depends only on the type node: the steps that choose it (alias stripping, bound resolution,
# beta reduction, unfolding) read nothing but the node and its children, and the bounds of type
# variables and path types are fields of those nodes. Because types are hash-consed, each
# representation is computed once per canonical node and kept for the whole process. Nodes
# containing a metavariable are lowered afresh every time, since a later solution can change them.


_UNSET = object()


class CRepr:
    """The C representation of one type; each part is computed on first use."""

    __slots__ = ("type", "_normalized", "_tag", "_c_type", "_is_word", "_printed")

    def __init__(self, t: QType) -> None:
        self.type = t
        self._normalized = self._tag = self._c_type = self._is_word = self._printed = _UNSET

    @property
    def normalized(self) -> QType:
        if self._normalized is _UNSET:
            self._normalized = _normalize_type_raw(self.type)
        return self._normalized

    @property
    def tag(self) -> str:
        if self._tag is _UNSET:
            self._tag = _type_to_c_tag_uncached(self.type)
        return self._tag

    @property
    def c_type(self) -> str:
        if self._c_type is _UNSET:
            self._c_type = _qtype_to_c_type_raw(self.type)
        return self._c_type

    @property
    def is_word(self) -> bool:
        if self._is_word is _UNSET:
            self._is_word = _is_word_type_raw(self.type)
        return self._is_word

    @property
    def printed(self) -> tuple[int, str]:
        """The length of str(type) and a digest of it (see _printed)."""
        if self._printed is _UNSET:
            self._printed = _printed_uncached(self.type)
        return self._printed


_LOWERED: dict[int, CRepr] = {}


def lower_type(t: QType) -> CRepr:
    """Returns the C representation of t, shared by every use of the same canonical type."""
    t = t.prune() if hasattr(t, "prune") else t
    if getattr(t, "_has_meta", True):
        return CRepr(t)
    entry = _LOWERED.get(id(t))
    if entry is None or entry.type is not t:
        entry = CRepr(t)
        _LOWERED[id(t)] = entry
    return entry


def normalize_type(t: QType) -> QType:
    """Reduces type operator applications so that C representations are chosen from the reduced type.

    Applications whose head reduces to a non-recursive type are replaced by that type; applications that
    reduce to a recursive type are only unfolded when the unfolding is a concrete tuple or record type. A recursive
    type whose unfolding is a tuple type is replaced by that unfolding.
    """
    return lower_type(t).normalized


def is_word_type(t: QType) -> bool:
    """Returns True if t is the standard library Word.T type."""
    return lower_type(t).is_word


def type_to_c_tag(t: QType) -> str:
    """Produces a deterministic, valid C identifier component for a QType."""
    return lower_type(t).tag


def qtype_to_c_type(t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Maps a semantic Quest QType to its corresponding C scalar or pointer type representation."""
    return lower_type(t).c_type


def qtype_to_name_str(t: QType) -> str:
    """Returns the human-readable Quest type name string for runtime diagnostics and printing."""
    t = t.prune() if hasattr(t, "prune") else t
    if isinstance(t, QAliasType):
        return t.name
    if is_word_type(t):
        return "Word.T"
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


def c_string_literal(s: str) -> str:
    """Escapes a Python string into a safe C string literal."""
    parts = []
    for ch in s:
        if ch == "\"":
            parts.append("\\\"")
        elif ch == "\\":
            parts.append("\\\\")
        elif ch == "\n":
            parts.append("\\n")
        elif ch == "\t":
            parts.append("\\t")
        elif ch == "\r":
            parts.append("\\r")
        elif 32 <= ord(ch) < 127:
            parts.append(ch)
        else:
            parts.append(f"\\x{ord(ch):02x}")
    return "\"" + "".join(parts) + "\""


def c_char_literal(ch: str) -> str:
    """Escapes a single Python character into a C char literal."""
    if ch == "\'":
        return "'\\''"
    if ch == "\\":
        return "'\\\\'"
    if ch == "\n":
        return "'\\n'"
    if ch == "\t":
        return "'\\t'"
    if ch == "\r":
        return "'\\r'"
    if 32 <= ord(ch) < 127:
        return f"'{ch}'"
    return f"'\\x{ord(ch):02x}'"


def qval_wrap(expr_str: str, t: QType) -> str:
    """Wraps a scalar or pointer expression into a QVal union initializer."""
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if qtype_to_c_type(t) == "QVal":
        return expr_str
    if t is OK_TYPE:
        return "Q_OK_VAL"
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return f"((QVal){{ .p = (void *)quest_record_box({expr_str}) }})"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return f"((QVal){{ .p = (void *)quest_variant_box({expr_str}) }})"
    if is_word_type(t):
        return f"((QVal){{ .u = (uint64_t)({expr_str}) }})"
    if t is INT_TYPE or t is BOOL_TYPE or t is CHAR_TYPE:
        return f"((QVal){{ .i = (int64_t)({expr_str}) }})"
    if t is REAL_TYPE:
        return f"((QVal){{ .r = (double)({expr_str}) }})"
    return f"((QVal){{ .p = (void *)({expr_str}) }})"


def qval_unwrap(qval_expr: str, t: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Extracts the underlying concrete scalar or pointer from a QVal expression."""
    t = t.prune() if hasattr(t, "prune") else t
    t = resolve_type_bound(t)
    t = normalize_type(t)
    if qtype_to_c_type(t, ctx) == "QVal":
        return qval_expr
    if isinstance(t, QRecordType) or resolve_record_bound(t) is not None:
        return f"(*((QRecordVal *)({qval_expr}.p)))"
    if isinstance(t, QVariantType) or resolve_variant_bound(t) is not None:
        return f"(*((QVariantVal *)({qval_expr}.p)))"
    if is_word_type(t):
        return f"({qval_expr}.u)"
    if t is INT_TYPE or t is BOOL_TYPE or t is CHAR_TYPE:
        return f"({qval_expr}.i)"
    if t is REAL_TYPE:
        return f"({qval_expr}.r)"
    if t is OK_TYPE:
        return "((void)0)"
    c_t = qtype_to_c_type(t, ctx)
    return f"(({c_t})({qval_expr}.p))"


def closure_fn_ptr_type(fun_type: QType, ctx: Optional[RecordNamingContext] = None) -> str:
    """Constructs the C function pointer cast type for invoking a closure."""
    quantifiers: tuple[Any, ...] = ()
    cur_type = normalize_type(fun_type)  # a recursive function type is called as its unfolding is
    while isinstance(cur_type, QAllType):
        quantifiers = quantifiers + cur_type.quantifiers
        cur_type = normalize_type(cur_type.body)

    if isinstance(cur_type, QFunType):
        if cur_type.result_type is OK_TYPE:
            ret_c = "void"
        elif isinstance(cur_type.result_type, QRecordType):
            ret_c = "QRecordVal"
        else:
            ret_c = qtype_to_c_type(cur_type.result_type, ctx)
        param_types = ["void *"]
        # Quantifier descriptors appear immediately after env
        for _ in quantifiers:
            param_types.append("const QTypeDescriptor *")
        for p in cur_type.params:
            if getattr(p, "is_out", False) or getattr(p, "is_var", False):
                param_types.append(f"{qtype_to_c_type(p.type_val, ctx)} *")
            elif p.type_val is OK_TYPE:
                param_types.append("QVal")
            else:
                param_types.append(qtype_to_c_type(p.type_val, ctx))
        sig = ", ".join(param_types)
        return f"{ret_c} (*)({sig})"

    ret_c = "void" if cur_type is OK_TYPE else (
        "QRecordVal" if isinstance(cur_type, QRecordType)
        else qtype_to_c_type(cur_type, ctx)
    )
    param_types = ["void *"]
    for _ in quantifiers:
        param_types.append("const QTypeDescriptor *")
    sig = ", ".join(param_types)
    return f"{ret_c} (*)({sig})"


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
        s_c = qtype_to_c_type(s.value_fields[i].type_val)
        t_c = qtype_to_c_type(t.value_fields[i].type_val)
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
