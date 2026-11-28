# questlang/codegen/c: the C backends

This directory holds the two backends that write C, and the pieces of C that other parts of the build need. The **C
printer** takes a unit from the end of the IR's pipeline (`ir_described`, the output of [`../../ir`](../../ir)'s
describe pass) and prints it as one C file, which the build engine ([`../../build`](../../build)) compiles with clang
and links against the runtime ([`../../../runtime`](../../../runtime)). **ssac** takes the same unit after it has been
built into SSA ([`../../ssa`](../../ssa)) and prints that as C instead. [`../backend`](../backend.int.quest) chooses
between them (and arm64) for each unit; see [`../README.md`](../README.md).

## The C printer: printing decisions, not making them

By the time a unit reaches [`printer`](printer.int.quest), every decision about how values are represented has been
made and recorded in the IR: which values are boxed, which conversions a subtyping coercion needs, which reads of a
tuple may go through a proxy, which run-time type descriptor each polymorphic operation receives. The printer only
spells those decisions in C. This keeps the hard work in passes the native backends share, and keeps the printer a
long but straightforward walk over the IR (`printC`).

The mapping is direct. Each IR function becomes a C function whose first parameter is its closure's environment,
followed by the descriptors of its own type parameters and then its ordinary parameters. A closure is a `QClosure`,
a code pointer and an environment, static when it captures nothing. IR variables are C locals of their type's
representation (`QInt`, a struct pointer, a `QVal` word), and the variables a top level binds outside loops are C
globals, registered with the collector as roots. The IR's structured statements are C's: a *join point* (a labelled
continuation that several branches jump to, the IR's way of sharing code after an `if` without duplicating it)
becomes a label and `goto`s; a `try` becomes a handler record and `setjmp`, popped on every way out of the region.
The recursive factorial

```quest
let rec fact(n: Int): Int = if n is 0 then 1 else n * fact(n - 1) end
```

prints as `static QInt qf_fact(void *_raw_env, QInt l_n)` with an `if` whose arms `return`, plus a static closure
`qf_fact_closure` that the global `g_fact` holds. A module file's unit also exports its interface's members in a
fixed ABI that other units link against: the module's record `qm_<module>`, its initializer `qv_mod_<module>_init`,
and a direct C function `qv_<module>_<member>` for each function or polymorphic value.

The printer is one large module because its sections (names, types, descriptors, proxies, aggregates, conversions,
calls, statements, functions, the unit) share its state, the per-unit `P` and the per-function `FnState`;
[docs/compiler-organization.md](../../../docs/compiler-organization.md) §7 explains why it is not split. It numbers
names and temporaries in the bootstrap's order, so the two compilers' C stays comparable.

## Declarations: what C needs before the code

Quest's structural types become C structs, and its subtyping becomes static tables.
[`declarations`](declarations.int.quest) writes everything that precedes the functions, each emitter returning lines
of C:

- **Aggregate structs.** Every tuple, record, option, and variant type the unit reaches gets a struct, named by a
  deterministic tag of its type, so that two units that mention the same structural type name the same struct.
- **Offset tables** ("evidence dictionaries"). A record seen at a supertype may be any record with at least those
  fields, at unknown offsets. Code that knows only the supertype reads a field through a table of the field's byte
  offset in the actual record's struct; the declarations define one static table for each (view, layout) pair the
  unit uses ([docs/c-representation.md](../../../docs/c-representation.md) §5.2).
- **Coercion tables.** A tuple used at a supertype needs no copy when its first components are at the same offsets,
  which static assertions check; a variant's tags are renumbered by a table from the subtype's to the supertype's.
- **Type descriptors.** The static descriptors that polymorphic code, `Dynamic` values, and printing read at run time.
- **Function type adapters.** For each function type with a descriptor, a thunk that converts arguments and results
  by descriptor, so that a closure can be called where its type is known only at run time.

The `Emitter` remembers what it has emitted, so that one unit never defines a struct or descriptor twice.
[`types`](types.int.quest) is the vocabulary all of this is spelled in: the C type of a representation, a value
wrapped as a `QVal` word and unwrapped, a record or variant stored in a one-word slot (boxed) and loaded back, and a
closure's function-pointer type. The layouts themselves come from [`../../repr`](../../repr), which the native
backends use too.

## Interface headers

When a C unit imports a module, it needs that module's structs and member signatures. [`headers`](headers.int.quest)
writes an interface's C header (`.int.h`), from the compiled interface, with its aggregate structs, its types' C
representations, and its members' signatures; [`../../build/interfaceHeaders`](../../build/interfaceheaders.int.quest) writes it beside
the interface's `.qi` file when a C compilation needs it. The arm64 backend reads layouts from interfaces directly and
needs no headers.

## ssac: the SSA printed as C

[`ssac`](ssac.int.quest) prints the SSA, not the IR, and so works at a much lower level: each block is a label, each
SSA value a local, a block's arguments are assignments before its `goto`, and memory is reached by byte offsets
(`*(int64_t *)(p + 16)`). It computes no layout and includes no header: every symbol the unit does not define is
declared as an array of bytes, and each call goes through a function pointer of the types its arguments have, so that
clang applies the C calling convention. Its C is compiled with extra flags (`ssac.cFlags`: GNU C, no type-based
aliasing). Because it shares everything with the arm64 backend up to instruction selection, it is an oracle for the
SSA and its passes, much as MLton's C backend prints its lowest IR.

## Counterpart in the bootstrap

[`bootstrap/python/quest/codegen/c`](../../../bootstrap/python/quest/codegen/c/README.md) has the printer,
declarations, headers, and C spellings, module for module, but not ssac.

## Further reading

- [docs/codegen-c.md](../../../docs/codegen-c.md): the C backend's translation of each construct
- [docs/c-representation.md](../../../docs/c-representation.md): the C representation of Quest's values and the ABI
- [docs/ir.md](../../../docs/ir.md) §8.3–8.5: the represent and describe passes, and printing C
- [docs/arm64.md](../../../docs/arm64.md) §3.14: the SSA-to-C printer
- [docs/build-process.md](../../../docs/build-process.md) §5: interface headers and when they are rewritten
