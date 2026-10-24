# Quest Intermediate Representation (IR)

This document specifies the intermediate representation between the typed AST and the C backend
(`bootstrap/python/quest/ir/`).
The IR is one data structure, refined by a sequence of small passes (nanopass style); each pass establishes invariants
that the IR verifier checks. The C printer consumes the last stage. A future native AArch64 backend
([roadmap.md](roadmap.md) step 6) would consume the same stage, adding its own late passes.

---

## 1. Purpose and Position in the Pipeline

```
source → tokens → AST → typed AST ─┬─→ interpreter
                                   └─→ lower → Core IR → specialize → closure-convert → represent
                                                → materialize descriptors → C printer → C → clang
                                                                         └→ (future) CFG/SSA → AArch64
```

Lowering the typed AST into the IR and running small, single-responsibility passes ensures that:

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
  ([c-representation.md](c-representation.md) §5.6). A module file's unit is its module alone, with its
  **exports**: its interface's members at the interface's types, bound last in its initializer (converted from the
  members, at the abstract types' representations, by the represent pass). Its record holds them, and it exports a
  C function `qv_<module>_<member>` for each that is a function or a polymorphic value, the ABI other units call
  (`codegen/c/declarations.py`, `module_function_signature`).
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
| `typevar` | a type variable: a type parameter in scope, or an abstract type of a module or interface (`m.T`); symbol, bound |
| `abstract` | opaque: an abstract type elaborated as such, an application of an abstract operator, a path type (`x.T`) |
| `external` | C-level opaque type |
| `operator` | a type operator (`Fun(X::K) T`), passed for a higher-kinded type parameter: opaque |
| `rec` | a reference into a recursive group: the canonical recursive graph of `types/canonical.py` |

Aliases are stripped and operator applications reduced before a shape is built; recursion is explicit through
`rec` references into the canonical graph, so that equal recursive types, however written, share one shape. Each
shape keeps its canonical type and its structure (the unfolding of a recursive type), from which descriptors and C
names are made. A canonical form names its binders afresh, so a polymorphic function type's shape has type parameters
(and value parameter names) of its own, not those of the type as written. The typed AST keeps its types (with alias
names) for the interpreter and for printing; IR nodes that print types (echo, error messages) carry the original
type alongside the shape.

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

The nodes are defined in `ir/nodes.py`, printed by `ir/printer.py`, and checked by `ir/verify.py`.

**Variables are objects.** An IR variable (`Var`) has a name hint and its Quest type (with alias names, for
printing); its shape is the type's, derived rather than stored, so that a pass rewriting types (specialization
substitutes type arguments) cannot leave the two disagreeing. A function's result is likewise its result type. It is bound by exactly one binder, and every use refers to the same object, so identity never depends
on names; the printer makes names distinct (`x`, `x.1`). Lowering maps each typed-AST symbol to its variable once.

**Atoms** are variables and constants (`Int`, `Real`, `Bool`, `Char`, `String`, `ok`). Operations take atoms only.

A **let** names the result of one operation, or copies an atom:

```
let t1: Int = prim +(x, 1)
```

The operations, by group (the stage column says where they may appear; `C` is Core, `R` represented):

