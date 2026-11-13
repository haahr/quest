"""Quest Bootstrap Compiler Test Runner.

Each test is a driver run of its own (quest_driver.py, in a subprocess), and so
a compilation session of its own, with its own unit graph and resolver
(docs/build-process.md §2.1): a test's builds never see another's resolutions or
typed units, only the artifacts in the worker's build directory, whose staleness
rules decide whether they are reused (docs/testing.md §2.2).

With --self-hosted, the tests of the phases the self-hosted compiler has run its
driver instead (questlang/driver/main, compiled to C first), against the
bootstrap's goldens and error expectations (docs/testing.md §2.3). With
--backend ssac too, its compiled tests compile every unit through the SSA's C
printer (docs/arm64.md §3.14); with ssac-program or ssac-modules, the program's
unit or its modules' alone, the rest through the C printer, so that the two
backends' units call each other both ways.
"""

import argparse
import concurrent.futures
import difflib
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

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
from quest.common.location import BYTE_ENCODING
from quest.testing.errors import run_error_test
from quest.testing.layout import (
    ROOT_DIR,
    TESTS_SOURCE_DIR,
    EXAMPLES_DIR,
    TESTS_GOLDEN_DIR,
    TESTS_ERRORS_DIR,
    DRIVER_SCRIPT,
    SELF_HOSTED_DRIVER,
)
from quest.testing.directives import (
    TestDirectives,
    parse_test_directives,
    parse_skipped_phases,
)
from quest.testing.selfhost import (
    STAGE_BACKENDS,
    build_seeded_driver,
    build_self_hosted_driver,
    check_self_hosting,
)
from quest.testing.transcripts import (
    discover_repl_tests,
    run_eval_test,
    run_repl_test,
    run_unit_check,
)


# The self-hosted compiler's phases, the tests it is not yet expected to pass,
# and where the errors it reports after the bootstrap's one are recorded
# (docs/testing.md §2.3)
#
# The IR stages only the self-hosted compiler has, after Core: the simplified
# stage (docs/ir.md section 8.6), dumped and run as the other stages are
SELF_HOSTED_IR_DUMP_PHASES = ("ir_simplified",)
SELF_HOSTED_IR_RUN_PHASES = ("run_ir_simplified",)
# The bootstrap's phases whose pipeline stands for theirs, to find the phases an
# error test runs before them
SELF_HOSTED_IR_STAND_INS = {"ir_simplified": "ir_core", "run_ir_simplified": "run_ir_core"}
SELF_HOSTED_PHASES = (
    "tokenize", "parse", "typecheck",
    IR_DUMP_PHASES[0], *SELF_HOSTED_IR_DUMP_PHASES, *IR_DUMP_PHASES[1:],
    IR_RUN_PHASES[0], *SELF_HOSTED_IR_RUN_PHASES, *IR_RUN_PHASES[1:],
    "ssa", "interpret", "run_c_compiled", "repl",
)
# The phases only the self-hosted compiler has: its own IR stages, and the SSA
# of its native backends (docs/ssa.md), dumped for every program that has an
# ir_core dump
SELF_HOSTED_ONLY_PHASES = (*SELF_HOSTED_IR_DUMP_PHASES, *SELF_HOSTED_IR_RUN_PHASES, "ssa")
# Where the self-hosted driver builds the units of the programs it compiles to
# C, under each worker's build directory: apart from the bootstrap's artifacts,
# which it would otherwise find fresh and reuse
SELF_HOSTED_UNITS_SUBDIR = "self-hosted-units"
# A statement's source position, at the end of a line of the self-hosted
# compiler's IR dumps (docs/ir.md section 10), which the bootstrap's lack
IR_POSITION = re.compile(r" @(?:(?:\d+:)?\d+:\d+|\+\d+)$", re.MULTILINE)
SELF_HOSTED_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending.txt"
# The self-hosted driver's options for each backend mode, and the tests the
# mode is not yet expected to pass, besides the self-hosted pending list's
BACKEND_MODES = {
    "ssac": ["--backend", "ssac"],
    "ssac-program": ["--backend", "c", "--unit-backend", "main=ssac"],
    "ssac-modules": ["--backend", "ssac", "--unit-backend", "main=c"],
    "arm64": ["--backend", "arm64"],
    "arm64-program": ["--backend", "c", "--unit-backend", "main=arm64"],
    "arm64-modules": ["--backend", "arm64", "--unit-backend", "main=c"],
    # A whole program, its modules merged into the program's unit (driver/whole,
    # docs/arm64.md section 3.12), through each backend
    "c-whole": ["--whole-program", "--backend", "c"],
    "ssac-whole": ["--whole-program", "--backend", "ssac"],
    "arm64-whole": ["--whole-program", "--backend", "arm64"],
    # The REPL's transcripts, their inputs compiled and run by the JIT, the
    # REPL's default (docs/jit.md section 5)
    "jit": [],
    # The run goldens' programs, each one input of the JIT
    "jit-files": ["--jit"],
}
SSAC_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending-ssac.txt"
ARM64_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending-arm64.txt"
WHOLE_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending-whole.txt"
JIT_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending-jit.txt"
BACKEND_PENDING = {mode: WHOLE_PENDING if mode.endswith("-whole") else SSAC_PENDING if mode.startswith("ssac")
                   else JIT_PENDING if mode.startswith("jit") else ARM64_PENDING for mode in BACKEND_MODES}
