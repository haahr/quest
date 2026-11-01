"""Checks that the arm64 backend's programs carry line tables a debugger reads
(docs/arm64.md section 3.16): a self-hosted driver compiles the program below
with --backend arm64, separately and as a whole program, and lldb, run in batch
mode, must stop at a breakpoint set on a Quest line and show the Quest lines of
the backtrace's frames. Skipped where there is no lldb. run_tests.py
--self-hosted runs it (docs/testing.md).

    python tests/self-hosted/line_tables.py DRIVER
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

PROGRAM = """import writer: Writer
import conv: Conv

let rec fib(n: Int): Int =
    if n < 2 then
        n
    else
        fib(n - 1) + fib(n - 2)
    end

writer.putString(writer.output conv.int(fib(20)) <> "\\n")
"""

# Each build's options, and what lldb must print: the breakpoint stopped at its
# line, in fib, which main called from the program's last line
BUILDS = ([], ["--whole-program"])
EXPECTED = ("stop reason = breakpoint 1.1", "frame #0: ", "`qf_fib at fib.quest:8:", "`main at fib.quest:11:")


def check(driver: str, options: list[str]) -> list[str]:
    """How lldb's session with the program built with options differs from
    what it must print."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        directory = Path(d)
        (directory / "fib.quest").write_text(PROGRAM, encoding="utf-8")
        build = subprocess.run([driver, "compile", "--backend", "arm64", *options, "fib.quest", "-o", "fib"],
                               capture_output=True, text=True, cwd=directory, env=environment)
        if build.returncode != 0:
            return [f"{' '.join(options) or 'separate'}: the build failed:\n{build.stderr}"]
        session = subprocess.run(["lldb", "--batch", "-o", "breakpoint set --file fib.quest --line 8", "-o", "run",
                                  "-o", "bt", "./fib"], capture_output=True, text=True, cwd=directory, timeout=120)
        missing = [text for text in EXPECTED if text not in session.stdout]
        if missing:
            return [f"{' '.join(options) or 'separate'}: lldb did not print {missing!r}:\n{session.stdout}"
                    f"{session.stderr}"]
        return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    if shutil.which("lldb") is None:
        print("no lldb: line tables not checked")
        sys.exit(0)
    driver = str(Path(sys.argv[1]).resolve())
    problems = [problem for options in BUILDS for problem in check(driver, options)]
    for problem in problems:
        print(problem)
    print(f"{len(BUILDS)} builds debugged, {len(problems)} problems")
    sys.exit(1 if problems else 0)
