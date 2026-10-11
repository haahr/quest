"""Quest Semantic Types, Kinds, Model Definitions, and Substitution."""

from __future__ import annotations

import dataclasses
import enum
import weakref
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, Union, runtime_checkable

from quest.diagnostics import (
    Diagnostic,
    DiagnosticRenderer,
    QuestCompilerError,
    TypeRecursionLimitExceeded,
)

# Deterministic safety bounds to prevent infinite recursion during type analysis
MAX_SUBTYPE_FUEL = 10_000
MAX_TYPE_EXPANSION_DEPTH = 500


@runtime_checkable
class TypeLookupEnv(Protocol):
    """Minimal environment protocol needed for lazy type variable evaluation."""
    def lookup_type_by_id(self, symbol_id: int) -> Optional[Any]: ...
    def lookup_type(self, name: str) -> Optional[Any]: ...

# ============================================================================
# Reserved Symbol Ids
# ============================================================================
#
# Symbol ids from the environment are positive, and inference metavariables count down from -1. A few type variables
# are made outside any environment (Dynamic's type parameter, and placeholders the C back end substitutes into types);
# their ids are negative too, so each use needs ids that no other use (and no metavariable) can produce.
#
# A reserved id is the negation of a prefix naming its use, times 2**32, plus an index within that use:
#
#     reserved_symbol_id(use, index) == -(use * 2**32 + index)
#
# Ids for different uses differ in their prefix, so they never coincide. Metavariable ids have prefix 0 (and
# QTypeMeta refuses to count past 2**32), so they never coincide with reserved ids either.


class ReservedSymbolUse(enum.IntEnum):
    """The uses of reserved symbol ids; each value is the prefix of that use's ids."""
    DYNAMIC_PARAM = 1  # Dynamic's type parameter (index 0)
    BOUND_VAR = 2  # placeholder for a bound type parameter of a polymorphic function type, by de Bruijn index
    CANONICAL_QUANTIFIER = 3  # quantifier of a polymorphic function type in canonical form, by position
    REC_SELF = 4  # placeholder for a recursion variable in the C tag of a recursive type, by nesting depth
    CANONICAL_REC = 5  # recursion variable of a recursive type in the C back end's canonical form, by position
    CANONICAL_BINDER = 6  # type parameter of a binder in the C back end's canonical form, by enclosing parameters
    HOLE = 7  # a type parameter of generic code in a C descriptor template, by position among the template's holes


RESERVED_INDEX_LIMIT = 1 << 32


def reserved_symbol_id(use: ReservedSymbolUse, index: int) -> int:
    """The reserved symbol id for the index-th variable of the given use."""
    if not 0 <= index < RESERVED_INDEX_LIMIT:
        raise ValueError(f"reserved symbol index {index} out of range for {use.name}")
    return -(use * RESERVED_INDEX_LIMIT + index)


def reserved_symbol_use(symbol_id: int) -> Optional[tuple[ReservedSymbolUse, int]]:
    """Decodes a reserved symbol id into its use and index, or returns None for any other id."""
    if symbol_id >= 0:
        return None
    prefix, index = divmod(-symbol_id, RESERVED_INDEX_LIMIT)
    if prefix not in ReservedSymbolUse._value2member_map_:
        return None
    return ReservedSymbolUse(prefix), index


def reserved_symbol_index(symbol_id: int, use: ReservedSymbolUse) -> Optional[int]:
    """The index of a symbol id reserved for `use`, or None if the id is not one of that use's."""
    decoded = reserved_symbol_use(symbol_id)
    if decoded is None or decoded[0] is not use:
        return None
    return decoded[1]


# ============================================================================
# 0. Free-Variable Metadata
# ============================================================================
#
# Every type node (and every component and kind) records, at construction, the symbol ids that a
# substitution could replace inside it (_fv) and whether it contains a metavariable (_has_meta).
# These mirror exactly what each substitute method does: a binder removes its own id from the
# substitution for the parts it scopes over, and parts that substitute leaves alone (such as the
# bounds of a QTypeFun's formals) contribute nothing. QType.substitute uses them to return a node
# untouched, without traversal, when no free variable is substituted. A node containing a
# metavariable is never skipped, because the metavariable may later be solved to anything.

_NO_FREE_VARS: frozenset[int] = frozenset()


def _set_free_vars(node: Any, free: Any, has_meta: bool) -> None:
    object.__setattr__(node, "_fv", frozenset(free) if free else _NO_FREE_VARS)
    object.__setattr__(node, "_has_meta", has_meta)


def _free_vars_of(parts: Any) -> tuple[set[int], bool]:
    """Union of the free variables of parts (None entries are skipped)."""
    free: set[int] = set()
    has_meta = False
    for part in parts:
        if part is not None:
            free |= part._fv
            has_meta = has_meta or part._has_meta
    return free, has_meta


def _init_free_vars(node: Any, *parts: Any, bound_ids: Any = ()) -> None:
    """Sets node's free variables to those of parts, minus bound_ids."""
    free, has_meta = _free_vars_of(parts)
    free.difference_update(bound_ids)
    _set_free_vars(node, free, has_meta)


# ============================================================================
# 0b. Hash-Consing
# ============================================================================
#
# Types, kinds, and their components are hash-consed: constructing a node returns the canonical
# object for its structure, so structurally identical nodes are one object and `is` decides
# structural identity. The key is the class and every field, display-only fields included (record
# provenance, binder and path names), so two nodes that would print differently are never merged.
# Child nodes appear in keys by identity, which is sound because they are canonical already.
# Nodes containing a metavariable are not interned: a metavariable is mutable, and a node that is
# shared must not change meaning when one inside it is solved. The table holds canonical nodes
# weakly, so types no longer referenced can be freed.

_INTERN_TABLE: "weakref.WeakValueDictionary[tuple[Any, ...], Any]" = weakref.WeakValueDictionary()


class _NotInternable(Exception):
    """A field value that cannot be part of an interning key."""


def _intern_key_part(value: Any) -> Any:
    if isinstance(type(value), _InternedNode):
        return (_InternedNode, id(value))
    if isinstance(value, tuple):
        return (tuple, tuple(_intern_key_part(v) for v in value))
    if value is None or isinstance(value, (str, int)):  # bool is an int: (type, value) keeps them apart
        return (type(value), value)
    raise _NotInternable(type(value).__name__)


def _intern(node: Any) -> Any:
    if getattr(node, "_has_meta", False):
        return node
    try:
        key = (type(node),) + tuple(_intern_key_part(getattr(node, f.name)) for f in dataclasses.fields(node))
    except _NotInternable:
        return node
    canonical = _INTERN_TABLE.get(key)
    if canonical is None:
        _INTERN_TABLE[key] = node
        return node
    return canonical


