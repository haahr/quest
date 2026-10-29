# The Quest Programming Language

A modern implementation of **Quest**, Luca Cardelli's language based on higher-order subtyping
(System $F_{<:}^\omega$), impredicative bounded quantification, and type operators within a three-level universe:
- **Level 2 (Kinds):** `TYPE`, `POWER(T)`, and `ALL(X::K1) K2`.
- **Level 1 (Types and Type Operators):** Records, tuples, variants, options, functions, recursive types, and
  compile-time type operators (`Fun(X::K) T`).
- **Level 0 (Values):** First-class functions, mutable cells (`var`), exceptions, and modules.

The ultimate objective of this project is a **fully self-hosted compiler written in Quest itself**, targeting native
**AArch64 (ARM64)** machine code with an interactive in-process **JIT compiler**.

---

## Why?

I read Luca Cardelli's paper [*Typeful Programming*](http://lucacardelli.name/Papers/TypefulProg.pdf) when I was an undergraduate and I was taken both by its philosophical arguments – *"There exists an identifiable programming style based on the widespread use of type information handled through mechanical typechecking techniques"* – and the power and elegance of its design. But, as far as I know, the original implementation was never made public and I never had a chance to use it.

Flash forward nearly four decades, I'm late to the party on agentic programming and vibe coding, but have recently gotten a taste of how much is possible. I wanted a hobby project to stretch my skills in directing a model to build something interesting, so I decided to build a version of Quest that I could actually play with. At the risk of having this project dismissed as AI slop, I will straightforwardly say that every line of code (and, other than this section, of documentation) in this project was written by Gemini (3.7 and 3.8 Flash, so far) or Claude (Opus 5.5) in [Google Antigravity](https://antigravity.google/) or [Claude Cowork](https://claude.com/product/cowork).

I've been trying to keep the design clean and the code readable; I've found Dave Rensin's paper and methodology [*Elephants, Goldfish and the New Golden Age of Software Engineering (or, Design is the New Code)*](https://drensin.medium.com/elephants-goldfish-and-the-new-golden-age-of-software-engineering-c33641a48874) to be very helpful in that regard. But, if human-guided, AI-written code bothers you, please stay away.

Otherwise, if you're interested in a retro programming language and an interesting waypoint in the evolution of types, take it out for a spin. *— Paul Haahr*

---

## Roadmap Summary

The compiler is built using a staged bootstrap methodology across seven milestones:

| Stage | Language | Subsystem | Status |
| :--- | :--- | :--- | :--- |
| **Step 1** | Python | Front-End: Lexer, PEG Parser, and Untyped AST | **Complete** |
| **Step 2** | Python | Typechecker: $F_{<:}^\omega$ Subtyping, Equi-Recursion, Elaboration | **Complete** |
| **Step 3** | Python | Tree-Walking Interpreter & Interactive REPL | **Complete** |
| **Step 4** | Python | Bootstrap C Compiler (IR pipeline emitting C99 + Boehm GC) | **Complete** |
| **Step 5** | Quest | Self-Hosted Front-End & C Compiler (written in Quest) | In Progress |
| **Step 6** | Quest | Self-Hosted Native AArch64 Compiler (Nanopass Pipeline) | Queued |
| **Step 7** | Quest | Native AArch64 JIT & Dynamic Incremental Runtime | Queued |

For architectural details on each stage, see [docs/roadmap.md](docs/roadmap.md).

---

## Quickstart

