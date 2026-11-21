# Adapter Closures Made Once

A plan for the task-list entry "A function value converted to a supertype allocates its adapter's closure every
time": the adapt plans' closures, `QAdaptClosure { fn, orig }` ([c-representation.md](c-representation.md) §6.3), are
4.6 percent of the compiler's allocations, and most of them convert a value that never changes. Three changes to the
thunk pass (`questlang/ir/thunks`, [ir.md](ir.md) §8.4.1) make them static, made once, or not made at all.

---

## 1. Where They Come From

An adapt plan converts a closure to a function type whose C signature differs, most often a concrete function passed
to a generic one, whose parameters are `QVal` words: `hashMap.new(intEqual hash.int)` passes two `All(a: Int b: Int)
Bool`-shaped functions where `hashMap.new` takes `All(a: K b: K) Bool`. A conversion of a *known* function (a variable
bound to a closure without captures or type arguments) is already the static closure of an adapter of its own, which
calls the function directly; any other conversion allocates a two-word closure holding the original.

Counted 2026-11-20 at `ca2cdad7` with a temporary filter in the runtime's `allocations` mode, noting only
allocations of layout `QAdaptClosure`, each attributed to its allocating function and source line (`atos`):

**The compiler's build** (stage 2 compiling `questlang/driver/main.quest`): 48.9 million adapter closures of
1,057 million allocations, nearly all of two kinds (a third appears in the benchmarks):

| Kind | Adapters | Share | Example |
|---|--:|--:|---|
| An imported module's function | 43.6 million | 89% | `hashMap.new(intEqual hash.int)` (`types/model:1641`) |
| A closure made and passed at once | 5.3 million | 11% | `hashMap.forEach(m fun(b p) ...)` (`types/canonical:1134`) |
| Other | under 0.1 million | | |

The first kind's other large sites are `sort.bisectRight(a.starts[v] p sort.intCompare)` (`machine/regalloc:68`, `:86`)
and `hashMap.new(stringOp.equal hash.string)` (`types/symbols:145`); the second's, the compiler's other
`hashMap.forEach` callbacks (`types/canonical:955`, `:1142`).

`intEqual`, the module's own function, is already known and its adapter static; `hash.int` beside it, an imported
member, is not: every `hashMap.new` of an `Int` key in the compiler allocates one adapter, every `sort` of integers
another.

**The MLton benchmarks** (`--scale 0.05`): adapter closures are 6.8 percent of simple's allocations (13.7 million,
`lists.map(:Int :Real)(fun(i: Int): Real ...)`, the second kind), 0.5 percent of model-elimination's (6.7 million,
`mapPartial(...)(matchConv l)`, where `matchConv = literalsConv("match_literals")` is a global bound to a closure the
program computes: a third kind, an immutable global that is not a known function), and under 0.6 percent of any other.

## 2. The Design

### 2.1. An imported member's adapter is static

A conversion of an imported module's member, `opModuleMember` of an import (`r.member`), is the static closure of an
adapter of its own, as a known function's is: the adapter takes the target's parameters, converts them by the plan's
fields, calls the member, and converts its result. The member is read inside the adapter, where lowering binds it as
it binds any member it calls, so each backend calls it as it calls an imported member (through the module's exported
function, `qv_<module>_<member>`, for a function the interface declares, [c-representation.md](c-representation.md)
§6.2): one direct call where the adapter called through `orig`. An interface's member never changes once its module
is initialized, and its importer's code runs only after, so reading it at each call reads the value the conversion
would have held.

- **In `thunks`:** `knownOf` also records a variable bound by `opModuleMember` of an import (not the unit's own
  module, whose members are its globals), and `adapter` takes, besides a known function, a module member to call.
  Adapters stay one per key: the member's module and name with the plan's types and layout.
- **Every backend** gets it, the pass being shared: the C printer, the SSA's (arm64, ssac, the JIT), and wasm, whose
  static closures are globals ([wasm.md](wasm.md) §3.1). The bootstrap's C printer makes its adapters itself and is
  left as it is: it is not what programs and the compiler are built with.

### 2.2. A conversion of an immutable global is made once

A conversion of a global that is bound once and never assigned (the top level's `let`, not `let var`), and is not a
known function, is made once, where the global is bound: the unit's initialization converts it after binding it, into
a global of its own, and each conversion reads that global. model-elimination's `matchConv` is converted once instead
of 2.6 million times.

- **In `thunks`:** a first walk of the unit's initialization finds the immutable globals bound to values of function
  type; a conversion of one, by an adapt plan, anywhere in the unit, becomes a read of the global holding its
  conversion by that plan, made right after the global's `let` (the plan's descriptors are static there: a global's
  type mentions no type parameter of a function).
- **Ordering:** a function that runs during initialization before the global's `let` reads the conversion's global
  unbound, as it would read the global itself unbound: no new case.

