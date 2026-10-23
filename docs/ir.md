# Quest Intermediate Representation (IR)

This document specifies the intermediate representation between the typed AST and the C backend, and the plan for
introducing it. The IR is one data structure, refined by a sequence of small passes (nanopass style); each pass
establishes invariants that the IR verifier checks. The C printer consumes the last stage. A future native AArch64
backend ([roadmap.md](roadmap.md) step 6) would consume the same stage, adding its own late passes.

Status: **design**. Nothing described here is implemented yet; §12 is the implementation plan.

---

## 1. Purpose and Position in the Pipeline

```
source → tokens → AST → typed AST ─┬─→ interpreter
                                   └─→ lower → Core IR → specialize → closure-convert → represent
                                                → materialize descriptors → C printer → C → clang
                                                                         └→ (future) CFG/SSA → AArch64
```

Today the C emitter (`codegen/c_emitter.py`, `c_analysis.py`) translates the typed AST directly, and on the way
reduces types, chooses representations, converts values between them, lifts closures, specializes functions, and
prints C. Each of these becomes a pass over the IR, so that:

- representation decisions and the conversions between representations are made once, by one pass, and are visible
  in the IR as explicit nodes (the C printer only prints);
- specialization and closure conversion are IR-to-IR transforms whose results are ordinary IR, analyzed and printed
  like anything else (no side tables keyed by AST node identity, no clones that analyses miss);
- every binder is a symbol, so identity never depends on names;
- types reaching the backend are lowered shapes (§4), never aliases or unreduced applications;
- expression-versus-statement plumbing (destination passing, temporaries for `if` and blocks as values) disappears
  into the normal form;
- each stage can be dumped (goldens) and verified (invariants) on its own.

The interpreter stays on the typed AST. It shares nothing with the lowering, which makes it an independent oracle:
every golden test compares the two.

## 2. Design Principles

1. **One IR, refined by passes.** A single set of node types. Each pass may only use the nodes its stage allows
   (§9), and the verifier checks the stage's invariants after it.
2. **A-normal form with join points.** Every intermediate value is named by a `let`. Arguments of operations are
   atoms (variables and constants). Control flow that produces a value joins through an explicit join point
   (§6.3), equivalent to an SSA block with arguments; lexical scope plays the role of dominance.
3. **Structured control flow.** `if`, `switch`, `loop`, and `try` stay structured, so the C printer produces
   structured, readable C, and exceptions remain regions rather than edges.
4. **Single assignment for compiler values; mutable variables only where the source has them.** Source-level
   `let var` locals are mutable variables with an assignment node; everything else is bound once. Since closures may
   not capture local mutable variables or `var`/`out` parameters ([type-system.md](type-system.md) §6.2.3), every
   mutable local whose address is not taken could be promoted to SSA values later.
5. **Symbols for every binder.** Variables, functions, join points, type parameters, and globals are IR symbols
   (unique ids, with a name hint for printing). Lookups are by symbol only.
6. **Types are lowered shapes; type arguments become values.** Quest cannot erase types (`Dynamic`, auto types,
   and `inspect` use them at run time), so type abstraction and application are explicit, and a later pass turns
   them into descriptor values (§7).
7. **Target-independent, ABI-aware.** The IR knows nothing of C syntax or AArch64 registers, but its lowered stage
   fixes representations as the Quest runtime ABI defines them ([c-representation.md](c-representation.md)), which
   compiled C and native code share with one runtime and one serialized form of dynamic values.

## 3. Program Structure

An IR **unit** corresponds to a compilation unit (a program, or a module compiled on its own):

- **Functions:** `fun f [type params] (params): result = body`. Top-level and module functions, specialized clones
  (§8.1), and, after closure conversion, every lifted local function. Each has a symbol; module members also carry
  their module's symbol and export name.
- **Globals:** top-level values and module-level `var` state, each a symbol with a type. Top-level rebindings
  (`let x = 1; ... let x = 2`) are distinct symbols, so distinct globals.
- **Module records:** a module's exported record, its layout, and its lazy initializer function
  ([c-representation.md](c-representation.md) §5.6).
- **Main:** the program's top-level phrases, in order, as the body of an initializer, including echo (§6.6).
- **Imports:** the units it depends on and the symbols it uses from them; interfaces (`.qi`) are unchanged.

