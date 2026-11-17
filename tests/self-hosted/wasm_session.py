"""Checks the driver compiled to wasm as a session in node (docs/wasm.md
section 6.1): the driver built with DRIVER --backend wasm -o, then run by
runtime/wasm/session-node.mjs in a worker with a Chromium worker's stack
(512 KB), interpreting each input (--no-jit) and compiling each with its JIT.

- The REPL's transcripts (tests/repl, docs/testing.md section 2.7) against
  their goldens, interpreted and with the JIT, but for those
  PENDING_TRANSCRIPTS names, and under the JIT those marked
  @skip-phase: jit;
- the kernel's protocol (kernel_protocol.py), interpreted and with the JIT,
  less what a session lacks (its --session);
- a session's recovery: interpreted, an input that overflows the stack past
  the interpreter's limit, rolled back by a replay; with the JIT, an
  overflow in an input's own code, rolled back with no replay, and one in
  the compiler, by a replay; each with the bindings before it kept;
- a review's programs for recovery (REVIEW; docs/wasm.md section 6.3), and
  a replay that cannot run an input again;
- the page (docs/wasm.md section 6.5) that tools/wasm-page/build writes from
  the same driver, its archives and its worker's session run in node
  (wasm_page.mjs).

Skipped, reporting nothing wrong, where node is missing.
run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/wasm_session.py DRIVER [--driver-wasm PATH]

--driver-wasm uses a driver already built (PATH its program module) rather
than building one, which takes a minute or two.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))
sys.path.insert(0, str(ROOT_DIR / "tools" / "jupyter"))

from quest.common.location import BYTE_ENCODING  # noqa: E402
from quest.testing.directives import parse_test_directives  # noqa: E402
from quest.testing.transcripts import discover_repl_tests, repl_transcript  # noqa: E402
from quest.testing.layout import TESTS_REPL_GOLDEN_DIR  # noqa: E402
from quest_session import DriverExited, Session  # noqa: E402

SESSION = ROOT_DIR / "runtime" / "wasm" / "session-node.mjs"
KERNEL_PROTOCOL = Path(__file__).resolve().parent / "kernel_protocol.py"
PAGE_CHECK = Path(__file__).resolve().parent / "wasm_page.mjs"
BUILD_PAGE = ROOT_DIR / "tools" / "wasm-page" / "build.py"
TIMEOUT = 300

# The transcripts a session does not reproduce, in each mode, each with its
# reason
PENDING_TRANSCRIPTS = {
    "interpreted": {
        # The interpreter's limit is lower here, so the frames repeat fewer
        # times
        "stack_overflow": "the frames' count depends on the call limit (QUEST_CALL_LIMIT)",
    },
    "jit": {
        # An uncaught exception shows its raise's site and <main> alone
        # (decision 12, docs/wasm.md section 2.9)
        "earlier_function_error": "a traceback is the raise site only (decision 12)",
        "module_errors": "a traceback is the raise site only (decision 12)",
    },
}


def build(driver: str, into: Path) -> Path:
    """The program module of the driver compiled by driver with --backend
    wasm, into/quest.wasm, with its runtime and units beside it; raises
    CalledProcessError if the build fails"""
    target = into / "quest.wasm"
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    subprocess.run([driver, "--backend", "wasm", "--build-dir", str(into / "build"), "-o", str(target),
                    str(ROOT_DIR / "questlang" / "driver" / "main.quest")],
                   check=True, capture_output=True, env=environment, cwd=into)
    return target


def wrapper(driver_wasm: Path, into: Path) -> Path:
    """An executable that stands in for `quest`, running the session"""
    script = into / "quest-session"
    script.write_text(f'#!/bin/sh\nexec node --no-warnings "{SESSION}" "{driver_wasm}" "$@"\n')
    script.chmod(0o755)
    return script


def check_transcripts(command: list[str], mode: str) -> list[str]:
    """The REPL's transcripts that command, a session in mode ("interpreted"
    or "jit"), does not answer as their goldens do, but for those pending or
    skipped in mode"""
    problems = []
    for source in discover_repl_tests():
        if source.stem in PENDING_TRANSCRIPTS[mode]:
            continue
        if mode == "jit" and "jit" in parse_test_directives(source).skipped_phases:
            continue
        try:
            actual, _ = repl_transcript(source, command, TIMEOUT)
        except subprocess.TimeoutExpired:
            problems.append(f"repl/{source.stem} ({mode}): timed out")
            continue
        expected = (TESTS_REPL_GOLDEN_DIR / f"{source.stem}.out").read_text(encoding=BYTE_ENCODING)
        if actual != expected:
            problems.append(f"repl/{source.stem} ({mode}): differs\n--- expected\n{expected}--- actual\n{actual}")
    return problems


def check_recovery(command: list[str], scratch: Path) -> list[str]:
    """Whether a session survives a stack overflow with the bindings made
    before it, and without those of the input that overflowed: interpreted,
    and with the JIT in an input's own code and in the compiler"""
    problems = []
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    # A limit the stack cannot hold, so that the engine's overflow comes first
    s = Session([*command, "--no-jit"], cwd=str(scratch), env={**environment, "QUEST_CALL_LIMIT": "100000"})
    try:
        s.execute("let a = 10")
        reply = s.execute("let lost = 1\nlet rec down(n: Int): Int = 1 + down(n + 1)\ndown(0)")
        got = (reply.status, reply.error and reply.error["error"])
        if got != ("error", "stack.overflow"):
            problems.append(f"an overflow past the interpreter's limit: {got}")
        after = (s.execute("a").results, s.execute("lost").status)
        if after != (["10 : Int"], "error"):
            problems.append(f"the session after an overflow: {after}")
    finally:
        s.kill()
    # With the JIT: an overflow in an input's own code, caught by the host at
    # its frame, rolls the input back with no replay, so that what it stored
    # in an earlier input's array stays, as a raise's store does; and one in
    # the compiler, on a phrase whose operators chain past what its stack
    # holds, replays the inputs that committed, which made the array afresh.
    # The array, an object an earlier input made and this one changes in
    # place, tells the two apart: a rollback keeps the store, a replay does
    # not.
    s = Session(command, cwd=str(scratch), env=environment)
    try:
        s.execute("let held = array of 1 end")
        reply = s.execute("let lost = 1\nlet rec down(n: Int): Int = n - down(n + 1)\nheld[0] := 2\ndown(0)")
        got = (reply.status, reply.error and reply.error["error"])
        if got != ("error", "stack.overflow"):
            problems.append(f"an overflow in an input's code: {got}")
        after = (s.execute("held[0]").results, s.execute("lost").status)
        if after != (["2 : Int"], "error"):
            problems.append(f"the session after an overflow in an input's code (no replay): {after}")
        reply = s.execute("held[0] := 3\n" + "1 + " * 3000 + "1")
        got = (reply.status, reply.error and reply.error["error"])
        if got != ("error", "stack.overflow"):
            problems.append(f"an overflow in the compiler: {got}")
        if s.execute("held[0]").results != ["1 : Int"]:
            problems.append(f"the session after an overflow in the compiler (a replay): {s.execute('held[0]').results}")
    finally:
        s.kill()
    return problems


