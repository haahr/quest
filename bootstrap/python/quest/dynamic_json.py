"""Serialization of Quest dynamic values (dynamic.extern and dynamic.intern), format version 1.

A serialized dynamic value is one JSON document holding a type table and a value (docs/dynamic.md §2):

    {"quest": 1, "types": [<type node>, ...], "type": <type ref>, "value": <value>}

A type ref is a built-in type name or an index into the table; recursive types are cycles in the table. The table
is canonical, so that the interpreter and compiled code write the same text for the same value: the writer builds
the graph of the types it meets, merges structurally equivalent nodes (the coarsest bisimulation), and numbers the
remaining nodes in the order a depth-first walk from the roots first reaches them. Values are decoded by following
their type, and objects reached more than once are written once, with @id, and then as {"@ref": n}.
"""

from __future__ import annotations

import json
import math
from typing import Any, Optional, Union

from quest.env import allocate_symbol_id
from quest.interpreter import DYNAMIC_ERROR_EXC, QuestException
from quest.runtime import (
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
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
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
    QTypeApp,
    QTypeVar,
    QVariantField,
    QVariantType,
    unalias,
)

FORMAT_VERSION = 1

# Graphs larger than this come from types that are not regular (their unfoldings never repeat)
_MAX_TYPE_NODES = 100_000

TypeRef = Union[str, int]


def _fail() -> QuestException:
    return QuestException(DYNAMIC_ERROR_EXC)


def parse_type_string(type_str: str) -> QType:
    """Parses and elaborates a Quest type expression (used for fixed schema types, such as that of .qi files)."""
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
        from quest.elaborate_types import elaborate_type
        from quest.env import Environment
        from quest.grammar import parse_quest_program
        from quest.tokenizer import Tokenizer
        from quest.tokens import SourceMap

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
# A node is (shape, children). The shape holds the constructor and its labels; children are type refs, in the
# order the node lists them: record fields sorted by name, tuple components and function parameters in order (then
# the function's result), variant and option cases in declaration order (only those with a payload).

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
    """True for Auto A::TYPE with a:A end, the type of dynamic values, whatever its parameter is named."""
    if not isinstance(t, QAutoType) or t.kind_bound is not TYPE_KIND or len(t.signature) != 1:
        return False
    f = t.signature[0]
    return f.name == "a" and not f.is_var and isinstance(f.type_val, QTypeVar) and f.type_val.symbol_id == t.symbol_id


def _structure(t: QType) -> QType:
    """t with aliases, solved metavariables, applications, and recursion unfolded down to its outer constructor."""
    for _ in range(1000):
        t = t.prune() if hasattr(t, "prune") else t
        t = unalias(t)
        if isinstance(t, (QRecType, QRecGroupType, QTypeApp)):
            unfolded = t.evaluate_lazily()
            if unfolded is t:
                return t
            t = unfolded
            continue
        return t
    raise _fail()


def _var_label(name: str, is_var: bool) -> str:
    if not is_var:
        return name
    return f"var {name}" if name else "var"


class _TypeGraph:
    """The graph of the types a value mentions, keyed by the identity of their (hash-consed) structures."""

    def __init__(self) -> None:
        self.nodes: list[Optional[tuple[tuple[Any, ...], tuple[TypeRef, ...]]]] = []
        self._index: dict[int, int] = {}
        self._keep: list[QType] = []

    def ref(self, t: QType) -> TypeRef:
        s = _structure(t)
        name = _BUILTIN_NAMES.get(id(s))
        if name is not None:
            return name
        if _is_dynamic_type(s):
            return "Dynamic"
        index = self._index.get(id(s))
        if index is not None:
            return index
        if len(self.nodes) >= _MAX_TYPE_NODES:
            raise _fail()
        index = len(self.nodes)
        self._index[id(s)] = index
        self._keep.append(s)
        self.nodes.append(None)
        self.nodes[index] = self._node(s)
        return index

    def _node(self, s: QType) -> tuple[tuple[Any, ...], tuple[TypeRef, ...]]:
        if isinstance(s, QRecordType):
            fields = sorted(s.fields, key=lambda f: f.name)
            labels = tuple(_var_label(f.name, f.is_var) for f in fields)
            return ("record", labels), tuple(self.ref(f.type_val) for f in fields)
        if isinstance(s, QTupleType):
            components = s.value_fields
            if len(components) != len(s.fields):
                raise _fail()  # type components (an abstract tuple): not encodable yet
            labels = tuple(_var_label(f.name or "", f.is_var) for f in components)
            return ("tuple", labels), tuple(self.ref(f.type_val) for f in components)
        if isinstance(s, (QVariantType, QOptionType)):
            if isinstance(s, QVariantType):
                cases = [(_var_label(v.name, v.is_var), v.type_val) for v in s.variants]
            else:
                cases = [(o.name, o.payload_type) for o in s.options]
            shape = ("variant" if isinstance(s, QVariantType) else "option",
                     tuple(label for label, _ in cases), tuple(p is not None for _, p in cases))
            return shape, tuple(self.ref(p) for _, p in cases if p is not None)
        if isinstance(s, QArrayType):
            return ("array",), (self.ref(s.element_type),)
        if isinstance(s, QFunType):
            modes = tuple("var" if p.is_var else "out" if p.is_out else "" for p in s.params)
            return ("fun", modes), tuple(self.ref(p.type_val) for p in s.params) + (self.ref(s.result_type),)
        if isinstance(s, QExceptionType):
            return ("exception",), (self.ref(s.payload_type),)
        # Polymorphic types, abstract and external types, type operators, and other auto types: not encodable yet
        raise _fail()


