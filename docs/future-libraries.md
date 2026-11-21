# Libraries to Consider Building

Libraries the standard library ([libraries.md](libraries.md)) does not have, gathered 2026-11-17, after util/regexp
([regexp.md](regexp.md)), and added to 2026-11-20 from Python's, Go's, Rust's, and OCaml's standard libraries. A
library written in Quest alone runs alike on every target, the browser included; one that needs the runtime needs C
and a wasm counterpart (marked "runtime" below).

## Text

- **Formatting, `util/format`** (Python's `str.format`, Go's `fmt`, Rust's `format!`). `conv` and `strutil` turn
  values into strings, but nothing pads, aligns, or sets a width or precision, which tables, reports, and benchmark
  output need. Padding and width/precision functions may be enough, without a format-string language.
- **Layout, `util/text`** (Python's `textwrap`). Wrap to a width, indent, and dedent.
- **Pretty printing, `util/pretty`** (OCaml's `Format`, Wadler's "prettier printer"). Layout that fits a width, for
  printing trees, IR, or JSON.
- **Diffs, `util/diff`** (Python's `difflib`). Longest-common-subsequence diffs of sequences of lines; a failed
  golden comparison in `util/test` would want one.

## Data formats and encodings

- **Encodings, `util/encoding`** (Go's `encoding/base64` and `encoding/hex`, Python's `base64`). Hex and base64,
  encoded and decoded. `io/display` base64-encodes images inside itself, and `util/digest`'s digests are printed in
  hex.
- **Binary packing, `util/bytes`** (Python's `struct`, Go's `encoding/binary`). Little- and big-endian integers and
  reals read from and written to strings at an offset. Quest's strings are bytes, so this is what reading or writing
  a file format needs.
- **CSV, `util/csv`** (Python's `csv`, Go's `encoding/csv`). A reader with quoting, as an iterator of records over
  `io/lines`, and a writer.
- **Compression, `util/deflate`** (Go's `compress/flate`, zlib). Possible in Quest alone, but sizable; for reading
  `.gz` and zip files, which nothing asks for yet.

## Parsing

- **`util/peg`.** The compiler's parser runs on a PEG engine of its own (`questlang/`); a general one would pair with
  util/regexp, which matches strings where a grammar parses them. Needs more design.

## Numbers

- **Decimal arithmetic, `util/decimal`** (Python's `decimal`). Fixed and floating decimal numbers with a chosen
  precision and rounding, over `util/bignum`; larger than `util/rational` (libraries.md §1.18), which is exact.

## Collections

- **Persistent collections, `collections/persistent`.** Immutable maps and vectors (hash array mapped tries), which
  suit Quest's functional side and may be shared freely. Needs more design.

## Testing and diagnostics

- **Unit tests, `util/test`.** The tree tests by goldens. Assertions, named tests, and a report of failures would let
  Quest programs test themselves. Needs more design.
- **Property-based testing** (Haskell's QuickCheck, Python's Hypothesis). Random inputs and shrinking, on
  `util/random`; after `util/test`.
- **Logging, `util/log`** (Go's `log/slog`, Python's `logging`). Levels and a prefix, written to `writer.err`.

## Probably not now

- **Networking and HTTP:** much runtime work, and nothing that would work alike in a browser.
- **Threads and concurrency:** a question for the language, not a library.
- **Unicode:** Quest has no UTF-8; it would touch the runtime and `conv`, not only a library.
