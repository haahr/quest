"""Compiler configuration options and settings."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CompilerOptions:
    """Compilation configuration options passed to compiler phases."""

    stop_after: Optional[str] = None
    dump_after: set[str] = field(default_factory=set)
    include_paths: list[Path] = field(default_factory=list)
    echo: bool = False
    show_offsets: bool = False
    show_values: bool = False
    target: Optional[Any] = None
    emit_c: bool = False
    output_path: Optional[Path] = None
    nogc: bool = False
    print_result: bool = False
    target_args: list[str] = field(default_factory=list)
    expected_exit: int = 0
    target_env: Optional[dict[str, str]] = None
    target_stdin: Optional[str] = None
    extra_objects: list[Path] = field(default_factory=list)
    build_dir: Optional[Path] = None
    whole_program: bool = False
    emit_deps: bool = False
    program_dir: Optional[Path] = None
    current_dir: Optional[Path] = None

    @property
    def is_c_compilation_mode(self) -> bool:
        """Checks whether compilation options specify actively compiling or generating C code."""
        if self.whole_program:
            return False
        # The C backends' phases: the current emitter's, and the IR's (docs/ir.md §12, step 5)
        c_phases = ("codegen_c", "run_c_compiled")
        if self.stop_after in c_phases:
            return True
        if self.emit_c or self.output_path is not None:
            return True
        return any(p in c_phases for p in self.dump_after)

    @property
    def is_typecheck_only(self) -> bool:
        """Checks whether compilation options specify stopping after typechecking in non-C mode."""
        return self.stop_after == "typecheck" and not self.is_c_compilation_mode
