# Plan: A JSON Library, `util/json`

One JSON library, `util/json : util/Json`, written in Quest with no externals, for three kinds of user:

- **Programs:** reading and writing JSON that other programs wrote or will read.
- **The compiler:** `.qm` manifests, `.qi` interfaces (dynamic-format documents, [dynamic.md](dynamic.md) §3.4), the
  build workers' messages, the ABI check's reads of artifacts, the Jupyter kernel's protocol, and the IR printer's
  quoting. All of these use `questlang/common/json` today; that module becomes `util/json` and goes away.
- **`dynamic.extern` and `dynamic.intern`:** the text layer of the dynamic format, in the interpreters that run
  Quest code. Compiled code's runtime keeps its own C (§1, decision 8), held to the same text by tests.

Built, 2026-11-18 (§5). §2 is the interface as designed (`lib/util/json.int.quest` has it as built), §3 how it is
built, and §5 the steps and where they departed from the design. §6 is a possibility for later, not part of the plan.

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
6. **`Object` was to be abstract, and is manifest.** Its operations are `newObject`, `put`, `get`, `remove`,
   `names`, `size`, and `forEach`, and callers are to use them alone. But an interface's manifest type cannot name
   an abstract type of the same interface: a module is checked against its interface by comparing each manifest
   type's two definitions as they are, the module's `Object` against the interface's opaque one (`elaboration.py`'s
   conformance check, and the self-hosted compiler's), so the recursive `Value`, whose `jObject` holds an `Object`,
   cannot be manifest while `Object` is abstract. Lifting that would change both compilers' module checking and how a
   value is held across the abstraction. So `Object` is a manifest tuple, its fields documented as the
   implementation's (§3.2).
7. **Errors carry a message and an offset.** `error: Exception(Failure)`, where a failure gives the byte offset in
   the text (or `~1` for an error that isn't about text, such as a wrong kind or a number that doesn't fit). The
   compiler's three handlers (`when json.error then`) keep working unchanged, since they don't bind the payload.
8. **Compiled code's `dynamic.extern` and `dynamic.intern` stay in their runtimes** (`runtime/quest_serialization.c`,
   and `runtime/wasm/dynamic` on WebAssembly; user, 2026-11-18). The C walks type descriptors, which Quest code
   cannot see, and both keep their own JSON writers and parsers. Instead:
   - Both follow §1's rules, with `unique`.
   - A conformance test (§4) makes compiled code's extern text byte-identical to `util/json`'s compact dump of the
     same document, and makes intern accept and reject the same texts.

   Moving them into Quest later, over a reflection interface that WebAssembly's serializer already nearly has, is
   §6. Nothing in this plan stands in its way.
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

The parser and the printer are reused. Python's `repr` for reals needed no module of its own: `conv.real` already
writes a real as `repr` does but for its `~` minus and its `inf`, so `real` replaces the one and refuses the other.
New work:
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

- **The self-hosted interpreter.** `dynamic.intern` reads with `read(rd parsingDynamic)`, in place of the
  interpreter's own scan of one document's text (`readDocument`, gone), and `dynamicReader.decodeDocument` takes the
  parsed document. `dynamicWriter` still builds a tree and prints it, rather than writing through an emitter as the
  design had it: a `.qi` file is written atomically from its whole text (`files.writeAtomically`), and extern makes
  the whole text before it writes any, so that a value it cannot extern leaves nothing half-written in the writer.
- **The bootstrap** keeps Python's `json`, which is the reference that §1, decision 3, matches.
- **Compiled code** keeps its C (decision 8).
- **WebAssembly** has its own serializer, in Quest: `runtime/wasm/dynamic`, a port of `quest_serialization.c` with
  its own JSON writer and parser ([wasm.md](wasm.md)). It keeps them, as the C runtime keeps its own (user,
  2026-11-18), and the conformance test covers it too. Moving either runtime onto `util/json` belongs to §6.

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
- **Compiled `dynamic` in Quest, now.** It needs §6's reflection interface, which is a plan of its own. The C is
  written and tested, and a conformance test keeps it honest until then.
- **Immutable trees,** which would let the library cache parses safely. But programs build trees by `put`, and the
  compiler's cache is the one cache anything needs.

## 5. Steps

1. **The library and its tests:** `lib/util/json.{int,mod}.quest` and §4's tests, with no user yet. Additive library
   code, so the targeted checks sufficed; pushed and released (`cbf6167a`), since stage 1 is the release compiling
   the compiler against the release's own `lib/` ([release-compiler.md](release-compiler.md)), which must hold
   `util/json` before the compiler can import it.
2. **The compiler on the library:** delete `questlang/common/json`, add `jsonCache`, rewrite the accessors. Check
   that artifacts come out byte-identical (the fixed point and the ABI corpus), and measure the build (§3.2).
3. **Dynamic on the library,** in the self-hosted interpreter (`read`; §3.4), with the conformance test,
   `tests/source/stdlib/json_dynamic.quest`. It found the one place where the implementations disagreed: the C
   runtime and WebAssembly's serializer wrote DEL (byte 127) as itself, and Python, so the interpreters, as `\u007f`.
   Both runtimes now escape it.
4. **Docs:** a `util/json` section in [libraries.md](libraries.md), [dynamic.md](dynamic.md) §3 pointing at it, and
   JSON removed from [future-libraries.md](future-libraries.md).

## 6. Later: Compiled `dynamic` in Quest

Not part of this plan's steps. This section says what moving `quest_serialization.c` into Quest would need, so
that the option stays open.

### 6.1. It Has Been Done Once

