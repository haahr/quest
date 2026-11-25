# Optimization Experiments

A notebook of attempts to make compiled Quest faster that did not end in a change, kept so that the next attempt
starts from what the last one found. Each was measured, built and taken back, or designed and set aside; most came from
the plan for closing the median MLton programs' gap (benchmarks.md §38 found the gaps; §40 to §44 measure what was
made). The attempts that succeeded are described where their code is: [ssa.md](ssa.md) §4.1 for the SSA's passes,
[arm64.md](arm64.md) for the backend, [collector.md](collector.md) for the allocation fast path.

Each entry says what was tried or proposed, what it was measured to gain (instructions retired, `tools/perf/counts.py`,
unless it says otherwise), why it went no further, and what would change that. New entries go in the section that
fits, with their date.

## 1. How these were judged

- **The 1% bar.** A change that saves less than 1% of the instructions of every program it was aimed at is not made,
  or is reverted once made. Below that, a count moves with a program's own variation (allocation addresses, hash
  orders), and a loaded machine moves the counts of programs that allocate much by up to 4%.
- **Whole-program-only changes are tabled** (the user, 2026-11-24). Most Quest programs are expected to be built unit
  by unit, so a change that gains only in a whole program leans toward tuning the benchmarks, not the compiler as it is
  used. Such designs are kept here and not built; the whole-program system is still measured, but no change aims at it
  alone.
- **Bytes are not instructions.** Fewer bytes allocated have not given fewer instructions: the nucleic experiment of
  §5.3 allocated 0.90 of its bytes and retired 0.99 to 1.00 of its instructions. A census of bytes bounds a
  representation change's gain but does not show it.
- **Counts are not times either.** Fewer instructions have taken more cycles (benchmarks.md §41: matrix-multiply 1.31
  times as long with 0.93 of the instructions), so whatever is made is also timed.

## 2. Tabled: they gain only in whole programs

### 2.1. Proving where proxies are made

A tuple or option type whose values may be proxies ([runtime-design.md](runtime-design.md) §2.3, `mayBeProxied` in
`repr/layout`) has every read of its tag, payload, or field preceded by a test of the low bit and a cold call. With no
proxy tests at all (a build in which nothing may be a proxy, unsound but exact for programs that make none), through
ssac and arm64: tyan 0.739 and 0.728, logic 0.834 and 0.800, mpuz 0.825 and 0.757, lexgen 0.706 and 0.703 (2026-11-23,
benchmarks.md §40). The tests are 17 to 27% of what tyan, logic, and mpuz retire: the largest single cost of code that
walks lists and trees. Laying the proxy path out of line (arm64.md, cold blocks) took part of it.

