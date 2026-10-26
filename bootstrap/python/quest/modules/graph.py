"""The graph of program units (docs/build-process.md §2.1).

A program is made of units: the program itself (a main routine, or inline code), module files (.mod.quest),
interface files (.int.quest), and the standard library's units, some of which have no source. Each import names a
unit by a path, which is resolved from the importing unit's directory and then the search paths
(docs/modules.md §2.2), and each unit has one canonical name (§2.3), which identifies it everywhere after.

This module holds what every consumer of units shares, so that each computes it in one way:

- **Resolution** (`Resolver`, `Resolved`): an import path, resolved from a directory with given search paths and
  program directory, to the unit's file and its names. Resolutions are memoized: each import is resolved once per
  compilation session, and every consumer (the type checker's loading, the interface compiler, the module compiler's
  manifests, the build engine's queue and staleness checks, the interpreter) receives the same result. Resolution
  depends only on which source files exist, which a compilation never changes; artifacts, which it does write, are
  looked up when needed (`fresh_interface_qi`).
- **Units** (`Unit`) and their **type-checked forms**: the interfaces and modules an environment has loaded, by kind
  and canonical name, with their elaborated scopes and typed modules, and the values of the modules the interpreter
  has run (`UnitGraph`). Typed forms belong to one elaboration (they hold the symbols it minted), so each
  type-checking Environment has its own graph; the graphs of one session share a resolver. The REPL keeps one graph
  across its inputs, each a session, and rolls it back when an input fails.
- **Edges** (`interface_import_paths`, `interface_dependencies`): the interfaces an interface imports, resolved from
  its directory, and those they import in turn.
- **Artifacts** (`unit_artifact_dir`, `ModuleArtifacts`, `interface_qi_file`): where a unit's .qi, .qm, .mod.c, and
  .o are under a build directory. Their staleness rules are in interface_compiler (interfaces) and manifest (modules).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Union

import quest.syntax.ast as ast
from quest.config import CompilerOptions
from quest.diagnostics import QuestCompilerError
from quest.modules.manifest import ModuleManifest, unit_staleness
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
from quest.modules.units import unit_kind
from quest.syntax.sources import read_source

if TYPE_CHECKING:
    from quest.types.symbols import Scope


class UnitKind(Enum):
    """What a unit is: the program (never imported), a module, or an interface."""
    PROGRAM = "program"
    MODULE = "module"
    INTERFACE = "interface"


def file_unit_kind(path: Path) -> UnitKind:
    """The kind of the unit in a file, by its name: a .int.quest holds an interface, a .mod.quest a module, and any
    other file a program."""
    kind = unit_kind(path)
    if kind == "interface":
        return UnitKind.INTERFACE
    if kind == "module":
        return UnitKind.MODULE
    return UnitKind.PROGRAM


@dataclass(frozen=True)
class Roots:
    """What resolving an import and naming a unit depend on, besides the importing directory: the search paths, in
    order, the program's directory (a root of last resort for canonical names), and QUEST_LIB."""
    search_paths: tuple[Path, ...]
    program_dir: Optional[Path]
    quest_lib: Optional[str]

    @classmethod
    def of(cls, search_paths: Any, program_dir: Optional[Path]) -> Roots:
        return cls(tuple(Path(p) for p in search_paths or ()), program_dir, os.environ.get("QUEST_LIB"))


class Resolved:
    """An import path resolved from a directory: the unit it names and the names it has.

    Its names are computed when first asked for, since computing one checks that the unit's path is a valid name
    (canonicalize_module_path raises otherwise), which callers that only look for the file do not do.
    """

    def __init__(self, kind: UnitKind, path: str, from_dir: Optional[Path], roots: Roots, source: Optional[Path],
                 prebuilt: Optional[Path] = None) -> None:
        self.kind = kind
        # The path as written in the import
        self.path = path
        self.from_dir = from_dir
        self.roots = roots
        # The unit's source file (.int.quest or .mod.quest), or None for a builtin or prebuilt unit
        self.source = source
        # For an interface without a source, the first .qi found on the search path (a binary distribution, Rule 3
        # of docs/build-process.md §5), or None
        self.prebuilt = prebuilt

    @property
    def unit_file(self) -> Optional[Path]:
        """The file the unit is loaded from when it has no fresher artifact: its source, else its prebuilt .qi."""
        return self.source if self.source is not None else self.prebuilt

    @cached_property
    def canonical_name(self) -> str:
        """The unit's canonical name, which keys it in a UnitGraph: its file's path relative to its root
        (docs/modules.md §2.3); for a unit without a file, the path imported (lowercased for an interface)."""
        search = list(self.roots.search_paths)
        if self.kind == UnitKind.INTERFACE:
            file = self.unit_file
            return canonicalize_module_path(file, search, self.roots.program_dir) if file else self.path.lower()
        return canonicalize_module_name(self.source, search, self.path, self.roots.program_dir)

    @cached_property
    def interface_name(self) -> str:
        """An interface's canonical name as importers record it (in typed programs and .qm manifests): its canonical
        path with the declared base name as the import writes it (util/Path), or for an interface without a
        source, the path imported."""
        return canonicalize_interface_name(
            self.source, list(self.roots.search_paths), self.path, self.roots.program_dir
        )

    @cached_property
    def artifact_name(self) -> str:
        """The name an interface's artifacts are placed by under a build directory: its source's canonical name, or
        without a source the path imported, lowercased (unit_artifact_dir)."""
        if self.source is None:
            return self.path.lower()
        return canonicalize_module_path(self.source, list(self.roots.search_paths), self.roots.program_dir)

    def __repr__(self) -> str:
        return f"Resolved({self.kind.value} {self.path!r} from {self.from_dir} -> {self.source})"


