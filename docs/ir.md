# Quest Intermediate Representation (IR)

This document specifies the intermediate representation between the typed AST and the C backend
(`bootstrap/python/quest/ir/`). The self-hosted compiler's IR (`questlang/ir/`, [milestone-4.md](milestone-4.md))
follows it module for module, and its printer writes the same textual form (§10), which the self-hosted suite compares
at every stage.
The IR is one data structure, refined by a sequence of small passes (nanopass style); each pass establishes invariants
that the IR verifier checks. The C printer consumes the last stage. A future native AArch64 backend
([roadmap.md](roadmap.md) step 6) would consume the same stage, adding its own late passes.

---

## 1. Purpose and Position in the Pipeline

```
source → tokens → AST → typed AST ─┬─→ interpreter
                                   └─→ lower → Core IR → specialize → closure-convert → represent
                                                → describe → C printer → C → clang
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
  (`let x = 1 ... let x = 2`) are distinct symbols, so distinct globals.
- **Module records:** a module's exported record, its layout, and its lazy initializer function
  ([c-representation.md](c-representation.md) §5.6). The initializer ends by making the record, a record literal of
  the module's members (`record m_record` after the module's members, `ir.Module.record`), which the printer stores
  in the module's global. A module file's unit is its module alone, with its
  **exports**: its interface's members at the interface's types, bound in its initializer after its members (converted
  from the members, at the abstract types' representations, by the represent pass). Its record holds them, and it
  exports a
  C function `qv_<module>_<member>` for each that is a function or a polymorphic value, the ABI other units call
  (`codegen/c/declarations.py`, `module_function_signature`).
- **Main:** the program's top-level phrases, in order, as the body of an initializer, including echo (§6.6).
- **Imports:** the units it depends on and the symbols it uses from them; interfaces (`.qi`) are unchanged.

Type declarations do not appear as items: the shapes in the IR carry everything later stages need, and the printer
derives C struct declarations from the shapes it meets. After the describe pass (§8.4), the unit lists its **static
data**: the static descriptors its operations refer to, the static offset tables of its record literals, and the tag
maps of its `variant_tags` plans, which a backend emits.

## 4. Types: Shapes and Representations

### 4.1. Shapes

Every binder and every operation's result has a **shape**, the backend's view of a Quest type, computed once per
canonical type (`shape(t)`, cached by the hash-consed type):

| Shape kind | Components |
|---|---|
| `int`, `real`, `bool`, `char`, `string`, `ok`, `word` | — |
| `tuple` | ordered value components (name, shape, `var`); type components are erased from the layout |
| `record` | fields (name, shape, `var`) |
| `variant` | cases (name, payload shape), ordered by name |
| `option` | cases (name, payload component shapes), ordered by name |
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
`rec` references into the canonical graph, so that equal recursive types, however written, share one shape.
Variant and option types are equal whatever order they list their cases in, so their shapes (and canonical forms)
order cases by name: equal types have one layout and one numbering of tags. An option's ordinal counts instead in
the order of its static type as written, which lowering records on the operations that read or make one. Each
shape keeps its canonical type and its structure (the unfolding of a recursive type), from which descriptors and C
names are made. A canonical form names its binders afresh, so a polymorphic function type's shape has type parameters
(and value parameter names) of its own, not those of the type as written. The typed AST keeps its types (with alias
names) for the interpreter and for printing; IR nodes that print types (echo, error messages) carry the original
type alongside the shape.

**Types as written.** Every IR variable's type is the type as written, by design, so that dumps and echo show the
program's alias names (`let p: Point`). Passes decide by shapes; where one needs the written structure of such a
type (a component's type for a variable it makes, a function type's quantifiers and signature, whose symbols a
call's type arguments refer to, or what echo writes), it asks `ir/written.py`, the one module below lowering that
looks inside types as written.

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

Inside an aggregate, a value is held in a **slot** of one word (`slot_representation`): a record or variant as a
pointer to an immutable 16-byte box, a `Bool` or `Char` as a word of its own, anything else as its representation, so
that a slot holds exactly the value's `word` form. The location a `var` or `out` parameter points to holds a record or
variant boxed too (`location_representation`). The represent pass makes boxing at slots explicit (§8.3): a variable
may be **boxed**, holding its record or variant in its slot representation (printed `x: box(T)`): a value read from a
slot is bound boxed and then unboxed, so that storing it into another slot reuses its box, and a mutable variable
whose address is taken, or a `var` or `out` parameter, of a record or variant type is boxed (a use of it reads the
value from its box).

A **layout** describes an aggregate in memory: its shape, together with which positions hold a type parameter's
value stored generically (as a `word`, or for a bounded parameter, as the type argument's own value in the bound's
representation). Since every slot is a word, layouts over type parameters agree in memory; two layouts of the same
shape differ only where a closure's C signature does (a `word` result in a register agrees only with integers and
pointers), or where a module's abstract type is held viewed at its bound. Whether two layouts agree is decided by
`generic_layout_agrees` (§8.3), mirroring
the runtime's `quest_layout_equivalent`.

## 5. Atoms, Operations, and Bindings

The nodes are defined in `ir/nodes.py`, printed by `ir/printer.py`, and checked by `ir/verify.py`. `ir/walk.py` has
the traversals the passes share, and the IR's explicit traversal of nodes' fields (`fields_of` and `rebuild`,
`contents`, `replace_vars`, `view_map_of`), with an entry or case for each class of node, which every walker of fields
uses rather than reading the dataclasses' fields by reflection
([self-hosting-refactorings.md](self-hosting-refactorings.md) §3).

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
| Tuples | `tuple(a...)` (value components; type components kept for printing; `box a` for a record or variant boxed in the tuple's allocation, after §8.3), `tuple_field(t, i)` | C+ |
| Records | `record(name = a, var name = a...)`, `record_field(r, name)` | C+ |
| Variants and options | `variant(tag, a)`, `option(tag, a...)` or `option(#n in (cases), a...)`, `is_tag(v, tag)`, `payload(v, tag)` (for an option, `payload(v, tag) #n`, its tuple starting with the case's ordinal `n`), `ordinal(v) in (cases)` (ordinals count in `cases`, the names of the cases of the option's static type as written) | C+ |
| Arrays | `array(a...)`, `array_rep(n, a)`, `index(a, i)` | C+ |
| Auto values | `auto[τ](a)` | C+ |
| Exceptions | `exception Name` (generative), `exception_payload(e)` | C+ |
| Addresses | `addr x` (a mutable variable), `addr r.name`, `addr t.#i`, `addr a[i]`, `cell(a)` (a fresh cell, for `var(e)`), `load p` | C+ |
| Conversions | `convert(a, plan)` (§8) | R+ |

From the represented stage on, operations also carry the represent pass's decisions about how they reach their
operands' components, printed after them: `via original` or `via proxy` on a read of a tuple's component (and a store
into one, its address, an option's tag or payload, and `is`) of a value that may be a proxy (§8.3); `via stored types`
on a record field read converted by the offset table's stored types; `with runtime offsets` on a record literal whose
view's offset table is found at run time; `converting (plans)` on a `type_app`; and an inspect case's arm.

From the described stage on (§8.4), every run-time use of a type also carries a **descriptor operand**: a descriptor
variable (a `Var` of the `descriptor` type, bound by the function, thunk, or inspect it is used in), `descriptor(τ)`
(a static descriptor; `echo_descriptor(τ)` for echo's), or `instantiate(τ, d...)` (a template τ, whose holes `?0`,
`?1`, ... stand for type parameters, instantiated with their descriptors). Descriptor operands are pure expressions,
not atoms named by lets. They print in place of type arguments (`call f [descriptor(Int)](x)`, `closure g {x}
[descriptor_A]`), and after the operations and plans that use them: `of d` on `is` of QVal words, record literals (with
`with offsets(V <- L)` for a static offset table, or `with runtime offsets(d)`), stored field reads, auto values,
inspect cases, and echo; `view(d1, d2)`, `runtime(d1, d2)`, and `record_view(d)` plans; a thunk's descriptor
variables after an `adapt` plan or a `type_app` (`[qd_0: descriptor]`), whose fields print in braces; an inspect's
witness after its value (`inspect v (witness: descriptor)`), and its arms' converted components with the descriptors
they convert from and to (`component(witness, descriptor(Int))`). A function's descriptor parameters print before
its parameters.

Library functions (`dynamic.new`, `arrayOp.size`, ...) are calls of module members, not operations of their own. A
module reference (the `m` of `call m.x` and `member m.x`) is the module itself: one the unit defines (`module m`), or
one it imports (`import m = "path" : Interface`, with its canonical name), never a name to look up. The lowering
maps the symbol a module's name binds (recorded on `TypedModule` and `TypedImportItem`) to it, and a standard
library module used without an import gets an import of its own. An import carries the record type of its interface
(`ir.Import.record_type`, its members' types as written), which lowering finds in the environment, so that the
backend needs no scope to read an imported member or to declare the functions the module exports.
Operations that can raise (calls, array indexing, `payload` of the wrong tag, division) do so through the enclosing
`try` regions (§6.4); the IR does not mark them, as no stage needs edges to handlers.

**Statements** besides `let`:

- `var x: τ = a` declares a mutable variable, and `x := a` assigns it. Only source-level `let var` locals and
  `var`/`out` parameters are mutable; a use of one reads it, and how a `var` parameter is passed (by pointer) is the
  printer's business. `addr x` takes the address of one for a `var` or `out` argument (`@x`). Mutable variables of a
  unit's or module's top level are globals.
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
of the components are explicit `convert` operations in the case (§8). For an auto value, the represent pass records
how each case gets its components from the payload stored in the witness-independent layout (an `InspectArm`, printed
after the case's binders): which are converted by descriptor, the bound a bounded type parameter's values are viewed
at, and for an exact case whether the stored payload is shared or converted when the run-time layouts agree, and
whether a layout error is raised when they do not.

### 6.6. Echo

`echo x : τ` prints a top-level phrase's value with its original Quest type (for alias names), as the driver's
`--echo` does; `result x : τ` prints the value of a program's last phrase, as the driver always does.

## 7. Type Parameters and Descriptors

In Core IR, a polymorphic function has type parameters (`fun f [A <: P] (x: A): A`) and calls supply type arguments
(`call f [Int] (x)`); shapes mention type parameters as `typevar` symbols. The **describe** pass (§8.4) makes them
values, following the uniform quantifier rule ([c-representation.md](c-representation.md) §6.4):

- each type parameter gets a descriptor variable, a parameter of representation `descriptor` preceding the value
  parameters (`ir.Function.descriptor_params`; one its closure supplies is read from its environment);
- each type argument becomes a descriptor operand: a static descriptor for a type that mentions no type parameter in
  scope, the descriptor variable for a type parameter in scope, and `instantiate(template, d...)` for a type that
  mentions type parameters in scope, whose template has a hole per parameter (§4.2), found by symbol;
- the other run-time uses of types (auto values, `inspect`, `is` of QVal words, record literals, echo, and the plans
  converted by `quest_convert`) take descriptor operands likewise.

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
result, over the function's type parameters, also decided on its shape (so a tuple type written through an alias or
a type operator's application, `Box(A)`, counts as one written out).

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
parameters, which the C printer emits as a runtime instantiation call using descriptor values (§7), converting
arguments and result by the plans the represent pass records on it (§8.3).

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
A polymorphic call's argument converts first to its parameter's type at the type arguments, then to the
parameter's generic representation (a bounded type parameter's values are held at their own view, so nothing
converts for them), in the context of the call's instantiation (and its
result back the same way); a `var` or `out` argument whose location is laid out differently from its parameter is
passed as a temporary of the parameter's representation (a shadow cell), copied in for `var` and out to the location
after the call; a location holding a record or variant boxed agrees with a generic parameter's `word` and is passed
by `cast`. An auto value's payload is stored in the auto type's witness-independent layout, its type
component's values at their own type (inspect reads them by the stored descriptor). Plans (`plan`):

| Plan | Meaning |
|---|---|
| none | used as it is |
| `box`, `unbox` | between a native scalar, pointer, record, or variant and its QVal word |
| `record_view` | a record viewed at a supertype, with its offset table (from the runtime map) |
| `variant_tags` | a variant's tag remapped by the static table of a subtype pair, when the cases' order differs |
| `view` | converted by the runtime between two views' descriptors: a tuple or option upcast to a supertype at which components change view, as a proxy of the original ([c-representation.md](c-representation.md) §5.8); a bounded type parameter's value (at its own view) used at another type; a variant or option from a module's abstract type's view at its bound to another type's |
| `cast` | a pointer to an aggregate whose layouts agree in memory, viewed through the other struct |
| `unproxy` | a cast to a tuple or option type that cannot be a proxy from one that may be: the original serves, as no component changes view |
| `slot_box`, `slot_unbox` | a record or variant put in a new box to be stored into a slot, and read from its box (a boxed variable) |
| `copy` | a new tuple, each component converted by its own plan and read as the plan's access says (an auto value's payload, stored in its witness-independent layout) |
| `runtime` | `quest_convert` between the native layout's descriptor and the generic layout's (a template instantiated with the type arguments): layouts that disagree at a polymorphic call (closures among the components whose C signatures differ) |
| `adapt` | a closure wrapped in a thunk of the target's signature converting its arguments (from the target's parameter types to the closure's) and its result |
| rejected | a conversion that would copy mutable data laid out differently: a compile-time error (`RejectedConversion`) |

Function types are compared with the target's type parameters renamed to the source's, and recursive ones
coinductively. A value of a type parameter bounded by a record, variant, option, or tuple type is held at its own
view, its type argument's, so it converts (`view`) only where it is used at another type; a module's abstract type's
is held viewed at its bound, and converts to that view whatever the layouts.

A type application records its plans (`TypeApp.plans`): for a polymorphic value of no parameters, its value's plan
from the generic result at the type arguments; for a function, those of the thunk the instance is, converting each
argument from the instance's parameter type to the function's generic one and the result back. An inspect case
records its arm (§6.5), and binders converted from the arm's type are bound by lets at the case's
start. A function whose value parameter is annotated with a supertype of its variable's parameter type takes the
variable's (lowering binds the annotation's at entry, and the copy converts).

