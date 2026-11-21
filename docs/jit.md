# The arm64 JIT

Step 7 of the [roadmap](roadmap.md): the self-hosted driver compiles each REPL input, `-e` program, and file it runs
to arm64 machine code in its own process, links it against the units already in the driver, and runs it, instead of
interpreting it. It uses the arm64 backend's pipeline ([arm64.md](arm64.md)) unchanged up to machine instructions, and
replaces the assembler and linker with an in-memory encoder and loader. It is written in Quest, in `questlang/jit/`
and `codegen/arm64/encode`, and the bootstrap does not have it ([testing.md](testing.md) §2.8), though it has the
language change the JIT needs (§3.11). What remains open is in §6.

---

## 1. Decisions

- **What runs on it.** The REPL, `-e`, and files (`quest FILE`, and `-i FILE`) run on it by default; `--no-jit`
  interprets instead (§3.10).
- **The same process,** sharing the driver's heap, runtime, and library state.
- **The driver is the library.** A phrase that imports a unit linked into the driver uses the driver's copy of it, its
  code and its state: `writer.output` is the compiler's own, and a phrase that imports `questlang/...` modules
  reaches the running compiler's. The circularity is intended.
- **Straight to an encoder.** No stage that writes `.s` and shells out to `as` and `ld` to make a dylib: `minst`
  already makes instructions data, so the encoder replaces the assembler from the start (§3.5).
- **The interpreters' semantics.** Interactive code redefines in place ([repl.md](repl.md) §6): a top-level `let` of
  a name's type updates the code that already uses it, so `let f() = 1; let g() = f(); let f() = 2; g()` is 2, in
  the interpreters and here; any other rebinding shadows, and programs, `-e`, and files scope lexically. Beyond that
  there is no hot-swapping (a redefinition with another type, or of a type); the roadmap's "dynamic patching and
  hot-swapping" is dropped. The REPL's output stays the interpreter's.
- **Incremental** means that an input compiles only itself; what earlier inputs compiled stays loaded.
- **A crash ends the session:** a fault or a runaway recursion in a phrase ends the driver as it ends a
  compiled program (exceptions.md §6). Ctrl-C likewise, except in a Jupyter kernel's driver (`--kernel`), where the
  JIT's code checks for an interrupt and it ends only the cell ([jupyter-kernel.md](jupyter-kernel.md) §5); only
  the kernel pays for the checks. Surviving faults and runaway recursion is open work (§6).
- **Self-hosted only,** and **runs in a binary built by either backend**: the JIT, and the code it writes, run in a
  binary whose units the C backend or the arm64 backend compiled (`QUEST_BACKEND=c` or `arm64`, for the driver). The
  host's units are reached only through the C ABI that both backends' objects share (§3.10).
- **The same pipeline** as `--backend arm64`, with its optimizations, within an input. No separate fast path.
- **A host unit that does not match its source is refused:** importing it is an error, never a second copy compiled
  from source (§3.3).
- **Frames by the frame-pointer chain,** for all compiled code, not only the JIT's (§3.9).
- **Results printed by the runtime's own formatter,** as a compiled program prints them, not by the interpreter's
  formatter from values read back by reflection, which could not follow proxies or show `Dynamic` values without
  redoing the runtime's work (§3.8).
- **The low-level primitives live in `os/`,** named for what they do rather than for the JIT, behind interfaces
  marked `unsound`: Cardelli's scheme, which the language enforces (§3.11), with `external` an unsound
  operation (§3.11, "Externals").
- **`os/value` is Cardelli's `Value`,** signature and all; what it lacks is in `os/code` (§3.11).
- **Neither interpreter runs `os/value` or `os/code`** (§3.11).
- **Differences from the interpreter** are accepted and documented (§4).
- **Kept simple** (after a review for complexity):
  - every separately compiled binary can host the JIT, with no host link mode, given one fingerprint symbol per module
    unit (§3.3, §3.10), a fingerprint of what JIT code depends on and nothing else (§3.3.1);
  - the driver links all of `lib/`, so the JIT compiles from source only the user's own module files (§3.4);
  - the transcripts that show an accepted difference are skipped under `--jit` rather than given goldens of their own
    (§5);
  - a phrase unit is a unit kind of its own (`nodes.Phrase`), whose top level is the initializer of a module of its
    own, whose record holds its bindings (§3.2).

## 2. Pipeline

```
input text ──parse, typecheck (as the REPL does: env, unit graph, snapshots)──► typed phrases
   ──lower as a phrase unit (§3.2)──► IR ──passes──► SSA ──select, allocate──► minst
   ──encode (§3.5)──► code and data with relocations ──load (§3.6)──► executable memory
   ──call the input's entry (§3.7)──► results printed by the runtime (§3.8)
   ──captured, for the REPL──► "==  ..."
```

Everything up to minst is the arm64 backend's, given a kind of unit of its own. The encoder, the loader, and the
REPL's use of them are the JIT's. An input of the REPL transcripts takes 0.2 to 1.5 ms to compile, load, and run
([benchmarks.md](benchmarks.md) §10, 2026-11-01).

