"""The bootstrap driver's command lines (docs/pipeline.md §4): the parsers of
run_driver's (./questboot) and run_compile's (`questboot compile`), and the
split of a command line into the driver's arguments and the program's. The
self-hosted counterpart is questlang/driver/options."""

from __future__ import annotations

import argparse
from pathlib import Path

from quest.modules.graph import UnitKind, file_unit_kind
from quest.pipeline import IR_DUMP_PHASES, IR_RUN_PHASES


def driver_parser() -> argparse.ArgumentParser:
    """The parser of run_driver's command line."""
    all_phases = [
        "tokenize", "parse", "desugar", "typecheck", *IR_DUMP_PHASES, *IR_RUN_PHASES, "interpret", "codegen_c",
        "run_c_compiled",
    ]

    arg_parser = argparse.ArgumentParser(
        prog="quest",
        description="Quest Compiler Driver — compile, check, interpret, and inspect Quest programs.",
        # Abbreviated options would hide which arguments take values from
        # split_program_args
        allow_abbrev=False,
    )
    arg_parser.add_argument(
        "files",
        nargs="*",
        default=[],
        help="Path to Quest source file (.quest), object files (.o, .a), or '-' for standard input.",
    )
    arg_parser.add_argument(
        "-o", "--output",
        dest="output",
        default=None,
        help="Output binary file path (or C file path if --emit-c).",
    )
    arg_parser.add_argument(
        "-c", "--compile-only",
        dest="compile_only",
        action="store_true",
        help="Compile only (do not link). For interfaces, generates .int.h and .qi.",
    )
    arg_parser.add_argument(
        "-e", "--eval", "--code", "--command",
        dest="code",
        help="Inline Quest code string to process.",
    )
    arg_parser.add_argument(
        "-i", "--interactive",
        dest="interactive",
        action="store_true",
        help="Run file, then enter interactive REPL (or enter REPL if no file).",
    )
    arg_parser.add_argument(
        "--echo",
        dest="echo",
        action="store_true",
        help="Echo Cardelli-format typescript for each top-level phrase in batch mode.",
    )
    arg_parser.add_argument(
        "--stop-after", "--stop_after",
        dest="stop_after",
        choices=all_phases,
        help="Stop pipeline execution after specified phase and dump its canonical output.",
    )
    arg_parser.add_argument(
        "--dump-after", "--dump_after",
        dest="dump_after",
        action="append",
        choices=all_phases,
        default=[],
        help="Dump canonical output of specified phase while continuing pipeline execution.",
    )
    arg_parser.add_argument(
        "--print-result", "--print_result",
        dest="print_result",
        action="store_true",
        help="Print Cardelli-format result of the final phrase when compiling C code.",
    )
    arg_parser.add_argument(
        "-I", "--include",
        dest="include_paths",
        action="append",
        default=[],
        help="Add directory to interface/module search path.",
    )
    arg_parser.add_argument(
        "--show-offsets",
        dest="show_offsets",
        action="store_true",
        help="Include character offsets in AST and typed AST dumps.",
    )
    arg_parser.add_argument(
        "--show-values",
        dest="show_values",
        action="store_true",
        help="Include parsed literal values in token dumps.",
    )
    arg_parser.add_argument(
        "--expected-exit", "--expected_exit",
        dest="expected_exit",
        type=int,
        default=0,
        help="Expected exit code of target program (for testing).",
    )
    arg_parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Stream build operations to stderr.",
    )
    arg_parser.add_argument(
        "--build-dir", "--build_dir",
        dest="build_dir",
        default=None,
        help="Directory path for transient build artifacts (default: .build).",
    )
    arg_parser.add_argument(
        "--whole-program", "--whole_program",
        dest="whole_program",
        action="store_true",
        help="Force whole-program compilation (inline all modules from source).",
    )
    arg_parser.add_argument(
        "--emit-deps", "--emit_deps",
        dest="emit_deps",
        action="store_true",
        help="Deprecated: module dependencies are recorded in .qm manifests.",
    )
    return arg_parser


