# questlang/ssa/passes: the SSA's optimizations and lowerings

The modules here transform the SSA (see [`../README.md`](../README.md)) between the builder
([`../build`](../build/README.md)), which makes straightforward but slow code, and the backends (arm64, `ssac`, and the
JIT), which translate what the passes leave nearly instruction for instruction. Each pass takes a unit and rewrites
its functions in place; each leaves valid SSA, which the verifier and the write-barrier check can confirm after it
(with `QUEST_CHECK_IR=1`), and each can be left out by name with `QUEST_SKIP_PASSES` to find which one breaks a
program. [`../pipeline.mod.quest`](../pipeline.mod.quest) decides what runs and in what order.

Most of the optimizations exist because of a measured gap: something clang does to the C backend's output that the
arm64 backend, which has no optimizer of its own beyond instruction selection and register allocation, would
otherwise miss. The interface comment of each module says what it does and why; this README explains how they fit
together.

## The order

| Order | Pass | What it does |
|---|---|---|
| 1 | [`escape`](escape.int.quest) | allocations that never leave their function become stack slots |
| 2 | [`promote`](promote.int.quest) | stack slots become SSA values |
| 3 | [`scalars`](../scalars.int.quest) | objects merged at block parameters become their words' values |
| 4 | [`constants`](constants.int.quest) | globals stored once with a constant become read-only constants |
| 5 | [`valueNumbers`](valuenumbers.int.quest) | redundant computations and loads are removed |
| 6 | [`conditions`](conditions.int.quest) | branches a dominating branch on the same comparison decides become jumps |
| 7 | [`selects`](selects.int.quest) | small two-armed branches become `select`s (if-conversion) |
| 8 | [`tables`](tables.int.quest) | dense switches of constants become table loads |
| 9 | [`accumulate`](accumulate.int.quest) | recursion through `+`, `*`, and the like becomes a loop |
| 10 | [`tailCalls`](tailcalls.int.quest) | calls in tail position are marked |
| 11 | [`tailJumps`](tailjumps.int.quest) | mutually tail-recursive functions become loops |
| 12 | [`trampolines`](trampolines.int.quest) | an exported entry point gets a copy of the function it forwards to |
| | [`interrupts`](interrupts.int.quest) | Jupyter kernel only: interrupt-flag checks at entries and loop heads |
| | [`unproxies`](unproxies.int.quest) | lowering: each `unproxy` becomes a test and a branch |
| | [`allocations`](allocations.int.quest) | lowering: each `quest_alloc` becomes the collector's inline fast path |

The first twelve are `pipeline.passes`, run by `pipeline.build`, and the driver can dump the SSA after each (phases
`ssa_escape`, `ssa_promote`, and so on). Scalar replacement is a pass like the others, though its module is in the
parent directory. The interrupt checks run at the end of `build`, and only when the kernel's driver turns them on.
The last two are lowerings, run by `pipeline.lower` just before code generation, so they appear in no dump.

## From the heap to registers

The first three passes work together to undo the builder's two simplifications: every mutable variable is a stack
slot, and every tuple, option payload, and record box is a heap allocation. After inlining (an IR pass) brings the
code that makes an object and the code that takes it apart into one function, many of those allocations are never
seen by anyone else.

**Escape analysis** ([`escape.mod.quest`](escape.mod.quest)) finds them. An allocation *escapes* if any pointer to it
could outlive or leave the function: passed to a call, stored somewhere other than into itself, returned, or compared.
Its pointers are the allocation's result and anything derived from it by a constant offset, by a block parameter that
is only ever bound to it, and so on. The analysis is per function, with no knowledge of other functions, and
conservative. An allocation that does not escape is replaced by a stack slot of the same size, zeroed where the
allocation was; its write barriers go, since a stack slot is already a root for the collector.

**Promotion** ([`promote.mod.quest`](promote.mod.quest)) then turns stack slots, both the builder's mutable variables
and the ones escape analysis just made, into SSA values. This is the classic SSA construction of Cytron et al.: each
word of a slot is a variable; a block where different definitions of it meet gets a parameter (placed at the
iterated dominance frontier, using [`../cfg.int.quest`](../cfg.int.quest)); and a walk down the dominator tree
replaces each load with the value last stored. A slot whose address is used for anything but loads and stores, or any
slot in a function that enters a `try` (whose handler must see memory as the body left it), stays a slot.

**Scalar replacement** ([`../scalars.mod.quest`](../scalars.mod.quest)) handles what escape analysis cannot: an object
that a block parameter merges with others, such as a tuple carried round a loop and rebuilt on every iteration, or an
option that is sometimes freshly allocated and sometimes a constant from static data. It groups the objects whose
pointers meet, and if every use of the group is a plain load, replaces each pointer parameter by the group's word
values, so a loop that carried a tuple carries its components.

Both escape analysis and scalar replacement rely on one fact the rest of the SSA does not know: a fresh allocation is
never a *proxy* (the tagged pointer that stands for a tuple or option viewed at a supertype), so the builder's tests
for one fold to false. [`proxyfold.mod.quest`](proxyfold.mod.quest) holds what the two share: finding each value's
definition, recognizing those proxy tests, and computing which blocks remain reachable once they fold.

## Cleaning up

