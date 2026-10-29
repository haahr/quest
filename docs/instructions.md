# Instructions for Working on Quest

These instructions are for any model (or person) working on this project: how to work with its owner, how to run
things, how to approach changes, and the conventions of its code, tests, documentation, and commits. They summarize
practice rather than repeat the detailed documents, which they point to. Read [README.md](../README.md) for the
project's purpose and the list of documents, and [roadmap.md](roadmap.md) for where it is going.

---

## 1. Working With the Owner

- **One committer.** Paul Haahr is the only committer. Work on the branch you are given, commit there, and push
  directly to `origin/main` (`git push origin HEAD:main`) *only when asked*. Never open pull requests.
- **Never push without an explicit instruction to push.** Pushing publishes to `main`, so it needs the owner's
  explicit request for the change at hand. Do not infer one: a request to commit, rebase, fix, or finish something
  is not a request to push, and an instruction to push one change does not carry over to later ones. When work is
  ready, commit it and say that it is ready to push.
- **Before pushing:** fetch, rebase on `origin/main` (or bring the branch up to date as your environment provides),
  and run `tools/check` (§2), or `tools/check --self-hosted-only` for a change to the self-hosted compiler alone.
  Push only a branch whose tests all pass.
- **Ask about decisions that are his,** and act on the rest. Language semantics, deviations from Cardelli's papers,
  policies (what to fix now and what to record), and trade-offs with lasting cost (representations, performance
  versus simplicity) are his. Present them with options and a recommendation, and say which one you would choose and
  why. Conventional or easily reversed choices are yours: make them and mention them.
- **Report faithfully.** Say what you found, not just what you did: failures with their output, steps skipped,
  bugs found in passing, and anything that surprised you enough to change a plan. A claim of done means tested.
- **Plans live in documents.** Larger work gets a written plan in `docs/` with numbered steps and a "done when" for
  each. Each step is a commit (or a few), and the plan is updated as steps finish and as surprises change it. When the
  plan is complete, what it found that is still true moves into the reference documents, and the plan is deleted;
  its history stays in git.
- **The task list** ([tasklist.md](tasklist.md)) records known problems and planned work nobody has started: each
  task has **Problem**, **Reproduce**, **Where to start**, and **Done when**. Add a task for a bug you find but do not
  fix (with the owner's agreement), verify its reproduction before writing it down, and remove the task in the
  commit that finishes it.

## 2. Environment and Commands

- **Python:** always `/opt/homebrew/bin/python3.11`; the system `python3` is too old.
- **Golden and error tests:** `python3.11 run_tests.py --phase all` from the repository root (`--phase` one of
  `tokenize`, `parse`, `typecheck`, `interpret`, `run_c_compiled`; `-k NAME` to filter; `--update-golden` to rewrite
  goldens). See [testing.md](testing.md).
- **Unit tests:** `python3.11 -m unittest discover -s tests/python`, from the repository root.
- **Before a push or a commit:** `tools/check` runs, at once, the self-hosting check seeded from the release (which
  ends with the self-hosted suite), the bootstrap's suite, and the unit tests, with the cores split between them, and
  then the terminal tests alone. `tools/check --self-hosted-only` runs only the self-hosting check, for a change to
  the self-hosted compiler alone: how it compiles (its IR, its C) or a refactoring of `questlang/`. Anything either
  compiler shares (the language, `lib/`, `runtime/`, what programs do or what errors say, the tests) needs the full
  `tools/check` ([testing.md](testing.md) §4.1).
- **The driver:** `python3.11 bootstrap/python/quest_driver.py --stop-after PHASE file.quest`, with `PHASE` one of
  `tokenize`, `parse`, `typecheck`, `interpret`, `codegen_c` (prints the C), `run_c_compiled`; `--echo` echoes
  top-level phrases; `--build-dir DIR` keeps a program's compiled interfaces and modules out of the source tree.
- **The self-hosted compiler:** `./questc` takes the same options, building itself first when its sources have
  changed: from the current release in `release/current` when there is one, else from the bootstrap
  ([release-compiler.md](release-compiler.md)). Its `-j N` compiles up to N modules at once
  ([build-process.md](build-process.md) §7.4).
- **The generated C:** `tools/c-diff` diffs the C of the golden programs as a revision's compiler (`--base`, HEAD by
  default) prints it against the working tree's; the suites check what the C does, not its text
  ([testing.md](testing.md) §2.9).
