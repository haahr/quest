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

```quest
interface Readline export
    (* Raised on a system error, such as an unreadable history file *)
    error: Exception
    (* Raised by readLine at the end of the input (Ctrl-D on an empty line) *)
    endOfInput: Exception
    (* Raised by readLine when the line is interrupted (Ctrl-C); the line read so far is discarded *)
    interrupted: Exception

    (* Whether readLine edits lines: standard input is a terminal, TERM is not empty, dumb, or emacs, and the runtime
     * has a line editor *)
    editing(): Bool
    (* Writes prompt and reads a line, without its newline, editing it if editing() is true. Without editing, it
     * reads from the same buffer as reader.input, so a program may mix the two *)
    readLine(prompt: String): String

    (* History, which the Up and Down keys move through; these do nothing unless editing() is true *)
    addHistory(line: String): Ok
    (* Reads a history file, if it exists *)
    readHistory(path: String): Ok
    (* Writes the history, its last maxLines lines, to a file *)
    writeHistory(path: String maxLines: Int): Ok
end
```

Strings are bytes ([syntax.md](syntax.md) §2.3): a line holds the bytes typed, whatever their encoding.

### 1.1. The C runtime (`runtime/quest_readline.c`)

- `editing` checks `isatty(0)` and `TERM`, once.
- `readLine` with editing calls `readline(prompt)`. A null result is `endOfInput`. Ctrl-C: a `SIGINT` handler,
  installed only for the call, `siglongjmp`s out of `readline`, which is then reset (`rl_free_line_state`,
  `rl_cleanup_after_signal`, or libedit's equivalents) and raises `interrupted`. This is the riskiest part, since
  libedit and GNU readline differ in their signal handling; Step 1 settles it with the pseudo-terminal test, against
  both libraries where both are installed, before anything is built on it.
- `readLine` without editing writes the prompt to `writer.output`, flushes it, and reads up to a newline through
  `quest_reader_input`'s buffer. End of input before any byte is `endOfInput`; a last line without a newline is a
  line.
- `-DQUEST_NOREADLINE` makes `editing` false and the history functions do nothing.

### 1.2. The bootstrap

`builtins.py` implements the externals with Python's `readline` module and `input()` with standard input read as
bytes. `quest/repl.py` then reads its lines and history through these same functions, not through `readline`
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
  for the next input; Step 2 checks that nothing in it assumes a fresh environment (`loader.install`, the hooks, and
  `e.report` are set again for each input, which is harmless).
- **Completeness** (`check_input_completeness`): an input is incomplete when the tokenizer reports an unclosed comment
  or unterminated string, or the parser fails at the EOF token. The tokenizer's errors are diagnostics with those
  messages; the parser's `syntaxError` knows the token it failed at but reports only a diagnostic, so it records
  whether that token was EOF where the REPL can ask.

---

## 3. Steps

### Step 0: Transcript tests (bootstrap only)

A `tests/repl/` directory of transcripts, each a file of input lines (with the usual `@args`, `@env` directives where
needed). The runner feeds each to `quest -i` on standard input and compares standard output, standard error, and the
exit status with `tests/golden/repl/`. The scenarios of `tests/python/test_repl.py` become transcripts: single and
multiple phrases, multi-line buffering, silent `ok`, multi-line output, rollback after a type error and after an
uncaught exception, rebinding, a syntax error mid-line, modules run once per session and forgotten on failure, files
created since, a module declared again, and `-i` with a file. `test_repl.py` keeps what transcripts cannot show (the
completeness function itself). No behavior changes; the goldens record the bootstrap's REPL as it is.

### Step 1: `io/readline`

The interface and module (§1), the C runtime file and its detection in `compiler_runner.py`, the bootstrap's externals
(§1.2), and the self-hosted builtins entries. Tests:
- A golden program reading lines from `@stdin` with `readLine` (prompts, a last line without a newline, the end of
  input), mixing `reader.getChar`, and writing and reading a history file in its scratch directory; it runs in every
  phase, compiled and interpreted, so the C and Python implementations agree.
- A pseudo-terminal unit test (Python's `pty`) of a compiled program: editing (Ctrl-A, Ctrl-K), Up to recall a history
  line, Ctrl-C raising `interrupted` with the program continuing, and Ctrl-D raising `endOfInput`.

### Step 2: The bootstrap's REPL on `io/readline`

`repl.py` reads lines and keeps history through the Step 1 functions (§1.2). The transcripts do not change; the
pseudo-terminal test runs against `quest` itself too.

### Step 3: Rollback and sessions in `questlang/`

The snapshots, `newSession`, and the frame-returning `evalProgramPhrases` of §2, with nothing calling them yet beyond a
questlang test that elaborates and runs two inputs, fails a third, and checks that the first two's bindings and
modules are as they were.

### Step 4: `questlang/driver/repl`

The completeness check, the loop (prompts `">>  "` and `"    "`, results prefixed `"==  "` with continuation lines
indented, diagnostics rendered against the input's `<repl>` source map), `evaluate` as a transaction, Ctrl-C clearing
the buffer, the end of input ending the session with a newline and status 0, and history in `$HOME/.quest_history`
(1,000 lines), all through `io/readline`.

### Step 5: The driver

`main.quest` enters the REPL with no file when standard input is a terminal, and with `-i`: alone, or after running a
file (whose errors exit with 1 before the REPL starts), with `system.args` holding `<repl>` or the file and the
arguments after `--` ([extensions.md](extensions.md)). The usage line gains `-i`. The self-hosted suite runs the
transcripts against the compiled driver; the pseudo-terminal test runs against it too.

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
