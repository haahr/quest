# The Four WebAssembly Plans Compared

Four plans were written on 2026-11-12 for the same goal: the self-hosted REPL in a browser, on WebAssembly's garbage
collection (WasmGC), with a JIT that compiles each interaction to a module. This document compares them, says what
is wrong in each, and lists the issues that some or all of them miss. The comments for each plan's author, as
questions without answers, are in [wasm-plans-comments.md](wasm-plans-comments.md).

| Plan | File | Where |
|---|---|---|
| Fable | [wasm-plan-fable.md](wasm-plan-fable.md) | `main` |
| Opus | [wasm-plan-opus.md](wasm-plan-opus.md) | `main` |
| Hydrogen | `docs/wasm-plan-hydrogen.md` | branch `worktree-wasm-hydrogen` only |
| Argon | `docs/wasm-plan-argon.md` | branch `worktree-wasm-plan-argon` only |

**Summary.** Fable and Opus are the two to build from. Both measured, both keep the current design's shape (native
representations where a type is known, one uniform representation elsewhere), and each covers the other's gaps:
Fable is stronger on the compiler, Opus on evidence and on the browser. Hydrogen and Argon each contain errors that
would not survive the first polymorphic test, though Argon has one idea worth keeping (§2.4).

Claims below marked *checked* were checked against the tree at d4cdd6ef. Engine behavior not measured by a plan is
from memory and is marked so.

---

## 1. How They Differ

| | Fable | Opus | Hydrogen | Argon |
|---|---|---|---|---|
| Uniform word | `eqref`; `Int` is an `i31` or a box | the same | `anyref`; `Int` always boxed | `eqref`; `Int` always boxed |
| Tuples | a struct per arity with a header, a subtype chain | a struct per arity, a subtype chain | typed structs or arrays, depending on use | a struct holding a slot array |
| Arrays | by element class (`i64`, `f64`, `i8`, `eqref`) | `eqref` in a wrapper struct; typed later | a bare `anyref` array | a struct holding a slot array |
| Records | array payload and index table | the same | struct of descriptor and array, and index table | the same as Hydrogen |
| Closures | native and uniform entries; an unknown call always uniform | both entries; native tried first by a cast | one typed entry, C's adapters | one `(ref func)`, cast at the call |
| `var`/`out` locations | (container, index), dispatching | the same; tuples through a helper | a `$QRef` object allocated per `@` | (slot array, index), no dispatch |
| Identity hash | a counter in the header; arrays unresolved | a hash field; arrays wrapped | no design | no design |
| `Real` printing and math | in Quest, named a hard part | in Quest, named a hard part | not mentioned | host imports |
| Tracebacks | the raise site only | JavaScript's stack; none in wasmtime | a shadow stack, deferred | the host's stack capture |
| Runtime | Quest over intrinsics | Quest over intrinsics | Quest | WAT or Quest |
| Units | a module per unit | a module per unit | unclear | per unit, and a linker of its own |
| Output | text and binary | binary, with a WAT printer | binary | binary, with a WAT printer |
| First milestone | self-compilation in wasmtime | the interpreter's REPL in a page | the interpreter's REPL | the suite, then self-compilation and the JIT |
| Measured | location costs, linking, allocation | 15 probes in V8 and wasmtime, stack depths | nothing | nothing |
| Owner's answers | recorded (§11) | partly recorded (§12) | decisions listed, source not said | decisions listed, source not said |

---

## 2. Each Plan

### 2.1. Fable

Strongest on the compiler's side: where the backend forks, a unit as a module from the first step, a census of what
the compiler uses before anything is ported, and a byte-identical fixed point as the first milestone. Its steps
have done-when conditions.

- **Every unknown call goes through the uniform entry.** Opus measured that at about ten times a native `call_ref`
  in V8 (322 ms against 31 ms for 100 million calls), and the cast that avoids it at nothing measurable.
- **Milestone 1 runs only in wasmtime,** which Opus measured at about 8 ns per `call_ref` against V8's 0.3 ns. The
  self-compilation will be slowest on the engine that matters least, with the closure rule above making it worse.
- **"Whether wasmtime's default collector reclaims cycles" is left open.** Opus answered it: it does not (1.6 GB
  against 15 MB under `copying`).
- **No interrupts,** and the stack's depth is one line among the risks.
- **A whole-program module for the page** is planned beside "the driver is the library" without saying how an
  input's module finds functions that inlining and specialization removed.

### 2.2. Opus

Strongest on evidence and on the browser: a worker's stack of about 512 KB, stack overflow that no wasm handler
catches, interrupts, cross-origin isolation, instantiation latency.

- **No self-compilation step.** The compiler compiled to WebAssembly is tested only through REPL transcripts until
  the JIT needs the backend to run in the page.
