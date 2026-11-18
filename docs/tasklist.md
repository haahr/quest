# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## A missing interface in an imported module's import is located at the module's first line

**Problem.** When a module file that a program imports itself imports an interface that cannot be found, both
compilers report the error at the module's `1:1`, quoting its first line, instead of at the import that names the
interface. It shows in a `-o` build with either compiler, and in `./quest`'s run with the JIT, which compiles the module
from source as a build does. A run with `--no-jit`, and the bootstrap's run, which type check the module through
`env.atImport`, locate it at the import. Since the compilers agree on `-o`, both must change together.

**Reproduce.** In an empty directory, `a.int.quest` (`interface A export g(): Ok end`), `a.mod.quest` (a comment on
its first line, then `module a : A import bad : Bad export let g(): Ok = bad.f() end`, with `bad : Bad` on line 4),
and `main.quest` (`import a : A; a.g();`), with no `bad.int.quest`. `./questboot --build-dir b -o b/m main.quest`
and `./quest --build-dir b2 main.quest` print `a.mod.quest:1:1: error: Undefined interface 'Bad': ...` and quote the
comment; `./questboot --build-dir b3 main.quest` prints `a.mod.quest:4:9`, the import, and `main.quest:1:10 ... note:
imported here`.

**Where to start.** Step 2 of `elaborate` in `questlang/modules/artifacts/modulecompiler.mod.quest` loads each
import's interface (`elaboration.loadInterface`) outside `env.atImport`, so the error keeps offset 0 and
`env.withUnitSource` places it at the file's start; the bootstrap's module compiler in `bootstrap/python/quest/` does
the same. Wrapping the load in `env.atImport(e imp.offset 1 ...)`, in both, should locate it at the import.

**Done when.** Every path (`-o`, run with the JIT, run with `--no-jit`) in both compilers reports the error at the
import, and a case under `tests/self-hosted/build-errors` shows it (`build_errors.py` checks all three paths).

---

## Quest isn't highlighted in JupyterLab's editor

**Problem.** The Jupyter kernel ([jupyter-kernel.md](jupyter-kernel.md)) names a Pygments lexer, which nbconvert uses
when it exports a notebook, but JupyterLab's own editor, CodeMirror 6, highlights a language only through a JupyterLab
extension, so Quest cells show as plain text while they're edited.

**Reproduce.** `tools/jupyter/install`, then open a Quest notebook in JupyterLab.

**Where to start.** A JupyterLab 4 extension (TypeScript, built with jupyterlab's extension tools) registering a
CodeMirror 6 language for `text/x-quest`, its tokens those of `tools/jupyter/quest_lexer.py`, installed by
`tools/jupyter/install` with the lexer.

**Done when.** A Quest cell's keywords, comments, and strings are highlighted as it's typed in JupyterLab.

---

## The Jupyter kernel hasn't been tried in JupyterLab's page

**Problem.** The kernel's tests drive it through `jupyter_client` and nbconvert, as a notebook does, but nobody has
yet run a notebook in JupyterLab's page itself: binding, printing, a failing cell, Tab completion of `vector.` (after
importing it), Shift-Tab inspection, `io/display`'s HTML and PNG, a cell reading a line, and the interrupt button on an
endless loop (the session survives) and on `system.run` of `sleep 30` (it restarts after five seconds).

**Where to start.** `tools/jupyter/install`, then `jupyter lab` in a directory of notebooks.

**Done when.** Each of those works by hand, or a task records what doesn't.

---

## The Jupyter kernel's later work

