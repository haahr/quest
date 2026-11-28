# A Review of the Self-Hosted Implementation for Readability and Structure (2026-11-27)

This review covers all of `questlang/` at 3ca8619a, about 113,000 lines in 25 directories. Its goal is clarity and
maintainability: what makes the code harder than it needs to be for a competent newcomer to read, change, or extend
safely. It is not about speed. It reports bugs only where reading the code turned them up.

Eight reviewers each read one area. Every claim was checked by grep, and the main claims were checked again for this
document (§1, and the counts in §2). The review leaves out:

- what [compiler-organization.md](compiler-organization.md) §7 decided to leave whole;
- what its §8 says the design relies on;
- what [tasklist.md](tasklist.md) already records;
- the wording of comments.

Overall the code reads well, and the reviewers said so area by area:

- **Comments and state.** Every module has an orienting interface comment, and each pass documents the fields of its
  state tuple.
- **The front end.** `common/` is a clean layer 0, and the parser's engine, grammar, and actions split is faithful.
- **The type checker.** Its dispatch through `checker.T` is easy to follow, and its families import each other in a
  shallow, acyclic graph.
- **The backends.** The JIT reuses the arm64 backend almost entirely, and the allocator never names a register.
- **Decisions made once.** `staticdata` describes each descriptor once for every printer.

The problems are mostly at the seams between areas. They come down to a few habits, each repeated in several places.

## 1. A Silent Miscompile Found by the Review

**`ir/represent`'s recursion guards leak when planning raises.**

- **The guards.** `planning` and `adapting` (`represent.mod.quest:304-305`) are module-global sets. `plan` inserts a
  key for a pair of shapes, calls `planInner`, and deletes the key afterwards (`:387-389`, `:435-443`).
- **The leak.** A `rejectedConversion` or `unsupportedConversion` raised underneath skips the delete. `representUnit`
  clears only `typeVarsMemo` (`:1504`).
- **The effect.** A later plan of the same pair finds the key and takes it for a recursive component being planned,
  which needs no conversion. A conversion with no layout gets the key `…,-`, which never changes, so the same pair
  repeats its key.

It shows in any long-lived process. Reproduced in `./quest -i` with the module of
`tests/errors/run/rejectedlayout.mod.quest`:

```
>>  import layouts: Layouts
layouts.mod.quest:4:26: error: Compiled code cannot convert a value of type 'layouts.T(Bool)' ... copy mutable data
>>  import layouts: Layouts
>>  layouts.first(:Bool layouts.bools)
==  true : Bool
```

The second import compiles the module without the conversion, which the first import rightly rejected. Importing once
and then using the module correctly reports `Undefined variable 'layouts'`.

**The fix:**

- clear both sets at the start of `representUnit`, or move them into the `Representer`;
- delete each key on the way out of a raise as well;
- add a REPL test that imports the module twice.

The fix is about 15 lines, in the self-hosted compiler only. The JIT, the REPL, and the Jupyter kernel are exposed;
batch builds are not.

Other possible bugs the reviewers flagged but did not reproduce are listed in §5.

## 2. Habits Across the Tree

Each subsection is a pattern found in several areas, with its instances and one proposal for all of them. They are
ranked by how much they cost a reader or a maintainer today.

### 2.1. The pipeline is written out by each of its callers

No single function is "compile this program through the pipeline". Each entry point writes out its own copy of the
sequence, and the copies have drifted.

**The front end** (tokenize, check the bag, parse, desugar, `elaborateProgram`, then copy errors and warnings into a
bag):

- It is written out in `driver/main.quest:1100-1181`, `driver/repl.mod.quest:180-200` and
  `lsp/analysis.mod.quest:173-305`.
- "Tokenize, check, parse" alone appears at 12 sites, each a little different:
  - `modules/units` adds an error with an empty message just to stop;
  - `modules/elaboration:252` and `modules/paths:130` parse even when tokenizing failed.

**The program's environment** (current and program directory, source file, `importsThroughInterfaces`, build directory, include
paths):

- It is set up in `main.quest:1112-1149`, `build/engine.mod.quest:393-410` and `lsp/analysis.mod.quest:95-108`.
- The three already differ: only main installs `resolver.variantOf` or adds `runtime/` for wasm, and the language
  server adds no lib paths.

**The IR passes:**

- Their order is written in `ir/pipeline.runPasses` and again in `driver/main.quest:316-350`'s `lowered`, its own
  array of the five steps.
- The sequence of lower, `openImports` or merge, verify, `setReferencesAlike`, then passes appears again in
  `codegen/backend.codeOfProgram` and `codeOfModuleFile`, and in both JIT targets (`jit/target.mod.quest:319-346`,
  `jit/target.wasm.mod.quest:144-160`).
- The JIT also repeats `codegen/native.unitCode`'s SSA build-and-lower.

**The SSA policy** for each backend is chosen in three places: `codegen/native:28-35`, `driver/ssaphases:19` and
`jit/target:326`. Under `--backend ssac`, the SSA dumps show arm64's passes.

**The program to an object** takes two routes:

- `engine.compileMainUnit` (plain `quest compile`) and the driver's `compiled` (with `--print-result`, `--echo`,
  stdin, whole-program, and wasm).
- They differ in which IR errors become diagnostics and in which caches the main object.
- The split is inherited from the bootstrap (`compile_main_unit` and `CodegenCPhase`), but no reader can tell which
  route built a given binary.