- **Releases:** `tools/release` cuts one from a clean tree at a commit on `main`, after the self-hosting check seeded
  from the current release (`--seed bootstrap` for the first, or past a gap); `--verify`, `--rollback`, and `--show`
  check, undo, and describe them.
- **Scratch files** go outside the repository (a temporary or scratchpad directory), never into `tests/` or `docs/`
  unless they become tests or documents.
- **Shared git state.** Several sessions may work in worktrees of one repository, sharing its stash. Do not use bare
  `git stash`/`git stash pop`; use a uniquely tagged stash and remove exactly that entry, or a temporary commit.

## 3. Method

- **Reproduce first, minimally.** Reduce a failure to the smallest program that shows it, and run it in both
  `interpret` and `run_c_compiled`. The interpreter is the reference: it shares nothing with the C backend, so
  compiled output that differs from it is a C bug unless the documents say otherwise.
- **Write the test before the fix,** and check that it fails without the fix (revert the fix, or stash just it, and
  rerun). A test that passes either way tests nothing.
- **Make sure a probe exercises what you think it does.** For example, direct calls of polymorphic functions with
  record or variant type arguments are *specialized* in C, so they never reach the generic code; call through a
  first-class polymorphic value (`let f: All(A::TYPE x: A) A = g`) to test generic paths.
- **Fix the class, not the instance.** When a bug comes from a pattern (a structural test on an unreduced type, a
  lookup by name), search for its other occurrences and fix or record them.
- **Prefer root-cause fixes.** If a workaround is the right step for now, say so in a comment and in a task.
- **Policy for bugs found along the way:** silent wrong answers (miscompilations) are fixed promptly; other failures
  are recorded (a task, and where a test cannot pass, a skipped phase with the reason) unless the owner decides
  otherwise. Ask when a case does not fit.
- **Validate before every commit:** `tools/check` (or `--self-hosted-only`, §2), all passing; a comment- or
  documentation-only change needs no suites. Keep the worktree clean between steps.
- **Measure when performance is at stake:** `python3.11 tests/perf/measure.py` compares C generation time, C size,
  and benchmark run times with `tests/perf/baseline.json` (on the same machine).

## 4. Code Conventions (Python Bootstrap)

- **Match the surrounding code** in naming, structure, comment density, and idiom. Lines of code are at most 120
  columns. Modules start with a docstring and `from __future__ import annotations`; use type hints and frozen
  dataclasses as the existing code does.
- **Comments wrap at 80 columns,** narrower than code so that prose stays easy to read. This holds for docstrings and
  every comment on lines of its own, in Python, Quest (`lib/`, `questlang/`, `examples/`), and C (`runtime/`): fill each
  paragraph so that no line, indentation included, passes column 80, and keep examples, aligned text, and lists in their
  own lines. A comment at the end of a line of code goes with the code and its 120 columns.
- **Docstrings and comments explain what and why,** in full sentences: what a function returns or does, what
  invariant it relies on, why a non-obvious choice was made. Do not narrate the code or its history ("now",
  "previously", "fixed"); that belongs in commit messages.
- **Identity is by symbol, never by name or by object.**
  - Bindings, type parameters, functions, and globals are identified by their symbols (`symbol_id`). Never look one
    up by name where another binding of the same name could be in scope (shadowing, a caller's and a callee's `A`).
  - Never key side tables by `id()` of typed AST nodes: transformations that copy nodes (specialization) leave the
    copies out. Put the data in the nodes, or give nodes explicit ids.
  - Re-elaborating a declaration mints fresh symbols, which no longer match the original; elaborate once.
- **Types are hash-consed and have no Python `==`** (it raises). Compare with `is_type_equal(t1, t2, env)` or
  identity (`is`), and key dictionaries by `type_identity_key` (C backend) or by canonical objects, not by types.
- **Types reach code generation unreduced:** alias nodes, applications of type operators (`Box(A)`), and recursive
  types. Below lowering, ask the type's shape (`ir/shapes.py`); elsewhere, reduce with `normalize_type`
  (`types/canonical.py`) before structural tests such as `isinstance(t, QTupleType)`; a test on the unreduced type
  silently skips `Box(A)`.
- **Invariant checks run in tests.** `QUEST_CHECK_CANONICAL=1` (C canonical forms), `QUEST_CHECK_SCOPES=1`
  (well-scoped typed programs), and `QUEST_CHECK_IR=1` (verified IR) are set by the test runners and the unit tests'
  helpers; production builds warn or skip. Add new internal checks the same way.
