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

The self-hosted counterpart is questlang/values/dynamicjson, with the JSON text
itself in questlang/common/json.
"""

from __future__ import annotations

from typing import Any, Optional, Union
from quest.values.model import (
    DYNAMIC_ERROR_EXC,
    QuestException,
)
from quest.modules.abstract_types import (
    ModuleAbstractType,
    abstract_type_by_symbol,
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
    QArrayType,
    QAutoType,
    QExceptionType,
    QExternalType,
    QFunType,
    QOptionType,
    QRecGroupType,
    QRecordType,
    QRecType,
    QTupleType,
    QType,
    QKind,
    QPowerKind,
    QTypeApp,
    QTypeKind,
    QTypeVar,
    QVariantType,
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
        from quest.common.diagnostics import QuestCompilerError
        from quest.typechecker.elaborate_types import elaborate_type
        from quest.types.env import Environment
        from quest.syntax.grammar import parse_quest_program
        from quest.syntax.tokenizer import Tokenizer
        from quest.common.location import SourceMap

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
# Labels, which the writer and reader share
# ============================================================================


def _field_name(label: str) -> str:
    return label[4:] if label.startswith("var ") else ("" if label == "var" else label)


def _is_var_label(label: str) -> bool:
    return label.startswith("var ") or label == "var"
