# Plan: A Self-Hosted REPL in the Browser, on WebAssembly GC

The goal: Quest's own REPL, the self-hosted driver, running in a browser page. The driver is compiled to WebAssembly by
a new backend, `wasm`, that targets the GC proposal (WASM-GC: typed structs, arrays, `i31ref`, and the engine's
collector) rather than a linear memory. At first the browser REPL interprets its inputs, as `--no-jit` does; later a
JIT compiles each input to a WebAssembly module of its own, which the page instantiates and links against the modules
already loaded, as the arm64 JIT ([jit.md](jit.md)) does with machine code.

The backend is written in Quest, in `questlang/`; the bootstrap does not get it ([testing.md](testing.md) §2.8).

**Status: proposed** (2026-11-12). Nothing is built. This document identifies the decisions to be made and the hard
parts, with a recommendation for each decision. Decision 1 is decided (2026-11-12); the others await the owner. Section 2 says where I think the suggested direction
is a problem. Section 3 records what I checked on this machine. Sections 5 and 6, representation and polymorphism, are
the core. Section 12 has the questions for the owner.

---

## 1. Decisions

Each is a recommendation, with the alternative and what it costs. Decisions 1–6 shape everything after them.
Decisions that depend on how engines behave are probed in step 1 (§11) before any code relies on them.

1. **Three stages, each one usable on its own.** *Decided 2026-11-12: the interpreting browser REPL (B) comes before
   the JIT (C).* (A) Programs compiled ahead of time to WASM-GC and run under
   wasmtime and node. (B) The self-hosted driver compiled by (A) and run in a page, *interpreting* its inputs: the
   browser REPL. (C) The JIT: each input compiled in the page to a module, instantiated by the page and linked to the
   driver's modules. (B) gives a browser REPL with no in-browser code generation at all. (C) is mostly the work of the
   arm64 JIT redone over wasm modules, and needs (A)'s backend to run inside the page.
2. **WASM-GC, as suggested.** The engine's collector, precise roots for free (a linear-memory collector cannot see
   wasm locals and needs a shadow stack), small modules, objects that JavaScript can hold. The price (§2.3) is a
   second runtime ABI and a runtime that cannot be the C one.
3. **The backend starts from the described IR, not from the SSA** (§4). The IR's control flow is structured (`if`,
   `switch`, `loop`, `try`, join points), which maps directly onto wasm's `block`, `loop`, `br_table`, and
   `try_table`. The SSA addresses memory by byte offsets and has lost structure, so it would need a stackifier. The
   wasm backend gets its own represent and describe decisions, through a target parameter to `codegen/layout`.
4. **One uniform value word: `eqref`** (§5.1, §6.4). Inside a function, values of known type are native (`i64` for
   `Int`, `f64` for `Real`, `i32` for `Bool` and `Char`, typed references for aggregates). In aggregate slots and as
   values of type parameters, every value is an `eqref`. `Bool`, `Char`, `Ok`, and small `Int`s are `i31ref`s; other
   `Int`s, `Real`s, and `Word`s are boxed in immutable structs. This keeps the C design's central property, that a
   native aggregate and a generic aggregate are laid out alike (§6.1), but boxing becomes real work where in C it was a
   reinterpretation.
5. **Closures with two entries** (§5.9): a uniform entry (all `eqref`) and a native one. Calling either way always
   works, so a closure's layout never depends on whether native or generic code made it. This removes the class of
   conversions that C must adapt or reject because a closure's C signature changes (c-representation.md §6.4.5).
6. **One wasm module per unit, linked by imports** (§8), for programs and the JIT alike. Types are canonicalized
   across modules by structure, so every module declares the same small, fixed set of wasm types (§5.16) and they
   agree.
7. **The runtime written in Quest** over a few dozen wasm intrinsics (§7), with a small host interface (bytes in and
   out, files, time, exit), implemented once over WASI for wasmtime and once in JavaScript for node and the browser.
8. **Test engines: wasmtime and node, both from step 1,** and the browser by hand at each stage's end (§2.1). wasmtime
   always runs with `-C collector=copying` (§3).
9. **The browser REPL runs in a Web Worker** and exports an "evaluate this input" entry, rather than running a
   blocking read loop (§9).
10. **The backend writes the binary format directly**, with a WAT printer beside it for goldens and debugging, as the
    arm64 backend writes instructions as data (jit.md §1). The JIT needs the encoder anyway, and node cannot read WAT.

---

## 2. Where I think the suggested direction has problems

### 2.1. wasmtime as the test engine

wasmtime is a good engine for the program suite: fast to start, WASI for I/O, and it runs GC, exceptions, and tail
calls (§3). But it has three problems as the *only* engine.

- **Its default collector leaks cycles.** wasmtime 50's default is `drc`, deferred reference counting with no cycle
  collection. A loop that makes 50 million self-referencing pairs grows to 1.6 GB under `drc` and stays at 15 MB
  under `copying` (§3). Quest's data is full of cycles (recursive closures, the compiler's graphs). Every wasmtime
  run must say `-C collector=copying`, and it is newer than `drc`, so it needs watching.