**The driver's own mode** is decided in four places:

- the top of `options` (`compileMode`, `fmtMode`, `lspMode`, plus scattered backend changes);
- main's top-level lets (`compiledPipeline`, `pipeline`);
- an 8-clause conjunction that sends a program to `buildProgram` or `run()` (`main.quest:1248-1251`);
- the elsif chain in `run()`.

About 13 terminal paths come out of these. A worker's arguments run through every top-level let before main reaches
the worker's branch.

**Proposal:**

- `options` computes one `Command` option (fmt, lsp, worker, unit file, build, and the program's routes), and main
  ends in one exhaustive `case`.
- `typecheck` (or a small `modules/program`) exports `checkProgram(sm bag e onPhase)`, and `env` exports one
  program-environment constructor; the driver, the REPL, and the language server call both.
- `syntax/parser` exports `parseSource(sm bag)`, which stops on a tokenizer error with a real diagnostic.
- `ir/pipeline` exports a table of the stages, `runThrough(unit stage onStage)`, and a `prepare` for opening or
  merging, the core check, and the backend's settings. The driver, `codegen/backend`, and the JIT call it.
- `codegen/native.policyFor(backend)` and `native.loweredSSA` are shared by `native`, `ssaphases`, and the JIT.

**Cost and value:**

- Roughly 500 lines over a dozen files, all of them new functions rather than module moves, so the bootstrap need not
  mirror any of it.
- No golden or ABI changes; every route is golden-tested.
- The value is high: this is where every new option, phase, front-end rule, or backend has to be threaded today.

### 2.2. There is no single convention for internal errors

"This is a compiler bug" is said a dozen ways. They are caught by lists that have drifted, and some of them by
nothing.

**The IR's exceptions:**

- They are `lower.loweringError`, `verify.verifyError`, `closure.capturesMutable`, `represent.unsupportedConversion`,
  `represent.rejectedConversion`, and `describe.unsupportedDescriptor`; a seventh, `nodes.noSuchPrim`, is not
  exported, so it cannot be caught by name.
- They are caught in five hand-copied lists: `driver/main.quest:360-374` (8 entries),
  `modules/artifacts/modulecompiler.mod.quest:270-278` (5), `jit/target` (4), `jit/target.wasm` (4), and
  `jit/session`.
- `engine.compileMainUnit` catches none of them.
- `moduleCompiler` misses `loweringError` and `verifyError`, so a `-j` worker reports either as a crash rather than a
  located error.
- Every handler for `rejectedConversion` outside `represent` is dead, since `represent.body` turns it into a
  `compilerError` (`:1476`).

**The SSA's checks:**

- `barriers.barrierError` is raised beside `verify.checkUnit` in `ssa/pipeline.run`, but nothing catches it, so a
  missed barrier escapes as a bare exception.
- The lookup tables' `unknown` exceptions are caught nowhere.
- `native` and `ssaphases` catch different lists.

**The type checker and `common`:**

- `types/` raises four uncaught exceptions of its own (`model.internalError`, `symbols.redefined`,
  `reduce.notAnOption`, `canonical.canonicalError`). These skip `checker.attempt`, so the error has neither an offset
  nor the `internal:` prefix that the header of `typecheck.mod.quest` promises.
- The type checker defines six identical local `internal` helpers.
- `diagnostics.fail("internal: …")` makes a recoverable error, but [diagnostics.md](diagnostics.md) §4.5 says an
  internal error is fatal. §3 names `diagbag.addFatal`, which nothing calls.

**The interpreters:**

- `irinterp` uses `fail` 22 times and `model.internalError` 23 times for the same kind of malformed IR.
- It silently coerces in other places: a non-Int index becomes `~1`, so a compiler bug looks like the program raising
  `arrayOp.error`.
- `not` of a non-Bool is `true` in `irinterp` (`:808`) and `false` in `treewalk` (`:274`).
- `model.fieldMissing` is never caught.

**wasm:** its `fail(): Ok` is followed by dummy values, which read as recovery (`wasm/codegen.mod.quest:189-191`,
`:1012-1015`).

**Proposal:**

- **`common`.** Add one `diagnostics.internal(A::TYPE what offset): A` with the prefix, decide whether it is fatal, and
  make §3 and §4.5 say so.
- **The IR.** Give it one internal-error exception (`nodes.irError`, raised by `nodes.internal`), and keep
  `rejectedConversion` private to `represent`. Then `ir/pipeline` can export one combinator that catches the IR's
  failures, and each catch site names only its backend's own.
- **The SSA.** Give it the same: `barriers` and the tables raise `verifyError` or one SSA error, caught by one helper
  that `native`, `ssaphases`, and the JIT share.
- **The interpreters.** State `irinterp`'s rule in its header: malformed IR raises `fail`, and only the program's own
  errors raise `model.*`. Replace the silent coercions with failures.

**Cost and value:**

- About 150 lines, plus an ABI bump for the IR interfaces.
- The bootstrap needs nothing, since its errors are classes.
- The value is high: the oracles (`verify`, the IR interpreter, the barrier check) exist to find compiler bugs, and
  these paths hide or garble what they find.

### 2.3. Protocols are carried in strings

Several contracts between modules are strings that must match by hand. A typo is never a compile error, and `case`
cannot check that every case is handled, which §8 counts on elsewhere.

**Token kinds in the formatter and the parser's error recovery:**

- `format/format`, `format/structure` and `syntax/parser/unclosed` turn each `TokenKind` into its printed name and
  compare strings.
- There are 39 such literals in `format.mod` and 33 in `structure.mod`, for example
  `isKind(st j "KW_END")`.
- The bracket classes (opening, closing, matching pair) are written out about six times, and again in `unclosed`.
- Separately, every keyword is spelled in about seven lists:
  - `TokenKind`;
  - `tokenKindName`, with 96 arms;
  - `isKeyword`;
  - the tokenizer's `initKeywords` and `spellingTable`;
  - the grammar's 90 `let kwX` lines;
  - `expected` and `unclosed`.

**Diagnostic text read as a protocol:**

- The REPL decides whether to read a continuation line by searching an error message for `"Unclosed comment"` and
  `"Unterminated string"` (`driver/repl.mod.quest:54-55`).
- The parser's `stoppedAt` scans labels for `"parsing stopped here"`, and the language server depends on it.
- Rewording a message, as an error-message pass would, breaks both without a failing test.
- `Diagnostic` has a `code` field with `setCode`, which nothing in `questlang/` uses.

**C type spellings used as representations:**

- `layout`'s cached answer, and the one that `slotOf` and `representationBytes` work from, is a C type spelling. The
  `Representation` enum exists but is not cached.
- The SSA builder decides `is` with `vals.eq(layout.representation(...) "QVariantVal")`.
- `ir/represent` decides conversions by `eq(cs "QVal")` (at 8 sites) and by whether a spelling ends in `*`.
- `genericLayout` decides ABI agreement by membership in lists of C names.
- All this contradicts [ir.md](ir.md) §2.7 ("knows nothing of C syntax").
- Eight functions come in Type and Shape twins, and "representation" means a string in some and the enum in others.

**Other kinds kept as strings:**

- descriptor kinds: `staticdata.DescriptorForm.kind`, one of 12 strings, which wasm parses back in `kindOf`;
- `genericLayout`'s places (`"slot"`, `"register"`, `"cell"`);
- `model.Param.mode` (`"value"`, `"var"`, `"out"`), compared at about 30 sites;
- backend names in `codegen/choice`, `native`, `backend`, and the driver;
- wasm's external tables, which encode signatures as strings like `"ennenn"` and arities as `"2"`;
- `repr/externals.functions`, an `Array(Array(String))` read by column index in three backends.

**Linkage names spelled by hand:**

- `"qv_mod_" <> … <> "_init"` and `_initialized` are written out about 20 times, in the C printer, `ssa/build/unit`,
  and wasm.
- `ssa/passes/constants` recognizes initializers by prefix and suffix.
- The phrase units' `"qj_"`, `"_entry"`, and `"_echo"` are spelled in `ir/lower`, `ssa/build/unit`, `jit/target`, and
  `jit/session`.
- `"qr_frames"` is spelled in `ssa/build/unit`, `codegen/arm64/codegen`, and `jit/loader`.
- `repr/symbols` already has `moduleRecordIdent` and `fingerprintIdent` for the same purpose.

**Proposal:**

- **Tokens.** Test `TokenKind`s with `?tag`. Keep one table in `syntax/tokens` (kind, name, spelling, class) from which
  the others are derived, and give it the bracket and declaration classes.
- **Diagnostics.** Set codes on the diagnostics that callers act on (`incomplete`, and the parse's stopping offset),
  and read the codes.
- **Representations.** Make `Representation` the cached, primary answer. Rename the string functions to `cType`,
  `slotCType`, and so on, derived from the enum, and add one `layout.words(rep)` table (finding 2.4).
- **Kinds.** Make options of descriptor kinds, places, parameter modes, and backends.
- **Names.** Put the linkage names in `repr/symbols` (`moduleInitIdent`, `phraseEntryIdent`, `framesIdent`,
  `isModuleInitSymbol`, …).
- **Externals.** Give `repr/externals` a lookup function and a tuple type for its entries.

**Cost and value:**

- These are separable. Tokens, diagnostic codes, and linkage names are each 40–300 lines, in the self-hosted compiler
  only, with no output change.
- Representations are about 150 lines across eight modules. `layout` is shared with the bootstrap, but only its
  internals change, so mirroring is optional.
- The value is high for tokens, diagnostic codes, and representations; medium for the rest.

### 2.4. The backends work out the same facts about shapes for themselves

The large decisions (representation, slots, descriptors, object layouts) are made once in `repr/`. The small ones are
worked out again by each backend, and the copies disagree on what to do when something is missing.

- **The index of a variant's or option's case.**
  - `codegen/c/printer.mod.quest:128` takes the first match and returns 0, as its comment says, when the case is
    missing.
  - `ssa/build/representation.mod.quest:37` takes the last match and also returns 0.
  - `wasm/codegen.mod.quest:1569` raises.
  - `staticdata:873` computes it inline.
  - A missing case is a compiler bug, and two of the three copies would turn it into tag 0.
- **Copies of functions the printer already imports.** `printer:99` copies `layout.heldShape` and `printer:119` copies
  `shapes.isFunction`. `ssa/build/values:75` copies `layout.slotIsQVal`. `componentShape` is written three times and
  `caseShape` twice.
- **Counting a type's quantifiers and the captured descriptors.** The quantifier count is written four times (printer,
  wasm, `ssa/build/unit`, `ssa/build/values`). The captured-descriptor count, `extent fn.typeParams - own`, is written
  three times.
- **Sizes.** An object's size, `8 * {if n is 0 then 1 else n end}`, is written seven times in `ssa/build`, beside
  `layout.slotsBytes(n)`, which differs for n = 0. An option's payload offset, `8 + 8 * i`, is a literal in three
  places, beside `runtimeLayout`'s header.
- **What `is` compares.** It is decided in four places: `ir/describe:497-533`, `printer:1709-1745`,
  `ssa/build/calls:64-110`, and `wasm/codegen:2016-2060`, each testing in its own way.
- **The closure that makes each function.** It is collected line for line alike in `printer:3290-3315` and
  `ssa/build/unit:338-360`, and once more in wasm.
- **The module initialization order.** It is written five or six times:
  - in the printer, twice;
  - in `ssa/build/unit`, three times (the module initializer, the JIT phrase entry, and `main`);
  - once in wasm.
- **Function-type descriptors.** Their thunk, adapter, and invoker are still built twice, in
  `codegen/c/declarations:950-1110` and `ssa/build/adapters`. `ir/thunks` already turned the other wrappers into IR
  functions for this reason (compiler-organization.md §6).
- **SSA passes repeated in wasm.** wasm repeats the SSA's `accumulate` and `concats` as pattern matching inside its
  statement emission (`wasm/codegen:4700-4990`).

**Proposal:**

- **New functions in `repr/`:** `shapes.tagIndex` (which raises), `shapes.caseShape`, `shapes.quantified`,
  `layout.allocationBytes`, `layout.optionComponentOffset`, and `layout.words`.
- **New functions in `ir/`:** `nodes.capturedDescriptors`, `walk.closuresByFunction`, and `initOrder(unit exported)`.
- **The backends' copies:** delete them.
- **`is`:** have `describe` record its decision on the operation, so each backend only switches on it.
- **Later:** move the function-type adapters into `ir/thunks`.

**Cost and value:**

- The new functions are about 300 lines, as additions, so the bootstrap need not mirror them. Recording `is` on the
  operation changes the described-stage dumps, which are the self-hosted compiler's own.
- The adapters are about 400 lines. They are worth doing but not urgent.
- The value is high: it removes two silent fallbacks, and these are the copies most likely to drift as a fourth target
  arrives.

### 2.5. State is hidden in globals and hooks

Mutable module-global state decides what several functions do, and nothing in their signatures shows it.

- **`ir/represent`'s `planning` and `adapting`:** the bug in §1.
- **`elaboration.hooks.elaborateBinding`:**
  - `typecheck.install` and `elaborateProgram` both assign it (`typecheck.mod.quest:428`, `:467`), and
    `elaborateProgram` never restores it, so the hook keeps that program's checker.
  - The build re-installs it before every module compile (`build/engine.mod.quest:387`, `:982`;
    `build/workers.mod.quest:411`).
  - The JIT session and the language server save and restore it, and `keepMembers` too, by hand.
  - `modules/elaboration.int.quest:12` and `:30` say that `typecheck.newChecker` sets the hooks, which it does not.
- **`shapes.setReferencesAlike`:** a flag in `repr/shapes` that shapes never reads. Only `ir/represent:450` reads it.
  Four callers each set it before `runPasses`: `codegen/backend` twice, and the two JIT targets.
- **Other globals:**
  - `selects.converted` passes a list of functions from `selectUnit` to `straightenUnit` across the whole pipeline.
  - `opened.lastSources` passes a unit's source files to `build/engine:467`, though `Unit` has a `mergedSources` field.
  - `diagnostics.sources` is a registry, filled from seven sites, that overrides the source map passed to `format`.
  - `typedAst`'s recorder is used only by the language server.
- **The process-wide compilation switches** (`inlined.setInlined`, `setTransparentAbstractTypes`,
  `setRegisteringApart`, `files.setWorkerTag`) are set from several places, and no list says who owns each.

**Proposal:**

- Fix §1 first.
- Have `elaborateProgram` restore the hook.
- Make `setReferencesAlike` a field of an argument to the IR passes, as `ssa.Policy` is for the SSA.
- Put the opened sources on the `Unit`.
- Let `straighten` test every function, as it already does for itself.
- Document the remaining switches in one place.

**Cost and value:**

- Each is 15–60 lines. Only the hook's alternative, moving `elaborateBinding` onto `env.T`, touches the bootstrap.
- The value is medium-high: these are the cases where reading a function does not tell you what it does.

### 2.6. Small helpers are re-implemented beside the shared ones

`common/` and `ssa/nodes` have helpers that their callers bypass:

- **Python's number repr.** `pyRepr.number` is copied in `ir/printer`, `values/model`, `typechecker/typedastprint`, and
  `repr/syntax`. `pyRepr.ints` does not use `number`, so a negative integer would print with `~` (§5).
- **Membership tests.** `strings.isOneOf` is re-implemented at least nine times. A `contains` over `Array(Int)` is
  written three times. 32 modules define `let eq(a b) = stringOp.equal(a b)`.
- **`common/files`.** It re-implements about 70 lines of `util/path`, which it already imports, and differs at the
  edges: `baseName("/")` is `""` against `"/"`.
- **SSA helpers.** These are copied:
  - `wordOf`;
  - the jump terminator (seven times);
  - the loop-header test;
  - `dropDeadParams`;
  - splitting a block in two (in `unproxies`, `allocations`, and `interrupts`).
  `allocations` also defines seven instruction builders that `ssa/nodes` already provides.
- **`CompilerError`.** It is built field by field 14 times. Adding a field touches 11 tuple literals.
- **The typechecker's prelude.** Each family module begins by re-declaring the same six helpers (nine copies of
  `expr` and `internal`).

