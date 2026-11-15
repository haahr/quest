# bootstrap/python/quest/testing: the end-to-end test runner

This package is the test runner behind `run_tests.py` at the top of the repository. It runs Quest programs through a
compiler driver, one phase at a time, and compares what the driver prints with expected output. It tests both
compilers: by default the bootstrap's driver (`quest_driver.py`), and with `--self-hosted` the self-hosted compiler's
driver, which it first builds. Unlike the rest of `bootstrap/python/quest`, it is not part of a compiler; it lives
here because it is Python and shares the bootstrap's helpers (its byte encoding, its module resolver for finding a
test's imports). The Python unit tests in `tests/python/` are separate and run under `unittest`.

## Phases and goldens

A compiler's work is divided into *phases*, and the driver can stop after any of them and print its result
(`--stop-after PHASE`): the tokens, the syntax tree, the typed program, the IR at each stage, the SSA, or the output
of running the program, interpreted (`interpret`), with its IR interpreted after a stage (`run_ir_<stage>`), or
compiled to a binary (`run_c_compiled`). A **golden test** is a program in `tests/source/` (or `examples/`) whose
output at a phase must equal a stored file, its golden, in `tests/golden/<phase>/`. All the run phases share one
golden, `tests/golden/run/`, since every way of running a program must print the same thing; that one comparison is
what holds the interpreters, every IR pass, and every backend to the same meaning.

[`runner.py`](runner.py) discovers the test programs, picks the phases that apply to the compiler under test, runs
each (program, phase) pair as a separate driver process so that no test sees another's compilation state, and
reports each result. Pairs run in parallel on a pool of workers, each with a build directory of its own.
`--update-golden` writes new goldens, but only those a compiler owns: the shared goldens of what programs do are
written by the bootstrap alone, and the IR and SSA dumps, which describe how the self-hosted compiler compiles, by
that compiler alone ([docs/testing.md](../../../../docs/testing.md) §2.8). Tests the self-hosted compiler, or one of
its backend modes, is not yet expected to pass are listed in `tests/self-hosted/pending*.txt`.

A test program steers its own run with **directives**, comments that [`directives.py`](directives.py) parses: phases
to skip (`(* @skip-phase: interpret *)`), the program's arguments, environment, standard input, expected exit
status, and timeout.

## Error tests

The tests in `tests/errors/<phase>/` are programs that must fail. Rather than compare the exact text of the error
messages, which would make every wording change touch many files, a test states its expectations inline, as a
comment on the line the error belongs to: `(* ERROR: regexp *)`. [`errors.py`](errors.py) runs the phases before the
test's and requires them to succeed, so a test cannot pass on an error it was not written for; then it runs the
test's phase, parses the diagnostics from standard error, and requires a one-to-one match between diagnostics and
expectations, by severity, file, and line.

## Testing the self-hosted compiler

[`selfhost.py`](selfhost.py) builds the self-hosted driver, with the bootstrap or with the current release
([`releases.py`](releases.py) finds the releases every worktree shares), and checks the **fixed point** of
self-compilation: stage 1, the seed's build of the compiler, builds stage 2, and stage 2 must write the same
artifacts for every unit that stage 1 wrote. When the release is the seed, the bootstrap's build runs alongside and
must agree too, which keeps the bootstrap able to build the compiler. The runner then tests stage 2.

`--backend` runs the compiled-program tests through each of the self-hosted compiler's backend modes: the SSA's C
printer (`ssac`), arm64, combinations of the two with the C printer per unit, whole-program builds, and the JIT.
[`transcripts.py`](transcripts.py) runs the tests that are transcripts rather than phase outputs: the REPL's
(`tests/repl/`, each file fed to `quest -i`), the `-e` programs of `tests/eval/cases.quest`, and the unit checks,
scripts that test the self-hosted driver's artifacts, builds, and Jupyter kernel. [`layout.py`](layout.py) records
where the tests, goldens, and drivers are.

## Further reading

- [docs/testing.md](../../../../docs/testing.md): the suites (§1), the runner's phases and options (§2.3),
  directives (§2.4, §2.5), REPL transcripts (§2.7), shared and own goldens (§2.8), error tests (§3), and
  `tools/check`, which picks the suites a change needs (§4.1).
- [docs/release-compiler.md](../../../../docs/release-compiler.md): releases, which seed the self-hosting check.
- [docs/build-process.md](../../../../docs/build-process.md) §2.1: why each test is a compilation session of its own.
