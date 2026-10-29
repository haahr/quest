# Quest Diagnostics: Errors and How They Are Reported

This document describes how the two compilers, their interpreters, and the REPL find errors, carry them to the
driver, and print them. The bootstrap's are `bootstrap/python/quest/diagnostics.py` and `pipeline.py`; the
self-hosted compiler's are `questlang/common/diagnostics` and `diagbag`. Both print the same text for the same error,
which the error tests compare ([testing.md](testing.md) §3).

---

## 1. Principles

1. **Offsets.** An error is located by a 0-indexed character offset and a length in its unit's source text. A
   `SourceMap` (`syntax/sources.py`, `questlang/common/location`) turns an offset into a file, line, and column when
   the error is printed.
2. **Raised where found, reported at the edge.** Code that finds an error raises it, and the work it was part of
   stops. Each phase of the pipeline catches what its work raised and makes a diagnostic of it; the driver prints the
   diagnostics.
3. **The first error, or several.** The bootstrap stops at the first error. The self-hosted type checker reports that
   error first and then every independent error it can find, without cascades (§4.5).
4. **Errors say where they are.** An error in an imported interface or module is located in that file, with the
   imports that led there (§4.4). An uncaught exception lists the Quest functions running where it was raised (§4.3).

---

## 2. Errors and Diagnostics

**Errors** are exceptions. In the bootstrap they are `QuestCompilerError` and its subclasses, each carrying a message,
an offset, and a length:

| Error | Raised by |
| :--- | :--- |
| `TokenizerError` | the tokenizer (`syntax/tokenizer.py`) |
| `ParserError` | the parser (`syntax/parser.py`) |
| `KindError`, `ContractivenessError` | kind checking (`types/kinds.py`) and contractiveness (`types/contractiveness.py`) |
| `QuestTypeError` | the type checker; with help text and notes where the checker has them |
| `TypeRecursionLimitExceeded` | type analysis that exceeds its step limit; a fatal error |
| `QuestRuntimeError` | the interpreters (`interpreter/primitives.py`), for an uncaught Quest exception or a run-time error |
| `FatalDiagnosticError` | the sink, when a fatal diagnostic is emitted (§3) |

The self-hosted compiler has one exception for all of them, `diagnostics.compilerError`, whose payload
(`diagnostics.CompilerError`) is the message, offset, length, help, notes, whether it is fatal, the file once it is
known, the "imported here" labels, and whether it is silent (§4.5). Its interpreters raise `model.runError`.

**A diagnostic** is what is printed. The bootstrap's `Diagnostic` has:

- `severity`: `FATAL`, `ERROR`, `WARNING`, or `INFO`. Only errors and fatal errors are reported today; nothing emits a
  warning or an informational diagnostic.
- `message`, and a `primary_label`: the offset and length the caret marks.
- `secondary_labels`: other places, each in its own file (`DiagnosticLabel.source_map`), such as the import that
  loaded the file the error is in.
- `notes` and `help_text`: background and advice, printed after the source line.
- `source_map`: the file the labels are in, when it is not the one being compiled.
- `trace`: for an uncaught exception, the frames running where it was raised, most recent first.

It also has `suggestions` (machine-applicable fixes) and an `error_code`, which the renderer prints but nothing sets.
`diagnostic_of(error)` makes an error's diagnostic. The self-hosted `diagnostics.Diagnostic` holds the same things
(its labels are `Label` tuples of a span, a message, and whether the label is primary), and
`diagnostics.errorDiagnostic` makes one of a `CompilerError`.

---

## 3. Reporting

**The bootstrap.** Each compilation has a `DiagnosticSink` (`CompilerContext.sink`). Each phase catches the
`QuestCompilerError` its work raises and emits its diagnostic to the sink; any other Python exception becomes an error
diagnostic whose note is the Python traceback (`Diagnostic.make_from_exception`), since it is a bug in the compiler.
Emitting a fatal diagnostic raises `FatalDiagnosticError`, which the pipeline catches. The pipeline stops after the
first phase that reported an error. The driver then prints every diagnostic to standard error, and exits with 70
(`EX_SOFTWARE`) if one is fatal, or else 1.