**Proposal:** move each to its shared home and delete the copies. That is about 300 lines in total, with no output
change. The value is medium as a batch.

## 3. Findings Within Each Area

These are the findings not covered by §2, by area, most valuable first.

### 3.1. Types and the type checker

- **The loop depth and the environment are each held twice.** Every family function takes
  `(c: checker.T … e: env.T loopDepth: Int)`. There are 280 mentions of `loopDepth` in `typechecker/`.
  - `c.loopDepth` and the argument are kept in step by hand at every loop.
  - Every `e` passed is `c.env`.
  - `checker.isGlobalVar` reads `c.env` where everything else reads `e`.

  Make `c.loopDepth` and `c.env` the only copies, first with an assertion under `tools/check` that they agree. That is
  about 450 mechanical lines; the bootstrap's signatures need not change. Value: high.
- **`checker.T`'s dispatch is in mutable fields.** `checkHook` and `synthHook` are filled after construction, and a
  checker made by `checker.new` directly fails at its first subexpression. Pass them to `checker.new`, and drop
  `typecheck`'s unused `newChecker`, `checkExpr`, and `synthExpr` exports.
- **`tuples.tupleScope` is 405 lines.** It takes eleven parameters and has fourteen mutable locals. Lift its four
  per-component cases into functions over a local state tuple.
