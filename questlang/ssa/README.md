# questlang/ssa: the native backends' SSA

This directory holds the self-hosted compiler's low-level intermediate form, an SSA (static single assignment: every
value is defined exactly once, by one instruction or as one block parameter). It sits between the IR stages and the
native backends. Its input is a unit of the described IR, the last of the IR stages in [`../ir`](../ir), in which
every variable already has a machine representation and every type that is needed at run time has a descriptor. Its
output is an SSA unit that one of three consumers turns into code: the arm64 backend
([`../codegen/arm64`](../codegen/arm64)), the default; `ssac`
([`../codegen/c/ssac.int.quest`](../codegen/c/ssac.int.quest)), which prints the SSA as C and serves as an oracle
for it; and the JIT ([`../jit`](../jit)), which runs the arm64 backend in memory. The C backend
([`../codegen/c`](../codegen/c)) does not use the SSA; it prints the described IR directly. The bootstrap
compiler has no SSA and no counterpart to this directory.

The SSA is target-independent but close to the machine. Where the IR still speaks of tuples, records, options,
closures, and `try`, the SSA speaks of 64-bit words, byte offsets, calls with C signatures, and branches. Everything
that the C backend leaves to C and clang (struct layout, the calling convention, the runtime header's inline helpers,
`setjmp`) the SSA decides itself, since the units it produces link with units the C backend compiles.

## Values, instructions, and blocks

The data structures are in [`nodes.int.quest`](nodes.int.quest). A function's values, blocks, and stack slots are each
numbered densely from 0, so that a pass keeps its facts about them in plain arrays indexed by number.

**Values have one of four machine types.** `int` is a 64-bit integer (Quest's `Int`, `Word`, `Bool`, and `Char` all
become one, as do tags, sizes, and offsets); `ptr` is a pointer the garbage collector must treat as a pointer; `real`
is a double; and `val` is a `QVal`, the runtime's uniform one-word representation of a value whose type is a type
parameter, which may or may not be a pointer depending on the type its descriptor names. Keeping `ptr` apart from
`int` lets the arm64 backend tell the collector precisely which stack slots and registers hold pointers. There are no
aggregate types: a record or variant value, 16 bytes in the C representation, is simply two values.

**Every instruction has one shape**: an opcode, an array of argument values, an array of result values, an immediate
integer, a symbol, and a source position (`Inst` in [`nodes.int.quest`](nodes.int.quest)). Loads and stores also carry
a width (8, 4, or 1 bytes), and calls carry a `Signature` saying how C passes each argument and result: in a word, in
a floating-point register, as half of a 16-byte pair, as a byte, or through memory. The uniform shape means that the
passes that care only about structure (the verifier, renaming, use counts) walk the argument and result arrays without
knowing what each opcode means.

**Blocks take parameters instead of φ nodes.** A block has a list of parameter values, its instructions, and one
terminator: `jump`, `branch`, `switch`, `return`, `tailCall`, `try`, or `unreachable`. A jump passes an argument for
each parameter of the block it goes to. Where a textbook SSA puts a φ node at a join to merge the values that reach it
from different predecessors, this SSA gives the join block a parameter and has each predecessor pass its value. Block
0 is the entry, and its parameters are the function's.

