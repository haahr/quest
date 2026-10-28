"""Quest Bootstrap Compiler Test Runner.

Each test is a driver run of its own (quest_driver.py, in a subprocess), and so
a compilation session of its own, with its own unit graph and resolver
(docs/build-process.md §2.1): a test's builds never see another's resolutions or
typed units, only the artifacts in the worker's build directory, whose staleness
rules decide whether they are reused (docs/testing.md §2.2).

With --self-hosted, the tests of the phases the self-hosted compiler has run its
driver instead (questlang/driver/main, compiled to C first), against the
bootstrap's goldens and error expectations (docs/milestone-2.md §3).
"""

import argparse
import concurrent.futures
import difflib
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

ROOT_DIR = Path(__file__).resolve().parents[4]

from quest.pipeline import (
    IR_DUMP_PHASES,
    IR_RUN_PHASES,
    PhasePipeline,
    default_pipeline,
    full_pipeline,
    ir_pipeline,
    ir_run_pipeline,
)
from quest.modules.graph import UnitKind, file_unit_kind
from quest.syntax.sources import BYTE_ENCODING
from quest.testing.errors import relativize_root_paths, run_error_test

TESTS_SOURCE_DIR = ROOT_DIR / "tests" / "source"
# The example programs the documentation walks through, run as golden tests too
# (docs/testing.md §2.1)
EXAMPLES_DIR = ROOT_DIR / "examples"
TESTS_GOLDEN_DIR = ROOT_DIR / "tests" / "golden"
TESTS_ERRORS_DIR = ROOT_DIR / "tests" / "errors"
DRIVER_SCRIPT = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"

# The self-hosted compiler's driver, the phases it has, the tests it is not yet
# expected to pass, and where the errors it reports after the bootstrap's one
# are recorded (docs/milestone-2.md §3)
SELF_HOSTED_DRIVER = ROOT_DIR / "questlang" / "driver" / "main.quest"
SELF_HOSTED_PHASES = (
    "tokenize", "parse", "typecheck", *IR_DUMP_PHASES, *IR_RUN_PHASES, "interpret", "codegen_c", "run_c_compiled", "repl",
)
# Where the self-hosted driver builds the units of the programs it compiles to
# C, under each worker's build directory: apart from the bootstrap's artifacts,
# which it would otherwise find fresh and reuse
SELF_HOSTED_UNITS_SUBDIR = "self-hosted-units"
SELF_HOSTED_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending.txt"
SELF_HOSTED_ERRORS_GOLDEN_DIR = TESTS_GOLDEN_DIR / "self-hosted" / "errors"
# Tests of several errors, which only the self-hosted driver reports:
# tests/self-hosted/errors/PHASE/NAME.quest
# The programs the self-hosted driver's -e runs, and the bootstrap's transcript
# of them (docs/milestone-3.md §3.2), which tests/eval/generate.py writes
EVAL_CASES = ROOT_DIR / "tests" / "eval" / "cases.quest"
# The checks of the self-hosted driver's unit files (-c): interfaces against its
# ABI corpus (tests/abi/corpus-self-hosted), and that lib/'s modules compile;
# and of the errors its builds report, against the bootstrap's; and that its
# parallel builds (-j) are its serial ones
UNIT_CHECKS = (
    ("self-hosted/abi_corpus", ROOT_DIR / "tests" / "abi" / "corpus.py", ("--compiler",)),
    ("self-hosted/unit_artifacts", ROOT_DIR / "tests" / "self-hosted" / "unit_artifacts.py", ()),
    ("self-hosted/build_errors", ROOT_DIR / "tests" / "self-hosted" / "build_errors.py", ()),
    ("self-hosted/parallel_build", ROOT_DIR / "tests" / "self-hosted" / "parallel_build.py", ()),
)
EVAL_GOLDEN = TESTS_GOLDEN_DIR / "self-hosted" / "eval.out"
SELF_HOSTED_ERRORS_DIR = ROOT_DIR / "tests" / "self-hosted" / "errors"
# REPL transcripts: each tests/repl/NAME.quest is the input to quest -i, and
# tests/golden/repl/NAME.out what it writes (docs/testing.md §2.7);
# tests/repl/files holds what they load
TESTS_REPL_DIR = ROOT_DIR / "tests" / "repl"
TESTS_REPL_GOLDEN_DIR = TESTS_GOLDEN_DIR / "repl"
TELEMETRY_LOG_PATH = Path("/tmp/quest_run_tests_telemetry.log")


def record_telemetry(total_duration: float, tests_run: int, workers_used: int) -> None:
    """Appends execution telemetry to /tmp/quest_run_tests_telemetry.log on
    successful test runs."""
    timestamp = datetime.now().astimezone().isoformat()
    log_line = (
        f"{timestamp} | duration={total_duration:.2f}s | tests={tests_run} | workers={workers_used}\n"
    )
    try:
        TELEMETRY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TELEMETRY_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(log_line)
    except OSError as err:
        print(f"Warning: could not write telemetry to {TELEMETRY_LOG_PATH}: {err}", file=sys.stderr)


