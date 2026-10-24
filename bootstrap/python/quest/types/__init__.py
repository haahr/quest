"""Quest Semantic Types, Kinds, Substitution, Subtyping, and Pretty Printing.

This package provides:
- quest.types.model: QType, QKind, primitive and composite type representations.
- quest.types.env: Symbol, ValueSymbol, TypeSymbol, KindSymbol, Scope, and Environment.
- quest.types.subtyping: Equi-recursive subtyping proofs, subkinding, and cache.
- quest.types.kinds: Kind checking, kind synthesis, and operator signatures.
- quest.types.contractiveness: Recursive type contractiveness (C \succ X) verification.
- quest.types.dump: Canonical S-expression and compact alias-aware formatters.
- quest.types.canonical: Reduced types, and the canonical (minimal graph) forms of recursive types.
"""

from __future__ import annotations

# 1. Model & Base Definitions
from quest.types.model import (
    BOTTOM_TYPE,
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
    INT_TYPE,
    MAX_SUBTYPE_FUEL,
    MAX_TYPE_EXPANSION_DEPTH,
    OK_TYPE,
    REAL_TYPE,
    RESERVED_INDEX_LIMIT,
    STRING_TYPE,
    TYPE_KIND,
    QAbstractType,
    QAliasType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QBottomType,
    QBoolType,
    QCharType,
    QExceptionType,
    QExternalType,
    QFunType,
    QIntType,
    QKind,
    QKindVar,
    QOkType,
    QOptionField,
    QOptionType,
    QOutType,
    QParam,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRealType,
    QRecGroupType,
    QRecType,
    QRecordField,
    QRecordType,
    QStringType,
    QTupleComponent,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QType,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QTypeKind,
    QTypeMeta,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
    KindLookupEnv,
    KindSymbolProtocol,
    ReservedSymbolUse,
    TypeLookupEnv,
    TypeSymbolProtocol,
    alias_reference,
    auto_matches_subtypes,
    auto_payload_type,
    binds_module,
    find_path_types,
    register_type_formatter,
    reserved_symbol_id,
    reserved_symbol_index,
    reserved_symbol_use,
    resolve_metas,
    strip_aliases,
    structurally_equal,
    type_mentions_symbol_ids,
    unalias,
    unsolved_metas,
)

# 2. Subtyping & Equivalence
from quest.types.subtyping import (
    SUBTYPE_CACHE,
    SubtypeTrail,
    clear_subtype_cache,
    is_kind_equal,
    is_subkind,
    is_subtype,
    is_type_equal,
)

# 3. Kinds, Well-kindedness, Operators, and Bounds
from quest.types.kinds import (
    INFIX_OPERATORS,
    KindError,
    check_kind,
    check_kind_well_formed,
    resolve_option_bound,
    resolve_record_bound,
    resolve_variant_bound,
    synth_kind,
    unfold_head,
)

# 4. Contractiveness
from quest.types.contractiveness import (
    ContractivenessError,
    check_type_contractive,
    is_type_contractive,
)

# 5. Canonical and Compact Formatting
from quest.types.dump import (
    format_type_compact,
    qtype_dump,
    short_type_name,
)

# 6. Scoping, Symbol Tables, and Lexical Environments
from quest.types.env import (
    BuiltinRegistry,
    Environment,
    KindSymbol,
    Scope,
    Symbol,
    TypeSymbol,
    ValueSymbol,
    allocate_symbol_id,
)

# Backward-compatibility aliases
_SUBTYPE_CACHE = SUBTYPE_CACHE
_unfold_head = unfold_head

# Enforce reference equality guard on all QType subclasses
for _cls in list(globals().values()):
    if isinstance(_cls, type) and issubclass(_cls, QType) and _cls is not QType:
        _cls.__eq__ = QType.__eq__
