# questlang/codegen/machine: what native targets share

This directory is the target-independent half of a native backend: the form a function takes once it is made of a
real machine's instructions, and the register allocator that works on that form. A target's instruction selector
(for the one target there is, [`../arm64/select`](../arm64/select.int.quest)) builds a machine function from a
function's SSA ([`../../ssa`](../../ssa)), using *virtual registers*, as many as it likes; the allocator here maps
them onto the target's few physical registers and its stack frame; and the target's code generator
([`../arm64/codegen`](../arm64/codegen.int.quest)) adds the frame and prints or encodes the result. Nothing in this
directory knows an arm64 instruction or a register's name, so that another target (x86-64, say) would write only
its own selection, printer, and target description and reuse all of this.

## A machine function, seen through a narrow window

The problem is how shared code can work on instructions it does not know. Quest's answer, in
[`machine`](machine.int.quest), is to give shared code only what it needs. A `Function` is a list of `Block`s, each
holding `Inst`s; each instruction carries:

- its **operands**, each a register number with whether the instruction reads or writes it. A number below the
  function's `firstVirtual` is a physical register, fixed by the calling convention (an argument's register before a
  call, a result's after); one above is virtual;
- its **kind**, one of six that every target shares: ordinary, move, jump, branch, call (which clobbers the
  registers a call does not preserve), and return;
- an **index** into a table of the target's own operations, which shared code never reads, and a jump's or branch's
  target block.

When shared code must make an instruction itself (a move, a load of a spilled value, a store of one), it asks the
target through `Lowering`, a record of the target's functions for exactly those. This is the structural-typing
alternative to parameterizing the SSA or the instruction set by a target, which in compiled Quest would cost
run-time dictionaries in the compiler's inner loops ([docs/arm64.md](../../../docs/arm64.md) §3.17 explains the
choice).

Virtual registers are in SSA form: each is defined once, by an instruction or as a block's parameter, and a jump
passes an argument for each of its target's parameters (block arguments, instead of the phi functions of textbook
SSA). A move between two registers is not a requirement but a *hint* that they should share one. The module also
provides the analyses the allocator needs: `live` (which virtual registers are live into and out of each block),
`order` (reverse postorder), `loopDepths`, and `removeDead` for instructions whose results nothing reads.

[`target`](target.int.quest) describes a target as data: its registers, each with a class (integer or real) and a
name; which are allocatable, and of those which a call clobbers (caller-saved) and which it preserves
(callee-saved); the registers arguments and results are passed in; the scratch registers kept for the target's own
code; its stack alignment and word size. [`../arm64/target`](../arm64/target.int.quest) is the one description.

## The register allocator

[`regalloc`](regalloc.int.quest) is a *linear scan* allocator with interval splitting, after Wimmer and Mössenböck.
Where a graph-coloring allocator builds a graph of which values are live at the same time and colors it, linear scan
lays the blocks out in one line, numbers the positions, and describes each value by its *lifetime interval*: the
ranges of positions where it is live, with holes where it is not (another value can use its register in a hole).
Taking intervals in order of their starts, it gives each a register free for as long as possible, and never
backtracks. Its interface header explains the algorithm at length; the main ideas are:

- **Splitting and spilling.** When no register is free for all of an interval, it takes one free for a prefix and
  splits the rest off, or takes a register from the intervals holding it, splitting them. A value thus lives in
  *pieces*, each in a register or in memory. Since every value is defined once, a value with a piece in memory is
  stored to its stack slot once, where it is defined; a later piece in a register costs one load. A constant is
  *rematerialized* (made again) instead of stored.
- **Costs.** Which value to spill is chosen by the estimated frequency of its next use: blocks in loops count for
  more, and blocks from which every path raises (cold blocks) for less, so a loop's values keep their registers.
- **Constraints.** Fixed physical operands, registers a call clobbers, and blocks a raise enters (where every
  register is dead, since the handler is reached by unwinding) make registers unavailable where they occur.
- **Hints** let a move's two sides, and a jump's argument and its target's parameter, share a register, so that the
  move disappears; this is what coalescing does in a coloring allocator.

`allocate` returns an `Allocation`, where every piece of every virtual register lives; `shareSlots` lets values
whose lifetimes do not overlap share a stack slot; and `rewrite` replaces the virtual registers by the allocated
ones, inserting loads into scratch registers, stores, and the moves between pieces and on edges. The moves on an edge
must happen as if all at once (a *parallel move*), so `rewrite` orders them, breaking cycles through a scratch
register.

Because the target is a parameter, the allocator is tested on its own, on hand-built machine functions for a toy
target with a few registers, so that its choices show:
[`tests/source/questlang/regalloc_scan.quest`](../../../tests/source/questlang/regalloc_scan.quest).

## What is not here

Frame layout, the prologue and epilogues, the frame maps the collector reads, branch relaxation, and pairing loads
and stores are the target's, in [`../arm64/codegen`](../arm64/codegen.int.quest) and
[`../arm64/peephole`](../arm64/peephole.int.quest). The bootstrap compiler has no native backend, so this directory
has no counterpart there.

## Further reading

- [docs/arm64.md](../../../docs/arm64.md) §3.8 (register allocation) and §3.17 (machine instructions and targets)
- [docs/ssa.md](../../../docs/ssa.md), the SSA that instruction selection starts from
