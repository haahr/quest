# Plan: Closing Part of the Gap to MLton

Five changes from [mlton-performance-review.md](mlton-performance-review.md) §4, items 1 to 5, decided on 2026-11-04.
Each removes work that MLton does not do on peek, wc-scanStream, ratio-regions, or zebra, and none depends on the
collector ([collector.md](collector.md)), whose bump allocation would make what they leave cheaper.

---

## 1. Decisions

- **The self-hosted compiler's alone.** These are optimizations, not fixes, so the bootstrap does not follow
  ([testing.md](testing.md) §2.8): the behavior goldens stay shared, and the IR and SSA goldens are the self-hosted
  compiler's own.
- **In the review's order,** with item 1 in two steps: inlining type applications (§2), inlining members that name
  their module's variables (§3), scalar replacement across block parameters (§4), specialization on a known function
  argument (§5), known calls of captured functions (§6), and the clears before a raise (§7).
- **Specialization per call site, bounded by the inliner's size,** not whole-program defunctionalization, and not
  a rewrite of the list library by hand.
- **peek is left as it is:** no extensible type, and options of `Int` stay boxed in a field.
- **No allocation in Boehm's internals.** The interim free-list pop the review considered is not done, since Boehm is
  to be replaced.
- **Each step measured alone** (§8), on the four and on the suite, before the next is begun.

## 2. Type Applications (`ir/simplify`)

A `type_app` whose instance is not a function (`maybe.none(:A)`, `lists.nil(:A)`) runs the function applied, as a
call of it without arguments would; specialize already treats it so ([ir.md](ir.md) §8.1). The simplifier considers
it for inlining as such a call: when the function the round knows has type parameters and no value parameters, and
the result's type is not a function's, the statement is treated as `call f [τ...]()` with the `type_app`'s callee,
module reference, member, and callee type, by the same rules (`inlining`) and expansion (`inline.expand`). A
`type_app` whose instance is a function (`lists.map(:Int :Int)` as a value) is left: it makes a closure.

*Done when* `language/inlined_calls` (or a new run test) shows `maybe.none(:Int)` and `lists.nil(:Int)` inlined in
its `ir_simplified` golden, and a switch on the constant they make folds.

## 3. Members That Name Their Module's Variables (`ir/inline`, `ir/simplify`)

A whole program inlines a call of a member from outside its module only when the member's function is closed
(`Analysis.closed`): `maybe.unwrap` names `error`, a variable of its module out of the caller's scope, and is never
inlined. Such a variable is in the caller's reach as the module's member, `member util/maybe.error`, an operation
the caller can bind. The analysis records, for each function, the variables it names and does not bind; a function
is **closed through members** when each of those is an immutable variable its module exports (`nodes.member` gives
the variable of each exported name). Its expansion at a call from outside the module binds each such variable first,
`let error.2 = member util/maybe.error`, and the copy uses that variable in its place (`clone.bindVar`). Inside the
module, where the variable is in scope, nothing changes.

*Done when* a run test's `ir_simplified` golden shows `maybe.unwrap(:Int o)` inlined into a main body, with the
member read before the raise and the raise's behavior unchanged (its output in the shared golden), and peek's and
zebra's `qf_unwrap` gone from their profiles.

## 4. Scalar Replacement Across Block Parameters (`ssa/escape`)

The review's §3.2 gives the shape: wc-scanStream's loop carries its `Stream` tuple as a block parameter bound to a
new allocation on every edge, and `input1`'s inlined returns join an option's allocation at a block parameter. Today
a parameter that is one of an allocation's pointers must be bound to that one value on every edge.

- **Which parameters.** A block parameter is *split* when every edge taken binds it to one of: a candidate
  allocation of one layout (the same size, each word stored at the same offset with the same type), another split
  parameter of that layout, or, for an option of a case without components, its constant. Its other uses are those
  that let an allocation be removed today (loads and stores at constant offsets, proxy tests).
- **The fixed point** is the existing one, with "bound to that one value" replaced by "bound to a splittable value on
  every edge": candidates and parameters are dropped together when either escapes.
- **The transformation.** A split parameter becomes one parameter per word of the layout; each edge passes the
  words it binds (an allocation's stored words, read where it was made, or the constant's tag and zeros), and each
  load of the parameter at an offset becomes the word's parameter. An allocation all of whose pointers are split
  parameters and loads is removed as one that does not escape is now (a slot, then promotion).
- **Identity.** An allocation whose identity is read (`peq`, a call, a hash) escapes, as now.

*Done when* `ssa_escape` shows a loop carrying a tuple and a join of two options split, and wc-scanStream's
allocations (allocations.py) drop to about the flattened variant's.

