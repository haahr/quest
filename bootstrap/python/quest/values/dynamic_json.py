"""Serialization of Quest dynamic values (dynamic.extern and dynamic.intern),
format version 1.

A serialized dynamic value is one JSON document holding a type table and a value
(docs/dynamic.md §2):

    {"quest": 1, "types": [<type node>, ...], "type": <type ref>,
     "value": <value>}

A type ref is a built-in type name or an index into the table; recursive types
are cycles in the table. The table is canonical, so that the interpreter and
compiled code write the same text for the same value: the writer builds the
graph of the types it meets, merges structurally equivalent nodes (the coarsest
bisimulation), and numbers the remaining nodes in the order a depth-first walk
from the roots first reaches them. Values are decoded by following their type,
and objects reached more than once are written once, with @id, and then as
{"@ref": n}.
"""

from __future__ import annotations

import json
import math
from typing import Any, Optional, Union

from quest.types.env import allocate_symbol_id
from quest.values.model import (
    DYNAMIC_ERROR_EXC,
    QuestException,
    FALSE_VALUE,
    OK_VALUE,
    TRUE_VALUE,
    QArray,
    QAutoVal,
    QBool,
    QChar,
    QInt,
    QOption,
    QReal,
    QRecord,
    QRef,
    QString,
    QTuple,
    QValue,
    QVariant,
    QWord,
)
from quest.modules.abstract_types import (
    ModuleAbstractType,
    abstract_type_by_name,
    abstract_type_by_symbol,
    abstract_type_symbol_id,
    register_unlinked_abstract_type,
)
from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionField,
    QOptionType,
    QParam,
    QRecGroupType,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QType,
    QKind,
    QPowerKind,
    QTypeApp,
    QTypeKind,
    QTypeVar,
    QVariantField,
    QVariantType,
    is_subtype,
    is_type_equal,
    unalias,
    pruned,
)

FORMAT_VERSION = 1

# Graphs larger than this come from types that are not regular (their unfoldings
# never repeat)
_MAX_TYPE_NODES = 100_000

TypeRef = Union[str, int]


def _fail() -> QuestException:
    return QuestException(DYNAMIC_ERROR_EXC)


def parse_type_string(type_str: str) -> QType:
    """Parses and elaborates a Quest type expression (used for fixed schema
    types, such as that of .qi files)."""
    base_types: dict[str, QType] = {
        "Int": INT_TYPE,
        "Real": REAL_TYPE,
        "Bool": BOOL_TYPE,
        "Char": CHAR_TYPE,
        "String": STRING_TYPE,
        "Ok": OK_TYPE,
        "Dynamic": DYNAMIC_TYPE,
        "Exception": EXCEPTION_TYPE,
    }
    cleaned = type_str.strip()
    if cleaned in base_types:
        return base_types[cleaned]

    try:
        from quest.diagnostics import QuestCompilerError
        from quest.typechecker.elaborate_types import elaborate_type
        from quest.types.env import Environment
        from quest.syntax.grammar import parse_quest_program
        from quest.syntax.tokenizer import Tokenizer
        from quest.syntax.sources import SourceMap

        source_map = SourceMap(cleaned, "<type>")
        tokens = Tokenizer(cleaned, "<type>").tokenize_all()
        ast_type = parse_quest_program(tokens, source_map, target="Type")
        env = Environment()
        return elaborate_type(ast_type, env)
    except (QuestCompilerError, ValueError):
        raise _fail() from None


# ============================================================================
# Type nodes
# ============================================================================
#
# A node is (shape, children). The shape holds the constructor and its labels;
# children are type refs, in the order the node lists them: record fields sorted
# by name, tuple components and function parameters in order (then the
# function's result), variant and option cases in declaration order (only those
# with a payload), an abstract type's arguments (then its representation), and
# an auto type's bound (if it has one, then its components). A param node refers
# to the type parameter of the auto type N auto types out from it (0 is the
# innermost), as descriptors do (de Bruijn indices).

# The external types whose values can be externed, and how: word.T is external
# "uint64_t", written as an integer
_EXTERNAL_TYPES = ("uint64_t",)
_WORD_LIMIT = 1 << 64

_BUILTIN_TYPES: dict[str, QType] = {
    "Ok": OK_TYPE,
    "Bool": BOOL_TYPE,
    "Char": CHAR_TYPE,
    "String": STRING_TYPE,
    "Int": INT_TYPE,
    "Real": REAL_TYPE,
    "Dynamic": DYNAMIC_TYPE,
}
_BUILTIN_NAMES: dict[int, str] = {id(t): name for name, t in _BUILTIN_TYPES.items()}


def _is_dynamic_type(t: QType) -> bool:
    """True for Auto A::TYPE with a:A end, the type of dynamic values, whatever
    its parameter is named."""
    if not isinstance(t, QAutoType) or t.kind_bound is not TYPE_KIND or len(t.signature) != 1:
        return False
    f = t.signature[0]
    return f.name == "a" and not f.is_var and isinstance(f.type_val, QTypeVar) and f.type_val.symbol_id == t.symbol_id


def _structure(t: QType) -> QType:
    """t with aliases, solved metavariables, applications, and recursion
    unfolded down to its outer constructor."""
    for _ in range(1000):
        t = pruned(t)
        t = unalias(t)
        if isinstance(t, (QRecType, QRecGroupType, QTypeApp)):
            unfolded = t.evaluate_lazily()
            if unfolded is t:
                return t
            t = unfolded
            continue
        return t
    raise _fail()


