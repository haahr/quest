# questlang/ir: the intermediate representation and its passes

This directory sits between the type checker and the backends. It takes a typed program (`typedAst.Program`, from
[`../typechecker`](../typechecker)) and lowers it into an intermediate representation (IR), then refines that IR
through a fixed sequence of small passes until every decision a backend needs has been made explicitly in the IR
itself: which functions are specialized, which become closures, how each value is represented in memory, where values
are converted between representations, and which run-time type descriptors each operation needs. The result, the
*described* IR, goes either to the C printer ([`../codegen/c`](../codegen/c)) or to the SSA builder
([`../ssa`](../ssa)), from which the arm64 backend (the default) and `ssac` compile. The backends only print or
translate what the IR says; they make no representation decisions of their own.

The directory does not decide how values are laid out. That knowledge lives one layer down, in
[`../repr`](../repr/README.md) (shapes, layouts, representations, descriptors' type-level forms), which the IR's passes
consult and which the backends consult again when they emit code.

## One IR, refined in stages

There is a single set of node types, defined in [`nodes.int.quest`](nodes.int.quest). Each pass rewrites a unit in
place and leaves it in the next *stage*; a stage is the same data structure with stronger invariants (the "nanopass"
style). The main ideas:

- **A-normal form (ANF).** Every intermediate value is named by a `let`, and operations take only *atoms*, variables
  and constants. `f(g(x) + 1)` becomes three lets. This makes evaluation order and every temporary explicit.
- **Structured control flow with join points.** `if`, `switch`, `loop`, and `try` stay structured, so the C printer
  writes readable structured C and exceptions remain regions rather than edges. A construct that produces a value on
  more than one path (an `if` expression, a `case`) jumps to a *join point*: a local continuation with parameters,
  the structured equivalent of an SSA block with arguments.
- **Variables are objects.** A `Variable` is a record with identity, bound by exactly one binder; every use refers to
  that same record. Names are only hints for printing, so passes never confuse two variables that happen to share a
  name. Lowering maps each typed-AST symbol to its variable once.
- **Types as written, decisions by shape.** Every variable keeps its Quest type as the program wrote it, alias names
  included, so dumps read like the source. Passes never test a type's syntax directly; they ask for its *shape*
  ([`../repr/shapes`](../repr/shapes.int.quest)), which strips aliases, reduces type-operator applications, and makes
  recursion explicit.
- **Types do not disappear.** Quest needs types at run time (`Dynamic`, auto values, `inspect`, echo), so type
  abstraction and application stay explicit until the describe pass turns them into descriptor values.

A unit (`nodes.Unit`) corresponds to one compilation unit: a program, a module file, or one REPL input. It holds a
main body, the modules it defines (each with an initializer body, its members, and its exported record), its imports,
its functions (after closure conversion), and, once described, its static data.

Here is a small program and its Core IR, as `quest --stop-after ir_core` prints it (source positions omitted):

```
let twice(A::TYPE f: All(x: A) A x: A): A = f(f(x))
let addTo(n: Int): All(x: Int) Int = fun(x: Int): Int x + n
let r = twice(:Int addTo(1) 3)
```

```
main {
  funs {
    fun twice [A::TYPE](f: Fun(x: A): A, x: A): A {
      let %1: A = call f(x)
      let %2: A = call f(%1)
      return %2
    }
  }
  funs {
    fun addTo(n: Int): Fun(x: Int): Int {
      funs {
        fun f.1(x.1: Int): Int {
          let %3: Int = prim +(x.1, n)
          return %3
        }
      }
      return f.1
    }
  }
  let %4: Fun(x: Int): Int = call addTo(1)
  let r: Int = call twice [Int](%4, 3)
}
```

Functions are still nested (`f.1` refers to `addTo`'s `n` freely), the call of `twice` still carries its type argument
`[Int]`, and nothing yet says how an `Int` is passed to code that expects an `A`.

## The flow of passes

[`pipeline.mod.quest`](pipeline.mod.quest)'s `runPasses` is the whole sequence after lowering; every backend, the JIT,
and the build call it. Read top to bottom:

| Stage after it | Modules | What they do |
|---|---|---|
| Core | `lower`, `captures` | typed AST to ANF IR |
| Simplified | `simplify`, `inline`, `contify` | optimize while functions are nested and types explicit |
| Specialized | `specialize` | clones polymorphic functions for some type arguments |
| Closed | `closure` | lifts every function to the top, making closures |
| (Closed) | `unbox` | marks small tuple results that need no allocation |
| Represented | `represent`, `slots` | insert every conversion between representations |
| Described | `describe`, `thunks` | give run-time types descriptors; make wrappers into functions |

**Lowering** ([`lower.mod.quest`](lower.mod.quest)) walks the typed AST, emitting statements into the current body and
returning the atom that holds each expression's value. Its pre-pass, [`captures`](captures.int.quest), finds the
mutable local variables that nested functions use; lowering holds each in a box (a one-component mutable tuple) so
that closures share it and never capture a mutable variable directly. Lowering has three entry points: `lowerProgram`
for a program, `lowerModuleFile` for a module compiled on its own, and `lowerPhrases` for a REPL or JIT input, whose
top-level bindings become fields of a module record of their own ([`../../docs/jit.md`](../../docs/jit.md)).

**The simplifier** ([`simplify.mod.quest`](simplify.mod.quest)) is the optimizer. It runs in rounds (at most six) of
copy and constant propagation, constant folding, dead-code removal, and the reduction of `switch`es and projections on
values built in the same function. Each round also inlines calls ([`inline`](inline.int.quest), which measures
functions and expands a call) and then *contifies* ([`contify`](contify.int.quest), MLton's term): a function whose
only uses are one outside call and its own tail calls becomes a loop at that call. Working on the Core IR is
deliberate: inlining a higher-order call here removes a closure that later passes would allocate, and inlining a
polymorphic call at a concrete type means the represent pass never sees a conversion. In the program above, the
simplifier inlines everything and `r` becomes the constant `5`. A recursive variant shows the other tools:

```
let rec apply(A::TYPE n: Int f: All(x: A) A x: A): A = if n is 0 then x else apply(:A n - 1 f f(x)) end
let r = apply(:Int 10 addTo(1) 3)
```

Here `apply` is recursive, so it is not inlined; but its parameter `f` is passed unchanged on every recursive call, so
the simplifier specializes `apply` on the known function `addTo(1)`, inlines `x + 1` into the copy, and contification
turns the copy into a `loop` with mutable `n` and `x`, leaving a join point to receive the result. The bootstrap has no
simplifier; its IR goes straight from Core to Specialized.

**Specialization** ([`specialize.mod.quest`](specialize.mod.quest)) handles polymorphic calls the simplifier left.
Quest compiles polymorphic code once, generically, with values of a type parameter held in one machine word; that is
cheap for integers and pointers but costly for records and variants (16 bytes each, boxed to fit a word). So a call
gets a clone of the function, with the types substituted, when its type arguments are closed and either are or hold
records or variants, or the function has `var`, `out`, or tuple parameters over its type parameters (the "selective
trigger"). Copying is [`clone`](clone.int.quest)'s, which the inliner shares.

**Closure conversion** ([`closure.mod.quest`](closure.mod.quest)) lifts every function to the unit's list of functions.
Each `funs` statement becomes `let`s of `closure f {captures...}`, and the lifted function reads its captures from its
environment with `env_field`. Variables bound once at a unit's or module's top level are *globals*, which functions
read directly instead of capturing ([`walk`](walk.int.quest)'s `globalVariables`). A function nested in a polymorphic
one takes the enclosing type parameters as extra leading ones, which its closure supplies. After this stage a backend
can call a closure's code directly when it knows which closure a variable holds (`walk.knownClosures`).

**Unboxed results** ([`unbox.mod.quest`](unbox.mod.quest)) marks functions that return a fresh one- or two-component
tuple of scalars to callers that only read its components, so the backends return the components in registers.

**Representation** ([`represent.mod.quest`](represent.mod.quest)) is where the IR becomes ABI-aware. Every type has a
representation (an `Int` is a 64-bit integer, a record a 16-byte pair of object pointer and offset table, a value of an
unbounded type parameter a generic `QVal` word, and so on; [`../repr/layout`](../repr/layout.int.quest)). Wherever a
value's representation differs from what its use expects, the pass inserts `convert(x, plan)`. A *plan*
(`nodes.Plan`) is one of a dozen kinds: `box`/`unbox` between a native value and a `QVal` word; `record_view` for a
record used at a supertype (a new offset table, no copy); `variant_tags` to renumber tags; `view` to wrap a tuple or
option in a *proxy*, a run-time view that converts components as they are read, so that an upcast never copies a
mutable object and identity (`is`) is preserved; `adapt` to wrap a closure whose calling convention differs; `runtime`
to convert by descriptor at run time; and others. The pass's last step, [`slots`](slots.int.quest), decides how each
aggregate's one-word *slots* are read and written: records and variants are stored in slots as pointers to immutable
boxes, and a read of a tuple component that might be a proxy is marked `direct`, `original`, or `proxy`.

**Description** ([`describe.mod.quest`](describe.mod.quest)) makes run-time types into values. A *descriptor* is the
runtime's data structure describing a type. Every polymorphic function gets a descriptor parameter per type parameter,
and every run-time use of a type gets a *descriptor operand*: the descriptor variable for a type parameter in scope, a
static descriptor for a closed type, or `instantiate(template, d...)` for a type built from parameters in scope (a
template with a hole per parameter). The pass also collects the unit's static data (`nodes.StaticData`): the static
descriptors, record offset tables, and tag maps a backend must emit. Finally [`thunks`](thunks.int.quest) turns the
small wrapper functions the plans need (adapters, type-application thunks, closures of external C functions) into
ordinary functions of the unit, so every backend compiles them like any other.

Compiled without the simplifier, as the bootstrap compiles it, the first example's main body ends up described like
this:

```
let %1: Fun(x: Int): Int = call addTo.1(1)
let %2: Fun(x: A): A = convert(%1, adapt)
let %3: A = convert(3, box)
let r: A = call twice.1 [descriptor(Int)](%2, %3)
let r.1: Int = convert(r, unbox)
```

`twice` is compiled once for all `A`, so its argument `3` is boxed into a word, the closure is adapted to take and
return words, the type argument `[Int]` has become the static descriptor of `Int`, and the result is unboxed.

## How repr/ feeds the stages

The IR's passes do not compute layouts; they ask [`../repr`](../repr/README.md). Lowering and every later pass decide by
shapes (`repr/shapes`), and where a pass makes a variable whose type is a component of a written type, it asks
`repr/written` so that the alias names survive. Specialization's trigger and the inliner's limits ask whether a type
holds records or variants, or whether generic code would lay it out differently (`repr/genericlayout`). The represent
pass is built on `repr/layout` (representations, slot representations, whether a tuple may be a proxy) and
`repr/genericlayout` (whether a native and a generic layout agree, and whether a conversion would copy mutable data,
which is rejected at compile time). The describe pass builds templates and holes from `repr/descriptors`. After the IR,
the backends use the rest of `repr/` (static data, object layouts for the collector, the runtime's struct layouts,
linked symbol names) to emit what the described IR names.

## Checking and inspecting the IR

- [`printer`](printer.int.quest) writes the textual form shown above; each stage can be dumped with
  `--dump-after ir_core` (or `ir_simplified`, `ir_specialized`, `ir_closed`, `ir_represented`, `ir_described`), and
  those dumps are golden tests (`tests/golden/ir_*`). [`stages`](stages.int.quest) names the stages, in order: a
  unit's `stage` is one of them, and the driver takes its `ir_STAGE` and `run_ir_STAGE` phases from their names.
- [`verify`](verify.int.quest) and [`verifycore`](verifycore.int.quest) check each stage's invariants (ANF, scoping,
  jumps only to enclosing join points, no `funs` after closure conversion, conversions only after represent, every
  descriptor bound where used). `runPasses` runs them after each pass when `QUEST_CHECK_IR=1`, which the test runners
  set.
- [`walk`](walk.int.quest) holds the traversals the passes share. Quest has no reflection, so a traversal lists
  each node's fields case by case, and two do it for the rest: `visitOp` and `visitStmt` call a `Visitor`'s function
  for each atom, used variable, binder, body, function, type, plan, and module a node holds. Describe lists a unit's
  types with it; `opUses`, `statementUses`, `statementBinders`, and `statementBodies`, which the passes call on every
  statement, are written out for speed and checked against it under `QUEST_CHECK_IR` (`traversalProblems`).
  `mapInOp` and `mapInStmt` replace a node's variables and atoms in place, descriptors and view maps included, and
  `clone` keeps its own cases, since it makes new nodes with their types substituted.
- The IR interpreter ([`../interpreter/irinterp`](../interpreter/irinterp.int.quest)) runs a unit at any stage
  (`--stop-after run_ir_described`, say). The tree-walking interpreter runs the typed AST without going through the
  IR at all, so comparing the two tests lowering and every pass against an independent oracle.

## Connections

Callers: [`../codegen/backend`](../codegen/backend.mod.quest) (lower, run the passes, print C or build SSA),
[`../driver`](../driver) (stage dumps, whole-program builds), [`../jit`](../jit) (each REPL input), and
[`../build`](../build) and [`../modules/artifacts`](../modules/artifacts) (separately compiled modules). Below it:
[`../types`](../types) for types and substitution, [`../repr`](../repr/README.md) for representation. The bootstrap
compiler's counterpart is [`bootstrap/python/quest/ir`](../../bootstrap/python/quest/ir/README.md): the same IR and
textual form, without the simplifier, unbox, or the thunks pass.

## Further reading

- [`docs/ir.md`](../../docs/ir.md): the IR's specification; §5–§6 nodes and control flow, §8 each pass, §9 the
  stages' invariants, §10 the textual form.
- [`docs/c-representation.md`](../../docs/c-representation.md): the runtime ABI the represent and describe passes
  target (§5 aggregates and proxies, §6.4 polymorphism and descriptors).
- [`docs/inlining.md`](../../docs/inlining.md): the simplifier's and inliner's settings and measurements.
- [`docs/ssa.md`](../../docs/ssa.md) and [`docs/codegen-c.md`](../../docs/codegen-c.md): what consumes the described IR.
- [`docs/compiler-organization.md`](../../docs/compiler-organization.md): where this directory sits among the layers.
