# Plan: Value Numbering and Hoisting in the SSA

The SSA's first optimization pass ([arm64-performance-review.md](arm64-performance-review.md) §3.4, §4 item 5, batch
7): redundant pure values and loads removed, along the dominator tree, and loop-invariant ones hoisted out of their
loops, so that both of the SSA's backends (`ssac` and `arm64`) gain. Nothing in the compiler, on the IR or the SSA,
does common subexpression elimination, value numbering, or loop-invariant code motion now. `ssac` has clang's, so
the gain is arm64's; `ssac` must not lose.

**The case it is for.** nucleic's `tfoCombine` (benchmarks/mlton/nucleic.quest line 94) multiplies two 4 by 3
matrices held in tuples. Its SSA has 70 loads of 24 fields: `%1`'s and `%2`'s words, each address made afresh, a
`const` and a `ptrAdd` (`%9 = ptrAdd %1, %8` where `%8 = const 8`) before each load at offset 0. The function is a
chain of blocks each with one predecessor: each `fmul` and `fadd` is followed by its NaN test and a branch to a raise
block, whose call is the only call, and nothing is stored. clang loads each field once (31 loads). The fields are
not proxies there (no proxy test is made), so no branch has to be folded for the loads to match.

---

## 1. Decisions

- **Two passes of the pipeline** ([ssa.md](ssa.md) §4.1), after `promote` and before `tailCalls`: `valueNumbers`
  (§3) and `hoist` (§4). After `promote`, since promotion turns slots into values and so exposes what is redundant;
  before `tailCalls`, which only marks calls. Each can be left out with `QUEST_SKIP_PASSES`, and each has its dump
  (`ssa_valueNumbers`, `ssa_hoist`).
- **Dominator-tree value numbering, scoped,** in the manner of Briggs, Cooper, and Simpson: one walk of the dominator
  tree with a hash table of the expressions available, entered on the way down and removed on the way back. No
  global (partition) value numbering and no partial redundancy elimination: what the case above needs is the
  dominator-tree form, and it is one walk.
- **Two kinds of load** (§2.2). An *invariant* load reads memory that nothing writes once the object it is in has
  been made; the builder marks it, since only the builder knows what it reads. Any other load is numbered only
  within a stretch of code that writes no memory. A field's static type is not enough to make its load invariant:
  `Tuple var a: A end <: Tuple a: A end` ([type-system.md](type-system.md) §3), so an immutable view may alias a
  `var` field that another holder assigns.
