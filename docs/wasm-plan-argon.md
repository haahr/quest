# WebAssembly (WasmGC) Backend and In-Browser Self-Hosted REPL Plan

## 1. Goals and Overview

The goal is to run a self-hosted Quest compiler and interactive REPL in a web browser, compiling Quest code to **WasmGC** (WebAssembly Garbage Collection) and using an in-browser JIT that compiles each REPL interaction into a small WasmGC module, dynamically instantiates and links it, and executes it against persistent session state.

During development and automated testing on macOS, the toolchain will target:
- **`wasm-tools`** (`/opt/homebrew/bin/wasm-tools` 1.263+): binary validation (`wasm-tools validate --features all`), disassembly (`wasm-tools print`), and binary-from-text assembly (`wasm-tools parse`) for unit tests.
- **`node`** (`/opt/homebrew/bin/node` v26+): V8 WasmGC + Exception Handling + Tail Call execution and browser-like dynamic module loading (`WebAssembly.Module` / `WebAssembly.Instance`) via a small JS host harness.
- **`wasmtime`** (`/opt/homebrew/bin/wasmtime` 50+): standalone CLI execution (`wasmtime run -W gc=y,function-references=y,exceptions=y,tail-call=y`) for single-module binaries and differential testing against the C and arm64 backends.

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
    inline bump GC, C ABI)         i31ref/boxes, call_ref, try_table)
        │                              │
        ├──► C backend                 ▼
        └──► arm64 / JIT          .wasm binary emitter
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
             CLI / Test Harnesses              Browser Worker
          (node, wasmtime, wasm-tools)     (Self-hosted compiler.wasm
                                            + dynamic per-phrase qj_<n>.wasm)
