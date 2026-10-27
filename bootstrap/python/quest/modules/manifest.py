"""Quest Module Manifest (.qm) serialization and deserialization.

A .qm file records the build metadata for an implementation module (.mod.quest)
or main routine (.quest), tracking imported modules and interface dependencies.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from quest.config.abi import ABI_VERSION, PRODUCER


@dataclass
class ImportedModuleRef:
    """Reference to an imported module and its declared interface.

    source is the module's source file as the importer found it, or "" if it has
    none (a builtin or prebuilt module). The build engine builds that file:
    units under different include roots can share a canonical name, so the name
    alone does not identify one. path is the module path the importer resolved
    (as written in its import, or the name of an implicitly used module), so
    that a later build can check that it still resolves to the same file.
    """
    name: str
    interface: str
    source: str = ""
    path: str = ""


@dataclass
class ImportedInterfaceRef:
    """Reference to an imported interface: its canonical name, source file, and
    timestamp.

    path is the interface path the importer resolved (as written in its import),
    so that a later build can check that it still resolves to the same file. dir
    is "" for an interface the unit imports itself (resolved from the unit's
    directory), and otherwise, for an interface the unit depends on through an
    imported interface's imports, the directory of the interface that imports
    it, which the path was resolved from.
    """
    name: str
    source: str
    mtime: float
    path: str = ""
    dir: str = ""


@dataclass
class ModuleManifest:
    """Build manifest stored in a .qm file."""
    name: str
    interface: Optional[str]
    source: str
    object: str
    imported_modules: list[ImportedModuleRef] = field(default_factory=list)
    imported_interfaces: list[ImportedInterfaceRef] = field(default_factory=list)
    # The artifact contract version and compiler the artifacts were produced
    # with (docs/build-process.md §5.2); None when read from a manifest that
    # records none.
    abi: Optional[int] = ABI_VERSION
    producer: Optional[str] = PRODUCER

    def to_dict(self) -> dict[str, Any]:
        """Serializes manifest to a dictionary."""
        return {
            "abi": self.abi,
            "producer": self.producer,
            "name": self.name,
            "interface": self.interface,
            "source": self.source,
            "object": self.object,
            "imported_modules": [asdict(m) for m in self.imported_modules],
            "imported_interfaces": [asdict(i) for i in self.imported_interfaces],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ModuleManifest:
        """Constructs a ModuleManifest from a dictionary."""
        imported_modules = [
            ImportedModuleRef(
                name=m["name"], interface=m["interface"], source=m.get("source", ""), path=m.get("path", "")
            )
            for m in data.get("imported_modules", [])
        ]
        imported_interfaces = [
            ImportedInterfaceRef(
                name=i["name"],
                source=i.get("source", ""),
                mtime=float(i.get("mtime", 0.0)),
                path=i.get("path", ""),
                dir=i.get("dir", ""),
            )
            for i in data.get("imported_interfaces", [])
        ]
        return cls(
            name=data["name"],
            interface=data.get("interface"),
            source=data.get("source", ""),
            object=data.get("object", ""),
            imported_modules=imported_modules,
            imported_interfaces=imported_interfaces,
            abi=data.get("abi") if isinstance(data.get("abi"), int) else None,
            producer=data.get("producer"),
        )


def write_qm(manifest: ModuleManifest, path: Path) -> None:
    """Writes a ModuleManifest to a .qm JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest.to_dict(), f, indent=2)
        f.write("\n")


def read_qm(path: Path) -> Optional[ModuleManifest]:
    """Reads a ModuleManifest from a .qm JSON file, or None if unreadable."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ModuleManifest.from_dict(data)
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        return None


def is_manifest_stale(manifest: ModuleManifest, qm_path: Path) -> bool:
    """Whether a unit's manifest says that its artifacts are out of date; the
    checks on the artifacts' own files are unit_staleness's.

    They are out of date if any of these holds:

    - The manifest was written by a compiler of another ABI version
      (config/abi.py), whose artifacts lay out data or make calls in other
      ways, so that this compiler cannot link with them.
    - The object file it records is missing.
    - The source it records exists and is newer than the manifest or the
      object file.
    - An interface the unit was compiled against, which it imports directly or
      through other interfaces, has a source newer than the manifest: the
      unit's C may depend on what it declared.

    A manifest that records no source, or a source that does not exist, is
    that of a prebuilt unit distributed without its source (an object and its
    .qm), which is up to date as long as its object and ABI version are."""
    if manifest.abi != ABI_VERSION:
        return True
    obj_path = Path(manifest.object)
    if not obj_path.is_file():
        return True

    src_path = Path(manifest.source) if manifest.source else None
    if src_path and src_path.is_file():
        try:
            qm_mtime = qm_path.stat().st_mtime
            if src_path.stat().st_mtime > qm_mtime:
                return True
            if src_path.stat().st_mtime > obj_path.stat().st_mtime:
                return True
        except OSError:
            return True
    elif not src_path or not src_path.exists():
        # Precompiled / binary mode: if .qm and .o exist without source, it is
        # up to date
        return False

    # Transitive interface staleness check
    try:
        qm_mtime = qm_path.stat().st_mtime
        for iface_ref in manifest.imported_interfaces:
            if iface_ref.source:
                iface_src = Path(iface_ref.source)
                if iface_src.is_file() and iface_src.stat().st_mtime > qm_mtime:
                    return True
    except OSError:
        return True

    return False


def unit_staleness(
    source: Path,
    qm_path: Path,
    c_path: Path,
    o_path: Path,
    imports_changed: Optional[Callable[[ModuleManifest], Optional[str]]] = None,
) -> Optional[str]:
    """Returns why a unit with a source file must be recompiled, or None if its
    artifacts are up to date.

    Up to date means: the .qm, .c, and .o exist and are no older than the source
    (and the .o no older than the .c), and the manifest records this source, the
    current ABI version, and no newer interface (docs/build-process.md §5.2,
    §7.1). Artifacts are named by canonical unit name only, so the recorded
    source tells a unit's artifacts from those of a same-named unit elsewhere.

    imports_changed, when given, says why the unit's imports would now resolve
    to other files than the manifest records (for example after a change of
    include paths), or returns None if they would not
    (graph.import_resolution_change).
    """
    if not qm_path.is_file() or not c_path.is_file() or not o_path.is_file():
        return f"missing artifacts in {qm_path.parent}"
    src_mtime = source.stat().st_mtime
    if (
        src_mtime > qm_path.stat().st_mtime
        or src_mtime > c_path.stat().st_mtime
        or c_path.stat().st_mtime > o_path.stat().st_mtime
    ):
        return "source file newer than artifacts"
    manifest = read_qm(qm_path)
    if manifest is None:
        return f"cannot parse {qm_path}"
    if not manifest.source or Path(manifest.source).resolve() != source.resolve():
        return f"artifacts built from a different source ({manifest.source or 'none recorded'})"
    if is_manifest_stale(manifest, qm_path):
        return "manifest indicates stale"
    if imports_changed is not None:
        return imports_changed(manifest)
    return None
