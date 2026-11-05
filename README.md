# The Quest Programming Language

An implementation of **Quest**, the language Luca Cardelli designed at Digital Equipment Corporation's Systems
Research Center (SRC) and described in [*Typeful Programming*](http://lucacardelli.name/Papers/TypefulProg.pdf)
(1989). Quest grew out of Cardelli's earlier work on ML and on Amber, and out of the bounded quantification of Cardelli
and Wegner's *On Understanding Types, Data Abstraction, and Polymorphism* (1985). It was in turn a major influence on
Modula-3, designed at SRC in the same years.

Quest's type system is Girard's System $F^\omega$ (functions polymorphic in types, and type operators, which are
functions from types to types) with subtyping added: System $F_{<:}^\omega$. Types have types of their own, called
kinds, so a program has three levels:
- **Values:** first-class functions, mutable variables and fields (`var`), exceptions, and modules.
- **Types and type operators:** records, tuples, variants, options, functions, and recursive types; a type operator
  (`Fun(X::K) T`) is applied at compile time.
- **Kinds:** `TYPE`, the kind of every type; `POWER(T)`, the kind of `T`'s subtypes, which bounds a type parameter;
  and `ALL(X::K1) K2`, the kind of a type operator.

Subtyping is structural: a record type with more fields is a subtype of one with fewer, whatever either is named.
Quantification is impredicative: a type parameter may stand for any type, a polymorphic one included, so polymorphic
functions are values like any other. This function, from [examples/argmax](examples/argmax/), finds the element of an
array whose key is greatest, and is polymorphic in the types of the elements and of their keys:

```quest
let argmax(E::TYPE K::TYPE)(
           a: Array(E)
           key: All(e: E) K
           isGreater: All(x: K y: K) Bool): Tuple index: Int element: E end =
    begin
        let n = arrayOp.size(:E a)
        if n is 0 then raise empty end end
        let var best = 0
        let var bestKey = key(a[0])
        for i = 1 upto n - 1 do
            let k = key(a[i])
            if isGreater(k bestKey) then
                best := i
                bestKey := k
            end
        end
        tuple let index = best let element = a[best] end
    end

let words = array of "pear" "fig" "banana" "kiwi" end
let longest = argmax(words string.length {>})
```

`:E` passes a type argument explicitly; the call at the end leaves `E` and `K` to be inferred, and `{>}` is the
operator `>` as a function.

---

## Why?

I read Luca Cardelli's paper [*Typeful Programming*](http://lucacardelli.name/Papers/TypefulProg.pdf) when I was an undergraduate and I was taken both by its philosophical arguments – *"There exists an identifiable programming style based on the widespread use of type information handled through mechanical typechecking techniques"* – and the power and elegance of its design. But, as far as I know, the original implementation was never made public and I never had a chance to use it.

Flash forward nearly four decades, I'm late to the party on agentic programming and vibe coding, but have recently gotten a taste of how much is possible. I wanted a hobby project to stretch my skills in directing a model to build something interesting, so I decided to build a version of Quest that I could actually play with. At the risk of having this project dismissed as AI slop, I will straightforwardly say that every line of code (and, other than this section, of documentation) in this project was written by Gemini (3.7 and 3.8 Flash, so far) or Claude (Opus 5.5) in [Google Antigravity](https://antigravity.google/) or [Claude Cowork](https://claude.com/product/cowork).

I've been trying to keep the design clean and the code readable; I've found Dave Rensin's paper and methodology [*Elephants, Goldfish and the New Golden Age of Software Engineering (or, Design is the New Code)*](https://drensin.medium.com/elephants-goldfish-and-the-new-golden-age-of-software-engineering-c33641a48874) to be very helpful in that regard. But, if human-guided, AI-written code bothers you, please stay away.

Otherwise, if you're interested in a retro programming language and an interesting waypoint in the evolution of types, take it out for a spin. *— Paul Haahr*

---

## Status

Two implementations of the language are tested to behave alike: a bootstrap in Python, with an interpreter and a
compiler to C, and a self-hosted compiler in Quest, which compiles itself to C or to arm64 machine code (see the
Quickstart below). Both run on macOS on Apple Silicon only; anything else is left as an exercise for the reader.

The compilers were built in steps ([docs/roadmap.md](docs/roadmap.md)):

| Step | Language | Subsystem | Status |
| :--- | :--- | :--- | :--- |
| **1** | Python | Front end: lexer, PEG parser, and syntax tree | Complete |
| **2** | Python | Type checker: $F_{<:}^\omega$ subtyping, recursive types, elaboration | Complete |
| **3** | Python | Tree-walking interpreter and REPL | Complete |
| **4** | Python | Compiler to C99, through an IR, with the Boehm garbage collector | Complete |
| **5** | Quest | Self-hosted front end, interpreter, and compiler to C | Complete |
| **6** | Quest | Native arm64 backend | Working; C is still the default backend |
| **7** | Quest | arm64 JIT compiler and incremental runtime | Begun ([docs/jit.md](docs/jit.md)): all 8 steps done |

### Implementation Notes
- **Representation:** polymorphism, structural subtyping, and mutable state together make data layout the subtle
  part of compiling Quest. Generic code must hold a value of any type in one word; a record seen at a supertype has its
  fields at other offsets; and an upcast cannot copy a value, because a mutable field must stay shared and `is` tests
  identity. [docs/runtime-design.md](docs/runtime-design.md) explains how records carrying their field offsets,
  one-word slots, proxies for upcast tuples and options, and runtime type descriptors fit together.
- **Types:** recursive types are equal to their unfoldings (equi-recursive), and subtyping between them is checked by
  Amadio and Cardelli's coinductive algorithm ([docs/type-system.md](docs/type-system.md)).
- **Compilation:** the typed syntax tree is lowered to an A-normal-form IR and refined by small passes
  ([docs/ir.md](docs/ir.md)); the arm64 backend goes through an SSA form with linear-scan register allocation
  ([docs/arm64.md](docs/arm64.md)).
- **Performance:** on the MLton benchmark suite, translated from Standard ML, programs from the C backend take 3.7
  times as long as MLton's, and from the arm64 backend 7.8 times (geometric means;
  [docs/benchmarks.md](docs/benchmarks.md) §7).

