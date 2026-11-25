"""Compares the samples of the ssac-built and arm64-built compilers.

Prints totals by image, then by symbol (summed over functions of one name),
sorted by the arm64 - ssac difference, and each binary's instruction count."""

import collections
import re
import subprocess
import sys
from pathlib import Path

P = Path(__file__).resolve().parent
TOP = int(sys.argv[1]) if len(sys.argv) > 1 else 40


def load(b):
    by_sym, by_img, total = collections.Counter(), collections.Counter(), 0
    me = f"quest-{b}"
    for f in sorted((P / f"samples-{b}").glob("r*")):
        lines = f.read_text().splitlines()[1:]
        for line in lines:
            _, image, sym = line.split(" ", 2)
            total += 1
            by_img["(compiler)" if image == me else image] += 1
            by_sym[sym if image == me else f"[{image}] {sym}"] += 1
    return total, by_img, by_sym


def sizes(b):
    """Instructions per symbol, summed over functions of one name"""
    out = subprocess.run(["otool", "-tv", str(P / f"quest-{b}")], capture_output=True, text=True).stdout
    n, cur, total = collections.Counter(), None, 0
    for line in out.splitlines():
        m = re.match(r"^(\S+):$", line)
        if m:
            cur = m.group(1).lstrip("_")
        elif cur and re.match(r"^[0-9a-f]+\t", line):
            n[cur] += 1
            total += 1
    return total, n


ts, imgs, syms = load("ssac")
ta, imga, syma = load("arm64")
print(f"total samples: ssac {ts}, arm64 {ta}, ratio {ta / ts:.3f}")
for img in sorted(set(imgs) | set(imga), key=lambda i: -(imgs[i] + imga[i])):
    print(f"  {imgs[img]:7} {imga[img]:7}  {imga[img] - imgs[img]:+7}  {img}")
ns_total, ns = sizes("ssac")
na_total, na = sizes("arm64")
print(f"instructions: ssac {ns_total}, arm64 {na_total}, ratio {na_total / ns_total:.3f}")
print()
print("  delta   ssac  arm64  ins-ssac ins-arm64  symbol")
keys = set(syms) | set(syma)
for k in sorted(keys, key=lambda k: -(syma[k] - syms[k]))[:TOP]:
    s = k.lstrip("_")
    print(f"{syma[k] - syms[k]:+7} {syms[k]:6} {syma[k]:6} {ns.get(s, 0):9} {na.get(s, 0):9}  {k}")
print("  ...")
for k in sorted(keys, key=lambda k: (syma[k] - syms[k]))[:TOP // 2]:
    s = k.lstrip("_")
    print(f"{syma[k] - syms[k]:+7} {syms[k]:6} {syma[k]:6} {ns.get(s, 0):9} {na.get(s, 0):9}  {k}")
