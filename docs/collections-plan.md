# Plan: Ordered Collections, a Deque, and Random Numbers

`collections/sortedMap`, `collections/sortedSet`, `collections/heap`, `collections/deque`, and `util/random`: the
second and third of [future-libraries.md](future-libraries.md)'s "clearly missing" libraries. All are Quest alone,
so they run alike on every target, the browser included. Steps 1 to 3 are built (§5).

## 1. Decisions

1. **Conventions are `collections`' own:** types `T::ALL(K::TYPE) ALL(V::TYPE) TYPE` with type arguments passed
   explicitly, functions `All(...)`, an `error` exception for misuse, `maybe.T` for a result that may be absent and
   `find` raising `error` where one must be present, comparisons that return ~1, 0, or 1 (as `util/sort`'s
   `intCompare` and `stringCompare`, and `sort.reverse` for the other order), and results gathered in a `vector.T`
   (user, 2026-11-18), as `hashMap.keys` and `regexp.findAll` give them.
2. **Mutable,** as `hashMap`, `hashSet`, and `vector` are: operations change the collection in place. A collection
   changed while `forEach` walks it raises `error` at the walk's next step, rather than giving an order that depends on
   the implementation.
3. **`sortedMap` and `sortedSet`** (user, 2026-11-18: both, as `hashMap` and `hashSet`): keys in the order a
   comparison gives, with the least, the greatest, the nearest to a key on either side, and ranges, by callback or as
   a vector (user, 2026-11-18). A B-tree underneath (§3).
4. **`heap` is push and pop** (user, 2026-11-18): no handles, so no decrease-key; a binary heap in a vector, the
   least element by its comparison first. What `questlang/codegen/machine/regalloc.mod.quest` keeps by hand.
5. **`deque`** is a ring buffer: pushes and pops at both ends in constant time, and indexing.
6. **`util/random` is seeded explicitly** (user, 2026-11-18): `new(seed)` gives the same numbers on every target and
   every run, for tests and benchmarks, and `fromClock()` seeds one from `os/time` for programs that want different
   numbers each run. There is no hidden shared generator. The generator is xoshiro256**, seeded by SplitMix64 (§3):
   fast, small, and good for simulation and testing; **not** for cryptography. Its members are not named for the
   modules a program uses beside it (`bits`, `anyInt`, `fraction`, not `word`, `int`, `real`).

## 2. The Interfaces

### 2.1. `collections/sortedMap : collections/SortedMap`

```quest
interface SortedMap
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
export
    (* A map whose keys are in the order its comparison gives *)
    T::ALL(K::TYPE) ALL(V::TYPE) TYPE
    Def Entry = Fun(K::TYPE V::TYPE) Record key: K value: V end

    (* Raised by find of a missing key, and by a walk of a map changed while
     * it is walked *)
    error: Exception

    (* A new empty map, its keys ordered by compare (~1, 0, or 1, as
     * sort.intCompare); keys compare 0 are one key *)
    new: All(K::TYPE V::TYPE) All(compare: All(a: K b: K) Int) T(K V)

    size: All(K::TYPE V::TYPE) All(m: T(K V)) Int
    empty: All(K::TYPE V::TYPE) All(m: T(K V)) Bool
    get: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    contains: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Bool
    find: All(K::TYPE V::TYPE) All(m: T(K V) key: K) V
    (* Sets key's value; whether key is new *)
    insert: All(K::TYPE V::TYPE) All(m: T(K V) key: K value: V) Bool
    (* Takes key out; its value, if it was there *)
    delete: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(V)
    clear: All(K::TYPE V::TYPE) All(m: T(K V)) Ok
    copy: All(K::TYPE V::TYPE) All(m: T(K V)) T(K V)

    (* ---- By order *)

    (* The entries with the least and the greatest keys *)
    least: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    greatest: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    (* The entry with the greatest key at most key, the least at least key,
     * the greatest below key, and the least above it *)
    floor: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    ceiling: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    below: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    above: All(K::TYPE V::TYPE) All(m: T(K V) key: K) maybe.T(Entry(K V))
    (* Takes the least or the greatest entry out, and gives it *)
    removeLeast: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))
    removeGreatest: All(K::TYPE V::TYPE) All(m: T(K V)) maybe.T(Entry(K V))

    (* ---- Walking, in key order *)

    keys: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(K)
    values: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(V)
    entries: All(K::TYPE V::TYPE) All(m: T(K V)) vector.T(Entry(K V))
    forEach: All(K::TYPE V::TYPE) All(m: T(K V) action: All(k: K v: V) Ok) Ok
    (* The entries with keys from lo, included, to hi, excluded *)
    forEachInRange: All(K::TYPE V::TYPE) All(m: T(K V) lo: K hi: K action: All(k: K v: V) Ok) Ok
    entriesInRange: All(K::TYPE V::TYPE) All(m: T(K V) lo: K hi: K) vector.T(Entry(K V))
    (* The number of keys less than key: its position, if it is a key *)
    rank: All(K::TYPE V::TYPE) All(m: T(K V) key: K) Int

    (* A new map with m's comparison, from each key k to f(k v); m is
     * unchanged *)
    map: All(K::TYPE V::TYPE W::TYPE) All(m: T(K V) f: All(k: K v: V) W) T(K W)
    filter: All(K::TYPE V::TYPE) All(m: T(K V) pred: All(k: K v: V) Bool) T(K V)
end
```

