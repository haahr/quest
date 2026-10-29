# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Compile functions of type parameters only whose results are functions

**Problem.** A function whose only parameters are type parameters runs when it is applied to types, and its result
may be a function or another polymorphic function: `let h(A::TYPE): All() Int = begin ... fun(): Int 1 end`,
`fun(A::TYPE) fun(): Int 2`, or the curried `let q(A::TYPE)(B::TYPE): Int` (whose inner function has type parameters
of its own, so the type checker keeps the two functions apart). Its type, `All(A::TYPE) All() Int`, is the type of a
function of type parameters then value parameters, `let f(A::TYPE)(): Int`, and the backend's calling convention
follows the type, so a caller would call `h` as it calls `f`: with the type and value arguments together, with no
point at which `h`'s body runs alone. Before the lowering rejected these functions, the C backends crashed on them or,
in the bootstrap, compiled `fun(A::TYPE) fun(B::TYPE x: B): Int 6` into code that printed a pointer as its result. The
interpreters run them correctly (the typed AST's `TypedFun.type_only`, `exprFun`'s `typeOnly`). Partial type
application is broken the same way: given `let g(A::TYPE B::TYPE): Int`, compiled code calls `g(:Int)` with one
descriptor where `g` takes two (clang rejects the C), and both interpreters run `g`'s body at the partial application.
[tasklist-plan.md](tasklist-plan.md) §1 plans both.

**Reproduce.** Compiling `tests/source/language/type_only_functions_returning_functions.quest` (`./questc
--stop-after run_c_compiled`) reports `a function of type parameters only whose result is a function`; the test skips its lowering phases.

**Where to start.** `function` in `quest/ir/lower.py` and `questlang/ir/lower.mod.quest`, where the check is. The
choice is the owner's, since it affects what a program prints: compile such a function as one of type parameters then
value parameters whose body computes the result and calls it (`h(A)() = (body)()`), which runs the body at each call
rather than once when it is applied to types; or give type-only functions a representation of their own, which
callers cannot choose from the type alone (a first-class value of type `All(A::TYPE) All() Int` may be either kind).

**Done when.** The test runs compiled with the interpreters' output, or the language says what such functions do and
both compilers do it, and the check in the lowering is gone.

---

## Faster word operations in compiled code

**Problem.** Each `word` operation in compiled code (`word.xorBits`, `word.shift`, `word.rotate`, and the rest of
`lib/word.int.quest`) costs three calls. The caller calls the importer's wrapper `qv_word_xorBits`, which calls
through the closure in the `word` module record, which calls the external `quest_word_xor_bits` in the runtime. None
of them can be inlined, because the module record is only filled in at run time. The self-hosted compiler hashes
type text with SHA-256 written in Quest (`questlang/codegen/sha256`) and hashes keys in `util/hash`, both made of word
operations. Profiling the compiler building itself (2026-10-27) put about 7.5% of its time in these call layers.

**Reproduce.** Build `questlang/driver/main` with `./questc` from nothing under `sample` (macOS) or `perf`, and
compare the time in the `qv_word_*` wrappers and closures with the time in the `quest_word_*` functions.

**Where to start.** Compile a call to a `word` operation whose target is known statically into a direct call to its
runtime function, or into the C operator (`^`, `<<`, ...) for the simple ones. An importer does not know today which
members of `word` are externals, or which runtime functions they are: neither the `.qi` nor the `.qm` records it, so
either the artifacts record it (an ABI change) or the backend treats `word` as a builtin it knows. Do the same in the
bootstrap, and in the same commit, while the two compilers are kept in step. Every compiled program's C changes, which
`tools/c-diff` shows. A native SHA-256 primitive would remove most of the remaining cost of `layout`'s
digests, but needs a new runtime primitive and so a release before `questlang/` can use it (docs/release-compiler.md
§2).

**Done when.** Word operations in generated C are direct calls or C operators, the self-hosted build of
`questlang/driver/main` spends no measurable time in the call layers, and both compilers produce the same C.

---

## Capture rules for `var` variables as the paper has them

**Problem.** The type checker's rule for which mutable variables a function may use is the reverse of the paper's.
*Typeful Programming* §4.8 says only that "functions cannot refer directly to global variables of `Var` type": they
must be passed as `in` and `out` parameters, or held in data structures (the own-variable idiom). It says nothing
against capturing local `var` variables. This implementation forbids capturing a function's local `let var` variables
(and `var` and `out` parameters) in a closure, and lets any function use a module-level or top-level `var` variable
directly ([type-system.md](type-system.md) §6.2.3, [codegen-c.md](codegen-c.md) §10.8). Its reason is an
implementation one: locals stay unboxed in their frame, so no pointer to them can outlive it. Converted code pays for
it: an SML `ref` captured by a closure has to become a tuple with a `var` field (benchmarks/mlton).

**Reproduce.** `tests/errors/typecheck/closure_capture_local_var.quest` is rejected ("Cannot capture 'var' variable
'x' in closure"), and a top-level `let var n = 0` used by a top-level `let bump(): Ok = n := n + 1` is accepted.

**Where to start.** `_check_capturable` in `bootstrap/python/quest/typechecker/checker.py` and its port in
`questlang/typechecker/checker.mod.quest`. Allowing a captured local `var` means holding it boxed, in a cell the closure
and the frame share, as a local whose address is taken already is (`location_representation`, codegen-c.md §10.8):
closure conversion (`ir/closure`, whose `capturesMutable` error goes away) and both interpreters must treat it so. `var`
and `out` parameters are references to the caller's locations, which the paper does not discuss; keep forbidding their
capture unless there is a reason not to. Forbidding direct use of a global `var` breaks any code that does it: audit
`lib/`, `questlang/`, and the tests first, and rewrite such uses with own variables. Update type-system.md §6.2.3, the
error goldens (`closure_capture_local_var` becomes a run test), and the conversion guide's rule 23. Change both
compilers in the same commit, while they are kept in step.

**Done when.** A closure can capture and update a local `var` variable, in every phase and in compiled code; a
function that refers directly to a global `var` variable is a type error; and §6.2.3 states the paper's rule.

---

## Objects compiled with and without the collector share a build directory

**Problem.** A build's staleness check (`unit_staleness`) compares an object with its sources and imports, but not
with whether it was compiled for the collector, so a build with `--nogc` reuses objects that a build without it left
in the same build directory, and the reverse. The objects disagree about allocation, and the link fails (`_GC_init`
undefined) or the program mixes allocators. Both compilers do it.

**Reproduce.** In an empty directory holding `p.quest` (`1 + 1`), `./quest compile p.quest`, then `./quest compile
--nogc p.quest -o n`: the link fails. `./questc` fails the same way.

**Where to start.** `_unit_staleness` in `bootstrap/python/quest/build/engine.py` and `unitStaleness` in
`questlang/build/engine.mod.quest`. Record the collector setting in each unit's `.qm` and treat a unit as stale when
it differs (an ABI change, since the manifest format changes), or keep the two kinds of object apart, in a
subdirectory of the build directory for `--nogc`, as the runtime's objects already are by their flags.

**Done when.** Builds with and without `--nogc` can alternate in one build directory, in both compilers, and a test
does it.