# Programs for recovery that a review found failing (docs/wasm.md sections
# 6.3 and 7, item 13), each in a fresh session: its inputs, and what the last must answer, its
# results or its error's name
REVIEW = [
    ("the subtype trail after an overflow", [
        "import dynamic: Dynamic",
        "Let P = Tuple a: Tuple x: Int y: Tuple z: Int w: Int end end b: String end",
        "Let Q = Tuple a: Tuple x: Int y: Tuple z: Int w: Int end end b: Int end",
        'let d = dynamic.new(:P tuple let a = tuple let x = 1 let y = tuple let z = 2 let w = 3 end end let b = "s"'
        ' end)',
        "let test(): Int = try begin let q = dynamic.be(:Q d) q.b end when dynamic.error then ~1 end",
        "let rec deep(n: Int): Int = begin let unused = test() n - deep(n + 1) end",
        "deep(0)",
        "test()"], ["-1 : Int"]),
    ("an overflow inside a host's file call", [
        "import system : System",
        'let rec down(n: Int): Int = if system.fileExists("flag") then n - down(n + 1) else 0 end',
        "down(0)"], "stack.overflow"),
    # Natively the open raises writer.error; here the bytes, not records, go
    # to the client's standard error, and the session goes on
    ("a write to the session's own descriptor 4", [
        "import writer : Writer",
        'let f = writer.file("/dev/fd/4")',
        'writer.putString(f "not a record\\n")',
        "writer.close(f)",
        "1 + 1"], ["2 : Int"]),
]


