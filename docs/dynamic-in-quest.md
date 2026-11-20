# Possibility: Compiled `dynamic` in Quest

**A possibility to consider later, not a plan in progress.** Nothing here is scheduled, and nothing in the tree
depends on it. It says what moving compiled code's `dynamic.extern` and `dynamic.intern` from C into Quest would
take, so that the option stays open and can be weighed when it is wanted.

Today each implementation of the dynamic format ([dynamic.md](dynamic.md)) has its own serializer and JSON layer
([json.md](json.md) §4):
- the bootstrap: Python, the reference;
- the self-hosted interpreter: `questlang/values/dynamic{json,writer,reader}`, over `util/json`;
- compiled code on C, ssac, arm64, and the JIT: `runtime/quest_serialization.c` (2,167 lines), with its own JSON;
- WebAssembly: `runtime/wasm/dynamic` (1,692 lines), with its own JSON.

`tests/source/stdlib/json_dynamic.quest` and the dynamic goldens hold them to the same text.

## 1. Goal

One serializer, in Quest, for every compiled target, with `util/json` as its text layer. Optionally the same
serializer for the self-hosted interpreter too (§6).

## 2. It Has Been Done Once

`runtime/wasm/dynamic` is `quest_serialization.c` in Quest, function for function:
- it builds the type graph and makes it canonical;
- it finds shared objects in a first pass;
- it writes the document;
- it reads a document back, making descriptors and then values.

It stands on two things, and native code would need the same two:
- **Descriptors that Quest can read and make.** On WebAssembly they are Quest data: `wasm/core`'s `Desc`, a tuple
  of kind, name, parts, labels, and flags, with `newDesc`, `setPart`, `instantiate`, `isSubtype`, and the registry
  of abstract types.
- **Values as one slot of unknown kind.** This is an `Any`, read and made by about 25 intrinsics (externals named
  `wasm.NAME`), among them `arraySlot`, `recordSlot`, `variantTag`, `autoPayload`, `newRecordPayload`, `newTuple`,
  `newOption`, and `same`.

So the work isn't writing a serializer in Quest. It is giving native code the interface that WebAssembly's
serializer stands on, and then running that one serializer on both.

## 3. The Interface: `runtime/reflect`

An unsound interface, which only unsound modules may import, as with `os/value` ([libraries.md](libraries.md) §4.4).
It would be implemented twice:
- **on WebAssembly,** by `wasm/core` and its intrinsics, mostly by renaming;
- **on native targets** (C, ssac, arm64, the JIT), by C externals over helpers the runtime already has.

| Group | Operations | Native implementation |
|---|---|---|
| **Types: reading** | `Desc` abstract, with `kind`, `name`, `partCount`, `part(d i)`, `label(d i)`, `flags(d i)`, `boundIndex`, `autoBound`, `storedType`, `storage`; `sameDesc` and `descHash`, for the type graph's tables | Reads of `QTypeDescriptor` and its `extra` structs. A record's fields are read by index in name order, never by offset |
| **Types: making** | `newDesc(kind name n)`, `setPart`, `setFlags`, `instantiate(template args)`, `isSubtype`, the bound variables | As `quest_read_type_table` makes run-time descriptors now: allocate, then fill, so a recursive type's descriptor can be cyclic |
| **Abstract types** | `abstractRep(d)`, `lookupAbstract(name arity)`, `registerUnlinked(name rep)`, `isWord(d)` | `quest_abstract_type_rep` and the registry of `quest_register_abstract_type` |
| **Values: reading** | `Any` abstract; `toInt`, `toReal`, `toBool`, `toChar`, `toString`, `toWord`; `field(x d i)`, `element(x d i)`, `arrayCount`, `arraySlot`, `caseOf(x d)`, `casePayload(x d)`, `autoWitness`, `autoComponent(x i)`, `convert(x from to)` | `quest_tuple_element`, `quest_variant_case`, `quest_record_field_offset`, `quest_convert`, `quest_dynamic_component`: the layout stays the runtime's business |
| **Values: making** | `fromInt` … `fromString`; `newRecord(d)`, `newTuple(d)`, and `newArray(d n)`, each with its slots unset, then `setSlot(x d i v)`; `newVariant(d tag payload)`, `newOption(d tag slots)`, `newAuto(d witness slots)` | Allocation by the object's layout, and stores through the write barrier |
| **Identity** | `same(a b)` and `identityHash(a)`, for the writer's table of objects reached twice | Address comparison and `quest_identity_hash` |

