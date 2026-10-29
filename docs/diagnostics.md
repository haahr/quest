# Quest Diagnostic, Error, and Warning Handling Architecture

This document specifies the comprehensive design for diagnostics, error reporting, warnings, error recovery, and
runtime error handling across the Quest compiler, interpreter, and REPL.

---

## 1. Design Goals and Principles

1. **Lightweight Offset Tracking:** Every error or warning identifies its location using a 0-indexed character offset
   in the source text, mapping to `(file, line, column)` coordinates on demand via `SourceMap`.
2. **Clear Separation of Problem, Context, and Remedy:**
   - **Problem (`Severity`):** The operational status (`FATAL`, `ERROR`, `WARNING`, `INFO`).
   - **Context (`notes` & `secondary_labels`):** Explanatory source positions and background information (e.g. "type
     defined here", "previously declared here").
   - **Remedy (`help_text` & `suggestions`):** Prescriptive advice or machine-applicable code replacements.
3. **Several Errors, No Cascades:** The self-hosted type checker reports every independent error it can find in a
   unit rather than stopping at the first, and binds the names a failed declaration declares to poisoned symbols so
   that one error does not cause others (§4.5). The bootstrap stops at the first error, which the self-hosted checker
   reports first.
4. **Immediate Fatal Abort with Full Prior Diagnostic Reporting:** Unrecoverable conditions (such as Internal Compiler
   Errors) emit a `FATAL` diagnostic which raises a `FatalDiagnosticError`. The outermost driver catches this exception
   and renders all prior accumulated diagnostics alongside the fatal diagnostic before terminating.
5. **Human and Machine Readability:** Formatter supports terminal rendering (with ANSI color highlighting and
   ASCII/Unicode source box gutters) as well as structured JSON/LSP output.
6. **Quest-Aware Runtime Stack Traces:** Runtime errors in the tree-walking interpreter provide native Quest call stack
   traces with source locations, function names, and callee expressions.

---

## 2. Core Diagnostic Data Structures

### 2.1. Severity
```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any, Callable

class Severity(Enum):
    """Operational severity of a diagnostic message."""
    FATAL = "fatal"      # Unrecoverable error / Internal Compiler Error (ICE); stops all passes
    ERROR = "error"      # User error; compilation proceeds to collect more errors if possible
    WARNING = "warning"  # Compilation proceeds; potential bug or style issue
    INFO = "info"        # Informational note or statistic
```

### 2.2. Labels and Actionable Suggestions
```python
@dataclass(frozen=True)
class DiagnosticLabel:
    """An annotated source position highlighting code context within a diagnostic."""
    offset: int
    length: int = 1
    message: Optional[str] = None
    is_primary: bool = True

@dataclass(frozen=True)
class CodeSuggestion:
    """An actionable fix that can be automatically applied by an IDE/LSP or displayed as a diff."""
    offset: int
    length: int
    replacement: str
    description: str
```

### 2.3. The `Diagnostic` Object and Fatal Exception
```python
@dataclass
class Diagnostic:
    severity: Severity                                # FATAL, ERROR, WARNING, or INFO
    message: str                                      # Primary error description
    primary_label: Optional[DiagnosticLabel] = None   # Underline on faulty code (if source-linked)
    secondary_labels: list[DiagnosticLabel] = field(
        default_factory=list
    )                                                 # Contextual positions (e.g. "type defined here")
    notes: list[str] = field(default_factory=list)    # Explanatory background facts
    help_text: Optional[str] = None                   # Actionable human advice
    suggestions: list[CodeSuggestion] = field(
        default_factory=list
    )                                                 # Machine-applicable quick-fixes
    error_code: Optional[str] = None                  # e.g., "E0102" or "ICE9001"

class FatalDiagnosticError(Exception):
    """Raised immediately by DiagnosticSink when a FATAL diagnostic is emitted."""
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic
```

---

## 3. Diagnostic Sink & Reporting Pipeline

### 3.1. `DiagnosticSink`
Instead of exclusively raising arbitrary exceptions, compiler passes emit diagnostics to a `DiagnosticSink`:

```
+----------------+       emit(diag)       +-------------------+
| Compiler Pass  | ---------------------> |  DiagnosticSink   |
| (Typechecker / |                        |  - errors: list   |
|  Elaborator)   | <--------------------- |  - warnings: list |
+----------------+   has_errors?          +-------------------+
        |                                           |
        | FATAL emitted?                            | render(source_map)
        v (raises FatalDiagnosticError)             v
+------------------------------------+    +-------------------+
| Outermost Driver (catches fatal,   | -> | Terminal / Stream |
| prints accumulated diagnostics)    |    +-------------------+
+------------------------------------+
```

```python
class DiagnosticSink:
    """Collects diagnostics during compilation phases."""
    def __init__(self, fail_fast: bool = False, warnings_as_errors: bool = False):
        self.diagnostics: list[Diagnostic] = []
        self.fail_fast = fail_fast
        self.warnings_as_errors = warnings_as_errors

    def emit(self, diag: Diagnostic) -> None:
        self.diagnostics.append(diag)
        if diag.severity == Severity.FATAL:
            raise FatalDiagnosticError(diag)
        if self.fail_fast and diag.severity == Severity.ERROR:
            raise FatalDiagnosticError(diag)

    @property
    def has_errors(self) -> bool:
        return any(
            d.severity in (Severity.FATAL, Severity.ERROR)
            or (self.warnings_as_errors and d.severity == Severity.WARNING)
            for d in self.diagnostics
        )

    @property
    def error_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity in (Severity.FATAL, Severity.ERROR))

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self.diagnostics if d.severity == Severity.WARNING)
```

### 3.2. Outermost Driver Handling
```python
def compile_stream(source_text: str, file_name: str) -> int:
    source_map = SourceMap(source_text, file_name)
    sink = DiagnosticSink()
    try:
        tokens = tokenize_with_sink(source_text, file_name, sink)
        tree = parse_with_sink(tokens, source_map, sink)
        typed_tree = elaborate_with_sink(tree, env, sink)
        if sink.has_errors:
            render_diagnostics(sink, source_map)
            return 1
        return 0
    except FatalDiagnosticError:
        # Render all diagnostics accumulated up to the fatal error, including the fatal error itself
        render_diagnostics(sink, source_map)
        return 2
```

---

## 4. Phase-by-Phase Diagnostic Strategy

### 4.1. Tokenizer & Parser
- **Tokenizer:**
  - Errors: Invalid characters, unterminated string literals, unterminated block comments `(* ... *)`, malformed
    numeric literals.
  - Recovery: Tokenizer can emit an `ERROR_TOKEN` and continue to find other lexical issues, or fail-fast on malformed
    files.
- **Parser (PEG / Packrat):**
  - Errors: Syntax errors at the furthest parsed token offset.
  - Information: Expected token kinds vs encountered token kind.

### 4.2. Kind & Type Elaboration
- **The first error, or several.** The bootstrap raises `QuestTypeError` at the first type error, and the pipeline
  reports it. The self-hosted checker reports that error first, with the same message and span, and goes on to find
  others (§4.5).
- **Compiler Warnings:**
  - **Unused Local Bindings:** `let unused = ...` where `unused` is never read in scope.
  - **Variable Shadowing:** Declaring `let x = ...` when an outer `x` is in scope (configurable warning).
  - **Unreachable Code:** Expressions appearing after `exit` or `raise` within a block.
  - **Redundant Explicit Dereferencing:** Using `@var` in an expression where implicit dereference occurs.
  - **Incomplete Pattern Matching:** Warning if a `case` or `inspect` omits branches and lacks an `else` branch.
- **Internal Compiler Errors (`FATAL`):**
  - AST node invariant violations (e.g. malformed synthetic nodes or missing type annotations during lowering).

### 4.3. Runtime Interpreter & Execution
Runtime errors are divided into two categories:

#### 1. Language-Level Quest Exceptions (`TypedRaise` / `TypedTry`)
- User-defined exceptions declared with `let exc = exception E: T end` (or `exception E: T end`) and raised via
  `raise exc with payload end`.
- Caught by `try ... when exc with p then ... end`.
- If uncaught, the exception is reported as a located error at the site it was raised, with the source line, followed
  by the Quest functions running there, most recent first ([exceptions.md](exceptions.md) §2):
  ```
  stack.mod.quest:18:9: error: Exception: stack.underflow
          raise underflow end
          ^
    in stack.pop
    in run
    in <main>
  ```
  Every backend reports the same exception and site. The interpreters list every frame; compiled code lists only
  some of them, those the C compiler did not inline or turn into jumps (exceptions.md §2.4).

#### 2. System / Language Invariant Violations
- **Division by Zero:** `x / 0` or `x mod 0`.
- **Array Out of Bounds:** Accessing `arr[i]` where `i < 0` or `i >= arr.length`.
- **Pattern Match Exhaustion:** Option or Variant tag without matching `when` arm and no `else`.
- **Dynamic Type Failure:** Dynamic `inspect` tag without matching arm and no `else`.
- **Uninitialized Variable Access:** Cyclic recursion accessing uninitialized cell.

#### Runtime Call Stack Frame Model
The interpreters keep the names of the running Quest functions on `RuntimeEnvironment.call_stack`, and an error
leaving a function records them in `QuestCompilerError.frames`, which the driver renders as `Diagnostic.trace`.
Compiled code walks the native stack instead, naming functions from the tables each unit registers
(exceptions.md §4 and §5).

### 4.4. Errors in Imported Interfaces and Modules
An offset means nothing without the file it is in, and an error found while loading an imported interface or module is
in that file, not the one being compiled. So the unit's file travels with the error:

- **The unit's file.** Each place that reads a unit from source (`module_loader.load_interface` and `load_module`,
  `interface_compiler.compile_interface_file`, and `module_compiler.compile_module_file`) parses and elaborates it
  inside `diagnostics.in_unit(source_map)` (through `Environment.unit_source` where there is an environment). A
  `QuestCompilerError` leaving it records that unit's `SourceMap`, unless an inner unit already did.
