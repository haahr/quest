# Plan: Iteration, `util/iter`

One iteration library, `util/iter : util/Iter`, so that a program walks a vector, a hash set, a sorted map's range, a
string's characters, or a regular expression's matches with the same code, and chains `map`, `filter`, `take` over
any of them without building vectors in between ([future-libraries.md](future-libraries.md), "Lazy sequences"). It
needs no change to the language: an iterator is a pair of closures, behind an abstract type.

A design, 2026-11-19; nothing is built. §1 is the decisions, §2 the measurements behind them, §3 the interface,
§4 what each collection adds, §5 what is left out, §6 the steps, and §7 what the user settled.

## 1. Decisions

1. **Pull is the paradigm.** The calling code is an ordinary loop, which can `break`, return from the middle, and
   walk two iterators in step:

   ```
   let it = vector.iter(v)
   while iter.more(it) do
       let x = iter.next(it)
       ...
   end
   ```

   Push (a function that calls its argument with each element) was the cheapest shape measured, but it makes the
   caller write the loop's body as a closure, stop it by returning `false`, and give up walking two in step (`zip`,
   merging sorted iterators, comparing two) unless one side pulls anyway. Pull costs 1.1 to 1.9 times push's
   instructions per element, with no allocation per element in either (§2). Pull is also the more general: an
   iterator becomes a push walk in three lines (`forEach`), and the reverse needs coroutines.
2. **An abstract `iter.T`, with functions, as every Quest library has.** An iterator is an `iter.T(A)`, read with
   `iter.more(it)` and `iter.next(it)` (type arguments inferred from the iterator), as a vector is a `vector.T(A)`
   read with `vector.get(v i)`. Inside `util/iter` it is a pair of closures:

   ```
   Let T = Fun(A::TYPE) Tuple more: All() Bool next: All() A end
   ```

   and a producer outside makes one with `iter.make(more next)`, a call per iterator, not per element.

   The alternative was the tuple visible, read as `it.more()` and `it.next()`. That is the only method-like API it
   would be in `lib/`, and it fixes the representation for good: `iter.T` can later grow a change counter, a size
   hint, or a `close` for an iterator over a file, or take another shape if one becomes cheaper, without changing
   a caller, and the importers' interfaces do not record it. The price is a call into `util/iter` for each `more`
   and `next` at the consumer, since separate compilation inlines nothing across modules: about 23 instructions per
   element the consumer takes (53 to 76 per element through a `map`, 130 to 142 through a `map` and a `filter`).
   Under `--whole-program`, which inlines across modules, the price is gone: both forms compile to the same code,
   11 instructions per element through a `map` (§2). Stages inside `util/iter` read the closures directly and do
   not pay it.
