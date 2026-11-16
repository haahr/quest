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
                   ("node", ["node", "--no-warnings", str(NODE_HOST)] + modules + [str(runtime), str(module)]))
        for engine, command in engines:
            got = run(command, d, environment)
            if got[0] != expected[0] or got[1] != expected[1]:
                problems.append(f"{name} in {engine}: exit status {got[0]} and output {got[1][:300]!r}, not "
                                f"{expected[0]} and {expected[1][:300]!r}; stderr {got[2][:300]!r}")
            elif not expected[2].startswith(got[2]):
                problems.append(f"{name} in {engine}: stderr {got[2][:300]!r} does not begin arm64's "
                                f"{expected[2][:300]!r}")
    return problems


def check_driver_run(driver: str) -> list[str]:
    """--backend wasm FILE runs the program in --wasm-engine's engine, as a
    program runs natively: its output, its status (200 through wasmtime too),
    an uncaught overflow as stack.overflow; -e is refused with it
    (docs/wasm-plan.md step 31)"""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        Path(d, "exit.quest").write_text('import system: System;\nimport writer: Writer;\n'
                                         'writer.putString(writer.output "before\\n");\nsystem.sysexit(200);\n')
        Path(d, "deep.quest").write_text("let rec deep(n: Int): Int = n - deep(n + 1);\ndeep(0);\n")
        for engine in ("wasmtime", "node"):
            base = [driver, "--backend", "wasm", "--wasm-engine", engine, "--build-dir", str(Path(d) / "build")]
            got = run(base + ["exit.quest"], d, environment)
            if got[:2] != (200, "before\n"):
                problems.append(f"--backend wasm in {engine}: status {got[0]}, output {got[1]!r}, stderr {got[2]!r}")
            got = run(base + ["deep.quest"], d, environment)
            if got[0] != 1 or not got[2].startswith("Exception: stack.overflow"):
                problems.append(f"an overflow in {engine}: status {got[0]}, stderr {got[2][:300]!r}")
        got = run([driver, "--backend", "wasm", "-e", "1 + 1"], d, environment)
        if got[0] != 2:
            problems.append(f"--backend wasm -e: status {got[0]}, not refused")
    return problems


def check_stale_runtime(driver: str) -> list[str]:
    """An object in the build directory that another runtime's compiler
    built (its quest.runtime section another stamp) is rebuilt, not linked
    and refused when instantiated (docs/wasm-plan.md step 31)"""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        Path(d, "main.quest").write_text('import writer: Writer;\nwriter.putString(writer.output "ran\\n");\n')
        build = Path(d) / "build"
        command = [driver, "--backend", "wasm", "--wasm-engine", "node", "--build-dir", str(build), "main.quest"]
        if run(command, d, environment)[:2] != (0, "ran\n"):
            return ["a stale runtime: the first build did not run"]
        objects = [o for o in build.rglob("*.wasm") if b"quest.runtime" in o.read_bytes()]
        if not objects:
            return ["a stale runtime: no object carries quest.runtime"]
        # another stamp, of the same length and with the same times, as an
        # earlier runtime's would be
        for o in objects:
            data = o.read_bytes()
            times = o.stat()
            at = data.rindex(b"quest.runtime") + len(b"quest.runtime")
            digits = bytes(b"0123456789"[(c - 48 + 1) % 10] if 48 <= c <= 57 else c for c in data[at:])
            o.write_bytes(data[:at] + digits)
            os.utime(o, ns=(times.st_atime_ns, times.st_mtime_ns))
        got = run(command[:1] + ["-v"] + command[1:], d, environment)
        if got[0] != 0 or not got[1].endswith("ran\n"):
            problems.append(f"a stale runtime: status {got[0]}, output {got[1][-300:]!r}, stderr {got[2][:300]!r}")
        elif "built against another wasm runtime" not in got[1] + got[2]:
            problems.append("a stale runtime: the build did not say why it rebuilt")
    return problems


def check(driver: str, update: bool = False) -> list[str]:
    if shutil.which("wasmtime") is None or shutil.which("node") is None:
        print("wasmtime or node is not installed: skipped")
        return []
    problems: list[str] = []
    for program in sorted(CASES.glob("*.quest")):
        problems += check_program(driver, program, update)
    problems += check_driver_run(driver)
    problems += check_stale_runtime(driver)
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
