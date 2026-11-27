# bootstrap/python/quest/build: building programs by separate compilation

This package turns a program and the modules it imports into an executable for the bootstrap compiler. The driver
hands it a main program (`questboot compile FILE`, or `-o`), and it compiles each unit on its own to C and an object
file, through its module compiler, recompiling only the units whose artifacts are stale, and links the objects with
the C runtime (`runtime/`). It is the original of [`questlang/build`](../../../../questlang/build/README.md), whose
README introduces the concepts; this one says where they are here and what differs.

## The concepts, here

- **The build engine.** [`engine.py`](engine.py)'s `BuildEngine` compiles the main program first (`build_main`), learns
  from the manifest its compilation writes which modules it imports, and brings those up to date from a first-in,
  first-out queue (`build_modules`), queueing each module's own imports as its manifest lists them. A unit is
  compiled against the interfaces of what it imports, never their implementations, which is what lets the engine
  discover the program's modules as it goes. A unit is stale if an artifact is missing or old, was made for another
  ABI version, was compiled against an interface that has since changed, or has an import that would now find
  another file. After compiling, the engine checks that each module implements the interface its importers expect
  and that modules do not import one another in a cycle, then links. `BuildEngine`'s docstring walks through an
  example with its log. The same file has `compile_unit_file`, which compiles one interface or module file alone, as
  `questboot -c` does; in questlang that is the driver's `compileUnitFile`.
- **The module compiler.** [`module_compiler.py`](module_compiler.py) compiles a module file to C (`<name>.mod.c`,
  defining the module's record, functions, and initializer), an object, and a manifest (`compile_module_file`), the
  steps numbered in its code. Its `write_unit`, which writes a unit's C, compiles it, and writes its manifest, ends a
  main routine's compilation too (`BuildEngine.compile_main_unit`).
- **The log.** [`logger.py`](logger.py) appends one timestamped, tagged line per event (`POP QUEUE`, `COMPILE MAIN`,
  ...) to `build.log` in the build directory, and with `-v` to standard error
  ([docs/build-process.md](../../../../docs/build-process.md) §9).
- **The host C compiler.** [`compiler_runner.py`](compiler_runner.py) finds clang or gcc, knows the flags C units
  get, compiles the runtime's objects once and caches them, and compiles, links, and runs programs
  ([docs/codegen-c.md](../../../../docs/codegen-c.md) §11).
- **Interface headers.** [`headers.py`](headers.py) keeps each interface's C header (`.int.h`) beside its `.qi`,
  rewriting it when the `.qi` is newer, so that a module's C can include its interface's declarations. The header's
  text comes from `quest/codegen/c/headers.py`.

## What differs from questlang/build

The bootstrap builds serially: there is no `-j` and no counterpart of `questlang/build/workers`. It has only the C
backend, so every unit is compiled from C and no manifest needs to record a backend. The check of whether a unit's
imports would now resolve elsewhere is `import_resolution_change` in
[`quest/modules/resolution.py`](../modules/resolution.py); questlang keeps it in its engine. The two engines otherwise follow
the same algorithm and write the same kinds of artifacts and log entries. Each treats a unit whose manifest the other
compiler wrote as stale, so the two never link each other's objects.

## Further reading

- [docs/build-process.md](../../../../docs/build-process.md): separate and whole-program compilation (§1), the build
  directory (§3), artifacts (§4), staleness (§5), the build algorithm (§7), and linking (§8).
- [`questlang/build/README.md`](../../../../questlang/build/README.md): the self-hosted counterpart, with parallel
  builds.
