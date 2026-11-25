# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## A few library modules inlined into their importers, as in a whole program

**Problem.** Separate compilation inlines nothing across modules ([ir.md](ir.md) §8.6), so outside `util/maybe`
every `isSome`, `isNone`, `unwrap`, and `some` is a call, at the generic layout of an abstract type. Measured in
[iter.md](iter.md) §2: a `filter` reaching its held element through `util/maybe` took 305 instructions per element,
and the same stage with an option type of its own, 143; util/iter's stages hold their elements in slots of their own
for that reason (rule 5). Two other fixes were weighed and set aside (2026-11-22): making `maybe.T` manifest gives up
the abstraction, and importers would have to write `?some` and `!some.val` for any gain; carrying every module's
small bodies in `.qi` files changes the separate compilation model, under which an importer depends on interfaces
alone.

The idea: a short list, fixed in the compiler, of library modules that every importing unit sees as a whole program
would, with their abstract types transparent to shapes and their members open to inlining and specialization. The
candidates are `util/maybe`, `util/iter`, and `collections/vector`: small or hot, polymorphic, and stable. A user's
own modules keep the interface-only model. The prelinked modules (`conv`, `int`, `string`, ...) are already a tier
of their own, always compiled apart (ir.md §4.1); this adds a tier always merged.

**Measured** ([benchmarks.md](benchmarks.md) §36, 2026-11-22), with a whole program that compiles the three apart:
they account for all of a whole program's gain in `benchmarks/iter/` (`filter` 153 instructions per element
separately, 45 whole), and for 56% of it in the compiler, 2.5% of the separate compiler's instructions retired
(whole: 4.5%). Inlining the three into separately compiled units, without the rest of a whole program, may gain
somewhat less there.

**Built (2026-11-24)** ([ir.md](ir.md) §8.6, [benchmarks.md](benchmarks.md) §43): importers copy the three
modules' small functions (all of `util/iter`'s), with every shape still opaque. A build of the compiler costs 1.33
times one without copies, the compiler built retires about 3.5% fewer instructions, and `benchmarks/iter`'s
pipelines run as a whole program's. Ten other rules for what to copy were measured and not kept (§43). Left:

- **util/iter's own slots** may give way to `util/maybe` (iter.md rule 5), measured.
- **The sources' 12%.** Every unit that imports an inlined module elaborates and lowers its source. The module's
  own compile could write its lowered IR beside its object for importers to read, which needs an IR serialization
  and builds ordered so that importers wait.
- **Whole programs.** `shapes.transparent` substitutes through each type before its cache, and whole programs cost
  3.6 times. A shape built structurally, taking a representation where it meets an abstract application and sharing
  the shapes of the parts, would not pay it. Not profiled.
- **Instances whose layouts disagree** (`iter.T(Real)`) stay calls. If iterators over `Real` or records matter, the
  conversion could be a view rather than a copy.
- **A program's own modules.** `--inline-module` is tested on one module of a test's. Nothing records the choice
  between builds but the `.qi` mark's freshness, and no error names a module it cannot serve (one with variants, or
  without a source).
- **`collections/hashMap`** as a fourth, measured the same way.
- **`util/maybe` alone** peaks at 9.6 GB building the compiler, against 5.5 GB for all three: one run, not explained.

**Done when.** The listed modules' calls are inlined in separately compiled importers, util/iter's own slots may give
way to `util/maybe` (iter.md rule 5 then says so), and the driver build's instructions retired and `benchmarks/iter/`
are in benchmarks.md; or the idea is dropped with its measurement.

---

## string.getSub, catSub, and conc in Quest, over an unfilled string

**Problem.** These three are externals (runtime/quest_runtime.c) only because Quest has no way to allocate a string
without filling it. Written in Quest over `string.new` and `string.setSub`, they keep `setSub`'s `memcpy`, but
`new(n c)` first fills all n bytes, so each byte is written twice: a cost on long strings that the C versions don't
pay. A review of the library's externals (2026-11-23) found every other cheap external either moved to Quest without
loss or worth keeping in C (string comparison, the string builder, `real.format`, and `strtod` lose 1.2 to 100 times
in Quest, measured on arm64).

