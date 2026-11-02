# Plan: The arm64 JIT

Step 7 of the [roadmap](roadmap.md): the self-hosted driver compiles each REPL input to arm64 machine code in its own
process, links it against the units already in the driver, and runs it, instead of interpreting it. It uses the arm64
backend's pipeline ([arm64.md](arm64.md)) unchanged up to machine instructions, and replaces the assembler and linker
with an in-memory encoder and loader. It is written in Quest, in `questlang/`, and the bootstrap does not get it
([testing.md](testing.md) §2.8), though it gets the language change the JIT needs (§3.11).

**Status: all 8 steps done** (2026-11-01) (§7). Section 1 records the decisions, section 7 the steps.

---

## 1. Decisions

Decided 2026-10-31:

- **What runs on it.** Eventually all of the REPL, and also `quest file.quest` and `-e`. While it is developed, only
  with `--jit`; without it, the driver interprets as now. *Revised 2026-11-01:* the REPL and `-e` run on it by
  default (§3.10), and files will now that a program's own modules can be imported (§3.4).
- **The same process,** sharing the driver's heap, runtime, and library state.
- **The driver is the library.** A phrase that imports a unit linked into the driver uses the driver's copy of it, its
  code and its state: `writer.output` is the compiler's own, and a phrase that imports `questlang/...` modules
  reaches the running compiler's. The circularity is intended.
- **Straight to an encoder.** No stage that writes `.s` and shells out to `as` and `ld` to make a dylib: `minst`
  already makes instructions data, so the encoder replaces the assembler from the start (§3.5).
- **Lexical semantics.** A rebinding shadows: functions compiled earlier keep the binding they saw, as in the
  interpreters (where `let f() = 1; let g() = f(); let f() = 2; g()` is 1). There is no hot-swapping, in the
  interpreters or here; the roadmap's "dynamic patching and hot-swapping" is dropped. The REPL's output stays the
  interpreter's.
- **Incremental** means that an input compiles only itself; what earlier inputs compiled stays loaded.
- **A crash ends the session,** for now: a fault or a runaway recursion in a phrase ends the driver as it ends a
  compiled program (exceptions.md §6). Ctrl-C likewise.
- **Self-hosted only,** and **runs in a binary built by either backend**: the JIT, and the code it writes, run in a
  binary whose units the C backend or the arm64 backend compiled (`QUEST_BACKEND=c` or `arm64`, for the driver). The
  host's units are reached only through the C ABI that both backends' objects share (§3.10).
- **The same pipeline** as `--backend arm64`, with its optimizations, within an input. No separate fast path.

Decided 2026-11-01:

- **A host unit that does not match its source is refused:** importing it is an error, never a second copy compiled
  from source (§3.3).
- **Frames by the frame-pointer chain,** for all compiled code, not only the JIT's (§3.9).
- **Results printed by the interpreter's formatter,** from values that reflection reads out of native memory (§3.8).
  *Replaced* during step 8: reflection could not follow proxies or show `Dynamic` values without redoing the
  runtime's work, so results are printed by the runtime's own formatter, as a compiled program prints them (§3.8).
- **The low-level primitives live in `os/`,** named for what they do rather than for the JIT, behind interfaces
  marked `unsound`: Cardelli's scheme, which the language now enforces (§3.11), with `external` an unsound
  operation (§3.11, "Externals").
- **`os/value` is Cardelli's `Value`,** signature and all; what it lacks is in `os/code` (§3.11).
- **Neither interpreter runs `os/value` or `os/code`** (§3.11).
- **Differences from the interpreter** are accepted and documented, for now (§4). Printing an exception's payload in
  the REPL is deferred: it needs an ABI change in every backend for one line of output (§6).
- **Kept simple** (after a review for complexity):
  - every separately compiled binary can host the JIT, with no host link mode, given one fingerprint symbol per module
    unit (§3.3, §3.10), a fingerprint of what JIT code depends on and nothing else (§3.3.1);
  - the driver links all of `lib/`, so the JIT compiles no imported module from source at first (§3.4);
  - the transcripts that show an accepted difference are skipped under `--jit` rather than given goldens of their own
    (§5);
  - phrase units stay a unit kind of their own (§3.2), not modules in disguise. *Revised* in step 6, and kept by
    the user's decision of 2026-11-01: a phrase unit is still a unit kind of its own (`nodes.Phrase`), but its top
    level is the initializer of a module of its own, whose record holds its bindings (§3.2).

