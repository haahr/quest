# A Plan for the Self-Hosted Review (2026-11-27)

This plan carries out [self-hosted-review.md](self-hosted-review.md) §6, step by step. The review gives each finding's
evidence and proposal; this plan says what each step changes, in which commits, and how each is checked. The review's
§1 miscompile is already fixed (6e01e770).

## 0. Decisions and Rules

The user decided:

- **An internal compiler error is fatal.** One `diagnostics.internal` adds a fatal error with the `internal:` prefix,
  as diagnostics.md §4.5 already says.
- **The module moves are made, with the bootstrap mirrored in the same step.** These are `moduleCompiler` into
  `build/`, the split of `modules/graph`, the interpreters' shared operations, and the REPL's echo text in `types/`.
- **The long functions are all split in this plan** (step 9), not only when next touched.
- **Nothing is pushed.** Commits stay local; the plan ends "ready to push".

How the work is checked:

- **Each commit builds `./quest`** (which rebuilds stage 1 and stage 2 when `questlang/` changes) and runs
  `./quest fmt --check` on the files it touched.
- **A refactoring meant to change no output** is confirmed by `tools/c-diff` (the test programs' C, HEAD against the
  working tree) and, when it edits `questlang/` widely, `tools/compare-codegen` (what the compiler makes of itself).
- **Targeted tests while working:** `run_tests.py --no-exclusive -k NAME`, with `--self-hosted` where the code is the
  self-hosted compiler's alone, and the unit tests of a module touched.
- **A full `tools/check` only at the end of a step that changes the compiler's behavior or interfaces**, not per
  commit: steps 2, 3, 4, 5, 6, 7, 8, and 9. Steps 1's documents and dead code need none (instructions on
  unreferenced code and Markdown); the `.qi` copies in `tests/abi/inputs` are refreshed when an interface changes.
- **ABI.** A step that changes an interface of `lib/` or the runtime bumps the ABI once, in its first commit that
  needs it.
- **The C fixed point** (bootstrap stage 1, then C) is run once, at the end of the plan; each step runs the arm64
  fixed point through `./quest`'s build.
- **A finding that turns out wrong** when the code is read closely is dropped, with a line in this plan saying why.
- **Behavior differences found on the way** (a second miscompile, a disagreement between the compilers) are fixed in
  their own commit, test first.

## 1. The Batches: Documents, Dead Code, and Helpers

- **1a. Documents** (review §4.2, the ir.md contradiction of §3.3, arm64.md's second-target claim of §3.5, the
  `represent` rule list of §3.3). One commit of Markdown and comments. No tests.
- **1b. Dead exports and dead code** (§4.1). Delete what is used nowhere; un-export what is used only inside its
  module. Both compilers where the item is shared (`ExceptionValue.payload`, `registerAlias`). `tests/abi/inputs` is a
  frozen snapshot, compiled on its own, so it needs no refresh. Checked by building `./quest` and the tests of
  `questlang/`'s modules (`run_tests.py -k questlang`). Done: 4cc8796d.
