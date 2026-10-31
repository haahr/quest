# Quest Build Process & Separate Compilation Specification

This document specifies the architectural design of the Quest compiler build process, encompassing separate
compilation (the default) and whole-program compilation modes, compilation artifact management within a dedicated
build directory (`.build/`), interface and module dependency tracking via `.qi` and `.qm` files, queue-driven
transitive closure resolution, self-guarding idempotent module initialization, and build logging.

---

## 1. Overview and Operational Modes

The Quest compiler (`./quest`, the self-hosted compiler, and `./questboot`, the Python bootstrap) supports two
distinct compilation strategies when building executable binaries:

### 1.1. Separate Compilation (Default Mode)
In separate compilation mode:
- Each interface (`.int.quest`) is compiled independently into a Quest Interface metadata file (`.qi`) and, where C
  needs one, a C header file (`<stem>.int.h`, §5.3). Keeping the `.int` of the source name prevents generated headers
  from colliding with or shadowing C standard library headers (such as `<math.h>`, `<string.h>`, or `<time.h>`).
- Each module implementation (`.mod.quest`) is compiled independently into a C implementation file (`<stem>.mod.c`), compiled by
  the host C compiler to an object file (`.o`), and accompanied by a Quest Module metadata file (`.qm`).
- A Quest main routine (`.quest`) is compiled into a `.main.c`, `.main.o`, and `.main.qm` metadata file (§3.2).
- Single-module and single-interface compilations *always* operate in separate compilation mode.
- When compiling an application starting from a main routine, compilation is driven by a dependency queue that builds
  or updates only out-of-date units across the transitive closure of needed modules, followed by linking all object
  files with the Quest runtime into an executable.

### 1.2. Whole-Program Compilation (`--whole-program`)
In whole-program compilation mode:
- Can only be initiated by pointing the compiler at a non-module, non-interface `.quest` file (a **Quest main
  routine**).
- The compiler traverses the entire AST and all imported modules in memory, resolving all bindings into a single
  unified compilation unit.
- Generates a single consolidated C file (e.g. `main.c`), with no `.qi` or `.qm` metadata files produced or read from
  disk.
- The single C file is compiled and linked directly to produce the native executable.
- *Note:* Bytecode/AST interpretation (`interpret`) always operates in whole-program mode, evaluating loaded modules
  directly in memory.

The remainder of this document specifies the architecture and rules for **Separate Compilation**.

---

## 2. Compilation Units vs. The Full Build Process

A fundamental architectural distinction exists between **compiling an individual compilation unit** and executing a
**full build**:

```
                       ┌─────────────────────────┐
                       │   Quest Main Routine    │ (non-module, non-interface .quest)
                       └────────────┬────────────┘
                                    │ triggers
                                    ▼
                       ┌─────────────────────────┐
                       │   Full Build Process    │ (Queue-driven dependency resolution)
                       └────────────┬────────────┘
                                    │ orchestrates
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
┌───────────────────────┐ ┌───────────────────────┐ ┌───────────────────────┐
│ Interface Compilation │ │  Module Compilation   │ │   Main Compilation    │
│ (.int.quest ->        │ │ (.mod.quest ->        │ │ (.quest ->            │
│   <stem>.int.h/.qi)   │ │   .qm/.mod.c/.o)      │ │   .main.{qm,c,o})     │
└───────────────────────┘ └───────────────────────┘ └───────────────────────┘
```

1. **Compilation of an Interface (`.int.quest`):**
   - Validates that the file contains exactly one `interface` declaration.
   - Typechecks the interface signatures in isolation (or with imported interfaces).
   - Emits:
     - `<stem>.int.h`: C typedefs, struct signatures, and function prototypes (named to avoid C header collisions, §3.2).
     - `.qi`: Serialized public interface metadata (types, kinds, signatures, and imported interfaces).
   - Does not invoke the host C compiler.

2. **Compilation of a Module (`.mod.quest`):**
   - Validates that the file contains exactly one `module` definition conforming to its declared interface.
   - Loads imported interfaces (regenerating stale `.qi` files as needed) to typecheck module members, and brings
     the header of the interface it implements, which its C includes, up to date (§5.3).
   - Notes imported modules without recursively compiling their implementations.
   - Emits:
     - `<stem>.mod.c`: C implementation code and exported module record initialization functions.
     - `.qm`: Quest Module metadata recording imported modules, imported interfaces, and dependency timestamps.
   - Invokes host C compiler (`clang` or `gcc`) to compile `<stem>.mod.c` to `<stem>.o`.

3. **Compilation of a Main Routine (`.quest`):**
   - Typechecks the top-level phrases and expressions against imported interfaces.
   - Emits:
     - `.c`: C implementation containing the `main()` entrypoint.
     - `.qm`: Metadata recording all imported modules and imported interfaces.
     - `.o`: Relocatable object file compiled from `.c`.

4. **Full Build Process (Targeting a Quest Main Routine):**
   - Initiated when the compiler driver is invoked on a Quest main routine (e.g. `quest main.quest` or
     `quest -o myapp app.quest`).
   - Executes a queue-driven build loop that determines the transitive closure of needed modules, checks staleness,
     rebuilds out-of-date interfaces and modules, and links all object files into the final executable.

### 2.1. The Unit Graph
Every consumer of units (the type checker's loading, the interface and module compilers, the build engine, the
interpreter, and the driver) works on one structure, the **unit graph** (`quest/modules/graph.py`), rather than
resolving imports and placing artifacts in its own way:

- **Units.** A unit is a program (a main routine or inline code, never imported), a module file, or an interface
  file, including the standard library's (`UnitKind`; `file_unit_kind` classifies a file by its suffix). A unit is
  identified by its kind and its canonical name ([modules.md §2.3](modules.md)).
