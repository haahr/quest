"""Measures the C backend, for comparing it with the baseline taken of the emitter it replaced (docs/ir.md §12, steps 0
and 6).

    python tests/perf/measure.py             # print a summary, comparing with tests/perf/baseline.json if present
    python tests/perf/measure.py --save      # also write the measurements to tests/perf/baseline.json

Two measurements:

- C generation: for every golden test program that is compiled to C, the time spent in the C backend (lowering to the
  IR, its passes, and printing C: neither type checking nor clang) and the size of the C it produces. The program's
  own C: the modules it imports are compiled on their own (the baseline's emitter compiled some into the program).
- Run time: for each benchmark in this directory (*.quest), the fastest of several runs of its compiled binary. The
  benchmarks cross polymorphic boundaries heavily, so they measure what the represent pass changes: casts, copies,
  and thunks.

Times depend on the machine, so compare measurements taken on the same one.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.codegen.c.compiler_runner import compile_c_source, run_binary
from quest.codegen.c.backend import program_to_c
from quest.config import CompilerOptions  # noqa: E402
from quest.pipeline import CompilerContext, compile_pipeline, default_pipeline, link_dependencies  # noqa: E402
from quest.testing.runner import discover_tests, parse_skipped_phases  # noqa: E402

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline.json"
SOURCE_DIR = ROOT_DIR / "tests" / "source"
RUNS = 5


def measure_generation() -> dict:
    programs: dict[str, list[float | int]] = {}
    for path in discover_tests(SOURCE_DIR):
        if "run_c_compiled" in parse_skipped_phases(path):
            continue
        source = path.read_text()
        options = CompilerOptions(stop_after="typecheck")
        ctx = CompilerContext.create(source_text=source, file_name=str(path), options=options)
        res = default_pipeline().execute(source, str(path), options=options, ctx=ctx)
        if not res.success:
            continue
        start = time.perf_counter()
        try:
            c_code, _ = program_to_c(res.artifacts["typecheck"], ctx.env, print_result=True)
        except Exception:
            continue
        programs[str(path.relative_to(ROOT_DIR))] = [round(time.perf_counter() - start, 4), len(c_code)]
    return {
        "programs": len(programs),
        "seconds": round(sum(p[0] for p in programs.values()), 3),
        "c_bytes": sum(p[1] for p in programs.values()),
        "per_program": programs,
    }


def measure_benchmarks() -> dict:
    results: dict[str, dict] = {}
    for path in sorted(HERE.glob("*.quest")):
        with tempfile.TemporaryDirectory() as tmp:
            source = path.read_text()
            options = CompilerOptions(build_dir=Path(tmp) / "build")
            ctx = CompilerContext.create(source_text=source, file_name=str(path), options=options)
            res = compile_pipeline().execute(source, str(path), options=options, ctx=ctx)
            if not res.success:
                raise SystemExit(f"{path.name}: {[d.message for d in res.diagnostics]}")
            binary = Path(tmp) / path.stem
            compile_c_source(res.artifacts["codegen_c"], output_path=binary, extra_objects=link_dependencies(ctx))
            times = []
            output = None
            for _ in range(RUNS):
                start = time.perf_counter()
                proc = run_binary(binary, timeout=600.0)
                times.append(time.perf_counter() - start)
                if proc.returncode != 0:
                    raise SystemExit(f"{path.name}: exit {proc.returncode}: {proc.stderr}")
                output = proc.stdout.strip()
        results[path.stem] = {"seconds": round(min(times), 4), "output": output}
    return results


def _commit() -> str:
    proc = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT_DIR, capture_output=True, text=True)
    return proc.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--save", action="store_true", help="write the measurements to tests/perf/baseline.json")
    args = parser.parse_args()
    current = {"commit": _commit(), "generation": measure_generation(), "benchmarks": measure_benchmarks()}
    baseline = json.loads(BASELINE.read_text()) if BASELINE.exists() else None

    def compare(now: float, before: float | None) -> str:
        return f" ({now / before:.2f}x baseline)" if before else ""

    gen = current["generation"]
    base_gen = baseline["generation"] if baseline else {}
    print(f"C generation: {gen['programs']} programs, {gen['seconds']:.2f}s{compare(gen['seconds'], base_gen.get('seconds'))},"
          f" {gen['c_bytes']} bytes of C{compare(gen['c_bytes'], base_gen.get('c_bytes'))}")
    for name, bench in current["benchmarks"].items():
        before = baseline["benchmarks"].get(name, {}).get("seconds") if baseline else None
        print(f"{name}: {bench['seconds']:.3f}s{compare(bench['seconds'], before)}")
    if args.save:
        BASELINE.write_text(json.dumps(current, indent=1, sort_keys=True) + "\n")
        print(f"wrote {BASELINE.relative_to(ROOT_DIR)}")


if __name__ == "__main__":
    main()