- **Diagnostics** are `QuestCompilerError` and its subclasses (`QuestTypeError`, which the type checker calls
  `TypeError`; `KindError`; ...) with source offsets.
  Messages are full sentences that quote names and types (`Recursive type 'T' must be applied to exactly its
  parameters, ...`). Internal errors start with `internal:`; limitations of the C backend start with `C code
  generation cannot ...`. See [diagnostics.md](diagnostics.md).
- **Generated C stays readable:** structured, with names derived from the source, so that it can be debugged.
- **Generated files are not edited by hand.** `tests/source/conversions/` comes from `tests/conversions/generate.py`
  the `parser_*` tests from `tests/parser/generate.py`, the `types_*` tests from `tests/types/generate.py`, and the
  `elaborate_*` tests from `tests/elaborate/generate.py`; change
  the generator and regenerate.
- **Interface and ABI changes:** a change to what `.qi` files or generated headers contain needs an `ABI_VERSION`
  bump ([build-process.md](build-process.md) §5.2); `tests/python/test_abi_corpus.py` checks it.

## 5. Writing Quest (Tests and Library Code)

Quest's syntax ([syntax.md](syntax.md); [converting-python-to-quest.md](converting-python-to-quest.md) for idioms)
has traps that cost time:

- **Infix operators share one precedence and associate to the right:** `a * 10 + b` is `a * (10 + b)`, and
  `i % 3 is 0` is `i % (3 is 0)`. Group with **braces**: `{a * 10} + b`. Parentheses are only for calls.
- **Equality is `is` and `isnot`;** `=` appears only in bindings (`let x = ...`, `record a = 1 end`). `is` on
  tuples, records, and arrays is identity.
- **Identifiers are letters and digits only** (no underscores), and so are the directory and file names of
  interfaces and modules.
- **Some capitalized words are keywords:** `Var`, `Rec`, `Out`, `Let`, `Def`, `Fun`, `All`, `Tuple`, `Record`, ...
  cannot name types. Function *types* are written `All(x: Int) Bool`; `Fun(X::K) T` is a type operator.
- **Option payloads:** `option some of T with v end` takes the payload's components; when the payload is a single
  value that is itself a tuple, name the component (`with let value = v end`).
- **Every construct closes with `end`,** including `raise E end`, `if ... end`, and `begin ... end`; a missing or
  extra `end` usually shows up as an unexpected token later on.
- **Type arguments are explicit or inferred:** `f(:Int x)`; a polymorphic constant is applied to types alone
  (`nil(:Int)`).