WebAssembly's `runtime/wasm/dynamic` (1,691 lines) is `quest_serialization.c` in Quest, function for function:
- it builds the type graph and makes it canonical;
- it finds shared objects in a first pass;
- it writes the document;
- it reads a document back, making descriptors and then values.

It needs two things from below it, and native code would need the same two:
- **Descriptors as Quest can read and make them.** On WebAssembly they are Quest data: `wasm/core`'s
  `Desc`, a tuple of kind, name, parts, labels, and flags, with `newDesc`, `setPart`, `instantiate`,
  `isSubtype`, and the registry of abstract types.
- **Values as one slot of unknown kind.** This is an `Any`, read and made by 38 intrinsics (externals named
  `wasm.NAME`), among them `arraySlot`, `recordSlot`, `variantTag`, `autoPayload`, `newRecordPayload`, `newTuple`,
  `newOption`, and `same`.

So the work is not writing a serializer in Quest. It is giving native code the interface that WebAssembly's
serializer stands on, and then running that one serializer on both.

### 6.2. The Interface: `runtime/reflect`

An unsound interface (only unsound modules may import it, as with `os/value`), implemented twice:
- **On WebAssembly,** by `wasm/core` and its intrinsics, mostly by renaming.
- **On native targets** (C, ssac, arm64, the JIT), by C externals over helpers the runtime already has.

| Group | Operations | Native implementation |
|---|---|---|
| **Types: reading** | `Desc` abstract, with `kind`, `name`, `partCount`, `part(d i)`, `label(d i)`, `flags(d i)`, `boundIndex`, `autoBound`, `storedType`, `storage`; `sameDesc` and `descHash`, for the type graph's tables | Reads of `QTypeDescriptor` and its `extra` structs. A record's fields are read by index in name order, never by offset |
| **Types: making** | `newDesc(kind name n)`, `setPart`, `setFlags`, `instantiate(template args)`, `isSubtype`, the bound variables | As `quest_read_type_table` makes run-time descriptors now: allocate, then fill, so a recursive type's descriptor can be cyclic |
| **Abstract types** | `abstractRep(d)`, `lookupAbstract(name arity)`, `registerUnlinked(name rep)`, `isWord(d)` | `quest_abstract_type_rep` and the registry of `quest_register_abstract_type` |
| **Values: reading** | `Any` abstract; `toInt`, `toReal`, `toBool`, `toChar`, `toString`, `toWord`; `field(x d i)`, `element(x d i)`, `arrayCount`, `arraySlot`, `caseOf(x d)`, `casePayload(x d)`, `autoWitness`, `autoComponent(x i)`, `convert(x from to)` | `quest_tuple_element`, `quest_variant_case`, `quest_record_field_offset`, `quest_convert`, `quest_dynamic_component`: the layout stays the runtime's business |
| **Values: making** | `fromInt` … `fromString`; `newRecord(d)`, `newTuple(d)`, and `newArray(d n)`, each with its slots unset, then `setSlot(x d i v)`; `newVariant(d tag payload)`, `newOption(d tag slots)`, `newAuto(d witness slots)` | Allocation by the object's layout, and stores through the write barrier |
| **Identity** | `same(a b)` and `identityHash(a)`, for the writer's table of objects reached twice | Address comparison and `quest_identity_hash` |

An object is made before its parts, then filled, for the same reason WebAssembly's reader does it: a value with
`@id` must exist before the `@ref`s inside it are read. That is why `setSlot` exists, and why it has to go
through the barrier.

### 6.3. What Native Code Must Allow

- **The collector must scan an `Any` ambiguously.** On native targets an `Any` is a `QVal`, which is a pointer or
  an untagged integer the collector can't tell apart. The collector already treats some words ambiguously: those
  in frames without a stack map, `val` words, and the JIT's data ([collector.md](collector.md)). An `Any` in a
  frame or an array would be one more such word. That's sound only while the heap doesn't move, so collector
  step 7 (evacuation) would have to pin what an ambiguous word reaches. The collector already has to do that for
  its other ambiguous words.
- **Barriers on `setSlot`.** Filling an object after it was allocated is a store into an existing object, which
  sticky-mark-bit generations need a barrier for ([collector.md](collector.md), barrier-after-store).
- **Descriptors made at run time are heap objects** traced like any other, as the C reader's are now.
- **A Quest `Desc` stays an opaque handle on native targets,** not a copy as a Quest tuple. A copy would double
  every descriptor and need converting back for `dynamic.be`.
- **Speed.** Each slot read becomes an external call that the C did inline. `extern` and `intern` are on no hot
  path of the compiler, which uses its own value model, but a benchmark should time externing and interning a
  large value under both implementations before the C is deleted.

### 6.4. What It Would Buy

- **One serializer for every compiled target,** in place of `quest_serialization.c` (2,166 lines) and
  `runtime/wasm/dynamic` (1,691). Both of their hand-written JSON layers would be replaced by `util/json`.
- **Optionally, one for the self-hosted interpreter too,** if `runtime/reflect` were also implemented over
  `questlang/values/model`, retiring `questlang/values/dynamic{json,writer,reader}`. The bootstrap keeps Python,
  which is the reference.

### 6.5. Steps, When Wanted

1. **`runtime/reflect` on WebAssembly,** with `runtime/wasm/dynamic` rewritten over it and over `util/json`. The
   bytes it writes must not change.
2. **`runtime/reflect` on native targets:** the C externals, ambiguous scanning of `Any`, and the barrier on
   `setSlot`. Unit-test them against `quest_serialization.c` on the dynamic goldens.
3. **Native `dynamic` on the shared serializer.** Run the dynamic goldens on every backend, plus stress mode,
   which interns under frequent collections. Time it against the C (§6.3), then delete the C's serialization.
4. **Optionally, the self-hosted interpreter** on the same serializer.
