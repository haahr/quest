# Plan: Tuning the Inliner, and Workers

What remains of the self-hosted compiler's IR optimizer, whose design is in [ir.md](ir.md) §8.6 (the simplifier,
inlining, and contification) and §8.7 (unboxed results). [benchmarks.md](benchmarks.md) §7 measures what is done:
the suite's programs take 0.71 times as long through C and 0.76 through arm64, and the compiler's build 3 to 5 percent
longer.

---

## 1. Tuning

The threshold (30), the bonuses (30 for closed type arguments, 10 for a known function argument, 5 for a constant),
the growth bound (half the unit, or 1000), and the bound of six rounds were chosen, not measured. *Done* (2026-11-02):
[benchmarks.md](benchmarks.md) §11.3 varies each alone across the suite, and keeps them all. No setting is faster
than the defaults by more than 0.1 percent; one round, a size of 0, or either bonus changed by a factor of three is
slower by 1.6 to 6 percent.

`QUEST_INLINE` overrides them for measuring, as a list of `name=value` separated by commas, read by `ir/simplify`
when the compiler starts: `size` (30), `polymorphic` (30), `function` (10), `constant` (5), `growth` (the percent of
the unit it may grow by, 50), `budget` (the least growth, 1000), and `rounds` (6). A build's workers inherit it, so
`QUEST_INLINE=size=60 run.py time --clean` measures the suite with that setting.

The whole-program comparison has been retaken since abstract types became transparent in whole programs (ir.md §4.1):
at [benchmarks.md](benchmarks.md) §8.2, a whole program takes 0.94 times as long as a separate build, and
ratio-regions, which took 1.68 times as long whole at §7.2, is no longer slower whole.

## 2. Workers: Reduced Entry Points

Every function keeps its uniform entry (its environment, then its descriptors, then its parameters at their generic
layouts), which closures, exported functions, the function table, tracebacks, and indirect calls need. Unboxed
results (ir.md §8.7) are the only reduced entry so far, and no test's function but `language/unboxed_results`'s
qualifies. **A worker** would be a function's body at a reduced signature, decided by analysis after closure
conversion (when every function is lifted and escape is easy to see) and before represent (which then chooses its
parameters' representations). The original becomes a wrapper that converts and calls the worker, and known calls
call the worker; a function that does not escape and is not exported has only known calls, so its signature is
rewritten in place, with no wrapper. A worker:

- **drops what it does not use or what is the same at every call:** an environment it never reads, descriptors
  unused or static at every call;
- **takes a tuple parameter's components,** when the callee only reads them: it does not store, return, capture,
  or `is`-compare the tuple, and the tuple has no `var` components;
- **returns more of a tuple's components, and of more kinds,** than unboxed results allow now;
- **takes a `var` or `out` parameter as a value in and a value out,** when nothing captures it.

Quest's tuples have identity (`is` compares addresses), so each is decided from the body, not the type; what a type
alone fixes is already done (`qv_` functions have no environment) or belongs to a calling convention of Quest's own
at the machine level ([arm64.md](arm64.md) §6). *Done when* a benchmark gains from each kind of reduction, measured
in benchmarks.md, or the kind is shown not to arise.
