# Exception Tracebacks (`docs/exceptions.md`)

This document specifies the design and implementation plan for reporting call-stack tracebacks when a Quest exception
is raised and not caught, across the tree-walking interpreter (`quest/interpreter/treewalk.py`), the IR interpreter
(`quest/interpreter/ir_interp.py`), and the C backend (`quest/ir/`, `quest/codegen/`, and `runtime/`).

Status: **design**. Nothing described here is implemented yet; §8 is the implementation plan.

---

## 1. Goals and Constraints

1. **Zero non-raising runtime cost in compiled code.** Normal function entry, execution, and return in compiled C code
   must not push or pop shadow stack frames, maintain frame links, or store per-call source locations. Only code that
   actually raises an exception pays the cost of walking the native call stack.
2. **Statically built per-unit function tables.** Each compiled C unit (`.mod.c` and main `.c`) emits a `const` table
   mapping the start addresses of its generated C functions to their Quest function names. At link time, a small
   generated C file provides a null-terminated array pointing to every linked unit's table.
3. **Preservation across non-matching `try ... when` handlers.** In Quest, a `try ... when` expression catches an
   exception via `setjmp`, tests the exception value against each `when` branch in turn, and re-raises if none matches.
   Because `longjmp` has already unwound the C stack by the time the handler runs, the raw return addresses and raise
   site are captured at the original `raise` and preserved on compiler-generated re-raises.
4. **Uniform output across interpreters and compiled code.** Both interpreters and compiled binaries report the
   uncaught exception, its raise site, and the active Quest call stack (most recent call first, function names only)
   on `stderr`, with `QUEST_TRACEBACK=0` available to suppress the traceback lines.
5. **Inlining tolerance in compiled code.** At `-O2`, the C compiler inlines functions and optimizes tail calls into
   jumps. Compiled tracebacks are not required to recover inlined or tail-called frames; instead, the sequence of
   functions reported by compiled code must be an ordered subsequence of the interpreter's traceback.

---

## 2. Traceback Output Format

When an exception escapes to the top level of a program (uncaught), it is reported on `stderr`.

### 2.1. Header Line and Raise Site

The first line preserves the existing `Exception: <name>` format (matched by `tests/golden/errors/run/*.error`),
followed by the raise-site line when known and the stack frames (most recent call first):

```text
Exception: int.error
  at tests/source/errors/run/divide_by_zero.quest:4:13
  in inner
  in outer
  in <main>
```

When an exception carries a non-`Ok` payload, the interpreters continue to format the payload on the header line
(`Exception: E with 42:Int`), while compiled code prints `Exception: E` (matching current runtime behavior).

The raise-site line has one of two forms:

- `  at <file>:<line>:<col>` when the exception is raised by an explicit `raise` expression or by a compiler-emitted /
  inline runtime check (such as integer or word division by zero, array bounds, or variant tag mismatch) whose source
  location is known at the raise site;
- `  in external <c_symbol>` when the exception is raised inside an out-of-line C runtime or standard-library primitive
  (such as `quest_writer_put_string` or `quest_string_get_sub`) that does not receive a caller source location.

### 2.2. Frame Naming Conventions

Every Quest function and module initializer has a canonical trace name shared by the tree-walking interpreter, the IR
interpreter, and the C printer:

| Construct | Trace Name | Example |
| :--- | :--- | :--- |
| Top-level function bound by `let f = fun ...` or `let rec f = ...` | `<name>` | `factorial` |
| Function bound inside a module `M` (canonical path `util/strutil`) | `<module>.<name>` | `strutil.split`, `M.helper` |
| Function nested inside another function `outer` | `<enclosing>.<name>` | `outer.step` |
| Anonymous function (`fun(...) ... end` not let-bound) | `<enclosing>.<anon>` (or `<anon>`) | `map.<anon>` |
| Module initializer body | `<module>.<init>` | `M.<init>` |
| Program top-level phrase evaluation | `<main>` | `<main>` |

Internal compiler-generated helpers in C—such as closure-conversion environment wrappers, function-type subtyping
adapters (`adapt` thunks), and `type_app` thunks—are recorded in the per-unit C function table so their code ranges are
accounted for (preventing misattribution to an adjacent Quest function), but are flagged as **hidden** so they are
skipped when printing the traceback.

### 2.3. Repeated Frames and Depth Cap

- **Consecutive duplicate collapsing:** If recursive calls produce $k > 1$ consecutive identical frame names in the
  rendered list, the first occurrence is printed as `  in <name>` followed by `  ... <name> repeated <k-1> more times`.