def _is_unbounded(kind: QKind) -> bool:
    """Whether an abstract type of this kind is encodable: TYPE or POWER(B), or
    an operator from types to TYPE."""
    if isinstance(kind, QPowerKind):
        return True
    while isinstance(kind, QAllKind):
        if not isinstance(kind.param_kind, QTypeKind):
            return False
        kind = kind.result_kind
    return isinstance(kind, QTypeKind)


def _module_abstract_type(s: QType) -> Optional[tuple[ModuleAbstractType, tuple[QType, ...]]]:
    """The module abstract type s is, or is an application of, with the
    application's arguments."""
    args: tuple[QType, ...] = ()
    if isinstance(s, QTypeApp):
        args = s.arguments
        s = unalias(pruned(s.constructor))
    if not isinstance(s, QTypeVar):
        return None
    entry = abstract_type_by_symbol(s.symbol_id)
    if entry is None or not _is_unbounded(entry.type_var.bound):
        return None
    return entry, args


def _representation(entry: ModuleAbstractType, args: tuple[QType, ...]) -> QType:
    """The representation of a module abstract type, or of an application of an
    abstract type operator."""
    if entry.linked:
        if entry.rep is None:  # a module known only through its interface
            raise _fail()
        return QTypeApp(constructor=entry.rep, arguments=args) if args else entry.rep
    for instance_args, rep in entry.instances:  # a type read from a module the program does not link
        if len(instance_args) == len(args) and all(is_type_equal(a, b) for a, b in zip(instance_args, args)):
            return rep
    raise _fail()


def _var_label(name: str, is_var: bool) -> str:
    if not is_var:
        return name
    return f"var {name}" if name else "var"


class _TypeGraph:
    """The graph of the types a value mentions, from which the document's type
    table is made (_canonical_table).

    ref(t) returns how the table refers to t: a built-in type by its name
    ("Int", "String", "Dynamic"), and any other type by the index of its node,
    which it adds, with the nodes of its parts, the first time it meets the
    type. A node is a shape (its constructor and labels: a record's field
    names, an option's case names) and the refs of its parts, so that

        Let Rec L = Option nil cons with head: Int tail: L end end

    is two nodes, the option and its payload tuple, and the tuple's tail
    refers back to the option:

        {"option": {"cons": 1, "nil": null}}
        {"tuple": [["head", "Int"], ["tail", 0]]}

    Nodes are keyed by the identity of a type's structure: types are
    hash-consed (made once for each structure), so equal types written alike
    share one, and a recursive type
    becomes a cycle as its unfolding reaches the type again. Equal types
    written differently may make separate nodes, which the canonical table
    merges.

    Inside an auto type (a value packed with a type it hides, its witness), an
    occurrence of its type parameter is a param node
    numbered by how many auto types lie between it and its binder (0 for the
    nearest), and a type that mentions such parameters is a node for each way
    it refers to them."""

    def __init__(self) -> None:
        self.nodes: list[Optional[tuple[tuple[Any, ...], tuple[TypeRef, ...]]]] = []
        self._index: dict[Any, int] = {}
        self._keep: list[QType] = []
        # The type parameters of the auto types around the type being added,
        # innermost last
        self._binders: list[int] = []

    def ref(self, t: QType) -> TypeRef:
        s = _structure(t)
        name = _BUILTIN_NAMES.get(id(s))
        if name is not None:
            return name
        if _is_dynamic_type(s):
            return "Dynamic"
        if isinstance(s, QTypeVar) and s.symbol_id in self._binders:
            return self._add(("param", len(self._binders) - 1 - self._binders.index(s.symbol_id)), s, None)
        # A type that mentions enclosing auto types' parameters is a node for
        # each way it refers to them
        key = (id(s), tuple(
            (b, len(self._binders) - 1 - i) for i, b in enumerate(self._binders) if b in s._fv
        ))
        return self._add(key, s, s)

    def _add(self, key: Any, s: QType, structure: Optional[QType]) -> int:
        index = self._index.get(key)
        if index is not None:
            return index
        if len(self.nodes) >= _MAX_TYPE_NODES:
            raise _fail()
        index = len(self.nodes)
        self._index[key] = index
        self._keep.append(s)
        self.nodes.append(None)
        self.nodes[index] = self._node(structure) if structure is not None else ((key[0], key[1]), ())
        return index

    def _node(self, s: QType) -> tuple[tuple[Any, ...], tuple[TypeRef, ...]]:
        match s:
            case QRecordType():
                fields = sorted(s.fields, key=lambda f: f.name)
                labels = tuple(_var_label(f.name, f.is_var) for f in fields)
                return ("record", labels), tuple(self.ref(f.type_val) for f in fields)
            case QTupleType():
                components = s.value_fields
                if len(components) != len(s.fields):
                    raise _fail()  # type components (an abstract tuple): not encodable yet
                labels = tuple(_var_label(f.name or "", f.is_var) for f in components)
                return ("tuple", labels), tuple(self.ref(f.type_val) for f in components)
            case QVariantType() | QOptionType():
                # Cases are listed by name, as compiled code numbers them
                # (docs/dynamic.md §2.2)
                if isinstance(s, QVariantType):
                    cases = [
                        (_var_label(v.name, v.is_var), v.type_val) for v in sorted(s.variants, key=lambda v: v.name)
                    ]
                else:
                    cases = [(o.name, o.payload_type) for o in sorted(s.options, key=lambda o: o.name)]
                shape = ("variant" if isinstance(s, QVariantType) else "option",
                         tuple(label for label, _ in cases), tuple(p is not None for _, p in cases))
                return shape, tuple(self.ref(p) for _, p in cases if p is not None)
            case QArrayType():
                return ("array",), (self.ref(s.element_type),)
            case QFunType():
                modes = tuple("var" if p.is_var else "out" if p.is_out else "" for p in s.params)
                return ("fun", modes), tuple(self.ref(p.type_val) for p in s.params) + (self.ref(s.result_type),)
            case QExceptionType():
                return ("exception",), (self.ref(s.payload_type),)
            case QExternalType() if s.c_type in _EXTERNAL_TYPES:
                return ("external", s.c_type), ()
            case QAutoType():
                if isinstance(s.kind_bound, QPowerKind):
                    bound: tuple[TypeRef, ...] = (self.ref(s.kind_bound.bound),)
                elif s.kind_bound is TYPE_KIND or isinstance(s.kind_bound, QTypeKind):
                    bound = ()
                else:
                    raise _fail()
                labels = tuple(_var_label(f.name, f.is_var) for f in s.signature)
                self._binders.append(s.symbol_id)
                try:
                    components = tuple(self.ref(f.type_val) for f in s.signature)
                finally:
                    self._binders.pop()
                return ("auto", labels, bool(bound)), bound + components
        abstract = _module_abstract_type(s)
        if abstract is not None:
            entry, args = abstract
            children = tuple(self.ref(a) for a in args)
            return ("abstract", entry.global_name, len(args)), children + (self.ref(_representation(entry, args)),)
        # Polymorphic types, other abstract and external types, and type
        # operators: not encodable
        raise _fail()


