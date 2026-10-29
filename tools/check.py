"""Runs the tests a change needs before it is pushed (docs/testing.md section
4.1), with the suites that it needs at once, the machine's cores split
between them.

    tools/check                    a change to both compilers, or to lib/, runtime/, or the tests
    tools/check --self-hosted-only a change to the self-hosted compiler alone (questlang/: its IR, its C)

A change to both runs, at once, the self-hosting check (run_tests.py
--self-hosting --seed release, which ends by running the self-hosted suite with
stage 2), the bootstrap's suite, and the unit tests but those that drive a
terminal, and then, alone, the terminal tests, which time out under load. A
change to the self-hosted compiler alone runs the self-hosting check only, with
all the workers. Each suite builds into a temporary directory of its own, so
they do not interfere. Their output is kept in .build/check/SUITE.txt, and
each suite's summary is printed with when it finished. The exit status is 0
when every suite passes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / ".build" / "check"
# The unit tests that drive a terminal (tests/python/test_readline_terminal.py)
PTY_TESTS = "tests/python/test_readline_terminal.py"


class Suite:
    """A suite's command, and once it has run, its status and when it ended."""

    def __init__(self, name: str, command: list[str], environment: dict[str, str] | None = None):
        self.name = name
        self.command = command
        self.environment = {**os.environ, **(environment or {})}
        self.output = OUTPUT_DIR / f"{name}.txt"
        self.returncode: int | None = None
        self.finished = 0.0

    def run(self, start: float) -> None:
        with self.output.open("w", encoding="utf-8") as out:
            self.returncode = subprocess.run(self.command, stdout=out, stderr=subprocess.STDOUT, cwd=ROOT_DIR,
                                             env=self.environment).returncode
        self.finished = time.monotonic() - start

    def summary(self) -> list[str]:
        """The lines of its output that sum it up: run_tests.py's summary, or
        unittest's count and verdict."""
        lines = self.output.read_text(encoding="utf-8", errors="replace").splitlines()
        picked = [line for line in lines if line.startswith(("Summary:", "  Golden tests:", "  Error tests:", "Ran ",
                                                             "OK", "FAILED", "Fixed point", "Bootstrappable",
                                                             "Stages 2 and 3"))]
        return picked or lines[-3:]


def run_at_once(suites: list[Suite], start: float) -> None:
    threads = [threading.Thread(target=suite.run, args=(start,)) for suite in suites]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-hosted-only", action="store_true",
                        help="a change to the self-hosted compiler alone: the self-hosting check only")
    parser.add_argument("--seed", choices=("release", "bootstrap"), default="release",
                        help="what builds the self-hosting check's stage 1 (default: the current release; the "
                        "bootstrap past a gap, docs/instructions.md section 6.1)")
    args = parser.parse_args()

    python = sys.executable
    cores = os.cpu_count() or 4
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_tests = [python, str(ROOT_DIR / "run_tests.py")]
    self_hosting = [*run_tests, "--self-hosting", "--seed", args.seed]
    unit = [python, "-m", "unittest"]
    unit_environment = {"PYTHONPATH": str(ROOT_DIR / "bootstrap" / "python")}

    if args.self_hosted_only:
        together = [Suite("self-hosting", [*self_hosting, "-j", str(min(8, cores))])]
        after: list[Suite] = []
    else:
        # The self-hosted suite takes longest, and sets when the run ends: it
        # gets most of the cores (docs/testing.md section 5.1)
        together = [
            Suite("self-hosting", [*self_hosting, "-j", str(max(1, cores * 6 // 10))]),
            Suite("bootstrap", [*run_tests, "-j", str(max(1, cores * 4 // 10))]),
            Suite("unit", [*unit, "discover", "-s", "tests/python"], {**unit_environment, "QUEST_SKIP_PTY_TESTS": "1"}),
        ]
        after = [Suite("pty", [*unit, PTY_TESTS], unit_environment)]

    start = time.monotonic()
    print(f"Running {', '.join(suite.name for suite in together)} at once"
          + (f", then {', '.join(suite.name for suite in after)}" if after else "")
          + f"; output in {OUTPUT_DIR.relative_to(ROOT_DIR)}/", flush=True)
    run_at_once(together, start)
    for suite in after:
        suite.run(start)

    failed = []
    for suite in [*together, *after]:
        verdict = "passed" if suite.returncode == 0 else f"FAILED (exit {suite.returncode})"
        print(f"== {suite.name}: {verdict}, finished at {suite.finished:.0f}s")
        for line in suite.summary():
            print(f"   {line}")
        if suite.returncode != 0:
            failed.append(suite.name)
    print(f"Elapsed {time.monotonic() - start:.0f}s"
          + (f"; failed: {', '.join(failed)} (see {OUTPUT_DIR.relative_to(ROOT_DIR)}/)" if failed else "; all passed"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
