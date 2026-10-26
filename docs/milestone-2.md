# Milestone 2: The Self-Hosted Type Checker

This plan ports the bootstrap's type checker to Quest: the semantic types (`bootstrap/python/quest/types/`), the type
checker (`typechecker/`), desugaring (`syntax/desugar.py`), and the part of the module system that type checking
needs (`modules/`, loading units from source). At the end, a compiled self-hosted driver type checks every program
of the test suite and prints the typed AST the bootstrap prints, or the bootstrap's first error and any further
errors it finds. It follows Milestone 1 (the front end, [compiler-organization.md](compiler-organization.md) §6) and
precedes Milestone 3 (values and the tree-walking interpreter).

The decisions this plan rests on (2026-10-26):
- **Errors.** The self-hosted checker reports every error it can, not only the first, using exceptions where they are
  the right tool (§2).
- **Maps.** Mutable maps are `collections/hashmap` (identity maps where the bootstrap keys a dictionary by `id()` or
  by an object that hashes by identity).
- **Testing.** Golden tests only. The bootstrap's suites run only when the bootstrap changes. The full goldens run
  against the compiled self-hosted driver, never an interpreted one (§3).
- **Layout.** `questlang/` follows the reorganized bootstrap module for module (§1), as the parser does.

Translation follows [converting-python-to-quest.md](converting-python-to-quest.md); the parser port (Milestone 1) set
the conventions: identical messages and spans, divergences only where Quest cannot hold what Python does, and each
divergence documented where it is made.

---

## 1. Layout

Each bootstrap module becomes the Quest module of the same name, lowercased with its underscores removed (canonical
names are letters and digits, [modules.md](modules.md) §2.3). Milestone 2 ports:

```
questlang/
├── common/        location, diagnostics, diagbag            (done)
├── syntax/        tokens, tokenizer, ast, astprint, parser, parser/* (done); desugar
├── types/         symbols (new, §1.1), model, kinds, subtyping, contractiveness, env, dump
├── typechecker/   typedast, typedastprint, checker (§1.1), checks, escape, lvalues, metas, elaboratetypes,
│                  bindings, application, aggregates, control, exceptions, autovalues, typecheck, scoping
├── modules/       paths, units, graph, abstracttypes, loader, elaboration, stdlib
└── driver/        main (the front end's phases, §3.1)
```

Later milestones add `values/` and `interpreter/` (3), `ir/` and the IR interpreter (4), and `codegen/`, the build
artifacts (`modules/interfacecompiler`, `modulecompiler`, `manifest`), and the full driver (5). `types/canonical`
is the backends', so it comes with Milestone 4.

### 1.1. Import cycles

Quest modules import each other acyclically; the bootstrap has two cycles (lazy imports inside functions), plus the
mixins' calls back into the checker. Each is broken in the bootstrap first (Step 0), so that the two layouts stay the
same:

1. **`types.env`, `types.kinds`, `types.subtyping`, `modules.graph`.** Subtyping imports `allocate_symbol_id` from
   `env`, and `env` and `graph` import each other (an `Environment` holds its `UnitGraph`; the graph resolves imports
   from an `Environment`'s directory and search paths). Move the symbols and scopes (`Symbol`, `ValueSymbol`,
   `TypeSymbol`, `KindSymbol`, `Scope`, `allocate_symbol_id`) to a new `types/symbols`, below `subtyping`, `kinds`,
   and `graph`; give the graph's resolution functions the directory and search paths rather than the environment.
2. **`typechecker.typecheck`, `typechecker.bindings`, `modules.elaboration`, `modules.loader`, `modules.stdlib`
   (and `modules.interface_compiler`).** The checker elaborates interfaces, modules, and imports by calling
   `modules.elaboration`, which calls back into the checker for bindings, and loads units through `loader`, which
   elaborates them and loads `.qi` files through `interface_compiler`. Make the dependencies point one way, checker
   above modules: the elaboration functions take the checker's entry points (`elaborate_binding`) as a parameter,
   the loader takes the elaboration it runs on a loaded unit, and loading a `.qi` is a hook that the driver installs
   when it has a build directory (so the type checker itself never imports `interface_compiler`).
3. **The checker's mixins.** `TypeElaborator` combines one mixin per construct family, and each calls the others
   through `self` (`self.check_expr` from `aggregates`, for instance). Move its state and shared helpers to
   `typechecker/checker.py`, a class the mixin modules import, with the dispatch (`check_expr`, `synth_expr`,
   `elaborate_binding`) reached through it. In Quest, `checker.T` is a tuple holding the state and `var` fields for
   the dispatch functions, which `typecheck` fills when it makes a checker, so that the construct modules sit below
   `typecheck` and call up through the tuple.