- **The imports that led there.** Each import is elaborated inside `diagnostics.at_import(offset, source_map)`, with
  the importing file's source map (`Environment.source_map`). An error located in another file gets a secondary
  label, "imported here", at the import, so a chain of imports reads innermost first. An error with no file yet was
  raised before the unit was read (it could not be found, say), so it is located at the import itself.
- **Rendering.** `diagnostic_of(error)` makes the diagnostic, carrying the unit's source map
  (`Diagnostic.source_map`) and the import labels (each `DiagnosticLabel.source_map`); the renderer locates each label
  in its own file. Diagnostics name a unit by its path relative to the current directory when it is inside it
  (`tokens.display_file_name`).

```
grp.int.quest:3:29: error: Undefined type 'Nope'
        Def A = Record b: Array(Nope) end
                                ^
  ::: usegrp.quest:1:11
    import grp: Grp
              - note: imported here
```

In C builds a module's body is compiled only when the program is linked, so an error in it is located in the module's
file but has no import label.

### 4.5. Reporting Several Errors (the Self-Hosted Compiler)
The self-hosted type checker (`questlang/typechecker/`) reports the bootstrap's error first, with the same message and
span, and then any further errors it finds:

- **Reporting.** Where the bootstrap raises `QuestCompilerError` or one of its subclasses, the self-hosted compiler
  raises `diagnostics.compilerError`. Its payload is the message, the offset in the unit being checked, the length,
  the help and notes, and whether the error is fatal. The offset is 0 where the raiser does not know it, as for the
  bootstrap's kind errors, which it reports at 1:1. Raising stops the work the error was part of, as in the bootstrap.
  An error that propagates out of a unit loaded from a file records the file (`env.withUnitSource`, the bootstrap's
  `in_unit`, §4.4), and `diagnostics.errorDiagnostic` makes the diagnostic, in that file or the current one.