## 2. Pipeline

```
input text ──parse, typecheck (as now: env, unit graph, snapshots)──► typed phrases
   ──lower as a phrase unit (§3.2)──► IR ──passes──► SSA ──select, allocate──► minst
   ──encode (§3.5)──► code and data with relocations ──load (§3.6)──► executable memory
   ──call the input's entry (§3.7)──► results printed by the runtime (§3.8)
   ──captured, for the REPL──► "==  ..."
```

Everything up to minst is the arm64 backend's, given a new kind of unit. The encoder, loader, and the REPL's use of
them are new.

## 3. Design

### 3.1. Where the JIT lives

- `questlang/jit/`: `loader` (the code arena, symbol resolution, relocation, registration) and `session` (the REPL's
  state: earlier inputs' records); the encoder is `codegen/arm64/encode`. The modules that use the unsound primitives
  are `unsound` modules.
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
ensures today.

- **Namespaces stack.** An input sees every binding of the inputs before it, as the interpreter's frames do; the type
  checker's environment already provides that. The session keeps, for each symbol an input that ran bound, where it
  lives (`lower.Earlier`: the module whose record holds it, its field, the record's type, and whether it is a `var`),
  and passes them to the next input's lowering.
- **Reading an earlier binding.** In a later input, a variable whose symbol the input does not bind and the session
  knows is a member of that module: the input imports the module as a unit imports any module (a `nodes.Import` of
  `qj_<n>`, with the record's type), and reads the binding as an `opModuleMember`. A top-level function is reached
  through the field holding its closure; calling its code directly, or inlining it, is a later optimization (§6).
  Rebindings are distinct symbols already (ir.md §2), so they are distinct fields, and a function an earlier input
  made keeps the binding it saw (lexical semantics, §1).
- **Writing an earlier `var`.** Global `var`s cannot be captured by functions (the rule the REPL already reports), so
  an earlier input's `var` is read and written only by later top-level code: through its field's address
  (`opAddrField` on the record) and with a store to the field (`sStoreField`). The field is in the record's payload,
  which every copy of the record shares, so a write is seen by every later input.
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

A phrase unit importing `util/strutil` is compiled as a separately compiled program unit importing it is now: it
references the module's record (`qm_util__strutil`) and initializer (`qv_mod_util__strutil_init`), and the loader
looks them up in the running binary with `dlsym`. This needs no change to how binaries are linked: the runtime is
compiled from its sources and linked as objects, not from an archive, so all of it is present; nothing is
dead-stripped; and an executable's global symbols are exported. Today's stage 2 exports 2,157, among them every
module's record, initializer, and `qv_` export, and links all of `questlang/` and all of `lib/` but `list` and
`dynamic`, which the driver will import so that every library module is in it (§3.4).

- **Agreement on interfaces.** The JIT compiles against the units' interfaces from source; the driver's copies were
  compiled from the source it was built from. Stage 2 is built from the tree by a compiler of the same source, and
  `./quest` rebuilds it when `lib/`, `questlang/`, or `runtime/` changes; a release reads the interfaces in its own
  `home/`. They can disagree only when a binary is run against a tree it was not built from. So each module unit, in
  both self-hosted backends, exports one more symbol, `qh_<unit>`, a constant string holding its interface's
  fingerprint (§3.3.1). The JIT looks it up before using a unit and refuses the import if it differs from the
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
compilation exposes no function bodies (inlining.md §1), so nothing in a module's implementation reaches JIT code.
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

One function in `modules/` computes it (`modules/fingerprint`), from the `.qi` that the compiler writes for the
interface and the JIT loads, and from the fingerprints of the interfaces it imports, found as the loader finds them;
the compiler calls it when it compiles a module unit, and the JIT when it imports one.

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

- **Compiling.** `modules/moduleCompiler.moduleFileUnit` elaborates the file as a separately compiled module is
  elaborated (in an environment of its own, its abstract types opaque, its imports known through their interfaces),
  and lowers it to a unit of the module alone; the session compiles that unit as it does an input's, through the
  passes, the SSA, and the arm64 backend, and loads it. Its record, initializer, and exports are the symbols a
  separately compiled module's object would define, so an input that imports it refers to them as it refers to the
  driver's, and the loader resolves them among the units loaded before (§3.6) rather than with `dlsym`.
- **Order.** A module file's own imports of module files are loaded before it, depth first; each of its imports of
  the driver's modules is checked against the driver's fingerprints, as an input's are.
- **Once.** A module file is loaded the first time an input imports it, and later inputs (and module files) that
  import it use that copy, whose state persists, as the interpreter's does. Editing the file during the session does
  not reload it. An input that fails after loading a module leaves it loaded; one whose module fails to compile
  leaves nothing loaded, and reports the module's error as the interpreter would.
- **Initialization.** The module's initializer, guarded to run once, runs when its first importer's does, as in a
  compiled program.
- **Exceptions** raised in a module file's code are located in its file (§3.7): the session keeps each loaded file's
  source by the name its code gives sites in it.

### 3.5. The encoder

`codegen/arm64/encode` turns a unit's minst sequence and its static data into a code section (32-bit words) and a
data section (bytes), each with a list of relocations (symbol, kind, offset). Each `Op` case gives its 32-bit word as the printer's gives
its text; the encoder's cases sit beside the printer's in `codegen/arm64`, so that adding an instruction is one edit
and the exhaustiveness check catches a case missing from either. What the assembler does now and the encoder must:

- **Labels and branches:** two passes, offsets then words; `relaxBranches` already ensures that every conditional
  branch reaches.
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
- **Unwind directives and `.loc`:** dropped. Frames need no unwind information (§3.9); line tables for JIT code are
  later work (§6).

The encoder is checked against the assembler: for every arm64 golden, the encoder's bytes equal the `__text` that
`clang -c` makes of the printed assembly, relocations aside.

### 3.6. The loader

- **The arena:** one region reserved with `mmap(MAP_JIT)` at the session's start (128 MB, so that every `bl` within
  it reaches), filled from its start. Writing toggles `pthread_jit_write_protect_np` and ends with
  `sys_icache_invalidate`. The data section goes in a separate, non-executable mapping (64 MB), with the GOT slots;
  the stubs go in the arena. Nothing is freed: an input that fails leaves its code behind, unused.
- **Symbols** (`jit/loader`): a unit's own symbols resolve first, then those the units before it export (the entries,
  the records), then the driver's (`dlsym`). A unit's other symbols (`qr_register_dicts`, its functions' names) are
  its own, so that units do not collide. A thread-local's slot holds the driver's own descriptor of it, which is what
  `dlsym` gives for a thread-local, so JIT code reads it as compiled code does; `os/code`'s `threadLocalGetter` is not
  needed.
- **Registration,** done by the entry as it is by `main` now: function tables (`quest_register_funcs`), record offset
  tables (`quest_register_record_dict`), and abstract types (`quest_register_abstract_type`). Type descriptors are
  interned by the runtime, so an input's descriptors are the host's when the types are the same. Two inputs may
  declare different modules of the same name (the REPL allows `module m ... end` twice), so a declared module's
  global name includes its input's number.
- **Collector roots:** the data mapping and the globals are registered with `GC_add_roots`; Boehm scans the host's
  image and stacks but not memory the JIT maps.
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
  from the location string that `quest_raise_at` receives, and the frames (§3.9), without the payload (§4). A unit
  names its source `<repl>#N`, N the input's number, so the site says which input raised, even a function an
  earlier input made; the session finds that input's source and reports the error in it, under its own name
  (`<repl>`, or the file's). The frames are those above `os/code`'s `call` (or the session's `run`, where a C-built
  driver keeps no frame of `call`'s), ending with `<main>`, the input's top level; the runtime's runs of one frame
  are kept. The input is then rolled back as now: the environment forgets its bindings, and its code and record stay
  in memory, unreachable. Writes it made to earlier inputs' `var`s stay, as in the interpreter
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

The first design read values back with reflection through `os/value` and formatted them with the interpreter's
formatter; it was replaced in step 8, since it could not follow proxies (a tuple or option viewed at a supertype) or
show a `Dynamic` value without redoing what the runtime already does (§1).

### 3.9. Frames

An uncaught exception's frames come from `quest_raise_at`'s walk of the native stack (exceptions.md §5.3), which uses
`_Unwind_Backtrace` to step from frame to frame, and `_Unwind_FindEnclosingFunction` and `dladdr` to find each
frame's function. The unwinder cannot step through JIT code, which has no unwind entries, and `dladdr` has no symbols
for it.

The runtime walks the frame-pointer chain instead, for all compiled code. Every function on Darwin arm64 that calls
another keeps a frame record (`x29` pointing at its caller's `x29` and the return address): the arm64 backend's
functions always (arm64.md §3.10), and clang's, whose default on Darwin keeps frame pointers in non-leaf functions.
A raise is a call, so every frame below it has a record. Each frame's function is found by `dladdr` for code in the
binary, and in the loader's ranges (§3.6) for JIT code; the exact match against the registered function tables
stays, as does the cache of each return address's function start (exceptions.md §5.3), which is right because
code is never unloaded, in the binary or in the arena (§3.6). This is simpler than the walk it replaces as well as
reaching JIT code:

- compact unwind's adjacent-function problem, which `quest_function_start` works around, no longer affects stepping;
- no unwind information is needed for JIT code.

The capture of exceptions.md §5.4 and the uncaught walk of §5.3 both change; the stack-overflow handler (§6) starts
its walk from the faulting context's `x29`. Linux, which exceptions.md also describes, keeps the unwinder. Frames
may differ from today's where the unwinder skipped a frame that the chain has (a C runtime function that calls back
into Quest, say), so the run goldens that list frames are checked again.

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
  inputs), and `-e` run on the JIT by default; `quest FILE` runs on it with `--jit`, as a single input.
- `--no-jit` interprets instead, as do `--stop-after`, `--dump-after`, `--show-offsets`, and `--show-values`, which
  name the interpreter's phases or output, and a driver that is not a host.

### 3.11. Unsound interfaces and modules

The grammar already has the marking (`["unsound"] "interface"` and `["unsound"] "module"`, in grammar.txt), and both
parsers record it, but nothing checks it. *Typeful Programming* §9.3 gives the rules, after Cedar-Mesa's and
Modula-3's unsafe modules. Both compilers check them (a change to the language, testing.md §2.8):

- a sound module, or a program, may not import an unsound interface; an unsound module may import any;
- only an unsound module may implement an unsound interface;
- an unsound module may export a sound interface, its author vouching that it is sound from outside;
- a sound interface may import an unsound one, since soundness can be compromised only by operations, not by types;
- the top level (a program, the REPL) is implicitly sound.

**Externals** (decided 2026-11-01). In Cardelli's system "the only unsound operations in Quest are provided by
built-in unsound interfaces such as Value". Here `external` is one too, allowed only in unsound modules: it gives a C
symbol whatever Quest type it is declared with, and nothing checks the declaration against the C, so a wrong one (a
C function's signature, a `Bool` or `Char` at the wrong width, a pointer the collector cannot see) corrupts memory
with no help from the type checker. An external declaration is `value.be` applied to a C symbol, and is treated the
same. The marking makes that trust boundary explicit and checked: `grep unsound` lists every module whose
correctness rests on hand-checked C. The eighteen modules of `lib/` that bind externals become `unsound module`s
behind their sound interfaces, as Cardelli intended for low-level facilities, so neither their interfaces nor the
programs that import them change. The four test programs that bind externals
(`tests/source/language/external_values`, `inlined_calls`, `thunks`, and `tests/elaborate/types`) move them into
small unsound modules.

The new primitives are two unsound interfaces in `lib/os/`:

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
and raise `error` for a null address or a displacement that is not a multiple of 8. That was enough for the first
design's reflection (§3.8): a tuple's components and a record's offset table and fields are words, and a `Bool` or
`Char` slot is a whole word too. The session uses it to read the string an input captured, and to give
`system.args` to the driver's `system` record.

**`os/code`** is new, and holds what has no counterpart in Cardelli's system:

- a code region: reserving one, writing words into it, making it executable (flushing the instruction cache);
- the address of a symbol of the running binary, as a `value.T`;
- calling an address as a function of no arguments under an exception handler, giving the exception state if it
  raised;
- the operations on the runtime the loader needs: registering collector roots and function ranges.

Neither interpreter runs them: interpreting a program that imports `os/value` or `os/code`, in the bootstrap or in
the self-hosted interpreter, is an error. The bootstrap's C backend compiles them, since it builds stage 1, which
contains the JIT, though stage 1 cannot run it (§3.10).

## 4. Differences From the Interpreter

Compiled code already differs from the interpreters in three accepted ways (exceptions.md §2.1, §2.4, §6), which
the JIT inherits, and which show in the REPL transcripts:

- an uncaught exception's header omits its payload (`Exception: Fail`, not `Exception: Fail with 3:Int`;
  `tests/golden/repl/rethrow.out`);
- it lists fewer frames, when the inliner or a tail call removes them;
- runaway recursion ends the session rather than raising `stack.overflow` (`tests/golden/repl/stack_overflow.out`).

All three are accepted and documented, here and in exceptions.md, for now. The payload could be printed in the REPL
if each exception carried its payload's type descriptor; that is deferred (§6).

Running in the driver's own process adds two more, which the run goldens through `--jit` show:

- a fatal runtime error (an option's ordinal out of bounds, say), which ends a compiled program, ends the driver,
  with the runtime's message and the input's internal source name (`<repl>#N`) as its site;
- a program that calls the compiler's own modules (the questlang tests) calls the running compiler's, and sees its
  state (§1, "the driver is the library").

## 5. Testing

- **Unsound interfaces:** the checks of §3.11 in both compilers, with a test of each rule's error.
- **Frames:** the run goldens that list frames, through the C, ssac, and arm64 backends, after the walk changes.
- **Encoder:** byte-for-byte against `clang -c` on the arm64 goldens (§3.5), in the unit checks.
- **The REPL transcripts** (`tests/source/repl`, `tests/golden/repl`) on the JIT, as a runner mode against the same
  goldens; the `repl` phase runs them with `--no-jit`, checking the interpreter. A transcript that shows an accepted
  difference (§4) is skipped under `--jit` by a marker in its source, as `@skip-phase run_c_compiled` skips a program;
  today that is `rethrow` and `stack_overflow`.
- **The run goldens** through `quest --jit FILE` (`--backend jit-files`), skipping the programs marked
  `@skip-phase: jit` or `@skip-phase: run_c_compiled`, whose differences the JIT shares with compiled code.
  `tests/self-hosted/pending-jit.txt` lists the rest of the differences (§4). The mode also runs `-e`'s transcript
  (`tests/eval`) on the JIT, the uncaught exception's payload left out of the expected header; the `interpret` phase
  runs it with `--no-jit`.
- **Both hosts:** the transcripts through a C-built and an arm64-built stage 2 (`QUEST_BACKEND`).
- tools/check runs these with the backends suite.

## 6. Later

- Printing an exception's payload in the REPL: a descriptor of the payload's type in `QException`, set by every
  backend (the bootstrap's C printer among them), an ABI change.
- Calling earlier inputs' functions directly, and inlining them.
- Registering JIT code with lldb (the GDB JIT interface), with line tables (arm64.md §3.16).
- Surviving faults and runaway recursion, and Ctrl-C, in the REPL.
- Running files on the JIT by default (the REPL and `-e` do, since 2026-11-01).

## 7. Steps

Each step ends with tools/check passing; its documentation changes with it. Steps 1 and 2 change the language and
the runtime for every program, and come first so that the JIT is built on them.

1. **`unsound`** (§3.11). Both compilers' type checkers enforce the rules, with `external` an unsound operation;
   `lib/`'s eighteen modules that bind externals become `unsound module`s, and the four test programs' externals
   move into unsound modules. A test of each rule's error, in both compilers (`tests/errors`). Documented in
   modules.md and extensions.md; roadmap.md drops hot-swapping.
   *Done* (2026-11-01). `external` covers types as well as values and functions, so an interface, even an unsound
   one, may declare no external type, and `tests/elaborate/types`'s external type became a case of the error. A `.qi`
   records `isUnsound`, an ABI change (59). The tests are `tests/errors/typecheck/unsound` and
   `tests/source/modules/unsound_modules`; modules.md §4.4 documents the rules.
2. **Frames by the frame-pointer chain** (§3.9). The runtime's capture and uncaught walk step by `x29`; the
   stack-overflow handler starts from the faulting context. The run goldens that list frames are checked through the
   C, ssac, and arm64 backends, and exceptions.md §5.3 describes the walk.
   *Done* (2026-11-01). The walk is Darwin arm64's (`Q_FRAME_POINTER_WALK`), with function starts from `dladdr` alone;
   other platforms keep the unwinder. Tracebacks through the C and arm64 backends, and the stack overflow's count of
   frames, are unchanged, and no golden changed.
3. **`os/value` and `os/code`** (§3.11): the interfaces, their unsound modules, and a C file in `runtime/`, with an
   ABI bump. Both interpreters refuse a program that imports either, by the interface's name rather than through
   builtins that name the new natives, so that the current release can still build stage 1. **A release follows this
   step.** Tests: an unsound module that reads a tuple's and a record's
   words through `os/value`; one that writes a hand-encoded function into a code region and calls it, and one whose
   function raises and gets the exception back.
   *Done* (2026-11-01, ABI 60). The natives are in `runtime/quest_code.c`; new-libraries.md §4.3 documents both
   interfaces. Both interpreters refuse the modules `os/value` and `os/code` by name. Tests:
   `tests/source/stdlib/os_value` and `os_code` (compiled only) and `tests/errors/run/os_value_interpreted`. Fixed
   alongside: the self-hosted loader gave a separately compiled hierarchical module no external types, so `os/code`'s
   `value.T` differed from `os/value`'s.
4. **Hosts** (§3.3, §3.10): the fingerprint (§3.3.1) and each module unit's `qh_` symbol, in both self-hosted
   backends; the driver imports `list` and `dynamic`. Tests: a program finds its units' fingerprints with `os/code`;
   the fingerprint is unchanged by an interface's comments, declaration order, and location, and changed by a change
   to an exported type, to a manifest type it imports, or to the ABI version.
   *Done* (2026-11-01, ABI 61). `modules/fingerprint` digests a `.qi` and, recursively, those of the interfaces it
   imports; the module compiler passes the digest to the backend, which emits `qh_<unit>` as a C string beside the
   module's record, through the C printer or as an SSA datum. Every module unit now exports a symbol it did not, so the
   ABI changed, which also rebuilds every unit with one. Test: `tests/self-hosted/fingerprints.py`
   (`self-hosted/fingerprints`), which checks the digest against one it computes from the `.qi` files, and so the
   ABI version's part in it.
5. **The encoder** (§3.5), beside the printer in `codegen/arm64`. A unit check encodes every arm64 golden's unit and
   compares the code with the `__text` of the printed assembly assembled by `clang -c`, relocations aside, and the
   data likewise.
   *Done* (2026-11-01). `codegen/arm64/encode` gives each instruction's word beside the printer's spelling of it
   (the printer now exports `expansion`), and lays out a unit's code and data with their relocations and each
   function's offset and size. Labels are resolved; so is a function's call of itself, which `as` resolves too
   (each function is an atom of its own under `.subsections_via_symbols`); every other symbol is relocated. With
   `QUEST_CHECK_ENCODING=1` the backend appends the encoding to a unit's assembly as comments, which
   `tests/self-hosted/encoder.py` (`self-hosted/encoder`) compares with `clang -c`'s object: 390 units, the run
   goldens' programs and the units they link. The driver's own 151 units, built with arm64, agree too. Forms the
   backend can emit but these programs do not (post-index loads, `ldrsw`, `movn`, `cmn`, shifts right by an
   immediate) are encoded from the manual and checked once a program uses them.
6. **The loader and phrase units: the REPL on `--jit`** (§3.2, §3.6–§3.9), after step 3's release: the arena, GOT
   slots and stubs, thread-locals, registration, roots, and function ranges; phrase units, their entries, result
   globals, and earlier inputs' globals; reflection; exceptions and rollback; `system.args`. A runner mode runs the
   REPL transcripts through `--jit` against their goldens, and tools/check runs it.
   *Done* (2026-11-01). `questlang/jit/` holds the loader, reflection, and the session (a sound interface, which
   `driver/repl` uses with `--jit`, over an unsound module). An input is a module of its own whose record holds its
   bindings (§3.2), rather than a global for each. An exception's site is located in the input whose code raised it,
   whose source the unit names `<repl>#N`. `system.args` is also stored into the driver's `system` record, which
   copied the runtime's array when it was initialized. The runner's `--backend jit` mode runs the transcripts, but for
   those marked `@skip-phase: jit` (`rethrow`, `stack_overflow`, §4) and those pending for step 7
   (`tests/self-hosted/pending-jit.txt`: `load`, `modules`); tools/check runs it with the backends. Fixed alongside:
   the encoder's `movn` (no program had used one).
7. **Imports and `-i`** (§3.3, §3.4): imports of the driver's units, refused when stale and, for the user's own
   modules, refused for now; `-i FILE` as the first input. The transcripts through a C-built and an arm64-built
   stage 2 (`QUEST_BACKEND`).
   *Done* (2026-11-01). Before an input runs, the session checks each module it imports: one not in the driver
   (`qm_`) is refused, as is one whose `qh_` differs from the fingerprint of the interface the input was compiled
   against, saying to rebuild the driver. With `--jit` the REPL's environment compiles as a program's does, its
   interfaces from `.qi` files in a build directory (`.build`, or `--build-dir`), which the fingerprints are of. A
   driver without fingerprints (a whole-program build) refuses `--jit` at the start. `-i FILE` runs the file as the
   first input, printing its last result as a program run does, and ends the driver with 1 if it fails. `modules`, which
   imports the user's own modules, is skipped under `--jit`. `tests/self-hosted/jit_hosts.py` checks a stale
   interface, an unchanged one, and a user's module, and runs the transcripts through an arm64-built driver.
8. **Files and `-e`** through `--jit`, each one input. A runner mode runs the run goldens through `quest --jit`;
   exceptions.md and this document list the differences that remain. The time to compile and load an input,
   measured on the transcripts and a few programs, in benchmarks.md.
   *Done* (2026-11-01, ABI 62). Results are printed by the runtime (§3.8), not by reflection, which is gone;
   `jit/reflect`
   with it. `--backend jit-files` runs the run goldens through `--jit`: all pass but those §4 and `pending-jit.txt`
   list (40, 37 of them importing modules of their own), and tools/check runs it. Fixed alongside: the loader's
   `adrp`, and the encoder's `adr`, for a negative distance (`/` truncates, so the high field was wrong), which
   crashed every program whose code called back into an earlier page; a phrase unit's top-level `Ok` bindings, which
   have no words to keep in its record; and the driver now links `collections/hashset` and `util/argparse`, the two
   library modules it did not. benchmarks.md §10 has the times: an input of the transcripts takes 0.2 to 1.5 ms to
   compile, load, and run.

**Releases.** Stage 1 is the release compiling the tree's `questlang/` against its own `lib/` and `runtime/`
(release-compiler.md §2), so a release is needed only when `questlang/` first uses something the release's `lib/` or
`runtime/` lacks:

- Steps 1 and 2 need none. `questlang/` binds no externals, and the release parses `unsound` without checking it.
  Stage 1, which checks it, compiles the tree's marked `lib/`; step 2 changes only `runtime/`, which stage 2 links.
- **Step 3 is followed by a release,** because step 6's `questlang/jit` is the first of `questlang/` to import
  `os/value` and `os/code`. `QUEST_SEED=bootstrap` could bridge the gap instead, but tools/check seeds its
  self-hosting check from the release.
- Steps 4, 5, 7, and 8 need none: `list` and `dynamic` are already in the release's `lib/`, only a test program reads
  the `qh_` symbols, and the rest is `questlang/` alone.
- An optional release after step 8 puts the JIT in the release.

After step 8, whether the JIT becomes the default for the REPL, for files, and for `-e` is decided from those
measurements, as the default backend was. roadmap.md and the README's status table follow each step.
