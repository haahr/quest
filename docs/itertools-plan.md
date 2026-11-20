# Plan: More Iterators, `util/iterTools`

A module after Python's `itertools`: the sources without end, the stages that group, window, or interleave, the
combinatoric iterators, and a few consumers that `util/iter` ([iter-plan.md](iter-plan.md)) leaves out. Interface and
implementation are written (`lib/util/itertools.int.quest`, `lib/util/itertools.mod.quest`) with a run test,
`tests/source/stdlib/itertools_operations.quest`, whose output was checked against Python 3.11's `itertools` for
the same arguments (`batched`, which is 3.12's, by hand). §6 has its status.

## 1. Decisions

1. **A module of its own, not more of `util/iter`.** `util/iter` has the stages most programs use (`map`,
   `filter`, `take`, `zip`, `concat`, `flatMap`, ...) and every collection's iterator depends on it; this module
   has the ones reached for less often, and its own dependencies (`collections/vector`, `deque`, `hashSet`), which
   `util/iter` must not have, since those collections import it. The name is `util/iterTools`, the file
   `itertools`, as `util/stringBuilder`'s is `stringbuilder`.
2. **Built on `util/iter`'s public API alone.** `iter.T` is abstract outside `util/iter`, so every stage is
   `iter.make(ready pull)` over `iter.more` and `iter.next`: its state is a tuple of `var`s the two closures share.
   Where `pull` hands out the source's next element as it is, it calls the source's `next` and lets its
   `iter.exhausted` propagate rather than testing `more` first; the stages that choose what to hand out (`stepBy`,
   `windows`, `pairwise`, `intersperse`, `interleave`, `zipLongest`) test `more` or call their own `ready` first and
   raise `iter.exhausted` themselves. Under a whole program the closures fold into the loop that walks them only once
   [abstract-inlining-plan.md](abstract-inlining-plan.md) lands; until then each stage costs what any `util/iter`
   stage does.
3. **Lookahead through `iter.peekable`.** A stage that must see the element after a run to know the run has ended
   (`groupBy`, `uniqueRuns`) reads it through `iter.peekable` and `iter.asIter`, rather than keeping a slot of its
   own. `accumulate` and `pairwise` hold the element before in a `Held` option (`made with var
   x`) whose payload is overwritten through the case binder, as `util/iter`'s slot is, so nothing is allocated per
   element.
4. **One-shot iterators; `cycle` keeps a copy, `cycleFrom` asks again.** As in `util/iter`, an iterator is consumed
   once. `cycle(it)` keeps the elements as it first hands them out and replays them, as Python's does;
   `cycleFrom(source)` takes `All() iter.T(A)` and calls it for each pass, keeping nothing, for a source that is
   cheap to walk again (an array, a range). Chosen by the user, 2026-11-20.
5. **Every array handed out is fresh.** `batched`, `windows`, `groupBy`'s `values`, and the combinatoric iterators
   make a new array for each element, which the caller may keep or change (the test changes one and checks the next
   is unharmed). Python's tuples are immutable, so it may share; Quest's arrays are not.
6. **Errors raise `iterTools.error`.** For a `step` or `size` below 1, a `lo` below 0 (`slice`), an `r` below 0, and
   an `n` below 0 (`tee`, `nth`), raised when the stage is made, not when it is first pulled. An `r` past the
   array's length is not an error: it gives no elements, as Python's does.
7. **The combinatoric iterators take arrays**, since they index their pool repeatedly, and use Python's algorithms
   (`idx`, `cycles`, and a `done` flag), so the order is Python's: by the positions chosen, earlier ones changing
   slowest. `product` of two arrays gives `iter.Pair`s; `productOf` of any number gives arrays, and `power(a r)` is
   `productOf` of `r` copies of `a` (Python's `product(a, repeat=r)`).
8. **`groupBy` hands out whole groups.** Python's `groupby` yields a key and a sub-iterator that shares the source,
   valid only until the next group is pulled; here each `Group(K A)` is a record of the key and an array of the run,
   so groups may be kept. `key` is called once per element (the stage maps each element to a pair of its key and
   itself first); the test counts the calls.

## 2. The interface

| Kind | Operations |
|---|---|
| Sources | `count(start step)`, `repeat(a)`, `repeatN(a n)`, `cycle(it)`, `cycleFrom(source)`, `iterate(a f)` |
| Stages | `accumulate(it f)`, `scan(it init f)`, `flatten(its)`, `reject(it p)`, `compress(it selectors)`, `stepBy(it step)`, `slice(it lo hi step)`, `pairwise(it)`, `windows(it size)`, `batched(it size)`, `groupBy(it key eq)`, `uniqueRuns(it eq)`, `unique(it equal hash)`, `intersperse(it sep)`, `interleave(its)`, `zipLongest(a b fillA fillB)`, `tee(it n)` |
| Combinatoric | `product(a b)`, `productOf(pools)`, `power(a r)`, `permutations(a r)`, `combinations(a r)`, `combinationsWithReplacement(a r)` |
| Consumers | `nth(it n)`, `allEqual(it eq)`, `partition(it p)` |

Python's names are kept where they say what Quest's conventions would (`accumulate`, `pairwise`, `batched`,
`compress`, `permutations`, ...), and changed where Quest's are already set: `islice` is `slice`, `groupby` is
`groupBy`, `filterfalse` is `reject`, `zip_longest` is `zipLongest`, `chain.from_iterable` is `flatten`, and the
recipes' `roundrobin`, `unique_justseen`, `unique_everseen`, `all_equal`, and `sliding_window` are `interleave`,
`uniqueRuns`, `unique`, `allEqual`, and `windows`. `scan` is `accumulate` with an initial value of another type,
which Python spells `accumulate(it, f, initial=x)`; `stepBy` is `slice` without bounds. `iterate` (Haskell's) and
`intersperse` come from other languages' libraries.

How each is built:

- Over `util/iter` directly: `flatten` (`flatMap` of the identity), `reject` (`filter` of `not`), `compress`
  (`filterMap` over `zip`), `slice` (`stepBy` of `take` of `drop`), `unique` (`filter` with `hashSet.insert`),
  `nth` (`first` of `drop`), `allEqual` and `partition` (loops).
- With a `deque`: `windows` (the window slides, and each element hands out a copy) and `tee` (a queue per branch of
  what the other branches pulled and this one has not reached).
- With a `vector`: `batched` and `groupBy` collect a run, then hand out `vector.toArray`; `cycle` keeps its
  first pass.

## 3. Left out

- **`chain`**: `iter.concat`. **`starmap`**: Quest functions take their arguments, not a tuple of them; `iter.map`
  with a function that takes the pair's fields does it. **`zip`, `takewhile`, `dropwhile`, `filter`, `map`**:
  `util/iter` has them.
- **Python's shared `groupby` sub-iterators** (§1 decision 8).
- **`tee`'s sharing with the source**: once `tee` is called, the source must not be pulled except through its
  branches (the interface says so). Python has the same rule.
- **More recipes** (`powerset`, `partition` into iterators, `nth_combination`, `random_*`): each is a few lines over
  these; add them when a program wants one.

## 4. Cost

Each stage is one `iter.make`: two closures and a state tuple when it is made, and per element the calls through
the source's closures plus its own. Under separate compilation that is about 23 instructions per element per stage
(iter-plan.md §2); the combinatoric iterators allocate their fresh array per element as well. Under a whole program
it is the same until [abstract-inlining-plan.md](abstract-inlining-plan.md) lands, after which `map`-like stages
fold into the consumer's loop. Nothing here was measured; no benchmark uses it.

## 5. Tests and goldens

`tests/source/stdlib/itertools_operations.quest` exercises every operation with Python's results, the edge cases
(empty inputs, `r` of 0 and past the length, sizes that do not divide), `more` repeated and `next` past the end,
each error, the combinatoric counts against their formulas (5³, 5!/2!, C(5,3), C(7,3)), the arrays' freshness,
and the number of calls `iterate` and `groupBy` make to their functions. The shared goldens (`tokenize`, `parse`,
`typecheck`, `run`) are the bootstrap's, and the self-hosted compiler prints the same `run` output; its own
`ir_core` and `ssa` goldens are its own.

## 6. Status

Committed, pushed and released 2026-11-20, with the user's change to `cycle` (§1 decision 4) and libraries.md §1.15.
