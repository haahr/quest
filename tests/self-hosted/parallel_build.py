"""Checks that a self-hosted driver's parallel builds (-j) are its serial ones.

Each directory under tests/self-hosted/parallel-build, and each under
tests/self-hosted/build-errors, is a program (main.quest) and the units it
imports. The driver builds a copy of it outside the checkout twice, with -j 1
and -j 4, into two build directories. A program that builds must leave the same
artifacts (as the self-hosting check compares them), the same build.log entries
in the same order (without their times), and a binary that prints the same; one
that fails must fail with the same exit status and diagnostics: those of the
first unit to fail in queue order, whichever compiled first (docs/build-process.md
section 7.4). run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/parallel_build.py DRIVER [CASE...]
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.testing.runner import compare_build_dirs  # noqa: E402

CASES_DIRS = (Path(__file__).resolve().parent / "parallel-build", Path(__file__).resolve().parent / "build-errors")


def log_entries(build: Path) -> list[str]:
    """A build's log entries, without their times and the build directory."""
    log = build / "build.log"
    if not log.is_file():
        return []
    text = log.read_text(encoding="utf-8").replace(str(build.resolve()), "<build>").replace(str(build), "<build>")
    return [re.sub(r"^\[[^]]*\] ", "", line) for line in text.splitlines()]


def check(driver: str, case: Path) -> list[str]:
    """How case's parallel build differs from its serial one."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        program = Path(d) / "program"
        shutil.copytree(case, program)
        results = {}
        for jobs in ("1", "4"):
            build = Path(d) / f"build-{jobs}"
            p = subprocess.run([driver, "-j", jobs, "--build-dir", str(build), "-o", str(build / "main"), "main.quest"],
                               capture_output=True, text=True, cwd=program, env=environment)
            stderr = p.stderr.replace(str(build.resolve()), "<build>").replace(str(build), "<build>")
            run = ""
            if p.returncode == 0:
                run = subprocess.run([str(build / "main")], capture_output=True, text=True, cwd=program).stdout
            results[jobs] = (build, p.returncode, stderr, run)
        (serial, serial_code, serial_err, serial_run), (parallel, code, err, run) = results["1"], results["4"]
        problems: list[str] = []
        if (code, err) != (serial_code, serial_err):
            problems.append(f"{case.name}: -j 1 exited {serial_code}:\n{serial_err}-j 4 exited {code}:\n{err}")
        elif code == 0:
            problems += compare_build_dirs(serial, parallel, case.name)
            if log_entries(serial) != log_entries(parallel):
                problems.append(f"{case.name}: build.log differs")
            if run != serial_run:
                problems.append(f"{case.name}: the program printed {run!r}, not {serial_run!r}")
        return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cases = [Path(c).resolve() for c in sys.argv[2:]] or sorted(
        p for d in CASES_DIRS for p in d.iterdir() if p.is_dir())
    driver = str(Path(sys.argv[1]).resolve())
    problems = [problem for case in cases for problem in check(driver, case)]
    for problem in problems:
        print(problem)
    print(f"{len(cases)} builds compared, {len(problems)} differences")
    sys.exit(1 if problems else 0)
