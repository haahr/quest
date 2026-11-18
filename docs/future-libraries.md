# Libraries to Consider Building

Libraries the standard library ([libraries.md](libraries.md)) does not have, gathered 2026-11-17, after util/regexp
([regexp-plan.md](regexp-plan.md)), none of them then planned or started. A library written in Quest alone runs alike
on every target, the browser included; one that needs the runtime needs C and a wasm counterpart (marked "runtime"
below).

## Clearly missing

1. **Time, `os/time`** (runtime). *Built 2026-11-18, as `os/time` and `util/datetime`
   ([time-plan.md](time-plan.md)).* Quest has no clock: util/regexp's benchmark times whole processes from Python for
   lack of one. A monotonic clock, the wall clock, sleep, and dates formatted and parsed.
2. **Ordered collections, `collections/sortedMap` and `collections/heap`.** *Built 2026-11-18, with
   `collections/sortedSet` and `collections/deque` ([collections-plan.md](collections-plan.md)).* No sorted map or set
   (iteration in order, range queries, the least and greatest keys), and no priority queue: a balanced tree
   (red-black, or a B-tree) and a binary heap, in Quest. A deque belongs here too.
3. **Random numbers, `util/random`.** *Built 2026-11-18 ([collections-plan.md](collections-plan.md)).* No generator:
   a seeded, deterministic one (PCG or xoshiro), in Quest, with integers in a range, reals, and shuffling. For tests
   and benchmarks; util/regexp's benchmark generates its inputs in Python for lack of one.

## Written already, inside the compiler

4. **JSON, `util/json`.** `questlang/common/json` parses and prints JSON for the compiler, and `dynamic` has JSON only
   for its own values. A general library is mostly its interface reshaped, and tests.
5. **Digests, `util/digest`.** `questlang/common/sha256` exists: SHA-256, and CRC-32 or FNV, as a library.

## Worth having, with more design

6. **Unit tests, `util/test`.** The tree tests by goldens. Assertions, named tests, and a report of failures would let
   Quest programs test themselves.
7. **File-system operations, `os/fs`** (runtime). Copying, renaming, removing a tree, walking a directory, and
   temporary files and directories; `tests/source/stdlib/os_process.quest` calls `mktemp` through a shell for lack
   of them. Under wasm, what WASI gives.
8. **Parsing, `util/peg`.** The compiler's parser runs on a PEG engine of its own (`questlang/`); a general one would
   pair with util/regexp, which matches strings where a grammar parses them.
9. **Lazy sequences, `util/iter`.** Streams (ranges, map, filter, take) that walk collections and
   `regexp.findAll`'s matches without making vectors: closures, and no change to the language.
10. **Persistent collections, `collections/persistent`.** Immutable maps and vectors (hash array mapped tries), which
    suit Quest's functional side and may be shared freely.

## Probably not now

- **Networking and HTTP:** much runtime work, and nothing that would work alike in a browser.
- **Threads and concurrency:** a question for the language, not a library.
- **Unicode:** Quest has no UTF-8.

## Where to start

Time, ordered collections, and random numbers: each fills a gap the tree has already met, and two of the three are
Quest alone.
