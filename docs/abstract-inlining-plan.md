# Plan: Folding Through a Module's Abstract Type

Under `--whole-program`, an iterator's pipeline does not fold into the loop that walks it, because its tuple
reaches the loop through copies that change its type, and the simplifier's tuple projection fold does not follow
them. This plan makes it follow them. It replaces the tasklist entry "A whole program does not inline through a
module's abstract type". Complete 2026-11-20: steps 1–3 (§4) done, and `map` measured at 11.1 instructions per
element in a whole program (`benchmarks/iter/README.md`).

## 1. The problem

A module that exports an abstract type implements it as a manifest one: inside `util/iter`, `T(A)` is
`Tuple more: All() Bool next: All() A end`. In a whole program every module is one unit, so `iter.more(it)` and
`iter.map` are inlined into the program, and the tuple an iterator is made of is in sight. But the value passes
through two copies on the way, which copy propagation leaves since it propagates only between variables of equal
types ([ir.md](ir.md) §8.6):

```
let %24: Tuple more: Fun(): Bool next: Fun(): Int end = tuple(more.3, next.3)
let %25: iter.T(Int) = %24        (the program's view: the abstract type)
let it.3: T(Int) = %25            (the module's view, inlined: T manifest)
let %26: Fun(): Bool = tuple_field(it.3, 0)
```

`simpler`'s `opTupleField` case (`questlang/ir/simplify.mod.quest`) folds a projection only when the tuple's own
`let` is `opMakeTuple`; here it is `opAtom`, a copy. So the closures stay closures, called through the tuple once
per element: `benchmarks/iter/`'s `map` takes 56 instructions per element in a whole program, where the same library
with `T` visible (`Def` in the interface, so no copy changes the type) takes 11.

The options' folds already follow such copies: `madeOf` walks `opAtom` copies of immutable variables to an
`opMakeOption` or `opMakeVariant`, for `maybe.T(Int)` of `T(Int)` (its comment). Tuples were left out.

## 2. The fix, and the prototype

A `tupleSource(s a)` beside `madeOf`: from an atom, through `opAtom` copies of immutable variables, to the atom bound
to an `opMakeTuple`, or none. `opTupleField` folds `tuple_field(x, i)` to the made tuple's `i`th argument when:

- the component is not `var` in the projection's type, `x`'s (as today);
- nor in the made tuple's own type, the source atom's: a copy may change the type, so both are checked (the source's
  is the one that says what was allocated; an abstract type's shape is unknown, so `varComponent` refuses it, which
  is right: nothing folds at a type whose components are not known);
- the argument is `stable` (a constant or an immutable variable), as today.

A mutable variable anywhere in the chain stops it (`tupleSource` returns none), since a later read might find it
reassigned. The fold replaces only the projection: the tuple itself is left to dead-code removal, so whether
anything reads its identity does not matter.

The prototype, 25 lines in `simplify.mod.quest`, measured with `benchmarks/iter/run.py` (20,000,000 elements,
instructions retired per element):

| Workload | Separate | Whole, before | Whole, prototype | Loop written out |
|---|---:|---:|---:|---:|
| `map` | 82 | 56 | 11 | 17 |
| `filter` | 151 | 116 | 45 | 17 |
| `sumInt` | 140 | 116 | 45 | 17 |

After it, `map`'s whole program is the visible type's 11: `more` and `next` are inlined into the loop, and the
range's and the map's closures with them. Separate compilation is unchanged, since nothing is inlined across modules
there. `filter`'s remaining 45 is its lookahead slot (`util/iter`'s `Look`: an option's payload overwritten through a
case binder, and a `full` flag), not the tuple; §5 has it.

## 3. What else it reaches

Any whole program with a module whose abstract type is a tuple of closures or of known values: the collections'
iterators (`vector.iter`, `hashMap.entryIter`, the B-tree's cursor), `regexp.findIter`, and `util/iterTools`
([iter.md](iter.md) §4), whose stages are all `iter.make` of two closures. The compiler itself is built separately,
so its own build does not change.

It also reaches copies that change the type by subtyping, not only by abstraction: a `BigTuple` passed as a
`SmallTuple`, or a tuple whose component is seen through a record view. Tuple subtyping is by prefix, so the
component's index is the same in both types, and `represent` puts the view's coercion on the folded value as it would
on the projection. With the prototype, `run_ir_simplified` passes all 350 programs, and the self-hosted goldens
that change are five language tests, all for this reason: `record_views`, `subtyping_coercions` and
`type_parameters_in_aggregates` from `ir_specialized` or `ir_represented` on, and `proxy_components` and
`view_proxies` in `ssa` only. In each, a projection of a tuple made in sight now folds to its argument
(`subtyping_coercions` prints `conv.int(30)`, its sum folded). Step 1's test covers a view as well as an
abstract type.

The bootstrap has no simplifier (`bootstrap/python/quest/ir` has no such pass), so the change is the self-hosted
compiler's alone: its own IR and SSA goldens may change, and the shared goldens, which say what programs do, must
not ([testing.md](testing.md)).

## 4. Steps

1. **The fold.** `tupleSource` and the `opTupleField` case as §2 has them, with ir.md §8.6's list saying projections
   are folded through copies of another type, as options' tests are. A run test in `tests/source/modules/` with a
   module of its own whose abstract type is a tuple with a `var` component and an immutable one, read and assigned
   through the program, and a tuple whose component is seen through a record view (a prefix supertype): it must
   print the same in every backend, the whole-program ones (`c-whole`, `arm64-whole`)
   included, which is what would catch a fold of the `var` one.
2. **The goldens.** Review the self-hosted `ir_*` and `ssa` goldens' changes (each a projection folded, and what that
   lets the inliner and dead-code removal do), and update them.
3. **The measurement.** `benchmarks/iter/run.py`, with the table in its README replaced, and a line in
   [benchmarks.md](benchmarks.md) if the topline set moves (its programs are whole programs only when built so).
   Done when `map` is about 11 instructions per element in a whole program.

## 5. Left for later

- **`filter`'s 45.** A lookahead stage pays for its slot: the option's tag test, the case binder's store, and the
  `full` flag. Assigning through `opt!tag` now changes the option (`107b5186`), which may let the slot be written
  more simply; whether it gets cheaper is not yet measured.
- **Records.** The simplifier folds no record field reads, through copies or not. No library's abstract type is a
  record of closures today, so nothing is measured to gain.
- **Separate compilation** still pays about 23 instructions per element the consumer pulls ([iter.md](iter.md) §2);
  only cross-module inlining would remove that, which separate compilation does not do by design.
