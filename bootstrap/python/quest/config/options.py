"""The options of one run of the compiler's pipeline (quest/pipeline.py),
which the driver (quest_driver.py) makes from its command line.

The self-hosted compiler has no counterpart: its driver and build engine take
their options directly (docs/compiler-organization.md §2). docs/pipeline.md
§3.1 lists the options."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class CompilerOptions:
    """The options of one run of the pipeline, read by its phases (through
    CompilerContext.options) and by the loaders and compilers they call
    (through Environment.options). CompilerContext.create fills in build_dir,
    current_dir, and program_dir when the driver leaves them unset."""

    # The phase to stop after, whose output is printed (--stop-after)
    stop_after: Optional[str] = None
    # Phases whose output is printed as the pipeline goes on (--dump-after)
    dump_after: set[str] = field(default_factory=set)
    # Directories searched for imported units (-I; docs/modules.md §2.2)
    include_paths: list[Path] = field(default_factory=list)
    # Print each top-level binding's signature and value, as the REPL does
    echo: bool = False
    # Print source offsets in AST dumps, and literals' values in token dumps
    show_offsets: bool = False
    show_values: bool = False
    # The grammar target the parse phase starts from (syntax/grammar.py,
    # resolve_syntax_target); None for a program
    target: Optional[Any] = None
    # Write C rather than a binary (--emit-c), and the file written (-o); both
    # mark the run as C compilation (is_c_compilation_mode)
    emit_c: bool = False
    output_path: Optional[Path] = None
    # Compile C with -DQUEST_NOGC, under which the collector never collects
    nogc: bool = False
    # Compiled code and the IR interpreter print the last phrase's result, as
    # the source interpreter does
    print_result: bool = False
    # What run_c_compiled runs the binary with, which inherits the driver's
    # environment and standard input: its arguments, and the exit status
    # expected of it (any other is an error)
    target_args: list[str] = field(default_factory=list)
    expected_exit: int = 0
    # Objects (.o) named on the command line, linked into the binary
    extra_objects: list[Path] = field(default_factory=list)
    # Where interface and module artifacts are built and reused
    # (docs/build-process.md §3); it is searched first for imports
    build_dir: Optional[Path] = None
    # Compile every module from source into the program's C (--whole-program;
    # docs/build-process.md §1.2), rather than separately
    whole_program: bool = False
    # The directory of the program's main file, against which unit names under
    # no search root are made canonical (docs/modules.md §2.3), and the
    # directory of the file being compiled
    program_dir: Optional[Path] = None
    current_dir: Optional[Path] = None
    # 'interface' or 'module' when the source is a unit file, whose phases
    # compile it as one (quest/modules/units.py)
    unit: Optional[str] = None

    @property
    def is_c_compilation_mode(self) -> bool:
        """Checks whether compilation options specify actively compiling or
        generating C code."""
        if self.whole_program:
            return False
        # The phases that print the IR as C and run the result (docs/testing.md
        # §2.3)
        c_phases = ("codegen_c", "run_c_compiled")
        if self.stop_after in c_phases:
            return True
        if self.emit_c or self.output_path is not None:
            return True
        return any(p in c_phases for p in self.dump_after)

    @property
    def is_typecheck_only(self) -> bool:
        """Checks whether compilation options specify stopping after
        typechecking in non-C mode."""
        return self.stop_after == "typecheck" and not self.is_c_compilation_mode
