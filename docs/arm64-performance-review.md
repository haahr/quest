# Why arm64's Code Is Slower Than clang's: A Review

Why programs compiled by the arm64 backend run slower than the same programs compiled through C by clang: what the
generated machine code does that clang's does not, and what in the back end (`questlang/ssa`,
`questlang/codegen/arm64`, `questlang/codegen/regalloc`) makes it do so. Every time here is a compiled program's run
time, on the six benchmarks near the median (life, ray, hamlet, mlyacc, zebra, nucleic), at `6f7cb100` (options as
values, and the traceback cache); none is the compiler's own. [arm64.md](arm64.md) §6 records what was found and done
before this; this review starts again from the measurements, and some of its conclusions revise §6's.

## 1. Summary

Programs compiled by arm64 run 1.2 to 1.95 times as long as the same programs compiled by the C backend. The gap in
run time is the product of two factors:

- **The SSA, compiled by clang (`ssac`), against the C backend:** 1.00 to 1.04 for four of the six, but 1.34 for
  hamlet and 1.58 for zebra. That part is in the SSA's builder, not the code generator: the C printer reads and
  builds options' payloads in place, and the SSA's builder does not (zebra allocates 4.76 GB through the SSA, 2.75 GB
  through C).
- **arm64 against clang on the same SSA:** 1.18 to 1.54. That part is the code generator.

The generated code loses its run time to six things, in order of what they cost. None is a single missing pass.
Each comes from a design choice that is reasonable for a first native backend but that LLVM made differently, and
for reasons that apply here.

1. **Spill decisions that ignore how often code runs.** Linear scan spills whatever has the furthest next use. It
   neither knows nor cares that one use is in a loop and the other is not, and a value live across a call on a cold
   path is treated as if it crossed a call on every path. In life's hottest loop, the list cursor goes through a
   stack slot on every iteration, a store-to-load round trip on the loop-carried dependence chain. clang keeps it in
   a register.
2. **Dead values left in spill slots, in a program scanned by a conservative collector.** Every spilled value has its
   own slot for the life of the frame, and keeps it after it dies. In mlyacc, `main`'s frame is 7.7 KB (clang's: 1 KB),
   and at a collection 519 to 717 of its words point into the heap (clang's: about 80). The collector keeps all of them
   alive: mlyacc's live pointer data is 2.6 MB rather than 0.75 MB, and marking takes 570 ms rather than 271 ms. That is
   about half of mlyacc's code-generation gap, and no LLVM-style measurement would have found it, because it costs
   nothing in the function where the slots are.
3. **Block layout in the builder's order.** Every check (a bounds check, a NaN check, an option's tag) puts its
   cold raising block between the check and the code that follows it. The hot path therefore jumps over the cold
   block every time: a taken unconditional branch per check. ray's `psRaytrace` has 193 `b`s to clang's 25.
4. **No redundancy elimination on the SSA.** No value numbering, no load elimination, no hoisting. nucleic's
   `tfoCombine` loads each field of its two matrices four times, and clang loads each once. The fields are
   immutable, a fact Quest knows and LLVM has to prove.
5. **Instruction selection by expansion, one SSA instruction at a time.** No `ldp`/`stp` outside prologues (clang:
   300 to 11,000 per program), no register-offset or shifted addressing (clang: 66 to 388), `adrp`, `add`, `ldr`
   for every global (406 to 1,072 per program; clang folds the `add`), a `Bool` result masked again after every
   call, a `ldr` then a `mov` where one `ldr` would do (136 to 3,588), and real constants built in four `mov`s and
   an `fmov`. In total, 1.2 to 1.75 times clang's instructions for the same SSA.
