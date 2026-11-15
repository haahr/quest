# Plan: The REPL in a Browser, on WasmGC

The goal: the self-hosted REPL running in a browser page. A new backend of the self-hosted compiler, `wasm`, compiles
Quest to WebAssembly with garbage collection (WasmGC): Quest's values are the engine's structs and arrays, and the
engine's collector is Quest's. The compiler is compiled by that backend, runs in the page, and in the end compiles
each interaction to a module that the page loads into the session, as the arm64 JIT loads machine code
([jit.md](jit.md)).

**Status: decided** (2026-11-12), **being built** (from 2026-11-13). This is the plan to build from. It is a hybrid of four plans written
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
census of what the compiler uses. Milestones 1, 2, and 3 are reached (2026-11-14): the compiler compiles itself in
node, the REPL runs in a page, and each input there is compiled to a module and run as compiled code (steps 13 and
14). Milestone 4's steps (§8.4) are drafted, with the owner's answers (§8.4.1), and are being built.

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
follows it. Natively `ssa/passes/tailcalls` finds these on the SSA, which this backend does not have, so it repeats the
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

The shared passes, `repr/layout`, and the native backends' goldens are unchanged. Today's represented IR has no
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

- **The base**, beneath both, is not Quest: the module `questlang/wasm/runtime` builds from the model (steps 3 to 6).
  It holds what Quest cannot say: the memory and the host's imports (§4.4), the exception tag and the built-in
  exceptions, `Int`'s boxing, and copying bytes to and from strings. It shrinks to that as the core grows (§4.5).
- **The core** imports no unit but the intrinsics, not even the library's helpers, and the backend checks it (§4.5). It holds `is`, the identity hash, descriptors and their
  instantiation, run-time subtyping, conversion, proxies, view maps, and the map of record tables. Its memo tables are written out over arrays, as the C runtime's are, not taken from
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
the part of `repr/externals`, and a test checks that it covers `lib/`. `os/process`, `os/code`, `os/value`, and
readline have no counterpart; their externals raise their module's error, with one exception. `code.symbol`
answers that there is no such symbol, as it does natively for a name the binary lacks:
`questlang/driver/interrupts` calls it at its top level, `driver/repl` imports that unit, and initialization runs
every imported unit's top level, so a `code.symbol` that raised would end the driver before it began. Step 1
lists every external the driver calls at a top level.

### 4.5. The Intrinsics

*Written 2026-11-13, after steps 6's exceptions and 9's units, and revised after its review the same day; the core
is built on it.*

*As built (2026-11-14), the design below with these departures:*
- **No `wasm/intrinsics` interface.** An intrinsic is an external named `wasm.NAME`, which each of the runtime's
  unsound modules declares itself, at the types it uses it at: `let toInt(x: core.Any): Int = external
  "wasm.fromAny"`. The backend compiles the external's call in place, by its name, from its arguments' types and
  its result's. `toAny` and `fromAny` take their type from the declaration, so the rule of point 3 below holds
  unchanged, and none of the build's changes for an interface without a module were needed. `Any` is
  `external "eqref"`, which the backend holds as an `eqref`.