---

## Quickstart

There are two implementations of Quest in this repository, and a launcher for each:
- `./questboot` runs the **bootstrap**, written in Python (`bootstrap/python/`). It needs no build step: it parses,
  type-checks, and interprets a program directly, or compiles it to C99 and then to a native binary with the host C
  compiler. It is the slower of the two, and its main job is to build the self-hosted compiler.
- `./quest` runs the **self-hosted compiler**, written in Quest (`questlang/`). It accepts the same programs and
  takes the same commands, and is built from source, by the bootstrap or by a release of itself, the first time it is
  run.

### Prerequisites
- macOS on Apple Silicon, with the Xcode Command Line Tools (`clang`, the assembler, and the linker).
- Python 3.11 or later, for the bootstrap and the test runner. The launchers look for Homebrew's Python first; set
  `PYTHON` to use another.
- Git: the self-hosted compiler's releases live in the clone's git directory.
- Optional: GNU readline (`brew install readline`) for the REPL's line editing; without it the REPL uses libedit's,
  or none.

### Trying Quest with the Bootstrap
`./questboot` works as soon as the repository is cloned:

```bash
git clone https://github.com/haahr/quest.git
cd quest
./questboot -e "40 + 2"                                         # prints 42 : Int
./questboot                                                     # the REPL, when standard input is a terminal
./questboot examples/argmax/argmax.quest                        # interprets a program
./questboot compile examples/argmax/argmax.quest -o argmax      # compiles it to a native binary, by way of C
./questboot --stop-after typecheck examples/argmax/argmax.quest # prints the type-checked syntax tree
```

[docs/walkthrough.md](docs/walkthrough.md) follows `examples/argmax` through every phase of the compiler.

### The Self-Hosted Compiler and the `quest` Driver
The self-hosted compiler is a Quest program, `questlang/driver/main.quest` and the modules it imports, called the
driver because it is the command-line entry point that runs the front end, the interpreter, and the backends. Its
front end and interpreter mirror the bootstrap's; beyond the bootstrap, it optimizes the IR
([docs/ir.md](docs/ir.md) §8.6), can write arm64 machine code instead of C (`--backend arm64`;
[docs/arm64.md](docs/arm64.md)), and runs programs, `-e`, and the REPL's inputs by compiling them to arm64 code in
memory rather than interpreting them (`--no-jit` interprets; [docs/jit.md](docs/jit.md)).

