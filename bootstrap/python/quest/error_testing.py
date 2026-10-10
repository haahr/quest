"""Quest Compiler Error and Diagnostic Test Runner Framework."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ExpectedDiagnostic:
    """An expected diagnostic declared via an inline comment (* SEVERITY: REGEXP *)."""
    line: int
    severity: str
    pattern: str
    # The file the comment is in (the test, or a unit it imports); None matches a diagnostic in any file
    file: Optional[Path] = None


@dataclass(frozen=True)
class ActualDiagnostic:
    """A diagnostic emitted by a compiler phase, parsed from stderr."""
    file_name: str
    line: int
    column: int
    severity: str
    message: str
    full_text: str


# Matches (* ERROR: ... *), (* WARNING: ... *), (* INFO: ... *), (* FATAL: ... *)
EXPECTATION_PATTERN = re.compile(
    r"\(\*\s*(ERROR|WARNING|INFO|FATAL)\s*:\s*(.*?)\s*\*\)",
    re.IGNORECASE,
)

# Matches standard compiler diagnostic header: file:line:col: severity: message
# or file:line:col: severity[code]: message
DIAGNOSTIC_HEADER_PATTERN = re.compile(
    r"^(.*?):(\d+):(\d+):\s*(error|warning|info|fatal)(?:\[.*?\])?:\s*(.*)$",
    re.IGNORECASE,
)


def extract_expected_diagnostics(source_text: str, file: Optional[Path] = None) -> list[ExpectedDiagnostic]:
    """Scans Quest source text (of file, if given) for inline diagnostic expectations on each line."""
    expectations: list[ExpectedDiagnostic] = []
    for line_idx, line in enumerate(source_text.splitlines(), start=1):
        for match in EXPECTATION_PATTERN.finditer(line):
            severity = match.group(1).lower()
            pattern = match.group(2).strip()
            expectations.append(ExpectedDiagnostic(line=line_idx, severity=severity, pattern=pattern, file=file))
    return expectations


def _unit_imports(path: Path) -> list[Path]:
    """The interface and module files beside path (found from its directory) that the unit or program in it imports,
    including a module's own interface; none if it does not parse."""
    from quest import ast
    from quest.grammar import parse_quest_program
    from quest.tokenizer import Tokenizer
    from quest.tokens import SourceMap

    try:
        text = path.read_text(encoding="utf-8")
        prog = parse_quest_program(Tokenizer(text, str(path)).tokenize_all(), SourceMap(text, str(path)))
    except Exception:
        return []
    interfaces: list[str] = []
    modules: list[str] = []
    for phrase in getattr(prog, "phrases", ()):
        items: tuple[ast.ImportItem, ...] = ()
        if isinstance(phrase, ast.ImportPhrase):
            items = phrase.items
        elif isinstance(phrase, ast.InterfaceDecl):
            items = phrase.imports
        elif isinstance(phrase, ast.ModuleDecl):
            items = phrase.imports
            interfaces.append(phrase.interface_name)
        for item in items:
            interfaces.append(item.effective_interface_path)
            modules.extend(item.effective_module_paths)
    candidates = [path.parent / f"{name.lower()}.int.quest" for name in interfaces]
    candidates += [path.parent / f"{name.lower()}.mod.quest" for name in modules]
    return [c for c in candidates if c.is_file()]


def imported_unit_files(source_file: Path) -> list[Path]:
    """The interface and module files beside an error test that it imports, directly or through other such units."""
    found: list[Path] = []
    queue = [source_file]
    while queue:
        for unit in _unit_imports(queue.pop(0)):
            unit = unit.resolve()
            if unit not in found and unit != source_file.resolve():
                found.append(unit)
                queue.append(unit)
    return found


def expected_diagnostics_of(source_file: Path) -> list[ExpectedDiagnostic]:
    """The inline expectations of an error test: those in the test and in the units beside it that it imports
    (docs/testing.md §3.3), each matched only by a diagnostic in its own file."""
    expectations: list[ExpectedDiagnostic] = []
    for file in [source_file.resolve(), *imported_unit_files(source_file)]:
        expectations.extend(extract_expected_diagnostics(file.read_text(encoding="utf-8"), file))
    return expectations


def _in_file(actual: ActualDiagnostic, file: Optional[Path]) -> bool:
    """Whether a diagnostic is located in file. The driver names the test by the absolute path it is given and
    an imported unit by its path relative to the driver's directory, if it is inside it, else by its full path."""
    if file is None:
        return True
    actual_path = Path(actual.file_name)
    if actual_path.is_absolute():
        return actual_path.resolve() == file
    return actual_path.name == file.name


