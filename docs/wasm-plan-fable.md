# Plan: The REPL in a Browser, on WasmGC

The next goal: the self-hosted REPL running in a browser. The compiler is compiled to WebAssembly by a new backend of
the self-hosted compiler, and in the end each interaction is compiled to a WebAssembly module that is loaded into the
running session, as the arm64 JIT loads machine code ([jit.md](jit.md)). The backend targets WebAssembly's garbage
collection (WasmGC): Quest's values are the engine's structs and arrays, and the engine's collector is Quest's.

**Status: decisions taken, nothing built** (2026-11-12). §4 to §7 list the design decisions, with options and a
recommendation for each; §8 the parts expected to be hard; §2 where I thought what was asked for was problematic. The
owner has answered the questions (§11), and §9 has the steps to the first milestone: **the compiler, compiled to
WebAssembly, compiling itself outside a browser.** One question is still open (§11, 2: `var` and `out`), and it
blocks nothing before the second milestone.

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
structurally across modules, so separately compiled modules agree on types without a linker; and every current
browser has it (Safari included, which a 64-bit linear memory would not have had).

**Checked on this machine** (wasmtime 50.0.1, default options, 2026-11-12): two hand-written modules, one preloaded
into the other (`--preload lib=lib.wat`), share struct types declared in each, with a struct family in which each
arity is a declared subtype of the one before; a 64-bit integer boxed as an `i31ref` or a struct and unboxed by
`br_on_cast_fail`; an exception thrown in one module and caught by `try_table` in the other, through an exported
tag; a `return_call` ten million deep; output through WASI from a module whose only linear memory is a page for the
I/O buffer; and sixty million allocations, most becoming garbage, in a quarter of a second, with the default
collector and with `-C collector=copying`. wasmtime reads the text format directly. Not checked: any of it in V8.

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
addresses for arrays. A `Real` is a boxed `f64`, always an allocation; `Bool` and `Char` are `i31`; `Ok` is null.
Consequence to check: `is` on two boxed integers must compare values, so `is` at a type parameter keeps going
through the descriptor, as `quest_val_is` does now.

**R3. Every aggregate slot is an `eqref`,** the value's uniform form, so that native and generic code agree on every
aggregate with no conversion, identity and `var` sharing are kept, and abstract types need no layout of their own
outside their module. This is today's rule with today's reason. Its cost is R2's test on every `Int` field.

**R4. Tuples and options: a family of structs, or arrays?** *Measure.*
- *Structs:* one type per arity, `{header, eqref × n}`, each a declared subtype of the arity before, so that a
  tuple used at a prefix type needs no cast (checked, §1). An option's case is the same struct with its tag in the
  header, so a case's binder can be the option itself, read as a tuple, which keeps payload sharing without a
  pointer into the object. Field reads are unchecked loads. A `var` component cannot be the target of a (container,
  index) location (R8), since a struct's index is static.
- *Arrays* of `eqref`, element 0 the header: one type for everything, locations uniform, a bounds check and a
  length word on every access.
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

**Recommended: the pair,** exact semantics at a few nanoseconds a call, because the cost falls on a feature the
compiler and library do not use, and copying's differences would be a change to the language as implemented, on one
target only. The measurement also settles that the pair does not force R4's arrays: a struct's component is reached
by a switch on the index. Awaiting the owner's word (§11, 2); built in the second milestone either way.

**R9. Identity and its hash.** `is` is `ref.eq` after unproxying, with options' value rules as now
([extensions.md](extensions.md), "Options as Values"). `hash.identityHash` has no address to hash: I recommend a
counter's value stored in the object's header word the first time it is asked for, which R4's header and a record
payload's first element can hold, and which strings and closures need a field for. Arrays have no header: either
the hash of an array is unsupported at first (the compiler hashes few arrays by identity, to be checked), or arrays
gain a wrapper struct, which costs every access an indirection.

**R10. Proxies are a struct type** (the fields of `QProxy`), recognized by a cast where a tag bit is tested now.
`type_may_be_proxied` keeps deciding which accesses test.

**R11. Closures** are a struct whose first fields are its code (P3 says of what type) and whose subtypes add
the captures at their native types, since only the function's own code reads them. A function that captures
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
stays valid, the session can go on, which the arm64 JIT cannot do ([jit.md](jit.md) §6).

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

