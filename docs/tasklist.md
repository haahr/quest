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