### Prerequisites
- Python 3.11+ (used for the bootstrap compiler and test runner).
- Host C compiler (`clang` or `gcc`) for compiling generated C99 code.
- Optional: [Boehm GC](https://github.com/ivmai/bdw-gc) (`bdw-gc` via Homebrew: `brew install bdw-gc`).
  The compiler automatically falls back to standard libc allocations when `--nogc` is specified.

### Running and Compiling Quest Code
Use the unified compiler driver script `./quest`:

```bash
# Evaluate an inline Quest expression via the interpreter
./quest -e "let x: Int = 40 + 2; x"

# Execute a Quest file via the tree-walking interpreter; the arguments after it are the program's (system.args)
./quest program.quest arg1 arg2

# Give arguments to an inline program, or the REPL, after --
./quest -e "import system: System; system.args" -- arg1 arg2

# Compile Quest source to a native binary (using host clang/gcc)
./quest compile program.quest

# Compile to an explicit output binary
./quest compile program.quest -o my_app

# Emit generated C99 source code without invoking the host compiler
./quest compile program.quest --emit-c

# Compile without Boehm GC (using standard libc malloc/calloc)
./quest compile program.quest --nogc -o my_app

# Compile and stop after a specific phase to inspect canonical output:
./quest --stop-after tokenize program.quest          # Dumps token stream
./quest --stop-after parse program.quest             # Dumps untyped S-expression AST
./quest --stop-after desugar program.quest           # Dumps desugared S-expression AST
./quest --stop-after typecheck program.quest         # Dumps typed S-expression AST
./quest compile --stop-after ir_core program.quest   # Dumps lowered ANF IR
./quest compile --stop-after codegen_c program.quest # Dumps emitted C99 source

# Dump intermediate representations while continuing:
./quest --dump-after parse --stop-after typecheck program.quest

# Add include search paths for imported interfaces/modules:
./quest -I ./lib -I ./interfaces main.quest
```

As with `python script.py`, the driver's options come before the program file: everything after it, options
included, is the program's. (`quest compile`, which does not run the program, takes options anywhere, as does the
driver for an interface or module file.)

`./quest` runs the Python bootstrap. `./questc` runs the self-hosted compiler (`questlang/`), which takes the same
commands and options, apart from the deprecated `--emit-deps` and the `--option=value` spelling, and adds `-j N` (build N modules at once). It builds
itself first when its sources have changed: from the current release, when `tools/release` has cut one, else from the
bootstrap ([docs/release-compiler.md](docs/release-compiler.md)).

### Running Tests
The project includes comprehensive unit tests, golden-file integration tests, and inline diagnostic error tests:

```bash
# Before a push: every suite a change needs, at once (docs/testing.md section 4.1)
tools/check
tools/check --self-hosted-only   # a change to the self-hosted compiler alone

# Run all golden integration tests and diagnostic error tests
python3 run_tests.py

# Run only golden tests or only diagnostic error tests
python3 run_tests.py --suite golden
python3 run_tests.py --suite errors

# Run all unit tests
PYTHONPATH=bootstrap/python python3 -m unittest discover -s tests/python
```

---

## Known Differences from Typeful Programming

