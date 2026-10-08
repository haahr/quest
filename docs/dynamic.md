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

> **Status:** designed, not yet implemented. Until it lands, `dynamic.extern` writes an unversioned
> predecessor in which `@type` is a Quest type expression printed as a string. That form is being replaced
> because printing a recursive type shares nothing (a single `syntax_ast` type printed as 5 MB), because both
> readers then need a Quest type parser (the C runtime has only a partial one), and because nested dynamics
> repeat their whole type. Files in the old form are not read; nobody keeps them until the self-hosted
> compiler is complete.

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
| `"Word"` | `Word.T` (externally implemented) |

A **TypeNode** is a JSON object with exactly one key, naming the type constructor:

| Node | Type |
| :--- | :--- |
| `{"record": {"<label>": TypeRef, ...}}` | `Record ... end` |
| `{"tuple": [["<label>", TypeRef], ...]}` | `Tuple ... end` (value components only, in order) |
| `{"variant": {"<tag>": TypeRef \| null, ...}}` | `Variant ... end`; `null` for a case without a payload |
| `{"option": {"<tag>": TypeRef \| null, ...}}` | `Option ... end`; `null` for a case without a payload |
| `{"array": TypeRef}` | `Array(T)` |
| `{"fun": {"params": [["<label>", TypeRef], ...], "result": TypeRef}}` | a monomorphic function type |
| `{"exception": TypeRef}` | `Exception(T)` |
| `{"abstract": "<module path>.<name>", "rep": TypeRef}` | an abstract type exported by a module (§2.3) |

A **label** is a field name, prefixed with `var ` when the field is mutable (`"var next"`). An unnamed tuple
component has the label `""` (or `"var"` when mutable). Identifiers cannot contain spaces and `var` is a
keyword, so labels are unambiguous. `Out(T)` does not occur in the types of values.

**Recursive types are cycles in the table.** Quest's recursive types are equi-recursive: two types are equal
when their infinite unfoldings are, and a recursive type is a finite graph with type constructors at the nodes
(Typeful Programming §4.7). The table is that graph, so it needs no `Rec` binder: a reference back to an
enclosing node is the recursion. For example, `Rec(L) Option nil cons with head: Int tail: L end end` is

```json
"types": [
  {"option": {"cons": 1, "nil": null}},
  {"tuple": [["head", "Int"], ["tail", 0]]}
]
```

Type operator applications are reduced before writing (`List(Int)` is written as the type it denotes), and
aliases are written as their meaning.

**Canonical order.** A writer numbers nodes in the order a depth-first walk from the root type first reaches
them, visiting record fields, variant cases and option cases in sorted order, tuple and parameter components in
order, and nested dynamics' types in the order their values are written. A writer may share structurally
identical nodes (hash-consed types make that natural), but a reader must not assume the table is minimal or
that equal types have one index: types are compared structurally, never by index.

**Not encodable yet.** Polymorphic types (`All`), tuple types with type components (abstract tuples), auto
types other than `Dynamic.T` (which is `Auto A::TYPE with a:A end` and is written by its built-in name), and type
operators themselves have binders that this table does not express. `dynamic.extern`
raises `dynamic.error` for a type containing one. A later version can add binder nodes.

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
| `Int`, `Word.T` | integer | Readers must parse 64-bit integers exactly, not through a double. |
| `Real` | number | Non-finite values are the strings `"NaN"`, `"Infinity"`, `"-Infinity"`. |
| `Char` | one-character string | |
| `String` | string | Standard JSON escaping. |
| `Record` | `{"<field>": value, ...}` | Keys sorted; exactly the type's fields; `var` fields hold their current value. |
| `Tuple` | `[value, ...]` | In component order. |
| `Array(T)` | `[value, ...]` | |
| `Variant`, `Option` | `"<tag>"` or `{"<tag>": value}` | Serde-style external tagging. A case without a payload, or with payload type `Ok`, is the bare tag. |
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
reached more than once get one.

### 2.6. Non-Externable Values and Errors

- Readers, writers and closures cannot be externed; nor can values whose type is not encodable (§2.2). `extern`
  raises `dynamic.error`. (Cardelli allows functions to be externed; that needs a code representation that this
  format does not have.)
- `intern` raises `dynamic.error` on malformed JSON, an unknown `quest` version, a type reference out of range,
  a type node it does not recognize, a value that does not fit its type, an undefined `@ref`, or an abstract type
  whose representation does not match (§2.3).

### 2.7. Formatting

`extern` writes compact JSON with no whitespace (`separators=(",", ":")`), so output is deterministic across
the interpreter and compiled code.

---

## 3. Implementation Architecture

### 3.1. Writing

Writing takes two passes over the value, as now: the first finds objects reached more than once, the second
writes the value. The type table is filled as the second pass meets each type: the root type, then each nested
dynamic's type, adding nodes in the canonical order of §2.2. Types are hash-consed, so a writer keyed on node
identity shares each type node it has already written.

### 3.2. Reading

Reading also takes two passes, as now: the first allocates every object with an `@id`, the second fills them and
resolves `@ref`s. Before either, the type table is turned into types:

- **Interpreter** (`bootstrap/python/quest/dynamic_json.py`): builds `QType`s from the graph. A node reached
  again while it is still being built is a back edge, so the node becomes a recursive type `Rec(X) ...` and the
  back edge becomes `X`; any choice of binder places gives an equal type. No Quest parser is involved.
- **C runtime** (`runtime/quest_serialization.c`): builds `QTypeDescriptor`s directly, since descriptors are
  already graphs: allocate one descriptor per node, then fill in their references. `dynamic.be` keeps comparing
  descriptors structurally (`quest_is_subtype`).

### 3.3. Descriptors in Generated C

Static descriptors carry the full structure of their type (record and tuple labels with `var` flags, case
payloads, function parameters and results, and, for an abstract type, its global name and representation), so
the C writer can produce the type table from them. A descriptor's `.name` is used only in diagnostics, so it
becomes a short display name instead of the full printed type. Name-based lookup
(`quest_lookup_type_descriptor_by_name`) and the type-string parser (`quest_parse_type_descriptor`) are
removed.

### 3.4. `.qi` Files

Interface artifacts are written in this format. Their schema is unchanged: signatures stay Quest-syntax strings
(`typeSig`, `manifestType`), because they are compiler metadata that need type variables and path types. Only
the envelope changes, which bumps `ABI_VERSION`.

### 3.5. The Current Implementation

Until version 1 lands, both backends write and read the unversioned predecessor: `{"@type": "<printed type>",
"@value": value}`, nesting the same envelope for each nested dynamic value. A dynamic value is an auto value whose
one component is the value (in C, a `QAuto` whose payload points to that component, stored as a `QVal`), and
serialization supports auto values with one component. The interpreter reads `@type` with the Quest parser
(`parse_type_string`); the C runtime looks it up among the program's registered descriptors or parses it with its
own type parser (`quest_parse_type_descriptor`), which reads auto types such as `Auto A :: TYPE with a: A end`,
laying out their components as the compiler stores them.

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
    {"option": {"cons": 1, "nil": null}},
    {"tuple": [["head", "Int"], ["tail", 0]]}
  ],
  "type": 0,
  "value": {"cons": [1, "nil"]}
}
```
