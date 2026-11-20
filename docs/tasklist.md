# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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

## A closure and its environment are two allocations

**Problem.** A closure that escapes is a `QClosure` and a separate environment object, so making one allocates
twice ([benchmarks.md](benchmarks.md) §3.2). Inlining, contification, and escape analysis remove many closures, but
not those that are stored or returned.

**Where to start.** The closure's layout in `questlang/repr/layout` and its construction in the SSA builder
(`questlang/ssa/build/`), with the runtime's `QClosure` (`runtime/quest_runtime.h`, an ABI change).

**Done when.** A closure is one object, its environment inline, in both backends, or the idea is dropped with its
measurement.

---

## `maybe.T` is abstract, so every test of one in another module is a call

**Problem.** `util/maybe` exports `T` abstract, though it is only `Option none some with val: A end end` and has no
invariant to protect. Separate compilation inlines nothing across modules ([ir.md](ir.md) §8.6), so outside
`util/maybe` every `isSome`, `isNone`, `unwrap`, and `some` is a call, where a visible type would let code write
`o?some` and `o!some.val`, inline. Measured in [iter-plan.md](iter-plan.md) §2: a `filter` reaching its held element
through `util/maybe` took 305 instructions per element, and the same stage with an option type of its own, 143.

**Where to start.** Make `T` manifest in `lib/util/maybe.int.quest` (choosing the field's name for good, perhaps
`value`, since it becomes public). Then:

- see what the dynamic format's change touches: a type mentioning `maybe.T` is encoded today as an abstract node
  ([dynamic.md](dynamic.md) §2.3) and would become an option type, so values externed before would not intern;
- update the goldens that print the type;
- rewrite the compiler's hottest call sites to the inline forms, and measure the driver build's instructions retired
  (`/usr/bin/time -l`).

Every importer rebuilds once, since the interface's fingerprint changes. Calls of `isSome` and the rest stay calls, so
only code that uses `?some` and `!some` gains.

**Done when.** `maybe.T` is public and the compiler's hot paths use the inline forms, with the measurement in
benchmarks.md, or the idea is dropped with its measurement.

---

## A whole program does not inline through a module's abstract type

**Problem.** Under `--whole-program`, a value that a module hands out as its abstract type is bound by a `let` that
changes its type (`let %19: iter.T(Int) = %18`, the tuple at the abstract type), and the simplifier does not see
through that copy when it folds `tuple_field` of a known tuple. So an iterator's closures stay closures called
through the tuple: `benchmarks/iter/`'s `map` takes 56 instructions per element in a whole program, where the same
library with `T` visible takes 11, its pipeline folded into the loop ([iter-plan.md](iter-plan.md) decision 2). Any
module whose abstract type is a tuple of closures, or of known values, pays the same.

**Plan.** [abstract-inlining-plan.md](abstract-inlining-plan.md): the fold, measured with a prototype (56 → 11),
what else it reaches, and its steps.

---

## An interface may declare a member twice

**Problem.** Both typecheckers accept an interface that declares the same member twice, with different types, and a
module that defines it twice to match. The self-hosted compiler builds and runs the program; the bootstrap's C fails
to compile, with `redefinition of typedef 'quest_sig_util__Regexp_matches'`. It was found by adding an iterator
`matches(r: T s: String): iter.T(Match)` to `util/regexp`, which already had `matches(r: T s: String): Bool`
([iter-plan.md](iter-plan.md) step 3, where the iterator became `findIter`).

**Reproduce.** Add `matches(r: T s: String): iter.T(String)` to `lib/util/regexp.int.quest` beside the existing
`matches`, and a `let matches` to match after the existing one in the module: `./quest --stop-after typecheck` and
`./questboot --stop-after typecheck` accept the module, and `run_tests.py -k stdlib/regexp_operations --phase
run_c_compiled` fails in the bootstrap's C. (A smaller case, not yet tried: an interface declaring `f` twice.)

**Where to start.** The checks of an interface's declarations in `questlang/typechecker/` (where a duplicate type
or exception name would be caught, if one is) and `bootstrap/python/quest/typechecker/`, and a module's lets
against its interface.

**Done when.** Both compilers reject a repeated member name in an interface, with the same message, and an error
test under `tests/errors` shows it.

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

