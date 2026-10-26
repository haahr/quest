"""Quest Bootstrap Compiler Test Runner.

Each test is a driver run of its own (quest_driver.py, in a subprocess), and so a compilation session of its own,
with its own unit graph and resolver (docs/build-process.md §2.1): a test's builds never see another's resolutions
or typed units, only the artifacts in the worker's build directory, whose staleness rules decide whether they are
reused (docs/testing.md §2.2).

With --self-hosted, the tests of the phases the self-hosted compiler has run its driver instead (questlang/driver/main,
compiled to C first), against the bootstrap's goldens and error expectations (docs/milestone-2.md §3).
"""

import argparse
import concurrent.futures
import difflib
import os
import queue
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
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
from quest.testing.errors import run_error_test

TESTS_SOURCE_DIR = ROOT_DIR / "tests" / "source"
# The example programs the documentation walks through, run as golden tests too (docs/testing.md §2.1)
EXAMPLES_DIR = ROOT_DIR / "examples"
TESTS_GOLDEN_DIR = ROOT_DIR / "tests" / "golden"
TESTS_ERRORS_DIR = ROOT_DIR / "tests" / "errors"
DRIVER_SCRIPT = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"

# The self-hosted compiler's driver, the phases it has, the tests it is not yet expected to pass, and where the
# errors it reports after the bootstrap's one are recorded (docs/milestone-2.md §3)
SELF_HOSTED_DRIVER = ROOT_DIR / "questlang" / "driver" / "main.quest"
SELF_HOSTED_PHASES = ("tokenize", "parse", "typecheck", "interpret")
SELF_HOSTED_PENDING = ROOT_DIR / "tests" / "self-hosted" / "pending.txt"
SELF_HOSTED_ERRORS_GOLDEN_DIR = TESTS_GOLDEN_DIR / "self-hosted" / "errors"
# Tests of several errors, which only the self-hosted driver reports: tests/self-hosted/errors/PHASE/NAME.quest
# The programs the self-hosted driver's -e runs, and the bootstrap's transcript of them (docs/milestone-3.md §3.2),
# which tests/eval/generate.py writes
EVAL_CASES = ROOT_DIR / "tests" / "eval" / "cases.quest"
EVAL_GOLDEN = TESTS_GOLDEN_DIR / "self-hosted" / "eval.out"
SELF_HOSTED_ERRORS_DIR = ROOT_DIR / "tests" / "self-hosted" / "errors"
TELEMETRY_LOG_PATH = Path("/tmp/quest_run_tests_telemetry.log")


def record_telemetry(total_duration: float, tests_run: int, workers_used: int) -> None:
    """Appends execution telemetry to /tmp/quest_run_tests_telemetry.log on successful test runs."""
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
    """Text from a test's source, a character per byte, as a string that subprocess gives the OS as those bytes."""
    return os.fsdecode(text.encode(BYTE_ENCODING))


def parse_test_directives(source_file: Path) -> TestDirectives:
    """Extracts test directives (@skip-phase, @args, @env, @exit, @timeout, @stdin, @echo) from comments."""
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
    """Returns the test programs under directory: every .quest file holding a program. Interfaces and modules beside
    the tests are imported by them, not run as tests (docs/testing.md §2.6)."""
    return sorted(p for p in directory.rglob("*.quest") if file_unit_kind(p) == UnitKind.PROGRAM)


def golden_test_id(source_file: Path) -> Path:
    """The path of a golden test's program relative to its goldens' directories: its path within tests/source, or
    within examples/ under examples/."""
    try:
        return source_file.relative_to(TESTS_SOURCE_DIR)
    except ValueError:
        return Path("examples") / source_file.relative_to(EXAMPLES_DIR)


# The IR's stages after Core are dumped (and compared with goldens) for a subset of the programs, chosen to exercise
# each pass: those that have a golden in the stage's directory. (Every program runs through every stage, verified, in
# the run_ir phases.) To add a program to a stage's subset, create its golden file empty and update goldens.
SUBSET_PHASES = IR_DUMP_PHASES[1:]

# The phases that run programs, whose output is compared with the run goldens
RUN_PHASES = ("interpret", "run_c_compiled", *IR_RUN_PHASES)


def golden_dir_for_phase(phase_name: str) -> Path:
    if phase_name in RUN_PHASES:
        return TESTS_GOLDEN_DIR / "run"
    return TESTS_GOLDEN_DIR / phase_name


def error_dir_for_phase(phase_name: str) -> Path:
    # Every phase that runs programs locates run-time errors at their raise sites (docs/exceptions.md §3)
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
    """Runs a golden test with the bootstrap driver, or the one driver_command runs (the self-hosted driver, whose
    output is compared with the bootstrap's goldens and never written to them)."""
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
    else:
        command = [
            python_executable,
            str(DRIVER_SCRIPT),
            "--stop-after",
            phase_name,
        ]
        if driver_args:
            command.extend(driver_args)
        # Every phase builds and reuses artifacts in the build directory (docs/build-process.md §5.2.4).
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

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    # Checks the C back end's canonical forms of types, which outside the tests only warn
    # (docs/c-representation.md §5.7)
    environment["QUEST_CHECK_CANONICAL"] = "1"
    # Checks that typed programs are well scoped (quest/typechecker/scoping.py)
    environment["QUEST_CHECK_SCOPES"] = "1"
    # Checks the IR's invariants after lowering (quest/ir/verify.py)
    environment["QUEST_CHECK_IR"] = "1"
    # The project directory, whose lib/ the self-hosted driver reads the standard library from (it runs elsewhere)
    environment["QUEST_HOME"] = str(ROOT_DIR)
    if directives.env and phase_name in RUN_PHASES:
        environment.update(directives.env)

    try:
        # Each run starts in a fresh, empty directory of its own, where the program may create files
        # (docs/testing.md §2.2)
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

    # A golden test is a valid program: one that exits with any other code fails, even when updating goldens.
    # Programs that should be rejected are error tests (docs/testing.md §3).
    if process.returncode != expected_exit:
        msg = f"  (failed with returncode {process.returncode}, expected {expected_exit})"
        if process.stderr:
            msg += f"\n{process.stderr.rstrip()}"
        return False, "[FAIL]", msg

    if update_golden and driver_command is None:
        out_file.write_text(process.stdout, encoding=BYTE_ENCODING)
        return True, "[UPDATED]", ""

    if not out_file.exists():
        return False, "[MISSING GOLDEN]", f"  (expected {out_file.relative_to(ROOT_DIR)})"

    expected_output = out_file.read_text(encoding=BYTE_ENCODING)
    if process.stdout == expected_output:
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
    """Executes a list of tasks for a given phase using the worker pool, printing results."""
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
    """Compiles the self-hosted driver to an executable in build_dir, with the bootstrap."""
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


