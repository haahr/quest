# Exception Tracebacks (`docs/exceptions.md`)

This document specifies how an uncaught Quest exception is reported, with where it was raised and the Quest functions
active at the time, in the tree-walking interpreter (`quest/interpreter/treewalk.py`), the IR interpreter
(`quest/interpreter/ir_interp.py`), and compiled code (`quest/ir/`, `quest/codegen/c/`, and `runtime/`).

Status: **design**. Nothing described here is implemented yet; §7 is the plan. Its first step replaces the task
"Uncaught exceptions are reported at the wrong place, or none" in `docs/tasklist.md`.

---

## 1. Goals

1. **The raise site, exactly, everywhere.** Every backend reports the source location of the `raise`, or of the
   checked operation (division, array index, variant tag), that raised the exception. This is the part users need
   most, and it is cheap and exact in every backend, so it comes first (§7, step 1).
2. **The active Quest functions, most recent first.** The interpreters report every frame. Compiled code reports an
   ordered subsequence of them: the C compiler inlines functions and turns tail calls into jumps, and those frames are
   lost. A frame compiled code cannot attribute with certainty is left out, never guessed.
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

---

## 3. Raise Sites

### 3.1. In the IR

`ir.Unit` gains the source map of its file, and the IR nodes that can raise gain `offset: Optional[int]`, copied from
the typed expression they are lowered from: `ir.Raise`, `ir.Prim` (checked arithmetic, ordinal checks),
`ir.ArrayNew`, `ir.ArrayGet`, `ir.ArraySet`, `ir.VariantAssert`, and `ir.AutoInspect`. The passes copy offsets with
the nodes, as they copy everything else.

A try's handler raises the caught exception again when no branch matches. Today that is `ir.Raise(exception)` with
the handler's variable, recognized in the C printer by the variable's identity (`handler_vars`). It becomes its own
terminator, `ir.Reraise(exception)`, which keeps the original raise site (and, in compiled code, the original frames;
§5.4). `ir.Raise` then always makes a new raise.

### 3.2. In the Interpreters

`QuestException` already has `offset`, and `in_unit` (`quest/diagnostics.py`) attaches an imported unit's source map
to errors raised while elaborating it. Raise sites use the same two fields rather than a new location type:

- The tree-walking interpreter tracks the source map of the unit whose code it is running (the program's, or a module
  file's while running that module's code), and sets it on a `QuestException` as it sets `offset`. Today an exception
  raised in `lib/dynamic.mod.quest` is rendered at its offset in the program's source, which can name a line past the
  end of the program.
- The IR interpreter sets `offset` from the raising node and the source map from the unit.
- `ir.Reraise` and a non-matching `TypedTry` raise the original `QuestException` object, so its site is kept.
- An exception raised by a `@qchecked` builtin backing an `external` has no offset: there is no Quest location to give
  it (§2.1).

### 3.3. In Compiled Code

The C printer turns an offset into a string literal `"file:line:col"`, one per raising site.

- `ir.Raise` prints `quest_raise_at(exc, payload, "file:line:col")`.
- The cold helpers of checked operations (`quest_raise_int_error`, `quest_raise_array_error`,
  `quest_raise_variant_error`, `quest_option_ordinal_error`, ...) take the location as an argument. The literal is
  referenced only on the failing branch, so the path that does not raise is the same compare-and-branch as now.
- Out-of-line runtime primitives raise with a null location.
- `QExceptionState` gains `const char *loc`, so a caught exception carries its raise site into the handler, and
  `ir.Reraise` prints `quest_reraise(state)`, which raises with the same location.

---

## 4. Frames in the Interpreters

The interpreters may keep per-call state, so they keep an explicit stack of frame names.

- `RuntimeEnvironment` gains `call_stack: list[str]`, shared by every scope and by both interpreters, which call each
  other (the IR interpreter runs imported library modules with `treewalk.py`, and library functions call back into IR
  closures).
- Both push `<main>` while running the program's phrases, `<module>.<init>` while initializing a module, and a
  function's name for the duration of each call (popped in a `finally`). Unnamed functions push nothing.
- A `QuestException` gains `frames: tuple[str, ...]`, set the first time the exception passes an interpreter boundary
  without them, to the stack reversed. A re-raise keeps them.

Names are given by the rules of §2.3 where functions are made:

- The elaborator records a let-bound function's binder on its `TypedFun` (a `binder: Optional[str]` field, set with
  `dataclasses.replace` where the let is elaborated, since typed nodes are frozen).
- The tree-walking interpreter qualifies it when it makes the closure: the name of the frame making the closure is the
  name of the function lexically enclosing it (or `<main>`, which adds no prefix, or `M.<init>`, which adds `M.`).
  `QClosure` gains `trace_name`, kept by `instantiate`.
- `ir/lower.py` qualifies it the same way from the function being lowered, and sets `ir.Function.trace_name`.
  Specialized clones and lifted closures keep it; functions the IR passes make (adapters, thunks) have none.

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

- `ir.Try` gains `catches`: the atoms of its patterns, evaluated before the try (`lower.py` hoists them); or `ALL`,
  when it has an `else` branch; or `UNKNOWN`, when some pattern is not pure. The handler still tests the patterns as
  now, against the hoisted atoms.
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
calling conventions of those static functions. `tests/perf/measure.py` measures the cost (`docs/testing.md`) before
this step lands.

### 5.3. Walking and Attributing Frames

The runtime walks the stack with the platform unwinder (`<unwind.h>`), on macOS (libSystem) and on Linux with glibc,
where clang and gcc emit unwind tables at `-O2` by default:

- `_Unwind_Backtrace` visits each frame; `_Unwind_GetIP` gives its return address, `ip`;
- `_Unwind_FindEnclosingFunction(ip - 1)` gives the start of the function containing the call, from the unwind tables
  (`ip - 1`, because a call to a `noreturn` helper may be a function's last instruction);
- the frame is attributed to the table entry whose address is **exactly** that start, and skipped if there is none.

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

## 6. Testing

1. **Run-error goldens** (`tests/golden/errors/run/*.error`) still match: the header is unchanged.
2. **Raise sites** (step 1): error tests whose `.error` patterns include the location, run in every phase: a `raise`
   in the program, each checked operation, a raise inside a library module's Quest code, a raise inside an external,
   and a re-raise through a `try` whose branches do not match. A unit test runs a binary directly and checks the
   format of §2.2.
3. **Interpreter frames** (step 2): for a set of traceback programs (nested and recursive calls, closures, module
   functions, library callbacks, re-raises), the full output of `interpret` and of the four `run_ir_*` phases is
   identical.
4. **Compiled frames** (step 3): for the same programs, `run_c_compiled` reports the same header and raise site as
   `interpret`, and its frames are a non-empty ordered subsequence of the interpreter's that ends with `<main>`.
   Separate cases cover each outcome of §5.1: an exception caught by a listed handler, by `else`, not caught, and
   re-raised through an `UNKNOWN` handler.

---

## 7. Plan

### Step 1: Raise sites in every backend

- Offsets on the raising IR nodes and the source map on `ir.Unit` (§3.1); `ir.Reraise`.
- Interpreters: the source map of the running unit on raised exceptions; offsets from IR nodes (§3.2).
- C: `quest_raise_at`, location arguments on the cold helpers, `loc` in `QExceptionState`, `quest_reraise` (§3.3).
  The binary prints the `at` line (§2.2).
- `run_c_compiled` parses the binary's output into a located diagnostic (§2.2).
- **Done when:** the tests of §6.2 pass in every phase, the task "Uncaught exceptions are reported at the wrong place,
  or none" is removed from `docs/tasklist.md`, and `ABI_VERSION` is bumped (the runtime's raise helpers change).

### Step 2: Frames in the interpreters

- `TypedFun.binder`; `QClosure.trace_name` and `ir.Function.trace_name`, qualified as in §4.
- `RuntimeEnvironment.call_stack`, pushed and popped by both interpreters; `QuestException.frames`.
- `Diagnostic.trace` and its rendering (§2.1).
- **Done when:** the tests of §6.3 pass.

### Step 3: Frames in compiled code

- Measure with `tests/perf/measure.py` with function tables emitted and registered (§5.2), before going further.
- `ir.Try.catches`, with pure patterns hoisted in `lower.py`; the handler fields and the chain walk of §5.1.
- Stack walking and exact attribution (§5.3), captured frames (§5.4), and `-fno-reorder-blocks-and-partition` for gcc.
- **Done when:** the tests of §6.4 pass, and `docs/c-representation.md` and `docs/runtime-design.md` describe the
  handler fields, the function tables, and frame printing.
