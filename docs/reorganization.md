# Compiler Reorganization Plan

This document plans a reorganization of the bootstrap compiler (`bootstrap/python/quest/`) and the C runtime, now
that C is compiled through the IR ([ir.md](ir.md)). It separates the complexity that the language requires from the
complexity that comes from design choices and from the compiler's organization, and orders the work that reduces the
latter: a preparatory phase, then three tracks that can proceed in parallel.

---

## 1. Where the Complexity Comes From

**Inherent in the language.** No reorganization removes these; every implementation pays for them:

- the type system: kinds, type operators, bounded quantification, power kinds, and equi-recursive types
  (`types/`, `typechecker/elaborate_types.py`, contractiveness, canonical forms of recursive types);
- types used at run time (`Dynamic`, auto types, `inspect`, echo), so types cannot be erased: descriptors, templates,
  and a run-time subtype check and converter;
- structural subtyping with first-class polymorphism: a value must be usable at a supertype and in generic code;
- tuples with type components, path types, and auto types: escape analysis and existential packaging;
- modules with abstract types and separate compilation: serialized interfaces, abstract types' identity across
  units, staleness;
- `var`/`out` parameters and mutable components interacting with subtyping.

**From design choices.** These could be made differently, at a cost:

- **records and variants whose values depend on their static type** (a record carries the offset table of the type it
  is viewed at, a variant its tag in that type's numbering), 16 bytes natively but one `QVal` word in generic code.
  This is the largest source of complexity in the backend: most of `codegen/layout.py`, the represent pass's
  conversion plans, the runtime's `quest_convert` and `quest_layout_equivalent` and the differential test between
  them, shadow cells, rejected conversions, and the identity limitation. Phase 0a decides how to change it;
- two interpreters, and Python implementations of every external, as independent oracles for each other;
- readable, structured C;
- the self-hosted copy of the front end in `questlang/` (temporary, by design).

**From the compiler's organization.** Tracks A to C below address these:

- the C printer still makes representation decisions (auto values, `inspect` arms, bounded type parameters' views,
  `type_app` thunks, adapters) and materializes descriptors, contrary to [ir.md](ir.md) §8.5;
- below lowering, represent, `layout.py`, the C declarations, and the printer work on raw types, normalizing them
  again and again (`strip_aliases`, `normalize_type`, `beta_reduce`), where shapes were meant to be the only view;
- `typechecker/typecheck.py` (3,349 lines) pairs a check and a synthesis function for most constructs, with much
  overlap, and desugars as it checks;
- modules are loaded along separate paths for the interpreter (`load_module_for_interpreter`), the compilers
  (`module_compiler`, `BuildEngine`), and the driver, and interface loading reaches the C backend;
- `codegen/canonical.py` is type theory living in the backend;
- the IR interpreter imports the tree-walking interpreter's private functions.

---

## 2. Phase 0: Preparation

Phase 0 lands before the tracks start. Its items are independent of one another.

### 0a. Representation of records and variants in aggregates

**The problem.** A record value is a `QRecordVal` (payload pointer and the offset table of its view), and a variant a
`QVariantVal` (tag in its type's numbering and payload), each 16 bytes, stored inline in tuples, option payloads,
records, and arrays. Two situations then force an aggregate to be rebuilt:

1. **Polymorphic boundaries.** Generic code stores a type parameter's value as a `QVal` word, which holds a record or
   variant only boxed. Native `Tuple x: P end` (16-byte slot) and generic `Tuple x: A end` (8-byte slot) disagree in
   memory, so a call converts by copying (`copy` and `runtime` plans, `quest_convert`), or rejects the call when the
   copy would not share mutable data (an array of records, a tuple with a `var` component of the parameter).
2. **View changes.** Upcasting `Tuple x: Big end` to `Tuple x: Small end` (or a tuple of variants to a tuple of a
   supervariant whose cases are numbered differently) changes the representation of an immutable component, so the
   tuple is copied, even with no polymorphism. The copy is a different object, so `is` differs from the interpreter,
   and a copy of a tuple with `var` components does not see later updates: with
   `let s: Tuple x: Small var n: Int end = t`, `t.n := 1` leaves `s.n` at 0 in C (1 interpreted). This is a
   miscompilation ([tasklist.md](tasklist.md)).

Records already avoid case 2 for record fields: a record's offset table lists, per field, the type the payload stores
it at when that differs from the view's (depth subtyping), and reads of such a field convert it
(`quest_record_dict`, `QRecordStoredTypes`). Upcasting a record never copies its payload.

**Decided: box records and variants in aggregate slots.** Every slot of an aggregate (tuple component, option
payload, record field, array element, auto payload) and every `QVal` word holds a record or variant as a pointer to an
immutable 16-byte box, so native and generic layouts agree in memory for every type. Locals, parameters, and results
stay unboxed, so field access is unchanged.

Consequences:

- A polymorphic call converts aggregates by pointer cast only. The `copy` and `runtime` plans at polymorphic
  boundaries disappear, `generic_layout_agrees` and `quest_layout_equivalent` become trivial (and the differential
  test with them), and the identity limitation at polymorphic calls goes away.
- Rejected conversions at polymorphic calls disappear: arrays of records and tuples with `var` components of a type
  parameter pass to generic code by cast.
- Specialization becomes a pure optimization: its trigger no longer has to avoid conversions, only slow paths.
- Costs: storing a record or variant into an aggregate allocates a 16-byte box (building a tuple of records, consing
  a list of variants, an option holding a record), and reading one adds an indirection. Boxes are immutable, so a box
  read from one aggregate can be stored into another without reallocating when the view is unchanged; the represent
  pass can keep the boxed form alongside the unboxed one to do so.
- Shadow cells remain for `var` arguments whose location is an unboxed local passed to a generic `var` parameter.
- The C structs of aggregates change, and so do descriptors' slot kinds, `quest_slot_read`, and `quest_convert`:
  an `ABI_VERSION` bump. The dynamic format and `.qi` files, which are type-level, do not change.

Boxing alone does not address view changes (case 2): the box holds the view, so an upcast that changes a component's
view still rebuilds the aggregate.

**Decided: views on tuples and options (V1).** The candidates considered, each keeping records' and variants'
16-byte values and evidence passing:

- **V1. Views on tuples and options (chosen).** Generalize records' stored types to tuples and options. A tuple
  or option whose type is *view-sensitive* is represented as a pair, like a record. A type is view-sensitive when
  values of its subtypes can be represented differently at it, which is a matter of subtyping, not polymorphism:
  a tuple or option type is view-sensitive when one of its immutable components (`var` components are invariant) is
  a record or variant, a type parameter bounded by one, a function whose signature mentions a view-sensitive type
  or one of the tuple's own type components (whose C signature changes when packed), or a view-sensitive tuple or
  option. `Tuple x: Int y: String end` and `Tuple x: A end` (unbounded `A`, whose values are uniform words or boxes)
  are not; `Tuple p: Point end` and `Tuple f: Fun(x: Small): Int end` are. The pair is its
  pointer and a view, the descriptor of the type its components are stored at, or NULL when that is its static type.
  An upcast keeps the pointer and sets the view to the source's view, or to the source type's descriptor when that is
  NULL: no allocation, no lookup, no copy. Reading a component through a non-NULL view converts it from its stored
  type: a record by the existing `(view, layout)` offset-table map, a variant by a tag table found the same way, a
  nested tuple or option by passing the view down (free), and a function by an adapter.
  - Fixes identity and lost updates for every upcast; nothing is copied.
  - Types that are not view-sensitive (tuples of scalars, strings, arrays, and other insensitive types) keep their
    one-word representation, decided statically from the type.
  - Costs: view-sensitive tuples and options are 16 bytes (in aggregate slots, boxed like records); each component
    read checks the view for NULL; reads through a view look up tables per descriptor pair, as record upcasts
    already do; a function component read through a view allocates an adapter on each read, which matters for
    tuples used as objects or packages viewed at a supertype.
- **V2. Static witnesses on tuples and options.** As V1, but the view is a static witness table for the upcast
  (per component: an offset-table map, a tag map, an adapter), built at compile time when the source view is NULL.
  Reads apply the witness without lookups. Upcasting a value that already has a witness needs the composition of two
  witnesses: a small allocated witness chaining them (reads apply the chain), or a memo table of compositions.
  Fewer run-time lookups than V1 in the common case, at the price of composition and of witness tables per upcast
  site.
- **V3. Reject.** Keep copying for view changes, reject statically any view-changing upcast of an aggregate that
  holds `var` components (directly or nested), and document that `is` can differ for immutable ones. Least work,
  rejects programs the interpreter runs, and leaves the conversion machinery for view changes in place.

A2 implements boxing and V1 together.

### 0b. Performance baseline

`tests/perf/baseline.json` dates from before the IR (`cf47e75`), and its three benchmarks barely exercise records
and variants. Add:

- a record benchmark: field reads and writes in hot loops, including records viewed at supertypes and records stored
  in tuples and lists;
- a variant benchmark: construction and `case` dispatch, with scalar and aggregate payloads, including upcasts;
- a real program: the self-hosted `questlang` tokenizer and parser compiled with the C backend, timed over the test
  corpus.

Then save the baseline at the current commit. **Performance bar for A2:** at most a 10% slowdown on any benchmark;
beyond that, optimize before landing.

**Done when.** The new benchmarks are in `tests/perf`, `measure.py` runs them, and the baseline is saved.

**Done:** `record_fields`, `variant_dispatch`, and `questlang_tokenizer` (the self-hosted tokenizer over a fixed set
of sources; there is no self-hosted parser yet), with the baseline saved after them. Against the previous baseline,
the pre-IR emitter's, `generic_lists` runs 1.20x as long; it was 1.13x when the IR became the C backend, within that
step's 20% bar, and has drifted since.

### 0c. Move `codegen/canonical.py` into `types/`

Mechanical: the reduced and canonical forms of types belong with the types. Imports follow.

**Done:** `types/canonical.py`.

### 0d. Share the interpreters' primitives; fix top-level rebinding

Move the primitive operations the IR interpreter imports from `interpreter/treewalk.py` (`_eval_int_arithmetic` and
the others) into a shared module, and fix the top-level rebinding task ([tasklist.md](tasklist.md)), whose cause is
the tree-walker's environment model.

**Done:** `interpreter/primitives.py` (arithmetic, comparisons, the standard library's runtime errors) and
`interpreter/formatting.py` (printing values by their types). Blocks, programs, modules, and REPL inputs evaluate
bindings with one rule (`eval_scoped_binding`): a binding that rebinds a name of the current frame gets a new frame,
which later phrases continue in, so closures built earlier keep what they captured
(`tests/source/language/top_level_rebinding.quest`).

### 0e. Bugs found while planning

Recorded in [tasklist.md](tasklist.md): the lost update after a view-changing tuple upcast (fixed by A2, per 0a),
and `is` between tuples of different types, which produces C that does not compile. **Done.**

---

## 3. Track A: Backend

Sequential: each step builds on the one before. This is the critical path.

**A1. Representations from shapes.** `layout.py` computes representations and layouts from shapes, cached per shape;
represent, `codegen/c/declarations.py`, and the printer use shapes, not raw types. Done when no code below lowering
calls `strip_aliases`, `normalize_type`, or `beta_reduce`, and goldens are unchanged.

**Done,** with these uses of the types as written remaining, each for a reason shapes cannot serve:

- the represent pass's `written_structure` and the signatures of function types (`collect_fun_quantifiers`, in
  `types/canonical.py`) in the represent pass and the printer's thunks: the variables the pass makes are printed
  with alias names, and the symbols of a function type's own type parameters, which call sites' type arguments and
  descriptor parameters are keyed by, are those of the type as written (a canonical form names binders afresh);
- echo of packages in the printer, which prints the type as written;
- `collect_aggregate_types` in `codegen/c/declarations.py`: the order of struct declarations, which interfaces' C
  headers pin (`tests/abi`), and record names follow the types as written (a canonical form may write the fields'
  types differently, naming the value parameters of equal function types alike), so moving it to shapes needs an
  `ABI_VERSION` bump.

Recording the written component types on IR operations at lowering would remove the first.

**A2. The representation change (0a).** Boxing in aggregates, and views on view-sensitive tuples and options, in
`layout.py`, the represent pass's plans, the runtime (`quest_convert`, `quest_layout_equivalent`, slot reads), and the
conversion matrix. Done when the matrix's identity column and the lost-update test pass in C, the rejected
conversions that boxing makes unnecessary are accepted, `ABI_VERSION` is bumped, and the benchmarks are within the
bar.

**A3. Representation decisions out of the printer.** Auto packing (`make_auto`), `inspect` arm conversions
(`auto_arm_converted`, `auto_layouts_agree`), bounded type parameters' views (`bounded_param_in_scope`), `type_app`
thunks, and adapters become `convert` plans or IR operations decided by represent. Done when the printer calls neither
`quest_convert` nor `layout.py`'s judgements on its own, and [ir.md](ir.md) §8.5 holds.

**A4. Descriptors as an IR pass** ([ir.md](ir.md) §8.4). A pass after represent makes descriptors IR values, and a
fifth stage (`ir_described`) is dumped and verified. Done when the printer prints descriptors it is given and creates
none.

A2 comes before A3 so that A3 ports only the plans that survive the representation change.

---

## 4. Track B: Front End

Independent of track A. Do it before porting the type checker to `questlang`, so the port starts from the smaller
structure.

**B1. Split `typecheck.py`** into files by construct family (bindings and functions, aggregates, control flow,
exceptions and `inspect`, application), with no change in behavior.

**Done:** `TypeElaborator` in `typecheck.py` keeps its state, the dispatch, the shared helpers, and the entry points,
and combines one mixin per family: `bindings.py`, `application.py`, `aggregates.py`, `control.py`, `exceptions.py`,
and `auto_values.py`.

**B2. Merge check and synthesis pairs** construct by construct, where checking is synthesis followed by subsumption
except for what the expected type propagates into.

**Done:** each construct the expected type flows into has one method, `_elaborate_X_expr` with an optional
expected type, which `check_expr` and `synth_expr` both call: if, block, fun, record, tuple, array, array
repetition, case, raise, try, inspect, auto values, and applications (`_elaborate_app_expr`); every other
expression is checked by synthesis and subsumption ([type-system.md](type-system.md) §6.1). Checking against a
polymorphic type stays separate (`_check_polymorphic_fun_expr`), since it renames the expected quantifiers. The
closure capture check is one helper (`_check_capturable`). No golden or error output changed; where the modes
differed visibly (the order of errors, the minting order of symbol ids, the escape checks that only synthesis
makes) the merged methods keep the difference.

**B3. A desugaring pass** between parsing and type checking: `andif`/`orif`, user infix operators as calls, `elsif`
chains. Typecheck dumps may change; error messages must still point at and name the source syntax.

**B4. Canonical recursive types at construction (experiment).** Prototype building canonical forms when types are
made, so that type equality is identity; measure type checking time and the code it removes (the subtyping cache,
`QUEST_CHECK_CANONICAL`), and adopt it only if it pays. After 0c and B1 to B3, since it touches `types/model.py` and
subtyping.

---

## 5. Track C: Units, Modules, and the Driver

Independent of tracks A and B.

**C1. Interface loading without the C backend.** The existing task ([tasklist.md](tasklist.md)): C compilation
writes the `.int.h` headers it needs, and `interface_compiler.py` no longer imports `codegen/c/`.

**Done:** `codegen/c/headers.py` writes headers beside their `.qi` files: compiling an interface file writes both
(`compile_interface_with_header`), and compiling a module brings its interface's header up to date
(`ensure_imported_interface_header`, from `module_compiler.py` and the pipeline's `codegen_c` phase). A header is up
to date when it is at least as new as its `.qi`; a missing or stale one is written without rewriting a fresh `.qi`
([build-process.md](build-process.md) §5.3). Builds no longer write headers for interfaces that only a main routine
loaded, which nothing includes. `test_dependencies.py` checks that only C compilation and the pipeline's clients reach
`quest.codegen.c`, through any chain of imports.

**C2. One graph of program units.** Resolution, type checking, and artifacts in one structure, replacing
`load_module_for_interpreter`, the driver's two places that dispatch on file suffixes (default and `compile` mode),
and the separate paths through `module_compiler` and `BuildEngine`, building on the unit-file checks
`quest/modules/units.py` shares.

**Done:** `quest/modules/graph.py` ([build-process.md](build-process.md) §2.1). A `Resolver` resolves each import
(path, directory, roots) once per session to a `Resolved` (source, prebuilt `.qi`, canonical, interface, and artifact
names); a `UnitGraph` (`env.units`) holds an environment's loaded units by kind and canonical name with their typed
forms, replacing `loaded_interfaces`, `loaded_modules_ast`, `module_export_scopes`, and `precompiled_modules`; the
graph also names artifact paths and holds the checks that resolve imports again. The type checker's loading, the
interface compiler (`ensure_resolved_interface_artifacts`), C headers, the module compiler's manifests and
`find_interface_header`, `unit_module_refs`, `BuildEngine` (one resolver per build), the pipeline, and
`load_module_for_interpreter` use it; the driver's two suffix dispatches are one (`run_unit_file`,
`compile_unit_file`). Left as they were: the build engine's queue keeps its own bookkeeping of modules (by lowercased
canonical name, from manifests), and `find_canonical_module_source` still finds the source of a manifest entry
recorded without one. Typed forms stay per environment (nested compilations elaborate their imports again), since
sharing them would change which symbols units are elaborated with.

**C3. The REPL and the test runner use the same graph.**

---

## 6. Order, Parallelism, and Conflicts

```
Phase 0:  0a (decision) ─────────────┐
          0b (baseline) ─────────────┤
          0c, 0d, 0e ────────────────┤
                                     ▼
Track A:  A1 ──► A2 ──► A3 ──► A4         (A2 needs 0a and 0b)
Track B:  B1 ──► B2 ──► B3 ──► B4?        (B4 needs 0c)
Track C:  C1 ──► C2 ──► C3
```

After phase 0, the tracks run in parallel, each in its own worktree and session, landing on `origin/main` step by
step. Where they touch the same things:

- **`ABI_VERSION`:** A2, possibly A4, and C1 (if headers change) bump it; the step that lands second takes the next
  number and regenerates the ABI corpus.
- **IR goldens:** A1 to A4 all change IR dumps, which is one reason track A stays sequential.
- **`pipeline.py` and `quest_driver.py`:** A4 adds a phase and C2 changes how units are loaded.
- **`interpreter/treewalk.py`:** 0d, B3, and C2; 0d lands first.
- **`types/model.py`:** 0c and B4, in that order.

Stale docstrings and comments are fixed by whichever step touches their files.

---

## 7. Decisions

| Decision | Choice |
|---|---|
| Records and variants at polymorphic boundaries (0a) | Boxed in aggregate slots and `QVal` words |
| View changes in aggregates (0a) | V1: view-sensitive tuples and options carry the descriptor of their stored type |
| Not pursued | One-word records and variants (per-site caches, boxing every variant); program-wide variant tags (awkward with separate compilation) |
| Lost update after a view-changing upcast | Fixed by A2, not before |
| Performance bar for A2 | At most 10% slower on any benchmark |
| Desugaring before type checking (B3) | Yes; typecheck dumps may change, error positions must not |
| Canonical types at construction (B4) | Experiment, then decide |
| Execution | Tracks in parallel worktrees after phase 0 |