class Resolver:
    """Resolves import paths to units, each (path, directory, roots) once.

    A resolver lives for one compilation session (a driver run, a pipeline execution, a build, one REPL input),
    during which the set of source files does not change; forget() starts a new one (UnitGraph.new_session).
    """

    def __init__(self) -> None:
        self._memo: dict[tuple[Any, ...], Resolved] = {}

    def forget(self) -> None:
        """Forgets every resolution, so that files created since are found."""
        self._memo.clear()

    def interface(self, path: str, from_dir: Optional[Path], roots: Roots) -> Resolved:
        """Resolves interface path `path` imported from from_dir: its .int.quest, or else a prebuilt .qi."""
        key = (UnitKind.INTERFACE, path, from_dir, roots)
        found = self._memo.get(key)
        if found is None:
            search = list(roots.search_paths)
            source = resolve_interface_source_file(path, from_dir, search)
            # Without a source, the first .qi on the search path, whatever its ABI version (loading it reports an
            # incompatible one)
            prebuilt = resolve_interface_file(path, from_dir, search) if source is None else None
            found = Resolved(UnitKind.INTERFACE, path, from_dir, roots, source, prebuilt)
            self._memo[key] = found
        return found

    def module(self, path: str, from_dir: Optional[Path], roots: Roots) -> Resolved:
        """Resolves module path `path` imported from from_dir: its .mod.quest, if it has one."""
        key = (UnitKind.MODULE, path, from_dir, roots)
        found = self._memo.get(key)
        if found is None:
            found = Resolved(
                UnitKind.MODULE, path, from_dir, roots, resolve_module_file(path, from_dir, list(roots.search_paths))
            )
            self._memo[key] = found
        return found

    def file(self, file: Path, roots: Roots) -> Resolved:
        """The unit in a file given directly (to the driver, or by a build that found it), rather than imported:
        its kind is the file's (file_unit_kind), and its canonical name is that of the file below its root."""
        key = ("file", file, roots)
        found = self._memo.get(key)
        if found is None:
            kind = file_unit_kind(file)
            found = Resolved(kind, strip_unit_suffix(file.name), file.parent, roots, file)
            self._memo[key] = found
        return found

    def interface_source(self, path: str, from_dir: Optional[Path], search_paths: Any) -> Optional[Path]:
        """The .int.quest interface path `path` imported from from_dir resolves to, or None."""
        return self.interface(path, from_dir, Roots.of(search_paths, None)).source

    def interface_dependencies(self, source: Path, search_paths: Any) -> list[InterfaceDependency]:
        """The interfaces the interface in source depends on: those it imports, those they import, and so on.

        Each import is resolved as compiling the importing interface resolves it (from its directory, then
        search_paths). Every import path of every importing directory appears once, in depth-first order. A unit
        compiled against an interface is compiled against all of these too: their types appear in the interface's
        signatures and in its generated header.
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
    """Resolves interface path `name` as env, a type-checking Environment, imports it: from env.current_dir, with
    its search paths and program directory (docs/modules.md §2.2)."""
    return env.units.resolver.interface(name, env.current_dir, Roots.of(env.include_paths, env.program_dir))


def resolve_module(name: str, env: Any) -> Resolved:
    """Resolves module path `name` as env, a type-checking Environment, imports it: from env.current_dir, with its
    search paths and program directory (docs/modules.md §2.2)."""
    return env.units.resolver.module(name, env.current_dir, Roots.of(env.include_paths, env.program_dir))


def fresh_interface_qi(resolved: Resolved) -> Optional[Path]:
    """The file an interface is loaded from when it has no artifacts of its own in a build directory: a fresh .qi
    on the search path if there is one, else its source (or prebuilt .qi), as resolve_interface_file finds it.

    Unlike the resolution, this depends on artifacts, which a compilation writes, so it is looked up each time.
    """
    if resolved.source is None:
        return resolved.prebuilt
    return resolve_interface_file(resolved.path, resolved.from_dir, list(resolved.roots.search_paths))


# The interface paths each interface source imports, by resolved path and modification time.
_interface_imports_cache: dict[tuple[Path, int], list[str]] = {}


def interface_import_paths(source: Path) -> list[str]:
    """The interface paths an interface source file imports, as written: the edges out of its unit.

    A file that cannot be read or parsed imports nothing here; compiling it reports why.
    """
    from quest.syntax.grammar import parse_quest_program
    from quest.syntax.sources import SourceMap
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


def unit_artifact_dir(build_dir: Path, canonical_name: str) -> Path:
    """The directory under build_dir that holds the artifacts of the unit named canonical_name: its canonical
    path's directory (docs/build-process.md §3.2)."""
    return build_dir / Path(canonical_name).parent if "/" in canonical_name else build_dir


