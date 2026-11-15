# bootstrap/python/quest/interpreter: the bootstrap's interpreters

This package runs Quest programs in Python, without compiling them. It is the bootstrap compiler's counterpart of
[`questlang/interpreter`](../../../../questlang/interpreter/README.md), which introduces the ideas in full; the two
have the same modules and must produce the same output and errors for every program. The bootstrap has no JIT, so
here the **tree-walking interpreter** is what runs every program, `-e` expression, and REPL input that is not
compiled to C: the `interpret` test phase, `./questboot` running a program, and the bootstrap's REPL
(`../driver/repl.py`). The **IR interpreter** is the same test oracle as the self-hosted one, running the IR after each
stage in the `run_ir_<stage>` phases.

The bootstrap's interpreters matter more than their size suggests: the bootstrap writes the shared run goldens
(`tests/golden/run/`) that every backend of both compilers is checked against, so its tree-walker is in effect the
executable specification of what a program prints ([docs/testing.md](../../../../docs/testing.md) §2.8).

## The modules

- [`treewalk.py`](treewalk.py) evaluates the typed AST (`eval_expr`, `eval_binding`, `eval_program_phrases`) in a
  chain of `RuntimeEnvironment`s, the bootstrap's frames. Polymorphic functions carry their type arguments at run
  time for `inspect`, auto values, and printing; imported modules are run once each by
  `load_module_for_interpreter`.
- [`ir_interp.py`](ir_interp.py) runs a lowered `ir.Unit`: statements return `None` to fall through or a signal for
  `return`, `jump`, `break`, or `continue`, and from the described stage on it checks that each descriptor operand
  describes the type it stands for.
- [`primitives.py`](primitives.py) has the arithmetic with compiled code's semantics (C's truncating division,
  `real.error` for a NaN), the standard library's exceptions, and the interpreter's own error, `QuestRuntimeError`.
- [`formatting.py`](formatting.py) prints a value as its static type shows it, and a top-level result in the REPL's
  interactive notation.
- [`builtins.py`](builtins.py) implements every `external "symbol"` of `lib/` (`resolve_external_symbol`).

## How it differs from the self-hosted interpreters

- **The standard library's externals are reimplemented in Python.** The self-hosted interpreter, being compiled
  Quest, calls the native library function a symbol names; the bootstrap has no such library, so `builtins.py`
  writes each one in Python and must match the C runtime's behavior by hand. Strings are Python `str`s holding one
  byte per character (Latin-1), and `use_byte_streams` makes the standard streams read and write that way.
- **Values are a Python class hierarchy,** `QValue` and its subclasses in
  [`quest.values.model`](../values/README.md), rather than one `Option` type.
- **Control flow uses Python exceptions:** `_LoopExit` for `exit`, and `QuestException` (a Quest exception) and
  `QuestRuntimeError` (an error of the interpreter) for raises, both `QuestCompilerError`s. The self-hosted
  interpreter folds these into one `model.runError`.
- **Recursion uses Python's stack,** whose limit is raised so that the shared limit of 1000 active calls
  (`MAX_CALL_DEPTH`) raises `stack.overflow` before Python's own limit is reached.

Compilation does not import this package (`tests/python/test_dependencies.py` checks this), so the bootstrap can
build the self-hosted compiler without it.

## Further reading

- [docs/interpreter.md](../../../../docs/interpreter.md): this interpreter's values, environments, and evaluation
  rules.
- [docs/repl.md](../../../../docs/repl.md): the REPL built on it.
- [docs/testing.md](../../../../docs/testing.md) §2.3: the `interpret` and `run_ir_<stage>` phases.
- [docs/compiler-organization.md](../../../../docs/compiler-organization.md) §6: differences from the self-hosted
  interpreter.
