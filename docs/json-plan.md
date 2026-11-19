# Plan: A JSON Library, `util/json`

One JSON library, `util/json : util/Json`, written in Quest with no externals, for three kinds of user:

- **Programs:** reading and writing JSON that other programs wrote or will read.
- **The compiler:** `.qm` manifests, `.qi` interfaces (dynamic-format documents, [dynamic.md](dynamic.md) §3.4), the
  build workers' messages, the ABI check's reads of artifacts, the Jupyter kernel's protocol, and the IR printer's
  quoting. All of these use `questlang/common/json` today; that module becomes `util/json` and goes away.
- **`dynamic.extern` and `dynamic.intern`:** the text layer of the dynamic format, in the interpreters that run
  Quest code. Compiled code's runtime keeps its own C (§1, decision 8), held to the same text by tests.

Not started. The interface in §2 is the design; §3 says how it is built, and §5 lists the steps.

## 1. Decisions

1. **A tree, with a streaming writer and a one-value reader.** A parsed document is a `Value` tree, as now. Output
   can also go straight to a `writer.T` through an `Emitter` (§2.5), with no tree in between, for large documents
   such as `.qi` files and externed values. `read` takes exactly one value from a `reader.T` (§2.3), which is what
   `dynamic.intern` needs: a reader may hold several documents in a row. A pull parser (events in place of a tree)
   is left out until a user needs one (§4).
2. **A number keeps its text.** `jNumber` holds the number as written, and whether it is an integer, as
   `questlang/common/json` does. That way every integer reads exactly: a `word.T` can exceed an `Int`, and the
   dynamic format needs 64-bit integers exactly ([dynamic.md](dynamic.md) §2.4). `toInt`, `toWord`, and `toReal`
   convert, and raise `error` when the value doesn't fit.
3. **Output is deterministic and matches Python's `json.dumps`:**
   - Compact output uses separators `,` and `:`, as the dynamic format requires.
   - Indented output matches `indent=n`, which is how `.qm` files are written.
   - Members come out in the order they were first put.
   - A real is written as Python's `repr` writes it.

   This keeps every artifact the compiler writes byte-identical across the move. It also keeps the bootstrap, which
   uses Python's `json`, writing the same bytes as the self-hosted compiler.
4. **Parsing is strict RFC 8259.** It rejects comments, trailing commas, single quotes, `NaN` and the infinities,
   leading zeros, and anything but whitespace after the value. A repeated member name keeps its last value, as
   Python does, unless the options ask for `unique`, which rejects it. The dynamic format requires `unique`
   ([dynamic.md](dynamic.md) §2.1).
5. **Strings are bytes, and a byte is the code point of the same number** (Latin-1). Bytes above 127 and control
   characters are written as `\u00XX`, and an escape above `\u00FF` is an error. Every Quest string round-trips
   exactly, and the text is what Python writes for a string decoded as Latin-1, which is how the bootstrap reads and
   writes its documents. There is no UTF-8 mode (user, 2026-11-18), as Quest has no UTF-8 (regexp-plan.md decision
   4). So for JSON from elsewhere, which is almost always UTF-8:
   - Raw bytes above 127 are read unchanged.
   - An escape such as `\u00e9` is read as the one byte E9, not the bytes C3 A9, and `\u4e2d` is an error.
   - Bytes above 127 are written as escapes, so a reader that isn't Quest sees each byte of a UTF-8 sequence as a
     character of its own.
6. **`Object` is abstract.** Its operations are `newObject`, `put`, `get`, `remove`, `names`, `size`, and
   `forEach`, so its representation can change without touching callers. That matters for speed: a `.qi` file is
   thousands of small objects, and §3.2 makes a small object two short arrays instead of a vector and a hash map.
7. **Errors carry a message and an offset.** `error: Exception(Failure)`, where a failure gives the byte offset in
   the text (or `~1` for an error that isn't about text, such as a wrong kind or a number that doesn't fit). The
   compiler's three handlers (`when json.error then`) keep working unchanged, since they don't bind the payload.
8. **Compiled code's `dynamic.extern` and `dynamic.intern` stay in C** (`runtime/quest_serialization.c`). They walk
   type descriptors, which Quest code cannot see, so the C's own JSON writer and parser stay. Instead:
   - The C follows §1's rules, with `unique`.
   - A conformance test (§4) makes compiled code's extern text byte-identical to `util/json`'s compact dump of the
     same document, and makes intern accept and reject the same texts.

   Moving extern and intern into Quest, over a reflection interface to descriptors, is in §4's alternatives.
9. **Caching parsed documents stays in the compiler.** `parseShared` reuses one tree for every parse of the same
   text, for the build's artifacts. A tree is mutable, so a library that shared trees between callers would let one
   caller's change reach another's. The cache moves to `questlang/common/jsonCache`.

