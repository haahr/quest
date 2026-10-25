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

- the C printer made representation decisions (auto values, `inspect` arms, bounded type parameters' views,
  `type_app` thunks, adapters; moved to the represent pass by A3) and materializes descriptors;
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

**Decided: views on tuples and options, as proxies.** The candidates considered, each keeping records' and variants'
16-byte values and evidence passing:

- **V1. Views as fat pointers.** A tuple or option whose type is *view-sensitive* (values of its subtypes can be
  represented differently at it: a component is a record, a variant, a type parameter bounded by one, a function whose
  signature mentions such a type, or a view-sensitive tuple or option) is a pair, its pointer and a view (the
  descriptor of the type its components are stored at, or NULL); an upcast sets the view, and reads through a view
  convert. Not pursued: with boxing it cannot make native and generic layouts agree, since `List(A)` (unbounded `A`)
  is not view-sensitive and `List(P)` is, so their cons cells would hold their tails differently, and polymorphic
  calls would copy lists of records again (A2's notes).
- **Proxies (chosen, A2).** Every slot, `QVal` word, variable, parameter, and result holds a tuple or option as one
  pointer, so boxing's memory agreement holds everywhere. A view-changing upcast allocates a small immutable *proxy*
  (the original object, the descriptor of the type its components are stored at, and the descriptor of the type it is
  used at), tagged in its pointer's low bit; nothing is copied, so identity and `var` components are shared. Reading a
  component of a tuple or option whose type may be proxied checks the tag; through a proxy, the component is read
  from the original and converted (a record by the `(view, layout)` offset-table map, a variant's or option's tag by a
  map of case names, a nested tuple or option by another proxy, a closure by an adapter), and kept in the proxy if it
  is immutable. Upcasting a proxy makes a new one of the original (proxies never chain), or gives back the original.
- **V2. Static witnesses on tuples and options.** As V1, but the view is a static witness table for the upcast
  (per component: an offset-table map, a tag map, an adapter), built at compile time when the source view is NULL.
  Not pursued, for V1's reason.
- **V3. Reject.** Keep copying for view changes, reject statically any view-changing upcast of an aggregate that
  holds `var` components (directly or nested), and document that `is` can differ for immutable ones. Least work,
  rejects programs the interpreter runs, and leaves the conversion machinery for view changes in place.

A2 implements boxing and proxies together.

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
  `ABI_VERSION` bump. (Moved to shapes in A2, record names with it.)

Recording the written component types on IR operations at lowering would remove the first.

**A2. The representation change (0a).** Boxing in aggregates, and views on view-sensitive tuples and options, in
`layout.py`, the represent pass's plans, the runtime (`quest_convert`, `quest_layout_equivalent`, slot reads), and the
conversion matrix. A2 also moves `collect_aggregate_types` to shapes (left over from A1), under the same
`ABI_VERSION` bump. Done when the matrix's identity column and the lost-update test pass in C, the rejected
conversions that boxing makes unnecessary are accepted, `ABI_VERSION` is bumped, and the benchmarks are within the
bar.

**Done:** boxing, `collect_aggregate_types` on shapes, and views as proxies, under `ABI_VERSION` 31.

- Every aggregate slot (tuple component, option payload, record field, array element, auto payload, module record
  field) is one word, its value's `QVal` form (`slot_representation` in `codegen/layout.py`): a record or variant is a
  pointer to an immutable box, a `Bool` or `Char` a word of its own (`QBoolSlot`, `QCharSlot`; before, tuples and
  records of them were read wrongly by generic code and the runtime). Wide arrays are gone; `quest_slot_read` and
  `quest_slot_write` copy words; auto payloads have no storage descriptors. The printer boxes and unboxes at slots,
  reusing the box a value was read from (`load_slot`, `slot_value`).
- The location a `var` or `out` parameter of a record or variant type points to holds it boxed
  (`location_representation`): a slot's address is passed as it is, and a local whose address is taken is held boxed,
  so such locations pass to generic `var` parameters by cast (no shadow cell).
- Polymorphic calls convert aggregates over unbounded type parameters by cast: the conversion matrix's identity column
  passes, and arrays of records and tuples with `var` components of a type parameter are accepted. `runtime` and
  `copy` plans and rejections remain where layouts still disagree: generic code views a bounded type parameter's
  values at the bound, and closures among the components whose C signatures change (registers). So
  `generic_layout_agrees` and `quest_layout_equivalent` are not trivial: they tell three places (slot, register, and
  the cell a `var` parameter points to) and bounded views apart, and the differential test stays.
- Also fixed: `is` between tuples of different types (compared as addresses), and option upcasts whose payload
  components change view (an unsupported conversion; now a runtime copy, as for tuples).

**Views as proxies.** 0a's V1 (fat pointers) conflicts with boxing's memory agreement (see 0a); the owner chose to
prototype proxies instead, which kept every value one pointer, and measured them against the bar:

- A tuple or option type *may be proxied* (`may_be_proxied` in `codegen/layout.py`) when a component may change view
  (a record, variant, auto value, type variable or abstract type, function whose signature mentions one, or a tuple or
  option that may be proxied), and an option also when it has two or more cases (a subtype may number them
  differently). The printer reads such a value's components through `quest_is_proxy` checks; components that cannot
  change view are read from the original as they are (`quest_unproxy`), as are tuples and options the function made
  itself. A value of any other type is never a proxy: an upcast to such a type unwraps one, and the runtime copies
  rather than proxies where the target type may not be proxied (a closure whose C signature changes with a generic
  layout), using the same predicate on descriptors.
- The tag is the pointer's low bit (`QUEST_PROXY_TAG`), not a header word: tuples have no header, and one would grow
  every tuple; the collector keeps a tagged pointer's proxy alive as it recognizes pointers into an allocation's
  interior (Boehm GC's default).
- An upcast that changes a component's view is a `view` plan (the runtime makes the proxy, `quest_make_proxy`);
  one that does not stays a cast, for options too when their cases keep their indices. Tuple `copy` plans for view
  changes are gone (only auto payloads are copied), and the `runtime` plans at polymorphic calls over bounded type
  parameters make proxies, so tuples with `var` components of a bounded type parameter are accepted, and identity
  holds there too. Variant payloads, `QVal` words, simply hold proxies; options bounded by options keep their `view`
  plans, which now make proxies.
- Reads through a proxy keep converted immutable components (records' views, nested proxies, adapters) in the proxy,
  so a closure is adapted once per proxy; a call through such an adapter still converts by descriptor, about three
  times slower than a statically adapted closure.
- `is`, identity hashes, printing, `quest_convert`, and dynamic serialization see through proxies (a proxy is shared
  as its original).
- Cost: the existing benchmarks run within 5% of main's; reads of a view-sensitive tuple that is not a proxy (an array
  of tuples of records, read in a hot loop) about 9 to 13% slower; reads through proxies about 3 times slower than of
  a copy (`view_reads`, a benchmark of both).

Remaining: options whose cases are listed in different orders are equal types laid out differently, and `ordinal`
of an option upcast to a supertype that numbers its cases differently gives the supertype's index in C but the
original's interpreted ([tasklist.md](tasklist.md), `Options whose cases are listed in different orders`).

**A3. Representation decisions out of the printer.** Auto packing (`make_auto`), `inspect` arm conversions
(`auto_arm_converted`, `auto_layouts_agree`), bounded type parameters' views (`bounded_param_in_scope`), `type_app`
thunks, and adapters become `convert` plans or IR operations decided by represent. Done when the printer calls neither
`quest_convert` nor `layout.py`'s judgements on its own, and [ir.md](ir.md) §8.5 holds.

**Done:** the represent pass decides, and records in the IR, every representation decision the printer made; the
printer prints what it is given ([ir.md](ir.md) §8.3, §8.5).

- **Slots** (`ir/slots.py`, the pass's last step): a read of a record or variant from a slot binds a *boxed* variable
  (`Var.boxed`, printed `box(T)`) and a `slot_unbox` conversion the value; storing the value into another slot, or
  boxing it into a QVal word, reuses that box; a value with no box gets a `slot_box` conversion, or is boxed in the
  tuple's or record's own allocation (`embedded`, printed `box a`); mutable variables whose address is taken, and
  `var` and `out` parameters, of record or variant types are boxed. Record field reads through stored types
  (`RecordField.stored`) and record literals' runtime offset tables (`MakeRecord.runtime_offsets`) are decided there
  too. `load_slot`, `slot_value`, `slot_field`, the printer's `located` set, and its box and freshness bookkeeping
  are gone.
- **Proxies:** reads of tuple and option components, option tags and payloads, writes of tuple `var` components and
  their addresses, and `is` record their access (`direct`, `original`, `proxy`, printed `via ...`), with the
  "made by this function" rule applied by the pass; casts to types that cannot be proxies are `unproxy` plans.
  `may_be_proxied` is unchanged, so it stays consistent with `quest_may_be_proxied`.
- **Autos and inspect:** `bounded_param` moved to the pass. An auto value of a bounded witness made by generic code
  copies its payload with `view` fields from the bound to the witness (the printer converted the payload tuple in
  place with `quest_convert`, which also changed the view of a tuple the program still held). Each inspect case
  records its arm (`InspectArm`: components converted by descriptor, the bound, exact cases' sharing, plan, and
  layout error, `auto_layouts_agree` moved to the pass); binders converted from the arm's type are bound by lets.
- **Type applications** record their thunks' plans (`TypeApp.plans`); adapters already carried theirs.
- **Also fixed:** a value parameter annotated with a proper supertype of its function's expected parameter type
  (former [tasklist.md](tasklist.md) task): lowering gives the parameter the variable's type and binds the
  annotation's at entry, which the pass converts (`language/contravariant_parameter_annotations`).

The verifier checks boxed representations and that slots take boxes. The C of every test program and benchmark is
unchanged but for names, the order of declarations, a separate statement per box, and three improvements: a record or
variant read from a slot or made as a literal is boxed into a QVal word by its own box rather than a new one; a copy
of a tuple the function made reads it without proxy checks; and the bounded auto payload copy above. The benchmarks'
C is unchanged but for names, and they run as on main.

Remaining in the printer, by design or for A4: it makes descriptors and templates, the types' declarations (structs,
offset tables and the subtype pairs that need them, `is_record_subtype` and the tuple and variant coercion tables),
and module records (boxing their members); it wraps and unwraps variant payloads, exception payloads, and echoed
values as QVal words by their representations; and it calls `quest_convert` only to print conversions recorded as
such (`view` and `runtime` plans, `stored` field reads, inspect arms). The written component types are still found
by `written_structure` (recording them on IR operations at lowering, A1's suggestion, would not have simplified A3, so
it is left for A4 or later).

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
chains. Typecheck dumps may change. Errors may change where desugaring gives a logical reason, provided each still
shows a reader clearly where the problem is in the source as written.

**Done:** `quest/syntax/desugar.py` ([syntax.md](syntax.md) §5), the pipeline's `desugar` phase between `parse` and
`typecheck` (dumped as an AST, without goldens), and `parse_unit` (`quest/modules/units.py`), which every other path
that parses a unit and checks it uses (the unit loader, the interface and module compilers, the build engine's main
routines). `quest.syntax` depends on no later phase. It rewrites `andif` and `orif`
into conditionals, user infix operators into calls, `elsif` chains into nested conditionals (ending in `else ok`
without an else branch), assignments to array elements into `ExprIndexAssign`, and non-recursive, non-external
`let` declarations with parameters into function values. The type checker rejects those forms as internal errors.
Left in the type checker: a conditional without elsif or else branches, a statement of type Ok whose then branch it
wraps in a block, since that is its typing rule rather than syntax; and the parameters of recursive and external
`let` declarations, which declare their types. Only the conditionals of `andif` and `orif` are marked
(`short_circuit`), so that their operands are still checked against Bool and errors name the operand; the other core
forms are elaborated as if written: an elsif chain without an else branch is checked against the expected type
branch by branch instead of synthesized (an `Int` expected reports the implicit `ok`), a user infix call gets the
expected type for its implicit type arguments, and an unbound operator is an undefined variable. New error tests pin
those errors; no typecheck dump or golden output changed, nor any existing error test.

**B4. Canonical recursive types at construction (experiment).** Prototype building canonical forms when types are
made, so that type equality is identity; measure type checking time and the code it removes, and adopt it only if it
pays: if it removes the `QUEST_CHECK_CANONICAL` guard and the on-demand canonicalization below the type checker (the
memo tables of `normalize_type` and `canonical_type`, shapes' separate canonical forms) and type checking is at most
about 10% slower. The subtyping cache stays either way: it records proofs between distinct types, which canonical
forms do not decide (equal types become identical, so it gains hits). After 0c and B1 to B3, since it touches
`types/model.py` and subtyping.

**Done (not adopted):** the prototype is on the branch `b4-prototype` (+85/−10 lines in `types/`). It fails both
parts of the criterion.

- *What it removes.* Only a design that keeps types as written can leave golden output and errors unchanged: each
  new interned type node gets its canonical form when it is made (a hook in `_InternedNode`, stored on the node as
  `_canon`), and `is_type_equal` returns early when two types' canonical forms are one object. That replaces the
  memo table of `canonical_type` with an attribute and nothing more. The guard stays, because computing canonical
  forms earlier does not make merging binders any safer. Shapes still need both forms: the canonical one for tags
  and descriptors, and the written one for the binder symbols that `collect_fun_quantifiers`, `written_structure`,
  and call-site type arguments are keyed by. `normalize_type` and its memo table are unchanged. The early return in
  `is_type_equal` hits on 245 of 23,780 calls over the corpus.
- *Making types canonical in place* (variant `QUEST_B4_STRONG=1`: a recursive type is replaced by its canonical
  form when it is made) breaks 26 typecheck goldens and 2 error tests. Recursion variables print as `Rec.0`.
  Members of recursive groups lose their names (`Array(Tree)` becomes `Array(Variant leaf: Int node: Forest end)`).
  Record fields are sorted, so record literals are elaborated in a different field order. `.qi` files no longer read
  back, because `Rec.0` does not parse. Making types canonical in place also conflicts with the type checker's
  invariants. Canonical binder ids are numbered by depth, so nested quantifiers that are open at the same time would
  share ids, which breaks substitution without renaming (§2.2 of [type-system.md](type-system.md)). Types with
  metavariables cannot be canonical until they are solved. And equality depends on definitions supplied after
  construction: inside a module, an abstract type equals its witness, and an auto value's type component equals
  its witness. So type equality cannot become identity in the type checker.
- *Cost.* Measured as CPU time (`time.process_time`; the machine's load average ran from 13 to over 400), over
  `--stop-after typecheck` of the 170 golden programs plus `tests/perf/*.quest` (which type-check the questlang
  modules), and `tests/perf/measure.py`'s C generation over 163 programs, with main and the branch run back to back:

  | | main | prototype |
  |---|---|---|
  | type checking | 13.0 s | 21.7 s (+67%) |
  | type checking, guard off | | ~+48% |
  | C generation | 7.0 s | 4.6 s |
  | both | 20.0 s | 26.3 s (+31%) |

  The C output is unchanged. Today the type checker computes no canonical forms, so all of this cost is new. Most of
  it is building canonical graphs: every new node that reaches a recursive type (5,179 of 58,006 new nodes) walks
  its whole graph again, such as every type that mentions the questlang AST's recursive group. The first version,
  which also treated every application of a type operator and every alias as possibly recursive, was +65% even
  with wall-clock timing. A cheap version would need an incremental algorithm: look up a new node by its shape and
  its children's canonical forms, and minimize only where a `Rec` is introduced. Binders' scope edges make open
  parts context-dependent, so this is new design work. Even then, it would not meet the first part of the
  criterion.

The plan's premise, that canonical forms at construction would make type equality identity and remove the
backend's second view of types, does not hold while types keep the names they were written with, which goldens,
errors, `.qi` files, and the IR's keying by binder symbols all rely on.

**The `fun` annotation soundness hole** (§7), after B3 as its own step.

**Done:** a function checked against a function type has its annotations checked as synthesis and subsumption would
check them ([type-system.md](type-system.md) §6.1): parameter modes must match, a parameter's annotation must fit the
expected type contravariantly (exactly for `var`, covariantly for `out`), and a result annotation must be a subtype
of the expected result, which the body is then checked against; a function with type parameters is synthesized; a
polymorphic function without value parameters has its result annotation checked too. A raise's `as` clause is
elaborated under an expected type, and a tuple rejects a phrase it cannot hold before matching an expected type. New
error tests cover each case; no golden output changed. A C miscompilation of a contravariant parameter annotation,
which predates the fix, was fixed in A3 (§3).

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

**Done:** The REPL keeps one `UnitGraph` across its inputs ([build-process.md](build-process.md) §2.1,
[repl.md](repl.md) §5). Each input is a session (`UnitGraph.new_session`, in `QuestREPL.evaluate`, which replaces the
loop's hook into the resolver), and an input that fails is rolled back with the graph's `snapshot` and `restore`. The
values of modules the interpreter has run moved from the runtime environment's `evaluated_modules` into the graph's
units (`Unit.value`), so a rollback forgets a module's typed form and value together; before, a failed input that
imported a module left its value behind, to be reused with the next import's new elaboration. The runtime environment
keeps holding the type checker's graph by reference, which is correct because `restore` changes the graph in place.
A module declared in the program is now run where it is declared, without the cache by name it shared with imported
modules, which made a REPL input that declared a module again get the old one, and a declaration that was rolled back
be remembered. The test runner's builds are driver runs, one session per test, so there is no graph to share across
tests; what the runner resolves itself now goes through the graph (discovering tests by `file_unit_kind`, following
error tests' imports with a `Resolver`). The driver's two copies of marking prebuilt objects precompiled are
`UnitGraph.add_prebuilt_objects`. Left as they were: the build engine's queue bookkeeping by lowercased canonical
name, `find_canonical_module_source`, and nested compilations elaborating imports in fresh Environments.

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
| View changes in aggregates (0a) | Views: a view-changing upcast of a tuple or option keeps the original, with the descriptor of its stored type |
| How V1's views meet boxed slots (A2) | Proxy objects (one pointer everywhere; a view-changing upcast allocates a proxy holding the original and its view): adopted, within the bar |
| Not pursued | One-word records and variants (per-site caches, boxing every variant); program-wide variant tags (awkward with separate compilation) |
| Lost update after a view-changing upcast | Fixed by A2, not before |
| `collect_aggregate_types` on shapes (left from A1) | In A2, under its `ABI_VERSION` bump |
| Performance bar for A2 | At most 10% slower on any benchmark |
| Desugaring before type checking (B3) | Yes; typecheck dumps may change, and errors may change for a logical reason if they still point clearly at the source |
| Canonical types at construction (B4) | Experiment; adopt if it removes the guard and on-demand canonicalization at most ~10% slower. Not adopted: it removes neither, and type checking was 67% slower (§4) |
| Fix the `fun` annotation soundness hole | After B3, as its own step |
| Execution | Tracks in parallel worktrees after phase 0 |
