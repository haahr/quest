# Exception Tracebacks (`docs/exceptions.md`)

This document specifies how an uncaught Quest exception is reported, with where it was raised and the Quest functions
active at the time, in the tree-walking interpreter (`quest/interpreter/treewalk.py`), the IR interpreter
(`quest/interpreter/ir_interp.py`), and compiled code (`quest/ir/`, `quest/codegen/c/`, and `runtime/`).

---

## 1. Goals

1. **The raise site, exactly, everywhere.** Every backend reports the source location of the `raise`, or of the
   checked operation (division, array index, variant tag), that raised the exception. This is the part users need
   most, and it is cheap and exact in every backend.
2. **The active Quest functions, most recent first.** The interpreters report every frame. Compiled code reports an
   ordered subsequence of them: the C compiler inlines functions and turns tail calls into jumps, and those frames are
   lost. A frame compiled code cannot attribute with certainty is left out, never guessed. Fewer frames from compiled
   code is accepted, not a bug to fix (§2.4).
3. **No cost to code that does not raise, nor to raises that are caught.** Compiled function entry and return are
   unchanged: no shadow stack, no frame links. Entering a `try` costs a few stores (§5.2). A raise walks the stack only
   when the exception will not be caught.
4. **One format.** The driver renders an uncaught exception like any other located error, with the source line, and
   the frames after it; a binary run on its own prints the same information as plain lines (§2).

---

## 2. Output

### 2.1. Through the Driver

An uncaught exception is a diagnostic located at its raise site, followed by its frames:

```text
tests/source/errors/run/divide_by_zero.quest:4:13: error: Exception: int.error
    let inner(n: Int): Int = n div 0;
                             ^
  in inner
  in outer
  in <main>
```

The header and source line are what the interpreter prints today. The `in` lines are new: a `trace` field on
`Diagnostic` (`quest/diagnostics.py`), rendered after the source line and any notes. Run-error goldens
(`tests/golden/errors/run/*.error`) match the substring `error: Exception: <name>`, which is unchanged.

An exception raised inside an external C primitive (`quest_string_get_char`, say) has no raise site: the diagnostic
has no label, and the first frame is the Quest function that called the primitive (when it was not inlined). An
exception raised in a library module's Quest code (`raise error` in `lib/dynamic.mod.quest`) is located in that file.

The interpreters format a non-`Ok` payload on the header line (`Exception: E with 42:Int`); compiled code does not
know the payload's type and prints `Exception: E`, as now.

### 2.2. From a Binary

A compiled program run directly prints the same information on `stderr`, without the source line:

```text
Exception: int.error
  at tests/source/errors/run/divide_by_zero.quest:4:13
  in inner
  in outer
  in <main>
```

The `at` line is omitted when there is no raise site. File names are `display_file_name` (`quest/syntax/sources.py`)
of the source file, fixed at compile time. The `run_c_compiled` phase parses this output into the diagnostic of
§2.1, reading the named file for the source line (and rendering without it if the file cannot be read). This
replaces today's `Diagnostic.make_error(stderr, 0)`, which places every compiled exception at `1:1`.

### 2.3. Frame Names

Interpreters and compiled code name frames the same way:

| Construct | Name | Example |
| :--- | :--- | :--- |
| Function bound at the top level (`let f(x: T): U = ...`, `let rec`, `let f = fun ...`) | its binder | `factorial` |
| Function bound in a module's body | module name `.` binder | `strutil.split`, `M.helper` |
| Function bound inside another function `p` | `p` `.` binder | `outer.step`, `strutil.split.step` |
| Function that is not let-bound | enclosing name `.<anon>`, or `<anon>` at the top level | `map.<anon>` |
| Module initializer | module name `.<init>` | `strutil.<init>` |
| The program's phrases | `<main>` | `<main>` |

A module's name is the last component of its canonical path (`strutil` for `util/strutil`), or the name a program
gives a module it declares. Compiler-generated functions (closure environments' thunks, function-type adapters,
`type_app` thunks, module export wrappers) have no name and are never reported.

