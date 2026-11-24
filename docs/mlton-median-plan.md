# Plan: Closing the Median Programs' Gap to MLton

A plan for what [benchmarks.md](benchmarks.md) §38 found: why the programs in the middle of the MLton suite retire 1.4
to 3.7 times MLton's instructions through arm64 (0.9 to 2.0 through ssac). Part 1 (§3) makes the cheapest changes, the
ones §38.4 estimates. Part 2 (§4) takes the rest of §38.3. Each step is measured by counts, which a loaded machine
barely changes (§2), and timed only at the end of each part.

Self-hosted compiler only, except where a step changes a library module or the runtime, which both compilers and every
backend share. The two-compilers policy holds: behavior goldens stay shared and are written by the bootstrap; IR, SSA,
and C goldens are each compiler's own. A step that changes the runtime or a library module changes the WebAssembly
backend too, in the same step ([wasm.md](wasm.md)); the SSA's passes do not reach it, since it starts from the IR.

## Status (2026-11-23)

Done and pushed, counted in [benchmarks.md](benchmarks.md) §40: steps 0, 1, 2, 3, 4, 6a, 7, and part of 13 and 16
(a proxy's slow path cold, a join taking its hot predecessor's register). Tried and not kept: `precedes` and `equal`
expanded inline (step 2), and the entry's unread parameters left out (step 15). Step 5 is measured and has two designs;
the user chose neither for now.

Timed in [benchmarks.md](benchmarks.md) §41, which found two regressions, fixed in local commits not yet pushed: step
4's replay put a move on matrix-multiply's loop chain (`82cc5e55`, see step 4), and the runtime's frame cache made
zebra take twice as long in some runs (`69f83386`). With both, against MLton's time: ssac 1.21, arm64 1.68, arm64
whole program 1.64 (§35's 1.25, 1.79, 1.85).

Part 2, analyzed and not made (local, not pushed): steps 11 and 24, under the plan's threshold; step 12, worth 6 to 9%
on lexgen but needing a whole-program analysis of a field's values (designed, tabled by D5); step 19's census
(`allocations.py --by-layout`); step 20, folded into 21, since alone it saves about 5% of logic's and raytrace's
bytes and 0.6% of the compiler's. Step 21, and step 20 with it, abandoned by the user (2026-11-24): not worth the
cost (§4.3). Step 23 analyzed: 4 to 10% on mpuz and logic, nothing
elsewhere (the user to decide). Not started: 6b, 8 to 10, 14, 17, 18, 25, 26. Tabled as whole-program only (D5): 5a, 12, 22.

Conversions changed (2026-11-23, [benchmarks.md](benchmarks.md) §42): an owner's own `ref` is a `var` field in boyer,
logic, model-elimination, mpuz, and ratio-regions (mpuz 0.90 to 0.94 of its instructions, logic 0.97), and loops stay
recursive, measured against hand-written loops for steps 25 and 26 (§4.4). The changed mpuz and logic are step 23's hand-made
variants (mpuz retires the same 0.940 and 0.896), so the conversions now have its gain; what is left of step 23 is
the compiler finding the pattern in code written the nested way, which no program in the suite now is.

## 1. Decisions

Made by the user on 2026-11-23:

- **D1, `conv.int` in Quest,** not C (step 1).
- **D2, NaN checks deferred, with the exact site recovered** on the cold path (step 4), so that no program's behavior
  changes.
- **D3, the start bit still set by each allocation, more cheaply** (step 6a). The bitmap built at collection (6b) is
  taken only if 6a's counts show that the bit is still a large part of the fast path and 6b's design looks meaningfully
  cheaper; the step reports which.
- **D4, the representation changes as specific steps** (§4.3), each measured before it is made, each stopping the
  section if it does not pay.

- **D5, whole-program-only steps tabled** (2026-11-24). Most Quest programs are expected to be built unit by unit,
  so a change that gains only in whole programs leans toward tuning the benchmarks rather than the compiler as it is
  used. Steps 5a, 12, and 22 are kept as designs and not made; the whole-program system is still measured, but no
  step aims at it alone.

**Pushing:** Part 1 was pushed on 2026-11-23, after a rebase onto `6921cbe2`, which had taken ABI 89 for its own
externals, so step 1's is 90. Each step was tested by targeted suites (the arm64 fixed point, each backend's run of
every program, the stress tier for step 6a), not `tools/check`, at the user's request. Later steps are committed and
wait for the user to push them.

## 2. Measuring

**Step 0: `tools/perf/counts.py`.** The script §38 used, made a tool:

- it runs the programs named, built by `variants.py` and by MLton, at a count;
- it writes their instructions retired and cycles (`/usr/bin/time -l`) and allocation (`QUEST_GC_STATS=1`, MLton's
  `@MLton gc-summary --`) to a JSONL file;
- `--against FILE` prints each program's ratio to an earlier file's.

The baseline is §38's eight at `184fac25`, with checksum, zern, and wc-input1 added (their causes are among §38.3's
too). Each step records the counts of the programs it is aimed at before and after, in its commit message, and the
whole set at the end of each part. A change that moves instructions retired by less than 1% is noise from the
programs' own variation (allocation addresses, hash orders), not from load.

Timing waits for a quiet machine: `run.py time --clean --scale 0.25` through arm64, ssac, and arm64 whole program, at
the end of each part, recorded as a new section of benchmarks.md.

**Done** (`tools/perf/counts.py`, profiling.md §3.1): `--tags mlton,ssac,arm64`, `--results`, `--against`,
`--scale` (a thirty-second by default), `--count`; MLton's binaries are copied from `run.py`'s builds. The baseline is
`benchmarks/mlton/baselines/2026-11-23/counts-73bb9e45.jsonl`, and Part 1's result `counts-5e9365cc.jsonl` (both
commits before the rebase). `./quest --no-exclusive` was added alongside, so a stage build need not wait for the lock.

## 3. Part 1: the cheapest changes (§38.4)

In order of instructions saved per line changed. Each is independent of the others.

### 3.1. Step 1: `conv.int` without `snprintf`

`quest_conv_int` (runtime/quest_stdlib.c) formats with `snprintf`, about 500 instructions a call; lexgen calls it
2.4 million times per run at count 48, 23% of its gap (§38.3 item 5).