### 1.2. Representations

- **Types and kinds** are options (`model.Type`, `model.Kind`) inside a node tuple that carries what the bootstrap
  caches on its objects (free variables, the interning key). Interning, the subtype cache, and the kind cache are
  hash maps; a type's identity (Python's `is` after interning) is `hash.identityEqual`.
- **Symbols and scopes** are tuples with `var` fields; a scope's members are a hash map from name to symbol, with the
  insertion order the bootstrap's dictionaries keep (a vector of names beside the map) wherever output depends on it.
- **The typed AST** follows `typed_ast.py` as `syntax/ast` follows `ast.py` (compiler-organization.md §3), and
  `typedastprint` prints what `TypedNode.dump` prints.
- **Desugaring** is a pass over the self-hosted AST, before the checker, as in the bootstrap.

---

## 2. Reporting Several Errors

The bootstrap raises `QuestTypeError` at the first error and the pipeline reports it. The self-hosted checker
reports that error first, with the same message and span, and goes on to find others.

- **Reporting.** `diagbag` gains `failed: Exception(Ok)` and `fail(bag span message)`, which adds an error to the bag
  and raises `failed`. Every place the bootstrap raises a type error calls `fail` (through `checks` and the checker's
  helpers), so an error stops the work it was part of, as in the bootstrap.
- **Recovery.** The checker catches `failed` at each binding: each phrase of a program, each binding of a block
  (function bodies, conditionals, and loops are made of blocks), and each member of an interface or module. The
  failed binding contributes nothing to the typed AST, and the checker goes on with the next.
- **No cascades.** The names a failed binding declares are bound to poisoned symbols: a poisoned value symbol, or a
  type or kind symbol whose definition is unknown. Using a poisoned symbol raises `failed` without adding an error,
  so a binding that depends on one fails silently. A binding with a declared type (`let f(x: Int): Int = ...`,
  `let x: T = ...`) is bound at that type even if its value fails, so its users are still checked. A failed import
  poisons the names it would have bound.
- **Fatal errors** stay fatal: an error that leaves nothing sensible to check (a cycle of imports, an internal error,
  the well-scopedness check of `scoping`) adds a fatal diagnostic and raises `diagbag.fatalError`, as syntax errors do.
- **Output.** The typed AST is printed only when there are no errors. The errors are printed in the order found,
  which is source order, as the bootstrap renders its one.

The bootstrap keeps stopping at the first error; it is the oracle for that error only.

---

## 3. Testing

### 3.1. The self-hosted driver

`questlang/driver/main` is a main routine that reads a Quest file and runs the self-hosted front end on it, with the
bootstrap driver's options for these phases: `--stop-after tokenize|parse|desugar|typecheck` prints the phase's dump
in the bootstrap's format (the token dump, `ast_dump`, and the typed AST dump), `-I` adds a search path, and the
standard library's interfaces are read from `lib/` (or `QUEST_LIB`), from source: `.qi` files are Milestone 5's. A
diagnostic is printed as the bootstrap prints it.

It is compiled to C by the bootstrap (`./quest -o build/questlang/main questlang/driver/main.quest`), once per test
run, into the test run's build directory.

### 3.2. Runs

- **The self-hosted suite** (`run_tests.py --self-hosted`, new): builds the driver, then runs it on every test
  program for the phases it has, comparing with the bootstrap's goldens (`tests/golden/tokenize`, `parse`,
  `typecheck`) and error expectations (`tests/errors/{tokenize,parse,typecheck}`). The goldens are the bootstrap's,
  unchanged: there is nothing to generate. For an error test, the driver's first diagnostic must be the expected one;
  its complete output must match `tests/golden/self-hosted/errors/PHASE/NAME.error`, which records the further
  errors once they are reviewed. Tests of several errors, which the bootstrap cannot pass, are in
  `tests/self-hosted/errors`.
- **Pending tests.** `tests/self-hosted/pending.txt` lists the goldens the driver is not yet expected to pass, one
  per line; the suite reports them separately and fails if one passes (so it is removed) or if a test not listed
  fails. The list starts with every typecheck golden and is empty when the milestone is done.
- **The self-hosted modules' own tests** (`tests/source/questlang`, which test modules from Quest programs, like
  `syntax_tokenizer`) run compiled, `run_tests.py --phase run_c_compiled -k questlang/`, in a normal run.
