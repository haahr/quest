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

## Objects compiled with and without the collector share a build directory

**Problem.** A build's staleness check (`unit_staleness`) compares an object with its sources and imports, but not
with whether it was compiled for the collector, so a build with `--nogc` reuses objects that a build without it left
in the same build directory, and the reverse. The objects disagree about allocation, and the link fails (`_GC_init`
undefined) or the program mixes allocators. Both compilers do it.

**Reproduce.** In an empty directory holding `p.quest` (`1 + 1`), `./quest compile p.quest`, then `./quest compile
--nogc p.quest -o n`: the link fails. `./questboot` fails the same way.

**Where to start.** `_unit_staleness` in `bootstrap/python/quest/build/engine.py` and `unitStaleness` in
`questlang/build/engine.mod.quest`. Record the collector setting in each unit's `.qm` and treat a unit as stale when
it differs (an ABI change, since the manifest format changes), or keep the two kinds of object apart, in a
subdirectory of the build directory for `--nogc`, as the runtime's objects already are by their flags.

**Done when.** Builds with and without `--nogc` can alternate in one build directory, in both compilers, and a test
does it.

---

## A case's binder is boxed again when its body stores it

**Problem.** The represent pass's slots step (docs/ir.md §8.3) remembers the box a record or variant was read from,
so that storing the value into another slot reuses the box (boxes are immutable) rather than allocating another. A
switch case whose binder takes a boxed payload binds the binder to the payload's box (`unboxBinder`), but the step
decides the slots of a statement's bodies before the statement's own, so the case's body has already been rewritten
by the time the box is remembered: storing the binder into a slot in the body (a field of a new record, an element of
an array) makes a new box. A performance problem, not a wrong result. Both compilers do it.

**Reproduce.** A switch over a variant whose case payload is a record, the case's body putting the binder in a new
record; `--dump-after ir_represented` shows a `slot_box` of the binder in the body where the binder's box would serve.

**Where to start.** `body` and `statement`'s `sSwitch` case in `questlang/ir/slots.mod.quest` (`variantCase`,
`optionCase`, `unboxBinder`), and `body`, `variant_case`, `option_case`, `unbox_binder` in
`bootstrap/python/quest/ir/slots.py`: bind each case's binder to its box before its body is decided. The IR and SSA
goldens of the tests whose cases store their binders change.

**Done when.** A stored binder reuses its payload's box in both compilers, the goldens show it, and the benchmarks
(docs/benchmarks.md) are measured before and after.

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