6. **Unwind information the linker cannot compact.** The prologue stores each callee-saved pair in the opposite
   order to the one Darwin's compact unwind format requires, so every function that saves a callee-saved register
   (372 of zebra's) falls back to DWARF CFI. Each frame a raise walks through then has libunwind parse an FDE:
   zebra spends 121 samples in libunwind to clang's none.

What does not explain the gap: instruction count in memory-bound loops (life's `member` loop costs arm64 what it
costs clang, with 1.3 times the instructions); clang's inlining of Quest's own functions, once Quest's inliner has
run (0 to 9 percent, mlyacc the most); and, as §6.2 of arm64.md found, vectorization and unrolling.

## 2. The measurements

### 2.1. How they were taken

Each benchmark was built `--whole-program` by stage 2 at `6f7cb100` with each backend: `c`; `ssac` (the SSA printed
as C, compiled by clang `-O2`); and `arm64`. For the experiments in §2.3, ssac's C was also rebuilt by hand. Times are
user time, the least of three alternating rounds. The load average was falling from a peak of about 40 to about 6
while they ran, so differences under about 5 percent are noise.

The tools, and how to use them, are in [profiling.md](profiling.md): `tools/perf/variants.py` builds the three
variants, `timeit.py` times them, `profile.py` samples the program counter (macOS's `sample` attributes time only to
functions, and Instruments needs Xcode) and attributes the samples to symbols and instructions, `asmstats.py`
compares the instruction mix, and `gcstats.py` summarizes the collector's statistics. A process migrates between
performance and efficiency cores, so the profiles are used to see *where* time goes within a function, never to
compare totals between runs. Frames and stack contents at a collection are from lldb, with a breakpoint on
`GC_stopped_mark` (profiling.md §6).

### 2.2. The two factors

Seconds, and each one's time over C's:

| Benchmark | C | ssac | arm64 | ssac / C | arm64 / ssac | arm64 / C |
|---|--:|--:|--:|--:|--:|--:|
| life | 1.58 | 1.60 | 2.47 | 1.01 | **1.54** | 1.57 |
| ray | 1.97 | 2.04 | 2.40 | 1.04 | 1.18 | 1.22 |
| hamlet | 1.28 | 1.71 | 2.05 | **1.34** | 1.20 | 1.61 |
| mlyacc | 1.61 | 1.66 | 2.36 | 1.03 | **1.42** | 1.47 |
| zebra | 1.47 | 2.32 | 2.86 | **1.58** | 1.23 | 1.95 |
| nucleic | 1.78 | 1.77 | 2.13 | 0.99 | 1.20 | 1.20 |

### 2.3. Experiments

- **clang's inlining of Quest's functions.** Every `qf_` and `qv_` function in ssac's C marked `noinline`: life
  1.02, ray 1.06, hamlet 1.41, mlyacc 1.12, zebra 1.55, nucleic 1.01 (each over C, against ssac's 1.01, 1.04, 1.34,
  1.03, 1.58, 0.99). So clang's inlining is worth at most 9 percent (mlyacc), and it is not why arm64 is slower.
  life's `qf_f_5`, the loop of `member`, which clang inlines into `qf_nthgen` and arm64 calls, kept out of line
  alone: 1.01.
- **The collector, per program** (collections, marking time, bytes freed):

  | Program | C | ssac | arm64 |
  |---|---|---|---|
  | life | 1679, 92 ms, 3.58 GB | 1679, 93 ms, 3.58 GB | 1695, 109 ms, 3.58 GB |
  | hamlet | 146, 287 ms, 3.15 GB | 102, 334 ms, 3.36 GB | 134, 332 ms, 3.40 GB |
  | mlyacc | 275, 131 ms, 4.32 GB | 608, 266 ms, 4.38 GB | 312, **570 ms**, 4.37 GB |
  | zebra | 1293, 85 ms, **2.75 GB** | 2253, 173 ms, 4.76 GB | 2244, 160 ms, 4.76 GB |

  ssac and arm64 run the same SSA, so they allocate the same. They differ only in what the collector finds alive,
  and in mlyacc that differs by a factor of 3.5 (§3.2).

## 3. Findings

### 3.1. Spill decisions that ignore frequency

**What happens.** In life, `qf_nthgen` (the generation step, with `occurs3`'s `member` loops inlined into it) takes
513 samples under arm64 and 283 under clang, with `qf_f_5` (the loop of `member` that neither inlines here) the same
in both. Its instruction mix, arm64 against clang:

| | clang | arm64 |
|---|--:|--:|
| instructions | 685 | 944 |
| loads from the stack | 7 | 74 |
| stores to the stack | 7 | 66 |
| unconditional branches | 56 | 138 |
| register moves | 158 | 206 |

The hottest instructions are in an inlined `member` loop. Its body under arm64:

```
loop:  tbz   w12, #0, 1f            ; the cursor a proxy?
       ...                          ; (quest_proxy_tag, cold)
1:     ldr   x13, [x12]             ; the cell's tag
       mov   x0, x13
       cbnz  x0, done
       ldr   x12, [sp, #0x108]      ; the cursor again, from its slot   <- 42 samples
       tbnz  w12, #0, proxy
       b     2f
2:     add   x13, x12, #8           ; the payload
       mov   x12, x13
       str   x13, [sp, #0xb0]       ; stored: live across a cold call
       tbz   w12, #0, 3f
       ...
3:     ldr   x13, [x12]
       mov   x0, x13
       ldr   x12, [x28]  ;  ldr x13, [x0]  ;  ldr x14, [x28, #8]  ;  ldr x15, [x0, #8]
       cmp   x12, x13  ;  ccmp x14, x15, #0, eq  ;  b.ne next
       ...
next:  ldr   x0, [sp, #0xb0]        ; the payload, back from its slot   <- 146 samples
       tbz   w0, #0, 4f
       ...                          ; (quest_proxy_element, cold)
4:     ldr   x12, [x0, #8]          ; the tail
       mov   x0, x12
       mov   x12, x0
       str   x0, [sp, #0x108]       ; the cursor, to its slot
       b     loop
```

clang's, from the same SSA, has eleven instructions on the hot path, the cursor in `x28` throughout, the payload
address made by a post-indexed load (`ldr x8, [x28], #8`), and the pair compared with two `ldp`s:

```
loop:  ldr   x8, [x28], #8
       cbnz  x8, done
       tbnz  w28, #0, proxy
       ldr   x0, [x28]
       ldp   x8, x9, [x27]
       ldp   x10, x11, [x0]
       cmp   x8, x10  ;  ccmp x9, x11, #0, eq  ;  b.eq found
       tbnz  w28, #0, proxy2
       ldr   x28, [x28, #8]
       tbnz  w28, #0, proxy3
       b     loop
```

The extra instructions cost little: the loop is a chain of dependent loads, and the machine has width to spare. The
slots are what cost: the cursor and the payload go through memory on the chain itself. The samples pile up on the
loads of what was just stored (146 and 42), most likely waiting on store-to-load forwarding.

**Why.** The payload is live across `quest_proxy_element`, which is called only when the list cell is a proxy. The
allocator (`regalloc.mod.quest`) makes caller-saved registers unavailable "from just after a call the interval is
live across", so the payload needs a callee-saved register. All ten are held by `nthgen`'s longer-lived values.
Linear scan then spills by "next use furthest away", so the loop's own value loses to values that are used next
outside the loop, and are therefore further away but run once.

**What LLVM does.** The greedy allocator weights each use by its block's frequency, so a value used in a loop is
hard to spill and one used outside it is cheap. Before spilling, it splits: region splitting (`SplitKit`, with
`SpillPlacement` choosing the split points over edge bundles) gives a value a register through the hot region and
spills it only around the cold call. A copy or a reload happens on the cold path, where the call costs more anyway.

**Recommendation.** Give the allocator a static frequency per block, and use it in two places:

- **Static frequency.** Each loop level multiplies by 8 or 10. A block that can only reach an `unreachable` (a check's
  raising block, which the builder already marks by terminator) or a proxy's slow path is cold, at 1/1000. The
  builder knows which branches lead to proxies and raises. `ssa/cfg` has the loops, and the allocator's numbering
  already lays blocks out in reverse postorder.
- **Spill choice.** Choose the interval to spill by the sum of its uses' and definitions' frequencies, divided by
  its length, rather than by its next use. LLVM's `VirtRegAuxInfo` computes this weight.
- **Calls.** Treat a call in a cold block as clobbering a caller-saved register only there: split the interval at
  the cold block's entry, store it there, and reload it on the way out, so that the hot path keeps it in a
  caller-saved register. This matters most here because every proxy check puts a call on a cold path beside nearly
  every load of an option or a tuple.

Expected: most of life's 1.54, and part of mlyacc's. This is the largest single item, and it is not coalescing, which
§6.3's item 3 tried. Coalescing lengthens intervals in a function already short of registers. Splitting by frequency
shortens them where it matters.

### 3.2. Dead values in spill slots, under a conservative collector

**What happens.** At collections during a run of mlyacc, under arm64 against clang:

| | clang | arm64 |
|---|--:|--:|
| `main`'s frame | 1,040 bytes | 7,696 bytes |
| words in it pointing into the collector's heap | 78 to 81 | 519 to 717 |
| live pointer data, median over the run | 0.75 MB | 2.6 MB |
| heap | 8.7 MB | 17.4 MB |
| marking time, whole run | 271 ms | 570 ms |

With one iteration rather than 100, arm64's median is already 1.4 MB, against clang's 0.71 MB. The retention is
within an iteration, not only of the previous one. The other frames on the stack are the same size in both
(`qf_foldr`, 64 bytes each; `qf_f_58`, 80 against 96).

**Why.** `codegen.compile` gives every virtual register that needs a slot a slot of its own
(`spillAt[v] := at; at := at + 8`). mlyacc's whole program, its top level and the benchmark's loop, is `main` after
inlining, so `main` has about 950 slots. Each is written once, when its value is defined, and never again. A value
dead for the rest of the run stays in its slot, and the collector, which scans the stack conservatively, keeps
whatever it points to. clang shares slots between intervals that do not overlap (`StackSlotColoring`) and keeps most
values in registers, which later values overwrite.

**The constraint.** A precise collector would scan only the slots its maps say hold live pointers. A conservative
one scans every word of every frame, so in this backend a dead pointer in the frame of a long-running function is a
leak, a constraint LLVM's code generators do not have. What is meant is that a slot whose value is dead holds no
pointer wherever the collector can look. Sharing slots, as clang does, has that effect only by accident: a dead
value stays until something else happens to be given its slot. So the fix is to clear slots explicitly, and sharing
is a separate matter, of frame size.

**Recommendation.**

- **Clear the slots of dead pointers** (3a). Where a spilled value of a type that may be a pointer (`typePtr`,
  `typeVal`) stops being live, store zero to its slot: after its last use in a block, or at the start of a
  successor it is live out of the block into, but not live into the successor. The allocator's liveness has both. A
  collection can happen only in a call (an allocation is a call, and a program has one thread), so a clear is needed
  only where a call can follow before the slot is written again or the function returns, which a backward walk over
  the positions finds. That keeps clears out of most loops and puts them where they matter, as in mlyacc's `main`.
  A clear costs at most one store per spilled pointer per path, no more than the store that spilled it, and usually
  none. Integers and reals keep nothing alive, and are never cleared.
- **Then share slots, by class** (3b): one pool for values that may be pointers, one for the rest, each a slot free
  again once the interval in it has ended, so that the frame holds the most values spilled at once rather than every
  value ever spilled. With 3a in place, sharing need not be right about retention, only about frame size. Keeping
  the classes apart gives each slot one kind for its whole life, which a precise collector could describe with one
  map per function, given 3a's clears.

**What remains.**

- **Slots not yet written.** A slot holds whatever an earlier frame left at its address until its value is
  defined, and neither clearing nor sharing changes that. Zeroing a frame's pointer slots in its prologue would, as
  Go's compiler does for slots whose liveness it cannot tell, at a cost to every call. It is to be measured before it
  is done: mlyacc's retention was of slots `main` had written itself.
- **Dead pointers in callee-saved registers,** which a callee saves into its frame, are roots too. clang's code has
  the same property and mlyacc does well under it, so this is second order; the liveness 3a uses could clear them as
  well.
- **A precise collector** would need more than this: maps of the live pointers at each call, for slots and for the
  callee-saved registers a frame holds, a collector that recognizes proxies' tagged pointers, and, for the backends
  that compile through C, a shadow stack, since clang emits no such maps for ordinary C. Neither 3a nor 3b stands in
  its way, and 3a's liveness of pointers at calls is what those maps would be made from.

Expected: 3a, about half of mlyacc's code-generation factor (300 of its 700 ms over ssac are marking), for a few
stores on paths that call. 3b, smaller frames everywhere, at no cost in code: the same loads and stores at
different offsets.

### 3.3. Block layout

**What happens.** The emitted order is the order in which the SSA's builder made the blocks, plus each branch edge's
block after its source (`select.mod.quest`: `layout`). `values.check` makes the good block and the bad block together
(`let good = ssa.newBlock(...)`, `let bad = ...`), the bad one is laid out after the code that continues from the
good one, and so each check's raise sits between one check and the next. nucleic's `tfoApply`, a straight line of
real arithmetic:

```
       fmul  d16, d16, d17
       fcmp  d16, d16
       b.vs  raise1
       ldr   d17, [x2, #8]  ;  ldr d18, [x1, #0x18]  ;  fmul d17, d17, d18
       fcmp  d17, d17
       b.vs  raise2
       b     next                   ; taken, every time
raise1:
       adrp  x0, site@PAGE  ;  add x0, x0, site@PAGEOFF
       bl    _quest_raise_real_error_at
       brk   #1
next:  fadd  d16, d16, d17
       ...
```

clang's, from the same SSA, is the arithmetic and the `b.vs`s with nothing between them, its raising blocks at the
end of the function. Unconditional branches, arm64 against clang: life 1,155 against 527, hamlet 13,333 against
4,616, mlyacc 6,247 against 2,538; in single functions, ray's `psRaytrace` 193 against 25, and `tfoApply` 17
against 0.

**Why it matters more than arm64.md §6.2 measured.** That section found `llc` without block placement 4 to 7 percent
slower. But `llc` without `MachineBlockPlacement` still keeps the order its IR passes chose, and clang's front end and
`SimplifyCFG` had already sunk the cold blocks. A taken branch per check splits the fetch stream on each check. In
check-dense code (real arithmetic, array loops) that is a bubble per operation.

**Recommendation.** Two steps, the first nearly free:

1. **Cold blocks last.** Move every block that ends in `unreachable` (a check's raise, `brk`), with the blocks only
   it reaches, to the end of the function, in their order. The branch inversion item 2 added then turns each
   check into one not-taken `b.cond`.
2. **Chains.** Lay out by chains: for each block, the successor that is hot (not cold, in the same loop) and not yet
   placed follows it, and a loop whose header tests is rotated so that the test is at its bottom. This is the
   Pettis–Hansen approach, with §3.1's static frequencies. It also removes the `tbnz w1, #0, X; b Y` pairs, where
   neither successor follows.

Expected: most of ray's and nucleic's 1.18 to 1.20, a few percent elsewhere. Do the first step before measuring the
second.

### 3.4. No redundancy elimination on the SSA

**What happens.** nucleic's `tfoCombine` (benchmarks/mlton/nucleic.quest line 94) multiplies two 4 by 3 matrices
held in tuples: `a.a ** b.a`, `a.a ** b.b`, `a.a ** b.c`, and so on. Each field is read 3 or 4 times. arm64 loads
each of `[x2]`, `[x2, #8]` ... four times (84 loads), and clang loads each once (31). The SSA's pipeline is
`promote` and `tailCalls` (`ssa/pipeline.mod.quest`). Nothing in the compiler, on the IR or the SSA, does common
subexpression elimination, value numbering, or loop-invariant code motion.

**Why Quest can do this cheaply.** A load of an immutable field is a function of its address alone. No store can
change it, so value numbering it needs no alias analysis, a fact LLVM has to infer (or be told, with
`!invariant.load`) and usually only half infers after inlining. The same holds for an array's length and a string's,
and for a descriptor's fields. The builder knows which loads are of immutable memory when it makes them.

**Recommendation.** Dominator-tree value numbering on the SSA, scoped by the dominator tree (in the manner of
Briggs, Cooper, and Simpson). Keys: pure arithmetic and comparisons, addresses, and loads the builder marks as
immutable. Then loop-invariant hoisting of the same, where the loop's preheader dominates every exit. That condition
keeps a load from moving above its null or proxy check. This is the "copy propagation, constant folding, dead code
elimination, value numbering" of arm64.md §6.3 item 5, which ranked it after the allocator because LLVM's
equivalents gained 3 to 5 percent there. But that measured LLVM's IR passes with `llc`'s selection-DAG combining
and `MachineCSE` still running, which recover part of the same redundancy. Here nothing does, so the gain should be
larger, and it serves `ssac` too.

### 3.5. Instruction selection

**What happens.** `select.mod.quest` expands each SSA instruction on its own, folding only an immediate, a
comparison into its branch, a one-bit test, a two-comparison conjunction, and a constant offset into an address.
Over every Quest function in each binary, arm64 against clang:

| Pattern | life | hamlet | zebra | mlyacc | nucleic | ray |
|---|--:|--:|--:|--:|--:|--:|
| instructions | 15,272 / 11,687 | 233,356 / 145,904 | 24,056 / 30,187 | 93,202 / 63,394 | 52,816 / 30,067 | 21,587 / 18,291 |
| `ldp`/`stp` outside the frame | 0 / 393 | 0 / 11,460 | 0 / 303 | 0 / 4,679 | 0 / 1,551 | 0 / 361 |
| register-offset or shifted operands | 0 / 66 | 0 / 388 | 0 / 68 | 0 / 165 | 0 / 70 | 0 / 105 |
| `adrp`, `add`, `ldr [x]` (global) | 406 / 1 | 1,072 / 28 | 562 / 43 | 897 / 1 | 379 / 1 | 551 / 3 |
| `ldr x, ...; mov y, x` | 136 / 4 | 3,588 / 30 | 515 / 3 | 1,899 / 18 | 151 / 1 | 228 / 1 |
| `and x, x0, #0xff` after a call | 44 / 1 | 129 / 1 | 42 / 1 | 107 / 1 | 41 / 1 | 92 / 1 |
| real constant through an x register | 8 / 2 | 8 / 2 | 8 / 2 | 8 / 2 | 5,202 / 15 | 39 / 7 |

(zebra's ssac has more instructions, probably because clang inlines more there.)

None of these is large alone, and §3.1's loop shows that extra instructions are often free. Together they are the
1.2 to 1.75 times the instructions, and they hold registers that §3.1 is short of. In order of what they buy:

- **`ldr` then `mov`.** A value loaded and then moved into the register of the block parameter (a `choose`'s
  result) or of an argument. The allocator gives the load's virtual register a scratch register and the join another.
  Hints from a move's destination back to the definition that feeds it would remove most of them. This is the case
  §6.3's hint-following attempt targeted. It did not pay alone, but it frees registers for §3.1.
- **Pairs.** A post-allocation pass that merges adjacent loads or stores of consecutive words off one base into
  `ldp`/`stp`, as `AArch64LoadStoreOptimizer` does, and post-indexed forms where the base is then incremented.
  Tuples, list cells, and options are pairs of words, so this is common in every program here.
- **Addresses.** `ldr x, [base, index, lsl #3]` for an array element, rather than `lsl`, `add`, and `ldr`; and a
  global's load as `adrp` then `ldr x, [x, sym@PAGEOFF]`, without the `add`. Since options as values, `nil` is
  such a global (`g_nil_2` in life, loaded this way at each use in `nthgen`'s loops).
- **Narrow results.** The SSA extends a C `bool` or `char` result after every call (ssa.md §2.2), even from a Quest
  function, which returns 0 or 1. arm64.md §6.4's Quest calling convention would remove it; a cheaper first step is
  to skip the extension when the callee is known to be Quest's.
- **Real constants.** A literal-pool `ldr d` or `fmov d, #imm` rather than four `mov`s and an `fmov` (nucleic's
  tables).

A pattern matcher over the SSA's single-use values, a tree at a time, is the conventional structure for the first
four. The selector already has `uses` and `defs` for its fusions, so it would extend what is there rather than
replace it.

### 3.6. Unwind information

**What happens.** In zebra under arm64, 121 samples are in libunwind (`CFI_Parser::parseFDEInstructions` and its
callers), and under clang none: zebra raises and catches constantly, and each raise that may be caught walks the
stack. In zebra's arm64 binary, 372 entries of `__unwind_info` are `UNWIND_ARM64_MODE_DWARF` (encoding `0x03...`),
pointing into an 18 KB `__eh_frame`; clang's binary has no DWARF entries and no `__eh_frame`.

**Why.** Darwin's compact encoding of a frame (`UNWIND_ARM64_MODE_FRAME`) describes callee-saved pairs at fixed
places below the frame record, `x19` at `fp - 8` and `x20` at `fp - 16`, then `x21` and `x22` below them, and so
on, as clang stores them: `stp x20, x19, [sp, #-32]!`. arm64's prologue stores `stp x19, x20` (`codegen.prologue`),
with `x19` at `fp - 16`. The assembler can only describe that with DWARF, so every function that saves a pair gets an
FDE, which libunwind interprets at every step. (arm64.md §3.10 says that the assembler and linker make compact
entries; they do only for functions that save nothing.)

**Recommendation.** Store each pair in the other order (`stp x20, x19`, `stp x22, x21`, ...; `d9, d8` likewise),
keeping the order of the pairs, then check `objdump --unwind-info` for no `0x03` encodings in Quest functions. This
changes no instruction count, shrinks the binary, and speeds every raise that walks frames, and the stack-overflow
handler's backtrace.

### 3.7. Outside the code generator

- **The SSA's builder lags the C printer** on options' payloads (escape-analysis.md §6, benchmarks.md §8): zebra
  allocates 73 percent more through the SSA, hamlet 7 percent. This is all of zebra's and hamlet's ssac-over-C
  factor (1.58, 1.34). It is not code generation, but it is the largest single factor in zebra's arm64/C ratio, and
  both backends that use the SSA pay it.
- **Quest's inliner leaves loops alone.** clang inlines hamlet's `strCompare` everywhere (no call to it remains),
  and arm64 calls it from 66 places. By §2.3 this is worth up to 9 percent, so it comes after everything above.

## 4. Recommendations, in order

| | Change | Where | Lines | Checks | Expected |
|---|---|---|--:|--:|---|
| 1 | Pairs stored in compact unwind's order | `codegen.prologue`, `restore` | 10 | 1 | raise-heavy programs (zebra) |
| 2 | Cold blocks last | `select` (`layout`), or after it | 10 to 100 | 1 to 2 | ray, nucleic: most of 1.2 |
| 3a | Dead pointers' spill slots cleared | `regalloc.rewrite`, from its liveness | 100 | 2 | mlyacc: about half of 1.42 |
| 3b | Spill slots shared, pointers apart from the rest | `codegen.compile`, what `regalloc` exposes | 100 | 1 to 2 | smaller frames |
| 4a | Static block frequencies; spill weights by frequency | `codegen` (from `ssa/cfg`), `regalloc` | 100 | 1 to 2 | part of life's 1.54 |
| 4b | Splitting around cold calls | `regalloc` | 100 to 1,000 | 2 to 4 | the rest of life's; mlyacc |
| 5 | Value numbering and hoisting of pure values and immutable loads | a new `ssa` pass; `ssa/build` | 100 to 1,000 | 2 to 4 | nucleic; every program; ssac too |
| 6 | `ldp`/`stp` and post-index; register-offset addresses; `adrp` + `ldr`; no re-extension | `select`, a post-allocation pass | 100 each | 1 to 2 each | a few percent each |
| 7 | Chain layout and loop rotation | after 2, with 4a's frequencies | 100 | 1 to 2 | a few percent |
| 8 | Options' payloads in the SSA, as in the C printer | escape-analysis.md (in progress) | — | — | zebra 1.58, hamlet 1.34 (ssac and arm64) |

**Lines** is the order of magnitude of the compiler's (and runtime's) lines added and removed, not counting tests and
goldens. **Checks** is how many runs of `tools/check` the change should take to push: one when it is right the first
time, more for each fix a run finds. Each run of every suite takes about 30 minutes, which is most of the time a
change takes. They are estimates from comparable commits:

- §6.3's item 1 (`c5aa1ab0`, helpers expanded in the builder): 145 lines; item 2 (`ccd9e7eb`, four selection
  patterns and branch inversion): 378, about 100 a pattern. The traceback cache (`3fc7b821`): 20. Items 1 and 2
  were checked together, in two or three runs of `tools/check` (one spoiled by an edit made while it ran).
- The allocator's interval splitting (`b75ee0fa`, arm64 step 11): 947 lines; linear scan itself (`70b4d698`): 497;
  moving it onto machine functions (`ba4150c3`): 1,762. §6.3's coalescing trial, not kept: about 200.
- The C printer's payload fixes (`193a3f11`): 211.
- `ssa/cfg` already has the dominator tree and loop depths, so 4a's frequencies are little more than loop depth and
  a walk for blocks that only reach `unreachable`, plus the use of them in the spill choice. Item 5 needs the
  builder to mark loads of immutable memory, which is in `ssa/build`, where escape analysis is being written.

To check the estimates, each item's commit should record its actual lines (`git show --numstat`, without `tests/`
and `.out` files) and its runs of `tools/check` here, beside the estimate.

| | Lines, actual | Checks, actual | Commit |
|---|--:|--:|---|
| 1 | 19 | 1, with 2 and 3a | `e7b7e44b` |
| 2 | 59 | 1, with 1 and 3a | `ee258b96` |
| 3a | 143 | 1, with 1 and 2 | `33b8e719` |
| 3b | 147 | 1, with 4a and the fixes | `914aec10` |
| 4a | 352 | 1, with 3b and the fixes | `ba0f9a4b` |
| 4b | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |

The first batch (items 1, 2, and 3a, 2026-11-01) passed `tools/check` in one run of every suite (40 minutes, since it
changes tests' goldens, which the self-hosted compiler's suites alone do not cover). Its estimates held: each item
within its order of magnitude, and one run against the one to five estimated. Two of its results differ from what
§3 predicted. Item 1's gain on zebra (0.89 of its time, measured before `418db1c2`) is mostly gone, since that
commit walks a raise's frames by the frame-pointer chain rather than libunwind; it still removes DWARF unwind
information from every binary. Item 3a cleared `main`'s frame (90 to 126 heap pointers at a collection, against 519
to 717 before and clang's 78 to 81), but mlyacc's median live data fell only from 2.6 MB to 2.0 MB, against clang's
0.77: what else keeps the rest alive (slots not yet written, callee-saved registers, or something not yet seen) is
open. Timings were taken on a machine loaded by other suites and are to be taken again.

The second batch (items 3b and 4a, 2026-11-01) came with three fixes that measuring it found, each a commit of its
own: a value dying as a jump's argument was never cleared, since the test of whether a call may follow looked only
at the instructions after the jump, of which there are none (`8ecaaf2c`, 25 lines); a loop header's parameter that
nothing reads, in memory because the header had more parameters than registers, was stored by the back edge every
time round and never cleared, since it dies at no read (`cb3757ed`, 11 lines); and raising blocks cleared slots
just before raising (`2df9f23c`, 10 lines). They were found with `tools/perf/retention.py` and the backend's
`QUEST_LIVE_SLOTS=1` annotations (`8f692304`, 86 lines of compiler and 272 of tools; docs/profiling.md section 6),
after the collector's own statistics proved misleading: it collects at different points in each build and run.
Clearing dead values' callee-saved registers was tried and not kept: it changed mlyacc's live data by under 1%. 4a's
estimate was low (352 lines against 100), a third of it moving definitions above their first use. Results against the
C backend, five rounds, at a load of 2 to 22: life 1.33 (1.55 with 3b alone), mlyacc 1.29 (1.34), nucleic 1.13
(1.14), ray 1.14, zebra 1.87, hamlet 1.00 of 3b's. mlyacc's median live data at forced collections is 1.31 MB, against
1.48 MB with 3b alone and 0.73 MB under C; `main`'s frame holds no dead pointers at the points checked, and what keeps
the rest alive (perhaps callee-saved registers saved by deeper frames) is open. In life's `qf_nthgen`, 4a takes
the stack loads from 74 to 34 and the stores from 116 to 59 (clang: 7 and 7).

Items 1 to 3 are small, independent, and each fixes something measured above; do them first and measure (3a
before 3b, so that each is measured alone). Item 4 is
the one that closes the most of the gap and is the most work. It changes the allocator's core heuristic, so it
should come with the `regalloc_scan` tests extended to loops with cold calls. Its first half is small and useful
alone. Measure it, and a narrower alternative to the second half, before writing the second half: proxy helpers
called through stubs that preserve the caller-saved registers, as LLVM's `preserve_most` convention does, since
proxy calls are most of the cold calls hot values are live across. Item 5 is the first optimization pass the SSA
would have, and it would help `ssac` too. Item 8 is the largest factor for zebra and hamlet, but it is outside the
code generator, and escape-analysis.md is its plan.

Each is to be measured as benchmarks.md measures (`run.py time --clean`), and the six here against `ssac` with
`tools/perf/timeit.py`. The figures above will move: §3.1's and §3.2's interact (fewer spills mean fewer slots to
clear), and §3.3's makes §3.1's loops shorter.
