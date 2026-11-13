# Plan: The REPL in a Browser, on WasmGC

The next goal: the self-hosted REPL running in a browser. The compiler is compiled to WebAssembly by a new backend of
the self-hosted compiler, and in the end each interaction is compiled to a WebAssembly module that is loaded into the
running session, as the arm64 JIT loads machine code ([jit.md](jit.md)). The backend targets WebAssembly's garbage
collection (WasmGC): Quest's values are the engine's structs and arrays, and the engine's collector is Quest's.

**Status: decisions taken, nothing built** (2026-11-12). §4 to §7 list the design decisions, with options and a
recommendation for each; §8 the parts expected to be hard; §2 where I thought what was asked for was problematic. The
owner has answered the questions (§11), and §9 has the steps to the first milestone: **the compiler, compiled to
WebAssembly, compiling itself outside a browser.** A review's twenty-two questions have been worked through, and
§12 says where each is answered and what it changed. The owner's answers to the last four questions (§11: 2 and 10
to 12) are provisional; no question is open.

---

## 1. What WasmGC Changes

Everything below the IR today rests on four things that WasmGC does not have. They are why this backend shares less
with the others than arm64 shares with C, and why representation is where most of the decisions are.

1. **No word that is either an integer or a pointer.** A field, a local, and a parameter each have one static type:
   a number (`i32`, `i64`, `f64`) or a reference. The uniform one-word slot ([runtime-design.md](runtime-design.md)
   §2.2), in which generic code stores an `Int` and a pointer alike and a descriptor says which, cannot be written.
   The only type that holds "any value" is a reference (`eqref`), and the only integers a reference holds without
   allocating are 31 bits (`i31ref`).
2. **No addresses.** No pointer into an object, no pointer arithmetic, no tag bit in a pointer. That removes `var`
   and `out` parameters as pointers to slots ([c-representation.md](c-representation.md) §6.5), an option case's
   binder as a pointer into the option, boxes embedded in their aggregate's allocation, the proxy bit
   (runtime-design.md §2.3), byte offsets in a record's offset table, and identity hashing by address.
3. **No C.** The runtime's C cannot touch the engine's objects. The collector (2,650 lines) is simply not needed; the
   rest of `runtime/` (about 7,000 lines: descriptors and run-time subtyping, `quest_convert`, proxies, view maps,
   printing, strings, `dynamic`'s serialization, exceptions) must exist again in another form, and so must what it
   takes from libc: formatting and parsing a `Real`, the mathematical functions, files.
4. **Static typing with casts.** A struct's field is read by a static index at a static struct type, and a function
   reference is called at a static function type. Where Quest's structural types do not give those, the code casts
   (`ref.cast`, `br_on_cast`), which is checked and costs a few instructions.

What it gives: no collector to ship or to find roots for, which was the largest risk of a linear-memory port; modules
loaded later share the heap by holding references, with nothing to relocate; type definitions are compared
structurally across modules, so separately compiled modules agree on types without a linker (R18 says what that
takes); and the current browsers have it. The backend needs three proposals beyond the first version of WebAssembly:
GC (with typed function references), tail calls, and exception handling with `exnref` (`try_table`). Safari was the
last to have each: GC and tail calls in 18.2, by my recollection, and `exnref` in 18.4, by MDN's compatibility data.
Neither was tested in a Safari; the nearest check is JavaScriptCore's, below. The page will not run in a Safari
before 18.4, nor in a Chrome or Firefox from before `exnref` (2025 and late 2024).

**Checked on this machine** (wasmtime 50.0.1, default options, 2026-11-12): two hand-written modules, one preloaded
into the other (`--preload lib=lib.wat`), share struct types declared in each, with a struct family in which each
arity is a declared subtype of the one before; a 64-bit integer boxed as an `i31ref` or a struct and unboxed by
`br_on_cast_fail`; an exception thrown in one module and caught by `try_table` in the other, through an exported
tag; a `return_call` ten million deep; output through WASI from a module whose only linear memory is a page for the
I/O buffer; and sixty million allocations, most becoming garbage, in a quarter of a second, with the default
collector and with `-C collector=copying`. wasmtime reads the text format directly.

**Checked later the same day,** for the review's questions (§12):

- *Other engines.* A module written in the binary format by hand (a GC struct, an exception thrown and caught by
  `try_table`, a `return_call` a million deep) gives the same answer in wasmtime, in node 26.13 (V8 14.6), and in
  JavaScriptCore as this machine's macOS has it (the system framework's `jsc`): Safari's engine, though not Safari.
- *wasmtime's default collector does not reclaim cycles.* The first check made no cycles and did not watch memory,
  so it could not show this. Twenty million rounds, each making two objects and dropping them: with the default
  (`drc`, reference counts) 2.7 s and 16 MB at most when the two do not point at each other, and 0.9 s and
  **1.9 GB** when they do, nothing being freed; with `-C collector=copying`, 0.12 s and 9 MB either way. The
  compiler's types, scopes, and symbols are cyclic, so everything runs under the copying collector, which is also
  twenty times faster at allocating here. (The Opus plan found the same.)
- *Limits* (R19): a chain of 63 subtypes is accepted and one of 64 refused; a struct of 10,000 fields is accepted
  and one of 10,001 refused.
- *The stack* (A8): with wasmtime's default, a function of one parameter recurses 20,000 deep and not 40,000;
  with `-W max-wasm-stack=8388608`, 160,000.
- *Bytes* (A9): copying from linear memory into a GC byte array, a byte at a time, takes 1.2 ns a byte.

## 2. Where I Think the Request Is Problematic

- **WasmGC is the right base for this goal, and it is the expensive one.** I would choose it too, for the reasons
  above. But it should be decided knowing that the backend forks from the others at the IR, not at the SSA: the SSA
  ([ssa.md](ssa.md)) is words, byte offsets, and `ptr`/`int` conversions, none of which survive, so its passes
  (escape analysis, promotion, scalar replacement, value numbering, inline allocation) do not apply, and the code is
  generated from the described IR, as the C printer's is. With a second runtime and a second model of
  representation, this is nearer in size to the C backend and runtime together than to the arm64 backend. A
  linear-memory port (the first draft of this plan) would have reused all of it and paid instead with its own
  collector, a 64-bit memory, and roots the engine hides.
- **`Int` stops being free in generic code.** Today a type parameter's value is a word and an `Int` in it costs
  nothing. On WasmGC it is a reference, and an `Int` in it is tested or allocated at every crossing (§4, R2). The
  compiler's own data lives in `vector.T(A)`, `hashMap.T(K V)`, and tuples, so the compiler compiled this way will be
  slower than its arm64 self by a factor nobody can state yet; a probe should measure it before the design is fixed
  (§9.1, step 1).
- **wasmtime alone will not do.** It is a good home for the run suite: it runs text, it has WASI, and everything §1
  needs works in it. Three limits:
  - Its command line cannot load a module made while a program runs, so the JIT, the goal's second half, cannot be
    tested in it without a host program written against its embedding API.
  - A browser's engine is V8 or its peers, not Cranelift: wasmtime's timings, and its collector's behavior, say
    little about the page.
  - Browsers and node take only the binary format, and no tool on this machine converts text to it.
  - Its defaults are wrong for this: the default collector leaks cycles and the default stack is 512 KiB (§1). Every
    run is `-C collector=copying` with `-W max-wasm-stack` set.
  I recommend wasmtime for the suite and node (installed, and V8) for the JIT and as the browser's stand-in, both
  from early on, with a binary encoder of the compiler's own early rather than late (§6, A5).
- **"Eventually a JIT" shapes the first module.** If the ahead-of-time compiler is built as one whole-program module
  and the JIT is added later, the questions of how modules name each other's functions, globals, and types are
  answered twice. I recommend that a unit be a module from the start (§7).
- **The interpreter is a milestone worth naming.** The compiler compiled to WasmGC already contains the
  tree-walking interpreter, so a REPL in a page exists as soon as the compiler runs there, before any JIT. I would
  have made that the first thing shown. *Decided otherwise:* the first milestone is the compiler compiling itself,
  outside a browser (§11, 5); the interpreter's REPL in a page then follows from it at little cost.

## 3. The Shape of the Design