Nearly all the tests come from one rule: an option of two or more cases may be a proxy, because its tags number its
cases in the order of their names, and an upcast to a type with more cases renumbers them (an `Option nil end` seen as
a list's `Option cons nil end` has its `nil` move from tag 0 to tag 1), so the upcast makes a proxy. Every list is
such an option.

**The design:** a proxy is made only by a conversion to a supertype (a `view` plan of `ir/represent`), whose target type
the proxy then has, so a value of a type no conversion makes a proxy at is never one. A whole program sees every such
conversion: `whole` runs represent's planning over the unit first, collects the shapes that view plans, `dynamic.be`,
and the runtime's descriptor views (`quest_view_*`) make proxies at, and `mayBeProxied` answers false for every other.
A check mode in which the runtime's proxy constructors abort at a shape the compiler said none is made at, run over the
suite and the tests, guards the proof. Moderate cost, in `ir/represent`, `repr/layout`, and `driver/whole`; no ABI
change.

**Why not:** unit by unit it gains nothing, since a unit cannot see the others' conversions. §3.1 is the only design
that gains unit by unit.

### 2.2. A closure field specialized to the function every construction stores

lexgen's `Dict` holds its comparison `leq` as a field, loaded and called through `blr` in the generic `lookup` and
`enter`. A hand-made lexgen whose `lookup` and `enter` are copied at `String` and at `Int` keys, calling `stringLeq` and
`intLeq` directly, retires 0.907 of the instructions through ssac and 0.936 through arm64 (whole programs at count 48).
The same pattern is in the library: `collections/hashMap` keeps `equal` and `hash` in its `T`, and the sorted maps and
the heap their comparisons. The inliner's specialization ([ir.md](ir.md) §8.6) covers only a self-recursive function's
static parameter passed a known function, not a field.

**The design:**

- **Where:** the self-hosted simplifier, in its rounds on the Core IR, where known functions are inlined and
  polymorphic code is cloned at closed types.
- **Facts** (a new `ir/fieldvalues`): at the start of each round after the first, a walk records, for every tuple made
  with an immutable function-typed component, its label, its value, and the component's type. By then small
  constructors such as `create` are inlined, so the construction is at a closed type. A global function (top-level or
  a module's member) is a known source; a load of the same label adds nothing (the facts are a fixed point, so
  `enter`'s copy of `d.leq` is the fact itself); anything else (a parameter, a local closure, a construction at an open
  type) makes the label unknown. Facts are keyed by label and component type, since tuples are structural: a load whose
  component type is `All(a: String b: String) Bool` sees the constructions with label `leq` whose stored type is a
  subtype of it, `stringLeq` and not `intLeq`.
- **Loads resolved:** a load of such a field at a closed type whose fact is one global function becomes a reference to
  it, so the call is known and the inliner's rules apply. A top-level function's closure is static, so nothing, `is`
  included, can tell.
- **Specialization:** in the generic `lookup` the load's type is open, so as the inliner clones a recursive function
  for a known function argument, it would clone a callee for a call at closed type arguments whose callee loads and
  calls a field of a parameter with a one-function fact at those types. Clones shared and bounded as `specialize`'s are.
- **Soundness:** function-typed fields only, since only the program's code makes closures (not deserialization or
  `dynamic`); `var` fields left out, or each assignment counted as a source; a label an external's type mentions is
  unknown; facts taken after dead-code removal, so that the generic `create` is gone.
- **Limits:** one function per type: two `hashMap`s at one key type with different `equal`s resolve nothing.
- **Gate:** the fact collector first, with a report flag (as `--report-inferable`), counting the loads it would resolve
  over the suite's whole programs and the compiler's own whole build, and those in loops.

**Why not:** every construction must be seen, so whole programs only. A main program's unit could be argued separately
(its structural tuples can come only from imports whose interfaces mention the label, and from `dynamic`), which would
be the way to make it gain unit by unit.

### 2.3. Payload-free cases tested by address

A payload-free case is a constant in each unit's table, so `is` cannot compare addresses across units and a test for
`nil` loads the tag. In a whole program there is one table, so a test for a payload-free case could be the pointer
compared with the constant's address, with no load, where every option of that type the program makes is made by
compiled code (not by `dynamic`, deserialization, or the runtime, which `whole` can see). No layout or ABI change.
About 4 instructions per element of tyan's and lexgen's list walks; not counted further.

**Why not:** whole programs only.

## 3. Waiting for a decision

### 3.1. Tags that no upcast renumbers

The way to §2.1's gain unit by unit: each case's tag is the same in every option type that has it, a 32-bit hash of
its name (with a type's two names that collide numbered apart, and that type keeping today's rule). An upcast then
renumbers nothing, and an option is a proxy only when a payload's components change view.

**Cost:** an ABI change through the runtime (`ordinal`, the payload-free constants' tables, which are indexed by
ordinal and would need a search, `dynamic` and serialization, the barrier's test that a word under 65536 is a tag),
both compilers' C, the SSA builder, and the WebAssembly backend. Every switch on an option's tag would become a search
over sparse constants rather than a jump table (`ssa/passes/tables` needs dense cases), which the compiler itself,
switching over options of 20 to 60 cases, would feel.

**Why not yet:** the user chose neither this nor §2.1 (2026-11-23). The first step, if taken up, is to count what
sparse switches cost, in a hand-made build of the compiler and of the suite, before designing further.

### 3.2. A ref allocated inside its owner

mpuz's `(v, ref false)` is two objects, and reading the flag loads the inner tuple's address first; MLton makes one.
The inner tuple's identity is observable only in ways that sharing an allocation keeps (`is` and `identityHash` use
its own address; a `var` component is shared by whoever holds the tuple), so it could be allocated in its owner's
allocation, as represent already embeds records' and variants' boxes ([c-representation.md](c-representation.md)
§5.1), reached by an interior pointer. When the field is immutable and every owner is made with a fresh inner tuple,
`outer.r.used` becomes one load at a constant offset.

