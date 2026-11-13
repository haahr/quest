# WebAssembly (WasmGC) Backend and In-Browser Self-Hosted REPL Plan (Argon)

## 1. Goals and Overview

The goal is to run a self-hosted Quest compiler and interactive REPL in a web browser, compiling Quest code to **WasmGC** (WebAssembly Garbage Collection) and using an in-browser JIT that compiles each REPL interaction into a small WasmGC module, dynamically instantiates and links it, and executes it against persistent session state.

During development and automated testing on macOS, the toolchain targets:
- **`wasm-tools`** (`/opt/homebrew/bin/wasm-tools` 1.263+): binary validation (`wasm-tools validate --features all`), disassembly (`wasm-tools print`), and binary-from-text assembly (`wasm-tools parse`) for unit tests.
- **`node`** (`/opt/homebrew/bin/node` v26+): V8 WasmGC + Exception Handling + Tail Call execution and browser-like dynamic module loading (`WebAssembly.Module` / `WebAssembly.Instance`) via a small JS host harness.
- **`wasmtime`** (`/opt/homebrew/bin/wasmtime` 50+): standalone CLI execution (`wasmtime run -W gc=y,function-references=y,exceptions=y,tail-call=y -C collector=copying`) for separate-unit testing (`--preload`) and differential testing against the C and arm64 backends.

### High-Level Architecture

```
Quest Source / REPL Phrase
        │
        ▼
Frontend (parse -> expand -> check)
        │
        ▼
Core IR -> simplify -> inline -> contify -> specialize -> closure -> unbox -> represent -> describe (+ thunks)
        │
        ├──────────────────────────────┐
        ▼                              ▼
   questlang/ssa                  questlang/wasm (NEW)
   (byte offsets, ptr tagging,    (typed WasmGC structs/arrays,
    inline bump GC, C ABI)         i31ref hybrid boxes, call_ref, try_table)
        │                              │
        ├──► C backend                 ▼
        └──► arm64 / JIT          .wasm binary emitter (questlang/wasm/encode)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
             CLI / Test Harnesses              Browser Worker
          (node, wasmtime, wasm-tools)     (compiler.wasm + VFS
                                            + dynamic per-phrase qj_<n>.wasm)
```

---

## 2. Answers to Cross-Plan Architectural Questions

### 2.1. Traps: Quest Today vs. WebAssembly Target

WebAssembly instructions can trap on integer division by zero, integer division overflow (`INT64_MIN / -1`), conversion of invalid floating-point numbers to integers, out-of-bounds array or string access, and access through a null reference. In WebAssembly, guest exception handlers cannot catch traps. 

The table below contrasts what Quest defines today with what the WasmGC target emits:

| Operation | Condition | Quest Today (`runtime/quest_runtime.h`, `c-representation.md`) | WebAssembly Behavior | WasmGC Backend Lowering |
| :--- | :--- | :--- | :--- | :--- |
| **Integer division & remainder** (`/`, `%`, `mod` on `Int`) | Divisor is `0` | Raises catchable `int.error` with location `"file:line:col"` (`quest_check_int_div_at`) | `i64.div_s` / `i64.rem_s` trap (`integer divide by zero`) | Emit explicit check: if `b == 0`, call `$quest_raise_int_error_at(site)` (throws `$quest_exception`). |
| **Integer division overflow** (`/`, `%`, `mod` on `Int`) | `int.minInt / ~1` | Wraps to `int.minInt` (remainder `0`) (`quest_int_div_at`, `quest_int_rem_at`) | `i64.div_s` traps (`integer overflow`) | If `b == -1`, evaluate `0 - a` (for `/`) or `0` (for `%`/`mod`); otherwise execute `i64.div_s` / `i64.rem_s`. |
| **Word division & remainder** (`word.div`, `word.mod`) | Divisor is `0` | Raises catchable `word.error` | `i64.div_u` / `i64.rem_u` trap | If `b == 0`, call `$quest_raise_word_error()` (throws `$quest_exception`). |
| **Conversion of `Real` to `Int`** (`real.floor`, `real.ceil`, `real.trunc`, `real.round`) | `NaN`, `±inf`, or $|r| \ge 2^{63}$ | In Quest, `NaN` is never a valid `Real` (`quest_real_result_at` raises catchable `real.error` on any `isnan`). Out of bounds raises catchable `real.error`. | `i64.trunc_f64_s` traps on `NaN`, `±inf`, or $|r| \ge 2^{63}$ | Check `(r != r) || (r < -9223372036854775808.0) || (r >= 9223372036854775808.0)` and call `$quest_raise_real_error()`. Then execute `i64.trunc_sat_f64_s` (saturating truncation never traps). |
| **Array & String indexing** (`a[i]`, `string.getChar`, `string.getSub`) | `i < 0` or `i >= len` | Raises catchable `arrayOp.error` (`quest_check_array_bounds_at`) or `string.error` (`quest_check_string_bounds_at`) with site | `array.get` / `array.set` trap on out-of-bounds | Emit unsigned 64-bit comparison `(i64.ge_u idx (i64.extend_i32_u (array.len a)))`. If true, call `$quest_raise_array_error_at(site)`. |
| **Array allocation size** (`array of(n, init)`) | `n < 0` or `n > 2^31 - 1` | `n < 0` raises catchable `arrayOp.error`. Excessive size calls `quest_oom()` (uncatchable fatal abort). | `array.new` takes `i32` and traps on negative or host allocation limit | Check `n < 0` -> raise `arrayOp.error`. Check `(i64.gt_s n 0x3fffffff)` -> call `$quest_oom()`. |
| **Option computed ordinal** (`option ordinal(n) of T end`) | `n < 0` or `n >= count` | Uncatchable fatal error: prints `"Option ordinal %lld out of bounds..."` to `stderr` and exits status 1 (`quest_check_option_ordinal_at`). | N/A | Check `(i64.ge_u n count)`: on failure call `$quest_option_ordinal_error_at(n, count, site)`, which writes to `stderr` and aborts. |
| **Failed cast** (`ref.cast`) & **Null dereference** | Invariant violation | Statically typed language: dynamic tests (`inspect`, `dynamic.be`) inspect `$TypeDescriptor` first; mismatch raises catchable `dynamic.error`. | Traps | A failed `ref.cast` or null dereference in emitted code is an internal compiler bug, never reachable in valid Quest code. |

---

