# Milestone 5: C Code Generation, Build Artifacts, and Self-Hosting

This plan ports the rest of the bootstrap's compiler to Quest: the C backend (`codegen/c`: types, declarations, the
printer, headers, and the compiler runner, with `codegen/backend` and `codegen/symbols`), the build artifacts
(`modules/interface_compiler`, `manifest`, and `module_compiler`: `.qi`, `.qm`, and `.int.h` files), the build engine
(`build/engine`, `logger`), the configuration (`config/abi`, `options`), and the driver's compiling half
(`pipeline.py`'s code generation and `quest_driver.py`'s options). At the end, the self-hosted compiler builds programs
as `quest -o` does, writing the bootstrap's C and artifacts byte for byte, and it compiles itself to a fixed point:
the compiler it builds builds the same compiler again. It follows Milestone 4 (the IR and its interpreter,
[milestone-4.md](milestone-4.md)).

**Status:** complete (2026-10-27). Every step is done, and the fixed point holds (Step 4).

The decisions this plan rests on (2026-10-26):
- **The C is checked by digest.** A new golden phase, `codegen_c`, holds the SHA-256 of the bootstrap's C for each
  run program (`tests/golden/codegen_c`, 198 small files), as `run_c_compiled` compiles it (with `--print-result`, and
  `--echo` where the program asks for it). Raise sites name the program's file, so the paths in the C under the
  checkout are made relative to it before digesting, and the digests do not depend on where the checkout is. The
  self-hosted suite compares the digest of its own C; on a mismatch the runner regenerates the
  bootstrap's C and shows the difference. This holds while the two compilers are kept in step. When they are allowed
  to diverge, and only the self-hosted compiler is maintained, the check changes (its goldens would be its own).
- **New system primitives.** `system.run(args: Array(String)): Tuple code: Int stdout: String stderr: String end` runs a
  program (by `posix_spawn`, no shell), capturing its output, which the compiler runner needs for the C compiler's
  diagnostics; `system.modifiedTime(path: String): Real` gives a file's modification time in seconds, as Python's
  `st_mtime` does, so that `.qm` manifests are interchangeable.
- **`./quest` stays the bootstrap.** A new `./questc` launcher runs the self-built compiler (stage 2, §2.3), building
  it when it is stale. The bootstrap remains the reference the goldens come from.
- **The REPL plan runs concurrently** ([self-hosted-repl.md](self-hosted-repl.md), Steps 3 to 6). Steps 0 to 2 here
  touch `lib/system`, `runtime/`, `codegen`, and `modules`, not the driver; Step 3, which grows the driver, rebases
  onto the REPL commits on main. Every push checks main for an ABI version collision first.
- **Artifacts are the bootstrap's.** The self-hosted compiler writes `.qi`, `.qm`, and `.int.h` files identical to the
  bootstrap's but for the producer (`questlang 0.1`, informational), so either compiler can reuse the other's build
  directory. `questlang/config/abi` declares the same `ABI_VERSION`; a unit test checks that the two agree.
- **The self-hosting check is a runner mode** (`run_tests.py --self-hosting`, §2.3), run when the milestone ends and
  afterwards before pushes that change `questlang/` or the bootstrap's backend, not on every self-hosted run.
- Carried over from Milestones 2 to 4: golden tests only, the full goldens run against the compiled driver,
  `questlang/` follows the bootstrap module for module, divergences only where Quest cannot hold what Python does
  (each documented where it is made), and the steps run straight through, each pushed when its runs pass.

---

## 1. Layout

```
questlang/
├── config/        abi, options (new)
├── codegen/       backend, symbols (new); c/: types, declarations, printer, headers, backend, compilerrunner (new)
├── modules/       interfacecompiler, manifest, modulecompiler (new); loader (reads fresh .qi files)
├── build/         engine, logger (new)
└── driver/        main (codegen_c, run_c_compiled, and the build options)
lib/system         run, modifiedTime (new)
runtime/           the primitives' C
questc             the launcher (new)
```

The layers, from the bottom: `config`; `codegen/symbols` and `backend` (above `codegen/layout`); `codegen/c/types`,
`declarations`, and `printer` (above `ir`); `codegen/c/headers` and `backend`; `modules/manifest`,
`interfacecompiler`, and `modulecompiler` (above `modules/loader` and `codegen/c`); `codegen/c/compilerrunner`; and
`build/engine` and `logger`, below `driver/main`.

### 1.1. Representations

- **C text** is built with `util/stringBuilder`, as the bootstrap's printer builds lists of lines.
- **`.qi` files** are read and written through `values/dynamicjson`, the shadow records the bootstrap passes to
  `dynamic.extern` and `intern` becoming Quest tuples of the same shape. The types they hold as strings are parsed by
  the parser's type target (the bootstrap's `parse_type_string`, which Milestone 3 deferred to this one).
- **`.qm` files** are JSON (`values/json`), written with the bootstrap's indentation; their modification times are
  `Real`s, compared as Python compares `st_mtime`.
