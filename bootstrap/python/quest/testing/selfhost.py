"""The self-hosting checks (docs/testing.md §2.3, docs/release-compiler.md):
building the self-hosted driver with the bootstrap or from the current
release, and checking that it compiles itself to a fixed point, its build
directories compared artifact by artifact."""

import concurrent.futures
import contextlib
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from quest.common.location import BYTE_ENCODING
from quest.testing import releases
from quest.testing.layout import ROOT_DIR, DRIVER_SCRIPT, SELF_HOSTED_DRIVER, build_jobs


def build_self_hosted_driver(python_executable: str, build_dir: Path) -> Path:
    """Compiles the self-hosted driver to an executable in build_dir, with the
    bootstrap."""
    binary = build_dir / "questlang-driver"
    command = [
        python_executable,
        str(DRIVER_SCRIPT),
        "--build-dir",
        str(build_dir / "self-hosted"),
        "-o",
        str(binary),
        str(SELF_HOSTED_DRIVER),
    ]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    process = subprocess.run(command, capture_output=True, text=True, env=environment, cwd=ROOT_DIR)
    if process.returncode != 0:
        sys.exit(f"Compiling {SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)} failed:\n{process.stdout}{process.stderr}")
    return binary


def build_driver_with(driver: Path, build_dir: Path, binary: Path, home: Path = ROOT_DIR, backend: str = "c",
                      whole_program: bool = False) -> float:
    """Compiles the self-hosted driver with the compiled driver `driver`, as
    -o does, into binary, its units' artifacts in build_dir, against the lib/
    and runtime/ in home (a release's own, or the tree's), its units through
    backend (docs/arm64.md section 3.12), or as one unit with whole_program.
    Returns the time the build took, in seconds."""
    return run_driver_build(driver, ["--build-dir", str(build_dir), "-o", str(binary)], home, backend,
                            whole_program, None)


def emit_whole_driver_with(driver: Path, build_dir: Path, output: Path, backend: str = "c") -> float:
    """Writes to output the code (C, or arm64's assembly) the compiled driver
    `driver` writes for the self-hosted driver as a whole program, through
    backend: the unit that -o --whole-program compiles in a temporary directory
    of its own, and so keeps nowhere. Returns the time it took, in seconds."""
    return run_driver_build(driver, ["compile", "--emit-c", "--build-dir", str(build_dir)], ROOT_DIR, backend, True,
                            output)


def run_driver_build(driver: Path, arguments: list[str], home: Path, backend: str, whole_program: bool,
                     output: Optional[Path]) -> float:
    """Runs the compiled driver `driver` on the self-hosted driver, with
    arguments, as build_driver_with and emit_whole_driver_with describe, its
    standard output into output if given. Returns the time it took, in
    seconds."""
    environment = os.environ.copy()
    environment["QUEST_HOME"] = str(home)
    # Against a release's home, the tree's questlang/ is found through -I.
    # Modules compile in parallel (-j), as every release since c787e2d6 can.
    flags = ["-I", str(ROOT_DIR)] if home != ROOT_DIR else []
    flags += ["-j", str(build_jobs())]
    # Named even for c, which a release whose default is arm64 would not use
    # otherwise
    flags += ["--backend", backend]
    if whole_program:
        flags.append("--whole-program")
    # compile is a subcommand, ahead of the options
    command = arguments[:1] + flags + arguments[1:] if arguments[0] == "compile" else flags + arguments
    start = time.perf_counter()
    with output.open("w", encoding=BYTE_ENCODING) if output else contextlib.nullcontext(subprocess.PIPE) as out:
        process = subprocess.run([str(driver), *command, str(SELF_HOSTED_DRIVER)], stdout=out, stderr=subprocess.PIPE,
                                 encoding=BYTE_ENCODING, env=environment, cwd=ROOT_DIR)
    if process.returncode != 0:
        sys.exit(f"{driver} failed to compile {SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}:\n"
                 f"{process.stdout or ''}{process.stderr}")
    return time.perf_counter() - start


