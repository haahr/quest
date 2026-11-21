# Libraries to Consider Building

Libraries the standard library ([libraries.md](libraries.md)) does not have, gathered 2026-11-17, after util/regexp
([regexp.md](regexp.md)). A library written in Quest alone runs alike on every target, the browser included;
one that needs the runtime needs C and a wasm counterpart (marked "runtime" below).

The three this list first called clearly missing have been built and are in [libraries.md](libraries.md): time, as
`os/time` (§4.5) and `util/datetime` (§1.10); ordered collections, as `collections/sortedMap`,
`collections/sortedSet`, `collections/heap`, and `collections/deque` (§2.5–§2.8); and random numbers, as
`util/random` (§1.11). The two written inside the compiler are libraries the compiler is built on: digests, as
`util/digest` (§1.12), and JSON, as `util/json` (§1.13) ([json.md](json.md)). File-system operations are `os/files`
(§4.6), with `glob`. Lazy sequences, which this list called worth having, are `util/iter` (§1.14) and
`util/iterTools` (§1.15) ([iter.md](iter.md)), with iterators for every collection, `regexp.findIter`, and a reader's
lines (`io/lines`, §3.3).

## Worth having, with more design

1. **Unit tests, `util/test`.** The tree tests by goldens. Assertions, named tests, and a report of failures would let
   Quest programs test themselves.
2. **Parsing, `util/peg`.** The compiler's parser runs on a PEG engine of its own (`questlang/`); a general one would
   pair with util/regexp, which matches strings where a grammar parses them.
3. **Persistent collections, `collections/persistent`.** Immutable maps and vectors (hash array mapped tries), which
   suit Quest's functional side and may be shared freely.

## Probably not now

- **Networking and HTTP:** much runtime work, and nothing that would work alike in a browser.
- **Threads and concurrency:** a question for the language, not a library.
- **Unicode:** Quest has no UTF-8.

## Where to start

Every library this list called clearly missing or found written inside the compiler is built; each one left needs
more design first.
