# Quest Project Implementation Roadmap

The eight steps of the Quest implementation, following a staged compiler methodology (inspired by Jeremy Siek's
*Essentials of Compilation*): a bootstrap in Python (steps 1 to 4), and a **self-hosted implementation written in
Quest** (steps 5 to 8) that compiles to native **AArch64 (ARM64)** machine code, runs interactive code on a **JIT
compiler**, and compiles to **WebAssembly**, on which it runs as the REPL in a browser. Every step is complete; open
work is in [tasklist.md](tasklist.md) and the reference documents' open-work sections.

---

## Roadmap Architecture Diagram

```
+-----------------------------------------------------------------------------------+
| BOOTSTRAP IN PYTHON (Located in bootstrap/python/quest/)                          |
|                                                                                   |
|  [Step 1] Lexer, Parser, AST (Immutable frozen dataclasses) [COMPLETE]            |
|       │                                                                           |
|       ▼                                                                           |
|  [Step 2] Bidirectional Typechecker & Type Evaluator (Kernel F<: subtyping)       |
|       │   [COMPLETE]                                                              |
|       ▼                                                                           |
|  [Step 3] Tree-Walking Interpreter & Interactive REPL [COMPLETE]                  |
|       │                                                                           |
|       ▼                                                                           |
|  [Step 4] Bootstrap C Compiler (Typed AST -> IR -> C99 + collector) [COMPLETE]    |
+-----------------------------------------------------------------------------------+
        │
        ▼
+-----------------------------------------------------------------------------------+
| SELF-HOSTING & NATIVE TARGETING IN QUEST (Located in questlang/)                  |
|                                                                                   |
|  [Step 5] Self-Hosted Front-End, Typechecker, & C Compiler [COMPLETE]             |
|       │   • Built first by the Python bootstrap, then by a release of itself      |
|       │   • Self-compilation fixed point: Quest compiles Quest                    |
|       ▼                                                                           |
|  [Step 6] Self-Hosted Native AArch64 Compiler (Nanopass Pipeline) [COMPLETE]      |
|       │   • Direct code generation; the default backend                           |
|       ▼                                                                           |
|  [Step 7] Native AArch64 JIT & Interactive Incremental Runtime [COMPLETE]         |
|       │   • In-process code emission and execution for the REPL, -e, and files    |
|       ▼                                                                           |
|  [Step 8] WebAssembly (WasmGC) Backend & the REPL in a Browser [COMPLETE]         |
|           • The compiler compiled to WebAssembly, a module for each input         |
+-----------------------------------------------------------------------------------+
```

---

## Detailed Stage Breakdown

### Step 1: Bootstrap Front-End (Python) — *Complete*
- **Tokenizer (Lexer):** Handles alphanumeric and symbolic identifiers, nested comments `(* ... *)`, string/char
  escape sequences, listfix constructs (`of ... end`, `of(...)`), and keyword rules. Each token tracks its starting
  character offset from the input start.
- **Parser:** PEG / recursive descent parser handling Quest grammar (uniform right-associative infix operators,
  initial/final keyword blocks, whitespace separation).
- **Abstract Syntax Tree (AST) & Desugaring (`quest/syntax/`):** Immutable functional AST definitions using
  `@dataclass(frozen=True)` and a syntactic desugaring pass (`desugar.py`) that rewrites derived forms (`andif`/`orif`,
  `elsif` chains, user infix operators, `a[i] := v`, and non-recursive `let f(S): T = e`) into core AST nodes before
  typechecking.

### Step 2: Bootstrap Typechecker & Evaluator (Python) — *Complete*
- **Three-Level Environment:** Kinds (Level 2), Types/Operators (Level 1), and Values (Level 0), with a unified
  `UnitGraph` (`quest/modules/graph.py`) tracking resolved imports and loaded interfaces/modules across all phases.
- **Bidirectional Typechecker (`quest/typechecker/`):** Term-level checking ($\Gamma \vdash e \Leftarrow T$) and
  synthesis ($\Gamma \vdash e \Rightarrow T$) following Dunfield & Krishnaswami, propagating contextual type
  information without global constraint solving.
- **Type Evaluator:** Normal-order typed $\lambda$-calculus evaluator for compile-time type operators (`Fun(S)A`).
- **Subtyping Engine (Kernel $F_{<:}^\omega$):**
  - Quantifier subtyping with contravariant bounds (`All(A <: S1) B1 <: All(A <: S2) B2` when `S2 <: S1`).
  - Structural subtyping for tuples (width/depth), records (evidence dictionary), variants, options, and contravariant/
    covariant functions.
  - Subtyping and implicit dereferencing of `Var` (read-write conjunction / coercion to value type), `Out`
    (contravariant), `Array`, and `Still`.
  - Recursive subtyping with cycle detection (Amadio-Cardelli coinductive algorithm $\Sigma$).
  - Recursive contractiveness validation ($C \succ X$, Cardelli & Longo Section 2.4/2.9, rule `[T µ]`).
  - Bounded quantification (`A<:B` $\equiv$ `A::POWER(B)`).
