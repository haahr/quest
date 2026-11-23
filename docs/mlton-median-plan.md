# Plan: Closing the Median Programs' Gap to MLton

A plan for what [benchmarks.md](benchmarks.md) §38 found: why the programs in the middle of the MLton suite retire 1.4
to 3.7 times MLton's instructions through arm64 (0.9 to 2.0 through ssac). Part 1 (§3) makes the cheapest changes, the
ones §38.4 estimates. Part 2 (§4) takes the rest of §38.3. Each step is measured by counts, which a loaded machine
barely changes (§2), and timed only at the end of each part.

Self-hosted compiler only, except where a step changes a library module or the runtime, which both compilers and every
backend share. The two-compilers policy holds: behavior goldens stay shared and are written by the bootstrap; IR, SSA,
and C goldens are each compiler's own. A step that changes the runtime or a library module changes the WebAssembly
backend too, in the same step ([wasm.md](wasm.md)); the SSA's passes do not reach it, since it starts from the IR.

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

Open: **pushing.** Each step is committed; `tools/check` runs at the end of each part (and after each step of §4.3,
which change the ABI); pushing waits for the user.

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

### 3.5. Step 5: no proxy tests for types no proxy is made of

A tuple or option type whose components can change view may hold a proxy (`mayBeProxied`, `repr/layout`;
[runtime-design.md](runtime-design.md) §2.3), so every read of its tag, payload, or field is preceded by `tbnz wN, #0`
and a cold call: 8 of the 25 instructions per element of tyan's walk through ssac, 5 to 8 per step of logic's.

A whole program knows every site that makes a proxy (an upcast whose components change view, `ir/represent`).
`whole` collects the types those sites make proxies of, and `mayBeProxied` answers false for any other in that unit.
Unit by unit it cannot know, and nothing changes.

**Tests:** a whole-program SSA golden of a list walk with no proxy test; `language/proxies` (or its equivalent) in
whole-program mode, unchanged. **Measure:** tyan, logic, lexgen, mpuz, as whole programs.

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

**Step 21, the tag in the header, not a word of its own (only after step 20).** With a layout per case, the tag is a
property of the layout: the case's layouts for one option type are made consecutive (one table per option shape),
so the tag is `(header & mask) - table` divided by the layout's size, a load, an `and`, a subtraction and a shift,
where today it is a load. The object loses its tag word (a cons cell 24 bytes, as MLton's), and the payload is at the
object's address:

- a case binder points to the object itself, which changes every case's offsets in the SSA builder, both C emitters,
  and the runtime;
- the barrier's test on the word before a payload goes: the payload is the object, and its header is the word before
  it;
- the constants of payload-free cases keep a header too (they are objects in static data with the case's layout), so
  that reading a tag is the same for every option;
- the arm64 backend reads a tag in one more instruction than now, so the step first counts, in a hand-edited build of
  tyan and logic, whether the bytes saved (fewer collections, better density) pay for it; it is not made if not.

**Step 22, payload-free cases tested by address (whole programs).** Today a payload-free case is a constant in each
unit's table, so `is` cannot compare addresses across units and a test for `nil` loads the tag. In a whole program
there is one unit, so one table: a case test for a payload-free case is the pointer compared with the constant's
address, with no load, where every option of that type that the program makes is made by compiled code (not by
`dynamic`, deserialization, or the runtime, which `whole` can see). It changes no layout and no ABI. Gain: about 4
instructions per element of tyan's and lexgen's list walks.

**Step 23, a component that is a `var` tuple made with its owner, flattened into it.** mpuz's `(v, ref false)` is two
objects, the value and the tuple holding its `used` flag; MLton makes one. In Quest, the inner tuple's identity is
observable (`is`, aliasing of its `var`), so it is flattened only where escape analysis shows the inner tuple is made
with the outer one, stored nowhere else, and never compared by `is`, a whole-program fact. The step first finds how
often the pattern occurs in the suite (a census of tuples stored only as one field of one other tuple made beside
them); it is designed further only if more than mpuz has it.

**Step 24, tuple results returned in registers.** `tfoCombine` allocates its 12-real result (43 of its 287
instructions); workers ([inlining.md](inlining.md) step 5) already return tuples unboxed, as several results. The
step finds why `tfoCombine`'s callers do not get a worker (its size, its being exported, or a caller that stores the
result), and widens the rule; a result that is stored is still allocated, but at the store, not in the callee. This
changes no layout and no ABI.

## 5. Order and stopping

Part 1's steps in order 1 to 7, then the part's counts and timings (§2) into benchmarks.md. Then Part 2: §4.1 and §4.2
in order; then §4.3, starting with the census (step 19) and the two steps that change no ABI (24, then 22), then 20, 21
(only after 20), and 23, each gated by its census gain. A step that saves less than 1% of instructions on every program
it was aimed at is reverted and recorded as tried in benchmarks.md, as §37.1 records the budgets. The plan is deleted
when done, its findings kept in benchmarks.md and the design docs the steps change.