- **`env.T` mixes too much.** It holds the scope stack alongside the build options (`importsThroughInterfaces` is read in 7 modules
  and `buildDir` in 10), the loader's session state, and REPL slots. Group the options as `e.options`, as the bootstrap
  does.
- **The name `Env` means three things.** `env.T`, `kinds.Env`, and `subtyping.Env` are different, and
  `env.lookupOf(e)` ignores its argument (24 sites). Rename the types, and drop the argument.
- **The families match each expression's form twice.** The dispatch has already matched it, and each family adds a
  fallback that cannot run (29 of them), because `ast.ExprForm`'s payloads are anonymous. This is cross-area through
  `syntax/ast`, and low priority.
- **Recovery and poisoning are written twice,** in `typecheck` and `bindings`, with different rules. `poison` covers
  types and kinds, but its name suggests every symbol.
- **`kinds.resolveOptionBound` is a second copy of `resolveBound`.** The comment explains how they differ. Merge them
  only together with the bootstrap's `kinds.py`.

### 3.2. Modules, build, and driver

- **`main.compiled` is 334 lines.** It holds a wasm bundler, a parser of wasm binaries' import sections, a topological
  sort, and the wasmtime and node launchers (`main.quest:487-905`). Move these to a self-hosted-only `wasm/bundle`;
  `compiled` becomes a dispatch of about 40 lines. Value: high.
