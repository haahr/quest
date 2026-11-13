"""The runner's transcript tests of the self-hosted driver (docs/testing.md
§2.3, §2.7): the programs -e runs, the unit checks (scripts run with the
driver), and the REPL's transcripts."""

import difflib
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from quest.common.location import BYTE_ENCODING
from quest.testing.errors import relativize_root_paths
from quest.testing.layout import ROOT_DIR, DRIVER_SCRIPT, EVAL_CASES, EVAL_GOLDEN, TESTS_REPL_DIR, TESTS_REPL_GOLDEN_DIR
from quest.testing.directives import LOAD_PATTERN, parse_test_directives


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
