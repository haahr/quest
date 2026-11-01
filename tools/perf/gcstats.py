"""Summarizes what the collector did in runs of binaries (docs/profiling.md
section 6), from the Boehm collector's GC_PRINT_STATS output: how many
collections, how long marking took, how much was freed, and how much was
alive. Builds of one program from the same SSA allocate the same, so a
difference in what is alive is a difference in what the stack and registers
hold: a conservative collector keeps whatever a dead slot points to.

    python3.11 tools/perf/gcstats.py .build/perf/mlyacc.c .build/perf/mlyacc.ssac .build/perf/mlyacc.arm64
    python3.11 tools/perf/gcstats.py --count 1 .build/perf/mlyacc.arm64
"""

import argparse
import re
import statistics
import sys
from pathlib import Path

from perfutil import DEFAULT_SCALE, benchmark_of, count_of, run_in_scratch


def stats(binary: Path, count: int) -> dict[str, float]:
    err = run_in_scratch([str(binary.resolve()), str(count)], env={"GC_PRINT_STATS": "1"},
                         capture_stderr=True).stderr
    collections = freed = 0
    mark_ns = 0
    live, heap = [], []
    for line in err.splitlines():
        m = re.match(r"GC #\d+ freed (-?\d+) bytes, heap (\d+) KiB", line)
        if m:
            collections += 1
            freed += int(m.group(1))
            heap.append(int(m.group(2)))
        m = re.match(r"World-stopped marking took (\d+) ms (\d+) ns", line)
        if m:
            mark_ns += int(m.group(1)) * 1_000_000 + int(m.group(2))
        m = re.match(r"In-use heap: \d+% \((\d+) KiB pointers", line)
        if m:
            live.append(int(m.group(1)))
    return {"collections": collections, "mark_ms": mark_ns / 1e6, "freed_mb": freed / 1e6,
            "live_median": statistics.median(live) if live else 0, "live_max": max(live, default=0),
            "heap_max": max(heap, default=0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("binaries", nargs="+", type=Path)
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="of the suite's counts (default 1/32)")
    parser.add_argument("--count", type=int, help="the count to run each benchmark at")
    args = parser.parse_args()
    print(f"{'binary':20} {'count':>5} {'GCs':>6} {'marking':>9} {'freed':>9} {'live, median':>13} "
          f"{'live, max':>10} {'heap, max':>10}")
    for binary in args.binaries:
        n = count_of(benchmark_of(binary), args.scale, args.count)
        s = stats(binary, n)
        print(f"{binary.name:20} {n:5} {s['collections']:6} {s['mark_ms']:6.0f} ms {s['freed_mb']:6.0f} MB "
              f"{s['live_median']:9.0f} KiB {s['live_max']:6.0f} KiB {s['heap_max']:6.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
