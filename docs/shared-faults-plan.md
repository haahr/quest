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

**What reading the code found (2026-11-15).** Each fault was traced to its code and, for steps 2 to 4, the fix
below was tried in a scratch copy of the tree, where every probe then gave the interpreter's output under arm64, the
JIT, `--backend c` and `ssac`. Four of the faults are wider than the table shows:

- Step 2's tuple bound is two faults, and the bootstrap's C path (`--stop-after run_c_compiled`) has both; it "runs"
  only in the bootstrap's interpreter. An option bound already works everywhere.
- Step 3 has nothing to do with `var`: any record or variant payload caught with a binder fails on every native
  target in both compilers, both C printers included (clang rejects their output).
- Step 4's C output does not compile either (`==` on two `QRecordVal` structs), in both compilers; only the
  interpreters run it.
- Step 6 is three disagreements, not one, and none of the three readers checks for a repeated key.

Steps 4 and 5 share a cause in the runtime: generic code compares and hashes a record by its box's address, and
every view of a record makes a new box.

## Steps

Each step says where the fault is, the fix, and its test. Fixes to shared code are made in both compilers
(two-compilers policy); a step that changes a header's inline code or the interface format bumps the ABI
(`questlang/config/abi.mod.quest` and `bootstrap/python/quest/config/abi.py`, now 76), so that cached artifacts and
the stages are rebuilt.

1. **A bounded quantifier in an interface.**
   *Where.* The `typeAll` branch of the interface printer writes each quantifier as its name, `::`, and the kind's
   display text, and a `POWER` kind displays as `<: B`, so `A <: Small` becomes `A::<: Small`: self-hosted,
   `formatType` in `questlang/modules/artifacts/interfacecompiler.mod.quest` (line 182, `model.showKind`);
   bootstrap, `bootstrap/python/quest/modules/artifacts/interface_compiler.py` line 229 (`f"{q.name}::{q.bound}"`).
   Every other kind in these printers already goes through the interface's own kind printer. The display text is
   wrong a second way too: it prints the bound with `model.show`, which writes a function type as `Fun(...): R`
   where the reader expects `All(...) R`.
   *Fix.* Print the bound with the interface's kind printer: `formatKindForQi(bound)` and `format_kind_for_qi`,
   giving `All(A::POWER(Small) x: A) Int`, which both readers already parse. Bump the ABI (77). The two compilers'
   interface files need not agree byte for byte (each reads only its own), but their printers mirror each other
   and should keep doing so.
   *Checked.* With the interface file corrected by hand, the importer printed the right answer under arm64, c,
   ssac, `--whole-program` and the JIT, and the bootstrap (patched in memory) under interpret, `run_ir_core`,
   `run_ir_described` and `run_c_compiled`. The wasm backend's view maps were not tried (they are not on `main`).
   *Test.* A module test beside `tests/source/modules/bounded_abstract_types.quest`, say
   `bounded_generic_import.quest` with `geom/bounded.int.quest` and `.mod.quest`: `getA(A <: Small x: A): Int`
   called with a wider record, the bound's own record, and a value ascribed to the bound; a bound with a field of
   function type (which catches `show`); and a higher-kinded quantifier. Goldens for every phase.
