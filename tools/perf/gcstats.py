"""Summarizes what the collector did in runs of binaries (docs/profiling.md
section 6), from the runtime's QUEST_GC_STATS=each output: how many
collections, full and minor, how long they paused the program, how much was
allocated, and how much was alive at the full ones. Builds of one program from the same SSA allocate the same, so a
difference in what is alive is a difference in what the stack and registers
hold: the collector scans them conservatively, and keeps whatever a dead slot
points to.

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
    err = run_in_scratch([str(binary.resolve()), str(count)], env={"QUEST_GC_STATS": "each"},
                         capture_stderr=True).stderr
    collections = minors = 0
    pause_ms = minor_pause_ms = allocated_mb = 0.0
    live, heap = [], []
    for line in err.splitlines():
        m = re.match(r"quest: gc #\d+: live (\d+) KB in \d+ KB of lines, heap (\d+) KB, ([0-9.]+) ms", line)
        if m:
            collections += 1
            live.append(int(m.group(1)))
            heap.append(int(m.group(2)))
            pause_ms += float(m.group(3))
        m = re.match(r"quest: gc minor #\d+: .*heap (\d+) KB, ([0-9.]+) ms", line)
        if m:
            minors += 1
            heap.append(int(m.group(1)))
            minor_pause_ms += float(m.group(2))
        m = re.match(r"quest: gc stats: .*allocated (\d+) MB", line)
        if m:
            allocated_mb = float(m.group(1))
    return {"collections": collections, "minors": minors, "pause_ms": pause_ms, "minor_pause_ms": minor_pause_ms,
            "allocated_mb": allocated_mb, "live_median": statistics.median(live) if live else 0,
            "live_max": max(live, default=0), "heap_max": max(heap, default=0)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("binaries", nargs="+", type=Path)
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="of the suite's counts (default 1/32)")
    parser.add_argument("--count", type=int, help="the count to run each benchmark at")
    args = parser.parse_args()
    print(f"{'binary':20} {'count':>5} {'full':>6} {'pauses':>9} {'minor':>6} {'pauses':>9} {'allocated':>9} "
          f"{'live, median':>13} {'live, max':>10} {'heap, max':>10}")
    for binary in args.binaries:
        n = count_of(benchmark_of(binary), args.scale, args.count)
        s = stats(binary, n)
        print(f"{binary.name:20} {n:5} {s['collections']:6} {s['pause_ms']:6.0f} ms {s['minors']:6} "
              f"{s['minor_pause_ms']:6.0f} ms {s['allocated_mb']:6.0f} MB {s['live_median']:9.0f} KiB "
              f"{s['live_max']:6.0f} KiB {s['heap_max']:6.0f} KiB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
