"""Shows how a change alters the C a compiler generates (docs/testing.md
section 2.9): the C of every program the golden tests compile and run, as one
revision's compiler prints it, against the C of the working tree's.

    tools/c-diff                    the self-hosted compiler's C at HEAD against the working tree's
    tools/c-diff --base origin/main against another revision's
    tools/c-diff --bootstrap        the bootstrap's C instead
    tools/c-diff -k option          only the programs whose test names contain "option"
    tools/c-diff --stat             only which programs differ, and by how many lines
    tools/c-diff --questlang        the tests of the self-hosted compiler's modules too (slow)

The revision's files are exported (git archive) to .build/c-diff/REVISION and
kept, with what the compilers build there, so a later comparison against the
same revision builds only the working tree's side again. Each side compiles
its own copy of the programs, against its own lib/ and runtime/. Paths under
either tree are made relative to it, so that only the C itself differs. The
exit status is 0 when no program's C differs, 1 when some does, and 2 when a
program does not compile.
"""

import argparse
import concurrent.futures
import difflib
import os
import queue
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.modules.graph import UnitKind, file_unit_kind  # noqa: E402
from quest.testing.runner import parse_test_directives  # noqa: E402

CACHE_DIR = ROOT_DIR / ".build" / "c-diff"
TRIVIAL_PROGRAM = "let x = 1;\n"


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True, check=True).stdout.strip()


def export_revision(revision: str) -> Path:
    """The files of revision, exported once into the cache."""
    sha = git("rev-parse", "--verify", revision + "^{commit}")
    tree = CACHE_DIR / sha[:12]
    if not (tree / ".exported").exists():
        shutil.rmtree(tree, ignore_errors=True)
        tree.mkdir(parents=True)
        archive = subprocess.run(["git", "archive", sha], cwd=ROOT_DIR, capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(tree)], input=archive, check=True)
        (tree / ".exported").write_text(sha + "\n")
    return tree


class Side:
    """One tree's compiler: what runs it, and where it builds."""

    def __init__(self, name: str, tree: Path, bootstrap: bool, python: str) -> None:
        self.name = name
        self.tree = tree
        self.bootstrap = bootstrap
        self.python = python
        compiler = "bootstrap" if bootstrap else "self-hosted"
        self.build_root = tree / ".build" / "c-diff-units" / compiler
        self.environment = os.environ.copy()
        self.environment["PYTHONPATH"] = str(tree / "bootstrap" / "python")
        self.environment["QUEST_HOME"] = str(tree)
        self.command: list[str] = []

    def prepare(self) -> None:
        """Builds the self-hosted compiler of the tree, once, before the
        programs compile in parallel (./questc rebuilds it when it is stale)."""
        if self.bootstrap:
            self.command = [self.python, str(self.tree / "bootstrap" / "python" / "quest_driver.py")]
            return
        print(f"c-diff: building the {self.name} tree's self-hosted compiler...", file=sys.stderr)
        with tempfile.TemporaryDirectory(prefix="c-diff-") as scratch:
            program = Path(scratch) / "trivial.quest"
            program.write_text(TRIVIAL_PROGRAM)
            process = subprocess.run(
                [str(self.tree / "questc"), "--build-dir", str(Path(scratch) / "build"), "--stop-after", "typecheck",
                 str(program)],
                capture_output=True, text=True, env=self.environment, cwd=scratch,
            )
        if process.returncode != 0:
            sys.exit(f"c-diff: building the {self.name} tree's compiler failed:\n{process.stdout}{process.stderr}")
        self.command = [str(self.tree / ".build" / "questc" / "stage2" / "questc")]

    def c_of(self, program: Path, echo: bool, build_dir: Path) -> tuple[bool, str]:
        """The C the compiler prints for program, as run_c_compiled compiles it,
        with the tree's paths relative; or, if it fails, why."""
        command = [*self.command, "--stop-after", "codegen_c", "--print-result", "--build-dir", str(build_dir)]
        if echo:
            command.append("--echo")
        command.append(str(program))
        with tempfile.TemporaryDirectory(prefix="c-diff-") as scratch:
            process = subprocess.run(command, capture_output=True, encoding="utf-8", env=self.environment,
                                     cwd=scratch)
        if process.returncode != 0:
            return False, (process.stdout + process.stderr).rstrip()
        text = process.stdout
        for root in {str(self.tree), str(self.tree.resolve())}:
            text = text.replace(root.rstrip(os.sep) + os.sep, "")
        return True, text


