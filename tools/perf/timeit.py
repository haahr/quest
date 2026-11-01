"""Times builds of the same benchmarks against each other (docs/profiling.md
section 3): each binary's least user time over several rounds, the binaries
of a benchmark run in turn within each round, so that a change in the
machine's load affects them alike.

    python3.11 tools/perf/timeit.py life mlyacc
        .build/perf/{life,mlyacc}.{c,ssac,arm64}, three rounds, at a
        thirty-second of the suite's counts
    python3.11 tools/perf/timeit.py --tags ssac,arm64,try --rounds 5 life
    python3.11 tools/perf/timeit.py --count 4 --dir /tmp/x zebra

Prints each binary's time and its ratio to the first tag's. User time, from
the children's resource usage, leaves out the system's time (ray, which
writes a character at a time, spends most of its elapsed time there).
"""

import argparse
import resource
import sys
from pathlib import Path

from perfutil import BUILD, DEFAULT_SCALE, count_of, run_in_scratch


def user_time(command: list[str]) -> float:
    """The user time of running command in a scratch directory"""
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime
    proc = run_in_scratch(command)
    elapsed = resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime - before
    if proc.returncode != 0:
        print(f"FAILED (exit {proc.returncode}): {' '.join(command)}", flush=True)
    return elapsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+", help="benchmarks, run as DIR/NAME.TAG")
    parser.add_argument("--tags", default="c,ssac,arm64", help="comma-separated; the first is the base")
    parser.add_argument("--dir", type=Path, default=BUILD, help="where the binaries are (default .build/perf)")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="of the suite's counts (default 1/32)")
    parser.add_argument("--count", type=int, help="run every benchmark at this count")
    args = parser.parse_args()
    tags = args.tags.split(",")
    for name in args.names:
        for tag in tags:
            if not (args.dir / f"{name}.{tag}").exists():
                sys.exit(f"no {args.dir / f'{name}.{tag}'} (tools/perf/variants.py builds them)")
    best: dict[tuple[str, str], float] = {}
    for _ in range(args.rounds):
        for name in args.names:
            count = str(count_of(name, args.scale, args.count))
            for tag in tags:
                t = user_time([str(args.dir / f"{name}.{tag}"), count])
                best[name, tag] = min(t, best.get((name, tag), float("inf")))
    for name in args.names:
        base = best[name, tags[0]]
        cells = "".join(f"  {tag}={best[name, tag]:6.2f} ({best[name, tag] / base:4.2f})" for tag in tags)
        print(f"{name:12} n={count_of(name, args.scale, args.count):<5}{cells}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