2. **An abstract type bounded by a tuple.** Two faults, by whether the module's representation is the bound or a
   wider tuple. Both come from code that takes an abstract type's shape where it needs the shape it is held at.
   *Where, the same tuple.* The module compiles, and the importer's `p.a` raises `arrayOp.error` in
   `questlang/ir/slots.mod.quest` `operation` (line 253, the `opTupleField` arm): `shapes.shape(typeOf(x.tup))` is
   the abstract shape, which has no components. Lowering resolves it (`lower.tupleIndex` uses
   `layout.resolvedShape`); slots' `opAddrComponent` (line 432) and `sStoreComponent` (around line 559), the C
   printer (lines 2005, 2061, 2256) and `ssa/build/control.mod.quest` (lines 125, 487) do not. The bootstrap's
   `ir/slots.py` line 309 is the same.
   *Where, a wider tuple.* The module itself fails, under arm64 as well as the JIT, with `unsupportedConversion`
   from `represent.viewPlan`: its tuple branch (`questlang/ir/represent.mod.quest` line 564) tests the shapes `ss`
   and `ts` themselves, where the record, variant and option branches test `sHeld` and `tHeld`
   (`layout.resolvedShape`). Bootstrap: `ir/represent.py` line 398.
   *Fix.* In `viewPlan`, before the tuple branch, a branch for the module's abstract value going back to its own
   wider representation (both held shapes tuples, the source held at its bound and the target not, the source
   with fewer components): `planUnproxy` if `layout.mayBeProxied(sHeld)`, else `planCast`. Then make the tuple
   branch test and use `sHeld` and `tHeld`, so that wider-to-bound is a cast, or a `planView` (a proxy) when a
   component changes view. In `unproxied` (represent line 370), resolve both shapes. Wrap the shapes listed above
   in `layout.resolvedShape`, which is the identity for anything not abstract and not a bounded type variable. The
   same changes in the bootstrap's `ir/represent.py`, `ir/slots.py` and `codegen/c/printer.py`.
   *Checked* in the self-hosted copy: a bound the same as the representation, a wider one, and one whose record
   component changes view and that has a `var` component (read, stored through, and passed back to the module,
   which takes the proxy path). The bootstrap's half was not tried.
   *Test.* Extend `modules/bounded_abstract_types` (and `geom/small`) with those three tuple bounds and an option
   bound with a wider payload, read, stored and passed back; regenerate its goldens in every phase.
   *Watch.* `resolvedShape` also resolves type variables held at their bound, so the full suite matters; the
   whole-program and transparent-abstract paths (`transparentAbstractTypes`) skip planning and need a whole-program
   run of the test.