### 2.2. Tail Calls Through Adapters and Call Chains

Native Quest (`questlang/ssa/tailCalls.mod.quest`) turns calls in tail position into jumps or tail calls, subject to:
1. The call is not inside an active `try` block (which must pop handlers).
2. The caller does not perform post-call conversions on the returned value.

#### Which calls stop being tail calls under WasmGC?
- **Within a function:** Direct and indirect calls in tail position that require no return-value conversions emit `return_call` or `return_call_ref` (using the WebAssembly Tail Call extension).
- **Calls through result-converting adapter thunks:**
  When a closure crosses a subtyping or instantiation boundary where return values must be converted (e.g. boxing an unboxed `i64` into `eqref`, or converting a return view via `planAdapt` in `ir/thunks.mod.quest`), the adapter thunk must wait for the callee to return so it can convert the result:
  ```
  caller --[return_call_ref]--> adapter_thunk --[call_ref]--> callee
                                      │
                                      ▼
                               (convert result)
                                      │
                                      ▼
                                   (return)
  ```
  The call from `adapter_thunk` to `callee` is **not** a tail call because the result must be converted before returning.

#### Why does this not exhaust the browser stack in a closure loop?
1. **Single-frame overhead:** Adapter thunks are created when a closure is *passed* across an adaptation boundary, not on every iteration of a loop.
2. Even if a recursive function `f` is invoked through an adapting wrapper `A`, `A` adds exactly **1 frame** on entry. When `f` calls itself tail-recursively (or mutually tail-calls `g`), `f` and `g` share their signature and dispatch directly via `return_call` or `return_call_ref`. The recursion executes in $O(1)$ stack space regardless of the initial entry wrapper.
3. The only way an unbounded loop could grow frames is if each iteration created a *new* result-converting wrapper around the next step, which Quest's closure conversion and representation passes never do.

---

### 2.3. The Stack: Compiler Recursion and Host Overflow

#### Empirical Measurements on the Self-Hosted Compiler
We measured the stack requirements of the stage 2 Quest compiler (`./quest`, arm64) using `RLIMIT_STACK` binary search on macOS:

1. **Per-unit compilation (`--stop-after ssa`):**
   - `questlang/types/canonical.mod.quest` (2,011 lines): succeeds at **64 KB**.
   - `questlang/types/model.mod.quest` (2,121 lines): succeeds at **64 KB**.
   - `questlang/codegen/c/printer.mod.quest` (3,317 lines, largest unit): fails at 64 KB, succeeds at **80 KB**.
   - `questlang/ir/lower.mod.quest` (2,268 lines): fails at 64 KB, succeeds at **80 KB**.
   - `questlang/values/dynamicjson.mod.quest` (1,801 lines): fails at 80 KB, succeeds at **96 KB**.
2. **Whole-program compilation (`--whole-program questlang/driver/main.quest`):**
   - Compiling all 287 modules (83,818 lines) into 770,504 lines of Described IR: fails at 64 KB, 96 KB, 128 KB; **succeeds at 192 KB**.

#### Comparison with Browser Stack Budgets
- **Chromium Web Worker:** ~512 KB available stack.
- **Main browser page thread:** ~1 MB available stack.
- **Native OS thread:** 8 MB.

At **96 KB** max for any individual module and **192 KB** for a full whole-program compilation, the compiler comfortably fits within a 512 KB Worker thread (< 38% stack utilization).

#### The Interpreter (`--no-jit`)
In `questlang/interpreter/primitives.mod.quest`, `maxCallDepth = 1000` is an internal software limit. However, each interpreted call frame traverses `treewalk.evalExpr` / `evalBlock` / `apply`, consuming ~2 KB of host stack per interpreted frame. In native execution (8 MB stack), 1,000 frames take ~2 MB. In a 512 KB Chromium Worker, a host stack overflow will trigger at ~200–250 nested interpreted calls before `maxCallDepth = 1000` is reached.

#### Host Stack Overflow Handling
In compiled Wasm code, an uncaught stack overflow is a fatal condition (`docs/exceptions.md` §6: *"Compiled code ends. ... A handler cannot catch it"*).
- When the host VM exhausts its stack, V8 throws `RangeError: Maximum call stack size exceeded` (or Wasmtime traps with `call stack exhausted`).
- The host harness (`run-wasm.js` in Node or the Web Worker message dispatcher) catches the `RangeError`, reads the function call names from `err.stack` (mapped via the Wasm `name` section), collapses consecutive recursive repeats (`... <fn> repeated N more times`), and reports:
  ```
  Exception: stack.overflow
    in <fn>...
  ```
- In the browser REPL Worker, the handler resets transient compiler state and the `quest_handlers` chain while keeping previously loaded session modules (`qm_qj_1..n-1`) intact, returning an error to the user prompt rather than terminating the worker.

---

### 2.4. Limits of the Engines and Safe Encodings

We probed engine limits across `wasm-tools validate --features all`, `wasmtime 50+`, and `node v26` (V8):

| Resource | Spec / Verified Limit | `wasm-tools` | `wasmtime` | `node` (V8) | Max in Quest Compiler | Safe Encoding in Plan |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Subtype depth** | **63** (depth 64 rejected) | 63 | 63 | 63 | **3** | Uniform `$Tuple` wrapping `$ValArray` has depth 3 (`$HeapObj :> $TupleLike :> $Tuple :> $Option`). Avoids deep `$tupN <: $tup(N-1)` chains which violate depth 63 on records/tuples with $\ge 62$ fields. |
| **Struct fields** | **10,000** | 10,000 | 10,000 | 10,000 | ~120 (module records) | Fixed struct fields used only for core runtime structs; aggregates use `$ValArray`. |
| **Function params** | **1,000** | 1,000 | 1,000 | 1,000 | ~24 | Arguments and multi-value returns stay well within 1,000. |
| **Function locals** | **50,000** | 50,000 | 50,000 | 50,000 | ~4,200 (in whole-program `main`) | Split large initializers into table-driven loops or chunked `$qm_init_<unit>` functions. |
| **Function body size** | **~7.65 MB** | 7,654,321 B | 7,654,321 B | 7,654,321 B | ~180 KB (`$qm_init`) | Well below limits; large literal data placed in passive data segments. |
| **Types per module** | **1,000,000** | 1,000,000 | 1,000,000 | 1,000,000 | ~800 | Shared `(rec ...)` prelude has 25 types; function signatures are interned. |