- **Processes and files.** The compiler runner finds the C compiler on `PATH` itself (the bootstrap's
  `shutil.which`), and runs it, `xcrun`, and `mktemp` (for the runtime cache's temporary objects, which the
  bootstrap's `tempfile.mkstemp` makes) through `system.run`. The runtime's sources are found beside `lib/`, under
  `QUEST_HOME` or the current directory, as `modules/paths` finds `lib/`.

---

## 2. Testing

### 2.1. The driver

`questlang/driver/main` gains the bootstrap's compiling options: `-o`, `-c` (an interface's `.qi` and `.int.h`, a
module's object and `.qm`), `-I`, `-v`, `--build-dir`, `--whole-program`, `--print-result`, `--expected-exit`, and
`--stop-after codegen_c|run_c_compiled` (and `--dump-after` for them), with the bootstrap's text, exit codes, and
diagnostics (a C compiler's failure, and a binary's run-time error mapped back to its source). `--emit-deps`, which
the bootstrap deprecates, is not ported, and `-i` is the REPL plan's.

### 2.2. Runs

- **The self-hosted suite** adds two phases: `codegen_c`, the digest of each run program's C against
  `tests/golden/codegen_c`, and `run_c_compiled`, every run golden and run-time error test compiled and run by the
  self-hosted compiler. Their tests start on the pending list, which is empty when the milestone is done.
- **The bootstrap's suite** gains the `codegen_c` phase too, so that `--update-golden` writes the digests and a change
  to the bootstrap's C shows as a golden change.
- **Artifacts.** The ABI corpus (`tests/abi/corpus.py`) gains `--compiler`, so the corpus can be regenerated by the
  self-hosted compiler and compared with the committed one; the self-hosted suite runs the comparison.
- **The questlang tests** run compiled, and **the bootstrap's suites** run when a commit changes the bootstrap,
  `lib/`, or `runtime/` (Step 0 does), as before.

### 2.3. Self-hosting

`run_tests.py --self-hosting` builds three compilers: stage 1, the self-hosted driver as the bootstrap builds it (as
the self-hosted suite does now); stage 2, built by stage 1 from the same sources; and stage 3, built by stage 2. It
checks that stage 1's C and artifacts for every questlang unit are the bootstrap's (the `.qm` files compared with
their paths and times normalized), that stage 2's are stage 1's (the fixed point), and that stage 2 passes the
self-hosted suite (`--self-hosted-driver`). Stage 3 is the fixed point's witness: its sources are stage 2's output,
so it must equal stage 2's binary up to the C compiler's own nondeterminism. `./questc` runs stage 2.

The self-hosted front end is fast enough for this: built by the bootstrap, it typechecks `questlang/driver/main` in 6
seconds (the bootstrap takes 289), with an identical dump, and runs it through `ir_described` in 11.

---

## 3. Steps

Each step is one or more commits; each ends with its runs passing.

### Step 0: System primitives (done)

`system.run` and `system.modifiedTime` in `lib/system` and the runtime (`posix_spawn` with pipes for standard output
and error, read without deadlock), the bootstrap's interpreters' builtins for them, and the self-hosted interpreters'
(`interpreter/builtins`, which call the native library). A golden test under `tests/source/stdlib` runs a program and
reads its output, exit code, and a file's time. If the runtime's interface changes, the ABI version is bumped and the
corpus regenerated. [quest-self-hosting-prerequisites.md](quest-self-hosting-prerequisites.md) §2 records the
primitives. The bootstrap's suites run.

### Step 1: The C backend (done)

Port `codegen/symbols` and `codegen/c/types`, `declarations`, and `printer`; the driver's `--stop-after codegen_c`
(with `--print-result`) prints a program's C as the bootstrap's does. The runner gains the `codegen_c` phase and its
digest goldens (bootstrap and self-hosted), and the self-hosted suite runs it on every run program. The self-hosted
compiler's C matches all 198 digests.

`config` comes with the steps that use it (`abi` with the artifacts in Step 2, `options` with the build in Step 3),
and `codegen/backend`'s passes are the driver's `lowered`, as they were for the IR's runs; its `implicit_imports`
comes with the build engine. Divergences: the printer names keyword-named variables of the bootstrap's otherwise
(`rec`, `out`, `record`, `inspect`), and keys its thunks by text rather than by tuples.

### Step 2: Interfaces, manifests, and compiled modules (done)

Port `config/abi`, `codegen/c/headers`, `modules/interfacecompiler`, `manifest`, and `modulecompiler`, with
`codegen/backend` and `codegen/c/backend` (a module file's C) and the part of `codegen/c/compilerrunner` that compiles
one C file (Step 3 ports the rest); the driver's `-c` writes an interface's `.qi` and `.int.h` and a module's C,
object, and `.qm`, and the loader reads an interface's `.qi` when it is fresh, as the bootstrap's does. `graph` gains
the artifacts' places and interfaces' dependencies, `paths` the `.qi` resolution and recorded dependencies, and the
environment a build directory and C compilation, in which modules are known through their interfaces. The
self-hosted suite's `codegen_c` phase checks the unit files: `self-hosted/abi_corpus` (the ABI corpus, regenerated
by the driver, is the checked-in one: all 60 files) and `self-hosted/unit_artifacts` (each of `lib/`'s modules
compiled alone by both compilers: the same C, `.qm`, `.qi`, and headers; all 23).

Divergences: path strings and files' text are `common/files`, which `config/abi` shares with `paths` (Python's
`pathlib`); a recorded source is compared with a source as normalized absolute paths, without resolving symbolic
links; `values/json` gains `json.dumps(indent=2)`'s format for manifests; unit-file compiles install the module
system's callbacks with a binding elaborator that stops at the first error (`typecheck.install`), as the
bootstrap's registrations at import do. The self-hosted compiler doesn't type a module with fresh artifacts through
its interface in a typecheck-only run, as the bootstrap does; it names a module's external types `module.T`, as the
bootstrap's runs do, except in a unit file's compile (the environment's `compilingUnit`), which names them as their
bindings do (`T`), as the bootstrap's elaborating the module's source does, so that headers' layout tags agree.

### Step 3: The build engine and compiled runs (done)

Port `build/engine` and `logger` and the rest of `codegen/c/compilerrunner` (the runtime's cached objects, linking,
running a binary); the driver's `-o`, `-v`, `--build-dir`, `-I`, `--whole-program`, `--print-result`,
`--expected-exit`, and `--stop-after run_c_compiled`, with its run-time error diagnostics. The self-hosted suite adds
`run_c_compiled`. This step rebases onto the REPL plan's driver commits on main.

The C phases compile the program as the bootstrap's do: its modules through their interfaces (C mode), with the
build directory's artifacts, searched first. The self-hosted suite's C phases give the driver a build directory of
its own under each worker's (`self-hosted-units`), apart from the bootstrap's artifacts, which it would otherwise find
fresh and reuse; the questlang tests are built once, as the bootstrap's are, by the self-hosted driver. All of
`run_c_compiled`'s run goldens and run-time error tests pass but `questlang/repl_sessions`, which times out compiled
as it does with the bootstrap.

Divergences: a Quest program can neither read the clock nor append to a file, so the logger runs `sh` (with `date`)
to append each entry to the log; temporary files are made by `mktemp`, the program's C in a temporary directory of
its own; a compiled program runs without the bootstrap's 10-second timeout; an error that is not a compiler error
(a C compiler's failure, say) is reported at the program's first character, without the bootstrap's Python
traceback; and `--dump-after` is ported for the C phases only.

### Step 4: Self-hosting (done)

The runner's `--self-hosting` mode (§2.3) and the `./questc` launcher. Stage 2 passes the self-hosted suite, and the
fixed point holds: the artifacts of all of the driver's units, as stages 1 and 2 write them, are the bootstrap's and
stage 1's, up to the producer and the build directory's path, and stages 2 and 3 are the same binary.

`./questc` builds its stages under `.build/questc` (stage 1 by `./quest`, stage 2 by stage 1) when it has none or any
file under `questlang/`, `lib/`, or `runtime/` is newer than stage 2, each build compiling only its stale units, and
then runs stage 2 with `QUEST_HOME` set to the tree. Building both from nothing takes about 20 minutes, most of it
the bootstrap's.

Divergences: the check compares every artifact a stage writes (`.mod.c`, `.main.c`, `.int.h`, `.qi`, and `.qm`) and
not the runtime's cached objects. The self-hosted compiler became fast enough to build itself only once its type
tables were keyed by integers rather than strings (`common/keys`, which the bootstrap doesn't need: Python hashes the
tuples it keys them by) and its `stripAliases` cached its results globally, as the bootstrap's does. Before that,
stage 2 took more than 30 minutes; it now takes about 8.

### Step 5: Documentation (done)

Update compiler-organization.md (§2's "so far", §6's Milestone 5 status), roadmap.md (Step 5's fixed point),
build-process.md (the self-hosted compiler's artifacts), testing.md (the new phases and `--self-hosting`), and
quest-self-hosting-prerequisites.md; record the divergences in this document. Each step's section records its own
divergences. Parallel builds, and the `os/process`, `os/filestats`, and `os/pathlib` libraries, which would replace
some of those divergences' workarounds, are on [tasklist.md](tasklist.md).

---

## 4. Done When

- The compiled self-hosted driver matches every `codegen_c` digest and passes every run golden and run-time error test
  at `run_c_compiled`, with `QUEST_CHECK_IR` and `QUEST_CHECK_CANONICAL` set, as the runner sets them; its regenerated
  ABI corpus is the committed one.
- `run_tests.py --self-hosting` passes: stage 1's output for questlang is the bootstrap's, stage 2's is stage 1's, and
  stage 2 passes the self-hosted suite. `./questc` runs stage 2.
- The questlang tests pass compiled; the bootstrap's suites pass.

## 5. Not in This Plan

- The self-hosted REPL (its own plan, [self-hosted-repl.md](self-hosted-repl.md)).
- Letting the compilers diverge and retiring the bootstrap, which would change how the C is checked (see the decisions above).
- Parallel builds, and a native backend with the CFG and SSA stages it would add (ir.md §8.6).
