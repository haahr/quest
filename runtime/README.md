# runtime: the C runtime of compiled Quest

Every compiled Quest program, whichever compiler and backend produced it, is linked with the C code in this
directory. The compilers emit only the program's own code; everything that code relies on but does not generate
lives here: how values are laid out in memory, allocation and the garbage collector, raising and catching
exceptions, run-time descriptions of types, printing, serialization of dynamic values, and the C functions behind
the standard library. The self-hosted compiler is itself a compiled Quest program, so its driver contains this
runtime too, and the JIT's machine code, loaded into the driver while it runs, calls the driver's copy.

The directory is flat: about 12,000 lines in 17 files. [`quest_runtime.h`](quest_runtime.h) is the interface that
generated code includes; it includes [`quest_types.h`](quest_types.h) (type descriptors) and [`quest_gc.h`](quest_gc.h)
(the collector). [`quest_runtime_internal.h`](quest_runtime_internal.h) declares what the runtime's own files share
but compiled code does not see. The rest are implementation files, one per concern, described below.

## How it is built and linked

The build compiles the runtime's C files with the system's C compiler, caches the objects under a key computed from
the contents of every file here, and links them with each program (`runtimeSources` in
`questlang/build/compilerrunner`). A compiled program's `main` first calls `quest_gc_init` and `quest_builtins_init`
(standard streams, `system.args`, the stack-overflow guard), then initializes each unit, which registers what the
runtime needs to know about it: its global roots for the collector, its function table for tracebacks, its record
offset tables, and its modules' abstract types.

The header is part of the *ABI*, the contract between separately compiled units: an object file or interface
artifact is reused only by a compiler with the same `ABI_VERSION`, and a test records a digest of the three headers
so that changing them without bumping the version fails. Native backends emit machine code rather than C, so they
cannot include the header; the self-hosted compiler mirrors its structs and constants in `questlang/repr/runtimelayout`,
which a test checks against it. Both compilers' output uses the same runtime, so a change here must keep the
bootstrap's C working too.

## The representation of values

Every value fits a 64-bit word, `QVal`, or a pair of them. An `Int`, `Real`, `Bool`, or `Char` is the word itself.
A string (`QString`) is a header with a length and a pointer to NUL-terminated bytes. An array is a length followed by
words. A closure (`QClosure`) is a pair of a C function and an environment of captured variables; calling it passes
the environment first, then the descriptors of its type arguments, then its arguments.

Structural subtyping is what makes the layout interesting. A record of type `Record a: Int b: Int c: Int end` may be
passed where `Record b: Int end` is expected, and the code that receives it cannot know where `b` is. So a record value
(`QRecordVal`, 16 bytes, passed in a register pair) is a pointer to its payload, whose fields are sorted by name,
together with an *offset table*, the byte offset of each field of the type the value is currently seen at. Code reads
field *i* at `payload + table[i]`, and viewing a record at a supertype changes only the table, never the payload. The
tables are cached by pair of (view, layout) descriptors in [`quest_views.c`](quest_views.c); compiled code registers its
own statically and the rest are computed on demand. Variants carry a tag that each variant type numbers on its own, so
viewing one at a supertype renumbers the tag (`quest_variant_adapt`).

Inside any aggregate, every component takes exactly one word, a record or variant being a pointer to a box: a tuple
of a record and an `Int` has the same layout as a generic `Tuple A B end`, so polymorphic code can take it without
copying. A tuple or option used at a supertype whose components change view is not copied either; the value becomes
a *proxy*, a tagged pointer (low bit set) to a `QProxy` that holds the original and the two descriptors, and reads
through it convert each component (`quest_convert`) as they are read.

## Type descriptors

Most of a program's types vanish in compilation, but some operations need a value's type at run time: `dynamic.be`
and `inspect` test subtyping, generic code converts between layouts, the REPL prints results, and `dynamic.extern`
writes the type with the value. A *type descriptor* (`QTypeDescriptor`, [`quest_types.h`](quest_types.h)) is a type
described as data: its kind (record, tuple, variant, function, auto, opaque, ...), a name for display, and per-kind
metadata such as a record's fields with their types and offsets. Compiled code emits descriptors statically and
passes them as the hidden arguments of polymorphic functions (dictionary passing, in effect); a recursive type's
descriptor is a cyclic graph. Inside generic code, a type built from type parameters is a *template*, a descriptor
with holes that `quest_instantiate_descriptor` fills with the actual arguments. [`quest_types.c`](quest_types.c)
holds the base types' descriptors and `quest_is_subtype`, which compares descriptors by structure, with a trail of
pairs under comparison so that recursive types terminate. A module's abstract type is opaque, identified by its global
name; each module registers its representation (`quest_register_abstract_type`) for the dynamic format.

## The collector

[`quest_gc.c`](quest_gc.c) is a non-moving, generational, mark-region collector in the Immix style. The heap is one
reserved range of 32 KB blocks divided into 128-byte lines; allocation bumps a cursor through a run of free lines
(a *hole*), which the inline fast path in [`quest_gc.h`](quest_gc.h) and the native backends' inline sequences do
without a call. Every object is preceded by a header word naming its *layout*, which says of each word whether it is
a pointer, a scalar, or ambiguous (a `QVal` of generic code, which may be either), so the collector scans precisely
where it can and conservatively elsewhere. Pointer-free objects go to a space of their own that is never scanned.

