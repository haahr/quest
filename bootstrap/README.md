# bootstrap: the Quest compiler in Python

The bootstrap is a second, independent implementation of Quest, written in Python. `./questboot` runs it
([`python/quest_driver.py`](python/quest_driver.py) is the entry point). It is not the compiler people use day to day;
that is the self-hosted compiler in [`questlang/`](../questlang/README.md). It exists for three reasons:

- **To rebuild from nothing.** The self-hosted compiler is written in Quest, so compiling it needs a Quest compiler.
  Normally an earlier release of itself does that ([release-compiler.md](../docs/release-compiler.md)); with no
  release, the bootstrap compiles the self-hosted compiler's sources into a first working stage, which then compiles
  itself.
- **To write the shared goldens.** For every front-end phase and every program's output, the two compilers must
  agree. The bootstrap writes the expected outputs (`run_tests.py --update-golden`), and the self-hosted compiler's
  suite is checked against them ([testing.md](../docs/testing.md) §2.8).
- **As a readable reference.** The self-hosted compiler was ported from it module for module, so the bootstrap is a
  compact, dynamically typed rendering of the same design, often the quickest way to see what a phase does.

## What it does, and what it leaves out

The bootstrap has the whole front end: tokenizer and PEG parser, desugaring, the bidirectional type checker over
Cardelli's type system, and the module system with separately compiled interfaces. It has the tree-walking interpreter
and the IR pipeline through representations and runtime descriptors, and a C backend; compiled programs link the same
C runtime ([`runtime/`](../runtime/README.md)) as the self-hosted compiler's.

It has none of the self-hosted compiler's optimizations or native code: no simplifier or inliner, no SSA, no arm64
backend, no JIT. Its C is therefore slower than what `./quest` produces, and its build compiles modules one at a time.
Changes to the language, the library, or the behavior of programs are made in both compilers; optimizations and other
changes to how code is compiled are made in the self-hosted compiler alone.

## Layout

The package [`python/quest/`](python/quest) mirrors [`questlang/`](../questlang/README.md) directory for directory, a
Python module's name lowercased with its underscores removed in Quest (`ir/verify_core.py` here, `ir/verifycore` there).
Each directory with a README introduces its stage and how it differs from the self-hosted counterpart:

- the front end: [`syntax/`](python/quest/syntax/README.md), [`types/`](python/quest/types/README.md),
  [`typechecker/`](python/quest/typechecker/README.md), [`modules/`](python/quest/modules/README.md);
- running directly: [`interpreter/`](python/quest/interpreter/README.md) over
  [`values/`](python/quest/values/README.md);
- compiling: [`ir/`](python/quest/ir/README.md), [`repr/`](python/quest/repr/README.md),
  [`codegen/c/`](python/quest/codegen/c/README.md), and [`build/`](python/quest/build/README.md), which compiles a
  program's modules and links them;
- the command line: [`driver/`](python/quest/driver/README.md) and [`pipeline.py`](python/quest/pipeline.py), which
  defines the phases a program passes through and runs them in order;
- the test runner behind `run_tests.py`: [`testing/`](python/quest/testing/README.md).

[`common/`](python/quest/common) (source locations and diagnostics) and [`config/`](python/quest/config) (the ABI
version and compiler options) are small enough to need no introduction.

## Further reading

- [compiler-organization.md](../docs/compiler-organization.md) §6: how the two compilers differ inside.
- [pipeline.md](../docs/pipeline.md): the phases and `./questboot`'s options.
- [instructions.md](../docs/instructions.md) §4: the conventions for the bootstrap's Python.
