"""Compares the instruction mix of two arm64 binaries' Quest code
(docs/profiling.md section 5): what kinds of instructions, and how many of
some patterns that show what a code generator folds and what it does not.

    python3.11 tools/perf/asmstats.py .build/perf/life.ssac .build/perf/life.arm64
        every Quest function (qf_, qv_, and main) of each
    python3.11 tools/perf/asmstats.py A B -f qf_nthgen -f qf_f_5
        those functions alone

Counts are static: instructions in the code, not executed. Each row shows
the first binary's count, the second's, and their ratio.
"""

import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

CATEGORIES = ["instructions", "unconditional branches", "conditional branches", "calls", "register moves",
              "constant moves", "stack loads", "stack stores", "other loads", "other stores", "cset/csel"]
PATTERNS = ["ldp/stp outside the frame", "register-offset or shifted operands", "adrp, add, ldr [x] (a global)",
            "ldr x, ...; mov y, x", "and #0xff after a call", "fmov d, x (a real constant)"]


def functions(binary: Path) -> dict[str, list[tuple[str, str]]]:
    """Each function's instructions, as (operation, operands), by symbol
    without its leading underscore"""
    text = subprocess.run(["otool", "-tvV", str(binary)], capture_output=True, text=True, check=True).stdout
    out: dict[str, list[tuple[str, str]]] = {}
    current = None
    for line in text.splitlines():
        m = re.match(r"^_(\S+):$", line)
        if m:
            current = out.setdefault(m.group(1), [])
            continue
        parts = line.split("\t")
        if current is not None and len(parts) > 1 and re.match(r"^[0-9a-f]+$", parts[0]):
            current.append((parts[1], parts[2] if len(parts) > 2 else ""))
    return out


def is_quest(name: str) -> bool:
    return name.startswith("qf_") or name.startswith("qv_") or name == "main"


def count(code: list[tuple[str, str]], c: collections.Counter) -> None:
    """Adds one function's categories and patterns to c"""
    prev = prev2 = ("", "")
    for op, args in code:
        c["instructions"] += 1
        stack = re.search(r"\[(sp|x29)\b", args) is not None
        if op == "b":
            c["unconditional branches"] += 1
        elif op.startswith("b.") or op in ("cbz", "cbnz", "tbz", "tbnz"):
            c["conditional branches"] += 1
        elif op in ("bl", "blr"):
            c["calls"] += 1
        elif op == "mov" and re.match(r"[xwd]\d+, [xwd]\d+$", args):
            c["register moves"] += 1
        elif op in ("mov", "movz", "movk", "movn"):
            c["constant moves"] += 1
        elif op.startswith("ld"):
            c["stack loads" if stack else "other loads"] += 1
        elif op.startswith("st"):
            c["stack stores" if stack else "other stores"] += 1
        elif op in ("cset", "csel", "csinc", "cinc"):
            c["cset/csel"] += 1
        if op in ("ldp", "stp") and not stack:
            c["ldp/stp outside the frame"] += 1
        if op in ("ldr", "str", "ldrb", "strb", "add", "sub") and re.search(r", (lsl|sxtw|uxtw) #?\d*\]?$", args):
            c["register-offset or shifted operands"] += 1
        if op == "ldr" and re.search(r"\[x\d+\]$", args) and prev[0] == "add" and prev2[0] == "adrp":
            c["adrp, add, ldr [x] (a global)"] += 1
        if op == "mov" and prev[0] == "ldr" and re.match(r"x\d+, x\d+$", args):
            if args.split(", ")[1] == prev[1].split(",")[0]:
                c["ldr x, ...; mov y, x"] += 1
        if op == "and" and args.endswith("#0xff") and prev[0] == "bl":
            c["and #0xff after a call"] += 1
        if op == "fmov" and re.match(r"d\d+, x\d+", args):
            c["fmov d, x (a real constant)"] += 1
        prev2, prev = prev, (op, args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("-f", "--function", action="append", default=[], help="a function (repeatable)")
    args = parser.parse_args()
    fa, fb = functions(args.first), functions(args.second)
    groups = [(f, [f.lstrip("_")]) for f in args.function] or [("Quest functions", None)]
    for title, names in groups:
        ca, cb = collections.Counter(), collections.Counter()
        for fs, c in ((fa, ca), (fb, cb)):
            for name, code in fs.items():
                if (names is None and is_quest(name)) or (names is not None and name in names):
                    count(code, c)
        print(f"{title}: {args.first.name} against {args.second.name}")
        for key in CATEGORIES + PATTERNS:
            ratio = f"{cb[key] / ca[key]:6.2f}" if ca[key] else "     -"
            print(f"  {key:40} {ca[key]:8} {cb[key]:8} {ratio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