class _InternedNode(type):
    """Metaclass returning the canonical (hash-consed) instance for each constructed node."""

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        return _intern(super().__call__(*args, **kwargs))


# ============================================================================
# 1. Kinds (Level 2)
# ============================================================================

class QKind(metaclass=_InternedNode):
    """Base class for all Quest kinds."""

    _fv: frozenset[int] = _NO_FREE_VARS
    _has_meta: bool = False

    def evaluate_lazily(self, env: Optional[Any] = None) -> QKind:
        """Evaluates kind aliases lazily on demand."""
        return self

    def substitute_kinds(self, subst: dict[int, QKind]) -> QKind:
        """Substitutes kind variables keyed by symbol_id."""
        return self

    def substitute_types(self, subst: dict[int, QType]) -> QKind:
        """Substitutes type variables inside power kind bounds."""
        return self

    def substitute(self, subst: dict[int, QType]) -> QKind:
        """Alias for substitute_types."""
        return self.substitute_types(subst)


@dataclass(frozen=True)
class QTypeKind(QKind):
    """The base kind TYPE (all proper types)."""

    def __str__(self) -> str:
        return "TYPE"


@dataclass(frozen=True)
class QPowerKind(QKind):
    """The power kind POWER(bound) / <: bound (all subtypes of bound)."""
    bound: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.bound)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QKind:
        return QPowerKind(self.bound.evaluate_lazily(env))

    def substitute_types(self, subst: dict[int, QType]) -> QKind:
        bound = self.bound.substitute(subst)
        return self if bound is self.bound else QPowerKind(bound)

    def __str__(self) -> str:
        return f"<: {self.bound}"


@dataclass(frozen=True)
class QAllKind(QKind):
    """Higher-order operator kind: ALL(param::param_kind) result_kind."""
    param_name: str
    param_id: int
    param_kind: QKind
    result_kind: QKind

    def __post_init__(self) -> None:
        _init_free_vars(self, self.param_kind, self.result_kind)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QKind:
        return QAllKind(
            param_name=self.param_name,
            param_id=self.param_id,
            param_kind=self.param_kind.evaluate_lazily(env),
            result_kind=self.result_kind.evaluate_lazily(env),
        )

    def substitute_kinds(self, subst: dict[int, QKind]) -> QKind:
        if self.param_id in subst:
            active_subst = {k: v for k, v in subst.items() if k != self.param_id}
        else:
            active_subst = subst
        param_kind = self.param_kind.substitute_kinds(subst)
        result_kind = self.result_kind.substitute_kinds(active_subst)
        if param_kind is self.param_kind and result_kind is self.result_kind:
            return self
        return QAllKind(
            param_name=self.param_name,
            param_id=self.param_id,
            param_kind=param_kind,
            result_kind=result_kind,
        )

    def substitute_types(self, subst: dict[int, QType]) -> QKind:
        param_kind = self.param_kind.substitute_types(subst)
        result_kind = self.result_kind.substitute_types(subst)
        if param_kind is self.param_kind and result_kind is self.result_kind:
            return self
        return QAllKind(
            param_name=self.param_name,
            param_id=self.param_id,
            param_kind=param_kind,
            result_kind=result_kind,
        )

    def __str__(self) -> str:
        return f"ALL({self.param_name} :: {self.param_kind}) {self.result_kind}"


@dataclass(frozen=True)
class QKindVar(QKind):
    """Kind variable reference."""
    name: str
    symbol_id: int

    def evaluate_lazily(self, env: Optional[Any] = None) -> QKind:
        if env is not None and hasattr(env, "lookup_kind_by_id"):
            sym = env.lookup_kind_by_id(self.symbol_id)
            if sym is not None:
                return sym.kind.evaluate_lazily(env)
        return self

    def substitute_kinds(self, subst: dict[int, QKind]) -> QKind:
        return subst.get(self.symbol_id, self)

    def __str__(self) -> str:
        return self.name


# Canonical singletons for kinds
TYPE_KIND = QTypeKind()


def _all_same(new: Any, old: Any) -> bool:
    """True if two equal-length sequences hold identical objects; substitute returns self then."""
    return all(a is b for a, b in zip(new, old))


# ============================================================================
# 2. Base Semantic Type (Level 1)
# ============================================================================

class QType(metaclass=_InternedNode):
    """Base class for all semantic Quest types."""

    _fv: frozenset[int] = _NO_FREE_VARS
    _has_meta: bool = False

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        """Evaluates type aliases and applications lazily to expose the outermost constructor."""
        return self

    def substitute(self, subst: dict[int, QType]) -> QType:
        """Performs capture-avoiding substitution using symbol_id keys.

        Returns self, without traversal, when no free variable of this type is substituted.
        """
        if not self._has_meta and self._fv.isdisjoint(subst):
            return self
        return self._substitute_full(subst)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        """Substitution by traversal; subclasses with parts override it."""
        return self

    def format(self, env: Optional[Any] = None) -> str:
        """Formats this type into a readable string, utilizing env aliases and bounded recursions."""
        from quest.types.dump import format_type_compact
        return format_type_compact(self, env=env)

    # The __str__ methods of types, their components, and kinds are mirrored by _printed_parts in
    # quest/codegen/c_types.py, which digests types without printing them; change both together.
    def __str__(self) -> str:
        return self.__class__.__name__

    def __eq__(self, other: Any) -> bool:
        raise NotImplementedError(
            "Do not use Python == on Quest types; use is_type_equal(t1, t2, env) or reference identity ('is')"
        )


# ============================================================================
# 3. Primitive Types
# ============================================================================

@dataclass(frozen=True)
class QIntType(QType):
    def __str__(self) -> str:
        return "Int"


@dataclass(frozen=True)
class QRealType(QType):
    def __str__(self) -> str:
        return "Real"


@dataclass(frozen=True)
class QBoolType(QType):
    def __str__(self) -> str:
        return "Bool"


@dataclass(frozen=True)
class QCharType(QType):
    def __str__(self) -> str:
        return "Char"


@dataclass(frozen=True)
class QStringType(QType):
    def __str__(self) -> str:
        return "String"


@dataclass(frozen=True)
class QOkType(QType):
    def __str__(self) -> str:
        return "Ok"


@dataclass(frozen=True)
class QBottomType(QType):
    """Internal bottom type: subtype of all types, used for divergent expressions like raise."""
    def __str__(self) -> str:
        return "Bottom"


