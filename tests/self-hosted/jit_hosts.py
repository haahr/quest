"""Checks the JIT's imports and hosts (docs/jit.md sections 3.3, 3.4, and
3.10): with a self-hosted driver,

- an input that imports a module whose interface differs from the one the
  driver was built with (a copy of lib/ with one interface changed, as
  QUEST_HOME) is refused, naming the module and saying to rebuild, and one whose
  interface is the same (an unchanged copy) is not;
- an input that imports modules of the user's own, which the JIT compiles from
  source, one importing another, in one input and again in a later one, shows
  what the interpreter shows: the modules are loaded once, keeping their state,
  and an exception raised in one is located in its file;
- the REPL's transcripts run through --jit in a driver whose units the arm64
  backend compiled, as they do in one the C backend compiled (run_tests.py
  --backend jit), against their goldens, but for those the jit mode skips.

run_tests.py --self-hosted runs it (docs/testing.md). A driver that cannot host
the JIT, a whole-program build (docs/jit.md section 3.10), is not checked.

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


def hosts_jit(driver: str) -> bool:
    """Whether the driver can host the JIT: a whole-program build cannot."""
    ran = subprocess.run([driver, "--jit", "-e", "1"], capture_output=True, text=True,
                         env={**os.environ, "QUEST_HOME": str(ROOT_DIR)}, timeout=120)
    return "cannot host the JIT" not in ran.stderr


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
    return problems


OWN_MODULES = {
    "step.int.quest": "interface Step export size: Int end\n",
    "step.mod.quest": "module step: Step export let size = 2 end\n",
    "counter.int.quest": "interface Counter export next(): Int fail(): Int end\n",
    "counter.mod.quest": """module counter: Counter
import step: Step
export
    let count = record var n = 0 end
    let next(): Int =
        begin
            count.n := count.n + step.size
            count.n
        end
    let broken: Exception = exception broken end
    let fail(): Int = raise broken end
end
""",
}
OWN_INPUTS = """import counter: Counter
counter.next()
counter.next()
import counter: Counter
counter.next()
counter.fail()
counter.next()
"""


def check_own_modules(driver: str, scratch: Path) -> list[str]:
    own = scratch / "own"
    own.mkdir()
    for name, text in OWN_MODULES.items():
        (own / name).write_text(text, encoding="utf-8")
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    shown = {}
    for name, options in (("JIT", []), ("interpreter", ["--no-jit"])):
        ran = subprocess.run([driver, *options, "-i"], input=OWN_INPUTS, capture_output=True, text=True, cwd=own,
                             env=environment, timeout=120)
        shown[name] = ran.stdout + ran.stderr
    if shown["JIT"] != shown["interpreter"] or "8 : Int" not in shown["JIT"]:
        return [f"modules of the user's own through the JIT:\n{shown['JIT']}\nand the interpreter:\n"
                f"{shown['interpreter']}"]
    return []


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
    if not hosts_jit(driver):
        print("the driver cannot host the JIT: jit hosts not checked")
        sys.exit(0)
    with tempfile.TemporaryDirectory() as d:
        found = check_imports(driver, Path(d)) + check_own_modules(driver, Path(d)) + check_arm64_host(driver, Path(d))
    for problem in found:
        print(problem)
    print(f"jit hosts: {len(found)} problems")
    sys.exit(1 if found else 0)
