# Comments on the Four WebAssembly Plans

Comments for each plan's author, from the comparison in [wasm-plans-comparison.md](wasm-plans-comparison.md). Each
names something the plan should think through and answer in its text. None proposes an answer: the answer is the
author's, and may be that the issue does not arise, with the reason.

§1 is for every author. §2 to §5 are one per plan, in addition to §1.

---

## 1. For Every Plan

1. **Traps.** Which WebAssembly instructions the backend would emit can trap (integer division, conversion of a
   `Real` to an integer, array access, a failed cast, an access through null)? No wasm handler catches a trap. For
   each, what does Quest say happens today (an exception a `try` can catch, a fatal error, undefined), and what will
   happen on this target?
2. **Tail calls through whatever stands between a caller and an unknown callee** (a uniform entry, an adapter, a
   boxing of the result). Which calls that are tail calls natively stop being tail calls? What does that do to a
   loop written through closures, on the stack a browser gives?
3. **The stack.** Opus measured about 512 KB in a Chromium worker and about 1 MB on a page's thread, against 8 MB
   natively. What is the deepest recursion of the compiler itself on a realistic input (not only of the
   interpreter's 1,000 calls), and what does the plan do when the host, not the program, sees the overflow?
4. **Limits of the engines.** What are the limits on subtype depth, struct fields, parameters, locals, a function's
   size, and types per module, and which of the plan's encodings (a subtype per tuple arity, a closure struct per
   function, an initializer that builds every descriptor) can reach one, in the compiler or in a user's program?
5. **Type identity across modules.** State exactly which types are in one recursion group and which stand alone.
   For each pair of runtime types that code tells apart with a cast or a test: what makes them distinct types, and
   does that survive someone later adding or removing a field?
6. **Reference locals.** Under validation's rule for locals of non-null reference type, what are the types of a join
   point's parameters, an `out` parameter's target, and a variable assigned on both arms of an `if`? What does the
   choice cost?
7. **`Int` where WebAssembly wants `i32`:** array and string lengths, indices, an allocation's size. What happens
   at a value that does not fit?
8. **Bytes across the host boundary.** JavaScript cannot read or write a GC array or struct. Say how text, a file's
   contents, and a JIT module's bytes cross in each direction, in the page and under WASI, and what it costs for
   the compiler reading its own sources.
9. **What the page serves.** The interpreter runs a library module from its source. For each stage of the plan
   (interpreting, JIT), which files of `lib/` must the page have: interfaces, modules' sources, `.qi`, compiled
   modules? Who produces each, and for which target?
10. **The driver as the library, against whole-program optimization.** If the page's compiler is one optimized
    module, what does an input's module import when the function it names was inlined, specialized, or removed? If
    it is a module per unit, what is given up?
11. **Artifacts and caches per target.** Does anything in a `.qi`, a build directory, the ABI version, or the
    fingerprint of jit.md §3.3 depend on the backend? What stops an artifact of one target being used by another?

---

## 2. Fable

1. **P3, every unknown call through the uniform entry.** Opus measured the uniform entry at about ten times a
   native `call_ref` in V8, and a cast to a native closure type at nothing. The plan's argument for P3 is about
   layouts agreeing. Does that argument require that a call *never* use a native entry through a closure? Which of
   the compiler's own calls are unknown calls with `Int`, `Word`, or `Real` arguments or results (hash functions,
   comparators, `map` and `fold`)?
2. **Milestone 1's engine.** Opus measured wasmtime at about 8 ns per `call_ref` and much slower than V8 at
   allocation. What does that predict for the time of a self-compilation, run serially, and for how often it can be
   run? Is the fixed point tied to wasmtime, or to any engine with files?
3. **The collector under wasmtime.** Step 1 leaves open whether the default reclaims cycles. Opus measured that it
   does not. The plan's own check of sixty million allocations did not show it: what did that check not exercise?
4. **R5 and R8 together.** A location may be an element of a typed array. List every container a location's
   dispatch must recognize once arrays have four classes, and say what the 6.2 ns of R8's table becomes.
5. **R9, arrays' identity hashes** are "unsupported at first, to be checked". `hashMap.new` and `hashSet` default to
   `hash.identityHash` at any key type. Which key types does the compiler use there?
6. **R2, `Ok` is null.** What then is the type of a slot (nullable everywhere?), and what do a cast and an unbox do
   when given null?
7. **J1 and stage 4 of milestone 2** plan a module per unit and a whole-program module for the page (§1, comment
   10).
8. **Interrupts.** An input that does not end: what can the page do, and what happens to the session?
9. **J5, source by URL.** The plan names the asynchrony. It does not say what a failed or slow fetch is to the
   compiler (an error at the import, a retry), nor how `QUEST_PATH`'s order is kept when a lookup cannot ask whether
   a file exists without fetching it.
