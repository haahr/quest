"""Quest Symbols and Lexical Scopes.

Symbols name values, types, and kinds; a scope holds the symbols declared in it,
in declaration order. Symbol ids are unique for the life of the process
(allocate_symbol_id), and every declared type and kind symbol is also found by
its id, globally. This module is below subtyping and the unit graph, which need
symbols and scopes but not the type-checking environment (types.env), which
holds them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from quest.types.model import QKind, QType


# ============================================================================
# 1. Symbol Definitions
# ============================================================================

class Symbol:
    """Base class for all named compiler symbols."""
    name: str


@dataclass
class ValueSymbol(Symbol):
    """Value-level symbol: x : Type."""
    name: str
    type_val: QType
    is_var: bool = False
    is_out: bool = False
    is_param: bool = False
    function_depth: int = 0
    symbol_id: int = 0

    _counter: ClassVar[int] = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.symbol_id == 0:
            ValueSymbol._counter += 1
            self.symbol_id = ValueSymbol._counter

    def __str__(self) -> str:
        var_prefix = "var " if self.is_var else ("out " if self.is_out else "")
        return f"{var_prefix}{self.name}: {self.type_val}"


@dataclass
class TypeSymbol(Symbol):
    """Type-level symbol: X :: Kind [= Definition]."""
    name: str
    symbol_id: int
    kind: QKind
    definition: Optional[QType] = None

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "definition":
            # A symbol id must mean one thing for the life of the process (it is
            # looked up globally), so a definition may be supplied after
            # declaration (None -> T) but never replaced.
            current = self.__dict__.get("definition")
            if current is not None:
                if value is current:
                    return
                raise RuntimeError(f"Type symbol '{self.name}' (#{self.symbol_id}) is already defined")
            if value is not None and self.__dict__.get("symbol_id") in _TYPE_IDS_SEEN_UNDEFINED:
                meanings_changed()
        super().__setattr__(name, value)

    @property
    def is_abstract(self) -> bool:
        return self.definition is None

    def __str__(self) -> str:
        if self.definition is not None:
            return f"{self.name} :: {self.kind} = {self.definition}"
        return f"{self.name} :: {self.kind}"


@dataclass
class KindSymbol(Symbol):
    """Kind-level symbol: K = Kind."""
    name: str
    symbol_id: int
    kind: QKind

    def __str__(self) -> str:
        return f"{self.name} = {self.kind}"


# ============================================================================
# 2. Lexical Scope
# ============================================================================

# Every declared type symbol, by symbol id. Symbol ids are unique for the life
# of the process (allocate_symbol_id), so a type variable can be resolved in
# O(1) regardless of the current scope.
_TYPE_SYMBOLS_BY_ID: dict[int, TypeSymbol] = {}
# Likewise every declared kind symbol.
_KIND_SYMBOLS_BY_ID: dict[int, KindSymbol] = {}

# Symbol ids that some lookup found undeclared (or, for types, without a
# definition). Meanings only become more defined, so cached subtyping results
# can go stale only when one of these ids gains a meaning; the subtype cache is
# cleared then (see the subtype cache notes in types.py).
_TYPE_IDS_SEEN_UNDEFINED: set[int] = set()
_KIND_IDS_SEEN_UNDEFINED: set[int] = set()

class Scope:
    """One frame of a chain of lexical scopes: the symbols declared directly in
    one block, function, interface, module, or other construct, and a link to
    the frame around it (parent).

    Values, types, and kinds have namespaces of their own, so that Let T = Int
    and let T: T = 1 may stand side by side. In a namespace, a later
    declaration of a name hides an earlier one in the same frame, as in

        begin let x = 1 let x = x + 1 x end

    where the second x is a new symbol; declarations keeps both, in order.

    lookup_value, lookup_type, and lookup_kind search this frame and then each
    enclosing one, out to the outermost (for a program's scopes, the
    environment's base scope, which holds the builtins); the *_local lookups
    search this frame alone. Types and kinds are also found by symbol id, since
    the types that refer to them hold ids (a QTypeVar holds its symbol_id), not
    names.

    Declaring a type or kind also records it by id in a table global to the
    process. If that gives a meaning to an id that a lookup had found without
    one, or changes the meaning an id had, the declaration calls
    meanings_changed, so that cached subtyping results, which may depend on the
    old meaning, are not reused."""

    def __init__(self, parent: Optional[Scope] = None, name: str = "local"):
        self.parent = parent
        self.name = name
        self.module_name: Optional[str] = None
        self._declarations: list[Symbol] = []
        self._values: dict[str, ValueSymbol] = {}
        self._types: dict[str, TypeSymbol] = {}
        self._types_by_id: dict[int, TypeSymbol] = {}
        self._kinds: dict[str, KindSymbol] = {}
        self._kinds_by_id: dict[int, KindSymbol] = {}

    @property
    def declarations(self) -> list[Symbol]:
        """Returns all symbols declared in this scope in strict declaration
        order."""
        return list(self._declarations)

    @property
    def values(self) -> dict[str, ValueSymbol]:
        return dict(self._values)

    @property
    def types(self) -> dict[str, TypeSymbol]:
        return dict(self._types)

    @property
    def kinds(self) -> dict[str, KindSymbol]:
        return dict(self._kinds)

    def declare_value(self, symbol: ValueSymbol) -> ValueSymbol:
        self._declarations.append(symbol)
        self._values[symbol.name] = symbol
        return symbol

    def declare_type(self, symbol: TypeSymbol) -> TypeSymbol:
        self._declarations.append(symbol)
        self._types[symbol.name] = symbol
        self._types_by_id[symbol.symbol_id] = symbol
        previous = _TYPE_SYMBOLS_BY_ID.get(symbol.symbol_id)
        if symbol.definition is not None and (
            symbol.symbol_id in _TYPE_IDS_SEEN_UNDEFINED
            or (previous is not None and previous.definition is not symbol.definition)
        ):
            meanings_changed()
        _TYPE_SYMBOLS_BY_ID[symbol.symbol_id] = symbol
        return symbol

    def declare_type_variable(
        self,
        name: str,
        symbol_id: int,
        kind: QKind,
        definition: Optional[QType] = None,
    ) -> TypeSymbol:
        """Declares a type symbol from its constituent attributes in the current
        scope."""
        return self.declare_type(
            TypeSymbol(
                name=name,
                symbol_id=symbol_id,
                kind=kind,
                definition=definition,
            )
        )

    def declare_kind(self, symbol: KindSymbol) -> KindSymbol:
        self._declarations.append(symbol)
        self._kinds[symbol.name] = symbol
        self._kinds_by_id[symbol.symbol_id] = symbol
        previous = _KIND_SYMBOLS_BY_ID.get(symbol.symbol_id)
        if symbol.symbol_id in _KIND_IDS_SEEN_UNDEFINED or (previous is not None and previous.kind is not symbol.kind):
            meanings_changed()
        _KIND_SYMBOLS_BY_ID[symbol.symbol_id] = symbol
        return symbol

    # --- Local Lookups ---

    def lookup_value_local(self, name: str) -> Optional[ValueSymbol]:
        return self._values.get(name)

    def lookup_type_local(self, name: str) -> Optional[TypeSymbol]:
        return self._types.get(name)

    def lookup_type_by_id_local(self, symbol_id: int) -> Optional[TypeSymbol]:
        return self._types_by_id.get(symbol_id)

    def lookup_kind_local(self, name: str) -> Optional[KindSymbol]:
        return self._kinds.get(name)

    def lookup_kind_by_id_local(self, symbol_id: int) -> Optional[KindSymbol]:
        return self._kinds_by_id.get(symbol_id)

    # --- Lexical Chain Lookups ---

    def lookup_value(self, name: str) -> Optional[ValueSymbol]:
        if name in self._values:
            return self._values[name]
        return self.parent.lookup_value(name) if self.parent else None

    def lookup_type(self, name: str) -> Optional[TypeSymbol]:
        if name in self._types:
            return self._types[name]
        return self.parent.lookup_type(name) if self.parent else None

    def lookup_type_by_id(self, symbol_id: int) -> Optional[TypeSymbol]:
        if symbol_id in self._types_by_id:
            return self._types_by_id[symbol_id]
        return self.parent.lookup_type_by_id(symbol_id) if self.parent else None

    def lookup_kind(self, name: str) -> Optional[KindSymbol]:
        if name in self._kinds:
            return self._kinds[name]
        return self.parent.lookup_kind(name) if self.parent else None

    def lookup_kind_by_id(self, symbol_id: int) -> Optional[KindSymbol]:
        if symbol_id in self._kinds_by_id:
            return self._kinds_by_id[symbol_id]
        return self.parent.lookup_kind_by_id(symbol_id) if self.parent else None

    def __repr__(self) -> str:
        return f"Scope({self.name!r}, {len(self._declarations)} decls)"


# ============================================================================
# 3. Symbol Ids and Meanings
# ============================================================================

_GLOBAL_SYMBOL_COUNTER: int = 0


def allocate_symbol_id() -> int:
    """Allocates a globally unique positive integer symbol ID."""
    global _GLOBAL_SYMBOL_COUNTER
    _GLOBAL_SYMBOL_COUNTER += 1
    return _GLOBAL_SYMBOL_COUNTER


# The number of times a symbol id gained a meaning after some lookup saw it
# without one. Meanings only become more defined, so judgments cached about
# types (the subtype cache, types.subtyping) can go stale only then; a cache
# records the generation it was filled in and is dropped when the generation
# changes.
_meaning_generation: int = 0


def meanings_changed() -> None:
    """Records that a symbol id that some lookup saw undefined has gained a
    meaning."""
    global _meaning_generation
    _meaning_generation += 1


def meaning_generation() -> int:
    """The number of times meanings_changed has been called."""
    return _meaning_generation
