# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## The self-hosted compiler loses the messages of errors in imported modules

**Problem.** When a module that a program imports fails to compile, `./quest` reports the error at the module's first
line with no message (`x.mod.quest:1:1: error:` and nothing after it), so its text, its location, and the "imported
here" note are all lost. `./questboot` reports the same error in full, and `./quest` does too when given the module
itself. It was met while writing the MLton-gap plan's passes, where a type error in an edited compiler module showed
only as `simplify.mod.quest:1:1: error:`.

**Reproduce.** In an empty directory, `x.int.quest` (`interface X export f(n: Int): Int end`), `x.mod.quest` (`module
x : X export let f(n: Int): Int = n + true end`), and `p.quest` (`import x : X; x.f(1)`). `./quest --build-dir b
p.quest` prints `x.mod.quest:1:1: error:` with an empty message; `./questboot --build-dir b2 p.quest` prints
`x.mod.quest:3:30: error: Type mismatch: synthesized type 'Bool' is not a subtype of expected type 'Int'`, the line
and caret, and `p.quest:1:10 ... note: imported here`; `./quest --build-dir b3 --stop-after typecheck x.mod.quest`
prints the error in full.

**Where to start.** The path an error takes out of an imported unit's compilation: `questlang/types/env.mod.quest`,
which relocates it with `diagnostics.inFile` and `diagnostics.atImport` (around lines 298–333), and those functions in
`questlang/common/diagnostics.mod.quest`; then `questlang/build/engine.mod.quest`, if the error comes back from a
unit the build engine compiled. Compare the bootstrap's `at_import` in `bootstrap/python/quest/diagnostics.py`. The
lost text suggests the error is rebuilt from a value that has no message or offset, rather than passed on.

**Done when.** `./quest` reports the error in an imported module as `./questboot` does (message, location, and the
"imported here" note), and an error test under `tests/` (with its `tests/golden/self-hosted/errors/` golden) shows it.

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

## Making a string of one character allocates and copies it twice

**Problem.** `quest_string_alloc` (`runtime/quest_runtime.c`), which `stringOp.new(size init)` calls, fills a buffer
of its own and passes it to `quest_string_new`, which allocates another buffer and copies the first into it: twice
the allocation and copying a new string needs. A performance problem, not a wrong result.

**Where to start.** `quest_string_alloc`: allocate the buffer and then the `QString` itself, as `quest_string_new`
does (in that order, so that its stores need no write barrier: docs/collector.md section 3.5), and fill the one
buffer.

**Done when.** `quest_string_alloc` allocates one buffer, and the suites pass.

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
