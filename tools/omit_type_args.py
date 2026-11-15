"""Omits the written type arguments that inference finds, throughout
questlang/ (docs/type-system.md section 6.9's --report-inferable), in two
commits:

    tools/omit-type-args                  equal types (the default)
    tools/omit-type-args --mode exact     only the same type nodes, spelled as written
    tools/omit-type-args --no-commit      leave the edits uncommitted (the second pass's
                                          report is then of the first pass's edits)
    tools/omit-type-args --no-compare     skip the comparison at the end

1. The compiler is built and reports (--report-inferable) over the driver,
   which imports all of questlang/.
2. The calls inferable from their value arguments alone lose their type
   arguments, by the byte ranges the report gives; the compiler is built from
   the result (it must build, since each call's type is unchanged); commit.
3. The compiler reports again, and the calls inferable only with their
   expected type lose theirs. A call can lose its expected type when the call
   around it loses its own type arguments, so the compiler is built, and the
   call around each error it reports is restored, until it builds; commit.
4. tools/compare-codegen compares every unit's arm64 assembly with the
   starting commit's, by one compiler: anything but source positions differing
   means some pass tells the old spelling from the new.

The working tree must be clean. The exit status is 0 when every step
succeeds and the code compares equal, 1 when the code differs, and 2 when a
step fails.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
STAGE2 = ROOT_DIR / ".build" / "quest-stages" / "stage2" / "quest"
DRIVER = "questlang/driver/main.quest"
FROM_ARGUMENTS = "from the arguments"
WITH_EXPECTED = "with the expected type"
REPORT = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+):(?P<col>\d+): type arguments can be inferred "
                    r"(?P<kind>from the arguments|with the expected type) \[(?P<start>\d+) (?P<end>\d+)\]$")
ERROR = re.compile(r"^(?P<file>[^:\s]+\.quest):(?P<line>\d+):(?P<col>\d+): error", re.M)


@dataclass(frozen=True)
class Call:
    """A reported call: its file (relative to the root), the byte offset where
    it starts, its type arguments' byte range, and its kind."""
    file: str
    offset: int
    start: int
    end: int
    kind: str


def line_starts(data: bytes) -> list[int]:
    """The byte offset of each line's start, line 1 first."""
    starts = [0]
    for i, b in enumerate(data):
        if b == 0x0A:
            starts.append(i + 1)
    return starts


def parse_report(text: str, root: Path, read=lambda path: path.read_bytes()) -> list[Call]:
    """The calls a report lists in root's questlang/, each once."""
    calls: set[Call] = set()
    starts: dict[str, list[int]] = {}
    for line in text.splitlines():
        m = REPORT.match(line)
        if not m:
            continue
        path = Path(m["file"])
        if path.is_absolute():
            try:
                path = path.relative_to(root)
            except ValueError:
                continue
        file = path.as_posix()
        if not file.startswith("questlang/"):
            continue
        if file not in starts:
            starts[file] = line_starts(read(root / file))
        offset = starts[file][int(m["line"]) - 1] + int(m["col"]) - 1
        calls.add(Call(file, offset, int(m["start"]), int(m["end"]), m["kind"]))
    return sorted(calls, key=lambda c: (c.file, c.start))


@dataclass
class Edited:
    """A file's text with some calls' type arguments deleted, and where each
    call starts in it."""
    data: bytes
    offsets: dict[Call, int]


def omit(data: bytes, calls: list[Call]) -> Edited:
    """data without the type arguments of calls, which are all in it."""
    out = bytearray()
    pos = 0
    deleted: list[tuple[int, int]] = []
    for call in sorted(calls, key=lambda c: c.start):
        if call.start < pos or data[call.start:call.start + 1] != b":":
            raise ValueError(f"{call.file}: no type arguments at byte {call.start}")
        out += data[pos:call.start]
        deleted.append((call.start, call.end))
        pos = call.end
    out += data[pos:]
    offsets = {c: c.offset - sum(e - s for s, e in deleted if e <= c.offset) for c in calls}
    return Edited(bytes(out), offsets)


def enclosing(edited: Edited, offset: int) -> Call | None:
    """The call whose start most closely precedes offset in the edited text:
    the one an error at offset is most likely in."""
    before = [(start, call) for call, start in edited.offsets.items() if start <= offset]
    return max(before, key=lambda pair: pair[0])[1] if before else None


