"""Runs the tests a change needs before it is pushed (docs/testing.md section
4.1), with the suites that it needs at once, the machine's cores split
between them.

    tools/check                    the suites the change needs, from the files it changes
    tools/check --self-hosted-only the self-hosted compiler's suites alone, whatever the change
    tools/check --all              every suite, whatever the change
    tools/check --stress           the stress tier alone
    tools/check --no-stress        the suites without the stress tier before them
    tools/check --light            the checks a move of modules needs, not a push's
    tools/check --jobs N           any of these with N cores, not the machine's
    tools/check --serial           any of these with the suites one after another
    tools/check --no-exclusive     any of these without taking the machine-wide lock

Each takes the lock that tools/exclusive takes (docs/testing.md section 4.2):
it waits for any other worktree's check or timing to end, and holds the lock
until it is done, so that no other heavy job loads the machine meanwhile. It
does not wait for the load to fall first, as a timing does: a check's results
do not depend on its speed, but for its timeouts, and when the only failures
are timeouts and the terminal tests, each is run again, alone, once, and the
run passes if they pass then.

The change is what differs from origin/main: the commits since they diverged,
and what is not yet committed. A change only to the self-hosted compiler, its
own goldens and pending lists, the docs, or Markdown files anywhere (README.md;
self_hosted_only_file) needs the self-hosted compiler's suites alone; any other
change needs every suite.

The self-hosted compiler's suites, run at once: the self-hosting check
(run_tests.py --self-hosting --seed release, which ends by running the
self-hosted suite with stage 2), the fixed point through arm64 (stages 2 and 3
built by it, which must write what stage 1 wrote: docs/arm64.md section 3.12), each
self-hosting check also checking the whole-program fixed point through its
backend (stage 2's whole-program build writes stage 2's whole-program code), and
the backends' suite (the self-hosted suite's compiled tests through the SSA's C
printer, ssac, for every unit; through the native arm64 backend, for every unit,
and for the program's alone; and whole programs through arm64:
docs/arm64.md section 4; and the wasm backend in node, and for a change to its
own files, WASM_PATHS, in wasmtime and as the driver compiled to wasm runs
each program by its JIT), whose compiled tests run under the collector's
`incremental` mode (a full collection's marking always under way in slices of
one object, each cycle's marks checked against a stop-the-world marking:
docs/collector.md section 7). Every suite adds, at once, the bootstrap's
suite and the unit tests but those that drive a terminal, and then, alone, the
terminal tests, which time out under load.

Before the suites, the stress tier (docs/testing.md section 4.1): the compiled
tests alone, under the collector's `stress` mode (a collection at every
allocation, thinning as a program's heap grows: docs/collector.md section 7)
with the other checks and `sites`, through ./quest's stage 2 and the arm64
backend, the C backend, and the JIT, and through the bootstrap's C. It takes
minutes, and finds a store without a barrier or a root left out within a few
allocations of the fault, which the suites' collections, megabytes apart,
reach only by chance; when it fails, the suites are not run.

Left to run by hand (docs/testing.md section 4.1): ssac's other modes and its
fixed points, since arm64 tests the SSA they share and the plain mode keeps
ssac's C printer working; arm64-modules, the boundary arm64-program tests from
the other side; c-whole, since the self-hosted suite runs the C backend and
arm64-whole whole programs; the JIT's modes, jit and jit-files, whose tests the
stress tier (jit-files) and the self-hosted suite's jit_hosts check (the
REPL's transcripts through an arm64-built driver's JIT) run; and the IR runs between Core and the described stage
(SKIPPED_PHASES), whose failures the described stage's run and the compiled
runs still show. Each suite builds into a temporary directory of its own, so
they do not interfere. Their output is kept in .build/check/SUITE.txt, and each
suite's summary is printed with when it finished. The exit status is 0 when
every suite passes.

--light is for a series of moves of modules (docs/testing.md section 4.1),
which can break a build but not a behavior: the self-hosted fixed
point through arm64, then the tests that import compiler modules
(tests/source/questlang) with its stage 2; every module of the bootstrap
imported; and the unit tests but those that drive a terminal. It is not enough
for a push, which needs the suites above.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

import exclusive  # noqa: E402
OUTPUT_DIR = ROOT_DIR / ".build" / "check"
# The unit tests that drive a terminal (tests/python/test_readline_terminal.py)
PTY_TESTS = "tests/python/test_readline_terminal.py"
# The paths a change may touch and still need the self-hosted compiler's suites
# alone: its sources, its own goldens (its IR and SSA dumps among them) and
# pending lists, and the docs
SELF_HOSTED_ONLY_PATHS = ("questlang/", "tests/golden/self-hosted/", "tests/golden/ir_", "tests/golden/ssa/",
                          "tests/self-hosted/", "docs/")


# The paths a change may touch and need the wasm backend's own modes, wasm
# (wasmtime) and wasm-jit (the driver compiled to wasm, its JIT running each
# program in node): its code generator and runtime, the JIT, a module's wasm
# variant, the library its externals table covers, the page, and its own
# tests. Every other change runs wasm-node alone of the three, which compiles
# every program as they do, and the self-hosted checks' wasm self-compilation
# (tests/self-hosted/wasm_selfcompile.py), which builds the wasm-jit mode's
# driver and must find it compiling itself to what the native compiler writes.
WASM_PATHS = ("questlang/wasm/", "runtime/wasm/", "questlang/jit/", "lib/", "tools/wasm-page/",
              "tests/self-hosted/pending-wasm", "tests/self-hosted/wasm")


def wasm_file(path: str) -> bool:
    """Whether a changed file needs every wasm mode"""
    return path.startswith(WASM_PATHS) or path.endswith(".wasm.mod.quest")


def self_hosted_only_file(path: str) -> bool:
    """Whether a changed file needs no more than the self-hosted compiler's
    suites: one of its own, or documentation, which no test reads."""
    return path.startswith(SELF_HOSTED_ONLY_PATHS) or path.endswith(".md")


# The IR runs left to run by hand: those between Core and the described stage
SKIPPED_PHASES = ("run_ir_simplified", "run_ir_specialized", "run_ir_closed", "run_ir_represented")
# The checks every compiled program the suites run makes (docs/collector.md
# section 7), and the stress tier's: a collection at every allocation too,
# until 1024 MB of heap has been walked at each rate, and the allocating
# functions kept for a failure's report. Where a compiler builds a test and
# runs it, the test alone is under stress (QUEST_GC_CHECK_CHILDREN), since
# the compiler under it takes ten times as long; the JIT's suite, where the
# two are one process, is where the compiler is, at a quarter of the budget
CHECKS = "layouts,roots,poison,barriers"
STRESS = CHECKS + ",stress,sites"
STRESS_ENVIRONMENT = {"QUEST_GC_CHECK": STRESS, "QUEST_GC_STRESS_BUDGET": "1024"}
STRESS_PROGRAMS_ENVIRONMENT = {"QUEST_GC_CHECK": CHECKS, "QUEST_GC_CHECK_CHILDREN": STRESS,
                               "QUEST_GC_STRESS_BUDGET": "1024"}
STRESS_JIT_ENVIRONMENT = {"QUEST_GC_CHECK": STRESS, "QUEST_GC_STRESS_BUDGET": "256"}
# The backends' suite: its compilers under the suites' checks, the tests they build and run under `incremental`
INCREMENTAL_PROGRAMS_ENVIRONMENT = {"QUEST_GC_CHECK_CHILDREN": CHECKS + ",incremental,sites",
                                    "QUEST_GC_STRESS_BUDGET": "1024"}


class Suite:
    """A suite's command, and once it has run, its status and when it ended."""

    def __init__(self, name: str, command: list[str], environment: dict[str, str] | None = None):
        self.name = name
        self.command = command
        self.environment = {**os.environ, **(environment or {})}
        self.output = OUTPUT_DIR / f"{name}.txt"
        self.returncode: int | None = None
        self.finished = 0.0

    def run(self, start: float) -> None:
        with self.output.open("w", encoding="utf-8") as out:
            self.returncode = subprocess.run(self.command, stdout=out, stderr=subprocess.STDOUT, cwd=ROOT_DIR,
                                             env=self.environment).returncode
        self.finished = time.monotonic() - start

    def summary(self) -> list[str]:
        """The lines of its output that sum it up: run_tests.py's summary and
        the tests that failed, or unittest's count and verdict."""
        lines = self.output.read_text(encoding="utf-8", errors="replace").splitlines()
        picked = [line for line in lines if line.startswith(("Summary:", "  Golden tests:", "  Error tests:", "Ran ",
                                                             "OK", "FAILED", "Fixed point", "Whole-program fixed point",
                                                             "Bootstrappable", "Stages 2 and 3", "=== Backend",
                                                             "  [FAIL]"))]
        return picked or lines[-3:]