**It can be written in Quest now, and already beats the native one.** Everything it needs is fast:

- `string.new(size, init)` is one runtime call (`quest_string_alloc`, two allocations and a `memset`);
- `string.setChar` and `ascii.char` are expanded inline by the SSA (`externalOperation`, `ssa/build/calls`): a null
  check, a bounds check, and a store; and a range check;
- division by the constant 10 has no check for a zero divisor.

This version counts the digits of the magnitude, allocates the string once, and fills it from the end. Quest's `/`
truncates toward zero, and its binary operators need braces to group (`q * 10 - m` is `q * {10 - m}`):

```
let int(n: Int): String =
    begin
        (* The negative magnitude holds every Int, the least included *)
        let var m = if n < 0 then n else 0 - n end
        let var digits = 1
        let var rest = m / 10
        while rest isnot 0 do
            digits := digits + 1
            rest := rest / 10
        end
        let sign = if n < 0 then 1 else 0 end
        let s = string.new({digits + sign} '0')
        if n < 0 then string.setChar(s 0 '~') end
        for i = {{digits + sign} - 1} downto sign do
            let q = m / 10
            string.setChar(s i ascii.char(48 + {{q * 10} - m}))
            m := q
        end
        s
    end
```

Built by the release at `63d0105a` and run on 2,000,000 Ints of 4 to 11 digits, it gives the native version's string
for 0, 1, 9, 10, 99, 100, their negations, and the greatest and least Int. Instructions retired per call, the loop
around it included:

| What the loop calls | Instructions |
|---|--:|
| `string.new(11 '0')` alone | 224 |
| `conv.int` (`snprintf`) | 994 |
| The Quest version | 613 |

So the Quest version costs about 390 instructions beyond its allocation against the native one's 770: about 37 a digit,
since it divides twice per digit. The step tries one division per digit (the count by comparisons with powers of ten,
or digits written right to left into a string of the greatest length and copied with `getSub`) and writes a C digit
loop as a yardstick, only to record how close the Quest version comes (D1 keeps Quest).

The Quest version also changes:

- `lib/conv.mod.quest`, which becomes a module with code (it imports `string` and `ascii`, neither of which imports
  `conv`);
- the WebAssembly backend's special case for `quest_conv_int` (`wasm/codegen`), which goes, the Quest code compiling
  to WebAssembly like any other;
- the interpreters' builtins (`interpreter/builtins`, the bootstrap's), whose entries go, the interpreters running the
  Quest code; their tests' times are watched, since a treewalk runs the loop step by step.

`conv.real` is left alone: it formats the shortest digits that read back as the same real, which Quest code should not
reimplement for a gain nothing has measured.

**Tests:** `stdlib/conv_*` (every Int's form, including 0, ~1, the least and greatest Int, and powers of 10 and one
less); the behavior goldens, unchanged. **Measure:** lexgen, and `benchmarks/mlton` programs that print numbers.

**Done.** The digits are counted by comparisons with powers of ten (minus ten to the power, up to 10^18), so each
digit costs one division. The WebAssembly backend's case and both interpreters' builtins went; `conv` imports `string`
as `stringOp`, since it now exports a `string` of its own (`6921cbe2`). `language/thunks`, which bound the external,
binds `word.popCount`'s instead. No C yardstick was written. lexgen: 0.843 of before through ssac, 0.861 through arm64.

### 3.2. Step 2: string comparisons expanded inline

`stringOp.precedes` is `quest_string_precedes`: a frame, a null check, and a `memcmp` call. In lexgen the strings
differ at their first byte 90% of the time (about 45% of its gap). `stringOp.equal`, logic's `quest_string_equal`, is a
call where MLton compares pointers.

`externalOperation` (`ssa/build/calls`) expands both, with `representation.choose` for the branches, as it does
`quest_string_length`:

- **equal:** the same pointer is equal; different lengths are not; otherwise the call.
- **precedes:** both non-null (else the call, which raises); if both are non-empty and their first bytes differ, the
  unsigned comparison of those bytes; otherwise the call.

The cold call keeps every case the runtime handles, so behavior cannot change.

**Tests:** an SSA golden showing the expansion; `stdlib/string_*`, unchanged. **Measure:** lexgen, logic.

**Done, differently.** The inline expansions were built and not kept. lexgen's keys all begin with a space, so a
test on the first byte never decided and cost lexgen 9%; `equal` as a same-pointer test saved logic 0.6% through ssac
and 0.3% through arm64, under the 1% bar. What was kept is in the runtime: `quest_string_precedes` compares up to 16
bytes itself, then calls `memcmp`. lexgen: 0.94 through ssac, 0.96 through arm64. Test: `stdlib/string_comparisons`.

### 3.3. Step 3: checks that a dominating check decides

