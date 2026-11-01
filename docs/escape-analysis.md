# Plan: Escape Analysis in the SSA

Allocations whose pointers never leave the function that makes them, removed in the SSA, so that both of its backends
(`ssac` and `arm64`) gain: a tuple made only to be taken apart, the tuple `o!tag` makes to read one component of,
an option's payload tuple copied into the option, a record's box only read, the box of an option that is tested and
unwrapped where it was made. It generalizes two fixes made in the C printer with [option-values.md](option-values.md)
(§6), and comes before that plan's step 3 (single-word options as nullable pointers, deferred), which is to be judged
by the allocations that remain.

---

## 1. Decisions

- **In the SSA, as a pass of its pipeline** ([ssa.md](ssa.md) §4.1), before `ssa/promote`: it serves both
  backends that start from the SSA, and reuses promotion rather than repeating it (§3).
- **An allocation that does not escape becomes a stack slot** of its size, zeroed as `quest_alloc`'s memory is; the
  existing promotion then makes values of the slots whose words are only loaded and stored. Where promotion cannot
  (a function that enters a `try`, a byte-wide access promotion refuses), the slot is still cheaper than the heap.
- **Conservative and local:** one function at a time, no interprocedural summaries. A pointer passed to any call,
  stored anywhere, returned, captured, or passed through a block argument escapes. Inlining
  ([inlining.md](inlining.md)) is what brings producer and consumer into one function.
- **The C printer keeps its own fixes** (§6) while it is the default backend, unless §6's measurements show them
  unnecessary; arm64.md step 15 (`ssac` as the C backend) would retire them.
- **The self-hosted compiler's alone,** as its SSA is ([testing.md](testing.md) §2.8).

## 2. What Escapes

A candidate is a call of `quest_alloc` with a constant size (`vals.alloc`); `quest_array_new`, exceptions, and the
runtime's other allocators are not candidates. Its result, and pointers derived from it by a constant offset
(`offsetPtr`), are *its pointers*. The allocation does not escape when every use of each of its pointers is:

1. **The address of a load or store** at a constant offset within the allocation's size (not the value stored).
2. **A proxy test** (`vals.isProxy`: `and(ptrToInt(p), QUEST_PROXY_TAG)`): a fresh allocation is never a proxy, so
   the test folds to zero, and the branches `vals.unproxy` and the tuple and option readers make on it fold to their
   direct arm. The fold is the pass's own (§3), since nothing else in the SSA knows that `quest_alloc` returns an
   aligned pointer.
3. **A value stored into a word of the allocation itself:** a word whose stores all store one of its pointers, at one
   offset, holds that pointer (as a tuple's first word holds the address of its fields), and a whole load of it is
   one of its pointers too.
4. **An argument bound to a block's parameter** that every edge taken binds to that one value (as the merge after a
   folded proxy test is): the parameter is one of its pointers.

Anything else is an escape: an argument to a call (the runtime's included: `quest_option_is`, `quest_val_is`, a
conversion), a value stored to memory, a return, a parameter bound to other values too, a comparison (`peq`, which
could fold but is left for now), a `toVal`, a `ptrToInt` used other than in a proxy test, or an access of part of a
word holding a pointer. Since the folds decide which blocks are reached, and a parameter's binding depends on the
edges reached, the analysis starts with every allocation thought not to escape, finds its pointers and the blocks
reached to a fixed point, and drops those that do escape, until none more does.

## 3. The Pass

`questlang/ssa/escape`, `ssa_escape` in the pipeline before `ssa_promote`:

1. Find the candidates and their pointers, and the blocks reached (§2).
2. For each that does not escape: fold its proxy tests (each `and` a zero, each branch on one a jump to its false
   arm); replace the call by a fresh stack slot of its size (whole words), its words stored zero where the call was,
   so that a load before a store reads zero as the heap's zeroed memory did, each zero of the type the word is
   stored (or loaded) as, so that promotion sees one type; access it through the slot's address, its derived
   pointers' offsets added to the accesses' own; and drop its derived pointers, the words holding its pointer and
   their stores and loads, its `ptrToInt`s, and the parameters bound to its pointers, with their arguments.
3. Drop the blocks no longer reached, renumbering the rest, as the builder does.
4. Leave the rest to `ssa/promote` and the existing dead-value handling: the stores to a promoted slot's words
   become values, and loads of them those values.