@dataclass(frozen=True)
class QExceptionType(QType):
    """Exception type, optionally carrying a payload type (defaults to Ok)."""
    payload_type: QType = field(default_factory=lambda: OK_TYPE)

    def __post_init__(self) -> None:
        _init_free_vars(self, self.payload_type)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        payload = self.payload_type.substitute(subst)
        return self if payload is self.payload_type else QExceptionType(payload_type=payload)

    def __str__(self) -> str:
        if self.payload_type is OK_TYPE:
            return "Exception"
        return f"Exception({self.payload_type})"


@dataclass(frozen=True)
class QExternalType(QType):
    """Opaque C data structure type (external "c_type")."""
    name: str
    c_type: str

    def __str__(self) -> str:
        return self.name if self.name else f'external "{self.c_type}"'


# Canonical singletons for primitive types
INT_TYPE = QIntType()
REAL_TYPE = QRealType()
BOOL_TYPE = QBoolType()
CHAR_TYPE = QCharType()
STRING_TYPE = QStringType()
OK_TYPE = QOkType()
BOTTOM_TYPE = QBottomType()
EXCEPTION_TYPE = QExceptionType()

# The names under which the environment declares the primitive types (Environment._init_builtins).
_BUILTIN_PRIMITIVE_NAMES: dict[str, QType] = {
    "Int": INT_TYPE, "Real": REAL_TYPE, "Bool": BOOL_TYPE, "Char": CHAR_TYPE, "String": STRING_TYPE,
    "Ok": OK_TYPE, "Exception": EXCEPTION_TYPE,
}



# ============================================================================
# 4. Composite Types (Tuples, Records, Variants, Options)
# ============================================================================

@dataclass(frozen=True)
class QTupleField(metaclass=_InternedNode):
    """A single (optionally named) value component in an ordered tuple type: [name:] T."""
    name: Optional[str]
    type_val: QType
    is_var: bool = False

    def __post_init__(self) -> None:
        _init_free_vars(self, self.type_val)

    def substitute(self, subst: dict[int, QType]) -> QTupleField:
        type_val = self.type_val.substitute(subst)
        return self if type_val is self.type_val else QTupleField(name=self.name, type_val=type_val, is_var=self.is_var)

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ""
        if self.name:
            return f"{var_prefix}{self.name}: {self.type_val}"
        return f"{var_prefix}:{self.type_val}"


@dataclass(frozen=True)
class QTupleTypeFormal(metaclass=_InternedNode):
    """A type formal component in an ordered tuple type: X::K."""
    name: str
    symbol_id: int
    bound: QKind

    def __post_init__(self) -> None:
        _init_free_vars(self, self.bound)

    def substitute(self, subst: dict[int, QType]) -> QTupleTypeFormal:
        bound = self.bound.substitute_types(subst)
        if bound is self.bound:
            return self
        return QTupleTypeFormal(name=self.name, symbol_id=self.symbol_id, bound=bound)

    def __str__(self) -> str:
        return f"{self.name}::{self.bound}"


@dataclass(frozen=True)
class QTupleTypeBinding(metaclass=_InternedNode):
    """A manifest type definition inside a tuple signature: Let X::K = T."""
    name: str
    type_val: QType
    bound: Optional[QKind] = None

    def __post_init__(self) -> None:
        _init_free_vars(self, self.type_val, self.bound)

    def substitute(self, subst: dict[int, QType]) -> QTupleTypeBinding:
        type_val = self.type_val.substitute(subst)
        bound = self.bound.substitute_types(subst) if self.bound else None
        if type_val is self.type_val and bound is self.bound:
            return self
        return QTupleTypeBinding(name=self.name, type_val=type_val, bound=bound)

    def __str__(self) -> str:
        bound_str = f"::{self.bound} " if self.bound else ""
        return f"Let {self.name}{bound_str}= {self.type_val}"


QTupleComponent = Union[QTupleField, QTupleTypeFormal, QTupleTypeBinding]


@dataclass(frozen=True)
class QTupleType(QType):
    """Ordered tuple type: Tuple [x:] T1 ... [y:] Tn end."""
    fields: tuple[QTupleComponent, ...]

    def __init__(self, elements: tuple[Union[QType, QTupleComponent], ...] = ()) -> None:
        normalized: list[QTupleComponent] = []
        for item in elements:
            if isinstance(item, (QTupleField, QTupleTypeFormal, QTupleTypeBinding)):
                normalized.append(item)
            else:
                normalized.append(QTupleField(name=None, type_val=item))
        object.__setattr__(self, "fields", tuple(normalized))
        # A type formal's bound sees the substitution; later fields do not see the formal's id.
        free: set[int] = set()
        bound_ids: set[int] = set()
        has_meta = False
        for f in self.fields:
            free |= f._fv - bound_ids
            has_meta = has_meta or f._has_meta
            if isinstance(f, QTupleTypeFormal):
                bound_ids.add(f.symbol_id)
        _set_free_vars(self, free, has_meta)

    @property
    def components(self) -> tuple[QTupleComponent, ...]:
        return self.fields

    @property
    def elements(self) -> tuple[QType, ...]:
        return tuple(f.type_val for f in self.fields if isinstance(f, (QTupleField, QTupleTypeBinding)))

    @property
    def value_fields(self) -> tuple[QTupleField, ...]:
        return tuple(f for f in self.fields if isinstance(f, QTupleField))

    @property
    def type_formals(self) -> tuple[QTupleTypeFormal, ...]:
        return tuple(f for f in self.fields if isinstance(f, QTupleTypeFormal))

    @property
    def is_existential(self) -> bool:
        return any(isinstance(f, QTupleTypeFormal) for f in self.fields)

    def get_field(self, name: str) -> Optional[QTupleComponent]:
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, QTupleType):
            return False
        if len(self.fields) != len(other.fields):
            return False
        for f1, f2 in zip(self.fields, other.fields):
            if type(f1) is not type(f2):
                return False
            if isinstance(f1, QTupleTypeFormal):
                assert isinstance(f2, QTupleTypeFormal)
                if f1.name != f2.name or f1.bound != f2.bound:
                    return False
            elif isinstance(f1, QTupleField):
                assert isinstance(f2, QTupleField)
                if f1.name is not None and f2.name is not None and f1.name != f2.name:
                    return False
                if f1.is_var != f2.is_var:
                    return False
                if f1.type_val != f2.type_val:
                    return False
            elif isinstance(f1, QTupleTypeBinding):
                assert isinstance(f2, QTupleTypeBinding)
                if f1.name != f2.name or f1.type_val != f2.type_val or f1.bound != f2.bound:
                    return False
        return True

    def __hash__(self) -> int:
        return hash(self.fields)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        curr_subst = dict(subst)
        new_fields: list[QTupleComponent] = []
        for f in self.fields:
            if isinstance(f, QTupleTypeFormal):
                new_f = f.substitute(curr_subst)
                new_fields.append(new_f)
                if f.symbol_id in curr_subst:
                    curr_subst.pop(f.symbol_id)
            elif isinstance(f, (QTupleField, QTupleTypeBinding)):
                new_fields.append(f.substitute(curr_subst))
            else:
                new_fields.append(f)
        if _all_same(new_fields, self.fields):
            return self
        return QTupleType(tuple(new_fields))

    def __str__(self) -> str:
        elems = " ".join(str(f) for f in self.fields)
        return f"Tuple {elems} end" if elems else "Tuple end"


