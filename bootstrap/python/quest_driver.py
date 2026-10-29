#!/usr/bin/env python3
"""Quest Compiler Unified CLI Driver.

Executes compiler phases sequentially, supporting early exit (--stop-after),
intermediate inspection (--dump-after), inline execution (-e), and include paths
(-I).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quest.interpreter.builtins import set_system_args, use_byte_streams
from quest.diagnostics import DiagnosticRenderer, QuestCompilerError, Severity, diagnostic_of
from quest.config import CompilerOptions
from quest.interpreter.formatting import format_interactive_result
from quest.pipeline import (
    CompilerContext,
    compile_pipeline,
    default_pipeline,
    IR_DUMP_PHASES,
    IR_RUN_PHASES,
    ir_pipeline,
    ir_run_pipeline,
    full_pipeline,
    link_dependencies,
)
from quest.build.engine import BuildEngine, compile_unit_file
from quest.codegen.c.compiler_runner import compile_c_source
from quest.modules.graph import UnitKind, file_unit_kind
from quest.repl import run_repl
from quest.values.model import QOk, qvalue_to_str
from quest.syntax.sources import SourceMap, os_text, read_source


def report_error(prog: str, error: Exception, source_file: Optional[Path] = None) -> None:
    """Writes an error raised while building or compiling source_file to stderr.
    A compiler error is located in the file it was raised in (an imported
    unit's, or else source_file) with its source line, as the pipeline reports
    errors in programs; any other error is written as its message."""
    if isinstance(error, QuestCompilerError):
        diag = diagnostic_of(error)
        source_map = None
        if diag.source_map is None and source_file is not None:
            try:
                source_map = SourceMap(read_source(source_file), str(source_file))
            except OSError:
                pass
        if diag.source_map is not None or source_map is not None:
            sys.stderr.write(DiagnosticRenderer.render_diagnostic(diag, source_map=source_map) + "\n")
            return
    sys.stderr.write(f"{prog}: error: {error}\n")


def run_unit_phases(prog: str, file_path: Path, parsed_args: argparse.Namespace) -> int:
    """Runs the phases --stop-after and --dump-after name on a unit file,
    compiled as the unit compilers compile it, and writes their output. Writes
    no artifacts of the unit itself. Returns the exit status.

    An interface file's phases end with typecheck, and a module file's with
    codegen_c: a unit does not run alone.
    """
    kind = file_unit_kind(file_path).value
    phases = compile_pipeline().phase_names()
    if kind == "interface":
        phases = phases[:phases.index("typecheck") + 1]
    requested = [p for p in (parsed_args.stop_after, *parsed_args.dump_after) if p is not None]
    for phase in requested:
        if phase not in phases:
            sys.stderr.write(
                f"{prog}: error: phase '{phase}' does not apply to {kind} file '{file_path}', whose phases are "
                f"{', '.join(phases)}\n"
            )
            return 1
    last = max(requested, key=phases.index)

    source_text = read_source(file_path)
    file_name = str(file_path)
    options = CompilerOptions(
        stop_after=last,
        dump_after=set(parsed_args.dump_after),
        include_paths=[Path(p) for p in parsed_args.include_paths],
        show_offsets=getattr(parsed_args, "show_offsets", False),
        show_values=getattr(parsed_args, "show_values", False),
        # Units imported while typechecking are built here, as for a program's
        # phases (docs/build-process.md §5.2.4)
        build_dir=Path(parsed_args.build_dir) if parsed_args.build_dir else Path(".build"),
        unit=kind,
    )
    ctx = CompilerContext.create(source_text, file_name, options=options)
    result = compile_pipeline().execute(source_text, file_name, options=options, ctx=ctx)
    for phase in phases:
        if result.dump_outputs.get(phase):
            sys.stdout.write(result.dump_outputs[phase] + "\n")
    for diag in result.diagnostics:
        sys.stderr.write(DiagnosticRenderer.render_diagnostic(diag, source_map=ctx.source_map) + "\n")
    if any(d.severity == Severity.FATAL for d in result.diagnostics):
        return 70
    return 0 if result.success else 1


def run_unit_file(prog: str, file_path: Path, parsed_args: argparse.Namespace) -> int:
    """Runs the driver, in either mode, on a unit file (an interface or module
    file): dumps the phases --stop-after and --dump-after name
    (run_unit_phases), then, without --stop-after, compiles the unit alone
    (compile_unit_file), reporting any error. Returns the exit status."""
    if parsed_args.stop_after or parsed_args.dump_after:
        status = run_unit_phases(prog, file_path, parsed_args)
        if status != 0 or parsed_args.stop_after:
            return status
    try:
        compile_unit_file(
            file_path,
            include_paths=[Path(p) for p in parsed_args.include_paths],
            build_dir=Path(parsed_args.build_dir) if parsed_args.build_dir else None,
            output=Path(parsed_args.output) if parsed_args.output else None,
            emit_deps=parsed_args.emit_deps,
        )
        return 0
    except Exception as err:
        report_error(prog, err, file_path)
        return 1


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


def run_driver(args: list[str]) -> int:
    """Executes the compiler driver with given CLI argument list."""
    if args and args[0] == "compile":
        return run_compile(args[1:])

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

    driver_args, target_args = split_program_args(arg_parser, args)
    parsed_args = arg_parser.parse_intermixed_args(driver_args)

    # Determine input source and extra objects
    is_inline_code = parsed_args.code is not None
    source_file = None
    extra_objects: list[Path] = []
    for f_str in parsed_args.files:
        p = Path(f_str)
        if p.suffix in OBJECT_SUFFIXES:
            extra_objects.append(p.resolve() if p.exists() else p)
        elif source_file is None:
            source_file = f_str
        else:
            sys.stderr.write(
                f"quest: error: multiple source files specified: '{source_file}' and '{f_str}'\n"
            )
            return 1

    if is_inline_code:
        source_text = os_text(parsed_args.code)
        file_name = "<string>"
    elif source_file is None:
        if parsed_args.interactive or sys.stdin.isatty():
            sys.argv = ["<repl>"] + target_args
            set_system_args(sys.argv)
            return run_repl()
        source_text = sys.stdin.read()
        file_name = "<stdin>"
    elif source_file == "-":
        source_text = sys.stdin.read()
        file_name = "<stdin>"
    else:
        file_path = Path(source_file)
        if not file_path.exists():
            sys.stderr.write(f"quest: error: file not found: '{file_path}'\n")
            return 1
        if file_unit_kind(file_path) != UnitKind.PROGRAM:
            return run_unit_file("quest", file_path, parsed_args)
        try:
            source_text = read_source(file_path)
            file_name = str(file_path)
        except OSError as error:
            sys.stderr.write(f"quest: error reading '{file_path}': {error}\n")
            return 1

    # Configure pipeline and options
    has_output = parsed_args.output is not None
    if (
        has_output
        and not parsed_args.whole_program
        and not parsed_args.stop_after
        and not parsed_args.dump_after
        and not parsed_args.echo
        and source_file not in (None, "-")
        and not is_inline_code
    ):
        file_path = Path(source_file)
        build_dir = Path(parsed_args.build_dir) if parsed_args.build_dir else Path(".build")
        include_paths = [Path(p) for p in parsed_args.include_paths]
        engine = BuildEngine(
            build_dir=build_dir,
            include_paths=include_paths,
            verbose=parsed_args.verbose,
            nogc=False,
            extra_objects=extra_objects,
        )
        try:
            engine.build_main(file_path, output_binary=Path(parsed_args.output))
            return 0
        except Exception as err:
            report_error("quest", err, file_path)
            return 1
    has_objects = bool(extra_objects)
    needs_c_pipeline = (
        has_output
        or has_objects
        or parsed_args.stop_after in ("codegen_c", "run_c_compiled")
        or any(p in ("codegen_c", "run_c_compiled") for p in parsed_args.dump_after)
    )
    if has_output:
        pipeline = compile_pipeline()
    elif needs_c_pipeline:
        pipeline = full_pipeline()
    elif parsed_args.stop_after in IR_RUN_PHASES:
        pipeline = ir_run_pipeline(parsed_args.stop_after.removeprefix("run_ir_"))
    elif parsed_args.stop_after in IR_DUMP_PHASES or any(p in IR_DUMP_PHASES for p in parsed_args.dump_after):
        last = max(
            (IR_DUMP_PHASES.index(p) for p in [parsed_args.stop_after, *parsed_args.dump_after] if p in IR_DUMP_PHASES)
        )
        pipeline = ir_pipeline(IR_DUMP_PHASES[last].removeprefix("ir_"))
    else:
        pipeline = default_pipeline()

    available_phases = pipeline.phase_names()
    stop_after = parsed_args.stop_after
    if has_objects and not has_output and stop_after is None and not parsed_args.dump_after:
        stop_after = "run_c_compiled"
    # Running compiled code, or IR, prints the last phrase's result as the
    # interpreter does
    print_result = (
        parsed_args.print_result or stop_after == "run_c_compiled" or stop_after in IR_RUN_PHASES
    )

    options = CompilerOptions(
        stop_after=stop_after,
        dump_after=set(parsed_args.dump_after),
        include_paths=[Path(p) for p in parsed_args.include_paths],
        echo=parsed_args.echo,
        show_offsets=parsed_args.show_offsets,
        show_values=parsed_args.show_values,
        print_result=print_result,
        target_args=target_args,
        expected_exit=parsed_args.expected_exit,
        extra_objects=extra_objects,
        # Every phase reuses (and builds) interface and module artifacts here
        # (docs/build-process.md §5.2.4).
        build_dir=Path(parsed_args.build_dir) if parsed_args.build_dir else Path(".build"),
        whole_program=parsed_args.whole_program,
        emit_deps=parsed_args.emit_deps,
    )

    sys.argv = [file_name] + target_args
    set_system_args(sys.argv)

    # Execute pipeline
    try:
        ctx = CompilerContext.create(source_text, file_name, options=options)
        ctx.env.units.add_prebuilt_objects(extra_objects, options.include_paths)
        result = pipeline.execute(source_text, file_name, options=options, ctx=ctx)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
        sys.stdout.flush()
        sys.stderr.flush()
        return code

    # Output any requested phase dumps
    for phase_name in available_phases:
        if phase_name in result.dump_outputs:
            out_str = result.dump_outputs[phase_name]
            if out_str:
                sys.stdout.write(out_str + "\n")

    # Print the final phrase result (unless it's ok or already printed via
    # dump/echo)
    if result.success and "interpret" not in result.dump_outputs and not parsed_args.echo:
        typed_prog = result.artifacts.get("typecheck")
        final_phrase = typed_prog.phrases[-1] if typed_prog and typed_prog.phrases else None
        val = result.artifacts.get("interpret")
        if val is not None:
            out_str = format_interactive_result(final_phrase, val)
            if out_str:
                sys.stdout.write(out_str + "\n")

    # Render diagnostics if any occurred
    if result.diagnostics:
        source_map = SourceMap(source_text, file_name)
        for diag in result.diagnostics:
            rendered = DiagnosticRenderer.render_diagnostic(diag, source_map=source_map)
            sys.stderr.write(rendered + "\n")

    # Exit code determination
    if any(d.severity == Severity.FATAL for d in result.diagnostics):
        return 70  # EX_SOFTWARE

    if not result.success:
        return 1

    if has_output:
        c_code = result.artifacts.get("codegen_c")
        if c_code is None:
            return 1
        output_path = Path(parsed_args.output)
        try:
            extra_objs = link_dependencies(ctx)
            compile_c_source(
                c_code,
                output_path=output_path,
                nogc=False,
                extra_objects=extra_objs,
            )
            return 0
        except Exception as error:
            sys.stderr.write(f"quest: error: {error}\n")
            return 1

    # If -i / --interactive was requested with a file, enter REPL with populated
    # context
    if parsed_args.interactive:
        return run_repl(ctx=ctx)

    if parsed_args.expected_exit != 0 and parsed_args.stop_after == "run_c_compiled":
        return parsed_args.expected_exit

    return 0


def run_compile(args: list[str]) -> int:
    """Executes the compile subcommand: translates Quest to C and invokes host
    compiler."""
    pipeline = compile_pipeline()
    available_phases = pipeline.phase_names()

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
        help="Compile without Boehm GC (uses standard libc malloc/free).",
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

    parsed_args = arg_parser.parse_args(args)

    # Determine input source and extra objects
    is_inline_code = parsed_args.code is not None
    source_file = None
    extra_objects: list[Path] = []
    for f_str in parsed_args.files:
        p = Path(f_str)
        if p.suffix in OBJECT_SUFFIXES:
            extra_objects.append(p.resolve() if p.exists() else p)
        elif source_file is None:
            source_file = f_str
        else:
            sys.stderr.write(
                f"quest compile: error: multiple source files specified: '{source_file}' and '{f_str}'\n"
            )
            return 1

    if is_inline_code:
        source_text = os_text(parsed_args.code)
        file_name = "<string>"
        default_out = Path("a.out")
    elif source_file is None:
        if sys.stdin.isatty():
            arg_parser.print_help(sys.stderr)
            return 1
        source_text = sys.stdin.read()
        file_name = "<stdin>"
        default_out = Path("a.out")
    elif source_file == "-":
        source_text = sys.stdin.read()
        file_name = "<stdin>"
        default_out = Path("a.out")
    else:
        file_path = Path(source_file)
        if not file_path.exists():
            sys.stderr.write(f"quest compile: error: file not found: '{file_path}'\n")
            return 1
        if file_unit_kind(file_path) != UnitKind.PROGRAM:
            return run_unit_file("quest compile", file_path, parsed_args)
        try:
            source_text = read_source(file_path)
            file_name = str(file_path)
            if file_path.suffix == ".quest":
                default_out = file_path.with_suffix("")
            else:
                default_out = file_path.with_name(file_path.name + ".bin")
        except OSError as error:
            sys.stderr.write(f"quest compile: error reading '{file_path}': {error}\n")
            return 1

    output_path = Path(parsed_args.output) if parsed_args.output else default_out

    if (
        not parsed_args.whole_program
        and not parsed_args.emit_c
        and not parsed_args.stop_after
        and not parsed_args.dump_after
        and not parsed_args.echo
        and not parsed_args.print_result
        and source_file not in (None, "-")
        and not is_inline_code
    ):
        file_path = Path(source_file)
        build_dir = Path(parsed_args.build_dir) if parsed_args.build_dir else Path(".build")
        include_paths = [Path(p) for p in parsed_args.include_paths]
        engine = BuildEngine(
            build_dir=build_dir,
            include_paths=include_paths,
            verbose=parsed_args.verbose,
            nogc=parsed_args.nogc,
            extra_objects=extra_objects,
        )
        try:
            if parsed_args.compile_only:
                engine.compile_main_unit(Path(file_path).resolve())
            else:
                engine.build_main(file_path, output_binary=output_path)
            return 0
        except Exception as err:
            report_error("quest compile", err, file_path)
            return 1

    options = CompilerOptions(
        stop_after=parsed_args.stop_after,
        dump_after=set(parsed_args.dump_after),
        include_paths=[Path(p) for p in parsed_args.include_paths],
        echo=parsed_args.echo,
        emit_c=parsed_args.emit_c,
        output_path=output_path,
        nogc=parsed_args.nogc,
        print_result=parsed_args.print_result,
        extra_objects=extra_objects,
        # Every phase reuses (and builds) interface and module artifacts here
        # (docs/build-process.md §5.2.4).
        build_dir=Path(parsed_args.build_dir) if parsed_args.build_dir else Path(".build"),
        whole_program=parsed_args.whole_program,
    )

    ctx = CompilerContext.create(source_text, file_name, options=options)
    ctx.env.units.add_prebuilt_objects(extra_objects, options.include_paths)
    result = pipeline.execute(source_text, file_name, options=options, ctx=ctx)

    for phase_name in available_phases:
        if phase_name in result.dump_outputs:
            out_str = result.dump_outputs[phase_name]
            if out_str:
                sys.stdout.write(out_str + "\n")

    if result.diagnostics:
        source_map = SourceMap(source_text, file_name)
        for diag in result.diagnostics:
            rendered = DiagnosticRenderer.render_diagnostic(diag, source_map=source_map)
            sys.stderr.write(rendered + "\n")

    if any(d.severity == Severity.FATAL for d in result.diagnostics):
        return 70

    if not result.success:
        return 1

    # A phase stopped after has been dumped; codegen_c's dump is the C
    if parsed_args.stop_after:
        return 0

    c_code = result.artifacts.get("codegen_c")
    if c_code is None:
        return 1

    if parsed_args.emit_c:
        if parsed_args.output:
            try:
                output_path.write_text(c_code, encoding="utf-8")
            except OSError as error:
                sys.stderr.write(f"quest compile: error writing '{output_path}': {error}\n")
                return 1
        else:
            sys.stdout.write(c_code)
        return 0

    try:
        extra_objs = link_dependencies(ctx)
        compile_c_source(
            c_code,
            output_path=output_path,
            nogc=parsed_args.nogc,
            extra_objects=extra_objs,
        )
    except Exception as error:
        sys.stderr.write(f"quest compile: error: {error}\n")
        return 1

    return 0


def main() -> int:
    use_byte_streams()
    return run_driver(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