- **The engine's builder chain is written at three sites, which differ.** The wasm engine omits `reportingInferable`.
  `engine.T.compiler` and `extraCFlags`, along with the workers' `--cc` and `--cflag`, are never given a value. Use one
  `engine.Settings` record and delete the dead fields.
- **`modules/artifacts/moduleCompiler` belongs to the build layer.** It imports `build/`, and `build/` imports it, so
  §5's layers are not acyclic as written. Its main-unit and module-unit code-emitting tails are near copies of the
  engine's. Move it to `build/`, mirrored in the bootstrap, and share the tail.
- **"C" names that mean any backend.** These include `compiledPipeline`, `backendPhases`, `codeOfUnit`, `codeOfProgram`, the field `c`
  that holds wasm bytes, `importsThroughInterfaces`, and `buildExecutable`. Rename the identifiers, not the golden-facing phase names.
- **The REPL, the JIT run, and the kernel are written as near copies.** Factor out `programArgs`, `importerName`,
  `report(bag sm)`, and one function that continues interactively.
- **`modules/graph` does three jobs.** It resolves imports, holds the unit graph, and lays out artifacts in a build
  directory. Split it in three, mirrored in the bootstrap. Value: medium-low.
- **Smaller items:**
  - Two modules are named `Headers`, and `build/headers` imports the other under its own name.
  - The kernel and the language server scan names with identical code.
  - Two `unitStaleness` functions have different contracts.
  - `.qi` import entries are written and parsed without a shared format.

### 3.3. The IR

- **ir.md contradicts itself on types.** §1, §2.6, and the §9 "Core" row say types are lowered shapes. §4.1, the
  README, and instructions.md §4 say, as the code does, that they are kept as written. Fix §1, §2.6, and §9. Value:
  medium-high, since this is the first page a newcomer reads.
- **`represent`'s numbered rule list does not cover every branch.** It omits the two shortcuts before rule 1, the `QVal`
  guards on rules 3 and 4, rule 9's "equal option types spelled otherwise", and the held-at-bound tuple case that
  rule 10 says cannot happen. §8 relies on this list being complete.
- **`represent.call` passes its result back through a mutable field.** It reports a generic call's instantiation
  through `genericResults`, which `statement` resets and reads. Return it instead.