def compiled_programs(tree: Path, questlang: bool) -> dict[str, tuple[Path, bool]]:
    """The programs run_c_compiled compiles in tree, by test name: those with run
    goldens that do not skip it, and the tests of the self-hosted compiler's
    modules (tests/source/questlang) only with questlang, since each compiles
    most of the compiler. Each comes with whether it is compiled with --echo."""
    programs: dict[str, tuple[Path, bool]] = {}
    for base, prefix in ((tree / "tests" / "source", Path()), (tree / "examples", Path("examples"))):
        for path in sorted(base.rglob("*.quest")):
            if file_unit_kind(path) != UnitKind.PROGRAM:
                continue
            test_id = prefix / path.relative_to(base)
            if not questlang and test_id.parts[0] == "questlang":
                continue
            if not (tree / "tests" / "golden" / "run" / test_id.with_suffix(".out")).exists():
                continue
            directives = parse_test_directives(path)
            if "run_c_compiled" in directives.skipped_phases:
                continue
            programs[test_id.with_suffix("").as_posix()] = (path, directives.echo)
    return programs


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff the C of the golden programs between a revision and the tree.")
    parser.add_argument("--base", default="HEAD", help="the revision to compare with (default HEAD)")
    parser.add_argument("--bootstrap", action="store_true", help="compare the bootstrap's C (default: self-hosted)")
    parser.add_argument("-k", "--test", help="only the programs whose test names contain this")
    parser.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 1, help="programs compiled at once")
    parser.add_argument("--questlang", action="store_true", help="include the tests of the compiler's modules")
    parser.add_argument("--stat", action="store_true", help="list the programs that differ, not their diffs")
    args = parser.parse_args()

    python = sys.executable
    base = Side("base", export_revision(args.base), args.bootstrap, python)
    work = Side("working", ROOT_DIR, args.bootstrap, python)
    base.prepare()
    work.prepare()

    base_programs = compiled_programs(base.tree, args.questlang)
    work_programs = compiled_programs(work.tree, args.questlang)
    names = sorted(set(base_programs) | set(work_programs))
    if args.test:
        names = [n for n in names if args.test in n]

    # Each worker builds in a directory of its own on each side, since a
    # compiler writes the units it builds into its build directory
    workers: queue.Queue[int] = queue.Queue()
    for i in range(args.jobs):
        workers.put(i)

    def compare(name: str) -> tuple[str, str, str]:
        worker = workers.get()
        try:
            texts = []
            for side, programs in ((base, base_programs), (work, work_programs)):
                if name not in programs:
                    texts.append(None)
                    continue
                path, echo = programs[name]
                ok, text = side.c_of(path, echo, side.build_root / f"w{worker}")
                if not ok:
                    return name, "error", f"{side.name}: {text}"
                texts.append(text)
        finally:
            workers.put(worker)
        old, new = texts
        if old is None:
            return name, "added", ""
        if new is None:
            return name, "removed", ""
        if old == new:
            return name, "same", ""
        diff = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                    fromfile=f"{args.base}/{name}.c", tofile=f"working/{name}.c")
        return name, "differs", "".join(diff)

    results: list[tuple[str, str, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
        for result in executor.map(compare, names):
            results.append(result)

    counts: dict[str, int] = {}
    for name, status, detail in results:
        counts[status] = counts.get(status, 0) + 1
        if status == "same":
            continue
        if status == "differs":
            if args.stat:
                lines = detail.splitlines()[2:]
                added = sum(1 for line in lines if line.startswith("+"))
                removed = sum(1 for line in lines if line.startswith("-"))
                print(f"{name}: +{added} -{removed}")
            else:
                sys.stdout.write(detail if detail.endswith("\n") else detail + "\n")
        elif status == "error":
            print(f"{name}: does not compile\n{detail}")
        else:
            print(f"{name}: {status}")
    summary = ", ".join(f"{counts[s]} {s}" for s in ("same", "differs", "added", "removed", "error") if s in counts)
    print(f"c-diff: {len(results)} programs: {summary}", file=sys.stderr)
    if counts.get("error"):
        return 2
    return 1 if counts.get("differs") or counts.get("added") or counts.get("removed") else 0


if __name__ == "__main__":
    sys.exit(main())
