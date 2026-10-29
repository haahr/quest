# Plan: The Native arm64 Backend

Step 6 of the [roadmap](roadmap.md): a backend in the self-hosted compiler that writes arm64 machine code for Darwin,
as an alternative to the C backend. Its object files link with the C backend's, unit by unit, and with the runtime,
which stays in C. It is written in Quest, in `questlang/`, and the bootstrap does not get it
([testing.md](testing.md) §2.8: the bootstrap gets the language's changes, not the self-hosted compiler's backends).

The code says **arm64** in directory, module, and option names; this document says arm64 too.

---

## 1. Decisions

- **An alternative to C, not a replacement.** The C backend stays, and both write objects with one ABI, so a program
  may mix units of each. Mixing is a requirement, not a convenience: it is how the backend is brought up (§3.12) and
  how a miscompile is found (§4).
- **Speed is not the first goal.** Code is not expected to be as fast as clang's at first. Optimizations come later
  (§6); the representation is chosen so that they can be added.
- **Tail calls whenever possible** (§3.7), not as a guarantee of the language.
- **Darwin only.** Mach-O, Apple's variant of AAPCS64, the Darwin assembler and linker. Linux would need another
  object format and relocation spelling (§3.11), kept in one module so that it could be added.
- **SSA with block arguments,** not φ nodes. The IR's join points already are blocks with arguments
  ([ir.md](ir.md) §6.3), so building the CFG is close to mechanical, and leaving SSA is one step: a block's arguments
  become parallel copies on the edges into it.
- **An SSA-to-C printer as an oracle** (§3.14): the low-level SSA printed as C runs the whole suite through the SSA,
  the layout, and the lowering before any arm64 code exists, and stays as a third backend to compare against.
- **Choosing a unit's backend is explicit.** A unit the arm64 backend cannot compile is an error, never silently
  compiled with C; mixed builds name their units' backends (§3.12).
- **The exception state stays thread-local** (§3.6), as it is for C.
- **Shared passes are the self-hosted compiler's.** Decisions moved out of the C printer into passes both of its
  backends use (§3.1) are not made in the bootstrap, whose C printer keeps making them itself.

## 2. Pipeline

```
described IR (ir.md §8.4)
  ├─→ C printer → C → clang                                              (unchanged)
  └─→ build SSA          questlang/ssa        CFG, block arguments, mutable locals promoted, try regions;
        │                                     machine scalar types; loads and stores at byte offsets
        ├─→ SSA-to-C printer  questlang/codegen/ssac  (the oracle, §3.14) → C → clang
        ▼
      lower to arm64     questlang/codegen/arm64   ABI (Apple AAPCS64), instruction selection: machine SSA over
        │                                          virtual registers, with fixed-register constraints
        ▼
      allocate registers questlang/codegen/regalloc  target-parameterized; out of SSA (parallel copies)
        │
        ▼
      frame              prologue, epilogue, spill slots, callee-saved registers, tail calls, unwind directives
        │
        ▼
      emit               assembly text (.s) and static data → clang -c → .o → linked with C units, runtime, libgc
```

The SSA is **target-independent but low-level**: its values are machine scalars, not Quest values, so that
lowering to arm64 is local and later optimizations are ordinary SSA optimizations. A Quest-level SSA would repeat
the IR and leave the hard lowering to the arm64 stage.

## 3. Design

### 3.1. Where the backends fork

The C backend leaves much of the lowering to C and clang: struct layout, padding, and alignment; static
initializers; the 64 `static inline` helpers and the macros of `runtime/quest_runtime.h` (integer division, `Real`
results, word operations, proxies, closure calls, ...); and `setjmp`. The arm64 backend must decide each of these
itself, and must decide them as C does, since its units link with C's.

- **An inventory first** (step 1): every decision the C printer (`questlang/codegen/c/printer` and `declarations`)
  and the runtime header make that is not just C syntax, and for each, where the arm64 backend gets it: a shared
  IR pass both backends consume, a shared module (as `questlang/codegen/layout` and `descriptors` are now), or the
  SSA's construction.
