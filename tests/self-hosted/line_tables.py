"""Checks that the arm64 backend's programs carry line tables a debugger reads
(docs/arm64.md section 3.16): a self-hosted driver compiles the program below
with --backend arm64, separately and as a whole program, and lldb, run in batch
mode, must stop at a breakpoint set on a Quest line and show the Quest lines of
the backtrace's frames. So must the JIT's code (docs/jit.md section 3.12), run
with QUEST_JIT_DEBUG=1 and lldb's plugin.jit-loader.gdb.enable on: the program
as a file, and its function as one REPL input called by the next, whose lines
lldb lists from the file the session writes. Skipped where there is no lldb.
run_tests.py --self-hosted runs it (docs/testing.md).

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


# The REPL's inputs: fib, then a call of it, at whose line in the first input
# lldb must stop and list it
REPL_INPUTS = PROGRAM.split("\n\n")[1] + "\nfib(20)\n"
JIT_EXPECTED = {
    "file": ("stop reason = breakpoint 1.1", "`qf_fib at fib.quest:8:", "`qv_mod_qj_1_init at fib.quest:11:"),
    "REPL": ("stop reason = breakpoint 1.1", "`qf_fib at input-1.quest:5:", "-> 5   \t        fib(n - 1)",
             "`qv_mod_qj_2_init at input-2.quest:1:"),
}


def check_jit(driver: str) -> list[str]:
    """How lldb's sessions with the program on the JIT differ from what they
    must print."""
    problems = []
    with tempfile.TemporaryDirectory() as d:
        directory = Path(d)
        # A killed session leaves the files it wrote for lldb here
        environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR), "QUEST_JIT_DEBUG": "1", "TMPDIR": d}
        (directory / "fib.quest").write_text(PROGRAM, encoding="utf-8")
        (directory / "inputs").write_text(REPL_INPUTS, encoding="utf-8")
        for name, breakpoint, launch in (("file", "--file fib.quest --line 8", "process launch -- fib.quest"),
                                         ("REPL", "--file input-1.quest --line 5", "process launch -i inputs -- -i")):
            session = subprocess.run(["lldb", "--batch", "-o", "settings set plugin.jit-loader.gdb.enable on",
                                      "-o", "breakpoint set " + breakpoint, "-o", launch, "-o", "bt", "-o", "kill",
                                      driver], capture_output=True, text=True, cwd=directory, env=environment,
                                     timeout=120)
            missing = [text for text in JIT_EXPECTED[name] if text not in session.stdout]
            if missing:
                problems.append(f"JIT, {name}: lldb did not print {missing!r}:\n{session.stdout}{session.stderr}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    if shutil.which("lldb") is None:
        print("no lldb: line tables not checked")
        sys.exit(0)
    driver = str(Path(sys.argv[1]).resolve())
    problems = [problem for options in BUILDS for problem in check(driver, options)] + check_jit(driver)
    for problem in problems:
        print(problem)
    print(f"{len(BUILDS)} builds and the JIT debugged, {len(problems)} problems")
    sys.exit(1 if problems else 0)
