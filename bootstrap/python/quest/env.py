"""Quest Scoping, Symbol Tables, and Lexical Environments."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Optional

from quest.types import (
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
    INFIX_OPERATORS,
    INT_TYPE,
    OK_TYPE,
    QAllType,
    QArrayType,
    QFunType,
    QKind,
    QParam,
    QQuantifier,
    QType,
    QTypeVar,
    REAL_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    clear_subtype_cache,
    distinct_alias_definition,
)


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
            # A symbol id must mean one thing for the life of the process (it is looked up globally), so
            # a definition may be supplied after declaration (None -> T) but never replaced.
            current = self.__dict__.get("definition")
            if current is not None:
                if value is current or current.__dict__.get("_alias_of") is value:
                    return
                raise RuntimeError(f"Type symbol '{self.name}' (#{self.symbol_id}) is already defined")
            # Each alias keeps its own definition object, so that it prints under its own name.
            value = distinct_alias_definition(value)
            if value is not None and self.__dict__.get("symbol_id") in _TYPE_IDS_SEEN_UNDEFINED:
                clear_subtype_cache()
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

# Every declared type symbol, by symbol id. Symbol ids are unique for the life of the process
# (allocate_symbol_id), so a type variable can be resolved in O(1) regardless of the current scope.
_TYPE_SYMBOLS_BY_ID: dict[int, TypeSymbol] = {}
# Likewise every declared kind symbol.
_KIND_SYMBOLS_BY_ID: dict[int, KindSymbol] = {}

# Symbol ids that some lookup found undeclared (or, for types, without a definition). Meanings only
# become more defined, so cached subtyping results can go stale only when one of these ids gains a
# meaning; the subtype cache is cleared then (see the subtype cache notes in types.py).
_TYPE_IDS_SEEN_UNDEFINED: set[int] = set()
_KIND_IDS_SEEN_UNDEFINED: set[int] = set()

class Scope:
    """A single lexical scope frame maintaining ordered declarations."""

    def __init__(self, parent: Optional[Scope] = None, name: str = "local"):
        self.parent = parent
        self.name = name
        self._declarations: list[Symbol] = []
        self._values: dict[str, ValueSymbol] = {}
        self._types: dict[str, TypeSymbol] = {}
        self._types_by_id: dict[int, TypeSymbol] = {}
        self._kinds: dict[str, KindSymbol] = {}
        self._kinds_by_id: dict[int, KindSymbol] = {}

    @property
    def declarations(self) -> list[Symbol]:
        """Returns all symbols declared in this scope in strict declaration order."""
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
            clear_subtype_cache()
        _TYPE_SYMBOLS_BY_ID[symbol.symbol_id] = symbol
        return symbol

    def declare_kind(self, symbol: KindSymbol) -> KindSymbol:
        self._declarations.append(symbol)
        self._kinds[symbol.name] = symbol
        self._kinds_by_id[symbol.symbol_id] = symbol
        previous = _KIND_SYMBOLS_BY_ID.get(symbol.symbol_id)
        if symbol.symbol_id in _KIND_IDS_SEEN_UNDEFINED or (previous is not None and previous.kind is not symbol.kind):
            clear_subtype_cache()
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
# 3. Compiler Environment
# ============================================================================

_GLOBAL_SYMBOL_COUNTER: int = 0


def allocate_symbol_id() -> int:
    """Allocates a globally unique positive integer symbol ID."""
    global _GLOBAL_SYMBOL_COUNTER
    _GLOBAL_SYMBOL_COUNTER += 1
    return _GLOBAL_SYMBOL_COUNTER


class Environment:
    """Manages the active lexical scope stack, built-in definitions, and module linkages."""

    def __init__(self, sink: Optional[Any] = None):
        self._symbol_counter: int = 0
        self.sink = sink
        self.base_scope: Scope = Scope(parent=None, name="base")
        self.global_scope: Scope = Scope(parent=self.base_scope, name="global")
        self.current_scope: Scope = self.global_scope
        self._interfaces: dict[str, Scope] = {}
        self._modules: dict[str, Scope] = {}
        self.include_paths: list[Path] = []
        self.current_dir: Optional[Path] = None
        self.loaded_modules_ast: dict[str, Any] = {}
        self.precompiled_modules: set[str] = set()
        self._loading_interfaces: list[str] = []
        self._loading_modules: list[str] = []
        self.subtype_cache: dict[tuple[int, int], bool] = {}
        self.options: Optional[Any] = None
        self._init_builtins()

    def fresh_symbol_id(self) -> int:
        """Allocates a unique positive integer symbol ID."""
        return allocate_symbol_id()

    def push_scope(self, name: str = "local") -> Scope:
        """Pushes a new child scope onto the active scope stack."""
        self.current_scope = Scope(parent=self.current_scope, name=name)
        return self.current_scope

    def pop_scope(self) -> Scope:
        """Pops the current scope from the stack and returns it."""
        if self.current_scope.parent is None:
            raise RuntimeError("Cannot pop root global scope from Environment")
        popped = self.current_scope
        self.current_scope = self.current_scope.parent
        return popped

    @contextmanager
    def scoped(self, name: str = "local") -> Iterator[Scope]:
        """RAII context manager for entering and exiting a lexical child scope."""
        self.push_scope(name)
        try:
            yield self.current_scope
        finally:
            self.pop_scope()

    # --- Direct Delegation Lookups ---

    def lookup_value(self, name: str) -> Optional[ValueSymbol]:
        return self.current_scope.lookup_value(name)

    def lookup_type(self, name: str) -> Optional[TypeSymbol]:
        return self.current_scope.lookup_type(name)

    def lookup_type_by_id(self, symbol_id: int) -> Optional[TypeSymbol]:
        sym = _TYPE_SYMBOLS_BY_ID.get(symbol_id)
        if sym is None or sym.definition is None:
            _TYPE_IDS_SEEN_UNDEFINED.add(symbol_id)
        return sym

    def lookup_kind(self, name: str) -> Optional[KindSymbol]:
        return self.current_scope.lookup_kind(name)

    def lookup_kind_by_id(self, symbol_id: int) -> Optional[KindSymbol]:
        sym = _KIND_SYMBOLS_BY_ID.get(symbol_id)
        if sym is None:
            _KIND_IDS_SEEN_UNDEFINED.add(symbol_id)
        return sym

    # --- Interface and Module Registries ---

    def register_interface(self, name: str, scope: Scope) -> None:
        self._interfaces[name] = scope

    def lookup_interface(self, name: str) -> Optional[Scope]:
        return self._interfaces.get(name)

    def register_module(self, name: str, scope: Scope) -> None:
        self._modules[name] = scope

    def lookup_module(self, name: str) -> Optional[Scope]:
        return self._modules.get(name)

    def snapshot(self) -> dict[str, Any]:
        """Captures a snapshot of the current environment state for rollback on error."""
        return {
            "symbol_counter": self._symbol_counter,
            "interfaces": dict(self._interfaces),
            "modules": dict(self._modules),
            "loaded_modules_ast": dict(self.loaded_modules_ast),
            "precompiled_modules": set(self.precompiled_modules),
            "scope_declarations": list(self.current_scope._declarations),
            "scope_values": dict(self.current_scope._values),
            "scope_types": dict(self.current_scope._types),
            "scope_types_by_id": dict(self.current_scope._types_by_id),
            "scope_kinds": dict(self.current_scope._kinds),
            "scope_kinds_by_id": dict(self.current_scope._kinds_by_id),
        }

    def restore(self, snap: dict[str, Any]) -> None:
        """Restores environment state from a previous snapshot."""
        self._symbol_counter = snap["symbol_counter"]
        self._interfaces = dict(snap["interfaces"])
        self._modules = dict(snap["modules"])
        if "loaded_modules_ast" in snap:
            self.loaded_modules_ast = dict(snap["loaded_modules_ast"])
        if "precompiled_modules" in snap:
            self.precompiled_modules = set(snap["precompiled_modules"])
        self.current_scope._declarations = list(snap["scope_declarations"])
        self.current_scope._values = dict(snap["scope_values"])
        self.current_scope._types = dict(snap["scope_types"])
        self.current_scope._types_by_id = dict(snap["scope_types_by_id"])
        self.current_scope._kinds = dict(snap["scope_kinds"])
        self.current_scope._kinds_by_id = dict(snap["scope_kinds_by_id"])

    # --- Built-in Initialization ---

    def _init_builtins(self) -> None:
        """Populates the base scope with primitives, and global scope with pre-linked modules."""
        # Built-in Kinds
        self.base_scope.declare_kind(
            KindSymbol(name="TYPE", symbol_id=self.fresh_symbol_id(), kind=TYPE_KIND)
        )

        # Built-in Primitive Types
        builtin_types = [
            ("Int", INT_TYPE),
            ("Real", REAL_TYPE),
            ("Bool", BOOL_TYPE),
            ("Char", CHAR_TYPE),
            ("String", STRING_TYPE),
            ("Ok", OK_TYPE),
            ("Dynamic", DYNAMIC_TYPE),
            ("Exception", EXCEPTION_TYPE),
        ]
        for type_name, qtype_inst in builtin_types:
            self.base_scope.declare_type(
                TypeSymbol(
                    name=type_name,
                    symbol_id=self.fresh_symbol_id(),
                    kind=TYPE_KIND,
                    definition=qtype_inst,
                )
            )

        # Built-in Primitive Values
        self.base_scope.declare_value(ValueSymbol(name="true", type_val=BOOL_TYPE))
        self.base_scope.declare_value(ValueSymbol(name="false", type_val=BOOL_TYPE))
        self.base_scope.declare_value(ValueSymbol(name="ok", type_val=OK_TYPE))

        # Built-in exception: DivideByZero
        # Note: Binding DivideByZero at root level is an extension to Cardelli's spec.
        self.base_scope.declare_value(ValueSymbol(name="DivideByZero", type_val=EXCEPTION_TYPE))

        # Built-in operators as functions (Cardelli §4.2)
        for op, (l_type, r_type, res_type) in INFIX_OPERATORS.items():
            op_fn_type = QFunType(
                params=(
                    QParam(name="a", type_val=l_type),
                    QParam(name="b", type_val=r_type),
                ),
                result_type=res_type,
            )
            self.base_scope.declare_value(ValueSymbol(name=op, type_val=op_fn_type))

        # Built-in monadic operators: not, extent, ordinal (Cardelli §4.2, §4.3, §4.5)
        self.base_scope.declare_value(
            ValueSymbol(
                name="not",
                type_val=QFunType(
                    params=(QParam(name="b", type_val=BOOL_TYPE),),
                    result_type=BOOL_TYPE,
                ),
            )
        )
        extent_quant_id = self.fresh_symbol_id()
        extent_quant = QQuantifier(name="A", symbol_id=extent_quant_id, bound=TYPE_KIND)
        extent_var = QTypeVar(name="A", symbol_id=extent_quant_id)
        extent_fn_type = QAllType(
            quantifiers=(extent_quant,),
            body=QFunType(
                params=(QParam(name="a", type_val=QArrayType(element_type=extent_var)),),
                result_type=INT_TYPE,
            ),
        )
        self.base_scope.declare_value(ValueSymbol(name="extent", type_val=extent_fn_type))

        ord_quant_id = self.fresh_symbol_id()
        ord_quant = QQuantifier(name="A", symbol_id=ord_quant_id, bound=TYPE_KIND)
        ord_var = QTypeVar(name="A", symbol_id=ord_quant_id)
        ord_fn_type = QAllType(
            quantifiers=(ord_quant,),
            body=QFunType(
                params=(QParam(name="o", type_val=ord_var),),
                result_type=INT_TYPE,
            ),
        )
        self.base_scope.declare_value(ValueSymbol(name="ordinal", type_val=ord_fn_type))

        # Pre-link standard library modules at top level (Cardelli §11.3)
        from quest.builtins import BuiltinModuleRegistry
        BuiltinModuleRegistry._ensure_initialized(self)
        mod_to_iface = {
            "writer": "Writer",
            "reader": "Reader",
            "conv": "Conv",
            "ascii": "Ascii",
            "int": "IntOp",
            "real": "RealOp",
            "string": "StringOp",
            "arrayOp": "ArrayOp",
            "dynamic": "Dynamic",
            "list": "List",
            "word": "Word",
        }
        for iface_name, iface_scope in BuiltinModuleRegistry._interfaces.items():
            self.register_interface(iface_name, iface_scope)
        for mod_name, mod_type in BuiltinModuleRegistry._module_types.items():
            self.global_scope.declare_value(ValueSymbol(name=mod_name, type_val=mod_type))
            iface_name = mod_to_iface.get(mod_name)
            if iface_name and iface_name in BuiltinModuleRegistry._interfaces:
                self.register_module(mod_name, BuiltinModuleRegistry._interfaces[iface_name])