- **It cannot test the JIT or the REPL as the browser runs them.** Stage C instantiates a new module per input from
  inside a running session. A guest module cannot do that in wasmtime without a host program written against
  wasmtime's embedding API. In node and the browser it is a few lines of JavaScript.
- **It is not a browser engine.** Stack limits, cast and `i31` costs, exception tracebacks, and the JavaScript API
  (synchronous compilation limits, workers) differ. node is V8, Chrome's engine, and is installed (v26.13).

So: wasmtime for the program suite and benchmarks, node for the REPL, the JIT, and a second opinion on programs, and
Chrome and Safari by hand (both are installed) at the end of each stage. node needs binary modules, not WAT, which is
one reason for decision 10.

### 2.2. The JIT as the way to a browser REPL

A JIT per interaction is a good end state, and per-input modules match how the arm64 JIT already treats inputs (a
module per input, `qj_<n>`, jit.md §3.2). But it should not be the *first* browser REPL. The self-hosted interpreter
already exists, and compiling the driver ahead of time gives a browser REPL (stage B) with no in-browser code
generation, no in-browser linking, and no encoder. Stage B also flushes out everything the driver needs from its
environment (files, processes, line editing, stack depth), which the JIT needs too.

### 2.3. WASM-GC: right for the browser, but its price should be explicit

I agree with WASM-GC. The alternative, a linear-memory target compiled through the C backends, could reuse the C
runtime and the collector. But it needs a shadow stack for the collector's roots, ships its own collector, and needs
either 64-bit memories (missing or new in some browsers) or a 32-bit runtime ABI. WASM-GC avoids all of that, but it
gives up things the C representation relies on:

| The C representation relies on | WASM-GC has instead | Consequence |
|---|---|---|
| `QVal`, one untagged word that is a pointer, an integer, or a double's bits | no union of references and numbers | boxing in generic code (§5.2) |
| byte offsets into objects (`OffsetDict`, `ptrAdd`) | `struct.get` with a static field index, or `array.get` | records become arrays (§5.4) |
| interior pointers (`var`/`out` parameters, `@r.f`, `@a[i]`, `@x`) | none | locations are (container, index) pairs (§5.10) |
| a low tag bit on proxies | no pointer bits | a proxy is a type of its own, found by a cast (§5.11) |
| addresses, for identity hashing | no addresses, and no hash on arrays | a hash field, or a side table (§5.12) |
| `setjmp`/`longjmp` | the exception-handling proposal | simpler, but no frame walk for tracebacks (§5.15) |
| the C runtime, 11,800 lines | C cannot hold GC references | the runtime is rewritten (§7) |

The last row is the largest single cost of the whole plan. It also means two runtime ABIs to keep in agreement, with
shared behavior goldens, as the two compilers policy already arranges for the two compilers.

### 2.4. "Self-hosted" in a browser

