"""The C headers of interfaces (`.int.h`) as the build keeps them: written beside
each interface's .qi, from the interface as compiled, by C compilation when it
needs it: compiling an interface file (compile_interface_with_header), or a
module, whose C translation includes its interface's header
(ensure_imported_interface_header). A header is up to date when it is at least
as new as its .qi, which is rebuilt whenever the interface's source or an
interface it depends on changes (docs/build-process.md §5). A header's text is
codegen/c/headers.py's.

The self-hosted counterpart is questlang/build/headers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from quest.common.diagnostics import at_import, in_unit
from quest.types.env import Environment
from quest.modules.graph import Resolved, Resolver, Roots
from quest.modules.artifacts.interface_compiler import (
    CompiledInterface,
    compile_interface_file,
    ensure_resolved_interface_artifacts,
)
from quest.modules.loader import resolve_interface, resolved_artifact_root
from quest.modules.paths import canonicalize_interface_name
from quest.codegen.c.headers import compile_interface_to_header


def interface_header_file(qi_file: Path) -> Path:
    """The C header beside an interface's .qi (`util/path.qi` and
    `util/path.int.h`)."""
    return qi_file.with_name(f"{qi_file.name[:-len('.qi')]}.int.h")


def header_is_current(qi_file: Path, h_file: Path) -> bool:
    """Whether an interface's header is up to date: it was written from the
    interface its .qi describes, after the .qi (which is rewritten whenever the
    interface changes, docs/build-process.md §5)."""
    return h_file.is_file() and qi_file.is_file() and h_file.stat().st_mtime >= qi_file.stat().st_mtime


def write_interface_header(
    compiled: CompiledInterface,
    build_dir: Optional[Path],
    program_dir: Optional[Path],
    resolver: Optional[Resolver] = None,
) -> Path:
    """Writes a compiled interface's header beside its .qi, and returns it.

    With a build directory, the headers of the interfaces it imports, which it
    #includes, are brought up to date there first, including those of builtin
    interfaces that are never loaded from source. resolver resolves those
    imports (a new one if None).
    """
    resolver = resolver or Resolver()
    if build_dir is not None:
        build_root = Path(build_dir).resolve()
        roots = Roots.of(compiled.include_paths, program_dir)
        with in_unit(compiled.source_map):
            for imp in compiled.decl.imports:
                with at_import(imp.offset, compiled.source_map):
                    ensure_resolved_interface_header(
                        resolver.interface(imp.effective_interface_path, compiled.source.parent, roots),
                        build_root, resolver,
                    )
    h_file = interface_header_file(compiled.qi_file)
    canonical_name = canonicalize_interface_name(compiled.source, list(compiled.include_paths), compiled.decl.name)
    h_file.parent.mkdir(parents=True, exist_ok=True)
    h_file.write_text(compile_interface_to_header(compiled.decl, compiled.scope, canonical_name), encoding="utf-8")
    return h_file


def compile_interface_with_header(
    file_path: Path,
    output_dir: Optional[Path] = None,
    include_paths: Optional[list[Path]] = None,
    build_dir: Optional[Path] = None,
    program_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Compiles an interface file to its .qi and its C header, as `quest -c
    x.int.quest` does, writing the headers of the interfaces compiled because it
    imports them too. Returns (header, qi)."""
    resolver = Resolver()

    def write(compiled: CompiledInterface) -> None:
        write_interface_header(compiled, build_dir, program_dir, resolver)

    compiled = compile_interface_file(
        file_path, output_dir=output_dir, include_paths=include_paths, build_dir=build_dir, program_dir=program_dir,
        on_compiled=write, resolver=resolver,
    )
    return interface_header_file(compiled.qi_file), compiled.qi_file


def ensure_interface_header(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
    build_dir: Path,
    program_dir: Optional[Path] = None,
) -> tuple[Path, Path]:
    """Brings interface `name`'s .qi and C header under build_dir up to date,
    resolving the import of `name` from current_dir with include_paths
    (ensure_resolved_interface_header)."""
    resolver = Resolver()
    resolved = resolver.interface(name, current_dir, Roots.of(include_paths, program_dir))
    return ensure_resolved_interface_header(resolved, build_dir, resolver)


def ensure_resolved_interface_header(
    resolved: Resolved, build_dir: Path, resolver: Optional[Resolver] = None
) -> tuple[Path, Path]:
    """Brings a resolved interface's .qi and C header under build_dir up to
    date, with the headers it includes, and returns (qi, header). The files may
    not exist if the interface has neither a source nor prebuilt artifacts (a
    builtin); without a source, the header is used as found (Rule 3).

    An interface rebuilt for its .qi gets its header at the same time. A header
    that is missing or older than a fresh .qi is written from the interface
    elaborated again, leaving the .qi (and so whatever depends on it) untouched,
    unless the .qi was found outside the build directory (from a standalone
    compilation): then both are rebuilt in the build directory rather than
    written into the source tree.
    """
    resolver = resolver or Resolver()
    program_dir = resolved.roots.program_dir

    def write(compiled: CompiledInterface) -> None:
        write_interface_header(compiled, build_dir, program_dir, resolver)

    artifacts = ensure_resolved_interface_artifacts(resolved, build_dir, on_compiled=write, resolver=resolver)
    h_file = interface_header_file(artifacts.qi_file)
    if artifacts.source is None or header_is_current(artifacts.qi_file, h_file):
        return artifacts.qi_file, h_file
    in_build_dir = artifacts.qi_file.parent.resolve() == artifacts.target_dir.resolve()
    artifacts.target_dir.mkdir(parents=True, exist_ok=True)
    compiled = compile_interface_file(
        artifacts.source, output_dir=artifacts.target_dir, include_paths=list(artifacts.search_paths),
        build_dir=build_dir, program_dir=program_dir, write_qi=not in_build_dir, resolver=resolver,
    )
    return compiled.qi_file, write_interface_header(compiled, build_dir, program_dir, resolver)


def ensure_imported_interface_header(name: str, env: Environment) -> Optional[Path]:
    """Brings the C header of interface `name`, as env imports it from
    env.current_dir, up to date where env loads the interface's .qi from (the
    build directory, or beside the source in a standalone compilation), and
    returns it; None when env elaborates interfaces from source."""
    resolved = resolve_interface(name, env)
    root = resolved_artifact_root(env, resolved)
    if root is None:
        return None
    return ensure_resolved_interface_header(resolved, root, env.units.resolver)[1]