```

---

## 2. Evaluation of Design Assumptions & Problematic Areas

Before detailing the design, several assumptions and architectural tensions around WasmGC and Quest's existing compiler pipeline need to be called out explicitly.

### 2.1. Problem 1: WasmGC Cannot Lower From `questlang/ssa`

In the existing compiler (`docs/ssa.md`, `docs/arm64.md`), the C and arm64 backends share `questlang/ssa` and `questlang/codegen/layout`. It is tempting to treat Wasm as another target below `ssa`, but **WasmGC fundamentally conflicts with `ssa`'s invariants**:

1. **No pointer arithmetic or byte-offset loads/stores:** `ssa` lowers tuple, record, option, and array accesses into `ptrAdd` + raw byte offsets (`load8`, `store8`). WasmGC `struct` and `array` references are completely opaque; fields can only be accessed by static field index (`struct.get`, `struct.set`) or element index (`array.get`, `array.set`).
2. **No low-bit pointer tagging (`QUEST_PROXY_TAG = 1`):** `ssa` uses `ptrToInt` / `intToPtr` to set and test bit 0 of tuple/option pointers for `QProxy`. WasmGC references cannot be converted to integers or bit-tagged.
3. **No interior pointers (`(char *)opt + 8`, `@r.f`, `@t.0`, `@a[i]`):**
   - In C/arm64, an option's payload starts at byte offset 8 and a case binder (`when tag with c:`) takes an interior pointer `(char *)opt + 8` as a tuple pointer so mutable (`var`) components are shared (`docs/c-representation.md` §5.3).
   - `:var` and `:out` arguments (`@x`, `@r.f`, `@t.0`, `@a[i]`) pass raw interior pointers `T *` into stack frames, heap structs, or arrays (`docs/c-representation.md` §13).
   - WasmGC **forbids interior pointers** into struct fields or array elements.
4. **No inline bump-pointer allocation or shadow stack:** `ssa` lowers `new` to inline `quest_gc_cursor` bump allocation and `quest_barrier` write barriers. On WasmGC, the host VM owns the heap and write barriers via `struct.new` and `array.new`.

**Recommendation:** The WasmGC backend must branch after **Described IR (`ir_described` + `ir/thunks`)**, not `ssa`. At the Described IR level, `tupleGet`, `recordGet`, `optionMatch`, `arrayGet`, `closureCall`, `convert`, and `:var`/`:out` modes are still explicit and structural. (Note: `ir/represent` and `ir/describe` are already almost completely target-independent—they operate on abstract slot indices and `QVal` boxing boundaries rather than byte offsets.)

---

### 2.2. Problem 2: WasmGC Has No Unboxed 64-Bit Universal Slot (`QVal`)

Quest's C/arm64 runtime relies heavily on `QVal` being an 8-byte untyped union (`int64_t i`, `double r`, `void *p`, `uint64_t u`) and on two properties that follow from it (`docs/c-representation.md` §2):
- **Uniform 1-word slots:** Every scalar (`Int`, `Real`, `Bool`, `Char`, `Word.T`, `Ok`) and every single-pointer aggregate fits in an 8-byte `QVal` without heap allocation.
- **Concrete-vs-generic layout equivalence (`generic_layout_agrees`):** A concrete `Tuple Int Real end` (`{ int64_t _0; double _1; }`) has the *exact same memory layout* as a generic `Tuple A B end` (`{ QVal _0; QVal _1; }`), so passing a concrete tuple or `Array(Int)` to a polymorphic function `fun(t: Tuple A B end)` is a zero-copy pointer cast that preserves `is` identity and `var` mutation sharing.

**Why this breaks in WasmGC:**
- WasmGC's universal reference hierarchy (`anyref` -> `eqref` -> `{i31ref, structref, arrayref}`) **cannot hold unboxed `i64` or `f64`**. Only 31-bit integers (`i31ref`) fit unboxed inside `eqref`.
- Because Quest `Int` and `Word.T` are 64-bit (`i64`) and `Real` is 64-bit IEEE-754 (`f64`), placing an `Int`, `Word.T`, or `Real` into an `eqref` slot requires a **heap-allocated immutable box struct** (`$BoxI64 = (struct (field i64))`, `$BoxF64 = (struct (field f64))`), whereas `Bool`, `Char`, and `Ok` fit unboxed in `i31ref`.
- Even more critically: in WasmGC, a struct with native scalar fields `(struct (field (mut i64)) (field (mut f64)))` is **disjoint from** `(struct (field (mut eqref)) (field (mut eqref)))`. They cannot be cast to one another!
- If concrete aggregates used unboxed `i64`/`f64` fields while polymorphic code expected `eqref` fields, crossing a polymorphic boundary would require either:
  1. Copying the aggregate (which **violates Quest semantics** for `is` pointer identity and `var` mutation aliasing—the exact bug documented as `generic_layout_copies_mutable_data` in `docs/c-representation.md` §2.4), or
  2. Wrapping every concrete tuple/array in a proxy or virtual accessor table on every field read/write.

**Recommendation (Uniform `eqref` Slots in Heap Aggregates, Unboxed Scalars in Locals/Signatures):**
- **Locals, expression temporaries, and monomorphic function parameters/returns** use unboxed Wasm scalars: `i64` (`Int`, `Word.T`), `f64` (`Real`), `i32` (`Bool`, `Char`, `Ok`). Because Quest already runs call-site specialization (`ir/specialize`) and tuple return unboxing (`ir/unbox`), hot monomorphic loops and local functions operate entirely on unboxed Wasm `i64` and `f64` locals.
- **Aggregate slots (`Tuple`, `Record`, `Option`, `Array`, closure environments) and unspecialized type-variable values (`QVal`)** uniformly use `eqref` (`slot_representation`). Storing an `Int`/`Word.T` into an aggregate slot allocates a `$BoxI64` (`struct.new $BoxI64`); storing a `Real` allocates a `$BoxF64` (`struct.new $BoxF64`); storing `Bool`/`Char`/`Ok` uses `ref.i31` (zero allocation).
- **Consequences and fixes:**
  1. Concrete and generic aggregates have the **exact same WasmGC representation**, so passing `Tuple Int Real end` or `Array(Int)` to `All(A::TYPE) ...` requires **zero copying and zero proxies**, preserving `var` sharing and `is` identity on aggregates.
  2. **`is` and `hash.identityHash` on boxed scalars:** In WasmGC, `ref.eq` on two separately boxed `$BoxI64(42)` structs evaluates to `0` (`false`). Therefore, generic `QVal` equality (`quest_val_is`) and `hash.identityHash` must treat `$BoxI64` and `$BoxF64` by value (matching C/arm64, where `a.u == b.u` compares the 64-bit payload of `QVal`), while using `ref.eq` (after proxy unwrapping) for all heap aggregate references.

---

### 2.3. Problem 3: Compiling the Existing C Runtime (`runtime/*.c`) to Linear Memory

Quest's current runtime (`runtime/quest_runtime.c`, `quest_gc.c`, `quest_serialization.c`, `quest_code.c`, `quest_readline.c`—~420 KB of C) manipulates `QVal`s, `QTypeDescriptor`s, `QRecordVal`s, and `QProxy`s as raw C pointers in flat memory.

**Why compiling `runtime/*.c` with Clang to Wasm linear memory is problematic for a WasmGC target:**
- Clang's `wasm32`/`wasm64` C target places C structs in **linear memory** (`memory 0`), not in the **WasmGC managed heap**. C code cannot dereference a WasmGC `(ref struct)` or `eqref`, and WasmGC structs cannot be cast to linear-memory `void *` pointers.
- Trying to store `QTypeDescriptor`s or strings in linear memory while keeping tuples/records/closures in WasmGC creates a split-world problem: strings and descriptors couldn't be stored in `eqref` slots without wrapper structs, and garbage-collecting linear-memory objects referenced from WasmGC objects would require finalizers.

**Recommendation:**
1. **Delete the GC (~134 KB):** `quest_gc.c` is completely unneeded on WasmGC; the browser/Wasmtime/V8 collector manages all allocations.
2. **Put all Quest values and descriptors in the WasmGC heap:** Strings, Arrays, Tuples, Options, Records, `OffsetDict`s, Closures, Proxies, and `QTypeDescriptor`s should all be native WasmGC structs/arrays.
3. **Implement the WasmGC runtime in two clean layers:**
   - **Wasm-side runtime (written in WAT/Wasm or low-level Quest):** Descriptor equality/subtyping (`quest_is_subtype`), `QViewMap` construction (`quest_view_map`), `quest_convert`, record dictionary lookup (`quest_record_dict`), value equality (`quest_val_is`), identity hashing, string operations, and `.qi` serialization/deserialization. Because this code runs as WasmGC functions, it inspects `$TypeDescriptor`, `$Proxy`, `$Record`, and `$String` structs directly via `struct.get`/`ref.test`.
   - **Host imports (`env` / `wasi` in JS or Wasmtime):** Thin host bindings for I/O (`os/io`, `io/readline`), virtual/real filesystem access (`os/fs`), clocks/timers (`os/time`), transcendental math / `Real` formatting (`Real.toString`, `Real.fromString`, `sin`, `cos`, `atan2`, `pow`, etc.), and dynamic Wasm module instantiation (`os/code` for the JIT).

---

### 2.4. Problem 4: WasmGC Isorecursive Type Equivalence Across Separate Modules and JIT Phrases

A subtle trap in the WasmGC specification is how types are matched across module boundaries (`import` / `export` and indirect calls):
- WasmGC types are **isorecursive**: two types in different Wasm modules are considered identical by the validator/linker **if and only if** they have the exact same structural definition *and* belong to structurally identical recursive type groups `(rec (type ...) ...)`.
- If each Quest compilation unit emitted ad-hoc WasmGC struct types for the specific tuples/options/functions it happened to use in a single `(rec ...)` block, a module `B.wasm` importing a function from `A.wasm` (or a REPL phrase `qj_2.wasm` importing from `qj_1.wasm`) would **fail Wasm link-time validation** with a type mismatch!

**Recommendation (Canonical WasmGC Type Prelude):**
- Every emitted `.wasm` module begins its Type Section with the **exact same fixed `(rec ...)` group of core runtime WasmGC types** (around 20 types: `$BoxI64`, `$BoxF64`, `$Cell`, `$ByteArray`, `$ValArray`, `$Int32Array`, `$String`, `$Array`, `$TupleOrProxy`, `$Tuple`, `$Proxy`, `$Option`, `$Record`, `$RecordBox`, `$VariantBox`, `$Closure`, `$Auto`, `$TypeDescriptor`, `$ViewMap`, `$Exception`).
- Any arity-specialized or signature-specific types (such as Wasm `(func ...)` signatures) are emitted outside the core `(rec ...)` group as standalone `(type (func ...))` entries that reference only Wasm scalar types (`i32`, `i64`, `f64`) and the fixed core WasmGC types.
- Because standalone non-recursive `(type (func ...))` definitions in WasmGC are structural over the core `(rec ...)` group, **every separately compiled module and every dynamically generated JIT phrase module (`qj_<n>.wasm`) will agree on WasmGC types automatically without global whole-program type coordination.**

---

### 2.5. Problem 5: Browser Main-Thread Limits and Synchronous REPL / Compiler I/O

In a browser:
1. Calling `new WebAssembly.Module(bytes)` synchronously on the main UI thread is disallowed by Chrome/V8 for modules larger than 4 KB (the self-hosted compiler `quest.wasm` will be several megabytes).
2. A synchronous REPL loop (`readline.readLine`) or long compilation on the main UI thread freezes the browser tab.

**Recommendation:**
- Run the self-hosted Quest compiler and REPL session inside a **Web Worker** (using `Cross-Origin-Opener-Policy: same-origin` and `Cross-Origin-Embedder-Policy: require-corp` so `SharedArrayBuffer` is available, with an async message-driven fallback when running per-phrase interactions if `SharedArrayBuffer` is unavailable).
- Inside a Web Worker, `new WebAssembly.Module(bytes)` and `new WebAssembly.Instance(mod, imports)` are **allowed synchronously for modules of any size**, so the JIT's `os/code` interface (`load` -> `lookup` -> call) remains completely synchronous and identical between Node, Wasmtime, and the browser!
- Moreover, `Atomics.wait` on a `SharedArrayBuffer` allows synchronous `readline.readLine` and a shared interrupt flag (`quest_interrupt_flag` for Ctrl-C in the browser) without rewriting the compiler or user programs into continuation-passing style or using Asyncify.

---

## 3. Value Representation on WasmGC

This section defines the concrete WasmGC representation corresponding to `docs/c-representation.md`.

### 3.1. Canonical Core WasmGC Type Prelude

Every emitted `.wasm` module starts with this shared `(rec ...)` type group so all modules share identical type identities:

```wat
(rec
  ;; Boxed 64-bit scalars for uniform eqref slots
  (type $BoxI64 (struct (field $v i64)))
  (type $BoxF64 (struct (field $v f64)))

  ;; Mutable 1-slot cell (used for :var/:out and captured mutable variables)
  (type $Cell   (struct (field $v (mut eqref))))

  ;; Primitive arrays
  (type $ByteArray  (array (mut i8)))
  (type $Int32Array (array (mut i32)))
  (type $ValArray   (array (mut eqref)))

  ;; Strings & Quest Arrays
  ;; $String: immutable length + UTF-8/byte array
  (type $String (struct (field $len i32) (field $bytes (ref $ByteArray))))
  ;; $Array: fixed-length mutable array of slots (wrapping $ValArray, or directly $ValArray)
  (type $Array  (struct (field $elems (ref $ValArray))))

  ;; Tuples, Options, and Proxies
  ;; Common supertype for Tuple, Option, and Proxy so proxy checks are a single br_on_cast!
  (type $TupleLike (sub (struct)))

  ;; Concrete Tuple: N slots stored in $ValArray (or fixed-arity subtypes $Tuple1..$Tuple8)
  (type $Tuple  (sub $TupleLike (struct
    (field $slots (ref $ValArray))
  )))

  ;; Concrete Option: 1-based tag + payload slots
  ;; Wait: if $Option extends $Tuple (inheriting $slots (ref $ValArray) + $tag i32),
  ;; then an Option IS a $Tuple with zero allocation for `when tag with c:`!
  (type $Option (sub $Tuple (struct
    (field $slots (ref $ValArray))
    (field $tag   i32)
  )))

  ;; Proxy view over a backing Tuple/Option/Proxy
  (type $Proxy  (sub $TupleLike (struct
    (field $target (ref $TupleLike))
    (field $view   (ref $ViewMap))
  )))

  ;; Records (evidence-passing payload + boxed form for 1-slot contexts)
  (type $Record (struct
    (field $desc  (ref null $TypeDescriptor))
    (field $slots (ref $ValArray))
  ))
  (type $RecordBox (struct
    (field $val  (ref $Record))
    (field $dict (ref $Int32Array))
  ))

  ;; Variants (boxed form for 1-slot contexts; unboxed is (i32, eqref))
  (type $VariantBox (struct
    (field $tag     i32)
    (field $payload eqref)
  ))

  ;; Closures
  (type $Closure (struct
    (field $fn  (ref func))
    (field $env eqref)
  ))

  ;; Auto & Dynamic (identical 2-field layout: value slot + runtime type descriptor)
  (type $Auto (struct
    (field $val  eqref)
    (field $type (ref $TypeDescriptor))
  ))

  ;; Runtime Type Descriptors & View Maps (details in Section 4)
  (type $TypeDescriptor (struct ...))
  (type $ViewMap        (struct ...))
)
```

*(Optimization note on `$Tuple` fields: Section 3.3 discusses fixed-arity struct subtypes `$Tuple0..$Tuple8` vs. `$ValArray`.)*

### 3.2. Concrete vs. Slot Representations (`ir/represent`)

Just as in C/arm64 (`docs/c-representation.md` §2.2), every Quest type has two representations:
1. **Concrete representation:** used for local variables, expression results, and known monomorphic function parameters/returns.
2. **Slot representation (`eqref`):** used whenever a value is stored in a tuple component, record field, option payload, array element, closure environment, or passed as an unspecialized type parameter (`QVal`).

| Quest Type | Concrete Wasm Type | Slot Wasm Type (`eqref`) | `slot_box` (Concrete -> Slot) | `slot_unbox` (Slot -> Concrete) |
| :--- | :--- | :--- | :--- | :--- |
| `Int`, `Word.T` | `i64` | `(ref $BoxI64)` as `eqref` | `(struct.new $BoxI64 x)` | `(struct.get $BoxI64 $v (ref.cast (ref $BoxI64) s))` |
| `Real` | `f64` | `(ref $BoxF64)` as `eqref` | `(struct.new $BoxF64 x)` | `(struct.get $BoxF64 $v (ref.cast (ref $BoxF64) s))` |
| `Bool`, `Char`, `Ok` | `i32` | `i31ref` as `eqref` | `(ref.i31 x)` | `(i31.get_u (ref.cast i31ref s))` |
| `String` | `(ref $String)` | `eqref` | upcast (nop) | `(ref.cast (ref $String) s)` |
| `Array(T)` | `(ref $Array)` | `eqref` | upcast (nop) | `(ref.cast (ref $Array) s)` |
| `Tuple ... end` | `(ref $TupleLike)` | `eqref` | upcast (nop) | `(ref.cast (ref $TupleLike) s)` |
| `Option ... end` | `(ref $TupleLike)` | `eqref` | upcast (nop) | `(ref.cast (ref $TupleLike) s)` |
| `Record ... end` | **Multi-value:** `(ref $Record), (ref $Int32Array)` | `(ref $RecordBox)` as `eqref` | `(struct.new $RecordBox v d)` | `struct.get $val`, `struct.get $dict` |
| `Variant ... end` | **Multi-value:** `i32, eqref` | `(ref $VariantBox)` as `eqref` | `(struct.new $VariantBox t p)` | `struct.get $tag`, `struct.get $payload` |
| `Fun(...) : ...` | `(ref $Closure)` | `eqref` | upcast (nop) | `(ref.cast (ref $Closure) s)` |
| `Auto`, `Dynamic.T` | `(ref $Auto)` | `eqref` | upcast (nop) | `(ref.cast (ref $Auto) s)` |
| Type param `A` | `eqref` | `eqref` | nop | nop |

Notice how cleanly Wasm's native **multi-value** support handles 2-word types (`Record` and `Variant`):
- In local variables, a `Record` is a pair of Wasm locals `(local $r_val (ref null $Record)) (local $r_dict (ref null $Int32Array))`.
- In function parameters and return values, a `Record` expands to two Wasm parameters or a two-value result `(result (ref $Record) (ref $Int32Array))`—the exact equivalent of arm64 passing/returning `QRecordVal` in `(x0, x1)`!
- And because `ir/represent` already inserts explicit `slot_box` and `slot_unbox` operations at every aggregate slot and type-variable boundary, the Wasm backend does not need to invent new boxing placement logic: `ir/represent` already marks every boundary.

### 3.3. Tuples, Options, and Proxies

#### Prefix Subtyping and Option Case Binders (`when tag with c:`)
Look closely at the subtyping hierarchy in the prelude above:
```
           $TupleLike
           /        \
       $Tuple      $Proxy
         |
      $Option (inherits $slots from $Tuple, adds $tag: i32)
```
This solves **both** the Option case-binder problem and the Proxy representation problem without interior pointers or bit-tagging:
1. **Option payload sharing (`case opt when tag with c:`):**
   - Because `$Option` is a WasmGC subtype of `$Tuple` (sharing the `$slots` field at field index 0), when an option case binds `with c:`, the binder `c` is **simply the `$Option` reference itself** upcast to `(ref $TupleLike)`!
   - If the option was actually a `$Proxy` wrapping an `$Option`, `c` is a `$Proxy` whose `$view` is the case's sub-view from `view.cases[tag - 1]`.
   - Zero interior pointers, zero payload copying, and `var` components inside the option case are shared identically to C/arm64!
2. **Proxies without low-bit tagging (`QUEST_PROXY_TAG`):**
   - In C/arm64, every tuple/option read tests `if ((uintptr_t)p & 1)` to check if `p` is a `QProxy`.
   - In WasmGC, `p` has static type `(ref $TupleLike)`. Checking whether `p` is a direct `$Tuple` (or `$Option`) versus a `$Proxy` is a single WasmGC instruction:
     ```wat
     ;; Fast path: direct $Tuple (also matches $Option since $Option <: $Tuple!)
     (block $is_proxy (result (ref $TupleLike))
       (br_on_cast_fail $is_proxy (ref $TupleLike) (ref $Tuple) (local.get $p))
       ;; Now on stack: (ref $Tuple). Read slot i directly!
       ...
     )
     ;; Slow path: $p is a $Proxy; call $quest_tuple_get_proxy($p, i)
     ```
   - When the compiler statically knows `p` was just constructed locally (`tupleNew` / `optionNew`), its static type is `(ref $Tuple)` or `(ref $Option)` and no `br_on_cast_fail` is emitted at all.

#### Mutable (`var`) vs. Immutable Tuple/Record Slots and `:var` / `:out` Parameters
Because WasmGC forbids interior pointers (`@t.0`, `@r.f`, `@x`, `@a[i]`), how should `:var` and `:out` reference parameters work?

There are two clean designs:
- **Design A (First-class Location Ref `(ref $Loc)` for `:var` / `:out` parameters):**
  - Keep tuple/record/array slots as direct `(mut eqref)` elements in `$ValArray` (so normal reads/writes are direct 1-instruction `array.get` / `array.set` with no extra `$Cell` indirection!).
  - Represent a `:var` or `:out` parameter as a small location value. In fact, what can a `:var` or `:out` argument be in Quest (`docs/c-representation.md` §13)?
    1. A local `let var x` whose address is taken (`@x`): allocate `x` in a 1-element `$ValArray` (index `0`).
    2. A mutable tuple component (`@t.i`) or option case component (`@c.i`): after resolving any `$Proxy` once at the call site (`quest_tuple_slot_loc(t, i)`), it is an element `(slots: (ref $ValArray), index: i32)`!
    3. A mutable record field (`@r.f`): it is an element `(slots: r.val.$slots, index: r.dict[f_idx])`—also `(slots: (ref $ValArray), index: i32)`!
    4. An array element (`@a[i]`): after bounds check at the call site, it is `(slots: a.$elems, index: i)`—**also `(slots: (ref $ValArray), index: i32)`**!
    5. A proxy's coerced immutable slot (rare: passing a narrower-typed slot by `:var` isn't allowed for immutable slots because Quest's type checker requires `var` invariance for mutable slots!).Wait—what if a `$Proxy` adapts a `var` component whose type `T` required a proxy/thunk conversion? In Quest (`docs/c-representation.md` §6.1), `var` fields and components are **invariant** (`T <: U` requires `T == U` for `var` fields), except for record width subtyping where the field type itself is identical! Wait—even if a `var` component has a subtype coercion or if all `var` slots live in `$ValArray`, **every single addressable mutable location in Quest (`@x`, `@t.i`, `@r.f`, `@a[i]`) is literally a pair `((ref $ValArray), i32)`!**
  - Let's verify that!
    - Local `var x` (when `@x` is taken): stored in a 1-element `$ValArray` at index `0`.
    - Tuple/Option `var` component `@t.i`: resolved through any proxy chain (following `view->indices` to the backing `$Tuple.$slots` and backing index `idx`), yielding `(backing.$slots, idx)`.
    - Record `var` field `@r.f`: `(r.val.$slots, r.dict[f])`.
    - Array element `@a[i]`: bounds-checked at `@a[i]` evaluation time, yielding `(a.$elems, i)`.
  - Therefore, **every `:var` and `:out` parameter in Quest is simply a multi-value pair `(param $loc_arr (ref $ValArray)) (param $loc_idx i32)`** (or a 2-field struct `$Loc` if stored in a closure)!
  - Reading a `:var` parameter inside the callee is just `(array.get $ValArray (local.get $loc_arr) (local.get $loc_idx))` + `slot_unbox`.
  - Writing a `:var` or `:out` parameter inside the callee is just `slot_box` + `(array.set $ValArray (local.get $loc_arr) (local.get $loc_idx) ...)`.
  - **No `$Cell` wrapper allocation on every `var` field of every tuple/record/array, and 100% faithful aliasing semantics for `@x`, `@t.i`, `@r.f`, and `@a[i]`!**

### 3.4. Records and Evidence Passing (`QRecordVal`)

Records in Quest use evidence passing (`docs/c-representation.md` §4):
- **Concrete representation:** two values:
  1. `val: (ref $Record)` containing `(field $desc (ref null $TypeDescriptor))` and `(field $slots (ref $ValArray))`.
  2. `dict: (ref $Int32Array)` mapping each visible field (in canonical alphabetical order) to its **0-based slot index** in `val.$slots` (in C/arm64 this stores byte offsets `8, 16, ...`; in WasmGC it stores 0-based `i32` slot indices `0, 1, ...`).
- **Field read (`r.f` where `f` is index `k` in static type):**
  ```wat
  (array.get $ValArray
    (struct.get $Record $slots (local.get $r_val))
    (array.get $Int32Array (local.get $r_dict) (i32.const k)))
  ```
  Followed by `slot_unbox` to the concrete field type.
- **Width subtyping (`Record a: Int, b: String end <: Record a: Int end`):**
  Constructs a new `$Int32Array` of length 1 containing `[ old_dict[0] ]` paired with the **same** `(ref $Record)`. Zero copying of record slots; `var` fields remain shared and `is` identity (`ref.eq` on `$Record`) is preserved.
- **Depth subtyping (`Record a: Sub end <: Record a: Super end`):**
  Handled by `quest_convert` / `ir/thunks` exactly as in C/arm64 (wrapping the adapted field in a proxy/thunk if representation changes).

### 3.5. Variants (`QVariantVal`)

- **Concrete representation:** two values `(tag: i32, payload: eqref)`.
  - `tag` is the 32-bit FNV-1a hash of the label name (`quest_label_tag`), identical to C/arm64.
  - `payload` is the `slot_box`ed `eqref` of the payload (`ref.null eq` if there is no payload).
- **Variant width subtyping:** identity operation (`tag` and `payload` are unchanged).
- **Slot representation:** `$VariantBox = (struct (field $tag i32) (field $payload eqref))`.

### 3.6. Closures and Typed Indirect Calls (`call_ref`)

In C/arm64, `QClosure` is `{ void *fn; void *env; }`.
In WasmGC:
- A closure value is `(ref $Closure)` where:
  ```wat
  (type $Closure (struct
    (field $fn  (ref func))
    (field $env eqref)
  ))
  ```
- Every closure implementation function takes `(param $env eqref)` as its first parameter, followed by any type-descriptor parameters `(param $td_A (ref $TypeDescriptor))`, followed by value parameters in their concrete Wasm types (`i64`, `f64`, `i32`, `eqref`, multi-value pairs for `Record`/`Variant`/`:var`/`:out`).
- At a call site `f(args...)` where the static signature has Wasm function type `$sig_T`:
  ```wat
  ;; Push env, descriptors, and arguments, then:
  (ref.cast (ref $sig_T) (struct.get $Closure $fn (local.get $f)))
  (call_ref $sig_T)
  ```
- **Why `(field $fn (ref func))` + `ref.cast (ref $sig_T)` + `call_ref` is ideal:**
  1. `$Closure` is a single uniform struct type across all function signatures, so storing closures in aggregates, passing them to polymorphic code, or putting them in `Auto` requires no signature-specific wrapper structs.
  2. `call_ref` dispatches directly to the function reference without needing a global `funcref` table or managing table slot indices across dynamically loaded JIT modules!
  3. Wasm's `return_call` and `return_call_ref` (Tail Call proposal, supported in Wasmtime, Node, and all major browsers) can also be used for tail calls if desired.

---

## 4. Polymorphism, Subtyping, and Intensional Type Analysis

Quest supports full $F_{<:}^\omega$ with structural subtyping (tuple prefix, record width/depth, option/variant width/depth, contravariant/covariant functions, bounded quantification) plus runtime type inspection (`inspect`, `Auto`, `Dynamic`).

BecauseQuest's middle-end passes (`ir/specialize`, `ir/closure`, `ir/unbox`, `ir/represent`, `ir/describe`, `ir/thunks`) are already cleanly separated from `ssa`, **almost the entire polymorphism architecture carries over directly to WasmGC**, with targeted adaptations for WasmGC types.

### 4.1. Unbounded Universal Polymorphism (`All(A::TYPE)`)

1. **Monomorphic Call-Site Specialization (`ir/specialize`):**
   - Just like C/arm64, when a polymorphic function is called with known concrete types, `ir/specialize` clones and specializes it (`docs/c-representation.md` §10.4.2).
   - On WasmGC, this is **even more valuable** than on C/arm64: a specialized function `id__Int(x: i64): i64` keeps `Int` and `Real` parameters/locals completely unboxed (`i64`/`f64`), avoiding `$BoxI64`/`$BoxF64` allocations entirely!
2. **Erased Generic Fallback (`ir/represent` + `ir/describe`):**
   - For unspecialized or higher-rank polymorphic calls, each `TYPE`-kinded parameter `A` lowers to:
     - Value parameters/returns of type `A` -> `eqref` (`QVal`).
     - A hidden runtime descriptor parameter `(param $desc_A (ref $TypeDescriptor))` injected by `ir/describe`.
   - At the call site, `ir/represent` inserts `slot_box` on concrete arguments (e.g. `i64` -> `$BoxI64`, `QRecordVal` -> `$RecordBox`) and `slot_unbox` on generic return values.

### 4.2. Structural Subtyping and Coercions (`convert` / `ir/thunks`)

When `T <: U`, how does a value of type `T` become a value of type `U` on WasmGC?

| Subtyping Form | WasmGC Mechanism | Cost |
| :--- | :--- | :--- |
| **Tuple prefix** (`Tuple A B end <: Tuple A end`) where shared slots have identical representation | Identity! Both are `(ref $TupleLike)` and `$ValArray` has slots `0..1`, of which the supertype reads slot `0`. | **Zero** (nop) |
| **Option width** (`Option a; b end <: Option a; b; c end`) where case payloads match | Identity! Both are `(ref $TupleLike)` (`$Option`) with the same 1-based `$tag`. | **Zero** (nop) |
| **Variant width** (`Variant a; b end <: Variant a; b; c end`) where payloads match | Identity! Both are `(i32, eqref)` with the same FNV-1a label hash. | **Zero** (nop) |
| **Record width** (`Record a: Int, b: Int end <: Record a: Int end`) | New `$Int32Array` `dict` mapping visible fields to existing indices in `$Record.$slots`. | Small `$Int32Array` alloc; zero slot copy |
| **Tuple / Option depth** (where a component requires conversion, e.g. `Record` width inside a Tuple, or function variance) | Allocate a `$Proxy` wrapping the target `$TupleLike` and a `$ViewMap` computed by `quest_view_map(src_desc, dst_desc)`. | 1 `$Proxy` alloc (`$ViewMap` cached) |
| **Function subtyping** (`(Super -> Sub) <: (Sub -> Super)`) | `ir/thunks` generates a typed wrapper closure that adapts parameters (`Sub -> Super`), calls the inner closure, and adapts the result (`Sub -> Super`). | 1 `$Closure` alloc |
| **Bounded type variable** (`A <: B` where `v: A` is coerced to `B`) | Calls `$quest_convert(val, desc_A, desc_B)` at runtime using the descriptors passed by `ir/describe`. | Dynamic descriptor check |

### 4.3. Bounded Quantification (`All(A <: B)`)

Quest uses **own-view representation** (`docs/c-representation.md` §10.4.3):
- Inside `fun(type A <: B, x: A)`, `x` has `A`'s own representation (as `eqref`), **not** `B`'s representation.
- When `x` is used at type `A` (e.g., returned as `A`, stored in an `A` slot, or compared with `is`), no conversion happens.
- Only when `x` is used at its bound `B` (e.g., reading a field declared on `B` or passing `x` to a function expecting `B`) does `ir/describe` emit `convert(x, desc_A, desc_B)`.
- If `B` is a Tuple or Option type and `x` is accessed in a loop, `quest_view_map(desc_A, desc_B)` memoizes the `$ViewMap` and wraps `x` in a `$Proxy` so subsequent component reads don't re-run descriptor traversal.

### 4.4. Runtime Type Descriptors (`$TypeDescriptor`) and `inspect` / `Auto` / `Dynamic`

In C/arm64, static `QTypeDescriptor`s are emitted as C static structs (`qd_...`), and dynamic instantiations fill `QHoleDescriptor` templates via `quest_instantiate_descriptor`.

In WasmGC:
- `$TypeDescriptor` is a WasmGC struct in the core `(rec ...)` prelude:
  ```wat
  (type $TypeDescriptor (struct
    (field $kind    i32)                  ;; QTypeKind enum (INT, REAL, TUPLE, RECORD, ...)
    (field $hash    i64)                  ;; 64-bit structural fingerprint (for O(1) equality)
    (field $flags   i32)                  ;; bit 0: has_holes, bit 1: is_mutable, etc.
    (field $int_data (ref $Int32Array))   ;; tags, mutability flags, hole indices, arities
    (field $names   (ref $StringArray))   ;; field names, option/variant labels, brand/opaque names
    (field $childs  (ref $DescArray))     ;; child descriptors (fields, params, results, template args)
  ))
  ```
- **Static descriptors (`qd_<id>`):** Initialized once in the module's start/init function (`$qm_init_<mod>`) and stored in module-level `(global $qd_<id> (mut (ref null $TypeDescriptor)))` globals (interned by structural `$hash` in a global descriptor table so `ref.eq` works for fast-path descriptor equality!).
- **Descriptor templates (`HOLE`, `STORED`, `APP`, `LAM`):** Evaluated by `$quest_instantiate_descriptor` in WasmGC, producing an interned `(ref $TypeDescriptor)`.
- **`Auto` and `Dynamic.T`:** Both are represented by `(ref $Auto)` (`{ $val: eqref, $type: (ref $TypeDescriptor) }`).
  - `auto(v: T)` boxes `v` via `slot_box` and pairs it with `desc_T`.
  - `inspect a when x: P: ...` calls `$quest_is_subtype(a.$type, desc_P)`; on match, it converts `a.$val` via `$quest_convert(a.$val, a.$type, desc_P)` and unboxes via `slot_unbox`.

---

## 5. Exceptions, Stack Traces, and Interrupts

### 5.1. Native Wasm Exception Handling (`try_table` / `throw`)

Instead of `_setjmp` / `_longjmp` (used in C/arm64, which requires demoting SSA locals modified inside `try` blocks to stack slots so registers aren't clobbered by `longjmp`), Wasm has native structured **Exception Handling**:
- All modules share a single imported/exported exception tag:
  ```wat
  (tag $quest_exception (param (ref $ExceptionPacket)))
  ```
  where `$ExceptionPacket` holds:
  - `$tag: i32` (FNV-1a hash of the exception's variant tag)
  - `$payload: eqref` (boxed exception payload)
  - `$Location` (`file: (ref $String)`, `line: i32`, `col: i32`)
  - `$trace: (ref $TraceArray)` (captured stack frames)
- **`raise e`:** Constructs `$ExceptionPacket` and executes `(throw $quest_exception)`.
- **`try ... handle ... always ... end`:** Lowers to Wasm's `block` + `try_table (catch $quest_exception $catch_label)`.
  - If an `always` (finally) block is present, the catch handler runs the `always` block before either matching the exception tag or rethrowing `(throw $quest_exception)`.
  - **Big win over C/arm64:** Wasm locals are preserved across `try_table` catches by the Wasm VM, so no `try`-local stack demotion pass is needed!

### 5.2. Zero-Overhead Stack Tracebacks

Quest's exception design (`docs/exceptions.md`) requires tracebacks with zero overhead on non-raising calls. On arm64, `quest_raise` walks `x29` frame pointers and looks up PCs in `qr_funcs`. Wasm deliberately hides physical stack pointers from guest code.

How to get accurate Quest stack traces on WasmGC with zero normal-call overhead:
1. **Emit the standard Wasm Custom `name` Section** in every `.wasm` binary (mapping each Wasm function index to its human-readable Quest name and source location, e.g., `foo (src/bar.quest:12)`).
2. When `raise` is executed, call a lightweight host import `$host_capture_stack()` (in JS/Node, `new Error().stack` or `WebAssembly.Exception` stack; in Wasmtime, host backtrace capture).
3. Both V8 (Node/Chrome/Firefox/Safari) and Wasmtime parse the Wasm `name` section automatically and include the function names in the captured stack frames, which are filtered (`qm_init_*` / `qj_*` boundaries) and formatted to match Quest's exact traceback format!

---

## 6. Separate Compilation, Linking, and the In-Browser JIT

### 6.1. Direct Binary `.wasm` Emission (`questlang/wasm`)

Following the philosophy of the native arm64 backend (`docs/arm64.md`), the self-hosted compiler should emit **binary `.wasm` directly** in Quest (`questlang/wasm/encode.mod.quest`), alongside a readable `.wat` pretty-printer (`questlang/wasm/wat.mod.quest`) for debugging and `--dump-wasm` inspection.
- The `.wasm` binary format is much simpler than Mach-O + arm64 instruction encoding: LEB128 integers, length-prefixed sections (Type, Import, Function, Global, Export, Element, Code, Data, Custom `name`), and stack-machine opcodes.
- During development, `wasm-tools validate --features all` and `wasm-tools print` provide immediate byte-level verification of every emitted `.wasm` module.

### 6.2. Separate Compilation vs. Whole-Program Bundling

We should support two linking modes from the same per-module `.wasm` emitter:

1. **Multi-Module Dynamic Linking (Used by the REPL JIT and Node/Browser Dev Runner):**
   - Each Quest module (`lib/int`, `lib/list`, ..., or REPL phrase `qj_<n>`) compiles to its own standalone `.wasm` module.
   - Cross-module references:
     - Module `M` exports its initialized module record as `(export "qm_<mangled>" (global $qm_<mangled>))` and its direct functions as `(export "qf_<mangled>_<fn>" (func ...))`.
     - Downstream modules import `(import "quest" "qm_<mangled>" (global (ref null $RecordBox)))` (or direct functions) from the host's module registry.
   - When the host instantiates module `M`, it passes the already-instantiated exports of `M`'s dependencies in the `imports` object and calls `M`'s `$qm_init_<mangled>()` function.

2. **Single-Module Linked Binary (Used for `wasmtime` CLI and shipping `compiler.wasm`):**
   - A lightweight Wasm linker in `questlang/wasm/link.mod.quest` merges the per-module functions, globals, and init calls of the dependency graph into a single self-contained `.wasm` binary with a `_start` export.
   - This allows running any compiled Quest program (and the self-hosted compiler itself!) directly with a single command:
     ```sh
     wasmtime run -W gc=y,function-references=y,exceptions=y,tail-call=y out.wasm
     ```

### 6.3. In-Browser Self-Hosted REPL and Per-Phrase JIT

The existing arm64 JIT (`docs/jit.md`, `questlang/jit/session.mod.quest`) was already architected around **phrase units (`nodes.Phrase`)**:
- Each REPL input is parsed into a `Phrase` and compiled through the standard module pipeline as synthetic module `qj_<n>`.
- Top-level `let` / `let var` / `fun` bindings live in `qj_<n>`'s module record (`qm_qj_<n>`), with mutable/redefinable bindings stored in 1-element boxes so closures from earlier phrases see updated definitions (`docs/jit.md` §3.3).
- Type definitions are fingerprinted (`qh_<name>`) and written to an in-memory `.qi` interface file under `/<quest-memory>/qj_<n>.qi` via `common/memoryFiles` (`docs/jit.md` §3.2).

**How this maps to the Browser WasmGC JIT:**

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Browser Tab                                                             │
│                                                                         │
│  ┌──────────────────────┐    postMessage /     ┌─────────────────────┐  │
│  │ Main UI Thread       │ ◄──────────────────► │ Web Worker          │  │
│  │ - Code editor / REPL │   SharedArrayBuffer  │ - compiler.wasm     │  │
│  │ - Output / trace UI  │                      │ - VFS (/lib, /mem)  │  │
│  │ - Interrupt button   │                      │ - Module Registry   │  │
│  └──────────────────────┘                      │ - qj_1.wasm, ...    │  │
│                                                └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

For each REPL interaction `n`:
1. The user enters a phrase in the browser UI; the Worker receives the line.
2. `compiler.wasm` (the self-hosted Quest compiler running on WasmGC inside the Worker) parses, type-checks (reading `/<quest-memory>/qj_<1..n-1>.qi` from `common/memoryFiles`), lowers to Described IR, and emits `qj_<n>.wasm` (~1–10 KB of Wasm bytes in memory).
3. `compiler.wasm` calls the host import `os_code_load("qj_<n>", wasm_bytes)`:
   - The Worker's JS host runs:
     ```js
     const mod = new WebAssembly.Module(wasmBytes);
     const instance = new WebAssembly.Instance(mod, sharedImports);
     registry.registerExports(instance.exports);
     instance.exports.qm_init_qj_n();
     ```
   - Because `sharedImports` contains the `WebAssembly.Global` exports (`qm_lib_*`, `qm_qj_1` .. `qm_qj_{n-1}`), the shared `$quest_exception` `WebAssembly.Tag`, and the runtime table/helpers, `qj_<n>.wasm` links in sub-millisecond time!
4. `compiler.wasm` formats and prints the resulting bindings/values using the runtime value printer and returns the output to the UI.

---

## 7. Staged Implementation & Testing Plan

All development and verification will use the Homebrew-installed tools (`wasm-tools`, `node`, `wasmtime`):

### Phase 1: Wasm Binary/WAT Emitter & Minimal Runtime Core
- Create `questlang/wasm/` with:
  - `types.int.quest` / `types.mod.quest`: Canonical WasmGC type prelude (`(rec ...)`), function signature interning.
  - `encode.int.quest` / `encode.mod.quest`: Binary `.wasm` encoder (sections, LEB128, WasmGC instructions, `name` custom section).
  - `wat.int.quest` / `wat.mod.quest`: Text `.wat` emitter for readable IR/codegen tests.
- Create the WasmGC runtime module (`runtime/wasm/`) + thin Node/Wasmtime host runner (`scripts/run-wasm.js` and `wasmtime` CLI wrapper).
- **Verification:** Every emitted `.wasm` file is validated with `wasm-tools validate --features all` and disassembled with `wasm-tools print`.

### Phase 2: Scalars, Control Flow, Functions, and Closures
- Lower Described IR scalars (`Int`, `Real`, `Bool`, `Char`, `Word.T`, `Ok`), arithmetic/bitwise/comparison primitives, `if`/`loop`/`block`, direct calls, and closures (`$Closure`, `call_ref`) to WasmGC.
- Implement `slot_box` / `slot_unbox` (`$BoxI64`, `$BoxF64`, `i31ref`).
- **Verification:** Run scalar, recursion, and closure golden tests under both `node` and `wasmtime`.

### Phase 3: Aggregates (`Tuple`, `Option`, `Record`, `Variant`, `Array`, `String`) and `:var` / `:out`
- Lower `$Tuple`, `$Option` (as subtype of `$Tuple` for case-binder sharing), `$Record` + `$Int32Array` multi-value evidence passing, `$Variant` multi-value `(i32, eqref)`, `$Array`, and `$String`.
- Lower `:var` and `:out` parameters as `((ref $ValArray), i32)` location pairs.
- Implement `$quest_val_is` and `$quest_identity_hash` (handling `$BoxI64`/`$BoxF64` by value and heap refs by `ref.eq` after proxy unwrapping).
- **Verification:** Differential test suite against C/arm64 on tuple, option, record, variant, array, string, and `:var`/`:out` test cases.

### Phase 4: Polymorphism, Proxies, Type Descriptors, and `Auto` / `Dynamic`
- Lower static and template `$TypeDescriptor`s (`HOLE`, `STORED`, `APP`, `LAM`) and intern them by structural hash.
- Implement `$quest_is_subtype`, `$quest_view_map`, `$quest_convert`, and `$Proxy` slot access (`br_on_cast_fail` fast path + proxy slow path).
- Lower `auto`, `inspect`, and `Dynamic` (`extern`/`intern`).
- **Verification:** Run all polymorphism, bounded quantification, subtyping, `auto`/`inspect`, and `dynamic` tests under `node` and `wasmtime`.

### Phase 5: Exceptions (`try_table` / `throw`) and Separate Compilation
- Lower `try` / `raise` to Wasm `$quest_exception` tag and `try_table`.
- Implement stack trace formatting via the Wasm `name` section.
- Implement multi-module linking (host import/export registry for Node/Browser) and single-module static linking (for `wasmtime`).
- Compile all of `lib/` (`int`, `real`, `string`, `list`, `table`, `set`, `sort`, `format`, `dynamic`, etc.) to WasmGC and pass the full language and library test suites.

### Phase 6: Self-Hosting the Compiler on WasmGC & CLI REPL JIT
- Compile `questlang/` itself to `compiler.wasm`.
- Verify bootstrap fixed-point: `compiler.wasm` running under `node` / `wasmtime` compiles hello-world, `lib/`, and `questlang/` to byte-identical `.wasm` outputs.
- Wire `questlang/jit/session` to the Wasm backend (`--backend wasm` in the JIT), compiling each REPL phrase to `qj_<n>.wasm` and instantiating it dynamically in Node via `WebAssembly.Instance`.
- Run the existing REPL golden test suite (`tests/repl/`) against the Wasm JIT in Node.

### Phase 7: Browser Host, Web Worker, and Interactive REPL UI
- Build the browser host (`web/`):
  - Web Worker hosting `compiler.wasm`, in-memory VFS (pre-populated with `lib/*.qi` and `/<quest-memory>`), and the dynamic `WebAssembly.Instance` module registry.
  - Browser UI with interactive prompt, multiline phrase detection, stdout/stderr streaming, formatted values/tracebacks, and interrupt button.
- Verify end-to-end in headless Chrome / Node and interactive browser sessions.

---

## 8. Resolved Design Decisions

1. **Runtime Implementation Language (WasmGC + Minimal Host Surface):**
   - Runtime operations that inspect WasmGC heap objects (`$quest_is_subtype`, `$quest_view_map`, `$quest_convert`, `$quest_record_dict`, value equality/hashing, and `.qi` serialization) will be implemented as WasmGC code (in WAT and/or low-level Quest modules) with a small host import surface (~20 functions for I/O, math/float formatting, time, and dynamic module loading). This keeps standalone `wasmtime` execution and `node`/browser execution at full parity.

2. **Tuple and Option Slot Representation (Uniform `$ValArray` First):**
   - `$Tuple` and `$Option` will start with the uniform `(ref $ValArray)` slot backing (`$Option <: $Tuple <: $TupleLike`, with `$Proxy <: $TupleLike`). This gives uniform arbitrary-arity tuples, zero-copy option case-binder sharing (`when tag with c:`), and uniform `:var`/`:out` location pairs (`((ref $ValArray), i32)`). Fixed-arity struct specializations (`$Tuple1..$Tuple8`) can be evaluated later as a targeted optimization once the system is end-to-end functional.

3. **"The Driver Is the Library" in the Browser:**
   - Just as on native arm64 (`docs/jit.md` §2.5), the browser REPL can expose both `lib/` and the already-loaded `questlang/` compiler modules ("the driver is the library") by seeding their `.qi` interfaces into the in-memory VFS and registering their module exports in the Worker's module registry.

4. **Browser Virtual File System:**
   - An in-memory virtual filesystem (seeded with `lib/*.qi` and `/<quest-memory>` for REPL phrase interfaces) is sufficient for the initial browser REPL implementation.
