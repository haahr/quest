# Plan: Inlining and Its Companions

An optimizer for the self-hosted compiler's IR: inlining, with the simplifications that make it pay, contification,
and reduced entry points for functions whose calls are all known; and calls of other modules' exported functions
without their closures. It starts after [backend-improvements.md](backend-improvements.md) is complete.

The cost it removes is measured in [benchmarks.md](benchmarks.md) §3.3: nothing is inlined that is not a runtime
primitive, higher-order code (imp-for's `forLoop`) calls closures where MLton runs straight loops, polymorphic calls
convert between native and generic layouts, and an exported function is called through its closure in a global.

---

## 1. Decisions

- **Inlining is on the Core IR,** before specialize and closure conversion (§2), as part of a simplifier that
  runs with it to a bound.
- **It is always on.** No option enables or disables it, in keeping with as few compiler options as possible; tests
  and bisection leave passes out through the pipeline's own mechanism ([backend-improvements.md](backend-improvements.md)
  §3.3), not a flag.
- **Across modules only in whole-program builds** (`--whole-program`, [build-process.md](build-process.md) §1.2),
  where every module is in one unit. Separate compilation gets no unfoldings: nothing is added to `.qi` files or
  manifests, so an importer still depends on interfaces alone and builds keep their parallelism.
- **Exported functions are called directly** through `qv_<mod>_<fn>` from other units, not through their closures
  (§6), in every build.
- **Heuristics are deterministic:** sizes, counts, and source order, never a hash table's iteration order, so that
  the self-hosting check's fixed point holds.
- **Removing polymorphism earns the largest bonus** (§3): a call at closed type arguments whose inlining lets
  represent and describe see no polymorphic call at all.
- **The self-hosted compiler's alone,** as its backends are ([testing.md](testing.md) §2.8): the bootstrap does not
  inline; behavior goldens stay shared, and each compiler's IR goldens are its own.
- **Tracebacks lose inlined frames,** as they lose frames clang removes now ([exceptions.md](exceptions.md) §2.4).
- **No `inline` or `noinline` annotations** in the language unless measurements show the heuristics cannot do
  without them.

## 2. Where in the Pipeline

```
lower → Core IR → simplify (inline, simplify, contify; to a bound) → specialize → closure-convert
      → workers (§5) → represent → describe → backends
```

| Where | What it sees | Verdict |
|---|---|---|
| Core IR, before specialize | `funs` as functions with free variables; types and type arguments explicit; no representations or conversions | **The inliner** |
| After closure-convert | environments allocated, captures read through `env_field` | Too late for closures: undoing one is harder than not making it |
| After represent or describe | `convert` plans, descriptor operands, thunks | Must preserve every conversion; polymorphic boxing already made |
| SSA | machine scalars | Leaf code only: runtime helpers expanded inline (arm64.md §6); clang already inlines within a C unit |

The Core IR is where inlining removes the costs that later passes would build:

- **Higher-order code.** Inlining `forLoop(1 n fun(i) ...)` makes its parameter a known local function, whose call can
  be inlined in turn; after closure conversion the same code is an allocated closure and an indirect call.
- **Polymorphism.** A polymorphic function inlined at closed type arguments has them substituted, so represent never
  sees the call and makes no conversions between native and generic layouts, and descriptors known statically fold
  away in describe.
- **Machinery that exists.** Specialize ([ir.md](ir.md) §8.1) clones a function with fresh binders and substitutes
  type arguments; an inlined body is that clone with its parameters bound to the call's arguments.
- **Returns and exceptions.** A `return` in the inlined body becomes a jump to a join point ([ir.md](ir.md) §6.3)
  bound around the inlined code; a `try` stays a structured region.
- **`var` and `out` parameters.** The inlined body uses the caller's variables, so their addresses are no longer
  taken, which the SSA's promotion then gains from.

## 3. Heuristics

**Size** is counted in IR operations and statements, a call weighing more than an atom's copy, measured on each
callee after inlining into it: functions are taken bottom-up over the call graph's strongly connected components.

**Always inlined:**

- a function called once that does not escape and is not exported;
- a function whose body is no larger than its call (its arguments, plus one).

**Inlined when its size less its bonuses is under a threshold,** about 30 to start, tuned on the benchmarks. The
bonuses, for what inlining at this call would remove:

- **Polymorphism removed (the largest):** the call supplies closed type arguments, so that after inlining the
  caller holds no polymorphic call of this function: no generic layouts, no conversions to and from them, no
  descriptors passed or instantiated. More when the callee uses descriptors (records' offset tables, `inspect`,
  `Dynamic`, `is` of `QVal` words, `quest_convert`), or has tuple, option, or record parameters or results over its
  type parameters.