- **The set built** is what printing needs: `same`, `toAny`, `fromAny`, `tupleCount`, `tupleSlot`, `arrayCount`,
  `arraySlot`, `recordField` (through the view's table), `optionTag`, `exceptionName`, and the base's `decimal`,
  `hex`, `escaped`, `charString`, and `put`. The table below stays the list to draw on.
- **Two units, under `runtime/wasm/`:** `wasm/core` makes descriptors (`base`, `newDesc`, `setPart`, `setText`)
  and instantiates templates (`instantiate`, memoized); `wasm/print` writes values by them (`show`, `echo`). The
  driver builds both with `runtime/` on the include path and preloads them before every other unit, and `-o`
  writes each unit's module beside the program, with `TARGET.units` naming them in order.
- **The uncaught report's hook is the program's `_start`,** not a field of the core: `$raised` carries the
  payload's descriptor, and `_start` writes the payload with `wasm/print`'s `show` and passes the text to the
  base's `uncaught`. Every exception a program does not catch reaches its `_start`, the inits of its units
  included.
- **Not yet built:** the backend's check that the core imports nothing but the library's members it compiles
  itself (the core imports `string` for those), and `--wasm-checked`.

The core (§4.2) is Quest that must reach what no Quest type exposes: a value's kind, an object's slots and hash, a
string's bytes. It does so through one unsound interface, `wasm/intrinsics`, whose members the backend compiles at
each call. The core is written against it, and so are descriptors, printing, and later the library's externals.
Changing it later means changing all of them.

**An interface with no module.**
- `wasm/intrinsics` is `runtime/wasm/intrinsics.int.quest`, an unsound interface ([modules.md](modules.md) §4.4).
  Only an unsound module may import it.
- No module implements it. The backend compiles each call of one of its functions to an instruction sequence, or to
  a call of the base, at the call site, as it already compiles `lib/`'s members it knows (step 3). A call costs what
  the instructions do.
- Three places that assume an interface has a module learn that this one has none: the engine's staleness test,
  which finds no object to compare; the driver's ordering of the units it preloads, which skips it among a
  manifest's imports; and linking, which links nothing for it.
- Nothing native compiles it or the core: `runtime/wasm/` is the wasm backend's alone, as `runtime/*.c` is the
  native backends'. A native build that meets an import of `wasm/intrinsics` reports it as an error naming the
  importer, rather than failing to link.

**Its types are the engine's references.**
- They are abstract types with no bound, and the backend holds any such type as an `eqref` (§3.2). So declaring
  them is all they need:
  - `Any`, every value as a slot holds it;
  - `Slots`, `$slots`;
  - `Bytes`, `$bytes`.
- A value crosses into and out of `Any` by two intrinsics, `toAny(A::TYPE x: A): Any` and
  `fromAny(A::TYPE x: Any): A`.
- The backend compiles each as §2.2's box or unbox **for the type argument at the call**, which the core always
  writes out. So no descriptor is needed: the core stays monomorphic, as §4.2 requires. A call whose type argument
  is a type parameter is a compile-time error in an unsound module, since only the core uses them.

**The first set** is what the core's first part needs (step 6). Each is one to four instructions:

| Group | Intrinsics |
|---|---|
| identity | `same(a b: Any): Bool` (`ref.eq`), `hashOf(x: Any): Int` and `setHash(x: Any h: Int): Ok` (an `$obj`'s field) |
| kinds | `isSmall`, `isBoxedInt`, `isTuple`, `isOption`, `isString`, `isArray`, `isRecord`, `isClosure`, `isException` (each `x: Any`, a `ref.test`) |
| small values | `smallValue(x: Any): Int` (`i31.get_s`), `small(n: Int): Any` (`ref.i31`, for a known range) |
| slots | `slotsOf(x: Any): Slots` (a tuple's, option's, array's, or payload's), `slotCount(s: Slots): Int`, `slot(s: Slots i: Int): Any`, `setSlot(s: Slots i: Int v: Any): Ok`, `newSlots(n: Int): Slots` |
| aggregates | `optionTag(x: Any): Int`, `newTuple(s: Slots): Any`, `newOption(tag: Int s: Slots): Any`, `newArray(s: Slots): Any` |
| records | `payloadOf(r: Any): Any` and `dictOf(r: Any): Any` (a `$recBox`'s), `dictSlot(d: Any i: Int): Int`, `layoutOf(p: Any): Any` |
| strings | `bytesOf(s: String): Bytes`, `byteCount(b: Bytes): Int`, `byte(b: Bytes i: Int): Int`, `setByte(b: Bytes i: Int v: Int): Ok`, `newString(n: Int): String` |
| exceptions | `exceptionName(e: Any): String` |
| the host | `put(fd: Int s: String): Ok`, `fatal(message: String status: Int): Ok` (the base's) |

**What an intrinsic misused does.** The core is unsound, so a wrong call is the core's bug, not a program's.
- `fromAny` at the wrong type, and `slot` or `byte` past the end, trap; the host reports a trap as an internal error.
  The backend's `--wasm-checked` compiles each cast as a `br_on_cast` and each index as a test, failing with a report
  that names the intrinsic and its caller, for debugging the core. It is off by default.
- `newSlots`, `newString`, and `newArray`'s sizes are tested against §2.10's limits like any allocation, so a size
  too large is the fatal out-of-memory error and not a trap.

**What the core may import: the intrinsics, and nothing else.** The core is beneath the library: once step 9
compiles the library to WebAssembly, every library unit imports `wasm/core`, so the core can use no library unit's
Quest code. That includes the helpers the rest of the compiler leans on (`maybe`, `vector`, `strutil`, `hashMap`):
the core uses `case`, arrays, and loops instead. It reaches the host through the intrinsics' `put` and `fatal`, not
`writer`, and raises the base's built-in exceptions by name through `wasm/intrinsics`' exception members (`int.error`
and the rest, declared there as the base's globals).
- The passes may add imports a module never wrote (`pipeline.implicitImports`). When the backend compiles the core,
  it checks the unit's whole import list, implicit imports included, and reports any import but `wasm/intrinsics`
  with the construct that caused it.

**Compiling the core is a mode of the backend.** Every other unit the backend compiles imports `wasm/core`, and some
constructs compile to calls of it: `is` at a type parameter, instantiation, conversion, and a raise's payload when it
needs a descriptor. The core cannot import itself, so when the backend compiles a unit of `runtime/wasm/core` it
adds no such import, and each of those constructs is a compile-time error there. The core is monomorphic (§4.2), so
it writes none of them: its `is` is at known types, and the payloads it raises are strings.

**Descriptors are Quest values, as tuples.** A descriptor (`QTypeDescriptor`'s counterpart) is a value of a tuple
type the core defines, its kind first, and not a type in R.
- R lists "the descriptors" (§2.11) because code would tell them apart by a cast; nothing does. Only the core makes
  and reads them, and a record's payload holds its own as an `Any` (`$record`'s layout field).
- A tuple and not a record, because a record held in a slot is a `$recBox` over a payload read through its dict
  (§2.5): two indirections on paths that polymorphic `is`, hashing, and echo take for every value. A tuple's field is
  a slot of its `$slots`, at a position fixed by its definition, so compiled code may later read a descriptor's kind
  inline without knowing a record's layout.
- A recursive type's descriptor is cyclic, so the slots that point at descriptors are `var` fields, filled in after
  the descriptors are made.
- A unit's initializer makes its static descriptors (`StaticData`) by calling the core's constructors: in functions
  of bounded size, within §2.11's limits, and before its top level runs.
- **A unit exports its types' descriptors** as globals, `descriptor.NAME`, beside `record.payload` and
  `record.dict`: a unit whose descriptor mentions an imported type imports the other unit's. That is part of each
  unit's ABI (§5.3).
- The core's instantiation is memoized by the descriptors it is given, so `List(T)` instantiated in two units is one
  descriptor, and run-time subtyping can compare descriptors by identity.

**How compiled code reaches the runtime.**
- The core is a unit, `wasm/core`, imported by every unit the backend compiles except its own, and preloaded after
  the base and before the library.
- `is` at a type parameter, instantiation, and conversion become calls of the core's functions by name, as calls of
  any unit are (§5.1).
- **Echo and printing are the upper layer's** (§4.2), since they need `Real`'s formatting and `util/bignum`. Echo
  compiles to a call of the upper layer, which a unit that echoes imports; a unit the upper layer imports must not
  echo, which the backend reports with the import's path.
- **The uncaught report reaches upward through a hook.** The base reports an uncaught exception, and a payload is
  printed by the upper layer above it. The core holds a `var` field for the printer, which the upper layer's
  initializer sets; the report uses it when set, and the base's plain form (the exception's name and the site, as
  now) when not, as when a library unit's initializer raises before the upper layer's has run.
- The driver builds the runtime's units from `runtime/wasm/` with `--backend wasm` into the build directory, once,
  as it builds the library's. A release will carry them built.

**How the core is tested.** It runs nowhere but under wasm, so the run goldens alone would find its bugs late and far
from their cause. Step 6 adds `tests/self-hosted/wasm/core/`: programs that call the core directly and print what it
returns, in both engines, for descriptors of a recursive type and of an instance, the identity hash, run-time
subtyping, and conversion. They are run goldens of their own, against expected text rather than native output,
since nothing native can run them.

**What it leaves for later.**
- Calling a closure held as an `Any`, by its uniform entry, which proxies' and adapters' conversions need
  (milestone 4).
- Reals' bits, which §4.3's formatting needs: `bits(r: Real): Int` and its inverse join with step 8's connection.
- More of either kind, added as the core needs them, each documented in the interface with its instructions.

**The review settled** (2026-11-13):
1. **Descriptors as Quest values** rather than R types, which drops them from the ABI's type group; as tuples, not
   records.
2. **The base kept** as a hand-built module beneath the core, rather than every non-Quest operation becoming an
   intrinsic.
3. **`toAny` and `fromAny` at the static type argument** as the only polymorphism the core uses.
4. **The core imports only the intrinsics**, checked when it is built; echo and printing are the upper layer's, and
   the uncaught report reaches them through a hook.

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

  Both are exact arithmetic, slow and plain, not one of the fast algorithms (Ryu, Grisu, Eisel-Lemire), whose
  subtlety is in avoiding big integers. Being exact, they give libc's digits, which the shared goldens check. A
  real's bits are `word.fromReal` and `word.toReal`, one instruction each. The work does not wait for the backend:
  it runs natively, so it is written and tested against libc first, and step 8 connects it.

  *Built 2026-11-13* as `lib/util/realconv` (step 8). It does not use `util/bignum`: that unit imports
  `util/strutil` and `conv`, whose real conversions this one provides on this target, so the imports would make a
  cycle. It has its own natural numbers instead, which need only a number times a small one plus a small one, a
  shift, a subtraction, and a comparison. Their limbs are below 2³⁰, so that in an array they are `i31ref`s and
  never boxed. It imports only `word`, `string`, and `ascii`, and uses no type parameter, so it can also be part
  of the core runtime (§4.2), which cannot instantiate descriptors. Reading back a candidate is not a second
  parse: the candidate reads back when it lies between the midpoints that separate the real from its neighbors.

  *Not taken:* a helper compiled from C, or JavaScript's `Number`. The owner chose against the first for the
  toolchain it adds to the build, and the second is absent in wasmtime, where the suite runs.
- **The mathematical functions, after it.** The compiler calls none of them. They are ported from a portable
  library of known quality (musl's or FreeBSD's `msun`) to Quest: about thirteen functions of `f64` arithmetic and
  bit operations. Until then their externals fail with a message. Their results are the same on every WebAssembly
  engine and may differ from Apple's libm in the last bit (Argon measured 1 to 2 units, §3.5 there), so goldens
  that print such results are recorded for this target or exempt (§7).

  *Built 2026-11-15* as `lib/util/realmath` (step 19): msun's functions ported line for line, each of C's
  expressions braced in C's order of evaluation, since Quest's operators associate to the right. Where msun returns
  NaN the port raises `real.error`, as the C runtime's wrappers do after libm. Built natively from FreeBSD's sources
  and compared on 229,905 values, the port's results are msun's to the bit. Against Apple's libm they agree within
  1 ulp, or 2 for `tan`, the hyperbolic functions, and `pow`; the exception is msun's least accurate case, `pow` of
  an x within 2⁻²⁰ of 1 to a power beyond 2³¹, hundreds of ulps from libm's. `real.format` is `realconv.format`,
  printf's `%e`, `%f`, and `%g` over the exact digits. No golden needed recording for this target: those that print
  the functions' results print 12 significant digits. The backend calls both units as it calls `realconv`'s other
  functions, and imports `util/realmath` into every program beside `wasm/print`, for `^^`. The two units take `real`
  only as externals, which compile to instructions, since `real`'s own module calls them.

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
instantiation; step 12 measured what that costs at start-up: about a fifth of a second to compile the 199 modules
in a Chromium page, and some three quarters of a second for the driver's initializers, run cold. The IR's whole-program build is not
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
imports the compiler's own units is some 150 of them. Step 12 measured the first input's latency and decided: the
`.qi` files are not shipped. A first input that imports eleven of the library's modules took 364 to 381 ms in four
sessions without them, and 369 to 397 ms with them, the interpreter's own elaboration and loading of the modules
being what costs. The question returns with milestone 3, whose compiler reads `.qi` files, and with inputs that
import more.

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

With the JIT, evaluating is still one request (step 13, the owner's choice in place of three): the driver compiles
the input, gives the host its module's bytes, and calls the host to load the module and to run it. The host runs the
input's code inside its own function, which catches an engine's stack overflow or a trap, so an error caught there
unwinds only the input's frames and those of the library and runtime it called (§6.3); the driver's frames below
are intact, and the input fails as if it had raised.

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
  call whose body nests calls (Opus), so some 80 to 250 calls in a worker. Measured in step 11, with locals
  reused: 753 calls of a simple body and 175 of a nested one in a worker's 512 KB, so a session sets the limit to
  150. In a Chromium worker (step 12): 734 and 169.
- **Compiled code does:** about 100 bytes for a small function's call in baseline code and about 30 when
  optimized, and about 8 bytes more for each live local in either (Opus's author, in V8: 580 bytes with 64 live
  locals, 2.1 KB with 256). Measured in a Chromium worker with the JIT (step 14): an input's recursion that is not
  in tail position (`1 + down(n - 1)`) reaches 5,297 calls, the driver's frames below it included, and further
  overflows in the input's own code, rolled back with no replay.
- **The compiler, cold, fits ordinary inputs** (step 14): the transcripts and every input measured compiled in a
  new worker, cold. What does not fit is the front end's nesting, shared with the interpreter: a chain of 498
  additions is the longest a new session's first input takes, about 1 KB of stack a level, as natively (0.9 KB),
  and both modes stop at the same length. Longer chains overflow in the compiler and replay (§6.3).

So the interpreter in a page is a checkpoint (decision 4): it shows the driver running in a page, with shallow
recursion, and the JIT follows at once as the REPL people use. The interpreter is not rewritten for this target.
Steps 11 and 12 measured its depth in WebAssembly, which the native figure only estimated.

Tests under node constrain the stack to a browser's (`--stack-size`, or a worker's `resourceLimits`), or they pass
where a browser fails.

### 6.3. When the Stack Overflows (decision 10)

No handler in a module sees the overflow: wasmtime traps, and V8 gives JavaScript a `RangeError`. The Quest code
that would roll a failed input back does not run. The host catches the error at the entry, and what it does depends
on what was running:

- **An input's compiled code:** the session's bindings change only when an input commits, so the host's function
  that ran the input gives the driver the overflow, the driver rolls the input back as it does a raise, reporting
  `stack.overflow`, and the session goes on. What the input had already
  done to earlier inputs' state stays done: a store to an earlier `var`, to an array's element, to a string, as
  after a raise today ([jit.md](jit.md) §3.2). This is better than native, where the session ends.

  The overflow lands in the deepest frame, which may be the runtime's, part way through an update of one of its
  shared tables (the descriptors' memo, the map of record tables): a point where no Quest raise can occur, and
  nothing rolls it back. So the core runtime (§4.2) counts, in a global, the updates of shared tables in progress,
  and makes each update visible by one final store where it can. The host reads the count after catching the
  error: zero, and the input is abandoned as above; not zero, and the session is replayed as below, once the
  request ends. A user's own
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
  once replay from source is seen to be slow. *Decided in step 14: not taken.* With the JIT, an overflow's replay of
  18 committed inputs, each compiled again, takes 64 to 141 ms in Chromium (about 4 to 8 ms an input), and an
  interrupt's, which starts a new worker, 106 to 689 ms, as the interpreter's, 72 to 729 ms: a new worker's start,
  the driver's initializers run cold, is most of it, and compiling the inputs again is not.
- **Under wasmtime or node, a program:** the run ends, as compiled code's overflow ends it natively.

A count at each function's entry that raises a catchable `stack.overflow` first (Fable's A8) is a later addition.

### 6.4. Interrupts (decision 11)

A running call cannot be stopped from outside, only its worker ended. The page ends the worker and replays, as
§6.3 does. The page needs no cross-origin isolation, so any static host can serve it.

*Found in step 13:* V8 cannot end a worker that runs WebAssembly's tail calls in a loop (`return_call`), as it
checks for termination at loops' back edges and at no tail call: an endless loop ends at once, and a function that
calls itself forever in tail position never does, node's process kept from exiting too. So a compiled input that
recurses forever in tail position cannot be interrupted. The remedies are the backend's, to compile a function's
call of itself in tail position as a loop (the engine then checks it), or a count of calls at each function's
entry. *Built in step 20,* the first: a function's call of itself in tail position sets its parameters and
branches to a loop around its code, and the page's interrupt ends such a recursion at once. **Mutual recursion is
not covered:** two or more functions that call each other forever in tail position still do so by `return_call`,
which V8 does not check, so an interrupt cannot end the worker, and the user must reload the page. Covering them
takes the second remedy, a count at every function's entry, at a cost in every call.

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
   *Done 2026-11-13:* `questlang/wasm/` has `model` (modules as data), `ops` (the operations whose immediates are
   all integers, one table for both formats), `encode`, `printer`, and `runtimeTypes` (R). The corpus is the
   questlang test `wasm_encode`, its golden the text and, in comments, the bytes; `tests/python/test_wasm.py` checks
   it. The encoder writes the name section as `wasm-tools parse` does, so the engines' traces name functions, and
   block and function types of several results by index, for `unbox` (§4.1). R holds only the types §2 defines
   in full; the steps that define the rest add them (`runtimeTypes`' header lists which).
3. **The backend's skeleton.** `--backend wasm`; code from the described IR for `Int`, `Bool`, `Char`, control
   flow, direct calls, tail calls, string literals, and the tests before trapping instructions (§2.10); output
   through the host, over WASI and in JavaScript; a unit is a module from this step on, the runtime a module of its
   own; the runner mode and its pending list.
   *Done when* the run goldens that need no more pass in both engines, a test of each row of §2.10 passes, loops
   whose tail calls reach their return through join points (§3.3) run a million times around in a worker's stack,
   and the native backends' goldens are unchanged.
   *Done 2026-11-13, but for three rows of §2.10:*
   - **Code:** `questlang/wasm/codegen` compiles a program's unit to a module that imports `quest.runtime` and
     exports `_start`. The runtime is `questlang/wasm/runtime`, built from the model until step 6 writes it in Quest.
   - **Running:** `--backend wasm` runs the program in wasmtime, or in node with `--wasm-engine node`
     (`runtime/wasm/run.mjs`), and `--stop-after codegen_wasm` prints its text. Until step 9 the program is its
     only unit, and the library's members it uses go through a table, not the engine's build.
   - **References:** every reference is an `eqref` for now, cast where it is used. The precise locals of §3.2 come
     later.
   - **Run goldens:** the modes `wasm` and `wasm-node` pass the same 15 in both engines.
     `tests/self-hosted/pending-wasm.txt` lists the other 282, each under the step that adds what it needs; no
     failure is a wrong result.
   - **Its own tests:** `self-hosted/wasm_programs` runs tail recursions, self and mutual, from one to three million
     deep, and division's row of §2.10, in wasmtime and in node's default stack, against the arm64 backend's output.
     Its `.wat` files are the backend's first text goldens.
   - **Tail position through join points:** the backend finds it, but in these programs no such join is left. The
     simplifier turns a jump to a join point that only returns into a return.
   - **The other rows of §2.10** wait for their types: Real to Int for step 8's connection, an index and a size to
     allocate for step 4's arrays.
4. **Aggregates:** tuples and options (§2.3), arrays (§2.4), strings, and records (§2.5) as far as the compiler
   has them, which is a module's record and one record type in the library (§10.1), with boxing at slot operations
   (§4.1), case binders that share the payload, and the options' value rules. A read of a type that may be proxied
   tests for the proxy and, finding one, fails as pending: nothing in the compiler makes one. Variants and records'
   views are pending.
   *Done when* their goldens pass, less those the pending list names.
   *Done 2026-11-13:*
   - **What the code generator adds:**
     - Tuples, and unboxed tuples as several results.
     - Options made by case and by ordinal, with `?`, `!`, `ordinal`, `switch` with shared binders, and `is` by
       the options-as-values rules.
     - Arrays, with the index, count, and size tests of §2.10.
     - `string`'s externals.
     - Records: two values natively, boxed in `$recBox` in a slot, and their views' tables are immutable globals.
   - **R** gains `$record`, `$dict`, and `$recBox`. The record's layout field is an `eqref` until step 6's
     descriptors.
   - **Run goldens:** the modes pass 40, the same in both engines, and 257 remain pending under later steps. None
     waits on step 4.
   - **Its own test:** `tests/self-hosted/wasm/aggregates.quest` runs in both engines against the arm64 backend. It
     leaves out `is` on records, which arm64 does not compile and this backend does.
   - **Caught on the way:** `conv.char` and `conv.string` quote and escape, which step 3's mapping missed.
   - **Rows of §2.10:** an index and a size to allocate are now tested before the instruction. Real to Int still
     waits for step 8's connection.
5. **Closures:** the closure types, both entries, the closure signature, the call through a closure with its test
   and its fallback, static closures.
   *Done when* the higher-order goldens that are not polymorphic pass.
   *Done 2026-11-13:*
   - **Entries:** every function's native entry takes its closure first, as `(ref $clos)`. A direct call passes the
     known closure when the function captures something, else a shared closure it never reads.
   - **Types:** `$closU(n)` and `$closS` are made for each signature, and each function's own final type adds its
     captures as mutable fields, so that a recursive value's (`sLetRec`) are filled in after it is made.
   - **Closures:** a function that captures nothing has a static closure, an immutable global. Uniform entries
     unbox, call, and box, and are the native entry itself when the signature is uniform.
   - **Calls through a closure** test for `$closS` and call its native entry, else box and call the uniform one,
     as tail calls where they are in tail position.
   - **Built-in operators as values** (`{+}`) are static closures over functions of their own, `Int`'s now and
     `Real`'s with step 8.
   - **Run goldens:** the modes pass 44, the same in both engines; 253 are pending, none under step 5.
   - **Its own test:** `tests/self-hosted/wasm/closures.quest` is checked in both engines against the arm64
     backend, a tail call through a closure a million times around among it.
6. **The runtime, first part,** which the census makes the whole of this milestone's runtime (§10.1): descriptors
   built by a unit's initializer within §2.11's limits, instantiation and its memoization, `is` at a type
   parameter, the identity hash, printing as the REPL echoes, exceptions with the uncaught report.
   *Done when* the goldens for printing and for exceptions pass with the C runtime's output, less tracebacks' frames.
   *Done 2026-11-14,* exceptions first (2026-11-13) and then descriptors and printing:
   - **R** gains `$exception` (hash and name) and `$raised`, a raised exception's state: the exception, its
     payload, the site, and how the report writes the payload.
   - **The runtime:** the built-in exceptions are its exported globals. `raise` throws the one tag with the state,
     and `uncaught` writes the C runtime's report less the frames.
   - **A `try`** is a `try_table` that catches the tag. The handler tests the state with `is`, which compares
     exceptions (`exceptionOf`), and raises it again with `throw`, so its site is kept.
   - **No tail call inside a `try`:** a call in tail position inside a `try`'s body is not made a tail call, since
     leaving the `try_table` would leave its handler.
   - **Descriptors** are values of `wasm/core`'s `Desc`, a tuple (§4.5). A unit whose code uses any imports the
     core's constructors, and a function it runs first in its initializer makes each of its static descriptors
     (`staticdata`'s forms) as a global: the base ones, then each collected one with its parts unset, then its
     parts, so that a recursive type's closes.
   - **Echo** of a value whose type needs a descriptor calls `wasm/print`'s `echo` with the value as a slot holds
     it.
   - **An uncaught payload** that needs a descriptor is written by `wasm/print`'s `show`: `$raised` carries the
     descriptor, and the program's `_start` passes the text to the base's `uncaught`.
   - **Run goldens:** the modes pass 77 and then 97, the same in both engines; the tests left under step 6 went
     to the steps that add what they need (a record view, a variant, a `Real`, `reader`).
     `tests/self-hosted/wasm/exceptions.quest` checks exceptions in both engines against arm64, and
     `polymorphism.quest` an uncaught payload written by its descriptor.
7. **Polymorphism:** descriptor parameters, and the three plans the compiler has (§10.3): `box`, `unbox`, and
   `adapt`, with the thunks `ir/thunks` makes for it. Own views, view maps, proxies, and the other subtyping plans
   are pending, as are `auto` and `inspect`: `lib/dynamic`, the one unit with either, is linked and never called,
   and its two functions that use them are compiled to fail as pending.
   *Done when* the polymorphism goldens pass, less what step 1 marked pending; and, as the first
   point at which the backend can compile them, the stack that the compiler's large recursive functions use for
   each level of nesting is measured in baseline code and recorded (§6.2), without waiting for step 10.
   *Built 2026-11-14, but for the measurement:*
   - **Signatures:** a function type's closure signature has a descriptor, an `eqref`, for each of its
     quantifiers' type parameters, before its value parameters; a type-only function's is the descriptors and its
     result's parts.
   - **Descriptor parameters:** a function's callers pass those of its own quantifiers; those its closure supplies
     (`typeArgs` of the closure made) are fields of its own closure type, after the entries and before the
     captures, which its prologue reads. A closure that supplies any is never static.
   - **Calls** pass the call's descriptors before the arguments, directly, through a closure's either entry, and
     to another unit's export; a type application (`opTypeApp`) is a call with descriptors alone, its result
     boxed or unboxed as its plan says.
   - **Adapters** (`adapt`, made by `ir/thunks`): a closure of the adapter that captures the closure it adapts,
     which its prologue binds to the adapter's environment.
   - **Descriptors at run time:** a descriptor variable is its local, and a template instantiated by the core's
     `instantiate`, memoized.
   - **`is` at a type parameter** compares the values as slots hold them: the same reference, or two boxed `Int`s
     of one value. An `unproxy` plan changes nothing, since nothing this backend compiles makes a proxy.
   - **Tests:** `tests/self-hosted/wasm/polymorphism.quest` calls generic functions of another unit
     (`wasm/units/gen`), which the program cannot specialize, and gets closures that capture descriptors.
   - **Run goldens:** none of those listed under step 7 waits on it any more; each went to what it does wait on:
     20 to milestone 4 (variants, views, `var` parameters, `auto`), 3 to step 8, and 15 to step 9's library.
   - **The measurement** needs the compiler's units compiled, and so the library: it moves to step 9.
8. **`Real` formatting and parsing in Quest** (§4.3).
   A subproject of its own, with its own risk: it is tested apart from the backend first, since the Quest code
   runs natively too, against the C runtime on the same inputs. Taken first, before step 2, at the owner's word.
   *Done when* the goldens that print and read `Real`s pass byte for byte, and a test of values chosen for their
   difficulty (halfway cases, subnormals, the largest and smallest, negative zero, infinities, and some millions
   of random bit patterns) agrees with the C runtime, natively and on this target.
9. **Units and the library:** exports at closure signatures, imports by name, initializers; the externals' table
   and its coverage test; the driver's build writing a module for each unit; the loaders for wasmtime and node;
   files, arguments, and the environment over WASI; artifacts (§5.3).
   *Done when* a program of several units using `lib/` runs in both engines, and the pending list holds only what
   step 1 excluded, locations, and the mathematical functions.
   *Taken before the rest of step 6, at the owner's word, so that the runtime can be a unit written in Quest.
   Units, done 2026-11-13; the library and the rest remain:*
   - **A module file's unit** is a module that exports:
     - its `init`, guarded by a flag, which runs its imports' `init`s in their order and then its body;
     - its record's two globals;
     - each of its functions, at its interface type's closure signature, through a wrapper that boxes or unboxes
       where its own differs.
   - **An importer** imports those by the unit's canonical name and reads members through the record.
   - **A program** runs its imports' `init`s, then its inline modules' bodies, then its top level.
   - **The build:** the engine writes a unit's module as its object. The driver preloads each unit's module in
     wasmtime, or passes it to `runtime/wasm/run.mjs` in node, in the order of their manifests' imports.
   - **The library's units** are still compiled by the C printer under `--backend wasm` (`choice.forFile`), and a
     program's calls of them still go through the runtime's table, until the library is compiled.
   - **Run goldens:** the modes pass 77, those of several units among them, the same in both engines. 220 are
     pending.

   *The library, first part, done 2026-11-14:*
   - **`lib/` is compiled by the wasm backend** like any unit (`choice.forFile` no longer sends it to C). A call of
     one of its externals (`repr/externals`), from a program or from the library itself, is compiled in place by
     the backend's table of externals: an instruction sequence (`Word`'s operations, `hash.mix` and `combine`,
     `ascii`, `arrayOp.size`, `string`'s length), a call of the base (`string`'s, `conv`'s, `writer`'s), or a call
     of `wasm/core`, whose Quest has `string`'s comparisons and joins, `util/stringbuilder`'s buffer, and
     `hash.identityHash`. An external value is a built-in exception, a constant, or a stream.
   - **What this target lacks** fails when it runs, with a message naming it, not when its unit is compiled: an
     external the table has no entry for, and a module's function that uses what the backend cannot yet compile
     (its body is that failure). So a library unit compiles whole, and a program runs until it reaches the
     missing part. A program's own code, and the runtime's, still fail when compiled.
   - **The runtime's units use the library only through the table:** they import no library unit, and a call of
     one the backend does not compile itself fails as they are compiled.
   - **Order:** the driver preloads the units in the order their modules' import sections give, which includes
     the runtime's units that the backend adds.
   - **`Real`, step 8's first part:** values as `f64`, boxed in `$boxReal`; constants; `+`, `-`, `*`, and `//`
     with their `real.error` tests; comparisons; `real.int`, `floor`, `round`, `ceil`, `trunc`, `sqrt`, and `div`;
     `Word`'s bits. `**`, the mathematical functions, and conversion to and from text still fail when run.
   - **Run goldens:** the modes pass 116, the same in both engines; 181 are pending.
   - **Still to come:** files, arguments, and the environment over WASI; `reader`; `conv.real` through
     `util/realconv`; the externals' coverage test.

   *The library, second part, built 2026-11-14:*
   - **WASI:** the base imports the rest of WASI's first preview that the library needs (arguments, the
     environment, opened directories, `path_open`, `fd_read`, `fd_readdir`, `path_filestat_get`, and creating,
     removing, and renaming), and exports each as `wasi:NAME`, with helpers that read and write its memory and
     copy strings to and from it. Over them `wasm/core` has, in Quest, `system`'s arguments, environment, files,
     and directories, `os/filestats`' `rawStat`, `writer.file` and `close`, and `reader`, buffered.
   - **Paths:** the host opens `/` and `.`; a relative path is resolved against the current directory, which
     starts as `PWD` and `changeDirectory` sets, and opened from `/`. wasmtime is run with `--dir /`, `--dir .`,
     `PWD`, and the environment variables the compiler reads; node through `node:wasi`, with the same.
   - **Without a counterpart:** `system.run` and `os/process` raise `system.error`; `os/code` and `os/value`
     raise `value.error`, but for `code.address`, which answers that there is no such symbol; `readline` edits
     no line and raises `readline.error`. WASI has no permission bits, so `rawStat`'s mode is `0o644` for a file
     and `0o755` for a directory: an accepted difference.
   - **`util/realconv`** writes a `Real` for `conv.real`, `stringBuilder`, echo, and `wasm/print`, and reads one
     for `strutil`; a unit that needs it imports it.
   - **The externals' coverage test** (`tests/python/test_wasm_externals.py`) checks that every external of
     `lib/` is compiled by the table or listed as lacking: the mathematical functions, `real.format`'s styles,
     and `dynamic`'s serialization.
   - **An exception the base does not define** (`readline.endOfInput`) is made by the unit's initializer, once,
     with the C runtime's name for it.
   - **Run goldens:** the modes pass 186, the same in both engines; 110 are pending, `os/process`'s among them.
     After step 10, 191; 105 pending.
     wasmtime inherits the environment (`-S inherit-env=y`).
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

    *Done 2026-11-14, milestone 1 reached:*
    - **Self-compilation:** the driver, compiled by the native compiler with `--backend wasm`, compiles itself with
      `--backend wasm -j 1` in node (its default stack) and in wasmtime, and writes the same 198 modules as the
      native compiler, byte for byte. Before that it wrote the same typecheck dump, described IR, and wasm and
      arm64 code as the native compiler for a small program, and the same modules for a program of two units.
    - **What it took, besides steps 2 to 9:** a caught exception as a value of `raised.T`; the library's exceptions
      the base lacks made by their units' initializers; and the build logger, which appends to its log file through
      a shell, leaving the file alone where no shell can run.
    - **Measured** ([benchmarks.md](benchmarks.md) §25): node takes 1.63 of the native compiler's wall time (55.6 s
      against 34.2), at about the same peak resident memory (3.5 GB); node's default heap limit did not need
      raising. Boxing `Int`s takes about 10 percent, the unneeded adapters about 8, and calls across units are the
      hottest functions. wasmtime with the copying collector takes 790 s. Since step 13 the driver that wasmtime
      runs is built with `--variant questlang/jit/target=none`, with no JIT: the wasm JIT's host is JavaScript's.
    - **The stack:** 126 KB compiles a small program and 296 KB the tokenizer's unit, in node, with `--liftoff-only`
      or without: within a worker's 512 KB. Step 7's measurement of the stack per level of the compiler's large
      recursive functions is this one's upper bound for now; a deeper input is milestone 2's to measure.
    - **The host:** `runtime/wasm/run.mjs` ends a run at `proc_exit` by unwinding to its top, so that node exits as
      after a script and writes `--cpu-prof`'s profile.

### 8.2. Milestone 2: The Interpreter in a Page

A checkpoint (decision 4): the driver of milestone 1, unchanged but for its entry, runs in a page's worker and
interprets each input, with whatever depth the stack gives. Its steps were drafted 2026-11-14 on milestone 1's
results, and the owner had step 11 built as drafted, with the interpreter's limit below a worker's stack, and then
step 12.

**Choices this draft makes,** each the owner's to confirm or change (§8.2.1 says why):

- **The session's protocol is the kernel's** ([jupyter-kernel.md](jupyter-kernel.md) §2): one entry takes one JSON
  request (`execute`, `complete`, `inspect`, `isComplete`), and the records go out on descriptor 4 as they do now.
  No second protocol is written, and the kernel's own test checks the session.
- **One host in JavaScript,** `runtime/wasm/host.mjs`, implements the part of WASI's first preview that the base
  imports, over a table of mounts. node runs the session on it, backed by node's files, and the page runs on it,
  backed by archives and requests. So node's tests test the page's host. `run.mjs` keeps `node:wasi` for programs.
- **The page is a directory of static files** that a tool builds; any static server serves it, `python3 -m
  http.server` for checking. Deploying it anywhere is not part of this milestone.

11. **The session in node.** The driver as a session that a host calls, and the host's recovery, all in node.
    - **The entry.** `questlang/driver/kernel` has a function that answers one request, the body of `runKernel`'s
      loop, which the loop calls. The driver under `--kernel` on this backend reads no descriptor 3: its top level
      registers that function with a runtime unit, `wasm/session`, and returns without exiting. The runtime module
      exports `request(length)`, which reads the request from the buffer and calls the function registered. The
      interpreter serves the inputs (`--no-jit` is implied: the native JIT needs `os/code`).
    - **Output in order.** Writes to descriptors 1, 2, and 4 reach the host as `fd_write` calls, in the order made,
      so a cell's output and its records interleave as they do through the kernel's pipes. The kernel's
      `writer.file("/dev/fd/4")` is a path the host maps to the record stream.
    - **The host** (`runtime/wasm/host.mjs`): WASI over mounts, each a directory of a kind: node's file system,
      for node; an archive in memory, read only; a list of URL prefixes, read by synchronous request (§5.2); and
      the session's own files, in memory, for what an input writes. The clock, the arguments, and the environment
      (`QUEST_HOME` names the library's mount). The loader: the runtime, then the units in their `.units` order,
      then the driver, then `_start`.
    - **The session's client** (`runtime/wasm/session.mjs`), the page's logic without the page: it keeps the
      committed inputs, calls `request`, and recovers. A `RangeError` or a trap during `execute` is a stack
      overflow (§6.3). In this milestone every input runs in the interpreter, whose structures the overflow may
      leave half updated, so every such overflow replays: a new instance, the committed inputs run again with their
      output suppressed, and the failed input's error is `stack.overflow`. An interrupt is a timeout that ends a
      `worker_threads` worker and replays the same way.
    - **The interpreter's limit on this target.** The interpreter raises a catchable `stack.overflow` when more
      than `maxCallDepth` calls are active (1,000), and the REPL rolls that input back like any failure. A
      worker's stack runs out first, so on this target the limit is set below the depth a worker's stack holds,
      measured in this step with a margin, and a user's deep recursion is an ordinary error with no replay. What
      the limit does not count still replays: a library function's own recursion, the parser's and the
      elaborator's on deeply nested input, and a call whose body nests unusually deep.
    - **The core's count** (§6.3): `wasm/core` counts its updates of the descriptors' memo in progress, in a global
      the runtime exports, so that milestone 3's host can tell an input's overflow from the runtime's.
    - **Tests in node:** `session.mjs` also speaks the kernel's protocol on its own descriptors 3 and 4, so
      `tests/self-hosted/kernel_protocol.py` runs against it as a driver, with `--no-jit`, less what has no
      counterpart (displays and `readLine` through descriptor 3, which come in step 12 as host calls; a SIGINT,
      replaced by its timeout). The REPL's transcripts (`tests/repl/`) run through a loop in `session.mjs` that
      reads lines, asks `isComplete`, and writes the REPL's prompts and results, against the same goldens. Both
      run in a worker with a worker's stack (`resourceLimits.stackSizeMb`, 0.5), and with `--liftoff-only`,
      as a page's first inputs run. Its own tests: an input that recurses past the stack, and one that loops
      forever, each followed by an input that sees the earlier bindings.
    *Done when* the kernel's protocol test and the transcripts pass in node at a worker's stack, but for those a
    pending list names with reasons; a session survives an overflow and an interrupt with its bindings; and the
    interpreter's depth in node at a worker's stack, with `--liftoff-only` and without, is recorded in §6.2 beside
    the native estimate (80 to 250 calls), with the limit chosen from it.

    *Done 2026-11-14:*
    - **The entry.** `questlang/driver/kernel` has `serve`, which answers one request (the body of `runKernel`'s
      loop), and, for a host, `serving` and `request`. With `QUEST_HOST_SESSION` set, the driver under `--kernel`
      or `-i` (after the file `-i` runs) holds its session and returns from `_start`; the host then calls the
      kernel unit's exported `request` for each request, whose line it queues for the read of `/dev/fd/3` that
      `request` makes. No `wasm/session` unit was needed: a unit's exported function takes its closure first, and
      the runtime module now exports `noClosure`, a closure that captures nothing, for a host to pass.
    - **The host:** `runtime/wasm/host.mjs`, WASI over mounts (node's files; a tree in memory, read only or not),
      with `/dev/fd/3` and `/dev/fd/4` as the request and record streams. `runtime/wasm/session.mjs` instantiates
      the driver over it, keeps the committed inputs, and replays them, their output suppressed, after an
      engine's stack overflow or a trap. `runtime/wasm/session-node.mjs` runs that in a worker, speaks the
      kernel's protocol on its own descriptors 3 and 4 (a SIGINT ends the worker and replays in a new one, the
      input's error `interrupted`), or reads lines as the REPL does. `run.mjs` keeps `node:wasi` for programs.
    - **The stack:** a node worker keeps 192 KB of its stack from V8, so `session-node.mjs` asks for 192 KB more
      than the 512 KB it means. At first the interpreter reached 40 calls there: `treewalk`'s `evalExpr` had
      1,211 locals, each a slot in a baseline frame. The locals' reuse §2.11 asked for was not built in milestone
      1; it is now `questlang/wasm/locals`, run on every module the backend makes: each local gets a slot of its
      type that no local live at the same time holds, liveness taken in the code's order and widened over loops.
      `evalExpr` has 29 locals. Self-compilation is still byte-identical (199 modules) and takes the same time.
    - **The interpreter's depth** in a worker's 512 KB, after the reuse: 753 calls of a function whose body is one
      `if`, and 175 of one whose body nests a `let`, a tuple, a loop, and an `if` around the call; 1,571 of the
      first in 1 MB; the same with `--liftoff-only`, since a first deep recursion runs in baseline code anyway.
      Natively the estimate was 80 to 250.
    - **The limit:** `QUEST_CALL_LIMIT` sets the interpreter's (`questlang/interpreter/primitives`), 1,000 when
      unset; a session sets 150, below both shapes, so a deep recursion is an ordinary `stack.overflow`, rolled
      back without a replay. A call whose body nests more still overflows the engine, and replays.
    - **The core's count:** `wasm/core.updating()`, its updates of the descriptors' memo in progress, which
      `Session.updating()` reads; unused until milestone 3.
    - **Warnings:** the kernel now writes an input's warnings to standard error as the REPL does, so the
      transcripts that have them agree, and a notebook shows them.
    - **Tests:** `tests/self-hosted/wasm_session.py` (a unit check of `run_tests.py --self-hosted`) builds the
      driver for wasm and runs, at a worker's stack: the REPL's 18 transcripts, all but `stack_overflow`, whose
      frames repeat as many times as the limit allows; the kernel's protocol test, with `--session`, which leaves
      out `system.run`'s cell and the cell of displays and `readLine`; and an overflow past the interpreter's
      limit, replayed, with the earlier bindings kept and the failed input's lost.
    - **Found on the way:** a module's top-level `let` whose value is an `if` fails the IR's check of scopes
      (`QUEST_CHECK_IR=1`), on every backend: the binding and each one after it are "used outside its scope".
      `primitives` avoids it with a function; the bug is not fixed here.
12. **The page.** A worker, the loader, the prompt.
    - **Built** by `tools/wasm-page/build` into a directory: `index.html`; the page's script, which owns the
      prompt, a line editor of its own with history, and the transcript; the worker's script, which runs
      `session.mjs`'s logic over `host.mjs`; the driver's modules as one archive (§5.1); and the library's sources,
      with or without the release's `.qi` files, as another (§5.2).
    - **Files:** `/quest/lib` is the library's archive; other URL prefixes may be given in the page's query, each
      mounted at `/remote/N` and named in `QUEST_PATH`; the current directory is the session's own files, which
      start empty and last as long as the page.
    - **What a page lacks:** `io/display` writes its record and the page shows its HTML, image, or text; `readLine`
      asks the page through a host call and gets the end of input, since a worker cannot wait for a person without
      shared memory (§6.4).
    - **Interrupts:** a button, and Ctrl-C at the prompt, end the worker and replay (§6.4).
    - **Measured** in a Chromium browser, by hand: the archives' sizes, compressed and not; start-up to the first
      prompt (fetching, compiling, instantiating, the driver's initializers); the first input's latency and the
      next's, with the `.qi` files in the archive and without, which decides whether they ship (§5.2); the
      interpreter's depth in a worker, against step 11's node figure; and a replay's time after ten inputs.
    *Done when* the transcripts of `tests/repl/` give their goldens when typed or pasted into the page in a
    Chromium browser, the only kind promised for now; an overflow and an interrupt recover there; and §6.2 and
    §5.2 record the measurements, with the `.qi` question decided on them.

    *Done 2026-11-14:*
    - **Built** by `tools/wasm-page/build` (`build.py`), which compiles the driver with `--backend wasm` (43 s with
      `./quest`), or takes one built (`--driver-wasm`), into a directory: `index.html` and `style.css`; `ui.mjs`,
      the prompt; `page.mjs`, which loads the archives, compiles the modules once, and runs a session's worker;
      `worker.mjs`, the worker; `host.mjs` and `session.mjs` of step 11 unchanged but for a mount over URL
      prefixes; `repl.mjs`, the REPL's loop, which `session-node.mjs` now uses too; and the two archives,
      `driver.qar.gz` and `lib.qar.gz`, in a format of their own (`runtime/wasm/archive.mjs`: an index in JSON, the
      members' bytes, gzip that the page undoes with `DecompressionStream`). `--tests` adds `check.html`, which
      runs the REPL's transcripts in the page against their goldens, and `--check` runs it in headless Chrome.
    - **Files:** `/` is the session's own files, in memory in the worker, the current directory `/work`; each change
      is posted to the page, whose copy a worker started after an interrupt begins with, so that they last as long
      as the page. `QUEST_HOME` is `/quest`, with the library's archive at `/quest/lib`. A `path=URL` in the
      page's query is mounted at `/remote/N` and named in `QUEST_PATH`, read by synchronous request, each file at
      most once; `load=PATH` and `args=` are `-i`'s file and the program's arguments.
    - **The prompt:** a line at a time, as the native REPL reads them, so a paste of several lines is several
      lines; a line typed while an input runs waits its turn. History on the arrows; Tab completes through the
      protocol's `complete`. Ctrl-C, or the button, interrupts an input (a new worker, the session replayed), and
      at the prompt discards the phrase in progress. Displays show as they come: HTML in a frame sandboxed without
      scripts, SVG and other images as images.
    - **`readLine`** raises `readline.error` on this target, as it did, rather than giving the end of input as the
      draft said: the end of input is `readline.endOfInput`, an exception made by the readline unit's initializer,
      which the code generated for the external cannot reach. Either way no line is read; a prompt for one waits
      for milestone 3.
    - **Checked** in the desktop app's Chromium and in Google Chrome, headless, with a profile of its own: the
      REPL's 16 transcripts give their goldens, typed a line at a time, `stack_overflow` pending as in node; by
      hand, an interrupt of an endless loop, an overflow at the interpreter's limit (rolled back), one past it
      (replayed, in 46 ms after ten inputs), displays, paste, completion. In node,
      `tests/self-hosted/wasm_page.mjs`, run by `self-hosted/wasm_session`, checks the page's build: its archives,
      and its worker's session, with a URL prefix, a file written and copied, a display, and a replay in a new
      worker that keeps the bindings and the files.
    - **Measured** in Chromium, from a server on the same machine:
      - the archives: the driver's modules 16.9 MB, 3.9 MB compressed; the library 265 KB, 54 KB compressed (327 KB
        and 60 KB with the `.qi` files);
      - start-up, a page's first: fetching 21 ms, unpacking 31, compiling 118, and the session's start, which
        instantiates the modules and runs the driver's initializers, cold, 761 ms; about a second to the prompt
        locally, so that a real network's 3.9 MB is what start-up waits for;
      - an input's latency: 9 ms for the first (`let x = 1 + 1`), 1 ms for the next; an input importing one library
        module, 68 ms, and eleven, about 375 ms, with the `.qi` files or without, so they are not shipped (§5.2);
      - the interpreter's depth in a worker: 734 calls of the simple body and 169 of the nested one, against node's
        753 and 175, so the limit of 150 stands (§6.2);
      - a replay: 117 ms for an interrupt after ten inputs (a new worker, the modules already compiled, the inputs
        run again), 46 ms for an overflow's (the same worker, a new instance).

#### 8.2.1. Why These Choices

- **The kernel's protocol.** §6.1's entries (initialize, whether an input is complete, evaluate, abandon) are the
  kernel's requests already, with completion and inspection besides, and the kernel's code answers them through
  `driver/repl`, whose `evaluate` already rolls a failed input back. The alternative, exports for each entry with
  their arguments in the buffer, needs a decoder of its own on each side for the same records. The cost is JSON
  for each request, which is small beside an interpreted input. Milestone 3's three-call evaluation (compile, the
  host runs the module, commit or abandon) becomes three more requests.
- **One host.** The page cannot use `node:wasi`, and the host is the part of the page most likely to be wrong:
  paths under mounts, file descriptors, directories listed, errors' numbers. Running node's tests over the page's
  host finds those in `tools/check`, not by hand. Programs keep `node:wasi`, so the run goldens still compare two
  independent WASI implementations, wasmtime's and node's.
- **An overflow the interpreter does not catch replays.** No Quest handler sees a WebAssembly stack overflow, so
  neither the interpreter's cleanup (its call stack, popped as each call returns) nor the REPL's rollback runs,
  and §6.3 replays whenever the interpreter or the compiler was running. The interpreter's own limit, set below
  the stack a worker has, turns the common case, a user's deep recursion, into an ordinary `stack.overflow` that
  rolls back; what remains replays, which is why the interpreter is a checkpoint and the JIT follows.
- **`readLine` ends at once in the page.** A worker can block on a person only through `Atomics.wait` on shared
  memory, which needs cross-origin isolation (decision 11). A prompt for a line is milestone 3's, or later's, to
  design with the JIT's three calls.

### 8.3. Milestone 3: Each Interaction a Module

The REPL people use: an input is compiled in the session to a module, which the host loads beside the driver's and
the earlier inputs' modules, and its code runs as compiled code, not interpreted. Its steps were drafted 2026-11-14
on milestone 2's results.

**What carries over from the native JIT** ([jit.md](jit.md) §3): everything up to a unit. `ir/lower`'s
`lowerPhrases` makes an input a phrase unit, a module `qj_<n>` whose record holds its bindings; a later input
imports it and reads them as members. `jit/session`'s bookkeeping is the same: the earlier inputs' bindings
(`lower.Earlier`), their sources by name, and the module files compiled and loaded once (§3.4 there). Redefinition
in place ([repl.md](repl.md) §6) needs nothing new: the lowering already holds a binding that may be redefined in a
box, a one-component `var` tuple that the input's record points to, which here is a `$tuple` of one slot; a later
input reaches it through the record and stores to it. A failed input is not committed. **What does not:** the arm64
backend, its encoder and loader, `os/code`'s calls and raw memory, the frames read from the native stack, and the
echo capture's C functions.

**Choices,** the owner's answers of 2026-11-14 to the first draft's (§8.3.1 says why):

- **The driver calls the host to run an input, in one request,** in place of §6.1's three (confirmed). The driver
  compiles the input, then calls a host import that instantiates its module and calls its entry. The host catches
  an engine's stack overflow or a trap at that import's boundary, so it unwinds only the input's frames, and those
  of the library and runtime it called, as §6.1 wanted; the driver's frames below are intact, and the import gives the
  failure back to the driver, which rolls the input back as it rolls back any raise. §6.1 and §6.3 are revised to
  say so when step 13 is built.
- **A module's bytes cross directly,** not as a file (the owner's answer): the core copies a string's bytes into
  the linear memory a chunk at a time, and the host gathers them, as `fd_write` is given its bytes now.
- **The JIT is chosen when the driver is built** (the owner's answer, the mechanism this draft's): `jit/session`
  keeps what is common and imports one interface, `jit/target`, whose implementation is a **variant** of its
  module, chosen by the build. A module may have variants, files beside it named `NAME.VARIANT.mod.quest`
  (`questlang/jit/target.wasm.mod.quest`), each implementing its one interface; `--variant UNIT=VARIANT` picks one,
  as `--unit-backend` picks a unit's backend, and without it a unit that has a variant named for the backend
  compiling it takes that variant (a unit the wasm backend compiles takes `wasm`), and any other takes the plain
  file. So the arm64 JIT
  is `jit/target.mod.quest`, today's code; the wasm JIT is `target.wasm.mod.quest`; and a driver with no JIT is
  `target.none.mod.quest`, which refuses `--jit` and interprets. Only the variant chosen is compiled and linked.
- **A driver run where no host can run its inputs** (wasmtime) is built with no JIT, `--variant
  questlang/jit/target=none` (the owner's answer, (b) of §8.3.1): a second build of the driver, made only when
  wasmtime runs it, by hand.

13. **The JIT in node.** Inputs compiled to modules and run by the host, in node, with no page.
    - **Variants:** `modules/paths` finds a unit's variant beside its file, and the build engine, the module
      compiler, and the whole-program build take the variant its backend or `--variant` names; a unit's canonical
      name is its plain file's, whatever its variant (`paths.stripUnitSuffix`), and its manifest records the
      variant, so that a change of variant rebuilds it, as a change of backend does. The bootstrap needs nothing: it
      compiles the plain files, the arm64 JIT among them, and its stage 1 is not a host (§3.10 of jit.md).
    - **The target:** `jit/session`'s arm64 parts move behind an interface, `jit/target` (whether the driver can
      host the JIT; compile a unit and load it; call an input's entry; whether the driver has a unit, and its
      fingerprint; set `system.args`), whose plain module is today's code, through `os/code` and `jit/loader`, and
      whose variants are `wasm` and `none`. Natively nothing changes: the arm64 goldens and the JIT's suites stay
      as they are.
    - **Phrase units in the wasm backend:** a phrase unit's entry, `qj_<n>_entry`, exported, runs its imports'
      initializers and its own, as a module's `init` does; with capture, the runtime's `wasm/print` writes what the
      phrases show to a buffer of its own rather than to standard output (`print.capture` and `print.captured`, in
      place of `quest_echo_capture` and `quest_echo_captured`), and the target reads it after the entry returns,
      from the one runtime instance the driver and the inputs share. A declared module's name begins with its
      input's, as natively.
    - **Fingerprints:** each module unit the wasm backend compiles exports `qh_<unit>`, its interface's fingerprint
      ([jit.md](jit.md) §3.3.1), with the target in what it digests (§5.3); the host reads it from the driver's
      instance, and the target compares it with the interface an input was compiled against, as `checkImport`
      does now.
    - **The host's imports** (`quest.host`, which only `jit/target`'s `wasm` variant imports): `bytes(at n)`,
      which appends n bytes of the linear memory to the module being given; `load(name)`, which compiles the bytes
      given, instantiates the module with the runtime, the driver's units, and the units loaded before, by name,
      and keeps the instance under name; `run(name)`, which calls its entry and gives 0, or
      1 for an engine's stack overflow and 2 for a trap, after which the host reads the core's count of updates
      (`core.updating`, step 11): not zero, and the session is replayed once the request ends (§6.3); and
      `has(unit)` and `fingerprint(unit)`. A Quest exception the entry raises is not caught by the host: it crosses
      the host's frame, as WebAssembly's exceptions do, to the target's handler, which reads its raise site from
      the exception. The imports are in `runtime/wasm/jit.mjs`, which `session.mjs` and `run.mjs` both use, so
      that `node run.mjs DRIVER FILE` runs a file through the JIT as `quest FILE` does natively.
    - **Traces:** decision 12 holds, so an input's uncaught exception shows its raise site and `<main>`, not the
      frames between: the transcripts that list frames are pending under the JIT, with that reason.
    - **`system.args`** is set through an intrinsic of the core's, not through raw memory as `os/value` sets it.
    - **The default:** the driver on this target runs the JIT unless given `--no-jit`, as natively. A session
      replays by compiling its committed inputs again (§6.3): correct, and measured in step 14. The driver that
      wasmtime runs, for its self-compilation, is built with `--variant questlang/jit/target=none`, and the
      instructions for that run (§8.1's step 10, [benchmarks.md](benchmarks.md) §25) say so.
    - **Tests in node:** `self-hosted/wasm_session` runs the REPL's transcripts and the kernel's protocol a second
      time with the JIT, with the skips their `jit` phase already names and a pending list of its own, and its
      recovery checks with the JIT: an overflow in an input's own code rolled back without a replay, the earlier
      bindings kept; one while the compiler runs, replayed; an interrupt. A runner mode, `wasm-jit`, runs the run
      goldens through `run.mjs` and the driver's JIT, one input each, as `jit-files` runs them natively, with a
      pending list of its own.
      Variants get a test of their own in the module suite: a unit with a variant, built with and without
      `--variant`, and rebuilt when the variant changes.
    *Done when* the transcripts and the kernel's protocol pass in node with the JIT at a worker's stack, but for
    the pending list's; the recovery checks pass; `wasm-jit` passes but for its pending list, whose entries are
    grouped by reason; and the arm64 JIT's suites and goldens are unchanged.

    *Done 2026-11-14:*
    - **Variants** ([build-process.md](build-process.md) §6.4): `codegen/choice` holds them beside the backends
      (`variants`, `variantFor`, `parseVariant`, `--variant` in `arguments`); `modules/graph`'s resolver chooses
      (`variantOf`, set by the driver, the engine's `withBackends`, and the build's workers), through
      `paths.chooseVariant`; `paths.stripUnitSuffix` drops a variant's name, so its unit and artifacts are its
      module's. `tests/self-hosted/variants.py` (a unit check) builds a program in one build directory with each
      choice of variant and backend, serially and with `-j 4`, and the interpreter.
    - **The target:** `questlang/jit/target` (an interface of its own, not unsound): its own file is the arm64 code
      that was `jit/session`'s, moved; `target.wasm.mod.quest` and `target.none.mod.quest` are its variants.
      `jit/session` keeps the inputs' bookkeeping and loses its arm64 imports, and is an ordinary module now. The
      wasm driver links no `jit/loader` or `jit/debugObject`. Natively nothing changes.
    - **Phrase units in the wasm backend:** compiled as modules though marked programs, their init the entry (the
      modules' initializers and then the unit's top level, as the native entry runs them); their echoes written
      with `wasm/print`'s `echoText`, which captures while a capture is on (`print.capture`, `print.captured`); the
      modules an input declares exported as `qj_N_k.FIELD`, which the host gives later inputs as the module
      `qj_N_k`.
    - **Fingerprints:** a module unit's module ends in a custom section, `quest.fingerprint`
      (`encode.customSection`), which the host reads (`WebAssembly.Module.customSections`). The digest is the
      native one: the target is not in it yet, as §5.3 has it, which matters only where artifacts of two targets
      could meet, and none do: the JIT compares an interface's fingerprint with its host's units alone. No ABI
      bump: each build writes the runtime's module afresh, and a unit compiled before simply does not import
      `raisedText`.
    - **Intrinsics for the target:** `wasm.host.NAME` (an import of `quest.host`, its Ints as i32s),
      `wasm.print.capture` and `captured`, `wasm.raisedName` (the runtime's new `raisedText`, as the uncaught
      report writes an exception, its payload by print's `show`) and `raisedSite`, `wasm.importedRecord` and
      `wasm.recordSet` (system.args set in the driver's own system record, by its field's index in name order).
      Strings cross to the host as bytes at 1 MB in the linear memory (`wasm.base.stringToMem`).
    - **The host:** `runtime/wasm/jit.mjs`, a linker over every unit's exports by name; `give`, `load`, `run`,
      `has` (the driver's own units alone: a unit the JIT loaded is loaded again after an input that loaded it
      fails), and `fingerprint`. `session.mjs` and `run.mjs` instantiate the driver through it, so `node run.mjs
      DRIVER FILE` runs a file through the JIT; `session-node.mjs` passes `--no-jit` only when given it; the page
      copies `jit.mjs` and still passes `--no-jit` (step 14).
    - **The driver:** a host's session (`QUEST_HOST_SESSION`) is served after the JIT's first input as after the
      interpreter's (`main.quest`'s `jitRun`).
    - **Tests:** `self-hosted/wasm_session` runs the transcripts and the kernel's protocol interpreted and with
      the JIT (pending under the JIT: `earlier_function_error` and `module_errors`, whose frames decision 12
      leaves out; the kernel's interrupt of a tail recursion, below), and the JIT's recovery: an overflow in an
      input's own code rolled back with no replay (an array it stored to keeps the store), and one in the
      compiler (3,000 chained additions) by a replay. The runner's `wasm-jit` mode runs the run goldens through
      `run.mjs` and the JIT, as `jit-files` does natively, in `tools/check`'s backends suite: 182 of 298 pass, and
      `tests/self-hosted/pending-wasm-jit.txt` lists the 115 others by what each needs, nearly all milestone 4's
      (variants 36, `auto`/`inspect`/`dynamic` 27, views 20, `var` parameters 18). The questlang test
      `codegen_choice` covers the variants' choice. Self-compilation in node is still byte-identical (198
      modules); the `.wat` goldens gain the import of `raisedText`; the no-JIT driver runs in wasmtime.
    - **Found:** (1) V8 cannot end a worker in a loop of tail calls (§6.4), so the kernel's interrupt of an endless
      tail recursion is left out in a session. (2) In kernel mode, where top-level bindings are not slots, an
      earlier input's `var` read by a later one is a location, which this backend lacks until milestone 4; the REPL
      (`-i`) boxes its bindings and is not affected. (3) An earlier input's tuple's field, read by a later input,
      fails under the JIT on both targets: natively the SSA's builder raises `arrayOp.error`
      (`values.toWord`), in the release too, and here the backend finds the record type without the field. (4)
      `questlang/types_judgments` under the wasm JIT reports no unbound type variable where the program compiled
      does; pending, to find.
14. **The JIT in the page.**
    - **Built** as step 12's page, the JIT on by default; the module files an input imports from a URL prefix are
      compiled in the session, as natively.
    - **Checked** in Chromium: `check.html` runs the transcripts with the JIT, as `--check` does headless, and, by
      hand, an overflow in an input (no replay) and in the compiler (a replay), an interrupt, and redefinition.
    - **Measured** in Chromium, by hand: an input's latency with the JIT, the first and the next, against the
      interpreter's from step 12; the compiler's stack in a worker as it compiles inputs, in baseline code, since
      the first inputs compile cold (step 10's 296 KB for the tokenizer was taken before the locals' reuse); the
      depth of compiled recursion in a worker; and a replay's time after ten inputs, compiling each again. If
      replay is slow, the refinement of §6.3, keeping each committed input's module and admitting it again without
      compiling it, is decided on that measure.
    *Done when* the transcripts give their goldens in the page with the JIT, but for the pending list's; the
    recoveries work there; and §6.2 and §6.3 record the measurements, with the refinement decided.

    *Done 2026-11-14:*
    - **Built:** the page passes the driver no `--no-jit`, so each input is compiled by the session's JIT
      (`target.wasm`, step 13) and run by the worker's `jit.mjs`, which step 13 already copied; `?jit=0` in the
      page's query, or the option `jit: false` to `PageSession`, interprets. A module file an input imports from a
      URL prefix is compiled in the session, as natively.
    - **Checked** in Chromium: `check.html` runs the transcripts with the JIT, and `check.html?jit=0` interpreted;
      `tools/wasm-page/build --check` runs both in headless Chrome. With the JIT 14 give their goldens, and 3 are
      pending: `earlier_function_error` and `module_errors` (decision 12's frames, as in node) and `stack_overflow`
      (`@skip-phase: jit`); interpreted, 16, and `stack_overflow` pending, as in step 12. By a measuring page in the
      desktop app's Chromium and in Chrome headless with fresh profiles: an overflow in an input's own code rolled
      back with no replay, its store to an earlier array kept and its binding not committed; one in the compiler
      (3,000 chained additions) by a replay, the store undone; redefinition (a function redefined, and an earlier
      input's caller seeing the new one); and an interrupt of an endless loop, after which the 18 committed inputs
      are bound again. In node, `tests/self-hosted/wasm_page.mjs` runs its session with the JIT and interpreted.
    - **Measured** in Chrome headless, each run a fresh profile, from a server on the same machine:
      - an input's latency with the JIT: 41 to 43 ms for the first (`let x = 1 + 1`), the compiler running cold,
        then 5 ms and 2 ms; interpreted, 5, 2, and 0 ms. An input importing one library module, 15 ms with the JIT
        and 26 to 28 ms interpreted. In the desktop app's pane, its first load, the first input took 265 ms and the
        next 74 ms, the machine in use; later loads, with V8's caches warm, 12 to 16 ms;
      - the compiler's stack, cold, and compiled recursion's depth in a worker (§6.2);
      - a replay's time (§6.3), which decided the refinement there: not taken.

#### 8.3.1. Why These Choices

- **One request, the host called from inside it.** §6.1's three calls were meant to keep the compiler's frames off
  the stack while an input runs, so that an overflow there need not replay. A host import gets the same: an
  engine's overflow unwinds to the nearest JavaScript frame that catches it, which is the import's, and the frames
  below it, the driver's REPL loop and the JIT's target, were not running and are intact. What three calls cost
  and this does not: the session's state split across requests (an input compiled, waiting to be committed or
  abandoned), and a Quest exception carried from the host back to the driver, which a JSON record cannot hold.
  What it costs: the driver's frames under the input, a few kilobytes of a worker's 512, taken from a deep
  recursion's room. `jit/session` keeps its shape, where `run` gives an outcome, and natively nothing moves.
- **Bytes directly.** The owner's answer. The engine's strings are opaque to JavaScript, so the bytes are copied
  through the linear memory either way; given directly, they never pass through a mount or a path.
- **Variants chosen by the build.** The owner asked for the JIT to be chosen when the driver is built. The
  language has no way to choose an implementation of an interface, and the build's `choice` assigns units to
  backends, not files to units, so the build gains one: a unit's file chosen among its variants, by the backend
  that compiles it unless `--variant` says otherwise. A unit's importers see its interface alone, which every
  variant implements, so they compile alike whichever is chosen, and only the one chosen is linked: a wasm driver
  carries no arm64 loader, and a native one no wasm JIT (each still compiles for every backend). The default by backend keeps `--backend wasm` making a
  driver that works with no flag more; `--variant` makes the others, such as one with no JIT.
- **A driver run where no host can run its inputs: (b), the owner's answer.** With the `wasm` variant, the driver's
  module imports the host's functions (`quest.host`'s `load`, `run`, and the rest), and an engine refuses to
  instantiate a module whose imports are not all supplied. node and the page supply them; wasmtime cannot, since
  they are JavaScript's, and wasmtime runs the driver built for wasm in one check, its self-compilation (step 10's
  790 s, run by hand, not by `tools/check`). The program suite in wasmtime is unaffected: programs do not import the
  JIT. The ways out: (a) wasmtime is given a module of stubs, each answering "no JIT", and the driver interprets
  there; (b) the driver for wasmtime is built with `--variant questlang/jit/target=none`, a second build of the
  driver, made only when wasmtime runs it; (c) the driver no longer runs in wasmtime, node alone running its
  self-compilation. (b) was taken: the variants make it a flag, no stub module is kept in step with the imports, and
  the build it adds is made only by hand.
- **No frames.** Frames would need a count at each function's entry or a shadow stack, a cost in every unit; the
  interpreter shows them, and decision 12 put them later.

### 8.4. Milestone 4: The Rest

The language entire on this target, then its speed, the page's size, and the other browsers. Its steps were drafted
2026-11-14 on milestone 3's results, and the owner answered its questions the same day (§8.4.1).

**Where it starts.** The run suite has 105 pending for `wasm` and `wasm-node`, and 115 for `wasm-jit`
(`tests/self-hosted/pending-wasm.txt` and `pending-wasm-jit.txt`). The second list is grouped by what each test
needs, and the first is the same tests compiled, less those that need only what the JIT adds. By what they need,
counting a test once for each list it is in:

| What a test needs | Tests (`wasm-jit`) | Step |
|---|---|---|
| variants | 36 | 16 |
| `auto`, `inspect`, and `dynamic` | 28 | 18 |
| records' views, subtyping, and proxies | 21 | 17 |
| `var` and `out` parameters, and locations | 19 | 15 |
| `Real`'s mathematical functions and `real.format` | 5 | 19 |
| a built-in operator as a value; a recursive value's record capture; an option's ordinal out of bounds (as the native JIT's); `types_judgments`' difference | 9 | 20 |
| `os/process`, `os/value`, `os/fileStats`' modes, readline (§7) | 7 | none: accepted |

The groups overlap where a test needs two things; a test is under the first of its needs that a step provides, and
it passes when the last does. Every step below removes from both lists the tests it makes pass, and its *done when*
is those of its group that need nothing a later step adds.

**What carries over:** the IR already lowers each of these (the C and arm64 backends compile them), and the
represent pass already plans their conversions. What each step adds is this backend's half, and the core's
functions that the C runtime has (§4.2): written in Quest over the intrinsics, monomorphic, ported from the C as it
stands, not redesigned.

15. **Locations.** `var` and `out` parameters, `@`, and `var(e)`, as §2.6 has them: every address a pair of a
    `(ref $slots)` and an `i32`, a local whose address is taken kept in a one-element slot array from its
    declaration, and the callee reading and writing through the pair with no dispatch. A module's top-level `var`
    whose address its unit takes lives in a slot array its global holds; one other units see is a field of the
    module's record. So the kernel's mode, whose top-level bindings are not slots, reads an earlier input's `var`
    by its record's field (step 13's finding 2).
    *Done when* the locations' group passes in both lists, and a kernel session (`kernel_protocol.py --session`)
    reads and assigns an earlier input's `var` with the JIT.
    *Done 2026-11-14:*
    - **Built** in `wasm/codegen` as §2.6 has it: a location is two values, a `(ref null $slots)` and an `i32`,
      wherever it is held (a variable of type `Var(T)` or `Out(T)`, a parameter, a closure signature's place).
      The unit's located variables (`locatedVariables`: each `var` and `out` parameter, and each variable whose
      address is taken) hold their location rather than their value: a read is an `array.get` and an unbox, an
      assignment a box and an `array.set`, and a declaration makes the variable's own slot array of one. The
      addresses (`addr`, `cell`, a record's field, a tuple's component, an array's element after its bounds test),
      `load`, and `store_at` are the pairs §2.6 lists, with no dispatch. A parameter whose declared type is a
      location (`o: Out(Int)`) is laid out as one too. A location crosses a uniform entry packed in a slot array of
      two, its slot array and its index as an `i31`: only that path allocates.
    - **Checked:** in the compiled list 5 tests pass (`cardelli_syntax`, `closure_captured_vars`,
      `lvalues_references`, `scalar_slots`, `module_calls_module`), and in the JIT's list 11 (those and
      `cardelli_operators`, `inlined_calls`, `mutable_locals`, `partial_type_application`, `tail_calls`,
      `try_mutable_locals`). The others of the group now stop at variants or views and are listed under them.
      A kernel session with the JIT reads, assigns, and passes `@v` to an earlier input's `var` (step 13's finding
      2): the phrase units' records hold their variables, as natively. `wasm`, `wasm-node`, and `wasm-jit` pass
      but for their lists (100 and 104 pending), and so do `self-hosted/wasm_session` and `wasm_programs`.
16. **Variants.** §2.5's pair, an `i32` tag in the type's numbering and an `eqref` payload, boxed in an immutable
    `$varBox` in a slot; the tag maps (`(array i32)`) that remap a variant seen at another type; `case` over a
    variant, `?` and `!`, `is`, printing and echo, and a variant's descriptor (`variant_tags`). The closure
    signature already has a variant's two values (§3.2).
    *Done when* the variants' group passes in both lists, but for those that also need step 17 or 18.
    *Done 2026-11-14:*
    - **Built** in `wasm/codegen`: a variant is two values, an `i32` tag in its type's numbering (its cases' name
      order, as C numbers them) and an `eqref` payload as a slot holds it (`ok` for a case without one), and in a
      slot a `$varBox` of the two. Its tag is tested (`?`) and its payload taken (`!`, raising
      `variant.tagMismatch`); a `case` branches on the tag and binds the payload; a `variantTags` conversion maps
      the tag through a table of the source's cases to the target's (`br_table` of constants), the payload as it
      is. A variant in a slot compared with `is`, inside a single-word option, is its box, as C compares its boxed
      word. An unboxed tuple (`ir/unbox`) now holds each component as its parts, so a variant or record component
      is two values. `wasm/print` writes a variant as `quest_put_value` does (`variant TAG with PAYLOAD end`),
      through two intrinsics, `wasm.variantTag` and `wasm.variantPayload`. Descriptors needed nothing new: the
      static data already describes a variant's cases.
    - **Checked:** in the compiled list 11 tests pass, in the JIT's 14 (the variants' group's, and
      `variant_assert_tag_mismatch`'s error test); the rest of the group now stops at views or at `auto` and
      `dynamic`, and is listed under them, which empties the JIT list's variants group.
17. **Records' views, subtyping, and proxies.** The rest of §4.2's core: run-time subtyping; conversion
    (`quest_convert`, the `view`, `runtime`, `copy`, `cast`, and `unproxy` plans); a record seen at a type whose
    table is known only at run time, through the map of record tables; a record's field stored at another type;
    bounded quantifiers, whose type parameter carries a view map, and a bound's representation in signatures
    (§3.2); and proxies, whose path at a read (§2.3) has been a pending stub since step 4. Natively these are the
    C runtime's `quest_views.c` (conversion, views, and proxies), which is ported.
    *Done when* the views' group passes in both lists, but for those that also need step 18, and the variants'
    that waited for it.
    *Done 2026-11-14:*
    - **What on this target views need, and what not:** every slot holds a value in one form (§2.2), so no two
      layouts of a type differ, and C's layout equivalence, stored representations, and conversions between
      layouts have nothing to do here. What a value seen at another type may need is its view: a record's table, a
      variant's or option's tags in the other type's numbering, a tuple's or option's components seen so. The core
      (§4.2) does that from descriptors, ported from `quest_types.c` and `quest_views.c` as they stand:
      `isSubtype` (structural, coinductive, as `quest_is_subtype`; a var part's invariance is not checked, since
      descriptors here do not say which parts are var), the map of record tables (`recordDict`, `viewDict`), the
      stored types a table records where a payload stores a field at another type (`storedField`), `convert`
      (`quest_convert`: a record's box with its table at the target, a variant adapted, a tuple or option proxied
      or copied), view maps (`viewMap` and its reads), and proxies.
    - **Records:** a `$record` carries its layout's descriptor, where the unit makes one (a closure's capture
      record, which no view needs, carries none); a `$dict` gains `stored`, null for every static table; a record
      whose table is known only at run time takes the core's.
    - **Bounded quantifiers:** a function fetches each view map where it begins (`Function.viewMaps`), and a read
      of a field, component, tag, or payload through the bound, a store into a field, and an address go through it.
    - **Conversions:** `view` and `runtime` by descriptors in the core, from a value's slot form; `copy` a new tuple
      of components each converted by its plan at slot level (`slotConvert`), where box, unbox, and cast are
      nothing; `unproxy` a proxy's original.
    - **Proxies:** a `$proxy` (a subtype of `$tupleLike`) holds the core's state, `Proxied`: the original, the type
      its components are stored at, the type it is seen at, an option's tags. An access the represent pass marks
      original or proxy tests for a `$tuple` first, and only on a miss calls the core (`unproxy`, `proxyTag`,
      `proxyElement`, `proxyOptionElement`, `proxyOptionPayload`), as C tests its tag bit; `is` compares
      originals; printing and the identity hash read through proxies.
    - **Checked:** 30 tests of the compiled list pass and 29 of the JIT's (21 and 20 with records' tables, 8 and 8
      with view maps and the conversions, `option_payload_sharing` with proxies). The rest of the group, and the
      variants' that waited for it, now stop at `auto`, `inspect`, or `dynamic`, and are listed under them, but
      `option_identity`: `is` on an abstract type's values compares them as its representation's, which needs the
      registry of abstract types' representations (`quest_register_abstract_type`) that `dynamic` needs too, so
      it moves to step 18.
