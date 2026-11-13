# Plan: The REPL in a Browser, on WasmGC

The goal: the self-hosted REPL running in a browser page. A new backend of the self-hosted compiler, `wasm`, compiles
Quest to WebAssembly with garbage collection (WasmGC): Quest's values are the engine's structs and arrays, and the
engine's collector is Quest's. The compiler is compiled by that backend, runs in the page, and in the end compiles
each interaction to a module that the page loads into the session, as the arm64 JIT loads machine code
([jit.md](jit.md)).

**Status: decided, nothing built** (2026-11-12). This is the plan to build from. It is a hybrid of four plans written
the same day, each revised after a review:

| Plan | What this plan takes from it |
|---|---|
| [wasm-plan-fable.md](wasm-plan-fable.md) | the shape of the design, the steps with their conditions, the scope of the first milestone, source served by URL |
| [wasm-plan-opus.md](wasm-plan-opus.md) | the closure signature and the rule for unit boundaries, the stack's measurements and the host's recovery, a module per unit in the page |
| [wasm-plan-argon.md](wasm-plan-argon.md) | slots in one array type, locations without dispatch, the shared passes left alone |
| [wasm-plan-hydrogen.md](wasm-plan-hydrogen.md) | the event-driven entry modeled on the kernel, tracebacks deferred |

Those documents hold the measurements and the arguments; this one cites them and does not repeat them.
[wasm-plans-comparison.md](wasm-plans-comparison.md) compares the plans as first written. Where this plan and one of
the four disagree, this plan holds.

§1 lists the decisions and whose they are. §2 to §6 are the design. §7 is what is given up. §8 has the steps.

---

## 1. Decisions

The owner took all of these on 2026-11-12. "Easy to change" means the choice can be revisited once there is code,
without redesign; the others shape every module.

| # | Decision | Hard or easy to change | From |
|---|---|---|---|
| 1 | Tuples and options hold their components in a slot array, inside one struct type, not in a struct per arity (§2.3) | hard | Argon, Hydrogen |
| 2 | Arrays hold `eqref` elements at first, inside a struct; typed elements are a later, measured step (§2.4) | hard | Argon, Hydrogen; the struct is Opus's |
| 3 | Every reference crosses a closure call and a unit's boundary as `eqref`; the receiver casts (§3.2, §5.1) | hard | Opus |
| 4 | Self-compilation first; then the interpreter in a page as a checkpoint, with whatever depth the stack gives; then the JIT as the real REPL (§8) | hard | the owner's earlier answers, and Opus's measurement |
| 5 | `Real` formatting, parsing, and mathematical functions are written in Quest; no C is compiled to WebAssembly (§4.3) | hard | Fable, Opus |
| 6 | A location is a (slot array, index) pair, with no dispatch (§2.6) | easy | Argon |
| 7 | The shared IR passes are unchanged; the backend boxes at slot operations (§4.1) | easy | Argon |
| 8 | A module per unit everywhere, the page included (§5.1) | easy | Opus |
| 9 | Uniform entries are wrappers; a tail call through one may cost a frame (§3.3) | easy | Opus |
| 10 | The host catches a stack overflow and abandons the input or replays the session (§6.3) | easy | Opus |
| 11 | The page does not require cross-origin isolation; an interrupt ends the worker and replays (§6.4) | easy | Argon, Opus |
| 12 | A traceback is the raise site only, at first (§2.9) | easy | Fable, Hydrogen |
| 13 | Self-compilation runs in node with a browser's stack; the program suite runs in wasmtime (§8) | easy | Opus |
| 14 | The first milestone's scope is what the compiler uses, with a pending list (§8.1) | easy | Fable |

Decisions 9 and 11 replace provisional answers recorded in Fable's plan (§11 there, 11 and 10): second bodies for
uniform entries and a page that requires isolation both remain possible later, and neither is built first.

**Settled in all four plans,** and not argued again here:

- The uniform value is `eqref`. An `Int` or `Word` there is an `i31ref` when it fits and a box otherwise; a `Real`
  is a box; `Bool`, `Char`, and `Ok` are `i31ref`s. Null is no Quest value.
- A closure has a native entry and a uniform entry.
- The backend starts from the described IR, not the SSA, and writes the binary format itself, with a printer to
  the text format beside it.
- One recursion group of runtime types, declared identically by every module.
- One exception tag; an exception's identity is a reference.
- Every operation that Quest defines to raise is tested before the instruction that would trap.
- The runtime is written in Quest over intrinsics. Bytes cross to the host through a small linear memory.
- The session runs in a worker, behind an entry that evaluates one input.
- wasmtime always runs with `-C collector=copying`; its default collector does not reclaim cycles.