- **Resolution, once.** An import is a path written in a unit, resolved from the unit's directory with the search
  paths and program directory (`Roots`). `Resolver` resolves each (path, directory, roots) once per compilation
  session and returns a `Resolved`: the unit's source (`.int.quest` or `.mod.quest`), for an interface without a
  source its prebuilt `.qi` (Rule 3, §5), and its names: `canonical_name` (the unit's key), `interface_name` (an
  interface's canonical name as importers record it, with the declared base name, `util/Path`), and `artifact_name`
  (where an interface's artifacts are placed). Every consumer of an import receives that one result. Resolution
  depends only on which source files exist, which a compilation never changes; artifacts, which it does write, are
  looked up when needed (`fresh_interface_qi`, a fresh `.qi` on the search path). A file given directly rather than
  imported (the unit file the driver compiles, a module source the build engine found) is named by `Resolver.file`.
  A session is a driver run (so each test the test runner runs; [testing.md §2.3](testing.md)), a build, or one REPL
  input (`UnitGraph.new_session` forgets the resolutions before each, so that files created since are found). A build
  (`BuildEngine`) has one resolver, which the units it compiles share, and the pipeline's C phases hand theirs to the
  build that links the program's modules.
- **Edges.** A unit's imports are its edges: an interface's are the interface paths it imports
  (`interface_import_paths`), each resolved from its directory; `Resolver.interface_dependencies` follows them
  transitively, for the `.qi` dependencies (§4.2) and the indirect entries of `.qm` manifests (§7.2).
- **Type-checked forms.** `UnitGraph` holds the units a type-checking `Environment` has loaded (`env.units`), each
  with its elaborated forms: an interface's scope, a module's typed module, the export scope of a module known only
  through its interface, and whether a module is typed through its interface alone (precompiled). Typed forms hold
  the symbols one elaboration minted, so each Environment has its own graph; the graphs of one session (an
  interface compiled for an importer, a module the interpreter elaborates on demand) share its resolver. A module the
  interpreter has run has its value, the record of its members, in the interpreter's runtime environment
  (`module_values`, by canonical name), so each module is run once per program. The runtime environment holds the
  graph of the Environment that type checked its program, the same object. Prebuilt objects given to the driver mark their modules precompiled (`add_prebuilt_objects`).
- **The REPL's graph.** The REPL keeps one graph across its inputs ([repl.md §5](repl.md)). Each input is a session
  (`new_session`); units loaded by earlier inputs stay loaded. An input that fails is rolled back with `snapshot` and
  `restore`, which forget the units it loaded and change the graph in place, so the runtime environment, holding
  the same graph, sees the rollback; the runtime environment's own `restore` forgets the modules the input ran.
- **Artifacts.** A unit's artifacts are named by its canonical name under a build directory (§3.2):
  `unit_artifact_dir`, `interface_qi_file`, and `ModuleArtifacts` (`.qm`, `.mod.c`, `.o`). Their staleness rules
  are §5 (interfaces, `ensure_resolved_interface_artifacts`), §5.3 (headers), and §7.1 (modules and main routines,
  `unit_staleness` with `import_resolution_change`, which resolves a manifest's recorded imports again through the
  resolver).

The graph lives in `quest.modules`, below C compilation: the C backend uses it (to write the headers of resolved
interfaces, `ensure_resolved_interface_header`) but the graph never reaches the C backend.

---

## 3. Dedicated Build Directory Layout (`.build/`) and Artifact Placement

### 3.1. Full Application Builds vs. Standalone Compilation
The compiler driver differentiates between orchestrating a full build of an application and compiling an isolated unit:

- **Full Application Builds (`quest main.quest`):**
  All intermediate artifacts (`.qi`, `*.int.h`, `.qm`, `.mod.c`, `.main.c`, `.o`, and `build.log`) reside strictly within a dedicated
  build directory (default `.build/` in the project root, or `--build-dir <dir>`). Source trees (`lib/`, `tests/`) are
  never modified by the build process.
- **Pipeline C Phases (`--stop-after codegen_c` / `run_c_compiled`, `--emit-c`, `-o` with objects):**
  These always have a build directory (`--build-dir <dir>`, default `.build/` in the current directory), and every
  interface and module they depend on is built there by the same build engine as a full application build (§7.3).
  Nested interface and module compilations inherit the same build directory. Only the main routine itself
  is handled differently: its C code is kept in memory (or written where `-o` / `--emit-c` say) rather than as
  `.build/<dir>/<main>.main.{qm,c,o}`.
- **Standalone Unit Compilation (`quest -c unit.int.quest` or `quest -c unit.mod.quest`):**
  - If `--build-dir <dir>` is specified, outputs are routed into `<dir>`.
  - If `-o <path>` is specified, outputs are placed in the directory containing `<path>`.
  - If neither is specified, outputs default to the source file directory (`file_path.parent`). This preserves
    isolated single-file tool workflows and localized unit tests without creating unintended `.build/` trees.

Compiled artifacts found outside the build directory (for example a `.qi`/`.int.h` or `.qm`/`.mod.c`/`.o` left next to a source
file by a standalone compilation) are used like those in the build directory when they are fresh: at least as new
as their sources and recording the running compiler's ABI version (§5.2).

```
quest/
├── lib/                             # Source files only
│   └── util/
│       ├── path.int.quest
│       └── path.mod.quest
│
└── .build/                          # Mirror build directory (for full builds)
    ├── build.log                    # Compilation and queue audit trail
    ├── util/
    │   ├── path.int.h               # Generated interface header (.int avoids libc collisions)
    │   ├── path.qi                  # Generated interface metadata
    │   ├── path.mod.c               # Generated module C implementation
    │   ├── path.qm                  # Generated module metadata
    │   └── path.o                   # Compiled native object file
    └── tests/
        ├── test_path.main.qm        # Main routine metadata
        ├── test_path.main.c         # Main routine C code
        ├── test_path.main.o         # Main routine object file
        └── test_path                # Linked executable (unless -o says otherwise)
```

### 3.2. Path Mapping Conventions
1. **Modules and Interfaces:**
   Artifact paths map directly to the canonical module path (`docs/modules.md` §2.3) inside `.build/`:
   - Interface `util/Path` (`lib/util/path.int.quest`) -> `.build/util/path.qi`, `.build/util/path.int.h`.
   - Module `util/path` (`lib/util/path.mod.quest`):
     `.build/util/path.qm`, `.build/util/path.mod.c`, `.build/util/path.o`.

   **Units of different programs can share artifact paths.** A canonical name identifies a unit only within one
   program's roots: its include paths and its program directory (`docs/modules.md` §2.3). Programs built into the same
   build directory with different roots can have different units with one canonical name, and so with one set of
   artifact paths. For example, `a/counter.mod.quest` and `b/counter.mod.quest`, each beside its program
   (`a/main.quest`, `b/main.quest`) and under no include root, are both named `counter`, and both build to
   `.build/counter.{qi,int.h,qm,mod.c,o}`. Units at the same relative path under different include roots (`-I x` with
   `x/util/path.mod.quest`, `-I y` with `y/util/path.mod.quest`) share paths the same way.

   This is correct but costs rebuilds, and is accepted rather than avoided. Every `.qi` and `.qm` records the source
   it was built from, and artifacts are reused only for that source (§5 Rule 1, §7.1 rule 5). So each program is
   always built from its own units, but building the programs alternately recompiles the shared units every time.
   A build directory per program (`--build-dir`) avoids the rebuilds.
2. **C Header Collision Prevention (`.int.h` and `.mod.c`):**
   Generated C files keep the `.int` or `.mod` of their source's name: `math.int.quest` generates `math.int.h`
   and `math.mod.quest` generates `math.mod.c`. The build directory and its subdirectories are on the host C
   compiler's include path, so a header named `math.h` would shadow `<math.h>` (included by the runtime) for every
   translation unit; no C library header has a name ending in `.int.h`. Generated C code includes
   `#include "util/path.int.h"`.
3. **Main Routines:**
   Artifacts mirror the source file's directory relative to the current directory, and carry a `.main` suffix:
   - `tests/test_path.quest` -> `.build/tests/test_path.main.qm`, `.build/tests/test_path.main.c`,
     `.build/tests/test_path.main.o`, and (when the API is not given an output path) the executable
     `.build/tests/test_path`.
   - A main routine outside the current directory has its artifacts at the top of `.build/`.

   Main routines are never imported, so they need no canonical name; mirroring their directory keeps `a/main.quest`
   and `b/main.quest` apart in a shared build directory. The `.main` suffix keeps them apart from the artifacts of
   a module with the same canonical path (`.qm` and `.o`), as `.mod.c` and `.int.h` do for modules and interfaces,
   so a main routine `m.quest` and a module `m.mod.quest` may share a directory.
   Even when two main routines do share artifact paths (both outside the current directory), each `.main.qm`
   records its source, and a main routine's artifacts are reused only for that source (§7.1).
4. **C Compiler Include Paths:**
   When compiling generated `.c` files to `.o`, the host C compiler is invoked with `-I <build-dir> -I runtime`,
   allowing `#include "util/path.int.h"` to resolve directly against generated headers in `.build/`.

---

## 4. Compilation Artifacts and Metadata Formats

The compilation process produces four distinct artifact types alongside source code:

| Artifact | Source File | Purpose | Generated By | Consumed By |
| :--- | :--- | :--- | :--- | :--- |
| **`.qi`** | `.int.quest` | Quest Interface metadata | Interface Compiler | Module Compiler, Importers |
| **`<stem>.int.h`** | `.int.quest` | C header file (typedefs, structs) | C backend (§5.3) | Host C Compiler |
| **`.qm`** | `.mod.quest`, `.quest` | Module metadata (imports) | Module/Main Compiler| Build Queue, Linker |
| **`.mod.c`/`.o`** | `.mod.quest` | C source and native object code | Module Compiler & C Compiler | Host Linker |
| **`.c`/`.o`**| `.quest` | C source and native object code | Main Compiler & C Compiler | Host Linker |

### 4.1. Manifest-Driven Dependency Tracking
Module dependency tracking and transitive closure resolution are governed directly by `.qm` manifests rather than
Make-style `.d` object prerequisite files, capturing both Quest interface-to-module contracts and semantic metadata.

### 4.2. Quest Interface Metadata (`.qi`)
A `.qi` file contains the complete type signature of an interface:
- Canonical interface name and declaring source path.
- List of imported interfaces.
- The interfaces it depends on (`deps`): those it imports, those they import, and so on, each with the path as
  written, the directory of the interface that imports it (the path was resolved from there, by sibling search,
  before the include paths), and the source it resolved to. They make the `.qi` stale when one of them changes
  (§5, Rule 1).
- Exported type declarations (abstract types, manifest definitions, records, variants, options).
- Exported value signatures and parameter modes (`val`, `var`, `out`).

#### 4.2.1. Type Alias Preservation and Size Compactness
To avoid exponential code expansion and multi-megabyte interface metadata files:
- **Alias Preservation:** References to type aliases are alias reference nodes (`docs/type-system.md` §2.2), and the
  interface compiler writes them under the name written in the interface source (e.g. `ast.TypeExpr`, `ast.Expr`,
  `FormalParam`) rather than expanding their definitions. On load the names resolve in the `.qi`'s own imports and
  declarations, so alias names survive the round trip.
- **Abstract Types by Their Modules' Names:** An imported module's abstract type is written under the module's own
  name (`vector.T`), not the name the interface imported it as (`vec = collections/vector`). So the loader registers
  each module a `.qi` imports under its own name too, unless another module is already registered under that name.
- **Two-Pass Type Deserialization:** When loading `.qi` files in `load_interface_from_qi_file`, type declarations are
  processed in two passes:
  1. *Symbol Registration Pass:* All type symbols are declared with fresh symbol IDs and kinds into the interface scope.
  2. *Definition Elaboration Pass:* Concrete manifest type strings are parsed and elaborated with all interface types
     already visible in scope. This enables forward and mutual references among types without undefined type errors.

### 4.3. Quest Module Metadata (`.qm`)
A `.qm` file records the build manifest for an implementation module or main routine:
- `name`: Canonical module name (e.g. `"util/path"`) or `"<main>"`.
- `interface`: Canonical interface name (e.g. `"util/Path"`) for modules; `null` for main routines.
- `source`: Path to source file (`.mod.quest` or `.quest`).
- `object`: Path to compiled `.o` file in `.build/`.
- `imported_modules`: Array of imported modules with canonical module and interface names (`docs/modules.md` §2.3),
  the source file the importer found (empty for builtin and prebuilt modules), which the build engine compiles, and
  the module path the importer resolved (as written in its import, or the name of a module it uses implicitly):
  `[ { "name": "util/strutil", "interface": "util/Strutil", "source": "/src/lib/util/strutil.mod.quest",
  "path": "util/strutil" }, ... ]`.
  A manifest without `source` (written before it was recorded) is followed by finding the file with that canonical name.
- `imported_interfaces`: Array of imported interfaces with canonical names, source paths, timestamps, and the
  interface path the importer resolved (for a module, including the interface it implements):
  `[ { "name": "util/Path", "source": "lib/util/path.int.quest", "mtime": 1727891234, "path": "util/Path" }, ... ]`.
  It also lists the interfaces the unit depends on through those interfaces' imports (§7.2), each with `dir`, the
  directory of the interface that imports it, which its path is resolved from; for the unit's own imports `dir` is
  absent or empty and the path is resolved from the unit's directory.

The recorded paths let a later build check that each import still resolves to the recorded source (§7.1, rule 4).
Every entry is written from the unit graph's resolution of the import (§2.1), the one its compilation used.

### 4.4. Builtin Runtime Modules (`BUILTIN_RUNTIME_MODULES`)
Certain core modules are implemented directly in the native C runtime (`runtime/quest_runtime.c`, with
`BuiltinModuleRegistry` providing the interpreter runtime symbol bridge) rather than as Quest source files:
- **Registry Set:** `BUILTIN_RUNTIME_MODULES = { "dynamic" }`.
- **Interface Exposure:** Each runtime module defines a standard Quest interface (`dynamic.int.quest`), producing
  `dynamic.qi` and `dynamic.int.h` for static typechecking.
- **No Implementation Artifacts:** Runtime modules do not have a `.mod.quest` source file or a separate `.o` object
  file; their implementations are permanently linked into the Quest runtime library.
- **Build Engine Behavior:** When an imported module belongs to `BUILTIN_RUNTIME_MODULES`, the build engine does not
  attempt to compile a `.mod.quest` or locate a separate `.o` file to link.

---

## 5. Interface Import Resolution & Staleness Rules

When compiling any source file (module, interface, or main routine) that imports an interface `I`:

```
                           ┌─────────────────────────┐
                           │   Import Interface I    │
                           └────────────┬────────────┘
                                        │
                             Find I.int.quest, I.qi
                                        │
               ┌────────────────────────┴────────────────────────┐
               ▼                                                 ▼
       I.int.quest exists                                 Only I.qi exists
               │                                                 │
       ┌───────┴───────┐                                         │
       ▼               ▼                                         │
    I.qi            I.qi                                         │
    missing         present                                      │
       │               │                                         │
       │         Check datestamps:                               │
       │         I.int.quest > I.qi?                             │
       │         ┌─────┴─────┐                                   │
       │       Yes           No                                  │
       ▼       ▼             ▼                                   ▼
  ┌─────────────────┐   ┌─────────────────┐             ┌─────────────────┐
  │   OUT OF DATE   │   │   UP TO DATE    │             │   UP TO DATE    │
  │ Compile I first │   │  Read from .qi  │             │ (Precompiled/   │
  │ into .build/    │   │                 │             │  No Source)     │
  └─────────────────┘   └─────────────────┘             └─────────────────┘
```

The compiler applies three strict rules in order:

1. **Rule 1 (Source and Artifacts Present):**
   If `I.int.quest` and `I.qi` both exist:
   - Compare filesystem modification timestamps (`mtime`). The bootstrap compares Python's float `st_mtime`. The
     self-hosted compiler compares exact nanoseconds (`os/fileStats`'s `modifiedNs`), taking each file's from a
     single `stat`. The two order files modified at least a microsecond apart the same way. The times recorded in a
     `.qm` are the float seconds in both compilers.
   - If `I.int.quest` is newer than `I.qi`, the artifacts are **out of date**.
   - If `I.qi` is newer than or equal to `I.int.quest`, the artifacts are **up to date**.
   - In either case, if `I.qi` records a different source (`source`) than this `I.int.quest`, the artifacts belong to
     another interface with the same canonical name (§3.2) and are **out of date**.
   - They are also **out of date** if an interface `I` depends on (its `deps`, §4.2) has a source newer than `I.qi`,
     or would now resolve to a different source. `I`'s signatures and generated header use the types of the
     interfaces it imports, so they change with them.

2. **Rule 2 (Source Present, Artifacts Incomplete):**
   If `I.int.quest` exists but `I.qi` is missing from `.build/`, the artifacts are **out of date**.

3. **Rule 3 (Binary Distribution / Precompiled Mode):**
   If `I.qi` (with `I.int.h`, for C compilation) exists in `.build/` (or an include directory) but `I.int.quest` does
   not exist:
   - The artifacts are assumed to be **up to date**.
   - This explicitly enables compiling against distributed precompiled Quest standard libraries or third-party
     packages without requiring the original source files.

### 5.1. Action on Interface Staleness
If an interface is determined to be **out of date**:
1. The compiler immediately pauses the dependent compilation unit.
2. The interface compiler compiles `I.int.quest`, generating `I.qi` in `.build/` (and, in C compilation, `I.int.h`,
   §5.3).
3. If interface compilation fails, compilation aborts with diagnostic messages referencing `I.int.quest`.
4. Once regenerated, the compiler resumes compiling the dependent unit, reading signatures from the fresh `I.qi`.

These rules are implemented once, by `ensure_resolved_interface_artifacts` in `interface_compiler.py`, for an
interface the unit graph has resolved (§2.1). It is called by `load_interface` whenever an interface is loaded from its
`.qi` (every driver run, §5.2.4, and C compilation), and by the interface compiler for each interface an interface
imports, even for interfaces the typechecker resolves without loading them (such as builtin interfaces like
`Writer`). `ensure_interface_artifacts` resolves an interface path first, for callers that start from one.

### 5.2. An ABI Version and Trusting Fresh Artifacts
**Status:** implemented (`quest/config/abi.py`, `tests/abi/`, and §5.2.4 in `module_loader.py`).

The intended model is that compiled artifacts are used whenever they are fresh: `.qi` and `<stem>.int.h` instead of
re-elaborating an `.int.quest`, and `.qm`, `.c` (`.mod.c` for a module), and `.o` instead of recompiling a `.mod.quest`
or main routine.
Freshness is currently judged by timestamps alone (Rules 1–3), which cannot tell whether an artifact was produced
under the same artifact contract as the running compiler. The stopgap in §3.1 (source always wins outside the build
directory) avoids trusting such artifacts, at the cost of re-elaborating every imported source on every run.

Two distinct concerns are involved:
1. **Reusing artifacts.** An artifact can be reused by another compiler, or another version of the same compiler, as
   long as both agree on the *artifact contract*: the `.qi`/`.qm` formats and the language of the type strings they
   contain, and the binary interface of the generated code. A correct `.o` produced last month links correctly with
   today's output if the contract has not changed, regardless of which implementation (the Python bootstrap compiler
   or the self-hosted compiler) produced it.
2. **Testing the compiler.** A change to code generation inside an unchanged contract (for example a regression in a
   function body) is invisible to artifact reuse, and should be: old artifacts remain correct. The compiler's own
   tests must exercise current code generation, so they build into a fresh directory (`docs/testing.md` §2.3) rather
   than relying on artifact invalidation.

#### 5.2.1. The ABI Version
Every `.qi` and `.qm` records:
- **`abi`: the artifact contract version,** an integer starting at 1, declared as an ordinary constant
  (`ABI_VERSION`) by every Quest compiler. The Python and self-hosted compilers share the number, which is bumped when
  either compiler's contract changes, but their artifacts may differ (docs/testing.md §2.8). A packaged compiler
  carries the constant in its code; nothing reads compiler sources at run time. The two compilers declare the
  constant separately, and `tests/python/test_abi_version.py` checks that they agree. If the self-hosted compiler
  gains a Makefile, it should generate its constant from the Python compiler's
  (`bootstrap/python/quest/config/abi.py`).
- **`producer`: the compiler that wrote the artifact,** its name and an ordinary version number bumped by hand
  (`quest-bootstrap 0.1`, or `questlang 0.1` for the self-hosted compiler). A compiler uses only the artifacts it
  wrote itself: one of the other's is out of date, as one of another ABI version is (§5.2.2), and rebuilt if its
  source is there.

The ABI version covers:
- the layout and meaning of `.qi` and `.qm` files, including the syntax and meaning of the type strings in `.qi`;
- the C representation of Quest types (struct layouts, value and pointer representations, evidence dictionaries,
  type descriptors);
- symbol name mangling (`docs/name-mangling.md`) and calling conventions, including type-descriptor parameters for
  polymorphic functions and module initialization (§8);
- the runtime interface generated code uses (`runtime/quest_runtime.h`);
- the names of generated files (`<stem>.int.h`, `<stem>.mod.c`, §3.2), since headers `#include` one another by name.

Placement:
- **`.qi`:** two new fields, `abi: Int` and `producer: String`, in the `QI_SCHEMA_TYPE_STR` record. Because the
  schema type itself changes, older `.qi` files no longer match it on load and are treated as stale.
- **`<stem>.int.h`:** a leading comment `/* quest abi <version> producer <producer> */`, for diagnosis only. A header is
  produced from the interface its `.qi` describes, and its freshness is decided by the `.qi` (§5.3).
- **`.qm`:** top-level keys `"abi"` and `"producer"`. A `.c`/`.o` pair is produced together with its `.qm`, and its
  freshness is decided by the `.qm`. The self-hosted compiler's also records `"backend"`, the backend that compiled the
  unit (`c`, `ssac`, or `arm64`, whose unit is `.mod.s` rather than `.mod.c`; `c` when absent, [arm64.md](arm64.md)
  §3.12): a unit the build's choice of backends (`--backend`, `--unit-backend`) assigns to another is stale, as
  `compiled by the <backend> backend`.

#### 5.2.2. Staleness Rules with the ABI Version
An artifact is **up to date** when it exists, is at least as new as each source it depends on (Rules 1 and 2 and the
`.qm` import timestamps, unchanged), **and** its recorded `abi` equals the running compiler's `ABI_VERSION`. A
missing, unreadable, or different `abi` makes it **out of date**, and it is rebuilt as today. A binary distribution
(no source, Rule 3) is checked the same way; since it cannot be rebuilt, a mismatch is a compilation error naming
the artifact and both versions.

With these rules the §3.1 stopgap is removed: a fresh artifact found next to a source file, or on the include path,
is used like one in the build directory. Rebuilding an interface after an ABI change gives it a newer timestamp, so
dependents are rebuilt by the existing transitive invalidation rule (§7.2).

#### 5.2.3. Keeping the ABI Version Honest
A version number is only as reliable as the discipline of bumping it, so a test enforces it. A checked-in ABI corpus
(`tests/abi/corpus`) records, for a frozen snapshot of every interface in the library and in `questlang/`
(`tests/abi/inputs`):
- the generated `.qi` files and `<stem>.int.h` headers, with the producer stamp and comments left out;
- a digest of `runtime/quest_runtime.h`;
- the self-hosted compiler's table of the standard library's externals (`questlang/codegen/externals.mod.quest`),
  whose functions importers call directly ([c-representation.md](c-representation.md) §6.2).

The inputs are a snapshot, not the live library, so that the corpus changes only when the compiler's output for the
same input changes; editing a library interface is a source change, not a contract change.
`python tests/abi/corpus.py --update` regenerates the corpus after a bump, and `--refresh-inputs` re-snapshots the
interfaces first.

`tests/python/test_abi_corpus.py` regenerates the corpus and fails if anything differs while `ABI_VERSION` is unchanged ("artifact contract
changed: bump ABI_VERSION and update the corpus"). Reading compiler and runtime sources here is a test's business, not
the compiler's. The same corpus serves as a cross-check of the self-hosted compiler: at the same ABI version, both
compilers keep corpora of their own: `tests/abi/corpus` is the bootstrap's, and `tests/abi/corpus-self-hosted` the
self-hosted compiler's, which its suite regenerates with the self-hosted driver and compares
(`self-hosted/abi_corpus`).

The self-hosted compiler (`questlang/`, run by `./quest`) writes its artifacts in the same places, under the same
rules, and with the same engine (`questlang/build/engine`, a port of this document's `BuildEngine`). Until the two
compilers diverged, it wrote the same artifacts as the bootstrap, up to the producer. Now they may differ, as
optimizations go into the self-hosted compiler alone, so neither compiler uses the other's artifacts
(§5.2.1). `run_tests.py --self-hosting` checks the self-hosted compiler's fixed point, and that the bootstrap still
builds the compiler the release does (docs/testing.md §2.3).

`./quest` builds the self-hosted compiler in two stages under `.build/quest-stages`, each an ordinary incremental build
with its own build directory (docs/release-compiler.md §2):
1. The seed builds stage 1. The seed is the current release, which every worktree shares (in the common git
   directory's `quest-release/`, docs/release-compiler.md §1), compiling against its own `lib/` and `runtime/` (its
   `home/`) and finding the tree's `questlang/` through `-I`, or the bootstrap.
2. Stage 1 builds stage 2 against the tree's `lib/` and `runtime/`, through the backend `QUEST_BACKEND` names (`c`,
   the default, `ssac`, or `arm64`; [arm64.md](arm64.md) step 12), so that stage 2 is the compiler as that backend
   compiles it. Another backend's stages are kept in `.build/quest-stages-BACKEND`, so that switching rebuilds
   neither.

The stages record their seed and are discarded when it changes. A release's `home/` has its commit's file times, so
§5's timestamp rules cannot compare artifacts built against one release with another release's sources.

What this misses: a contract change that nothing in the corpus exercises. The corpus covers the whole library and the
test suite's interfaces, and grows when a gap is found.

The corpus deliberately leaves out the link-level surface between units: the symbols each unit defines and references
that no header declares, such as module initialization functions and module records (each `.c` declares those of its
dependencies with `extern`). Changing them is still an ABI change and needs a bump; renaming module records from
`qv_m` to `qm_m` was one. But a forgotten bump there fails loudly, as an undefined symbol when linking against an
older object, whereas a forgotten bump for a layout or calling-convention change links and then misbehaves silently.
The corpus concentrates on the silent kind.

#### 5.2.4. Using Artifacts Outside C Compilation
Every driver run has a build directory (`--build-dir`, default `.build/` in the current directory), not only C
compilations, and the typecheck and interpret phases use it too:
- **Interfaces:** every phase loads an imported interface from its `.qi`, building or rebuilding it first when it is
  missing or stale. Loading an interface builds only the `.qi`; generating the C header is costly and only C
  compilation needs it, so a C build writes the headers it needs when they are missing or older than their `.qi`
  (§5.3).
- **Modules, when typechecking only** (`--stop-after typecheck`): a module whose `.qm`, `.mod.c`, and `.o` are fresh, in
  the build directory or next to its source, is typed through its interface alone, without elaborating its body or
  re-proving conformance, as separate C compilation does (`separately_compiled_module_scope`). Without fresh
  artifacts the module is elaborated from source; a typecheck never invokes the C compiler.
- **Modules, when interpreting:** the interpreter executes module bodies (it reuses the module trees elaborated while
  typechecking), so they are always elaborated from source; only their interfaces come from `.qi`. Caching elaborated
  module bodies would be a separate design.

Programs that drive the compiler through its API (`CompilerOptions` without a `build_dir`) keep elaborating from
source. On the `syntax_ast` test, which imports the self-hosted `ast` and `astprint` modules, a typecheck takes about
0.8 s from source and 0.3 s once a C build has produced the module artifacts.

Typecheck dumps must not depend on whether an interface came from source or from `.qi`. Alias reference nodes
(`docs/type-system.md` §2.2) keep alias names across the `.qi` round trip, and
`tests/python/test_separate_compilation_types.py` checks that the two paths agree.

#### 5.2.5. Consequences for Testing
Users get artifact reuse across compiler versions that share an ABI version. The compiler's own test runs keep
building into a fresh temporary directory by default, so that they always exercise current code generation;
`--build-dir` remains available to reuse a directory when speed matters more than hermeticity.

### 5.3. Interface Headers Belong to C Compilation
An interface's C header (`<stem>.int.h`) is written by the C backend (`quest/codegen/c/headers.py`), not by the
interface compiler, so loading an interface (which the type checker does) never reaches the C backend
(`tests/python/test_dependencies.py` checks that nothing outside C compilation does). C compilation writes the headers
it needs, beside their `.qi` files:

- **Compiling an interface file** (`quest -c x.int.quest`, `compile_interface_with_header`) writes its `.qi` and its
  header, and with a build directory, the headers of the interfaces it imports.
- **Compiling a module** (`module_compiler.compile_module`, and the pipeline's `codegen_c` phase on a module file,
  `unit_interface_header`) brings the header of the interface it implements up to date before generating C, since
  the module's C `#include`s it (`ensure_imported_interface_header`), and includes it by the interface path as
  written if that finds a header on the C include path, else by that header's path relative to the include path
  (`find_interface_header`). A main routine's C includes no interface header, so compiling one writes none.
- **A header `#include`s the headers of the interfaces its interface imports,** so writing one first brings those
  up to date in the build directory, including those of builtin interfaces that are never loaded from source.

A header is **up to date** when it exists and is at least as new as its `.qi` (`header_is_current`). The `.qi` is
rewritten whenever its interface's source, or an interface it depends on, changes (Rules 1 and 2) or the ABI version
changes (§5.2.2), so the header follows the `.qi`'s staleness rather than repeating it. `ensure_interface_header`
first brings the `.qi` up to date (an interface rebuilt for it gets its header at the same time), then:
- a header missing or older than a fresh `.qi` in the build directory (for example after a typecheck or interpret run
  built only the `.qi`) is written from the interface elaborated again, leaving the `.qi`, and so every unit compiled
  against it, untouched;
- a fresh `.qi` found outside the build directory (from a standalone compilation) whose header is missing or stale
  is rebuilt with its header in the build directory, rather than writing into the source tree;
- without a source (Rule 3), the header is used as found.

Headers are written only where C needs them: after a full build, the build directory has headers for the interfaces
of the modules compiled and for the interfaces those headers include, not for interfaces that only a main routine
or the type checker loaded.

---

## 6. Module Import Handling and Import Discipline

When source code imports a module `M`:
```quest
import util/path : util/Path
```

The compiler strictly separates interface binding from implementation scheduling:
1. **Interface Binding Only:**
   - The compiler resolves and loads the interface `util/Path` using the rules in §5.
   - It checks that all usages of `path.<member>` conform to the signatures declared in `util/Path`.
2. **Deferred Module Implementation:**
   - The compiler does **not** load, parse, or compile `util/path.mod.quest` during this step.
   - It records the dependency tuple `(name: "util/path", interface: "util/Path")`.
3. **Artifact Persistence:**
   - This dependency is persisted to the `.qm` metadata file under `imported_modules`.

### 6.1. Strict Module Isolation for Modules and Interfaces (*Typeful Programming*)
In accordance with Luca Cardelli's *Typeful Programming* principles, Quest modules and interfaces adhere to strict
module isolation:
- Every imported interface and module used within a `.mod.quest` or `.int.quest` file **must be explicitly declared**
  in the file's header import clauses (`import m = mod : Mod`).
- Modules and interfaces never receive implicit or ambient module imports. All external dependencies must be
  explicitly stated, ensuring self-contained and auditable compilation units.

### 6.2. Implicit Standard Library Module Discovery for Main Routines
In contrast to modules, Quest application main routines (`.quest` files) frequently utilize language syntactic
conveniences and core operations (such as string concatenation `^` or array slicing) whose generated C code relies
on runtime helper operations provided by standard library modules (e.g. `string`, `arrayOp`).
- Main routines are not required to manually write boilerplate import clauses for core standard library helpers.
- Lowering a main routine to the IR treats each standard library module it uses without importing it as an import of
  it with its interface (`module_ref` in `ir/lower.py`), including a library module compiled from source (`list`,
  from `lib/list.mod.quest`); `implicit_imports` in `codegen/backend.py` lists them.
- These implicitly referenced modules are automatically recorded into the main routine's `.main.qm` under
  `imported_modules`.
  (`unit_module_refs` in `build/engine.py` computes this list, explicit imports plus implicit ones, for both full
  builds and the pipeline's C phases.)
- The build engine then queues and links them transitively into the final executable just like explicitly imported
  modules.

### 6.3. Inter-Module Interface Conformance Verification
Because separate compilation decouples the compilation of an importing unit from the imported module's implementation:
- An importing compilation unit compiles and typechecks strictly against the imported interface (`Iface.qi`).
- The imported module compiles and typechecks strictly against its own declared interface (`ActualIface.qi`).
- To prevent type mismatches and binary desynchronization across separate compilation boundaries, the build engine
  explicitly enforces that the module's declared interface (`mod.qm.interface`) conforms to the interface expected by
  each importer (`imported_modules[...].interface`).
- **Canonical Name Representation:** All module and interface references recorded in `.qm` metadata files are
  canonicalized (e.g. `util/path` and `util/Path`).
- **Strict Canonical Equality:** Interface conformance is evaluated strictly on canonical interface name equality
  (`actual == expected`). If an importer expects canonical interface `gui/Window` but the imported module implements
  `os/Window`, or if package prefixes differ across modules, the build engine immediately detects the mismatch and halts
  compilation with a fatal type error (`Type error: '<importer>' imports module '<mod>' as interface '<expected>', but
  module '<mod>' implements interface '<actual>'`) before generating binary code or invoking the linker.

---

## 7. The Queue-Driven Full Build Process

Building a Quest application begins with a Quest main routine. The build engine employs a **FIFO work queue** to compute
and rebuild the transitive closure of required modules.

```
                              ┌────────────────────┐
                              │  Queue main.quest  │
                              └─────────┬──────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                       ┌──────>│ Queue Empty?    ├──────> [ Proceed to Link ]
                       │       └────────┬────────┘
                       │                │ No
                       │                ▼
                       │       ┌─────────────────┐
                       │       │  Pop next item  │
                       │       └────────┬────────┘
                       │                │
                       ▼                ▼
                 Is item stale?
                 - Missing .qm, .c, or .o?
                 - source > .qm or .c?
                 - Any imported interface source > .qm?
                       ┌────────────────┴────────────────┐
                      Yes                                No
                       ▼                                 ▼
             [ Compile Item ]                    [ Read Item .qm ]
             - Rebuild stale interfaces          - Enqueue unvisited
             - Enqueue unvisited modules           imported modules
             - Emit .qm, .c, .o in .build/       - Record .o for linker
             - Record .o for linker
                       │                                 │
                       └────────────────┬────────────────┘
                                        │
                                        └───────┘
```

### 7.1. Build Algorithm

1. **Initialization:**
   - Let `work_queue` be a FIFO queue of compilation items (`main.quest` or module names).
   - Let `discovered_modules` be a set of canonical module names to prevent duplicate enqueueing.
   - Let `expected_interfaces` be a map from module name to expected interface constraints `(importer, interface)`.
   - Let `linked_objects` be an ordered set of object file paths (`.o`) to pass to the linker.
   - Enqueue the Quest main routine `main.quest`.

2. **Queue Processing Loop:**
   While `work_queue` is not empty, dequeue `item`:

   - **Check for Runtime Builtin Modules:**
     If `item` is in `BUILTIN_RUNTIME_MODULES` (e.g. `"dynamic"`):
     - The module's implementation is built directly into the runtime; no `.mod.quest` or `.o` file exists.
     - Verify and regenerate its interface (`dynamic.int.quest` -> `dynamic.qi`) if needed per §5.
     - Continue to the next queue item without checking for `.mod.quest` or `.o`.

   - **Determine Paths:**
     - For main routine: source is `main.quest`; artifacts are `.build/main.main.qm`, `.build/main.main.c`,
       `.build/main.main.o` (under the main routine's directory, §3.2).
     - For module `M`: source is `M.mod.quest`; artifacts are `.build/M.qm`, `.build/M.mod.c`, `.build/M.o`.

   - **Check Staleness:**
     An item is **up to date** (precompiled / binary distribution mode) if:
     - `.qm` and `.o` (or `.c`) exist, and no source `.quest` or `.mod.quest` exists on disk.
     Otherwise, when source is present, an item is **stale** if:
     1. Any corresponding artifact (`.qm`, `.c`, or `.o`) is missing from `.build/`.
     2. `mtime(source) > mtime(.qm)` or `mtime(source) > mtime(.c)` or `mtime(.c) > mtime(.o)`.
     3. Any interface `I` in `.qm.imported_interfaces` has `mtime(I.int.quest) > mtime(.qm)` (the **Transitive Interface
        Invalidation Rule**; see §7.2).
     4. Any interface or module path the unit imports would now resolve to a different source file or canonical name
        than `.qm.imported_interfaces` / `.qm.imported_modules` record. Imports are resolved again as the unit's
        compilation resolves them (from the unit's directory, then the current search paths), so changing `-I`, or
        adding a file earlier on the search path, rebuilds the units it affects even though no file they were compiled
        against changed. Without this rule such a build would reuse the old artifacts and, because the build engine
        compiles the module sources a manifest names, link the old imported modules too.
     5. The `.qm` records a different `source` than the unit's source file: the artifacts belong to another unit with
        the same artifact paths (§3.2).

   - **Action if Stale:**
     - Compile the source file (`main.quest` or `M.mod.quest`).
     - For each imported interface: verify and regenerate `I.qi` per §5, and for a module, its interface's
       `I.int.h` per §5.3.
     - Emit `.qm` and `.c` into `.build/`.
     - Compile `.c` to `.o` via the host C compiler (`clang -c ... -o .build/...`).
     - Read the generated `.qm` manifest.
     - **Verify Interface Conformance:** Verify that `manifest.interface` satisfies all expected interfaces recorded
       in `expected_interfaces[item]` from importing units. If there is a mismatch, raise a `BuildError`.
     - For each module `Dep` in `imported_modules`:
       - Record `(item, Dep.interface)` in `expected_interfaces[Dep.name]`.
       - If `Dep` is not in `discovered_modules`, add `Dep` to `discovered_modules` and enqueue `Dep`.
     - Add `.o` to `linked_objects`.

   - **Action if Up to Date:**
     - Read the existing `.qm` file from `.build/`.
     - **Verify Interface Conformance:** Verify that `manifest.interface` satisfies all expected interfaces recorded
       in `expected_interfaces[item]` from importing units. If there is a mismatch, raise a `BuildError`.
     - For each module `Dep` in `.qm.imported_modules`:
       - Record `(item, Dep.interface)` in `expected_interfaces[Dep.name]`.
       - If `Dep` is not in `discovered_modules`, add `Dep` to `discovered_modules` and enqueue `Dep`.
     - Add `.o` to `linked_objects`.

3. **Termination:**
   When the queue is empty, all units in the transitive closure are guaranteed to have current `.qm`, `.c`, and
   `.o` files in `.build/`, and all module interface contracts have been verified.

4. **Module Implementation Import Cycle Check:**
   Separate compilation of module implementations strictly requires an acyclic dependency graph (DAG). Circular
   implementation dependencies (`module A` imports `B`, and `module B` imports `A`) make separate compilation and
   modular evaluation impossible.
   - The build engine constructs a directed graph of all modules in the transitive closure using the `imported_modules`
     recorded in their `.qm` manifests.
   - It performs a depth-first topological sort / cycle detection across this graph.
   - If any cycle is detected, the build terminates immediately with a diagnostic detailing the cyclic dependency
     chain (e.g. `Error: circular module dependency detected: A -> B -> A`).

### 7.2. The Transitive Interface Invalidation Rule
A critical flaw in naive separate compilation systems is the *Fragile Interface Problem*:
> If an interface `util/Strutil` is updated, `util/path.mod.quest` may not have been touched, meaning
> `path.mod.quest` is *older* than `path.mod.c` and `path.qm`. However, `path.mod.c` was compiled against struct offsets and
> prototypes in the *previous* `strutil.int.h`. Skipping `path` produces binary desynchronization and runtime faults.

**Resolution:** When inspecting an existing `.qm` file during staleness checking, the compiler checks the datestamps
of all interfaces recorded in `imported_interfaces`. If any interface source (`I.int.quest`) is newer than `M.qm`,
unit `M` is deemed **stale** and recompiled against the updated interface.

The interfaces recorded are not only those `M` imports but also those they import, transitively: if `M` imports
only `Helper`, and `Helper` imports `Base` and uses `Base`'s type `T` in its signatures, then `M` is compiled against
`Base` as well. Changing `T` from `Int` to `Real` changes `Helper`'s C signatures without touching `M`'s or `Helper`'s
source. If `M` were not rebuilt, its object would still call `Helper`'s functions with integer arguments and results
while the rebuilt `Helper` module uses doubles, a mismatch that links and then computes wrong values. Rebuilding the
modules that import `Base` directly does not help, since a rebuilt module does not make its importers stale; only
recording `Base` in `M.qm` does. Rule 4 of §7.1 likewise resolves these indirect imports again, from the directory
of the interface that imports them.

### 7.3. One Build Path for Full Builds and Pipeline C Phases
The driver produces native code from a main routine in two ways: the **full build** (`quest main.quest -o app`,
`BuildEngine.build_main`) and the **pipeline C phases** (`--stop-after codegen_c` / `run_c_compiled`, which the test
runner uses, and `quest compile` with `--stop-after` / `--emit-c`). Both delegate everything about dependencies to the
build engine, so there is exactly one implementation of staleness checks, artifact placement, and object collection:

```
  Full build (build_main)                          Pipeline C phases
  ───────────────────────                          ─────────────────
  main stale? ──yes──> compile_main_unit           Tokenize -> Parse -> Typecheck -> CodegenC
       │                (typecheck, emit C,                         │
       │                 write .main.{qm,c,o})         unit_module_refs(imports, analysis)
       │no                      │                                   │
  read .main.qm                 │                                   │
       │                        │                                   │
       └──────────┬─────────────┘                                   │
                  ▼                                                 ▼
     BuildEngine.build_modules(imported_modules)  <────── link_dependencies(ctx)
       (queue of §7.1: staleness, compile into build dir,     (run_c_compiled, -o)
        conformance §6.3, cycle check §8.2)
                  │
                  ▼
     objects to link ──> link_objects (full build) / compile_c_source + run (pipeline)
```

- **Typechecking never builds modules.** While a unit is typechecked for C compilation, imported modules are typed
  against their interfaces only (§6), and only interface artifacts are regenerated (§5.1). The typechecker, the module
  loader, and the C analysis do not compile modules, search for objects, or record objects to link.
- **The module queue is `BuildEngine.build_modules`.** Given the modules a unit imports (with the interfaces it
  expects of them), it runs the §7.1 queue over their transitive closure and returns the objects to link: the
  driver's extra objects first, then one object per module. `build_main` runs it after bringing the main routine
  up to date; the pipeline runs it through `link_dependencies` (in `pipeline.py`) when a phase needs to link
  (`run_c_compiled`, or `-o` without a full build).
- **Which modules a unit needs** comes from `unit_module_refs` (§6.2), shared by `compile_main_unit` and
  `CodegenCPhase`.
- **Modules record only explicit imports.** A module's `.qm` lists exactly its import clauses (§6.1), which is what
  the queue follows.

| Responsibility | Implementation |
| :--- | :--- |
| Import resolution, unit names, typed units (§2.1) | `quest.modules.graph` (`Resolver`, `UnitGraph`) |
| Interface staleness & regeneration (§5) | `interface_compiler.ensure_resolved_interface_artifacts` |
| Interface headers (§5.3) | `codegen.c.headers.ensure_interface_header` |
| Module / main staleness (§7.1) | `BuildEngine._unit_staleness` |
| Module queue, conformance, cycles (§7.1, §6.3, §8.2) | `BuildEngine.build_modules` |
| Modules a unit links against (§6.2) | `build.engine.unit_module_refs` |
| Artifact paths under the build directory (§3.2) | `graph.unit_artifact_dir`, `ModuleArtifacts`, `interface_qi_file`, `interface_header_file` |

### 7.4. Parallel Builds (`-j N`, the Self-Hosted Compiler)
The self-hosted driver's `-j N` compiles up to N modules at once (`questlang/build/engine`, `questlang/build/workers`).
`./quest` builds both its stages with as many as there are CPUs (`QUEST_JOBS`); the runner builds the self-hosting
check's stages and the questlang tests that way. The bootstrap builds serially. A parallel build writes the same
artifacts as a serial one, and the same `build.log` entries in the same order; only the times differ.

- **Modules depend on interfaces, not on each other,** so any stale modules can compile at once once the interfaces
  they import are built. The engine learns which modules to build only from the manifests their compilations write
  (§7.1), so it takes the queue a **wave** at a time. A wave pops the modules queued and not yet popped, and those they
  are predicted to queue: each popped module's top-level imports (from its source if it is stale, from its manifest
  if not), resolved as its compilation resolves them, and so on. Its manifest will list them, so the prediction is
  never wrong, only short of the imports its C adds or a nested import brings, which the next wave pops.
- **Popping is a serial build's.** A wave works out each module's artifacts and staleness as a serial build would when
  the module's turn comes, which does not depend on the modules compiled before it, and keeps the log entries that
  makes, and any error it raises.
- **The stale modules compile in child processes.** They are dealt round robin into at most N batches. Each batch is
  compiled in order by one child, the driver run in unit mode (`--unit-module`, one per module, with the engine's
  search paths and options), so that it loads the interfaces its modules share once, as a serial build does.
- **Then the queue is followed as a serial build follows it.** Each module in turn writes its log entries, raises its
  error if popping or compiling it failed, reads its manifest, verifies interfaces, and queues its imports. A child
  stops at its first failure and writes the error to its standard output; the engine raises it again in its turn, so
  the error reported is a serial build's (the first in queue order), reported as a serial build reports it.
- **Workers write interfaces' artifacts atomically.** Two children may rebuild the same stale interface at once: each
  writes a `.qi` and a header to a temporary file of its own and renames it into place (`paths.writeAtomically`), so
  neither reads half of a file the other writes. Only one process writes each module's artifacts.
- **A unit's C does not depend on what was compiled before it.** A module abstract type's descriptor is named by its
  global name (`os/process.T`) whether or not the process has elaborated its module, which a child may not have done
  (`descriptors.moduleAbstractTypeName`).

`tests/self-hosted/parallel_build.py` builds the programs under `tests/self-hosted/parallel-build` and
`tests/self-hosted/build-errors` with `-j 1` and `-j 4`, and requires the same artifacts, log, and output, or the
same error. Building the self-hosted driver with `-j 8` takes about 34 seconds, against 56 serially: the main
program's compilation (about 10 seconds) is serial, and each child loads its batch's interfaces itself.

---

## 8. Self-Guarding Idempotent Module Initialization & Linking

### 8.1. Initialization Mechanics
Initialization order does **not** depend on compilation order or queue order. Each compiled module `M` emits a
self-guarding, idempotent initialization function `qv_mod_<M>_init()`:

```c
static bool qv_mod_M_initialized = false;

void qv_mod_M_init(void) {
    if (qv_mod_M_initialized) return;
    qv_mod_M_initialized = true;

    /* Initialize direct dependencies first */
    qv_mod_dep1_init();
    qv_mod_dep2_init();

    /* Evaluate top-level module bindings and instantiate module record */
    ...
}
```

- **Dynamic Depth-First Post-Order:** Because each module's initializer recursively invokes the initializers of the
  modules it directly imports before running its own body, initialization order is dynamically resolved at runtime in
  strict dependency order (dependencies initialize before dependents).
- **Idempotency:** The `qv_mod_M_initialized` guard ensures every module record is evaluated exactly once, even in
  diamond dependency topologies (e.g. `A` imports `B` and `C`, both importing `D`).
- **Main Routine Entry:** In `main()`, the generated C code simply invokes `qv_mod_dep_init()` for the modules directly
  imported by the main routine.

### 8.2. Cycle Detection
While interfaces may cross-reference types freely (provided no value/type recursion cycle violates contractiveness),
circular module implementation dependencies are strictly invalid.
- Separate compilation requires that module implementations form a Directed Acyclic Graph (DAG) so that dependencies
  can be compiled, linked, and initialized without deadlock.
- At build time, the build engine inspects the `.qm` dependency graph via DFS to detect cycles and emit descriptive
  errors before invoking the linker.
- At runtime, a recursion guard flag (`qv_mod_M_in_progress`) can optionally trap any circular initialization attempts
  as an additional defense.

### 8.3. Native Linking
Once the queue is empty, the driver invokes the host C compiler / linker:
```sh
clang -o app .build/main.main.o .build/util/path.o .build/util/strutil.o ... runtime/quest_runtime.o -lgc
```
Passing all discovered `.o` files in `linked_objects`.

---

## 9. Build Logging and Audit Trail

To make the separate compilation process completely transparent and debuggable, the compiler records all build events
to an audit log:
- **Default Location:** `<build-dir>/build.log` (e.g. `.build/build.log`).
- **Configuration:** Controlled via `--build-log <path>` or disabled via `--no-build-log`.
- **Verbose Console Output:** The `--verbose` CLI flag echoes all build log entries directly to `stderr` in real time.

### 9.1. Log File Structure
The log records structured timestamps, queue transitions, staleness evaluations, and tool invocations:

```
[2026-10-02T16:50:01] BUILD START: target=tests/source/stdlib/path_operations.quest mode=separate build_dir=.build
[2026-10-02T16:50:01] QUEUE INIT: enqueued main routine 'path_operations'
[2026-10-02T16:50:01] POP QUEUE: 'path_operations'
[2026-10-02T16:50:01] EVAL STALENESS: 'path_operations' -> STALE (.build/path_operations.qm missing)
[2026-10-02T16:50:01] COMPILE MAIN: 'path_operations'
[2026-10-02T16:50:01] RESOLVE INTERFACE: 'util/Path' -> 'lib/util/path.int.quest'
[2026-10-02T16:50:01] EVAL STALENESS: 'util/Path' (.build/util/path.qi) -> UP TO DATE
[2026-10-02T16:50:01] WRITE QM: .build/path_operations.qm
[2026-10-02T16:50:01] EMIT C: .build/path_operations.c
[2026-10-02T16:50:01] HOST COMPILE: clang -c .build/path_operations.c -o .build/path_operations.o
[2026-10-02T16:50:01] ENQUEUE MODULE: 'util/path' (from main import)
[2026-10-02T16:50:01] POP QUEUE: 'util/path'
[2026-10-02T16:50:01] EVAL STALENESS: 'util/path' -> STALE (strutil.int.quest > path.qm)
[2026-10-02T16:50:01] COMPILE MODULE: 'util/path'
[2026-10-02T16:50:01] ENQUEUE MODULE: 'util/strutil' (from util/path import)
[2026-10-02T16:50:01] ENQUEUE MODULE: 'util/stringbuilder' (from util/path import)
[2026-10-02T16:50:01] WRITE QM: .build/util/path.qm
[2026-10-02T16:50:01] EMIT C: .build/util/path.mod.c
[2026-10-02T16:50:01] HOST COMPILE: clang -c .build/util/path.mod.c -o .build/util/path.o
[2026-10-02T16:50:02] POP QUEUE: 'util/strutil'
[2026-10-02T16:50:02] EVAL STALENESS: 'util/strutil' -> UP TO DATE
[2026-10-02T16:50:02] READ QM: .build/util/strutil.qm (no new unvisited modules)
...
[2026-10-02T16:50:03] QUEUE EMPTY: transitive closure verified (4 modules)
[2026-10-02T16:50:03] HOST LINK: clang -o app .build/path_operations.o .build/util/path.o ... -lquest_runtime
[2026-10-02T16:50:03] BUILD COMPLETE: exit_code=0
```

---

## 10. SHA-256 Digests of Files

Staleness (§5) compares file times, never contents: no source or artifact is hashed to decide whether a unit is
stale. The build hashes the contents of files in these places, each with SHA-256:

1. **The runtime's objects** (both compilers, on every link: `runtime_objects` in
   `bootstrap/python/quest/codegen/c/compiler_runner.py`, `runtimeObjects` in
   `questlang/codegen/c/compilerrunner`). The key of the cache directory the objects are kept in
   (`.build/runtime/KEY/`, or `$QUEST_RUNTIME_CACHE/KEY/`) is the first 24 hex digits of a digest of the C compiler's
   name, its `--version` output, the compile flags, and the name and contents of every `.c` and `.h` file in
   `runtime/` ([codegen-c.md](codegen-c.md) §11.3). Changing any of them compiles the runtime again.
2. **The release's compiler** ([release-compiler.md](release-compiler.md)):
   - `./quest` hashes the current release's `quest` (with `shasum -a 256`) each time it runs with the release as
     its seed, and refuses a binary whose digest is not the one `release.json` records. The release's commit and the
     digest are the seed's identity, recorded in `.build/quest-stages/seed`: when either changes, the stages are built
     again from nothing.
   - `run_tests.py --seed release` (`current_release` in `bootstrap/python/quest/testing/runner.py`) makes the same
     check before building from the release.
   - `tools/release` records the digest of the new `quest` in `release.json` when it cuts a release, and checks it
     again in `--verify` and before installing a new release.

The tests hash a file too, though no build does: the ABI corpus records a digest of `runtime/quest_runtime.h`
(§5.2.3).

The C backend's other digests are of text it makes, not of files: the names of generated C types (a type's printed
form, in `layout.type_digest` and `layout.text_digest`, `questlang/codegen/layout` in the self-hosted compiler), and
the tags of long shapes. The self-hosted compiler computes these with SHA-256 written in Quest
(`questlang/codegen/sha256`), which is a measurable part of its time ([tasklist.md](tasklist.md)).

---

## 11. Summary of Architectural Guarantees

1. **Deterministic Staleness:** Interface and module updates propagate reliably through the transitive closure via the
   `.qm` invalidation rules, eliminating runtime struct offset mismatches and stale object crashes.
2. **Clean Source Tree:** In full application builds, all generated files (`.qi`, `*.int.h`, `.qm`, `.c`, `.mod.c`, `.o`) live
   strictly under `.build/`.
3. **Decoupled Compilation Units:** Compiling a module never triggers compilation of other modules—it only records
   module names and validates against interface `.qi` files.
4. **Order-Independent Initialization:** Dynamic, self-guarding module initializers guarantee correct initialization
   order at runtime regardless of queue discovery order.
5. **Uniform Main Routines:** Main routines emit `.qm` files, allowing incremental builds to read imports without
   re-parsing source code.
6. **Full Auditability:** Every scheduling and staleness decision is captured in `build.log` and optionally displayed
   with `--verbose`.
7. **Implementation DAG Invariant:** Module implementation imports must form a directed acyclic graph (DAG), which is
   explicitly validated before linking to prevent circular implementation deadlocks.
8. **Explicit Module Isolation vs. Main Routine Ergonomics:** Modules and interfaces strictly adhere to Cardelli's
   *Typeful Programming* explicit import declarations, while main routines discover implicit standard library helper
   modules automatically post-analysis.
9. **One Build Path:** Full builds and the pipeline's C phases share one implementation of staleness checks,
   artifact placement, and object collection (§7.3), so a C-phase run from an empty build directory builds
   everything it links, rather than depending on objects an earlier build left behind.
10. **Test Harness Timeout Enforcement:** The end-to-end test runner (`run_tests.py`) enforces a configurable per-test
   execution timeout (defaulting to 30.0 seconds via `--timeout`). Any individual test process that hangs or exceeds
   this deadline is terminated immediately with a failure, preventing runaway builds or deadlocks.
