# Quest Interactive REPL

This document describes the Quest interactive Read-Eval-Print Loop (REPL), its execution modes, input buffering
rules, prompt formatting, terminal handling, and error recovery.

---

## 1. Overview

The Quest REPL provides an interactive top-level environment for evaluating Quest expressions, defining variables and
functions, importing modules, and experimenting with types.

Both drivers have one, and they behave the same: the bootstrap's (`bootstrap/python/quest/repl.py`, in Python) and the
self-hosted compiler's (`questlang/driver/repl`, in Quest, compiled with the driver). Each reads its input through
`io/readline` (§4) and interprets each input in the tree-walking interpreter; the same transcripts test both
(docs/testing.md §2.7). Section 8 describes how the two are built.

Key features:
- **Persistent Lexical and Dynamic Environments:** Types, bindings, and modules defined in one phrase remain in scope
  for subsequent phrases.
- **Redefinition in Place:** A top-level `let` of a name's type redefines it for the code that already uses it, so
  fixing a function fixes its callers (§6).
- **Semicolon-Optional Multi-line Buffering:** Evaluates syntactically complete phrases immediately. If input is
  incomplete (e.g. open block, unclosed delimiter, or missing operand), the REPL automatically prompts for continuation
  lines until the phrase is closed. Semicolons may end a phrase but are optional.
- **Uniform 4-Column Alignment:** Clean visual structure using 4-character prompts and response prefixes.
- **Transactional Error Rollback:** If a phrase fails typechecking or raises an uncaught runtime exception, any partial
  environment bindings from that phrase are rolled back, preserving a consistent environment.
- **Line Editing & History:** Line editing and a history saved to `~/.quest_history`, through `io/readline`, with
  plain lines for `dumb` and `emacs` terminals and input that is not a terminal.

---

## 2. Invocation Modes

### 2.1. Direct REPL Launch
Running `quest` without a file or `-e` enters the REPL when standard input is a terminal (`system.isTerminal(0)` in
the self-hosted driver). Otherwise the driver reads a program from standard input and runs it, naming it `<stdin>`,
as it does for a file of `-`. The arguments after a `--` are the program's, and the REPL's `system.args` is `<repl>`
followed by them.

```bash
$ quest
>>  let a = 10
==  let a:Int = 10
>>  a * 4
==  40 : Int
```

The self-hosted driver's REPL compiles each input to arm64 code and runs it in its own process, instead of interpreting
it ([jit.md](jit.md)), unless `--no-jit` is given; its output is the interpreter's but for the differences jit.md §4
lists. An `-e` program or a file given without `-i` runs as one input in the same way. A file given with `-i` is the
first input; an input may import the driver's own modules (the library's, and the compiler's), whose copies in the
driver it uses, and the user's, which the JIT compiles from source and loads once in a session.

### 2.2. Interactive Mode with File (`-i` / `--interactive`)
The `-i` and `--interactive` flags execute a file through the compiler pipeline first, and if successful, drop into
the REPL with the file's bindings and types in scope:

```bash
$ quest -i tests/source/03_functions_closures.quest
>>  apply(add1 100)
==  101 : Int
>>  adder(5)(10)
==  15 : Int
```

If the loaded file contains a compile error (syntax, kind, or type error) or encounters an uncaught runtime exception,
the diagnostic is emitted to `stderr` and the process exits immediately with code `1` without launching the REPL.
Inputs continue in the file's environment and in the frame its last phrase left, and `system.args` is the file
followed by the arguments after it. `-i` alone enters the REPL whatever standard input is, which is how the
transcripts feed it their lines.

