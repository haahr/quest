# Restructuring Plan

Carries out the structure suggestions of the 2026-11-06 comment review (§3 of `comment-review.md`): moves of modules
between directories, a few renames, one home for each duplicated helper, splits of the largest modules, and splits of
the runtime's largest files. Nothing here changes what a program does or what the compilers print, except where a
step says so.

**Decisions (2026-11-12).** All of §3, in the stages below. The bootstrap's files move with their self-hosted
counterparts, keeping the two trees parallel ([compiler-organization.md](compiler-organization.md) §2). File names
stay lowercase, new ones too; unit paths keep their camelCase (`questlang/modules/interfaceCompiler` is
`interfacecompiler.mod.quest`). Each stage passes the light check (§1); the full `tools/check` runs at the end (and
after stage 7, the runtime's), then the push.

---

## 1. Checking a Stage

A move breaks a build, not a behavior: an importer names the old path, a Python import fails, or a test imports a
compiler module by its path. What it cannot change, by what the inventory found, is a golden: no golden output names
any module this plan moves (the only module paths in goldens are `questlang/common/*` and `questlang/syntax/*`, which
stay). So a stage needs:

1. **The self-hosted fixed point** through arm64 (`run_tests.py --self-hosting --seed release --stage-backend arm64
   --fixed-point-only`): the release builds stage 1 from the tree, stage 1 stage 2, stage 2 stage 3, and stages 2 and
   3 must write the same code. Any self-hosted import the stage broke fails here.
2. **The bootstrap**: every module under `bootstrap/python/quest` imported, and the unit suite
   (`python -m unittest`), which drives most of the bootstrap.
3. **The tests that import compiler modules** (`tests/source/questlang/*`), compiled by stage 2.

The three run at once, as `tools/check --light` (stage 0 adds it), in about a quarter of the full check's time. They
miss what only the full check sees: the other backends, the stress modes, and behavior; the stages that change code
rather than move it (stages 5, 6, and 7) say what more they need.

A move renames the moved module's C symbols (`mangleModuleName`: `questlang/repr/layout` is
`questlang__repr__layout`) but not the scheme, so it needs no ABI bump. `tests/abi/inputs` is a frozen snapshot of
interfaces and is not updated.

---

## 2. Stages

Each stage is one or more commits, rebased onto `origin/main` as it lands; each updates the docs that name what it
moves (compiler-organization.md §2 and §5 above all).

### Stage 0. The light check

`tools/check --light` runs §1's three checks at once, reporting as the other suites do. A tooling change: its unit
tests only.

### Stage 1. Utilities to their homes

| Unit | To | Bootstrap |
|---|---|---|
| codegen/sha256 | common/sha256 | none (hashlib) |
| values/json | common/json | none (the json module) |
| codegen/c/compilerRunner | build/compilerRunner | codegen/c/compiler_runner.py → build/compiler_runner.py |
| ir/whole | driver/whole (its one importer is driver/main) | none |

First, because stage 2's representation directory imports sha256.

### Stage 2. A backend-neutral representation directory

codegen/layout, codegen/descriptors, ir/shapes, ir/written, codegen/runtimeLayout, codegen/objectLayout, and
codegen/staticdata are the representation of values in memory, which the IR passes, the SSA, and both backends use;
they move to **`questlang/repr/`**, and the bootstrap's counterparts (layout, descriptors, shapes, written,
objectlayout) to `bootstrap/python/quest/repr/`. So do codegen/symbols (the names units link against), codegen/syntax
(the spelling of C text, which layout's struct names need), and codegen/externals (the library's external C
functions), which ir/, ssa/, and the representation import too. codegen/runtimeFunctions, used only by ssa/, moves to
**`ssa/runtimeFunctions`**. ir/ and ssa/ then import nothing from codegen/, and codegen/ imports them: the layering
§5 of compiler-organization.md describes. About 100 import lines change (shapes alone has 38 importers, layout 21).

### Stage 3. The two Backend modules

