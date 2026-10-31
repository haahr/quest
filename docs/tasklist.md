# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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

## Native code has no line tables

**Problem.** Programs compiled by the arm64 backend carry no DWARF line tables, so lldb cannot break on a Quest line
or show one in a backtrace ([arm64.md](arm64.md) §1, step 14, deferred by the user on 2026-10-31 while the backend
improvements rewrite the arm64 backend). The IR has source offsets only on the operations that can raise (arithmetic,
indexing, raises, option payloads), not on calls, lets, or control flow, so a table made from them alone would leave
most lines without an entry and show a frame's last arithmetic line rather than its call site.

**Reproduce.** `./quest compile --backend arm64 -o p p.quest` for a program of a few lines, then `lldb p`,
`breakpoint set --file p.quest --line 3`: no locations.

**Where to start.** Give every IR statement that lowering makes (lets, dos, returns, jumps, branches) the source
offset of the expression it comes from (`questlang/ir/lower.mod.quest`; printed only with `--show-offsets`, so the IR
goldens keep), carry it through the SSA's instructions (`questlang/ssa/nodes`, `ssa/build`) and the machine
instructions (`questlang/codegen/arm64/minst`), and have the printer emit a `.file` per source file (a merged
program's too, `nodes.site`'s numbering) and a `.loc` wherever the line changes. Coordinate with the backend
improvements plan ([backend-improvements.md](backend-improvements.md)), which owns those types until it is done.

**Done when.** Native code has `.file` and `.loc` directives for its source lines, and lldb shows a breakpoint's Quest
line and a backtrace's lines in a test program.
