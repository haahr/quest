# Plan: A Self-Hosted REPL in the Browser, on WebAssembly GC

The goal: Quest's own REPL, the self-hosted driver, running in a browser page. The driver is compiled to WebAssembly by
a new backend, `wasm`, that targets the GC proposal (WASM-GC: typed structs, arrays, `i31ref`, and the engine's
collector) rather than a linear memory. At first the browser REPL interprets its inputs, as `--no-jit` does. Later a
JIT compiles each input to a WebAssembly module of its own, which the page instantiates and links against the modules
already loaded, as the arm64 JIT ([jit.md](jit.md)) does with machine code.

The backend is written in Quest, in `questlang/`; the bootstrap does not get it ([testing.md](testing.md) §2.8).

**Status: proposed** (2026-11-12, revised the same day after a review). Nothing is built. Decision 1 is the owner's;
the others are recommendations awaiting the owner. Section 2 says where the suggested direction is a problem.
Section 3 records what was measured on this machine. Sections 5–7 (representation, polymorphism, traps) and 10
(the stack) are the core. Section 15 has the questions for the owner, and section 16 maps the review's questions to
the sections that answer them.

---

## 1. Decisions

Each decision comes with its alternative and its cost. Decisions that depend on how engines behave were probed
(§3); what remains to be measured is said where it matters.

1. **Four stages, in this order** (decided 2026-11-12):
   - (A) programs compiled ahead of time to WASM-GC, run under wasmtime and node;
   - (S) the compiler compiled by (A) compiling itself under node, outside a browser, to a fixed point (§14,
     step S);
   - (B) the driver from (S) in a page, *interpreting* its inputs: the first browser REPL;
   - (C) the JIT: each input compiled in the page to a module, instantiated and linked by the page.

   The owner chose B before C in this plan. In Fable's plan ([wasm-plan-fable.md](wasm-plan-fable.md) §11, answer 5),
   the owner chose the compiler compiling itself outside a browser as the first milestone. Both answers hold with S
   placed between A and B, which is where this plan puts it.
2. **WASM-GC**, as suggested: the engine's collector, precise roots, small modules, and objects JavaScript can hold.
   The price (§2.3) is a second runtime ABI and a runtime that cannot be the C one.
3. **The backend starts from the described IR, not from the SSA** (§4), with its own represent and describe decisions
   through a target parameter to `codegen/layout`.
4. **One uniform value word, `eqref`** (§5.1, §6.4). Values of known type are native inside a function (`i64`,
   `f64`, `i32`, typed references). In tuple, record, option, and variant slots, and as type parameters' values, they
   are `eqref`s: `i31ref` for `Bool`, `Char`, `Ok`, and small `Int`s, and boxes for the other `Int`s, `Word`s, and
   `Real`s. The probes confirmed this (§3.1).
5. **Closures with two entries** (§5.9): a uniform entry (all `eqref`), and a native entry whose signature erases
   every reference type to `eqref` (the *closure signature*, §5.9.1). Native code calls the native entry after a cast;
   generic code calls whichever entry its static type allows. The probes confirmed this too.
6. **Typed arrays from the start** (§5.7), *revised*: `Array(Int)` and `Array(Word)` hold `i64`, `Array(Real)` holds
   `f64`, `Array(Bool)` and `Array(Char)` hold `i8`, and other arrays `eqref`. Each is held in a struct (for its hash,
   §5.12) whose subtype tells generic code the element kind. Deferring this would change every module's array access
   later, an ABI change, and the compiler's hash vectors would box full-width `Word`s until then.
7. **One module per unit, linked by imports** (§8), for programs, the driver, and the JIT alike, with one fixed
   recursion group of runtime types shared by every module (§5.16).
8. **Every reference crosses a unit boundary as `eqref`** (§5.16.3): an exported function's signature is its closure
   signature, computed from the interface alone. The receiver casts.
9. **The runtime written in Quest** over a few dozen wasm intrinsics (§9), with a small host interface implemented
   over WASI for wasmtime and in JavaScript for node and the browser. Bytes cross through a staging area in a linear
   memory (§9.3).
10. **No trap is a Quest exception** (§7). Every operation that Quest defines to raise is tested before the
    instruction that would trap. A trap is either resource exhaustion (stack, memory) or a bug in the compiler.
11. **Test engines: wasmtime (`-C collector=copying`) and node, from step 1**, and Chrome by hand at each stage's end.
    Safari is still untested (§15).
12. **The driver runs in a Web Worker with an `evaluate(input)` entry** (§12), unless the stack policy (§10.4) moves it
    to the page's thread.
13. **The backend writes the binary format directly**, with a WAT printer beside it for goldens. Its output is checked
    against `wasm-tools` (installed: 1.263.0).
14. **The stack policy for the interpreter in a page is open** (§10.4). The interpreter needs about 6 KB of native
    stack per interpreted call. A page gives about 1 MB, a worker about 512 KB, and JSPI no more than 1 MB. 1,000
    interpreted calls do not fit. The owner must choose what gives.

---

## 2. Where I think the suggested direction has problems

### 2.1. wasmtime as the only test engine

- **Its default collector, `drc`, does not collect cycles.** 50 million self-referencing pairs grew to 1.6 GB under
  `drc`, and stayed at 15 MB under `-C collector=copying` (§3). Every run must name `copying`.
- **It cannot host the JIT.** A guest module cannot instantiate new modules without a host program written against
  wasmtime's embedding API; in node and the browser that takes a few lines of JavaScript.
- **It is not a browser engine.** Its indirect calls cost about 25 times V8's (§3.1). Its stack, its traps, and its
  lack of a JavaScript API differ from the browser's.
- **Stack switching is unavailable in it** on this machine (§3.2).

