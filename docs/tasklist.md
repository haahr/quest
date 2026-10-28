# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Parallel builds in the self-hosted engine

**Problem.** The self-hosted build engine (`questlang/build/engine`) compiles one unit at a time, in its own process, so
a build uses a single core. Building `questlang/driver/main` takes about a minute, a third of it in clang. Building the
questlang tests for the self-hosted suite takes several more, nearly all of it compiling the questlang modules they
share. The tests build one after another into a shared build directory (`build_questlang_tests` in
`bootstrap/python/quest/testing/runner.py`), because the engine takes no locks: two builds at once could both find a
unit stale and write its artifacts at the same time.

**Reproduce.** Run `./questc` after touching `questlang/types/model.mod.quest`, or `run_tests.py --self-hosted`, and
watch the CPU: one `questlang-driver` process at 100% of one core.

**Where to start.** Add `-j N` to the driver and have the engine compile up to N units at once, each in a child process
of the driver (a `--compile-unit` mode, or `-c` with `--build-dir`). This needs a way to start processes without waiting
for them, which `os/process` provides ([new-libraries.md](new-libraries.md) §4.2). The engine first has to know the
import graph before compiling anything: parse each unit's imports, which is cheap, instead of finding them as it
compiles. A unit can compile once the interfaces it imports have their `.qi` files. Modules depend only on interfaces,
not on other modules' objects, so most modules can compile in parallel once the interfaces are built. Keep the queue
order for linking and for the log, so that build output stays deterministic. Then build the questlang tests with one
driver invocation that takes every test as a root, or with `-j`, instead of one at a time.

**Done when.** `./questc -j 8` and the self-hosted suite's questlang test build use several cores. Their artifacts are
byte-identical to a serial build's, apart from build.log's order, and the driver build is several times faster.

---

## Faster word operations in compiled code

**Problem.** Each `word` operation in compiled code (`word.xorBits`, `word.shift`, `word.rotate`, and the rest of
`lib/word.int.quest`) costs three calls. The caller calls the importer's wrapper `qv_word_xorBits`, which calls
through the closure in the `word` module record, which calls the external `quest_word_xor_bits` in the runtime. None
of them can be inlined, because the module record is only filled in at run time. The self-hosted compiler hashes
type text with SHA-256 written in Quest (`questlang/codegen/sha256`) and hashes keys in `util/hash`, both made of word
operations. Profiling the compiler building itself (2026-10-27) put about 7.5% of its time in these call layers.

**Reproduce.** Build `questlang/driver/main` with `./questc` from nothing under `sample` (macOS) or `perf`, and
compare the time in the `qv_word_*` wrappers and closures with the time in the `quest_word_*` functions.

**Where to start.** Compile a call to a `word` operation whose target is known statically into a direct call to its
runtime function, or into the C operator (`^`, `<<`, ...) for the simple ones. An importer does not know today which
members of `word` are externals, or which runtime functions they are: neither the `.qi` nor the `.qm` records it, so
either the artifacts record it (an ABI change) or the backend treats `word` as a builtin it knows. Do the same in the
bootstrap, and in the same commit, while the two compilers are kept in step. Every compiled program's C changes, so the
`codegen_c` digests are regenerated. A native SHA-256 primitive would remove most of the remaining cost of `layout`'s
digests, but needs a new runtime primitive and so a release before `questlang/` can use it (docs/release-compiler.md
§2).

**Done when.** Word operations in generated C are direct calls or C operators, the self-hosted build of
`questlang/driver/main` spends no measurable time in the call layers, and both compilers produce the same C.

---

## An `Ok` component of a tuple or option payload in compiled code

**Problem.** A tuple type with a component of type `Ok`, or an option tag whose payload has one, compiles to a C struct
with a `void` field, which clang rejects ("field has incomplete type 'void'"). The interpreters run such programs.
Converted code works around it with an empty tuple, `Let Unit = Tuple end`, in the `Ok` component's place
(benchmarks/mlton).

**Reproduce.** Compile `Let P = Tuple e: Ok s: Int end let p: P = tuple let e = ok let s = 1 end let n = p.s`.

**Where to start.** `emit_aggregate_structs` in `bootstrap/python/quest/codegen/c/declarations.py`, which takes each
component's slot type, and its port in `questlang/codegen/c/declarations.mod.quest`; the slot of an `Ok` component
should be no field at all (or a placeholder byte), with the projections and constructors that use the component's index
agreeing.