- **The bootstrap's suites** (`run_tests.py` and the unit tests) run only in a commit that changes the bootstrap,
  `lib/`, or `runtime/`, and in Step 0. A run of the full golden suite interprets the questlang tests too, so they
  are exercised there as well.

A commit is pushed when its runs pass: the self-hosted suite and the questlang tests always, and the bootstrap's
suites when it changes what they test. testing.md and the memory of push rules change accordingly (Step 1).

---

## 4. Steps

Each step is one or more commits; each ends with its runs passing.

### Step 0: Bootstrap refactorings

Break the cycles of §1.1 in the bootstrap: `types/symbols.py`; the graph's resolution without an `Environment`; the
elaboration and loader hooks; `typechecker/checker.py`. No output changes; both bootstrap suites and the benchmarks
(within 10% of main, `tests/perf/measure.py`) pass.

**Done when** the bootstrap's import graph among `types`, `typechecker`, and `modules` (lazy imports included) is
acyclic apart from `modules.interface_compiler`, `module_compiler`, and their users, which the driver wires.

### Step 1: Driver, desugaring, and the self-hosted suite

Port `syntax/desugar`; write `driver/main` with the tokenize, parse, and desugar phases; add `--self-hosted` and the
pending list to the runner; update testing.md and compiler-organization.md (§2, §5, §6).

**Done when** the driver passes every tokenize and parse golden and the tokenize and parse error tests, and the
typecheck goldens are all pending. (This also checks the parser on every test program directly, beyond the
`parser_*` tests.)

### Step 2: Symbols, types, kinds, and their printer

Port `types/symbols`, `model` (types, kinds, substitution, free variables, interning), and `dump` (the canonical and
compact formatters, which error messages and the typed AST dump use). Test with questlang tests that build types and
print them, whose goldens a script (`tests/types/generate.py`, like `tests/astprint/generate.py`) gets from the
bootstrap building the same types.

**Done when** those tests pass compiled.

### Step 3: Subtyping, kinds, contractiveness, environments

Port `subtyping` (equi-recursive proofs and their cache), `kinds` (kind synthesis and checking), `contractiveness`,
and `env` (the environment and the builtin registry, without units yet). Test the judgments with generated tests, as
in Step 2.

### Step 4: Elaborating types; the typed AST

Port `typechecker/typedast`, `typedastprint`, `elaboratetypes`, and `checks`, and the driver's typecheck phase for
programs of type and kind bindings. Typecheck goldens of programs without imports and with only type bindings leave
the pending list.

### Step 5: The checker

Port `checker`, `typecheck`, and the construct families in dependency order: literals, variables, blocks, and
functions (`bindings`); calls (`application`, `lvalues`, `metas`); control flow (`control`); aggregates; exceptions;
auto values (`autovalues`, `escape`); and `scoping`, which runs in the driver when `QUEST_CHECK_SCOPES=1`, as the
runner sets it. Report errors as §2 has them from the first construct on. Goldens of programs without imports leave
the pending list as their constructs land.

### Step 6: Modules from source

Port `modules/paths`, `units`, `graph` (resolution and the unit graph, without artifacts), `abstracttypes`,
`loader` (from source only), `elaboration`, and `stdlib`. The remaining typecheck goldens, which import the standard
library or the test's own modules, leave the pending list.

### Step 7: Errors

Run the typecheck error tests; review and record each test's further errors (§3.2); add tests of several errors to
`tests/self-hosted/errors` (independent errors in one file, errors after a failed declaration with and without a
declared type, a failed import); and fix cascades the review finds.

**Done when** every typecheck error test reports the bootstrap's error first and its recorded output exactly.

### Step 8: Wrapping up

Empty the pending list; update compiler-organization.md (§2's "so far", §6) and testing.md; record the divergences
(as §2 and the representations make them) in this document; remove the scratch tooling.

---

## 5. Done When

- The compiled self-hosted driver passes every tokenize, parse, and typecheck golden and error test of the suite,
  with the bootstrap's text, and its further errors are recorded and reviewed.
- The questlang tests pass compiled; the bootstrap's suites pass.
- `questlang/` has the layout of §1, and the bootstrap's has no cycles among the ported modules.

## 6. Not in This Plan

- `.qi` and `.qm` artifacts, build directories, and C headers (Milestone 5): the driver reads interfaces from source.
- `types/canonical` (Milestone 4).
- Values, the tree-walking interpreter, `dynamic` serialization, and the REPL (Milestone 3).
- Reporting several errors in the bootstrap.
