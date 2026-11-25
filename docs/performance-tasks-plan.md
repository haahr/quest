# Plan: The Performance Tasks Left Open

Ten entries of [tasklist.md](tasklist.md): the eight performance tasks benchmarks.md named as left and nothing had taken
up (collected 2026-11-25), and the two that §47's profile of the compiler added. Each is analyzed first, and made only
if the analysis shows it worth it; what is not made goes into [optimization-experiments.md](optimization-experiments.md)
with its numbers, and its task-list entry is removed either way. The plan is deleted when done.
## 1. Measuring

- **Counts, every step:** instructions retired and cycles, all 46 programs built unit by unit through ssac and arm64
  (`tools/perf/variants.py --separate --backends ssac,arm64`) and counted at a thirty-second of the suite's counts
  (`tools/perf/counts.py --tags ssac,arm64 --against`), against the commit before the step. Counts need no quiet
  machine.
- **The compiler's counts, for the steps aimed at it (1, 8, 9):** the suite does not run the compiler's code, so these
  steps count the compiler itself: each stage 2 (arm64-built, and ssac-built for the gap) compiling the driver through
  arm64 at `-j 1` from an empty build directory, three rounds, under `/usr/bin/time -l`, which reports instructions
  retired and cycles. Instructions repeat to 0.3% between rounds and do not depend on load (§47's rounds: 530.3, 531.8,
  531.5 G ssac-built; 663.9, 666.1, 663.5 G arm64-built), so they need no lock. The arm64-built compiler retires 1.25
  times the ssac-built one's instructions but takes about 1.08 times its cycles, so instructions overstate its gap:
  these steps are judged on cycles as well, and sampled (§47's script, under the lock) only to find where the time
  goes.
- **The bar:** a change that saves under 1% of the instructions of every program it aims at (or of the compiler's,
  for the steps aimed at it) is not made (or is reverted), and is recorded in optimization-experiments.md.
- **Cycles as well as instructions.** §44 found three regressions that counts alone hid (fewer instructions, more
  cycles: a reload's register, a loop's layout). Every step compares cycles too, and a program whose cycles rise by 5%
  or more while its instructions fall is taken apart before the step is kept. This matters most for step 9, since
  optimization-experiments.md §7 records a stall that any shift of a loop's registers can set off.
- **Timing once, at the end:** `run.py time --clean --scale 0.25`, before and after, through C, ssac, arm64, and arm64
  whole program, each in a worktree of its own under the lock (9 to 12 minutes a run by §35's run times, with its
  clean build: about an hour of the lock for the four after, and as much for the four before, which can run at the
  plan's start); MLton's times reused unless its inputs change; the
  results a new section of benchmarks.md. A worktree under the scratchpad cannot build MLton's originals (a directory
  starting with `-`), so a run there takes no `--mlton`.
- **Tests per step:** the suites the step touches (the self-hosted arm64, ssac, and JIT runs, the SSA goldens, the
  encoder; WebAssembly where the step changes the IR or the runtime it shares), and the arm64 fixed point for a
  compiler change. `tools/check` once at the end ([testing.md](testing.md) §4.1).
- **Self-hosted compiler only,** under the two-compilers policy: these change no behavior, so the bootstrap does not
  follow, and behavior goldens stay as they are.

## 2. Order

Small SSA changes first, since they change the code every later step measures, the tables for returning switches
before the rest since it is the largest single item §47 found; then the exception handlers, an IR change that every
backend shares; then four analyses of where arm64 trails ssac (three programs and the compiler's heap), whose
findings are the evidence for the register allocator; then the allocator, the largest change; the collector last,
since it changes collections and so every allocating program's counts and times, and its own measure is memory.
The heap's analysis (step 8) is cheap and feeds the allocator, so it runs early, on its track (§4).

| Step | Task | Kind | Aimed at | Track |
|---|---|---|---|---|
| 0 | Baseline | measure | everything | both |
| 1 | Tables for switches whose arms return | SSA, small | the compiler (`opcodeIndex`, `opcodeName`) | A |
| 2 | An unproxy first made inside a loop, hoisted | SSA, small | loops over records' fields | A |
| 3 | Loads reused across a join | SSA, small | none known yet | A |
| 4 | Fewer exception handlers entered | IR, every backend | knuth-bendix, boyer, model-elimination | B |
| 5 | The small recursions on arm64 | analysis, then arm64 | even-odd | A |
| 6 | arm64 against ssac on the bignum programs | analysis, then arm64 | smith-normal-form, pidigits | A |
| 7 | Spills in very large inlined functions | analysis, then arm64 | ratio-regions | A |
| 8 | The arm64-built compiler's larger heap | analysis | the compiler's memory and collector time | B, first |
| 9 | arm64's register allocator | arm64, large | the compiler; findIndex; what 5 to 8 found | A |
| 10 | The collector's growth target | runtime | memory: the compiler's workers, barnes-hut | B, last |
| 11 | Timing, `tools/check`, write-up | measure | everything | both merged |

## 3. Steps

### Step 0: Baseline

Counts of all 46 at the plan's first commit, the baseline of the steps after it, and the compiler's counts (§1) of
both stage 2s at that commit. The compiler's profile is
benchmarks.md §47 (at `dd931491`, before §46's null tests): the arm64-built compiler takes 1.07 of the ssac-built
one's user time and 1.25 of its maximum resident size; of the samples' difference, 80% is compiled Quest code
(`opcodeIndex` 13% alone, step 1), 19% the collector (step 8), and the rest spread thin over the hash map and vector
functions, `hash.string`, and `equal`, none by more than 570 of 98,571 samples (step 9). Step 9 profiles the compiler
again by §47's script (`benchmarks/mlton/baselines/2026-11-25/compiler-profile.sh`) before and after its changes.
The programs' ratios through arm64 and ssac (§44's times, before §46): even-odd 1.80 of ssac's time,
smith-normal-form 2.16, pidigits 1.16, ratio-regions 1.13; knuth-bendix 0.63, boyer 0.87, model-elimination 0.97
(arm64 already faster: step 4 is about time against MLton, not against ssac).

### Step 1: Tables for switches whose arms return

`nodes.opcodeIndex` is a 54-arm jump table through arm64, each arm a `mov` and an epilogue (288 instructions), 1,682
of the arm64-built compiler's samples against the ssac-built one's 544 (§47). The tables pass takes a switch whose arms
jump with constants to one join, but the simplifier makes a join whose continuation only returns a return in each arm
(`straightened` in `ir/simplify`), so a function whose body is the switch has no join; clang makes the returns a table
of values.

- **Change:** `ssa/passes/tables` takes a switch whose arms each return constants (the same number of them, of the
  same types) as one whose arms jump with them to a join that returns: the table's loads and one return. The default
  arm, and an arm that does anything but return a constant, keep their blocks, as the pass does for jumps now.
  `opcodeIndex` tests its operand for a proxy before the switch (`unproxy`, arm64's low-bit test and a cold call), so
  the range check and the table's load come after that test, on the value it gives.
- **Analysis alongside:** list the functions it applies to over the compiler and the suite (`opcodeName` is likely one:
  396 instructions through arm64 against ssac's 16).
- **Tests:** an `ssa_tables` case of a switch whose arms return, and an SSA golden of a function whose body is such a
  switch (`language/option_switches` has its tables only in `let`s now).
- **Done when:** `opcodeIndex` is a range check and a load through arm64, and the compiler's counts (§1), its cycles
  with its instructions, are measured against the step before; the samples again by §47's script, if the counts
  leave the share of `opcodeIndex` unclear.

### Step 2: An unproxy first made inside a loop, hoisted

`movable` in `ssa/passes/loops` does not list `opUnproxy`, and rotation's walk stops at one (benchmarks.md §22.2 item
6). An `unproxy` of an invariant value is pure, but it may call the runtime (a proxy's original) and must stay after
any check that guards its operand.

- **Analysis:** count, over the suite's SSA after the loops pass, the `unproxy`s inside loops whose operand is
  invariant, and how many are in the hot code of any program (`profile.py`). If none is hot anywhere, record it and
  stop.
- **Change:** `unproxy` movable when its operand is invariant and known not null or checked before the loop; rotation's
  walk continues past one. arm64's unproxy is a test of the low bit and a cold call, so moving it moves the test.
- **Tests:** a `language/` test of a loop over a record's fields whose SSA golden shows one proxy test before the
  loop; the JIT verifier on it.
- **Done when:** that golden holds and the counts are measured.

### Step 3: Loads reused across a join

Value numbering starts a new memory generation at a join unless the join has one predecessor, so a load after an `if`
without an `else` is not reused (benchmarks.md §24.3, batch 7). No benchmark showed one hot then.

- **Analysis first, by a census:** a build that continues a join's generation when every predecessor keeps the same
  one (no store, no call between the dominator's generation and the join), reporting the loads it would merge, counted
  over the suite. Cheap to build, since the rule is local to `ssa/passes/valueNumbers`.
- **Watch:** value numbering can break `ldp` pairs and lengthen live ranges (it cost tailmerge and hamlet 1 to 5%
  once, benchmarks.md §44.1); cycles as well as instructions.
- **Done when:** kept with an `ssa_valueNumbers` case, or recorded.

### Step 4: Fewer exception handlers entered

A `try` whose body cannot raise still pushes a handler, and a raise to a handler in the same function goes through
the runtime rather than jumping (benchmarks.md §3.5; arm64.md §6.2). Inlining makes the second commoner.

- **Analysis:** count, in knuth-bendix, boyer, and model-elimination, the handlers entered and the raises taken per
  iteration (a runtime counter under a check mode, or a census of the IR after inlining), and what share of their
  time is the push and the raise through the runtime (`profile.py`). If both together are under 1% of each
  program's samples, record and stop: this is the only step that changes the IR under every backend, the JIT's and
  WebAssembly's exception lowering included, and arm64 already takes less than ssac's time on all three (step 0), so
  the gain is only against MLton, and the bar is firm.
- **Change, in the IR, so every backend gains:** a `try` body with no call, no raise, and nothing that can raise
  (checked arithmetic, bounds, null, and the interrupt checks that `settings.interruptChecks` adds for the Jupyter
  kernel, which raise) needs no handler, so the rule is decided where those checks are known, or treats a
  loop as able to raise whenever they may be on; a `raise` whose nearest handler is in the same function, with
  no frame between, is a jump to the handler with the payload. The handler's matching (which exceptions it catches,
  `reraise` of the rest) stays the same code. The JIT and WebAssembly take the IR as it comes; check that
  WebAssembly's exception lowering (wasm.md) accepts a handler reached by a jump as well as by a raise.
- **Tests:** `language/` tests of a `try` whose body cannot raise, of a raise caught in the same function (and one
  that is not caught there and goes up), and of a raise inside an inlined callee caught by the caller; their outputs
  are shared behavior goldens, so the bootstrap writes them; every mode, WebAssembly included; the stress tier, since
  handlers are roots.
- **Done when:** both are in and measured on the three programs, or recorded.

### Step 5: The small recursions on arm64

even-odd takes 1.8 times ssac's time through arm64, since clang reduces its loop further after `tailJumps` (§14.2).
fib, tak, and tailfib are clang's folding, not chased (§27.3).

- **Analysis:** the hot loop through both backends side by side (`tools/perf/asmstats.py`, the ssac binary's
  disassembly): what clang does that arm64 does not (a strength reduction, a parity test folded, the two functions'
  loop merged).
- **Change:** only if what clang does is a rule that applies beyond this program; a program-specific fold is recorded
  and not made.
- **Done when:** named, and fixed or recorded.

### Step 6: arm64 against ssac on the bignum programs

smith-normal-form takes 2.16 times ssac's time through arm64, pidigits 1.16, by §44's times (§35.3, before §44, had
1.94 and 1.20); the analysis times both again at the step's commit before comparing. §46's null rule took their arm64
instructions to 0.914 and 0.917, but nothing has taken apart what is left.

- **Analysis:** profile both through both backends; compare `mulLimbs`, `addLimbs`, and the division loop with
  `asmstats.py`: instruction count per limb, loads and stores per limb, the carries (`adds`/`adc` against a compare
  and an add), spills in the inner loop.
- **Change:** local fixes in selection or the peephole pass are made here, each with an `arm64_select` case; anything
  that is the register allocator's goes to step 9 with its count per limb.
- **Done when:** what is left is named, and each part fixed or handed to step 9 or recorded.

### Step 7: Spills in very large inlined functions

ratio-regions' `preflowPush` (12,682 instructions) had most of its hot samples on spills and reloads, and on loads of
the queue array from a global on every bucket (benchmarks.md §9); 1.13 of ssac's time after §44.

- **Analysis:** profile it again; sort its hot samples into spills, reloads, the global's loads, and the rest. The
  global's load may now be §25's module cell kept across a loop (`ssa/passes/loops`), if the loop meets its rules;
  find which rule it misses.
- **Change:** a loops-pass rule widened, if that is what misses; spills go to step 9.
- **Done when:** named, and fixed, handed to step 9, or recorded.

### Step 8: The arm64-built compiler's larger heap

The arm64-built compiler's heap is 1.25 times the ssac-built one's at its largest compiling the driver (6.9 against
5.5 GB at `-j 1`), and its collector takes 1,640 more samples (§47). The two compile the same source, so the difference
is in what their code keeps reachable: a value in a spill slot or a callee-saved register past its last use, which a
stack map counts as live, is the likeliest cause.

- **Analysis, in order:** §47 measured the maximum resident size, not what is live, so first rule out the simpler
  causes. With `tools/perf/gcstats.py` on both compilers compiling the driver at `-j 1`: the bytes each allocates, the
  number of collections and where they fall, and the live bytes after each. If the arm64-built code allocates more
  (a box or a closure ssac's C does not make) or collects at other points, that is the cause, and it is named there.
  Only if the live bytes after a collection differ, which frames' stack maps keep more (`retention.py dead`, the
  words a precise collector would not keep).
- **Change:** if it is the allocator's (a callee-saved register or slot keeping a dead pointer), it goes to step 9,
  with the frames named; if it is the stack maps' own precision (a map marking a slot live past its value's last use),
  it is fixed in the maps.
- **Done when:** the cause is named, and fixed, handed to step 9, or shown to be the maps' precision and recorded.

### Step 9: arm64's register allocator

The arm64-built compiler takes 1.06 of the ssac-built one's time (§45). What §22 left is the allocator's: copies at a
loop's join, a spill reloaded each round in hashMap's `findIndex`, and an `ldr` then a `mov` where one `ldr` would do
(§24.1 item 5; §38.3 item 7). `883a870d` made a join take its hot predecessor's register; hint-following and full
coalescing were tried and not kept (arm64.md §6.1). Steps 5 to 8 add what they find.

- **Analysis:** the three costs counted over the suite and the compiler, from the machine code: moves at joins,
  reloads inside loops of a value not redefined there, and a load into a scratch register then moved. That count,
  with §47's profile, says which of them matters.
- **Changes, in this order, each measured alone and kept only if it pays:**
  1. a load whose result is only moved takes the move's destination (no `ldr` then `mov`);
  2. conservative (Briggs) coalescing of a join's parameter with its arguments, as arm64.md §6.2 proposes: coalesce
     only when the merged interval's neighbours with significant degree stay fewer than the registers, so no new
     spill is made, unlike the full coalescing that was not kept;
  3. a value live across a loop but not redefined in it, spilled, reloaded once before the loop where a register is
     free for the loop, rather than in each round. This is spill placement, like optimization-experiments.md §6's
     "values live only across a cold call" (not started); if one placement rule serves both, it is one change, and
     §6's entry is updated with what it finds.
- **Watch:** the register-dependent stall (optimization-experiments.md §7): any change here shifts registers across
  the suite, so cycles are compared program by program, and peek, fib, and tak are checked by name.
- **Tests:** `regalloc_scan` and `arm64_*` cases for each; the arm64 fixed point; the JIT, which uses the allocator.
- **Done when:** `findIndex`'s probe loop has no copy at its join and no reload each round, and the compiler's gap
  and the suite's counts are measured; or judged not worth it and recorded.

### Step 10: The collector's growth target counts a recyclable block as in use

After the compiler's collections the blocks in use are 3.2 times the live lines and 6.6 times the live bytes, so a `-j
8` worker's heap reaches 2.2 GB for 223 MB of data (§16.3), barnes-hut 451 MB for 3 MB live (§17.2).

- **Analysis:** at each collection of the compiler's driver build and of barnes-hut, the target as computed now and
  as it would be from live lines (a debug print under `QUEST_GC_STATS`), and how many more collections the lower
  target would make.
- **Change:** the target after the sweep (`quest_gc_sweep`, `runtime/quest_gc.c`; collector.md §9.6) counts live lines
  rather than blocks in use, with a floor so a small heap does not collect constantly. The WebAssembly runtime's
  allocator, if it computes a target the same way, changes with it, in the same step. A change to the runtime alone
  does not empty the stage caches, so a stage 2 built before it looks fresh: remove `.build/quest-stages*` (or bump
  the ABI, if a header's layout changes) before building or measuring after it.
- **Measure:** maximum resident size (`/usr/bin/time -l`) of the driver build at `-j 8` and of the suite's largest
  heaps, and the suite's counts (more collections are more instructions); the times in step 11.
- **Tests:** the stress tier and the collector's own tests.
- **Done when:** the target counts live lines and memory and time are measured; kept if memory falls without the
  suite's time rising by more than 1%.

### Step 11: Timing, `tools/check`, write-up

The timing of §1, a benchmarks.md section with each step's counts and the times, the task-list entries removed,
optimization-experiments.md holding what was not made, `tools/check`, and this plan deleted. Done once, by one
session, after both tracks (§4) are on main.

## 4. Two tracks, two sessions

The steps fall into two sets that touch different files, and each step is measured against its own parent commit by
counts that need no quiet machine, so two sessions can make them at once, each in a worktree of its own:

| Track | Steps | Files |
|---|---|---|
| A: the SSA and arm64's code | 1, 2, 3, 5, 6, 7, 9 | `ssa/passes/*`, `codegen/arm64`, `codegen/machine/regalloc` |
| B: the IR, the heap, the runtime | 8, 4, 10 | `ir/*`, each backend's handlers, `quest_gc.c`, wasm's allocator |

- **What crosses between them.** Step 8's finding feeds step 9: B does 8 first and hands what the allocator keeps
  alive to A (a task-list note or a message) before A starts 9. Step 10 changes every allocating program's
  collections, and so their counts: B lands it on main only after A has measured step 9, so that A's last comparisons
  do not mix the two. Step 4 changes only exception code, which no step of A touches.
- **Each track's baseline.** Each session takes step 0's counts at its own first commit, and rebases only between
  steps, counting again after a rebase that brought the other's changes.
- **The machine.** Counts and the compiler's counts (§1) need no lock, but each step's suites and fixed point load the
  machine, and two sessions running them at once lengthen each other's runs (arm64-whole's slow tests have 120 s;
  tools/check runs a timeout again alone). Neither runs its suites while the other holds the lock for a timing.
  Sampling (§47's script) and `run.py time` take the lock and wait for a quiet machine as always.
- **Why not one session.** One could make every step in order; it would only make step 4, long and touching every
  backend, wait behind the allocator work, or the allocator behind it, though neither needs the other.