18. **`auto`, `inspect`, and `dynamic`.** An `auto` value and `inspect` (`opMakeAuto`, `sInspect`), and
    `lib/dynamic`'s externals: `copy`, `intern`, `extern`, and the serialization. The serialization is the core's
    upper layer (§4.2), since it may import the library; the interpreter's Quest version (`values/dynamicjson`) is
    the model where it serves, and the C runtime's (`quest_serialization.c`) is the reference, byte for byte, which
    the shared goldens check.
    *Done when* the `dynamic` group passes in both lists, and with it every test of steps 16 and 17 that waited.
    *Done 2026-11-14:*
    - **Auto values and inspect:** an `$auto` (its witness's descriptor and its other components' tuple); `inspect`
      matches a case by the core's `isSubtype` (both ways for an exact one), and binds the stored components, or a
      new tuple of them each converted by the arm's descriptors. `dynamic.copy` is the core's.
    - **Descriptors**, which step 17's views and this step's matching compare, now carry what C's do: each part's
      flags (var, out, a function's result, a quantifier's bound, an auto type's bound), a function type's
      parameters, an abstract type operator's application's arguments, a stored type's type and storage (a module's
      bounded abstract type, held at its bound), a bound variable for each index (nested auto types), and an
      instance's name with its holes written as its arguments' (cut off at 80 characters, as C's). Record types'
      descriptors are named as the C backend names them, a digest of each record's shape in its name, so that two
      records whose fields lay out alike are no longer one descriptor. `is` and the identity hash compare an abstract
      type's values as its representation's, through the registry of abstract types' representations that each
      module fills where it begins (`quest_register_abstract_type`); `is` by descriptor keeps a reference test as
      its fast path.
    - **Function adapters:** a closure seen at a function type whose parameters or result change view is wrapped in
      an adapter (quest_convert's `meta->adapt`), which converts each argument and the result through the core. The
      backend makes them where it compiles the core: for each uniform arity up to 8, a closure type `$adaptN` and
      its uniform entry, and a function that makes one.
    - **Serialization:** `runtime/wasm/dynamic`, the runtime's upper layer, is `quest_serialization.c` in Quest:
      the type graph of descriptors, its canonical table, the sharing scan, the writer, a streaming JSON parser
      (with one character of lookahead, which the core's reader gives back), the type table's descriptors, and the
      reader. `lib/dynamic.wasm.mod.quest`, the library's first variant (step 13's mechanism), calls it for
      `intern` and `extern`, so the C backend's library is unchanged; a variant's library path drops its name.
    - **Checked:** in the compiled list 46 tests pass, and 47 in the JIT's (with this step's group, the rest of
      step 17's: `option_identity`'s abstract types, and `stdlib/bytes`). The lists hold only `Real`'s mathematics
      (step 19), step 20's, and §7's absences. A program is checked with the runtime's units on its search path, as
      it is compiled, since the library's wasm variants import them.
19. **`Real`'s mathematics.** §4.3's second half: the mathematical functions ported to Quest from musl's or
    FreeBSD's `msun`, in a unit of the library beside `util/realconv` (and, like it, written and tested natively
    against libc first); `**` on reals; and `real.format`, a third formatter over `realconv`'s exact digits. A
    golden whose printed results differ from Apple's libm in the last bit is recorded for this target or exempt,
    each named (§7, 6).
    *Done when* the `Real` group passes in both lists, and the tests of the functions against libc pass natively
    within the error bound the port states.
    *Done 2026-11-15:*
    - **The functions:** `lib/util/realmath`, msun's `sin`, `cos`, and `tan` (with their reduction modulo π/2 at
      every magnitude), `asin`, `acos`, `atan`, `atan2`, `exp` (and `expm1` within), `log`, `sinh`, `cosh`, `tanh`,
      and `pow`, ported line for line (§4.3). Compared with msun built natively from FreeBSD's sources on 229,905
      values, every result is msun's to the bit.
    - **Against libc:** `stdlib/realmath_operations` checks each natively against Apple's libm, at its edges and at
      pseudo-random values: within 1 ulp, or 2 for `tan`, the hyperbolic functions, and `pow`, with `real.error`
      where libm's result is NaN. Left out: msun's least accurate case (§4.3).
    - **`real.format`** is `realconv.format`; `stdlib/realconv_format` checks it against `snprintf` at ten
      precisions in each style. Both tests skip the bootstrap's interpreters, for which each takes minutes.
    - **`tests/python/test_wasm_externals`** no longer lists the mathematical functions or `real.format` as lacking,
      and takes a wasm variant's `wasm.` intrinsics as compiled.
    - **Wired:** `real`'s functions and `^^` call `util/realmath`, which every program imports beside `wasm/print`.
    - **Checked:** no golden needed recording for this target. The `Real` group passes in both lists; in each,
      `language/real_values` moves to step 20's built-in operators as values. What is left: step 20's, and §7's
      absences.
