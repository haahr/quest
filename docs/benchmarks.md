# Benchmarks

Quest has two sets of benchmarks:

- **The MLton suite** (`benchmarks/mlton`): the 46 Standard ML programs of MLton's benchmark suite, each converted to
  Quest, with a runner that checks each conversion's output against the original's and times both. It measures how
  fast Quest programs run against a mature optimizing compiler for a similar language, and it is where Quest's
  performance is tracked (§3).
- **The C backend's measurements** (`tests/perf`): a few small programs that cross polymorphic boundaries or use
  records and variants in hot loops, and the time the backend takes to generate C, for checking that a change to the
  backend does not slow it or its output (`python tests/perf/measure.py`, compared with `tests/perf/baseline.json`).

This document describes the MLton suite, records the baseline taken on 2026-10-28, lists what profiling the
slowest benchmarks found and what could be done about it, compares the C and arm64 backends (§4 to §6),
measures the inliner (§7), times every backend and the inliner's settings at one commit (§11), and measures the
Jupyter kernel's interrupt checks (§12).

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
removed work the other did (§2.3), so the mean without them is reported beside it.

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
would close most of it, for these two benchmarks only.

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
