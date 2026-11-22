# Iterators: `util/iter` and `util/iterTools`

`util/iter : util/Iter` is Quest's iteration library: one way to walk a vector, a hash set, a sorted map's range, a
string's characters, a reader's lines, or a regular expression's matches, and to chain `map`, `filter`, `take` and the
rest over any of them without building vectors in between. `util/iterTools : util/IterTools`, after Python's
`itertools`, adds the sources without end, the stages that group, window, or interleave, the combinatoric iterators,
and a few consumers. Both are Quest alone, with no externals and no change to the language
(`lib/util/iter.{int,mod}.quest`, `lib/util/itertools.{int,mod}.quest`). Their interfaces and a summary of their rules
are in [libraries.md](libraries.md) §1.14 and §1.15. This document says how they are built, who uses them, why they
are the way they are, what they cost, and what was left out.

They have three kinds of user:
- **Programs,** walking collections and their own structures.
- **The producers:** the collections, `util/regexp`, and `io/lines`, each of which exports its own iterators and
  builders (§3).
- **The self-hosted compiler,** which walks hash maps through iterators where it built a vector only to walk it (§5).

## 1. Rules

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
2. **`iter.T` is abstract, read with functions, as every Quest library's type is.** An iterator is an `iter.T(A)`,
   read with `iter.more(it)` and `iter.next(it)`, as a vector is a `vector.T(A)` read with `vector.get(v i)`. Inside
   `util/iter` it is a pair of closures:

   ```
   Let T = Fun(A::TYPE) Tuple more: All() Bool next: All() A end
   ```

   and a producer outside makes one with `iter.make(more next)`, a call per iterator, not per element.

   The alternative was the tuple visible, read as `it.more()` and `it.next()`. That would be the only method-like API
   in `lib/`, and it would fix the representation for good. Abstract, `iter.T` can grow a change counter, a size hint,
   or a `close` for an iterator over a file, or take another shape if one becomes cheaper, without changing a caller,
   and the importers' interfaces do not record it. The price is a call into `util/iter` for each `more` and `next` at
   the consumer, since separate compilation inlines nothing across modules (§2); a whole program folds the stages
   into its loop through the abstract type's copies ([ir.md](ir.md) §8.6).
3. **`more` and `next`, for familiarity.** `more` says whether there is another element and changes nothing a caller
   can see: calling it twice is calling it once. `next` returns the element and moves past it. This is Java's
   `Iterator` (`hasNext`, `next`), which most programmers know, and `next` gives each element once, so a `map`'s
   function runs once per element whatever the caller does. A producer's closures keep this contract; `make` does not
   check them.

   `advance`/`current` (C#'s `MoveNext`/`Current`) is cheaper through stages that look ahead (114 instructions per
   element through `filter` against 130, §2), since with it nothing is held. With `more`/`next`, a stage that has to
   find out whether there is another element (`filter`, `filterMap`, `takeWhile`, `dropWhile`, `merge`, a peekable
   iterator) pulls it from its source in `more` and holds it until `next`. Familiarity, a `next` that cannot be read
   before its iterator starts, and `map`'s once-per-element call outweigh a difference confined to those stages.
4. **`next` past the end raises `iter.exhausted`.** Every `next`, a producer's included, checks that there is an
   element. It costs a comparison per element (about 6 instructions through a `map`, §2), and a loop that goes wrong
   stops with an error rather than reading past its source.
