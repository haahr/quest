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

---


## The bootstrap's C gives a converted known function a new adapter each time

**Problem.** Passing a program's own function to a generic one twice and comparing the two, as in

```
let same(A::TYPE f: All(x: A y: A) Int g: All(x: A y: A) Int): Bool = f is g
let own(x: Int y: Int): Int = x - y
same(:Int own own)
```

gives `true` in both interpreters and in the self-hosted compiler's code, whose thunk pass makes a known function's
adapter a static closure ([ir.md](ir.md) §8.4.1), and `false` in the bootstrap's C, whose printer allocates the
adapter's closure at each conversion. The same holds for an imported function (`sort.intCompare`) since the
adapter-closures plan's first step.

**Where to start.** The bootstrap's adapt plans, `codegen/c/printer.py`'s `convert` (`case "adapt"`) and `adapter`:
for a known function, or an imported member, a static closure of an adapter that calls it directly, as `ir/thunks`
does.

**Done when.** A shared test that compares converted functions with `is` gives the same answer in every phase.

---

## A tag test that a dominating `?tag` decides is made again

**Problem.** In `if o?made then o!made.x := v end`, the tag is tested twice: `o?made` is an `is_tag`, and `o!made`,
whether read or used as a location, tests it again (a location is lowered as a one-case `switch` whose other case
raises). The simplifier folds a `switch` or a `!` only when the option is made in sight (`madeOf`), not when an
enclosing `if` on `is_tag` of the same value has taken its true branch. Where the option is a `var` field, as
util/iter's lookahead slot (`l.slot`), the two even read it separately (`%57 = tuple_field(%54, 0)`, `is_tag(%57,
made)`, then `%59 = tuple_field(%54, 0)`, `switch tag(%59)`), though nothing between them can change it. Measured
2026-11-20 with `benchmarks/iter/` ([iter.md](iter.md) rule 5): `hold` written so takes a `filter` 46.1 instructions
per element in a whole program against the `case` binder's 45.1, and 156.7 against 153.2 separately, which is why
util/iter keeps the `case`.

**Where to start.** Two levels, the self-hosted compiler's alone, as optimizations are. In the simplifier
(`questlang/ir/simplify`), walking an `if`'s then-branch whose condition is `is_tag(a, t)` with `a` immutable, keep
`a`'s tag as `t`, and fold a `switch` on `a` and a `!t` of it as `sSwitch` does a known option's; that covers an
option bound by `let`. For two loads of a `var` field, the loads must first be seen to be one value: in the SSA,
`ssa_valueNumbers` could merge loads with no store or call between them that may change the field, after which a
branch on a tag that a dominating block already tested can be folded.

**Done when.** `if o?made then ... o!made.x ... end` has one tag test in the IR or SSA for an immutable `o` and for a
`var` field read twice with nothing between, and `benchmarks/iter/` measures `hold` written with `?made` and `!made.x
:=` at the `case` binder's cost, so that util/iter may use either (iter.md rule 5 then says so).
