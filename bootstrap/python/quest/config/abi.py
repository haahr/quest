"""The artifact contract (ABI) version recorded in every .qi, .qm, and generated
header.

Artifacts are reused only when they record the running compiler's ABI_VERSION
(docs/build-process.md §5.2). The version covers the .qi/.qm formats and the
type strings in .qi files, the C representation of Quest types, symbol name
mangling and calling conventions, and the runtime interface
(runtime/quest_runtime.h). Bump it whenever any of these change incompatibly;
tests/python/test_abi_corpus.py fails until you do.

The self-hosted compiler declares the same constant, bumped when either
compiler's contract changes (tests/python/test_abi_version.py checks that they
agree), but each compiler uses only the artifacts it wrote (PRODUCER,
has_current_abi). If the self-hosted compiler gains a Makefile, it should
generate its copy from this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ABI_VERSION = 47

# The compiler that wrote an artifact: this one uses only its own.
PRODUCER = "quest-bootstrap 0.1"


def header_stamp() -> str:
    """The first line of every generated interface header."""
    return f"/* quest abi {ABI_VERSION} producer {PRODUCER} */"


def _recorded_field(artifact: Path, key: str) -> object:
    """A top-level field of a .qi or .qm file, or None if it is absent or the
    file cannot be read."""
    try:
        data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("value"), dict):  # .qi: a serialized dynamic value
        data = data["value"]
    return data.get(key) if isinstance(data, dict) else None


def recorded_abi(artifact: Path) -> Optional[int]:
    """The ABI version recorded in a .qi or .qm file, or None if it records none
    or cannot be read."""
    abi = _recorded_field(artifact, "abi")
    return abi if isinstance(abi, int) and not isinstance(abi, bool) else None


def recorded_producer(artifact: Path) -> Optional[str]:
    """The compiler a .qi or .qm file records as having written it, or None if
    it records none or cannot be read."""
    producer = _recorded_field(artifact, "producer")
    return producer if isinstance(producer, str) else None


def has_current_abi(artifact: Path) -> bool:
    """Whether this compiler can use an artifact: one it wrote itself, for this
    ABI version. The self-hosted compiler shares the ABI version, but its
    artifacts are its own (docs/testing.md section 2.8), so each compiler
    rebuilds the other's."""
    return recorded_abi(artifact) == ABI_VERSION and recorded_producer(artifact) == PRODUCER


def built_from(artifact: Path, source: Path) -> bool:
    """True if a .qi or .qm file records source as the file it was built from.

    Artifacts are named by canonical unit name only, so a same-named unit
    elsewhere (another directory sharing the build directory, say) can leave
    artifacts that are newer than this unit's source but were not built from it.
    """
    recorded = _recorded_field(artifact, "source")
    return isinstance(recorded, str) and recorded != "" and Path(recorded).resolve() == Path(source).resolve()


def incompatible_artifact_message(artifact: Path) -> str:
    found = recorded_abi(artifact)
    if found == ABI_VERSION:
        producer = recorded_producer(artifact)
        found_str = f"producer '{producer}'" if producer is not None else "no producer"
        return (
            f"Precompiled artifact '{artifact}' records {found_str}, but this compiler is '{PRODUCER}', and its "
            "source is not available to rebuild it"
        )
    found_str = f"ABI version {found}" if found is not None else "no ABI version"
    return (
        f"Precompiled artifact '{artifact}' records {found_str}, but this compiler requires ABI version "
        f"{ABI_VERSION}, and its source is not available to rebuild it"
    )