def current_release() -> Path:
    """The current release of the self-hosted compiler (docs/release-compiler.md):
    its directory, after checking that its compiler is the binary its
    release.json describes."""
    release = releases.current_release(ROOT_DIR)
    if release is None:
        sys.exit(f"There is no current release in {releases.releases_dir(ROOT_DIR)}; make one with tools/release, "
                 "or use --seed bootstrap")
    binary = release / "quest"
    description = release / "release.json"
    if not binary.is_file() or not description.is_file():
        sys.exit(f"The current release, {release}, has no quest or release.json")
    recorded = json.loads(description.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(binary.read_bytes()).hexdigest() != recorded:
        sys.exit(f"{binary} is not the binary its release.json describes")
    return release


def build_seeded_driver(build_dir: Path) -> Path:
    """Compiles the self-hosted driver from the current release in two stages
    (docs/release-compiler.md section 2), in build_dir/seeded: the release
    builds stage 1 against its own lib/ and runtime/, and stage 1 builds stage 2
    against the tree's. Returns stage 2."""
    release = current_release()
    seeded = build_dir / "seeded"
    stage1 = seeded / "stage1" / "questlang-driver"
    stage2 = seeded / "stage2" / "questlang-driver"
    print("  stage 1 (by the release)...")
    print(f"    {build_driver_with(release / 'quest', seeded / 'stage1' / 'build', stage1, release / 'home'):.1f}s")
    print("  stage 2 (by stage 1)...")
    print(f"    {build_driver_with(stage1, seeded / 'stage2' / 'build', stage2):.1f}s")
    return stage2


# The artifacts a build directory holds for each unit, compared by
# --self-hosting: the C of the c and ssac backends, or arm64's assembly
ARTIFACT_SUFFIXES = (".mod.c", ".main.c", ".mod.s", ".main.s", ".int.h", ".qi", ".qm")

# The backends that can build stages 2 and 3 (--stage-backend)
STAGE_BACKENDS = ("c", "ssac", "arm64")


def normalized_artifact(path: Path, build_dir: Path) -> str:
    """An artifact's text, without what differs between compilers and build
    directories: the producer (informational) and the build directory's path."""
    text = path.read_text(encoding=BYTE_ENCODING)
    if path.name.endswith(".int.h"):
        lines = text.split("\n")
        if lines and lines[0].startswith("/* quest abi"):
            lines = lines[1:]
        text = "\n".join(lines)
    elif path.suffix in (".qi", ".qm"):
        text = re.sub(r'"producer": ?"[^"]*"', '"producer": ""', text)
    for build in sorted({str(build_dir), str(build_dir.resolve())}, key=len, reverse=True):
        text = text.replace(build, "<build>")
    return text


def compare_build_dirs(expected_dir: Path, actual_dir: Path, what: str) -> list[str]:
    """How the artifacts in actual_dir differ from those in expected_dir: the
    files missing from either, and those whose normalized texts differ."""
    def artifacts(d: Path) -> dict[str, Path]:
        return {
            str(f.relative_to(d)): f for f in d.rglob("*")
            if f.is_file() and f.name.endswith(ARTIFACT_SUFFIXES) and "runtime" not in f.relative_to(d).parts
        }

    expected, actual = artifacts(expected_dir), artifacts(actual_dir)
    problems = [f"{what}: missing {name}" for name in sorted(expected.keys() - actual.keys())]
    problems += [f"{what}: extra {name}" for name in sorted(actual.keys() - expected.keys())]
    for name in sorted(expected.keys() & actual.keys()):
        a = normalized_artifact(expected[name], expected_dir)
        b = normalized_artifact(actual[name], actual_dir)
        if a != b:
            diff = list(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                             fromfile=f"expected/{name}", tofile=f"actual/{name}", n=1))
            problems.append(f"{what}: {name} differs\n" + "".join(diff[:40]).rstrip())
    return problems


def check_whole_program_fixed_point(stage2: Path, stages: Path, backend: str) -> list[str]:
    """Checks the whole-program fixed point through backend (docs/testing.md
    section 2.3): stage 2 builds the driver as a whole program, and that
    compiler must write the whole program's code stage 2 writes. Its own
    whole-program build must then be the same compiler, so is not built.
    Returns the problems found, if any."""
    whole = stages / "whole"
    binary = whole / "questlang-driver"
    expected, actual = whole / "stage2.out", whole / "whole.out"
    whole.mkdir(parents=True, exist_ok=True)
    through = "" if backend == "c" else f", through {backend}"
    print(f"Compiling stage 2 as a whole program (by stage 2{through}), and its whole program's code alongside it...")
    # Each is mostly one unit, so they share the cores
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        emitted = executor.submit(emit_whole_driver_with, stage2, whole / "stage2-emit", expected, backend)
        seconds = build_driver_with(stage2, whole / "build", binary, backend=backend, whole_program=True)
        emit_seconds = emitted.result()
    print(f"  {seconds:.1f}s, and {emit_seconds:.1f}s")
    print(f"Writing the whole program's code with the whole-program stage 2{through}...")
    print(f"  {emit_whole_driver_with(binary, whole / 'whole-emit', actual, backend):.1f}s")
    a = expected.read_text(encoding=BYTE_ENCODING)
    b = actual.read_text(encoding=BYTE_ENCODING)
    if not a:
        return [f"whole program{through}: stage 2 wrote no code"]
    if a != b:
        diff = list(difflib.unified_diff(a.splitlines(keepends=True), b.splitlines(keepends=True),
                                         fromfile="stage 2", tofile="whole-program stage 2", n=1))
        return [f"whole program{through}: the whole-program stage 2 writes other code than stage 2\n"
                + "".join(diff[:40]).rstrip()]
    print(f"Whole-program fixed point{through}: the whole-program stage 2 writes the {len(a.encode(BYTE_ENCODING))} "
          "bytes stage 2 wrote")
    return []