## 3. Design

### 3.1. Where the JIT lives

- `questlang/jit/`: `loader` (the code arena, symbol resolution, relocation, registration), `target` (compiling a
  unit and loading it, calling an input's entry, the driver's units and their fingerprints), and `session` (the
  REPL's state: earlier inputs' records); the encoder is `codegen/arm64/encode`. `target` is what differs by
  machine: its own file is arm64's, and its variants ([build-process.md](build-process.md) §6.4) are WebAssembly's
  (`target.wasm`, [wasm.md](wasm.md) §6.1) and none (`target.none`, no JIT). The modules that use the
  unsound primitives are `unsound` modules.
- Two unsound interfaces in `lib/os/`, with a C file in `runtime/`, for what Quest cannot do (§3.11).
- `driver/repl` chooses between `treewalk.evalProgramPhrasesIn` and the JIT for its running step; snapshots, rollback,
  completeness, and printing stay its own.

### 3.2. Inputs as units

Each input (one or more phrases, `let x = 1; let y = 2; x + y`) is compiled as one **phrase unit**, a unit kind of its
own beside program and module units (`nodes.Unit.phrase`, a `nodes.Phrase`: the input's number and whether its
results are captured, §3.8). The session numbers inputs from 1, and every name a unit defines that another unit can
see carries its number.

**An input is a module of its own.** `lower.lowerPhrases` lowers the phrases as `program()` lowers a program's,
into the initializer of a module named for the input, `qj_<n>`. The module's members are the input's top-level
value bindings, each a field `v<symbol>` named for its symbol's number. When the phrases have run, the initializer
makes the module's record, with a `var` field for each `var`, and the unit exports it as `qm_qj_<n>`; a later
input reaches the input's bindings only through that record. For the REPL's inputs

```quest
let x = 1                 (* input 1 *)
let var count = 0         (* input 2 *)
let f(n: Int): Int = n + x
count := f(count)         (* input 3 *)
```

input 1's unit is a module `qj_1` with one member, `x`, and a record `{v<x> = 1}`; input 2's is `qj_2`, whose
record holds `count`, a `var` field, and `f`'s closure; `f`, compiled in input 2, reads `x` as a member of
`qj_1`, which input 2 imports. Input 3 imports `qj_2` alone: it reads `f` as a member of it, `count` through its
field's address, and stores the result into that field.

Why a module: a module's members are what the compiler already keeps whatever its passes do, and a member's
representation is the one its record's layout fixes (an imported member is read by its record's offset table, at
its index in name order, in its slot form). A global per binding, the first design, would have needed every pass to
keep each top-level variable alive and in a representation that later units agree on, which nothing in the compiler
ensures.