**Slots and proxies.** The pass's last step (`ir/slots.py`) decides how values are stored into and read from slots,
and read through proxies:

- an operation that reads a record or variant from a slot (a tuple's component, a record's field, an array's element,
  a location, a module's member, a variant's or exception's payload, a QVal word unboxed, and a record literal, made
  in its box) binds a boxed variable, as does a variant case's binder of its payload, and a `slot_unbox` conversion
  the value; storing the value into another slot, or boxing it into a QVal word (a `box` plan from the boxed
  variable), reuses its box;
- an operation that stores a record or variant into a slot (a tuple, record, option, variant, or array being made, a
  store, a cell, an assignment of a boxed mutable variable, a raised exception's payload, and an echoed value, which
  the runtime takes as a QVal word) takes a box: the one remembered, or a new one (`slot_box`); a tuple or record
  being made boxes the others in its own allocation instead (`embedded`, printed `box a`). A payload or echoed value
  is a slot of one word, so the C printer only reinterprets the slot's word as a QVal (and back), and boxes nothing;
- a read of a component of a tuple or option whose type may be proxied (`may_be_proxied`), a write of a tuple's var
  component and its address, an option's tag, and `is` record their access: direct (the value is not a proxy: its
  type cannot be one, or, for a tuple's component read or a copy's, the function made it), from the original (it may
  be a proxy, but the component cannot change view), or through a proxy (checked, and converted);