def check_self_hosting(python_executable: str, build_dir: Path, seed: str = "bootstrap", backend: str = "c",
                       whole_program: bool = False) -> Path:
    """Builds the three stages of the self-hosted compiler (docs/testing.md
    section 2.3) and checks the fixed point: stage 2 (stage 1's build, stage 1
    being the seed's build of the self-hosted driver) writes the artifacts stage
    1 wrote, for every unit of the driver. Stage 3, stage 2's build, should be
    stage 2's binary, up to the C compiler's own nondeterminism.

    With the release as the seed (docs/release-compiler.md section 3), the
    release builds stage 1 against its own lib/ and runtime/. The bootstrap's
    build of the driver runs alongside it, and builds a stage 2 of its own,
    whose artifacts must be the release's stage 1's: that is, the bootstrap
    still builds the compiler the release does (docs/testing.md section 2.8).

    With a backend other than c (docs/arm64.md section 3.12), stages 2 and 3 are
    built through it: stage 2 is then the compiler as that backend compiles it,
    built by stage 1, compiled by C, and the fixed point is that it writes what
    stage 1 wrote, assembly or C, for every unit. The bootstrap's comparison,
    which does not depend on the backend, is left to the check with c.

    With whole_program, it then checks the whole-program fixed point through
    the backend too (check_whole_program_fixed_point). Returns stage 2, which
    the self-hosted suite then runs."""
    stages = build_dir / "self-hosting"
    shutil.rmtree(stages, ignore_errors=True)
    if seed == "release":
        release = current_release()
        stage1 = stages / "stage1" / "questlang-driver"
        if backend == "c":
            print(f"Compiling stage 1 ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}, by the release), and the "
                  "bootstrap's build alongside it...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                bootstrap = executor.submit(build_self_hosted_driver, python_executable, build_dir)
                seconds = build_driver_with(release / "quest", stages / "stage1" / "build", stage1, release / "home")
                bootstrap_stage1 = bootstrap.result()
        else:
            print(f"Compiling stage 1 ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}, by the release)...")
            seconds = build_driver_with(release / "quest", stages / "stage1" / "build", stage1, release / "home")
        print(f"  {seconds:.1f}s")
    else:
        print(f"Compiling stage 1 ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}, by the bootstrap)...")
        stage1 = build_self_hosted_driver(python_executable, build_dir)
    stage2 = stages / "stage2" / "questlang-driver"
    stage3 = stages / "stage3" / "questlang-driver"
    through = "" if backend == "c" else f", through {backend}"
    print(f"Compiling stage 2 (by stage 1{through})...")
    seconds = build_driver_with(stage1, stages / "stage2" / "build", stage2, backend=backend)
    print(f"  {seconds:.1f}s")
    print(f"Compiling stage 3 (by stage 2{through})...")
    seconds = build_driver_with(stage2, stages / "stage3" / "build", stage3, backend=backend)
    print(f"  {seconds:.1f}s")
    problems = compare_build_dirs(stages / "stage2" / "build", stages / "stage3" / "build", "stage 2 against stage 1")
    if seed == "release" and backend == "c":
        print("Compiling stage 2 again, by the bootstrap's stage 1...")
        seconds = build_driver_with(bootstrap_stage1, stages / "stage2-bootstrap" / "build",
                                    stages / "stage2-bootstrap" / "questlang-driver")
        print(f"  {seconds:.1f}s")
        problems += compare_build_dirs(stages / "stage2" / "build", stages / "stage2-bootstrap" / "build",
                                       "the bootstrap's stage 1 against the release's")
    if whole_program and not problems:
        problems += check_whole_program_fixed_point(stage2, stages, backend)
    if problems:
        print("\n\n".join(problems))
        sys.exit("The self-hosting check failed")
    count = sum(1 for f in (stages / "stage2" / "build").rglob("*") if f.name.endswith(ARTIFACT_SUFFIXES))
    print(f"Fixed point{through}: stage 2 writes the {count} artifacts stage 1 wrote")
    if backend == "c" and seed == "release":
        print("Bootstrappable: the bootstrap's stage 1 writes the release's stage 1's artifacts")
    elif backend == "c":
        print("(Seeded by the bootstrap: --seed release also checks that the bootstrap builds the release's compiler)")
    if stage2.read_bytes() != stage3.read_bytes():
        print("Note: the binaries of stages 2 and 3 differ, from identical " + ("C" if backend != "arm64" else "assembly"))
    else:
        print("Stages 2 and 3 are the same binary")
    return stage2