- **Namespaces stack.** An input sees every binding of the inputs before it, as the interpreter's frames do; the type
  checker's environment already provides that. The session keeps, for each symbol an input that ran bound, where it
  lives (`lower.Earlier`: the module whose record holds it, its field, the record's type, whether it is a `var`, and
  whether it is a slot's box), and passes them to the next input's lowering. A slot's is kept once, by its first
  symbol, and looked up through the environment's `slots` (`lower.slotOf`).
- **Reading an earlier binding.** In a later input, a variable whose symbol the input does not bind and the session
  knows is a member of that module: the input imports the module as a unit imports any module (a `nodes.Import` of
  `qj_<n>`, with the record's type), and reads the binding as an `opModuleMember`. A top-level function is reached
  through the field holding its closure; calling its code directly, or inlining it, is open work (§6).
  Rebindings are distinct symbols already (ir.md §2), so they are distinct fields; a redefinition is not a rebinding
  (below).
- **Writing an earlier `var`.** Global `var`s cannot be captured by functions (the rule the REPL already reports), so
  an earlier input's `var` is read and written only by later top-level code: through its field's address
  (`opAddrField` on the record) and with a store to the field (`sStoreField`). The field is in the record's payload,
  which every copy of the record shares, so a write is seen by every later input.
- **Slots are boxes.** In an interactive input (the REPL's, or the file `-i` runs), every top-level value binding is
  a slot ([repl.md](repl.md) §6), and the phrase unit holds it in a **box**, the one-component `var` tuple the
  lowering uses for a local `var` that closures capture (`lower.boxesSlot`, `l.boxes`). Defining a slot makes its box,
  and the record's field `v<slot>` is the box (`Earlier.boxed`). Every use loads the box's component when it runs: the
  input's own uses (closures capture the box), and a later input's, through the record. A redefinition stores to the
  box, its own input's or an earlier one's, and adds no field. So a slot's symbol is never a known callee: its
  function is called through its closure, never inlined, specialized, or called directly, which is what redefinition
  costs ([repl.md](repl.md) §6). New recursive functions are made with their boxes in one `let rec` (`recSlots`), so
  that their bodies, which name their slots, read the boxes; a simultaneous `let ... and ...` computes every member's
  value before storing any. A slot of type `Ok` has no box, and a recursive value that is not a function names its
  group's members directly. A box's loads are ordinary loads of a `var` cell, which the SSA's passes do not take as
  invariant. A failed input's stores to earlier boxes stay, as its assignments do.
- **What is not a field.** A binding of type `Ok` has no words, so it is not in the record, and a later input reads
  it as `ok`. A named exception is a field when a phrase declares it (`exception E end`); one a `let` binds is the
  `let`'s value, its field.
- **Modules an input declares** (`module k: I export ... end`) are part of its unit, as a program's are. Their names
  begin with the input's (`qj_<n>_k`), so that each input's are its own (the REPL allows `module k` twice), and their
  records are exported, so that a later input that names `k` imports its record. So, likewise, are the modules an
  input imports: a later input that names one imports it by its own record (`qm_<module>`, the driver's).
- **The entry** (`qj_<n>_entry`) is a function of no arguments: it registers the unit's dictionaries and function
  table, calls its imports' initializers (each guarded, so the driver's already-initialized modules, and earlier
  inputs', return at once), and its modules', the input's own last. Unlike a program's `main`, it does not
  initialize the collector or the builtins. With capture (§3.8) it starts the capture first and leaves the captured
  text in `qj_<n>_echo` last.
- **An input that fails** raises before its initializer makes the record. The REPL forgets its bindings (the
  environment rolls back) and the session records none of them, so no later input reads its record; its code and
  data stay loaded, unused. A write it made to an earlier input's `var` stays, as in the interpreter.
- **What a user sees of it:** nothing, but in a debugger. Tracebacks name a declared module by the name it was
  declared with (`k.<init>`) and the input's top level `<main>`, as the interpreter's do (§3.9), and diagnostics never
  name the modules. The SSA builds no direct-call adapters (`qv_qj_<n>_<field>`) for a phrase unit's members, which
  only records are read through.

### 3.3. The driver as the library

A phrase unit importing `util/strutil` is compiled as a separately compiled program unit importing it is: it
references the module's record (`qm_util__strutil`) and initializer (`qv_mod_util__strutil_init`), and the loader
looks them up in the running binary with `dlsym`. This needs no change to how binaries are linked: the runtime is
compiled from its sources and linked as objects, not from an archive, so all of it is present; nothing is
dead-stripped; and an executable's global symbols are exported, among them every module's record, initializer, and
`qv_` export. Stage 2 links all of `questlang/` and all of `lib/`: `driver/main` imports the library modules it does
not use itself (`list`, `dynamic`, `collections/hashSet`, `util/argparse`) so that every one is in it (§3.4).

- **Agreement on interfaces.** The JIT compiles against the units' interfaces from source; the driver's copies were
  compiled from the source it was built from. Stage 2 is built from the tree by a compiler of the same source, and
  `./quest` rebuilds it when `lib/`, `questlang/`, or `runtime/` changes; a release reads the interfaces in its own
  `home/`. They can disagree only when a binary is run against a tree it was not built from. So each module unit, in
  both self-hosted backends, exports one more symbol, `qh_<unit>`, a constant string holding its interface's
  fingerprint (§3.3.1), emitted beside the module's record (as a C string by the C printer, as an SSA datum by
  arm64). The JIT looks it up before using a unit and refuses the import if it differs from the
  fingerprint of the interface it compiled against: the error names the unit, says the binary was built from another
  version of its interface, and suggests rebuilding (`./quest` does). Compiling a second copy instead would silently
  give the phrase state of its own, and break the sharing of §1.
- **The driver stays separately compiled.** A whole-program build (`--whole-program`) merges modules and drops their
  symbols, so it cannot host the JIT (§3.10).
- **`system.args`** is the driver's own argument array in the driver's copy of `system`. The REPL gives programs
  `<repl>` and the arguments after `--` (repl.md §2.1), so the session sets the runtime's array to that view before
  the first input runs; the driver has read its own arguments by then.

#### 3.3.1. What the fingerprint covers

JIT code depends on a host unit only through its interface: it calls the unit's exported functions by their `qv_`
symbols with signatures that follow from their types, reads its module record through offset tables that follow from
its exports, and lays out its abstract types' values generically, as all code outside a module does. Separate
compilation exposes no function bodies (ir.md §8.6), so nothing in a module's implementation reaches JIT code.
The fingerprint is therefore of the interface as the compiler elaborates it, and of nothing else: a SHA-256 digest,
written as hex, of

1. the ABI version (`config/abi`), which changes whenever the runtime's layouts or the calling conventions do;
2. the interface's canonical path;
3. its imports, as the `.qi` records them (`maybe=util/maybe:util/Maybe`), sorted;
4. its exported types, sorted by name: each one's name, kind, and, for a manifest type, its definition, as the `.qi`
   prints them;
5. its exported values, sorted by name: each one's name and type, as the `.qi` prints them;
6. the fingerprints of the interfaces it imports, so that a change to a type it uses by name (a manifest type in
   another interface, `maybe.T` say) changes its fingerprint too.

One function in `modules/` computes it (`modules/artifacts/fingerprint`), from the `.qi` that the compiler writes for
the interface and the JIT loads, and from the fingerprints of the interfaces it imports, found as the loader finds
them; the compiler calls it when it compiles a module unit, and the JIT when it imports one.

It leaves out everything that does not change what JIT code assumes: the interface file's comments, layout, and
declaration order; every absolute path (the `.qi` records its source and its dependencies' directories, which differ
between worktrees and between a release's `home/` and the tree); the module's implementation; the producer string,
since a host's units and the JIT that runs in it are compiled by compilers of one source (stage 2's units by stage
1, which is the same source as stage 2; a release's likewise); and file times.

So an import is refused only when the interface itself, or one it imports, means something different from what the
host was built with, or the ABI changed. Renaming an import's alias also changes it (item 3), which is rare and,
since it can only happen in a tree the binary was not built from, harmless. A change to a widely imported interface
such as `util/Maybe` makes every unit that imports it, directly or not, refuse; that is the case the check exists
for, and `./quest` rebuilds the driver whenever it happens in the tree.

### 3.4. Units not in the driver

With all of `lib/` in the driver, the only units a phrase can import that the driver lacks are the user's own module
files; modules declared in an input (§3.2) are part of it. A unit is never both: if the host links it, the host's copy
is used (§3.3); otherwise the JIT compiles the module file from source, and loads it once in the session.

- **Compiling.** `modules/artifacts/moduleCompiler.moduleFileUnit` elaborates the file as a separately compiled module
  is elaborated (in an environment of its own, its abstract types opaque, its imports known through their interfaces),
  and lowers it to a unit of the module alone; the session compiles that unit as it does an input's, through the passes,
  the SSA, and the arm64 backend, and loads it. Its record, initializer, and exports are the symbols a separately
  compiled module's object would define, so an input that imports it refers to them as it refers to the driver's, and
  the loader resolves them among the units loaded before (§3.6) rather than with `dlsym`.
- **Order.** A module file's own imports of module files are loaded before it, depth first; each of its imports of
  the driver's modules is checked against the driver's fingerprints, as an input's are.
- **Once.** A module file is loaded the first time an input imports it, and later inputs (and module files) that
  import it use that copy, whose state persists, as the interpreter's does. Editing the file during the session does
  not reload it. An input that fails forgets the module files it loaded, as the interpreter forgets the modules it ran,
  so that a later import loads them afresh (`tests/repl/modules.quest`); those earlier inputs loaded stay, their state
  kept. A module that fails to compile reports its error as the interpreter would.
- **Initialization.** The module's initializer, guarded to run once, runs when its first importer's does, as in a
  compiled program.
- **Exceptions** raised in a module file's code are located in its file (§3.7): the session keeps each loaded file's
  source by the name its code gives sites in it.

#### 3.4.1. Artifacts in memory

The JIT types imports as separately compiled code does, each module through its interface's record, and so reads
interfaces from `.qi` artifacts, whose text is also what the fingerprints of §3.3.1 digest. Those artifacts are kept
in memory, not in a build directory: nothing a program run on the JIT does writes to the directory it runs in.

- **Where.** The JIT's build directory is `common/memoryFiles`' root, `/<quest-memory>`, a path that is never a real
  directory. `modules/paths` (`readText`, `isFile`, `modifiedNs`, `writeAtomically`) and `config/abi`'s reader treat a
  path under it as a text in the process, so the interface compiler, the loader, and `modules/artifacts/fingerprint`
  run as they do with files, the same `.qi` text written, parsed, and digested.
- **Freshness.** A file in memory is newer than every file (`modifiedNs` is the greatest `Int`), so it is never
  rebuilt: within a process a unit, once loaded, stays loaded, as in the interpreter's REPL (§3.4).
- **Cost.** Each run elaborates the interfaces it imports again, which a build directory would have kept: about 10 ms
  for a program that imports `util/maybe` and `collections/hashMap`, 1.5 ms for one that imports nothing.
- `--build-dir DIR` keeps them in `DIR` instead.

### 3.5. The encoder

`codegen/arm64/encode` turns a unit's minst sequence and its static data into a code section (32-bit words) and a
data section (bytes), each with a list of relocations (symbol, kind, offset), and each function's offset and size.
Each `Op` case gives its 32-bit word as the printer's gives its text (the printer's `expansion`); the encoder's cases
sit beside the printer's in `codegen/arm64`, so that adding an instruction is one edit and the exhaustiveness check
catches a case missing from either. What the encoder does in place of the assembler:

- **Labels and branches:** two passes, offsets then words; `relaxBranches` ensures that every conditional branch
  reaches. Labels are resolved, and so is a function's call of itself, as `as` resolves it (each function is an atom
  of its own under `.subsections_via_symbols`); every other symbol is relocated.
- **Symbol addresses** (`relocPage`, `relocGot`): `adrp` reaches ±4 GB, and the arena may be farther than that from
  the host's image. Within the arena, `adrp`/`add` is patched directly; a symbol in the host is reached through a GOT
  slot in the arena (`adrp`/`ldr`), which the loader fills with its address.
- **Calls** (`bl _f`): `bl` reaches ±128 MB. A call to the host goes to a stub in the arena (`adrp x16` of its GOT
  slot, `ldr x16`, `br x16`), as the linker's stubs do; calls within the arena are direct.
- **Thread-locals** (`relocTlv`, for `quest_current_exception_handler` and `quest_current_exception`): the code reads
  a descriptor and calls its first word, which returns the variable's address on the current thread. The loader puts
  the driver's own descriptor of the variable, which `dlsym` gives, in the GOT slot. Code generation is unchanged, and
  the encoder treats the reference as any other GOT entry.
- **Data:** the static data's words, with absolute relocations for pointers to functions and other data.
- **Unwind directives:** dropped, since frames need no unwind information (§3.9). **`.loc`:** kept as a table of
  positions by code offset, for a debugger (§3.12).

The encoder is checked against the assembler: with `QUEST_CHECK_ENCODING=1` the backend appends a unit's encoding to
its assembly as comments, and `tests/self-hosted/encoder.py` checks, for the run goldens' programs and the units they
link, that the encoder's bytes equal the `__text` (and data) that `clang -c` makes of the printed assembly,
relocations aside. Forms the backend can emit that no such program uses are encoded from the manual.

### 3.6. The loader

- **The arena:** one region reserved with `mmap(MAP_JIT)` at the session's start (128 MB, so that every `bl` within
  it reaches), filled from its start. Writing toggles `pthread_jit_write_protect_np` and ends with
  `sys_icache_invalidate`. The data section goes in a separate, non-executable mapping (64 MB), with the GOT slots;
  the stubs go in the arena. Both are asked of `mmap` by address (`quest_code_reserve`): the first just above the
  runtime's own text, each later one just after the last, since `adrp` from the arena must reach the GOT slots and
  the host's image. The kernel's own placement was beyond 4 GB in three runs of a hundred: the collector's tables
  filled the pages above the binary, the arena landed just under Darwin's shared cache (2 GB above the binary), and
  the data went past the cache, 7 GB away. So the collector maps its tables beside its heap (collector.md §3.1), and a
  region that still lands out of reach (not above the text and ending within 3.5 GB of it) is asked for again from
  the first address, where the search finds any gap below. Nothing is freed: an input that fails leaves its code
  behind, unused.
- **Symbols** (`jit/loader`): a unit's own symbols resolve first, then those the units before it export (the entries,
  the records), then the driver's (`dlsym`). A unit's other symbols (`qr_register_dicts`, its functions' names) are
  its own, so that units do not collide. A thread-local's slot holds the driver's own descriptor of it, which is what
  `dlsym` gives for a thread-local, so JIT code reads it as compiled code does; `os/code`'s `threadLocalGetter` is not
  needed.
- **Registration,** done by the entry as by a program's `main`: function tables (`quest_register_funcs`), record offset
  tables (`quest_register_record_dict`), and abstract types (`quest_register_abstract_type`). The runtime compares
  type descriptors structurally (`quest_is_subtype`; an opaque one by its name), not by address, so an input's
  descriptors match the host's when the types are the same. Two inputs may declare different modules of the same name
  (the REPL allows `module m ... end` twice), so a declared module's global name includes its input's number.
- **Frame tables:** a unit's frame table (arm64.md §3.13), by which the collector scans its frames' live words
  alone, goes in the arena after the unit's code, its first word set to the code's address less its own, under the
  unit's symbol `qr_frames`; the unit's `qr_register_dicts` registers it, as compiled code's does.
- **Collector roots:** the data mapping and the globals are registered with `quest_code_add_roots`
  (`quest_gc_add_roots`), as a region of ambiguous roots; the collector scans the host's root tables and stacks but
  not memory the JIT maps.
- **Function ranges:** the loader keeps each JIT function's start, end (its `Lf<k>_end` label), and frame name, for
  attributing frames (§3.9).

### 3.7. Running an input

The driver calls the input's entry through a primitive that installs an exception handler around the call, like a
`try ... else` with a traced binder, and returns whether it raised and, if so, the exception state. The handler
records work for both C-built code (setjmp) and arm64-built code (native resume), so a raise in JIT code reaches the
handler whichever backend built the host.

- **Results** are in the entry's result globals, one per phrase, each with the phrase's static type, which the
  session knows.
- **An exception** is reported as compiled code reports it through the driver (exceptions.md §2.1): the raise site,
  from the location string that the raise passes, its payload (exceptions.md §2.1), and the frames (§3.9). A unit
  names its source `<repl>#N`, N the input's number, so the site says which input raised, even a function an
  earlier input made; the session finds that input's source and reports the error in it, under its own name
  (`<repl>`, or the file's). The frames are those above `os/code`'s `call` (or the session's `run`, where a C-built
  driver keeps no frame of `call`'s), ending with `<main>`, the input's top level; the runtime's runs of one frame
  are kept. The input is then rolled back as the interpreter's is: the environment forgets its bindings, and its
  code and record stay in memory, unreachable. Writes it made to earlier inputs' `var`s stay, as in the interpreter
  (`tests/golden/repl/rollback.out`).
- **Output** goes through the runtime's writers, which the host shares, so the order of a phrase's output and the
  REPL's is kept.

### 3.8. Printing results

A phrase unit's phrases show their results as a compiled program's do with `--echo` (or `--print-result`): the
lowering emits each one's echo, and the runtime's printers (`quest_print_value`, `quest_print_typed`, and
`quest_echo_text` for a declaration) write it when the phrase runs, by its descriptor. Those printers are checked
against the interpreter's formatter already, by the shared run goldens, and they read values as compiled code holds
them: through proxies, `Dynamic` values by their descriptors, cycles guarded.

- **A file or `-e`** is one input, which prints as a compiled program does: its last phrase's result, or every
  phrase's with `--echo`, as it runs.
- **The REPL** captures what an input prints instead (`quest_echo_capture` in its entry, and `quest_echo_captured`,
  whose string the entry leaves in `qj_<n>_echo`), with a separator line before each phrase's, and prints each
  phrase's lines with its prompts (`==  `, then the continuation's indentation), after the input has run, as it does
  for the interpreter. While capturing, the printers write to a memory stream made `stdout`, so a program's own output
  is not captured.

Reading values back with reflection through `os/value` and formatting them with the interpreter's formatter was
tried first and not kept, since it could not follow proxies (a tuple or option viewed at a supertype) or show a
`Dynamic` value without redoing what the runtime already does (§1).

### 3.9. Frames

An uncaught exception's frames come from `quest_raise_at`'s walk of the native stack (exceptions.md §5.3). The
platform unwinder (`_Unwind_Backtrace`) cannot step through JIT code, which has no unwind entries, and `dladdr` has
no symbols for it.

So on Darwin arm64 (`Q_FRAME_POINTER_WALK` in `runtime/quest_exceptions.c`) the runtime walks the frame-pointer chain,
for all compiled code. Every function there that calls another keeps a frame record (`x29` pointing at its caller's
`x29` and the return address): the arm64 backend's functions always (arm64.md §3.10), and clang's, whose default on
Darwin keeps frame pointers in non-leaf functions. A raise is a call, so every frame below it has a record. Each
frame's function start is found by `dladdr` for code in the binary, and in the loader's ranges (§3.6,
`quest_code_add_function`) for JIT code, then matched exactly against the registered function tables; the cache of
each return address's function start (`quest_function_start`, exceptions.md §5.3) is right because code is never
unloaded, in the binary or in the arena (§3.6). The walk needs no unwind information, and compact unwind's
adjacent-function problem does not affect stepping.

The capture of exceptions.md §5.4 and the uncaught walk of §5.3 both use the chain; the stack-overflow handler
(exceptions.md §6) starts its walk from the faulting context's `x29`. Other platforms keep the unwinder.

### 3.10. The host binary and the driver

**Hosts.** A host is a binary the JIT runs code in: in practice the driver. Any separately compiled binary built by the
self-hosted compiler, with either backend, can be one (§3.3); a binary is a host if its units export fingerprint
symbols, which the JIT checks for. The bootstrap emits none, so stage 1 is not a host, and `--jit` there is an error
that says so; nor is a whole-program build, which interprets the REPL and `-e` instead. Stage 2, and so `./quest` and
every release, is a host.

Nothing in the JIT's code depends on how the host's units were compiled: it calls them through the C ABI, reaches
their data through GOT slots, and raises and catches through the runtime's handler records, which carry both the
setjmp state of C-built code and the resume state of arm64 code (arm64.md §3.6).

**The driver:**

- The REPL, `-i FILE` (whose file is then compiled as the first input, its top-level bindings in scope for later
  inputs), `-e`, and `quest FILE` (a single input) run on the JIT by default; `--jit` asks for it explicitly.
- `--no-jit` interprets instead, as do `--stop-after`, `--dump-after`, `--show-offsets`, and `--show-values`, which
  name the interpreter's phases or output, `--whole-program`, and a driver that is not a host. The test runners pass
  `--stop-after interpret` for the interpreter's goldens, so they check the interpreter.

### 3.11. Unsound interfaces and modules

The grammar has the marking (`["unsound"] "interface"` and `["unsound"] "module"`, in grammar.txt). *Typeful
Programming* §9.3 gives the rules, after Cedar-Mesa's and Modula-3's unsafe modules. Both compilers check them (a
language rule, testing.md §2.8; [modules.md](modules.md) §4.4), and a `.qi` records whether its interface is unsound
(`isUnsound`):

- a sound module, or a program, may not import an unsound interface; an unsound module may import any;
- only an unsound module may implement an unsound interface;
- an unsound module may export a sound interface, its author vouching that it is sound from outside;
- a sound interface may import an unsound one, since soundness can be compromised only by operations, not by types;
- the top level (a program, the REPL) is implicitly sound.

**Externals.** In Cardelli's system "the only unsound operations in Quest are provided by
built-in unsound interfaces such as Value". Here `external` is one too, allowed only in unsound modules: it gives a C
symbol whatever Quest type it is declared with, and nothing checks the declaration against the C, so a wrong one (a
C function's signature, a `Bool` or `Char` at the wrong width, a pointer the collector cannot see) corrupts memory
with no help from the type checker. An external declaration is `value.be` applied to a C symbol, and is treated the
same. The marking makes that trust boundary explicit and checked: `grep unsound` lists every module whose
correctness rests on hand-checked C. The modules of `lib/` that bind externals are `unsound module`s behind sound
interfaces, as Cardelli intended for low-level facilities, so the programs that import them need no marking. Test
programs that bind externals (`tests/source/language/external_values`, `inlined_calls`, `thunks`) do so in small
unsound modules. `external` covers types as well as values and functions, so an interface, even an unsound one, may
declare no external type. The rules' errors are tested in `tests/errors/typecheck/unsound`, and their uses in
`tests/source/modules/unsound_modules`.

The JIT's primitives are two unsound interfaces in `lib/os/` ([libraries.md](libraries.md) §4.4), whose
natives are in `runtime/quest_code.c`:

**`os/value`** is Cardelli's `Value` (*Typeful Programming*, appendix), with its signature unchanged:

```quest
unsound interface Value
export
    T::TYPE                              (* an arbitrary value: one word *)
    error: Exception(Ok)                 (* raised when an operation cannot be carried out *)
    length: Int                          (* the size of a T, in bytes: 8 *)
    new(A::TYPE a: A): T                 (* any value as a T *)
    be(A::TYPE v: T): A                  (* a T as a value of any type. Unsound! *)
    fetch(addr: T displ: Int): T         (* the word at addr + displ bytes *)
    store(addr: T displ: Int w: T): Ok   (* store a word at addr + displ bytes. Unsound! *)
end
```

It fits this implementation exactly because every slot holds one word, the value's slot representation
(c-representation.md, "Slots"): `new` gives that word (a record's or variant's box pointer, a real's bits, a
string's pointer), and `be` takes it back. `fetch` and `store` address bytes, the "implementation-dependent units",
and raise `error` for a null address or a displacement that is not a multiple of 8. A tuple's components and a
record's offset table and fields are words, and a `Bool` or `Char` slot is a whole word too
(`tests/source/stdlib/os_value` reads them). The session uses it to read the string an input captured, to give
`system.args` to the driver's `system` record, and to link debugger objects (§3.12).

**`os/code`** holds what has no counterpart in Cardelli's system (`tests/source/stdlib/os_code` writes a hand-encoded
function into a code region and calls it):

- a code region: reserving one, writing words into it, making it executable (flushing the instruction cache);
- the address of a symbol of the running binary, as a `value.T`;
- calling an address as a function of no arguments under an exception handler, giving the exception state if it
  raised;
- the operations on the runtime the loader needs: registering collector roots and function ranges.

Neither interpreter runs them: interpreting a program that imports `os/value` or `os/code`, in the bootstrap or in
the self-hosted interpreter, is an error, given by the module's name (`tests/errors/run/os_value_interpreted`), not
by builtins that name the natives, so that a release's interpreter needs none of them. The bootstrap's C backend
compiles them, since it builds stage 1, which contains the JIT, though stage 1 cannot run it (§3.10).

### 3.12. Debugging

With `QUEST_JIT_DEBUG=1`, a session describes each unit it loads to a debugger through the GDB JIT interface, which
lldb reads when told to (macOS's lldb ignores it by default):

```text
$ QUEST_JIT_DEBUG=1 lldb -o 'settings set plugin.jit-loader.gdb.enable on' -- quest prog.quest
(lldb) breakpoint set --file prog.quest --line 8
(lldb) run
```

Breakpoints on Quest lines and on functions (by their symbols, `qf_fib`) resolve as the units load, and backtraces
show the lines of JIT frames; there are no variable locations, as in the arm64 backend's own debugging information.

- **The object.** For each unit, `jit/debugObject` writes a Mach-O arm64 object in memory: one section of code, at
  the address the loader put it at, so that nothing needs relocating; a symbol for each function; and DWARF 4, a
  compile unit with a subprogram per function and a line table, as `codegen/arm64/asm` writes for a unit assembled to a
  file ([arm64.md](arm64.md) §3.16), from the `.loc` positions the encoder keeps (`Encoded.lines`). Each
  function's line sequence starts at its first instruction with its first position, so that a breakpoint on the
  function finds a line and lldb skips the prologue. The DWARF sections are at address 0: lldb reads an in-memory
  object's sections from the process at their addresses, but one at a small address from the object itself.
- **The interface.** The runtime defines its two symbols, `__jit_debug_descriptor` and `__jit_debug_register_code`
  (`quest_code.c`); the session finds them with `os/code`'s `symbol`, links the object into the descriptor's list
  with `os/value`'s `store` (each object and its list entry a string's bytes, which the session keeps), and calls the
  function with `os/code`'s `call`. Since a release builds stage 1 against its own `lib/`, the session uses no
  `os/code` function made for debugging, and a driver whose runtime lacks the symbols describes nothing.
  `tests/self-hosted/line_tables.py` checks the objects with lldb.
- **Sources.** A unit's file is the input's file, for a program given as a file, or a module file's own. An input
  that has none (a REPL input, an `-e` program) is written to `input-N.quest` in a directory of the session's own
  under `TMPDIR`, which the session removes when it ends; a driver that is killed, or a program that calls
  `system.exit`, leaves it.
- **Cost.** Describing a unit costs about 0.2 ms, a fifth of a typical REPL input, so it is not the default.

## 4. Differences From the Interpreter

Compiled code differs from the interpreters in two accepted ways (exceptions.md §2.4, §6), which the JIT
inherits, and which show in the REPL transcripts:

- it lists fewer frames, when the inliner or a tail call removes them;
- runaway recursion ends the session rather than raising `stack.overflow` (`tests/golden/repl/stack_overflow.out`).

Both are accepted, here and in exceptions.md. An uncaught exception's payload is shown as the interpreters show it
(exceptions.md §2.1), but for one of a module's abstract type, which compiled code shows as `<hidden>`.

Running in the driver's own process adds one more, which the run goldens through `--jit` show:

- a program that calls the compiler's own modules (the questlang tests) calls the running compiler's, and sees its
  state (§1, "the driver is the library").

A fatal runtime error (an option's ordinal out of bounds, say), which ends a compiled program, ended the driver until
2026-11-15, with the input's internal source name (`<repl>#N`) as its site. It now ends the input, reported as the
compiled program reports it (exceptions.md §2.5), and a REPL goes on.

## 5. Testing

- **Unsound interfaces:** the checks of §3.11 in both compilers, with a test of each rule's error.
- **The primitives:** `tests/source/stdlib/os_value` and `os_code`, compiled only (§3.11).
- **Frames:** the run goldens that list frames, through the C, ssac, and arm64 backends.
- **Fingerprints:** `tests/self-hosted/fingerprints.py` checks each unit's `qh_` digest against one it computes from
  the `.qi` files (§3.3.1).
- **Encoder:** byte-for-byte against `clang -c` (§3.5), `tests/self-hosted/encoder.py`.
- **The REPL transcripts** (`tests/repl`, `tests/golden/repl`) on the JIT (`--backend jit`), against the same
  goldens; the `repl` phase runs them with `--no-jit`, checking the interpreter. A transcript that shows an accepted
  difference (§4) is skipped under `--jit` by a marker in its source (`@skip-phase: jit`), as
  `@skip-phase run_c_compiled` skips a program; that is `stack_overflow`.
- **Imports and hosts:** `tests/self-hosted/jit_hosts.py` checks a stale interface's refusal, an unchanged one, and the
  user's own modules (§3.3, §3.4).
- **Debugging:** `tests/self-hosted/line_tables.py` (§3.12).
- **The run goldens** through `quest --jit FILE` (`--backend jit-files`), skipping the programs marked
  `@skip-phase: jit` or `@skip-phase: run_c_compiled`, whose differences the JIT shares with compiled code.
  `tests/self-hosted/pending-jit.txt` lists the rest of the differences (§4). The mode also runs `-e`'s transcript
  (`tests/eval`) on the JIT; the `interpret` phase runs it with `--no-jit`.
- **Both hosts:** the transcripts through a C-built and an arm64-built stage 2 (`QUEST_BACKEND`, in `jit_hosts.py`).
- tools/check runs these with the backends suite.

## 6. Open Work

- Inlining and specializing earlier inputs' functions in later inputs (parked). Calling them directly alone
  (exporting a phrase unit's functions' code and calling it with a null environment, rather than loading the
  binding's closure) was tried on 2026-11-01 and not kept: 200 million calls of an earlier `add1` took 0.27 s against
  0.26 s, and 100 million of an earlier generic `twice` 1.78 s against 1.47 s, `twice`'s code byte for byte the same,
  its placement differing. In one unit the same loops take 0.13 s and 0.06 s: the gap is inlining and
  specialization, which need the earlier inputs' IR, not the call. Since interactive code's functions are slots
  (§3.2), this means direct calls and inlining of slots whose definition has not changed, undone when one does: the
  session would keep each input's IR and each slot's dependents. Only if redefinition's cost (repl.md §6) matters in
  practice.
- Surviving faults and runaway recursion in the REPL.
