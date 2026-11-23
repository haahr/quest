# Plan: Closing the Median Programs' Gap to MLton

A plan for what [benchmarks.md](benchmarks.md) §38 found: why the programs in the middle of the MLton suite retire 1.4
to 3.7 times MLton's instructions through arm64 (0.9 to 2.0 through ssac). Part 1 (§3) makes the cheapest changes, the
ones §38.4 estimates. Part 2 (§4) takes the rest of §38.3. Each step is measured by counts, which a loaded machine
barely changes (§2), and timed only at the end of each part.

Self-hosted compiler only, except where a step changes a library module or the runtime, which both compilers and every
backend share. The two-compilers policy holds: behavior goldens stay shared and are written by the bootstrap; IR, SSA,
and C goldens are each compiler's own. A step that changes the runtime or a library module changes the WebAssembly
backend too, in the same step ([wasm.md](wasm.md)); the SSA's passes do not reach it, since it starts from the IR.

## 1. Decisions for the user

Each is marked where it arises; none blocks the steps before it.

- **D1, `conv.int` in Quest or in C** (step 1). Recommended: Quest. A first version already retires 0.62 of the
  native one's instructions per call (§3.1); it is kept if it is within about 1.5 times a C digit loop's.
- **D2, NaN checks deferred** (step 4). Recommended: deferred with the exact site recovered on the cold path (§3.4), so
  that no program's behavior changes. The alternative, raising at the observation point, would change the language's
  rule.
- **D3, the object-start bitmap** (step 6). Whether a start bit is still set by every allocation (cheaper, step 6a) or
  the bitmap is built for each region at collection from the objects' headers (step 6b, a collector design change).
- **D4, data representation** (§4.3). Each item there changes how values are laid out across every backend and the
  runtime; each needs its own plan, and the user's go-ahead, before it starts.
- **Pushing.** Recommended: commit each step, run `tools/check` at the end of each part, and push when the user says.

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
loop as a yardstick (**D1**), keeping the Quest version if it is within about 1.5 times the C loop's count.

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

### 3.4. Step 4: NaN checks where a value is observed (D2)

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

### 3.5. Step 5: no proxy tests for types no proxy is made of

A tuple or option type whose components can change view may hold a proxy (`mayBeProxied`, `repr/layout`;
[runtime-design.md](runtime-design.md) §2.3), so every read of its tag, payload, or field is preceded by `tbnz wN, #0`
and a cold call: 8 of the 25 instructions per element of tyan's walk through ssac, 5 to 8 per step of logic's.

A whole program knows every site that makes a proxy (an upcast whose components change view, `ir/represent`).
`whole` collects the types those sites make proxies of, and `mayBeProxied` answers false for any other in that unit.
Unit by unit it cannot know, and nothing changes.

**Tests:** a whole-program SSA golden of a list walk with no proxy test; `language/proxies` (or its equivalent) in
whole-program mode, unchanged. **Measure:** tyan, logic, lexgen, mpuz, as whole programs.

### 3.6. Step 6: a cheaper allocation (D3)

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

**6b, the bitmap built at collection (D3, a design change):** every object begins with its layout (or a size word and
its layout), so the objects in the space allocated since the last collection can be walked from each region's start,
and their bits set then, before marking needs them. The allocation then sets no bit at all. This would need
[collector.md](collector.md) changed first (every allocation must leave a parsable region, including the runtime's
own), and is a step of its own if the user wants it.

**Tests:** the stress tier (`tools/check --stress`), which allocates through every path; the collector's own tests.
**Measure:** logic, tyan, nucleic.

### 3.7. Step 7: real elements loaded as reals, the data offset folded

On arm64, a `Real` array element is loaded into an integer register and moved with `fmov` (and stored the same way
back), because the builder reads a slot as a word and reinterprets it (`loadWord` and `slotFromWord`,
`ssa/build/control`); and the `+8` of the array's data is added before every access rather than folded into the
address. That is 48 of fft's butterfly.

Instruction selection (`codegen/arm64/select`) folds a reinterpretation of a load's result into the load (`ldr d`), and
of a store's operand into the store (`str d`), and folds a constant added to a base into the immediate offset of the
load or store (`ldr d, [x, #8]` or, with an index, after a shifted register add). The SSA does not change.

**Tests:** `questlang/arm64_select` cases for each fold. **Measure:** fft, matrix-multiply, nucleic.

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

### 4.3. Data representation (D4: each its own plan)

Investigations, not steps: each says what it would gain, from counts of the programs built by hand where possible, and
what it would cost across the runtime, every backend, and the interpreters.

- **An option's tag in its header word:** today a word of its own (`str` and cons cells 32 bytes against MLton's 24);
  logic allocates 1.55 times MLton's bytes for the same objects.
- **Each case of an option sized to itself:** today every case is as large as the largest (a `Term`'s `ref` 32 bytes
  against 16).
- **Payload-free cases as immediates, and two-word cons cells:** `nil` is an object in the heap and a cons three words
  where MLton's nil is an immediate and its cell two; 4 instructions per element of tyan's walks.
- **A tuple of a value and a `var` flattened:** mpuz's `(v, ref false)`, two objects where MLton makes one.
- **Tuples returned in registers:** `tfoCombine` allocates its result, 43 of its instructions, where MLton returns
  the tuple flattened. Workers (inlining.md step 5) carry tuple results unboxed already; the step finds why
  `tfoCombine`'s are not.

## 5. Order and stopping

Part 1's steps in order 1 to 7, then the part's counts and timings (§2) into benchmarks.md, then Part 2's sections in
order. A step that saves less than 1% of instructions on every program it was aimed at is reverted and recorded as
tried in benchmarks.md, as §37.1 records the budgets. The plan is deleted when done, its findings kept in benchmarks.md
and the design docs the steps change.