20. **What is left of the lists.** A built-in operator passed as a value; a recursive value's capture of a record;
    an option's ordinal out of bounds, which is pending on the native JIT too and is fixed in both; and
    `questlang/types_judgments`, which under the wasm JIT reports no unbound type variable where the program
    compiled does: a difference to find first. And, if the owner takes it (§8.4.1), step 13's finding 1: a
    function's call of itself in tail position compiled as a loop, so that V8 can end the worker it runs in.
    *Done when* each list holds only §7's absences (`os/process`, `os/value`, `os/fileStats`' modes, readline)
    and decision 12's frames, each with its reason, and the kernel's interrupt of a tail recursion runs in a
    session if the remedy is taken.
    *Done 2026-11-15:*
    - **Built-in operators as values:** every one the C runtime has a trampoline for, `Real`'s (`^^` by
      `util/realmath`), `<>`, and `Bool`'s eager `/\` and `\/` beside `Int`'s, each a static closure with a native
      and a uniform entry. `language/real_values` then showed `word.toReal` of a NaN's bits returning it, not raising
      `word.error` as the C runtime does; fixed.
    - **A recursive value's capture of a record** (or a variant), two parts, filled in by two fields.
    - **A fatal runtime error under either JIT** is reported as the compiled program's is and ends the input, not the
      driver (exceptions.md §2.5, jit.md §4). Natively, `quest_fatal` returns from `os/code`'s call as an exception
      named `fatal: ` and the message, which no handler in the input sees, so that the release-built stage 1 needs no
      new function; on WebAssembly, the runtime holds a fatal error's report while the host runs an input
      (`holdFatal`, `fatalReport`) and traps, the host returns 3, and the target reports it. `system.exit`, whose
      report is empty, still exits.
    - **`questlang/types_judgments`** differs under the wasm JIT as under the native one, for the native JIT's
      documented reason (jit.md §4): the test's unbound type variable, symbol 299, is found in the running compiler's
      tables. It stays pending in both JIT lists with that reason.
    - **Self tail calls as loops (remedy (a))**, §6.4: the page's interrupt ends an endless self recursion. Checked
      in node, the wasm JIT's driver in a worker thread on `let rec count(n: Int): Int = count(n + 1)`: before, the
      worker survived `terminate()` and kept node from exiting; after, it ended 7 ms after it. A mutual recursion
      still cannot be ended, as §6.4 says.
    - **Checked:** wasm and wasm-node 299/299, wasm-jit 298/298, jit-files 296/296, jit 16/16, arm64 299/299. The
      lists hold §7's absences (`os/code`, `os/filestats`' modes, `os/process`, `os/value`, readline, and
      `system_run`), and in both JIT lists `types_judgments`.