## 5. Specialization on a Known Function Argument (`ir/inline`, `ir/simplify`)

A recursive function is never inlined, so `lists.app(:XY)(fun(p: XY) ... ps)` allocates its closure on every call
and calls it indirectly on every element. A **static parameter** of a function `f` is a value parameter that every
call of `f` in its own body passes unchanged: the parameter itself, in its position, with `f`'s own type parameters
as type arguments. `f` qualifies when it is recursive through itself alone (its component has one member), names
itself only in such calls, and has a static parameter. At a call of `f` whose argument for a static parameter is a
function the round knows, and which the inliner's other rules allow (its size less its bonuses at most the
threshold, its type arguments closed, the growth bound), the call is **specialized**: replaced by

```
funs { fun loop(the other parameters) = f's body, with f's type parameters substituted, each static parameter
                                         replaced by its argument, and each call of f a call of loop on the others }
call loop(the other arguments)
```

The copy is a clone with fresh variables and labels (`clone`), as an expansion is. `loop` is then a local function
called once from outside, which contification makes a loop when its own calls are tail calls (`app`, `exists`,
`all`, `foldl`), and the known function's calls in it are known calls, which the inliner takes in the next round.
Where its calls are not tail calls (`map`, `foldr`), `loop` stays a local function, whose closure is made once per
call rather than the argument's being called through a closure on each element.

*Done when* `language/inlined_calls` (or a new run test) shows `lists.app` and `lists.exists` of a closure made into
loops with the closure's body in them, and ratio-regions' `preflowPush` allocates no closure per bucket.

## 6. Known Calls of Captured Functions (`ir/closure`, the C printer, the SSA builder)

The review's §3.4 is to be corrected: zebra's calls of `same`, `left`, and `adjacent` are already known in the
simplified IR (`call f.11(...)`), the inliner having inlined `make`. They are indirect in the code because
`isConsistent` is a local function that names them: closure conversion makes each a capture, read from the
environment at its start (`let same.1 = env_field(env, k)`), and the backends call a function directly only through
a variable bound to its closure (`closureVars` in the SSA builder, `p.closures` in the C printer).

A variable bound to `env_field(env, i)` in a lifted function `g` holds a closure of a known function `h` when every
closure made of `g` captures, at index `i`, a variable known to hold a closure of `h`. One analysis, shared by both
backends, finds these to a fixed point, starting from the lets of `closure h {...}` and their copies, and the calls
through them become direct calls of `h`'s code with the closure's environment, as calls through a let of the closure
are now.

*Done when* zebra's `qf_isConsistent` has no indirect calls (`blr`) of `same`'s functions, and a run test shows a
local function calling another it captures directly (its SSA golden).

## 7. Clears Before a Raise (arm64 `regalloc`, `select`)

In ratio-regions' `preflowPush`, each failed bounds check goes to a block that stores zero to 26 dead slots and then
jumps to the block that raises ([mlton-performance-review.md](mlton-performance-review.md) §3.8): the clears that
`5f74f6c4` removed from raising blocks, now on the edge before one. The block follows the check in the layout, so
every check that passes takes a branch over it.

- No clears on an edge into a block that only raises (or that leads only to one), as there are none in such a
  block.
- Such an edge's block laid out cold, with the raising block, so that a check that passes falls through.

*Done when* `preflowPush`'s bounds checks branch away on failure with no clears on the way, and the arm64 suite
passes.

## 8. Measurement

After each step, before the next:

- **The four** (peek, wc-scanStream, ratio-regions, zebra) through C and arm64, whole programs:
  `run.py time --clean --whole-program --scale 0.25 NAME...`, and their allocations (`allocations.py`).
- **The suite** at `--scale 0.25`, whole programs, through arm64, against the run before the step, to see what else
  it reaches and that nothing is slower.
- **The compiler's build time** (driver, through C), since §2, §3, and §5 inline more.

The results are recorded here as each step finishes, and at the end in [benchmarks.md](benchmarks.md).

## 9. Testing

- Each step's run tests (shared behavior goldens, written by the bootstrap) and the self-hosted goldens they change
  (`ir_simplified`, `ssa`), regenerated with `--self-hosted --update-golden` and read.
- `ssa_escape` for §4; the arm64 suite for §7.
- `tools/check` before each step's commit.

## 10. Steps

1. This plan, and the review's §3.4 corrected.
2. Type applications (§2).
3. Members that name their module's variables (§3).
4. Scalar replacement across block parameters (§4).
5. Specialization on a known function argument (§5).
6. Known calls of captured functions (§6).
7. Clears before a raise (§7).
8. The measurements recorded in benchmarks.md, and this plan retired into ir.md, ssa.md, and arm64.md.