@dataclass(frozen=True)
class QRecordField(metaclass=_InternedNode):
    """A single field inside a record type."""
    name: str
    type_val: QType
    is_var: bool = False

    def __post_init__(self) -> None:
        _init_free_vars(self, self.type_val)

    def substitute(self, subst: dict[int, QType]) -> QRecordField:
        type_val = self.type_val.substitute(subst)
        if type_val is self.type_val:
            return self
        return QRecordField(name=self.name, type_val=type_val, is_var=self.is_var)

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ""
        return f"{var_prefix}{self.name}: {self.type_val}"


@dataclass(frozen=True)
class QRecordType(QType):
    """Unordered record type with structural subtyping: Record [var] x: T ... end."""
    fields: tuple[QRecordField, ...]
    provenance: Optional[str] = field(default=None, compare=False)

    def __post_init__(self) -> None:
        _init_free_vars(self, *self.fields)

    def get_field(self, name: str) -> Optional[QRecordField]:
        for field_entry in self.fields:
            if field_entry.name == name:
                return field_entry
        return None

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        fields = tuple(f.substitute(subst) for f in self.fields)
        return self if _all_same(fields, self.fields) else QRecordType(fields, provenance=self.provenance)

    def __str__(self) -> str:
        if self.provenance:
            return f"Module '{self.provenance}'"
        fields_str = " ".join(str(f) for f in self.fields)
        return f"Record {fields_str} end" if fields_str else "Record end"


def binds_module(name: str, t: QType) -> bool:
    """Whether a value binding of name with type t is the module bound to that name, not a binding shadowing it.

    A module's binding has the module's record type, whose provenance is the name the module is bound to.
    """
    return isinstance(t, QRecordType) and t.provenance == name


@dataclass(frozen=True)
class QVariantField(metaclass=_InternedNode):
    """A tagged branch inside a variant type."""
    name: str
    type_val: Optional[QType] = None
    is_var: bool = False

    def __post_init__(self) -> None:
        _init_free_vars(self, self.type_val)

    def substitute(self, subst: dict[int, QType]) -> QVariantField:
        type_val = self.type_val.substitute(subst) if self.type_val else None
        if type_val is self.type_val:
            return self
        return QVariantField(name=self.name, type_val=type_val, is_var=self.is_var)

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ""
        if self.type_val:
            return f"{var_prefix}{self.name}: {self.type_val}"
        return f"{var_prefix}{self.name}"


@dataclass(frozen=True)
class QVariantType(QType):
    """Variant type: Variant tag1: T1 ... end."""
    variants: tuple[QVariantField, ...]

    def __post_init__(self) -> None:
        _init_free_vars(self, *self.variants)

    def get_variant(self, name: str) -> Optional[QVariantField]:
        for v in self.variants:
            if v.name == name:
                return v
        return None

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        variants = tuple(v.substitute(subst) for v in self.variants)
        return self if _all_same(variants, self.variants) else QVariantType(variants)

    def __str__(self) -> str:
        variants_str = " ".join(str(v) for v in self.variants)
        return f"Variant {variants_str} end" if variants_str else "Variant end"


@dataclass(frozen=True)
class QOptionField(metaclass=_InternedNode):
    """A tagged case inside an option type."""
    name: str
    payload_type: Optional[QType] = None

    def __post_init__(self) -> None:
        _init_free_vars(self, self.payload_type)

    def substitute(self, subst: dict[int, QType]) -> QOptionField:
        payload = self.payload_type.substitute(subst) if self.payload_type else None
        return self if payload is self.payload_type else QOptionField(name=self.name, payload_type=payload)

    def __str__(self) -> str:
        if self.payload_type:
            return f"{self.name} with {self.payload_type}"
        return self.name


@dataclass(frozen=True)
class QOptionType(QType):
    """Option type: Option tag1 tag2 with T end."""
    options: tuple[QOptionField, ...]

    def __post_init__(self) -> None:
        _init_free_vars(self, *self.options)

    def get_option(self, name: str) -> Optional[QOptionField]:
        for opt in self.options:
            if opt.name == name:
                return opt
        return None

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        options = tuple(o.substitute(subst) for o in self.options)
        return self if _all_same(options, self.options) else QOptionType(options)

    def __str__(self) -> str:
        options_str = " ".join(str(o) for o in self.options)
        return f"Option {options_str} end" if options_str else "Option end"


# ============================================================================
# 5. Functions, References, and Computation Types
# ============================================================================

@dataclass(frozen=True)
class QParam(metaclass=_InternedNode):
    """Formal parameter to a function."""
    name: str
    type_val: QType
    is_var: bool = False
    is_out: bool = False

    def __post_init__(self) -> None:
        _init_free_vars(self, self.type_val)

    def substitute(self, subst: dict[int, QType]) -> QParam:
        type_val = self.type_val.substitute(subst)
        if type_val is self.type_val:
            return self
        return QParam(name=self.name, type_val=type_val, is_var=self.is_var, is_out=self.is_out)

    def __str__(self) -> str:
        prefix = "var " if self.is_var else ("out " if self.is_out else "")
        return f"{prefix}{self.name}: {self.type_val}"


@dataclass(frozen=True)
class QFunType(QType):
    """Function type: Fun(params) : result_type."""
    params: tuple[QParam, ...]
    result_type: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, *self.params, self.result_type)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        params = tuple(p.substitute(subst) for p in self.params)
        result_type = self.result_type.substitute(subst)
        if result_type is self.result_type and _all_same(params, self.params):
            return self
        return QFunType(params=params, result_type=result_type)

    def __str__(self) -> str:
        params_str = " ".join(str(p) for p in self.params)
        return f"Fun({params_str}): {self.result_type}"


@dataclass(frozen=True)
class QVarType(QType):
    """Mutable reference cell type: Var(T)."""
    element_type: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.element_type)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QVarType(element_type)

    def __str__(self) -> str:
        return f"Var({self.element_type})"


