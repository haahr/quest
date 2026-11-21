# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## A function value converted to a supertype allocates its adapter's closure every time

**Problem.** An adapt plan (a closure used at a function type whose arguments or result need converting, ir.md §8.4.1)
allocates a two-word closure, `QAdaptClosure { fn, orig }`, each time the conversion runs. The compiler's build makes
48.9 million of them, 4.6 percent of its allocations, more than one object per closure saved
([benchmarks.md](benchmarks.md) §32).

**Where to start.** `benchmarks/mlton/allocations.py --sites` on the compiler's build (or a temporary counter by layout,
as §32 used) for the conversions that make them; then whether a known function's could be static, as the thunk pass
already makes a known function's adapter (`ir/thunks`), or whether the conversion could be hoisted out of the code that
repeats it.

**Done when.** The adapters the compiler makes most are static or made once, measured as §32 measures, or the idea is
dropped with its measurement.

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

## An interface may declare a member twice

**Problem.** Both typecheckers accept an interface that declares the same member twice, with different types, and a
module that defines it twice to match. The self-hosted compiler builds and runs the program; the bootstrap's C fails
to compile, with `redefinition of typedef 'quest_sig_util__Regexp_matches'`. It was found by adding an iterator
`matches(r: T s: String): iter.T(Match)` to `util/regexp`, which already had `matches(r: T s: String): Bool`
([iter.md](iter.md) §3, where the iterator became `findIter`).

**Reproduce.** Add `matches(r: T s: String): iter.T(String)` to `lib/util/regexp.int.quest` beside the existing
`matches`, and a `let matches` to match after the existing one in the module: `./quest --stop-after typecheck` and
`./questboot --stop-after typecheck` accept the module, and `run_tests.py -k stdlib/regexp_operations --phase
run_c_compiled` fails in the bootstrap's C. (A smaller case, not yet tried: an interface declaring `f` twice.)

**Where to start.** The checks of an interface's declarations in `questlang/typechecker/` (where a duplicate type
or exception name would be caught, if one is) and `bootstrap/python/quest/typechecker/`, and a module's lets
against its interface.

**Done when.** Both compilers reject a repeated member name in an interface, with the same message, and an error
test under `tests/errors` shows it.

---

## Faults the wasm review reported that no probe reproduced

**Problem.** A review of the wasm backend (2026-11-15) reported three faults that probes written the same day did not
show, so nothing was planned for them:
- an `out` argument that needs a conversion and that the callee does not assign (a segmentation fault natively);
- subsumption of an auto value with a covariant record component (every mode gave the right answer);
- the JIT's "a use of variable qj_1_record (423), which nothing binds", for which the review gives no program.

**Where to start.** A program that shows one, run compiled, by the JIT, and by both interpreters.

**Done when.** A program shows one and it is fixed with that program as its test, or a review of the code finds the
fault gone.

---


## A failed subtyping alternative leaves its metavariables solved

**Problem.** `subtyping.solve` assigns a metavariable in place (`x.meta.instance := some(t)`), and nothing records the
assignment to undo it. `step` tries a type variable's bound first and falls back to the structural rules when that
fails (`prove(bound sup)`, then `structural(sub sup …)`, types/subtyping.mod.quest:321–326); a metavariable solved
inside the failed attempt stays solved, so the fallback, and a record's or variant's later fields, are checked against
a solution that no proof stands behind. Found by reading the code in the review behind
[compiler-refactoring-ideas.md](compiler-refactoring-ideas.md) (2026-11-20); no program is known to go wrong.

**Where to start.** A program where the bound's proof solves a metavariable and then fails, typechecked by both
compilers (`./quest --stop-after typecheck`, `./questboot --stop-after typecheck`), and whether the bootstrap's
subtyping has the same shape. The fix is a trail of assignments with `mark()` and `undoTo(mark)`, undone when an
alternative fails (OCaml's `Btype.snapshot`/`backtrack`, Lean's `MetavarContext` save and restore); assignments are
made in two places, `subtyping.solve` and `model`'s path compression (types/model.mod.quest:766).

**Done when.** Such a program typechecks as it should in both compilers, with a test, or the review finds that no
metavariable can be solved in a failed alternative and says why in a comment at `step`.

---

## The C printer decides where a collection can happen by reading its own C

**Problem.** Whether an emitted line may allocate, and so collect, is decided by scanning its text for an identifier
right before a parenthesis (`callsFunction`, questlang/codegen/c/printer.mod.quest:330–352), with `sizeof` and lines
starting `quest_barrier` excepted. `emit` then logs each object under initialization (`quest_barrier`) before such a
line. The collector's correctness therefore depends on the spelling of generated C: a call that reaches the
allocator without that shape (a macro used without parentheses, or a call through a cast function pointer, whose `(`
follows a `)`) misses its barrier, which is a fault; a non-call with the shape (a field macro, `f(` inside a string
literal) only adds a barrier that costs time.

**Where to start.** Whether any emitted line today calls without the shape, by comparing the lines `callsFunction`
accepts with the calls the printer makes (`QUEST_COLLECTOR_STRESS` runs, [collector.md](collector.md), would show a
missed barrier). The structural fix is the printer recording calls as it builds them, the first step of
[compiler-refactoring-ideas.md](compiler-refactoring-ideas.md) §6.4.

**Done when.** Barriers are placed from what the printer knows it called, not from the text, and the C goldens and
the stress tier are unchanged.

---

## The IR's renaming walk misses descriptors that cloning copies

**Problem.** `walk.mapInStmt` (questlang/ir/walk.mod.quest, used by `replaceVarsInStmt`) renames an `sRaise`'s
exception and payload but not its `descriptor`, and an `sInspect`'s value but not its `witness` or its cases'
descriptors; `clone.copyStmt` copies all three. Variables inside those are therefore left unrenamed by any pass that
renames through `walk`. It may be safe only because every such pass runs before descriptors are attached
(`describe`), but nothing states or checks that. Found by the review in
[compiler-refactoring-ideas.md](compiler-refactoring-ideas.md) §3.2.

**Where to start.** Which passes call `replaceVarsInStmt` or `mapInStmt`, and at which stages; then either rename the
missing fields, or have `verify` reject a descriptor at a stage before `describe` and say so at `mapInStmt`. The
bootstrap's walk, which reflects over fields, is the other compiler to compare.

**Done when.** `mapInStmt` renames every variable `clone` copies, or a check makes the stage argument hold; and
§3.2's generic visitor, if taken, removes the question.

---

## `selects` reads predecessors after changing terminators

**Problem.** `selectFunction` (questlang/ssa/passes/selects.mod.quest:106–126) computes `cfg.graph(f)` once and
goes on using `g.preds` in `through` after `convert` has rewritten earlier blocks' terminators, so later blocks see a
graph that is no longer the function's. It is safe only because an arm `through` accepts has exactly one
predecessor, which a conversion of a different block cannot change; nothing states this.

**Where to start.** Confirm the argument (a conversion rewrites only its own block's terminator, and an arm block's
only predecessor is that block), then state it in a comment at `selectFunction`, or recompute the graph after each
conversion. A per-function analysis cache cleared when a pass changes the CFG
([compiler-refactoring-ideas.md](compiler-refactoring-ideas.md) §5.5) would make the question explicit.

**Done when.** The argument is written down at the loop, or the graph is recomputed, with the ssa goldens unchanged.

---