**Constant globals** ([`constants.mod.quest`](constants.mod.quest)): a module's member bound to a constant, such as
`let oneW = word.fromInt(1)`, is a global that the module's initializer stores once and every use loads, inside every
loop that uses it. When nothing could read the global before its single store, and the unit does not export it, the
pass makes its static data hold the value from the start and replaces each load with the constant.

**Value numbering** ([`valuenumbers.mod.quest`](valuenumbers.mod.quest)) is the general cleanup, in the manner of
Briggs, Cooper, and Simpson: walking the dominator tree, an instruction equal to one that dominates it (same opcode,
immediate, and argument values) is replaced by the earlier one. Loads take part as long as nothing in between may have
written memory, using the effects table in [`../runtimefunctions.int.quest`](../runtimefunctions.int.quest) to know
which runtime calls write none; loads marked *invariant* by the builder (a closure's code pointer, an array's length)
are reused across anything. A load right after a store to the same word becomes the stored value. Because the arm64
backend folds comparisons, constants, and address arithmetic into the instruction that uses them, those are reused
only within their own block: sharing them across a function made them live longer and spill. Instructions left
unused are removed.

## Shaping control flow

**Selects** ([`selects.mod.quest`](selects.mod.quest)) is if-conversion: a branch whose two arms only pass different
values to the same join becomes a straight jump with a `select` choosing between the values, which arm64 makes a
`csel` or `cset`. It pays off on unpredictable branches, such as the carry in arbitrary-precision arithmetic.

**Tables** ([`tables.mod.quest`](tables.mod.quest)): a `switch` of at least four dense cases, each of which only
passes constants to one join, becomes a range check and a load from a table in the unit's static data, as clang does
with such a C `switch`.

## Calls and recursion

**Accumulator recursion** ([`accumulate.mod.quest`](accumulate.mod.quest)): a function such as

```
let rec sum(n: Int): Int = if n is 0 then 0 else n + sum(n - 1) end
```

is not tail-recursive, since the addition follows the call. Because `Int` arithmetic wraps, `+` is associative, so the
pass rewrites the function as a loop with an accumulator parameter that starts at 0 and adds `n` each time round.

**Tail calls** ([`tailcalls.mod.quest`](tailcalls.mod.quest)) marks a call whose results are what its function
returns, directly or through blocks that only pass them on, by making it the block's `tailCall` terminator, which the
backends compile as a jump rather than a call. A function from which a stack slot's address may escape, including any
function with a `try`, has none, since a tail call ends the caller's frame.

**Tail jumps** ([`tailjumps.mod.quest`](tailjumps.mod.quest)) handles mutual recursion. The direct tail calls among
the unit's functions form a graph, whose strongly connected components (by Tarjan's algorithm) are the groups of
mutually tail-recursive functions. Into each member of a group are copied the others it reaches, within a size limit,
so that each tail call to another member becomes a jump to its copy: `even` and `odd` calling each other become one
loop in each.

**Trampolines** ([`trampolines.mod.quest`](trampolines.mod.quest)): other units call a module's function through an
exported entry point that does nothing but tail-call the function, often through an adapter that tail-calls it in
turn. The pass copies a small enough function, and its adapter, into its exported entry point, so that a call from
another unit runs the function without the intermediate hops. It reuses tail jumps' copying (`tailJumps.spliceInto`).

## Lowering for the backends

**Unproxies** ([`unproxies.mod.quest`](unproxies.mod.quest)): until now, the test of whether a pointer is a proxy, and
the load of the original if it is, has been a single pure `unproxy` instruction, so that value numbering could merge a
loop's repeated tests into one before the loop. This pass expands each into a branch on the tag bit and a join.

**Allocations** ([`allocations.mod.quest`](allocations.mod.quest)): the C backend gets the collector's allocation fast
path inline from the runtime's header. The SSA backends get it here: each `quest_alloc` of a constant size becomes a
load of the allocation cursor and limit, a bump of the cursor when there is room, a store of the header word, and a
call of the runtime's slow path otherwise.

**Interrupts** ([`interrupts.mod.quest`](interrupts.mod.quest)), for the Jupyter kernel only, splits each function's
entry and each loop head to test the runtime's interrupt flag, so that a cell stuck in a loop can be interrupted.

## Testing

Each pass has a questlang test (`ssa_escape`, `ssa_promote`, `ssa_scalars`, `ssa_valuenumbers`, and so on, in
`tests/source/questlang`) that reads small functions written in the SSA's textual form, runs the pass and the
verifier, and prints the functions before and after; `tests/golden/run/questlang` holds the expected output.

## Further reading

- [docs/ssa.md](../../../docs/ssa.md) §4.1 (each pass in detail, with the measurements that motivated it), §4.2
  (escape analysis), and §4.3 (scalar replacement).
- [docs/benchmarks.md](../../../docs/benchmarks.md), where the effect of each pass was measured.
- [docs/arm64.md](../../../docs/arm64.md) §3.7 (tail calls) and §3.6 (why a function with a `try` keeps its slots).
- [docs/collector.md](../../../docs/collector.md) §3.4 (the inline allocation sequence) and §3.5 (write barriers).
- [docs/jupyter-kernel.md](../../../docs/jupyter-kernel.md) §5 (interrupts).
