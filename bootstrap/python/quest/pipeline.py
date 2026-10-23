"""Quest Compiler Phase Pipeline Framework.

Provides uniform lifecycle management, execution, and artifact inspection
across compiler phases (tokenize, parse, typecheck, interpret, codegen).
"""

from __future__ import annotations

import sys
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from quest.build.engine import BuildEngine, unit_module_refs
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.codegen.backend import IR_PASSES
from quest.codegen.compiler_runner import compile_c_source, run_binary
from quest.config import CompilerOptions

import quest.syntax.ast as ast
from quest.diagnostics import (
    diagnostic_of,
    Diagnostic,
    DiagnosticSink,
    FatalDiagnosticError,
    QuestCompilerError,
    Severity,
)
from quest.elaborate_types import elaborate_kind, elaborate_type
from quest.env import Environment, Scope
from quest.syntax.grammar import parse_quest_program
from quest.interpreter.treewalk import (
    QuestRuntimeError,
    RuntimeEnvironment,
    eval_binding,
    eval_expr,
    eval_program,
    eval_program_phrases,
    format_interactive_result,
)
from quest.values.model import QuestException, OK_VALUE, QOk, QValue, qvalue_to_str
from quest.syntax.parser import ParserError
from quest.syntax.tokenizer import Tokenizer, TokenizerError
from quest.syntax.sources import SourceMap
from quest.syntax.tokens import Token, TokenKind
from quest.typechecker.typecheck import (
    elaborate_phrase,
    elaborate_program,
    synth_expr,
)
from quest.typed_ast import TypedBinding, TypedExpr, TypedImport, TypedModule, TypedProgram
from quest.types import KindError, QKind, QType


@dataclass
class CompilerContext:
    """Shared state passed through all stages of a compilation session."""
    source_text: str
    file_name: str
    source_map: SourceMap
    sink: DiagnosticSink = field(default_factory=DiagnosticSink)
    env: Environment = field(default_factory=Environment)
    options: CompilerOptions = field(default_factory=CompilerOptions)
    _runtime_env: Optional[RuntimeEnvironment] = field(default=None, repr=False)
    # Modules the generated C unit links against; set by CodegenCPhase (see link_dependencies).
    imported_modules: list[Any] = field(default_factory=list)
    # The typed program, kept by IrCorePhase for the IR's C backend (its imports, for linking)
    typed_program: Optional[Any] = None

    @property
    def runtime_env(self) -> RuntimeEnvironment:
        if self._runtime_env is None:
            r_env = RuntimeEnvironment.create_root_env()
            self._configure_runtime_env(r_env)
            self._runtime_env = r_env
        return self._runtime_env

    @runtime_env.setter
    def runtime_env(self, value: Optional[RuntimeEnvironment]) -> None:
        self._runtime_env = value
        if value is not None:
            self._configure_runtime_env(value)

    def _configure_runtime_env(self, r_env: RuntimeEnvironment) -> None:
        r_env.include_paths = list(self.env.include_paths)
        r_env.loaded_modules_ast = self.env.loaded_modules_ast
        r_env.current_dir = self.env.current_dir
        r_env.program_dir = self.env.program_dir

    @classmethod
    def create(
        cls,
        source_text: str,
        file_name: str = "<stdin>",
        options: Optional[CompilerOptions] = None,
        env: Optional[Environment] = None,
        runtime_env: Optional[RuntimeEnvironment] = None,
    ) -> CompilerContext:
        """Constructs a fresh CompilerContext with initialized SourceMap."""
        opts = options or CompilerOptions()
        environment = env if env is not None else Environment(builtin_registry=BuiltinModuleRegistry)

        # Wire include_paths and current_dir
        environment.options = opts
        if opts.build_dir is None and opts.is_c_compilation_mode:
            # Separate compilation always has a build directory, so that nested interface and module
            # compilations agree on where artifacts live (docs/build-process.md §3.1).
            opts.build_dir = Path(".build")
        environment.include_paths = list(opts.include_paths)
        if opts.build_dir and Path(opts.build_dir).resolve() not in [p.resolve() for p in environment.include_paths]:
            environment.include_paths.insert(0, Path(opts.build_dir).resolve())

        if file_name and not file_name.startswith("<"):
            try:
                p = Path(file_name).resolve()
                current_dir = p.parent
                environment.current_dir = current_dir
            except (OSError, RuntimeError):
                cwd = Path.cwd()
                environment.current_dir = cwd
        elif environment.current_dir is None:
            cwd = Path.cwd()
            environment.current_dir = cwd
        if environment.program_dir is None:
            environment.program_dir = environment.current_dir
        opts.current_dir = environment.current_dir
        opts.program_dir = environment.program_dir

        source_map = SourceMap(source_text, file_name)
        sink = DiagnosticSink()
        environment.sink = sink
        environment.source_map = source_map
        ctx = cls(
            source_text=source_text,
            file_name=file_name,
            source_map=source_map,
            sink=sink,
            env=environment,
            options=opts,
            _runtime_env=runtime_env,
        )
        if runtime_env is not None:
            ctx._configure_runtime_env(runtime_env)
        return ctx


