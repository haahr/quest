"""The bootstrap compiler's command-line driver, which ./questboot runs
(through bootstrap/python/quest_driver.py).

run_driver interprets a program, compiles and runs it, dumps its phases
(--stop-after, --dump-after), or starts the REPL; run_compile (`questboot
compile`) compiles a program to a binary or to C. The self-hosted counterpart
is questlang/driver/main; docs/pipeline.md §4 describes the command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from quest.interpreter.builtins import set_system_args, use_byte_streams
from quest.common.diagnostics import DiagnosticRenderer, QuestCompilerError, Severity, diagnostic_of
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
from quest.build.compiler_runner import compile_c_source
from quest.modules.graph import UnitKind, file_unit_kind
from quest.driver.options import OBJECT_SUFFIXES, compile_parser, driver_parser, split_program_args
from quest.driver.repl import run_repl
from quest.common.location import SourceMap, os_text, read_source


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


def run_driver(args: list[str]) -> int:
    """Runs the bootstrap driver (./questboot) on the command line args, without
    the program name, and returns the exit status. Its self-hosted counterpart
    is questlang/driver/main.quest; docs/pipeline.md §4 describes the command
    line.

    It decides what to do in this order:

    1. A first argument `compile` hands the rest to run_compile, which
       translates the program to C and compiles it.
    2. The arguments after the program file (or after `--`) are the program's,
       not the driver's (split_program_args); system.args is the source's
       name followed by them.
    3. Files ending in .o, .a, .dylib or .so are objects to link with the
       program; at most one other file is the source.
    4. The source is the -e code if given. Without a file, the driver enters
       the REPL (docs/repl.md §2.1) if -i is given or standard input is a
       terminal, and otherwise reads the program from standard input, as it
       does for the file `-`. An interface or module file goes to
       run_unit_file, which dumps its phases or compiles it alone, and
       returns.
    5. A program file with -o, and without --whole-program, --stop-after,
       --dump-after or --echo, is built by the BuildEngine with separate
       compilation: each imported module is compiled to its own object in the
       build directory (default .build), reused while fresh, and linked
       (docs/build-process.md §1.1).
    6. Otherwise one pipeline runs the whole program: with -o, through C
       (compile_pipeline), the C then compiled and linked here; with objects
       or a codegen_c or run_c_compiled phase, through C and running the
       compiled program (full_pipeline); with --stop-after run_ir_STAGE,
       through the IR to STAGE and running it in the IR interpreter; with an
       ir_STAGE phase, through the IR to the latest stage asked for; and by
       default through the tree-walking interpreter. Objects given without -o
       or a phase make the run stop after run_c_compiled: the program is
       compiled, linked with them, and run.

    After the pipeline, the driver writes the requested dumps in phase order,
    then the last phrase's result when the program was interpreted (unless
    --echo or an interpret dump printed it already), then the diagnostics. The
    status is the program's own if it called exit, 70 (EX_SOFTWARE) for an
    internal compiler error, 1 for any other error (a compiled run whose exit
    status is not --expected-exit among them), --expected-exit after a
    successful --stop-after run_c_compiled, and 0 otherwise; with -i the REPL
    then starts in the program's environment (docs/repl.md §2.2). The
    pipeline phases use and build imported units' artifacts in the build
    directory (docs/build-process.md §5.2.4) even when nothing is written.
    """
    if args and args[0] == "compile":
        return run_compile(args[1:])

    arg_parser = driver_parser()

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

    # Configure pipeline and options. A program file built to -o takes the
    # separate-compilation path and returns here; everything else runs one
    # pipeline below
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
    )

    sys.argv = [file_name] + target_args
    set_system_args(sys.argv)

    # Execute pipeline
    try:
        ctx = CompilerContext.create(source_text, file_name, options=options)
        ctx.env.units.add_prebuilt_objects(extra_objects, options.include_paths)
        # The file -i runs is interactive, the REPL's first input
        # (docs/repl.md section 6)
        ctx.env.interactive = parsed_args.interactive
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
    """Runs `questboot compile` on its arguments args (the command line after
    `compile`), which compiles a program to a binary or to C, and returns the
    exit status. docs/pipeline.md §4.2 describes the command line.

    - Files ending in .o, .a, .dylib, or .so are objects to link; at most one
      other file is the source, or the -e code, or standard input (`-`, or no
      file when standard input is not a terminal). An interface or module file
      goes to run_unit_file, which compiles it alone.
    - A program file without --whole-program, --emit-c, --stop-after,
      --dump-after, --echo, or --print-result is built by the BuildEngine with
      separate compilation (docs/build-process.md §1.1); with -c it is
      compiled to an object but not linked.
    - Otherwise the compile pipeline translates the whole program to C, and
      prints the dumps asked for and the diagnostics. Unless it stopped after
      a phase, the C is written (--emit-c: to -o, or to standard output), or
      compiled by the host C compiler and linked with the modules it imports,
      built as separate compilation builds them, and the objects given.

    The binary is -o, or the source's name without .quest (a.out for -e code
    or standard input). The status is 0 on success, 70 (EX_SOFTWARE) for an
    internal compiler error, and 1 for any other error. Unlike run_driver, it
    never runs the program."""
    pipeline = compile_pipeline()
    available_phases = pipeline.phase_names()

    arg_parser = compile_parser(available_phases)

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
