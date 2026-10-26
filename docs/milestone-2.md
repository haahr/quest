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
  by an object that hashes by identity). A hash map keeps insertion order, as a Python dictionary does (it is laid
  out as CPython's is), so the bootstrap's reliance on that order carries over.
- **Testing.** Golden tests only. The bootstrap's suites run only when the bootstrap changes. The full goldens run
  against the compiled self-hosted driver, never an interpreted one (§3).
- **Layout.** `questlang/` follows the reorganized bootstrap module for module (§1), as the parser does.
- **Pace.** The steps run straight through, each pushed when its runs pass, stopping only for a surprise that needs
  a decision.

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

Quest modules import each other acyclically; the bootstrap had two cycles (lazy imports inside functions), plus the
mixins' calls back into the checker. Step 0 broke each in the bootstrap, so that the two layouts stay the same:

1. **`types.env`, `types.kinds`, `types.subtyping`, `modules.graph`.** Subtyping imported `allocate_symbol_id` from
   `env`, `env` cleared subtyping's cache, and `env` and `graph` imported each other. The symbols and scopes
   (`Symbol`, `ValueSymbol`, `TypeSymbol`, `KindSymbol`, `Scope`, `allocate_symbol_id`, the global symbol indexes) are
   now `types/symbols`, below `subtyping` and `graph`; a symbol gaining a meaning bumps a generation there, and the
   subtype cache drops itself when the generation changes. `env` imports `graph`. The graph's resolution functions
   still take an environment for its directory, search paths, and units (duck typed in Python); in Quest they take
   those directly.
2. **`typechecker.typecheck`, `typechecker.bindings`, `modules.elaboration`, `modules.loader`, `modules.stdlib`,
   `modules.interface_compiler`.** Elaboration called back into the loader and the checker. Now elaboration is below
   both: the loader registers its functions with it (`register_unit_loader`) when imported, `typecheck` registers
   `elaborate_binding` (`register_binding_elaborator`) and imports the loader, and elaboration's `load_interface` and
   `load_module` call the registered ones, as do `stdlib` and `interface_compiler`. (The `Environment`'s builtin
   registry, which `stdlib` registers, already worked this way.) In Quest the hooks are `var` fields of a tuple that
   `elaboration` exports.
3. **The checker's mixins.** `TypeElaborator` combined one mixin per construct family, and each called the others and
   the dispatch through `self`. The state and shared helpers are now `typechecker/checker.py`'s `Checker`, the base
   of every family, which declares the dispatch (`check_expr`, `synth_expr`) that `TypeElaborator` defines. The
   families call each other in one direction (`exceptions` and `auto_values` below `bindings` and `application`,
   `bindings` below `aggregates` and `control`). In Quest, `checker.T` is a tuple holding the state and `var` fields
   for the dispatch functions, which `typecheck` fills when it makes a checker; a family calls the families below it
   directly.

### 1.2. Representations

- **Types and kinds** are options (`model.Type`, `model.Kind`) inside a node tuple that carries what the bootstrap
  caches on its objects (free variables, the interning key). Interning, the subtype cache, and the kind cache are
  hash maps; a type's identity (Python's `is` after interning) is `hash.identityEqual`.
- **Symbols and scopes** are tuples with `var` fields; a scope's members are a hash map from name to symbol, in
  insertion order as the bootstrap's dictionaries are.
- **The typed AST** follows `typed_ast.py` as `syntax/ast` follows `ast.py` (compiler-organization.md §3), and
  `typedastprint` prints what `TypedNode.dump` prints.
- **Desugaring** is a pass over the self-hosted AST, before the checker, as in the bootstrap.

---

## 2. Reporting Several Errors

The bootstrap raises `QuestTypeError` at the first error and the pipeline reports it. The self-hosted checker
reports that error first, with the same message and span, and goes on to find others.

