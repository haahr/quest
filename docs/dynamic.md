# Quest Dynamic Types & Serialization (`dynamic.extern` / `dynamic.intern`)

This document specifies the design, runtime representation, and JSON serialization format for Quest dynamic
types (`Dynamic.T`, also named `Dynamic`). The `dynamic` module is an ordinary library module,
`lib/dynamic.mod.quest`: `new` and `be` are written in Quest, and `copy`, `extern`, and `intern` are runtime
operations declared `external` (implemented in `bootstrap/python/quest/dynamic_json.py` and
`bootstrap/python/quest/builtins.py` for the interpreter, and `runtime/quest_serialization.c` for compiled code).

---

## 1. Overview & Theoretical Foundation

In Cardelli's *Typeful Programming* (§9.1 and Appendix), dynamic types provide a type-sound mechanism for handling
heterogeneous data, persistence, and run-time metaprogramming. A dynamic value packages an arbitrary runtime value
together with its type. As Cardelli defines it, `Dynamic.T` is the auto type `Auto A::TYPE with a:A end`
([type-system.md](type-system.md) §6.11), so a dynamic value is an auto value whose one component `a` is the value:

```quest
interface Dynamic
import
    reader: Reader
    writer: Writer
export
    Def T = Auto A::TYPE with a: A end
    error: Exception
    new(A::TYPE a: A): T
    be(A::TYPE d: T): A
    copy(d: T): T
    intern(rd: reader.T): T
    extern(wr: writer.T d: T): Ok
end;
```

*A discrepancy in Cardelli:* the prose of §9.1 defines `Dynamic_T` as `Auto A::TYPE with a:A end`, but the
`Dynamic` interface in his appendix writes `Def T = Auto A::TYPE with :A end`, with an unnamed component. An unnamed
component cannot be selected, which would leave an `inspect` binder no way to reach the value, so Quest follows
§9.1. The global type name `Dynamic` also denotes this type.

- **`dynamic.new(:Type val)`**: `auto :Type with val end`.
- **`dynamic.be(:TargetType d)`**: `inspect d when TargetType with x then x.a else raise error as TargetType end
  end`: the value if `d`'s type component is a subtype of `TargetType`, otherwise `dynamic.error`.
- **`inspect d when T with x then ... end`**: as for any auto value, `x` is the component tuple, and `x.a` the
  packaged value.
- **`dynamic.copy(d)`**: A new dynamic value with the same type component and value (the value itself is shared).
- **`dynamic.extern(wr, d)`**: Serializes `d` into a stream in a cycle-safe, JSON-compatible representation.
- **`dynamic.intern(rd)`**: Deserializes a dynamic value from an input stream, reconstructing the object graph,
  resolving cyclic/shared references, and restoring the packaged type for subsequent `dynamic.be` checks.

---


## 2. Wire Format, Version 1

> **Status:** implemented in both backends (`bootstrap/python/quest/dynamic_json.py` and
> `runtime/quest_serialization.c`), except abstract types (§2.3), which neither writes yet. It replaced an
> unversioned predecessor in which `@type` was a Quest type expression printed as a string: printing a recursive type
> shares nothing (a single `syntax_ast` type printed as 5 MB), both readers needed a Quest type parser (the C runtime
> had only a partial one), and nested dynamics repeated their whole type. Files in the old form are not read.

A serialized dynamic value is one JSON document that holds a **type table** and a **value**. Every type the
document mentions is written once, as structured JSON, in the table; types and values refer to table entries by
index. Values are decoded by following their type, so the value encoding stays close to plain JSON.

### 2.1. Document

```json
{
  "quest": 1,
  "types": [ <TypeNode>, ... ],
  "type": <TypeRef>,
  "value": <Value>
}
```

- **`quest`**: the format version, an integer. A reader rejects versions it does not know (`dynamic.error`).
  It is independent of the build ABI version (docs/build-process.md §5.2), although `.qi` files use this
  format, so changing it also bumps the ABI.
- **`types`**: the type table. Nested dynamic values anywhere in `value` use the same table.
- **`type`**: the type of the dynamic value.
- **`value`**: the value, encoded as §2.4 describes for that type.