@dataclass(frozen=True)
class QArrayType(QType):
    """Mutable array type: Array(T)."""
    element_type: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.element_type)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QArrayType(element_type)

    def __str__(self) -> str:
        return f"Array({self.element_type})"


@dataclass(frozen=True)
class QOutType(QType):
    """Write-only output parameter type: Out(T)."""
    element_type: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.element_type)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QOutType(element_type)

    def __str__(self) -> str:
        return f"Out({self.element_type})"


# ============================================================================
# 6. Polymorphic, Higher-Order, and Parameterized Types
# ============================================================================

@dataclass(frozen=True)
class QQuantifier(metaclass=_InternedNode):
    """Type quantifier in All(X::K) T or All(X <: Bound) T."""
    name: str
    symbol_id: int
    bound: QKind

    def __post_init__(self) -> None:
        _init_free_vars(self, self.bound)

    def substitute(self, subst: dict[int, QType]) -> QQuantifier:
        bound = self.bound.substitute_types(subst)
        if bound is self.bound:
            return self
        return QQuantifier(name=self.name, symbol_id=self.symbol_id, bound=bound)

    def __str__(self) -> str:
        if isinstance(self.bound, QPowerKind):
            return f"{self.name} <: {self.bound.bound}"
        return f"{self.name} :: {self.bound}"


@dataclass(frozen=True)
class QAllType(QType):
    """Universal quantification: All(X::K) T."""
    quantifiers: tuple[QQuantifier, ...]
    body: QType

    def __post_init__(self) -> None:
        # Quantifier bounds see the whole substitution; the body does not see the quantified ids.
        free, has_meta = _free_vars_of(self.quantifiers)
        body_free = set(self.body._fv)
        body_free.difference_update(q.symbol_id for q in self.quantifiers)
        _set_free_vars(self, free | body_free, has_meta or self.body._has_meta)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        # Avoid capturing bound quantifiers
        bound_ids = {q.symbol_id for q in self.quantifiers}
        active_subst = {k: v for k, v in subst.items() if k not in bound_ids}
        quantifiers = tuple(q.substitute(subst) for q in self.quantifiers)
        body = self.body.substitute(active_subst)
        if body is self.body and _all_same(quantifiers, self.quantifiers):
            return self
        return QAllType(quantifiers=quantifiers, body=body)

    def __str__(self) -> str:
        quants = " ".join(str(q) for q in self.quantifiers)
        return f"All({quants}) {self.body}"


@dataclass(frozen=True)
class QAutoType(QType):
    """Existential / automorphic type: Auto X::K with ... end."""
    type_param: str
    symbol_id: int
    kind_bound: QKind
    signature: tuple[QRecordField, ...]

    def __post_init__(self) -> None:
        _init_free_vars(self, *self.signature, bound_ids=(self.symbol_id,))

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        if self.symbol_id in subst:
            active_subst = {k: v for k, v in subst.items() if k != self.symbol_id}
        else:
            active_subst = subst
        signature = tuple(f.substitute(active_subst) for f in self.signature)
        if _all_same(signature, self.signature):
            return self
        return QAutoType(
            type_param=self.type_param,
            symbol_id=self.symbol_id,
            kind_bound=self.kind_bound,
            signature=signature,
        )

    def __str__(self) -> str:
        sig_str = " ".join(str(f) for f in self.signature)
        if isinstance(self.kind_bound, QPowerKind):
            return f"Auto {self.type_param} <: {self.kind_bound.bound} with {sig_str} end"
        return f"Auto {self.type_param} :: {self.kind_bound} with {sig_str} end"


def auto_payload_type(auto: QAutoType, witness: Optional[QType] = None) -> QTupleType:
    """The tuple type of an auto value's payload: Tuple S[witness] end for the signature S.

    Without a witness, the result is the witness-independent layout used to store payloads, in which the
    type parameter is an abstract type bounded by the auto type's kind.
    """
    if witness is None:
        witness = QAbstractType(name=auto.type_param, symbol_id=auto.symbol_id, bound=auto.kind_bound)
    subst = {auto.symbol_id: witness}
    return QTupleType(tuple(
        QTupleField(name=f.name, type_val=f.type_val.substitute(subst), is_var=f.is_var)
        for f in auto.signature
    ))


def auto_matches_subtypes(auto: QAutoType) -> bool:
    """True if inspect may select a branch whose type is a proper supertype of an auto value's type.

    That is sound only when the type parameter occurs in the signature solely as the whole type of
    immutable components (fst,snd:A), so that each component may be viewed at the supertype. Otherwise
    (e.g. f(x:A):Int, l:List(A)) a branch is selected only when the types are equal. A signature with
    var components also matches exactly, so that the binders always share the auto value's components.
    """
    for f in auto.signature:
        if f.is_var:
            return False
        if auto.symbol_id not in f.type_val._fv:
            continue
        t = unalias(f.type_val)
        if not isinstance(t, (QTypeVar, QAbstractType)) or t.symbol_id != auto.symbol_id:
            return False
    return True


@dataclass(frozen=True)
class QTypeFormal(metaclass=_InternedNode):
    """Formal type parameter for a type-level function: Fun(X::K) T."""
    name: str
    symbol_id: int
    bound: QKind

    def __str__(self) -> str:
        return f"{self.name} :: {self.bound}"


@dataclass(frozen=True)
class QTypeFun(QType):
    """Type-level abstraction: Fun(X::K) BodyType."""
    params: tuple[QTypeFormal, ...]
    body: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.body, bound_ids=[p.symbol_id for p in self.params])

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        bound_ids = {p.symbol_id for p in self.params}
        active_subst = {k: v for k, v in subst.items() if k not in bound_ids}
        body = self.body.substitute(active_subst)
        return self if body is self.body else QTypeFun(params=self.params, body=body)

    def __str__(self) -> str:
        params_str = " ".join(str(p) for p in self.params)
        return f"Fun({params_str}) {self.body}"


@dataclass(frozen=True)
class QTypeApp(QType):
    """Type operator application: Constructor(Arg1, ..., ArgN)."""
    constructor: QType
    arguments: tuple[QType, ...]

    def __post_init__(self) -> None:
        _init_free_vars(self, self.constructor, *self.arguments)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        ctor = self.constructor.evaluate_lazily(env)
        if isinstance(ctor, QExceptionType) and len(self.arguments) == 1:
            return QExceptionType(payload_type=self.arguments[0].evaluate_lazily(env))
        if isinstance(ctor, QTypeFun):
            subst = {
                formal.symbol_id: arg
                for formal, arg in zip(ctor.params, self.arguments)
            }
            return ctor.body.substitute(subst).evaluate_lazily(env)
        return QTypeApp(constructor=ctor, arguments=self.arguments)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        constructor = self.constructor.substitute(subst)
        arguments = tuple(arg.substitute(subst) for arg in self.arguments)
        if constructor is self.constructor and _all_same(arguments, self.arguments):
            return self
        return QTypeApp(constructor=constructor, arguments=arguments)

    def __str__(self) -> str:
        args_str = " ".join(str(a) for a in self.arguments)
        return f"{self.constructor}({args_str})"


