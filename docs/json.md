# JSON: `util/json`

`util/json : util/JSON` is Quest's JSON (RFC 8259) library, written in Quest with no externals
(`lib/util/json.{int,mod}.quest`). Its interface and a summary of its rules are in [libraries.md](libraries.md)
§1.13. This document says how it is built, who uses it, why it is the way it is, and what was left out.

It has three kinds of user:
- **Programs,** reading and writing JSON that other programs wrote or will read.
- **The self-hosted compiler,** for:
  - `.qm` manifests and `.qi` interfaces (dynamic-format documents, [dynamic.md](dynamic.md) §3.4);
  - the build workers' messages;
  - the ABI check's reads of artifacts;
  - the Jupyter kernel's protocol;
  - the IR printer's quoting.

  These used `questlang/common/json`, which became `util/json` and is gone.
- **The self-hosted interpreter's `dynamic.extern` and `dynamic.intern`,** for the text layer of the dynamic format.
  Compiled code's runtimes keep their own JSON (§4).

## 1. Rules

1. **A document is a `Value` tree.** `parse`, `parseWith`, and `read` make one; `dump`, `dumpWith`, and `write`
   print one. An `Emitter` also writes a value to a writer as its parts are given, with no tree, exactly as `write`
   would print it, empty arrays and objects as `[]` and `{}` included. `read` takes exactly one value from a
   `reader.T`, so a reader may hold several documents in a row; a number, `true`, `false`, or `null` at the top
   level is read one character past its end, as a reader can't put a character back.
2. **A number keeps its text.** `jNumber` holds the number as written, and whether it is an integer (no fraction and
   no exponent). Every integer reads exactly, which the dynamic format needs: a `word.T` can exceed an `Int`
   ([dynamic.md](dynamic.md) §2.4). `toInt`, `toWord`, and `toReal` convert, and raise `error` when the value doesn't
   fit. `equal` compares numbers by value, so `1.0` equals `1`.
3. **Output is deterministic and matches Python's `json.dumps`** for the same value read as Latin-1:
   - compact output uses separators `,` and `:`, as the dynamic format requires;
   - indented output matches `indent=n`, which is how `.qm` files are written;
   - members come out in the order they were first put;
   - a real is written as Python's `repr` writes it.

   So the compiler's artifacts didn't change when it moved onto the library, and the bootstrap, which uses Python's
   `json`, writes the same bytes as the self-hosted compiler.
4. **Parsing is strict.** It rejects comments, trailing commas, single quotes, `NaN` and the infinities, leading
   zeros, and anything but whitespace after the value. A repeated member name keeps its last value in its first
   place, as Python's does, unless the options are `parsingDynamic` (`unique`), which refuses it, as the dynamic
   format requires ([dynamic.md](dynamic.md) §2.1).
