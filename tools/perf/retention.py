"""What a program keeps alive, compared at the same points (docs/profiling.md
section 6). The collector collects where its heuristics say, which differ
between builds and between runs, so the runtime's `collect` mode
(QUEST_GC_CHECK=collect with QUEST_GC_COLLECT_EVERY=N) forces a collection
every N allocations, the same points in every build of one program.

    python3.11 tools/perf/retention.py live .build/perf/mlyacc.ssac .build/perf/mlyacc.arm64
        the live data at each forced collection: the median and largest for
        each binary, and the points where they differ most from the first's
    python3.11 tools/perf/retention.py dead mlyacc --at 120
        stopped at the 120th forced collection, the words of each Quest
        frame that point into the heap but hold no value live across the
        call the frame is in: what a precise collector would not keep

dead builds NAME with the arm64 backend and QUEST_LIVE_SLOTS=1, which puts at
each call's return address a symbol and a comment saying where the values live
across the call are (the code is the same as without it), into
.build/perf/live/, and prints the program's assembly there too.
"""

import argparse
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from perfutil import BENCHMARKS, BUILD, DATA, ROOT, run_in_scratch

FRAMES = Path(__file__).resolve().parent / "lldb_frames.py"


def forcing(every: int, trap: int = 0) -> dict[str, str]:
    """The environment that forces a collection every `every` allocations,
    printing FORCED before each, and stops at the trap-th in quest_gc_trap"""
    return {"QUEST_GC_CHECK": "collect", "QUEST_GC_COLLECT_EVERY": str(every), "QUEST_GC_COLLECT_TRAP": str(trap),
            "QUEST_GC_STATS": "each"}


def series(binary: Path, count: int, every: int) -> dict[int, int]:
    """The live data, in KB, after each forced collection"""
    err = run_in_scratch([str(binary.resolve()), str(count)], capture_stderr=True, env=forcing(every)).stderr
    out, forced = {}, None
    for line in err.splitlines():
        m = re.match(r"FORCED (\d+)", line)
        if m:
            forced = int(m.group(1))
            continue
        m = re.match(r"quest: gc #\d+: live (\d+) KB", line)
        if m and forced is not None:
            out[forced] = int(m.group(1))
            forced = None
    return out


def live(args: argparse.Namespace) -> int:
    runs = [series(b, args.count, args.every) for b in args.binaries]
    for b, s in zip(args.binaries, runs):
        values = list(s.values()) or [0]
        print(f"{b.name:24} {len(s):5} points  median {statistics.median(values):7.0f} KiB  "
              f"max {max(values):7.0f} KiB")
    if len(runs) > 1:
        base = runs[0]
        points = sorted(set(base).intersection(*runs[1:]))
        worst = sorted(points, key=lambda k: -max(abs(r[k] - base[k]) for r in runs[1:]))[:args.top]
        print(f"\nthe {len(worst)} points differing most from {args.binaries[0].name}:")
        for k in sorted(worst):
            print(f"  {k:5}" + "".join(f"  {r[k]:7}" for r in runs))
    return 0


def dead(args: argparse.Namespace) -> int:
    out = BUILD / "live"
    out.mkdir(parents=True, exist_ok=True)
    build = out / "build"
    shutil.rmtree(build, ignore_errors=True)
    source = BENCHMARKS / f"{args.name}.quest"
    binary, asm, nm = out / f"{args.name}.arm64", out / f"{args.name}.s", out / f"{args.name}.nm"
    env = {**os.environ, "QUEST_LIVE_SLOTS": "1", "QUEST_JOBS": os.environ.get("QUEST_JOBS", "8")}
    common = ["--backend", "arm64", "--whole-program", "--build-dir", str(build)]
    subprocess.run([str(ROOT / "quest"), "compile", *common, "-o", str(binary), str(source)], env=env, check=True)
    with open(asm, "w") as f:
        subprocess.run([str(ROOT / "quest"), *common, "--stop-after", "codegen_arm64", str(source)], env=env,
                       stdout=f, check=True, cwd=BENCHMARKS)
    symbols = subprocess.run(["nm", str(binary)], capture_output=True, text=True, check=True).stdout
    nm.write_text("".join(line + "\n" for line in symbols.splitlines() if "_live_" in line))
    work = Path(tempfile.mkdtemp(prefix="quest-perf-"))
    try:
        shutil.copytree(DATA, work / "DATA")
        variables = " ".join(f"{k}={v}" for k, v in forcing(args.every, args.at).items())
        report = subprocess.run(["lldb", "--batch", "-o", f"command script import {FRAMES}",
                                 "-o", f"settings set target.env-vars {variables}", "-o", "b quest_gc_trap",
                                 "-o", f"process launch -o /dev/null -e /dev/null -- {args.count}",
                                 "-o", f"deadroots {asm} {nm}", "-o", "bt", "-o", "kill", str(binary)],
                                cwd=work, capture_output=True, text=True).stdout
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for line in report.splitlines():
        if line.startswith(("DEAD", "SAVED")) or re.match(r"\s+(\* )?frame #", line):
            print(line)
    print(f"\nannotated assembly: {asm}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("live", help="live data at forced collections")
    p.add_argument("binaries", nargs="+", type=Path)
    p.add_argument("--top", type=int, default=10, help="how many differing points to show (default 10)")
    p = sub.add_parser("dead", help="dead words in frames at a forced collection")
    p.add_argument("name", help="a benchmark (benchmarks/mlton/NAME.quest)")
    p.add_argument("--at", type=int, required=True, help="which forced collection")
    for p in sub.choices.values():
        p.add_argument("--every", type=int, default=20000, help="allocations between collections (default 20000)")
        p.add_argument("--count", type=int, default=3, help="the count to run at (default 3)")
    args = parser.parse_args()
    return live(args) if args.command == "live" else dead(args)


if __name__ == "__main__":
    sys.exit(main())
