# Plan: Rethrowing Caught Exceptions

A plan for implementing [raised.md](raised.md) (2026-10-29): the binder `else with e then`, the library module
`raised` with `raised.T` and `raised.reraise`, and their tracebacks. The language changes go into both compilers
(the two-compilers policy, [testing.md](testing.md) §2.8); the native backend's part (step 5) is the self-hosted
compiler's alone.

Steps 1 and 7 are commits of their own. Steps 2 through 6 are one commit, since a golden test that uses the binder
runs in every phase of both suites, and none of them can pass until the whole pipeline handles it. Step 1 took the
next ABI version (56), since it changes the runtime header and the externals table. Each commit passes
`tools/check`.

**Status** (2026-10-29): steps 1 to 6 are done, unpushed until the arm64 plan is finished. Step 7 waits for them to be
pushed and for a release cut from them, since `questlang/` may use only what the current release compiles
([instructions.md](instructions.md) §6.1).

| Step | What | Compilers |
| --- | --- | --- |
| 1 | The `raised` module, its runtime functions, and the interpreters' builtins | both |
| 2 | Syntax: grammar, parsers, AST | both |
| 3 | Type checking: the binder's type, the typed AST | both |
| 4 | The interpreters: binding and raising again | both (4 interpreters) |
| 5 | The IR, the C backend, and the native backend | both; SSA and arm64 self-hosted |
| 6 | Tests and documentation, ABI bump | both |
| 7 | Using it in the self-hosted compiler | self-hosted |

---

## 1. The `raised` Module

- `lib/raised.int.quest` and `lib/raised.mod.quest` as raised.md §4.1 gives them: `T::TYPE` in the interface, and
  `Let T = external "QRaised *"` in the module, as `os/process` has its `T`.
