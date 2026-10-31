"""Checks a self-hosted driver's choice of backends (docs/arm64.md section 3.12).

tests/self-hosted/backends is a program (main.quest) and a module it imports,
which pass records, closures, exceptions, and polymorphic values across their
boundary. The driver builds a copy of it outside the checkout, into one build
directory, with each of a sequence of choices of backends: every unit by c,
every unit by ssac or arm64, and the program and its module split between the
backends both ways. Each build must print what the first printed; each unit's
manifest must record the backend that compiled it; a unit compiled by another
backend than the build's choice must be compiled again, and one compiled by the
same must not. Malformed options are usage errors, and --whole-program is the c
backend's alone. A runaway recursion through a frame larger than the stack's
guard page ends with stack.overflow with each backend, and tail recursions ten
million deep run in constant stack with arm64. run_tests.py --self-hosted runs
it (docs/testing.md).

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

EXPECTED = "(6, 8)\n(33, 44)\n(9, 12)\ntoo far: 300\n7\n7\n691847.5\n1230539.875\n1231539.875\n908000411\n"

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


OVERFLOW_LETS = 3000


def overflow_program(lets: int) -> str:
    """A recursion through a function whose frame is far larger than the
    stack's guard page, its values all live across the recursive call, so that
    they are spilled: first a hundred deep, which prints the sum of 1 to lets -
    1, then without end."""
    body = "\n".join(f"        let a{i} = a{i - 1} + {i}" for i in range(1, lets))
    others = " + ".join(f"a{i}" for i in range(lets - 1))
    return (f"import writer : Writer conv : Conv ;\n"
            f"let rec deep(n: Int limit: Int): Int =\n    begin\n        let a0 = n\n{body}\n"
            # (Not a + deep(n + 1), which clang makes a loop with an accumulator;
            # the others added on both sides are used after the call)
            f"        if n is limit then a{lets - 1}\n"
            f"        elsif {{deep({{n + 1}} limit) + {others}}} > {{a{lets - 1} + {others}}} then a{lets - 1} else 0 end\n"
            f"    end;\n"
            f"writer.putString(writer.output conv.int(deep(0 100)) <> \"\\n\");\n"
            f"writer.putString(writer.output conv.int(deep(0 ~1)));\n")


def check_overflow(driver: str) -> list[str]:
    """Each backend's recursion through a large frame works when bounded, and
    when runaway ends with stack.overflow, as exceptions.md section 6 has it,
    rather than a crash past the guard page (docs/arm64.md section 10.2)."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    problems: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        program = Path(d) / "overflow.quest"
        program.write_text(overflow_program(OVERFLOW_LETS))
        expected = f"{(OVERFLOW_LETS - 1) * OVERFLOW_LETS // 2}\n"
        for backend in ("c", "ssac", "arm64"):
            build = Path(d) / f"build-{backend}"
            p = subprocess.run([driver, "--backend", backend, "--build-dir", str(build), "-o", str(build / "main"),
                                str(program)], capture_output=True, text=True, cwd=d, env=environment)
            if p.returncode != 0:
                problems.append(f"overflow with {backend}: the build failed: {p.stderr.strip()[:500]}")
                continue
            try:
                run = subprocess.run([str(build / "main")], capture_output=True, text=True, cwd=d, timeout=60)
            except subprocess.TimeoutExpired:
                problems.append(f"overflow with {backend}: the program ran for a minute")
                continue
            if run.returncode != 1 or run.stdout != expected or "stack.overflow" not in run.stderr:
                problems.append(f"overflow with {backend}: exit status {run.returncode}, stdout {run.stdout[:100]!r}, "
                            f"stderr {run.stderr[:300]!r}")
    return problems


TAIL_PROGRAM = """import writer : Writer conv : Conv ;
let say(s: String): Ok = writer.putString(writer.output s <> "\\n");
let rec sum(n: Int acc: Int): Int = if n is 0 then acc else sum({n - 1} {acc + n}) end;
let rec isEven(n: Int): Bool = if n is 0 then true else isOdd(n - 1) end
and isOdd(n: Int): Bool = if n is 0 then false else isEven(n - 1) end;
let rec repeat(n: Int f: All(x: Int) Int x: Int): Int = if n is 0 then x else repeat({n - 1} f f(x)) end;
let step = 3;
let rec countdown(n: Int): Int = if n is 0 then 0 else bounce(n) end
and bounce(n: Int): Int = begin let k = fun(m: Int): Int countdown(m - step) k({n + step} - 1) end;
say(conv.int(sum(10000000 0)));
say(conv.bool(isEven(10000001)));
say(conv.int(repeat(10000000 fun(x: Int): Int {x + step} 0)));
say(conv.int(countdown(10000000)));
"""


def check_tail_calls(driver: str) -> list[str]:
    """With arm64, self, mutual, and closure tail recursions ten million deep,
    which would need hundreds of megabytes of stack as calls, run in the
    default stack (docs/arm64.md section 3.7)."""
    environment = {**os.environ, "QUEST_HOME": str(ROOT_DIR)}
    with tempfile.TemporaryDirectory() as d:
        program = Path(d) / "tail.quest"
        program.write_text(TAIL_PROGRAM)
        build = Path(d) / "build"
        p = subprocess.run([driver, "--backend", "arm64", "--build-dir", str(build), "-o", str(build / "main"),
                            str(program)], capture_output=True, text=True, cwd=d, env=environment)
        if p.returncode != 0:
            return [f"tail calls: the build failed: {p.stderr.strip()[:500]}"]
        try:
            run = subprocess.run([str(build / "main")], capture_output=True, text=True, cwd=d, timeout=60)
        except subprocess.TimeoutExpired:
            return ["tail calls: the program ran for a minute"]
        expected = f"{10000000 * 10000001 // 2}\nfalse\n30000000\n0\n"
        if run.returncode != 0 or run.stdout != expected:
            return [f"tail calls: exit status {run.returncode}, stdout {run.stdout[:200]!r}, "
                    f"stderr {run.stderr[:300]!r}"]
    return []


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    problems = check(sys.argv[1]) + check_overflow(sys.argv[1]) + check_tail_calls(sys.argv[1])
    for problem in problems:
        print(problem)
    print("the backends agree" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)