def extract_expected_patterns(error_golden_text: str) -> list[str]:
    """Scans .error golden file text for expected regex/substring patterns."""
    patterns: list[str] = []
    for line in error_golden_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def match_error_patterns(stderr_text: str, patterns: list[str]) -> tuple[bool, list[str]]:
    """Checks whether all expected pattern lines are present in stderr_text (literal or regex)."""
    unmatched: list[str] = []
    stderr_lower = stderr_text.lower()
    for pat in patterns:
        matched = False
        if pat.lower() in stderr_lower:
            matched = True
        else:
            try:
                if re.search(pat, stderr_text, re.IGNORECASE | re.MULTILINE):
                    matched = True
            except re.error:
                pass
        if not matched:
            unmatched.append(pat)
    return len(unmatched) == 0, unmatched


def format_canonical_error_golden(stderr_text: str) -> str:
    """Generates canonical pattern lines from stderr_text for --update-golden."""
    diags = parse_actual_diagnostics(stderr_text)
    if diags:
        lines = [f"{d.severity.lower()}: {d.message}" for d in diags]
        return "\n".join(lines) + "\n"
    # Fallback to non-empty lines from stderr
    clean_lines = [line.strip() for line in stderr_text.splitlines() if line.strip()]
    return "\n".join(clean_lines) + "\n"


def parse_actual_diagnostics(stderr_text: str) -> list[ActualDiagnostic]:
    """Parses compiler stderr output into a list of ActualDiagnostic objects."""
    diagnostics: list[ActualDiagnostic] = []
    lines = stderr_text.splitlines()
    idx = 0

    while idx < len(lines):
        line = lines[idx]
        match = DIAGNOSTIC_HEADER_PATTERN.match(line)
        if match:
            file_name = match.group(1).strip()
            line_num = int(match.group(2))
            col_num = int(match.group(3))
            severity = match.group(4).lower()
            message = match.group(5).strip()

            # Collect subsequent lines that belong to this diagnostic (carets, notes, help)
            block_lines = [line]
            idx += 1
            while idx < len(lines) and not DIAGNOSTIC_HEADER_PATTERN.match(lines[idx]):
                block_lines.append(lines[idx])
                idx += 1

            full_text = "\n".join(block_lines)
            diagnostics.append(
                ActualDiagnostic(
                    file_name=file_name,
                    line=line_num,
                    column=col_num,
                    severity=severity,
                    message=message,
                    full_text=full_text,
                )
            )
        else:
            idx += 1

    return diagnostics


def execute_phase(
    phase_name: str,
    source_file: Path,
    python_executable: str,
    root_dir: Path,
    extra_args: Optional[list[str]] = None,
    env_vars: Optional[dict[str, str]] = None,
    stdin_data: Optional[str] = None,
    timeout: Optional[float] = None,
    build_dir: Optional[Path] = None,
    driver_args: Optional[list[str]] = None,
) -> tuple[int, str, str]:
    """Executes the compiler driver up to the specified phase with an optional timeout."""
    driver_script = root_dir / "bootstrap" / "python" / "quest_driver.py"
    command = [
        python_executable,
        str(driver_script),
        "--stop-after",
        phase_name,
    ]
    if driver_args:
        command.extend(driver_args)
    # Every phase builds and reuses artifacts in the build directory (docs/build-process.md §5.2.4).
    if build_dir is None:
        build_dir = root_dir / ".build"
    build_dir.mkdir(parents=True, exist_ok=True)
    command.extend(["--build-dir", str(build_dir)])
    if extra_args:
        command.extend(extra_args)
    command.append(str(source_file.resolve()))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root_dir / "bootstrap" / "python")
    if env_vars:
        env.update(env_vars)

    try:
        # Each run starts in a fresh, empty directory of its own, where the program may create files
        with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                input=stdin_data,
                env=env,
                timeout=timeout,
                cwd=scratch_dir,
            )
        return process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (
            exc.stdout.decode("utf-8", errors="replace") if exc.stdout else ""
        )
        stderr = exc.stderr if isinstance(exc.stderr, str) else (
            exc.stderr.decode("utf-8", errors="replace") if exc.stderr else ""
        )
        timeout_msg = f"Phase '{phase_name}' timed out after {timeout} seconds"
        full_err = f"{stderr}\n{timeout_msg}" if stderr else timeout_msg
        return -1, stdout, full_err


