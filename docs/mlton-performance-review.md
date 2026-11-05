# Why Quest's Code Is Slower Than MLton's: A Review

Why four of the MLton suite's programs (peek, wc-scanStream, ratio-regions, zebra) run 7 to 45 times as long as the
originals compiled by MLton, what Quest's compiler and runtime do that MLton's do not, and what would close the gap.
[arm64-performance-review.md](arm64-performance-review.md) compared the arm64 backend with clang on the same SSA; this
review compares all three of Quest's backends with MLton on the same algorithm. Apart from the bignum programs
(tensor, smith-normal-form, pidigits; [bignum.md](bignum.md)), these four are the furthest from MLton in
[benchmarks.md](benchmarks.md) §13: arm64 takes 73, 32, 9.6, and 10.5 times MLton's time there. Everything here was
measured at `63edc7d7`, with whole programs (`--whole-program`), on 2026-11-03.

## 1. Summary

The gap is in work, not in how fast the work runs. Quest's programs run at about MLton's instructions per cycle (4.2
to 5.2, against 4.6 to 7.3), and they retire 7 to 32 times as many instructions. The backends barely matter: C,
`ssac`, and arm64 are within 30 percent of each other on all four, and against a gap of 7 to 45 that is noise. What
the extra instructions do, in order of what they cost:

1. **Each allocation costs about 110 instructions.** The Boehm collector's `GC_malloc`, reached through `quest_alloc`,
   takes 110 instructions and 20 cycles for a 16-byte object, even with nothing live. That covers the call, a
   thread-local lookup through `pthread_getspecific`, the free list, building free lists, and marking. MLton bumps a
   pointer inline, and its copying collector spends nothing on objects that die young. With the collector's
   allocators replaced by a bump allocator that never frees (an experiment, §2.4), the four take 0.46 to 0.68 of
   their time. That is the most any change to the allocator alone can gain, and [collector.md](collector.md) is the
   plan for it.
2. **Quest allocates what MLton does not.** On the same work, Quest allocates 2.5 to 14 times MLton's bytes, and on
   peek a million times. Four causes, each a different optimization that is missing:
   - **wc-scanStream:** values passed through a block parameter escape (§3.2).
   - **ratio-regions:** closures passed to recursive library functions are allocated at each call (§3.3).
   - **zebra:** calls of closures captured by another function are not known calls (§3.4).
   - **peek and zebra:** `maybe.T(Int)` is boxed (§3.5).

   Removing each by hand in the source takes wc-scanStream to 0.16 of its time, ratio-regions to 0.43, and zebra to
   0.59.
3. **Two kinds of call the inliner never inlines** (§3.6). `maybe.none(:A)` and `lists.nil(:A)`, a function of type
   parameters alone, are called through a closure loaded from a global, in the hottest loops of peek and
   ratio-regions. `maybe.unwrap` is not inlined at all, because it names its module's `error`.
4. **peek's conversion is not the original's algorithm in cost** (§3.7). SML's property list holds exceptions, each
   `addPeek` declaring a fresh constructor, so a probe compares a tag. Quest has no extensible type, so the conversion
   holds closures that write into a cell, and a probe is two indirect calls, an allocation, and a store. MLton then
   optimizes peek's whole loop to 5 KB of allocation in all. No compiler change here closes peek's gap; a language
   change could.

After the experiments, what remains is 3.8 to 4.4 times MLton's time on three of the four. The rest is ordinary code
quality, of which the largest parts are a proxy check before most loads and the spills in very large inlined
functions (§3.8).

## 2. The measurements

### 2.1. How they were taken

`tools/perf/variants.py` built each program with each backend as a whole program. `run.py`'s `build_original` built
the MLton originals (MLton 20241230, `-output` only, as `run.py time --mlton` does), linked beside them as
`.build/perf/NAME.mlton`. Times are from `tools/perf/timeit.py --tags mlton,c,ssac,arm64 --rounds 3`, least user
time. The load average was 6 to 10, with a spike to 129 from other work, so the ratios between Quest's backends are
uncertain to 10 percent, but not the ratios to MLton. Instructions and cycles are from `/usr/bin/time -l`. Allocations
are from `benchmarks/mlton/allocations.py --whole-program --backend arm64`, and MLton's from `@MLton gc-summary --`.

