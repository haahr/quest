# Plan: Self-Hosted Quest Browser REPL on WasmGC

**Status:** Draft / Design Plan (Revised after Architecture Review)  
**Target:** Self-hosted Quest compiler (`questlang/`) and REPL running in a browser, targeting WebAssembly with GC (`WasmGC`), with an eventual per-interaction WasmGC JIT.  
**Dev & Test Toolchain:** `wasmtime` (50.0.1), `wasm-tools` (1.263.0), `node` (v26.13.0 / V8 14.6).

---

## 1. Executive Summary

The goal is a self-hosted Quest REPL running in a browser:

1. **AOT WasmGC Backend:** `questlang/` gains a WasmGC backend (`--backend wasm`) lowering from `ir` to `.wasm` modules runnable in `wasmtime`, `node`, and Chromium/V8.
2. **Browser Host (Web Worker):** The compiled driver runs in a Web Worker with an event-driven ABI (`repl_init`, `repl_incomplete`, `repl_eval`) and JS host shims for `lib/os/`, `lib/io/`, and `Math.*`.
3. **Per-Interaction WasmGC JIT:** Each user phrase is compiled to a small WasmGC module in memory and synchronously instantiated in the Worker via `new WebAssembly.Module` / `new WebAssembly.Instance` against the driver's exports and earlier phrase instances.

---

## 2. Where the Suggested Design Is Problematic

Several aspects of Quest's existing architecture—and of the C/ARM64 JIT (`docs/jit.md`)—conflict directly with WasmGC and browser execution:

### 2.1. WasmGC Has No Interior Pointers (`@` Lvalues and `OffsetDict`)
In Quest (`docs/c-representation.md` §6.5), functions take `var` (read-write) and `out` (write-only) parameters, and call sites pass `@x`, `@r.f`, `@a[i]`, `@t.1`, or chained paths like `@a[i].f`. C and ARM64 use interior pointers (`&qv_x`, `(char *)r.val + offset_f`, `&arr->data[i]`).

**Problem:** WasmGC `ref`s can only point to the *head* of a `struct` or `array`. There is no pointer-to-field, pointer-to-array-element, pointer-to-local, or byte-offset arithmetic.

### 2.2. WasmGC Strictly Separates Numeric Values from GC References
In C/ARM64, Quest uses a uniform 64-bit word `QVal` (`union { void *p; int64_t i; double r; uint64_t u; }`). Any polymorphic slot (`A::TYPE`) is 8 bytes.

**Problem:** WasmGC has **no untagged union** of `i64`/`f64` and `eqref`. Reference types live on the GC heap; `i64` and `f64` are unboxed value types; `i31ref` only holds 31-bit signed integers (insufficient for 64-bit `Int` and `Word.T`). Universal polymorphism requires heap-boxing `Int`, `Real`, and `Word.T` across generic `A::TYPE` boundaries and in generic containers.

### 2.3. Per-Interaction Wasm Modules vs. WasmGC Type Identity & `os/value`/`os/code`
1. **`os/value` and `os/code` cannot exist on WasmGC.** The JIT cannot reserve executable memory or `fetch`/`store` at byte offsets; it must emit `.wasm` bytes and ask the JS host to instantiate them.
2. **WasmGC `rec`-group type identity:** Two separately compiled Wasm modules only share `struct`/`array` types if their `rec` groups are structurally identical. Cross-module types must live in a **canonical shared `rec` group** (§4.3).
3. **Host/JIT module boundaries:** Each REPL interaction is a new `WebAssembly.Module` + `WebAssembly.Instance`. There is no in-place code patching.

### 2.4. `runtime/quest_runtime.c` and `quest_serialization.c` Cannot Touch WasmGC Objects
- `quest_gc.c` is replaced by WasmGC.
- `quest_runtime.c` (~194 KB) and `quest_serialization.c` (~94 KB) cannot be compiled to linear-memory Wasm and directly inspect WasmGC structs/arrays. Runtime operations (`quest_is_subtype`, `quest_convert`, `quest_record_view`, `quest_make_proxy`, `quest_val_is`, `quest_identity_hash`, `dynamic.extern`/`intern`, `echo`) must be **written in Quest or emitted directly as WasmGC**.

### 2.5. Traps vs. Quest Exceptions
WebAssembly traps (integer division by zero, `INT64_MIN / -1`, `f64 -> i64` out-of-range/NaN, array out-of-bounds, failed `ref.cast`, `null` dereference) **cannot be caught by `try_table`**. Every trap that Quest specifies as a catchable exception (`int.error`, `real.error`, `word.error`, `arrayOp.error`) must be **explicitly guarded** before executing the Wasm instruction (§5.1).