### 2.2. `collections/sortedSet : collections/SortedSet`

```quest
interface SortedSet
import
    util/maybe : util/Maybe
    collections/vector : collections/Vector
export
    (* A set whose elements are in the order its comparison gives *)
    T::ALL(A::TYPE) TYPE
    error: Exception

    new: All(A::TYPE) All(compare: All(a: A b: A) Int) T(A)
    size: All(A::TYPE) All(s: T(A)) Int
    empty: All(A::TYPE) All(s: T(A)) Bool
    contains: All(A::TYPE) All(s: T(A) elem: A) Bool
    (* Whether elem was not there before; whether it was *)
    insert: All(A::TYPE) All(s: T(A) elem: A) Bool
    delete: All(A::TYPE) All(s: T(A) elem: A) Bool
    clear: All(A::TYPE) All(s: T(A)) Ok
    copy: All(A::TYPE) All(s: T(A)) T(A)

    least: All(A::TYPE) All(s: T(A)) maybe.T(A)
    greatest: All(A::TYPE) All(s: T(A)) maybe.T(A)
    floor: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    ceiling: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    below: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    above: All(A::TYPE) All(s: T(A) elem: A) maybe.T(A)
    removeLeast: All(A::TYPE) All(s: T(A)) maybe.T(A)
    removeGreatest: All(A::TYPE) All(s: T(A)) maybe.T(A)

    elements: All(A::TYPE) All(s: T(A)) vector.T(A)
    forEach: All(A::TYPE) All(s: T(A) action: All(elem: A) Ok) Ok
    forEachInRange: All(A::TYPE) All(s: T(A) lo: A hi: A action: All(elem: A) Ok) Ok
    elementsInRange: All(A::TYPE) All(s: T(A) lo: A hi: A) vector.T(A)
    rank: All(A::TYPE) All(s: T(A) elem: A) Int

    (* As hashSet's, each a new set with s1's comparison *)
    union: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    intersection: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    difference: All(A::TYPE) All(s1: T(A) s2: T(A)) T(A)
    isSubset: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool
    equal: All(A::TYPE) All(s1: T(A) s2: T(A)) Bool
    filter: All(A::TYPE) All(s: T(A) pred: All(elem: A) Bool) T(A)
end
```

### 2.3. `collections/heap : collections/Heap`

