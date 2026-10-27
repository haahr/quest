# The Self-Hosted REPL and the `readline` Library

This plan gives the self-hosted driver (`questlang/driver/main.quest`) the bootstrap's REPL ([repl.md](repl.md)):
`quest` with no file at a terminal, `-i` with or without a file, multi-line input, rollback of a failed input, and
line editing with history. Line editing comes from a new standard library module, `readline`, whose externals call
the C library's readline API; the bootstrap implements the same externals with Python's `readline`, so that the
bootstrap's REPL and Quest programs edit lines the same way. It follows Milestone 3 ([milestone-3.md](milestone-3.md)),
which left the REPL and `--interactive` out (§6), and does not depend on Milestone 4.

The decisions this plan rests on (2026-10-26):
- **Library.** `lib/io/readline.{int,mod}.quest`, `import io/readline : io/Readline`, a new category beside
  `collections` and `util` ([new-libraries.md](new-libraries.md)). It is small and Cardelli-style: errors and the end
  of input are exceptions, not options.
- **C library.** The readline API, which both GNU readline and libedit provide (`<readline/readline.h>`). The build
  detects them as it does Boehm GC (`detect_gc_flags`): GNU readline where it is installed (Homebrew's `readline`, or
  the system's), compiled `-DQUEST_GNU_READLINE`, else libedit (`-ledit`, part of macOS, and `libedit-dev` on Linux),
  else neither, `-DQUEST_NOREADLINE`, which reads plain lines. The runtime keeps the two libraries' differences (signal
  handling, history truncation) behind that flag. GNU readline is GPL, which binds the programs linked with it; that
  is the user's choice when they install it.
- **Linking.** The externals live in a runtime file of their own, `runtime/quest_readline.c`, compiled and linked with
  every program, as `quest_serialization.c` is. Linking only the programs that import `io/readline` would need the
  build to know a module's link flags, which it does not; libedit is a system library, so linking it always costs
  little.
- **Testing.** REPL transcripts are golden tests: a file of input lines fed to `quest -i` on standard input, which is
  not a terminal, so `readLine` writes its prompt and reads a plain line. The bootstrap writes the goldens and the
  self-hosted run compares against them, as for programs. Editing, history, and Ctrl-C need a terminal and are tested
  through a pseudo-terminal.
- Carried over from Milestones 2 and 3: `questlang/` follows the bootstrap module for module (the REPL is
  `questlang/driver/repl`, as the bootstrap's is `quest/repl.py`), divergences are documented where they are made, and
  each step is pushed when its runs pass.

---

## 1. The `io/readline` Interface

The interface is `lib/io/readline.int.quest`, documented in [new-libraries.md](new-libraries.md) §3.1: `editing`,
`readLine` (raising `endOfInput` and `interrupted`), and the history functions `addHistory`, `readHistory`, and
`writeHistory`. Strings are bytes ([syntax.md](syntax.md) §2.3): a line holds the bytes typed, whatever their encoding.

### 1.1. The C runtime (`runtime/quest_readline.c`)

- `editing` is true when standard input and output are terminals and `TERM` is not empty, `dumb`, or `emacs`.
- `readLine` with editing uses readline's callback interface, waiting for input with `select`, as CPython's `readline`
  module does. Its `SIGINT` handler, installed only while it reads, sets a flag that ends the wait (the handler has no
  `SA_RESTART`); the line is then abandoned (`rl_free_line_state`, `rl_callback_sigcleanup` for GNU readline,
  `rl_cleanup_after_signal`) and `interrupted` raised. Nothing `longjmp`s out of the library. Step 1's pseudo-terminal
  test runs this against GNU readline and libedit both.
- `readLine` without editing writes the prompt to `writer.output`, flushes it, and reads up to a newline through
  `quest_reader_input`'s buffer. End of input before any byte is `endOfInput`; a last line without a newline is a
  line.
- The history is the runtime's own list, mirrored into the line editor's, and its file is plain lines. The line
  editors' own files differ (libedit's starts with a cookie and escapes its lines), and the bootstrap's REPL, whose
  Python may use libedit, shares `~/.quest_history` with compiled REPLs, which may use GNU readline.