---

### 2.5. Type Identity Across Modules

In WebAssembly GC, type equivalence across modules is **isorecursive**:
- The canonical identity of the $i$-th type in a recursion group $G$ is the pair $(G, i)$.
- Two types in the same recursion group at indices $i \ne j$ are **nominally distinct even if their field structures are identical**.
- Standalone types outside a `(rec ...)` group form singleton recursion groups and are canonically equal if and only if their structures are identical.

#### Prelude Partitioning: Fixed `(rec ...)` Group vs. Standalone Types
1. **The Core `(rec ...)` Group (indices 0..24, identical in every emitted module):**
   Contains all 25 runtime aggregate types and the uniform closure signature:
   `0: $BoxI64`, `1: $BoxF64`, `2: $ByteArray`, `3: $Int32Array`, `4: $ValArray`, `5: $StringArray`, `6: $DescArray`, `7: $HeapObj`, `8: $Cell`, `9: $String`, `10: $Array`, `11: $TupleLike`, `12: $Tuple`, `13: $Option`, `14: $Proxy`, `15: $Record`, `16: $RecordBox`, `17: $VariantBox`, `18: $UniformFn`, `19: $Closure`, `20: $Auto`, `21: $Exception`, `22: $ExceptionPacket`, `23: $TypeDescriptor`, `24: $ViewMap`.
2. **Standalone Types (outside the group):**
   Only concrete function types `(type $sig_T (func ...))` and their corresponding closure subtypes:
   ```wat
   (type $Closure_T (sub final $Closure (struct
     (field $hash    (mut i32))
     (field $uniform (ref $UniformFn))
     (field $env     eqref)
     (field $native  (ref $sig_T))
   )))
   ```

#### Distinction and Evolution Guarantees
- Within the canonical group, types are separated by their fixed index. Adding or removing a field on one struct does not collapse it with another struct.
- Across precompiled modules, any change to the core `(rec ...)` group alters its canonical hash. Precompiled `.wasm` units are protected against incompatible prelude mismatches by checking `abi.version` in `questlang/config/abi.mod.quest`.

---

### 2.6. Reference Locals and Non-Null Validation

WebAssembly validation requires that non-defaultable locals of non-null reference type `(ref $T)` be initialized before use. The validator tracks initialization status within enclosing control-flow blocks and resets uninitialized status when leaving branches.

#### Lowering Choices:
1. **Join points (`sJoin` / `sJump`):**
   - *Forward-only joins:* Lowered directly as Wasm multi-value block results:
     ```wat
     (block $join (result (ref $Tuple) i64)
       ...
       (br $join (local.get $t) (local.get $val))
     )
     ```
     This requires zero locals and zero null checks.
   - *Loop join points / back-edges:* Lowered using nullable locals `(local (ref null $T))`. On entry to the join point, the value is promoted to non-null via `(ref.as_non_null (local.get $x))`.
2. **`out` parameters:** Passed as non-null parameter pairs `(param $loc_arr (ref $ValArray)) (param $loc_idx i32)`. At the call site, an uninitialized local `let var x: T` passed via `@x` is backed by a 1-element `$ValArray` allocated with `(array.new_default $ValArray (i32.const 1))` containing `ref.null eq`.
3. **Variables assigned on both arms of an `if`:**
   - Single-value joins use `(if (result (ref $T)) (then ...) (else ...))`, placing the non-null reference directly on the operand stack.
   - Complex mutable variables use `(local (ref null $T))` and read via `(ref.as_non_null (local.get $v))`. In both V8 and Cranelift (Wasmtime), dominating `ref.as_non_null` checks are eliminated, and memory dereferences (`struct.get`) fold the check into a hardware trap.

---

### 2.7. `Int` (`i64`) Where WebAssembly Wants `i32`

Quest's `Int` is a 64-bit signed integer (`i64`), while WebAssembly arrays, strings, and memories use unsigned/signed 32-bit indices (`i32`).

#### Indexing Bounds Checks
Before any `array.get` or `array.set`, Quest emits an unsigned 64-bit bounds check against the 32-bit array length:
```wat
(i64.ge_u (local.get $idx_i64) (i64.extend_i32_u (array.len (local.get $arr))))
```
- If `idx < 0`, bit 63 is set; `i64.ge_u` evaluates to `1` (out of bounds).
- If `idx >= 2^31`, `i64.ge_u` evaluates to `1` because `(i64.extend_i32_u len) < 2^31`.
- Any index outside `[0, len)` raises catchable `arrayOp.error` (or `string.error`) **before `i32.wrap_i64` is executed**. A 64-bit value like $2^{32}$ never wraps to 0.

#### Allocations and Lengths
- **Allocation count `n`:** If `n < 0`, raise catchable `arrayOp.error`. If `n > 0x3fffffff` (or exceeding engine array limits), fail with an uncatchable out-of-memory abort (`quest_oom()`).
- **Lengths (`extent a`, `string.length(s)`):** `(i64.extend_i32_u (array.len a))` always fits losslessly in an `i64` `Int`.

---

### 2.8. Bytes Across the Host Boundary

JavaScript and host runtimes cannot read or write WebAssembly GC structs and arrays directly.

#### Boundary Transfer Mechanism
Every module shares an exported linear memory buffer `(memory (export "memory") 1)`. Two small runtime functions transfer bytes between linear memory and WasmGC `(ref $ByteArray)`:
- `$wasm_mem_to_bytes(ptr: i32, len: i32) -> (ref $ByteArray)`
- `$wasm_bytes_to_mem(arr: (ref $ByteArray), ptr: i32) -> i32`

#### Operation Across Environments:
- **In the Browser / Node:**
  - *Reading files/sources:* JS writes into `new Uint8Array(memory.buffer, ptr, len).set(sourceBytes)` and calls `$wasm_mem_to_bytes`.
  - *Writing files / Loading JIT modules:* Quest calls `$wasm_bytes_to_mem` and invokes host import `os_code_load(name, ptr, len)`. JS reads `new Uint8Array(memory.buffer, ptr, len)` and passes it to `new WebAssembly.Module`.
- **Under WASI (`wasmtime`):**
  WASI calls (`fd_read`, `fd_write`) operate directly on `memory 0` at `ptr`, and the Wasm runtime transfers bytes to/from `$ByteArray` using the same helpers.