`./quest` is a shell script that builds the driver into a native binary when needed and then runs it. The binary is
not checked in: it is built from `questlang/` on first use, and again whenever `questlang/`, `lib/`, or `runtime/`
changes. In a fresh clone there is no release of the compiler to build it with, so the first run builds it with the
bootstrap, which takes about ten minutes; later builds compile only what changed:

```bash
./quest -e "40 + 2"       # builds .build/quest-stages, then prints 42 : Int
```

The build has two stages, each a self-hosted compiler: the bootstrap (or a release) compiles the driver into stage 1,
and stage 1 compiles it again, against the tree's `lib/` and `runtime/`, into stage 2, which is what `./quest` runs.
Stage 2 is thus the compiler compiled by itself, from the current source. Set `QUEST_VERBOSE=1` to see the steps,
`QUEST_JOBS` to change how many modules build at once (by default, one per CPU), and `QUEST_BACKEND` to choose the
backend stage 1 compiles stage 2 with: `c` (the default), `arm64`, or `ssac`, which prints the arm64 backend's
intermediate form as C, as a check on it.

To build faster, and to run the tests as a push needs them, cut the clone's first release, from a clean checkout of
`main`. It runs the self-hosting check and the self-hosted suite first, so it takes about twenty minutes:

```bash
tools/release --seed bootstrap   # the first release, built by the bootstrap
tools/release --show             # what it is
```

From then on `./quest` builds from the release, in about two minutes from nothing, and `tools/check` seeds the
self-hosting check from it. Every worktree of the clone shares the release
([docs/release-compiler.md](docs/release-compiler.md)). Without a release, `tools/check --seed bootstrap` runs the same
suites.

### Releases and Installing Quest

A release is a checked build of the self-hosted compiler at a commit on `main`, with that commit's `lib/` and
`runtime/`, kept in the clone's git directory. It seeds `./quest`'s builds, so after a pull, `./quest` rebuilds
its stages from the release rather than from the bootstrap; a new release is only needed when the compiler's sources
use something the current release cannot compile. `tools/release` manages them:

```bash
tools/release                    # cut a release from HEAD (clean, and on main), after the self-hosting check
tools/release --whole-program    # the same, releasing the whole-program build of the compiler
tools/release --show             # describe the current and previous releases
tools/release --verify           # check the current release: its binary's digest, and a program it builds and runs
tools/release --rollback         # swap the current and previous releases
tools/release --install          # install the current release for use outside the tree
```

`--install` copies the current release to `~/.local/share/quest/COMMIT`, where later cuts cannot remove it, checks
it there, and writes `~/.local/bin/quest`, which runs it against its own `lib/` and `runtime/`; `--install PREFIX`
uses `PREFIX/share` and `PREFIX/bin` instead. Installing a later release keeps the earlier ones beside it. An installed
compiler still needs clang to build programs.

### Running and Compiling Quest Code
A Quest source file's suffix says what it holds. An interface, the exported names and types of a module, is in a
`.int.quest` file; a module, which implements an interface, is in a `.mod.quest` file; and a main program, which
imports interfaces and runs from top to bottom, has the suffix `.quest` alone. `import scoring: Scoring` in
`examples/argmax/argmax.quest` finds `scoring.int.quest` and `scoring.mod.quest` by name, in the importing file's
directory first and then on the search path (`-I` and `lib/`; [docs/modules.md](docs/modules.md) §2).

`./quest` runs and compiles programs:

```bash
# Interpret an expression, or a program; the arguments after the program are its own (system.args)
./quest -e "let x: Int = 40 + 2; x"
./quest program.quest arg1 arg2

# Give arguments to an inline program, or the REPL, after --
./quest -e "import system: System; system.args" -- arg1 arg2

# Compile a program to a native binary, by way of C
./quest compile program.quest -o my_app

# Write the C instead, or compile with the collector never collecting
./quest compile program.quest --emit-c
./quest compile program.quest --nogc -o my_app

# Compile to arm64 machine code instead of C
./quest compile --backend arm64 program.quest -o my_app

# Print a phase's output and stop: the tokens, the syntax tree, the typed tree, the first IR, the C
./quest --stop-after tokenize program.quest
./quest --stop-after parse program.quest
./quest --stop-after typecheck program.quest
./quest compile --stop-after ir_core program.quest
./quest compile --stop-after codegen_c program.quest

# Print a phase's output and continue
./quest --dump-after parse --stop-after typecheck program.quest
```