An object is made before its parts and then filled, for the same reason WebAssembly's reader does it: a value with
`@id` must exist before the `@ref`s inside it are read. That is why `setSlot` exists, and why it has to go through
the barrier.

## 4. What Native Code Must Allow

- **The collector must scan an `Any` ambiguously.** On native targets an `Any` is a `QVal`, a pointer or an
  untagged integer that the collector can't tell apart. The collector already treats some words ambiguously: those
  in frames without a stack map, `val` words, and the JIT's data ([collector.md](collector.md)). An `Any` in a frame
  or an array would be one more. That is sound only while the heap doesn't move, which it doesn't today; if
  collector step 7 (evacuation), not taken for now, were ever taken, it would have to pin what an ambiguous word
  reaches, as it must for the other ambiguous words.
- **Barriers on `setSlot`.** Filling an object after it was allocated is a store into an existing object, which
  sticky-mark-bit generations need a barrier for ([collector.md](collector.md)).
- **Descriptors made at run time are heap objects,** traced like any other, as the C reader's are now.
- **A `Desc` stays an opaque handle on native targets,** not a copy as a Quest tuple. A copy would double every
  descriptor and need converting back for `dynamic.be`.
- **Speed.** Each slot read becomes an external call where the C reads inline. `extern` and `intern` are on no hot
  path of the compiler, which uses its own value model, but they may be on a program's.

## 5. Steps, If Taken

Each step leaves every target writing the same bytes as before: the dynamic goldens, `json_dynamic`, and the
`.qi` files read back and written again, with no golden updated.

1. **A benchmark first.** Extern and intern a large value (a deep tree, a wide record array, shared objects) and
   time them on C and arm64, so there is a number to compare each later step with. Add it to
   [benchmarks.md](benchmarks.md).
2. **`runtime/reflect` on WebAssembly,** as a renaming of `wasm/core`'s descriptor operations and the intrinsics.
   `runtime/wasm/dynamic` imports it instead of `wasm/core` and the intrinsics directly. No change in what it does.
3. **`runtime/wasm/dynamic` on `util/json`.** Its JSON writer and parser give way to the library's: the writer to
   an emitter or a tree (whichever keeps extern from writing half a document, [json.md](json.md) §4), the parser to
   `json.read(rd parsingDynamic)`. WebAssembly then has one JSON layer fewer, which tests §1's claim cheaply,
   before any native work.
4. **`runtime/reflect` on native targets:** the C externals, ambiguous scanning of `Any`, and the barrier on
   `setSlot`. Unit-test them against `quest_serialization.c` on the dynamic goldens, and run the collector's stress
   and sites modes over them ([collector.md](collector.md)).
5. **The serializer as a library module** (for example `runtime/dynamic`), moved out of `runtime/wasm` and compiled
   for every target. Native targets switch to it behind a flag, both implementations side by side, with
   `json_dynamic` run on each.
6. **Measure and decide.** Time step 1's benchmark under both. If the Quest serializer is close enough, make it the
   default and delete `quest_serialization.c`'s serializer, keeping whatever of the C the runtime still needs (the
   descriptor helpers, `dynamic.be`). If not, stop with WebAssembly on the shared module and native code on C.

Every step that changes the runtime is a backend change, so it goes with WebAssembly in the same step, and a step
that adds externals bumps the ABI.

## 6. What It Would Buy

- **One serializer for every compiled target,** in place of `quest_serialization.c` and `runtime/wasm/dynamic`,
  and both of their hand-written JSON layers replaced by `util/json`.
- **Optionally, one for the self-hosted interpreter too,** if `runtime/reflect` were also implemented over
  `questlang/values/model`, retiring `questlang/values/dynamic{json,writer,reader}` (1,977 lines). The bootstrap keeps
  Python, which is the reference.

## 7. Questions to Settle First

- **Is the speed cost acceptable,** and for which programs? Step 1 answers how much it is; whether that is
  acceptable is the user's call.
- **Does ambiguous scanning of `Any` constrain the collector too much?** It rules nothing out today, but it adds to
  what evacuation would have to pin.
- **Should the interpreter share it** (§6)? That would put `runtime/reflect` over a third value model, and the
  interpreter's serializer is the one the compiler's `.qi` files go through.
