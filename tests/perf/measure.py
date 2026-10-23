"""Measures the C backend, for comparing the IR backend against today's (docs/ir.md §12, steps 0 and 6).

    python tests/perf/measure.py             # print a summary, comparing with tests/perf/baseline.json if present
    python tests/perf/measure.py --save      # also write the measurements to tests/perf/baseline.json

Two measurements:

- C generation: for every golden test program that is compiled to C, the time spent in the C emitter (emit_program
  and emit_module, so neither type checking nor clang) and the size of the C it produces.
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

from quest.codegen import compile_c_source, run_binary  # noqa: E402
from quest.codegen import c_emitter  # noqa: E402
from quest.pipeline import compile_pipeline  # noqa: E402
from quest.testing.runner import discover_tests, parse_skipped_phases  # noqa: E402

HERE = Path(__file__).resolve().parent
BASELINE = HERE / "baseline.json"
SOURCE_DIR = ROOT_DIR / "tests" / "source"
RUNS = 5


def _timed_emitter() -> list[float]:
    """Wraps the emitter's entry points so that the time spent in them is recorded."""
    spent: list[float] = []
    for name in ("emit_program", "emit_module"):
        original = getattr(c_emitter.CEmitter, name)

        def timed(self, *args, _original=original, **kwargs):
            start = time.perf_counter()
            try:
                return _original(self, *args, **kwargs)
            finally:
                spent.append(time.perf_counter() - start)

        setattr(c_emitter.CEmitter, name, timed)
    return spent


def measure_generation() -> dict:
    spent = _timed_emitter()
    programs: dict[str, list[float | int]] = {}
    for path in discover_tests(SOURCE_DIR):
        if "run_c_compiled" in parse_skipped_phases(path):
            continue
        spent.clear()
        res = compile_pipeline().execute(path.read_text(), str(path))
        if not res.success or "codegen_c" not in res.artifacts:
            continue
        programs[str(path.relative_to(ROOT_DIR))] = [round(sum(spent), 4), len(res.artifacts["codegen_c"])]
    return {
        "programs": len(programs),
        "seconds": round(sum(p[0] for p in programs.values()), 3),
        "c_bytes": sum(p[1] for p in programs.values()),
        "per_program": programs,
    }


def measure_benchmarks() -> dict:
    results: dict[str, dict] = {}
    for path in sorted(HERE.glob("*.quest")):
        res = compile_pipeline().execute(path.read_text(), str(path))
        if not res.success:
            raise SystemExit(f"{path.name}: {[d.message for d in res.diagnostics]}")
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / path.stem
            compile_c_source(res.artifacts["codegen_c"], output_path=binary)
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
