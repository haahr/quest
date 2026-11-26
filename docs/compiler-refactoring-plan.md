# Plan: Refactoring the Self-Hosted Compiler

Refactorings that make `questlang/` easier to change without mistakes. They come from a read-only review of the whole
compiler on 2026-11-20 (f0f13513). On 2026-11-25 (f47a1c00), after 63 commits to `questlang/`, the review's ideas were
checked against the code again, and the counts below are from that second check. The new `loops`, `nanchecks`, and
`conditions` passes had added their own copies of most of the SSA duplication the review found.

The performance-tasks plan ([benchmarks.md](benchmarks.md) §49), which changed `ssa/passes/*` and `codegen/arm64` too,
has landed; steps 11 and 12, in the build engine, were made while it ran, and two of these ideas, the machine
instructions' facts (`minst.info`, cc30757e) and the calling convention read from the target description (129eaf62),
were made with its step 9. When a step is done, its section is deleted,
and what it leaves that lasts goes into the documents that describe the code: [ssa.md](ssa.md), [ir.md](ir.md),
[arm64.md](arm64.md), [wasm.md](wasm.md), [build-process.md](build-process.md), [testing.md](testing.md), and the
READMEs. The plan is deleted when the order in §2 is done; §4 and §5 then go to whatever document fits them, or are
deleted.

## 1. Rules

- **Behavior does not change.** A refactoring step leaves the SSA, IR, C, assembly, and WebAssembly goldens byte for
  byte as they were. A step that changes output is two steps.
- **Self-hosted compiler only.** None of these steps changes shared behavior, so under the two-compilers policy the
  bootstrap does not follow. Where an error, usage, or log text is shared, it stays identical.
- **Derive before testing.** Where two lists must agree, one is computed from the other. Where the compiler can check
  a fact (an exhaustive `case` with no `else`), it does. A test is for what is left over: facts that must agree but
  cannot be derived, and prose that lists what the code defines.
- **Tests per step:** the suites the step touches. For SSA steps, those are the SSA goldens, the self-hosted arm64,
  ssac, and JIT runs, and `ssa_*` phase dumps. Each step also needs the arm64 fixed point. The C fixed point and
  `tools/check` run once, at the end of each group in §2.