The top level is not a value, so its keys need no `@`.

### 2.2. Type References and Type Nodes

A **TypeRef** is either the name of a built-in type, as a string, or a non-negative integer index into
`types`:

| Built-in name | Type |
| :--- | :--- |
| `"Ok"`, `"Bool"`, `"Char"`, `"String"`, `"Int"`, `"Real"` | the basic types |
| `"Dynamic"` | `Dynamic.T` |

A **TypeNode** is a JSON object with exactly one key, naming the type constructor:

| Node | Type |
| :--- | :--- |
| `{"record": {"<label>": TypeRef, ...}}` | `Record ... end` |
| `{"tuple": [["<label>", TypeRef], ...]}` | `Tuple ... end` (value components only, in order) |
| `{"variant": {"<tag>": TypeRef \| null, ...}}` | `Variant ... end`; `null` for a case without a payload |
| `{"option": {"<tag>": TypeRef \| null, ...}}` | `Option ... end`; a case's components are a `tuple` node |
| `{"array": TypeRef}` | `Array(T)` |
| `{"fun": {"params": [["<mode>", TypeRef], ...], "result": TypeRef}}` | a monomorphic function type |
| `{"exception": TypeRef}` | `Exception(T)` |
| `{"abstract": "<module path>.<name>", "rep": TypeRef}` | an abstract type exported by a module (§2.3) |

A **label** is a field name, prefixed with `var ` when the field is mutable (`"var next"`). An unnamed tuple
component has the label `""` (or `"var"` when mutable). Identifiers cannot contain spaces and `var` is a
keyword, so labels are unambiguous. A function parameter is written by its mode alone (`""`, `"var"`, or `"out"`),
since parameter names do not affect function types. `Out(T)` does not occur in the types of values.

Variant and option cases are listed in the order the type declares them, which is how compiled code numbers
them. An option case with components (`cons with head: Int tail: L end`) refers to a tuple node for them; a case
without, and a variant case without a payload, has `null`.

**Recursive types are cycles in the table.** Quest's recursive types are equi-recursive: two types are equal
when their infinite unfoldings are, and a recursive type is a finite graph with type constructors at the nodes
(Typeful Programming §4.7). The table is that graph, so it needs no `Rec` binder: a reference back to an
enclosing node is the recursion. For example, `Rec(L) Option nil cons with head: Int tail: L end end` is

```json
"types": [
  {"option": {"nil": null, "cons": 1}},
  {"tuple": [["head", "Int"], ["tail", 0]]}
]
```

Type operator applications are reduced before writing (`List(Int)` is written as the type it denotes), and
aliases are written as their meaning.

