# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Parallel builds in the self-hosted engine

**Problem.** The self-hosted build engine (`questlang/build/engine`) compiles one unit at a time, in its own process,
so a build uses a single core. Building `questlang/driver/main` takes about 8 minutes. Building the questlang tests
for the self-hosted suite takes several more, nearly all of it compiling the questlang modules they share. The tests
build one after another into a shared build directory (`build_questlang_tests` in
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

## An `os/filestats` library

**Problem.** `system.modifiedTime` is the only file metadata available. The build engine, the manifests, and the
interpreter's builtins call it after a separate `system.fileExists` or `system.isFile` call, which costs a second
`stat` and leaves a race between the two calls. Nothing can read a file's size, its type beyond file or directory, or
its permissions.

**Where to start.** Add `lib/os/filestats.{int,mod}.quest`, modeled on Python's `os.stat_result` (what
`pathlib.Path(...).stat()` returns). It holds one tuple of the fields both platforms have: size, mode, kind (file,
directory, symlink, or other), and the access, modification, and change times. Give the times both as Python's float
seconds and as integer nanoseconds (`st_mtime_ns`), because the build's staleness checks should compare exact
integers. Have `stat(path)` raise `system.error` and `find(path): maybe.T(Stats)` return none for a missing file, plus
`lstat` for symlinks. Compute the times as `quest_system_modified_time` does now, so that C and the interpreter agree
exactly. Then move the callers of `system.modifiedTime`, `fileExists`, and `isFile` in `questlang/` over to it, and
decide whether `modifiedTime` stays in `system`.

**Done when.** The questlang callers make a single `stat` call per file, and goldens show the same stats in C and the
interpreter.

---

## An `os/pathlib` library

**Problem.** `util/path` handles paths only as strings and only lexically. Filesystem operations are free functions in
`system` that take strings. Code ported from Python's `pathlib`, such as the bootstrap's build engine and runner, has
nothing to map onto.

**Where to start.** Decide whether a path is a value of its own type (Python's `Path`, built with `/` written as
`join`) or stays a string with methods grouped around it. Build it on `util/path` for the lexical part (parts, parent,
name, stem, suffix, `withSuffix`, `relativeTo`, `resolve`) and on `os/filestats` and `system` for the rest (`exists`,
`isFile`, `isDir`, `stat`, `iterDir`, `mkdir` with parents, `unlink`, `rename`, `readText`, `writeText`). Keep
`util/path` as it is, or fold it in, but not both.

**Done when.** The library is documented in docs/new-libraries.md, has goldens in every run phase, and at least the
build engine uses it in place of string paths.