- **Performance:** none of these is meant to change the compiler's speed. A step whose restructuring sits on a hot
  path (`subtyping`'s keys, §5) counts the compiler's instructions before and after, by
  benchmarks.md §49.1's method, and stays within 1%.

## 2. Order

| Group | Step | What | Size |
|---|---|---|---|
| 3. IR structure | 7 | One visitor for IR nodes, with positions in one place | medium |
| 4. Small and mechanical | 8 | IR passes' state in their records; IR stages as an option | small |
| | 9 | C representations as an option | small |
| | 10 | One kernel for both interpreters | small to medium |
| | 13 | One strongly-connected-components routine | small |

Group 1 comes first because each of its steps fixes a copy that has already drifted. Group 2 makes the SSA's facts one
table, after group 1 has removed the copies that would otherwise be converted twice. Group 3 is the largest step taken
here. Group 4's steps are independent of each other and can run in any order, or in parallel sessions, since they touch
different files. Steps are not renumbered as they are done. §4 lists the larger ideas left for later, and §5 those
not taken.

## 3. Steps

### Step 7: One visitor for IR nodes

**Problem.** `Op` has 34 cases and `Stmt` 25. About twelve chains re-list their fields: `walk`'s `statementBodies`,
`statementBinders`, `opUses`, `statementUses`, `mapInOp`, and `mapInStmt`; `clone`'s `copyOp` and `copyStmt`;
`describe`'s `opTypes` and `stmtTypes`; `verifycore`, the printer, and `irinterp`. Each backend has its own
chain too. Adding `opIsSet` touched 14 files. The renaming walk once missed descriptors that cloning copied (fixed in
4a7cea93), the kind of mistake that comes from keeping copies in step. 18 `Stmt` cases carry `var pos`, so `stmtPos`
and `positionAt` are 18 identical arms each.

**Change.**
- `visitOp` and `visitStmt` in `ir/walk`, taking one closure per kind of child (atom, variable, type, descriptor, plan,
  function, body, binder), with in-place variants.
- `opUses`, `statementUses`, `mapInOp`, `mapInStmt`, describe's collector, and most of `clone` follow from them.
- The printer, `verifycore`, `irinterp`, and the backends keep their own exhaustive cases: they do different things
  per case, not the same thing to each child.
- Positions move out of the cases: `Stmt = Tuple var pos kind: StmtKind`. If that change is too wide for the backends
  in one step, it is a step of its own after this one.

**Tests.** IR goldens at every stage, unchanged, and `verify` at every stage as always.

### Step 8: IR passes' state in their records

**Problem.** `represent.typeVarsMemo`, `planning`, and `adapting`, `describe.uses`, and `nodes.counter` are module-level
state, cleared by hand (`hashMap.clear(typeVarsMemo)`, `represent:1502`). The passes are not reentrant, which the JIT
and the kernel would want. IR stages are strings (`unit.stage := "simplified"`) compared by `atLeast` six times.

**Change.** The state moves into `Representer` and `Describer`, and the counter into the unit. `Stage` becomes an
option, with its name for printing.

### Step 9: C representations as an option

**Problem.** The C printer decides by comparing type spellings: 11 comparisons with `"QVal"` or `"QVariantVal"`, and
3 tests of `endsWith(… "*")`, which grew with `opIsSet`.

**Change.** A `CRep` option, made by `layout` and spelled only when printed.

**Tests.** The C goldens, unchanged.

### Step 10: One kernel for both interpreters

**Problem.** `treewalk.optionAssertion` (`:446`) and `irinterp.payloadOf` (`:381`) are near copies that already
differ: treewalk checks `i < extent labels`, and irinterp does not. Bounds checks are written inline three times in
treewalk and four in irinterp. treewalk dispatches operators by their spelling, and irinterp maps each `Prim` back to
a spelling (`nodes.primName`) to call the same functions.

**Change.**
- The value-level operations move into `interpreter/primitives`: option assertion and payload, the indexed access with
  its bounds check, and arithmetic by operator.
- Both interpreters call them.
- Whether irinterp should check the labels' bound is decided first. If it should, adding the check is a fix that
  lands before this step.

**Tests.** The shared behavior goldens through both interpreters; `run_ir_*` at every stage.

### Step 13: One strongly-connected-components routine

**Problem.** Tarjan's algorithm is written three times: `ssa/passes/tailjumps:38`, `ir/inline:101`, and
`types/canonical:898-961`.

**Change.** One generic routine over integer nodes and a successor function, in a shared utility module. If
canonical's version interleaves work with the walk, it keeps its own and says why.

## 4. Later

Worth doing, but larger or less urgent; each becomes a step when there is time for it.

- **One traversal for types.** `TypeForm` has 28 cases. Full chains over it:
  - in `types/model`: `formFree`, `typeKey`, `substituteFull`, `typeParts`, `rebuild`, `findPathTypes`,
    `typeMentionsSymbolIds`, and `show`;
  - in `canonical`: `canonicalNode` and `mayRecurParts`;
  - in `dump`: `compact`, `className`, `typeDump`, and `shortTypeName`;
  - elsewhere: `kinds.synthUncached`, `repr/shapes.shapeOf`, `interfacecompiler.formatType`, and
    `digests.printedParts`.

  That is about 16. A `children(t)` that yields each part with the ids bound at it, and a `rebuild(t f)`, would shrink
  most of them. Part order must match `typeParts` for the bootstrap's parity. This has the largest payoff of anything
  here, but the chains have not grown since the review.
- **`Plan` as a sum type.** A `kind` and 8 var fields whose meaning depends on it. It is tested in about 82
  `case … kind when planX` arms (24 in `nodes`, 18 in wasm's codegen, 12 each in the C printer and
  `ssa/build/aggregates`) and built by hand 38 times. An option with one case per kind would touch every backend.
- **`repr/staticdata` as options.** `Ref` encodes null as `symbol = ""` and a bound variable as a reserved symbol with
  `index > 0`. `DescriptorForm.kind` is a string, which wasm maps to numbers by a linear list (`kindOf`) and a
  hand-numbered `baseKinds`. Options for both, and one numbering per target.
- **The WebAssembly builders.** `runtime.mod.quest` numbers its functions by hand (`24 + wasiCount + …`), its locals
  by number (199 uses), its branches by depth, and its data string by counted offsets (`piece(39 6)`). These break
  silently when an export or a string is added. A `wasm/build` with named functions, named locals, labels, and a
  string pool would fix that half first. Symbolic function indices resolved at the end would then remove
  `unitModule`'s pre-scan (`wasm/codegen.mod.quest:5850-6130`), and with it most of the externals table problem.
- **Build keys.** Staleness is decided by file times (`manifest.isManifestStale`, `paths.dependencyChange`,
  `interfacecompiler.current`), though `fingerprint` hashes an interface's meaning and only the JIT uses it. The
  currency rules are spread over `manifest`, `engine`, `paths`, and `abi`, and a `.qi` is parsed three ways with
  silent defaults. One recorded key per artifact (ABI, producer, backend, source digest, import resolutions,
  dependency fingerprints), whose first differing part is the reason, and one schema with one encoder and decoder.
  This is one project. It pays when a comment edit in a widely imported interface should rebuild nothing.
- **Narrowing the block-local opcodes** (after step 5): ssac keeps arm64's `rematerializable` set (the table's
  constants, symbols, and nulls, and the comparisons, `and`s, `mul`s, and `ptrAdd`s arm64 fuses), since narrowing it
  to the table's is a change of output. Whether ssac does better with the table's alone, and whether arm64 still needs
  its constants kept block-local now that `select.rematerializable` makes them again, are measured changes:
  instructions retired on the benchmarks and the compiler, and hamlet's stack accesses (ssa.md §4.1).
