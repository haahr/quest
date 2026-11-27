"""Import resolution (docs/build-process.md §2.1): an import path, resolved
from a directory with given search paths and program directory, to the unit's
file and its names (`Resolver`, `Resolved`).

Resolutions are memoized: each import is resolved once per compilation session,
and every consumer (the type checker's loading, the interface compiler, the
module compiler's manifests, the build engine's queue and staleness checks, the
interpreter) receives the same result. Resolution depends only on which source
files exist, which a compilation never changes; artifacts, which it does write,
are looked up when needed (`fresh_interface_qi`). The edges between interfaces
(`interface_import_paths`, `Resolver.interface_dependencies`) are found here
too, and whether a unit's recorded imports would now resolve differently
(`import_resolution_change`).

The units loaded are quest.modules.graph's, and where their artifacts are under
a build directory quest.modules.artifacts.placement's. The self-hosted
counterpart is questlang/modules/resolution.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Optional

import quest.syntax.ast as ast
from quest.common.diagnostics import QuestCompilerError
from quest.modules.artifacts.manifest import ModuleManifest
from quest.modules.paths import (
    InterfaceDependency,
    canonicalize_interface_name,
    canonicalize_module_name,
    canonicalize_module_path,
    resolve_interface_file,
    resolve_interface_source_file,
    resolve_module_file,
    same_source,
    strip_unit_suffix,
)
from quest.modules.units import UnitKind, file_unit_kind
from quest.common.location import read_source


@dataclass(frozen=True)
class Roots:
    """What resolving an import and naming a unit depend on, besides the
    importing directory: the search paths, in order, the program's directory (a
    root of last resort for canonical names), and QUEST_LIB."""
    search_paths: tuple[Path, ...]
    program_dir: Optional[Path]
    quest_lib: Optional[str]

    @classmethod
    def of(cls, search_paths: Any, program_dir: Optional[Path]) -> Roots:
        return cls(tuple(Path(p) for p in search_paths or ()), program_dir, os.environ.get("QUEST_LIB"))


class Resolved:
    """An import path resolved from a directory: the unit it names and the names
    it has.

    Its names are computed when first asked for, since computing one checks that
    the unit's path is a valid name (canonicalize_module_path raises otherwise),
    which callers that only look for the file do not do.
    """

    def __init__(self, kind: UnitKind, path: str, from_dir: Optional[Path], roots: Roots, source: Optional[Path],
                 prebuilt: Optional[Path] = None) -> None:
        self.kind = kind
        # The path as written in the import
        self.path = path
        self.from_dir = from_dir
        self.roots = roots
        # The unit's source file (.int.quest or .mod.quest), or None for a
        # builtin or prebuilt unit
        self.source = source
        # For an interface without a source, the first .qi found on the search
        # path (a binary distribution, Rule 3 of docs/build-process.md §5), or
        # None
        self.prebuilt = prebuilt

    @property
    def unit_file(self) -> Optional[Path]:
        """The file the unit is loaded from when it has no fresher artifact: its
        source, else its prebuilt .qi."""
        return self.source if self.source is not None else self.prebuilt

    @cached_property
    def canonical_name(self) -> str:
        """The unit's canonical name, which keys it in a UnitGraph: its file's
        path relative to its root (docs/modules.md §2.3); for a unit without a
        file, the path imported (lowercased for an interface)."""
        search = list(self.roots.search_paths)
        if self.kind == UnitKind.INTERFACE:
            file = self.unit_file
            return canonicalize_module_path(file, search, self.roots.program_dir) if file else self.path.lower()
        return canonicalize_module_name(self.source, search, self.path, self.roots.program_dir)

    @cached_property
    def interface_name(self) -> str:
        """An interface's canonical name as importers record it (in typed
        programs and .qm manifests): its canonical path with the declared base
        name as the import writes it (util/Path), or for an interface without a
        source, the path imported."""
        return canonicalize_interface_name(
            self.source, list(self.roots.search_paths), self.path, self.roots.program_dir
        )

    @cached_property
    def artifact_name(self) -> str:
        """The name an interface's artifacts are placed by under a build
        directory: its source's canonical name, or without a source the path
        imported, lowercased (unit_artifact_dir)."""
        if self.source is None:
            return self.path.lower()
        return canonicalize_module_path(self.source, list(self.roots.search_paths), self.roots.program_dir)

    def __repr__(self) -> str:
        return f"Resolved({self.kind.value} {self.path!r} from {self.from_dir} -> {self.source})"


class Resolver:
    """Resolves import paths to units, each (path, directory, roots) once.

    A resolver lives for one compilation session (a driver run, a pipeline
    execution, a build, one REPL input), during which the set of source files
    does not change; forget() starts a new one (UnitGraph.new_session).
    """

    def __init__(self) -> None:
        self._memo: dict[tuple[Any, ...], Resolved] = {}

    def forget(self) -> None:
        """Forgets every resolution, so that files created since are found."""
        self._memo.clear()

    def interface(self, path: str, from_dir: Optional[Path], roots: Roots) -> Resolved:
        """Resolves interface path `path` imported from from_dir: its
        .int.quest, or else a prebuilt .qi."""
        key = (UnitKind.INTERFACE, path, from_dir, roots)
        found = self._memo.get(key)
        if found is None:
            search = list(roots.search_paths)
            source = resolve_interface_source_file(path, from_dir, search)
            # Without a source, the first .qi on the search path, whatever its
            # ABI version (loading it reports an incompatible one)
            prebuilt = resolve_interface_file(path, from_dir, search) if source is None else None
            found = Resolved(UnitKind.INTERFACE, path, from_dir, roots, source, prebuilt)
            self._memo[key] = found
        return found

    def module(self, path: str, from_dir: Optional[Path], roots: Roots) -> Resolved:
        """Resolves module path `path` imported from from_dir: its .mod.quest,
        if it has one."""
        key = (UnitKind.MODULE, path, from_dir, roots)
        found = self._memo.get(key)
        if found is None:
            found = Resolved(
                UnitKind.MODULE, path, from_dir, roots, resolve_module_file(path, from_dir, list(roots.search_paths))
            )
            self._memo[key] = found
        return found

    def file(self, file: Path, roots: Roots) -> Resolved:
        """The unit in a file given directly (to the driver, or by a build that
        found it), rather than imported: its kind is the file's
        (file_unit_kind), and its canonical name is that of the file below its
        root."""
        key = ("file", file, roots)
        found = self._memo.get(key)
        if found is None:
            kind = file_unit_kind(file)
            found = Resolved(kind, strip_unit_suffix(file.name), file.parent, roots, file)
            self._memo[key] = found
        return found

    def interface_source(self, path: str, from_dir: Optional[Path], search_paths: Any) -> Optional[Path]:
        """The .int.quest interface path `path` imported from from_dir resolves
        to, or None."""
        return self.interface(path, from_dir, Roots.of(search_paths, None)).source

    def interface_dependencies(self, source: Path, search_paths: Any) -> list[InterfaceDependency]:
        """The interfaces the interface in source depends on: those it imports,
        those they import, and so on.

        Each import is resolved as compiling the importing interface resolves it
        (from its directory, then search_paths). Every import path of every
        importing directory appears once, in depth-first order. A unit compiled
        against an interface is compiled against all of these too: their types
        appear in the interface's signatures and in its generated header.
        """
        roots = Roots.of(search_paths, None)
        deps: list[InterfaceDependency] = []
        seen: set[tuple[str, str]] = set()
        visited = {source.resolve()}

        def visit(importer: Path) -> None:
            importer_dir = str(importer.parent.resolve())
            for path in interface_import_paths(importer):
                if (importer_dir, path) in seen:
                    continue
                seen.add((importer_dir, path))
                dep_src = self.interface(path, importer.parent, roots).source
                deps.append(InterfaceDependency(path=path, dir=importer_dir, source=str(dep_src) if dep_src else ""))
                if dep_src is not None and dep_src.resolve() not in visited:
                    visited.add(dep_src.resolve())
                    visit(dep_src)

        visit(source)
        return deps


def resolve_interface(name: str, env: Any) -> Resolved:
    """Resolves interface path `name` as env, a type-checking Environment,
    imports it: from env.current_dir, with its search paths and program
    directory (docs/modules.md §2.2)."""
    return env.units.resolver.interface(name, env.current_dir, Roots.of(env.include_paths, env.program_dir))


def resolve_module(name: str, env: Any) -> Resolved:
    """Resolves module path `name` as env, a type-checking Environment, imports
    it: from env.current_dir, with its search paths and program directory
    (docs/modules.md §2.2)."""
    return env.units.resolver.module(name, env.current_dir, Roots.of(env.include_paths, env.program_dir))


def fresh_interface_qi(resolved: Resolved) -> Optional[Path]:
    """The file an interface is loaded from when it has no artifacts of its own
    in a build directory: a fresh .qi on the search path if there is one, else
    its source (or prebuilt .qi), as resolve_interface_file finds it.

    Unlike the resolution, this depends on artifacts, which a compilation
    writes, so it is looked up each time.
    """
    if resolved.source is None:
        return resolved.prebuilt
    return resolve_interface_file(resolved.path, resolved.from_dir, list(resolved.roots.search_paths))


# The interface paths each interface source imports, by resolved path and
# modification time.
_interface_imports_cache: dict[tuple[Path, int], list[str]] = {}


def interface_import_paths(source: Path) -> list[str]:
    """The interface paths an interface source file imports, as written: the
    edges out of its unit.

    A file that cannot be read or parsed imports nothing here; compiling it
    reports why.
    """
    from quest.syntax.grammar import parse_quest_program
    from quest.common.location import SourceMap
    from quest.syntax.tokenizer import Tokenizer

    try:
        key = (source.resolve(), source.stat().st_mtime_ns)
    except OSError:
        return []
    cached = _interface_imports_cache.get(key)
    if cached is not None:
        return cached
    paths: list[str] = []
    try:
        text = read_source(source)
        prog = parse_quest_program(Tokenizer(text, str(source)).tokenize_all(), SourceMap(text, str(source)))
        if isinstance(prog, ast.Program) and len(prog.phrases) == 1 and isinstance(prog.phrases[0], ast.InterfaceDecl):
            paths = [imp.effective_interface_path for imp in prog.phrases[0].imports]
    except (OSError, QuestCompilerError):
        paths = []
    _interface_imports_cache[key] = paths
    return paths


def import_resolution_change(
    manifest: ModuleManifest,
    current_dir: Optional[Path],
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
    resolver: Optional[Resolver] = None,
) -> Optional[str]:
    """Says how a unit's recorded imports would now resolve differently, or
    returns None if they would not.

    Each interface and module path the unit imported is resolved again as the
    unit's compilation resolves it (from the unit's directory current_dir, then
    include_paths) and canonicalized against the same roots. A different source
    file or canonical name (after a change of include paths, or a new file
    earlier on the search path) means the unit was compiled against other code
    than it would be now (docs/build-process.md §7.1). An interface the unit
    depends on through another interface's imports is resolved from that
    interface's directory, recorded with it. Imports recorded without a path (by
    manifests that predate recording it) cannot be checked and are skipped.
    """
    resolver = resolver or Resolver()
    roots = Roots.of(include_paths, program_dir)
    for iface in manifest.imported_interfaces:
        if not iface.path:
            continue
        found = resolver.interface(iface.path, Path(iface.dir) if iface.dir else current_dir, roots)
        src = found.source
        if not same_source(src, iface.source):
            return f"interface '{iface.path}' now resolves to {src or 'no source'}, not {iface.source or 'no source'}"
        if found.interface_name != iface.name:
            return f"interface '{iface.path}' is now named '{found.interface_name}', not '{iface.name}'"
    for mod in manifest.imported_modules:
        if not mod.path:
            continue
        found = resolver.module(mod.path, current_dir, roots)
        src = found.source
        if not same_source(src, mod.source):
            return f"module '{mod.path}' now resolves to {src or 'no source'}, not {mod.source or 'no source'}"
        if found.canonical_name != mod.name:
            return f"module '{mod.path}' is now named '{found.canonical_name}', not '{mod.name}'"
    return None
