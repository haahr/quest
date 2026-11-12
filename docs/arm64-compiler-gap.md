# Plan: Narrowing the arm64-Built Compiler's Gap to the C-Built One

Five changes to the self-hosted compiler's SSA and arm64 backend, from the profile of [benchmarks.md](benchmarks.md)
§21.5 (2026-11-12): the arm64-built compiler takes 1.13 of the C-built one's user time compiling the driver through
arm64, and all of the difference is in the compiled Quest code. The first three are the profile's named causes, the
last two what the hash map's probe loop (`findIndex`) showed of the general one:

| Step | Change | Share of the difference (§21.5) |
|---|---|---|
| §2 | Constants in the fewest instructions | part of the general half |
| §3 | Switches: tables of values, and a binary search | about 16 percent |
| §4 | The write barriers' fast paths inline | up to 19 percent |
| §5 | Trampolines without frames, and exports that are their functions | about 11 percent |
| §6 | A proxy test once per value | part of the general half |

---

## 1. Decisions

- **The self-hosted compiler's alone.** These are optimizations of the SSA and the arm64 backend, which the bootstrap
  does not have ([testing.md](testing.md) §2.8). The behavior goldens stay shared; the SSA goldens and the questlang
  tests of the passes are the self-hosted compiler's own. §5's identity adapters (§5.2) change the IR, which both of
  its backends compile, so its IR goldens change too.
- **The JIT follows.** It runs the same SSA pipeline and arm64 backend (jit.md §1), so each step holds for code the
  JIT writes, and the `jit` and `jit-files` modes check it.
- **The cheapest and most contained first:** constants (§2), switches (§3), barriers (§4), trampolines (§5), proxy
  tests (§6). Each is measured alone (§7) before the next is begun, and kept only if it helps the compiler or the
  suite without hurting the other.
- **No change to the ABI between units.** Exports keep their symbols and signatures (§5.3 inlines rather than
  changing how an environment is passed). A step that changes what a unit's artifacts contain bumps `ABI_VERSION`
  as usual; either way the stage caches (`.build/quest-stages*`) are removed before measuring, since a codegen
  change after the step's last ABI bump leaves a stale stage 2 that looks fresh.
- **The barriers inline (§4),** decided by the user (2026-11-12). The collector's allocation fast path is already
  inline in the SSA ([collector.md](collector.md) §3.4), and the barriers' are its counterpart. (The user rejected
  inlining Boehm's allocation into programs on 2026-10-31, as a dependency on Boehm's internals; the barriers are
  Quest's own runtime's.)
- **Jump tables are not made** unless §3's measurements leave large switches hot: a binary search needs no new
  relocation, encoding, or branch relaxation (arm64.md §3.11), in the assembler or the JIT's encoder.

## 2. Constants in the Fewest Instructions (`codegen/arm64/printer`, `select`)

`opMovConst` stands for a constant that needs more than one instruction, and `printer.expansion` writes each nonzero
halfword, the first by `movz` and the rest by `movk`: −1 and −2 take four instructions each, and the driver's binary
has 1,117 such sequences, none in the C-built one. `opMovImm` already encodes one halfword by `movz`, its complement
by `movn`, and a logical immediate by `orr` from `xzr`.

- **The expansion picks the shortest form:** a constant `opMovImm` can encode is one instruction; otherwise the
  halfwords that are not `0xffff` after a `movn` when there are fewer of them than nonzero halfwords after a `movz`;
  otherwise `movz` and `movk` as now. The same expansion serves the assembler's text and the JIT's encoder.
- **Comparisons and arithmetic with a small negative constant** use the negated immediate: `cmn x, #n` for a
  comparison with −n, and `sub`/`add` swapped for an addition of −n, where n fits an immediate (selection, `select`).

*Done when* the questlang arm64 tests show −1, −2, `0xffff0000ffffffff`, and a logical immediate each in one
instruction, and a comparison with −1 as `cmn`; the fixed point holds through arm64; and the driver's stage 2 has no
four-instruction sequence for a value one instruction makes.

