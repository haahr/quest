# questlang/values: run-time values and the dynamic format

This directory defines what a Quest value is when the self-hosted compiler interprets a program rather than compiling
it, and how such values are written to and read from text in the *dynamic format*, the JSON document that
`dynamic.extern` writes and `dynamic.intern` reads. The interpreters in
[`questlang/interpreter`](../interpreter/README.md) compute these values; the interface compiler
(`questlang/modules/artifacts/interfacecompiler`) uses them too, because a compiled interface, a `.qi` file, is a
document in the dynamic format whose value is a record describing the interface. Compiled programs never see these
modules: in compiled code a value is its C representation, and the same format is written and read by the runtime
(`runtime/quest_serialization.c`).

## Values

[`model.int.quest`](model.int.quest) declares `Value`, an `Option` (Quest's algebraic data type) with a case for
each kind of run-time value: `vInt`, `vString`, `vRecord`, `vTuple`, `vArray`, `vVariant`, `vOption`, `vClosure`,
`vRef`, `vAuto`, `vException`, and a few more. Two choices shape it.

- **Native where possible.** A scalar holds its Quest value, and a string, word, reader, writer, or string builder
  holds the native Quest object, so the standard library's functions act on it directly and the interpreter inherits
  their exact semantics.
- **Identity is the host's identity.** Quest's `is` compares scalars by value and everything else by identity. A
  record, tuple, array, closure, cell, or auto value is a Quest tuple or array whose identity is the interpreted
  value's, so `model.same` is `is` on what the two values hold.

A record's fields are kept by name and printed in sorted order; a tuple keeps its components in order with their
labels, if its type gives them. A mutable variable or `var` field is a `Ref`: a cell, or a reference to an array
element or tuple component, which is what a `var` or `out` argument passes. An auto value (Cardelli's package of a
type with components that depend on it) pairs its components with the type; a dynamic value is the auto value of
type `Auto A::TYPE with a:A end`, so it carries its value's type at run time, which `dynamic.be` checks against.

The interpreter's frames (`Frame`, and `Root`, which every frame of one run shares) are declared here too, although
their operations are the tree-walker's: a closure must hold the frame it was made in, and Quest's acyclic module
graph requires the types to be in one place. Errors are here as well. One Quest exception, `runError`, stands for
everything that goes wrong while running; its `Cause` is either a Quest exception raised by the program (with its
payload and the payload's type) or an internal error of the interpreter, and it records the raise site and the
frames that were running.

## The dynamic format

A document holds a table of types and a value of one of them:

```
{"quest":1,"types":[{"option":{"cons":1,"nil":null}},{"tuple":[["head","Int"],["tail",0]]}],
 "type":0,"value":{"cons":[1,"nil"]}}
```

This is the list `cons(1, nil)` at type `Rec IntList = Option nil cons with head: Int tail: IntList end end`: entry 0
is the option type, entry 1 the tuple of its `cons` case, which refers back to entry 0, so recursive types are cycles
in the table. A record, tuple, or array reached more than once is written once, tagged `"@id"`, and afterwards as
`{"@ref": n}`, so sharing and cycles in the value survive a round trip.

The table is **canonical**: the interpreter and compiled code must write the same text for the same value, although they
meet types in different forms (types of the checker here, descriptors in C).
[`dynamicjson.mod.quest`](dynamicjson.mod.quest) holds what writing and reading share. Its `Graph` collects one node per
type structure as the writer meets types; `canonicalTable` then merges structurally equivalent nodes, the coarsest
bisimulation, found by partition refinement (start with nodes grouped by shape, split groups whose children fall in
different groups until nothing splits), and numbers the survivors in the order a depth-first walk from the roots reaches
them. Two descriptions of the same recursive type, unrolled differently, therefore give the same table. Abstract types
of modules are written by their global name, with their representation found through the module's registration.

[`dynamicwriter.mod.quest`](dynamicwriter.mod.quest) (`encode`) makes two passes over a value, following its type:
the first counts how often each object is reached and collects the types, the second writes. A record seen at a
supertype writes only that type's fields. A value the format cannot hold (a function, an exception, a reader) raises
`dynamic.error`. [`dynamicreader.mod.quest`](dynamicreader.mod.quest) (`decode`) turns the table back into types,
making a back edge into a recursive type, and reads the value in one pass, registering each `"@id"` object before
reading its components so that references inside it resolve.

## Connections

`questlang/interpreter/builtins` calls `encode` and `decode` for `dynamic.extern` and `dynamic.intern`; the interface
compiler writes `.qi` files with `encode` and loads them with `decode`; the types come from
[`questlang/types`](../types/README.md). The bootstrap's counterpart is
[`bootstrap/python/quest/values`](../../bootstrap/python/quest/values/README.md), and the C runtime's writer and
reader are in [`runtime/quest_serialization.c`](../../runtime/quest_serialization.c); the three must agree byte for
byte.

## Further reading

- [docs/dynamic.md](../../docs/dynamic.md): the format (§2), its implementations (§3), and worked examples (§4).
- [docs/interpreter.md](../../docs/interpreter.md) §1 and §2: the interpreter's values.
- [docs/type-system.md](../../docs/type-system.md) §6.12: auto types, of which dynamic values are one.
- [docs/build-process.md](../../docs/build-process.md) §5: `.qi` files.
