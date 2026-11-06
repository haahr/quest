# Profiling Generated Code

How to find out why a compiled Quest program runs as fast as it does: which backend's code is slower and by how
much, where in the code the time goes, and what the collector is doing. The tools are in `tools/perf/`, and run
with Homebrew's Python (`python3.11`) on macOS on arm64. [arm64-performance-review.md](arm64-performance-review.md)
is an example of their use. For whole suites, use `benchmarks/mlton/run.py` ([benchmarks.md](benchmarks.md)), and for
the compiler's own speed, `tests/perf/measure.py` ([testing.md](testing.md)).

## 1. The approach

The same program, built by different backends from the same source, separates the causes of a difference:

- **`c`**, the C backend: the IR printed as C, compiled by clang `-O2`.
- **`ssac`**: the SSA printed as C, compiled by clang `-O2`. It calls the runtime as arm64 does and starts from the
  same SSA, so `ssac` against `c` is what the SSA (its builder and its passes) costs, and arm64 against `ssac` is
  what the code generator costs.
- **`arm64`**, the native backend.

Then, for the factor that matters: time the builds against each other (§3), profile both to find the functions and
the instructions where they differ (§4), compare their instruction mix (§5), and check the collector (§6). Two builds
from the same SSA allocate exactly the same, so a difference in the collector's work is a difference in what the
generated code leaves on the stack.

Before any of this, rebuild: a build directory's objects are not rebuilt when the compiler changes, which is why
`variants.py` starts each build in a fresh one.

## 2. Building the variants

```bash
python3.11 tools/perf/variants.py life ray hamlet mlyacc zebra nucleic
```

builds each benchmark (`benchmarks/mlton/NAME.quest`) with each backend, as whole programs, into
`.build/perf/NAME.BACKEND`. `--backends ssac,arm64` chooses backends, `--separate` compiles units separately, `--dir`
puts the binaries elsewhere, and `--emit-c` also writes the C of the `c` and `ssac` builds (`NAME.BACKEND.c`), for
experiments that change the C and rebuild it by hand: marking functions `noinline`, say, to see what clang's inlining
is worth.

## 3. Timing

```bash
python3.11 tools/perf/timeit.py life ray hamlet mlyacc zebra nucleic
```

runs `.build/perf/NAME.TAG` for each tag (`--tags`, by default `c,ssac,arm64`), the tags of one benchmark in turn
within each of three rounds (`--rounds`), and prints each one's least user time and its ratio to the first tag's.
Running them in turn, rather than all of one then all of the next, means that a change in the machine's load affects
them alike, and the least of a few runs is what the code can do when nothing interferes. Each runs in a scratch
directory with a copy of `DATA/`, at a thirty-second of the suite's count (`--scale`, `--count`), which takes one to
three seconds.

User time leaves out the system's: ray writes its output a character at a time and spends most of its elapsed time
in the kernel. On a loaded machine, differences under about 5 percent are noise; check the load average first.

## 4. Where the time goes

`sample(1)` attributes time to functions only, and Instruments needs Xcode. `profile.py` loads a small sampler
(`tools/perf/pcprof.c`, built into `.build/perf/pcprof.dylib`) into the program with `DYLD_INSERT_LIBRARIES`. A
thread of its own wakes every millisecond, records the program counter of each of the program's threads that is
running, as `sample` does, and names each sample's image and symbol at exit. It does not use `SIGPROF`: macOS posts a
profiling timer's signal when the thread next returns to user mode, usually from a system call, so a program that
calls the system now and then had its samples piled on the calls (wc-scanStream showed 88 percent in `read`, where it
spends 2).

```bash
python3.11 tools/perf/profile.py .build/perf/life.arm64
python3.11 tools/perf/profile.py .build/perf/life.arm64 -f qf_nthgen
python3.11 tools/perf/profile.py .build/perf/life.arm64 -f qf_nthgen --listing
```

The first prints the samples of three runs (`--runs`) by image and by symbol. The second adds `qf_nthgen`'s hottest
instructions, and the third every instruction of it, each with its samples, in the order of the code, which is the
view to read a loop in.

Reading it:

- **Profile both builds.** A function that is hot in one and not the other may be inlined in the other: clang inlines
  freely, so its time is in the caller. Mark the function `noinline` in the `ssac` build's C to compare it alone.
- **A sample lands on the instruction after a stall.** A load that waits shows as samples on the instruction that
  uses its result, or on itself if the stall is the load's address. A load just after a store to the same slot waits
  for store-to-load forwarding, so samples piling up on stack loads in a loop mean a value in the loop goes through
  memory.
- **Compare within a binary, not totals across runs.** A process migrates between performance and efficiency cores,
  so the totals of two runs differ by more than their code does; `timeit.py` compares totals.