- **What step 6 left.** `ssa/nodes` has `constantOf`, `useCounts`, `operands`, and `mapOperands`, and the passes'
  plain copies call them. Left as they were: `proxyFold.Defs` (a value's block and index, which escape and scalars
  need to find an instruction's place), barriers' table of definitions (the same, for a checker), arm64 selection's
  use counts and definitions (made in its one sweep over the function with what else it collects, on a hot path), and
  the terminator cases of escape and scalars that give each kind of use its own reason.
- **An analysis cache for the SSA passes.** `cfg.graph` is rebuilt once per pass and four times inside `loops`. A
  `changesCfg` flag in `ssa/pipeline`'s table of passes would make a cache per function possible; it was left out of
  that table (step 1) because nothing reads it, and a wrong flag nothing checks would be worse than none. The cache
  adds it, with a check under `QUEST_CHECK_IR` that a pass flagged as keeping the CFG did. Count first.
- **One provenance solver for escape and scalars.** Both keep a `State` with `defOf`, `takenTargets`, `setPointer`,
  `pointers`, and `check`, nearly line for line, and both grew by about 200 lines since the review. One sparse solver,
  with each pass supplying its lattice and legality checks, is the largest and riskiest idea here. The optimism the
  scalars comments describe must carry over exactly.
- **What step 11 left of the build's settings.** `moduleCompiler.Settings` now carries what compiling a module
  depends on, through the engine (`engine.settings`), the workers' `Job`, and the command line a worker reads back
  (`workers.command` and `parseCommand`, side by side). Two parts were left: `engine.T` is still rebuilt field by
  field in `changed` for `parallel`, `withBackends`, and `reportingInferable`, which only the driver calls, once each;
  and the environment is set up both in `driver/main.run` and `engine.compileMainUnit`, which differ (interactive
  mode, the JIT's in-memory artifacts, whole-program compiling) more than they repeat.
- **The rest of the build engine's scheduler.** `unflushedBuildModules` keeps its queue, predicted imports, deferred
  notes, and conformance checks (three sites) in about 440 lines of closures, after step 12.

## 5. Not Taken

Each with its reason, so that it is not proposed again without new evidence:
- **A table of WebAssembly externals** (review §2.4): `externalCall` shrank from 384 to 320 lines as externals moved to
  Quest, and symbolic indices (§4) remove the part that hurts.
- **Value numbering's trivial-parameter collapse in `ssa/blockParams`** (step 3): it decides which parameters are
  trivial through the pass's own union-find of equal values, so on its own it would find fewer; the removal that
  follows it is `blockParams.dropParams`.
- **A table of IR primitives** (§2.3): 26 prims, unchanged since the review; step 10 removes the interpreters' share.
- **A generated IR node spec** (§3.2's second tier): generated sources in the tree, and field compatibility with the
  bootstrap; step 7 gets most of the benefit by hand.
- **One printer for types** (§3.4): six printers whose outputs each must stay as they are (two of them are formats
  written to files).
- **A locally nameless form for bound variables** (§4.5): the typed `ReservedSymbolUse` constructors and decoders
  already exist; the encoding is provisional and the user may revisit it, which is a design decision, not a
  refactoring.
- **Tuple cache keys** (§4.6) and **exact use counts in the simplifier** (§5.8): these are compile-time performance,
  judged under performance rules (a measured gain of 1%), not here.
- **Machine labels as integers and one emission layer for arm64** (§4.7, §6.3): `QUEST_CHECK_ENCODING` already keeps
  the three offset computations equal, and nothing has broken there.
- **A C AST** (§6.4): large, and the C backend is no longer the default. The self-hosted printer's `callsFunction`
  treats more text as a call than the bootstrap's `_CALL_RE` does, which is safe (extra barriers) and allowed, since
  C goldens are per compiler.
- **Fusion matched once in arm64 selection** (§6.6), **JIT relocations shared with the encoder** (§6.7), **one
  logical-immediate routine** (§6.8): small, in code that rarely changes, guarded by the encoder test. §6.8's
  parallel-move half was wrong: `ssac.jumpText` copies through temporaries and does not resolve parallel moves.
- **Use-site expectations and an IR type check** (§5.7), **a context record in the typechecker** (§5.11), **one head
  reduction for types** (§5.12): medium to large, in code that has not been changing, each with subtle differences
  that would need to become explicit.
- **Error recovery in the typechecker** (§8.1): already in place at every binding (`bindings.elaborateRecovering`,
  diagnostics.md §4.5); finer recovery inside an expression would need an error type, which is a feature, not a
  refactoring.
- **Typed parser actions** (§8.2), **a condition context in lowering** (§8.3), **a declarative option table** beyond
  the SSA's phases (§7.5), **shared memo tables** (§7.7), **build errors as diagnostics** (§7.8): low payoff now.
- From the review's own list: a rewrite DSL, a generic block-level dataflow framework, e-graphs, Pratt parsing, and a
  Salsa-style query engine.

## 6. What to Keep

The review's reading of what the compiler already does well, which these steps should not undo:
- **Types:** hash-consed nodes that cache their free ids and metavariables; the coinductive subtype prover; one
  `elaborateX(expected)` per construct; canonicalization by partition refinement.
- **IR:** ANF with structured join points; lowering by destination passing; `verify` and the IR interpreter at every
  stage; the numbered rule list in front of `represent.plan`.
- **SSA:** block parameters; one instruction shape with dense numbering; a verifier and a text form that round-trips;
  the runtime functions' effects table; one `cfg` module; bisecting with `QUEST_SKIP_PASSES`.
- **Machine code:** the target-independent machine layer and linear scan; an encoder separate from the printer and
  checked against it; exhaustive `case` with no `else`.
- **WebAssembly:** `wasm/model` as a typed module; one opcode table for `encode` and `printer`.
- **Build:** `Diagnostic`, `SourceMap`, and atomic `.qi` writes.