@dataclass
class PipelineResult:
    """Summary of a pipeline execution session."""
    success: bool
    final_phase: Optional[str]
    artifacts: dict[str, Any] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    dump_outputs: dict[str, str] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(d.severity in (Severity.ERROR, Severity.FATAL) for d in self.diagnostics)

    @property
    def final_artifact(self) -> Optional[Any]:
        if self.final_phase and self.final_phase in self.artifacts:
            return self.artifacts[self.final_phase]
        return None


class Phase(ABC):
    """Abstract base class for a discrete compiler transformation pass."""
    name: str
    description: str
    artifact_name: str

    @abstractmethod
    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        """Executes the phase on input_data. Returns output artifact or None on failure."""
        pass

    @abstractmethod
    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        """Renders the output artifact as canonical human-readable or golden-test text."""
        pass


class TokenizePhase(Phase):
    """Lexical analysis phase: converts source text into token stream."""
    name = "tokenize"
    description = "Tokenize source text into lexical tokens"
    artifact_name = "tokens"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[list[Token]]:
        source_text = str(input_data)
        tokenizer = Tokenizer(source_text, ctx.file_name)
        try:
            return tokenizer.tokenize_all()
        except QuestCompilerError as error:
            ctx.sink.emit(diagnostic_of(error))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        tokens: list[Token] = output_data
        lines: list[str] = []
        for token in tokens:
            loc = ctx.source_map.locate(token.offset)
            pos_str = f"{loc.line}:{loc.column}"
            if token.kind == TokenKind.EOF:
                lines.append(f"{pos_str}\t{token.kind.name}")
                break
            if ctx.options.show_values and token.value is not None:
                lines.append(f"{pos_str}\t{token.kind.name}\t{token.lexeme}\t(value={token.value!r})")
            else:
                lines.append(f"{pos_str}\t{token.kind.name}\t{token.lexeme}")
        return "\n".join(lines)


class ParsePhase(Phase):
    """Syntactic analysis phase: parses token stream into untyped AST."""
    name = "parse"
    description = "Parse token stream into untyped S-expression AST"
    artifact_name = "ast"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        tokens: list[Token] = input_data
        try:
            return parse_quest_program(tokens, ctx.source_map, target=ctx.options.target)
        except QuestCompilerError as error:
            ctx.sink.emit(diagnostic_of(error))
            return None
        except (ValueError, TypeError) as error:
            ctx.sink.emit(Diagnostic.make_from_exception(error, 0))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        if isinstance(output_data, ast.ASTNode):
            return ast.ast_dump(output_data, show_offsets=ctx.options.show_offsets)
        return str(output_data)


class TypecheckPhase(Phase):
    """Semantic analysis phase: elaborates AST into typed AST."""
    name = "typecheck"
    description = "Elaborate AST terms and kinds into typed AST"
    artifact_name = "typed_ast"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        try:
            match input_data:
                case ast.Program():
                    return elaborate_program(input_data, ctx.env)
                case ast.Expr():
                    return synth_expr(input_data, ctx.env)
                case ast.Type():
                    return elaborate_type(input_data, ctx.env)
                case ast.Kind():
                    return elaborate_kind(input_data, ctx.env)
                case ast.ASTNode():
                    return elaborate_phrase(input_data, ctx.env)
                case _:
                    return input_data
        except QuestCompilerError as error:
            ctx.sink.emit(diagnostic_of(error))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        if hasattr(output_data, "dump"):
            try:
                return output_data.dump(env=ctx.env)
            except TypeError:
                return output_data.dump()
        return str(output_data)