The driver assumes a POSIX process. It reads `lib/` from disk, spawns `clang`, writes build directories, uses
`readline` and a terminal, and relies on 8 MB of main-thread stack (exceptions.md §6: about 2 KB per interpreted
call, up to the interpreter's 1,000-call limit). A page has no files or processes. A Chromium worker's stack is about
512 KB, measured in §3.1. This is not a reason to change direction, but it is real work in stage B (§9), and the
stack depth is now the largest known risk of stage B.

---

## 3. What was checked on this machine

- **wasmtime 50.0.1** (`/opt/homebrew/bin/wasmtime`) runs a module with GC structs, `i31ref`, `return_call`, and
  `try_table`/`throw` with a tag whose payload is an `eqref`, under `-W gc=y,exceptions=y,tail-call=y`.
- **Collectors:** `-C collector=drc|null|copying`. Under `drc`, 50 million self-cyclic pairs reached 1.6 GB resident;
  under `copying`, 500 million reached 15 MB in 1.2 s.
- **Linking:** `wasmtime run --preload a=a.wat b.wat` links two modules. Module `b` imported a function returning
  `(ref $t2)` and a mutable `eqref` global from `a`, with the types declared separately in each module: a chain
  `$t2 <: $t1 <: $t0` of structs of 2, 1, and 0 `mut eqref` fields. The types agreed, `b` upcast `$t2` to `$t1` with no
  cast, and `ref.cast` back worked. This is the tuple scheme of §5.3 across modules.
- **Stack overflow** under wasmtime is a trap ("call stack exhausted"), which no wasm handler catches;
  `-W max-wasm-stack=N` sets the limit.
- **node v26.13.0** runs GC, exceptions, and tail calls with no flags. `wasm-tools` 1.263.0 (installed 2026-11-12)
  assembles WAT for it.
- **Chrome and Safari** are installed. The built-in browser (Chromium 156) ran the stack probe below. Safari has not
  been tried.

### 3.1. Probes (step 1, 2026-11-12)

The probes are hand-written WAT modules, timed on a busy machine (load average 3–6), so the numbers are indicative,
not benchmarks. node figures are the best of three warm runs. wasmtime figures are one cold run each, including
compilation (about 13 ms) and the setup of each case.

| Probe | node (V8) | wasmtime |
|---|---|---|
| tuple of two `Int`s made and read 20M times: native `i64` fields | 86 ms | 87 ms |
| … two-value words, `(i64, eqref)` per slot (§6.4 b) | 105 ms | 96 ms |
| … uniform `eqref`, small `Int`s (`i31ref`) (§6.4 a) | 115 ms | 151 ms |
| … uniform `eqref`, large `Int`s (boxed) | 150 ms | 210 ms |
| `Array(Real)` of 1M filled once, summed 50 times: `(array f64)` | 48 ms | 62 ms |
| … boxed elements | 65 ms | 247 ms |
| generic `map (+1)` over 1M `Int`s, 20 times: native closure and `(array i64)` | 23 ms | 262 ms |
| … two-value words | 54 ms | 306 ms |
| … uniform, small `Int`s | 38 ms | 293 ms |
| … uniform, large `Int`s (a box per element per pass) | 505 ms | 683 ms |
| 100M calls of an `Int -> Int` closure: typed native entry, no cast | 33 ms | 843 ms |
| … `br_on_cast` to the native closure type, then the native entry (§5.9) | 31 ms | 921 ms |
| … uniform entry, boxing argument and result | 322 ms | 1,218 ms |
| sum of 1M small `Int`s 200 times: `(array eqref)` read directly | 136 ms | 382 ms |
| … through a struct holding a hash and the array (§5.12 a) | 131 ms | 437 ms |

| Probe | Result |
|---|---|
| compile, instantiate, and run a 1.4 KB module of 30 functions importing 8 functions and a global (a JIT input), 1,000 times in node | 10 µs each |
| deepest recursion, frame with 4 / 32 / 128 live `i64` locals: node main thread | 10,361 / 3,107 / 913 |
| … node worker (default `resourceLimits`) | 41,196 / 12,358 / 3,634 |
| … Chromium page | 10,335 / 3,099 / 911 |
| … Chromium Web Worker | 5,289 / 1,586 / 465 |
| stack overflow inside `try_table (catch_all …)` or `(catch_all_ref …)`, node and Chromium | never caught by wasm; a `RangeError` reaches JavaScript |

What they say:

- **Decision 4 holds.** For small `Int`s the uniform word costs about a third over native fields, and the two-value
  word (§6.4 b) is no better where it matters most: a generic `map` over small `Int`s is faster uniform (38 ms) than
  with pairs (54 ms). The pathology is large `Int`s and `Real`s in generic code, a box per value (505 ms against
  38 ms). Specialization and inlining at closed type arguments (§5.2) and typed scalar arrays (§5.7) are the remedies,
  not a different word. Reading boxed `Real`s from an array costs less than feared in V8 (1.35×, fill included).
- **Decision 5 holds.** The cast at a native call site costs nothing measurable in V8. Calling the uniform entry with
  boxing costs ten times as much, which is what a closure without a native entry would cost on every call.
- **§5.12 (a) holds:** wrapping arrays in a struct for their hash costs nothing in V8 and about 14% in wasmtime.
- **The JIT's latency is not a concern:** about 10 µs per small input module.
- **No wasm handler catches a stack overflow**, in V8 as in wasmtime. The host must catch it (§5.15, §9).
- **The stack is the serious risk (§2.4, §9).** A Chromium worker has about half the page thread's stack, roughly
  512 KB against 1 MB, where node's workers have 4 MB. A frame of 128 live words reaches a depth of only 465 in a
  Chromium worker. The interpreter's limit is 1,000 calls at about 2 KB of native stack each.
- **wasmtime is much slower than V8 at indirect calls** (about 8 ns a `call_ref`, against 0.3 ns) and at allocation.
  That is fine for correctness tests, but wasmtime's timings say nothing about the browser.

---

## 4. Where the backend starts

```
typed AST → lower → Core → simplify → specialize → closure-convert → represent(wasm) → describe(wasm) → wasm printer
                                                    └─ the same passes, whose layout decisions take a target
```

- **Branch after closure conversion.** Specialization, inlining, contification, and closure conversion do not depend
  on the target. Represent (ir.md §8.3) does: its plans (`box`, `cast`, `slot_box`, `view`, `runtime`, `adapt`,
  `rejected`) are decided by `codegen/layout`, whose answers come from "every slot is a 64-bit word". With a target
  parameter, the same pass makes the wasm decisions. Most plans keep their meaning; `box`/`unbox` stop being free;
  `cast` holds in more places, and `runtime` and `rejected` in fewer, since closures always agree (§5.9).
- **Print from the described IR**, as the C printer does (ir.md §8.5). Join points become `block`s with results;
  `jump k` becomes `br`; `loop` becomes `loop` inside a `block`; `switch` becomes `br_table`; `try` becomes
  `try_table`. Every IR construct has a direct wasm form, and the printer makes no representation decisions.
- **What is lost by not using the SSA:** its optimizations (escape analysis, scalar replacement, value numbering,
  selects, accumulator tail loops; ssa.md §4.1). The engines' optimizing tiers do some of this. Escape analysis
  matters more here than in C, because boxes are allocations. If measurements show the need, a GC-typed SSA is a
  later step, not a prerequisite.
- **Self-hosted only.** The bootstrap gets no wasm backend. A golden of the wasm stage needs `--self-hosted`, as the
  IR goldens do.

---

## 5. Representation

### 5.1. The table

| Quest type | Native (locals, parameters, results) | In a slot, and as a type parameter's value (`eqref`) |
|---|---|---|
| `Int` | `i64` | `i31ref` if it fits in 31 bits, else `(ref $boxInt)` |
| `Word.T` | `i64` | as `Int` (unsigned: `i31ref` below 2^30) |
| `Real` | `f64` | `(ref $boxReal)` |
| `Bool`, `Char` | `i32` | `i31ref` |
| `Ok` | nothing | `i31ref` 0 |
| `String` | `(ref $string)` | the same |
| tuple of n components | `(ref $tupN)`, or `(ref $tup0)` if it may be a proxy | the same |
| record | two values: `(ref $recPayload)` and `(ref $dict)` | `(ref $recBox)`, an immutable box of the two |
| variant | two values: `i32` tag and `eqref` payload | `(ref $varBox)` |
| option | `(ref $opt)` (a case's struct is a subtype) | the same |
| `Array(T)` | `(ref $array)`, an `(array (mut eqref))` | the same |
| function | `(ref $clos)`, or the subtype of its native signature | the same |
| `auto`, exception, `Dynamic` | structs of their own | the same |
| descriptor | `(ref $desc)` | — |

The word is `eqref`, not `anyref`, so that `is` is `ref.eq`. Host references (`externref`) are not `eqref`; a host
handle is wrapped in a struct or represented as an `i32` handle into a table the host keeps.

### 5.2. Scalars and boxing

`Int` arithmetic wraps at 64 bits (type-system.md §6.3.1), so `i31ref` cannot be `Int`'s only word form. Boxing tests
whether the value fits in 31 bits and makes an `i31ref` if it does, otherwise a `$boxInt`. Unboxing does
`br_on_cast i31` and otherwise reads the box. Most integers in the compiler (indices, counts, tags, characters) are
small, so the allocation is rare and the branch predictable. `Real` always boxes. Caching boxes for common values (0.0,
1.0) is optional.

`is` on a type parameter's values already takes the type's descriptor (ir.md §9, Described), so boxed `Int`s and
`Real`s can be compared by value, as the C runtime compares their bits. `is` on a box must never be `ref.eq` alone.

Boxing makes specialization and inlining (c-representation.md §6.4.3, ir.md §8.6) worth more than they are in C. The
`should_specialize` rule should consider scalar type arguments, not only records and variants.

### 5.3. Tuples

`$tupN` is a struct of N `mut eqref` fields, declared `$tupN <: $tup(N-1) <: … <: $tup0`. Quest's tuple width
subtyping drops trailing components, so an upcast is a wasm upcast, with no cast or copy (checked across modules,
§3). Components are read with `struct.get` at a static index. Every field is mutable, because wasm subtyping requires
field mutability to match; Quest's `var` checking is static anyway.

A tuple type that may be a proxy (`may_be_proxied`) is held as `(ref $tup0)`, and a component read is
`br_on_cast $tupN` with the proxy's path on failure. The cast replaces C's low-bit test.

An alternative is to make tuples arrays like records (§5.4), which would make every slot addressable by index (§5.10)
at the cost of a bounds check on each read. I recommend structs: tuples are the most common aggregate, and V8
optimizes struct access well.

### 5.4. Records

Width subtyping drops arbitrary fields, so a field's position cannot be static, and `struct.get` needs a static
index. A record's payload is therefore an `(array (mut eqref))`, with element 0 holding its layout descriptor and the
fields after it, in name order. The evidence that C passes as an offset table becomes an index table: `$dict` is a
struct of an `(array i32)` of indices and the `stored_types` (c-representation.md §5.2). `r.x` is two `array.get`s
(table, then payload) and an unbox. Records are passed as two wasm values, and functions return them as two results
(multi-value), like C's register pairs. In a slot, a record is boxed in an immutable `$recBox`, as C boxes
`QRecordVal`.

The IR's `embedded` boxes (one allocation for a struct and its boxes) have no WASM-GC counterpart, since objects do
not nest. A tuple of three records costs four allocations, not one.

### 5.5. Variants

A variant is two values, an `i32` tag in its type's numbering and an `eqref` payload, boxed in an immutable `$varBox`
in a slot. Tag maps are `(array i32)`s. This is C's design unchanged.

### 5.6. Options

`$opt` is a struct holding an `i32` tag. Each number of components has a subtype `$optN` that adds N `mut eqref`
fields. Cases without components are static singletons, made once per module or shared through the runtime. To read
the tag, `struct.get $opt 0`; to read a component, cast to `$optN`. Options are values (extensions.md, "Options as
Values"; the option-values plan's single-word `is`), and `quest_option_is` carries over in the runtime. A decision for
later: whether an option type whose cases all lack components becomes an `i31ref` instead of a singleton.

### 5.7. Arrays

`Array(T)` is an `(array (mut eqref))` for every `T`, so that `Array(Int)` and generic code's `Array(A)` agree (arrays
are invariant, and generic code reads them in place). The cost is boxed elements: `Array(Real)` holds a box per
element. This is the one place where the boxing in decision 4 hurts numeric programs badly. The later fix (§6.4,
alternative c) is typed arrays for scalar element types, `(array (mut i64))` and `(array (mut f64))`, which generic code
reads through a three-way dispatch on the element descriptor that it already holds.

### 5.8. Strings

`$string` is a struct with a mutable length and a mutable reference to an `(array (mut i8))`, whose length is the
capacity. Strings are mutable (`string.setChar`, `setSub`), so JavaScript strings do not fit. Text crosses to the host
as bytes, and the host decodes it as UTF-8.

### 5.9. Closures

`$clos` is a struct whose first field is the **uniform entry**, a `(ref $uN)` where `$uN` takes the closure, the
descriptors, and N `eqref`s, and returns an `eqref`. For each native wasm signature S, a subtype `$closS` adds the
**native entry**, a typed `(ref $fnS)`. Each function's own closure struct is a subtype of `$closS` that adds its
captured variables. The entries cast the closure to that struct on entry.

- **Native call site** of static type S: `br_on_cast $closS`, then `call_ref` the native entry. On failure (generic
  code made the closure and knows only its uniform entry), box the arguments, call the uniform entry, and unbox the
  result.
- **Generic call site:** always the uniform entry.
- **The uniform entry of a native function** is a small wrapper that unboxes, calls, and boxes. The backend emits it
  for functions that escape as values.

So any closure can be called at any of its layouts, and the C rule that a `QVal` result agrees only with integers and
pointers has no counterpart here. Adapters remain only for subtyping that changes a view (a record parameter's
table, a variant's tags); those are `adapt` plans, as now. The cost is code size, one wrapper per escaping function,
and a type check at each native indirect call.

### 5.10. Locations: `var` and `out` parameters, `@`

WASM-GC has no pointer into the middle of an object, so a location is passed as two values: a container (`eqref`)
and an `i32` index.

- **Array element and record field** (`@a[i]`, `@r.f`): the array or the record's payload, and the index. A read
  `br_on_cast`s to the array type and does `array.get`.
- **Tuple component** (`@t.i`): the tuple and `i`. The callee does not know `i` statically, so a tuple location is
  read and written through a runtime helper (`br_table` on `i`). Tuple `var` components passed by reference should
  be rare; step 1 counts them in the compiler.
- **Local variable** (`@x`, `var(e)`): a heap cell, a one-element array, allocated where the address is taken. C
  uses a stack slot. A cheaper later option is copy-in/copy-out through multi-value results when the local is passed
  once in the call and nothing in a handler reads it. The C backend's tier-2 shadow cells (c-representation.md
  §6.5.2) already accept that semantics, so it is not a new compromise, but it is a decision.
- **Module `var`s** (the REPL's slots are boxes already, jit.md §3.2): the box and 0.

A location's type does not say which kind of container it is in, so the representation is the pair, not a struct per
kind, to avoid an allocation per `@` argument.

### 5.11. Proxies

`$proxy` is a struct (the original, the stored and view descriptors, an option's tag map, the cache), declared as a
subtype of `$tup0`, so that a value of a proxiable tuple type is a `(ref $tup0)` either way. For options, the
proxiable form is `eqref` and the tag read casts. The rules of c-representation.md §5.8 carry over unchanged: no
proxy chains, `is` compares originals, `var` components are written in the original, and immutable components are
cached. Only the test changes, a cast instead of a bit.

### 5.12. Identity and identity hashing

`is` is `ref.eq` after unproxying (and by value for boxed scalars, §5.2). `hash.identityHash` cannot use an address.
The choices:

- (a) a lazily assigned `i32` hash field in every struct that can be hashed (tuples, options, closures, strings, the
  record box, auto values). Arrays cannot have extra fields, so Quest arrays and record payloads would have to be
  wrapped in a struct, adding an indirection to every element access.
- (b) a hash field in structs, and a side table for arrays, which leaks without weak references. wasm has no weak
  references. A host `WeakMap` would work in JavaScript, but not in wasmtime.
- (c) (a), plus arrays wrapped in a struct only when the type checker cannot rule out hashing them. Not tractable
  across polymorphism.

I lean to (a) with the array wrapper. The wrapper also gives arrays a place for a hash, and an `Array(Real)` a place
to hold a typed backing store later (§5.7). Step 1 measures what the indirection costs. The compiler uses
`identityHash` in its interpreter, `represent`, and `dynamicjson`, so this matters for stage B.

### 5.13. Descriptors

`$desc` is a struct hierarchy by kind (tuple, record, variant, function, …), mirroring `QTypeDescriptor`. Closed
descriptors are immutable globals. WASM-GC allows `struct.new` and `array.new_fixed` in global initializers, but not
cycles, so recursive types' descriptors are built at module start, with a mutable field closing each cycle.
Templates, `instantiate`, view maps, `quest_is_subtype`, and the offset-table map work as in C, rewritten in Quest
(§7). The uniform quantifier rule (one descriptor parameter per quantifier) is unchanged.

### 5.14. Modules and globals

A module's record is a mutable global holding a record (two globals: payload and table), exported when other units
import it. Initialization is lazy, guarded by an `i32` global, as now. An imported function is called directly through
a wasm import rather than through the record, as C calls the module's exported wrapper.

### 5.15. Exceptions

One tag, `$quest`, carries the exception (an `eqref`: its generative identity) and its payload (an `eqref`). `try`
becomes `try_table` with `catch $quest` (or `catch_all_ref` for `else`), and re-raising is `throw_ref`. C's
`volatile` rule (ir.md §6.4) disappears.

Tracebacks (exceptions.md §5) walk frames by the frame-pointer chain; wasm has no frame walk. Choices: under a
JavaScript host, an import called at a traced raise (`all traced`, §5.1 there) can read `new Error().stack`, which
names wasm functions through the name section. Under wasmtime there is nothing equivalent, so tracebacks would be
missing or need a shadow stack of function ids. I recommend the JavaScript route, with wasmtime's goldens recording
no frames, as an accepted difference (jit.md §4 has precedent).

Stack overflow is a trap in wasmtime and a `RangeError` in V8, and in neither does a wasm `try` catch it. That
matches compiled code today ("a handler cannot catch it"). In the browser, the host catches the `RangeError`, ends
the input, and rolls it back, which is better than native, where the session ends (jit.md §1).

### 5.16. The type section

Because every slot is an `eqref`, the wasm types do not depend on Quest's types. The set is finite and small:
`$tup0…$tupK`, `$opt` and `$optN`, the boxes, `$recPayload`, `$dict`, `$string`, `$array`, `$proxy`, the descriptor
hierarchy, and the closure types by wasm signature. Only the closure types grow with the program, and each depends
only on its signature's wasm value types. Each type is emitted the same way in every module, in a canonical order, so
cross-module structural canonicalization makes them agree (§3). Precise per-Quest-type structs (a `Tuple Int String`
as `{i64, ref $string}`) would make this hard across separately compiled units, which is another argument for
decision 4.

---

## 6. Polymorphism

### 6.1. What carries over

The C design rests on one property: **a native aggregate and a generic aggregate are laid out alike**, so that
passing an `Array(R)` or a tuple to polymorphic code is a cast, and `is` and `var` sharing survive (runtime-design.md
§2.2). With every slot an `eqref`, the property still holds. `Tuple Int String` and `Tuple A B` are both `$tup2`, and
`Array(Int)` and `Array(A)` are both `$array`. So, mostly unchanged:

- **Unbounded quantifiers:** one descriptor parameter each; values of `A` are `eqref`s; aggregates over `A` pass by
  `cast`, which for wasm is usually nothing.
- **Bounded quantifiers** (`A <: B`): values held at their own view, fields and cases read through memoized view
  maps (`(array i32)`s), conversion by `view` plans.
- **Existentials** and path types: erased type components; values at `eqref` or the bound's representation.
- **Higher-kinded parameters, abstract types:** opaque descriptors, as now.
- **`auto`, `inspect`, `Dynamic`:** descriptors and runtime subtyping, with payloads in the witness-independent layout.
- **Polymorphic recursion:** no problem, since nothing is monomorphized by necessity.

### 6.2. What changes

- **`box`/`unbox` are real** (§5.2): an `i31` test, and sometimes an allocation, at every boundary where a native
  `Int` becomes a word: a polymorphic call's argument, a store into any slot, a read from any slot. In C, a tuple of
  two `Int`s stores raw words; here it stores `i31ref`s or boxes. Monomorphic code over aggregates pays this too,
  which C never did. That is the price of decision 4.
- **Closures never need layout conversion** (§5.9). The `rejected` conversions caused by closures in arrays, and the
  closures inside a tuple that a polymorphic call must convert component by component (c-representation.md §6.4.3),
  go away.
- **Polymorphic `var` parameters:** a location is a container and an index whatever its type, and its slot is an
  `eqref`, so a generic `var p: A` and a native `var p: Int` both receive a location. They differ in what they read:
  the native callee unboxes. Shadow cells (tier 2) are needed only where C needs them for a different reason (a
  record's box), and probably not at all.
- **Specialization** should also trigger on scalar type arguments (§5.2).

### 6.3. Records under polymorphism

A record is two values natively and one boxed word in a slot, as in C, so `slot_box` and `slot_unbox` keep their
meaning. Generic code that makes a record whose field has type `A` stores an `eqref` there. A native reader at
`A = Int` unboxes it. In C, by contrast, the layouts agree only because the word is the integer. The `stored_types`
mechanism is still needed for depth subtyping and bounded parameters, but not for scalars.

### 6.4. Alternatives for the word

- **(a) Uniform `eqref`, `i31ref` and boxes** (recommended). One layout per arity, a finite type set (§5.16),
  precise collection, and simple codegen. Its costs: boxing `Real`s and large `Int`s in aggregates and in generic
  code, and a branch on every unbox. This is what other WASM-GC compilers for languages with uniform polymorphism
  have converged on.
- **(b) Two-wasm-value words:** every word is an `(i64, eqref)` pair; scalars use the `i64`, references the `eqref`.
  There is no boxing at all, and native and generic layouts still agree. But every slot is two fields (about 1.5×
  the memory), every generic parameter two wasm parameters, and every aggregate struct twice as wide. It is
  attractive for numeric code and costly everywhere else. It is worth a micro-benchmark in step 1 against (a), because
  it is the only design that keeps C's "no boxing" property.
- **(c) Typed slots, with generic code dispatching on descriptors.** `Tuple Int String` is `{i64, ref}`. Generic code
  that reads a `Tuple A B` component must know which struct type it has, and there are 3^n shapes per arity. This is
  infeasible for tuples. It is feasible, and worthwhile, for arrays alone: three element representations, chosen by
  the element descriptor that generic code already has. That is §5.7's later step.

---

## 7. The runtime

The C runtime (`runtime/`, about 11,800 lines) cannot operate on GC references, so the wasm target needs its own.

- **In Quest, over intrinsics.** A module of unsound primitives (the `os/value` scheme, jit.md §3.11), compiled by
  the wasm backend to single instructions: kind tests (`ref.test`), struct and array access by index, box and unbox,
  `ref.eq`, `i31` operations, byte arrays. The runtime's logic (conversion, proxies, runtime subtyping, descriptor
  instantiation, view maps, record table maps, value printing for echo and the REPL, `dynamic.extern` and `intern`,
  string operations) is written in Quest on top. Hand-written WAT only where Quest cannot express something.
- **The library's externals.** The library names about 150 distinct external C symbols and expressions
  (`quest_real_sin`, `(&quest_exc_real_error)`, `QUEST_REAL_PI`). The wasm backend maps each one to an intrinsic, a
  runtime function, or a host import. The table plays the role that `codegen/externals` plays for C, and a test checks
  that it covers `lib/`.
- **Real numbers, a hard part.** Printing (`%.17g`-like shortest digits, runtime line 758 on) and parsing (the
  lexer's real literals, `conv`) must match the C runtime byte for byte, because the goldens are shared. That means a
  correctly rounded `strtod` and digit generation in Quest (`bignum` exists). `sin`, `exp`, `log`, `pow` and the rest
  are not wasm instructions. JavaScript's `Math` and a Quest port of a libm can differ from Apple's libm in the last
  bit, which a 17-digit print shows. Decide whether goldens with transcendental results are shared or recorded per
  target.
- **The host interface:** write bytes to a stream, read a line, read and write a file (in a virtual file system in
  the browser), time, exit, random seed. WASI preview 1 under wasmtime (it needs a small linear memory for buffers,
  which a GC module may also have) and JavaScript in node and the browser.

---

## 8. Units and linking

- **A module per unit**, exporting its record global, its functions (for direct calls), and its dictionaries. It
  imports the runtime module, the host interface, and its imports' exports, by unit name. wasmtime links them with
  `--preload` (§3); node and the browser with a small JavaScript loader.
- **The library and the runtime** are prebuilt modules, as `lib/` is prelinked for C.
- **Whole programs** (ir.md §8.6) still work: one module.
- **Interface artifacts:** `.qi` stays as it is. Instead of `.int.h`, the wasm backend needs the import signatures,
  which come from the interface and the fixed type set.
- **Releases:** the driver as wasm modules is a new release artifact, built by the native compiler.

---

## 9. The REPL in a page (stage B)

- **A Web Worker** runs the driver. Chrome limits synchronous compilation on the main thread, and a worker keeps the
  page responsive. The page sends input lines and receives output.
- **An entry per input**, not a read loop. A blocking read in a worker needs `SharedArrayBuffer` and `Atomics.wait`,
  and that needs cross-origin isolation headers. An exported `evaluate(input)` that returns when the input has run
  needs neither. The REPL's multi-line heuristics (repl.md §3.2) move to the entry's caller, or the entry returns
  "need more".
- **Line editing** is the page's; `lib/io/readline`'s terminal code is not used.
- **Files:** a virtual file system holding `lib/` (sources, `.int`, `.qi`) and the user's scratch files, bundled with
  the page or fetched lazily.
- **Interrupts** (Ctrl-C): a running wasm call cannot be interrupted, only the worker terminated, which loses the
  session. Keeping it means polling a flag in loop headers and calls, which again needs a `SharedArrayBuffer`. This
  is a decision: accept "interrupt restarts the session" at first.
- **Stack:** the interpreter's 1,000-call limit must hold within a worker's stack (§2.4). A Chromium worker has
  about 512 KB (§3.1), against the 2 MB that 1,000 calls of the natively compiled interpreter use. How much a call
  uses compiled to wasm is not known until the interpreter is, so step 5 measures it first. The options, in order of
  preference:
  1. make the interpreter's evaluation use less stack per Quest call (fewer nested wasm frames per call);
  2. run the driver on the page's thread (about 1 MB), giving up the worker's benefits (decision 9);
  3. run the interpreter on a stack of its own through the stack-switching proposal (JSPI in browsers;
     wasmtime has `-W stack-switching`), if engines let such a stack be larger;
  4. lower the limit in the browser, a difference from every other implementation.
  Whatever the limit, a `RangeError` from a deeper overflow must end the input, not the session.
- **Size:** the driver is 84,000 lines of Quest. Its wasm size and its startup time (compiling it, loading `lib/`'s
  interfaces) are unknown, and step 4 measures them.

---

## 10. The JIT (stage C)

The arm64 JIT's design maps onto modules closely:

- **An input is a module** (`qj_<n>`), as now. Its record is an exported global. A later input imports the earlier
  inputs' records it uses, and the loader supplies them.
- **Slots are boxes** already (jit.md §3.2), so redefinition in place needs nothing new: a box is a `$tup1` whose
  component a later input stores.
- **A failed input** is simply not committed: its module stays instantiated and unused, as its machine code does now.
- **"The driver is the library"** (jit.md §1): an input that imports `writer` or `questlang/...` must reach the
  driver's own instances. This works only if the driver is built as per-unit modules (§8), whose exports the loader
  passes to each new input's instantiation. That is a constraint on stage B's build.
- **Compiling in the page** needs the encoder (decision 10) and the backend inside the driver. Latency per input is
  one `new WebAssembly.Module` and one instantiation: about 10 µs for a 30-function module in node (§3.1), so the
  compiler, not the engine, will set the JIT's latency.
- **The fingerprint** check (jit.md §3.3) carries over, comparing an input's expectations with the driver's modules.

---

## 11. Steps (tentative)

Each stage's last step ends with the suite run on the new target. Costs are recorded as actuals, not estimated.

1. **Probes**, before any compiler code, in hand-written WAT, under wasmtime and node (which needs an assembler, §12):
   (a) the micro-benchmarks of §6.4, (a) against (b): a tuple-of-`Int`s loop, an `Array(Real)` sum, a record field
   loop, a generic `map` over `Int`s; (b) the cost of a cast at a native closure call (§5.9) and of the array wrapper
   (§5.12); (c) instantiation latency of a small module in node; (d) the stack depth reachable in a node worker and in
   Chrome, by recursion depth of a frame of the interpreter's size; (e) whether V8 lets a wasm `catch_all` see a stack
   overflow; (f) exceptions (`exnref`) and tail calls in Safari. The results may change decisions 4, 5, and 9.
   *Done 2026-11-12 (§3.1) except (f), Safari. Decisions 4 and 5 hold; decision 9 holds, but the worker's stack
   is the risk step 5 must face first.*
2. **The target parameter in `codegen/layout`** and a wasm represent stage, golden-tested on the IR alone, with the C
   target's goldens unchanged.
3. **The printer and encoder** for a first subset (scalars, tuples, closures, no polymorphism), running `examples/`
   under wasmtime; then all of the IR; then the runtime in Quest, written alongside.
4. **Stage A complete:** the program suite on wasm under wasmtime and node, its accepted differences recorded
   (tracebacks, transcendental reals); the benchmarks for scale.
5. **The driver as wasm** (stage B): the host interface, the virtual file system, the per-input entry, the worker,
   and the page. The interpreter's transcripts run in node against the wasm driver.
6. **The JIT** (stage C): the backend running in the page, the loader, per-input modules, and the JIT's transcripts
   in node.

---

## 12. Questions for the owner

1. ~~Is stage B, an interpreting REPL in the browser before the JIT, acceptable as the first deliverable?~~
   *Answered 2026-11-12: yes, interpreter first* (decision 1).
2. ~~May I install `wasm-tools`?~~ *Installed by the owner 2026-11-12.* binaryen's `wasm-opt` would also allow
   measuring whether a post-pass optimizer helps.
3. **Which browsers must work?** Chrome alone (via node's V8) is easiest. Safari's support for exception handling and
   tail calls is the newest and needs checking.
4. **Are behavior differences acceptable** where wasm forces them: no tracebacks under wasmtime, possibly last-bit
   differences in transcendental `Real` functions, an interrupt that restarts the session?
5. **Performance target:** is the wasm target judged as a REPL (startup, latency per input), or also by the
   benchmark geomean like the native backends? This decides how soon §5.7's typed arrays and §6.4's alternative (b)
   matter.
6. **Hosting:** will the page be served with cross-origin isolation headers (needed for `SharedArrayBuffer`, which
   would allow interrupts and a blocking read)?
