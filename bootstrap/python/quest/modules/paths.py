"""Quest Module and Interface File Path Resolution and Canonicalization.

Provides file-based path discovery, canonical hierarchical root calculations,
name mangling, and artifact freshness checking:
- Resolves interface files as <name.lower()>.int.quest or <name.lower()>.qi
- Resolves module files as <name.lower()>.mod.quest
- Resolves object files as <name.lower()>.o
- Canonical roots and paths relative to search roots (-I, QUEST_LIB, lib/)
- Enforces valid ASCII alphanumeric path component naming
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from quest.config.abi import built_from, has_current_abi
from quest.modules.manifest import ModuleManifest, unit_staleness
from quest.config import CompilerOptions
from quest.diagnostics import QuestCompilerError, QuestTypeError
from quest.syntax.tokens import TokenKind
from quest.syntax.tokenizer import Tokenizer

DEFAULT_PROJECT_DIR = Path(__file__).resolve().parents[4]
DEFAULT_LIB_DIR = (DEFAULT_PROJECT_DIR / "lib").resolve()

UNIT_SUFFIXES = (".int.quest", ".mod.quest", ".qi", ".o")

# Each directory and file name in a canonical name; anything else could not be mangled into C identifiers
# unambiguously (docs/modules.md §2.3, docs/name-mangling.md §4.1).
_NAME_COMPONENT = re.compile(r"[A-Za-z0-9]+")


@dataclass(frozen=True)
class InterfaceDependency:
    """An interface that an interface imports, directly or through the interfaces it imports.

    path is the interface path as written in the importing interface, dir the importing interface's directory (the
    path was resolved from it, by sibling search, before the include paths), and source the .int.quest it resolved
    to, or "" if none (a builtin or prebuilt interface). A .qi records the dependencies of its interface, so that it
    is stale when one of them changes or would resolve elsewhere (docs/build-process.md §5, Rule 1).
    """
    path: str
    dir: str
    source: str


def _same_file(found: Optional[Path], recorded: str) -> bool:
    """True if found, a resolved source or None, is the file recorded ("" for none)."""
    if found is None or not recorded:
        return found is None and not recorded
    return found.resolve() == Path(recorded).resolve()


def recorded_dependencies(qi_path: Path) -> Optional[list[InterfaceDependency]]:
    """The interface dependencies a .qi records, or None if it cannot be read or records none."""
    try:
        data = json.loads(Path(qi_path).read_text(encoding="utf-8"))
        deps = data["value"]["deps"]
        return [InterfaceDependency(path=d["path"], dir=d["dir"], source=d["source"]) for d in deps]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def dependency_change(
    deps: list[InterfaceDependency], include_paths: list[Path], artifact_mtime: float
) -> Optional[str]:
    """Says how an interface's recorded dependencies changed since an artifact built from them, or returns None.

    A dependency changed if its path would now resolve to a different source (from the directory recorded with it,
    then include_paths), or if its source is newer than the artifact.
    """
    for dep in deps:
        src = resolve_interface_source_file(dep.path, Path(dep.dir) if dep.dir else None, include_paths)
        if not _same_file(src, dep.source):
            return f"interface '{dep.path}' now resolves to {src or 'no source'}, not {dep.source or 'no source'}"
        if src is not None and src.stat().st_mtime > artifact_mtime:
            return f"imported interface {src} is newer"
    return None


def _dependencies_unchanged(qi_path: Path, include_paths: list[Path]) -> bool:
    """True if a .qi records its interface's dependencies and none has changed since it was built."""
    deps = recorded_dependencies(qi_path)
    return deps is not None and dependency_change(deps, include_paths, qi_path.stat().st_mtime) is None


def strip_unit_suffix(filename: str) -> str:
    """Strips recognized unit suffixes (.int.quest, .mod.quest, .qi, .o) from a filename."""
    for ext in UNIT_SUFFIXES:
        if filename.endswith(ext):
            return filename[: -len(ext)]
    return filename