# The phases that compile a program, which a backend's mode runs; the jit mode
# runs the REPL's transcripts, but those marked @skip-phase: jit, which show a
# difference the JIT is allowed (docs/jit.md section 4)
BACKEND_PHASES = ("run_c_compiled",)
JIT_PHASES = ("repl",)
JIT_FILE_PHASES = ("interpret",)
SELF_HOSTED_ERRORS_GOLDEN_DIR = TESTS_GOLDEN_DIR / "self-hosted" / "errors"
# The checks of the self-hosted driver's unit files (-c): interfaces against its
# ABI corpus (tests/abi/corpus-self-hosted), and that lib/'s modules compile;
# and of the errors its builds report, against the bootstrap's; that its
# parallel builds (-j) are its serial ones; that its compile command does
# what the bootstrap's does; that lldb reads the arm64 backend's line tables;
# that its kernel mode serves a Jupyter kernel's requests; and that the kernel
# serves a notebook's
UNIT_CHECKS = (
    ("self-hosted/abi_corpus", ROOT_DIR / "tests" / "abi" / "corpus.py", ("--compiler",)),
    ("self-hosted/unit_artifacts", ROOT_DIR / "tests" / "self-hosted" / "unit_artifacts.py", ()),
    ("self-hosted/build_errors", ROOT_DIR / "tests" / "self-hosted" / "build_errors.py", ()),
    ("self-hosted/parallel_build", ROOT_DIR / "tests" / "self-hosted" / "parallel_build.py", ()),
    ("self-hosted/compile_command", ROOT_DIR / "tests" / "self-hosted" / "compile_command.py", ()),
    ("self-hosted/backends", ROOT_DIR / "tests" / "self-hosted" / "backends.py", ()),
    ("self-hosted/line_tables", ROOT_DIR / "tests" / "self-hosted" / "line_tables.py", ()),
    ("self-hosted/fingerprints", ROOT_DIR / "tests" / "self-hosted" / "fingerprints.py", ()),
    ("self-hosted/encoder", ROOT_DIR / "tests" / "self-hosted" / "encoder.py", ()),
    ("self-hosted/jit_hosts", ROOT_DIR / "tests" / "self-hosted" / "jit_hosts.py", ()),
    ("self-hosted/kernel_protocol", ROOT_DIR / "tests" / "self-hosted" / "kernel_protocol.py", ()),
    ("self-hosted/jupyter_kernel", ROOT_DIR / "tests" / "self-hosted" / "jupyter_kernel.py", ()),
)
# Tests of several errors, which only the self-hosted driver reports:
# tests/self-hosted/errors/PHASE/NAME.quest
SELF_HOSTED_ERRORS_DIR = ROOT_DIR / "tests" / "self-hosted" / "errors"
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
SUBSET_PHASES = (*SELF_HOSTED_IR_DUMP_PHASES, *IR_DUMP_PHASES[1:])

