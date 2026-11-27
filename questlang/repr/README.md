# questlang/repr: how values are represented

This directory answers one question for the rest of the compiler: given a Quest type, what does a value of it look
like at run time? It turns types (from [`../types`](../types)) into *shapes*, decides each shape's machine
representation and memory layout, says when generic code lays a value out differently from specialized code, and
supplies the type-level forms of run-time type descriptors, the layouts the garbage collector scans, the runtime's own
struct layouts, and the names compiled units link against. It computes nothing about any particular program's control
flow; it is a library of decisions about types.

Two groups of clients use it. The IR's passes ([`../ir`](../ir/README.md)) consult it to decide where values must be
converted (the represent pass) and which descriptors operations need (the describe pass). The backends, the C printer
([`../codegen/c`](../codegen/c)) and the SSA builder ([`../ssa`](../ssa)) that feeds the arm64 backend, consult it
again to emit exactly the layouts the IR assumed. Keeping these decisions in one place shared by every backend is what
lets C code, native arm64 code, the C runtime ([`../../runtime`](../../runtime)), and serialized dynamic values agree
on one ABI.

## Shapes: types as a backend sees them

A Quest type as the type checker holds it may be an alias, an application of a type operator (`List(Int)`), or a
recursive type written in any of several equivalent ways. A backend cares about none of that. A *shape*
([`shapes.int.quest`](shapes.int.quest)) is the structural view: aliases stripped, operator applications reduced,
recursion made explicit as a cycle (the shape of `List(Int)` is an option whose `cons` payload's tail is that same
shape). `shape(t)` is computed from the canonical form of `t` and cached, so equal types, however written, share one
shape object. Its kinds are the scalars, `tuple`, `record`, `variant`, `option`, `array`, `fun`, `all` (a
polymorphic function), `auto`, `typevar` (a type parameter or a module's abstract type), `abstract`, `external` (an
opaque C type), and a few more. Code below lowering asks questions of shapes, never of types, because a structural
test on a type misses the same type reached through an alias.