So the plan uses wasmtime for the program suite, node (V8, Chrome's engine) for the REPL, the JIT, timings, and a
second run of programs, and Chrome by hand.

### 2.2. The JIT as the way to a browser REPL

A JIT per input is a good end state. It is not the first browser REPL (decision 1).

### 2.3. WASM-GC's price

| The C representation relies on | WASM-GC has instead | Consequence |
|---|---|---|
| `QVal`, one untagged word that is a pointer, an integer, or a double's bits | no union of references and numbers | boxing in generic code (§5.2) |
| byte offsets into objects | `struct.get` at a static index, `array.get` | records become arrays (§5.4) |
| interior pointers (`var`/`out`, `@`) | none | locations are (container, index) pairs (§5.10) |
| a low tag bit on proxies | no pointer bits | a proxy is a type of its own, found by a cast (§5.11) |
| addresses, for identity hashing | none, and no fields on arrays | a hash field, and arrays wrapped in a struct (§5.12) |
| `setjmp`/`longjmp` | exception handling | simpler, but no frame walk for tracebacks (§5.15) |
| signals for stack overflow | a trap no wasm handler sees | the host handles overflow (§10.5) |
| an 8 MB stack | about 0.5–1 MB | the interpreter does not fit (§10) |
| the C runtime, 11,800 lines | C cannot hold GC references | the runtime is rewritten (§9) |

### 2.4. The stack

The serious problem, measured in §3.2 and treated in §10. The driver's compiler fits in a browser's stack for
ordinary inputs; its interpreter does not, at the interpreter's own limit of 1,000 calls.

### 2.5. "Self-hosted" in a browser

The driver assumes a POSIX process: files, `clang`, processes, `readline`, a terminal. §11 and §12 say what the page
replaces them with.

---

## 3. What was checked on this machine

- **wasmtime 50.0.1** runs GC structs, `i31ref`, `return_call`, and `try_table`/`throw` with an `eqref` payload, under
  `-W gc=y,exceptions=y,tail-call=y`. `-C collector=drc|null|copying`: under `drc`, 50 million self-cyclic pairs
  reached 1.6 GB resident; under `copying`, 500 million reached 15 MB in 1.2 s.
- **Linking:** `wasmtime run --preload a=a.wat b.wat` links two modules whose separately declared types (a chain of
  structs of 2, 1, and 0 `mut eqref` fields) agree. An upcast needed no cast, and `ref.cast` back worked.
- **Stack overflow** is a trap in wasmtime ("call stack exhausted") and a `RangeError` in V8 (§3.2).
- **node v26.13.0** runs GC, exceptions (including `exnref`), tail calls, and JSPI with no flags. **`wasm-tools`
  1.263.0** assembles and validates.
- **Chromium 156** (the built-in browser) ran the stack probes. **Safari** has not been tried.

### 3.1. Representation probes (2026-11-12)

The probes are hand-written WAT, run on a busy machine (load average 3–6), so the timings are indicative. node figures
are the best of three warm runs. wasmtime figures are one cold run each, including about 13 ms of compilation.

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
| … through a struct holding a hash and the array (§5.12) | 131 ms | 437 ms |
| compile, instantiate, and run a 1.4 KB module of 30 functions importing 8 functions and a global, 1,000 times | 10 µs each | — |

What they say:

- **The uniform word holds.** For small `Int`s it costs about a third over native fields. The two-value word is no
  better where generic code matters (38 ms against 54 ms for `map`). The cost is in boxes: large `Int`s, `Word`s, and
  `Real`s in generic code (505 ms). The remedies are typed arrays (decision 6), specialization, and inlining, not a
  different word.
- **Two-entry closures hold.** The cast at a native call site costs nothing measurable in V8; the uniform entry with
  boxing costs ten times as much.
- **The array wrapper costs nothing in V8** and about 14% in wasmtime.
- **Module latency is not a concern** for the JIT.
- **wasmtime's timings say nothing about the browser.**

### 3.2. Limits, stacks, and bytes (2026-11-12, second round)

**Engine limits.** Modules generated at and just past each limit:

| Limit | V8 (node) | wasmtime | `wasm-tools` |
|---|---|---|---|
| supertype chain depth | 63 (64 rejected) | 63 (64 rejected) | — |
| struct fields | 10,000 accepted | accepted | 10,001 refused |
| function parameters / results | 1,000 accepted | — | 1,001 refused |
| locals per function | 50,000 (50,001 rejected) | rejected past 50,000 | — |
| operands of `array.new_fixed` | 10,000 (10,001 rejected) | 10,001 accepted | — |
| array length | about 1 GiB of payload: 1,073,741,792 `i8`, 134,217,720 `eqref`; past it `array.new` traps ("requested new array is too large") | not probed | — |

The JavaScript API also documents limits on function body size (7,654,321 bytes), types and functions (1,000,000
each), and imports and exports (100,000 each). Those were not probed.

**Stacks.** Deepest recursion of a function with 4 / 32 / 128 live `i64` locals:

| Where | Depth | Stack, roughly |
|---|---|---|
| node main thread | 10,361 / 3,107 / 913 | 1 MB |
| node worker (default `resourceLimits`) | 41,196 / 12,358 / 3,634 | 4 MB |
| Chromium page | 10,335 / 3,099 / 911 | 1 MB |
| Chromium Web Worker | 5,289 / 1,586 / 465 | 512 KB |
| JSPI (`WebAssembly.promising`), on the page or in a worker, in node or Chromium | 10,151 / 3,044 / 894 | 1 MB |

- JSPI runs wasm on a stack of its own of V8's `--wasm-stack-switching-stack-size`, 984 KB by default. Setting it to
  8,000 in node did not deepen the recursion, nor did `--experimental-wasm-growable-stacks`. A page cannot set V8
  flags anyway.
- Core stack switching (`cont.new`/`resume`) is behind `--experimental-wasm-wasmfx` in V8. wasmtime 50 refuses it on
  this machine: "the wasm_stack_switching feature is not supported on this compiler configuration".
- No wasm handler (`catch_all`, `catch_all_ref`) caught an overflow in node or Chromium; JavaScript received a
  `RangeError`.

**The native compiler's and interpreter's stack.** These were measured by running stage 2 (`./quest`'s compiler)
under `ulimit -s`, bisecting for the smallest stack that works:

| Run | Smallest stack |
|---|---|
| compile `questlang/ir/lower.mod.quest` (the largest source, through arm64 code generation) | ≤ 64 KB (fails at 32) |
| compile `questlang/types/canonical.mod.quest` | ≤ 64 KB |
| compile `questlang/driver/main.quest` | about 160 KB |
| compile a block of 3,000 `let`s | about 23 KB |
| compile `let x: Int = 1 + 1 + … + 1` with 3,000 terms | about 2.6 MB (0.9 KB per term of nesting) |
| interpret (`--no-jit`) `f(100)` for `f(n) = if n is 0 then 0 else f(n - 1) + f(0) + 1 end` | about 650 KB |
| … `f(900)` | about 5.6 MB: **about 6.2 KB per interpreted call** |

exceptions.md §6 estimates about 2 KB per interpreted call of a simple function. This function, whose body nests three
calls and two additions, measures three times that.

**Bytes across the host boundary.** Moving 3.4 MB, about the size of `questlang/`'s 3,396,435 bytes of source,
between a linear memory and a GC byte array took 2.2 ms each way warm (8.8 ms cold), with a loop of `i32.load8_u` and
`array.set`. Reading it from JavaScript one byte per exported call took 14–23 ms.

---

## 4. Where the backend starts

```
typed AST → lower → Core → simplify → specialize → closure-convert → represent(wasm) → describe(wasm) → wasm printer
```

- **Branch after closure conversion.** Represent (ir.md §8.3) is decided by `codegen/layout`, whose answers come from
  "every slot is a 64-bit word". With a target parameter, the same pass makes the wasm decisions. `box`/`unbox` stop
  being free; `cast` holds in more places; `runtime` and `rejected` hold in fewer, because closures always agree
  (§5.9).
- **Print from the described IR.** A join point becomes a `block` with results, `jump` becomes `br`, `loop` becomes
  `loop`, `switch` becomes `br_table`, and `try` becomes `try_table`.
- **What is lost by skipping the SSA:** its optimizations (ssa.md §4.1). Escape analysis matters more here, since
  boxes are allocations. A GC-typed SSA is a later option, not a prerequisite.
- **Self-hosted only.** Goldens of the wasm stages need `--self-hosted`.

---

## 5. Representation

### 5.1. The table

| Quest type | Native (locals, internal calls) | Slot and type-parameter form (`eqref`) |
|---|---|---|
| `Int`, `Word.T` | `i64` | `i31ref` if it fits in 31 bits (signed for `Int`, below 2^30 for `Word`), else `(ref $boxInt)` |
| `Real` | `f64` | `(ref $boxReal)` |
| `Bool`, `Char` | `i32` | `i31ref` |
| `Ok` | nothing | `i31ref` 0 |
| `String` | `(ref $string)` | the same |
| tuple of n components | `(ref $tupN)`, or `(ref $tup0)` if it may be a proxy (§5.11) | the same |
| record | two values: `(ref $recPayload)` and `(ref $dict)` | `(ref $recBox)` |
| variant | two values: `i32` tag and `eqref` payload | `(ref $varBox)` |
| option | `(ref $opt)` | the same |
| `Array(T)` | `(ref $arrayK)` for T's element kind K (§5.7), or `(ref $array)` when T's kind is not known statically | the same |
| function | `(ref $clos)`, or the subtype of its closure signature | the same |
| `auto`, exception, `Dynamic` | structs of their own | the same |
| descriptor | `(ref $desc)` | — |

### 5.2. Scalars and boxing

`Int` wraps at 64 bits (type-system.md §6.3.1), so `i31ref` cannot be its only word form. Boxing tests the range:
`ref.i31` silently keeps the low 31 bits, so the test is required for correctness, not only for speed. `is` on a type
parameter's values takes the descriptor (ir.md §9), so boxed scalars compare by value. `is` on a box is never
`ref.eq` alone. Specialization (`should_specialize`) should also trigger on scalar type arguments.

### 5.3. Tuples

`$tupN` is a struct of N `mut eqref` fields, for N from 0 to 32, declared `$tupN <: $tup(N-1)`, so that width
subtyping is a wasm upcast. Engines limit the chain to depth 63 (§3.2). A tuple of more than 32 components is a
`$tupBig <: $tup32`: 32 fields and a 33rd holding an `(array (mut eqref))` of the rest, at least as long as the
static type needs. Width subtyping among large tuples is then the array's length, and component i ≥ 32 is
`array.get` at i − 32. The figure 32 is a choice; anything up to 62 works.

### 5.4. Records

Width subtyping drops arbitrary fields, so a field's position is not static. The payload is an
`(array (mut eqref))` (`$recPayload`), with the layout descriptor at element 0 and the fields in name order after
it. `$dict` holds an `(array i32)` of indices and the stored types. `r.x` is two `array.get`s and an unbox. A record
is two wasm values, returned as two results, and is boxed in an immutable `$recBox` in a slot. The IR's `embedded`
boxes have no counterpart: objects do not nest.

### 5.5. Variants

A variant is an `i32` tag and an `eqref` payload, boxed in an immutable `$varBox` in a slot. Tag maps are
`(array i32)`s, as in C.

### 5.6. Options

`$opt` holds an `i32` tag, and `$optN <: $opt` adds N `mut eqref` fields. **A case without components is a constant
from the runtime:** the runtime module exports an array of `$opt` objects indexed by tag, built once, and every
module imports it. `is` never depends on that sharing. By extensions.md "Options as Values", two options of the same
component-less case are `is` each other at the type `is` is applied at, so `is` on options compares tags (and, for
a single-word type, components), with `ref.eq` only as a fast path. `is` therefore holds across modules either way.
Sharing makes the fast path hit, and saves each module from allocating its own constants. A proxy's tag is read
through the proxy (§5.11). Representing an all-constant option type as an `i31ref` is a later option.

### 5.7. Arrays (decision 6)

A Quest array is an `$array` struct, holding the identity hash (§5.12). One subtype per element kind holds the
store:

| Element type | Kind | Store |
|---|---|---|
| `Int`, `Word.T` | `I64` | `(array (mut i64))` |
| `Real` | `F64` | `(array (mut f64))` |
| `Bool`, `Char` | `I8` | `(array (mut i8))` |
| anything else, including `Ok` | `Eq` | `(array (mut eqref))` |

- **Native code** knows the kind from the static element type and uses `$arrayK` directly.
- **Generic code** (`Array(A)`) holds an `(ref $array)`. To read an element, it dispatches with `br_on_cast` on the
  four subtypes and boxes; to write, it dispatches and unboxes. When it makes an `Array(A)`, it takes the kind from
  A's descriptor. An abstract element type outside its module is generic code's case. Arrays are invariant, so an
  array's kind is fixed by its type wherever it is made.
- **The compiler's tables:** `Array(Int)` side tables and the `vector.T(word.T)` of hashes in `collections/hashmap`
  are `I64` stores, so a full-width hash is not boxed in the store. Generic `vector.get` still boxes it on the way out,
  a young-generation allocation per read, unless the call is specialized or inlined.
- **Why now:** typed arrays change every array access and the location of an array element (§5.10), so adding them
  later would be an ABI change that rebuilds every module. The `Array(Real)` probe (§3.1) and the boxing of
  full-width `Word`s argue for paying the dispatch in generic code from the start.

### 5.8. Strings

`$string`: a mutable hash, a mutable length, and a mutable reference to an `(array (mut i8))` whose length is the
capacity.

### 5.9. Closures

`$clos` (in the runtime's group, §5.16) holds the identity hash. For d descriptors and n value parameters,
`$closU(d,n) <: $clos` adds the uniform entry, of type `$u(d,n)`, a function of `(ref $clos)`, d `(ref $desc)`s, and
n `eqref`s, returning `eqref`. For each closure signature S (§5.9.1), `$closS <: $closU(d,n)` adds the native entry,
a `$fnS` taking `(ref $clos)` and S's parameters. A function's own closure struct, `$closF <: $closS`, final, adds
its captured variables. Each entry casts its first argument to its own `$closF`. Taking `(ref $clos)` rather than
itself keeps every function type out of recursion groups.

- **A native call site** of closure signature S does `br_on_cast $closS` and calls the native entry. On failure it
  boxes, calls the uniform entry, and unboxes.
- **A generic call site** knows its closure signature too, from its static type with type parameters as `eqref`, and
  does the same.
- **The uniform entry of a native function** unboxes, calls, and boxes. When S has no scalars, records, or variants,
  S is the uniform signature, and one function serves as both entries.

#### 5.9.1. The closure signature

The closure signature of a function type maps each parameter and the result as follows:

- `Int` and `Word` to `i64`;
- `Real` to `f64`;
- `Bool` and `Char` to `i32`;
- `Ok` to nothing;
- a record to `(ref $recPayload) (ref $dict)`;
- a variant to `i32 eqref`;
- a `var`/`out` parameter to `eqref i32`, a location (§5.10);
- **every other type to `eqref`:** strings, tuples, options, arrays, functions, abstract types, and type
  parameters.

Each quantifier adds a `(ref $desc)` before the value parameters. The callee casts a reference parameter to its
precise type when it uses it (§3.1: casts are cheap). Direct calls between known functions inside a unit may use
precise reference types.

Inside generic code, S is computed the same way, with the type parameters as `eqref`. So **a closure made for
`String -> Word` has S = `(eqref) -> i64`, the same S that generic code computes for `K -> Word`.** That closure is
called through its native entry from generic code, with no boxing of the `Word`.

**`hashMap(K V)`'s `hash: All(k: K) word.T` and `equal: All(k1: K k2: K) Bool`:**

- **K = `String`:** the caller's closures have S = `(eqref) -> i64` and `(eqref eqref) -> i32`, which are generic
  code's S. Every hash and equality call takes the native path: no allocation, no boxing.
- **K = `Int`:** the caller's closure for `Int -> Word` has S = `(i64) -> i64`, which is not generic code's
  `(eqref) -> i64`. At the polymorphic call `hashMap.new(:Int :V equal hash)`, the represent pass's `adapt` plan
  (ir.md §8.3) wraps it once in an adapter whose native entry has generic code's S. The adapter unboxes the `i31ref`
  key and calls the original. Each hash call then takes the native path through the adapter, and nothing is boxed
  (full-width hashes are `i64` results). An adapter is a new closure, so `is` does not hold between it and the
  original, as with C's adapters today.
- **Without the adapter** (a closure stored where no conversion ran, such as in an `Array` of closures), the cast
  fails and the uniform path boxes the result: correct, and slower.

### 5.10. Locations: `var` and `out` parameters, `@`

A location is two values: a container (`eqref`) and an `i32` index. The container is an `$array` (by kind), a record
payload, a tuple, a one-element cell for a local whose address is taken (`@x`, `var(e)`), or a module `var`'s box. A
read dispatches on the container with `br_on_cast`, in the order of the static element type's likely container.

**Neither the compiler nor the library passes a location at all.** A grep of `questlang/` and `lib/` for `@x` and
`var(e)` arguments finds them only in comments and diagnostics, as Fable's census (R8) also found. So locations
affect only users' programs, and their cost is not on the compiler's path.

### 5.11. Proxies

`$proxy <: $tup0`, final, holds the original, the stored and view descriptors, an option's tag map, and the cache.
Within a unit, a tuple type that may be proxied (`may_be_proxied`) is held as `(ref $tup0)`. A component read is
`br_on_cast $tupN` (or `$tupBig`), taking the proxy's path when the cast fails. A tuple type that cannot be proxied is
held as `(ref $tupN)`. At a unit's boundary both cross as `eqref` (decision 8, §5.16.3); the receiver casts to the
form its own type gives. A proxiable option is held as `(ref eq)`. The rules of c-representation.md §5.8 are
otherwise unchanged.

### 5.12. Identity and identity hashing

`is` is `ref.eq` after unproxying, and compares boxed scalars by value. `hash.identityHash` reads a lazily assigned
`i32` field present in every struct that can be hashed: tuples, options, closures, strings, the record box, the array
wrapper, and auto values. Arrays have no fields, which is the other reason for the wrapper (§5.7). Its cost in V8 is
nil (§3.1).

### 5.13. Descriptors

`$desc` is a struct hierarchy by kind. Closed descriptors are immutable globals with constant initializers, which
WASM-GC allows (`struct.new`, `array.new_fixed`). Cycles, and arrays past V8's 10,000 operands of `array.new_fixed`,
are built in a start function. That function is split into chunks, uses globals rather than locals (the 50,000-local
limit), and keeps each chunk well below V8's 7.6 MB function size, so that large modules' descriptors stay within
every limit (§8.4). Templates, view maps, `quest_is_subtype`, and the offset-table map are rewritten in Quest (§9).

### 5.14. Modules, globals, and initialization

A module's record is two mutable globals, payload and table, exported. Initialization is explicit, as in C: each unit
exports `init`, guarded by an `i32` global. Its first act is to call its imports' `init`s in the order of its import
list, then to run its own top level. A program's entry, or the loader for a phrase (§13), calls the root's `init`.

Functions that other modules import directly do not test the guard. An importer cannot call them before its own
`init` has run its imports' `init`s, since its own code runs only after that, exactly as C's direct calls of
`qv_<mod>_<fn>` rely on. Wasm `start` functions are not used for Quest initialization, because their order is the
order of instantiation, which would make output order depend on the loader. A start function only builds a module's
static descriptors and constants, which have no visible effects.

### 5.15. Exceptions

One tag, `$quest`, in the runtime module, imported by every module, carries the exception and its payload (two
`eqref`s).

- **`try` with `when` and `else` catches only `$quest`:** `try_table (catch $quest …)`, never `catch_all`.
- **A JavaScript exception from a host import** never reaches Quest code as such. The import shims (§9.2) catch
  JavaScript errors and return error results, which the runtime raises as the library's exceptions (`reader.error`,
  say) where the library's contract says it raises. Any other error is a host failure and ends the input (§10.5).
- **Another language's tag, or a JavaScript exception thrown through a callback,** passes through every Quest handler
  unseen, and reaches the host.
- **Quest has no `always` or `finally`** (the grammar has none), so nothing must run during foreign unwinding.

Re-raising is `throw` with the same pair, or `throw_ref` from `catch_ref`. Tracebacks: under a JavaScript host, an
import at a traced raise reads `new Error().stack`, which names wasm functions through the name section. Under
wasmtime there is nothing equivalent, so wasmtime's runs print no frames, an accepted difference.

### 5.16. Type identity

WASM-GC types are iso-recursive: a type is identified by its recursion group's structure and its index in the group.
Two modules' types are the same when their groups are structurally identical, and two types in one group are
distinct whenever their indices differ, even with identical fields.

#### 5.16.1. The runtime group

One recursion group, R, holds every type that code tells apart by a cast or a test, or that the runtime defines. It
is emitted identically, in one order, by every module, from one table in the backend. R contains:

- the boxes `$boxInt` and `$boxReal`;
- the tuples `$tup0`…`$tup32` and `$tupBig`, and `$proxy`;
- `$opt` and `$opt1`…`$optM`;
- `$string` and the four stores (`(array (mut i8))` and the others);
- `$array` and its four subtypes `$arrayEq`, `$arrayI64`, `$arrayF64`, and `$arrayI8`;
- `$recPayload` (an `(array (mut eqref))`, distinct from `$arrayEq`'s store by its index), `$dict`, `$recBox`, and
  `$varBox`;
- `$clos`, and the cell for locals;
- the exception, auto, and `Dynamic` structs;
- the descriptor hierarchy, view maps, and the proxy cache.

**What makes each pair of tested types distinct is its index in R**, not its fields, so adding or removing a field
later never makes two of them collide. Changing R changes every module's types. That is an ABI change, caught by the
wasm ABI version (§8.5), and it rebuilds every module.

#### 5.16.2. Types that stand alone

Each of these is in a group of its own (a singleton), and identified by structure:

- `$u(d,n)`, `$fnS`, `$closU(d,n)`, and `$closS`, which depend on the closure signature and refer only to types in R;
- each function's `$closF`;
- each function's own (non-closure) function type.

That identity is wanted. The cast to `$closS` at a call site must succeed across modules for a closure of the same
signature, and must fail for any other signature. A different S means a different field type, hence a different
type. Two functions whose `$closF`s have identical shapes get the same type, which is harmless: only a closure's own
entries cast to its `$closF`, and every closure's entries are its own. Leaf types are declared `final`, which lets V8
cast them with one comparison.

#### 5.16.3. Unit boundaries (decision 8)

An exported function's wasm signature is its **closure signature** (§5.9.1), computed from the interface's types
alone, which the exporter and every importer see alike. So abstract types, tuples (proxiable or not), options,
strings, and arrays all cross as `eqref`. The exporter's internal signature may be more precise, and its export is a
wrapper that casts. An abstract type whose representation is an `Int` crosses as `eqref` (boxed), as it is generic
outside its module, matching C's rule that a module's abstract types convert at its boundary.

### 5.17. Reference locals and nullability

Validation lets a local of non-null reference type be read only after a `local.set` in the same or an enclosing
block, earlier in the code. Initialization inside a block is forgotten when the block ends.

- **A join point's parameters** arrive as the results of the `block` the join point becomes, and are `local.set`
  just after it, at the join's own level. They can be non-null.
- **A variable assigned on both arms of an `if`** (a source `let var`, assigned in nested blocks) is declared
  nullable, `(ref null T)`, and read with `ref.as_non_null`, or with the cast that the read needs anyway, which checks
  for null too. A value that flows out of an `if` or `case` expression goes through a join point, so only true
  mutable variables are nullable.
- **An `out` parameter's target** is a container slot (§5.10). Slots are nullable `eqref`s, which allows
  `array.new_default` and `struct.new_default`. A cell for an uninitialized `let var` is made with a default value
  (`i31ref` 0, or 0 for scalar kinds), never null. No null ever reaches a Quest-visible read.
- **Cost:** a null check on reads of nullable locals, which V8 mostly folds into the following access through its
  trap handler. A wrong guess by the compiler is a trap, a compiler bug (§7). The printer must also reuse wasm locals
  by type and liveness, because the limit is 50,000 per function (§3.2) and large initializers would otherwise
  exceed it.

### 5.18. `Int` where wasm wants `i32`

Array and string lengths and indices are `i32`s in wasm, but `Int` in Quest.

- **Indices:** the bounds test is done in `i64`. It tests the index, unsigned, against the length extended to `i64`,
  so negative and huge indices raise `array.error` (or `string.error`) as now, before `i32.wrap_i64`.
- **Lengths** are extended to `i64` when read.
- **Allocation counts:** a negative count raises `array.error`, as now. A count above the engine's maximum (about
  1 GiB of payload in V8, §3.2) would make `array.new` trap. The runtime therefore tests the count against the
  target's maximum first, and reports a fatal out-of-memory error with a message, as native code does when an
  allocation fails, rather than an uncatchable trap. Strings and the stores of typed arrays are capped the same way:
  a string's byte length is at most about 1 GiB.

---

## 6. Polymorphism

### 6.1. What carries over

The C design's central property is that a native aggregate and a generic aggregate are laid out alike
(runtime-design.md §2.2). That property holds for tuples, records, options, and variants, whose slots are all
`eqref`s. For arrays it holds through the kind dispatch of §5.7. So unbounded quantifiers (descriptor parameters,
`eqref` values, aggregates by cast) carry over, as do bounded quantifiers (own views, view maps), existentials, opaque
higher-kinded parameters, `auto`/`inspect`/`Dynamic`, and polymorphic recursion.

### 6.2. What changes

- **`box`/`unbox` are real** (§5.2), including in monomorphic code storing `Int`s into tuples.
- **Closures never need layout conversion** for correctness (§5.9). `adapt` remains as an optimization at
  polymorphic calls (§5.9.1) and for view changes.
- **Arrays over type parameters dispatch on kind** (§5.7).
- **Polymorphic `var` parameters** receive a location whatever their type (§5.10); there are no shadow cells.
- **Specialization** also triggers on scalar type arguments.

### 6.3. Records under polymorphism

As in C, a record is two values natively and one boxed word in a slot. `stored_types` remains for depth subtyping
and bounded parameters, but is not needed for scalars.

### 6.4. Alternatives for the word

- **(a) Uniform `eqref`** (chosen, decision 4).
- **(b) Two-value words, `(i64, eqref)`:** no boxing, but slots twice as wide and generic code no faster (§3.1).
- **(c) Typed slots with descriptor dispatch:** infeasible for tuples (3^n shapes per arity). It is adopted for
  arrays alone (decision 6).

### 6.5. Tail calls

Quest does not guarantee tail calls: arm64 makes them "whenever possible, not as a guarantee of the language"
(arm64.md §1), and clang may or may not. Wasm's `return_call` and `return_call_ref` *are* guaranteed. So the wasm
backend emits them wherever the IR has a call in tail position, and every direct call and every native-entry call in
tail position stays a tail call.

Calls that are tail calls natively stop being tail calls when something must happen after the callee returns:

- **a native function's uniform entry, when its result is a scalar, record, or variant:** the wrapper calls the native
  entry, then boxes. When the result is a reference, the wrapper `return_call`s;
- **the uniform fallback at a call site whose own result is native** (box arguments, call, unbox the result);
- **an adapter whose result converts** (a record's view, a variant's tags);
- **a call inside a `try`**, as natively.

**A loop written through closures** stays a constant-stack loop when its calls are native-to-native (direct, or
native entries of the same closure signature) or generic-to-generic through uniform entries with reference results.
It grows the stack by one frame per iteration when the cycle passes through a native function reached through its
uniform entry and returning a scalar: generic code tail-calling a closure `Int -> Int` that tail-calls back into
generic code, say. Natively, on arm64, such a cycle is a tail call, because a `QVal` `Int` needs no conversion. At
about 512 KB to 1 MB of stack and wrapper frames of a few dozen bytes, such a loop overflows after some 10,000
iterations in a browser. This is a wasm-specific regression, rare in practice: the compiler and the library do not
loop through closures this way, to my knowledge. It is documented as an accepted difference, and specialization
removes it where it applies.

---

## 7. Traps

No wasm handler catches a trap (§3.2), so every operation that Quest defines to raise is tested before the instruction
that would trap (decision 10).

| Instruction that traps | When | Quest today | On wasm |
|---|---|---|---|
| `i64.div_s`, `i64.rem_s` | divisor 0 | `int.error` (catchable) | tested first; raises `int.error` |
| `i64.div_s` | `minInt / -1` | wraps to `minInt`; `%` gives 0 (type-system.md §6.3.1) | tested first, as the SSA's builder does; wraps |
| `i64.div_u`, `i64.rem_u` | divisor 0 | `word.error` | tested first; raises `word.error` |
| `i64.trunc_f64_s` | NaN, infinity, out of `Int`'s range | `real.error` from `real.floor`/`round`; NaN cannot occur | range tested first; raises `real.error` |
| `array.get`, `array.set` | index out of bounds | `array.error`; strings: `string.error` | tested in `i64` first (§5.18); raises |
| `array.new` | count too large for the engine | negative: `array.error`; too large for memory: fatal out of memory | negative raises; past the target's maximum, a fatal error before the trap (§5.18) |
| `array.copy`, `array.fill`, `array.init_data` | range out of bounds | the runtime's operations raise | the runtime's operations test first |
| `ref.cast`, `ref.as_non_null`, `struct.get` on null, `call_ref` on null | a failed cast, a null | cannot happen | emitted only where the types guarantee success; a trap is a compiler bug |
| `unreachable` | after a call that cannot return | cannot happen | a trap is a compiler bug |
| linear-memory loads and stores (the staging area, §9.3) | out of bounds | — | the runtime's own code; a trap is a runtime bug |
| (none: the engine) | stack exhausted | compiled code: fatal, uncatchable; interpreters: `stack.overflow` at 1,000 calls (exceptions.md §6) | a trap or `RangeError`, uncatchable by wasm; the host handles it (§10.5) |
| (none: the engine) | memory exhausted | fatal | the engine traps or, in a browser, may kill the page; the host reports it |

Arithmetic otherwise cannot trap: `i64` wraps as Quest's `Int` does, the saturating conversions are never needed, and
`f64` arithmetic follows IEEE with Quest's NaN tests in front (type-system.md §6.3.2). A trap that the table calls a
bug ends the run with a message naming it as an internal error, so that a failing test is not mistaken for a Quest
exception.

---

## 8. Units, linking, and artifacts

### 8.1. A module per unit

Each unit exports its record globals, its functions (as closure-signature wrappers, §5.16.3), its dictionaries, its
`init`, and its fingerprint (§8.5). It imports the runtime module, the host interface, and its imports' exports, by
unit name. wasmtime links with `--preload`; node and the page link with a small JavaScript loader.

### 8.2. The driver as the library, against whole-program optimization

The JIT's rule (jit.md §1) is that an input naming `writer` or a `questlang/...` module reaches the driver's own
copy, its code and its state.

- **As a module per unit** (recommended). An input imports a member exactly as a unit imports it: the exported
  wrapper, or the record's field. What is given up is inlining across units, by the compiler (which does not inline
  across separately compiled units today either) and, as far as I know, by V8, which does not inline through imports
  from another instance. That should be measured at step S. About 250 instantiations at startup cost about 10 µs
  each (§3.1).
- **As one optimized module.** Two kinds of whole-program optimization must be told apart:
  - **The IR's `--whole-program`** (ir.md §8.6) sees through abstract types to their representations, so a whole
    driver lays out an abstract type's values natively where a separately compiled input expects the generic layout.
    An input would then disagree with the driver at every abstract type. **Not compatible with the driver as the
    library**, unless every interface member is also exported through a wrapper that converts to the separate
    layout, which would undo the point.
  - **Merging the per-unit modules at the wasm level** (binaryen's `wasm-merge`, then `wasm-opt`) keeps every export,
    since exports are roots. An inlined or specialized function stays exported in its generic form, because inputs
    call that form and never a clone. Removal can only take what no export reaches, which an input could not have
    named. This is compatible, and is an optimization to measure once the per-unit build works.

### 8.3. Interfaces

`.qi` stays as it is. No `.int.h` is written for wasm. An importer's view of an export comes from the interface and
the closure-signature rule.

### 8.4. Limits

The encodings that could reach an engine limit (§3.2), and what keeps each one under:

| Encoding | Limit | Reachable by | Kept under by |
|---|---|---|---|
| the tuple chain `$tupN <: $tup(N-1)` | depth 63 | a tuple of 64 or more components, which is legal | the chain stops at 32; `$tupBig` holds the rest in an array (§5.3) |
| `$optN` fields, `$closF` captures | 10,000 fields | an option case or a closure with 10,000 components | not by real code; the backend refuses above it with a diagnostic |
| a closure struct per function | 1,000,000 types per module | not by the compiler (thousands of functions per unit) | — |
| descriptors and constants built by a start function | 7.6 MB per function body; 50,000 locals | the driver's largest units, the generated `codegen/externals` | chunked start functions over globals (§5.13) |
| string literals and constant arrays | 10,000 operands of `array.new_fixed` in V8 | any literal longer than 10,000 bytes; the parser's and the externals' tables | `array.new_data` from data segments and `array.new_elem` from element segments, never `array.new_fixed` past a small size |
| parameters and results | 1,000 each | a function of more than about 1,000 value and descriptor parameters, records counting twice | not by real code; refused with a diagnostic |
| locals | 50,000 per function | a large initializer with one local per binding | locals reused by type and liveness (§5.17) |
| exports | 100,000 per module | a merged driver that exports every member (§8.2) | the driver's interfaces have far fewer members; to be counted at step S |

### 8.5. Artifacts and caches per target

Today, `.qi`, `.qm`, and generated headers record the ABI version (`config/abi`), one number shared by the bootstrap
and by the C, ssac, and arm64 backends, whose objects link together. The `.qm` records the backend, and a unit that
the build assigns to another backend is stale (build-process.md §5.2). The JIT's fingerprint digests the ABI version
and the interface's elaborated form (jit.md §3.3.1). None of that knows about a target whose objects cannot link
with the others.

- **`.qi` is target-independent** (types, as elaborated) and keeps the shared version, so one `.qi` serves every
  target.
- **A wasm ABI version**, `wasmAbiVersion` in `config/abi`, covers what only wasm code depends on: R's types and order
  (§5.16.1), the closure-signature rule, the runtime module's imports, and the host interface. Every wasm module
  records the shared and the wasm version, and the target, in a custom section (`quest-abi`). The `.qm` of a wasm
  unit records `"backend": "wasm"` and the wasm version.
- **Build directories** keep wasm apart, in `.build/wasm/`, as `./quest` keeps another backend's stages in
  `.build/quest-stages-BACKEND`. Native backends share a directory because they link together; wasm never links with
  them.
- **The fingerprint** for wasm digests the target and both versions, as well as what it digests today. A native host's
  fingerprint and a wasm host's therefore never match.
- **What stops an artifact of one target being used by another:** the `.qm`'s backend check (stale, so rebuilt); the
  loader's check of the `quest-abi` section (refused); the fingerprint (refused); and, last, wasm instantiation itself,
  which fails when an import's signature does not match. `--unit-backend` refuses to mix wasm with native backends.

---

## 9. The runtime

### 9.1. In Quest, over intrinsics

The runtime is a module of unsound primitives (the `os/value` scheme, jit.md §3.11), compiled by the wasm backend to
single instructions: casts and tests, struct and array access by index, boxes, `ref.eq`, `i31` operations, and the
byte stores. The runtime's logic is written in Quest on top: conversions, proxies, runtime subtyping, descriptor
instantiation, view maps, record tables, value printing, `dynamic`, strings, and real formatting and parsing.

### 9.2. The library's externals

`lib/` names **182 distinct external strings** (a regular expression over `lib/`, counting distinct quoted strings):

- **174 values:** 151 C functions (`quest_…`), 9 constants (`QUEST_REAL_PI`, `QUEST_INT_MAX`, …), and 14
  exceptions' addresses (`(&quest_exc_real_error)`, …);
- **8 types:** `uint64_t`, `QWriter *`, and the like.

The earlier "about 150" was a miscount; Fable's 161 matches none of these categories exactly (functions and constants
together are 160). **The compiler uses all 174 values:** it links 32 of `lib/`'s 34 units, and the two it does not
link, `io/display` and `util/bignum`, have no externals.

Each external maps to an intrinsic, a runtime function, or a host import. A table plays the part of
`codegen/externals`, and a test checks that it covers `lib/`. In the page, `os/process`, `os/code`, `io/readline`, and
`os/filestats`' writes have no meaning. Their externals raise the module's error, or are host stubs, and the driver
does not call them on the paths the page uses (§12).

**Real numbers** are a hard part. `conv.real` prints the shortest round-tripping digits, and the lexer and `conv`
parse literals, so the wasm runtime needs a correct `strtod` and digit generation, in Quest (`bignum` helps). `sin`,
`exp`, `log`, `pow` and the others are not wasm instructions. A port and JavaScript's `Math` can differ from Apple's
libm in the last bit, which 17 digits show. Goldens with transcendental results are shared or recorded per target, an
owner's question (§15).

### 9.3. The host interface, and bytes across it

JavaScript cannot read or write a GC array or struct, except one element per exported call (14–23 ms for 3.4 MB,
§3.2). WASI preview 1 takes buffers in a linear memory. So the runtime module has a small linear memory, the
**staging area**, and the host interface moves bytes only through it:

| Bytes | Wasm to host | Host to wasm |
|---|---|---|
| text written (`writer`) | the runtime copies the GC byte array into the staging area and calls `write(fd, ptr, len)`; the page decodes it as UTF-8 (`TextDecoder` on the memory), WASI's `fd_write` takes it as is | — |
| text read (a line, `reader`) | — | the host writes UTF-8 into the staging area (JavaScript's `TextEncoder.encodeInto`; WASI's `fd_read`) and returns the length; the runtime copies it into a new GC byte array |
| a file's contents | as text written, in chunks of the staging area's size, to the page's virtual file system or WASI's `fd_write` | as text read, in chunks, from the virtual file system or WASI's `path_open`/`fd_read` |
| a JIT module's bytes | the compiler's GC byte array is copied into the staging area, grown to fit; the page passes a slice of the memory's buffer to `new WebAssembly.Module` | — |

The staging area grows with `memory.grow` to fit the largest transfer, or transfers are chunked. **What it costs the
compiler to read its own sources:** 3.4 MB in about 2 ms warm each way (§3.2), once per build, negligible against
compilation.

---

## 10. The stack

### 10.1. What the browser gives

About 1 MB on a page's thread, about 512 KB in a Chromium worker, and about 1 MB on a JSPI stack, in a worker or not
(§3.2). A page cannot change any of these. Core stack switching is experimental in V8 and unavailable in wasmtime
here. node's workers have 4 MB, so tests under node must constrain the stack (`--stack-size`, or worker
`resourceLimits`) to the browser's, or they will pass where the browser fails.

