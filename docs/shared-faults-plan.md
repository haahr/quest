# Plan: Faults of Shared and Native Code the WebAssembly Review Found

[wasm-review.md](wasm-review.md) §7 lists faults it met while reviewing the wasm backend that are not that
backend's: they are in the shared front end and IR, in the self-hosted compiler's SSA and the native runtime, or in
the JIT. Each was checked again on 2026-11-15, on the wasm branch rebased onto `main` (`20d7316a`), by a program of
its own run five ways: compiled by arm64, by the self-hosted interpreter (`--no-jit`), by the JIT, compiled to wasm
and run in node, and by the bootstrap's interpreter. The same probes on `main` itself (`e91686e3`, which has no
wasm backend), in the other four ways, give the same results, so each fault is `main`'s, not the wasm branch's. The
probes are not in the tree; each step's test is the probe made a golden.

| Fault (review §7) | arm64 | interpreter | JIT | wasm | bootstrap | Step |
|---|---|---|---|---|---|---|
| A bounded quantifier in an interface | fails to import | runs | fails | fails | fails | 1 |
| An abstract type bounded by a tuple | `arrayOp.error` in `ir/slots` | runs | `unsupportedConversion`, uncaught | `arrayOp.error` | runs | 2, 7 |
| A `var` record parameter raised as a payload | `arrayOp.error` in `ssa/build` | runs | the same | runs | runs | 3 |
| `is` between records of known type | refused by the SSA | runs | refused | runs | runs | 4 |
| An option's proxy's identity hash | differs from its original's | agrees | differs | agrees | agrees | 5 |
| A document's record with a field given twice | `dynamic.error` | read | `dynamic.error` | `dynamic.error` | read | 6 |
| A rejected conversion under the JIT | | | uncaught, with the compiler's traceback | | | 7 |

**Not reproduced** by the probes written for them, and so not planned until a program shows them: an `out`
argument that needs a conversion and that the callee does not assign (the review: a segmentation fault natively),
and subsumption of an auto value with a covariant record component (every mode gives the right answer); and the
JIT's "a use of variable qj_1_record (423), which nothing binds", whose probe the review does not give. The native
fatal error on a field given twice is gone: compiled code now raises `dynamic.error`, so step 6 is now a
disagreement between the targets.

## Steps

1. **A bounded quantifier in an interface.** `getA(A <: Small x: A): Int` in an `.int.quest` is written into the
   interface's artifacts as `All(A::<: Small x: A) Int`, which the type reader cannot parse, so no importer can see
   it: bounded generic code cannot live in another unit. The self-hosted interpreter, which reads the interface's
   source, runs it. Fix the type's printing (the bound as `A <: Small`) in both compilers, whose artifacts must
   agree, and check that the importer's code then calls it at the right view on every backend: the wasm backend's
   view maps (wasm-plan.md §8.5 step 25) are the first to meet a bounded parameter from another unit.
   *Done when* a module test with a bounded function in an interface passes in every phase and mode.
2. **An abstract type bounded by a tuple or an option.** `P::POWER(Tuple a: Int end)` with `P` a wider tuple in
   its module fails in shared code: `ir/slots.operation` raises `arrayOp.error`, and `ir/represent.viewPlan`, under
   the JIT, finds no conversion from the representation to the bound. A record bound works (`modules/
   bounded_abstract_types`). Give the IR a plan for a tuple's or option's component read through such a bound, as
   it has for a record's view.
   *Done when* a module test reads a component through each kind of bound, in every mode.
3. **A `var` record parameter raised as an exception's payload,** in the self-hosted compiler's SSA alone:
   `ssa/build/aggregates.recordField` indexes the record's parts as if it were held unboxed. Fix the builder to
   take the boxed location's value, as the C printer and the wasm backend do.
   *Done when* a run golden raises one and catches it, and passes on arm64 and the JIT.
4. **`is` between records in code of known type,** refused by the SSA ("is of a value of QRecordVal"), so arm64
   and the JIT do not compile what the C backend, the wasm backend, and the interpreters run. Give the SSA the
   comparison the C printer makes (the records' payloads by identity).
   *Done when* a run golden compares records with `is` and `isnot`, and passes on every backend.
5. **An option's proxy's identity hash** differs from its original's natively while `is` holds: the C runtime's
   `quest_option_identity_hash` hashes the proxy, not what it proxies, so an identity map can lose an entry. Unproxy
   before hashing, as `is` does.
   *Done when* a run golden puts a value in an identity map through one view and finds it through another.
6. **A document's record with a field given twice:** compiled code raises `dynamic.error` (C's reader), and both
   interpreters read the document, taking one of the two. The interpreters' `dynamic` raises `dynamic.error` as
   C's does, so that every target refuses it.
   *Done when* an error test of the document passes in every mode.
7. **A conversion the represent pass rejects, under the JIT,** ends the input with an uncaught `rejectedConversion`
   or `unsupportedConversion` and the compiler's own traceback, where a compiled program reports it as a compiler
   error. The JIT's session catches both, as it catches the SSA's and the loader's failures, and reports them as
   "the JIT cannot compile this input".
   *Done when* step 2's program, before step 2's fix, gives that message under the JIT (a check in the JIT's tests).

## Order

Steps 1 and 2 first: they keep whole kinds of program from compiling on every compiled target, and step 1 keeps
bounded generic code out of libraries. Then 3 to 5, which are each one function. Step 6 is a rule to match, and 7
the JIT's report. The steps are independent; each lands with its test, in a shared phase where it can, so that
both compilers' suites hold it (testing.md §2.8).