class InterpretPhase(Phase):
    """Interpretation phase: evaluates typed AST in tree-walking interpreter."""
    name = "interpret"
    description = "Evaluate typed AST in tree-walking interpreter"
    artifact_name = "value"

    def __init__(self) -> None:
        self._last_final_phrase: Optional[TypedBinding | TypedExpr] = None
        self._last_phrase_results: list[tuple[TypedBinding | TypedExpr, QValue]] = []

    @property
    def last_phrase_results(self) -> list[tuple[TypedBinding | TypedExpr, QValue]]:
        return self._last_phrase_results

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[QValue]:
        try:
            match input_data:
                case TypedProgram():
                    if input_data.phrases:
                        self._last_final_phrase = input_data.phrases[-1]
                    else:
                        self._last_final_phrase = None
                    def echo(phrase: TypedBinding | TypedExpr, val: QValue) -> None:
                        out_str = format_interactive_result(phrase, val)
                        if out_str:
                            sys.stdout.write(out_str + "\n")

                    self._last_phrase_results = eval_program_phrases(
                        input_data, ctx.runtime_env, on_result=echo if ctx.options.echo else None
                    )
                    return self._last_phrase_results[-1][1] if self._last_phrase_results else OK_VALUE

                case TypedExpr():
                    self._last_final_phrase = input_data
                    val = eval_expr(input_data, ctx.runtime_env)
                    self._last_phrase_results = [(input_data, val)]
                    if ctx.options.echo:
                        out_str = format_interactive_result(input_data, val)
                        if out_str:
                            sys.stdout.write(out_str + "\n")
                    return val

                case TypedBinding():
                    self._last_final_phrase = input_data
                    val = eval_binding(input_data, ctx.runtime_env)
                    self._last_phrase_results = [(input_data, val)]
                    if ctx.options.echo:
                        out_str = format_interactive_result(input_data, val)
                        if out_str:
                            sys.stdout.write(out_str + "\n")
                    return val

                case QType() | QKind():
                    self._last_final_phrase = None
                    self._last_phrase_results = []
                    return OK_VALUE

                case _:
                    self._last_final_phrase = None
                    self._last_phrase_results = []
                    return OK_VALUE
        except QuestCompilerError as error:
            ctx.sink.emit(diagnostic_of(error))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        val: QValue = output_data
        if ctx.options.echo:
            return ""  # run already echoed every phrase's result, the last one included
        if self._last_final_phrase is not None:
            return format_interactive_result(self._last_final_phrase, val)
        return qvalue_to_str(val)


def link_dependencies(ctx: CompilerContext) -> list[Path]:
    """Builds the modules a C unit produced by CodegenCPhase imports, returning the objects to link.

    Delegates to the BuildEngine, so that staleness checks, artifact placement, and object collection
    are the same as for a full application build (docs/build-process.md §7.3).
    """
    opts = ctx.options
    engine = BuildEngine(
        build_dir=opts.build_dir,
        include_paths=list(opts.include_paths),
        nogc=opts.nogc,
        extra_objects=list(opts.extra_objects),
    )
    importer = Path(ctx.file_name).stem if not ctx.file_name.startswith("<") else ctx.file_name
    return engine.build_modules(ctx.imported_modules, importer=importer, program_dir=ctx.env.program_dir)


class IrCorePhase(Phase):
    """Lowering to the IR's Core stage (docs/ir.md), the first step of C compilation."""
    name = "ir_core"
    description = "Lower the typed AST to Core IR"
    artifact_name = "ir_unit"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        from quest.ir.lower import lower_program
        from quest.ir.verify import check_unit, ir_checks_enabled

        try:
            prog = input_data if isinstance(input_data, TypedProgram) else TypedProgram(phrases=(input_data,))
            ctx.typed_program = prog
            unit = lower_program(
                prog, ctx.env, echo=ctx.options.echo, print_result=getattr(ctx.options, "print_result", False)
            )
            if ir_checks_enabled():
                check_unit(unit)
            return unit
        except Exception as error:
            ctx.sink.emit(Diagnostic.make_from_exception(error, 0))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        from quest.ir.printer import format_unit

        return format_unit(output_data) if output_data is not None else ""


class IrPassPhase(Phase):
    """An IR pass, producing the IR at its stage (docs/ir.md §8, §9), verified when QUEST_CHECK_IR=1."""
    artifact_name = "ir_unit"

    def __init__(self, stage: str, run_pass: Any) -> None:
        self.name = f"ir_{stage}"
        self.description = f"Run the IR pass producing the {stage} stage"
        self.run_pass = run_pass

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        from quest.ir.verify import check_unit, ir_checks_enabled

        if input_data is None:
            return None
        try:
            unit = self.run_pass(input_data)
            if ir_checks_enabled():
                check_unit(unit)
            return unit
        except Exception as error:
            ctx.sink.emit(Diagnostic.make_from_exception(error, 0))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        from quest.ir.printer import format_unit

        return format_unit(output_data) if output_data is not None else ""