- a record field read records whether it goes through the offset table's stored types (`RecordField.stored`), and a
  record literal whether its view's offset table is found at run time (`MakeRecord.runtime_offsets`).

Static decisions (whether layouts agree, whether a copy would lose updates) are made by `generic_layout_agrees` and
`generic_layout_copies_mutable_data` in `codegen/layout.py`, which a differential test
(`tests/python/test_layout_differential.py`) checks against the runtime's `quest_layout_equivalent`. After this pass,
every operation's atoms have exactly the representations the operation requires.

**Identity.** `is` is object identity for tuples, records, and arrays, so a conversion must not copy them. Every slot
being a word, a polymorphic call converts aggregates over unbounded type parameters by `cast`; an upcast that changes
a component's view, and a `runtime` conversion at a polymorphic call over a bounded type parameter, make a proxy of
the original rather than a copy, which `is` sees through ([c-representation.md](c-representation.md) §5.8). The
runtime still copies a tuple or option where the target type cannot be proxied (only a closure among its components,
whose C signature changes with a generic layout). The conversion matrix (`tests/conversions/generate.py`) tests the
rule, so that it is checked rather than incidental; `language/view_proxies` tests upcasts.

### 8.4. Describe

`ir/describe.py`, after represent, producing the described stage. It gives every run-time use of a type its
descriptor operand (§5, §7), keyed by symbol:

- a type parameter in scope is its descriptor variable (`ir.DescriptorParam`): a function's, bound by the function
  for each of its type parameters (its own passed before its parameters, those its closure supplies read from its
  environment); a thunk's (an `adapt` plan's, or a function `type_app`'s, `thunk_params`), bound for the type
  parameters of the type it is adapted to, which its plans name by the symbols the represent pass recorded
  (`thunk_symbols`: the target's, and the source's that `shared_signatures` renamed them to); and, in an inspect's
  arms, the inspected auto value's type component (`ir.Inspect.witness`), under the auto type's own symbol;
- a type mentioning no type parameter in scope is its static descriptor; one mentioning some is its template, a hole
  for each, instantiated with their descriptors;
- the generic layout of a polymorphic callee's type (a `runtime` plan's) is its template with a hole for each of the
  callee's type parameters too, instantiated with the type arguments' descriptors.

The uses: type arguments of calls, closures, type applications, and external calls; auto values' witnesses; inspect
cases' types and arms' converted components (and an exact arm's plan); `is` of QVal words; a record literal's own
type, and with runtime offsets its view; a field read through stored types; echo (an echo-only static descriptor for
a closed type, which writes its type components with their alias names); and the `record_view`, `view`, and `runtime`
plans, nested ones included (a copy's view fields, an adapter's fields). A thunk is a C function of its own, passed
only its own type parameters' descriptors: a type there that mentions a type parameter of the enclosing function is
rejected (`UnsupportedDescriptor`; no program does).

A function whose body reads values of a type parameter bounded by a record, variant, option, or tuple type through
the bound (a field, a component, a tag, a payload) gets a view map for it (`ir.ViewMapParam` in `Function.view_maps`, printed as
`view_map` lines at the function's start: the type argument's view map at the bound, from the parameter's descriptor
and the bound's), and each such operation the view map it reads through (`view_map`, printed `through ...`), since
generic code holds those values at their own view ([c-representation.md](c-representation.md) §5.1).

The pass lists the unit's static data (`ir.StaticData`): the static descriptors its operations refer to (templates
among them), the static offset tables of record literals (`ir.OffsetTable`: the view and the layout, registered with
the runtime for dynamic values when both are closed; a module's record is a record literal, §3), and the tag maps of
`variant_tags` plans (`ir.TagMap`), and the types whose aggregates C declares (`types`: those of the unit's
variables, operations, and plans, of its record literals' own layouts and its inspect arms' payloads, of its imports'
interfaces, and of its offset tables, `unit_types`); and each module's abstract types' registrations for dynamic
values ([dynamic.md](dynamic.md) §2.3). An echo of a package with a prefix, whose line is known statically from its type as
written, becomes an echo of its text.

Descriptor operands are small pure expressions rather than values named by lets, by design, so where they are
evaluated is a backend's choice: the C printer evaluates each where it is used, and a native backend could share them.
They could not all be let-bound: the thunks of `adapt` plans and type applications bind their own descriptor variables
without an IR body, and an inspect arm uses the witness's before its case's body begins. (Binding the others would
share little: an instantiation repeated in a function costs a lookup in the runtime's cache, and few programs repeat
one.)

### 8.5. Print C

Prints the last stage as C (`codegen/c/printer.py`): struct declarations and descriptors for the layouts it meets, a
function per IR function, structured statements for structured control, labeled blocks for join points (or inlined
bodies), and `volatile` mutable variables where §6.4 requires. C names derive from symbols and their name hints
(`g_<name>`, `l_<name>`, `qf_<name>`, with a suffix when two symbols share a hint in one scope; see
[name-mangling.md](name-mangling.md)), keeping the generated C readable for debugging. The printer makes no
representation decisions: it prints the plans, boxed variables, accesses, inspect arms, and type applications' plans
the represent pass recorded, and calls `quest_convert` only to print a conversion recorded as one (`view` and
`runtime` plans, a field read through stored types, an inspect arm's converted components). It prints the
descriptors it is given and makes none (§8.4): it names descriptor variables (a function's parameters, a thunk's
`qd_<k>`, an inspect's `->type_desc`), declares the static descriptors (with those of their parts) and the offset
tables and tag maps of the unit's static data, and calls `quest_instantiate_descriptor` for an instantiated template.
It declares the structs of the aggregates of the unit's listed types (`ir.StaticData.types`), and the C compiler
checks that every struct the C names is among them. What it still decides is how to spell the IR in C: the C
signatures of thunks and of a module file's exported functions, the `static_assert`s of the tuple casts it prints,
and the reinterpretation of a slot's word as a QVal (and back) for a variant's or exception's payload and an echoed
value, which the slots pass gives it in their slot forms.

### 8.6. Future: CFG and SSA for the native backend

The native AArch64 backend would add, after §8.4 (whose descriptor operands it would materialize as it sees fit):
building a control-flow graph from the structured IR (join points
become blocks with arguments), promoting mutable locals whose address is not taken to SSA values, and then
instruction selection, register allocation (simpler on SSA), and emission. The C path does not need these: clang
builds its own SSA and optimizes.

## 9. Stages and Invariants

| Stage | After | Invariants (checked by the verifier) |
|---|---|---|
| **Core** | lowering | ANF: operation arguments are atoms; every variable is bound once and used only in its scope; functions do not use mutable variables of enclosing functions; jumps name enclosing join points with matching arity, and breaks and continues enclosing loops, within one function; returns only in functions; terminators last; ordinal operations record a permutation of their option's cases, and option payloads their ordinals (`ir/verify.py`). Types are shapes, so aliases and unreduced applications cannot occur. Type parameters are checked on the typed AST (`typechecker/scoping.py`), as abstract types of modules are type variables too |
| **Specialized** | §8.1 | as Core; every specialized call refers to an existing clone |
| **Closed** | §8.2 | no `funs` statement remains; every closure is of one of the unit's functions; those functions use only their parameters, their environment, and globals (the variables the unit's top levels bind outside loops). `type_app` remains, an operation on closures |
| **Represented** | §8.3 | every value is used in the representation its use requires (a let's copy, an assignment, a return, a jump's argument, and a call's arguments and result have the C representations of what they bind, assign, return, or pass to; a boxed value's is its slot representation); conversions only through `convert`; slots (components of tuples, records, and arrays being made, stores, cells) take records and variants boxed, but for those embedded; only variables of record or variant types are boxed |
| **Described** | §8.4 | every run-time use of a type has its descriptor operands (type arguments, auto values' witnesses, inspect cases and arms, `is` of QVal words, record literals, stored field reads, echo, the plans converted by descriptor), and every function its type parameters' descriptor variables; every descriptor variable an operand uses is bound where it is used and of the `descriptor` type (a thunk's plans use only the thunk's own); no static descriptor or template mentions a type parameter whose descriptor is a variable there (nor, in a thunk, one of the enclosing function's); the static descriptors and tables operations refer to are the unit's static data. The IR interpreter also checks that each operation's descriptors describe the types they stand for |

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

and, described (§8.4; types print as written, representations follow from them, and the reads of a list that may be
a proxy go through it):

```
fun length [A::TYPE](descriptor_A: descriptor, l: List(A)): Int {
  join k3(r: Int) {
    return r
  } in {
    switch tag(l) via proxy {
      case cons (c: Tuple head: A tail: List(A) end) via (proxy, proxy): {
        let t: List(A) = tuple_field(c, 1) via proxy
        let n: Int = call length [descriptor_A](t)
        let r.1: Int = prim +(1, n)
        jump k3(r.1)
      }
      else: {
        jump k3(0)
      }
    }
  }
}
```

A caller at `Bool` passes its list as it is (every slot is a word) and the descriptor of `Bool`:

```
let n: Int = call length [descriptor(Bool)](flags)
```

## 11. Open Questions

- **Inlining.** Not planned for the C path (clang inlines). A small inliner over Core IR would mostly help the
  native backend, and specialization of small polymorphic functions.
- **Separate compilation of specializations.** Specializing calls of another unit's functions needs the callee's IR,
  which `.qi` files do not carry; they stay unspecialized unless units ship their Core IR.