As with `python script.py`, the driver's options come before the program file: everything after it, options
included, is the program's. (`quest compile`, which does not run the program, takes options anywhere, as does the
driver for an interface or module file.)

`./questboot` takes the same commands and options, except `--backend` and `-j N` (build N modules at once).

### Running Tests

```bash
tools/check            # before a push: the suites a change needs, at once (docs/testing.md section 4.1)
tools/check --all      # every suite
python3.11 run_tests.py                   # the bootstrap's golden-file and error tests
python3.11 run_tests.py --self-hosted     # the self-hosted compiler's
PYTHONPATH=bootstrap/python python3.11 -m unittest discover -s tests/python   # the bootstrap's unit tests
```

---

## Known Differences from *Typeful Programming*

1. **Systems of interfaces:** the paper's "Huge Programs" section (§7.3) describes systems of interfaces, which group
   interdependent interfaces and modules, but only sketches out the design, and the paper says that features without
   syntax in its appendix "should be regarded with more suspicion". They are not implemented.
2. **Serialization:** `dynamic.extern` and `dynamic.intern` write and read typed data, cyclic data included, but not
   functions, which the paper's design would also cover.
3. **Hierarchical module names:** interfaces and modules have names like `util/random` that map to directories; the
   paper's names are flat.
4. **Optional semicolons:** the paper ends every top-level phrase with `;`. Here a semicolon is accepted only there
   too, but is never required: the grammar does not need one to find where a phrase ends.
5. **Catching and re-raising any exception (`try ... else with e then`):** in the paper, a `try`'s `else` branch
   catches an exception that no `when` branch names, but cannot refer to it. Here `else with e then` binds the caught
   exception, whatever its type, and `raised.reraise` raises it again, still reported where it was first raised. Code
   can thus clean up after any failure and let the failure continue, as `finally` does in other languages
   ([docs/raised.md](docs/raised.md)).
6. **Hexadecimal integers:** the paper writes integers in decimal only. Here `0x` or `0X` followed by hexadecimal
   digits is an integer too (`0xFF` is 255, `~0x10` is -16), within the same 64-bit signed range, so
   `0xFFFFFFFFFFFFFFFF` is out of range rather than ~1. In the paper's syntax, `0xab` is the integer 0 followed by
   the identifier `xab` ([docs/extensions.md](docs/extensions.md), "Hexadecimal Integers").
7. **Redefinition at the REPL:** the paper's top level is lexically scoped, so a new definition of a name shadows it,
   and functions defined earlier keep the old one. Here, interactively (the REPL, and a file run with `-i`), a new
   `let` of a name at the same type updates it in place, for the code that already uses it, so that fixing a function
   fixes its callers; one at another type shadows, with a warning. Programs are unchanged
   ([docs/repl.md](docs/repl.md) §6).

[docs/extensions.md](docs/extensions.md) describes the additions to the language and its libraries, among them the
`System` interface to the operating system, the `Word` type, and `external` declarations of C functions.

### Characters Are Bytes
As in the paper, whose `Ascii` interface converts between characters and the codes 0 to 255, a `Char` is a byte and a
`String` a sequence of bytes, and there is no support for UTF-8. Bytes pass through unchanged, in source files and in
input and output, so UTF-8 text can be read, copied, and printed; but `string.length` counts bytes, not characters.

---

## Documentation Index

To learn how the compiler works, start with [docs/walkthrough.md](docs/walkthrough.md), which follows one small
program through every phase, then [docs/type-system.md](docs/type-system.md) and
[docs/runtime-design.md](docs/runtime-design.md).

### 1. The Language
- [docs/TypefulProgramming.md](docs/TypefulProgramming.md): Cardelli's *Typeful Programming* (1989, revised 1993),
  the definition of Quest this implementation follows.
- [docs/ASemanticBasisForQuest.md](docs/ASemanticBasisForQuest.md): Cardelli and Longo's semantics of Quest's
  three levels and subtyping (1991).
- [docs/TheQuestLanguageAndSystem.md](docs/TheQuestLanguageAndSystem.md): Cardelli's description of the original
  Quest system and its bytecode interpreter (1994).
- [docs/grammar.txt](docs/grammar.txt): the grammar, in EBNF.
- [docs/extensions.md](docs/extensions.md): additions to the language (`System`, `Word`, hierarchical modules, and
  `external` declarations).