def eval_programs() -> list[str]:
    """The programs of tests/eval/cases.quest, one per line, after its opening comment."""
    lines = EVAL_CASES.read_text(encoding=BYTE_ENCODING).splitlines()
    end = next(i for i, line in enumerate(lines) if line.rstrip().endswith("*)"))
    return [line for line in lines[end + 1:] if line.strip()]


def eval_transcript(driver_command: list[str], timeout: float = 30.0) -> str:
    """What a driver writes for each program of eval_programs run with -e: its standard output and error, and its
    exit status, each run in a fresh directory of its own."""
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
    """The self-hosted driver's -e against the bootstrap's transcript (eval_transcript)."""
    actual = eval_transcript(driver_command, timeout)
    expected = EVAL_GOLDEN.read_text(encoding=BYTE_ENCODING)
    if actual == expected:
        return True, "[PASS]", ""
    diff = difflib.unified_diff(
        expected.splitlines(keepends=True), actual.splitlines(keepends=True),
        fromfile="golden/self-hosted/eval.out", tofile="actual/self-hosted/eval.out",
    )
    return False, "[FAIL]", "  (transcript mismatch)\n" + "".join(diff).rstrip()


def self_hosted_pending() -> set[str]:
    """The tests the self-hosted driver is not yet expected to pass: PHASE:TEST for a golden test, and
    errors/PHASE:TEST for an error test, one per line (# starts a comment)."""
    if not SELF_HOSTED_PENDING.exists():
        return set()
    entries = (line.split("#", 1)[0].strip() for line in SELF_HOSTED_PENDING.read_text(encoding="utf-8").splitlines())
    return {entry for entry in entries if entry}


def with_pending(
    key: str, pending: set[str], counts: dict[str, int], run_fn: Callable[[Path], tuple[bool, str, str]]
) -> Callable[[Path], tuple[bool, str, str]]:
    """run_fn, for a test that may be pending: a pending test that fails is reported as pending, and one that passes
    fails, so that it is taken off the list."""
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
        "run_c_compiled",
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
        "against the bootstrap's goldens.",
    )
    arg_parser.add_argument(
        "--self-hosted-driver",
        metavar="PATH",
        help="With --self-hosted, run this compiled self-hosted driver rather than compiling one.",
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
    if args.self_hosted:
        phases_to_run = [phase for phase in phases_to_run if phase in SELF_HOSTED_PHASES]
        if args.self_hosted_driver:
            driver_command = [str(Path(args.self_hosted_driver).resolve())]
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
            if source_files or runs_eval:
                print("=== Golden Tests ===")
                for phase in phases_to_run:
                    golden_dir = golden_dir_for_phase(phase)
                    if not golden_dir.exists():
                        continue
                    print(f"--- Phase: {phase} ---")
                    phase_tasks: list[PhaseTask] = []
                    for source_file in source_files:
                        skipped_phases = parse_skipped_phases(source_file)
                        rel_source = golden_test_id(source_file)
                        test_id = str(rel_source.with_suffix(""))
                        if phase.lower() in skipped_phases:
                            skipped_golden += 1
                            print(f"  [SKIP] {phase}:{test_id}")
                            continue
                        if phase in SUBSET_PHASES and not (golden_dir / rel_source.with_suffix(".out")).exists():
                            # Dumped for a subset of the programs only: those with goldens
                            continue

                        def make_golden_runner(
                            sf: Path, p: str
                        ) -> Callable[[Path], tuple[bool, str, str]]:
                            return lambda w_dir: run_single_golden_test(
                                sf,
                                p,
                                update_golden=args.update_golden,
                                python_executable=python_executable,
                                timeout=args.timeout,
                                build_dir=w_dir,
                                driver_args=driver_args,
                                driver_command=driver_command,
                            )

                        run_fn = with_pending(
                            f"{phase}:{test_id}", pending, pending_counts, make_golden_runner(source_file, phase)
                        )
                        phase_tasks.append(PhaseTask(test_id=test_id, run_fn=run_fn))

                    # The self-hosted driver's -e, against the bootstrap's transcript
                    if phase == "interpret" and runs_eval:
                        eval_command = driver_command
                        phase_tasks.append(PhaseTask(
                            test_id="self-hosted/eval",
                            run_fn=with_pending(
                                f"{phase}:self-hosted/eval", pending, pending_counts,
                                lambda w_dir: run_eval_test(eval_command, args.timeout),
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

                # The self-hosted driver's tests of several errors, whose diagnostics must all be expected
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