**Canonical tables.** Both backends write the same table for the same type, so that their output can be
compared, as the golden tests do. A writer builds the graph of the types it meets (from types in the interpreter,
from descriptors in compiled code, which unroll recursive types differently), merges structurally equivalent nodes
(partition refinement to the coarsest bisimulation, starting from each node's constructor and labels), and numbers
the remaining nodes in the order a depth-first walk first reaches them: from the dynamic value's type, then from
the types of nested dynamic values in the order their values are written, visiting each node's components in the
order the node lists them (record fields by name, cases in declaration order, tuple components and parameters in
order, then a function's result). The table is therefore minimal, and equal types have one entry. A reader does not
rely on this: it compares types structurally, never by index.

**Not encodable yet.** Polymorphic types (`All`), tuple types with type components (abstract tuples), auto
types other than `Dynamic.T` (which is `Auto A::TYPE with a:A end` and is written by its built-in name), and type
operators themselves have binders that this table does not express; abstract types, including `Word.T`, await §2.3.
`dynamic.extern` raises `dynamic.error` for a type containing one. A later version can add binder nodes.

### 2.3. Abstract Types

Cardelli allows every dynamic value to be externed except readers and writers (Typeful Programming §9.1), and
requires the type in a dynamic to be *closed*: it may not contain free type variables. A module's abstract type
`a.T` is closed in that sense, because it is named through the global name space of compiled modules, in which
`a.T` matches `b.T` precisely when `a` and `b` are the same module (§7.3, the diamond import). An abstract type
extracted from a local tuple value (`t.A`) depends on that value and is not closed.

- **`dynamic.new` rejects value-dependent abstract types.** The typechecker reports a static error when the type
  given to `dynamic.new` contains an abstract type whose root is not a module (a let-bound tuple, a parameter, a
  block variable), since the type would escape its scope.
- **Module abstract types are written by global name and representation.** A module abstract type is written as
  `{"abstract": "geo/coord.P", "rep": TypeRef}`: the module's import path, a dot, the type name, and the type
  that implements it. The writer gets the representation from the module that defines it (in the interpreter,
  the module's environment; in compiled code, a descriptor the module registers for each exported abstract type).
- **On `intern`, the representation is checked.** If the reading program links the module `geo/coord`, the
  abstract type is read as `coord.P` only if the recorded representation is equal (as an equi-recursive type) to
  that module's actual representation; otherwise `intern` raises `dynamic.error`. This catches a file written
  by a program linked with an older implementation of the module.
- **An unlinked module's type stays opaque.** If the reading program does not link the module, the type is
  reconstructed as an opaque nominal type with the same global name and representation. No static type in the
  program names it, so `dynamic.be` can only succeed at `Dynamic`-compatible types, and externing it again
  writes the same node.

Within the language, abstraction is preserved: only `dynamic.be(:coord.P d)` yields the value, and only at type
`coord.P`. The JSON text does expose the representation, as it exposes every value.

### 2.4. Values

Decoding is directed by the type, so the same JSON shape can mean different things at different types (an array
is an `Array` or a `Tuple`; a string is a `String`, a `Char` or a payload-free case). A value that does not fit
its type raises `dynamic.error`.

| Type | JSON | Notes |
| :--- | :--- | :--- |
| `Ok` | `null` | |
| `Bool` | `true` / `false` | |
| `Int` | integer | Readers must parse 64-bit integers exactly, not through a double. |
| `Real` | number | As Python's `repr` writes it: the shortest digits that read back exactly, positional for decimal exponents in [-4, 16) (`100.0`, `0.0001`) and otherwise `1e+16`, `1e-05`. Infinities are the strings `"Infinity"` and `"-Infinity"`; NaN is not a `Real` value. |
| `Char` | one-character string | |
| `String` | string | Standard JSON escaping. |
| `Record` | `{"<field>": value, ...}` | Keys sorted; exactly the type's fields; `var` fields hold their current value. |
| `Tuple` | `[value, ...]` | In component order. |
| `Array(T)` | `[value, ...]` | |
| `Variant` | `"<tag>"` or `{"<tag>": value}` | Serde-style external tagging. A case without a payload, or with payload type `Ok`, is the bare tag. |
| `Option` | `"<tag>"` or `{"<tag>": [value, ...]}` | A case without components is the bare tag; otherwise its components, in order. |
| `Dynamic.T` | `{"@type": TypeRef, "@value": value}` | The nested value's type is in the document's table. |
| abstract type | the value at its representation type | |

### 2.5. Sharing and Cycles

`extern` and `intern` preserve sharing and circularities within one dynamic value, but not across values
(Typeful Programming §9.1). Records, tuples and arrays that are reached more than once are written in full the
first time, with an identifier, and as a reference afterwards:

- A shared record has an `"@id": n` key alongside its fields. Field names never begin with `@`.
- A shared tuple or array is written as `{"@id": n, "@items": [value, ...]}`; the type says which it is.
- Every later occurrence is `{"@ref": n}`.

Identifiers are integers, numbered from 1 in the order the writer first reaches the shared objects. Only objects
reached more than once get one. An object's `@id` always precedes its `@ref`s in the document, so a reader can
allocate the object when it meets the `@id`, before reading its components. Empty tuples and the components of an
option value are never shared: compiled code has one empty tuple, and stores an option's components in the option
value itself.

### 2.6. Non-Externable Values and Errors

- Readers, writers and closures cannot be externed; nor can values whose type is not encodable (§2.2). `extern`
  raises `dynamic.error`. (Cardelli allows functions to be externed; that needs a code representation that this
  format does not have.)
- Exception values cannot be externed either. Each evaluation of an exception expression makes a new exception,
  and handlers match exceptions by identity, so an exception read back from a file could never be caught by any
  handler in the reading program. Types may still mention `Exception(T)` (for instance in a variant case the value
  does not use), so the type node exists.
- `intern` raises `dynamic.error` on malformed JSON, an unknown `quest` version, a type reference out of range,
  a type node it does not recognize, a value that does not fit its type, an undefined `@ref`, or an abstract type
  whose representation does not match (§2.3).

### 2.7. Formatting

`extern` writes compact JSON with no whitespace (`separators=(",", ":")`), so output is deterministic across
the interpreter and compiled code.

---

## 3. Implementation Architecture

### 3.1. Writing

Writing takes two passes over the value: the first finds objects reached more than once, and collects the types
of the dynamic value and of the nested dynamic values it reaches; the type table is then made canonical (§2.2); the
second pass writes the document. Both passes follow the value's type, so a record viewed at a supertype writes only
that type's fields.

### 3.2. Reading

Reading takes one pass over the value, after the type table is turned into types. An object with an `@id` is
allocated and registered before its components are read, so `@ref`s inside it and after it resolve to it.

- **Interpreter** (`bootstrap/python/quest/dynamic_json.py`): builds `QType`s from the graph. A node reached
  again while it is still being built is a back edge, so the node becomes a recursive type `Rec(X) ...` and the
  back edge becomes `X`; any choice of binder places gives an equal type. No Quest parser is involved.
- **C runtime** (`runtime/quest_serialization.c`): builds `QTypeDescriptor`s directly, since descriptors are
  already graphs: allocate one descriptor per node, then fill in their references. `dynamic.be` keeps comparing
  descriptors structurally (`quest_is_subtype`).

### 3.3. Descriptors in Generated C

Static descriptors carry the full structure of their type (record and tuple labels with `var` flags, case
payloads, function parameters and results), so the C writer produces the type table from them; §2.3 will add an
abstract type's global name and representation. A descriptor's `.name` is used only in diagnostics (and, for
opaque types, in comparisons), so it is the type printed and cut off at 80 characters
(`descriptor_display_name`). Static descriptors are no longer registered with the runtime or looked up by name,
and the runtime no longer parses type strings.

### 3.4. `.qi` Files

Interface artifacts are written in this format. Their schema is unchanged: signatures stay Quest-syntax strings
(`typeSig`, `manifestType`), because they are compiler metadata that need type variables and path types. Only
the envelope changed, with `ABI_VERSION` 4.

### 3.5. Abstract Types

Module abstract types are not yet handled as §2.3 describes: both backends raise `dynamic.error` when externing a
value whose type mentions one.

---

## 4. Example Serialization

### Cyclic Record in Quest
```quest
Let Node = Record id: Int var next: Dynamic.T end;
let n1 = record id = 1 var next = dynamic.new(:Ok ok) end;
let n2 = record id = 2 var next = dynamic.new(:Node n1) end;
n1.next := dynamic.new(:Node n2);

let d = dynamic.new(:Node n1);
dynamic.extern(writer.output d);
```

**Serialized JSON output (compact on the wire, formatted here for clarity):**
```json
{
  "quest": 1,
  "types": [
    {"record": {"id": "Int", "var next": "Dynamic"}}
  ],
  "type": 0,
  "value": {
    "@id": 1,
    "id": 1,
    "next": {
      "@type": 0,
      "@value": {
        "id": 2,
        "next": {"@type": 0, "@value": {"@ref": 1}}
      }
    }
  }
}
```

The record type is written once, though three dynamics use it. When decoded with `dynamic.intern(reader.input)`,
`n1.next.next` is identical to `n1` in memory, and `dynamic.be(:Node d)` succeeds.

### Recursive List
```quest
Let Rec IntList = Option nil cons with head: Int tail: IntList end end;
let l = option cons of IntList with tuple let head = 1 let tail = option nil of IntList end end end;
dynamic.extern(writer.output dynamic.new(:IntList l));
```

```json
{
  "quest": 1,
  "types": [
    {"option": {"nil": null, "cons": 1}},
    {"tuple": [["head", "Int"], ["tail", 0]]}
  ],
  "type": 0,
  "value": {"cons": [1, "nil"]}
}
```