A slot is per function, not per execution: an allocation in a loop reuses its slot each time round, zeroed each
time. That is sound because a parameter that is one of its pointers is bound to that one value on every edge
(§2), so no pointer from one iteration is live in the next.

Promotion does not take a slot whose word is stored and loaded as different types: a tuple of a type parameter's
values stores a `val` and may load it as a `ptr`. Such slots stay slots, which is still cheaper than the heap.

## 4. Testing

- **Per-pass goldens** (`ssa_escape`), small functions in the textual SSA as `ssa_promote`'s are
  ([ssa.md](ssa.md) §6, [backend-improvements.md](backend-improvements.md) §3.4): an allocation only loaded and
  stored (removed); one stored into another, passed to a call, returned, or passed as a block argument (kept); one
  made in a loop; one behind proxy tests; one compared with another pointer; one in a function that enters a `try`
  (a slot, not promoted).
- **Language tests** that run in every backend: `language/escaping_allocations`, whose values must survive each kind
  of escape and whose fresh tuples and options must behave as before (identity included: two fresh tuples are not
  `is` each other).
- **Every backend's runner mode and the fixed points:** the compiler builds itself through `ssac` and `arm64` with
  the pass (`tools/check`).
- **Allocation counts,** recorded by a counting interposer of `GC_malloc` (the one used for benchmarks.md §7.2's
  ratio-regions finding, made a tool, `benchmarks/mlton/allocations.py`): ratio-regions, peek, zebra, and the
  suite, through `ssac` and `arm64`, before and after.

## 5. Steps

1. **The allocation counter as a tool:** `benchmarks/mlton/allocations.py NAME... [--backend b] [--whole-program]`,
   building each benchmark and reporting its allocations by function. *Done when* it reproduces benchmarks.md
   §7.2's ratio-regions counts. *Done* (2026-11-01): at `--count 96` it counts the 22,355,456 allocations of
   benchmarks.md §8.2 through C (§7.2's 29.3 million predate options as values), and through `ssac` and `arm64`,
   whose allocations go through the runtime's `quest_alloc`, 187 more, by the same functions.
2. **The analysis and its dump** (§2): `ssa_escape` marks candidates as kept or removable, without changing them.
   *Done when* the per-pass goldens show each case of §4 classified as intended. *Done* (2026-11-01):
   `questlang/ssa/escape`'s `analyze`, and the questlang test `ssa_escape`.
3. **The transformation** (§3), with the folds. *Done when* the suite passes in every SSA mode, the fixed points
   through `ssac` and `arm64` hold, and the per-pass goldens show the removals. *Done* (2026-11-01): `escape` in
   `questlang/ssa/pipeline` before `promote`, `ssa_escape` showing each function after the pass and after
   promotion, and the behavior test `language/escaping_allocations`.
4. **Measurements:** allocation counts and the suite's times through `ssac` and `arm64`, separate and whole, in
   benchmarks.md, dated. *Done when* benchmarks.md records them against the counts and times before the pass.
5. **The C printer's fixes** (§6), decided from the measurements.
6. **Then** option-values.md's step 3, if the allocations that still escape justify it.

## 6. The C Printer's Fixes

Options as values ([option-values.md](option-values.md)) gave the C printer two specialized forms of this pass, by
pattern rather than analysis, for the statements that make them adjacent:

- **An option made from its payload tuple** (`let t = tuple(...); let o = option(tag, t)`, `t` used once): the
  option stores the tuple's components, and the tuple is not made.
- **`o!tag.field`** (`let p = payload(o, tag); let x = tuple_field(p, i)`, `p` used once): the component is read
  from the option, and the tuple of the ordinal and components is not made.

They took peek from 960 million allocations to 400 million through C. Step 5 tests whether they are still
necessary:

- **Through the SSA:** with the pass, `ssac` and `arm64` should allocate no more than the C printer with its fixes on
  peek, zebra, and ratio-regions. If they allocate more, the pass misses a case the fixes catch, and is extended
  rather than the fixes copied into the SSA builder.
- **Through the C printer:** clang cannot remove a `GC_malloc` it does not know as an allocator, so the C printer
  gains nothing from the SSA's pass. The fixes stay while the C printer is the default backend, and are removed when
  `ssac` replaces it (arm64.md step 15), with that step's comparison including the pass.
- **Their cost:** they were kept (`193a3f11`; [benchmarks.md](benchmarks.md) §8: peek 0.57 of its time without them,
  wc-scanStream 0.71, zebra 0.89). The C printer's output has no goldens, so the behavior tests are all that check
  them.