def artifact_stem(canonical_name: str) -> str:
    """The base name, without suffix, of the artifacts of the unit named canonical_name."""
    return Path(canonical_name).name.lower()


def interface_qi_file(build_dir: Path, canonical_name: str) -> Path:
    """Where the .qi of the interface named canonical_name is under build_dir."""
    return unit_artifact_dir(build_dir, canonical_name) / f"{artifact_stem(canonical_name)}.qi"


@dataclass(frozen=True)
class ModuleArtifacts:
    """A module's artifacts in one directory: its manifest, its C translation, and its object."""
    qm: Path
    c: Path
    o: Path

    @classmethod
    def in_dir(cls, directory: Path, stem: str) -> ModuleArtifacts:
        return cls(directory / f"{stem}.qm", directory / f"{stem}.mod.c", directory / f"{stem}.o")

    @classmethod
    def under(cls, build_dir: Path, canonical_name: str) -> ModuleArtifacts:
        """The artifacts of the module named canonical_name under build_dir."""
        return cls.in_dir(unit_artifact_dir(build_dir, canonical_name), artifact_stem(canonical_name))

    def paths(self) -> tuple[Path, Path, Path]:
        """The .qm, .mod.c, and .o."""
        return (self.qm, self.c, self.o)


def import_resolution_change(
    manifest: ModuleManifest,
    current_dir: Optional[Path],
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
    resolver: Optional[Resolver] = None,
) -> Optional[str]:
    """Says how a unit's recorded imports would now resolve differently, or returns None if they would not.

    Each interface and module path the unit imported is resolved again as the unit's compilation resolves it (from
    the unit's directory current_dir, then include_paths) and canonicalized against the same roots. A different
    source file or canonical name (after a change of include paths, or a new file earlier on the search path) means
    the unit was compiled against other code than it would be now (docs/build-process.md §7.1). An interface the
    unit depends on through another interface's imports is resolved from that interface's directory, recorded with
    it. Imports recorded without a path (by manifests that predate recording it) cannot be checked and are skipped.
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


def has_fresh_module_artifacts(
    file_path: Path,
    canon_name: str,
    target: Optional[Union[CompilerOptions, Any]],
    resolver: Optional[Resolver] = None,
) -> bool:
    """True if module source file_path has up-to-date .qm/.mod.c/.o in the build directory or beside it.

    Up to date includes its imports still resolving, with the current include paths, to the files it was built
    against.
    """
    opts = target if isinstance(target, CompilerOptions) or target is None else target.options
    build_dir = opts.build_dir if opts is not None else None
    include_paths = list(opts.include_paths or []) if opts is not None else []
    program_dir = opts.program_dir if opts is not None else None
    if build_dir is not None:
        root = Path(build_dir).resolve()
        if root not in include_paths:
            include_paths.insert(0, root)

    def imports_changed(manifest: ModuleManifest) -> Optional[str]:
        return import_resolution_change(manifest, file_path.parent, include_paths, program_dir, resolver)

    stem = artifact_stem(canon_name)
    candidates = [ModuleArtifacts.in_dir(file_path.parent, stem)]
    if build_dir is not None:
        candidates.insert(0, ModuleArtifacts.under(Path(build_dir).resolve(), canon_name))
    return any(unit_staleness(file_path, a.qm, a.c, a.o, imports_changed) is None for a in candidates)


@dataclass(eq=False)
class Unit:
    """An interface or module an environment has loaded, with its type-checked forms.

    An interface has its scope once elaborated (from source or from its .qi). A module has its typed module once
    elaborated or synthesized from its interface, and an export scope when it is known only through its interface
    (separate compilation); precompiled marks a module typed through its interface alone (a prebuilt object, a
    module built separately, or one with fresh artifacts in a typecheck-only run). A module the interpreter has
    run has its value: the record of its members, made once per program (load_module_for_interpreter).
    """
    kind: UnitKind
    canonical_name: str
    scope: Optional[Scope] = None
    typed_module: Optional[Any] = None
    export_scope: Optional[Scope] = None
    precompiled: bool = False
    value: Optional[Any] = None

    def state(self) -> tuple[Any, ...]:
        return (self.scope, self.typed_module, self.export_scope, self.precompiled, self.value)


@dataclass
class UnitGraph:
    """The units one type-checking Environment has loaded, by kind and canonical name, and the resolver that
    resolves its imports.

    Loaded units are shared by canonical name (docs/modules.md §2.3): every importer of a file, through any path,
    gets the same unit, and so the same interface scope, export scope (with the same abstract types), typed module,
    and, once the interpreter has run it, value. The interpreter's RuntimeEnvironment holds the graph of the
    Environment that type checked its program (CompilerContext.runtime_env), the same object, so that the two never
    disagree about which units are loaded: restore changes the graph in place.

    A graph outlives a session when the REPL keeps it from one input to the next. Each input is a session of its
    own (new_session), and one that fails is rolled back (snapshot, restore), forgetting the units it loaded, typed
    forms and values alike, so that importing them again elaborates and runs them again.
    """
    resolver: Resolver = field(default_factory=Resolver)
    _units: dict[tuple[UnitKind, str], Unit] = field(default_factory=dict)

    def new_session(self) -> None:
        """Starts a new compilation session on this graph: imports are resolved again, so that files created since
        are found. Units already loaded stay loaded, as they were elaborated (the REPL starts one for each input)."""
        self.resolver.forget()

    def unit(self, kind: UnitKind, canonical_name: str) -> Unit:
        """The unit of this kind named canonical_name, added if not yet known."""
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
        """The scope of the loaded interface named canonical_name, if it has been loaded."""
        found = self.find(UnitKind.INTERFACE, canonical_name)
        return found.scope if found is not None else None

    def typed_module(self, canonical_name: str) -> Optional[Any]:
        """The typed module named canonical_name, if it has been loaded."""
        found = self.find(UnitKind.MODULE, canonical_name)
        return found.typed_module if found is not None else None

    def is_precompiled(self, name: str) -> bool:
        """Whether the module named name (its canonical name, or the name a source-less module is imported by) is
        typed through its interface alone."""
        found = self.find(UnitKind.MODULE, name)
        return found is not None and found.precompiled

    def interface_scopes(self) -> dict[str, Scope]:
        """The loaded interfaces' scopes, by canonical name."""
        return {u.canonical_name: u.scope for u in self._units.values() if u.kind == UnitKind.INTERFACE and u.scope}

    def export_scopes(self) -> dict[str, Scope]:
        """The export scopes of modules known through their interfaces, by canonical name."""
        return {
            u.canonical_name: u.export_scope
            for u in self._units.values()
            if u.kind == UnitKind.MODULE and u.export_scope is not None
        }

    def adopt(self, interface_scopes: dict[str, Scope], export_scopes: dict[str, Scope]) -> None:
        """Takes interfaces and export scopes another environment loaded (the standard library's, which are loaded
        once per process), replacing any of the same names."""
        for name, scope in interface_scopes.items():
            self.unit(UnitKind.INTERFACE, name).scope = scope
        for name, scope in export_scopes.items():
            self.unit(UnitKind.MODULE, name).export_scope = scope

    def add_prebuilt_objects(self, objects: list[Path], include_paths: Any) -> None:
        """Marks the modules of prebuilt object files given to the driver as typed through their interfaces alone,
        by their canonical names (against include_paths) and by their base names."""
        for obj in objects:
            self.unit(UnitKind.MODULE, canonicalize_module_path(obj, list(include_paths or ()))).precompiled = True
            self.unit(UnitKind.MODULE, obj.name.split(".")[0]).precompiled = True

    def snapshot(self) -> dict[tuple[UnitKind, str], tuple[Any, ...]]:
        """The units' typed forms and values, for restore (the REPL rolls back an input that failed)."""
        return {key: u.state() for key, u in self._units.items()}

    def restore(self, snap: dict[tuple[UnitKind, str], tuple[Any, ...]]) -> None:
        """Puts the units' typed forms and values back as snapshot found them, forgetting units loaded since. The
        graph is changed in place, so every holder of it (the interpreter's RuntimeEnvironment) sees the change."""
        self._units = {key: Unit(key[0], key[1], *state) for key, state in snap.items()}
