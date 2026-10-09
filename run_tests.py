"""Quest Bootstrap Compiler Test Runner."""

import argparse
import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ensure bootstrap/python is importable
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))

from quest.error_testing import run_error_test
from quest.pipeline import PhasePipeline, default_pipeline, full_pipeline

TESTS_SOURCE_DIR = ROOT_DIR / "tests" / "source"
TESTS_GOLDEN_DIR = ROOT_DIR / "tests" / "golden"
TESTS_ERRORS_DIR = ROOT_DIR / "tests" / "errors"
DRIVER_SCRIPT = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"

# Interfaces and modules beside the tests are imported by them, not run as tests (docs/testing.md §2.6).
UNIT_SUFFIXES = (".int.quest", ".mod.quest")

SKIP_PHASE_PATTERN = re.compile(r"\(\*\s*@skip-phase:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
ARGS_PATTERN = re.compile(r"\(\*\s*@args:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
ENV_PATTERN = re.compile(r"\(\*\s*@env:\s*([^*]+?)\s*\*\)", re.IGNORECASE)
EXIT_PATTERN = re.compile(r"\(\*\s*@exit:\s*([0-9]+)\s*\*\)", re.IGNORECASE)
TIMEOUT_PATTERN = re.compile(r"\(\*\s*@timeout:\s*([0-9.]+)\s*\*\)", re.IGNORECASE)
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


def parse_test_directives(source_file: Path) -> TestDirectives:
    """Extracts test directives (@skip-phase, @args, @env, @exit, @timeout, @stdin) from comments."""
    text = source_file.read_text(encoding="utf-8")

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
            args.extend(shlex.split(raw_args))

    env: dict[str, str] = {}
    for match in ENV_PATTERN.finditer(text):
        raw_env = match.group(1).strip()
        if raw_env:
            for item in shlex.split(raw_env):
                if "=" in item:
                    k, v = item.split("=", 1)
                    env[k] = v
                else:
                    env[item] = ""

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
    )


def parse_skipped_phases(source_file: Path) -> set[str]:
    """Extracts skipped phase names from (* @skip-phase: ... *) comments."""
    return parse_test_directives(source_file).skipped_phases


def discover_tests(directory: Path) -> list[Path]:
    """Returns the test programs under directory: every .quest file except interfaces and modules."""
    return sorted(p for p in directory.rglob("*.quest") if not p.name.endswith(UNIT_SUFFIXES))


def golden_dir_for_phase(phase_name: str) -> Path:
    if phase_name in ("interpret", "run_c_compiled"):
        return TESTS_GOLDEN_DIR / "run"
    return TESTS_GOLDEN_DIR / phase_name


def error_dir_for_phase(phase_name: str) -> Path:
    if phase_name in ("interpret", "run_c_compiled"):
        return TESTS_ERRORS_DIR / "run"
    return TESTS_ERRORS_DIR / phase_name


def golden_error_file_for_test(source_file: Path, phase_name: str) -> Path:
    phase_folder = "run" if phase_name in ("interpret", "run_c_compiled") else phase_name
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
    return default_pipeline()


def run_single_golden_test(
    source_file: Path,
    phase_name: str,
    update_golden: bool = False,
    python_executable: str = sys.executable,
    timeout: float = 30.0,
    build_dir: Optional[Path] = None,
    driver_args: Optional[list[str]] = None,
) -> bool:
    golden_base = golden_dir_for_phase(phase_name)
    rel_source = source_file.relative_to(TESTS_SOURCE_DIR)
    target_dir = golden_base / rel_source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    out_file = target_dir / f"{source_file.stem}.out"
    error_file = target_dir / f"{source_file.stem}.error"
    test_id = str(rel_source.with_suffix(""))

    directives = parse_test_directives(source_file)
    expected_exit = directives.exit_code if phase_name in ("interpret", "run_c_compiled") else 0
    effective_timeout = directives.timeout if directives.timeout is not None else timeout

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

    command.append(str(source_file))

    if directives.args and phase_name in ("interpret", "run_c_compiled"):
        command.append("--")
        command.extend(directives.args)

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
    if directives.env and phase_name in ("interpret", "run_c_compiled"):
        environment.update(directives.env)

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            input=directives.stdin_data if phase_name in ("interpret", "run_c_compiled") else None,
            env=environment,
            timeout=effective_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"  [FAIL] {phase_name}:{test_id} (TIMED OUT after {effective_timeout:.1f}s)")
        stderr = exc.stderr if isinstance(exc.stderr, str) else (
            exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        )
        if stderr:
            for line in stderr.strip().splitlines()[:15]:
                print(f"    {line}")
        return False

    if update_golden:
        if process.returncode == expected_exit:
            out_file.write_text(process.stdout, encoding="utf-8")
            if error_file.exists():
                error_file.unlink()
            print(f"  [UPDATED] {phase_name}:{test_id} (.out)")
        else:
            error_file.write_text(process.stderr, encoding="utf-8")
            if out_file.exists():
                out_file.unlink()
            print(f"  [UPDATED] {phase_name}:{test_id} (.error)")
        return True

    # Case 1: Process exit code matches expected_exit
    if process.returncode == expected_exit:
        if out_file.exists():
            expected_output = out_file.read_text(encoding="utf-8")
            if process.stdout == expected_output:
                print(f"  [PASS] {phase_name}:{test_id}")
                return True
            else:
                print(f"  [FAIL] {phase_name}:{test_id} (stdout mismatch)")
                diff = difflib.unified_diff(
                    expected_output.splitlines(keepends=True),
                    process.stdout.splitlines(keepends=True),
                    fromfile=f"golden/{golden_base.name}/{rel_source.with_suffix('.out')}",
                    tofile=f"actual/{golden_base.name}/{rel_source.with_suffix('.out')}",
                )
                print("".join(diff))
                return False
        elif error_file.exists():
            print(
                f"  [FAIL] {phase_name}:{test_id} "
                f"(expected compiler error in {error_file.name}, but command succeeded)"
            )
            return False
        else:
            print(
                f"  [MISSING GOLDEN] {phase_name}:{test_id} "
                f"(expected {out_file.relative_to(ROOT_DIR)})"
            )
            return False

    # Case 2: Process return code mismatch
    if error_file.exists():
        expected_error = error_file.read_text(encoding="utf-8")
        if process.stderr == expected_error:
            print(f"  [PASS] {phase_name}:{test_id} (expected error)")
            return True
        else:
            print(f"  [FAIL] {phase_name}:{test_id} (stderr mismatch)")
            diff = difflib.unified_diff(
                expected_error.splitlines(keepends=True),
                process.stderr.splitlines(keepends=True),
                fromfile=f"golden/{golden_base.name}/{rel_source.with_suffix('.error')}",
                tofile=f"actual/{golden_base.name}/{rel_source.with_suffix('.error')}",
            )
            print("".join(diff))
            return False
    elif out_file.exists():
        print(
            f"  [FAIL] {phase_name}:{test_id} "
            f"(failed with returncode {process.returncode}, expected {expected_exit})"
        )
        if process.stderr:
            print(process.stderr)
        return False
    else:
        print(
            f"  [MISSING GOLDEN] {phase_name}:{test_id} "
            f"(expected error golden in {error_file.relative_to(ROOT_DIR)})"
        )
        return False