Every array access checks for a null array and for its index against the length (`elementAddress`,
`ssa/build/aggregates`), as every string access does (`byteAddress`). A check ends a block, and value numbering
removes repeated comparisons only within a block (by design: arm64 fuses a comparison into its branch there), so a
check that an earlier one on the same values already decided is made again, and so are the loads after it. fft's
butterfly makes 24 null checks and 24 bounds checks for its 8 elements, and loads 16 (64 of arm64's 228 instructions).

A new pass, `ssa/passes/conditions`, after value numbering: along the dominator tree it records, for each edge of a
conditional branch on a comparison, the fact the edge establishes (`a == null` false, `i < n` unsigned true), keyed by
the comparison's operands' value numbers. A branch on a comparison that a recorded fact decides becomes a jump. Value
numbering then runs once more, so that the loads the removed checks separated are merged.

Unsigned less-than also decides a weaker one: `i < n` decides `i < n'` where `n'` has the same value number as `n`
(the same array's length), and `j < n` where `j` is `i` (the common case after value numbering). Nothing more general
than equal value numbers is attempted in this step.

**Tests:** `questlang/ssa_conditions` (hand-built SSA: a repeated null check, a repeated bounds check, a check on
another array kept, a check not dominated kept); `language/*` SSA goldens regenerated. **Measure:** fft, mpuz,
matrix-multiply.

**Done.** Facts are made at a block that one edge of a branch alone enters, and hold in the blocks it dominates.
Operands are keyed by what they are where value numbering keeps them apart (constants, nulls, symbols, invariant
loads); an equality also gives its negation; only the same comparison is decided, not the weaker unsigned ones. A
decided branch becomes a jump, unreached blocks go, and a changed function is numbered again. Through arm64: fft
0.812, matrix-multiply 0.967, mpuz 0.973; ssac unchanged, since clang already removed them.

### 3.4. Step 4: NaN checks where a value is observed

`Real` arithmetic raises `real.error` on a NaN result ([arm64.md](arm64.md) §3, `ssa/build/calls`: `opIsNaN` and a
check after each `++`, `--`, `**`, `//`). That is 126 of `tfoCombine`'s 203 instructions over MLton's, 48 of fft's
butterfly, 16 of mandelbrot's loop.

A NaN operand makes each of the four operations' result NaN, so in a chain of them, a check of the last result finds
any NaN an earlier one made. The builder keeps its checks, and a new pass, `ssa/passes/nanchecks`, removes a check on a
value whose only uses are as an operand of another checked real operation in the same block. The check that remains
is on the chain's last value.

What changes is where the error would be raised: at the first operation that made a NaN, today, with its source site.
To keep that exactly, the remaining check's cold path does not raise directly. It branches to a block that recomputes
the chain from its inputs, checking each result in order, and raises at the first NaN, with that operation's site.
The values are pure and the operations deterministic, so the recomputation finds the same first NaN. Nothing between
the operations is observable: they are in one block, and the pass stops a chain at anything other than a real
operation.

So no program's behavior changes, and no backend or interpreter has to follow. The rule stays as written.

**Tests:** `questlang/ssa_nanchecks` (a chain, a chain with a use outside it kept, the recomputation block);
`language/real_errors` (or its equivalent) extended with NaNs made at each position of a chain, each raising at its
own site, in every mode. **Measure:** nucleic, fft, mandelbrot, matrix-multiply.

**Done, wider than a block.** A region is blocks joined by checks' good edges, each entered only from the last,
storing nothing and calling nothing. A check goes when its value comes from `fadd`, `fsub`, `fmul`, or `fdiv` and every
use is such an operation in the region. A failing check jumps to the region's replay, which raises at the original
site. The pass, `ssa/passes/nanChecks`, runs before value numbering. Tests: `tests/errors/run/nan_chain_1` to `3`,
which raise at each operation of a chain, in every mode. Against the baseline, through ssac and arm64: nucleic 0.824
and 0.864, matrix-multiply 0.876 and 0.934, zern 0.964 and 0.936, mandelbrot 0.994 and 0.947.

**Fixed after timing** (`82cc5e55`). The replay read every value the region's blocks read, the running sum of
matrix-multiply's dot loop among them, so that sum stayed live past the next and arm64 moved the next sum back into
its register on each iteration: 1.31 times the time, with fewer instructions. The replay now stops before the last
check's block and jumps to its raise, since when every earlier check passes, the last is the one that failed.
matrix-multiply takes 0.66 of the step's time through arm64 ([benchmarks.md](benchmarks.md) §41).

### 3.5. Step 5: fewer proxy tests (two designs, the user to choose)

A tuple or option type whose values may be proxies (`mayBeProxied`, `repr/layout`; [runtime-design.md](runtime-design.md)
§2.3) has every read of its tag, payload, or field preceded by `tbnz wN, #0` and a cold call. **Measured** (2026-11-23,
a build in which `mayBeProxied` is always false, unsound but exact for these programs, which make no proxies):
instructions retired against the baseline, through ssac and arm64, tyan 0.739 and 0.728, logic 0.834 and 0.800, mpuz
0.825 and 0.757, lexgen 0.706 and 0.703 (with steps 1 and 2, which alone gave 0.794 and 0.823). The tests are 17 to 27%
of what tyan, logic, and mpuz retire: the largest single item for code that walks lists and trees.

Nearly all come from one rule: an option of two or more cases may be a proxy, because its tags number its cases in the
order of their names, and an upcast to a type with more cases renumbers them (an `Option nil end` seen as a list's
`Option cons nil end` has its `nil` move from tag 0 to tag 1), so the upcast makes a proxy that shows the original at
the new numbering. Every list and logic's `Term` is such an option. Proxies for a payload whose components change view
are the rarer case, and both designs keep them.

**5a, a whole program proves where proxies are made.** A proxy is made only by a conversion to a supertype (a `view`
plan of `ir/represent`, §5.8), whose target type the proxy then has; a value of a type no conversion makes a proxy at
is never one, since nothing converts down. A whole program sees every such conversion: `whole` runs represent's planning
over the unit before representing it (planning with today's rule, which can only find more), collects the shapes that
view plans and `dynamic.be`'s and the runtime's descriptor views (`quest_view_*`, reached from plans whose targets are
static types) make proxies at, and `mayBeProxied` answers false for every other. Costs: moderate, in `ir/represent`,
`repr/layout`, and `driver/whole`; no ABI change. Gains only in whole programs; unit by unit nothing changes, since a
unit cannot see the others' conversions. The soundness of the proof rests on finding every place that makes a proxy, so
the step adds a check mode in which the runtime's proxy constructors abort on a shape the compiler said none is made
at, run over the suite and the tests.

**5b, tags that no upcast renumbers.** Each case's tag is the same in every option type that has it: a 32-bit hash of
its name (with a type's two names that collide numbered apart, and that type keeping today's rule). An upcast then
renumbers nothing, and an option is a proxy only when a payload's components change view. Gains everywhere, unit by
unit too. Costs: an ABI change through the runtime (`ordinal`, the payload-free constants' tables, which are indexed by
ordinal and would be found by a search, `dynamic` and serialization, the barrier's test that a word under 65536 is a
tag), both compilers' C, the SSA builder, and the WebAssembly backend; and every switch on an option's tag becomes a
search over sparse constants rather than a jump table (the tables pass requires dense cases), which the compiler itself,
switching over options of 20 to 60 cases, would feel. So 5b would first count, in a hand-made build of the compiler and
of the suite, what sparse switches cost, before any of it is designed further.

Recommended: 5a first, whose gain is certain for whole programs and whose cost is local; 5b only if unit-by-unit
programs need the gain and its count of sparse switches is small. With 5a tabled (D5), 5b, after its count, is the only way to the gain.

**Tests either way:** a whole-program SSA golden of a list walk with no proxy test; the proxy tests
(`language/proxies` and the like) in whole-program mode, unchanged; the stress tier. **Measure:** tyan, logic, lexgen,
mpuz.

**Not taken:** the user chose neither design for now (2026-11-23); 5a, gaining only in whole programs, is tabled by
D5 (2026-11-24).

### 3.6. Step 6: a cheaper allocation

The fast path (`quest_gc_bump` and `quest_gc_note_start`, runtime/quest_gc.h; `ssa/passes/allocations`) is about 22
instructions through ssac and 30 through arm64, against MLton's 3 to 8: the cursor, the limit, and
`quest_gc_check_flags` each read as a global (arm64 builds each address with `adrp` and `add`, every time), the limit
and the flags tested with `cset`, `cset`, `orr`, `cbnz`, and the start bit set by a byte's read, or, and write (11 to
13 instructions). About 550 M of logic's instructions per iteration.

**6a, behavior unchanged:**

- the flags folded into the limit: while any check flag is set, the limit is the space's start, so every allocation
  fails the one comparison and takes the slow path, which counts it; `quest_gc_check_flags` is then read only there;
- the cursor and limit of a space next to each other, read by one `ldp` from one address;
- the start bit set with fewer instructions: the bitmap's base folded with the heap's low address into one global, so
  that the bit's byte is one `add` from the object's address shifted.

Both backends emit the sequence (arm64 from `ssa/passes/allocations`, ssac from the inline functions), so both change
together; the WebAssembly runtime's allocator has its own fast path, which gets the same flags-in-limit change.

**6b, the bitmap built at collection, only if 6a leaves the bit a large part of the path (D3):** every object begins
with its layout (or a size word and its layout), so the objects in the space allocated since the last collection can be
walked from each region's start, and their bits set then, before marking needs them. The allocation then sets no bit at
all. This would need [collector.md](collector.md) changed first (every allocation must leave a parsable region,
including the runtime's own), so 6a reports the bit's share of the fast path after its changes and, if it is large, a
sketch of 6b's cost: the walk at each collection over the objects allocated since the last.

**Tests:** the stress tier (`tools/check --stress`), which allocates through every path; the collector's own tests.
**Measure:** logic, tyan, nucleic.

**6a done, in part.** The flags are folded into the limit: a checking mode hides the limits after each allocation, as
an incremental cycle does, so the inline path tests the limit alone. The start bit's byte is `quest_gc_start_base` plus
the address shifted right by 6, one global. The cursor and limit were not paired for one `ldp`, and the WebAssembly
runtime's allocator is unchanged. Against the baseline, through ssac and arm64: logic 0.887 and 0.895, tyan 0.924 and
0.923, nucleic 0.763 and 0.802. 6b is not started.

### 3.7. Step 7: real elements loaded as reals, the data offset folded

On arm64, a `Real` array element is loaded into an integer register and moved with `fmov` (and stored the same way
back), because the builder reads a slot as a word and reinterprets it (`loadWord` and `slotFromWord`,
`ssa/build/control`); and the `+8` of the array's data is added before every access rather than folded into the
address. That is 48 of fft's butterfly.

Instruction selection (`codegen/arm64/select`) folds a reinterpretation of a load's result into the load (`ldr d`), and
of a store's operand into the store (`str d`), and folds a constant added to a base into the immediate offset of the
load or store (`ldr d, [x, #8]` or, with an index, after a shifted register add). The SSA does not change.

**Tests:** `questlang/arm64_select` cases for each fold. **Measure:** fft, matrix-multiply, nucleic.

**Done in the SSA, not in selection.** The builder's `realSlot` loads and stores a `Real` slot as a real, since the
slot holds its bits, so no reinterpretation is left to fold. The `+8` was not folded. Through arm64, against the
baseline: fft 0.677, matrix-multiply 0.868, zern 0.877; ssac unchanged.

## 4. Part 2: the rest of §38.3

These are larger, and each is measured on its own before the next. The order is by expected gain.

### 4.1. Missing optimizations before the code generator

- **Step 8, loop-invariant code motion** (`ssa/passes/licm`): pure instructions, invariant loads (an array's length, a
  string's data, a closure's captured variables reloaded on each pass of a self-recursive loop), and the checks that
  depend only on them (a null check), hoisted out of a loop to its preheader when the loop always runs its body at
  least once or the instruction cannot raise. matrix-multiply's length and null checks, mpuz's string fields, lexgen's
  closure reloads. Constants stay where they are used (value numbering keeps them local for register pressure), but a
  constant used in a loop is made once before it when a register is free, which is the allocator's choice (§4.2).
- **Step 9, strength reduction of induction variables:** `r * cols + i` in a loop where `i` steps by 1 becomes a pointer
  that steps by 8. matrix-multiply's 6 of 30.
- **Step 10, `real.int` inline:** `quest_real_from_int` is a call (`scvtf` in C); `externalOperation` expands it to the
  conversion. MLton calls a function for it too, so this gains on MLton: 13% of mandelbrot's samples.
- **Step 11, small comparison functions inlined into their callers:** tyan's `M.compare`, called from `P.plus` and
  returning a `Relation` the caller dispatches on (about 25 instructions a term), is not inlined, and the inliner's
  reason (size, recursion, or the growth bound) is found first; a function whose result is immediately cased on is a
  candidate for a bonus, as a constant argument is.
- **Step 12, a closure argument specialized to the known function:** lexgen's `Dict` takes `leq` as a closure, called
  through `blr` in its search loop. When every `Dict` in a whole program is made with the same `leq`, the inliner's
  specialization (ir.md §8.6) applies; the step finds why it does not here.

**Step 11 analyzed, not made** (2026-11-23). `mCompare` is self-recursive, and `simplify.eligible` inlines a recursive
function only when it has a static parameter passed a known function, which `mCompare` (two lists of Ints) has not:
neither its size nor the growth bound is the reason. Inlining it usefully would take two transformations the
simplifier lacks: copying a recursive callee into its caller as a local loop, and case-of-case (a switch on a join's
parameter pushed into the jumps that pass it a known constant), since a known-tag switch is decided only on a
variable whose definition is known. Two hand-made versions of tyan bound the gain, whole programs at its count of 12,
instructions retired against the unchanged program:

| Variant | ssac | arm64 |
|---|--:|--:|
| `mCompare` returns an Int, which `plus` and `minus` test with `if` | 0.982 | 0.994 |
| the comparison's loop written into `plus` and `minus` (no call, no `Relation`) | 0.956 | 1.015 |

So the `Relation` result costs under 2%, and the call at most 4.4% through ssac and nothing through arm64, whose
loop over `var`s costs more than the call it saves (step 14's kind of cost). Below what the two transformations
would cost to build; not made.

**Step 12 analyzed** (2026-11-23). `leq` is not a parameter but a field of the `Dict` tuple, loaded as `d.leq` in
the generic `lookup` and `enter`; the inliner's specialization covers only a self-recursive function's static
parameter passed a known function, so it cannot apply. A hand-made lexgen whose `lookup` and `enter` are copied at
`String` and at `Int` keys, calling `stringLeq` and `intLeq` directly, retires 0.907 of the instructions through ssac
and 0.936 through arm64 (whole programs at count 48, the same output). Getting that automatically needs a
whole-program fact about a field: every `Dict(String _)` made in the program (by `create`, once inlined, or as a copy
of another `Dict`'s `leq`) holds `stringLeq`, every `Dict(Int _)` `intLeq`, and the field is immutable, so a load of
`leq` from a `Dict` at a closed type is that function, which the simplifier then calls directly and inlines. That is a
design of its own (where the facts are collected, how a copy of the field is followed, and what makes a type's field
values known), for the user to decide on; it is not started.

**Step 12 designed, tabled by D5** (2026-11-24). The same pattern is in the library: `collections/hashMap` keeps
`equal` and `hash` in its `T`, and the sorted maps and the heap their comparisons, so the gain is not lexgen's alone.
The design, should it be taken up:

- **Where:** the self-hosted simplifier, in its rounds on the Core IR, where a known function is inlined and
  polymorphic code is cloned at closed types; whole programs only, since every construction must be seen.
- **Facts** (a new `ir/fieldvalues`): at the start of each round after the first, a walk of the unit records, for
  every tuple made with an immutable function-typed component, its label, its value, and the component's type. By
  then small constructors such as `create` are inlined, so the construction is at a closed type. A value is a known
  source when it is a global function (top-level or a module's member); a load of the same label adds nothing (the
  facts are a fixed point, so `enter`'s copy of `d.leq` is the fact itself); anything else (a parameter, a local
  closure, a construction at an open type) makes the label unknown. Facts are keyed by label and component type, not by
  the type's name: tuples are structural, so any tuple with a `leq` component of a subtype is a `Dict`, whatever it
  was written as. A load whose component type is `All(a: String b: String) Bool` can see the values of the
  constructions with label `leq` whose stored type is a subtype of it: `stringLeq`, not `intLeq`. Keying by the
  component's type makes the facts per instantiation.
- **Loads resolved:** a load of such a field at a closed type whose fact is one global function becomes a reference to
  it, so the call through it is known and the inliner's rules apply. A top-level function's closure is static, so
  nothing, `is` included, can tell.
- **Specialization on a known field:** in the generic `lookup` the load's type is `All(a: K b: K) Bool`, open. As the
  inliner clones a recursive function for a known function passed to a static parameter (ir.md §8.6), it would clone a
  callee for a call at closed type arguments whose callee loads and calls a field of a parameter with a one-function
  fact at those types; in the clone the load resolves and the call inlines. Clones are shared by function and type
  arguments, as `specialize`'s are, and bounded as the known-function bonus is.
- **Soundness:** function-typed fields only, since only the program's code makes closures (not deserialization or
  `dynamic`); `var` fields left out, or each assignment counted as a source; a label that an external's type mentions
  unknown; facts taken after dead-code removal, so that the generic `create` is gone; source order throughout, for the
  fixed point.
- **Limits:** one function per type: `hashMap`s at one key type with two `equal`s resolve nothing, and telling them
  apart by where each was made would need cloning per construction site. Unit by unit it gains nothing; a main
  program's unit could be argued separately (its structural tuples can come only from imports whose interfaces mention
  the label, and from `dynamic`).
- **Work and tests:** `ir/fieldvalues`, a hook in `simplify`, the extension of `inline.specialize`; self-hosted only,
  behavior goldens unchanged. `language/` goldens at `ir_simplified`: a load resolved; two functions flowing in, the
  load left; a wider tuple of another name flowing in; a generic construction left, the label unknown; a `var` field.
  ir.md §8.6 and inlining.md.
- **Gate:** the fact collector first, with a report flag (as `--report-inferable`), counting over the suite's whole
  programs and the compiler's own whole build the loads it would resolve, and those in loops.

### 4.2. The arm64 code generator

From §38.3 item 7 and the subagents' listings; each a change to `codegen/arm64` alone, tested by `questlang/arm64_*`
cases:

- **Step 13, loads into their final register:** a load into a scratch register followed by a move (four per element of
  tyan's compare); the register allocator's hint for the load's result is the move's destination.
- **Step 14, loops rotated:** the test at the bottom, one branch per iteration, and no back-edge moves for parameters
  that are permuted (mandelbrot's three `fmov`s, mpuz's two `mov`s).
- **Step 15, no dead closure argument on a back edge:** a self-recursive call that passes the closure it does not read
  (`mov x12, #0; mov x20, x0; mov x0, x12`).
- **Step 16, the common path of a check laid out in line:** a proxy test's non-proxy path, and a check's success path,
  fall through.
- **Step 17, values live only across a cold call saved only on its path:** `tfoCombine`'s reals stored and reloaded
  around `quest_gc_alloc_slow` on the fast path; spill code moved to the cold block.
- **Step 18, `cset`/`orr` sequences as branches:** a conjunction of comparisons that feeds only a branch becomes `ccmp`
  and one branch (logic's 1,563 `cset`/`csel` against ssac's 19).

**Done in part** (`883a870d`, for steps 13 and 16): a block that calls the runtime for a proxy is cold, as one that
raises is, so it is laid out of line; and a jump's register hint from a cold block comes after the others, so a proxy
test's join takes the hot path's register and the move is on the cold path. Through arm64, against the baseline: tyan
0.863, logic 0.850, lexgen 0.770, mpuz 0.925, nucleic 0.784. **Tried for step 15 and not kept:** leaving the entry's
unread parameters (a loop's static closure) out of block 0, under 1%.

### 4.3. Data representation

Today ([c-representation.md](c-representation.md) §5.1, §5.3; [collector.md](collector.md) §3.2):

- every object has a header word before it: its layout's address in the low 48 bits, and two bytes of flags above;
- an option is a tag word and then a union of its cases' payloads, as large as the largest; its layout describes the
  union as a whole, and a case's payload is a tuple at the option's address plus 8, which a case binder points to;
- a case without components is the address of a constant in its unit's table, one object per tag;
- an option's tag is read with a load, `is` on options compares by case, and the write barrier tells an option's
  payload from an object by the word before it (a tag is under 65536, `Q_BARRIER_TAG_LIMIT`).

logic allocates 1.55 times MLton's bytes for the same objects, and a list cell is 32 bytes to MLton's 24 with its nil
tested by a load.

Every step here changes the ABI (an ABI bump, both compilers' C, the runtime, the arm64 and ssac backends, the JIT),
except where it says otherwise. The WebAssembly backend keeps its own layout (wasm.md §2.3: slots in an array inside
one struct type) and changes only where the runtime it shares does. The bootstrap emits the same layouts as the
self-hosted compiler, so it follows every layout step, behavior goldens unchanged.

**Step 19, a census before any design.** `QUEST_GC_CHECK=allocations` (`benchmarks/mlton/allocations.py`) counts
allocations by function; it gains `--by-layout`: the count and bytes of each layout, and for options of each case.
Run over the whole suite and the compiler's own build, it gives each of steps 20 to 24 its gain in bytes before it is
designed further. Each step below states the gain it needs: a step whose census gain is under 3% of the bytes
allocated on every program, with no program's instructions moved by 1% in a hand-built experiment, is not made.

**Step 19 done** (2026-11-23): `allocations.py --by-layout`, from the `allocations` mode's census by layout and size
(runtime/quest_gc.c, written to `$QUEST_LAYOUTS_OUT`; no ABI change). An option made at a known case already has
that case's own layout (`repr/objectlayout`), so the census tells cases apart by layout with no tag read. Over the
suite (arm64 whole programs, a thirty-second of the counts), options are 50 to 100% of the bytes of 15 programs
(tyan 96%, tailmerge and DLXSimulator 100%, logic 58%), and almost none of 23. What the census gives each step:

- **Step 21 (the tag in the header)** saves the tag's 8 bytes of every option object: 25 to 26% of the bytes of
  zebra, tyan, tailmerge, and DLXSimulator; 19 to 22% of peek, boyer, mlyacc, life, vliw, and model-elimination; 15%
  of hamlet and logic; 10 to 15% of count-graphs, tsp, simple, lexgen, and knuth-bendix; 8% of nucleic. Far above
  the 3% gate, so steps 20 and 21 are worth designing further.
- **Step 20 (each case sized to itself)** gains what a case's payload is smaller than the union, which the census
  cannot see, since an option is allocated at the union's size. Lists, most options' bytes, have one case with a
  payload, so for them step 20 gains nothing; it is measured on the types with several (logic's `Term`, hamlet's
  syntax) when it is designed.
- **Step 22 (payload-free cases by address)** saves no bytes, only the tag's load, and **step 23** applies to mpuz,
  which allocates almost nothing at this count: their gains are in instructions, not bytes, and each needs its own
  hand-built experiment.

**Step 20, each case of an option sized to itself.** An option's object is its tag and then its own case's payload,
not the largest case's. That needs a layout for each case (a tag, then the case's words, with their kinds), so that
the collector and the barrier find an object's size and pointers from its header as they do now:

- `repr/layout` gives an option shape a layout per case, with the union's layout kept for generic code
  (`QOptionHeader`), which reads only the tag and the case's own words;
- the allocation of `option c of T with ... end` uses case `c`'s size and layout; a payload-free case stays a constant;
- nothing reads past a case's own words today, which the step checks first: copying (`opt!tag` copies only the case),
  generic conversion between layouts (§5.1's polymorphic calls), serialization, `dynamic`, and the runtime's
  `quest_view_*` and proxy functions, each listed and fixed before the change;
- the collector's layout table gains the cases; the barrier is unchanged.

Gain to check: logic's `Term`, a `ref` of 32 bytes to 16; the census over the suite.

**Step 20 analyzed, not made on its own** (2026-11-23). The census gives each option's bytes by case, and a case's
own size is its declaration's (in the compiler, a scratch build that named each case's layout with its word count).
A case's saving is the union's size less its own: header, tag, and the case's words.

- **The suite:** only seven programs put more than 3% of their bytes in options with several payload cases. logic's
  `con` and `ref` (24 bytes in a 32-byte union) and raytrace's one- and two-word cases of `V` (in a 56-byte union)
  save about 5% of each program's bytes; knuth-bendix and model-elimination at most 1.5%; boyer, hamlet, and mlyacc
  almost nothing, since their bytes are in the largest case. Lists, most options' bytes, have one case with a payload
  and gain nothing.
- **The compiler** (the self-hosted one compiling `questlang/driver/main.quest`, 50 GB in 1.05 billion objects):
  options are 14.6% of the bytes (`maybe.some` 4.3%), and step 20 saves 0.6%, no type more than 0.12%. Step 21 saves
  3.1% from options made at a known case, and up to about 1% more from those made generically. Most of its bytes are
  vectors (the tuple 8.3%, the arrays behind them about 16%), byte buffers, and strings.

A 5% saving in bytes is unlikely to show in time: step 24's nucleic experiment saved 10% and moved instructions by
under 1.3%. So step 20 is not made as a step of its own, for a full ABI change. It is folded into step 21: with the
tag in a case's own layout, sizing each case to itself is a small addition there, if wanted.

**Step 21, the tag in the header, not a word of its own.** Each case already has a layout of its own
(`repr/objectlayout`; step 20 is folded in here). With a layout per case, the tag is a property of the layout: the
case's layouts for one option type are made consecutive (one table per option shape), so the tag is `(header & mask) -
table` divided by the layout's size, a load, an `and`, a subtraction and a shift, where today it is a load. The object
loses its tag word (a cons cell 24 bytes, as MLton's), and the payload is at the object's address:

- a case binder points to the object itself, which changes every case's offsets in the SSA builder, both C emitters,
  and the runtime;
- the barrier's test on the word before a payload goes: the payload is the object, and its header is the word before
  it;
- the constants of payload-free cases keep a header too (they are objects in static data with the case's layout), so
  that reading a tag is the same for every option;
- the arm64 backend reads a tag in one more instruction than now, so the step first counts, in a hand-edited build of
  tyan and logic, whether the bytes saved (fewer collections, better density) pay for it; it is not made if not.

**Step 21 abandoned** (2026-11-24, the user's decision; step 20 goes with it). Not worth the cost: it saves 15 to
26% of the bytes of the programs that allocate options most, but the census measures bytes, not time, and fewer bytes
have not been fewer instructions (step 24's nucleic saved 10% of its bytes and under 1.3% of its instructions). Against
that, every case test that reads a tag takes four instructions where it takes one; it is the widest change in the plan
(every case's offsets, both compilers' C, the runtime, the barrier, the arm64, ssac, and JIT backends, proxies,
`dynamic`, an ABI bump and a release), and it needs one table of consecutive layouts per option type, which options
made in other units, generically, or by the runtime make hard to keep. Whether it paid could have been bounded
without building it, by timing two throwaway builds: options padded by a word (the bytes' cost, the inverse of the
gain) and every tag read made the four-instruction sequence (the reads' cost). That was not run: the cost is certain and
large, the gain uncertain.

**Step 22, payload-free cases tested by address (whole programs).** Today a payload-free case is a constant in each
unit's table, so `is` cannot compare addresses across units and a test for `nil` loads the tag. In a whole program
there is one unit, so one table: a case test for a payload-free case is the pointer compared with the constant's
address, with no load, where every option of that type that the program makes is made by compiled code (not by
`dynamic`, deserialization, or the runtime, which `whole` can see). It changes no layout and no ABI. Gain: about 4
instructions per element of tyan's and lexgen's list walks. **Tabled by D5** (2026-11-24): whole programs only.

**Step 23, a tuple field made with its owner, allocated inside it.** mpuz's `(v, ref false)` is two objects, the value
and the tuple holding its `used` flag, and reading the flag loads the inner tuple's address first; MLton makes one
object. The inner tuple's identity is observable, but only in ways that sharing an allocation keeps: `is` and
`identityHash` compare and hash its address, which stays its own; and a `var` component is shared by whoever holds the
tuple (`let r = outer.r` then `r.used := true` shows through `outer.r.used`), which holds while it stays one object.
What they rule out is copying the inner tuple's components into the outer one, not allocating them together.

So the inner tuple is allocated after its owner, in the owner's allocation, as the represent pass does already for
records' and variants' boxes (`embedded`, [c-representation.md](c-representation.md) §5.1), reached by an interior
pointer that the start bitmap resolves. When the field is immutable and every owner is made with a fresh inner tuple
(a local condition: an immutable tuple-typed field whose value, at every construction of the owner, is a tuple made in
the same expression), `outer.r` is always `outer + k`, so `outer.r.used` is a load at a constant offset from `outer`,
with no load of the inner tuple's address. The step first finds how often the pattern occurs in the suite (a census of
such fields); it is designed further only if more than mpuz has it.

**Step 23 analyzed** (2026-11-23). The pattern is a ref (a tuple of one `var` field) made fresh with its owner and
reached through it. A census of 16-byte objects (one-word tuples) over the suite and the compiler finds it allocated
in bulk only in logic (`Ref`, inside `Term`'s `ref` case: 10.7 million, 3.5% of its bytes) and in ratio-regions
(`QueueRef`, 7.8% of a small total); mpuz makes its ten once per solve but reads them on every step of its search.
The compiler's 16-byte objects are almost all empty arrays. Hand-made variants with the ref folded into its owner,
written as step 23 would make them (mpuz's `used` a field of `Value`; logic's `ref` case holding `var v` itself, a
`Ref` being the case's payload, so that `x.r.v` is `x.v`), whole programs, with their output and logic's `testit`
unchanged:

| Program | Instructions, arm64 | ssac | Bytes |
|---|--:|--:|--:|
| mpuz (count 32) | 0.940 | 0.896 | |
| logic (count 64) | 0.955 | 0.954 | 0.965 |

So it is worth 4 to 10% on two programs and nothing measurable elsewhere. Both are refs translated from SML, and the
source form above (a `var` field in the owner, or in an option's case) already gets the gain without the compiler's
help; the step is the compiler finding it for code written the nested way. Not made yet: the user to decide.

**Step 24, tuple results returned in registers.** `tfoCombine` allocates its 12-real result (43 of its 287
instructions); workers ([inlining.md](inlining.md) step 5) already return tuples unboxed, as several results. The
step finds why `tfoCombine`'s callers do not get a worker (its size, its being exported, or a caller that stores the
result), and widens the rule; a result that is stored is still allocated, but at the store, not in the callee. This
changes no layout and no ABI.

**Step 24 analyzed, not made** (2026-11-23). `tfoCombine` is far over the inlining threshold (30), and its result
falls outside unboxed results' rule twice: that rule takes one or two components, each an Int, Bool, Char, or
String, and a `Tfo` is twelve Reals. Workers, which would widen it, are not built (inlining.md §2). Of its calls, the
one in `dgfBase` (`tfoCombine(nuc.dgfBaseTfo tfoCombine(tfo tfoInvOrtho(x)))`) makes two `Tfo`s that are only
read. A hand-made nucleic with the three calls fused, so that only the stored `Tfo` is allocated, allocates 0.903 of
the bytes, but retires 0.987 of the instructions through ssac and 1.004 through arm64 (whole programs at count 128;
its own check of the result passes), where 24 live Reals spill. Under the 1% this part asks on arm64; not made.

### 4.4. Loops in recursive form

The conversions keep the originals' recursive loops (2026-11-23), so the compiler, not the conversion, must make them
good loops. [benchmarks.md](benchmarks.md) §42.3 measured hand-written loop versions of six programs: contification
already makes most of them what the loops are, within 3%, and two costs are left:

- **Step 25, a module cell kept in a register across a loop:** mandelbrot adds to `sumIterations.n` on each pass of
  its middle loop; with the sum a parameter instead it retires 0.908 of the instructions through ssac and 0.900
  through arm64. In a loop whose body makes no call that can reach the cell and reads it through no other name, the
  cell's field is loaded before the loop, carried as a loop parameter, and stored at each exit (and before a raise).
- **Step 26, indices that step together merged:** tensor's folds pass two or three indices that each step by one;
  with one index and the others offsets from it, 0.968 and 0.973. Close to step 9's strength reduction, and done with
  it.

Also found, not about the recursive form: Quest's own `while` on a `var` flag costs 1.25 times the recursion through
arm64 in mandelbrot (likely step 14's), and imp-for's nest, which clang computes without looping, retires 324 times
ssac's instructions through arm64 in every form.

## 5. Part 3: five steps, in order (2026-11-24)

The user chose (2026-11-24) the next five, all of which gain unit by unit, in this order. Each is evaluated by counts
on the loaded machine, without the lock (`--no-exclusive`): instructions and bytes of whole programs at a
thirty-second of the suite's counts, unit by unit through arm64 and ssac, against the commit before it, with
`run.py check` of every program through both and the suites the step touches. `tools/check` runs once, at the end;
then one timing of the suite (§2), with the lock, on a quiet machine. Commits stay local until the user says to push.

- **D6, loop rotation in the SSA** (the user, 2026-11-24): hoisting was tried on 2026-11-03 and found almost
  nothing, since a loop's invariant loads sit behind its null and bounds checks (`dominatesExits` failed). So step 8
  rotates loops in the SSA first, so that ssac and arm64 both gain, and step 14 keeps only arm64's back-edge moves.

1. **Step 10, `real.int` as an SSA conversion.** A new pure opcode (`opIntToReal`): built for the external
   `quest_real_from_int` in `ssa/build/calls`' `externalOperation`; printed, parsed, and verified; folded on a
   constant; `(double)` in ssac's C, `scvtf` on arm64. mandelbrot's `real.int(j)` is the aim.
2. **Steps 25 and 8, loops: memory promoted, rotated, invariants hoisted** (`ssa/passes/loops`, a new pass on
   `ssa/cfg`'s dominators, natural loops from back edges):
   - *Promotion (25):* a word at an address the loop does not change (a module cell's field: a global's invariant
     load plus an offset), which the loop loads and stores, where nothing else in the loop can write it: no call but
     runtime functions that write no memory (their effects), and no store but to that address, to the loop's own
     allocations, and to stack slots. It is loaded before the loop into a stack slot, the loop's loads and stores use
     the slot, and every exit (a raise's cold path included) stores it back; slot promotion then makes it a register.
     First non-pointer words only (Int, Real, Bool), so that no store moves past a barrier's reasoning; pointers only
     if a census finds them hot.
   - *Rotation (D6):* a loop whose header tests and exits becomes its test before the loop and a copy at the bottom,
     so the body runs at least once once entered, and its first pass's checks dominate the rest.
   - *Hoisting (8):* pure instructions, invariant loads, and the checks that depend only on them (null, bounds on an
     unchanging length) moved to the preheader of a rotated loop; constants left where they are used.
   - Gate: mandelbrot (25), matrix-multiply, mpuz, lexgen (8); each part kept only if it saves 1% somewhere it aims
     at, and the hoisting is watched for the spills value numbering once caused (ssa.md §4.1) and for broken `ldp`
     pairs.
3. **Steps 9 and 26, induction variables and bounds checks:** in a rotated loop, `base + i * 8` for an induction
   variable `i` becomes a pointer stepping by 8, and indices that step together become one with offsets.
   matrix-multiply's 6 of 30, tensor's 3% (benchmarks.md §42.3). With each induction variable's range known (its
   start, step, and the test that bounds it), a bounds check it implies goes (the user, 2026-11-24): `0 <= i <
   length` for a loop over an array's indices whose length does not change in it, and checks of `i + c` that the
   range covers. Today only a check that an identical dominating one decides is removed (`ssa/passes/conditions`);
   a check implied by a different comparison is not.
4. **Step 14, arm64's back-edge moves:** with loops rotated in the SSA, what is left is the moves of permuted
   parameters on a back edge (mandelbrot's `fmov`s, mpuz's `mov`s). Probed first by counting the moves on the hot back
   edges of mandelbrot, mpuz, and the `while`-on-a-flag loop of §42.3; built only if they are 1% of a program.
5. **Step 18, conjunctions as `ccmp`:** counted first, how many of logic's 1,563 `cset`/`csel` are in its hot code
   (`tools/perf` samples); built only if they are 1% of its instructions.

**To investigate when Part 3 is done** (the user, 2026-11-24):

- **Non-null facts:** a value freshly allocated, or already dereferenced, is not known to be non-null, so a later null
  check of it stays unless an identical one dominates it. How many such checks the suite's hot code runs, and what
  knowing them would save.

## 6. Order and stopping

Part 1's steps in order 1 to 7, then the part's counts and timings (§2) into benchmarks.md. Then Part 2: §4.1 and §4.2
in order; then §4.3, starting with the census (step 19) and the two steps that change no ABI (24, then 22), then 23
(20 and 21 abandoned), each gated by its census gain. A step that saves less than 1% of instructions on every program
it was aimed at is reverted and recorded as tried in benchmarks.md, as §37.1 records the budgets. The plan is deleted
when done, its findings kept in benchmarks.md and the design docs the steps change.