`k > 1` consecutive frames with the same name are printed as one `in <name>` line followed by
`  ... <name> repeated <k-1> more times`.

### 2.4. Compiled Code Lists Fewer Frames

The exception and its raise site are the same in every backend (compiled code omits a payload, §2.1). The frames
are not: compiled code lists an ordered subsequence of the interpreters' frames, often far fewer, and that is accepted.
Generated C is compiled with `-O2`, and the frames of functions the C compiler inlines into their callers, or calls
by a jump in tail position, do not exist at run time; recovering them would need either a shadow stack (a cost on
every call, against §1's third goal) or reading the C compiler's debug information for inlined code. For

```quest
let a = 1
let e = exception E end
let f(n: Int): Int = raise E end
f(a)
```

the interpreters list `in f` and `in <main>`, and compiled code only `in <main>`, since `f` is inlined into the
program's initializer. Frames are also lost in a gcc cold section when the driver's flag does not apply (§5.3), and
all of them on a platform without the unwinder's functions. Whatever is listed is in the interpreters' order and
ends with `<main>`, and nothing is listed that was not running.

To see every frame, run the program with the interpreter (`--stop-after interpret`) or the IR interpreter
(`--stop-after run_ir_represented`), which report the same raise site.

---

## 3. Raise Sites

### 3.1. In the IR

`ir.Unit` has the source map of its file (`source_map`, from the environment's when the unit is lowered), and the IR
nodes that can raise have `offset: Optional[int]`, copied from the typed expression they are lowered from: `ir.Raise`;
`ir.Prim` (integer and real arithmetic); `ir.Payload` (`v!tag`); `ir.MakeOption` (a computed ordinal);
`ir.ArrayRep`, `ir.Index`, `ir.AddrElement`, and `ir.StoreElement` (array counts and bounds); and
`ir.Inspect` (an auto value no case matches). The passes copy offsets with the nodes, as they copy everything else.

The IR lowers calls of the standard library's `arrayOp.new`, `get`, and `set` to the array operations themselves,
so their errors are located at the call. The tree-walking interpreter runs `lib/arrayop.mod.quest`, whose functions
raise the errors themselves, so it locates them in that file: the one place the backends report different sites.

A try's handler raises the caught exception again when no branch matches, with its own terminator,
`ir.Reraise(exception)`, which keeps the original raise site (and, in compiled code, the original frames; §5.4).
`ir.Raise` always makes a new raise.

### 3.2. In the Interpreters

`QuestException` already has `offset`, and `in_unit` (`quest/diagnostics.py`) attaches an imported unit's source map
to errors raised while elaborating it. Raise sites use the same two fields rather than a new location type:

- The tree-walking interpreter's scopes have the source map of the file whose code runs in them (`RuntimeEnvironment.
  source_map`: the program's, set by the interpret phase, or a module file's, set when the module is loaded). Every
  closure is applied by `run_closure`, which gives an error raised in the closure's body the source map of the scope
  the closure was made in, unless the error has one already; so does a module's initialization. (Before, an
  exception raised in `lib/dynamic.mod.quest` was rendered at its offset in the program's source, which could name a
  line past the end of the program.)
- The IR interpreter sets `offset` from the raising node and the source map from the unit, for errors the operation
  raises that are not located already.
- `ir.Reraise` and a non-matching `TypedTry` raise the original `QuestException` object, so its site is kept.
- An exception raised by a `@qchecked` builtin backing an `external` has no offset: there is no Quest location to give
  it (§2.1).

### 3.3. In Compiled Code

The C printer turns an offset into a string literal `"file:line:col"`, one per raising site.

- `ir.Raise` prints `quest_raise_at(exc, payload, "file:line:col")`.
- The checked operations and their cold helpers have `_at` versions that take the location
  (`quest_int_div_at`, `quest_check_array_bounds_at`, `quest_check_array_count_at`, `quest_real_divide_at`,
  `quest_check_option_ordinal_at`, `quest_raise_variant_error_at`, `quest_raise_dynamic_error_at`, ...). The literal
  is referenced only on the failing branch, so the path that does not raise is the same compare-and-branch as before.
- The versions without `_at`, which the runtime's primitives use, raise with a null location.
- A fatal run-time error with a site (an option ordinal out of bounds) prints the same `at` line after its message.
- `QExceptionState` gains `const char *loc`, so a caught exception carries its raise site into the handler, and
  `ir.Reraise` prints `quest_reraise(state)`, which raises with the same location.

---

## 4. Frames in the Interpreters

The interpreters may keep per-call state, so they keep an explicit stack of frame names.

- `RuntimeEnvironment.call_stack: list[str]` is shared by every scope and by both interpreters, which call each other
  (the IR interpreter runs imported library modules with `treewalk.py`, and library functions call back into IR
  closures).
- The interpret phase and the IR interpreter's `run` push `<main>` while running the program (the IR interpreter's
  around its imports too, which the source interpreter runs when the program's import phrase runs); both push
  `<module>.<init>` while initializing a module (`run_module_init`, `Interpreter.in_frame`); and both push a function's
  name for the duration of each call (`run_closure` for closures, functions defined as externals included, and
  `Interpreter.apply` for IR functions), popped in a `finally`. The functions the IR passes make push nothing.
- `QuestCompilerError.frames: Optional[tuple[str, ...]]`, rendered as `Diagnostic.trace`, is set the first time an
  error leaves a frame without them (`note_frames`), to the stack reversed. A re-raise keeps them. Fatal run-time
  errors (an option ordinal out of bounds) have frames as exceptions do.

Names are given by the rules of §2.3 where functions are made (`frame_name`, `quest/diagnostics.py`). A let-bound
function is the value of a `TypedLetValue`, which both consumers see, so the binder needs no field of its own:

- The tree-walking interpreter names a closure when it makes it (`make_closure`), from the binder, if any, and the
  frame making it, which is the function lexically enclosing it (or `<main>`, or `M.<init>`). `QClosure.trace_name`
  is kept by `instantiate`; `QClosure.name`, which printing shows, is unchanged.
- `ir/lower.py` names a function the same way from the frame of the code being lowered (`_Lowerer.frame`), and sets
  `ir.Function.trace_name`. Specialized clones and lifted closures keep it.

The two implementations of the rule are checked against each other by the tests of §6.

---

## 5. Frames in Compiled Code

### 5.1. Whether an Exception Will Be Caught

Compiled code finds the frames by walking the native stack, which is only possible before `longjmp` unwinds it. To
avoid walking the stack for exceptions that are caught, a raise first asks whether a handler will catch the exception.

A `try`'s handler compares the exception with each branch's pattern, in order, with `is`; with an `else` branch it
catches everything. A pattern is an expression, evaluated today after the exception is caught. When every pattern is
**pure** (an immutable variable, a constant such as a built-in exception, or a field of a module record) evaluating it
before the try's body gives the same value, so the try can record what it catches when it is entered:

- `ir.Try` gains `catching` and `catches`: `CATCH_LISTED` and the atoms of its patterns, evaluated before the try
  (`lower.py` hoists them); or `CATCH_ALL`, when it has an `else` branch; or `CATCH_UNKNOWN`, when some pattern is not
  pure. The handler still tests the patterns as now, against the hoisted atoms.
- `QExceptionHandler` gains `const QException *const *catches` and `int n_catches`, with `-1` for `ALL` and `-2` for
  `UNKNOWN`. Entering a `try` stores them, from a local array of the catch atoms that lives as long as the try's
  block. The handler is popped on every way out of the block, as now.

`quest_raise_at` walks the handler chain from the innermost handler:

- a handler that catches the exception, or catches everything: it **will be caught**. Set `quest_current_exception`
  and `longjmp`, as now.
- a handler that does not list it: go on to the next.
- an `UNKNOWN` handler: it **might be caught**. Capture the frames (§5.4), then `longjmp`.
- the end of the chain: it **will not be caught**. Print the exception and its frames from the live stack (§5.3) and
  `exit(1)`, without allocating.

`quest_reraise` walks the chain the same way from the next handler out, and prints the captured frames, if any, when
the exception will not be caught. Without captured frames (a raise that was going to be caught, re-raised from a
handler that did not match), it prints the frames from the live stack, which start at the re-raising handler's
function. That is accurate for that point in the program, and happens only when a handler with an `UNKNOWN` pattern
did not match.

### 5.2. Function Tables

Each generated C unit (a program's `.main.c`, a module's `.mod.c`) emits a table of the C functions it defines that
have names, with their names:

```c
static const QFuncEntry qr_funcs[] = {
    { (const void *)&qf_inner_1, "inner" },
    { (const void *)&qf_outer_2, "outer" },
    { (const void *)&main, "<main>" },
};
```

Module initializers are listed as `M.<init>`. Unnamed functions are not listed, and need not be (§5.3).

Each unit registers its table where it registers its record dictionaries, in `qr_register_dicts`, which `main` and
each exported module's initializer call before any code of the unit runs: `quest_register_funcs(qr_funcs, n)`. No
link-time step, generated file, or naming convention for tables is needed. The runtime sorts the registered entries
by address the first time it prints frames.

Taking the address of every named function means the C compiler can no longer drop unused arguments or change the
calling conventions of those static functions. (The printer already makes a static closure of every function, which
takes its address, though one that is not used is dropped.) `tests/perf/measure.py` ([testing.md](testing.md)) shows no
measurable difference in the benchmarks' run times with the tables.

### 5.3. Walking and Attributing Frames

The runtime walks the stack with the platform unwinder (`<unwind.h>`), on macOS (libSystem) and on Linux with glibc,
where clang and gcc emit unwind tables at `-O2` by default:

- `_Unwind_Backtrace` visits each frame; `_Unwind_GetIP` gives its return address, `ip`;
- `_Unwind_FindEnclosingFunction(ip - 1)` gives the start of the function containing the call, from the unwind tables
  (`ip - 1`, because a call to a `noreturn` helper may be a function's last instruction);
- the frame is attributed to the table entry whose address is **exactly** that start, and skipped if there is none.

Linux's unwind tables (`.eh_frame`) describe each function on its own. macOS's compact unwind tables do not: they
describe a run of adjacent functions whose prologues are alike as one entry, so the unwinder's start can be an
earlier function's (a function placed just after `main` was reported as `main`). On macOS, the runtime takes the
start from the symbol table instead (`dladdr`, which has static functions), when it lies between the unwinder's start
and `ip` (`quest_function_start`). A stripped binary has no local symbols, and its frames may be attributed to the
nearest exported function before them; the driver does not strip binaries.

Exact matching attributes nothing by proximity. Frames in the runtime, in the C library, below `main`, and in
compiler-generated functions match no entry and are skipped. An inlined function's code belongs to the function it
was inlined into, as it should. Code that gcc moves to a separate cold section (`f.cold`, which holds the calls to
raise helpers) has unwind information of its own, so it matches no entry, and the frame is lost rather than
misattributed; the driver passes `-fno-reorder-blocks-and-partition` when the host compiler is gcc so that the
raising function's frame is kept. On platforms without these functions the runtime prints no frames.

Frames are printed as they are walked, with repeats collapsed (§2.3), so there is no depth limit.

### 5.4. Captured Frames

When an exception might be caught (§5.1), the raise captures its frames before `longjmp`: the function starts of
§5.3, already collapsed into runs, as `(start, count)` pairs, up to `Q_MAX_TRACE_RUNS` (64) runs, with a flag when
there were more. The capture is allocated with `quest_alloc_atomic` and referenced from `QExceptionState`
(`const QTrace *trace`), so a handler's copy of the caught exception keeps it, even if the handler raises and catches
other exceptions before re-raising. The runs are attributed to names when they are printed. When truncated, the
output ends with `  ... (traceback truncated)`.

---

## 6. Running Out of Stack

Runaway recursion, such as `let rec f(n: Int): Int = f(n + 1)`, ends differently in the interpreters and in compiled
code.

**The interpreters raise `stack.overflow`.** A call that would make more than 1,000 calls of Quest functions active
at once (`MAX_CALL_DEPTH` in `quest/interpreter/primitives.py`, `maxCallDepth` in `questlang/interpreter/primitives`,
`<main>` counting as one) raises the exception `stack.overflow` instead of calling. It is an ordinary exception: a
handler's `else` catches it, and the program goes on, and the REPL reports it and rolls the input back
([repl.md](repl.md) §5). Uncaught, it is reported like any other, its frames collapsed:

```
fib.quest:1:49: error: Exception: stack.overflow
    let rec fib(n: Int): Int = if n < 2 then n else fib(n - 1) + fib(n + 2) end; fib(10)
                                                    ^
  in fib
  ... fib repeated 998 more times
  in <main>
```

The tree-walking interpreters locate it at the call that would have gone too deep; the IR interpreters' calls have no
offsets, so theirs has no site. The limit is the same in both implementations so that their output agrees, and low
enough for both to reach it before their own stacks run out: the bootstrap raises Python's recursion limit to 50
frames per call, and a `RecursionError` that comes first (a body of very deeply nested blocks) is raised as
`stack.overflow` too; the self-hosted interpreter, compiled code itself, uses about 2 KB of C stack per call of a
simple function, well within the 8 MB of the main thread's.

**Compiled code ends.** Compiled code does not count its calls. Runaway recursion runs into the guard page below the
main thread's stack, and a handler for the fault, on a signal stack of its own (`quest_install_stack_guard` in
`runtime/quest_runtime.c`, on macOS and on Linux with glibc), prints `Exception: stack.overflow` and the frames
running, with no site, and exits with status 1, as for any uncaught exception (§2.2); output written before is
flushed. A handler cannot catch it. Other faults keep their default action. The C compiler may turn some runaway recursion
into a loop, such as `1 + f(n + 1)`, which then runs forever rather than overflowing. Since the self-hosted interpreter is
compiled code, the handler also reports the rare overflow of its own stack that comes before its limit.

---

## 7. Testing

1. **Run-error goldens** (`tests/golden/errors/run/*.error`) remain only for errors with no site (raised inside an
   external, or a layout conversion error), and match the unchanged header.
2. **Raise sites:** the run error tests (`tests/errors/run`) run in every phase that runs programs, the four
   `run_ir_*` phases included, and their `(* ERROR *)` comments check the line of the site: a `raise` in the
   program, each checked operation, a raise in a module's function (`raise_in_module`, in `raiser.mod.quest` beside
   it), a raise in a function the program passes to a module (`raise_in_callback`), and a re-raise through a `try`
   whose branches do not match (`reraise_keeps_site`). A unit test in `tests/python/test_quest_driver.py` runs a
   binary directly and checks the format of §2.2.
3. **Interpreter frames:** `tests/python/test_tracebacks.py` checks the frames of programs with nested and
   recursive calls, an anonymous callback, a module's functions and a callback from one, a re-raise, and a module
   initializer that raises, and that the full output of `interpret` and of the four `run_ir_*` phases is identical.
4. **Compiled frames:** for the same programs, `run_c_compiled` reports the same header and raise site as
   `interpret`, and its frames are a non-empty ordered subsequence of the interpreter's that ends with `<main>`
   (not the same frames, §2.4).
   Separate cases cover each outcome of §5.1: an exception caught by a listed handler, by `else`, not caught, and
   re-raised through an `UNKNOWN` handler.
5. **Running out of stack** (§6): `language/stack_overflow_caught` catches `stack.overflow` in every interpreter
   phase, the run error test `stack_overflow` checks its site in `interpret`, the REPL transcript `stack_overflow`
   goes on after it, and `test_tracebacks.py` checks its frames in every interpreter and the compiled report.