- **Capture cap in compiled code:** Compiled code captures up to `Q_MAX_TRACEBACK` (64) raw return addresses. If the
  stack exceeded `Q_MAX_TRACEBACK` before reaching `<main>`, a final line `  ... (traceback truncated)` is printed.
- **Disabling tracebacks:** Setting `QUEST_TRACEBACK=0` in the environment suppresses the `at ...` and `in ...` lines,
  printing only the `Exception: ...` line.

---

## 3. Raise-Site and Function Name Attribution

For the two interpreters and the C backend to agree on function names and raise sites, two pieces of metadata are
established in the front end and carried through the IR:

### 3.1. Assigning Function Trace Names (`quest/typechecker/` or pre-pass)

During or immediately after typechecking (before either `interpret` or `ir_core` runs), a lightweight pass walks the
`TypedProgram` (and any `TypedModule`) and assigns a `trace_name: str` field on every `TypedFun`:

- When a `TypedLet` or `TypedLetRec` binds a variable `x` to a `TypedFun` (possibly wrapped in `TypedTypeApp` or
  type abstractions), the function's local name is `x`.
- Inside a `TypedModule` with canonical path `canon`, top-level module bindings are prefixed with `canon.`.
- Inside a `TypedFun` with `trace_name = p`, nested functions get `f"{p}.{child_name}"` (or `f"{p}.<anon>"` if not
  directly let-bound).

### 3.2. Source Locations on Raising Nodes

Every `TypedExpr` already carries `offset: int`. In addition, the `SourceMap` (or file name and line/column lookup) of
each compilation unit is attached to the `TypedProgram` / `TypedModule` so offsets can be resolved to
` SourceLoc(file: str, line: int, column: int)`:

- Display file names use `tokens.display_file_name(path)` (path relative to the repository/working root when inside
  it), so golden outputs do not depend on the checkout path.
