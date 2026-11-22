# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## A few library modules inlined into their importers, as in a whole program

**Problem.** Separate compilation inlines nothing across modules ([ir.md](ir.md) §8.6), so outside `util/maybe`
every `isSome`, `isNone`, `unwrap`, and `some` is a call, at the generic layout of an abstract type. Measured in
[iter.md](iter.md) §2: a `filter` reaching its held element through `util/maybe` took 305 instructions per element,
and the same stage with an option type of its own, 143; util/iter's stages hold their elements in slots of their own
for that reason (rule 5). Two other fixes were weighed and set aside (2026-11-22): making `maybe.T` manifest gives up
the abstraction, and importers would have to write `?some` and `!some.val` for any gain; carrying every module's
small bodies in `.qi` files changes the separate compilation model, under which an importer depends on interfaces
alone.

The idea: a short list, fixed in the compiler, of library modules that every importing unit sees as a whole program
would, with their abstract types transparent to shapes and their members open to inlining and specialization. The
candidates are `util/maybe`, `util/iter`, and `collections/vector`: small or hot, polymorphic, and stable. A user's
own modules keep the interface-only model. The prelinked modules (`conv`, `int`, `string`, ...) are already a tier
of their own, always compiled apart (ir.md §4.1); this adds a tier always merged.

**Measured** ([benchmarks.md](benchmarks.md) §36, 2026-11-22), with a whole program that compiles the three apart:
they account for all of a whole program's gain in `benchmarks/iter/` (`filter` 153 instructions per element
separately, 45 whole), and for 56% of it in the compiler, 2.5% of the separate compiler's instructions retired
(whole: 4.5%). Inlining the three into separately compiled units, without the rest of a whole program, may gain
somewhat less there.

**Where to start.** The two questions that decide whether it can be built:

- **One module, one state.** Each module's globals stay single: `maybe.error`, `vector.error`, and `iter.exhausted`
  and `iter.error` are exceptions, matched by identity, so an importer may copy function bodies but must refer to the
  compiled module's globals, not merge a copy of the module the way `driver/whole` does.
- **Layouts across the boundary.** Inlined code sees `vector.T(Int)` through to its representation; calls not
  inlined, and units that are not importers, see it at its abstract layout (`genericLayout.abstractInstance`). Every
  value crossing between them must agree or be converted.

The rest follows whole programs: opaque shapes keep descriptors, echo, and dynamic values unchanged; every backend and
the JIT (its units, module rollback) take the bodies; build cache keys include the listed modules' bodies; tracebacks
lose their frames, as in a whole program. Self-hosted only. State the rule for joining the list (small, hot,
polymorphic, stable, no state worth isolating) where the list is defined.

**Later: a user's own modules.** Once the list works, consider a command-line option naming some of a program's
own modules for the same treatment. Such a module's `.qi` must then be marked as one whose importers inline it (and
carry what they need to), so that a build compiling an importer knows its object depends on the module's bodies, not
its interface alone; an unmarked `.qi` keeps today's meaning.

**Done when.** The listed modules' calls are inlined in separately compiled importers, util/iter's own slots may give
way to `util/maybe` (iter.md rule 5 then says so), and the driver build's instructions retired and `benchmarks/iter/`
are in benchmarks.md; or the idea is dropped with its measurement.

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