### 10.2. The compiler

Natively, the compiler compiles its largest source in at most 64 KB and its driver's `main.quest` in about 160 KB
(§3.2). Its recursion grows with the nesting of the input: 0.9 KB per level of a chain of infix operators, so a
3,000-term chain needs 2.6 MB. If wasm frames are about the size of arm64's, which must be measured at step S, the
compiler fits a browser's stack for its own sources with a margin of three to six times. It fails on generated or
pathological inputs nested a few hundred to a thousand levels deep.

### 10.3. The interpreter

Natively, about 6.2 KB per interpreted call of a function whose body nests calls (§3.2). Under the same assumption
about frame sizes, the interpreter's limit of 1,000 calls needs about 6 MB, and the browser gives about 80 calls in a
Chromium worker and about 160 on the page's thread or a JSPI stack. **Interpreter-first (decision 1) and a 1,000-call
interpreter in a page are incompatible**, unless the interpreter changes.

### 10.4. The policy for the interpreter in a page (decision 14, open)

The choice is the owner's. Measuring first: at step B1, the driver compiled to wasm interprets the recursion probe
under node with the stack constrained to 512 KB and to 984 KB. That gives the wasm bytes per interpreted call, which
the native figure only estimates. Then:

1. **Make each interpreted call nest fewer host frames,** by targeted changes to the evaluator: evaluate a call's
   arguments without a frame per subexpression, and give `if` and `begin` no frame of their own. This might gain a
   factor of two or three; it does not reach 1,000.