- **Lean toward sharing.** Descriptor materialization (the descriptor operands of §8.4 become explicit loads and
  calls), conversion plans, and record offset tables are candidates for shared passes or modules, so that one
  implementation decides what a value's bits are.
- **Runtime helpers.** Native code cannot call a `static inline` function. Each helper the backend needs gets an
  out-of-line definition in `quest_runtime.c`, which the backend calls at first; hot ones are later expanded inline by
  instruction selection, with tests that compare the two.

### 3.2. The SSA

`questlang/ssa`: nodes, printer, verifier, and construction from the IR.

- **Types:** `i64`, `f64`, `ptr` (a pointer the collector must see; see §3.13), and `i1` for conditions. Narrower
  integers appear only as the widths of loads and stores (strings' bytes, `Bool` and `Char` fields, if their layouts
  have them).
- **Values** are instruction results and block parameters. An instruction may have several results: a call that
  returns a 16-byte value (a record's evidence pair, a `QVariantVal`) returns two. Every 16-byte value is split into
  two scalars when the SSA is built, so no later stage sees aggregates.
- **Instructions:** integer and floating arithmetic and comparisons, conversions, `load`/`store` (width, base,
  offset), `addr` of a stack slot or a global, constants and symbol addresses, `call` (direct, by symbol, or indirect,
  by address) with an ABI-neutral argument list, and the runtime's operations as calls by name.
- **Terminators:** `jump b(args)`, `branch c, b1(args), b2(args)`, `switch v, table, default`, `return values`,
  `tail_call`, `raise` (a call that does not return), `unreachable`.
- **Stack slots:** a function's mutable locals whose address is taken (`addr x`, for `var`/`out` arguments and `@x`)
  and the locals of §3.6 live in named stack slots; everything else is an SSA value.
- **The verifier** checks that definitions dominate uses, that jumps pass arguments of their blocks' parameters'
  number and types, that terminators end blocks, and the stage's invariants; it runs after each pass when
  `QUEST_CHECK_IR=1`, as the IR's does.
- **A textual form,** dumped by `--stop-after ssa` and by later stages (`ssa_arm64`, `arm64_asm`), with goldens owned
  by the self-hosted compiler (testing.md §2.8).

**Construction.** The IR is structured, which makes the simple algorithm of Braun et al. (*Simple and Efficient
Construction of Static Single Assignment Form*, CC 2013) a good fit: blocks are sealed as the structured statements
are walked, and a mutable local's reads find their definitions on the fly, with no dominance frontiers. `if`,
`switch`, `loop`, `break`, `continue`, and `join` become blocks and edges; a join point is a block whose parameters
are its own.

### 3.3. Layout and the ABI

- **Layout.** The arm64 backend computes every offset, size, and alignment that clang computes for the C backend's
  structs: tuples, records, options, variants, environments, module records, and the runtime's own types (`QClosure`,
  `QArray`, `QString`, `QVariantVal`, descriptors, handlers). These live in one shared module, and the C backend
  emits a `static_assert(offsetof(...) == N)` for each layout it prints, so that any C compilation checks the arm64
  backend's arithmetic. The runtime's types get the same assertions in `quest_runtime.c`.
- **Calls** follow Apple's AAPCS64, as clang does for the same C declarations: integer and pointer arguments in
  `x0`–`x7`, `double`s in `d0`–`d7`, the rest on the stack; a 16-byte composite that is not all `double`s in two `x`
  registers, even if it holds a `double`; results in `x0`/`x1` or `d0`; the caller extends arguments narrower than 32
  bits. The closure calling convention of [runtime-design.md](runtime-design.md) §4.1 and the signatures of
  [c-representation.md](c-representation.md) §6.2 are the contract.
