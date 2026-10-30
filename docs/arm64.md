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
- **Debug information** (decided 2026-10-29): DWARF line tables (`.file` and `.loc` directives, from the IR's source
  offsets), in a step of their own after linear scan; no variable locations.
- **The default backend** stays C; whether arm64 becomes the default (for programs, for building the compiler, for
  releases) is decided after step 12, from measured compile and run times (decided 2026-10-29). No such decision is
  final: step 12's measurements are of a backend without most optimizations (§6), and as its code improves, arm64
  becomes the more likely choice. The question is reopened whenever benchmarks.md records a significant change.
- **One SSA-based C backend in the end** (step 15): the tree-walking C printer is a second, hand-written
  implementation of every operation's access sequence (§3.1), kept in agreement with the SSA's builder only by tests.
  Once the SSA's code is good enough, `ssac` replaces it as the self-hosted compiler's C backend, so that each
  operation is lowered once. The bootstrap's C printer stays, since the bootstrap gets no SSA.

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

The C backend leaves much of the lowering to C and clang: struct layout, static initializers, the 89 `static
inline` helpers and the macros of `runtime/quest_runtime.h` (integer division, `Real` results, word operations,
proxies, ...), the calling convention, and `setjmp`. The SSA backends must decide each of these themselves, as C does,
since their units link with C's.

The inventory (§7) lists each decision and where the SSA backends get it. In short:

- **Layout is simple.** Every aggregate slot is one word, so tuples, records, options, and offset tables are word
  arithmetic, which the shared `layout` module can compute (step 3). Closure environments are private to their unit,
  so the SSA backends need not lay them out as C does.
- **Shared by step 2** (§7.5): thunks become IR functions made by a pass, so that every backend gets them; static data
  (descriptors, offset tables, tag maps) gets a shared description; slot conversions become data in `layout`; and
  the runtime's inline helpers get external definitions too.
- **Everything else is the SSA's construction:** each operation's access sequence (proxies, offset tables, view maps,
  option payloads, checks), `try`, and the unit's structure. It is a second implementation of what the C printer
  prints, kept in agreement by the mixed builds (§4).

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
  by the self-hosted compiler (testing.md §2.8): the SSA's for every run test, since it is target-independent and
  changes only when the lowering does; machine code's and assembly's for a curated set, each chosen for a construct
  (switches, `try`, closures, tail calls, spills), since they change with almost any backend change (decided
  2026-10-29).

**Construction.** The IR is structured, so its statements become blocks and edges directly. Mutable variables are
built as stack slots, loaded and stored (decided 2026-10-29, [ssa.md](ssa.md) §4); a later pass promotes those whose
address is not taken to values, for which Braun et al.'s algorithm (*Simple and Efficient Construction of Static
Single Assignment Form*, CC 2013) suits the structured IR: blocks sealed as they are walked, with no dominance
frontiers. `if`,
`switch`, `loop`, `break`, `continue`, and `join` become blocks and edges; a join point is a block whose parameters
are its own.

### 3.3. Layout and the ABI

- **Layout.** The arm64 backend computes every offset and size that clang computes for the C backend's structs, and
  the C asserts each, so that any C compilation checks the arm64 backend's arithmetic:
  - aggregates' structs (tuples, records, options and their cases' payloads): `codegen/layout` (`tupleBytes`,
    `recordFieldOffset`, `optionBytes`, `slotsBytes`), asserted after each struct the C defines, in units and in
    interface headers (`static_assert(... == N, layout_<struct>_...)`);
  - the unit's static data (descriptors and their payloads, offset tables): `codegen/staticdata` (step 2), asserted
    after each;
  - the runtime's own structs that generated code touches (`QClosure`, `QArray`, `QString`, `QExceptionState`,
    `QViewMap`, every descriptor struct, ...) and its constants (`QTypeKind`'s, `Q_CATCH_ALL`, ...):
    `codegen/runtimeLayout`, a table that the questlang test `codegen_runtime_layout` prints as C assertions and
    `tests/python/test_runtime_layout.py` compiles against `quest_runtime.h`.

  Closure environments are private to their unit and need no assertions (§7.1); the exception handler's layout
  changes in step 8.
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

**As built (2026-10-30).** `questlang/codegen/regalloc` is linear scan in its simplest form (Poletto and Sarkar's),
not yet Wimmer and Franz's: each value has one range, the hull of where it is live (liveness over the blocks in
reverse postorder, a jump's arguments used at its end and its destination's parameters written there), and a value
spilled is spilled throughout. A range that crosses a call takes only a callee-saved register; when none of its class
is free, whichever range ends last is spilled. There is no splitting and no rematerialization yet. The registers it
gives are `x12`–`x15`, `x19`–`x28`, `d16`–`d31`, and `d8`–`d15`, none an argument, a result, or a scratch register
(`x9`–`x11`, `x16`, `x17`, `d0`, `d1`), so a call's arguments can be loaded in any order; a thread-local's address,
whose accessor is called, counts as a call. The prologue saves the pairs of callee-saved registers the function's
values use. A jump's copies are moves when no parameter's register holds another of its arguments, and otherwise go
through the copy area, as before. A function that enters a `try` keeps every value in its slot, as step 8 left it,
which also keeps its handler's view of them simple (§3.6). `regalloc_scan` (a questlang test) shows its choices on
small functions with a target of a few registers.

**With splitting (2026-10-30, after Wimmer and Mössenböck, *Optimized Interval Splitting in a Linear Scan Register
Allocator*, VEE 2005).** A value's interval is now the ranges where it is live, with holes, so another value can
use its register in a hole. Intervals are taken in order of their starts:

- **A free register.** An interval takes a register free for all of it, a caller-saved one first. If none is, it
  takes the one free longest and the rest is split off, as long as some register is free where it starts.
- **None free.** It takes the register whose holders are next used furthest away, splitting them where it starts,
  unless its own next use is further. In that case it is spilled until that use, from which the rest is allocated
  again.
- **Calls and handlers.** A caller-saved register is unavailable from just after a call the interval is live
  across. Every register is unavailable at the start of a `try`'s handler that the interval covers.

So a value lives in pieces, each in a register or in memory:

- **Memory.** A value with a piece in memory is stored to its slot where it is defined. Because an SSA value never
  changes, the slot stays valid wherever the value is live. A piece in memory therefore costs nothing to enter,
  and a split child is always in memory until its next use.
- **Back to a register.** A piece in a register that starts inside a block starts at a use. The allocation's
  `moves` load it there (or move it between registers) just before that instruction.
- **Block starts.** A piece that starts at a block's start is reached by the code of each edge into the block. Its
  parallel moves take each parameter to its register and its slot, and each value live in from where it is at the
  edge's source. They are sequenced so that nothing is overwritten before it is read. When only cycles are left,
  one move's source is copied to the scratch register `x10` (through `fmov` for a `d` register), which breaks its
  cycle, so a frame no longer needs a copy area. A branch's edges each have their own code (after `cbz`, on each
  side), so no critical edge needs splitting.
