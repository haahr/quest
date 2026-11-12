# The Native arm64 Backend

A backend in the self-hosted compiler that writes arm64 machine code for Darwin, beside the C backend, from the SSA
([ssa.md](ssa.md)). Its object files link with the C backend's, unit by unit, and with the runtime, which stays in
C. It is written in Quest, in `questlang/`, and the bootstrap does not get it ([testing.md](testing.md) §2.8: the
bootstrap gets the language's changes, not the self-hosted compiler's backends). The JIT ([jit.md](jit.md)) uses the
same pipeline up to machine instructions.

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
- **Debug information:** DWARF line tables (`.file` and `.loc` directives, from the IR's source offsets, §3.16); no
  variable locations.
- **The default backend is arm64,** for programs, for building the compiler, and for releases, since 2026-11-12:
  the user's decision from the measurements of [benchmarks.md](benchmarks.md) §21, once a release through arm64 and
  the stage caches were checked (§21.4), on the condition that the arm64-built compiler stay within 25 percent of the
  C-built one. It had been C, from §5 (2026-10-30). `--backend c` compiles through C; `codegen_c` and `compile
  --emit-c` mean C unless a backend is given, as `codegen_arm64` means arm64. The bootstrap, which has no arm64
  backend, compiles through C. No such decision is final: the question is reopened whenever benchmarks.md records a
  significant change.
- **One SSA-based C backend in the end** (§5): the tree-walking C printer is a second, hand-written
  implementation of every operation's access sequence (§3.1), kept in agreement with the SSA's builder only by tests.
  Once the SSA's code is good enough, `ssac` replaces it as the self-hosted compiler's C backend, so that each
  operation is lowered once. The bootstrap's C printer stays, since the bootstrap gets no SSA.

## 2. Pipeline

```
described IR (ir.md §8.4)
  ├─→ C printer → C → clang                                              (unchanged)
  └─→ build SSA          questlang/ssa        CFG, block arguments, mutable locals promoted, try regions;
        │                                     machine scalar types; loads and stores at byte offsets
        ├─→ SSA-to-C printer  questlang/codegen/c/ssac  (the oracle, §3.14) → C → clang
        ▼
      lower to arm64     questlang/codegen/arm64   ABI (Apple AAPCS64), instruction selection: machine SSA over
        │                                          virtual registers, with fixed-register constraints
        ▼
      allocate registers questlang/codegen/machine/regalloc  target-parameterized; out of SSA (parallel copies)
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
  arithmetic, which the shared `layout` module computes (§3.3). Closure environments are private to their unit,
  so the SSA backends need not lay them out as C does.
- **Shared** (§7.5): thunks are IR functions made by a pass, so that every backend gets them; static data
  (descriptors, offset tables, tag maps) has a shared description; slot conversions are data in `layout`; and the
  runtime's inline helpers have external definitions too.
- **Everything else is the SSA's construction:** each operation's access sequence (proxies, offset tables, view maps,
  option payloads, checks), `try`, and the unit's structure. It is a second implementation of what the C printer
  prints, kept in agreement by the mixed builds (§4).

### 3.2. The SSA

`questlang/ssa`, described in [ssa.md](ssa.md): target-independent and low-level. Its values are machine scalars of
four types (`int`, `ptr`, `real`, and `val`, a `QVal` word), a 16-byte value split into two when the SSA is built, so
that no later stage sees aggregates; its instructions reach memory by byte offsets and call by symbol or address,
each call with its C signature; mutable variables are built as stack slots, loaded and stored, and promoted to values
by a later pass ([ssa.md](ssa.md) §4.1). The IR is structured, so its statements become blocks and edges directly:
`if`, `switch`, `loop`, `break`, `continue`, and `join` become blocks and edges, and a join point is a block whose
parameters are its own. The verifier runs after the builder and after every pass when `QUEST_CHECK_IR=1`, as the
IR's does. Its textual form is dumped by `--stop-after ssa`, with a golden for every run test, the self-hosted
compiler's own (testing.md §2.8), since it is target-independent and changes only when the lowering does; nothing
after it has goldens, since machine code changes with almost any backend change.

### 3.3. Layout and the ABI

- **Layout.** The arm64 backend computes every offset and size that clang computes for the C backend's structs, and
  the C asserts each, so that any C compilation checks the arm64 backend's arithmetic:
  - aggregates' structs (tuples, records, options and their cases' payloads): `repr/layout` (`tupleBytes`,
    `recordFieldOffset`, `optionBytes`, `slotsBytes`), asserted after each struct the C defines, in units and in
    interface headers (`static_assert(... == N, layout_<struct>_...)`);
  - the unit's static data (descriptors and their payloads, offset tables): `repr/staticdata`, asserted after
    each;
  - the runtime's own structs that generated code touches (`QClosure`, `QArray`, `QString`, `QExceptionState`,
    `QViewMap`, `QLayout`, every descriptor struct, ...) and its constants (`QTypeKind`'s, `Q_CATCH_ALL`, ...):
    `repr/runtimeLayout`, a table that the questlang test `codegen_runtime_layout` prints as C assertions and
    `tests/python/test_runtime_layout.py` compiles against `quest_runtime.h`.

  Closure environments are private to their unit and need no assertions (§7.1).
- **Calls** follow Apple's AAPCS64, as clang does for the same C declarations: integer and pointer arguments in
  `x0`–`x7`, `double`s in `d0`–`d7`, the rest on the stack; a 16-byte composite that is not all `double`s in two `x`
  registers, even if it holds a `double`; results in `x0`/`x1` or `d0`; the caller extends arguments narrower than 32
  bits. The closure calling convention of [runtime-design.md](runtime-design.md) §4.1 and the signatures of
  [c-representation.md](c-representation.md) §6.2 are the contract.
- **Narrow arguments.** Darwin places arguments past the registers at their natural size and alignment, not in 8-byte
  slots as standard AAPCS64 does, so a C `bool` or `QChar` on the stack takes a byte. The SSA marks such parameters and
  results (`narrow`, [ssa.md](ssa.md) §2.2), `placeArguments` places each stack argument at its size and alignment (a
  16-byte composite as two words), and a function extends its own narrow parameters on entry, since a C caller leaves
  their upper bits unspecified. No other C type narrower than a word occurs: Quest's own types are words, `bool`,
  `QChar`, or 16-byte composites, and `tests/python/test_runtime_signatures.py` fails if any function the runtime
  declares takes or returns another (`quest_system_init`'s and `quest_builtins_init`'s `int argc` alone, the first
  argument, in a register). `modules/wide_calls` calls across units with arguments past the registers of each kind,
  which the backends' mixed modes compile natively on one side and through C on the other.
- **Symbols the unit does not define** are reached through the GOT, and a thread-local through its descriptor's
  accessor, so that one spelling serves the runtime, other units, and the system's libraries.
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

The data is the SSA's, not the C declarations': a unit's data is words, text, and zeros ([ssa.md](ssa.md) §5), its
descriptors laid out by `ssa/statics` from `repr/staticdata`'s descriptions (§7.5), and its function types'
adapters, thunks, and invokers, its exported functions, its function table, and `qr_register_dicts` are SSA
functions, so that `ssac` and arm64 emit the same data and code. Static data cannot hold a thread-local's address,
which is not a constant.

### 3.5. Instruction selection

Greedy pattern matching over single-use values within a block, producing machine SSA: arm64 instructions over
virtual registers, with fixed-register constraints at calls, returns, and parameters. arm64 is three-address with
few constraints, so the patterns are few:

- address modes: base plus immediate offset, base plus scaled index;
- constants: `movz`/`movk` sequences, logical immediates, `adrp` + `add` for symbols;
- shifted and extended operands, `madd`/`msub`;
- comparison fused into branches: `cbz`/`cbnz`, `tbz`/`tbnz`, `cmp` + `b.cond`; `csel`/`cset` for values;
- `ldp`/`stp` for the halves of 16-byte values and for saving registers.

As built (`codegen/arm64/select`, over `minst`'s instructions, §3.17): immediates
for `add`, `sub`, and `cmp`, a comparison with a small negative constant as `cmn` of its negation; a constant in the
fewest instructions (`printer.expansion`, which the assembler's text and the JIT's encoder share): one `mov` when
`movz`, `movn`, or `orr` of a logical immediate makes it, else from whichever of 0 and ~0 leaves fewer halfwords to
fill, a `movz` or `movn` and a `movk` for each other halfword (−1 and −2 had been four instructions each, 1,117 such
sequences in the driver); `and`, `orr`, and `eor` with logical (bitmask) immediates; a comparison fused into its
branch; an `and` of one bit, seen through conversions between words, or a value compared with 0, as `tbz`/`tbnz` or
`cbz`/`cbnz`, and a switch's case 0 as `cbz`; a switch of at least eight dense cases (their range at most twice their
number) as a jump table (§3.11), one of more than four others as a search, a comparison with the middle case
branching to it when equal and, by `b.gt`, to a block of its own that searches the greater ones, the lesser searched
on, down to runs of up to four compared in turn, so that 60 sparse cases take about six comparisons; an `and` of two
integer comparisons as `cmp`, `ccmp`, and `b.cond`; a
load or store at the start of a symbol the unit defines as `adrp` and the access at the symbol's page offset, without
the `add`; one at a `ptrAdd` of a base and an index, or of an index times the access's width (an array's element),
made for it alone, at the base and the index register, shifted (`ldr x0, [x1, x2, lsl #3]`), without the `mul` or
the `add`; and no extension of a narrow result (ssa.md §2.2) of a call of a function in the unit that returns its
narrow results extended, which is every one but those that tail-call, for such a result, a function that may not. When
the code is emitted, blocks that only jump are passed over, a jump to the next block falls through, and a conditional
branch to the next block is inverted before the block's last jump. The blocks are laid out in chains: from the entry,
each is followed by its best successor not yet placed, one not cold, then in a deeper loop, then making no call (a
proxy's slow path is not followed into), then first in the builder's order; the blocks from which every path raises
come last (arm64-performance-review.md §3.3). Last, loads (or stores) of 8 bytes off one base, at offsets 8 apart,
are merged into an `ldp` (`stp`): a load's partner moved up to it, a store moved down to its partner, across up to 16
instructions that touch only registers, and none that branch or store (nor, for a store, load) or that write the
base or the moved access's register (arm64-performance-review.md §3.5). Two stores are left apart when the code
that runs next (up to 12 instructions on, following jumps, until a call or a write of the base) loads one of their two
words alone, with no load of the other within four instructions to make a pair of: a lone load does not forward from
half of a pair's store, which cost psdes-random a fifth of its time once a tuple's two stores had one base
(benchmarks.md §18.2).

### 3.6. Exceptions

**In C** a `try` pushes a `QExceptionHandler` holding a `jmp_buf` (`runtime/quest_runtime.h`) onto a thread-local
chain and calls `_setjmp`; a raise walks the chain (exceptions.md §5.1) and `_longjmp`s. `_setjmp` stores all the
callee-saved registers (`x19`–`x28`, `fp`, `lr`, `sp`, `d8`–`d15`) through a dyld stub: no system call, but
flat-array, with a `try` in its innermost loop, spent 69 percent of its time there ([benchmarks.md](benchmarks.md)
§3.5).

**C cannot do much better.** clang does not provide `__builtin_setjmp`, which saves only the frame and stack pointers
and the resume address, on arm64. An assembly routine that returns twice is no better than `_setjmp`: clang keeps
values in callee-saved registers across any call, so the routine must save them all. Only inline assembly can let
clang save just the registers live across the `try`: an `asm goto` that stores `sp`, `fp`, and the handler label's
address, names the label as a target, and clobbers every callee-saved register. Whether clang keeps the label's code
and the frame as the handler expects is not something it promises, so that is an experiment (§6). What C can do
reliably is enter fewer handlers (§6).

**Native code does.** A native function controls its own registers, so its handler needs only where to resume:

- **One handler record, two kinds.** The record's common fields (`prev`, `catches`, `n_catches`) come first, then
  `resume`, `sp`, and `fp`, then the `jmp_buf`. A C handler's `resume` is `NULL` (both C printers and the SSA's builder
  set it); a native `try` stores its handler block's address and its frame's `sp` and `fp` instead of calling
  `_setjmp`. A raise walks the chain as before and resumes a C handler with `_longjmp`, and a native one with a few
  instructions of inline assembly in the runtime (`quest_resume_native`) that set `sp` and `fp` and branch.
- **At a native handler's entry every register is dead.** The function's frame is intact, and its prologue's saved
  registers are still in it, so its epilogue restores its caller's registers as usual. Values the handler uses come
  from the frame, or are reloaded by the jump from the block a raise enters (§3.8).
- **A function that enters a `try` saves every callee-saved register** (`x19`–`x28`, `d8`–`d15`) on entry and
  restores them at each return, with their unwind information: the frames a raise skips may have left anything in
  them, and the function's caller expects its own. That is one save per call, where `_setjmp` was one per `try`
  entered, so a `try` in a loop costs only its record's stores. `tests/self-hosted/backends` checks it: a C loop keeps
  its state in such registers across calls of a native closure that catches what C code raises.
- **SSA and `try`.** As the C printer marks `volatile` the mutable variables assigned in a `try` body and live in its
  handler or after the `try` (ir.md §6.4), the SSA keeps a function's mutable variables in stack slots when it enters
  a `try` ([ssa.md](ssa.md) §4.1). Every other value the handler uses dominates the `try`'s entry, so the handler
  block needs no parameters from the points that raise.
- **The chain stays thread-local** (`_Thread_local`, though Quest has no threads). On Darwin, native code gets a
  thread-local's address from its descriptor's accessor (`_tlv_get_addr`, a call; the SSA's `threadLocal`), taken at
  each use. Raises go through the runtime.
- **Tracebacks** need no change to the runtime: native functions are in their units' function tables, have frame
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

**As built.** `ssa/passes/tailCalls` marks them as the builder finishes a unit, so the SSA's dumps show them (`tail` before
the call), and both native backends compile them:

- A call is in tail position when its results, or the extension of its byte result (a `Bool` or `Char`, which every
  caller extends again), are returned, directly or through blocks that only pass them on to a `return`.
- A function from which a stack slot's address may escape (stored, passed to a call, or returned, through
  arithmetic, copies, and block parameters) has no tail calls. That covers the first two exceptions above at once,
  since a `try`'s record is such a slot, and so is a `var` argument's cell and a composite passed through memory. It
  is coarser than they ask: a function with any such slot loses all its tail calls.
- arm64 compiles a call of the function itself as a jump to its first block, whatever its arguments; one of another
  function whose arguments all go in registers as the frame popped and `b` or `br`; and the rest as a call and a
  return, a coarser rule than the comparison with the caller's incoming argument area. `ssac` prints `return
  f(...);` and leaves the jump to clang.
- `language/tail_calls` covers each case in every phase, a hundred deep; `self-hosted/backends` runs self, mutual,
  and closure tail recursions ten million deep with arm64, in the default 8 MB stack.

### 3.8. Register allocation

`questlang/codegen/machine/regalloc`, parameterized by a target description (register classes, allocatable and fixed
registers, what a call clobbers), so that it can be tested on its own.

It is linear scan on SSA with interval splitting (Wimmer and Mössenböck, *Optimized Interval Splitting in a Linear
Scan Register Allocator*, VEE 2005), on a machine function's virtual registers (§3.17): spilling, rematerialization
of constants, and leaving SSA by parallel copies on each edge, sequenced so that nothing is overwritten before it is
read. `regalloc_scan` (a questlang test) shows its choices on small functions with a target of a few registers.

Registers: `x18` is never used; `x16`/`x17` are scratch only within a sequence (the linker's veneers use them);
`x29` is always the frame pointer; `x19`–`x28` and `d8`–`d15` are callee-saved (the low 64 bits of `d8`–`d15`,
which is all a `double` needs). A pointer is never held only in a floating-point register (§3.13).

**Intervals.** A value's interval is the ranges where it is live, with holes, so another value can use its register
in a hole. Intervals are taken in order of their starts:

- **A free register.** An interval takes a register free for all of it, a caller-saved one first. If none is, it
  takes the one free longest and the rest is split off, as long as some register is free where it starts.
- **None free.** It takes the register whose holders are next used furthest away, splitting them where it starts,
  unless its own next use is further. In that case it is spilled until that use, from which the rest is allocated
  again.
- **Calls and handlers.** A caller-saved register is unavailable from just after a call the interval is live
  across. Every register is unavailable at the start of a `try`'s handler that the interval covers.
- **Costs** (2026-11-01, arm64-performance-review.md §3.1, item 4a). Spilling an interval costs the load at its
  next use, so that use's block's frequency: 1000, times 8 for each loop the block is in (up to four, from
  `cfg.loopDepths` over the machine function), or 1 for a cold block (from which every path raises, which the
  target tells the allocator). The choice above takes the register whose holders cost least, and spills the
  interval instead if it costs less; the nearest next use decides only at equal costs, as in code without loops.
  A register is also taken, where one is free for only part of the interval, if its holders cost less than the
  part the free one would spill: so a value used in a loop and live across a call in it gets a callee-saved
  register held by one used next only after the loop. That one is then in memory from the loop's body, and is
  loaded again on the back edge if it is in its register at the header.

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

**On machine functions.** The allocator works on a machine
function's virtual registers (`codegen/machine/machine`), which `codegen/arm64/select` selects from the SSA, rather than on
the SSA's values, and it reads no register's name: a target (`codegen/machine/target`) gives it register numbers.

- **Fixed registers.** The calling convention is moves to and from physical registers: arguments before a call,
  its results after, the parameters at the entry, and returned values before a return. A register is unavailable
  where such an operand fixes it, from the instruction that writes it to the last that reads it, so `x0`–`x8` and
  `d0`–`d7` are allocatable too (after `x12`–`x15` and `d16`–`d29`); the scratch registers are `x9`–`x11`, `x16`,
  `x17`, `d30`, and `d31`.
- **Hints.** A move's two registers, and a jump's argument and its target's parameter, are hints: an interval
  takes the register of what it is hinted to when that one is free for all of it, so the move costs nothing.
- **Rewriting.** `regalloc.rewrite` puts the registers allocated in the instructions: an operand in memory is
  loaded into a scratch register (`x9`, `x10`, `x11`, or `d30`, `d31`), a result in memory is written to one and
  stored, and the moves between pieces and on edges are made in parallel, as above. An edge's moves are made
  before its jump, or at the start of a branch's target, which selection makes a block of its own.
- **Rematerialization** is of an instruction that reads no virtual register: a constant, a symbol's address, or an
  address in the frame.
- **The frame** is the outgoing arguments' area, the stack slots, then a slot for each register stored in memory.
- **Dead values' slots are left as they are** (2026-11-05; they were cleared from 2026-11-01,
  arm64-performance-review.md §3.2). While the collector scanned frames whole, a slot that still held a dead value's
  pointer kept what it pointed to alive (in mlyacc, whose whole program is `main`, hundreds of them did), so
  `rewrite` stored zero to a slot where its value died, if a call might follow and the target's `Lowering` said the
  value might be a pointer. A collection now scans, of a frame, the slots its call's map says are live (§3.13), so a
  dead pointer keeps nothing, and arm64's `Lowering` asks for no clears; `rewrite` still makes them for a target that
  asks (the allocator's test target does). For such a target, a value that dies at a branch, on the path that falls
  through, is cleared only if a call may follow on that path, not on the branch's target's, and a cold block's call
  is not one that may follow (2026-11-05, [benchmarks.md](benchmarks.md) §20.1): under frames scanned whole, a failed
  bounds check's path cleared every pointer live into the passing one before jumping to the raise, 1,541 clears in
  ratio-regions' `preflowPush` rather than 33. Since arm64 asks for none, this changes none of its code;
  `regalloc_scan` case 14 shows it.
- **A value never read is never stored** (2026-11-01). Its piece may be in memory, a loop header's parameter that
  only the back edge defines when the header has more parameters than registers, say; but nothing would read its slot,
  and since it dies at no read, nothing would clear it, so the back edge stored a dead pointer each time round, as in
  mlyacc's `main`.
- **Spill slots shared by type** (2026-11-01, arm64-performance-review.md §3.2, item 3b). `regalloc.shareSlots`
  gives values of one kind (for arm64, one SSA type: `int`, `ptr`, `val`, or `real`) one slot where their lifetimes,
  from first position to last, do not overlap, so a frame holds the most values in memory at once rather than every
  one ever there. A lifetime is stretched over the two places `rewrite` writes a slot outside it: a parameter's on
  each jump into its block, and a clear after its value dies, where the target asks for clears. A function that
  enters a `try` keeps a slot for each value: its handler reloads from slots what liveness in the try's body does
  not see it use.
- **A block a raise enters,** beside its `try`, which jumps to the handler, has every register dead at its start;
  the handler may then have what it uses in registers, loaded by that jump's moves.

### 3.9. Primitive semantics

Native code must do what the C helpers do, including the cases where arm64 and C differ:

- `Int` arithmetic wraps (§8): `+`, `-`, and `*` overflow, undefined in C, gets `-fwrapv`.
- `sdiv` does not trap on zero, and gives `INT64_MIN` for `INT64_MIN / -1`, which is undefined in C (`quest_int_div_at`
  checks only for zero).
- Shift counts are taken modulo 64 by arm64 and are undefined in C past 63; the word helpers handle the counts.
- `fcvtzs` saturates; C's conversion of an out-of-range `double` is undefined.
- `Real` arithmetic raises `real.error` on a NaN result, and division on a zero divisor (`quest_real_result_at`).
- `Char` is a `uint8_t` (`QChar`) on every platform, not C's `char`, whose signedness is the platform's (signed on
  Darwin arm64, unsigned on Linux arm64), so a `Char` widened to a slot or a register is zero-extended everywhere. A C
  character literal above 127 is cast to `QChar` (a C character literal is an `int` of the platform's `char`, so
  `'\310'` alone is -56 on Darwin); the SSA's `Char` constants are 0 to 255 and its loads and received values
  zero-extended; the runtime and both interpreters read a `Char` as unsigned. `stdlib/high_chars` runs characters
  above 127 through constants, strings, slots, generic words, a hash map, parameters, results, and a dynamic round
  trip, in every phase and backend.

The inventory (§7.2) lists every helper, and the arm64 tests (§4) cover each edge case against the C backend.

### 3.10. Frames, symbols, and unwind information

Every function that calls has a frame record (`stp x29, x30`) and sets `x29`, which Darwin requires and the
traceback walk uses. A function that needs none has none: one that saves no callee-saved register, has no frame,
calls nothing (a tail call is a branch), and has no instruction using `x29`, `x30`, or `sp` (as an argument passed on
the stack would) keeps them as its caller left them, its unwind information a frameless function's, so that a
backtrace from it reads its return address in `x30` (`tests/self-hosted/line_tables.py` stops in one). Leaves, loops
that call nothing, and the trampolines (an export's or an adapter's branch on to its function) are such
functions; none is on the stack when a collection walks it, since none calls. The prologue and epilogue save the callee-saved registers the function uses, with `.cfi` directives from which
the assembler and linker make compact unwind entries. The prologue stores the lowest of the pairs it saves
first, moving `sp` once (`stp x28, x27, [sp, #-96]!`), then the others and the frame record above it, as clang does.
Each pair's odd register is above its even one, and the `.cfi_offset` directives name `x19` before `x20` and each pair
in order down from the frame record: the places and order Darwin's compact unwind encoding needs. Stored the other way,
every function that saved a pair had DWARF CFI instead, which libunwind interprets at each frame a raise walks
(found 2026-11-01, arm64-performance-review.md §3.6; `tests/python/test_arm64.py` checks every function's entry).
A compact unwind entry assumes the whole prologue has run, and the stack-overflow handler's backtrace reads it, so a
prologue that pushed the record and then each pair downward could fault on a pair just below a record that fit, and
the backtrace then read that pair from the guard page and crashed in the handler (found 2026-10-30, once in many
runs, once linear scan made frames small). Stored lowest first, the prologue faults on its first store or not at all.
Each function has a symbol (local unless exported), so that
`dladdr` attributes frames as exceptions.md §5.3 describes, and the unit emits `.subsections_via_symbols`. The
stack-overflow handler (exceptions.md §6) works unchanged.

**Large frames and the guard page.** A frame larger than the stack's guard region could step over it, so that a stack
overflow wrote beyond the stack rather than faulting in the guard, and exceptions.md §6's handler never ran. As clang
does, a prologue whose frame is more than 4 KB calls `___chkstk_darwin` (`x9` holding its size in bytes), which
probes each page, before moving `sp`. `tests/self-hosted/backends.py` recurses without end through a function with a
24 KB frame (its values kept live across the recursive call, where they are spilled) and checks that each backend
reports `stack.overflow`.

### 3.11. Emission

**Assembly text first,** assembled by `clang -c`: the assembler does instruction encoding, relocations, Mach-O, and
unwind tables, the text is readable when debugging, and assembling it is a check in itself. Darwin's spellings:
`_` before every C symbol, `L` before local labels, `sym@PAGE`/`sym@PAGEOFF` for addresses, `@GOTPAGE`/`@GOTPAGEOFF`
for data in dylibs, `@TLVPPAGE`/`@TLVPPAGEOFF` for thread-locals' descriptors, `bl _f` for any call (the linker
adds stubs). The linker signs arm64 executables ad hoc. All of
this is in one module, so that another object format would replace only it.

The instructions are data (§3.17) that both the printer and an in-memory encoder use: `codegen/arm64/encode`, the
JIT's ([jit.md](jit.md) §3.5), turns them into 32-bit words with relocations, checked byte for byte against the
assembler by `self-hosted/encoder`.

**Branch ranges.** `clang -c`'s assembler does not relax arm64 branches whose targets are out of range; it reports a
fixup error. `b.cond`, `cbz`, `cbnz`, and `adr` reach 1 MB either way, and `tbz` and `tbnz` only 32 KB. So
`peephole.relaxBranches`, once instruction sizes are known, turns a conditional branch whose target is out of reach
into the inverse branch around an unconditional `b` (128 MB), round after round until none changes, a
pseudo-instruction counted as the instructions it expands to, and a jump table as its entries, a word each; a `try`'s
`adr` takes the address of a branch beside it to the handler. The questlang test `arm64_relax` checks it with a reach
of a few instructions.

**Jump tables,** in the assembler's code and the JIT's alike. A switch of dense cases (§3.5) subtracts its least case,
checks the result against the range's size (`cmp`, `b.hs` to the default), and branches through a table of 32-bit
offsets placed just after the `br`: `adr x, Ltable`, `ldrsw y, [x, i, lsl #2]`, `add x, x, y`, `br x`. The table is
three pseudo-instructions of `minst`: `opJumpTable`, which the printer writes as `.data_region jt32` and the table's
label (so that otool and lldb read its words as data, as clang's tables are marked); an `opJumpEntry` for each value
in the range, `.long Ltarget-Ltable` (a gap's target the default); and `opJumpTableEnd`, `.end_data_region`. The JIT's
encoder writes each entry as the difference of the two labels' offsets, which it knows in its first pass. In the
machine function each entry is a branch to a block of its own, as every branch's target is (the register allocator
moves an edge's values at its start), which the emitter passes over when it only jumps; the end is the block's last
instruction, of the kind that leaves the function, but without the epilogue a return has, since the `br` has already
left. An entry's offset reaches any distance, and the `adr` reaches the table just after it.

### 3.12. Build integration and mixing units

- **Choosing the backend, per unit** (`codegen/choice`): `--backend c|ssac|arm64` for every unit (`c` by default),
  and a repeatable `--unit-backend UNIT=BACKEND` for one, a unit named as its manifest names it (a module by its
  canonical name, the program as `main`). Mixed builds are for tests and for finding a miscompile.
- **No fallback.** A unit using something the arm64 backend does not support is an error that names the construct,
  never compiled with C instead, so that a passing test means what it says.
- **Artifacts:** an arm64 unit writes `.mod.s` (or `.main.s`) where the C backend writes `.mod.c`, and its `.o` in
  the same place, assembled by `clang -c`. A unit's manifest records its backend (`"backend"`), and a unit compiled
  by another is stale. Interface headers are still written when a C unit needs them; the arm64 backend reads layouts
  from interfaces, not from headers.
- **Whole programs** (`--whole-program`, [build-process.md](build-process.md) §1.2) go through any backend, as one
  unit, so they take no `--unit-backend`. `driver/whole` lowers each imported module with a source as a module file is
  lowered and merges it into the program's unit, its references to merged modules made the unit's own, while the
  library's modules known only through interfaces and objects stay imported and are linked. A unit says whether it
  is a program's (`Unit.isProgram`). The merged files' offsets are numbered apart, so that a raise names its own file
  (`nodes.site`); a module imported by two names is merged once, by its name in lower case.
- **Building the compiler:** `QUEST_BACKEND=c|ssac|arm64` chooses the backend `./quest`'s stage 1 compiles stage 2
  with ([release-compiler.md](release-compiler.md) §2), each backend's stages in their own directory (the default's,
  arm64's, in `.build/quest-stages`, another's in `.build/quest-stages-<backend>/`), so that switching rebuilds
  neither.
  `run_tests.py --self-hosting --stage-backend ssac|arm64` checks that the compiler built by that backend writes the
  C-built compiler's artifacts for every unit (testing.md §4.1).

### 3.13. The collector

The collector scans a frame of native code by its **map** ([collector.md](collector.md) §3.3 and §8, step 5): the
words live across the call the frame is in, and no others. What that asks of the backend:

- every value live across a call is in a callee-saved register or in a slot of the frame, and the map says which:
  the allocator keeps no value in a caller-saved register across a call, a value with a piece in memory is stored to
  its slot where it is defined, and a rematerialized value has neither (it is a constant, or an address that is not
  the heap's);
- no pointer held only in a floating-point register;
- no derived pointer outside its object while the object is live only through it. A pointer into an object, or to
  its end (an empty array's elements), is found by the collector's start bits; nothing in the backend makes one
  further out, and optimizations must not.

**A call's map** gives each live value by its SSA type ([ssa.md](ssa.md) §1): a `ptr` is a pointer; a `val` is an
ambiguous word, since its descriptor, not its type, says whether it is a pointer; an `int` is an ambiguous word
too, since `ptrToInt` puts a pointer's bits in one, which may outlive the pointer (a proxy's test); a `real` is
left out. The collector marks a pointer's object and validates an ambiguous word first, so an integer that is not
an address costs a range test. A value with a slot is taken from the slot, which holds it wherever it is live, and
one without from its callee-saved register. `codegen.callMaps` computes the maps from the allocation by a backward
walk of each block from its live-out set; a live value found in any other register is an error of the allocator's,
which the walk reports rather than leave to a collection.

**The frame table** is what a unit gives the collector: for each function with mapped calls, the words from `sp` to
its frame record, the pairs of callee-saved registers its prologue saves (§3.10), the words at `sp` that nothing
describes (the outgoing arguments' area and the stack slots, where escape analysis puts aggregates, ssa.md §4.2:
scanned as ambiguous words), and for each call its return address, in instructions from the function's start, with
its map. `runtime/quest_gc.c` has the bytes' form. The return addresses come from labels put after the calls, which
keep their places through pairing and branch relaxation and are then dropped; each instruction is four bytes, as
the encoder relies on too. The table is the unit's `qr_frames`, in `__TEXT,__const`: the SSA's builder makes a
placeholder of that name, an empty table, and the call that registers it (`quest_register_frames`) in the unit's
`qr_register_dicts`, and the backend writes the table in the placeholder's place, so `ssac`, which prints the
placeholder, registers nothing. Addresses in it are differences (the first function's from the table, each listed
function's from the first), which the linker resolves, so the table needs no fixing up when the program starts. The
JIT's loader puts a unit's table in the code's region, sets its first word, and the unit registers it the same way
([jit.md](jit.md) §3.6).

**A function that enters a `try` has no maps,** and is not listed: its handler reloads from slots what liveness in
the try's body does not see it use, so its frame is scanned whole, as C's frames are.

**The collector's walk** follows the frame records from its own frame (every function that calls keeps one). A
record's return address names the call its caller is in: if a table lists it, the caller's frame is scanned by the
map, and otherwise whole. A callee-saved register live across a mapped call is where the youngest frame after it
saved it, which the walk knows while every frame since is mapped, their prologues being described; past a frame
that is not, the places known so far are scanned as ambiguous words, and that frame whole, so a register's value is
always seen, and seen as what its owner says when the frames between are mapped. A register no mapped frame has
live is not scanned where a mapped frame saved it. `QUEST_GC_MAPS=0` scans every frame whole, and `QUEST_GC_STATS`
counts the frames scanned each way.

`codegen.frameSlots` returns each slot of a function's frame with its offset, its size, and its class, and
`codegen.frameMaps` the frame and each call's map as text; `questlang/arm64_frames` prints both for functions that
spill pointers, integers, reals, and `val`s across a call. `QUEST_LIVE_SLOTS=1` names what is live across each call
in the assembly ([profiling.md](profiling.md) §6).

### 3.14. The SSA-to-C printer

`questlang/codegen/c/ssac` prints a unit's low-level SSA as C, as MLton's C backend prints its lowest IR: each block a
label, each SSA value a local, block arguments assignments before the `goto`, stack slots a local byte array, and
memory reached by byte offsets (`*(int64_t *)(p + 16)`). It computes no layout and chooses no representation; it
only prints what the SSA says, so a test that passes through it checks the SSA's construction, the shared layout
(its units link with the C backend's, which assert their offsets), and every lowering before instruction selection.

- **No header.** `ssac`'s C includes nothing and declares everything itself, so that nothing it prints conflicts with
  the runtime's declarations: a symbol the unit does not define is `extern char name[]` (a thread-local, `extern
  __thread`). Its units compile as GNU C, with `-fno-strict-aliasing` (they read and write a word of memory as
  different C types) and `-fno-builtin` (`ssac.cFlags`).
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
pass. Cross-module inlining, in whole programs, now makes abstract ids affordable there (§6.3).

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
  only after a release (release-compiler.md §2).

### 3.16. Line tables

Native code carries a DWARF line table, so that lldb can break on a Quest line and show the lines of a backtrace's
frames (§1: lines only, no variable locations). A position is attached at each level and carried to the next:

- **IR statements.** Every statement that makes code where it is (a let, a store, a branch, a jump, a return, a raise)
  has the source offset of the expression or binding lowering made it from, in the unit's numbering of files
  (`nodes.stmtPos`, [ir.md](ir.md) §5), or none. Lowering sets the position as it enters each expression and binding,
  so a nested call has its own column. Passes keep the positions of the statements they copy; a statement a pass makes
  in place of another takes that one's (a jump for a return, a return for a jump, the assignments and the `continue`
  that contification makes of a tail call), and inlining gives the parameters' bindings and the result's the call's
  position, the inlined body keeping its own. A function's return has none of its own.
- **The SSA.** The builder resolves a statement's offset to a file, line, and column, and every instruction and
  terminator it appends from then on has that position (`Inst.loc`, `Block.termLoc`, [ssa.md](ssa.md) §2), until the
  next statement with a position; the unit lists its files' absolute paths (`Unit.files`).
- **Machine code.** Selection records each instruction's position beside its operation (`Selection.locs`), so that
  register allocation, which numbers instructions, sees none of it. When the function's code is laid out, a
  `.loc file line column` directive (`minst.opLoc`) goes before each instruction whose position differs from the last
  one given, but for a constant or an address that allocation makes again where it is used, which keeps its
  definition's position and would move the line back. The directives come after allocation and the choice of blocks to
  pass over, so the code is the same with or without them.
- **The unit.** The assembly declares each file (`.file 1 "dir" "name"`), and the assembler writes the line table from
  the directives. It does not write the debugging information a debugger reaches the table through when the input has
  its own `.loc` directives, so `codegen/arm64/asm` writes it: a compile unit for the unit's own file, its directory as
  the compilation directory, with a subprogram for each function, from its symbol to a label past its code, and the
  language code 0x8000, from the range DWARF leaves to users. dsymutil and lldb place each function's lines at its
  address through the subprograms.

lldb finds a separately built program's debugging information through the debug map the linker writes, in the
objects in the build directory, which must stay there. A program assembled and linked in one step (`--whole-program`)
has its object only as a temporary, so the driver passes `-g` to that step, and clang runs dsymutil, which writes
`program.dSYM` beside the binary; the tests' temporary binaries are linked without it.

What the table cannot show: code that the inliner copies keeps its source's lines, so stepping into an inlined call
shows the callee's lines without a frame for it; and a line whose code is gone (a constant propagated, a jump to the
next block) has no address, so a breakpoint set on it resolves to the next line that has one.

### 3.17. Machine instructions and targets

**The SSA stays one target-independent representation,** with one `Opcode` option. It is not parameterized by a
target's operations, and targets' operations are not subtypes of a shared subset: an option with fewer cases is the
subtype, so a shared subset would be a subtype of each target's option, not a supertype a target extends; a pass
generic over "some target's operations" would need a bounded type parameter, which compiled Quest implements with
view maps and tag maps at run time (the cost §3.15 keeps out of inner loops); and a shared pass casing on the subset
would need `else` for the rest. What is specific to a target happens after the SSA, in three layers:

1. **The SSA** ([ssa.md](ssa.md)), target-independent.
2. **A target's machine instructions** (`codegen/arm64/minst`): `arm64.Op`, an option of the target's operations with
   their immediates, conditions, and addressing modes, made by instruction selection over virtual registers and cased
   on, without `else`, only by that target's selection (`codegen/arm64/select`), printer, and encoder.
3. **Shared machine-level code over a structural shape** (`codegen/machine/machine`): a machine function's blocks hold
   instructions, each with its operands (each a virtual or physical register, used or defined) and a shared kind
   (`kindOrdinary`, `kindMove`, `kindJump`, `kindBranch`, `kindCall`, `kindReturn`); the target's `Op` sits in a table
   beside them, indexed by instruction, which shared code never reads. A physical operand is fixed, and moves (and a
   jump's arguments with its target's parameters) are the allocator's hints. The register allocator, liveness over
   virtual registers, parallel moves, frame layout, and branch relaxation work on that shape; when they must make an
   instruction (a move, a spill, a reload, a jump), they ask the target through a record of its functions
   (`Lowering`: a move, a load and a store of a virtual register's slot, and the scratch registers).

**A target description** (`codegen/machine/target`) gives the shared code a target's registers (numbers, classes, names),
which are allocatable, caller-saved, and callee-saved, its argument and result registers by class, its scratch
registers, its stack alignment, and its word size. `codegen/arm64/target` is the only one; nothing outside a target's
own modules names a register. Selection gives each conditional branch's target a block of its own, where its edge's
moves go, and a `try` a block beside it that a raise enters; the printer expands three pseudo-instructions (a
constant, a symbol's address, a thread-local's). An x86-64 backend would be a selection, a printer, and a target
description, reusing everything in `codegen/machine/machine`; an LLVM or WASM backend would print the SSA with its
signatures (WASM would also need `try` through its exception handling, slots on a shadow stack, and precise roots).

## 4. Testing

- **The shared goldens** of what programs do run with `--backend ssac` and `--backend arm64` too (runner modes, as
  `--self-hosted` is), and every run test passes with each. Each mode has a pending list, as the self-hosted driver
  has (`tests/self-hosted/pending-ssac.txt`, `pending-arm64.txt`, testing.md §2.3), now empty: a pending test that
  passes fails, so the lists only shrink.
- **Mixed builds:** each multi-unit test also runs with its units split between the backends (alternating, and the
  other way), which finds any disagreement about layout or calls. For `ssac`, every test is multi-unit (its
  library modules are units too), and the runner's `ssac-program` and `ssac-modules` modes compile the program's unit
  or its modules' through `ssac` and the rest through C, so that calls, closures, records, and exceptions cross
  between the backends both ways; `tests/self-hosted/backends.py` builds one program with every split in one build
  directory.
- **Calls between C and native code,** generated for each kind of signature: integers, `double`s, 16-byte values,
  descriptors, closures, `var`/`out` pointers, more than eight arguments, in both directions.
- **Layout assertions** (§3.3) compile in every C unit.
- **The verifier** after every stage, and the SSA's goldens.
- **The self-hosting check** with the arm64 backend: stage 2 built by it compiles the compiler and writes the same
  artifacts as stage 2 built by the C backend.
- **Before every push,** `tools/check` runs these (testing.md §4.1): the backends' modes, the self-hosting check
  through `arm64` with the whole-program fixed point, and the ABI tests; through `ssac`, and `arm64-modules`, by
  hand.
- **Benchmarks:** compile and run times against the C backend, recorded with their dates in benchmarks.md.

## 5. Open Work

**`ssac` as the C backend** (§1). Measure `ssac`'s code and compile times against the C printer's, with the SSA's
passes (promotion, escape analysis) and whatever else the comparison needs. If `ssac` is close enough, it becomes the
self-hosted compiler's C backend: `--backend c` selects it, the C printer and its goldens are retired, along with its
own forms of escape analysis (c-representation.md §5.3), and `--whole-program` goes through the SSA. *Done when* the
self-hosted compiler has one C backend, or benchmarks.md records why the C printer stays and what would change that.
At the last measurement (benchmarks.md §5), the compiler built by `ssac` took 1.2 to 1.4 times as long to run as the
one built by C; the suite's programs through `ssac` are still to be timed.

## 6. Possible Future Optimizations

What might be done to the code the backend generates, each to be measured (benchmarks.md) before and after.
[arm64-performance-review.md](arm64-performance-review.md) carries this on from new measurements.

### 6.1. Where arm64's time goes (2026-10-31)

arm64's programs take 2.08 times C's (geometric mean, benchmarks.md §7.2), but the median ratio is 1.58: tailfib,
fib, tak, md5, checksum, and psdes-random (5 to 17) pull the mean up. Six benchmarks near the median (life, ray,
hamlet, mlyacc, zebra, nucleic: 1.4 to 1.8 times C) were rebuilt with each of clang's optimizations off in turn,
`ssac`'s C through LLVM's `opt` and `llc` in stages, and profiled with `sample` (least user time of three alternating
runs, on a loaded machine, so differences under about 5 percent are noise). The gap is two factors of about the same
size:

1. **Runtime helpers called out of line: 1.20 to 1.44** (C against `ssac`, one compiler, `ssac` calling the
   helpers as arm64 does). 8 to 23 percent of arm64's samples are in helpers that C inlines to a few instructions:
   `quest_option_tag` (13 percent of life, 8 of zebra), `quest_real_mul_at` and its siblings (14 to 18 percent of ray
   and nucleic), `quest_unproxy`, `quest_string_get_char` and `quest_string_length`, and `quest_ascii_val`.
2. **Code generation for the same SSA: 1.13 to 1.48** (arm64 against `ssac` at `-O2`). LLVM's IR optimizations add
   little to SSA the IR's passes have simplified: `mem2reg` alone and `llc -O2` come within 1.04 to 1.19 of `-O2`
   (life the most), and `-O2` is no faster than `-O1`. No one machine pass matters either: without machine LICM,
   machine CSE, branch folding, block placement, or coalescing, 0 to 7 percent each, and fast instruction selection
   costs nothing. The register allocator does: LLVM's fast allocator costs up to 1.35 against its greedy one, and arm64
   is 1.17 to 1.32 behind `llc -O2`. In the programs' functions arm64 emits 1.5 times LLVM's instructions: 2.6 to 2.8
   times the unconditional branches, 1.4 to 1.7 times the register moves, 1.5 to 2 times the constant moves, 1.6 times
   the stack loads and stores, and hundreds of `and`s and `cset`s where LLVM has a `tbz` or a fused branch. life's
   inner loop (`qf_f_5`) is 72 instructions to clang's 48.

Neither vectorization nor unrolling changes these programs (0.90 to 1.01), nor does clang's inlining of their own
functions once Quest's inliner has run. Allocation and collection are 50 to 67 percent of C's time in the same six
(§6.2, item 2), a cost the two backends share.

### 6.2. Recommendations, in order

§6.1's first factor, the runtime's helpers called out of line, is gone: the SSA's builder expands them inline
([ssa.md](ssa.md) §4). Most of the instruction selection it found missing is done (§3.5). arm64's time against C's
after both: life 1.50, ray 1.25, hamlet 1.38, mlyacc 1.54, zebra 1.44, nucleic 1.20. What remains:

1. **Fewer moves and spills in the allocator:** coalescing a copy's source and destination where their ranges do not
   interfere (a block argument and its parameter, a call's argument and its register), a spill placed at the definition
   and a reload at the use rather than around every use, and `ldp` and `stp` for adjacent spill slots (now shared by
   values whose lifetimes do not overlap, §3.8). Eager loads at a block's start (`repeat` in imp-for loads all four of
   its closure's fields at entry, two into callee-saved registers, though two are used only on one path) belong here
   too. Expected: the rest of the second factor; LLVM's allocators show that it is where the code generator's advantage
   lies. *Tried, and not kept* (2026-11-01), since neither paid:
   - **Hints followed through registers not yet given one:** a value passed to a block's parameter is allocated
     before the parameter, so its hint names no register and it takes `x12`, and the edge moves it. Following the
     parameter's own hints, three deep, to a call's result or another argument removed life's `ldr x12, [x20]; mov
     x0, x12`, but no benchmark changed beyond noise.
   - **Coalescing:** a move's two registers, and a jump's argument and its target's parameter, joined in one interval
     (union-find before the scan; each register given the group's pieces where it is live, and the moves between
     pieces credited to the one live there) where the groups' ranges do not overlap. It passed the suite, left life's
     inner loop with no moves, and took 942 instructions and 153 stack accesses of life's `qf_f_6` to 815 and 115.
     On an idle machine (five rounds), against no coalescing: ray, hamlet, zebra, and nucleic within noise either
     way; coalescing only the jumps that go forward, mlyacc 1.50 to 1.40 but life 1.50 to 1.59; only moves, or only
     back edges, nothing. Longer intervals in a function short of registers (`qf_f_6` uses every callee-saved one)
     are the likely cost, so a conservative test (Briggs's: coalesce only where the merged interval stays
     allocatable) would be the next thing to try.

   With the helpers inline and the selection done, `llc -O2` on the same SSA leaves hamlet no faster than arm64, life
   1.25 times faster, and mlyacc 1.34. In the hot functions read (life's `qf_f_5`, mlyacc's `qf_union` and its list
   length) arm64 spills nothing; what LLVM does that arm64 does not is block placement (a cold exit between a loop's
   blocks costs arm64 a `b` on the hot path; without it `llc` was 1.04 to 1.07 slower, §6.1) and a move made before a
   branch rather than in a block of its own.
2. **Allocation's fast path inline:** with benchmarks.md §3.1's per-size free-list cache in the runtime, the
   pop of a free list is a few instructions that the C backend gets from the header and arm64 could select inline.
   Not part of the arm64/C gap, but the largest cost both share. *Not done while the collector was Boehm's* (the
   user's decision, 2026-10-31: an allocation path compiled into programs was a deeper dependency on it than Quest
   should have); done with Quest's own collector ([collector.md](collector.md) step 3).
3. **Then, measured before more is done:**
   - **On the SSA:** copy propagation, constant folding, dead code elimination, value numbering, block merging, and
     jump threading. LLVM's equivalents gain 3 to 5 percent on SSA the IR's passes have simplified (life 13 to 19),
     so these come after the allocator;
   - **promotion in functions that enter a `try`,** whose mutable variables stay in slots ([ssa.md](ssa.md) §4.1),
     and tail calls in functions any of whose slots' addresses escape (§3.7);
   - **entering fewer handlers:** a `try` whose body cannot raise pushes no handler, and a raise whose handler is in
     the same function is a jump (benchmarks.md §3.5); on the IR, for every backend, and commoner now that inlining
     puts a raise beside its handler;
   - **the small recursive functions** (tailfib 16.8 times C, fib 8.7, tak 7.4), whose recursion clang turns into
     loops or accumulations and neither the IR's passes nor arm64 do, and **word arithmetic** (md5 7.1, checksum
     6.7, psdes-random 5.2), which is instruction selection: these make the mean twice the median.

### 6.3. Other ideas

- **Options like `maybe.T` as a pointer or a constant, with nothing allocated:** [option-values.md](option-values.md)
  (deferred).
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
  - **payload-free option cases are now constants** (c-representation.md §5.3), so opcodes need not be made once
    by hand any more;
  - **`maybe.T` as a manifest option type** (§3.15), so that code `case`s on it and needs no `-1` for "none";
  - **one-case variants unboxed in aggregates' slots,** so that a `Variant block: Int end` id costs nothing in an
    array or a node, and the type checker tells a block's number from an instruction's;
  - **typed ids even while they allocate,** if the language fixes come later, accepting their cost until they do.
  Cross-module inlining (ir.md §8.6) has made the backend's ids as abstract types affordable in whole programs.
- **A cheaper `try` in C:** the `asm goto` experiment of §3.6.
- **Better register allocation than linear scan,** if §6.2's first item leaves spilling costs.

## 7. The C Backend's Decisions, and Where the SSA Gets Each

A survey (2026-10-29) of `questlang/codegen/c/printer`, `declarations`, and `types`, and of
`runtime/quest_runtime.h`: what the C backend decides that is more than C syntax, and where the SSA backends (`ssac`
and `arm64`) get each decision. The sources are:

- **layout**: `questlang/repr/layout` and `repr/shapes`, already shared;
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
| Scalars: `Int` `int64_t`, `Real` `double`, `Word` `uint64_t`, `Bool` C `bool` (1 byte), `Char` `uint8_t` (`QChar`, §3.9), `Ok` nothing (a `void` result; `QVal` 0 where stored) | `layout.representation` | layout; a narrow value in a register is always extended to 64 bits (zero-extended, both), and one received is extended again, never trusted (Apple's ABI extends only to 32 bits) |
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
| Runtime structs read or written directly: `QClosure`, `QArray`, `QAuto`, `QRecordHeader`, `QExceptionState`, `QExceptionHandler`, `QViewMap.index`, offset tables, the proxy tag bit | `quest_runtime.h` | layout, with assertions (§3.3) |
| Descriptor structs: every `QTypeDescriptor` kind and its payload structs, with `bool` and `size_t` fields | `emitTypeDescriptors` (500 lines), `types.descriptorForm` | data, laid out by the runtime structs' layouts |
| Function-type adapters: for each function type described, `quest_adapt_<T>` (wraps a closure converted at run time by descriptor), its thunk, and `quest_invoke_<T>` (calls a closure with `QVal` arguments), which the runtime calls through the type's descriptor | `emitFunTypeAdapters` | data describes them; each backend generates their code from it (the SSA's backends in the SSA), since the IR cannot express a call through a descriptor's invoker |

### 7.2. Operations

| Decision | In the C backend | SSA backends |
|---|---|---|
| `Int` `+`, `-`, `*`: C operators, without `-fwrapv`, so overflow is undefined; comparisons | `prim` | build: wraps (§8) |
| `Int` `/`, `%`, `mod`: a zero divisor raises `int.error`; `INT64_MIN / -1` and `INT64_MIN % -1` are undefined in C | `quest_int_div_at`, `quest_int_mod_at` (inline) | build: the zero check inline, then `sdiv` (and `msub`), which give `INT64_MIN` and 0 |
| `Real` `++`, `--`, `**`, `//`: a NaN result raises `real.error`, as does a zero divisor; `^^` | `quest_real_*_at` (inline), `quest_real_pow_at` | build for the inline ones; runtime for `^^` |
| `is`: `==` on words and pointers; through `quest_unproxy` for an original access; `quest_val_is(d, a, b)` on `QVal` words | `prim` | build; runtime for `quest_val_is` |
| `<>` and string constants: `quest_string_concat`; a constant is `quest_string_new(literal, length)` at each evaluation | `prim`, `const` | runtime, the literal's bytes as data |
| Word operations: the externals of `lib/word`, called directly (ABI 50), all `static inline` | `quest_word_*` | runtime, out of line (§7.5) |
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
| Exceptions: `quest_alloc_exception(name)` at each evaluation; the handler record and catch array on the C stack, popped on every way out (`leaveTo`); the handler's variable a copy of `QExceptionState` (48 bytes); `quest_raise_at(exc, payload, site)`, or `quest_raise_typed_at(exc, payload, descriptor, text, site)` with a payload of a type other than `Ok`; `quest_reraise(state)` (by value, so through memory) | `sTry`, `sRaise`, `emitCatches` | build (§3.6), runtime, abi |
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
| Allocation: `quest_alloc(size, layout)` bumps the collector's cursor through the current hole (zeroed as it is entered) past a header word naming the layout, and sets the object's start bit; the slow path finds the next hole or collects ([collector.md](collector.md) §3.4) | `quest_runtime.h` (inline) | runtime, out of line, so that the mode is the runtime's |

### 7.4. What clang Does

- **The calling convention** (§3.3), with the composites: `QRecordVal` and `QVariantVal` in two `x` registers, and
  `QExceptionState` (48 bytes) through memory, as any composite over 16 bytes.
- **Frames and unwind information** (§3.10): clang keeps frame pointers on Darwin and emits compact unwind.
- **`setjmp`** (§3.6).
- **Optimization:** the inline helpers inlined, registers allocated, and more, none of which the SSA backends must
  match.

### 7.5. What the Backends Share

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
   description, its C unchanged; the SSA backends lay it out by the runtime structs' layouts (§3.3) and generate
   the adapters' and invokers' code in the SSA. The descriptor forms and record naming are in
   `repr/staticdata`, which builds the description; `declarations` prints it.
3. **Slot conversions as data.** `layout` says which of a few kinds of conversion takes a shape's value to its slot's
   word and back, and `codegen/c/types` spells each kind in C.
4. **Out-of-line runtime helpers.** The header's `static inline` helpers are declared `Q_INLINE`, which is
   `static inline` everywhere but one runtime file, which defines it as nothing before including the header and so
   gives the runtime an external definition of each, under its own name. Every other translation unit keeps its own
   inline copies, as C allows.

Everything else in §7.2 and §7.3 is the SSA's construction. An operation's access sequence is short, and its C text
does not translate into SSA, so sharing it would need an intermediate form that neither backend wants. The mixed
builds (§4) keep the two implementations agreeing.

## 8. Integer Arithmetic Wraps

`Int` arithmetic wraps, in two's complement, in every implementation (decided 2026-10-29). The three implementations
disagreed before (tried on `9223372036854775807 + 1` and `INT64_MIN / ~1`): the bootstrap's interpreter gave
`9223372036854775808`, outside `Int`'s range, from Python's unbounded integers, and compiled code and the self-hosted
interpreter (which is compiled code) wrapped, by C's undefined behavior. Now C is compiled with `-fwrapv`,
`INT64_MIN / -1` is `INT64_MIN` (and `% -1` is 0) in the runtime's helpers, the bootstrap's interpreter reduces
results to 64 bits, and run tests check each case (ABI 52). arm64's `add`, `sub`, `mul`, `sdiv`, and `msub` do what
Quest does.