- **Local Type Inference & Signatures:** Signature matching, manifest type/kind expansion (`Def`, `DEF`, `_`), and
  argument/parameter reconciliation.

### Step 3: Bootstrap Tree-Walking Interpreter & REPL (Python) — *Complete*
- **Runtime Values & Memory (`quest/values/model.py`):** `QValue` hierarchy, primitives, aggregates (`QRecord`,
  `QTuple`, `QArray`, `QVariant`, `QOption`), closures (`QClosure`, `QBuiltinFun`), mutable reference cells
  (`QRef`), auto/dynamic envelopes (`QAutoVal`), Cardelli object identity (`is` / `isnot`), and deep structural
  equality.
- **Evaluator (`quest/interpreter/`):** Scoped lexical frames (`RuntimeEnvironment`), tree-walking evaluator
  (`treewalk.py`), IR interpreter (`ir_interp.py`), shared primitive operations (`primitives.py`) and formatting
  (`formatting.py`), exceptions (`try...when...else`, `raise`), `auto` / `inspect` dynamic type reflection, and
  Cardelli standard library bridges (`builtins.py`).
- **Interactive REPL (`quest/driver/repl.py`):** Persistent multi-line REPL with transactional `UnitGraph` rollback on
  error and batch `--echo` / `-i` modes.
- Interpreter architecture in [interpreter.md](interpreter.md); REPL guide in [repl.md](repl.md).

### Step 4: Bootstrap C Compiler (Python) — *Complete*
- **Intermediate Representation & Passes (`quest/ir/`):** A-normal form with structured control flow and join points
  (`ir/lower.py`), canonical type shapes (`repr/shapes.py`), call-site specialization (`ir/specialize.py`), closure
  conversion and lambda lifting (`ir/closure.py`), representation, slot boxing, and proxy conversion insertion
  (`ir/represent.py`, `ir/slots.py`), and runtime type descriptor materialization (`ir/describe.py`).
- **Runtime Representation & C Code Generation (`quest/codegen/`):** Uniform 64-bit `QVal` ABI, 16-byte `QRecordVal`
  fat pointers with static offset dictionaries, 16-byte unboxed `QVariantVal` values with static tag remapping, uniform
  1-word boxed aggregate slots (`slot_representation`), tagged `QProxy` views on depth-upcast tuples and options,
  native pointer lowering (`T *`) for `var`/`out` parameters, runtime type descriptors (`QTypeDescriptor`), and
  portable C99 emission (`codegen/c/`).
- **Runtime & Separate Compilation (`runtime/`, `quest/modules/`, `quest/build/`):** C99 runtime with Quest's own
  garbage collector ([collector.md](collector.md); `--nogc` never collects),
  `setjmp`/`longjmp` exceptions with `<unwind.h>` native stack tracebacks, JSOG dynamic graph serialization
  (`dynamic.extern` / `dynamic.intern`), separate compilation of interfaces (`.int.h`, `.qi`) and modules (`.mod.c`,
  `.o`, `.qm`), and incremental build/dependency resolution (`BuildEngine`).
- Specifications: [runtime-design.md](runtime-design.md), [ir.md](ir.md), [c-representation.md](c-representation.md),
  [codegen-c.md](codegen-c.md), [modules.md](modules.md), [build-process.md](build-process.md), and
  [extensions.md](extensions.md).

### Step 5: Self-Hosted Compiler & Interpreter (Written in Quest) — *Complete*
- The compiler and interpreter in idiomatic, modular Quest under `questlang/`
  ([compiler-organization.md](compiler-organization.md)): the front end, the type checker (which reports several
  errors, [diagnostics.md](diagnostics.md) §4.5), the tree-walking interpreter and the REPL, the IR and its
  interpreter, and the C backend, build artifacts, and build engine.
- Collection, utility, and operating-system libraries in Quest (`collections/vector`, `collections/hashMap`,
  `collections/hashSet`, `util/maybe`, `util/stringBuilder`, `util/strutil`, `util/path`, `util/argParse`, `util/hash`,
  `io/readline`, `os/fileStats`, `os/process`; see [libraries.md](libraries.md)).
- The fixed point `Quest(Quest) == Quest`: the self-hosted compiler's build of itself writes the artifacts its seed's
  build wrote, and rebuilds itself as the same binary (`run_tests.py --self-hosting`). `./quest` runs it, built by a
  released self-hosted compiler ([release-compiler.md](release-compiler.md)), compiling modules in parallel; the
  bootstrap builds the first release.