### 2.3. Kernel Mode (`--kernel`)
The self-hosted driver's `--kernel` serves a program instead of a person: the Jupyter kernel ([jupyter.md](jupyter.md)).
It reads requests from descriptor 3 and writes records to descriptor 4, each a JSON object on a line of its own
(jupyter.md §2), until descriptor 3 ends. Its standard output and error are the program's. `{"execute": CODE}` runs CODE
as one input, as a completed phrase runs here: its phrases' results are `result` records, an input that fails is rolled
back (§5) and reported as an `error` record, and a `done` record ends the request. `complete`, `inspect` and
`isComplete` requests answer from the session's environment, for completion, inspection, and complete input. With
`QUEST_KERNEL` set, as the kernel sets it, `io/display` and `io/readline` use the same descriptors for a notebook's
displays and lines (new-libraries.md §3.1, §3.2). A cell has no continuation lines: one that ends in the middle of a
phrase is a syntax error. `--kernel` takes neither a file nor `-e`, and `--no-jit` interprets the cells. Standard output
is line-buffered when `QUEST_LINE_BUFFERED` is set, which the kernel does, so that a cell's lines arrive while it runs.

---

## 3. Prompts & Visual Formatting

The REPL enforces strict 4-character columnar alignment:

| Element | String | Meaning |
| :--- | :--- | :--- |
| **Main Prompt** | `">>  "` | Ready for a new top-level phrase. |
| **Continuation Prompt** | `"    "` | 4 blank spaces; input is incomplete and waiting for closing syntax. |
| **Response Prefix** | `"==  "` | Prefixes the evaluated result of each non-`ok` phrase. |

