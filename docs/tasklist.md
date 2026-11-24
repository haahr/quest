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

**Plan:** [inlined-modules-plan.md](inlined-modules-plan.md) (2026-11-22). It covers choosing the modules by
profiling, copying members while each module's state stays single, layouts across the boundary, staleness, the steps,
and a later `--inline-module` option for a program's own modules, marked in their `.qi` files.

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