- **A unit's interface to others** is what its C would define: the exported wrappers `qv_<mod>_<fn>`, the module
  record and initializer (`qv_mod_<M>_init`, [build-process.md](build-process.md) §8), the registration of record
  dictionaries and function tables, and `main` for a program. A C unit importing a native one includes the same
  `.int.h` as before.

### 3.4. Static data

Each unit's data, which clang now lays out from C initializers: static descriptors and descriptor templates, string
literals, static closures `{ fn, NULL }`, record dictionaries and offset tables, the function table of
[exceptions.md](exceptions.md) §5.2, module records and their guards, and source locations for raise sites. Pointers
in data are relocations. Read-only data goes in `__TEXT,__const` or `__TEXT,__cstring`; data with pointers in
`__DATA,__const` (or `__DATA` when written at run time).

### 3.5. Instruction selection

Greedy pattern matching over single-use values within a block, producing machine SSA: arm64 instructions over
virtual registers, with fixed-register constraints at calls, returns, and parameters. arm64 is three-address with
few constraints, so the patterns are few:

- address modes: base plus immediate offset, base plus scaled index;
- constants: `movz`/`movk` sequences, logical immediates, `adrp` + `add` for symbols;
- shifted and extended operands, `madd`/`msub`;
- comparison fused into branches: `cbz`/`cbnz`, `tbz`/`tbnz`, `cmp` + `b.cond`; `csel`/`cset` for values;
- `ldp`/`stp` for the halves of 16-byte values and for saving registers.

### 3.6. Exceptions

**Today** a `try` pushes a `QExceptionHandler` holding a `jmp_buf` (`runtime/quest_runtime.h`) onto a thread-local
chain and calls `_setjmp`; a raise walks the chain (exceptions.md §5.1) and `_longjmp`s. `_setjmp` stores all the
callee-saved registers (`x19`–`x28`, `fp`, `lr`, `sp`, `d8`–`d15`) through a dyld stub: no system call, but
flat-array, with a `try` in its innermost loop, spends 69 percent of its time there ([benchmarks.md](benchmarks.md)
§3.5).

**C cannot do much better.** clang does not provide `__builtin_setjmp`, which saves only the frame and stack pointers
and the resume address, on arm64. An assembly routine that returns twice is no better than `_setjmp`: clang keeps
values in callee-saved registers across any call, so the routine must save them all. Only inline assembly can let
clang save just the registers live across the `try`: an `asm goto` that stores `sp`, `fp`, and the handler label's
address, names the label as a target, and clobbers every callee-saved register. Whether clang keeps the label's code
and the frame as the handler expects is not something it promises, so that is an experiment, not part of this plan.
What C can do reliably is enter fewer handlers (§6).

**Native code can.** A native function controls its own registers, so its handler needs only where to resume:

- **One handler record, two kinds.** The record keeps its common fields (`prev`, `catches`, `n_catches`) first, then
  either the `jmp_buf` (C) or a resume address, `sp`, and `fp` (native), with a field telling which. A raise walks
  the chain as it does now and resumes a C handler with `_longjmp` and a native one through a small assembly routine
  in the runtime that sets `sp` and `fp` and branches. This is an ABI change (a version bump), and the C printers of
  both compilers change only in the field names they use.
- **At a native handler's entry every register is dead.** The function's frame is intact, and its prologue's saved
  registers are still in it, so its epilogue restores its caller's registers as usual. Values the handler uses come
  from the frame.
- **SSA and `try`.** As the C printer marks `volatile` the mutable variables assigned in a `try` body and live in its
  handler or after the `try` (ir.md §6.4), the SSA keeps exactly those in stack slots rather than promoting them.
  Every other value the handler uses dominates the `try`'s entry, so the handler block needs no parameters from the
  points that raise. The register allocator gives each value live into a handler a stack slot that is valid
  throughout the `try`'s body.
