# Plan: Omitting the Type Arguments Inference Finds

`questlang/` writes the type arguments of most polymorphic calls (`vector.get(:Type v i)`), though the type checker
infers many of them. This plan removes every written type argument that inference finds exactly, by a process that
can be rerun from any base, since the edits touch most of `questlang/` and conflict with every change in flight. The
lasting results are the process and its tools; the edits themselves are redone, from a fresh rebase, when they land.

## 1. Where It Stands (2026-11-15)

- **§2.1, the report,** is on main (`2d416c77`): `--report-inferable[=equal|exact]`, described in
  [type-system.md](type-system.md) §6.9.
- **§2.2, the tools,** are `tools/omit-type-args` and `tools/compare-codegen` ([testing.md](testing.md) §2.9). A
  trial run in `exact` mode at `fcaa43a9` omitted 3,757 calls inferable from their arguments and 434 that need their
  expected type, none restored, and every unit's assembly compared equal; its edits were discarded.
- **A first removal,** with the report's first form (the environment variable `QUEST_REPORT_INFERABLE`, exact type
  nodes), is on branch `questlang/infer-type-args` (local), to be abandoned (§2.4): `566fef29` omits the 3,756 calls
  inferable from their value arguments alone, and `2ce3ff3d` the 434 inferable only with the expected type, found
  after the first pass, since a call that needs its expected type can lose it when the call around it loses its own
  type arguments. Every module's arm64 assembly at `2ce3ff3d` is main's, but for source positions (§2.2's
  comparison).

**Why aliases stay.** About 7,700 more calls are inferable to an equal type but not the same node: a type argument
written as an alias (`:Type` for `model.Type`, `:Entry`) is inferred as the type the alias names. Omitting those
changed three modules' code, because `simplify` propagates a copy only between variables of the same type node
(`simplify.mod.quest`, the `copied` test, `y.v.type.id is x.v.type.id`), and an alias is not the type it names; a
copy whose two variables' types are spelled differently stays. ir.md §4.1 says passes decide by shapes, and the
types IR variables carry are the types as written, alias names and all.

## 2. Steps

### 2.1. Land the reporting flag alone

The report is the lasting tool, so it lands first and on its own, as a driver option rather than the environment
variable it began as: `--report-inferable[=equal|exact]`.

- **A flag, not a variable,** for three reasons. The build engine recompiles only stale units, and only a recompiled
  unit is reported, so a variable silently reported nothing for a warm build directory; given the flag, the engine
  compiles every unit, and each worker is passed it (`workers.command`). A variable left set reaches every compiler
  under it, and its lines on standard error would fail goldens far from their cause. And the report is an output a
  tool consumes, as `--dump-after`'s is, listed in the usage text, with a misspelled mode an error.
- **Two modes.** `equal` (the default) reports a call when inference finds equal types (`subtyping.isTypeEqual`),
  which is what to omit once §2.3 is done; `exact` only when it finds the same type nodes, spelled as written, which
  is safe to omit today and lets §2.4's comparison be narrowed to the alias-spelled calls.
- **The state is the environment's,** not a module's: the mode and the calls found are fields of `env.T`, which the
  checker reaches everywhere and which lives as long as the unit being compiled, so that a REPL or JIT session could
  set it too.
- **Programs as well as modules:** `driver/main.quest` and test programs are compiled as programs, whose type check
  (`typecheck.elaborateProgram`) reported nothing; the driver writes their calls too.
- **The output,** on standard error, one line a call: `FILE:LINE:COL: type arguments can be inferred from the
  arguments [FROM TO]`, or `... with the expected type [FROM TO]`, with the byte range of the type arguments.
- **A unit test** (`tests/python`) compiles a small module and program with the flag in each mode and checks the
  reported positions, ranges, and classes, including a call nested in an inferred call (not tried), a call whose
  argument is a proper subtype (not reported), and an alias-spelled type argument (reported by `equal` alone).
- **Documented** beside the rule for implicit type arguments ([type-system.md](type-system.md) §6.9) and in the
  self-hosted driver's options ([pipeline.md](pipeline.md) §5).
- **Not covered:** the modules a program run by the JIT loads, which the build engine does not compile.
- Full check, push.

### 2.2. Make the process a tool

The process lives in scratchpad scripts today; it becomes `tools/omit-type-args`, so that it can be rerun after any
rebase:

1. Build the compiler, and report (`--report-inferable`) over `questlang/driver/main.quest`.
2. Delete the type arguments of every call inferable from its arguments, by the reported byte ranges; build; commit.
3. Report again, and delete those that need the expected type; build; on an error, restore the call that encloses
   it and build again, until the build succeeds; commit.
4. Compare (below), and stop if anything but positions differs.

And `tools/compare-codegen BASE`: every `questlang/` unit compiled to arm64 (`--stop-after codegen_arm64`) from
`BASE` and from the working tree by one compiler binary, `.loc` lines, the tree's path, and `FILE:LINE:COL` strings
normalized, and the units that still differ listed with their differences. Unit tests for both tools' parsing and
edits, as tooling-only changes have ([testing.md](testing.md)).

### 2.3. Decide by equal types in simplify and unbox

Three tests decide by type identity: `simplify`'s `copied` (copy propagation) and the two in `unbox` (`x.v.type.id
is fun1.resultType.id`, lines 116 and 175). Each becomes a test of equal types, the identity first and
`subtyping.isTypeEqual` after, as `represent.equal` and `genericLayout.typeEqual` already do. Before relying on it:

- **The verifier** (`ir/verify`) must accept a use of a variable whose type is equal to the one it replaces but
  spelled otherwise.
- **What prints types** must not change: echo and error messages carry their own types (ir.md §4.1), so renaming a
  variable should not change them; the run, repl, and error goldens are the test.
- **Echo descriptors** are kept per spelling on purpose (`describe`'s `static`, keyed by the type's id for echo), so
  that echo writes the alias names; nothing here changes them.
- **Cost:** `isTypeEqual` is a subtyping proof, cached for types without metavariables, where the identity test was
  one comparison; time the compiler's build of the driver before and after (benchmarks.md §22.1's method).
- **Goldens:** the simplified IR and the SSA of programs whose copies were spelled differently change; review each
  as an improvement (fewer copies), and update them.

Full check, then the benchmark suite (`--scale 0.25 --clean`) against main's, since the simplifier changes what every
program compiles to.

### 2.4. Redo the removal from a fresh base

Once §2.1 to §2.3 are on main, and just before it would land (so that it conflicts with as little as possible):
abandon `566fef29` and `2ce3ff3d`, rebase, and run `tools/omit-type-args` (`--report-inferable=equal`).
`tools/compare-codegen` against the base must show no unit differing but for positions. A difference means a pass
still tells spellings apart (or a type argument's spelling is visible, as echo's is); fix the pass, or exclude those
calls and say why in the commit. Full check, push, at once, and tell the other workstreams that `questlang/` changed
throughout (a rebase across it conflicts wherever a call's type arguments were edited, and the tool can be rerun on
their side instead of resolving by hand).

## 3. Open Questions

- Calls the report cannot try: those nested in an inferred call's arguments, and constructors with nothing to infer
  from (`vector.new(:T)`). The second pass covers the first kind as the passes peel the outer calls; a third pass
  finds what the second exposes, if any.