- **Boxed arrays first** fits this compiler badly: its side tables are `Array(Int)` and its hashes full-width
  `Word`s (Fable's observation, R5).
- **How fine a native signature is, is not said.** If `String` is `(ref $string)` in it, a `String -> Word` hash
  function given to `hashMap(K V)` fails the cast at the generic call site, whose static signature has an `eqref`
  there, and takes the uniform path, boxing a `Word` per call.
- **`else` as `catch_all_ref`** also catches a host's exception thrown through an import.
- **Steps are six coarse stages** with no done-when conditions.

### 2.3. Hydrogen

- **The closure design is C's,** with adapters "identical to C". An `i64` and a reference never agree as a word and
  an integer do, so nearly every function value that crosses into generic code would need an adapter, and the
  conversions C rejects would be common.
- **Tuples have two layouts,** chosen by whether a tuple is "monomorphic and never proxied", which separate
  compilation cannot prove.
- **A `var` argument allocates** an object at each `@`.
- **Tail calls are said to come from `ssa/tailCalls`** while the backend lowers from the IR.
- **Compiling a JIT module is called "naturally async".** In a worker it is synchronous at any size (Opus measured
  10 µs).
- **Nothing** on `Real`, identity hashing, `is` on boxed integers, or the stack's depth.

### 2.4. Argon

- **Variant tags are not hashes of labels.** They are in the type's numbering and remapped by tag maps
  (c-representation.md, "tagmap", *checked*), so "variant width subtyping is identity" is wrong.
- **Exceptions are keyed by a hash of a name.** They are generative: each evaluation makes a new identity
  (c-representation.md, "generates a new unique exception value", *checked*).
- **"`ir/represent` already marks every boundary" is false.** An `Int` in a tuple's slot needs no conversion today,
  so the pass inserts none; it asks `layout.genericLayoutAgrees` (*checked*).
- **`Real` formatting, the mathematical functions, and stack capture are host imports** "at full parity under
  wasmtime", whose command line supplies no imports but WASI's.
- **Every tuple, option, and array is two allocations** and two loads, not measured.
- **A linker of its own** for single-module binaries, where wasmtime's `--preload` already links (checked by Fable
  and Opus).
- **The idea worth keeping:** with every slot in one array type, every location is a (slot array, index) pair and
  nothing dispatches. But the compiler and library pass no `var` or `out` argument at all (Fable's count), so the
  design pays on the commonest aggregate for the rarest feature.

---

## 3. Issues None of the Four Raises

1. **Traps are not exceptions.** `i64.div_s` traps on zero and on the least integer divided by -1, `array.get` on
   bounds, `i64.trunc_f64_s` on NaN and out of range, `ref.cast` on failure, and an access through null. No wasm
   handler catches a trap. Quest's `int.error` and bounds errors are ordinary exceptions (exceptions.md, *checked*).
2. **The uniform entry and tail calls.** A wrapper that boxes its result cannot `return_call`, nor can a caller that
   unboxes one. Loops driven through closures with `Int`, `Real`, or record results grow the stack, which in a
   Chromium worker is about 512 KB.
3. **Subtype chains have a depth limit:** engines need support only 63 levels (from memory). The largest tuple in
   the compiler has about 23 components (a rough count), so this concerns users' programs.
4. **Structurally equal types are one type.** Types declared apart in each module are the same type when their
   structure is the same, so `ref.test` cannot tell two such runtime types apart. No collision was found in Fable's
   or Opus's types, and nothing prevents one. A single `rec` group (Hydrogen, Argon) makes its members distinct.
5. **Locals of non-null reference type** must be set before they are read, within the block structure. Join points'
   parameters and `out` parameters meet this rule.
6. **The page's whole-program module against "the driver is the library".** Inlining and specialization remove what
   an input's module imports. Opus states the per-unit constraint; Fable plans both.
7. **Lengths and indices are `i32`** in WasmGC, and Quest's are `Int`.

## 4. Issues Some Miss

| Issue | Raised by | Missed by |
|---|---|---|
| JavaScript cannot read a GC array, so text and a module's bytes cross through linear memory | Fable | Opus (unspecified), Hydrogen, Argon |
| The interpreter runs library modules from their source (`treewalk.mod.quest`, `uninterpreted` and after, *checked*), so the page needs `lib/*.mod.quest` | Fable (J5, source by URL) | Hydrogen and Argon bundle `.qi` only |
| wasmtime's default collector leaks cycles | Opus | Fable (left open), Hydrogen, Argon |
| A worker's stack, and that overflow reaches only the host | Opus (measured) | Fable (one line), Hydrogen, Argon |
| Interrupting a running input | Opus, Argon | Fable, Hydrogen |
| `is` on boxed scalars must compare values | Fable, Opus, Argon | Hydrogen |
| `Real` printing and parsing to the byte, and transcendental functions' last bits | Fable, Opus | Hydrogen; Argon assumes a host |
| The driver must be built a module per unit for the JIT | Fable, Opus | Hydrogen, Argon (ships one `compiler.wasm`) |
| A fixed point of self-compilation as a test | Fable, Argon | Opus, Hydrogen |
| Safari's exception handling and tail calls | Opus (listed unchecked) | Fable and Argon assert them |

## 5. What Was Confirmed

- **Lowering from the IR is sound,** as all four choose: join points are jumped to only from their own body
  (ir.md §6.3), so each is a block and each jump a `br`.
- **A module per unit can be instantiated in order:** imports among modules and interfaces are acyclic (modules.md,
  "Acyclic Dependency Enforcement").
- **The interpreter reaches the library through builtins written in Quest,** not through `dlsym` or `os/value`, so
  it ports with the compiler; `os/value` and `os/code` are refused by name.
- **A string's length does not change** (`capacity` always equals `length`, `quest_runtime.h`), and a string literal
  is a fresh string at each evaluation.
