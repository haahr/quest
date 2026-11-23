# WebAssembly: The `wasm` Backend and the REPL in a Browser

The self-hosted compiler has a backend, `wasm`, that compiles Quest to WebAssembly with garbage collection (WasmGC):
Quest's values are the engine's structs and arrays, and the engine's collector is Quest's. The compiler compiled by
that backend runs in a browser page, the REPL at <https://haahr.github.io/quest/>, and there compiles each input to a
module that the page loads into the session, as the arm64 JIT loads machine code ([jit.md](jit.md)). The same
modules run programs under wasmtime and node.

What this document covers: the decisions that shape the design (§1); how values are represented (§2) and closures
called (§3); the compiler's backend and the runtime, which is written in Quest (§4); units, modules, and artifacts
(§5); the page and its session, including what happens when the stack overflows (§6); what differs from the native
backends (§7); the tools and tests (§8); the measurements behind the design (§9); and what is still open (§10).

The design was chosen on 2026-11-12, from four plans written the same day, and built from 2026-11-13 to 2026-11-16
in five milestones: the compiler compiling itself in node, the interpreter in a page, each input a module, the rest
of the language, and the fixes a review found. Code comments cite this document's sections.

---

## 1. Decisions

The owner took these on 2026-11-12. "Easy to change" means the choice can be revisited without redesign; the others
shape every module.

| # | Decision | Hard or easy to change |
|---|---|---|
| 1 | Tuples and options hold their components in a slot array, inside one struct type, not in a struct per arity (§2.3) | hard |
| 2 | Arrays hold `eqref` elements, inside a struct; typed elements would be a later, measured step (§2.4) | hard |
| 3 | Every reference crosses a closure call and a unit's boundary as `eqref`; the receiver casts (§3.2, §5.1) | hard |
| 4 | Self-compilation first; then the interpreter in a page as a checkpoint; then the JIT as the REPL people use | hard |
| 5 | `Real` formatting, parsing, and mathematical functions are written in Quest; no C is compiled to WebAssembly (§4.3) | hard |
| 6 | A location is a (slot array, index) pair, with no dispatch (§2.6) | easy |
| 7 | The shared IR passes are unchanged; the backend boxes at slot operations (§4.1) | easy |
| 8 | A module per unit everywhere, the page included (§5.1) | easy |
| 9 | Uniform entries are wrappers; a tail call through one may cost a frame (§3.3) | easy |
| 10 | The host catches a stack overflow and abandons the input or replays the session (§6.3) | easy |
| 11 | The page does not require cross-origin isolation; an interrupt ends the worker and replays (§6.4) | easy |
| 12 | A traceback is the raise site only (§2.9) | easy |
| 13 | Self-compilation runs in node with a browser's stack; the program suite runs in wasmtime and node (§8.3) | easy |
| 14 | The compiler's own needs came first, with a list of tests pending (§8.3) | easy |

**Common to every design considered:**

- The uniform value is `eqref`. An `Int` or `Word` there is an `i31ref` when it fits and a box otherwise; a `Real`
  is a box; `Bool`, `Char`, and `Ok` are `i31ref`s. Null is no Quest value. (`anyref` would not do: `ref.eq` needs
  `eqref`.)
- A closure has a native entry and a uniform entry (§3.1).
- The backend starts from the described IR, not the SSA, and writes the binary format itself, with a printer to the
  text format beside it.
- One recursion group of runtime types, declared identically by every module (§2.11).
- One exception tag; an exception's identity is a reference (§2.9).
- Every operation that Quest defines to raise is tested before the instruction that would trap (§2.10).
- The runtime is written in Quest over intrinsics (§4.2, §4.5). Bytes cross to the host through a small linear
  memory (§4.4).
- The session runs in a worker, behind an entry that evaluates one input (§6.1).
- wasmtime always runs with `-C collector=copying`: its default collector, reference counting, does not reclaim
  cycles. 20 million rounds of two cyclic objects took 0.9 s and 1.9 GB under it, and 0.12 s and 9 MB under the
  copying collector (2026-11-12).

**Not taken,** so that nobody proposes them again without new evidence:

- *Monomorphizing everything:* polymorphic functions are first-class, type operators are higher-order, abstract
  types are compiled apart, and `auto` and `dynamic` choose types at run time.
- *Typed layouts with type passing:* generic code would read every field through a getter its descriptor supplies,
  and an object's layout would depend on who made it.
- *`Ok` as null:* every test for a kind would then have to mean something for `Ok`.
- *`Int` narrowed to 31 bits:* a change to the language; `Word`, the hashes, and `util/bignum` need 64.
- *A two-value uniform word (`i64`, `eqref`):* slots twice as wide, and generic code no faster (38 against 54 ms for
  a `map`).
- *A runtime in hand-written WebAssembly text or in JavaScript:* thousands of lines nobody can type-check, or a
  runtime absent from wasmtime and slow across the boundary.

---

## 2. Representation

### 2.1. The Shape

As natively, a value has a native representation in locals, parameters, and results of known calls, and one uniform
representation wherever its type is not known to the code that holds it: aggregate slots, type parameters' values,
calls through closures. Natively the uniform representation is a word; here it is an `eqref`.

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
| a location | two values: `(ref null $slots)` and an `i32` index (§2.6) | a slot array of two |
| `auto`, an exception, `Dynamic` | structs of their own | the same |

A slot's type is the nullable `eqref`, so that an array can be made before it is filled. A null read from a slot is
the compiler's or the runtime's mistake, never a value, and no code tests for it.

### 2.2. Scalars