# --serial: the suites run one after another, each with all the cores
SERIAL = False


def share(cores: int, numerator: int, denominator: int) -> int:
    """The workers a suite gets of cores: its share of them when the suites
    run at once, and all of them when they run one after another (--serial)."""
    return cores if SERIAL else max(1, cores * numerator // denominator)


def together_word() -> str:
    """How the suites run, for the messages that announce them."""
    return "one after another" if SERIAL else "at once"


def run_at_once(suites: list[Suite], start: float) -> None:
    """Runs the suites, at once, or one after another with --serial."""
    if SERIAL:
        for suite in suites:
            suite.run(start)
        return
    threads = [threading.Thread(target=suite.run, args=(start,)) for suite in suites]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def report(suites: list[Suite], start: float) -> list[str]:
    """Prints each suite's verdict and summary; the names of those that failed."""
    failed = []
    for suite in suites:
        verdict = "passed" if suite.returncode == 0 else f"FAILED (exit {suite.returncode})"
        print(f"== {suite.name}: {verdict}, finished at {suite.finished:.0f}s")
        for line in suite.summary():
            print(f"   {line}")
        if suite.returncode != 0:
            failed.append(suite.name)
    print(f"Elapsed {time.monotonic() - start:.0f}s"
          + (f"; failed: {', '.join(failed)} (see {OUTPUT_DIR.relative_to(ROOT_DIR)}/)" if failed else "; all passed"),
          flush=True)
    return failed


def timed_out(output: str) -> list[tuple[str, str]] | None:
    """The tests a run_tests.py run's output says failed, as (phase, test),
    if every one of them timed out; None if any failed otherwise, or if the
    run failed and names no test that did."""
    lines = output.splitlines()
    tests = []
    for i, line in enumerate(lines):
        if line.startswith("  [FAIL] ") and ":" in line:
            following = lines[i + 1] if i + 1 < len(lines) else ""
            if "TIMED OUT" not in following:
                return None
            phase, _, test = line[len("  [FAIL] "):].partition(":")
            tests.append((phase, test))
    return tests or None


def alone(command: list[str], phase: str, test: str) -> list[str]:
    """command, a run_tests.py run, narrowed to one test in one phase, on one
    worker."""
    narrowed = []
    skip = False
    for argument in command:
        if skip:
            skip = False
        elif argument in ("-j", "--phase", "-k", "--test"):
            skip = True
        else:
            narrowed.append(argument)
    return [*narrowed, "--phase", phase, "-k", test, "-j", "1"]


def rerun(failed: list[Suite], start: float) -> bool:
    """Runs again, alone and once each, the failures that load explains: the
    terminal tests' suite, and the tests that timed out. Whether every
    failure was one of those and passes now; nothing is run if any failure
    was of another kind."""
    plan = []
    for suite in failed:
        if suite.name == "pty":
            plan.append(Suite("pty-again", suite.command, suite.environment))
            continue
        tests = timed_out(suite.output.read_text(encoding="utf-8", errors="replace"))
        if tests is None:
            return False
        for n, (phase, test) in enumerate(tests):
            plan.append(Suite(f"{suite.name}-again-{n + 1}", alone(suite.command, phase, test), suite.environment))
    print(f"Running again, alone: {', '.join(suite.name for suite in plan)} (timeouts and terminal tests, which "
          "load explains)", flush=True)
    for suite in plan:
        suite.run(start)
    return not report(plan, start)


def outcome(suites: list[Suite], start: float) -> bool:
    """Reports the suites; whether they passed, their timeouts and terminal
    tests once run again alone (rerun)."""
    failed = report(suites, start)
    return not failed or rerun([suite for suite in suites if suite.name in failed], start)


def stress_tier(python: str, cores: int, self_hosted_only: bool) -> bool:
    """Runs the stress tier; whether it passed. The driver is ./quest's stage
    2, built first without the checks (the launcher builds what is stale)."""
    environment = {name: value for name, value in os.environ.items() if not name.startswith("QUEST_GC_")}
    build = subprocess.run([str(ROOT_DIR / "quest"), "-e", "ok"], cwd=ROOT_DIR, env=environment, capture_output=True,
                           text=True)
    if build.returncode != 0:
        print(f"The stress tier's driver did not build:\n{build.stdout}{build.stderr}")
        return False
    driver = ROOT_DIR / ".build" / "quest-stages" / "stage2" / "quest"
    run_tests = [python, str(ROOT_DIR / "run_tests.py"), "--timeout", "120", "-j", str(share(cores, 1, 3))]
    self_hosted = [*run_tests, "--self-hosted", "--self-hosted-driver", str(driver)]
    suites = [
        Suite("stress-arm64", [*self_hosted, "--backend", "arm64"], STRESS_PROGRAMS_ENVIRONMENT),
        Suite("stress-c", [*self_hosted, "--phase", "run_c_compiled"], STRESS_PROGRAMS_ENVIRONMENT),
        Suite("stress-jit", [*self_hosted, "--backend", "jit-files"], STRESS_JIT_ENVIRONMENT),
    ]
    if not self_hosted_only:
        suites.append(Suite("stress-bootstrap", [*run_tests, "--phase", "run_c_compiled"], STRESS_ENVIRONMENT))
    start = time.monotonic()
    print(f"Running the stress tier ({', '.join(suite.name for suite in suites)}) {together_word()}; output in "
          f"{OUTPUT_DIR.relative_to(ROOT_DIR)}/", flush=True)
    run_at_once(suites, start)
    return outcome(suites, start)


def changed_files() -> list[str] | None:
    """The files that differ from origin/main: in the commits since the two
    diverged, and not yet committed (untracked files included). None if git
    cannot say."""
    def git(*arguments: str) -> list[str] | None:
        process = subprocess.run(["git", *arguments], capture_output=True, text=True, cwd=ROOT_DIR)
        return process.stdout.splitlines() if process.returncode == 0 else None

    base = git("merge-base", "HEAD", "origin/main")
    committed = git("diff", "--name-only", base[0]) if base else None
    untracked = git("ls-files", "--others", "--exclude-standard")
    if committed is None or untracked is None:
        return None
    return sorted({*committed, *untracked})


# Imports every module of the bootstrap's package, and compiles its driver
# script, which nothing imports: a move that left an import behind fails here
IMPORT_ALL = """
import importlib, pkgutil, py_compile, sys
import quest
failed = []
for module in pkgutil.walk_packages(quest.__path__, "quest."):
    try:
        importlib.import_module(module.name)
    except Exception as error:
        failed.append(f"{module.name}: {type(error).__name__}: {error}")
try:
    py_compile.compile("bootstrap/python/quest_driver.py", doraise=True)
except py_compile.PyCompileError as error:
    failed.append(f"quest_driver.py: {error}")
print("\\n".join(failed) or "OK: every module imported")
sys.exit(1 if failed else 0)
"""


def light(seed: str, cores: int) -> int:
    """Runs the --light checks at once, with cores split between them; 0 if
    they pass."""
    python = sys.executable
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    unit_environment = {"PYTHONPATH": str(ROOT_DIR / "bootstrap" / "python")}
    suites = [
        Suite("light-self-hosting", [python, str(ROOT_DIR / "run_tests.py"), "--self-hosting", "--seed", seed,
                                     "--stage-backend", "arm64", "-k", "questlang/", "-j", str(share(cores, 1, 2))]),
        Suite("light-imports", [python, "-c", IMPORT_ALL], unit_environment),
        Suite("light-unit", [python, "-m", "unittest", "discover", "-s", "tests/python"],
              {**unit_environment, "QUEST_SKIP_PTY_TESTS": "1"}),
    ]
    start = time.monotonic()
    print(f"Running {', '.join(suite.name for suite in suites)} {together_word()} (not enough for a push); output in "
          f"{OUTPUT_DIR.relative_to(ROOT_DIR)}/", flush=True)
    run_at_once(suites, start)
    return 1 if report(suites, start) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--self-hosted-only", action="store_true",
                       help="the self-hosted compiler's suites alone, whatever the change")
    which.add_argument("--all", action="store_true", help="every suite, whatever the change")
    stress = parser.add_mutually_exclusive_group()
    stress.add_argument("--stress", action="store_true", help="the stress tier alone (minutes)")
    stress.add_argument("--no-stress", action="store_true", help="the suites without the stress tier before them")
    which.add_argument("--light", action="store_true",
                       help="the checks a move of modules needs (docs/testing.md section 4.1), not a push's")
    parser.add_argument("--seed", choices=("release", "bootstrap"), default="release",
                        help="what builds the self-hosting check's stage 1 (default: the current release; the "
                        "bootstrap past a gap, docs/instructions.md section 6.1)")
    parser.add_argument("--serial", action="store_true",
                        help="run the suites one after another, each with all the cores (or --jobs), not at once")
    parser.add_argument("--jobs", type=int, metavar="N",
                        help="the cores to split between the suites, rather than the machine's; also each build's "
                        "modules at once (QUEST_JOBS)")
    parser.add_argument("--no-exclusive", action="store_true",
                        help="run at once, without the machine-wide lock")
    args = parser.parse_args()
    if args.no_exclusive:
        return checks(args, parser)
    with exclusive.exclusive("tools/check " + " ".join(sys.argv[1:]), quiet=False):
        return checks(args, parser)