| Group | Operations | Stage |
|---|---|---|
| Scalars | `prim op(a...)`: arithmetic, comparison, logic, string concatenation, identity (`is`) | C+ |
| Calls | `call f [τ...](a...)` (a function bound by `funs`, or a function value in a variable), `call m.x [τ...](a...)` (a module's member), `type_app f [τ...]` (a polymorphic value applied to types only) | C+ |
| Modules and externals | `member m.x` (a module's member as a value), `external "symbol"` (a C value, or a C function as a closure), `call external "symbol" [τ...](a...)` (the body of a function defined as `external`: a call of the C function, with its type parameters' descriptors) | C+ |
| Closures | `closure f {a...} [τ...]` (a closure of the unit's function `f`, capturing the atoms, and supplying the enclosing functions' type parameters it takes first), `env_field(env, i)` | after closure conversion |
| Tuples | `tuple(a...)` (value components; type components kept for printing), `tuple_field(t, i)` | C+ |
| Records | `record(name = a, var name = a...)`, `record_field(r, name)` | C+ |
| Variants and options | `variant(tag, a)`, `option(tag, a...)` or `option(#n, a...)`, `is_tag(v, tag)`, `payload(v, tag)`, `ordinal(v)` | C+ |
| Arrays | `array(a...)`, `array_rep(n, a)`, `index(a, i)` | C+ |
| Auto values | `auto[τ](a)` | C+ |
| Exceptions | `exception Name` (generative), `exception_payload(e)` | C+ |
| Addresses | `addr x` (a mutable variable), `addr r.name`, `addr t.#i`, `addr a[i]`, `cell(a)` (a fresh cell, for `var(e)`), `load p` | C+ |
| Conversions | `convert(a, plan)` (§8) | R+ |
| Descriptors | `descriptor(τ)`, `instantiate(template, d...)`, `descriptor_param(A)` | after materialization |

Library functions (`dynamic.new`, `arrayOp.size`, ...) are calls of module members, not operations of their own. A
module reference (the `m` of `call m.x` and `member m.x`) is the module itself: one the unit defines (`module m`), or
one it imports (`import m = "path" : Interface`, with its canonical name), never a name to look up. The lowering
maps the symbol a module's name binds (recorded on `TypedModule` and `TypedImportItem`) to it, and a standard
library module used without an import gets an import of its own.
Operations that can raise (calls, array indexing, `payload` of the wrong tag, division) do so through the enclosing
`try` regions (§6.4); the IR does not mark them, as no stage needs edges to handlers.

**Statements** besides `let`:

- `var x: τ = a` declares a mutable variable, and `x := a` assigns it. Only source-level `let var` locals and
  `var`/`out` parameters are mutable; a use of one reads it, and how a `var` parameter is passed (by pointer) is the
  printer's business. `addr x` takes the address of one for a `var` or `out` argument (`@x`). Mutable variables of a
  unit's or module's top level are globals.
- `declare x: τ` declares a variable whose value one later `let x = op` in its scope binds: a named exception made
  inside an expression, whose name the rest of the enclosing scope sees (handlers of a `try` around it included).
  It is a value, not a mutable variable, so closures capture it; reading it before its `let` has run is undefined
  (the type checker allows naming an exception made on a branch that did not run, a gap in
  [tasklist.md](tasklist.md)).
- `let rec (x: τ ...) { body }` binds recursive values: `body` computes each variable's value (a constructor or a
  function), and closures made in it may refer to all of them.
- `store r.name := a`, `store t.#i := a`, `store a[i] := v`, and `store *p := a` store into a `var` component, an
  array element, or the location at an address.
- `do op` evaluates an operation for its effect.
- `funs { fun f [A::K](x: τ, var y: τ): τ { body } ... }` binds functions, top-level, module, and local alike: the
  members of a `funs rec` see one another (and themselves), and those of a plain `funs` do not. An anonymous function
  is bound to a temporary. Closure conversion (§8.2) tells top-level from local functions by their free variables.
- `echo x : τ` and `result x : τ` print a top-level phrase's value (§6.6).

## 6. Control Flow

A **body** is a sequence of statements; a terminator, if any, is last. The terminators are `return a`, `jump
k(a...)`, `break l`, `continue l`, `raise a [with p]`, and `unreachable` (after a call that cannot return, such as
`exit`). Structured statements (`if`, `switch`, `inspect`, `loop`, `try`, `join`) may appear anywhere in a body: a
branch that ends without a terminator continues with the statement after the structured statement.

### 6.1. Conditionals and Switches

```
if a { body } else { body }
switch tag(v) { case cons (c: τ): { body } case nil: { body } else: { body } }
```