### 3.1. Single-Line and Semicolon Behavior
Semicolons are optional at the end of a top-level phrase (see [extensions.md](extensions.md#semicolons)). Both
forms are valid:

```quest
>>  let x = 1
==  let x:Int = 1
>>  let y = 2;
==  let y:Int = 2
```

Multiple phrases on a single line, with or without semicolons between them, are evaluated sequentially, and each
non-`ok` phrase outputs its result on its own line prefixed with `"==  "`:

```quest
>>  let x = 1; let y = 2; x + y
==  let x:Int = 1
==  let y:Int = 2
==  3 : Int
```

### 3.2. Multi-line Input & Heuristics
When a line ends while a construct is open (such as a function body, `if...then`, `loop`, `try`, `record`, or open
parenthesis), the REPL presents the continuation prompt (`"    "`):

```quest
>>  let rec fib(n: Int): Int =
        if n <= 1 then
            n
        else
            fib(n - 1) + fib(n - 2)
        end
==  let fib:All(n:Int):Int = <fun>
>>  fib(10)
==  55 : Int
```

The continuation heuristic checks:
1. **Lexical scanning:** If the tokenizer encounters an unterminated string literal or unclosed comment at EOF, it
   continues prompting.
2. **Grammar parsing:** If the parser reaches `EOF` while expecting a closing token or operand, it continues prompting.
3. **Syntax errors:** If a syntax error occurs on a non-EOF token (e.g. `let 123 = 4`), the diagnostic is emitted
   immediately, the buffer is cleared, and the REPL resets to `">>  "`.

Since a line that completes a phrase ends it, a phrase continues onto the next line only if the line leaves it
incomplete. In a file, `let total = a` followed by a line `+ b` is one phrase; at the REPL, `let total = a` is
evaluated when its line ends, and `+ b` is then a syntax error. Break a long phrase after an operator, `=`, or `and`,
or inside an open bracket or block, rather than before.

### 3.3. Silent `ok` Phrases
Statements and expressions that evaluate to `ok` (assignments, loops, imports, or explicit `ok;`) produce no output:

```quest
>>  let var total = 0
==  let var total:Int = 0
>>  total := 42
>>  total
==  42 : Int
```

### 3.4. Multi-Line Output Formatting
When an evaluated phrase produces a multi-line formatted string (e.g. tuples or records), the first line is prefixed
with `"==  "` and subsequent lines are indented with 4 spaces (`"    "`):

```quest
>>  (1, "abc", true)
==  ( 1,
      "abc",
      true ) : Tuple(Int, String, Bool)
```

---

## 4. Terminal Support & History

### 4.1. Line Editing and History
The REPL reads its input through `io/readline` ([new-libraries.md](new-libraries.md) §3.1), whose line editor is
Python's `readline` module in the bootstrap and GNU readline or libedit in compiled code. Arrow keys (`Up`/`Down`)
move through the history, and the usual Emacs editing keys (`Ctrl-A`, `Ctrl-E`, `Ctrl-K`) work. Each non-blank line
typed is added to the history, which is read from `~/.quest_history` at the start of the session and written back,
its last 1,000 lines, at the end. The file holds a line per entry, whatever the line editor, so the bootstrap's REPL
and a compiled one share it.

### 4.2. Dumb & Emacs Terminal Detection
Lines are edited only when standard input and output are terminals and the `TERM` environment variable is not
`"dumb"`, `"emacs"`, or empty (`readline.editing()`). Otherwise the REPL writes its prompts and reads plain lines, with
no history, which is how its transcripts are tested (docs/testing.md §2.7).

---

## 5. Error Recovery & Transactional Rollback

If a phrase fails during parsing, typechecking, or runtime evaluation:
1. A structured diagnostic is rendered to `stderr` with line and column pointers.
2. The environment is restored to its exact state prior to that phrase.
3. The session remains active and prompts for the next command.

The rollback (`QuestREPL.evaluate`, and `evaluate` in `questlang/driver/repl`) restores the type checker's environment and the runtime environment: their
bindings, the frame evaluation continues in, and the units the input loaded. The REPL keeps one unit graph
(`docs/build-process.md` §2.1) for its whole session, which holds the interfaces and modules loaded so far, with their
typed forms; the runtime environment holds that same graph, and the values of the modules the interpreter has run
(`module_values`). An input that fails forgets the units it loaded and the modules it ran, so that importing a module
again elaborates and runs it again, as if the failed input had never been. Side effects are not undone: output already
written stays written, a variable of an earlier binding or module assigned by the failed input keeps its new value, and
so does a binding the failed input redefined (§6), since a redefinition is an assignment.

Each input is also a compilation session of its own (`UnitGraph.new_session`): its imports are resolved again, so
that it finds interface and module files created since an earlier input, including one that failed for want of them.
Units already loaded stay as they were loaded: editing a module file that an earlier input imported does not change
it in the session. A module declared in an input (`module m: I ... end`) is run where it is declared, so declaring it
again in a later input replaces it.

Example:
```quest
>>  let a = 10
==  let a:Int = 10
>>  let a = 99 let b: Int = "type error"
<repl>:1:25: error: Type mismatch: synthesized type 'String' is not a subtype of expected type 'Int'
    let a = 99 let b: Int = "type error"
                            ^
>>  a
==  10 : Int
```

Notice `a` remains `10` because the failed line was rolled back transactionally.

---

## 6. Redefinition

Interactive code, the REPL's inputs and the file `-i` runs (its first input), binds its top-level names as Python and
Lisp do: a later definition of a name updates the code that already uses it, so that fixing a function fixes its
callers without redefining each of them. Programs, `-e`, and `quest FILE` scope lexically, and nothing here changes
them.

```quest
>>  let f(n: Int): Int = 100 / n
>>  let g(n: Int): Int = f(n) + 1
>>  let f(n: Int): Int = n
>>  g(0)
==  1 : Int
```

**The rule.** Each value `let` at an interactive input's top level (not in a block, function, tuple, or module) binds
a *slot*, which has a type and a `var`-ness. A later top-level `let` of the name whose current binding is a slot of an
equal type and the same `var`-ness **redefines** the slot: every use of it, earlier and later, sees the new value from
then on. Types are equal when each is a subtype of the other, so two quantified types that differ only in their
variables' names are equal, as are a type and an alias of it. Any other rebinding shadows, as in a program: a different
type, a `var` for a non-`var`, or a name that is not a slot (a module's, an import's, an exception's).

- **Every use is late-bound**, in later inputs and in the input that defines the slot, inside functions too: `let
  p() = 1; let q() = p(); let p() = 2; q()` on one line is 2. A function's calls of itself go through its slot, so a
  redefined `let rec` function's old callers reach its new body.
- **`let x = 2 and y = x`** computes every member's value before binding any, so `y` gets the `x` before the
  redefinition.
- **A `var` slot** is redefined by `let var x = e`, which stores to it as `x := e` does; functions still may not name a
  global `var`.
- **Modules' bodies are closed**: they cannot name the bindings around them, so no module names a slot, and a module's
  members are never slots. A module declared again replaces the first, as before (§5).
- **Types are not redefined**: `Let T = ...` again shadows, and a function whose type names the old `T`, redefined
  with the new one, shadows too.

**The warning.** A top-level `let` that shadows a slot, because its type or `var`-ness differs, writes a warning on
standard error, and the input runs:

```
<repl>:1:1: warning: 't' now has a different type; functions defined earlier keep the earlier 't'
```

It is the only shadowing left at an interactive top level, so it names exactly the case that surprises.

**Rollback.** A redefinition is an assignment: an input that fails after redefining a slot leaves the slot's new value,
as it leaves a `:=` (§5). The environment and the values still agree, since a redefinition keeps the slot's type.

**How.** The type checkers (`_declare_let` in `quest/typechecker/bindings.py`, `declareLet` in
`questlang/typechecker/bindings`) map each interactive top-level `let`'s symbol to its slot, in the environment's
`slots` (part of its snapshot), and mark a redefining `let` (`TypedLetValue.redefines`, `LetValue.redefines`,
`:redefines` in the dump); they report the warning, the self-hosted checker through its `warnings`. The drivers set
`interactive` on the environment for the REPL and for `-i`. The interpreters, whose frames bind by name, store a
redefinition where the name is bound, as an assignment does (`bind_let`, `bindLet`), instead of opening a frame for
it. The JIT holds each slot in a box, which uses load and redefinitions store to ([jit.md](jit.md) §3.2).

**The cost**, on the JIT: a use of a slot is a load when it runs, so interactive code's top-level functions are called
through their slots, never inlined, specialized, or called directly. Calls from a later input already went through the
earlier input's record, and pay little more; calls within the input that defines the function lose what inlining
gave. Typed at the REPL (2026-11-02, the best of three, each including about 0.1 s for the session):

| Loop | Lexical | Redefinable |
|---|--:|--:|
| 200 million calls of an earlier input's `add1` | 0.32 s | 0.35 s |
| 200 million calls of `add1`, all in one input | 0.17 s | 0.30 s |
| 100 million calls of an earlier input's generic `twice` | 2.17 s | 2.57 s |
| 100 million calls of `twice`, all in one input | 0.17 s | 2.43 s |

So a file run with `-i` is slower than the same file run as a program; a program pays nothing.

---

## 7. Signals & Exit

- **`Ctrl-D` (EOF):** On an empty input line, exits the REPL cleanly with exit code `0`.
- **`Ctrl-C` (Interrupt):** Cancels the current multi-line input buffer without terminating the session, returning to
  `">>  "`.

---

## 8. The Two Implementations

The two REPLs are the same loop over the same steps; only their languages differ.

| Step | Bootstrap (`quest/repl.py`) | Self-hosted (`questlang/driver/repl`) |
| :--- | :--- | :--- |
| Completeness | `check_input_completeness` | `incomplete`: an unclosed comment or string, or a syntax error at the end of the input |
| Snapshots | `Environment.snapshot`, `RuntimeEnvironment.snapshot` (the unit graph inside) | `env.snapshot`, `graph.snapshot`, `treewalk.snapshot` |
| Sessions | `UnitGraph.new_session` | `graph.newSession` |
| Running | `compile_phrase`, then the interpret phase's phrase results | `treewalk.evalProgramPhrasesIn`, which also gives the frame the next input runs in |
| Input | `io/readline` through the interpreter's Python `readline` | `io/readline` through `runtime/quest_readline.c` |

The self-hosted snapshots leave out two things the bootstrap's record, neither observable: a symbol counter (the
bootstrap's ids come from a global allocator that no restore resets, so they are never reused either) and a frame's
parent (which cannot change in `model.Frame`). The two `io/readline`s differ too: the self-hosted interpreter's is
the compiled library, built with GNU readline or libedit, and the bootstrap's is Python's `readline`, with the same
history file format ([new-libraries.md](new-libraries.md) §3.1). Each driver decides for itself whether standard input
is a terminal: Python's `isatty` in the bootstrap's, `system.isTerminal` in the self-hosted one.