def declared_module_name(file_path: Optional[Path], canon_name: str) -> str:
    """Returns the name declared by `module <name>` in file_path, else the last segment of canon_name."""
    fallback = canon_name.split("/")[-1]
    if file_path is None or not file_path.is_file():
        return fallback
    try:
        tokens = Tokenizer(file_path.read_text(encoding="utf-8"), str(file_path)).tokenize_all()
    except (OSError, QuestCompilerError):
        return fallback
    for tok, nxt in zip(tokens, tokens[1:]):
        if tok.kind == TokenKind.KW_MODULE:
            return nxt.lexeme
    return fallback


def is_c_compilation_mode(target: Optional[Union[CompilerOptions, Any]] = None) -> bool:
    """Checks whether the compiler options or environment specify actively compiling C code."""
    if target is None:
        return False
    if isinstance(target, CompilerOptions):
        return target.is_c_compilation_mode
    opts = getattr(target, "options", None)
    if isinstance(opts, CompilerOptions):
        return opts.is_c_compilation_mode
    return False


def is_typecheck_only(target: Optional[Union[CompilerOptions, Any]] = None) -> bool:
    """Checks whether compiler options specify stopping after typechecking in non-C mode."""
    if target is None:
        return False
    if isinstance(target, CompilerOptions):
        return target.is_typecheck_only
    opts = getattr(target, "options", None)
    if isinstance(opts, CompilerOptions):
        return opts.is_typecheck_only
    return False


def has_fresh_module_artifacts(
    file_path: Path,
    canon_name: str,
    target: Optional[Union[CompilerOptions, Any]],
) -> bool:
    """True if module source file_path has up-to-date .qm/.mod.c/.o in the build directory or beside it.

    Up to date includes its imports still resolving, with the current include paths, to the files it was built
    against.
    """
    opts = target if isinstance(target, CompilerOptions) else getattr(target, "options", None)
    build_dir = getattr(opts, "build_dir", None)
    include_paths = list(getattr(opts, "include_paths", None) or [])
    program_dir = getattr(opts, "program_dir", None)
    if build_dir is not None:
        root = Path(build_dir).resolve()
        if root not in include_paths:
            include_paths.insert(0, root)

    def imports_changed(manifest: ModuleManifest) -> Optional[str]:
        return import_resolution_change(manifest, file_path.parent, include_paths, program_dir)

    stem = Path(canon_name).name.lower()
    candidates = [file_path.parent]
    if build_dir is not None:
        root = Path(build_dir).resolve()
        candidates.insert(0, root / Path(canon_name).parent if "/" in canon_name else root)
    return any(
        unit_staleness(file_path, d / f"{stem}.qm", d / f"{stem}.mod.c", d / f"{stem}.o", imports_changed) is None
        for d in candidates
    )


def import_resolution_change(
    manifest: ModuleManifest,
    current_dir: Optional[Path],
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
) -> Optional[str]:
    """Says how a unit's recorded imports would now resolve differently, or returns None if they would not.

    Each interface and module path the unit imported is resolved again as the unit's compilation resolves it (from
    the unit's directory current_dir, then include_paths) and canonicalized against the same roots. A different
    source file or canonical name (after a change of include paths, or a new file earlier on the search path) means
    the unit was compiled against other code than it would be now (docs/build-process.md §7.1). An interface the
    unit depends on through another interface's imports is resolved from that interface's directory, recorded with
    it. Imports recorded without a path (by manifests that predate recording it) cannot be checked and are skipped.
    """
    for iface in manifest.imported_interfaces:
        if not iface.path:
            continue
        src = resolve_interface_source_file(iface.path, Path(iface.dir) if iface.dir else current_dir, include_paths)
        if not _same_file(src, iface.source):
            return f"interface '{iface.path}' now resolves to {src or 'no source'}, not {iface.source or 'no source'}"
        canon = canonicalize_interface_name(src, include_paths, iface.path, program_dir)
        if canon != iface.name:
            return f"interface '{iface.path}' is now named '{canon}', not '{iface.name}'"
    for mod in manifest.imported_modules:
        if not mod.path:
            continue
        src = resolve_module_file(mod.path, current_dir, include_paths)
        if not _same_file(src, mod.source):
            return f"module '{mod.path}' now resolves to {src or 'no source'}, not {mod.source or 'no source'}"
        canon = canonicalize_module_name(src, include_paths, mod.path, program_dir)
        if canon != mod.name:
            return f"module '{mod.path}' is now named '{canon}', not '{mod.name}'"
    return None