- **The chain stays thread-local** (`_Thread_local`, though Quest has no threads). On Darwin, native code gets a
  thread-local's address from its descriptor's accessor (`_tlv_get_addr`, a call); the address does not change
  within a thread, so a function that enters a `try` gets it once, and keeps it in a stack slot. Raises go through the
  runtime, as now.
- **Tracebacks** need no change to the runtime: native functions are in the unit's function table, have frame
  pointers, and have unwind information (§3.10).

### 3.7. Tail calls

A call in tail position is compiled as a jump (restore the callee-saved registers, `fp`, and `lr`; pop the frame;
`b` or `br`) unless:

- it is in a `try`'s body, whose handler must stay on the chain;
- an argument is an address in the caller's frame (`addr x` of a stack slot, for a `var`/`out` argument);
- the callee's stack arguments need more room than the caller's incoming argument area (rare: eight integer and
  eight `double` arguments go in registers).

Direct, indirect (through a closure), and runtime calls are all eligible. Self tail calls become jumps to the
function's first block, which also gives loops written as recursion (benchmarks.md §3.2) their speed. Frames
removed by tail calls are missing from tracebacks, as frames clang removes are now (exceptions.md §2.4).

### 3.8. Register allocation

`questlang/codegen/regalloc`, parameterized by a target description (register classes, allocatable and fixed
registers, what a call clobbers), so that it can be tested on its own.

1. **First, a trivial allocator:** every virtual register gets a stack slot, and each instruction loads its operands
   into scratch registers and stores its results. It is small, obviously correct, and stays as the baseline the real
   allocator is tested against.
2. **Then linear scan on SSA** (Wimmer and Franz, *Linear Scan Register Allocation on SSA Form*, CGO 2010), with
   interval splitting, spilling, and rematerialization of constants.
3. **Out of SSA:** split critical edges, turn block arguments into parallel copies, and sequence each set of copies,
   breaking cycles with a scratch register.

Registers: `x18` is never used; `x16`/`x17` are scratch only within a sequence (the linker's veneers use them);
`x29` is always the frame pointer; `x19`–`x28` and `d8`–`d15` are callee-saved (the low 64 bits of `d8`–`d15`,
which is all a `double` needs). A pointer is never held only in a floating-point register (§3.13).

### 3.9. Primitive semantics

Native code must do what the C helpers do, including the cases where arm64 and C differ:

- `sdiv` does not trap on zero, and gives `INT64_MIN` for `INT64_MIN / -1`, which is undefined in C; the helpers
  (`quest_int_div_at`, ...) say what Quest does.
- Shift counts are taken modulo 64 by arm64 and are undefined in C past 63; the word helpers handle the counts.
- `fcvtzs` saturates; C's conversion of an out-of-range `double` is undefined.
- `Real` arithmetic raises `real.error` on a NaN result, and division on a zero divisor (`quest_real_result_at`).

The inventory of step 1 lists every helper, and the arm64 tests (§4) cover each edge case against the C backend.

### 3.10. Frames, symbols, and unwind information

Every function has a frame record (`stp x29, x30`) and sets `x29`, which Darwin requires and the traceback walk
uses. The prologue and epilogue save the callee-saved registers the function uses, with `.cfi` directives from which
the assembler and linker make compact unwind entries. Each function has a symbol (local unless exported), so that
`dladdr` attributes frames as exceptions.md §5.3 describes, and the unit emits `.subsections_via_symbols`. The
stack-overflow handler (exceptions.md §6) works unchanged.

### 3.11. Emission

**Assembly text first,** assembled by `clang -c`: the assembler does instruction encoding, relocations, Mach-O, and
unwind tables, the text is readable when debugging, and assembling it is a check in itself. Darwin's spellings:
`_` before every C symbol, `L` before local labels, `sym@PAGE`/`sym@PAGEOFF` for addresses, `@GOTPAGE`/`@GOTPAGEOFF`
for data in dylibs, `@TLVPPAGE`/`@TLVPPAGEOFF` for thread-locals' descriptors, `bl _f` for any call (the linker
adds stubs). The linker signs arm64 executables ad hoc. All of
this is in one module, so that another object format would replace only it.

