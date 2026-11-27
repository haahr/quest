# questlang/jit: compiling and running code in the compiler's own process

The self-hosted driver runs Quest code without writing a binary: the REPL's inputs, `quest -e PROGRAM`, and
`quest FILE` are compiled to arm64 machine code inside the running driver, loaded into its memory, and called. This
directory is what makes that possible. It sits after the whole compiler: an input is parsed and type-checked as the
REPL always does ([`../driver/repl`](../driver/repl.mod.quest)), lowered to the IR, and compiled through the IR's
passes, the SSA ([`../ssa`](../ssa)), and the arm64 backend ([`../codegen/arm64`](../codegen/arm64/README.md)) exactly
as `--backend arm64` would compile it. Only the last steps differ: instead of writing assembly and calling the
assembler and linker, the backend's encoder produces machine words with relocations, and the loader here places them
in executable memory and resolves their symbols. `--no-jit` runs the tree-walking interpreter
([`../interpreter`](../interpreter)) instead.

The compiled code shares everything with the driver: its heap and collector, the runtime, and the library. A phrase
that imports `util/strutil` uses the driver's own copy of that module, its code and its state; the driver is the
library.

## Inputs as modules

[`session`](session.int.quest) holds the state of a sequence of inputs, and `session.run` compiles, loads, and runs
one. The central idea is that **each input is compiled as a module of its own**. Input *n* becomes a *phrase unit*
(lowered by `ir/lower`'s `lowerPhrases`) whose top-level code is the initializer of a module `qj_<n>`, and whose
top-level bindings are the fields of that module's record. A later input that names an earlier binding imports the
earlier input's module and reads the binding as a member of its record, as any compiled unit reads another module's
member. For

```quest
let x = 1                      (* input 1: module qj_1, record {x} *)
let f(n: Int): Int = n + x     (* input 2: module qj_2, imports qj_1, record {f} *)
f(41)                          (* input 3: imports qj_2, calls f through its closure *)
```

each input compiles only itself; the code of earlier inputs stays loaded. This reuses what the compiler already
guarantees for modules (a member keeps the representation its record's layout fixes) rather than asking every pass to
keep top-level variables alive in an agreed form. The session remembers, for each binding of an input that ran, which
module holds it and in which field (`lower.Earlier`), and passes that to the next input's lowering.

Interactive inputs may *redefine* a function in place: after `let f() = 1; let g() = f(); let f() = 2`, `g()` is 2,
as in the interpreter. To allow this, a top-level binding in an interactive input is held in a *box* (a one-word
mutable cell) that the record's field points to, and every use loads the box when it runs; a redefinition stores into
the existing box. The cost is that such a function is always called through its closure, never inlined.

An input that raises an exception reports it as an `Outcome` (its name, where it was raised, and the frames running
there) rather than ending the driver; its bindings are forgotten, so no later input reads its record.

## Targets

What the session needs of a target is [`target`](target.int.quest): compiling and loading a unit, running an
input's entry point, and asking for the driver's built-in modules and their fingerprints. The build picks one of
three implementations by module variant ([docs/build-process.md](../../docs/build-process.md) §6.4). The default,
`target.mod.quest`, compiles to arm64 and loads into the driver's process through `loader`, as the rest of this
README describes; `target.wasm.mod.quest`, for a driver that itself runs on WebAssembly, compiles each unit with the
wasm backend and hands its bytes to the host to instantiate and run ([docs/wasm.md](../../docs/wasm.md) §6.1); and
`target.none.mod.quest` has no JIT, so the driver interprets its inputs (the wasmtime-hosted driver, which has no
host to load modules).

## The driver as the library, and its limits

An input's references to library modules resolve to the driver's own symbols. That only works if the driver's
compiled modules match the interfaces the JIT compiles against, which can fail when a binary is run against a source
tree it was not built from. So every compiled module exports a fingerprint of its interface (a SHA-256 digest of what
compiled code depends on, made by `modules/artifacts/fingerprint`), and the session checks it before using a module,
refusing the import if it differs. `session.refusal` reports a driver that cannot host the JIT at all, one whose
modules carry no fingerprints. A user's own module file, which the driver does not link, is compiled from source and
loaded once in a session, after the module files it imports.

## Loading code

[`loader`](loader.int.quest) does a linker's and a dynamic loader's work in memory. A session reserves a 128 MB arena
for code, so that `bl`, arm64's call instruction, which reaches 128 MB in either direction, can reach any loaded
function from any other, and a separate region for data. Each unit is placed after the last, and its relocations are
resolved against its own symbols, those exported by units loaded before it, and the driver's (found with `dlsym`).
The driver's code may lie out of a `bl`'s reach, so a reference to a driver symbol goes through a *GOT slot* (a word
holding the symbol's full address) and, for a call, a small stub in the arena that jumps through it. Each unit's data
is registered as a root of the collector, and each function's code is registered so that stack frames in it can be
named in tracebacks. Nothing is ever freed.

Quest's type system cannot check any of this: making memory executable and calling an address are unsafe. The
primitives live in `lib/os` (`os/value`, `os/code`) behind interfaces marked `unsound`, and `loader` and `session`
are `unsound` modules, the scheme *Typeful Programming* gives for low-level code: only an unsound module may import
an unsound interface.

## Debugging JIT code

With `QUEST_JIT_DEBUG=1`, the session describes each loaded unit to lldb. [`debugobject`](debugobject.int.quest)
builds, in memory, a Mach-O object file whose code section is the unit's code at the address it was loaded at (so
nothing needs relocating), with a symbol for each function and DWARF line tables from the encoder's source positions.
The session hands it to the debugger through the GDB JIT interface, a protocol by which a program announces in-memory
object files to an attached debugger, and writes each input's source to a file the line table can name.

## Further reading

- [docs/jit.md](../../docs/jit.md): the JIT's decisions (§1), pipeline (§2), phrase units (§3.2), fingerprints
  (§3.3), module files (§3.4), the encoder and loader (§3.5–3.6), unsound interfaces (§3.11), debugging (§3.12),
  and its differences from the interpreter (§4)
- [docs/repl.md](../../docs/repl.md): the REPL that drives it, and redefinition (§6)
- [docs/arm64.md](../../docs/arm64.md): the backend it shares
