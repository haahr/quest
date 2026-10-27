# Self-Hosting Prerequisites for Quest

This document specifies the foundational capabilities, data structures, runtime libraries, and operating system
primitives required to implement the **Step 5 Self-Hosted Front-End and Compiler** (`questc` written in Quest).

It details the features currently used by the Python bootstrap implementation (`bootstrap/python/quest/`) that are
absent from core Quest or Cardelli's standard library specification (*Typeful Programming* §11.2), organizing them
into modular subsystems that can be developed incrementally.

---

## 1. Core Data Structures & Collections

The primary collection libraries required for self-hosting have been implemented and are documented in
`docs/new-libraries.md`:
- `collections/vector : collections/Vector` (growable dynamic arrays `Vector(T)`)
- `collections/hashMap : collections/HashMap` (compact ordered hash tables `HashMap(K, V)`)
- `collections/hashSet : collections/HashSet` (hash sets `HashSet(T)` built on `HashMap`)

Queues and stacks (used for scope stacks in `types/env.py`, block nesting and token lookahead buffers, and
topological sort queues) are straightforwardly implemented on top of `collections/vector`.

---

## 2. Operating System, Process Execution, and Filesystem Primitives

Quest's `System` interface provides operating system and filesystem primitives:
`args`, `sysexit`, `getEnv`, `fileExists`, `isFile`, `isDirectory`, `makeDirectory`, `removeFile`,
`removeDirectory`, `renameFile`, `currentDirectory`, `changeDirectory`, `listDirectory`, `run`, and `modifiedTime`.

### 2.1. Process Execution (`subprocess.run`)
- **Python Usage**: `compiler_runner.py` invokes the host C compiler (`clang` or `gcc`) to compile and link generated
  C source into object files (`.o`) and executables, reading its diagnostics from its standard error.
- **Primitive** (Milestone 5, [milestone-5.md](milestone-5.md)):
  ```quest
  system.run(args: Array(String)): Tuple code: Int stdout: String stderr: String end
  ```
  Runs `args[0]`, found on `PATH`, with the rest as its arguments, without a shell (`posix_spawnp`), and waits for
  it: its exit code (a signal's negated number when one killed it, as in Python) and what it wrote to standard
  output and error, read together so that neither pipe fills. A program that cannot be run raises `system.error`.

### 2.2. File Modification Times (`os.stat(...).st_mtime`)
- **Python Usage**: the build's staleness checks and `.qm` manifests compare modification times.
- **Primitive**: `system.modifiedTime(path: String): Real`, the seconds since the epoch, computed as Python computes
  `st_mtime`, so that the two compilers' manifests agree.

### 2.3. Host Toolchain Discovery (`shutil.which`)
- **Python Usage**: Locating `clang` or `gcc` in the host `$PATH`.
- **Implementation**: Pure Quest function reading `system.getEnv("PATH")`, splitting on `:`, and checking
  `system.fileExists`.

## 3. Algorithms and Math Utilities

### 3.1. Binary Search (`bisect.bisect_right`)
- **Usage**: `tokens.py` maps a character offset to `(line, column)` in $O(\log N)$ time by searching an array of line
  start offsets.
- **Implementation**: A simple `binarySearchRight(arr: Array(Int), target: Int): Int` in pure Quest.

### 3.2. Sorting Algorithms (`sorted`, `list.sort`)
- **Usage**:
  - **Canonical Record Field Ordering**: Cardelli §4.1 specifies record type labels are ordered lexicographically
    to determine field layout and tuple representations.
  - **Diagnostic Ordering**: Sorting compiler diagnostics by line and column before displaying.
  - **Syntax Error Messages**: Sorting expected token names.
- **Implementation**: Generic Quicksort or Mergesort parameterized by a comparison function:
  ```quest
  sort(A::TYPE arr: Vector(A), compare: Fun(a: A, b: A): Int): Ok
  ```

### 3.3. Graph Topological Sort
- **Usage**: Topological sorting of modules to verify acyclic imports (Cardelli §7.1) and generate module
  initialization sequences.
- **Implementation**: Graph adjacency list with Kahn's algorithm or DFS in pure Quest.

---

## 4. Command-Line Argument Parsing
 
- **Python Usage**: `argparse.ArgumentParser` handles positional arguments (`main.quest`, `foo.o`), options with
  values (`-o <file>`, `-I <dir>`, `--stop-after <phase>`), and boolean flags (`-c`, `--emit-c`, `--nogc`).
- **Quest Solution**: Implemented in pure Quest as `util/argParse : util/ArgParse`
  (`lib/util/argparse.{int,mod}.quest`), operating over `system.args: Array(String)` or arbitrary vectors
  of strings, documented in `docs/new-libraries.md`.

---

## 5. Language-Level Architectural Adaptations

Migrating the Python object-oriented codebase to Quest requires structural adaptations to match Quest's type system.
[self-hosting-refactorings.md](self-hosting-refactorings.md) plans the ones best made in the Python compiler first
(formatting C, reflective traversals, nodes discriminated by which fields are set, duck typing).

### 5.1. Class Hierarchies to Algebraic Data Types (`Variant`)
- In Python, AST nodes (`ExprIf`, `ExprFun`, `ExprRecord`) and types (`QFunType`, `QRecordType`) are classes
  inheriting from `ASTNode` and `QType`, inspected using `isinstance()`.
- In Quest, there are no classes or inheritance. All AST and Type structures must be modeled as **recursive variant
  types** (`Let Rec Expr = Variant if: Tuple ... end fun: Tuple ... end ... end`) and inspected via
  `case expr of ... end`.

### 5.2. RAII / Context Managers to Higher-Order Functions
- In Python, `with env.scoped():` manages entering and leaving lexical scopes.
- In Quest, scope lifecycle should use higher-order functions:
  ```quest
  env.withScope("local", fun(s: Scope): Ret ... end)
  ```
  using `try ... when` to guarantee `popScope` runs on normal exit or exception.

### 5.3. Multi-Pattern Matching
- Python 3.10+ matches pairs of types simultaneously (`match (sub, sup): case (QTupleType(...), QTupleType(...)):`).
- Quest `case` dispatches on one variant at a time, requiring nested `case` expressions.

---

## 6. Implementation Roadmap & Priority Matrix

Every prerequisite is met, and the self-hosted compiler compiles itself (Milestone 5,
[milestone-5.md](milestone-5.md)). The libraries (`collections/vector`, `collections/hashMap`, `collections/hashSet`,
`util/maybe`, `util/stringBuilder`, `util/strutil`, `util/path`, `util/argParse`, `util/hash`, and `util/sort`) are
documented in `docs/new-libraries.md`. The OS primitives are `system.run` and `system.modifiedTime` (§2). Binary search
and the topological sort are written in Quest where they are used. The AST and type models are
[compiler-organization.md](compiler-organization.md) §3's.

Two of the bootstrap's needs turned out to be missing, and are worked around for now:
- **A clock and appending to a file.** The build log's timestamps and appends run `sh` with `date`
  (`questlang/build/logger`).
- **Hashing structured keys.** The bootstrap keys its type tables by tuples, which Python hashes. Keys built as
  strings made the self-hosted compiler several times slower, so the tables use integer keys interned through
  `questlang/common/keys`.

Planned libraries that would replace workarounds and serve later work are on [tasklist.md](tasklist.md): `os/process`
(processes that run in parallel, for parallel builds), `os/filestats`, and `os/pathlib`.