- **The type a callee is taken at is computed four times,** in `represent` twice, in `describe`, and in `verify`.
  `memberType` is written twice. The variable-to-member-name helpers in `specialize` and `simplify` have drifted.
- **`simplify.body` is a 219-line loop.** It controls the loop three ways. Give each statement kind a function that
  returns keep, drop, splice, or restart.
- **`verify`'s two stage checks are long `let`s of closures.** They are 216 and 301 lines. Give them a checker tuple,
  as `verifycore` has.
- **`describe.unitTypes`' offset-table clause is dead in both compilers.** It runs before `staticData` is attached.
  Decide whether those types need declaring, then delete the clause or move it.
- **Names:**
  - `inline.specialize` is a different thing from the `specialize` pass;
  - `contify.Unit` shadows `nodes.Unit`;
  - `clone.var1` and `clone.label1` say nothing;
  - `simplify.noVariable` is a sentinel where an option would serve.

### 3.4. repr and SSA construction

- **`ssa/build/values` is a grab bag.** Its interface has about 110 exports doing seven jobs. Split the representation
  as SSA words into `ssa/build/parts`. `ssa/build/representation` is also misnamed: it holds access and control flow.
- **`ssa/scalars` is a pass outside `passes/`, and it imports from `passes/`.** This inverts the layering the READMEs
  describe. Move it.
- **`layout`'s byte functions take a `Type` and return 8 for any other form.** Callers must remember to pass
  `shape.structure`. Take a `Shape`, and raise on the wrong kind.
- **Long functions:**
  - `ssa/verify.problemsIn` is 364 lines;
  - `ssa/build/unit.buildUnit` is 263, and its init sequence is written three times;
  - `ssa/build/control.statement` is 281.

### 3.5. SSA passes, machine, and arm64

- **The pass list hides steps from `QUEST_SKIP_PASSES` and the `ssa_NAME` dumps.** §8 counts bisecting with
  `QUEST_SKIP_PASSES` as a strength, and these steps weaken it:
  - `tailJumps` also runs `loops.loopTailCalls` (`ssa/pipeline:57`);
  - `loops` runs `promote`, `valueNumbers` up to three times, and `conditions`, and `conditions` runs `valueNumbers`
    again, so skipping `valueNumbers` still numbers values;
  - `straighten` and `interrupts` run after the list, and `unproxies` cannot be skipped.

  Name `loopTailCalls` and `straighten` as passes, make the nested reruns respect skipping, and list the skip-only
  names. Value: high.
- **`ssa/passes/loops` is four passes in one module.** At 1,418 lines it holds self tail calls, module cells, hoisting
  and rotation, and bounds checks; `hoistLoop` alone is 374. Split it into modules, keeping the order, and break up
  `hoistLoop`. Value: high.
- **Facts about runtime functions are kept outside the effects table.** Passes keep lists of names:
  - `conditions.allocates`;
  - `constants.registrations`;
  - `proxyFold.isBarrier`;
  - `barriers`;
  - `loops.calm`, which `loops` imports `conditions` to reach.

  Add `fresh` and `registration` columns to `runtimeFunctions`, and delete the lists.
- **arm64 restates the callee-saved registers three times, unchecked.** They appear in `savedFirsts` and
  `savedSeconds`, in `callMaps`' `x19 + k` numbering, and in `frameMaps`' decoding. A change to
  `description.calleeSaved` would break the collector's frame maps without any error. Derive all three from the
  description, and name the literal 8s and 16s. Assembly stays byte-identical, and §7's "frames left whole" is
  respected.
- **Target-independent code sits in `arm64/codegen`.** Block layout, cold-block marking, jump threading, and
  `definedSymbols` live there, yet `codegen/machine/README.md` and arm64.md:716 say a second target would write only
  selection, a printer, and a description. At least fix the docs.
- **Long functions:**
  - `select.select` is 272 lines, with four analyses after its sweep;
  - `codegen.machineCode` is 174;
  - `regalloc.allocateWith` is about 400, and `coalesceWith` about 435.

  Extract the analyses and phases. Measure the allocator's compile time when you do.
- **`arm64/codegen` declares two types named `Compiled`, and the second shadows the first.** `machine/target` imports
  `ssa/nodes` only for `classOfType`, which only `select` uses.

### 3.6. The C backend and wasm

- **`wasm/codegen.unitModule` is 686 lines.** Its import scan predicts what the emitters will later call:
  - 41 insert-if-absent blocks for 45 `runtimeUnitCall` sites;
  - a missed import shows up only at run time;
  - `initRuntime`'s test for calling `print.init` differs from the import's.

  Give each external one declarative entry that both read, and split the function into its six phases. Value: high.
- **`externalCall` and `intrinsic` dispatch through 162 `named("…")` string comparisons.** Move the stateless tables
  into a `wasm/externals` module, with typed rows.
- **wasm's descriptor kinds and part flags match `runtime/wasm/core` only by position.** The companion `_abstract`
  descriptor is invented separately in `declarations`, `ssa/statics`, and wasm. Export the constants, and have
  `staticdata` describe the companion.
- **wasm has four notions of `ValType` equality.** `codegen`'s `sameType` treats every reference type as the same,
  which is deliberate for exports and tail calls, but its name hides that. Rename it `sameClass`, and give `model`
  exact equality and a key.