```quest
interface Heap
import
    collections/vector : collections/Vector
export
    (* A priority queue: the least element by its comparison comes out first
     * (sort.reverse of a comparison, for the greatest) *)
    T::ALL(A::TYPE) TYPE

    (* Raised by pop and peek of an empty heap *)
    error: Exception

    new: All(A::TYPE) All(compare: All(a: A b: A) Int) T(A)
    (* A heap of v's elements, made in linear time; v is unchanged *)
    fromVector: All(A::TYPE) All(v: vector.T(A) compare: All(a: A b: A) Int) T(A)

    size: All(A::TYPE) All(h: T(A)) Int
    empty: All(A::TYPE) All(h: T(A)) Bool
    push: All(A::TYPE) All(h: T(A) elem: A) Ok
    (* Takes the least element out, and gives it *)
    pop: All(A::TYPE) All(h: T(A)) A
    (* The least element, left in *)
    peek: All(A::TYPE) All(h: T(A)) A
    (* push then pop, in one step: elem itself if it is least *)
    pushPop: All(A::TYPE) All(h: T(A) elem: A) A
    clear: All(A::TYPE) All(h: T(A)) Ok
    (* The elements, in no particular order; h is unchanged *)
    elements: All(A::TYPE) All(h: T(A)) vector.T(A)
end
```

### 2.4. `collections/deque : collections/Deque`

```quest
interface Deque
import
    collections/vector : collections/Vector
export
    (* A double-ended queue: pushes and pops at both ends in constant time,
     * and its elements indexed from the front *)
    T::ALL(A::TYPE) TYPE

    (* Raised by a pop, front, or back of an empty deque, and an index outside
     * 0 to length - 1 *)
    error: Exception

    new: All(A::TYPE) T(A)
    newWithCapacity: All(A::TYPE) All(capacity: Int) T(A)
    length: All(A::TYPE) All(d: T(A)) Int
    empty: All(A::TYPE) All(d: T(A)) Bool

    pushFront: All(A::TYPE) All(d: T(A) elem: A) Ok
    pushBack: All(A::TYPE) All(d: T(A) elem: A) Ok
    popFront: All(A::TYPE) All(d: T(A)) A
    popBack: All(A::TYPE) All(d: T(A)) A
    front: All(A::TYPE) All(d: T(A)) A
    back: All(A::TYPE) All(d: T(A)) A

    (* Element i, 0 the front *)
    get: All(A::TYPE) All(d: T(A) index: Int) A
    set: All(A::TYPE) All(d: T(A) index: Int value: A) Ok
    clear: All(A::TYPE) All(d: T(A)) Ok
    copy: All(A::TYPE) All(d: T(A)) T(A)

    (* Front to back *)
    forEach: All(A::TYPE) All(d: T(A) action: All(elem: A) Ok) Ok
    toVector: All(A::TYPE) All(d: T(A)) vector.T(A)
    fromVector: All(A::TYPE) All(v: vector.T(A)) T(A)
end
```

### 2.5. `util/random : util/Random`

```quest
interface Random
import
    collections/vector : collections/Vector
    word : Word
export
    (* =========================================================================
     * Pseudo-Random Numbers (Random)
     *
     * A generator, xoshiro256** seeded by SplitMix64: the same numbers from
     * the same seed on every target. Not for cryptography.
     *
     *     let r = random.new(1989)
     *     let die = random.below(r 6) + 1
     *     random.shuffle(:String r names)
     * ====================================================================== *)

    (* A generator, changed by each number it gives *)
    T::TYPE

    (* Raised for a bound of 0 or less, a range whose hi is below its lo, and a
     * choice from an empty array *)
    error: Exception

    (* A generator from seed: the same seed, the same numbers *)
    new(seed: Int): T
    (* A generator seeded from os/time's clocks: different numbers each run *)
    fromClock(): T
    (* A generator that will give the numbers r will give from now; r is
     * unchanged *)
    copy(r: T): T
    (* A new generator, seeded from r's next numbers, independent of r from
     * then on: for a part of a program that needs its own *)
    split(r: T): T

    (* ---- Numbers *)

    (* 64 random bits *)
    bits(r: T): word.T
    (* Any Int, each equally likely *)
    anyInt(r: T): Int
    (* An Int from 0 to n - 1, each equally likely (without bias, by Lemire's
     * method); raises error for n <= 0 *)
    below(r: T n: Int): Int
    (* An Int from lo to hi, both included; raises error for hi < lo *)
    between(r: T lo: Int hi: Int): Int
    (* A Real from 0.0, included, to 1.0, excluded, with 53 random bits *)
    fraction(r: T): Real
    bool(r: T): Bool
    (* A Real from the normal distribution of mean 0 and standard deviation 1
     * (the Box-Muller method) *)
    normal(r: T): Real

    (* ---- Arrays and vectors *)

    (* a's elements in a random order, in place (Fisher-Yates) *)
    shuffle: All(A::TYPE) All(r: T a: Array(A)) Ok
    shuffleVector: All(A::TYPE) All(r: T v: vector.T(A)) Ok
    (* One of a's elements, each equally likely; raises error if a is empty *)
    choice: All(A::TYPE) All(r: T a: Array(A)) A
    (* k of a's elements, none twice, in a random order; raises error unless
     * 0 <= k <= extent a *)
    sample: All(A::TYPE) All(r: T a: Array(A) k: Int) vector.T(A)
end
```