def run_error_test(
    source_file: Path,
    target_phase: str,
    precursor_phases: list[str],
    python_executable: str,
    root_dir: Path,
    golden_error_file: Optional[Path] = None,
    update_golden: bool = False,
    extra_args: Optional[list[str]] = None,
    env_vars: Optional[dict[str, str]] = None,
    stdin_data: Optional[str] = None,
    phase_configs: Optional[dict] = None,
    timeout: Optional[float] = None,
    build_dir: Optional[Path] = None,
    driver_args: Optional[list[str]] = None,
) -> tuple[bool, str]:
    """Runs an error test with precursor validation, timeout, and pattern-based or diagnostic matching."""
    # Step 1: Precursor Phase Validation
    for pre_phase in precursor_phases:
        rc, _, stderr = execute_phase(
            pre_phase, source_file, python_executable, root_dir,
            extra_args=extra_args, env_vars=env_vars, stdin_data=stdin_data,
            timeout=timeout, build_dir=build_dir, driver_args=driver_args,
        )
        if rc != 0 or parse_actual_diagnostics(stderr):
            err_msg = stderr.strip() if stderr.strip() else f"exited with code {rc}"
            return False, (
                f"Precursor phase '{pre_phase}' failed unexpectedly before reaching target phase '{target_phase}':\n"
                f"{err_msg}"
            )

    # Step 2: Target Phase Execution
    rc, stdout, stderr = execute_phase(
        target_phase, source_file, python_executable, root_dir,
        extra_args=extra_args, env_vars=env_vars, stdin_data=stdin_data,
        timeout=timeout, build_dir=build_dir, driver_args=driver_args,
    )
    if rc == -1 and f"timed out after {timeout} seconds" in stderr:
        return False, f"Target phase '{target_phase}' timed out after {timeout}s"
    if rc == 0:
        return False, f"Expected error in phase '{target_phase}', but command succeeded with return code 0"

    # Step 3: Golden Pattern Matching (or update)
    if golden_error_file is not None:
        if update_golden:
            golden_content = format_canonical_error_golden(stderr)
            golden_error_file.parent.mkdir(parents=True, exist_ok=True)
            golden_error_file.write_text(golden_content, encoding="utf-8")
            return True, "[UPDATED]"

        if golden_error_file.exists():
            patterns = extract_expected_patterns(golden_error_file.read_text(encoding="utf-8"))
            ok, unmatched = match_error_patterns(stderr, patterns)
            if ok:
                return True, ""
            report_lines = [f"  Expected patterns NOT found in stderr ({golden_error_file.name}):"]
            for pat in unmatched:
                report_lines.append(f"    - /{pat}/")
            report_lines.append("  Actual stderr was:")
            for line in stderr.strip().splitlines():
                report_lines.append(f"    | {line}")
            return False, "\n".join(report_lines)

    # Step 4: Fallback to inline (* ERROR: ... *) comments if golden file not present
    expected = expected_diagnostics_of(source_file)
    if not expected:
        if golden_error_file is not None:
            return False, f"Missing golden error file: {golden_error_file}"
        return False, f"Test file {source_file.name} defines no (* SEVERITY: REGEXP *) expectations"

    actual = parse_actual_diagnostics(stderr)
    unmatched_expected = list(expected)
    unmatched_actual = list(actual)

    for exp in expected:
        for act in list(unmatched_actual):
            if act.line == exp.line and act.severity == exp.severity and _in_file(act, exp.file):
                if re.search(exp.pattern, act.message, re.IGNORECASE) or re.search(
                    exp.pattern, act.full_text, re.IGNORECASE
                ):
                    unmatched_expected.remove(exp)
                    unmatched_actual.remove(act)
                    break

    if not unmatched_expected and not unmatched_actual:
        return True, ""

    report_lines = []
    if unmatched_expected:
        report_lines.append("  Expected diagnostics NOT found:")
        for exp in unmatched_expected:
            where = f"{exp.file.name}:" if exp.file is not None and exp.file != source_file.resolve() else ""
            report_lines.append(f"    - {where}line {exp.line}: {exp.severity.upper()}: /{exp.pattern}/")
    if unmatched_actual:
        report_lines.append("  Unexpected actual diagnostics emitted:")
        for act in unmatched_actual:
            where = "" if _in_file(act, source_file.resolve()) else f"{Path(act.file_name).name}:"
            report_lines.append(f"    - {where}line {act.line}:{act.column}: {act.severity.upper()}: {act.message}")

    return False, "\n".join(report_lines)
