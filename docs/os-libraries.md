# Operating-System Libraries

This plan carries out three tasks from [tasklist.md](tasklist.md):

- an `os/filestats` library;
- an `os/process` library;
- typed paths, added to `util/path` instead of a separate `os/pathlib`.

Parallel builds, which need `os/process`, stay on the tasklist as a separate piece of work.

The decisions (2026-10-27):

- The libraries land in the order filestats, process, paths.
- `system.modifiedTime` is removed once questlang no longer calls it. `fileExists`, `isFile`, and `isDirectory` stay.
- A path is an abstract type with free functions, in `util/path`, not in a new `os/pathlib`. Its String functions
  stay.
- Releases are cut from the self-hosted compiler as it now is, which builds the driver in about a minute; the first
  is cut before step 1.
- Releases are cut as the plan needs them (§1).

---

## 1. How Each Library Lands

The release rule ([release-compiler.md](release-compiler.md) §2) says that `questlang/` may use only what the current
release compiles against its own `lib/`. So each library lands in two commits with a release between them:

1. **The library commit.** It adds:
   - the interface and module in `lib/`;
   - the natives in `runtime/`, with an ABI bump if there are any;
   - the bootstrap interpreter's builtins (`bootstrap/python/quest/interpreter/builtins.py`);
   - the self-hosted interpreter's builtins (`questlang/interpreter/builtins.mod.quest`, plus a `Value` variant when
     the library has a native handle);
   - goldens in the run, compiled, and IR phases;
   - a section in [new-libraries.md](new-libraries.md);
   - a snapshot of the interface in the ABI corpus's inputs (`tests/abi/corpus.py --refresh-inputs`).

   The interpreter's builtins are the one use of a new library inside `questlang/` that cannot wait for a release.
   That is the gap §2 of the release plan allows for: until the release is cut, `./questc` needs
   `QUESTC_SEED=bootstrap`. The runner and `tools/release` build from the bootstrap by default, so nothing else
   notices.
2. **A release** (`tools/release`), cut from the library commit once it is pushed.
3. **The use commit.** It moves the callers in `questlang/` over to the library and removes what the library replaces.

Each commit is pushed when the self-hosted suite, the questlang compiled tests, the bootstrap goldens, and the unit
tests pass. Before each push, check main for new commits and for ABI collisions.

## 2. `os/filestats`

### 2.1. Interface

```quest
interface FileStats
import
    util/maybe : util/Maybe
export
    (* What kind of thing a path names *)
    Let Kind = Option file directory symlink other end

    (* Python's os.stat_result: the fields both platforms have *)
    Let T = Tuple
        size: Int
        (* The permission bits (st_mode & 0o7777); the kind is in kind *)
        mode: Int
        kind: Kind
        (* Seconds since the epoch, as Python computes st_atime, st_mtime, and
         * st_ctime *)
        accessTime: Real
        modifiedTime: Real
        changeTime: Real
        (* The same times as exact integers, as st_*_ns *)
        accessNs: Int
        modifiedNs: Int
        changeNs: Int
    end

    (* The stats of the file a path names, following symlinks; raises
     * system.error if there is none *)
    stat(path: String): T
    (* The same, but of a symlink itself *)
    lstat(path: String): T
    (* stat, or none if the path names nothing *)
    find(path: String): maybe.T(T)
    (* lstat, or none if the path names nothing *)
    lfind(path: String): maybe.T(T)
end
```

- **Natives.** `quest_filestats_stat(path, follow)` fills a flat tuple, with the kind as an Int and −1 meaning
  missing. `find` and `stat` are written in Quest over it, so that only one native raises. The Real times are
  computed as `quest_system_modified_time` computes them now, so that C and Python agree exactly. ABI 43.
- **Interpreters.** In the bootstrap, `os.stat` and `os.lstat`, using `st_*` and `st_*_ns`. In the self-hosted
  interpreter, it calls `fileStats` itself. It needs no `Value` variant, because the result is an ordinary tuple.
- **Goldens.**
  - Stats of files a test creates: size, kind, the mode after a `chmod`-free write, and `find` on a missing path.
  - A file's `modifiedNs` agrees with its `modifiedTime`.
  - The error for a missing path.

  Times themselves are not printed, because they vary from run to run.

### 2.2. Use

- Move the questlang callers over: the 13 `system.modifiedTime` calls listed below, and the `fileExists` or `isFile`
  calls that guard them. Each file then takes one `find` instead of two calls, in:
  - `build/engine`;
  - `codegen/c/headers`;
  - `modules/paths`, `loader`, `interfacecompiler`, `modulecompiler`, `graph`, and `manifest`.
- Staleness compares `modifiedNs`. These are exact integers, where the bootstrap compares Python's float `st_mtime`.
  For files modified at least a microsecond apart, the two order times identically. A golden or unit test should
  cover two files with equal and unequal times.
- The `.qi` scope cache in `loader` and the source key in `graph` key on `modifiedNs` instead of `conv.real` of a
  Real.