def main() -> int:
    available_phases = [
        "tokenize",
        "parse",
        "typecheck",
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
        "--build-dir",
        help="Build directory for C phases, reused across runs (default: a fresh temporary directory per run, "
        "so that results never depend on artifacts from earlier compiler versions).",
    )
    arg_parser.add_argument(
        "--shadow",
        action="append",
        default=[],
        metavar="CHECK",
        help="Run the compiler with --shadow-CHECK (repeatable; 'all' enables every shadow-mode cross-check).",
    )

    args = arg_parser.parse_args()

    if args.build_dir:
        build_dir = Path(args.build_dir).resolve()
        temp_build_dir: Optional[Path] = None
    else:
        temp_build_dir = Path(tempfile.mkdtemp(prefix="quest-test-build-"))
        build_dir = temp_build_dir
    driver_args = [f"--shadow-{check}" for check in args.shadow]
    try:
        return run_all_tests(args, available_phases, build_dir, driver_args)
    finally:
        if temp_build_dir is not None:
            shutil.rmtree(temp_build_dir, ignore_errors=True)


def run_all_tests(
    args: argparse.Namespace,
    available_phases: list[str],
    build_dir: Path,
    driver_args: list[str],
) -> int:

    # Determine suite mode
    suite_mode = "errors" if args.errors else args.suite

    # Fallback to sys.executable if specified python does not exist
    python_executable = args.python if os.path.exists(args.python) else sys.executable

    phases_to_run = available_phases if args.phase == "all" else [args.phase]

    total_golden = 0
    passed_golden = 0
    skipped_golden = 0
    total_errors = 0
    passed_errors = 0

    print(f"Running tests with Python: {python_executable}")
    print(f"Suite: {suite_mode}, Phases: {', '.join(phases_to_run)}, Timeout: {args.timeout}s")
    print(f"Build dir: {build_dir}" + (f", Driver args: {' '.join(driver_args)}" if driver_args else "") + "\n")

    # 1. Run Golden Tests (if suite is 'golden' or 'all')
    if suite_mode in ("golden", "all"):
        source_files = discover_tests(TESTS_SOURCE_DIR)
        if args.test:
            source_files = [
                sf for sf in source_files
                if args.test in str(sf.relative_to(TESTS_SOURCE_DIR))
            ]

        if source_files:
            print("=== Golden Tests ===")
            for phase in phases_to_run:
                golden_dir = golden_dir_for_phase(phase)
                if not golden_dir.exists():
                    continue
                print(f"--- Phase: {phase} ---")
                for source_file in source_files:
                    skipped_phases = parse_skipped_phases(source_file)
                    rel_source = source_file.relative_to(TESTS_SOURCE_DIR)
                    test_id = str(rel_source.with_suffix(""))
                    if phase.lower() in skipped_phases:
                        skipped_golden += 1
                        print(f"  [SKIP] {phase}:{test_id}")
                        continue
                    total_golden += 1
                    if run_single_golden_test(
                        source_file,
                        phase,
                        update_golden=args.update_golden,
                        python_executable=python_executable,
                        timeout=args.timeout,
                        build_dir=build_dir,
                        driver_args=driver_args,
                    ):
                        passed_golden += 1
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
            if not error_files:
                continue

            if not error_phases_found:
                print("=== Diagnostic Error Tests ===")
                error_phases_found = True

            print(f"--- Phase: {phase} ---")
            pipeline = pipeline_for_phase(phase)
            precursors = pipeline.precursors_of(phase)
            for error_file in error_files:
                skipped_phases = parse_skipped_phases(error_file)
                rel_id = str(error_file.relative_to(phase_error_dir).with_suffix(""))
                if phase.lower() in skipped_phases:
                    print(f"  [SKIP] {phase}:{rel_id}")
                    continue

                total_errors += 1
                directives = parse_test_directives(error_file)
                golden_err_file = golden_error_file_for_test(error_file, phase)
                effective_timeout = directives.timeout if directives.timeout is not None else args.timeout
                passed, report = run_error_test(
                    source_file=error_file,
                    target_phase=phase,
                    precursor_phases=precursors,
                    python_executable=python_executable,
                    root_dir=ROOT_DIR,
                    golden_error_file=golden_err_file,
                    update_golden=args.update_golden,
                    extra_args=directives.args,
                    env_vars=directives.env,
                    stdin_data=directives.stdin_data,
                    timeout=effective_timeout,
                    build_dir=build_dir,
                    driver_args=driver_args,
                )
                if passed:
                    passed_errors += 1
                    status = "[UPDATED]" if report == "[UPDATED]" else "[PASS]"
                    print(f"  {status} {phase}:{rel_id}")
                else:
                    print(f"  [FAIL] {phase}:{rel_id}")
                    print(report)

    # Summary report
    total_tests = total_golden + total_errors
    total_passed = passed_golden + passed_errors

    skip_str = f" ({skipped_golden} skipped)" if skipped_golden > 0 else ""
    print(f"\nSummary: {total_passed}/{total_tests} tests passed{skip_str}.")
    if suite_mode == "all":
        print(f"  Golden tests: {passed_golden}/{total_golden} passed{skip_str}")
        print(f"  Error tests:  {passed_errors}/{total_errors} passed")

    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    sys.exit(main())
