"""Where a unit's artifacts are under a build directory (docs/build-process.md
§3.2): an interface's .qi, and a module's .qm, .mod.c, and .o, by the unit's
canonical name, or beside its source; and whether a module's are fresh. Their
staleness rules are in interface_compiler (interfaces) and manifest (modules).

The self-hosted counterpart is questlang/modules/artifacts/placement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from quest.config import CompilerOptions
from quest.modules.artifacts.manifest import ModuleManifest, unit_staleness
from quest.modules.resolution import Resolver, import_resolution_change


def unit_artifact_dir(build_dir: Path, canonical_name: str) -> Path:
    """The directory under build_dir that holds the artifacts of the unit named
    canonical_name: its canonical path's directory (docs/build-process.md
    §3.2)."""
    return build_dir / Path(canonical_name).parent if "/" in canonical_name else build_dir


def artifact_stem(canonical_name: str) -> str:
    """The base name, without suffix, of the artifacts of the unit named
    canonical_name."""
    return Path(canonical_name).name.lower()


def interface_qi_file(build_dir: Path, canonical_name: str) -> Path:
    """Where the .qi of the interface named canonical_name is under
    build_dir."""
    return unit_artifact_dir(build_dir, canonical_name) / f"{artifact_stem(canonical_name)}.qi"


@dataclass(frozen=True)
class ModuleArtifacts:
    """A module's artifacts in one directory: its manifest, its C translation,
    and its object."""
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


def has_fresh_module_artifacts(
    file_path: Path,
    canon_name: str,
    target: Optional[Union[CompilerOptions, Any]],
    resolver: Optional[Resolver] = None,
) -> bool:
    """True if module source file_path has up-to-date .qm/.mod.c/.o in the build
    directory or beside it.

    Up to date includes its imports still resolving, with the current include
    paths, to the files it was built against.
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