def _canonical_table(
    nodes: list[Any], roots: list[TypeRef]
) -> tuple[list[dict[str, Any]], dict[int, int]]:
    """Merges equivalent nodes and numbers the rest from the roots; returns the table and each node's index in it."""
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
    def __init__(self) -> None:
        self.graph = _TypeGraph()
        self.roots: list[TypeRef] = []
        self.nested: list[tuple[dict[str, Any], TypeRef]] = []
        self.seen: set[int] = set()
        self.shared: set[int] = set()
        self.ids: dict[int, int] = {}

    def _deref(self, val: QValue) -> QValue:
        while isinstance(val, QRef):
            val = val.value
        return val

    @staticmethod
    def _has_identity(val: QValue) -> bool:
        """Whether val may be shared: records, arrays, and nonempty tuples (compiled code has one empty tuple)."""
        return isinstance(val, (QRecord, QArray)) or (isinstance(val, QTuple) and len(val.elements) > 0)

    def _children(self, val: QValue, ref: TypeRef) -> list[tuple[QValue, TypeRef]]:
        """The component values of val with their type refs, in the order they are written."""
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
            # An option's components are stored in the option value itself (as in compiled code), so they are
            # written in place and never shared
            payload = self._deref(val.payload)
            components = self.graph.nodes[payload_ref][1]
            if not isinstance(payload, QTuple) or len(payload.elements) < len(components):
                raise _fail()
            return list(zip(payload.elements, components))
        raise _fail()  # functions and exceptions cannot be externed

    def _case_payload(self, val: QValue, shape: tuple[Any, ...], children: tuple[TypeRef, ...]) -> Optional[TypeRef]:
        """The type ref of a variant or option value's payload, or None if it is written as its bare tag."""
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
        for child, child_ref in self._children(val, ref):
            self.scan(child, child_ref)

    def encode(self, val: QValue, ref: TypeRef) -> Any:
        val = self._deref(val)
        if isinstance(ref, str):
            return self._encode_builtin(val, ref)
        kind = self.graph.nodes[ref][0][0]
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
            if math.isnan(r):
                return "NaN"
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
    return json.dumps(document, separators=(",", ":"), allow_nan=False)


# ============================================================================
# Reading
# ============================================================================

_NODE_KINDS = ("record", "tuple", "variant", "option", "array", "fun", "exception")


class _Reader:
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

    # --- the type table ---

    def _check_ref(self, ref: Any) -> None:
        if isinstance(ref, bool) or not (
            (isinstance(ref, str) and ref in _BUILTIN_TYPES)
            or (isinstance(ref, int) and 0 <= ref < len(self.table))
        ):
            raise _fail()

    def _check_node(self, node: Any) -> None:
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
        ((kind, body),) = self.table[ref].items()
        return kind, body

    def type_of(self, ref: TypeRef) -> QType:
        """The QType of a table entry; a node reached again while it is being built becomes a recursive type."""
        if isinstance(ref, str):
            return _BUILTIN_TYPES[ref]
        done = self.types.get(ref)
        if done is not None:
            return done
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
        if not (t._fv & self.binder_id_set):
            self.types[ref] = t
        return t

    # --- values ---

    def _shared(self, data: Any, kind: str) -> tuple[Optional[QValue], Optional[int], Any]:
        """Resolves {"@ref": n}; otherwise returns the object's @id (if any) and its contents."""
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
        if isinstance(ref, str):
            return self._builtin_value(data, ref)
        kind, body = self.node(ref)
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
            special = {"NaN": math.nan, "Infinity": math.inf, "-Infinity": -math.inf}
            if isinstance(data, str) and data in special:
                return QReal(special[data])
        if ref == "Bool" and isinstance(data, bool):
            return TRUE_VALUE if data else FALSE_VALUE
        if ref == "Char" and isinstance(data, str) and len(data) == 1:
            return QChar(data)
        if ref == "String" and isinstance(data, str):
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


def jsog_decode(raw_json: str) -> QAutoVal:
    """Deserializes a version 1 document into a dynamic value."""
    try:
        document = json.loads(raw_json)
    except (json.JSONDecodeError, RecursionError):
        raise _fail() from None
    if not isinstance(document, dict) or set(document) != {"quest", "types", "type", "value"}:
        raise _fail()
    if document["quest"] != FORMAT_VERSION or isinstance(document["quest"], bool):
        raise _fail()
    reader = _Reader(document["types"])
    reader._check_ref(document["type"])
    return reader.dynamic(document["type"], document["value"])