- The build (`compiler_runner.detect_readline_flags`) uses GNU readline where it is installed
  (`-DQUEST_GNU_READLINE`), else libedit (`-ledit`), else neither (`-DQUEST_NOREADLINE`, when `editing` is false).
  `QUEST_READLINE=gnu`, `edit`, or `none` chooses one.

### 1.2. The bootstrap

`builtins.py` implements the externals with Python's `readline` module and `input()` with standard input read as
bytes, and keeps a history list of its own, as the C runtime does (Python's automatic history is off, since
`readLine`'s caller adds lines). `quest/repl.py` then reads its lines and history through these same functions, not through `readline`
directly, so the two REPLs share one definition of editing, dumb terminals, and the end of input. The self-hosted
interpreter's builtins table (`questlang/interpreter/builtins.mod.quest`) gains the externals, calling the native
library, as it does for `reader`.

---

## 2. What the Self-Hosted Compiler Needs

The bootstrap's REPL (`QuestREPL.evaluate`, repl.md §5) keeps one type environment, unit graph, and runtime frame for
the session, and puts them back when an input fails. The self-hosted compiler has none of the rollback:

- **Type environment** (`questlang/types/env`): `snapshot` and `restore` of the symbol counter, the interfaces and
  modules, and the current scope's tables, as `Environment.snapshot` does.
- **Unit graph** (`questlang/modules/graph`): `snapshot`, `restore` (forgetting the units loaded since), and
  `newSession` (the resolver forgets its resolutions, so that files created since are found).
- **Interpreter** (`questlang/interpreter/treewalk`): the root state's module values, snapshotted and restored in
  place, and the frame a session continues in. `evalProgramPhrases` already threads the frame through a program's
  phrases; a variant returns the last one, so that the next input continues in it (`eval_scoped_binding`).
- **Elaboration**: `typecheck.elaborateProgram` checks into the environment it is given, so a phrase's bindings stay
  for the next input; Step 3 checks that nothing in it assumes a fresh environment (`loader.install`, the hooks, and
  `e.report` are set again for each input, which is harmless).
- **Completeness** (`check_input_completeness`): an input is incomplete when the tokenizer reports an unclosed comment
  or unterminated string, or the parser fails at the EOF token. The tokenizer's errors are diagnostics with those
  messages; the parser's `syntaxError` knows the token it failed at but reports only a diagnostic, so it records
  whether that token was EOF where the REPL can ask.

---

## 3. Steps

### Step 0: Transcript tests (bootstrap only) (done)

A `tests/repl/` directory of transcripts, each a file of input lines (with the usual `@args`, `@env` directives where
needed). The runner feeds each to `quest -i` on standard input and compares standard output, standard error, and the
exit status with `tests/golden/repl/`. The scenarios of `tests/python/test_repl.py` become transcripts: single and
multiple phrases, multi-line buffering, silent `ok`, multi-line output, rollback after a type error and after an
uncaught exception, rebinding, a syntax error mid-line, modules run once per session and forgotten on failure, files
created since, a module declared again, and `-i` with a file. `test_repl.py` keeps what transcripts cannot show (the
completeness function itself). No behavior changes; the goldens record the bootstrap's REPL as it is.

### Step 1: `io/readline` (done)

The interface and module (§1), the C runtime file and its detection in `compiler_runner.py`, the bootstrap's externals
(§1.2), and the self-hosted builtins entries. Tests:
- A golden program reading lines from `@stdin` with `readLine` (prompts, a last line without a newline, the end of
  input), mixing `reader.getChar`, and writing and reading a history file in its scratch directory; it runs in every
  phase, compiled and interpreted, so the C and Python implementations agree.
- A pseudo-terminal unit test (Python's `pty`) of a compiled program: editing (Ctrl-A, Ctrl-K), Up to recall a history
  line, Ctrl-C raising `interrupted` with the program continuing, and Ctrl-D raising `endOfInput`.

### Step 2: The bootstrap's REPL on `io/readline` (done)

`repl.py` reads lines and keeps history through the Step 1 functions (§1.2). The transcripts do not change; the
pseudo-terminal test runs against `quest` itself too.

### Step 3: Rollback and sessions in `questlang/` (done)

The snapshots, `newSession`, and the frame-returning `evalProgramPhrases` of §2, with nothing calling them yet beyond a
questlang test that elaborates and runs two inputs, fails a third, and checks that the first two's bindings and
modules are as they were.

`env.snapshot` and `restore`, `graph.newSession`, `snapshot`, and `restore`, and `treewalk.snapshot`, `restore`, and
`evalProgramPhrasesIn` (the phrases' results and the frame after them). `tests/source/questlang/repl_sessions.quest`
runs the scenarios of the REPL transcripts through them. Two divergences from the bootstrap, both because the
bootstrap's step does nothing that the self-hosted compiler can observe:
- The environment's snapshot does not record a symbol counter. The bootstrap's records `_symbol_counter`, but its ids
  come from the global `allocate_symbol_id`, which no restore resets, so ids are never reused there either.
- A frame's snapshot does not record its parent, which cannot change in `model.Frame`. The REPL keeps the frame the
  next input runs in, and goes back to the one an input that fails started in, as the bootstrap's does.

### Step 4: `questlang/driver/repl` (done)

The completeness check, the loop (prompts `">>  "` and `"    "`, results prefixed `"==  "` with continuation lines
indented, diagnostics rendered against the input's `<repl>` source map), `evaluate` as a transaction, Ctrl-C clearing
the buffer, the end of input ending the session with a newline and status 0, and history in `$HOME/.quest_history`
(1,000 lines), all through `io/readline`.

`questlang/driver/repl.{int,mod}.quest`, which also holds `runErrorDiagnostic`, the driver's before. The transcripts
found one bootstrap bug, which is fixed: `compile_phrase` left the environment's source map on the session's first,
empty input, so an error in an input's import was reported at 1:1 with no source line.

### Step 5: The driver (done)

`main.quest` enters the REPL with no file when standard input is a terminal, and with `-i`: alone, or after running a
file (whose errors exit with 1 before the REPL starts), with `system.args` holding `<repl>` or the file and the
arguments after `--` ([extensions.md](extensions.md)). The usage line gains `-i`. The self-hosted suite runs the
transcripts against the compiled driver; the pseudo-terminal test runs against it too.

`system.isTerminal(fd)` (ABI 42) tells the driver whether standard input is a terminal; without one, it reads the
program from standard input, as the bootstrap's does, and as it does for a file of `-`. The pseudo-terminal test runs
the self-hosted driver when `QUEST_SELF_HOSTED_DRIVER` names one already compiled, since compiling it there would take
minutes.

### Step 6: Done

Update repl.md (both REPLs, and `io/readline` underneath), new-libraries.md (`io/readline`), interpreter.md,
testing.md (transcripts), compiler-organization.md (status), and milestone-3.md §6; record the divergences here.

---

## 4. Done When

- The compiled self-hosted driver passes every REPL transcript with the bootstrap's output, diagnostics, and exit
  status, and the pseudo-terminal test passes against both drivers.
- `io/readline` behaves the same compiled, in the bootstrap's interpreter, and in the self-hosted one.
- The bootstrap's suites and the self-hosted run pass.

## 5. Not in This Plan

- Completion (Tab), and any key bindings beyond the library's defaults.
- A REPL for compiled code: the REPL interprets, as the bootstrap's does.
- Undoing a failed input's side effects (output written, variables assigned), which the bootstrap does not undo
  either (repl.md §5).
