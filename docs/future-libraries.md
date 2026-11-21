# Libraries to Consider Building

Libraries the standard library ([libraries.md](libraries.md)) does not have, gathered 2026-11-17, after util/regexp
([regexp.md](regexp.md)). A library written in Quest alone runs alike on every target, the browser included;
one that needs the runtime needs C and a wasm counterpart (marked "runtime" below).

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