---

## 2. Representation

### 2.1. The Shape

The current design's division carries over: native representations in locals, parameters, and results of known
calls; one uniform representation wherever a value's type is not known to the code that holds it (aggregate slots,
type parameters' values, calls through closures). Today the uniform representation is a word; here it is an `eqref`.

| Quest type | Native | In a slot, and as a type parameter's value |
|---|---|---|
| `Int`, `Word.T` | `i64` | `i31ref` if it fits in 31 bits, else `(ref $boxInt)` |
| `Real` | `f64` | `(ref $boxReal)` |
| `Bool`, `Char` | `i32` | `i31ref` |
| `Ok` | nothing | the `i31ref` 0 |
| `String` | `(ref $string)` | the same |
| tuple | `(ref $tuple)`, or `(ref $tupleLike)` if it may be a proxy | the same |
| option | `(ref $option)`, or `(ref $tupleLike)` if it may be a proxy | the same |
| record | two values: `(ref $record)` and `(ref $dict)` | `(ref $recBox)` |
| variant | two values: an `i32` tag and an `eqref` payload | `(ref $varBox)` |
| `Array(T)` | `(ref $array)` | the same |
| function | `(ref $clos)`, or the subtype of its closure signature (§3) | the same |
| `auto`, an exception, `Dynamic` | structs of their own | the same |

A slot's type is the nullable `eqref`, so that an array can be made before it is filled. A null read from a slot is
the compiler's or the runtime's mistake, never a value, and no code tests for it.

### 2.2. Scalars

Boxing an `Int` tests its range, which correctness requires: `ref.i31` keeps the low 31 bits silently. An integer
that fits is never boxed, so the representation of a value is unique. Unboxing tests for `i31` (`br_on_cast`) and
otherwise reads the box. `is` at a type parameter goes through the descriptor, as `quest_val_is` does now, and
compares boxed scalars by value; `is` on a box is never `ref.eq` alone.

Argon measured the alternative, always boxing: 3.4 times slower in V8 for slot writes and reads, and some 150 to
250 million more allocations for one unit's compilation (§3.9 there).

### 2.3. Tuples and Options (decision 1)

```wat
(type $obj       (sub (struct (field $hash (mut i32)))))
(type $tupleLike (sub $obj (struct (field $hash (mut i32)))))
(type $tuple     (sub $tupleLike (struct (field $hash (mut i32)) (field $slots (ref $slots)))))
(type $option    (sub final $tuple (struct (field $hash (mut i32)) (field $slots (ref $slots)) (field $tag i32))))
(type $proxy     (sub final $tupleLike (struct (field $hash (mut i32)) ...)))
```

`$slots` is `(array (mut eqref))`. A tuple of any arity is a `$tuple`; component i is element i of its slots.

- **Width subtyping** needs nothing: a tuple seen at a prefix type is the same object, read at fewer indices.
- **An option's case binder** is the option itself, read as a tuple, since `$option` is a subtype of `$tuple`. The
  payload is shared, with no pointer into an object. A case without components shares one empty slot array.
  Options are values ([extensions.md](extensions.md), "Options as Values"), so `is` on options follows those rules
  and uses `ref.eq` only as a fast path.
- **A proxy** is recognized by a cast where a tag bit is tested now: a type that may be proxied is held as
  `(ref $tupleLike)`, and a read is `br_on_cast $tuple` with the proxy's path on failure. `type_may_be_proxied`
  keeps deciding which accesses test.
- **The runtime reads component i for an i known only at run time** (conversion, printing, proxies, `dynamic`).
  Here that is an `array.get`. With a struct per arity it would be a switch over every arity.
- **No limit is near.** The deepest chain of subtypes in the plan is five (§2.11). A struct per arity would have
  met the engines' limit of 63 and needed a cap and an overflow type.

*The cost,* measured by Argon (§3.7 there) against a flat struct of three fields: in V8, allocation 8% slower and a
typed read 17% slower; in wasmtime, about 1.7 times slower at both. A tuple is two objects. Flat structs remain the
known optimization if the self-compilation's profile asks for it; adopting them later changes every tuple access and
the locations of §2.6.

### 2.4. Arrays (decision 2)

```wat
(type $array (sub final $obj (struct (field $hash (mut i32)) (field $elems (ref $slots)))))
```