21. **Speed, as the profile asks.** Step 10's profile named boxing `Int`s (about 10% of self-compilation) and the
    adapters this target does not need (about 8%, §3.2), and calls across units as the hottest functions. So:
    the adapters left out where the closure signatures already agree, by a model of this target in the represent
    pass (§4.1), and the `Int` boxes that remain found and counted before any is removed. Self-compilation in node
    is profiled again before and after, beside arm64's, in [benchmarks.md](benchmarks.md) §25, and the run suite's
    programs are timed in node and wasmtime. Typed arrays (§2.4), specialization on scalar type arguments (§4.1),
    and flat tuples (§2.3) are taken only if the new profile shows them leading.
    *Done when* benchmarks.md records the profiles before and after, and each change is kept or not on its measure.
    *Done 2026-11-15* ([benchmarks.md](benchmarks.md) §25.1):
    - **The adapters** this target does not need are left out: where a pointer and a `QVal` are one `eqref`, a
      closure only boxed or unboxed between them has the generic signature already (`shapes.referencesAlike`, set
      per unit by the backend that runs the passes). Self-compilation in node 64.7 to 60.8 s; kept.
    - **The `Int` boxes**, counted first: hash maps' `insert`, `get`, and `findIndex`, `vector.append`, vectors'
      constructors, and `hexDigest`. Each unit now has its own `boxInt` and `unboxInt`, which V8 inlines, where it
      called the runtime's across instances. 58.4 to 45.1 s; kept. None is removed.
    - **The MLton suite in node:** `benchmarks/mlton/run.py --backend wasm` (node or wasmtime, 7800 KB of node's
      stack). 45 of 46 agree with MLton; raytrace's image differs by msun's last bits against libm's, proven by a
      native build on `util/realmath`. It found two faults, fixed: `isnot` on proxied tuples and options was `is`
      (`language/isnot_shared_tuples`), and a call ending an `if`'s arm, a case, or a join's body was no tail call.
      And it found files written a byte at a time through WASI: a file's writer is now buffered in the core and
      flushed on close, on flush, and when the program ends (ray 518 to 18 s, output1 1893 to 33 s).
    - **Measured at the end:** self-compilation 47.5 s in node against 39.4 s natively (1.21, from 1.63); the
      suite 7.20 times MLton and 3.53 times arm64 (geometric means over the 46).
    - **Not taken:** typed arrays, specialization on scalar type arguments, and flat tuples; the profile is now led
      by the collector (12.7%) and the calls across units into `vector` and `hashMap`, which none of them addresses.
