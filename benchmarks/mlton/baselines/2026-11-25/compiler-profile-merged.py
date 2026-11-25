import collections, re, sys
from pathlib import Path
P = Path(__file__).resolve().parent
def key(sym):
    s = sym.lstrip("_")
    m = re.match(r"qv_.*?_([A-Za-z0-9]+)$", s)
    if m: return "q:" + m.group(1)
    if s.startswith("qf_"): return "q:" + s[3:]
    return s
def load(b):
    c = collections.Counter(); cat = collections.Counter()
    for f in (P / f"samples-{b}").glob("r*"):
        for line in f.read_text().splitlines()[1:]:
            _, image, sym = line.split(" ", 2)
            k = key(sym) if image == f"quest-{b}" else "[lib] " + sym
            c[k] += 1
            cat["quest code" if k.startswith("q:") else ("runtime+collector" if image == f"quest-{b}" else "system libraries")] += 1
    return c, cat
s, cs = load("ssac"); a, ca = load("arm64")
for k in cs: print(f"{k:20} ssac {cs[k]:6}  arm64 {ca[k]:6}  ratio {ca[k]/cs[k]:.3f}  delta {ca[k]-cs[k]:+6}")
print()
for k in sorted(set(s)|set(a), key=lambda k: -(a[k]-s[k]))[:30]:
    print(f"{a[k]-s[k]:+6} {s[k]:6} {a[k]:6}  {k}")
print("...")
for k in sorted(set(s)|set(a), key=lambda k: (a[k]-s[k]))[:12]:
    print(f"{a[k]-s[k]:+6} {s[k]:6} {a[k]:6}  {k}")