The current design's division carries over, and that is the main recommendation of this document: **native
representations in locals, parameters, and results of known calls; one uniform representation everywhere a value's
type is not known to the code that holds it** (aggregate slots, type parameters' values, calls through closures).
Today the uniform representation is a word; here it is an `eqref`. The represent pass ([ir.md](ir.md) §8.3) already
inserts a `convert` at every crossing between the two, with a plan (`box`, `unbox`, `slot_box`, `record_view`,
`view`, `adapt`, ...); what changes is what the representations are and what each plan costs.

The alternatives to that shape, and why not:

- **Monomorphize everything.** Not possible for Quest: polymorphic functions are first-class values, type operators
  are higher-order, modules' abstract types are compiled apart, and `auto` and `dynamic` choose types at run time.
  Specialization stays what it is now, an optimization of direct calls ([ir.md](ir.md) §8.1).
- **Typed layouts with type passing:** each aggregate laid out by its own type (an `i64` field for an `Int`), and
  generic code, which already receives a descriptor for each type parameter, choosing the access by descriptor.
  A struct field cannot be read without statically naming the struct type, so generic code would reach every field
  through a getter the descriptor supplies (an indirect call), or be compiled once per combination of its
  parameters' classes. It keeps `Int` fields unboxed at the cost of the common generic path, and makes one object
  have a layout that depends on who made it, which the uniform slot exists to prevent. Worth revisiting only for
  types proven never to reach generic code, in a whole program.

## 4. Representation: Decisions

Each has a recommendation; "measure" means the probe of §9 decides.

**R1. The uniform value is `eqref`.** Structs, arrays, and `i31ref` are all `eq`, and `ref.eq` is `is`. Function
references are not, so a closure is a struct holding one; a host's value (`externref`) is wrapped likewise.

**R2. `Int` in a uniform position: an `i31ref` when it fits, else a boxed `i64`.** An `Int` stays 64 bits and is an
`i64` wherever its type is known. Boxing it tests the range; unboxing tests for `i31` and otherwise reads the box.
Most integers a compiler stores (indices, counts, tags, positions) fit, so most boxings allocate nothing.
*Alternatives:* always box (simpler, an allocation per store); narrow `Int` (a language change, and `Word`, hashes,
and `util/bignum` need 64 bits). `Word.T` is boxed the same way, and its values are often full width, which R5
addresses for arrays. A `Real` is a boxed `f64`, always an allocation; `Bool` and `Char` are `i31`.
Consequence to check: `is` on two boxed integers must compare values, so `is` at a type parameter keeps going
through the descriptor, as `quest_val_is` does now.

**`Ok` is the `i31` zero, and null is no Quest value.** (I first wrote that `Ok` is null; the review asked what a
slot's type and a cast then are, and the answer was not good: every test for a kind would also have had to mean
something for `Ok`.) A slot's type is still the nullable `eqref`, because an array being filled, a cell an `out`
parameter is about to initialize, and a descriptor an initializer has yet to tie are null before they are written,
and a non-null type would need a dummy value for each. So a null read from a slot is always the compiler's or the
runtime's mistake, never a value: an unbox given one fails its test for `i31` and then traps in its cast to the box,
and a cast to a struct type traps, both of which are R15's "cannot happen" traps. No code tests for null.

**R3. Every aggregate slot is an `eqref`,** the value's uniform form, so that native and generic code agree on every
aggregate with no conversion, identity and `var` sharing are kept, and abstract types need no layout of their own
outside their module. This is today's rule with today's reason. Its cost is R2's test on every `Int` field.

**R4. Tuples and options: a family of structs, or arrays?** *Measure.*
- *Structs:* one type per arity, `{header, eqref × n}`, each a declared subtype of the arity before, so that a
  tuple used at a prefix type needs no cast (checked, §1). An option's case is the same struct with its tag in the
  header, so a case's binder can be the option itself, read as a tuple, which keeps payload sharing without a
  pointer into the object. Field reads are unchecked loads. A `var` component is the target of a (container, index)
  location (R8) through a switch on the index, since a struct's field index is static.
- *Arrays* of `eqref`, element 0 the header: one type for everything, locations uniform, a bounds check and a
  length word on every access.
- *A limit settles part of it:* a chain of subtypes may be 63 deep (R19), so a struct for each arity cannot go on
  for ever. The compiler's widest tuple has 23 components, but a user's may have more. So the family is the arities
  0 to 48, each a subtype of the one before; a wider tuple keeps its first 47 components in fields and the rest in
  an array of `eqref` in the 48th. A prefix type still needs no cast, and only code that knows the tuple to be wide
  reads the array.

The header word (an `i32`) also serves the identity hash (R9). A tuple or option type that cannot be a proxy has
its struct type statically; one that may be is an `eqref` cast at each access, which is today's `direct` and `proxy`
access modes with a cast for the tag-bit test.

**R5. Arrays by element class:** an array of `i64` for `Int` and `Word`, of `f64` for `Real`, of `i8` for `Char` and
`Bool`, and of `eqref` for everything else. Code that knows the element type uses its array type directly; generic
code (`Array(A)`) does not know the class and dispatches by casting the array, and allocates by its descriptor's
class. *Alternative:* every array of `eqref`, with no dispatch, and every full-width `Word` or `Real` element an
allocation. The compiler's side tables are `Array(Int)` and its hashes `Word`s ([arm64.md](arm64.md) §3.15), so I
recommend classes. *The invariant to hold:* the site that allocates and every site that reads must agree on the
class, including where the element type is a module's abstract type whose representation is `Int`: such a type is
"unknown" outside its module and dispatches, and its descriptor answers for its representation.

**R6. Records stay a pair:** the payload (an array of `eqref`: element 0 its layout's descriptor, then the fields
sorted by name) and the view's offset table (an array of indices, with the stored types as now). Field access is
`payload[table[i]]`, as it is `*(val + dict->offset)` now; width subtyping pairs the payload with another table;
the runtime's map of tables carries over. In a slot the pair is boxed, as now, but the box can no longer be
embedded in its aggregate's allocation, so storing a fresh record into a slot allocates twice. *Alternative:* a
record value is always one reference to a `{payload, table}` box, which makes storing free and an upcast an
allocation. I recommend the pair, since the represent pass's boxed variables already reuse boxes.

**R7. Variants stay a pair** of a tag and a payload (`i32`, `eqref`), remapped by tables as now, boxed in slots.

**R8. Locations (`var` and `out` parameters, `@`).** The hardest representation question. Options:
- *A pair of a container and an index,* dispatching on the container where the location is read or written: a cell
  (a one-field struct, for a local whose address is taken), a slot of an `eqref` array, an element of a typed
  array. Exact semantics, no allocation for `@a[i]` or `@r.f`. A local whose address is taken becomes a heap cell.
  It wants R4's arrays, or a helper that switches on the index for struct fields.
- *Accessor closures* (a getter and a setter): exact, general, an allocation per `@`, an indirect call per access.
- *Copy in, copy out,* through extra results: no allocation, locals stay locals, and it is already what an
  unspecialized polymorphic call does today (Tier 2, c-representation.md §6.5). It differs observably when the
  callee raises after assigning (the assignment is lost), when two parameters alias, and when the callee reaches
  the location another way.

*What is and is not a location.* A `var` field or component is not one: assigning it is a `struct.set` or
`array.set` on its aggregate, and reading it a `get`, whichever option is taken. Its only cost on this target is
R2's, the test or box of an `Int` stored in a slot. A `let var` local is a WebAssembly local, since no function uses
an enclosing function's mutable variables ([ir.md](ir.md) §9, Core). R8 concerns only the IR's address operations
(`addr x`, `addr r.name`, `addr t.#i`, `addr a[i]`, `cell(a)`, `load p`), which exist only for arguments of `var`
and `out` parameters.

*How common* (counted 2026-11-12): `questlang/` and `lib/` declare about 980 `var` fields, components, and locals,
and contain **no** `var` or `out` parameter and no `@` or `var(e)` argument. 134 of the 823 test sources use them.
So for the compiler and the REPL this decision costs nothing either way; it matters to the run suite and to users'
programs.

*What each costs* (wasmtime 50.0.1, 200 million calls of a function that adds one to an `Int` location, nothing
inlined; the time per call includes the loop):

| The location is | The callee is given | ns per call |
|---|---|---|
| a local | the value, and returns it (copying) | 1.4 |
| a local, kept in a cell | the cell, at its own type | 2.1 |
| a local, in a cell made for each call | the cell, at its own type | 4.6 |
| a local, kept in a cell | a container and an index, dispatching | 6.2 |
| a tuple's `var` component | the value, and returns it (copying) | 3.9 |
| a tuple's `var` component | a container and an index, dispatching | 9.3 |

So an exact reference through the pair costs about 5 ns a call more than copying, with no allocation in a loop; the
dispatch (two failed casts before a struct's component is reached, then a switch on the index, then R2's unboxing)
is the cost, and it goes where the callee is specialized or inlined for its argument, as Tier 1 does now. The rows
for a typed cell say what a callee that could assume a cell would cost, but a callee cannot, since the same code is
given `@x` and `@t.f`.

*With R5's array classes, every container a dispatch may meet:* a cell of each class a local or a top-level variable
can have (`i64` for `Int` and `Word`, `f64`, `i32` for `Bool` and `Char`, `eqref` for the rest, records and variants
boxed as in slots); an array of each of the four classes; and a struct of the tuple family. That is nine, not more:
a record's payload and a wide tuple's overflow are arrays of `eqref` (R9 makes a payload and such an array one
type), and a component reached through a proxy is passed as the original's. But a callee knows its parameter's
class, so it tests only for what can hold that class: for `var p: Int`, an `i64` cell, an `i64` array, and the three
containers of `eqref` that hold it boxed (five); for a `Real`, likewise five; for a reference type, three; for a
type parameter, all nine. Two dispatches were measured:

- *A chain of tests,* as in the table: 6.2 ns when the first hits and 9.3 after two fail, so about 1.5 ns for each
  test that fails. With cells tested first, **the 6.2 ns stays 6.2 for a local;** the worst case for an `Int` (a
  struct's component, after four failures) is about 12 ns, and for a type parameter about 18.
- *A selector:* the caller, which knows the container's kind statically, puts it in the index's top four bits, and
  the callee switches on it and casts once. Measured the same way: 9.0 ns for a cell, 10.5 for an `i64` array, 12.5
  for an array of `eqref`, 10.5 for a struct's component. Flat in the number of classes, and slower than the chain
  wherever the chain hits early.

The chain, ordered cell first and limited to the parameter's class, is the plan; the selector is the fallback if V8
orders the costs differently.

**Recommended: the pair,** exact semantics at a few nanoseconds a call, because the cost falls on a feature the
compiler and library do not use, and copying's differences would be a change to the language as implemented, on one
target only. The measurement also settles that the pair does not force R4's arrays: a struct's component is reached
by a switch on the index. Taken, provisionally (§11, 2); built in the second milestone.

**R9. Identity and its hash.** `is` is `ref.eq` after unproxying, with options' value rules as now
([extensions.md](extensions.md), "Options as Values"). `hash.identityHash` has no address to hash: I recommend a
counter's value stored in the object's header word the first time it is asked for, which R4's header and a record
payload's first element can hold, and which strings and closures need a field for.

*Arrays.* I first wrote that an array's hash could be unsupported at first. It cannot: the interpreter, which is in
the compiler, hashes `Array(Value)` by identity. **Every array has a header element** holding the hash: element 0 of
an array of `eqref`, of `i64`, or of `f64` (its bits), and the first four bytes of an array of `i8`; element `i` is
at `i + 1` (or `i + 4`), a constant added to an index that is being compared anyway (R16). No wrapper, no
indirection, and an array of `eqref` and a record's payload become one type.

*What the compiler hashes by identity* (counted 2026-11-12). Every `hashMap.new` and `hashSet` in `questlang/`
passes its own equality and hash; of some 350 maps, all but two are keyed by `Int` or `String`, and
`newIdentityMap` is not used. `hash.identityHash` itself is called on a tuple (`model.Subst`, in a memo key of
`ir/represent`), on `model.Builtin`, and, in `interpreter/builtins` and `values/dynamicjson`, on every kind of
interpreted value: records, tuples, arrays, variants, closures, strings, readers, writers, string builders, and
the scalars. So the first milestone needs the counter for tuples, options, arrays, strings, closures, and the
library's handles, and hashing by value through the descriptor for `Int`, `Word`, `Bool`, `Char`, and `Real`.
`ir/represent`'s key puts the hash's digits in a string; that it never reaches output is to be confirmed in step 2,
since a counter's values differ from addresses.

**R10. Proxies are a struct type** (the fields of `QProxy`), recognized by a cast where a tag bit is tested now.
`type_may_be_proxied` keeps deciding which accesses test.

**R11. Closures** are a struct whose first fields are its code (P3 says of what types: a uniform entry, and in a
subtype a native one) and whose further subtypes add the captures at their native types, since only the function's
own code reads them. A function that captures
nothing has one static closure, a global.

**R12. Strings** are a struct of a length, a byte array, and a hash field; literals are created from data segments.
Text crosses to the host (WASI, or JavaScript) through a page of linear memory, the module's only one.

**R13. Descriptors and static data** are structs in globals. Descriptor graphs are cyclic, so a unit's are built or
tied by its initializer, not by constant expressions. Templates, instantiation, and memoization are runtime code as
now.

**R14. Exceptions** are WebAssembly's: one tag whose payload is the exception state; a `try` is a `try_table` whose
handler tests which exception it caught and rethrows what it does not catch. The handler chain, which today
decides before unwinding whether a raise will be caught ([exceptions.md](exceptions.md) §5.1), has no use but the
uncaught report, and the engine hides the frames: a traceback is the raise site, plus whatever the host gives (in a
browser, the engine's stack trace of the exception, readable if the module has a name section). A stack overflow is
the engine's trap, which no handler in the module sees; the host catches it, and, since the heap is the engine's and
stays valid, the session can go on, which the arm64 JIT cannot do ([jit.md](jit.md) §6). A8 has the stack in full.

**R15. Traps.** No handler in a module catches a trap, so the rule is: **no trap is reachable from a Quest program
compiled by a correct compiler, but the stack's and the heap's.** Every case in which Quest raises today is tested
for before the instruction that would trap, and raises the same exception.

| Instruction | Traps when | Quest today | On this target |
|---|---|---|---|
| `i64.div_s`, `i64.rem_s` | the divisor is 0, or the quotient overflows | `int.error` for 0; the SSA's builder tests for 0 and -1 before dividing | the same two tests, emitted before it |
| `i64.div_u`, `i64.rem_u` | the divisor is 0 | `word.error` | the test first |
| `i64.trunc_f64_s` | a NaN, or a value out of range | `real.error` from `floor`, `round`, `ceil`, `trunc` | the range tested, then the saturating form, which cannot trap |
| `array.get`, `array.set`, `array.copy`, `array.fill` | the index is out of bounds | `array.error`, `string.error`, `vector.error`, from the runtime's checks | a test in 64 bits before the index is narrowed (R16), raising the same; the engine's own check then cannot fail |
| `array.new` | the engine cannot allocate that many | `array.error` or `string.error` for a negative size; a fatal error when memory runs out | the size tested (R16); beyond that, the heap's exhaustion, below |
| `struct.get`, `struct.set`, `array.len`, `call_ref`, `ref.as_non_null` | the reference is null | Quest has no null | cannot happen (R2); a trap is the compiler's bug |
| `ref.cast` | the value is of another type | no counterpart: C would misread memory | cannot happen; where a program's values decide (unboxing, a dispatch), the code is a `br_on_cast`, which does not trap |
| `unreachable` | always | fatal errors with a message (an option ordinal out of bounds) | after the runtime has given the host the message and the site |
| a call | the stack is exhausted | compiled: the guard page's report of `stack.overflow`, which no `try` catches; interpreted: a catchable `stack.overflow` at 1,000 calls | A8 |
| an allocation | the heap is exhausted | a fatal error | the engine's trap or exception, fatal to the call in progress; the host reports it |
| `i32.load`, `i32.store` | outside the transfer buffer (A9) | none | the runtime's bug |

A trap ends the call the host made; what the host and the session do then is A8's. The host reports a trap that is
none of the stack's and the heap's as an internal error, with the engine's message.

**R16. `Int` where WebAssembly wants `i32`:** an array's or a string's length, an index, a size to allocate. An
`Int` is 64 bits, and `i32.wrap_i64` alone would make index 2³² + 5 read element 5. So:

- *An index* is compared in 64 bits, unsigned, with the length (`array.len`, extended, less the header of R9), which
  catches a negative index and a huge one at once and raises the exception of R15; only then is it narrowed. The
  engine repeats a comparison that can no longer fail; what the pair costs is step 1's to measure.
- *A size* is tested in 64 bits: negative raises as today; over 2³¹ - 8 raises the same exception, where natively
  the allocation would be tried and the collector's fatal error follow. A size under that which the engine refuses
  is the heap's exhaustion.
- *A length* read back is an `i32` extended, so it is always a valid `Int`.

So an array or a string has fewer than 2³¹ elements on this target, a limit that a browser's memory makes
unobservable except as the exception in place of the fatal error.

**R17. Locals of reference types.** Validation requires a local of a non-null reference type to be set before it is
read, and forgets, at a block's end, a set made inside it. By case:

- *A variable bound once* (most of the IR, which is in ANF): set where it is bound, and every use is in the
  binding's scope, which is the same block or one inside it. Non-null.
- *A join point's parameters:* the join is a block whose label takes them, a jump is a `br` with the values on the
  stack, and the continuation, after the block's `end` and so at the outer level, begins by setting the locals.
  Non-null.
- *An `if` or `switch` that gives a value:* the arms leave it as the block's result; no local is set in an arm.
- *A `let var` variable assigned on both arms of an `if`:* it was set where it was declared, before the `if`, so the
  arms' assignments are not what initializes it. Non-null.
- *An `out` parameter's target:* a location (R8), not a local. A local passed with `@x` lives in a cell from its
  declaration, and the cell's field is the class's (an `i64`, or the nullable `eqref` of R2), so validation sees
  nothing unset; a target the callee was to initialize and did not is null, and reading it traps where C reads
  whatever was on the stack.
- *What is left* (a variable the backend cannot show to be set on every path, if the IR has any) is declared
  nullable, and costs a null check where a non-null value is required; `struct.get`, `array.get`, and `call_ref` take
  a nullable operand and check it themselves.

No dummy values. The cost of the choice is the null checks on what is left, expected to be none in practice, and a
few extra `local.set`s at joins.

**R18. Type identity across modules.** Two types are the same when their definitions are, position for position
within their recursion groups, whatever module declares them. Left alone, that merges types the runtime must tell
apart: a variant's box (an `i32` and an `eqref`) and the tuple family's arity 1 (a header `i32` and an `eqref`) have
one definition, and a cast testing for one would accept the other, silently.

- **One recursion group holds every type that code tells apart by a cast or a test:** the boxes of an `Int` and of a
  `Real`; the four cells (R8); the four array types (R5); the tuple family's 49 arities (R4); the string; the
  closure's base (P3); the record's box and the variant's box; the proxy; a raised exception's state. Members of one
  group are distinct by their position, so two with the same fields are still two types. `i31` is distinct from all
  of them by kind.
- *Does that survive someone adding or removing a field?* Yes: no edit to a member can merge it with another, since
  position, not content, separates them. And an edit changes the identity of every member at once, so a module
  compiled against the table as it was fails to link (an import's type does not match), instead of running with a
  mistaken layout. The group is printed from one table by every module (J2); it is some 70 types, a few hundred
  bytes a module.
- **Standing alone, each its own group, and meant to merge:** function types (a native entry's by its signature, a
  uniform entry's by its arity); the closure type of each native signature (P3); and each function's own closure
  type, a subtype of those that adds its captures. Two functions with captures of the same types share a closure
  type, harmlessly: only a function's own code reads its captures, and it casts only its own closure.
- **Not structural at all:** tags and globals belong to the instance that defines them. The exception tag is the
  runtime module's, imported by every other; a tag declared in each module would be a different tag in each.

Quest's own types add nothing to this: they are structural, and all of them are represented by the group's members.

**R19. The engines' limits** (the JavaScript API's, which browsers enforce; wasmtime has the first two, checked):

| Limit | Value | What of the plan could reach it | What is done |
|---|---|---|---|
| depth of subtypes | 63 | a struct for each tuple arity | the family stops at 48 (R4); closures are 3 deep (P3) |
| fields of a struct | 10,000 | a closure's captures; nothing else, wide tuples overflowing at 48 | an error naming the function, if ever |
| parameters | 1,000 | a function of 500 record parameters (each is a pair) | an error; none exists |
| locals of a function | 50,000 | a local for each of the IR's variables, in a large function after inlining, or in an initializer | locals are reused by type as scopes end, which the stack wants too (A8) |
| size of a function's body | 7,654,321 bytes | an initializer that builds every descriptor and constant of a unit, or of a whole program | initializers are cut into functions of bounded size; constant data comes from data segments, not code |
| data segments | 100,000 | a segment for each string literal of a whole program | one segment a unit, literals by offset |
| operands of `array.new_fixed` | 10,000 | a long array literal | a loop, or a data segment |
| types, groups, functions, globals, imports, exports | 1,000,000 each | a closure type and two function types for each function | far off: the compiler has about 5,000 function definitions in source |
| a module's size | 1 GiB | nothing | |
| wasmtime's GC heap | 4 GiB (its references are 32 bits) | the self-compilation: natively 848 MB live at most and 3.1 GB resident ([benchmarks.md](benchmarks.md) §17, §21), and a copying collector holds its live data twice | measured in step 11; node is the alternative (§9.1) |

A limit reached is a compile-time error naming what reached it, never a module an engine refuses.

## 5. Polymorphism: Decisions

**P1. Type parameters' values are uniform (`eqref`); descriptors are passed as now.** The uniform quantifier rule
(c-representation.md §6.4) stays: each quantifier is a descriptor parameter, used for `auto`, `inspect`, `dynamic`,
`is` at a type parameter, view maps, printing, and now also for R5's array class. Polymorphic functions as values,
polymorphic recursion, and higher-kinded parameters need nothing more, as now.

**P2. What `box` and `unbox` cost.** Today a scalar becomes a word for nothing, and only records and variants are
boxed. Here every `Int`, `Word`, and `Real` crossing into generic code is R2's test or allocation, and every crossing
back a test. So `should_specialize`, which now clones a callee for record and variant arguments and for `var`
parameters, should consider scalars too, against the growth in code; and inlining across modules in a whole program
([ir.md](ir.md) §8.6) matters more than it does natively. *Measure,* on the compiler itself.

**P3. Calls through closures: one uniform entry for every function.** The largest change from today, and I
recommend it.
- *Today* a closure has one code pointer at its native C signature. A caller holding it at a generically laid out
  type reaches it through an adapter thunk or its type's invoker, and where a signature differs inside mutable data
  the conversion is rejected (c-representation.md §6.4.5). A word and an integer or pointer agree in a register, so
  this is rare: `Real`s, `Bool`s, records.
- *On WasmGC* `i64` and `eqref` never agree, and each reference type is its own, so nearly every function type
  would differ between its native and generic forms: an adapter allocated wherever a function value crosses into
  generic code, and the rejected cases common.
- *Recommended:* a function has a **native entry**, typed by its own parameters and results and used by every call
  whose callee is known (which is most calls: ssa.md §4, "Closures"), and a **uniform entry**, of a type that
  depends only on its arity (the closure, then `eqref`s, giving an `eqref`), which a closure's code field holds and
  every call through a closure uses; it unboxes, calls the native entry, and boxes the result. It is today's
  invoker, made the only way an unknown callee is called. Then a function value needs no conversion when its type
  is instantiated, keeps its identity, and may sit in any array or `var` slot; `adapt` remains only where a view
  really changes (a record parameter's offset table, a variant's tags), as function subtyping needs today; and the
  `runtime` and rejected plans for layouts, `quest_layout_equivalent` for functions, and abstract types' generic
  layout outside their modules all go.
- *Costs:* an unknown call boxes its `Int` and `Real` arguments and result (free for small integers, an allocation
  per `Real`); a record argument is boxed; a `var` parameter's location must have a uniform form (R8); and each
  function used as a value has two bodies' worth of entry code.

*Revised after the review: a closure also carries its native entry.* The argument above is about layouts agreeing,
and it requires only that the uniform entry always exist and be what a caller uses when it does not know the
callee's native signature. It does not require that a call through a closure never use a native entry. The Opus
plan measured, in V8, a call through the uniform entry at about ten times a native `call_ref`, and a cast to a
native closure type at nothing. So:

- The closure's base (in R18's group) holds the uniform entry. For each native signature there is a closure type,
  a subtype of the base, that adds the native entry as a typed function reference; a function's own closure type is
  a subtype of its signature's, adding its captures. Three deep.
- A caller whose static function type has native signature S tests the closure for S's type (`br_on_cast`) and
  calls the native entry when it is one, the uniform entry when it is not. It is not one exactly where an adapter
  stands today: the function was made at another signature and came to this type by instantiation or subtyping
  (the identity at `Int -> Int`, a parameter that is a record seen through another view).
- A closure costs one more field, and a module one more type for each signature it calls or defines.

*What this does not help, and which of the compiler's calls those are.* A call made by generic code has the generic
signature. `hashMap`'s call of its hash function, at `K -> Word`, is (`eqref`) to `i64`; `hash.int` is (`i64`) to
`i64`; the test fails, and the uniform entry boxes the `Word`, which is full width and so allocates, at every
lookup. By reading the sources (the count by profile is step 2's):

- *Hash functions:* every one of the compiler's roughly 350 hash maps and sets passes one, and all but two are keyed
  by `Int` or `String`. The result is a `Word`: **an allocation per lookup.** This is the costly case.
- *Equalities and predicates* (`Bool`), *comparators* (a small `Int`), and `vector.map`, `fold`, `iter`, `exists`
  over `Int` elements: tests of range, no allocation, but the ten-fold call.
- *`Real`:* none on the compiler's paths.

Remedies, to be chosen by the probe, in the order I would try them: (1) specialization and inlining across units of
the collections' small functions (P2), which makes the call known; (2) where the represent pass sees a function
passed at an instance of a generic type (`hash.int` at `K -> Word` with `K` an `Int`), wrap it once in a closure of
the generic signature, so that the generic caller's test succeeds: an allocation for each map, not for each lookup.
That is today's `adapt` plan, kept as an optimization and no longer needed for correctness; as today, the wrapper
and the function are different under `is`.

**P7. Tail calls.** Natively they are made "whenever possible, not as a guarantee of the language"
([arm64.md](arm64.md) §3.7), for direct calls and calls through closures alike. Here `return_call` and
`return_call_ref` do it, and a call can be one exactly when no code must run after it, that is, when caller and
callee give results of the same WebAssembly types. Calls that are tail calls natively and would stop being so:

1. A native entry whose result is converted between its native and uniform forms (an `Int`, `Word`, `Real`, `Bool`,
   `Char`, a record, a variant), calling an unknown callee through the uniform entry: the result is unboxed after
   the call. (Where P3's test for the native signature succeeds, the call is a tail call; this is its other branch.)
2. A uniform entry that is a wrapper, calling its native entry and boxing the result.
3. A call in a `try`'s body, as natively.

Results that are references in both forms (tuples, options, strings, arrays, closures, and `Ok`, which a native
entry returns as its uniform value for this reason) need no conversion, and their calls stay tail calls.

*What 1 and 2 do to a loop written through closures:* a state machine or a continuation-passing loop whose closures
return an `Int` leaves two frames a step, where natively it runs in constant stack. At 100 bytes a frame, a
worker's 512 KB ends after a few thousand steps. That is a program that runs natively and dies in the page, in a
shape functional programs take, so wrappers alone will not do.

*Recommended:* **for a function whose result is converted, the uniform entry is a second compilation of the body,
not a wrapper.** It unboxes its parameters on entry and its result type is `eqref`; in it every tail call goes to a
uniform entry, by `return_call_ref` when the callee is unknown and by `return_call` of the callee's uniform entry
when it is known (so that callee needs one too: the need spreads along tail-call edges, within a unit by analysis,
and across units to exported functions with converted results). Then case 2 is gone, and case 1 happens once: a
native entry's call into the chain leaves one frame, and everything the chain does after is in uniform entries. The
loop runs in constant stack plus that frame. The cost is code: such functions' bodies twice. How many functions
have a converted result and are used as values or tail-called from one that is, step 2 counts; if it is most of the
compiler, the fallback is wrappers with the limitation documented.

A function's tail call of itself is a branch to a `loop` at its top, as arm64 makes it a jump.

**P4. Bounded quantification keeps own views and view maps** (c-representation.md §5.1): a record is still a
payload and a table, so a view map still indexes the type argument's table. The code is the runtime's, ported.

**P5. Subtyping's conversions keep their plans:** `record_view`, `variant_tags`, proxies for tuples and options
whose components change view, `adapt` for functions. None depends on addresses once R6, R7, and R10 are taken.

**P6. `auto`, `inspect`, and `dynamic`** need the descriptors and the run-time subtyping, conversion, and
serialization that the C runtime has. They are the bulk of the runtime to be written again (§6, A3). How much of
them the compiler itself needs, as against the programs it compiles, is counted in step 2 (§9.1).

## 6. The Compiler and the Runtime: Decisions

**A1. Where the backend forks.** Lowering, specialization, closure conversion, and the simplifier, inliner, and
contifier are representation-free and are shared. The represent and describe passes are where representations
enter. *Recommended:* one represent pass parameterized by a model of representation (what each shape is natively
and in a slot, which plans exist, what agrees with what), with `codegen/layout` as the native model and a new one
for WasmGC, rather than a second pass: the pass's rules about where conversions go are the language's, and two
copies would drift. The risk is to the native backends, whose `ir_represented` goldens must not change. The owner
accepts either this or a fork of the pass, the choice being cheap to reverse (§11, 9); it is argued and taken in
step 4, when the first shapes show how much of the pass's code asks for a layout.

**A2. Code is generated from the described IR, with no SSA.** The IR is structured (`if`, `switch`, `loop`, `join`),
and so is WebAssembly, so control flow maps directly and no CFG need be restructured. What the SSA's passes did is
either the engine's job or is lost; if the loss matters, Binaryen's optimizer can run over the module shipped to the
page, as a build step, not a dependency of the compiler.

**A3. The runtime is written in Quest,** in unsound modules ([modules.md](modules.md) §4.4) over a small set of
primitives the backend compiles inline (cast a uniform value to a kind, read and write a slot, make an aggregate of
a given arity, call a closure's uniform entry), and compiled by this backend with everything else.
*Alternatives:* WebAssembly text by hand (thousands of lines nobody can type-check) or JavaScript (absent in
wasmtime, and slow across the boundary). The two runtimes must agree to the byte on what programs print, which the
shared goldens check.

**A4. The library's externals:** 161 C functions under `lib/`, each to become an instruction sequence (`word`,
most of `real`), Quest code (`string`, `stringBuilder`, `conv`), or a host call (`reader`, `writer`, `system`,
`os/fileStats`). `os/process`, `os/code`, `os/value`, and GNU readline have no counterpart.

**A5. Text and binary.** The backend builds instructions as data and prints them as text or encodes them, as
`minst` serves the arm64 printer and encoder. wasmtime runs either; node and browsers need the binary; the text is
what a person reads and what goldens, if any, hold.

**A6. No mixing with C units.** A WasmGC unit's values are not C's, so the bring-up method of the other backends
(move units between backends until the miscompile is found) is gone. The interpreter is the reference, the IR dumps
the evidence, and every test runs whole in the new backend or not at all.

**A7. The bootstrap gets nothing,** as with every backend; language-visible changes to `lib/` go in both compilers
as always.

**A8. The stack.** Natively the main thread has 8 MB, and a guard page's handler reports `stack.overflow` with the
frames running ([exceptions.md](exceptions.md) §6). Here the stack is the engine's, smaller, and its overflow is a
trap that the host sees and the program does not.

*How much there is.* wasmtime: 512 KiB by default, where a function of one parameter recurses 20,000 deep and not
40,000; `-W max-wasm-stack` raises it (160,000 deep at 8 MiB, checked). node: about 10,000 JavaScript frames by
default, raised by `--stack-size`. A page: the Opus plan measured about 512 KB in a Chromium worker and about 1 MB
on a page's thread, with no flag.

*How much the compiler needs* (measured 2026-11-12): the native compiler building itself (`quest compile` of the
driver, arm64, `-j 8`) succeeds with the stack limited to **256 KB** and fails with 128 KB. So its deepest
recursion on its own 90,000 lines is between 128 and 256 KB of arm64 frames, not megabytes: its long structures
are walked by loops and tail calls. The interpreter's 1,000 calls at about 2 KB each are 2 MB, a different matter:
that limit is the interpreter's own and is lowered for this target if needed.

*What changes that figure here,* none of it measurable before there is code: a baseline compiler (V8's Liftoff)
gives every local a slot, so frames are larger until a function is optimized, and largest for functions with many
locals, which is a second reason to reuse locals (R19); uniform entries add frames where calls are not tail calls
(P7); the engine keeps its own data in each frame. Twice to four times the native figure would be 0.25 to 1 MB,
which is the size of a worker's stack. So the first milestone is safe (a flag), and the page is not known to be.

*What the plan does:*

1. **Measure,** in step 11: the least stack with which the self-compilation succeeds in wasmtime and in node, by
   their flags, and which functions are on the stack at the deepest point.
2. **Where a few recursions account for the depth,** make them loops or give them explicit stacks, in the compiler's
   source, for every target.
3. **A count in the code, for sessions** (milestone 2): a unit compiled for a session adds, at each function's
   entry, a constant weighted by the function's locals to a global, compares it with a limit, and subtracts at
   exit; a `try`'s handler restores the count it entered with. Over the limit it raises `stack.overflow`, an
   ordinary exception that a `try` catches, as in the interpreters, with the heap and the session's state as after
   any exception. The limit is set by the host from what it finds the stack to be (it recurses a calibrating
   function once at start). The same comparison is the interrupt's poll (J7). Its cost is step 1's to measure; a
   program compiled for a file, like the compiler of milestone 1, does without it.
4. **When the host sees the overflow anyway** (a deep recursion in code without the count, or a count set too
   high): the call the host made ends with the engine's error. The heap is the engine's and intact; what may be
   wrong is state the unwinding would have restored (the count, a scope the compiler had pushed, an input half
   defined). The driver's entry points are therefore written so that each begins by restoring such state, as the
   session rolls a failed input's module back today ([jit.md](jit.md)): the host reports `stack.overflow` without
   frames, calls the driver's recovery entry, and the session goes on. Under WASI, with no session to keep, the
   host's message says to raise the flag.

**A9. Bytes across the host's boundary.** Neither JavaScript nor WASI can read or write a GC array or struct; both
see only linear memory. So there is one memory, the runtime module's, exported, used only as a buffer for what
crosses, and grown to the largest thing that has crossed.

| What | In the page | Under WASI |
|---|---|---|
| text in (an input, a fetched source) | the host encodes it into the buffer as UTF-8 and calls an entry with its length; the runtime copies it into a new byte array | `fd_read` fills the buffer; the same copy |
| text out (output, diagnostics) | the runtime copies the string's bytes into the buffer and calls an import with the length; the host decodes | the same copy, then `fd_write` |
| a file's contents | as text in, from a fetch (J5) | as text in, in pieces of the buffer's size |
| a JIT module's bytes | the encoder's byte array copied into the buffer; the host copies them out of its view and compiles them, synchronously in a worker | not applicable: wasmtime's command line cannot load them |

There is no bulk instruction between linear memory and a GC array, so each copy is a loop: 1.2 ns a byte in
wasmtime (5 MB a hundred times in 0.61 s). The compiler reading its own sources, about 5 MB with the
library, pays some 6 ms for it in a self-compilation of minutes. An interaction's module is kilobytes. A `String`
is bytes on both sides, so nothing is transcoded. Not used: JavaScript's string builtins and `externref` strings,
which would tie the runtime to one host and are absent in wasmtime.

**A10. Artifacts and caches, by target.**

- *A `.qi`* holds an interface's types, imports, and sources, with the ABI version and its producer
  ([build-process.md](build-process.md) §4.2): nothing of a backend. One `.qi` serves every target, as it serves C
  and arm64 now.
- *A `.qm`* already records the backend that compiled its unit, and a unit the build assigns to another backend is
  stale (§5.2.1 there). `wasm` is one more name; the unit's code is a `.wasm` beside it, where a `.o` would be.
- *The stages* are already kept by backend (`.build/quest-stages-BACKEND`).
- *The ABI version* is one number for "the runtime's layouts and the calling conventions", and this target has a
  second runtime with its own. *Recommended:* keep the one number, bumped for a change to either runtime, which
  costs rebuilds on the target that did not change and cannot be wrong; and add the target's name to what the
  fingerprint of [jit.md](jit.md) §3.3.1 digests, so that a unit's fingerprint for this target never equals its
  native one. Today nothing in the fingerprint depends on the backend.
- *What stops an artifact of one target being used by another:* in a build directory, the `.qm`'s backend; for
  loading, the file itself (a page cannot load a `.o`, nor the arm64 JIT a `.wasm`); between a host and an input,
  the fingerprint with the target in it; and between modules of this target built from different versions of the
  runtime's types, R18: the import fails to link.
- *In the page* the build directory is memory, as the native JIT's is (`common/memoryFiles`, jit.md §3.4.1): the
  session writes and reads its `.qi` texts there, and nothing is cached between sessions at first.

## 7. Modules and the JIT: Decisions

**J1. A unit is a module.** Each interface's exports are WebAssembly exports (functions at their native entries,
the module record and initializer, globals), each import an import by name, and the host instantiates the modules
in order: wasmtime by `--preload`, a page by a loader of a few lines. An interaction's module is one more unit.

*A module for each unit, against a whole program for the page.* I planned both without saying how "the driver is
the library" survives the second: if the page's compiler is one optimized module, what does an input's module
import when the function it names was inlined, specialized, or removed? Three builds, kept apart:

- *A module a unit:* the build of milestone 1 and of every interaction. What is given up is inlining and
  specialization across units, which on this target is also what removes the boxing at calls of the library's small
  generic functions (`vector.get` at `Int`); step 11 measures it.
- *A whole program, for a program nobody imports:* free to inline, specialize, and remove, as now.
- *The page's driver: a whole program with roots.* The build is given the units an input may import (the library's
  interfaces; not the compiler's own units, unless listed). For each, every exported value keeps its standard
  definition (its native entry at its declared type, and its uniform entry if P7 gives it one), its unit's record,
  the state its initializer makes, and its fingerprint, all exported under the names a module for that unit would
  export. Inlining copies a root into its callers and leaves the root; specialization adds clones and leaves the
  root; removal of dead code starts from the roots; a unit's state is one set of globals whoever refers to it. So an
  input's module imports only roots, and they are always there. What is given up: the roots' code stays though the
  compiler may not call it (size), and an input's own calls of the library are not inlined.

  Today a whole-program driver has no fingerprints and refuses `--jit` ([jit.md](jit.md)), so the rooted build is new
  work in `ir/whole`, and of use natively too. If step 11 finds the whole program's gain small, the page ships the
  per-unit modules as one bundle, and nothing but that gain is given up.

**J2. Types are declared in every module that uses them** and compared structurally by the engine (checked, §1).
The runtime's types form fixed groups that every module declares identically; the backend must print them from one
table, since a difference in a group is a link error at best.

**J3. The session's loop belongs to the host.** A page cannot block for input, and compiling a module there is
asynchronous or in a worker. So the driver exports entry points (take an input, return a module's bytes or a
diagnostic; run a loaded unit; print a value) and the page drives them, as the Jupyter kernel's session drives the
REPL ([jupyter-kernel.md](jupyter-kernel.md)). "The driver is the library" (jit.md §1) holds: an input that imports
a unit of the driver's links to the driver's exports.

**J4. Redefinition in place** ([repl.md](repl.md) §6) needs a top-level binding to be a mutable cell that later
modules import, not an immutable global.

**J5. Files in a page: a URL prefix is a `QUEST_PATH` directory** (decided, §11, 8). The page is given one or more
URL prefixes, and an import looks under each as it looks in a directory of `QUEST_PATH`, fetching **source**
(`.int.quest`, `.mod.quest`), which the compiler in the page compiles. The library is served the same way, or
compiled into the page's module ahead of time. To be designed with the second milestone: a fetch is asynchronous
and the compiler's file reads are not, so either the host fetches what an input's imports name before calling the
compiler (it must then learn the imports first, and theirs, in rounds), or the compiler runs in a worker with
synchronous requests; and a directory cannot be listed over HTTP, so nothing may depend on listing one.

*Decided after the review:* the session runs in a worker (J7 wants one too), and a file read is a synchronous
request there, which workers allow, so the compiler's reads stay as they are. What a request's outcome is to the
compiler, and how `QUEST_PATH`'s order is kept when existence cannot be asked without fetching:

- *Three outcomes, as for a file:* the text; "no such file"; or an error with a reason. Only a 404 or 410 is "no
  such file". A network failure, a timeout, a 5xx, a 403, or a body that is not the file (a server's HTML error
  page with status 200, told by its content type) is an error **at the import**, naming the URL and the reason.
- *Order:* an import looks under each prefix in turn and takes the first that has the file. A prefix's error is
  never read as its not having the file: the lookup stops there. Falling through would let a later prefix shadow an
  earlier one that had only hiccuped, and the session would run a different module without a word.
- *Retries and slowness* are the host's: it may retry a failed request a bounded number of times before reporting,
  and a slow one is slow until the host's timeout makes it an error. The compiler never retries.
- *Each URL is fetched at most once in a session,* found or not found: a test for existence is the fetch, kept, so
  it and the read that follows agree, and a session sees one version of a file. A command of the page forgets them.
- *What cannot be asked* is an error where it is asked: a directory's entries, a file's time (a constant, as for
  the native JIT's files in memory).
- *Later, if the probing costs:* a prefix may serve an index of its files, read once, after which a lookup under it
  fetches only what exists.
- A prefix on another origin must allow the page's origin (CORS); that is its server's business, and its failure is
  the error above.

**J6. What the page serves,** by stage of milestone 2 (§9.2). The interpreter runs a library module from its source,
its externals being the compiled library's functions in the driver, as natively
([interpreter.md](interpreter.md)).

| File | Interpreting (stage 1) | A module per input (stage 2) | Who makes it, for which target |
|---|---|---|---|
| the driver: compiler, interpreter, runtime, and the library units it links | needed | needed, its library units being roots (J1) | `quest compile --backend wasm`, at a release; this target only |
| the library's interfaces (`.int.quest`) | each one an input imports, directly or not | the same | nobody: the tree's files, the same for every target |
| the library's modules (`.mod.quest`) | each one an input imports: the interpreter runs it | only those not in the driver, which the session compiles to a module | the tree's files; where a module's body differs for this target (A3, A4), this target's |
| `.qi` | none: made in the session's memory from the interface (A10) | none, likewise | the session |
| compiled modules of library units | none | none: they are the driver's roots | |
| a user's modules, sources under a URL prefix (J5) | interpreted | compiled in the session | the user |

So the page serves two kinds of thing: the driver, built for this target, and sources, built by nobody. Serving
`.qi` files made ahead would save each session the interfaces' compilation, at the price of a second artifact to
keep in step with the driver; not at first.

**J7. Interrupts.** An input that does not end. Natively only the kernel's driver handles it: a flag the signal
handler sets, tested at each function's entry and each loop's head in the JIT's code and in the interpreter's loop,
raising `interrupted`, with the session ended if the cell has not stopped after a grace period
([jupyter-kernel.md](jupyter-kernel.md) §5). In a page:

- *On the page's own thread* nothing can be done: the page is frozen with the input. So **the session runs in a
  worker,** which the synchronous fetches of J5 and the synchronous compilation of an input's module want too.
- *A worker can always be terminated,* and the session dies with it, since its heap is the instance's. The page
  starts another and says so; it can offer to replay the transcript, which runs the inputs' effects again.
- *To stop the input and keep the session,* the flag must be memory both threads see: a shared linear memory, which
  a browser grants only to a page that is cross-origin isolated (two response headers, which some static hosts
  cannot send). The page's thread stores the flag; the interpreter's loop tests it (stage 1, at no cost in code),
  and compiled code tests it at function entries and loop heads, where A8's count already compares, in every unit
  compiled for a session, the driver's library units included, since an input can loop inside the library. It
  raises `interrupted`, and the session goes on. What the test costs the compiler's own speed in the page is to be
  measured; the driver for milestone 1 has none.
- *The grace period* stays: an input that has not stopped some seconds after the flag (it is inside a host call, or
  in code without the test) is terminated with its worker.

*Decided* (§11, 10, provisionally): the page requires isolation, so the worker and the shared flag always, and
termination only after the grace period. Wherever the page is hosted must send the two headers.

## 8. The Hard Parts, in Order of Risk

1. **The second model of representation** in the represent pass and everything that asks a shape for its layout,
   without disturbing the native backends (A1), and the performance of `Int` and closures under it (R2, P2, P3).
2. **The runtime again, in Quest** (A3, P6): run-time subtyping, `quest_convert`, proxies, view maps, descriptor
   templates, and `dynamic`'s serialization, agreeing with the C to the byte.
3. **Locations** (R8).
4. **`Real` without libc:** shortest round-trip printing and exact parsing as C's `printf` and `strtod` give them
   (the goldens hold their output), and `sin`, `exp`, `pow`, and the rest, which WebAssembly lacks and wasmtime
   cannot import from a host.
5. **Debugging without mixing** (A6), up to the real test: the compiler, 84,000 lines of Quest, compiling itself
   through the backend and writing what its native self writes.
6. **Identity hashing** (R9) and the invariant of array classes (R5).
7. **The JIT's protocol** (J1 to J4), and that wasmtime cannot test it.
8. **The stack** (A8): the first milestone's limit is a flag and the second's is not; the compiler needs 128 to
   256 KB natively and a worker has about 512; an overflow is the host's to see. With it, tail calls through
   uniform entries (P7), which decide whether a loop of closures has a depth at all.
9. **What else the engine hides or limits:** frames for tracebacks; the limits of R19, the locals of a function and
   an initializer's size above all; a module's size and start-up time with every descriptor built at
   initialization; interrupts (J7).

## 9. Steps

Two milestones. The first has steps; the second has stages, whose steps are written when the first is reached and
its measurements are known.

### 9.1. Milestone 1: The Compiler Compiles Itself on WebAssembly

The self-hosted compiler, compiled by the new backend to WasmGC modules, runs in wasmtime and compiles itself there,
writing the same modules its native self writes. Scope is what the compiler and the REPL use (§11, 4); everything
else is pending, with reasons.

*The engine.* The fixed point is not tied to wasmtime. It needs an engine with files, arguments, and the
environment, which is WASI's first preview: wasmtime has it, and so does node (`node:wasi`, marked experimental;
present in node 26, checked), which takes the encoder's binary. The self-compilation is run in both and must give
the same bytes, which also tests each engine against the other; the suite's small programs stay with wasmtime,
which starts fast and reads text.

*What it will take.* Natively the self-compilation in one process is 66 to 75 s, 43 GB allocated, 848 MB live at
most ([benchmarks.md](benchmarks.md) §17, §21). The Opus plan measured wasmtime at about 8 ns for a `call_ref` and
far behind V8 at allocation (under the default collector; with the copying one a small allocation was 3 ns here,
§1, but that collector copies everything live at each collection). I cannot turn those into a time honestly before
step 1 has the costs of the operations and step 2 their counts; my guess is three to ten times native, so 3 to 12
minutes in wasmtime, and less in node. Either way it is a check for a step's end and before a push, as the
whole-program arm64 checks are, not one for every `tools/check`. The driver's `-j` starts processes through
`os/process`, which this target lacks, so the build is serial inside the engine; a script outside can run an engine
for each unit, interfaces first, which gives `-j` back.

1. **A probe by hand.** The alternatives still marked "measure", as WebAssembly text, for a generic vector of
   integers, a hash map, a closure-heavy loop, and records read through views: R4 (structs or arrays), R5 (array
   classes, and what the dispatch costs generic code), P3 (the uniform entry's boxing against a known call), and
   R2's test on every `Int` slot. Timed in wasmtime, and in node once something on the machine writes the binary
   format (`wasm-tools`, if it may be installed, or step 3's encoder). Also: P3's test for a native closure type
   against the uniform entry, and a hash map's hash function called each of the ways P3 lists; R16's comparison
   before the engine's; A8's count at a function's entry; and a null check (R17).
   *Done when* R4 and R5 are decided in §4 with their numbers, P2 says how far `should_specialize` should widen, and
   P3's remedy for hash functions is chosen.
2. **A census of what the compiler uses:** which of `lib/`'s 161 externals; `auto`, `inspect`, and `dynamic`;
   identity hashes, and of which shapes (R9), and that `ir/represent`'s use of one reaches no output; operations on
   `Real`; `os/process` and the parallel build. By a profile of a self-compilation: the calls through closures, by
   signature, and how many box a `Word` or a `Real` (P3). From the IR of the compiler's units: the functions whose
   result is converted and that are used as values or tail-called from one that is (P7); the largest function's
   variables and the largest initializer (R19); the widest tuple and closure.
   *Done when* §6 has the table, each row saying instruction, Quest, host call, or pending, and P7's choice between
   second bodies and wrappers is made on the count.
3. **Instructions, text, and encoder** (`questlang/wasm/`): instructions and types as data, a printer to the text
   format, an encoder to the binary, and the runtime's type groups printed from one table (J2).
   *Done when* a module built by hand in a unit test (integers, direct calls, a struct, an exception) runs in
   wasmtime from its text and from its binary, and in node from its binary, giving the same output.
4. **The backend's skeleton.** `--backend wasm` (`codegen/choice`); A1 argued and taken; code from the described IR
   for `Int`, `Bool`, `Char`, control flow (`if`, `switch`, `loop`, `join`), direct calls, tail calls, string
   literals, and output through WASI; a unit is a module from this step on, with the runtime a preloaded module
   (J1); a runner mode for the run goldens with a pending list.
   *Done when* the run goldens that need no more than this pass in the mode, and the native backends'
   `ir_represented` goldens are unchanged.
5. **Aggregates:** tuples and options as step 1 decided, with headers, `var` components, case binders that share
   the payload, option values' rules; arrays by class where the element type is known; strings and their operations.
   *Done when* their goldens pass.
6. **Closures:** the closure struct and its subtypes, captures at native types, the native and uniform entries,
   calls through closures, static closures for functions that capture nothing.
   *Done when* the higher-order goldens that are not polymorphic pass.
7. **Records and variants:** the payload and table, views and width subtyping, tag tables, boxes in slots, the
   represent pass's reuse of boxes.
   *Done when* their goldens pass.
8. **The runtime in Quest, first part:** descriptors and templates built by a unit's initializer (R13),
   instantiation and its memoization, `is` at a type parameter, printing of values as the REPL echoes them,
   exceptions (`try`, `raise`, `raised`, the uncaught report with the raise site), the identity hash (R9).
   *Done when* the goldens for exceptions and for printing pass, with output equal to the C runtime's.
9. **Polymorphism:** descriptor parameters, the `box` and `unbox` plans, generic code over arrays of every class,
   specialization as step 1 set it, own views and view maps (P4), proxies and the subtyping plans (P5), and as much
   of `auto` and `inspect` as step 2 found the compiler to use.
   *Done when* the polymorphism and subtyping goldens pass, less what step 2 marked pending.
10. **Units and the library:** exports and imports by name, initializers in dependency order, a link that is a
    list of modules for wasmtime's `--preload`; the driver's build writing a module per unit, serially; the
    externals of step 2's table; the host side on WASI: files, arguments, the environment, the clock.
    *Done when* a program of several units using `lib/` runs, and the pending list holds only what step 2 excluded
    and `var` and `out` parameters.
11. **The compiler through the backend.** The driver's units compiled by the native compiler with `--backend wasm`;
    the result run in wasmtime to compile a small program, then the run suite's sources, then itself. Differences
    are found against the native compiler's IR dumps, stage by stage (A6).
    *Done when* the compiler running in wasmtime and in node, compiling itself with `--backend wasm`, writes in
    each modules byte-identical to those the native compiler wrote; and [benchmarks.md](benchmarks.md) records,
    beside arm64's, the time and peak memory of that self-compilation in each engine, the least stack it succeeds
    with in each (A8), and its time built as one whole program against a module a unit (J1).

### 9.2. Milestone 2: The REPL in a Page

Stages, in order; steps to be written after milestone 1.

1. **The interpreter's REPL in node, then in a page,** in a worker, with the session's loop the host's (J3), imports
   from URL prefixes (J5), what J6 lists served, interrupts (J7), and recovery from the host's errors (A8).
2. **Each interaction a module:** compiled in the session, loaded by the host, linked to the driver's roots and
   to earlier interactions' (J1, J4), with the count and the poll in its code (A8, J7); in node first, then in the
   page. Checked in a Chromium browser, the only kind promised for now (§11, 12).
3. **The rest of the language on this target:** `var` and `out` parameters (R8), `dynamic` and the rest of `auto`
   and `inspect`, `Real` in full (§8, 4), and the run suite's pending list worked down.
4. **The page's module:** a whole-program build, its size and start-up time, and whether Binaryen earns a place in
   the build (A2).

## 10. Testing

The shared run goldens, through a runner mode for the backend, with a pending list whose entries give reasons, as
arm64's had; the interpreter as the reference for any difference; wasmtime (`-C collector=copying`, and
`-W max-wasm-stack` at the native 8 MB, so that the suite's deep recursions behave as natively) for the suite, with
tests of its own for what differs on this target (the exception in place of R16's fatal error, a trap's report,
`stack.overflow` by A8's count); node for whatever loads
modules; and the self-compilation of step 11. The existing suites do not change, and `tools/check` runs the new mode
only when the backend's files differ, until its time is known.

## 11. Questions for the Owner, and the Answers

Answered 2026-11-12.

1. **node beside wasmtime?** *Yes.* Whether tools may be installed (`wasm-tools`, Binaryen) was not said; neither is
   needed before step 3's encoder exists, and step 1 uses `wasm-tools` only if it may.
2. **`var` and `out`: exact references or copying?** *Exact references, by R8's pair* (provisionally, 2026-11-12).
   The owner first asked what each costs, noting that the parameters are rare and `var` fields common; R8 answered:
   `var` fields are not affected, the compiler and library pass no locations at all, and an exact reference costs
   about 5 ns a call more than copying. Built in milestone 2.
3. **`Int` as `i31` or a box:** *accepted.*
4. **Scope:** *the compiler with the REPL;* much of the full test suite eventually.
5. **The first milestone:** *the compiler compiled to WebAssembly running on itself, not in a browser* (§9.1), not
   the interpreter's REPL in a page.
6. **The uniform closure entry (P3):** *yes.*
7. **The runtime in Quest (A3):** *yes, as much of it as possible.*
8. **In the page:** *a URL prefix behaves as a `QUEST_PATH` directory from which modules are loaded as source* (J5).
   Nothing was asked of the host beyond that, so the page is text in and out until asked otherwise.
9. **Parameterize the represent pass or fork it:** *either;* to be argued when it arises (step 4), and cheap to
   change if wrong.

Raised by the review (§12), and answered provisionally (2026-11-12):

10. **May the page require cross-origin isolation** (J7)? *Yes.* So an input is interrupted through the shared
    flag and the session kept; ending the worker remains for an input that does not stop within the grace period.
11. **A loop through closures in constant stack** (P7) costs a second body for some functions. Is the code worth
    it? *Yes, probably.* Second bodies are the plan; step 2 still counts them, and the count goes back to the owner
    if it is most of the compiler.
12. **Which browsers?** *For now, only Chromium's, that is, V8.* node is then the page's engine outside a page, and
    Safari and Firefox are not checked or promised; what §1 says of them stands as information.

## 12. The Review's Questions, and Where They Are Answered

A review put eleven questions to every plan for this goal and eleven to this one (2026-11-12). Each is answered in
the section its subject belongs to. Where an answer changed the plan, the change is marked.

| Across the plans | Answered in | What changed |
|---|---|---|
| 1. Traps | R15 | new: every trapping instruction, with today's behavior and this target's |
| 2. Tail calls through what stands before an unknown callee | P7 | new: second bodies for uniform entries, in place of wrappers, where a result is converted |
| 3. The stack | A8 | new: the compiler's need measured (128 to 256 KB natively); a count for sessions; recovery when the host sees the overflow |
| 4. The engines' limits | R19, R4 | the tuple family stops at 48 and overflows into an array; locals are reused; initializers are cut up |
| 5. Type identity across modules | R18 | new: one recursion group for every type told apart by a cast |
| 6. Reference locals | R17 | new |
| 7. `Int` where `i32` is wanted | R16 | new: comparisons in 64 bits before narrowing; under 2³¹ elements |
| 8. Bytes across the host's boundary | A9 | new: one linear memory as a buffer; 1.2 ns a byte |
| 9. What the page serves | J6 | new |
| 10. The driver as the library, against whole-program optimization | J1 | new: a whole program with roots |
| 11. Artifacts and caches by target | A10 | the target's name joins the fingerprint |

| Of this plan | Answered in | What changed |
|---|---|---|
| 1. P3: must every unknown call use the uniform entry? | P3 | no: a closure carries its native entry too, found by a cast; hash functions' `Word` results named as the costly case |
| 2. Milestone 1's engine | §9.1 | the fixed point runs in wasmtime and in node; a guess of 3 to 12 minutes, not a prediction |
| 3. wasmtime's collector and cycles | §1 | confirmed that the default leaks them; the first check made no cycles; the copying collector everywhere |
| 4. R5 and R8 together | R8 | nine containers, at most five for a parameter of a known class; 6.2 ns stays for a local, about 12 at worst for an `Int` |
| 5. R9: arrays' identity hashes | R9 | arrays get a header element; the compiler's uses counted |
| 6. R2: `Ok` as null | R2 | withdrawn: `Ok` is the `i31` zero and null is no value |
| 7. J1 and the page's whole program | J1 | as 10 above |
| 8. Interrupts | J7 | new: a worker; a shared flag where the page is isolated |
| 9. J5: failed and slow fetches, and the path's order | J5 | only "not found" moves to the next prefix; any other failure is an error at the import |
| 10. The stack deserves more | A8, §8 | as 3 above |
| 11. Safari's `exnref` and tail calls | §1 | run in JavaScriptCore on this machine; Safari 18.4 by MDN's data; a Safari itself in milestone 2 |
