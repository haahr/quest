# bootstrap/python/quest/repr: how values are represented, in the bootstrap

This package tells the bootstrap compiler what a value of each Quest type looks like at run time. The IR's passes in
[`../ir`](../ir/README.md) consult it to decide where values are converted and which descriptors operations need, and
the C printer in [`../codegen/c`](../codegen/c) consults it again to declare the structs, descriptors, and layouts the
IR assumed. Both compilers encode the same rules, so the code either compiles links against the one C runtime
([`runtime/`](../../../../runtime)).

The self-hosted compiler's [`questlang/repr`](../../../../questlang/repr/README.md) is a port of this package, and its
README is the full introduction. In brief, the concepts are:

- **Shapes** ([`shapes.py`](shapes.py)): the structural view of a type that backends decide by, with aliases stripped,
  type-operator applications reduced, and recursion made a cycle; cached per canonical type, so equal types share one
  shape. [`written.py`](written.py) is the one place below lowering that looks inside types as the program wrote them,
  so that IR dumps and echo keep alias names.
- **Representations and slots** ([`layout.py`](layout.py)): each type's machine representation (a scalar, a pointer,
  a 16-byte record or variant value, or a generic `QVal` word for an unbounded type parameter's value) and its slot
  representation, one word in every aggregate, with records and variants boxed. Because every slot is a word, generic
  and specialized code agree on most layouts; [`generic_layout.py`](generic_layout.py) decides where they do not, and
  where a conversion would copy mutable data. `layout.type_tag` names structs and descriptors, and
  [`digests.py`](digests.py) tells apart the types a tag conflates.
- **Descriptors' type-level forms** ([`descriptors.py`](descriptors.py)): canonical forms of function and auto types,
  and the holes of descriptor templates that the describe pass instantiates at run time.
- **Object layouts** ([`objectlayout.py`](objectlayout.py)): for each allocation, which words are pointers, scalars,
  or ambiguous, so the precise collector can scan it.
- **Linked names and C text** ([`symbols.py`](symbols.py), [`syntax.py`](syntax.py)): the mangling of what units link
  against, and the spelling of C literals and repeated forms.

## How it differs from questlang/repr

The self-hosted package has three modules this one lacks, because the self-hosted compiler has backends besides C:

- `staticdata` (descriptor forms, record and offset-table names, static data's layouts) is here part of the C backend,
  in [`../codegen/c/types.py`](../codegen/c/types.py), since only the C printer needs it.
- `runtimelayout` (the runtime header's struct offsets and constants) exists for the arm64 backend, which cannot include
  a C header; the bootstrap's C includes `quest_runtime.h`.
- `externals` (the standard library's external C functions, built in so that importers call them directly) has no
  counterpart here.

A differential test (`tests/python/test_layout_differential.py`) checks this package's generic-layout decisions
against the runtime's `quest_layout_equivalent`.

## Further reading

- [`docs/ir.md`](../../../../docs/ir.md) §4: shapes and representations.
- [`docs/c-representation.md`](../../../../docs/c-representation.md): the runtime ABI these modules encode.
- [`docs/collector.md`](../../../../docs/collector.md) §3.2: object layouts.
- [`docs/name-mangling.md`](../../../../docs/name-mangling.md): linked symbols' C names.
