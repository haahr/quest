# Plan: Self-Hosted Quest Browser REPL on WasmGC

**Status:** Draft / Design Plan  
**Target:** Self-hosted Quest compiler (`questlang/`) and REPL running in a browser, targeting WebAssembly with GC (`WasmGC`), with an eventual per-interaction WasmGC JIT.  
**Dev & Test Toolchain:** `wasmtime` (50.0.1), `wasm-tools` (1.263.0), `node` (v26.13.0 / V8 14.6).

---

## 1. Executive Summary

The goal is a self-hosted Quest REPL running in a browser:

1. **AOT WasmGC Backend:** `questlang/` gains a WasmGC backend (`--backend wasm`) that compiles Quest programs and the self-hosted compiler itself (`questlang/driver/main`, ~84K lines across 287 `.quest` files) to `.wasm` modules runnable in `wasmtime`, `node`, and browsers.
2. **Browser Host:** The compiled driver runs in the browser with a JS host shim replacing `lib/os/`, `lib/io/`, and `runtime/`.
3. **Per-Interaction WasmGC JIT:** Instead of falling back to the tree-walking interpreter (`--no-jit`), the browser REPL compiles each user phrase to a small WasmGC module in memory, passes it to `WebAssembly.compile` / `WebAssembly.instantiate`, and executes it against the live session state.

This document identifies the **problematic assumptions** in the target architecture, the **hardest design problems** (especially value representation, polymorphism, lvalues, and cross-module WasmGC types), a **concrete representation and compilation design**, a **phased roadmap**, and **open questions**.

---

## 2. Where the Suggested Design Is Problematic

Several aspects of Quest's existing architecture—and of the C/ARM64 JIT (`docs/jit.md`)—conflict directly with WasmGC and browser execution:

### 2.1. WasmGC Has No Interior Pointers (`@` Lvalues and `OffsetDict`)
In Quest (`docs/c-representation.md` §6.5), functions take `var` (read-write) and `out` (write-only) parameters, and call sites pass `@x`, `@r.f`, `@a[i]`, `@t.1`, or chained paths like `@a[i].f`. The C and ARM64 backends rely on **interior pointers** (`&qv_x`, `(char *)r.val + offset_f`, `&arr->data[i]`).

**Problem:** WasmGC `ref`s can only point to the *head* of a `struct` or `array`. There is no pointer-to-field, no pointer-to-array-element, no pointer-to-local, and no byte-offset pointer arithmetic. This affects:
- `@` lvalues (`var`/`out` parameters)
- `QRecordVal` field access via `offsetof`
- `QOptionHeader` payload access (`(char *)opt + 8`)

### 2.2. WasmGC Strictly Separates Numeric Values from GC References
In C/ARM64, Quest uses a uniform 64-bit word `QVal` (`union { void *p; int64_t i; double r; uint64_t u; }`). Any polymorphic slot (`A::TYPE`), array element, or generic parameter is 8 bytes, regardless of whether it holds an `Int`, `Real`, `Word.T`, or heap pointer.

**Problem:** WasmGC has **no untagged union** of `i64`/`f64` and `anyref`. Reference types (`anyref`, `structref`, `arrayref`, `i31ref`) live on the GC-managed stack/heap; `i64` and `f64` are unboxed value types. You cannot store an unboxed `i64` or `f64` in an `anyref` slot, and `i31ref` only holds 31-bit signed integers (insufficient for 64-bit `Int` and `Word.T`). Therefore, **universal polymorphism requires heap-boxing primitives** (`Int`, `Real`, `Word.T`) when they cross generic `A::TYPE` boundaries or live in generic containers.

### 2.3. Per-Interaction Wasm Modules vs. WasmGC Type Identity
In the ARM64 JIT (`docs/jit.md` §3.2–3.6), each REPL input is compiled into a shared flat address space: `dlsym` resolves host symbols, machine code reads host structs directly, and `os/value` + `os/code` write executable bytes into `MAP_JIT` regions.