- **1c. Shared helpers** (§2.6): `pyRepr.number` used by its four copies, and `pyRepr.ints` through it (with a test
  of a negative id, §5); `strings.isOneOf` and an `Array(Int)` `contains` in `common/`;
  `common/files` through `util/path` (deciding `baseName("/")` by what its callers need); the SSA helpers (`wordOf`,
  the jump terminator, the loop-header test, `dropDeadParams`, splitting a block, `allocations`' builders) in
  `ssa/nodes` or `ssa/cfg`; one `CompilerError` constructor. (The typechecker's prelude goes with 2d.) `tools/c-diff`
  must show no change. The 32 local `let eq(a b) = stringOp.equal(a b)` one-liners stay: each reads plainly where it
  is, and a shared one would only move the import.

## 2. The Internal-Error Convention (§2.2, and §5's moduleCompiler bug)

- **2a. `common/diagnostics.internal(A::TYPE what offset): A`**, which raises a fatal `CompilerError` with the
  `internal:` prefix; diagbag's `addFatal` is used by it. diagnostics.md §3 and §4.5 describe it.
- **2b. The IR's one exception.** `nodes.irError` and `nodes.internal` replace `loweringError`, `verifyError`,
  `capturesMutable`, `unsupportedConversion`, `unsupportedDescriptor`, and the unexported `noSuchPrim`;
  `rejectedConversion` becomes private to `represent`. `ir/pipeline` exports one combinator that turns `irError` into
  a located diagnostic. The five catch lists (driver, `moduleCompiler`, both JIT targets, `jit/session`) and
  `engine.compileMainUnit` use it. A test first: a `-j` worker with `QUEST_CHECK_IR=1` meeting a verify failure must
  report a located error, not a crash (§5).
- **2c. The SSA's.** `barriers.barrierError` and the tables' `unknown` become `ssa/verify`'s error (or one SSA error),
  caught by one helper that `native`, `ssaphases`, and the JIT share.
- **2d. The type checker.** `types/`'s four exceptions are caught by `checker.attempt` (or raise through
  `diagnostics.internal`), so they get an offset and the prefix; the six `internal` helpers become one.
- **2e. The interpreters.** `irinterp` states its rule in its header (malformed IR raises `fail`; only the program's own
  errors raise `model.*`); the silent coercions (a non-Int index, `not` of a non-Bool) fail instead;
  `model.fieldMissing` is caught or deleted.
- **2f. wasm.** `fail` returns `A`, so no dummy value follows it.
- **2g. §5's other suspects**, each with a test first: the `quest_rec_` field names against C keywords, and the wasm
  JIT's `print.init`. A real bug is fixed in its own commit.

ABI bump for the IR interfaces. `tools/check` at the end.

## 3. The Pipeline's Entry Points (§2.1, §2.5, §3.2)

- **3a. `syntax/parser.parseSource(sm bag)`**, which stops on a tokenizer error with a real diagnostic; the 12 sites
  call it.
- **3b. `checkProgram(sm bag e onPhase)`** (in `typecheck` or a small `modules/program`) and one program-environment
  constructor in `env`; the driver, the REPL, and the language server call both. `elaborateProgram` restores the
  `elaborateBinding` hook (§2.5), and the interface comments say who sets it.
- **3c. `ir/pipeline`'s table of stages**, `runThrough(unit stage onStage)`, and `prepare` (opening or merging, the core
  check, the backend's settings, including `referencesAlike` as a field of the IR passes' argument, §2.5). The
  driver's `lowered`, `codegen/backend`'s two routes, and both JIT targets call them. The opened sources go on the
  `Unit`, and `straighten` tests every function rather than reading `selects.converted` (§2.5).
- **3d. `codegen/native.policyFor(backend)` and `native.loweredSSA`**, shared by `native`, `ssaphases`, and the JIT, so
  `--backend ssac` dumps its own passes.
- **3e. The driver's `Command`.** `options` computes one option, and main ends in one exhaustive `case`.
- **3f. `wasm/bundle`.** The bundler, the import-section parser, the sort, and the launchers leave `main.compiled`.
- **3g. `engine.Settings`.** One record for the builder chain's three sites; the dead fields and worker flags go.
- **3h. `moduleCompiler` into `build/`**, mirrored in the bootstrap, sharing the code-emitting tail with the engine.
- **3i. The interactive paths' shared helpers** (`programArgs`, `importerName`, `report`, continuing interactively)
  for the REPL, the JIT run, and the kernel.
- **3j. `modules/graph` in three** (imports, the unit graph, the build directory's artifacts), mirrored in the
  bootstrap.
- **3k. Names and small items:** the "C" names that mean any backend; the two `Headers`; the scanner shared by the
  kernel and the language server; the two `unitStaleness`; the `.qi` import entries' format; the remaining
  process-wide switches listed in one place (§2.5).

`tools/c-diff` after each of 3a–3d; `tools/check` at the end.

## 4. The Shape Facts and the IR's Own Findings (§2.4, §3.3)

- **4a. New functions in `repr/`:** `shapes.tagIndex` (which raises), `caseShape`, `quantified`,
  `layout.allocationBytes`, `optionComponentOffset`, `words`. The copies in the printer, `ssa/build`, wasm, and
  `staticdata` call them. A test first if any copy's tag-0 fallback is reachable.
- **4b. New functions in `ir/`:** `nodes.capturedDescriptors`, `walk.closuresByFunction`, `initOrder(unit exported)`;
  the five or six init orders and the closure collections use them.
- **4c. `is`:** `describe` records its decision on the operation, and the backends switch on it. Described-stage
  goldens change.
- **4d. The function-type adapters into `ir/thunks`**, deleting `declarations:950-1110` and `ssa/build/adapters`.
- **4e. The IR's findings (§3.3):** `represent.call` returns its instantiation; one `calleeType` for `represent`,
  `describe`, and `verify`; one `memberType`; the variable-to-member-name helper shared by `specialize` and `simplify`;
  `describe.unitTypes`' dead clause (both compilers); the names (`inline.specialize`, `contify.Unit`, `clone.var1`,
  `simplify.noVariable`).

`tools/c-diff` after 4a, 4b, 4d, 4e (no change); `tools/check` at the end.

## 5. Strings as Protocols (§2.3)