While this implementation strives for high fidelity to Luca Cardelli's
[*Typeful Programming*](http://lucacardelli.name/Papers/TypefulProg.pdf), several practical distinctions exist:

1. **Systems of Interfaces:**
   Cardelli discusses "systems of interfaces" in the "Huge Programs" section (§7.3) as a conceptual mechanism to group
   and configure interdependent interfaces and modules. However, this feature was not clearly defined or given formal
   syntax in the paper, and requires further thought before implementation. As Cardelli noted in Section 1:
   > *"The example language is still speculative in some parts; the boundary between solid and tentative features can
   > be detected by looking at the formal syntax in the Appendix. Features that have been given syntax there have also
   > been implemented and are relatively well thought out. Other features described in the paper should be regarded
   > with more suspicion"*

2. **Dynamic Serialization (`dynamic.extern` / `dynamic.intern`):**
   Cardelli envisioned dynamic values serializing arbitrary data and code representations. In this implementation,
   `dynamic.extern` and `dynamic.intern` serialize and deserialize typed values (primitives, records, tuples, variants,
   options, arrays, dynamic packages, and type descriptors) with cyclic reference preservation. Serialization of
   first-class functions and closures is not supported due to portability, code versioning, and execution
   environment constraints.

3. **Hierarchical Module Namespaces & Signature Aliasing:**
   Cardelli's module system placed all interfaces and modules in a single flat namespace, with "systems of modules"
   (§7.3) remaining an underspecified concept. This implementation of Quest introduces hierarchical module namespaces
   with forward slashes (`/`) mapping directly to filesystem directory trees (e.g. `import util/random : util/Random`),
   along with two-tier local signature aliasing (`import rnd : Rnd = util/random : util/Random` and
   `import :Rnd = :util/Random`).

4. **Optional Semicolons:**
   The paper ends every top-level phrase with `;`. This implementation accepts a semicolon only there too, but does
   not require it, in files or at the REPL: Quest's grammar never needs one to find where a phrase ends.

For full details on language extensions (including the `System` OS interface and native `external` syntax) as well as
runtime additions, see [docs/extensions.md](docs/extensions.md).

---

## Characters and Strings: Bytes, Not UTF-8

**This implementation of Quest does not support UTF-8**, at least not yet. As in Typeful Programming, whose `Ascii`
interface converts between characters and the codes 0 to 255, a `Char` is a byte and a `String` is a sequence of bytes.
Only the ASCII range, 0 to 127, has a defined meaning; what a byte from 128 to 255 means is up to whoever reads it, as
it was for C programs in 1987.

Bytes pass through unchanged. A source file may hold any bytes, in comments and in string and character literals, and
the escapes `\ddd` and `\xHH` give any code up to 255. Readers and writers, the standard streams, command-line
arguments, environment variables, and file names are all read and written a byte per character, by the interpreter as
by compiled code. So a UTF-8 file can be copied, and UTF-8 text in a string literal printed, correctly. But
`string.length` counts bytes, not characters, and `string.getChar` gets a byte, which may be part of a multi-byte
character.

---

## Documentation Index

The documentation in `docs/` is organized to take you from Quest's language foundations through the front end, type
system, intermediate representation, and native runtime design. If you are new to the compiler, start with
[docs/walkthrough.md](docs/walkthrough.md), [docs/pipeline.md](docs/pipeline.md),
[docs/type-system.md](docs/type-system.md), [docs/runtime-design.md](docs/runtime-design.md), and
[docs/ir.md](docs/ir.md).

### 1. Foundational Literature & Language Specification
- [docs/TypefulProgramming.md](docs/TypefulProgramming.md): Luca Cardelli's foundational treatise on Quest and typeful
  programming (1989/1993).
- [docs/ASemanticBasisForQuest.md](docs/ASemanticBasisForQuest.md): Cardelli & Longo (1991) formal semantic foundation
  for Quest's three-level system and subtyping theory.
- [docs/TheQuestLanguageAndSystem.md](docs/TheQuestLanguageAndSystem.md): System architecture and original bytecode
  interpreter design (1994).
- [docs/grammar.txt](docs/grammar.txt): Canonical EBNF grammar specification.
- [docs/extensions.md](docs/extensions.md): Core language extensions (`System`, `Word`, hierarchical modules, and native
  `external` bindings).
- [docs/new-libraries.md](docs/new-libraries.md): Extended standard libraries (`collections/vector`,
  `collections/hashMap`, `collections/hashSet`, `util/maybe`, `util/stringBuilder`, `util/strutil`, `util/path`,
  `util/argParse`, `util/hash`).
- [docs/converting-python-to-quest.md](docs/converting-python-to-quest.md): Idiomatic translation patterns from Python
  to Quest.

### 2. Compiler Architecture, Front-End, & Type System
- [docs/walkthrough.md](docs/walkthrough.md): *The Life of `argmax`*: a guided walk through every compiler phase with
  one small program ([examples/argmax/](examples/argmax/)).
- [docs/pipeline.md](docs/pipeline.md): The phase pipeline (`tokenize` $\to$ `parse` $\to$ `desugar` $\to$ `typecheck`
  $\to$ IR passes $\to$ `codegen_c` $\to$ `run_c_compiled`), interpreter pipeline, and CLI driver.
- [docs/syntax.md](docs/syntax.md): Lexical scanning, character offset tracking, packrat PEG parser combinators,
  untyped AST structure, and syntactic desugaring (`quest/syntax/desugar.py`).
- [docs/type-system.md](docs/type-system.md): Higher-order $F_{<:}^\omega$ type system, subkinding, Amadio–Cardelli
  coinductive subtyping, recursive contractiveness ($C \succ X$), bidirectional elaboration, and how static types bridge
  to canonical runtime shapes.
- [docs/modules.md](docs/modules.md): Cardelli's first-order module system, interfaces, abstract vs. manifest types,
  canonical module names, and separate compilation contracts.
- [docs/build-process.md](docs/build-process.md): Incremental separate compilation engine, the unified `UnitGraph`
  (`quest/modules/graph.py`), `.qi`/`.qm` manifests, ABI versioning, and transitive linking.

### 3. IR, Runtime Representation, & C Code Generation
- [docs/runtime-design.md](docs/runtime-design.md): **Start here for the backend:** why compiling $F_{<:}^\omega$ with
  structural subtyping and mutable state is subtle, and how 16-byte evidence-passing structs (`QRecordVal`,
  `QVariantVal`), uniform 1-word boxed aggregate slots, tagged `QProxy` views, and runtime `QTypeDescriptor`s fit
  together.
- [docs/ir.md](docs/ir.md): The A-normal form (ANF) intermediate representation with structured control flow and join
  points, canonical `Shape`s (`ir/shapes.py`), and the five nanopasses (`lower` $\to$ `specialize` $\to$ `closure`
  $\to$ `represent` $\to$ `describe`).
- [docs/c-representation.md](docs/c-representation.md): Reference specification for the C99 runtime ABI, `QVal` and
  slot representations, proxy conversions, closures, arrays, and runtime helpers.
- [docs/codegen-c.md](docs/codegen-c.md): How the C printer (`codegen/c/printer.py`) spells the described IR as portable
  C99 and invokes the host C toolchain.
- [docs/name-mangling.md](docs/name-mangling.md): C identifier mangling rules and symbol namespaces (`g_`, `l_`, `qf_`,
  `qm_`, `qv_`).
- [docs/dynamic.md](docs/dynamic.md): Dynamic type packaging (`auto`, `dynamic.T`), runtime subtyping (`inspect`,
  `dynamic.be`), and cyclic JSOG serialization (`dynamic.extern` / `dynamic.intern`).
- [docs/exceptions.md](docs/exceptions.md): Zero-cost stack-unwinding exception tracebacks and raise-site reporting in
  interpreters and compiled code.
- [docs/interpreter.md](docs/interpreter.md): Bootstrap tree-walking interpreter, runtime `QValue` model, and
  operational evaluation rules.
- [docs/repl.md](docs/repl.md): Interactive REPL, multi-line continuation heuristics, and transactional error rollback.

### 4. Testing, Diagnostics, & Contributor Guide
- [docs/testing.md](docs/testing.md): Test harness architecture: golden files, inline comment error tests, IR phase
  evaluators, conversion matrices, and performance benchmarks.
- [docs/benchmarks.md](docs/benchmarks.md): The MLton benchmark suite converted to Quest, the topline performance
  metric (the self-hosted compiler's time over MLton's), its baseline, and where the time goes.
- [docs/diagnostics.md](docs/diagnostics.md): Structured diagnostic error reporting, severity levels, and multi-file
  import traces.
- [docs/instructions.md](docs/instructions.md): Guide for contributors and models working on Quest: workflow, commands,
  invariants, code and documentation conventions, and Quest syntax traps.

### 5. Roadmap & Self-Hosting Plans
- [docs/roadmap.md](docs/roadmap.md): Seven-stage implementation roadmap from Python bootstrap to native AArch64 JIT.
- [docs/compiler-organization.md](docs/compiler-organization.md): Module architecture and milestones for the
  self-hosted Quest compiler (`questlang/`).
- [docs/quest-self-hosting-prerequisites.md](docs/quest-self-hosting-prerequisites.md): Library and runtime
  prerequisites for self-hosting.
- [docs/release-compiler.md](docs/release-compiler.md): Releases of the self-hosted compiler (`tools/release`), which
  seed `./questc` in two stages.
- [docs/tasklist.md](docs/tasklist.md): Open bugs and planned tasks.