## 7. Modules and the JIT: Decisions

**J1. A unit is a module.** Each interface's exports are WebAssembly exports (functions at their native entries,
the module record and initializer, globals), each import an import by name, and the host instantiates the modules
in order: wasmtime by `--preload`, a page by a loader of a few lines. An interaction's module is one more unit. A
whole-program build remains for the module shipped to the page, where inlining across units pays.

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
8. **What the engine hides:** frames for tracebacks, the stack's depth (engines' stacks are smaller than Darwin's
   8 MB, and the compiler recurses deeply), a module's size and start-up time with every descriptor built at
   initialization.

## 9. Steps

Two milestones. The first has steps; the second has stages, whose steps are written when the first is reached and
its measurements are known.

### 9.1. Milestone 1: The Compiler Compiles Itself on WebAssembly

The self-hosted compiler, compiled by the new backend to WasmGC modules, runs in wasmtime and compiles itself there,
writing the same modules its native self writes. Scope is what the compiler and the REPL use (§11, 4); everything
else is pending, with reasons.

1. **A probe by hand.** The alternatives still marked "measure", as WebAssembly text, for a generic vector of
   integers, a hash map, a closure-heavy loop, and records read through views: R4 (structs or arrays), R5 (array
   classes, and what the dispatch costs generic code), P3 (the uniform entry's boxing against a known call), and
   R2's test on every `Int` slot. Timed in wasmtime, and in node once something on the machine writes the binary
   format (`wasm-tools`, if it may be installed, or step 3's encoder). The probe also settles which of wasmtime's
   collectors the suite runs under: the default counts references, and whether it reclaims cycles is to be checked.
   *Done when* R4 and R5 are decided in §4 with their numbers, and P2 says how far `should_specialize` should widen.
2. **A census of what the compiler uses:** which of `lib/`'s 161 externals; `auto`, `inspect`, and `dynamic`;
   identity hashes, and of which shapes (R9); operations on `Real`; `os/process` and the parallel build; and the
   deepest recursion of a self-compilation, against wasmtime's stack.
   *Done when* §6 has the table, and each row says instruction, Quest, host call, or pending.
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
    *Done when* the compiler running in wasmtime, compiling itself with `--backend wasm`, writes modules
    byte-identical to those the native compiler wrote, and the time and peak memory of that self-compilation are
    recorded in [benchmarks.md](benchmarks.md) beside arm64's.

### 9.2. Milestone 2: The REPL in a Page

Stages, in order; steps to be written after milestone 1.

1. **The interpreter's REPL in node, then in a page,** with the session's loop the host's (J3) and imports from URL
   prefixes (J5).
2. **Each interaction a module:** compiled in the session, loaded by the host, linked to the driver's exports and
   to earlier interactions' (J1, J4); in node first, then in the page.
3. **The rest of the language on this target:** `var` and `out` parameters (R8), `dynamic` and the rest of `auto`
   and `inspect`, `Real` in full (§8, 4), and the run suite's pending list worked down.
4. **The page's module:** a whole-program build, its size and start-up time, and whether Binaryen earns a place in
   the build (A2).

## 10. Testing

The shared run goldens, through a runner mode for the backend, with a pending list whose entries give reasons, as
arm64's had; the interpreter as the reference for any difference; wasmtime for the suite, node for whatever loads
modules; and the self-compilation of step 11. The existing suites do not change, and `tools/check` runs the new mode
only when the backend's files differ, until its time is known.

## 11. Questions for the Owner, and the Answers

Answered 2026-11-12.

1. **node beside wasmtime?** *Yes.* Whether tools may be installed (`wasm-tools`, Binaryen) was not said; neither is
   needed before step 3's encoder exists, and step 1 uses `wasm-tools` only if it may.
2. **`var` and `out`: exact references or copying?** *Open.* The owner asked what each costs, noting that the
   parameters are rare and `var` fields common. R8 now answers: `var` fields are not affected; the compiler and
   library pass no locations at all; an exact reference costs about 5 ns a call more than copying. Recommended:
   exact references, by R8's pair. Built in milestone 2.
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