## 2. The Interface

```quest
(* JSON: RFC 8259 text, parsed into Value trees and printed from them, or
 * written straight to a writer by an Emitter. A string is bytes, each the
 * code point of the same number (Latin-1). Output is deterministic: compact or
 * indented, members in the order first put, reals as Python's repr writes
 * them. *)

interface Json
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
    word : Word
    reader : Reader
    writer : Writer
export
```

### 2.1. Values

```quest
    (* An object: members in the order first put, at most one per name *)
    Object::TYPE

    Def Rec Value = Option
        jNull
        jBool with b: Bool end
        (* A number as written: an integer if it has neither a fraction nor
         * an exponent *)
        jNumber with text: String isInteger: Bool end
        jString with s: String end
        jArray with items: vector.T(Value) end
        jObject with o: Object end
    end

    null: Value
    bool(b: Bool): Value
    int(n: Int): Value
    (* The unsigned integer w *)
    word(w: word.T): Value
    (* r as Python's repr writes it; raises error if r is not finite *)
    real(r: Real): Value
    (* A number given as its text; raises error unless it is a JSON number *)
    number(text: String): Value
    string(s: String): Value
    arrayValue(items: vector.T(Value)): Value
    object(o: Object): Value

    newObject(): Object
    (* Sets a member: a new name at the end, an existing one in place *)
    put(o: Object name: String v: Value): Ok
    get(o: Object name: String): maybe.T(Value)
    (* Removes a member, giving its value if it had one *)
    remove(o: Object name: String): maybe.T(Value)
    names(o: Object): Array(String)
    size(o: Object): Int
    forEach(o: Object action: All(name: String v: Value) Ok): Ok

    (* Structural equality: numbers by value (1.0 is 1), objects by their
     * members whatever the order *)
    equal(a: Value b: Value): Bool
```

The array constructor keeps its current name, `arrayValue`, since `array` is a keyword
([grammar.txt](grammar.txt)).

### 2.2. Options

```quest
    Def ParseOptions = Record
        (* Whether a repeated member name is an error, rather than its last
         * value winning *)
        unique: Bool
    end
    (* Not unique *)
    parsing: ParseOptions
    (* Unique: the dynamic format's *)
    parsingDynamic: ParseOptions

    Def PrintOptions = Record
        (* 0 for compact text (separators "," and ":"), else spaces a
         * level, each element and member on a line of its own, as Python's
         * json.dumps(indent=n) writes them *)
        indent: Int
    end
    compact: PrintOptions
    indented(n: Int): PrintOptions
```

`parse` and `dump` use `parsing` and `compact`, so they behave exactly as `questlang/common/json` does now.

### 2.3. Parsing and Printing

```quest
    Def Failure = Tuple message: String offset: Int end
    (* Raised on text that is not JSON, a value of the wrong kind, or a
     * number that does not fit *)
    error: Exception(Failure)

    (* One value, the whole text but whitespace *)
    parse(text: String): Value
    parseWith(text: String options: ParseOptions): Value
    (* One value from rd, read to its end and no further, but for a number,
     * true, false, or null at the top level, after which one more character
     * is read (a reader cannot put one back); raises error at end of
     * stream *)
    read(rd: reader.T options: ParseOptions): Value

    dump(v: Value): String
    dumpWith(v: Value options: PrintOptions): String
    write(wr: writer.T v: Value options: PrintOptions): Ok
```

`read` replaces the interpreter's `readDocument` ([builtins.mod.quest](../questlang/interpreter/builtins.mod.quest)),
which today scans one document's text and then parses it a second time.

### 2.4. Reading a Tree

Every program reading JSON writes the same checks over and over: `manifest.stringMember`, `dynamicReader.integer`,
and a dozen `case v when jObject with x then ...` blocks. The library has them once, each raising `error` when the
value is not of the kind asked for:

```quest
    toBool(v: Value): Bool
    (* Raises error unless v is an integer that fits *)
    toInt(v: Value): Int
    toWord(v: Value): word.T
    (* Any number, rounded to the nearest real *)
    toReal(v: Value): Real
    toString(v: Value): String
    toArray(v: Value): vector.T(Value)
    toObject(v: Value): Object
    (* v's member name, raising error if v is not an object or has none *)
    member(v: Value name: String): Value
    (* v's member name if v is an object that has one *)
    optional(v: Value name: String): maybe.T(Value)
```

### 2.5. Writing a Stream

