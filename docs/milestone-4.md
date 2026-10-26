# Milestone 4: The Self-Hosted IR and Its Interpreter

This plan ports the bootstrap's intermediate representation to Quest ([ir.md](ir.md)): lowering the typed AST to Core
IR (`bootstrap/python/quest/ir/lower.py`), the passes that refine it (specialize, closure-convert, represent,
describe), its printer and verifier, the reduced and canonical forms of types the passes use (`types/canonical`), and
the IR interpreter (`interpreter/ir_interp.py`), which runs each stage. At the end, the compiled self-hosted driver
dumps every stage as `quest --stop-after ir_STAGE` does and runs every program at every stage as `--stop-after
run_ir_STAGE` does, with the bootstrap's text. It follows Milestone 3 (the tree-walking interpreter,
[milestone-3.md](milestone-3.md)) and precedes Milestone 5 (C code generation, the build artifacts, and
self-hosting).

The decisions this plan rests on (2026-10-26):
- **Codegen's shared layer.** The passes use `codegen/layout` (how values are laid out: representations, views,
  slots), `codegen/descriptors` (type descriptors' holes and bound variables), and `codegen/syntax` (the C text
  vocabulary layout spells names with). They are ported in this milestone, under `questlang/codegen/`, where the
  bootstrap has them; Milestone 5 adds the C backend proper (`codegen/c`) beside them.
- **Checks.** The IR verifier (`ir/verify.py`, run when `QUEST_CHECK_IR=1`) and the canonical-form guard
  (`QUEST_CHECK_CANONICAL=1`, in `types/canonical`) are ported, and the driver runs them when the variables are set,
  as the runner sets them, as it runs `scoping` for `QUEST_CHECK_SCOPES`.
- **Runs.** The self-hosted suite runs every stage: the five dump phases (`ir_core` for every program, the later
  stages for the subsets that have goldens) and the five run phases (`run_ir_core` through `run_ir_described`) on
  every run golden and run-time error test, as the bootstrap's suite does.
- Carried over from Milestones 2 and 3: golden tests only, the full goldens run against the compiled driver,
  `questlang/` follows the bootstrap module for module, divergences only where Quest cannot hold what Python does
  (each documented where it is made), and the steps run straight through, each pushed when its runs pass.

---

## 1. Layout

```
questlang/
├── types/         canonical (completed: canonical forms and the guard)
├── codegen/       syntax, layout, descriptors (new; the C backend, codegen/c, is Milestone 5's)
├── ir/            shapes, nodes, walk, written, printer, slots, represent, describe, verify, lower, specialize,
│                  closure (new)
├── interpreter/   irinterp (new)
└── driver/        main (the ir_STAGE and run_ir_STAGE phases)
```

The layers, from the bottom: `types/canonical`; `ir/shapes`; `codegen/syntax` and `layout`; `codegen/descriptors`;
`ir/nodes` and `walk`; `ir/written`, `printer`, and `slots`; `ir/represent`; `ir/describe`; `ir/verify`; `ir/lower`
(above `typechecker` and `modules`), `specialize`, and `closure`; and `interpreter/irinterp`, above `treewalk`, whose
modules and builtins it shares.

### 1.1. Step 0's refactoring

`ir/slots.py` imports `may_be_stored_as_subtype` from `ir/represent.py` inside a function, and `represent` imports
`slots`: a cycle, which Quest's acyclic imports cannot hold. The function (and what it needs) moves down into
`slots`, which `represent` imports. The bootstrap's other lazy imports in these packages go one way (`verify` of
`describe`, `describe` and `layout` of `modules/abstract_types`, `ir_interp` of `treewalk`, `builtins`, and
`descriptors`), so they become ordinary imports. No output changes.

### 1.2. Representations

- **IR nodes** follow `ir/nodes.py` as the typed AST follows `typed_ast.py`: an option per family (atoms,
  operations, statements, addresses and stores, descriptors), tuples for the rest. A binder is a variable symbol with
  an id, so identity never depends on names.
- **Traversals** are `ir/walk`'s explicit tables (`fields_of`, `rebuild`, `contents`), case by case, as the bootstrap's
  self-hosting refactoring made them; the bootstrap's printer reads fields by reflection, and the Quest printer lists
  each node's fields explicitly.
