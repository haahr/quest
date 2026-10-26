# Quest Module System and File Imports

This document describes the Quest module system based on Luca Cardelli's *Typeful Programming* (§7.1), including
interfaces, module implementations, information hiding, file-based loading conventions, search path resolution, and
evaluation semantics.

---

## 1. Overview and Theoretical Foundations

Quest implements a first-order module system as described by Luca Cardelli in *Typeful Programming* (1991, §7.1):

- **Interfaces (`interface ... export ... end`):** Specifications describing types, kinds, and value signatures. They
  define the public contract that implementation modules must satisfy.
- **Modules (`module m: I ... export ... end`):** Implementations that provide concrete definitions matching an
  interface. Modules can have private local state and bindings hidden behind the interface.
- **Information Hiding & Abstract Types:**
  - An abstract type declared in an interface (`T::TYPE`) is opaque to consumers of any module implementing that
    interface.
  - In the module's export scope, `T` becomes an opaque type variable unique to that module instance (`m.T`),
    preventing clients from depending on its internal representation.
  - A manifest type declared in an interface (`Def T = Int` or `Let T = Int`) is transparent, and its definition is
    known to all clients.
- **Singleton Module Semantics:** Modules are instantiated at most once at link time. When multiple modules or phrases
  import the same module (e.g. in diamond dependencies), all importers share the identical runtime record and mutable
  state cells.

---

## 2. File Conventions & Search Rules

When the Quest compiler or interpreter encounters an import for an interface or module that is not already
registered in the lexical environment, it automatically loads it from disk via the unified module loader.

### 2.1. File Extensions, Case Normalization, and Hierarchical Directories
- **Interfaces:** Saved with the extension `.int.quest`.
- **Modules:** Saved with the extension `.mod.quest`.
- **Hierarchical Paths:** Unquoted forward slashes (`/`) represent directory nesting. For example, `util/random`
  maps to the path `util/random.mod.quest` (or `util/random.int.quest`).
- **Case Normalization:** When searching for a file, the compiler normalizes the filename components to lowercase:
  - An interface `util/Counter` or `util/counter` maps to `util/counter.int.quest`.
  - A module `util/Stack` or `util/stack` maps to `util/stack.mod.quest`.
  This ensures deterministic, portable behavior across case-sensitive (Linux) and case-insensitive (macOS, Windows)
  filesystems.

### 2.2. Search Order Precedence & Sibling Relative Resolution
The file loader searches directories in the following strict order:
1. **Implicit Active Directory (Sibling Relative):** The directory containing the active `.quest` file or currently
   compiling module is searched first. For instance, if `util/calc.mod.quest` imports `math`, the loader searches for
   `util/math.mod.quest` before searching root include directories.
2. **Explicit Include Paths (`-I`):** Any directories specified on the command line via `-I` / `--include` (or
   configured in `CompilerOptions.include_paths`), searched in command-line order.

A file in the active directory shadows any file with the same name in the include paths.

### 2.3. Canonical Names
Every interface and module file has one **canonical name**, which identifies it everywhere after it is found: in the
importer's typed AST and C code, in the unit's own module header (`module m: I`), in `.qm` manifests (including the
build directory path of its artifacts), and in mangled C symbols ([name-mangling.md §4](name-mangling.md)). It is the
file's path, without its suffix, relative to a **root**:
1. The deepest of the include roots that contains the file: `QUEST_LIB`, the include paths (`-I`), `lib/`, and the
   project directory (the root of this repository).
2. Otherwise, the directory of the program being compiled (the main routine's directory, or the current directory for
   inline code).
3. Otherwise (a standalone `quest -c` of a file under no include root), the file's own directory: its name is its base
   name.

Every directory and file name in a canonical name may contain only ASCII letters and digits; any other character (such
as `_`, `-`, or `.`) is an error when the file is loaded. Import paths cannot name such files anyway, but directories
between a root and the file are part of the name too: a program in `tests/source/my_tests/` cannot import the module
beside it, whose name would be `tests/source/my_tests/counter`. The restriction keeps mangled C names valid and
unambiguous ([name-mangling.md §4.1](name-mangling.md)).