SKIP_PHASE_PATTERN = re.compile(r"\(\*\s*@skip-phase:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
ARGS_PATTERN = re.compile(r"\(\*\s*@args:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
ENV_PATTERN = re.compile(r"\(\*\s*@env:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
EXIT_PATTERN = re.compile(r"\(\*\s*@exit:\s*([0-9]+)\s*\*\)", re.IGNORECASE)
TIMEOUT_PATTERN = re.compile(r"\(\*\s*@timeout:\s*([0-9.]+)\s*\*\)", re.IGNORECASE)
ECHO_PATTERN = re.compile(r"\(\*\s*@echo\s*\*\)", re.IGNORECASE)
LOAD_PATTERN = re.compile(r"\(\*\s*@load:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
STDIN_PATTERN = re.compile(r"\(\*\s*@stdin:(?:[ \t]*\r?\n)?(.*?)\*\)", re.DOTALL | re.IGNORECASE)


@dataclass
class TestDirectives:
    """Directives extracted from test source comments."""
    skipped_phases: set[str] = field(default_factory=set)
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    exit_code: int = 0
    timeout: Optional[float] = None
    stdin_data: Optional[str] = None
    echo: bool = False


def _os_arg(text: str) -> str:
    """Text from a test's source, a character per byte, as a string that
    subprocess gives the OS as those bytes."""
    return os.fsdecode(text.encode(BYTE_ENCODING))


def parse_test_directives(source_file: Path) -> TestDirectives:
    """Extracts test directives (@skip-phase, @args, @env, @exit, @timeout,
    @stdin, @echo) from comments."""
    text = source_file.read_text(encoding=BYTE_ENCODING)

    skipped: set[str] = set()
    for match in SKIP_PHASE_PATTERN.finditer(text):
        raw = match.group(1)
        for part in re.split(r"[,;\s]+", raw):
            cleaned = part.strip().lower()
            if cleaned:
                skipped.add(cleaned)

    args: list[str] = []
    for match in ARGS_PATTERN.finditer(text):
        raw_args = match.group(1).strip()
        if raw_args:
            args.extend(_os_arg(a) for a in shlex.split(raw_args))

    env: dict[str, str] = {}
    for match in ENV_PATTERN.finditer(text):
        raw_env = match.group(1).strip()
        if raw_env:
            for item in shlex.split(raw_env):
                if "=" in item:
                    k, v = item.split("=", 1)
                    env[_os_arg(k)] = _os_arg(v)
                else:
                    env[_os_arg(item)] = ""

    exit_code = 0
    for match in EXIT_PATTERN.finditer(text):
        exit_code = int(match.group(1))

    custom_timeout: Optional[float] = None
    for match in TIMEOUT_PATTERN.finditer(text):
        custom_timeout = float(match.group(1))

    stdin_chunks: list[str] = []
    for match in STDIN_PATTERN.finditer(text):
        stdin_chunks.append(match.group(1))
    stdin_data = "".join(stdin_chunks) if stdin_chunks else None

    return TestDirectives(
        skipped_phases=skipped,
        args=args,
        env=env,
        exit_code=exit_code,
        timeout=custom_timeout,
        stdin_data=stdin_data,
        echo=ECHO_PATTERN.search(text) is not None,
    )


def parse_skipped_phases(source_file: Path) -> set[str]:
    """Extracts skipped phase names from (* @skip-phase: ... *) comments."""
    return parse_test_directives(source_file).skipped_phases


def discover_tests(directory: Path) -> list[Path]:
    """Returns the test programs under directory: every .quest file holding a
    program. Interfaces and modules beside the tests are imported by them, not
    run as tests (docs/testing.md §2.6)."""
    return sorted(p for p in directory.rglob("*.quest") if file_unit_kind(p) == UnitKind.PROGRAM)


def golden_test_id(source_file: Path) -> Path:
    """The path of a golden test's program relative to its goldens' directories:
    its path within tests/source, or within examples/ under examples/."""
    try:
        return source_file.relative_to(TESTS_SOURCE_DIR)
    except ValueError:
        return Path("examples") / source_file.relative_to(EXAMPLES_DIR)


# The IR's stages after Core are dumped (and compared with goldens) for a subset
# of the programs, chosen to exercise each pass: those that have a golden in the
# stage's directory. (Every program runs through every stage, verified, in the
# run_ir phases.) To add a program to a stage's subset, create its golden file
# empty and update goldens.
SUBSET_PHASES = IR_DUMP_PHASES[1:]

# The phases that run programs, whose output is compared with the run goldens
RUN_PHASES = ("interpret", "run_c_compiled", *IR_RUN_PHASES)

# The phase printing each run program's C as run_c_compiled compiles it (with
# --print-result, and --echo where the program asks for it). Its goldens are
# digests of the C (c_digest), as the C is about 37 KB a program.
CODEGEN_PHASE = "codegen_c"

# The goldens of how a compiler compiles, rather than of what programs do, are
# each compiler's own (docs/testing.md section 2.8): the IR dumps are the
# self-hosted compiler's alone, and the C digests are its in
# tests/golden/codegen_c and the bootstrap's in tests/golden/bootstrap/codegen_c.
# The other phases' goldens are shared: both compilers must match them, and the
# bootstrap writes them, since what programs do changes in both.
BOOTSTRAP_GOLDEN_DIR = TESTS_GOLDEN_DIR / "bootstrap"
SELF_HOSTED_OWN_PHASES = (*IR_DUMP_PHASES, CODEGEN_PHASE)


def writes_golden(phase_name: str, self_hosted: bool) -> bool:
    """Whether --update-golden with the self-hosted compiler (or with the
    bootstrap) writes a phase's goldens."""
    if self_hosted:
        return phase_name in SELF_HOSTED_OWN_PHASES
    return phase_name not in IR_DUMP_PHASES


def c_digest(c_text: str) -> str:
    """The golden of a program's C: the SHA-256 of its text, with the paths in
    it under the checkout relative to it (raise sites name the program's
    file), so that the digest does not depend on where the checkout is."""
    text = relativize_root_paths(c_text, ROOT_DIR)
    return hashlib.sha256(text.encode(BYTE_ENCODING)).hexdigest() + "\n"


def bootstrap_c(source_file: Path, echo: bool, python_executable: str, build_dir: Path, timeout: float) -> str:
    """The bootstrap's C for a program, to show how another compiler's
    differs."""
    command = [python_executable, str(DRIVER_SCRIPT), "--stop-after", CODEGEN_PHASE, "--print-result",
               "--build-dir", str(build_dir)]
    if echo:
        command.append("--echo")
    command.append(str(source_file.resolve()))
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
        process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding=BYTE_ENCODING,
                                 env=environment, timeout=timeout, cwd=scratch_dir)
    return process.stdout


# The tests of the self-hosted compiler's modules run compiled only: under the
# bootstrap's interpreters, each would interpret the compiler's code for minutes.
# Their modules are compiled once per run, into a build directory the tests
# share (build_questlang_tests).
QUESTLANG_TESTS_DIR = TESTS_SOURCE_DIR / "questlang"
QUESTLANG_INTERPRETED_PHASES = ("interpret", *IR_RUN_PHASES)
QUESTLANG_BUILD_SUBDIR = "questlang-tests"
QUESTLANG_SELF_HOSTED_BUILD_SUBDIR = "self-hosted-questlang-tests"


def is_questlang_test(source_file: Path) -> bool:
    return source_file.is_relative_to(QUESTLANG_TESTS_DIR)


def build_questlang_tests(
    python_executable: str, source_files: list[Path], build_dir: Path, driver_command: Optional[list[str]] = None
) -> None:
    """Compiles and links the questlang tests in build_dir, one at a time, with
    the bootstrap's driver or driver_command, so that the modules they import
    are compiled once. Their run_c_compiled phase then runs them in parallel in
    build_dir, once this has finished, reading the fresh artifacts and writing
    only their own programs'. Their other phases, which run while this builds,
    use their workers' own build directories, since they compile into the build
    directory they are given. A test that fails to build here fails when it
    runs, and reports why."""
    build_dir.mkdir(parents=True, exist_ok=True)
    for source_file in source_files:
        command = [
            # The self-hosted driver compiles the modules in parallel
            *(driver_command + ["-j", str(os.cpu_count() or 1)] if driver_command
              else [python_executable, str(DRIVER_SCRIPT)]),
            "--build-dir",
            str(build_dir),
            "-o",
            str(build_dir / source_file.stem),
            str(source_file.resolve()),
        ]
        subprocess.run(command, capture_output=True, env=golden_environment(), cwd=ROOT_DIR)


def self_hosted_units_dir(build_dir: Path) -> Path:
    """Where the self-hosted driver builds the units of programs compiled to C
    for a worker whose build directory is build_dir: the questlang tests' shared
    directory itself, else a subdirectory of the worker's."""
    return build_dir if build_dir.name == QUESTLANG_SELF_HOSTED_BUILD_SUBDIR else build_dir / SELF_HOSTED_UNITS_SUBDIR


def golden_dir_for_phase(phase_name: str, self_hosted: bool = False) -> Path:
    if phase_name in RUN_PHASES:
        return TESTS_GOLDEN_DIR / "run"
    if phase_name == CODEGEN_PHASE and not self_hosted:
        return BOOTSTRAP_GOLDEN_DIR / phase_name
    return TESTS_GOLDEN_DIR / phase_name


def error_dir_for_phase(phase_name: str) -> Path:
    # Every phase that runs programs locates run-time errors at their raise
    # sites (docs/exceptions.md §3)
    if phase_name in RUN_PHASES:
        return TESTS_ERRORS_DIR / "run"
    return TESTS_ERRORS_DIR / phase_name


def golden_error_file_for_test(source_file: Path, phase_name: str) -> Path:
    phase_folder = "run" if phase_name in RUN_PHASES else phase_name
    base_dir = TESTS_ERRORS_DIR / phase_folder
    try:
        rel_path = source_file.relative_to(base_dir)
    except ValueError:
        try:
            rel_path = source_file.relative_to(TESTS_ERRORS_DIR / phase_name)
        except ValueError:
            rel_path = Path(source_file.name)
    return TESTS_GOLDEN_DIR / "errors" / phase_folder / rel_path.with_suffix(".error")


def pipeline_for_phase(phase_name: str) -> PhasePipeline:
    if phase_name in ("codegen_c", "run_c_compiled"):
        return full_pipeline()
    if phase_name in IR_RUN_PHASES:
        return ir_run_pipeline(phase_name.removeprefix("run_ir_"))
    if phase_name in IR_DUMP_PHASES:
        return ir_pipeline(phase_name.removeprefix("ir_"))
    return default_pipeline()


def golden_environment() -> dict[str, str]:
    """The environment golden tests' drivers run in."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    # Checks the C back end's canonical forms of types, which outside the tests
    # only warn (docs/c-representation.md §5.7)
    environment["QUEST_CHECK_CANONICAL"] = "1"
    # Checks that typed programs are well scoped (quest/typechecker/scoping.py)
    environment["QUEST_CHECK_SCOPES"] = "1"
    # Checks the IR's invariants after lowering (quest/ir/verify.py)
    environment["QUEST_CHECK_IR"] = "1"
    # The project directory, whose lib/ the self-hosted driver reads the
    # standard library from (it runs elsewhere)
    environment["QUEST_HOME"] = str(ROOT_DIR)
    return environment


def run_single_golden_test(
    source_file: Path,
    phase_name: str,
    update_golden: bool = False,
    python_executable: str = sys.executable,
    timeout: float = 30.0,
    build_dir: Optional[Path] = None,
    driver_args: Optional[list[str]] = None,
    driver_command: Optional[list[str]] = None,
) -> tuple[bool, str, str]:
    """Runs a golden test with the bootstrap driver, or the one driver_command
    runs (the self-hosted driver), against the phase's goldens for that compiler
    (golden_dir_for_phase), writing them with update_golden if it writes them
    (writes_golden)."""
    golden_base = golden_dir_for_phase(phase_name, driver_command is not None)
    rel_source = golden_test_id(source_file)
    target_dir = golden_base / rel_source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{source_file.stem}.out"

    directives = parse_test_directives(source_file)
    expected_exit = directives.exit_code if phase_name in RUN_PHASES else 0
    effective_timeout = directives.timeout if directives.timeout is not None else timeout

    if driver_command is not None:
        command = [*driver_command, "--stop-after", phase_name]
        # The units of programs compiled to C are built and reused there
        if phase_name in (CODEGEN_PHASE, "run_c_compiled") and build_dir is not None:
            command.extend(["--build-dir", str(self_hosted_units_dir(build_dir))])
    else:
        command = [
            python_executable,
            str(DRIVER_SCRIPT),
            "--stop-after",
            phase_name,
        ]
        if driver_args:
            command.extend(driver_args)
        # Every phase builds and reuses artifacts in the build directory
        # (docs/build-process.md §5.2.4).
        if build_dir is None:
            build_dir = ROOT_DIR / ".build"
        build_dir.mkdir(parents=True, exist_ok=True)
        command.extend(["--build-dir", str(build_dir)])
    if expected_exit != 0:
        command.extend(["--expected-exit", str(expected_exit)])
    if directives.echo and phase_name in (*RUN_PHASES, CODEGEN_PHASE):
        command.append("--echo")
    if phase_name == CODEGEN_PHASE:
        command.append("--print-result")

    command.append(str(source_file.resolve()))

    # The arguments after the program file are the program's
    if directives.args and phase_name in RUN_PHASES:
        command.extend(directives.args)

    environment = golden_environment()
    if directives.env and phase_name in RUN_PHASES:
        environment.update(directives.env)

    try:
        # Each run starts in a fresh, empty directory of its own, where the
        # program may create files (docs/testing.md §2.2)
        with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=BYTE_ENCODING,
                input=directives.stdin_data if phase_name in RUN_PHASES else None,
                env=environment,
                timeout=effective_timeout,
                cwd=scratch_dir,
            )
    except subprocess.TimeoutExpired as exc:
        msg = f"  (TIMED OUT after {effective_timeout:.1f}s)"
        stderr = exc.stderr if isinstance(exc.stderr, str) else (
            exc.stderr.decode(BYTE_ENCODING, errors="replace") if exc.stderr else ""
        )
        if stderr:
            for line in stderr.strip().splitlines()[:15]:
                msg += f"\n    {line}"
        return False, "[FAIL]", msg

    # A golden test is a valid program: one that exits with any other code
    # fails, even when updating goldens. Programs that should be rejected are
    # error tests (docs/testing.md §3).
    if process.returncode != expected_exit:
        msg = f"  (failed with returncode {process.returncode}, expected {expected_exit})"
        if process.stderr:
            msg += f"\n{process.stderr.rstrip()}"
        return False, "[FAIL]", msg

    output = c_digest(process.stdout) if phase_name == CODEGEN_PHASE else process.stdout
    if update_golden and writes_golden(phase_name, driver_command is not None):
        out_file.write_text(output, encoding=BYTE_ENCODING)
        return True, "[UPDATED]", ""

    if not out_file.exists():
        return False, "[MISSING GOLDEN]", f"  (expected {out_file.relative_to(ROOT_DIR)})"

    expected_output = out_file.read_text(encoding=BYTE_ENCODING)
    if output == expected_output:
        return True, "[PASS]", ""

    if phase_name == CODEGEN_PHASE:
        # A digest tells nothing of the difference. For the self-hosted
        # compiler, the bootstrap's C shows how it differs from that, which
        # was the same C until the compilers diverged.
        msg = "  (C digest mismatch)"
        if driver_command is not None and build_dir is not None:
            expected_c = bootstrap_c(source_file, directives.echo, python_executable, build_dir, effective_timeout)
            diff = list(difflib.unified_diff(
                relativize_root_paths(expected_c, ROOT_DIR).splitlines(keepends=True),
                relativize_root_paths(process.stdout, ROOT_DIR).splitlines(keepends=True),
                fromfile=f"bootstrap/{rel_source.with_suffix('.c')}",
                tofile=f"actual/{rel_source.with_suffix('.c')}",
            ))
            msg += "\n" + "".join(diff[:80]).rstrip()
        return False, "[FAIL]", msg

    diff = difflib.unified_diff(
        expected_output.splitlines(keepends=True),
        process.stdout.splitlines(keepends=True),
        fromfile=f"golden/{golden_base.name}/{rel_source.with_suffix('.out')}",
        tofile=f"actual/{golden_base.name}/{rel_source.with_suffix('.out')}",
    )
    return False, "[FAIL]", "  (stdout mismatch)\n" + "".join(diff).rstrip()


@dataclass
class PhaseTask:
    test_id: str
    run_fn: Callable[[Path], tuple[bool, str, str]]


def run_phase_tasks(
    phase: str,
    tasks: list[PhaseTask],
    pool: queue.Queue[Path],
    executor: concurrent.futures.ThreadPoolExecutor,
    jobs: int,
) -> tuple[int, int]:
    """Executes a list of tasks for a given phase using the worker pool,
    printing results."""
    if not tasks:
        return 0, 0

    total_count = len(tasks)
    passed_count = 0

    if jobs == 1:
        for task in tasks:
            worker_dir = pool.get()
            try:
                passed, status, report = task.run_fn(worker_dir)
            finally:
                pool.put(worker_dir)
            if passed:
                passed_count += 1
            print(f"  {status} {phase}:{task.test_id}")
            if report:
                print(report)
        return total_count, passed_count

    def _worker(task: PhaseTask) -> tuple[PhaseTask, bool, str, str]:
        worker_dir = pool.get()
        try:
            passed, status, report = task.run_fn(worker_dir)
            return task, passed, status, report
        finally:
            pool.put(worker_dir)

    futures = [executor.submit(_worker, task) for task in tasks]
    for fut in concurrent.futures.as_completed(futures):
        task, passed, status, report = fut.result()
        if passed:
            passed_count += 1
        print(f"  {status} {phase}:{task.test_id}")
        if report:
            print(report)

    return total_count, passed_count


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


def build_driver_with(driver: Path, build_dir: Path, binary: Path, home: Path = ROOT_DIR) -> float:
    """Compiles the self-hosted driver with the compiled driver `driver`, as
    -o does, into binary, its units' artifacts in build_dir, against the lib/
    and runtime/ in home (a release's own, or the tree's). Returns the time the
    build took, in seconds."""
    environment = os.environ.copy()
    environment["QUEST_HOME"] = str(home)
    # Against a release's home, the tree's questlang/ is found through -I. A
    # driver built from the tree compiles modules in parallel (-j); a release
    # may be older than -j.
    include = ["-I", str(ROOT_DIR)] if home != ROOT_DIR else ["-j", str(os.cpu_count() or 1)]
    start = time.perf_counter()
    process = subprocess.run(
        [str(driver), *include, "--build-dir", str(build_dir), "-o", str(binary), str(SELF_HOSTED_DRIVER)],
        capture_output=True, encoding=BYTE_ENCODING, env=environment, cwd=ROOT_DIR,
    )
    if process.returncode != 0:
        sys.exit(f"{driver} failed to compile {SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}:\n"
                 f"{process.stdout}{process.stderr}")
    return time.perf_counter() - start


# The current release of the self-hosted compiler (docs/release-compiler.md)
RELEASE_DIR = ROOT_DIR / "release" / "current"


def current_release() -> Path:
    """The current release's compiler, after checking that it is the binary
    its release.json describes."""
    binary = RELEASE_DIR / "questc"
    description = RELEASE_DIR / "release.json"
    if not binary.is_file() or not description.is_file():
        sys.exit("There is no release in release/current; make one with tools/release, or use --seed bootstrap")
    recorded = json.loads(description.read_text(encoding="utf-8"))["sha256"]
    if hashlib.sha256(binary.read_bytes()).hexdigest() != recorded:
        sys.exit("release/current/questc is not the binary its release.json describes")
    return binary


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
    print(f"    {build_driver_with(release, seeded / 'stage1' / 'build', stage1, RELEASE_DIR / 'home'):.1f}s")
    print("  stage 2 (by stage 1)...")
    print(f"    {build_driver_with(stage1, seeded / 'stage2' / 'build', stage2):.1f}s")
    return stage2


# The artifacts a build directory holds for each unit, compared by
# --self-hosting
ARTIFACT_SUFFIXES = (".mod.c", ".main.c", ".int.h", ".qi", ".qm")


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


def check_self_hosting(python_executable: str, build_dir: Path, seed: str = "bootstrap") -> Path:
    """Builds the three stages of the self-hosted compiler (docs/milestone-5.md
    section 2.3) and checks the fixed point: stage 2 (stage 1's build, stage 1
    being the seed's build of the self-hosted driver) writes the artifacts stage
    1 wrote, for every unit of the driver. Stage 3, stage 2's build, should be
    stage 2's binary, up to the C compiler's own nondeterminism.

    With the release as the seed (docs/release-compiler.md section 3), the
    release builds stage 1 against its own lib/ and runtime/. The bootstrap's
    build of the driver runs alongside it, and builds a stage 2 of its own,
    whose artifacts must be the release's stage 1's: that is, the bootstrap
    still builds the compiler the release does (docs/testing.md section 2.8).
    Returns stage 2, which the self-hosted suite then runs."""
    stages = build_dir / "self-hosting"
    shutil.rmtree(stages, ignore_errors=True)
    if seed == "release":
        release = current_release()
        print(f"Compiling stage 1 ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}, by the release), and the "
              "bootstrap's build alongside it...")
        stage1 = stages / "stage1" / "questlang-driver"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            bootstrap = executor.submit(build_self_hosted_driver, python_executable, build_dir)
            seconds = build_driver_with(release, stages / "stage1" / "build", stage1, RELEASE_DIR / "home")
            bootstrap_stage1 = bootstrap.result()
        print(f"  {seconds:.1f}s")
    else:
        print(f"Compiling stage 1 ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}, by the bootstrap)...")
        stage1 = build_self_hosted_driver(python_executable, build_dir)
    stage2 = stages / "stage2" / "questlang-driver"
    stage3 = stages / "stage3" / "questlang-driver"
    print("Compiling stage 2 (by stage 1)...")
    seconds = build_driver_with(stage1, stages / "stage2" / "build", stage2)
    print(f"  {seconds:.1f}s")
    print("Compiling stage 3 (by stage 2)...")
    seconds = build_driver_with(stage2, stages / "stage3" / "build", stage3)
    print(f"  {seconds:.1f}s")
    problems = compare_build_dirs(stages / "stage2" / "build", stages / "stage3" / "build", "stage 2 against stage 1")
    if seed == "release":
        print("Compiling stage 2 again, by the bootstrap's stage 1...")
        seconds = build_driver_with(bootstrap_stage1, stages / "stage2-bootstrap" / "build",
                                    stages / "stage2-bootstrap" / "questlang-driver")
        print(f"  {seconds:.1f}s")
        problems += compare_build_dirs(stages / "stage2" / "build", stages / "stage2-bootstrap" / "build",
                                       "the bootstrap's stage 1 against the release's")
    if problems:
        print("\n\n".join(problems))
        sys.exit("The self-hosting check failed")
    count = sum(1 for f in (stages / "stage2" / "build").rglob("*") if f.name.endswith(ARTIFACT_SUFFIXES))
    print(f"Fixed point: stage 2 writes the {count} artifacts stage 1 wrote")
    if seed == "release":
        print("Bootstrappable: the bootstrap's stage 1 writes the release's stage 1's artifacts")
    else:
        print("(Seeded by the bootstrap: --seed release also checks that the bootstrap builds the release's compiler)")
    if stage2.read_bytes() != stage3.read_bytes():
        print("Note: the binaries of stages 2 and 3 differ, from identical C")
    else:
        print("Stages 2 and 3 are the same binary")
    return stage2


def eval_programs() -> list[str]:
    """The programs of tests/eval/cases.quest, one per line, after its opening
    comment."""
    lines = EVAL_CASES.read_text(encoding=BYTE_ENCODING).splitlines()
    end = next(i for i, line in enumerate(lines) if line.rstrip().endswith("*)"))
    return [line for line in lines[end + 1:] if line.strip()]


def eval_transcript(driver_command: list[str], timeout: float = 30.0) -> str:
    """What a driver writes for each program of eval_programs run with -e: its
    standard output and error, and its exit status, each run in a fresh
    directory of its own."""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    environment["QUEST_HOME"] = str(ROOT_DIR)
    parts: list[str] = []
    for program in eval_programs():
        with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
            process = subprocess.run(
                [*driver_command, "-e", program],
                capture_output=True,
                encoding=BYTE_ENCODING,
                env=environment,
                timeout=timeout,
                cwd=scratch_dir,
            )
        parts.append(f"=== {program}\n--- stdout\n{process.stdout}--- stderr\n{process.stderr}--- exit {process.returncode}\n")
    return "".join(parts)


def run_eval_test(driver_command: list[str], timeout: float) -> tuple[bool, str, str]:
    """The self-hosted driver's -e against the bootstrap's transcript
    (eval_transcript)."""
    actual = eval_transcript(driver_command, timeout)
    expected = EVAL_GOLDEN.read_text(encoding=BYTE_ENCODING)
    if actual == expected:
        return True, "[PASS]", ""
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True), actual.splitlines(keepends=True),
        fromfile="golden/self-hosted/eval.out", tofile="actual/self-hosted/eval.out",
    )
    return False, "[FAIL]", "  (transcript mismatch)\n" + "".join(diff).rstrip()


def run_unit_check(python_executable: str, script: Path, args: tuple[str, ...], driver: str) -> tuple[bool, str, str]:
    """Runs one of UNIT_CHECKS on the self-hosted driver: it passes if the
    script exits with 0."""
    process = subprocess.run([python_executable, str(script), *args, driver], capture_output=True,
                             encoding=BYTE_ENCODING)
    if process.returncode == 0:
        return True, "[PASS]", ""
    return False, "[FAIL]", "  (" + script.relative_to(ROOT_DIR).as_posix() + " failed)\n" + (
        process.stdout + process.stderr).rstrip()[-4000:]


def discover_repl_tests() -> list[Path]:
    """The REPL transcripts: the .quest files directly in tests/repl."""
    return sorted(TESTS_REPL_DIR.glob("*.quest"))


def repl_transcript(source_file: Path, command: list[str], timeout: float) -> tuple[str, int]:
    """What a driver writes when source_file is the input to its REPL
    (quest -i), in a fresh directory of its own: its standard output and error,
    and its exit status. An @load directive names a file, relative to
    tests/repl, for -i to run first; the @args are the program's arguments,
    after the file or a --."""
    directives = parse_test_directives(source_file)
    text = source_file.read_text(encoding=BYTE_ENCODING)
    load = LOAD_PATTERN.search(text)
    command = [*command, "-i"]
    if load:
        command.append(str((TESTS_REPL_DIR / load.group(1)).resolve()))
    elif directives.args:
        command.append("--")
    command.extend(directives.args)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    environment["QUEST_HOME"] = str(ROOT_DIR)
    environment["QUEST_CHECK_CANONICAL"] = "1"
    environment["QUEST_CHECK_SCOPES"] = "1"
    environment["QUEST_CHECK_IR"] = "1"
    environment.update(directives.env)
    with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
        process = subprocess.run(
            command,
            input=text,
            capture_output=True,
            encoding=BYTE_ENCODING,
            env=environment,
            timeout=directives.timeout or timeout,
            cwd=scratch_dir,
        )
        transcript = f"--- stdout\n{process.stdout}--- stderr\n{process.stderr}--- exit {process.returncode}\n"
        # The scratch directory and the checkout, which the module system's
        # errors name, and the checkout's files, by relative paths
        for scratch in sorted({scratch_dir, os.path.realpath(scratch_dir)}, key=len, reverse=True):
            transcript = transcript.replace(scratch, "<scratch>")
    transcript = relativize_root_paths(transcript, ROOT_DIR)
    for root in sorted({str(ROOT_DIR), str(ROOT_DIR.resolve())}, key=len, reverse=True):
        transcript = transcript.replace(root, "<root>")
    return transcript, process.returncode


def run_repl_test(
    source_file: Path,
    update_golden: bool,
    python_executable: str,
    timeout: float,
    build_dir: Path,
    driver_command: Optional[list[str]],
) -> tuple[bool, str, str]:
    """A REPL transcript (repl_transcript) against its golden, with the
    bootstrap's driver or driver_command."""
    command = driver_command or [python_executable, str(DRIVER_SCRIPT), "--build-dir", str(build_dir)]
    out_file = TESTS_REPL_GOLDEN_DIR / source_file.with_suffix(".out").name
    try:
        actual, _ = repl_transcript(source_file, command, timeout)
    except subprocess.TimeoutExpired:
        return False, "[FAIL]", "  (TIMED OUT)"
    if update_golden and driver_command is None:
        out_file.write_text(actual, encoding=BYTE_ENCODING)
        return True, "[UPDATED]", ""
    if not out_file.exists():
        return False, "[MISSING GOLDEN]", f"  (expected {out_file.relative_to(ROOT_DIR)})"
    expected = out_file.read_text(encoding=BYTE_ENCODING)
    if actual == expected:
        return True, "[PASS]", ""
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True), actual.splitlines(keepends=True),
        fromfile=f"golden/repl/{out_file.name}", tofile=f"actual/repl/{out_file.name}",
    )
    return False, "[FAIL]", "  (transcript mismatch)\n" + "".join(diff).rstrip()


def self_hosted_pending() -> set[str]:
    """The tests the self-hosted driver is not yet expected to pass: PHASE:TEST
    for a golden test, and errors/PHASE:TEST for an error test, one per line (#
    starts a comment)."""
    if not SELF_HOSTED_PENDING.exists():
        return set()
    entries = (line.split("#", 1)[0].strip() for line in SELF_HOSTED_PENDING.read_text(encoding="utf-8").splitlines())
    return {entry for entry in entries if entry}


def with_pending(
    key: str, pending: set[str], counts: dict[str, int], run_fn: Callable[[Path], tuple[bool, str, str]]
) -> Callable[[Path], tuple[bool, str, str]]:
    """run_fn, for a test that may be pending: a pending test that fails is
    reported as pending, and one that passes fails, so that it is taken off the
    list."""
    if key not in pending:
        return run_fn

    def run(w_dir: Path) -> tuple[bool, str, str]:
        passed, status, report = run_fn(w_dir)
        if passed:
            return False, "[FAIL]", f"  (passes, but is pending: remove '{key}' from {SELF_HOSTED_PENDING.name})"
        counts["pending"] += 1
        return True, "[PENDING]", ""

    return run


def main() -> int:
    available_phases = [
        "tokenize",
        "parse",
        "typecheck",
        *IR_DUMP_PHASES,
        *IR_RUN_PHASES,
        "interpret",
        CODEGEN_PHASE,
        "run_c_compiled",
        "repl",
    ]

    arg_parser = argparse.ArgumentParser(description="Run Quest compiler tests (golden outputs and error suites).")
    arg_parser.add_argument(
        "--phase", choices=available_phases + ["all"], default="all", help="Compiler phase to test."
    )
    arg_parser.add_argument(
        "--suite",
        choices=["golden", "errors", "all"],
        default="all",
        help="Test suite to run (default: all).",
    )
    arg_parser.add_argument(
        "--errors",
        action="store_true",
        help="Shorthand for --suite errors.",
    )
    arg_parser.add_argument("--test", "-k", help="Filter test name substring or exact filename.")
    arg_parser.add_argument(
        "--update-golden", action="store_true", help="Overwrite golden files with actual test output."
    )
    arg_parser.add_argument(
        "--python",
        default="/opt/homebrew/opt/python@3.11/libexec/bin/python",
        help="Python binary to use.",
    )
    arg_parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Timeout in seconds for each individual test run (default: 30.0s).",
    )
    arg_parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=min(8, os.cpu_count() or 4),
        help="Number of concurrent test workers (default: min(8, CPU count), 1 for serial).",
    )
    arg_parser.add_argument(
        "--workers",
        type=int,
        dest="jobs",
        help="Alias for --jobs.",
    )

    arg_parser.add_argument(
        "--self-hosted",
        action="store_true",
        help="Test the self-hosted compiler: compile its driver, and run it on the tests of the phases it has, "
        "against the shared goldens and its own (docs/testing.md section 2.8).",
    )
    arg_parser.add_argument(
        "--self-hosted-driver",
        metavar="PATH",
        help="With --self-hosted, run this compiled self-hosted driver rather than compiling one.",
    )

    arg_parser.add_argument(
        "--self-hosting",
        action="store_true",
        help="Check that the self-hosted compiler compiles itself to a fixed point (stages 1 to 3), then run the "
        "self-hosted suite with stage 2.",
    )
    arg_parser.add_argument(
        "--seed",
        choices=["bootstrap", "release"],
        default="bootstrap",
        help="What builds the self-hosted driver for --self-hosted and --self-hosting: the bootstrap (the default, "
        "one build), or the current release in release/current (two stages, docs/release-compiler.md).",
    )

    arg_parser.add_argument(
        "--build-dir",
        help="Build directory for C phases, reused across runs (default: a fresh temporary directory per run, "
        "so that results never depend on artifacts from earlier compiler versions).",
    )

    args = arg_parser.parse_args()

    jobs = max(1, args.jobs)
    if args.build_dir:
        build_dir = Path(args.build_dir).resolve()
        temp_build_dir: Optional[Path] = None
    else:
        temp_build_dir = Path(tempfile.mkdtemp(prefix="quest-test-build-"))
        build_dir = temp_build_dir
    driver_args: list[str] = []
    try:
        return run_all_tests(args, available_phases, build_dir, driver_args, jobs=jobs)
    finally:
        if temp_build_dir is not None:
            shutil.rmtree(temp_build_dir, ignore_errors=True)