`switch` covers `case` on variants and options, by tag; a case may bind the payload. A conditional or `case`
*expression* jumps to a join point with its value (§6.3).

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
  if c { jump k(1) } else { let t: Int = call f(x); jump k(t) }
}
```

Its parameters are the values flowing into it (an SSA block's arguments). Lowering uses a join point for every
construct that produces a value on more than one path: `if`, `case`, `inspect`, and `try` expressions. After the
continuation (which may itself end without a terminator), control continues with the statement after the `join`.
Join points are not values, are never captured by closures, and are jumped to only from their own body; the C
printer prints them as a labeled block with variables for their parameters, or inlines a join point used once.

### 6.4. Exceptions

```
try { body } handle (e: Exception) { body }
raise a
```

`try` is a region: a `raise` in the body, or in any function it calls, transfers to the handler. The handler's
variable holds the exception raised together with its payload: `prim is(e, E)` compares the exception, and
`exception_payload(e)` reads the payload, and `raise e` raises it again with the same payload. Branches of a Quest `try ... when ... else ... end` become tests of the exception's identity in the
handler, re-raising when none matches. The C printer prints `try` with `setjmp`/`longjmp` (as
[c-representation.md](c-representation.md) §7 describes), popping the handler on every way out of the body (falling
off its end, or a jump, break, continue, or return). C makes a non-`volatile` local modified between `setjmp` and
`longjmp` indeterminate afterwards, so the printer declares `volatile` every mutable variable that is assigned in a
`try` body and live in its handler or after the `try`. The IR makes this decidable from the region structure.

### 6.5. Inspect and Dynamic

`inspect` (auto values and dynamic values) is a structured statement, like `switch`: each case tests the value's
run-time type against a type (subtype or exact match) and binds the value's components as of that type. Conversions
of the components are explicit `convert` operations in the case (§8).

### 6.6. Echo

`echo x : τ` prints a top-level phrase's value with its original Quest type (for alias names), as the driver's
`--echo` does; `result x : τ` prints the value of a program's last phrase, as the driver always does.

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

`ir/specialize.py`. Clones a polymorphic function bound by a `funs` statement (top-level, local, or a member of
one of the unit's modules), substituting the type arguments of a call for its type parameters, and redirects the
call to the clone. A call is specialized when it supplies all the function's type parameters, its type arguments
are closed (they mention no type parameter of the functions enclosing the call, for which a clone would have no
descriptor; the enclosing function's own clones specialize the call in turn), and the selective trigger of
[c-representation.md](c-representation.md) §6.4.3 holds: a type argument that is or holds (in tuples, options,
arrays, or cells) a record or variant, decided on its shape; or a `var` or `out` parameter, or a tuple parameter or
result, over the function's type parameters.

The clone has fresh binders throughout and is bound by the same `funs` statement as the original, so it is in scope
wherever the original is and sees the same free variables (a local function's clone captures what the original
does). A clone of a module's function is also a member of the module (`first_spec1`), which calls from outside the
module name. Clones are specialized in turn, and shared by function and type arguments (by identity, never by name),
so a recursive function's clone calls itself; clones made for calls in clones are bounded in depth (16), beyond
which calls stay generic, since polymorphic recursion (a function of `A` calling itself at `List(A)`) would
otherwise specialize without end. Specialization runs *before* closure conversion: a clone's local functions are
part of the clone, and are lifted with it.

### 8.2. Closure-convert

`ir/closure.py`. Lifts every function, top-level and nested alike, to the unit's functions, and replaces each `funs`
statement with lets of `closure f {captures...}`. A function's captures are its free variables (by identity) other
than globals, in the order of their first use; globals are the variables the unit's top levels (its main body and
its modules' initializers) bind outside loops, each bound at most once in a run, which lifted functions use
directly. Since closures do not capture mutable locals, captures are values, copied into the closure; the lifted
function reads them from its environment (`fun f {env} ...`) at its start, `let x = env_field(env, i)`, and uses
those variables in their place. Nested functions are converted first, so a function's captures include what the
closures it makes capture.

A function nested in a polymorphic one takes the enclosing functions' type parameters as its leading type
parameters (same symbols, so its types need no rewriting), which its closure supplies: `closure g {x} [A]` inside
`f [A]`. Recursive local functions that capture one another (or themselves) are made in a `let rec`, whose closures
refer to the variables being bound; the C printer fills in those captures once all the group's closures are
allocated, as the IR interpreter does.

`type_app` stays an operation, now on closures: instantiating a polymorphic closure binds its next type
parameters, which the C printer emits as a runtime instantiation call using descriptor values (§7).

### 8.3. Represent

`ir/represent.py`. A binder's representation is its shape's (`codegen/layout.py`, shared by every backend, which
computes layouts from shapes and caches them per shape), so the pass inserts `convert` wherever a value's
representation or layout differs from the one its use requires. Its decisions are made on shapes. The variables it
makes have types as written, with their alias names, which the IR prints (§5): the types of components of a type as
written (`written_structure`), and the signatures of function types as written, whose type parameters' symbols are
those the call's type arguments and the callee's parts refer to (§4.1). This is the
single conversion operation:

```
let y: Box(Bool) = convert(x, plan)
```

The uses that require representations: a let's copy, an assignment, a return, a jump's argument, and a store take
the type of what they bind, assign, return, pass to, or store into; a call's argument its callee's parameter type,
and its result comes in its callee's result type; a component of a tuple, record, variant, option, or array being
made its component's type, and one read comes in the type its aggregate gives it. A member of one of the unit's
modules is called (or read) from outside at its interface's types and converts to the module's own at the boundary.
A polymorphic call's argument converts first to its parameter's type at the type arguments (a record viewed at the
type argument), then to the parameter's generic representation, in the context of the call's instantiation (and its
result back the same way); a `var` or `out` argument whose location is laid out differently from its parameter is
passed as a temporary of the parameter's representation (a shadow cell), copied in for `var` and out to the location
after the call. An auto value's payload is stored in the auto type's witness-independent layout, its type
component's values at their own type (inspect reads them by the stored descriptor). Plans (`plan`):

| Plan | Meaning |
|---|---|
| none | used as it is |
| `box`, `unbox` | between a native scalar, pointer, record, or variant and its QVal word |
| `record_view` | a record viewed at a supertype, with its offset table (from the runtime map) |
| `variant_tags` | a variant's tag remapped by the static table of a subtype pair, when the cases' order differs |
| `view` | a variant or option converted by the runtime from a bounded type parameter's view at its bound to another type's |
| `cast` | a pointer to an aggregate whose layouts agree in memory, viewed through the other struct |
| `copy` | a new tuple, each component converted by its own plan |
| `runtime` | `quest_convert` between the native layout's descriptor and the generic layout's (a template instantiated with the type arguments): layouts that disagree at a polymorphic call |
| `adapt` | a closure wrapped in a thunk of the target's signature converting its arguments (from the target's parameter types to the closure's) and its result |
| rejected | a conversion that would copy mutable data laid out differently: a compile-time error (`RejectedConversion`) |

Function types are compared with the target's type parameters renamed to the source's, and recursive ones
coinductively. A value of a type parameter bounded by a record, variant, or option is held viewed at its bound, so it
converts to that view whatever the layouts.

Static decisions (whether layouts agree, whether a copy would lose updates) are made by `generic_layout_agrees` and
`generic_layout_copies_mutable_data` in `codegen/layout.py`, which a differential test
(`tests/python/test_layout_differential.py`) checks against the runtime's `quest_layout_equivalent`. After this pass,
every operation's atoms have exactly the representations the operation requires.

**Identity.** A `copy` or `runtime` step builds a new tuple or option, so the converted value is not the same object
as the original, and `is` (object identity for tuples, records, and arrays) can answer differently in compiled code
than in the interpreter: a `Tuple x: P end`, with `P` a record type, passed through an unspecialized polymorphic
function that returns it is no longer `is` the original. A `cast` keeps identity, and specialized calls need no
conversion. This is a documented limitation of the C backend, recorded in [tasklist.md](tasklist.md) to return to;
the conversion matrix (`tests/conversions/generate.py`) tests it, so that the rule is checked rather than incidental.

### 8.4. Materialize descriptors

On the C path, descriptors (§7) are materialized directly by the C printer as it prints: a run-time type's descriptor
is emitted where it is used, keyed by symbol (a type parameter's, the descriptor parameter of its function or of the
closure's environment that captured it; a closed type's static one; a type mentioning type parameters in scope, its
template instantiated with theirs; the generic layout of a polymorphic callee's type, its template with a hole for
each of the callee's type parameters, instantiated with the type arguments'). The future native backend, which has no
C printer to make them, can materialize descriptors as a separate IR pass.

### 8.5. Print C

Prints the last stage as C (`codegen/c/printer.py`): struct declarations and descriptors for the layouts it meets, a
function per IR function, structured statements for structured control, labeled blocks for join points (or inlined
bodies), and `volatile` mutable variables where §6.4 requires. C names derive from symbols and their name hints
(`g_<name>`, `l_<name>`, `qf_<name>`, with a suffix when two symbols share a hint in one scope; see
[name-mangling.md](name-mangling.md)), keeping the generated C readable for debugging. The printer makes no
representation decisions.

### 8.6. Future: CFG and SSA for the native backend

The native AArch64 backend would add, after §8.4: building a control-flow graph from the structured IR (join points
become blocks with arguments), promoting mutable locals whose address is not taken to SSA values, and then
instruction selection, register allocation (simpler on SSA), and emission. The C path does not need these: clang
builds its own SSA and optimizes.

## 9. Stages and Invariants

| Stage | After | Invariants (checked by the verifier) |
|---|---|---|
| **Core** | lowering | ANF: operation arguments are atoms; every variable is bound once and used only in its scope; functions do not use mutable variables of enclosing functions; jumps name enclosing join points with matching arity, and breaks and continues enclosing loops, within one function; returns only in functions; terminators last (`ir/verify.py`). Types are shapes, so aliases and unreduced applications cannot occur. Type parameters are checked on the typed AST (`typechecker/scoping.py`), as abstract types of modules are type variables too |
| **Specialized** | §8.1 | as Core; every specialized call refers to an existing clone |
| **Closed** | §8.2 | no `funs` statement remains; every closure is of one of the unit's functions; those functions use only their parameters, their environment, and globals (the variables the unit's top levels bind outside loops). `type_app` remains, an operation on closures |
| **Represented** | §8.3 | every value is used in the representation its use requires (a let's copy, an assignment, a return, a jump's argument, and a call's arguments and result have the C representations of what they bind, assign, return, or pass to); conversions only through `convert` |
| (Descriptors) | §8.4 | not a separate IR stage on the C path: the C printer makes descriptors as it prints (§8.4) |

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

- **Inlining.** Not planned for the C path (clang inlines). A small inliner over Core IR would mostly help the
  native backend, and specialization of small polymorphic functions.
- **Separate compilation of specializations.** Specializing calls of another unit's functions needs the callee's IR,
  which `.qi` files do not carry; they stay unspecialized unless units ship their Core IR.
