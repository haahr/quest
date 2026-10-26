# Quest Interactive REPL

This document describes the Quest interactive Read-Eval-Print Loop (REPL), its execution modes, input buffering
rules, prompt formatting, terminal handling, and error recovery.

---

## 1. Overview

The Quest REPL provides an interactive top-level environment for evaluating Quest expressions, defining variables and
functions, importing modules, and experimenting with types.

Key features:
- **Persistent Lexical and Dynamic Environments:** Types, bindings, and modules defined in one phrase remain in scope
  for subsequent phrases.
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
Running `quest` without arguments from an interactive terminal (TTY) enters the REPL directly:

```bash
$ quest
>>  let a = 10
==  let a:Int = 10
>>  a * 4
==  40 : Int
```

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

The rollback (`QuestREPL.evaluate`) restores the type checker's environment and the runtime environment: their
bindings, the frame evaluation continues in, and the units the input loaded. The REPL keeps one unit graph
(`docs/build-process.md` §2.1) for its whole session, which holds the interfaces and modules loaded so far, with their
typed forms; the runtime environment holds that same graph, and the values of the modules the interpreter has run
(`module_values`). An input that fails forgets the units it loaded and the modules it ran, so that importing a module
again elaborates and runs it again, as if the failed input had never been. Side effects are not undone: output already
written stays written, and a variable of an earlier binding or module assigned by the failed input keeps its new value.

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

## 6. Signals & Exit

- **`Ctrl-D` (EOF):** On an empty input line, exits the REPL cleanly with exit code `0`.
- **`Ctrl-C` (Interrupt):** Cancels the current multi-line input buffer without terminating the session, returning to
  `">>  "`.