2. **Run the driver on the page's thread** (1 MB, twice the worker's). That gives up the worker (decision 12): the
   page is unresponsive while an input runs, and synchronous compilation on the main thread is limited in Chrome.
   **Or a worker on a JSPI stack:** also 1 MB, and the worker is kept. Both double the depth.
3. **Make interpreted calls not nest host frames at all:** an evaluator whose Quest-level calls are on a heap stack
   (an explicit continuation, a CEK machine). The depth is then bounded by memory, but it is a rewrite of the
   self-hosted interpreter, and slower.
4. **A lower limit in the page,** fixed (not measured at run time, so that output is deterministic), say 100 calls.
   This is a difference from every other implementation that recursive programs over lists of a few hundred elements
   would show.
5. **Bring the JIT forward:** compiled code needs a frame of tens of bytes per call, not kilobytes, so about 10,000
   calls fit in 1 MB.

My recommendation: measure at B1; take 1 and 2 (JSPI in a worker) at once; and if the depth is still below about 500,
ask the owner to choose between 3 and 5 rather than accept 4.

### 10.5. When the host sees the overflow

No wasm handler sees an overflow, so the Quest code that recovers from a failed input (the REPL's rollback, written
with `try`) does not run. Under node and in the page, JavaScript catches the `RangeError` at the `evaluate` call, and
what it does depends on what was running:

- **Running an input's compiled code (stage C):** the compiler had finished, and the session's state changes only when
  the input commits (jit.md §3.2). JavaScript calls the driver's `abandonInput()` export, which forgets the input as a
  raise would, and the session continues. A store the input made to an earlier `var` stays, as with a raise today.
  This is better than native, where the session ends (jit.md §1).
- **Compiling or interpreting (stages B and C):** the compiler's or interpreter's own structures may be half updated,
  and no Quest cleanup ran. JavaScript discards the worker, starts a new one, replays the session's committed inputs
  with output suppressed, and reports `stack overflow; the session was restored` for the failed input. Replay assumes
  that inputs are deterministic. An input that read the clock or a file that changed since may differ; the virtual
  file system is the page's and survives the worker. If replay fails, the session is lost, and the page says so.
- **Under wasmtime** (the test suite, programs): the trap ends the run, as compiled code's overflow ends it natively
  (exceptions.md §6). The test runner maps wasmtime's "call stack exhausted" to the native output's
  `Exception: stack.overflow`, without frames.

The compiler's own overflow on pathological inputs (§10.2) is handled the same way. A later refinement is a nesting
limit in the parser that reports a diagnostic before the host's stack runs out.

---

## 11. What the page serves

The owner's answer in Fable's plan (§11, answer 8) applies to both: in the page, a URL prefix behaves as a
`QUEST_PATH` directory from which modules are loaded as source.

