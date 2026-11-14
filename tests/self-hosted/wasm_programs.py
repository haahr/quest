"""Checks a self-hosted driver's wasm backend (docs/wasm-plan.md, step 3) on the
programs in tests/self-hosted/wasm, which test what the shared run goldens
cannot: tail calls a million deep and more, in an engine's own stack, and the
tests before instructions that would trap (section 2.10).

For each program NAME.quest:
- its module's text (--stop-after codegen_wasm) is NAME.wat, the backend's
  text golden; --update writes it;
- built with --backend wasm -o, its module, the runtime's, and its units'
  (the runtime's in Quest among them), which -o writes beside it, run in
  wasmtime and in node (runtime/wasm/run.mjs), with node's default stack,
  about a browser worker's;
- each run's exit status and standard output are the arm64 backend's for the
  same program, and its standard error the start of arm64's: an uncaught
  exception's report without the frames, which this target leaves out
  (decision 12).

Skipped, reporting nothing wrong, where wasmtime or node is missing.
run_tests.py --self-hosted runs it (docs/testing.md).

    python tests/self-hosted/wasm_programs.py DRIVER [--update]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CASES = Path(__file__).resolve().parent / "wasm"
NODE_HOST = ROOT_DIR / "runtime" / "wasm" / "run.mjs"
WASMTIME = ["wasmtime", "run", "-W", "gc=y,function-references=y,tail-call=y,exceptions=y", "-C", "collector=copying"]
TIMEOUT = 120
# The programs' own units, in CASES/units, are imported as units/NAME
INCLUDES = ["-I", str(CASES)]


def run(command: list[str], cwd: str, environment: dict[str, str]) -> tuple[int, str, str]:
    try:
        r = subprocess.run(command, capture_output=True, text=True, cwd=cwd, env=environment, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return -1, "", f"ran for {TIMEOUT} seconds"
    return r.returncode, r.stdout, r.stderr


def check_program(driver: str, program: Path, update: bool) -> list[str]:
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    name = program.stem
    with tempfile.TemporaryDirectory() as d:
        build = Path(d) / "build"
        # The module's text, the backend's golden
        code, text, err = run([driver, "--stop-after", "codegen_wasm", "--build-dir", str(build)] + INCLUDES
                              + [str(program)], d, environment)
        golden = program.with_suffix(".wat")
        if code != 0:
            return [f"{name}: codegen_wasm failed: {err.strip()[:500]}"]
        if update:
            golden.write_text(text)
        elif not golden.exists() or golden.read_text() != text:
            problems.append(f"{name}: the module's text is not {golden.name} (--update writes it)")
        # The arm64 backend's run, which the engines' must match
        native = Path(d) / "native"
        code, _, err = run([driver, "--backend", "arm64", "--build-dir", str(build), "-o", str(native)] + INCLUDES
                           + [str(program)], d, environment)
        if code != 0:
            return problems + [f"{name}: the arm64 build failed: {err.strip()[:500]}"]
        expected = run([str(native)], d, environment)
        module = Path(d) / f"{name}.wasm"
        code, _, err = run([driver, "--backend", "wasm", "--build-dir", str(build), "-o", str(module)] + INCLUDES
                           + [str(program)], d, environment)
        if code != 0:
            return problems + [f"{name}: the wasm build failed: {err.strip()[:500]}"]
        runtime = Path(str(module) + ".runtime.wasm")
        # The units' modules beside it, the runtime's in Quest among them, in
        # the order to load them
        units = Path(str(module) + ".units").read_text().split()
        preloads = [a for u in units for a in ("--preload", u)]
        modules = [a for u in units for a in ("--module", u)]
        engines = (("wasmtime", WASMTIME + ["--preload", f"quest.runtime={runtime}"] + preloads + [str(module)]),
                   ("node", ["node", str(NODE_HOST)] + modules + [str(runtime), str(module)]))
        for engine, command in engines:
            got = run(command, d, environment)
            if got[0] != expected[0] or got[1] != expected[1]:
                problems.append(f"{name} in {engine}: exit status {got[0]} and output {got[1][:300]!r}, not "
                                f"{expected[0]} and {expected[1][:300]!r}; stderr {got[2][:300]!r}")
            elif not expected[2].startswith(got[2]):
                problems.append(f"{name} in {engine}: stderr {got[2][:300]!r} does not begin arm64's "
                                f"{expected[2][:300]!r}")
    return problems


def check(driver: str, update: bool = False) -> list[str]:
    if shutil.which("wasmtime") is None or shutil.which("node") is None:
        print("wasmtime or node is not installed: skipped")
        return []
    problems: list[str] = []
    for program in sorted(CASES.glob("*.quest")):
        problems += check_program(driver, program, update)
    return problems


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--update"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    problems = check(args[0], "--update" in sys.argv[1:])
    for problem in problems:
        print(problem)
    print("the wasm programs run as natively" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)
