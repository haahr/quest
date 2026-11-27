# questlang/build: building programs by separate compilation

This directory turns a program and the modules it imports into an executable. It sits after the compiler proper: the
driver ([`questlang/driver`](../driver/README.md)) hands it a main program when asked for a binary (`quest compile
FILE`, or `-o`), and it compiles each unit on its own, through its module compiler and the backends in
`questlang/codegen`, recompiling only the units whose artifacts are stale, then links the objects with the C runtime (`runtime/`) using the host C
compiler. It also holds the pieces every compiled program needs whether or not the engine runs: finding and invoking
the host C compiler, and keeping interfaces' C headers up to date.

## The build engine

[`engine.int.quest`](engine.int.quest) implements the build ([docs/build-process.md](../../docs/build-process.md) §7).
Its central problem is that the engine does not know in advance which modules a program needs: a unit's imports are
known only after it is parsed, and the code a compiled unit links against can include modules it never named (ones
the C it generates refers to). So the engine learns the graph as it goes. `buildMain` compiles the main program first;
its compilation writes a manifest (`.qm`) listing the modules it imports. `buildModules` then runs a first-in,
first-out queue: it pops a module, compiles it if stale, reads its manifest, and queues the modules that lists, each
once. This works because a unit is compiled against the *interfaces* of what it imports, never their
implementations, so no module has to be compiled before another one that imports it.

For a `main.quest` that imports `counter : Counter`, `quest compile -v main.quest` logs, in part:

```
POP QUEUE: 'main' (kind=main)
EVAL STALENESS: 'main' -> STALE (missing artifacts in .../build)
COMPILE MAIN: 'main'
ENQUEUE MODULE: 'counter' (from main import)
POP QUEUE: 'counter' (kind=module)
COMPILE MODULE: 'counter'
VERIFY INTERFACE: 'counter' implements 'Counter', satisfies ...
HOST LINK: linking 2 objects into .../main
```

A unit is *stale* if an artifact is missing or older than its source, if its artifacts carry another ABI version (the
number that changes whenever the layout of data or calls changes) or another backend, if an interface it was compiled
against has changed, or if one of its imports would now find a different file. Since each module is compiled alone,
two whole-program checks follow: each module's interface must be the one each importer expects of it (`VERIFY
INTERFACE`), and modules must not import one another in a cycle. The objects are then linked in queue order, after
any objects named on the command line. Every step is recorded by [`logger.int.quest`](logger.int.quest) in `build.log`
in the build directory (`.build` by default), and on standard error with `-v`
([docs/build-process.md](../../docs/build-process.md) §9).

## The module compiler

[`modulecompiler.int.quest`](modulecompiler.int.quest) compiles a module file in numbered steps that its code
follows: (1) load the interface it implements; (2) load the interfaces and modules it imports, recording each as the
unit graph resolved it; (3) elaborate the module; (4) bring its interface's header up to date; (5) translate the
module through its backend, C, `ssac`, arm64, or wasm by `questlang/codegen/choice`, into `<name>.mod.c`,
`<name>.mod.s`, or `<name>.mod.wasm`, defining the module's record, its exported functions, and an initializer that
runs its body once; (6) compile that to `<name>.o` with the host C compiler (a wasm module is its own object); and (7)
write its manifest. Steps 5 to 7 end a main routine's compilation too: the engine's `compileMainUnit` calls the same
`writeUnit`. While a module file is compiled, its abstract types stay opaque even inside a whole-program build
(`compilingApart`), since its importers see it only through its interface. The engine compiles each stale module with
it, in a child process with `-j`, and so does the driver for `quest -c x.mod.quest`.

The JIT needs the same elaboration without the files: `moduleFileUnit` elaborates a module file and lowers it to an IR
unit of the module alone, along with the module files it imports, which the JIT compiles and loads first
([docs/jit.md](../../docs/jit.md) §3.4).

## Parallel builds

With `-j N`, [`workers.int.quest`](workers.int.quest) compiles up to N modules at once
([docs/build-process.md](../../docs/build-process.md) §7.4). Because modules depend only on interfaces, any stale
modules can be compiled together once their imported interfaces exist. The engine takes the queue a *wave* at a time:
it pops the queued modules and predicts the ones they will queue from their top-level imports, deals the stale ones
into batches, and runs each batch in a child process, which is the driver itself started in unit mode
(`--unit-module`), so that a batch shares the interfaces it loads. The engine then follows the queue as a serial build
does, writing log entries, reading manifests, and re-raising a child's error in its turn. The result, artifacts, log,
and the error reported, is the same as a serial build's. Two children may rebuild the same stale interface, so
interface artifacts are written to a temporary file and renamed into place (`files.writeAtomically` in
[`common/files`](../common/files.int.quest)).

## The host C compiler and the runtime

Every backend's output, C from the C printer and `ssac`, assembly from arm64, becomes an object through the host C
compiler. [`compilerrunner.int.quest`](compilerrunner.int.quest) finds it (clang, else gcc, on `PATH`), knows the flags
every C file gets (the runtime's headers, `-DQUEST_NOGC` for a collector that never collects, the line editor
library), compiles and links, and runs a compiled binary for the `run_c_compiled` phase. The runtime's own objects are
compiled once and cached under a key of their sources, the compiler and its version, and the flags, so that a test run
of thousands of programs does not recompile the runtime for each ([docs/testing.md](../../docs/testing.md) §5.2).

## Interface headers

A module's generated C includes its interface's header (`.int.h`), which declares the module's record and exported
functions for C code. The C backend writes a header's text (`questlang/codegen/c/headers`);
[`headers.int.quest`](headers.int.quest) decides where it lives and when it must be rewritten. A header sits beside its
interface's `.qi`, and is current when written after that `.qi`, which is itself rebuilt whenever the interface or one
it depends on changes. So keeping headers current reduces to keeping `.qi` files current, which the interface compiler
does. The module compiler calls `ensureImportedInterfaceHeader` before compiling a module, and the driver calls
`compileInterfaceWithHeader` for `quest -c x.int.quest` ([docs/build-process.md](../../docs/build-process.md) §5.3).

## Connections

The engine depends on [`questlang/modules`](../modules/README.md): the unit graph's resolver (shared by every unit
the build compiles, so each import is searched for once), artifact paths under the build directory, and the
interface compiler and manifests in [`artifacts/`](../modules/artifacts/README.md). Which backend compiles each unit comes from
`questlang/codegen/choice`, and the manifest records it. When the driver compiles a program's own unit itself (a run
through `run_c_compiled`, or `--whole-program`, whose unit has its modules merged into it), it calls `buildModules`
only for the modules that unit still imports, and links the result with `compileCSource`. The bootstrap counterpart is
[`bootstrap/python/quest/build/`](../../bootstrap/python/quest/build/README.md), which builds serially.

## Further reading

- [docs/build-process.md](../../docs/build-process.md): separate and whole-program compilation (§1), the build
  directory's layout (§3), artifacts (§4), staleness and the ABI version (§5), the build algorithm (§7), linking
  (§8), and the log (§9).
- [docs/codegen-c.md](../../docs/codegen-c.md): the C backend, and how its output is compiled.
- [docs/modules.md](../../docs/modules.md) §9: separate compilation from the module system's side.