**Problem.** Two uses of the kernel aren't built: connecting a notebook to a program already running (a REPL served
on a socket, rather than a session the kernel starts), and notebooks as tests (a `.ipynb`'s cells run through the
protocol, their outputs compared with the notebook's).

**Where to start.** `tools/jupyter/quest_session.py` for both: a session over a socket, and a runner of a notebook's
cells.

**Done when.** Either is wanted and built; until then, this records them.

---

## The write barriers' inline fast paths, not kept, may be worth another try

**Problem.** The arm64-built compiler spends time in `quest_barrier_slot` and `quest_barrier_object`, called out of
line at every barriered store. Inlining their fast paths (an SSA expansion after the barrier rule's check, in arm64's
and the JIT's code) took `quest_barrier_slot` from 924 of the compiler's samples to 27, but made the compiler 1.3
percent slower (0.9 percent with the slot barrier alone inline) and its text 1.8 percent larger, and the suite didn't
move ([benchmarks.md](benchmarks.md) §22.2, item 3). It wasn't kept. It may pay once the code around a barrier is
shorter, or with a smaller expansion: only in loops, only the slot barrier, or a shared out-of-line tail.

**Where to start.** Branch `claude/inline-barriers-not-kept` on origin (`87acb5e7`, on `238a594f`):
`questlang/ssa/writeBarriers` and its test `ssa_write_barriers`, the runtime's entries in `codegen/runtimeFunctions`
and `codegen/runtimeLayout`, and the pipeline's call. It predates the restructuring: the
pass belongs in `questlang/ssa/passes/`, and `runtimeLayout` is now `questlang/repr/runtimeLayout`.

**Done when.** A variant makes the compiler or the suite faster, measured as §22.1 measures, and is kept, or the idea
is dropped and the branch with it.

---

## The collector's growth target counts a recyclable block as wholly in use

**Problem.** After a full collection the heap may grow to `Q_GC_GROWTH` times the blocks in use
(the target `quest_gc_sweep` sets in `runtime/quest_gc.c`), and a recyclable block with one live line counts as a
block in use, so a heap of mostly empty recyclable blocks collects more often than its live data warrants
([benchmarks.md](benchmarks.md) §16.3).

**Where to start.** The target's computation after the sweep, which could count a recyclable block's free lines
(its holes) as free, as the allocator does.

**Done when.** The target counts holes as free, and the suite and the compiler's timings (benchmarks.md §16.1) are no
worse.

---

## Character I/O locks the stream for every character

**Problem.** `reader.getChar` and `reader.more` call `fgetc`, and `writer.putChar` calls `fputc`
(`runtime/quest_stdlib.c`), each locking and unlocking the stream; that is most of wc-input1's and output1's time.
`getc_unlocked` in the reader, tried, made wc-input1 five times faster ([benchmarks.md](benchmarks.md) §3.4).

**Where to start.** The reader's and writer's character functions in `runtime/quest_stdlib.c`, with the stream's
locking taken once per call into the library rather than per character, or dropped where a stream has one thread.

**Done when.** The reader and writer use the unlocked calls (or an equivalent buffer of their own), and wc-input1 and
output1 are measured again.

---

## A closure and its environment are two allocations

**Problem.** A closure that escapes is a `QClosure` and a separate environment object, so making one allocates
twice ([benchmarks.md](benchmarks.md) §3.2). Inlining, contification, and escape analysis remove many closures, but
not those that are stored or returned.

**Where to start.** The closure's layout in `questlang/repr/layout` and its construction in the SSA builder
(`questlang/ssa/build/`), with the runtime's `QClosure` (`runtime/quest_runtime.h`, an ABI change).

**Done when.** A closure is one object, its environment inline, in both backends, or the idea is dropped with its
measurement.

---

## Single-word options as pointers: adopt the design or undo its rule

**Problem.** The language compares single-word options by component ([extensions.md](extensions.md), "Options as
Values") so that they could be held as nullable pointers, but that representation was deferred (2026-11-01): what
still allocates in the suite is options of `Int`, which it would leave boxed. Until it is adopted, the rule costs a
comparison of components and buys nothing.

**Where to start.** [option-values.md](option-values.md): its design, and what adopting or dropping it takes.

**Done when.** The representation is built, or the single-word `is` rule is undone in both compilers, the runtime,
the interpreters, the tests, and extensions.md, and option-values.md is deleted. Variants follow options' rule
(extensions.md, "Variants as Values", `quest_variant_is`): if the rule is undone, so is theirs, and compiled variants,
two words with no location, need a box or `is` on them is refused.

---

## The collector never moves objects

**Problem.** Minor collections leave small survivors scattered over nearly every block they filled, and their sticky
marks keep those lines until the next full collection, so allocation hops between ever smaller holes; only moving the
survivors gives the blocks back whole ([collector.md](collector.md) §3.6). Live lines are about twice live bytes after
the compiler's build and a long REPL session (collector.md §8.4, 2026-11-05). The owner chose on 2026-11-05 not to
take evacuation for now.

**Where to start.** The design in [collector.md](collector.md) §9.1 (evacuation after marking through a bounded slot
log, metadata allocated pinned at birth) and §9.2 (the three-state identity hash, serialization holding moves off);
the header's reserved bits in `runtime/quest_gc.h`.

**Done when.** The criteria of collector.md §9.1 are met, or the idea is dropped with its measurement.

---

## Generic allocation sites have no precise layouts

**Problem.** An aggregate allocated in generic code (`Tuple A Int end` in a polymorphic function, `Array(A)`'s
elements) has ambiguous words, which the collector validates and which would pin their referents if objects moved
([collector.md](collector.md) §3.3). Worth doing only after evacuation, on its measured pinned fraction (decision 13).

**Where to start.** [collector.md](collector.md) §9.2: descriptor parameters (`DescriptorParam`) extended to
functions that allocate such aggregates, and an inline cache of the layout at the site; `repr/objectLayout` in both
compilers. An ABI change.

**Done when.** The criteria of collector.md §9.2 are met, or the idea is dropped.

---

## Incremental marking runs on the mutator's core

**Problem.** A full collection's cycle marks in slices inside the allocation slow path ([collector.md](collector.md)
§3.10). A marker thread would take that work off the mutator, at the cost of fences in the barrier's slow path and a
protocol for the shared bitmaps. No workload has shown the need (the compiler's build takes the same time with cycles
as without, collector.md §8.6, 2026-11-05); the owner chose on 2026-11-05 not to take it for now.

**Where to start.** [collector.md](collector.md) §9.3; write the protocol down before coding; a `concurrent` checking
mode beside `incremental` in `runtime/quest_gc.c`.

**Done when.** A measured workload shows the mutator paying for marking and the thread recovers it, or the idea is
dropped.

---

## Quest has no allocation-free check or typed overlay on raw memory

**Problem.** A module cannot be checked to allocate nothing, and unsound code reads raw memory by hand-computed
offsets (`os/value.fetch`, the JIT's session reading record payloads). Both are what a collector written in Quest
would need ([collector.md](collector.md) §3.11, §9.4), and both are useful on their own: for inlined externals and
loops that must not allocate, and for readable `os/value` code.

**Where to start.** The IR after escape analysis, for the check; *Typeful Programming* §9.2 (`Still` values) for the
overlay.

**Done when.** Either facility exists with tests, or the idea is dropped.

---

## A dynamic reader cannot read on after a document it refused

**Problem.** `dynamic.intern` reading documents one after another from one reader: once it refuses a document (one
that repeats a key, docs/dynamic.md §2.1, or any that does not decode), every later read from that reader raises
`dynamic.error` too, though the next document is well formed. Found 2026-11-15 writing
`tests/source/stdlib/dynamic_repeated_keys.quest`, which therefore reads each document from a file of its own.

**Reproduce.** A program that calls `dynamic.intern(reader.input)` three times, catching `dynamic.error` each time,
given on standard input three documents, one per line, the second repeating a key: the third read fails. Check every
target: compiled, the JIT, and both interpreters.

**Where to start.** How a read consumes its document before decoding it: `readDocument` and `dynamicIntern` in
`questlang/interpreter/builtins.mod.quest`, the bootstrap's `dynamic_reader.py`, and the runtime's reading in
`runtime/quest_serialization.c`. A refused document should be consumed whole, so the reader stands at the next one.

**Done when.** A read after a refused document reads the next one on every target, and `dynamic_repeated_keys` (or
a new test) reads its documents from standard input.

---

## Faults the wasm review reported that no probe reproduced

**Problem.** A review of the wasm backend (2026-11-15) reported three faults that probes written the same day did not
show, so nothing was planned for them:
- an `out` argument that needs a conversion and that the callee does not assign (a segmentation fault natively);
- subsumption of an auto value with a covariant record component (every mode gave the right answer);
- the JIT's "a use of variable qj_1_record (423), which nothing binds", for which the review gives no program.

**Where to start.** A program that shows one, run compiled, by the JIT, and by both interpreters.

**Done when.** A program shows one and it is fixed with that program as its test, or a review of the code finds the
fault gone.

---

## A whole-program build loses the exception of a generic helper inlined into a caller

**Problem.** A module's generic function that raises the module's own exception, such as
`let fail(A::TYPE): A = raise error end`, breaks a whole-program build (`--whole-program`, the arm64-whole mode) once
a call to it is inlined into `main` with nothing else left around it: the IR verifier (`QUEST_CHECK_IR=1`, which the
test runner sets) reports `main: variable 'error' is used outside its scope`, and without the verifier the build
carries the bad IR on. A plain `raise error end` in the same place is fine, and so is the helper when the call is not
reduced to the raise alone. Found 2026-11-18 by util/datetime's `add` and `diff`, which now raise directly.

**Reproduce.** `m.int.quest`: `interface M export error: Exception f(i: Int d: Int): Int end`; `m.mod.quest`:
`module m : M export let error: Exception = exception error: Ok end let fail(A::TYPE): A = raise error end let
f(i: Int d: Int): Int = fail(:Int) end`; and a program `import m : M; ... conv.int(m.f(1 2)) ...`. `QUEST_CHECK_IR=1
./quest --whole-program -o p p.quest` fails as above.

**Where to start.** How the whole-program inliner (`questlang/ir/`) brings a specialized generic function's body into
its caller: a reference to the defining module's top-level binding (here the exception) is not rewritten to the
binding the whole program has for it.

**Done when.** The reproduction builds and runs, a golden test of it runs in the arm64-whole mode, and util/datetime
may use such a helper again.
