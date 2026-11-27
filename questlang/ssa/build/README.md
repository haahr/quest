# questlang/ssa/build: from the described IR to SSA

The builder turns a unit of the described IR, the last of the IR stages in [`../../ir`](../../ir), into an SSA unit
(see [`../README.md`](../README.md) for the SSA itself). Its single entry point is `buildUnit` in
[`../build.int.quest`](../build.int.quest), which [`../pipeline.mod.quest`](../pipeline.mod.quest) calls before running
the SSA's passes. The builder is a second implementation of what the C backend's printer
([`../../codegen/c`](../../codegen/c)) prints: for every IR operation, statement, and piece of static data, it emits
the instructions and data that the C code and clang would have produced, so that units built either way link
together and behave the same. Where the C printer can lean on C (struct layout, the calling convention, the runtime
header's `static inline` helpers, `setjmp`), the builder spells the decision out in words, offsets, and calls.

The builder aims to be simple and obviously correct rather than to produce good code; the passes in
[`../passes`](../passes/README.md) improve what it makes. When it meets a construct it cannot build, it raises
`unsupported`, naming the construct, which the backends report as an internal error.

## The structure of the IR it starts from

By the time the builder sees it, the IR has done most of the work of lowering Quest. It is in a form close to ANF
(administrative normal form: every operation's operands are variables or constants, never nested expressions); its
functions are closed, with each closure's environment explicit; each variable has a *representation* (how many
machine words it takes and of what kind); and each type needed at run time has a descriptor, either static data or
something to construct. Its control flow is structured: `if`, `loop` with `break` and `continue`, `switch`, `try`, and
`join`. A *join point* (`sJoin`) is a labelled continuation that jumps in its body enter with arguments, much like a
local function that is only ever called in tail position.

That structure makes the translation direct, statement by statement, in
[`control.mod.quest`](control.mod.quest): an `if` becomes a `branch` to two new blocks that both jump to a third; a
`loop` becomes a head block, which the body jumps back to at its end and at a `continue`, and an after block, which a
`break` jumps to; a join point becomes a block whose parameters are the join's parameters, and each jump to the label
passes its arguments. No φ placement is needed, because the only values that merge at blocks are join parameters.

## Variables

Each IR variable has a `Binding`, defined in [`values.int.quest`](values.int.quest), which says where its value lives:

- An **immutable variable** is bound to SSA values: as many as its representation has parts
  ([`parts`](parts.int.quest)). An `Ok` has none; an `Int` one `int`; a record two words (a pointer to its fields and
  its offset table), and a variant two (its tag and its payload).
- A **mutable variable** is a stack slot, loaded on every read and stored on every assignment, as C compiled without
  optimization keeps it. This is always correct, needs no analysis, and gives `try` what it needs for free: a handler
  sees what the body last stored. The promotion pass later turns the slots it can into values.
- A **`var` or `out` parameter** is the address of the location the caller passed.
- The **variable of a `try`'s handler** is a copy of the runtime's exception state in a slot.
- A **global** is a word of the unit's static data (`g_<name>`): a variable bound at a top level that a function or
  another top level names, or that a module exports. It must outlive the code that binds it, since the unit's
  functions read it later.

A function `let f(x: Int): Int = x + 1` becomes, in outline, a function whose parameters are its closure's
environment pointer and its argument, and whose body is two instructions and a return:

```
function qf_f(%0: ptr, %1: int): int {
b0(%0: ptr, %1: int):
  %2: int = const 1
  %3: int = add %1, %2
  return %3
}
```

## Memory, aggregates, and proxies

Every slot of a tuple, record, option, or array is one word, so aggregates are word arithmetic: the layout and the
offsets come from [`../../repr`](../../repr) (`layout`, `runtimeLayout`, `staticdata`), the same modules the C
backend's declarations are generated from. Reading a field may still take several steps, which
[`objects.mod.quest`](objects.mod.quest) and [`aggregates.mod.quest`](aggregates.mod.quest) build:

- A record's field is found through its **offset table**, since a record viewed at a supertype has the same data but
  fields at different positions; a value of a bounded type parameter goes through the **view map** its type
  argument supplies.
- A tuple or option viewed at a supertype may be a **proxy**: a tagged pointer to a small object that refers to the
  original and maps its components. Reading through one tests the tag bit first. The builder emits that test as a
  single `unproxy` instruction, kept whole until lowering so that value numbering can merge repeated tests of the
  same pointer.
- A **conversion** between representations (the represent pass's plans) moves a value into or out of a box, a `QVal`
  word, or a different view.

Allocation is a call of the runtime's `quest_alloc` with a constant size and the address of the object's **layout**,
a static description of which of its words are pointers, which the builder records once per unit for the collector
([`values.int.quest`](values.int.quest)'s `UnitBuilder`). An object's initializing stores need no write barrier while
it is still young; the builder tracks, with `beginInit` and `endInit`, whether a call that may collect has come
between the allocation and its stores, and emits the barrier when one has.

## Calls, closures, and checks

[`calls.mod.quest`](calls.mod.quest) builds calls. A call's arguments are passed as C passes them, recorded in the
call's signature: a record or variant as a 16-byte pair, a `Bool` or `Char` as a byte, an `Ok` as a zero word. A call
of a variable known to hold a closure of one of the unit's own functions calls that function directly, as the C
backend does; any other closure call loads the code pointer from the closure and calls through it. Calls of the
standard library's external C functions that C would inline (the `word` module's arithmetic and shifts, `ascii.val`,
`string.length`) become instructions instead of calls, so the SSA backends do not pay for calls that the C backend
never makes. Runtime functions are called by name through the table in
[`../runtimefunctions.mod.quest`](../runtimefunctions.mod.quest), which supplies each one's signature.

Run-time checks (bounds, division by zero, counts, ordinals) are built by `check` in
[`values.mod.quest`](values.mod.quest): the test branches to a separate block that computes the source site and calls
the runtime's raise, so that the common path does no work beyond the test.

Type descriptors, which polymorphic code receives as extra arguments, are built in
[`descriptors.mod.quest`](descriptors.mod.quest): a static descriptor is a symbol's address; an instantiated one is
made at run time; and a list of them is passed as an array in a stack slot.

## Exceptions

A `try` builds the runtime's handler record in a stack slot, links it onto the runtime's global handler chain
(`quest_current_exception_handler`), and ends the block with the SSA's `try` terminator, whose handler block the
backend resumes at when the body raises. Every way out of the body (falling off its end, a `break`, a jump to a join
point outside, a `return`) first pops the handler, which is why the builder remembers how many handlers were entered
where each loop and join point is defined.

## The unit

[`unit.mod.quest`](unit.mod.quest) assembles the unit. Besides one SSA function per IR function, it makes:

- the program's `main`, or each module's initializer, guarded by a flag so it runs once;
- the static data: string literals, type descriptors (laid out by [`../statics.mod.quest`](../statics.mod.quest)),
  offset tables, tag maps, static closures of the unit's functions, and object layouts;
- `qr_register_dicts`, which registers the unit's roots (its globals that may hold pointers, and its module records)
  with the collector, its table of function names for tracebacks, and the offset tables of records viewed at
  supertypes.

[`adapters.mod.quest`](adapters.mod.quest) makes the functions that come from types rather than from code: a module
file's exported entry points (`qv_<module>_<member>`), which other units call, and for each function type described
at run time its adapter, thunk, and invoker, the machinery by which the runtime changes a closure's type (a closure's
type fixes how its arguments are passed, so a closure used at another type has to be wrapped).

Finally, each function is finished: blocks that end without a terminator get `unreachable`, and blocks the entry
cannot reach are dropped.

## How the modules depend on one another

The modules form a chain, each using only those before it: `parts` (representations as SSA words), `values` (the
builder's state, emitting, variables, words), `objects` (slots, aggregates' components, proxies, allocation),
`descriptors`, `calls`,
`aggregates`, `control`, `adapters`, and `unit`. [`../build.mod.quest`](../build.mod.quest) re-exports `unit`'s
`buildUnit`.

## Further reading

- [docs/ssa.md](../../../docs/ssa.md) §4 (the builder's rules for variables, memory, closures, the exception
  state, and inline helpers) and §5 (what a unit contains).
- [docs/arm64.md](../../../docs/arm64.md) §7: each decision the C backend leaves to C and clang, and where the builder
  makes it.
- [docs/ir.md](../../../docs/ir.md) §8.4, the described IR.
- [docs/c-representation.md](../../../docs/c-representation.md): the data representation (boxes, offset tables,
  proxies, option payloads) that the builder reproduces in words.
- [docs/exceptions.md](../../../docs/exceptions.md) §5, the handler chain and tracebacks.
- [docs/collector.md](../../../docs/collector.md) §3.2 (layouts) and §3.5 (write barriers).
