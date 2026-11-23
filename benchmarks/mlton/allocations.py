#!/usr/bin/env python3
"""Counts the MLton benchmarks' allocations, by the function that makes them.

    allocations.py NAME... [--backend b] [--whole-program] [--scale s | --count n]

builds each conversion as run.py does (into .build/ here, with --compiler or
./quest), runs it once in a scratch directory under the runtime's
`allocations` mode (QUEST_GC_CHECK=allocations, which counts every allocation
by the allocating function and its caller), and prints its allocations and
their bytes, in all and by function, most first. An allocation the runtime
makes for compiled code (through quest_alloc, or a quest_ function such as a
conversion or a string operation) is counted to the compiled function that
called it, the runtime's function named after it. --sites also lists the
allocating call sites. --by-layout lists them by layout instead: each layout's
allocations and bytes, and its sizes when it has several (the runtime's
census, written to $QUEST_LAYOUTS_OUT); an option made at a known case has
that case's layout, so its cases are apart.
docs/benchmarks.md section 9 records them.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import run

HERE = Path(__file__).resolve().parent
def counted(binary: Path, count: int, timeout: float) -> tuple[list[tuple[str, str, int, int]], list[str]]:
    """The runtime's lines from running binary with count in a scratch
    directory holding a copy of DATA/: two return addresses, a count, and
    bytes; and its census's lines by layout (quest_gc_dump_layouts)."""
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        shutil.copytree(run.DATA_DIR, work / "DATA")
        out = work / "allocations.txt"
        layouts = work / "layouts.txt"
        env = dict(os.environ, QUEST_GC_CHECK="allocations", QUEST_ALLOCATIONS_OUT=str(out),
                   QUEST_LAYOUTS_OUT=str(layouts))
        subprocess.run([str(binary), str(count)], cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       preexec_fn=run.deep_stack, env=env, timeout=timeout, check=True)
        rows = [line.split() for line in out.read_text().splitlines()]
        census = layouts.read_text().splitlines() if layouts.exists() else []
    return [(r[0], r[1], int(r[2]), int(r[3])) for r in rows], census


def by_layout(name: str, census: list[str], args: argparse.Namespace) -> None:
    """The census by layout, the most bytes first, with each size of a layout
    made at several"""
    rows = []
    for line in census:
        total, n, size, layout = line.split(" ", 3)
        rows.append((int(total), int(n), int(size), layout))
    bytes_all = sum(r[2] for r in rows)
    by_name: Counter[str] = Counter()
    for r in rows:
        by_name[r[3]] += r[2]
    print(f"{name}: {sum(r[1] for r in rows):,} allocations by layout, {bytes_all:,} bytes")
    for layout, size in by_name.most_common(args.top):
        mine = sorted((r for r in rows if r[3] == layout), key=lambda r: -r[2])
        n = sum(r[1] for r in mine)
        each = f"{mine[0][0]} B each" if len(mine) == 1 else "sizes below"
        print(f"  {size:17,} B {100 * size / max(bytes_all, 1):5.1f}% {n:15,}  {each:>12}  {layout}")
        if len(mine) > 1:
            for total, k, s, _ in mine[:4]:
                print(f"  {s:17,} B {100 * s / max(bytes_all, 1):5.1f}% {k:15,}  {total:>5} B each")


def report(name: str, binary: Path, count: int, args: argparse.Namespace) -> None:
    rows, census = counted(binary, count, args.timeout)
    if args.by_layout:
        by_layout(name, census, args)
        return
    names = symbolize(binary, [a for r in rows for a in r[:2]])
    by_function: Counter[str] = Counter()
    bytes_by_function: Counter[str] = Counter()
    by_site: Counter[str] = Counter()
    for first, second, n, size in rows:
        function, where = names[first]
        # The runtime's allocations count to the compiled code that asked for them
        if function.startswith("quest_") and second != "0x0":
            caller, where = names[second]
            function = caller if function == "quest_alloc" else f"{caller} (via {function})"
        by_function[function] += n
        bytes_by_function[function] += size
        by_site[f"{function} at {where}"] += n
    total = sum(by_function.values())
    print(f"{name} n={count}: {total:,} allocations, {sum(bytes_by_function.values()):,} bytes")
    for function, n in by_function.most_common(args.top):
        print(f"  {n:15,} {100 * n / max(total, 1):5.1f}% {bytes_by_function[function]:17,} B  {function}")
    if args.sites:
        print("  sites:")
        for site, n in by_site.most_common(args.top):
            print(f"  {n:15,} {100 * n / max(total, 1):5.1f}%  {site}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+")
    parser.add_argument("--compiler", default=str(run.ROOT / "quest"), help="the Quest compiler (default ./quest)")
    parser.add_argument("--backend", help="build with this backend: c, ssac, or arm64")
    parser.add_argument("--whole-program", action="store_true", help="build each as a whole program")
    parser.add_argument("--scale", type=float, default=0.25, help="multiply the suite's counts by this (default 0.25)")
    parser.add_argument("--count", type=int, help="run every program at this count")
    parser.add_argument("--top", type=int, default=12, help="list this many functions (default 12)")
    parser.add_argument("--sites", action="store_true", help="also list the allocating call sites")
    parser.add_argument("--by-layout", action="store_true", help="list allocations by layout instead")
    parser.add_argument("--timeout", type=float, default=3600.0, help="seconds a run may take")
    parser.add_argument("--clean", action="store_true", help="remove .build/ first, as run.py --clean does")
    args = parser.parse_args()
    # Heavy, though counts need no quiet machine: it waits while another job
    # holds the machine-wide lock (docs/testing.md section 4.2)
    run.exclusive.yield_to_holder("allocations.py")
    names = run.benchmark_names(args.names)
    if args.clean:
        shutil.rmtree(run.BUILD_DIR, ignore_errors=True)
    compiler = [str(Path(args.compiler).resolve()) if "/" in args.compiler else args.compiler]
    for name in names:
        binary = run.build_conversion(name, compiler, args.backend, args.whole_program)
        report(name, binary, args.count or max(1, round(run.COUNTS[name] * args.scale)), args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