codegen/backend (the IR passes' pipeline) becomes **ir/pipeline**, as ssa/pipeline is the SSA's; then
codegen/c/backend (which dispatches c, ssac, and arm64) becomes **codegen/backend**, with an exception of its own,
`backend.unsupported`, which driver/main and modules/moduleCompiler catch in place of `printer.unsupported`. The
bootstrap's codegen/backend.py and codegen/c/backend.py move the same way (it has no re-raise to replace).

### Stage 4. Directories

- **ssa/passes/**: escape, promote, constants, valueNumbers, selects, accumulate, tailCalls, tailJumps, interrupts,
  allocations (2,920 lines), as ssa/build/ holds the SSA's construction; ssa/ keeps the representation and its tools.
- **codegen/machine/**: target, machine, regalloc (1,973 lines), the machine-independent half of a native backend,
  which arm64 uses; **ssac** moves to codegen/c/ssac, beside the printer it shares the C runtime with.
- **modules/artifacts/**: interfaceCompiler, moduleCompiler, manifest, fingerprint, the code that writes and reads
  `.qi`, `.qm`, and objects, apart from modules/' loading and resolving; the bootstrap's interface_compiler,
  module_compiler, and manifest likewise.
- **Lowercase file names**: the units this plan moves get lowercase file names as they move (objectLayout,
  runtimeLayout, runtimeFunctions in stage 2; valueNumbers, tailCalls, tailJumps here); common/memoryFiles and
  jit/debugObject, which stay where they are, are renamed in place. Their unit paths are unchanged.
- **typechecker**: scoping's walk of the typed tree (children, bindingChildren, letValues) moves into typedAst;
  escape's auto-value helpers into autoValues; lvalues and metas fold into application, in both compilers.

### Stage 5. One home for each duplicated helper (code changes)

The review's items 4 and 5, after an inventory of every copy (2026-11-12), which found some copies identical, some
differing, and some claimed duplicates not to be. Given one home, their callers calling it:

- syntax/ast's effectiveModulePaths and effectiveInterfacePath (8 copies in 4 modules), as the bootstrap's
  ast.ImportItem has them. elaboration's copy also took present but empty module paths as absent; the grammar never
  makes such an import, so every copy agreed on every import there is.
- moduleCompiler's interfaceRef (build/engine's was the same); modules/paths's stem (build/engine's and driver/main's)
  and lastSegment (loader's differed only on a trailing slash, which canonical names never have); elaboration's
  declareTypesAndKinds (interfaceCompiler's took its arguments in the other order); interfaceCompiler's `.qi` field
  readers (fingerprint's were the same).
- repr/shapes's isViewedKind (3 copies) and isFunction (4), repr/layout's heldShape (2); ssa/nodes's typeCode and
  typeOfCode (scalars's were the same) and definitions (3 passes built the table the same way); ir/walk's unitBodies
  (simplify's and slots's lists of a unit's bodies).
- common/pyRepr: Python's repr of strings (diagnostics's, and staticdata's, written again), lists (loader's), tuples
  and lists of items (staticdata's), and integers (scoping's).
- values/model's isVisited and joined (interpreter/formatting's were the same); types/model's powerBoundOf
  (subtyping's namedBound and canonical's were the same).
- irinterp's isOneOf, which nothing called, removed.

Left as they are, and why:

- The functions that find the call a statement makes (simplify, contify, inline) and that rewrite returns (inline,
  contify) or jumps (simplify): each does something different.
- The two caches of a unit file's text (modules/paths, modules/elaboration): they look for different things.
- The defining-instruction tables that also record blocks, indexes, or uses (arm64/select, barriers, verify, scalars,
  escape); the lists of a unit's bodies that start with main (thunks, walk's knownClosures) or pair each body with its
  function (verify).
- intEqual (`a is b`, about 37 copies) and the isOneOf functions: one line each, not worth an import.
- The interpreters' resolveType: the same steps on two different frames.
- The C printer's isFunction and heldShape, which go through its own cached shapeOf; build/engine's quoted and
  pyList and the tokenizer's charRepr, which are not Python's repr and print what the bootstrap's messages print.
- The functions that expose a type's head, which differ in what they look through: canonical's interface lists them
  and says when to use which.

Besides the light check: the self-hosted compiler's whole suite (the self-hosting check), since messages and dumps
that print with these helpers are checked there; the bootstrap is unchanged.

### Stage 6. Splits of large modules

Each split follows the banners already in the module, so it moves code without changing it:

| Module | Split out |
|---|---|
| codegen/c/printer | proxies, aggregates, and conversions; unit assembly; the shared state (P, FnState) first |
| ir/lower | the REPL's phrase units; the capturedMutables pre-pass |
| types/canonical | head reduction and option queries → types/reduce (with stage 5's heads) |
| values/dynamicJson | the type graph and canonical table; the writer; the reader |
| codegen/arm64/codegen | the peephole passes (relaxBranches, pairs); frames and stack maps |
| repr/layout | printed types and digests; generic-layout agreement |
| typechecker/aggregates | tuples → typechecker/tuples |
| driver/main | option parsing → driver/options; binary error parsing |
| ir/verify | representationProblems; descriptorProblems, itself split by banner |
| ssa/build/values | representation, slots, components → ssa/build/representation |
| driver/repl | the Jupyter protocol → driver/kernel |
| modules/paths | generic file operations → common/files |
| build/engine | unflushedBuildModules into staleness, waves, conformance, and cycles |
| codegen/c/headers | build freshness and writing → build/ |

The bootstrap's counterparts split the same way where they have the same seam; where the bootstrap's module is
organized differently, the split is the self-hosted compiler's only, and compiler-organization.md §6 says so.

Left whole (decided 2026-11-12), because no split of them moves code without changing it:

- **codegen/c/printer.** Its sections share the printer's state (P, FnState) and a few dozen helpers (names, C types,
  descriptors, emitting). A lower module of them would export some 40 names, which the printer's other 2,700 lines
  would then all qualify, and the unit assembly, split upward, would need 19 of the printer's internals exported.
- **ir/lower's REPL phrase units.** phraseExpr and echoBinding are members of lowering's recursive group, and
  lowerPhrases uses most of the lowerer's internals (newLowerer, binding, emit, inBody, lowerModule): a module of
  them would need the lowerer's state exported.
- **codegen/arm64/codegen's frames and stack maps.** Their definitions (the frame's slots and layout, the frame
  maps, the unit's frame table) lie in three of its sections, with no seam between them and the rest.
- **build/engine's unflushedBuildModules.** One 425-line function, not sections: dividing it into staleness, waves,
  conformance, and cycles is a rewrite of the build's main loop, not a split.

### Stage 7. The runtime's files

- quest_runtime.c (4,665 lines) into quest_exceptions.c (exceptions, the stack guard), quest_print.c (printing,
  echo), quest_types.c (descriptors, subtyping, the run-time constructors), quest_views.c (views, proxies,
  conversions, templates, view maps), quest_os.c and quest_stdlib.c (the library's natives), its banners corrected;
  each file with static roots registers a roots callback, as quest_serialization.c does.
- quest_gc.c's checking modes (~870 lines) into quest_gc_check.c, behind quest_gc_internal.h.
- quest_runtime.h an umbrella over quest_gc.h and quest_types.h: the header's digest changes, so ABI bump.

Every list of the runtime's sources changes (both compilers' compiler runners, the JIT's, the release's snapshot), so
this stage runs the full `tools/check`, not the light one.

### Stage 8. lib/ and tools/

- util/path's T and its file-system functions move to os/ (os/path), leaving util/path the string functions; the
  library's file-system operations, now in system, os/fileStats, and path, are listed in one place in its docs.
- tools/'s four identical launchers that find Python share one helper.

### Stage 9. The bootstrap's own

- testing/runner.py (1,552 lines): self-hosting (with releases.py) and transcripts in modules of their own.
- quest_driver.py: its argument parsing apart from its dispatch, and quest/driver/main and quest/driver/repl, as
  questlang has.
- The layout to questlang's where it differs: diagnostics.py → common/diagnostics.py, syntax/sources.py →
  common/location.py, ast.py's ast_dump → syntax/astprint.py, typed_ast.py's printer → typechecker/typedastprint.py.
- quest/__init__.py's unused re-exports, and the dead classes, removed.

### Stage 10. Finish

compiler-organization.md's tree and layers (§2, §5) as they now are, the full `tools/check`, the push, and a release.
This document is then deleted, what it decided recorded in compiler-organization.md.
