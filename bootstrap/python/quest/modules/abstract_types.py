"""The abstract types that modules export, by global name, for serializing dynamic values (docs/dynamic.md §2.3).

A module's abstract type is closed: it is named through the global name space of modules, as the module's
canonical path, a dot, and the type's name ("geo/coord.P"). Its opaque type has one symbol id per global name in
the process, so that every environment that elaborates or imports the module (the interpreter evaluates modules in
environments of their own) agrees on it. Elaborating a module records each abstract type it exports with its
representation, so that dynamic.extern can write a value of the type at its representation, and dynamic.intern can
check a recorded representation against the module's. dynamic.intern also records the types of modules the
program does not link, as opaque types with the representations they were written with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from quest.env import allocate_symbol_id
from quest.types import QType, QTypeVar


@dataclass
class ModuleAbstractType:
    """An abstract type (or abstract type operator) exported by a module.

    `linked` is false for a type read from a module the program does not link. `rep` is the type that implements a
    linked module's type (a type operator for an abstract type operator), once the module has been elaborated from
    its source. An unlinked type's representations are in `instances`: each pair is the arguments of an application
    (empty for a type) and the representation it was written with.
    """

    global_name: str
    type_var: QTypeVar
    linked: bool
    rep: Optional[QType] = None
    instances: list[tuple[tuple[QType, ...], QType]] = field(default_factory=list)


_SYMBOL_IDS: dict[str, int] = {}
_BY_SYMBOL: dict[int, ModuleAbstractType] = {}
_BY_NAME: dict[str, ModuleAbstractType] = {}


def abstract_type_symbol_id(global_name: str) -> int:
    """The symbol id of the opaque type of the module abstract type with this global name."""
    symbol_id = _SYMBOL_IDS.get(global_name)
    if symbol_id is None:
        symbol_id = _SYMBOL_IDS[global_name] = allocate_symbol_id()
    return symbol_id


def _record(global_name: str, type_var: QTypeVar, linked: bool) -> ModuleAbstractType:
    entry = _BY_NAME.get(global_name)
    if entry is None or entry.type_var is not type_var or entry.linked != linked:
        entry = ModuleAbstractType(global_name, type_var, linked)
        _BY_NAME[global_name] = entry
    _BY_SYMBOL[type_var.symbol_id] = entry
    return entry


def register_exported_abstract_type(global_name: str, type_var: QTypeVar) -> None:
    """Records an abstract type that a module the program links exports."""
    _record(global_name, type_var, linked=True)


def register_abstract_type_representation(global_name: str, type_var: QTypeVar, rep: QType) -> None:
    """Records the representation of an exported abstract type, from the module's source."""
    _record(global_name, type_var, linked=True).rep = rep


def register_unlinked_abstract_type(global_name: str, type_var: QTypeVar) -> ModuleAbstractType:
    """Records an abstract type read from a module the program does not link."""
    return _record(global_name, type_var, linked=False)


def abstract_type_by_symbol(symbol_id: int) -> Optional[ModuleAbstractType]:
    return _BY_SYMBOL.get(symbol_id)


def abstract_type_by_name(global_name: str) -> Optional[ModuleAbstractType]:
    return _BY_NAME.get(global_name)


def module_abstract_types(canon: str) -> list[ModuleAbstractType]:
    """The abstract types the module with canonical name canon exports, with their representations, by name."""
    prefix = canon + "."
    return sorted(
        (e for name, e in _BY_NAME.items() if e.linked and e.rep is not None and name.startswith(prefix)
         and "." not in name[len(prefix):]),
        key=lambda e: e.global_name,
    )