class RunIrPhase(Phase):
    """Runs the IR in the IR interpreter (quest/interpreter/ir_interp.py), a test oracle for the lowering and the
    passes: its output is compared with the source interpreter's. The IR prints the program's results itself."""
    artifact_name = "ir_run"

    def __init__(self, stage: str) -> None:
        self.name = f"run_ir_{stage}"
        self.description = f"Run the IR at its {stage} stage in the IR interpreter"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[Any]:
        from quest.interpreter.ir_interp import run_unit

        if input_data is None:
            return None
        try:
            run_unit(input_data, ctx.runtime_env)
            return OK_VALUE
        except QuestCompilerError as error:
            ctx.sink.emit(diagnostic_of(error))
            return None

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        return ""


class CodegenCPhase(Phase):
    """C code generation: prints the represented IR as C99 source code (docs/ir.md §8.5)."""
    name = "codegen_c"
    description = "Print the represented IR as C99 source code"
    artifact_name = "c_source"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[str]:
        from quest.codegen.backend import implicit_imports
        from quest.codegen.c_printer import print_c

        if input_data is None:
            return None
        try:
            unit = input_data
            c_code = print_c(unit, ctx.env)
        except Exception as error:
            ctx.sink.emit(Diagnostic.make_from_exception(error, 0))
            return None
        prog = ctx.typed_program
        import_items = [it for phrase in prog.phrases if isinstance(phrase, TypedImport) for it in phrase.items]
        ctx.imported_modules = unit_module_refs(
            import_items, implicit_imports(unit, prog), ctx.env.current_dir, ctx.env.include_paths,
            ctx.env.program_dir,
        )
        return c_code

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        return str(output_data) if output_data is not None else ""


class RunCCompiledPhase(Phase):
    """Native binary execution phase: compiles C code and runs the resulting binary."""
    name = "run_c_compiled"
    description = "Compile C code to native binary and execute it"
    artifact_name = "stdout"

    def run(self, input_data: Any, ctx: CompilerContext) -> Optional[str]:
        if not isinstance(input_data, str):
            return None

        c_code: str = input_data
        with tempfile.NamedTemporaryFile(suffix="", delete=False) as tmp_file:
            bin_path = Path(tmp_file.name)

        try:
            extra_objs = link_dependencies(ctx)
            compile_c_source(
                c_code,
                output_path=bin_path,
                nogc=ctx.options.nogc,
                extra_objects=extra_objs,
            )
            proc = run_binary(
                bin_path,
                args=ctx.options.target_args,
                env=ctx.options.target_env,
                input_data=ctx.options.target_stdin,
            )
            if proc.returncode != ctx.options.expected_exit:
                msg = proc.stderr.strip() if proc.stderr else f"Binary exited with code {proc.returncode}"
                ctx.sink.emit(Diagnostic.make_error(msg, 0))
            return proc.stdout
        except QuestCompilerError as error:
            # Such as a type error in an imported module's body, found when the module is compiled
            ctx.sink.emit(diagnostic_of(error))
            return None
        except Exception as error:
            ctx.sink.emit(Diagnostic.make_from_exception(error, 0))
            return None
        finally:
            if bin_path.exists():
                try:
                    bin_path.unlink()
                except OSError:
                    pass

    def dump(self, output_data: Any, ctx: CompilerContext) -> str:
        if output_data is None:
            return ""
        s = str(output_data)
        return s[:-1] if s.endswith("\n") else s


