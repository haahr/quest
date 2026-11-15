"""Checks a module's variants (docs/build-process.md section 6.4): a program
that imports a module with variants, built by DRIVER with each choice of
one, in one build directory, so that a change of variant rebuilds the
module, and run.

- Without --variant, a unit compiled by a backend that names a variant it
  has takes it (arm64's), and one compiled by a backend it has none for
  takes its own file (c's);
- --variant UNIT=VARIANT takes that variant, whatever the backend, or the
  module's own file if it has no such variant;
- a parallel build (-j) chooses as a serial one does;
- the interpreter's run of the program chooses as its default backend does.

run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/variants.py DRIVER
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

FILES = {
    "which.int.quest": "interface Which export name: String end\n",
    "which.mod.quest": 'module which: Which export let name = "own" end\n',
    "which.arm64.mod.quest": 'module which: Which export let name = "arm64" end\n',
    "which.none.mod.quest": 'module which: Which export let name = "none" end\n',
    "main.quest": 'import writer: Writer\nimport which: Which\nwriter.putString(writer.output which.name <> "\\n")\n',
}

# Each build's options, and the variant its program shows, in order, in one
# build directory
BUILDS = [
    ([], "arm64"),
    (["--variant", "which=none"], "none"),
    ([], "arm64"),
    (["--backend", "c"], "own"),
    (["--backend", "c", "--variant", "which=none"], "none"),
    (["--variant", "which=nothere"], "own"),
    (["-j", "4", "--variant", "which=none"], "none"),
]


def check(driver: str) -> list[str]:
    problems = []
    with tempfile.TemporaryDirectory() as d:
        scratch = Path(d)
        for name, text in FILES.items():
            (scratch / name).write_text(text)
        environment = {"QUEST_HOME": str(ROOT_DIR), "PATH": "/usr/bin:/bin"}
        for options, expected in BUILDS:
            built = subprocess.run([driver, "compile", "--build-dir", "b", *options, "-o", "p", "main.quest"],
                                   cwd=scratch, capture_output=True, text=True, env=environment, timeout=300)
            ran = subprocess.run([str(scratch / "p")], capture_output=True, text=True, timeout=60) \
                if built.returncode == 0 else None
            got = ran.stdout.strip() if ran else f"no build:\n{built.stdout}{built.stderr}"
            if got != expected:
                problems.append(f"{' '.join(options) or 'no options'}: expected {expected!r}, got {got!r}")
        interpreted = subprocess.run([driver, "--no-jit", "main.quest"], cwd=scratch, capture_output=True, text=True,
                                     env=environment, timeout=120)
        if interpreted.stdout.strip() != "arm64":
            problems.append(f"interpreted: expected 'arm64', got {interpreted.stdout + interpreted.stderr!r}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    found = check(sys.argv[1])
    for problem in found:
        print(problem)
    print(f"variants: {len(found)} problems")
    sys.exit(1 if found else 0)