The canonical name depends only on the file and these roots, not on how an import found the file. So a module found
by sibling search has the same name for every importer, and the name its interface gets in the module header is the one
its importers expect. Interface names keep the declared base name (`util/Counter` for `util/counter.int.quest`).
For example:
- `/home/me/app/main.quest` importing `util/arith`, with no `-I`: `util/arith`; its sibling import `helper` is
  `util/helper`.
- `tests/source/modules/counter.mod.quest` beside a program in this repository: `tests/source/modules/counter`, or
  `modules/counter` with `-I tests/source`.

The program's directory is a root of last resort, not an include path: it is searched only by sibling search from
the main routine. Units under different roots may share a canonical name (a program's `util/path` and `lib/util/path`);
importers record the source file they found in their `.qm` ([build-process.md §4.3](build-process.md)), so the build
engine compiles the right one, but two such units cannot be linked into one program.

Loaded interfaces and modules are shared by canonical name: every importer of a file, in any phase, gets the same
interface scope, module export scope (with the same abstract types), and module value. The names an import binds
(`counter`, `Counter`, or an alias) are local to the importing unit: a module loaded from a file sees only the builtins
and its own imports, so `counter` beside a program and `util/counter` imported as `counter` by a module in `util/` are
different modules, even in one program. Builtin interfaces with sources in `lib/` (such as `Writer`) are those files'
interfaces, so importing them by name or by file gives the same scope.

---

## 3. Single Definition Rule and Strict Validation

To keep compilation units clean, modular, and predictable, interface and module files must adhere to strict
structural constraints:

1. **Single Top-Level Phrase:**
   A `.int.quest` file must contain **strictly one** top-level phrase: an `interface` declaration.
   A `.mod.quest` file must contain **strictly one** top-level phrase: a `module` definition.
   Top-level expressions, `let` bindings, or standalone `import` statements outside the construct are prohibited.
2. **Name Matching:**
   The identifier declared in the file header must match the filename basename (case-insensitively). For example,
   `util/counter.int.quest` must declare `interface Counter` (or `counter`), not `interface Bag`.
3. **Interface Conformance:**
   In a module file `m.mod.quest`, the interface specified in the module header (`module m: I` or `module m: Path/I`)
   must match the expected interface requested by the importer or define a canonical relative interface path.
4. **Cycle Detection:**
   The loader tracks the active import chain. Circular imports among interfaces (e.g., `A` imports `B`
   which imports `A`) or modules are detected and reported as compile-time errors displaying the cycle path.

---

## 4. Syntax and Usage

### 4.1. Interface Declarations (`.int.quest`)
An interface declaration exports abstract types, manifest types, kinds, and value signatures:

```quest
(* util/counter.int.quest *)
interface Counter
export
    T::TYPE
    new(init: Int): T
    inc(c: T): T
    get(c: T): Int
end
```

Interfaces can also import other interfaces using a leading `import` clause with hierarchical paths:
```quest
interface ExtendedCounter
import :util/Counter
export
    reset(c: Counter.T): Counter.T
end
```

### 4.2. Module Definitions (`.mod.quest`)
A module provides concrete implementations for the members specified in its interface:

```quest
(* util/counter.mod.quest *)
module counter : Counter
export
    Let T = Int
    let new(init: Int): T = init
    let inc(c: T): T = c + 1
    let get(c: T): Int = c
end
```

Modules can declare internal imports before their export block:
```quest
(* app.mod.quest *)
module app : App
import util/counter: util/Counter
export
    let run(): Int = counter.get(counter.inc(counter.new(10)))
end
```

### 4.3. Top-Level Imports & Hierarchical Aliasing (`main.quest`)
Client programs import interfaces and modules using the two-tier `import` syntax:

- **Flat Imports (Backward-Compatible):**
  ```quest
  import counter: Counter
  import :Counter
  ```

- **Hierarchical Path Imports:**
  ```quest
  import util/counter: util/Counter
  import :util/Counter
  ```
  When imported without aliases, the bound local names default to the final component (e.g. `counter` and `Counter`).

- **Local Signature Aliasing:**
  To prevent local identifier collisions or assign concise local names, this implementation of Quest supports
  signature-based aliasing for both modules and interfaces:
  - **Both Module and Interface Aliased:**
    ```quest
    import cnt : Cnt = util/counter : util/Counter
    ```
    Binds module value `cnt` and interface types/kinds `Cnt` (e.g. `Cnt_T`).
  - **Module Aliased Only:**
    ```quest
    import cnt = util/counter : util/Counter
    ```
    Binds module value `cnt` and interface types `Counter` (e.g. `Counter_T`).
  - **Interface Aliased with Module:**
    ```quest
    import :Cnt = util/counter : util/Counter
    ```
    Binds default module value `counter` and aliased interface types `Cnt` (e.g. `Cnt_T`).
  - **Standalone Interface Aliased:**
    ```quest
    import :Cnt = :util/Counter
    ```
    Binds aliased interface types `Cnt` into scope without instantiating any module.
  - **Multiple Modules for One Interface:**
    ```quest
    import c1 = util/counter1, c2 = util/counter2 : util/Counter
    ```

In all contexts, `/` in expressions (e.g. `10 / 2`) remains the standard division operator without syntactic ambiguity.

---

## 5. Singleton Evaluation & Diamond Dependencies

Cardelli's module system defines modules as link-time singletons. At runtime:
- Each module is evaluated at most once when first imported.
- Subsequent imports of the same module retrieve the cached module record (`QRecord`).
- Mutable state (`let var`) encapsulated within a module is preserved across all importing sites.

### Example: Shared Mutable State Across Diamond Imports
```
        +---------------+
        |  store.mod    |  (let var count = 0)
        +---------------+
          /           \
         /             \
+---------------+   +---------------+
| clienta.mod   |   | clientb.mod   |  (both import store: Store)
+---------------+   +---------------+
         \             /
          \           /
        +---------------+
        |   main.quest  |  (imports clienta and clientb)
        +---------------+
```

When `clienta` invokes `store.inc()`, the mutation is immediately visible when `clientb` calls `store.get()`. Both
clients interact with the exact same runtime instance.

---

## 6. Compiler CLI Integration

The Quest driver (`quest`) and compiler pipeline support include paths using the standard `-I` flag:

```bash
# Search current directory first, then ./lib and ./interfaces:
quest -I ./lib -I ./interfaces main.quest

# In interactive REPL mode:
quest -i -I ./lib

# Native C compilation mode:
quest compile -I ./lib main.quest -o main_app
```

---

## 7. Compilation Architecture

Quest compiles modules through its intermediate representation ([ir.md](ir.md)), supporting both **separate
compilation** (the default for all file-backed modules) and **whole-program compilation** (`--whole-program` or inline
`module` declarations in a single source file). Both modes share the same core semantic and representation invariants:

1. **Acyclic Dependency Enforcement (Cardelli §7.1):**
   - As Cardelli explicitly specifies (*Typeful Programming* §7.1, p. 55): *"The import dependencies of both
     modules and interfaces must form a directed acyclic graph; that is, mutually recursive imports are not
     allowed to guarantee that the linking process is deterministic."*
   - Neither interfaces nor modules may form cycles. Topological sort order is guaranteed to be unambiguous
     and deterministic.
2. **Module Export Representation (First-Class `QRecordVal` Fat Pointers):**
   - Each module `m : I` with mangled canonical name `<clean>` compiles to a top-level C record variable
     `QRecordVal qm_<clean>;` (`static` in whole-program mode, `extern` in separate compilation). Module records use
     their own `qm_` prefix so that they cannot collide with a user identifier of the same name (`qv_m`).
   - The interface `I` specifies the record struct layout containing closures and values for all exported value fields.
   - `qm_<clean>` stores `.val` pointing to the allocated payload struct and `.dict` pointing to the static identity
     evidence dictionary for the interface record type.
3. **Abstract Type Erasure to `QVal`:**
   - Across compilation boundaries, abstract types (`T::TYPE`) cannot have known concrete scalar representations.
     Interface signatures and record fields represent abstract types uniformly as 64-bit words (`QVal` / `void *`).
   - Inside a module `m : I`, bindings are elaborated and lowered using their concrete implementation types. At the
     module export boundary, the representation pass (`ir/represent.py`, [ir.md §3](ir.md)) converts each exported value
     and function closure from the module's concrete representation to the interface's erased representation (boxing or
     adapting arguments and results as needed) before populating `qm_<clean>`.
4. **Manifest Type Erasure:**
   - Interface records only store value components (`FieldSig`); manifest types (`Def T = ...`) and type constructors
     are erased at runtime and do not generate struct fields.
5. **Topological Module Initialization (`qv_mod_<clean>_init`):**
   - Each module emits an initialization function `void qv_mod_<clean>_init(void)` (`static` in whole-program mode,
     external in separate compilation) protected by an idempotent boolean flag
     `static bool qv_mod_<clean>_initialized;`.
   - The initializer registers record offset dictionaries and abstract type descriptors, recursively calls the
     initializers of all imported modules, executes the module's internal declarations and statements, allocates the
     module record payload, and writes the exported values into `qm_<clean>`.
   - `main()` invokes the initializers of all top-level imported and inline modules before executing the main program
     phrases, guaranteeing singleton semantics across diamond dependency graphs.

---

## 8. Unified Native & Hybrid Quest/C Modules

Rather than treating standard library modules as compiler-internal special cases, Quest unifies pure Quest modules,
standard library modules, and hybrid Quest/C modules through a single pipeline:

### 8.1. Declarative Module Architecture
- Standard library modules reside on disk in `lib/` as regular Quest units (`.int.quest` and `.mod.quest`), compiled to
  pre-built `.qi`, `.int.h`, `.mod.c`, `.o`, and `.qm` artifacts on demand.
- The tree-walking and IR interpreters bridge external C symbols to Python (`quest/interpreter/builtins.py`): external
  C symbol names map to Python functions (`EXTERNAL_FUNCTIONS`) and to constants and exceptions (`EXTERNAL_VALUES`).
  Only `dynamic` (`Dynamic`) remains a purely runtime-synthesized module without a `.mod.quest` implementation file.
- Within a `.mod.quest` file, declarations can be pure Quest bindings or `external "..."` bindings (`TypedExternal` /
  `ir.External`) that bind directly to C runtime types, functions, or global values.

### 8.2. Direct Calls vs. First-Class Module Records
The IR and C backend optimize module member calls while preserving Cardelli's first-class module semantics:
1. **Direct Call Lowering:**
   - Within the same compilation unit (or when calling an `external` C function binding), known function calls bypass
     closure allocation and call the underlying static IR function (`qf_<name>`) or C runtime symbol directly.
   - Across separately compiled modules, calling an exported function or polymorphic value on an imported module
     (`m.f(...)`) emits a direct call to the module's exported C wrapper function `qv_<clean>_<member>(...)`
     (`ir.ImportCall`).
2. **First-Class Concrete Value Records:**
   - When a module is used as a first-class value (e.g. `let r = m` or passed to a function expecting the interface
     record type) or when accessing a non-function value field (`m.x`), code accesses `qm_<clean>`.
   - During `qv_mod_<clean>_init()`, every exported function (including functions bound via `external`) is wrapped in a
     `QClosure` at the interface's representation and stored alongside exported non-function values in `qm_<clean>`.

### 8.3. Hybrid Quest/C Modules
Modules can freely mix Quest definitions and `external` C bindings:
```quest
(* fileio.int.quest *)
interface FileIO
export
    Handle::TYPE
    stdout: Handle
    writeHello(h: Handle): Ok
end

(* fileio.mod.quest *)
module fileio : FileIO
import writer: Writer
export
    Let Handle = external "QWriter *"
    let stdout: Handle = external "quest_writer_output"
    let writeHello(h: Handle): Ok =
        writer.putString(h "Hello Native!\n")
end
```
Inside `fileio`, `writeHello` is a pure Quest function that calls into `writer`, while `Handle` and `stdout` bind
directly to C runtime types and symbols.

---

## 9. Separate Compilation Architecture

Separate compilation is the default compilation model for all file-backed interfaces and modules (both flat modules in
`lib/` and hierarchical modules in subdirectories). See [build-process.md](build-process.md) for the build engine and
staleness rules.

### 9.1. Interface Compilation (`.int.quest` -> `.int.h` + `.qi`)
Compiling an interface (`quest -c counter.int.quest`) generates two artifacts:
1. **C Header (`x.int.h`, generated by `codegen/c/headers.py`):**
   - Named `x.int.h` rather than `x.h` so that an interface named like a C library header (`math`, `string`,
     `time`, ...) cannot shadow it: generated-code directories are on the C compiler's include path, and the
     runtime includes `<math.h>` and others ([build-process.md §3.2](build-process.md)).
   - Preprocessor guards (`#ifndef QUEST_INTF_X_H ... #endif`), named from the interface's canonical include-relative
     path with `/` mapped to `__` (`util/Math` guards with `QUEST_INTF_UTIL__MATH_H`), so same-named interfaces in
     different directories can be included together. The typedef names below use the same path, case preserved
     (`quest_sig_util__Math_<member>`).
   - `#include "quest_runtime.h"`.
   - Recursive `#include "<dep>.int.h"` for any imported interfaces (`import : Dep`).
   - Abstract types (`T::TYPE`) erase to uniform 64-bit words (`typedef QVal quest_type_X_T;`).
   - Manifest types (`Def T = ...`) emit concrete C typedefs or struct definitions.
   - Function pointer typedefs (`typedef <Ret> (*quest_sig_X_<member>)(<Params>);`).
2. **Type Metadata (`x.qi`):**
   - A serialized dynamic value ([dynamic.md §2](dynamic.md)) of Quest's interface descriptor record types:
     ```quest
     Let InterfaceDep = Record
         dir: String
         path: String
         source: String
     end

     Let InterfaceTypeDecl = Record
         group: Int
         isManifest: Bool
         kind: String
         manifestType: String
         name: String
     end

     Let InterfaceValueDecl = Record
         isPoly: Bool
         name: String
         typeSig: String
     end

     Let InterfaceDesc = Record
         abi: Int
         deps: Array(InterfaceDep)
         imports: Array(String)
         name: String
         producer: String
         source: String
         types: Array(InterfaceTypeDecl)
         values: Array(InterfaceValueDecl)
     end
     ```
   - A manifest type's `manifestType` is its definition in Quest type syntax. The members of a mutually recursive
     group (`Def Rec A = ... and B = ...`) are consecutive declarations sharing a nonzero `group` number (0 for any
     other type), and each records only its body, naming the other members; the loader elaborates the bodies of a
     group together and rebuilds the group from them. A member of a group of recursive type operators (`Def Rec
     Tree(A::TYPE) = ... and Forest(A::TYPE) = ...`) records `Fun(A::TYPE) Body`, with the other members applied to
     the parameters (`Forest(A)`), and the loader elaborates the group as it would its declaration.
   - Serialized via `dynamic.extern` / `jsog_encode` and deserialized via `dynamic.intern` / `jsog_decode`.
   - Allows the compiler to typecheck client code or implementing modules without the original `.int.quest` source.

### 9.2. Module Compilation (`.mod.quest` -> `.mod.c` + `.o` + `.qm`)
Compiling a module implementation (`quest -c counter.mod.quest`) produces three artifacts:
1. **C Source File (`<name>.mod.c`):**
   - Includes `#include "quest_runtime.h"` and `#include "<interface>.int.h"`.
   - Emits all internal module functions as `static` C functions (`qf_<name>`) and internal module state as `static`
     globals.
   - **Exported C Symbols (determined solely by the module's canonical name `<clean>` and its interface):**
     - **Module record (`QRecordVal qm_<clean>;`):** Global singleton holding the module's exported record value, with
       all fields converted to the interface's representation by `ir/represent.py`.
     - **Idempotent initializer (`void qv_mod_<clean>_init(void)`):** Guarded by `static bool
       qv_mod_<clean>_initialized`. Registers offset dictionaries and abstract type descriptors, calls
       `qv_mod_<dep>_init()` for each imported module, runs the module body, and populates `qm_<clean>`.
     - **Exported function wrappers (`<Ret> qv_<clean>_<member>(<Params>)`):** One external C function for each
       function or polymorphic value in the interface (`CPrinter.exported_functions` in `codegen/c/printer.py`), using
       the signature computed by `module_function_signature` (`codegen/c/declarations.py`) from the interface's types.
       Each wrapper invokes the corresponding exported closure stored by the module.
2. **Relocatable Object File (`<name>.o`):**
   - Produced by invoking the host C compiler (`clang -c <name>.mod.c -o <name>.o -I runtime -I <include_paths>`).
3. **Module Build Manifest (`<name>.qm`):**
   - Records the module's canonical name, implemented interface, source/object paths, and direct module/interface
     dependencies for incremental build checking and transitive linking ([build-process.md §4](build-process.md)).

### 9.3. Client Compilation, Self-Contained `extern` Declarations, and Why There Are No `.mod.h` Files
When a client compilation unit (another `.mod.quest` or a main `.quest` program) imports a module via `import m : I`:
1. **Interface-Only Compile-Time Dependency:**
   - Typechecking and C code generation for the importing unit depend **only** on the interface `I` (`.qi` /
     `.int.quest`) and never on `m.mod.quest` having been compiled—or even existing yet.
   - Generating a `<mod>.mod.h` header when compiling `<mod>.mod.quest` and `#include`-ing it in client `.c` files would
     violate separate compilation: it would force every importer of `m` to wait until `m.mod.quest` is compiled before
     the importer's C code could be compiled, and any rebuild of `m.mod.quest` could trigger unnecessary C
     recompilations of its importers.
   - Conversely, the interface header `<iface>.int.h` cannot hardcode `extern` declarations for a specific module
     because an interface does not know which modules implement it (and a program may import multiple modules
     implementing the same interface, e.g. `import m1, m2 : I`).
2. **Self-Contained `extern` Declarations Derived from `(module_name, interface)`:**
   - Because a module's exported C ABI is completely determined by its mangled canonical name `<clean>` and the
     imported interface `I`'s `Scope`, the client `.c` file (`CPrinter.import_declarations` in `codegen/c/printer.py`)
     synthesizes exact `extern` declarations directly from `(clean, I)`:
     - `extern QRecordVal qm_<clean>;`
     - `extern void qv_mod_<clean>_init(void);`
     - `extern <Ret> qv_<clean>_<member>(<Params>);` for every function and polymorphic value in `I`, using the exact
       same `module_function_signature(clean, member, type, c_type)` helper used when compiling `<mod>.mod.c`.
   - Direct calls `m.f(x)` lower to `ir.ImportCall` and emit `qv_<clean>_f(...)`.
   - Non-function value fields `m.v` (and first-class uses of `m` itself) read from `qm_<clean>`; they are not exported
     as separate C global variables.
3. **Linking:**
   - Only at the final link step (when producing an executable binary) does the build engine ensure that all
     transitively imported modules are compiled to `.o` files and passed to `clang` alongside the runtime objects
     ([build-process.md §7](build-process.md)).
   - The `--whole-program` compiler flag overrides separate compilation, loading all imported modules from `.mod.quest`
     source and emitting their definitions directly into a single C translation unit.

### 9.4. Hierarchical Modules and C Symbol Mangling
When compiling hierarchical interfaces and modules:
1. **Directory Tree Preservation:**
   When an interface or module in a subdirectory is compiled (e.g. `quest -c util/calc.mod.quest`), the compiler
   creates matching output subdirectories in the target destination (such as `.build/util/`), writing
   `util/calc.mod.c`, `util/calc.o`, and `util/calc.qm`.
2. **C Symbol Mangling:**
   Because C identifiers cannot contain forward slashes, directory delimiters in canonical module names are mangled
   to `__` (double underscore) via `mangle_module_name` ([name-mangling.md §2.5](name-mangling.md)):
   - Module record: `qm_util__calc`
   - Initializer: `qv_mod_util__calc_init`
   - Initialized flag: `qv_mod_util__calc_initialized`
   - Exported functions: `qv_util__calc_multiply`
   Single underscores (`_`) separate the mangled module name from the exported member name.
3. **Canonical Module Identity:**
   Both whole-program C code generation and separate compilation identify modules by their canonical names (§2.3,
   e.g. `util/calc`), not by the local alias or relative path used in an `import` clause. When imported using a local
   alias (such as `import c = util/calc : util/Calc`), client C code emits external declarations for `qm_util__calc`,
   `qv_mod_util__calc_init`, and `qv_util__calc_multiply`. Likewise, a sibling import `import helper : Helper` inside
   `util/calc.mod.quest` resolves to canonical name `util/helper` and refers to `qm_util__helper`.

---

## 10. Module Dependency Tracking (`.qm` Manifests)

Module and interface dependencies are tracked through `.qm` module manifests (see
[build-process.md §4](build-process.md)):

1. **Manifest Contents (`.qm`):**
   Each compiled module `<name>.qm` (a JSOG-encoded dynamic value of type `ModuleManifest`) records:
   - `name`: the module's canonical name (e.g. `"util/strutil"`).
   - `interface`: the canonical name of the interface it implements.
   - `source` and `object`: resolved paths to `<name>.mod.quest` and `<name>.o`.
   - `imported_modules`: the canonical names, interfaces, and source paths of all directly imported modules.
   - `imported_interfaces`: the canonical names, source paths, modification timestamps (`mtime`), and resolution
     paths/directories of the module's own interface and all directly or transitively imported interfaces.
2. **Incremental Rebuild & Transitive Linker Resolution:**
   When building or linking a program, the build engine (`quest/build/engine.py`) walks the `imported_modules` graph
   starting from the root compilation unit's direct imports, checks whether any module's `.o` or `.qm` is missing or
   stale relative to its `.mod.quest` source or the interfaces recorded in `imported_interfaces`, rebuilds stale units
   in topological order, and passes the transitive closure of `.o` files to the host C linker
   ([build-process.md §7](build-process.md)).

---

## See Also
- [build-process.md](build-process.md): Incremental build engine, `.qi`/`.qm` manifests, and staleness rules.
- [name-mangling.md](name-mangling.md): C identifier mangling and `qm_`/`qv_`/`qf_` namespace prefixes.
- [ir.md](ir.md): Intermediate representation and interface boundary representation conversions (`ir/represent.py`).
- [pipeline.md](pipeline.md): Compiler pipeline framework and CLI driver options.
- [c-representation.md](c-representation.md): C runtime ABI, record representation, and function calling conventions.
- [type-system.md](type-system.md): Type system, subtyping, and signature elaboration.
- [interpreter.md](interpreter.md): Tree-walking interpreter and runtime environment.
- [syntax.md](syntax.md): Concrete syntax and grammar rules.