- **A function argument the callee calls,** which makes the call known, to be inlined or contified in turn.
- **A constant the callee branches or switches on,** or an option or variant made at the call that the callee cases
  on.
- **A `var` or `out` argument,** whose address inlining no longer takes.

**Never:**

- a function into its own strongly connected component;
- past a depth of 16, as specialize bounds its clones;
- past a growth bound: a caller to twice its size, the unit to one and a half times.

## 4. The Simplifier and Contification

Inlining alone gains little; with it, to a bound on rounds and growth:

- **copy propagation** of atoms;
- **dead `let`s,** closures and allocations nothing reads included;
- **constant folding,** and `if` and `switch` on constants;
- **case of a known constructor:** a `switch` on an option or variant made in the same function, and `!` of one;
- **projections of a tuple made in the same function,** when the tuple has no `var` components and nothing reads its
  identity.

**Contification** (MLton's term): a local function called only in tail position, from one continuation, becomes a
join point, or a loop when it calls itself, rather than a closure. With inlining, it is what turns imp-for and
tailfib into loops.

## 5. Workers: Reduced Entry Points

Every function keeps its uniform entry (its environment, then its descriptors, then its parameters at their
generic layouts), which closures, exported functions, the function table, tracebacks, and indirect calls need.

**A worker** is a function's body at a reduced signature, decided by analysis after closure conversion (when every
function is lifted and escape is easy to see) and before represent (which then chooses its parameters'
representations). The original becomes a wrapper that converts and calls the worker; known calls (a variable bound
to a closure of the unit's function, and what inlining leaves) call the worker. A worker:

- **drops what it does not use or what is the same at every call:** an environment it never reads, descriptors
  unused or static at every call;
- **takes a tuple parameter's components,** when the callee only reads them: it does not store, return, capture,
  or `is`-compare the tuple, and the tuple has no `var` components;
- **returns a tuple's components as results,** when every return makes a fresh tuple and every caller only reads
  its components, which saves an allocation each call;
- **takes a `var` or `out` parameter as a value in and a value out,** when nothing captures it.

**A function that does not escape and is not exported** has only known calls, so its signature is rewritten in
place, with no wrapper.

**Not a second convention by type.** Quest's tuples have identity (`is` compares addresses), so flattening and
multiple results are decided from the body, not the type; what a type alone fixes is already done (`qv_` functions
have no environment) or is the machine level's (arm64.md §6's calling convention of Quest's own).

## 6. Exported Functions Called Directly

A call from another unit of an imported module's exported function calls `qv_<mod>_<fn>` directly, with no load of
the module record's closure and no indirect call. The C backend and the SSA's builder both do; the module's
initialization guarantees the function's globals are set before any call, as now. This is the rest of
benchmarks.md §3.3, independent of the inliner, and the first step.

## 7. Testing

- **The IR's stages** get dump names (`simplify`, `contify`, `workers`), each with goldens of its own, the
  self-hosted compiler's.
- **Behavior:** every golden passes with the optimizer, compiled through each backend, checked against the
  interpreter as now; and per-pass tests of the simplifier and inliner on small IR, as backend-improvements.md §3.4
  makes possible for the SSA.
- **Determinism:** the self-hosting check's fixed point, with the optimizer running on the compiler itself.
- **Measurements** in benchmarks.md, dated, before and after each step: imp-for, tailfib, md5, checksum, the
  benchmarks whose polymorphic calls dominate, and the compiler's own build time.

## 8. Steps

1. **Exported functions called directly** (§6). *Done when* no unit calls another's exported function through its
   closure, and benchmarks.md records the change.
2. **The simplifier** (§4, without contification), with its dump and goldens. *Done when* it runs on every unit and
   the suite passes.
3. **Inlining of functions called once,** then of small ones and those §3's bonuses favor, polymorphism's first,
   through specialize's cloning. *Done when* imp-for's `forLoop` is inlined and its argument's call with it, and a
   polymorphic call at closed type arguments that §3 inlines leaves no conversion or descriptor in its caller.
4. **Contification** (§4). *Done when* imp-for's and tailfib's loops are loops in the IR.
5. **Workers** (§5), and signatures rewritten in place for functions that do not escape. *Done when* a function
   returning a fresh tuple to callers that only read it allocates no tuple.
6. **Whole-program builds** inline across modules. *Done when* `--whole-program` builds inline the library's small
   functions into their callers, and benchmarks.md compares them with separate compilation.
7. **Tuning:** the threshold, bonuses, and growth bounds set from the measurements. *Done when* benchmarks.md
   records the settings and why.