10. **§8, item 8, the stack** deserves the treatment Opus gives it (§1, comment 3), since the first milestone's
    compiler recurses in wasmtime with a limit that is a flag, and the second's in a worker with one that is not.
11. **Safari** is said to have what is needed. Exception handling with `exnref` and tail calls there were not
    checked.

---

## 3. Opus

1. **What a native signature is (§5.9).** The table of §5.1 gives `String` the native type `(ref $string)`. At a
   call site inside generic code, whose static type mentions a type parameter, what is "the native signature S",
   and does a closure made for `String -> Word` match it? State the rule, and say for `hashMap(K V)` calling its
   hash and equality functions which path is taken.
2. **No step compiles the compiler with itself.** Stage B runs the driver's interpreter; stage C needs the backend,
   compiled by itself, to be correct in the page. Where is that first tested, and against what?
3. **§5.7, boxed arrays first.** The compiler's side tables are `Array(Int)` and its hashes are `Word`s, often full
   width. What does a self-compilation allocate for them under this rule? If typed arrays come later, what changes
   then for locations (§5.10), for the wrapper of §5.12, and for every module compiled before?
4. **§5.3, the tuple chain** `$tupN <: … <: $tup0` and `$proxy <: $tup0` (§1, comment 4). And: a proxy is a subtype
   of `$tup0` with fields of its own, so what exactly is the static type of a tuple that may be proxied, and of one
   that may not, at a unit's boundary?
5. **§5.15, `else` as `catch_all_ref`.** What else can arrive there: a JavaScript exception thrown by a host import,
   another language's tag? Should a Quest `else` or `always` see it?
6. **§5.6, constant cases as singletons "once per module or shared through the runtime".** Options are values and
   `is` compares them. Which is it, and does `is` hold across modules either way?
7. **§5.14, lazy initialization guarded by a global.** Who calls a unit's initializer when another module imports
   its functions directly as wasm imports, not through the record?
8. **§9, the stack.** Four options are listed in order of preference. What measurement chooses among them, and at
   which step is it taken? Option 3 names a proposal: what is its state in each engine the plan tests with?
9. **§11, steps.** Each needs a condition for being done, and stage A's "then all of the IR; then the runtime" is
   most of the work in one line. What is the order inside it, and what can be tested at each point?
10. **§7, externals "about 150"; Fable counts 161.** Which is right, and which does the compiler itself use?
11. **Decision 1** records the owner's choice of the interpreter's REPL before the JIT. Fable's §11 records that the
    first milestone is the compiler compiling itself outside a browser. Are the two plans' records of the owner's
    answers consistent, and if so, where does self-compilation sit in this plan's stages?

---

## 4. Hydrogen

1. **§3.6, closures.** A closure has one function at its own signature, and adapters "work identically to C". In C
   a word and an integer agree in a register, so a function over `Int` can be called by generic code unchanged. On
   WasmGC `i64` and `anyref` do not agree. What happens when `fun(x: Int): Int` is passed where `A -> B` is
   expected, stored in an `Array(A -> A)`, or held in a `var` slot that generic code later calls? Which of C's
   rejected conversions (c-representation.md §6.4.5) become common?
2. **§3.3, the recommendation** uses typed structs "only when a tuple is monomorphic and neither its type nor any
   supertype requires proxying". Who decides that, with which information, for a tuple that crosses a unit's
   boundary or is created in a REPL input and passed to the library? What is the cost of being wrong?
3. **§3.1, always boxing `Int`.** How many allocations is that for the compiler's own `vector.T(A)`, `hashMap`, and
   tuples of integers? The note says `i31` can be added later "without changing any ABI": name the places where a
   boxed `Int` is recognized (unboxing, `is`, hashing, printing, `dynamic`) and check the claim for each.
4. **`anyref` or `eqref`.** `is` needs reference equality. What does it cost when the uniform word is `anyref`?
5. **`is` and hashing on boxed scalars.** Two boxes of 42 are different references. What do `is` at a type
   parameter and `hash.identityHash` (the default of `hashMap`) return?
6. **Identity hashing** has no design: there are no addresses. Where does a hash come from, for which shapes?
7. **§3.7, a `$QRef` per `@`.** State the allocation count for `f(@a[i])` in a loop, and compare the alternatives
   the other plans measured. "`$QCell_T` can be a subtype of `$QRef_T`": write the types and check that they
   validate.
8. **§5.3 takes tail calls from `questlang/ssa/tailCalls`,** and decision 6 lowers from the IR. Where does the
   backend learn that a call is a tail call?
9. **§2.5 and §5.4 call compiling a module asynchronous** and reach for JSPI. What does a worker permit
   synchronously? Does the plan need JSPI at all, and which engines have it?
10. **`Real`** is absent: printing and parsing that match the C runtime's bytes (the goldens are shared), and the
    mathematical functions, none of which is a wasm instruction.
11. **§5.2, a shadow frame stack "pushed and popped around non-leaf functions".** What does that cost per call, and
    what does deferring tracebacks do to the run goldens that hold them?
