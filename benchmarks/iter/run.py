#!/opt/homebrew/bin/python3.11
"""Counts util/iter's cost per element (benchmarks/iter/README.md,
docs/iter.md section 2).

    benchmarks/iter/run.py [--elements N] [--only NAME,...]

It builds iter.quest three times with ./quest: as separate units (the
default, which inlines util/maybe, util/iter, and collections/vector into
their importers, docs/inlined-modules-plan.md), as separate units inlining
none of them (--no-inline-library), and with --whole-program. It runs each
workload once in each under /usr/bin/time -l, checks that the builds print
the same sum, and prints the instructions retired per element, which load
barely changes, and the seconds.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
WORK = ROOT / ".build" / "iter-bench"

WORKLOADS = [
    ("loop", "a for loop written out: map and filter inline"),
    ("map", "range, map, and the program's loop through iter.more and iter.next"),
    ("filter", "range, map, filter, and the program's loop"),
    ("sumInt", "range, map, filter, and iter.sumInt, which reads the closures in place"),
]

BUILDS = [("separate", []), ("no-inline", ["--no-inline-library"]), ("whole", ["--whole-program"])]


def build() -> dict[str, Path]:
    """The program of each build"""
    programs = {}
    for name, flags in BUILDS:
        program = WORK / f"iter-{name}"
        done = subprocess.run([str(ROOT / "quest"), "compile", *flags, "--build-dir", str(WORK / f"build-{name}"),
                               "-o", str(program), str(HERE / "iter.quest")], capture_output=True, text=True)
        if done.returncode != 0:
            sys.exit(f"run.py: iter.quest did not compile ({name}):\n{done.stdout}{done.stderr}")
        programs[name] = program
    return programs


def measure(program: Path, workload: str, elements: int) -> tuple[str, int, float]:
    """The sum the program prints, the instructions it retired, and its seconds"""
    done = subprocess.run(["/usr/bin/time", "-l", str(program), workload, str(elements)], capture_output=True,
                          text=True)
    if done.returncode != 0:
        sys.exit(f"run.py: {program.name} {workload} failed:\n{done.stderr}")
    instructions = re.search(r"(\d+)\s+instructions retired", done.stderr)
    seconds = re.search(r"([\d.]+) real", done.stderr)
    return done.stdout.strip(), int(instructions.group(1)) if instructions else 0, float(seconds.group(1))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--elements", type=int, default=20_000_000, help="the integers each workload walks")
    parser.add_argument("--only", help="the workloads to run, comma-separated")
    options = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    programs = build()
    chosen = [w for w in WORKLOADS if not options.only or w[0] in options.only.split(",")]
    print(f"{'workload':<10} " + " ".join(f"{n + ' instr':>15} {n + ' s':>11}" for n, _ in BUILDS) + "  sum")
    failed = False
    for name, _ in chosen:
        sums, cells = set(), []
        for build_name, _ in BUILDS:
            total, instructions, seconds = measure(programs[build_name], name, options.elements)
            sums.add(total)
            cells.append(f"{instructions / options.elements:15.1f} {seconds:11.3f}")
        failed |= len(sums) != 1
        print(f"{name:<10} " + " ".join(cells) + f"  {' / '.join(sorted(sums))}")
    if failed:
        sys.exit("run.py: the builds disagree")


if __name__ == "__main__":
    main()