- **Reporting.** As the bootstrap raises `QuestCompilerError` and its subclasses where it finds an error, the
  self-hosted compiler raises `diagnostics.compilerError`, whose payload is the message, the offset in the unit being
  checked (0 where the raiser does not know where, as for the bootstrap's kind errors, which it reports at 1:1), the
  length, the help and notes, and whether it is fatal. Raising stops the work the error was part of, as in the
  bootstrap. An error that propagates out of a unit loaded from a file records the file (`env.withUnitSource`, the
  bootstrap's `in_unit`); `diagnostics.errorDiagnostic` makes the diagnostic, in that file or the current one.
- **Recovery.** The checker catches `compilerError` at each binding: each phrase of a program, each binding of a
  block (function bodies, conditionals, and loops are made of blocks), and each member of an interface or module,
  and adds its diagnostic to the bag. The failed binding contributes nothing to the typed AST, and the checker goes
  on with the next. Code that changes the environment's state (its scopes, the unit being elaborated) restores it as
  the error propagates, as the bootstrap's `finally` blocks do (`env.scoped`).
- **No cascades.** The names a failed binding declares are bound to poisoned symbols: a poisoned value symbol, or a
  type or kind symbol whose definition is unknown. Using a poisoned symbol raises an error that the recovery point
  does not report, so a binding that depends on one fails silently. A binding with a declared type (`let f(x: Int): Int = ...`,
  `let x: T = ...`) is bound at that type even if its value fails, so its users are still checked. A failed import
  poisons the names it would have bound.
- **Fatal errors** stay fatal: an error that leaves nothing sensible to check (a cycle of imports, an internal error,
  the well-scopedness check of `scoping`) adds a fatal diagnostic and raises `diagbag.fatalError`, as syntax errors do.
- **Limit.** After 20 errors the checker reports that it stopped (a fatal diagnostic) and stops.
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

### Step 0: Bootstrap refactorings (done)

Break the cycles of §1.1 in the bootstrap: `types/symbols.py`; the elaboration hooks; `typechecker/checker.py`. No
output changes; both bootstrap suites pass. (The benchmarks, `tests/perf/measure.py`, time the C backend and compiled
programs, which this step does not change.)

**Done when** the bootstrap's import graph among `types`, `typechecker`, `modules`, and `syntax` (lazy imports
included) is acyclic.

### Step 1: Driver, desugaring, and the self-hosted suite (done)

Port `syntax/desugar`; write `driver/main` with the
tokenize, parse, and desugar phases; add `--self-hosted` and the pending list to the runner; remove the generated
`astprint_*` tests and `tests/astprint/` (the driver checks every parse golden directly; the `parser_*` tests stay, for
the grammar's rules and errors); update testing.md.

**Done when** the driver passes every tokenize and parse golden and the tokenize and parse error tests, and the
typecheck goldens are all pending. (This also checks the parser on every test program directly, beyond the
`parser_*` tests.)

### Step 2: Symbols, types, kinds, and their printer (done)

Port `types/symbols`, `model` (types, kinds, substitution, free variables, interning), and `dump` (the canonical and
compact formatters, which error messages and the typed AST dump use). Test with questlang tests that build types and
print them, whose goldens a script (`tests/types/generate.py`, like `tests/parser/generate.py`) gets from the
bootstrap building the same types.

**Done when** those tests pass compiled. (`structurally_equal` is not ported: nothing uses it. The model's components
are plain tuples, whose identity is that of the types they hold; nodes record their identity as an id.)

### Step 3: Subtyping, kinds, contractiveness, environments (done)

Port `subtyping` (equi-recursive proofs and their cache), `kinds` (kind synthesis and checking), `contractiveness`,
and `env` (the environment and the builtin registry, without units yet). Test the judgments with generated tests, as
in Step 2.

`kinds` and `contractiveness` use the environment's scopes, so in Quest they are above `env`; the bootstrap's
`INFIX_OPERATORS`, which `env` declares and `kinds` only held, moved to `env.py` to keep the two layouts the same.
Subtyping takes only the environment's lookups (`subtyping.Env`, the bootstrap's `env` or `None`). The step found and
fixed a bug of the bootstrap's C backend: a closure returning `Ok` adapted to a generic result
(`modules/ok_result_closures`).

### Step 4: Elaborating types; the typed AST (done)

Port `typechecker/typedast`, `typedastprint`, `elaboratetypes`, and `checks`. Test elaboration with a generated test,
as the parser's are: `tests/elaborate/generate.py` makes `elaborate_types`, which elaborates programs of type and kind
declarations and prints the symbols they declare, or the first error, as the bootstrap does.

The bootstrap locates errors in components (parameters, field signatures, bindings, branches, imports) at their own
offsets, so the AST's component tuples gained the offsets the bootstrap's nodes have, and the parser tests compare
them (`astprint.dumpWithOffsets`, the driver's `--show-offsets`). The bootstrap's `_RecOperatorSymbol`, a subclass of
`TypeSymbol`, is a table of the operators being defined, by symbol id. A type path through a module to a module
(`m.n.T`) is reported as an undefined module; the bootstrap's scopes have no `lookup_module`, so it fails there. The
driver's typecheck phase moved to Step 5, since it is the checker's program loop.

### Step 5: The checker (done)

Port `checker`, `typecheck` (and with it the driver's typecheck phase), and the construct families in dependency
order: literals, variables, blocks, and functions (`bindings`); calls (`application`, `lvalues`, `metas`); control
flow (`control`); aggregates; exceptions; auto values (`autovalues`, `escape`); and `scoping`, which runs in the driver
when `QUEST_CHECK_SCOPES=1`, as the runner sets it. Report errors as §2 has them from the first construct on. Goldens
of programs without imports leave the pending list as their constructs land.

The runner's self-hosted phases include typecheck, and the pending list started with the typecheck goldens and error
tests the driver failed: those of imports, interfaces, modules, and the standard library, which Step 6 takes off.
§2's recovery is in place: a phrase, a block's binding, and (Step 6) a module's member are recovery points
(`bindings.elaborateRecovering`, `checker.attempt`), and a block with a failed binding fails silently
(`diagnostics.silentError`); a failed declaration's names are bound to poisoned symbols (`symbols.poisonValue`,
`symbols.poison`), or to its declared type, from its annotations. Every typecheck error test the driver can run passes
with one error.

Open question: `errors/typecheck:aggregates/tuple_unsupported_component_checked` expects the bootstrap's type error
for an import inside a tuple, which the self-hosted parser rejects as a syntax error (the self-hosted AST holds
imports, interfaces, and modules only at the top level, Milestone 1). It stays pending until that is decided.

### Step 6: Modules from source (done)

Port `modules/paths`, `units`, `graph` (resolution and the unit graph, without artifacts), `abstracttypes`,
`loader` (from source only), `elaboration`, and `stdlib`. The remaining typecheck goldens, which import the standard
library or the test's own modules, leave the pending list.

Every typecheck golden and error test passes, and the pending list holds only Step 5's open question. Where the two
compilers differ:
- **Paths** are strings, made absolute and normalized lexically, without following symbolic links. The project
  directory, which the bootstrap knows as its own source tree, is `QUEST_HOME`, which the runners set (the driver runs
  in a scratch directory), or else the current directory.
- **Interfaces** are elaborated from source in the importer's environment, with the unit's own names
  (`env.withUnitNames`), where the bootstrap driver compiles each to a `.qi` in an environment of its own and loads
  that; the messages of unit files are those of that path (`units.unitDeclaration`). A module's external types are
  named `module.T` in its export scope, as the bootstrap's typecheck-only runs, which type modules with fresh
  artifacts through their interfaces, name them.
- **Locations.** An error propagating out of an import is located there as the bootstrap's `at_import` and
  `in_unit` do (`env.atImport`, `env.withUnitSource`, `diagnostics.atImport`, which adds the "imported here"
  labels); one reported at a recovery point inside a unit is located as if it had propagated (`env.locate`, from the
  stack of imports being loaded). Diagnostics render labels in other files from the source maps registered for them
  (`diagnostics.registerSource`).
- **Recovery.** An import, an interface, and a module declaration are recovery points, and a module's members too
  (the elaboration hook is `bindings.elaborateRecovering`); a module with a failed member fails silently, and a failed
  import or module poisons the names it would have bound.

The step found and fixed a bug of the bootstrap's C backend: a member of a recursive type group that does not refer
back to itself is not recursive, and has its unfolding's shape (`ir/shapes.py`), so that a tuple literal of it in
another module has its representation (`modules/nonrecursive_group_member`; ABI version 37).

### Step 7: Errors (done)

Run the typecheck error tests; review and record each test's further errors (§3.2); add tests of several errors to
`tests/self-hosted/errors` (independent errors in one file, errors after a failed declaration with and without a
declared type, a failed import); and fix cascades the review finds.

No typecheck error test reports a further error, so none is recorded. The tests of several errors are
`tests/self-hosted/errors/typecheck` (independent errors, failed declarations with and without declared types, a
block's errors, a failed import, and the limit of 20), which the runner's `--self-hosted` runs: every diagnostic must
be one of the test's inline expectations, and every expectation must be reported. The error tests' harness now reads
`fatal error:` diagnostics, which it had not recognized.

**Done when** every typecheck error test reports the bootstrap's error first and its recorded output exactly.

### Step 8: Wrapping up

Empty the pending list; update compiler-organization.md (§2's "so far", §6) and testing.md; record the divergences
(as §2 and the representations make them) in this document; remove the scratch tooling.

Done but the pending list: it holds Step 5's open question, an import inside a tuple, which needs a decision (the
self-hosted AST holding imports, interfaces, and modules below the top level, or the test changing). The divergences
are recorded in Steps 4 to 7; the scratch tooling was never in the repository.

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
