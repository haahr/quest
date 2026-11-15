# bootstrap/python/quest/values: the bootstrap's run-time values and dynamic format

This package is the bootstrap's counterpart of [`questlang/values`](../../../../questlang/values/README.md), which
introduces its ideas in full. It defines the values the bootstrap's interpreters
([`quest.interpreter`](../interpreter/README.md)) compute, and the dynamic format, the JSON document that
`dynamic.extern` writes and `dynamic.intern` reads. Unlike the interpreter package, compilation uses it too: an
interface's compiled form, its `.qi` file, is a document in the dynamic format, which
`../modules/artifacts/interface_compiler.py` writes and reads with this package.

## Values

[`model.py`](model.py) is a class hierarchy rooted at `QValue`: `QInt`, `QString`, `QRecord`, `QTuple`, `QArray`,
`QVariant`, `QOption`, `QClosure`, `QBuiltinFun`, `QRef` (with `QArrayElementRef` and `QTupleElementRef` for
references into aggregates), `QAutoVal` for auto and dynamic values, `QExceptionVal`, and wrappers of host objects
such as `QWriter` and `QReader`. Each class gives its type's name and its canonical text. Quest's `is` is `qvalue_is`:
value equality for scalars, Python object identity for everything else. `QuestException` is a Quest exception raised
in Python, carrying the exception value and its payload.

The self-hosted `questlang/values/model` makes the same distinctions with one `Option` type, and holds strings,
readers, and writers as native Quest objects rather than Python ones. It also declares the interpreter's frames,
which here are the tree-walker's own `RuntimeEnvironment`.

## The dynamic format

[`dynamic_json.py`](dynamic_json.py) holds what writing and reading share: the type graph, made canonical by merging
structurally equivalent nodes and numbering the rest in depth-first order, so that the interpreters and compiled code
write identical text for the same value. It also holds `parse_type_string`, which reads the Quest type syntax that
`.qi` files store their signatures in; the self-hosted compiler keeps that in its interface compiler instead.
[`dynamic_writer.py`](dynamic_writer.py) (`jsog_encode`) and [`dynamic_reader.py`](dynamic_reader.py)
(`jsog_decode`) write and read documents, sharing and cycles included, through `"@id"` and `{"@ref": n}`.

The writer here, the self-hosted one, and the C runtime's (`runtime/quest_serialization.c`) must agree byte for
byte; the run goldens of the programs that call `dynamic.extern` check it.

## Further reading

- [docs/dynamic.md](../../../../docs/dynamic.md): the format and its implementations.
- [docs/interpreter.md](../../../../docs/interpreter.md) §2: this value hierarchy, class by class.
