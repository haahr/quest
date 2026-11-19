# Plan: File-System Operations, `os/files`

Copying, removing and walking trees, finding files by pattern, temporary files and directories, symlinks, and
permissions, item 4 of
[future-libraries.md](future-libraries.md). Today the file system is split among `system` (paths as Strings:
`makeDirectory`, `removeFile`, `listDirectory`, ...), `os/fileStats` (what `stat(2)` says), and `os/path` (paths as
values, over both). None of them copies a file, removes a tree, walks one, finds files by a pattern, or makes a
temporary name: `tests/source/stdlib/os_process.quest` runs `mktemp -d` through a shell for lack of one, and
`system.error` says nothing of what failed or why. Its questions were settled with the user 2026-11-19, and it was
built the same day (§8); libraries.md §4.6 documents it.

## 1. Decisions

1. **The name is `os/files : os/Files`** (user, 2026-11-19): a word, and it reads well at the call
   (`files.copy(a b)`, `files.removeTree(d)`, `files.makeTempDirectory("build")`). `os/fs`, the item's name, would
   have been the tree's only abbreviated module name, and `os/fileSystem` is long at every call. Its function that
   lists a tree's files is `allFiles`, not `files.files`.
2. **Two layers, as os/time and util/datetime are** (the user's split for time, 2026-11-17). The *primitives* are
   one system call each, externals that take Strings and return an `Int` status (§4). Everything else is written in
   Quest over them and `os/fileStats`: copying, trees, walking, and temporary names. Only the primitives need each
   target's runtime. Unlike time, both layers are one module, because the Quest layer is small and a program should
   not need two imports to copy a file. The primitives stay private to it.
3. **Paths are Strings,** as in `system` and `os/fileStats`, so that `files` sits beside them under `os/path`.
   `os/path` gains `path.T` wrappers for the operations a program reaches for (copy, copyTree, removeTree, walk,
   glob, the temporaries), in step 3 (user, 2026-11-19).
4. **Failures say what and why** (user, 2026-11-19). `files.error` carries a `Failure`: the operation, the path, a
   `Code` from a short list of the errors a program acts on (`notFound`, `exists`, `notEmpty`, ...), and a message. So
   `removeTree` of a missing directory can be caught and told apart from one it may not enter, which `system.error`
   cannot do. The messages are fixed text in Quest, not `strerror`'s, so every target writes the same.
   `system.error`, which the other modules raise, has no payload.
5. **Symlinks are never followed when changing anything.** `removeTree` removes a symlink, not what it names. `walk`
   reports a symlink and does not enter it. `copyTree` copies a symlink as a symlink, as `cp -R`, `cp -a`, and
   `shutil.copytree(symlinks=True)` do.
6. **Temporary names are made in Quest:** a random name from `util/random`, created with the exclusive-create
   primitive (`O_CREAT | O_EXCL`) or `mkdir`, and tried again on `exists`. This is how `mkstemp` and `mkdtemp` work,
   and it needs no `mkstemp` external, which WASI has no counterpart for. Files are created with mode 0600 and
   directories with 0700, as theirs are.
7. **`copy` copies content and permission bits,** as `shutil.copy` does, but not times or ownership. Its content is
   read and written in Quest in 64 KiB pieces (reader and writer are byte-exact, since Quest strings are bytes), so a
   file of any size copies in bounded memory and alike on every target. A native `copyfile`/`copy_file_range` would
   be faster on large files, and can replace the loop later without changing the interface.
8. **Under wasm, what WASI gives.** WASI preview 1 has symlinks (`path_symlink`, `path_readlink`) and times
   (`path_filestat_set_times`), but no permission bits. So `setMode` raises `unsupported` there, and `copy` skips
   the mode. The browser page's files are an in-memory mount (`tools/wasm-page/worker.mjs`), and `runtime/wasm/host.mjs`
   implements each new call over its mounts.
9. **`system`'s file functions stay** for the programs that use them. `files` has its own versions of the few it needs
   (`remove`, `removeDirectory`, `rename`, `makeDirectory`, `list`) so that they raise `files.error`. libraries.md
   says to prefer `files` for new code.
10. **`glob` finds files by a shell pattern** (user, 2026-11-19), as Python's `glob.glob(recursive=True)` and
    `Path.glob` do: `*`, `?`, `[abc]`, `[!a-z]`, and `**` as a whole component for zero or more directories. It is
    written in Quest over `list` and `os/fileStats`, so it needs no primitive of its own and runs alike on every
    target. Matching one name against one component is `util/path`'s `matches`, a string operation that touches no
    file. The matcher is written directly, about 60 lines, not by translating to util/regexp. There is no brace
    expansion (`{a,b}`); two calls do the same.

## 2. The Interface

```quest
interface Files
import
    collections/vector : collections/Vector
    os/fileStats : os/FileStats
export
    (* =========================================================================
     * File-System Operations (Files)
     *
     * Copying, moving, and removing files and trees; walking a tree;
     * temporary files and directories; symlinks, permissions, and times.
     * Paths are Strings, as in system and os/fileStats; os/path has paths as
     * values. A failure raises error with what failed and why:
     *
     *     try files.removeTree(dir) when files.error with f then
     *         if f.code?notFound then ok else raise files.error with f end end
     *     end
     * ====================================================================== *)

    (* The errors a program tells apart; other is any other, whose message
     * says which *)
    Def Code = Option
        notFound          (* ENOENT *)
        exists            (* EEXIST *)
        notDirectory      (* ENOTDIR *)
        isDirectory       (* EISDIR *)
        notEmpty          (* ENOTEMPTY *)
        permission        (* EACCES, EPERM *)
        crossDevice       (* EXDEV: a rename between file systems *)
        unsupported       (* ENOTSUP, and what a target cannot do *)
        other
    end

    (* The operation ("remove", "copy", ...), the path it failed on (for
     * copy and rename, whichever one failed), the code, and a message such as
     * "No such file or directory" *)
    Def Failure = Tuple operation: String path: String code: Code message: String end

    error: Exception(Failure)

    (* ----- Files and directories, one system call each ----- *)

    (* Remove the file or symlink path (unlink) *)
    remove(path: String): Ok
    (* Remove the empty directory path (rmdir) *)
    removeDirectory(path: String): Ok
    (* Rename from to to, replacing a file to if there is one (rename) *)
    rename(from: String to: String): Ok
    (* Make the directory path, with permission bits mode before the umask (mkdir) *)
    makeDirectory(path: String mode: Int): Ok
    (* Make the file path, empty, with mode before the umask; raises exists
     * if anything is at path (open with O_CREAT | O_EXCL) *)
    createNew(path: String mode: Int): Ok
    (* The names in the directory path, without . and .., sorted *)
    list(path: String): vector.T(String)
    (* Make a symlink at path whose target is target (symlink) *)
    symlink(target: String path: String): Ok
    (* The target of the symlink path (readlink) *)
    readLink(path: String): String
    (* Set path's permission bits (chmod); unsupported under wasm *)
    setMode(path: String mode: Int): Ok
    (* Set path's access and modification times, in nanoseconds since the
     * epoch (utimensat) *)
    setTimes(path: String accessNs: Int modifiedNs: Int): Ok
    (* The absolute path with no symlink, . or .. (realpath) *)
    realPath(path: String): String

    (* ----- Built on them ----- *)

    (* Make the directory path and any missing parents (mkdir -p); succeeds
     * if path is a directory already *)
    makeDirectories(path: String): Ok
    (* Copy the file from to to, its content and permission bits, replacing
     * a file to; from must be a file (following symlinks) *)
    copy(from: String to: String): Ok
    (* Copy the tree at from to to, which must not exist: directories made,
     * files copied, symlinks made anew with the same targets *)
    copyTree(from: String to: String): Ok
    (* Remove path and, if it is a directory, everything in it; a symlink
     * is removed, not followed *)
    removeTree(path: String): Ok
    (* rename, or for crossDevice, copyTree (or copy) then removeTree *)
    move(from: String to: String): Ok

    (* What walk shows of each path: the path (root joined with the names
     * down to it), its stats not following a symlink, and its depth (0 for
     * root) *)
    Def Entry = Tuple path: String stats: fileStats.T depth: Int end
    (* Visit root and everything under it, before its contents and in name
     * order (pre-order); visit's result says whether to enter a directory,
     * and walk never enters a symlink *)
    walk(root: String visit: All(e: Entry) Bool): Ok
    (* The regular files under root, by walk, in its order *)
    allFiles(root: String): vector.T(String)

    (* The paths that pattern matches, sorted (as strings, so a directory's
     * entries follow it): pattern's components are matched one at a time,
     * each as util/path's matches, and ** matches zero or more directories.
     * A relative pattern is relative to the current directory, and its
     * results are relative too; an empty vector if nothing matches.
     * Examples:
     *   glob("lib/os/*.int.quest")  => lib/os/code.int.quest, ...
     *   glob("tests/**/*.quest")    => every .quest file under tests
     *)
    glob(pattern: String): vector.T(String)
    (* glob of root joined with pattern, its results relative to root; pattern
     * must be relative *)
    globIn(root: String pattern: String): vector.T(String)

    (* ----- Temporary files and directories ----- *)

    (* The directory for temporaries: TMPDIR if set and not empty, else /tmp *)
    tempDirectory(): String
    (* A new directory in tempDirectory(), named prefix and random letters,
     * mode 0700; its path *)
    makeTempDirectory(prefix: String): String
    (* A new empty file there, named prefix, random letters, and suffix,
     * mode 0600; its path *)
    makeTempFile(prefix: String suffix: String): String
    (* The result of action on a new temporary directory, which is removed
     * with everything in it afterward, whether action returns or raises *)
    withTempDirectory(A::TYPE prefix: String action: All(dir: String) A): A
end
```

`util/path` gains the matcher `glob` is built on:

```quest
    (* Whether name, one component (no /), matches pattern: * any run of
     * characters, ? any one, [abc] or [a-z] one of them, [!...] one not of
     * them; neither * nor ? nor a class matches a leading . of name
     * Examples:
     *   matches("*.quest" "a.int.quest") => true
     *   matches("*" ".git")              => false
     *   matches(".*" ".git")             => true
     *)
    matches(pattern: String name: String): Bool
```

`list` returns a vector and `allFiles` returns one, following the vector convention for results
([collections-plan.md](collections-plan.md)). `walk` takes a function and builds nothing, so a large tree costs no
more memory than its depth.

## 3. Behavior

- **`copy`** opens `from` with `reader.file` and writes `to` with `writer.file`, in `reader.getString(r 65536)`
  pieces, then sets `to`'s mode to `from`'s (`fileStats.stat`). It refuses a directory with `isDirectory`, and refuses
  `from` and `to` naming the same file (the same `realPath`) with `exists`, as `cp` does, rather than truncating the
  source.
- **`removeTree`** uses `lfind` to choose: nothing raises `notFound`; a directory has its entries removed, then
  itself; anything else is `remove`d. A failure partway raises with the path that failed, leaving the rest, as
  `rm -r` does.
- **`walk`** uses `lstat`, so a symlink's `kind` is `symlink` and `walk` does not enter it. `visit`'s `false` skips a
  directory's contents. An entry removed between `list` and `lstat` is skipped, not raised.
- **`move`** is `rename` when it succeeds. On `crossDevice` it copies, then removes the source, so a failure leaves
  the source whole.
- **`glob`** splits the pattern into components and walks only the directories they can reach. A component with no
  `*`, `?`, or `[` is a name, looked up with `lfind` rather than listed. Any other component is matched against
  `list` of the directory so far, and `**` takes the directory itself and every directory under it. The details
  follow Python's `glob` (`include_hidden=False`), so `test_files.py` can compare them:
  - `*`, `?`, `[...]`, and `**` do not match a name that starts with `.`, so `*` skips `.git`; a component written
    with a leading `.` (`.*`) matches such names.
  - `**` does not enter a symlink to a directory (§1.5), though a pattern may name one explicitly.
  - A pattern ending in `/` matches directories only.
  - An unclosed `[` is a literal character, as in `fnmatch`, so no pattern is an error. A directory that cannot be
    listed is skipped, as Python skips it.
- **Temporary names** are the prefix and 10 letters from `[a-z0-9]`, drawn from a `util/random.fromClock()`
  generator the module keeps. That is 51 bits, so `exists` comes up again only after another program takes the same
  name, and the module tries 100 names before raising `exists`.

## 4. Implementation

**The primitives are externals returning an `Int`**: 0 for success, or a negative code for a failure (−1 for
`notFound`, −2 `exists`, and so on in `Code`'s order; `other` is −(1000 + errno), so its message can name the errno).
`readLink` returns its text and `list` an array, as `system.listDirectory` does, keeping their status for a
`lastStatus` primitive to give (§8). The Quest wrapper checks the status and raises `error` with a `Failure` it
builds. So C never constructs a Quest exception with a payload, and the messages are one table in Quest, alike on
every target.

- **C** (`runtime/quest_os.c`, beside `fileStats`): `unlink`, `rmdir`, `rename`, `mkdir`, `open(O_CREAT|O_EXCL)`
  then `close`, `opendir`/`readdir`, `symlink`, `readlink`, `chmod`, `utimensat`, `realpath`; each maps `errno` as
  above.
- **wasm** (`runtime/wasm/core.mod.quest`, `questlang/wasm/runtime.mod.quest`'s `wasiFunctions`, and
  `runtime/wasm/host.mjs`): `path_unlink_file`, `path_remove_directory`, `path_rename`, `path_create_directory`,
  and `path_open` with `O_EXCL` are already imported. This adds `path_symlink`, `path_readlink`, and
  `path_filestat_set_times`. WASI's errno numbers are mapped to `Code` in `core`. `setMode` returns `unsupported`,
  and `core` computes `realPath` from `path_readlink`, since WASI has no `realpath`.
- **The interpreters:** the bootstrap's builtins (`os.unlink`, `os.symlink`, `os.utime(ns=...)`, `os.path.realpath`,
  ...) return the same statuses, and the self-hosted interpreter calls the compiled library's own
  (`questlang/interpreter/builtins`).
- **ABI:** the externals bump the ABI once, with the corpora updated (`tests/abi/corpus.py --update`, and
  `--compiler` for the self-hosted one) and `files`'s interface snapshotted in `tests/abi/inputs/lib/os/`.
- **Externals table:** `questlang/repr/externals.mod.quest`, regenerated by `tools/externals`.

## 5. Tests

- **`tests/source/stdlib/os_files.quest`**, a golden test in a directory from `makeTempDirectory`, removed at its end:
  - each primitive, and each `Code` a program can provoke (`notFound`, `exists`, `notEmpty`, `notDirectory`,
    `isDirectory`);
  - `copy` of an empty file, a 200 KB file of every byte value (more than three pieces), and onto itself;
  - a tree with nested directories, an empty one, and a symlink, through `copyTree`, `walk` (the order, a skipped
    directory, the symlink not entered), `allFiles`, and `removeTree`;
  - `glob` and `globIn` on that tree: `*`, `?`, classes, `**` at the start, middle, and end, a hidden file and a
    hidden directory, a trailing `/`, a symlinked directory under `**`, and a pattern that matches nothing;
  - temporary names: two calls differ, and `withTempDirectory` removes its directory after a raise.

  It prints paths relative to the temporary directory, so the golden is the same on every run. Under wasm, the
  symlink and mode lines are skipped: the test asks `setMode` once, and prints the same lines either way.
- **`tests/python/test_files.py`** compares `walk` and `copyTree` on a generated tree of a few hundred entries with
  Python's `os.walk` and `shutil.copytree(symlinks=True)`, and `glob` on a few dozen patterns with Python's
  `glob.glob(recursive=True)`, sorted.
- **`tests/source/stdlib/path_operations.quest`** gains `matches`: each construct, a leading `.`, `/` never matched,
  and an unclosed `[`.
- **`os_process.quest`** uses `makeTempDirectory` and `removeTree` instead of `mktemp` through a shell.
- Every backend mode runs `os_files` (including wasm and wasm-node); the browser page's check (`tools/wasm-page/check`)
  makes and removes a temporary directory.

## 6. Steps

1. **The primitives and `Failure`**, in C, wasm, and both interpreters, with the ABI bump, and the primitive half of
   `os_files.quest`.
2. **The Quest layer:** `makeDirectories`, `copy`, `removeTree`, `copyTree`, `move`, `walk`, `allFiles`, `glob`,
   `globIn`, and the temporaries, with `util/path`'s `matches`; the rest of `os_files.quest`,
   `path_operations.quest`'s lines, and `test_files.py`.
3. **Uses and docs:** `os_process.quest` on the temporaries; libraries.md §4.6; future-libraries.md's item marked
   built; and `os/path`'s wrappers (§1.3).

## 7. Left Out

The user had no preference on these (2026-11-19), so they wait for a program that needs them:

1. **`appendText`**, a writer that appends to a file, which `writer.file` cannot make, since it truncates.
2. **Hard links** (`link`).
3. **A native `copy`** (`copyfile`, `copy_file_range`) in place of §1.7's Quest loop, if large copies prove slow.

## 8. As Built

Built 2026-11-19, in two commits: steps 1 and 2 together, since the primitives are private to the module the Quest
layer is in, and then step 3. Where it differs from the sections above:

1. **`realPath` is Quest, on every target,** not a primitive: each component resolved in turn with `lfind`, a
   symlink's target put in its place, at most 40 of them. So there are ten primitives, not eleven, and wasm needs no
   `realpath` of its own.
2. **Value-returning primitives keep their status.** `list` and `readLink` return their value (empty on failure),
   and an eleventh external, `quest_files_last_status`, gives the status, so that no primitive returns a tuple, which
   C would need a layout for.
3. **`**` steps only into directories that are not symlinks** when more components follow it, and matches a symlink
   only as the last component, so nothing is reached through a symlink, as `pathlib`'s glob behaves; Python's
   `glob` would go through one. `**` also starts only from a directory, as Python's does (`x/**` matches nothing for
   a file `x`). `test_files.py` compares the two on trees without symlinks.
4. **The self-hosted interpreter calls the primitives directly,** through `questlang/interpreter/fileCalls`, a module
   of the same externals, rather than through `os/files`, which keeps them private. As with os/time, questlang/
   builds from the bootstrap (`QUEST_SEED=bootstrap`) until a release has the runtime's new functions.
5. **The browser page** starts its files with a `/tmp` (`tools/wasm-page/page.mjs`), so that the temporaries work
   there, and `tests/repl/temporary_files.quest` makes and removes one in the REPL, natively, in node, and in the
   page. That transcript keeps its values within single inputs: the JIT's `-i` session misreads a global tuple's
   fields in later inputs, a fault the release had before os/files, now in [tasklist.md](tasklist.md).
6. **Under node**, `setTimes` goes through `fs.utimesSync`, which takes seconds as a Number, so it is exact to the
   microsecond; `os_files.quest` sets whole seconds.

