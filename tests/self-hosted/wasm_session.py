"""Checks the driver compiled to wasm as a session in node (docs/wasm-plan.md
step 11): the driver built with DRIVER --backend wasm -o, then run by
runtime/wasm/session-node.mjs in a worker with a Chromium worker's stack
(512 KB), interpreting each input.

- The REPL's transcripts (tests/repl, docs/testing.md section 2.7) against
  their goldens, but for PENDING_TRANSCRIPTS;
- the kernel's protocol (kernel_protocol.py), interpreted, less what a
  session lacks (its --session);
- a session's recovery: an input that overflows the stack past the
  interpreter's limit, and one interrupted, each rolled back by a replay, with
  the bindings before it kept.

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
from quest.testing.transcripts import discover_repl_tests, repl_transcript  # noqa: E402
from quest.testing.layout import TESTS_REPL_GOLDEN_DIR  # noqa: E402
from quest_session import Session  # noqa: E402

SESSION = ROOT_DIR / "runtime" / "wasm" / "session-node.mjs"
KERNEL_PROTOCOL = Path(__file__).resolve().parent / "kernel_protocol.py"
TIMEOUT = 300

# The transcripts a session does not reproduce, each with its reason
PENDING_TRANSCRIPTS = {
    # The interpreter's limit is lower here, so the frames repeat fewer times
    "stack_overflow": "the frames' count depends on the call limit (QUEST_CALL_LIMIT)",
}


def build(driver: str, into: Path) -> Path:
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


def check_transcripts(command: list[str]) -> list[str]:
    problems = []
    for source in discover_repl_tests():
        if source.stem in PENDING_TRANSCRIPTS:
            continue
        try:
            actual, _ = repl_transcript(source, command, TIMEOUT)
        except subprocess.TimeoutExpired:
            problems.append(f"repl/{source.stem}: timed out")
            continue
        expected = (TESTS_REPL_GOLDEN_DIR / f"{source.stem}.out").read_text(encoding=BYTE_ENCODING)
        if actual != expected:
            problems.append(f"repl/{source.stem}: differs\n--- expected\n{expected}--- actual\n{actual}")
    return problems


def check_recovery(command: list[str], scratch: Path) -> list[str]:
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
    return problems


def check(driver: str, driver_wasm: str | None) -> list[str]:
    if shutil.which("node") is None:
        print("node is missing: the session is not checked")
        return []
    with tempfile.TemporaryDirectory() as d:
        into = Path(d)
        target = Path(driver_wasm) if driver_wasm else build(driver, into)
        quest = wrapper(target, into)
        problems = check_transcripts([str(quest)])
        protocol = subprocess.run([sys.executable, str(KERNEL_PROTOCOL), "--session", str(quest)],
                                  capture_output=True, text=True, timeout=TIMEOUT * 4)
        if protocol.returncode != 0:
            problems.append(f"the kernel's protocol:\n{protocol.stdout}{protocol.stderr}")
        scratch = into / "scratch"
        scratch.mkdir()
        problems += check_recovery([str(quest)], scratch)
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
