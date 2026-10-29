# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Faster word operations in compiled code

**Problem.** Each `word` operation in compiled code (`word.xorBits`, `word.shift`, `word.rotate`, and the rest of
`lib/word.int.quest`) costs three calls. The caller calls the importer's wrapper `qv_word_xorBits`, which calls
through the closure in the `word` module record, which calls the external `quest_word_xor_bits` in the runtime. None
of them can be inlined, because the module record is only filled in at run time. The self-hosted compiler hashes
type text with SHA-256 written in Quest (`questlang/codegen/sha256`) and hashes keys in `util/hash`, both made of word
operations. Profiling the compiler building itself (2026-10-27) put about 7.5% of its time in these call layers.

**Reproduce.** Build `questlang/driver/main` with `./questc` from nothing under `sample` (macOS) or `perf`, and
compare the time in the `qv_word_*` wrappers and closures with the time in the `quest_word_*` functions.

**Where to start.** Compile a call to a `word` operation whose target is known statically into a direct call to its
runtime function, or into the C operator (`^`, `<<`, ...) for the simple ones. An importer does not know today which
members of `word` are externals, or which runtime functions they are: neither the `.qi` nor the `.qm` records it, so
either the artifacts record it (an ABI change) or the backend treats `word` as a builtin it knows. Do the same in the
bootstrap, and in the same commit, while the two compilers are kept in step. Every compiled program's C changes, which
`tools/c-diff` shows. A native SHA-256 primitive would remove most of the remaining cost of `layout`'s
digests, but needs a new runtime primitive and so a release before `questlang/` can use it (docs/release-compiler.md
§2).

**Done when.** Word operations in generated C are direct calls or C operators, the self-hosted build of
`questlang/driver/main` spends no measurable time in the call layers, and both compilers produce the same C.

---

## Objects compiled with and without the collector share a build directory

**Problem.** A build's staleness check (`unit_staleness`) compares an object with its sources and imports, but not
with whether it was compiled for the collector, so a build with `--nogc` reuses objects that a build without it left
in the same build directory, and the reverse. The objects disagree about allocation, and the link fails (`_GC_init`
undefined) or the program mixes allocators. Both compilers do it.

**Reproduce.** In an empty directory holding `p.quest` (`1 + 1`), `./quest compile p.quest`, then `./quest compile
--nogc p.quest -o n`: the link fails. `./questc` fails the same way.

**Where to start.** `_unit_staleness` in `bootstrap/python/quest/build/engine.py` and `unitStaleness` in
`questlang/build/engine.mod.quest`. Record the collector setting in each unit's `.qm` and treat a unit as stale when
it differs (an ABI change, since the manifest format changes), or keep the two kinds of object apart, in a
subdirectory of the build directory for `--nogc`, as the runtime's objects already are by their flags.

**Done when.** Builds with and without `--nogc` can alternate in one build directory, in both compilers, and a test
does it.
