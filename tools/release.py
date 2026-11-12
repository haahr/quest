"""Cuts, verifies, and rolls back releases of the self-hosted compiler
(docs/release-compiler.md). A release is a commit's stage 2, kept with a
snapshot of that commit's lib/ and runtime/ (home/) and a description of
itself (release.json) in a directory named by the commit, among the releases
that every worktree of the repository shares (quest/testing/releases.py):
current names the release that seeds builds, and previous the one before it.

    tools/release              cut a release from HEAD, after the self-hosting check, seeded from the current release
    tools/release --seed bootstrap
                               the same, seeded from the bootstrap (the first release, or past a gap)
    tools/release --backend c  the same, releasing stage 2 as the C backend compiles it (arm64's by default)
    tools/release --whole-program
                               the same, releasing stage 2's whole-program build, after its fixed point and the
                               self-hosted suite with it
    tools/release --verify     check the current release: its binary's digest, and a program it builds and runs
    tools/release --rollback   swap the current and previous releases
    tools/release --show       print the current and previous releases' descriptions
    tools/release --install [PREFIX]
                               copy the current release to PREFIX/share/quest/COMMIT (PREFIX is ~/.local by
                               default), check it there, and point PREFIX/bin/quest at it
"""

import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.testing.releases import releases_dir  # noqa: E402

RELEASES = releases_dir(ROOT_DIR)
CURRENT = RELEASES / "current"
PREVIOUS = RELEASES / "previous"
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