**Problem:**
1. **`os/value` and `os/code` cannot exist on WasmGC.** `value.fetch(addr, displ)`, `value.store`, `code.reserve`, and `code.write32` assume linear/native memory and writable executable pages. The WasmGC JIT must instead emit a **Wasm binary module** (`Array(Byte)` / `String`) and ask the host to instantiate it.
2. **WasmGC type compatibility across modules:** WasmGC `struct` and `array` types are *isorecursive* (`rec` groups). Two separately compiled Wasm modules only share a `struct`/`array` type if their `rec` groups are structurally identical (same fields, mutability, supertypes, and order inside the `rec` group). If each REPL phrase emits a custom `rec` group of its own types, `ref.cast` across modules will fail unless all cross-module types live in a **canonical shared `rec` group** (or use generic `array`/`struct` supertypes).
3. **Host/JIT module boundaries:** Each REPL interaction becomes a new `WebAssembly.Module` + `WebAssembly.Instance`. Cross-module calls must go through imported/exported functions, tables, or `funcref`/`struct` values—there is no in-place code patching.

### 2.4. `runtime/quest_runtime.c` and `quest_serialization.c` Cannot Touch WasmGC Objects
Quest currently relies on ~194 KB of C in `runtime/quest_runtime.c`, ~134 KB in `runtime/quest_gc.c`, and ~94 KB in `runtime/quest_serialization.c`.
- `quest_gc.c` is replaced by WasmGC itself (good).
- **Problem:** Compiling `quest_runtime.c` or `quest_serialization.c` to Wasm via clang/LLVM puts them in **linear memory**, which **cannot hold or traverse WasmGC `struct`/`array` references** (except awkwardly through `externref` handle tables across a JS/Wasm boundary). All runtime operations that inspect Quest values (`quest_convert`, `quest_is_subtype`, `quest_record_view`, `quest_make_proxy`, `quest_val_is`, `echo` formatting, `dynamic.extern`/`intern`, string/array ops) should be **written in Quest or emitted directly as WasmGC**, not compiled from C.

### 2.5. Synchronous REPL Loop vs. Browser Main Thread
`questlang/driver/repl` reads lines synchronously via `io/readline` and runs `WebAssembly` synchronously in native code.