12. **§5.4, "bundle `lib/` interface files (`.qi` or source `.int.quest`)"** (§1, comment 9): phase 3 interprets.
13. **How the driver is divided into modules** is not said. Phase 4's inputs must link to the driver's own instances
    of the library (jit.md §3.3). What do they import, from what?
14. **Nothing was measured or run.** Phase 0 lists probes. Which of the plan's decisions would change on their
    results? Those should be stated as open until then, not as recorded decisions (§7), and §7 should say which
    decisions are the owner's.
15. **wasmtime** is listed as a tool. Which of the plan's needs can it not test (loading a module made at run
    time), and what did the other plans find about its default collector?

---

## 5. Argon

1. **§3.5, variants.** The plan says a tag is the FNV-1a hash of the label, "identical to C/arm64", and that width
   subtyping is the identity. Read c-representation.md on `tagmap_<Target>_<Source>` and on tags in "the slot's
   type's numbering", and `view->index[v.tag]` for bounded quantifiers. What is a tag, and what does an upcast do?
2. **§5.1, exceptions.** The packet holds "the FNV-1a hash of the exception's variant tag". Read
   c-representation.md on `quest_alloc_exception`: what must two evaluations of the same `exception` declaration
   give, and what must two declarations of the same name in different modules give?
3. **§2.1 and §3.2, "`ir/represent` already marks every boundary".** Today, does the represented IR contain a
   conversion where an `Int` is stored into a tuple's component or read from an array? Look at
   `layout.genericLayoutAgrees` and where the pass calls it. What must change in the pass, and what protects the
   native backends' goldens when it does?
4. **§3.6, one `$Closure` with `(ref func)` and a cast at the call.** When `fun(x: Int): Int` reaches generic code
   that calls it at `(eqref) -> eqref`, what does the cast do? Compare §4.2's row for function subtyping, which
   covers variance but not instantiation.
5. **§2.3 and §8.1, host imports for `Real` formatting, mathematics, and stack capture,** with "full parity" under
   wasmtime. What imports can the wasmtime command line supply? Does JavaScript's formatting of a number equal the
   C runtime's, to the byte, for every value the goldens print? Do the engines' `sin` and `pow` agree with Apple's
   libm in the last bit?
6. **§5.2, tracebacks from the name section.** The name section gives function names. Where do the file, line, and
   column of each frame come from? What do inlining, contification, and specialization do to the frames listed?
   What does capturing the host's stack cost at a raise that a handler then catches, and how often does the compiler
   raise and catch?
7. **§3.1, two allocations for every tuple, option, and array.** Measure it against a struct of slots, in V8 and
   wasmtime, for allocation and for reads. The location design of §3.3 is the reason given: count how many `var` and
   `out` arguments the compiler, the library, and the tests pass, and weigh the two.
8. **§3.3, "every location is a (`$ValArray`, `i32`)".** The text argues with itself ("Wait", "Let's verify
   that!") and should be rewritten as a claim with its proof. Then: is it still true if arrays of `Int` or `Real`
   are ever stored unboxed? For a `var` component reached through a proxy? For a local of record or variant type,
   which is two values?
9. **§2.2, always boxing `Int` and `Word`.** The plan does not consider `i31ref` for small integers, which three
   plans adopt or name. What does always boxing allocate in a self-compilation?
10. **Identity hashing** is assigned to a phase (`$quest_identity_hash`) with no design. Nothing in the prelude has
    a field for a hash. Where does it come from?
11. **§3.1, the prelude.** `$Option` redeclares `$Tuple`'s field; `$StringArray` and `$DescArray` are used and not
    declared; `$TypeDescriptor` and `$ViewMap` are elided. Write the group in full and validate it with
    `wasm-tools`, then run the cross-module check the plan relies on.
12. **§6.2, a linker written in Quest** to merge modules for wasmtime. What does wasmtime's `--preload` already do?
    What is the linker's size, and what does it add to what must be correct?
13. **§6.3 and §8.3, `compiler.wasm` as one module, and "the driver is the library".** An input's module imports
    the library's functions and module records from the registry. If the compiler is one linked module, what are
    those exports, and do they survive the linker?
14. **§8.4, a file system seeded with `lib/*.qi`.** Which target's `.qi`, written by which compiler? If the page
    ever interprets, what does the interpreter need (§1, comment 9)?
15. **§2.5, cross-origin isolation is assumed** for `SharedArrayBuffer`. Where will the page be hosted, and can it
    set those headers? What works without them?
16. **wasmtime's default collector.** Opus measured that it does not reclaim cycles. The plan's commands do not
    choose a collector.
17. **Nothing was measured or run,** and §8 is titled "Resolved Design Decisions". Say who resolved each, and which
    rest on a measurement not yet made.
18. **Phases have no conditions for being done** beyond "run the tests", and phase 5 holds exceptions, linking, and
    the whole library together. What is the order within it?
