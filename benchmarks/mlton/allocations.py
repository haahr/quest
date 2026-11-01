#!/usr/bin/env python3
"""Counts the MLton benchmarks' allocations, by the function that makes them.

    allocations.py NAME... [--backend b] [--whole-program] [--scale s | --count n]

builds each conversion as run.py does (into .build/ here, with --compiler or
./quest), runs it once in a scratch directory with allocations.c interposed on
the collector's allocators, and prints its allocations and their bytes, in all
and by function, most first. An allocation the runtime makes for compiled code
(through quest_alloc, or a quest_ function such as a conversion or a string
operation) is counted to the compiled function that called it, the runtime's
function named after it. --sites also lists the allocating call sites.

The counts are the collector's calls; GC_malloc_atomic's are included.
docs/escape-analysis.md section 4 uses them.
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
SOURCE = HERE / "allocations.c"
DYLIB = run.BUILD_DIR / "allocations.dylib"


def interposer() -> Path:
    """allocations.c built as a library, rebuilt when it has changed."""
    if not DYLIB.is_file() or DYLIB.stat().st_mtime < SOURCE.stat().st_mtime:
        DYLIB.parent.mkdir(parents=True, exist_ok=True)
        prefix = subprocess.run(["brew", "--prefix", "bdw-gc"], capture_output=True, text=True).stdout.strip()
        subprocess.run(["clang", "-dynamiclib", "-O2", "-fno-omit-frame-pointer", "-o", str(DYLIB), str(SOURCE),
                        f"-L{prefix or '/opt/homebrew/opt/bdw-gc'}/lib", "-lgc"], check=True)
    return DYLIB


def counted(binary: Path, count: int, timeout: float) -> list[tuple[str, str, int, int]]:
    """The interposer's lines from running binary with count in a scratch
    directory holding a copy of DATA/: two return addresses, a count, and
    bytes."""
    with tempfile.TemporaryDirectory() as d:
        work = Path(d)
        shutil.copytree(run.DATA_DIR, work / "DATA")
        out = work / "allocations.txt"
        env = dict(os.environ, DYLD_INSERT_LIBRARIES=str(interposer()), QUEST_ALLOCATIONS_OUT=str(out))
        subprocess.run([str(binary), str(count)], cwd=work, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                       preexec_fn=run.deep_stack, env=env, timeout=timeout, check=True)
        rows = [line.split() for line in out.read_text().splitlines()]
    return [(r[0], r[1], int(r[2]), int(r[3])) for r in rows]


def symbolize(binary: Path, addresses: list[str]) -> dict[str, tuple[str, str]]:
    """Each address's function and source position (or offset), by atos."""
    names = {"0x0": ("(outside the program)", "")}
    wanted = sorted(set(addresses) - set(names))
    for start in range(0, len(wanted), 2000):
        chunk = wanted[start:start + 2000]
        lines = subprocess.run(["atos", "-o", str(binary), "-l", "0x100000000", *chunk],
                               capture_output=True, text=True, check=True).stdout.splitlines()
        for address, line in zip(chunk, lines):
            function, _, rest = line.partition(" (in ")
            where = rest.partition(") ")[2] or address
            names[address] = (function, where.strip("()"))
    return names


def report(name: str, binary: Path, count: int, args: argparse.Namespace) -> None:
    rows = counted(binary, count, args.timeout)
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
    parser.add_argument("--timeout", type=float, default=3600.0, help="seconds a run may take")
    parser.add_argument("--clean", action="store_true", help="remove .build/ first, as run.py --clean does")
    args = parser.parse_args()
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