### 2.6. Stack Limits & Uncatchable Stack Overflow
Chromium Workers have ~512 KB of stack (~1 MB on the main thread) vs. 8 MB natively. (Probed on Node v26.13.0: ~62,874 minimal 1-param frames in a Node worker, ~15,596 on the main thread, though Chromium's Worker stack is smaller.)
- Wasm stack overflow throws a JS `RangeError` that **no Wasm `try_table` can catch**.
- The compiler's own recursive-descent parser, equi-recursive `is_subtype`, typechecker, and IR passes can hit deep recursion on pathological inputs. When V8 throws `RangeError`, the Worker's JS host catches it, reports `Exception: stack.overflow`, and rolls back or resets the session.

### 2.7. No Object Addresses for Identity Hashing (`hash.identityHash`)
WasmGC objects can be moved by the collector and have no observable memory address. `hash.identityHash` (used as the default by `collections/hashmap` and `collections/hashset`) must use a lazy per-object ID field (§3.8).

---

## 3. Representation & Compilation Design

### 3.1. Universal Polymorphic Value: `eqref` (Not `anyref`)
Use **`eqref`** (`(ref null eq)` / `(ref eq)`) as the universal polymorphic representation (`QVal` equivalent), **not `anyref`**:
- `ref.eq` requires `(ref null eq)` (`eqref`), not `anyref` (verified with `wasm-tools validate`).
- All Quest polymorphic values are WasmGC structs, arrays, `i31ref`, or `$QClosureBase` structs wrapping `funcref`—all of which are subtypes of `eqref`. There are no `externref`s inside Quest values.

### 3.2. Primitives, Boxing, and `i31ref`
| Quest Type | Monomorphic / Specialized Wasm Type | Polymorphic (`eqref`) Representation | Notes |
| :--- | :--- | :--- | :--- |
| `Int` | `i64` | `(ref $QBox_Int)` = `(struct (field i64))` | Full 64-bit signed. |
| `Real` | `f64` | `(ref $QBox_Real)` = `(struct (field f64))` | Full 64-bit IEEE-754. |
| `Word.T` | `i64` | `(ref $QBox_Word)` = `(struct (field i64))` | Unsigned 64-bit. |
| `Bool` | `i32` (0 or 1) | `i31ref` (`ref.i31`) | Zero-allocation. |
| `Char` | `i32` (0..255) | `i31ref` (`ref.i31`) | Zero-allocation. |
| `Ok` | `(ref eq)` / eliminated | `(ref.i31 (i32.const 0))` | Distinct from `null` (which is reserved for uninitialized locals). |
| `String` | `(ref $QString)` | `(ref $QString)` | See §3.3. |

- **Boxing cost:** In `collections/vector.T(A)` and `collections/hashmap(K, V)`, `A`/`K`/`V` are already polymorphic (`eqref`), so `Int`s stored in generic collections are boxed. Monomorphic `Int` locals, parameters, returns, and `contify`-ed loops remain unboxed `i64`.
- **`i31ref` for small `Int`s is an ABI choice:** Adding an `i31ref` fast path for 31-bit `Int`s later is **not** transparent—it affects all five places that inspect boxed `Int`s: (1) unboxing (`br_on_cast i31ref` vs `$QBox_Int`), (2) `quest_val_is`, (3) `quest_identity_hash`, (4) `echo` formatting, and (5) `dynamic.extern`/`intern`. Any change to it bumps `config/abi`.

### 3.3. Strings and Arrays
- **`String`:** `(struct (field $id (mut i32)) (field $len (mut i32)) (field $data (mut (ref $QByteArray))))` where `$QByteArray = (array (mut i8))`. Supports $O(1)$ length, `setChar`/`setSub`, and identity hashing (`$id`).
- **`Array(T)`:** `(struct (field $id (mut i32)) (field $elems (ref $QAnyArray)))` where `$QAnyArray = (array (mut eqref))`.
  - Why uniform `eqref` elements? Quest `Array` is mutable and invariant, and must pass to generic `All(A::TYPE a: Array(A))` without copying (copying breaks aliasing; `array (mut i64)` is not a subtype of `array (mut eqref)`).
  - **Lengths & indices (`Int` -> `i32`):** Quest `Int` is `i64`; Wasm arrays use `i32`. Every index/length checks `n < 0 || n > MAX_I32_ARRAY` (or `idx < 0 || idx >= len`) in `i64` and raises `arrayOp.error` before `i32.wrap_i64`.

### 3.4. Tuples and Proxies
- **Decision (pending Phase 0):** Use the uniform **`$QTupleAny`** representation for all tuples initially: `(sub $QTupleBase (struct (field $id (mut i32)) (field $slots (ref $QAnyArray))))`, with `$QTupleProxy` as a sibling subtype of `$QTupleBase`.
- **Why not typed WasmGC structs for monomorphic tuples?** If a tuple crosses a unit boundary or is passed from a REPL input to a library function, both sides must agree on its layout; moreover, WasmGC limits `sub` depth to **63**, so arity-based prefix subtyping chains would fail for large tuples. Scalar-unboxed tuple structs are only safe as a local optimization for module-private, non-escaping tuples.

### 3.5. Records and Evidence Passing
- **Payload:** `$QRecordPayload = (struct (field $id (mut i32)) (field $layout (ref $QTypeDescriptor)) (field $fields (ref $QAnyArray)))`, fields sorted alphabetically.
- **Evidence Dictionary:** `$QOffsetDict = (struct (field $slots (ref $QInt32Array)) (field $stored (ref null $QDescArray)))`, mapping view field index $i \to$ payload slot index (plus optional `stored_types` for depth subtyping).
- **First-class `QRecordVal`:** Unboxed multi-value `(ref $QRecordPayload, ref $QOffsetDict)` in locals/params/returns; boxed in a 2-field `$QRecordBox` when stored in an `eqref` slot.
- Works across separately compiled REPL modules with **zero** per-record-type Wasm `struct` declarations.

### 3.6. Options and Variants
- **Variants:** Unboxed multi-value `(i32, eqref)` in locals/params/returns; `$QVariantBox = (struct (field $tag i32) (field $payload eqref))` in `eqref` slots. Static `tagmap`s are `$QInt32Array` globals.
- **Options:** `$QOptionBase` with `$QOptionVal = (sub $QOptionBase (struct (field $id (mut i32)) (field $tag i32) (field $fields (ref $QAnyArray))))` and `$QOptionProxy = (sub $QOptionBase (...))`, dispatched via `ref.test $QOptionProxy`.

### 3.7. Closures, Generic Calls, and Adapters
In C, `QInt` and `QVal` share 64-bit GPRs. **In WasmGC, `i64` (`Int`, `Word.T`) and `eqref` do NOT agree.**
- **Uniform Closure Representation:**
  Every closure is a subtype of `$QClosureBase = (sub (struct (field $id (mut i32)) (field $invoke (ref $GenericInvoker))))`, where `$GenericInvoker` has a uniform signature `(param (ref $QClosureBase) (ref $QAnyArray)) (result eqref)`.
  - Typed closures (e.g. `Int -> Int`) add a second field `(field $fn (ref $Fn_i64_to_i64))` plus captured environment fields directly on the closure struct (1 allocation total).
  - **Direct & typed indirect calls** invoke `$fn` via `call_ref $Fn_i64_to_i64` (unboxed `i64`, zero boxing!).
  - **Generic calls (`A -> B`) or calls through `Array(A -> A)` / `var` slots:** invoke `$invoke` via `call_ref $GenericInvoker`! Because **every** closure carries `$invoke`, storing `fun(x: Int): Int` in an `Array(A -> A)` and calling it from generic code works with **zero** `quest_layout_conversion_error` (eliminating a failure case that C rejects in `c-representation.md` §6.4.5!).
- **Tail Calls:**
  - `questlang/ir/contify` already computes tail position (`scan` in `contify.mod.quest`). The WasmGC emitter tracks `in_tail_pos` (false inside `try`) and emits `return_call` / `return_call_ref`.
  - **Calls that stop being tail calls:** Polymorphic calls where the *result* must be unboxed (`eqref -> i64`/`f64`) or adapted by `quest_adapt_fun` after the call returns. (Argument boxing happens *before* the call and preserves tail position.) Monomorphic closure loops stay true tail calls ($O(1)$ stack).

### 3.8. Identity (`is`) and Identity Hashing (`hash.identityHash`)
- **`is` at polymorphic type `A::TYPE` (`quest_val_is(desc, a, b)`):**
  1. Fast path: `if ref.eq(a, b) return true` (works directly because `a, b: eqref`).
  2. Slow path (only when `ref.eq` is false): check `desc` (or `br_on_cast` on `$QBox_Int`, `$QBox_Real`, `$QBox_Word`, `$QOptionBase`, `$QTupleProxy`). Two distinct `$QBox_Int(42)` boxes compare their unboxed `i64` values and return `true`; `$QBox_Real` compares `f64` (`-0.0 == 0.0`); `$QTupleProxy` / `$QOptionProxy` unproxy to `$orig` and `ref.eq` (plus option single-word/empty-case rules).
- **`hash.identityHash(desc, x)`:**
  - Scalars (`$QBox_Int`, `$QBox_Real`, `$QBox_Word`, `i31ref`): unbox and hash the value (`-0.0` normalized to `0.0`).
  - Heap objects (`$QString`, `$QArray`, `$QTupleVal`, `$QRecordPayload`, `$QClosureBase`, `$QExceptionTag`): lazily assign a non-zero `i32` ID into their `$id` field from a global monotonic counter (`next_id += 1`) on first hash, then mix with `quest_hash_mix64`.

### 3.9. `var`, `out`, and `@` Lvalues (Pending Phase 0 Probe)
Because WasmGC has no interior pointers:
- **Option A (`$QRef` capability structs):** `(type $QRef_Int (sub (struct)))`, `(type $QCell_Int (sub final $QRef_Int (struct (field (mut i64)))))` (validates in `wasm-tools`!), plus `(type $QRef_ArrayElem (sub final $QRef_Any (struct (field (ref $QAnyArray)) (field i32))))` and `$QRef_RecordField`.
  - `@x` where `x` is already in `$QCell_T` allocates **0** extra objects.
  - `f(@a[i])` in a loop allocates **1** small 2-field struct per call, preserving exact aliasing (`f(@a[i] @a[i])`).
- **Option B (Unboxed `(target: eqref, slot: i32)` pair):** Pass `var`/`out` as 2 Wasm parameters `(target, slot)` where `target` is `$QCell_T` (with `slot = -1`), `$QAnyArray`, `$QRecordPayload`, or `$QTupleVal`. **0** allocations even for `f(@a[i])` in a loop, and preserves exact aliasing! (Only needs a `$QCell` if a local `var` has `@x` taken.)
- **Option C (Shadow cell copy-in/copy-out):** 0 allocations, *but* breaks aliasing on `f(@a[i] @a[i])`.
- Phase 0 will benchmark Option A vs Option B.

### 3.10. Non-Null Reference Locals & Join Points
Under WasmGC validation, a local of non-null type `(ref $T)` is uninitialized at function entry and is **still considered uninitialized after an `if` even if assigned in both arms**.
- **Join-point parameters** (`ir/nodes.Stmt.sJoin`): compile to Wasm `block (result ...)` stack values (always initialized, zero overhead).
- **Variables assigned in `if` arms or `out` targets:** use **nullable `(ref null $T)`** locals initialized to `ref.null`, with `ref.as_non_null` on read.

---

## 4. Polymorphism & Cross-Module Type Identity

### 4.1. Polymorphism Compilation
- Every quantifier `(A::K)` compiles to `(param $desc_A (ref $QTypeDescriptor))`.
- Unbounded `A::TYPE` uses `eqref`; bounded `A <: Record`/`Variant` uses the bound's representation at the caller's own view.
- `questlang/ir/specialize` clones polymorphic functions at concrete call sites, eliminating `$QBox_Int`/`$QBox_Real` allocations in hot monomorphic code.

### 4.2. Canonical Shared `rec` Group vs. Per-Module Types
To share GC types across the host driver and per-interaction JIT modules:
- **Canonical Shared `rec` Group (first entries of every module's type section):**
  Contains all cross-module ABI types: `$QTypeDescriptor` + its subtypes (`Record`, `Tuple`, `Variant`, `Option`, `Array`, `Fun`, `Opaque`, `Hole`, `Stored`), `$QBox_Int`, `$QBox_Real`, `$QBox_Word`, `$QByteArray`, `$QAnyArray`, `$QInt32Array`, `$QDescArray`, `$QString`, `$QArray`, `$QRecordPayload`, `$QOffsetDict`, `$QRecordBox`, `$QTupleBase`, `$QTupleVal`, `$QTupleProxy`, `$QOptionBase`, `$QOptionVal`, `$QOptionProxy`, `$QVariantBox`, `$QClosureBase`, `$GenericInvoker`, `$QRef_*`, `$QExceptionTag`, `$QExceptionInstance`.
  - Note: Types at distinct indices in the same `rec` group (e.g., `$QBox_Int` vs `$QBox_Word`) are distinct under `ref.test`/`ref.cast`.
  - Any change to this `rec` group increments `config/abi` (and thus unit fingerprints).
- **Stand-alone Per-Module Types (after the `rec` group):**
  Per-function `$FnSig` types and per-closure `$QEnv_<fn>` structs (inheriting from `$QClosureBase`), plus private local types.

### 4.3. Engine Limits Check
- **Subtype depth (spec limit: 63):** Max depth in our hierarchy is **2** (`$QRef` / `$QTupleBase` / `$QClosureBase` / `$QTypeDescriptor`).
- **Monolithic initializer risk:** Emitting all static `QTypeDescriptor`s in one `start` function for an 84K-line compiler could hit V8's per-function size limit (~7.6 MB). **Fix:** Emit closed descriptors as **Wasm `global` constant expressions** (`struct.new` / `array.new_fixed` in global initializers) and split module initialization per Quest unit.

---

## 5. Runtime, Exceptions, `Real`, and Host Boundary

### 5.1. Guarded Operations (Avoiding Wasm Traps)
| Operation | Wasm Trap | Quest Semantics | Required Wasm Guard |
| :--- | :--- | :--- | :--- |
| `i64.div_s` / `rem_s` | `b == 0` or `INT64_MIN / -1` | `int.error` on `0`; wrap on `-1` | Check `b == 0 -> throw int.error`; `b == -1 -> -a` / `0` |
| `i64.div_u` / `rem_u` | `b == 0` | `word.error` on `0` | Check `b == 0 -> throw word.error` |
| `i64.trunc_f64_s` | `NaN`, `+-Inf`, out-of-range | `real.error` | Check finite & in-range -> else `throw real.error` |
| `array.get`/`set`/`new` | OOB or negative/huge `i32` | `arrayOp.error` | Check `i64` bounds `0 <= idx < len` -> else `throw arrayOp.error` |
| `Real` `+ - * /` | (IEEE returns `NaN`) | `real.error` on `NaN` or `0.0` div | Check `b == 0.0` on `/`; check `f64.ne r r` (`isnan`) -> `throw real.error` |

### 5.2. Generative Exceptions (`exnref`)
- Declare **one** Wasm tag: `(tag $quest_exn (param (ref $QExceptionInstance)))`.
- Each `exception E of T end` allocates a fresh `$QExceptionTag(name, desc)`. `try ... when E` catches `$quest_exn` and checks `ref.eq` on `$tag`.
- Full tracebacks are deferred; uncaught exceptions report `Exception: <name>`.

### 5.3. `Real` Math & Formatting
- **Math (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `log`, `pow`, `sinh`, `cosh`, `tanh`):** Import `Math.*` from JS (wrapped to check `isnan` -> `real.error`).
- **Formatting & parsing (`quest_real_format`, `echo`, string -> `Real`):** JS `Number.toFixed`/`toExponential` differs from C `snprintf` on `-0.0`, exponent padding, and ties. To match shared run goldens byte-for-byte, implement C-compatible formatting/parsing in Quest/Wasm (or a small tested formatter).

### 5.4. Host Boundary, Served Files, and Module Packaging
- **Bytes across the JS/WASI boundary:** JS cannot directly index `$QByteArray`. Use a **1-page (64 KB) linear memory bounce buffer** (`memory 1`): JS reads/writes `Uint8Array` in linear memory, and Wasm copies to/from `$QByteArray` in a tight loop (or `array.new_data` for bundled static assets). The same linear memory works for WASI `fd_read`/`fd_write` in `wasmtime`.
- **What the page serves:**
  - *Phase 3 (Interpreter):* Needs `lib/**/*.int.quest` and `lib/**/*.mod.quest` (bundled as static data or fetched by Worker) so the interpreter can run library modules from source.
  - *Phase 4 (JIT):* Needs pre-built `lib/**/*.qi` interface files only; `lib/` implementations are already compiled into the driver.
- **Driver packaging for Phase 4:** Compile the driver as **one WasmGC module** *without* whole-program dead-stripping of `lib/` exports, exporting every `lib/` module's record (`qm_*`), initializer (`qv_*_init`), exported functions (`qv_*`), and interface fingerprint (`qh_*`). Phase 4 JIT phrase modules `qj_<n>` import these from `driverInstance.exports` (and earlier `qj_<k>.exports`) via the JS `importObject`.
- **Target-separated artifacts:** Build outputs go to `build/wasm/` (separate from `build/c/` and `build/arm64/`), and `config/abi` / interface fingerprints distinguish WasmGC from native targets.

---

## 6. Phased Implementation Plan

### Phase 0: Probes & Feasibility Smoke Tests (`wasm-tools`, `wasmtime`, `node`)
- Probe and benchmark:
  1. Unboxed `(target: eqref, slot: i32)` vs `$QRef` struct for `@` lvalues.
  2. Linear-memory bounce buffer throughput for reading `questlang/` sources.
  3. Synchronous `new WebAssembly.Module` + `new WebAssembly.Instance` inside a Node `worker_threads` Worker sharing the canonical `rec` group with a host module.
  4. Note on tooling: `wasmtime` CLI cannot dynamically load guest-generated `.wasm` modules at runtime (and Wasmtime 50's DRC collector does not collect cycles), so `wasmtime` tests **Phases 1–3 (AOT & interpreter)** while **`node` (V8)** tests **all Phases 0–4 including the WasmGC JIT**.

### Phase 1: Wasm Binary Emitter & Minimal AOT `--backend wasm`
- Build `questlang/codegen/wasm/` lowering directly from `ir` (emitting binary `.wasm`, canonical `rec` group, structured control flow, `return_call`/`return_call_ref`, and guarded traps).
- Run `tests/source/language/` subsets on `wasmtime` and `node`.

### Phase 2: Full Quest Semantics in WasmGC
- Implement Evidence Passing (`$QRecordPayload` + `$QOffsetDict`), variants, options, `$QTupleProxy`/`$QOptionProxy`, `$QRef` lvalues, `QTypeDescriptor`s, `Dynamic`/`Auto`, generative exceptions (`$quest_exn`), lazy `$id` identity hashing, and `Real` math/formatting.
- Port `quest_runtime.c` / `quest_serialization.c` logic to Quest.
- Run `tests/source/` on `wasmtime` and `node` (excluding traceback-only goldens).

### Phase 3: Self-Hosted Compiler & Interpreter REPL in Browser
- Compile `questlang/driver/main` (with tree-walking interpreter + bundled `lib/*.int.quest`/`*.mod.quest`) to WasmGC with the event-driven ABI (`repl_init`, `repl_incomplete`, `repl_eval`).
- Test against `tests/repl/` transcripts in `node` and in a Chromium Web Worker UI.

### Phase 4: Per-Interaction WasmGC JIT
- Implement `questlang/jit/wasmSession` emitting `.wasm` bytes per phrase unit `qj_<n>` and calling the Worker's synchronous `host_compile_and_run`.
- Verify `tests/repl/` transcripts under the WasmGC JIT in `node` and Chromium.

---

## 7. Decisions & Provisional Choices

### Owner Decisions (Locked In)
1. **Browser & Engine Target:** Chromium/V8 initially (`WasmGC`, `tail-call`, `exnref`).
2. **Execution Environment:** **Web Worker** with an **event-driven ABI** (`repl_init`, `repl_incomplete`, `repl_eval`); no JSPI needed since `new WebAssembly.Module` is synchronous and uncapped in a Worker.
3. **Lowering Level:** Lower directly from **`ir`** (after `specialize`, `closure`, `represent`, `describe`, `simplify`/`inline`/`contify`), not `ssa`.
4. **Exception Tracebacks:** Deferred; uncaught exceptions report the exception name without frame walking initially.
5. **External `lib/` Primitives:** Stub/virtual `lib/os/` and `lib/io/` initially.
6. **Staged Milestone:** Phase 3 compiles `questlang` with the tree-walking interpreter to WasmGC first, before Phase 4 adds the per-interaction WasmGC JIT.

### Provisional Technical Choices (Pending Phase 0 Probes)
- **`@` Lvalue Encoding:** Unboxed `(target: eqref, slot: i32)` pair vs. `$QRef` capability structs (benchmark allocation/call overhead in Phase 0).
- **Tuple Representation:** Uniform `$QTupleAny` everywhere vs. scalar-unboxed structs for module-private non-escaping tuples.
- **Small `Int` Boxing:** Always `$QBox_Int` vs. `i31ref` for 31-bit `Int`s (ABI decision—must be locked before Phase 2).
- **Host Byte Transfer:** 64 KB linear-memory bounce buffer vs. per-chunk export helpers.
