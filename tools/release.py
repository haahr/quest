"""Cuts, verifies, and rolls back releases of the self-hosted compiler
(docs/release-compiler.md). A release is a commit's stage 2, kept in
release/current with a snapshot of that commit's lib/ and runtime/ (home/) and
a description of itself (release.json); the release before it is kept in
release/previous.

    tools/release              cut a release from HEAD, after the self-hosting check
    tools/release --verify     check the current release: its binary's digest, and a program it builds and runs
    tools/release --rollback   swap the current and previous releases
    tools/release --show       print the current and previous releases' descriptions
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
RELEASE_DIR = ROOT_DIR / "release"
CURRENT = RELEASE_DIR / "current"
PREVIOUS = RELEASE_DIR / "previous"
NEW = RELEASE_DIR / "new"
DEFAULT_CHECK_DIR = ROOT_DIR / ".build" / "release-check"
ABI_SOURCE = ROOT_DIR / "questlang" / "config" / "abi.mod.quest"
SMOKE_PROGRAM = 'import writer: Writer;\nwriter.putString(writer.output "release ok\\n");\n'


def fail(message: str) -> None:
    sys.exit(f"release: {message}")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT_DIR, capture_output=True, text=True, check=True).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def abi_constants() -> tuple[int, str]:
    """The ABI version and producer the self-hosted compiler declares
    (questlang/config/abi), which a release built from this tree carries."""
    text = ABI_SOURCE.read_text(encoding="utf-8")
    abi = re.search(r"let abiVersion = (\d+)", text)
    producer = re.search(r'let producer = "([^"]*)"', text)
    if abi is None or producer is None:
        fail(f"cannot find the ABI version and producer in {ABI_SOURCE.relative_to(ROOT_DIR)}")
    return int(abi.group(1)), producer.group(1)


def check_tree() -> str:
    """HEAD's commit, which must be clean and on main."""
    if git("status", "--porcelain"):
        fail("the working tree is not clean; a release is cut only from a commit")
    commit = git("rev-parse", "HEAD")
    git("fetch", "-q", "origin")
    merged = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"], cwd=ROOT_DIR)
    if merged.returncode != 0:
        fail(f"HEAD ({commit[:8]}) is not on origin/main; a release is cut only from a commit on main")
    return commit


def snapshot_home(commit: str, home: Path) -> None:
    """The commit's lib/ and runtime/, as committed, into home."""
    home.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", commit, "lib", "runtime"], cwd=ROOT_DIR, capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", str(home)], input=archive.stdout, check=True)


def smoke_test(release: Path) -> str:
    """Builds and runs a small program with the release, against its own home;
    returns what went wrong, or an empty string."""
    environment = os.environ.copy()
    environment["QUEST_HOME"] = str(release / "home")
    with tempfile.TemporaryDirectory(prefix="quest-release-") as scratch:
        source = Path(scratch) / "smoke.quest"
        source.write_text(SMOKE_PROGRAM, encoding="utf-8")
        binary = Path(scratch) / "smoke"
        build = subprocess.run(
            [str(release / "questc"), "--build-dir", str(Path(scratch) / "build"), "-o", str(binary), str(source)],
            capture_output=True, text=True, env=environment, cwd=scratch,
        )
        if build.returncode != 0:
            return f"building a program failed:\n{build.stdout}{build.stderr}"
        run = subprocess.run([str(binary)], capture_output=True, text=True, cwd=scratch)
        if run.returncode != 0 or run.stdout != "release ok\n":
            return f"the program it built printed {run.stdout!r} and exited {run.returncode}"
    return ""


def verify(release: Path) -> str:
    """What is wrong with the release in release, or an empty string."""
    description = release / "release.json"
    if not description.is_file():
        return f"{release.relative_to(ROOT_DIR)} has no release.json"
    recorded = json.loads(description.read_text(encoding="utf-8"))
    binary = release / "questc"
    if not binary.is_file():
        return f"{release.relative_to(ROOT_DIR)} has no questc"
    if sha256(binary) != recorded["sha256"]:
        return f"{binary.relative_to(ROOT_DIR)}'s digest is not the one release.json records"
    for part in ("lib", "runtime"):
        if not (release / "home" / part).is_dir():
            return f"{release.relative_to(ROOT_DIR)}/home has no {part}/"
    return smoke_test(release)


def cut(python: str, check_dir: Path) -> None:
    commit = check_tree()
    abi, producer = abi_constants()
    print(f"Checking {commit[:8]} (run_tests.py --self-hosting --build-dir {check_dir})...", flush=True)
    shutil.rmtree(check_dir, ignore_errors=True)
    check = subprocess.run([python, str(ROOT_DIR / "run_tests.py"), "--self-hosting", "--build-dir", str(check_dir)],
                           cwd=ROOT_DIR)
    if check.returncode != 0:
        fail("the self-hosting check or the self-hosted suite failed; no release was cut")
    stage2 = check_dir / "self-hosting" / "stage2" / "questlang-driver"

    shutil.rmtree(NEW, ignore_errors=True)
    NEW.mkdir(parents=True)
    shutil.copy2(stage2, NEW / "questc")
    snapshot_home(commit, NEW / "home")
    description = {
        "commit": commit,
        "abi": abi,
        "producer": producer,
        "sha256": sha256(NEW / "questc"),
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "checked": "run_tests.py --self-hosting (the fixed point, and the self-hosted suite with stage 2)",
    }
    (NEW / "release.json").write_text(json.dumps(description, indent=2) + "\n", encoding="utf-8")
    problem = verify(NEW)
    if problem:
        fail(f"the new release does not work ({problem}); it is left in release/new")

    # Each rename is atomic, so an interruption leaves a whole release in
    # current, or none there and the new one still in new
    shutil.rmtree(PREVIOUS, ignore_errors=True)
    if CURRENT.exists():
        CURRENT.rename(PREVIOUS)
    NEW.rename(CURRENT)
    print(f"Released {commit[:8]} (abi {abi}) in release/current")


def rollback() -> None:
    if not PREVIOUS.is_dir():
        fail("there is no previous release to roll back to")
    swap = RELEASE_DIR / "swap"
    shutil.rmtree(swap, ignore_errors=True)
    if CURRENT.exists():
        CURRENT.rename(swap)
    PREVIOUS.rename(CURRENT)
    if swap.exists():
        swap.rename(PREVIOUS)
    show()


def show() -> None:
    for release in (CURRENT, PREVIOUS):
        description = release / "release.json"
        if description.is_file():
            d = json.loads(description.read_text(encoding="utf-8"))
            print(f"{release.name}: {d['commit'][:8]} abi {d['abi']} {d['producer']}, cut {d['date']}")
        else:
            print(f"{release.name}: none")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--verify", action="store_true", help="check the current release")
    action.add_argument("--rollback", action="store_true", help="swap the current and previous releases")
    action.add_argument("--show", action="store_true", help="describe the current and previous releases")
    parser.add_argument("--check-dir", type=Path, default=DEFAULT_CHECK_DIR,
                        help="where the self-hosting check builds its stages (default .build/release-check)")
    args = parser.parse_args()
    if args.verify:
        problem = verify(CURRENT) if CURRENT.is_dir() else "there is no current release"
        if problem:
            fail(problem)
        print("The current release is sound")
    elif args.rollback:
        rollback()
    elif args.show:
        show()
    else:
        cut(sys.executable, args.check_dir.resolve())


if __name__ == "__main__":
    main()