```quest
    (* Writes one value to a writer as its parts are given; raises error on
     * parts out of order (a name outside an object, a value where a name
     * belongs, an end without a beginning, or finish before the value is
     * complete) *)
    Emitter::TYPE
    emitter(wr: writer.T options: PrintOptions): Emitter
    beginObject(e: Emitter): Ok
    (* The next member's name, in an object *)
    name(e: Emitter n: String): Ok
    endObject(e: Emitter): Ok
    beginArray(e: Emitter): Ok
    endArray(e: Emitter): Ok
    (* A whole value, as an element or a member's value *)
    value(e: Emitter v: Value): Ok
    nullValue(e: Emitter): Ok
    boolValue(e: Emitter b: Bool): Ok
    intValue(e: Emitter n: Int): Ok
    wordValue(e: Emitter w: word.T): Ok
    realValue(e: Emitter r: Real): Ok
    stringValue(e: Emitter s: String): Ok
    (* Raises error unless one whole value has been written *)
    finish(e: Emitter): Ok
end
```

The emitter writes exactly what `write` would write for the same tree, indented output included. An empty array
or object is written as `[]` or `{}`, as Python writes them, so the emitter holds back an opening bracket until it
sees the first element or the end.

## 3. Implementation

### 3.1. From `questlang/common/json`

The parser, the printer, and Python's `repr` for reals (`questlang/common/pyRepr`, which moves to the library as a
private module, `util/pyRepr`) are reused. New work:
- the options;
- `read`;
- the accessors and the emitter;
- the small object (§3.2);
- `Failure` offsets: the parser already tracks its position, so it only has to report it.

### 3.2. Objects

An object holds two arrays, names and values, in insertion order, with a `hashMap` index added only past eight
members. Lookups below that size are a linear scan with a length check before comparing bytes. This replaces a
tuple, a vector, and a hash map per object, even for a type node with one member. The measure is a driver build's
allocation and time, taken as [benchmarks.md](benchmarks.md) §28.3 took them, since the build reads every `.qi`
and `.qm` file.

### 3.3. The Compiler

- Every import of `questlang/common/json` becomes an import of `util/json`.
- `parseShared` moves to `questlang/common/jsonCache`.
- `manifest.mod.quest`'s and `dynamicreader.mod.quest`'s hand-written accessors give way to §2.4's.

Neither artifacts nor ABI change: the fixed point and the ABI corpus (`tests/abi/corpus*/`) must come out
byte-identical, with no `corpus.py --update`.

### 3.4. Dynamic

- **The self-hosted interpreter.** `dynamicWriter` and `dynamicReader` change in two ways. They write through an
  emitter instead of building a tree and dumping it, which takes the extern of a large value from three copies of
  it (value, tree, text) to one. And they read with `read(rd parsingDynamic)`.
- **The bootstrap** keeps Python's `json`, which is the reference that §1, decision 3, matches.
- **Compiled code** keeps its C (decision 8).
- **WebAssembly** has no `dynamic` ([wasm.md](wasm.md)), so nothing changes there. The library itself runs on
  WebAssembly like any Quest code.

## 4. Tests and Alternatives

Tests:
- **`tests/source/stdlib/json_values.quest`:** construction, accessors, `equal`, and the emitter, each against
  `dumpWith`.
- **`tests/source/stdlib/json_parse.quest`:** a corpus of accepted and rejected texts, in the manner of
  JSONTestSuite, with and without `unique`. Every rejection reports its offset.
- **`tests/python/test_json.py`:** the corpus against Python's `json`, decoding as Latin-1 and
  printing with `separators` and `indent`. This is the reference for decision 3.
- **Dynamic conformance:** externing the same values in compiled code and in the self-hosted interpreter gives the
  same bytes. These values are the existing dynamic goldens, plus `.qi` files read back and written again.

Alternatives not chosen:
- **A pull parser** (a stream of events), for documents too large for a tree. No current user has one. It can be
  added behind §2.3 without changing the tree.
- **Mapping JSON straight to Quest values by type,** as serde does. That is what `dynamic` does for its own format.
  For arbitrary JSON, the accessors cover reading and the emitter covers writing.
- **Compiled `dynamic` in Quest.** This needs a Quest interface to type descriptors, which the runtime has no
  reason to expose otherwise. The C is written and tested, and a conformance test keeps it honest.
- **Immutable trees,** which would let the library cache parses safely. But programs build trees by `put`, and the
  compiler's cache is the one cache anything needs.

## 5. Steps

1. **The library and its tests:** `lib/util/json.{int,mod}.quest`, `util/pyRepr`, and §4's tests, with no user
   yet. Additive library code, so the targeted checks suffice.
2. **The compiler on the library:** delete `questlang/common/json`, add `jsonCache`, rewrite the accessors. Check
   that artifacts come out byte-identical (the fixed point and the ABI corpus), and measure the build (§3.2).
3. **Dynamic on the library,** in the self-hosted interpreter (emitter and `read`), with the conformance test.
4. **Docs:** a `util/json` section in [libraries.md](libraries.md), [dynamic.md](dynamic.md) §3 pointing at it, and
   JSON removed from [future-libraries.md](future-libraries.md).