22. **The page's size and start-up.** Step 12 measured 3.9 MB compressed and about a second to the prompt
    locally, three quarters of it the driver's initializers, run cold. This step measures where the initializers'
    time goes, by unit, and what merging the modules (§5.1) saves in size and in compiling; and it tries what the
    measure points to: the initializers' tables built lazily, units the REPL never calls left out of the archive,
    or modules merged at the WebAssembly level, keeping every export.
    *Done when* §5.1 and step 12's figures are measured again, and each change is kept or not on its measure.
23. **Other browsers.** `check.html` run in Firefox and Safari, both modes, and the page used by hand. Each
    engine's support for what this target uses (WasmGC, tail calls, exceptions with `exnref`, a worker's
    synchronous request) is recorded, and its stack in a worker measured as step 12 measured Chromium's (§6.2).
    *Done when* §6.2 and a new note in §6 record each browser's results, and the page says which it supports.

#### 8.4.1. Why These Choices

**The owner's answers, 2026-11-14:** (1) the order stands, the language first; (2) the tail recursion's remedy is
(a), a function's call of itself in tail position compiled as a loop, with the limit for mutual recursion in V8
recorded in this target's documentation (§6.4); (3) steps 21 and 22 are in this milestone; (4) Safari and a recent
Firefox are tested if they can be. After step 23, the work is rebased onto `main` and its conflicts resolved.