- **Recovery points.** The checker catches `compilerError` at each binding and adds its diagnostic to the checker's
  errors: each phrase of a program, each binding of a block (function bodies, conditionals, and loops are made of
  blocks), each import, interface, and module declaration, and each member of an interface or module
  (`bindings.elaborateRecovering`). A failed binding contributes nothing to the typed AST, and the checker goes on
  with the next. Code that changes the environment's state (its scopes, the unit being elaborated) restores it as the
  error propagates, as the bootstrap's `finally` blocks do.
- **No cascades.** The names a failed binding declares are bound to poisoned symbols (`symbols.poisonValue`,
  `symbols.poison`): a poisoned value symbol, or a type or kind symbol whose definition is unknown. Using one raises
  `diagnostics.silentError`, which no recovery point reports, so a binding that depends on a failed one fails
  silently. So does a block or a module with a failed member. A binding with a declared type (`let f(x: Int): Int =
  ...`, `let x: T = ...`) is bound at that type even when its value fails, so its users are still checked. A failed
  import or module poisons the names it would have bound.
- **Fatal errors** stay fatal. An error that leaves nothing sensible to check (a cycle of imports, an internal error,
  the well-scopedness check of `scoping`) adds a fatal diagnostic and raises `diagbag.fatalError`, as syntax errors
  do.
- **Limit.** After 20 errors the checker reports that it stopped (`checker.maxErrors`), with a fatal diagnostic.
- **Output.** The typed AST is printed only when there are no errors. The errors are printed in the order found,
  which is source order.
- **Unit-file compiles.** Compiling an interface or module file on its own (`-c`, and the build engine's compiles of
  imported units) stops at a unit's first error, as the bootstrap's does: `typecheck.install` gives the module system
  a binding elaborator that fails with a member's first error, even one a block recovered from.

The error tests check the first error against the bootstrap's expectation, and any further errors against a reviewed
record of the driver's output; tests of several errors are the self-hosted compiler's own ([testing.md](testing.md)
§2.3).

---

## 5. Diagnostic Renderer & Visual Formatting

### 5.1. Output Format Example
```
error[E0105]: record type mismatch
  --> src/geometry.quest:14:10
   |
 4 | Let Point = Tuple x: Int y: Int end
   |             ^ note: expected type defined here
...
14 | let p: Point = tuple x = 10 y = "20" end
   |                ^ field 'y' has type 'String', expected 'Int'
   |
   = help: try converting the string using 'Int.fromString(y)'
```
