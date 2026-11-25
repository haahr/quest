# Plan: Closing the Median Programs' Gap to MLton

Fixes for what [benchmarks.md](benchmarks.md) §38 found: why the median programs of the MLton suite take longer than
MLton's builds of them. Three parts are done and pushed (2026-11-23 to 11-24); what is left is below. The plan is
deleted when it is done.

## Where the finished work is

- **What was made** is described with the code it changed: the SSA's passes `nanChecks`, `conditions`, and `loops`,
  and `intToReal`, in [ssa.md](ssa.md) §2 and §4.1; the cold proxy blocks and their register hints in
  [arm64.md](arm64.md) §3.8; the allocation fast path in [collector.md](collector.md) §3.4; `conv.int` in Quest and the
  runtime's string comparison in their code's comments; `tools/perf/counts.py` in [profiling.md](profiling.md) §3.1;
  and the census by layout in `benchmarks/mlton/allocations.py --by-layout`.
- **What it gained** is in benchmarks.md: Part 1 counted in §40 and timed in §41 (with two regressions the timing
  found, fixed), the conversions' changes in §42, Part 3 counted in §44.
- **What was measured or designed and not made** (proxy tests, a closure field's known function, payload-free cases by
  address, tags no upcast renumbers, refs inside their owners, the tag in the header, and the smaller ones under the 1%
  bar) is in [optimization-experiments.md](optimization-experiments.md), each with why.

## What is left

1. **Part 3's timing** (benchmarks.md §44.2): `run.py time --clean --scale 0.25`, one run each, before (`31dc2eac`)
   and after (`3daeb07b`), through C, ssac, arm64, and arm64 whole program, in separate worktrees under the lock.
   Running since 2026-11-24.
2. **arm64's back-edge moves** (what is left of step 14): with loops rotated in the SSA, mandelbrot's inner loop still
   ends in `fmov`s that register assignment makes from a permuted pair of parameters. Counted first on the hot back
   edges of mandelbrot and mpuz; made only if they are 1% of a program.
3. **Non-null facts** (the user, 2026-11-24, to investigate): a value freshly allocated, or already dereferenced, is
   not known to be non-null, so a later null check of it stays unless an identical one dominates it. How many such
   checks the suite's hot code runs, and what knowing them would save; designed only if that is 1% of a program.

Each is measured by instructions retired (`tools/perf/counts.py`) on whole programs at a thirty-second of the suite's
counts, unit by unit through arm64 and ssac, against the commit before it; a change under 1% on every program it aims at
is not made, and goes into optimization-experiments.md with its numbers. Gains only in whole programs are not aimed at
(optimization-experiments.md §1).