An in-memory encoder (instructions to 32-bit words, with relocations) belongs to step 7, the JIT; the instruction
descriptions should be data that both the printer and an encoder can use, and the encoder can then be tested byte for
byte against the assembler.

### 3.12. Build integration and mixing units

- **Selecting it:** `--backend arm64` (the default stays `c`; `ssac` selects the oracle). Every unit of the build is
  compiled by the selected backend.
- **No fallback.** A unit using something the arm64 backend does not support yet is an error that names the
  construct, never compiled with C instead, so that a passing test means what it says.
- **Choosing per unit** (for bring-up, tests, and finding a miscompile): an option naming units and the backend
  each is compiled with, overriding `--backend` for them. During bring-up, a test whose units are not all supported
  is on a pending list (§4) until they are.
- **Artifacts:** an arm64 unit writes `.mod.s` (or `.main.s`) where the C backend writes `.mod.c`, and its `.o` in
  the same place. The backend that wrote a unit's `.o` is recorded with its artifacts, and an `.o` from the other
  backend is stale. Interface headers are still written when a C unit needs them; the arm64 backend reads layouts
  from interfaces, not from headers.
- **Whole-program compilation** (build-process.md §1.2) comes after self-hosting with the arm64 backend (step 13).

### 3.13. The collector

Boehm's collector scans the stack and registers conservatively, so native code needs no stack maps. It does need:

