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
(`tools/perf/pcprof.c`, built into `.build/perf/pcprof.dylib`) into the program with `DYLD_INSERT_LIBRARIES`. It
records the program counter every millisecond of CPU time, and names each sample's image and symbol at exit:

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
- **Kernel samples are left out** unless `--kernel` is given. The collector's marker threads wait in the kernel, and
  a signal for the process may land on one of them.

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

runs each with `GC_PRINT_STATS=1` and summarizes: collections, total marking time, bytes freed, the live pointer
data at collections (median and largest), and the largest heap. Builds from the same SSA free the same, so when
their live data differ, the build with more is keeping dead objects alive: the collector scans the stack and
registers conservatively, and a stack slot holding a dead value's pointer keeps what it points to. In mlyacc at
`6f7cb100`, arm64's live data was 3.5 times ssac's, and marking took twice as long. Running at `--count 1` shows
whether the retention is within one iteration or of earlier ones.

To find the frames responsible, stop the program in lldb at a collection, with a breakpoint on `GC_stopped_mark`,
and walk the stack in lldb's Python:

- **Frame sizes:** the difference between consecutive frames' `GetSP()`, for each frame of
  `lldb.thread`. A frame much larger in one build than the other is a suspect (mlyacc's `main`: 7.7 KB under arm64,
  1 KB under clang).
- **Pointers in a frame:** read the frame's memory (`process.ReadMemory(lo, hi - lo, error)`) and count the words
  that fall in the collector's heap, which is the `VM_ALLOCATE` regions that `vmmap PID` lists. Calling `GC_base`
  from an lldb expression does not work there, since the collector holds its lock.

Run lldb with `--batch` and `-o` commands (`b GC_stopped_mark`, `process launch -o /dev/null -- COUNT`, `c` to
skip collections, then `script ...`), from a directory with a copy of `DATA/`.

## 7. Unwind information

A program that raises and catches often walks its stack at each raise (exceptions.md §5). Each frame described by
DWARF CFI rather than a compact unwind entry costs libunwind a parse. `objdump --unwind-info BINARY` lists each
function's encoding; on arm64, `0x03...` is DWARF, `0x04...` a frame, and `0x02...` frameless. A Quest function with
`0x03` is one the linker could not compact, and samples in `libunwind.dylib` in §4's profile show what it costs.
