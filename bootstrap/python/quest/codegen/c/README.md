# bootstrap/python/quest/codegen/c: the bootstrap's C backend

This is the bootstrap compiler's only backend. It takes a unit at the end of the IR's pipeline (lowered, specialized,
closure-converted, with representations and run-time type descriptors decided by the passes in [`../../ir`](../../ir))
and prints it as one C file, which the build engine compiles with the host C compiler
([`../../build/compiler_runner.py`](../../build/compiler_runner.py)) and links against the runtime. The entry points
that lower a typed program or module file, run the IR's passes, and call the printer are in
[`../backend.py`](../backend.py).

The self-hosted compiler's [`questlang/codegen/c`](../../../../../questlang/codegen/c/README.md) is the same backend,
module for module, and its README is the full introduction. In short:

- [`printer.py`](printer.py) (`print_c`, with its state in the `CPrinter` class) prints decisions, it does not make
  them: each IR function becomes a C function taking its closure's environment, then its type parameters'
  descriptors, then its parameters; closures are `QClosure`s; join points and loop exits are labels; `try` regions
  are `setjmp` handlers. A module file's unit exports its record, initializer, and a direct C function per exported
  function, the ABI other units link against.
- [`declarations.py`](declarations.py) (`CDeclarationEmitter`) writes what precedes the functions: a struct for each
  aggregate type, the offset tables through which code reads a record's fields at a supertype, the coercion tables
  for tuples and variants used at supertypes, static type descriptors, and adapters for function types.
- [`headers.py`](headers.py) writes interfaces' C headers (`.int.h`), which C units that import an interface include.
- [`types.py`](types.py) holds the C spellings of representations, `QVal` wrapping, slot loads and stores, and
  closures' function-pointer types.

## How it differs from the self-hosted backend

- **C only.** The bootstrap has no SSA, no ssac, no arm64 backend, and no JIT, so it has no backend choice either:
  `--backend` and `--unit-backend` are the self-hosted driver's.
- **Less optimized input.** The bootstrap's IR pipeline has no simplifier, inliner, or unboxed results, so the C it
  prints for a program differs from the self-hosted compiler's; each compiler keeps its own IR and C goldens, and the
  two share only behavior goldens.
- **Where descriptors are named.** Choosing a type's descriptor form (`descriptor_form`) and naming record structs
  and offset tables (`RecordNamingContext`) live here in `types.py`; the self-hosted compiler keeps them in
  `questlang/repr/staticdata`, which its native backends share.
- **Failure.** What the printer cannot print raises `NotImplementedError`, where the self-hosted printer raises its
  `unsupported` exception.

The self-hosted printer creates names and temporaries in this printer's order, so that the two compilers' C for the
same IR reads alike.

## Further reading

- [docs/codegen-c.md](../../../../../docs/codegen-c.md): the C backend's translation of each construct
- [docs/c-representation.md](../../../../../docs/c-representation.md): the C representation of Quest's values
- [docs/ir.md](../../../../../docs/ir.md) §8.5: printing C
