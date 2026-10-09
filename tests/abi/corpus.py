"""The ABI corpus: generated interface artifacts that pin the artifact contract (docs/build-process.md §5.2.3).

The corpus is generated from a frozen snapshot of the interfaces in lib/ and questlang/ (tests/abi/inputs), so
that it changes only when the compiler's output for the same input changes, not when the library evolves. It holds
each interface's generated .qi file and C header, normalized so that only contract-relevant content remains (no
producer stamp, no comments), plus a digest of the runtime interface (runtime/quest_runtime.h) and the ABI version
the corpus was generated with. tests/python/test_abi_corpus.py regenerates it and fails if it changed while
ABI_VERSION did not.

    python tests/abi/corpus.py --update          # after bumping ABI_VERSION: regenerate the corpus
    python tests/abi/corpus.py --refresh-inputs  # re-snapshot lib/ and questlang/ interfaces, then regenerate
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.build.abi import ABI_VERSION  # noqa: E402
from quest.interface_compiler import compile_interface_file  # noqa: E402

ABI_DIR = Path(__file__).resolve().parent
CORPUS_DIR = ABI_DIR / "corpus"
INPUTS_DIR = ABI_DIR / "inputs"
# Snapshot layout mirrors the search roots: inputs/lib/... (like lib/) and inputs/questlang/... (under the project).
SNAPSHOT_SOURCES = ((ROOT_DIR / "lib", INPUTS_DIR / "lib"), (ROOT_DIR / "questlang", INPUTS_DIR / "questlang"))
RUNTIME_HEADER = ROOT_DIR / "runtime" / "quest_runtime.h"


def _normalize_qi(text: str) -> str:
    data = json.loads(text)
    value = data.get("value", {})
    value.pop("producer", None)
    value.pop("abi", None)
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _normalize_header(text: str) -> str:
    without_comments = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    lines = [line.rstrip() for line in without_comments.splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def generate() -> dict[str, str]:
    """Returns the corpus as {relative path: content}."""
    corpus: dict[str, str] = {}
    with tempfile.TemporaryDirectory() as tmp:
        build_dir = Path(tmp)
        include_paths = [INPUTS_DIR / "lib", INPUTS_DIR]
        for src in sorted(INPUTS_DIR.rglob("*.int.quest")):
            compile_interface_file(src, include_paths=include_paths, build_dir=build_dir)
        for artifact in sorted(build_dir.rglob("*")):
            if not artifact.is_file():
                continue
            rel = artifact.relative_to(build_dir).as_posix()
            text = artifact.read_text(encoding="utf-8")
            if artifact.suffix == ".qi":
                corpus[rel] = _normalize_qi(text)
            elif artifact.suffix == ".h":
                corpus[rel] = _normalize_header(text)
    corpus["quest_runtime.h.sha256"] = hashlib.sha256(RUNTIME_HEADER.read_bytes()).hexdigest() + "\n"
    corpus["ABI_VERSION"] = f"{ABI_VERSION}\n"
    return corpus


def read_checked_in() -> dict[str, str]:
    if not CORPUS_DIR.is_dir():
        return {}
    return {
        p.relative_to(CORPUS_DIR).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(CORPUS_DIR.rglob("*"))
        if p.is_file()
    }


def refresh_inputs() -> None:
    if INPUTS_DIR.exists():
        shutil.rmtree(INPUTS_DIR)
    for source_root, snapshot_root in SNAPSHOT_SOURCES:
        for src in sorted(source_root.rglob("*.int.quest")):
            dest = snapshot_root / src.relative_to(source_root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)


def update() -> None:
    if CORPUS_DIR.exists():
        shutil.rmtree(CORPUS_DIR)
    for rel, content in generate().items():
        path = CORPUS_DIR / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] in (["--update"], ["--refresh-inputs"]):
        if sys.argv[1] == "--refresh-inputs":
            refresh_inputs()
            print(f"Snapshotted interfaces into {INPUTS_DIR}")
        update()
        print(f"Wrote ABI corpus for ABI version {ABI_VERSION} to {CORPUS_DIR}")
    else:
        print(__doc__)
        sys.exit(2)