Boxing an `Int` tests its range, which correctness requires: `ref.i31` keeps the low 31 bits silently. The test is
on the 64-bit pattern read as signed, for a `Word` as for an `Int`: the value fits when n + 2³⁰, compared unsigned,
is below 2³¹, one test for both ends (`questlang/wasm/runtime`'s `boxInt`, and the copy each unit has of it). A
pattern that fits is never boxed, so the representation of a pattern is unique, whichever of the two types it has.
Unboxing tests for `i31` (`br_on_cast`) and otherwise reads the box. `is` at a type parameter goes through the
descriptor, as `quest_val_is` does natively, and compares boxed scalars by value; `is` on a box is never `ref.eq`
alone.

Always boxing was measured before the design was chosen: 3.4 times slower in V8 for slot writes and reads, and some
150 to 250 million more allocations for one unit's compilation (2026-11-12).

### 2.3. Tuples and Options (decision 1)

```wat
(type $obj       (sub (struct (field $hash (mut i32)))))
(type $tupleLike (sub $obj (struct (field $hash (mut i32)))))
(type $tuple     (sub $tupleLike (struct (field $hash (mut i32)) (field $slots (ref $slots)))))
(type $option    (sub final $tuple (struct (field $hash (mut i32)) (field $slots (ref $slots)) (field $tag i32))))
(type $proxy     (sub final $tupleLike (struct (field $hash (mut i32)) (field $state eqref))))
```

`$slots` is `(array (mut eqref))`. A tuple of any arity is a `$tuple`; component i is element i of its slots.

- **Width subtyping** needs nothing: a tuple seen at a prefix type is the same object, read at fewer indices.
- **An option's case binder** is the option itself, read as a tuple, since `$option` is a subtype of `$tuple`. The
  payload is shared, with no pointer into an object. Options are values ([extensions.md](extensions.md), "Options
  as Values"), so `is` on options follows those rules and uses `ref.eq` only as a fast path. `opt!tag` makes a new
  tuple, its components copied, after a test of the tag that raises `variant.tagMismatch`.
- **Tags are in name order,** as natively. A case without components allocates nothing: the runtime holds a table of
  such options, one for each tag, made as they are first asked for, and every module takes them from it. `is` does
  not depend on the sharing.
- **A proxy** (a tuple seen at a type whose components the original holds in another form, natively
  [c-representation.md](c-representation.md) §5.8) is a `$proxy` whose state is the core's `Proxied`: the original,
  the type it is stored at, the type it is seen at, and an option's tags in that type's numbering. A type that may
  be proxied is held as `(ref $tupleLike)`; a read tests for `$tuple` (`br_on_cast`) and calls the core only on a
  miss (`unproxy`, `proxyTag`, `proxyElement`, `proxyOptionElement`, `proxyOptionPayload`), each component read from
  the original and converted to the type it is seen at. `type_may_be_proxied` decides which accesses test. Through a
  view map, a component is read through the proxy (`codegen`'s `proxyAware`) and written, or its address taken, in
  the original's slot (`ir.original`). The concrete representation of a type argument with a bound is the core's
  `proxiedType` (`quest_proxied_type`).
- **The runtime reads component i for an i known only at run time** (conversion, printing, proxies, `dynamic`): an
  `array.get`. With a struct per arity it would be a switch over every arity.
- **No limit is near.** The deepest chain of subtypes is five. A struct per arity would have met the engines' limit
  of 63 supertypes and needed a cap and an overflow type. The compiler's widest tuple has 23 components.

*The cost:* a tuple is two objects. Measured against a flat struct (§9.1), in V8 the slot array costs allocation
(1.1 to 1.7 times) and nothing in reads; in wasmtime the flat struct is about twice as fast. Flat structs for small
arities remain the known optimization if a profile asks for it; adopting them would change every tuple access and the
locations of §2.6.

### 2.4. Arrays (decision 2)

```wat
(type $array (sub final $obj (struct (field $hash (mut i32)) (field $elems (ref $slots)))))
```

Every `Array(T)` holds `eqref` elements, so `Array(Int)` and generic code's `Array(A)` are one type, read in place
with no dispatch, and no site must agree with another about an element kind. The struct gives the array its
identity hash; its indirection costs nothing measurable in V8 and about 14% in wasmtime.

*The cost:* a full-width `Word` (the hash vectors of `collections/hashmap`) or a `Real` allocates a box at each
store, about 23 ns in V8 against 1 ns into an `i64` array (§9.2). Small integers do not.

*If a profile asks:* subtypes of `$array` by element kind (`i64`, `f64`, `i8`), with generic code dispatching on the
subtype. That would add containers to §2.6's locations and must hold an invariant that fails silently when broken:
the site that allocates and every site that reads agree on the kind, including for an abstract type whose
representation is an `Int`. Typed arrays box on every generic read and are far slower in wasmtime (§9.2); they would
pay only for `Array(Real)` and `Array(Word)` used at a known type.

### 2.5. Records and Variants

```wat
(type $record (sub final $obj (struct (field $hash (mut i32)) (field $layout eqref) (field $slots (ref $slots)))))
```

A record is a pair, as natively: the payload (`$record`, its fields in name order in its slots) and the view's
table (`$dict`: an `(array i32)` of slot indices and the stored types, null in every static table). `r.x` is
`payload.slots[dict.indices[i]]` and an unbox. Width subtyping pairs the payload with another table. In a slot the
pair is boxed in an immutable `$recBox`. A box cannot be embedded in its aggregate's allocation, so the IR's
`embedded` boxes are ordinary ones here.

- **The layout** is the descriptor of the record type the payload was made at, where the unit makes one (a
  closure's capture record has none). A view's table known at compile time is an immutable global; one known only at
  run time comes from the core (`recordDict`, `viewDict`), memoized.
- **A field a subtype's record may hold at another type** (`x.stored`, [c-representation.md](c-representation.md)
  §5.2) is read through the core's `storedField`.

A variant is a pair of an `i32` tag, in its type's numbering (its cases in name order), and an `eqref` payload, boxed
in an immutable `$varBox` in a slot. A case with no payload carries `ok`. A tag map between two variant types'
numberings (`variantTags`) is a `br_table` of constants. An unboxed tuple holds a record or variant component as its
two parts.

**A boxed value used as a plain one:** a variable may hold a record or variant boxed. `codegen`'s `atomAs` pushes an
atom in the form the target holds it, at returns, jumps to joins, assignments, and declarations.

### 2.6. Locations (decision 6)

A location, what a `var` or `out` parameter receives, is two values wherever it is held, a variable of type `Var(T)`
or `Out(T)` included: a `(ref null $slots)` and an `i32` index. Every address the IR can take is such a pair:

| The IR's address | The pair |
|---|---|
| a local (`@x`), or a temporary (`var(e)`) | a one-element slot array made where the variable is declared, and 0 |
| a record's field (`@r.f`) | the payload's slots, and `dict[f]` |
| a tuple's or a case's component (`@t.i`) | the slots of the tuple after unproxying, and i |
| an array's element (`@a[i]`) | the array's slots, and i, after the bounds test |
| a module's top-level `var` | as a local when only its unit takes its address; one that other units see is a field of the module's record |

The callee reads with `array.get` and an unbox, and writes with a box and `array.set`. Nothing dispatches, and the
semantics are exact, including aliasing. A local whose address is taken lives in its slot array from its
declaration (`codegen`'s `locatedVariables`), and is read and written through it; a record or variant there is its
box. At a uniform entry a location is one `eqref`: a slot array of two, the slot array and the index as an `i31`.

A phrase unit's record holds its `var`s, so a later input reads and assigns an earlier input's `var`.

*Not taken:* accessor closures (an allocation for each `@`, an indirect call for each access); copying in and out (it
loses an assignment when the callee raises, and breaks when parameters alias); a reference object for each `@` (an
allocation at every call); a container and index with dispatch on the container's kind (6 to 9 ns a call in
wasmtime, against 1 to 2 ns, measured 2026-11-12).

### 2.7. Strings

`$string` is a subtype of `$obj` holding a length and a `(ref $bytes)`, `$bytes` being `(array (mut i8))`. Strings
are mutable in place (`string.setChar`), except a read-only one (§2.8). A string literal denotes one static,
read-only string, the same at every evaluation, as natively ([extensions.md](extensions.md#string-literals)):
`codegen`'s `questLiteral` keeps one global for each distinct literal in a unit, null until the literal is first
evaluated, when it is made from the unit's one data segment (`array.new_data`) with its read-only bit set. Making
them on first use rather than as the unit starts spares a unit of thousands of literals the time to make them all.
An empty string is `array.new_default`, so that a unit whose literals are all empty, and so has no segment, is still
valid. The backend's own text (error messages, echo's prefixes) is a fresh, writable string each time, which no
program can name. A string's length is below §2.10's limit, `maxBytes`.

### 2.8. Identity and Its Hash

`is` is `ref.eq` after unproxying, with §2.2's rule for scalars and the options' rules. `hash.identityHash` has no
address to hash: every object with an identity is a subtype of `$obj`, whose `$hash` field takes the next value of a
counter the first time it is asked for: tuples, options, proxies' originals, strings, arrays, records' payloads,
closures (`$clos`), exceptions, and auto values. The boxes are not:

- a scalar hashes by its value, a boxed `Real` by its bits, with the two zeros alike (`wasm.realBits`);
- a boxed record is its payload;
- an option hashes by its case when the case has no components, else by identity, as natively;
- an abstract type's values compare and hash as its representation's (§4.2's registry).

**The read-only bit.** The counter stays below 2³⁰, so the field's bit 30 is free, and marks a read-only string, as
the native header's `Q_HEADER_READONLY` does: a string literal (§2.7) and a string the interpreters freeze
(`runtime/wasm/core`'s `stringFreeze`). `stringSetChar` and `stringSetSub` raise `string.error` when it is set, and
`objectHash` reads the hash below it and keeps the bit when storing one.

A counter's values differ from addresses. The fixed point does not depend on them: `ir/represent` puts an identity
hash's digits in a memo key, but hash maps iterate in insertion order, so no output varies with the hashes.

### 2.9. Exceptions and Tracebacks (decision 12)

One tag, defined by the runtime module and imported by every other, carries the exception's state, a `$raised`: the
exception, its payload, the site of the raise, and the payload's descriptor. Evaluating an `exception` declaration
allocates an `$exception` (a hash and a name); the built-in exceptions are globals of the runtime, and one the
runtime lacks (`readline.endOfInput`) is made once by its unit's initializer. A `try` is a `try_table` that catches
only that tag, never `catch_all`, so a host's exception or another language's passes through unseen. A handler tests
the state's exception with `is` (`exceptionOf`), and one that does not match re-raises with `throw`, the state
unchanged, so the site is kept. A caught exception is a value of `raised.T`.

The engine hides the frames, so a traceback is the raise site, which the raise already carries as text. Run goldens
whose output holds frames are pending under the wasm modes (§8.3). Options, neither built: the JavaScript stack read
at a traced raise, under a JavaScript host; a shadow stack of function names, at a cost to every call. Quest has no
`finally`, so nothing must run while a foreign exception unwinds.

### 2.10. Traps, and `Int` Where WebAssembly Wants `i32`

No handler catches a trap. **No trap is reachable from a Quest program compiled by a correct compiler, except the
stack's and the heap's.**

- **Division and remainder:** the divisor is tested for 0 (raising `int.error` or `word.error`) and for -1 (which
  wraps, as natively) before the instruction.
- **`Real` to `Int`:** the range and NaN are tested (raising `real.error`), then the saturating conversion is used.
  A `Word`'s bits that are a NaN have no `Real` value, and `word.toReal` raises.
- **An index** is compared in 64 bits, unsigned, with the length extended, which catches a negative index and a huge
  one at once and raises the exception the native backends raise; only then is it narrowed to `i32`.
- **A size to allocate:** negative raises as natively; over the maximum is the fatal out-of-memory error (status 70),
  with its message, before `array.new` can trap. The maximum is the least of the engines' figures (§9.4), V8's, so a
  program behaves alike on each: 134,217,720 `eqref` elements (`codegen`'s `maxElements`), and for a string's bytes
  `maxBytes` (`questlang/wasm/runtime`, 2³⁰; but see §10).
- **An option's ordinal out of bounds** is the fatal error that natively it is.
- **A failed cast or a null** cannot happen. Where a program's values decide (unboxing, a proxy), the code is a
  `br_on_cast`, which does not trap. A trap is reported by the host as an internal error.

So an array has fewer than about 2²⁷ elements on this target, and a string fewer than 2³⁰ bytes.

### 2.11. Types Across Modules

A type is identified by its recursion group's structure and its position in the group. Types declared apart with the
same structure are one type, which a cast could then not tell apart.

- **One group, R, holds every type the runtime defines or code tells apart by a cast:** `$boxInt`, `$boxReal`,
  `$slots`, `$bytes`, `$i32s`, `$obj`, `$tupleLike`, `$tuple`, `$option`, `$proxy`, `$string`, `$array`, `$record`,
  `$dict`, `$recBox`, `$varBox`, `$clos`, `$auto`, `$exception`, and `$raised`. Position makes its members distinct,
  so no later edit can merge two. Every module declares R first, from one table (`questlang/wasm/runtimetypes`).
  Descriptors and view maps are not in R: they are Quest tuples of the core (§4.5), and a type of R that refers to
  one holds it as an `eqref` (`$record`'s layout, `$auto`'s descriptor).
- **Standing alone, and meant to merge by structure:** function types, the closure types of §3.1 for each signature,
  and each function's own closure type. Leaf types are `final`, which lets V8 cast with one comparison.
- **A change to R is a change to the ABI** (§5.3): a module compiled against another R fails to link, since an
  import's type does not match.

The engines' limits, measured: 50,000 locals in a function, so `questlang/wasm/locals` reuses them (§2.12); 10,000
struct fields and 10,000 operands of `array.new_fixed`, so a tuple or array written out is at most 10,000 long and a
closure's captures fewer; 1,000 parameters and 1,000 results; a function's size (7.6 MB); 100,000 data segments; 63
supertypes. A limit reached is a compile-time error naming what reached it.

### 2.12. Reference Locals

Validation requires a local of non-null reference type to be set before it is read, and forgets at a block's end a
set made inside it. A variable bound once is set where it is bound and is non-null. A join point is a block whose
results are its parameters, set just after the block's end. A mutable variable assigned inside nested blocks is
declared nullable. An `out` parameter's target is a slot, which is nullable already.

**Locals are reused** (`questlang/wasm/locals`, run on every function of every module): each local's live range, from
its first use to its last and widened over a loop it may carry a value around, is found; then the locals, in order
of where they start, each take the first slot of their type whose locals have all ended. The baseline compiler gives
every declared local a slot on the stack (§9.4), so this is for the stack as much as for the limit: the interpreter's
`evalExpr` went from 1,211 locals to 29.

---

## 3. Closures

### 3.1. Two Entries

`$clos` is in R. For n value parameters, `$closU(n)`, a subtype, adds the **uniform entry**: a function of the
closure, its descriptors, and n `eqref`s, giving an `eqref`. For each closure signature S (§3.2), `$closS`, a subtype
of that, adds the **native entry**. A function's own closure type, final, adds the descriptors the closure supplies
(its type arguments, if any) and then its captures, as mutable fields, so that a recursive group of closures
(`sLetRec`) can be made first and filled in after; a record or variant capture is two fields. Only the function's own
code reads them. A function that captures nothing has one closure, a global.

**The uniform entry's n counts Quest's value parameters, not WebAssembly's.** Each is exactly one `eqref`,
whatever it is natively: a record is its `$recBox` and a variant its `$varBox`, though each is two values in a
native signature; a location is a slot array of two (§2.6); an `Ok` is the `i31ref` 0. The result is exactly one
`eqref`. So every function type of n parameters has the one uniform type, which is what lets any caller use it.

**Every entry takes its closure first, as `(ref $clos)`,** the base type in R, never as its own closure type, and
casts it in its body when it has captures. An entry typed by its own closure type would make the function type and
the closure type refer to each other, which puts them in one recursion group; as it is, each stands alone and merges
across modules by structure (§2.11). A direct call of a function that captures nothing passes a shared closure,
`noClosure`, that the callee never reads.

- **A known callee** is called directly.
- **A call through a closure** whose static type has closure signature S tests the closure for `$closS`
  (`br_on_cast`) and calls the native entry. When the test fails, it boxes the arguments, calls the uniform entry,
  and unboxes the result.
- **The uniform entry** of a function unboxes, calls the native entry, and boxes the result. When S has no scalar,
  record, variant, or location, S is the uniform signature and one function is both entries.

So a function value can be called at any type it has, with no conversion, and may sit in any array or `var` slot:
this representation has no need of the conversions C rejects because a function's signature differs inside mutable
data ([c-representation.md](c-representation.md) §6.4.5). The represent pass still rejects them, so that both
targets accept the same programs, and still wraps a function passed at a generic type in an adapter, which is
another closure under `is`, as natively (§3.2, §4.1). The test costs nothing measurable in V8, and the uniform entry
ten times a native call.

**Built-in operators as values** (`Int`'s and `Real`'s arithmetic, `^^` by `util/realmath`, `<>`, `Bool`'s eager
`/\` and `\/`) are static closures with both entries.

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
| a `var` or `out` parameter | `(ref null $slots) i32` |
| every other type: strings, tuples, options, arrays, functions, abstract types, type parameters | `eqref` |

Each quantifier adds a descriptor, an `eqref`, before the value parameters; a function with type parameters only
takes its descriptors and gives its result. A type application (`opTypeApp`) is a call with descriptors alone. A
function casts each reference parameter once, at entry, into a local of its precise type.

**Every function has this signature, not only closures' entries and exports.** Precise reference types appear in
locals only. `return_call` and `return_call_ref` require the callee's result type to be a subtype of the caller's,
so a function whose result were a `(ref $string)` could not tail-call one that gives an `eqref`. With one rule for
every signature, any call in tail position whose results agree in kind can be a tail call (§3.3). The one exception
is a function the `unbox` pass has given an unboxed result (§4.1): it returns its tuple's components as several
results, at their closure-signature types, and is only ever called directly.

**The signature is computed after bounds are resolved,** as `layout.resolvedShape` does for every backend: a type
parameter or an abstract type with a bound has its bound's representation (two values for a record's, an `i64` for
`Int`'s), and only one without a bound is an `eqref`. The bound is in the interface, so exporter and importer agree.

**An `Ok` is a value wherever a value is expected:** a parameter, a result, a local, a slot. The represent pass gives
no plan when either side of a conversion is `Ok`, so nothing in the IR marks where an `Ok` meets a type parameter or
a slot, and an `Ok` that were nothing in some places would have to be made or dropped at crossings the backend could
not see. Natively an `Ok` parameter is a word for the same reason. As a result a wrapper has nothing to push after
its call, and a callback of a scalar parameter and an `Ok` result, which is every `iter`-style callback over `Int`s,
is tail-called through its uniform entry (§3.3).

The signature is computed from the type alone, with a type parameter as `eqref`. So a closure made for `String ->
Word` has the signature that generic code computes for `K -> Word`, and `hashMap`'s calls of a string's hash and
equality take the native entry with nothing boxed. A closure whose own signature has a scalar where the caller's has
a type parameter (`hash.int` at `K -> Word`) would fail the test and go through the uniform entry, but the represent
pass already wraps such a function in an adapter of the generic signature, its `adapt` plan, wherever a parameter or
the result needs a `box` or `unbox` (the compiler has 813 such conversions). The adapter's closure signature is the
generic caller's, so the caller's test succeeds and nothing is boxed but the key, an `i31ref`. Adapters C needs and
this target does not (for `hash.string` and `stringOp.equal`, where a pointer is boxed to a word natively) are left
out: the backend sets `shapes.referencesAlike` for its units (`choice.referencesAlike`, which arm64 shares), and the
pass makes none where both sides are references.

**Function adapters for a view's change** (a closure seen at another function type, `quest_convert`'s): the backend
builds `$adaptN` and a maker for each uniform arity up to 8 when it compiles the core. A unit that calls a closure
wider than that (`arityPast`) makes its maker and registers it (`registerAdapter`); the core's `adapterFor` finds it,
or raises `dynamic.error`.

*Not taken:* every unknown call through the uniform entry (ten times slower); C's single entry with adapters (an
`i64` and an `eqref` never agree, so nearly every function crossing into generic code would need one); one `(ref
func)` with a cast at the call (a wrong cast traps).

### 3.3. Tail Calls (decision 9)

Tail calls are made "whenever possible, not as a guarantee of the language" ([arm64.md](arm64.md)): `return_call`
and `return_call_ref` wherever no code must run after the call. That is every direct call and every native-entry call
in tail position, and a uniform entry's call when the result is a reference.

- **Tail position is found by the backend, through join points:** a call is in tail position when its result reaches
  a return by any chain of jumps to join points whose continuations only pass it on, including a call that ends an
  `if`'s arm, a case, or a join's body. Natively `ssa/passes/tailcalls` finds these on the SSA, which this backend
  does not have, so it repeats the analysis on the described IR; the simplifier turns a jump to a join that only
  returns into a return. Without it, loops the native backends run in constant stack nest.
- **No call inside a `try`'s body is a tail call,** since it would leave the handler (`LabelKind.labelTry`,
  `insideTry`).
- **A function's call of itself in tail position is a loop:** it sets the parameters and branches to a loop around
  the function's code, which starts after the prologue (captures read, view maps made). V8 checks for termination at
  a loop's back edge and at no tail call, so this is what lets an interrupt end such a recursion (§6.4).
- **An accumulating recursion is a loop too,** as the SSA's accumulate pass makes it natively: a function returning
  an `Int`, one of whose blocks returns its own call's result plus (or times) another value, adds (or multiplies)
  that value into an accumulator and branches to the loop; each other return gives what it returns combined with
  the accumulator, which starts at the operation's identity (`accumulation`). A function with a `try` is not
  converted, and in a converted one no other tail call is made, since it would return without the accumulator.

A uniform entry that must box its result, and a caller that must unbox one, leave a frame. A loop written through
closures that passes through one each time around grows the stack where natively it does not. With §3.2, and `Ok`
results returned as values, that needs a closure whose result is a scalar, a record, or a variant, called at a type
parameter, in a cycle. A callback that a loop calls and that returns to it, as `fold`'s does with a scalar
accumulator, is not such a cycle: its frame is gone before the next step. It is an accepted difference (§7); the
remedy, if a real program needs it, is a second compilation of the body as the uniform entry.

---

## 4. The Compiler and the Runtime

### 4.1. Where the Backend Forks (decision 7)

```
typed AST → lower → Core → simplify → specialize → closure-convert → unbox → represent → describe → wasm
```

`unbox` (`ir/unbox`) gives a known local function that returns a tuple an unboxed result: its returns give the
components (`sReturnTuple`) and its direct calls bind them (`sLetTuple`). Here those are WebAssembly's several
results.

The shared passes, `repr/layout`, and the native backends' goldens are unchanged. The represented IR has no
conversion where a scalar meets a slot (`slots` asks `layout.isBoxedInSlots`, true only of records and variants);
the native backends convert in the SSA's builder. The wasm backend does the same in its own code generator: every slot
operation (making a tuple, reading a component, an array's element, a record's field, a store) boxes or unboxes by
the slot's static type, and the IR's `box`, `unbox`, `slot_box`, and `slot_unbox` plans become real conversions.

**What each of the pass's plans means here.** The pass decides its plans from C's layouts ([ir.md](ir.md) §8.3), so
some are made for reasons this target does not have. Each still has a meaning that is correct:

| Plan | On this target |
|---|---|
| `box`, `unbox` | a real conversion: a scalar to and from its `eqref` (§2.2), a record or variant to and from its box |
| `slot_box`, `slot_unbox` | as natively: a record's or variant's box made, reused, and read |
| `record_view`, `variant_tags`, `view`, `unproxy` | as natively, by the ported runtime |
| `cast` | nothing, or a cast between reference types |
| `copy` | as natively: a new tuple, each component by its own plan |
| `adapt` | as natively: a closure of the target's signature that converts and calls, made where C's signatures differ (less those §3.2 leaves out); correct either way, since any closure can be called at any signature |
| `runtime` | the ported `quest_convert` between the two descriptors, in which a function's layout never differs: only views convert, as proxies. Where C copies a tuple because a closure among its components changes signature, this target keeps the original |
| rejected | a compile-time error, as natively |

Two consequences, both accepted (§7): the pass rejects on this target what it rejects for C, though §3.1's closures
would run those programs, so both targets accept the same language; and `is` answers true here on a tuple that C's
`runtime` conversion copied.

Control flow maps directly: the IR is structured, a join point is jumped to only from its own body
([ir.md](ir.md) §6.3), so a join is a block, a jump a `br`, a `loop` a `loop`, a `switch` a `br_table` on the tag,
and a `try` a `try_table`. What the SSA's passes do natively is the engine's job here, or is lost.

**What the backend cannot compile:** in a program's unit or the runtime's, a compile-time error naming it
(`unsupported`); in a module's unit, the function becomes one that ends the program, with a message naming it, when
it is called, so that a library unit with one such function still serves the rest.

The bootstrap compiler gets nothing, as with every backend since the C one.

### 4.2. The Runtime in Quest

The C runtime cannot touch the engine's objects. The collector is not needed; the rest exists again, in Quest, in
unsound modules ([modules.md](modules.md) §4.4) over intrinsics the backend compiles in place (§4.5). It was ported
from the C as it stands, function by function, not redesigned, and the two runtimes must agree to the byte on what
programs print, which the shared run goldens check.

**The runtime is in layers, so that imports stay acyclic** (§5.1). The library's externals are the runtime's
functions, so a runtime module that imported a library unit would be imported by it in turn: `collections/hashmap`
imports `util/hash`, whose `identityHash` is the runtime's.

- **The base** (`questlang/wasm/runtime`), beneath everything, is not Quest: a module the backend builds instruction
  by instruction. It holds what Quest cannot say: the exception tag and the built-in exceptions, the memory and the
  host's imports, WASI's functions among them (§4.4), `Int`'s boxing, string's externals, and the text that output,
  conversions, and the uncaught and fatal reports need. Quest code names one of its exports as the external
  `wasm.base.FIELD`.
- **The core** (`runtime/wasm/core`), C's `quest_types.c` and `quest_views.c`: descriptors and their instantiation,
  memoized, so that one instance is one descriptor; run-time subtyping (`isSubtype`, coinductive, with binders and
  fuel for quantifiers as the type checkers have them); `quest_convert` (`convert`, `convertAuto`); proxies; view
  maps (`viewMap`); the record tables (`recordDict`, `viewDict`, `storedField`); `is` at a descriptor (`valIs`) and
  the identity hash; the registry of abstract types' representations (`registerAbstract`, filled by each module where
  it begins); and the library's externals that are Quest on this target: strings' comparisons and joins, the string
  builder's buffer, and over WASI `system`'s arguments, environment, files, and directories, `os/filestats`'
  `rawStat`, buffered file writers, and a buffered reader. **Its code is monomorphic:** it defines descriptors and
  their instantiation, so it can use no type parameter whose descriptor would have to be instantiated to run it, and
  no `auto`, `inspect`, or `dynamic`. And it can run no library unit's Quest code, since every library unit imports
  it: it uses no `maybe`, `vector`, or `hashMap`, but tables written out over arrays and searched in order, and takes
  `string`, `system`, `real`, `writer`, and `reader` only for their externals and exceptions, which the backend
  compiles in place (`codegen`'s `isUnitImport`).
- **Above it**, units that may import the library: `runtime/wasm/print` (printing and echo, `quest_print.c`), and
  `runtime/wasm/dynamic` (`dynamic`'s serialization, `quest_serialization.c`), which `lib/dynamic.wasm.mod.quest`
  calls for `intern` and `extern`. `util/realconv` and `util/realmath` (§4.3) serve both, and are compiled as
  ordinary library units. None of the units they import may echo.

**The library's externals.** `lib/` names 174 external values, and the compiler links all of them. Each maps, by
`codegen`'s table, to an instruction sequence in place, a function of the base, or a function of a runtime unit in
Quest; `tests/python/test_wasm_externals.py` checks that the table covers `lib/`. One with no counterpart fails
when it is called, with a message naming it, not when it is compiled: `system.run` and `os/process` raise
`system.error`, `os/code` and `os/value` raise `value.error` (except that `code.symbol` answers that there is no
such symbol, as natively for a name the binary lacks, since `questlang/driver/interrupts` asks at its top level),
and readline's functions raise `readline.error`, `quest_readline_editing` being 0. `rawStat`'s mode is `0o644` or
`0o755`, since WASI has no permission bits.

**File output** is buffered and given to WASI 64 KB at a time, flushed when a writer is flushed or closed and at
exit, as C's stdio buffers it; a byte at a time, a call into the host each, two of the MLton benchmarks took 50 and
37 times as long as natively. The base's `putString` and `putChar` loop until everything is written, retrying
WASI's "try again", and the core raises `writer.error` on any other error. A closed writer refuses to write.

**Fatal errors and exit.** A fatal error under a host that runs inputs (the JIT, §6.1) is held: the runtime keeps the
report (`holdFatal`, `fatalReport`) and traps, and the host reports it. `system.exit`'s report is empty and is never
held, so it ends the run even while an input runs. wasmtime cannot exit with a status above 125: under the driver
(`QUEST_WASM_EXIT_LINE`) the core's `exitStatus` exits with 125 and writes a last line `quest: exit status N` to
standard error, which the driver turns back into status N.

### 4.3. `Real` (decision 5)

WebAssembly's `f64` instructions cover arithmetic, `sqrt`, `floor`, `ceil`, `trunc`, `nearest`, `abs`, `min`, `max`,
and `copysign`, exactly, on every engine. It has no other mathematical function and no formatting or parsing, and
neither has WASI. JavaScript has both, but wasmtime's command line cannot import them, browsers need not agree on
`Math.sin`'s last bit, and `Number`'s text differs from Quest's (`-` for `~`, no `.0` on whole numbers, exponents
past 1e21 rather than 1e16). So both are written in Quest, and no C is compiled to WebAssembly: the owner chose
against the toolchain a helper compiled from C would add.

- **Formatting and parsing:** `lib/util/realconv`. The C runtime's `quest_shortest_digits` asks libc's `snprintf`
  for the correctly rounded decimal of p digits, for p from 1, tries it and its two neighbors, and keeps the first
  that `strtod` reads back as the same value. `realconv` is those two libc functions' parts, in exact arithmetic,
  and the loop as it stands:
  - *the correctly rounded decimal of p digits:* a double is an integer times a power of two, exactly, so this is a
    big-integer multiplication or division by a power of ten and a rounding to even;
  - *the correctly rounded double of a decimal:* a big-integer division gives the 53 bits and what is left decides
    the rounding, with subnormals and overflow as cases. A decimal is read to 800 significant digits and a sticky
    one, so reading a long number is linear.

  Being exact, they give libc's digits, which the shared goldens check. Reading back a candidate is not a second
  parse: it reads back when it lies between the midpoints that separate the real from its neighbors. `realconv` does
  not use `util/bignum`, which imports `util/strutil` and `conv`, whose real conversions this unit provides on this
  target: it has its own natural numbers, whose limbs are below 2³⁰ so that in an array they are `i31ref`s and never
  boxed. It imports only `word`, `string`, and `ascii`. A real's bits are `word.fromReal` and `word.toReal`, one
  instruction each. `real.format` is `realconv.format`, printf's `%e`, `%f`, and `%g` over the exact digits; `%g`'s
  ties follow C's rule on both targets.
- **The mathematical functions:** `lib/util/realmath`, FreeBSD's `msun` ported line for line, each of C's expressions
  braced in C's order of evaluation, since Quest's operators associate to the right. Where msun returns NaN the port
  raises `real.error`, as the C runtime's wrappers do after libm. Built natively from FreeBSD's sources and compared
  on 229,905 values, the port's results are msun's to the bit. Against Apple's libm they agree within 1 ulp, or 2
  for the hyperbolic functions and `pow`, or 3 for `tan`; the exception is msun's least accurate case, `pow` of an x
  within 2⁻²⁰ of 1 to a power beyond 2³¹, hundreds of ulps from libm's. Goldens that print the functions' results
  print 12 significant digits, so none needed recording for this target. The backend imports `util/realmath` into
  every program beside `wasm/print`, for `^^`. Both units take `real` only as externals, which compile to
  instructions, since `real`'s own module calls them.

### 4.4. The Host, and Bytes Across It

Neither JavaScript nor WASI can read a GC array. The base has one linear memory, used only as a buffer for what
crosses. Text out is copied from the string's bytes into the buffer, and the host is called with a length; text in
arrives in the buffer and is copied into a new byte array; a large string crosses in pieces of 1 MB
(`wasm.base.stringToMem`). A `String` is bytes on both sides, so nothing is transcoded. Each copy is a loop: about 2
to 11 ms for the compiler's 4 MB of source, once in a build. JavaScript's string builtins and `externref` strings were
not used: they tie the runtime to one host and are absent from wasmtime.

The host interface is WASI's first preview, `wasi:NAME` among the base's imports, which the core calls: streams and
files, directories (the host's preopened ones, from descriptor 3 up), a path's stat, renaming and removing, the
arguments and the environment, the clock, and exit. It is implemented by wasmtime, by node's `node:wasi` for
programs (`runtime/wasm/run.mjs`), and in JavaScript for sessions, in node and in the page alike
(`runtime/wasm/host.mjs`, §6.1); keeping `node:wasi` for programs keeps two WASI implementations compared. Under a
session the host adds `quest.host`'s imports for the JIT (§6.1).

### 4.5. The Intrinsics

The runtime's units are Quest that must reach what no Quest type exposes: a value's kind, an object's slots and hash,
a string's bytes. An intrinsic is an external named `wasm.NAME` that a runtime module declares itself, at the types
it uses it at, and that the backend compiles at each call, by its name, from its arguments' types and its result's:

```quest
let toInt(x: core.Any): Int = external "wasm.fromAny"
```

- **`Any`** is `external "eqref"`, every value as a slot holds it, which the backend holds as an `eqref`. A value
  crosses into and out of it by `toAny` and `fromAny`, compiled as §2.2's box or unbox **for the type the
  declaration gives**, so no descriptor is needed and the core stays monomorphic.
- **The set** is what the runtime's units use: `same` (`ref.eq`), `toAny`, `fromAny`, `hashOf` and `setHash`, the
  tests of a kind (`isRecBox` and the like), the slots of tuples and arrays (`tupleCount`, `tupleSlot`,
  `arrayCount`, `arraySlot`), records' fields through their tables (`recordField`, `recPayload`, `recDict`),
  `optionTag`, `variantTag` and `variantPayload`, `exceptionName`, `realBits`, and `autoPayload`; the base's text
  (`decimal`, `hex`, `escaped`, `charString`, `put`); and for the JIT, `wasm.host.NAME` (the host's imports, `Int`s
  as `i32`), `wasm.print.capture` and `captured`, `wasm.raisedName` and `raisedSite`, `wasm.importedRecord`, and
  `wasm.recordSet`.
- **A misused intrinsic** is the runtime's bug, not a program's: `fromAny` at the wrong type, or a slot past the end,
  traps, and the host reports an internal error.

**Descriptors are Quest values, as tuples.** A descriptor (`QTypeDescriptor`'s counterpart) is a value of the core's
tuple type `Desc`: its kind, name, parts, labels, a tuple's type components' positions and texts, and each part's
flags (1 var, 2 out, 4 a function's result, 8 a quantifier's bound, 16 the representation a document recorded for an
abstract type, 32 an auto type's bound), as C's have them. A tuple and not a record, because a record held in a slot
is a box over a payload read through its table: two indirections on paths that polymorphic `is`, hashing, and echo
take for every value. A recursive type's descriptor is cyclic, its parts filled in after it is made. A unit's
initializer makes the descriptors its code needs (`StaticData`) by calling the core's constructors (`base`,
`newDesc`, `setPart`, `setText`, `boundVar`, `instantiate`), before its top level runs; instance names are cut at 80
characters.

**How compiled code reaches the runtime.** Every unit the backend compiles imports the core, except the runtime's own,
and `is` at a type parameter, instantiation, conversion, proxies, and view maps are calls of the core's functions by
name. Echo calls `wasm/print`. An uncaught exception reaches the program's `_start`, the inits of its units
included: `$raised` carries the payload's descriptor, and `_start` writes the payload with `wasm/print`'s `show`
and passes the text to the base's report; a payload the base can write itself (kinds 1 to 8: `Int`, `Bool`,
`Char`, `String`, `Ok`, `Word`, a function, an abstract type's value) needs no descriptor. The driver builds the
runtime's units from `runtime/wasm/` with the build's other units, and preloads them before every other.

---

## 5. Units and Linking

### 5.1. A Module for Each Unit (decisions 3 and 8)

Each unit is a WebAssembly module, for programs, for the driver in the page, and for each input. It exports its
initializer, `init`, its record's two globals (payload and table), and each of its functions at its *interface*'s
closure signature (§3.2), through a wrapper where the function's own signature differs; it imports the base, the
core, and what it uses of other units, by unit name (a library unit's by its path in `lib/`). wasmtime links with
`--preload`, node and the page with a loader of a few lines, in the order of the import section. Imports among units
are acyclic ([modules.md](modules.md)), so the modules can be instantiated in order.

An exported function's signature is computed from the interface alone, which the exporter and every importer see
alike. So tuples that may or may not be proxied, and abstract types, all cross as `eqref`, and an abstract type whose
representation is an `Int` crosses boxed, as a module's abstract types convert at its boundary in C.

Initialization is explicit, as in C: a unit's `init`, guarded by a global, calls its imports' `init`s in the order of
its import list, then its inline modules', then runs its own top level. WebAssembly's start functions only build a
module's static data, since their order is the loader's. A function imported from another unit needs no guard: an
importer's code runs only after its `init`.

**The page's driver is these same modules,** 154 of them: the variants of `codegen/native` and `driver/ssaphases`
for this target (§5.3) leave the SSA's and the native backends' units out. They are served as one archive, fetched
once and cut into modules by the loader, since a request each would cost far more than the instantiation (13 to 15 ms
for all of them). The IR's whole-program build is not used for the driver: it sees through abstract types to their
representations, so its layouts would disagree with an input compiled apart. Merging the modules at the WebAssembly
level, which keeps every export, is a possible optimization of size and start-up, not taken.

**A phrase unit** (a REPL input) is compiled as a module file's unit, though its manifest marks it a program: its
`init` runs its top level, and the modules it declares are exported as `qj_N_k.FIELD`.

### 5.2. Files in a Page

A URL prefix is a `QUEST_PATH` directory: the page is given prefixes, and an import looks under each in turn,
fetching source, which the compiler in the page compiles or the interpreter runs. A worker may make a synchronous
request (an `XMLHttpRequest` that is not asynchronous; `fetch` is always asynchronous), so the compiler's file reads
stay as they are. Only "not found" (404 or 410) moves the lookup to the next prefix; any other failure is an error at
the import. A synchronous request is deprecated on a page's own thread, not in a worker, and it follows CORS as any
request does. Its real costs are a round trip for each file and a logged 404 for each prefix that lacks one, which is
why the library is not served that way.

**The compiler never sees a URL.** Its paths are POSIX's: `path.isAbsolute` tests for a leading `/`, and
`modules/paths` leaves out a library directory for which `system.isDirectory` is false. So the host mounts each
prefix at an absolute path of its own, `QUEST_PATH` names those, the host answers `isDirectory` for a mount, and it
turns a path under it into the prefix's URL inside its own file calls. In the page the working directory is `/work`,
`QUEST_HOME` is `/quest`, the library is `/quest/lib`, and the user's prefixes are `/remote/N`.

The library is served as an archive of its files (`lib.qar.gz`, about 54 KB compressed), fetched once when the
session starts, after which a lookup under it makes no request. `.qi` texts are made in the session's memory, from
the interfaces, as the native JIT makes them; shipping the release's `.qi` files was measured and not taken (a first
input importing eleven library modules took 364 to 381 ms without them and 369 to 397 ms with them).

### 5.3. Artifacts

A `.qi` holds nothing of a backend, and one serves every target. A unit's code is a `.wasm` where a `.o` would be,
and wasm builds have a directory of their own. The ABI version stays one number, bumped for a change to either
runtime or to R. Two custom sections make an object's provenance checkable:

- **`quest.fingerprint`,** the unit's fingerprint ([jit.md](jit.md) §3.3.1), read by the host with
  `WebAssembly.Module.customSections`; its digest is the native one.
- **`quest.runtime`,** `backend.runtimeStamp()`, a hash of the base module's encoding. An object whose stamp differs
  was built against another wasm runtime and is stale, and is rebuilt.

A `.qm` written by another backend is already stale: the build engine (`questlang/build/engine`, "compiled by the …
backend") compares the manifest's backend with the one the build assigns the unit.

**Module variants.** A unit may have variants, `NAME.VARIANT.mod.quest` beside `NAME.mod.quest`, and the build takes
the variant named for the backend it compiles with, or the one `--variant UNIT=VARIANT` names
([build-process.md](build-process.md)); the manifest records it. `questlang/jit/target` has `target.wasm` (the JIT
of §6.1) and `target.none` (no JIT, for the driver run under wasmtime, built by hand with `--variant
questlang/jit/target=none`); `codegen/native` and `driver/ssaphases` have `wasm` variants that leave the native
backends out; `lib/dynamic` has a `wasm` variant that calls `runtime/wasm/dynamic`.

---

## 6. The Page

### 6.1. The Session

The driver runs in a worker. Its session speaks the kernel's protocol ([jupyter-kernel.md](jupyter-kernel.md)):
`execute`, `complete`, `inspect`, and `isComplete`, as JSON. Under `QUEST_HOST_SESSION`, `--kernel` or `-i` makes
the driver's `_start` return with its session held (`questlang/driver/kernel`'s `serving`), and the host calls its
exported `request` with each request; requests arrive on `/dev/fd/3` and records leave on `/dev/fd/4`. The page owns
the loop, the prompt, and line editing; `io/readline` is not used. One host, in JavaScript, serves node and the page
(`runtime/wasm/host.mjs`, with `session.mjs` for the session and `session-node.mjs` to run one under node), so the
page's host is the one `tools/check` tests.

**With the JIT** (`questlang/jit/target.wasm`, the default), evaluating is still one request: the driver compiles the
input, gives the host its module's bytes directly (`give`), and calls the host to load the module (`load`) and to run
it (`run`). The host runs the input's code inside its own function, which catches an engine's stack overflow, a
trap, or a held fatal error (`run` returns 1, 2, or 3), so an error caught there unwinds only the input's frames and
those of the library and runtime it called; the driver's frames below are intact, and the input fails as if it had
raised. A Quest exception crosses the host's frame to the target's handler. `has` and `fingerprint` let the driver
reuse its own units for an input's imports. The page's `?jit=0` interprets instead.

### 6.2. The Stack

A Chromium worker has about 512 KB of stack and a page's thread about 1 MB, against 8 MB natively, and a page can
change neither. JSPI and stack switching give no deeper stack, and a page cannot set the engine's flags.

- **The compiler fits ordinary inputs, cold.** V8 runs cold code in its baseline compiler, whose frames give every
  declared local a slot (§9.4), and a page's first inputs run the compiler cold; reusing locals (§2.12) is what makes
  it fit. What does not fit is the front end's nesting, about 1 KB of stack a level, as natively (0.9 KB): a chain of
  498 additions is the longest a new session's first input takes in node's worker. Longer ones overflow in the
  compiler and replay (§6.3).
- **Compiled code fits:** about 100 bytes for a small function's call in baseline code and about 30 when optimized,
  and about 8 bytes more for each local. An input's recursion that is not in tail position (`1 + down(n - 1)`)
  reaches about 5,300 calls in Chromium, the driver's frames below it included, and further overflows in the input's
  own code, rolled back with no replay.
- **The interpreter does not reach its own limit of 1,000 calls:** 753 calls of a simple body and 175 of a nested one
  in 512 KB. So **the session's call limit is the engine's** (`session.mjs`'s `callLimits`, `QUEST_CALL_LIMIT`):
  about two thirds of the cold depth, 150 in Chromium and node, 250 in Firefox, and 80 in Safari and any engine not
  known, so that the interpreter raises its own `stack.overflow`, never the engine's.

**In each browser's worker** (2026-11-15, each browser fresh):

| Browser | JIT: `1 + down(n - 1)` | Interpreted: simple, nested body | Longest chain of additions, JIT / interpreted |
|---|--:|--:|--:|
| Chrome 157 | 5,476 | 769, 492 | 469 / 469 |
| Firefox 160 | 96,893 | 1,619, 1,198 | 1,060 / 1,060 |
| Safari 26.6.2 | 24,779 | 575, 348 | 349 / 466 |

The nested body there is lighter than the one the limits are set by (a tuple, a `let`, a loop, and an `if` around
the call), which, called once in a new session so that its code runs cold, reaches 181 calls in Chrome, 378 in
Firefox, and 117 in Safari, whose depth varies.

Tests under node constrain the stack to a browser's (`--stack-size`, or a worker's `resourceLimits`; a node worker
keeps 192 KB of its stack, so `session-node.mjs` asks for that much more), or they would pass where a browser fails.

### 6.3. When the Stack Overflows (decision 10)

No handler in a module sees the overflow: wasmtime traps ("call stack exhausted"), V8 and JavaScriptCore give
JavaScript a `RangeError`, and SpiderMonkey an `InternalError`, "too much recursion" (the hosts' `isStackOverflow`
takes both, and a file call that meets one rethrows it). The Quest code that would roll a failed input back does not
run. The host catches the error at the entry, and what it does depends on what was running:

- **An input's compiled code:** the session's bindings change only when an input commits, so the host's `run` gives
  the driver the overflow, the driver rolls the input back as it does a raise, reporting `stack.overflow`, and the
  session goes on. What the input had already done to earlier inputs' state stays done: a store to an earlier
  `var`, to an array's element, to a string, as after a raise ([jit.md](jit.md) §3.2). This is better than native,
  where the session ends.

  The overflow lands in the deepest frame, which may be the runtime's, part way through an update of one of its
  shared tables: a point where no Quest raise can occur, and nothing rolls it back. So the core counts, in a global
  (`updating`), the updates in progress of its caches (instances, record tables, view maps), each made visible by one
  final store where it can; the registry of abstract types and the bound variables are safe to leave half updated.
  The host reads the count after catching the error: zero, and the input is abandoned as above, after `recover` in
  `wasm/core` and `wasm/print` empties the proofs in progress (subtyping's and equivalence's trails) and print's
  nesting and witnesses; not zero, and the session is replayed as below, once the request ends. A user's own data
  structure caught half updated is the user's, as when an interpreter raises `stack.overflow`.
- **The compiler or the interpreter,** or an exception that escapes the driver (`WebAssembly.Exception`): their
  structures may be half updated. The host ends the worker, starts another, and replays the session's committed
  inputs with their output suppressed (a new worker starts quiet), then reports the overflow for the failed input.
  Replay runs the inputs' effects again and assumes they give the same results. Each committed input records the
  names it bound; a replay that cannot run one again says so and goes on: `quest: the session started again, and N
  inputs that ran before did not run again; no longer bound: ...`.

  Replay compiles each input again; keeping each committed input's module to run it without compiling was measured
  and not taken: an overflow's replay of 18 committed inputs takes 64 to 141 ms in Chromium, and an interrupt's,
  which starts a new worker, 106 to 689 ms, most of it the new worker's start.
- **Under wasmtime or node, a program:** the run ends, reported as `Exception: stack.overflow` with status 1, as
  compiled code's overflow ends it natively.

A count at each function's entry that raises a catchable `stack.overflow` first is a possible addition, at a cost in
every call.

### 6.4. Interrupts (decision 11)

A running call cannot be stopped from outside, only its worker ended. The page ends the worker and replays, as §6.3
does; a second interrupt during a replay starts over with no inputs. The page needs no cross-origin isolation, so any
static host can serve it.

V8 checks for termination at loops' back edges and at no tail call, so a function that calls itself forever in tail
position would never end; that is why such a call is a loop (§3.3), which an interrupt ends at once (7 ms after
`terminate()`). **Mutual recursion is not covered:** two or more functions that call each other forever in tail
position do so by `return_call`, which V8 does not check, so an interrupt cannot end the worker, and the user must
reload the page. Covering them takes a count at every function's entry, at a cost in every call.

*The cost of replay grows with the session:* stopping an endless loop runs every earlier input again, the long ones
at their full length, and their effects outside the session (a file in the page's store written) happen twice. It is
the price of needing nothing from the host. Where the two cross-origin isolation headers are present, a flag in
shared memory that compiled code polls could stop an input and keep the session without a replay; that is an
addition, with a cost in every unit compiled for a session.

### 6.5. The Page, Browsers, and Publishing

The page (`tools/wasm-page/`) is static files: `index.html`, `style.css`, `ui.mjs` (the transcript, the prompt, and
history), `page.mjs` (`PageSession`, which starts and restarts the worker), `worker.mjs` (the session, with
`getSync` for a prefix's files), `transcript.mjs` (output batched a frame at a time, so printing does not freeze the
page), and the archives `driver.qar.gz` and `lib.qar.gz`. Query parameters: `path=` (URL prefixes), `load=` (a file
to run first), `args=`, and `jit=0`; a prefix or file of another origin is used only after the user confirms. Every
import and fetch carries the build's stamp (`?v=STAMP`, and `BUILD` in `page.mjs`, checked against the driver
archive's), and a mismatch reloads the page once, then fails.

The page and its check (`tools/wasm-page/build --check --browser chrome|firefox|safari`) run in Chrome 157, Firefox
160, and Safari 26.6.2 on macOS, in both modes, every transcript passing in each. So each has what this target uses:
WasmGC with typed function references, tail calls, exceptions with `exnref`, and a worker's synchronous request.
Chrome and Firefox run headless with profiles of their own; Safari has no headless mode and runs the check in a
window of the user's. The page names the browsers it was tested in, and on failing to start, what an engine needs.
Not tested: Chromium's other browsers, mobile browsers, and Linux and Windows.

The page is published as the repository's GitHub Pages site by `tools/wasm-page/publish --push`, which builds it in a
worktree of a commit on `origin/main` (with `--built-from`, so its about note names the commit) and force-pushes it
as the one commit of the branch `gh-pages`: the built archives keep no history, here or on GitHub. Without `--push`
it builds and commits the site in `.build/wasm-publish/` to try first; `--local` does that for an unpushed commit.

---

## 7. Accepted Differences From the Native Backends

1. **Tracebacks** are the raise site only (§2.9).
2. **A tail call through a uniform entry that converts a result** leaves a frame (§3.3).
3. **The stack is smaller:** a deep recursion that runs natively may overflow in a page, and the interpreter's limit
   of 1,000 calls is the engine's there (§6.2).
4. **A stack overflow or an interrupt may replay the session** (§6.3, §6.4), and an endless mutual tail recursion
   cannot be interrupted (§6.4).
5. **An array has fewer than about 2²⁷ elements, and a string fewer than 2³⁰ bytes;** past them the program ends out
   of memory, where natively a 2³²-byte string is made (§2.10).
6. **The mathematical functions' results may differ in the last bits** from Apple's libm: by up to 2 ulp, 3 for
   `tan` (§4.3).
7. **`os/process`, `os/code`, `os/value`, and readline** are absent, and with them the parallel build (§4.2); a file's
   mode is `0o644` or `0o755`.
8. **`is` on some converted values:** true on a tuple that C's `runtime` conversion copies (§4.1).
9. **The heap's end is the engine's.** A browser ends the tab of a page whose worker fills the heap; node, given a
   limit (`session-node.mjs --heap-mb`), ends the worker it finds over it, and the session replays. With WebAssembly's
   GC objects V8 aborts the whole process at the limit for a large allocation and slows near it for small ones, so
   no limit is set by default.
10. **No mixing with C units:** a wasm unit's values are not C's. The interpreter is the reference and the IR dumps
    are the evidence.
11. **Under wasmtime, an exit status above 125** is 125 and a last line on standard error, which the driver maps back
    (§4.2).
12. **A cyclic type table in a `dynamic` document** fails with `dynamic.error` after 100,000 steps, where natively it
    overflows the stack.
13. **In a session, descriptors 3 and 4** are the session's streams (§6.1): a program that writes to descriptor 4
    finds its lines that are not the session's JSON passed to standard error, where natively the open fails.
14. **`--backend wasm FILE`** runs the program with no standard input.

Each has a remedy named in its section, and none is built before it is asked for.

---

## 8. Building, Running, and Testing

### 8.1. The Code

| Where | What |
|---|---|
| `questlang/wasm/model` | modules as data: types, functions, instructions, sections |
| `questlang/wasm/ops` | the instructions' opcodes |
| `questlang/wasm/encode` | the binary format, its name section byte for byte as `wasm-tools` writes it |
| `questlang/wasm/printer` | the text format, for `--stop-after codegen_wasm` and the `.wat` goldens |
| `questlang/wasm/runtimetypes` | R, the runtime's recursion group (§2.11) |
| `questlang/wasm/runtime` | the base runtime, built instruction by instruction (§4.2) |
| `questlang/wasm/locals` | the reuse of locals (§2.12) |
| `questlang/wasm/codegen` | the backend: a unit's described IR as a module |
| `questlang/jit/target.wasm`, `target.none` | the JIT's target in a session, and none (§5.3) |
| `runtime/wasm/core`, `print`, `dynamic` | the runtime in Quest (§4.2) |
| `lib/util/realconv`, `realmath` | `Real`'s text and mathematics (§4.3) |
| `runtime/wasm/run.mjs` | node's runner for programs, over `node:wasi`; it unwinds at `proc_exit`, so `--cpu-prof` works |
| `runtime/wasm/host.mjs`, `session.mjs`, `session-node.mjs`, `jit.mjs`, `repl.mjs`, `archive.mjs` | the JavaScript host, the session, the JIT's linker, a REPL over a session, and the archives (`.qar`: a JSON index, the bytes, gzipped) |
| `tools/wasm-page/` | the page (§6.5), `build`, and `publish` |
| `tools/wasm-probes/` | the probes of §9 |

### 8.2. The Driver

- `quest --backend wasm FILE` compiles the program and runs it under wasmtime (`--wasm-engine node` for node); with
  `-o` it writes the program's module and each unit's beside it, with `FILE.units` naming them in order. `-e`, `-i`,
  `--kernel`, and the REPL are refused with this backend.
- `--stop-after codegen_wasm` prints a unit's module as text.
- wasmtime runs with `-C collector=copying`, `-W max-wasm-stack=8388608` (8 MB of stack, as natively), `-S
  inherit-env=y`, and `--dir /` and `--dir .` with `PWD`; node with `--stack-size=7800`.
- The driver compiled to wasm runs under node by `runtime/wasm/session-node.mjs` (`--stack-kb`, `--heap-mb`), and
  compiles itself there to modules byte-identical to the native wasm build's.

### 8.3. The Tests

- **Run goldens in three modes** (`runner.py`; [testing.md](testing.md)): `wasm` (wasmtime), `wasm-node`, and
  `wasm-jit` (the driver compiled to wasm, in node, its JIT compiling each program as a session's input). What they do
  not yet pass is listed, with a reason, in `tests/self-hosted/pending-wasm.txt` and `pending-wasm-jit.txt`; each
  mode is skipped where its engine is missing. `tools/check` runs `wasm-node` on every change, and `wasm` and
  `wasm-jit` for a change to wasm code (`WASM_PATHS` in `tools/check.py`) or with `--all`.
- **`tests/self-hosted/wasm_programs.py`:** the programs in `tests/self-hosted/wasm/` with `.wat` goldens of the
  backend's own text, compiled by paths relative to the repository's root so the goldens hold no checkout's path;
  `--backend wasm FILE` run directly (`check_driver_run`); an object built against another runtime rebuilt
  (`check_stale_runtime`).
- **`tests/self-hosted/wasm_session.py`:** the session under node, with the transcripts the page's check uses
  (`check_transcripts`), recovery from overflows interpreted and compiled (`check_recovery`, `check_review`), a
  replay that loses inputs (`check_lost`), and the page built and run in node (`check_page`,
  `tests/self-hosted/wasm_page.mjs`).
- **`tests/self-hosted/wasm_selfcompile.py`:** the wasm driver compiling itself to modules byte-identical to the
  native build's.
- **`tests/python/test_wasm.py`:** the encoder's corpus (the questlang test `wasm_encode`), each module's bytes equal
  to `wasm-tools parse` of its text, valid, and run by wasmtime and node; **`test_wasm_externals.py`:** the table of
  externals covers `lib/`.
- **The page in a browser:** `tools/wasm-page/build --check [--browser chrome|firefox|safari]`, which no suite runs.
- **Benchmarks:** `benchmarks/mlton/run.py --backend wasm` ([benchmarks.md](benchmarks.md) §25).

wasmtime 50.0.1, node 26.13, and `wasm-tools` 1.263.0 are what the suites ran with.

---

## 9. Measurements

### 9.1. Tuples (decision 1)

*2026-11-13, by the probes in `tools/wasm-probes/`* (`gen.py` writes them as text, `build.sh` assembles them,
`run.mjs` and `stack.mjs` run them in node 26.13, `wt.sh` in wasmtime 50.0.1 with the copying collector; node's
figures the best of five warm runs, wasmtime's one process each, compilation included; a machine in use, so the
timings are indicative). A tree of 2²¹ nodes, each a tuple of a kind, a span, and two children, built and then
walked, summing kinds and spans. The span either fits 31 bits or is boxed.

| | V8: slot array | V8: flat struct | wasmtime: slot array | wasmtime: flat struct |
|---|---|---|---|---|
| build once, spans fit | 66 ms | 39 ms | 150 ms | 52 ms |
| build once, spans boxed | 83 ms | 75 ms | 100 ms | 118 ms |
| walk 10 times, spans fit | 86 ms | 104 ms | about 350 ms | about 180 ms |
| walk 10 times, spans boxed | 115 ms | 139 ms | about 420 ms | about 250 ms |

- **In V8, the slot array costs allocation and nothing else:** building is 1.7 times slower when nothing else is
  allocated, and 1.1 times when one component in four is a boxed integer; walking was not slower.
- **In wasmtime the flat struct is about twice as fast** at both.
- **A boxed integer stored in a tuple costs 8 to 18 ns in V8,** in either layout: the price of "`i31` or a box", not
  of decision 1.

### 9.2. Arrays (decision 2)

A million elements, either all fitting 31 bits or all full-width (`i * 0x9E3779B97F4A7C15`, as a `Word` hash is),
first with the element type known to the code, then through another unit's generic `get` and `set`, as
`collections/hashmap` reaches its hashes through `collections/vector`. "Typed" is an `i64` store that generic code
finds by a cast of the array's struct, boxing what it returns and unboxing what it is given.

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
  the box outlives the store, so it is a write barrier and a survivor, not only an allocation.
- **Through a unit, typed arrays box on the way out:** every read allocates, and reads are 1.4 times slower.
- **wasmtime's copying collector makes short-lived boxes ruinous** (13.8 s against 0.23 s), since each collection
  copies the live array.

### 9.3. Casts at Boundaries (decision 3)

A function of three reference parameters (a string, a tuple, an array) that reads a field of each, called 100
million times from another module: at precise parameter types, and at `eqref` with a cast of each at entry.

| | precise | `eqref` and three casts |
|---|---|---|
| V8 | 213 ms | 292 ms |
| wasmtime | 0.19 s | 0.33 s |

The three casts cost 0.8 ns a call in V8 and 1.4 ns in wasmtime.

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

- **A first deep recursion runs entirely in baseline code** (node with no flags gave the baseline figures exactly).
- **A baseline frame is about 63 bytes and 8 for each local declared,** whether or not it is live; an optimized frame
  is 21 to 26 bytes whatever the locals. So reusing locals gives back a factor of four (§2.12).

The largest array each engine makes, by bisection (the basis of §2.10):

| Element | V8 | wasmtime (copying collector) |
|---|---|---|
| `eqref` | 134,217,720 | 536,870,899 |
| `i64` | 134,217,720 | 268,435,449 |
| `i8` | 1,073,741,792 | 2,147,483,596 |

wasmtime's default stack is 512 KiB, in which a one-parameter function recurses 20,000 deep; with `-W
max-wasm-stack=8388608`, 160,000.

### 9.5. Collectors and Full-Width Integers

- **wasmtime's copying collector copies everything live at each collection,** so short-lived garbage beside a large
  live heap is very slow there (§9.2). A self-compilation, with hundreds of megabytes live, took 790 s in wasmtime
  and 55.6 s in node (2026-11-14), which is why it runs in node (decision 13). wasmtime's GC heap is also 4 GiB, its
  references being 32 bits.
- **Full-width integers in slots are the cost to watch:** 8 to 23 ns for each one stored. The compiler makes some by
  packing two small ones (a merged file's span, a reserved symbol id); a pair of small integers would allocate
  nothing.

### 9.6. The Compiler and Programs

- **Self-compilation** (2026-11-15, [benchmarks.md](benchmarks.md) §25): 47.5 s in node against 39.4 s native, 1.21
  times, byte-identical output. Leaving out the adapters this target does not need (§3.2) took it from 64.7 to 60.8
  s, and a copy of `boxInt` and `unboxInt` in each unit, rather than a call into the base, from 58.4 to 45.1 s. The
  profile is now led by the collector (about 13%) and calls across units into `vector` and `hashMap`, which no
  inlining crosses outside a whole program.
- **The MLton suite** (2026-11-15): 7.20 times MLton and 3.53 times arm64 in node; 45 of 46 programs agree with
  native output, raytrace differing in msun's last bits.
- **Sizes of the compiler** (2026-11-13): over its 5,703 functions, a median of 10 IR variables, 85 at the 90th
  percentile and 503 at the 99th; the largest has 1,450. Its widest closure captures 11 values.
- **`Real`:** reading three numbers of 400,000 digits took 0.23 s natively and 0.28 s in node. Writing and reading an
  `Array(Real)` of 100,000 took 0.55 s natively, 1.7 s in node, and 22.5 s in wasmtime, almost all of it formatting.

### 9.7. The Page

- **Start-up** (2026-11-15, locally): about a quarter of a second to the prompt. The driver's archive is 3,147 KB
  compressed. Compiling its modules takes 84 to 113 ms in Chrome, 203 in Firefox, and 120 in Safari; instantiating
  them 13 to 15 ms; the driver's initializers 141 ms in node, about 15 of them making descriptors. A session starts in
  150 ms interpreted and 57 with the JIT in Chrome, 67 and 56 in Safari. Making descriptors from data, merging the
  modules, and initializing lazily were considered and not taken.
- **The JIT** (2026-11-14): a first input takes 41 to 43 ms, later ones 2 to 5; an input that imports a library
  module, 15 ms, against 26 to 28 interpreted.
- **Output:** the page appends 20,000 lines in under a second.

---

## 10. Open Problems

Found and not fixed, each small or rare; none is a difference §7 accepts.

- **`maxBytes` is 32 bytes over V8's limit.** It is 2³⁰, and V8 makes byte arrays of at most 1,073,741,792 (§9.4), so
  a string of 1,073,741,793 to 1,073,741,824 bytes passes the test and traps in V8 instead of ending out of memory.
- **Echo of a large aggregate is quadratic:** `wasm/print`'s `show` joins its text with `<>`.
- **The core's caches are scanned, not hashed,** and never emptied: reading a `dynamic` document at a supertype
  16,000 times takes 12 s in wasmtime. **Formatting `Real`s in wasmtime** is slow for the same reason as §9.5.
- **Serialization recurses** (`runtime/wasm/dynamic`'s `scan`, as C's does): a list of 10,000 cells round-trips with 8
  MB of stack, against 15,000 natively.
- **`dynamic`'s `concrete`** converts a value once, where C's `quest_concrete` converts it again after each step
  through an abstract type's representation or an auto value's witness; it matters only if such a type is a stored
  type with storage, which no case has shown.
- **The JSON reader** reads `[]` at a record type as `record end`.
- **A runtime's own raise reports a site in `wasm/core`,** not the caller's.
- **`isUnitImport`** names `util/realconv` and `util/realmath` instead of following a rule; a rule tried broke unit
  loading.
- **Not checked:** that the core imports only what the backend compiles in place, and a mode compiling each
  intrinsic's cast as a test (`--wasm-checked`); neither is built.
- **The page:** each worker makes its own URL mounts, so a URL may be fetched again after a replay; a server that
  answers 200 for a missing file (an HTML error page) is taken at its word.
- **The host's `open`** handles only the flags the core passes (read, a directory, or create with truncate): create
  without truncate would replace an existing file, and append and exclusive are ignored.
- **Pending under the JIT:** the transcripts whose output holds frames (§2.9).
- **Shared faults** a review reported and no probe reproduced are in [tasklist.md](tasklist.md).