def resolve_interface_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds interface `name` on the search path: a fresh .qi if there is one, else its .int.quest.

    A .qi is fresh when it records this compiler's ABI version and the source it was built from, and is at
    least as new as that source (docs/build-process.md §5.2). Without a source, the first .qi found is returned
    whatever its ABI version; loading it reports an incompatible one.
    """
    source_file = resolve_interface_source_file(name, current_dir, include_paths)
    source_mtime = source_file.stat().st_mtime if source_file is not None else None

    stem = name.lower()
    dirs_to_check: list[Path] = []
    if current_dir is not None:
        dirs_to_check.append(current_dir)
    for inc in include_paths:
        dirs_to_check.append(Path(inc))
    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        dirs_to_check.append(Path(env_lib))
    if DEFAULT_LIB_DIR.is_dir():
        dirs_to_check.append(DEFAULT_LIB_DIR)
    if DEFAULT_PROJECT_DIR.is_dir():
        dirs_to_check.append(DEFAULT_PROJECT_DIR)

    for d in dirs_to_check:
        qi_candidate = d / f"{stem}.qi"
        if not qi_candidate.is_file():
            continue
        if source_mtime is None:
            return qi_candidate.resolve()
        if (
            has_current_abi(qi_candidate)
            and qi_candidate.stat().st_mtime >= source_mtime
            and built_from(qi_candidate, source_file)
            and _dependencies_unchanged(qi_candidate, include_paths)
        ):
            return qi_candidate.resolve()

    return source_file


def resolve_interface_source_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.int.quest in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.int.quest"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


def resolve_module_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.mod.quest in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.mod.quest"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


def resolve_object_file(
    name: str,
    current_dir: Optional[Path],
    include_paths: list[Path],
) -> Optional[Path]:
    """Finds <name.lower()>.o in current_dir, include_paths, or DEFAULT_LIB_DIR."""
    filename = f"{name.lower()}.o"
    if current_dir is not None:
        candidate = current_dir / filename
        if candidate.is_file():
            return candidate.resolve()

    for inc in include_paths:
        candidate = Path(inc) / filename
        if candidate.is_file():
            return candidate.resolve()

    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        candidate = Path(env_lib) / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_LIB_DIR.is_dir():
        candidate = DEFAULT_LIB_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    if DEFAULT_PROJECT_DIR.is_dir():
        candidate = DEFAULT_PROJECT_DIR / filename
        if candidate.is_file():
            return candidate.resolve()

    return None


def canonical_roots(include_paths: list[Path], program_dir: Optional[Path] = None) -> list[Path]:
    """Returns the directories canonical names are relative to, in the order canonicalize_module_path tries them.

    The include roots (QUEST_LIB, include paths, lib/, the project directory) come first, deepest first, then the
    program's directory, which names only the units under none of the include roots.
    """
    roots: list[Path] = []
    env_lib = os.environ.get("QUEST_LIB")
    if env_lib:
        roots.append(Path(env_lib).resolve())
    for inc in include_paths:
        roots.append(Path(inc).resolve())
    if DEFAULT_LIB_DIR.is_dir():
        roots.append(DEFAULT_LIB_DIR.resolve())
    if DEFAULT_PROJECT_DIR.is_dir():
        roots.append(DEFAULT_PROJECT_DIR.resolve())
    roots.sort(key=lambda p: len(p.parts), reverse=True)
    if program_dir is not None:
        roots.append(Path(program_dir).resolve())
    return list(dict.fromkeys(roots))


def canonicalize_module_path(
    file_path: Path,
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
) -> str:
    """Computes the canonical hierarchical name of the unit in file_path (e.g. 'util/path').

    The name is the file's path, without its suffix, relative to the first of canonical_roots that contains it
    (docs/modules.md §2.3); a file under none of them is named by its base name. It depends only on the file and
    the roots, not on the import that found it, so importers, the unit itself, manifests, and mangled C symbols
    all agree on it as long as they pass the same include paths and program directory.

    Raises QuestTypeError if a directory or file name in it contains anything but ASCII letters and digits.
    """
    resolved = file_path.resolve()
    parts = [resolved.name]
    for root in canonical_roots(include_paths, program_dir):
        try:
            parts = list(resolved.relative_to(root).parts)
        except ValueError:
            continue
        break
    parts[-1] = strip_unit_suffix(parts[-1])
    bad = [part for part in parts if not _NAME_COMPONENT.fullmatch(part)]
    if bad:
        raise QuestTypeError(
            f"Invalid module path '{'/'.join(parts)}' for '{resolved}': '{bad[0]}' contains characters other than "
            f"letters and digits, which are the only ones allowed in the directory and file names of interfaces "
            f"and modules"
        )
    return "/".join(parts)


def find_canonical_module_source(
    canon_name: str,
    include_paths: list[Path],
    program_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Finds the module source whose canonical name is canon_name, the inverse of canonicalize_module_path."""
    relative = f"{canon_name.lower()}.mod.quest"
    for root in canonical_roots(include_paths, program_dir):
        candidate = root / relative
        if candidate.is_file() and canonicalize_module_path(candidate, include_paths, program_dir) == canon_name:
            return candidate.resolve()
    return None