- Remove `system.modifiedTime` from:
  - `lib/system`;
  - the runtime (`quest_system_modified_time`, with an ABI bump to 44);
  - both interpreters' builtins;
  - the goldens that use it, which move to `fileStats`.

  The ABI corpus's frozen `system.int.quest` input keeps it until the next `--refresh-inputs`. That refresh is part
  of this commit.

## 3. `os/process`

### 3.1. Interface

This is the interface from the tasklist:

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

- **Runtime.**
  - The handle is `QProcess *`, holding the pid, the status once the process is reaped, and two unlinked temp files
    that receive its standard output and error.
  - `spawn` uses `posix_spawnp`, as `system.run` does. `spawnIn` changes the directory in the child, with
    `posix_spawn_file_actions_addchdir_np`, which both macOS and glibc have.
  - A table of live handles lets `waitAny` reap with `waitpid(-1)` and record the status on whichever handle the
    process belongs to.
  - `wait` reads the files back once, and keeps the Result, so that a second call returns the same one.
  - A pid that is not in the table is ignored.
  - ABI 45.
- **Bootstrap interpreter.** A `QProcess` class over `subprocess.Popen`, with `tempfile.TemporaryFile`s for the
  output. `waitAny` calls `os.waitpid(-1, 0)`, maps the pid through a table, and sets that `Popen`'s `returncode`.
- **Self-hosted interpreter.** A `vProcess with p: process.T end` variant in `values/model` with identity hashing,
  as `vStringBuilder` has, and builtins that call `process` itself.
- **Goldens.** The tests run `sh -c` with:
  - exit codes, and output on both streams;
  - `spawnIn`'s directory;
  - `isDone` before and after `wait`, and `wait` called twice;
  - `waitAny` with a `sleep 1` child and an immediate one;
  - `kill` with signal 15, giving code −15;
  - the error for a missing program.

### 3.2. Use

No questlang caller changes: parallel builds are what will use `os/process`. The release after this library is still
needed, because the self-hosted interpreter imports it. The tasklist's parallel-builds entry is updated to say that
the library exists.

## 4. Paths in `util/path`

- **The type.** `util/path` gains an abstract `T`, implemented as a String normalized as Python's `PurePath`
  normalizes:
  - repeated separators collapse;
  - `.` components and a trailing `/` drop;
  - `..` is kept, because cancelling it needs the filesystem.

  Two equal paths are then equal strings, and `path.equal` and `path.hash` make `T` usable as a `hashMap` key.
- **The String functions stay as they are,** and the functions over `T` are added beside them with names of their
  own, Python's where they do not collide:
  - `of(s)` and `toString(p)` convert;
  - the decomposition functions are `parent`, `name`, `pathStem`, `suffix`, `withSuffix`, and `pathParts`;
  - joining is `child(p s)` and `joinPaths(p q)`;
  - `pathIsAbsolute`, `normalizePath`, `pathRelativeTo`, and `resolvePath`.

  The T functions are written over the String ones.
- **Filesystem functions, over `T`.**
  - `exists`, `isFile`, and `isDir`;
  - `stat` and `find`, delegating to `fileStats`;
  - `iterDir`, which is sorted, unlike `system.listDirectory`, so that output is deterministic;
  - `mkdir(p parents: Bool)`, `unlink`, `rename`, `readText`, and `writeText`.

  `util/path` then imports `os/filestats`, `system`, `reader`, and `writer`. It has no natives, so it needs no ABI
  bump and no interpreter builtins.
- **Goldens.** The current `path_operations` golden stays. A new golden exercises the functions over `T`, and another
  the filesystem functions, in a directory the test creates.
- **Use.**
  - `questlang/common/files` (`isAbsolute`, `join`, `components`, `normalize`, `absolute`, `readText`) folds into
    `util/path`, and its callers move.
  - The build engine's paths become `path.T` (the tasklist's "done when").
  - Other string paths in `modules/` and `codegen/` move only where they meet the engine's interfaces. The rest can
    move later.

## 5. Documentation and the Tasklist

- [new-libraries.md](new-libraries.md) gains a section 4, Operating System (`lib/os/`), for `os/filestats` and
  `os/process`. Its `util/path` section (§1.4) gains the functions over `T`.
- [tasklist.md](tasklist.md) loses the three library entries as they land, and the parallel-builds entry points at
  `os/process`.
- The comment on `system.run` in `lib/system.int.quest` points at `os/process`.
- [build-process.md](build-process.md) §5 says that staleness compares nanosecond times.

## 6. Steps

0. Release the faster self-hosted compiler, so that seeded builds are fast too.
1. `os/filestats`: the library, at ABI 43.
2. Release.
3. The questlang callers move to `fileStats`, and `system.modifiedTime` is removed, at ABI 44.
4. `os/process`: the library, at ABI 45.
5. Release.
6. `util/path`: the type and the filesystem functions.
7. Release.
8. `common/files` folds into `util/path`, and the build engine moves to `path.T`.
