"""Writing dynamic values (dynamic.extern): a dynamic value's type table,
canonical (dynamic_json.py), and its value; an object reached more than once is
written once, with @id, and then as {"@ref": n} (docs/dynamic.md §2). A value
the format cannot hold raises dynamic.error.

The self-hosted counterpart is questlang/values/dynamicwriter.
"""

from __future__ import annotations

import json
import math
from typing import Any, Optional
from quest.values.model import (
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
from quest.values.dynamic_json import FORMAT_VERSION, TypeRef, _fail, _TypeGraph, _canonical_table, _field_name


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
        """The JSON (a Python value for json.dumps) of val written at the type
        ref, a built-in type's name or a node of the graph; scan must have
        walked the whole document's value first, so that shared objects are
        known. Raises dynamic.error (_fail) for a value that cannot be written,
        such as a function, or one that does not match its type.

        - A record is an object of its fields, and a tuple or array an array;
          a shared one has an "@id" where it is first written ({"@id": n,
          "@items": [...]} for a tuple or array) and is {"@ref": n} after.
        - A variant or option is its case's name when the case has no
          payload, and otherwise {case: payload}: an option's payload an
          array of its components, written in place and never shared.
        - An auto value or a Dynamic is {"@type": witness, "@value": ...}, its
          components at their types with the witness for the type parameter.
          The witness is a root of the type table.
        - An external type's value is its word, and a built-in type's value as
          _encode_builtin writes it (a Real's infinities as strings)."""
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
            if math.isnan(r):  # not a Real value (docs/type-system.md §6.3.2)
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
