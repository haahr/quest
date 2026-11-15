"""Checks that the driver compiled to wasm compiles itself (docs/wasm-plan.md
steps 10 and 22): the driver built with DRIVER --backend wasm -o, then that
driver, run in node by runtime/wasm/run.mjs, building the driver again with
--backend wasm into a fresh directory. The two builds must be the same: the
same units, each unit's module and the program's and the runtime's the same
bytes. A fixed point: the wasm driver is the native compiler's wasm backend,
compiled by that backend, so it must write what the native compiler writes.

Skipped, reporting nothing wrong, where node is missing.
run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/wasm_selfcompile.py DRIVER [--driver-wasm PATH]

--driver-wasm uses a driver already built (PATH its program module, with
PATH.units and PATH.runtime.wasm beside it) rather than building one.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
MAIN = ROOT_DIR / "questlang" / "driver" / "main.quest"
RUN = ROOT_DIR / "runtime" / "wasm" / "run.mjs"
TIMEOUT = 900


def build(command: list[str], into: Path) -> tuple[Path | None, str]:
    """The driver built by command into into, -j 1 (the wasm driver runs no
    processes): its program module, or None and what went wrong"""
    into.mkdir(parents=True, exist_ok=True)
    target = into / "quest.wasm"
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    r = subprocess.run([*command, "--backend", "wasm", "-j", "1", "--build-dir", str(into / "build"), "-o",
                        str(target), str(MAIN)], capture_output=True, text=True, env=environment, cwd=into,
                       timeout=TIMEOUT)
    if r.returncode != 0:
        return None, f"{' '.join(command[:1])} exited {r.returncode}:\n{r.stdout}{r.stderr}"
    return target, ""


def units(program: Path) -> dict[str, Path]:
    """A build's units, by name, from PROGRAM.units"""
    entries = (program.parent / f"{program.name}.units").read_text().split()
    return {name: Path(path) for name, path in (entry.split("=", 1) for entry in entries)}


def node_command(program: Path) -> list[str]:
    """The command that runs a wasm driver in node, its units given by name"""
    modules = [arg for name, path in units(program).items() for arg in ("--module", f"{name}={path}")]
    return ["node", "--no-warnings", str(RUN), *modules, f"{program}.runtime.wasm", str(program)]


def compare(native: Path, wasm: Path) -> list[str]:
    """What differs between two builds of the driver"""
    problems = []
    a, b = units(native), units(wasm)
    if set(a) != set(b):
        only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
        problems.append(f"the units differ: only natively {only_a}, only in wasm {only_b}")
    for name in sorted(set(a) & set(b)):
        if a[name].read_bytes() != b[name].read_bytes():
            problems.append(f"the unit {name} differs")
    for suffix, what in (("", "the program's module"), (".runtime.wasm", "the runtime module")):
        if Path(f"{native}{suffix}").read_bytes() != Path(f"{wasm}{suffix}").read_bytes():
            problems.append(f"{what} differs")
    return problems


def check(driver: str, driver_wasm: str | None) -> list[str]:
    if shutil.which("node") is None:
        return []
    with tempfile.TemporaryDirectory() as d:
        scratch = Path(d)
        if driver_wasm is not None:
            native = Path(driver_wasm).resolve()
        else:
            built, problem = build([driver], scratch / "native")
            if built is None:
                return [f"the native build of the wasm driver: {problem}"]
            native = built
        rebuilt, problem = build(node_command(native), scratch / "self")
        if rebuilt is None:
            return [f"the wasm driver compiling itself in node: {problem}"]
        return compare(native, rebuilt)


if __name__ == "__main__":
    args = sys.argv[1:]
    built = None
    if "--driver-wasm" in args:
        at = args.index("--driver-wasm")
        built = args[at + 1]
        del args[at:at + 2]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    found = check(args[0], built)
    for problem in found[:20]:
        print(problem)
    print(f"wasm self-compilation: {len(found)} problems")
    sys.exit(1 if found else 0)
