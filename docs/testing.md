# Quest Compiler Testing Framework

This document describes the testing architecture for the two Quest compilers, the bootstrap and the self-hosted one,
including unit tests, golden-file end-to-end tests for valid programs, and diagnostic inline-comment tests for invalid
programs.

---

## 1. Overview of Test Suites

The compiler test suite is organized into three complementary testing tiers. Before a push, `tools/check` runs the
suites a change needs, at once (section 4.1).

1. **Python Unit Tests (`tests/python/`):**
   - Fine-grained unit tests written in Python using `unittest`.
   - Verifies individual compiler modules, functions, algorithms, and data structures:
     - `test_types_and_env.py`: Scopes, symbol tables, kind well-formedness, subkinding.
     - `test_diagnostics.py`: Structured diagnostics, `DiagnosticSink`, severities, formatters.
     - `test_typed_ast.py`: Typed AST node constructors, S-expression serialization.
     - `test_phase3_functions.py`, `test_phase5_exceptions_dynamic.py`, `test_phase6_modules_interfaces.py`: Typing that
       source text cannot express, and module and interface scopes.
   - What a program's source can show, such as the type an expression synthesizes or that a program is rejected, is a
     golden or error test instead (sections 2 and 3).
   - Run via:
     ```bash
     PYTHONPATH=bootstrap/python python3 -m unittest discover -s tests/python
     ```

2. **Golden-File Compiler Tests (`tests/source/` and `tests/golden/`):**
   - End-to-end tests for valid Quest programs.
   - Executes the unified compiler driver (`quest_driver.py --stop-after <phase>`) against
     canonical `.quest` source files.
   - Validates stdout against exact expected outputs in `tests/golden/<phase>/<name>.out`.
   - Both the `interpret` phase and the `run_c_compiled` phase compare their stdout against
     the unified `tests/golden/run/` directory.

3. **Diagnostic & Error Tests (`tests/errors/`):**
   - Negative tests for invalid programs containing deliberate syntax, lexical, or type errors.
   - Avoids fragile exact-match terminal formatting goldens by embedding inline expectation directives in comments
     within the source file.
   - Enforces precursor phase validity and strict bidirectional 1:1 matching between expected and actual diagnostics.

---

## 2. Golden-File Testing Framework

### 2.1. Directory Structure

```
tests/
  ├── source/
  │   ├── 01_lexer_basics.quest ... 07_exceptions_dynamic.quest
  │   ├── stdlib/
  │   │   ├── ascii_int_real.quest
  │   │   ├── conv_formatting.quest
  │   │   ├── list_operations.quest
  │   │   ├── arrayop_operations.quest
  │   │   ├── dynamic_operations.quest
  │   │   └── modules_first_class.quest
  │   ├── language/
  │   │   ├── functions_recursion.quest
  │   │   ├── arrays_operations.quest
  │   │   ├── tuples_records.quest
  │   │   ├── closures_captures.quest
  │   │   ├── options_variants.quest
  │   │   ├── variants_cardelli.quest
  │   │   ├── subtyping_coercions.quest
  │   │   ├── exceptions_try_when.quest
  │   │   ├── existential_packages.quest
  │   │   ├── auto_types.quest
  │   │   ├── auto_type_parameters.quest
  │   │   ├── record_views.quest
  │   │   ├── nested_record_views.quest
  │   │   ├── function_subtyping.quest
  │   │   ├── runtime_type_descriptors.quest
  │   │   ├── cardelli_syntax.quest
  │   │   ├── cardelli_options.quest
  │   │   └── cardelli_operators.quest
  │   ├── modules/
  │   │   ├── counter.int.quest, counter.mod.quest, ... (imported by the tests, not tests themselves)
  │   │   ├── import_from_test_directory.quest
  │   │   └── ...
  │   └── specialization/
  │       ├── quantifier_descriptors.quest
  │       ├── aggregate_subtyping.quest
  │       ├── bounded_quantifiers.quest
  │       ├── callsite_specialization.quest
  │       └── flat_stride_arrays.quest
  └── golden/
      ├── tokenize/ (mirrors tests/source hierarchy)
      ├── parse/    (mirrors tests/source hierarchy)
      ├── typecheck/(mirrors tests/source hierarchy)
      └── run/      (mirrors tests/source hierarchy for interpret and run_c_compiled)
```

Test sources are discovered recursively (`*.quest`, except interfaces and modules; see §2.6), preserving their relative
directory paths in `tests/golden/`.

The example programs in `examples/`, which documentation walks through (`examples/argmax/` for
[walkthrough.md](walkthrough.md)), are golden tests too, discovered the same way. Their goldens are under `examples/`
in each phase's directory (`tests/golden/typecheck/examples/argmax/argmax.out`), and each example has goldens for
every IR stage, not a subset, so a change to any phase's output for an example is noticed. `-k examples/` selects
them.
`tests/python/test_walkthrough.py` checks that the excerpts walkthrough.md shows, each marked with the file and phase
it comes from, are what the compiler prints; a change that makes an excerpt stale fails it, and the document is
updated with the goldens.

