"""The Quest bootstrap compiler, in Python: the secondary compiler, which
builds stage 1 of the self-hosted compiler in questlang/ (the primary one) when
there is no release, and which ./questboot runs. Its subpackages and modules
are imported by name; the package exports nothing itself. Importing it
imports the type checker, which registers its binding elaborator with
quest.modules.elaboration, which needs it.

- quest.syntax: tokens, the tokenizer, the parser, the AST, and desugaring
- quest.types: types, kinds, environments, subtyping, and type printing
- quest.typechecker: type elaboration and the type checker, producing the
  typed AST
- quest.modules: modules, interfaces, imports, and separate compilation
- quest.values, quest.interpreter: values, the tree-walking interpreter, and
  the IR interpreter
- quest.ir: the intermediate representation and its passes (docs/ir.md)
- quest.codegen: layouts and the C backend, which prints the IR as C
- quest.build: whole-program and multi-module builds
- quest.config: compiler options and the artifact ABI
- quest.testing: the golden test runner
- quest.driver: the command line (quest_driver.py runs it), and the REPL
- quest.common: diagnostics, and locations in sources
- quest.pipeline: the compiler's phases (docs/pipeline.md)

docs/compiler-organization.md describes the self-hosted compiler's modules and
the bootstrap module each follows.
"""

# For its side effect: the type checker registers its binding elaborator
import quest.typechecker.typecheck  # noqa: E402,F401