- **Rematerialization.** A constant, a real constant, the null, a slot's address, or a symbol's address (not a
  thread-local's) needs no slot. Where it is in memory it is computed again, and if its first piece is in memory,
  its instruction emits nothing.
- **`try` functions.** A function that enters a `try` is allocated like any other. What its handler uses is in
  memory at the handler's start, so the handler's code reloads it. The function still saves every callee-saved
  pair, which it must restore for its caller after a raise has passed through frames that clobbered them.

`regalloc.spillAll`, every value in memory, remains as the baseline.

### 3.9. Primitive semantics

Native code must do what the C helpers do, including the cases where arm64 and C differ:

- `Int` arithmetic wraps (§8): `+`, `-`, and `*` overflow, undefined in C, gets `-fwrapv`.
- `sdiv` does not trap on zero, and gives `INT64_MIN` for `INT64_MIN / -1`, which is undefined in C (`quest_int_div_at`
  checks only for zero).
- Shift counts are taken modulo 64 by arm64 and are undefined in C past 63; the word helpers handle the counts.
- `fcvtzs` saturates; C's conversion of an out-of-range `double` is undefined.
- `Real` arithmetic raises `real.error` on a NaN result, and division on a zero divisor (`quest_real_result_at`).
- `Char` is C's `char`, which is signed on Darwin arm64, so a `Char` widened to a slot is sign-extended. This ties the
  language to a platform's choice; the preference is `uint8_t` (§10.4).

The inventory (§7.2) lists every helper, and the arm64 tests (§4) cover each edge case against the C backend.

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

- **Calls** are C calls through a pointer to a function of the types the call's arguments and results have (a 16-byte
  composite a struct of two words, one passed through memory a struct of its bytes), so clang applies the ABI as the
  callee's own C declaration would; the arm64 backend's ABI lowering is checked by the mixed builds instead (§4).
- **`try`** is a C `try` as now: the handler record, `_setjmp` at the region's entry, and a `goto` to the handler
  block when it returns again. The SSA's rule for `try` (§3.6) is the rule `_setjmp` needs: values the handler uses
  were defined before the region, and mutable variables live in it are stack slots. A function that enters a `try`
  has its values `volatile`, and reaches memory through `volatile` pointers.
- **Data** is arrays of words (`void *` for words, `char` for text, `uint64_t` for zeros), declared before the
  functions and defined after them, so that data and functions may refer to one another in any order.
- **Tail calls** are ordinary calls, which clang may or may not make jumps.

It stays after the arm64 backend is complete: a test that fails with arm64 and passes with `ssac` is a bug after
the SSA, and one that fails with both is a bug in it or before it.

### 3.15. Writing it in Quest

The SSA, the register allocator, and the arm64 backend are graph-heavy and mutation-heavy, and their inner loops run
over many small objects, unlike the parts of `questlang/` written so far. Since the bootstrap does not get them, they
need not follow its Python line by line, and are written for Quest directly.

**Entities are integers, and an efficient choice rather than a natural one.** As in Cranelift, a function's values,
blocks, instructions, and virtual registers are dense `Int`s, each kind numbered in a table of the function, and a
pass's side tables (liveness, intervals, assignments, spill slots) are `Array(Int)` or `Array(Bool)` indexed by them.
Side tables are then arrays, with no hashing (`util/hash.identityHash` remains the choice for keys that are not dense
indices); "none" is `-1`, without a `maybe.T`; and graphs have no cycles to tie. This is closer to C or Fortran than
to Quest: the type checker cannot tell a block's number from an instruction's, so indexing the blocks with an
instruction's number is an error it does not catch. Quest's typed alternatives cost too much today:

- a one-case variant (`Variant block: Int end`) is a distinct type that allocates nothing as a value, but an
  aggregate's slot holds a variant boxed (§7.1), so every id stored in an array or a node would allocate;
- an abstract type exported by the SSA's nodes module hides its `Int` from the other modules, which would reach it,
  and their side tables, through calls across modules, which are not inlined (benchmarks.md §3.3).

So the backend relies instead on names (`block`, `inst`, `value`, `vreg` in every identifier that holds one), on
helper functions that take and return one kind, and on the verifier, which checks each table's references after every
pass. Cross-module inlining would make abstract ids free, and the backend could adopt them then.

**Other conventions:**

- **One instruction shape:** an opcode, an `Array(Int)` of arguments, one of results, and an immediate or extra
  field. Quest has no reflection, so the IR's traversals are tables written by hand (`ir/walk`); with one shape, the
  structural passes (verifier, uses and definitions, renaming, liveness, allocation, leaving SSA) loop over arrays,
  and only the passes that care what an instruction means (instruction selection, printers, optimizations) case on
  its opcode.
- **Opcodes are options, not strings,** cased on without `else`, so that a new opcode is a type error everywhere it is
  not handled. The C backend's string kinds (`shape.kind`, `plan.kind`, access modes) are not copied. A payload-free
  option case allocates each time it is made (benchmarks.md §3.6), so each opcode is made once, as a constant of its
  module, and `ordinal` indexes tables by opcode.
