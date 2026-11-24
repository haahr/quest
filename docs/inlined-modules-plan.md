# Plan: Library Modules Inlined into Their Importers

A plan for the tasklist entry "A few library modules inlined into their importers, as in a whole program"
([tasklist.md](tasklist.md)): separately compiled units copy the small functions of `util/maybe`, `util/iter`, and
`collections/vector` from their sources, so that the inliner and the specializer see them, while each module's state
stays single. Self-hosted compiler only. The bootstrap is untouched: behavior goldens stay shared, and its output
does not change.

**Status (2026-11-23):** rewritten after the first design was built, measured, and found to cost a build 3.4 times
its instructions. The second design (§2) is built: a build of the compiler costs 1.33 times one without copies, the
compiler it makes retires 3.5 to 7% fewer instructions, and `benchmarks/iter`'s pipelines run as a whole program's
do ([benchmarks.md](benchmarks.md) §43). §3 says why the first design cost what it did, §4 what is left, and §5
what is open. The design as it stands is described in [ir.md](ir.md) §8.6 and [build-process.md](build-process.md)
§4; this document goes when §4 is done.

## 1. What it is for

[benchmarks.md](benchmarks.md) §36 built whole programs with the three modules kept apart. In `benchmarks/iter` they
account for all of a whole program's gain (`filter`: 153 instructions per element separately, 45 whole), and in the
compiler for 56% of it. A whole program costs 3.6 times the instructions of a separate build and gives up parallel
and incremental builds, so the question was how much of that gain a separate build can have, and for how much.

`tools/perf/crosscalls.py` counts the call sites between modules in a separate arm64 build. For the compiler:
`collections/vector` 12,093 (4,040 to small members), `util/maybe` 11,952 (9,908), `collections/hashMap` 4,246 (92),
`util/stringBuilder` 1,273, `util/strutil` 602, `util/hash` 190, `util/iter` 96. The list is the first three;
`collections/hashMap` is the next candidate, and few of its calls are to small members.

## 2. The design

- **The list.** `questlang/modules/inlined` holds the library's three. `--inline-module M` adds a module, its path
  resolved as the program's imports are, and `--no-inline-library` drops the library's. The driver forwards the set
  to its workers.
- **Copies.** An importer elaborates an inlined module's source and holds a copy of what it reaches of it
  (`ir/opened`): a `nodes.Module` named `opened/<module>`, with no exports, its symbols the unit's own. The copy keeps
  functions and scalar constants. A member with identity (an exception, a string, a variable, anything computed) is
  read from the compiled module's record, and a function that reaches a private one is not copied, so the module's
  state stays single and its object needs no new exports. Copies are pruned to what the unit reaches, before the
  simplifier and after it.
- **A bound on what is copied.** A function larger than its bound, by the inliner's measure of its body (statements,
  a call counting 2), is left out, with the functions that use it, and its calls stay calls of the compiled module.
  What a unit copies it compiles again, and the large functions cost most and gain least (§3.3), so a function of
  data alone has a bound of 15, which leaves `vector.append` (46) a call. A function that takes or returns a
  function, or a value that holds one, gains by its
  caller's functions being known in its body (§3.5), and its bound is the largest function the inliner takes at a
  call with type arguments, its threshold and polymorphic bonus (60): a larger one would not be inlined. The type is
  searched through aliases, applications, and the representations of inlined modules' abstract types, which the
  importer holds before it copies a module that names them: an iterator is a tuple of two functions in `util/iter`'s
  source, and is one in `collections/vector`'s copy too (`vector.iter`). No module is named, and no bound is a
  module's own. Of the three modules' 75 functions, 32 over 15 pass functions (26 of
  `util/iter`, and `vector.forEach`, `fold`, `iter`, `iterReversed`, `appendIter`, and `fromIter`), the largest 60.
  With `vector.iter` copied, a filter, map, and sum over a vector of 20 million has no call in its loop, and the
  program retires 4.89 G instructions against 5.15 G (2.44 G as a whole program, whose `append`s are inlined too). `QUEST_INLINE`'s `copy` and `copyFun` set the two
  bounds, for measuring.