- no pointer held only in a floating-point register, or in a spill slot the collector cannot see;
- no derived pointer outside its object while the object is live only through it (a pointer to one past an array,
  kept as a loop's end). Nothing in this plan makes one; later optimizations must not;
- interior pointers to be recognized, as for C now (a proxy is its original's address plus one).

The SSA's `ptr` type costs little and keeps stack maps, and so a precise or moving collector, possible later.

### 3.14. The SSA-to-C printer

`questlang/codegen/ssac` prints a unit's low-level SSA as C, as MLton's C backend prints its lowest IR: each block a
label, each SSA value a local, block arguments assignments before the `goto`, stack slots a local byte array, and
memory reached by byte offsets (`*(int64_t *)(p + 16)`). It computes no layout and chooses no representation; it
only prints what the SSA says, so a test that passes through it checks the SSA's construction, the shared layout
(its units link with the C backend's, which assert their offsets), and every lowering before instruction selection.

- **Calls** are C calls of the declared signatures, so clang applies the ABI; the arm64 backend's ABI lowering is
  checked by the mixed builds instead (§4).
- **`try`** is a C `try` as now: the handler record, `_setjmp` at the region's entry, and a `goto` to the handler
  block when it returns again. The SSA's rule for `try` (§3.6) is the rule `_setjmp` needs: values the handler uses
  were defined before the region, and mutable variables live in it are stack slots, which the printer declares
  `volatile`.
- **Tail calls** are ordinary calls, which clang may or may not make jumps.

It stays after the arm64 backend is complete: a test that fails with arm64 and passes with `ssac` is a bug after
the SSA, and one that fails with both is a bug in it or before it.

## 4. Testing

- **The shared goldens** of what programs do run with `--backend ssac` and `--backend arm64` too (runner modes, as
  `--self-hosted` is), and every run test passes with each. Until then, each mode has a pending list, as the
  self-hosted driver had (`tests/self-hosted/pending.txt`, testing.md §2.3): a pending test that passes fails, so the
  list only shrinks.
- **Mixed builds:** each multi-unit test also runs with its units split between the backends (alternating, and the
  other way), which finds any disagreement about layout or calls.
- **Calls between C and native code,** generated for each kind of signature: integers, `double`s, 16-byte values,
  descriptors, closures, `var`/`out` pointers, more than eight arguments, in both directions.
- **Layout assertions** (§3.3) compile in every C unit.
- **The verifier** after every stage, and the SSA's goldens.
- **The real allocator against the trivial one:** the suite passes with each.
- **The self-hosting check** with the arm64 backend: stage 2 built by it compiles the compiler and writes the same
  artifacts as stage 2 built by the C backend.
- **Before every push,** `tools/check` runs all of these, the `ssac` and `arm64` modes included, though it takes
  longer for them.
- **Benchmarks:** compile and run times against the C backend, recorded with their dates in benchmarks.md.

## 5. Steps

1. **Inventory the C backend's implicit decisions** (§3.1, §3.9). *Done when* this document lists each decision and
   where the arm64 backend gets it, and the shared passes or modules it calls for are planned here.
2. **Share what the inventory says to share,** and give the runtime's `static inline` helpers out-of-line
   definitions. *Done when* the C backend consumes the shared passes, the suites and the self-hosting check pass, and
   the goldens they change are updated.
3. **Shared layout with assertions** (§3.3). *Done when* every C unit and the runtime assert the offsets the shared
   module computes, and the suites pass.
4. **The SSA:** nodes, printer, verifier, construction (§3.2), with `--stop-after ssa`. *Done when* every run test's
   units build SSA that verifies, with goldens for a selection.
5. **The SSA-to-C printer** (§3.14) and `--backend ssac`, with its runner mode and pending list. *Done when* the
   suite passes with `ssac`, its pending list is empty, and multi-unit tests pass with their units split between
   `ssac` and `c`.
6. **A first arm64 backend:** instruction selection, the trivial allocator, frames, static data, emission, and
   linking, for straight-line code, calls, and control flow; other constructs are errors (§3.12). *Done when* the
   tests that use only those pass with `--backend arm64`, and the rest are on its pending list.
7. **Every construct:** closures, descriptors, conversions, records, variants, arrays, strings, modules and their
   initialization, function tables. *Done when* only tests that raise or catch exceptions are pending.
8. **Exceptions** (§3.6): the shared handler record (ABI bump), native `try` and `raise`, tracebacks. *Done when* the
   pending list is empty, and mixed builds raise across the backends both ways.
9. **`tools/check` runs everything** (§4): the `ssac` and `arm64` modes and the mixed-build and ABI tests, before
   every push. *Done when* it does, with both pending lists empty.
10. **Tail calls** (§3.7). *Done when* self, sibling, and closure tail calls are jumps, and a deep tail recursion runs
    in constant stack.
11. **Linear scan** (§3.8). *Done when* the suite passes with it, and benchmarks.md has dated run and compile times
    for both backends.
12. **Self-hosting with the arm64 backend** (§4). *Done when* the check passes, and `./questc` can build its stages
    with either backend.

13. **Whole-program compilation** with the arm64 backend (build-process.md §1.2). *Done when* `--whole-program`
    builds with `--backend arm64` (and `ssac`) pass the suite.

## 6. Possible Future Optimizations

Not part of this plan: what might be done once it is complete, each to be measured (benchmarks.md) before and after.
The list grows as ideas come up; when the plan is complete, what remains moves to benchmarks.md §3.

- **On the SSA:** copy propagation, constant folding, dead code elimination, value numbering, block merging and jump
  threading.
- **Inlining,** on the IR rather than the SSA, so that every backend gains (benchmarks.md §3.3).
- **Entering fewer handlers:** a `try` whose body cannot raise (no calls and no operations that raise) pushes no
  handler, and a raise whose handler is in the same function is a jump (benchmarks.md §3.5). On the IR, for every
  backend.
- **Runtime helpers expanded inline** by instruction selection, rather than called out of line (§3.1).
- **A cheaper `try` in C:** the `asm goto` experiment of §3.6.
- **Allocating spill slots and stack slots better:** sharing slots between values whose lifetimes do not overlap, and
  `ldp`/`stp` for adjacent spills.
- **Better register allocation** than linear scan, if measurements show spilling costs.