- In the IR (`quest/ir/nodes.py`), `loc: Optional[SourceLoc]` is added to:
  - `ir.Raise(exception, payload, loc=...)`
  - `ir.Prim(op, args, type, loc=...)` (used for checked arithmetic `/`, `%`, `^^`, option ordinal checks, etc.)
  - `ir.ArrayNew`, `ir.ArrayGet`, `ir.ArraySet` (which raise `arrayOp.error` on negative size or out-of-bounds index)
  - `ir.VariantAssert`, `ir.AutoInspect` (when a tag or dynamic check can raise)
  - `ir.Call` / `ir.CallClosure` / `ir.CallModule` (used by the IR interpreter when an external raises, though C uses
    the external's own symbol for out-of-line external raises; see §3.3).

### 3.3. Raises Inside External / Runtime Primitives

Exceptions can be raised in two ways outside explicit `raise` statements:

1. **Inline compiler-emitted checks** (division/modulo by zero, negative array size, array bounds check, variant tag
   assertion):
   - In the interpreters and in C, these have the exact `SourceLoc` of the Quest operation (`loc`) and report
     `  at <file>:<line>:<col>`.
   - In C, the inline helpers in `runtime/quest_runtime.h` (`quest_int_div`, `quest_int_mod`, `quest_word_div`,
     `quest_word_mod`, `quest_real_div`, `quest_array_bounds_check`, etc.) gain `_at(..., const char *loc)` variants
     (or take `const char *loc` passed by `CPrinter`), passing `loc` (`"file:line:col"`) only to the cold
     `quest_raise_*_at(loc)` call when the check fails. On the non-failing fast path, `loc` is an unused constant
     address or literal that costs nothing if the branch is not taken (or the check is emitted as an inline macro/helper
     whose slow path passes the literal).
2. **Out-of-line C runtime functions** (`quest_string_get_char`, `quest_writer_put_string`, `quest_reader_get_char`,
   etc., called via `external` declarations in `lib/`):
   - Passing a caller source location into every `external` C function would alter the C ABI of all external primitives
     and add an extra argument to every call even when no exception is raised.
   - Instead, out-of-line runtime functions call `quest_raise_at(&quest_exc_..., Q_OK_VAL, NULL, __func__)`, recording
     the C external symbol (e.g. `"quest_string_get_char"`).
   - In the interpreters (`quest/interpreter/builtins.py`), `@qchecked` and external wrappers know the external symbol
     name (`sym_name`) and attach `external_name=sym_name` to any `QuestException` raised within them.
   - Both the interpreters and compiled code therefore report `  in external <c_symbol>` as the raise site, and the
     enclosing Quest wrapper function in `lib/` (e.g. `string.get` or `writer.put`) appears as the first Quest frame if
     not inlined.

---

## 4. Design for the Interpreters

### 4.1. `QuestException` Representation (`quest/values/model.py`)

`QuestException` is extended with traceback state that is populated once at the original raise and augmented as frames
unwind:

```python
@dataclass(frozen=True)
class SourceLoc:
    file: str
    line: int
    column: int

    def format(self) -> str:
        return f"{self.file}:{self.line}:{self.column}"
```

On `QuestException`:

- `raise_loc: Optional[SourceLoc] = None`: The source location of the `raise` or checked primitive operation.
- `external_name: Optional[str] = None`: The C symbol name if raised inside an external primitive (`TypedExternal`).
- `frames: list[str]`: The list of Quest function names on the call stack from innermost (most recent) to outermost
  (`<main>`).
- **Capturing the stack at raise time:** `RuntimeEnvironment` maintains an explicit `call_stack: list[str]` (pushed on
  function, module, and `<main>` entry, popped on exit) and a `source_map: Optional[SourceMap]`. At the moment a
  `QuestException` is first constructed (or first caught at an interpreter boundary),
  `exc.frames = list(reversed(env.call_stack))` snapshots the entire active call stack in one step.
  Because the interpreters are allowed extra runtime parameters and state, maintaining `call_stack` on
  `RuntimeEnvironment` (shared between `treewalk.py` and `ir_interp.py`) handles mixed calls between the IR
  interpreter and tree-walking stdlib modules seamlessly, and guarantees that re-raising an existing `QuestException`
  object across a non-matching `try ... when` handler preserves `exc.frames` and `exc.raise_loc` untouched.

### 4.2. Tree-Walking Interpreter (`quest/interpreter/treewalk.py`)

1. **`QClosure` naming:**
   - Add `trace_name: str = "<anon>"` to `QClosure` (`quest/values/model.py`), preserved across `QClosure.instantiate`.
   - When `eval_expr` evaluates `TypedFun`, it sets `trace_name=expr.trace_name`.
2. **Call stack tracking in `RuntimeEnvironment`:**
   - Add `call_stack: list[str]` and `source_map: Optional[SourceMap]` to the shared state of `RuntimeEnvironment` (so
     `push_scope()` shares the same `call_stack` list reference, while `in_unit` / module loading updates the active
     `SourceMap`).
   - Push `"<main>"` around top-level program execution (`eval_program_phrases`).
   - Push `f"{mod_name}.<init>"` around module evaluation (`TypedModule`).
   - Push `closure.trace_name` around every `QClosure` body evaluation (both in `TypedApp` and in 0-parameter
     `TypedTypeApp`).
3. **Capturing at raise sites:**
   - Explicit `TypedRaise`: resolves `expr.offset` via the current unit's `SourceMap` to a `SourceLoc`, snapshots
     `frames = list(reversed(env.call_stack))`, and raises `QuestException(..., raise_loc=loc, frames=frames)`.
   - Checked operations in `treewalk.py` (or helpers called from `treewalk.py`) and `@qchecked` builtins in
     `builtins.py`: if a `QuestException` is raised without `frames` populated, the `TypedApp` / `eval_expr` boundary
     attaches `raise_loc` (if not an external) or `external_name` (if raised from a `QBuiltinFun` backing an
     `external`), and snapshots `frames = list(reversed(env.call_stack))`.
   - Re-raise in `TypedTry`: when no `when` clause matches, `raise` re-raises the original `QuestException` instance,
     which already has `raise_loc` / `external_name` and `frames` set, so they are not overwritten.

### 4.3. IR Interpreter (`quest/interpreter/ir_interp.py`)

1. **Function trace names on `ir.Function`:**
   - Add `trace_name: str = "<anon>"` to `ir.Function` (`quest/ir/nodes.py`).
   - `ir/lower.py` copies `TypedFun.trace_name` onto the lowered `ir.Function`.
   - `ir/specialize.py` and `ir/closure.py` preserve `trace_name` when cloning specialized functions or lifting
     closures. Adapter thunks created by `ir/represent.py` get `trace_name=""` (hidden).
2. **Shared call stack with `RuntimeEnvironment`:**
   - `_Interpreter` in `ir_interp.py` already receives `runtime_env: RuntimeEnvironment`.
   - `run_unit` pushes `"<main>"` onto `runtime_env.call_stack` while executing `unit.main`, and pushes
     `f"{m.name}.<init>"` while initializing each `ir.Module`.
   - `_Interpreter.call` pushes `fn.trace_name` (when non-empty) onto `runtime_env.call_stack` for the duration of the
     frame and pops it in a `finally` block.
   - Because imported standard-library modules are executed by `treewalk.py` using the same `runtime_env`, calls from
     IR functions into stdlib functions and callbacks from stdlib functions back into IR closures (`QBuiltinFun`
     wrapping `_Interpreter.apply`) share one unified `runtime_env.call_stack`.
3. **Raising and re-raising in IR:**
   - In `ir.Raise`: if `exc` is `_Raised(raised)` and `p is None`, it is a compiler-generated re-raise from a
     non-matching `try` handler, so `raise exc.raised` preserves the original `QuestException` and its traceback.
   - Otherwise, `ir.Raise` constructs a fresh `QuestException` with `raise_loc=s.loc` and
     `frames=list(reversed(self.runtime_env.call_stack))`.
   - Checked IR primitives (`ir.Prim`, `ir.ArrayNew`, `ir.ArrayGet`, `ir.ArraySet`, `ir.VariantAssert`,
     `ir.AutoInspect`) attach `s.loc` and snapshot `self.runtime_env.call_stack` when raising `QuestException`.

### 4.4. Formatting Uncaught Exceptions in the Pipeline (`quest/pipeline.py`, `quest/diagnostics.py`)

Currently, `InterpretPhase` and `RunIrPhase` catch `QuestCompilerError` (which `QuestException` subclasses) and emit it
through `ctx.sink.emit(diagnostic_of(error))`, which renders `error: Exception: <name>`, whereas `RunCCompiledPhase`
takes `proc.stderr.strip()` (`Exception: <name>`) and wraps it in `Diagnostic.make_error(msg, 0)`, which also renders
`error: Exception: <name>` followed by any remaining lines of `msg`.

With tracebacks enabled (`os.environ.get("QUEST_TRACEBACK") != "0"`):
- `QuestException.format_traceback()` formats the `at <loc>` / `in external <sym>` line and the `in <func>` lines (with
  consecutive duplicate collapsing).
- `QuestException.to_diagnostic()` includes those lines in `Diagnostic.message` after the `Exception: <name>` header
  line (and sets `primary_label=None` so the diagnostic renderer prints the same clean multi-line message as
  `RunCCompiledPhase`, rather than a separate compiler source snippet).

---

## 5. Design for Compiled Code (C Backend and Runtime)

### 5.1. Zero Cost on the Non-Raising Path

In compiled C code:
- Function prologues and epilogues are untouched: no frame pointers or function names are pushed to a side stack.
- `try ... when` blocks still compile to a single `QExceptionHandler` linked into `quest_current_exception_handler` plus
  `setjmp(handler.env_jmp)`.
- Inline checks (`quest_int_div_at(a, b, "file.quest:10:5")`) test the divisor first (`if (b == 0)`); only the cold
  branch calls the `Q_NORETURN` helper `quest_raise_int_error_at("file.quest:10:5")`. Because the string literal is
  only referenced in the cold call, the hot path is a single conditional branch followed by hardware division.

### 5.2. Runtime Data Structures (`runtime/quest_runtime.h`)

```c
#define Q_MAX_TRACEBACK 64

/* Flags for QFuncEntry.flags */
#define Q_FUNC_VISIBLE 0u
#define Q_FUNC_HIDDEN  1u  /* Compiler-generated adapter/thunk: skip when printing */
#define Q_FUNC_MAIN    2u  /* Top-level <main>: stop stack walk after this frame */

typedef struct QFuncEntry {
    const void *addr;   /* Start address of the C function */
    const char *name;   /* Quest trace name (e.g. "factorial", "strutil.split", "<main>") */
    uint32_t    flags;  /* Q_FUNC_VISIBLE, Q_FUNC_HIDDEN, Q_FUNC_MAIN */
} QFuncEntry;

typedef struct QFuncTable {
    const QFuncEntry *entries;
    size_t            count;
} QFuncTable;

/* Null-terminated master list of per-unit tables, generated at link time */
extern const QFuncTable *const quest_all_func_tables[];

/* Heap-allocated traceback captured at the original raise site */
typedef struct QTraceback {
    const char *raise_loc;           /* "file:line:col", or NULL */
    const char *external_fn;         /* C function name when raised in an external, or NULL */
    int         n_pcs;               /* Number of captured return addresses */
    void       *pcs[Q_MAX_TRACEBACK];
} QTraceback;

typedef struct QExceptionState {
    const QException *exc;
    QVal              payload;
    QTraceback       *trace;         /* Captured at original raise; preserved across re-raise */
} QExceptionState;
```

> [!NOTE]
> Storing a `QTraceback *` pointer in `QExceptionState` (rather than embedding `void *pcs[64]` directly inside
> `QExceptionState`) keeps `sizeof(QExceptionState)` at 24 bytes. When a `try` handler catches an exception and copies
> `quest_current_exception` into a local variable `QExceptionState l_e = quest_current_exception;`, copying is 24 bytes
> instead of 544 bytes, and if a `when` branch raises and catches a *nested* exception before the outer handler
> re-raises `l_e`, `l_e.trace` still points to the outer exception's intact `QTraceback`.

### 5.3. Raise and Re-raise Entry Points (`runtime/quest_runtime.c`)

1. **`quest_raise_at(const QException *exc, QVal payload, const char *loc, const char *ext_fn)`**:
   - Allocates a `QTraceback *tb = (QTraceback *)quest_alloc_atomic(sizeof(QTraceback))` (unless `QUEST_TRACEBACK=0`).
   - Records `tb->raise_loc = loc` and `tb->external_fn = ext_fn`.
   - Captures the native call stack into `tb->pcs` using `backtrace(tb->pcs, Q_MAX_TRACEBACK)` (see §5.4).
   - If `quest_current_exception_handler == NULL`, prints the exception and traceback to `stderr` and calls `exit(1)`.
   - Otherwise, sets `quest_current_exception = (QExceptionState){ exc, payload, tb }` and calls
     `longjmp(quest_current_exception_handler->env_jmp, 1)`.
2. **`quest_raise(const QException *exc, QVal payload)`**:
   - Compatibility wrapper calling `quest_raise_at(exc, payload, NULL, NULL)`.
3. **`quest_reraise(QExceptionState state)`**:
   - Called by compiler-generated fallback branches of `try ... when` handlers when no `when` clause matches.
   - If `quest_current_exception_handler == NULL`, prints `state.exc` and `state.trace` to `stderr` and calls
     `exit(1)`.
   - Otherwise, sets `quest_current_exception = state` (preserving `state.trace`) and `longjmp`s to the next handler.
   - In the IR, a compiler-generated re-raise is already distinguished from a user `raise` because its `ir.Raise`
     operand is the handler's `exc_var` with `payload=None`. `CPrinter` emits `quest_reraise(l_exc);` for this case and
     `quest_raise_at(exc, payload, "file:line:col", NULL);` for an explicit `raise`.

### 5.4. Stack Walking Mechanism

In `runtime/quest_runtime.c`:

- **Primary mechanism (`<execinfo.h>`):** On macOS (`libSystem`) and Linux (`glibc`), `#include <execinfo.h>` provides
  `int backtrace(void **buffer, int size)`.
  - Requires no extra compiler or linker flags on macOS (which mandates frame pointers on arm64 and x86_64 by ABI) or
    on Linux (where `clang` and `gcc` emit `.eh_frame` unwind tables by default at `-O2`).
- **Fallback mechanism (`__builtin_frame_address`):** On platforms without `<execinfo.h>` (guarded by
  `#if defined(__APPLE__) || (defined(__linux__) && defined(__GLIBC__))`),
  a small frame-pointer walker walks the `(void **)__builtin_frame_address(0)` chain while the frame pointer is
  aligned and strictly increasing within a bounded stack window.

### 5.5. Per-Unit Function Tables Emitted by `CPrinter`

In every generated C unit (`.mod.c` and `.main.c`), `CPrinter` emits a `QFuncTable` at the end of the file:

- Every C function emitted in the unit is included:
  - Normal and specialized IR functions (`qf_...`): `flags = Q_FUNC_VISIBLE`, `name = "<trace_name>"`.
  - Exported module wrapper functions (`qv_<mod>_<member>`): `flags = Q_FUNC_HIDDEN`, `name = ""`. These are 1-line
    wrappers that forward to the underlying closure `qf_...`. Marking the wrapper `Q_FUNC_HIDDEN` ensures its code
    range is claimed in the table without duplicating `<mod>.<member>` when `qf_...` is called out-of-line (and if
    `qf_...` is inlined into the wrapper, omitting it is consistent with any other inlined call).
  - Module initializer (`qv_mod_<mod>_init`): `flags = Q_FUNC_VISIBLE`, `name = "<mod>.<init>"`.
  - Top-level program function (`main` in `.main.c`): `flags = Q_FUNC_VISIBLE | Q_FUNC_MAIN`, `name = "<main>"`.
  - Internal helpers (`qr_register_dicts`, function-type adapters `q_adapt_...`): `flags = Q_FUNC_HIDDEN`, `name = ""`.
- **Table naming:**
  - For a module file whose first exported module has mangled canonical name `<clean>`:
    `const QFuncTable qv_func_table_mod_<clean> = { ... };`
  - For a main program unit:
    `const QFuncTable qv_func_table_main = { ... };`

```c
static const QFuncEntry qr_func_entries[] = {
    { (const void *)&qr_register_dicts, "", Q_FUNC_HIDDEN },
    { (const void *)&qf_inner_1, "inner", Q_FUNC_VISIBLE },
    { (const void *)&qf_outer_2, "outer", Q_FUNC_VISIBLE },
    { (const void *)&main, "<main>", Q_FUNC_VISIBLE | Q_FUNC_MAIN },
};
const QFuncTable qv_func_table_main = {
    qr_func_entries,
    sizeof(qr_func_entries) / sizeof(qr_func_entries[0])
};
```

### 5.6. Link-Time Master Table Generation

Because a program links one `.main.o` and zero or more module `.o` files, the linker needs a definition of
`quest_all_func_tables`.

In `compiler_runner.py` (`link_objects` and `compile_c_source`) and `build/engine.py`:
- Every linked module object corresponds to a canonical module name `<clean>` (known from the build engine's module
  closure or extracted from the `.qm` / object list, or passed as `module_names: list[str]` to `link_objects` and
  `compile_c_source`).
- Right before invoking the host C compiler to link the executable, `compiler_runner.py` generates a small temporary C
  file (or writes `<stem>.tables.c` in `build_dir` when invoked via `BuildEngine`) containing:

```c
#include "quest_runtime.h"

extern const QFuncTable qv_func_table_main;
extern const QFuncTable qv_func_table_mod_std__int;
extern const QFuncTable qv_func_table_mod_util__strutil;
extern const QFuncTable quest_runtime_func_table;

const QFuncTable *const quest_all_func_tables[] = {
    &qv_func_table_main,
    &qv_func_table_mod_std__int,
    &qv_func_table_mod_util__strutil,
    &quest_runtime_func_table,
    NULL
};
```

- Notice `quest_runtime_func_table`: defined in `runtime/quest_runtime.c`, it lists key runtime entry points (with
  `Q_FUNC_HIDDEN`). Including runtime functions in the merged address table bounds the code addresses of adjacent Quest
  functions in the binary's `__text` / `.text` section!

### 5.7. Resolving Return Addresses (`pc`) to Function Names

When an uncaught exception is about to be printed:

1. **Flatten and sort:** The runtime collects all `QFuncEntry` items from `quest_all_func_tables[]` into a single array
   and sorts them by ascending `(uintptr_t)entry.addr`. (This happens at most once per process, right before `exit(1)`.)
2. **Lookup for each return address `raw_pc` in `tb->pcs`:**
   - A return address `raw_pc` points to the instruction *after* the `call` / `bl` instruction. To ensure a call at the
     very end of a function (such as a call to a `Q_NORETURN` raise helper) resolves to the calling function and not
     the next function in the text segment, we search using `uintptr_t query = (uintptr_t)raw_pc - 1`.
   - Binary search the sorted `QFuncEntry` array for the last entry with `(uintptr_t)entry.addr <= query`.
   - **Bounding false matches:** What if `query` is inside `libc` (e.g. `qsort` or `_start` below `main`) or a shared
     library (`libgc`) at a higher address than the last Quest function?
     - First, once the walk encounters an entry with `Q_FUNC_MAIN` (`<main>`), it records `<main>` and stops walking
       outer frames (ignoring C startup frames `_start` / `start` below `main`).
     - Second, we reject any match where `query - (uintptr_t)entry.addr > Q_MAX_FUNC_BYTES` (e.g. `65536` bytes) or, on
       POSIX systems with `<dlfcn.h>` (`dladdr`), where `dli_fbase` does not match `&main`'s image base.
   - If the matched entry has `Q_FUNC_HIDDEN`, it is skipped; if it has `Q_FUNC_VISIBLE`, its `entry.name` is emitted
     into the frame list.

---

## 6. ABI and Precompiled Artifacts

Adding `qv_func_table_mod_<clean>` to every compiled module `.o` changes the set of symbols expected by the link step.
Accordingly:
- `ABI_VERSION` in `bootstrap/python/quest/config/abi.py` is incremented (from 26 to 27) so `BuildEngine` and test
  runners automatically recompile any cached `.qm` / `.mod.c` / `.o` artifacts in `.build/`.

---

## 7. Testing Strategy

1. **Existing Run Error Goldens (`tests/golden/errors/run/*.error`):**
   - `match_error_patterns` in `quest/testing/errors.py` checks that every expected pattern in `.error` appears in
     `stderr`. Because the first line remains `error: Exception: <name>`, all existing `.error` files continue to
     match in both `interpret` and `run_c_compiled`.
   - `format_canonical_error_golden` (used by `--update-golden`) will preserve the first line of the diagnostic message
     unless the test is in the dedicated traceback test suite.
2. **Interpreter vs. IR Interpreter Traceback Equivalence:**
   - Extend the test runner (`run_tests.py` / `tests/python/test_tracebacks.py`) so that for traceback error tests, the
     full `stderr` output (exception line, raise site, and complete list of `in <func>` frames, including `<main>`,
     nested functions, closures, module calls, and `try ... when` re-raises) is compared **identically** between
     `interpret` and all four IR interpreter stages (`run_ir_core`, `run_ir_specialized`, `run_ir_closed`,
     `run_ir_represented`).
3. **Compiled Code (`run_c_compiled`) Subsequence Verification:**
   - For compiled runs of traceback tests, the test harness parses the output of `interpret` and `run_c_compiled` into:
     - `exception_header`: e.g. `Exception: CustomFailure` (comparing the exception name, since C does not format
       arbitrary payloads)
     - `raise_site`: `at <file>:<line>:<col>` or `in external <symbol>`
     - `frames`: ordered list of function names `["inner", "middle", "outer", "<main>"]`
   - It asserts that:
     1. `compiled.exception_name == interp.exception_name`
     2. `compiled.raise_site == interp.raise_site`
     3. `compiled.frames` is a non-empty **ordered subsequence** (and subset) of `interp.frames` (for instance, if
        `inner` was inlined into `middle` by `clang -O2`, `["middle", "outer", "<main>"]` is a valid subsequence of
        `["inner", "middle", "outer", "<main>"]`).
4. **Opt-Out Verification (`QUEST_TRACEBACK=0`):**
   - Unit tests verify that running with `QUEST_TRACEBACK=0` in `interpret`, `run_ir_core`, and `run_c_compiled`
     suppresses all `at ...` and `in ...` lines and prints only the `Exception: <name>` line.

---

## 8. Phased Implementation Plan

### Step 1: Function Trace Names and Source Locations on Typed AST

- **Changes:**
  - Define `SourceLoc(file, line, column)` in `quest/diagnostics.py` (or `quest/syntax/sources.py`).
  - Add `trace_name: str = "<anon>"` to `TypedFun` in `quest/typechecker/typed_ast.py` and `QClosure` in
    `quest/values/model.py`.
  - Implement a small pass `assign_trace_names(program_or_module, module_name=...)` invoked at the end of typechecking
    (`elaborate_program`, `elaborate_module`) that populates `TypedFun.trace_name` according to §2.2.
  - Attach `source_map` to `TypedProgram` and `TypedModule` so offsets can be converted to `SourceLoc` during
    interpretation and IR lowering.
- **Done when:** Unit tests verify `TypedFun.trace_name` for top-level functions, recursive functions, module
  functions, nested functions, and anonymous lambdas; existing test suites pass.

### Step 2: Tracebacks in the Tree-Walking Interpreter (`treewalk.py` & `builtins.py`)

- **Changes:**
  - Extend `QuestException` (`quest/values/model.py`) with `raise_loc: Optional[SourceLoc]`,
    `external_name: Optional[str]`, `frames: tuple[str, ...]`, and traceback formatting (`format_traceback()`), gated on
    `QUEST_TRACEBACK != "0"`.
  - Add shared `call_stack: list[str]` and unit `source_map` tracking to `RuntimeEnvironment`
    (`quest/interpreter/treewalk.py`).
  - Push/pop `"<main>"`, `"<module>.<init>"`, and `closure.trace_name` in `treewalk.py`.
  - Populate `raise_loc` and `frames` on explicit `TypedRaise` and checked operations (`int.error`, `real.error`,
    `word.error`, `arrayOp.error`, `variant.tagMismatch`, `dynamic.error`), and `external_name` + `frames` in
    `builtins.py` when an external primitive raises.
  - Ensure `TypedTry` re-raises preserve the original `QuestException`'s `raise_loc` and `frames`.
- **Done when:** Uncaught exceptions in `interpret` print the raise site and most-recent-first call stack; re-raising
  through a non-matching `try ... when` preserves the original raise site and inner frames; `QUEST_TRACEBACK=0`
  suppresses the traceback; all golden and unit tests pass.

### Step 3: Tracebacks in the IR and IR Interpreter (`quest/ir/` & `ir_interp.py`)

- **Changes:**
  - Add `trace_name: str` to `ir.Function` and `loc: Optional[SourceLoc]` to `ir.Raise`, `ir.Prim`, `ir.ArrayNew`,
    `ir.ArrayGet`, `ir.ArraySet`, `ir.VariantAssert`, and `ir.AutoInspect` (`quest/ir/nodes.py`).
  - Update `ir/lower.py` to populate `trace_name` on functions and `loc` on raising nodes from the unit's `SourceMap`.
  - Update `ir/specialize.py`, `ir/closure.py`, and `ir/represent.py` to propagate `trace_name` and `loc` through all
    IR transformations (marking generated adapter thunks with `trace_name=""`).
  - Update `ir_interp.py` to push/pop `fn.trace_name`, `"<module>.<init>"`, and `"<main>"` on
    `runtime_env.call_stack`, and attach `loc` and `frames` when raising `QuestException` (preserving them on
    `_Raised` re-raises).
- **Done when:** For a suite of traceback test programs (covering nested calls, closures, modules, stdlib calls,
  checked ops, and `try ... when` re-raises), `interpret`, `run_ir_core`, `run_ir_specialized`, `run_ir_closed`, and
  `run_ir_represented` produce identical traceback output.

### Step 4: C Runtime Traceback Capture, Symbol Resolution, and Printing (`runtime/`)

- **Changes:**
  - Define `QFuncEntry`, `QFuncTable`, `QTraceback`, and updated `QExceptionState` in `runtime/quest_runtime.h`
    (updating the `static_assert` on `sizeof(QExceptionState)`).
  - Implement `quest_raise_at`, `quest_reraise`, and `_at` variants of the runtime error helpers
    (`quest_raise_int_error_at`, `quest_raise_array_error_at`, `quest_raise_variant_error_at`, etc.) in
    `runtime/quest_runtime.c` and `runtime/quest_runtime.h`.
  - Update out-of-line runtime primitives in `runtime/quest_runtime.c` and `runtime/quest_serialization.c` to pass
    `__func__` as `ext_fn` when raising.
  - Implement `backtrace()` capture (with `__builtin_frame_address` fallback), lazy merging/sorting of
    `quest_all_func_tables[]`, `pc - 1` binary search with `<main>` termination and address-range validation,
    consecutive-duplicate collapsing, and `QUEST_TRACEBACK=0` checking in `runtime/quest_runtime.c`.
  - Define `quest_runtime_func_table` in `runtime/quest_runtime.c`.
- **Done when:** C runtime compiles cleanly under `-std=c99 -pedantic-errors -Wall -Wextra -O2`.

### Step 5: Emitting Function Tables and Link-Time Master Table (`quest/codegen/` & `quest/build/`)

- **Changes:**
  - Update `CPrinter` (`quest/codegen/c/printer.py`) to:
    - Emit `quest_raise_at(..., "file:line:col", NULL)` for explicit `ir.Raise` and `quest_reraise(...)` for
      handler re-raises.
    - Pass `"file:line:col"` to inline checked operations (`quest_int_div_at`, bounds checks, variant tag assertions).
    - Emit `qv_func_table_main` (in main units) or `qv_func_table_mod_<clean>` (in module units) containing all
      emitted C functions with their `trace_name` and `Q_FUNC_*` flags.
  - Update `compiler_runner.py` and `build/engine.py` to generate and compile the link-time table file defining
    `quest_all_func_tables[]` for all linked units plus `quest_runtime_func_table`.
  - Bump `ABI_VERSION` in `quest/config/abi.py`.
- **Done when:** All compiled golden and error tests build, link, and pass with `ABI_VERSION` bumped.

### Step 6: Traceback Test Suite and Documentation Updates

- **Changes:**
  - Add dedicated traceback tests in `tests/python/test_tracebacks.py` (and/or `tests/source/errors/run/`) verifying:
    - Exact traceback match between `interpret` and `run_ir_*`.
    - Exception name match, raise-site match, and frame subsequence match for `run_c_compiled`.
    - Preservation of original traceback across non-matching `try ... when` blocks in both interpreters and compiled C.
    - Recursive frame collapsing (`repeated N more times`).
    - Suppression via `QUEST_TRACEBACK=0`.
  - Update `docs/codegen-c.md` and `docs/runtime-design.md` to reference `docs/exceptions.md`.
- **Done when:** `python3.11 run_tests.py --phase all` and `python3.11 -m unittest discover -s tests/python` both pass
  with zero failures.
