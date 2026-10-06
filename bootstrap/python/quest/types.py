"""Quest Semantic Types, Kinds, Substitution, and Subtyping."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Union

from quest.diagnostics import (
    Diagnostic,
    DiagnosticRenderer,
    QuestCompilerError,
    TypeRecursionLimitExceeded,
)

# Deterministic safety bounds to prevent infinite recursion during type analysis
MAX_SUBTYPE_FUEL = 10_000
MAX_TYPE_EXPANSION_DEPTH = 500


# ============================================================================
# 1. Kinds (Level 2)
# ============================================================================

class QKind:
    """Base class for all Quest kinds."""

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

class QType:
    """Base class for all semantic Quest types."""

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        """Evaluates type aliases and applications lazily to expose the outermost constructor."""
        return self

    def substitute(self, subst: dict[int, QType]) -> QType:
        """Performs capture-avoiding substitution using symbol_id keys."""
        return self

    def format(self, env: Optional[Any] = None) -> str:
        """Formats this type into a readable string, utilizing env aliases and bounded recursions."""
        return format_type_compact(self, env=env)

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
class QDynamicType(QType):
    def __str__(self) -> str:
        return "Dynamic"


@dataclass(frozen=True)
class QBottomType(QType):
    """Internal bottom type: subtype of all types, used for divergent expressions like raise."""
    def __str__(self) -> str:
        return "Bottom"


@dataclass(frozen=True)
class QExceptionType(QType):
    """Exception type, optionally carrying a payload type (defaults to Ok)."""
    payload_type: QType = field(default_factory=lambda: OK_TYPE)

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self

    def substitute(self, subst: dict[int, QType]) -> QType:
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
DYNAMIC_TYPE = QDynamicType()
BOTTOM_TYPE = QBottomType()
EXCEPTION_TYPE = QExceptionType()


# ============================================================================
# 4. Composite Types (Tuples, Records, Variants, Options)
# ============================================================================

@dataclass(frozen=True)
class QTupleField:
    """A single (optionally named) value component in an ordered tuple type: [name:] T."""
    name: Optional[str]
    type_val: QType
    is_var: bool = False

    def substitute(self, subst: dict[int, QType]) -> QTupleField:
        type_val = self.type_val.substitute(subst)
        return self if type_val is self.type_val else QTupleField(name=self.name, type_val=type_val, is_var=self.is_var)

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ""
        if self.name:
            return f"{var_prefix}{self.name}: {self.type_val}"
        return f"{var_prefix}:{self.type_val}"


@dataclass(frozen=True)
class QTupleTypeFormal:
    """A type formal component in an ordered tuple type: X::K."""
    name: str
    symbol_id: int
    bound: QKind

    def substitute(self, subst: dict[int, QType]) -> QTupleTypeFormal:
        bound = self.bound.substitute_types(subst)
        if bound is self.bound:
            return self
        return QTupleTypeFormal(name=self.name, symbol_id=self.symbol_id, bound=bound)

    def __str__(self) -> str:
        return f"{self.name}::{self.bound}"


@dataclass(frozen=True)
class QTupleTypeBinding:
    """A manifest type definition inside a tuple signature: Let X::K = T."""
    name: str
    type_val: QType
    bound: Optional[QKind] = None

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

    def substitute(self, subst: dict[int, QType]) -> QType:
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
class QRecordField:
    """A single field inside a record type."""
    name: str
    type_val: QType
    is_var: bool = False

    def substitute(self, subst: dict[int, QType]) -> QRecordField:
        type_val = self.type_val.substitute(subst)
        return self if type_val is self.type_val else QRecordField(name=self.name, type_val=type_val, is_var=self.is_var)

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ""
        return f"{var_prefix}{self.name}: {self.type_val}"


@dataclass(frozen=True)
class QRecordType(QType):
    """Unordered record type with structural subtyping: Record [var] x: T ... end."""
    fields: tuple[QRecordField, ...]
    provenance: Optional[str] = field(default=None, compare=False)

    def get_field(self, name: str) -> Optional[QRecordField]:
        for field_entry in self.fields:
            if field_entry.name == name:
                return field_entry
        return None

    def substitute(self, subst: dict[int, QType]) -> QType:
        fields = tuple(f.substitute(subst) for f in self.fields)
        return self if _all_same(fields, self.fields) else QRecordType(fields, provenance=self.provenance)

    def __str__(self) -> str:
        if self.provenance:
            return f"Module '{self.provenance}'"
        fields_str = " ".join(str(f) for f in self.fields)
        return f"Record {fields_str} end" if fields_str else "Record end"


@dataclass(frozen=True)
class QVariantField:
    """A tagged branch inside a variant type."""
    name: str
    type_val: Optional[QType] = None
    is_var: bool = False

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

    def get_variant(self, name: str) -> Optional[QVariantField]:
        for v in self.variants:
            if v.name == name:
                return v
        return None

    def substitute(self, subst: dict[int, QType]) -> QType:
        variants = tuple(v.substitute(subst) for v in self.variants)
        return self if _all_same(variants, self.variants) else QVariantType(variants)

    def __str__(self) -> str:
        variants_str = " ".join(str(v) for v in self.variants)
        return f"Variant {variants_str} end" if variants_str else "Variant end"


@dataclass(frozen=True)
class QOptionField:
    """A tagged case inside an option type."""
    name: str
    payload_type: Optional[QType] = None

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

    def get_option(self, name: str) -> Optional[QOptionField]:
        for opt in self.options:
            if opt.name == name:
                return opt
        return None

    def substitute(self, subst: dict[int, QType]) -> QType:
        options = tuple(o.substitute(subst) for o in self.options)
        return self if _all_same(options, self.options) else QOptionType(options)

    def __str__(self) -> str:
        options_str = " ".join(str(o) for o in self.options)
        return f"Option {options_str} end" if options_str else "Option end"


# ============================================================================
# 5. Functions, References, and Computation Types
# ============================================================================

@dataclass(frozen=True)
class QParam:
    """Formal parameter to a function."""
    name: str
    type_val: QType
    is_var: bool = False
    is_out: bool = False

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

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    def substitute(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QVarType(element_type)

    def __str__(self) -> str:
        return f"Var({self.element_type})"


@dataclass(frozen=True)
class QArrayType(QType):
    """Mutable array type: Array(T)."""
    element_type: QType

    def substitute(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QArrayType(element_type)

    def __str__(self) -> str:
        return f"Array({self.element_type})"


@dataclass(frozen=True)
class QOutType(QType):
    """Write-only output parameter type: Out(T)."""
    element_type: QType

    def substitute(self, subst: dict[int, QType]) -> QType:
        element_type = self.element_type.substitute(subst)
        return self if element_type is self.element_type else QOutType(element_type)

    def __str__(self) -> str:
        return f"Out({self.element_type})"


# ============================================================================
# 6. Polymorphic, Higher-Order, and Parameterized Types
# ============================================================================

@dataclass(frozen=True)
class QQuantifier:
    """Type quantifier in All(X::K) T or All(X <: Bound) T."""
    name: str
    symbol_id: int
    bound: QKind

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

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    def substitute(self, subst: dict[int, QType]) -> QType:
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
        return f"Auto {self.type_param} :: {self.kind_bound} with {sig_str} end"


@dataclass(frozen=True)
class QTypeFormal:
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

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    @property
    def current_symbol_id(self) -> int:
        return self.bindings[self.active_index][1]

    @property
    def current_name(self) -> str:
        return self.bindings[self.active_index][0]

    def siblings(self) -> tuple[QRecGroupType, ...]:
        """One node per binding of this group (self at active_index), shared by all of them."""
        siblings = self.__dict__.get("_siblings")
        if siblings is None:
            siblings = tuple(
                self if idx == self.active_index else QRecGroupType(bindings=self.bindings, active_index=idx)
                for idx in range(len(self.bindings))
            )
            for node in siblings:
                object.__setattr__(node, "_siblings", siblings)
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

    def substitute(self, subst: dict[int, QType]) -> QType:
        bound_ids = {b[1] for b in self.bindings}
        active_subst = {k: v for k, v in subst.items() if k not in bound_ids}
        new_bodies = tuple(b[3].substitute(active_subst) for b in self.bindings)
        if all(nb is b[3] for nb, b in zip(new_bodies, self.bindings)):
            return self
        new_bindings = tuple((b[0], b[1], b[2], nb) for b, nb in zip(self.bindings, new_bodies))
        return QRecGroupType(bindings=new_bindings, active_index=self.active_index)

    def __str__(self) -> str:
        return f"RecGroup({self.current_name})"


@dataclass(frozen=True)
class QTypeVar(QType):
    """Named type variable with unique symbol identity."""
    name: str
    symbol_id: int
    bound: Optional[QKind] = None

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        if env is not None:
            sym = env.lookup_type_by_id(self.symbol_id) if hasattr(env, "lookup_type_by_id") else None
            if sym is not None and sym.definition is not None:
                return sym.definition.evaluate_lazily(env)
        return self

    def substitute(self, subst: dict[int, QType]) -> QType:
        return subst.get(self.symbol_id, self)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class QAbstractType(QType):
    """An abstract type bounded by a kind."""
    name: str
    symbol_id: int
    bound: QKind

    def substitute(self, subst: dict[int, QType]) -> QType:
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

    @property
    def symbol_id(self) -> int:
        return hash((self.root_symbol_id, self.field_name))

    def evaluate_lazily(self, env: Optional[Any] = None) -> QType:
        return self

    def substitute(self, subst: dict[int, QType]) -> QType:
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
        return False

    return visit(typ)


# ============================================================================
# 8. Type Inference Metavariable
# ============================================================================

class QTypeMeta(QType):
    """Mutable type metavariable (?T_1) for local bidirectional unification."""
    _counter: int = 0

    def __init__(self, bound: QKind = TYPE_KIND, name: Optional[str] = None):
        QTypeMeta._counter += 1
        self.symbol_id: int = -QTypeMeta._counter  # Negative IDs for inference metavars
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

    def substitute(self, subst: dict[int, QType]) -> QType:
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
    import dataclasses

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


# ============================================================================
# 9. Equi-Recursive Subtyping and Type Equivalence
# ============================================================================

def is_type_equal(t1: QType, t2: QType, env: Optional[Any] = None) -> bool:
    """Checks equi-recursive type equivalence (t1 <: t2 and t2 <: t1)."""
    return is_subtype(t1, t2, env) and is_subtype(t2, t1, env)


class SubtypeTrail:
    """Coinductive assumptions of one subtyping proof: pairs (sub, sup) currently assumed to hold.

    Named type variables are keyed by symbol and everything else by object identity. The trail keeps
    every keyed object alive for the duration of the proof, so that an id can never be reused by a
    different (temporary) type and match an assumption it was not part of.
    """

    __slots__ = ("_assumed", "_keep_alive")

    def __init__(self) -> None:
        self._assumed: set[tuple[Any, Any]] = set()
        self._keep_alive: list[QType] = []

    @staticmethod
    def key(t: QType) -> tuple[Any, ...]:
        if isinstance(t, (QTypeVar, QAbstractType)):
            return ("var", t.symbol_id)
        if isinstance(t, QPathType):
            return ("path", t.root_symbol_id, t.field_name)
        return ("obj", id(t))

    def pair(self, sub: QType, sup: QType) -> tuple[Any, Any]:
        return (self.key(sub), self.key(sup))

    def __contains__(self, pair: tuple[Any, Any]) -> bool:
        return pair in self._assumed

    def assume(self, pair: tuple[Any, Any], sub: QType, sup: QType) -> None:
        self._assumed.add(pair)
        self._keep_alive.append(sub)
        self._keep_alive.append(sup)


def is_subtype(
    sub: QType,
    sup: QType,
    env: Optional[Any] = None,
    trail: Optional[SubtypeTrail] = None,
    fuel: int = MAX_SUBTYPE_FUEL,
) -> bool:
    """Checks if sub is a subtype of sup (sub <: sup) with coinductive cycle detection and fuel limit."""
    if sub is sup:
        return True

    if fuel <= 0:
        raise TypeRecursionLimitExceeded(
            f"Subtyping proof exceeded step limit of {MAX_SUBTYPE_FUEL} steps "
            f"while checking ({sub} <: {sup})"
        )
    fuel -= 1

    if trail is None:
        trail = SubtypeTrail()

    # 0. Coinductive cycle detection for recursive types before lazy unfolding
    type_pair = trail.pair(sub, sup)
    if type_pair in trail:
        return True
    if isinstance(sub, (QRecType, QRecGroupType)) or isinstance(sup, (QRecType, QRecGroupType)):
        trail.assume(type_pair, sub, sup)

    # 1. Evaluate both types lazily to expose outermost constructors
    sub_lazy = sub.evaluate_lazily(env)
    sup_lazy = sup.evaluate_lazily(env)

    # 2. Reflexivity & identical instances (no Python structural == on QType)
    if sub_lazy is sup_lazy:
        return True
    if (
        isinstance(sub_lazy, (QTypeVar, QAbstractType, QPathType))
        and isinstance(sup_lazy, (QTypeVar, QAbstractType, QPathType))
        and SubtypeTrail.key(sub_lazy) == SubtypeTrail.key(sup_lazy)
    ):
        return True
    if (
        isinstance(sub_lazy, (QIntType, QRealType, QBoolType, QCharType, QStringType, QOkType, QDynamicType))
        and type(sub_lazy) is type(sup_lazy)
    ):
        return True

    # 2b. Bottom type: subtype of all types
    if isinstance(sub_lazy, QBottomType):
        return True

    # 3. Metavariable resolution & unification
    if isinstance(sub_lazy, QTypeMeta):
        pruned = sub_lazy.prune()
        if pruned is not sub_lazy:
            return is_subtype(pruned, sup_lazy, env, trail, fuel)
        sub_lazy.instance = sup_lazy
        return True
    if isinstance(sup_lazy, QTypeMeta):
        pruned = sup_lazy.prune()
        if pruned is not sup_lazy:
            return is_subtype(sub_lazy, pruned, env, trail, fuel)
        sup_lazy.instance = sub_lazy
        return True

    # 4. Top types: in Quest, any proper type is a subtype of itself or upper bounds
    # 5. Coinductive trail check
    pair = trail.pair(sub_lazy, sup_lazy)
    if pair in trail:
        return True
    trail.assume(pair, sub_lazy, sup_lazy)

    # 6. Type Variable bound checking
    if isinstance(sub_lazy, (QTypeVar, QAbstractType, QPathType)):
        if sub_lazy.bound and isinstance(sub_lazy.bound, QPowerKind):
            if is_subtype(sub_lazy.bound.bound, sup_lazy, env, trail, fuel):
                return True

    # 7. Pattern matching across type pairs
    match (sub_lazy, sup_lazy):
        # Tuples: prefix match (Cardelli §7.1, §10.2), matching names, covariant elements / subkinds
        case (QTupleType(fields=sub_fields), QTupleType(fields=sup_fields)):
            if len(sub_fields) < len(sup_fields):
                return False
            curr_sup_fields = list(sup_fields)
            for idx in range(len(curr_sup_fields)):
                s_f = sub_fields[idx]
                t_f = curr_sup_fields[idx]
                if isinstance(s_f, QTupleTypeFormal) and isinstance(t_f, QTupleTypeFormal):
                    if s_f.name != t_f.name or not is_subkind(s_f.bound, t_f.bound, env):
                        return False
                    if t_f.symbol_id != s_f.symbol_id:
                        subst = {t_f.symbol_id: QTypeVar(s_f.name, s_f.symbol_id, s_f.bound)}
                        for rem_idx in range(idx + 1, len(curr_sup_fields)):
                            curr_sup_fields[rem_idx] = curr_sup_fields[rem_idx].substitute(subst)
                elif isinstance(s_f, QTupleTypeBinding) and isinstance(t_f, QTupleTypeFormal):
                    if s_f.name != t_f.name:
                        return False
                    if isinstance(t_f.bound, QPowerKind):
                        if not is_subtype(s_f.type_val, t_f.bound.bound, env, trail, fuel):
                            return False
                    subst = {t_f.symbol_id: s_f.type_val}
                    for rem_idx in range(idx + 1, len(curr_sup_fields)):
                        curr_sup_fields[rem_idx] = curr_sup_fields[rem_idx].substitute(subst)
                elif isinstance(s_f, QTupleField) and isinstance(t_f, QTupleField):
                    if t_f.name is not None and s_f.name != t_f.name:
                        return False
                    if t_f.is_var:
                        if not s_f.is_var:
                            return False
                        if not (is_subtype(s_f.type_val, t_f.type_val, env, trail, fuel)
                                and is_subtype(t_f.type_val, s_f.type_val, env, trail, fuel)):
                            return False
                    else:
                        if not is_subtype(s_f.type_val, t_f.type_val, env, trail, fuel):
                            return False
                elif isinstance(s_f, QTupleTypeBinding) and isinstance(t_f, QTupleTypeBinding):
                    if s_f.name != t_f.name or not is_subtype(s_f.type_val, t_f.type_val, env, trail, fuel):
                        return False
                else:
                    return False
            return True

        # Records: width, depth, and mutable invariance
        case (QRecordType(), QRecordType()):
            for sup_field in sup_lazy.fields:
                sub_field = sub_lazy.get_field(sup_field.name)
                if sub_field is None:
                    return False
                if sup_field.is_var:
                    if not sub_field.is_var:
                        return False
                    if not (is_subtype(sub_field.type_val, sup_field.type_val, env, trail, fuel)
                            and is_subtype(sup_field.type_val, sub_field.type_val, env, trail, fuel)):
                        return False
                else:
                    if not is_subtype(sub_field.type_val, sup_field.type_val, env, trail, fuel):
                        return False
            return True

        # Variants: width and payload covariance
        case (QVariantType(), QVariantType()):
            for sub_var in sub_lazy.variants:
                sup_var = sup_lazy.get_variant(sub_var.name)
                if sup_var is None:
                    return False
                if sub_var.type_val is not None:
                    if sup_var.type_val is None:
                        return False
                    if sub_var.is_var or sup_var.is_var:
                        if not (is_subtype(sub_var.type_val, sup_var.type_val, env, trail, fuel)
                                and is_subtype(sup_var.type_val, sub_var.type_val, env, trail, fuel)):
                            return False
                    else:
                        if not is_subtype(sub_var.type_val, sup_var.type_val, env, trail, fuel):
                            return False
                elif sup_var.type_val is not None:
                    return False
            return True

        # Options: width and payload covariance
        case (QOptionType(), QOptionType()):
            for sub_opt in sub_lazy.options:
                sup_opt = sup_lazy.get_option(sub_opt.name)
                if sup_opt is None:
                    return False
                if sub_opt.payload_type is not None:
                    if sup_opt.payload_type is None:
                        return False
                    if not is_subtype(sub_opt.payload_type, sup_opt.payload_type, env, trail, fuel):
                        return False
                elif sup_opt.payload_type is not None:
                    return False
            return True

        # Functions: contravariant value params, invariant var params, covariant out params and result
        case (QFunType(), QFunType()):
            if len(sub_lazy.params) != len(sup_lazy.params):
                return False
            for s_param, t_param in zip(sub_lazy.params, sup_lazy.params):
                if s_param.is_var or t_param.is_var:
                    if s_param.is_var != t_param.is_var:
                        return False
                    if not (is_subtype(t_param.type_val, s_param.type_val, env, trail, fuel)
                            and is_subtype(s_param.type_val, t_param.type_val, env, trail, fuel)):
                        return False
                elif s_param.is_out or t_param.is_out:
                    if s_param.is_out != t_param.is_out:
                        return False
                    if not is_subtype(s_param.type_val, t_param.type_val, env, trail, fuel):
                        return False
                else:
                    if not is_subtype(t_param.type_val, s_param.type_val, env, trail, fuel):
                        return False
            return is_subtype(sub_lazy.result_type, sup_lazy.result_type, env, trail, fuel)

        # References (Var) & Arrays: invariant element type
        case (QVarType(element_type=s_elem), QVarType(element_type=t_elem)) | \
             (QArrayType(element_type=s_elem), QArrayType(element_type=t_elem)):
            if s_elem is t_elem:
                return True
            return (is_subtype(s_elem, t_elem, env, trail, fuel)
                    and is_subtype(t_elem, s_elem, env, trail, fuel))

        # Out parameters: contravariant
        case (QOutType(element_type=s_elem), QOutType(element_type=t_elem)):
            if s_elem is t_elem:
                return True
            return is_subtype(t_elem, s_elem, env, trail, fuel)

        # Exceptions: invariant payload type
        case (QExceptionType(payload_type=s_pay), QExceptionType(payload_type=t_pay)):
            if s_pay is t_pay:
                return True
            return (is_subtype(s_pay, t_pay, env, trail, fuel)
                    and is_subtype(t_pay, s_pay, env, trail, fuel))

        # Universal Quantifiers (Kernel F<:): bounds match, body covariant
        case (QAllType(), QAllType()):
            if len(sub_lazy.quantifiers) != len(sup_lazy.quantifiers):
                return False
            subst = {
                t_quant.symbol_id: QTypeVar(s_quant.name, s_quant.symbol_id, s_quant.bound)
                for s_quant, t_quant in zip(sub_lazy.quantifiers, sup_lazy.quantifiers)
            }
            for s_q, t_q in zip(sub_lazy.quantifiers, sup_lazy.quantifiers):
                t_bound_renamed = t_q.bound.substitute_types(subst)
                if not is_kind_equal(s_q.bound, t_bound_renamed, env):
                    return False
            return is_subtype(sub_lazy.body, sup_lazy.body.substitute(subst), env, trail, fuel)

        # Type Functions (Type Operators): parameter kinds match, bodies subtype under substitution
        case (QTypeFun(), QTypeFun()):
            if len(sub_lazy.params) != len(sup_lazy.params):
                return False
            subst = {
                t_p.symbol_id: QTypeVar(s_p.name, s_p.symbol_id, s_p.bound)
                for s_p, t_p in zip(sub_lazy.params, sup_lazy.params)
            }
            for s_p, t_p in zip(sub_lazy.params, sup_lazy.params):
                t_bound_renamed = t_p.bound.substitute_types(subst)
                if not is_kind_equal(s_p.bound, t_bound_renamed, env):
                    return False
            return is_subtype(sub_lazy.body, sup_lazy.body.substitute(subst), env, trail, fuel)

        # Type operator application (e.g. List.T(A))
        case (
            QTypeApp(constructor=s_c, arguments=s_args),
            QTypeApp(constructor=t_c, arguments=t_args),
        ):
            if len(s_args) != len(t_args) or not is_type_equal(s_c, t_c, env):
                return False
            for sa, ta in zip(s_args, t_args):
                if sa is ta:
                    continue
                if not (is_subtype(sa, ta, env, trail, fuel) and is_subtype(ta, sa, env, trail, fuel)):
                    return False
            return True

        # External Types: structural equality on underlying C type
        case (QExternalType(c_type=sub_c), QExternalType(c_type=sup_c)):
            return sub_c.strip() == sup_c.strip()

        case _:
            return False


def is_kind_equal(k1: QKind, k2: QKind, env: Optional[Any] = None) -> bool:
    """Checks if two kinds are equivalent (k1 <= k2 and k2 <= k1)."""
    return is_subkind(k1, k2, env) and is_subkind(k2, k1, env)


def is_subkind(sub: QKind, sup: QKind, env: Optional[Any] = None) -> bool:
    """Checks if sub is a subkind of sup (sub <= sup) with Full Subkinding on Kinds."""
    sub_lazy = sub.evaluate_lazily(env)
    sup_lazy = sup.evaluate_lazily(env)

    # 1. Reflexivity
    if sub_lazy is sup_lazy:
        return True

    # 2. Binary pattern matching
    match (sub_lazy, sup_lazy):
        # Power Kind to TYPE: POWER(T) <= TYPE
        case (QPowerKind(), QTypeKind()):
            return True

        # Power to Power: POWER(S) <= POWER(T) iff S <: T
        case (QPowerKind(bound=s_bound), QPowerKind(bound=t_bound)):
            return is_subtype(s_bound, t_bound, env)

        # Higher-Order Operator Kinds (Full Subkinding on Kinds):
        # ALL(X :: K1) K2 <= ALL(Y :: K1') K2' iff K1' <= K1 and K2 <= K2'[Y -> X]
        case (QAllKind(), QAllKind()):
            if not is_subkind(sup_lazy.param_kind, sub_lazy.param_kind, env):
                return False
            renamed_sup_res = sup_lazy.result_kind.substitute_types({
                sup_lazy.param_id: QTypeVar(sub_lazy.param_name, sup_lazy.param_id)
            }).substitute_kinds({
                sup_lazy.param_id: QKindVar(sub_lazy.param_name, sub_lazy.param_id)
            })
            return is_subkind(sub_lazy.result_kind, renamed_sup_res, env)

        case _:
            return False


# ============================================================================
# 10. Kind Synthesis, Checking, and Well-Kindedness
# ============================================================================

class KindError(QuestCompilerError):
    """Raised when kind synthesis, kind checking, or well-kindedness verification fails."""

    def __init__(
        self,
        message: str,
        offset: int = 0,
        help_text: Optional[str] = None,
        notes: Optional[list[str]] = None,
        length: int = 1,
    ) -> None:
        super().__init__(message=message, offset=offset, length=length)
        self.help_text = help_text
        self.notes = notes or []

    def to_diagnostic(self, length: int = 1) -> Diagnostic:
        """Converts this error into a structured Diagnostic object."""
        return Diagnostic.make_error(
            message=self.message,
            offset=self.offset,
            length=length,
            help_text=self.help_text,
            notes=self.notes,
        )

    def format_with_source(self, source_map: Any, length: int = 1) -> str:
        """Renders a diagnostic message with underlined source context."""
        return DiagnosticRenderer.render_diagnostic(self.to_diagnostic(length), source_map)


def check_kind_well_formed(kind: QKind, env: Optional[Any] = None) -> None:
    """Verifies that a kind is well-formed according to Quest kind formation rules."""
    kind_lazy = kind.evaluate_lazily(env)
    match kind_lazy:
        case QTypeKind():
            return

        case QPowerKind(bound=bound):
            # Bound of a power kind MUST be a proper type of kind TYPE
            check_kind(bound, TYPE_KIND, env)
            return

        case QOperatorKind(param_name=pname, param_kind=pkind, result_kind=rkind):
            check_kind_well_formed(pkind, env)
            check_kind_well_formed(rkind, env)
            return

        case QAllKind(
            param_name=param_name,
            param_id=param_id,
            param_kind=param_kind,
            result_kind=result_kind,
        ):
            check_kind_well_formed(param_kind, env)
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope(f"kind_param_{param_name}")
                try:
                    env.current_scope.declare_type(
                        TypeSymbol(
                            name=param_name,
                            symbol_id=param_id,
                            kind=param_kind,
                        )
                    )
                    check_kind_well_formed(result_kind, env)
                finally:
                    env.pop_scope()
            else:
                check_kind_well_formed(result_kind, env)
            return

        case QKindVar(name=name, symbol_id=symbol_id):
            if env is not None and hasattr(env, "lookup_kind_by_id"):
                sym = env.lookup_kind_by_id(symbol_id)
                if sym is None:
                    sym = env.lookup_kind(name)
                if sym is None:
                    raise KindError(f"Unbound kind variable '{name}' (#{symbol_id})")
            return

        case _:
            raise KindError(f"Malformed or unsupported kind '{kind_lazy}'")


# ============================================================================
# 11. Recursive Type Contractiveness Verification (C \succ X)
# ============================================================================

def is_type_contractive(
    qtype: QType,
    recursive_var_ids: set[int],
    env: Optional[Any] = None,
    seen_aliases: Optional[set[int]] = None,
    depth: int = 0,
) -> bool:
    """Verifies that `qtype` is contractive in all variable IDs in `recursive_var_ids` (C \\succ X).

    According to Cardelli & Longo (1991, Section 2.4/2.9) and MacQueen, Plotkin & Sethi (1986):
    - Primitive types (Int, Bool, Top, etc.) are contractive in all X.
    - Type variable Y is contractive in X iff Y != X.
    - Type constructors (Record, Tuple, Option, Variant, Fun, Array, Var, Out) are contractive in X.
    - Universal quantifier All(X':K)B is contractive in X iff X not free in K and B \\succ X.
    - Type application (λ(X':K)B)(A) is contractive in X iff the beta-reduced body \\succ X.
    - Recursive type Rec(X')B is contractive in X iff B \\succ X' and B \\succ X.
    """
    if depth > MAX_TYPE_EXPANSION_DEPTH:
        raise TypeRecursionLimitExceeded(
            f"Type contractiveness check exceeded recursion depth of {MAX_TYPE_EXPANSION_DEPTH}"
        )
    seen = seen_aliases or set()
    qtype_lazy = qtype.evaluate_lazily(env)

    match qtype_lazy:
        case QTypeVar(symbol_id=sym_id):
            if sym_id in recursive_var_ids:
                return False
            if env is not None and hasattr(env, "lookup_type_by_id"):
                sym = env.lookup_type_by_id(sym_id)
                if sym is not None and sym.definition is not None and sym_id not in seen:
                    return is_type_contractive(sym.definition, recursive_var_ids, env, seen | {sym_id}, depth + 1)
            return True

        case QTypeMeta(name=mname):
            if mname == "Top":
                return True
            if env is not None and hasattr(env, "lookup_type"):
                sym = env.lookup_type(mname)
                if sym is not None and sym.definition is not None and sym.symbol_id not in seen:
                    return is_type_contractive(
                        sym.definition, recursive_var_ids, env, seen | {sym.symbol_id}, depth + 1
                    )
            return True

        case QRecType(symbol_id=inner_id, body=inner_body):
            return (
                is_type_contractive(inner_body, {inner_id}, env, seen, depth + 1)
                and is_type_contractive(inner_body, recursive_var_ids, env, seen, depth + 1)
            )

        case QRecGroupType(bindings=bindings, active_index=active_idx):
            all_group_ids = {b[1] for b in bindings}
            active_body = bindings[active_idx][3]
            return is_type_contractive(active_body, recursive_var_ids | all_group_ids, env, seen, depth + 1)

        case QAllType(quantifiers=quants, body=body):
            return is_type_contractive(body, recursive_var_ids, env, seen, depth + 1)

        case QTypeApp(constructor=ctor, arguments=args):
            ctor_lazy = ctor.evaluate_lazily(env)
            match ctor_lazy:
                case QTypeAbs(symbol_id=param_sym, body=body):
                    subst = {param_sym: args[0]} if args else {}
                    reduced = body.substitute_types(subst)
                    return is_type_contractive(reduced, recursive_var_ids, env, seen, depth + 1)
                case _:
                    return is_type_contractive(ctor_lazy, recursive_var_ids, env, seen, depth + 1)

        case (
            QRecordType()
            | QTupleType()
            | QOptionType()
            | QVariantType()
            | QFunType()
            | QArrayType()
            | QVarType()
            | QOutType()
        ):
            # Guarded by constructor
            return True

        case (
            QOkType()
            | QBoolType()
            | QCharType()
            | QStringType()
            | QIntType()
            | QRealType()
            | QExceptionType()
            | QDynamicType()
            | QBottomType()
        ):
            return True

        case _:
            return True


def check_type_contractive(
    qtype: QType,
    recursive_var_ids: set[int],
    var_name: str,
    offset: int = 0,
    env: Optional[Any] = None,
) -> None:
    """Validates that `qtype` is contractive in `recursive_var_ids`, raising KindError if not."""
    if not is_type_contractive(qtype, recursive_var_ids, env):
        raise KindError(
            f"Recursive type '{var_name}' is not contractive; "
            "recursive type variable must be guarded by a constructor",
            offset=offset,
            help_text=(
                "ensure recursive variable appears inside a record, tuple, function, "
                "option, variant, or array type"
            ),
            notes=[
                f"definition of '{var_name}' refers directly to itself as a bare alias without a guarding constructor"
            ],
        )


def check_kind(type_val: QType, expected_kind: QKind, env: Optional[Any] = None) -> None:
    """Checks that type_val has a kind that is a subkind of expected_kind."""
    expected_lazy = expected_kind.evaluate_lazily(env)
    if isinstance(expected_lazy, QPowerKind):
        if is_subtype(type_val, expected_lazy.bound, env):
            return
        raise KindError(
            f"Kind mismatch: type '{type_val}' is not a subtype of bound '{expected_lazy.bound}'"
        )
    synthesized = synth_kind(type_val, env)
    if not is_subkind(synthesized, expected_lazy, env):
        raise KindError(
            f"Kind mismatch: type '{type_val}' has kind '{synthesized}', "
            f"which is not a subkind of expected kind '{expected_kind}'"
        )


# Kinds synthesized during the current top-level kind check, keyed by node identity. Elaborated types
# are DAGs (aliases are shared), so without this every shared subterm is re-checked on every path to it.
_kind_memo: Optional[dict[int, tuple[QType, QKind]]] = None
_kind_memo_env: Optional[Any] = None


def synth_kind(type_val: QType, env: Optional[Any] = None) -> QKind:
    """Synthesizes the most specific minimal kind K for type_val in the given environment.

    Results are memoized for the duration of the outermost call. That is sound because a node's kind
    depends only on the node and the binders in scope, which have unique symbol ids, so a shared node
    has the same kind wherever it occurs. Metavariables are not memoized (their kind follows their
    solution), and a nested call with a different environment bypasses the memo.
    """
    global _kind_memo, _kind_memo_env
    if isinstance(type_val, QTypeMeta):
        return _synth_kind_uncached(type_val, env)
    if _kind_memo is not None:
        if env is not _kind_memo_env:
            return _synth_kind_uncached(type_val, env)
        hit = _kind_memo.get(id(type_val))
        if hit is not None and hit[0] is type_val:
            return hit[1]
        kind = _synth_kind_uncached(type_val, env)
        _kind_memo[id(type_val)] = (type_val, kind)
        return kind

    _kind_memo, _kind_memo_env = {}, env
    try:
        kind = _synth_kind_uncached(type_val, env)
    finally:
        _kind_memo, _kind_memo_env = None, None
    return kind


def _synth_kind_uncached(type_val: QType, env: Optional[Any] = None) -> QKind:
    """Synthesizes the kind of type_val; recursive checks go through the memoizing synth_kind."""
    match type_val:
        case (QIntType() | QRealType() | QBoolType() | QCharType() | QStringType()
              | QOkType() | QDynamicType() | QExceptionType() | QExternalType()):
            return TYPE_KIND

        case QTupleType(fields=fields):
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope("tuple_kind_check")
                try:
                    for f in fields:
                        if isinstance(f, QTupleTypeFormal):
                            check_kind_well_formed(f.bound, env)
                            env.current_scope.declare_type(
                                TypeSymbol(name=f.name, symbol_id=f.symbol_id, kind=f.bound)
                            )
                        elif isinstance(f, QTupleField):
                            check_kind(f.type_val, TYPE_KIND, env)
                        elif isinstance(f, QTupleTypeBinding):
                            check_kind(f.type_val, TYPE_KIND, env)
                            env.current_scope.declare_type(
                                TypeSymbol(
                                    name=f.name,
                                    symbol_id=env.fresh_symbol_id(),
                                    kind=f.bound or TYPE_KIND,
                                    definition=f.type_val,
                                )
                            )
                finally:
                    env.pop_scope()
            else:
                for f in fields:
                    if isinstance(f, QTupleTypeFormal):
                        check_kind_well_formed(f.bound, env)
                    elif isinstance(f, (QTupleField, QTupleTypeBinding)):
                        check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QRecordType(fields=fields):
            for f in fields:
                check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QVariantType(variants=variants):
            for v in variants:
                if v.type_val is not None:
                    check_kind(v.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QOptionType(options=options):
            for opt in options:
                if opt.payload_type is not None:
                    check_kind(opt.payload_type, TYPE_KIND, env)
            return TYPE_KIND

        case QFunType(params=params, result_type=res_type):
            for param in params:
                check_kind(param.type_val, TYPE_KIND, env)
            check_kind(res_type, TYPE_KIND, env)
            return TYPE_KIND

        case QVarType(element_type=elem) | QArrayType(element_type=elem) | QOutType(element_type=elem):
            check_kind(elem, TYPE_KIND, env)
            return TYPE_KIND

        case QTypeVar(name=name, symbol_id=sym_id, bound=bound):
            if bound is not None:
                return bound
            if env is not None and hasattr(env, "lookup_type_by_id"):
                sym = env.lookup_type_by_id(sym_id)
                if sym is None:
                    sym = env.lookup_type(name)
                if sym is not None:
                    return sym.kind
            raise KindError(f"Unbound type variable '{name}' (#{sym_id})")

        case QAbstractType(bound=bound) | QPathType(bound=bound):
            check_kind_well_formed(bound, env)
            return bound

        case QTypeMeta():
            pruned = type_val.prune()
            if pruned is not type_val:
                return synth_kind(pruned, env)
            return type_val.bound

        case QAllType(quantifiers=quants, body=body):
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope("all_type")
                try:
                    for q in quants:
                        check_kind_well_formed(q.bound, env)
                        env.current_scope.declare_type(
                            TypeSymbol(name=q.name, symbol_id=q.symbol_id, kind=q.bound)
                        )
                    check_kind(body, TYPE_KIND, env)
                finally:
                    env.pop_scope()
            else:
                for q in quants:
                    check_kind_well_formed(q.bound, env)
                check_kind(body, TYPE_KIND, env)
            return TYPE_KIND

        case QAutoType(type_param=param_name, symbol_id=sym_id, kind_bound=kbound, signature=sig):
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope("auto_type")
                try:
                    check_kind_well_formed(kbound, env)
                    env.current_scope.declare_type(
                        TypeSymbol(name=param_name, symbol_id=sym_id, kind=kbound)
                    )
                    for f in sig:
                        check_kind(f.type_val, TYPE_KIND, env)
                finally:
                    env.pop_scope()
            else:
                check_kind_well_formed(kbound, env)
                for f in sig:
                    check_kind(f.type_val, TYPE_KIND, env)
            return TYPE_KIND

        case QRecType(var_name=vname, symbol_id=sym_id, bound=bound, body=body):
            check_kind_well_formed(bound, env)
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope(f"rec_{vname}")
                try:
                    env.current_scope.declare_type(
                        TypeSymbol(name=vname, symbol_id=sym_id, kind=bound)
                    )
                    check_kind(body, bound, env)
                finally:
                    env.pop_scope()
            else:
                check_kind(body, bound, env)
            return bound

        case QRecGroupType(bindings=bindings, active_index=idx):
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope("rec_group")
                try:
                    for b_name, b_id, b_kind, _ in bindings:
                        check_kind_well_formed(b_kind, env)
                        env.current_scope.declare_type(
                            TypeSymbol(name=b_name, symbol_id=b_id, kind=b_kind)
                        )
                    for _, _, b_kind, b_body in bindings:
                        check_kind(b_body, b_kind, env)
                finally:
                    env.pop_scope()
            return bindings[idx][2]

        case QTypeFun(params=formals, body=body):
            if env is not None and hasattr(env, "push_scope"):
                from quest.env import TypeSymbol
                env.push_scope("type_fun")
                try:
                    for formal in formals:
                        check_kind_well_formed(formal.bound, env)
                        env.current_scope.declare_type(
                            TypeSymbol(name=formal.name, symbol_id=formal.symbol_id, kind=formal.bound)
                        )
                    body_kind = synth_kind(body, env)
                finally:
                    env.pop_scope()
            else:
                for formal in formals:
                    check_kind_well_formed(formal.bound, env)
                body_kind = synth_kind(body, env)

            result_kind = body_kind
            for formal in reversed(formals):
                result_kind = QAllKind(
                    param_name=formal.name,
                    param_id=formal.symbol_id,
                    param_kind=formal.bound,
                    result_kind=result_kind,
                )
            return result_kind

        case QTypeApp(constructor=ctor, arguments=args):
            ctor_kind = synth_kind(ctor, env).evaluate_lazily(env)
            for arg in args:
                if not isinstance(ctor_kind, QAllKind):
                    raise KindError(
                        f"Type application error: constructor '{ctor}' "
                        f"has non-operator kind '{ctor_kind}'"
                    )
                check_kind(arg, ctor_kind.param_kind, env)
                ctor_kind = ctor_kind.result_kind.substitute_types({
                    ctor_kind.param_id: arg
                }).evaluate_lazily(env)
            return ctor_kind

        case _:
            raise KindError(f"Cannot synthesize kind for unknown type node '{type_val}'")


# ============================================================================
# 11. Canonical S-Expression Pretty Printer (qtype_dump)
# ============================================================================

def qtype_dump(item: Union[QType, QKind], indent: int = 0) -> str:
    """Formats a QType or QKind into a canonical 2-space indented S-expression string."""
    pad = "  " * indent
    match item:
        case (QIntType() | QRealType() | QBoolType() | QCharType() | QStringType()
              | QOkType() | QDynamicType() | QExceptionType() | QTypeKind()):
            return f"({item.__class__.__name__})"

        case QPowerKind(bound=bound):
            return f"({item.__class__.__name__}\n{pad}  :bound {qtype_dump(bound, indent + 1)})"

        case QAllKind(param_name=pname, param_kind=pkind, result_kind=rkind):
            return (
                f"({item.__class__.__name__}\n"
                f"{pad}  :param '{pname}'\n"
                f"{pad}  :param_kind {qtype_dump(pkind, indent + 1)}\n"
                f"{pad}  :result_kind {qtype_dump(rkind, indent + 1)})"
            )

        case QTypeVar(name=name, symbol_id=sym_id) | QAbstractType(name=name, symbol_id=sym_id) \
             | QKindVar(name=name, symbol_id=sym_id):
            return f"({item.__class__.__name__} '{name}' #{sym_id})"

        case QPathType(root_name=rname, root_symbol_id=rsym_id, field_name=fname):
            return f"(QPathType '{rname}.{fname}' #{rsym_id})"

        case QTupleType(fields=fields):
            if not fields:
                return "(QTupleType)"
            field_strs = []
            for f in fields:
                if isinstance(f, QTupleTypeFormal):
                    field_strs.append(
                        f"{pad}    (QTupleTypeFormal '{f.name}' #{f.symbol_id} :: {f.bound})"
                    )
                elif isinstance(f, QTupleField):
                    field_strs.append(
                        f"{pad}    (QTupleField {f.name or ''}{' :var' if f.is_var else ''} "
                        f"{qtype_dump(f.type_val, indent + 2)})"
                    )
                elif isinstance(f, QTupleTypeBinding):
                    field_strs.append(
                        f"{pad}    (QTupleTypeBinding '{f.name}' = {qtype_dump(f.type_val, indent + 2)})"
                    )
            f_joined = "\n".join(field_strs)
            return f"(QTupleType\n{pad}  :fields (\n{f_joined}\n{pad}  ))"

        case QRecordType(fields=fields):
            if not fields:
                return "(QRecordType)"
            field_strs = "\n".join(
                f"{pad}    (QRecordField '{f.name}'{ ' :var' if f.is_var else '' } "
                f"{qtype_dump(f.type_val, indent + 2)})"
                for f in fields
            )
            return f"(QRecordType\n{pad}  :fields (\n{field_strs}\n{pad}  ))"

        case QVariantType(variants=variants):
            if not variants:
                return "(QVariantType)"
            var_strs = "\n".join(
                f"{pad}    (QVariantField '{v.name}'"
                + (f" {qtype_dump(v.type_val, indent + 2)}" if v.type_val else "")
                + ")"
                for v in variants
            )
            return f"(QVariantType\n{pad}  :variants (\n{var_strs}\n{pad}  ))"

        case QOptionType(options=options):
            if not options:
                return "(QOptionType)"
            opt_strs = "\n".join(
                f"{pad}    (QOptionField '{o.name}'"
                + (f" {qtype_dump(o.payload_type, indent + 2)}" if o.payload_type else "")
                + ")"
                for o in options
            )
            return f"(QOptionType\n{pad}  :options (\n{opt_strs}\n{pad}  ))"

        case QFunType(params=params, result_type=res_type):
            param_strs = "\n".join(
                f"{pad}    (QParam '{p.name}'{ ' :var' if p.is_var else '' }{ ' :out' if p.is_out else '' } "
                f"{qtype_dump(p.type_val, indent + 2)})"
                for p in params
            )
            return (
                f"(QFunType\n"
                f"{pad}  :params (\n{param_strs}\n{pad}  )\n"
                f"{pad}  :result {qtype_dump(res_type, indent + 1)})"
            )

        case QVarType(element_type=elem) | QArrayType(element_type=elem) | QOutType(element_type=elem):
            return f"({item.__class__.__name__}\n{pad}  :element {qtype_dump(elem, indent + 1)})"

        case QAllType(quantifiers=quants, body=body):
            quant_strs = "\n".join(
                f"{pad}    (QQuantifier '{q.name}' #{q.symbol_id} {qtype_dump(q.bound, indent + 2)})"
                for q in quants
            )
            return (
                f"(QAllType\n"
                f"{pad}  :quantifiers (\n{quant_strs}\n{pad}  )\n"
                f"{pad}  :body {qtype_dump(body, indent + 1)})"
            )

        case QTypeApp(constructor=ctor, arguments=args):
            arg_strs = "\n".join(f"{pad}    {qtype_dump(arg, indent + 2)}" for arg in args)
            return (
                f"(QTypeApp\n"
                f"{pad}  :constructor {qtype_dump(ctor, indent + 1)}\n"
                f"{pad}  :arguments (\n{arg_strs}\n{pad}  ))"
            )

        case QRecType(var_name=vname, symbol_id=sym_id, bound=bound, body=body):
            return (
                f"(QRecType '{vname}' #{sym_id}\n"
                f"{pad}  :bound {qtype_dump(bound, indent + 1)}\n"
                f"{pad}  :body {qtype_dump(body, indent + 1)})"
            )

        case QRecGroupType(bindings=bindings):
            b_strs = "\n".join(
                f"{pad}    (Binding '{b[0]}' #{b[1]} {qtype_dump(b[2], indent + 2)} {qtype_dump(b[3], indent + 2)})"
                for b in bindings
            )
            return f"(QRecGroupType\n{pad}  :bindings (\n{b_strs}\n{pad}  ))"

        case _:
            return f"({item.__class__.__name__})"


# ============================================================================
# Operator Signatures (Cardelli §4.2)
# ============================================================================

# Operator signature table for non-overloaded Quest infix operators:
# Maps operator symbol -> (expected_left_type, expected_right_type, result_type)
INFIX_OPERATORS: dict[str, tuple[QType, QType, QType]] = {
    # Integer arithmetic
    "+": (INT_TYPE, INT_TYPE, INT_TYPE),
    "-": (INT_TYPE, INT_TYPE, INT_TYPE),
    "*": (INT_TYPE, INT_TYPE, INT_TYPE),
    "/": (INT_TYPE, INT_TYPE, INT_TYPE),
    "%": (INT_TYPE, INT_TYPE, INT_TYPE),
    "mod": (INT_TYPE, INT_TYPE, INT_TYPE),
    # Integer relational
    "<": (INT_TYPE, INT_TYPE, BOOL_TYPE),
    "<=": (INT_TYPE, INT_TYPE, BOOL_TYPE),
    ">": (INT_TYPE, INT_TYPE, BOOL_TYPE),
    ">=": (INT_TYPE, INT_TYPE, BOOL_TYPE),
    # Real arithmetic (doubled)
    "++": (REAL_TYPE, REAL_TYPE, REAL_TYPE),
    "--": (REAL_TYPE, REAL_TYPE, REAL_TYPE),
    "**": (REAL_TYPE, REAL_TYPE, REAL_TYPE),
    "//": (REAL_TYPE, REAL_TYPE, REAL_TYPE),
    "^^": (REAL_TYPE, REAL_TYPE, REAL_TYPE),
    # Real relational (doubled)
    "<<": (REAL_TYPE, REAL_TYPE, BOOL_TYPE),
    "<<=": (REAL_TYPE, REAL_TYPE, BOOL_TYPE),
    ">>": (REAL_TYPE, REAL_TYPE, BOOL_TYPE),
    ">>=": (REAL_TYPE, REAL_TYPE, BOOL_TYPE),
    # String concatenation
    "<>": (STRING_TYPE, STRING_TYPE, STRING_TYPE),
    # Boolean eager operations
    "/\\": (BOOL_TYPE, BOOL_TYPE, BOOL_TYPE),
    "\\/": (BOOL_TYPE, BOOL_TYPE, BOOL_TYPE),
}


def resolve_record_bound(t: QType, env: Optional[Any] = None) -> Optional[QRecordType]:
    """Resolves upper bound for a type variable or path type if bounded by a record type."""
    curr = t
    visited = set()
    while True:
        curr_lazy = curr.evaluate_lazily(env) if env is not None else curr
        if isinstance(curr_lazy, QRecordType):
            return curr_lazy
        if (
            isinstance(curr_lazy, (QTypeVar, QAbstractType, QPathType))
            and isinstance(curr_lazy.bound, QPowerKind)
        ):
            sym_id = getattr(curr_lazy, "symbol_id", id(curr_lazy))
            if sym_id in visited:
                return None
            visited.add(sym_id)
            curr = curr_lazy.bound.bound
        else:
            return None


def resolve_variant_bound(t: QType, env: Optional[Any] = None) -> Optional[QVariantType]:
    """Resolves upper bound for a type variable or path type if bounded by a variant type."""
    curr = t
    visited = set()
    while True:
        curr_lazy = curr.evaluate_lazily(env) if env is not None else curr
        if isinstance(curr_lazy, QVariantType):
            return curr_lazy
        if (
            isinstance(curr_lazy, (QTypeVar, QAbstractType, QPathType))
            and isinstance(curr_lazy.bound, QPowerKind)
        ):
            sym_id = getattr(curr_lazy, "symbol_id", id(curr_lazy))
            if sym_id in visited:
                return None
            visited.add(sym_id)
            curr = curr_lazy.bound.bound
        else:
            return None


def resolve_option_bound(t: QType, env: Optional[Any] = None) -> Optional[QOptionType]:
    """Resolves an option type, unwrapping type applications, recursive types, or bounds."""
    curr = t
    visited = set()
    while True:
        if isinstance(curr, QOptionType):
            return curr
        if isinstance(curr, QRecType):
            curr = curr.body
            continue
        if isinstance(curr, QTypeApp):
            ctor = curr.constructor
            if env is not None and isinstance(ctor, (QTypeVar, QAbstractType, QPathType)):
                ctor = ctor.evaluate_lazily(env)
            if isinstance(ctor, QTypeFun):
                subst = {p.symbol_id: arg for p, arg in zip(ctor.params, curr.arguments)}
                curr = ctor.body.substitute(subst)
                continue
            elif env is not None:
                curr_lazy = curr.evaluate_lazily(env)
                if not isinstance(curr_lazy, QTypeApp):
                    curr = curr_lazy
                    continue
        if (
            isinstance(curr, (QTypeVar, QAbstractType, QPathType))
            and isinstance(curr.bound, QPowerKind)
        ):
            sym_id = getattr(curr, "symbol_id", id(curr))
            if sym_id in visited:
                return None
            visited.add(sym_id)
            curr = curr.bound.bound
            continue
        if env is not None:
            curr_lazy = curr.evaluate_lazily(env)
            if curr_lazy is not curr and type(curr_lazy) is not type(curr):
                curr = curr_lazy
                continue
        return None


def format_type_compact(
    t: Union[QType, QKind, None],
    env: Optional[Any] = None,
    visited_ids: Optional[set[int]] = None,
    depth: int = 0,
) -> str:
    """Formats a QType or QKind into a compact, human-readable string with alias awareness and bounded recursion."""
    if t is None:
        return ""
    if visited_ids is None:
        visited_ids = set()

    # 1. Alias lookup from environment (Option B: Name/Alias priority)
    # Check if this type object or its symbol corresponds to a declared type alias in env or an imported interface
    if env is not None and isinstance(t, QType):
        alias_name = getattr(env, "lookup_alias_for_type", None)
        if callable(alias_name):
            found_alias = alias_name(t)
            if found_alias:
                return found_alias
        # Check if t matches an interface type symbol
        interfaces = getattr(env, "_interfaces", None)
        if isinstance(interfaces, dict):
            # Prioritize clean, short interface names (e.g. 'Ast' over full paths)
            for iface_name, iface_scope in interfaces.items():
                if "/" in iface_name:
                    continue
                types_dict = getattr(iface_scope, "types", None)
                if isinstance(types_dict, dict):
                    for name, sym in types_dict.items():
                        if sym.definition is not None and sym.definition is t:
                            return f"{iface_name}.{name}"

    # 2. Primitives and Singletons
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
    if t is DYNAMIC_TYPE:
        return "Dynamic"
    if t is BOTTOM_TYPE:
        return "Bottom"
    if t is EXCEPTION_TYPE:
        return "Exception"
    if t is TYPE_KIND:
        return "TYPE"

    # 3. Kinds
    if isinstance(t, QPowerKind):
        return f"POWER({format_type_compact(t.bound, env, visited_ids, depth)})"
    if isinstance(t, QAllKind):
        p_str = format_type_compact(t.param_kind, env, visited_ids, depth)
        r_str = format_type_compact(t.result_kind, env, visited_ids, depth)
        return f"All({t.param_name} :: {p_str}) {r_str}"

    # 4. Symbol identifiers and paths
    if isinstance(t, (QTypeVar, QAbstractType)):
        return t.name
    if isinstance(t, QPathType):
        return f"{t.root_name}.{t.field_name}"
    if isinstance(t, QExternalType):
        return t.name if t.name else f'external "{t.c_type}"'

    # 5. Type constructor containers
    if isinstance(t, QArrayType):
        return f"Array({format_type_compact(t.element_type, env, visited_ids, depth)})"
    if isinstance(t, QVarType):
        return f"Var({format_type_compact(t.element_type, env, visited_ids, depth)})"
    if isinstance(t, QOutType):
        return f"Out({format_type_compact(t.element_type, env, visited_ids, depth)})"

    # 6. Type Application
    if isinstance(t, QTypeApp):
        ctor_str = format_type_compact(t.constructor, env, visited_ids, depth)
        args_str = " ".join(format_type_compact(arg, env, visited_ids, depth) for arg in t.arguments)
        return f"{ctor_str}({args_str})" if args_str else f"{ctor_str}()"

    # 7. Type-level Functions
    if isinstance(t, QTypeFun):
        if depth > 2:
            return "Fun(...)"
        params_str = " ".join(
            f"{p.name} :: {format_type_compact(p.bound, env, visited_ids, depth + 1)}"
            for p in t.params
        )
        body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
        return f"Fun({params_str}) {body_str}"

    # 8. Function Type
    if isinstance(t, QFunType):
        if depth > 3:
            return "Fun(...)"
        p_items = []
        for p in t.params:
            prefix = "var " if p.is_var else ("out " if p.is_out else "")
            t_s = format_type_compact(p.type_val, env, visited_ids, depth + 1)
            p_items.append(f"{prefix}{p.name}: {t_s}" if p.name else t_s)
        params_str = " ".join(p_items)
        res_str = format_type_compact(t.result_type, env, visited_ids, depth + 1)
        return f"Fun({params_str}): {res_str}"

    # 9. All Quantifier Type
    if isinstance(t, QAllType):
        if depth > 3:
            return "All(...) ..."
        quants_str = " ".join(str(q) for q in t.quantifiers)
        body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
        return f"All({quants_str}) {body_str}"

    # 10. Records (Module check first)
    if isinstance(t, QRecordType):
        if t.provenance:
            return f"Module '{t.provenance}'"
        if depth > 3:
            return "Record ... end"
        f_strs = " ".join(
            f"{'var ' if f.is_var else ''}{f.name}: {format_type_compact(f.type_val, env, visited_ids, depth + 1)}"
            for f in t.fields
        )
        return f"Record {f_strs} end" if f_strs else "Record end"

    # 11. Tuples
    if isinstance(t, QTupleType):
        if depth > 3:
            return "Tuple ... end"
        f_parts: list[str] = []
        for f in t.fields:
            if isinstance(f, QTupleField):
                var_p = "var " if f.is_var else ""
                t_str = format_type_compact(f.type_val, env, visited_ids, depth + 1)
                f_parts.append(f"{var_p}{f.name}: {t_str}" if f.name else f"{var_p}{t_str}")
            elif isinstance(f, QTupleTypeBinding):
                t_str = format_type_compact(f.type_val, env, visited_ids, depth + 1)
                f_parts.append(f"Let {f.name} = {t_str}")
            elif isinstance(f, QTupleTypeFormal):
                k_str = format_type_compact(f.bound, env, visited_ids, depth + 1)
                f_parts.append(f"Type {f.name} :: {k_str}")
            else:
                f_parts.append(str(f))
        elems_str = " ".join(f_parts)
        return f"Tuple {elems_str} end" if elems_str else "Tuple end"

    # 12. Variants and Options
    if isinstance(t, QVariantType):
        if depth > 3:
            return "Variant ... end"
        v_strs = " ".join(
            f"{'var ' if v.is_var else ''}{v.name}: {format_type_compact(v.type_val, env, visited_ids, depth + 1)}"
            if v.type_val is not OK_TYPE and v.type_val is not None else v.name
            for v in t.variants
        )
        return f"Variant {v_strs} end" if v_strs else "Variant end"

    if isinstance(t, QOptionType):
        if depth > 3:
            return "Option ... end"
        o_strs = " ".join(
            f"{o.name} with {format_type_compact(o.payload_type, env, visited_ids, depth + 1)}"
            if o.payload_type is not None else o.name
            for o in t.options
        )
        return f"Option {o_strs} end" if o_strs else "Option end"

    # 13. Recursive Types (Bounded unfold / self-reference handling)
    if isinstance(t, QRecType):
        if t.symbol_id in visited_ids or depth > 1:
            return t.var_name
        visited_ids = visited_ids | {t.symbol_id}
        b_str = format_type_compact(t.bound, env, visited_ids, depth + 1)
        body_str = format_type_compact(t.body, env, visited_ids, depth + 1)
        return f"Rec({t.var_name} :: {b_str}) {body_str}"

    if isinstance(t, QRecGroupType):
        if t.current_symbol_id in visited_ids or depth > 1:
            return t.current_name
        return f"RecGroup({t.current_name})"

    return str(t)


# Disallow Python == across all QType subclasses, directing callers to is_type_equal or reference identity ('is')
for _cls in list(globals().values()):
    if isinstance(_cls, type) and issubclass(_cls, QType) and _cls is not QType:
        _cls.__eq__ = QType.__eq__