- **Every shape stays opaque.** The unit's types are laid out as they are without copies. A copy's code names the
  abstract types' representations, and meets the unit's values through the conversions represent already has for a
  module's member called at its interface's type (`represent.call`, and the `let`s the inliner binds parameters
  with). Where an abstract type's generic and native layouts agree (`vector.T(Int)`, `maybe.T(Real)`), the conversion
  changes no value. Where they do not (`iter.T(Real)`, whose closures' signatures change with `Real`), converting
  would copy the value, so the call is not of the copy at all: `opened.rewriteRefs` leaves it a call of the compiled
  module, the inliner refuses it, and the specializer already kept such calls generic
  (`genericLayout.abstractLayoutsDifferAt`, over the test the specializer had). `repr/shapes`, the type model, the
  records' names, and the C printer's declarations are as they were before any of this.
- **Staleness.** The `.qi` of an inlined module's interface holds `"inlined": true`, and is fresh only while that
  agrees with the build's set. A unit's `.qm` holds `inlined_modules`, the set it was compiled with, and
  `inlined_sources`, the sources it copied from; the unit is stale when the set differs or a source is missing or
  newer. Units that copy a module and units that do not link together, so nothing else has to agree.
- **Where sources are loaded.** Compiling to C or assembly, an import is typed against its interface; an inlined
  module's source is loaded as well (`e.openInlined`). An interface's compile and the JIT do not load it.
- **Initializers.** A module file's initializer calls its copies' initializers after its imports'.
- **Tests.** The phases that print compiler output run with `--no-inline-library`, so that their goldens do not
  change with the library's bodies; `(* @inline-library *)` and `(* @inline-module: M *)` opt in (testing.md §2.5).
  `modules/inlined_module_state` tests identity across copied and compiled code with `--inline-module`, at `Int` and
  at `Real`. `modules/inlined_library` shows, in its simplified IR and SSA, what a default build inlines.
- **Version and stack.** ABI 91, for the `.qi` mark. Every program is linked with a 64 MB main stack on macOS (both
  compilers, exceptions.md §6): the interpreter's frames grew with inlining.

## 3. The first design, and what was measured

### 3.1. Transparency per application

The first design made the unit's shapes see through an inlined module's abstract type at each application whose
layouts agree, as a whole program's shapes see through all of them: `shapes.openedTransparent`, by a filtered
substitution over each type before its shape was taken. It was 342 lines of `repr/shapes`, with records' names, the
C printer's aggregates, and a shape cache emptied whenever a representation was registered. Both crashes met while
building it were layout disagreements between a transparent and an opaque view of one type.

It cost 3.4 times a separate build's instructions for 2.6 to 4.8% fewer in the compiler built. A whole program costs
3.6 times, which had not been measured before.

### 3.2. Where its cost was

The driver's build, one process (`-j 1`, arm64), in G instructions retired, which load does not change. "Nothing
copied" loads and lowers the sources and copies no function (`copy=0`).

| Build | Transparent | Opaque |
|---|---:|---:|
| No inlined modules | 491 | 456 |
| Nothing copied | 1,437 (2.93×) | 510 (1.12×) |
| Functions of size 15 or less | 1,518 (3.09×) | 592 (1.30×) |
| No bound | 1,808 (3.68×) | 840 (1.84×) |

Most of the transparent build's cost was paid before any function was copied. In a profile of that build, 65% of
the samples were under `openedTransparent`, called on shape-cache misses: substituting through a type before taking
its shape costs in proportion to the type, at every new type node. Emptying the cache less often saved 11 to 17% and
made 68 units' code depend on what the process had compiled before, so it was not kept. The costs suspected earlier
(the inliner's growth, the back end on bigger functions, elaborating the sources in every unit) are what is left in
the opaque column: 54 G for the sources, the rest in proportion to what is copied.

Before that, one real cost was found and fixed on its own (`2d5fe8a5`, benchmarks.md §39): a one-block large object
scanned the collector's whole block table on every allocation.

### 3.3. What the bound buys

Opaque builds at each bound, and each compiler then building the same tree without copies, median of three runs
(a compiler's count varies by 4%, sometimes 8%, with its addresses):

| `copy` | Build | Peak memory | `__TEXT` | The compiler built |
|---|---:|---:|---:|---:|
| no inlined modules | 456 | 4.4 GB | 11.4 MB | 514 |
| 0 | 510 (1.12×) | 5.0 GB | 11.4 MB | |
| 5 | 545 (1.19×) | 4.9 GB | 12.3 MB | 510 |
| 15 | 592 (1.30×) | 6.2 GB | 12.9 MB | 477 |
| 30 | 652 (1.43×) | 9.3 GB | 13.5 MB | 473 |
| 60 | 833 (1.83×) | 13.2 GB | 15.4 MB | 466 |
| none | 840 (1.84×) | 14.2 GB | 15.4 MB | 463 |

The opaque compilers at 15 and with no bound gained what the transparent ones did. Each of them built the tree's 216
units to the same assembly, objects, and manifests as the compiler without copies.

### 3.4. Tried with the first design, and dropped

- **A cache of elaborated inlined modules** across a process's units, in three versions (§6.6 of this document's
  earlier form, `afc4c4ce`): it saved 17% of the transparent build, where elaboration fed the shapes' cost. In the
  opaque build the sources cost 54 G of 592 in all, and the cache's key (the expected interface, the imports'
  interfaces, the search roots, the variant) is easy to get wrong, so none of it is in.
- **No effect:** memoizing `openedTransparent`, an inliner budget that left the copies out, `vector.append`'s grow
  path out of line.
- **Exports for openers:** not needed, since a function that reaches private state is not copied.

### 3.5. Functions that pass functions want a larger bound

`benchmarks/iter`, instructions retired per element, each build made clean:

| Workload | No inlined modules | `copy` 15 | 30 | 60 | none | Whole program |
|---|---:|---:|---:|---:|---:|---:|
| `map` | 83.1 | 29.1 | 15.1 | 9.1 | 9.1 | 9.1 |
| `filter` | 151.6 | 125.6 | 117.6 | 44.1 | 44.1 | 44.1 |
| `sumInt` | 140.1 | 125.1 | 117.1 | 44.1 | 44.1 | 44.1 |

With its stages copied, a separately compiled pipeline is a whole program's. So such functions have their own bound (§2);
at first `util/iter` had none, by its name.

## 4. What is left

tools/check passed on the second design (2026-11-23), with the arm64 and C fixed points, but for two tests that
fail on main without it: `test_walkthrough`'s two argmax excerpts, and a whole program that imports
`collections/vector` and uses `conv` without importing it, which links `string` twice.

1. Push, and a release, whose compiler is then the faster one.
2. Retire this document: the open items below to [tasklist.md](tasklist.md), and the comments that name it
   (`ir/opened`, `modules/inlined`, `driver/options`, `tools/perf/crosscalls.py`, the tests) to ir.md §8.6.

## 5. Open

- **The sources' 12%.** Every unit that imports an inlined module elaborates and lowers its source. The module's
  own compile could write its lowered IR beside its object for importers to read, which needs an IR serialization
  and builds ordered so that importers wait.
- **Whole programs.** `shapes.transparent` substitutes before the cache as `openedTransparent` did, and whole
  programs cost 3.6 times. A shape built structurally, taking a representation where it meets an abstract
  application and sharing the shapes of the parts, would not pay it. Not profiled.
- **Instances whose layouts disagree** stay calls. If iterators over `Real` or records matter, the conversion could
  be a view rather than a copy.
- **A program's own modules.** `--inline-module` is tested on one module of a test's. Nothing records the choice
  between builds but the `.qi` mark's freshness, and no error names a module it cannot serve (one with variants, or
  without a source).
- **`collections/hashMap`** as a fourth, measured the same way.
