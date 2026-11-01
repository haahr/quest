"""What the profiling tools share (docs/profiling.md): where things are, the
benchmarks' counts, and running a benchmark's binary as benchmarks/mlton/run.py
does, in a scratch directory holding a copy of DATA/."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCHMARKS = ROOT / "benchmarks" / "mlton"
DATA = BENCHMARKS / "DATA"
BUILD = ROOT / ".build" / "perf"

sys.path.insert(0, str(BENCHMARKS))
from run import COUNTS  # noqa: E402

# A thirty-second of MLton's counts: one to three seconds of a Quest program
# on an M-series Mac, enough to time and profile without waiting
DEFAULT_SCALE = 1 / 32


def count_of(name: str, scale: float = DEFAULT_SCALE, count: int | None = None) -> int:
    """The count to run a benchmark at: count if given, else its suite count
    scaled. A program that is not a benchmark runs at count 1."""
    if count is not None:
        return count
    return max(1, round(COUNTS[name] * scale)) if name in COUNTS else 1


def benchmark_of(binary: Path) -> str:
    """The benchmark a binary was built from, by the variants.py naming,
    NAME.BACKEND, or its whole name"""
    return binary.name.split(".")[0]


def run_in_scratch(command: list[str], env: dict[str, str] | None = None,
                   capture_stderr: bool = False) -> subprocess.CompletedProcess:
    """Runs command in a new directory holding a copy of DATA/, with its output
    discarded (and its standard error captured, if asked)"""
    work = Path(tempfile.mkdtemp(prefix="quest-perf-"))
    try:
        shutil.copytree(DATA, work / "DATA")
        return subprocess.run(command, cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE if capture_stderr else None, text=True,
                              env={**os.environ, **(env or {})})
    finally:
        shutil.rmtree(work, ignore_errors=True)
