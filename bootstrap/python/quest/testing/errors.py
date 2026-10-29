"""Quest Compiler Error and Diagnostic Test Runner Framework."""

from __future__ import annotations

import difflib
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import quest.syntax.ast as ast
from quest.modules.graph import Resolver, Roots
from quest.syntax.grammar import parse_quest_program
from quest.syntax.sources import BYTE_ENCODING, SourceMap
from quest.syntax.tokenizer import Tokenizer


@dataclass(frozen=True)
class ExpectedDiagnostic:
    """An expected diagnostic declared via an inline comment (* SEVERITY: REGEXP
    *)."""
    line: int
    severity: str
    pattern: str
    # The file the comment is in (the test, or a unit it imports); None matches
    # a diagnostic in any file
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


# Matches (* ERROR: ... *), (* WARNING: ... *), (* INFO: ... *), (* FATAL: ...
# *)
EXPECTATION_PATTERN = re.compile(
    r"\(\*\s*(ERROR|WARNING|INFO|FATAL)\s*:\s*(.*?)\s*\*\)",
    re.IGNORECASE,
)

# Matches standard compiler diagnostic header: file:line:col: severity: message
# or file:line:col: severity[code]: message
DIAGNOSTIC_HEADER_PATTERN = re.compile(
    r"^(.*?):(\d+):(\d+):\s*(error|warning|info|fatal)(?: error)?(?:\[.*?\])?:\s*(.*)$",
    re.IGNORECASE,
)


def extract_expected_diagnostics(source_text: str, file: Optional[Path] = None) -> list[ExpectedDiagnostic]:
    """Scans Quest source text (of file, if given) for inline diagnostic
    expectations on each line."""
    expectations: list[ExpectedDiagnostic] = []
    for line_idx, line in enumerate(source_text.splitlines(), start=1):
        for match in EXPECTATION_PATTERN.finditer(line):
            severity = match.group(1).lower()
            pattern = match.group(2).strip()
            expectations.append(ExpectedDiagnostic(line=line_idx, severity=severity, pattern=pattern, file=file))
    return expectations


def _unit_imports(path: Path, resolver: Resolver) -> list[Path]:
    """The interface and module files beside path (found from its directory, as
    compiling it resolves them, but without search paths) that the unit or
    program in it imports, including a module's own interface; none if it does
    not parse. Units found elsewhere (the standard library's) are not beside
    it."""
    try:
        text = path.read_text(encoding=BYTE_ENCODING)
        prog = parse_quest_program(Tokenizer(text, str(path)).tokenize_all(), SourceMap(text, str(path)))
    except Exception:
        return []
    interfaces: list[str] = []
    modules: list[str] = []
    for phrase in getattr(prog, "phrases", ()):
        items: tuple[ast.ImportItem, ...] = ()
        match phrase:
            case ast.ImportPhrase(items=import_items):
                items = import_items
            case ast.InterfaceDecl(imports=import_items):
                items = import_items
            case ast.ModuleDecl(imports=import_items, interface_name=iface_name):
                items = import_items
                interfaces.append(iface_name)
        for item in items:
            interfaces.append(item.effective_interface_path)
            modules.extend(item.effective_module_paths)
    roots = Roots.of((), None)
    here = path.parent.resolve()
    found = [resolver.interface(name, path.parent, roots).source for name in interfaces]
    found += [resolver.module(name, path.parent, roots).source for name in modules]
    return [f for f in found if f is not None and f.is_relative_to(here)]


def imported_unit_files(source_file: Path) -> list[Path]:
    """The interface and module files beside an error test that it imports,
    directly or through other such units.

    The imports are resolved by a resolver of the test's own
    (docs/build-process.md §2.1), each once."""
    resolver = Resolver()
    found: list[Path] = []
    queue = [source_file]
    while queue:
        for unit in _unit_imports(queue.pop(0), resolver):
            unit = unit.resolve()
            if unit not in found and unit != source_file.resolve():
                found.append(unit)
                queue.append(unit)
    return found