# The phases that run programs, whose output is compared with the run goldens
RUN_PHASES = ("interpret", "run_c_compiled", *IR_RUN_PHASES, *SELF_HOSTED_IR_RUN_PHASES)

# The goldens of how a compiler compiles, rather than of what programs do, are
# the self-hosted compiler's own (docs/testing.md section 2.8): the IR dumps.
# The other phases' goldens are shared: both compilers must match them, and the
# bootstrap writes them, since what programs do changes in both. The C itself
# has no goldens; tools/c-diff shows how a change alters it.
SELF_HOSTED_OWN_PHASES = (*IR_DUMP_PHASES, *SELF_HOSTED_IR_DUMP_PHASES, "ssa")


def writes_golden(phase_name: str, self_hosted: bool) -> bool:
    """Whether --update-golden with the self-hosted compiler (or with the
    bootstrap) writes a phase's goldens."""
    if self_hosted:
        return phase_name in SELF_HOSTED_OWN_PHASES
    return phase_name not in IR_DUMP_PHASES and phase_name not in SELF_HOSTED_ONLY_PHASES


# The tests of the self-hosted compiler's modules run compiled only: under the
# bootstrap's interpreters, each would interpret the compiler's code for minutes.
# Their modules are compiled once per run, into a build directory the tests
# share (build_questlang_tests).
QUESTLANG_TESTS_DIR = TESTS_SOURCE_DIR / "questlang"
QUESTLANG_INTERPRETED_PHASES = ("interpret", *IR_RUN_PHASES, *SELF_HOSTED_IR_RUN_PHASES)
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


def golden_dir_for_phase(phase_name: str) -> Path:
    if phase_name in RUN_PHASES:
        return TESTS_GOLDEN_DIR / "run"
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
    phase_name = SELF_HOSTED_IR_STAND_INS.get(phase_name, phase_name)
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
    golden_base = golden_dir_for_phase(phase_name)
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
        if phase_name == "run_c_compiled" and build_dir is not None:
            command.extend(["--build-dir", str(self_hosted_units_dir(build_dir))])
        if driver_args:
            command.extend(driver_args)
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
    if directives.echo and phase_name in RUN_PHASES:
        command.append("--echo")

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

    output = process.stdout
    if phase_name == "ssa":
        # The SSA's raise sites name the program by the path it was given,
        # which is absolute, since the test runs in a scratch directory; the
        # golden names it relative to the checkout, so that it holds in any
        output = output.replace(str(ROOT_DIR) + os.sep, "")
    if update_golden and writes_golden(phase_name, driver_command is not None):
        out_file.write_text(output, encoding=BYTE_ENCODING)
        return True, "[UPDATED]", ""

    if not out_file.exists():
        return False, "[MISSING GOLDEN]", f"  (expected {out_file.relative_to(ROOT_DIR)})"

    expected_output = out_file.read_text(encoding=BYTE_ENCODING)
    if driver_command is None and phase_name in IR_DUMP_PHASES:
        # The IR goldens are the self-hosted compiler's (§2.8)
        expected_output = IR_POSITION.sub("", expected_output)
    if output == expected_output:
        return True, "[PASS]", ""

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


def self_hosted_pending(path: Path = SELF_HOSTED_PENDING) -> set[str]:
    """The tests the self-hosted driver is not yet expected to pass: PHASE:TEST
    for a golden test, and errors/PHASE:TEST for an error test, one per line (#
    starts a comment)."""
    if not path.exists():
        return set()
    entries = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
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
            return False, "[FAIL]", f"  (passes, but is pending: remove '{key}' from its pending list)"
        counts["pending"] += 1
        return True, "[PENDING]", ""

    return run


