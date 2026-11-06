# Benchmarks

Quest has two sets of benchmarks:

- **The MLton suite** (`benchmarks/mlton`): the 46 Standard ML programs of MLton's benchmark suite, each converted to
  Quest, with a runner that checks each conversion's output against the original's and times both. It measures how
  fast Quest programs run against a mature optimizing compiler for a similar language, and it is where Quest's
  performance is tracked (§3).
- **The C backend's measurements** (`tests/perf`): a few small programs that cross polymorphic boundaries or use
  records and variants in hot loops, and the time the backend takes to generate C, for checking that a change to the
  backend does not slow it or its output (`python tests/perf/measure.py`, compared with `tests/perf/baseline.json`).

This document describes the MLton suite, records the baseline taken on 2026-10-28, lists what profiling the slowest
benchmarks found and what could be done about it, compares the C and arm64 backends (§4 to §6), measures the inliner
(§7), times every backend and the inliner's settings at one commit (§11), measures the Jupyter kernel's interrupt checks
(§12), times the SSA's backends after the arm64 review (§13), measures the SSA's loops of accumulated recursion and
mutual tail calls (§14), and times the library's arbitrary-precision integers (§15).

> **tensor changed on 2026-11-06 (§1.4).** Both its original and its conversion now use each operation's result and
> no longer print timings. Until then MLton removed the work, so tensor's times before that date, MLton's 0.03 s in
> the 2026-10-28 baseline above all, measure a different program from the one in the tree, and MLton's must be taken
> again before tensor's ratio means anything.

## 1. The MLton suite

`benchmarks/mlton/README.md` describes the suite: where the originals come from, how they were converted, how the
conversions are checked, and the two programs (fxp and merge) left out. In short:

- Each `NAME.quest` is a conversion of `sml/NAME.sml`, keeping its algorithms, data structures, and order of
  operations. A program does its work n times, n being its first argument.
- `expected/` holds the originals' output (standard output, exit status, and the files they write) as MLton-compiled
  programs produce it at count 1. A conversion must match it byte for byte.
- MLton's counts (`COUNTS` in `run.py`) make each original run for 30 to 45 seconds on its authors' machine in 2022.

### 1.1. Running

`run.py` builds the conversions with a Quest compiler (`./quest`, the self-hosted one, unless `--compiler` names
another, such as `./questboot`) and the originals with `mlton`, and runs each program in a scratch directory holding a
copy of `DATA/`.

| Command | What it does |
|---|---|
| `run.py check [NAME...]` | Runs each conversion at count 1 and compares its output with `expected/` |
| `run.py time [NAME...]` | Times each conversion at MLton's count times `--scale`, or at `--count` |
| `run.py report FILE...` | Summarizes times recorded with `--results` (§1.2) |
| `run.py reference [NAME...]` | Rebuilds the originals and records their output in `expected/` again |

Options of `time` (and, where they apply, `check`):

| Option | Effect |
|---|---|
| `--compiler PATH` | The Quest compiler that builds (or interprets) the conversions |
| `--backend B` | Builds the conversions with backend `B` (`c`, `ssac`, or `arm64`; [arm64.md](arm64.md)), into a build directory of its own; `time` reports each build's seconds |
| `--interpret` | Runs each conversion in the compiler's tree-walking interpreter (`--stop-after interpret`) instead of building it |
| `--jit` | Runs each conversion on the compiler's JIT (`--jit`, [jit.md](jit.md)) instead of building it, each run compiling it again |
| `--mlton` | Also times the original, and prints the ratio |
| `--mlton-only` | Times only the original |
| `--scale S`, `--count N` | Runs at MLton's count times S (default 1), or at N |
| `--runs R` | Times each program R times (default 1); the median is reported |
| `--timeout T` | Seconds a run may take (default 3600); a run that takes longer ends that program's runs |
| `--results FILE` | Appends each program's times to FILE as a JSON line |
| `--clean` | Removes `benchmarks/mlton/.build/` before building anything (also for `check` and `reference`) |

A run at count 1 is also checked against `expected/`, and one that prints the wrong output is recorded with the first
line of its standard error and ends that program's runs. Builds (not timed) go to `benchmarks/mlton/.build/`.

That build tree's unit caches don't notice a change to the compiler, so a run after one can link units the old
compiler built. Pass `--clean` to the first command of any measurement (or check) taken after the compiler has changed;
the commands below do.

### 1.2. Reports

`run.py report` reads the JSON lines that `--results` wrote, from any number of files, and prints a Markdown table for
each Quest system (a compiler, or a compiler's interpreter): each benchmark's count, MLton's median time and the
system's at that count, their ratio, and the geometric mean of the ratios. `--exclude NAME,...` adds a second mean
without those benchmarks. A run that timed out shows as `>T`, its ratio a lower bound, and makes the mean a lower
bound; one that printed the wrong output shows as failed and counts in no mean. A later entry for a benchmark,
system, and count replaces an earlier one, so a benchmark can be timed again and appended.

### 1.3. The topline metric

**The geometric mean, over all the benchmarks, of the ratio of the self-hosted compiler's time to MLton's**, each
timed at the same count. Lower is better; 1 means as fast as MLton. A geometric mean weights a factor of two the same
on every benchmark, however long it runs. Four benchmarks' ratios say less about either compiler than about which one
removed work the other did (§2.3), so the mean without them is reported beside it. tensor was one of them until
2026-11-06 (§1.4).

### 1.4. Changes to the suite

- **tensor, 2026-11-06: the results are used, and the timings are not printed.** The original (`sml/tensor.sml`)
  timed each operation, 20 or 4 repetitions of it on a square tensor of 100 to 500 a side, and printed the average
  milliseconds and nothing else; each result went unused. MLton removed the work: the original took 0.02 s of
  processor time at the suite's quarter count of 2, and every time it printed was 0. The conversion did all the work,
  as Quest's compilers do not remove a call whose result is unused, so tensor's ratio was 3,337 in the 2026-10-28 baseline and 554 to 1,234 in the last suite.
  Both now add each result's element [1,2] to a sum per operation and print the sums in place of the times (40, 20,
  and 20 for `+`, `*`, and `/`, and 4 times the size for the contractions `+*` and `*+`), and `expected/tensor.out`
  was recorded again. MLton then takes 7.92 s at count 2 (load 13.7), the contractions about 120 to 150 ms a call at
  500 a side, as many as before: it does each call, and hoists none out of the loop. Against that, the last suite's
  Quest times (§19 for C and arm64, §17 for ssac, processor time) put tensor at about 4.1 through C, 1.8 through ssac,
  and 2.1 through arm64. **Times of tensor before this change, Quest's and MLton's, are of the old program:** compare
  only times taken after it, and take MLton's again (`run.py time --mlton-only --scale 0.25 tensor`, appended to the
  results reported, replaces the 2026-10-28 baseline's) before reporting tensor's ratio.

## 2. Baseline (2026-10-28)

### 2.1. How it was taken

| | |
|---|---|
| Machine | Apple M1 Max (8 performance and 2 efficiency cores), 64 GB, macOS 26.6.2 |
| MLton | 20241230 |
| C compiler | Apple clang 21.0.0, at `-O2`, as both Quest compilers invoke it |
| Collector | Boehm-Demers-Weiser 8.2.12 (Homebrew `bdw-gc`) |
| Quest | `7551249b` (ABI 49, with `_setjmp` exceptions); the conversions as of `47b5a20c` |