Shapes lose alias names, which the IR's dumps and echo want to keep. [`written`](written.int.quest) is the one module
that looks inside types *as written*: the structure of a written type (so a component's type keeps its alias), a
function type's parameters and result, and what echo prints.

## Representations, slots, and layouts

[`layout`](layout.int.quest) gives every shape three related answers.

- Its **representation** is the class of machine value a variable of it holds (`Representation`): nothing for `Ok`;
  a 64-bit integer, byte, or real for scalars; a pointer for strings, tuples, options, arrays, and closures; two words
  for a record (its object and the offset table of the record type it is viewed at, which is how structural record
  subtyping works without copying) or a variant (its tag and payload); and a generic `QVal` word for a value of an
  unbounded type parameter.
- Its **slot representation** is how it is held inside an aggregate or a `QVal` word. Every slot is exactly one word:
  a record or variant is stored as a pointer to an immutable 16-byte box, a `Bool` or `Char` as a word of its own. The
  `WordForm` says how every backend converts a value to and from its word.
- Its **layout**: the byte offsets of tuple components, record fields, and option payloads (`tupleBytes`,
  `recordFieldOffset`, `optionBytes`), as C lays them out on a 64-bit target, so that a backend that is not C lays out
  the same structs.

The one-word-slot rule is the key design choice. Quest compiles a polymorphic function once, holding values of a type
parameter as `QVal` words. Because every slot is a word, a `Tuple x: Int p: Point end` built by specialized code has
the same memory layout as the generic `Tuple x: A p: B end` that polymorphic code reads, so passing it needs no copy:
the represent pass inserts a `cast`, not a conversion. Where layouts still differ (a closure among the components
whose calling convention changes with its types), [`genericlayout`](genericlayout.int.quest) says so:
`genericLayoutAgrees` decides whether a native layout and a generic one agree, mirroring the runtime's
`quest_layout_equivalent`, and `genericLayoutCopiesMutableData` detects a conversion that would copy mutable data,
which the represent pass rejects at compile time because the copy would not share later updates. The same module lays
out applications of a module's abstract type operators as seen from outside the module.

Values can also be *proxies*: when a tuple or option is used at a supertype at which a component's representation
changes (a record field viewed through a different offset table, say), the runtime wraps the original object in a
view rather than copying it, so that identity and mutable components are preserved. `layout.mayBeProxied` says which
shapes may be proxies, which the IR's slots step uses to decide how each component read must check.

`layout.typeTag` names a type's C struct and descriptor deterministically; where two different types would get the
same tag, [`digests`](digests.int.quest) adds a short hash of the type's printed text.

## Descriptors and static data

Quest cannot erase types: `Dynamic`, auto values, `inspect`, and echo need them at run time, as does generic code that
must convert values. A *descriptor* is the runtime's data structure for a type. [`descriptors`](descriptors.int.quest)
gives their type-level forms: canonical forms of function and auto types (parameter names dropped, type parameters
replaced by de Bruijn-indexed placeholders) so that equal types share a descriptor, and the *holes* of descriptor
templates, which the IR's describe pass instantiates at run time with the descriptors of type parameters in scope.

[`staticdata`](staticdata.int.quest) is the backend-facing side: for each type, the form of its descriptor
(`descriptorForm`: a base descriptor the runtime defines, or one the unit emits, `quest_type_<tag>`), the names of
record structs and their offset tables (`RecordNaming`), and the layouts of a unit's static descriptors, offset tables,
and tag maps. The C backend spells these in C; the SSA's backends lay them out as data themselves.

## What the backends and the runtime need

- [`objectlayout`](objectlayout.int.quest): for every object compiled code allocates, a `Layout` saying for each word
  whether it is a pointer, a scalar, or ambiguous (a `QVal` of generic code). The precise collector
  ([`../../runtime/quest_gc.c`](../../runtime/quest_gc.c)) scans objects by these, and `QUEST_GC_CHECK=layouts`
  checks them.
- [`runtimelayout`](runtimelayout.int.quest): a table of the offsets and sizes of the structs in
  `runtime/quest_runtime.h` that generated code touches, and the header's constants, for the arm64 backend, which
  cannot include a C header. A test prints the table as C assertions and compiles them against the header.
- [`symbols`](symbols.int.quest): name mangling, so that units compiled by any backend link with one another and with
  the runtime (`mangleModuleName`, `mangleModuleIdent`).
- [`syntax`](syntax.int.quest): the spelling of C literals and repeated C forms, used by the C backend and by the
  modules here that produce C text.
- [`externals`](externals.mod.quest): a table, generated from `lib/` by `tools/externals`, of the standard library's
  members defined as external C functions and its external types, so that an importer calls the C function directly.
- [`externalFunctions`](externalfunctions.int.quest): that table's functions as typed rows, and the lookup the
  backends make of a library member's C symbol.

## Connections

Below this directory are [`../types`](../types) (types, canonical forms, substitution); above it, every user listed
above: [`../ir`](../ir/README.md) (lower, specialize, represent, slots, describe, thunks),
[`../codegen/c`](../codegen/c), [`../ssa`](../ssa) (especially `ssa/build` and `ssa/statics`),
[`../codegen/arm64`](../codegen/arm64), and [`../modules`](../modules) (the externals table during elaboration).
The bootstrap compiler's counterpart is
[`bootstrap/python/quest/repr`](../../bootstrap/python/quest/repr/README.md), which has the same modules except
`staticdata` (in the bootstrap, part of its C backend), `runtimelayout`, and `externals`.

## Further reading

- [`docs/ir.md`](../../docs/ir.md) §4: shapes and representations as the IR uses them; §8.3–§8.4: the passes that
  consult this directory.
- [`docs/c-representation.md`](../../docs/c-representation.md): the runtime ABI these modules encode (§3 the `QVal`
  word, §5 aggregates and proxies, §6.4 descriptors and generic layouts).
- [`docs/collector.md`](../../docs/collector.md) §3.2: object layouts and how the collector uses them.
- [`docs/arm64.md`](../../docs/arm64.md): how the native backend lays out data without C.
- [`docs/name-mangling.md`](../../docs/name-mangling.md): the C names of linked symbols.
