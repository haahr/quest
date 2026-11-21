# Plan: Lazy Values, Memoization, and a Linked Hash Map

Three libraries from [future-libraries.md](future-libraries.md): `util/lazy`, a value computed the first time it is
asked for and kept (OCaml's `Lazy`, Rust's `LazyCell`, Go's `sync.OnceValue`); `util/memo`, a function that keeps the
results it has returned (Python's `functools.cache` and `lru_cache`); and `collections/linkedHashMap`, a hash map
whose keys can be reordered in constant time (Python's `OrderedDict`, Java's `LinkedHashMap`), on which `util/memo`'s
bounded cache is built. All three are written, with run tests whose output was worked out by hand and matches in the
bootstrap and the self-hosted compiler, separately and as a whole program:

| File | What |
|---|---|
| `lib/collections/linkedhashmap.int.quest`, `.mod.quest` | `collections/linkedHashMap`, 345 lines with comments |
| `lib/util/lazy.int.quest`, `.mod.quest` | `util/lazy`, 61 lines |
| `lib/util/memo.int.quest`, `.mod.quest` | `util/memo`, 118 lines |
| `tests/source/stdlib/linkedhashmap_operations.quest` | order, reinsertion, moves, pops, deletes anywhere, growth, the iterators, and a thousand random operations against a list kept by hand |
| `tests/source/stdlib/lazy_operations.quest` | forcing once, `fromValue`, `peek`, `map`, `once`, raises, `cycle` |
| `tests/source/stdlib/memo_operations.quest` | unbounded, recursive (`fib 80` in 81 calls), raises, LRU order, `forget`, `clear`, a two-value key, the error |

Nothing is committed; §8 has the steps.

## 1. Decisions

1. **Three modules.** `util/lazy` imports only `util/maybe` and `raised`, so any library may use it, the collections
   and `util/iter` included. `util/memo` needs `collections/hashMap` and `collections/linkedHashMap`, which import
   `util/iter`, and so could not be imported by them. `collections/linkedHashMap` is a collection of its own, not
   part of `util/memo`, since its order operations are what any cache, or any queue keyed by value, needs.
2. **A raise keeps nothing, and the next call tries again** (settled with the user, 2026-11-20). If a lazy value's
   computation raises, the value goes back to pending and the exception goes on, with its own raise site
   (`raised.reraise`); the next `force` calls the function again. If a memoized function raises, no result is kept
   for that key. This is Python's `cache` and Rust's `OnceCell::get_or_try_init`, and it lets a computation that failed
   for a passing reason (a file not there yet) succeed later. OCaml instead keeps the exception and raises it again on
   every `force`, so the function runs at most once; Rust's `LazyCell` is poisoned for good. The price of this choice
   is that a computation that raises may run more than once.
3. **Forcing a lazy value inside its own computation raises `lazy.cycle`,** as OCaml's raises `Lazy.Undefined`,
   rather than recursing until `stack.overflow`. The state is `running` while the function runs, which `force` checks.
   After `cycle`, the value is pending again (decision 2). `util/memo` does not check: a recursive call for a key whose
   result is being computed computes it again, as Python's `cache` does, and a function that truly calls itself with
   the same key overflows the stack.
4. **The function goes once the value comes.** A forced lazy value holds only its value, so what the function captured
   can be collected, as in OCaml and Rust.
5. **One argument, with `equal` and `hash`.** Quest has no tuple of arguments to key on, as Python's decorator does,
   so a memoized function takes one value; a function of several takes a tuple or a record, with an `equal` and a
   `hash` for it (`hash.combine`). The equality and hash are given as `collections/hashMap`'s are; `hash.identityEqual`
   and `hash.identityHash` give Python's default for objects.
6. **Recursion by `self`.** Python's `@cache` on a recursive function memoizes its own calls because the decorator
   rebinds the function's name, which its body looks up when it runs. A Quest function's own name always means
   itself, so `makeRecursive` and `makeBoundedRecursive` take a function of `self` and the key and pass it the
   memoized function. `make` and `makeBounded` wrap a plain function to take a `self` it ignores, so all four share
   two implementations. The four constructors stay four (settled with the user), rather than a capacity of 0 meaning
   unbounded.
7. **`make`, not `new`, for memo's constructors** (settled with the user): `make`, as `iter.make` and `lazy.make`, is
   for a value built from the functions given; `new` is for an empty container the caller fills, as
   `linkedHashMap.new` is. Type parameters are curried, as the rest of `lib/` has them.
8. **A bounded cache is least recently used, on a linked hash map.** `collections/hashMap` keeps insertion order, so a
   hit could delete and insert its key, and an eviction take the first; but a deleted entry stays in its dense arrays
   until a rebuild, and finding the first live key passes over them, up to the map's size between rebuilds. A linked
   hash map moves a key to the end and takes the first off in constant time: a hit is `get` and `moveToEnd`, a miss at
   capacity `popFirst` and `insert`.
9. **A linked hash map's order changes only when asked** (settled with the user): `get`, `find`, and `contains` do not
   move a key, and inserting a key already present changes its value and leaves it in place, as Python's `OrderedDict`
   does. Java's `LinkedHashMap` has an access order that moves a key on every read; here a cache calls `moveToEnd`
   itself, which keeps reads free of surprises for a map used only for its order.
10. **A cache is a tuple of closures.** `memo.T(K V)` is `apply`, `contains`, `size`, `forget`, `clear`, and the
    counts, made by `unbounded` or `lru` over their own tables, so one abstract type serves both kinds, and in a whole
    program the closures fold into their callers as an iterator's do (ir.md §8.6).
11. **Hits and misses are counted,** as Python's `cache_info`, which is how one tells whether a cache is earning its
    memory; `clear` keeps them.
12. **`lazy.fromValue(x)` for a value already computed** (settled with the user, 2026-11-20). Other languages: OCaml's
    `Lazy.from_val`, Kotlin's `lazyOf`, Scheme's `eager` (SRFI-45) and `make-promise` (R7RS), Rust's
    `OnceCell::from`. `lazy.value` reads as an accessor, as Kotlin's `Lazy.value` is one; `lazy.eager` is Scheme's
    word, but an oxymoron qualified by its module; bare `lazy.from` reads as a conversion, so `lazy.from(f)` may be
    taken to take the function, and the misuse type-checks. `fromValue` is OCaml's name spelled out, and names its
    source as `hashMap.fromEntries` and `vector.fromArray` do.

## 2. `collections/linkedHashMap`

```quest
interface LinkedHashMap
import
    util/maybe : util/Maybe
    iterLib = util/iter : util/Iter
    word: Word
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    Def Entry = Fun(K::TYPE V::TYPE) Tuple key: K value: V end
    error: Exception                                              (* find of a key not present *)
    new: (equal hash) T(K V)
    size, empty
    get: (m key) maybe.T(V)                                       (* does not reorder *)
    contains, find
    insert: (m key value) Bool                                    (* new keys last; present ones stay *)
    delete: (m key) maybe.T(V)
    clear
    moveToEnd, moveToFront: (m key) Bool                          (* whether present *)
    first, last, popFirst, popLast: (m) maybe.T(Entry(K V))
    forEach: (m action) Ok
    entryIter, keyIter, valueIter                                 (* first to last, live *)
end
```

(Each is polymorphic in `K` and `V`; the interface file has the full types.) `Entry` is the same shape as
`hashMap.Entry`. `hashMap`'s `map`, `filter`, `fold`, `filterMap`, `keys`, `values`, `entries`, and `fromEntries` are
left out until something wants them.

The entries are in slots 0 to `count - 1` of four arrays (`keys`, `values`, and `prev` and `next`, which link the
slots from first to last, `~1` ending the list), with a `hashMap.T(K Int)` from keys to slots. Moving an entry is
relinking it, and nothing is allocated except when the arrays grow (doubling, from 8). A delete moves the last slot
into the deleted one's place, relinking its neighbors and updating its key's slot, so the slots stay dense; then it
overwrites the slot left over with the first entry's key and value, so that no slot past `count` keeps a deleted key
or value from being collected (and empties the arrays when the map is empty). An iterator holds the slot it returned
last and follows its `next`; a change to the map other than through it leaves what it returns unspecified, as for
every collection (docs/iter.md), and a slot past `count` ends it rather than reading past the entries.

## 3. `util/lazy`

```quest
interface Lazy
import
    util/maybe : util/Maybe
export
    T::ALL(A::TYPE) TYPE
    cycle: Exception
    make: All(A::TYPE) All(f: All() A) T(A)                       (* not called until forced *)
    fromValue: All(A::TYPE) All(a: A) T(A)                            (* already computed *)
    force: All(A::TYPE) All(l: T(A)) A
    isForced: All(A::TYPE) All(l: T(A)) Bool
    peek: All(A::TYPE) All(l: T(A)) maybe.T(A)                    (* without forcing *)
    map: All(A::TYPE B::TYPE) All(l: T(A) f: All(a: A) B) T(B)    (* lazy too *)
    once: All(A::TYPE) All(f: All() A) All() A                    (* Go's sync.OnceValue *)
end
```

A lazy value is `Tuple var state: State(A) end`, where `State(A)` is `Option pending with f: All() A end running
forced with value: A end end`. `force` reads the state: `forced`, the value; `running`, raise `cycle`; `pending`,
set `running`, call the function inside a `try` whose `else with e` puts back the pending state it found and
re-raises, then set `forced` and return the value. `make` allocates the tuple and the pending option; the first
`force`, the forced option. A forced value costs a call into `util/lazy`, a tag test, and a load.

## 4. `util/memo`

```quest
interface Memo
import
    word: Word
export
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    error: Exception                                              (* a capacity below 1 *)
    make: (f equal hash) T(K V)
    makeBounded: (f capacity equal hash) T(K V)                   (* least recently used *)
    makeRecursive: (f: All(self: All(k: K) V k: K) V equal hash) T(K V)
    makeBoundedRecursive: (f capacity equal hash) T(K V)
    apply: (c k) V
    asFunction: (c) All(k: K) V
    memoize: (f equal hash) All(k: K) V                           (* asFunction(make(f equal hash)) *)
    contains: (c k) Bool                                          (* not a use *)
    size: (c) Int
    forget: (c k) Bool
    clear: (c) Ok
    hits: (c) Int
    misses: (c) Int
end
```

`unbounded` keeps a `hashMap.T(K V)`: `apply` looks the key up, and on a miss calls the function with itself as
`self`, inserts the result, and returns it. The insert comes after the call, so a recursive call for the same key may
have inserted the same result first, which the insert overwrites.

`lru` keeps a `linkedHashMap.T(K V)` in the order of use. A hit counts, moves the key to the end, and returns the
value. A miss counts, calls the function, and then, unless a recursive call inserted the key meanwhile, pops the first
entry if the map is at capacity and inserts the key last.

Costs, not measured: a hit is a closure call, the key's hash, and a hash map lookup and its `maybe.T`; bounded, a
second lookup for `moveToEnd` and two or three relinking stores. A miss adds the function and an insert. A
`getAndMoveToEnd` in `linkedHashMap` would save the bounded hit's second lookup, if a measurement shows it matters.

## 5. Left out

- **Expiry by time** (Python's `cachetools.TTLCache`): a clock read per call; a caller can `forget` instead.
- **Weak keys or values:** the collector has no weak references.
- **Thread safety:** Quest has no threads.
- **Several arguments without a tuple,** and a default `equal` and `hash`: Quest has neither variadic functions nor
  type classes; decision 5.
- **Detecting a recursive memoized call for the key in progress** (decision 3): a set of keys in progress per cache,
  paid on every miss, for a mistake the stack overflow already reports.
- **Lazy streams** (OCaml's `Seq`, Haskell's lists): `util/iter` covers walking a sequence as it is produced.
- **An access-ordered linked hash map** (decision 9).

## 6. Known limits

- **`lazy.cycle` is raised from the inner `force`,** so the traceback of an uncaught one shows where the value was
  forced again, which is where the mistake is.
- **A linked hash map's arrays do not shrink** as entries are deleted, until it is empty or cleared; the slots past
  `count` hold live entries' keys and values, so they keep nothing alive that the map does not.

## 7. Found along the way

- **The bootstrap's typechecker crashes on a type named through another module's import.** `hash.word.T` as a
  function's return type raises `AttributeError: 'Scope' object has no attribute 'lookup_module'` in `elaborate_type`
  (`bootstrap/python/quest/typechecker/elaborate_types.py`). The self-hosted compiler reports it as an error,
  "Undefined module/interface 'word' in type path 'hash.word.T'", which the bootstrap should print too. The tests
  import `word` and write `word.T` instead.

## 8. Steps

1. **Check and commit** the three libraries and their tests and goldens (the shared ones from the bootstrap, the
   self-hosted `ir_core` and `ssa` from `--self-hosted --update-golden`). Nothing else imports them, the compiler
   included, so only their three tests can change, and `tools/check`'s self-hosting, unit, and pty suites cannot:
   the tests run alone through each mode `tools/check` would run them in (the bootstrap's phases; the self-hosted
   suite under the collector's checks; the four `run_ir` phases it skips; the backends `ssac`, `arm64`,
   `arm64-program`, `arm64-whole`, `c-whole`, the three wasm modes, as `lib/` is a wasm path, and `jit-files`; and
   the stress tier on `arm64` and `c-whole`). Then push, and cut a release, since a new `lib/` module goes push,
   release, then any compiler use; the compiler uses none of them today.
2. **Document:** libraries.md sections for `util/lazy`, `util/memo`, and `collections/linkedHashMap` (§1.16, §1.17,
   and §2.9), with their interface summaries; take all three out of future-libraries.md; retire this plan into those
   sections.
3. **The bootstrap crash** (§7): an error test of its own, with the self-hosted compiler's message as the expected
   one, and the bootstrap's `elaborate_type` fixed to report it.