def main() -> int:
    """The test runner's command line (run_tests.py): runs the tests the
    options select and returns the exit status, run_all_tests's (0 if every
    test passed or is pending). docs/testing.md §2.3 describes the options.

    C phases build in --build-dir, or else in a fresh temporary directory,
    removed at the end, so that results never depend on artifacts an earlier
    compiler wrote. --backend may name several modes, separated by commas,
    which needs --self-hosted or --self-hosting: one self-hosted driver then
    serves every mode (with --self-hosting, the stage 2 that the fixed-point
    check, run once, built; else --self-hosted-driver or one compiled here),
    and each mode's tests run in turn, the status the worst of theirs."""
    available_phases = [
        "tokenize",
        "parse",
        "typecheck",
        IR_DUMP_PHASES[0],
        *SELF_HOSTED_IR_DUMP_PHASES,
        *IR_DUMP_PHASES[1:],
        IR_RUN_PHASES[0],
        *SELF_HOSTED_IR_RUN_PHASES,
        *IR_RUN_PHASES[1:],
        "ssa",
        "interpret",
        "run_c_compiled",
        "repl",
    ]

    arg_parser = argparse.ArgumentParser(description="Run Quest compiler tests (golden outputs and error suites).")
    arg_parser.add_argument(
        "--phase", choices=available_phases + ["all"], default="all", help="Compiler phase to test."
    )
    arg_parser.add_argument(
        "--skip-phase",
        choices=available_phases,
        action="append",
        default=[],
        help="A phase not to test, though --phase would; repeated for several (tools/check skips the IR runs "
        "between Core and the described stage, docs/testing.md section 4.1).",
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
        "--backend",
        default="c",
        help="With --self-hosted, compile the compiled tests' units with this backend (docs/arm64.md §3.12): "
        "ssac compiles every unit through the SSA's C printer, ssac-program the program's alone, and ssac-modules "
        "the modules' alone. Each runs only the phases that compile, with its own pending list too. Several, "
        "separated by commas, run one after another with one driver.",
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
        "--stage-backend",
        choices=list(STAGE_BACKENDS),
        default="c",
        help="With --self-hosting, build stages 2 and 3 through this backend, so that the fixed point is the "
        "compiler as the backend compiles it (docs/arm64.md section 3.12).",
    )
    arg_parser.add_argument(
        "--whole-program-fixed-point",
        action="store_true",
        help="With --self-hosting, also check the whole-program fixed point through the stage backend: stage 2's "
        "whole-program build must write the whole program's code stage 2 writes (docs/testing.md section 2.3).",
    )
    arg_parser.add_argument(
        "--fixed-point-only",
        action="store_true",
        help="With --self-hosting, check the fixed point and stop, without running the suite with stage 2.",
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
    backends = args.backend.split(",")
    for backend in backends:
        if backend != "c" and backend not in BACKEND_MODES:
            arg_parser.error(f"--backend: {backend!r} is not one of c, {', '.join(BACKEND_MODES)}")
    try:
        if len(backends) == 1:
            return run_all_tests(args, available_phases, build_dir, [], jobs=jobs)
        if not (args.self_hosted or args.self_hosting):
            arg_parser.error("several backends need --self-hosted or --self-hosting")
        # One driver for every backend's run: with --self-hosting, the
        # self-hosting check's stage 2, checked once rather than once a backend
        python_executable = args.python if os.path.exists(args.python) else sys.executable
        if args.self_hosting:
            args.self_hosted = True
            args.self_hosted_driver = str(check_self_hosting(python_executable, build_dir, args.seed, args.stage_backend,
                                                             args.whole_program_fixed_point))
            args.self_hosting = False
            if args.fixed_point_only:
                return 0
        elif not args.self_hosted_driver:
            print(f"Compiling the self-hosted driver ({SELF_HOSTED_DRIVER.relative_to(ROOT_DIR)}) for the backends:")
            args.self_hosted_driver = str(build_seeded_driver(build_dir) if args.seed == "release"
                                          else build_self_hosted_driver(python_executable, build_dir))
        status = 0
        for backend in backends:
            print(f"\n=== Backend: {backend} ===")
            args.backend = backend
            status = max(status, run_all_tests(args, available_phases, build_dir, [], jobs=jobs))
        return status
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
    """Runs the golden and error tests the parsed command line args select,
    in build_dir with jobs workers, printing a line per test and a summary.
    Returns 0 if every test run passed (or is pending), 1 if any failed, and 2
    for --backend without --self-hosted. main calls it once per --backend mode,
    with a fresh driver_args, which it extends with the mode's options; with
    several modes and --self-hosting, main runs the self-hosting check once,
    first, and each mode's tests with its stage 2.
    docs/testing.md §2.3 describes the runner and its modes.

    The phases are --phase's, or all of available_phases, narrowed to the
    compiler under test:

    - The bootstrap's driver (the default) runs neither the SSA nor the
      self-hosted compiler's own IR stages, and without --phase, none of the
      IR dumps either, whose goldens are the self-hosted compiler's (§2.8).
    - --self-hosted runs the self-hosted driver, compiled here (with the
      bootstrap, or with the release under --seed release) unless
      --self-hosted-driver names one, on the phases it has
      (SELF_HOSTED_PHASES). --self-hosting first checks the self-hosted
      compiler's fixed point (check_self_hosting, which exits if it fails)
      and then runs that suite with stage 2; with --fixed-point-only it
      returns 0 after the check.
    - --backend MODE, other than c, needs --self-hosted: it passes the mode's
      options to the driver (BACKEND_MODES) and keeps only the mode's phases,
      run_c_compiled for the ssac, arm64 and whole-program modes, repl for
      jit, and interpret for jit-files.

    --skip-phase then removes phases, and --test keeps only the tests whose
    id contains its text. The golden suite runs phase by phase, each phase's
    tests in parallel, then the error suite does the same (--suite and
    --errors choose the suites).

    Each worker has a build directory of its own (w0, w1, ... under
    build_dir; build_dir itself with one worker), which a test borrows from
    worker_pool while it runs, so concurrent tests never write the same
    artifacts. The questlang tests are the exception: one background thread
    compiles them all into a shared directory while the earlier phases run,
    and their run_c_compiled tests wait for it and run there.

    With the self-hosted driver, the tests in tests/self-hosted/pending.txt,
    and in the backend mode's own pending list, are not yet expected to pass
    (with_pending): a failure counts as a pass reported as [PENDING], and a
    pass is a failure, so that the entry is removed.
    """
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
        args.self_hosted_driver = str(check_self_hosting(python_executable, build_dir, args.seed, args.stage_backend,
                                                         args.whole_program_fixed_point))
        if args.fixed_point_only:
            return 0
    if not args.self_hosted and args.phase == "all":
        # The IR dumps are the self-hosted compiler's; --phase runs one with the
        # bootstrap, to compare its IR with them
        phases_to_run = [phase for phase in phases_to_run if phase not in IR_DUMP_PHASES]
    if not args.self_hosted:
        # The bootstrap has no SSA
        phases_to_run = [phase for phase in phases_to_run if phase not in SELF_HOSTED_ONLY_PHASES]
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
        if args.backend != "c":
            mode_phases = {"jit": JIT_PHASES, "jit-files": JIT_FILE_PHASES}.get(args.backend, BACKEND_PHASES)
            phases_to_run = [phase for phase in phases_to_run if phase in mode_phases]
            driver_args.extend(BACKEND_MODES[args.backend])
            pending |= self_hosted_pending(BACKEND_PENDING[args.backend])
        else:
            # The C backend's goldens and runs, named, since the driver's own
            # default is arm64
            driver_args.extend(["--backend", "c"])
    elif args.backend != "c":
        print("--backend needs --self-hosted", file=sys.stderr)
        return 2
    phases_to_run = [phase for phase in phases_to_run if phase not in args.skip_phase]

    # Counts for the summary, by suite
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
                    # With the backend mode's options, so that the tests,
                    # which run at once, find the shared modules up to date
                    args=(python_executable, questlang_files, questlang_build_dir,
                          [*driver_command, *driver_args] if driver_command else None),
                )
                questlang_build.start()
            if source_files or runs_eval or repl_files:
                print("=== Golden Tests ===")
                for phase in phases_to_run:
                    golden_dir = golden_dir_for_phase(phase)
                    if not golden_dir.exists():
                        continue
                    print(f"--- Phase: {phase} ---")
                    phase_tasks: list[PhaseTask] = []
                    # The REPL's transcripts, rather than the programs
                    for source_file in repl_files if phase == "repl" else []:
                        test_id = f"repl/{source_file.stem}"
                        if args.backend == "jit" and "jit" in parse_skipped_phases(source_file):
                            skipped_golden += 1
                            print(f"  [SKIP] {phase}:{test_id}")
                            continue
                        # The self-hosted driver's REPL runs on the JIT by
                        # default; the repl phase checks its interpreter, the
                        # jit mode its JIT
                        repl_command = None if driver_command is None else [
                            *driver_command, *driver_args, *([] if args.backend == "jit" else ["--no-jit"])]

                        def make_repl_runner(sf: Path, command: Optional[list[str]]
                                             ) -> Callable[[Path], tuple[bool, str, str]]:
                            return lambda w_dir: run_repl_test(
                                sf, args.update_golden, python_executable, args.timeout, w_dir, command
                            )

                        phase_tasks.append(PhaseTask(
                            test_id=test_id,
                            run_fn=with_pending(f"{phase}:{test_id}", pending, pending_counts,
                                                make_repl_runner(source_file, repl_command)),
                        ))
                    if phase == "run_c_compiled" and questlang_build is not None:
                        questlang_build.join()
                    for source_file in source_files if phase != "repl" else []:
                        skipped_phases = parse_skipped_phases(source_file)
                        rel_source = golden_test_id(source_file)
                        test_id = str(rel_source.with_suffix(""))
                        if driver_command is None and is_questlang_test(source_file):
                            skipped_phases = skipped_phases | set(QUESTLANG_INTERPRETED_PHASES)
                        if phase in ("ssa", *SELF_HOSTED_IR_DUMP_PHASES) and "ir_core" in skipped_phases:
                            # The SSA is dumped for the programs whose IR is
                            skipped_phases = skipped_phases | {phase}
                        if args.backend == "jit-files" and skipped_phases & {"jit", "run_c_compiled"}:
                            # A difference the JIT is allowed, or one compiled
                            # code shows, which the JIT does too (docs/jit.md
                            # section 4)
                            skipped_phases = skipped_phases | {phase}
                        if phase.lower() in skipped_phases:
                            skipped_golden += 1
                            print(f"  [SKIP] {phase}:{test_id}")
                            continue
                        if phase in SUBSET_PHASES and not (golden_dir / rel_source.with_suffix(".out")).exists():
                            # Dumped for a subset of the programs only: those
                            # with goldens
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
                    # transcript: its interpreter, and in the jit-files mode
                    # its JIT, -e's default
                    if phase == "interpret" and runs_eval:
                        eval_jit = args.backend == "jit-files"
                        eval_command = [*driver_command, *([] if eval_jit else ["--no-jit"])]
                        phase_tasks.append(PhaseTask(
                            test_id="self-hosted/eval",
                            run_fn=with_pending(
                                f"{phase}:self-hosted/eval", pending, pending_counts,
                                lambda w_dir: run_eval_test(eval_command, args.timeout),
                            ),
                        ))

                    # (The checks run the driver themselves, with its own options)
                    if phase == "run_c_compiled" and driver_command is not None and args.backend == "c":
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

                    # The phase's tests, all queued, run on the workers
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
                precursors = pipeline.precursors_of(SELF_HOSTED_IR_STAND_INS.get(phase, phase))
                error_tasks: list[PhaseTask] = []
                for error_file in error_files:
                    skipped_phases = parse_skipped_phases(error_file)
                    rel_id = str(error_file.relative_to(phase_error_dir).with_suffix(""))
                    if args.backend == "jit-files" and skipped_phases & {"jit", "run_c_compiled"}:
                        skipped_phases = skipped_phases | {phase}
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
                            run_fn=with_pending(
                                f"errors/{phase}:{multi_id}",
                                pending,
                                pending_counts,
                                make_multi_runner(
                                    multi_file, phase, multi_directives,
                                    multi_directives.timeout if multi_directives.timeout is not None else args.timeout,
                                ),
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