def checks(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Runs the checks args asks for; 0 if they pass."""
    if args.jobs is not None and args.jobs < 1:
        parser.error("--jobs must be at least 1")
    cores = args.jobs or os.cpu_count() or 4
    global SERIAL
    SERIAL = args.serial
    if args.jobs is not None:
        # Before the suites are made, which copy the environment: their
        # builds of the self-hosted driver compile N modules at once, as ./quest
        # does with it
        os.environ["QUEST_JOBS"] = str(args.jobs)

    if args.light:
        return light(args.seed, cores)
    every_wasm_mode = True
    if args.self_hosted_only or args.all:
        self_hosted_only = args.self_hosted_only
    else:
        changed = changed_files()
        every_wasm_mode = changed is None or any(wasm_file(f) for f in changed)
        others = None if changed is None else [f for f in changed if not self_hosted_only_file(f)]
        self_hosted_only = others == []
        if changed is None:
            print("Running every suite: git cannot say what the change is")
        elif others:
            print(f"Running every suite: the change touches {others[0]}"
                  + (f" and {len(others) - 1} more files" if len(others) > 1 else "")
                  + " outside the self-hosted compiler")
        else:
            print(f"Running the self-hosted compiler's suites alone: the change's {len(changed)} files are all its "
                  "own (--all runs every suite)")

    python = sys.executable
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_tests = [python, str(ROOT_DIR / "run_tests.py"), *(f"--skip-phase={phase}" for phase in SKIPPED_PHASES)]
    self_hosting = [*run_tests, "--self-hosting", "--seed", args.seed, "--whole-program-fixed-point"]
    # The suite runs with stage 2 as arm64 compiles it, as releases are; C's
    # fixed point is checked too, and with it the bootstrap's comparison
    fixed_points = [Suite(f"self-hosting-{backend}", [*self_hosting, "--stage-backend", backend, "--fixed-point-only"])
                    for backend in ("c",)]
    self_hosting = [*self_hosting, "--stage-backend", "arm64"]
    # The JIT's modes run by hand: the stress tier runs jit-files, and the
    # self-hosted suite's jit_hosts check runs the REPL's transcripts (jit's
    # tests) through --jit in an arm64-built driver. So does c-whole: the
    # self-hosted suite runs the C backend, and arm64-whole whole programs.
    # wasm (wasmtime) and wasm-jit when the change touches the wasm backend's
    # own code (WASM_PATHS), or with --all or --self-hosted-only
    wasm_modes = "wasm,wasm-node,wasm-jit" if every_wasm_mode else "wasm-node"
    if not every_wasm_mode:
        print("The wasm modes: wasm-node alone, the change touching none of the wasm backend's own files")
    backends = [*run_tests, "--self-hosted", "--seed", args.seed, "--backend",
                "ssac,arm64,arm64-program,arm64-whole," + wasm_modes]
    unit = [python, "-m", "unittest"]
    unit_environment = {"PYTHONPATH": str(ROOT_DIR / "bootstrap" / "python")}
    # Every compiled program the suites run, the compilers among them, checks
    # its objects' layouts and its units' root tables (docs/collector.md
    # section 7)
    os.environ["QUEST_GC_CHECK"] = CHECKS

    if not args.no_stress:
        if not stress_tier(python, cores, self_hosted_only):
            print("The stress tier failed: the suites were not run")
            return 1
        if args.stress:
            return 0

    if self_hosted_only:
        together = [
            Suite("self-hosting", [*self_hosting, "-j", str(min(8, cores))]),
            Suite("backends", [*backends, "-j", str(share(cores, 1, 4))], INCREMENTAL_PROGRAMS_ENVIRONMENT),
            *fixed_points,
        ]
        after: list[Suite] = []
    else:
        # The self-hosted suite takes longest, and sets when the run ends: it
        # gets most of the cores (docs/testing.md section 5.1)
        together = [
            Suite("self-hosting", [*self_hosting, "-j", str(share(cores, 5, 10))]),
            Suite("backends", [*backends, "-j", str(share(cores, 2, 10))], INCREMENTAL_PROGRAMS_ENVIRONMENT),
            *fixed_points,
            Suite("bootstrap", [*run_tests, "-j", str(share(cores, 3, 10))]),
            Suite("unit", [*unit, "discover", "-s", "tests/python"], {**unit_environment, "QUEST_SKIP_PTY_TESTS": "1"}),
        ]
        after = [Suite("pty", [*unit, PTY_TESTS], unit_environment)]

    start = time.monotonic()
    print(f"Running {', '.join(suite.name for suite in together)} {together_word()}"
          + (f", then {', '.join(suite.name for suite in after)}" if after else "")
          + f"; output in {OUTPUT_DIR.relative_to(ROOT_DIR)}/", flush=True)
    run_at_once(together, start)
    for suite in after:
        suite.run(start)

    return 0 if outcome([*together, *after], start) else 1


if __name__ == "__main__":
    sys.exit(main())