# ============================================================================
# 7. Recursive Types, Variables, and Abstract Types
# ============================================================================

@dataclass(frozen=True)
class QRecType(QType):
    """Single recursive type: Rec(X::K) T."""
    var_name: str
    symbol_id: int
    bound: QKind
    body: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.body, bound_ids=(self.symbol_id,))

    def unfold_lazily(self) -> QType:
        """Unfolds Rec(X) T lazily by substituting Rec(X) T for X in T.

        The unfolding is a pure function of this immutable node, so it is computed once and cached;
        since it refers back to self, repeated unfoldings share one finite object graph.
        """
        unfolded = self.__dict__.get("_unfolded")
        if unfolded is None:
            unfolded = self.body.substitute({self.symbol_id: self})
            object.__setattr__(self, "_unfolded", unfolded)
        return unfolded

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self.unfold_lazily().evaluate_lazily(env)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        if self.symbol_id in subst:
            active_subst = {k: v for k, v in subst.items() if k != self.symbol_id}
        else:
            active_subst = subst
        body = self.body.substitute(active_subst)
        if body is self.body:
            return self
        return QRecType(var_name=self.var_name, symbol_id=self.symbol_id, bound=self.bound, body=body)

    def __str__(self) -> str:
        return f"Rec({self.var_name} :: {self.bound}) {self.body}"


@dataclass(frozen=True)
class QRecGroupType(QType):
    """Mutually recursive type group: Let Rec T1 = ... and T2 = ..."""
    # Each entry: (name, symbol_id, bound_kind, body_type)
    bindings: tuple[tuple[str, int, QKind, QType], ...]
    active_index: int = 0

    def __post_init__(self) -> None:
        _init_free_vars(self, *(b[3] for b in self.bindings), bound_ids=[b[1] for b in self.bindings])

    @property
    def current_symbol_id(self) -> int:
        return self.bindings[self.active_index][1]

    @property
    def current_name(self) -> str:
        return self.bindings[self.active_index][0]

    def siblings(self) -> tuple[QRecGroupType, ...]:
        """The canonical node for each binding of this group, shared by all of them."""
        siblings = self.__dict__.get("_siblings")
        if siblings is None:
            siblings = tuple(
                QRecGroupType(bindings=self.bindings, active_index=idx) for idx in range(len(self.bindings))
            )
            existing = siblings[0].__dict__.get("_siblings")
            if existing is not None:
                siblings = existing
            else:
                for node in siblings:
                    object.__setattr__(node, "_siblings", siblings)
            object.__setattr__(self, "_siblings", siblings)
        return siblings

    def unfold_lazily(self) -> QType:
        """Unfolds the active mutually recursive binding lazily.

        Cached like QRecType.unfold_lazily; substituting the shared sibling nodes keeps the unfoldings
        of all bindings of the group within one finite object graph.
        """
        unfolded = self.__dict__.get("_unfolded")
        if unfolded is None:
            subst = {binding[1]: node for binding, node in zip(self.bindings, self.siblings())}
            unfolded = self.bindings[self.active_index][3].substitute(subst)
            object.__setattr__(self, "_unfolded", unfolded)
        return unfolded

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self.unfold_lazily().evaluate_lazily(env)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        bound_ids = {b[1] for b in self.bindings}
        active_subst = {k: v for k, v in subst.items() if k not in bound_ids}
        new_bodies = tuple(b[3].substitute(active_subst) for b in self.bindings)
        if all(nb is b[3] for nb, b in zip(new_bodies, self.bindings)):
            return self
        new_bindings = tuple((b[0], b[1], b[2], nb) for b, nb in zip(self.bindings, new_bodies))
        return QRecGroupType(bindings=new_bindings, active_index=self.active_index)

    def __str__(self) -> str:
        # Like Rec(X::K) T, with the active binding's body; the other bindings' variables print as their names
        name, _, bound, body = self.bindings[self.active_index]
        return f"Rec({name} :: {bound}) {body}"


@dataclass(frozen=True)
class QTypeVar(QType):
    """Named type variable with unique symbol identity."""
    name: str
    symbol_id: int
    bound: Optional[QKind] = None

    def __post_init__(self) -> None:
        _set_free_vars(self, (self.symbol_id,), False)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        if env is not None:
            sym = env.lookup_type_by_id(self.symbol_id) if hasattr(env, "lookup_type_by_id") else None
            if sym is not None and sym.definition is not None:
                return sym.definition.evaluate_lazily(env)
        return self

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        return subst.get(self.symbol_id, self)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class QAbstractType(QType):
    """An abstract type bounded by a kind."""
    name: str
    symbol_id: int
    bound: QKind

    def __post_init__(self) -> None:
        _set_free_vars(self, (self.symbol_id,), False)

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        return subst.get(self.symbol_id, self)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class QPathType(QType):
    """Path-dependent abstract type projected from an immutable value binding: x.A."""
    root_name: str
    root_symbol_id: int
    field_name: str
    bound: QKind = field(compare=False)

    def __post_init__(self) -> None:
        _init_free_vars(self, self.bound)

    @property
    def symbol_id(self) -> int:
        return hash((self.root_symbol_id, self.field_name))

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        new_bound = self.bound.substitute_types(subst)
        if new_bound is not self.bound:
            return QPathType(
                root_name=self.root_name,
                root_symbol_id=self.root_symbol_id,
                field_name=self.field_name,
                bound=new_bound,
            )
        return self

    def __str__(self) -> str:
        return f"{self.root_name}.{self.field_name}"