`tools/perf/profile.py` put 88 percent of wc-scanStream's samples in the kernel, in `__read_nocancel`. That cannot
be right: the run spends 0.05 s of its 2.9 in the system, whether or not the collector has marker threads
(`GC_MARKERS=1` changes nothing). macOS's `sample` gave the distribution in §3.2, which agrees with the allocation
counts. The other three profiles agree with `sample`. The sampler now reads running threads' program counters
itself rather than taking `SIGPROF`, whose delivery macOS defers to the next system call's return (profiling.md §4),
and its profile of wc-scanStream agrees with `sample`'s.

### 2.2. Time

Least user time of three rounds, and each one's ratio to MLton's. The counts are those of `timeit.py` (a
thirty-second of the suite's), except ratio-regions: its count is the image's side, so it was run at the suite's
quarter, 384.

| Benchmark | count | MLton | C | `ssac` | arm64 |
|---|--:|--:|--:|--:|--:|
| peek | 6 | 0.30 s | 13.15 (44) | 12.90 (43) | 13.37 (45) |
| wc-scanStream | 1024 | 0.59 s | 17.75 (30) | 17.67 (30) | 22.76 (39) |
| ratio-regions | 384 | 1.02 s | 8.56 (8.4) | 8.23 (8.1) | 9.22 (9.1) |
| zebra | 2 | 0.35 s | 2.51 (7.2) | 2.72 (7.8) | 2.32 (6.7) |

As whole programs, timed in turn, arm64 takes 1.05 of C's time on peek and 0.92 on zebra. At the suite's quarter
count, it took 1.08 and 0.93. §13 recorded 1.52 and 1.21. That table's programs were compiled separately, and each
backend's runs were half an hour apart, so it is one of those two; which one was not measured.

### 2.3. Instructions and allocations

| Benchmark | count | instructions, MLton / arm64 | cycles, MLton / arm64 | IPC, MLton / arm64 | allocated, MLton / Quest |
|---|--:|--:|--:|--:|--:|
| peek | 2 | 2.24 G / 70.9 G | 0.31 G / 13.7 G | 7.3 / 5.2 | 5 KB / 6.40 GB (400 M objects) |
| wc-scanStream | 128 | 2.12 G / 37.5 G | 0.44 G / 8.9 G | 4.8 / 4.2 | 181 MB / 5.25 GB (256 M) |
| ratio-regions | 384 | 17.0 G / 125.3 G | 3.16 G / 27.8 G | 5.4 / 4.5 | 1.05 GB / 14.46 GB (782 M) |
| zebra | 2 | 4.66 G / 32.2 G | 1.02 G / 7.05 G | 4.6 / 4.6 | 0.99 GB / 2.54 GB (140 M) |

`ssac` retires 13 to 19 percent fewer instructions than arm64, in about the same cycles. Under MLton, collection
takes 0 to 17 percent of each run (wc-scanStream the most).

Where each Quest program allocates:

- **peek:** all of its allocation is `maybe.some` in the entry closure (`qf_hd_2`), 2.5 per `peek` on average: one per
  entry tried.
- **wc-scanStream:** 2 objects per character, both in `main`: a `Stream` tuple (16 bytes) and a `Read` option (24).
- **ratio-regions:** 90 percent is in `qf_preflowPush`. 84 percent of all its objects (at count 128) are made at
  ratio-regions.quest line 325: the closure passed to `lists.app` in `loop2`, one per bucket of the height queue on
  every wave, and most buckets are empty.
- **zebra:** 60 percent is `maybe.some` in `find`, inlined into `isConsistent` (84 million).

### 2.4. Experiments

**What an allocation costs.** A C loop of 10<sup>8</sup> `GC_MALLOC`s of 16 or 24 bytes, linked with the same libgc
and with the runtime's free space divisor of 1, keeping almost nothing live, takes 109 to 111 instructions and 20
cycles per allocation.

**Allocation for nearly nothing.** `DYLD_INSERT_LIBRARIES` with a library that interposes `GC_malloc` and
`GC_malloc_atomic` with a bump allocator that never frees. It is still a call from `quest_alloc`, through the
interposer, and it touches fresh memory, which costs page faults and cache misses that a reused nursery would not:

| Benchmark | count | MLton | arm64 | arm64, bump | bump / arm64 |
|---|--:|--:|--:|--:|--:|
| peek | 1 | 0.05 s | 2.28 s | 1.23 s | 0.54 |
| wc-scanStream | 64 | 0.06 s | 1.39 s | 0.71 s | 0.51 |
| ratio-regions | 128 | 0.06 s | 0.39 s | 0.18 s | 0.46 |
| zebra | 2 | 0.33 s | 2.28 s | 1.56 s | 0.68 |

**The allocations removed by hand.** Three variants of the conversions, each built as a whole program through arm64,
in the scratchpad (not kept). Each passes its own check (`raise bench.bug` on a wrong count):

- **wc-scanStream, flattened:** `count` and `input1` written as one loop over `(chunk, pos, ns)`. This is what
  scalar replacement across block parameters would make of them (§3.2).
- **ratio-regions, loops:** `loop2`'s two `lists.app` calls written as local recursive functions over the list, which
  contification makes loops. This is what specializing `app` for its known argument would make (§3.3).
- **zebra, `Int`:** `find` returns an `Int`, ~1 for none, rather than a `maybe.T(Int)`. This is what an unboxed option
  of an `Int` would make. A known call of `same`, inlined, would let escape analysis remove the boxes instead (§3.4).

| Variant | count | before | after | after, bump | MLton |
|---|--:|--:|--:|--:|--:|
| wc-scanStream, flattened | 64 | 1.45 s, 18.8 G instructions | 0.23 s, 2.27 G | 0.21 s | 0.06 s |
| ratio-regions, loops | 128 | 0.43 s, 6.16 G | 0.23 s, 3.42 G | 0.18 s | 0.06 s |
| ratio-regions, loops | 384 | 9.96 s, 125.2 G | 4.30 s, 61.5 G | — | 1.01 s |
| zebra, `Int` | 2 | 2.45 s, 32.2 G | 1.45 s, 19.8 G | 1.21 s | 0.33 s |

## 3. Findings

### 3.1. The cost of an allocation

**What happens.** Every allocation is a call of `quest_alloc`, which is `GC_MALLOC`, which calls `GC_malloc_kind`.
That looks up the thread's free lists with `pthread_getspecific`, pops one, and refills it through `GC_build_fl` and
`GC_allochblk_nth` when it is empty. Each collection then marks from the roots, and sweeps lazily as blocks are reused.
In the profiles, the allocator and the collector take 55 percent of peek's samples (`pthread_getspecific` another 11),
67 percent of wc-scanStream's (by `sample`), 56 percent of ratio-regions' (`pthread_getspecific` 13.5), and 41
percent of zebra's (6). The micro-benchmark puts it at 110 instructions an object, without the call into
`quest_alloc` or the stores that initialize the object. At that rate, the allocations alone are 62 percent of peek's
instructions, 75 percent of wc-scanStream's, 69 percent of ratio-regions', and 48 percent of zebra's.

**What MLton does.** It allocates by bumping a frontier pointer held in a register, against a limit checked once per
basic block for all of the block's allocations, and it collects young objects by copying. An object that dies before
the next collection costs its bump and nothing more. wc-scanStream's original allocates 1.4 bytes a character, and
MLton's collector spends 25 ms of a 146 ms run.

**Recommendation.** [collector.md](collector.md)'s design is the fix: bump allocation inline in both backends
(§3.4 there), and sticky mark bits so that the young are reclaimed by line (§3.5). The bump experiment bounds what
allocation can gain on these four, 0.46 to 0.68 of their time. That leaves them 3 to 25 times MLton's, so the
allocations themselves (§3.2 to §3.5) matter as much as their price.

An interim step was considered and dropped: popping from free lists of Boehm's (`gc_inline.h`) inline in
`quest_alloc`. It would change only the runtime, but it depends on Boehm's internals, and Boehm is to be replaced.

### 3.2. Allocations through block parameters (wc-scanStream)

**What happens.** The whole program is `main`: `count`, `input1`, and the reading closure are inlined into it, and
contification makes `count` a loop. Each character then runs this code, in arm64's output:

```
       bl    _quest_string_get_char
       and   x19, x0, #0xff
       ...                          ; the chunk and the position, with proxy checks
       add   x22, x12, #0x1         ; pos + 1
       mov   x0, #0x10
       bl    _quest_alloc           ; the Stream tuple
       stp   x20, x22, [x24]
       mov   x0, #0x18
       bl    _quest_alloc           ; the Read option, with its payload in it
       stp   x21, x19, [x0]
       str   x24, [x0, #0x10]
       b     loop                   ; which reads the Read's tag and fields at once
```

The `Read` is read as soon as it is made. It reaches its reader through a block parameter: `input1`'s two returns,
the character and the recursive call at the end of a chunk, join there. The `Stream` is the loop's parameter, bound to
a new tuple on every edge.

**Why.** `ssa/escape` ([ssa.md](ssa.md) §4.2) lets an allocation's pointer flow into a block parameter only when every
edge binds the parameter to that one allocation. A parameter bound to several allocations, or to an allocation on one
edge and a constant on another, is an escape. That is the shape of every loop that carries a tuple, and of every
function that returns an option from more than one place, once inlining has made the return a join.

**What MLton and LLVM do.** MLton's SSA passes tuples flattened, as separate arguments and results, wherever the
tuple is not otherwise needed (its `localFlatten` and `deepFlatten` passes). LLVM's SROA splits allocas only, which do
not flow through phis, so a frontend has to have done it. GHC's worker/wrapper transformation and constructed product
results do it for functions.

**Recommendation.** Scalar replacement across block parameters, in `ssa/escape` or as a pass after it:

- **Which parameters.** A block parameter is split into one parameter per word when every edge binds it to one of
  three things: a candidate allocation of one layout (the same size, its words stored at the same offsets with the
  same types), another such parameter, or, for an option, a constant of a case without components. Its other uses
  must be the uses that let an allocation be removed today.
- **The fixed point.** The analysis is the existing one, with "bound to that one value" replaced by "bound to a
  splittable value on every edge". Those found split together, an edge passing its allocation's words (or the
  constant's tag and zeros) in place of the pointer.
- **Identity.** An option or tuple whose identity is read (`is`, or a hash) still escapes, as now.

The flattened variant takes wc-scanStream from 1.45 s to 0.23 s, 18.8 to 2.3 billion instructions. Loops that carry
a tuple, and inlined functions that return an option from several places, are common in the compiler itself, so this
is likely to matter beyond the benchmark.

### 3.3. Closures for recursive higher-order functions (ratio-regions)

**What happens.** `preflowPush`'s `loop2` visits every bucket of the height queue on every wave, and for each one
calls `lists.app(:XY)(fun(p: XY): Ok marked[p.y][p.x] := false ps)` and `lists.app` of a larger closure. `app` is
recursive, so the inliner does not inline it ([ir.md](ir.md) §8.6: "a recursive function at all"). Each call
therefore allocates its closure, even for an empty list: 84 percent of the program's allocations. `someVector`'s
`lists.exists` and `everyN`'s argument are the same shape.

**What MLton does.** Its closure conversion defunctionalizes, by a whole-program flow analysis. A function argument
that can only be one `fn` becomes a known function, `List.app`'s loop calls it directly, and its environment's
variables are passed as the loop's arguments, so no closure is allocated.

**Recommendation.** Specialize a recursive function on an argument that is a known function and is passed unchanged
to its recursive calls (the static argument transformation, and GHC's specialization on a function argument):

- clone the function for the call, with the argument replaced by the known function in the clone's body;
- inline the known function at its calls in the clone, as the inliner already does for a non-recursive callee given
  a known function (its bonus of 10);
- contify the clone into a loop at the call.

The clone is made per call site, so it needs a size bound like the inliner's. `lists.app`, `lists.exists`,
`lists.map`, and folds are the cases that matter, and they are small. The variant with local loops takes
ratio-regions from 9.96 s to 4.30 s at count 384, and halves its instructions.

### 3.4. Known closures called through captures (zebra)

**What happens.** zebra's `same`, `left`, and `adjacent` are `make(fun ...)`: `make` returns a `fun`, and is inlined,
so each variable is bound to a known function, and the simplified IR calls them as such (`call f.11(...)`: 9 calls of
`same`'s function and 4 of `adjacent`'s in `isConsistent`). Their calls in the code are still indirect: 13 `blr`s
remain in `qf_isConsistent` in the `Int` variant, where `find`'s comparisons are inlined. `isConsistent` is a local
function that names them, so closure conversion makes each a capture, read from its environment at its start, and
the backends call a function directly only through a variable bound to its closure. Each `find` inlined into
`isConsistent` returns a `maybe.some` box (28 calls of `quest_alloc` in the function), and the box is an argument of
such a call, so it escapes.

**Recommendation.** Treat a variable read from a closure's environment as a known closure when every closure of that
function captures, at that index, a known closure of one function, so that the calls through it are direct
([mlton-gap.md](mlton-gap.md) §6). A direct call still takes the boxes as arguments; they are removed only where the
inliner then inlines `same`'s function (13 calls of a function larger than its threshold) or where an unboxed
representation of the option would apply. The `Int` variant measures the larger effect (2.45 s to 1.45 s, without the
84 million boxes), by changing the representation; how much the direct calls recover is to be measured.

### 3.5. Options of `Int` are boxed (peek, zebra)

[option-values.md](option-values.md) says that what still escapes in peek and zebra is mostly `maybe.some`'s box, and
that its deferred step would remove it. It would not: its representation holds a single-word option as its component
only when the component is a pointer, and excludes `Int`, `Bool`, `Char`, and `Real`, which have no spare value.
peek's and zebra's options are `maybe.T(Int)`. zebra's boxes go with §3.4. peek's are stored into a `var` field of a
cell, so they escape however the calls are made, and only an option two words wide, tag and value, held unboxed in
the field would remove them. That plan's status line is to be corrected; a two-word representation is a larger change
than it plans, and §3.7 matters more for peek.

### 3.6. Calls the inliner never inlines

- **Type applications.** `questlang/ir/inline` inlines `opCall`s, and never `opTypeApp`: the application of a function
  that takes type parameters alone. `maybe.none(:A)` and `lists.nil(:A)` are such functions, each returning a
  constant. In peek's `find` loop, each probe calls `qf_none` through the closure in `maybe`'s record (2 percent of
  the samples, beside the spills around the call). In ratio-regions' loop over the buckets, each one calls `qf_nil`
  (3 percent of the loop variant's samples), and that call is most of the loop's cost on an empty bucket.
- **Members that name their module's variables.** `maybe.unwrap` raises `maybe.error`, so its body names a variable of
  its module, and a whole program does not inline it ([ir.md](ir.md) §8.6). It is a call in peek's and zebra's hot
  paths (`qf_unwrap`, 3.8 and 5 percent of their samples). Rewriting such a reference as a member of the module's record
  (`maybe.error`), which the caller can name in a whole program, would lift the restriction.

Both are small changes to the inliner, and help every program that uses `maybe` and `lists`.

### 3.7. peek's universal type

SML's `Plist` holds `exn`s. Each `addPeek` declares `exception E of 'a`, so each property has a constructor of its
own, and `peek` finds its entry by matching the constructor, a comparison. MLton sees all four constructors, all the
lists, and the loop, and the original allocates 5 KB in all. The conversion's comment says why it differs: Quest's
exceptions are not values a list can hold. It encodes the universal type with closures, each entry a function that
stores its value in its `addPeek`'s cell. A probe is then:

- an indirect call of `maybe.none` (§3.6);
- a store into the cell;
- an indirect call of the entry, which allocates a `maybe.some` and stores it;
- a load and a test of the cell.

With allocation nearly free, peek still takes 25 times MLton's time. `dynamic.T` does not help: `dynamic.be(:Int)`
tests a structural type, and peek's four properties are all of `Int` but must be told apart. What would let a
conversion follow the original is a generative, extensible type, such as exceptions as values that a list can hold
and a `case` can match. That is a language question, not a compiler one, and is for the user to decide; until then,
peek measures closure calls and allocation, not property lists.

### 3.8. What remains

After the experiments, wc-scanStream takes 3.8 times MLton's time, ratio-regions 4.3, and zebra 4.4. From the
listings:

- **Proxy checks.** Nearly every load of a tuple, list cell, or option field is preceded by `tbnz w, #0` and has a
  cold call of `quest_proxy_element` or its relatives. zebra's `isConsistent` has 168 such call sites, 56 for tags and
  28 for options' payloads. They are not taken, but they lengthen the hot path, and each holds registers live across
  a call.
- **Very large inlined functions.** ratio-regions' `preflowPush` is 12,682 instructions. Most of its hot samples are
  on spills and reloads, and on loads of the queue array from a global on every bucket.
- **Clears on the way to a raise, laid out hot.** In `preflowPush`, each failed bounds check of the queue goes to a
  block that stores zero to 26 dead slots (arm64-performance-review.md §3.2, 3a), then jumps to the raise. These are
  the clears that `5f74f6c4` removed from raising blocks, now on the edge before one. The block also follows the
  check in the layout, so every check that passes takes a branch over 27 instructions. Both are for the code
  generator: no clears on an edge into a block that only raises, and such an edge laid out cold, as its target is.
- **Runtime calls per character.** wc-scanStream calls `quest_string_length` and `quest_string_get_char` once per
  character (8 percent of its `sample` samples). The C backend and `ssac` call them too. They are candidates for the
  SSA's instructions, as the word module's operations became (benchmarks.md §13).

None of these is MLton's cost model; each is the subject of the arm64 review or of a small change.

## 4. Recommendations, in order

In order of what they buy per line of change. **Lines** is the order of magnitude of the compiler's and runtime's
lines, without tests and goldens; **checks** is how many runs of `tools/check` the change should take to push, as in
arm64-performance-review.md §4.

| | Change | Where | Lines | Checks | Expected |
|---|---|---|--:|--:|---|
| 1 | Inline type applications, and members naming their module's variables | `ir/inline` | 100 | 1 to 2 | a few percent on peek, ratio-regions, zebra; every user of `maybe` and `lists` |
| 2 | Scalar replacement across block parameters | `ssa/escape` | 100 to 1,000 | 2 to 3 | wc-scanStream 0.16 of its time; loops that carry tuples |
| 3 | Specialization of recursive functions on a known function argument | `ir/inline`, `ir/clone`, `ir/contify` | 100 to 1,000 | 2 to 3 | ratio-regions 0.43; every `lists.app` and `exists` of a closure |
| 4 | Calls of captured known closures as known calls | `ir/closure`, the C printer, the SSA builder | 100 | 1 to 2 | zebra, up to 0.59 |
| 5 | No clears on an edge into a raising block; such edges laid out cold (§3.8) | `regalloc`, `select` (`layout`) | 10 to 100 | 1 | a taken branch less per check, in large functions |
| 6 | The collector, inline bump allocation | [collector.md](collector.md) | — | — | 0.46 to 0.68 on all four, with what 1 to 4 leave |
| 7 | A generative, extensible type, for peek: declined (§3.7) | the language | — | — | peek |
| 8 | Correct option-values.md: its step does not unbox `maybe.T(Int)` (done) | `docs` | — | — | — |

Items 1 to 5 are planned in [mlton-gap.md](mlton-gap.md), in that order, in the self-hosted compiler only: they are
optimizations, so the bootstrap compiler need not follow (two-compilers policy). Item 3 is specialization per call site
with a size bound, not whole-program defunctionalization. The language is left as it is for peek, and so are options of
`Int`, which stay boxed (§3.5). An interim inline free-list pop in Boehm (§3.1) is not to be done, since Boehm is to be
replaced.

Items 1 to 4 each remove work that MLton does not do, and are independent of the collector. Their gains multiply
with item 6's, since each removes allocations whose cost item 6 lowers. Items 2 and 3 are measured above by hand;
item 4's is to be measured. Each should be measured alone, on these four and on the suite
(`run.py time --clean --whole-program`), with `allocations.py` before and after.