| Files | Stage B (interpreting) | Stage C (JIT) | Produced by, for which target |
|---|---|---|---|
| the driver's modules: every unit of `questlang/` and the 32 `lib/` units it links, and the runtime module, as `.wasm` | needed: the interpreter's builtins call the driver's compiled library (interpreter.md, "Builtins") | needed: they are also the library inputs import (§8.2) | the native compiler's wasm backend (step S), target wasm |
| `lib/*.int.quest` | needed: the interpreter elaborates every interface it imports | needed: inputs are typed against them | source |
| `lib/*.mod.quest` | needed: the interpreter runs library modules from source, with externals bound to the driver's compiled library | not needed for the library, whose compiled copies are the driver's; kept for `--no-jit` | source |
| `.qi` | optional: elaborating interfaces from source in the page costs about 10 ms per program (jit.md §3.4.1); a prebuilt set saves it | optional, as in B: the JIT keeps `.qi` in memory and can make them in the page | any build; target-independent (§8.5) |
| fingerprints | — | embedded in each driver module (§8.1), compared with the page's elaboration of each interface | the wasm build |
| the user's modules | as source, from the URL prefix | as source, compiled in the page | the user |
| `.qm`, `.int.h`, objects, the C runtime | never | never | — |

---

## 12. The REPL in a page (stage B)