def compile_parser(available_phases: list[str]) -> argparse.ArgumentParser:
    """The parser of run_compile's command line, whose --stop-after takes one
    of available_phases, the compile pipeline's."""
    arg_parser = argparse.ArgumentParser(
        prog="quest compile",
        description="Quest Compiler — compile Quest source into C or native machine binary.",
    )
    arg_parser.add_argument(
        "files",
        nargs="*",
        default=[],
        help="Path to Quest source file (.quest), object files (.o, .a), or '-' for standard input.",
    )
    arg_parser.add_argument(
        "-o", "--output",
        dest="output",
        default=None,
        help="Output binary file path (or C file path if --emit-c).",
    )
    arg_parser.add_argument(
        "--emit-c",
        dest="emit_c",
        action="store_true",
        help="Emit C source code instead of compiling to a binary executable.",
    )
    arg_parser.add_argument(
        "--nogc",
        dest="nogc",
        action="store_true",
        help="Compile with -DQUEST_NOGC: the collector allocates but never collects.",
    )
    arg_parser.add_argument(
        "-c", "--compile-only",
        dest="compile_only",
        action="store_true",
        help="Compile only (do not link). For interfaces, generates .int.h and .qi.",
    )
    arg_parser.add_argument(
        "-e", "--eval", "--code", "--command",
        dest="code",
        help="Inline Quest code string to compile.",
    )
    arg_parser.add_argument(
        "--echo",
        dest="echo",
        action="store_true",
        help="Echo Cardelli-format typescript for top-level phrases.",
    )
    arg_parser.add_argument(
        "-I", "--include",
        dest="include_paths",
        action="append",
        default=[],
        help="Add directory to interface/module search path.",
    )
    arg_parser.add_argument(
        "--stop-after", "--stop_after",
        dest="stop_after",
        choices=available_phases,
        help="Stop pipeline execution after specified phase and dump its canonical output.",
    )
    arg_parser.add_argument(
        "--dump-after", "--dump_after",
        dest="dump_after",
        action="append",
        choices=available_phases,
        default=[],
        help="Dump canonical output of specified phase while continuing pipeline execution.",
    )
    arg_parser.add_argument(
        "--print-result", "--print_result",
        dest="print_result",
        action="store_true",
        help="Print Cardelli-format result of the final phrase when compiling C code.",
    )
    arg_parser.add_argument(
        "-v", "--verbose",
        dest="verbose",
        action="store_true",
        help="Stream build operations to stderr.",
    )
    arg_parser.add_argument(
        "--build-dir", "--build_dir",
        dest="build_dir",
        default=None,
        help="Directory path for transient build artifacts (default: .build).",
    )
    arg_parser.add_argument(
        "--whole-program", "--whole_program",
        dest="whole_program",
        action="store_true",
        help="Force whole-program compilation (inline all modules from source).",
    )
    arg_parser.add_argument(
        "--emit-deps", "--emit_deps",
        dest="emit_deps",
        action="store_true",
        help="Deprecated: module dependencies are recorded in .qm manifests.",
    )
    return arg_parser


OBJECT_SUFFIXES = (".o", ".a", ".dylib", ".so")


def split_program_args(arg_parser: argparse.ArgumentParser, args: list[str]) -> tuple[list[str], list[str]]:
    """Splits the command line into the driver's arguments and the program's, as
    Python does a script's: everything after the program file (or '-') is the
    program's, options included, so that `quest program.quest -x y` passes the
    program -x and y. A unit file and an object file are not programs, and so
    options may follow them. A '--' before the program file ends the driver's
    arguments too, giving the program's to -e code or the REPL."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            return args[:i], args[i + 1:]
        if arg.startswith("-") and arg != "-":
            action = arg_parser._option_string_actions.get(arg)
            # An option that takes a value takes the next argument, unless it is
            # written --option=value
            i += 2 if action is not None and action.nargs != 0 else 1
            continue
        if arg == "-" or (Path(arg).suffix not in OBJECT_SUFFIXES and file_unit_kind(Path(arg)) == UnitKind.PROGRAM):
            return args[:i + 1], args[i + 1:]
        i += 1
    return args, []
