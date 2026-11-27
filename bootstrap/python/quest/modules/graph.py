"""The graph of program units (docs/build-process.md §2.1).

A program is made of units: the program itself (a main routine, or inline code),
module files (.mod.quest), interface files (.int.quest), and the standard
library's units, some of which have no source. Each import names a unit by a
path, which is resolved from the importing unit's directory and then the search
paths (docs/modules.md §2.2, quest.modules.resolution), and each unit has one
canonical name (§2.3), which identifies it everywhere after.

This module holds the **units** (`Unit`) and their **type-checked forms**: the
interfaces and modules an environment has loaded, by kind and canonical name,
with their elaborated scopes and typed modules (`UnitGraph`). Typed forms
belong to one elaboration (they hold the symbols it minted), so each
type-checking Environment has its own graph; the graphs of one session share a
resolver. The REPL keeps one graph across its inputs, each a session, and rolls
it back when an input fails.

The self-hosted counterpart is questlang/modules/graph.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from quest.modules.paths import canonicalize_module_path
from quest.modules.resolution import Resolver
from quest.modules.units import UnitKind

if TYPE_CHECKING:
    from quest.types.symbols import Scope


@dataclass(eq=False)
class Unit:
    """An interface or module an environment has loaded, with its type-checked
    forms.

    An interface has its scope once elaborated (from source or from its .qi). A
    module has its typed module once elaborated or synthesized from its
    interface, and an export scope when it is known only through its interface
    (separate compilation); precompiled marks a module typed through its
    interface alone (a prebuilt object, a module built separately, or one with
    fresh artifacts in a typecheck-only run). The values of modules the
    interpreter has run are the interpreter's
    (RuntimeEnvironment.module_values), not the unit's.
    """
    kind: UnitKind
    canonical_name: str
    scope: Optional[Scope] = None
    typed_module: Optional[Any] = None
    export_scope: Optional[Scope] = None
    precompiled: bool = False

    def state(self) -> tuple[Any, ...]:
        return (self.scope, self.typed_module, self.export_scope, self.precompiled)


@dataclass
class UnitGraph:
    """The units one type-checking Environment has loaded, by kind and canonical
    name, and the resolver that resolves its imports.

    Loaded units are shared by canonical name (docs/modules.md §2.3): every
    importer of a file, through any path, gets the same unit, and so the same
    interface scope, export scope (with the same abstract types), and typed
    module. The interpreter's RuntimeEnvironment holds the graph of the
    Environment that type checked its program (CompilerContext.runtime_env), the
    same object, so that the two never disagree about which units are loaded:
    restore changes the graph in place.

    A graph outlives a session when the REPL keeps it from one input to the
    next. Each input is a session of its own (new_session), and one that fails
    is rolled back (snapshot, restore), forgetting the units it loaded, so that
    importing them again elaborates them again (and the runtime environment's
    rollback forgets their values, so that they run again).
    """
    resolver: Resolver = field(default_factory=Resolver)
    _units: dict[tuple[UnitKind, str], Unit] = field(default_factory=dict)

    def new_session(self) -> None:
        """Starts a new compilation session on this graph: imports are resolved
        again, so that files created since are found. Units already loaded stay
        loaded, as they were elaborated (the REPL starts one for each input)."""
        self.resolver.forget()

    def unit(self, kind: UnitKind, canonical_name: str) -> Unit:
        """The unit of this kind named canonical_name, added if not yet
        known."""
        key = (kind, canonical_name)
        found = self._units.get(key)
        if found is None:
            found = Unit(kind, canonical_name)
            self._units[key] = found
        return found

    def find(self, kind: UnitKind, canonical_name: str) -> Optional[Unit]:
        """The unit of this kind named canonical_name, if known."""
        return self._units.get((kind, canonical_name))

    def interface_scope(self, canonical_name: str) -> Optional[Scope]:
        """The scope of the loaded interface named canonical_name, if it has
        been loaded."""
        found = self.find(UnitKind.INTERFACE, canonical_name)
        return found.scope if found is not None else None

    def typed_module(self, canonical_name: str) -> Optional[Any]:
        """The typed module named canonical_name, if it has been loaded."""
        found = self.find(UnitKind.MODULE, canonical_name)
        return found.typed_module if found is not None else None

    def is_precompiled(self, name: str) -> bool:
        """Whether the module named name (its canonical name, or the name a
        source-less module is imported by) is typed through its interface
        alone."""
        found = self.find(UnitKind.MODULE, name)
        return found is not None and found.precompiled

    def interface_scopes(self) -> dict[str, Scope]:
        """The loaded interfaces' scopes, by canonical name."""
        return {u.canonical_name: u.scope for u in self._units.values() if u.kind == UnitKind.INTERFACE and u.scope}

    def export_scopes(self) -> dict[str, Scope]:
        """The export scopes of modules known through their interfaces, by
        canonical name."""
        return {
            u.canonical_name: u.export_scope
            for u in self._units.values()
            if u.kind == UnitKind.MODULE and u.export_scope is not None
        }

    def adopt(self, interface_scopes: dict[str, Scope], export_scopes: dict[str, Scope]) -> None:
        """Takes interfaces and export scopes another environment loaded (the
        standard library's, which are loaded once per process), replacing any of
        the same names."""
        for name, scope in interface_scopes.items():
            self.unit(UnitKind.INTERFACE, name).scope = scope
        for name, scope in export_scopes.items():
            self.unit(UnitKind.MODULE, name).export_scope = scope

    def add_prebuilt_objects(self, objects: list[Path], include_paths: Any) -> None:
        """Marks the modules of prebuilt object files given to the driver as
        typed through their interfaces alone, by their canonical names (against
        include_paths) and by their base names."""
        for obj in objects:
            self.unit(UnitKind.MODULE, canonicalize_module_path(obj, list(include_paths or ()))).precompiled = True
            self.unit(UnitKind.MODULE, obj.name.split(".")[0]).precompiled = True

    def snapshot(self) -> dict[tuple[UnitKind, str], tuple[Any, ...]]:
        """The units' typed forms, for restore (the REPL rolls back an input
        that failed)."""
        return {key: u.state() for key, u in self._units.items()}

    def restore(self, snap: dict[tuple[UnitKind, str], tuple[Any, ...]]) -> None:
        """Puts the units' typed forms back as snapshot found them, forgetting
        units loaded since. The graph is changed in place, so every holder of it
        (the interpreter's RuntimeEnvironment) sees the change."""
        self._units = {key: Unit(key[0], key[1], *state) for key, state in snap.items()}