def check_review(command: list[str], scratch: Path) -> list[str]:
    """REVIEW's programs whose last input does not answer as expected, or
    whose session ends"""
    problems = []
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    (scratch / "flag").write_text("x\n")
    for name, inputs, expected in REVIEW:
        s = Session(command, cwd=str(scratch), env=environment)
        try:
            for line in inputs:
                reply = s.execute(line)
            got = reply.results if reply.status == "ok" else (reply.error or {}).get("error")
            if got != expected:
                problems.append(f"{name}: {got}, not {expected}")
        except DriverExited as e:
            problems.append(f"{name}: the session ended ({e.status})")
        finally:
            s.kill()
    return problems


def check_lost(command: list[str], scratch: Path) -> list[str]:
    """A replay that cannot run an input again says so, with the names it no
    longer has, and the session goes on (docs/wasm.md section 6.3):
    the input removed a file, which is gone when the replay runs it again"""
    problems = []
    (scratch / "gone.txt").write_text("x\n")
    s = Session(command, cwd=str(scratch), env={**os.environ, "QUEST_HOME": str(ROOT_DIR)})
    try:
        s.execute("import system : System")
        s.execute('let removed = begin system.removeFile("gone.txt") 5 end')
        s.execute("let after = removed + 1")
        # An overflow in the compiler, as in check_recovery, so a replay
        reply = s.execute("1 + " * 3000 + "1")
        rendered = (reply.error or {}).get("rendered", "")
        if "no longer bound: removed, after" not in rendered:
            problems.append(f"a replay that loses inputs: {rendered!r}")
        if s.execute("2 + 3").results != ["5 : Int"]:
            problems.append("the session after a replay that lost inputs")
    except DriverExited as e:
        problems.append(f"a replay that loses inputs: the session ended ({e.status})")
    finally:
        s.kill()
    return problems


def check_page(driver_wasm: Path, into: Path) -> list[str]:
    """The page built from driver_wasm, checked in node"""
    page = into / "page"
    built = subprocess.run([sys.executable, str(BUILD_PAGE), "--driver-wasm", str(driver_wasm), "-o", str(page)],
                           capture_output=True, text=True, timeout=TIMEOUT)
    if built.returncode != 0:
        return [f"the page's build:\n{built.stdout}{built.stderr}"]
    run = subprocess.run(["node", "--no-warnings", str(PAGE_CHECK), str(page), str(ROOT_DIR / "tests" / "repl")],
                         capture_output=True, text=True, timeout=TIMEOUT)
    if run.returncode != 0:
        return [f"the page:\n{run.stdout}{run.stderr}"]
    return []


def check(driver: str, driver_wasm: str | None) -> list[str]:
    """Every problem the module docstring's checks find in the wasm driver
    that driver builds (or driver_wasm, if given); nothing where node is
    missing"""
    if shutil.which("node") is None:
        print("node is missing: the session is not checked")
        return []
    with tempfile.TemporaryDirectory() as d:
        into = Path(d)
        target = Path(driver_wasm) if driver_wasm else build(driver, into)
        quest = wrapper(target, into)
        problems = check_transcripts([str(quest), "--no-jit"], "interpreted")
        problems += check_transcripts([str(quest)], "jit")
        protocol = subprocess.run([sys.executable, str(KERNEL_PROTOCOL), "--session", str(quest)],
                                  capture_output=True, text=True, timeout=TIMEOUT * 4)
        if protocol.returncode != 0:
            problems.append(f"the kernel's protocol:\n{protocol.stdout}{protocol.stderr}")
        scratch = into / "scratch"
        scratch.mkdir()
        problems += check_recovery([str(quest)], scratch)
        problems += check_review([str(quest)], scratch)
        problems += check_lost([str(quest)], scratch)
        problems += check_page(target, into)
    return problems


if __name__ == "__main__":
    args = sys.argv[1:]
    built = None
    if "--driver-wasm" in args:
        at = args.index("--driver-wasm")
        built = args[at + 1]
        del args[at:at + 2]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    found = check(args[0], built)
    for problem in found:
        print(problem)
    print(f"wasm session: {len(found)} problems")
    sys.exit(1 if found else 0)