### 2.3. A closure made to be converted is made at the converted type

A closure of a lifted function `f` that is converted once and used nowhere else (simple's lambdas, the compiler's
`hashMap.forEach` callbacks) is made instead as a closure of `g`, a copy of `f` (`ir/clone`) whose parameters and
result are the target type's: `g` converts its parameters by the plan's fields to `f`'s types, runs `f`'s body, and
converts its result. `g` has `f`'s captures in `f`'s order, so its closure holds what `f`'s would have; `f`, unused,
is dropped. One allocation, the closure, where there were two, and one call fewer when it runs.

- **In `thunks`:** in a block, a `let` of `closure f {captures}` whose variable's only use is a later `opConvert` by an
  adapt plan in the same block, and `f` made into no other closure, is rewritten: the conversion becomes
  `closure g {captures}`, and the `let` goes.
- **Copies:** `g` is a new function, so a lambda converted at two types (two plans) is two copies; one converted once,
  the case counted, is one, `f` being dropped.

### 2.4. A conversion that repeats inside a loop is made before it

What §2.1–2.3 leave is conversions of closures that arrive at run time: a function's parameter, or a closure read
from a data structure. When one site converts the same closure again and again, the usual cause is a loop converting
a value defined outside it, which converting once, before the loop, removes without a table. This is the last stage,
taken only if the counts after §2.1–2.3 show it pays.

- **First, measure:** the same temporary filter, its sites keyed by the call site and the original closure's address,
  counts how often a site converts a closure it converted before. Sites converting distinct closures each time (a
  closure per element of a list) gain nothing from hoisting or caching.
- **The hoisting:** in `thunks`, an `opConvert` by an adapt plan inside a loop (`sLoop`, `sWhile`, a `for`'s body, as
  the IR has them), of an atom bound outside the loop, whose plan's descriptors are bound outside it too, is moved to
  just before the loop into a variable of its own, and the conversion becomes a read of that variable. A conversion
  in a branch the loop may not take is hoisted too: converting a closure has no effect but allocating, so making it
  once early is safe.
- **A cache was considered and not taken:** a table from (closure, type) to its adapter costs a lookup at each
  conversion, more than the two-word allocation it saves, keeps every closure it has seen alive unless its entries
  are weak (the collector has no weak references), and makes every repeated conversion identical under `is`. A
  one-entry cache per site (the last original and its adapter in static data, a pointer comparison) is the cheap form,
  kept in reserve should the counts show a site repeating a closure that hoisting cannot reach (a recursion converting
  its own parameter, say).

### 2.5. What does not change

- **Identity:** `is` on functions compares closures (c-representation.md §6.1). Converting the same imported member
  or the same global twice now gives the same closure, where it gave two. Whether the interpreters agree (what their
  conversions of a function give under `is`) is checked first, and the tests that compare converted functions
  (`language/function_subtyping`, the identity tests) with them; a disagreement is resolved toward what the
  interpreters do, or recorded in extensions.md, before the step lands.
- **The runtime's adapters** (`quest_adapt_<tag>`, `QFunAdapterClosure`), made by `quest_convert` for `dynamic.be`
  and fields read at a subtype, are not counted here and stay.

## 3. Steps

Each step its tests, the compiler's fixed point (`run_tests.py --self-hosting --fixed-point-only`, through arm64 and
C), the counts of §1 again, and a commit; `tools/check` once at the end, then the push.

1. **Imported members' adapters static** (§2.1): the compiler's build should lose about 43.6 million allocations
   (4.1 percent). **Done:** 48.6 to 5.2 million adapter closures, the build 1,055.8 to 1,012.2 million allocations,
   stage 2 rebuilt from an empty `.build/quest-stages` (a stage 2 whose unchanged units were cached from the compiler
   before counted none fewer). Its test, `language/imported_adapters`, converts library functions at generic types
   (comparators, hashes, equality) in a loop and in a function called often, on every backend.
2. **Lambdas made at the converted type** (§2.3): simple's 13.7 million and the compiler's 5.3 million. A test of a
   lambda converted once, at a type parameter and at a supertype of a record, with captures of each kind.
3. **Globals' conversions made once** (§2.2): model-elimination's 6.7 million. A test of a global closure converted in
   a loop, and one converted inside a function called before the global is bound.
4. **Repeated conversions** (§2.4): the counts by site and original closure; if a site converts one closure many
   times, the loop hoisting, with a test of a conversion in a loop and in a branch of one; if none does, the counts
   are recorded and the stage ends there.
5. **The measurement:** the MLton benchmarks' times at `--scale 0.25` and the compiler's build, before and after, in
   benchmarks.md as a section of its own; the plan then retires into ir.md §8.4.1 and that section.

## 4. Done When

The adapter closures of §1 are gone from the compiler's build and from simple and model-elimination, or each kind
that is kept is recorded with why, the suites pass, and the times are recorded.