Type declarations do not appear as items: the shapes in the IR carry everything later stages need, and the printer
derives C struct declarations and descriptors from the shapes it meets.

## 4. Types: Shapes and Representations

### 4.1. Shapes

Every binder and every operation's result has a **shape**, the backend's view of a Quest type, computed once per
canonical type (`shape(t)`, cached by the hash-consed type):

| Shape kind | Components |
|---|---|
| `int`, `real`, `bool`, `char`, `string`, `ok`, `word` | — |
| `tuple` | ordered value components (name, shape, `var`); type components are erased from the layout |
| `record` | fields (name, shape, `var`) |
| `variant` | cases (name, payload shape) |
| `option` | cases (name, payload component shapes) |
| `array` | element shape |
| `fun` | parameters (shape, mode `value`/`var`/`out`), result shape |
| `all` | type parameters (symbol, bound), body shape |
| `auto` | type component bound, signature |
| `exception` | payload shape |
| `typevar` | type parameter symbol (in scope), bound |
| `abstract` | opaque: an abstract type of a module, an application of an abstract operator, a path type |
| `external` | C-level opaque type |
| `rec` | a reference into a recursive group: the canonical recursive graph of `codegen/c_types.py` |

Aliases are stripped and operator applications reduced before a shape is built; recursion is explicit through
`rec` references into the canonical graph, so that equal recursive types, however written, share one shape. The
typed AST keeps its types (with alias names) for the interpreter and for printing; IR nodes that print types (echo,
error messages) carry the original type alongside the shape.

### 4.2. Representations

From the represented stage on (§9), every binder also has a **representation**, the ABI's class for its values:

| Representation | C (today) | Used for |
|---|---|---|
| `word` | `QVal` | a value of an unbounded type parameter, stored generically |
| `int`, `real`, `bool`, `char` | `QInt`, `QReal`, `QBool`, `QChar` | scalars |
| `ptr(layout)` | `T *` | strings, tuples, options, arrays, closures, auto values, exceptions |
| `record(view)` | `QRecordVal` (16 bytes) | a record and the offset table of its view |
| `variant(tags)` | `QVariantVal` (16 bytes) | a variant and its tag space |
| `descriptor` | `const QTypeDescriptor *` | a run-time type (§7) |
| `void` | — | `Ok` results |