### 2.2. Standard Output and Execution Discipline
- **Valid Programs:** Must complete successfully with exit code 0. Standard output is captured and verified against
  the corresponding `<test>.out` file.
- **Unified Run Directory (`tests/golden/run`):** Both tree-walking interpretation (`interpret`) and native binary
  execution (`run_c_compiled`) produce identical Cardelli interactive outputs and compare against `tests/golden/run/`.
- **`--print-result` Flag:** When invoking `quest_driver.py --stop-after run_c_compiled`, `--print-result` is enabled
  automatically so that the compiled binary outputs the final phrase result. For standalone compilation
  (`quest compile`), binaries are silent by default unless `--print-result` is explicitly passed.
- **Working Directory:** Every run of the driver, in every phase and for error tests too, starts in a fresh, empty
  temporary directory of its own, which the runner deletes afterwards. A program may create, read, and remove files
  there with relative paths, and it cannot see or leave files in the repository; a test that inspects files creates
  them first (`stdlib/system_fs_operations`). The runner passes the test's path as an absolute path, and the build
  directory is shared by all runs as before.
- **Output Streams:**
  - `stdout`: Used exclusively for valid phase artifacts (e.g. token tables, AST S-expressions, typed AST dumps,
    run output).
  - `stderr`: Reserved exclusively for diagnostic error messages and warnings.

### 2.3. Test Runner (`run_tests.py`)
The test runner executes each test source file across active compiler phases via `quest_driver.py`:
- `tokenize`: Runs `quest_driver.py --stop-after tokenize <source_file>`.
- `parse`: Runs `quest_driver.py --stop-after parse <source_file>`.
- `typecheck`: Runs `quest_driver.py --stop-after typecheck <source_file>`.
- `ir_core`: Runs `quest_driver.py --stop-after ir_core <source_file>`, which lowers the typed program to Core IR
  ([ir.md](ir.md)) and prints it (compared against `tests/golden/ir_core/`). Generated tests skip it.
- `ir_specialized` (and each later IR stage, `ir_<stage>`): the IR after that stage's pass, compared against
  `tests/golden/ir_<stage>/` for a subset of the programs only, those with a golden there, chosen to exercise the
  pass (every program runs through every stage, verified, in the `run_ir_<stage>` phases). To add a program to a
  stage's subset, create its golden file empty and update goldens (`--phase ir_<stage> --update-golden`).
- `run_ir_core`: Runs `quest_driver.py --stop-after run_ir_core <source_file>`, which runs the Core IR in the IR
  interpreter (`quest/interpreter/ir_interp.py`), compared against `tests/golden/run/`. Each later IR stage gets a phase of its
  own (`run_ir_<stage>`), so that a pass that changes a program's output fails in its stage's phase. The run error
  tests are not run through them.
- `interpret`: Runs `quest_driver.py --stop-after interpret <source_file>` (compared against `tests/golden/run/`).
- `run_c_compiled`: Runs `quest_driver.py --stop-after run_c_compiled <source_file>`, which compiles the program
  through the IR to C (`quest/codegen/c/printer.py`, [ir.md](ir.md)), links it with the modules it imports (compiled
  on their own, through the IR too), and runs it (compared against `tests/golden/run/`, and the run error tests
  against their goldens).

**Commands:**
```bash
# Run all golden tests across all phases (tokenize, parse, typecheck, interpret, run_c_compiled)
python3 run_tests.py

# Run only a specific phase
python3 run_tests.py --phase run_c_compiled
python3 run_tests.py --phase interpret

# Run only matching tests
python3 run_tests.py -k 03_functions

# Update golden files after an intentional change
python3 run_tests.py --update-golden
```

If stdout does not match the golden file, `run_tests.py` prints a unified diff detailing the exact mismatch.

`--update-golden` records a test's output only when the test exits as expected (with 0, or the code given by
`@exit`); a test that fails is reported as `[FAIL]` and no golden is written, since a golden test is a valid program.
Programs that must be rejected belong in the error suite (§3).

**Hermetic builds:** every phase builds into a fresh temporary build directory for each run (shared by the tests of
that run and deleted afterwards), so results never depend on artifacts left by earlier runs or compiler versions.
Pass `--build-dir <dir>` to reuse a build directory across runs for speed: safe only while the compiler is
unchanged, since artifacts are judged stale by their sources and ABI version, not by the compiler that wrote them.
Unit tests that invoke the driver give it a build directory inside their own temporary directory, so no test writes
into the repository.

**One session per test:** each test is a driver run of its own, and so a compilation session of its own, with its own
unit graph and resolver (`docs/build-process.md` §2.1). Tests share only the artifacts in their worker's build
directory, which the staleness rules decide whether to reuse; no test sees another's resolutions or typed units. The
questlang tests (`tests/source/questlang/`) share one build directory instead, `questlang-tests/` in the run's: while
the other phases run, the runner compiles and links each of them there in turn (`build_questlang_tests`), so the
self-hosted compiler's modules are compiled once per run rather than once per worker, and the tests then run in
parallel against those fresh artifacts, each writing only its own program's. The
runner itself classifies files (§2.6) and follows error tests' imports (§3.3) through the same graph: `file_unit_kind`
and a `Resolver` of each error test's own.

