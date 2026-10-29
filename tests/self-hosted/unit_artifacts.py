"""Checks that a self-hosted driver compiles each unit file on its own.

Each module file under lib/ is compiled alone (`-c`) by the driver, into a build
directory of its own, which must leave its C translation (.mod.c), manifest
(.qm), object (.o), and its interface's .qi and C header (.int.h). The artifacts
are the self-hosted compiler's own, so they are not compared with the
bootstrap's (docs/testing.md section 2.8); the ABI corpus pins its interfaces'.
run_tests.py --self-hosted runs it (docs/testing.md section 2.3).

    python tests/self-hosted/unit_artifacts.py DRIVER [MODULE...]
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

# What compiling a module leaves, by suffix: its own artifacts and its
# interface's
EXPECTED_SUFFIXES = (".mod.c", ".qm", ".o", ".qi", ".int.h")


def check(driver: str, modules: list[Path]) -> list[str]:
    """The modules that fail to compile, or leave an artifact out, with why."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    for module in modules:
        with tempfile.TemporaryDirectory() as build:
            process = subprocess.run([driver, "-c", "--build-dir", build, str(module)],
                                     capture_output=True, text=True, env=environment)
            if process.returncode != 0:
                problems.append(f"{module.relative_to(ROOT_DIR)}: {process.stderr.strip()[:500]}")
                continue
            names = [f.name for f in Path(build).rglob("*") if f.is_file()]
            missing = [suffix for suffix in EXPECTED_SUFFIXES if not any(n.endswith(suffix) for n in names)]
            if missing:
                problems.append(f"{module.relative_to(ROOT_DIR)}: no {', '.join(missing)} written")
    return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    modules = [Path(m).resolve() for m in sys.argv[2:]] or sorted((ROOT_DIR / "lib").rglob("*.mod.quest"))
    problems = check(sys.argv[1], modules)
    for problem in problems:
        print(problem)
    print(f"{len(modules) - len(problems)} of {len(modules)} modules compile")
    sys.exit(1 if problems else 0)