**Done when.** Tuples and option payloads with `Ok` components compile and run, with tests in `tests/source/`, in both
compilers.

---

## Option tags named like C keywords in compiled code

**Problem.** An option tag is used verbatim as the name of its payload's member in the C union of the option's struct,
so a tag named like a C keyword (`int`, `struct`, `union`, `if`, ...) produces C that does not compile. Converted code
renames such tags (benchmarks/mlton).

**Reproduce.** Compile `Let T = Option int with n: Int end struct end let t = option int of T with 3 end`.

**Where to start.** `emit_aggregate_structs` in `bootstrap/python/quest/codegen/c/declarations.py` (`struct
..._payload { ... } {o.name};`) and its port in `questlang/codegen/c/declarations.mod.quest`, and every place that
names the member (`printer.py`'s option accessors and the questlang printer): mangle the member name, for instance with
a prefix, everywhere at once.

**Done when.** Tags named like any C keyword compile, with a test in `tests/source/`, in both compilers.

---

## Polymorphic functions that pass exceptions of their type parameters to local functions

**Problem.** A polymorphic function that defines a local function with a parameter of type `Exception(B)`, for its
type parameter `B`, and passes it to another polymorphic function, fails in C code generation: "a thunk converts by the
descriptor of 'B', which mentions the type parameter B of the function it is made in, whose descriptor it is not
passed". The interpreters run it. Converted code makes such functions monomorphic (benchmarks/mlton).

**Reproduce.**

```
let sub(A::TYPE)(f: All(s: A e: Exception(A)) A s: A): A =
    begin
        let e: Exception(A) = exception e: A end
        try f(s e) when e with v then v end
    end
let g(B::TYPE)(x: B): B =
    begin
        let h(s: B e: Exception(B)): B = raise e with s end
        sub(:B)(h x)
    end
let y = g(:Int)(5)
```

**Where to start.** `check_available` in `bootstrap/python/quest/ir/describe.py`, which raises the error, and its port
in `questlang/ir/describe.mod.quest`: the thunk that converts `h` needs `B`'s descriptor, which `g` has but does not pass
to the thunk; closure conversion should capture it.

**Done when.** The example compiles and runs, with a test in `tests/source/`, in both compilers.

---

## Capture rules for `var` variables as the paper has them

**Problem.** The type checker's rule for which mutable variables a function may use is the reverse of the paper's.
*Typeful Programming* §4.8 says only that "functions cannot refer directly to global variables of `Var` type": they
must be passed as `in` and `out` parameters, or held in data structures (the own-variable idiom). It says nothing
against capturing local `var` variables. This implementation forbids capturing a function's local `let var` variables
(and `var` and `out` parameters) in a closure, and lets any function use a module-level or top-level `var` variable
directly ([type-system.md](type-system.md) §6.2.3, [codegen-c.md](codegen-c.md) §10.8). Its reason is an
implementation one: locals stay unboxed in their frame, so no pointer to them can outlive it. Converted code pays for
it: an SML `ref` captured by a closure has to become a tuple with a `var` field (benchmarks/mlton).

**Reproduce.** `tests/errors/typecheck/closure_capture_local_var.quest` is rejected ("Cannot capture 'var' variable
'x' in closure"), and a top-level `let var n = 0` used by a top-level `let bump(): Ok = n := n + 1` is accepted.

**Where to start.** `_check_capturable` in `bootstrap/python/quest/typechecker/checker.py` and its port in
`questlang/typechecker/checker.mod.quest`. Allowing a captured local `var` means holding it boxed, in a cell the closure
and the frame share, as a local whose address is taken already is (`location_representation`, codegen-c.md §10.8):
closure conversion (`ir/closure`, whose `capturesMutable` error goes away) and both interpreters must treat it so. `var`
and `out` parameters are references to the caller's locations, which the paper does not discuss; keep forbidding their
capture unless there is a reason not to. Forbidding direct use of a global `var` breaks any code that does it: audit
`lib/`, `questlang/`, and the tests first, and rewrite such uses with own variables. Update type-system.md §6.2.3, the
error goldens (`closure_capture_local_var` becomes a run test), and the conversion guide's rule 23. Change both
compilers in the same commit, while they are kept in step.

**Done when.** A closure can capture and update a local `var` variable, in every phase and in compiled code; a
function that refers directly to a global `var` variable is a type error; and §6.2.3 states the paper's rule.