def expected_diagnostics_of(source_file: Path) -> list[ExpectedDiagnostic]:
    """The inline expectations of an error test: those in the test and in the
    units beside it that it imports (docs/testing.md §3.3), each matched only by
    a diagnostic in its own file."""
    expectations: list[ExpectedDiagnostic] = []
    for file in [source_file.resolve(), *imported_unit_files(source_file)]:
        expectations.extend(extract_expected_diagnostics(file.read_text(encoding=BYTE_ENCODING), file))
    return expectations


def _in_file(actual: ActualDiagnostic, file: Optional[Path]) -> bool:
    """Whether a diagnostic is located in file. The driver names the test by the
    absolute path it is given and an imported unit by its path relative to the
    driver's directory, if it is inside it, else by its full path."""
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
    """Checks whether all expected pattern lines are present in stderr_text
    (literal or regex)."""
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


def relativize_root_paths(text: str, root_dir: Path) -> str:
    """Rewrites absolute paths under root_dir in text as paths relative to
    it."""
    for root in {str(root_dir), str(root_dir.resolve())}:
        text = text.replace(root.rstrip(os.sep) + os.sep, "")
    return text


def format_canonical_error_golden(stderr_text: str) -> str:
    """Generates canonical pattern lines from stderr_text for
    --update-golden."""
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

            # Collect subsequent lines that belong to this diagnostic (carets,
            # notes, help)
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
    driver_command: Optional[list[str]] = None,
) -> tuple[int, str, str]:
    """Executes the compiler driver up to the specified phase with an optional
    timeout: the bootstrap's, or the one driver_command runs (the self-hosted
    driver, which has a build directory only for the C phases)."""
    if driver_command is not None:
        command = [*driver_command, "--stop-after", phase_name]
        # The units of programs compiled to C are built and reused there, apart
        # from the bootstrap's artifacts
        if phase_name in ("codegen_c", "run_c_compiled") and build_dir is not None:
            command.extend(["--build-dir", str(build_dir / "self-hosted-units")])
    else:
        driver_script = root_dir / "bootstrap" / "python" / "quest_driver.py"
        command = [
            python_executable,
            str(driver_script),
            "--stop-after",
            phase_name,
        ]
        if driver_args:
            command.extend(driver_args)
        # Every phase builds and reuses artifacts in the build directory
        # (docs/build-process.md §5.2.4).
        if build_dir is None:
            build_dir = root_dir / ".build"
        build_dir.mkdir(parents=True, exist_ok=True)
        command.extend(["--build-dir", str(build_dir)])
    if extra_args:
        command.extend(extra_args)
    command.append(str(source_file.resolve()))

    env = os.environ.copy()
    env["PYTHONPATH"] = str(root_dir / "bootstrap" / "python")
    # Checks that typed programs are well scoped (quest/typechecker/scoping.py),
    # as golden tests do
    env["QUEST_CHECK_SCOPES"] = "1"
    env["QUEST_CHECK_IR"] = "1"
    # The project directory, whose lib/ the self-hosted driver reads the
    # standard library from (it runs elsewhere)
    env["QUEST_HOME"] = str(root_dir)
    if env_vars:
        env.update(env_vars)

    try:
        # Each run starts in a fresh, empty directory of its own, where the
        # program may create files
        with tempfile.TemporaryDirectory(prefix="quest-test-") as scratch_dir:
            process = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding=BYTE_ENCODING,
                input=stdin_data,
                env=env,
                timeout=timeout,
                cwd=scratch_dir,
            )
        return process.returncode, process.stdout, process.stderr
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else (
            exc.stdout.decode(BYTE_ENCODING, errors="replace") if exc.stdout else ""
        )
        stderr = exc.stderr if isinstance(exc.stderr, str) else (
            exc.stderr.decode(BYTE_ENCODING, errors="replace") if exc.stderr else ""
        )
        timeout_msg = f"Phase '{phase_name}' timed out after {timeout} seconds"
        full_err = f"{stderr}\n{timeout_msg}" if stderr else timeout_msg
        return -1, stdout, full_err


def _diagnostic_blocks(stderr: str) -> list[str]:
    """stderr's diagnostics, each its header line and the lines after it up to
    the next header."""
    blocks: list[list[str]] = []
    for line in stderr.splitlines():
        if DIAGNOSTIC_HEADER_PATTERN.match(line) or not blocks:
            blocks.append([line])
        else:
            blocks[-1].append(line)
    return ["\n".join(block) + "\n" for block in blocks]


