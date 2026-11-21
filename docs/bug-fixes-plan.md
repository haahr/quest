# Bug Fixes Plan

A plan to fix every bug in [tasklist.md](tasklist.md) as of 2026-11-20, in an order chosen so that the confirmed
faults go first, steps touching the same files go one after another, and investigations that may find nothing go
last. Delete this plan when its last step lands, as each step deletes its task.

**Status, 2026-11-21:** steps 0, 1, and 3 to 8 are done. Step 2 (the bootstrap's static adapters) is being done in
another session; this plan goes when it lands. Step 8 found two faults and fixed them (an unassigned out argument,
and wasm's auto record components); its third report, the JIT's, is a task of its own.

## 1. The Task List, Sorted

**Bugs** (a program goes wrong, or could, or a build is not reproducible):

| Task | Status | Compilers |
| :--- | :--- | :--- |
| Closures made in a `for` loop share the loop variable | confirmed, in both treewalks only; being fixed | both |
| An interface may declare a member twice | confirmed | both |
| The bootstrap's C gives a converted known function a new adapter | confirmed | bootstrap |
| The C printer decides where a collection can happen by reading its own C | latent: no wrong barrier known | both |
| A failed subtyping alternative leaves its metavariables solved | latent: no program known | self-hosted; bootstrap? |
| The IR's renaming walk misses descriptors that cloning copies | latent: may be safe by stage order | self-hosted |
| `selects` reads predecessors after changing terminators | latent: safe by an unstated argument | self-hosted |
| The arm64 fixed point's stages 2 and 3 are different binaries | confirmed, harmless to output | self-hosted |
| Faults the wasm review reported that no probe reproduced | unconfirmed | self-hosted |

**Potential improvements** (nothing goes wrong; the code could be faster), not in this plan:

- A function value converted to a supertype allocates its adapter's closure every time (allocation, 4.6 percent of
  the compiler's build): done, [benchmarks.md](benchmarks.md) §34.
- `maybe.T` is abstract, so every test of one in another module is a call (instructions per use).

The ideas in [compiler-refactoring-ideas.md](compiler-refactoring-ideas.md) are improvements too; several steps
below name the idea that would remove their bug's cause for good, but take only the fix.

## 2. Order

Confirmed faults that change what a program does come first, smallest first. The two C-printer steps go together,
since both change `bootstrap/python/quest/codegen/c/printer.py`. The typechecker and IR invariants follow, each needing
a probe before a fix; then the two investigations, which may end in a note rather than a change.

0. Closures in a `for` loop (in progress in this session: both treewalks fixed, `language/for_closures` written).
1. An interface may declare a member twice.
2. The bootstrap's C adapter for a converted known function.
3. Barriers from what the C printer called, not from its text.
4. Metavariables solved in a failed subtyping alternative.
5. The IR's renaming walk and descriptors.
6. `selects` and its predecessors.
7. The arm64 stages' differing binaries.
8. The wasm review's unreproduced faults.

## 3. Steps

### Step 1. An interface may declare a member twice

**Probe.** The smaller case first: an interface declaring `f` twice, with different types, and a module defining
both; `./quest --stop-after typecheck` and `./questboot --stop-after typecheck` should both accept it today. Then
the same with two types, and two exceptions, to see which duplicates are already caught.

**Fix.** In both typecheckers' checks of an interface's declarations (`questlang/typechecker/`, and
`bootstrap/python/quest/typechecker/`), reject a member name declared twice, with one message and position (the
second declaration) in both; and, if a module may still define a name twice to match, the module's lets against its
interface too.

**Tests.** Error tests under `tests/errors` (shared goldens, written by the bootstrap): a repeated member, and a
repeated member with the same type. The self-hosted suite must give the same text.

### Step 2. The bootstrap's C adapter for a converted known function

**Fix.** In `bootstrap/python/quest/codegen/c/printer.py`'s `convert` (`case "adapt"`) and `adapter`: for a known
function, or an imported member, emit a static closure of an adapter that calls it directly, as the self-hosted
compiler's `ir/thunks` does, so converting the same function twice gives the same closure.

**Tests.** A shared run test, `language/adapter_identity` say: the task's `same(:Int own own)`, an imported function
(`sort.intCompare`), and one converted at two different types, comparing with `is`; the same answer in every phase,
`interpret` and `run_ir_*` included. The bootstrap's ABI corpus may change (its own goldens).

### Step 3. Barriers from what the C printer called

Both C printers find calls by scanning each emitted line (`callsFunction` in `questlang/codegen/c/printer.mod.quest`,
`_CALL_RE` in `bootstrap/python/quest/codegen/c/printer.py`).

**Probe.** Log, under a temporary flag, every line either printer emits that `callsFunction` or `_CALL_RE` judges a
call and every call the printer makes, over the whole suite and the compiler's own build; any call it makes whose
line does not have the shape is the fault the task describes. Run the stress tier (`tools/check --stress`) as it is
for a baseline.

**Fix.** Each printer counts a possible collection where it emits a call (its call, runtime call, and allocation
helpers), and `emit` stops reading text: the first step of compiler-refactoring-ideas.md §6.4. A line the printer
writes as text and that calls (a macro that allocates, say) must go through one of those helpers.

**Tests.** The C goldens (`codegen_c` and the self-hosted C dumps) and the ABI corpora unchanged, unless the probe
found a missed barrier, in which case the change at that site is the fix and a stress run of a program that reaches
it is its test; the stress tier passes.

### Step 4. Metavariables solved in a failed subtyping alternative

**Probe.** A program where the bound's proof in `subtyping.step` solves a metavariable and then fails, so that the
structural fallback, or a later field, sees the solution: a type variable bounded by a type that matches a
metavariable's first use but not the goal. Typecheck it with both compilers; check whether the bootstrap's
`is_subtype` tries the same alternatives (`bootstrap/python/quest/types/subtyping.py`, where solutions are assigned
at lines 362 and 368).

**Fix.** If the probe goes wrong: a trail of assignments with `mark()` and `undoTo(mark)`, assignments recorded in
`subtyping.solve` and `model`'s path compression, and `step` undoing to its mark when an alternative fails; the same
in the bootstrap if it has the shape. If no program can go wrong, a comment at `step` that says why.

**Tests.** The program as a shared typecheck or run test, the same in both compilers; the typecheck goldens
otherwise unchanged.

### Step 5. The IR's renaming walk and descriptors

**Probe.** `walk.replaceVarsInStmt` has two callers, `ir/closure` and `ir/simplify`; at which stages each runs
relative to `describe`, which attaches the descriptors `mapInStmt` skips.

**Fix.** Rename the skipped fields in `mapInStmt` (an `sRaise`'s `descriptor`, an `sInspect`'s `witness` and its
cases' descriptors) as `clone` copies them, which costs little and needs no argument about stages; and a comment
there that it covers every variable `clone` copies.

**Tests.** The IR goldens unchanged; `run_ir_*` and every backend unchanged. The bootstrap reflects over fields, so
it has no counterpart.

### Step 6. `selects` and its predecessors

**Fix.** Confirm that `convert` rewrites only its own block's terminator and that an arm `through` accepts has one
predecessor, the block being converted; then state that argument in a comment at `selectFunction`. Recompute the
graph only if the argument fails.

**Tests.** The ssa goldens unchanged (`run_tests.py --self-hosted --phase ssa`).

### Step 7. The arm64 stages' differing binaries

**Probe.** Build stages 2 and 3 through arm64 (`run_tests.py --self-hosting --fixed-point-only --stage-backend
arm64`), keep both binaries, and compare them: `cmp -l` for where, `otool -l` for `LC_UUID`, `dwarfdump` for paths,
and the linker's input order.

**Fix.** Whatever differs: a path made relative or fixed, objects given to the linker in a fixed order, or a UUID
made from content (`-no_uuid` is not wanted, since lldb uses it). If it cannot be made the same, the note in
`bootstrap/python/quest/testing/selfhost.py` says what differs and why that is harmless.

**Tests.** The fixed point through arm64 reports the same binary, or the new note.

### Step 8. The wasm review's unreproduced faults

**Probe.** One program for each of the three: an `out` argument needing a conversion that the callee does not
assign; subsumption of an auto value with a covariant record component; and the JIT's unbound `qj_1_record`, from the
review's description. Run each compiled, by the JIT, on wasm, and by both interpreters.

**Fix.** A fault that shows is fixed with its program as a shared run test. One that does not is dropped from the
task list with a line in the task's place in [wasm.md](wasm.md) saying what was tried. Stop after a day's probing.

## 4. Testing and Pushing

Each step is one commit, with its task removed from tasklist.md in the same commit. A step that changes a compiler
runs `tools/check` before its push; steps 5 and 6 are small enough to share one check. Steps that change only a
comment (6, if the argument holds) need no suites. Every fix of shared behavior (steps 1, 2, 4, 8) lands in both
compilers in the same step, with its test in a shared phase, under the two-compilers policy. Push after each step's
check passes; a release is cut after steps that change what the compiler builds (2 does not, being the bootstrap's;
3, 4, and 5 may) when useful.
