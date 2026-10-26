"""Quest Type-Checking Environments: the scope stack, the builtins, and the
interfaces, modules, and units in scope. Symbols and scopes are
quest.types.symbols's (and are re-exported here)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, ClassVar, Optional, Protocol

from quest.diagnostics import in_unit
from quest.modules.graph import UnitGraph
from quest.types.model import (
    BOOL_TYPE,
    CHAR_TYPE,
    DYNAMIC_TYPE,
    EXCEPTION_TYPE,
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
)
from quest.types.symbols import (
    KindSymbol,
    Scope,
    Symbol,
    TypeSymbol,
    ValueSymbol,
    _KIND_IDS_SEEN_UNDEFINED,
    _KIND_SYMBOLS_BY_ID,
    _TYPE_IDS_SEEN_UNDEFINED,
    _TYPE_SYMBOLS_BY_ID,
    allocate_symbol_id,
)


# ============================================================================
# Operator Signatures (Cardelli §4.2)
# ============================================================================

# Operator signature table for non-overloaded Quest infix operators, which the
# environment declares as functions: Maps operator symbol ->
# (expected_left_type, expected_right_type, result_type)
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


# ============================================================================
# 1. Compiler Environment
# ============================================================================

class BuiltinRegistry(Protocol):
    """Protocol for a registry that populates standard library modules and
    interfaces into an Environment."""

    def populate_environment(self, env: Environment) -> None:
        ...

    def ensure_interface(self, iface_name: str, env: Optional[Environment] = None) -> Optional[Scope]:
        ...

    def ensure_module(self, mod_name: str, env: Optional[Environment] = None) -> Optional[Scope]:
        ...


class Environment:
    """Manages the active lexical scope stack, built-in definitions, and module
    linkages."""

    _default_builtin_registry: ClassVar[Optional[BuiltinRegistry]] = None

    @classmethod
    def set_default_builtin_registry(cls, registry: Optional[BuiltinRegistry]) -> None:
        """Configures the default builtin registry used when none is provided to
        __init__."""
        cls._default_builtin_registry = registry

    def __init__(
        self,
        sink: Optional[Any] = None,
        builtin_registry: Optional[BuiltinRegistry] = None,
    ):
        self._symbol_counter: int = 0
        self.sink = sink
        self.base_scope: Scope = Scope(parent=None, name="base")
        self.global_scope: Scope = Scope(parent=self.base_scope, name="global")
        self.current_scope: Scope = self.global_scope
        self._interfaces: dict[str, Scope] = {}
        self._modules: dict[str, Scope] = {}
        self.include_paths: list[Path] = []
        self.current_dir: Optional[Path] = None
        # The source map of the file being elaborated (the program, or an
        # imported unit; see unit_source), which imports are located in when
        # they report errors in the units they load
        self.source_map: Optional[Any] = None
        # The directory of the program being compiled, which names units under
        # no include root (docs/modules.md §2.3)
        self.program_dir: Optional[Path] = None
        self._units: Optional[UnitGraph] = None
        self._loading_interfaces: list[str] = []
        self._loading_modules: list[str] = []
        self.subtype_cache: dict[tuple[int, int], bool] = {}
        self.options: Optional[Any] = None
        # The interface and module names in _interfaces and _modules are those
        # of the unit being elaborated: the builtins and the unit's imports. The
        # units loaded from files are in units, by canonical name.
        self._builtin_interfaces: dict[str, Scope] = {}
        self._builtin_modules: dict[str, Scope] = {}
        self._init_builtins()
        reg = self._default_builtin_registry if builtin_registry is None else builtin_registry
        self.builtin_registry = reg
        if reg:
            reg.populate_environment(self)
        self._builtin_interfaces = dict(self._interfaces)
        self._builtin_modules = dict(self._modules)

    @property
    def units(self) -> UnitGraph:
        """The units this environment has loaded, with their type-checked forms,
        and the resolver of its imports (quest.modules.graph.UnitGraph,
        docs/build-process.md §2.1)."""
        if self._units is None:
            self._units = UnitGraph()
        return self._units

    @units.setter
    def units(self, graph: UnitGraph) -> None:
        self._units = graph

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
        """RAII context manager for entering and exiting a lexical child
        scope."""
        self.push_scope(name)
        try:
            yield self.current_scope
        finally:
            self.pop_scope()

    # --- Direct Delegation Lookups and Declarations ---

    def declare_type_variable(
        self,
        name: str,
        symbol_id: int,
        kind: QKind,
        definition: Optional[QType] = None,
    ) -> TypeSymbol:
        """Declares a type symbol in the active scope."""
        return self.current_scope.declare_type_variable(
            name=name,
            symbol_id=symbol_id,
            kind=kind,
            definition=definition,
        )

    def lookup_value(self, name: str) -> Optional[ValueSymbol]:
        res = self.current_scope.lookup_value(name)
        if res is None and self.builtin_registry and self.builtin_registry.ensure_module(name, self):
            res = self.current_scope.lookup_value(name)
        return res

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
        res = self._interfaces.get(name)
        if res is None and self.builtin_registry:
            res = self.builtin_registry.ensure_interface(name, self)
        return res

    def register_module(self, name: str, scope: Scope) -> None:
        self._modules[name] = scope

    def lookup_module(self, name: str) -> Optional[Scope]:
        res = self._modules.get(name)
        if res is None and self.builtin_registry:
            res = self.builtin_registry.ensure_module(name, self)
        return res

    @contextmanager
    def unit_source(self, source_map: Any) -> Iterator[None]:
        """Elaborates a unit loaded from the file of source_map: errors raised
        inside are located in that file (diagnostics.in_unit), and imports it
        makes are located in it (source_map)."""
        saved = self.source_map
        self.source_map = source_map
        try:
            with in_unit(source_map):
                yield
        finally:
            self.source_map = saved

    @contextmanager
    def unit_names(self) -> Iterator[None]:
        """Gives a unit being loaded from a file its own interface and module
        names.

        Inside, only the builtin names are registered, so the unit's imports are
        resolved from its own directory rather than taken from its importer's
        names, which may name different units (a sibling `counter` of a unit in
        util/ is util/counter). The importer's names are restored afterwards;
        loaded units are shared through units, by canonical name.
        """
        saved = (self._interfaces, self._modules)
        self._interfaces = dict(self._builtin_interfaces)
        self._modules = dict(self._builtin_modules)
        try:
            yield
        finally:
            self._interfaces, self._modules = saved

    def snapshot(self) -> dict[str, Any]:
        """Captures a snapshot of the current environment state for rollback on
        error."""
        return {
            "symbol_counter": self._symbol_counter,
            "interfaces": dict(self._interfaces),
            "modules": dict(self._modules),
            "units": self.units.snapshot(),
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
        if "units" in snap:
            self.units.restore(snap["units"])
        self.current_scope._declarations = list(snap["scope_declarations"])
        self.current_scope._values = dict(snap["scope_values"])
        self.current_scope._types = dict(snap["scope_types"])
        self.current_scope._types_by_id = dict(snap["scope_types_by_id"])
        self.current_scope._kinds = dict(snap["scope_kinds"])
        self.current_scope._kinds_by_id = dict(snap["scope_kinds_by_id"])

    # --- Built-in Initialization ---

    def _init_builtins(self) -> None:
        """Populates the base scope with primitives, and global scope with
        pre-linked modules."""
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

        # Built-in monadic operators: not, extent, ordinal (Cardelli §4.2, §4.3,
        # §4.5)
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