A census of one-word tuples (2026-11-23) found the pattern in bulk only in logic (`Ref`, inside `Term`'s `ref` case:
10.7 million, 3.5% of its bytes) and ratio-regions (`QueueRef`); mpuz makes its ten once per solve but reads them on
every step. The compiler's 16-byte objects are almost all empty arrays. Hand-made variants, whole programs:

| Program | Instructions, arm64 | ssac | Bytes |
|---|--:|--:|--:|
| mpuz (count 32) | 0.940 | 0.896 | |
| logic (count 64) | 0.955 | 0.954 | 0.965 |

**Why not yet:** the suite's conversions now write these as a `var` field of the owner (benchmarks.md §42.1), which
gets the same gain with no compiler change, so no program in the suite has the nested form left. What remains is the
compiler finding the pattern in code written the nested way; the branch `claude/step23-embeds` keeps nested variants
for measuring it. The user to decide.

## 4. Abandoned

### 4.1. The tag in the header, and each case sized to itself

An option's tag would be a property of its case's layout (a case's layouts for one option type consecutive, the tag
computed from the header as `(header & mask) - table` divided by the layout's size), so the object loses its tag word:
a cons cell 24 bytes, as MLton's, rather than 32. Each case's object could then also be its own size, not the largest
case's. A census by layout (`allocations.py --by-layout`, 2026-11-23) gave the bytes saved: 25 to 26% of zebra, tyan,
tailmerge, and DLXSimulator; 19 to 22% of peek, boyer, mlyacc, life, vliw, and model-elimination; 15% of hamlet and
logic; 3.1% of the compiler's own allocation. Sizing each case to itself alone saves about 5% of logic's and
raytrace's bytes, at most 1.5% of any other program's, and 0.6% of the compiler's.

**Why not** (the user, 2026-11-24): the cost is certain and large, the gain uncertain. Every case test that reads a tag
would take four instructions where it takes one; it is the widest change considered (every case's offsets, both
compilers' C, the runtime, the barrier, the arm64, ssac, and JIT backends, proxies, `dynamic`, an ABI bump), and it
needs a table of consecutive layouts per option type, which options made in other units, generically, or by the runtime
make hard to keep. And bytes have not been instructions (§1).

**What would bound it cheaply,** if it comes up again: two throwaway builds, timed: options padded by a word (the
bytes' cost, the inverse of the gain), and every tag read made the four-instruction sequence (the reads' cost).

## 5. Under the bar

### 5.1. String comparisons expanded inline

`precedes` and `equal` expanded in the SSA: `equal` as a same-pointer test, then lengths, then the call; `precedes` by
the first bytes when they differ. lexgen's keys all begin with a space, so the first-byte test never decided and cost
lexgen 9%; the same-pointer test saved logic 0.6% through ssac and 0.3% through arm64. Not kept. What was kept is in the
runtime: `quest_string_precedes` compares up to 16 bytes itself before calling `memcmp`.

### 5.2. Small recursive comparison functions inlined

tyan's `mCompare`, called from `P.plus` and returning a `Relation` the caller cases on, is not inlined because it is
self-recursive, and the simplifier inlines a recursive function only when a static parameter is passed a known
function. Inlining it usefully would need two transformations the simplifier lacks: copying a recursive callee into
its caller as a local loop, and case-of-case (a switch on a join's parameter pushed into the jumps that pass it a known
constant). Hand-made tyans bound the gain (whole programs, count 12):

| Variant | ssac | arm64 |
|---|--:|--:|
| `mCompare` returns an Int, which `plus` and `minus` test with `if` | 0.982 | 0.994 |
| the comparison's loop written into `plus` and `minus` | 0.956 | 1.015 |

**Why not:** under 2% for the `Relation`, at most 4.4% for the call through ssac and nothing through arm64, below what
the two transformations would cost to build.

### 5.3. Large tuple results returned in registers

nucleic's `tfoCombine` allocates its 12-real result. Unboxed results take one or two components, each an Int, Bool,
Char, or String, and workers, which would widen that, are not built ([inlining.md](inlining.md) §2). A hand-made nucleic
with the three calls in `dgfBase` fused, so that only the stored `Tfo` is allocated, allocated 0.903 of the bytes but
retired 0.987 of the instructions through ssac and 1.004 through arm64 (whole programs, count 128), where 24 live Reals
spill. **Why not:** under the bar on arm64.

### 5.4. Conjunctions as `ccmp`

A conjunction of comparisons that feeds only a branch, as `ccmp` and one branch rather than `cset`s and an `orr`.
§38 counted 1,563 `cset`/`csel` in logic through arm64; after the later changes it has 608, mostly in cold code, and
its five hottest functions (about 90% of its samples) hold one or two each among 150 to 600 instructions (2026-11-24).
**Why not:** under 1% of logic.

### 5.5. Induction variables strength-reduced, and indices that step together merged

`base + i * 8` for an induction variable `i` as a pointer stepping by 8, and tensor's two or three indices that each
step by one merged into one with offsets. Merged indices are worth at most about 3% of tensor alone (benchmarks.md
§42.3's hand-written loops, which merged them and more), whose index checks stay since the indices' ranges are not
known. Strength reduction trades a multiply for an add where the index is still needed for its bounds check, and arm64
folds the scaling into the address already. **Why not:** not worth building for one program's 3%.

### 5.6. A loop's unread entry parameters left out

A self-recursive loop that passes a static closure it does not read (`mov x12, #0; mov x20, x0; mov x0, x12`): leaving
the entry's unread parameters out of block 0 saved under 1%. Not kept. `ssa/passes/loops` now drops the block
parameters promotion leaves unused, which covers the loops it makes.

### 5.7. Tried in `ssa/passes/loops` and not kept

- **One header for two or more self tail calls:** they are usually nested loops in one function (zern's `lp2`, into
  which `lp1` is inlined), and one header merged them into a shape clang no longer split: 1.09 of zern's ssac
  instructions. Such functions are left to the backends.
- **Immutable globals' loads marked invariant in every function,** for value numbering: tailmerge and hamlet took 1 to
  5% more (longer live ranges). The cell promotion reads a global's load as a base itself instead.
- **Loops rotated for ssac:** clang rotates loops itself, and one rotated before it can compile worse (fib 1.20), so
  rotation of loops with no checks to move is arm64 only.
- **A block merged into its one predecessor that jumps to it,** so that a header's test ends it: tensor 1.04, nothing
  helped.

## 6. Not started

- **The start bitmap built at collection.** The allocation fast path sets the object's start bit
  ([collector.md](collector.md) §3.4); instead the collector could walk the objects allocated since the last collection
  and set their bits then, so the allocation sets none. It needs every allocation, the runtime's included, to leave a
  parsable region, a collector change first. The fast path was made cheaper instead (the flags folded into the limit,
  the bit's byte one global away), which left the bit a few instructions; the user's rule is to take this only if the
  bit is still a large part of the path and the walk looks meaningfully cheaper.
- **Cursor and limit loaded as a pair** (one `ldp` from one address), part of the same fast-path work, not done.
- **The WebAssembly allocator's flags folded into its limit,** as the native one's are; not done.
- **Values live only across a cold call saved only on its path:** `tfoCombine`'s reals are stored and reloaded around
  `quest_gc_alloc_slow` on the fast path; the spill code could move to the cold block. Not measured.

## 7. Observed, not taken apart

- **A `while` on a `var` flag through arm64:** mandelbrot's inner loop written that way retired 1.25 times the
  recursive version's instructions through arm64, though 0.88 through ssac (benchmarks.md §42.3, before the loops pass
  rotated loops). Not a cost of the recursive form the suite uses, but of Quest's own loops; to be counted again.
- **imp-for through arm64** retires 324 times ssac's instructions: clang computes the nest's result without looping,
  as it does fib's (benchmarks.md §2.3). Not a cost the compiler should chase.