- **A Web Worker** runs the driver (decision 12), subject to §10.4. It exports `evaluate(input)`, which returns when
  the input has run, and `abandonInput()` (§10.5). The REPL's multi-line heuristics (repl.md §3.2) move to the caller,
  or `evaluate` answers "incomplete".
- **Line editing** is the page's. `lib/io/readline` is not used.
- **Files:** a virtual file system in JavaScript, holding `lib/` (fetched from the URL prefix) and the user's files.
- **Interrupts:** a running wasm call cannot be interrupted, only its worker terminated. With replay (§10.5),
  terminating the worker and replaying keeps the session. Polling a `SharedArrayBuffer` flag would avoid the replay,
  but needs cross-origin isolation headers (§15).

---

## 13. The JIT (stage C)

- **An input is a module** (`qj_<n>`), exporting its record. The loader passes it the earlier inputs' records it
  imports, and the driver's modules' exports.
- **Slots are boxes** (jit.md §3.2), `$tup1`s, so redefinition in place needs nothing new.
- **A failed input** is not committed; its instance stays unused.
- **Compiling in the page** needs the backend inside the driver, compiled by itself (step S). Instantiation costs
  about 10 µs for a small module (§3.1), so the compiler sets the latency.
- **Bytes** cross as in §9.3.
- **The fingerprint** check carries over, with the target in it (§8.5).