- **The order follows the dependencies.** Locations stand alone and are the smallest change, so they come first
  and clear the kernel's finding. Variants come before views because a view's conversion remaps variants' tags,
  and `dynamic` comes after both because its serialization walks every kind of value. `Real`'s mathematics stands
  apart and could move anywhere; it is late because only five tests wait for it. Speed comes after the language,
  so that the profile is taken over code that compiles everything, and the page and the browsers last, since
  they change nothing the suites check. The owner kept this order.
- **Ported, not redesigned.** The C runtime's conversion, views, and proxies are known to be right against the
  goldens; porting them to Quest over the intrinsics keeps the two runtimes printing alike (§4.2). The core's rule
  stands: monomorphic, with no `auto`, `inspect`, or `dynamic` inside it.
- **Step 13's finding 1, the endless tail recursion that cannot be interrupted.** The remedies, for step 20:
  (a) A function's call of itself in tail position compiled as a loop: V8 checks for termination at loops' back
  edges, so the worker can be ended; it covers self-recursion only, not mutual recursion through `return_call`. (b) A count at each function's entry, which also gives a catchable
  `stack.overflow` (§6.3's later addition), at a cost in every call. (c) Neither: the page's interrupt then fails
  only on an endless tail recursion, and the user reloads. The owner chose (a).
- **Speed only where measured.** The profile asked for two things, and the others in §8.4's old list (typed
  arrays, specialization, flat tuples) wait for a profile that asks for them. The owner included step 21.
- **The page's size.** 3.9 MB compressed is most of a real network's start-up, and three quarters of a local
  start-up is the initializers. The owner included step 22.
- **Which browsers.** Safari and a recent Firefox are tested where this machine has them (the owner's answer);
  Chromium stays the one that the checks run.
- **Not in this milestone:** §7's accepted differences stay accepted: `os/process`, `os/code`, `os/value`, and
  readline absent, and tracebacks the raise site only (decision 12). The native JIT's failure on an earlier
  input's tuple field (step 13's finding 3) is a bug of both JITs' shared code, to be fixed apart from this plan.

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
| printing: `conv.real`, `stringBuilder.appendReal` | the dumps of tokens, syntax, typed syntax, and IR; `common/json`; `values/model` | needed (step 8) |
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