@dataclass(frozen=True)
class QAliasType(QType):
    """A reference to a type alias, as written in the source (Span, location.Span, ast.Expr).

    The node is transparent: evaluation (and so subtyping and kinding) looks straight through it to
    the alias's definition, its target. It exists so that the printer and the .qi writer can show the
    name that was written. Hash-consing keeps references to different aliases (or the same alias
    spelled differently) apart, because the name and symbol are part of the key. C code generation
    never sees alias nodes; they are stripped at the codegen boundary (strip_aliases).
    """
    name: str
    symbol_id: int
    target: QType

    def __post_init__(self) -> None:
        _init_free_vars(self, self.target)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        if isinstance(self.target, (QRecType, QRecGroupType)):
            return self.unfold_lazily().evaluate_lazily(env)
        return self.target.evaluate_lazily(env)

    def unfold_lazily(self) -> QType:
        """Unfolds an alias of a recursive type through the alias: Rec(X) T, named N, unfolds to T[N/X].

        Equivalent to unfolding the target (the alias equals it), but recursive occurrences keep
        printing as the alias's name. Cached like QRecType.unfold_lazily; the unfolding refers back to
        this node, so it stays a finite object graph.

        A binding of a mutually recursive group unfolds likewise, with each other binding of the group
        replaced by an alias named after it, qualified as this alias is (m.Forest unfolds with m.Tree).
        Those aliases are the nodes that references to the other bindings elaborate to, so the
        unfoldings of a group's aliases also share one finite object graph.
        """
        unfolded = self.__dict__.get("_unfolded")
        if unfolded is None:
            target = self.target
            if isinstance(target, QRecType):
                unfolded = target.body.substitute({target.symbol_id: self})
            else:
                assert isinstance(target, QRecGroupType)
                qualifier = (
                    self.name[: -len(target.current_name)] if self.name.endswith(target.current_name) else ""
                )
                subst: dict[int, QType] = {
                    binding[1]: self if node is target else QAliasType(
                        name=qualifier + binding[0], symbol_id=binding[1], target=node
                    )
                    for binding, node in zip(target.bindings, target.siblings())
                }
                unfolded = target.bindings[target.active_index][3].substitute(subst)
            object.__setattr__(self, "_unfolded", unfolded)
        return unfolded

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        target = self.target.substitute(subst)
        # A substitution that changes the target leaves a type that is no longer the named alias.
        return self if target is self.target else target

    def __str__(self) -> str:
        return self.name


def alias_reference(name: str, symbol_id: int, target: QType) -> QType:
    """The elaboration of a reference to the alias `name`: an alias node, except for builtin primitives.

    A primitive's own name (Int, Ok, ...) is declared as a type symbol defined as the primitive; it is
    not a user alias and prints the same either way, so its references elaborate to the primitive.
    """
    if _BUILTIN_PRIMITIVE_NAMES.get(name) is target:
        return target
    return QAliasType(name=name, symbol_id=symbol_id, target=target)


def unalias(t: QType) -> QType:
    """Looks through alias reference nodes at the top of t."""
    while isinstance(t, QAliasType):
        t = t.target
    return t


# Cardelli's Dynamic_T (Typeful Programming §9.1): a value of any type packaged with its type, the auto type
# Auto A::TYPE with a:A end. (His appendix writes the component unnamed, Auto A::TYPE with :A end, but an unnamed
# component cannot be selected, so this follows §9.1.) The global type name Dynamic denotes it, as does the
# dynamic module's T. Its type parameter has a reserved symbol id.
_DYNAMIC_PARAM_ID = reserved_symbol_id(ReservedSymbolUse.DYNAMIC_PARAM, 0)
DYNAMIC_TYPE = QAutoType(
    type_param="A",
    symbol_id=_DYNAMIC_PARAM_ID,
    kind_bound=TYPE_KIND,
    signature=(QRecordField(name="a", type_val=QTypeVar(name="A", symbol_id=_DYNAMIC_PARAM_ID, bound=TYPE_KIND)),),
)


# strip_aliases results for canonical nodes, which are immutable: (node, result) by id(node).
_STRIPPED: dict[int, tuple[Any, Any]] = {}


def strip_aliases(node: Any, memo: Optional[dict[int, Any]] = None) -> Any:
    """Rebuilds a type (or kind, or component) with every alias reference replaced by its target."""
    if memo is None:
        memo = {}
    key = id(node)
    if key in memo:
        return memo[key]
    cached = _STRIPPED.get(key)
    if cached is not None and cached[0] is node:
        return cached[1]
    result = node
    if isinstance(node, QAliasType):
        result = strip_aliases(node.target, memo)
    elif isinstance(node, QTypeMeta):
        pruned = node.prune()
        result = node if pruned is node else strip_aliases(pruned, memo)
    elif isinstance(node, tuple):
        items = tuple(strip_aliases(item, memo) for item in node)
        if any(a is not b for a, b in zip(items, node)):
            result = items
    elif isinstance(type(node), _InternedNode) and dataclasses.is_dataclass(node):
        values = {f.name: getattr(node, f.name) for f in dataclasses.fields(node)}
        stripped = {k: strip_aliases(v, memo) for k, v in values.items()}
        if any(stripped[k] is not values[k] for k in values):
            result = QTupleType(stripped["fields"]) if isinstance(node, QTupleType) else type(node)(**stripped)
    memo[key] = result
    if isinstance(type(node), _InternedNode) and not getattr(node, "_has_meta", False):
        if len(_STRIPPED) > 200_000:
            _STRIPPED.clear()
        _STRIPPED[key] = (node, result)
    return result


def find_path_types(typ: QType) -> list[QPathType]:
    """Finds all QPathType instances occurring anywhere within a QType."""
    result: list[QPathType] = []
    visited: set[int] = set()

    def visit(t: QType) -> None:
        t_id = id(t)
        if t_id in visited:
            return
        visited.add(t_id)

        if isinstance(t, QPathType):
            result.append(t)
            if isinstance(t.bound, QPowerKind):
                visit(t.bound.bound)
        elif isinstance(t, QFunType):
            for p in t.params:
                visit(p.type_val)
            visit(t.result_type)
        elif isinstance(t, QTupleType):
            for f in t.fields:
                if isinstance(f, (QTupleField, QTupleTypeBinding)):
                    visit(f.type_val)
                elif isinstance(f, QTupleTypeFormal):
                    if isinstance(f.bound, QPowerKind):
                        visit(f.bound.bound)
        elif isinstance(t, QRecordType):
            for rf in t.fields:
                visit(rf.type_val)
        elif isinstance(t, QAllType):
            for q in t.quantifiers:
                if isinstance(q.bound, QPowerKind):
                    visit(q.bound.bound)
            visit(t.body)
        elif isinstance(t, QAutoType):
            for rf in t.signature:
                visit(rf.type_val)
        elif isinstance(t, QOptionType):
            for of in t.options:
                if of.payload_type is not None:
                    visit(of.payload_type)
        elif isinstance(t, QVariantType):
            for vf in t.variants:
                if vf.type_val is not None:
                    visit(vf.type_val)
        elif isinstance(t, (QVarType, QArrayType, QOutType)):
            visit(t.element_type)
        elif isinstance(t, QTypeApp):
            visit(t.constructor)
            for arg in t.arguments:
                visit(arg)
        elif isinstance(t, QRecType):
            visit(t.body)
        elif isinstance(t, QRecGroupType):
            for b in t.bindings:
                visit(b[3])
        elif isinstance(t, QExceptionType):
            visit(t.payload_type)
        elif isinstance(t, QAliasType):
            visit(t.target)

    visit(typ)
    return result