**Problem:** In a browser:
- Main-thread JS cannot block on stdin/user input.
- Main-thread `WebAssembly.Module` / `new WebAssembly.Instance` has synchronous size limits in browsers (historically 4 KB–8 MB in V8/Firefox) when compiling large modules like the self-hosted compiler.
- **Implication:** Either run the compiler/REPL in a **Web Worker** (with async `WebAssembly.compile` or `SharedArrayBuffer` for blocking `readline`), or structure the browser REPL as an **event-driven** host API (`repl_init()`, `repl_eval(input)` returning output/errors)—mirroring `--kernel` mode (`docs/repl.md` §2.3), which already separates line reading from phrase evaluation. Even in a Worker, `WebAssembly.compile` for JIT modules is naturally `async` (or uses JSPI `WebAssembly.Suspending` if synchronous from Wasm's perspective).

### 2.6. Wasm Exceptions Are Static, Generative Exceptions Are Dynamic, and Wasm Hides Stack Frames
- Quest exceptions (`exception E of T end`) are **generative**: each evaluation creates a distinct exception identity, and `try ... when E with x` matches by runtime identity. Wasm `exnref` (`tag`) declarations are **static** module items and cannot be generated at runtime.
- Quest produces detailed stack tracebacks (`docs/exceptions.md`) by walking native frame pointers. Wasm `try_table`/`throw` unwinds the stack opaquely with no portable stack inspection API.

---

## 3. Core Design Decisions & Representation

### 3.1. Primitive Types & Universal Polymorphic Value (`anyref`)

| Quest Type | Monomorphic / Specialized Wasm Type | Boxed / Polymorphic (`anyref`) Representation | Notes |
| :--- | :--- | :--- | :--- |
| `Int` | `i64` | `(ref $QBox_Int)` = `(struct (field i64))` | Full 64-bit signed; `i31ref` is only 31-bit so cannot hold all `Int`s. |
| `Real` | `f64` | `(ref $QBox_Real)` = `(struct (field f64))` | Full 64-bit IEEE-754. |
| `Word.T` | `i64` | `(ref $QBox_Word)` = `(struct (field i64))` | Unsigned 64-bit; shares `i64` ops (`i64.add`, `i64.div_u`, `i64.popcnt`, etc.). |
| `Bool` | `i32` (0 or 1) | `i31ref` (`ref.i31`) | Zero-allocation in V8/Wasmtime! |
| `Char` | `i32` (0..255) | `i31ref` (`ref.i31`) | Zero-allocation. |
| `Ok` | `(ref null any)` or `i32` (or eliminated) | `ref.null any` or `(ref.i31 (i32.const 0))` | Distinct from `null` if `anyref` uses `null` as uninitialized. Using `i31(0)` for `Ok` avoids `null` ambiguity. |
| `String` | `(ref $QString)` | `(ref $QString)` | See §3.2. |

**Optimization note:** We can optionally tag small 31-bit `Int`s as `i31ref` and only heap-allocate `$QBox_Int` when outside $[-2^{30}, 2^{30}-1]$. However, starting with uniform `$QBox_Int` is much simpler and avoids a `br_on_cast $i31ref` branch on every generic `Int` unbox; `i31ref` optimization can be added later without changing any ABI if `$QBox_Int` is kept internal to boxing/unboxing.

### 3.2. Strings and Arrays

- **`String`:** Quest strings are mutable byte sequences with $O(1)$ length (`string.length`, `string.getChar`, `string.setChar`, `string.setSub`).
  - Representation: `(struct (field $len (mut i32)) (field $data (mut (ref $QByteArray))))` where `$QByteArray = (array (mut i8))`.
  - Why a wrapper struct instead of bare `(array (mut i8))`? It supports capacity > length for growth if needed, and keeps `QString` distinct from `Array(Char)` / `Array(Byte)` under `ref.test`.
- **`Array(T)`:** In Quest (`docs/c-representation.md` §5.4), arrays are mutable, fixed-length, and **invariant** (`Array(S) <: Array(T)` iff `S == T`).
  - **Key tension:** In C, `Array(Int)` and `Array(A)` (in generic code) have the exact same layout (`QVal data[]`), so passing `Array(Int)` to a generic function `f(A::TYPE a: Array(A))` is a zero-cost pointer cast. In WasmGC, `(array (mut i64))` is **not** a subtype of `(array (mut anyref))`, and copying a mutable array would break aliasing!
  - **Decision:** Represent `Array(T)` uniformly as `(array (mut anyref))` (or `(struct (field (ref (array (mut anyref)))))` if type-tagged, though bare `(array (mut anyref))` is faster and has `array.len` built in!). Elements of `Array(Int)` are boxed `$QBox_Int`—*except* where specialization or whole-program optimization proves an array never flows into unspecialized generic `Array(A)` code. This guarantees 100% semantic compatibility with Quest's generic functions and `Dynamic` without runtime conversion errors.

### 3.3. Tuples and Prefix Subtyping

Quest tuples support **prefix subtyping** (`Tuple x: Int y: Real end <: Tuple x: Int end`), **depth subtyping** on immutable components, **invariance** on `var` components, and **identity** (`is`).

- **Option 1 (Native WasmGC `struct` subtyping):**
  Each tuple shape maps to a WasmGC `struct` inheriting from its prefix:
  - `Tuple end` $\to$ `$QTupleBase = (sub (struct))`
  - `Tuple x: Int end` $\to$ `$QTup_i64 = (sub $QTupleBase (struct (field i64)))`
  - `Tuple x: Int y: Real end` $\to$ `$QTup_i64_f64 = (sub $QTup_i64 (struct (field f64)))`
  - **Problem:**
    1. *Generic `Tuple`s:* Inside `All(A::TYPE)`, `Tuple fst: A snd: Int end` has field 0 of type `anyref`, whereas `Tuple fst: Real snd: Int end` has field 0 of type `f64`. In WasmGC, `(struct (field f64) (field i64))` is **not** a subtype of `(struct (field anyref) (field i64))`.
    2. *Proxies (`QProxy`):* When a tuple is upcast such that a component changes view (e.g., a nested record or closure signature changes), Quest wraps it in a `QProxy` (`docs/c-representation.md` §5.8) rather than copying, preserving `is` identity and `var` sharing. A `$QProxy` struct cannot inherit from `$QTup_i64_f64` because `$QProxy` doesn't have the unboxed `i64`/`f64` fields!
    3. *Cross-module `rec` groups:* Every tuple shape in a REPL phrase would have to agree with host `rec` groups.

- **Option 2 (Uniform Slot Array for Generic/Proxied, Typed Structs for Non-Escaping/Monomorphic):**
  - Every `Tuple` (or every tuple that may be proxied / passed generically) has a common supertype `$QTupleAny = (sub (struct))`.
  - A concrete tuple can be `(sub $QTupleAny (struct (field $slots (ref $QAnyArray))))` (or inline `(array (mut anyref))`), while `$QProxy` is `(sub $QTupleAny (struct (field $orig (ref $QTupleAny)) (field $stored ...) (field $view ...) ...))`.
  - Accessing a component of a tuple that `may_be_proxied` (`codegen/layout`) checks `ref.test $QProxy` (replacing the C low-bit tag check `ptr & 1`), and otherwise casts to the concrete tuple type and reads the slot directly.
  - **Recommendation:** Use typed WasmGC structs (`$QTup_...`) **only** when a tuple is monomorphic and neither its type nor any supertype it is cast to requires proxying (or in specialized functions); otherwise use the uniform `(array (mut anyref))` / `$QTupleAny` representation so generic code, proxies, and cross-module REPL phrases work uniformly without `rec`-group explosion.

### 3.4. Records and Structural Subtyping (Evidence Passing without Byte Offsets)

Quest records have **width + permutation + depth subtyping** (`Record x: Int y: Real end <: Record y: Real end`). In C, `QRecordVal` is `{ void *val; const void *dict; }` where `dict` is an `OffsetDict` of `size_t` byte offsets.

Since WasmGC has no `offsetof` or byte-offset loads, there are two ways to implement Evidence Passing in WasmGC:

1. **Slot-Index Dictionary + `(array (mut anyref))` Payload (Recommended Baseline):**
   - A record payload is `$QRecordPayload = (struct (field $layout (ref $QTypeDescriptor)) (field $fields (ref (array (mut anyref)))))`, with fields sorted alphabetically by name in the payload's creation type.
   - An evidence dictionary (`OffsetDict`) is `(array i32)` mapping the view's alphabetical field index $0 \dots k-1$ to the payload's slot index in `$fields` (plus optional `stored_types` array for depth subtyping, exactly as in `docs/c-representation.md` §5.2!).
   - A first-class `QRecordVal` is either a 2-value multi-value `(ref $QRecordPayload, ref $QOffsetDict)` (unboxed on the Wasm stack and in function parameters/returns!) or a 2-field struct `$QRecordVal` when stored in a slot.
   - **Field read `r.x` (at view index `i`):** `array.get $fields (array.get $dict i)` + `ref.cast` / unbox (plus `quest_convert` if `stored_types != null` and the field is a complex immutable type).
   - **Why this is great for WasmGC + JIT:**
     - Zero per-record-type Wasm `struct` declarations needed!
     - Works seamlessly across separately compiled REPL modules without any `rec`-group coordination for user-defined record types.
     - Dynamic `quest_record_dict(view, layout)` builds `(array i32)` at runtime cleanly.
2. **Typed Struct Payload + Vtable of Getter/Setter `funcref`s (Optional Optimization):**
   - Payload is a typed WasmGC `struct` with unboxed `i64`/`f64` fields; `dict` is a struct of typed getter/setter `funcref`s.
   - Faster for monomorphic hot loops, but requires generating getter/setter functions per field per record type, complicates `stored_types` depth subtyping, and requires cross-module type agreement. Better saved as a later optimization if needed.

### 3.5. Options and Variants

- **Variants (`Variant a: Int b: String end`):**
  - In Quest, variants are unordered, each branch has 1 payload, and upcasting remaps tags via a static `tagmap`.
  - In WasmGC: unboxed multi-value `(i32, anyref)` for local/param/return values (matching `QVariantVal`'s zero-allocation semantics!), and a 2-field struct `$QVariantBox = (struct (field i32) (field anyref))` when stored in an `anyref` slot.
  - Upcasting across unordered subtyping uses a static `(array i32)` tagmap (`array.get $tagmap tag`).
- **Options (`Option a b with x: Bool end ... end`):**
  - Ordered sums with 0+ components per case, `ordinal(o)`, `!` extraction, `var` components in case binders, and `QProxy` support.
  - Representation: `$QOptionAny` supertype, with concrete option values holding `(field $tag i32)` and `(field $fields (ref $QAnyArray))` (where case `a` with 0 fields can share a per-case singleton constant, matching `docs/c-representation.md` §5.3). `$QOptionProxy` is a subtype of `$QOptionAny` holding `(orig, stored, view, tags, cache)` and checked via `ref.test $QOptionProxy`.

### 3.6. Closures and Calling Conventions

- Every Quest closure compiles to a subtype of `$QClosureBase = (sub (struct (field $fn funcref)))` (or a generic `$QClosure = (struct (field $fn (ref $FnSig)) (field $env ...))` where captured variables are stored directly as fields of the closure struct—1 GC allocation instead of C's 2 allocations for `QClosure` + `QEnv`!).
- **Direct calls** to known functions call the Wasm function directly (`call $qf_foo` or `return_call $qf_foo`) without allocating or touching the closure struct.
- **Indirect calls** cast the closure to `(ref $QClosure_Sig)` (or extract `$fn` and `ref.cast` to `(ref $FnSig)`) and invoke `call_ref $FnSig` passing the closure itself as the `env` parameter.
- **Adapter thunks** (`quest_adapt_fun` for `dynamic.be`, `inspect`, and depth-subtyped record fields): work identically to C, wrapping the underlying closure in a new closure struct whose `$fn` converts arguments/results via `quest_convert` and invokes the wrapped closure.

### 3.7. `var`, `out`, and `@` Lvalues (Solving the Interior Pointer Problem)

Since WasmGC cannot take `&x`, `&r.f`, or `&a[i]`, we need a clean representation for `var`/`out` parameters and `@` lvalues:

1. **Local `var` whose `@` address is taken:** Boxed in a 1-field mutable GC struct `$QCell_T = (struct (field (mut T_wasm)))` (just like `lower.boxesSlot` already boxes `var`s captured by REPL slots!).
2. **General `@` Lvalues (`@r.f`, `@a[i]`, `@t.1`, `@x`):**
   - **Recommended Design — Mutable Reference Pair / Capability (`$QRef_T`):**
     Represent a `var T` / `out T` parameter as a WasmGC struct (or unboxed pair) representing a **slot reference**:
     - Either a **polymorphic cell/lens** `(struct (field $get (ref $Getter_T)) (field $set (ref $Setter_T)))` (or a base `$QRef` with subtypes `$QRef_Cell`, `$QRef_ArrayElem(arr, idx)`, `$QRef_RecordField(payload, slot_idx)`).
     - **Why tagged `$QRef` subtypes beat closures:** Creating `(struct.new $QRef_ArrayElem arr idx)` or `(struct.new $QRef_RecordField payload slot_idx)` allocates **one tiny 2-field GC struct** (no closure function generation per call site!), preserves **exact aliasing** (unlike copy-in/copy-out shadow cells—so `swap(@a[i] @a[j])` and `f(@a[i] @a[i])` work 100% faithfully!), and works for `var` parameters passed through multiple levels of calls (`g(@y)` just forwards the `$QRef`!).
     - **Fast path:** For `@x` where `x` is already boxed in `$QCell_T`, `$QCell_T` itself can *be* a subtype of `$QRef_T` (zero extra allocation at `@x` call sites!).
     - **Polymorphic `var p: A`:** Uses `$QRef_Any` (reading/writing `anyref`). When calling an unspecialized polymorphic function with `@x` of unboxed type `Int` (`i64`), a `$QRef_BoxedInt` adapter (or shadow cell) converts between `i64` and `$QBox_Int` on read/write.

---

## 4. Polymorphism and Type Descriptors

Quest's polymorphism combines **parametric polymorphism (`All(A::K)`)**, **bounded quantification (`A <: B`)**, **existential packages**, and **Intensional Type Analysis (`Dynamic`, `Auto`, `inspect`)**.

### 4.1. How Polymorphism Compiles to WasmGC

1. **Uniform Quantifier Rule:**
   Every universal quantifier `(A::K)` compiles to a leading parameter `(param $desc_A (ref $QTypeDescriptor))`.
   - Unbounded `A::TYPE` parameters have Wasm type `anyref` (`(ref null any)`).
   - Bounded `A <: Record ...` / `A <: Variant ...` parameters use the bound's representation (`QRecordVal` / `QVariantVal`) at the caller's own view, plus `$desc_A` for field/tag view-map lookup—identical to `docs/c-representation.md` §5.2 & §5.3.
2. **Selective Call-Site Specialization (`questlang/ir/specialize`):**
   Quest's IR already has `specialize`, which clones polymorphic functions at concrete call sites!
   - On WasmGC, specialization is **even more valuable** than on C/ARM64: specializing `f(:Int ...)` eliminates `$QBox_Int` allocations and keeps `Int`/`Real` in unboxed `i64`/`f64` Wasm locals and parameters.
   - Generic (`anyref`) versions are still emitted for first-class polymorphic closures, polymorphic recursion, and separate compilation boundaries.
3. **Boxing/Unboxing at Generic Boundaries:**
   - The `represent` pass (`questlang/ir/represent`) already inserts `box` and `unbox` plans where native types meet generic `QVal` slots.
   - For WasmGC, `box(Int)` emits `struct.new $QBox_Int`, `unbox(Int)` emits `struct.get $QBox_Int 0 (ref.cast (ref $QBox_Int) v)`. Same for `Real` (`$QBox_Real`) and `Word.T` (`$QBox_Word`). `Bool` and `Char` use `ref.i31` / `i31.get_u`.

### 4.2. Runtime Type Descriptors (`QTypeDescriptor`)

- `QTypeDescriptor` becomes a WasmGC `struct` hierarchy (`$QTypeDescriptor` base + subtypes for record, tuple, variant, option, array, fun, opaque, hole, stored).
- Static closed descriptors are emitted as Wasm `global`s initialized in the module's `start` / init function (or constant `struct.new` in WasmGC constant expressions! Note: WasmGC allows `struct.new` and `array.new_fixed` inside **constant expressions** for `global` initializers, including cyclic/mutually-recursive globals if initialized in `start`!).
- Descriptor templates (`quest_instantiate_descriptor` for open types inside generic functions) are implemented directly in Quest/WasmGC.

### 4.3. Cross-Module Type Identity for Separate Compilation & REPL JIT

To allow separately compiled modules (driver + stdlib + per-interaction JIT modules) to pass `QTypeDescriptor`, `QRecordVal`, `QTupleAny`, `QOptionAny`, `QString`, `QClosureBase`, and `QBox_*` values without `ref.cast` failures:

- **Canonical Shared `rec` Group:** Define a single, fixed WasmGC `rec` group containing all universal runtime/ABI types (`$QTypeDescriptor`, `$QBox_Int`, `$QBox_Real`, `$QBox_Word`, `$QString`, `$QAnyArray`, `$QRecordPayload`, `$QOffsetDict`, `$QTupleAny`, `$QOptionAny`, `$QProxy`, `$QClosureBase`, `$QRefAny`, `$QException`, etc.).
- Every Wasm module emitted by `--backend wasm` (the host driver AND every JIT phrase module) emits **this exact `rec` group as its first type section entries** (or imports them via a shared type/import convention). Because WasmGC type equality is structural on `rec` groups, V8 and Wasmtime treat all of these types as **identical** across every dynamically loaded JIT module!
- **Per-module private types** (e.g. a closure struct `$QEnv_foo` capturing local variables, or a specialized `$FnSig` for a private function) are declared *after* the shared `rec` group, inheriting from `$QClosureBase` or `anyref`.

---

## 5. Runtime, Exceptions, Dynamic, and Browser Host

### 5.1. Eliminating `quest_runtime.c`

| Current C File | WasmGC Replacement |
| :--- | :--- |
| `runtime/quest_gc.c` | **Deleted** — WasmGC handles all allocation, tracing, write barriers, and collection. |
| `runtime/quest_runtime.c` | **Ported to Quest / WasmGC runtime module**: `quest_is_subtype`, `quest_convert`, `quest_record_view`, `quest_record_dict`, `quest_make_proxy`, `quest_val_is`, `quest_identity_hash`, `echo` formatting, `Word` ops (using native Wasm `i64.*` instructions), `String` ops. |
| `runtime/quest_serialization.c` | **Ported to Quest** (`dynamic.extern` / `dynamic.intern`) using WasmGC byte arrays (`String` / `Array(Byte)`) and the WasmGC `QTypeDescriptor`s. |
| `runtime/quest_readline.c` | **Replaced by JS host / Browser UI** (and WASI/Node stdin for CLI testing). |

### 5.2. Exceptions & Tracebacks

- **Control flow:** Use the standard Wasm **Exceptions (`exnref`)** proposal (`tag`, `throw`, `try_table` — supported in `wasmtime 50 -W exceptions=y`, `node v26`, Chrome, Firefox, Safari).
- **Generative Identity:** Declare **one** Wasm tag `$quest_exn (param (ref $QExceptionInstance))`. Each Quest `exception E of T end` allocates a fresh `$QExceptionTag` object at runtime (holding its name and payload descriptor). Raising `E` constructs `$QExceptionInstance(tag, payload_anyref, frames)` and executes `throw $quest_exn`. `try ... when E` catches `$quest_exn` and checks `ref.eq` on `tag`.
- **Tracebacks (`docs/exceptions.md`):** Because Wasm `try_table` does not expose the call stack, maintain a lightweight **shadow frame stack** (a global `array` or linked `$QFrame` chain) pushed/popped around non-leaf functions (or functions that may raise), or capture the shadow stack at `raise` time. (Can be gated by a flag like `--no-tracebacks` if needed for peak speed.)

### 5.3. Tail Calls

- Quest's SSA already identifies tail calls (`questlang/ssa/tailCalls`). Emit Wasm `return_call` / `return_call_ref` (enabled by default in V8/Node 26 and Chrome/Firefox; `-W tail-call=y` in Wasmtime 50). Note: Safari/WebKit tail-call support should be verified if Safari is a required target; if not, a trampoline or non-tail fallback is trivial.

### 5.4. Browser Host & REPL Execution Model

- **Interface:** Model the browser REPL on `--kernel` mode (`docs/repl.md` §2.3):
  - `quest_repl_init()`: initializes stdlib, built-in `.qi` virtual filesystem, and REPL session.
  - `quest_repl_incomplete(text) -> Bool`: drives multi-line continuation prompts in the browser terminal UI.
  - `quest_repl_eval(text) -> Result`: parses, typechecks, compiles (or interprets initially), runs the phrase, captures `==  ...` output and `stdout`/`stderr`, and rolls back on error.
- **Virtual Filesystem for `lib/*.qi`:** Bundle `lib/` interface files (`.qi` or source `.int.quest`) into the Wasm module's data/init or pass them from JS at startup so the in-browser compiler can resolve `import util/maybe : util/Maybe`, etc.
- **REPL JIT Loading:**
  - Just like `docs/jit.md` §3.2, each REPL input is lowered as a phrase unit `qj_<n>` whose module record holds its bindings (`Earlier.boxed` cells).
  - Instead of `os/code`, a `wasmJit` bridge calls an imported host function `host_compile_and_run(wasm_bytes, imports) -> result` (in JS: `WebAssembly.compile(bytes)` -> `WebAssembly.instantiate(mod, importObject)` -> `instance.exports.qj_n_entry()`).
  - Using a **Web Worker** for the REPL allows `host_compile_and_run` to be synchronous from Wasm's perspective (or `async` via JSPI `WebAssembly.promising` / `WebAssembly.Suspending` in Node 26 / Chrome).

---

## 6. Phased Implementation Plan

### Phase 0: Toolchain & Feasibility Smoke Tests (`wasm-tools`, `wasmtime`, `node`)
- Write small hand-crafted `.wat` test modules exercising our core primitives (`$QBox_Int`, `$QRecordPayload` + `$QOffsetDict`, `$QRef` lvalues, `$QClosureBase` + `call_ref`, `$quest_exn` + `try_table`, cross-module `rec` group sharing, `return_call_ref`).
- Validate with `wasm-tools validate`, run in both `wasmtime -W gc=y,function-references=y,tail-call=y,exceptions=y` and `node v26.13.0`, and verify JS `WebAssembly.Module` dynamic instantiation from inside a running WasmGC module.

### Phase 1: Wasm Binary Emitter & Minimal AOT `--backend wasm`
- Build a Wasm binary encoder in `questlang/codegen/wasm/` (emitting sections, `rec` groups, functions, locals, structured control flow from SSA/IR).
- Compile basic Quest programs (arithmetic, functions, closures, tuples, arrays, strings, control flow, `stdout` via WASI / JS host import) and run `tests/source/language/` subsets on `wasmtime` and `node`.

### Phase 2: Full Quest Semantics in WasmGC
- Implement Evidence Passing for records (`$QRecordPayload` + `$QOffsetDict`), variants, options, and `$QProxy` views.
- Implement `$QRef` lvalues for `var`/`out`/`@`.
- Implement `QTypeDescriptor`s, polymorphic `anyref` boxing/unboxing, bounded polymorphism, `Dynamic` (`dynamic.new`/`dynamic.be`/`inspect`), and `Auto`.
- Implement generative exceptions (`$quest_exn` + shadow frames) and port `quest_runtime.c` / `quest_serialization.c` logic to Quest.
- Run the full `tests/source/` suite against `--backend wasm` on `wasmtime` and `node`.

### Phase 3: Self-Hosted Compiler & Interpreter REPL in Browser
- Compile `questlang/driver/main` (initially with the tree-walking interpreter for REPL phrases, plus bundled `lib/*.qi` VFS) to WasmGC.
- Build a minimal browser/Node JS host harness (`repl_init`, `repl_incomplete`, `repl_eval`) and test against `tests/repl/` transcripts in `node`.

### Phase 4: Per-Interaction WasmGC JIT
- Implement `questlang/jit/wasmSession` (mirroring `questlang/jit/session` for `qj_<n>` phrase units, `Earlier` bindings, and rollback, but emitting `.wasm` bytes instead of ARM64 `minst`).
- Wire `host_instantiate_and_run` in Node and Browser (Web Worker + `WebAssembly.compile`/`instantiate` or JSPI).
- Verify `tests/repl/` transcripts pass under the WasmGC JIT in `node` and a browser.

---

## 7. Recorded Decisions

1. **Browser & Engine Support:** Chromium/V8 is sufficient initially (gives us WasmGC, `tail-call`, `exnref`, and JSPI if needed).
2. **Execution Environment:** Run the REPL in a **Web Worker**, using an **event-driven ABI** (`repl_init`, `repl_incomplete`, `repl_eval`) so switching to/from the main thread later requires only JS host glue changes.
3. **Exception Tracebacks:** Full source-level stack tracebacks are deferred to a later phase; initial WasmGC exceptions can omit frame walking.
4. **External `lib/` Primitives:** Browser builds will start with stub/virtual implementations for POSIX `lib/os/` and `lib/io/` modules.
5. **Staged Milestone:** Phase 3 will compile `questlang` with the tree-walking interpreter to WasmGC first, providing a working browser REPL and test oracle before building the per-interaction WasmGC JIT in Phase 4.
6. **Lowering Level (`ir` vs. `ssa`):** The WasmGC backend will lower directly from `ir` (after `specialize`, `closure`, `represent`, `describe`, and `simplify`/`inline`/`contify`), rather than `ssa`. `ir` already has structured control flow (avoiding CFG flattening + relooping) and preserves typed aggregate operations that map directly to WasmGC instructions without `ssa`'s byte offsets or `quest_gc.c` write barriers.