---

## 14. Steps

Each step has a condition for being done. Costs are recorded as actuals, not estimated.

**Step 1: probes.** Done 2026-11-12 (§3), except Safari.

### 14.1. Stage A: programs

Stage A is mostly the work, so it is split by what can be tested at each point. Each step's tests run under wasmtime
and node, and each step adds the language tests it covers to a list (`tests/wasm/<step>.txt`) that later steps keep
passing.

- **A1. The target parameter and the wasm represented stage.** `codegen/layout` takes a target; `--backend wasm`
  runs through `ir_described`. *Done when* the IR verifier passes (`QUEST_CHECK_IR=1`) for the IR corpus under the
  wasm target, its represented-stage goldens are recorded, and the C target's goldens are unchanged.
- **A2. The encoder, the WAT printer, and R.** *Done when*, for a corpus of hand-written and generated modules, the
  encoder's bytes equal `wasm-tools parse` of the printed WAT, and every module validates under `wasm-tools validate`.
- **A3. A monomorphic subset:**
  - `Int`, `Bool`, `Char`, and string literals (from data segments), tuples, options, control flow (join points,
    loops, `switch`), and direct calls;
  - native closures (both entries) and exceptions (`$quest`);
  - the traps' tests (§7);
  - a runtime of a few functions: write a string, write an `Int`, exit;
  - the WASI and JavaScript hosts for those.

  *Done when* the first list of language tests, the hello-world-sized `examples/`, and tests of every row of §7 pass.
- **A4. Records, variants, typed arrays, locations, and the string operations.** *Done when* the second list passes,
  including the aggregate and `var`/`out` tests.
- **A5. Polymorphism:**
  - descriptors (static, templates, start functions within §8.4's limits);
  - uniform entries, boxing, the closure-signature rule, and adapters;
  - view maps, proxies, and specialization on scalar arguments;
  - the generic array dispatch.

  *Done when* the conversion matrix (`tests/conversions`), `language/view_proxies`, and the polymorphism tests pass.
- **A6. The runtime in Quest:**
  - `quest_convert` and runtime subtyping;
  - printing and echo;
  - `dynamic.extern` and `intern`;
  - real formatting and parsing, and the transcendental functions.

  *Done when* the echo, dynamic, and real goldens pass byte for byte, except any transcendental results that the owner
  allows to differ.
- **A7. The library and linking:**
  - all 174 externals mapped, with the coverage test;
  - the library built as per-unit modules;
  - multi-module programs, with `--preload` and the JavaScript loader;
  - the wasm ABI version and artifacts (§8.5).

  *Done when* the module tests pass and the coverage test is green.
- **A8. Stage A complete.** *Done when* the behavior suite passes on both engines except a written list of accepted
  differences (tracebacks under wasmtime, §5.15; tail calls through uniform entries, §6.5; transcendental reals if
  allowed), and the benchmarks have run once at scale for a baseline.

### 14.2. Step S: the compiler compiles itself, outside a browser

The owner's first milestone in Fable's record (decision 1). This is where the backend, compiled by itself, is first
tested.

- **S1.** The driver, compiled to wasm by the native driver, runs under node with the stack constrained to 984 KB
  (§10.1). It compiles the test corpus with `--backend wasm`. *Done when* its output (wasm modules and IR goldens) is
  byte-identical to the native driver's for the whole corpus.
- **S2.** The wasm driver compiles the driver itself to wasm. *Done when* that output is byte-identical to what the
  native driver produced for the same source: a fixed point, which tests the wasm-hosted backend against the native
  one. Measured at S: the compiler's stack depth in wasm on its own sources, and the cost of per-unit modules (§8.2).

### 14.3. Stage B: the interpreter in a page

- **B1.** Measure the interpreter's wasm stack per call (§10.4) under node. The owner chooses the policy.
- **B2.** The JavaScript host's file system (the URL prefix), `evaluate` and `abandonInput`, the worker, replay
  (§10.5), and the page. *Done when* the interpreter's REPL transcripts pass under node against the wasm driver (with
  the policy's accepted differences), and the REPL works by hand in Chrome.

### 14.4. Stage C: the JIT

- **C1.** The loader, per-input modules, and fingerprints with the target. *Done when* the JIT's transcripts pass
  under node against the wasm driver, and by hand in Chrome.

---

## 15. Questions for the owner

1. ~~Interpreter before the JIT?~~ *Answered: yes* (decision 1). Step S placed before B to agree with Fable's record.
2. ~~`wasm-tools`?~~ *Installed.* May binaryen also be installed, to measure merging and `wasm-opt` (§8.2)?
3. **The interpreter's stack in a page (§10.4):** after measuring at B1, which of the options, if 1 and 2 are not
   enough: a heap-stack interpreter, the JIT sooner, or a lower limit?
4. **Which browsers must work?** Chrome alone is measured. Safari's support for GC, `exnref`, tail calls, and JSPI is
   untested.
5. **Accepted differences:**
   - no tracebacks under wasmtime;
   - tail calls through uniform entries (§6.5);
   - transcendental `Real` results that differ in the last bit, or goldens per target;
   - an interrupt that replays the session.
6. **Performance target:** a REPL (startup, latency per input), or also the benchmarks?
7. **Hosting:** will the page be served with cross-origin isolation headers (for `SharedArrayBuffer`: interrupts
   without replay, a blocking read)?

---

## 16. The review's questions, and where they are answered

Questions that apply across the plans:

1. Traps: §7.
2. Tail calls through what stands between caller and callee: §6.5.
3. The stack: §3.2 (measurements), §10.2 (the compiler), §10.5 (the host sees it).
4. Engine limits: §3.2, §8.4.
5. Type identity across modules: §5.16.
6. Reference locals: §5.17.
7. `Int` where wasm wants `i32`: §5.18.
8. Bytes across the host boundary: §9.3.
9. What the page serves: §11.
10. The driver as the library against whole-program optimization: §8.2.
11. Artifacts and caches per target: §8.5.

Questions about this plan:

1. What a native signature is, and `hashMap`: §5.9.1.
2. Where the self-compiled backend is first tested: §14.2.
3. Boxed arrays first: replaced by typed arrays from the start (decision 6, §5.7).
4. The static type of tuples that may and may not be proxied, at a boundary: §5.11, §5.16.3.
5. `else` as `catch_all_ref`: replaced; `else` catches only `$quest` (§5.15).
6. Constant option cases: shared through the runtime, and `is` holds across modules either way (§5.6).
7. Who calls an initializer when functions are imported directly: §5.14.
8. Which measurement chooses the stack policy, and the state of stack switching: §10.4, §3.2.
9. Steps with conditions, and the order inside stage A: §14.
10. The count of externals: §9.2.
11. The two plans' records of the owner's answers: decision 1.