## 3. Implementation

- **`sortedMap` and `sortedSet`** share a B-tree in a module of their own, `collections/btree`, which neither
  interface names: nodes of up to 31 keys in arrays, values beside them in a map's, and each node's count of keys
  below it for `rank`. Logarithmic operations with few allocations and a shallow tree, where a red-black tree would
  make a node for every key. A change count lets `forEach` notice a change made while it walks.
- **`heap`:** a binary heap in a `vector`, element k's children at 2k + 1 and 2k + 2; `fromVector` sifts down from the
  middle (Floyd's method), in linear time.
- **`deque`:** a ring buffer in an array, its capacity doubled when full, a head index, and a length.
- **`util/random`:** four `word.T`s of state; xoshiro256** with `word.rotate`, `word.shift`, `word.xorBits`, and
  `word.mul`; SplitMix64 to expand the seed into the four words (so that seeds near each other give unrelated
  streams); `below` by Lemire's multiply-and-reject with `word.mulHi`; `fraction` from the top 53 bits; `fromClock`
  mixing `os/time`'s `nowInNanoseconds()` and `ticks()` through SplitMix64.

## 4. Tests

- **`util/random`** first, since the others' tests use it: its first numbers from known seeds against the reference
  C implementations of xoshiro256** and SplitMix64 (a unit test computes them in Python), the same numbers on every
  target, `below` and `between` at their edges and without bias (counts over many draws), `shuffle` and `sample` as
  permutations, and the errors.
- **`sortedMap` and `sortedSet`:** long random sequences of operations, from `util/random`, checked at every step
  against a simple model (a sorted vector), so that the B-tree's splits, merges, and rebalancing are all reached; the
  order queries and ranges at and past the ends; and a change during `forEach`.
- **`heap`:** heapsort of random vectors against `util/sort`, with `fromVector` and with pushes, and `pushPop`.
- **`deque`:** random operations against a model, through the buffer's wrapping and growth.
- Each as goldens in every phase of both compilers and the backends' modes, wasm included.

## 5. Steps

1. **`util/random`.**
2. **`heap` and `deque`.**
3. **`sortedMap` and `sortedSet`,** on `collections/btree`.

*Built 2026-11-18:* steps 1 to 3, each with its golden test, passing in every phase of both compilers and in the
arm64, ssac, arm64-whole, JIT, wasm, wasm-node, and wasm-jit modes. `util/random`'s known answers are recomputed by
`tests/python/test_random.py` with a reference implementation; `fromClock` mixes a count of its calls into the
clocks, since two calls can read the same ones. The B-tree's test grows a map to three levels (1,200 keys) and
empties it in a random order, checked against a model at every step; a change of a value during `forEach` is allowed,
an added or removed key raises `error`. libraries.md has §1.11 and §2.5 to §2.8.
4. **libraries.md's sections** for all five, and `regalloc`'s heap moved to `collections/heap` if it measures no
   slower, after a release has the library (docs/release-compiler.md §2).
