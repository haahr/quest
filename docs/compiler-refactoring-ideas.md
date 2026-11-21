# Compiler Refactoring Ideas

Abstractions from other compilers and language implementations that would make `questlang/` easier to understand,
change, or trust. They come from a read-only review of the whole self-hosted compiler (about 84,000 lines) on
2026-11-20; the claims marked *checked* were confirmed against the code, the rest are the reviewers' readings. None of
this is planned work: each idea is a candidate, ranked within its section by payoff. The faults the review found are
tasks in [tasklist.md](tasklist.md), not here.

None of the ideas needs type classes, GADTs, or macros; they use options, tuples, closure records, generic `hashMap`
and `vector`, and tables indexed by `ordinal`, all of which the compiler already uses. Output that must match the
bootstrap byte for byte (logs, usage text, error text, printed IR) constrains several of them; and under the
two-compilers policy, any change to shared behavior goes in both compilers, behind the shared goldens.

## 1. What to Keep

- **Types:** hash-consed nodes that cache their free ids and whether they hold a metavariable (Lean 4's
  `Expr.Data`); the coinductive subtype prover; one `elaborateX(expected)` per construct, for both checking and
  synthesis (Dunfield and Krishnaswami); canonicalization by partition refinement.
- **IR:** ANF with structured join points; lowering by destination passing; `verify` at every stage and the IR
  interpreter as an oracle at every stage (GHC's Core Lint and MLton's per-IL checks, applied semi-formally); the
  numbered rule list in front of `represent.plan`.
- **SSA:** block parameters rather than φ nodes (MLIR, Cranelift, SIL); one instruction shape with dense numbering;
  a verifier and a text form that round-trips; the runtime functions' effects table; one `cfg` module; bisecting
  with `QUEST_SKIP_PASSES`; `barriers`, a textbook forward dataflow over bitsets.
- **Machine code:** the target-independent machine layer with a Wimmer-style linear scan taking the target as a
  parameter (LLVM's MachineInstr and regalloc2's split); an encoder separate from the printer and checked against it
  (`QUEST_CHECK_ENCODING`); exhaustive `case` with no `else` ([arm64.md](arm64.md) §5).
- **WebAssembly:** `wasm/model` as a typed module, one opcode table that both `encode` and `printer` read (as
  wasm-tools does), the runtime's recursion group built from a table, `locals` as a pass after code generation.
- **Build:** `Diagnostic` (severity, labels, notes, help, code), close to rustc's; `SourceMap`; atomic `.qi` writes.

## 2. Property Tables Instead of Repeated Exhaustive Cases

The most widespread pattern. Exhaustive `case` keeps every predicate honest about every opcode, but each predicate
lists them all again, so a new opcode means editing many lists, each a chance to put it in the wrong arm. One
exhaustive `info(op): OpInfo` per opcode set, held in an array indexed by `ordinal`, keeps the check in one `case` and
turns the predicates into field reads. Precedents: LLVM's `MCInstrDesc` and `Instruction.def` (from TableGen), Go's
`genericOps.go` → `opGen.go`, GHC's `primops.txt.pp`, MLton's `Prim`, MLIR traits.

1. **SSA opcodes (53).** Listed in about 15 places: `nodes` (`resultType`, `opcodeIndex`, `opcodeName`, `opcodes`),
   `valuenumbers` (`numbered`, `local`, `commutative`), `selects.speculable`, `tailcalls`, `verify`, the parser and
   printer, `accumulate` (`combines`, `identity`), and five in `codegen/arm64/select`. `local` and `commutative` use
   `else false`, which loses the check. Fields: name, arity, result-type rule, pure, commutative, speculable, memory
   effect, which arguments carry provenance, identity element. Medium.