- **`declarations.Emitter` leaks.** `emittedDescriptorTags` is written and never read. Two things are named
  `definedStructs`. The printer shuttles state back into the emitter.
- **Interface headers emit typedefs that nothing consumes.** These are `quest_type_`, `quest_rec_`, and `quest_sig_`.
  The `quest_rec_` structs spell field names raw (§5).
- **The printer finds barrier call sites by scanning its own C text, with a test that differs from the bootstrap's
  regex.** It errs toward extra barriers. Make the identifier test positive.
- **`ssac` contains a 68-line liveness analysis.** Move it to `ssa/cfg`.

### 3.7. Interpreters, values, the language server, and the JIT

- **The two interpreters re-implement the same operations on values.** These include:
  - substituting type arguments;
  - instantiating a closure;
  - following refs, three times counting the dynamic writer;
  - the index check followed by a raise;
  - building a raised `RunError`;
  - inspect's match;
  - reading and storing fields.

  They also have two rules for whether applying a value to types runs it. Put the shared operations in
  `interpreter/primitives` and `values/model`, mirrored in the bootstrap. Value: high.
- **`treewalk.evalIn` is one 515-line case.** Lift its larger arms (locations, assignment, `for`, `try`, `inspect`)
  into members of its `rec` group.
- **The REPL's echo text is built twice.** `interpreter/formatting` builds `let var x:T = …`, `Let T::K = U`,
  `DEF K = …` and `exception e`, and `ir/lower` builds them again; the two must agree byte for byte. The language
  server imports the interpreter only to get `valueDeclaration`. Move these to `types/`, mirrored in the bootstrap.
- **The JIT's debug object has drifted from `codegen/arm64/asm`'s DWARF.**
  - The producer is `questlang` in one and `quest` in the other.
  - The attributes are in a different order.
  - `high_pc` is `data4` in one and `data8` in the other.
  - Only the debug object gives `frame_base`.
  - Its interface still says it matches the assembler.

  Share one table of constants and abbreviations.
- **The JIT loader re-derives instruction fields that the encoder knew.** These are adrp's immediate and a page
  offset's access width.
- **`irinterp` has a second root frame.** `Interpreter.root` is used only for operator builtins, beside `renv`, which is
  already a root. `IrClosure.env` is an array of captures, while `model.Closure.env` is a frame.
- **The language server:**
  - the same constant names (`classKind`, `functionKind`, …) have different values in `navigation` and `outline`,
    because LSP has two kind enumerations;
  - its catch-alls drop the exception's name, which `lib/raised` cannot report yet;
  - it rebuilds the line index on every request.

## 4. Two Batches of Small Changes

### 4.1. Dead exports and dead code

Every area has exports that nothing outside the module uses, and some that nothing uses at all. Each was checked by
grep over `questlang/`, `tests/`, and `tools/`.

The ones used nowhere:

- **types:**
  - `model.resetMetaCounter`, `tupleElements`, `isSolved`, `unsolvedMetasInKind`;
  - `subtyping.clearSubtypeCache`, `env.popScope`, `kinds.resolveVariantBound`, `dump.formatKindCompact`,
    `symbols.symbolName`.

  `model.isSolved` is also confused with a local `isSolved` in `application`, which behaves differently.
- **common and syntax:**
  - `diagbag.addWarning`, `addFatal`, `getAll`;
  - `diagnostics.info`, `make`, `code`, `setCode`;
  - `tokenizer.peekToken`, with its `peeked` field;
  - `ast.exprSelect`, `typeTuple`, `declTypeBinding`;
  - `grammar.T.phrase` and `.signature`.

  `diagbag.addStoppingError` is typed `Ok` but always raises, so its callers raise a second, unreachable time.
- **modules and build:**
  - six of `build/compilerrunner`'s eleven exports;
  - four of `build/headers`';
  - `graph.find`, `interfaceImportPaths`, `paths.canonicalRoots`, `fingerprint.ofQi`;
  - three exports of `interfacecompiler`;
  - `manifest.isManifestStale`, `elaboration.importInterface`;
  - three prompts in `driver/repl`;
  - five unused imports in `driver/main.quest`.
- **ir:** `nodes.sameModuleRef`, `opened.openedModules`, `walk.replaceVarsInOp`, `walk.replaceAtomsInOp`,
  `printer.formatBody`.
- **repr and ssa:**
  - `shapes.isScalar`, `shapesReachable`, `descriptors.funDescriptorTag`, `nodes.defaultPolicy`, `nodes.wordsBytes`;
  - `staticdata.registerAlias`, which is never called in either compiler, so `RecordNaming.aliasByShape` is always
    empty and the comment describing aliases describes nothing;
  - dead locals in `select` and `codegen`, and `Let Datum` in `codegen/backend`.
- **interpreters and values:**
  - `treewalk.define`, `evalExpr`, `evalScopedBinding`, `evalProgramPhrases`;
  - `model.tupleOf`, `realString`, `fieldMissing`;
  - `ExceptionValue.payload`, which is always `none`, in both compilers.

About as many more are used only inside their own module; un-export those. Deleting unreferenced code needs no
`tools/check`, but the `.qi` files in `tests/abi/inputs` copy these interfaces and must be refreshed.

### 4.2. Documents that disagree with the code

**compiler-organization.md:**

