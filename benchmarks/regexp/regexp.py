"""regexp.quest's workloads with Python's re, a backtracking matcher, for
comparison (benchmarks/regexp/README.md): the same arguments, the same number
printed. Run with -I."""

import re
import sys


def main() -> None:
    workload, path, repeat = sys.argv[1], sys.argv[2], int(sys.argv[3])
    with open(path, "rb") as f:
        text = f.read()
    lines = text.rstrip(b"\n").split(b"\n")

    def containing(r: re.Pattern) -> int:
        return sum(1 for line in lines if r.search(line))

    def summed(r: re.Pattern, f) -> int:
        n = 0
        for line in lines:
            m = r.search(line)
            if m:
                n += f(m)
        return n

    def once() -> int:
        if workload == "walk":
            return sum(len(line) for line in lines)
        if workload == "literal":
            return containing(re.compile(rb"ERROR"))
        if workload == "caseless":
            return containing(re.compile(rb"(?i)error"))
        if workload == "alternation":
            return containing(re.compile(rb"\b(?:timeout|refused|reset|unreachable)\b"))
        if workload == "prefix":
            return summed(re.compile(rb"user=(\w+)"), lambda m: len(m.group(1)))
        if workload == "date":
            return summed(re.compile(rb"(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)"), lambda m: int(m.group(4)))
        if workload == "anchored":
            return summed(re.compile(rb"^([A-Z]+) "), lambda m: 1 if m.group(1) == b"WARN" else 0)
        if workload == "tokens":
            return len(re.findall(rb'[A-Za-z_]\w*|\d+|"(?:[^"\\]|\\.)*"|\S', text))
        if workload == "replace":
            return len(re.sub(rb"\s+", b" ", text))
        sys.exit(f"regexp.py: no workload {workload}")

    result = 0
    for _ in range(repeat):
        result = once()
    print(result)


main()