- **Kernel samples are left out** unless `--kernel` is given. A thread blocked in the kernel, such as an idle marker
  thread of the collector's, is not sampled at all; a kernel sample is of a thread running a system call, at its
  user program counter in `libsystem_kernel`.
- **The count of samples is wall time,** a sample a millisecond for each running thread, so a loaded machine, on
  which the program waits for a core, gives fewer, and the collector's marker threads add theirs while they mark.

## 5. Instruction mix

```bash
python3.11 tools/perf/asmstats.py .build/perf/life.ssac .build/perf/life.arm64
python3.11 tools/perf/asmstats.py .build/perf/life.ssac .build/perf/life.arm64 -f qf_nthgen
```

counts, in every Quest function of each binary (`qf_`, `qv_`, and `main`), or in the functions named, the kinds of
instructions: branches, calls, moves, loads and stores to the stack and elsewhere. It also counts patterns that show
what one code generator folds and the other does not: `ldp` and `stp` outside the frame, register-offset and
shifted operands, a global loaded by `adrp`, `add`, `ldr`, a load followed by a move of its result, a `Bool` masked
after a call, and a real constant made in an `x` register. The counts are static, of the code, not of what runs, so
they say what to look for, and a profile says whether it matters. In a loop that chases pointers, extra instructions
are often free; extra stack loads on the chain are not.

## 6. The collector

```bash
python3.11 tools/perf/gcstats.py .build/perf/mlyacc.c .build/perf/mlyacc.ssac .build/perf/mlyacc.arm64
```

runs each with `QUEST_GC_STATS=each` and summarizes: full and minor collections, the time each kind's pauses
took, bytes allocated, the live data at full collections (median and largest), and the largest heap. Builds from the same SSA allocate the same, so
when their live data differ, the build with more is keeping dead objects alive: the collector scans the stack and
registers conservatively, and a stack slot holding a dead value's pointer keeps what it points to. In mlyacc at
`6f7cb100` (under the Boehm collector), arm64's live data was 3.5 times ssac's, and marking took twice as long.
Running at `--count 1` shows whether the retention is within one iteration or of earlier ones.

The live data at the collector's own collections is a poor measure, though: it collects where its heuristics say,
which depend on what the program keeps alive, so two builds (and two runs of one build: mlyacc's 96 iterations took
286 collections in one run and 673 in another) are measured at different points. Compare builds at the same points
instead:

```bash
python3.11 tools/perf/retention.py live .build/perf/mlyacc.c .build/perf/mlyacc.ssac .build/perf/mlyacc.arm64
```

forces a collection every 20,000 allocations (`--every`) with the runtime's `collect` mode (`QUEST_GC_CHECK=collect`
and `QUEST_GC_COLLECT_EVERY`), and prints the live data there: the median and the largest for each binary, and the
points where the others differ most from the first. Builds from the same SSA allocate the same, so each point is the
same point of the program in every build.

To find what keeps it alive at one of those points:

```bash
python3.11 tools/perf/retention.py dead mlyacc --at 120
```

builds the program with the arm64 backend and `QUEST_LIVE_SLOTS=1` into `.build/perf/live/`, with its assembly
beside it, runs it to the 120th forced collection in lldb, and prints each word of each Quest frame that points into
the heap but holds no value live across the call the frame is in: what a precise collector would not keep. With
`QUEST_LIVE_SLOTS=1`, the backend puts a symbol at each call's return address and, as a comment before it, where the
values live across the call are (their slots, as offsets from `sp`, and their registers) and the frame's size below
its saved registers; the code is the same as without it. A word is DEAD if it is in one of the frame's own slots, and
SAVED if it is a callee-saved register the frame saved for its caller, whose own annotation says whether it is live.
The annotated assembly then shows where a DEAD word's slot was written and where its value should have been cleared.
`tools/perf/lldb_frames.py` has the lldb command (`deadroots`), which stops at the collection
(`QUEST_GC_COLLECT_TRAP`, a breakpoint on `quest_gc_trap`) and reads the heap's range from the runtime's
`quest_gc_heap_lo` and `quest_gc_high_water`.

This found the two leaks of arm64-performance-review.md §4's actuals: values dying as a jump's argument were never
cleared, and a loop header's parameters that nothing reads were stored by the back edge every time round. With them
fixed, mlyacc's `main` had no DEAD words.

## 7. Unwind information

A program that raises and catches often walks its stack at each raise (exceptions.md §5). Each frame described by
DWARF CFI rather than a compact unwind entry costs libunwind a parse. `objdump --unwind-info BINARY` lists each
function's encoding; on arm64, `0x03...` is DWARF, `0x04...` a frame, and `0x02...` frameless. A Quest function with
`0x03` is one the linker could not compact, and samples in `libunwind.dylib` in §4's profile show what it costs.
