# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## `maybe.T` is abstract, so every test of one in another module is a call

**Problem.** `util/maybe` exports `T` abstract, though it is only `Option none some with val: A end end` and has no
invariant to protect. Separate compilation inlines nothing across modules ([ir.md](ir.md) §8.6), so outside
`util/maybe` every `isSome`, `isNone`, `unwrap`, and `some` is a call, where a visible type would let code write
`o?some` and `o!some.val`, inline. Measured in [iter.md](iter.md) §2: a `filter` reaching its held element
through `util/maybe` took 305 instructions per element, and the same stage with an option type of its own, 143.

**Where to start.** Make `T` manifest in `lib/util/maybe.int.quest` (choosing the field's name for good, perhaps
`value`, since it becomes public). Then:

- see what the dynamic format's change touches: a type mentioning `maybe.T` is encoded today as an abstract node
  ([dynamic.md](dynamic.md) §2.3) and would become an option type, so values externed before would not intern;
- update the goldens that print the type;
- rewrite the compiler's hottest call sites to the inline forms, and measure the driver build's instructions retired
  (`/usr/bin/time -l`).

Every importer rebuilds once, since the interface's fingerprint changes. Calls of `isSome` and the rest stay calls, so
only code that uses `?some` and `!some` gains.

**Done when.** `maybe.T` is public and the compiler's hot paths use the inline forms, with the measurement in
benchmarks.md, or the idea is dropped with its measurement.

---

## The JIT's "a use of variable qj_1_record, which nothing binds"

**Problem.** A review of the wasm backend (2026-11-15) reported the JIT failing with "a use of variable qj_1_record
(423), which nothing binds", the SSA builder's message for a variable with no binding
(questlang/ssa/build/values.mod.quest, `read`), and gave no program. Its other two reports were found and fixed
on 2026-11-21: an out argument the callee leaves unassigned (`language/out_converted_unassigned`,
`language/out_generic_unassigned`) and an auto value whose record component mentions its type, which made an
invalid wasm module (`language/auto_record_components`). Probes of records through the JIT (out arguments, auto
values, record views, closures) did not show this one.

**Where to start.** A program with a record bound by a let that the JIT's unit boundary or module rollback
(docs/jit.md) may separate from its use: a REPL session that redefines a record-typed value, or `-e` with a record
captured by a function compiled in a later unit.

**Done when.** A program shows it and it is fixed with that program as its test, or a review of the JIT's binding
of variables across units finds it cannot happen.