**ABI corpus:** `tests/python/test_abi_corpus.py` fails when the generated interface artifacts (`.qi` files and C
headers for a frozen snapshot of the library's interfaces) change without a bump of `ABI_VERSION`
(`docs/build-process.md` §5.2.3). After an intended contract change, bump the version and run
`python tests/abi/corpus.py --update`; to snapshot newer library interfaces, run `python tests/abi/corpus.py
--refresh-inputs`.

**Self-hosted compiler:** `python3 run_tests.py --self-hosted` compiles the self-hosted compiler's driver
(`questlang/driver/main.quest`) to C with the bootstrap, then runs it, instead of the bootstrap's driver, on every test
of the phases it has (tokenize, parse, typecheck, the IR's dumps and runs at every stage, `ir_STAGE` and
`run_ir_STAGE`, interpret, and `run_c_compiled`), against the shared goldens and error expectations, which the bootstrap writes, and against its own (§2.8). The driver
takes the bootstrap driver's `--stop-after PHASE FILE` and prints
the phase's dump in the bootstrap's format (it also has `desugar`, which has no goldens). It reports errors after the
bootstrap's one: an error test passes when the driver's first diagnostic is the expected one and, if it reports more,
when its whole output is `tests/golden/self-hosted/errors/PHASE/TEST.error`, which `--self-hosted --update-golden`
writes for review. `tests/self-hosted/pending.txt` lists the tests the driver is not yet expected to pass
(`PHASE:TEST`, or `errors/PHASE:TEST`): they are reported as pending, and one that passes fails, so that it is taken
off the list. The tests of several errors, which only the self-hosted driver reports, are in
`tests/self-hosted/errors/PHASE`: each diagnostic the driver reports must be one of the test's inline expectations,
and each expectation must be reported. The error tests check one file at a time; `self-hosted/build_errors`
(`tests/self-hosted/build_errors.py`) checks the errors of builds. Each directory under
`tests/self-hosted/build-errors` is a program whose `-o` build fails in a unit it imports, and the driver must report
what the bootstrap does: the error in the unit's file, with its line. `self-hosted/parallel_build`
(`tests/self-hosted/parallel_build.py`) builds those programs and the ones under `tests/self-hosted/parallel-build`
with `-j 1` and `-j 4`: a parallel build must leave a serial one's artifacts, log, and program output, or report its
error ([build-process.md](build-process.md) §7.4). `self-hosted/compile_command` (`tests/self-hosted/compile_command.py`)
runs `compile` command lines (`--emit-c`, `--nogc`, `-c`, `-e`, and the rest), and options the drivers share, with both
drivers: each must exit with the bootstrap's status and errors, leave its files, and print what it prints, apart from
the C.

The runners set `QUEST_HOME` to the project directory, where the self-hosted driver, which runs in a scratch
directory, finds `lib/`. `--self-hosted-driver PATH` runs a driver already compiled (as by `./quest -o build/questlang/main
questlang/driver/main.quest`, or `./questc`'s stage 2 in `.build/questc/stage2/questc`) rather than compiling one,
which takes minutes.

`run_c_compiled` compiles and runs every run program and run-time error test with the self-hosted driver, and runs the
checks of its unit files, builds, and ABI corpus (`self-hosted/abi_corpus`, `self-hosted/unit_artifacts`,
`self-hosted/build_errors`, `self-hosted/parallel_build`, `self-hosted/compile_command`). The generated C has no goldens: `tools/c-diff` shows how a
change alters it (§2.9). `run_c_compiled` builds into a directory of its own under each worker's (`self-hosted-units`), so that they don't reuse the bootstrap's fresh
artifacts. The self-hosted driver builds the questlang tests once, one after another, into a shared directory
(`self-hosted-questlang-tests`).

**Self-hosting:** `python3 run_tests.py --self-hosting` checks the self-hosted compiler's fixed point, then runs the
self-hosted suite with stage 2. Stage 1 is the seed's
build of the driver: the bootstrap's by default. Stage 2 is stage 1's build of it, and stage 3 is stage 2's. The check
requires:
- **The fixed point:** every artifact stage 2 writes for the driver's units (`.mod.c`, `.main.c`, `.int.h`, `.qi`, and
  `.qm`) must be the one stage 1 wrote, up to the producer and the build directory's path. Stages 2 and 3 should be
  the same binary, and the check says so if they are not.
- **Bootstrappability,** with `--seed release`: the bootstrap's build of the driver, which runs alongside the release's
  stage 1, builds a stage 2 of its own, whose artifacts must be the release's stage 1's. The two stage 1s are the same
  compiler built by different compilers, so they must compile the same way. This is what keeps the bootstrap able to
  rebuild the compiler from nothing once the two compilers' outputs differ (§2.8). `tools/release` runs the check
  this way.

Each stage builds with `-j` set to the number of CPUs. The bootstrap's artifacts are not compared with the
self-hosted compiler's, which are its own (§2.8). The check runs before every push, as part of `tools/check` (§4.1).

**Seeds:** `--seed release` makes the current release (`release/current`, [release-compiler.md](release-compiler.md))
build the driver, rather than the bootstrap.
- `--self-hosted` then builds it in two stages, the release's against its own `lib/` and `runtime/` and that build's
  against the tree's, and tests the second.
- `--self-hosting` then starts from the release, and also checks bootstrappability.

The default stays the bootstrap for `--self-hosted`. Its single build of the driver is all that suite needs, and it
keeps the bootstrap able to build the tree's compiler between releases.

The driver's `-e`, which no golden uses, is tested against the bootstrap's: `tests/eval/cases.quest` holds programs,
one per line, and `python tests/eval/generate.py` writes the bootstrap driver's transcript of them
(`tests/golden/self-hosted/eval.out`, each program's output, errors, and exit status), which the self-hosted suite
compares the driver's with (`interpret:self-hosted/eval`).

**Which runs:** a change to the self-hosted compiler alone runs the self-hosting check, and any other change the
bootstrap's suites too (`run_tests.py` and the unit tests); `tools/check` runs them (§4.1).

**The questlang tests run compiled only:** the bootstrap's suites skip them in `interpret` and the `run_ir_*` phases,
as if every one said so with `@skip-phase` (§2.4), since each would interpret the self-hosted compiler's code for half
a minute or more per phase. The self-hosted suite, whose driver is compiled, still interprets them.

**Self-hosted parser:** `tests/parser/generate.py` writes a test for each input in `tests/parser`, whose cases are
separated by lines that are just `(* ---- *)`: `tests/source/questlang/parser_NAME.quest` parses each case with the
self-hosted parser (`questlang/syntax/parser`) and prints its AST with `astprint.dumpWithOffsets`, or its syntax
error, and its golden holds what the bootstrap's parser and `ast_dump` (with every node's offset) give. `forms.quest` uses every rule of the grammar;
`errors.quest` holds syntax errors, whose messages and positions must be the bootstrap's. Regenerate them with
`python tests/parser/generate.py` after changing an input. `syntax_parser.quest` tests what only the self-hosted
parser has (its entry points, its nodes' extents, imports below the top level, and the phrases its AST holds only
at the top level), and
`syntax_parser_engine.quest` tests the engine with a small grammar.

**Self-hosted type system:** `tests/types/generate.py` builds types and kinds with the bootstrap's model and applies
operations to them, and writes tests that do the same with the self-hosted modules (`questlang/types/*`), whose
goldens hold what the bootstrap gives: `types_model` the model's operations (printing, hash-consing, free variables,
substitution, evaluation and unfolding, metavariables, queries), and `types_judgments` the judgments (subtyping,
subkinding, kind synthesis and its errors, contractiveness, bounds, the environment's builtins). Regenerate them
with `python tests/types/generate.py` after changing a case.

**Self-hosted type elaboration:** `tests/elaborate/generate.py` writes a test for each input in `tests/elaborate`,
whose cases, separated as the parser's are, are programs of type and kind declarations:
`tests/source/questlang/elaborate_NAME.quest` elaborates each case's declarations in order, in a new environment,
with `questlang/typechecker/elaboratetypes`, printing the symbols they declare or the first error, and its golden
holds what the bootstrap's `elaborate_types` gives. Regenerate them with `python tests/elaborate/generate.py`.

**Conversion matrix:** `tests/conversions/generate.py` writes the programs in `tests/source/conversions`, one per place
compiled code converts values between representations (polymorphic calls, first-class polymorphic values, type
applications, closures, shapes as type arguments, dynamic values, subsumption, stores, identity), each exercising
every shape over a type parameter (tuples, options, records, variants, arrays, closures, recursive types) at scalar,
record, variant, and tuple type arguments ([ir.md](ir.md) §8.4). Goldens come from the interpreter. Cells
listed in the generator's `KNOWN_FAILURES` go into `*_known_failures.quest`, which skips the compiled phase, each
with its reason; cells in `REJECTED` are compile-time errors of C generation, checked by
`tests/python/test_conversion_rejections.py`. After changing the generator, run `python tests/conversions/generate.py`
and then `python run_tests.py -k conversions/ --update-golden`.

**Performance baseline:** `python tests/perf/measure.py` measures the time spent in the C emitter and the size of the
C it produces over the compiled test programs, and the run times of the benchmarks in `tests/perf`, comparing them
with `tests/perf/baseline.json` (`--save` rewrites it). It is not part of the test suite.

**Scope checks:** with `QUEST_CHECK_SCOPES=1`, which `run_tests.py`, the error tests, and the unit tests' helpers set,
the type checker checks that every typed program is well scoped (`quest/typechecker/scoping.py`): variables are used
within their binders' scopes, and functions' type parameters within their functions. A failure is an internal
error. Production builds skip the check.

**IR checks:** with `QUEST_CHECK_IR=1`, set in the same places, the compiler verifies the IR after lowering
(`quest/ir/verify.py`): every variable is used within its binder's scope and bound once, closures capture no mutable
local, jumps and breaks name enclosing join points and loops, and terminators end their bodies. A failure is an
internal error.

### 2.4. Phase Skipping Directives (`(* @skip-phase: ... *)`)
For language features that are fully supported in the tree-walking Python interpreter but not yet implemented in the
C compilation backend (or for tests specific to certain phases), tests can include in-file phase skipping directives:

```quest
(* @skip-phase: run_c_compiled *)
```

- **Multiple Phases**: Even though `@skip-phase:` is singular, multiple phases can be omitted using comma- or
  whitespace-separated names (e.g. `(* @skip-phase: run_c_compiled, interpret *)`) or multiple comment directives.
- **Reporting**: Skipped phases are explicitly noted during test execution (`[SKIP] phase:test_name`) and counted in
  the test summary without being counted as failures.
- **Golden Management**: When updating goldens with `--update-golden`, skipped phases are ignored and will not
  generate unexpected `.out` files.

### 2.5. Host-Environment Directives (`@args`, `@env`, `@exit`, `@stdin`, `@echo`)
Tests that interact with host OS primitives (command-line arguments, environment variables, exit codes, and standard
input) can specify host execution requirements via top-level comment directives:

- **Command-Line Arguments (`(* @args: ... *)`)**:
  Specifies arguments passed to the program when executing `interpret` or `run_c_compiled`:
  ```quest
  (* @args: hello "world with spaces" *)
  ```
  Arguments are tokenized with standard shell quoting rules and passed after the `--` separator to `quest_driver.py`.
  Available in Quest via `system.args`.

- **Environment Variables (`(* @env: ... *)`)**:
  Sets environment variables for the test process:
  ```quest
  (* @env: QUEST_TEST_ENV_VAR=quest_success_value DEBUG=1 *)
  ```
  Available in Quest via `system.getEnv(...)`.

- **Expected Process Exit Code (`(* @exit: ... *)`)**:
  Specifies the non-zero exit code expected from program execution:
  ```quest
  (* @exit: 42 *)
  ```
  Applies exclusively to execution phases (`interpret` and `run_c_compiled`); earlier phases (`tokenize`, `parse`,
  `typecheck`) must still exit with `0`. The test runner validates that the process exits with the specified code,
  while verifying standard output against `<test>.out`.

- **Process Timeout (`(* @timeout: ... *)`)**:
  Overrides the default per-test timeout (default: 30.0 seconds) for tests that compile large modular suites:
  ```quest
  (* @timeout: 60.0 *)
  ```
  The test runner applies this timeout to each phase invoked for the test.

- **Standard Input (`(* @stdin: ... *)`)**:
  Supplies standard input data to the running program using a multi-line comment block:
  ```quest
  (* @stdin:
  First input line
  Second input line
  *)
  ```
  Available in Quest via `reader.input`.

- **Echoed Results (`(* @echo *)`)**:
  Runs the program with `--echo` in `interpret` and `run_c_compiled`, so that every top-level phrase prints its result
  as the interactive REPL does (`let x:Int = 5`, `3 : Int`, `exception E`, `Let T::TYPE = Int`), not only the last.
  A test can then check many values without printing each with `writer` and `conv`. Compiled code echoes exactly as
  the interpreter does, because both format a value by its static type all the way down: a record shows the fields
  of its type (sorted by name), a function is `<fun>`, a value of an abstract type (such as `list.T(Int)` or a
  module's `T`) is `<hidden>`, and an auto value names its type component as its runtime descriptor does. Compiled
  code writes compound values from their type descriptors (`quest_print_typed`), including tuples' type components
  (`Let A = Int`).

### 2.6. Interfaces and Modules Used by Tests
A test can import interfaces and modules defined in `.int.quest` and `.mod.quest` files beside it, found by the
ordinary sibling search (`docs/modules.md` §2.2). These files are not tests: the runner does not discover them, so no
phase (not even `tokenize` or `parse`) is run on them by themselves and they have no goldens. They are compiled only as
imports of the tests that use them, in every phase that a test reaches, and may be shared by several tests in their
directory. The same holds for error tests in `tests/errors/`.

```quest
(* tests/source/modules/import_from_test_directory.quest, beside counter.int.quest and counter.mod.quest *)
import counter: Counter
counter.get(counter.inc(counter.new(10)))
```

Units may also be in subdirectories of a test's directory, imported by their paths (`import arith = util/arith :
util/Arith;` in `tests/source/modules/subdirectory_units.quest`). A unit's canonical name is its path relative to the
project directory (`tests/source/modules/counter`; `docs/modules.md` §2.3), so units in different test directories may
share names, and may share names with library units, without their artifacts colliding in the shared build directory.
One test may also use different units with the same base name (`counter` and `util/counter` in
`tests/source/modules/same_name_units.quest`).

### 2.7. REPL Transcripts (`tests/repl/`)
The REPL ([repl.md](repl.md)) is tested by transcripts, in the `repl` phase. Each `tests/repl/NAME.quest` is the
standard input of `quest -i`, run in a scratch directory of its own, and `tests/golden/repl/NAME.out` is what the
driver writes: its standard output, its standard error, and its exit status. Standard input is not a terminal, so the
REPL writes its prompts without editing and the input lines are not echoed: a line's prompt is followed directly by
the response to it, if any. Paths under the checkout are written relative to it (or `<root>` for the checkout itself),
and the scratch directory as `<scratch>`.

- `(* @load: PATH *)` names a file, relative to `tests/repl` (they are in `tests/repl/files/`), for `-i` to run before
  reading input. Only the `.quest` files directly in `tests/repl` are transcripts.
- `@args` are the program's arguments, after the loaded file or after a `--`; `@env` and `@timeout` are as for golden
  tests (section 2.5).
- A transcript that needs interfaces and modules writes them itself (with `writer`), since the REPL resolves imports
  from its directory, the scratch directory.

Comment lines are inputs too, so a transcript's opening comment shows as a prompt (and a continuation prompt per extra
line). Line editing, history, and Ctrl-C need a terminal, and are not tested here.

The self-hosted suite runs the same transcripts against the compiled self-hosted driver, comparing its output with the
bootstrap's goldens, so the two REPLs must agree exactly.

**At a terminal:** `tests/python/test_readline_terminal.py` runs programs that use `io/readline` (compiled with GNU
readline and with libedit, and interpreted) and the REPL in a pseudo-terminal: the REPL starts without `-i`, recalls
a line from the history file, edits it, abandons a continued phrase on Ctrl-C, ends on Ctrl-D, and writes the
history back. It runs the bootstrap's driver, and the self-hosted one too when `QUEST_SELF_HOSTED_DRIVER` names one
already compiled (as `run_tests.py --self-hosted --build-dir DIR` leaves in `DIR/questlang-driver`), since compiling
it there would take minutes.

---

### 2.8. Two Compilers: Shared and Own Goldens

The self-hosted compiler is the primary one; the bootstrap is kept so that the compiler can be rebuilt from nothing.
The two must agree on what programs do, but not on how they compile them, so that optimizations and other internal
changes go into the self-hosted compiler alone, while language changes and bug fixes go into both.

| Phase | Goldens | Written by |
| :--- | :--- | :--- |
| `tokenize`, `parse`, `typecheck` | shared: `tests/golden/PHASE` | the bootstrap |
| `interpret`, `run_ir_STAGE`, `run_c_compiled` | shared: `tests/golden/run` | the bootstrap |
| `repl`, error tests, `-e` (`self-hosted/eval`) | shared | the bootstrap |
| `ir_STAGE` (the IR's dumps) | the self-hosted compiler's alone: `tests/golden/ir_STAGE` | the self-hosted compiler |
| the ABI corpus | each compiler's own: `tests/abi/corpus` (bootstrap), `tests/abi/corpus-self-hosted` | each compiler |

- **Shared goldens** describe what programs do and what errors they report. Both suites must match them, and only the
  bootstrap's `--update-golden` writes them, since a change to them is a change to the language or a bug fix, which
  lands in both compilers. So **every bug fix adds or changes a test in a shared phase,** most often a run test: if
  only one compiler has the fix, the other's suite fails until it has it too. A bug in what only the self-hosted
  compiler does (an optimization, say) is fixed there alone, but still gets a run test.
- **Own goldens** describe how a compiler compiles: the self-hosted compiler's IR, which `--self-hosted
  --update-golden` writes. The bootstrap's suite skips the IR dumps: when its later phases agree, its IR adds nothing,
  and `--phase ir_STAGE` still runs one, to compare the bootstrap's IR with the self-hosted compiler's goldens when a
  bootstrap test fails. Neither compiler's C has goldens (§2.9).
- **The self-hosting check** keeps the bootstrap honest: its build of the compiler must compile as the release does
  (§2.3, bootstrappability).
- **Artifacts are each compiler's own.** The compilers share `ABI_VERSION`, which changes when either one's artifact
  contract does, and each corpus pins its compiler's. Each compiler uses only the `.qi` and `.qm` files whose
  `producer` is its own (`quest-bootstrap 0.1` or `questlang 0.1`), and rebuilds the other's, or reports them when it
  cannot (`config/abi`).
- **The runtime is shared,** so a change to it must keep the bootstrap's C working: adding a function for the
  self-hosted compiler is fine, but changing what existing C relies on means changing the bootstrap too.

### 2.9. The Generated C (`tools/c-diff`)

The suites check what compiled programs do (`run_c_compiled`), not the C they compile to. Goldens of the C would change
with every change to it, an ABI's or an imported interface's as much as the backend's, and a digest's mismatch would
show nothing of what had changed. Instead, `tools/c-diff` shows the change itself: it prints the C of every program `run_c_compiled` compiles, as a revision's compiler prints it (`--stop-after codegen_c
--print-result`), against the working tree's, as unified diffs.

```sh
tools/c-diff                     # the self-hosted compiler's C at HEAD against the working tree's
tools/c-diff --base origin/main  # against another revision's
tools/c-diff --bootstrap         # the bootstrap's C
tools/c-diff -k option --stat    # the programs whose names contain "option": which differ, by how many lines
tools/c-diff --questlang         # the tests of the self-hosted compiler's modules too (slow)
```

Each side compiles its own copy of the programs against its own `lib/` and `runtime/`, and paths under each tree are
made relative to it. The revision's files are exported into `.build/c-diff/REVISION` and kept with what is built
there, so its self-hosted compiler (about six minutes to build from the bootstrap) is built once. The exit status is 0
when no program's C differs, 1 when some does, and 2 when one does not compile. Use it to confirm that a change meant
to leave the C alone does (a refactoring, a change to the front end), and to review what a backend change does to it.

## 3. Diagnostic & Error Testing Framework (`tests/errors/`)

### 3.1. Design Motivation
Exact-match golden files for error reporting are fragile: cosmetic adjustments to terminal box-drawing characters,
line gutters, column pointers, color ANSI sequences, or minor wording changes in help text break all golden files,
even when compiler diagnostic semantics remain correct.

The diagnostic testing framework tests errors semantically using **inline expectation comments** directly inside the
failing test source files.

### 3.2. Directory Structure and Phase Scoping

Error tests are organized by the specific compiler phase responsible for detecting and reporting the error:

```
tests/errors/
  ├── tokenize/
  │   ├── invalid_character.quest
  │   └── unclosed_string.quest
  ├── parse/
  │   ├── missing_end.quest
  │   └── invalid_infix.quest
  └── typecheck/
      ├── non_contractive_rec.quest
      ├── record_field_mismatch.quest
      └── unhandled_exception.quest
```

### 3.3. Inline Expectation Syntax

Expected diagnostics are declared using standard Quest block comments (`(* ... *)`) placed directly on the line where
the diagnostic is expected:

```
(* <SEVERITY>: <REGEXP> *)
```

- `<SEVERITY>`: One of `ERROR`, `WARNING`, `INFO`, `FATAL` (case-insensitive).
- `<REGEXP>`: A regular expression pattern matched against the diagnostic's primary `message`, `notes`, or `help_text`.

A test may import interfaces and modules beside it (§2.6), and an expectation may be placed in one of those files, on
the line of that file where the diagnostic is expected: an error in an imported interface or module is reported in its
own file (`docs/diagnostics.md` §4.4). The runner collects the expectations of the test and of every unit beside it that
the test imports, directly or through other units (each import resolved from its importer's directory as compiling
it resolves it, keeping the units found there), and matches each only by a diagnostic in its own file. A unit's
expectations apply to every test that imports it, so a unit with an error should be imported by one test.

#### Examples
```quest
(* tests/errors/typecheck/non_contractive_rec.quest *)
Let Rec Bad::TYPE = Bad (* ERROR: not contractive *)

(* tests/errors/typecheck/type_mismatch.quest *)
let x: Int = "hello" (* ERROR: type mismatch.*expected 'Int' *)

(* tests/errors/typecheck/warnings.quest *)
let unused = 42 (* WARNING: unused variable 'unused' *)
```

### 3.4. Precursor Phase Validation
A test in `tests/errors/<phase>/` must contain errors **only in `<phase>`**.

When running a test for `<phase>`:
1. The runner executes all precursor phases in order (e.g. for `typecheck`, it first runs `tokenize` and `parse`).
2. If any precursor phase produces an error, the test fails immediately:
   ```
   [FAIL] typecheck:tests/errors/typecheck/bad_syntax.quest
     Precursor phase 'parse' failed unexpectedly before reaching 'typecheck':
     test.quest:2:5: error: syntax error, expected 'end'
   ```
This enforces independence of concerns and ensures tests do not pass accidentally due to earlier unintended failures.

### 3.5. Bidirectional 1:1 Diagnostic Matching
To prevent silent regressions (such as cascading poison errors or unverified warnings), the runner enforces exact
bidirectional matching:

1. **Every Expected Diagnostic Must Be Found:** Every inline expectation `(* SEVERITY: REGEXP *)` on line $N$ must
   match an actual diagnostic emitted with that severity on line $N$.
2. **Every Actual Diagnostic Must Be Expected:** Every diagnostic emitted by the compiler in the tested phase must
   match one of the declared inline expectations.
3. If any expected diagnostic is missing, or any unexpected diagnostic is emitted, the test fails with a clear diff.

---

## 4. Summary of Test Commands

| Test Suite | Purpose | Execution Command |
| :--- | :--- | :--- |
| **Unit Tests** | Module & algorithm verification | `python3 -m unittest discover -s tests/python` |
| **Golden Tests** | Valid end-to-end outputs | `python3 run_tests.py` |
| **Error Tests** | Semantic diagnostic verification | `python3 run_tests.py --errors` |
| **Update Goldens** | Refresh golden output files | `python3 run_tests.py --update-golden` |
| **REPL** | REPL transcripts (section 2.7) | `python3 run_tests.py --phase repl` |
| **Self-Hosted** | The self-hosted compiler against the bootstrap's goldens | `python3 run_tests.py --self-hosted` |
| **Questlang** | The self-hosted compiler's modules, compiled (each suite runs them too) | `python3 run_tests.py -k questlang/` |
| **Self-Hosting** | The self-hosted compiler's fixed point, then the self-hosted suite with stage 2 | `python3 run_tests.py --self-hosting` |
| **Release** | The self-hosting check, then a new release in `release/current` | `tools/release` |
| **Before a push** | The suites a change needs, at once (section 4.1) | `tools/check` or `tools/check --self-hosted-only` |

### 4.1. Before a Push (`tools/check`)

Which tests a change needs depends on which compilers it changes (section 2.8, and
[instructions.md](instructions.md) §9):

| Change | Command | Runs | Takes (10 cores) |
| :--- | :--- | :--- | ---: |
| **Both compilers,** or what they share: the language, `lib/`, `runtime/`, a fix to what programs do or what errors they report, the tests | `tools/check` | At once: the self-hosting check seeded from the release (60% of the workers), the bootstrap's suite (40%), and the unit tests but the terminal ones; then the terminal tests alone | about 11 min |
| **The self-hosted compiler alone:** `questlang/` changes to how it compiles (its IR, its C), and refactorings | `tools/check --self-hosted-only` | The self-hosting check seeded from the release, with 8 workers | about 11 min |

- **Both take about as long,** since the self-hosted suite sets when either ends (section 5.1); `--self-hosted-only`
  leaves the bootstrap's suite and the unit tests out, which a change to the self-hosted compiler alone cannot
  affect, and frees the cores they would use.
- **The self-hosting check** (`run_tests.py --self-hosting --seed release`) builds stage 1 with the release, and the
  bootstrap's build alongside it, then stages 2 and 3. It checks the fixed point, that the bootstrap still builds what
  the release does, and that stages 2 and 3 are the same binary, and then runs the whole self-hosted suite with
  stage 2. It replaces `--self-hosted`, for 2-3 minutes more. Past a gap (a feature the release does not have yet,
  [instructions.md](instructions.md) §6.1), `tools/check --seed bootstrap` builds stage 1 with the bootstrap.
- **The questlang tests** (`tests/source/questlang/`) need no run of their own: each suite runs them compiled, with its
  own compiler.
- **The suites do not interfere:** each builds into a temporary directory of its own, the runtime's cached objects
  are written atomically, and only `--update-golden` writes goldens. They compete only for cores, which is why the
  self-hosted suite, the longest, gets most of them, and why the terminal tests (`tests/python/test_readline_terminal.py`),
  which time out under load waiting for a pseudo-terminal's output, run alone afterwards. `QUEST_SKIP_PTY_TESTS=1`
  skips them.
- **Output:** each suite's output is kept in `.build/check/SUITE.txt`; `tools/check` prints each suite's summary and
  when it finished, and exits 0 only when every suite passes.
- **A comment- or documentation-only change** needs no suites.

---

## 5. Test Suite Performance

### 5.1. Where the Time Goes
Measured 2026-10-28 on a quiet 10-core machine:

| Suite | Alone, 8 workers | At once with the others |
| :--- | ---: | ---: |
| Self-hosted (`--self-hosted`) | about 500 s | 519 s (6 workers) |
| Bootstrap (`run_tests.py`) | about 345 s | 494 s (3 workers) |
| Unit tests | about 65 s | 69 s |
| Terminal tests, alone afterwards | 3 s | 3 s |

One after another they take about 15 minutes; at once, 522 s. The self-hosted suite takes about as long with 6 workers
as with 8, so it is bound by what it does serially, not by cores: building the driver before any test, the barriers
between phases, and its long unit checks (`self-hosted/build_errors` and the others), each of which builds its cases
one after another. Those are where a shorter run would come from.

Each suite runs a phase's tests in a pool of `-j` workers (by default 8, or the number of CPUs if fewer), each with
its own build directory; the phases run one after another. The questlang tests are built once, in the background,
into a shared build directory, and then run in parallel there (section 2.3). The runtime's C files are compiled once
into objects that every link reuses ([codegen-c.md](codegen-c.md) §11.3).

### 5.2. A Possible Speedup
**Avoid redundant precursor runs in error tests.** Each error test first reruns every earlier phase in its own process
to confirm that it passes (section 3.4), although the target-phase run already executes those phases in the same
process. If the target run's diagnostics recorded which phase failed, one process per test would suffice, probably
cutting the error suite by half to two-thirds.