3. **A record or variant caught as an exception's payload.** Two causes.
   *Where, the IR (both compilers).* Slots decides whether a handler's binder is boxed from
   `exceptionPayload(typeOf(x.exc))` (`questlang/ir/slots.mod.quest` line 380; `bootstrap/python/quest/ir/slots.py`
   lines 389–390), but `x.exc` is the handler's own variable, of type `Exception`, so the answer is always "not
   boxed" and no `slot_unbox` is inserted; each printer then reads the box into an unboxed variable.
   *Where, the SSA (self-hosted).* The raise (`questlang/ssa/build/control.mod.quest` line 565) passes the payload,
   already a box after slots, through `vals.toWord`, which boxes it again (`quest_record_box` with one argument).
   *Fix.* Decide from the bound variable's type: `maybe.isSome(:Variable v) andif boxed(...shape of v's type...)`,
   and in the bootstrap `var is not None and _boxed(shape(var.type))`. In the raise, use
   `representation.slotToWord`, as the C printer's `shapeSlotToQval` does (`printer.mod.quest` line 2383).
   *Test.* A shared run golden, `tests/source/language/exception_record_payloads.quest`: a record and a variant
   raised from a `var` parameter and caught, a `var` argument taken from a tuple's slot (`f(@t.r)`), and a payload
   returned from its handler. The slots change alters the IR goldens (`ir_represented`, `ir_described`) of any
   handler with a record or variant binder, in both compilers; regenerate them.
4. **`is` between records of known type.**
   *Where.* The SSA refuses a value of more than one part (`questlang/ssa/build/calls.mod.quest` lines 73–78), and a
   record has two (`val`, `dict`). Both C printers (`codegen/c/printer.mod.quest` lines 1624–1660,
   `bootstrap/python/quest/codegen/c/printer.py` lines 1276–1295) emit `==` on the two structs, which clang rejects.
   *Fix.* Compare the payload pointers, `.val`: a view of a record changes only its `dict` (`quest_record_view`),
   and records have no proxies. In the SSA, a branch before the refusal for a `QRecordVal` that compares the first
   parts with `ssa.opPeq` (`isnot` is the existing xor); in both C printers, `(l).val == (r).val` when the type is
   known and its C type is `QRecordVal`, guarded for a type that is none (handler variables clear it). arm64 and
   the JIT both build through the SSA, so one fix covers both.
   *Test.* A shared run golden, `tests/source/language/record_identity.quest`: `is` and `isnot` on one record, on
   equal but distinct records, through a supertype's view, and in a generic `same(A::TYPE x: A y: A)` that is not
   inlined (which needs step 5).
   *Variants* are refused the same way; step 8 gives them their rule first.
5. **A record's identity in generic code, an option's proxy's identity hash among them.**
   *Where.* Not the option code: `quest_option_identity_hash` (`runtime/quest_views.c` line 574) unproxies. The
   option's component is a record, and reading it through a proxy (`quest_proxy_option_element` →
   `quest_proxy_cached` → `quest_convert`) views the record into a new box with `quest_record_box`, cached in each
   proxy separately. `quest_identity_hash` (`runtime/quest_stdlib.c` line 549) hashes a record's word, the box's
   address, and `quest_val_is` (`runtime/quest_runtime.h` line 899) compares it, so two views of one record differ
   in both, with no option involved (`identityHash` of `r` and of `r` viewed as `Small` differ natively). The JIT
   calls the same functions (`hash.identityHash` is `external "quest_identity_hash"`; generic `is` is
   `quest_val_is`).
   *Fix.* A `QTYPE_KIND_RECORD` case in both: hash and compare `((const QRecordVal *)x.p)->val`, the payload, as
   step 4's code of known type and the interpreters do. Both are needed: with the hash alone, an identity map finds
   the bucket and then fails the equality. `quest_val_is` is inline in the header, so bump the ABI.
   *Test.* Extend `tests/source/language/option_identity.quest` (which the JIT's files also run): an option whose
   component is a record, viewed twice at a narrower type, put into `hashMap.newIdentityMap` through one view and
   found through the other, with the two hashes equal; and the same for a bare record and its view.
   *Watch.* Variants are reboxed the same way (`quest_variant_box`) and auto values copied (`quest_convert_auto`);
   see whether generic `is` reaches them, and if so give them the same case or note why not.
6. **A document whose record has a key twice.** What each target does today:

   | The document | arm64 and the JIT | both interpreters |
   |---|---|---|
   | its value repeats a key the type has once | `dynamic.error` | read, the last value |
   | its type repeats a field the value has once | `dynamic.error` | read |
   | both repeat it | read, the **first** value | read, the **last** value |

   C refuses the first two only because the number of keys stops matching (`runtime/quest_serialization.c` around
   line 2009); its parser (`quest_parse_json_object`, line 1322) keeps every entry, and `quest_json_obj_get` takes
   the first. The self-hosted reader parses with `questlang/common/json`, whose `put` (lines 43–48) keeps the last
   value (documented in its interface) and is called from `questlang/values/dynamicreader.mod.quest` line 765; the
   bootstrap's `dynamic_reader.py` line 509 parses with `json.loads` into a dict.
   *Fix.* One rule in all three readers: an object with a repeated key is `dynamic.error`. In C, compare each new
   key with the earlier ones in `quest_parse_json_object`. Self-hosted, a strict parse in `common/json` (a function
   or a flag that raises `json.error` when `put` finds the name already there), used at dynamicreader line 765,
   which already turns `json.error` into `fail`; the kernel, manifests and ABI code keep the lenient parse.
   Bootstrap, an `object_pairs_hook` that raises on a repeated key, with its `ValueError` caught where `json.loads`
   is. Add the rule to docs/dynamic.md §2.2 and §2.4.
   *Test.* An error test, `tests/errors/run/dynamic_repeated_field.quest` (`dynamic_error.quest` is the model),
   whose standard input is the document that repeats the key in both type and value, the one every target reads
   today; check first that error tests take `@stdin`. Error tests do not run under the JIT, so also a run golden,
   `tests/source/stdlib/dynamic_repeated_keys.quest`, that reads all three documents, one per line, and catches
   each with `when dynamic.error`.
7. **A conversion the represent pass rejects is a compile-time error,** with the program's location, in both
   compilers and every driver (decided 2026-11-15). A conversion that would copy mutable data laid out two ways
   (`rejectedConversion`) is the program's fault, not the compiler's. A rejected conversion found later to be one
   that should compile is fixed where that conversion is planned, not by relaxing this rule.
   *Where.* Two raises in `questlang/ir/represent.mod.quest`: `layoutPlan` (line 224, a value passed to or from a
   polymorphic function that lays it out generically) and `abstractPlan` (line 490, a value of a module's abstract
   type operator between the module's layout and its own); the bootstrap's `RejectedConversion`
   (`bootstrap/python/quest/ir/represent.py` lines 159, 184, 442). Today they are reported without a location:
   `driver/main.quest` `reportingInternal` (line 337) reports one as an internal error, and the bootstrap's pipeline
   turns any exception into a diagnostic at offset 0 (`pipeline.py` line 475 and the like). Under the JIT
   (`compileAndLoad` in `questlang/jit/session.mod.quest`, lines 410–417) and in a module's build
   (`modulecompiler.compileModule`, `questlang/modules/artifacts/modulecompiler.mod.quest` lines 227–230, which
   catches only `cBackend.unsupported`, while `backend.moduleFileToC` runs the passes outside its `try`), one escapes
   with the compiler's traceback.
   *Fix.*
   - **A location.** The represent pass keeps no source position. Give it the offset of the operation whose
     conversion it is planning (the `offset` that calls, stores and the like carry for run-time errors), passed
     down to `layoutPlan` and `abstractPlan`, and make `rejectedConversion` carry it with the message. Where the
     operation carries no offset (`opConvert` has none), add one in lowering, or fall back to the enclosing
     function's. Check first which operations reach the two raises.
   - **A diagnostic.** Self-hosted, a handler beside `reportingInternal` that reports `rejectedConversion` as
     `diagnostics.error` at that position (`nodes.sourcePos`), not as an internal error; the same in the module
     compiler, for a module's own source; and in the JIT's session, as the program's error, so that the REPL prints
     it as it prints a type error and goes on. Bootstrap, the same: `RejectedConversion` with its offset, caught in
     the pipeline as a located diagnostic.
   - **The rest stay internal.** `unsupportedConversion`, `describe.unsupportedDescriptor` and
     `closure.capturesMutable` are the compiler's failures: catch them in the JIT's session (as "the JIT cannot
     compile this input") and in the module compiler (as internal errors), the set `reportingInternal` catches.
   *Test.*
   - A new phase of error tests, `tests/errors/represent/` (docs/testing.md §3), whose expectations are compile
     errors after type checking, run by both drivers with the C backend and arm64. The cells of the conversion
     matrix's `REJECTED` (`tests/conversions/generate.py`), now checked by
     `tests/python/test_conversion_rejections.py`, become error tests there, written by the generator, and that unit
     test goes.
   - An error test, in its own directory of modules, for the abstract type operator that `abstractPlan` rejects,
     which step 2 does not fix:

     ```
     interface Ar export T::ALL(A::TYPE) TYPE  bools: T(Bool)  first(A::TYPE t: T(A)): A end
     module ar : Ar export Let T = Fun(A::TYPE) Array(All(u: Int) A)
         let bools: T(Bool) = array of fun(u: Int): Bool true end
         let first(A::TYPE t: T(A)): A = t[0](0) end
     ```

     imported by `ar.first(:Bool ar.bools)`.
   - A check in `tests/self-hosted/jit_hosts.py` (shaped like `check_own_modules`) that the JIT reports that
     program's error at its location and goes on, with no line of the compiler's traceback.
   - The interpreters run these programs and will go on running them: the error is compiled code's, and an error
     test's expectations apply to the compiled phases only.
8. **`is` between variants** (decided 2026-11-15): the rule options have (docs/extensions.md, Options as Values),
   applied to variants. *Typeful Programming* §3.1 gives every type but the scalars "same memory location", and
   §6.3 makes variants like options; this implementation already compares options by case and component, and a
   compiled variant has no location of its own to compare.
   *The rule.* Two variants are `is` each other, at the variant type `is` is applied at, when they are of the same
   case and their values are `is` each other at that case's type; a case of type `Ok` is its case. A variant's case
   carries exactly one value, so every variant is what a single-word option is. `{variant p of V with 1 end} is
   {variant p of V with 1 end}` is true, which the interpreters now say is false.
   *The layout, checked.* A variant is two words, `QVariantVal` (`runtime/quest_runtime.h` line 150): its tag, in
   its type's numbering, and one payload word, the case's value in its slot form (an `Int` itself, a string's
   pointer, a record's or variant's box, a tuple's or option's pointer or proxy; docs/c-representation.md §5.3).
   In a slot or in generic code it is boxed (`quest_variant_box`). An upcast remaps the tag and keeps the payload
   word, unless the case's type changes, when `quest_variant_adapt` (`runtime/quest_views.c` line 1475) converts it
   with `quest_convert`: a record then gets a new box, a variant a new box, and a tuple or option a proxy. So
   comparing the tags and the payload words fails exactly where step 5's record case is needed, and the payload is
   compared at the case's type, as `is` at that type compares it, not as bits.
   *Fix.*
   - **The SSA and both C printers** (where step 4 refuses and miscompiles records, `calls.mod.quest` lines
     73–78, `printer.mod.quest` lines 1624–1660, `printer.py` lines 1276–1295): for a variant of known type, the
     tags equal and the payloads `is` at the case's type, by a runtime call, `quest_variant_is(descriptor, a, b)`,
     taking the two `QVariantVal`s; code of known case may compare inline later if it pays.
   - **The runtime.** `quest_variant_is`, and a `QTYPE_KIND_VARIANT` case in `quest_val_is` (unbox both, then the
     same) and in `quest_identity_hash` (the tag's case name and the payload's identity hash at the case's type, as
     `quest_option_identity_hash` does, so that two views of one variant at a type hash alike). `quest_val_is` is
     inline in the header: bump the ABI, with step 5's bump if they land together.
   - **The interpreters.** The self-hosted interpreter's `primitives.sameAt` (which knows the static type and
     already compares options by case) and the bootstrap's `qvalue_is` (`bootstrap/python/quest/values/model.py`
     line 810) and identity hash (`interpreter/builtins.py` around line 885): a variant compared and hashed by case
     and value at the case's type. `values/model.same`, which knows no type, keeps identity, as it does for options.
   - **The language's description.** A paragraph for variants in docs/extensions.md beside Options as Values, and
     docs/runtime-design.md §3's list (which says variants are compared by location).
   *Test.* A shared run golden, `tests/source/language/variant_identity.quest`: two variants made apart with the
   same case and an `Int`, a string, a record, and `Ok`; different cases; one variant and its upcast (tags
   renumbered), and an upcast that converts its record value; `is` in a generic function that is not inlined; and
   an identity map keyed by variants, found through another view. Then step 4's record-identity golden gains its
   variant cases.
   *Tied to options.* docs/option-values.md says that if its deferred design is dropped, options' single-word rule
   goes back to identity. Variants follow options: if that happens, this rule goes too, and compiled variants need a
   location (a box) or `is` on them is refused.

## Order

Step 7 first: it makes the represent pass's rejections the program's errors, and the rest of its failures reports
rather than tracebacks, while the other steps land. Then steps 1 and 2, which keep whole kinds of program from
compiling on every compiled target (step 1 keeps bounded generic code out of libraries); 2 is the largest. Then 3;
5, then 8, then 4 (step 8 needs step 5's record case for a variant's record value, and step 4's golden takes step
8's variants); and 6. Steps 1, 5 and 8 each bump the ABI; if they land together, one bump will do. Each step lands
with its test, in a shared phase where it can, so that both compilers' suites hold it (testing.md §2.8).
