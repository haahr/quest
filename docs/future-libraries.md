# Libraries to Consider Building

Libraries the standard library ([libraries.md](libraries.md)) does not have, gathered 2026-11-17, after util/regexp
([regexp-plan.md](regexp-plan.md)). A library written in Quest alone runs alike on every target, the browser included;
one that needs the runtime needs C and a wasm counterpart (marked "runtime" below).

The three this list first called clearly missing have been built and are in [libraries.md](libraries.md): time, as
`os/time` (§4.5) and `util/datetime` (§1.10) ([time-plan.md](time-plan.md)); ordered collections, as
`collections/sortedMap`, `collections/sortedSet`, `collections/heap`, and `collections/deque` (§2.5–§2.8); and random
numbers, as `util/random` (§1.11) ([collections-plan.md](collections-plan.md)). Digests, the second written
inside the compiler, are `util/digest` (§1.12), and the compiler's SHA-256 is built on it. File-system operations
are `os/files` (§4.6), with `glob` ([files-plan.md](files-plan.md)).

## Written already, inside the compiler

1. **JSON, `util/json`.** `questlang/common/json` parses and prints JSON for the compiler, and `dynamic` has JSON only
   for its own values. A general library is mostly its interface reshaped, and tests.

## Worth having, with more design

2. **Unit tests, `util/test`.** The tree tests by goldens. Assertions, named tests, and a report of failures would let
   Quest programs test themselves.
3. **Parsing, `util/peg`.** The compiler's parser runs on a PEG engine of its own (`questlang/`); a general one would
   pair with util/regexp, which matches strings where a grammar parses them.
4. **Lazy sequences, `util/iter`.** Streams (ranges, map, filter, take) that walk collections and
   `regexp.findAll`'s matches without making vectors: closures, and no change to the language.
5. **Persistent collections, `collections/persistent`.** Immutable maps and vectors (hash array mapped tries), which
   suit Quest's functional side and may be shared freely.

## Probably not now

- **Networking and HTTP:** much runtime work, and nothing that would work alike in a browser.
- **Threads and concurrency:** a question for the language, not a library.
- **Unicode:** Quest has no UTF-8.

## Where to start

JSON: the code exists inside the compiler, so it is mostly an interface and tests, and it is Quest alone.