- **Shapes** are interned as types are (`ir/shapes`), and the caches the bootstrap keys by a type's or shape's
  identity are hash maps keyed by its id.
- **The IR interpreter** runs on Milestone 3's values (`values/model`) and frames of its own, and calls the same
  builtins; its closures are builtins over IR functions, as the bootstrap's `_Closure` is.

---

## 2. Testing

### 2.1. The driver

`questlang/driver/main` gains `--stop-after ir_core|ir_specialized|ir_closed|ir_represented|ir_described`, which
prints the stage's dump as the bootstrap's printer does, and `--stop-after run_ir_core|...|run_ir_described`, which
lowers the program, runs the passes up to the stage, and runs the result in the IR interpreter, printing what the
bootstrap's IR run prints (the last phrase's result, or every phrase's with `--echo`). With `QUEST_CHECK_IR=1` the
verifier checks each stage's invariants after its pass, and with `QUEST_CHECK_CANONICAL=1` the canonical forms are
checked, as in the bootstrap's tests.

### 2.2. Runs

- **The self-hosted suite** adds the ten phases: the IR dump goldens (`tests/golden/ir_core`, 178; the later stages'
  subsets, about 18 each) and the run goldens and run-time error tests at each run stage. The pending list starts
  with all of them and is empty when the milestone is done.
- **The questlang tests** run compiled, and **the bootstrap's suites** run when a commit changes the bootstrap,
  `lib/`, or `runtime/` (Step 0 does), as before.

---

## 3. Steps

Each step is one or more commits; each ends with its runs passing.

### Step 0: Break the IR's import cycle

§1.1, in the bootstrap. Both bootstrap suites pass.

**Done when** the bootstrap's imports among `ir`, `codegen` (but `codegen/c`), `types/canonical`, and
`interpreter/ir_interp`, lazy ones included, are acyclic.

### Step 1: Canonical forms, shapes, and layout

Complete `types/canonical` (canonical forms of types, their graphs, the recursion binders, and the guard), and port
`ir/shapes`, `codegen/syntax`, `codegen/layout`, and `codegen/descriptors`. They are tested through the dumps of the
steps after this one, which print shapes and representations.

### Step 2: Core IR

Port `ir/nodes`, `walk`, `printer`, and `lower`, with the verifier's checks of Core IR, and add the `ir_core` phase to
the driver and the runner's self-hosted phases, with every IR phase's goldens and tests on the pending list. The
`ir_core` goldens leave it.

### Step 3: The IR interpreter

Port `interpreter/irinterp` and the `run_ir_core` phase. The run goldens and run-time error tests at Core leave the
list.

### Step 4: Specialize and closure-convert

Port `ir/written`, `specialize`, and `closure`, with their stages' verifier checks, and the `ir_specialized`,
`ir_closed`, `run_ir_specialized`, and `run_ir_closed` phases. Their tests leave the list.

### Step 5: Represent

Port `ir/slots` and `represent`, with the stage's checks, and the `ir_represented` and `run_ir_represented` phases.

### Step 6: Describe

Port `ir/describe`, with the stage's checks (the rest of `verify`), and the `ir_described` and `run_ir_described`
phases. The pending list is empty.

### Step 7: Done

Update compiler-organization.md (§2's "so far", §6's Milestone 4 status), ir.md (the self-hosted IR beside the
bootstrap's), and testing.md; record the divergences in this document.

---

## 4. Done When

- The compiled self-hosted driver passes every IR dump golden at every stage, and every run golden and run-time error
  test at every run stage, with `QUEST_CHECK_IR` and `QUEST_CHECK_CANONICAL` set, as the runner sets them.
- The questlang tests pass compiled; the bootstrap's suites pass.
- `questlang/` has the layout of §1, and the bootstrap's has no cycles among the ported modules.

## 5. Not in This Plan

- The C backend (`codegen/c`, `codegen/backend`, `codegen/symbols`), the build artifacts (`.qi`, `.qm`, headers), the
  build engine, and self-hosting (Milestone 5).
- A native backend, and the CFG and SSA stages it would add (ir.md §8.6).