- **No semicolons except after a top-level phrase,** where they are optional ([extensions.md](extensions.md#semicolons)).
  `begin let a = 1; a end`, `f(1; 2)`, and `Record x: Int; y: Int end` are syntax errors. The style in `lib/`,
  `questlang/`, and `examples/` is to write none at all; tests may end top-level phrases with them.

## 6. Tests

See [testing.md](testing.md) for the framework. In practice:

- **Golden tests** are programs in `tests/source/**` with expected outputs per phase in `tests/golden/<phase>/`; the
  `interpret` and `run_c_compiled` phases share one golden (`tests/golden/run/`), which is how the backends are
  compared. Generate goldens with `--update-golden -k NAME`, then *read* them: a golden is a claim about correct
  behavior, not a record of whatever the compiler printed. Changing a test's comments changes its `tokenize` golden.
- **Error tests** are programs in `tests/errors/<phase>/` with inline expectations (`(* ERROR: regexp *)` on the
  line of the error) and `.error` goldens in `tests/golden/errors/`. Errors raised by C generation cannot be error
  tests (the `run` phase needs C generation to succeed); test them in `tests/python/`.
- **Directives** in comments: `@skip-phase` (with a comment giving the reason, and the task, if there is one),
  `@args`, `@env`, `@exit`, `@stdin`, `@echo`, `@timeout`.
- **Unit tests** live in `tests/python/` and import `tests.python.helpers` for parsing, elaborating, and running, and
  for the invariant checks it enables.
- **Generated matrices** cover combinations by construction: the conversion matrix
  (`tests/conversions/generate.py`) lists cells that fail in C, each with its reason, and cells C generation rejects.
- **Name tests for what they test,** with a comment at the top saying what and why, and section comments
  (`(* 1. ... *)`) whose numbers appear in their output where that helps locate a failure.
- **The self-hosting check,** `run_tests.py --self-hosting` (with `--seed release` to start from the release), runs
  before every push, as part of `tools/check`.

### 6.1. Releases

- **`questlang/` may use only what the current release compiles,** against the release's own `lib/` and `runtime/`.
  Using a new language feature, `lib/` function, or runtime primitive in `questlang/` takes a commit that adds it, a
  release cut from that commit, and then a commit that uses it. `QUESTC_SEED=bootstrap` builds past such a gap when
  the bootstrap has the feature too.
- **Cut a release** by hand, never automatically: when `questlang/` needs something the current release cannot
  compile, after a larger piece of work, and otherwise when convenient. Only the owner asks for one, as for a push.
- **Roll back** (`tools/release --rollback`) when a release turns out to be bad, and say so; one previous release is
  kept.

## 7. Documentation

- **The documents are the specification;** keep them true. Update them in the same commit as the change they
  describe: [type-system.md](type-system.md) (types and checking), [runtime-design.md](runtime-design.md) (the compiled
  runtime architecture), [c-representation.md](c-representation.md) (the C ABI), [codegen-c.md](codegen-c.md) (the C
  backend), [ir.md](ir.md) (the IR and its passes), [modules.md](modules.md), [testing.md](testing.md),
  [tasklist.md](tasklist.md), and others as they apply. Add new documents to the list in [README.md](../README.md).
- **Describe the system as it is,** with the decisions and limitations that shaped it and the reasons for them;
  history belongs in commit messages. A limitation accepted for now is documented where the behavior is, and gets a
  task.
- **Measurements carry their dates,** since a number is only as current as the code it was taken on: a timing, a
  profile, or a benchmark baseline says when it was measured. [benchmarks.md](benchmarks.md) is the one document that
  keeps history: its dated baselines stay as later ones are added, so that each can be compared with the ones before.
  Take the dates from the measurements themselves (the commit that recorded them, or the results' files), so that
  they are accurate.
- **Style:** prose and bullets at 120 columns, numbered sections (`### 5.1.`), relative links, code and names in
  backticks. Refer to code by file and function (`_elaborate_fun_expr` in `typechecker/bindings.py`), and check that
  the names exist. Cite Cardelli's papers (in `docs/`) by title and section when following or departing from them.

## 8. Commits

- **One logical change per commit;** a plan's steps are separate commits. A fix and its test go together.
- **Subject:** imperative, specific, about the effect, and under about 72 characters (`Declare mutable locals
  assigned in try bodies volatile in C`).
- **Body:** wrapped at about 80 columns; what was wrong (with its symptom), why, and what the change does, in prose.
  Mention surprises and anything left for later.
- **Trailer:** end with the co-author line your environment specifies for the model writing the commit, for example
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Commit only files that belong to the change; no scratch files, no generated output that the tests regenerate.

## 9. Current Direction

- The C backend lowers typed ASTs through the five-pass intermediate representation ([ir.md](ir.md)): ANF with
  structured control flow and join points (`ir_core` $\to$ `ir_specialized` $\to$ `ir_closed` $\to$ `ir_represented`
  $\to$ `ir_described`), with representations, 1-word slot boxing, and tagged proxies decided by `ir/represent.py` and
  runtime descriptors materialized by `ir/describe.py`.
- Compiled code uses native representations in locals/parameters/returns (including 16-byte `QRecordVal` and
  `QVariantVal`), uniform 1-word boxed slots (`slot_representation`) in all aggregates, own views with `QViewMap` for
  bounded type parameters, and tagged `QProxy` views for depth-upcast tuples and options
  ([runtime-design.md](runtime-design.md), [c-representation.md](c-representation.md)).
- Open bugs and planned follow-up work for the compiler are tracked in [tasklist.md](tasklist.md).
- The self-hosted compiler compiles itself to a fixed point ([roadmap.md](roadmap.md) step 5), seeded by a release
  ([release-compiler.md](release-compiler.md)). It is the
  primary compiler; the bootstrap is kept so that the compiler can be rebuilt from nothing ([testing.md](testing.md)
  §2.8):
  - **Both compilers get** language changes, `lib/` changes, and fixes to bugs in what programs do or what errors
    they report. Each such change comes with a test in a shared phase (a run, error, or front-end test), which both
    suites run, so that a change made in one alone fails the other's.
  - **The self-hosted compiler alone gets** optimizations and other changes to how it compiles (its IR and C), with
    goldens of its own (`--self-hosted --update-golden`).
  - **The runtime is shared:** a change to it must keep the bootstrap's C working.
  - **`questlang/` uses only what the bootstrap compiles,** as well as what the release does, so that the bootstrap
    can still build it.
  - Prefer clarity over cleverness in the bootstrap.