- [docs/new-libraries.md](docs/new-libraries.md): libraries beyond the paper's (collections, `util/maybe`,
  `util/stringBuilder`, `util/path`, `util/argParse`, and others).
- [docs/raised.md](docs/raised.md): catching an exception of any type with `else with e then`, and raising it again.
- [docs/dynamic.md](docs/dynamic.md): values packaged with their types (`auto`, `dynamic.T`), testing their types at
  run time (`inspect`), and serializing them (`dynamic.extern`, `dynamic.intern`).
- [docs/converting-python-to-quest.md](docs/converting-python-to-quest.md): translating Python idioms to Quest.

### 2. Front End and Type System
- [docs/walkthrough.md](docs/walkthrough.md): *The Life of `argmax`*, every compiler phase applied to
  [examples/argmax/](examples/argmax/).
- [docs/pipeline.md](docs/pipeline.md): the phases, from tokens to a running program, and the command-line driver.
- [docs/syntax.md](docs/syntax.md): the lexer, the packrat PEG parser, the syntax tree, and desugaring.
- [docs/type-system.md](docs/type-system.md): kinds and subkinding, coinductive subtyping of recursive types,
  bidirectional elaboration, and how static types become runtime shapes.
- [docs/modules.md](docs/modules.md): interfaces and modules, abstract and manifest types, how imports are found, and
  separate compilation.
- [docs/build-process.md](docs/build-process.md): incremental separate compilation, interface and module manifests,
  and linking.
- [docs/interpreter.md](docs/interpreter.md): the tree-walking interpreter and its evaluation rules.
- [docs/repl.md](docs/repl.md): the REPL, its continuation lines, and how it undoes a phrase that fails.
- [docs/jupyter-kernel.md](docs/jupyter-kernel.md): the Jupyter kernel, its protocol, interrupts, and installing it.

### 3. IR, Runtime, and Code Generation
- [docs/runtime-design.md](docs/runtime-design.md): why compiling Quest is subtle, and how its runtime
  representations fit together.
- [docs/ir.md](docs/ir.md): the A-normal-form IR, its canonical shapes of types, and its passes (`lower`, `simplify`,
  `specialize`, `closure`, `represent`, `describe`).
- [docs/inlining.md](docs/inlining.md): the plan for what remains of the IR optimizer (ir.md §8.6): tuning, and
  workers.
- [docs/mlton-gap.md](docs/mlton-gap.md): the plan for five optimizations the MLton performance review found missing.
- [docs/c-representation.md](docs/c-representation.md): the C runtime's ABI: value and slot representations, proxies,
  closures, and arrays.
- [docs/codegen-c.md](docs/codegen-c.md): how the IR is printed as C99 and compiled.
- [docs/name-mangling.md](docs/name-mangling.md): how Quest names become C symbols.
- [docs/ssa.md](docs/ssa.md): the SSA form the native backend is built on, and its passes (escape analysis,
  promotion, tail calls).
- [docs/arm64.md](docs/arm64.md): the arm64 backend: instruction selection, register allocation, and assembly for
  Darwin.
- [docs/exceptions.md](docs/exceptions.md): how an uncaught exception is reported, with where it was raised and the
  functions active then, in the interpreters and in compiled code.

### 4. Testing and Contributing
- [docs/testing.md](docs/testing.md): the test suites: golden files, error tests, and the self-hosting check.
- [docs/benchmarks.md](docs/benchmarks.md): the MLton benchmarks translated to Quest, and the measurements of each
  backend against MLton.
- [docs/diagnostics.md](docs/diagnostics.md): how errors are reported.
- [docs/instructions.md](docs/instructions.md): the guide for contributors, people and models: workflow, commands,
  conventions, and Quest syntax traps.

### 5. The Self-Hosted Compiler
- [docs/roadmap.md](docs/roadmap.md): the seven steps from the Python bootstrap to a JIT compiler.
- [docs/compiler-organization.md](docs/compiler-organization.md): the modules of the self-hosted compiler
  (`questlang/`), and how they differ from the bootstrap's.
- [docs/release-compiler.md](docs/release-compiler.md): releases of the self-hosted compiler (`tools/release`), from
  which `./quest` is built.
- [docs/tasklist.md](docs/tasklist.md): open bugs and planned tasks.