def run_all_tests(
    args: argparse.Namespace,
    available_phases: list[str],
    build_dir: Path,
    driver_args: list[str],
    jobs: int = 1,
) -> int:
    start_time = time.perf_counter()

    # Determine suite mode
    suite_mode = "errors" if args.errors else args.suite

    # Fallback to sys.executable if specified python does not exist
    python_executable = args.python if os.path.exists(args.python) else sys.executable

    phases_to_run = available_phases if args.phase == "all" else [args.phase]

    driver_command: Optional[list[str]] = None
    pending: set[str] = set()
    pending_counts = {"pending": 0}
    if args.self_hosting:
        args.self_hosted = True
        args.self_hosted_driver = str(check_self_hosting(python_executable, build_dir, args.seed))
    if not args.self_hosted and args.phase == "all":
        # The IR dumps are the self-hosted compiler's; --phase runs one with the
        # bootstrap, to compare its IR with them
        phases_to_run = [phase for phase in phases_to_run if phase not in IR_DUMP_PHASES]
    if args.self_hosted:
        phases_to_run = [phase for phase in phases_to_run if phase in SELF_HOSTED_PHASES]
        if args.self_hosted_driver:
            driver_command = [str(Path(args.self_hosted_driver).resolve())]
        elif args.seed == "release":
            print(f"Compiling the self-hosted driver ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}), from the release:")
            driver_command = [str(build_seeded_driver(build_dir))]
        else:
            print(f"Compiling the self-hosted driver ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)})...")
            driver_command = [str(build_self_hosted_driver(python_executable, build_dir))]
        pending = self_hosted_pending()

    total_golden = 0
    passed_golden = 0
    skipped_golden = 0
    total_errors = 0
    passed_errors = 0

    print(f"Running tests with Python: {python_executable}")
    print(
        f"Suite: {suite_mode}, Phases: {', '.join(phases_to_run)}, "
        f"Timeout: {args.timeout}s, Workers: {jobs}"
    )
    print(f"Build dir: {build_dir}" + (f", Driver args: {' '.join(driver_args)}" if driver_args else "") + "\n")

    # Set up worker pool with isolated build directories
    worker_pool: queue.Queue[Path] = queue.Queue()
    for i in range(jobs):
        w_dir = build_dir if jobs == 1 else (build_dir / f"w{i}")
        w_dir.mkdir(parents=True, exist_ok=True)
        worker_pool.put(w_dir)

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        # 1. Run Golden Tests (if suite is 'golden' or 'all')
        if suite_mode in ("golden", "all"):
            source_files = discover_tests(TESTS_SOURCE_DIR) + discover_tests(EXAMPLES_DIR)
            if args.test:
                source_files = [sf for sf in source_files if args.test in str(golden_test_id(sf))]

            runs_eval = driver_command is not None and (not args.test or args.test in "self-hosted/eval")
            repl_files = [f for f in discover_repl_tests() if not args.test or args.test in f"repl/{f.stem}"]
            # The questlang tests' modules are compiled while the other phases
            # run, and the tests run compiled in the build directory this
            # leaves
            questlang_files = [
                sf for sf in source_files
                if is_questlang_test(sf) and "run_c_compiled" not in parse_skipped_phases(sf)
            ]
            questlang_build_dir = build_dir / (
                QUESTLANG_BUILD_SUBDIR if driver_command is None else QUESTLANG_SELF_HOSTED_BUILD_SUBDIR
            )
            questlang_build: Optional[threading.Thread] = None
            if "run_c_compiled" in phases_to_run and questlang_files:
                questlang_build = threading.Thread(
                    target=build_questlang_tests,
                    args=(python_executable, questlang_files, questlang_build_dir, driver_command),
                )
                questlang_build.start()
            if source_files or runs_eval or repl_files:
                print("=== Golden Tests ===")
                for phase in phases_to_run:
                    golden_dir = golden_dir_for_phase(phase, driver_command is not None)
                    if not golden_dir.exists():
                        continue
                    print(f"--- Phase: {phase} ---")
                    phase_tasks: list[PhaseTask] = []
                    # The REPL's transcripts, rather than the programs
                    for source_file in repl_files if phase == "repl" else []:
                        def make_repl_runner(sf: Path) -> Callable[[Path], tuple[bool, str, str]]:
                            return lambda w_dir: run_repl_test(
                                sf, args.update_golden, python_executable, args.timeout, w_dir, driver_command
                            )

                        test_id = f"repl/{source_file.stem}"
                        phase_tasks.append(PhaseTask(
                            test_id=test_id,
                            run_fn=with_pending(f"{phase}:{test_id}", pending, pending_counts,
                                                make_repl_runner(source_file)),
                        ))
                    if phase == "run_c_compiled" and questlang_build is not None:
                        questlang_build.join()
                    for source_file in source_files if phase != "repl" else []:
                        skipped_phases = parse_skipped_phases(source_file)
                        rel_source = golden_test_id(source_file)
                        test_id = str(rel_source.with_suffix(""))
                        if driver_command is None and is_questlang_test(source_file):
                            skipped_phases = skipped_phases | set(QUESTLANG_INTERPRETED_PHASES)
                        if phase.lower() in skipped_phases:
                            skipped_golden += 1
                            print(f"  [SKIP] {phase}:{test_id}")
                            continue
                        if phase in SUBSET_PHASES and not (golden_dir / rel_source.with_suffix(".out")).exists():
                            # Dumped for a subset of the programs only: those
                            # with goldens
                            continue
                        if phase == CODEGEN_PHASE and (
                            "run_c_compiled" in skipped_phases
                            or not (golden_dir_for_phase("run_c_compiled") / rel_source.with_suffix(".out")).exists()
                        ):
                            # The C of the programs run_c_compiled runs
                            continue

                        def make_golden_runner(
                            sf: Path, p: str
                        ) -> Callable[[Path], tuple[bool, str, str]]:
                            # Only run_c_compiled waits for the shared
                            # build; a phase before it would compile into
                            # the directory while the build writes it
                            shared = (
                                questlang_build_dir
                                if questlang_build is not None and p == "run_c_compiled" and sf in questlang_files
                                else None
                            )
                            return lambda w_dir: run_single_golden_test(
                                sf,
                                p,
                                update_golden=args.update_golden,
                                python_executable=python_executable,
                                timeout=args.timeout,
                                build_dir=shared or w_dir,
                                driver_args=driver_args,
                                driver_command=driver_command,
                            )

                        run_fn = with_pending(
                            f"{phase}:{test_id}", pending, pending_counts, make_golden_runner(source_file, phase)
                        )
                        phase_tasks.append(PhaseTask(test_id=test_id, run_fn=run_fn))

                    # The self-hosted driver's -e, against the bootstrap's
                    # transcript
                    if phase == "interpret" and runs_eval:
                        eval_command = driver_command
                        phase_tasks.append(PhaseTask(
                            test_id="self-hosted/eval",
                            run_fn=with_pending(
                                f"{phase}:self-hosted/eval", pending, pending_counts,
                                lambda w_dir: run_eval_test(eval_command, args.timeout),
                            ),
                        ))

                    if phase == CODEGEN_PHASE and driver_command is not None:
                        for check_id, script, script_args in UNIT_CHECKS:
                            if args.test and args.test not in check_id:
                                continue
                            phase_tasks.append(PhaseTask(
                                test_id=check_id,
                                run_fn=with_pending(
                                    f"{phase}:{check_id}", pending, pending_counts,
                                    lambda w_dir, s=script, a=script_args: run_unit_check(
                                        python_executable, s, a, driver_command[0]),
                                ),
                            ))

                    p_total, p_passed = run_phase_tasks(
                        phase, phase_tasks, worker_pool, executor, jobs
                    )
                    total_golden += p_total
                    passed_golden += p_passed
                print()

        # 2. Run Diagnostic Error Tests (if suite is 'errors' or 'all')
        if suite_mode in ("errors", "all"):
            error_phases_found = False
            for phase in phases_to_run:
                phase_error_dir = error_dir_for_phase(phase)
                if not phase_error_dir.exists():
                    if phase == "interpret" and (TESTS_ERRORS_DIR / "interpret").exists():
                        phase_error_dir = TESTS_ERRORS_DIR / "interpret"
                    else:
                        continue

                error_files = discover_tests(phase_error_dir)
                if args.test:
                    error_files = [
                        ef for ef in error_files
                        if args.test in str(ef.relative_to(TESTS_ERRORS_DIR))
                    ]
                if not error_files and not (driver_command is not None and (SELF_HOSTED_ERRORS_DIR / phase).exists()):
                    continue

                if not error_phases_found:
                    print("=== Diagnostic Error Tests ===")
                    error_phases_found = True

                print(f"--- Phase: {phase} ---")
                pipeline = pipeline_for_phase(phase)
                precursors = pipeline.precursors_of(phase)
                error_tasks: list[PhaseTask] = []
                for error_file in error_files:
                    skipped_phases = parse_skipped_phases(error_file)
                    rel_id = str(error_file.relative_to(phase_error_dir).with_suffix(""))
                    if phase.lower() in skipped_phases:
                        print(f"  [SKIP] {phase}:{rel_id}")
                        continue

                    directives = parse_test_directives(error_file)
                    golden_err_file = golden_error_file_for_test(error_file, phase)
                    effective_timeout = (
                        directives.timeout if directives.timeout is not None else args.timeout
                    )

                    def make_error_runner(
                        ef: Path,
                        p: str,
                        g_file: Path,
                        d: TestDirectives,
                        eff_timeout: float,
                        f_file: Optional[Path],
                    ) -> Callable[[Path], tuple[bool, str, str]]:
                        def runner(w_dir: Path) -> tuple[bool, str, str]:
                            passed, report = run_error_test(
                                source_file=ef,
                                target_phase=p,
                                precursor_phases=precursors,
                                python_executable=python_executable,
                                root_dir=ROOT_DIR,
                                golden_error_file=g_file,
                                update_golden=args.update_golden,
                                extra_args=d.args,
                                env_vars=d.env,
                                stdin_data=d.stdin_data,
                                timeout=eff_timeout,
                                build_dir=w_dir,
                                driver_args=driver_args,
                                driver_command=driver_command,
                                further_errors_file=f_file,
                            )
                            if passed:
                                status = "[UPDATED]" if report == "[UPDATED]" else "[PASS]"
                                return True, status, ""
                            return False, "[FAIL]", report

                        return runner

                    run_fn = with_pending(
                        f"errors/{phase}:{rel_id}",
                        pending,
                        pending_counts,
                        make_error_runner(
                            error_file,
                            phase,
                            golden_err_file,
                            directives,
                            effective_timeout,
                            SELF_HOSTED_ERRORS_GOLDEN_DIR / phase / Path(rel_id).with_suffix(".error")
                            if driver_command is not None
                            else None,
                        ),
                    )
                    error_tasks.append(PhaseTask(test_id=rel_id, run_fn=run_fn))

                # The self-hosted driver's tests of several errors, whose
                # diagnostics must all be expected
                multi_dir = SELF_HOSTED_ERRORS_DIR / phase
                if driver_command is not None and multi_dir.exists():
                    for multi_file in discover_tests(multi_dir):
                        multi_id = "self-hosted/" + str(multi_file.relative_to(multi_dir).with_suffix(""))
                        if args.test and args.test not in multi_id:
                            continue
                        multi_directives = parse_test_directives(multi_file)

                        def make_multi_runner(
                            mf: Path, p: str, d: TestDirectives, eff_timeout: float
                        ) -> Callable[[Path], tuple[bool, str, str]]:
                            def runner(w_dir: Path) -> tuple[bool, str, str]:
                                passed, report = run_error_test(
                                    source_file=mf,
                                    target_phase=p,
                                    precursor_phases=precursors,
                                    python_executable=python_executable,
                                    root_dir=ROOT_DIR,
                                    extra_args=d.args,
                                    env_vars=d.env,
                                    stdin_data=d.stdin_data,
                                    timeout=eff_timeout,
                                    build_dir=w_dir,
                                    driver_args=driver_args,
                                    driver_command=driver_command,
                                    all_errors=True,
                                )
                                return (True, "[PASS]", "") if passed else (False, "[FAIL]", report)

                            return runner

                        error_tasks.append(PhaseTask(
                            test_id=multi_id,
                            run_fn=make_multi_runner(
                                multi_file, phase, multi_directives,
                                multi_directives.timeout if multi_directives.timeout is not None else args.timeout,
                            ),
                        ))

                e_total, e_passed = run_phase_tasks(
                    phase, error_tasks, worker_pool, executor, jobs
                )
                total_errors += e_total
                passed_errors += e_passed

    # Summary report
    total_tests = total_golden + total_errors
    total_passed = passed_golden + passed_errors
    total_duration = time.perf_counter() - start_time

    skip_str = f" ({skipped_golden} skipped)" if skipped_golden > 0 else ""
    if pending_counts["pending"]:
        skip_str += f" ({pending_counts['pending']} pending)"
    print(f"\nSummary: {total_passed}/{total_tests} tests passed{skip_str}.")
    if suite_mode == "all":
        print(f"  Golden tests: {passed_golden}/{total_golden} passed{skip_str}")
        print(f"  Error tests:  {passed_errors}/{total_errors} passed")

    if total_passed == total_tests and total_tests > 0:
        record_telemetry(total_duration, total_tests, jobs)

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