2. **arm64 machine instructions (about 55).** `minst` (`results`, `pure`), `printer.count`, `peephole`
   (`conditional`, label counting, `access`, `crossing`), `codegen` (`isBrk`, which lists 54 ops to return false;
   `retarget`), and `select` (`constOf`, `condition`, `isComparison`, `isRealComparison`). Fields: defs, pure,
   mayLoad, mayStore, isBranch, isCall, isTerminator, isDirective; label-bearing ops get a `labelOf`/`withLabel`
   pair. Operand roles (def, use, use-def, later fixed registers) would replace "the first n registers are defs",
   which cannot express `movk`'s read of its destination (regalloc2's `Operand`, GCC's `=r`/`+r`). Small to medium.
3. **IR primitives.** Spread over `nodes` (`primName`, `primNamed`), `simplify` (`pure`, `foldInt`, `foldPrim`), both
   interpreters (treewalk by operator spelling), and three backends. One record per prim: spelling, operand and
   result kinds, may raise, folder. Backend emission stays an exhaustive case. Small.
4. **WebAssembly externals.** `wasm/codegen.externalCall` is a 400-line `elsif named("quest_…")` chain, after three
   side tables (`coreExternals`, `realconvExternals`, `realmathExternals`) of `Array(Array(String))` with signatures
   coded as `"ennenn"` and arities as text, each searched linearly; `intrinsic` has the same shape. One
   `hashMap.T(String ExternalImpl)` whose cases (base field, core, realconv, realmath, inline emitter, raises) carry
   typed `Array(ValType)` signatures, as Go's `ssagen` intrinsics map and Cranelift's libcalls do. With §6.1, the
   same entry says what to import and how to call it. Medium.

### 2.5. A Sketch, for the SSA Opcodes

One record per opcode, made by one exhaustive `case` in `ssa/nodes`, and an array of them indexed by `opcodeIndex`:

```quest
(* What every pass needs to know about an opcode, decided in one place:
 * info's case lists every opcode with no else, so a new opcode cannot be
 * added without deciding each fact *)
Def Effect = Option pure reads writes calls end
Def Traps = Option never divides end                 (* opDiv, opRem *)
Def OpInfo = Tuple
    name: String
    arity: Int                                        (* ~1: variable (calls, select) *)
    effect: Effect
    traps: Traps
    commutative: Bool
    local: Bool          (* fused by arm64 selection, or cheap to keep near: VN keeps it in its block *)
    provenance: Array(Int)                            (* arguments a pointer result derives from *)
    identity: maybe.T(Int)                            (* accumulate: 0 for add, 1 for mul *)
end

let info(op: Opcode): OpInfo =
    case op
        when opAdd then commutative(identity(fact("add" 2 pure never) 0))
        when opSub then fact("sub" 2 pure never)
        when opMul then commutative(local(identity(fact("mul" 2 pure never) 1)))
        when opDiv then fact("div" 2 pure divides)
        when opEq then commutative(local(fact("eq" 2 pure never)))
        when opPtrAdd then local(provenance(fact("ptrAdd" 2 pure never) 0))
        when opLoad then fact("load" 1 reads never)
        when opStore then fact("store" 2 writes never)
        when opCall, opCallIndirect then fact(... ~1 calls never)
        ...                                           (* the rest, no else *)
    end

(* Built once: the passes read fields, not cases *)
let infos: Array(OpInfo) = (* info(opcodes[i]) for each i *)
let infoOf(op: Opcode): OpInfo = infos[opcodeIndex(op)]
```

`fact` fills in the defaults (not commutative, not local, no provenance, no identity), and `commutative`, `local`,
`identity`, and `provenance` each return the record with one fact changed; Quest has no record update. Only tuples and
functions are needed. The predicates then read the table:

