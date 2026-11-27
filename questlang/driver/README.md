# questlang/driver: the `quest` command

This directory is the top of the self-hosted compiler: the program `./quest` runs. It reads the command line, decides
what the user asked for, and strings the other directories together to do it: the front end in `questlang/syntax`
and `questlang/typechecker`, the IR in `questlang/ir`, the backends in `questlang/ssa` and `questlang/codegen`, the
interpreters in `questlang/interpreter`, the JIT in `questlang/jit`, unit compilation in
[`questlang/modules`](../modules/README.md), and the build engine in [`questlang/build`](../build/README.md). Nothing
else imports it. Its command line is the bootstrap's (`./questboot`), with more phases and options
([docs/pipeline.md](../../docs/pipeline.md) §5).

## The driver is a program

Unlike every other unit in `questlang/`, [`main.quest`](main.quest) is a Quest *program*, not a module: a sequence of
top-level phrases that run in order when the executable starts. Its first phrases bind the parsed command line, the
list of phases this run goes through, and the functions for each kind of work; its last phrases dispatch. It imports
some library modules it never uses (`list`, `dynamic`, `collections/hashSet`, ...), so that they are linked into the
driver: the JIT compiles user code that links against the modules already in the driver's process, so the driver is
also the library ([docs/jit.md](../../docs/jit.md) §3.3).

[`options.int.quest`](options.int.quest) parses `system.args` when its module is initialized, before `main.quest`
runs, into a tuple of every option (`options`), and knows every phase name: the IR's stages, the SSA's phases, and
the backends'. A bad command line prints the usage and exits with status 2.

## What a run does

The forms of the command line, which `main.quest`'s header describes in full:

- **Running a program** (`quest FILE`, `-e CODE`, or standard input). The program is tokenized, parsed, desugared,
  and type-checked, then compiled and run by the JIT, or with `--no-jit` (or an option only the interpreter has)
  walked by the tree-walking interpreter. It prints the last phrase's result, or each phrase's with `--echo`.
- **Phases** (`--stop-after PHASE`, `--dump-after PHASE`). The driver computes `pipeline`, the list of phases this
  run passes through, then runs them in order and prints the output of each one asked for: tokens, the AST, the typed
  AST, the IR at a stage, the SSA after a pass, the generated C or assembly, or a compiled run's output. Each phase
  runs only if the ones before it found no errors. The test runner compares these outputs with golden files
  ([docs/testing.md](../../docs/testing.md) §2.3), so their formats are fixed. There is no framework of phase
  objects, as the bootstrap has: the phases are function calls in sequence. The SSA's phases run in
  [`ssaphases.int.quest`](ssaphases.int.quest), a module of its own so that a driver compiled to WebAssembly can
  substitute its variant `ssaphases.wasm` and leave out the SSA ([docs/wasm.md](../../docs/wasm.md) §5.1).
- **A unit file** given alone (`x.int.quest` or `x.mod.quest`, `-c` optional). `compileUnitFile` compiles an
  interface to its `.qi` and C header, or a module to its C or assembly, object, and `.qm`.
- **Building** (`quest compile FILE`, or `-o`). `buildProgram` hands the program to the build engine, which compiles
  each stale unit separately and links a binary. Other compiled runs (`--stop-after run_c_compiled`, `--emit-c`,
  `--whole-program`) go through `compiled`, which translates the program's own unit here and uses the engine only for
  the modules that unit imports.
- **Formatting** (`quest fmt [-w | --check] [FILE|DIRECTORY...]`). The driver hands the files to the formatter
  ([`questlang/format`](../format), [docs/formatter.md](../../docs/formatter.md)), which prints each formatted,
  rewrites it with `-w`, or with `--check` names the files that would change.
- **The language server** (`quest lsp`). The driver hands standard input and output to
  [`questlang/lsp`](../lsp)'s server ([docs/lsp.md](../../docs/lsp.md)).
- **A parallel build's worker**. Run with a worker's command line, the driver compiles a batch of modules for its
  parent ([`build/workers`](../build/workers.int.quest)).

For a compiled program that fails, [`binaryerrors.int.quest`](binaryerrors.int.quest) turns what it printed on
standard error, an uncaught exception's message, the site it was raised at, and its stack frames, into a diagnostic
pointing into the program's source, as the interpreter's errors are reported
([docs/exceptions.md](../../docs/exceptions.md) §2.2).

## Whole programs

With `--whole-program`, [`whole.int.quest`](whole.int.quest) merges every imported module that has a source into the
program's IR unit, each after the modules it imports, and rewrites references to them as references within the unit.
The IR passes and backends then see one unit, so inlining and specialization reach across module boundaries, and
`dropUnreachable` deletes module members the program cannot reach. A module known only through its interface (a
library module, prebuilt) stays an import and is linked from its object
([docs/build-process.md](../../docs/build-process.md) §1.2). Since the modules are merged, the driver also makes
their abstract types transparent to the layout code: a merged module's `T = Int` is laid out as an `Int`.

## The REPL

[`repl.int.quest`](repl.int.quest) runs the interactive loop: with no program at a terminal, or after one with `-i`.
It reads lines through `io/readline`, keeping history in `~/.quest_history`, and keeps reading while the text so far
is `incomplete`: an unclosed comment or string, or a syntax error at the very end of the input. Each input is a
transaction (`evaluate`): the session snapshots the type environment, the unit graph, and the interpreter's frame,
compiles and runs the input, and restores the snapshots if it fails, so a type error or uncaught exception leaves no
half-made bindings behind ([docs/repl.md](../../docs/repl.md) §5). Inputs are compiled and run by a JIT session
(`newJit`) by default, otherwise by the interpreter. Later inputs may redefine earlier names
([docs/repl.md](../../docs/repl.md) §6).

## The Jupyter kernel

`quest --kernel` serves a Jupyter notebook: `tools/jupyter`'s kernel starts the driver and sends it requests, each a
JSON object on one line, on file descriptor 3, and reads records back on descriptor 4, leaving standard output and
error to the program ([docs/jupyter-kernel.md](../../docs/jupyter-kernel.md) §2).
[`kernel.int.quest`](kernel.int.quest) runs that protocol over a REPL session, one cell an input.
[`interrupts.int.quest`](interrupts.int.quest) lets the notebook's interrupt button stop a running cell: a `SIGINT`
handler sets a runtime flag, which code the JIT compiled checks at each function's entry and loop head, and the
interpreter polls
([docs/jupyter-kernel.md](../../docs/jupyter-kernel.md) §5).

## Connections

The bootstrap counterpart is [`bootstrap/python/quest/driver/`](../../bootstrap/python/quest/driver/README.md), which
has `main`, `options`, and `repl`, but no JIT, whole-program merging, kernel, or workers. The driver is built from the
tree by a released self-hosted compiler, or by the bootstrap
([docs/release-compiler.md](../../docs/release-compiler.md)).

## Further reading

- [docs/pipeline.md](../../docs/pipeline.md): the phases' names (§2) and the command line (§4, §5).
- [docs/repl.md](../../docs/repl.md): the REPL's input, output, rollback, and redefinition.
- [docs/jit.md](../../docs/jit.md): how the JIT runs programs and REPL inputs.
- [docs/jupyter-kernel.md](../../docs/jupyter-kernel.md): the kernel's protocol and interrupts.
- [docs/build-process.md](../../docs/build-process.md) §1.2: whole-program compilation.
- [docs/diagnostics.md](../../docs/diagnostics.md): how the driver reports errors.
