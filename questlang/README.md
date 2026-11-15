# questlang: the self-hosted Quest compiler

This directory is the Quest compiler written in Quest: the primary implementation, which compiles itself. `./quest`
runs it. One program, [`driver/main.quest`](driver/main.quest), holds a compiler with three ways to run what it
compiles: a tree-walking interpreter, a JIT that compiles to arm64 machine code in memory and runs it, and ahead-of-time
backends that write C or arm64 assembly and link a binary. The Python compiler in [`bootstrap/`](../bootstrap/README.md)
does the same front-end work and exists so that this one can be rebuilt from nothing.

## How it is built

The compiler is a Quest program like any other, so something must compile it first. Normally that is a *release*: a copy
of an earlier build of this compiler kept in `.git/quest-release` ([release-compiler.md](../docs/release-compiler.md)).
`./quest` has the release compile this tree into *stage 1*, then has stage 1 compile the tree again into *stage 2*,
which is the compiler that runs. Stage 2 compiling the tree writes the same files stage 1 wrote, byte for byte: the
compiler is at a *fixed point*, which the test suite checks ([testing.md](../docs/testing.md) §4.1). Because stage 1 is
the release's work, it is built against the release's own standard library, so code here can use a new library function
only once a release includes it.

## The flow of a program

A program passes through the same front end whichever way it runs, and through a series of intermediate
representations, each a little closer to the machine, when it is compiled:

```
source text
  │  syntax/        tokens, then an abstract syntax tree; derived forms rewritten (desugaring)
  ▼
  │  typechecker/   bidirectional type checking against types/' model of types; the result is a typed AST,
  │  types/         every name resolved and every expression annotated with its type
  │  modules/       imports resolved to interfaces (.int.quest) and their compiled forms (.qi)
  ▼
typed AST ──────────────► interpreter/ + values/   (--no-jit: walk the tree)
  │  ir/            lowered to the IR, then simplified (inlining), specialized, closure-converted,
  │  repr/          given machine representations, and given runtime type descriptors
  ▼
IR ─────────────────────► codegen/c/                (C text, compiled by clang)
  │  ssa/           translated to SSA form and optimized (escape analysis, value numbering, tail calls ...)
  ▼
SSA ────────────────────► codegen/arm64/ + machine/ (arm64 assembly: the default)
                          jit/                      (the same arm64 code, encoded and loaded in memory)
```

Every compiled program links against the C runtime in [`runtime/`](../runtime/README.md): object layouts, the garbage
collector, exceptions, and the standard library's primitives.

The driver can stop after any of these phases and print what it has (`./quest --stop-after typecheck file.quest`,
`--stop-after ir_closed`, `--stop-after ssa`, `--stop-after codegen_arm64`), which is how the golden tests check each
stage and the best way to see what a stage does ([pipeline.md](../docs/pipeline.md)).

## The directories

**Foundations.** [`common/`](common/README.md) holds what every layer uses: source locations, diagnostics, files and
paths, JSON, hashing.

**The front end.** [`syntax/`](syntax/README.md) turns text into an abstract syntax tree, with a data-driven PEG parser
in [`syntax/parser/`](syntax/parser/README.md). [`types/`](types/README.md) is the model of Quest's types: subtyping,
kinds, the evaluation of type operators, and the environments that bind names. [`typechecker/`](typechecker/README.md)
checks each construct and produces the typed AST. [`modules/`](modules/README.md) finds, loads, and elaborates
interfaces and modules, and [`modules/artifacts/`](modules/artifacts/README.md) writes and reads their compiled forms.

**Running without compiling.** [`interpreter/`](interpreter/README.md) evaluates the typed AST directly, over the
values of [`values/`](values/README.md), which also defines the dynamic (self-describing) values the language exposes.

**The middle end.** [`ir/`](ir/README.md) is the intermediate representation and its passes, from the first lowering
to closure-converted, representation-annotated code. [`repr/`](repr/README.md) decides how each type is laid out in
memory and what runtime descriptors it needs.

**The back ends.** [`ssa/`](ssa/README.md) turns the IR into SSA form ([`ssa/build/`](ssa/build/README.md)) and
optimizes it ([`ssa/passes/`](ssa/passes/README.md)). [`codegen/`](codegen/README.md) chooses a backend per unit:
[`codegen/c/`](codegen/c/README.md) prints C from the IR; [`codegen/arm64/`](codegen/arm64/README.md) selects arm64
instructions from the SSA, using the register allocator and instruction model of
[`codegen/machine/`](codegen/machine/README.md). [`jit/`](jit/README.md) uses the arm64 backend to compile and load code
inside the running compiler.

**Building and driving.** [`build/`](build/README.md) compiles a program's modules separately, each only when stale, in
parallel, and links the result. [`config/`](config) records the ABI version that tags every artifact.
[`driver/`](driver/README.md) is the command line, the REPL, and the Jupyter kernel.

## Interfaces and modules

Each unit is a pair of files: an interface (`name.int.quest`), which declares the types and values the unit exports,
and a module (`name.mod.quest`), which defines them. Other units see only the interface, so an interface's comments are
the place to read what a unit provides; its module's comments explain how. Imports form a directed acyclic graph, as
Quest's module system requires, so the directories form layers, each using only those below it
([compiler-organization.md](../docs/compiler-organization.md) §5).

## The bootstrap counterpart

The Python bootstrap mirrors this tree module for module, with names in snake case
(`typechecker/bindings` here is `typechecker/bindings.py` there). Both compilers print the same output for every
front-end phase and run every program the same way, which the shared golden tests check; the self-hosted compiler
alone has the simplifier, the SSA, the arm64 backend, and the JIT, and those have tests of their own
([testing.md](../docs/testing.md) §2.8). A change to the language, the library, or what a program does is made in both.

## Further reading

- [compiler-organization.md](../docs/compiler-organization.md): the module structure, layers, and the differences
  from the bootstrap.
- [pipeline.md](../docs/pipeline.md): the phases and the driver's options.
- [walkthrough.md](../docs/walkthrough.md): one program followed through every stage.
- [README.md](../README.md): the project, and the list of all design documents.