```quest
(* valuenumbers *)
let numbered(i: ssa.Inst): Bool =
    case ssa.infoOf(i.op).effect when pure, reads then true when writes, calls then false end
let local(op: ssa.Opcode): Bool = ssa.infoOf(op).local
let commutative(op: ssa.Opcode): Bool = ssa.infoOf(op).commutative

(* selects: speculable is "pure and cannot trap", plus its one rule that looks at an argument *)
let speculable(defs: Array(maybe.T(ssa.Inst)) i: ssa.Inst): Bool =
    let n = ssa.infoOf(i.op)
    case n.effect
        when pure then n.traps?never andif not(ssa.isOp(i ssa.opSlot))
        when reads then loadOfStatic(defs i)
        when writes, calls then false
    end

(* nodes *)
let opcodeName(op: Opcode): String = infoOf(op).name
```

`verify`'s arity check reads `arity`, `accumulate` reads `identity`, and escape and scalars read `provenance` rather
than listing `opPtrAdd` and `opUnproxy`.

The table holds facts, not behavior. Each backend's emission for each opcode (`arm64/select`, ssac's printer) stays an
exhaustive `case` with no `else`, so no backend can skip an opcode, and so do `resultType` for the opcodes whose result
depends on their arguments (`select`, `load`) and `verify`'s checks of calls and of load and store widths.

The other opcode sets follow the same pattern:
- `minst.Op`: an `MInfo` of defs (replacing "the first n registers are defs"), pure, mayLoad, mayStore, isBranch,
  isCall, isTerminator, isDirective, and a `labelOf`/`withLabel` pair; `isBrk`'s 54-case list becomes a field read.
- `nodes.Prim`: a `PrimInfo` of spelling, operand and result kinds, may raise, and folder, in place of
  `primName`/`primNamed`, `simplify.pure` and `foldInt`, and treewalk's string lists.
- The wasm externals: a `hashMap` from symbol to an `ExternalImpl` option (`implCore(fn params results)`,
  `implRealmath(fn arity)`, `implInline(emitter)`, ...), with typed signatures.

The cost is one table per opcode set and mechanical rewrites of the predicates, each checked by the goldens, whose
SSA, IR, and C output should not change; reading a field of `infos[i]` costs about what the `case` did. One decision is
the user's: whether `local` belongs in the table or stays value numbering's own policy, a tuning choice (ssa.md
section 4.1) rather than a fact about the opcode.

## 3. One Generic Traversal per Tree

1. **Types** (*checked*). `types/model` spells out the ~25-case chain over `TypeForm` about ten times (`formFree`,
   `typeKey`, `substituteFull`, `typeParts`, `rebuild`, `findPathTypes`, `typeMentionsSymbolIds`, `show`), and
   `canonical` (`canonicalNode`, `rebuildNode`, `mayRecurParts`), `dump` (`compact`, `typeDump`), `contractiveness`,
   and `kinds.synthUncached` repeat it; the interface says a new form needs four separate edits. Each copy encodes
   binder scoping its own way. rustc's `TypeFoldable`/`TypeVisitor` writes the structure once: here, one
   `children(t)` yielding each part with the ids bound at it, and one `rebuild(t f)`, would make `formFree`,
   `substitute`, the "mentions" walkers, and `mayRecur` 5 to 15 lines each, and `typeKey` the tag plus labels plus
   child ids. Hot paths (`substitute`, `typeKey`) may keep hand-written versions checked against the generic one;
   part order must match `typeParts` for bootstrap parity. Medium; it makes §4.5, §8.1, and §8.2 cheaper.
