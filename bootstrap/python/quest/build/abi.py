"""The artifact contract (ABI) version recorded in every .qi, .qm, and generated header.

Artifacts are reused only when they record the running compiler's ABI_VERSION (docs/build-process.md §5.2).
The version covers the .qi/.qm formats and the type strings in .qi files, the C representation of Quest
types, symbol name mangling and calling conventions, and the runtime interface (runtime/quest_runtime.h).
Bump it whenever any of these change incompatibly; tests/python/test_abi_corpus.py fails until you do.

The self-hosted compiler declares the same constant; if it gains a Makefile, that should generate its
copy from this file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ABI_VERSION = 9

# The compiler that wrote an artifact: informational, for diagnostics only.
PRODUCER = "quest-bootstrap 0.1"


def header_stamp() -> str:
    """The first line of every generated interface header."""
    return f"/* quest abi {ABI_VERSION} producer {PRODUCER} */"


def recorded_abi(artifact: Path) -> Optional[int]:
    """The ABI version recorded in a .qi or .qm file, or None if it records none or cannot be read."""
    try:
        data = json.loads(Path(artifact).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("value"), dict):  # .qi: a serialized dynamic value
        data = data["value"]
    abi = data.get("abi") if isinstance(data, dict) else None
    return abi if isinstance(abi, int) and not isinstance(abi, bool) else None


def has_current_abi(artifact: Path) -> bool:
    return recorded_abi(artifact) == ABI_VERSION


def incompatible_artifact_message(artifact: Path) -> str:
    found = recorded_abi(artifact)
    found_str = f"ABI version {found}" if found is not None else "no ABI version"
    return (
        f"Precompiled artifact '{artifact}' records {found_str}, but this compiler requires ABI version "
        f"{ABI_VERSION}, and its source is not available to rebuild it"
    )