5. **A lookahead stage holds its element in an option it reuses.** A generic `A` has no empty value, so a held
   element needs an option around it. Made per element, that is an allocation per element (72 MB in §2's pipeline);
   held in `util/maybe`'s abstract `T`, every test of it is a call into another module (305 instructions per element).
   Instead `util/iter` keeps a private `Slot`, an option of its own type made with the first element held, whose
   payload's `var` is then overwritten, and a flag saying whether it holds an element not yet handed out:

   ```
   Let Slot = Fun(A::TYPE) Option none made with var x: A end end
   ```

   It overwrites the element through a `case` binder, which is the option's payload itself (`when made with c then
   c.x := x`). `if l.slot?made then l.slot!made.x := x else ... end` stores into the same component, since a
   selection through `!` used as a location is the option's own ([type-system.md](type-system.md) §6.8), and costs
   the same: the simplifier decides the location's tag test by the `?made` before it, and reads the slot once
   ([ir.md](ir.md) §8.6). Measured 2026-11-22 with `benchmarks/iter/`, a `filter` took 44.7 instructions per element
   in a whole program against the `case`'s 45.1, and 153.3 against 153.2 separately, so either may be used.
   `?made` and `!made.x` are inline tests and reads,
   and nothing is allocated after the first element (130 instructions per element, 1.8 MB). The stages that look ahead
   share one pair of helpers for it, `hold` and `release`.
6. **Closures, not an existential package.** `Tuple S::TYPE state: S more(s: S): Bool ... end` was measured as the
   representation too. It was twice as slow as the closures through `map` (§2): generic code reads the package's
   fields through proxy checks, since a value of the type may be a view of another, and calls the functions through
   adapters for the abstract `S`. It also cannot be read in place: `s.it.more(s.it.state)` is rejected ("bind to an
   immutable variable first"). The closures' environment is the state, and neither problem arises. Since `iter.T` is
   abstract, this is the module's choice alone and can be revisited.
7. **An iterator is one-shot; a source makes new ones.** Walking a collection again means asking it for another
   iterator, `vector.iter(v)`. A function that needs to walk its argument more than once takes a maker,
   `All() iter.T(A)`, as `iterTools.cycleFrom` does; most take an `iter.T(A)`. The maker has no name (an `Iterable`):
   an interface's manifest type cannot name an abstract type of the same interface ([json.md](json.md) rule 6).
8. **Pairs are records and tuples, one per element.** `enumerate`'s elements are `iter.Indexed(A)`, `Record index: Int
   value: A end`; `zip`'s are `iter.Pair(A B)`, `Record first: A second: B end`; and a map's entries are its
   `Entry(K V)`, the tuple `Tuple key: K value: V end` that `hashMap` and `sortedMap` export (a record until nothing
   was found to use an entry at a supertype). Each costs an allocation per element, which a type of iterator of pairs
   with its own readers would avoid, at the price of a second set of names (`more2`, `next2`, and readers) for every
   operation that takes one. A program walking a map's keys or values alone uses `keyIter` or `valueIter`, which make
   none.
9. **`util/iter` imports no collection; the collections import it.** Each collection exports its own iterators and
   builders, `vector.iter(v)`, `vector.fromIter(it)`, `sortedMap.entryIterInRange(m lo hi)` (§3). `util/iter` has
   sources only for what has no module of its own: ranges, arrays, strings' characters, and constants. This keeps the
   dependency one way, as `util/maybe`'s is, and is why `util/iterTools`, which needs `vector`, `deque`, and `hashSet`,
   is a module of its own (§4).
10. **An iterator sees its collection live; a change during a walk leaves the result unspecified.** It reads the
    collection as it is at each `more` and `next`. If elements are added or removed while an iterator is in use,
    other than through it, what the iterator returns from then on is unspecified: it may skip or repeat elements,
    or, for the sorted collections, raise `error`, since the B-tree's cursor checks the `changes` count its `walk`
    already keeps. No collection counts changes for its iterators alone, so inserts and deletes cost nothing more.
11. **Producers are written by hand.** That is the cost of pull. A collection's iterator keeps as state what its loop
    kept in local variables: an index for the vector, the deque, and the hash collections' tables; a stack of nodes
    for the B-tree, whose `walk` recurses. A source whose `more` must do the work of finding the next element (the
    hash collections skipping deleted slots, a regular expression's next match) leaves its position on that element,
    so that `more` stays idempotent and `next` only reads and steps. A program that wants an iterator over its own
    structure does the same and passes its closures to `iter.make`, or uses `iter.unfold` where the state is one
    value.
12. **`unfold` is functional.** `iter.unfold(seed step)` calls `step` with a seed, which returns `maybe.none()` at the
    end or `maybe.some` of an `iter.Step(A S)`, `Record value: A seed: S end`, the element and the next seed. That is
    an option and a record per element, against a step that changes its seed in place and returns `Bool`; the
    functional step reads better and needs no mutable state, and a producer that cannot afford the records uses
    `make`. Its `more` calls the step and holds the option it returns until `next`, so it needs no slot (rule 5).
13. **A peekable iterator is a type of its own.** `iter.peekable(it)` makes an `iter.Peekable(A)` over `it`, whose
    next element `iter.peek(p)` returns without consuming it (raising `iter.exhausted` at the end, as `next` does).
    The stream is walked through `iter.asIter(p)`, an `iter.T(A)` over the same elements and the same held one, so
    that `more` and `next` keep their one name each: a parser holds both, peeks through `p`, and takes through the
    iterator. It holds what `peek` or `more` pulled in rule 5's slot. Only code that asks for peeking pays for it; a
    `peek` on every `iter.T` would make every iterator carry the slot. `merge` is built on two of them.

## 2. Cost

The shapes were measured before the library was written. Each pipeline sums a range of 20,000,000 integers mapped by
`x * 3`, then also filtered to the even ones, with the library in its own module and the consumer in the program,
compiled by the self-hosted compiler at `589fe937` (arm64), as separate units (the default) and with
`--whole-program`. Instructions retired per element of the source, from `/usr/bin/time -l`:

| Shape | `map`, separate | `map` + `filter`, separate | `map`, whole | `map` + `filter`, whole | Max RSS, filter |
|---|---:|---:|---:|---:|---:|
| A `for` loop, written out | — | 19 | — | — | 1.7 MB |
| Push: `All(f: All(a: A) Bool) Bool` | 47 | 80 | 14 | 29 | 1.8 MB |
| Pull, `advance`/`current` closures, read in place | 53 | 114 | | | 1.8 MB |
| Pull, `more`/`next` closures, read in place, own option whose `var` is overwritten | 53 | 130 | 11 | 46 | 1.8 MB |
| Pull, `more`/`next` closures, read in place, own option around a reused cell | 53 | 143 | 11 | 47 | 1.8 MB |
| The `var`'s row through `iter.more(it)` and `iter.next(it)`, the tuple visible | 76 | 142 | 11 | 46 | 1.8 MB |
| **`util/iter` as built: abstract `iter.T`, checking `next` (`benchmarks/iter/`)** | 82 | 151 | 11 | 45 | |
| Pull, `more`/`next` closures, own option per held element | 53 | 161 | | | 72 MB |
| Pull, `more`/`next` closures, `maybe.some` per held element | 53 | 230 | | | 72 MB |
| Pull, `more`/`next` closures, `util/maybe` around a reused cell | 53 | 305 | | | 1.8 MB |
| Pull, `more`/`next` existential package, `maybe.some` per element | 109 | 273 | | | 72 MB |

Blank cells were not measured. The 72 MB is an option made per held element; the rows show that the allocation costs
less than reaching the held element through another module's abstract type does.

- **Separate compilation** pays a call into `util/iter` for each `more` and `next` the consumer makes, about 23
  instructions per element it takes (53 to 76 through a `map`, 130 to 142 through a `map` and a `filter`). Stages
  inside `util/iter` read the closures in place and do not pay it, and nor do its consumers (`forEach`, `fold`,
  `find`, `sumInt`, ...), which pay only the call of their function.
- **A whole program** inlines across modules. With the tuple visible, it inlines the consumer's `iter.more` and
  `iter.next` away, and the whole pipeline too: to about a loop written out through a `map` (11), and to 2.5 times
  one through a `filter`, whose element is held and checked by both `more` and `next`. With `iter.T` abstract, as
  built, the same: the simplifier folds a known tuple's projections through the copies that give it the abstract
  type ([ir.md](ir.md) §8.6; 56 through a `map` before it).
- **Building a pipeline** allocates its stages' closures: two per stage, and the state of the stages that have any.
  In a whole program, those it inlines are not allocated.

`benchmarks/iter/` keeps the library's own measurement: `run.py` builds `iter.quest` both ways, runs a loop written
out, a `map`, a `map` and a `filter`, and the same through `iter.sumInt`, and prints the instructions per element. Its
README has the numbers at `7e9b5f89`, the library's first version (17 for its loop, a different program from the
table's).

`util/iterTools` was not measured, and no benchmark uses it. Each of its stages is one `iter.make`, two closures and a
state tuple when it is made, and per element the calls through its source's closures plus its own: about 23
instructions per element per stage under separate compilation; under a whole program its stages fold into the
loop as `util/iter`'s do. The combinatoric iterators and `batched`, `windows`, and `groupBy` allocate an array per
element as well.

## 3. Producers

Each takes its element types as the module's other operations do, walks in the order its `forEach` does, and makes
its iterator with `iter.make`, from closures over its own state:

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
| `collections/bTree` | `cursor` (each entry in a range, as `read(k v)`), which the sorted collections use | — |
| `util/regexp` | `findIter`, `findStringIter` (lazy `findAll`, which is now `vector.fromIter(findIter(r s))`) | — |
| `io/lines` | `iter` (the rest of a reader's lines, [libraries.md](libraries.md) §3.3) | — |

- **Names.** `keys` and `values` stay the names of the vector-returning operations, so the iterators are `keyIter`
  and `valueIter`. The regular expression's iterators were to be `matches` and `matchStrings`, but `matches` was
  taken (whether the whole string matches). The collections import the library as `iterLib`, since an operation
  named `iter` would hide an import named `iter`.
- **The hash collections** walk their insertion-ordered table by index; `more` skips deleted slots and stops on a
  live one, which `next` returns.
- **The sorted collections** walk through the B-tree's `cursor`, which keeps a stack of the nodes above the current
  key, at most the tree's height, and raises `error` on a change, as `walk` does (rule 10).
- **`regexp.findIter`** finds the next match in `more` and holds it (its type is known, so it needs no option);
  `next` hands it out and resumes the search after it.
- **`io/lines.iter`** reads through the reader, which holds the position, so two iterators over one reader share it,
  and reading the reader between `next`s moves it. It does not close the reader.

## 4. `util/iterTools`

1. **A module of its own.** `util/iter` has the stages most programs use, and every collection's iterator depends on
   it; `util/iterTools` has the ones reached for less often, and its own dependencies (`collections/vector`,
   `deque`, `hashSet`), which `util/iter` must not have (rule 9). The name is `util/iterTools`, the file
   `itertools`, as `util/stringBuilder`'s is `stringbuilder`.
2. **Built on `util/iter`'s public API alone.** `iter.T` is abstract outside `util/iter`, so every stage is
   `iter.make(ready pull)` over `iter.more` and `iter.next`, its state a tuple of `var`s the two closures share. Where
   `pull` hands out the source's next element as it is, it calls the source's `next` and lets its `iter.exhausted`
   propagate; the stages that choose what to hand out (`stepBy`, `windows`, `pairwise`, `intersperse`, `interleave`,
   `zipLongest`) call their own `ready` first and raise `iter.exhausted` themselves. Several are `util/iter`'s stages
   composed: `flatten` is `flatMap` of the identity, `reject` is `filter` of `not`, `compress` is `filterMap` over
   `zip`, `slice` is `stepBy` of `take` of `drop`, `unique` is `filter` with `hashSet.insert`, and `nth` is `first`
   of `drop`. `windows` slides a `deque`, `tee` keeps a `deque` per branch of what the others pulled and it has not
   reached, and `batched`, `groupBy`, and `cycle` collect into a `vector`.
3. **Lookahead through `iter.peekable`.** A stage that must see the element after a run to know the run has ended
   (`groupBy`, `uniqueRuns`) reads it through `iter.peekable` and `iter.asIter`, rather than keeping a slot of its
   own. `accumulate` and `pairwise` hold the element before in a `Held` option (`made with var x`) whose payload is
   overwritten through the case binder, as `util/iter`'s slot is, so nothing is allocated per element.
4. **`cycle` keeps a copy; `cycleFrom` asks again.** An iterator is consumed once (rule 7). `cycle(it)` keeps the
   elements as it first hands them out and replays them, as Python's does; `cycleFrom(source)` takes an
   `All() iter.T(A)` and calls it for each pass, keeping nothing, for a source that is cheap to walk again (an array,
   a range).
5. **Every array handed out is fresh.** `batched`, `windows`, `groupBy`'s `values`, and the combinatoric iterators
   make a new array for each element, which the caller may keep or change. Python's tuples are immutable, so it may
   share; Quest's arrays are not.
6. **Errors raise `iterTools.error`** when the stage is made, not when it is first pulled: a `step` or `size` below
   1, a `lo` below 0 (`slice`), an `r` below 0, and an `n` below 0 (`tee`, `nth`). An `r` past the array's length is
   not an error: it gives no elements, as Python's does.
7. **The combinatoric iterators take arrays,** since they index their pool repeatedly, and use Python's algorithms
   (`idx`, `cycles`, and a `done` flag), so the order is Python's: by the positions chosen, earlier ones changing
   slowest. `product` of two arrays gives `iter.Pair`s; `productOf` of any number gives arrays, and `power(a r)` is
   `productOf` of `r` copies of `a` (Python's `product(a, repeat=r)`).
8. **`groupBy` hands out whole groups.** Python's `groupby` yields a key and a sub-iterator that shares the source,
   valid only until the next group is pulled; here each `Group(K A)` is a record of the key and an array of the run,
   so groups may be kept. `key` is called once per element: the stage maps each element to a pair of its key and
   itself first.
9. **`tee` owns its source.** Once `tee` is called, the source must not be pulled except through its branches, as in
   Python.
10. **Names** are Python's where they say what Quest's conventions would, and Quest's where those are set
    ([libraries.md](libraries.md) §1.15 lists the renamings). `iterate` (Haskell's) and `intersperse` come from other
    languages' libraries.

## 5. The Compiler

The self-hosted compiler walks hash maps through iterators where it built a vector of keys or values only to walk
it: `hashMap.keyIter` in `typechecker/scoping` (`copyIds`), `valueIter` in `typechecker/bindings` (`valueIds`), a
block's scope in `typechecker/control`, `modules/elaboration`, and `modules/graph`, and `entryIter` over the known
closures in `ssa/build/unit` and the C printer, where it also saves a `find` per key (`f16c148d`). Stage 2 building
the driver from scratch, three runs each, retired 511.3 billion instructions against 512.5 (one baseline run at
520.5), about 0.2% fewer, in 67–70 s against 69–71 s.

The release builds the compiler first, against its own `lib/`, so the compiler could use `util/iter` only once a
release (`1945cfef`) had it, as for `util/digest`.

## 6. Tests

- **`tests/source/stdlib/iter_operations.quest`:** each source, stage, and consumer of `util/iter`; `more` called
  repeatedly, `next` past the end, and peeking; the stages that look ahead holding elements of a type with no empty
  value (strings); and pipelines against loops written out.
- **`tests/source/stdlib/collection_iterators.quest`:** each collection's iterators against its `forEach`, through
  stages; the B-tree's cursors over a tree of several levels, from and in ranges; a hash map's iterators past deleted
  entries; a sorted collection changed during a walk; and the builders.
- **`tests/source/stdlib/regexp_iterators.quest`:** the same matches as `findAll`, empty ones included, a walk that
  stops early, and a pipeline over the matches.
- **`tests/source/stdlib/itertools_operations.quest`:** every operation of `util/iterTools`, with the results of
  Python 3.11's `itertools` for the same arguments (`batched`, which is 3.12's, by hand); the edge cases (empty
  inputs, `r` of 0 and past the length, sizes that do not divide); each error; the combinatoric counts against their
  formulas; the arrays' freshness; and the number of calls `iterate` and `groupBy` make to their functions.

Each runs through every backend. The shared goldens (`tokenize`, `parse`, `typecheck`, `run`) are the bootstrap's;
the self-hosted compiler prints the same `run` output and has its own IR and SSA goldens.

## 7. Left Out and Pending

Left out:
- **Generators.** A `yield` would let a producer be written as a loop, but it is a language change (a coroutine per
  walk).
- **Push as a second paradigm.** `forEach` is the one push operation, a consumer. The collections keep their own
  `forEach`, `fold`, and `map`, which stay the fastest way to walk one collection whole.
- **A visible iterator type** (`it.more()`), rule 2.
- **An iterator of pairs** with readers of its own (`more2`, `next2`, `left`, `right`), rule 8.
- **Change counting** in the collections for their iterators, rule 10.
- **`advance`/`current`, out parameters, and the existential package,** rules 3 and 6. An `out` parameter
  (`next(out x: A): Bool`) would be one call per element, but almost nothing uses `out` parameters, and a `map`
  would still need a local of type `A` to start with.
- **Parallel or chunked walks,** until Quest has threads.
- **Python's `chain`, `starmap`, and the stages `util/iter` has.** `chain` is `iter.concat`; Quest functions take
  their arguments, not a tuple of them, so `iter.map` with a function that reads the pair's fields is `starmap`; and
  `zip`, `takewhile`, `dropwhile`, `filter`, and `map` are in `util/iter`.
- **Python's shared `groupby` sub-iterators,** §4 item 8.
- **More recipes** (`powerset`, `partition` into iterators, `nth_combination`, the `random_` ones): each is a few
  lines over these; they can be added when a program wants one.

Pending:
- **`util/maybe` inlined.** `filterMap`'s function, `unfold`'s step, `find`, `first`, and the rest speak `maybe.T`,
  which is abstract, so every test of one outside `util/maybe` is a call; that is why the stages hold their elements
  in a slot of their own (rule 5). The tasklist entry "A few library modules inlined into their importers, as in a
  whole program" ([tasklist.md](tasklist.md)) would let importers inline `util/maybe` and keep `maybe.T` abstract.