2. **IR nodes** (*checked*). Each `Op` and `Stmt` case is declared four times (the options and the per-case tuples, in
   `nodes.int.quest` and again in `nodes.mod.quest`), and about eight chains re-list its fields: `walk`
   (`statementBodies`, `statementBinders`, `opUses`, `statementUses`, `mapInOp`, `mapInStmt`), `clone`, `describe`
   (`opTypes`, `stmtTypes`), `verify`, the printer, and `irinterp`. The chains already disagree (tasklist.md). Two
   tiers:
   - by hand: one `visitOp`/`visitStmt` taking closures per kind of child (atom, variable, type, descriptor, plan,
     function, body, binder), with in-place variants, from which `opUses`, `mapInOp`, describe's collector, and most
     of `clone` follow (Flambda's `map_named` and `iter`; uniplate-style children). Medium.
   - generated: an ASDL-like node spec from which a `tools/` generator writes the options, tuples, constructors, and
     visitors (CPython's `asdl_c.py`, nanopass `define-language`). Large: generated sources in the tree, and the
     bootstrap must stay field-compatible.
3. **Positions on IR statements.** 18 `Stmt` cases carry `var pos`, so `stmtPos` and `positionAt` are 40 lines of
   identical arms; `offset: maybe.T(Int)` repeats across ops. `Stmt = Tuple var pos kind: StmtKind`, or a side table
   (CPython ASDL attributes, Flambda's `Debuginfo`, Cranelift's srcloc table). Falls out of the generated tier.
4. **One printer for types.** `model.show`, `dump.compact`, `dump.typeDump`, and `shortTypeName` each walk the forms,
   differing in depth limits, abbreviations, and layout. One `render(t style)` (OCaml's `Printtyp`); worth doing only
   with §3.1, since every style must match the bootstrap.

## 4. Sum Types Where Strings and Sentinels Carry Meaning

1. **IR `Plan`.** One tuple of a `kind` and 8 var fields whose meaning depends on it (`fields` is components for a
   copy, parameters then result for an adapt); 19 `planIs` and `planKindIndex` tests across represent, slots,
   describe, the printers, and SSA. An Option with one case per kind (GHC's `Coercion`; Leroy's wrap and unwrap
   coercions). Medium; touches every backend.
2. **`repr/staticdata`.** `Ref` encodes null as `symbol = ""` and a bound variable as the symbol
   `"quest_type_bound_vars"` with `index > 0`; `DescriptorForm.kind` is a string; `Descriptor.kindConstant` is the C
   macro name, which wasm (`kindOf`, a linear list) and C/arm64 (`runtimeLayout.constant`) each map to their own
   numbers. `DescKind` and `Ref` options, with a numbering per target or one shared with `runtime/wasm/core`, and a
   `Part` case for the synthesized opaque part (MLton's `ObjectType`, GHC's `ClosureTypeInfo`). Medium; output
   unchanged. `values/dynamicjson.Ref` and `Shape.kind` have the same shape, smaller.
3. **C representations.** The C printer decides by comparing type spellings (`eq(cType(t) "QVal")`, `"QVariantVal"`,
   `endsWith(… "*")`). A `CRep` option produced by `layout` and spelled only when printed. Small, and the first step
   of §6.4.
4. **Driver phases.** Strings in an array searched by `reaches` and `shows`, with `irStage(prefix)` joining strings
   and the backend rules scattered over `driver/main` and `options`. A `Phase` option computed once from the options
   (GHC's `Phase`/`StopPhase`). Medium; main.quest is the hardest file in its area to read.
5. **Canonical bound variables.** `model.ReservedSymbolUse` packs de Bruijn bound variables and positional
   quantifiers, recursions, and binders into negative symbol ids (prefix × 2³²), decoded by arithmetic in
   `canonical`; `kinds` keys path types by `~1 * t.id`. A locally nameless representation in disguise; a
   `typeBound with use index` form, or at least typed constructors and decoders. The encoding is already marked
   provisional. Medium.
6. **String cache keys.** `subtyping` builds `"v123|o456"` keys twice per step on the checker's hottest path;
   value numbering keys expressions by `opcodeName <> " " <> …` and orders commutative operands by their text. Tuple
   keys with a hash combiner, as `hashMap.new` already allows (rustc's `FxHashMap<(Ty, Ty), _>`, Go's `cse`, LLVM
   GVN's `Expression`). Small.
7. **Machine labels.** Strings, with relaxation recognizing its own by the prefix `"_r"`. Integers with a name table
   for printing (§6.3).

## 5. Shared Analyses and Utilities

1. **SSA def-use and definitions.** No use lists: `onlyProxyTests` scans the whole function per `ptrToInt`, and use
   counting is hand-rolled in `concats`, `valuenumbers`, and `scalars`. Definitions exist four ways (`ssa.definitions`,
   `proxyFold.Defs`, a copy in `tables`, `valuenumbers.constantOf`). A `uses(f)` analysis built on demand in one
   sweep (LLVM use lists, Cranelift's value lists), one `Defs`, and `operands(t)`/`mapOperands(t f)` for terminators,
   whose non-target operands are listed five times. Small to medium.
2. **SSA cleanup.** Trivial-parameter removal, parameter dropping with its jump arguments, and dead code are written
   in `valuenumbers` and again in `scalars.dropDeadParams`; "filter targets' args by kept params, then clear" appears
   four times. One module (Braun et al.'s trivial-φ removal, Go's `phielim` and `deadcode`, MLton's `RemoveUnused`).
   Small.
3. **`copyInst`.** `tailjumps` copies an `Inst` by listing its fields, so the next field added is silently dropped;
   `ssa.copyInst(i mapValue)` (LLVM's `ValueMapper`). Small.
4. **Strongly connected components** (*checked*). Tarjan's algorithm is written three times: `ssa/passes/tailjumps`,
   `ir/inline`, `types/canonical`. One shared routine. Small.
5. **Pass table and analysis cache.** `ssa/pipeline` names passes in an array and dispatches on the names through an
   if-chain; the READMEs have drifted (`concats` is in neither pass table). An array of `{name run changesCfg}`
   records (Go's `passes []pass`), and a per-function cache of `cfg.graph` and definitions cleared when a pass says
   it changed the CFG (LLVM's `PreservedAnalyses`). Small.
6. **One provenance analysis for escape and scalars.** `passes/escape` and `scalars` each have a state with `ptr` and
   `off` arrays, a `setPointer`, `reach`, `takenTargets`, a `pointers()` fixed point, and a `check()` classifying uses
   almost line for line; `onlyProxyTests` is copied verbatim; escape nests three whole-function fixed points. One
   sparse solver with a lattice per value and executable CFG edges (Wegman–Zadeck SCCP, LLVM's `SCCPSolver`, Graal's
   partial escape analysis), each pass supplying its merge policy and legality checks. Large and the riskiest idea
   here: the optimism the scalars comments describe must carry over exactly.
7. **Use-site expectations in the IR.** The type each operand position expects is worked out in `represent`
   (`statement`, `operation`, `storedType`), again in `verify.representationProblems`, and in `describe`; the callee
   type of a call through a module member alone appears four times. One `walk.expectations(stmt)` that `represent`
   inserts conversions from and `verify` checks against (Leroy, "Unboxed objects and polymorphic typing", 1992).
   Medium. Then an IR type check under `QUEST_CHECK_IR`, `atomType(arg) <: expected` after each pass (GHC's Core
   Lint, MLton's per-IL type check), starting from "subtype or same shape" with known exceptions per stage. Medium
   to large.
8. **Exact use counts in the simplifier.** `walk.countUses` runs once per round; deleting a dead pure `let` does not
   decrement its operands, so a dead chain takes a round per link under `maxRounds = 6`, and each statement is
   rewritten twice per round. Decrement and cascade on deletion (Appel and Jim, "Shrinking lambda expressions in
   linear time"; GHC's occurrence analyser), and one atom map for renaming and substitution. Measure the rounds
   first. Medium.
9. **One kernel for both interpreters.** `treewalk.optionAssertion` and `irinterp.payloadOf`'s option branch are near
   copies; the bounds check and `arrayOpError` appear three times in each; treewalk dispatches operators by spelling,
   irinterp maps `Prim` back to the spelling. Value-level semantics in `primitives`, both interpreters thin over it
   (CompCert's shared `Cop` and `Values`). Small to medium.
10. **Module-level state in IR passes.** `represent.planning`, `adapting`, `typeVarsMemo`, `describe.uses`, and
    `nodes.counter` move into `Representer` and `Describer`, so the passes are reentrant for the JIT and the manual
    `hashMap.clear` goes. IR stages as an option rather than strings scanned by `atLeast`. Small.
11. **A context record in the typechecker.** Every family function takes `(c expr expected e loopDepth)`;
    `loopDepth` appears 239 times, and also lives in `checker.T.loopDepth`, kept in step by hand at four sites. An
    immutable `Ctx` of env, loop depth, and function depth, with `checker.T` keeping only global state (GHC's
    `TcGblEnv`/`TcLclEnv`, rustc's `FnCtxt`). Medium, mechanical.
12. **One head reduction for types.** Seven "expose the head" functions (`evaluateLazily`, `normalizeType`,
    `betaReduceHead`, `unfoldRecursive`/`Any`, `resolveTypeBound`, `kinds.unfoldHead` and two private resolvers,
    `canonical.canonicalStructure`) differ in what they look through and in caching. One `whnf(t steps lookup)` with
    flags and named presets (Rocq's `whd` with `RedFlags`, Lean 4's `whnfCore` with `WhnfCoreConfig`, GHC's `coreView`
    vs `tcView`). Medium; their subtle differences (arity tolerance) must become explicit flags.

## 6. Builders and Buffers in the Emitters

1. **Symbolic references in WebAssembly.** Imports come before defined functions in the index space, so
   `unitModule` walks every statement first to guess which imports codegen will need, re-deriving the dispatch of
   `externalCall`, `intrinsic`, and `prim` and repeating the signatures, and codegen checks at emission whether it
   guessed right; `importedFunctions + length(functions)` arithmetic appears 15 times, and `runtime.mod.quest`
   numbers functions by hand. Function, global, and tag immediates as symbolic references, imports added on first
   use, indices resolved in one final pass (Binaryen, walrus, LLVM's wasm object writer). Medium to large; with
   §2.4 the pre-scan disappears.
2. **A structured-control builder for WebAssembly.** Each block is an `emit` plus an `open`, and `close` emits the
   `end`; `if`/`else`/`end` are often written by hand; `runtime.mod.quest` uses numbered locals and branch depths, and
   one data string with hand-counted offsets (`piece(39 6)`). A `wasm/build` module both use: `block`, `loop`, and
   `ifElse` taking a body closure, `br(label)` by name, named locals, a string pool, and short constructors for the
   boilerplate (`nullRef`, `callQuest`, which pushes `noClosure`, written by hand 42 times). Binaryen's `Builder`,
   walrus's `InstrSeqBuilder`. Medium, incremental. `memo(table key build)` replaces the twenty hand-written
   find-or-insert maps in `G`, whose `funcType` keys are printed text. Then `codegen.mod.quest` (6,225 lines) splits
   along its banners, with `statement` passed as a closure to break the `body`/`operation` cycle.
3. **One emission layer for arm64.** Labels are strings, and label offsets are computed three times: by
   `relaxBranches` (a fixed point over `printer.count`), by `encode.unit`, and in the label maps. Integer labels and a
   MachBuffer-like module owning emission, binding, and fixups by branch range (Cranelift's `MachBuffer`, LLVM's
   `MCAssembler`), feeding one streamer with a text sink and an object sink (LLVM's `MCStreamer`, Go's `obj.Prog`),
   so alignment and layout are decided once rather than kept equal by `QUEST_CHECK_ENCODING`. Medium; asm text stays
   identical.
4. **A C AST behind the C printer.** Besides §4.3, whether a call may collect is decided on emitted text: an
   identifier before a parenthesis, or a closure's code pointer (`->fn))(`, added 2026-11-21 when the review found
   indirect calls missed), so a new way of calling must be taught to `callsFunction` and `_CALL_RE`. A small C expression and statement AST (or just Call nodes first) with `mayCollect(e)` computed
   from it (GHC's PprC printing Cmm, CompCert's Clight, MLton's C codegen). Large for the whole 3,370-line printer,
   staged.
5. **arm64 calling convention as data** (*checked*). `targets.Target`'s `arguments`, `results`, `scratch`,
   `stackAlign`, and `wordBytes` are never read; `select.placeArguments` hard-codes AAPCS64's counters,
   `resultRegisters` hard-codes `d0`/`x0`/`x1`, and `Lowering.scratch` is separate from `description.scratch`. An ABI
   record that `placeArguments` and the allocator's lowering both read (LLVM's `CallingConv.td`, Cranelift's
   `compute_arg_locs`), Darwin's narrow-argument packing staying code. Small to medium.
6. **Fusion matched once in arm64 selection.** The pre-pass that fills `fused`, `folded`, `indexOf`, and `shiftOf`
   matches bit tests, conjunctions, and zero tests, and `terminator` matches the same shapes again; the two must
   agree. A `BranchShape` (and `AddressShape`) computed once per block, or Cranelift's bottom-up lowering with
   `sink_inst`, which removes the pre-pass. Medium.
7. **Relocations in the JIT.** `jit/loader` duplicates the encoder's `field`/`shl`, re-decodes an instruction word to
   find a page offset's scale, and hand-encodes stub words. A per-kind relocation description shared with the
   encoder, the scale recorded on the relocation, stubs made by `encode.word` (BFD's `reloc_howto_type`, LLVM's
   `RuntimeDyldMachOAArch64`). Small.
8. **Small duplications.** `minst.isLogical` and `encode.bitmask` both compute logical immediates (LLVM's
   `processLogicalImmediate`); `ssac.jumpText` and the allocator each resolve parallel moves (regalloc2's
   `ParallelMoves`). Small.

## 7. Build System: Content Keys over File Times

1. **Early cutoff.** `modules/artifacts/fingerprint` hashes a `.qi`'s meaning, ignoring comments, layout, and order,
   but only the JIT uses it; staleness is decided by file times in `manifest.isManifestStale`,
   `paths.dependencyChange`, and `interfacecompiler.current`, and the `.qm`'s recorded `mtime` per interface is never
   read back. Record dependency fingerprints in the `.qm` and the `.qi`'s `deps`, stale when one differs: a comment
   edit in a widely imported interface then rebuilds none of its importers, and file-time fragility goes (GHC's `.hi`
   hashes, OCaml's `.cmi` CRCs, Shake and Bazel early cutoff, Go's content-keyed cache). Medium.
2. **One recorded key per artifact.** The currency rules are spread over `manifest`, `engine.artifactStaleness` and
   `importResolutionChange`, `interfacecompiler.current`, `paths.resolveInterfaceFile`/`dependenciesUnchanged`, and
   `abi.hasCurrentAbi`, with near-duplicate "now resolves to X" messages. An action key (ABI, producer, backend,
   source digest, import resolutions, dependency fingerprints) whose first differing component is the reason, one
   module owning [build-process.md](build-process.md) §5 (Bazel and Buck action keys, Shake's traces). Medium, with
   §7.1; every reason string must stay as it is.
3. **One schema for `.qi` and `.qm`.** A `.qi` is read four ways (`abi.recordedField`, `paths.recordedDependencies`,
   `interfacecompiler.qiRecord`, `fingerprint.ofQi`), missing fields quietly default to `""`, the schema exists only
   as a string, imports are packed as `"n1,n2=p1,p2:I"`, and `manifest` writes and reads JSON field by field. Quest
   types with one encoder and decoder each (rustc's `CrateRoot`, GHC's `Binary ModIface`). Medium.
4. **A build session record.** About ten settings travel through `engine.T` (rebuilt field by field), `workers.Job`
   (serialized to argv by hand, parsed back in `unitMain`), and eleven positional parameters of
   `compileModuleFile`; the environment is set up in both `driver/main.run` and `engine.compileMainUnit`. One
   `BuildSession` with `newEnv` and a `toArgs`/`fromArgs` pair (rustc's `Session`, clang's `CompilerInvocation`).
   Small to medium.
5. **A declarative option table.** `driver/options` is one if-chain with spellings inline, the usage text written
   separately, and `ssaPhases` copying `ssa/pipeline.passes`. A table of option specs generating the usage, with
   phase names from their owners (LLVM's `OptTable`, Go's `flag`). Small to medium; the usage must stay identical.
6. **Scheduling apart from bookkeeping.** `engine.unflushedBuildModules` is about 410 lines of closures: a queue, the
   discovered and expected tables, predicted imports, deferred log notes replayed in order, conformance checked twice,
   and cycle detection by linear scan (`preparedIndex` makes it quadratic). Tasks that report what they need when they
   finish (Shake's `need`, Buck2's dynamic outputs), a scheduler emitting events in deterministic order, and separate
   passes for conformance and cycles. Large; hash maps for `preparedIndex` and the cycle check first.
7. **Shared memo tables.** Six caches with their own invalidation (`graph.Resolver.memo`, `importPathsMemo`,
   `loader.loadedQis`, `fingerprint.known`, `compiledByQi`, `jsonCache.parseShared`) and a `compiling` stack saved
   and restored by hand; long-running processes (REPL, JIT, kernel) depend on them agreeing. One `fileMemo` keyed by
   path and stamp, the stamp a digest once §7.1 is in. Small; a Salsa-style query database is the large version, not
   needed yet.
8. **Build errors as diagnostics.** `engine.buildError` and `compilerRunner.failure` carry only text, so a cycle or
   interface mismatch cannot point at the import that caused it. `Diagnostic`s with the cycle as notes and an
   "imported here" label; later a clang-style file id plus offset in every location. Small to medium; wording
   unchanged.

## 8. Smaller Ideas

1. **An error type in the typechecker.** Any error aborts its enclosing binding, so one bad subexpression hides every
   later error in a large function. A `typeError` form that is sub- and supertype of everything and suppresses
   messages mentioning it, plus `exprError` (rustc's `TyKind::Error`, Swift's `ErrorType`, GHC's deferred errors).
   Medium to large, cheap after §3.1; multi-error output would be self-hosted only.
2. **Typed parser actions.** `syntax/parser/actions` reads positional `args[i]` 218 times, checked only at run time.
   Typed helpers per arity, or a record per rule. Small to medium; the grammar and error text stay as they are.
3. **A condition context in lowering.** `if` lowers its condition as a value, so `a andif b` materializes a Bool
   through a join that the simplifier straightens afterwards. A third context that emits branches (Appel's `Cx`, V8's
   `TestResultScope`), only if IR dumps or simplifier rounds show it matters.

## 9. Not Recommended

- **A rewrite DSL** (ISLE, Go's `.rules`, MLIR patterns): there is little algebraic simplification, and without
  macros the DSL would need its own code generator.
- **A generic block-level dataflow framework:** `barriers` is its only client in `ssa/`; reconsider if codegen's
  liveness would share it.
- **E-graphs,** at this size.
- **Pratt parsing or pretty-printer combinators:** byte-for-byte parity with the bootstrap's parser errors and IR
  text leaves little to gain.
- **A full Salsa-style query engine** now; §7.7's shared memo covers the present caches.

## 10. A Possible Order

1. Property tables (§2), starting with SSA opcodes and arm64 instructions.
2. The type and IR traversals (§3.1, §3.2 by hand), which make several later ideas cheaper.
3. `Plan` and `staticdata` as sum types (§4.1, §4.2).
4. The WebAssembly builder and symbolic references (§6.2, §6.1, with §2.4).

The build system's early cutoff (§7.1) stands alone and can be taken at any point.
