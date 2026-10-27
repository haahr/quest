"""Quest values in Python: the interpreters' values (quest.interpreter), and the
data of the dynamic format (quest.values.dynamic_json), which `.qi` interface
files are written in too, so compilation uses them as well.

The value hierarchy (QValue) and its operational semantics:
- Primitive values (Ok, Bool, Int, Real, Char, String)
- Compound aggregates (Record, Tuple, Array)
- Sum types (Variant, Option)
- First-class functions and closures (QClosure, QBuiltinFun)
- Mutable heap cells (QRef)
- Auto values (including dynamic values) and exception values (QAutoVal,
  QExceptionVal)
- Cardelli 'is'/'isnot' identity predicate and recursive structural equality.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from collections.abc import Sequence
from typing import Any, Optional

from quest.diagnostics import Diagnostic, DiagnosticLabel, QuestCompilerError, Severity
from quest.types import QType, is_type_equal


# ============================================================================
# 1. Base Runtime Value
# ============================================================================

class QValue(ABC):
    """Abstract base class for all runtime Quest values."""

    @property
    @abstractmethod
    def type_name(self) -> str:
        """Returns the human-readable Quest type name of this value."""
        pass

    @abstractmethod
    def to_str(self, visited: Optional[set[int]] = None) -> str:
        """Formats the value into canonical Quest text with cycle detection."""
        pass

    def __str__(self) -> str:
        return self.to_str()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_str()})"


# ============================================================================
# 2. Primitive Values
# ============================================================================

class QOk(QValue):
    """Singleton unit value of type Ok."""

    _instance: Optional[QOk] = None

    def __new__(cls) -> QOk:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def type_name(self) -> str:
        return "Ok"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return "ok"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, QOk)

    def __hash__(self) -> int:
        return hash("QOk")


OK_VALUE = QOk()


class QBool(QValue):
    """Boolean value (true or false)."""

    _true_instance: Optional[QBool] = None
    _false_instance: Optional[QBool] = None

    def __new__(cls, value: bool) -> QBool:
        if value:
            if cls._true_instance is None:
                inst = super().__new__(cls)
                inst._value = True
                cls._true_instance = inst
            return cls._true_instance
        else:
            if cls._false_instance is None:
                inst = super().__new__(cls)
                inst._value = False
                cls._false_instance = inst
            return cls._false_instance

    @property
    def value(self) -> bool:
        return self._value

    @property
    def type_name(self) -> str:
        return "Bool"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return "true" if self._value else "false"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QBool):
            return self._value == other._value
        return False

    def __hash__(self) -> int:
        return hash(self._value)


TRUE_VALUE = QBool(True)
FALSE_VALUE = QBool(False)


class QInt(QValue):
    """Signed 64-bit integer value."""

    def __init__(self, value: int):
        self.value = int(value)

    @property
    def type_name(self) -> str:
        return "Int"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QInt):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class QWord(QValue):
    """Unsigned 64-bit word value."""

    def __init__(self, value: int):
        self.value = int(value) & 0xFFFF_FFFF_FFFF_FFFF

    @property
    def type_name(self) -> str:
        return "Word.T"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return f"16#{self.value:x}#"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QWord):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class QReal(QValue):
    """64-bit floating point real number."""

    def __init__(self, value: float):
        self.value = float(value)

    @property
    def type_name(self) -> str:
        return "Real"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if math.isinf(self.value):
            return "inf" if self.value > 0 else "-inf"
        res = str(self.value)
        if "e" not in res and "." not in res:
            res += ".0"
        return res

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QReal):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class QChar(QValue):
    """A character value: a byte, with code 0 to 255, of which only ASCII has a
    defined meaning."""

    def __init__(self, value: str):
        if len(value) != 1:
            raise ValueError(f"QChar must be a single character, got: {value!r}")
        self.value = value

    @property
    def type_name(self) -> str:
        return "Char"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        char = self.value
        if char == "\n":
            escaped = "\\n"
        elif char == "\t":
            escaped = "\\t"
        elif char == "\r":
            escaped = "\\r"
        elif char == "\\":
            escaped = "\\\\"
        elif char == "'":
            escaped = "\\'"
        elif 32 <= ord(char) <= 126:
            escaped = char
        else:
            escaped = f"\\x{ord(char):02x}"
        return f"'{escaped}'"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QChar):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


class QString(QValue):
    """String literal value."""

    def __init__(self, value: str):
        self.value = str(value)

    @property
    def type_name(self) -> str:
        return "String"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        escaped_parts: list[str] = []
        for char in self.value:
            if char == "\n":
                escaped_parts.append("\\n")
            elif char == "\t":
                escaped_parts.append("\\t")
            elif char == "\r":
                escaped_parts.append("\\r")
            elif char == "\\":
                escaped_parts.append("\\\\")
            elif char == '"':
                escaped_parts.append('\\"')
            elif 32 <= ord(char) <= 126:
                escaped_parts.append(char)
            else:
                escaped_parts.append(f"\\x{ord(char):02x}")
        return f'"{"".join(escaped_parts)}"'

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QString):
            return self.value == other.value
        return False

    def __hash__(self) -> int:
        return hash(self.value)


# ============================================================================
# 3. Compound Aggregates
# ============================================================================

class QRecord(QValue):
    """Unordered collection of labeled fields."""

    def __init__(self, fields: Optional[dict[str, QValue]] = None):
        self.fields: dict[str, QValue] = dict(fields) if fields is not None else {}

    @property
    def type_name(self) -> str:
        return "Record"

    def get(self, field_name: str) -> QValue:
        if field_name not in self.fields:
            raise KeyError(f"Record has no field '{field_name}'")
        return self.fields[field_name]

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if visited is None:
            visited = set()
        if id(self) in visited:
            return "record ... end"
        visited.add(id(self))

        try:
            if not self.fields:
                return "record end"
            sorted_items = sorted(self.fields.items(), key=lambda kv: kv[0])
            fields_str = " ".join(f"{name}={val.to_str(visited)}" for name, val in sorted_items)
            return f"record {fields_str} end"
        finally:
            visited.remove(id(self))


class QTuple(QValue):
    """Ordered sequence of values, with optional field labels."""

    def __init__(
        self,
        elements: tuple[QValue, ...],
        labels: Optional[tuple[Optional[str], ...]] = None,
    ):
        self.elements = tuple(elements)
        if labels is not None:
            if len(labels) != len(elements):
                raise ValueError("labels length must match elements length")
            self.labels: Optional[tuple[Optional[str], ...]] = tuple(labels)
            self._name_to_index: dict[str, int] = {
                name: idx for idx, name in enumerate(labels) if name is not None
            }
        else:
            self.labels = None
            self._name_to_index = {}

    @property
    def type_name(self) -> str:
        return "Tuple"

    def get_by_index(self, index: int) -> QValue:
        if index < 0 or index >= len(self.elements):
            raise IndexError(f"Tuple index {index} out of bounds [0, {len(self.elements)})")
        return self.elements[index]

    def get_by_name(self, name: str) -> QValue:
        if name not in self._name_to_index:
            raise KeyError(f"Tuple has no labeled component '{name}'")
        return self.elements[self._name_to_index[name]]

    def set_by_index(self, index: int, value: QValue) -> None:
        if index < 0 or index >= len(self.elements):
            raise IndexError(f"Tuple index {index} out of bounds [0, {len(self.elements)})")
        elems = list(self.elements)
        elems[index] = value
        self.elements = tuple(elems)

    def set_by_name(self, name: str, value: QValue) -> None:
        if name in self._name_to_index:
            self.set_by_index(self._name_to_index[name], value)
        elif name.isdigit():
            self.set_by_index(int(name), value)
        elif name.startswith("_") and name[1:].isdigit():
            self.set_by_index(int(name[1:]), value)
        else:
            raise KeyError(f"Tuple has no labeled component '{name}'")

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if visited is None:
            visited = set()
        if id(self) in visited:
            return "tuple ... end"
        visited.add(id(self))

        try:
            if not self.elements:
                return "tuple end"
            parts: list[str] = []
            for idx, elem in enumerate(self.elements):
                label = self.labels[idx] if self.labels and idx < len(self.labels) else None
                elem_str = elem.to_str(visited)
                if label:
                    parts.append(f"{label}={elem_str}")
                else:
                    parts.append(elem_str)
            return f"tuple {' '.join(parts)} end"
        finally:
            visited.remove(id(self))


class QArray(QValue):
    """Mutable fixed-size array of Quest values."""

    def __init__(self, elements: list[QValue]):
        self.elements: list[QValue] = list(elements)

    @property
    def type_name(self) -> str:
        return "Array"

    def size(self) -> int:
        return len(self.elements)

    def get(self, index: int) -> QValue:
        if index < 0 or index >= len(self.elements):
            raise IndexError(f"Array index {index} out of bounds [0, {len(self.elements)})")
        return self.elements[index]

    def set(self, index: int, value: QValue) -> None:
        if index < 0 or index >= len(self.elements):
            raise IndexError(f"Array index {index} out of bounds [0, {len(self.elements)})")
        self.elements[index] = value

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if visited is None:
            visited = set()
        if id(self) in visited:
            return "array of ... end"
        visited.add(id(self))

        try:
            if not self.elements:
                return "array of end"
            elems_str = " ".join(e.to_str(visited) for e in self.elements)
            return f"array of {elems_str} end"
        finally:
            visited.remove(id(self))


# ============================================================================
# 4. Sum / Disjoint Union Values
# ============================================================================

class QVariant(QValue):
    """Unordered tagged variant value with optional payload."""

    def __init__(self, tag: str, payload: Optional[QValue] = None):
        self.tag = tag
        self.payload = payload

    @property
    def type_name(self) -> str:
        return "Variant"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.payload is not None:
            return f"variant {self.tag} with {self.payload.to_str(visited)} end"
        return f"variant {self.tag} end"


class QOption(QValue):
    """Ordered tagged option value with optional payload. Its ordinal is its
    case's index in the static type it is used at (option_case_names), not in
    the type it was made at."""

    def __init__(
        self,
        tag: str,
        payload: Optional[QValue] = None,
    ):
        self.tag = tag
        self.payload = payload

    @property
    def type_name(self) -> str:
        return "Option"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.payload is not None:
            return f"option {self.tag} with {self.payload.to_str(visited)} end"
        return f"option {self.tag} end"


# ============================================================================
# 5. Functions & Closures
# ============================================================================

class QClosure(QValue):
    """First-class function closure capturing its lexical environment."""

    def __init__(
        self,
        params: tuple[str, ...],
        body: Any,
        env: Any,
        name: Optional[str] = None,
        type_param_ids: tuple[int, ...] = (),
        type_bindings: Optional[dict[int, Any]] = None,
        trace_name: str = "<anon>",
    ):
        self.params = tuple(params)
        self.body = body
        self.env = env
        self.name = name
        # The closure's frame in tracebacks (docs/exceptions.md §2.3)
        self.trace_name = trace_name
        # A polymorphic function's type parameters (symbol ids), and the types
        # bound to them by type applications
        self.type_param_ids = tuple(type_param_ids)
        self.type_bindings: dict[int, Any] = dict(type_bindings or {})

    def instantiate(self, type_args: Sequence[Any]) -> QClosure:
        """This closure with its next unbound type parameters bound to type_args
        (a type application)."""
        unbound = [i for i in self.type_param_ids if i not in self.type_bindings]
        bindings = dict(self.type_bindings)
        bindings.update(zip(unbound, type_args))
        return QClosure(self.params, self.body, self.env, self.name, self.type_param_ids, bindings, self.trace_name)

    @property
    def type_name(self) -> str:
        return "Function"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.name:
            return f"<fun:{self.name}>"
        return "<fun>"


class QBuiltinFun(QValue):
    """Built-in host function wrapper."""

    def __init__(
        self,
        name: str,
        fn: Callable[..., QValue],
        doc: Optional[str] = None,
    ):
        self.name = name
        self.fn = fn
        self.doc = doc

    @property
    def type_name(self) -> str:
        return "BuiltinFunction"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return f"<builtin:{self.name}>"


# ============================================================================
# 6. Mutable Heap Cells
# ============================================================================

class QRef(QValue):
    """Mutable heap reference cell for 'var' variables and assignable fields."""

    def __init__(self, value: QValue):
        self.value = value

    @property
    def type_name(self) -> str:
        return f"Ref({self.value.type_name})"

    def deref(self) -> QValue:
        return self.value

    def assign(self, new_value: QValue) -> None:
        self.value = new_value

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if visited is None:
            visited = set()
        if id(self) in visited:
            return "ref(...)"
        visited.add(id(self))
        try:
            return f"ref({self.value.to_str(visited)})"
        finally:
            visited.remove(id(self))


class QArrayElementRef(QRef):
    """Mutable reference cell into an array element."""

    def __init__(self, array: Any, index: int):
        self.array = array
        self.index = index

    @property
    def value(self) -> QValue:
        return self.array.get(self.index)

    @value.setter
    def value(self, new_val: QValue) -> None:
        self.array.set(self.index, new_val)

    def deref(self) -> QValue:
        return self.array.get(self.index)

    def assign(self, new_value: QValue) -> None:
        self.array.set(self.index, new_value)


class QTupleElementRef(QRef):
    """Mutable reference cell into a tuple component."""

    def __init__(self, tup: Any, index: int):
        self.tup = tup
        self.index = index

    @property
    def value(self) -> QValue:
        elem = self.tup.get_by_index(self.index)
        return elem.deref() if isinstance(elem, QRef) else elem

    @value.setter
    def value(self, new_val: QValue) -> None:
        elem = self.tup.get_by_index(self.index)
        if isinstance(elem, QRef):
            elem.assign(new_val)
        else:
            elems = list(self.tup.elements)
            elems[self.index] = new_val
            self.tup.elements = tuple(elems)

    def deref(self) -> QValue:
        return self.value

    def assign(self, new_value: QValue) -> None:
        self.value = new_value


# ============================================================================
# 7. Dynamic & Exception Envelopes
# ============================================================================

class QAutoVal(QValue):
    """Auto value (Cardelli §4.6): a tuple of components packaged with the
    closed type that determines their shape. type_val is the type component;
    value is the QTuple of components. A dynamic value is an auto value of type
    Auto A::TYPE with a:A end, whose one component is the packaged value."""

    def __init__(self, value: Any, type_val: Any):
        self.value = value
        self.type_val = type_val

    @property
    def type_name(self) -> str:
        return "Auto"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        val_str = self.value.to_str(visited)
        return f"auto({val_str} : {self.type_val})"


class QExceptionVal(QValue):
    """Runtime exception value with tag name and optional payload."""

    def __init__(self, name: str, payload: Optional[QValue] = None):
        self.name = name
        self.payload = payload

    @property
    def type_name(self) -> str:
        return "Exception"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.payload is not None:
            return f"exception {self.name} with {self.payload.to_str(visited)}"
        return f"exception {self.name}"


# ============================================================================
# 8. I/O Stream Handles (Writer.T and Reader.T)
# ============================================================================

class QWriter(QValue):
    """Output stream handle wrapping a Python text stream or open file."""

    def __init__(self, stream: Any, is_file: bool = False, file_name: Optional[str] = None):
        self.stream = stream
        self.is_file = is_file
        self.file_name = file_name
        self.is_closed = False

    @property
    def type_name(self) -> str:
        return "Writer.T"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.file_name:
            return f"<writer:file {self.file_name}>"
        return "<writer>"


class QStringBuilder(QValue):
    """The native buffer of a string builder (lib/util/stringbuilder): the
    pieces appended so far, as Python strings taken when they are appended."""

    def __init__(self) -> None:
        self.pieces: list[str] = []
        self.length = 0

    def append(self, text: str) -> None:
        if text:
            self.pieces.append(text)
            self.length += len(text)

    @property
    def type_name(self) -> str:
        return "StringBuilder.Buffer"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return "<string builder>"


class QReader(QValue):
    """Input stream handle wrapping a Python text stream or open file."""

    def __init__(self, stream: Any, is_file: bool = False, file_name: Optional[str] = None):
        self.stream = stream
        self.is_file = is_file
        self.file_name = file_name
        self.is_closed = False
        # The character reader.more read ahead, which the next read takes
        self.peek: Optional[str] = None

    @property
    def type_name(self) -> str:
        return "Reader.T"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        if self.file_name:
            return f"<reader:file {self.file_name}>"
        return "<reader>"


class QTypeValue(QValue):
    """Runtime representation of a type witness/value."""

    def __init__(
        self,
        type_val: Any,
        bound: Optional[Any] = None,
        name: Optional[str] = None,
    ):
        self.type_val = type_val
        self.bound = bound
        self.name = name

    @property
    def type_name(self) -> str:
        return "Type"

    def to_str(self, visited: Optional[set[int]] = None) -> str:
        return str(self.type_val)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, QTypeValue):
            return (
                (self.type_val is other.type_val or is_type_equal(self.type_val, other.type_val))
                and self.name == other.name
            )
        return False

    def __hash__(self) -> int:
        return hash((id(self.type_val), self.name))


# ============================================================================
# 8. Predicates: Identity & Structural Equality
# ============================================================================

def qvalue_is(v1: QValue, v2: QValue) -> bool:
    """Implements Quest's 'is' equality predicate (Cardelli Section 3.1).

    Value equality for primitives (Ok, Bool, Char, Int, Real);
    object identity (same memory location) for all other types (String, Array,
    Record, Tuple, Variant, Option, Closure, Ref, Dynamic, Exception).
    """
    if type(v1) is not type(v2):
        return False

    match v1:
        case QOk():
            return isinstance(v2, QOk)
        case QBool(value=b_val):
            return b_val is v2.value
        case QInt(value=n_val) | QWord(value=n_val) | QReal(value=n_val) | QChar(value=n_val):
            return n_val == v2.value
        case QTypeValue(type_val=t1):
            assert isinstance(v2, QTypeValue)
            return t1 is v2.type_val or is_type_equal(t1, v2.type_val)
        case _:
            # For all other types: pointer identity
            return v1 is v2


def qvalue_structural_eq(
    v1: QValue,
    v2: QValue,
    visited: Optional[set[tuple[int, int]]] = None,
) -> bool:
    """Whether two values have the same structure, comparing their parts all
    the way down, for tests: not Quest's own is, which compares aggregates by
    identity.

    Two values are equal if they are of the same class and:

    - scalars (Bool, Int, Word, Real, Char, String) hold equal Python values,
      so that 0.0 equals -0.0 and NaN equals nothing;
    - records have the same field names, tuples the same labels, arrays the
      same length, and their components are equal;
    - options, variants, and exceptions have the same tag or name and equal
      payloads, or none;
    - var cells (QRef) hold equal values, whether or not they are one cell;
    - auto values have equal types (==, on the type objects) and equal
      contents, and type values equal types (is_type_equal);
    - closures and builtins are the same object.

    Sharing is not compared: a tuple holding one record twice equals one
    holding two equal records. Cycles are compared coinductively: a pair of
    values met again while it is being compared is taken to be equal, so that
    two cyclic lists of the same elements are equal however they were built."""
    if v1 is v2:
        return True

    if type(v1) is not type(v2):
        return False

    if visited is None:
        visited = set()

    pair = (id(v1), id(v2))
    if pair in visited:
        return True
    visited.add(pair)

    match (v1, v2):
        case (QOk(), QOk()):
            return True

        case (
            (QBool(value=x1), QBool(value=x2))
            | (QInt(value=x1), QInt(value=x2))
            | (QWord(value=x1), QWord(value=x2))
            | (QReal(value=x1), QReal(value=x2))
            | (QChar(value=x1), QChar(value=x2))
            | (QString(value=x1), QString(value=x2))
        ):
            return x1 == x2

        case (QTypeValue(type_val=t1), QTypeValue(type_val=t2)):
            return t1 is t2 or is_type_equal(t1, t2)

        case (QRecord(fields=f1), QRecord(fields=f2)):
            if set(f1.keys()) != set(f2.keys()):
                return False
            for k in f1:
                if not qvalue_structural_eq(f1[k], f2[k], visited):
                    return False
            return True

        case (QTuple(elements=elems1, labels=labels1), QTuple(elements=elems2, labels=labels2)):
            if len(elems1) != len(elems2) or labels1 != labels2:
                return False
            for e1, e2 in zip(elems1, elems2):
                if not qvalue_structural_eq(e1, e2, visited):
                    return False
            return True

        case (QArray(elements=elems1), QArray(elements=elems2)):
            if len(elems1) != len(elems2):
                return False
            for e1, e2 in zip(elems1, elems2):
                if not qvalue_structural_eq(e1, e2, visited):
                    return False
            return True

        case ((QVariant(tag=tag1, payload=p1), QVariant(tag=tag2, payload=p2))
              | (QOption(tag=tag1, payload=p1), QOption(tag=tag2, payload=p2))):
            if tag1 != tag2 or (p1 is None) != (p2 is None):
                return False
            if p1 is not None and p2 is not None:
                return qvalue_structural_eq(p1, p2, visited)
            return True

        case (QRef(value=val1), QRef(value=val2)):
            return qvalue_structural_eq(val1, val2, visited)

        case (QAutoVal(type_val=t1, value=val1), QAutoVal(type_val=t2, value=val2)):
            if t1 != t2:
                return False
            return qvalue_structural_eq(val1, val2, visited)

        case (QExceptionVal(name=n1, payload=p1), QExceptionVal(name=n2, payload=p2)):
            if n1 != n2 or (p1 is None) != (p2 is None):
                return False
            if p1 is not None and p2 is not None:
                return qvalue_structural_eq(p1, p2, visited)
            return True

        case _:
            # Closures and Builtins fallback to pointer identity
            return v1 is v2


def qvalue_to_str(val: QValue) -> str:
    """Canonical string formatter for any Quest runtime value."""
    return val.to_str()


# ============================================================================
# Quest exceptions raised in Python
# ============================================================================

class QuestException(QuestCompilerError):
    """Language-level Quest exception (e.g. int.error or user-raised
    exception)."""

    def __init__(
        self,
        exc_val: QExceptionVal,
        payload: Optional[QValue] = None,
        payload_type: Optional[QType] = None,
        offset: Optional[int] = None,
        length: int = 1,
    ):
        super().__init__(message=exc_val.to_str(), offset=offset, length=length)
        self.exc_val = exc_val
        self.payload = payload
        self.payload_type = payload_type

    def to_diagnostic(self, length: Optional[int] = None) -> Diagnostic:
        len_val = length if length is not None else self.length
        label = DiagnosticLabel(offset=self.offset, length=len_val) if self.offset is not None else None
        if self.payload is not None and not isinstance(self.payload, QOk):
            payload_str = qvalue_to_str(self.payload)
            type_str = f":{self.payload_type}" if self.payload_type is not None else ""
            msg = f"Exception: {self.exc_val.name} with {payload_str}{type_str}"
        else:
            msg = f"Exception: {self.exc_val.name}"
        return Diagnostic(
            severity=Severity.ERROR,
            message=msg,
            primary_label=label,
        )


# Raised by the dynamic format's reader and writer (quest.values.dynamic_json),
# as by the dynamic module
DYNAMIC_ERROR_EXC = QExceptionVal("dynamic.error")