**`try` is a terminator.** It names the stack slot holding the handler record (already pushed on the runtime's chain),
a body block, and a handler block. The handler's only predecessor is the `try`'s block, so ordinary dominance gives
the rule exception handling needs: a handler uses only values defined before the `try`. How control actually reaches
the handler is each backend's choice (`ssac` uses `_setjmp`; arm64 records a resume address).

A **unit** is its functions plus its static data: zeroed storage for globals, C strings for literals, and words (each
an integer or a symbol's address) for type descriptors, offset tables, layouts, and the like.

## A small example

The SSA has a textual form, which [`printer.mod.quest`](printer.mod.quest) writes and `--stop-after ssa` prints. A loop
that counts up to its argument, as the builder makes it, keeps its counter in a stack slot:

```
function count(%0: int): int slots [8:8] {
b0(%0: int):
  %1: ptr = slot 0
  %2: int = const 0
  store8 %1 + 0, %2
  jump b1()
b1():
  %3: int = load8 %1 + 0
  %4: int = lt %3, %0
  branch %4, b2(), b3()
b2():
  %5: int = load8 %1 + 0
  %6: int = const 1
  %7: int = add %5, %6
  store8 %1 + 0, %7
  jump b1()
b3():
  %8: int = load8 %1 + 0
  return %8
}
```

After the promotion pass the slot is gone, and the counter is a parameter of the loop head `b1`, which the entry and
the loop's back edge each pass a value for:

```
function count(%0: int): int {
b0(%0: int):
  %2: int = const 0
  jump b1(%2)
b1(%9: int):
  %4: int = lt %9, %0
  branch %4, b2(), b3()
b2():
  %6: int = const 1
  %7: int = add %9, %6
  jump b1(%7)
b3():
  return %9
}
```

(Both are from the questlang test `ssa_promote`.) [`parser.mod.quest`](parser.mod.quest) reads the text back into a
unit with the values' numbers unchanged, so that a pass can be tested on SSA written by hand, and so that the driver,
under `QUEST_CHECK_IR=1`, can check that every SSA it prints reads back as itself.

## From the described IR to final SSA

[`pipeline.mod.quest`](pipeline.mod.quest) is the entry point the backends and the JIT call. Its `build` runs three
phases:

1. **The builder** ([`build/`](build/README.md)) turns each IR function, the module initializers, and the program's
   `main` into SSA, and lays out the unit's static data. It favors simplicity over quality: every mutable variable
   is a stack slot, loaded and stored, and every allocation is a call of the runtime's `quest_alloc`.
2. **The passes** ([`passes/`](passes/README.md), whose README lists them) run in a fixed order, each on every
   function of the unit, named in [`passnames.mod.quest`](passnames.mod.quest). The SSA is valid after each one, so
   any pass can be left out (the environment variable `QUEST_SKIP_PASSES`), which is how a miscompilation is bisected.
3. **Lowering**, which `pipeline.lower` runs just before code generation, expands two instructions that the passes
   prefer to see whole: `unproxy`, and calls of `quest_alloc`, which become the collector's inline bump-pointer
   sequence.

Scalar replacement lives here, in [`scalars.mod.quest`](scalars.mod.quest), rather than in `passes/`, but it runs as
one of the passes, after promotion. It replaces objects that a block parameter merges (a tuple carried around a loop,
say) by the values of their words.

## Shared analyses and tables

Several modules here serve the builder, the passes, and the backends alike.

- [`cfg.int.quest`](cfg.int.quest) computes a function's control flow graph: predecessors and successors, reverse
  postorder, the dominator tree (by Cooper, Harvey, and Kennedy's algorithm), dominance frontiers, and loop depths.
  Promotion places block parameters at dominance frontiers; value numbering walks the dominator tree; the verifier
  checks that every definition dominates its uses. The arm64 backend and the machine layer
  ([`../codegen/machine`](../codegen/machine)) use the same module for their own block graphs.
- [`runtimefunctions.mod.quest`](runtimefunctions.mod.quest) is a table of every runtime function the SSA calls: its C
  prototype, from which its SSA signature follows, and its effects (whether it reads or writes memory, may raise,
  allocates, or never returns). The passes read the effects to know, for instance, that `quest_alloc` writes only the
  object it makes, so a value loaded before the call is still valid after it. A questlang test checks the table against
  `runtime/quest_runtime.h`.
- [`statics.mod.quest`](statics.mod.quest) lays out type descriptors and object layouts as words of static data,
  matching the runtime's C structs, from the backend-independent descriptions in [`../repr`](../repr).

## Checking

The SSA is checked by two analyses that run after the pipeline every time, and after the builder and every pass when
`QUEST_CHECK_IR=1`.

[`verify.mod.quest`](verify.mod.quest) checks the SSA's structural invariants: each value defined once and dominating
its uses, every instruction's arguments and results of the number and types its opcode takes, calls matching their
signatures, jumps passing the right number and types of arguments, every block terminated, and a `try`'s handler
reached only from its `try`.

[`barriers.mod.quest`](barriers.mod.quest) checks the rule that keeps the generational collector sound. When a
pointer is stored into an object that a collection may already have seen (an old object), the runtime must be told,
by a call of a *write barrier* (`quest_barrier` or `quest_barrier_slot`), before anything that may collect; otherwise
a minor collection, which scans only young objects and the old ones the barriers logged, could free a young object
still reachable from an old one. The builder emits barriers by this rule, and a pass that moves or removes stores
could break it. The check is a forward dataflow analysis over each function, tracking which allocations are still
young and which stores still owe a barrier, and it reports any store still owed at a call that may collect or at a
return. A missed barrier would otherwise show up only when a collection happened to fall in the window.

## How it connects

The driver ([`../driver`](../driver)) dumps the SSA after the builder (phase `ssa_built`), after each pass
(`ssa_escape`, `ssa_promote`, and so on), and at the end (`ssa`); the `ssa` goldens in `tests/golden/ssa` hold the
final form for every run test, and the questlang tests `ssa_promote`, `ssa_escape`, `ssa_valuenumbers`, and their
siblings run each pass on SSA written as text. [`../codegen/backend.mod.quest`](../codegen/backend.mod.quest) calls
`pipeline.build` and `pipeline.lower` for the `arm64` and `ssac` backends; [`../jit`](../jit) does the same for the code
it compiles; and the Jupyter kernel's driver turns on interrupt checks (`pipeline.setInterruptChecks`), which put a
test of the runtime's interrupt flag at each function's entry and loop head.

Inside, the builder depends on [`../ir`](../ir) for its input and on [`../repr`](../repr) for layouts and descriptor
descriptions; the passes depend only on the SSA's own modules.

## Further reading

- [docs/ssa.md](../../docs/ssa.md): the SSA's reference: types (§1), instructions (§2), blocks and `try` (§3), the
  builder and every pass (§4), units (§5), the textual form (§6), the verifier and barrier check (§7).
- [docs/arm64.md](../../docs/arm64.md) §3.2 (where the SSA sits), §3.14 (`ssac`), §3.15 (why the data structures are
  arrays of numbered values), and §7 (each decision the C backend leaves to clang, and where the SSA makes it).
- [docs/ir.md](../../docs/ir.md) §8.4, the described IR the builder starts from.
- [docs/collector.md](../../docs/collector.md) §3.4 (inline allocation) and §3.5 (generations and write barriers).
- [docs/compiler-organization.md](../../docs/compiler-organization.md), for where `ssa/` sits among the compiler's
  layers.