def type_mentions_symbol_ids(typ: QType, sym_ids: set[int]) -> bool:
    """Returns True if the given type mentions any symbol ID from sym_ids."""
    if not sym_ids:
        return False
    visited: set[int] = set()

    def visit(t: QType) -> bool:
        t_id = id(t)
        if t_id in visited:
            return False
        visited.add(t_id)

        if isinstance(t, (QTypeVar, QAbstractType)):
            if t.symbol_id in sym_ids:
                return True
        elif isinstance(t, QPathType):
            if isinstance(t.bound, QPowerKind) and visit(t.bound.bound):
                return True
        elif isinstance(t, QFunType):
            if any(visit(p.type_val) for p in t.params) or visit(t.result_type):
                return True
        elif isinstance(t, QTupleType):
            for f in t.fields:
                if isinstance(f, (QTupleField, QTupleTypeBinding)) and visit(f.type_val):
                    return True
                elif isinstance(f, QTupleTypeFormal) and isinstance(f.bound, QPowerKind):
                    if visit(f.bound.bound):
                        return True
        elif isinstance(t, QRecordType):
            if any(visit(rf.type_val) for rf in t.fields):
                return True
        elif isinstance(t, QAllType):
            if any(isinstance(q.bound, QPowerKind) and visit(q.bound.bound) for q in t.quantifiers):
                return True
            return visit(t.body)
        elif isinstance(t, QAutoType):
            return any(visit(rf.type_val) for rf in t.signature)
        elif isinstance(t, QOptionType):
            return any(of.payload_type is not None and visit(of.payload_type) for of in t.options)
        elif isinstance(t, QVariantType):
            return any(vf.type_val is not None and visit(vf.type_val) for vf in t.variants)
        elif isinstance(t, (QVarType, QArrayType, QOutType)):
            return visit(t.element_type)
        elif isinstance(t, QTypeApp):
            return visit(t.constructor) or any(visit(arg) for arg in t.arguments)
        elif isinstance(t, QRecType):
            return visit(t.body)
        elif isinstance(t, QRecGroupType):
            return any(visit(b[3]) for b in t.bindings)
        elif isinstance(t, QExceptionType):
            return visit(t.payload_type)
        elif isinstance(t, QAliasType):
            return visit(t.target)
        return False

    return visit(typ)


# ============================================================================
# 8. Type Inference Metavariable
# ============================================================================

class QTypeMeta(QType):
    """Mutable type metavariable (?T_1) for local bidirectional unification."""
    _counter: int = 0
    _has_meta: bool = True

    def __init__(self, bound: QKind = TYPE_KIND, name: Optional[str] = None):
        QTypeMeta._counter += 1
        if QTypeMeta._counter >= RESERVED_INDEX_LIMIT:
            raise RuntimeError("too many type metavariables: their ids would collide with reserved symbol ids")
        self.symbol_id: int = -QTypeMeta._counter  # Negative IDs for inference metavars (see Reserved Symbol Ids)
        self.bound: QKind = bound
        self.name: str = name or f"?T{abs(self.symbol_id)}"
        self.instance: Optional[QType] = None

    @classmethod
    def reset_counter(cls) -> None:
        cls._counter = 0

    def is_solved(self) -> bool:
        return self.instance is not None

    def prune(self) -> QType:
        """Flattens chained metavariable instantiations."""
        if self.instance is not None:
            if isinstance(self.instance, QTypeMeta):
                self.instance = self.instance.prune()
            return self.instance
        return self

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        pruned = self.prune()
        if pruned is not self:
            return pruned.evaluate_lazily(env)
        return self

    def _substitute_full(self, subst: dict[int, QType]) -> QType:
        pruned = self.prune()
        if pruned is not self:
            return pruned.substitute(subst)
        return subst.get(self.symbol_id, self)

    def __str__(self) -> str:
        pruned = self.prune()
        if pruned is not self:
            return str(pruned)
        return self.name

    def __repr__(self) -> str:
        pruned = self.prune()
        if pruned is not self:
            return f"QTypeMeta({self.name} => {pruned!r})"
        return f"QTypeMeta({self.name})"


def unsolved_metas(t: Union[QType, QKind, None]) -> list[QTypeMeta]:
    """Returns the unsolved metavariables occurring in t (looking through solved ones), in order."""
    found: list[QTypeMeta] = []
    visited: set[int] = set()

    def visit(node: Any) -> None:
        if node is None or isinstance(node, (str, int, bool)) or id(node) in visited:
            return
        visited.add(id(node))
        if isinstance(node, QTypeMeta):
            pruned = node.prune()
            if pruned is node:
                found.append(node)
            else:
                visit(pruned)
        elif isinstance(node, (tuple, list)):
            for item in node:
                visit(item)
        elif dataclasses.is_dataclass(node):
            for f in dataclasses.fields(node):
                visit(getattr(node, f.name))

    visit(t)
    return found


def resolve_metas(t: QType) -> QType:
    """Replaces solved metavariables in t by their solutions (substitution prunes them)."""
    return t.substitute({})


def structurally_equal(a: Any, b: Any) -> bool:
    """True if two types (or kinds, or components) have identical structure, field by field.

    Metavariables compare by identity after pruning. This is not type equivalence (see
    is_type_equal); it is used to cross-check optimizations that must not change any structure.
    """

    assumed: set[tuple[int, int]] = set()

    def eq(x: Any, y: Any) -> bool:
        if x is y:
            return True
        if isinstance(x, QTypeMeta):
            x = x.prune()
        if isinstance(y, QTypeMeta):
            y = y.prune()
        if x is y:
            return True
        if isinstance(x, QTypeMeta) or isinstance(y, QTypeMeta) or type(x) is not type(y):
            return False
        if isinstance(x, (tuple, list)):
            return len(x) == len(y) and all(eq(xi, yi) for xi, yi in zip(x, y))
        if dataclasses.is_dataclass(x):
            key = (id(x), id(y))
            if key in assumed:
                return True
            assumed.add(key)
            return all(eq(getattr(x, f.name), getattr(y, f.name)) for f in dataclasses.fields(x))
        return x == y

    return eq(a, b)


