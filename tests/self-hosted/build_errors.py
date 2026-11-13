"""Checks that a self-hosted driver reports the errors of a build, and of a
run, as the bootstrap does.

Each directory under tests/self-hosted/build-errors is a program (main.quest)
whose build with -o fails in a unit it imports. The bootstrap and the driver
each build a copy of it outside the checkout (under which its units would be
named from the checkout's root), from the copy's directory, and must fail with
the same diagnostics: located in the unit's file, with its line. Each also runs
the program, the driver with its JIT, which compiles an imported module from
source, and with --no-jit, which type checks it from source, and each run must
report the bootstrap's run's diagnostics, with the import that loaded the unit
quoted from main.quest. run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/build_errors.py DRIVER [CASE...]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CASES_DIR = Path(__file__).resolve().parent / "build-errors"


def build(command: list[str], case: Path, linked: bool = True) -> tuple[int, str]:
    """The exit status and standard error of building a copy of case's program
    with command (or, unless linked, running it), with the copy's path left
    out."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        program = Path(d) / "program"
        shutil.copytree(case, program)
        build_dir = Path(d) / "build"
        output = ["-o", str(build_dir / "main")] if linked else []
        p = subprocess.run([*command, "--build-dir", str(build_dir), *output, "main.quest"],
                           capture_output=True, text=True, cwd=program, env=environment)
        return p.returncode, p.stderr.replace(str(Path(d).resolve()), "<tmp>").replace(d, "<tmp>")


def compare(driver: str, cases: list[Path]) -> list[str]:
    """The cases the driver reports differently from the bootstrap, with how."""
    problems: list[str] = []
    bootstrap = str(ROOT_DIR / "questboot")
    for case in cases:
        expected = build([bootstrap], case)
        if expected[0] == 0:
            problems.append(f"{case.name}: the bootstrap builds it")
            continue
        ran = build([bootstrap], case, linked=False)
        for how, command, wanted, linked in (("-o", [driver], expected, True),
                                             ("run", [driver], ran, False),
                                             ("run --no-jit", [driver, "--no-jit"], ran, False)):
            actual = build(command, case, linked)
            if actual != wanted:
                problems.append(f"{case.name} ({how}): expected (exit {wanted[0]})\n{wanted[1]}"
                                f"but got (exit {actual[0]})\n{actual[1]}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cases = [Path(c).resolve() for c in sys.argv[2:]] or sorted(p for p in CASES_DIR.iterdir() if p.is_dir())
    problems = compare(sys.argv[1], cases)
    for problem in problems:
        print(problem)
    failed = len({problem.split(" ")[0].rstrip(":") for problem in problems})
    print(f"{len(cases) - failed} of {len(cases)} programs report the same errors")
    sys.exit(1 if problems else 0)