**The self-hosted compiler.** Each compilation has a diagnostic bag (`diagbag.T`). A phase adds the diagnostics of
the errors it catches; an error after which the phase cannot go on, such as a syntax error, is added and then raises
`diagbag.fatalError` (`addStoppingError`), as a fatal one does (`addFatal`). The driver's phases run only while the bag
has no errors, and `finish` in `driver/main` prints the bag's diagnostics to standard error and exits with 1 if there
are any.

---

## 4. Phase by Phase

### 4.1. Tokenizer and Parser
- **The tokenizer** stops at the first lexical error: an unexpected character, an unclosed comment, an unterminated
  string or character literal, an empty character literal, an unknown or unterminated escape, an invalid number, or
  an integer out of range.
- **The parser** reports one syntax error, at the farthest position any alternative reached, naming everything that
  was expected there, sorted. Both compilers report the same position and text.

### 4.2. Kinds and Types
- **The first error, or several.** The bootstrap raises at the first kind or type error, and the pipeline reports it.
  The self-hosted checker reports that error first, with the same message and span, and goes on to find others
  (§4.5).
- **Internal errors.** A broken invariant of the bootstrap usually shows as a Python exception, reported with its
  traceback (§3). The self-hosted checker reports one as an error whose message starts `internal:`.

### 4.3. Running Programs
Every run-time error is a Quest exception. A program raises its own with `raise exc with payload end` and catches them
with `try ... when exc with p then ... end`; the standard library raises its own the same way:

| Exception | Raised by |
| :--- | :--- |
| `int.error` | integer division or remainder by zero |
| `arrayOp.error` | an index out of bounds, or a negative array size |
| `variant.tagMismatch` | extracting an option's or variant's case (`!`) when the value is another case |
| `dynamic.error` | `dynamic.be` on a type mismatch, and `copy`, `intern`, and `extern` failures |
| `stack.overflow` | a call that would go too deep |

An uncaught exception is reported as a located error at the site it was raised, with the source line, followed by the
Quest functions running there, most recent first ([exceptions.md](exceptions.md) §2):

```
stack.mod.quest:18:9: error: Exception: stack.underflow
        raise underflow end
        ^
  in stack.pop
  in run
  in <main>
```

Every backend reports the same exception and site. The interpreters list every frame; compiled code lists only some
of them, those the C compiler did not inline or turn into jumps (exceptions.md §2.4).

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
  (`syntax/sources.py`).

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

## 5. Rendering

`DiagnosticRenderer.render_diagnostic` (and `diagnostics.format` in the self-hosted compiler) prints a diagnostic as
the location, the severity, and the message, then the source line with a caret under the primary label's span:

```
two.quest:1:14: error: Type mismatch: synthesized type 'String' is not a subtype of expected type 'Int'
    let x: Int = "a"
                 ^
two.quest:2:15: error: Type mismatch: synthesized type 'Int' is not a subtype of expected type 'Bool'
    let y: Bool = 3
                  ^
```

The self-hosted compiler reports both errors of this program; the bootstrap reports the first. After the source line
come each secondary label, as `::: FILE:LINE:COLUMN` with its line and a dashed underline (§4.4), then each note
(`= note:`), the help (`= help:`), and an uncaught exception's frames (`in NAME`, with a run of the same frame shown
once and then `... NAME repeated N more times`). A diagnostic without a location prints only its message. A fatal
diagnostic says `fatal:` in the bootstrap and `fatal error:` in the self-hosted compiler. A unit is named by its path
relative to the current directory when it is inside it (`display_file_name` in `syntax/sources.py`). The output is
plain text, without color.