- It is the primary compiler: the two compilers share what programs do, not how they compile them
  ([testing.md](testing.md) §2.8). The bootstrap is kept so that the compiler can be rebuilt from nothing, and the
  self-hosting check confirms that it still builds the compiler the release does.
- The self-hosted driver takes the bootstrap's commands and options: the interpreter and REPL, `compile` (with
  `--emit-c`, `--nogc`, and `-c`), separate compilation of units, and every phase's `--stop-after` and `--dump-after`.
  `self-hosted/compile_command` checks that the two drivers' commands do the same.

### Step 6: Native AArch64 Code Generator (Written in Quest) — *Complete*
- A native arm64 backend for Darwin whose objects link with the C backend's, unit by unit
  ([arm64.md](arm64.md)): lowering and layout shared with the C printer, a low-level SSA with block arguments and its
  passes ([ssa.md](ssa.md)), an SSA-to-C printer (`ssac`) as an oracle, instruction selection into machine SSA over
  virtual registers, linear-scan register allocation, and frames, tail calls, exceptions, stack maps for the
  collector, and assembly emission.
- Follows the evidence-passing object model and AAPCS64 register conventions in [runtime-design.md](runtime-design.md).
- arm64 is the default backend, for programs, the compiler, and releases, since 2026-11-12 (arm64.md §1,
  [benchmarks.md](benchmarks.md) §21); `--backend c` compiles through C.

### Step 7: Native AArch64 JIT & Interactive Incremental Runtime — *Complete*
- In-process code emission and execution for the REPL, `-e`, and files, the default way the driver runs them
  (`--no-jit` interprets), with the interpreters' semantics: interactive code redefines a name of the same type in
  place ([repl.md](repl.md) §6), and otherwise a rebinding shadows (no hot-swapping).
- Described in [jit.md](jit.md): `unsound` interfaces and modules ([modules.md](modules.md) §4.4), frames found by
  the frame-pointer chain, `os/value` and `os/code` ([libraries.md](libraries.md) §4.4), interface
  fingerprints in every module unit (`qh_`), an in-memory arm64 encoder and loader in place of the assembler and
  linker, and the user's own modules compiled and loaded as units ([benchmarks.md](benchmarks.md) §10 has the times).
  What jit.md leaves for later (inlining across inputs, redefinition with another type, surviving faults) is open
  work there.

### Step 8: WebAssembly Backend & the REPL in a Browser — *Complete*
- A backend, `wasm`, that compiles Quest to WebAssembly with garbage collection ([wasm.md](wasm.md)): the engine's
  structs and arrays are Quest's values and its collector is Quest's (§2), every closure has a native and a uniform
  entry (§3), and the runtime is the C runtime ported to Quest over intrinsics, with `Real`'s formatting, parsing, and
  mathematics in Quest too (§4). Each unit is a module (§5).
- Built in five milestones, 2026-11-13 to 2026-11-16: the compiler compiling itself in node, to the same modules as
  natively; the interpreter in a browser page; each REPL input compiled to a module and loaded into the session, as the
  arm64 JIT does; the rest of the language (locations, variants, proxies, `dynamic`); and a review's fixes.
- The REPL page ([wasm.md](wasm.md) §6), published at <https://haahr.github.io/quest/>, runs in Chrome, Firefox, and
  Safari, and survives a stack overflow by rolling the input back or replaying the session. What differs from the
  native backends is in §7; the suites run its programs in wasmtime and node (§8.3).

---

## See Also
- [README.md](../README.md): Project overview and quickstart.
- [syntax.md](syntax.md): Lexer, parser, and untyped AST specification.
- [type-system.md](type-system.md): Semantic types, subtyping theory, and elaboration.
- [pipeline.md](pipeline.md): Compiler pipeline framework and CLI driver.
- [ir.md](ir.md): Intermediate representation and optimization/lowering passes.
- [codegen-c.md](codegen-c.md): C code generator and compiler runner.
- [c-representation.md](c-representation.md): C ABI and runtime representation.
- [runtime-design.md](runtime-design.md): Object representation (Evidence Passing vs Fat Pointers) and ABI.
- [interpreter.md](interpreter.md): Interpreter runtime architecture, value model, and semantic decisions.
- [compiler-organization.md](compiler-organization.md): Organization of the self-hosted compiler, and how it differs
  from the bootstrap.
- [wasm.md](wasm.md): The WebAssembly backend, its runtime, and the REPL in a browser.
- [extensions.md](extensions.md): OS, CLI, and native interop extensions to the core language.