- **Check first** that an importer's `raised.T` is the external type, so that it equals the type checker's built-in
  one (step 3): an importer's export scope gives such an abstract type its external definition
  (`create_module_export_scope`, `modules/elaboration.py`; `createModuleExportScope`, using the externals table for
  the library's modules, in `questlang/modules/elaboration.mod.quest`), but the interface's own signatures name the
  opaque type variable (`reraise`'s parameter), so a test must pass a value of the external type made elsewhere to
  `raised.reraise`. Until step 3 there is no such value in Quest; a unit test can build the type checker's constant
  and check it against the importer's `raised.T` and `reraise`'s parameter type in both compilers. If they differ,
  resolve the type variable to its definition where subtyping compares them.
- Runtime (`runtime/quest_runtime.h`, `.c`):
  - `typedef struct QRaised { QExceptionState state; } QRaised;`
  - `QRaised *quest_raised_capture(const QExceptionState *s)`: a heap copy (`quest_alloc`, as the payload may be a
    pointer).
  - `QVal quest_raised_reraise(const QTypeDescriptor *a, QRaised *r)`, `Q_NORETURN`: `quest_reraise(r->state)`.
  - `Q_CATCH_ALL_TRACED (-3)`: a handler that catches everything, into which `quest_raise_at` and `quest_reraise`
    capture frames before jumping (exceptions.md §5.1), as they do for `Q_CATCH_UNKNOWN`. It gets its own constant
    rather than reusing `Q_CATCH_UNKNOWN`, whose meaning ("might be caught") the handler chain's walk relies on.
- Interpreters' builtins: `quest_raised_reraise` in `bootstrap/python/quest/interpreter/builtins.py` and in
  `questlang/interpreter/builtins.mod.quest`, raising the held exception object (step 4 defines the values).
- `tools/externals`: regenerate the table. `raised.T` gains a `types` row; `reraise` has a type parameter, so it is not
  a `functions` row, and needs none (it is rare).
- `dynamic.extern` of a `raised.T`: confirm that it raises `dynamic.error`, as for other external types, in
  `values/dynamic_json.py`, `questlang/values/dynamicjson.mod.quest`, and `runtime/quest_serialization.c`.

Nothing can make a `raised.T` until step 3, so this commit's test is that the module builds and the externals table's
unit test passes.

## 2. Syntax

- `docs/grammar.txt`: `TryBranches` as raised.md §2 gives it.
- Bootstrap: `ExprTry` gains `else_binder: Optional[str]` and `else_binder_type: Optional[TypeExpr]`
  (`syntax/ast.py`); the parser (`syntax/grammar.py`) reads `with ide [":" Type] "then"` after `else` when the next
  token is `with`.
- Self-hosted: `exprTry` gains the same fields (`questlang/syntax/ast.int.quest`); the parser's grammar and actions
  (`questlang/syntax/parser/`) read the same, with the bootstrap's error text.
- The AST printers (`syntax/astprint`) show the binder.

## 3. Type Checking

- A constant for the type, `QExternalType(name="raised.T", c_type="QRaised *")`, beside the other primitive types
  (`types/model.py`; `questlang/types/model.mod.quest`).
- `_elaborate_try_expr` (`typechecker/exceptions.py`) and its port (`questlang/typechecker/exceptions.mod.quest`):
  with an `else` binder, check the annotation, if any, equals the constant; declare the binder, immutable, in a scope
  named `try_<name>` (already local for capture and global-`var` purposes, type-system.md §6.2.3); and elaborate the
  `else` branch in it.
- `TypedTry` gains `else_binder: Optional[ValueSymbol]` (`typechecker/typed_ast.py`; `typedast.int.quest`), and the
  typed AST printers, walkers, and scope-exception finders (`scope_exceptions`) visit it.
- `raise e end` with `e: raised.T` keeps the existing error; an error test pins its text (step 6).

## 4. The Interpreters

- Values: `QRaisedVal(exc: QuestException)` in `values/model.py`; `vRaised with model.RunError` (or the type the
  self-hosted interpreter's `model.runError` carries) in `questlang/values/model.int.quest`. Both display as
  `<hidden>` (`interpreter/formatting.py`, `questlang/interpreter/formatting.mod.quest`), as their type is opaque.
- Tree-walking interpreters (`interpreter/treewalk.py`, `questlang/interpreter/treewalk.mod.quest`): when no branch
  matches and the `else` has a binder, bind it to the caught exception object, wrapped, and run the branch.
- `quest_raised_reraise` (step 1) raises that object itself, so its offset and frames are kept, as a `TypedTry` whose
  branches do not match already does.
- The IR interpreters (`interpreter/ir_interp.py`, `questlang/interpreter/irinterp.mod.quest`) run step 5's new IR
  statement the same way.

## 5. The IR and the Backends

- A new IR operation, `CaughtException(exception)` (`caught_exception(e)`, `opCaughtException`), beside
  `ExceptionPayload`: the raised exception a `try`'s handler caught (`exception`, the `Try`'s variable), as a value of
  `raised.T`, bound by a `let`. (Planned as a statement; an operation like `ExceptionPayload` needed nothing new in
  the passes.)
- `ir.Try.catching` gains `CATCH_ALL_TRACED`, for a `try` whose `else` has a binder.
- Lowering (`ir/lower.py`, `questlang/ir/lower.mod.quest`): with a binder, the handler's `else` path is
  `let binder = caught_exception(exception)` then the branch; `catching` is `CATCH_ALL_TRACED`.
- Every pass that matches statements handles the new one: `walk`, `verify`, `specialize`, `printer`, `describe`
  (both compilers), the representation and closure passes in the self-hosted compiler where they enumerate
  statements.
- C printer (`codegen/c/printer.py`, `questlang/codegen/c/printer.mod.quest`): `dest = quest_raised_capture(&state);`
  and `Q_CATCH_ALL_TRACED` in `emit_catches`.
- Native backend (self-hosted): the SSA builder (`questlang/ssa/build.mod.quest`) turns `CaughtException` into a call of
  `quest_raised_capture` with the address of the handler's state slot (ssa.md: the state is already a stack slot,
  whose address `quest_reraise` gets); `ssac` and the arm64 code generator need nothing new beyond the call, and the
  catch kind in the handler record. Add the case to whichever arm64 step covers `try` if that step is not done yet
  when this lands ([arm64.md](arm64.md)).

## 6. Tests, Documentation, ABI

Tests, as behavior goldens shared by both suites, with error tests in `tests/errors/`:

- `tests/source/language/rethrow_unknown.quest`:
  - the `finally` idiom, with the cleanup run for an exception the handler does not know and for one it does;
  - the payload kept (an outer `when Fail with m` receives the original `m`);
  - library exceptions (`int.error`, `arrayOp.error`) passing through;
  - a value of `raised.T` stored, returned from a function, captured by a closure, and raised after its `try` has
    finished;
  - an `else` branch that raises and catches another exception before raising its own again;
  - `reraise` in checked and synthesized positions (`:A` written);
  - the annotated form `else with e: raised.T then`;
  - `stack.overflow` raised again, in the interpreters only (`@skip-phase: run_c_compiled`, as
    `stack_overflow_caught` does).
- Run errors (`tests/errors/run`): `rethrow_keeps_site`, an uncaught exception raised again whose `(* ERROR *)` line
  is the original raise's, in every phase that runs programs.
- Type errors (`tests/errors/typecheck`): `raise e end` with `e: raised.T`; an annotation other than `raised.T`;
  assigning to the binder.
- Syntax errors: `else with then`, `else with e` without `then`.
- `tests/python/test_tracebacks.py`: an uncaught exception raised again through `else with` has the original frames
  in every interpreter phase, and in compiled code a non-empty ordered subsequence ending with `<main>` that includes
  the raising function's frame when it was not inlined.
- The REPL: a transcript binding a raised exception to a top-level variable and showing it as `<hidden>`.

Documentation:

- [type-system.md](type-system.md): a §6.15 on the binder and `raised.T`, pointing to raised.md.
- [exceptions.md](exceptions.md) §3.1 and §5.1: `CaughtException`, `raised.reraise` as a re-raise, and
  `CATCH_ALL_TRACED`.
- [ir.md](ir.md): the new statement and catch kind; [ssa.md](ssa.md) if the builder's description lists statements.
- raised.md loses its "This document specifies an extension" framing and becomes the reference.

ABI: bump `ABI_VERSION` (`bootstrap/python/quest/config/abi.py`, `questlang/config/abi.mod.quest`) and refresh the
corpus. The arm64 work bumps the ABI often; rebase just before committing and take the next free number.

## 7. Using It

Replace the hand-written idiom (raised.md §1) in the self-hosted compiler, where it misses exceptions it does not
list: `flushingLog` (`questlang/build/engine.mod.quest`), `loading` (`questlang/modules/loader.mod.quest`), `inScope`
(`questlang/modules/elaboration.mod.quest`), and the scope swap in `questlang/types/env.mod.quest`. The bootstrap
needs nothing: it uses Python's `try`/`finally`. If the four sites end up alike, that is the case for adding
`raised.ensure` (raised.md §7), which is not part of this plan.

---

## Decisions

Settled (2026-10-29):

- The names `raised`, `Raised`, and `raised.T`, and `raised.reraise` for the rethrow (a verb, and the name the IR,
  the runtime, and exceptions.md already use for the operation).
- An abstract `T` in the interface, defined as an external type in the module.