#### Measured Cost of Compiler Source Loading
We benchmarked transferring all 287 source files of `questlang/` (4,307,486 bytes = 4.11 MB):
- **Node v26 (V8):** Host $\to$ WasmGC takes **11.28 ms**; WasmGC $\to$ Host takes **10.09 ms**.
- **Wasmtime 50 (`-C collector=copying`):** Full roundtrip takes **15.98 ms** (~8.0 ms each way).
- **Single REPL phrase module `qj_<n>.wasm` (~2–10 KB):** Boundary copy takes **< 0.03 ms**.

---

### 2.9. What the Page Serves

| Execution Mode in Browser | Files Required from `lib/` (62 modules, 237 KB source) | Files Required from `questlang/` (287 modules, 4.11 MB source) | Producer & Target |
| :--- | :--- | :--- | :--- |
| **1. Browser JIT REPL (User Mode)** | Precompiled `lib` `.wasm` units in Worker registry + `lib/**/*.qi` (~120 KB total) in VFS | Precompiled `compiler.wasm` (or unit bundle); `questlang/**/*.qi` (~636 KB) for reflection | Produced at build time by `./quest compile --backend wasm`. `.qi` files are target-independent (ABI v25). |
| **2. Browser Interpreter Mode (`--no-jit`)** | `lib/**/*.int.quest` and `lib/**/*.mod.quest` (62 files, 237.3 KB raw, ~60 KB gzipped) + `lib/**/*.qi` | Compiled `compiler.wasm` (containing tree-walk and IR interpreters) | Source files copied directly from repository into VFS bundle (`vfs-bundle.json`). |
| **3. In-Browser Self-Compilation** | `lib/**/*.qi` + `lib/**/*.{int,mod}.quest` | `questlang/**/*.{int,mod}.quest` (287 files, 4.11 MB raw, ~850 KB gzipped) | Copied from repo into on-demand VFS archive `questlang-src.json`. |

---

### 2.10. The Driver as the Library vs. Whole-Program Optimization

In `questlang/jit/session.mod.quest` lines 105–112:
```quest
"the JIT cannot run from this binary: its own modules' symbols are missing (a whole-program build drops them)"
```
When compiled with `--whole-program`, `questlang/ir/whole.mod.quest` dead-code eliminates unused module members, internalizes functions, and drops per-module records `qm_<mod>`, exports `qv_<mod>_<fn>`, and fingerprint globals `qh_<mod>`. A REPL phrase importing `list.map` from the host compiler binary would fail to link.

#### Resolution:
1. **Per-Unit Archive in Web Worker (`quest-units.bundle`):**
   The browser Worker loads precompiled per-unit `.wasm` modules from an uncompressed archive and instantiates them in topological order into the Worker's `registry`. Every `lib/` and `questlang/` module record and function export is preserved with zero symbol stripping.
2. **Linked Module with Retained Exports:**
   When linking into a single `compiler.wasm`, the bundler retains all exported module records (`qm_<mod>`), functions (`qv_<mod>_*`), and fingerprints (`qh_<mod>`) in the Wasm Export Section rather than dropping them during dead-code elimination.

---

### 2.11. Artifacts, Caches, and Manifest Staleness Per Target

- **`.qi` Interface files and `qh_<mod>` Fingerprints:** Completely **target-independent** (recording ABI version 25, type shapes, values, and pre-lowering inline IR).
- **`.qm` Manifest Bug in `manifest.mod.quest`:**
  In `questlang/modules/manifest.mod.quest` lines 206–224, `isManifestStale` checks ABI version, producer, and file hashes, but **does not verify that `man.backend == currentBackend`**. If a project builds with `--backend arm64` and then `--backend wasm` in the same build directory, `manifest.unitStaleness` treats the arm64 `.qm` as fresh and attempts to pass Mach-O objects to the Wasm pipeline.
- **Fix:**
  1. Update `manifest.isManifestStale` to mark any manifest with `man.backend != currentBackend` as stale.
  2. Use distinct object extensions (`<stem>.wasm` vs `<stem>.o`).
  3. Default Wasm builds to `.build/quest-stages-wasm/`.

---

## 3. Plan-Specific Technical Deep-Dives

### 3.1. Variants, Slot Numbering, and Bounded Quantifiers

In Quest (`docs/c-representation.md` §5.3.2):
- A variant tag is a **dense 0-based integer (`0, 1, ..., n-1`) indexing the cases of the variant's static type in alphabetical order of case names**. (It is NOT an FNV-1a hash.)
- **Width Subtyping (`Variant a: Int, c: Bool end <: Variant a: Int, b: String, c: Bool end`):**
  When the alphabetical case indices of the subtype differ from the supertype, `ir/represent` generates `planVariantTags`. At runtime, the tag is remapped using a static lookup array `tagmap_<Target>_<Source>[src.tag]` (`(array i32)` in WasmGC), yielding `(tagmap[src.tag], src.payload)` with zero heap allocation.
- **In an Aggregate Slot (`$VariantBox`):**
  A variant stored in a slot has its tag in **the slot's static type's numbering**. Any upcast remaps the tag *before* `slot_box` stores it into the slot.
