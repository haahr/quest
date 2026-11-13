"""Reading dynamic values (dynamic.intern): a document's type table made into
types, and its value read at its type, an @ref at the type its place expects
(docs/dynamic.md §2). A document that does not fit raises dynamic.error.

The self-hosted counterpart is questlang/values/dynamicreader.
"""

from __future__ import annotations

import json
import math
from typing import Any, Optional
from quest.types.env import allocate_symbol_id
from quest.values.model import (
    QuestException,
    FALSE_VALUE,
    OK_VALUE,
    TRUE_VALUE,
    QArray,
    QAutoVal,
    QChar,
    QInt,
    QOption,
    QReal,
    QRecord,
    QString,
    QTuple,
    QValue,
    QVariant,
    QWord,
)
from quest.modules.abstract_types import (
    abstract_type_by_name,
    abstract_type_symbol_id,
    register_unlinked_abstract_type,
)
from quest.types import (
    TYPE_KIND,
    QAllKind,
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionField,
    QOptionType,
    QParam,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QType,
    QKind,
    QPowerKind,
    QTypeApp,
    QTypeVar,
    QVariantField,
    QVariantType,
    is_subtype,
    is_type_equal,
)
from quest.values.dynamic_json import FORMAT_VERSION, TypeRef, _fail, _EXTERNAL_TYPES, _WORD_LIMIT, _BUILTIN_TYPES, _is_unbounded, _representation, _field_name, _is_var_label


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
    shared as it was when written, if the type it was read at is a subtype of
    the type the reference is read at."""

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
        # Each @id's object, and the type it was read at
        self.objects: dict[int, tuple[QValue, TypeRef]] = {}
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

    def _shared(self, data: Any, kind: str, ref: TypeRef) -> tuple[Optional[QValue], Optional[int], Any]:
        """Resolves {"@ref": n} read at the type ref, whose object must have
        been read at a subtype of it (as the runtime's quest_read_value
        checks); otherwise returns the object's @id (if any) and its
        contents."""
        if isinstance(data, dict) and "@ref" in data:
            if len(data) != 1:
                raise _fail()
            shared = self.objects.get(data["@ref"]) if isinstance(data["@ref"], int) else None
            if shared is None:
                raise _fail()
            obj, read_at = shared
            if read_at != ref and not is_subtype(self.type_of(read_at), self.type_of(ref)):
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
        """The value the JSON data denotes at the type ref, the reverse of
        _Writer.encode; raises dynamic.error (_fail) when data does not have
        the form ref's type gives it.

        A record, tuple, or array with an "@id" is recorded in objects before
        its components are read, so that a {"@ref": n} within it (a cycle) or
        after it returns the same object. An auto value's witness must be a
        subtype of the auto type's bound, and its components are read with
        the witness for the type parameter."""
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
            existing, obj_id, fields = self._shared(data, kind, ref)
            if existing is not None:
                return existing
            if not isinstance(fields, dict) or set(fields) != {_field_name(label) for label in body}:
                raise _fail()
            rec = QRecord({})
            if obj_id is not None:
                self.objects[obj_id] = (rec, ref)
            for label, r in body.items():
                name = _field_name(label)
                rec.fields[name] = self.value(fields[name], r)
            return rec
        if kind in ("tuple", "array"):
            existing, obj_id, items = self._shared(data, kind, ref)
            if existing is not None:
                return existing
            if not isinstance(items, list):
                raise _fail()
            if kind == "array":
                arr = QArray([])
                if obj_id is not None:
                    self.objects[obj_id] = (arr, ref)
                arr.elements = [self.value(item, body) for item in items]
                return arr
            if len(items) != len(body):
                raise _fail()
            labels = tuple(_field_name(label) or None for label, _ in body)
            tup = QTuple(tuple(OK_VALUE for _ in body), labels=labels)
            if obj_id is not None:
                self.objects[obj_id] = (tup, ref)
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
