"""Checks a self-hosted driver's choice of backends (docs/arm64.md section 3.12).

tests/self-hosted/backends is a program (main.quest) and a module it imports,
which pass records, closures, exceptions, and polymorphic values across their
boundary. The driver builds a copy of it outside the checkout, into one build
directory, with each of a sequence of choices of backends: every unit by c,
every unit by ssac or arm64, and the program and its module split between the
backends both ways. Each build must print what the first printed; each unit's manifest must
record the backend that compiled it; a unit compiled by another backend than the
build's choice must be compiled again, and one compiled by the same must not.
Malformed options are usage errors, and --whole-program is the c backend's
alone. run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/backends.py DRIVER
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CASE = Path(__file__).resolve().parent / "backends"

EXPECTED = "(6, 8)\n(33, 44)\n(9, 12)\ntoo far: 300\n7\n7\n691847.5\n1230539.875\n1231539.875\n"

# The choices built in turn into one build directory: the options, and the
# backend each unit's manifest must then record
BUILDS = (
    ([], {"main": "c", "geometry": "c"}),
    (["--backend", "ssac"], {"main": "ssac", "geometry": "ssac"}),
    (["--backend", "ssac"], {"main": "ssac", "geometry": "ssac"}),
    (["--unit-backend", "main=ssac"], {"main": "ssac", "geometry": "c"}),
    (["--backend", "ssac", "--unit-backend", "main=c"], {"main": "c", "geometry": "ssac"}),
    (["--backend", "c", "--unit-backend", "geometry=ssac", "--unit-backend", "geometry=c"],
     {"main": "c", "geometry": "c"}),
    (["--backend", "arm64"], {"main": "arm64", "geometry": "arm64"}),
    (["--backend", "arm64", "--unit-backend", "geometry=c"], {"main": "arm64", "geometry": "c"}),
    (["--backend", "c", "--unit-backend", "geometry=arm64"], {"main": "c", "geometry": "arm64"}),
    (["--backend", "ssac", "--unit-backend", "geometry=arm64"], {"main": "ssac", "geometry": "arm64"}),
)


def manifests(build: Path) -> dict[str, dict]:
    """The build's manifests, by the unit each names (main for the program)."""
    found = {}
    for qm in build.rglob("*.qm"):
        data = json.loads(qm.read_text(encoding="utf-8"))
        found["main" if data.get("name") == "<main>" else data.get("name")] = data
    return found


def check(driver: str) -> list[str]:
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        program = Path(d) / "program"
        shutil.copytree(CASE, program)
        build = Path(d) / "build"
        for options, backends in BUILDS:
            label = " ".join(options) or "(the default)"
            binary = build / "main"
            before = {unit: data.get("backend") for unit, data in manifests(build).items()} if build.exists() else {}
            if (build / "build.log").exists():
                (build / "build.log").unlink()
            p = subprocess.run([driver, *options, "--build-dir", str(build), "-o", str(binary), "main.quest"],
                               capture_output=True, text=True, cwd=program, env=environment)
            if p.returncode != 0:
                problems.append(f"{label}: the build failed: {p.stderr.strip()[:800]}")
                continue
            run = subprocess.run([str(binary)], capture_output=True, text=True, cwd=program)
            if run.stdout != EXPECTED:
                problems.append(f"{label}: the program printed {run.stdout!r}, not {EXPECTED!r}")
            found = manifests(build)
            for unit, backend in backends.items():
                recorded = found.get(unit, {}).get("backend")
                if recorded != backend:
                    problems.append(f"{label}: {unit}'s manifest records {recorded!r}, not {backend!r}")
            # Every library unit is compiled by the build's default backend
            default = options[options.index("--backend") + 1] if "--backend" in options else "c"
            for unit, data in found.items():
                if unit not in backends and data.get("backend") != default:
                    problems.append(f"{label}: {unit}'s manifest records {data.get('backend')!r}, not {default!r}")
            # A unit is compiled again exactly when its backend changed (or it
            # was never compiled)
            log = (build / "build.log").read_text(encoding="utf-8") if (build / "build.log").exists() else ""
            stale = set(re.findall(r"EVAL STALENESS: '([^']*)' -> STALE", log))
            for unit, data in found.items():
                changed = before.get(unit) != data.get("backend")
                if changed != (unit in stale):
                    problems.append(f"{label}: {unit} was {'' if unit in stale else 'not '}compiled again, though its "
                                    f"backend {'changed' if changed else 'did not change'}")

        for options, message in (
            (["--backend", "x86"], "--backend takes c, ssac, or arm64"),
            (["--unit-backend", "main"], "--unit-backend takes UNIT=BACKEND"),
            (["--unit-backend", "main=x"], "--unit-backend takes UNIT=BACKEND"),
            (["--whole-program", "--backend", "ssac"], "--whole-program compiles with the c backend only"),
        ):
            p = subprocess.run([driver, *options, "--build-dir", str(build), "-o", str(build / "other"), "main.quest"],
                               capture_output=True, text=True, cwd=program, env=environment)
            if p.returncode == 0 or message not in p.stderr:
                problems.append(f"{' '.join(options)}: exit status {p.returncode}, stderr {p.stderr.strip()[:300]!r}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    problems = check(sys.argv[1])
    for problem in problems:
        print(problem)
    print("the backends agree" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)