def _check_further_errors(
    stderr: str, root_dir: Path, further_errors_file: Optional[Path], update_golden: bool
) -> tuple[bool, str, str]:
    """For the self-hosted driver: checks the diagnostics after its first
    against further_errors_file (or records them there), and returns the first,
    which the test's expectations are matched against."""
    blocks = _diagnostic_blocks(stderr)
    if len(blocks) <= 1:
        if further_errors_file is not None and further_errors_file.exists():
            return False, f"  Further errors recorded in {further_errors_file.name} were not reported", stderr
        return True, "", stderr
    full = relativize_root_paths(stderr, root_dir)
    if further_errors_file is None:
        return True, "", blocks[0]
    if update_golden:
        further_errors_file.parent.mkdir(parents=True, exist_ok=True)
        further_errors_file.write_text(full, encoding=BYTE_ENCODING)
    elif not further_errors_file.exists():
        shown = "\n".join(f"    | {line}" for line in full.strip().splitlines())
        where = further_errors_file.relative_to(root_dir)
        return False, f"  Further errors are not recorded in {where} (review, then --update-golden):\n{shown}", stderr
    elif further_errors_file.read_text(encoding=BYTE_ENCODING) != full:
        diff = difflib.unified_diff(
            further_errors_file.read_text(encoding=BYTE_ENCODING).splitlines(keepends=True),
            full.splitlines(keepends=True),
            fromfile=str(further_errors_file.relative_to(root_dir)),
            tofile="actual",
        )
        return False, "  Further errors differ:\n" + "".join(diff).rstrip(), stderr
    return True, "", blocks[0]


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
    driver_command: Optional[list[str]] = None,
    further_errors_file: Optional[Path] = None,
    all_errors: bool = False,
) -> tuple[bool, str]:
    """Runs an error test with precursor validation, timeout, and pattern-based
    or diagnostic matching.

    With driver_command, the test runs the self-hosted driver, which may report
    errors after the bootstrap's one (docs/diagnostics.md §4.5): its first
    diagnostic must be the one expected, and when it reports more, its whole
    output must be further_errors_file's, which --update-golden writes for
    review. With all_errors (a test of several errors,
    tests/self-hosted/errors), its diagnostics must be the test's inline
    expectations, every one."""
    # Step 1: Precursor Phase Validation
    for pre_phase in precursor_phases:
        rc, _, stderr = execute_phase(
            pre_phase, source_file, python_executable, root_dir,
            extra_args=extra_args, env_vars=env_vars, stdin_data=stdin_data,
            timeout=timeout, build_dir=build_dir, driver_args=driver_args, driver_command=driver_command,
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
        timeout=timeout, build_dir=build_dir, driver_args=driver_args, driver_command=driver_command,
    )
    if rc == -1 and f"timed out after {timeout} seconds" in stderr:
        return False, f"Target phase '{target_phase}' timed out after {timeout}s"
    if rc == 0:
        return False, f"Expected error in phase '{target_phase}', but command succeeded with return code 0"

    if driver_command is not None and not all_errors:
        ok, report, stderr = _check_further_errors(stderr, root_dir, further_errors_file, update_golden)
        if not ok:
            return False, report

    # Step 3: Golden Pattern Matching (or update)
    if golden_error_file is not None:
        # Golden files must not depend on where the repository is checked out
        stderr = relativize_root_paths(stderr, root_dir)
        # The bootstrap's goldens are the bootstrap's: the self-hosted driver
        # only records its further errors
        if update_golden and driver_command is None:
            golden_content = format_canonical_error_golden(stderr)
            golden_error_file.parent.mkdir(parents=True, exist_ok=True)
            golden_error_file.write_text(golden_content, encoding=BYTE_ENCODING)
            return True, "[UPDATED]"

        if golden_error_file.exists():
            patterns = extract_expected_patterns(golden_error_file.read_text(encoding=BYTE_ENCODING))
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

    # Step 4: Fallback to inline (* ERROR: ... *) comments if golden file not
    # present
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