- **Not the selection's patterns.** arm64's selection fuses a comparison, a one-bit test, or a conjunction into the
  branch on it, and an index into a load's address, only when it is made in the branch's (or access's) block and used
  once (`select.mod.quest`, `fused` and `indexOf`). Value numbering must not merge two of them across blocks, or the
  branch gets a `cset` and a `cbnz`; those opcodes are numbered only within a block (§2.1).
- **The self-hosted compiler's alone,** as its SSA is ([testing.md](testing.md) §2.8).

## 2. What Is Numbered

### 2.1. Pure Values

An instruction's key is its opcode, its immediate, its symbol, and its arguments' value numbers: `const`,
`realConst`, `symbol`, `null`, `slot`, `threadLocal`, `ptrAdd`, integer and real arithmetic, bitwise operations,
conversions (`intToPtr`, `ptrToInt`, `toVal`, `fromVal`, `realBits`, `bitsReal`, `sext8`, `zext8`), and `isNaN`.
Commutative operations (`add`, `mul`, `and`, `or`, `xor`, `eq`, `ne`, `peq`, `pne`, `fadd`, `fmul`, `feq`) order
their arguments by number. A `copy` is replaced by its argument. `div` and `rem` are numbered (they cannot trap
once the builder's tests have passed, and a dominating one ran after the same tests) but never hoisted (§4).

The comparisons (`eq` to `ult`, `peq`, `pne`, the real comparisons), an `and` with a constant (a one-bit test), and
`ptrAdd` and `mul` by an access's width are what selection fuses; they are replaced only by an equal one earlier in
the same block. Constants and symbols are numbered across the function: arm64's allocator rematerializes them
(`select.rematerializable`) rather than spilling them, but not a constant that takes `movz` and `movk` or a real
constant's `fmov`, so §5 measures numbering constants function-wide against block-local, and keeps the faster.

A block's parameter whose every incoming argument is one value (or the parameter itself) is that value, and is
removed from its block and its jumps' arguments.

### 2.2. Loads

A load's key is its address taken apart as a base value plus a constant byte offset (through `ptrAdd`s of
constants, so that `load8 %9 + 0`, `%9 = ptrAdd %1, const 8`, and `load8 %1 + 8` are one key), its width, its
extension, and its type.

- **An invariant load** (`load8 … invariant` in the textual form, ssa.md §6) is available wherever the earlier one
  dominates it, across stores and calls, and may be hoisted (§4). The builder marks the loads of what is never
  written after it is made: a closure's code and environment pointers, an environment's captured values (a captured
  `var` is a cell, whose contents are not marked), an array's and a string's length and a string's data pointer, a
  record's offset table and its words, a proxy's original, an option's ordinal, a type descriptor's words, and the
  words of static data that is not writable (`Data.writable` false). A module's record is written while the module
  is initialized, so its loads are not marked. Step 2 lists each marked load in the builder, with the reason it is
  invariant.
- **Any other load** is available only while no memory has been written: each block's walk keeps a memory
  generation, which a `store`, a call (direct or indirect) of anything but a runtime function the effects table
  (`codegen/runtimeFunctions`) says writes nothing, and a `try` advance. A block inherits its immediate dominator's
  generation at the end of the dominator's walk when the dominator is its only predecessor, and starts a new one
  otherwise. That covers `tfoCombine`, whose blocks each have one predecessor; a join (an `if` without an `else`
  over a field read twice) is §5's question, answered by measuring before a finer rule is written.
- **A store makes its value available** to a later load of the same key, in its generation, as promotion does for a
  slot: `counter.count := counter.count + 1` then a read of `counter.count`.

The escape pass turns an allocation that does not escape into a stack slot and its accesses into the slot's, and a
slot in a loop is reused each time round: it clears the invariant mark on the loads it redirects, so that a load of
one iteration's tuple is not taken as the next's.

## 3. The Value-Numbering Pass

`questlang/ssa/valueNumbers`, on each function, with `cfg.graph`:

1. Walk the dominator tree from the entry, keeping a table of available keys (§2), scoped by the tree: each block's
   entries are removed after its children are walked.
2. In each block, replace each block parameter that §2.1 finds trivial; then for each instruction, look up its key.
   If an equal value is available, replace the instruction's result by it (`nodes.replaceUses`, collected and
   applied once at the end) and remove the instruction; otherwise enter it. A store or a writing call advances the
   generation after its own entry, and a store enters its value under its key in the new generation.
3. Remove the pure instructions left without uses (the `ptrAdd`s and `const`s of the addresses replaced loads used),
   to a fixed point, since nothing else in the pipeline removes dead values.

The pass keeps the blocks and terminators as they are, so the graph stays valid throughout.

## 4. The Hoisting Pass

`questlang/ssa/hoist`, on each function, after `valueNumbers`:

1. Find each natural loop (cfg's back edges, as `cfg.loopDepths` walks them) and give each a **preheader**: the one
   predecessor from outside if its only successor is the header, or else a new block that the edges from outside go
   to, passing the header's parameters through. The graph is made again after preheaders are added.
2. From the innermost loops outward, move to the preheader each instruction of the loop that is pure (§2.1) or an
   invariant load (§2.2), whose arguments are all defined outside the loop (or hoisted already), and that is safe to
   run every time the preheader is reached:
   - pure arithmetic, bitwise operations, conversions, `ptrAdd`, constants, and symbols, but not `div` and `rem`, and
     not a shift by a count that is not a constant: `ssac` writes C, in which a division by 0 and a shift by 64 or
     more are undefined, though the code that guards them would never let them run;
   - an invariant load whose block dominates every exit of the loop (every edge to a block outside it, the edges to
     raise blocks included), so that it runs after the null and proxy tests that guard its address, or whose address
     is a symbol's or a slot's.
   - Nothing that selection fuses (§2.1), since it would leave its block.
3. Then `valueNumbers` again, if §5 finds that hoisting leaves duplicates in the preheaders (two loops' hoisted
   copies of one constant, say); the pipeline runs a pass by name, so this is one more name in `pipeline.passes`.

Hoisting lengthens what is live across a loop, which arm64's linear scan may spill (review §3.1). §5 measures it
alone, apart from value numbering.

## 5. Measurement

Each against the commit before it, as batches 4 and 5 were (review §4): `tools/perf/timeit.py`, five rounds at a
thirty-second of the suite's counts, through C, `ssac`, and arm64, on the twelve of the review's last table and
even-odd; and the suite's geometric means with `run.py time --clean` at `--scale 0.25`
([benchmarks.md](benchmarks.md) §11). Also counted, with `tools/perf/variants.py`'s builds:

- loads in `tfoCombine` (70 now; clang has 31) and in each program, static;
- `cset`s, to show that no fused branch was lost (§2.1);
- spill stores and reloads, before and after hoisting;
- the time the self-hosted compiler takes to build itself (`./quest`'s driver build, `QUEST_JOBS` 8), since the
  passes run on every function of every unit.

The questions to answer by measuring, each in its step's commit:

- constants and symbols numbered across the function, or only within a block (§2.1);
- whether the new memory generation at every join loses loads worth a finer rule (§2.2);
- whether hoisting gains on arm64 at all once its spills are counted, and whether `valueNumbers` is worth running
  again after it (§4).

## 6. Testing

- **Per-pass tests** in the textual SSA, read by `questlang/ssa/parser`, as `ssa_tailcalls` and `ssa_escape` are:
  `tests/source/questlang/ssa_valuenumbers.quest` and `ssa_hoist.quest`, each function printed before and after its
  pass and verified. For value numbering: pure values repeated in one block and across a dominator; commuted
  arguments; a load at `ptrAdd` plus offset matching one at an offset; an ordinary load across a store, across a
  writing call, across a call of a runtime function that writes nothing, and across a join; an invariant load across
  each of those; a store's value read back; a trivial block parameter; a comparison feeding branches in two blocks
  (not merged). For hoisting: an invariant load in a loop's body that dominates its exits (hoisted) and one in a
  conditional arm (not); a `div` (not); a loop whose header has two outside predecessors (a preheader made); nested
  loops.
- **The marks:** the SSA goldens show `invariant` on the loads the builder marks; `language/` tests that assign a
  `var` field read through an immutable view, through an alias, across a call, inside a loop, check that no such
  load is taken as invariant (`language/var_field_views`, new).
- **Every backend and the fixed points:** `tools/check`, which builds the compiler with itself through `ssac` and
  arm64 with the passes, and runs the backends' suite through both; and the 46 benchmarks' `run.py check` through
  arm64 (whole-program and separate) and `ssac`, since the suite's own tests have few hot loops.

## 7. Steps

| | Step | Lines | Checks |
|---|---|--:|--:|
| 1 | The baseline: §5's timings and counts at `main`, with 35f49904's inlined library operations | tools only | — |
| 2 | Invariant loads: the mark on `Inst` and in the text, the builder's marks, escape clearing them | 50 to 150 | 1 |
| 3 | `valueNumbers`: pure values and invariant loads (§2.1, the first half of §2.2, §3) | 200 to 400 | 1 |
| 4 | Ordinary loads, by memory generation, and stores' values (the rest of §2.2) | 50 to 150 | 1 |
| 5 | `hoist`, with preheaders (§4) | 150 to 300 | 1 to 2 |

- **Step 1** *is done when* the review's §4 has the twelve and even-odd timed at `main`, and `tfoCombine`'s loads
  counted, since the batch 4 and 5 timings predate 35f49904.
- **Step 2** changes no code that runs: *done when* every SSA golden shows the marks (one regeneration), the parser
  reads them back, and `language/var_field_views` passes everywhere.
- **Step 3** *is done when* its per-pass test shows each case of §6, the 46 benchmarks pass through each backend,
  and its timings are recorded. Constants are measured function-wide and block-local here.
- **Step 4** *is done when* `tfoCombine` has about 24 loads on arm64 and the join question of §5 is answered by a
  count of the loads a join cost across the suite.
- **Step 5** *is done when* it is measured alone against step 4; if it gains nothing on arm64 once its spills are
  counted, it is not kept, as loop rotation was not (review §4), and §4 records why.

Each step is committed alone and measured against the one before it; the batch is pushed after one `tools/check`
run, as batches 4 and 5 were. When it is done, the design moves to [ssa.md](ssa.md) §4 (a section beside §4.2's
escape analysis) and this plan is deleted, as the finished plans were (474f578b).