## 3. Switches (`ssa/tables`, `codegen/arm64/select`)

A switch is a comparison and a branch for each case, in order. `nodes.opcodeIndex`, a 52-way case mapping an
opcode to its position, takes 1,555 samples against the C build's 196, where clang made it a bounds check and a load
from a table of 52 words. Two changes, the first for every SSA backend, the second for arm64:

1. **A table of values** (a new SSA pass, `tables`, after `selects`). A switch qualifies when every case's target,
   and the default's unless it is unreachable or raises, is an empty block that jumps to one join block with
   constant arguments, and the cases are dense (the range of their values at most twice their number) and at least
   four. It becomes a range check against the default (when the cases do not cover the tag's whole range) and a
   load from a static table of the unit's data (`contentsWords`, one table per join parameter) indexed by the value
   less the least case, then the jump to the join. A table's words are read-only data, like the unit's other
   constants.
2. **A binary search** (arm64 selection). A switch with more than four cases left by (1) is compiled as a balanced
   tree of comparisons over the sorted cases (`cmp`, `b.eq`, `b.lo`/`b.hi`), its leaves runs of up to three
   comparisons in order, so that 52 cases take about six comparisons rather than up to 52. `cbz` stays for a case of
   0 at a leaf. `ssac` keeps its C `switch`, which clang lowers.

*Done when* an SSA questlang test (in the style of `ssa_scalars`) shows a dense switch of constants become a table
and a sparse or non-constant one left; an arm64 questlang test runs switches of 5, 16, and 60 cases, dense, sparse,
negative, and with a default, through the search; and `opcodeIndex`'s arm64 code is a range check and a load.

## 4. The Write Barriers' Fast Paths Inline (`ssa/allocations`, `codegen/backend`)

The SSA's backends call `quest_barrier` and `quest_barrier_slot` out of line, and the C backend's code inlines them
from `runtime/quest_runtime.h`: in the profile `quest_barrier_slot` takes 1,864 samples and `quest_barrier` 192,
besides what the calls cost their callers in saved registers. A new expansion beside `inlineAllocation`, run where it
runs (`codegen/backend` for arm64, and `jit/session`), after the barrier rule's check (`ssa/barriers`), which needs
the calls:

- **`quest_barrier(obj)`:** the word before `obj`; if it is under `Q_BARRIER_TAG_LIMIT` (an option's tag before its
  payload), the word before that; if it has `Q_HEADER_OLD` and not `Q_HEADER_LOGGED`, a call of `quest_barrier_log`.
- **`quest_barrier_slot(slot)`:** the slot less `quest_gc_heap_lo`; if that is under `quest_gc_heap_hi` less
  `quest_gc_heap_lo`, and the line's mark byte (`quest_gc_lines`, by the offset shifted by `Q_GC_LINE_BITS`) is
  nonzero, the card's byte (`quest_gc_cards`, by `Q_GC_CARD_BITS`); if that is zero, a call of
  `quest_barrier_card`.
- **The constants come from the runtime's header,** through `runtimeLayout` (as `QUEST_PROXY_TAG` does), so that a
  change to the header's barrier changes the expansion with it; a test compares the two.
- **The globals are loaded at each barrier.** They change only when the heap grows, inside a call that allocates;
  value numbering may share their loads between barriers with no call between them, and does nothing else.
- **`ssac` keeps the calls,** which its C compiler inlines from the header already.

*Done when* an SSA questlang test shows both expansions; the stress tier (`tools/check --stress`, with the `barriers`
check) passes; and `quest_barrier_slot` is gone from the compiler's profile.

## 5. Trampolines (`codegen/arm64`, `ir/thunks`, `ssa`)

A call of another unit's function goes through its export (`qv_<module>_<member>`), which moves the arguments to
make room for a null environment and branches to an adapter (`qa_adapt_N`), which sets `x0` and branches to the
function, each pushing a frame around its branch: vector.get is three calls where the C build's export is the
function itself. The 2,508 functions that only branch on take 1,134 samples, against 57 in the C build.

1. **No frame for a function that needs none** (arm64 frames). A function whose only calls are tail calls, with no
   stack slots and no callee-saved registers used, keeps `fp` and `lr` as they are and makes no frame record: no
   `stp`/`ldp`, its unwind information that of a frameless function ([profiling.md](profiling.md) §7). The tail
   call is then a plain `b`.
2. **No adapter that converts nothing** (`ir/thunks`). Find why vector.get's export calls an adapter (ir.md §8.4.1:
   one is made when the interface's type differs from the function's own); an adapt plan whose argument and result
   conversions are all identities, and whose type parameters pass through unchanged, is dropped, and the export
   calls the function. This changes the IR for both backends.
