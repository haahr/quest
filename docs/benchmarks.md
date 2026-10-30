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
slowest benchmarks found and what could be done about it, and compares the C and arm64 backends (§4).

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
an option value.

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

Step 11 of [arm64.md](arm64.md) (linear scan) asks for dated run and compile times for both backends; these are the
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
functions (arm64.md step 11) are to be measured.

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