5. **Strings are bytes, and by default a byte is the code point of the same number** (Latin-1). A byte that isn't
   printable ASCII (a control character, DEL, or a byte above 127) is written as `\u00XX`, and an escape above `ÿ` is
   an error. Every Quest string round-trips exactly. In this default mode, for JSON from elsewhere, which is almost
   always UTF-8:
   - raw bytes above 127 are read unchanged;
   - an escape such as `é` is read as the one byte E9, not the bytes C3 A9, and `中` is an error;
   - bytes above 127 are written as escapes, so a reader that isn't Quest sees each byte of a UTF-8 sequence as a
     character of its own.

   **The UTF-8 mode** (user, 2026-11-23, which lifted "no UTF-8 mode" of 2026-11-18 for an opt-in mode only) is for
   JSON exchanged with programs that aren't Quest, such as an editor talking to the language server
   ([lsp.md](lsp.md)). It is the `utf8` field of `ParseOptions` and `PrintOptions` (`parsingUtf8`,
   `compactUtf8`):
   - an escape gives its code point's UTF-8 encoding; a high surrogate's escape must be followed by a low one's, the
     two giving the pair's code point, and a surrogate's escape without its partner is an error, though Python
     accepts it;
   - raw bytes are read unchanged, and are not checked;
   - output is what `json.dumps(ensure_ascii=False)` writes, encoded as UTF-8: only control characters, `"` and `\`
     are escaped, a well-formed UTF-8 sequence is written as it is, and each maximal subpart of an ill-formed one
     (Unicode's rule for U+FFFD substitution, which Python's `errors="replace"` follows) as U+FFFD. The text is then
     always UTF-8, but a string that wasn't doesn't round-trip.

   `tests/python/test_json.py` checks the mode against Python reading the text as UTF-8 with `errors="replace"`.
6. **`Object` is manifest, though callers should treat it as abstract.** Its operations are `newObject`, `put`,
   `get`, `remove`, `names`, `size`, and `forEach`. It would be abstract, but an interface's manifest type can't
   name an abstract type of the same interface: a module is checked against its interface by comparing each manifest
   type's two definitions as they are (the bootstrap's `elaboration.py` and the self-hosted compiler's conformance
   check), so the recursive `Value`, whose `jObject` holds an `Object`, couldn't be manifest while `Object` was
   abstract. Lifting that would change both compilers' module checking.
7. **Errors carry a message and an offset.** `error: Exception(Failure)`, where a `Failure` gives the byte offset in
   the text, or `~1` for an error that isn't about text: a value of the wrong kind, a number that doesn't fit, or an
   emitter's parts out of order.
8. **The library doesn't cache parsed documents.** A tree is mutable, so a library that shared trees between callers
   would let one caller's change reach another's. The compiler, which knows nothing changes its artifacts' trees,
   caches them in `questlang/common/jsonCache` (§3).

## 2. Implementation

The parser and printer came from `questlang/common/json`.
- **Parsing** is a scanner over the text that tracks its position, which is the `Failure` offset. `read` collects
  one value's text from the reader a character at a time, counting brackets outside strings, and then parses it.
- **Printing** builds the text in a string builder. `write` prints the whole value and then writes it.
- **Reals** are written by `conv.real`, which already writes a real as `repr` does but for its `~` minus, which
  `real` changes, and its `inf`, which `real` refuses.
- **The emitter** keeps a stack of frames, one per open array or object, with its element count and, for an
  object, whether a name waits for its value. It writes to the writer in pieces of 64 KB. Nothing in the tree uses
  it yet (§5).

### 2.1. Objects

An object is a tuple of two arrays, names and values, in insertion order; a count of the slots in use; and a
`hashMap` from name to position, which is used only past 8 members (`smallSize`). Below that size, a lookup is a
linear scan that checks lengths before comparing bytes, which for the small objects most documents are made of (a
`.qi` file's type nodes have one or two members) is quicker than hashing and needs no table.

Every object starts from shared arrays and an index that are never written (`noNames`, `noValues`, `noIndex`). Its
first `put` replaces the arrays with ones of capacity 2, which double as they fill, and growing past 8 members
makes it a new index of its own.

This replaced a tuple, a vector, and a hash map per object. It saved nothing measurable ([benchmarks.md](benchmarks.md)
§29): a driver build's allocation stayed at 51 GB, of which JSON is too small a part to show, and its user time is 2
to 3% higher, near noise. As first written, each object's own empty arrays and table left 3.1M more objects live
and the heap 10% larger; the shared empties cut that to 0.4M and 3%.

## 3. The Compiler

- Every user imports `util/json`. `manifest.mod.quest` and `dynamicreader.mod.quest` read trees with the library's
  accessors (`toInt`, `member`, `optional`, and the rest) in place of their own.
- `questlang/common/jsonCache.parseShared` parses each artifact's text once per build and shares the tree, which
  callers must not change.
- Manifests are written with `dumpWith(... indented(2))`.

The move left artifacts and the ABI unchanged: the fixed point and the ABI corpus (`tests/abi/corpus*/`) came out
byte-identical.

## 4. The Dynamic Format

Each implementation of `dynamic.extern` and `dynamic.intern` has its own JSON layer:

| Implementation | JSON |
|---|---|
| The bootstrap | Python's `json`, the reference that rule 3 matches |
| The self-hosted interpreter | `util/json` |
| Compiled code on C, ssac, arm64, and the JIT | `runtime/quest_serialization.c`'s own writer and parser |
| WebAssembly | `runtime/wasm/dynamic`'s own, in Quest |

- **The self-hosted interpreter.** `dynamic.intern` reads with `json.read(rd parsingDynamic)`, and
  `dynamicReader.decodeDocument` takes the parsed tree. `dynamicWriter` builds a tree and prints it, rather than
  writing through an emitter. A `.qi` file is written atomically from its whole text (`files.writeAtomically`), and
  extern makes the whole text before it writes any, so that a value it can't extern leaves nothing half-written.
- **Compiled code** keeps its C, and WebAssembly its Quest port of that C (user, 2026-11-18). Both walk type
  descriptors, which Quest code can't see. Both follow rules 3 to 5, with `unique`.

Moving compiled code's serializer into Quest, over `util/json`, is a possibility for later:
[dynamic-in-quest.md](dynamic-in-quest.md).

## 5. Tests

- **`tests/source/stdlib/json_values.quest`:** construction, the accessors, `equal`, and the emitter, each against
  `dumpWith`.
- **`tests/python/test_json.py`:** the library against Python's `json`, reading and writing text as Latin-1. It
  makes a file of cases, answered by Python, and `tests/json/corpus.quest` checks them:
  - texts to accept or reject, in the manner of JSONTestSuite, with and without `unique`, each accepted one
    printed compact and indented by 2;
  - random documents, printed by Python in either form or with random whitespace, which the library must print
    back as Python does;
  - reals written as `repr` writes them, and integers at an `Int`'s ends.

  This is the reference for rule 3.
- **`tests/source/stdlib/json_dynamic.quest`:** conformance of the dynamic format. It externs the same values in
  every implementation of §4 and checks that they write the same text and accept and reject the same texts.

The conformance test found two bugs, both fixed:
- the C runtime and WebAssembly wrote DEL (byte 127) as itself, where Python, and so the interpreters, write
  `\u007f`;
- WebAssembly's check that two types' proxies agree (`proxiesAgreeIn` in `runtime/wasm/core`) kept no trail of the
  pairs in progress, as the C runtime's does, so a type that refers to itself twice, such as a binary tree, took
  exponential time and hung.

## 6. Left Out

- **A pull parser** (a stream of events in place of a tree), for documents too large for a tree. No user has one;
  it can be added beside `read` without changing the tree.
- **The emitter in the compiler.** It was designed for large documents, `.qi` files and externed values, but both
  are made whole before they are written (§4), so nothing uses it.
- **Mapping JSON straight to Quest values by type,** as serde does. That is what `dynamic` does for its own format;
  for arbitrary JSON, the accessors cover reading and the emitter covers writing.
- **Immutable trees,** which would let the library cache parses safely. Programs build trees by `put`, and the
  compiler's cache is the one cache anything needs.
- **UTF-8** (rule 5).
