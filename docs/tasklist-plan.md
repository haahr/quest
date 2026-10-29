# Plan: The Remaining Tasks

A plan for the three tasks left in [tasklist.md](tasklist.md) (2026-10-28), in the order to do them, with the decisions
each needs from the owner. Each step is a commit (or a few) and passes both suites; each task's entry leaves the task
list in the commit that finishes it.

| Order | Task | Kind | Compilers | Decision |
| --- | --- | --- | --- | --- |
| 1 | Type application (type-only functions with function results; partial) | correctness | both | semantics (§1.1) |
| 2 | Capture rules for `var` variables as the paper has them | language | both | ban global `var` use? (§2.1) |
| 3 | Faster word operations in compiled code | optimization | self-hosted | finding externals (§3.1) |

**Why this order.** Correctness before speed, and language changes before optimizations:

- Task 1 is the smallest, fixes programs that fail to compile today, and settles what type application means, which
  both later tasks build on: the interpreters, the type checker, and the lowering are the parts it touches.
- Task 2 changes the language in both compilers, which must stay in step for it, and changes how closures hold
  variables (a captured `var` becomes a shared cell). Doing it before task 3 means the optimization is measured on the
  closure representation that stays, and the code task 2 rewrites (the benchmarks' and tests' global variables) is
  rewritten once.
- Task 3 is an optimization, so it goes into the self-hosted compiler alone (testing.md §2.8; the task's text, which
  asks for both, predates that policy), and is measured against the benchmark baseline
  ([benchmarks.md](benchmarks.md)) once nothing else is changing the generated code.

---

## 1. Type Application

**Facts.** The implementation identifies a curried polymorphic type with the uncurried one: `let g(A::TYPE x: A): Int`
and `let f(A::TYPE)(x: A): Int` both have the type `All(A :: TYPE) Fun(x: A): Int`, and either can be bound to a
variable declared with the other's written type. About 400 definitions in `lib/`, `questlang/`, and the benchmarks are
curried in their type parameters, and the C backend compiles every value of such a type as one function taking the
type descriptors and the value arguments together. So a function of type parameters only whose result is a function
(`let h(A::TYPE): All() Int = ...`) has the type of a function of type parameters then value parameters, and no
representation can tell the two apart from the type. Today the lowering rejects such functions (the task).

Found while planning: **partial type application** is broken too. Given `let g(A::TYPE B::TYPE): Int`, `g(:Int)` type
checks (as `All(B :: TYPE) Int`), but compiled code calls `g` with one descriptor where it takes two (clang rejects the
C), and both interpreters run `g`'s body at the partial application instead of at `h(:Bool)`. A curried definition
whose inner function has type parameters, `q(A::TYPE)(B::TYPE)`, is the same case.

### 1.1. Decision: what a type-only function with a function result does

- **(a) Recommended: it is the merged function.** The type checker turns `fun(A::TYPE) e`, where `e`'s type is
  `All(params) R`, into `fun(A::TYPE)(params) e(params)`: the function of type parameters then the result's parameters,
  whose body computes `e` and applies it. This follows from the type identity: a value of that type behaves like any
  other. What the body does before it yields the function happens at each call rather than once at type application.
  Programs that depend on the difference are rare (none in the tree), and the interpreters and the compilers agree
  because the change happens before either sees the program.
- (b) Reject such functions in the type checker, with a message pointing to the curried form. Simpler, but rejects
  programs the paper accepts.
- (c) Give type-only functions a representation of their own. Not possible without separating the curried and
  uncurried types, which changes the type system and the ~400 definitions' calling convention.

### 1.2. Steps

1. **Partial type application in the interpreters.** A type application runs a type-only closure only when all its type
   parameters are bound (the IR interpreter already checks this). Run test: `g(:Int)` then `h(:Bool)` prints the body's
   output after the partial application. *Done when* the test passes in `interpret` and the `run_ir_*` phases, in both
   suites.
2. **Partial type application in compiled code.** A type application with fewer type arguments than the callee's type
   takes makes a closure that holds the given descriptors and, applied to the rest (and the value arguments), calls the
   callee with all of them, as the represent pass's instance closures do for conversions. In both compilers' lowering
   and represent passes. *Done when* the step 1 test runs compiled with the same output, and `tools/c-diff` shows no
   change to the C of any other program.