def run(*command: str, check: bool = True) -> subprocess.CompletedProcess:
    process = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True)
    if check and process.returncode != 0:
        sys.exit(f"omit-type-args: {' '.join(command)} failed:\n{process.stdout}{process.stderr}")
    return process


def build() -> subprocess.CompletedProcess:
    return run(str(ROOT_DIR / "quest"), "-e", "ok", check=False)


def report(mode: str) -> list[Call]:
    with tempfile.TemporaryDirectory(prefix="omit-type-args-") as tmp:
        process = run(str(STAGE2), "compile", f"--report-inferable={mode}", "-j", "8", "--build-dir",
                      str(Path(tmp) / "build"), "-o", str(Path(tmp) / "quest"), DRIVER)
    return parse_report(process.stderr, ROOT_DIR)


def write(calls: list[Call], base: dict[str, bytes]) -> dict[str, Edited]:
    """Each file of calls, edited from its text in base (read into base the
    first time), written."""
    by_file: dict[str, list[Call]] = {}
    for call in calls:
        by_file.setdefault(call.file, []).append(call)
    edited = {}
    for file, its in by_file.items():
        if file not in base:
            base[file] = (ROOT_DIR / file).read_bytes()
        edited[file] = omit(base[file], its)
        (ROOT_DIR / file).write_bytes(edited[file].data)
    return edited


def restore(base: dict[str, bytes]) -> None:
    for file, data in base.items():
        (ROOT_DIR / file).write_bytes(data)


def commit(message: str) -> None:
    run("git", "add", "-u", "questlang")
    run("git", "commit", "-q", "-m", message + "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mode", choices=("equal", "exact"), default="equal")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--no-compare", action="store_true")
    args = parser.parse_args()
    if run("git", "status", "--porcelain", "--untracked-files=no").stdout.strip():
        sys.exit("omit-type-args: the working tree has changes")
    base = run("git", "rev-parse", "HEAD").stdout.strip()

    # 1 and 2: the calls inferable from their arguments
    if build().returncode != 0:
        sys.exit("omit-type-args: the compiler does not build")
    first = [c for c in report(args.mode) if c.kind == FROM_ARGUMENTS]
    write(first, {})
    built = build()
    if built.returncode != 0:
        print(built.stdout + built.stderr, file=sys.stderr)
        return 2
    print(f"omit-type-args: {len(first)} calls inferable from their arguments", file=sys.stderr)
    if not args.no_commit and first:
        commit(f"Omit the type arguments inference finds from a call's arguments\n\n"
               f"tools/omit-type-args --mode {args.mode}: the {len(first)} calls whose written type arguments\n"
               f"inference finds from their value arguments alone.")

    # 3: those that need their expected type, restoring the calls the build rejects
    second = [c for c in report(args.mode) if c.kind == WITH_EXPECTED]
    excluded: set[Call] = set()
    texts: dict[str, bytes] = {}
    while True:
        kept = [c for c in second if c not in excluded]
        restore(texts)
        edited = write(kept, texts)
        built = build()
        if built.returncode == 0:
            break
        errors = [(m["file"], int(m["line"]), int(m["col"])) for m in ERROR.finditer(built.stdout + built.stderr)]
        rejected = set()
        for file, line, col in errors:
            if file in edited:
                offset = line_starts(edited[file].data)[line - 1] + col - 1
                call = enclosing(edited[file], offset)
                if call is not None:
                    rejected.add(call)
        if not rejected:
            print(built.stdout + built.stderr, file=sys.stderr)
            return 2
        excluded |= rejected
    print(f"omit-type-args: {len(kept)} calls inferable with their expected type ({len(excluded)} restored)",
          file=sys.stderr)
    if not args.no_commit and kept:
        commit(f"Omit the type arguments inference finds with a call's expected type\n\n"
               f"tools/omit-type-args --mode {args.mode}: the {len(kept)} calls whose written type arguments\n"
               f"inference finds only with the type the context expects of the call, found after the first\n"
               f"pass; {len(excluded)} that the build then rejected keep theirs.")

    # 4: the code, against the starting commit's
    if args.no_compare:
        return 0
    return subprocess.run([str(ROOT_DIR / "tools" / "compare-codegen"), "--base", base], cwd=ROOT_DIR).returncode


if __name__ == "__main__":
    sys.exit(main())