**Where to start.** An allocation the runtime and every backend provide, such as `string.uninitialized(n)` (zeroed
where a backend must, as WebAssembly's `array.new_default` is), and the three functions written over it in
lib/string.mod.quest, as runtime/wasm/core.mod.quest already writes `catSub` and `conc`.

**Done when.** The three are Quest, a micro-benchmark of each on long strings shows no loss against the C versions,
and their runtime functions and interpreter builtins are gone; or the primitive is judged not worth adding.

## An array copy in arrayOp

**Problem.** lib/arrayop.int.quest offers only `new`, `extent`, `get`, and `set`, so a program that needs a copy of an
array writes the loop itself. The first element supplies the fill value, so an empty array needs its own case.

**Where to start.** A `copy` in lib/arrayop.mod.quest, along these lines:

```quest
let copy(A::TYPE a: Array(A)) =
  begin
    let n = extent(a)
    if n is 0 then array of :A end
    else
      let b = array of(n a[0])
      for i = 1 upto {n - 1} do
        b[i] := a[i]
      end
      b
    end
  end
```

A runtime primitive (a `memcpy` on the C and arm64 backends, `array.copy` on WebAssembly) would avoid filling `b`
before overwriting it, as with the string task above.

**Done when.** `copy` is in the interface, with a test, and the hand-written copies in lib/ and questlang/ use it; or
it is judged not worth adding.

## What the error-message help left out

**Problem.** The help for names, mismatches, and syntax errors (diagnostics.md §4.1–4.2) left four things out:

- a missing import of a library module (`nothing named 'vector' is imported; collections/vector :
  collections/Vector imports the collection`), which needs the list of `lib/` interfaces where a lookup fails;
- the location of the declaration in the help for `Iter.T` and an unapplied `vector.T` (`where it is declared, at
  3:13`), which needs the declared type's span where the subtype failure is found;
- a note on the usual syntax error naming a construct still open where the parse stopped, left out since nearly
  every error inside a block would carry it;
- several syntax errors in one report, which needs recovery points in the grammar and the engine.

**Where to start.** `typechecker/near_miss.py` and `questlang/typechecker/nearMiss` for the first two;
`syntax/unclosed.py` and `questlang/syntax/parser/unclosed` for the third.

**Done when.** Each is in both compilers with an error test, or judged not worth it.

---

The entries below are the performance work benchmarks.md names as left and nothing has taken up: not done since, not
in [optimization-experiments.md](optimization-experiments.md), and not declined (collected 2026-11-25). Each is
measured by instructions retired (`tools/perf/counts.py`) on whole programs at a thirty-second of the suite's counts,
unit by unit through arm64 and ssac; a change under 1% on every program it aims at goes into
optimization-experiments.md instead.

## arm64's register allocator: copies at joins, spills reloaded each round, loads moved

**Problem.** The arm64-built compiler takes 1.06 of the ssac-built one's time (benchmarks.md §45), and §21.5 found
half of its gap then in the hot functions' length: hashMap `findIndex` 157 instructions against C's 117, `insert` 677
against 542, sha256 `hexDigest` 1,215 against 552. What §22 left of it is the register allocator's (§22.3): copies at
a loop's join, a spill reloaded each round in `findIndex`, and an `ldr` then a `mov` where one `ldr` would do (§24.1
item 5, 136 to 3,588 per program; §38.3 item 7, four per element of tyan's compare). `883a870d` made a join take its
hot predecessor's register; hint-following and full coalescing were tried and not kept (arm64.md §6.1).

**Where to start.** `codegen/machine/regalloc`; arm64.md §6.2 proposes conservative (Briggs) coalescing. A profile of
the ssac-built and arm64-built compilers (§21.5's method) says which functions carry the gap now.

**Done when.** `findIndex`'s probe loop has no copy at its join and no reload each round, and the compiler's gap and
the suite's counts are measured; or it is judged not worth it.

## An unproxy first made inside a loop, hoisted

**Problem.** The loops pass hoists invariant values, but not an `unproxy` first made inside the loop (benchmarks.md
§22.2 item 6): `movable` in `ssa/passes/loops` does not list `opUnproxy`, and rotation's walk stops at one.

**Where to start.** `questlang/ssa/passes/loops.mod.quest`, `movable` and rotation's walk; the `unproxy` must stay
after any check that guards it.

**Done when.** A loop over a record's fields tests its proxy once before the loop, with a test, and the counts are
measured.

## Loads reused across a join

**Problem.** Value numbering starts a new memory generation at a join, continuing one only from a single
predecessor, so a load after an `if` without an `else` is not reused (benchmarks.md §24.3, batch 7). No benchmark
showed one hot then.

**Where to start.** `questlang/ssa/passes/valueNumbers`: a join whose predecessors all keep a generation (no store, no
call) can continue it.

**Done when.** Measured on the suite, and kept or moved to optimization-experiments.md.

## Fewer exception handlers entered

**Problem.** A `try` whose body cannot raise still pushes a handler, and a raise whose handler is in the same function
goes through the runtime rather than jumping (benchmarks.md §3.5; arm64.md §6.2). Inlining makes the second commoner.
knuth-bendix, boyer, and model-elimination raise and catch constantly; arm64's `try` no longer calls `_setjmp`
(arm64.md §3.6), but the push and the raise through the runtime remain.

**Where to start.** The IR, for every backend: a body with no call and no raise needs no handler; a raise to a
handler in the same function is a jump to it with the payload.

**Done when.** Both are in, with tests, on every backend, WebAssembly included, and measured on those three programs.

## The small recursions on arm64

**Problem.** even-odd through arm64 takes about 1.8 times ssac's time (benchmarks.md §35.3, 0.53 against 0.29 of
MLton's), since clang reduces its loop further after `tailJumps` (§14.2). fib, tak, and tailfib are clang's folding
and not worth chasing (§27.3).

**Where to start.** arm64.md §6.2, "The small recursions": compare even-odd's loop through both backends
(`tools/perf/asmstats.py`).

**Done when.** The difference in its loop is understood and fixed, or recorded in optimization-experiments.md.

## Spills in very large inlined functions

**Problem.** ratio-regions' `preflowPush` (12,682 instructions) had most of its hot samples on spills and reloads,
and on loads of the queue array from a global on every bucket (benchmarks.md §9). It takes 2.99 times MLton's time
through arm64 against 2.61 through ssac (§35.3, before §44).

**Where to start.** Profile it again after §44 (`tools/perf/profile.py .build/perf/ratio-regions.arm64 -f ...`);
arm64.md §6.2 has it.

**Done when.** The spills are understood and the fix measured, or it is recorded as not worth it.

## arm64 against ssac on the bignum programs

**Problem.** smith-normal-form takes 23.7 times MLton's time through arm64 against 12.2 through ssac, and pidigits
10.3 against 8.58 (benchmarks.md §35.3). §15.4–§15.5 fixed the carries and the constant loads, and §44 took 0.90 to
0.95 of their instructions, but nothing takes apart what is left.

**Where to start.** Time them again after §44, then compare `mulLimbs` and its neighbours through both backends with
`asmstats.py` and `profile.py`.

**Done when.** What is left is named, and fixed or recorded.

## The collector's growth target counts a recyclable block as in use

**Problem.** After the compiler's collections the blocks in use are 3.2 times the live lines and 6.6 times the live
bytes, so a `-j 8` worker's heap reaches 2.2 GB for 223 MB of data (benchmarks.md §16.3), and barnes-hut's 451 MB for
3 MB live (§17.2). Memory, not time.

**Where to start.** The target computed after the sweep in `quest_gc_sweep`, `runtime/quest_gc.c`; collector.md §9.6.

**Done when.** The target counts live lines, and the compiler's maximum resident size and the suite's times are
measured.

## WebAssembly's slowest programs, profiled

**Problem.** Through node, imp-for takes 35.0 times MLton's time, wc-scanStream 91.2, knuth-bendix 27.1, fft 15.3,
and matrix-multiply 8.16 (benchmarks.md §35.3); §25.1 says they wait for a profile of their own. Typed arrays were
measured slower (wasm.md §9.2).

**Where to start.** node's `--cpu-prof` on each, as wasm.md describes for the compiler.

**Done when.** Each one's time is accounted for, and what would fix it is a task or a note in
optimization-experiments.md.

## Two observations to check

- **simple reports `gc minors: 0` for 465 collections** (benchmarks.md §34). Likely §17.2's rule that a heap whose
  blocks in use stay under half of the 64 MB minimum has only full collections; confirm, and say so in collector.md.
- **mlyacc's heap held 1.31 MB live against C's 0.73** (§24.2 item 9), measured under the conservative scan. Stack
  maps (§18) scan only what is live across each call; measure it again, and drop it if the difference is gone.