def canonicalize_interface_name(
    file_path: Optional[Path],
    include_paths: list[Path],
    declared_name: str,
    program_dir: Optional[Path] = None,
) -> str:
    """Computes canonical hierarchical interface name (e.g. 'util/Path')."""
    if file_path is None:
        return declared_name
    canon_mod = canonicalize_module_path(file_path, include_paths, program_dir)
    base_name = declared_name.split("/")[-1]
    if "/" in canon_mod:
        parent_dir = str(Path(canon_mod).parent)
        return f"{parent_dir}/{base_name}"
    if "/" in declared_name:
        return declared_name
    return base_name


def canonicalize_module_name(
    file_path: Optional[Path],
    include_paths: list[Path],
    raw_name: str,
    program_dir: Optional[Path] = None,
) -> str:
    """Computes canonical hierarchical module name (e.g. 'util/path')."""
    if file_path is None:
        return raw_name
    return canonicalize_module_path(file_path, include_paths, program_dir)


def canonical_import_name(
    mod_path: str,
    target: Union[CompilerOptions, Any],
    current_dir: Optional[Path] = None,
) -> str:
    """Returns the canonical name of the module an import in current_dir names mod_path.

    Builtin and source-less (precompiled) modules keep the name they are imported by.
    """
    if isinstance(target, CompilerOptions):
        cur = current_dir if current_dir is not None else target.current_dir
        inc = target.include_paths
        prog = target.program_dir
    else:
        cur = current_dir if current_dir is not None else getattr(target, "current_dir", None)
        inc = getattr(target, "include_paths", None)
        prog = getattr(target, "program_dir", None)
        opts = getattr(target, "options", None)
        if not inc and opts is not None:
            inc = opts.include_paths
        if prog is None and opts is not None:
            prog = opts.program_dir
        if cur is None and opts is not None:
            cur = opts.current_dir

    src = resolve_module_file(mod_path, cur, inc or [])
    return canonicalize_module_name(src, inc or [], mod_path, prog)