3. **The export is its function** (SSA, a new pass, `trampolines`). An exported function whose body is a call of a
   function of its own unit, with the arguments passed through and the results returned, and whose callee is small
   (at most 64 instructions, its calls only tail calls or raises), gets a copy of the callee's blocks in place of the
   call: the export is then the function, as the C build's is, and the unit's own callers still call `qf_`. The
   callee's other callers are unchanged, and nothing else is inlined.

*Done when* questlang arm64 tests show a trampoline without a frame and its unwind information read by lldb
(`line_tables`); `vector.get`'s export is one function in the driver's stage 2; and the profile's trampolines take
a few dozen samples, as the C build's do.

## 6. A Proxy Test Once per Value (`ssa/nodes`, `ssa/build`, `valueNumbers`, both SSA backends)

Reading a field of a record that may be a proxy (`original` access) tests its low bit and, for a proxy, loads the
original from it, and `vals.unproxy` builds that as a branch and a join each time. Value numbering cannot merge two
such diamonds, so `findIndex`'s loop tests the same record before each field it loads, the record a parameter of
the loop.

- **An instruction, `unproxy`:** `%2: ptr = unproxy %1`, pure, its value `%1` when `%1`'s low bit is clear and the
  proxy's original otherwise. `vals.unproxy` makes it; every pass treats it as a pure use of its operand (escape
  and scalar replacement as they treat the proxy test now: an allocation's `unproxy` is the allocation).
- **Value numbering merges** an `unproxy` of a value with one in a dominating block, as it does other pure
  instructions, so that a loop whose record was unproxied before it tests it no more.
- **Each backend lowers it late:** arm64 as `tbz` over the load of the original, `ssac` as `quest_unproxy`. The
  parser, printer, and verifier know it, and the SSA goldens show it.
- **Not hoisted:** an `unproxy` first made inside a loop stays there. Value numbering's hoisting was tried and not
  kept, finding almost nothing to move ([arm64-performance-review.md](arm64-performance-review.md) §4, batch 7), but
  an `unproxy` of a loop's invariant record would be one such thing; a hoist of `unproxy`s of loop-invariant values
  to the loop's entry is a follow-up, if the profile still shows them.

*Done when* an SSA questlang test shows two `unproxy`s of one value merged and the backends' lowering runs (run
tests through `arm64` and `ssac` with proxies); and `findIndex`'s loop in the driver's stage 2 loads its record's
fields with no test between them.

## 7. Measurement

Each step, after its tests and `tools/check` pass, on a machine idle for three minutes, with the stage caches
rebuilt:

- **The compiler,** as §21.5 measured it: the C-built and arm64-built stage 2 compiling the driver through arm64 at
  `-j 1` from an empty build directory, three rounds alternating, user time; and the sampled profile, to see the
  step's own functions change.
- **The suite,** through arm64, whole program, `--scale 0.25 --clean`, one run, against §20.3's
  (`quest-arm64-whole-eb7a20e2.jsonl`), for what the change does to programs: the barriers and the switches matter
  to the array-heavy and the variant-heavy programs.
- **The compile time** of the driver through arm64 at `-j 8`, since §4 and §5.3 grow the code.

## 8. Write-up

The steps' measurements in [benchmarks.md](benchmarks.md) §22, each step by commit as §20 recorded the MLton-gap
steps', with the data in `benchmarks/mlton/baselines/`; arm64.md's sections on selection (switches, constants),
frames, and the barriers updated; and this plan retired into §22.