The self-hosted compiler is `./quest` (stage 2, seeded from the bootstrap), and the bootstrap `./questboot`. When these
times were taken, they were `./questc` and `./quest`, and the baselines and the tables below name the systems so
(`questc`, `questc interpret`, and `quest interpret`, the bootstrap's). Each system ran each benchmark three times, and
each time is the median of the three.

- **Compiled:** MLton and `./quest` at a quarter of MLton's counts (`--scale 0.25`), so that most of MLton's runs take
  2 to 14 seconds, one benchmark at a time (MLton's three runs, then Quest's) on an otherwise idle machine.
- **Interpreted:** `./questboot --stop-after interpret` (the bootstrap's interpreter, in Python) and
  `./quest --stop-after interpret` (the self-hosted one, compiled) at count 1, the least a program can do, with a
  10-minute timeout, against MLton at count 1. Their times include parsing and type checking the program, and MLton's
  at count 1 are dominated by process startup for the benchmarks whose single iteration is short, so these ratios are
  rough; at ratios in the hundreds or thousands, the difference does not matter. The two interpreters ran side by
  side.

The times are in `benchmarks/mlton/baselines/2026-10-28/`, one file per command below, so that a later
measurement can be reported beside them. To take them again (into a directory of your choosing, here `new/`):

```bash
cd benchmarks/mlton
./run.py time --clean --mlton --compiler ../../quest --scale 0.25 --runs 3 --timeout 1800 --results new/compiled.jsonl
./run.py time --mlton-only --count 1 --runs 3 --results new/mlton-count1.jsonl
./run.py time --interpret --compiler ../../quest --count 1 --runs 3 --timeout 600 --results new/quest-interpret.jsonl
./run.py time --interpret --compiler ../../questboot --count 1 --runs 3 --timeout 600 --results new/questboot-interpret.jsonl
./run.py report new/*.jsonl --exclude fib,tailfib,tak,tensor
```

The topline alone takes about two and a half hours (the first command); the interpreters take several more.

### 2.2. Summary

| System | Geometric mean of time / MLton's | Benchmarks that ran |
|---|---|---|
| Self-hosted compiler (`./quest`) | **5.05**; 6.49 without fib, tailfib, tak, and tensor | all 46 |
| Self-hosted interpreter (`./quest --stop-after interpret`) | 557 on the 8 that both interpreters finish; >1246 on the 17 that finish or time out | 9 finish, 8 time out, 29 fail |
| Bootstrap interpreter (`./questboot --stop-after interpret`) | 2453 on the 8 that both interpreters finish; >2052 on the 20 that finish or time out | 8 finish, 12 time out, 26 fail |

The self-hosted compiler's programs take about five times MLton's time. The interpreters cannot run most of the suite
(§2.4); where both run, the self-hosted interpreter is 4.4 times as fast as the bootstrap's (2.8 to 5.2).

### 2.3. The self-hosted compiler

Times in seconds; n is a quarter of MLton's count.

| Benchmark | n | MLton | questc | Ratio |
|---|--:|--:|--:|--:|
| barnes-hut | 8192 | 4.18 | 19.25 | 4.61 |
| boyer | 3072 | 5.14 | 39.99 | 7.77 |
| checksum | 3072 | 9.59 | 344.21 | 35.9 |
| count-graphs | 3 | 4.22 | 27.29 | 6.47 |
| DLXSimulator | 2 | 4.37 | 22.03 | 5.04 |
| even-odd | 6 | 3.74 | 0.94 | 0.25 |
| fft | 4 | 3.83 | 5.92 | 1.55 |
| fib | 8 | 14.17 | 0.51 | 0.036 |
| flat-array | 12288 | 7.79 | 44.74 | 5.74 |
| hamlet | 96 | 9.91 | 30.42 | 3.07 |
| imp-for | 1024 | 3.89 | 61.60 | 15.8 |
| knuth-bendix | 768 | 8.56 | 79.44 | 9.28 |
| lexgen | 384 | 3.18 | 9.24 | 2.90 |
| life | 8 | 7.55 | 26.82 | 3.55 |
| logic | 64 | 6.46 | 29.13 | 4.51 |
| mandelbrot | 2 | 2.96 | 33.14 | 11.2 |
| matrix-multiply | 48 | 4.84 | 25.23 | 5.21 |
| md5 | 3 | 7.27 | 92.27 | 12.7 |
| mlyacc | 768 | 5.59 | 15.97 | 2.85 |
| model-elimination | 1 | 7.24 | 42.98 | 5.94 |
| mpuz | 32 | 4.29 | 53.19 | 12.4 |
| nucleic | 1024 | 4.42 | 8.74 | 1.98 |
| output1 | 3 | 6.49 | 53.72 | 8.28 |
| peek | 48 | 2.24 | 334.39 | 149.3 |
| pidigits | 1024 | 0.82 | 35.10 | 42.8 |
| psdes-random | 6 | 11.31 | 112.84 | 9.98 |
| ratio-regions | 384 | 0.95 | 20.35 | 21.4 |
| ray | 384 | 6.07 | 23.16 | 3.81 |
| raytrace | 24 | 6.20 | 11.08 | 1.79 |
| simple | 256 | 10.24 | 18.20 | 1.78 |
| smith-normal-form | 48 | 4.03 | 764.13 | 189.5 |
| string-concat | 64 | 1.72 | 11.49 | 6.68 |
| tailfib | 128 | 2.74 | 0.01 | 0.003 |
| tailmerge | 6144 | 5.17 | 50.64 | 9.79 |
| tak | 8 | 12.82 | 0.61 | 0.047 |
| tensor | 2 | 0.03 | 86.81 | 3337 |
| tsp | 4 | 3.74 | 12.40 | 3.32 |
| tyan | 96 | 5.15 | 16.88 | 3.28 |
| vector-rev | 24 | 3.49 | 11.23 | 3.22 |
| vector32-concat | 12 | 2.33 | 5.22 | 2.24 |
| vector64-concat | 8 | 1.88 | 3.57 | 1.90 |
| vliw | 256 | 5.02 | 15.96 | 3.18 |
| wc-input1 | 4096 | 8.95 | 80.30 | 8.97 |
| wc-scanStream | 8192 | 5.30 | 197.02 | 37.2 |
| zebra | 16 | 2.49 | 64.81 | 26.0 |
| zern | 4096 | 3.12 | 9.59 | 3.07 |

Four ratios measure which compiler removed work rather than how fast either runs it:

- **fib, tak, and tailfib**: each iteration computes the same pure function of the same constants, and clang computes
  it once and hoists it out of the loop: the conversions take the same time at count 1, 8, and 64. Per call, Quest is
  still faster on fib (0.70 seconds for fib 41 against MLton's 1.78), whose recursion clang partly turns into a loop
  and whose additions MLton checks for overflow.
- **tensor**: its operations produce results nothing uses, and MLton removes the work; the conversion does all of it.
  The suite changed tensor on 2026-11-06 so that both use the results (§1.4).

even-odd is genuinely faster in Quest (0.16 seconds an iteration against MLton's 0.64): clang turns the mutual
recursion into a loop. The time scales with the count.

### 2.4. The interpreters

Times in seconds at count 1. A failure is the interpreter's error: **stack overflow** is `stack.overflow`, raised
when more than 1000 calls are active (§3.9), which the conversions' recursive loops reach at once; **type application
bug** is the mis-evaluation of §3.9; raytrace catches every exception, as its original does, so its overflow shows only
as the image it does not write. The bootstrap interpreter reaches the 10-minute timeout on life, md5, and tsp before
it reaches the depth that overflows the self-hosted one. Ratios against MLton at count 1 overstate the gap where MLton's
time is mostly process startup (0.01 seconds).

| Benchmark | MLton | questc interpret | Ratio | quest interpret | Ratio |
|---|--:|--:|--:|--:|--:|
| barnes-hut | 0.01 | 0.17 | 27.0 | 0.79 | 124.3 |
| boyer | 0.01 | 9.23 | 884.9 | 25.75 | 2468 |
| checksum | 0.01 | stack overflow |  | stack overflow |  |
| count-graphs | 1.42 | >600 | >422.4 | >600 | >422.4 |
| DLXSimulator | 2.22 | stack overflow |  | stack overflow |  |
| even-odd | 0.64 | stack overflow |  | stack overflow |  |
| fft | 1.02 | stack overflow |  | stack overflow |  |
| fib | 1.78 | >600 | >337.8 | >600 | >337.8 |
| flat-array | 0.01 | 17.12 | 2090 | 77.52 | 9465 |
| hamlet | 0.22 | type application bug |  | type application bug |  |
| imp-for | 0.01 | 82.75 | 7396 | 402.94 | 36011 |
| knuth-bendix | 0.02 | stack overflow |  | stack overflow |  |
| lexgen | 0.02 | stack overflow |  | stack overflow |  |
| life | 0.95 | stack overflow |  | >600 | >629.7 |
| logic | 0.09 | stack overflow |  | stack overflow |  |
| mandelbrot | 1.47 | stack overflow |  | stack overflow |  |
| matrix-multiply | 0.10 | stack overflow |  | stack overflow |  |
| md5 | 2.43 | stack overflow |  | >600 | >247.1 |
| mlyacc | 0.02 | type application bug |  | type application bug |  |
| model-elimination | 7.23 | type application bug |  | type application bug |  |
| mpuz | 0.14 | >600 | >4396 | >600 | >4396 |
| nucleic | 0.01 | 12.41 | 1320 | 49.58 | 5276 |
| output1 | 2.17 | stack overflow |  | stack overflow |  |
| peek | 0.05 | >600 | >11880 | >600 | >11880 |
| pidigits | 0.01 | 1.12 | 175.1 | 5.89 | 918.6 |
| psdes-random | 4.24 | stack overflow |  | stack overflow |  |
| ratio-regions | 0.01 | 0.18 | 27.8 | 0.85 | 131.5 |
| ray | 0.02 | stack overflow |  | stack overflow |  |
| raytrace | 0.27 | no output file |  | no output file |  |
| simple | 0.05 | stack overflow |  | stack overflow |  |
| smith-normal-form | 0.09 | stack overflow |  | stack overflow |  |
| string-concat | 0.03 | stack overflow |  | stack overflow |  |
| tailfib | 0.03 | 116.75 | 3875 | 591.86 | 19642 |
| tailmerge | 0.01 | stack overflow |  | stack overflow |  |
| tak | 1.62 | >600 | >369.6 | >600 | >369.6 |
| tensor | 0.01 | >600 | >41174 | >600 | >41174 |
| tsp | 1.09 | stack overflow |  | >600 | >549.6 |
| tyan | 0.06 | 174.73 | 2957 | >600 | >10154 |
| vector-rev | 0.16 | >600 | >3743 | >600 | >3743 |
| vector32-concat | 0.20 | stack overflow |  | stack overflow |  |
| vector64-concat | 0.24 | stack overflow |  | stack overflow |  |
| vliw | 0.03 | type application bug |  | type application bug |  |
| wc-input1 | 0.04 | stack overflow |  | stack overflow |  |
| wc-scanStream | 0.04 | stack overflow |  | stack overflow |  |
| zebra | 0.16 | >600 | >3637 | >600 | >3637 |
| zern | 0.01 | stack overflow |  | stack overflow |  |

## 3. Where the time goes, and what to do about it

Twenty benchmarks were profiled with macOS `sample`: those with the worst ratios (above 10, leaving out tensor, whose
ratio is MLton's doing, and md5, studied through its C and §3.3's experiment instead) and ten others. Their
generated C was read, and the promising remedies were tried by hand on copies of the runtime or of the generated C,
each checked to print what `expected/` holds. The findings, roughly in order of how much they would move the topline:

### 3.1. Allocation goes through libgc's general entry

Every allocation calls `GC_malloc` in the libgc dylib, which finds its thread's free lists with `pthread_getspecific`,
through two dyld stubs. In peek, zebra, wc-scanStream, tailmerge, ratio-regions, count-graphs, mpuz, mandelbrot, and
imp-for, the allocation entry alone (`GC_malloc_kind`, `pthread_getspecific`, the stubs) is a quarter to a half of all
samples, and collection (`GC_mark_from`, `GC_build_fl`, `GC_reclaim_generic`) another 10 to 25 percent. MLton
allocates by bumping a pointer, and collects a small nursery. The share of each profile's samples in allocation and
collection (libgc, its thread lookup, and clearing new memory), and in the causes of §3.4 and §3.5:

| Benchmark | Allocation and collection | Thread-local access | `_setjmp` | stdio locking |
|---|--:|--:|--:|--:|
| tailmerge | 90% | | | |
| ratio-regions | 87% | | | |
| logic | 81% | | | |
| wc-scanStream | 77% | | | |
| mandelbrot | 75% | | | |
| zebra | 73% | | | |
| hamlet | 70% | | | |
| peek | 69% | | | |
| barnes-hut | 65% | | | |
| knuth-bendix | 61% | 9% | 4% | |
| count-graphs | 56% | 5% | 3% | |
| boyer | 50% | 8% | 4% | |
| imp-for | 50% | | | |
| mpuz | 49% | | | |
| checksum | 28% | | | |
| pidigits | 12% | | | |
| flat-array | | | 70% | |
| output1 | | | | 93% |
| wc-input1 | | | | 85% |
| smith-normal-form | | | | |

This is the largest single cost in the suite, in the middle of the table (hamlet, logic, barnes-hut) as much as at
its end.

- **A per-size free-list cache in the runtime** (tried): `quest_alloc` pops an object from a list for its size class
  (16-byte granules up to 256 bytes), refilled by `GC_malloc_many`, which libgc provides for this; only larger
  objects call `GC_malloc`. The common case becomes a few inline instructions. Measured (count, seconds before and
  after): peek 12, 89.6 to 53.5; zebra 8, 34.8 to 26.4; wc-scanStream 4096, 102.9 to 75.7; tailmerge 3072, 29.6 to
  21.0; ratio-regions 192, 2.95 to 2.05; knuth-bendix 384, 44.1 to 33.6; mandelbrot 1, 17.7 to 11.6; imp-for 512, 32.5
  to 27.6; nucleic 1024, 9.6 to 8.7. The cache must be per thread if Quest gains threads, and its objects are kept
  alive until used.
- Linking libgc statically removes the stubs. A generational or bump-allocating collector is the larger step that
  would close the rest of the gap.

### 3.2. Local functions allocate their closures, and call themselves through them

A local function that captures variables is a heap-allocated environment plus a heap-allocated closure, created each
time its definition is evaluated, even when it is only ever called directly and never escapes. mandelbrot creates one
for its innermost loop at every point of the grid; checksum and md5 create one for a three-line helper at every word
read; imp-for's `forLoop` allocates three objects each call. And a recursive local function calls itself through its
own closure (`((T (*)(...))(l_loop->fn))(l_loop->env, ...)`), so clang cannot turn the recursion into a loop.

- **Non-escaping closures on the stack, or lambda-lifted** (tried by hand on mandelbrot): with the environment and
  closure of `loop3` on `loop2`'s stack, mandelbrot at count 1 went from 18.1 to 11.2 seconds. Lambda lifting (passing
  the captured variables as arguments) does the same without the stack frame.
- **Self tail calls of known functions as jumps** (tried by hand on mandelbrot): with the stack closure, `loop2`'s
  tail call to itself was no longer a tail call (the closure's address is taken), so each point added a stack frame;
  compiling the self tail call as a jump to the top of the function took it from 11.2 to 3.7 seconds (MLton: 1.47).
  The IR knows which calls are calls of the function itself; making them direct calls (`qf_loop(env, ...)`) already
  lets clang make the loop when nothing else stands in the way, and a jump does it always. Calling the function
  directly alone, with the heap closure, gained 4 percent.
- **One allocation per closure**: the closure and its environment can be one object (the code pointer as the
  environment's first word), halving closure allocations everywhere.

### 3.3. Nothing is inlined across modules

The library's small operations (`word.add`, `word.andBits`, `word.shift`, `ascii.val`, `string.getChar`, `real.int`)
are calls into other translation units, often two deep (`qv_word_shift` calls `quest_word_shift_val`), and a function
exported by a module is called through its closure in a global (`qv_util__maybe_none` calls `g_none_3->fn`). checksum
makes about eight calls per byte. Building a whole program and the runtime with `-flto` (tried): md5 at count 1 went
from 33.1 to 19.8 seconds, checksum at count 64 from 7.7 to 5.4. Defining the primitive operations as `static inline`
functions in the runtime header, and calling an imported module's functions directly rather than through their
closures, would get most of this without LTO. Quest has no inliner of its own, which also hurts higher-order code
such as imp-for, where MLton inlines `forLoop` and its arguments into straight loops.

**Done in part (ABI 50, and 51 for the table):** the self-hosted compiler now calls a standard library function that its
module defines as an external C function directly, from a table of them built into the compiler, rather than through the
module's wrapper and closure, and the word module's primitives are `static inline` in the runtime header
([c-representation.md](c-representation.md) §6.2). Measured against the compiler before it, alternately, at a tenth of
the suite's counts on a loaded machine (two runs each):

| Benchmark | Before (s) | After (s) |
| --- | --: | --: |
| md5 | 32.3, 34.0 | 9.5, 9.6 |
| checksum | 167.4, 163.6 | 74.3, 67.5 |
| psdes-random | 61.5, 74.8 | 33.5, 26.9 |
| DLXSimulator | 14.1, 14.1 | 14.9, 13.3 |

md5 gained more than LTO gave it. The compiler's own build (`-j 8`, from nothing) went from 37 and 36 seconds to 26
and 26. Calls of exported Quest functions (`qv_util__maybe_none`) still go through closures, and nothing is inlined
that is not a runtime primitive.

### 3.4. Character I/O locks the stream for every character

`reader.getChar` and `reader.more` call `fgetc`, and `writer.putChar` calls `fputc`, each of which locks and unlocks
the stream (and reads `errno`): two thirds of wc-input1's and output1's samples. Using `getc_unlocked` in the reader
(tried) took wc-input1 at count 2048 from 42.5 to 8.5 seconds, about twice MLton's time. `putc_unlocked` in the
writer should do the same for output1.

### 3.5. Each try costs a `_setjmp`

Since `7551249b`, a try no longer makes system calls, but `_setjmp` saves every callee-saved register, through a dyld
stub. flat-array has a try in its innermost loop and spends 69 percent of its time in `_setjmp`; knuth-bendix, boyer,
and model-elimination raise and catch constantly. Options:

- A smaller jump buffer saved inline (the frame and stack pointers and the resume address, letting the compiler save
  only the registers live across the try): clang's `__builtin_setjmp` does this, but not for arm64 (tried), so it
  would be a few lines of assembly per target.
- Not installing a handler when the body cannot raise, and compiling a raise whose handler is in the same function as
  a jump (which inlining, §3.3, would make common).
- The exception state is `_Thread_local`, which on macOS is a call to `_tlv_get_addr` at every try and raise (7
  percent of knuth-bendix's samples). With plain globals (tried): knuth-bendix 44.3 to 40.1 seconds, boyer 10.9 to
  10.1, model-elimination 47.2 to 46.1. Quest programs have one thread.

### 3.6. Payload-free option cases allocate

`option none of T end` allocates an object holding only its tag every time (`maybe.none` in peek and zebra, `nil` in
every list). A case with no payload could be one shared constant per option type, if nothing observes the identity of
an option value. *Done* in part (2026-11-01, [extensions.md](extensions.md), "Options as Values", §8): such cases are
constants compared by case; `maybe.some`'s box ([option-values.md](option-values.md)) remains.

### 3.7. Arbitrary-precision integers are slow in the suite's library

pidigits (43 times MLton's time) and smith-normal-form (190 times) spend almost all their time in `support/intinf`,
the suite's own bignums in Quest: base 10^9 limbs in arrays of 64-bit `Int`, every result a new array. MLton's
`IntInf` is GMP, with 64-bit limbs and hand-written loops, and keeps values that fit in a word unboxed, so most of
smith-normal-form's arithmetic never reaches GMP. The generated loops are already tight (clang divides by the base by
multiplying by its reciprocal: making `base` a literal changed nothing, tried); the gap is the representation. A
native bignum in the runtime (GMP, or 32-bit limbs with 64-bit intermediate products) with a small-value fast path
would close most of it, for these two benchmarks only. *Done* differently (2026-11-04, §15): the library's
`util/bignum`, in Quest on 64-bit limbs with `word.mulHi`, replaced `support/intinf`, and the two programs take 14 and
17 times MLton's time through C.

### 3.8. Not opportunities

- Real arithmetic checks each result for NaN; removing the checks from mandelbrot's loops changed nothing (tried).
- Top-level immutable bindings are C globals, but clang folds a global stored only with a constant (§3.7).

### 3.9. The interpreters

Neither interpreter implements tail calls, and both stop a program that has more than 1000 calls active with
`stack.overflow` (`MAX_CALL_DEPTH`, `primitives.maxCallDepth`), as a portable stand-in for the native stack. The
conversions keep the originals' recursive loops, so most of the suite overflows when interpreted (§2.4). Running the
suite in an interpreter needs tail calls there, or a much deeper limit. When the baseline was taken, both interpreters
also mis-evaluated a function whose type parameters are followed by an empty value-parameter list (`let f(A::TYPE)():
Int = 3`, called as `f(:Int)()`), which stopped hamlet, mlyacc, model-elimination, and vliw (the tables' "type
application bug"). Since that was fixed, hamlet, mlyacc, and vliw overflow in both interpreters, and model-elimination
reaches the 10-minute timeout.

### 3.10. The conversions

Three conversions parsed hexadecimal word constants from strings each time they ran (`hex("d76aa478")`), where MLton
folds the literal at compile time; md5 spent three quarters of its time parsing them (52.8 times MLton's time, 12.7
after `47b5a20c` wrote them in decimal). peek's original keeps a property list as a list of exceptions, each declaring
a fresh exception constructor; Quest's exceptions are not values a list can hold, so the conversion uses closures that
fill a cell instead, which allocates more than the original does.

## 4. The backends compared (2026-10-30)

Linear scan ([arm64.md](arm64.md) §3.8) asked for dated run and compile times for both backends; these are the
first. They show what the arm64 backend's code cost before interval splitting (§3.8 of arm64.md, as built: one
range per value, spilled whole; promotion and tail calls in).

### 4.1. How they were taken

The machine, MLton, clang, and collector are §2.1's. Quest was `074bc251` (ABI 55, native `try` for arm64, the C
backend still `_setjmp`); the conversions were §2.1's. Both systems are `./quest`, the conversions built with
`--backend c` and `--backend arm64`, at a quarter of MLton's counts, **one run each** (not three), the C pass first
and then arm64, one benchmark at a time. The machine was not otherwise busy, but this session was editing files
meanwhile. MLton's times are the 2026-10-28 baseline's (§2), which were taken at the same counts. The times are in
`benchmarks/mlton/baselines/2026-10-30/`:

```bash
cd benchmarks/mlton
./run.py time --clean --backend c --scale 0.25 --timeout 1800 --results new/quest-c.jsonl
./run.py time --backend arm64 --scale 0.25 --timeout 1800 --results new/quest-arm64.jsonl
./run.py report baselines/2026-10-28/compiled.jsonl new/quest-*.jsonl --exclude fib,tailfib,tak,tensor
```

### 4.2. Summary

| System | Geometric mean of time / MLton's | Run time, all 46 | Build time, all 46 |
|---|---|---|---|
| `./quest --backend c` | **5.24**; 6.12 without fib, tailfib, tak, and tensor | 44.0 min | 31.1 s (median 0.3 s) |
| `./quest --backend arm64` | **11.62**; 11.77 without them | 80.8 min | 27.4 s (median 0.3 s) |
| `./quest` on 2026-10-28 (C, §2.2), for comparison | 5.05; 6.49 without them | | |

The arm64 backend's programs take 2.22 times as long as the C backend's (geometric mean of the ratios, from 1.11 for
imp-for and output1 to 32.6 for tailfib). Its builds take 0.93 times as long. Both build times include compiling the
libraries the program uses: the C build of DLXSimulator, the first, also built the units every later build reused
(2.1 s, against 1.9 s for arm64). Most of a build is the front end and linking, so the backend's share is small in
either.

Where arm64 is furthest behind is where clang does the most:

- **fib, tak, tailfib, even-odd** (4.8 to 32.6 times the C backend): small recursive functions, which clang inlines,
  unrolls, or turns into loops.
- **md5, psdes-random, checksum** (3.5 to 6.3): word arithmetic in tight loops, where every value spilled is a load
  and a store, and clang's instruction selection (shifts and rotates folded into operands) does more per
  instruction.
- **smith-normal-form, peek, pidigits** (1.4 to 2.0): dominated by the arbitrary-precision library and allocation
  (§3.1, §3.7), so the backend matters less.

The C backend's 5.24 against 5.05 on 2026-10-28 is mixed:

- **Faster:** md5 (0.29 of its earlier time, from §3.10's decimal constants), psdes-random (0.44), checksum (0.45),
  string-concat (0.61), and tyan (0.83) are faster since then.
- **Slower:** tailfib went from 0.01 s to 0.26 s, which is most of the topline's change. fib, tak, flat-array, and
  even-odd are 1.3 to 1.5 times slower.
- **The rest:** the other 36 are within 15 percent of their earlier times, which one run per benchmark cannot tell
  from noise.

Without the four benchmarks §1.3 sets aside, the mean improved, from 6.49 to 6.12.

The arm64 numbers are the baseline against which interval splitting, rematerialization, and allocation in `try`
functions (arm64.md §3.8) are to be measured.

### 4.3. With splitting

Quest was `22e03678`: interval splitting, rematerialization, and allocation in `try` functions (arm64.md §3.8, with
splitting), with an edge's cycles of moves broken through `x10` rather than a copy area. The run was taken as in
§4.1, after `--clean`, with the machine otherwise idle. Its times are
`benchmarks/mlton/baselines/2026-10-30/quest-arm64-split.jsonl`.

| System | Geometric mean of time / MLton's | Run time, all 46 |
|---|---|---|
| `./quest --backend arm64`, before splitting (§4.2) | 11.62; 11.77 without fib, tailfib, tak, and tensor | 80.8 min |
| `./quest --backend arm64`, with splitting | **11.01**; 11.13 without them | 76.5 min |

Its programs take 0.94 times as long as before splitting, and 2.09 times as long as the C backend's (from 2.22). Its
builds took 24.9 s for all but the first, DLXSimulator, whose 57.5 s included rebuilding `./quest`'s stages.

- **Faster:** flat-array (0.49 of its time before), matrix-multiply (0.70), tailfib (0.79, the cycle of moves in its
  loop now five register moves, not eight memory operations), boyer and hamlet (0.81), count-graphs (0.89),
  psdes-random (0.90).
- **The rest:** within 10 percent of before. tak is the slowest relative to before (1.10).

The furthest behind C are as in §4.2: tailfib (26.1 times C), fib (17.6), tak (10.8), md5 (6.0), even-odd (4.8), and
the word-arithmetic loops vector32-concat, checksum, and psdes-random (3.5 to 3.7).

A first run of this measurement, at `b75ee0fa`, overlapped a release build in another worktree. It showed imp-for,
tailfib, checksum, and logic 1.35 to 1.74 times slower than before splitting. Their code was unchanged, and an A/B
of eleven benchmarks at `--scale 0.05` on an idle machine put all but three within 3 percent. Measurements need the
machine to themselves.

## 5. Choosing the default backend (2026-10-30)

Step 12 asks for the measurements from which the default backend is decided. The user decides; this section gives the
numbers and a recommendation. Releases are built with C until then.

### 5.1. The compiler as each backend compiles it

`./quest` with `QUEST_BACKEND=c`, `ssac`, or `arm64` builds stage 2, the compiler, through that backend (stage 1, the
seed's, compiled by C). Each stage 2 then compiled the driver (`questlang/driver/main.quest`, 124 units) from an empty
build directory, once each, on an otherwise idle machine, at `e804792b` with the SSA's join fix:

| Compiler compiled by | Through arm64, `-j 8` | Through arm64, `-j 1` | Through C, `-j 8` | Against C's compiler |
|---|--:|--:|--:|--:|
| `c` (clang `-O2` on the C printer's C) | 24.6 s | 52.6 s | 26.4 s | 1 |
| `ssac` (clang `-O2` on the SSA's C) | 35.4 s | 64.7 s | 37.8 s | 1.23–1.44 |
| `arm64` (the native backend) | 53.6 s | 82.9 s | 59.2 s | 1.58–2.24 |

The output's backend matters little (the C output adds clang's time in every row alike); what differs is the compiler
running. Every stage 2 writes the same artifacts as the C-compiled one (the fixed point, which `tools/check` checks
through each backend), so the rows differ only in speed.

### 5.2. Programs

From §4, at a quarter of MLton's counts, the MLton suite's programs compiled by the arm64 backend take 2.09 times as
long as by the C backend (geometric mean against MLton 11.01 and 5.24). Building them takes 0.93 times as long: most
of a build is the front end and linking. The suite through `ssac` is yet to be timed (an overnight job, the
measurement step 15 needs).

### 5.3. Recommendation

**Keep `c` the default for now.** The arm64 backend's code runs about twice as long as clang's, in the compiler and in
the suite, and saves only a few percent of build time, while `c` is the backend everything else is measured against. The
gap is the instruction selection, jump threading, and inlining that clang does and arm64.md §6 and the
backend-improvements plan (since done; arm64.md §3.17) listed. Revisit when arm64's code is within about 1.2 times C's
on both measures, or when building time matters more than running time (the REPL, the test suite's many small programs),
where arm64's builds skip clang's compile of the C: an assembly unit needs only the assembler.

## 6. The backend improvements (2026-10-31)

The backend-improvements plan's steps 8 to 10 (the arm64 backend's instructions as data ([arm64.md](arm64.md) §3.17),
the allocator on machine functions, the compiler's speed, and the `val` type) and the arm64 backend before register
allocation, measured as one batch at the plan's end.

### 6.1. How they were taken

Each version was built in a detached worktree of its own: step 8's base `c08fea94`, after step 8 `373ecce3`, after
each of step 9's two changes `0e8ca0cd` and `20f0d4ed`, the plan's end `88d7970b`, and the arm64 backend before
register allocation, `2aad8279` and `73e7aaf9` (tail calls, and linear scan's first commit), each with the builder's
part of `59743032` (the Ok-argument fix) applied. Each job waited until no test suite, check, or other benchmark ran
and the load average had been under 6 for two minutes. The suite's runs are `run.py time --clean --scale 0.25
--timeout 1800`, one run each, against the 2026-10-28 baseline's MLton times; this session was editing and testing
meanwhile, at two jobs, during the last three suites, and `tools/check` (the whole machine) overlapped `73e7aaf9`'s
from tsp on, so its times are high. The times are in `benchmarks/mlton/baselines/2026-10-31/`.

### 6.2. Compile times

The C-built stage 2 of each version building the driver through arm64 from an empty build directory (`-j 8`, three
runs), and printing the driver's SSA (`--stop-after ssa --dump-after ssa`, one unit at a time):

| Version | Driver through arm64 (s) | The driver's SSA printed (s) |
|---|--:|--:|
| step 8's base, `c08fea94` | 25.5, 26.5, 26.0 | 11.1, 10.8, 10.5 |
| after step 8, `373ecce3` | 23.7, 23.8, 29.2 | 12.1, 11.8, 11.8 |
| step 9: the allocator's search by position, `0e8ca0cd` | 22.4, 23.1, 22.8 | 10.4, 10.1, 10.2 |
| step 9: the printer's lists joined, `20f0d4ed` | 23.9, 22.5, 22.6 | 10.2, 10.4, 10.4 |
| the plan's end, `88d7970b` | 22.0, 22.0, 22.2 | 10.2, 10.2, 10.0 |

- **Step 8** saved about 2.5 s of the build (its 29.2 s run aside), but printing the SSA got about 1 s slower.
- **Step 9's allocator change** pays: about 1 s of the build and 1.7 s of printing, which more than takes back step
  8's. **Its printer change** is within noise either way, and stays as the clearer code.
- **The compiler as arm64 compiles it** (`QUEST_BACKEND=arm64`, building the driver through C, `-j 8`) took 56.1,
  56.1, and 56.0 s at step 8's base and 52.9, 53.5, and 53.3 s at the end: its code is about 5 percent faster.

### 6.3. Programs

| System | Geometric mean of time / MLton's | Over the 42 all finished | Run time |
|---|--:|--:|--:|
| arm64 before register allocation, `2aad8279` | 21.26 (40) | 21.95 | 118.9 min (41) |
| arm64 before register allocation, `73e7aaf9` (loaded, §6.1) | | 25.11 | 136.6 min (42) |
| arm64 at step 8's base, `c08fea94` | 11.33 | 10.33 | 79.5 min |
| arm64 at the plan's end, `88d7970b` | **10.22** | 9.28 | 75.6 min |
| ssac at the plan's end, `88d7970b` (first timed) | **7.42** | 6.58 | 65.2 min |
| C, `074bc251` (§4.2), for comparison | 5.24 | | 44.0 min |

Before register allocation, lexgen, model-elimination, and zebra do not compile (their `else with` handlers came
later) and smith-normal-form timed out.

- **Steps 8 to 10 made arm64's programs 0.90 times as long** (geometric mean of the ratios, all 46): tailfib 0.63,
  even-odd 0.67, tsp 0.74, flat-array and life 0.77, fib 0.84, and most of the rest 0.85 to 0.95. Four got slower:
  string-concat 1.38, md5 1.11, checksum 1.06, and imp-for 1.00, the word-arithmetic and string loops, where
  selection now folds immediates and offsets the old code did not but the allocator spills differently.
- **Register allocation** (linear scan, arm64.md §3.8, with exceptions and tail calls after it) made them 0.42 times as
  long as at `2aad8279`, over the 40 both finished.
- **ssac**, the SSA printed as C for clang, takes 0.73 times arm64's time at the end and 1.42 times C's: clang
  inlines and turns into loops what neither the SSA nor arm64 does (fib 12.6 times ssac's in arm64, tailfib 18.4,
  tak 8.6, even-odd 3.5), while arm64 is ahead on flat-array (0.46 of ssac's time, its try without `_setjmp`).
- **Against C**, arm64 is furthest behind on md5 (6.7), checksum and psdes-random (3.6), vector32-concat (3.4), and
  the small recursive functions; the inliner ([ir.md](ir.md) §8.6) is to close most of the gap that is not
  instruction selection.

## 7. The inliner (2026-10-31)

The inlining plan's steps 1 to 6 ([ir.md](ir.md) §8.6 and §8.7; exported functions called directly, the simplifier,
inlining, contification, and in part unboxed tuple results and inlining across a whole program's modules), measured at
`36244e7b` against the last measurements before them: C at `074bc251` (§4.2) and arm64 at `88d7970b` (§6.3).

### 7.1. How they were taken

The machine, MLton's times, and the counts are §4.1's: `run.py time --clean --scale 0.25 --timeout 1800`, one run
each, with `--backend c`, then `--backend c --whole-program`, then `--backend arm64`. Each job waited until no test
suite, check, or other benchmark ran and the load average had been under 6 for two minutes, and nothing else ran
meanwhile. The times are in `benchmarks/mlton/baselines/2026-10-31/`: `quest-c-36244e7b.jsonl`,
`quest-c-whole-36244e7b.jsonl`, `quest-arm64-36244e7b.jsonl`, and `compile-times.jsonl`.

### 7.2. Programs

| System | Geometric mean of time / MLton's | Without fib, tailfib, tak, and tensor | Run time, all 46 |
|---|--:|--:|--:|
| C, `074bc251` (§4.2) | 5.24 | 6.12 | 44.0 min |
| C, `36244e7b` | **3.74** | 4.24 | 35.9 min |
| C, `36244e7b`, `--whole-program` | **3.71** | 4.21 | 35.5 min |
| arm64, `88d7970b` (§6.3) | 10.22 | 10.56 | 75.6 min |
| arm64, `36244e7b` | **7.79** | 7.95 | 60.4 min |
| ssac, `88d7970b` (§6.3), for comparison | 7.42 | 8.94 | 65.2 min |

- **C's programs take 0.71 times as long** (geometric mean of the ratios, all 46). Most gained where the inliner
  removes a higher-order or polymorphic call in a loop and contification makes the loop: imp-for 0.09 of its time
  before, mandelbrot 0.15, mpuz 0.20, matrix-multiply 0.23, checksum 0.32, psdes-random 0.39, life 0.47, and zern,
  hamlet, ratio-regions, count-graphs, and md5 0.55 to 0.62. Only zebra got slower (1.14).
- **arm64's take 0.76 times as long,** the same benchmarks gaining most (imp-for 0.17, mpuz and mandelbrot 0.29,
  matrix-multiply 0.46), DLXSimulator the one slower (1.15). arm64 now runs about as fast as ssac did at `88d7970b`
  (1.05 times its time, and ahead without the four, 7.95 against 8.94), and still 2.08 times C's: the small recursive
  functions (tailfib 16.8, fib 8.7, tak 7.4), whose recursion neither inlining nor contification removes and clang
  does, and the word arithmetic (md5 7.1, checksum 6.7, psdes-random 5.2), which is instruction selection.
- **The whole-program build** takes 0.99 times as long as separate compilation, which is within noise for all but
  two. even-odd takes 0.61 of the separate time, its mutually recursive functions in one unit with the library's.
  ratio-regions takes **1.68 times as long** (12.1 s against 20.3 s, and 12.4 and 12.2 against 19.2 and 19.5 in two
  reruns), the time it took before the inliner. It allocated 46.6 million objects against 29.3 million: built whole,
  contification made `raoRatioRegion`, called once and never calling itself, a loop at the top level before the
  inliner could splice it in, so its matrices were the loop's variables rather than the module's globals, and the
  closures `preflowPush`'s inner loop passes to `lists.app` captured them, allocating an environment, a closure, and
  an adapter each per iteration rather than using static closures. Contification now leaves a function that never
  calls itself and is not recursive to the inliner ([ir.md](ir.md) §8.6, contification); `49452427` had already hidden
  it here. These whole-program times predate `49452427`, which makes a whole program's abstract types transparent so
  that the library's members inline across them; they are to be retaken.
- **Building** the 46 took 42.1 s through C (median 0.4 s), 72.1 s whole (median 0.9 s: each build compiles the
  library with the program), and 34.4 s through arm64.

### 7.3. Compile times

Each commit's C-built stage 2 building its own commit's driver (`questlang/driver/main.quest`) from an empty build
directory, `-j 8`, three runs, alternating:

| Compiler | Through C (s) | Through arm64 (s) |
|---|--:|--:|
| `88d7970b`, before the inliner | 27.0, 25.9, 25.7 | 21.4, 21.4, 21.6 |
| `36244e7b` | 27.1, 26.9, 26.9 | 22.5, 22.5, 22.5 |

The optimizer costs about 1 s of the build, 3 to 5 percent, which includes compiling its own modules: the later
driver is larger.

## 8. Options as values (2026-11-01)

Options as values ([extensions.md](extensions.md); an option of a case without components is compared by its case
and is a shared constant; a single-word option is compared by its component) and the C printer's two payload fixes
(an option made from its payload tuple's components, and `o!tag.field` read in place,
[c-representation.md](c-representation.md) §5.3), measured through C against the commit before them. What they buy is
allocation: §3.6's objects for `nil` and `none`, and the tuples copied into and out of options' payloads.

### 8.1. How they were taken

As §7.1: `run.py time --clean --scale 0.25 --timeout 1800 --backend c`, one run each, each job waiting until no test
suite, check, or other benchmark ran and the load average had been under 6 for two minutes. Each compiler was its
commit's stage 2 with its own `lib/` and `runtime/` (`QUEST_HOME`), so that all ran in one tree:

- **A,** `c62476f7`, main before the change (contification and narrowed globals, §7.2).
- **B,** steps 1 and 2 on A (`1a5f1b55`, pushed rebased as `83dbd27a`).
- **C,** B with the C printer's fixes (`7ef34e42`, pushed rebased as `193a3f11`).

A, B, and C separately, then A and C with `--whole-program`. The commits were measured before being rebased onto
`3fc7b821` and later, so none of these include that commit's traceback cache (§8.3). The times are in
`benchmarks/mlton/baselines/2026-11-01/`, named by the commits measured: `quest-c-c62476f7.jsonl`,
`quest-c-1a5f1b55.jsonl`, `quest-c-7ef34e42.jsonl`, `quest-c-whole-c62476f7.jsonl`, and
`quest-c-whole-7ef34e42.jsonl`.

### 8.2. Programs

| System | Geometric mean of time / MLton's | Without fib, tailfib, tak, and tensor | Run time, all 46 |
|---|--:|--:|--:|
| C, A | 3.86 | 4.38 | 36.9 min |
| C, B | 3.64 | 4.12 | 34.2 min |
| C, C | **3.50** | 3.94 | 31.7 min |
| C, A, `--whole-program` | 3.65 | 4.12 | 35.3 min |
| C, C, `--whole-program` | **3.41** | 3.83 | 31.3 min |

Times as a fraction of A's (below 1 is faster), for the benchmarks that moved most:

| Benchmark | B | C | C whole / A whole |
|---|--:|--:|--:|
| peek | 0.73 | **0.41** | 0.40 |
| ratio-regions | 0.67 | 0.66 | 0.70 |
| wc-scanStream | 0.95 | 0.68 | 0.70 |
| zebra | 0.81 | 0.72 | 0.72 |
| boyer | 0.88 | 0.80 | 0.90 |
| model-elimination | 0.81 | 0.80 | 0.88 |
| hamlet | 0.89 | 0.82 | 0.85 |
| mlyacc | 0.84 | 0.82 | 0.95 |
| knuth-bendix | 0.84 | 0.83 | 0.85 |
| logic | 0.85 | 0.83 | 0.93 |
| **geometric mean, all 46** | **0.94** | **0.91** | **0.94** |

- **Steps 1 and 2 take 0.94 times as long.** The gains are in programs built on lists and optional values, where
  `nil` and `none` no longer allocate: ratio-regions went from 29.3 million allocations to 22.4 million, and
  knuth-bendix, model-elimination, logic, mlyacc, boyer, and hamlet gained 11 to 19 percent. None got slower
  outside noise (tailfib, at 0.25 s, 1.10; tailmerge 1.06; tsp 1.04).
- **The C printer's fixes take a further 0.96,** almost all of it in three programs: peek (0.57 of B's time; 960
  million allocations to 400 million), wc-scanStream (0.71), and zebra (0.89), which read options' payloads in their
  inner loops. Nothing got slower outside noise (vector32-concat 1.08 separately, 0.92 whole).
- **Whole programs** gain about as much (0.94). At A, building whole takes 0.94 times as long as building separately,
  and ratio-regions is no longer slower whole (§7.2: 11.4 s against 12.8 s).
- **What remains** is mostly `maybe.some`, which step 3 (deferred) would remove: at B, 800 million of peek's 960
  million allocations and 168 million of zebra's 341 million were in `maybe.some`.

### 8.3. zebra and the traceback cache

zebra raises and catches exceptions constantly, and is what showed that attributing a traceback's frames had become
slow: with line tables in the binary (arm64.md §3.16), `dladdr` scanned every symbol, the debug map's entries
included, for each frame of each raise. `3fc7b821` caches each return address's function start. Measured alone,
as §8.1, with that commit's compiler (A plus the cache and a documentation commit):

| Compiler | zebra (s) | / MLton's |
|---|--:|--:|
| A, `c62476f7` | 76.6 | 30.8 |
| B | 61.8 | 24.8 |
| C | 54.9 | 22.1 |
| `3fc7b821` | **44.4** | **17.8** |

The cache alone takes zebra to 0.58 of A's time, more than options as values do (0.72). They are independent (one
removes allocations, the other the cost of each raise), so with both zebra should take about 0.42 of A's time. The
time is `quest-c-zebra-3fc7b821.jsonl`.

## 9. Escape analysis (2026-11-01)

Escape analysis ([ssa.md](ssa.md) §4.2), which makes the allocations that do not leave their function stack
slots in the SSA, measured by allocations rather than time: the allocations are what it changes, and its effect on
them is large and exact, so the suite's times are left to a later retake. Counted by `allocations.py` at `--scale
0.25` (ratio-regions n=384, peek n=48, zebra n=16), with `eb84b59b`'s compiler, the pass skipped
(`QUEST_SKIP_PASSES=escape`) and run; C's counts, which the pass does not change, are with the C printer's payload
fixes (§8).

| Benchmark | ssac and arm64, without the pass | With it | Ratio | C, with the C printer's fixes |
|---|--:|--:|--:|--:|
| peek | 23.04 billion | **9.60 billion** | 0.42 | 9.60 billion |
| zebra | 2.72 billion | **1.12 billion** | 0.41 | 1.38 billion |
| ratio-regions | 811 million | **782 million** | 0.96 | 811 million |

`ssac` and `arm64` allocate exactly alike, with the pass and without it, as they share the SSA.

- **The payload tuples are gone:** `maybe.unwrap`'s (3.84 billion of peek's, 660 million of zebra's), half of
  `maybe.some`'s (the tuple it copies into the option), and half of `lists.cons`'s, `append`'s, `fromArray`'s,
  `relabel`'s, and `enqueue`'s.
- **Against the C printer's fixes,** the SSA allocates no more on any of the three, and less on zebra (1.12 billion
  against 1.38), since the pass also removes the payload tuples of `cons` and `append`, which the fixes' patterns do
  not match ([c-representation.md](c-representation.md) §5.3).
- **What remains** in peek and zebra is mostly `maybe.some`'s box (9.6 billion and 672 million), which escapes by
  being returned, and which [option-values.md](option-values.md) (deferred) would remove; in ratio-regions,
  90 percent is `preflowPush`'s 706 million, which the pass does not touch.

## 10. The JIT (2026-11-01)

The time the JIT ([jit.md](jit.md)) takes to compile, load, and run an input, against the interpreter's time to
run it, measured on the REPL transcripts and on four programs, with a stage 2 the C backend built.

### 10.1. How they were taken

Each command was run three times, in a scratch directory, and the least wall time kept; the time of an empty session
(`quest --jit -i` and `quest -i` with no input: 8 ms and 7 ms) is subtracted. Inputs are counted as the transcript's
lines that begin a phrase, roughly. Another worktree's tests were running on the machine, so the times are rough.

### 10.2. The transcripts

| Transcript | Inputs | JIT (ms) | Per input (ms) | Interpreter (ms) |
|---|---:|---:|---:|---:|
| args | 2 | 3 | 1.5 | 3 |
| declared_modules | 8 | 6 | 0.7 | 1 |
| earlier_function_error | 5 | 6 | 1.3 | 1 |
| incomplete_at_end | 2 | 1 | 0.4 | 0 |
| multiline | 12 | 7 | 0.6 | 3 |
| phrases | 11 | 6 | 0.5 | 1 |
| rethrow | 5 | 8 | 1.5 | 2 |
| rollback | 15 | 10 | 0.7 | 1 |
| syntax_errors | 6 | 1 | 0.2 | 1 |

An input takes 0.2 to 1.5 ms through the JIT: lowering, the passes, the SSA, selection and allocation, encoding,
loading, and running, the first three dominating. That is several times the interpreter's time for these small
inputs, and well under what a person notices.

### 10.3. Programs

| Program | Lines | JIT (ms) | Interpreter (ms) |
|---|---:|---:|---:|
| `language/thunks` | 98 | 35 | 11 |
| `language/cardelli_operators` | 48 | 6 | 1 |
| `03_functions_closures` | 11 | 2 | 1 |
| `stdlib/sort_operations` | 147 | 36 | 39 |

A file is one input, so the JIT compiles all of it before running it. It costs more than interpreting a program
that does little (`thunks` compiles many generic functions and their thunks), and about the same where the program
does some work (`sort_operations`); a program that runs long would gain what compiled code gains over the
interpreter. Whether the JIT becomes the default is decided from these (jit.md §7).

## 11. Every backend, and the inliner's settings (2026-11-02)

The whole suite through every backend at one commit, `9a08223f` (ABI 63), after the arm64 performance review's first
two batches ([arm64-performance-review.md](arm64-performance-review.md) §4), escape analysis (§9), and options as
values (§8); the six programs that review follows, timed again on an idle machine; and the inliner's settings, each
varied alone ([inlining.md](inlining.md) §1).

### 11.1. How they were taken

As §7.1: `run.py time --clean --scale 0.25 --timeout 1800`, one run each, with `--backend c`, `--backend c
--whole-program`, `--backend ssac`, `--backend arm64`, `--backend arm64 --whole-program`, and `--jit`, in that order,
each waiting until the load average had been under 6 for two minutes. Another worktree's work kept the load at 1.1 to
2.2 throughout, on one or two of the machine's cores. The compiler was the release cut at `9a08223f`, a normal (not
whole-program) build, so the JIT ran in a driver the C backend built; its times include compiling each program, which
it does on every run. Then the six through `tools/perf/variants.py` and `tools/perf/timeit.py --rounds 5`, and the
inliner's settings through C at `--scale 0.05`, each with `QUEST_INLINE` set and `--clean`. The times are in
`benchmarks/mlton/baselines/2026-11-02/`: `quest-c-9a08223f.jsonl`, `quest-c-whole-9a08223f.jsonl`,
`quest-ssac-9a08223f.jsonl`, `quest-arm64-9a08223f.jsonl`, `quest-arm64-whole-9a08223f.jsonl`,
`quest-jit-9a08223f.jsonl`, and `quest-c-inline-SETTING-9a08223f.jsonl`.

### 11.2. Programs

| System | Geometric mean of time / MLton's | Without fib, tailfib, tak, and tensor | Run time, all 46 |
|---|--:|--:|--:|
| C, `7ef34e42` (§8.2) | 3.50 | 3.94 | 31.7 min |
| C | **3.54** | 4.00 | 31.7 min |
| C, `--whole-program` | **3.34** | 3.75 | 30.8 min |
| ssac, `88d7970b` (§6.3) | 7.42 | 8.94 | 65.2 min |
| ssac | **3.48** | 4.08 | 37.9 min |
| arm64, `36244e7b` (§7.2) | 7.79 | 7.95 | 60.4 min |
| arm64 | **5.17** | 5.30 | 44.9 min |
| arm64, `--whole-program` | **4.86** | 4.97 | 41.0 min |
| JIT | **6.11** | 6.39 | 46.6 min |

Each backend's time against C's (below 1 is faster), for the programs furthest from it, and the geometric means:

| Benchmark | C (s) | C whole | ssac | arm64 | arm64 whole | JIT |
|---|--:|--:|--:|--:|--:|--:|
| tailfib | 0.25 | 1.00 | 1.07 | 16.65 | 16.51 | 16.04 |
| fib | 0.74 | 1.02 | 1.05 | 9.08 | 9.12 | 8.86 |
| tak | 0.81 | 1.02 | 1.03 | 7.48 | 7.41 | 7.22 |
| md5 | 17.10 | 0.96 | 3.94 | 6.83 | 5.88 | 3.69 |
| checksum | 49.94 | 0.97 | 3.65 | 6.39 | 4.29 | 4.12 |
| psdes-random | 19.93 | 1.01 | 4.09 | 4.77 | 3.85 | 4.24 |
| even-odd | 1.20 | 0.64 | 1.02 | 3.38 | 3.38 | 3.25 |
| string-concat | 7.03 | 1.00 | 1.36 | 2.78 | 1.73 | 1.99 |
| zern | 5.25 | 0.93 | 0.94 | 2.63 | 2.63 | 2.97 |
| mpuz | 10.10 | 1.01 | 1.13 | 2.01 | 1.84 | 1.99 |
| vector64-concat | 3.50 | 1.03 | 1.02 | 1.80 | 1.80 | 2.44 |
| vector32-concat | 5.13 | 1.12 | 0.99 | 1.77 | 1.79 | 2.20 |
| hamlet | 15.28 | 0.87 | 0.96 | 1.40 | 1.14 | 7.81 |
| ratio-regions | 8.67 | 0.90 | 0.99 | 1.08 | 1.04 | 3.09 |
| flat-array | 64.44 | 0.92 | 3.88 | 1.04 | 1.10 | 1.12 |
| count-graphs | 17.31 | 0.96 | 2.27 | 0.91 | 0.89 | 1.17 |
| boyer | 33.34 | 0.91 | 1.71 | 0.86 | 0.84 | 1.00 |
| tensor | 80.18 | 0.99 | 0.18 | 0.23 | 0.23 | 0.23 |
| imp-for | 5.98 | 1.00 | 0.04 | 0.95 | 0.94 | 0.93 |
| **geometric mean, all 46** | | **0.94** | **0.98** | **1.46** | **1.37** | **1.73** |
| without fib, tailfib, tak, and tensor | | 0.94 | 1.02 | 1.32 | 1.24 | 1.60 |

- **The SSA's backends have caught up.** ssac takes 0.47 of its time at §6.3 and now runs as fast as C (0.98), ahead
  of it on 24 of the 46; arm64 takes 0.66 of its time at §7.2, and 1.46 of C's. C itself is where §8.2 left it.
- **On the six, arm64 is level with C:** the geometric mean of their ratios is 1.04 here, and 1.06 in five rounds
  of `timeit.py` ([arm64-performance-review.md](arm64-performance-review.md) §4, the baseline). The rest of arm64's
  distance from C is in a few programs. Without the four, three (md5, checksum, and psdes-random) are 46 percent of
  it, by the sum of the logarithms of the ratios, and with even-odd, string-concat, zern, and mpuz, 80 percent; the
  other 35 take 1.08 of C's time.
- **md5, checksum, and psdes-random are slow in the SSA, not the code generator:** ssac takes 3.7 to 4.1 times C's
  time on them, as arm64 does 4.8 to 6.8. What the C path keeps and the SSA loses is not yet known (they are word
  arithmetic in loops); fixing it speeds up ssac, arm64, and the JIT alike. flat-array, count-graphs, and boyer are
  slow through ssac only (1.7 to 3.9), and arm64 is faster than C on them.
- **zern, string-concat, mpuz, and the vector concatenations are the code generator's:** ssac takes about C's time
  and arm64 1.8 to 2.8 times it. even-odd (3.4 through arm64, 1.0 through ssac) is a second of mutual tail calls,
  as the four are small recursions that clang transforms; it is to be looked at before being counted with these.
- **Whole programs** take 0.94 of a separate build's time through C and 0.94 through arm64, which gains most where
  the library's members inline into the program's loops: checksum 0.67, peek 0.67, string-concat 0.62, zebra 0.82.
- **The JIT** takes 1.18 of arm64's time (geometric mean), since it compiles the program on each run: hamlet, the
  largest, takes 5.6 times arm64's time, and ratio-regions 2.9. Where the run is long, it is near arm64, and it is
  faster on md5, checksum, and psdes-random (0.54 to 0.89 of arm64's), most likely because their calls into the
  library go to the driver's copies, which the C backend built ([jit.md](jit.md) §3.4).

### 11.3. The inliner's settings

Each of §7's settings ([ir.md](ir.md) §8.6) varied alone from the defaults, the suite's time with each as a fraction
of its time with the defaults (geometric mean of the 46), and the programs that moved more than 8 percent:

| Setting | Default | Time / default's | Programs that moved most |
|---|--:|--:|---|
| `size=0` | 30 | 1.051 | checksum 2.50, md5 1.53, life 1.26, hamlet 1.26 |
| `size=15` | | 1.013 | life 1.79 |
| `size=60` | | 1.008 | |
| `size=120` | | 1.004 | |
| `rounds=1` | 6 | 1.060 | psdes-random 1.57, md5 1.56, life 1.43, matrix-multiply 1.43, mpuz 1.38 |
| `rounds=3` | | 1.007 | life 1.15 |
| `rounds=12` | | 1.002 | string-concat 1.09 |
| `polymorphic=0` | 30 | 1.004 | |
| `polymorphic=60` | | 1.000 | ratio-regions 0.92 |
| `function=0` | 10 | 1.016 | tsp 1.12, vliw 1.11 |
| `function=30` | | 1.034 | peek 1.41, tsp 1.10, ratio-regions 0.88 |
| `constant=0` | 5 | 1.029 | model-elimination 1.29, mpuz 1.10 |
| `constant=20` | | 1.021 | tsp 1.12 |
| `growth=25` | 50 | 1.024 | mlyacc 1.10, hamlet 1.09 |
| `growth=100` | | 0.999 | tailmerge 0.86 |
| `budget=250` | 1000 | 1.006 | |
| `budget=4000` | | 0.999 | ratio-regions 0.91 |

output1, which writes a file, took 1.38 and 1.51 of its time with `constant=0` and `function=30`, which ran while
another worktree's load rose to 3.6, and about its default time with every other setting; it is left out of those
two rows' means.

**The defaults stay.** No setting is faster than them by more than 0.1 percent, so none was retaken at `--scale 0.25`.
Each default is near the best of its range:

- **size (30):** inlining nothing larger than 0 loses checksum's and md5's inner loops, and 15 loses life's (1.79);
  60 and 120 gain nothing, so 30 is where the gains stop, with room either way.
- **rounds (6):** one round leaves the calls that inlining exposes (psdes-random, md5, life, matrix-multiply,
  mpuz); three is nearly enough (life 1.15), and twelve gains nothing, the simplifier having reached its fixed point.
- **polymorphic (30):** neither 0 nor 60 changes the suite's time. The bonus matters only for a callee that a
  closed type argument makes small enough, which in the suite is ratio-regions, gaining 8 percent at 60 and losing
  4 at 0; kept, as it costs nothing.
- **function (10) and constant (5):** both directions are slower. Without them, functions that take a known function
  or constant (tsp's and vliw's iterators, model-elimination's) are not inlined; with three or four times the bonus,
  larger callees are, and peek, tsp, and model-elimination grow and slow.
- **growth (50 percent) and budget (1000):** limits rather than levers: halving the growth costs 2 percent (mlyacc
  and hamlet stop inlining), and doubling it or raising the budget to 4000 changes nothing, so they rarely bind.

## 12. The Jupyter kernel's interrupt checks (2026-11-03)

Under `--kernel`, the code the JIT compiles checks the interrupt flag at each function's entry and loop head
([jupyter-kernel.md](jupyter-kernel.md) §5). Nothing else compiles them, so only a kernel's cells pay. Each of the six
of [arm64-performance-review.md](arm64-performance-review.md) ran as one cell, at `--scale 0.25`'s count, in a fresh
session with the checks and in one with `QUEST_SKIP_PASSES=interrupts`, alternating, three rounds, the best of each.
A cell's time includes compiling the program, so the time of the same cell at a count of 0 was subtracted. The load
average was 3 to 5.

| Program | With checks | Without | Ratio |
|---|--:|--:|--:|
| life | 15.70 s | 15.26 s | 1.03 |
| ray | 19.04 s | 21.08 s | 0.90 |
| mlyacc | 13.51 s | 13.11 s | 1.03 |
| zebra | 28.24 s | 27.69 s | 1.02 |
| nucleic | 10.80 s | 10.61 s | 1.02 |

- **The checks cost 2 to 3 percent** in four of the five. Ray was faster with them, in every round, which nothing
  here explains (code placement, perhaps); taken as noise, the cost is about 2.5 percent.
- **Hamlet can't be measured this way.** Its cell at a count of 0 took 97 to 152 seconds, more than its count adds,
  and varied more than the checks could cost.
- The cost is a cell's alone, and small next to what interrupting without losing the session is worth, so the checks
  stay on in kernel mode.

## 13. The SSA's backends after the review's batches (2026-11-03)

The suite through C, ssac, and arm64 at `42ba562c`, after the arm64 performance review's batches 4 to 7
([arm64-performance-review.md](arm64-performance-review.md) §4): block layout, register-offset and paired loads and
stores, the library's inlined externals as instructions in the SSA and other externals called directly from it, and
value numbering ([ssa.md](ssa.md) §4.1).

### 13.1. How they were taken

As §11.1: `run.py time --clean --scale 0.25 --timeout 1800`, one run each, with `--backend c`, `--backend ssac`, and
`--backend arm64`, in that order, each waiting until the load average had been under 4 for two minutes (the
desktop's own load kept it near 3, so §11's threshold of 6 would have waited for nothing). The load was 1.5 to 3.2
throughout. The compiler was `./quest` at `42ba562c`, stage 2 built by C. The times are in
`benchmarks/mlton/baselines/2026-11-03/`: `quest-c-42ba562c.jsonl`, `quest-ssac-42ba562c.jsonl`, and
`quest-arm64-42ba562c.jsonl`.

### 13.2. Programs

| System | Geometric mean of time / MLton's | Without fib, tailfib, tak, and tensor | Run time, all 46 |
|---|--:|--:|--:|
| C, `9a08223f` (§11.2) | 3.54 | 4.00 | 31.7 min |
| C | **3.47** | 3.92 | 31.5 min |
| ssac, `9a08223f` (§11.2) | 3.48 | 4.08 | 37.9 min |
| ssac | **2.79** | 3.20 | 31.6 min |
| arm64, `9a08223f` (§11.2) | 5.17 | 5.30 | 44.9 min |
| arm64 | **3.63** | 3.66 | 34.0 min |

Each backend's time against C's at the same commit (below 1 is faster), ordered by arm64's, with §11's ratios beside
them:

| Benchmark | C (s) | ssac | arm64 | ssac, §11 | arm64, §11 |
|---|--:|--:|--:|--:|--:|
| tailfib | 0.25 | 1.00 | 9.12 | 1.07 | 16.65 |
| fib | 0.76 | 1.03 | 8.89 | 1.05 | 9.08 |
| tak | 0.81 | 1.02 | 7.48 | 1.03 | 7.48 |
| even-odd | 1.22 | 1.00 | 3.36 | 1.02 | 3.38 |
| peek | 107.23 | 1.03 | 1.52 | 1.01 | 1.62 |
| vector32-concat | 5.08 | 1.04 | 1.51 | 0.99 | 1.77 |
| vector64-concat | 3.64 | 0.90 | 1.43 | 1.02 | 1.80 |
| psdes-random | 20.06 | 1.03 | 1.34 | 4.09 | 4.77 |
| wc-scanStream | 127.69 | 0.95 | 1.31 | 1.09 | 1.43 |
| smith-normal-form | 764.78 | 1.00 | 1.30 | 1.00 | 1.30 |
| pidigits | 35.22 | 1.00 | 1.24 | 0.99 | 1.41 |
| zebra | 21.54 | 1.01 | 1.21 | 1.03 | 1.46 |
| matrix-multiply | 5.88 | 0.99 | 1.19 | 0.95 | 1.42 |
| zern | 5.06 | 0.98 | 1.11 | 0.94 | 2.63 |
| mandelbrot | 4.88 | 0.99 | 1.00 | 1.03 | 1.34 |
| mpuz | 10.04 | 0.46 | 0.85 | 1.13 | 2.01 |
| md5 | 16.59 | 0.76 | 0.84 | 3.94 | 6.83 |
| tyan | 12.33 | 0.86 | 0.83 | 1.10 | 1.31 |
| hamlet | 14.24 | 0.80 | 0.81 | 0.96 | 1.40 |
| count-graphs | 16.57 | 2.13 | 0.76 | 2.27 | 0.91 |
| boyer | 32.93 | 1.64 | 0.75 | 1.71 | 0.86 |
| flat-array | 61.77 | 3.51 | 0.71 | 3.88 | 1.04 |
| string-concat | 7.04 | 0.25 | 0.40 | 1.36 | 2.78 |
| checksum | 49.44 | 0.16 | 0.27 | 3.65 | 6.39 |
| tensor | 79.94 | 0.18 | 0.21 | 0.18 | 0.23 |
| imp-for | 5.88 | 0.04 | 0.90 | 0.04 | 0.95 |
| **geometric mean, all 46** | | **0.80** | **1.04** | 0.98 | 1.46 |
| without fib, tailfib, tak, and tensor | | 0.82 | 0.93 | 1.02 | 1.32 |

- **arm64 has caught C:** 1.04 of its time over all 46, down from 1.46, and 0.93 without the four; it is faster than
  C on 26 of the 46, and takes 0.70 of its own time at §11. Without fib, tailfib, tak, and even-odd (the small
  recursions clang transforms), it takes 0.87 of C's.
- **ssac is now the fastest backend,** 0.80 of C's time and 2.79 of MLton's, faster than C on 31 of the 46. arm64
  takes 1.30 of ssac's time, and 1.11 without those four.
- **md5, checksum, psdes-random, string-concat, and mpuz were the externals:** §11 found them slow in the SSA, not
  the code generator. With the library's inlined word operations as instructions in the SSA, and other externals
  called directly, they take 0.04 to 0.40 of their §11 times through both ssac and arm64, and all but psdes-random
  are now faster than C. zern (2.63 to 1.11), hamlet (1.40 to 0.81), and tyan (1.31 to 0.83) gained on arm64 alone,
  from the code generator's batches.
- **What is left for arm64** is mostly the four small recursions (tailfib, though 9.12 from 16.65, fib, tak, and
  even-odd), which are 72 percent of what it loses to C where it is slower, by the sum of the logarithms of the
  ratios. Of the rest, peek, the vector concatenations, wc-scanStream, smith-normal-form, pidigits, zebra, and
  matrix-multiply take 1.2 to 1.5 of C's time; ssac takes about C's time on all of them, so they are the code
  generator's.
- **ssac is still slow on flat-array (3.51), count-graphs (2.13), and boyer (1.64),** where arm64 is faster than
  C; this is in ssac's C, not the SSA.
- **C moved by 0.98,** within noise except tailmerge, at 1.25 of its §11 time; a second run took 54.6 seconds, and
  every run before §11 took 50 to 54, so §11's 44.1 was the outlier.

## 14. Loops of accumulated recursion and of mutual tail calls (2026-11-03)

§13 left arm64's distance from C mostly in four small recursions. Two are not the code's: clang calls `tak(33 22 11)`
once for the whole count, seeing that it returns the same value each time, and folds tailfib's `fib(44)` to a
constant, so that its main does nothing but call `bench.count()`; arm64 makes the same loops of their tail calls. The
other two were: fib, whose `fib(n - 1) + fib(n - 2)` clang turns into one call and a loop adding into an accumulator,
and even-odd, whose `even1` and `odd1` clang makes one loop. Two passes of the SSA now do the same ([ssa.md](ssa.md)
§4.1): `ssa/accumulate` and `ssa/tailJumps`.

### 14.1. What they change

A count, not kept, of the functions each pass changed, over the 46 programs (whole programs, through arm64) and the
compiler's driver:

| | `accumulate` | `tailJumps` (copies made) |
|---|--:|--:|
| The 46 | 1 (fib's `fib`) | 15: hamlet 11, even-odd 2, logic 1, knuth-bendix 1 |
| The driver | 0 | 5 |

### 14.2. Times

`tools/perf/variants.py` and `tools/perf/timeit.py --rounds 5` at its default thirty-second of the suite's counts,
whole programs, with both passes and with `QUEST_SKIP_PASSES=accumulate,tailJumps`; the load average was 2.1 to 2.7.
Each time is the least user time of the five rounds, and the ratio is to C's:

| Program | C | arm64 before | arm64 after | ssac before | ssac after |
|---|--:|--:|--:|--:|--:|
| fib | 0.50 s | 0.81 (1.62) | 0.57 (1.15) | 0.50 (1.00) | 0.53 (1.07) |
| even-odd | 0.08 s | 0.62 (7.81) | 0.31 (3.91) | 0.08 (1.00) | 0.00 (0.03) |
| hamlet | 1.74 s | 1.49 (0.85) | 1.55 (0.89) | 1.50 (0.86) | 1.47 (0.84) |
| logic | 2.37 s | 1.83 (0.77) | 1.82 (0.77) | 1.81 (0.76) | 1.83 (0.77) |
| knuth-bendix | 6.78 s | 5.77 (0.85) | 5.77 (0.85) | 7.86 (1.16) | 7.99 (1.18) |

- **fib through arm64 takes 0.70 of its time,** one call a level instead of two; through ssac, clang had already done
  the same to the C, and gains nothing.
- **even-odd through arm64 takes half its time:** one loop of two steps, without a frame pushed and popped at each.
  It is still 3.9 times C's, whose whole program (at this count, one even and one odd of 500,000,000) clang reduces
  further; through ssac, given one function, clang now folds the loop away.
- **hamlet, logic, and knuth-bendix do not move.** hamlet's arm64 difference was noise: nine rounds of timeit made it
  1.01, and its cycles were 5,097 and 5,096 million, its instructions retired 0.2 percent more. Its copies are of
  small functions of its elaborator's, pattern matcher's, and pretty printer's traversals.
- **Compile times do not move:** the driver's build through arm64 took 59.3 to 59.9 seconds with the passes and
  without, twice each.

Scaled by these ratios, §13's 8.89 times C's time for fib through arm64 would be about 6.2, and even-odd's 3.36 about
1.7; the rest of fib's is the count clang hoists. The suite was not retaken, as no other program changed.

## 15. The library's arbitrary-precision integers (2026-11-04)

pidigits and smith-normal-form use `util/bignum` (`lib/util/bignum.mod.quest`) in place of the suite's own
`support/intinf`, which is deleted (§3.7). The new library holds a value as its two's complement on 64-bit limbs in an
`Array(word.T)`, does Int arithmetic when both operands have one limb, and multiplies limbs with `word.mulHi`, one
`umulh` on arm64. The programs' algorithms are unchanged.

### 15.1. How they were taken

`run.py time --scale 0.25 --timeout 1800`, one run each, the two programs alone, with `--backend c` (and `--clean`),
`ssac`, and `arm64`, each waiting until the load average had been under 4 for two minutes. The collector is still
libgc, which is not generational. The library allocates each result at its largest possible length and copies it
when it turns out shorter, counting on a generational collector to make that cheap, so these times are to be taken
again under the new collector ([collector.md](collector.md)).

- `fd1f5a71`: the library. The load was 2.3 to 4.9.
- `fd1fedee`: `quest_array_new` skips the fill of an array whose initial word is zero. The memory is zeroed already,
  and the library allocates every result as such an array. Other worktrees' builds raised the load to 89 during C's
  smith-normal-form, whose time (141.3 s) is left out, and to 11.9 by the end of arm64's.

The times are in `benchmarks/mlton/baselines/2026-11-04/`, `quest-{c,ssac,arm64}-{fd1f5a71,fd1fedee}.jsonl`.

### 15.2. Times

Seconds, with §13's times at `42ba562c` for the suite's library, and each time over MLton's (pidigits 0.82 s,
smith-normal-form 4.03 s):

| Program | Backend | `support/intinf` (§13) | `util/bignum` | Faster | / MLton | Without the fill |
|---|---|--:|--:|--:|--:|--:|
| pidigits | C | 35.22 | 11.26 | 3.1x | 13.7 | 10.06 |
| | ssac | 35.20 | 11.98 | 2.9x | 14.6 | 11.52 |
| | arm64 | 43.63 | 18.26 | 2.4x | 22.3 | 17.61 |
| smith-normal-form | C | 764.78 | 70.05 | 10.9x | 17.4 | (load) |
| | ssac | 766.0 | 66.49 | 11.5x | 16.5 | 67.20 |
| | arm64 | 991.5 | 360.17 | 2.8x | 89.4 | 370.97 |

These two programs alone move §13's geometric means of time over MLton's from 3.47 to about 3.21 through C, from 2.79
to 2.58 through ssac, and from 3.63 to 3.48 through arm64.

- **smith-normal-form spends 95 percent of its time in `mulLimbs`'s inner loop** (`sample`), through C and arm64
  alike. The numbers grow to many limbs, and the multiplications are the bulk of the work.
- **arm64 is 5.1 times slower than C on smith-normal-form,** in the same loop. Each carry is
  `bit(word.lt(sum operand))`. clang compiles it to `adds` and `csel`; arm64's select makes it a compare and branch,
  which mispredict about half the time, as a carry is about as likely as not. The loop also loads `zeroW` and `oneW`,
  which are module globals, at each use. A carry computed from the operands' top bits instead (Hacker's Delight,
  section 2-13, without a comparison) took arm64's smith-normal-form to 144.6 s but C's to 115.9 s and pidigits'
  through C to 14.23 s, so the library keeps the comparison. An if-conversion in the SSA, making
  `if b then 1 else 0` a `csel` or `cset`, is what it calls for (§15.4).
- **pidigits spends about 18 percent of its time allocating and collecting** through C (`sample`): `GC_mark_from` 8
  percent, `quest_array_new` 5, zeroing 3, the rest in libgc. Skipping the fill gained 4 to 11 percent; smith-normal-
  form, which allocates far less for its work, did not move.

### 15.3. What the plan left out

- **Atomic allocation of arrays without pointers** (`Array(Int)`, `Array(Real)`, `Array(word.T)`, and the like), which
  libgc then does not scan: `GC_mark_from`'s 8 percent of pidigits is its ceiling there. Every array is allocated by
  `quest_array_new` with `quest_alloc`, scanned, and the element type is not known at that call. (No compiler emits
  `quest_alloc_atomic`, though [collector.md](collector.md) §1 lists `Array(Int)` among its uses.) The collector's
  step 1, which gives every allocation a layout, is where an array of scalars gets one without pointers; the plan
  leaves it to that.
- **`word.copy`**, a `memmove` of limbs: the library's copies take linear time against the multiplications' and
  divisions' quadratic time, and the profiles put the time in those loops, so it was not added.

### 15.4. If-conversion

`ssa/selects` ([ssa.md](ssa.md) §4.1) makes a branch whose arms only pass values to one block a `select`, which arm64
makes a `csel` (or a `cset` of 1 and 0) on the flags of the branch's comparison, and ssac a `?:`. An arm may move up to
two instructions into the branch's block, if they cannot trap or write: `util/bignum`'s carries load the module's
globals `oneW` and `zeroW` in their arms, and the pass did nothing to them until loads of static data at a symbol
could move (smith-normal-form through arm64 took 362.2 s, pidigits 17.97 s). Taken as §15.1, one run each, the load
3.2 to 4.9, the times in `quest-{ssac,arm64}-selects.jsonl` (the second line of each program):

| Program | Backend | Before (§15.2, without the fill) | With selects | Faster |
|---|---|--:|--:|--:|
| pidigits | ssac | 11.52 | 11.24 | 1.02x |
| | arm64 | 17.61 | 14.41 | 1.22x |
| smith-normal-form | ssac | 67.20 | 66.89 | 1.00x |
| | arm64 | 370.97 | 115.95 | 3.20x |

- **arm64's `mulLimbs` loop** has a `cmp` and a `csel` for each carry, and no branch on it. smith-normal-form through
  arm64 is now 1.7 times C's 70.05 s, from 5.1.
- **ssac does not move:** clang already made the same branch a `csel`.
- **What remains of arm64's distance** in the loop is mostly the four loads of `oneW` and `zeroW` an iteration, which
  C folds (`zeroW` to `xzr`, `oneW` loaded once before the loop). Both loops check `r` for null and its bounds at each
  access.

### 15.5. Constant globals

`ssa/constants` ([ssa.md](ssa.md) §4.1) makes a global the unit stores once with a constant, before anything that could
read it, read-only data holding the constant, and each of its loads the constant itself. `util/bignum`'s `oneW`,
`zeroW`, and `onesW` are such globals: arm64's `bignum.mod.s` loads none of them now, where it loaded them in every
iteration of each loop using them. The library's initialization calls its imports' initializations and registers its
types first, which the pass had to know reach none of the library's code. Taken as §15.1, one run each, the load 3.5
to 5.9, the times in `quest-{ssac,arm64}-constants.jsonl`:

| Program | Backend | With selects (§15.4) | With constants | Faster |
|---|---|--:|--:|--:|
| pidigits | ssac | 11.24 | 10.98 | 1.02x |
| | arm64 | 14.41 | 13.22 | 1.09x |
| smith-normal-form | ssac | 66.89 | 63.57 | 1.05x |
| | arm64 | 115.95 | 107.85 | 1.08x |

smith-normal-form through arm64 is 1.5 times C's 70.05 s, from 1.7; through ssac it is now faster than C.

## 16. The collector (2026-11-04)

The suite on the collector of [collector.md](collector.md) step 3 against §13's Boehm times: the stop-the-world
mark-region collector of `runtime/quest_gc.c` with its bump allocation, the inline allocation sequence of
`ssa/allocations` ([ssa.md](ssa.md) §4.1) in the SSA's backends, and the noscan space for layouts of scalars alone.

### 16.1. How they were taken

As §13.1 (`run.py time --clean --scale 0.25 --timeout 1800`, one run each, `--backend c`, `ssac`, and `arm64`, in
that order), then arm64 again under `QUEST_SKIP_PASSES=inlineAllocation`, which leaves each allocation a call of
`quest_alloc` for the runtime's slow path. The compiler was `./quest` from the working tree that became step 3's
commit, stage 2 built by C, with ssac still calling the runtime's `quest_alloc` out of line (§16.2 says what
inlining it there changed, measured apart). The machine was loaded throughout by another build and its check (load
averages 4 to 19 at the starts of the runs, against §13's 1.5 to 3.2), so `run.py` now records each run's processor
time (user and system, from `getrusage` of the child) beside its wall time, and the tables give both. A wall ratio
divides by §13's wall time under its lighter load; the processor ratio divides the after side's processor time by the
same before wall time, since §13 recorded none, so the two bracket the truth and the processor one is the fairer
where they differ. Neither is a clean measurement; the suite is to be retaken on an idle machine after step 4. The
times are in `benchmarks/mlton/baselines/2026-11-04/`: `quest-c-step3.jsonl`, `quest-ssac-step3.jsonl`,
`quest-arm64-step3.jsonl`, and `quest-arm64-calls-step3.jsonl`. A wall time under a second is the first run of a
fresh binary rather than the program (tailfib's 0.23 s is 0.00 s of processor time), so the four small programs'
wall ratios say nothing, and their processor ratios little.

### 16.2. Programs

The ratio of step 3's time to §13's, by wall time and by processor time, ordered by the best ratio in the row:

| Benchmark | C | C, CPU | ssac | ssac, CPU | arm64 | arm64, CPU |
|---|--:|--:|--:|--:|--:|--:|
| wc-scanStream | 0.39 | 0.39 | 0.55 | 0.55 | 0.52 | 0.52 |
| tensor | 0.40 | 0.40 | 1.05 | 1.03 | 1.01 | 0.99 |
| barnes-hut | 0.48 | 0.47 | 0.68 | 0.67 | 0.66 | 0.62 |
| logic | 0.49 | 0.48 | 0.59 | 0.58 | 0.60 | 0.57 |
| simple | 0.51 | 0.50 | 0.62 | 0.60 | 0.66 | 0.63 |
| DLXSimulator | 0.53 | 0.52 | 0.70 | 0.68 | 0.74 | 0.72 |
| ratio-regions | 0.57 | 0.54 | 0.79 | 0.64 | 0.64 | 0.61 |
| even-odd | 0.98 | 0.79 | 0.99 | 0.81 | 0.57 | 0.50 |
| vliw | 0.59 | 0.56 | 0.76 | 0.73 | 0.68 | 0.66 |
| hamlet | 0.60 | 0.58 | 0.74 | 0.71 | 1.11 | 0.76 |
| tyan | 0.61 | 0.59 | 0.70 | 0.66 | 0.76 | 0.74 |
| mlyacc | 0.61 | 0.58 | 0.74 | 0.69 | 0.71 | 0.68 |
| tailmerge | 0.61 | 0.61 | 0.71 | 0.70 | 0.68 | 0.67 |
| psdes-random | 0.99 | 0.98 | 0.76 | 0.69 | 0.64 | 0.62 |
| count-graphs | 0.66 | 0.65 | 0.92 | 0.91 | 0.85 | 0.80 |
| model-elimination | 0.66 | 0.65 | 0.79 | 0.78 | 0.68 | 0.67 |
| knuth-bendix | 0.67 | 0.66 | 0.78 | 0.77 | 0.71 | 0.70 |
| boyer | 0.67 | 0.66 | 0.97 | 0.95 | 0.87 | 0.85 |
| nucleic | 0.69 | 0.66 | 0.82 | 0.77 | 0.80 | 0.77 |
| zebra | 0.70 | 0.69 | 0.82 | 0.81 | 0.78 | 0.77 |
| life | 0.72 | 0.70 | 0.85 | 0.83 | 0.84 | 0.82 |
| ray | 0.72 | 0.70 | 1.01 | 0.95 | 0.95 | 0.92 |
| raytrace | 0.73 | 0.71 | 0.86 | 0.83 | 0.88 | 0.82 |
| peek | 0.74 | 0.74 | 0.93 | 0.86 | 0.83 | 0.83 |
| lexgen | 0.77 | 0.74 | 0.91 | 0.88 | 0.93 | 0.88 |
| string-concat | 0.98 | 0.94 | 0.80 | 0.64 | 0.85 | 0.77 |
| tsp | 0.85 | 0.83 | 1.00 | 0.96 | 0.92 | 0.90 |
| fib | 0.98 | 0.67 | 1.03 | 0.72 | 0.85 | 0.72 |
| vector-rev | 0.98 | 0.95 | 0.90 | 0.86 | 0.98 | 0.96 |
| vector32-concat | 0.97 | 0.92 | 0.90 | 0.86 | 1.02 | 0.99 |
| tailfib | 0.92 | 0.01 | 0.93 | 0.02 | 1.00 | 0.90 |
| vector64-concat | 0.92 | 0.86 | 1.06 | 0.94 | 1.00 | 0.96 |
| flat-array | 0.93 | 0.92 | 1.05 | 1.05 | 1.02 | 0.99 |
| imp-for | 1.85 | 1.81 | 0.94 | 0.01 | 1.68 | 1.11 |
| zern | 0.96 | 0.92 | 0.97 | 0.92 | 0.99 | 0.95 |
| tak | 0.97 | 0.70 | 0.97 | 0.70 | 1.02 | 0.97 |
| pidigits | 0.98 | 0.97 | 0.99 | 0.98 | 0.97 | 0.97 |
| checksum | 1.00 | 1.00 | 1.08 | 1.04 | 1.52 | 1.10 |
| mpuz | 1.01 | 0.98 | 1.03 | 0.98 | 1.03 | 1.00 |
| mandelbrot | 1.01 | 0.96 | 1.04 | 0.99 | 1.08 | 1.01 |
| output1 | 1.02 | 1.02 | 1.16 | 1.05 | 1.05 | 1.05 |
| wc-input1 | 1.04 | 1.04 | 1.05 | 1.05 | 1.03 | 1.02 |
| md5 | 1.03 | 1.01 | 1.03 | 1.01 | 1.03 | 1.02 |
| smith-normal-form | 1.04 | 1.04 | 1.25 | 1.07 | 1.13 | 1.07 |
| matrix-multiply | 1.39 | 1.33 | 1.04 | 1.00 | 1.07 | 1.03 |
| fft | 1.07 | 1.02 | 1.12 | 1.07 | 1.24 | 1.17 |
| **geometric mean** | **0.79** | **0.69** | **0.89** | **0.69** | **0.88** | **0.82** |
| against MLton, before → after | 0.69 → 0.54 |  | 0.55 → 0.49 |  | 0.72 → 0.63 |  |

- **The allocation-heavy programs halve on C:** wc-scanStream 0.39, tensor 0.40, barnes-hut 0.48, logic 0.49, simple
  0.51, DLXSimulator 0.53, and the rest of the eleven that §3.1 found dominated by allocation and collection are at 0.57
  to 0.74. Against MLton, the suite's geometric mean goes from 0.69 to 0.54 of MLton's time through C, 0.55 to 0.49
  through ssac, and 0.72 to 0.63 through arm64 (`benchmarks/mlton/baselines/2026-10-28/compiled.jsonl`).
- **C gained more than the SSA's backends on the same programs** (wc-scanStream 0.39 against ssac's 0.55 and arm64's
  0.52). ssac's reason was that its printer declares every runtime symbol it calls as an opaque external and so called
  `quest_alloc` out of line, the header's inline copy in `quest_inline.c`, where C's printer gets the header's inline
  sequence from clang. The SSA's inline allocation pass now runs before ssac's printer as before arm64's: logic and
  wc-scanStream through ssac, the calls against the sequence, timed by hand at a quarter of the suite's counts (64 and
  2,048), twice each, were 10.5 and 10.6 s against 9.5 and 10.2 for logic and 16.7 and 16.8 against 11.6 and 11.7 for
  wc-scanStream, so 0.93 and 0.70; the ssac column above is without the pass.
- **Two losses are code placement, the rest the load's.** imp-for (C 1.85, arm64 1.11 by processor time) allocates 1.1
  billion one-word boxes and little else (collector.md step 1's table), and matrix-multiply (C 1.39) allocates almost
  nothing (183 MB in 8 s: three collections, 0.6 ms of pauses). Both compile to the same C as before but for the
  allocation, and timed back to back against the Boehm release compiler's builds of them (`3ad3867e`, the commit before
  step 1, in its own tree) they took 10.4 s against 5.6 and 7.8 against 5.7. Neither time is the allocation sequence's.
  Compiled against variants of the header (`quest_alloc` in `runtime/quest_runtime.h`: the test of the checking flags,
  the cursor and limit of the object's space, the bump, the header's store, and a read-modify-write of the object's
  start bit), both programs run the same instructions in their inner loops whatever the variant, and their times swing
  with where clang places `main`'s loops, into which everything is inlined: without the start bit's five instructions,
  matrix-multiply takes 5.1 s (Boehm's build 5.7) and imp-for 7.4; without the flags' test, imp-for takes 14.7; with
  every loop aligned to 64 bytes (`-falign-loops=64`), imp-for takes 10.5 to 11.8 with the start bit or without it, and
  matrix-multiply 8.0 and 5.3 as before, so the loops' own alignment is not the whole of it (the same instructions at
  other addresses, on the same data, take 0.8 and 1.3 ns per inner iteration); and gathering the collector's five
  globals into one struct, so that the sequence takes one address instead of five, changes nothing (10.5 and 8.2). So
  these two ratios measure code placement, which the C backend does not control, and the sequence's own cost against
  `GC_malloc`'s call is at most what imp-for's best placement shows: 1.8 s more over 1.1 billion allocations, 1.6 ns
  each, against the collections it buys on the programs above. fft (1.02 to 1.17), checksum (arm64 1.10),
  smith-normal-form (1.04 to 1.07), and output1 (1.02 to 1.05) are within what the load did to the other programs by
  processor time, except that fft's arm64 loss is the inline sequence's (below).
- **Inline against calls on arm64:** the sequence pays where allocation is the cost and costs a few percent where it
  is not, and the geometric mean over the 46 is 0.99 by processor time (1.02 by wall, three programs hit by the load),
  so the pass is kept:

| Benchmark | calls (s) | inline (s) | inline / calls, wall | calls, CPU (s) | inline, CPU (s) | inline / calls, CPU |
|---|--:|--:|--:|--:|--:|--:|
| tailmerge | 25.71 | 19.89 | 0.77 | 25.47 | 19.59 | 0.77 |
| psdes-random | 20.50 | 17.20 | 0.84 | 20.26 | 16.75 | 0.83 |
| zebra | 24.29 | 20.44 | 0.84 | 24.01 | 20.15 | 0.84 |
| wc-scanStream | 99.34 | 87.77 | 0.88 | 99.00 | 87.41 | 0.88 |
| ratio-regions | 6.51 | 5.81 | 0.89 | 6.28 | 5.55 | 0.88 |
| vliw | 7.49 | 6.98 | 0.93 | 7.21 | 6.68 | 0.93 |
| barnes-hut | 10.75 | 10.32 | 0.96 | 10.45 | 9.70 | 0.93 |
| DLXSimulator | 12.49 | 11.72 | 0.94 | 12.25 | 11.42 | 0.93 |
| simple | 10.46 | 10.05 | 0.96 | 10.22 | 9.61 | 0.94 |
| peek | 142.12 | 135.28 | 0.95 | 141.84 | 134.82 | 0.95 |
| logic | 11.78 | 11.48 | 0.98 | 11.54 | 10.99 | 0.95 |
| tyan | 8.14 | 7.80 | 0.96 | 7.91 | 7.57 | 0.96 |
| pidigits | 43.48 | 42.51 | 0.98 | 43.17 | 42.24 | 0.98 |
| mlyacc | 8.17 | 8.11 | 0.99 | 7.80 | 7.69 | 0.99 |
| life | 9.42 | 9.32 | 0.99 | 9.18 | 9.08 | 0.99 |
| nucleic | 6.70 | 6.50 | 0.97 | 6.32 | 6.26 | 0.99 |
| vector64-concat | 5.25 | 5.20 | 0.99 | 5.03 | 4.98 | 0.99 |
| vector-rev | 10.89 | 10.83 | 0.99 | 10.64 | 10.60 | 1.00 |
| wc-input1 | 80.35 | 80.25 | 1.00 | 80.06 | 79.97 | 1.00 |
| string-concat | 2.46 | 2.40 | 0.97 | 2.17 | 2.17 | 1.00 |
| tensor | 16.97 | 16.99 | 1.00 | 16.72 | 16.75 | 1.00 |
| tak | 6.13 | 6.16 | 1.00 | 5.90 | 5.92 | 1.00 |
| model-elimination | 18.99 | 19.06 | 1.00 | 18.73 | 18.78 | 1.00 |
| boyer | 21.24 | 21.57 | 1.02 | 21.02 | 21.08 | 1.00 |
| zern | 5.52 | 5.54 | 1.00 | 5.29 | 5.31 | 1.00 |
| tailfib | 2.23 | 2.24 | 1.00 | 2.01 | 2.01 | 1.00 |
| ray | 11.71 | 11.69 | 1.00 | 11.27 | 11.31 | 1.00 |
| raytrace | 8.74 | 9.24 | 1.06 | 8.48 | 8.59 | 1.01 |
| vector32-concat | 7.75 | 7.85 | 1.01 | 7.51 | 7.61 | 1.01 |
| tsp | 11.37 | 11.55 | 1.02 | 11.09 | 11.31 | 1.02 |
| fib | 4.96 | 5.72 | 1.15 | 4.71 | 4.83 | 1.03 |
| md5 | 14.10 | 14.47 | 1.03 | 13.86 | 14.22 | 1.03 |
| output1 | 53.15 | 54.67 | 1.03 | 52.88 | 54.34 | 1.03 |
| mpuz | 8.56 | 8.80 | 1.03 | 8.33 | 8.56 | 1.03 |
| smith-normal-form | 1021.12 | 1119.57 | 1.10 | 1019.40 | 1056.55 | 1.04 |
| flat-array | 41.96 | 44.30 | 1.06 | 41.72 | 43.27 | 1.04 |
| mandelbrot | 4.97 | 5.27 | 1.06 | 4.75 | 4.93 | 1.04 |
| count-graphs | 9.86 | 10.71 | 1.09 | 9.62 | 10.01 | 1.04 |
| matrix-multiply | 7.10 | 7.44 | 1.05 | 6.87 | 7.19 | 1.05 |
| even-odd | 2.15 | 2.35 | 1.09 | 1.92 | 2.05 | 1.06 |
| knuth-bendix | 30.79 | 32.43 | 1.05 | 30.15 | 32.12 | 1.07 |
| lexgen | 6.81 | 7.34 | 1.08 | 6.48 | 6.96 | 1.07 |
| checksum | 13.66 | 20.26 | 1.48 | 13.42 | 14.72 | 1.10 |
| imp-for | 5.50 | 8.89 | 1.62 | 5.27 | 5.89 | 1.12 |
| hamlet | 8.08 | 12.74 | 1.58 | 7.78 | 8.69 | 1.12 |
| fft | 5.44 | 6.37 | 1.17 | 5.21 | 6.03 | 1.16 |
| **geometric mean** (46) | | | **1.02** | | | **0.99** |

### 16.3. The compiler's own build

The driver (`questlang/driver/main.quest`) built from an empty build directory with `-j 8`, twice each, alternating:
the Boehm release compiler `3ad3867e` in its own tree against `./quest` here, under `/usr/bin/time -l`, at load 3
to 4.

| Compiler | Wall (s) | User + system (s) | Largest resident set (GB) |
|---|--:|--:|--:|
| `3ad3867e`, Boehm | 28.3, 28.0 | 142.8, 141.9 | 1.26 |
| Step 3 | 23.3, 23.3 | 109.0, 109.6 | 3.77 |

The build takes 0.83 of the wall time and 0.77 of the processor time, and three times the memory. The collector's
statistics (`QUEST_GC_STATS=1`) of the same build in one process (`-j 1`): 23 collections, 5.0 s of pauses in all
and 994 ms the longest, 42.2 GB allocated, 9.9 GB the most in blocks at once, 848 MB the most live at once, in 1,784
MB of lines; 20.3 million objects live at the end, 84 MB of them large. The memory is the trigger's: a block with one
live line counts as in use, the target is twice the blocks in use after a collection, and after the compiler's
collections the blocks in use are 3.2 times the live lines and 6.6 times the live bytes (a `-j 8` worker's
sixteenth: 223 MB live in 458 MB of lines in 1,485 MB of blocks), so a worker's heap reaches 2.2 GB for 223 MB of
data. Live lines against live bytes, the fragmentation that recycling cannot recover and that step 7 would, is 2.1
here; step 4 records it again with minor collections, which reclaim the young blocks before they scatter, and
should count a recyclable block's holes as free when it sets the target.

## 17. Generations (2026-11-05)

The suite on the collector of [collector.md](collector.md) step 4 against §16's step 3 times: sticky mark bits, minor
collections every nursery of blocks taken (64 MB, adapting to what survives), the object barrier logging and the slot
barrier marking cards, and the full collections as before.

### 17.1. How they were taken

As §16.1 (`run.py time --clean --scale 0.25 --timeout 1800`, one run each, `--backend c`, `ssac`, and `arm64`, in that
order), by `./quest` from the working tree that became step 4's commit, stage 2 built by C from a clean stage build (ABI
70), after `tools/check` had passed on the same tree. The machine was idle but for another session's single benchmark
run (load averages 1.2 to 3.5 at the starts of the runs); both wall and processor times are given, and the ratios of
each to §16's own, which were taken under a heavier load: where the two differ by much (imp-for, hamlet, and checksum
through arm64), it is §16's wall time that the load stretched, and the processor ratio is the one to read. The suite was
taken twice. The first taking, with the nursery at 8 MB, is what §17.2's second paragraph and its table come from, and
it changed the default to 64 MB; the table below is the second, at 64 MB. The times are in
`benchmarks/mlton/baselines/2026-11-05/`: `quest-c-step4.jsonl`, `quest-ssac-step4.jsonl`, and
`quest-arm64-step4.jsonl`; the first taking's are beside them as `-step4-nursery8.jsonl`, and ssac's with its
allocations left as calls (`QUEST_SKIP_PASSES=inlineAllocation`) as `quest-ssac-calls-step4.jsonl`. The ssac column
carries the inline allocation sequence too, which §16.2 measured apart from the suite on two programs, since ssac's
suite in §16 was taken without it; §17.2's last paragraph separates the two.

### 17.2. Programs

The ratio of step 4's time to step 3's, by wall time and by processor time, ordered by the best ratio in the row:

| Benchmark | C | C, CPU | ssac | ssac, CPU | arm64 | arm64, CPU |
|---|--:|--:|--:|--:|--:|--:|
| hamlet | 1.06 | 1.06 | 1.14 | 1.15 | 0.60 | 0.85 |
| imp-for | 0.94 | 0.95 | 1.07 | – | 0.61 | 0.88 |
| checksum | 0.97 | 0.97 | 0.94 | 0.95 | 0.66 | 0.89 |
| wc-scanStream | 0.97 | 0.97 | 0.68 | 0.68 | 0.97 | 0.97 |
| ratio-regions | 1.04 | 1.04 | 0.74 | 0.86 | 1.01 | 1.01 |
| smith-normal-form | 0.96 | 0.96 | 0.80 | 0.93 | 0.89 | 0.94 |
| peek | 0.97 | 0.97 | 0.81 | 0.87 | 0.85 | 0.85 |
| tailmerge | 0.96 | 0.96 | 0.84 | 0.84 | 0.95 | 0.95 |
| fib | 1.04 | 1.03 | 1.01 | 1.00 | 0.85 | 0.96 |
| output1 | 0.98 | 0.98 | 0.85 | 0.93 | 0.96 | 0.96 |
| tsp | 0.99 | 0.99 | 0.85 | 0.87 | 0.98 | 0.98 |
| simple | 0.98 | 0.98 | 0.86 | 0.85 | 0.96 | 0.98 |
| fft | 1.01 | 1.00 | 0.99 | 0.98 | 0.86 | 0.86 |
| DLXSimulator | 0.99 | 0.99 | 0.86 | 0.85 | 0.95 | 0.95 |
| logic | 0.98 | 0.98 | 0.87 | 0.86 | 0.92 | 0.94 |
| nucleic | 0.98 | 0.97 | 0.87 | 0.88 | 0.97 | 0.96 |
| count-graphs | 1.01 | 1.00 | 1.04 | 1.03 | 0.87 | 0.90 |
| barnes-hut | 1.07 | 1.07 | 0.88 | 0.87 | 0.95 | 0.98 |
| mlyacc | 0.99 | 0.98 | 0.89 | 0.87 | 0.95 | 0.94 |
| tyan | 0.98 | 0.98 | 0.89 | 0.90 | 0.98 | 0.98 |
| vector64-concat | 1.00 | 0.99 | 0.89 | 0.93 | 0.98 | 0.98 |
| life | 0.99 | 0.98 | 0.90 | 0.89 | 0.95 | 0.95 |
| ray | 0.98 | 0.97 | 0.90 | 0.92 | 0.99 | 0.98 |
| even-odd | 1.02 | 1.01 | 1.01 | 0.98 | 0.91 | 0.93 |
| raytrace | 0.98 | 0.98 | 0.97 | 0.96 | 0.92 | 0.95 |
| lexgen | 0.99 | 0.99 | 0.99 | 0.98 | 0.93 | 0.91 |
| mandelbrot | 0.99 | 0.98 | 0.96 | 0.95 | 0.93 | 0.95 |
| matrix-multiply | 0.97 | 0.98 | 0.96 | 0.96 | 0.94 | 0.94 |
| vector-rev | 0.95 | 0.95 | 1.00 | 1.00 | 0.94 | 0.93 |
| flat-array | 0.98 | 0.98 | 0.94 | 0.94 | 0.94 | 0.96 |
| model-elimination | 0.97 | 0.97 | 1.33 | 1.33 | 0.95 | 0.95 |
| wc-input1 | 0.96 | 0.96 | 0.95 | 0.95 | 0.97 | 0.97 |
| md5 | 0.97 | 0.97 | 0.99 | 0.99 | 0.95 | 0.95 |
| mpuz | 0.98 | 0.97 | 0.98 | 0.97 | 0.95 | 0.95 |
| psdes-random | 0.97 | 0.97 | 1.22 | 1.33 | 0.95 | 0.97 |
| knuth-bendix | 0.96 | 0.96 | 1.00 | 1.00 | 0.95 | 0.96 |
| vector32-concat | 1.02 | 0.99 | 0.96 | 0.94 | 0.96 | 0.95 |
| zebra | 0.96 | 0.96 | 1.08 | 1.08 | 1.23 | 1.23 |
| tensor | 0.98 | 0.98 | 0.96 | 0.96 | 0.98 | 0.98 |
| string-concat | 0.96 | 0.96 | 1.01 | 0.98 | 1.02 | 0.98 |
| pidigits | 0.97 | 0.97 | 0.98 | 0.98 | 0.98 | 0.98 |
| zern | 0.97 | 0.97 | 0.98 | 0.98 | 0.99 | 0.98 |
| tak | 1.05 | 1.03 | 1.04 | 1.01 | 0.98 | 0.98 |
| boyer | 0.99 | 0.99 | 1.05 | 1.06 | 0.98 | 0.97 |
| vliw | 1.00 | 0.98 | 1.14 | 1.15 | 0.99 | 0.99 |
| tailfib | 1.10 | – | 1.14 | – | 1.00 | 0.99 |
| **geometric mean** | **0.99** | **0.98** | **0.95** | **0.96** | **0.93** | **0.95** |
| against MLton, before → after | 0.54 → 0.54 |  | 0.49 → 0.47 |  | 0.63 → 0.59 |  |

- **Level with step 3 through C, ahead of it through the SSA's backends.** The geometric means are 0.99 by wall time and
  0.98 by processor time through C, 0.95 and 0.96 through ssac, and 0.93 and 0.95 through arm64; against MLton the suite
  goes from 0.54 to 0.54 of MLton's time through C, 0.49 to 0.47 through ssac, and 0.63 to 0.59 through arm64. Some of
  the gain is step 3's load (C's code is the same but for the barriers, and its processor ratio of 0.98 is about what
  that load cost), and arm64's three best wall ratios (hamlet, imp-for, checksum, 0.60 to 0.66) are 0.85 to 0.89 by
  processor time. Two programs still lose through C, barnes-hut (1.07) and hamlet (1.06), for the reason of the next
  paragraph, less of it. arm64's zebra (1.23) is one run's: the same binary run three more times took 20.2, 24.9, and
  20.7 s, so it has two speeds, by where a run's stack and heap land, and the faster is 0.99 of step 3's.

- **The nursery's size is what the first taking measured.** With the 8 MB the design gave it, the suite lost to step 3
  through C: 1.03 by both times over the 46 (`quest-c-step4-nursery8.jsonl`; 0.97 and 0.95 through ssac and arm64), and
  1.10 to 1.17 on the programs that allocate most. The same binaries of the ten that lost most, run again at other sizes
  and with minor collections off (`QUEST_GC_NURSERY`; processor seconds, one run each, the 8 MB column the mean of two):

| Benchmark | 8 MB (s) | 16 MB | 32 MB | 64 MB | none | 64 MB / 8 MB | none / 8 MB |
|---|--:|--:|--:|--:|--:|--:|--:|
| barnes-hut | 10.52 | 9.89 | 9.99 | 10.06 | 9.07 | 0.96 | 0.86 |
| mlyacc | 8.56 | 8.00 | 7.53 | 7.46 | 7.48 | 0.87 | 0.87 |
| DLXSimulator | 14.74 | 14.31 | 13.28 | 13.02 | 12.91 | 0.88 | 0.88 |
| boyer | 24.49 | 23.82 | 23.02 | 22.14 | 21.98 | 0.90 | 0.90 |
| tailmerge | 36.17 | 36.30 | 36.34 | 32.97 | 32.61 | 0.91 | 0.90 |
| wc-scanStream | 54.74 | 54.38 | 53.27 | 50.25 | 49.90 | 0.92 | 0.91 |
| vliw | 7.21 | 6.96 | 7.36 | 6.71 | 6.61 | 0.93 | 0.92 |
| tyan | 7.77 | 7.69 | 7.56 | 7.31 | 7.19 | 0.94 | 0.92 |
| hamlet | 9.32 | 8.96 | 8.66 | 8.99 | 8.99 | 0.96 | 0.96 |
| ratio-regions | 5.34 | 5.35 | 5.06 | 5.42 | 5.37 | 1.01 | 1.01 |
| **geometric mean, against 8 MB** | | **0.97** | **0.95** | **0.93** | **0.91** | | |

The loss is the minor collections', not the barriers', and it is not their pauses: barnes-hut's collections pause 0.40 s
in all at 8 MB (1,725 minor, 12 full) and 0.33 s with full ones alone (89), of 10 s. It is where allocation goes
afterwards. A minor collection leaves its survivors where they are, one or two percent of the nursery's bytes in small
objects scattered over nearly every block it filled, and the marks are sticky until the next full collection, so
allocation, which takes a block's holes before a free block, hops between ever smaller holes: barnes-hut's 34 GB went
into 32.7 million holes of 1.0 KB on average at 8 MB, 12.9 million of 2.7 KB at 64 MB, and 2.1 million of 16 KB with
full collections alone (`QUEST_GC_STATS` counts the holes), and by a profile (`profile.py`) the slow path took four
times the samples at 8 MB that it took with none, and the program's two hot functions 13 and 8 percent more. What full
collections alone cost instead is memory: barnes-hut's heap reaches 451 MB for 3 MB of live data, since a block with one
live line counts as in use and the target is twice the blocks in use, against 67 MB at 8 MB and 211 MB at 64. The
default is now 64 MB, the heap's least size (so a heap whose blocks in use stay under half of that has full collections
alone), which takes most of the loss back here and all of it on the compiler's build (§17.3). The rest is what moving
the young survivors would recover ([collector.md](collector.md) step 7).

- **ssac's losses are the inline allocation sequence's, and so are its gains.** model-elimination (1.33) and
  psdes-random (1.22) do not move with the nursery, and a profile shows no barrier in them. ssac's suite has the
  sequence for the first time here, and against its own build with the allocations left as calls
  (`QUEST_SKIP_PASSES=inlineAllocation`), by processor time:

| Benchmark | calls (s) | inline (s) | inline / calls, wall | calls, CPU (s) | inline, CPU (s) | inline / calls, CPU |
|---|--:|--:|--:|--:|--:|--:|
| wc-scanStream | 65.80 | 45.33 | 0.69 | 65.14 | 44.96 | 0.69 |
| simple | 8.56 | 7.41 | 0.87 | 8.31 | 7.15 | 0.86 |
| peek | 95.86 | 83.06 | 0.87 | 95.59 | 82.79 | 0.87 |
| logic | 11.03 | 9.60 | 0.87 | 10.76 | 9.34 | 0.87 |
| tailmerge | 19.33 | 17.05 | 0.88 | 19.04 | 16.78 | 0.88 |
| DLXSimulator | 11.56 | 10.32 | 0.89 | 11.26 | 9.98 | 0.89 |
| ratio-regions | 5.56 | 5.03 | 0.90 | 5.30 | 4.77 | 0.90 |
| barnes-hut | 9.92 | 8.99 | 0.91 | 9.63 | 8.71 | 0.90 |
| mlyacc | 6.94 | 6.44 | 0.93 | 6.49 | 5.92 | 0.91 |
| nucleic | 5.93 | 5.49 | 0.93 | 5.67 | 5.24 | 0.92 |
| life | 7.98 | 7.43 | 0.93 | 7.74 | 7.19 | 0.93 |
| md5 | 12.35 | 12.95 | 1.05 | 12.11 | 12.70 | 1.05 |
| count-graphs | 30.52 | 33.54 | 1.10 | 30.23 | 33.03 | 1.09 |
| zebra | 17.32 | 19.17 | 1.11 | 17.03 | 18.88 | 1.11 |
| boyer | 49.26 | 55.23 | 1.12 | 48.99 | 54.67 | 1.12 |
| hamlet | 8.21 | 9.57 | 1.17 | 7.90 | 9.27 | 1.17 |
| vliw | 7.39 | 8.81 | 1.19 | 7.05 | 8.50 | 1.21 |
| model-elimination | 26.81 | 37.22 | 1.39 | 26.55 | 36.93 | 1.39 |
| psdes-random | 13.96 | 19.34 | 1.39 | 13.70 | 19.09 | 1.39 |
| **geometric mean** (46) | | | **1.00** | | | **1.00** |

The other 25 are within 0.94 to 1.04, and the geometric mean over the 46 is 1.00 by either time. The sequence is the
same SSA that arm64 compiles to a gain on these programs (§16.2: psdes-random 0.83, model-elimination 1.00), printed as
C with every load and store through a `char *` and compiled without strict aliasing, and what clang makes of it varies
as it did for C's own allocation in §16.2 (psdes-random takes 19 s through C too, and 14 s through ssac with calls);
marking the slow path's branch unlikely changes nothing. ssac keeps the pass: it costs nothing on the whole, and it is
the path arm64 and the JIT take, which ssac is there to test.

### 17.3. The compiler's own build

The driver (`questlang/driver/main.quest`) built from an empty build directory with `-j 8` under `/usr/bin/time -l`,
twice at each nursery, alternating, on an idle machine (load 1.2); §16.3's step 3 line (full collections alone) for
comparison:

| Collector | Wall (s) | User + system (s) | Largest resident set (GB) |
|---|--:|--:|--:|
| Step 3 (§16.3) | 23.3, 23.3 | 109.0, 109.6 | 3.77 |
| Step 4, nursery 8 MB | 24.6, 24.5 | 117.5, 116.8 | 1.22 |
| 32 MB | 23.5, 23.4 | 111.9, 111.3 | 1.34 |
| 64 MB, the default | 22.6, 22.6 | 106.6, 106.4 | 1.39 |
| 128 MB | 21.9, 21.9 | 102.8, 102.9 | 1.65 |
| no minor collections | 22.6, 22.6 | 106.1, 106.3 | 3.50 |

At the default the build takes 0.97 of step 3's wall time and processor time in 0.37 of its memory; at 8 MB it took 1.05
and 1.07 in 0.32, which is what the first taking found, and with no minor collections it is step 3's collector but for
the barriers, which cost it nothing that shows. The times fall steadily as the nursery grows, for the reason §17.2
gives, and the memory rises past 64 MB, so the default is there.

The collector's statistics (`QUEST_GC_STATS=each`) of the same build in one process (`-j 1`) at the default: 9 full
collections, pausing 1.75 s in all and 876 ms at the longest; 271 minor collections, pausing 2.32 s in all and 27 ms at
the longest (the nursery adapts upward on the compiler: 160 MB a minor collection, on average), with 1.75 GB surviving
them of the 43.4 GB allocated, 4.0 percent; 247,000 objects logged and 589,000 cards marked; 2.57 GB the most in blocks
at once (step 3: 9.9 GB); and 1,067 MB live at the end in 2,259 MB of lines, 2.1 bytes of lines for a live byte, as in
step 3. The allocation went into 87 million holes, half a kilobyte each. With the 8 MB nursery the same build had 1,949
minor collections pausing 3.06 s (10 ms the longest) and 9 full ones pausing 2.30 s. The longest pause is still a full
collection's, most of a second, which is step 6's to shorten.

A REPL session, the transcripts of `tests/repl` replayed twenty times through `./quest -i` (4.4 GB allocated in 2.1 s):
22 minor collections pausing 38.5 ms in all and 8 full ones pausing 14.7 ms, 3.4 ms the longest of either; 13.1 MB live
at the end in 28.5 MB of lines, 2.2 to one; 241 MB the most in blocks. With the 8 MB nursery it had 184 minor
collections pausing 166 ms and 2 full ones, in 121 MB.

## 18. Stack maps (2026-11-05)

The arm64 backend on the collector of [collector.md](collector.md) step 5 against §17's step 4: each frame of native
code scanned by the map of its call, the words live across it and no others ([arm64.md](arm64.md) §3.13), and dead
values' slots no longer cleared.

### 18.1. How they were taken

As §17.1, `--backend arm64` alone (the change is the arm64 backend's and the collector's stack scan; C's code and its
frames, scanned whole, are as they were), by `./quest` from the working tree that became step 5's commit (ABI 72), after
`tools/check` had passed on it. The machine was idle (load averages 1.7 to 2.1). The times are in
`benchmarks/mlton/baselines/2026-11-05/quest-arm64-step5.jsonl`.

### 18.2. Programs

The ratio of step 5's time to step 4's through arm64, for the programs at 0.98 or under and at 1.03 or over by
processor time:

| Benchmark | step 4 (s) | step 5 (s) | step 5 / step 4, wall | step 4, CPU (s) | step 5, CPU (s) | step 5 / step 4, CPU |
|---|--:|--:|--:|--:|--:|--:|
| zebra | 25.04 | 20.44 | 0.82 | 24.71 | 20.12 | 0.81 |
| mpuz | 8.39 | 7.62 | 0.91 | 8.14 | 7.37 | 0.91 |
| barnes-hut | 9.80 | 9.41 | 0.96 | 9.52 | 9.14 | 0.96 |
| life | 8.87 | 8.65 | 0.98 | 8.61 | 8.40 | 0.98 |
| hamlet | 7.64 | 7.48 | 0.98 | 7.37 | 7.19 | 0.98 |
| wc-scanStream | 85.29 | 83.50 | 0.98 | 84.94 | 83.15 | 0.98 |
| fft | 5.46 | 5.38 | 0.98 | 5.20 | 5.12 | 0.98 |
| tailfib | 2.25 | 2.47 | 1.10 | 1.99 | 2.22 | 1.11 |
| psdes-random | 16.42 | 19.98 | 1.22 | 16.16 | 19.72 | 1.22 |
| **geometric mean** (46) | | | **1.00** | | | **1.00** |

- **Level with step 4:** the geometric mean over the 46 is 1.00 by either time, and the 37 programs not shown are within
  0.99 to 1.02. The maps cost a running program nothing, being read only at a collection, and what the backend no longer
  does, clearing a dead value's slot, was a store in a few loops: mpuz, a fifth of whose `assign` samples were those
  stores (arm64-performance-review.md §4), takes 0.91 of its time. zebra's 0.82 is step 4's run at the slower of its two
  speeds (§17.2). tailfib's 1.11 is two seconds of a loop whose code is the same, twelve bytes further on (the three
  instructions that register the frame table come before it in the unit): built by both compilers and run twice each, it
  took 2.96 and 2.99 s against 3.04 and 3.22.

- **psdes-random's 1.22 is a pair of stores.** The same binary takes 19.8 to 20.2 s run after run, and step 4's
  compiler's code for it 16.1 s against the same runtime, so it is the code. With the object's own address the base of
  both of a tuple's stores (collector.md step 5: the allocation's base is no longer a pointer), the backend's pairing
  merges them into one `stp`, where step 4 had two stores from two bases, and the loop that follows loads one of the two
  words alone, which the processor does not forward from a pair's store. ssa.md §4.1 records the same hazard from the
  loads' side, on the same program. The commit after this one leaves such a pair of stores apart ([arm64.md](arm64.md)
  §3.5), and psdes-random takes 16.3 s.

### 18.3. The compiler's own build

The compiler built by the arm64 backend (`./quest compile --backend arm64 questlang/driver/main.quest`), building the
driver in one process (`-j 1`) under `QUEST_GC_STATS=1`: step 4's, step 5's, and step 5's with the tables unread
(`QUEST_GC_MAPS=0`), which scans every frame whole and has no clears either:

| Compiler | Wall (s) | Live at most (MB) | Largest resident set (GB) |
|---|--:|--:|--:|
| Step 4's | 70.0 | 1,083 | 2.87 |
| Step 5's | 70.4, 69.7 | 1,063, 1,061 | 2.85, 2.84 |
| Step 5's, tables unread | 69.7, 69.7 | 1,145, 1,136 | 2.90, 2.88 |

- **The live data is 2 percent less than with step 4's clears, and 7 percent less than whole frames without them,**
  which is what the maps are worth to this program's memory: its frames held few dead pointers once step 4's backend
  cleared the slots, and the maps do a little better than the clears did (a dead register's saved copy and a slot dead
  across this call but stored later are skipped too). The time is the same. Each run scans about 8,400 frames by their
  tables and 3,450 whole (the runtime's and the collector's own, and the functions that enter a `try`), 16 and 6 a
  collection.

- **The tables are 822 KB, 13 percent of the code's size,** in `__TEXT,__const` (2.10 MB to 2.92 MB), and the code is
  125 KB smaller without the clears (6.47 MB to 6.35 MB), so the binary grows 3.5 percent (21.5 MB to 22.3 MB). Nothing
  reads the tables until a collection walks a frame of their unit.

## 19. Incremental marking (2026-11-05)

The collector of [collector.md](collector.md) step 6 against §18's step 5: a full collection that the heap's growth asks
for marks in slices between which the program runs, and allocations during it take the slow path.

### 19.1. How they were taken

As §17.1, `--backend c` and `--backend arm64`, by `./quest` from the working tree that became step 6's commit (ABI 73),
after `tools/check` had passed on it. The machine was idle but for another session's single benchmark run (load averages
1.6 to 2.9). The suite was taken twice: the first taking, with every full collection the heap asked for a cycle, is what
§19.2's second paragraph comes from, and it added the condition the second was taken with. The times are in
`benchmarks/mlton/baselines/2026-11-05/`: `quest-c-step6.jsonl` and `quest-arm64-step6.jsonl`, and the first taking's
with `-every` in their names. Step 5 changed nothing of C's, so C's column is against §17's step 4.

### 19.2. Programs

Through C, step 6's time against step 4's, for the programs at 0.97 or under and at 1.03 or over by processor time:

| Benchmark | step 4 (s) | step 6 (s) | step 6 / step 4, wall | step 4, CPU (s) | step 6, CPU (s) | step 6 / step 4, CPU |
|---|--:|--:|--:|--:|--:|--:|
| imp-for | 10.30 | 9.01 | 0.87 | 10.05 | 8.75 | 0.87 |
| life | 8.79 | 8.54 | 0.97 | 8.53 | 8.29 | 0.97 |
| even-odd | 1.22 | 1.20 | 0.99 | 0.97 | 0.94 | 0.97 |
| peek | 77.05 | 80.89 | 1.05 | 76.78 | 80.57 | 1.05 |
| **geometric mean** (46) | | | **1.00** | | | **1.00** |

Through arm64, against step 5's:

| Benchmark | step 5 (s) | step 6 (s) | step 6 / step 5, wall | step 5, CPU (s) | step 6, CPU (s) | step 6 / step 5, CPU |
|---|--:|--:|--:|--:|--:|--:|
| psdes-random | 19.98 | 16.26 | 0.81 | 19.72 | 16.00 | 0.81 |
| tailfib | 2.47 | 2.34 | 0.95 | 2.22 | 2.06 | 0.93 |
| ray | 11.83 | 11.62 | 0.98 | 11.32 | 11.03 | 0.97 |
| mlyacc | 7.70 | 7.93 | 1.03 | 7.28 | 7.48 | 1.03 |
| **geometric mean** (46) | | | **0.99** | | | **0.99** |

- **Level with what came before:** 1.00 by either time through C over the 46 programs, and 0.99 through arm64. A program
  whose full collections take under 10 ms has none of them as cycles (below), which is nearly every program here, so
  what the suite measures of this step is the allocation path's change, the header word stored by whichever path
  allocates: nothing. imp-for's 0.87 is its placement again (§16.2; it was 1.06 in the first taking below, of the same
  code). arm64's psdes-random (0.81) and tailfib (0.93) are not this step's: the commit between the two leaves a pair of
  stores apart when the loop after reads half of it (§18.2), and tailfib's twelve bytes have moved again.

- **The first taking, with every full collection the heap asked for a cycle, lost 2 percent through C**
  (`quest-c-step6-every.jsonl`, `quest-arm64-step6-every.jsonl`; 1.00 through arm64 with psdes-random's gain in it), and
  the same programs through both backends. Through C, those at 1.04 or over:

| Benchmark | step 4 (s) | every one a cycle (s) | every one a cycle / step 4, wall | step 4, CPU (s) | every one a cycle, CPU (s) | every one a cycle / step 4, CPU |
|---|--:|--:|--:|--:|--:|--:|
| vliw | 6.86 | 7.05 | 1.03 | 6.53 | 6.77 | 1.04 |
| logic | 12.28 | 12.76 | 1.04 | 12.02 | 12.50 | 1.04 |
| DLXSimulator | 13.10 | 13.76 | 1.05 | 12.79 | 13.44 | 1.05 |
| imp-for | 10.30 | 10.91 | 1.06 | 10.05 | 10.64 | 1.06 |
| hamlet | 9.08 | 9.65 | 1.06 | 8.76 | 9.33 | 1.06 |
| ratio-regions | 5.11 | 5.69 | 1.11 | 4.86 | 5.42 | 1.11 |
| tailmerge | 32.33 | 37.86 | 1.17 | 32.07 | 37.61 | 1.17 |
| **geometric mean** (46) | | | **1.02** | | | **1.02** |

tailmerge shows why. Its live data is 15 MB in the heap's least size, 64 MB, and it has 1,535 full collections in 19 s,
5 ms each and 21 ms at the longest: the same binary through arm64, at the suite's count, with the cycles' pace and the
allocation between slices varied (`QUEST_GC_PACE`, `QUEST_GC_SLICE`):

| Full collections | Wall (s) | Their pauses in all (s) | Longest pause (ms) | Born marked (MB) |
|---|--:|--:|--:|--:|
| stopping the world | 18.8 | 8.4 | 21.1 | – |
| cycles, pace 4, slices 32 KB apart | 21.8 | 10.3 | 1.4 | 4,365 |
| pace 16 | 19.9 | 9.3 | 0.4 | 1,103 |
| pace 16, slices 8 KB apart | 19.9 | 9.3 | 0.2 | 1,091 |
| pace 64, slices 8 KB apart | 19.5 | 9.1 | 1.2 | 275 |

As cycles, those collections cost the slow path's call for each allocation made while one runs and a scan of every
object born then (4.4 GB of the 75 GB allocated at pace 4), and what they buy is a pause of 1.4 ms in place of one of
21. A faster pace shortens the cycles and shrinks the loss without removing it. So a full collection is a cycle only
when the last one took longer than a pause may, 10 ms (`QUEST_GC_PAUSE`; 0 makes every one a cycle, as in this taking),
and tailmerge has its old time: 18.5 s.

### 19.3. The compiler's own build, and a REPL session

The driver built from an empty build directory with `-j 8` under `/usr/bin/time -l`, three times each way, alternating,
with full collections in cycles and with `QUEST_GC_INCREMENTAL=0`, which stops the world for each:

| Full collections | Wall (s) | User + system (s) | Largest resident set (GB) |
|---|--:|--:|--:|
| in cycles (when the last took over 10 ms) | 21.1, 21.1, 21.3 | 108.3, 109.1, 108.7 | 1.54, 1.54, 1.35 |
| stopping the world | 21.0, 21.4, 21.1 | 108.4, 109.8, 108.2 | 1.37, 1.37, 1.39 |

The same build in one process (`-j 1`), and the REPL session of §17.3 (the transcripts of `tests/repl` replayed twenty
times), by `QUEST_GC_STATS`:

| | Build, cycles | Build, stopping the world | REPL, cycles | REPL, stopping the world |
|---|--:|--:|--:|--:|
| Wall (s) | 65.7 | 65.2 | 2.25 | 2.25 |
| Full collections | 9, 6 of them cycles | 9 | 9, all cycles | 9 |
| their pauses in all (ms) | 2,202 | 1,360 | 20.5 | 17.1 |
| the longest (ms) | 11.6 | 660 | 0.65 | 3.75 |
| a cycle's first pause, longest (ms) | 1.3 | | 0.65 | |
| slices | 7,013 | | 77 | |
| a slice, longest (ms) | 2.5 | | 0.44 | |
| a cycle's last pause, longest (ms) | 2.3 | | 0.36 | |
| last pauses that gave up | 0 | | 0 | |
| allocated during cycles (MB) | 247 | | 2 | |
| Minor collections | 271 | 276 | 22 | 22 |
| their pauses in all (ms) | 2,266 | 2,358 | 41 | 41 |
| the longest (ms) | 29.7 | 24.0 | 3.7 | 3.7 |
| Most in blocks (MB) | 2,894 | 2,817 | 247 | 245 |
| Largest resident set (GB) | 3.15 | 3.08 | 0.29 | 0.28 |

- **The longest pause of a full collection goes from 660 ms to 12 ms on the build,** and that one is a collection that
  stopped the world and ran over, after which the rest are cycles: within the cycles the longest first pause is 1.3 ms,
  the longest slice 2.5 ms, and the longest last pause 2.3 ms, none of which gave its work back. The build takes the
  same time either way, in one process and in eight. Marking in slices is 1.6 times the work of marking at once (2.2 s
  against 1.4), since the slices also scan the 247 MB born while they ran and what the barriers logged, and since 7,000
  starts are colder than nine; it is 3 percent of the build's time.

- **The slow path during a cycle costs nothing that shows:** 247 MB of the build's 43.5 GB, 0.6 percent, is allocated
  while a cycle runs, 41 MB a cycle, which is also how far the heap passes its target and the nursery its size before
  the cycle's sweep (the most in blocks rises 3 percent, the resident set 2; with eight workers the largest resident set
  was 0.17 GB more in two runs of three). The fallback the design kept, a flag word on the inline path of every
  allocation, is not needed.

- **A slice is bounded:** it marks 4 bytes for each byte allocated since the last, a megabyte at most, the rest of a
  large allocation's share left to the slices that follow; before the bound a slice after a 4 MB table's allocation took
  16 ms. An object over 128 KB is scanned a piece at a time; before that a slice that met a large table took 13 ms.

- **The REPL session's full collections are 2 ms each and stop the world;** the cycles' column is with
  `QUEST_GC_PAUSE=0`, which makes each a cycle, to show them: no pause over 0.65 ms.

- **The longest pause of any kind is now a minor collection's,** 30 ms on the build (9 ms on average), where the nursery
  has adapted to 160 MB a collection and 6 MB survive each. That, not the full collections, is what is left of the
  collector's latency.

### 19.4. On the tree with §15's changes (2026-11-06)

§16 to §19 were measured on trees without §15's changes (the library's integers, `ssa/selects`, and `ssa/constants`),
which reached the main branch while the collector was being written. The collector's commits were then replayed onto
them, and the ABI numbers and section numbers in these sections are the replayed ones. The suite was not retaken. The
compiler's own build was, as in §19.3 with full collections in cycles, three times with `-j 8` and once with `-j 1`,
on an idle machine (load 1.8), by `./quest` from the replayed step 6 (ABI 73), and it is as it was:

| | Step 6 (§19.3) | Replayed |
|---|--:|--:|
| Wall, `-j 8` (s) | 21.1, 21.1, 21.3 | 21.0, 21.2, 21.1 |
| User + system (s) | 108.3, 109.1, 108.7 | 109.5, 109.6, 109.8 |
| Largest resident set (GB) | 1.54, 1.54, 1.35 | 1.55, 1.55, 1.44 |
| Wall, `-j 1` (s) | 65.7 | 66.2 |
| A full collection's pause, longest (ms) | 11.6 | 10.8 |
| A slice, longest (ms) | 2.5 | 3.6 |
| A minor collection's pause, longest (ms) | 29.7 | 27.7 |

`ssa/constants` makes as many globals constant with the collector as without (123 globals stay writable in the SSA
goldens on both trees), now that it takes the registrations of roots and frame tables and the barriers as running no
Quest code, and `ssa/selects` makes the same 32 selects there.

## 20. Closing part of the gap to MLton (2026-11-06)

Five changes from [mlton-performance-review.md](mlton-performance-review.md) §4, items 1 to 5, and one the suite
called for, each removing work MLton does not do on peek, wc-scanStream, ratio-regions, or zebra, made as the steps of
a plan (`docs/mlton-gap.md`, retired into this section; its step 1 was the plan itself, `83827cce`). They are the
self-hosted compiler's alone: optimizations, not fixes, so the bootstrap does not follow ([testing.md](testing.md)
§2.8). They were made and first measured under Boehm, then replayed onto the collector of §16 to §19; every time
below was taken after the replay, under the collector.

The times are in `benchmarks/mlton/baselines/2026-11-06/`: the four at each commit through C and arm64
(`quest-c-whole-four-COMMIT.jsonl`, `quest-arm64-whole-four-COMMIT.jsonl`), the suite through arm64
(`quest-arm64-whole-COMMIT.jsonl`), §20.4's two left out (`-without-steps-2-3`, `-without-static-closures`), §20.5's
bound lifted (`quest-arm64-whole-growth-100000-eb7a20e2.jsonl`), and MLton's tensor (`mlton-tensor.jsonl`).

### 20.1. The steps

Decided on 2026-11-04: specialization per call site, bounded by the inliner's size, not whole-program
defunctionalization; peek left as it is (no extensible type, options of `Int` boxed in a field); no interim free-list
pop in Boehm. Each step was measured on the four before the next was begun.

2. **Type applications** (`1505c50c`, [ir.md](ir.md) §8.6): a `type_app` whose instance is not a function
   (`maybe.none(:A)`, `lists.nil(:A)`) is inlined as a call of the function without arguments would be.
   `language/inlined_type_applications`.
3. **Members that name their module's variables** (`1505c50c`, ir.md §8.6): a whole program inlines a member's
   function from outside its module when each variable of its module that it names is an immutable exported member
   that is not a function; the copy reads it as the member (`let error.2 = member util/maybe.error`).
   `language/inlined_module_members`.
4. **Scalar replacement across block parameters** (`17613817`, `ssa/scalars`, [ssa.md](ssa.md) §4.3): run after
   promotion rather than in escape analysis, since wc-scanStream's loop carries its stream in a stack slot until
   promotion makes it a block parameter. It splits groups (an option holding a tuple nests the tuple's layout), takes
   a no-payload option's constant in the unit's static data as an object, drops the dead parameters promotion leaves
   (which kept the stream whole), and replaces single objects escape analysis left. Replayed onto the collector, it
   recognizes `quest_alloc` with its layout, and treats a write barrier as escape analysis does, as no use of the
   object, dropping it with the object (`ssa_scalars`' case with barriers; `ssa/barriers` finds none owed after it).
   It runs before `ssa/constants`.
5. **Specialization on a known function argument** (`1906c59c`, ir.md §8.6): `language/specialized_recursion`. Found
   on the way:
   - the unit's growth bound was spent before the simplifier reached `preflowPush`'s calls, so a specialization is
     bounded by the threshold alone;
   - `let var g = fun ...` was bound as a function and read as a variable, in both compilers' lowering (`d04c2f1d`,
     `language/mutable_function_variables`);
   - a static parameter given a constant was left unbound, so mlyacc and vliw did not build (`26e8a9b1`), found by the
     suite, which tools/check does not build;
   - a local function whose closure captures only itself (map's, specialized in boyer's `rewrite`) allocated it each
     time its enclosing function ran; such a group's closures are now static (`13826a80`, ir.md §8.2), read-only data
     that need no entry in the root tables.
6. **Known calls of captured functions** (`fbff0279`, `walk.knownClosures`, ir.md §8.2): the review's §3.4 was
   corrected, since zebra's calls of `same`, `left`, and `adjacent` were known in the simplified IR and indirect only
   because closure conversion made them captures. `language/captured_known_calls`. Found on the way: steps 2 and 3
   made zebra slower, their copies of `maybe.none` and `maybe.unwrap`, counted at their whole size, spending the
   growth bound before `isConsistent`; the bound now counts a copy's size less the call's (2). §11.3's settings were
   measured with the whole size, so the suite below measures this too.
7. **Clears at a branch** (`250c480e`, [arm64.md](arm64.md) §3.8, `regalloc_scan` case 14): for a target that asks
   for clears, a value dying at a branch, on the path that falls through, is cleared only if a call may follow on
   that path, and a cold block's call is not one. Under Boehm, whose frames were scanned whole, a failed bounds
   check's path cleared every pointer live into the passing one, and `preflowPush` had 1,541 clears rather than 33.
   Under the collector, a frame's map says which slots are live, arm64 asks for no clears, and **this step changes no
   arm64 code**: it measures as noise below, and is kept for the targets that ask.
8. **Unreachable members of a whole program** (`97dd6562`, `whole.dropUnreachable`, ir.md §8.6), added on 2026-11-05
   when the suite found imp-for through arm64 1.87 times slower after steps 2 to 7 (under Boehm): steps 2 and 3 made
   more of the library inlinable, and copies into members imp-for never calls spent nearly all the growth bound
   before main's calls of `forLoop`. A whole program now keeps only the members it can reach, and the growth bound
   was raised from half the unit's size to three quarters (or 1000, if more). A module whose record nothing reads
   has none, and so no entry in the root tables (`unit.mod.quest`, the C printer's `qr_roots`).

Then arm64's functions were aligned to 16 bytes rather than 4 (`eb7a20e2`, `asm.functionStart`, and the JIT's
encoder, which pads between functions to match): under Boehm, step 8 made fib and tak 12 and 15 percent slower by
moving their unchanged code to worse addresses, and 16-byte alignment gave them their old times back.

The four after each step, through C and arm64, whole programs, at `--scale 0.25`, one run each (2026-11-06, each
phase begun after a minute with the load average below 5; it was 1.9 to 3.2):

| Commit | peek C | arm64 | wc-scanStream C | arm64 | ratio-regions C | arm64 | zebra C | arm64 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `b9ca7cb2` (before) | 69.11 | 80.73 | 49.40 | 82.39 | 4.10 | 5.21 | 12.79 | 13.59 |
| `1505c50c` (2, 3) | 71.34 | 92.74 | 50.62 | 82.59 | 5.11 | 5.90 | 14.17 | 14.33 |
| `17613817` (4) | 71.25 | 91.68 | 49.78 | 27.95 | 5.02 | 5.88 | 13.97 | 14.15 |
| `1906c59c` (5) | 71.19 | 91.35 | 49.36 | 27.55 | 2.46 | 2.74 | 13.95 | 29.51 |
| `fbff0279` (6) | 66.12 | 78.12 | 49.29 | 27.59 | 2.01 | 2.35 | 12.55 | 13.46 |
| `250c480e` (7) | 65.38 | 77.81 | 49.47 | 27.57 | 2.01 | 2.36 | 12.55 | 13.43 |
| `13826a80` (5, static closures) | 65.59 | 77.95 | 49.31 | 27.49 | 2.04 | 2.34 | 12.64 | 13.38 |
| `97dd6562` (8) | 64.67 | 76.85 | 49.46 | 27.52 | 2.11 | 2.34 | 10.27 | 11.06 |
| `eb7a20e2` (alignment) | 65.58 | 77.15 | 49.73 | 27.77 | 2.15 | 2.36 | 10.42 | 11.22 |

As they now measure:

- **Steps 2 and 3 cost on their own:** every one of the four is slower after them, peek through arm64 by 15 percent,
  ratio-regions by a quarter through C, zebra by a tenth. They pay only with the steps after them (§20.4).
- **Step 4** takes wc-scanStream through arm64 to 0.34 of its time. Through C it does not move: `ssa/scalars` is a
  pass of the SSA, which the C backend does not use.
- **Step 5** halves ratio-regions, but doubles zebra through arm64 (14.15 s to 29.51), which step 6 more than undoes,
  with peek's cost from steps 2 and 3. Steps 5 and 6 go together.
- **Step 7** changes nothing, as above; nor do the static closures on the four (but see §20.4).
- **Step 8** takes zebra to about 0.8 of its time through both backends.
- **The alignment** changes none of the four by more than noise.

### 20.2. The four, before and after

At `b9ca7cb2` and `eb7a20e2`, from the table above:

| Program | C before | C after | arm64 before | arm64 after |
|---|--:|--:|--:|--:|
| peek | 69.11 s | 65.58 (0.95) | 80.73 s | 77.15 (0.96) |
| wc-scanStream | 49.40 s | 49.73 (1.01) | 82.39 s | 27.77 (0.34) |
| ratio-regions | 4.10 s | 2.15 (0.52) | 5.21 s | 2.36 (0.45) |
| zebra | 12.79 s | 10.42 (0.81) | 13.59 s | 11.22 (0.83) |

Their allocations through arm64 (`allocations.py --clean`):

| Program | Before | After |
|---|--:|--:|
| peek | 9,600,002,430 | 9,600,001,837 |
| wc-scanStream | 16,394,076,198 | 8,060,947 |
| ratio-regions | 781,856,080 | 75,821,979 |
| zebra | 1,121,286,121 | 875,030,710 |

These are the counts the steps gave under Boehm: the replay changed what the steps remove not at all. wc-scanStream's
bytes go from 467 GB to 8.4 GB, ratio-regions' from 20.7 GB to 1.9 GB. zebra's `isConsistent` makes 426 million
allocations rather than 672 million: the `maybe.some` boxes of the calls step 6 made direct and the inliner then took.
peek's are its options of `Int`, left as they are.

Under the collector the gains are smaller than under Boehm (wc-scanStream through arm64 0.34 rather than 0.17,
ratio-regions 0.45 rather than 0.27), since each allocation the steps remove costs less under the collector than it
did under Boehm (§16).

### 20.3. The suite

The 46 programs through arm64, whole, at `b9ca7cb2`, `97dd6562` (step 8), and `eb7a20e2`, each begun after a minute
with the load average below 5 (it was 2.0 to 2.9). The geometric mean of the time ratios, after to before, is
**0.913** in wall time and **0.910** in processor time; 845 s of wall time in all becomes 751 s. Step 8 to the
alignment is 0.998 in both. Those that moved by 5 percent or more, all faster:

| Program | Before | After step 8 | After | Ratio |
|---|--:|--:|--:|--:|
| wc-scanStream | 80.63 s | 27.44 s | 27.43 s | 0.34 |
| ratio-regions | 5.15 s | 2.33 s | 2.32 s | 0.45 |
| model-elimination | 19.68 s | 13.32 s | 13.22 s | 0.67 |
| knuth-bendix | 35.20 s | 24.60 s | 24.52 s | 0.70 |
| simple | 9.26 s | 7.49 s | 7.16 s | 0.77 |
| zebra | 14.07 s | 11.01 s | 11.02 s | 0.78 |
| psdes-random | 16.37 s | 13.00 s | 13.03 s | 0.80 |
| mlyacc | 7.13 s | 6.26 s | 6.28 s | 0.88 |
| boyer | 21.54 s | 19.24 s | 19.19 s | 0.89 |
| zern | 5.33 s | 4.80 s | 4.77 s | 0.89 |
| ray | 11.52 s | 10.48 s | 10.45 s | 0.91 |
| mpuz | 8.56 s | 8.11 s | 8.09 s | 0.94 |
| peek | 80.13 s | 76.44 s | 75.99 s | 0.95 |

None is slower by more than 4 percent (mandelbrot, 1.04). imp-for takes 5.32 s (5.34 before). fib and tak take 4.85
and 6.00 s, against 4.86 and 6.11 before and 4.86 and 6.07 after step 8: on this tree step 8 did not move them to
worse addresses, and the alignment neither helps nor hurts them. It is kept so that a function's loops stay where
they are as the code before it changes.

tensor through arm64 takes 16.54 s (16.28 s of processor time) after, 16.68 s before. MLton's, taken again with
`run.py time --mlton-only --scale 0.25 tensor` on the program as §1.4 changed it, takes 7.48 s (7.15 s of processor
time; load 1.4), so tensor's ratio through arm64 is **2.21** in wall time and 2.28 in processor time.

MLton's other times were not taken again. Against §2's (2026-10-28, the least of three runs), with tensor's from
above, the suite through arm64, whole, takes **2.22** times as long as MLton's at the tip (geometric mean of wall time
over the 46; 2.46 without fib, tailfib, and tak), against 2.43 before. Coarse, since one side is a single run and the
other a week older: by program, from fib's 0.34, tak's 0.47, and even-odd's 0.57 to zebra's 4.4, wc-scanStream's 5.2,
pidigits' 15.5, smith-normal-form's 24.6, and peek's 34.1. Unit by unit, from §19's times (before these steps, and
without tensor, which §19 timed as the old program), C's take 2.38 times as long and arm64's 2.62.

### 20.4. Steps measured by leaving them out

Two of the steps measured as costs or not at all in §20.1, so the tip was measured without each, the four and the
suite through arm64 as above (load 1.3 to 2.7):

- **Steps 2 and 3 off,** switched off where they apply (`memberReads` always none, and no `type_app` taken as a
  call), since step 5's `inline.specialize` takes step 3's reads, and the commit does not revert alone. The suite is
  **1.027** of the tip's wall time (1.025 processor): zebra 1.17, boyer 1.14, simple 1.13, lexgen 1.11,
  matrix-multiply and ratio-regions 1.10, peek 1.06, imp-for 1.06, model-elimination and nucleic 1.05; none faster
  than hamlet's 0.98. Of the four: peek 73.14 s through C and 80.97 through arm64, ratio-regions 2.38 and 2.56, zebra
  11.88 and 12.99, wc-scanStream unchanged. So what steps 2 and 3 cost alone, the later steps more than recover with
  them.
- **The static closures reverted** (`13826a80`, which reverts cleanly): the four are unchanged, but the suite is
  **1.026** of the tip's (1.026 processor): knuth-bendix 1.19, boyer 1.10, mlyacc and vliw 1.06, fft 1.05, simple
  1.04.

All the steps are kept.

### 20.5. The growth bound

How often the unit's growth bound refuses a call the threshold allows, at the tip, counted by a trace not kept (one
line for each refusal, so a call refused in each of the six rounds counts six times): 22 of the 46 programs reach it.
hamlet 5,414, nucleic 4,160, model-elimination 3,065, logic 1,657, mlyacc 1,502, simple 1,317, boyer 1,316, vliw
1,060, DLXSimulator 796, lexgen 209, life 200, knuth-bendix 192, smith-normal-form 164, raytrace 162, count-graphs
111, tsp 109, ratio-regions 94, tensor 64, tyan 51, ray 48, zebra 31, barnes-hut 11.

With the bound lifted (`QUEST_INLINE=growth=100000`), the 17 of these that take less than a minute (all but
smith-normal-form, tensor, tyan, ray, and barnes-hut, which reach it least or take longest) take **1.000** of their
time (geometric mean): simple 0.84, life 0.95, hamlet, nucleic, and logic 0.97, but zebra 1.11, mlyacc and
knuth-bendix 1.06, and model-elimination 1.04. Builds take longer: hamlet 39.4 s, boyer 40.6 s (20.1 and 33.0 with
the bound). So the bound is reached often, but lifting it gains nothing overall; a bound for each function, in
proportion to its size, would want simple's gain without zebra's loss, and is not done.

### 20.6. Compile times

The compiler's driver, built through C from an empty build directory, twice each: 65.60 and 65.66 s before, 67.76
and 67.73 s after (3.2 percent longer), from §20.1's steps 2, 3, and 5 inlining more. A whole program's own build takes
less time than before (through arm64, wc-scanStream 0.7 s to 0.3 s, ratio-regions 1.1 to 0.7), its unreachable
members no longer compiled.

## 21. The C and arm64 backends, for programs and for the compiler (2026-11-06)

Whether arm64 should become the default backend (decided as C in [arm64.md](arm64.md) §1, from §5): the compiler as
each backend builds it, and the suite through C at the tip, beside §20.3's suite through arm64. Each phase began after
three minutes with the load average below 5, at `9d3b08d6` (§20's code; no compiler change since `eb7a20e2`).

The data are in `benchmarks/mlton/baselines/2026-11-06/`: the script (`compiler-timings.sh`), `/usr/bin/time -l` of the
stage 2 builds (`compiler-stage2-c-9d3b08d6.txt`, `compiler-stage2-arm64-9d3b08d6.txt`) and of the driver builds
(`compiler-driver-c-built-9d3b08d6.txt`, `compiler-driver-arm64-built-9d3b08d6.txt`), and the suite through C
(`quest-c-whole-9d3b08d6.jsonl`); the suite through arm64 is §20.3's `quest-arm64-whole-eb7a20e2.jsonl`.

### 21.1. Building the compiler

Stage 1 (the release's) compiling the driver with `-j 8 --backend c` or `--backend arm64` into an empty build
directory, twice each, alternating:

| Backend | Wall | User | Maximum resident |
|---|--:|--:|--:|
| C | 26.62, 27.73 s | 116.3, 121.0 s | 1.39, 1.52 GB |
| arm64 | 22.47, 24.10 s | 96.7, 98.2 s | 1.27, 1.25 GB |

arm64 takes 0.86 of C's time, having no clang to run.

### 21.2. The compiler each backend builds

Each stage 2 compiling the driver (output through C) from an empty build directory, three rounds alternating
between the compilers and between `-j 8` and `-j 1`. The third round was slower for both, the machine likely busier,
but the ratio held:

| | C-built | arm64-built | arm64 / C (means) |
|---|--:|--:|--:|
| `-j 8` wall | 23.76, 23.72, 27.74 s | 26.39, 26.64, 30.55 s | 1.11 |
| `-j 1` wall | 73.80, 72.52, 75.60 s | 77.56, 77.44, 79.63 s | 1.06 |
| `-j 1` user | 67.21, 66.56, 68.78 s | 71.39, 71.42, 73.30 s | 1.06 |
| `-j 1` maximum resident | 3.11 GB | 3.13 GB | 1.01 |

On 2026-10-30 (§5.1) the arm64-built compiler took 1.58 to 2.24 times as long; now 1.06 to 1.11. The times include
clang compiling the driver's C, the same for both, so the compilers' own ratio is somewhat higher; it was not
separated. Where the rest goes is not profiled; the suite's call-bound programs (§21.3) suggest calls.

### 21.3. Programs

The suite, whole program, `--scale 0.25`, arm64 against C, geometric means over the 46 programs: **1.045** wall,
1.169 processor. Without fib, tak, tailfib, and even-odd, which clang turns into loops (3.0 to 9.3 times as long
through arm64; tailfib's processor time 492 times, clang leaving almost nothing): **0.884** wall, 0.891 processor,
arm64 faster on 30 of the 42.

| Program | arm64 / C | Program | arm64 / C | Program | arm64 / C |
|---|--:|---|--:|---|--:|
| imp-for | 0.47 | matrix-multiply | 0.86 | tsp | 1.01 |
| wc-scanStream | 0.49 | lexgen | 0.87 | mandelbrot | 1.02 |
| tensor | 0.50 | tyan | 0.88 | fft | 1.07 |
| checksum | 0.59 | hamlet | 0.89 | ratio-regions | 1.09 |
| tailmerge | 0.59 | boyer | 0.92 | zern | 1.09 |
| string-concat | 0.63 | barnes-hut | 0.97 | md5 | 1.12 |
| psdes-random | 0.64 | output1 | 0.97 | peek | 1.15 |
| logic | 0.71 | life | 0.97 | pidigits | 1.31 |
| knuth-bendix | 0.72 | raytrace | 0.97 | smith-normal-form | 1.47 |
| flat-array | 0.73 | vliw | 0.98 | vector64-concat | 1.52 |
| zebra | 0.75 | nucleic | 0.98 | vector32-concat | 1.54 |
| ray | 0.79 | vector-rev | 0.98 | even-odd | 3.03 |
| mpuz | 0.80 | wc-input1 | 0.99 | fib | 6.54 |
| mlyacc | 0.80 | simple | 0.99 | tak | 7.41 |
| DLXSimulator | 0.82 | count-graphs | 1.00 | tailfib | 9.33 |
| model-elimination | 0.86 |  |  |  |  |

The arm64 run is §20.3's, earlier the same day; the C run is this section's.

### 21.4. What follows

The user leans to arm64 as the default for building the compiler as well as for programs (2026-11-06); nothing is
switched yet, and arm64.md §1's decision stands until the checks below pass and the user decides. What is left:

1. **Releases from an arm64-built stage 2.** `tools/release` runs `run_tests.py --self-hosting --seed ...`, which
   builds stages 2 and 3 through C; it has no backend option. Give it one (passing `--stage-backend arm64`, which
   `tools/check`'s `self-hosting-arm64` already uses with `--fixed-point-only`), run the full self-hosted suite with
   that stage 2 (the JIT, REPL, and pty tests included, since the JIT then runs in an arm64-built host, jit.md §1),
   record the backend in `release.json`, and check `--verify`, `--rollback`, and `--install` on such a release.
2. **The stage caches.** `./quest` keeps C's stages in `.build/quest-stages` and another backend's in
   `.build/quest-stages-BACKEND`, with `QUEST_BACKEND` defaulting to `c` (`quest`, line 21). Decide where the default's
   stages live after the switch, and check that a tree whose cache was built by the old default rebuilds stage 2 rather
   than reusing it (and see the ABI trap: a stale stage 2 after a codegen change).
3. **The default for programs.** The driver's `--backend` defaults to C (`questlang/driver/main.quest`, its usage
   text and its option's default). Survey the tests and goldens that run without a backend and so assume C, `-c`'s
   outputs, `tools/check`'s choice of suites, and the bootstrap, which has no arm64 backend and stays C.
4. **Documents:** arm64.md §1's decision, README.md, release-compiler.md, and roadmap.md where they name C as the
   default.
5. **Optional:** profile the arm64-built compiler compiling the driver for §21.2's 6 to 11 percent, likely calls.
