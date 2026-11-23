"""Counts what benchmarks do, rather than timing them (docs/profiling.md
section 3.1): the instructions each retires and the cycles it takes, from
/usr/bin/time -l, and what it allocates. A loaded machine barely changes
the instructions retired, so they compare builds without a quiet machine.

    python3.11 tools/perf/counts.py fft lexgen
        .build/perf/NAME.TAG for each tag (--tags, by default mlton,ssac,arm64)
    python3.11 tools/perf/counts.py --results after.jsonl --against before.jsonl fft
        also appends each count to after.jsonl, and prints each one's ratio
        to before.jsonl's for the same benchmark, tag, and count

The tag mlton is the original built by MLton (benchmarks/mlton/run.py's
build, copied to DIR/NAME.mlton); the others are tools/perf/variants.py's
builds. Quest's allocation is QUEST_GC_STATS=1's; MLton's is its
@MLton gc-summary's.
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from perfutil import BUILD, DEFAULT_SCALE, count_of, run_in_scratch

FIELDS = {"instructions": r"(\d+)\s+instructions retired", "cycles": r"(\d+)\s+cycles elapsed"}


def mlton_binary(name: str, directory: Path) -> Path:
    """DIR/NAME.mlton, built by run.py's MLton build if it is missing"""
    from run import build_original
    target = directory / f"{name}.mlton"
    if not target.exists():
        shutil.copy2(build_original(name), target)
    return target


def allocated(tag: str, stderr: str) -> int | None:
    """The bytes the run allocated, from its collector's summary"""
    if tag == "mlton":
        m = re.search(r"total bytes allocated: ([\d,]+)", stderr)
        return int(m.group(1).replace(",", "")) if m else None
    m = re.search(r"allocated (\d+) MB", stderr)
    return int(m.group(1)) * 1_000_000 if m else None


def count_run(binary: Path, tag: str, count: int) -> dict:
    """One run's counts"""
    options = ["@MLton", "gc-summary", "--"] if tag == "mlton" else []
    env = {} if tag == "mlton" else {"QUEST_GC_STATS": "1"}
    proc = run_in_scratch(["/usr/bin/time", "-l", str(binary), *options, str(count)], env=env, capture_stderr=True)
    row: dict = {"status": proc.returncode}
    for key, pattern in FIELDS.items():
        m = re.search(pattern, proc.stderr)
        row[key] = int(m.group(1)) if m else None
    row["allocated"] = allocated(tag, proc.stderr)
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("names", nargs="+", help="benchmarks, run as DIR/NAME.TAG")
    parser.add_argument("--tags", default="mlton,ssac,arm64", help="comma-separated; the first is the base")
    parser.add_argument("--dir", type=Path, default=BUILD, help="where the binaries are (default .build/perf)")
    parser.add_argument("--scale", type=float, default=DEFAULT_SCALE, help="of the suite's counts (default 1/32)")
    parser.add_argument("--count", type=int, help="run every benchmark at this count")
    parser.add_argument("--results", type=Path, help="append each count to this JSONL file")
    parser.add_argument("--against", type=Path, help="print each count's ratio to this JSONL file's")
    args = parser.parse_args()
    tags = args.tags.split(",")
    earlier: dict[tuple[str, str, int], dict] = {}
    if args.against:
        for line in args.against.read_text().splitlines():
            r = json.loads(line)
            earlier[r["name"], r["tag"], r["count"]] = r
    for name in args.names:
        count = count_of(name, args.scale, args.count)
        rows = {}
        for tag in tags:
            binary = mlton_binary(name, args.dir) if tag == "mlton" else args.dir / f"{name}.{tag}"
            if not binary.exists():
                sys.exit(f"no {binary} (tools/perf/variants.py builds it)")
            rows[tag] = {"name": name, "tag": tag, "count": count, **count_run(binary, tag, count)}
            if args.results:
                with args.results.open("a") as out:
                    out.write(json.dumps(rows[tag]) + "\n")
        base = rows[tags[0]]["instructions"] or 1
        cells = []
        for tag in tags:
            r = rows[tag]
            if r["instructions"] is None:
                cells.append(f"{tag}=failed ({r['status']})")
                continue
            cell = f"{tag}={r['instructions'] / 1e9:6.2f}G ({r['instructions'] / base:4.2f})"
            before = earlier.get((name, tag, count))
            if before and before.get("instructions"):
                cell += f" was {r['instructions'] / before['instructions']:5.3f}"
            cells.append(cell)
        print(f"{name:16} n={count:<5} " + "  ".join(cells), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