@contextlib.contextmanager
def locked():
    """Holds the releases' lock, which every change to current and previous
    takes, so that two worktrees cutting or rolling back at once do not
    interleave their changes."""
    RELEASES.mkdir(parents=True, exist_ok=True)
    with (RELEASES / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def target(link: Path) -> Path | None:
    """The release a link names, if it names one."""
    return link.resolve() if link.is_dir() else None


def point(link: Path, release: Path) -> None:
    """Points link at release, atomically: a new link replaces the old one by
    renaming, so that a reader finds the old release or the new one."""
    temporary = link.with_name(link.name + ".new")
    temporary.unlink(missing_ok=True)
    temporary.symlink_to(release.name)
    os.replace(temporary, link)


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
            [str(release / "quest"), "--build-dir", str(Path(scratch) / "build"), "-o", str(binary), str(source)],
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
        return f"{release} has no release.json"
    recorded = json.loads(description.read_text(encoding="utf-8"))
    binary = release / "quest"
    if not binary.is_file():
        return f"{release} has no quest"
    if sha256(binary) != recorded["sha256"]:
        return f"{binary}'s digest is not the one release.json records"
    for part in ("lib", "runtime"):
        if not (release / "home" / part).is_dir():
            return f"{release}/home has no {part}/"
    return smoke_test(release)


def cut(python: str, check_dir: Path, seed: str, backend: str, whole_program: bool) -> None:
    commit = check_tree()
    abi, producer = abi_constants()
    current = target(CURRENT)
    if current is not None and current.name == commit:
        fail(f"{commit[:8]} is the current release already")
    # The new release is built from the current one, which must be sound
    if seed == "release":
        if current is None:
            fail(f"there is no current release in {RELEASES} to seed from; cut the first with --seed bootstrap")
        problem = verify(current)
        if problem:
            fail(f"the current release does not work ({problem}); roll back, or cut with --seed bootstrap")
        seeded_by = "release " + json.loads((current / "release.json").read_text(encoding="utf-8"))["commit"]
    else:
        seeded_by = "bootstrap"
    # Stages 2 and 3 are built through backend, so that the release is the
    # compiler as backend compiles it, and the suite runs with it
    command = ["run_tests.py", "--self-hosting", "--seed", seed, "--stage-backend", backend, "--build-dir",
               str(check_dir)]
    stages = check_dir / "self-hosting"
    if whole_program:
        # The fixed points first, the whole-program one among them, and then
        # the suite with the whole-program build, which is what is released
        command += ["--whole-program-fixed-point", "--fixed-point-only"]
        binary = stages / "whole" / "questlang-driver"
        suite = ["run_tests.py", "--self-hosted", "--self-hosted-driver", str(binary), "--build-dir",
                 str(check_dir / "whole-suite")]
    else:
        binary = stages / "stage2" / "questlang-driver"
    print(f"Checking {commit[:8]} ({' '.join(command)})...", flush=True)
    shutil.rmtree(check_dir, ignore_errors=True)
    check = subprocess.run([python, str(ROOT_DIR / command[0]), *command[1:]], cwd=ROOT_DIR)
    if check.returncode != 0:
        fail("the self-hosting check or the self-hosted suite failed; no release was cut")
    if whole_program:
        print(f"Checking the whole-program build ({' '.join(suite)})...", flush=True)
        check = subprocess.run([python, str(ROOT_DIR / suite[0]), *suite[1:]], cwd=ROOT_DIR)
        if check.returncode != 0:
            fail("the self-hosted suite failed with the whole-program build; no release was cut")

    # Written beside the releases, under a name no other cut uses, and
    # renamed into place once it works
    new = RELEASES / f"new-{commit[:8]}-{os.getpid()}"
    shutil.rmtree(new, ignore_errors=True)
    new.mkdir(parents=True)

    shutil.copy2(binary, new / "quest")
    snapshot_home(commit, new / "home")
    description = {
        "commit": commit,
        "abi": abi,
        "producer": producer,
        "sha256": sha256(new / "quest"),
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        # Stage 1 was built by the seed: the release before this one, or the
        # bootstrap
        "seed": seeded_by,
        # The backend that compiled the released compiler
        "backend": backend,
        "checked": f"run_tests.py --self-hosting --seed {seed} --stage-backend {backend} (the fixed point, and the "
                   "self-hosted suite with stage 2)",
    }
    if whole_program:
        # Stage 2's build of the driver as a whole program (--whole-program)
        description["build"] = "whole program"
        description["checked"] = (f"run_tests.py --self-hosting --seed {seed} --stage-backend {backend} "
                                  "--whole-program-fixed-point (the fixed points), and the self-hosted suite with the "
                                  "whole-program build")
    (new / "release.json").write_text(json.dumps(description, indent=2) + "\n", encoding="utf-8")
    problem = verify(new)
    if problem:
        fail(f"the new release does not work ({problem}); it is left in {new}")

    with locked():
        # Another worktree may have changed the releases during the check
        current = target(CURRENT)
        if current is not None and current.name == commit:
            shutil.rmtree(new)
            fail(f"{commit[:8]} was released while this release was checked")
        release = RELEASES / commit
        shutil.rmtree(release, ignore_errors=True)
        new.rename(release)
        # Each change of a link is atomic, so an interruption leaves current
        # naming a whole release
        if current is not None:
            point(PREVIOUS, current)
        point(CURRENT, release)
        remove_unnamed()
    print(f"Released {commit[:8]} (abi {abi}) in {release}")


def remove_unnamed() -> None:
    """Removes the releases neither current nor previous names, with the lock
    held. A cut in progress elsewhere (new-...) is left alone."""
    kept = {link.resolve().name for link in (CURRENT, PREVIOUS) if link.is_dir()}
    for entry in RELEASES.iterdir():
        if entry.is_dir() and not entry.is_symlink() and entry.name not in kept and not entry.name.startswith("new-"):
            shutil.rmtree(entry, ignore_errors=True)


def rollback() -> None:
    with locked():
        previous, current = target(PREVIOUS), target(CURRENT)
        if previous is None:
            fail("there is no previous release to roll back to")
        point(CURRENT, previous)
        if current is not None:
            point(PREVIOUS, current)
    show()


# The first lines of the command --install writes, by which a later --install
# knows that it may replace it
WRAPPER_HEADER = "#!/bin/sh\n# Quest, installed by tools/release --install"


def install(prefix: Path) -> None:
    """Copies the current release out of the repository, where a later cut
    cannot remove it, and writes prefix/bin/quest, which runs it against its
    own home/. Releases installed before are kept, to switch back to."""
    current = target(CURRENT)
    if current is None:
        fail(f"there is no current release in {RELEASES} to install")
    commit = json.loads((current / "release.json").read_text(encoding="utf-8"))["commit"]
    command = prefix / "bin" / "quest"
    if command.exists() and not command.read_text(encoding="utf-8", errors="replace").startswith(WRAPPER_HEADER):
        fail(f"{command} exists, and tools/release --install did not write it")
    installed = prefix / "share" / "quest" / commit
    if not installed.is_dir():
        # Copied beside it and renamed into place, so that an interrupted
        # install leaves no partial release under its commit's name
        partial = installed.with_name(f"new-{commit[:8]}-{os.getpid()}")
        shutil.rmtree(partial, ignore_errors=True)
        shutil.copytree(current, partial, symlinks=True)
        partial.rename(installed)
    problem = verify(installed)
    if problem:
        fail(f"the installed release does not work ({problem})")
    # QUEST_HOME is the release's own home/, whatever the caller's says: the
    # binary was compiled against its lib/ and runtime/
    command.parent.mkdir(parents=True, exist_ok=True)
    temporary = command.with_name(command.name + ".new")
    temporary.write_text(f'{WRAPPER_HEADER} from release {commit} (release.json there)\n'
                         f'QUEST_HOME={shlex.quote(str(installed / "home"))} exec {shlex.quote(str(installed / "quest"))} '
                         '"$@"\n', encoding="utf-8")
    temporary.chmod(0o755)
    os.replace(temporary, command)
    print(f"Installed {commit[:8]} in {installed}, run as {command}")
    if str(command.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"{command.parent} is not on PATH")


def show() -> None:
    for release in (CURRENT, PREVIOUS):
        description = release / "release.json"
        if release.is_dir() and description.is_file():
            d = json.loads(description.read_text(encoding="utf-8"))
            # Releases cut before seeding from the release recorded no seed:
            # theirs was the bootstrap
            seed = d.get("seed", "bootstrap")
            seed = f"release {seed.split()[1][:8]}" if seed.startswith("release ") else seed
            # Releases cut before --backend recorded none: C compiled them
            build = f", {d.get('backend', 'c')}" + (f", {d['build']}" if "build" in d else "")
            print(f"{release.name}: {d['commit'][:8]} abi {d['abi']} {d['producer']}{build}, cut {d['date']}, "
                  f"seeded by {seed}")
        else:
            print(f"{release.name}: none")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--verify", action="store_true", help="check the current release")
    action.add_argument("--rollback", action="store_true", help="swap the current and previous releases")
    action.add_argument("--show", action="store_true", help="describe the current and previous releases")
    action.add_argument("--install", nargs="?", type=Path, const=Path.home() / ".local", metavar="PREFIX",
                        help="install the current release in PREFIX/share/quest, run as PREFIX/bin/quest "
                             "(default ~/.local)")
    parser.add_argument("--seed", choices=("release", "bootstrap"), default="release",
                        help="what builds the check's stage 1: the current release (default), or the bootstrap")
    parser.add_argument("--check-dir", type=Path, default=DEFAULT_CHECK_DIR,
                        help="where the self-hosting check builds its stages (default .build/release-check)")
    parser.add_argument("--backend", choices=("c", "ssac", "arm64"), default="arm64",
                        help="the backend that compiles the released compiler (stages 2 and 3; default arm64)")
    parser.add_argument("--whole-program", action="store_true",
                        help="release stage 2's whole-program build of the driver rather than stage 2")
    args = parser.parse_args()
    if args.verify:
        problem = verify(target(CURRENT)) if CURRENT.is_dir() else f"there is no current release in {RELEASES}"
        if problem:
            fail(problem)
        print("The current release is sound")
    elif args.rollback:
        rollback()
    elif args.show:
        show()
    elif args.install is not None:
        install(args.install.expanduser().resolve())
    else:
        cut(sys.executable, args.check_dir.resolve(), args.seed, args.backend, args.whole_program)


if __name__ == "__main__":
    main()
