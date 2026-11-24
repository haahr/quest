# The Inliner's Settings, and Workers

The settings of the self-hosted compiler's IR optimizer, whose design is in [ir.md](ir.md) §8.6 (the simplifier,
inlining, and contification) and §8.7 (unboxed results), and one piece of open work on it, workers.
[benchmarks.md](benchmarks.md) §7 measures the optimizer (2026-10-31): the suite's programs took 0.71 times as long
through C and 0.76 through arm64, and the compiler's build 3 to 5 percent longer.

---

## 1. Settings

The threshold (30), the bonuses (30 for closed type arguments, 10 for a known function argument, 5 for a constant),
the growth bound, and the bound of six rounds were chosen, then measured: [benchmarks.md](benchmarks.md) §11.3
(2026-11-02) varies each alone across the suite, and keeps them all. No setting was faster than the defaults by more
than 0.1 percent; one round, a size of 0, or either bonus changed by a factor of three was slower by 1.6 to 6 percent.
The growth bound was raised from half the unit to three quarters on 2026-11-05 ([benchmarks.md](benchmarks.md) §20.1).

`QUEST_INLINE` overrides them for measuring, as a list of `name=value` separated by commas, read by `ir/simplify`
(`setting`) when the compiler starts: `size` (30), `polymorphic` (30), `function` (10), `constant` (5), `growth` (the
percent of the unit it may grow by, 75), `budget` (the least growth, 1000), `rounds` (6), and `copy` and `copyFun` (the largest
function an importer copies from an inlined module: 15 for one that passes no function, and for one that does the
sum of `size` and `polymorphic`; -1 for no bound; ir.md §8.6). A build's workers inherit it, so `QUEST_INLINE=size=60 run.py time --clean` measures the
suite with that setting.

Whole programs and separate builds compare at [benchmarks.md](benchmarks.md) §8.2 (2026-11-01), measured once
abstract types were transparent in whole programs (ir.md §4.1): a whole program took 0.94 times as long as a separate
build, and ratio-regions, which took 1.68 times as long whole at §7.2, was no longer slower whole.

## 2. Open Work: Workers, Reduced Entry Points

Every function keeps its uniform entry (its environment, then its descriptors, then its parameters at their generic
layouts), which closures, exported functions, the function table, tracebacks, and indirect calls need. Unboxed
results (ir.md §8.7) are the only reduced entry, and no test's function but `language/unboxed_results`'s qualifies.
**A worker** would be a function's body at a reduced signature, decided by analysis after closure conversion (when
every function is lifted and escape is easy to see) and before represent (which then chooses its parameters'
representations). The original becomes a wrapper that converts and calls the worker, and known calls call the worker;
a function that does not escape and is not exported has only known calls, so its signature is rewritten in place,
with no wrapper. A worker:

- **drops what it does not use or what is the same at every call:** an environment it never reads, descriptors
  unused or static at every call;
- **takes a tuple parameter's components,** when the callee only reads them: it does not store, return, capture,
  or `is`-compare the tuple, and the tuple has no `var` components;
- **returns more of a tuple's components, and of more kinds,** than unboxed results allow;
- **takes a `var` or `out` parameter as a value in and a value out,** when nothing captures it.

Quest's tuples have identity (`is` compares addresses), so each is decided from the body, not the type; what a type
alone fixes is already done (`qv_` functions have no environment) or belongs to a calling convention of Quest's own
at the machine level ([arm64.md](arm64.md) §6.2). Each kind of reduction is worth keeping if a benchmark gains from
it, measured in benchmarks.md, or else the kind is shown not to arise.
