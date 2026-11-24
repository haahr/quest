"""Counts the calls between modules in a separately compiled arm64 build
(docs/benchmarks.md section 36): for each module, how many call
sites in other modules' code call its exported members, and how big each
member's code is, which says which modules inlining into their importers
could gain from.

    python3.11 tools/perf/crosscalls.py BUILD_DIR
        each module's call sites from other modules, most first
    python3.11 tools/perf/crosscalls.py BUILD_DIR --members 40
        and the 40 members called from the most sites

BUILD_DIR is a --build-dir of a separate arm64 build, whose units' assembly
(NAME.mod.s, NAME.main.s) it reads. Counts are static: call sites in the
code, not calls made. A member's size is the instructions of the function
its exported entry jumps to, or of the entry itself, which says whether the
inliner could take it (docs/inlining.md section 1).
"""

import argparse
import collections
import re
import sys
from pathlib import Path

CALL = re.compile(r"^\s+(bl|b)\s+_(qv_[A-Za-z0-9_]+)\s*$")
LABEL = re.compile(r"^_([A-Za-z0-9_]+):$")
INSTRUCTION = re.compile(r"^\s+[a-z]")


def unitName(build: Path, path: Path) -> str:
    """A unit's module name as its symbols spell it (collections__vector),
    from its assembly's path in the build directory"""
    rel = path.relative_to(build).as_posix()
    stem = re.sub(r"\.(mod|main)\.s$", "", rel)
    return stem.replace("/", "__")


def functions(text: str) -> dict[str, list[str]]:
    """Each function's instruction lines, by symbol without its underscore"""
    out: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        m = LABEL.match(line)
        if m:
            current = out.setdefault(m.group(1), [])
        elif current is not None and INSTRUCTION.match(line) and not line.strip().startswith("."):
            current.append(line)
    return out


def memberSize(fns: dict[str, list[str]], entry: str) -> int:
    """The instructions of an exported entry's function: the static one it
    tail-calls when that is all it does, else the entry's own"""
    body = fns.get(entry, [])
    for line in body:
        m = re.match(r"^\s+b\s+_(qf_[A-Za-z0-9_]+)\s*$", line)
        if m and m.group(1) in fns:
            return len(fns[m.group(1)])
    return len(body)


def owner(symbol: str, modules: list[str]) -> str | None:
    """The module whose exported member symbol is (qv_<module>_<member>),
    the longest module name that prefixes it"""
    best = None
    for m in modules:
        if symbol.startswith("qv_" + m + "_") and (best is None or len(m) > len(best)):
            best = m
    return best


def scan(build: Path) -> tuple[collections.Counter, collections.Counter, dict[str, int], set[str]]:
    """Call sites by callee module and by callee member, from other modules'
    code; each member's size; and the callers of each module"""
    texts = {unitName(build, p): p.read_text() for p in sorted(build.rglob("*.s"))}
    modules = sorted(texts)
    byModule: collections.Counter = collections.Counter()
    byMember: collections.Counter = collections.Counter()
    sizes: dict[str, int] = {}
    callers: dict[str, set[str]] = collections.defaultdict(set)
    parsed = {name: functions(text) for name, text in texts.items()}
    for caller, text in texts.items():
        for line in text.splitlines():
            m = CALL.match(line)
            if not m:
                continue
            callee = owner(m.group(2), modules)
            if callee is None or callee == caller:
                continue
            byModule[callee] += 1
            byMember[m.group(2)] += 1
            callers[callee].add(caller)
            if m.group(2) not in sizes:
                sizes[m.group(2)] = memberSize(parsed[callee], m.group(2))
    return byModule, byMember, sizes, callers


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build", type=Path, help="the --build-dir of a separate arm64 build")
    ap.add_argument("--members", type=int, default=0, help="also list this many members, most called first")
    ap.add_argument("--small", type=int, default=40, help="a member of at most this many instructions is small")
    args = ap.parse_args()
    if not any(args.build.rglob("*.s")):
        print(f"crosscalls: no assembly in {args.build} (an arm64 build's --build-dir)", file=sys.stderr)
        return 1
    byModule, byMember, sizes, callers = scan(args.build)
    smallSites: collections.Counter = collections.Counter()
    for member, n in byMember.items():
        if sizes.get(member, 0) <= args.small:
            smallSites[owner(member, list(byModule)) or ""] += n
    print(f"{'module':40} {'sites':>7} {'small':>7} {'callers':>8}")
    for module, n in byModule.most_common():
        print(f"{module:40} {n:7} {smallSites[module]:7} {len(callers[module]):8}")
    if args.members:
        print()
        print(f"{'member':56} {'sites':>7} {'size':>6}")
        for member, n in byMember.most_common(args.members):
            print(f"{member:56} {n:7} {sizes.get(member, 0):6}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
