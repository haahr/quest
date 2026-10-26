"""The standard library's modules and interfaces, as the type checker and the
compilers see them: their names, and their interfaces and module scopes, loaded
on demand. Their implementations are elsewhere: C (runtime/, lib/) for compiled
code, and Python (quest.interpreter.builtins) for the interpreters."""

from __future__ import annotations

from typing import Optional

from quest.types.env import Environment, Scope, ValueSymbol
from quest.types import QType
from quest.modules.elaboration import (
    build_record_type_from_scope,
    load_interface,
    separately_compiled_module_scope,
)

STANDARD_LIBRARY_MODULES: dict[str, str] = {
    "list": "List",
    "string": "StringOp",
    "conv": "Conv",
    "int": "IntOp",
    "real": "RealOp",
    "ascii": "Ascii",
    "arrayOp": "ArrayOp",
    "word": "Word",
    "writer": "Writer",
    "reader": "Reader",
    "system": "System",
}

STANDARD_LIBRARY_INTERFACES: dict[str, str] = {}
for _mod, _iface in STANDARD_LIBRARY_MODULES.items():
    STANDARD_LIBRARY_INTERFACES[_iface] = _iface
    STANDARD_LIBRARY_INTERFACES[_iface.lower()] = _iface
    STANDARD_LIBRARY_INTERFACES[_mod] = _iface
    STANDARD_LIBRARY_INTERFACES[_mod.lower()] = _iface

STANDARD_LIBRARY_MODULE_NAMES: dict[str, str] = {}
for _mod in STANDARD_LIBRARY_MODULES:
    STANDARD_LIBRARY_MODULE_NAMES[_mod] = _mod
    STANDARD_LIBRARY_MODULE_NAMES[_mod.lower()] = _mod


class BuiltinModuleRegistry:
    """The standard library's interfaces and modules, loaded on demand into an
    Environment (its builtin_registry)."""

    _cached_interfaces: dict[str, Scope] = {}
    _cached_mod_scopes: dict[str, Scope] = {}
    _cached_mod_types: dict[str, QType] = {}
    _cached_loaded_interfaces: dict[str, Scope] = {}
    _cached_module_export_scopes: dict[str, Scope] = {}

    @classmethod
    def ensure_interface(cls, iface_name: str, env: Optional[Environment] = None) -> Optional[Scope]:
        """Loads and caches standard library interface `iface_name`, registering
        it in `env`."""
        target_iface = STANDARD_LIBRARY_INTERFACES.get(iface_name)
        if target_iface is None:
            return None
        if target_iface not in cls._cached_interfaces:
            base_env = Environment(builtin_registry=False)
            iface_scope = load_interface(target_iface, base_env)
            cls._cached_interfaces[target_iface] = iface_scope
            cls._cached_loaded_interfaces.update(base_env.units.interface_scopes())
            cls._cached_module_export_scopes.update(base_env.units.export_scopes())

        iface_scope = cls._cached_interfaces[target_iface]
        if env is not None:
            env.register_interface(target_iface, iface_scope)
            if iface_name != target_iface:
                env.register_interface(iface_name, iface_scope)
            env._builtin_interfaces[target_iface] = iface_scope
            env.units.adopt(cls._cached_loaded_interfaces, cls._cached_module_export_scopes)
        return iface_scope

    @classmethod
    def ensure_module(cls, mod_name: str, env: Optional[Environment] = None) -> Optional[Scope]:
        """Loads and caches standard library module `mod_name`, registering it
        in `env`."""
        norm_mod = STANDARD_LIBRARY_MODULE_NAMES.get(mod_name)
        if norm_mod is None:
            return None
        iface_name = STANDARD_LIBRARY_MODULES[norm_mod]
        cls.ensure_interface(iface_name, env)
        if norm_mod not in cls._cached_mod_scopes:
            base_env = Environment(builtin_registry=False)
            iface_scope = cls._cached_interfaces[iface_name]
            mod_scope = separately_compiled_module_scope(norm_mod, iface_scope, base_env)
            cls._cached_mod_scopes[norm_mod] = mod_scope
            cls._cached_mod_types[norm_mod] = build_record_type_from_scope(mod_scope, provenance=norm_mod)

        mod_scope = cls._cached_mod_scopes[norm_mod]
        mod_type = cls._cached_mod_types[norm_mod]
        if env is not None:
            env.register_module(norm_mod, mod_scope)
            if mod_name != norm_mod:
                env.register_module(mod_name, mod_scope)
            env._builtin_modules[norm_mod] = mod_scope
            if not env.global_scope.lookup_value_local(norm_mod):
                env.global_scope.declare_value(ValueSymbol(name=norm_mod, type_val=mod_type))
        return mod_scope

    @classmethod
    def populate_environment(cls, env: Environment) -> None:
        """Registers standard library resolution hook into an Environment."""
        env.builtin_registry = cls


Environment.set_default_builtin_registry(BuiltinModuleRegistry)

