# questlang/interpreter: running Quest without compiling it

This directory holds the self-hosted compiler's two interpreters. The **tree-walking interpreter** runs a type-checked
program directly from the typed AST that `questlang/typechecker` produces; the **IR interpreter** runs the IR that
`questlang/ir` lowers that program to, at any of its stages. Neither produces machine code: both compute values of
[`questlang/values`](../values/README.md) and print them as compiled code would. By default the driver compiles a
program, an `-e` expression, or a REPL input with the JIT (`questlang/jit`) and runs the machine code; the tree-walker
runs them instead under `--no-jit`, in the `interpret` test phase, and wherever the driver cannot host the JIT. The IR
interpreter is a test oracle: the `run_ir_<stage>` phases run every test program's IR after each pass and compare its
output with what the program is supposed to print, so that a pass that changes a program's meaning fails at that
pass, before any code is generated.

Everything here mirrors the bootstrap's `bootstrap/python/quest/interpreter/` module for module, and the two must
print the same output and the same errors for every program (the shared run goldens, `tests/golden/run/`).

## The tree-walking interpreter

[`treewalk.mod.quest`](treewalk.mod.quest) is the most direct reading of the typed AST: `evalExpr` has a case per
expression form and evaluates subexpressions recursively, so the interpreter's own stack serves as the program's.
Its environment is a chain of frames (`model.Frame`), each mapping names to values. Plain names suffice, without the
type checker's symbols, because the checker has already resolved every name; a binding that rebinds a name already
in its frame gets a fresh frame, so that closures made before it keep what they captured. A function value is a
closure holding its parameter names, its body, and the frame it was made in.

Control flow that is not expression evaluation uses Quest's own exceptions. `exit` raises a private `loopExit` that
the nearest loop catches. A Quest `raise` raises `model.runError`, carrying the exception value and its payload,
which the nearest `try` with a matching branch catches; one that nothing catches propagates out of the interpreter
and is reported with its raise site and the frames that were running (the interpreter keeps a call stack of frame
names for that, [docs/exceptions.md](../../docs/exceptions.md) §4). A call depth limit turns runaway recursion into
the `stack.overflow` exception compiled code raises.

Types are mostly erased, but a few operations need them at run time: `inspect`, auto values, `dynamic.be`, and the
printing of results. So a polymorphic function's type arguments travel with it. A type application such as
`list.nil(:Int)` binds the next type parameters in a copy of the closure (`instantiate`); the body then runs with
those bindings in its frame, and `resolveType` substitutes them into any type the body consults. A function whose
only parameters are type parameters, a polymorphic constant, runs as soon as it is applied to all its types.

Imports are run on demand. `loadModuleForInterpreter` resolves an import through the type checker's unit graph,
runs the module's typed body once in a frame of its own, and caches the resulting record of exports by the module's
canonical name. The REPL keeps one root frame across inputs and uses `snapshot` and `restore` to roll back an input
that fails.

## The IR interpreter

[`irinterp.mod.quest`](irinterp.mod.quest) runs a `nodes.Unit` of the IR ([docs/ir.md](../../docs/ir.md)). The IR is
in A-normal form (every intermediate result named) and uses *join points*, local continuations reached by `jump`,
instead of nested expressions, so the interpreter is statement-based: a statement either falls through or yields a
signal (`sigReturn`, `sigJump`, `sigBreak`, `sigContinue`) that enclosing statements pass outward until one handles
it. Raises still travel as `model.runError`, as in the tree-walker. Because one interpreter covers every stage, it
also follows the IR's changing shape: after closure conversion a closure is built from explicit captures, with
fix-ups for a `let rec` whose functions capture each other; from the described stage on, operations carry type
descriptor operands, which the interpreter evaluates to types and checks against the types they stand for, so a
wrongly built descriptor fails here too.

The two interpreters share values and call each other. A unit's imports, the standard library included, are loaded
and run by the tree-walker, and an IR function is a builtin to the tree-walker, so library code written in Quest can
call back into IR code.

## What the two share

[`primitives.mod.quest`](primitives.mod.quest) defines the standard library's exceptions as interpreted values
(`int.error`, `string.error`, ...) and integer and real arithmetic and comparison, implemented with Quest's own
operators, so that a division by zero, say, raises what compiled code raises. The operators are options
(`Arithmetic`, `Comparison`): the tree walker finds them by their spellings (`infixOf`), and the IR interpreter by an
exhaustive case over its primitives. The two also share what `opt!tag` gives for an option (`optionComponents`) and
the bound an index, an indexed store, or an element's address must be within (`inBounds`). `sameAt` is Quest's `is`
at a known static type, which for options compares by case ([docs/extensions.md](../../docs/extensions.md)).

[`builtins.mod.quest`](builtins.mod.quest) gives the meaning of every `external "symbol"` that `lib/` declares.
Since this interpreter is itself compiled Quest, each entry calls the library function the symbol names and wraps its
result: `quest_string_get_char` is `stringOp.getChar`. The native function's semantics are therefore exactly compiled
code's, and an error the library raises (`stringOp.error`) is caught and re-raised as the interpreted exception the
program's `try` expects. Only operations on interpreted values themselves are written here: `dynamic.copy`,
`extern`, and `intern` (through `questlang/values`' reader and writer), identity hashing, and `system.args`.
[`filecalls.mod.quest`](filecalls.mod.quest) exposes the runtime primitives behind `os/files`, which that module keeps
private, so that the builtins return the status codes compiled code receives.

[`literals.mod.quest`](literals.mod.quest) marks a string literal read-only as both interpreters first evaluate it,
as compiled code's static literals are marked, so that `string.setChar` on one raises `string.error`; the builtins'
`quest_string_freeze` uses it too.

[`formatting.mod.quest`](formatting.mod.quest) prints a value as its static type shows it, as Cardelli specifies:
a value of an abstract type prints as `<hidden>`, a function as `<fun>`, and a record shows only the fields of the
type it is seen at. It also writes a top-level phrase's result in the interactive notation the REPL and `--echo` use:

```
>>  let total = 1 + 2
==  let total:Int = 3
```

## Connections

The driver (`questlang/driver/main.quest`) builds a root frame with `treewalk.newRoot` and calls
`evalProgramPhrasesIn` for `--no-jit` runs, or `irInterp.runUnit` for the `run_ir_<stage>` phases;
`questlang/driver/repl` and the Jupyter kernel (`questlang/driver/kernel`) use the tree-walker the same way. The
interpreters read the typed AST (`questlang/typechecker/typedAst`), types (`questlang/types`), the unit graph and
module elaboration (`questlang/modules`), and the IR (`questlang/ir/nodes`). Nothing in compilation depends on this
directory. The bootstrap's counterpart, written in Python, is
[`bootstrap/python/quest/interpreter`](../../bootstrap/python/quest/interpreter/README.md).

## Further reading

- [docs/interpreter.md](../../docs/interpreter.md): the interpreter's values, evaluation rules, and semantic decisions.
- [docs/repl.md](../../docs/repl.md): the REPL, which runs inputs in the JIT or, with `--no-jit`, here.
- [docs/jit.md](../../docs/jit.md) §4: where the JIT is allowed to differ from the interpreter.
- [docs/testing.md](../../docs/testing.md) §2.3: the `interpret` and `run_ir_<stage>` phases.
- [docs/exceptions.md](../../docs/exceptions.md) §3.2 and §4: raise sites and frames in the interpreters.
- [docs/compiler-organization.md](../../docs/compiler-organization.md) §6: where the self-hosted interpreter differs
  from the bootstrap's internally.