Every `Array(T)` holds `eqref` elements, so `Array(Int)` and generic code's `Array(A)` are one type, read in place
with no dispatch, and no site must agree with another about an element kind. The struct gives the array its
identity hash; Opus measured the indirection at nothing in V8 and about 14% in wasmtime (§3.1 there).

*The cost:* a full-width `Word` (the hash vectors of `collections/hashmap`) or a `Real` allocates a box at each
store. Small integers do not.

*Later, if measured to matter:* subtypes of `$array` by element kind (`i64`, `f64`, `i8`), as Opus's §5.7 and
Fable's R5 describe, with generic code dispatching on the subtype. That step also adds containers to §2.6's
locations and must hold an invariant that fails silently when broken: the site that allocates and every site that
reads agree on the kind, including for an abstract type whose representation is an `Int`. It is not taken before the
self-compilation has been profiled.

### 2.5. Records and Variants

```wat
(type $record (sub final $obj (struct (field $hash (mut i32)) (field $layout (ref null $desc)) (field $slots (ref $slots)))))
```

A record stays a pair, as now: the payload (`$record`, its fields in name order in its slots) and the view's table
(`$dict`: an `(array i32)` of slot indices, and the stored types). `r.x` is `payload.slots[dict[i]]` and an unbox.
Width subtyping pairs the payload with another table. In a slot the pair is boxed in an immutable `$recBox`. A box
can no longer be embedded in its aggregate's allocation, so the IR's `embedded` boxes are ordinary ones here.

A variant stays a pair of an `i32` tag, in its type's numbering, and an `eqref` payload, remapped by tag maps
(`(array i32)`) as now, and boxed in an immutable `$varBox` in a slot.

### 2.6. Locations (decision 6)

