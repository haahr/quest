"""Checks that a self-hosted driver compiles unit files as the bootstrap does.

Each module file under lib/ is compiled alone (`-c`) by the bootstrap and by the
driver, each into a build directory of its own, and their artifacts are
compared: the C translations (.mod.c) byte for byte, and the manifests (.qm),
interfaces (.qi), and C headers (.int.h) written with them, with the build
directory and the producer, which differ, left out. Objects are not compared.
run_tests.py --self-hosted runs it (docs/milestone-5.md).

    python tests/self-hosted/unit_artifacts.py DRIVER [MODULE...]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _normalized(text: str, build: Path, qi: bool) -> str:
    data = json.loads(text)
    (data["value"] if qi else data).pop("producer", None)
    out = json.dumps(data, indent=2)
    for path in (str(build.resolve()), str(build)):
        out = out.replace(path, "<build>")
    return out


def _header(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("/* quest abi"))


def _artifacts(build: Path) -> dict[Path, str]:
    found: dict[Path, str] = {}
    for f in sorted(build.rglob("*")):
        if not f.is_file() or f.suffix == ".o":
            continue
        rel = f.relative_to(build)
        text = f.read_text(encoding="utf-8")
        if f.suffix in (".qm", ".qi"):
            text = _normalized(text, build, f.suffix == ".qi")
        elif f.name.endswith(".int.h"):
            text = _header(text)
        found[rel] = text
    return found


def compare(driver: str, modules: list[Path]) -> list[str]:
    """The modules whose artifacts differ (or fail to compile), with why."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    for module in modules:
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            boot, selfh = Path(a), Path(b)
            runs = (
                [str(ROOT_DIR / "quest"), "-c", "--build-dir", str(boot), str(module)],
                [driver, "-c", "--build-dir", str(selfh), str(module)],
            )
            failed = [p for p in (subprocess.run(r, capture_output=True, text=True, env=environment) for r in runs)
                      if p.returncode != 0]
            if failed:
                problems.append(f"{module.relative_to(ROOT_DIR)}: {failed[0].stderr.strip()[:500]}")
                continue
            expected, actual = _artifacts(boot), _artifacts(selfh)
            differing = [str(rel) for rel in sorted(set(expected) | set(actual)) if expected.get(rel) != actual.get(rel)]
            if differing:
                problems.append(f"{module.relative_to(ROOT_DIR)}: {', '.join(differing)} differ")
    return problems


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    modules = [Path(m).resolve() for m in sys.argv[2:]] or sorted((ROOT_DIR / "lib").rglob("*.mod.quest"))
    problems = compare(sys.argv[1], modules)
    for problem in problems:
        print(problem)
    print(f"{len(modules) - len(problems)} of {len(modules)} modules agree")
    sys.exit(1 if problems else 0)