- **Bounded Quantifiers (`All(V <: Variant ... end)`):**
  Generic code holds `v: V` at its **own view** (the actual type argument's case numbering). Inside the generic function, `ir/describe` fetches `view = $quest_view_map(desc_V, desc_Bound)`. Operations `v?tag`, `v!tag`, and `case v` map `v.tag` to the bound's numbering using `(array.get $Int32Array (struct.get $ViewMap $index $view) $v_tag)`.

---

### 3.2. Generative Identity of Exceptions

In Quest (`docs/c-representation.md` §7.1, `Cardelli §4.9`):
- `exception E [: T] end` (`opMakeException`) is **generative**:
  1. Evaluating the same exception declaration twice (e.g. inside a function or loop) produces two distinct `(ref $Exception)` objects. `e1 is e2` evaluates to `0` (`false`).
  2. Two exception declarations with the same name in different modules allocate distinct `(ref $Exception)` heap objects.
  3. Standard exceptions (`int.error`, `real.error`, etc.) are pre-allocated singleton `(ref $Exception)` globals exported by the runtime.
- `$ExceptionPacket` holds `(field $exc (ref $Exception))`. Handler matching (`try ... when E ...`) checks identity via `(ref.eq (struct.get $ExceptionPacket $exc $pkt) (global.get $E))`.

---

### 3.3. Representation Boundaries and Protecting Native Goldens

In the existing compiler:
- `ir/represent` and `ir/slots` do not emit conversions when an `Int` is stored in a tuple or array. `slots.decideSlots` calls `layout.isBoxedInSlots`, which returns `true` only for records and variants (`QRecordVal` and `QVariantVal`).
- For C and arm64, scalar conversion to/from 64-bit slot words occurs in `questlang/ssa/build/values.mod.quest`.
- **WasmGC Pipeline Integration:**
  `ir/represent.mod.quest`, `ir/slots.mod.quest`, and `codegen/layout.mod.quest` remain **completely unchanged** for C and arm64, protecting 100% of existing `tests/golden/` files.
  In `questlang/wasm/build/`, slot operations (`opMakeTuple`, `opTupleField`, `opMakeOption`, `opMakeArray`, `opIndex`, `sStoreComponent`, `sStoreElement`, etc.) call `toEqref` and `fromEqref` directly, handling `i31ref` / `$BoxI64` / `$BoxF64` conversions.

---

### 3.4. Closures and Generic Instantiation (Two-Entry Dispatch)

When a function `fun(x: Int): Int` (Wasm type `(func (param (ref $Closure) i64) (result i64))`) is stored in a tuple or array and passed to generic code expecting `(func (param (ref $Closure) eqref) (result eqref))`, `layout.genericLayoutAgrees` is `true`, so no adapter thunk is generated. Calling it with `(ref.cast (ref $sig_generic))` would trap.

#### Validated Solution: Two-Entry Closures
Every closure provides two entry points:
1. Base `$Closure` in the core prelude:
   ```wat
   (type $UniformFn (func (param (ref $Closure) (ref $DescArray) (ref $ValArray)) (result eqref)))
   (type $Closure (sub $HeapObj (struct
     (field $hash    (mut i32))
     (field $uniform (ref $UniformFn))
     (field $env     eqref)
   )))
   ```
2. For each distinct concrete Wasm signature `$sig_T`, a final subtype:
   ```wat
   (type $Closure_T (sub final $Closure (struct
     (field $hash    (mut i32))
     (field $uniform (ref $UniformFn))
     (field $env     eqref)
     (field $native  (ref $sig_T))
   )))
   ```
3. At an indirect call site expecting signature `$sig_T`:
   - `br_on_cast` checks if the closure is `$Closure_T`.
   - **Fast path (>99.9% of calls):** Dispatches directly to `$native` via `call_ref $sig_T` (or `return_call_ref $sig_T` for tail calls) with unboxed arguments and zero allocation.
   - **Slow path (generic mismatch):** Boxes arguments into `$ValArray`, calls `$uniform`, and unboxes the result. Traps are impossible.

---

### 3.5. `Real` Formatting, Math, and `libm` Parity Under `wasmtime`

#### Capabilities and Divergences:
1. `wasmtime` CLI provides only WASI and `--preload` modules; it cannot import arbitrary host JavaScript functions.
2. JavaScript's `Number.toString()` differs from Quest's `quest_conv_real` / `quest_format_real` (`runtime/quest_runtime.c` lines 773–825):
   - Quest prints `'~'` for negative numbers (`~1.5`, `~inf`), while JS prints `'-'`.
   - Quest outputs `.0` on integral floats (`1.0`, `42.0`), while JS prints `"1"`, `"42"`.
   - Quest switches to scientific notation at $|r| < 10^{-4}$ or $|r| \ge 10^{16}$ with 2-digit exponents (`1e-05`), while JS switches at $10^{-6}$ / $10^{21}$.
3. Evaluating V8 (`node v26`) math functions against macOS `libSystem.B.dylib` (`libm`) revealed 1–2 ULP differences across `sin`, `cos`, `tan`, `atan`, `exp`, `log`, and `pow`.

#### Solution for Complete Differential Parity:
Compile `quest_format_real`, `strtod`, and standard `fdlibm` / `musl` transcendental functions (`sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2`, `exp`, `log`, `pow`, `sinh`, `cosh`, `tanh`) into a pure scalar WebAssembly helper module (`runtime/wasm/libm_fmt.wasm`).
This requires zero host imports, operates solely on `f64`/`i32` and linear scratch memory, and guarantees bit-for-bit identical math and formatting across `wasmtime`, `node`, and all web browsers.

---

### 3.6. Stack Tracebacks and the `name` Section

In Quest (`docs/exceptions.md` §2.1–3.3):
- Stack frames in tracebacks consist of **function names only** (`  in <trace_name>`).
- File, line, and column information is attached **only to the raise site itself** (`"file:line:col"`), emitted as a string literal passed directly to `$quest_raise_at`.
- **Inlining, Contification, and Specialization:**
  - *Inlining:* Inlined frames belong to the caller, while the raise site offset identifies the exact original call location via source maps.
  - *Contification:* Tail-recursive local functions turned into loops are attributed to their enclosing function.
  - *Specialization and Closure Lifting:* Lifted functions preserve their `ir.Function.trace_name` in the Wasm `name` section.
- **Zero Overhead on Caught Exceptions:**
  Quest's `quest_handlers` chain records whether an enclosing handler catches an exception (`CATCH_LISTED` or `CATCH_ALL`). Before capturing a traceback, `$quest_raise_at` inspects the chain: if caught, **no stack trace is captured**, avoiding host overhead.
- For `wasmtime` CLI parity without JS host imports, a 2-instruction shadow call ring (`global $trace_sp` indexing a fixed `Int32Array`) records active function IDs on non-leaf function entry and exit.

---

### 3.7. Flat Structs vs. `$Tuple` Wrapping `$ValArray`

#### Empirical Performance Benchmarks
We benchmarked 20,000,000 allocations (3-tuples) and 200,000,000 field reads in `node v26` and `wasmtime 50` (`-C collector=copying`):

| Operation | `$TupleArr` (`$Tuple` wrapping `$ValArray`, 2 allocs) | Flat `$Tuple3` Struct (1 alloc) | Speedup of Flat Struct |
| :--- | :--- | :--- | :--- |
| **V8 (`node`) Allocation (20M escaping)** | 300.5 ms | 278.3 ms | **1.08x** |
| **Wasmtime Allocation (20M escaping)** | 1,621.2 ms | 963.3 ms | **1.68x** |
| **V8 (`node`) Direct Typed Field Read (200M)** | 201.4 ms | 172.2 ms | **1.17x** |
| **V8 (`node`) Cast Read from `$TupleLike` (200M)** | 399.8 ms (`sub final`, depth 1) | 414.7 ms (`sub`, depth 4) | **0.96x** (flat struct cast is 4% slower) |
| **Wasmtime Direct Typed Field Read (200M)** | 496.5 ms | 269.2 ms | **1.84x** |
| **Wasmtime Cast Read from `$TupleLike` (200M)** | 946.8 ms | 566.0 ms | **1.67x** |

#### Codebase Census of `var` and `out` Parameters
We scanned all parameter lists and call-site arguments across the entire Quest codebase:
- `questlang/` (287 files, 83,818 lines): **0** `var` params, **0** `out` params, **0** `@` arguments.
- `lib/` (62 files, 6,622 lines): **0** `var` params, **0** `out` params, **0** `@` arguments.
- `tests/` (823 files, 34,035 lines): **58** `var` params, **15** `out` params, **58** `@` arguments (only 14 of which are `@r.f` or `@t.i`).

#### Trade-Off Analysis:
While flat structs reduce allocation in microbenchmarks, uniform `$ValArray` backing provides decisive architectural advantages for Quest:
1. Avoids the WasmGC maximum subtype depth of 63 (which flat prefix subtype hierarchies violate on tuples/records with $\ge 62$ fields).
2. `$Option <: $Tuple` enables zero-copy, zero-allocation option case binder sharing (`when tag with c:`).
3. Uniform location pairs `((ref $ValArray), i32)` handle all `:var`/`:out` parameters uniformly.

---

### 3.8. Proof: Every Addressable Location is `($ValArray, i32)`

#### Formal Claim:
In Quest, every addressable mutable location passed to a `:var` or `:out` parameter (`opAddrVar`, `opAddrCell`, `opAddrField`, `opAddrComponent`, `opAddrElement`) is representable as a pair `(slots: (ref $ValArray), index: i32)`.

#### Proof:
1. **`opAddrVar(v)` (`@x` on local `let var x`):** Any local whose address is taken is allocated as a 1-element `$ValArray` at index 0: `(v_slots, 0)`.
2. **`opAddrCell(init)` (`var(e)` temporary cell):** Allocates a 1-element `$ValArray` initialized with `toEqref(init)` at index 0: `(cell_slots, 0)`.
3. **`opAddrField(r, f)` (`@r.f` on record):** Record fields live in `r.val.$slots`. The field index is looked up in `r.dict[f]`, yielding `(r.val.$slots, r.dict[f])`.
4. **`opAddrComponent(t, i)` (`@t.i` on tuple or option case):** Mutable components are invariant (`T == U`). Unproxying `t` via `$quest_unproxy(t)` reaches the backing `$Tuple`, yielding `(backing.$slots, i)`.
5. **`opAddrElement(a, idx)` (`@a[idx]` on array):** After the 64-bit bounds check at the address site, this evaluates to `(a.$elems, i32.wrap_i64 idx)`.
6. **Record/Variant Local Variables:** In `questlang/ir/slots.mod.quest` lines 606–626, `slots.decideSlots` marks any mutable local or `:var`/`:out` parameter of record or variant type with `v.boxed := true`. In aggregate slots, records and variants are stored as single `eqref` pointers to immutable `$RecordBox` or `$VariantBox` objects. Assigning through `:var`/`:out` stores the new box reference into `slots[index]`.

#### Invariant Boundary:
This property holds because aggregate slots uniformly use `$ValArray`. If arrays of `Int` or `Real` were stored unboxed as `(array (mut i64))` or if tuples used heterogeneous flat structs, `:var`/`:out` parameters would require either per-element `$Cell` wrappers or getter/setter closure pairs.

---

### 3.9. `i31ref` Hybrid vs. Always-Boxed Integers

#### Empirical Allocation Profiling
Running `./quest` with `QUEST_GC_CHECK=allocations` revealed that compiling a single module (`questlang/ir/represent.mod.quest`, 1,337 lines) natively performs **57,768,617 allocations (4.15 GB)**.
Because AST spans, token positions, type IDs, hash tables, and vector lengths all store integers into slots, always boxing integers into `$BoxI64` would add **150M–250M additional heap allocations (~2.4–4.0 GB)** per unit compile, and 2–3 billion extra allocations during self-compilation.

#### Benchmark: `i31ref` Hybrid vs. Always-`$BoxI64` (20M slot writes + reads)
- **Node v26 (V8):** `93.9 ms` (always-box) $\to$ **`27.8 ms`** (`i31ref` hybrid) — **3.38x faster**, zero allocations for integers in $[-2^{30}, 2^{30}-1]$.
- **Wasmtime 50 (`-C collector=copying`):** `373.5 ms` (always-box) $\to$ **`67.2 ms`** (`i31ref` hybrid) — **5.56x faster**, zero allocations.

#### Disjoint Representation Invariant:
Small integers in $[-2^{30}, 2^{30}-1]$ are unboxed directly in `i31ref`. Large integers outside this range allocate `$BoxI64`. An integer in $[-2^{30}, 2^{30}-1]$ is never allocated as a `$BoxI64`, ensuring canonical representation.

---

### 3.10. Identity Hashing Design

1. Struct `$HeapObj (sub (struct (field $hash (mut i32))))` is the base type for all heap objects (`$TupleLike`, `$Array`, `$String`, `$Closure`, `$Exception`, `$Cell`). At allocation, `$hash` is initialized to `0`.
2. `$quest_obj_hash(obj: (ref $HeapObj)) -> i64`:
   If `obj.$hash == 0`, increments global atomic counter `(global $next_id_hash (mut i32))` (skipping 0) and stores it in `obj.$hash`. Returns SplitMix64 mixed hash of `obj.$hash`.
3. `$quest_identity_hash(t: (ref $TypeDescriptor), x: eqref) -> i64`:
   - `REAL`: Unboxes `$BoxF64`, normalizes `-0.0` to `0.0`, and mixes bits.
   - `INT`, `WORD`, `BOOL`, `CHAR`, `OK`: Extracts integer from `i31ref` or `$BoxI64` and mixes bits.
   - `OPTION`: Computes hash based on tag and case payload.
   - `TUPLE`, `STRING`, `ARRAY`, `FUN`, `EXCEPTION`: Unproxies to `$HeapObj` and calls `$quest_obj_hash`.

---

### 3.11. Canonical WasmGC Type Prelude

Every emitted module begins with this validated 25-type `(rec ...)` group (verified with `wasm-tools validate --features all`):

```wat
(rec
  ;; 0: Boxed 64-bit integer outside i31 range
  (type $BoxI64 (struct (field $v i64)))
  ;; 1: Boxed 64-bit floating-point real
  (type $BoxF64 (struct (field $v f64)))

  ;; 2..6: Primitive arrays
  (type $ByteArray   (array (mut i8)))
  (type $Int32Array  (array (mut i32)))
  (type $ValArray    (array (mut eqref)))
  (type $StringArray (array (ref $String)))
  (type $DescArray   (array (ref $TypeDescriptor)))

  ;; 7: Base heap object carrying lazy identity hash
  (type $HeapObj (sub (struct (field $hash (mut i32)))))

  ;; 8: Mutable cell
  (type $Cell (sub final $HeapObj (struct (field $hash (mut i32)) (field $v (mut eqref)))))

  ;; 9: Immutable string (UTF-8 bytes)
  (type $String (sub final $HeapObj (struct (field $hash (mut i32)) (field $len i32) (field $bytes (ref $ByteArray)))))

  ;; 10: Quest Array of slots
  (type $Array (sub final $HeapObj (struct (field $hash (mut i32)) (field $elems (ref $ValArray)))))

  ;; 11: Tuple-like common supertype
  (type $TupleLike (sub $HeapObj (struct (field $hash (mut i32)))))

  ;; 12: Concrete Tuple wrapping slot array
  (type $Tuple (sub $TupleLike (struct (field $hash (mut i32)) (field $slots (ref $ValArray)))))

  ;; 13: Concrete Option extending Tuple (tag + payload slots)
  (type $Option (sub final $Tuple (struct (field $hash (mut i32)) (field $slots (ref $ValArray)) (field $tag i32))))

  ;; 14: Proxy view over backing TupleLike
  (type $Proxy (sub final $TupleLike (struct (field $hash (mut i32)) (field $target (ref $TupleLike)) (field $view (ref $ViewMap)))))

  ;; 15: Record value payload
  (type $Record (sub final $HeapObj (struct (field $hash (mut i32)) (field $desc (ref null $TypeDescriptor)) (field $slots (ref $ValArray)))))

  ;; 16: Boxed record for single-slot contexts
  (type $RecordBox (struct (field $val (ref $Record)) (field $dict (ref $Int32Array))))

  ;; 17: Boxed variant for single-slot contexts
  (type $VariantBox (struct (field $tag i32) (field $payload eqref)))

  ;; 18: Uniform closure dispatch signature
  (type $UniformFn (func (param (ref $Closure) (ref $DescArray) (ref $ValArray)) (result eqref)))

  ;; 19: Base closure carrying uniform dispatch entry
  (type $Closure (sub $HeapObj (struct (field $hash (mut i32)) (field $uniform (ref $UniformFn)) (field $env eqref))))

  ;; 20: Auto & Dynamic wrapper
  (type $Auto (sub final $HeapObj (struct (field $hash (mut i32)) (field $val eqref) (field $type (ref $TypeDescriptor)))))

  ;; 21: Generative exception object
  (type $Exception (sub final $HeapObj (struct (field $hash (mut i32)) (field $name (ref $String)))))

  ;; 22: Thrown exception packet
  (type $ExceptionPacket (struct (field $exc (ref $Exception)) (field $payload eqref) (field $site (ref $String)) (field $trace (ref null $Int32Array))))

  ;; 23: Runtime type descriptor
  (type $TypeDescriptor (sub final $HeapObj (struct
    (field $hash      (mut i32))
    (field $kind      i32)
    (field $desc_hash i64)
    (field $flags     i32)
    (field $int_data  (ref $Int32Array))
    (field $names     (ref $StringArray))
    (field $childs    (ref $DescArray))
  )))

  ;; 24: View map for bounded subtyping and proxies
  (type $ViewMap (sub final $HeapObj (struct
    (field $hash   (mut i32))
    (field $index  (ref $Int32Array))
    (field $convs  (ref $DescArray))
    (field $cases  (ref $DescArray))
  )))
)
```

---

### 3.12. Multi-Module Linking

Instead of writing a custom binary `.wasm` linker in Quest (`questlang/wasm/link.mod.quest`), we leverage:
1. **`wasmtime --preload` on CLI:**
   `wasmtime run -W gc=y,function-references=y,exceptions=y,tail-call=y -C collector=copying --preload a=a.wasm b=b.wasm main.wasm` links multi-module programs natively.
2. **`ir/whole.mod.quest` (`--whole-program`):**
   Merges IR graphs before codegen to emit a single `.wasm` binary when standalone execution is required.
3. **In-Browser Worker Registry:**
   Instantiates per-unit modules in topological order and wires exports directly into downstream imports.

---

### 3.13. Virtual File System Seeding

The browser virtual filesystem is pre-seeded with:
1. `lib/**/*.qi` (~120 KB total) for REPL type checking and compilation.
2. `lib/**/*.{int,mod}.quest` (237.3 KB total) to allow interpreter execution (`--no-jit`).
3. Memory mount `/<quest-memory>/` for REPL phrase `.qi` files.

---

### 3.14. Cross-Origin Isolation and Hosting

The browser REPL operates in **event-driven mode** inside a Web Worker:
- The Worker receives phrases via `postMessage`, compiles `qj_<n>.wasm`, instantiates it with `new WebAssembly.Module` and `new WebAssembly.Instance`, executes `qm_init_qj_n`, and streams stdout/stderr back.
- **This requires NO `SharedArrayBuffer`, NO COOP/COEP headers, and runs seamlessly on standard static hosts (e.g. GitHub Pages).**
- When COOP/COEP headers are present, `SharedArrayBuffer` enables an optional non-terminating Ctrl-C interrupt flag.

---

### 3.15. `wasmtime` Collector Configuration

`wasmtime`'s default WasmGC collector (`drc`) does not reclaim cyclical references. Because Quest closures, type graphs, and data structures contain cycles, all `wasmtime` invocations must pass:
```sh
wasmtime run -W gc=y,function-references=y,exceptions=y,tail-call=y -C collector=copying <file>.wasm
```

---

## 4. Design Decisions, Provenance, and Empirical Measurements

| Decision | Provenance | Basis / Empirical Finding |
| :--- | :--- | :--- |
| **Runtime in WasmGC** | Confirmed by project owner | Avoids split-world linear memory issues; enables 100% parity across `node`, `wasmtime`, and browser. |
| **Uniform `$ValArray` for Tuples/Options** | Confirmed by project owner | Avoids engine subtype depth limit of 63; enables zero-copy option case binders (`when tag with c:`); simplifies `:var`/`:out` locations. |
| **Driver as the Library in Browser** | Confirmed by project owner | Retains module exports in Worker registry to support REPL dynamic linkage. |
| **In-Memory VFS Seeded with `lib/`** | Confirmed by project owner | Pre-seeds 120 KB of `.qi` interfaces and 237 KB of stdlib source, supporting both JIT and `--no-jit` interpreter modes. |
| **`i31ref` Hybrid Boxing for `Int`/`Word`** | Empirically revised in Argon review | Avoids 150M–250M `$BoxI64` allocations per unit compile; measured 3.4x (V8) and 5.6x (Wasmtime) speedups. |
| **Two-Entry Closures (`$Closure` + `$Closure_<sig>`)** | Empirically revised in Argon review | Prevents illegal cast traps when generic code invokes monomorphic closures in tuples/arrays. |
| **Pure-Wasm Float/Math Module (`libm_fmt.wasm`)** | Empirically revised in Argon review | Replaces host math imports, eliminating 1–2 ULP variations and formatting differences for bit-identical results. |
| **`wasmtime --preload` and IR whole-program linking** | Empirically revised in Argon review | Eliminates ~2,000 lines of complex binary Wasm linker code in Quest. |
| **Event-Driven Worker REPL** | Empirically revised in Argon review | Runs without requiring `SharedArrayBuffer` or cross-origin isolation headers on static web hosts. |
| **`wasmtime -C collector=copying`** | Empirically revised in Argon review | Required to reclaim cyclic references in closures and compiler data structures. |

---

## 5. Staged Implementation Plan with Testable Exit Conditions

### Phase 1: Wasm Binary/WAT Emitter & Minimal Runtime Core
- Implement `questlang/wasm/types.mod.quest` (canonical prelude) and `encode.mod.quest` (LEB128, binary sections, instructions).
- Implement `runtime/wasm/` core and `scripts/run-wasm.js` test runner.
- **Done when:** A hand-written WAT test and an emitted minimal `.wasm` binary validate with `wasm-tools validate --features all` and execute under `node` and `wasmtime -C collector=copying`.

### Phase 2: Scalars, Control Flow, and Closures
- Lower scalars (`Int`, `Real`, `Bool`, `Char`, `Word.T`, `Ok`), arithmetic, comparisons, `if`/`loop`/`block`, direct calls, and closures (`$Closure`, `$Closure_<sig>`, `br_on_cast`, `call_ref`, `return_call_ref`).
- Implement `i31ref` hybrid boxing (`$box_int`, `$unbox_int`).
- **Done when:** `tests/source/language/arithmetic.quest`, `recursion.quest`, and `closures.quest` pass under both `node` and `wasmtime`.

### Phase 3: Aggregates (`Tuple`, `Option`, `Record`, `Variant`, `Array`, `String`) and `:var` / `:out`
- Lower `$Tuple` and `$Option` backed by `$ValArray`.
- Lower `$Record` + `$Int32Array` multi-value pairs and `$Variant` multi-value pairs.
- Lower `:var` and `:out` parameters as `((ref $ValArray), i32)` location pairs.
- Implement `$quest_val_is` and `$quest_identity_hash`.
- **Done when:** All aggregate and reference parameter tests in `tests/source/language/` pass identically to C and arm64 backends.

### Phase 4: Polymorphism, Subtyping, Proxies, and Type Descriptors
- Lower static and template `$TypeDescriptor` structs and interning tables.
- Implement `$quest_is_subtype`, `$quest_view_map`, `$quest_convert`, and `$Proxy` access.
- Lower `auto`, `inspect`, and `Dynamic`.
- **Done when:** All polymorphic, bounded quantification, and dynamic type tests pass under `node` and `wasmtime`.

### Phase 5a: Exceptions (`try_table` / `throw`), Handler Pre-Checks, and Tracebacks
- Lower `try` / `raise` to Wasm `$quest_exception` and `try_table`.
- Implement `quest_handlers` pre-check avoiding trace capture on caught exceptions.
- Implement trace formatting via the Wasm `name` section.
- **Done when:** All tests in `tests/source/language/exceptions.quest` and `tests/errors/run/` match their goldens under `node` and `wasmtime`.

### Phase 5b: Separate Compilation, Manifest Backend Tagging, and Multi-Module Linking
- Fix `manifest.isManifestStale` to enforce `man.backend == currentBackend`.
- Emit module records `qm_<mod>`, exports `qv_<mod>_*`, and fingerprints `qh_<mod>`.
- Support multi-module loading via `wasmtime --preload` and the Node registry.
- **Done when:** Multi-module programs compile separately to `.wasm` files and link cleanly under `wasmtime --preload` and `node`.

### Phase 5c: Standard Library (`lib/`) Bring-Up and Full Test Suite
- Compile all 62 modules of `lib/` in dependency order.
- Integrate `runtime/wasm/libm_fmt.wasm` for formatting and math.
- **Done when:** The complete language and standard library test suite passes with zero failures under both `node` and `wasmtime -C collector=copying`.

### Phase 6: Self-Hosting Compiler on WasmGC & CLI REPL JIT
- Compile `questlang/` to `compiler.wasm`.
- Verify bootstrap fixed-point: `compiler.wasm` compiles `questlang/` to byte-identical output.
- Wire `questlang/jit/session` to `--backend wasm`, compiling REPL phrases to `qj_<n>.wasm` and instantiating them dynamically in Node.
- **Done when:** REPL test suite (`tests/repl/`) passes against the Wasm JIT in Node.

### Phase 7: Web Worker Host & Browser REPL UI
- Build browser runner in `web/` with Web Worker host, in-memory VFS, module registry, and interactive REPL UI.
- Verify multiline evaluation, output streaming, and error reporting.
- **Done when:** A user can open `web/index.html` in Chrome, Firefox, or Safari and interact with the self-hosted Quest REPL.
