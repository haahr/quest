# Plan: Tail Calls in the Interpreters

All four interpreters run a call in tail position without adding a call to those active:
- the tree-walkers, `bootstrap/python/quest/interpreter/treewalk.py` and `questlang/interpreter/treewalk`;
- the IR interpreters, `ir_interp.py` and `questlang/interpreter/irinterp`.

So does a run through `-i`, the REPL, and the Jupyter kernel. A tail-recursive loop then runs to any depth, where
today it stops at 1000 active calls with `stack.overflow` ([benchmarks.md](benchmarks.md) §3.9).

This is not a language guarantee. The compiled backends keep what they do now:
- arm64 and WebAssembly make tail calls "whenever possible" ([arm64.md](arm64.md) §3.7, [wasm.md](wasm.md) §3.3);
- C leaves them to clang.

Nothing in the language, the typechecker, the IR, or the SSA changes.

Both compilers change, under the two-compilers policy. The behavior goldens stay shared and are written by the
bootstrap. Each step does one compiler's interpreter of one kind, and each interpreter stays the other compiler's
counterpart line for line, as it is now.

## 1. The rule

A call is in tail position when its value is the calling function's value, with nothing left to do after it in that
function. In the source, that is a call that is:

- a function's body;
- the result of a block in tail position;
- a branch (then, elsif, or else) of an `if` in tail position;
- a branch or the `else` of a `case` or `inspect` in tail position.

Nothing else is a tail position:
- a `try`'s body or handlers, because the handler has to stay active while the call runs;
- a loop's body;
- an operand, an argument, or a binding's value;
- the condition of an `if` or the target of a `case`;
- a module's initializer, or a phrase at the top level.

In the IR, a tail call is a `let v = call ...` followed directly by `return v`, where:
- `v` is not one of a `letrec`'s declared variables;
- the statement is not inside a `try` statement's body.

A return inside a loop's body leaves the function, so a call there can be a tail call in the IR. That never happens
in the source.

These calls qualify:
- calls of closures, direct or through a value;
- calls of a module's members;
- a type application that runs its closure's body (treewalk's "whether applying the closure to types runs it").

A call of an external (`TypedExternal`, `CallExternal`, a builtin) runs as it does now. It makes no Quest call that
stays active.

## 2. The mechanism: a trampoline at the call boundary

Two things the interpreters already do make this easy:
- they keep a call's variables in heap-allocated scopes (`push_scope`, IR `_Frame`), not on the host's stack;
- they keep the frames they report in a list of their own (`call_stack`, `root.callStack`).

So a tail call does not need a new activation. The interpreter does this instead:
- the call evaluates its callee and arguments, then returns a pending call instead of running it;
- the function call that is running (`run_closure`/`runClosure`, IR `apply`) loops while a call is pending.

Each turn of that loop does what one call does now:
- checks the depth limit;
- checks for an interrupt (self-hosted);
- replaces the frame name on top of the call stack with the new closure's;
- binds the type arguments and arguments in a fresh scope or frame;
- runs the body.

An error raised in the loop is located in the file of the closure running then, not the first one's
([exceptions.md](exceptions.md) §3.2). The call stack is popped once, when the loop ends.

The pending call must never reach a position that is not a tail position. It is represented as follows:

- **Tree-walkers.** `eval_expr`/`evalExpr` take a tail flag, false by default. Only the forms in §1 pass it on to
  their parts.
  - In Python, the pending call is a private sentinel object: a `_TailCall` holding the closure and the arguments.
  - In Quest, a pending-call slot on the frame's root holds the closure and the arguments. That avoids a new `Value`
    variant, which would reach formatting, equality, and the builtins.
- **IR interpreters.** `body` returns the signal `("tailcall", callee, args)` in Python, and the matching signal in
  Quest, next to `("return", v)`. `apply` loops on it.

**Calls between the two kinds of interpreter.** Functions the IR interpreter runs (the unit's) and functions the
tree-walker runs (the imported modules') can call each other. A tail call from one kind to the other stays an ordinary
call: the loop of the callee's kind runs it, and the caller's frame stays active. Making it a tail call too would need
one loop shared by both kinds. That is left out unless a test shows a program that needs it.

## 3. What changes, visibly

- **Tracebacks.** An exception that ends a program, or that the REPL reports, no longer lists the frames of functions
  that called in tail position.
  - Compiled code already drops such frames, which [exceptions.md](exceptions.md) §2.4 accepts. Whatever is listed
    stays in the interpreters' order and ends with `<main>`.
  - All four interpreters drop the same frames. Goldens that change are regenerated and reviewed in the step that
    changes them.
- **stack.overflow.** It still comes at 1000 active calls, for recursion that is not a tail call. The test
  tests/source/language/stack_overflow_caught.quest (`1 + down(n + 1)`) is unchanged.
- **Benchmarks run interpreted.** Most of the MLton conversions recurse in positions that are not tail positions
  (§3.9). This plan alone probably does not make the suite run in an interpreter. Step 5 counts which programs it does
  make run.

## 4. Steps

0. **Tests first.** Add `tests/source/language/tail_calls.quest`, with each loop 100000 deep:
   - a self tail call;
   - mutual tail calls;
   - a tail call through a closure value;
   - a tail call through a block, `if`, `case`, and `inspect`;
   - a tail call of a module's member;
   - a tail call of a type-parameterized function.

   Add the counterparts that must still overflow in the interpreters:
   - a call in a `try`'s body;
   - a call in a loop's body that recurses;
   - a call as an operand.

   Add one uncaught exception raised after tail calls, for the traceback. Choose depths whose non-tail cases overflow
   in the interpreters but stay within the native stack in every compiled backend. Otherwise, skip those phases, as
   stack_overflow_caught.quest does.

   With today's interpreters, the deep cases fail. Their expected output is written by hand in this step, and the
   goldens are checked in once step 1 passes them.
1. **Bootstrap tree-walker** (treewalk.py): the tail flag, `_TailCall`, and the loop in `run_closure`. Write the shared
   run golden from it. Its `--phase run` tests and the REPL goldens pass, with any traceback goldens regenerated.
2. **Self-hosted tree-walker** (treewalk.mod.quest): the same, with the pending slot on the frame's root. The
   self-hosted run phase passes the same goldens.
3. **Bootstrap IR interpreter** (ir_interp.py): the `tailcall` signal and the loop in `apply`. Every run_ir phase
   passes.
4. **Self-hosted IR interpreter** (irinterp.mod.quest): the same, so that every run_ir phase passes in the self-hosted
   compiler too.
5. **Docs and counts.**
   - [interpreter.md](interpreter.md): the rule and the mechanism. This plan's content moves there, and the plan is
     deleted.
   - [exceptions.md](exceptions.md) §2.4 and §4: the interpreters drop the frames of functions that called in tail
     position.
   - [benchmarks.md](benchmarks.md) §3.9: which MLton programs now run interpreted, and which still overflow.
6. **Check.** tools/check, then commit. Ready to push.

**Done when** the tail_calls test passes in every interpreter and every backend, its overflow counterparts still
overflow in the interpreters, and tools/check passes.