- **§2 (the layout):**
  - it omits the `format/` and `lsp/` directories;
  - it omits `parser/expected` and `unclosed`, `common/jsoncache` and `overlays`, and `jit/target` with its wasm and
    none variants;
  - it lists `common/json`, which is gone;
  - its passes listing omits `concats`, `nanChecks`, `conditions`, and `loops`.
- **§5 (the layers):**
  - it places `types/reduce` too high: `typechecker/bindings` imports it;
  - it names neither `format` nor `lsp`;
  - it orders `modules/artifacts` and `build/` as if acyclic.
- **§6:** it does not record that `repr/staticdata`, `runtimeLayout`, and `externals` are the self-hosted compiler's
  alone.

**Other design documents:**

- **ir.md:** the shapes contradiction of §3.3.
- **diagnostics.md:** §3 and §4.5 (§2.2).
- **ssa.md:**
  - §4.1's `tailJumps` bullet omits `loopTailCalls`, which appears nowhere in the documents;
  - it cites `calls.libraryOperation`, which is now `externalOperation`;
  - it says unproxying is a test of the proxy bit, when it is `opUnproxy`.
- **arm64.md:**
  - `Lowering` makes no jump;
  - "three pseudo-instructions" lists two;
  - the claim about a second target (§3.5).
- **codegen-c.md:** §1 says the printer makes no representation decisions, but its `fusedTuples` does; it also names
  the bootstrap's homes for `descriptor_form`.
- **c-representation.md:**
  - it cites `ir/closure_convert.py`;
  - it says abstract types erase uniformly, although bounded ones do not;
  - it names only the bootstrap's functions.
- **syntax.md:** it says the parser has four modules; it has six.
- **interpreter.md:**
  - its title still says "Bootstrap";
  - it lists `is` and `isnot` among the root frame's operators;
  - it describes references as cells only.

**READMEs and interface comments:**

- **READMEs:**
  - `common/` links a `json.int.quest` that no longer exists;
  - `syntax/parser/` says the REPL relies on the farthest position;
  - `ssa/passes/` describes promotion of slots in functions with handlers wrongly, and files `interrupts` under the
    wrong heading;
  - `codegen/arm64/` names the wrong callers, and says only three modules case on `Op`;
  - `typechecker/` names the wrong callers;
  - `jit/`, `interpreter/`, and `driver/` omit modules and commands.
- **Interface and module comments:**
  - `wasm/codegen` says it reads the represented IR, but it reads the described IR;
  - `clone.int` explains why it skips later passes' fields, but the reason is not true for `thunks`;
  - `thunks.int` lists three of the pass's five jobs;
  - `ir/pipeline`'s comment for `runPasses` sits above `simplified`, and `main.quest:478-486` has a comment above the
    wrong function;
  - `debugobject.int` says its DWARF matches the assembler's (§3.7);
  - the family lists in `checker.int` and `typecheck.mod` leave out `tuples`.

All of this is Markdown or comments, so none of it needs a test run.

## 5. Possible Bugs Not Reproduced

These turned up while reading. Each needs a test before anyone believes it.

- **`build/headers`:** the `quest_rec_` struct of an interface header spells record fields raw. A manifest record with
  a field named like a C keyword (`long`, `default`) should produce a header that does not compile. The other structs
  spell fields `qf_` + `memberIdent`.
- **`common/pyrepr`:** `pyRepr.ints` prints a negative integer with `~`, unlike Python. Its callers print symbol ids,
  which the high-bit reserved scheme may make negative.
- **The wasm JIT:** `jit/target.wasm:70` calls `wasm.raisedName`, which uses `print.show`. `initRuntime` calls
  `print.init` only for echoes, phrases, or capture. Check whether such a unit can call `show` before `print` is
  initialized.
- **The IR exception lists:** `moduleCompiler` misses `loweringError` and `verifyError`, so under `QUEST_CHECK_IR=1` a
  `-j` worker reports a crash rather than a located error (§2.2).

## 6. An Order of Work

Fix §1 first. It is a miscompile, and the policy is to fix those promptly.

After that, ranked by value for cost, mostly independent of one another, and each a commit or a short plan:

1. **The batches.** The documents (§4.2) and the dead exports (§4.1), which are cheap, and the documents are the map
   a newcomer reads first.
2. **The internal-error convention (§2.2).** It removes drift that already hides compiler bugs.
3. **The pipeline's entry points (§2.1), starting with `ir/pipeline` and the front end.** Then the driver's `Command`
   and moving wasm out of `main.compiled` (§3.2).
4. **The shape facts that backends work out for themselves (§2.4).** It removes two silent tag-0 fallbacks.
5. **Strings as protocols (§2.3).** Diagnostic codes and linkage names first (small), then tokens, then
   representations.
6. **The skippable SSA passes and the split of `loops` (§3.5).**
7. **The type checker's duplicated state (§3.1).**
8. **The interpreters' shared operations (§3.7).** These need the bootstrap mirrored.
9. **The long functions** (`unitModule`, `tupleScope`, `evalIn`, `simplify.body`, `hoistLoop`, the allocator), each
   when its module is next changed for another reason.

Some proposals here touch areas shared with the bootstrap; each says whether the bootstrap has to mirror it. Most are
new functions or changes inside a module, which compiler-organization.md §7's parallel-trees rule does not require
the bootstrap to follow. The exceptions are the module moves: `moduleCompiler` to `build/`, splitting `modules/graph`,
the interpreters' shared operations, and the interactive notation.