- **Tuples for nodes and tables,** whose fields are at fixed offsets; records only where their subtyping is needed,
  since a record's field is read through its offset table. **Options** for sum types with several fields, their
  payloads' `var` fields rewritten in place, as the IR's are; **variants** for small hot sum values held in
  variables rather than in aggregates (an operand's location: `reg`, `stack`, `imm`), which allocate nothing.
- **Inner loops index arrays directly.** A call of `vector.get`, `maybe.isSome`, or `hashMap` crosses modules through
  closures and descriptors; a local function that captures variables allocates each time its definition is
  evaluated (benchmarks.md §3.2); a `try` costs a `_setjmp`. Helpers in the same module, not polymorphic, are cheap.
- **`maybe.T` is abstract** (`lib/util/maybe.int.quest` exports `T::ALL(A::TYPE) TYPE`), so code reaches it only
  through `isSome`, `unwrap`, and the rest, which take their type arguments at every call and cross modules. Making
  it a manifest option type (proposed; a library change, so released before `questlang/` uses it) would let code
  `case` on it directly. Until then, integer tables keep most `maybe.T`s out of the backend.
- **Patterns as functions.** `case` matches one level, with no nested patterns or guards, so instruction selection's
  patterns (§3.5) are functions over the table of definitions (`defOf(value)`, `shiftedByConstant(value)`).
- **Text through a string builder** (`util/stringbuilder`) or straight to a writer, not chains of `<>`, each of which
  allocates a new string.
- **Iteration, not recursion, over graphs:** compiled Quest uses about 2 KB of stack per call, so reverse postorder,
  dominators (Cooper, Harvey, and Kennedy's iterative algorithm), and liveness use explicit worklists.
- **A bitset library** (`collections/bitset`) for liveness, which `lib/` lacks. A new library reaches `questlang/`
  only after a release (release-compiler.md §2), so it lands in step 3.

## 4. Testing

- **The shared goldens** of what programs do run with `--backend ssac` and `--backend arm64` too (runner modes, as
  `--self-hosted` is), and every run test passes with each. Until then, each mode has a pending list, as the
  self-hosted driver had (`tests/self-hosted/pending.txt`, testing.md §2.3): a pending test that passes fails, so the
  list only shrinks.
- **Mixed builds:** each multi-unit test also runs with its units split between the backends (alternating, and the
  other way), which finds any disagreement about layout or calls. For `ssac` (step 5), every test is multi-unit (its
  library modules are units too), and the runner's `ssac-program` and `ssac-modules` modes compile the program's unit
  or its modules' through `ssac` and the rest through C, so that calls, closures, records, and exceptions cross
  between the backends both ways; `tests/self-hosted/backends.py` builds one program with every split in one build
  directory.
- **Calls between C and native code,** generated for each kind of signature: integers, `double`s, 16-byte values,
  descriptors, closures, `var`/`out` pointers, more than eight arguments, in both directions.
- **Layout assertions** (§3.3) compile in every C unit.
- **The verifier** after every stage, and the SSA's goldens.
- **The real allocator against the trivial one:** the suite passes with each.
- **The self-hosting check** with the arm64 backend: stage 2 built by it compiles the compiler and writes the same
  artifacts as stage 2 built by the C backend.
- **Before every push,** `tools/check` runs all of these, the `ssac` and `arm64` modes included, though it takes
  longer for them. The self-hosting check through the `ssac` and `arm64` backends (the compiler built by each,
  compiling itself to a fixed point) runs on demand until the compiler self-hosts fully on arm64 (step 12), and from
  then on through both before every push (decided 2026-10-29).
- **Benchmarks:** compile and run times against the C backend, recorded with their dates in benchmarks.md.

## 5. Steps

1. **Inventory the C backend's implicit decisions** (§3.1, §3.9). *Done* (2026-10-29): §7, with what step 2 shares in
   §7.5 and what it decided in §8.
2. **Share what §7.5 lists:** thunks as IR functions, the description of static data, slot conversions as data, and
   the runtime helpers' external definitions; and make `Int` arithmetic wrap everywhere (§8). *Done* (2026-10-29):
   `Int` wraps (ABI 52); the helpers have external definitions (ABI 53); thunks are IR functions (`ir/thunks`, ir.md
   §8.4.1); slot conversions are layout's word forms; and `codegen/staticdata` describes the descriptor forms,
   record naming, descriptors, offset tables, and tag maps (the function-type adapters are those of its function
   descriptors, whose code each backend generates), whose sizes and offsets the C asserts.
3. **Shared layout with assertions** (§3.3), and `collections/bitset` (§3.15). *Done* (2026-10-29): `codegen/layout`
   and `codegen/staticdata` compute every struct's layout and the C asserts them (ABI 54); `codegen/runtimeLayout`'s
   table of the runtime's structs is checked against the header; release a5ddef5b has `collections/bitset`.
4. **The SSA:** nodes, printer, verifier, construction (§3.2), with `--stop-after ssa`. *Done* (2026-10-29): every
   run test's program unit builds SSA that verifies, with a golden for each ([ssa.md](ssa.md) §6); the questlang test
   `ssa_verify` checks the verifier. Decided while building it: mutable variables are stack slots, promoted by a later
   pass, rather than built into values on the fly (ssa.md §4). Module units are built through the SSA by `ssac`'s
   builds in step 5, which run every unit through it.
5. **The SSA-to-C printer** (§3.14) and `--backend ssac`, with its runner mode and pending list. *Done*
   (2026-10-29): every golden and error test of the self-hosted suite's compiled phase passes with every unit, the
   library's included, compiled by `ssac`, and with the program's unit or its modules' alone (`run_tests.py
   --self-hosted --backend ssac`, `ssac-program`, `ssac-modules`); `tests/self-hosted/pending-ssac.txt` is empty;
   and `tools/check` runs the three modes before every push (decided 2026-10-29: from this step on, rather than from
   step 9). What it settled (§9 has the rest):
   - **`ssac`'s C includes no header** and declares everything itself, so that nothing it prints conflicts with the
     runtime's declarations: a symbol the unit does not define is `extern char name[]` (a thread-local, `extern
     __thread`); each call goes through a pointer to a function of the types its arguments and results have, a
     16-byte composite as a struct of two words and one passed through memory as a struct of its bytes, so that
     clang passes them as AAPCS64 does. Its units compile as GNU C, with `-fno-strict-aliasing` (they read and write
     a word of memory as different C types) and `-fno-builtin` (`ssac.cFlags`).
   - **Static data is the SSA's,** not the C declarations' (superseding what was settled before this step): a unit's
     data is words, text, and zeros (ssa.md §5), its descriptors laid out by `ssa/statics` from `codegen/staticdata`'s
     descriptions, and its function types' adapters, thunks, and invokers, its exported functions, its function
     table, and `qr_register_dicts` built as SSA functions, so that the arm64 backend emits the same data and code.
   - **The backend is chosen per unit** (`codegen/choice`): `--backend` for every unit, and a repeatable
     `--unit-backend UNIT=BACKEND` for one, a unit named as its manifest names it (a module by its canonical name,
     the program as `main`). A unit's manifest records its backend (`"backend"`), and a unit compiled by another is
     stale. `--whole-program` stays the C backend's until step 13.
6. **A first arm64 backend:** instruction selection, the trivial allocator, frames, static data, emission, and
   linking, for straight-line code, calls, and control flow; other constructs are errors (§3.12). *Done*
   (2026-10-29), with step 7: `codegen/arm64/codegen` compiles the SSA with the trivial allocator (every value has a
   slot in its frame; each instruction loads its arguments into scratch registers and stores its results), and
   `codegen/arm64/asm` spells Darwin's assembly; a unit's `.mod.s` (or `.main.s`) is assembled by `clang -c`. Every
   golden and error test passes with `--backend arm64`, with the program's unit alone (`arm64-program`) and with the
   modules' alone (`arm64-modules`); `tests/self-hosted/pending-arm64.txt` is empty, and `tools/check` runs the
   three modes (ahead of step 9). Decided while building it:
   - **A `try` called `_setjmp`,** with the C backend's handler record, until step 8: the trivial allocator keeps no
     value in a register across a call, so `_setjmp`'s register restore lost nothing.
   - **Narrow arguments** (a C `bool` or `char`) are marked in the SSA (`narrow`, ssa.md §2.2): Darwin packs them on
     the stack a byte each, which a mixed build of `tests/self-hosted/backends` (with more arguments than registers)
     found, for `ssac` too; and a function extends its own on entry, since a C caller leaves their upper bits
     unspecified.
   - **Every symbol the unit does not define is reached through the GOT,** a thread-local through its descriptor's
     accessor, so that one spelling serves the runtime, other units, and the system's libraries.
7. **Every construct:** closures, descriptors, conversions, records, variants, arrays, strings, modules and their
   initialization, function tables. *Done* (2026-10-29) with step 6: the SSA had lowered every construct to loads,
   stores, and calls, so nothing was pending.
8. **Exceptions** (§3.6): the shared handler record (ABI bump), native `try` and `raise`, tracebacks. *Done when* the
   pending list is empty, and mixed builds raise across the backends both ways. *Done* (2026-10-29, ABI 55): the
   record's common fields come first, then `resume`, `sp`, and `fp`, then the `jmp_buf`; a C handler's `resume` is
   `NULL` (both C printers and the SSA's builder set it), and the native backend's `try` stores its handler block's
   address and its frame's `sp` and `fp` instead of calling `_setjmp`. A raise resumes a native handler with a few
   instructions of inline assembly in the runtime (`quest_resume_native`). Decided while building it:
   - **A function that enters a `try` saves every callee-saved register** (`x19`-`x28`, `d8`-`d15`) on entry and
     restores them at each return, with their unwind information: the frames a raise skips may have left anything
     in them, and the function's caller expects its own. That is one save per call, where `_setjmp` was one per
     `try` entered, so a `try` in a loop costs only its record's stores. `tests/self-hosted/backends` checks it: a C
     loop keeps its state in such registers across calls of a native closure that catches what C code raises.
   - The chain's thread-local address is still taken at each use (its accessor is a call), not once per function as
     §3.6 suggests; with the linear-scan allocator (step 11), a function that enters a `try` can keep it in a slot.
   - Tracebacks needed nothing: native functions are in their units' function tables and keep frame pointers.
9. **`tools/check` runs everything** (§4): the `arm64` mode, its mixed builds, and the ABI tests, before every push,
   besides `ssac`'s (step 5). *Done when* it does, with both pending lists empty. *Done* (2026-10-29), with step 8: its
   backends' suite runs `ssac`, `arm64`, and the mixed modes of each, both pending lists empty; the self-hosted
   suite runs `self-hosted/backends` (calls of every kind of signature across the backends, both ways), the ABI
   corpus, and `test_ssac`/`test_arm64`.
10. **Tail calls** (§3.7). *Done when* self, sibling, and closure tail calls are jumps, and a deep tail recursion runs
    in constant stack. *Done* (2026-10-29): `ssa/tailCalls` marks them as the builder finishes a unit, so the SSA
    dumps show them (`tail` before the call), and both native backends compile them:
    - A call is in tail position when its results, or the extension of its byte result (a `Bool` or `Char`, which
      every caller extends again), are returned, directly or through blocks that only pass them on to a `return`.
    - A function from which a stack slot's address may escape (stored, passed to a call, or returned, through
      arithmetic, copies, and block parameters) has no tail calls. That covers §3.7's first two exceptions at
      once: a `try`'s record is such a slot, and so is a `var` argument's cell and a composite passed through
      memory. It is coarser than §3.7 asks, a function with any such slot losing all its tail calls; the linear
      scan's liveness (step 11) can narrow it.
    - `arm64` compiles a call of the function itself as a jump to its first block, whatever its arguments; one of
      another function whose arguments all go in registers as the frame popped and `b` or `br`; and the rest as a
      call and a return, a coarser rule than §3.7's comparison with the caller's incoming argument area. `ssac` prints `return f(...);` and leaves the jump to clang.
    - `language/tail_calls` covers each case in every phase, a hundred deep; `self-hosted/backends` runs self,
      mutual, and closure tail recursions ten million deep with `arm64`, in the default 8 MB stack.
11. **Linear scan** (§3.8). *Done when* the suite passes with it, and benchmarks.md has dated run and compile times
    for both backends. *Begun* (2026-10-30) with promotion, as §6 suggests: `ssa/promote` makes values of the slots
    of whole words whose addresses do not escape, in functions without a `try` ([ssa.md](ssa.md) §4.1). Then the
    simplest linear scan (§3.8, as built), which the suite passes with. Then interval splitting, rematerialization,
    and allocation in functions that enter a `try` (§3.8, with splitting). benchmarks.md §4 has the run and build
    times of both backends from before splitting (arm64's geometric mean against MLton 11.6, C's 5.2); the same
    measurement with splitting remains.
12. **Self-hosting with the arm64 backend** (§4). *Done when* the check passes, `./quest` can build its stages with
    either backend, `tools/check` runs the self-hosting check through `ssac` and `arm64` too, and benchmarks.md has
    the measurements from which the default backend is decided.

13. **Whole-program compilation** with the arm64 backend (build-process.md §1.2). *Done when* `--whole-program`
    builds with `--backend arm64` (and `ssac`) pass the suite.
14. **Line tables** (§1). *Done when* native code has `.file` and `.loc` directives for its source lines, and lldb
    shows a breakpoint's Quest line and a backtrace's lines in a test program.
15. **`ssac` as the C backend** (§1). Measure `ssac`'s code and compile times against the C printer's, with the
    SSA's promotion of stack slots (§6) and whatever else the comparison needs. If `ssac` is close enough, it becomes
    the self-hosted compiler's C backend: `--backend c` selects it, the C printer and its goldens are retired, and
    `--whole-program` goes through the SSA. *Done when* the self-hosted compiler has one C backend, or benchmarks.md
    records why the C printer stays and what would change that.

The plan is not complete until each hazard of §10 is addressed or shown not to arise.

## 6. Possible Future Optimizations

Not part of this plan: what might be done once it is complete, each to be measured (benchmarks.md) before and after.
The list grows as ideas come up; when the plan is complete, what remains moves to benchmarks.md §3.

- **On the SSA:** promoting mutable variables' stack slots to values (§3.2), copy propagation, constant folding, dead
  code elimination, value numbering, block merging and jump threading.
- **Inlining,** on the IR rather than the SSA, so that every backend gains (benchmarks.md §3.3).
- **Entering fewer handlers:** a `try` whose body cannot raise (no calls and no operations that raise) pushes no
  handler, and a raise whose handler is in the same function is a jump (benchmarks.md §3.5). On the IR, for every
  backend.
- **Runtime helpers expanded inline** by instruction selection, rather than called out of line (§3.1).
- **A cheaper `try` in C:** the `asm goto` experiment of §3.6.
- **Allocating spill slots and stack slots better:** sharing slots between values whose lifetimes do not overlap, and
  `ldp`/`stp` for adjacent spills.
- **Better register allocation** than linear scan, if measurements show spilling costs.
- **Payload-free option cases as shared constants** (benchmarks.md §3.6), so that a case such as `maybe.none` or an
  opcode allocates nothing. `is` compares options by address, so this changes what `is` says of two such values, a
  decision for the language.
- **Options like `maybe.T` as a pointer or 0, with nothing allocated** (noted 2026-10-29; nothing done yet): for an
  option with one case whose payload is one pointer, which is never 0, and other cases without payloads, the
  payload-free case is 0 (or, for several, small integers below the first page) and the other case is its payload's
  pointer itself, as Rust represents `Option<&T>`. To be worked out:
  - **proxies** (c-representation.md §5.8): an option value may be a proxy, its low bit set, and so may a tuple or
    option payload, so the encoding must still tell a proxied option from a payload that is itself a proxy;
  - **case binders share payloads**, `var` components included, and a payload held as the option itself has no
    memory of its own for a binder to share, so only immutable payloads qualify;
  - **`is`**, which compares options by address now;
  - **everything that reads options by descriptor:** the runtime's readers (`quest_option_tag`,
    `quest_option_element`), `quest_convert`, dynamic values and their serialization, and the interpreters'
    agreement with compiled code.
- **Cross-module inlining** (benchmarks.md §3.3), which would also let the backend's ids be abstract types (§3.15).
- **Promotion before linear scan, and before step 12's measurements:** linear scan gains little while every mutable
  variable is a stack slot, so promoting slots, with copy propagation and dead code elimination, early would make
  both linear scan's and the default backend's measurements more representative (§1).
- **A calling convention of Quest's own for calls between native functions.** The SSA's calls now follow C's: values
  in the order of the C function's parameters, 16-byte composites' starts and `memory` arguments recorded, narrow
  results extended after the call (ssa.md §2.2). Making the convention an attribute of each function and call, C's
  only where C is on the other side (externals, the runtime, exported `qv_` functions, adapters, the function table),
  would let calls within native code use a convention of their own: no extension of narrow values, a 16-byte value
  split between registers and the stack, more argument and result registers, a fixed register for the environment,
  and tail calls that could be guaranteed, which §3.7's limit on stack arguments now prevents. It could start out
  identical to C's, so that adding the attribute changes no code.
- **Fixing the language's costs that shape the backend's code** (§3.15), so that its largest and most bug-prone
  parts can be written with types rather than conventions. Retrofitting typed ids into a mature allocator and
  instruction selector is costly, so these are worth doing before the backend grows large:
  - **payload-free option cases as shared constants** (above), so that opcodes need not be made once by hand;
  - **`maybe.T` as a manifest option type** (§3.15), so that code `case`s on it and needs no `-1` for "none";
  - **one-case variants unboxed in aggregates' slots,** so that a `Variant block: Int end` id costs nothing in an
    array or a node, and the type checker tells a block's number from an instruction's;
  - **typed ids even while they allocate,** if the language fixes come later, accepting their cost until they do.

## 7. Inventory of the C Backend's Decisions

Step 1's survey (2026-10-29) of `questlang/codegen/c/printer`, `declarations`, and `types`, and of
`runtime/quest_runtime.h`: what the C backend decides that is more than C syntax, and where the SSA backends (`ssac`
and `arm64`) get each decision. The sources are:

- **layout**: `questlang/codegen/layout` and `ir/shapes`, already shared;
- **pass**: a shared IR pass after describe (§7.5), whose results the C printer prints too;
- **data**: a shared description of static data (§7.5);
- **build**: the SSA's construction, which does what the C printer prints for the operation; the mixed builds (§4)
  check that the two agree;
- **runtime**: a call of the runtime, with the out-of-line helpers of §7.5;
- **abi**: the arm64 backend's ABI lowering (§3.3).

### 7.1. Values and Layout

Every aggregate slot is one 8-byte word, so most layouts are arithmetic on word indices, with no padding and no
alignment beyond 8.

| Decision | In the C backend | SSA backends |
|---|---|---|
| Scalars: `Int` `int64_t`, `Real` `double`, `Word` `uint64_t`, `Bool` C `bool` (1 byte), `Char` C `char` (signed on Darwin arm64), `Ok` nothing (a `void` result; `QVal` 0 where stored) | `layout.representation` | layout; a narrow value in a register is always extended to 64 bits (`Char` signed, `Bool` zero), and one received is extended again, never trusted (Apple's ABI extends only to 32 bits) |
| 16-byte values: a record is `QRecordVal { val, dict }`, a variant `QVariantVal { tag, payload }` | runtime structs | layout; two SSA values each (§3.2) |
| Slots: a record or variant in a slot is a pointer to an immutable 16-byte box; `Bool` and `Char` are widened to a word (`QBoolSlot`, `QCharSlot`); every other value is its own word | `layout.slotRepresentation` | layout |
| Slot conversions, value to slot and back: `Real` by its bits, `Bool`, `Char`, and `Int` as `.i`, a record or variant boxed or dereferenced | `codegen/c/types` (`shapeSlotToQval`, `qvalWrap`, ...), as C text | build, by rules moved into layout (§7.5) |
| Tuples: component `i` at `8i` | `emitAggregateStructs` | layout |
| Records: one allocation of the box (`QRecordVal`, 16 bytes) and then the payload: a header word (the layout's descriptor), then the fields sorted by name, a word each | `makeRecord`, `emitAggregateStructs` | layout |
| Options: `int64_t tag` at 0, then a union of the cases' components at 8, a word each; a case's binder points at offset 8, sharing the components | `emitAggregateStructs`, `optionCasePayload` | layout |
| Embedded boxes: the boxes of an aggregate's fresh record and variant components, 16 bytes each, after it in the same allocation | `embeddedBoxes`, `fillEmbedded` | build |
| Closure environments: descriptors `d_i`, then captures `c_i` in their C types, not slots (so `bool`, `char`, and 16-byte values, with C's padding); a type application's environment `{ orig, desc[n] }` | `envStruct`, `typeAppThunk` | build; only the unit that makes an environment reads it, so the SSA backends lay environments out as they like |
| Offset tables (record evidence): a `size_t` for each field of the view, sorted by name, then `stored_types`; static ones by `offsetof` | `emitEvidenceDictionaries` | layout for the offsets (word indices), data for the tables |
| Variant tags: a case's index in name order; tag maps between subtypes are static `int64_t` arrays | `shapes`, `emitCoercionTables` | layout, data |
| Tuple casts: a supertype's components at the same offsets as the subtype's prefix, checked by `static_assert` | `emitCoercionTables` | nothing: true of word slots by construction |
| Array elements: `QVal` words after `length`; a `Bool` or `Char` element's address is its word's first byte (little-endian) | `arraySlot` | build |
| Runtime structs read or written directly: `QClosure`, `QArray`, `QAuto`, `QRecordHeader`, `QExceptionState`, `QExceptionHandler`, `QViewMap.index`, offset tables, the proxy tag bit | `quest_runtime.h` | layout, with assertions in `quest_runtime.c` (step 3) |
| Descriptor structs: every `QTypeDescriptor` kind and its payload structs, with `bool` and `size_t` fields | `emitTypeDescriptors` (500 lines), `types.descriptorForm` | data, laid out by the runtime structs' layouts |
| Function-type adapters: for each function type described, `quest_adapt_<T>` (wraps a closure converted at run time by descriptor), its thunk, and `quest_invoke_<T>` (calls a closure with `QVal` arguments), which the runtime calls through the type's descriptor (found in step 2) | `emitFunTypeAdapters` | data describes them; each backend generates their code from it (the SSA's backends in the SSA), since the IR cannot express a call through a descriptor's invoker |

### 7.2. Operations

| Decision | In the C backend | SSA backends |
|---|---|---|
| `Int` `+`, `-`, `*`: C operators, without `-fwrapv`, so overflow is undefined; comparisons | `prim` | build: wraps (§8) |
| `Int` `/`, `%`, `mod`: a zero divisor raises `int.error`; `INT64_MIN / -1` and `INT64_MIN % -1` are undefined in C | `quest_int_div_at`, `quest_int_mod_at` (inline) | build: the zero check inline, then `sdiv` (and `msub`), which give `INT64_MIN` and 0 |
| `Real` `++`, `--`, `**`, `//`: a NaN result raises `real.error`, as does a zero divisor; `^^` | `quest_real_*_at` (inline), `quest_real_pow_at` | build for the inline ones; runtime for `^^` |
| `is`: `==` on words and pointers; through `quest_unproxy` for an original access; `quest_val_is(d, a, b)` on `QVal` words | `prim` | build; runtime for `quest_val_is` |
| `<>` and string constants: `quest_string_concat`; a constant is `quest_string_new(literal, length)` at each evaluation | `prim`, `const` | runtime, the literal's bytes as data |
| Word operations: the externals of `lib/word`, called directly (ABI 50), all `static inline` | `quest_word_*` | runtime, out of line (§7.5); inline later (§6) |
| Arrays: `quest_check_array_bounds_at` and `quest_check_array_count_at` (inline), `quest_array_new`; a literal allocated and filled inline | `arraySlot`, `makeArray` | build for the checks; runtime for the rest |
| Tuple components, and option tags and payloads, by access: direct; original (`quest_unproxy`: the tag bit cleared); proxy (the tag bit tested, then the runtime's `quest_proxy_*`, or the slot) | `tupleComponent`, `optionTag`, `optionComponent` | build; runtime for the proxy paths |
| Record fields: through the offset table (`dict->offset_f`); a stored field (`stored_types`) converted by `quest_convert`; through a view map (`quest_view_record_*`) | `recordSlot`, `recordField` | build; runtime for conversions and view maps |
| Records made: box and payload allocated together, the header's descriptor, the offset table static or `quest_record_dict(view, layout)` | `makeRecord` | build, data |
| Options made: allocated, the tag stored (an ordinal checked by `quest_check_option_ordinal_at` and mapped through a table), the payload stored; payloads read into a new tuple, with the ordinal first for `#n` | `makeOption`, `payload`, `optionCaseTuple` | build |
| Variants: tag tests, the payload's check (`quest_raise_variant_error_at`), tags translated through a view map (`index[tag]`) or a tag map | `payload`, `tagOf`, `convert` | build |
| Conversion plans: `box`, `unbox`, `cast`, `unproxy`, `slot_box`, `slot_unbox`, and `variant_tags` inline; `record_view`, `view`, and `runtime` through the runtime; `copy` as a new tuple; `adapt` as a thunk | `convert` | build; `adapt` by the shared pass (§7.5) |
| Thunks: adapters (`qa_adapt`), type applications' thunks (`qa_type_app`) and environments, closures of externals (`qx_`), each made once for its key | `adapter`, `typeAppThunk`, `externalClosure` | pass (§7.5) |
| Calls: a known closure directly (`f(env or NULL, ...)`), an external directly, an imported module's member through its exported function `qv_<mod>_<member>`, others through `fn` and `env`; descriptors after the environment; an `Ok` result is `void`, an `Ok` argument `QVal` 0 | `callClosure`, `callOp` | build, abi |
| Closures: a static closure `{ f, NULL }` for every function; otherwise environment and closure allocated apart; a `let rec`'s captures of its own variables filled in afterwards | `makeClosure`, `sLetRec` | build, data |
| Descriptor operands: variables, static descriptors (symbols), templates instantiated by `quest_instantiate_descriptor(t, n, array)` with the array on the stack; view maps fetched in the prologue (`quest_view_map`) | `descriptor`, `function` | build, data; the array a stack slot |
| Auto values and `inspect`: `quest_auto_new`, `quest_is_subtype`, `quest_layout_equivalent`, conversions arm by arm | `makeAuto`, `inspectAuto` | build, runtime |
| Exceptions: `quest_alloc_exception(name)` at each evaluation; the handler record and catch array on the C stack, popped on every way out (`leaveTo`); the handler's variable a copy of `QExceptionState` (32 bytes); `quest_raise_at(exc, payload, site)`, `quest_reraise(state)` (by value, so through memory) | `sTry`, `sRaise`, `emitCatches` | build (§3.6), runtime, abi |
| Raise sites: a C string `"file:line:col"` for each, or `NULL` | `site` | data |
| Mutable variables: locals, `volatile` when assigned in a `try` body; `var` and `out` parameters as pointers to their locations; boxed mutable variables; a cell for `var(e)`, a C local whose address is passed | `assign`, `atom`, `opAddrVar`, `opAddrCell`, `volatileVars` | build: stack slots (§3.2, §3.6) |
| Echo: `quest_print_value`, `quest_print_typed` | `echo` | runtime |

### 7.3. The Unit

| Decision | In the C backend | SSA backends |
|---|---|---|
| `main`: `quest_gc_init`, `quest_builtins_init(argc, argv)`, `qr_register_dicts`, the imports' initializers, the modules', the top level, `return 0` | `printUnit` | build |
| A module's initializer: its guard; its abstract types registered (`quest_register_abstract_type`); for an exported module, `qr_register_dicts` and the imports' initializers; its body; its record stored in the module's global | `moduleInit` | build |
| `qr_register_dicts`: the function table and the registered offset tables | `printUnit` | build, data |
| The function table `qr_funcs` | `funcTableEntries` | data |
| Exported functions `qv_<mod>_<member>` (without an environment), the module record, and the initializer: what the interface header declares and C importers use | `exportedFunctions`, `headers` | build, abi; names from `symbols` |
| Globals: a unit's top-level variables as `static` C globals; module records as `QRecordVal` globals | `globalDeclarations` | data |
| Allocation: `quest_alloc` is `GC_MALLOC` (zeroed), or `calloc` with `--nogc`; `quest_alloc_atomic` is not zeroed with `--nogc` | `quest_runtime.h` (inline) | runtime, out of line, so that the mode is the runtime's |

### 7.4. What clang Does

- **The calling convention** (§3.3), with the composites: `QRecordVal` and `QVariantVal` in two `x` registers, and
  `QExceptionState` (32 bytes) through memory, as any composite over 16 bytes.
- **Frames and unwind information** (§3.10): clang keeps frame pointers on Darwin and emits compact unwind.
- **`setjmp`** (§3.6).
- **Optimization:** the inline helpers inlined, registers allocated, and more, none of which the SSA backends must
  match.

### 7.5. What Step 2 Shares

1. **Thunks as IR functions.** A pass after describe makes the adapters, type applications' thunks, and closures of
   externals into IR functions and closures. The IR can express them: a thunk's closure captures the original closure
   and, for a type application, takes the descriptors (`closure f {orig} [τ...]`), and the conversions in its body are
   `convert` operations. The C printer then prints them as it prints any function, and loses `adapter`,
   `typeAppThunk`, `externalClosure`, and `finishThunkCall`; the SSA backends get them for nothing. Since the pass
   runs after describe, it makes described IR itself (a thunk's descriptor parameters and its plans' descriptor
   operands, which the represent and describe passes now leave on the plans), and the verifier checks it as it checks
   the describe pass's output.
2. **A description of static data** (decided 2026-10-29: now, rather than C for native units' data until the JIT
   needs it). A shared module describes each descriptor, offset table, and tag map as structured data, its runtime
   struct's fields (integers, booleans, strings, and references to other data and to functions), as
   `declarations.emitTypeDescriptors` computes them now, and lists the function types whose adapters and invokers the
   unit supplies, with their signatures. Each value carries both its C spelling (`sizeof`, `offsetof`, a descriptor's
   expression) and what the SSA backends need (bytes, offsets, a symbol and an index). The C printer prints the
   description, its C unchanged; the SSA backends lay it out by the runtime structs' layouts (step 3) and generate
   the adapters' and invokers' code in the SSA. In order: the descriptor forms and record naming move from
   `codegen/c/types` into a shared module; the description is built there; then `declarations` prints it.
3. **Slot conversions as data.** `layout` says which of a few kinds of conversion takes a shape's value to its slot's
   word and back, and `codegen/c/types` spells each kind in C.
4. **Out-of-line runtime helpers.** The header's `static inline` helpers are declared `Q_INLINE`, which is
   `static inline` everywhere but one runtime file, which defines it as nothing before including the header and so
   gives the runtime an external definition of each, under its own name. Every other translation unit keeps its own
   inline copies, as C allows.

Everything else in §7.2 and §7.3 is the SSA's construction. An operation's access sequence is short, and its C text
does not translate into SSA, so sharing it would need an intermediate form that neither backend wants. The mixed
builds (§4) keep the two implementations agreeing.

## 8. Decided From the Inventory

1. **`Int` arithmetic wraps** (decided 2026-10-29), in two's complement, in every implementation. The three disagree
   today (tried on `9223372036854775807 + 1` and `INT64_MIN / ~1`): the bootstrap's interpreter gives
   `9223372036854775808`, outside `Int`'s range, from Python's unbounded integers, and compiled code and the
   self-hosted interpreter (which is compiled code) wrap, to `-9223372036854775808`, by C's undefined behavior.
   `INT64_MIN % ~1` is 0 in all three. Step 2 makes them agree: `-fwrapv` for C, `INT64_MIN / -1` defined as
   `INT64_MIN` (and `% -1` as 0) in the runtime's helpers, results reduced to 64 bits in the bootstrap's interpreter,
   and run tests of each case. arm64's `add`, `sub`, `mul`, `sdiv`, and `msub` then do what Quest does.

## 9. What the Oracle Found

Running every unit through `ssac` (step 5) found where the SSA's builder did not do what the C printer does, each
fixed in the builder, with what the test that found it was:

- A static descriptor operand of an echoed type is its echo descriptor (`echoDescriptorForm`), as the C printer's
  `staticDescriptorOf` has it.
- Only a module file's initializer (an exported module's) calls `qr_register_dicts` and its imports' initializers; a
  module file has no `main`.
- External values the runtime spells as expressions: an object's address (`(&quest_exc_writer_error)`), a Real
  without a literal (`QUEST_REAL_INFINITY`, by its bits, `runtimeLayout.realBits`), and a runtime variable read as a
  value (`quest_system_args`, `runtimeLayout.variables`).
- Static data cannot hold a thread-local's address, which is not a constant; `ssac` refuses such data.

## 10. Hazards to Address

Problems the plan does not yet handle, each to be addressed (or shown not to arise) before the plan is complete (§5),
with what would address it.

1. **Branch ranges.** `clang -c`'s assembler does not relax arm64 branches whose targets are out of range; it reports
   a fixup error. `b.cond`, `cbz`, and `cbnz`, which step 6's code uses, reach 1 MB either way, and `tbz` and `tbnz`,
   which instruction selection (§3.5) would add, only 32 KB, so a large function, above all with the trivial
   allocator's loads and stores (§3.8), can exceed them. *Solution:* the emitter relaxes branches itself: once
   instruction sizes are known, an out-of-range conditional branch becomes the inverted condition around an
   unconditional `b` (128 MB), repeated until no branch changes. Jump tables for `switch` hold offsets wide enough for
   the function. *Addressed* (2026-10-29): `relaxBranches` relaxes each function's conditional branches whose
   targets are more than 260,000 instructions away, round after round (the questlang test `arm64_relax`, with a reach
   of a few instructions); a `try`'s `adr`, which also reaches 1 MB, takes the address of a branch beside it to the
   handler. Step 6 makes no jump tables yet; they will need the same care.
2. **Large frames and the guard page.** The trivial allocator gives every virtual register a slot, so a large
   function has a large frame, and a frame larger than the stack's guard region can step over it, so that a stack
   overflow writes into whatever memory lies beyond rather than faulting in the guard, and exceptions.md §6's handler
   may never run. Step 6's prologue moves `sp` by the whole frame at once, however large. *Solution:* as clang does,
   a prologue whose frame exceeds a page calls `___chkstk_darwin` (or probes each page itself) before moving `sp`; a
   test recurses through a function with a large frame and checks that the stack overflow is reported.
   *Addressed* (2026-10-29): a frame of more than 4 KB is moved through `___chkstk_darwin` (`x9` holding its size in
   bytes), as clang does; `tests/self-hosted/backends.py` recurses without end through a function with a 24 KB
   frame and checks that each backend reports `stack.overflow`.
3. **Apple's stack arguments.** Darwin's arm64 ABI places arguments past the registers at their natural size and
   alignment, not in 8-byte slots as standard AAPCS64 does. Step 6 handles the case that arises today, a C `bool` or
   `char` taking one byte (`narrow`, ssa.md §2.2), but any other C type narrower than a word that a signature gains
   (a 4-byte `int`, say) would be packed the same way. *Solution:* the ABI lowering places stack arguments by their
   C types' sizes and alignments rather than by a list of narrow ones, and §4's tests of calls between C and native
   code cover narrow types, `double`s, and 16-byte composites past the eighth argument, in both directions.
4. **`Char` is C's `char`** (§3.9, §7.1), whose signedness is the platform's: signed on Darwin arm64, unsigned on
   Linux arm64. A `Char` above 127 is then a negative integer on one and not on the other, and the representation
   leaks into conversions, comparisons, and slots. *Solution (preferred):* `Char` is `uint8_t` everywhere, in the
   runtime's types, `layout.representation`, both compilers' C printers, the SSA (a `Char` loaded, received, or
   returned is zero-extended, as `Bool` is), and both interpreters, which must agree; an ABI bump, with run tests of
   characters above 127. Doing it while there is one platform keeps the change small.
5. **Pointers through integers.** §3.13 keeps `ptr` apart from `int` so that a precise or moving collector stays
   possible, but `QVal` words and proxies already cross between them (`intToPtr`, `ptrToInt`, ssa.md §1), so the
   distinction alone does not give stack maps. *Solution:* state the requirement precisely: the register allocator
   carries each virtual register's `ptr` or `int` class through allocation, into spill slots, and the frame records
   which slots hold pointers, so that stack maps at calls could be emitted later; and a word whose pointer-ness is
   dynamic (a `QVal`) is described as such, for a precise collector to resolve by descriptor.
