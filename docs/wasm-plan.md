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

§1 lists the decisions and whose they are. §2 to §6 are the design. §7 is what is given up. §8 has the steps, and
§9 the results of step 0's probes (2026-11-13), on which the owner confirmed decisions 1 and 2, and §10 step 1's
census of what the compiler uses. Steps 0 and 1 are done; step 2 is next.

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
| `Ok` | the `i31ref` 0, as an `eqref` | the same |
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

Boxing an `Int` tests its range, which correctness requires: `ref.i31` keeps the low 31 bits silently. The test is
on the 64-bit pattern read as signed, for a `Word` as for an `Int`: the value fits when it equals the sign
extension of its low 31 bits. A pattern that fits is never boxed, so the representation of a pattern is unique,
whichever of the two types it has. Unboxing tests for `i31` (`br_on_cast`) and
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
  payload is shared, with no pointer into an object. Options are values ([extensions.md](extensions.md), "Options
  as Values"), so `is` on options follows those rules and uses `ref.eq` only as a fast path.
- **A case without components allocates nothing:** the runtime holds a table of such options, one for each tag,
  made as they are first asked for, and every module takes them from it. (The lexer's token type has 93 such
  cases.) `is` does not depend on the sharing.
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
(`$dict`: a struct of an `(array i32)` of slot indices and the stored types). `r.x` is
`payload.slots[dict.indices[i]]` and an unbox.
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
| a module's top-level `var` | as a local: a top-level `var` whose address its unit takes is kept in a one-element slot array that its global holds, and 0; one that other units see is a field of the module's record, and is a record's field |

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
address to hash: every object with an identity is a subtype of `$obj`, whose `$hash` field takes the next value of a
counter the first time it is asked for: tuples, options, proxies' originals, strings, arrays, records' payloads,
closures (`$clos`), exceptions, and auto values. The boxes of scalars, of records, and of variants are not: scalars
hash by value, through the descriptor, and a boxed record is its payload.

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
- **A size to allocate:** negative raises as today; over the maximum is the fatal out-of-memory error, with its
  message, before `array.new` can trap. The maximum is by element kind and by engine, measured and not assumed: V8
  takes 134,217,720 `eqref` elements (about 2²⁷) and 1,073,741,792 bytes, and wasmtime 536,870,899 and
  2,147,483,596 (§9.4). The runtime tests against the least of the engines' figures for the kind, which are V8's,
  so a program behaves alike on each.
- **A failed cast or a null** cannot happen. Where a program's values decide (unboxing, a proxy), the code is a
  `br_on_cast`, which does not trap. A trap of this kind is reported by the host as an internal error.

So an array has fewer than about 2²⁷ elements on this target, and a string fewer than about 2³⁰ bytes.

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

**The uniform entry's n counts Quest's value parameters, not WebAssembly's.** Each is exactly one `eqref`,
whatever it is natively: a record is its `$recBox` and a variant its `$varBox`, though each is two values in a
native signature; a location is a boxed pair; an `Ok` is the `i31ref` 0, as it is natively. The result is exactly
one `eqref`. So every function type of n parameters and d quantifiers has the one uniform
type, which is what lets any caller use it.

**Every entry takes its closure as `(ref $clos)`,** the base type in R, never as its own closure type, and casts it
to its own type in its body when it has captures. An entry typed by its own closure type would make the function
type and the closure type refer to each other, which puts them in one recursion group; as it is, each stands alone
and merges across modules by structure (§2.11).

- **A known callee** is called directly, with no closure.
- **A call through a closure** whose static type has closure signature S tests the closure for `$closS`
  (`br_on_cast`) and calls the native entry. When the test fails, it boxes the arguments, calls the uniform entry,
  and unboxes the result.
- **The uniform entry** of a function unboxes, calls the native entry, and boxes the result. When S has no scalar,
  record, variant, or location, S is the uniform signature and one function is both entries. A location reaches a
  uniform entry as one `eqref`, a pair boxed for the call, which allocates; it is the rare path of a rare feature.

So a function value can be called at any type it has, with no conversion, and may sit in any array or `var` slot:
this representation has no need of the conversions C rejects because a function's signature differs inside mutable
data ([c-representation.md](c-representation.md) §6.4.5). The represent pass still rejects them at first, so that
both targets accept the same programs, and still wraps a function passed at a generic type in an adapter, which
is another closure under `is`, as it is natively (§3.2, §4.1). Opus measured the test at nothing in V8, and
the uniform entry at ten times a native call (§3.1 there).

### 3.2. The Closure Signature (decision 3)

The closure signature of a function type maps each parameter and the result:

| Quest type | WebAssembly |
|---|---|
| `Int`, `Word` | `i64` |
| `Real` | `f64` |
| `Bool`, `Char` | `i32` |
| `Ok` | `eqref`, the `i31ref` 0 |
| a record | `(ref $record) (ref $dict)` |
| a variant | `i32 eqref` |
| a `var` or `out` parameter | `(ref $slots) i32` |
| every other type: strings, tuples, options, arrays, functions, abstract types, type parameters | `eqref` |

Each quantifier adds a descriptor before the value parameters. A function casts each reference parameter once, at
entry, into a local of its precise type.

**Every function has this signature, not only closures' entries and exports.** Precise reference types appear in
locals only. `return_call` and `return_call_ref` require the callee's result type to be a subtype of the caller's,
so a function whose result were a `(ref $string)` could not tail-call one that gives an `eqref` (Opus's author
checked: `wasm-tools validate` rejects it). With one rule for every signature, any call in tail position whose
results agree in kind can be a tail call (§3.3). The one exception is a function the `unbox` pass has given an
unboxed result (§4.1): it returns its tuple's components as several results, at their closure-signature types,
and is only ever called directly.

**The signature is computed after bounds are resolved,** as `layout.resolvedShape` does for every backend: a type
parameter or an abstract type with a bound has its bound's representation (two values for a record's, an `i64`
for `Int`'s), and only one without a bound is an `eqref`. The bound is in the interface, so exporter and importer
still agree. The compiler's units have neither (§10.1), so this first matters in milestone 4.

**An `Ok` is a value wherever a value is expected:** a parameter, a result, a local, a slot. The represent pass
gives no plan when either side of a conversion is `Ok`, so nothing in the IR marks where an `Ok` meets a type
parameter or a slot, and an `Ok` that were nothing in some places would have to be made or dropped at crossings
the backend could not see. Natively an `Ok` parameter is a word for the same reason. As a result, a wrapper has
nothing to push after its call: a callback of a scalar parameter and an `Ok` result, which is every `iter`-style
callback over `Int`s, is tail-called through its uniform entry (§3.3). Changing this later would change every
such signature.

The signature is computed from the type alone, with a type parameter as `eqref`. So a closure made for
`String -> Word` has the signature that generic code computes for `K -> Word`, and `hashMap`'s calls of a string's
hash and equality take the native entry with nothing boxed.

*A closure whose own signature has a scalar where the caller's has a type parameter* (`hash.int` at `K -> Word`)
would fail the test and go through the uniform entry, at ten times the cost and with the `Word` result boxed.
Nearly all of the compiler's roughly 350 hash maps are keyed by `Int` or `String`, so this looked like the case the
first milestone's running time rested on. **The census found that it does not arise** (§10.3): the represent pass
already wraps such a function in an adapter of the generic signature, its `adapt` plan, wherever a parameter or the
result needs a `box` or `unbox`, which for C is every scalar and every pointer. `hashMap.new(:Int :V intEqual
hash.int)` is given two adapters today, natively, and the compiler's units have 813 such conversions. On this
target the adapter's closure signature is the generic caller's, so the caller's test succeeds and nothing is boxed
but the key, which is an `i31ref`.

What is left:

- *A function inside a tuple or an array* that reaches generic code unconverted: the uniform entry, correctly and
  slowly. C's `runtime` plan, which would wrap it, occurs nowhere in the compiler (§10.3).
- *Adapters this target does not need:* the pass also wraps `hash.string` and `stringOp.equal`, since for C a
  pointer is boxed to a word. Here their signatures already agree (`eqref`), and the adapter is one more call. A
  model of this target in the pass (§4.1) would leave them out; step 10's profile says whether it matters.

### 3.3. Tail Calls (decision 9)

Tail calls are made "whenever possible, not as a guarantee of the language" ([arm64.md](arm64.md)). Here
`return_call` and `return_call_ref` make them, wherever no code must run after the call: every direct call and
every native-entry call in tail position, and a uniform entry's call when the result is a reference.

**Tail position is found by the backend, through join points.** A call is in tail position when its result reaches
a return by any chain of jumps to join points whose continuations only pass it on, not only when a `return`
follows it. Natively `ssa/tailCalls` finds these on the SSA, which this backend does not have, so it repeats the
analysis on the described IR. Without it, loops that the native backends run in constant stack nest: before that
pass existed, the benchmark `zern`'s two loops nested 16,384 deep. Step 3 tests it.

A uniform entry that must box its result, and a caller that must unbox one, leave a frame. A loop written through
closures that passes through one each time around grows the stack where natively it does not. With §3.2, and `Ok`
results returned as values, that needs a closure whose result is a scalar, a record, or a variant, called at a type
parameter, in a cycle. A callback that a loop calls and that returns to it, as `fold`'s does with a scalar
accumulator, is not such a cycle: its frame is gone before the next step, and what it loses to the uniform entry
is time, which §3.2's first remedy gives back. It is an accepted difference (§7). Fable's
P7 has the remedy if a real program needs it: a second compilation of the body as the uniform entry. It adds code
and changes no type.

---

## 4. The Compiler and the Runtime

### 4.1. Where the Backend Forks (decision 7)

```
typed AST → lower → Core → simplify → specialize → closure-convert → unbox → represent → describe → wasm
```

`unbox` (`ir/unbox`) gives a known local function that returns a tuple an unboxed result: its returns give the
components (`sReturnTuple`) and its direct calls bind them (`sLetTuple`). Here those are WebAssembly's several
results.

The shared passes, `codegen/layout`, and the native backends' goldens are unchanged. Today's represented IR has no
conversion where a scalar meets a slot (`slots` asks `layout.isBoxedInSlots`, true only of records and variants);
the native backends convert in the SSA's builder. The wasm backend does the same in its own builder: every slot
operation (making a tuple, reading a component, an array's element, a record's field, a store) boxes or unboxes by
the slot's static type, and the IR's `box`, `unbox`, `slot_box`, and `slot_unbox` plans become real conversions.

**What each of the pass's plans means here.** The pass decides its plans from C's layouts ([ir.md](ir.md) §8.3),
so some are made for reasons this target does not have. Each still has a meaning that is correct:

| Plan | On this target |
|---|---|
| `box`, `unbox` | a real conversion: a scalar to and from its `eqref` (§2.2), a record or variant to and from its box |
| `slot_box`, `slot_unbox` | as now: a record's or variant's box made, reused, and read |
| `record_view`, `variant_tags`, `view`, `unproxy` | as now, by the ported runtime |
| `cast` | nothing, or a cast between reference types |
| `copy` | as now: a new tuple, each component by its own plan |
| `adapt` | as now: a closure of the target's signature that converts and calls. Made where C's signatures differ, which is not always where this target's do; correct either way, since any closure can be called at any signature |
| `runtime` | the ported `quest_convert` between the two descriptors, in which a function's layout never differs: only views convert, as proxies. Where C copies a tuple because a closure among its components changes signature, this target keeps the original |
| rejected | a compile-time error, as now |

Two consequences, both accepted (§7). The pass rejects on this target what it rejects for C, though §3.1's closures
would run those programs: both targets accept the same language. And `is` answers true here on a tuple that C's
`runtime` conversion copied.

The pass is given a model of this target's representation only when an optimization needs one: §3.2's third
remedy, lifting the rejections, and specialization on scalar type arguments, which matters more here than natively
because it removes boxes.

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

**The runtime is in two layers, so that imports stay acyclic** (§5.1). The library's externals are the runtime's
functions, so a runtime module that imported a library unit would be imported by it in turn: `collections/hashmap`
imports `util/hash`, whose `identityHash` is the runtime's.

- **The core** imports no unit. It holds the exception tag, the built-in exceptions, the intrinsics' functions,
  `is`, the identity hash, descriptors and their instantiation, run-time subtyping, conversion, proxies, view maps,
  and the map of record tables. Its memo tables are written out over arrays, as the C runtime's are, not taken from
  `collections/`. Every external of `lib/` maps to an instruction sequence, a host call, or a function of the core.
  **Its code is monomorphic:** it defines descriptors and their instantiation, so it can use no type parameter
  whose descriptor would have to be instantiated to run it, and no `auto`, `inspect`, or `dynamic`. It is a
  self-contained program over the intrinsics, nearer in style to the C it replaces than to the library, and that
  is most of step 6's size.
- **The upper layer** (printing and echo, `dynamic`'s serialization) may import library units, `util/bignum` and
  the `Real` formatting of §4.3 among them. No unit it imports may import it; in particular none of them may echo.

The backend checks the rule when it builds the runtime, and reports the cycle's path.

`lib/` names 174 external values (151 C functions, 9 constants, 14 exceptions; Opus's count, §9.2 there), and the
compiler links all of them. Each maps to an instruction sequence, a runtime function, or a host call. A table plays
the part of `codegen/externals`, and a test checks that it covers `lib/`. `os/process`, `os/code`, `os/value`, and
readline have no counterpart; their externals raise their module's error, with one exception. `code.symbol`
answers that there is no such symbol, as it does natively for a name the binary lacks:
`questlang/driver/interrupts` calls it at its top level, `driver/repl` imports that unit, and initialization runs
every imported unit's top level, so a `code.symbol` that raised would end the driver before it began. Step 1
lists every external the driver calls at a top level.

### 4.3. `Real` (decision 5)

WebAssembly's `f64` instructions cover arithmetic, `sqrt`, `floor`, `ceil`, `trunc`, `nearest`, `abs`, `min`, `max`,
and `copysign`, exactly, on every engine. It has no other mathematical function and no formatting or parsing, and
neither has WASI. JavaScript has both, but wasmtime's command line cannot import them and browsers need not agree
on `Math.sin`'s last bit. So both are written in Quest, and no C is compiled to WebAssembly.

- **Formatting and parsing, in the first milestone.** The compiler itself needs them: the lexer parses real
  literals and `conv` prints them. The C runtime does neither itself: `quest_shortest_digits` asks libc's `snprintf`
  for the correctly rounded decimal of p digits, for p from 1, tries it and its two neighbors, and keeps the first
  that `strtod` reads back as the same value. So what is written in Quest is those two libc functions' parts, and
  the runtime's loop over them is ported as it stands:
  - *the correctly rounded decimal of p digits:* a double is an integer times a power of two, exactly, so this is
    a big-integer multiplication or division by a power of ten and a rounding to even;
  - *the correctly rounded double of a decimal:* the decimal is an integer times a power of ten, exactly; a
    big-integer division gives the 53 bits and what is left decides the rounding, with subnormals and overflow as
    cases.

  Both are exact arithmetic over `util/bignum`, slow and plain, not one of the fast algorithms (Ryu, Grisu,
  Eisel-Lemire), whose subtlety is in avoiding big integers. Being exact, they give libc's digits, which the shared
  goldens check. One new intrinsic reinterprets an `f64`'s bits as an `i64` and back. The work is some hundreds of
  lines and does not wait for the backend: it runs natively, so it can be written and tested against libc at any
  time before step 8, which only connects it.

  *Not taken:* a helper compiled from C, or JavaScript's `Number`. The owner chose against the first for the
  toolchain it adds to the build, and the second is absent in wasmtime, where the suite runs.
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

The host interface is small: write bytes to a stream and read them; open, read, and write a file; make a directory,
list one, rename and remove a file, and a file's size and time (the build's test for staleness); the arguments and
the environment; the clock; exit; and, in a page, load a module's bytes. The compiler of step 10 writes its
modules and its build directory through it. It is implemented once over WASI's first
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
at its boundary in C. Functions inside a unit have the same kind of signature (§3.2), so an export is the function
itself, with no wrapper.

Initialization is explicit, as in C: a unit's `init`, guarded by a global, calls its imports' `init`s in the order
of its import list and then runs its own top level. WebAssembly's start functions only build a module's static
data, since their order is the loader's.

**The page's driver is these same modules,** about 290 of them, instantiated at about 10 µs each. They are served
as one archive, fetched once and cut into modules by the loader, since 290 requests would cost far more than the
instantiation; what compiling them costs at start-up is measured in step 12. The IR's whole-program build is not
used for the driver: it sees through abstract types to their representations, so its layouts would disagree with an
input compiled apart (Opus's §8.2). Merging the modules at the WebAssembly level, which keeps every export, is a
later optimization of size and start-up.

### 5.2. Files in a Page

A URL prefix is a `QUEST_PATH` directory (the owner's answer in Fable's plan, J5 there, which has the details): the
page is given prefixes, and an import looks under each in turn, fetching source, which the compiler in the page
compiles or the interpreter runs. A worker may make a synchronous request (an `XMLHttpRequest` that is not
asynchronous; `fetch` is always asynchronous), so the compiler's file reads stay as they are. Only "not found"
moves the lookup to the next prefix; any other failure is an error at the import. Each URL is fetched at most once
in a session.

A synchronous request is deprecated on a page's own thread, not in a worker, and it follows CORS as any request
does. Its real costs are a round trip for each file and a logged 404 for each prefix that lacks one, which is why
the common case does not use it:

**The compiler never sees a URL.** Its paths are POSIX's: `path.isAbsolute` tests for a leading `/`, so
`https://host/lib` would be taken as relative to the current directory and normalized into nonsense, and
`modules/paths` leaves out a library directory for which `system.isDirectory` is false. So the host mounts each
prefix at an absolute path of its own (`/lib`, `/remote/0`), `QUEST_PATH` names those, the host answers
`isDirectory` for a mount, and it turns `/lib/list.int.quest` into the prefix's URL inside its own file calls.

A prefix may also be given as an archive of its files, fetched once when the session starts, after which a lookup
under it makes no request. The library is served that way, beside the driver's modules: its sources are about
240 KB (Argon's count), which one file at a time would be a round trip for each import. Requests one file at a
time are then for the user's prefixes.

The page serves two kinds of thing: the driver's modules, built for this target at a release, and sources
(`lib/`'s interfaces and modules, and the user's), built by nobody. The interpreter runs a library module from its
source, with its externals bound to the driver's compiled library, as natively. `.qi` texts are made in the
session's memory, from the interfaces, as the native JIT makes them (about 10 ms for a program's, natively). A
`.qi` holds nothing of a target (§5.3), so the library's archive can carry the release's `.qi` files beside the
sources, and save a session's first inputs the elaboration of every interface they reach, which for an input that
imports the compiler's own units is some 150 of them. Step 12 measures the first input's latency and decides.

### 5.3. Artifacts

A `.qi` holds nothing of a backend, and one serves every target. A unit's code is a `.wasm` where a `.o` would be,
and wasm builds have a directory of their own, as the stages are kept by backend. The ABI version stays one number,
bumped for a change to either runtime or to R, and the target's name joins what the JIT's fingerprint digests
([jit.md](jit.md) §3.3.1), so a unit's fingerprint for this target never equals its native one. A `.qm` written by
another backend is already stale: the test is not in `manifest.isManifestStale` but in the build engine
(`questlang/build/engine`, "compiled by the … backend"), which compares the manifest's backend with the one the
build assigns the unit. `wasm` is one more name there, from step 3.

---

## 6. The Page

### 6.1. The Session

The driver runs in a worker. It exports entry points, modeled on the kernel's session
([jupyter-kernel.md](jupyter-kernel.md)): initialize; say whether an input is complete; evaluate an input, returning
what it printed; abandon an input. The page owns the loop, the prompt, and line editing; `io/readline` is not used.
Compiling a module is synchronous in a worker at any size.

With the JIT, evaluating is three calls by the host, not one: the driver compiles the input and returns its
module's bytes; the host loads the module and calls its code itself; the driver then commits the input, or abandons
it. So no frame of the compiler is on the stack while an input's code runs, and an error the host catches there
unwinds only the input's frames and those of the library and runtime it called (§6.3).

### 6.2. The Stack

A Chromium worker has about 512 KB of stack and a page's thread about 1 MB, against 8 MB natively, and a page can
change neither (Opus's §3.2).

- **The compiler fits natively, and is not known to fit here.** Natively it compiles its largest unit in under
  100 KB of stack (Opus, Argon), and its whole driver in about 160 KB (Opus), in 192 KB as a whole program (Argon),
  or somewhere between 128 and 256 KB (Fable). It fails on input nested hundreds of levels deep: 0.9 KB for each
  level of a chain of infix operators. But V8 runs cold code in its baseline compiler, which gives every local a
  slot on the stack: Fable's author measured a recursive function of 20 locals reaching a depth of 31,000 when
  optimized and 4,450 in baseline, frames seven times larger. A page's first inputs run the compiler cold. Seven
  times 160 KB does not fit a worker. So the printer's reuse of locals (§2.11) is a measure for the stack as much
  as for the limit, and step 10 measures the compiler's stack in baseline code, at a worker's limit, where a long
  self-compilation that has tiered up would not show it. If it does not fit, an overflow in the compiler replays
  the session (§6.3) on ordinary inputs, which is not acceptable; the remedies are fewer locals, the page's thread
  (twice the stack), and loops for the compiler's deepest recursions.
- **The interpreter does not,** at its own limit of 1,000 calls: natively about 6 KB of stack for an interpreted
  call whose body nests calls (Opus), so some 80 to 250 calls in a worker.
- **Compiled code does:** about 100 bytes for a small function's call in baseline code and about 30 when
  optimized, and about 8 bytes more for each live local in either (Opus's author, in V8: 580 bytes with 64 live
  locals, 2.1 KB with 256).

So the interpreter in a page is a checkpoint (decision 4): it shows the driver running in a page, with shallow
recursion, and the JIT follows at once as the REPL people use. The interpreter is not rewritten for this target.
Step 12 measures its depth in WebAssembly, which the native figure only estimates.

Tests under node constrain the stack to a browser's (`--stack-size`, or a worker's `resourceLimits`), or they pass
where a browser fails.

### 6.3. When the Stack Overflows (decision 10)

No handler in a module sees the overflow: wasmtime traps, and V8 gives JavaScript a `RangeError`. The Quest code
that would roll a failed input back does not run. The host catches the error at the entry, and what it does depends
on what was running:

- **An input's compiled code:** the session's bindings change only when an input commits, so the host calls the
  entry that abandons the input, reports `stack.overflow`, and the session goes on. What the input had already
  done to earlier inputs' state stays done: a store to an earlier `var`, to an array's element, to a string, as
  after a raise today ([jit.md](jit.md) §3.2). This is better than native, where the session ends.

  The overflow lands in the deepest frame, which may be the runtime's, part way through an update of one of its
  shared tables (the descriptors' memo, the map of record tables): a point where no Quest raise can occur, and
  nothing rolls it back. So the core runtime (§4.2) counts, in a global, the updates of shared tables in progress,
  and makes each update visible by one final store where it can. The host reads the count after catching the
  error: zero, and it abandons the input as above; not zero, and it replays the session as below. A user's own
  data structure caught half updated is the user's, as it is when an interpreter raises `stack.overflow` today.
  (The alternative, reading the error's stack text for a runtime function's name, depends on each engine's format
  and replays for every overflow inside a library call, most of which harm nothing.)
- **The compiler or the interpreter:** their structures may be half updated. The host ends the worker, starts
  another, replays the session's committed inputs with their output suppressed, and reports the overflow for the
  failed input. Replay runs the inputs' effects again and assumes they give the same results.

  Replay need not compile again what was compiled. A `WebAssembly.Module` can be passed between threads, so the
  page keeps the driver's compiled modules and gives them to the new worker, which only instantiates them: built
  with the page. After milestone 3, the page can keep each committed input's module and `.qi` text too, and a new
  entry of the driver can admit an input again from those, running its code without compiling it: a refinement,
  once replay from source is seen to be slow.
- **Under wasmtime or node, a program:** the run ends, as compiled code's overflow ends it natively.

A count at each function's entry that raises a catchable `stack.overflow` first (Fable's A8) is a later addition.

### 6.4. Interrupts (decision 11)

A running call cannot be stopped from outside, only its worker ended. The page ends the worker and replays, as
§6.3 does. The page needs no cross-origin isolation, so any static host can serve it.

*The cost of replay grows with the session:* stopping an endless loop runs every earlier input again, the long
ones at their full length, and their effects outside the session (a request made, a file in the page's store
written) happen twice. It is the price of needing nothing from the host, and the reason the shared flag stays in
the plan as the next step if sessions prove long. Where the two headers are
present, a flag in shared memory that compiled code polls could stop an input and keep the session without a
replay; that is an addition, with a cost in every unit compiled for a session.

---

## 7. Accepted Differences From the Native Backends

1. **Tracebacks** are the raise site only (§2.9).
2. **A tail call through a uniform entry that converts a result** leaves a frame (§3.3).
3. **The stack is smaller:** a deep recursion that runs natively may overflow in a page, and the interpreter's limit
   of 1,000 calls is not reached there (§6.2).
4. **A stack overflow or an interrupt may replay the session** (§6.3, §6.4).
5. **An array has fewer than about 2²⁷ elements, and a string fewer than about 2³⁰ bytes** (§2.10).
6. **The mathematical functions' results may differ in the last bit** from Apple's libm, and are absent until
   milestone 4 (§4.3).
7. **`os/process`, `os/code`, `os/value`, and readline** are absent, and with them the parallel build.
8. **`is` on some converted values:** true on a tuple that C's `runtime` conversion copies (§4.1).
9. **No mixing with C units.** The other backends were brought up by moving units between backends until a
   miscompile was found; a wasm unit's values are not C's. The interpreter is the reference and the IR dumps are
   the evidence.

Each has a remedy named in its section, and none is built before it is asked for.

---

## 8. Steps

Four milestones. The first has steps with conditions; the others have stages, whose steps are written when the
first is reached and its measurements are known. Costs are recorded as actuals
([arm64-performance-review.md](arm64-performance-review.md) §4), not estimated.

The four plans' probes measured this design's pieces, and each section cites them. Two things about their
combination were not measured, and step 0 measures them before any compiler code.

`wasm-tools` 1.263.0, wasmtime 50.0.1, and node 26.13 are installed (`/opt/homebrew/bin`).

### 8.1. Milestone 1: The Compiler Compiles Itself

The self-hosted compiler, compiled by the new backend to a module for each unit, runs in node and compiles itself
there, writing the modules its native self writes. The scope is what the compiler uses (decision 14); everything
else is on a pending list, with reasons, as arm64's was.

Tests run in wasmtime (`-C collector=copying`, `-W max-wasm-stack` at the native 8 MB, so that the suite's
recursions behave as natively) and in node, through a runner mode for the run goldens. `tools/check` runs the mode
only when the backend's files differ, until its time is known.

0. **Two probes, by hand, in WebAssembly text.** (a) Decision 3's cost: a function of three reference parameters
   called through an export and through a closure, with a cast of each parameter on entry, against the same
   function at precise types, in node and wasmtime. (b) The stack in baseline code: a function shaped like the
   compiler's recursive ones (some tens of locals, a few live across the call), its depth in node with
   `--liftoff-only` and without, at a worker's limit, with locals reused and not. (c) Decisions 1 and 2 on the
   compiler's own shapes, since after step 4 every module is built on them and step 10's profile comes too late to
   change them: tuples made and read as slot arrays and as flat structs, and arrays of `eqref` and of `i64`, with
   the integers the compiler stores, many of which do not fit 31 bits and so are boxed at every store (spans of
   merged files, `file * 2³²`; reserved symbol ids; every `Word` hash; SHA-256's words), in a vector, a hash map
   keyed by `Int`, and a walk over tuples. (d) Each engine's largest array, by element kind (§2.10).
   *Done when* §2.3, §2.4, §3.2, and §6.2 record the numbers, and decisions 1 and 2 are confirmed or changed on
   them, by the owner.
   *Done 2026-11-13: §9 has the numbers and what they say. Decision 3 stands, and the owner confirmed decisions 1
   and 2 on them the same day.*
1. **A census of what the compiler uses:** `auto`, `inspect`, and `dynamic`; identity hashes, and that
   `ir/represent`'s use of one reaches no output (§2.8); operations on `Real`; `os/process`; the widest closure and
   the largest function's variables (§2.11).
   *Done when* each is listed as needed for this milestone or pending.
   *Done 2026-11-13: §10. It removes variants, record views, proxies' making, `auto`, `inspect`, and locations
   from this milestone, and finds §3.2's adapters already made; steps 4, 6, and 7 are narrowed below.*
2. **Instructions, encoder, and printer** (`questlang/wasm/`): instructions and types as data, an encoder to the
   binary format, a printer to the text format, and R from one table.
   *Done when*, for a corpus of modules built in unit tests, the encoder's bytes equal `wasm-tools parse` of the
   printed text, every module passes `wasm-tools validate`, and one with a struct, an exception, and a tail call
   gives the same output in wasmtime and in node.
3. **The backend's skeleton.** `--backend wasm`; code from the described IR for `Int`, `Bool`, `Char`, control
   flow, direct calls, tail calls, string literals, and the tests before trapping instructions (§2.10); output
   through the host, over WASI and in JavaScript; a unit is a module from this step on, the runtime a module of its
   own; the runner mode and its pending list.
   *Done when* the run goldens that need no more pass in both engines, a test of each row of §2.10 passes, loops
   whose tail calls reach their return through join points (§3.3) run a million times around in a worker's stack,
   and the native backends' goldens are unchanged.
4. **Aggregates:** tuples and options (§2.3), arrays (§2.4), strings, and records (§2.5) as far as the compiler
   has them, which is a module's record and one record type in the library (§10.1), with boxing at slot operations
   (§4.1), case binders that share the payload, and the options' value rules. A read of a type that may be proxied
   tests for the proxy and, finding one, fails as pending: nothing in the compiler makes one. Variants and records'
   views are pending.
   *Done when* their goldens pass, less those the pending list names.
5. **Closures:** the closure types, both entries, the closure signature, the call through a closure with its test
   and its fallback, static closures.
   *Done when* the higher-order goldens that are not polymorphic pass.
6. **The runtime, first part,** which the census makes the whole of this milestone's runtime (§10.1): descriptors
   built by a unit's initializer within §2.11's limits, instantiation and its memoization, `is` at a type
   parameter, the identity hash, printing as the REPL echoes, exceptions with the uncaught report.
   *Done when* the goldens for printing and for exceptions pass with the C runtime's output, less tracebacks' frames.
7. **Polymorphism:** descriptor parameters, and the three plans the compiler has (§10.3): `box`, `unbox`, and
   `adapt`, with the thunks `ir/thunks` makes for it. Own views, view maps, proxies, and the other subtyping plans
   are pending, as are `auto` and `inspect`: `lib/dynamic`, the one unit with either, is linked and never called,
   and its two functions that use them are compiled to fail as pending.
   *Done when* the polymorphism goldens pass, less what step 1 marked pending; and, as the first
   point at which the backend can compile them, the stack that the compiler's large recursive functions use for
   each level of nesting is measured in baseline code and recorded (§6.2), without waiting for step 10.
8. **`Real` formatting and parsing in Quest** (§4.3).
   A subproject of its own, with its own risk: it is tested apart from the backend first, since the Quest code
   runs natively too, against the C runtime on the same inputs.
   *Done when* the goldens that print and read `Real`s pass byte for byte, and a test of values chosen for their
   difficulty (halfway cases, subnormals, the largest and smallest, negative zero, infinities, and some millions
   of random bit patterns) agrees with the C runtime, natively and on this target.
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
    self-compilation's time and peak memory, and a profile naming what boxes most (§2.4's `Word`s, the full-width
    integers of §9.5) and what the unneeded adapters of §3.2 cost.

    *The stack,* measured apart: the least stack with which the driver compiles one unit and a REPL-sized input in
    node with `--liftoff-only`, as a page's first inputs run, against a worker's 512 KB and a page's 1 MB (§6.2).

    *The heap:* natively the self-compilation peaks at 3.1 GB resident, and here every tuple is two objects. node's
    default heap limit will need raising (`--max-old-space-size`), or the build run as a process for each unit,
    interfaces first, which also gives back the parallelism that `os/process` cannot.

### 8.2. Milestone 2: The Interpreter in a Page

A checkpoint (decision 4).

11. **The session's entries and the JavaScript host** (§6.1, §4.4, §5.2), with recovery by replay (§6.3, §6.4); the
    interpreter's REPL transcripts in node against the wasm driver.
12. **The page:** the worker, the loader, the prompt; the interpreter's depth measured in a Chromium worker and
    recorded (§6.2). Checked by hand in a Chromium browser, the only kind promised for now.

### 8.3. Milestone 3: Each Interaction a Module

13. **The JIT:** an input is a unit, compiled in the session to a module, its bytes passed through the buffer and
    loaded by the host, linked to the driver's modules and to earlier inputs'. Redefinition in place
    ([repl.md](repl.md) §6) needs nothing new: the lowering already holds a binding that may be redefined in a box,
    a one-component `var` tuple that the input's record points to ([jit.md](jit.md) §3.2), which here is a
    `$tuple` of one slot; a later input reaches it through the record and stores to it. A failed input is not
    committed. The
    fingerprint check carries over, with the target in it. The JIT's transcripts in node, then by hand in the page.

### 8.4. Milestone 4: The Rest

In an order chosen then:

- `var` and `out` parameters (§2.6);
- the rest of `auto`, `inspect`, and `dynamic`;
- the mathematical functions in Quest (§4.3), and `real.format`;
- variants, records' views, bounded quantifiers, proxies, and the runtime they need: subtyping, `quest_convert`,
  view maps, the map of record tables (§10.1);
- the run suite's pending list worked down;
- whatever step 10's profile asked for: typed arrays (§2.4), adapters at polymorphic calls (§3.2), specialization
  on scalar type arguments (§4.1), flat tuples (§2.3);
- the page's size and start-up time, and merging modules (§5.1);
- Safari and Firefox, neither checked nor promised until then.

---

## 9. Step 0's Results (2026-11-13)

The probes are in `tools/wasm-probes/`: `gen.py` writes them as WebAssembly text, `build.sh` assembles them with
`wasm-tools`, `run.mjs` and `stack.mjs` run them in node 26.13 (V8), and `wt.sh` in wasmtime 50.0.1 with the
copying collector. Small integers are `i31ref`s and others boxes, as §2.2 has them. The machine was in use (load
averages 2 to 6), so the timings are indicative: node's are the best of five warm runs, each variant in a process
of its own, and repeated runs agreed within 5%; wasmtime's are one process each, compilation included.

### 9.1. Tuples (decision 1)

A tree of 2²¹ nodes, each a tuple of a kind (a small integer), a span, and two children, built and then walked,
summing kinds and spans. The span either fits 31 bits or is boxed, as a merged file's span is (`file * 2³² + d`).

| | V8: slot array | V8: flat struct | wasmtime: slot array | wasmtime: flat struct |
|---|---|---|---|---|
| build once, spans fit | 66 ms | 39 ms | 150 ms | 52 ms |
| build once, spans boxed | 83 ms | 75 ms | 100 ms | 118 ms |
| walk 10 times, spans fit | 86 ms | 104 ms | about 350 ms | about 180 ms |
| walk 10 times, spans boxed | 115 ms | 139 ms | about 420 ms | about 250 ms |

(wasmtime's figures are derived: its runs build five times, or build once and walk ten times.)

- **In V8, the slot array costs allocation and nothing else.** Building is 1.7 times slower when nothing else is
  allocated, and 1.1 times when one component in four is a boxed integer. Walking was not slower but 20% faster; I
  cannot explain that, and Argon's loop over one tuple measured the opposite (17% slower), so I take reads as about
  equal.
- **In wasmtime the flat struct is about twice as fast** at both, with exceptions that look like the collector's
  timing.
- **A boxed integer stored in a tuple costs 8 to 18 ns in V8** (the difference between the rows), in either layout.
  That is more than the second object costs (about 13 ns a node), and it is the price of decision "`i31` or a box",
  not of decision 1.

**Decision 1 stands** (confirmed by the owner, 2026-11-13).
The cost in V8 is a tenth to a third of a tuple's allocation and none of its
reads, against which stand one type for every arity, the runtime's access by a run-time index, locations without
dispatch, and no limit of arity. If step 10's profile shows tuples' allocation leading, flat structs for the common
small arities remain possible.

### 9.2. Arrays (decision 2)

A million elements, either all fitting 31 bits or all full-width (`i * 0x9E3779B97F4A7C15`, as a `Word` hash is).
First with the element type known to the code, as in the compiler's `Array(Int)` side tables; then through another
unit's generic `get` and `set`, as `collections/hashmap` reaches its `vector.T(word.T)` of hashes through
`collections/vector`. Inlining does not cross units outside a whole program ([ir.md](ir.md) §8.6), so the second is
how the compiler's vectors are used. "Typed" there is an `i64` store that the generic code finds by a cast of the
array's struct, boxing what it returns and unboxing what it is given.

| V8 | `eqref` elements | `i64` elements |
|---|---|---|
| known type: fill 20 times, values fit | 31 ms | 21 ms |
| known type: fill once, sum 100 times, values fit | 69 ms | 64 ms |
| known type: fill 20 times, full-width | 464 ms | 21 ms |
| known type: fill once, sum 100 times, full-width | 82 to 94 ms | 64 ms |
| through a unit: set all 20 times, values fit | 55 ms | 67 ms |
| through a unit: set all once, get all 50 times, values fit | 120 ms | 164 ms |
| through a unit: set all 20 times, full-width | 516 to 549 ms | 91 ms |
| through a unit: set all once, get all 50 times, full-width | 154 to 171 ms | 225 to 237 ms |

| wasmtime | `eqref` elements | `i64` elements |
|---|---|---|
| known type: fill 20 times, full-width | 0.33 s | 0.04 s |
| through a unit: set all 20 times, values fit | 0.06 s | 0.16 s |
| through a unit: set all 20 times, full-width | 0.42 s | 5.4 s |
| through a unit: set all once, get all 50 times, full-width | 0.23 s | 13.8 s |

- **For values that fit 31 bits the two are equal** where the type is known, and `eqref` is faster by 20 to 35%
  through a unit, where typed arrays pay the dispatch.
- **Storing a full-width value into an `eqref` array costs about 23 ns in V8,** against 1 ns into an `i64` array:
  the box outlives the store, so it is a write barrier and a survivor, not only an allocation. Reading it back
  costs little (0.2 to 0.3 ns more).
- **Through a unit, typed arrays box on the way in and on the way out.** The boxes die at once, which V8 makes
  cheap (4.5 ns a store), so stores are still 6 times faster than into an `eqref` array; but every read allocates,
  and reads are 1.4 times slower than from an `eqref` array, whose box was made once.
- **wasmtime's copying collector makes those short-lived boxes ruinous:** 13.8 s where `eqref` arrays take 0.23 s,
  since each collection copies the live array. Typed arrays would make the suite crawl there wherever a `Word`
  vector is read.

What the compiler stores full-width in arrays is its hashes: one store for each insertion into a hash map (a
rehash moves the boxes, and allocates none), and one read or more for each lookup. Typed arrays would save about
20 ns an insertion and lose about 1 ns a lookup. Its other full-width integers (spans, reserved symbol ids) are in
tuples, which decision 2 does not touch.

**Decision 2 stands** (confirmed by the owner, 2026-11-13).
Typed arrays win only on stores of full-width values, lose on every generic
read, add the invariant of §2.4, and are far worse in wasmtime. They would pay for `Array(Real)` and `Array(Word)`
used at a known type in a user's numeric program, which is milestone 4's question, and the struct around the store
keeps that door open.

### 9.3. Casts at Boundaries (decision 3)

A function of three reference parameters (a string, a tuple, an array) that reads a field of each, called 100
million times from another module: at precise parameter types, and at `eqref` with a cast of each at entry.

| | precise | `eqref` and three casts |
|---|---|---|
| V8 | 213 ms | 292 ms |
| wasmtime | 0.19 s | 0.33 s |

The three casts cost 0.8 ns a call in V8 and 1.4 ns in wasmtime, about a third of a call that does nothing else.
**Decision 3 stands.**

### 9.4. The Stack in Baseline Code, and Array Limits

A recursive function of 40 `i64` locals, each set and used once in turn, two values live across the call; the same
with the 40 steps sharing two locals; and a function with none. The deepest recursion before V8's `RangeError`:

| Where | Tier | no locals | 40 locals | 40 steps in 2 locals |
|---|---|---|---|---|
| node's main thread (984 KB) | baseline | 15,545 | 2,487 | 10,363 |
| | optimized (`--no-liftoff`) | 46,635 | 37,308 | 37,308 |
| a node worker, `stackSizeMb: 0.5` | baseline | 4,452 | 712 | 2,968 |
| | optimized | 13,356 | 10,683 | 10,683 |
| a node worker, `stackSizeMb: 1` | baseline | 12,644 | 2,023 | 8,429 |
| | optimized | 37,932 | 30,345 | 30,345 |

- **node with no flags gave the baseline figures exactly:** a first deep recursion runs entirely in baseline code.
- **A baseline frame is about 63 bytes and 8 for each local,** declared, whether or not it is live: 395 bytes with
  40 locals, 95 with two. An optimized frame is 21 to 26 bytes whatever the locals.
- **So a function of 40 locals reaches a fifteenth of its optimized depth, and reusing locals gives back a factor
  of four.** The printer's reuse of locals (§2.11) is required for the stack, not only for the limit of 50,000,
  and it should be aggressive: a local for each type, not for each variable.
- This confirms that the native figure cannot stand for the page (§6.2). With 0.9 KB of native stack for a level
  of the compiler's nesting, and baseline frames perhaps three to seven times an optimized frame's, a worker's
  512 KB is some 80 to 200 levels of nesting in a cold compiler, where the native compiler has thousands. Step 7
  measures it on the compiler's own functions.

The largest array each engine makes, by bisection:

| Element | V8 | wasmtime (copying collector) |
|---|---|---|
| `eqref` | 134,217,720 | 536,870,899 |
| `i64` | 134,217,720 | 268,435,449 |
| `i8` | 1,073,741,792 | 2,147,483,596 |

### 9.5. Besides

- **wasmtime's copying collector copies everything live at each collection,** so short-lived garbage beside a
  large live heap is very slow there (§9.2). The suite's programs are small. A self-compilation, with hundreds of
  megabytes live, is not, which is one more reason it runs in node (decision 13).
- **Full-width integers in slots are the cost to watch** (§9.1, §9.2): 8 to 23 ns for each one stored, in a
  compiler that natively allocates 57 million objects for one unit. Where the compiler makes such integers by
  packing two small ones (a merged file's span, a reserved symbol id), a pair of small integers would allocate
  nothing. That is a change to the compiler's source for step 10's profile to ask for, not a change to this design.

---

## 10. Step 1's Census (2026-11-13)

What the compiler uses, from two sources: its text (`questlang/` and `lib/`), and the described IR of each of its
175 units (the 174 modules of `questlang/` and `lib/`, and `driver/main`), dumped with
`quest compile --stop-after ir_described` and counted. The IR is each unit's own, compiled apart, as this target
compiles them. It holds 5,703 functions.

### 10.1. What the First Milestone Needs, and What It Does Not

| Feature | In the compiler's units | First milestone |
|---|---|---|
| tuples | 4,317 made, 34,795 components read | needed |
| options | 2,603 made, 3,070 `switch`es | needed |
| arrays | 2,213 made, 6,697 elements read, 2,752 stores | needed |
| closures | made at 5,517 sites, 5,146 of them capturing nothing; at most 11 captures | needed; the static closure of §3.1 is the common case |
| a module's record, and members read through it | 174 records, 4,097 `member`s | needed |
| other records | one type, `hashMap.Entry`, made at one site | needed, without views |
| exceptions | 837 `raise`s, 168 `try`s in 35 units | needed |
| type parameters | 3,599 type applications; 9,477 `box` and 6,752 `unbox` plans | needed |
| functions passed at generic types | 813 `adapt` plans in 85 units | needed (§10.3) |
| reads that may meet a proxy | 23,611 in 136 units | the test is needed; the proxy's path is pending, since nothing makes one |
| variants | none | pending |
| a record seen at a supertype (`record_view`), `variant_tags` | none | pending |
| `view`, `runtime`, `copy`, `cast`, `unproxy` plans | none | pending |
| bounded quantifiers | none | pending |
| `var` and `out` parameters, `@`, `var(e)` | none | pending, as planned |
| `auto`, `inspect` | one each, both in `lib/dynamic` (`new`, `be`) | pending: the unit is linked so that inputs can import it, and the compiler never calls it |
| `dynamic.copy`, `intern`, `extern` | externals of `lib/dynamic`; the interpreter has its own, in Quest (`values/dynamicjson`) | pending |

So the first milestone's runtime is much less than §4.2's list: descriptors and their instantiation, `is`, the
identity hash, printing, exceptions. Run-time subtyping, `quest_convert`, proxies, view maps, and the map of record
tables wait for milestone 4, where the run suite needs them. Steps 4, 6, and 7 are narrowed accordingly (§8.1).

### 10.2. `Real`

| Use | Where | First milestone |
|---|---|---|
| reading a literal: `strutil.tryToReal` (`quest_strutil_to_real`) | the lexer, once | needed (step 8) |
| printing: `conv.real`, `stringBuilder.appendReal` | the dumps of tokens, syntax, typed syntax, and IR; `values/json`; `values/model` | needed (step 8) |
| arithmetic and comparison | 21 primitive operations in four units: `lib/real`, the interpreter's primitives and builtins, `values/dynamicjson` | needed: instructions, with the NaN tests |
| bits of a `Real` (`word.fromReal`, `toReal`) | the native backends' constants | needed: one instruction each |
| `real.format` (a style and a digit count) | only the interpreter's builtin for an interpreted program's call | pending; a third formatter to write, in milestone 4 |
| `sin`, `log`, `exp`, and the rest | only the interpreter's builtins | pending (§4.3) |

The compiler's own paths use no mathematical function and no `real.format`, so step 8 is the lexer's reader and
`conv.real`'s printer, as planned.

### 10.3. Adapters Are Already Made

The plan expected a function with a scalar parameter, passed where generic code has a type parameter, to be called
through its uniform entry (§3.2), and named it the cost the first milestone's running time rested on. The IR shows
otherwise. `hashMap.new(:Int :Bool intEqual hash.int)`, in `ir/represent`:

```
let %114: Fun(n: Int): word.T = member hash.int
let intEqual.2: Fun(k1: K k2: K): Bool = closure qa_adapt.5 {}
let %115: Fun(k: K): word.T = convert(%114, adapt by qa_adapt.6)
let foundIds.1: hashMap.T(Int Bool) = call hashMap.new [descriptor(Int), descriptor(Bool)](intEqual.2, %115)
```

and the thunk is `fun qa_adapt.1 {orig}(k: K): word.T { let k' : Int = convert(k, unbox); return call orig(k') }`.
The pass's `adaptPlan` makes one whenever a parameter or the result has a plan of its own, and `box` and `unbox`
are plans. So the generic code is handed a closure of its own signature, and on this target calls its native
entry; the `Word` comes back as an `i64`.

The same rule wraps `hash.string` and `stringOp.equal`, whose pointers C boxes. This target would not need those
(§3.2).

### 10.4. Sizes

| Measure | Value | Against |
|---|---|---|
| variables of a function: median, 90th and 99th percentile | 10, 85, 503 | |
| the most variables in one function | 1,450 (`ssa/statics`'s `descriptorData`); eleven others over 1,100 | the limit of 50,000 locals |
| captures of the widest closure | 11 | 10,000 fields |
| distinct externals named | 174 | Opus's count of `lib/`'s values |

**The large functions are the stack's problem, not the limit's.** Those with over a thousand variables are the
compiler's great `case`s over a form, and several are the recursive walks themselves: the IR verifier's
`statement` (1,416), `ir/clone`'s `copyOp` (1,368), `ir/describe`'s `opTypes` (1,374), the lowering's `valueForm`
(1,158), `types/model`'s `rebuild` (1,176), and the interpreter's `evalExpr` (1,181). At 8 bytes for each local in
baseline code (§9.4), a frame of `evalExpr` with a local for each variable would be 9 KB, and fifty levels of it a
worker's whole stack. Each arm of such a `case` uses a few variables, so locals shared by type across arms bring a
frame down to the widest arm's. If that is not enough, the printer can put a large `case`'s arms into functions of
their own, so that a frame holds only the arm taken. Step 7 measures which.

### 10.5. The Host

- **`os/process`** is used by `build/workers`, which spawns a driver for each batch of a parallel build, and by
  the interpreter's builtins. With this backend the compiler spawns nothing else: it writes the modules itself,
  with no assembler, C compiler, or linker. A serial build never calls it.
- **`os/code` and `os/value`** are used by `driver/interrupts` and the native JIT (`jit/loader`, `jit/session`);
  **readline** by `driver/repl` and the interpreter's builtins. None is on the path of a compilation.
- **`os/fileStats`** is used by the build's test for staleness and by the paths' lookups, and is needed (§4.4).
- **Externals called while units initialize:** a search of every initializer's own statements finds 34 distinct
  callees, nearly all the library's constructors (`hashMap.new`, `hashMap.insert`, `vector.new`) filling tables.
  Two reach the host: `system.getEnv`, which the host has, and `code.symbol` in `driver/interrupts`, which §4.2
  already answers. The search does not follow calls into functions, so step 9's first run is the real test.

### 10.6. Identity Hashes and the Fixed Point

`hash.identityHash` is called where Fable's plan counted it (R9 there): on a substitution in `ir/represent`, on a
builtin, and on interpreted values. Its values differ on this target, a counter's where natively an address's, and
the fixed point of step 10 needs the compiler's output not to depend on them. It does not:

- **In `ir/represent`** the hash's digits are part of a string that keys the set of plans in progress, which is
  only asked, added to, and deleted from. It needs distinct live objects to have distinct hashes, which a counter
  gives.
- **Everywhere,** `collections/hashmap` and `hashSet` iterate in insertion order (`keys`, `values`, `entries`,
  `iter`, `fold`), never in the order of hashes, so no listing the compiler makes from a map depends on a hash.