class PhasePipeline:
    """Manages sequential execution of registered compiler phases."""

    def __init__(self, phases: Optional[list[Phase]] = None) -> None:
        self.phases: list[Phase] = phases or []

    def register(self, phase: Phase) -> None:
        """Appends a phase to the pipeline."""
        self.phases.append(phase)

    def phase_names(self) -> list[str]:
        """Returns the ordered list of registered phase names."""
        return [p.name for p in self.phases]

    def get_phase(self, name: str) -> Optional[Phase]:
        """Looks up a registered phase by name."""
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None

    def precursors_of(self, target_name: str) -> list[str]:
        """Returns the names of all phases strictly preceding target_name."""
        names = self.phase_names()
        if target_name not in names:
            raise ValueError(f"Unknown phase '{target_name}'. Available: {names}")
        idx = names.index(target_name)
        return names[:idx]

    def execute(
        self,
        source_text: str,
        file_name: str = "<stdin>",
        options: Optional[CompilerOptions] = None,
        ctx: Optional[CompilerContext] = None,
        target: Optional[Any] = None,
    ) -> PipelineResult:
        """Executes the pipeline on source_text."""
        opts = options or CompilerOptions()
        if target is not None:
            opts.target = target
        context = ctx or CompilerContext.create(source_text, file_name, opts)
        context.options = opts

        current_data: Any = source_text
        artifacts: dict[str, Any] = {}
        dump_outputs: dict[str, str] = {}
        final_phase: Optional[str] = None

        try:
            for phase in self.phases:
                final_phase = phase.name

                # Run phase
                current_data = phase.run(current_data, context)
                if current_data is not None:
                    artifacts[phase.name] = current_data

                # Check if dump requested via --dump-after or --stop-after
                should_dump = (phase.name in opts.dump_after) or (opts.stop_after == phase.name)
                if should_dump and current_data is not None:
                    dump_outputs[phase.name] = phase.dump(current_data, context)

                # Halt if phase encountered errors or reached --stop-after
                if context.sink.has_errors:
                    break
                if opts.stop_after == phase.name:
                    break

        except FatalDiagnosticError as fatal_err:
            # Fatal diagnostic already recorded in sink
            pass

        return PipelineResult(
            success=not context.sink.has_errors,
            final_phase=final_phase,
            artifacts=artifacts,
            diagnostics=list(context.sink.diagnostics),
            dump_outputs=dump_outputs,
        )

    def compile_file(
        self,
        path: Path,
        options: Optional[CompilerOptions] = None,
        ctx: Optional[CompilerContext] = None,
    ) -> PipelineResult:
        """Executes the pipeline on a file from disk."""
        source_text = path.read_text(encoding="utf-8")
        return self.execute(source_text, str(path), options=options, ctx=ctx)

    def compile_phrase(
        self,
        phrase_text: str,
        options: Optional[CompilerOptions] = None,
        ctx: Optional[CompilerContext] = None,
    ) -> PipelineResult:
        """Executes the pipeline on an interactive REPL phrase, preserving context."""
        context = ctx or CompilerContext.create(phrase_text, "<repl>", options=options)
        context.sink = DiagnosticSink()
        context.env.sink = context.sink
        # Update source_text and source_map for this specific phrase
        context.source_text = phrase_text
        context.source_map = SourceMap(phrase_text, context.file_name)
        return self.execute(phrase_text, context.file_name, options=options, ctx=context)


def default_pipeline() -> PhasePipeline:
    """Returns the standard compiler pipeline containing all active phases."""
    pipeline = PhasePipeline()
    pipeline.register(TokenizePhase())
    pipeline.register(ParsePhase())
    pipeline.register(TypecheckPhase())
    pipeline.register(InterpretPhase())
    return pipeline


# The IR's stages (docs/ir.md §9, quest.ir.nodes.STAGES), in order: Core, then those the passes produce
IR_STAGES = ("core", *(stage for stage, _ in IR_PASSES))
IR_DUMP_PHASES = tuple(f"ir_{stage}" for stage in IR_STAGES)
IR_RUN_PHASES = tuple(f"run_ir_{stage}" for stage in IR_STAGES)


def ir_pipeline(stage: str = "core") -> PhasePipeline:
    """Returns the pipeline lowering to IR and running its passes up to the given stage (Tokenize -> Parse ->
    Typecheck -> IrCore -> ...)."""
    if stage not in IR_STAGES:
        raise ValueError(f"no IR stage '{stage}'")
    pipeline = PhasePipeline()
    pipeline.register(TokenizePhase())
    pipeline.register(ParsePhase())
    pipeline.register(TypecheckPhase())
    pipeline.register(IrCorePhase())
    for pass_stage, run_pass in IR_PASSES[:IR_STAGES.index(stage)]:
        pipeline.register(IrPassPhase(pass_stage, run_pass))
    return pipeline


def ir_run_pipeline(stage: str) -> PhasePipeline:
    """Returns the pipeline lowering to IR, running its passes up to the given stage, and running it in the IR
    interpreter."""
    pipeline = ir_pipeline(stage)
    pipeline.register(RunIrPhase(stage))
    return pipeline


def compile_pipeline() -> PhasePipeline:
    """Returns the C compilation pipeline: through the IR's passes to C (Tokenize -> Parse -> Typecheck -> IrCore ->
    the IR passes -> CodegenC)."""
    pipeline = ir_pipeline(IR_STAGES[-1])
    pipeline.register(CodegenCPhase())
    return pipeline


def full_pipeline() -> PhasePipeline:
    """Returns the full C compilation and execution pipeline."""
    pipeline = compile_pipeline()
    pipeline.register(RunCCompiledPhase())
    return pipeline