Generations use sticky mark bits: only a full collection clears marks, so objects allocated since the last collection
are exactly the unmarked ones, and a minor collection marks and sweeps only those. For that to be sound, compiled
code calls a *write barrier* after storing a pointer into an existing object (`quest_barrier`, `quest_barrier_slot`),
which records an old object or card that may now point to a young one. Roots are each unit's registered global
slots, the runtime's own statics, the JIT's data regions, and the stacks: arm64 frames precisely, by the frame tables
the backend registers, and other frames conservatively. A long full collection is replaced next time by incremental
marking in slices. `quest_gc_hold` holds collections off while the runtime builds a structure with stores between its
allocations. `QUEST_GC_CHECK` selects checking modes that verify layouts, roots, and barriers in the test suites.

## Exceptions

[`quest_exceptions.c`](quest_exceptions.c) implements Quest's `raise` and `try`. An exception is a `QException`
identified by its address, since each evaluation of an exception declaration makes a new one. Each active `try`
pushes a `QExceptionHandler` on a thread-local stack. A raise (`quest_reraise`, where every raise ends up) first
searches the stack to see whether anything will catch the exception, since tracebacks can be read only from the live
stack before it unwinds: if nothing will, it prints the exception, the raise site, and the frames, and exits; if a
handler might re-raise it, it captures the frames first. Then it transfers control to the innermost handler, by
`longjmp` for code compiled through C, or for arm64 code by restoring the handler's stack and frame pointers and
branching to its resume address. Frames are named through the function tables each unit registers
(`quest_register_funcs`). A fault handler, running on a stack of its own, reports a fault at the stack's low end as an
uncaught `stack.overflow`, with the frames running.

## Dynamic values and printing

A dynamic value is an auto value (`QAuto`): a descriptor paired with its components.
[`quest_serialization.c`](quest_serialization.c) writes and reads them in the dynamic format, a JSON document of a
type table and a value, following the descriptors, with shared and cyclic objects written once. Its type table is
canonical, so its text is byte for byte what the interpreters' writers produce
([`questlang/values`](../questlang/values/README.md)). [`quest_print.c`](quest_print.c) prints a value by its
descriptor as the interpreters print it, for echoed results and uncaught exceptions' payloads, and formats reals with
the shortest digits that read back as the same value.

## The standard library's externals

The standard library in `lib/` is written in Quest, but its primitives are declared `external` and bound to C
symbols: `string.getChar` is `external "quest_string_get_char"`. Those functions are here:
[`quest_runtime.c`](quest_runtime.c) has strings, arrays, reals, the built-in operators as closures, and the runtime's
roots; [`quest_stdlib.c`](quest_stdlib.c) has readers and writers, conversions, string builders, `ascii`, words, and
hashing; [`quest_os.c`](quest_os.c) has `system`, `os/fileStats`, and `os/process` (arguments, environment, files,
processes) and the Jupyter kernel's interrupts; [`quest_readline.c`](quest_readline.c) has `io/readline`'s line
editing and history. Each raises its module's exception (`string.error`, ...) on failure. The self-hosted
interpreter's builtins call these same functions, which is why interpreted and compiled programs behave alike;
the bootstrap's interpreter reimplements them in Python. [`quest_inline.c`](quest_inline.c) gives the header's
inline helpers external definitions, for machine code that cannot inline them.

## Code loading

[`quest_code.c`](quest_code.c) implements the two unsound library modules the JIT is written on, `os/value` (any value
as a raw word, and reading and writing memory) and `os/code`: reserving executable regions (Darwin's `MAP_JIT`, placed
near the runtime's own text so that the loaded code reaches it by PC-relative addressing), writing instructions into
them, looking up the driver's symbols with `dlsym`, calling loaded code under an exception handler, registering the
loaded code's data as collector roots, and the GDB JIT interface through which lldb sees loaded code. The JIT
itself, in `questlang/jit`, encodes and links the code; the runtime only provides these primitives.

## Further reading

- [docs/runtime-design.md](../docs/runtime-design.md): the runtime's design in overview, and why Quest's types make
  it subtle.
- [docs/c-representation.md](../docs/c-representation.md): the representation of every kind of value, descriptors
  (§6.4), exceptions (§7), and the runtime's functions (§10).
- [docs/collector.md](../docs/collector.md): the collector's design (§3) and checking modes (§7).
- [docs/exceptions.md](../docs/exceptions.md) §5 and §6: tracebacks and stack overflow in compiled code.
- [docs/dynamic.md](../docs/dynamic.md): the dynamic format.
- [docs/jit.md](../docs/jit.md) §3.6 and §3.11: the loader and the unsound primitives.
- [docs/arm64.md](../docs/arm64.md): how the native backend calls the runtime and cooperates with the collector.
- [docs/libraries.md](../docs/libraries.md): the standard library's modules.