3. **`more` and `next`, for familiarity.** `more` says whether there is another element and changes nothing a caller
   can see: calling it twice is calling it once. `next` returns the element and moves past it; called when `more`
   would say `false`, it raises `iter.exhausted`. This is Java's `Iterator` (`hasNext`, `next`), which most
   programmers know, and `next` gives each element once, so a `map`'s function runs once per element whatever the
   caller does. A producer's closures keep this contract; `make` does not check them.

   `advance`/`current` (C#'s `MoveNext`/`Current`) was measured as the alternative and is cheaper through stages
   that look ahead (114 instructions per element through `filter` against 130, §2), since with it nothing is held.
   With `more`/`next`, a stage that has to find out whether there is another element (`filter`, `takeWhile`,
   `dropWhile`, `flatMap`, `peekable`) pulls it from its source in `more` and holds it until `next`. Familiarity, a
   `next` that cannot be read before its iterator starts, and `map`'s once-per-element call outweigh the
   difference, which is confined to those stages.
4. **A lookahead stage holds its element in an option it reuses.** A generic `A` has no empty value, so a held element
   needs an option around it. Made per element, that is an allocation per element (72 MB in §2's pipeline); held
   in `util/maybe`'s abstract `T`, every test of it is a call into another module (305 instructions per element;
   making `maybe.T` public is a task in [tasklist.md](tasklist.md)). Instead each such stage keeps an option of its
   own type, made with the first element it holds, whose payload's `var` it then overwrites, and a flag saying
   whether it holds an element not yet handed out:

   ```
   Let Slot = Fun(A::TYPE) Option none made with var x: A end end
   ```

   It overwrites the element through a `case` binder, which is the option's payload itself (`when made with c then
   c.x := x`); `s.slot!made.x := x` would compile and change nothing, since `!` makes a copy
   ([type-system.md](type-system.md) §6.8). `?made` and `!made.x` are inline tests and reads, and nothing is
   allocated after the first element (§2: 130 instructions per element, 1.8 MB). The stages share one private
   helper for this in `util/iter`.
5. **Closures inside, not an existential package.** `Tuple S::TYPE state: S more(s: S): Bool ... end` was measured
   as the representation too. It was twice as slow as the closures through `map` (§2): generic code reads the
   package's fields through proxy checks, since a value of the type may be a view of another, and calls the
   functions through adapters for the abstract `S`. It also cannot be read in place: `s.it.more(s.it.state)` is
   rejected ("bind to an immutable variable first"). The closures' environment is the state, and neither problem
   arises. Since `iter.T` is abstract, this is the module's choice alone and can be revisited.
6. **An iterator is one-shot; a source makes new ones.** Walking a collection again means asking it for another
   iterator, `vector.iter(v)`. A function that needs to walk its argument more than once takes a maker,
   `All() iter.T(A)`, which `util/iter` names `Iterable(A)`; most take an `iter.T(A)`.
7. **Pairs are records.** A map's entries are its `Entry(K V)`, the record `hashMap` and `sortedMap` already export;
   `enumerate`'s are `iter.Indexed(A)`, `Record index: Int value: A end`; and `zip`'s are `iter.Pair(A B)`,
   `Record first: A second: B end`. Each costs a record per element, which a type of iterator of pairs with its own
   readers would avoid, at the price of a second set of names (`more2`, `next2`, and readers) for every operation
   that takes one. A program walking a map's keys or values alone uses `keyIter` or `valueIter`, which make none.
8. **`util/iter` imports no collection; the collections import it.** Each collection exports its own iterators and
   builders, `vector.iter(v)`, `vector.fromIter(it)`, `sortedMap.entryIterInRange(m lo hi)` (§4). `util/iter` has
   sources only for what has no module of its own: ranges, arrays, strings' characters, and constants. This keeps
   the dependency one way, as `util/maybe`'s is.
9. **An iterator sees its collection live; a change during a walk leaves the result unspecified.** It reads the
   collection as it is at each `more` and `next`. If elements are added or removed while an iterator is in use,
   other than through it, what the iterator returns from then on is unspecified (it may skip or repeat elements,
   or, for the sorted collections, raise `error`, as the B-tree's `walk` does when its `changes` count moves). No
   collection counts changes for its iterators, so inserts and deletes cost nothing more.
10. **Producers written by hand are the cost of pull.** A collection's iterator keeps as state what its loop kept in
    local variables: an index for the vector, the deque, and the hash collections' tables; a stack of nodes for the
    B-tree, whose `walk` recurses today. A source whose `more` must do the work of finding the next element (the
    hash collections skipping deleted slots, a regular expression's next match) leaves its position on that
    element, so that `more` stays idempotent and `next` only reads and steps. A program that wants an iterator over
    its own structure writes the same and passes its closures to `iter.make`, or uses `iter.unfold` where the state
    is one value.
11. **`unfold` is functional.** `iter.unfold(seed step)` calls `step` with a seed, which returns `maybe.none()` at
    the end or `maybe.some` of an `iter.Step(A S)`, `Record value: A seed: S end`, the element and the next seed.
    That is an option and a record per element, against a step that changes its seed in place and returns `Bool`;
    the functional step reads better and needs no mutable state, and a producer that cannot afford the records uses
    `make`. Its `more` calls the step and holds the option it returns until `next`, so it needs no slot of its own
    (decision 4).
12. **`next` past the end raises.** Every `next`, a producer's included, checks that there is an element and raises
    `iter.exhausted` if not, as the `evens` example in §3 does. It costs a comparison per element, and a loop that
    goes wrong stops with an error rather than reading past its source.
13. **A peekable iterator is a type of its own.** `iter.peekable(it)` makes an `iter.Peekable(A)` over `it`, whose
    next element `iter.peek(p)` returns without consuming it (raising `iter.exhausted` at the end, as `next` does).
    The stream is walked through `iter.asIter(p)`, an `iter.T(A)` over the same elements and the same held one, so
    that `more` and `next` keep their one name each: a parser holds both, peeks through `p`, and takes through the
    iterator. It is a lookahead stage, holding what `peek` or `more` pulled in decision 4's slot. Only code that asks
    for peeking pays for it; a `peek` on every `iter.T` would make every iterator carry the slot.

## 2. Measurements

Each pipeline sums a range of 20,000,000 integers mapped by `x * 3`, then also filtered to the even ones, with the
library in its own module and the consumer in the program, compiled by the self-hosted compiler at `589fe937`
(arm64), as separate units (the default) and with `--whole-program`. Instructions retired per element of the source,
from `/usr/bin/time -l`:

| Shape | `map`, separate | `map` + `filter`, separate | `map`, whole | `map` + `filter`, whole | Max RSS, filter |
|---|---:|---:|---:|---:|---:|
| A `for` loop, written out | — | 19 | — | — | 1.7 MB |
| Push: `All(f: All(a: A) Bool) Bool` | 47 | 80 | 14 | 29 | 1.8 MB |
| Pull, `advance`/`current` closures, read in place | 53 | 114 | | | 1.8 MB |
| Pull, `more`/`next` closures, read in place, own option whose `var` is overwritten | 53 | 130 | 11 | 46 | 1.8 MB |
| Pull, `more`/`next` closures, read in place, own option around a reused cell | 53 | 143 | 11 | 47 | 1.8 MB |
| **The `var`'s row through `iter.more(it)` and `iter.next(it)` (the plan)** | 76 | 142 | 11 | 46 | 1.8 MB |
| Pull, `more`/`next` closures, own option per held element | 53 | 161 | | | 72 MB |
| Pull, `more`/`next` closures, `maybe.some` per held element | 53 | 230 | | | 72 MB |
| Pull, `more`/`next` closures, `util/maybe` around a reused cell | 53 | 305 | | | 1.8 MB |
| Pull, `more`/`next` existential package, `maybe.some` per element | 109 | 273 | | | 72 MB |

Blank cells were not measured. The 72 MB is an option made per held element; the rows show that the allocation
costs less than reaching the held element through another module's abstract type does. The plan's row differs from
the one above it only in the consumer's calls of `iter.more` and `iter.next`, which `--whole-program` inlines away;
so does the whole pipeline, to about a loop written out through a `map`, and to 2.5 times one through a `filter`
(its held element, and `more` and `next` both checking it). A pipeline allocates its stages' closures when it is built: two
per stage, and the state of the stages that have any; in a whole program, those it inlines are not allocated.

## 3. The interface

`lib/util/iter.int.quest`, in outline (comments in the real file say what each does; the names follow `vector` and
`hashMap` where they have the same operation):

```
interface Iter
import
    util/maybe : util/Maybe
export
    (* An iterator of A's: more says whether there is another, next returns
     * it and moves past it *)
    T::ALL(A::TYPE) TYPE
    (* An iterator whose next element can be looked at without consuming it *)
    Peekable::ALL(A::TYPE) TYPE
    Def Iterable = Fun(A::TYPE) All() T(A)
    Def Indexed = Fun(A::TYPE) Record index: Int value: A end
    Def Pair = Fun(A::TYPE B::TYPE) Record first: A second: B end
    Def Step = Fun(A::TYPE S::TYPE) Record value: A seed: S end

    (* Raised by next when there is no next element *)
    exhausted: Exception

    (* Iterating *)
    more: All(A::TYPE) All(it: T(A)) Bool
    next: All(A::TYPE) All(it: T(A)) A
    make: All(A::TYPE) All(more: All() Bool next: All() A) T(A)

    (* Sources *)
    empty: All(A::TYPE) All() T(A)
    once: All(A::TYPE) All(a: A) T(A)
    range: All(lo: Int hi: Int) T(Int)            (* lo up to hi - 1 *)
    rangeBy: All(lo: Int hi: Int step: Int) T(Int)
    ofArray: All(A::TYPE) All(a: Array(A)) T(A)
    chars: All(s: String) T(Char)
    unfold: All(A::TYPE S::TYPE) All(seed: S step: All(s: S) maybe.T(Step(A S))) T(A)

    (* Stages *)
    map, filter, filterMap, take, drop, takeWhile, dropWhile, concat, flatMap: on T(A)
    peekable: All(A::TYPE) All(it: T(A)) Peekable(A)
    peek: All(A::TYPE) All(p: Peekable(A)) A                (* the next element, not consumed *)
    asIter: All(A::TYPE) All(p: Peekable(A)) T(A)          (* the same elements, the peeked one first *)
    enumerate: All(A::TYPE) All(it: T(A)) T(Indexed(A))
    zip: All(A::TYPE B::TYPE) All(a: T(A) b: T(B)) T(Pair(A B))
    merge: All(A::TYPE) All(a: T(A) b: T(A) compare: All(x: A y: A) Int) T(A)

    (* Consumers *)
    forEach: All(A::TYPE) All(it: T(A) f: All(a: A) Ok) Ok
    fold, count, any, all, find, first, last, min, max, toArray, sumInt: on T(A)
    equal: All(A::TYPE) All(a: T(A) b: T(A) eq: All(x: A y: A) Bool) Bool
end
```

`merge` looks ahead on both sides and holds the smaller element's side, with decision 4's slot; `zip` and `equal`
need no holding. The consumers read the closures in place, so a loop through `forEach`, `fold`, or `find` pays no
call per element for `more` and `next`, only the call of its function. The same code walks any source:

```
let total(it: iter.T(Int)): Int =
    begin
        let var t = 0
        while iter.more(it) do t := t + iter.next(it) end
        t
    end

total(vector.iter(v)) + total(hashSet.iter(h)) + total(iter.take(sortedSet.iter(s) 10))

(* Whether two sorted sets have the same members, stopping at the first difference *)
iter.equal(sortedSet.iter(a) sortedSet.iter(b) intEqual)

(* A producer: the even numbers below n *)
let evens(n: Int): iter.T(Int) =
    begin
        let c = tuple let var i = 0 end
        iter.make(fun(): Bool c.i < n fun(): Int begin
            if c.i >= n then raise iter.exhausted end
            let x = c.i c.i := x + 2 x
        end)
    end
```

## 4. What each collection adds

Each takes its element types as the module's other operations do, and walks in the order its `forEach` does:

| Module | Iterators | Builders |
|---|---|---|
| `collections/vector` | `iter`, `iterReversed` | `fromIter`, `appendIter` |
| `collections/deque` | `iter` | `fromIter` |
| `collections/hashMap` | `entryIter` (of its `Entry(K V)`), `keyIter`, `valueIter` | `fromEntries` |
| `collections/hashSet` | `iter` | `fromIter` |
| `collections/sortedMap` | `entryIter`, `entryIterFrom`, `entryIterInRange`, `keyIter`, `valueIter` | `fromEntries` |
| `collections/sortedSet` | `iter`, `iterFrom`, `iterInRange` | `fromIter` |
| `collections/heap` | `iter` (in heap order, not sorted), `drain` (in order, removing) | `fromIter` |
| `collections/bitset` | `iter` (members in order) | `fromIter` |
| `util/regexp` | `matches`, `matchStrings` (lazy `findAll`) | — |

`keys` and `values` stay the names of the vector-returning operations they are now, so the iterators are `keyIter`
and `valueIter`; `entryIter` makes a record per element, the others none. Each makes its iterator with
`iter.make`, from closures over its own state. The sorted
collections' iterators keep a stack of the nodes above the current key, at most the tree's height (decision 10). The
hash collections' walk their insertion-ordered table by index; `more` skips deleted slots and stops on a live one,
which `next` returns. A regular expression's `matches` finds the next match in `more` and holds it (its type is
known, so it needs no option); `next` hands it out and resumes the search after it.

## 5. Left out

- **Generators.** A `yield` would let a producer be written as a loop, but it is a language change (a coroutine per
  walk).
- **Push as a second paradigm.** `forEach` is the one push operation, a consumer. Collections keep their own
  `forEach`, `fold`, and `map`, which stay the fastest way to walk one collection whole.
- **A visible iterator type** (`it.more()`), for the reasons in decision 2.
- **An iterator of pairs** with readers of its own (`more2`, `next2`, `left`, `right`), which would avoid a record
  per element but double the names; pairs are records (decision 7).
- **Change counting** in the collections for their iterators (decision 9).
- **`advance`/`current`, out parameters, and the existential package**, for the reasons in decisions 3 and 5. An
  `out` parameter (`next(out x: A): Bool`) would be one call per element, but almost nothing uses `out`
  parameters, and a `map` would still need a local of type `A` to start with.
- **Parallel or chunked walks**, until Quest has threads.

## 6. Steps

1. `util/iter` with `T`, `Iterable`, the record types, `make`, the sources, stages, and consumers, and decision 4's helper for
   the lookahead stages; a golden program for each, including `more` called repeatedly and `next` past the end; the
   cost table of §2 as a benchmark in `benchmarks/`, separate and whole-program, so the numbers are kept; and
   libraries.md's section.
2. The collections' iterators and builders (§4), with goldens through every backend: vector, the hash collections,
   deque, bitset, heap, and the sorted collections last (the stack).
3. `regexp.matches` and `matchStrings`, and `findAll` defined over them.
4. The compiler's own loops where an iterator would replace a vector it builds only to walk it, measured on the
   driver build as usual.

## 7. Settled with the user

2026-11-19: `util/iter` (decision 8 and the module's name); an iterator sees its collection live, with the result
unspecified on a change (decision 9); a functional `unfold` (decision 11); records for pairs (decision 7); `next`
raising past the end (decision 12); and a peekable iterator as a type of its own (decision 13). Before that, in
order: pull rather than push, `more`/`next` rather than `advance`/`current` for familiarity, and an abstract `iter.T`
read with functions rather than a visible tuple.
