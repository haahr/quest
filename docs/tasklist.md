# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Parallel builds in the self-hosted engine

**Problem.** The self-hosted build engine (`questlang/build/engine`) compiles one unit at a time, in its own process,
so a build uses a single core. Building `questlang/driver/main` takes about 8 minutes. Building the questlang tests
for the self-hosted suite takes several more, nearly all of it compiling the questlang modules they share. The tests
build one after another into a shared build directory (`build_questlang_tests` in
`bootstrap/python/quest/testing/runner.py`), because the engine takes no locks: two builds at once could both find a
unit stale and write its artifacts at the same time.

**Reproduce.** Run `./questc` after touching `questlang/types/model.mod.quest`, or `run_tests.py --self-hosted`, and
watch the CPU: one `questlang-driver` process at 100% of one core.

**Where to start.** Add `-j N` to the driver and have the engine compile up to N units at once, each in a child process
of the driver (a `--compile-unit` mode, or `-c` with `--build-dir`). This needs a way to start processes without
waiting for them; see the proposed `io/process` library. The engine first has to know the import graph before
compiling anything: parse each unit's imports, which is cheap, instead of finding them as it compiles. A unit can
compile once the interfaces it imports have their `.qi` files. Modules depend only on interfaces, not on other
modules' objects, so most modules can compile in parallel once the interfaces are built. Keep the queue order for
linking and for the log, so that build output stays deterministic. Then build the questlang tests with one driver
invocation that takes every test as a root, or with `-j`, instead of one at a time.

**Done when.** `./questc -j 8` and the self-hosted suite's questlang test build use several cores. Their artifacts are
byte-identical to a serial build's, apart from build.log's order, and the driver build is several times faster.