def _canonical_table(
    nodes: list[Any], roots: list[TypeRef]
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    """Merges equivalent nodes and numbers the rest from the roots; returns the
    table and each node's index in it."""
    shape_ids: dict[Any, int] = {}
    cls = [shape_ids.setdefault(shape, len(shape_ids)) for shape, _ in nodes]
    count = len(shape_ids)
    while True:
        sigs: dict[Any, int] = {}
        refined = [
            sigs.setdefault((cls[i], tuple(c if isinstance(c, str) else cls[c] for c in children)), len(sigs))
            for i, (_, children) in enumerate(nodes)
        ]
        if len(sigs) == count:
            break
        cls, count = refined, len(sigs)

    number: dict[int, int] = {}  # class -> table index
    order: list[int] = []  # a representative node of each class, in table order

    def visit(ref: TypeRef) -> None:
        if isinstance(ref, str) or cls[ref] in number:
            return
        number[cls[ref]] = len(order)
        order.append(ref)
        for child in nodes[ref][1]:
            visit(child)

    for root in roots:
        visit(root)

    def mapped(ref: TypeRef) -> TypeRef:
        return ref if isinstance(ref, str) else number[cls[ref]]

    table = []
    for node_index in order:
        shape, children = nodes[node_index]
        refs = [mapped(c) for c in children]
        kind = shape[0]
        if kind == "record":
            table.append({"record": dict(zip(shape[1], refs))})
        elif kind == "tuple":
            table.append({"tuple": [[label, r] for label, r in zip(shape[1], refs)]})
        elif kind in ("variant", "option"):
            remaining = iter(refs)
            table.append({kind: {label: (next(remaining) if has else None) for label, has in zip(shape[1], shape[2])}})
        elif kind == "array":
            table.append({"array": refs[0]})
        elif kind == "fun":
            table.append({"fun": {"params": [[m, r] for m, r in zip(shape[1], refs)], "result": refs[-1]}})
        elif kind == "external":
            table.append({"external": shape[1]})
        elif kind == "abstract":
            node: dict[str, Any] = {"abstract": shape[1]}
            if shape[2]:
                node["args"] = refs[:-1]
            node["rep"] = refs[-1]
            table.append(node)
        elif kind == "auto":
            bound = refs[0] if shape[2] else None
            components = refs[1:] if shape[2] else refs
            table.append({"auto": {"bound": bound, "components": [[l, r] for l, r in zip(shape[1], components)]}})
        elif kind == "param":
            table.append({"param": shape[1]})
        else:
            table.append({"exception": refs[0]})
    return table, {i: number[cls[i]] for i in range(len(nodes)) if cls[i] in number}


# ============================================================================
# Writing
# ============================================================================


def _field_name(label: str) -> str:
    return label[4:] if label.startswith("var ") else ("" if label == "var" else label)


def _is_var_label(label: str) -> bool:
    return label.startswith("var ") or label == "var"


class _Writer:
    """Writes a value as the document's value, by its type, in two passes.

    scan walks the value first and finds the objects reached more than once:
    records, arrays, and nonempty tuples, which have identity. encode then
    writes it as JSON, following its type: a record as an object, a tuple as
    an array, an option as {case: payload} or the case's name alone, and a
    shared object with an @id where it is first written and as {"@ref": n}
    where it is met again. So a pair of one point twice,

        tuple let a = p let b = p end

    is written

        [{"@id": 1, "x": 10, "y": 20}, {"@ref": 1}]

    and a cycle of objects ends in a @ref. Writing adds the types it meets to
    the graph; an abstract type's value is written at its representation's
    type, and an auto value's components at their types with the auto value's
    witness, the type it hides, for its type parameter (witnesses)."""

    def __init__(self) -> None:
        self.graph = _TypeGraph()
        self.roots: list[TypeRef] = []
        self.nested: list[tuple[dict[str, Any], TypeRef]] = []
        self.seen: set[int] = set()
        self.shared: set[int] = set()
        self.ids: dict[int, int] = {}
        # The witnesses of the auto values being written, innermost last, which
        # param nodes refer to
        self.witnesses: list[TypeRef] = []

    def _deref(self, val: QValue) -> QValue:
        while isinstance(val, QRef):
            val = val.value
        return val

    @staticmethod
    def _has_identity(val: QValue) -> bool:
        """Whether val may be shared: records, arrays, and nonempty tuples
        (compiled code has one empty tuple)."""
        return isinstance(val, (QRecord, QArray)) or (isinstance(val, QTuple) and len(val.elements) > 0)

    def _concrete(self, ref: TypeRef) -> TypeRef:
        """The type a value of type ref is written at: an abstract type's value
        is written at its representation, and a value of an auto type's
        parameter at the auto value's witness."""
        while not isinstance(ref, str):
            shape, children = self.graph.nodes[ref]
            if shape[0] == "abstract":
                ref = children[-1]
            elif shape[0] == "param":
                if shape[1] >= len(self.witnesses):
                    raise _fail()
                ref = self.witnesses[-1 - shape[1]]
            else:
                break
        return ref

    def _auto(self, val: QValue, ref: int) -> tuple[TypeRef, list[tuple[QValue, TypeRef]]]:
        """An auto value's witness, and its components with their types (which
        refer to the witness by param)."""
        shape, children = self.graph.nodes[ref]
        components = children[1:] if shape[2] else children
        if not isinstance(val, QAutoVal) or not isinstance(val.value, QTuple):
            raise _fail()
        if len(val.value.elements) != len(components):
            raise _fail()
        return self.graph.ref(val.type_val), list(zip(val.value.elements, components))

    def _children(self, val: QValue, ref: TypeRef) -> list[tuple[QValue, TypeRef]]:
        """The component values of val with their type refs, in the order they
        are written."""
        ref = self._concrete(ref)
        if isinstance(ref, str):
            if ref == "Dynamic":
                if not isinstance(val, QAutoVal) or len(val.value.elements) != 1:
                    raise _fail()
                return [(val.value.elements[0], self.graph.ref(val.type_val))]
            return []
        shape, children = self.graph.nodes[ref]
        kind = shape[0]
        if kind == "record":
            if not isinstance(val, QRecord):
                raise _fail()
            out = []
            for label, child in zip(shape[1], children):
                name = _field_name(label)
                if name not in val.fields:
                    raise _fail()
                out.append((val.fields[name], child))
            return out
        if kind == "tuple":
            if not isinstance(val, QTuple) or len(val.elements) < len(children):
                raise _fail()
            return list(zip(val.elements, children))
        if kind == "array":
            if not isinstance(val, QArray):
                raise _fail()
            return [(e, children[0]) for e in val.elements]
        if kind in ("variant", "option"):
            payload_ref = self._case_payload(val, shape, children)
            if payload_ref is None:
                return []
            if kind == "variant":
                return [(val.payload, payload_ref)]
            # An option's components are stored in the option value itself (as
            # in compiled code), so they are written in place and never shared
            payload = self._deref(val.payload)
            components = self.graph.nodes[payload_ref][1]
            if not isinstance(payload, QTuple) or len(payload.elements) < len(components):
                raise _fail()
            return list(zip(payload.elements, components))
        if kind == "external":
            return []
        if kind == "auto":
            return self._auto(val, ref)[1]
        raise _fail()  # functions and exceptions cannot be externed

    def _case_payload(self, val: QValue, shape: tuple[Any, ...], children: tuple[TypeRef, ...]) -> Optional[TypeRef]:
        """The type ref of a variant or option value's payload, or None if it is
        written as its bare tag."""
        if not isinstance(val, (QVariant, QOption)):
            raise _fail()
        remaining = iter(children)
        for label, has in zip(shape[1], shape[2]):
            payload_ref = next(remaining) if has else None
            if _field_name(label) == val.tag:
                if payload_ref in (None, "Ok"):
                    return None
                if shape[0] == "option" and (isinstance(payload_ref, str) or self.graph.nodes[payload_ref][0][0] != "tuple"):
                    raise _fail()
                return payload_ref
        raise _fail()

    def scan(self, val: QValue, ref: TypeRef) -> None:
        """Finds the records, tuples, and arrays reached more than once."""
        val = self._deref(val)
        if self._has_identity(val):
            if id(val) in self.seen:
                self.shared.add(id(val))
                return
            self.seen.add(id(val))
        concrete = self._concrete(ref)
        if not isinstance(concrete, str) and self.graph.nodes[concrete][0][0] == "auto":
            witness, components = self._auto(val, concrete)
            self.witnesses.append(witness)
            for child, child_ref in components:
                self.scan(child, child_ref)
            self.witnesses.pop()
            return
        for child, child_ref in self._children(val, ref):
            self.scan(child, child_ref)

    def encode(self, val: QValue, ref: TypeRef) -> Any:
        val = self._deref(val)
        ref = self._concrete(ref)
        if isinstance(ref, str):
            return self._encode_builtin(val, ref)
        kind = self.graph.nodes[ref][0][0]
        if kind == "external":
            if not isinstance(val, QWord):
                raise _fail()
            return val.value
        if kind == "auto":
            # As a dynamic value is: its witness, then its components at their
            # types, which refer to the witness
            witness, components = self._auto(val, ref)
            out_auto: dict[str, Any] = {"@type": witness, "@value": None}
            self.roots.append(witness)
            self.nested.append((out_auto, witness))
            self.witnesses.append(witness)
            out_auto["@value"] = [self.encode(child, child_ref) for child, child_ref in components]
            self.witnesses.pop()
            return out_auto
        obj_id: Optional[int] = None
        if self._has_identity(val) and id(val) in self.shared:
            if id(val) in self.ids:
                return {"@ref": self.ids[id(val)]}
            obj_id = len(self.ids) + 1
            self.ids[id(val)] = obj_id
        if kind == "record":
            out: dict[str, Any] = {} if obj_id is None else {"@id": obj_id}
            shape = self.graph.nodes[ref][0]
            for label, (child, child_ref) in zip(shape[1], self._children(val, ref)):
                out[_field_name(label)] = self.encode(child, child_ref)
            return out
        if kind in ("tuple", "array"):
            items = [self.encode(child, child_ref) for child, child_ref in self._children(val, ref)]
            return items if obj_id is None else {"@id": obj_id, "@items": items}
        if kind in ("variant", "option"):
            shape, children = self.graph.nodes[ref]
            payload_ref = self._case_payload(val, shape, children)
            if payload_ref is None:
                return val.tag
            if kind == "option":
                return {val.tag: [self.encode(child, child_ref) for child, child_ref in self._children(val, ref)]}
            return {val.tag: self.encode(val.payload, payload_ref)}
        raise _fail()

    def _encode_builtin(self, val: QValue, ref: str) -> Any:
        if ref == "Int" and isinstance(val, QInt):
            return val.value
        if ref == "Real" and isinstance(val, (QReal, QInt)):
            r = float(val.value)
            if math.isnan(r):  # not a Real value (docs/type-system.md §6.3.1)
                raise _fail()
            if math.isinf(r):
                return "Infinity" if r > 0 else "-Infinity"
            return r
        if ref == "Bool" and isinstance(val, QBool):
            return val.value
        if ref == "Char" and isinstance(val, QChar):
            return val.value
        if ref == "String" and isinstance(val, QString):
            return val.value
        if ref == "Ok":
            return None
        if ref == "Dynamic":
            ((component, witness),) = self._children(val, ref)
            out = {"@type": witness, "@value": None}
            self.roots.append(witness)
            self.nested.append((out, witness))
            out["@value"] = self.encode(component, witness)
            return out
        raise _fail()


def jsog_encode(dyn: QAutoVal) -> str:
    """Serializes a dynamic value as a version 1 document."""
    w = _Writer()
    w.scan(dyn, "Dynamic")
    if not isinstance(dyn, QAutoVal) or len(dyn.value.elements) != 1:
        raise _fail()
    root = w.graph.ref(dyn.type_val)
    w.roots.append(root)
    value = w.encode(dyn.value.elements[0], root)
    table, index = _canonical_table(w.graph.nodes, w.roots)

    def mapped(ref: TypeRef) -> TypeRef:
        return ref if isinstance(ref, str) else index[ref]

    for out, witness in w.nested:
        out["@type"] = mapped(witness)
    document = {"quest": FORMAT_VERSION, "types": table, "type": mapped(root), "value": value}
    # ASCII, with a \u escape for each byte above 127, as C writes it
    return json.dumps(document, separators=(",", ":"), allow_nan=False)


# ============================================================================
# Reading
# ============================================================================

_NODE_KINDS = (
    "record", "tuple", "variant", "option", "array", "fun", "exception", "external", "abstract", "auto", "param",
)


def _arity(kind: QKind) -> int:
    n = 0
    while isinstance(kind, QAllKind):
        n, kind = n + 1, kind.result_kind
    return n


def _operator_kind(arity: int) -> QKind:
    """TYPE, or the kind of an operator from `arity` types to TYPE: that of an
    abstract type of an unlinked module."""
    kind: QKind = TYPE_KIND
    for i in reversed(range(arity)):
        kind = QAllKind(param_name=f"A{i + 1}", param_id=allocate_symbol_id(), param_kind=TYPE_KIND, result_kind=kind)
    return kind


class _Reader:
    """Reads a document's value back by its type, from the document's type
    table, raising dynamic.error (_fail) at anything ill-formed.

    The constructor checks every node of the table before anything is read
    (_check_node). type_of makes the QType of a node, once: a node reached
    again while its own type is being made, as the option above is from its
    tail, becomes a recursive type. value decodes JSON by its type, the
    reverse of _Writer.encode: an object with an @id is recorded in objects
    as it is made, so that a later {"@ref": n} returns that same object,
    shared as it was when written."""

    def __init__(self, table: Any) -> None:
        if not isinstance(table, list):
            raise _fail()
        self.table = table
        for node in table:
            self._check_node(node)
        self.types: dict[int, QType] = {}
        self.active: set[int] = set()
        self.recursive: set[int] = set()
        self.binder_ids = {i: allocate_symbol_id() for i in range(len(table))}
        self.binder_id_set = set(self.binder_ids.values())
        self.objects: dict[int, QValue] = {}
        # The type parameters of the auto types being built, innermost last,
        # which param nodes refer to; and the witnesses of the auto values being
        # read, which values of those parameters are read at
        self.auto_params: list[QTypeVar] = []
        self.witnesses: list[TypeRef] = []

    # --- the type table ---

    def _check_ref(self, ref: Any) -> None:
        if isinstance(ref, bool) or not (
            (isinstance(ref, str) and ref in _BUILTIN_TYPES)
            or (isinstance(ref, int) and 0 <= ref < len(self.table))
        ):
            raise _fail()

    def _check_node(self, node: Any) -> None:
        """Checks that one entry of a document's type table has the form
        docs/dynamic.md §2.2 gives, raising dynamic.error (_fail) if not.

        A document may come from anywhere, so the reader checks the whole table
        before reading anything with it, and the rest of the reader can then
        index the table and take a node's parts apart without checking. An
        entry is an object with one key, naming a type constructor, such as

            {"tuple": [["head", "Int"], ["tail", 0]]}

        or an abstract type, {"abstract": ..., "args": [...], "rep": ...}, whose
        args are optional but not empty. Every type reference must be the name
        of a built-in type ("Int") or the index of an entry in the table (0). An
        option case's reference, if any, must be to a tuple entry, the case's
        components. A function parameter's mode is "", "var", or "out", and a
        param entry's count of auto types is a non-negative integer. Labels
        are checked only to be strings."""
        if isinstance(node, dict) and "abstract" in node:
            if set(node) - {"abstract", "args", "rep"} or "rep" not in node or not isinstance(node["abstract"], str):
                raise _fail()
            args = node.get("args", [None])
            if not isinstance(args, list) or not args:
                raise _fail()
            for ref in node.get("args", []):
                self._check_ref(ref)
            self._check_ref(node["rep"])
            return
        if not isinstance(node, dict) or len(node) != 1:
            raise _fail()
        ((kind, body),) = node.items()
        if kind == "record" or kind in ("variant", "option"):
            if not isinstance(body, dict):
                raise _fail()
            for label, ref in body.items():
                if not isinstance(label, str):
                    raise _fail()
                if ref is not None or kind == "record":
                    self._check_ref(ref)
                if kind == "option" and ref is not None and (
                    isinstance(ref, str) or not isinstance(self.table[ref], dict) or "tuple" not in self.table[ref]
                ):
                    raise _fail()  # an option case's components are a tuple type
        elif kind == "tuple":
            if not isinstance(body, list) or not all(
                isinstance(c, list) and len(c) == 2 and isinstance(c[0], str) for c in body
            ):
                raise _fail()
            for _, ref in body:
                self._check_ref(ref)
        elif kind in ("array", "exception"):
            self._check_ref(body)
        elif kind == "external":
            if body not in _EXTERNAL_TYPES:
                raise _fail()
        elif kind == "param":
            if not isinstance(body, int) or isinstance(body, bool) or body < 0:
                raise _fail()
        elif kind == "auto":
            if not isinstance(body, dict) or set(body) != {"bound", "components"}:
                raise _fail()
            if body["bound"] is not None:
                self._check_ref(body["bound"])
            components = body["components"]
            if not isinstance(components, list) or not all(
                isinstance(c, list) and len(c) == 2 and isinstance(c[0], str) for c in components
            ):
                raise _fail()
            for _, ref in components:
                self._check_ref(ref)
        elif kind == "fun":
            if not isinstance(body, dict) or set(body) != {"params", "result"} or not isinstance(body["params"], list):
                raise _fail()
            for p in body["params"]:
                if not (isinstance(p, list) and len(p) == 2 and p[0] in ("", "var", "out")):
                    raise _fail()
                self._check_ref(p[1])
            self._check_ref(body["result"])
        else:
            raise _fail()

    def node(self, ref: int) -> tuple[str, Any]:
        if "abstract" in self.table[ref]:
            return "abstract", self.table[ref]
        ((kind, body),) = self.table[ref].items()
        return kind, body

    def concrete(self, ref: TypeRef) -> TypeRef:
        """The type a value of type ref is written at: an abstract type's value
        is written at its representation, and a value of an auto type's
        parameter at the auto value's witness."""
        for _ in range(len(self.table) + len(self.witnesses) + 1):
            if isinstance(ref, str):
                return ref
            if "abstract" in self.table[ref]:
                ref = self.table[ref]["rep"]
            elif "param" in self.table[ref]:
                n = self.table[ref]["param"]
                if n >= len(self.witnesses):
                    raise _fail()
                ref = self.witnesses[-1 - n]
            else:
                return ref
        raise _fail()

    def abstract_type(self, name: str, args: tuple[QType, ...], rep: QType) -> QType:
        """The module abstract type `name` (applied to args), whose recorded
        representation is rep: the linked module's type if rep is its
        representation, or the opaque type of an unlinked module
        (docs/dynamic.md §2.3)."""
        entry = abstract_type_by_name(name)
        closed = not (rep._fv & self.binder_id_set) and not any(a._fv & self.binder_id_set for a in args)
        if entry is None:
            if not closed:
                raise _fail()
            var = QTypeVar(name=name, symbol_id=abstract_type_symbol_id(name), bound=_operator_kind(len(args)))
            entry = register_unlinked_abstract_type(name, var)
        if _arity(entry.type_var.bound) != len(args) or not _is_unbounded(entry.type_var.bound):
            raise _fail()
        if not entry.linked:
            try:
                known = _representation(entry, args)
            except QuestException:
                if not closed:
                    raise
                entry.instances.append((args, rep))
                known = rep
        else:
            known = _representation(entry, args)
        if not is_type_equal(known, rep):
            raise _fail()
        return QTypeApp(constructor=entry.type_var, arguments=args) if args else entry.type_var

    def type_of(self, ref: TypeRef) -> QType:
        """The QType of a table entry; a node reached again while it is being
        built becomes a recursive type."""
        if isinstance(ref, str):
            return _BUILTIN_TYPES[ref]
        done = self.types.get(ref)
        if done is not None:
            return done
        if "param" in self.table[ref]:
            n = self.table[ref]["param"]
            if n >= len(self.auto_params):
                raise _fail()
            return self.auto_params[-1 - n]
        binder = self.binder_ids[ref]
        if ref in self.active:
            self.recursive.add(ref)
            return QTypeVar(name=f"T{ref}", symbol_id=binder, bound=TYPE_KIND)
        self.active.add(ref)
        kind, body = self.node(ref)
        t: QType
        if kind == "record":
            t = QRecordType(tuple(
                QRecordField(name=_field_name(label), type_val=self.type_of(r), is_var=_is_var_label(label))
                for label, r in body.items()
            ))
        elif kind == "tuple":
            t = QTupleType(tuple(
                QTupleField(name=_field_name(label) or None, type_val=self.type_of(r), is_var=_is_var_label(label))
                for label, r in body
            ))
        elif kind == "variant":
            t = QVariantType(tuple(
                QVariantField(
                    name=_field_name(label),
                    type_val=None if r is None else self.type_of(r),
                    is_var=_is_var_label(label),
                )
                for label, r in body.items()
            ))
        elif kind == "option":
            t = QOptionType(tuple(
                QOptionField(name=label, payload_type=None if r is None else self.type_of(r))
                for label, r in body.items()
            ))
        elif kind == "array":
            t = QArrayType(element_type=self.type_of(body))
        elif kind == "external":
            t = QExternalType(name=body, c_type=body)
        elif kind == "abstract":
            args = tuple(self.type_of(a) for a in body.get("args", ()))
            t = self.abstract_type(body["abstract"], args, self.type_of(body["rep"]))
        elif kind == "auto":
            kind_bound: QKind = TYPE_KIND if body["bound"] is None else QPowerKind(bound=self.type_of(body["bound"]))
            param = QTypeVar(name=f"A{len(self.auto_params)}", symbol_id=allocate_symbol_id(), bound=kind_bound)
            self.auto_params.append(param)
            try:
                signature = tuple(
                    QRecordField(name=_field_name(label), type_val=self.type_of(r), is_var=_is_var_label(label))
                    for label, r in body["components"]
                )
            finally:
                self.auto_params.pop()
            t = QAutoType(type_param=param.name, symbol_id=param.symbol_id, kind_bound=kind_bound, signature=signature)
        elif kind == "fun":
            t = QFunType(
                params=tuple(
                    QParam(name=f"x{i + 1}", type_val=self.type_of(r), is_var=mode == "var", is_out=mode == "out")
                    for i, (mode, r) in enumerate(body["params"])
                ),
                result_type=self.type_of(body["result"]),
            )
        else:
            t = QExceptionType(payload_type=self.type_of(body))
        self.active.discard(ref)
        if ref in self.recursive:
            t = QRecType(var_name=f"T{ref}", symbol_id=binder, bound=TYPE_KIND, body=t)
        # A type that mentions a recursive type's binder, or an enclosing auto
        # type's parameter, is that type only where it was reached
        if not (t._fv & self.binder_id_set) and not any(p.symbol_id in t._fv for p in self.auto_params):
            self.types[ref] = t
        return t

    # --- values ---

    def _shared(self, data: Any, kind: str) -> tuple[Optional[QValue], Optional[int], Any]:
        """Resolves {"@ref": n}; otherwise returns the object's @id (if any) and
        its contents."""
        if isinstance(data, dict) and "@ref" in data:
            if len(data) != 1:
                raise _fail()
            obj = self.objects.get(data["@ref"]) if isinstance(data["@ref"], int) else None
            if obj is None:
                raise _fail()
            return obj, None, None
        if isinstance(data, dict) and "@id" in data:
            obj_id = data["@id"]
            if not isinstance(obj_id, int) or isinstance(obj_id, bool) or obj_id in self.objects:
                raise _fail()
            if kind == "record":
                return None, obj_id, {k: v for k, v in data.items() if k != "@id"}
            if set(data) != {"@id", "@items"}:
                raise _fail()
            return None, obj_id, data["@items"]
        return None, None, data

    def value(self, data: Any, ref: TypeRef) -> QValue:
        ref = self.concrete(ref)
        if isinstance(ref, str):
            return self._builtin_value(data, ref)
        kind, body = self.node(ref)
        if kind == "external":
            if not isinstance(data, int) or isinstance(data, bool) or not 0 <= data < _WORD_LIMIT:
                raise _fail()
            return QWord(data)
        if kind == "auto":
            if not isinstance(data, dict) or set(data) != {"@type", "@value"}:
                raise _fail()
            witness = data["@type"]
            self._check_ref(witness)
            if body["bound"] is not None and not is_subtype(self.type_of(witness), self.type_of(body["bound"])):
                raise _fail()
            items = data["@value"]
            components = body["components"]
            if not isinstance(items, list) or len(items) != len(components):
                raise _fail()
            self.witnesses.append(witness)
            try:
                values = tuple(self.value(item, r) for item, (_, r) in zip(items, components))
            finally:
                self.witnesses.pop()
            labels = tuple(_field_name(label) for label, _ in components)
            return QAutoVal(QTuple(values, labels=labels), self.type_of(witness))
        if kind == "record":
            existing, obj_id, fields = self._shared(data, kind)
            if existing is not None:
                return existing
            if not isinstance(fields, dict) or set(fields) != {_field_name(label) for label in body}:
                raise _fail()
            rec = QRecord({})
            if obj_id is not None:
                self.objects[obj_id] = rec
            for label, r in body.items():
                name = _field_name(label)
                rec.fields[name] = self.value(fields[name], r)
            return rec
        if kind in ("tuple", "array"):
            existing, obj_id, items = self._shared(data, kind)
            if existing is not None:
                return existing
            if not isinstance(items, list):
                raise _fail()
            if kind == "array":
                arr = QArray([])
                if obj_id is not None:
                    self.objects[obj_id] = arr
                arr.elements = [self.value(item, body) for item in items]
                return arr
            if len(items) != len(body):
                raise _fail()
            labels = tuple(_field_name(label) or None for label, _ in body)
            tup = QTuple(tuple(OK_VALUE for _ in body), labels=labels)
            if obj_id is not None:
                self.objects[obj_id] = tup
            tup.elements = tuple(self.value(item, r) for item, (_, r) in zip(items, body))
            return tup
        if kind in ("variant", "option"):
            make = QVariant if kind == "variant" else QOption
            cases = {_field_name(label): r for label, r in body.items()}
            if isinstance(data, str):
                if data not in cases or cases[data] not in (None, "Ok"):
                    raise _fail()
                return make(data, OK_VALUE)
            if not isinstance(data, dict) or len(data) != 1:
                raise _fail()
            ((tag, payload),) = data.items()
            if tag not in cases or cases[tag] in (None, "Ok"):
                raise _fail()
            if kind == "option":
                # The case's components, written in place
                _, components = self.node(cases[tag])
                if not isinstance(payload, list) or len(payload) != len(components):
                    raise _fail()
                labels = tuple(_field_name(label) or None for label, _ in components)
                values = tuple(self.value(item, r) for item, (_, r) in zip(payload, components))
                return make(tag, QTuple(values, labels=labels))
            return make(tag, self.value(payload, cases[tag]))
        raise _fail()

    def _builtin_value(self, data: Any, ref: str) -> QValue:
        if ref == "Int" and isinstance(data, int) and not isinstance(data, bool):
            return QInt(data)
        if ref == "Real":
            if isinstance(data, (int, float)) and not isinstance(data, bool):
                return QReal(float(data))
            special = {"Infinity": math.inf, "-Infinity": -math.inf}
            if isinstance(data, str) and data in special:
                return QReal(special[data])
        if ref == "Bool" and isinstance(data, bool):
            return TRUE_VALUE if data else FALSE_VALUE
        # A character is a byte, so a \u escape above \u00ff gives none
        if ref == "Char" and isinstance(data, str) and len(data) == 1 and _is_bytes(data):
            return QChar(data)
        if ref == "String" and isinstance(data, str) and _is_bytes(data):
            return QString(data)
        if ref == "Ok" and data is None:
            return OK_VALUE
        if ref == "Dynamic" and isinstance(data, dict) and set(data) == {"@type", "@value"}:
            self._check_ref(data["@type"])
            return self.dynamic(data["@type"], data["@value"])
        raise _fail()

    def dynamic(self, ref: TypeRef, data: Any) -> QAutoVal:
        value = self.value(data, ref)
        return QAutoVal(QTuple((value,), labels=("a",)), self.type_of(ref))


def _reject_json_constant(name: str) -> Any:
    """Rejects the non-JSON tokens NaN, Infinity, and -Infinity that Python's
    json module accepts."""
    raise _fail()


def _is_bytes(text: str) -> bool:
    """Whether each character of text is a byte, as a Quest character is."""
    return max(text, default="\0") <= "\xff"


def jsog_decode(raw_json: str) -> QAutoVal:
    """Deserializes a version 1 document into a dynamic value."""
    try:
        document = json.loads(raw_json, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, RecursionError):
        raise _fail() from None
    if not isinstance(document, dict) or set(document) != {"quest", "types", "type", "value"}:
        raise _fail()
    if document["quest"] != FORMAT_VERSION or isinstance(document["quest"], bool):
        raise _fail()
    reader = _Reader(document["types"])
    reader._check_ref(document["type"])
    return reader.dynamic(document["type"], document["value"])