A **layout** describes an aggregate in memory: its shape, together with which positions hold a type parameter's
value stored generically (as a `word`, or as the bound's representation for a bounded parameter). Two layouts of the
same shape may differ: `Tuple x: A end` in generic code and `Tuple x: Bool end` at the call. Whether two layouts
agree in memory is decided by `generic_layout_agrees` (§8.3), mirroring the runtime's `quest_layout_equivalent`.

## 5. Atoms, Operations, and Bindings

**Atoms** are variables (symbols) and constants (`Int`, `Real`, `Bool`, `Char`, `String`, `ok`). Operations take
atoms only.

A **binding** names the result of one operation:

```
let t1: Int = add(x, 1)
```

The operations, by group (the stage column says where they may appear; `C` is Core, `R` represented):

| Group | Operations | Stage |
|---|---|---|
| Scalars | `prim op(a...)`: arithmetic, comparison, logical, `Word` operations, conversions between scalars | C+ |
| Calls | `call f [τ...] (a...)` (known function), `call_closure c [τ...] (a...)`, `call_native n (a...)` | C+ |
| Functions | `fun ... ` (nested function value), `type_app f [τ...]` (polymorphic value applied to types only) | C (until closure conversion) |
| Closures | `closure f {env: a...}`, `env_field(e, i)` | after closure conversion |
| Tuples | `tuple(a...)`, `tuple_field(t, i)` | C+ |
| Records | `record(name: a...)`, `record_field(r, name)` | C+ |
| Variants and options | `variant(tag, a)`, `option(tag, a...)`, `tag(v)`, `is_tag(v, tag)`, `payload(v, tag)` | C+ |
| Arrays | `array(a...)`, `array_rep(n, a)`, `index(a, i)`, `size(a)` | C+ |
| Auto values | `auto(τ, a...)`, `auto_type(v)`, `auto_payload(v)` | C+ |
| Exceptions | `exception(name)` (generative), `raise` (§6.4) | C+ |
| Cells and addresses | `addr(x)` (of a mutable variable), `addr_field(t, i)`, `addr_index(a, i)`, `load(p)`, `store(p, a)` | C+ |
| Modules | `module_record(m)` (forces initialization), `global(g)` | C+ |
| Conversions | `convert(a, plan)` (§8) | R+ |
| Descriptors | `descriptor(τ)`, `instantiate(template, d...)`, `descriptor_param(A)` | after materialization |
| Dynamic | `dynamic_new(d, a)`, `dynamic_be(d, a)`, `inspect` (§6.5) | C+ |

Operations that can raise (calls, array indexing, `payload` of the wrong tag, `dynamic_be`, division) do so through
the enclosing `try` regions (§6.4); the IR does not mark them, as no stage needs edges to handlers.

**Mutable variables** are declared and assigned by statements:

```
var n: Int = 0
n := add(n, 1)
```

Only source-level `let var` locals, and `var`/`out` parameters (as pointers), are mutable. `addr(x)` takes the
address of a mutable variable for a `var` or `out` argument (`@x`); field and element addresses take the address of
a `var` component or an array element. Module-level `var` variables are globals.

## 6. Control Flow

A **body** is a sequence of bindings, mutable-variable statements, and expression statements, ending in a
terminator. The terminators are `return a`, `jump k(a...)`, `break l`, `continue l`, `raise a`, and `unreachable`
(after a call that cannot return, such as `exit`).

### 6.1. Conditionals and Switches

```
if a then { body } else { body }
switch tag(v) { case cons: { body } case nil: { body } else: { body } }
```

`switch` covers `case` on variants and options (by tag), and on ordinals. Both are statements: their branches end in
terminators. A conditional *expression* jumps to a join point (§6.3).

### 6.2. Loops

```
loop l { body }
```

`loop` repeats its body; `break l` and `continue l` leave or restart the labeled loop. Quest's `while`, `for`, and
`loop ... exit` lower to it: `for i = a upto b` becomes a mutable counter, a test, and `continue`.

### 6.3. Join Points

A join point is a local continuation, used only in tail position:

```
join k(r: Int) { rest of the block, using r } in {
  if c then { jump k(1) } else { let t: Int = f(x); jump k(t) }
}
```

Its parameters are the values flowing into it (an SSA block's arguments). Lowering uses a join point for every
construct that produces a value on more than one path: `if`, `case`, and `inspect` expressions, blocks whose last
expression is one of these, and `try` expressions. Join points are not values, are never captured by closures, and
are jumped to only from their own scope; the C printer prints them as a labeled block with variables for their
parameters, or inlines a join point used once.

### 6.4. Exceptions

```
try { body } handle (e) { body }
raise a
```

`try` is a region: a `raise` in the body, or in any function it calls, transfers to the handler, which receives the
exception value; branches of a Quest `try ... when ... else ... end` become a `switch` on the exception in the
handler, re-raising when none matches. The C printer prints `try` with `setjmp`/`longjmp` (as
[c-representation.md](c-representation.md) §7 describes). C makes a non-`volatile` local modified between `setjmp`
and `longjmp` indeterminate afterwards, so the printer declares `volatile` every mutable variable that is assigned in
a `try` body and live in its handler or after the `try`. The IR makes this decidable from the region structure.

### 6.5. Inspect and Dynamic

`inspect` (auto values and dynamic values) is a structured statement, like `switch`: each branch tests the value's
run-time type against a branch type (subtype or exact match), binds the converted components, and ends in a
terminator. Conversions of the components are explicit `convert` operations in the branch (§8).

### 6.6. Echo

The REPL-style echo of top-level phrases is `echo(a, τ)`, an expression statement that prints a value with the
original Quest type (for alias names) and its descriptor or static format.

## 7. Type Parameters and Descriptors

In Core IR, a polymorphic function has type parameters (`fun f [A <: P] (x: A): A`) and calls supply type arguments
(`call f [Int] (x)`); shapes mention type parameters as `typevar` symbols. The **materialize descriptors** pass makes
them values, following the uniform quantifier rule ([c-representation.md](c-representation.md) §6.4):

- each type parameter becomes a parameter of representation `descriptor`, preceding the value parameters;
- each type argument becomes a `descriptor` value: a static descriptor for a closed type, the descriptor parameter
  for a type parameter in scope, and `instantiate(template, d...)` for a type that mentions type parameters in scope,
  whose template has a hole per parameter (§4.2), found by symbol;
- the other run-time uses of types (auto values, `inspect`, `dynamic.new`, `dynamic.be`, echo, `quest_convert`) take
  descriptor values likewise.

Descriptors in scope are keyed by the type parameter's symbol, so a caller's `A` and a callee's `A` never meet by
name.

## 8. Passes

### 8.1. Specialize

Clones a polymorphic top-level or module function called with record or variant type arguments (the selective
trigger of [c-representation.md](c-representation.md) §6.4.3), substituting the type arguments for its type
parameters, and redirects those calls to the clone. Specialization runs *before* closure conversion: a clone's local
functions are part of the clone, and are lifted with it. Calls are matched to functions by symbol, so a local binding
shadowing a top-level function is never confused with it. Calls of local polymorphic functions can be specialized
here too, since a local function is a symbol like any other (the restriction recorded in
[tasklist.md](tasklist.md) can be lifted once this pass exists).

### 8.2. Closure-convert

Lifts every nested `fun` to a top-level function taking an environment, and replaces it with a `closure`
operation listing the captured atoms. Captured variables are found by symbol (free variables of the function's
body); since closures do not capture mutable locals, captures are values, copied into the environment. Recursive
local functions (`let rec`) capture each other through the environment, built after all members' closures are
allocated (the deferred captures of today's `_emit_rec_bindings`). `type_app` becomes a closure over the function and
its type arguments.

### 8.3. Represent

Assigns every binder a representation (§4.2) and inserts `convert` wherever a value's representation or layout
differs from the one its use requires. This is the single conversion operation:

```
let y: Box(Bool) = convert(x, plan)
```

The plan is computed once per (source, target, context) and memoized; the context says why the value converts:
plain subsumption, or passing to (or returning from) a polymorphic callee whose generic layout is described by the
callee's type and the call's instantiation. Plan steps:

| Step | Meaning |
|---|---|
| `same` | no change |
| `box`, `unbox` | between a native scalar, pointer, record, or variant and its `word` form |
| `bound_view` | between a bounded type parameter's own view and its bound's |
| `record_view(target)` | re-view a record with the target's offset table |
| `variant_tags(map)` | remap tags, only when the variants' cases differ |
| `cast` | a pointer to an aggregate whose layouts agree in memory, viewed through the other struct |
| `copy(steps...)` | build a new tuple or option, converting each component by its own plan |
| `runtime(from, to)` | `quest_convert` with both descriptors: recursive types, and layouts known only at run time |
| `adapt(param plans, result plan)` | wrap a closure in a thunk converting its arguments and result |
| `reject` | a conversion that would copy mutable data laid out differently: a compile-time error |

Static decisions (whether layouts agree, whether a copy would lose updates) are made by `generic_layout_agrees` and
`generic_layout_copies_mutable_data` in `codegen/c_types.py`, which a differential test checks against the runtime's
`quest_layout_equivalent` (§12, step 0). After this pass, every operation's atoms have exactly the representations
the operation requires.

**Identity.** A `copy` or `runtime` step builds a new tuple or option, so the converted value is not the same object
as the original, and `is` (object identity for tuples, records, and arrays) can answer differently in compiled code
than in the interpreter: a `Tuple x: P end`, with `P` a record type, passed through an unspecialized polymorphic
function that returns it is no longer `is` the original. A `cast` keeps identity, and specialized calls need no
conversion. This is a documented limitation of the C backend, recorded in [tasklist.md](tasklist.md) to return to;
the conversion matrix (§12, step 0) tests it, so that the rule is checked rather than incidental.

### 8.4. Materialize descriptors

§7.

### 8.5. Print C

Prints the last stage as C: struct declarations and descriptors for the layouts it meets, a function per IR
function, structured statements for structured control, labeled blocks for join points (or inlined bodies), and
`volatile` mutable variables where §6.4 requires. C names derive from symbols and their name hints (`qv_<name>`,
with a suffix when two symbols share a hint in one scope), keeping the generated C readable for debugging. The
printer makes no representation decisions.

### 8.6. Future: CFG and SSA for the native backend

The native AArch64 backend would add, after §8.4: building a control-flow graph from the structured IR (join points
become blocks with arguments), promoting mutable locals whose address is not taken to SSA values, and then
instruction selection, register allocation (simpler on SSA), and emission. The C path does not need these: clang
builds its own SSA and optimizes.

## 9. Stages and Invariants

| Stage | After | Invariants (checked by the verifier) |
|---|---|---|
| **Core** | lowering | ANF: operation arguments are atoms; every binder is a symbol bound once, used only in its scope; join points jumped to only in tail position within their scope; shapes only (no aliases, no unreduced applications); type parameters in scope for every `typevar` |
| **Specialized** | §8.1 | as Core; every specialized call refers to an existing clone |
| **Closed** | §8.2 | no nested `fun` or `type_app`; every function's free variables are its parameters, its environment, and globals |
| **Represented** | §8.3 | every binder has a representation; every operation's atoms have the representations it requires; conversions only through `convert` |
| **Descriptors** | §8.4 | no type parameters or type arguments remain; every run-time type is a `descriptor` value |

The verifier runs after every pass when `QUEST_CHECK_IR=1`, which the test runners set (like
`QUEST_CHECK_CANONICAL`); production builds skip it.

## 10. Textual Form

Every stage can be dumped (`--dump-after ir_core`, `ir_closed`, ... in the driver), for goldens and debugging:

```
fun length [A :: TYPE] (l: List(A)): Int {
  switch tag(l) {
    case cons: {
      let c: Tuple head: A tail: List(A) end = payload(l, cons)
      let t: List(A) = tuple_field(c, 1)
      let n: Int = call length [A] (t)
      let r: Int = prim add(1, n)
      return r
    }
    else: { return 0 }
  }
}
```

and, after representation and descriptors:

```
fun length (d_A: descriptor, l: ptr<List(?0)>): int {
  switch tag(l) {
    case cons: {
      let c: ptr<Tuple head: ?0 tail: List(?0) end> = payload(l, cons)
      let t: ptr<List(?0)> = tuple_field(c, 1)
      let n: int = call length (d_A, t)
      let r: int = prim add(1, n)
      return r
    }
    else: { return 0 }
  }
}
```

(`?0` marks a position stored generically, as a `word`.) A caller at `Bool` passes its native list:

```
let xs: ptr<List(Bool)> = ...
let xs1: ptr<List(?0)> = convert(xs, cast)
let n: int = call length (descriptor(Bool), xs1)
```

## 11. Open Questions

- **Native bindings.** Library bindings implemented natively carry C symbols or inline C templates
  (`TypedNativeBinding`). The IR keeps them as `call_native n (a...)`, which the C printer expands; a native backend
  needs its own implementations of each, or calls to C symbols only.
- **Inlining.** Not planned for the C path (clang inlines). A small inliner over Core IR would mostly help the
  native backend, and specialization of small polymorphic functions.
- **Separate compilation of specializations.** Specializing calls of another unit's functions needs the callee's IR,
  which `.qi` files do not carry; they stay unspecialized (as today) unless units ship their Core IR.

---

## 12. Implementation Plan

Each step is one or more commits that keep the full test suite passing. The current C backend stays the default until
step 6.

**Step 0: Safety net.**
- **Policy for what it finds.** Silent miscompilations in today's emitter are fixed in the emitter now, since every
  compiled program is exposed until the IR backend replaces it. Anything else is recorded as a known failure (the
  compiled phase skipped, with a reason naming the task) for the IR backend to fix.
- **Mutable variables across `setjmp`.** *Done.* The emitter miscompiled a mutable local assigned in a `try` body
  and read in its handler or after it: at `-O2` the assignment was lost (`bump(4)` below printed 40 compiled and 50
  interpreted). Such locals are now `volatile` (§6.4), tested by `tests/source/language/try_mutable_locals.quest`:
  ```quest
  exception Stop end;
  let bump(n: Int): Int =
      begin
          let var x = n;
          try begin x := x + 1; raise Stop end; x := 100 end when Stop then x := x * 10 end;
          x
      end;
  ```
- **A generated conversion matrix.** *Done* (`tests/conversions/generate.py`, [testing.md](testing.md)). It found two
  bugs, both fixed: generic code read record fields of a type parameter wrongly when the record stored a record or
  variant there natively, and specializations keyed by types crashed C generation. A checked-in script writes one program per place values convert (polymorphic
  call arguments and results, annotated bindings and subsumption, field and array stores, closure and
  type-application thunks, `inspect` arms, `dynamic.be`, record fields stored at a subtype) into
  `tests/source/conversions/`, each marked as generated, covering the type shapes (scalars, tuples, options, records
  with width and depth subtyping, variants, arrays, closures, recursive types, bounded parameters, auto types) at
  scalar, record, and variant type arguments. Goldens come from the interpreter. An identity column checks `is`
  where conversions cast (identity kept) and records where they copy (§8.3). Conversions the C backend rejects at
  compile time (mutable data laid out differently) become unit tests, since the error suite cannot express errors
  of C generation.
- **A differential layout test**, built on `codegen/c_types.py` alone (descriptor forms, holes, and templates, which
  outlive the emitter): for enumerated small types and seeded random ones, C programs compare
  `quest_layout_equivalent` with `generic_layout_agrees`, asserting soundness (wherever the static check says the
  layouts agree, the runtime must) and reporting where the static check is only conservative.
- **A baseline**, committed as a report: C emission time and generated C size over the test corpus, and run times of
  a few compiled programs that cross polymorphic boundaries heavily, for step 6 to compare against.

**Step 1: Identity in the typechecker.**
- A well-scopedness check over the typed AST, run in tests: every type variable is bound by an enclosing quantifier
  or declared symbol, every variable by an enclosing binder.
- Fix any place it finds that re-elaborates a declaration with fresh symbols (as functions' parameter annotations
  did).

**Step 2: Shapes.**
- `codegen/shapes.py` (or `ir/shapes.py`): `shape(t)` and the shape kinds of §4.1, built on the canonical forms of
  `codegen/c_types.py`, with unit tests (equal types share shapes; aliases and applications reduce; recursion is
  explicit).
- Optionally, move the current emitter's structural type tests onto shapes where that is cheap; not required, since
  the emitter is replaced.

**Step 3: IR and lowering to Core.**
- `ir/` package: node types (§5, §6), symbols, the textual form (§10), and the verifier for the Core stage (§9).
- Lowering from the typed AST, construct by construct (expressions, blocks and join points, loops, `case`, `try`,
  `inspect`, functions and type parameters, tuples with type components, modules and their records, top-level
  phrases and echo), with IR dump goldens for a representative set of tests (a `--dump-after ir_core` phase in the
  test runner).
- Every golden test lowers to verified Core IR (a test mode that lowers without printing).

**Step 4: Passes.**
- Specialize (§8.1), with calls matched by symbol.
- Closure-convert (§8.2).
- Represent (§8.3): representations, plans, and `convert` insertion, including variant tag maps decided from cases
  (closing the variant tag-map task).
- Materialize descriptors (§7), with type parameters keyed by symbol.
- Each pass with dump goldens and its stage's verifier.

**Step 5: C printer, as an alternative backend.**
- `codegen/c_printer.py` printing the descriptor stage (§8.5), reusing `c_declarations.py` for struct declarations,
  descriptors, and adapters where it fits.
- A driver option (`--backend ir`) and a test runner mode running every compiled test through it, until all pass and
  the conversion matrix matches.
- Changes to the current emitter are frozen from here, except for fixes needed to keep tests passing.

**Step 6: Switch and delete.**
- Make the IR backend the default; compare emission time and C size with the step 0 baseline.
- Delete `c_emitter.py`, most of `c_analysis.py`, and the parts of `c_types.py` that only the emitter used.
- Update [codegen-c.md](codegen-c.md) and [c-representation.md](c-representation.md) (§5.1 and §6.4 around the
  `convert` plans), and the task list: close the variant tag-map task, and note what is now in place for top-level
  rebindings (distinct globals per symbol) and for specializing local functions.

**Risks.** Step 3 and step 4 are the bulk of the work: the lowering covers all 62 typed AST node kinds, and the
represent pass absorbs the conversion logic now spread over the emitter. Running the full suite through the new
backend (step 5) is the measure of parity. Until step 6, fixes may land twice; freezing the current emitter at step 5
keeps that short.
