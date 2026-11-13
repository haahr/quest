"""The directives a test program's comments give the runner: the phases to
skip (docs/testing.md §2.4); its arguments, environment, exit status,
timeout, standard input, and echo (§2.5); and the files a REPL transcript
loads (§2.7)."""

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from quest.syntax.sources import BYTE_ENCODING


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