A `var` or `out` parameter receives two values: a `(ref $slots)` and an `i32` index. Every address the IR can take
is such a pair (Argon's §3.8 has the proof):

| The IR's address | The pair |
|---|---|
| a local (`@x`), or a temporary (`var(e)`) | a one-element slot array made where the address is taken, and 0 |
| a record's field (`@r.f`) | the payload's slots, and `dict[f]` |
| a tuple's or a case's component (`@t.i`) | the slots of the tuple after unproxying, and i |
| an array's element (`@a[i]`) | the array's slots, and i, after the bounds test |

The callee reads with `array.get` and an unbox, and writes with a box and `array.set`. Nothing dispatches, and the
semantics are exact, including aliasing. A local whose address is taken lives in its slot array from its
declaration; a record or variant there is its box.

Neither `questlang/` nor `lib/` passes a location at all (counted by Fable, Opus, and Argon), so this is built after
the first milestone.

### 2.7. Strings

`$string` is a subtype of `$obj` holding a length and a `(ref $bytes)`, `$bytes` being `(array (mut i8))`. Strings
are mutable in place (`string.setChar`), and a literal is a fresh string at each evaluation, as now, made from the
unit's data segment.

### 2.8. Identity and Its Hash

`is` is `ref.eq` after unproxying, with §2.2's rule for scalars and the options' rules. `hash.identityHash` has no
address to hash: every heap object is a subtype of `$obj`, whose `$hash` field takes the next value of a counter the
first time it is asked for. Scalars hash by value, through the descriptor.

A counter's values differ from addresses. `ir/represent` puts an identity hash's digits in a memo key; that it
never reaches the compiler's output is checked in step 1 (§8.1), since the fixed point depends on it.

### 2.9. Exceptions and Tracebacks (decision 12)

One tag, defined by the runtime module and imported by every other, carries the exception's state. Evaluating an
`exception` declaration allocates an `$exception`, and a handler matches by `ref.eq`; the built-in exceptions are
globals of the runtime. A `try` is a `try_table` that catches only that tag, never `catch_all`, so a host's
exception or another language's passes through unseen. Re-raising is `throw_ref`.

The engine hides the frames, so a traceback is the raise site, which the raise already carries as text. Run goldens
that hold frames are on a list of accepted differences. Later options, neither built first: the JavaScript stack
read at a traced raise, under a JavaScript host; a shadow stack of function names, at a cost to every call.

### 2.10. Traps, and `Int` Where WebAssembly Wants `i32`

No handler catches a trap. **No trap is reachable from a Quest program compiled by a correct compiler, except the
stack's and the heap's.** Fable's R15 and Opus's §7 have the table of instructions; in short:

- **Division and remainder:** the divisor is tested for 0 (raising `int.error` or `word.error`) and for -1 (which
  wraps, as now) before the instruction.
- **`Real` to `Int`:** the range and NaN are tested (raising `real.error`), then the saturating conversion is used.
- **An index** is compared in 64 bits, unsigned, with the length extended, which catches a negative index and a
  huge one at once and raises the exception of today; only then is it narrowed to `i32`.
- **A size to allocate:** negative raises as today; over the target's maximum is the fatal out-of-memory error, with
  its message, before `array.new` can trap.
- **A failed cast or a null** cannot happen. Where a program's values decide (unboxing, a proxy), the code is a
  `br_on_cast`, which does not trap. A trap of this kind is reported by the host as an internal error.

An array or a string has fewer than 2³⁰ elements on this target.

### 2.11. Types Across Modules

A type is identified by its recursion group's structure and its position in the group. Types declared apart with
the same structure are one type, which a cast could then not tell apart.

- **One group, R, holds every type the runtime defines or code tells apart by a cast:** `$boxInt`, `$boxReal`,
  `$slots`, `$bytes`, the `i32` array, `$obj`, `$tupleLike`, `$tuple`, `$option`, `$proxy`, `$string`, `$array`,
  `$record`, `$dict`, `$recBox`, `$varBox`, `$clos`, `$exception` and a raised exception's state, the auto and
  `Dynamic` structs, the descriptors, and the view maps. Position makes its members distinct, so no later edit can
  merge two. Every module declares R first, from one table in the backend.
- **Standing alone, and meant to merge by structure:** function types, the closure types of §3.1 for each
  signature, and each function's own closure type.
- **A change to R is a change to the ABI** (§5.3): a module compiled against another R fails to link, since an
  import's type does not match.

Fable's R19 and Opus's §3.2 measured the engines' limits. With decision 1 none is near but two: 50,000 locals in a
function, so the printer reuses locals by type as scopes end; and a function's size (7.6 MB) and `array.new_fixed`'s
10,000 operands, so a unit's descriptors and constants come from data segments and from initializers cut into
functions of bounded size. A limit reached is a compile-time error naming what reached it.

### 2.12. Reference Locals

Validation requires a local of non-null reference type to be set before it is read, and forgets at a block's end a
set made inside it. A variable bound once is set where it is bound and is non-null. A join point is a block whose
results are its parameters, set just after the block's end. A mutable variable assigned inside nested blocks is
declared nullable. An `out` parameter's target is a slot, which is nullable already.

---

## 3. Closures

### 3.1. Two Entries

`$clos` is in R. For d descriptor parameters and n value parameters, `$closU(d,n)`, a subtype, adds the **uniform
entry**: a function of the closure, d descriptors, and n `eqref`s, giving an `eqref`. For each closure signature S
(§3.2), `$closS`, a subtype of that, adds the **native entry**. A function's own closure type, final, adds its
captures at their native types; only its own code reads them. A function that captures nothing has one closure, a
global.

- **A known callee** is called directly, with no closure.
- **A call through a closure** whose static type has closure signature S tests the closure for `$closS`
  (`br_on_cast`) and calls the native entry. When the test fails, it boxes the arguments, calls the uniform entry,
  and unboxes the result.
- **The uniform entry** of a function unboxes, calls the native entry, and boxes the result. When S has no scalar,
  record, or variant, S is the uniform signature and one function is both entries.

So a function value needs no conversion when its type is instantiated, keeps its identity, and may sit in any
array or `var` slot. The conversions C rejects because a function's signature differs inside mutable data
([c-representation.md](c-representation.md) §6.4.5) do not arise. Opus measured the test at nothing in V8, and the
uniform entry at ten times a native call (§3.1 there).

### 3.2. The Closure Signature (decision 3)

The closure signature of a function type maps each parameter and the result:

| Quest type | WebAssembly |
|---|---|
| `Int`, `Word` | `i64` |
| `Real` | `f64` |
| `Bool`, `Char` | `i32` |
| `Ok` | nothing |
| a record | `(ref $record) (ref $dict)` |
| a variant | `i32 eqref` |
| a `var` or `out` parameter | `(ref $slots) i32` |
| every other type: strings, tuples, options, arrays, functions, abstract types, type parameters | `eqref` |

Each quantifier adds a descriptor before the value parameters. The callee casts a reference parameter to its type
where it uses it.

The signature is computed from the type alone, with a type parameter as `eqref`. So a closure made for
`String -> Word` has the signature that generic code computes for `K -> Word`, and `hashMap`'s calls of a string's
hash and equality take the native entry with nothing boxed.

*What it does not cover:* a closure whose own signature has a scalar where the caller's has a type parameter
(`hash.int` at `K -> Word`). The test fails and the uniform entry boxes: an allocation for each hash of an `Int`
key, since a hash is a full-width `Word`. The remedy is today's `adapt` plan as an optimization: where a function is
passed at an instance of a generic type, wrap it once in a closure of the generic signature. It needs the represent
pass to know this target's signatures, which §4.1 defers, so it is taken when step 10's profile shows the cost.

### 3.3. Tail Calls (decision 9)

Tail calls are made "whenever possible, not as a guarantee of the language" ([arm64.md](arm64.md)). Here
`return_call` and `return_call_ref` make them, wherever no code must run after the call: every direct call and
every native-entry call in tail position, and a uniform entry's call when the result is a reference.

A uniform entry that must box its result, and a caller that must unbox one, leave a frame. A loop written through
closures that passes through one each time around grows the stack where natively it does not. With §3.2 that needs
a closure with a scalar result called at a type parameter, in a cycle. It is an accepted difference (§7). Fable's
P7 has the remedy if a real program needs it: a second compilation of the body as the uniform entry. It adds code
and changes no type.

---

## 4. The Compiler and the Runtime

### 4.1. Where the Backend Forks (decision 7)

```
typed AST → lower → Core → simplify → specialize → closure-convert → represent → describe → wasm
```

The shared passes, `codegen/layout`, and the native backends' goldens are unchanged. Today's represented IR has no
conversion where a scalar meets a slot (`slots` asks `layout.isBoxedInSlots`, true only of records and variants);
the native backends convert in the SSA's builder. The wasm backend does the same in its own builder: every slot
operation (making a tuple, reading a component, an array's element, a record's field, a store) boxes or unboxes by
the slot's static type, and the IR's `box`, `unbox`, `slot_box`, and `slot_unbox` plans become real conversions.

The pass is given a model of this target's representation only when an optimization needs one: §3.2's adapters, and
specialization on scalar type arguments, which matters more here than natively because it removes boxes.

Control flow maps directly: the IR is structured, a join point is jumped to only from its own body
([ir.md](ir.md) §6.3), so a join is a block, a jump a `br`, a `loop` a `loop`, a `switch` a `br_table`, and a `try`
a `try_table`. What the SSA's passes did is the engine's job or is lost.

The bootstrap gets nothing, as with every backend.

### 4.2. The Runtime in Quest

The C runtime cannot touch the engine's objects. The collector is not needed; the rest exists again, in Quest, in
unsound modules ([modules.md](modules.md) §4.4) over intrinsics the backend compiles to single instructions (a cast
or a test for a kind, a slot's read and write, a box, `ref.eq`, the `i31` operations, bytes). On top, in Quest:
descriptors and their instantiation, run-time subtyping, `quest_convert`, proxies, view maps, the map of record
tables, printing and echo, strings, `dynamic`'s serialization, exceptions.

The two runtimes must agree to the byte on what programs print, which the shared run goldens check.

`lib/` names 174 external values (151 C functions, 9 constants, 14 exceptions; Opus's count, §9.2 there), and the
compiler links all of them. Each maps to an instruction sequence, a runtime function, or a host call. A table plays
the part of `codegen/externals`, and a test checks that it covers `lib/`. `os/process`, `os/code`, `os/value`, and
readline have no counterpart; their externals raise their module's error.

### 4.3. `Real` (decision 5)

WebAssembly's `f64` instructions cover arithmetic, `sqrt`, `floor`, `ceil`, `trunc`, `nearest`, `abs`, `min`, `max`,
and `copysign`, exactly, on every engine. It has no other mathematical function and no formatting or parsing, and
neither has WASI. JavaScript has both, but wasmtime's command line cannot import them and browsers need not agree
on `Math.sin`'s last bit. So both are written in Quest, and no C is compiled to WebAssembly.

- **Formatting and parsing, in the first milestone.** The compiler itself needs them: the lexer parses real
  literals and `conv` prints them. Both are done exactly, over `util/bignum`, not fast: parsing by big-integer
  arithmetic to the correctly rounded `f64`, printing by the method of `quest_format_real`, which finds the shortest
  digits that read back as the same value. Being exact, they give the C runtime's bytes, which the shared goldens
  check. One new intrinsic reinterprets an `f64`'s bits as an `i64` and back.
- **The mathematical functions, after it.** The compiler calls none of them. They are ported from a portable
  library of known quality (musl's or FreeBSD's `msun`) to Quest: about thirteen functions of `f64` arithmetic and
  bit operations. Until then their externals fail with a message. Their results are the same on every WebAssembly
  engine and may differ from Apple's libm in the last bit (Argon measured 1 to 2 units, §3.5 there), so goldens
  that print such results are recorded for this target or exempt (§7).

### 4.4. The Host, and Bytes Across It

Neither JavaScript nor WASI can read a GC array. The runtime module has one linear memory, used only as a buffer
for what crosses, grown to the largest thing that has crossed. Text out is copied from the string's bytes into the
buffer, and the host is called with a length; text in arrives in the buffer and is copied into a new byte array. A
`String` is bytes on both sides, so nothing is transcoded. Each copy is a loop: about 2 to 11 ms for the compiler's
4 MB of source (Opus's and Argon's measurements), once in a build.

The host interface is small: write bytes to a stream, read bytes, open and read a file, the arguments and the
environment, the clock, exit, and, in a page, load a module's bytes. It is implemented once over WASI's first
preview, for wasmtime and for node's `node:wasi`, and once in JavaScript for the page.

---

## 5. Units and Linking

### 5.1. A Module for Each Unit (decisions 3 and 8)

Each unit is a WebAssembly module, for programs, for the driver in the page, and for each interaction. It exports
its functions, its record (two globals, payload and table), its initializer, and its fingerprint, and imports the
runtime module, the host interface, and what it uses of other units, by unit name. wasmtime links with `--preload`,
node and the page with a loader of a few lines. Imports among units are acyclic ([modules.md](modules.md)), so the
modules can be instantiated in order.

**An exported function's signature is its closure signature** (§3.2), computed from the interface alone, which the
exporter and every importer see alike. So tuples that may or may not be proxied, and abstract types, all cross as
`eqref`, and an abstract type whose representation is an `Int` crosses boxed, as a module's abstract types convert
at its boundary in C. Calls inside a unit may use more precise types.

Initialization is explicit, as in C: a unit's `init`, guarded by a global, calls its imports' `init`s in the order
of its import list and then runs its own top level. WebAssembly's start functions only build a module's static
data, since their order is the loader's.

**The page's driver is these same modules,** about 290 of them, instantiated at about 10 µs each. The IR's
whole-program build is not used for it: it sees through abstract types to their representations, so its layouts
would disagree with an input compiled apart (Opus's §8.2). Merging the modules at the WebAssembly level, which
keeps every export, is a later optimization of size and start-up.

### 5.2. Files in a Page

A URL prefix is a `QUEST_PATH` directory (the owner's answer in Fable's plan, J5 there, which has the details): the
page is given prefixes, and an import looks under each in turn, fetching source, which the compiler in the page
compiles or the interpreter runs. In a worker a fetch can be synchronous, so the compiler's file reads stay as they
are. Only "not found" moves the lookup to the next prefix; any other failure is an error at the import. Each URL is
fetched at most once in a session.

The page serves two kinds of thing: the driver's modules, built for this target at a release, and sources
(`lib/`'s interfaces and modules, and the user's), built by nobody. The interpreter runs a library module from its
source, with its externals bound to the driver's compiled library, as natively. `.qi` texts are made in the
session's memory.

### 5.3. Artifacts

A `.qi` holds nothing of a backend, and one serves every target. A unit's code is a `.wasm` where a `.o` would be,
and wasm builds have a directory of their own, as the stages are kept by backend. The ABI version stays one number,
bumped for a change to either runtime or to R, and the target's name joins what the JIT's fingerprint digests
([jit.md](jit.md) §3.3.1), so a unit's fingerprint for this target never equals its native one. Fable's plan says a
`.qm` of another backend is already stale and Argon's says `isManifestStale` does not test it; step 9 checks and
fixes it if needed.

---

## 6. The Page

### 6.1. The Session

The driver runs in a worker. It exports entry points, modeled on the kernel's session
([jupyter-kernel.md](jupyter-kernel.md)): initialize; say whether an input is complete; evaluate an input, returning
what it printed; abandon an input. The page owns the loop, the prompt, and line editing; `io/readline` is not used.
Compiling a module is synchronous in a worker at any size.

### 6.2. The Stack

A Chromium worker has about 512 KB of stack and a page's thread about 1 MB, against 8 MB natively, and a page can
change neither (Opus's §3.2).

- **The compiler fits.** Natively it compiles its largest unit in under 100 KB of stack and its whole driver in
  under 200 KB (measured by Fable, Opus, and Argon). It fails on input nested hundreds of levels deep: 0.9 KB for
  each level of a chain of infix operators.
- **The interpreter does not,** at its own limit of 1,000 calls: natively about 6 KB of stack for an interpreted
  call whose body nests calls (Opus), so some 80 to 250 calls in a worker.
- **Compiled code does:** tens of bytes a call.

So the interpreter in a page is a checkpoint (decision 4): it shows the driver running in a page, with shallow
recursion, and the JIT follows at once as the REPL people use. The interpreter is not rewritten for this target.
Step 12 measures its depth in WebAssembly, which the native figure only estimates.

Tests under node constrain the stack to a browser's (`--stack-size`, or a worker's `resourceLimits`), or they pass
where a browser fails.

### 6.3. When the Stack Overflows (decision 10)

No handler in a module sees the overflow: wasmtime traps, and V8 gives JavaScript a `RangeError`. The Quest code
that would roll a failed input back does not run. The host catches the error at the entry, and what it does depends
on what was running:

- **An input's compiled code:** the session's state changes only when an input commits, so the host calls the
  entry that abandons the input, reports `stack.overflow`, and the session goes on. This is better than native,
  where the session ends.
- **The compiler or the interpreter:** their structures may be half updated. The host ends the worker, starts
  another, replays the session's committed inputs with their output suppressed, and reports the overflow for the
  failed input. Replay runs the inputs' effects again and assumes they give the same results.
- **Under wasmtime or node, a program:** the run ends, as compiled code's overflow ends it natively.

A count at each function's entry that raises a catchable `stack.overflow` first (Fable's A8) is a later addition.

### 6.4. Interrupts (decision 11)

A running call cannot be stopped from outside, only its worker ended. The page ends the worker and replays, as
§6.3 does. The page needs no cross-origin isolation, so any static host can serve it. Where the two headers are
present, a flag in shared memory that compiled code polls could stop an input and keep the session without a
replay; that is an addition, with a cost in every unit compiled for a session.

---

## 7. Accepted Differences From the Native Backends

1. **Tracebacks** are the raise site only (§2.9).
2. **A tail call through a uniform entry that converts a result** leaves a frame (§3.3).
3. **The stack is smaller:** a deep recursion that runs natively may overflow in a page, and the interpreter's limit
   of 1,000 calls is not reached there (§6.2).
4. **A stack overflow or an interrupt may replay the session** (§6.3, §6.4).
5. **Arrays and strings have fewer than 2³⁰ elements** (§2.10).
6. **The mathematical functions' results may differ in the last bit** from Apple's libm, and are absent until
   milestone 4 (§4.3).
7. **`os/process`, `os/code`, `os/value`, and readline** are absent, and with them the parallel build.
8. **No mixing with C units.** The other backends were brought up by moving units between backends until a
   miscompile was found; a wasm unit's values are not C's. The interpreter is the reference and the IR dumps are
   the evidence.

Each has a remedy named in its section, and none is built before it is asked for.

---

## 8. Steps

Four milestones. The first has steps with conditions; the others have stages, whose steps are written when the
first is reached and its measurements are known. Costs are recorded as actuals
([arm64-performance-review.md](arm64-performance-review.md) §4), not estimated.

No probe step: the four plans' probes measured what this design rests on, and each section cites them.

### 8.1. Milestone 1: The Compiler Compiles Itself

The self-hosted compiler, compiled by the new backend to a module for each unit, runs in node and compiles itself
there, writing the modules its native self writes. The scope is what the compiler uses (decision 14); everything
else is on a pending list, with reasons, as arm64's was.

Tests run in wasmtime (`-C collector=copying`, `-W max-wasm-stack` at the native 8 MB, so that the suite's
recursions behave as natively) and in node, through a runner mode for the run goldens. `tools/check` runs the mode
only when the backend's files differ, until its time is known.

1. **A census of what the compiler uses:** `auto`, `inspect`, and `dynamic`; identity hashes, and that
   `ir/represent`'s use of one reaches no output (§2.8); operations on `Real`; `os/process`; the widest closure and
   the largest function's variables (§2.11).
   *Done when* each is listed as needed for this milestone or pending.
2. **Instructions, encoder, and printer** (`questlang/wasm/`): instructions and types as data, an encoder to the
   binary format, a printer to the text format, and R from one table.
   *Done when*, for a corpus of modules built in unit tests, the encoder's bytes equal `wasm-tools parse` of the
   printed text, every module passes `wasm-tools validate`, and one with a struct, an exception, and a tail call
   gives the same output in wasmtime and in node.
3. **The backend's skeleton.** `--backend wasm`; code from the described IR for `Int`, `Bool`, `Char`, control
   flow, direct calls, tail calls, string literals, and the tests before trapping instructions (§2.10); output
   through the host, over WASI and in JavaScript; a unit is a module from this step on, the runtime a module of its
   own; the runner mode and its pending list.
   *Done when* the run goldens that need no more pass in both engines, a test of each row of §2.10 passes, and the
   native backends' goldens are unchanged.
4. **Aggregates:** tuples and options (§2.3), arrays (§2.4), strings, records and variants (§2.5), with boxing at
   slot operations (§4.1), case binders that share the payload, and the options' value rules.
   *Done when* their goldens pass.
5. **Closures:** the closure types, both entries, the closure signature, the call through a closure with its test
   and its fallback, static closures.
   *Done when* the higher-order goldens that are not polymorphic pass.
6. **The runtime, first part:** descriptors built by a unit's initializer within §2.11's limits, instantiation and
   its memoization, `is` at a type parameter, the identity hash, printing as the REPL echoes, exceptions with the
   uncaught report.
   *Done when* the goldens for printing and for exceptions pass with the C runtime's output, less tracebacks' frames.
7. **Polymorphism:** descriptor parameters, the `box` and `unbox` plans, own views and view maps, proxies and the
   subtyping plans, and as much of `auto`, `inspect`, and `dynamic` as step 1 found the compiler to use.
   *Done when* the polymorphism and subtyping goldens pass, less what step 1 marked pending.
8. **`Real` formatting and parsing in Quest** (§4.3).
   *Done when* the goldens that print and read `Real`s pass byte for byte, and a test of values chosen for their
   difficulty (halfway cases, subnormals, the largest and smallest) agrees with the C runtime.
9. **Units and the library:** exports at closure signatures, imports by name, initializers; the externals' table
   and its coverage test; the driver's build writing a module for each unit; the loaders for wasmtime and node;
   files, arguments, and the environment over WASI; artifacts (§5.3).
   *Done when* a program of several units using `lib/` runs in both engines, and the pending list holds only what
   step 1 excluded, locations, and the mathematical functions.
10. **The compiler through the backend.** The driver's units compiled by the native compiler with `--backend wasm`
    and run in node, with the stack constrained to a browser's, to compile a small program, then the run suite's
    sources, then itself. Differences are found against the native compiler's IR dumps, stage by stage.
    *Done when* the compiler running in node, compiling itself with `--backend wasm`, writes modules byte-identical
    to those the native compiler wrote; and [benchmarks.md](benchmarks.md) records, beside arm64's, that
    self-compilation's time and peak memory, the least stack it succeeds with, and a profile naming what boxes
    most (§2.4's `Word`s, §3.2's hash functions), which decides whether typed arrays or adapters are taken.

### 8.2. Milestone 2: The Interpreter in a Page

A checkpoint (decision 4).

11. **The session's entries and the JavaScript host** (§6.1, §4.4, §5.2), with recovery by replay (§6.3, §6.4); the
    interpreter's REPL transcripts in node against the wasm driver.
12. **The page:** the worker, the loader, the prompt; the interpreter's depth measured in a Chromium worker and
    recorded (§6.2). Checked by hand in a Chromium browser, the only kind promised for now.

### 8.3. Milestone 3: Each Interaction a Module

13. **The JIT:** an input is a unit, compiled in the session to a module, its bytes passed through the buffer and
    loaded by the host, linked to the driver's modules and to earlier inputs'. A top-level binding that may be
    redefined is a cell that later modules import ([repl.md](repl.md) §6). A failed input is not committed. The
    fingerprint check carries over, with the target in it. The JIT's transcripts in node, then by hand in the page.

### 8.4. Milestone 4: The Rest

In an order chosen then:

- `var` and `out` parameters (§2.6);
- the rest of `auto`, `inspect`, and `dynamic`;
- the mathematical functions in Quest (§4.3);
- the run suite's pending list worked down;
- whatever step 10's profile asked for: typed arrays (§2.4), adapters at polymorphic calls (§3.2), specialization
  on scalar type arguments (§4.1), flat tuples (§2.3);
- the page's size and start-up time, and merging modules (§5.1);
- Safari and Firefox, neither checked nor promised until then.
