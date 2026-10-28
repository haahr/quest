# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Parallel builds in the self-hosted engine

**Problem.** The self-hosted build engine (`questlang/build/engine`) compiles one unit at a time, in its own process, so
a build uses a single core. Building `questlang/driver/main` takes about a minute, a third of it in clang. Building the
questlang tests for the self-hosted suite takes several more, nearly all of it compiling the questlang modules they
share. The tests build one after another into a shared build directory (`build_questlang_tests` in
`bootstrap/python/quest/testing/runner.py`), because the engine takes no locks: two builds at once could both find a
unit stale and write its artifacts at the same time.

**Reproduce.** Run `./questc` after touching `questlang/types/model.mod.quest`, or `run_tests.py --self-hosted`, and
watch the CPU: one `questlang-driver` process at 100% of one core.

**Where to start.** Add `-j N` to the driver and have the engine compile up to N units at once, each in a child process
of the driver (a `--compile-unit` mode, or `-c` with `--build-dir`). This needs a way to start processes without
waiting for them; see "An `os/process` library" below. The engine first has to know the import graph before
compiling anything: parse each unit's imports, which is cheap, instead of finding them as it compiles. A unit can
compile once the interfaces it imports have their `.qi` files. Modules depend only on interfaces, not on other
modules' objects, so most modules can compile in parallel once the interfaces are built. Keep the queue order for
linking and for the log, so that build output stays deterministic. Then build the questlang tests with one driver
invocation that takes every test as a root, or with `-j`, instead of one at a time.

**Done when.** `./questc -j 8` and the self-hosted suite's questlang test build use several cores. Their artifacts are
byte-identical to a serial build's, apart from build.log's order, and the driver build is several times faster.

---

## An `os/process` library

**Problem.** `system.run` is the only way to start a process, and it waits for the process to finish, so a program
cannot run several at once. Parallel builds need that (see above).

**Where to start.** Add `lib/os/process.{int,mod}.quest`, a native handle like stringBuilder's (`Let Handle = external
"QProcess *"`), with `quest_process_*` in the runtime and in the bootstrap's builtins:

```quest
interface Process
export
    T::TYPE
    Let Result = Tuple code: Int stdout: String stderr: String end
    spawn(args: Array(String)): T
    spawnIn(args: Array(String) dir: String): T
    pid(p: T): Int
    isDone(p: T): Bool
    wait(p: T): Result
    waitAny(ps: Array(T)): Int
    kill(p: T sig: Int): Ok
end
```

`spawn` starts `args[0]`, found on PATH, without a shell and without waiting, and raises `system.error` if the program
cannot start. `wait` returns what `system.run` does, and the same result every time it is called. `waitAny` returns
the index of the first of `ps` to finish. Send a child's standard output and error to unlinked temp files, not pipes,
so that the parent never has to drain pipes while children run. `wait` then reads the files back. `waitAny` reaps with
`waitpid(-1)`, so the runtime keeps a table of live handles and records a status on whichever handle it belongs to.
In the interpreter, use `subprocess.Popen` with `tempfile.TemporaryFile`, and map pids through the same kind of table.
Leave `system.run` as it is. Leave out stdin, environment changes, and streaming output until something needs them.
The new runtime functions need an ABI bump.

**Done when.** Goldens in the run, compiled, and IR phases show that `wait`, `waitAny`, `isDone`, and the error for a
missing program behave the same everywhere, and docs/new-libraries.md documents the library.

---

## An `os/pathlib` library

**Problem.** `util/path` handles paths only as strings and only lexically. Filesystem operations are free functions in
`system` that take strings. Code ported from Python's `pathlib`, such as the bootstrap's build engine and runner, has
nothing to map onto.

**Where to start.** Decide whether a path is a value of its own type (Python's `Path`, built with `/` written as
`join`) or stays a string with methods grouped around it. Build it on `util/path` for the lexical part (parts, parent,
name, stem, suffix, `withSuffix`, `relativeTo`, `resolve`) and on `os/fileStats` and `system` for the rest (`exists`,
`isFile`, `isDir`, `stat`, `iterDir`, `mkdir` with parents, `unlink`, `rename`, `readText`, `writeText`). Keep
`util/path` as it is, or fold it in, but not both.

**Done when.** The library is documented in docs/new-libraries.md, has goldens in every run phase, and at least the
build engine uses it in place of string paths.

---

## Faster word operations in compiled code

**Problem.** Each `word` operation in compiled code (`word.xorBits`, `word.shift`, `word.rotate`, and the rest of
`lib/word.int.quest`) costs three calls. The caller calls the importer's wrapper `qv_word_xorBits`, which calls
through the closure in the `word` module record, which calls the external `quest_word_xor_bits` in the runtime. None
of them can be inlined, because the module record is only filled in at run time. The self-hosted compiler hashes
type text with SHA-256 written in Quest (`questlang/codegen/sha256`) and hashes keys in `util/hash`, both made of word
operations. Profiling the compiler building itself (2026-10-27) put about 7.5% of its time in these call layers.

**Reproduce.** Build `questlang/driver/main` with `./questc` from nothing under `sample` (macOS) or `perf`, and
compare the time in the `qv_word_*` wrappers and closures with the time in the `quest_word_*` functions.

**Where to start.** Compile a call to a `word` operation whose target is known statically into a direct call to its
runtime function, or into the C operator (`^`, `<<`, ...) for the simple ones. An importer does not know today which
members of `word` are externals, or which runtime functions they are: neither the `.qi` nor the `.qm` records it, so
either the artifacts record it (an ABI change) or the backend treats `word` as a builtin it knows. Do the same in the
bootstrap, and in the same commit, while the two compilers are kept in step. Every compiled program's C changes, so the
`codegen_c` digests are regenerated. A native SHA-256 primitive would remove most of the remaining cost of `layout`'s
digests, but needs a new runtime primitive and so a release before `questlang/` can use it (docs/release-compiler.md
§2).

**Done when.** Word operations in generated C are direct calls or C operators, the self-hosted build of
`questlang/driver/main` spends no measurable time in the call layers, and both compilers produce the same C.
