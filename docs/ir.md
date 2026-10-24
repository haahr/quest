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

The C emitter the IR replaced (`codegen/c_emitter.py` and `c_analysis.py`, deleted in step 6, §12) translated the
typed AST directly, and on the way reduced types, chose representations, converted values between them, lifted
closures, specialized functions, and printed C. Each of these is a pass over the IR, so that:

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
| `rec` | a reference into a recursive group: the canonical recursive graph of `codegen/canonical.py` |

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

The current emitter's trigger differs on tuples: `is_specialization_needed` returns true for any tuple type
(reaching its own tuple case never), so it specializes for a tuple, option, or list of scalars when the type
argument arrives expanded (`B`, an alias the C compilation mode expands) but not as an alias application
(`Box(Int)`). The pass follows the rule as stated, seeing through aliases.

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
allocated (the deferred captures of today's `_emit_rec_bindings`), as the IR interpreter does.

`type_app` stays an operation, now on closures: instantiating a polymorphic closure binds its next type
parameters, which the descriptor stage (§7) makes descriptor values and the C printer a call of the runtime's
instantiation, rather than a generated closure per use (a change from the first plan, which made it a closure over
the function and its type arguments).

### 8.3. Represent

`ir/represent.py`. A binder's representation is its type's (`codegen/layout.py`, shared by every backend), so the pass
inserts `convert` wherever a value's representation or layout differs from the one its use requires. This is the
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
`generic_layout_copies_mutable_data` in `codegen/layout.py`, which a differential test checks against the runtime's
`quest_layout_equivalent` (§12, step 0). After this pass, every operation's atoms have exactly the representations
the operation requires.

**Identity.** A `copy` or `runtime` step builds a new tuple or option, so the converted value is not the same object
as the original, and `is` (object identity for tuples, records, and arrays) can answer differently in compiled code
than in the interpreter: a `Tuple x: P end`, with `P` a record type, passed through an unspecialized polymorphic
function that returns it is no longer `is` the original. A `cast` keeps identity, and specialized calls need no
conversion. This is a documented limitation of the C backend, recorded in [tasklist.md](tasklist.md) to return to;
the conversion matrix (§12, step 0) tests it, so that the rule is checked rather than incidental.

### 8.4. Materialize descriptors

§7. *Done in the C printer, rather than as a stage of its own:* a run-time type's descriptor is printed where it is
used, keyed by symbol (a type parameter's, the descriptor parameter of its function or of the closure's environment
that captured it; a closed type's static one; a type mentioning type parameters in scope, its template instantiated
with theirs; the generic layout of a polymorphic callee's type, its template with a hole for each of the callee's
type parameters, instantiated with the type arguments'). A separate pass would only rename the same decisions; the
native backend, which has no C printer to make them, can add one.

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
| **Core** | lowering | ANF: operation arguments are atoms; every variable is bound once and used only in its scope; functions do not use mutable variables of enclosing functions; jumps name enclosing join points with matching arity, and breaks and continues enclosing loops, within one function; returns only in functions; terminators last (`ir/verify.py`). Types are shapes, so aliases and unreduced applications cannot occur. Type parameters are checked on the typed AST (step 1), as abstract types of modules are type variables too |
| **Specialized** | §8.1 | as Core; every specialized call refers to an existing clone |
| **Closed** | §8.2 | no `funs` statement remains; every closure is of one of the unit's functions; those functions use only their parameters, their environment, and globals (the variables the unit's top levels bind outside loops). `type_app` remains, an operation on closures |
| **Represented** | §8.3 | every value is used in the representation its use requires (a let's copy, an assignment, a return, a jump's argument, and a call's arguments and result have the C representations of what they bind, assign, return, or pass to); conversions only through `convert` |
| (Descriptors) | §8.4 | not a stage: the C printer makes descriptors as it prints (§8.4) |

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
- **A differential layout test.** *Done* (`tests/python/test_layout_differential.py`). For every shape at every type
  argument, and seeded random compositions of shapes, a generated program makes a dynamic value of each type in
  generic code (through a first-class value, so that it is not specialized) and in native code, and a harness
  appended to its C compares the two descriptors with `quest_layout_equivalent`. The test asserts soundness (wherever
  `generic_layout_agrees` says the layouts agree, the runtime must) and reports where the compiler is only
  conservative; today the two agree on all 124 pairs. Getting the descriptors from dynamic values, rather than from
  `c_types.py` alone as first planned, uses the emitter's descriptor emission, so the test will move to the IR
  backend's in step 5.
- **A baseline.** *Done* (`tests/perf/measure.py`, saved in `tests/perf/baseline.json` at `cf47e75`): time in the C
  emitter and size of the C for the 158 compiled test programs (15.3s, 49 MB), and run times of three benchmarks
  that cross polymorphic boundaries heavily (`tests/perf/*.quest`: generic lists at `Int`, tuples of records copied
  through an unspecialized function, closures adapted by thunks; 0.31–0.44s each). `python tests/perf/measure.py`
  compares a later state with it, on the same machine.

**Step 1: Identity in the typechecker.** *Done.*
- A well-scopedness check over the typed AST (`quest/typechecker/scoping.py`), run after type checking when
  `QUEST_CHECK_SCOPES=1`, which the test runners set: a locally bound variable is used only within its binder's
  scope, a polymorphic function's `type_param_ids` are its own type's quantifiers, and a type mentioning a
  function's type parameter occurs only inside that function. All 159 golden test programs, and the library modules
  they compile, pass it.
- It found no more re-elaborations with fresh symbols. It did find that `QAllType` treated quantifier bounds as
  outside its binder (`All(A B <: A) T` had `A` free, and substitution reached the bound's `A`); quantifiers are now a
  telescope, each bound seeing the quantifiers before it as bound.

**Step 2: Shapes.** *Done.*
- `ir/shapes.py`: `shape(t)` and the shape kinds of §4.1, built on the canonical forms of `codegen/canonical.py` and
  cached per canonical type, with unit tests (`tests/python/test_shapes.py`: equal types share one shape, aliases
  and applications reduce, recursion is a cycle of shapes, and every type of a set of programs covering all kinds
  has a shape). Over the whole test corpus, about 12,000 types have shapes; only type operators (`Fun(A::K) T`, in
  type declarations), which are not the types of values, have none.
- Abstract types of modules are elaborated as type variables, so their shapes are `typevar`s, told apart from type
  parameters by symbol where descriptors are made (§7).
- The current emitter keeps its structural type tests; it is replaced, not migrated.

**Step 3: IR and lowering to Core.** *Done.*
- `ir/` package: node types (`ir/nodes.py`, §5, §6), the textual form (`ir/printer.py`, §10), and the verifier for
  the Core stage (`ir/verify.py`, §9). Variables are objects, bound once and used by reference; the printer gives
  them distinct names.
- Lowering from the typed AST (`ir/lower.py`), construct by construct: expressions, blocks and join points, loops,
  `case`, `try`, `inspect`, functions and type parameters, tuples with type components, modules and their records,
  and top-level phrases and echo.
- An `ir_core` pipeline phase (`--stop-after ir_core`) prints a program's Core IR; the test runner lowers and
  verifies every non-generated golden test with it (`QUEST_CHECK_IR=1`), with goldens in `tests/golden/ir_core` and
  targeted tests in `tests/python/test_ir_lower.py`. The generated tests (conversions, astprint) skip the phase.
- Additions to the IR as specified: `LetRec`, for recursive values (`let rec self: T = tuple ... end`), whose
  closures refer to the variables being bound; `Echo` and `EchoText`, for top-level phrases printed as the
  interpreter does; and `Builtin` and `ModuleMember` (with no member) for built-in functions and modules used as
  values.
- The typed AST gained what the lowering needs to bind by symbol: `TypedException.symbol`, the symbol a named
  exception's name binds, and `TypedTuple.labels`, the symbols of a tuple's component labels.
- A named exception made inside an expression is visible to the rest of its scope, including handlers of a `try`
  around it, so the lowering declares it (`declare`) before the binding (or at the start of the function body) that
  contains it, and binds it where the exception is made (step 4 replaced a first version, a mutable variable, which
  closures could not capture).

**Step 4: Passes.**
- Fix first: a nested function using a hoisted exception of its enclosing function failed verification, since
  closures do not capture mutable variables. *Done:* `declare` (§5) declares a variable whose value one later let
  binds, so the exception is a value that closures capture.
- An IR interpreter (`interpreter/ir_interp.py`), run by the test runner on the IR after each stage and compared with
  `tests/golden/run`, so that a pass that changes a program's meaning is caught at that pass. *Done for Core:* the
  `run_ir_core` phase runs every golden test program's Core IR, the generated ones included. It uses the source
  interpreter's values, and the modules a unit imports (the standard library included) are loaded and run by the
  source interpreter; IR functions are built-in functions to it, so either kind of function calls the other. The
  run error tests are not run through it, since the IR keeps no source offsets to locate its errors. An imported
  module's path, canonical name, and interface now are in the unit (`import` in the textual form), where the
  interpreter (and the C printer) find them.
- Specialize (§8.1), with calls matched by symbol, including calls of local polymorphic functions (lifting the
  restriction in [tasklist.md](tasklist.md)); the trigger stays selective (record or variant type arguments).
  *Done:* the `ir_specialized` stage, run on every golden test (`run_ir_specialized`), with goldens for 16 programs
  and targeted tests in `tests/python/test_ir_specialize.py`. Before it, IR variables and functions got their
  shapes from their types (a pass rewriting types cannot leave the two disagreeing), and module references became
  the modules and imports themselves.
- Closure-convert (§8.2). *Done:* the `ir_closed` stage, run on every golden test (`run_ir_closed`), where the IR
  interpreter gives lifted functions only the globals, so that a missed capture fails; goldens for 15 programs, and
  targeted tests in `tests/python/test_ir_closure.py`. The unit records its stage, which the verifier checks
  against.
- Each pass with its stage's verifier on every test, and dump goldens for a subset of 15 to 20 programs chosen to
  exercise it (Core IR keeps goldens for every program).
- *Changed:* represent and descriptors move to step 5, built with the C printer. The IR interpreter checks a pass
  that changes a program's meaning, but representations do not change meaning: to the interpreter, `convert` is an
  identity (but for copies), so only the C a representation is printed as shows whether it is right.

**Step 5: Represent, descriptors, and the C printer, as an alternative backend, in vertical slices.**
- Represent (§8.3): representations, plans, and `convert` insertion, including variant tag maps decided from cases
  (closing the variant tag-map task). Materialize descriptors (§7), with type parameters keyed by symbol. Each with
  its stage's verifier and dump goldens for a subset, as the earlier passes.
- `codegen/c_printer.py` printing the descriptor stage (§8.5), reusing `c_declarations.py` for struct declarations,
  descriptors, and adapters where it fits.
- A driver option (`--backend ir`) and a test runner mode running every compiled test through it.
- Built a slice at a time, each slice's representations checked by compiling and running the tests it covers:
  scalars, strings, functions, closures, control flow, exceptions, and library calls first; then tuples, records
  (views), variants (tag maps), options, and arrays; then polymorphic calls (generic layouts, conversion plans,
  descriptors), function subtyping (adapters), auto values and `inspect`, and modules. Done when every compiled test
  passes through it and the conversion matrix matches.
- Changes to the current emitter are frozen from here, except for fixes needed to keep tests passing.
- *Slice 1 done:* `ir/represent.py` (box and unbox plans: values of type parameters held as QVal words),
  `codegen/c_printer.py` (functions as C functions taking their closure's environment, static closures for those
  capturing nothing, direct calls of known closures, globals at file scope, join points and loop exits as labels, try
  regions as setjmp handlers popped on every way out, `volatile` for what a try body assigns, module calls and
  records by the current emitter's ABI, declarations through `c_declarations.py`), and the `codegen_c_ir` and
  `run_c_ir` phases (`run_tests.py --phase run_c_ir`, not yet part of the default run; now `codegen_c` and
  `run_c_compiled`, step 6): 50 of the 159 golden programs compile and run through it. The rest need tuples, records, options, variants, arrays, `inspect`,
  `type_app`, and the conversions between layouts, which raise until their slices.
- *Slice 2 done:* tuples, records (offset tables, static for literals viewed at width subtypes and from the runtime
  map otherwise, fields read through stored types), variants, options, and arrays (wide for records and variants),
  as the current emitter lays them out; plans `record_view`, `variant_tags`, `cast`, and `copy` (a tuple whose
  components convert); out arguments whose location's type is a supertype of the parameter's (through a
  temporary, converted into the location after the call); calls of the unit's modules' members converted at the
  module's boundary (its interface's types, abstract ones among them, to its own); and a polymorphic call's
  arguments converted to the parameter types at the type arguments before their generic ones (and results back).
  The standard library's `arrayOp.new`, `size`, `get`, and `set` lower to the IR's array operations, since arrays of
  records and variants are stored wide and could not be passed to the generic functions. Two fixes in earlier
  passes came of it: a clone's type is made from its parameters (a function's variable may be typed with other
  quantifier symbols than its type parameters), and a closure capturing only the enclosing functions' type
  parameters has an environment for their descriptors. 115 of the 159 programs compile and run.
- *Slice 3 done, and step 5 with it:* polymorphism. Plans in a call's layout context (`runtime` conversions
  between native and generic layouts by descriptor templates, casts where they agree, rejection where a copy would
  lose updates), descriptor templates for types mentioning type parameters in scope, closure adapters (`adapt`
  thunks), `type_app` (a closure binding the type arguments' descriptors, converting arguments and result; or a
  polymorphic value's instance), shadow cells for `var` and `out` arguments of generic parameters, bounded type
  parameters held viewed at their bounds (`view` back from the bound), and auto values and `inspect`. Represent is
  a stage of its own (`ir_represented`, run and verified on every test, with goldens for 16 programs). Every golden
  program and every run error test compiles and runs through the IR backend, and `run_c_ir` is part of the default
  run. The conversion matrix's known identity failures (`identity_known_failures`) are skipped for it as for the
  current emitter: copies change identity in both.

**Step 6: Switch and delete.** *Done.*
- Make the IR backend the default, for programs and for module files (`module_compiler.py`, `build/engine.py`);
  the IR's phases take the old names (`codegen_c`, `run_c_compiled`), and the emitter's phases go.
- Compare emission time, C size, and benchmark run times with the step 0 baseline, and record them here. A
  regression does not block the switch; one over about 20% becomes a task in the task list.
- Delete the emitter in the step's last commit, once both suites pass through the IR alone (no period behind a
  flag).
- Delete `c_emitter.py`, most of `c_analysis.py`, and the parts of `c_types.py` that only the emitter used. *Done:*
  `c_emitter.py`, `c_analysis.py` (all but `collect_aggregate_types`, now in `c_declarations.py`), and
  `quest/analysis/` (the emitter's closure analysis) are deleted, along with what only they used of
  `c_declarations.py` (lambda environments and trampolines, the emitter's module declarations); everything left in
  `c_types.py` is still used. The printer's own helpers from the emitter moved into it (`_value_kind`, the existential
  echo) and into `c_declarations.py` (`emit_fun_type_adapters`).
- *Module files: done.* `module_compiler.py` and `BuildEngine` compile through the IR (`codegen/c/backend.py`), so the
  standard library is IR-compiled, and both suites pass with the emitter's programs linking against it (its ABI is
  the emitter's). Module files needed exports (§3) and externals: a function defined as `external` calls its C
  function (`call external`), and an external C function used as a value is a static closure over a thunk calling
  it (or called directly, where a variable bound to it is called). A program built by `quest compile` is now silent
  unless built with `--print-result`, as [testing.md](testing.md) says; the emitter printed a final expression
  phrase's value regardless.
- *The switch: done.* The IR's printer is the `codegen_c` phase, after the IR's phases in `compile_pipeline()`, and
  `run_c_compiled` runs what it prints; the emitter's phases and `codegen_c_ir`/`run_c_ir` are gone.
- *Performance* (`tests/perf/measure.py`, against the emitter's baseline at `cf47e75`, same machine): C generation
  for the 158 compiled programs takes 6.6s (0.43x) and produces 21 MB of C (0.43x). Those ratios flatter the IR: the
  emitter compiled imported modules with source files into each program's C, and the IR links them, compiled once.
  Like for like, the 26 programs with no imports: 0.52x the time, 0.70x the C. Benchmark run times:
  `copied_records` 0.98x, `generic_closures` 1.01x, `generic_lists` 1.13x, all within the 20% bar.
  `tests/perf/baseline.json` stays the emitter's, for comparison.
- *Afterwards*, for backends to come: the C backend's modules moved to `codegen/c/` (`printer.py`, `declarations.py`,
  `types.py`, `headers.py` for interfaces' C headers, `compiler_runner.py`, `backend.py`), and what a native backend
  would share stayed in `codegen/`: layouts and representations (`layout.py`), canonical forms (`canonical.py`),
  descriptors' type-level forms (`descriptors.py`), linkage names (`symbols.py`), and the passes (`backend.py`). The
  represent pass decides from representations rather than C types, and only C compilation's drivers import
  `codegen/c/` (`tests/python/test_dependencies.py`). (The file names in the steps above are as they were then.)
- Update [codegen-c.md](codegen-c.md) and [c-representation.md](c-representation.md) (§5.1 and §6.4 around the
  `convert` plans), and the task list: close the variant tag-map task, and note what is now in place for top-level
  rebindings (distinct globals per symbol) and for specializing local functions.

**Risks.** Step 3 and step 4 are the bulk of the work: the lowering covers all 62 typed AST node kinds, and the
represent pass absorbs the conversion logic now spread over the emitter. Running the full suite through the new
backend (step 5) is the measure of parity. Until step 6, fixes may land twice; freezing the current emitter at step 5
keeps that short.
