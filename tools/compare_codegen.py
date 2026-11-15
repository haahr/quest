"""Compares the code one compiler generates for questlang/ at a revision with
the code it generates for the working tree, unit by unit, ignoring source
positions: for checking that an edit of questlang/'s source, such as
tools/omit-type-args's, changes nothing the compiler makes of it.

    tools/compare-codegen                       the working tree against HEAD, through arm64
    tools/compare-codegen --base origin/main    against another revision
    tools/compare-codegen --phase ir_described  another phase's output (--stop-after)
    tools/compare-codegen --compiler PATH       another compiler (the working tree's stage 2 by default)
    tools/compare-codegen -k ir/                only the units whose paths contain ir/

The revision's files are exported as tools/c-diff exports them (git archive,
into .build/c-diff/REVISION). Each tree's units are compiled in that tree,
against its own lib/, into a build directory of its own. Before comparing, the
tree's path becomes TREE, lines of .loc directives go, and FILE.quest:LINE:COL
positions (in the strings that locate run-time errors) lose their numbers. The
exit status is 0 when every unit compares equal, 1 when some differ, and 2
when a unit does not compile.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import difflib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

from c_diff import export_revision  # noqa: E402

STAGE2 = ROOT_DIR / ".build" / "quest-stages" / "stage2" / "quest"
POSITION = re.compile(r"(\.quest):\d+:\d+")


def normalize(text: str, tree: Path) -> str:
    """text with tree's path, .loc lines, and source positions' numbers out"""
    lines = [line for line in text.splitlines() if not line.lstrip().startswith(".loc")]
    return POSITION.sub(r"\1:L:C", "\n".join(lines).replace(str(tree), "TREE")) + "\n"


def units(tree: Path) -> list[str]:
    """questlang/'s modules in tree, and the driver, which is a program"""
    found = sorted(str(p.relative_to(tree)) for p in (tree / "questlang").rglob("*.mod.quest"))
    return found + ["questlang/driver/main.quest"]


def compile_unit(compiler: str, tree: Path, unit: str, phase: str, build: Path) -> tuple[int, str]:
    environment = os.environ.copy()
    environment["QUEST_HOME"] = str(tree)
    process = subprocess.run([compiler, "--stop-after", phase, "--build-dir", str(build), unit], cwd=tree,
                             capture_output=True, text=True, env=environment, timeout=1800)
    if process.returncode != 0:
        return process.returncode, process.stdout + process.stderr
    return 0, normalize(process.stdout, tree)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--phase", default="codegen_arm64")
    parser.add_argument("--compiler", default=None)
    parser.add_argument("-k", dest="filter", default="")
    parser.add_argument("-j", dest="jobs", type=int, default=8)
    args = parser.parse_args()
    compiler = args.compiler
    if compiler is None:
        built = subprocess.run([str(ROOT_DIR / "quest"), "-e", "ok"], cwd=ROOT_DIR, capture_output=True, text=True)
        if built.returncode != 0:
            print(built.stdout + built.stderr, file=sys.stderr)
            return 2
        compiler = str(STAGE2)
    trees = {"base": export_revision(args.base), "working": ROOT_DIR}
    names = [u for u in units(ROOT_DIR) if args.filter in u]
    base_units = set(units(trees["base"]))
    only_working = [u for u in names if u not in base_units]
    names = [u for u in names if u in base_units]

    def side(which: str):
        tree = trees[which]
        build = ROOT_DIR / ".build" / "compare-codegen" / which
        # One unit first, so that the library's units are built once
        compile_unit(compiler, tree, names[0], args.phase, build)
        with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
            return list(pool.map(lambda u: compile_unit(compiler, tree, u, args.phase, build), names))

    base, working = side("base"), side("working")
    status = 0
    for unit, (bcode, btext), (wcode, wtext) in zip(names, base, working):
        if bcode != 0 or wcode != 0:
            print(f"== {unit}: does not compile ({'base' if bcode else 'working tree'})\n"
                  f"{(btext if bcode else wtext)[:2000]}")
            status = 2
        elif btext != wtext:
            print(f"== {unit}")
            diff = difflib.unified_diff(btext.splitlines(), wtext.splitlines(), "base", "working", lineterm="", n=1)
            for line in list(diff)[2:40]:
                print(line)
            status = max(status, 1)
    for unit in only_working:
        print(f"== {unit}: not in the base")
    print(f"compare-codegen: {len(names)} units, " + ("all equal" if status == 0 else "some differ"), file=sys.stderr)
    return status


if __name__ == "__main__":
    sys.exit(main())