3. **The decision of §1.1** in both type checkers (`_check_polymorphic_fun_expr` and `_check_fun_expr`, and their
   ports in `questlang/typechecker/bindings`). With (a), the rewritten function is no longer type-only, so the lowering
   check from d0a82d83 never fires; remove it. *Done when*
   `tests/source/language/type_only_functions_returning_functions.quest` runs in every phase (its skips removed, and
   its golden updated to the agreed semantics), and type-system.md describes type application.

---

## 2. Capture Rules for `var` Variables

**Facts.** No module in `lib/` or `questlang/` has a module-level `let var`. The benchmarks have 41 top-level ones and
the tests 48, some of them used directly by functions. The REPL's idiom of a top-level `let var` updated by a function
is one of them.

### 2.1. Decision: both halves of the paper's rule, or only the first

The task's *done when* asks for both: (i) closures may capture local `var` variables, and (ii) functions may not refer
directly to global `var` variables. (i) only accepts more programs. (ii) rejects programs that work today: some of the
89 top-level variables above, and REPL sessions that update a global from a function. **Recommended:** do (i), then
(ii) in its own commit after the audit, so (ii) can be dropped or deferred without undoing (i). The plan assumes both.

### 2.2. Steps

1. **Capture of local `var` variables** (both compilers, one commit). `_check_capturable` allows a local `let var`
   (still not `var` and `out` parameters). Closure conversion (`ir/closure`) holds a captured mutable local in a cell
   the frame and the closure share, as `location_representation` already does for a local whose address is taken; its
   `capturesMutable` error goes away. Both interpreters already share frames with closures; check that each does.
   `tests/errors/typecheck/closure_capture_local_var.quest` becomes a run test, with cases for a counter closure, two
   closures sharing a variable, a capture in a loop, and a captured variable updated after the closure is made. *Done
   when* those run in every phase, and type-system.md §6.2.3, codegen-c.md §10.8, and the conversion guide's rule 23
   say so.
2. **Simplify the conversions** that hold an SML `ref` in a tuple only because a closure captured it (the benchmarks'
   conversions note it). *Done when* `run.py check` passes for every benchmark changed. Optional; worth doing where it
   makes a conversion closer to its original.
3. **Audit global `var` use**: list each function in `lib/`, `questlang/`, `benchmarks/`, `tests/`, and `examples/`
   that refers directly to a global `var` variable, and the REPL transcripts that do. *Done when* the list is in this
   plan, with how each use will be rewritten (an own variable, or a parameter).
4. **Forbid direct use of global `var` variables** (both compilers, one commit), rewriting the audited uses. A function
   refers to a global `var` variable only through parameters or data structures. Error tests for a direct read and a
   direct assignment. *Done when* both suites pass, every benchmark's `run.py check` passes, and §6.2.3 states the
   paper's rule.

---

## 3. Faster Word Operations

**Facts.** A `word` operation costs three calls (wrapper, module-record closure, runtime function), none inlinable.
The same holds for every external in `lib/`: about 150 external declarations across 17 modules (`real` 29, `word` 26,
`system` 16, `string` 15, ...). [benchmarks.md](benchmarks.md) §3.3 measured link-time inlining at 1.67 times faster
for md5 and 1.43 for checksum.

### 3.1. Decision: how an importer learns that a member is an external

- **(a) Recommended: the interface artifacts record it.** The `.qi` records, for each member a module defines as
  `external "symbol"`, its C symbol, and a call of that member through the module compiles to a direct call. An ABI
  change, general to every library module. Unsafe only if a module could be swapped for another implementing the same
  interface without recompiling importers; Quest's build already recompiles importers when a `.qi` changes.
- (b) The backend knows `word` (and others) as builtins: no ABI change, but a list to keep in step with `lib/`.

### 3.2. Steps

1. **Direct calls of external members** (self-hosted only; ABI bump; corpora regenerated). *Done when* the self-hosted
   suite passes, `tools/c-diff` shows calls of `quest_word_*` and the other externals in place of `qv_*` wrappers, and
   the bootstrap still builds and runs programs against the new runtime header (the bootstrap keeps its own calls).
2. **Inline the small ones**: the word operations that are one C operator (`^`, `|`, `&`, `<<`, ...) become `static
   inline` functions in `runtime/quest_runtime.h`, so a direct call compiles to the operator. *Done when* md5,
   checksum, and the compiler's own build are timed against the baseline and the results are recorded in
   benchmarks.md (expected: most of §3.3's gain, and the 7.5% of the compiler's time the task measured).
3. **Native SHA-256** for `layout`'s digests, as the task suggests: a runtime primitive, so `questlang/` can use it only
   after a release has it. Optional; measure step 2 first.
