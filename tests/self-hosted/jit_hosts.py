"""Checks the JIT's imports and hosts (docs/jit.md sections 3.3, 3.4, and
3.10): with a self-hosted driver,

- an input that imports a module whose interface differs from the one the
  driver was built with (a copy of lib/ with one interface changed, as
  QUEST_HOME) is refused, naming the module and saying to rebuild, and one whose
  interface is the same (an unchanged copy) is not;
- an input that imports a module of the user's own is refused;
- the REPL's transcripts run through --jit in a driver whose units the arm64
  backend compiled, as they do in one the C backend compiled (run_tests.py
  --backend jit), against their goldens, but for those the jit mode skips.

run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/jit_hosts.py DRIVER
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

from quest.testing import runner  # noqa: E402


def session(driver: str, home: Path, cwd: Path, text: str) -> str:
    """What a --jit REPL session with QUEST_HOME home writes for text."""
    environment = {**os.environ, "QUEST_HOME": str(home)}
    ran = subprocess.run([driver, "--jit", "-i"], input=text, capture_output=True, text=True, cwd=cwd,
                         env=environment, timeout=120)
    return ran.stdout + ran.stderr


def check_imports(driver: str, scratch: Path) -> list[str]:
    problems: list[str] = []
    for name, change in (("same", False), ("changed", True)):
        home = scratch / name
        shutil.copytree(ROOT_DIR / "lib", home / "lib")
        (home / "runtime").symlink_to(ROOT_DIR / "runtime")
        if change:
            maybe = home / "lib" / "util" / "maybe.int.quest"
            text = maybe.read_text(encoding="utf-8")
            maybe.write_text(text[:text.rindex("end")] + "    extra: Int\nend\n", encoding="utf-8")
        work = scratch / (name + "-work")
        work.mkdir()
        shown = session(driver, home, work, "import util/maybe: util/Maybe\nmaybe.isSome(:Int maybe.some(:Int 1))\n")
        refused = "built from another version of the interface of module 'util/maybe'" in shown
        if refused != change:
            problems.append(f"an import of util/maybe with its interface {name} was "
                            f"{'refused' if refused else 'not refused'}:\n{shown}")
    own = scratch / "own"
    own.mkdir()
    (own / "counter.int.quest").write_text("interface Counter export n: Int end\n", encoding="utf-8")
    (own / "counter.mod.quest").write_text("module counter: Counter export let n = 1 end\n", encoding="utf-8")
    shown = session(driver, ROOT_DIR, own, "import counter: Counter\ncounter.n\n")
    if "module 'counter' is not in the driver" not in shown:
        problems.append(f"an import of the user's own module was not refused:\n{shown}")
    return problems


def check_arm64_host(driver: str, scratch: Path) -> list[str]:
    host = scratch / "quest-arm64"
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    built = subprocess.run([driver, "compile", "--backend", "arm64", "-j", "8", "--build-dir", str(scratch / "build"),
                            "questlang/driver/main.quest", "-o", str(host)], capture_output=True, text=True,
                           cwd=ROOT_DIR, env=environment)
    if built.returncode != 0:
        return [f"the arm64 build of the driver failed:\n{built.stdout}{built.stderr}"]
    pending = runner.self_hosted_pending(runner.JIT_PENDING)
    problems = []
    for source in runner.discover_repl_tests():
        if "jit" in runner.parse_skipped_phases(source) or f"repl:repl/{source.stem}" in pending:
            continue
        actual, _ = runner.repl_transcript(source, [str(host), "--jit"], 120)
        expected = (runner.TESTS_REPL_GOLDEN_DIR / (source.stem + ".out")).read_text(encoding="utf-8")
        if actual != expected:
            problems.append(f"repl/{source.stem} through an arm64-built driver:\n{actual}")
    return problems


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    driver = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory() as d:
        found = check_imports(driver, Path(d)) + check_arm64_host(driver, Path(d))
    for problem in found:
        print(problem)
    print(f"jit hosts: {len(found)} problems")
    sys.exit(1 if found else 0)
