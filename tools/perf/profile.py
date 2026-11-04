"""Profiles a binary by its program counter (docs/profiling.md section 4):
where its time goes, by symbol, and within one function by instruction.
macOS's sample(1) attributes time only to functions, and Instruments needs
Xcode; this needs only clang, and works on any backend's binaries.

    python3.11 tools/perf/profile.py .build/perf/life.arm64
        the symbols with the most samples, over three runs
    python3.11 tools/perf/profile.py .build/perf/life.arm64 -f qf_nthgen
        and qf_nthgen's hottest instructions
    python3.11 tools/perf/profile.py .build/perf/life.arm64 -f qf_nthgen --listing
        and all of qf_nthgen, each instruction with its samples
    python3.11 tools/perf/profile.py --count 2 --runs 5 .build/perf/zebra.ssac

The binary runs as tools/perf/timeit.py runs it, with tools/perf/pcprof.c
loaded (built into .build/perf/ when it is older than its source), which
samples each running thread every interval. Samples in the kernel (threads
running a system call) are left out of the table unless --kernel is given;
a blocked thread is not sampled. A program migrates between performance
and efficiency cores, so compare where the time goes within a binary, not
the totals of two runs or two binaries; timeit.py compares those.
"""

import argparse
import collections
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from perfutil import BUILD, DEFAULT_SCALE, benchmark_of, count_of, run_in_scratch

SOURCE = Path(__file__).resolve().parent / "pcprof.c"
KERNEL = ("libsystem_kernel.dylib",)


def sampler() -> Path:
    """The sampler library, built if its source is newer"""
    lib = BUILD / "pcprof.dylib"
    if not lib.exists() or lib.stat().st_mtime < SOURCE.stat().st_mtime:
        BUILD.mkdir(parents=True, exist_ok=True)
        subprocess.run(["clang", "-O2", "-Wall", "-dynamiclib", str(SOURCE), "-o", str(lib)], check=True)
    return lib


def samples(binary: Path, count: int, runs: int, interval: int) -> list[tuple[int, str, str]]:
    """Each sample of runs runs: its address in the binary's own numbering (for
    the main executable's code), its image, and its symbol"""
    lib = sampler()
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(runs):
            path = Path(tmp) / f"run{k}"
            run_in_scratch([str(binary.resolve()), str(count)],
                           env={"DYLD_INSERT_LIBRARIES": str(lib), "PCPROF_OUT": str(path),
                                "PCPROF_INTERVAL_US": str(interval)})
            lines = path.read_text().splitlines()
            slide = int(lines[0].split()[1], 16)
            for line in lines[1:]:
                pc, image, symbol = line.split(" ", 2)
                out.append((int(pc, 16) - slide, image, symbol))
    return out


def listing(binary: Path, function: str) -> list[tuple[int, str]]:
    """The function's instructions, as otool prints them: address and text"""
    text = subprocess.run(["otool", "-tvV", str(binary)], capture_output=True, text=True, check=True).stdout
    out, inside = [], False
    for line in text.splitlines():
        m = re.match(r"^(\S+):$", line)
        if m:
            inside = m.group(1) in (function, "_" + function)
            continue
        parts = line.split("\t")
        if inside and len(parts) > 1 and re.match(r"^[0-9a-f]+$", parts[0]):
            out.append((int(parts[0], 16), "\t".join(parts[1:])))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("binary", type=Path)
    parser.add_argument("-f", "--function", help="show this function's instructions (qf_nthgen, or _qf_nthgen)")
    parser.add_argument("--listing", action="store_true", help="the whole function, not only its hottest")
    parser.add_argument("--top", type=int, default=30, help="how many symbols or instructions (default 30)")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--interval", type=int, default=1000, help="microseconds between samples (default 1000)")
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="of the suite's counts (default 1/32)")
    parser.add_argument("--count", type=int, help="the count to run the benchmark at")
    parser.add_argument("--kernel", action="store_true", help="count samples in the kernel too")
    args = parser.parse_args()
    count = count_of(benchmark_of(args.binary), args.scale, args.count)
    taken = samples(args.binary, count, args.runs, args.interval)
    me = args.binary.name
    kept = [s for s in taken if args.kernel or s[1] not in KERNEL]
    print(f"{len(taken)} samples over {args.runs} runs at count {count}; {len(taken) - len(kept)} in the kernel"
          f"{'' if args.kernel else ', left out'}")
    by_symbol = collections.Counter(s[2] if s[1] == me else f"[{s[1]}] {s[2]}" for s in kept)
    by_image = collections.Counter("(this binary)" if s[1] == me else s[1] for s in kept)
    for image, n in by_image.most_common():
        print(f"  {n:7} {100 * n / len(kept):5.1f}%  {image}")
    print()
    for symbol, n in by_symbol.most_common(args.top):
        print(f"  {n:7} {100 * n / len(kept):5.1f}%  {symbol}")
    if args.function:
        code = listing(args.binary, args.function)
        if not code:
            sys.exit(f"no function {args.function} in {args.binary}")
        at = collections.Counter(a for a, image, _ in kept if image == me)
        total = sum(at[a] for a, _ in code)
        print(f"\n{args.function}: {total} samples, {len(code)} instructions")
        shown = code if args.listing else sorted(code, key=lambda c: -at[c[0]])[:args.top]
        for address, text in shown:
            print(f"  {at[address]:6} {address:x}  {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