- **5a. Diagnostic codes** for what callers act on: the REPL's `incomplete` and the parse's stopping offset.
- **5b. Linkage names** in `repr/symbols` (`moduleInitIdent`, `phraseEntryIdent`, `framesIdent`, `isModuleInitSymbol`).
- **5c. Tokens:** one table in `syntax/tokens` (kind, name, spelling, class) from which the keyword lists are derived;
  the formatter and `unclosed` test kinds by tag and class.
- **5d. Representations:** `Representation` is the cached answer; the string functions become `cType`, `slotCType`,
  and so on; `represent`, the SSA builder, and `genericLayout` decide by the enum. The bootstrap's `layout` keeps its
  own internals.
- **5e. Kinds as options:** descriptor kinds, `genericLayout`'s places, `Param.mode`, backend names; `repr/externals`
  gets a typed entry and a lookup; wasm's external tables and `named("…")` dispatch become typed rows in
  `wasm/externals` (§3.6).

`tools/c-diff` after each; `tools/check` at the end.

## 6. The SSA, the Machine, and arm64 (§3.4, §3.5, §3.6's `ssac`)

- **6a. Skippable passes:** `loopTailCalls` and `straighten` named in the pass list; the nested reruns of
  `valueNumbers` and `conditions` respect `QUEST_SKIP_PASSES`; the skip-only names listed. ssa.md §4.1 says so.
- **6b. `ssa/passes/loops` in four modules** (self tail calls, module cells, hoisting and rotation, bounds checks),
  keeping the order.
- **6c. The runtime functions' facts** as `fresh` and `registration` columns of `runtimeFunctions`; the passes'
  lists go.
- **6d. arm64's callee-saved registers** derived from the description in `savedFirsts`, `callMaps`, and `frameMaps`,
  with the 8s and 16s named. Assembly byte-identical.
- **6e. The rest:** `ssa/scalars` into `passes/`; `ssa/build/values` split into `parts`, and `representation` renamed;
  `layout`'s byte functions take a `Shape`; `ssac`'s liveness into `ssa/cfg`; the two `Compiled`s; `machine/target`'s
  import of `ssa/nodes`; the machine README's second-target claim matched to the code.

`tools/compare-codegen` and `tools/c-diff` after each; `tools/check` at the end.

## 7. The Type Checker's Duplicated State (§3.1)

- **7a.** An assertion, under `tools/check`'s test runs, that the `loopDepth` and `e` passed agree with `c.loopDepth`
  and `c.env`.
- **7b.** The parameters removed, family by family, one commit each.
- **7c.** `checkHook` and `synthHook` passed to `checker.new`; `typecheck`'s unused exports go.
- **7d.** `env.T`'s options as `e.options`; the three `Env`s renamed; `env.lookupOf` without its argument.
- **7e.** Recovery and poisoning written once; `poison` named for what it covers. `resolveOptionBound` merged with
  `resolveBound` in both compilers.

`tools/check` at the end.

## 8. The Interpreters, Values, the Language Server, and the JIT (§3.7)

- **8a.** The shared operations on values in `interpreter/primitives` and `values/model`, mirrored in the bootstrap;
  one rule for whether applying a value to types runs it.
- **8b.** The REPL's echo text in `types/`, used by `interpreter/formatting` and `ir/lower`, mirrored in the bootstrap.
- **8c.** `irinterp`'s second root frame; `IrClosure.env` as a frame.
- **8d.** The JIT's debug object and `codegen/arm64/asm` sharing one table of DWARF constants and abbreviations; the
  loader reads instruction fields from the encoder.
- **8e.** The language server: separate names for LSP's two kind enumerations; the line index kept per document.

`tools/check` at the end.

## 9. The Long Functions

Each split into named phases or members, one commit each, with no output change (`tools/c-diff`, and
`tools/compare-codegen` for the compiler's own code):

- `wasm/codegen.unitModule` (with 5e's declarative externals);
- `tuples.tupleScope`;
- `treewalk.evalIn`;
- `simplify.body` (each statement kind returning keep, drop, splice, or restart);
- `hoistLoop`;
- `verify`'s two stage checks (a checker tuple);
- `ssa/verify.problemsIn`, `buildUnit`, `control.statement`;
- `select.select`, `codegen.machineCode`;
- `regalloc.allocateWith` and `coalesceWith`, with the compiler's build time measured before and after.

`tools/check` at the end, then the C fixed point.

## 10. The End

The review and this plan are deleted, and what remains undone goes to [tasklist.md](tasklist.md).
compiler-organization.md records any convention the plan set (the internal-error rule, the pipeline's entries, where
shape facts live).
