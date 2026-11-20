# Five Task-List Fixes

A plan for five entries of [tasklist.md](tasklist.md), and a follow-up to the first, taken in this order, each a step
of its own:

1. Assigning through `opt!tag` compiles and changes nothing. **Done:** the direct form is refused; the nested form
   changes the option, so it stays. Step 2 replaces the refusal.
2. Assigning through `opt!tag` changes the option: `o!made.x := v` and `@o!made.x` reach the option's own component.
   **Done.**
3. Undo the single-word rule for options, and simplify what it left.
4. A dynamic reader cannot read on after a document it refused.
5. A missing interface in an imported module's import is located at the module's first line.
6. Character I/O locks the stream for every character. **Done:** the unlocked calls, measured in
   [benchmarks.md](benchmarks.md) §31.

Each step ends the same way (§7): its tests, then `tools/check` on a quiet machine, then a commit, a rebase onto
`origin/main`, and a push. Its entry leaves tasklist.md in the same commit.

---

## 1. Assigning Through `opt!tag`

**Now.** `opt!tag` is a new tuple ([type-system.md](type-system.md) §6.8), so `o!made.x := 2` assigns a component of
a copy that is discarded once the statement ends. Both typecheckers accept it.

**Change.** Reject an assignment whose target is a selection (`exprSelect`) whose base is itself an option extraction
(`exprVariantAssert` in the self-hosted AST, `ExprVariantAssert` in the bootstrap's), of an option type. Make the
check after the target is known to be a tuple's `var` component, so a field that does not exist or is immutable keeps
its own error. Only the direct form is rejected: `let t = o!made` then `t.x := 2` changes `t`, as it should.

- `questlang/typechecker/control.mod.quest`, the `exprSelect` arm of the assignment (target 2, beside "Cannot assign
  to immutable tuple field").
- `bootstrap/python/quest/typechecker/control.py`, the matching `ExprSelect` case.

The message, in both: `Cannot assign to a component of 'o!made', which is a copy: use a case binder (when made with
c then c.x := ...)`, located at the selection, as the immutable field's error is. It names the option expression as
written when that is a variable, and `opt!tag` otherwise.

Variant extraction (`v!tag`) is not affected: it gives the payload itself, not a copy.

**A nested selection** (`o!made.inner.x := 2`, `inner` a tuple component): check first what it does in every
evaluator. If it changes nothing, as the direct form does, reject it too, by looking through selections to the first
base that is not a selection. If it changes the option, accept it and record why in type-system.md §6.8.

**Tests.**

- `tests/errors/typecheck/aggregates/option_extraction_assign.quest`, the task's reproduction, with its `.error`
  golden, run by both compilers (the shared error suite).
- If the nested form is rejected, a second error test for it. If it is accepted, a golden test showing its effect.
- type-system.md §6.8 gains a sentence: assigning through an extraction is refused, and a case binder is the way
  to change a payload.

---

## 2. Assigning Through `opt!tag` Changes the Option

**Why.** Programmers expect `o!made.x := v` to change `o`, as it did in iter-plan.md's decision 4, where it printed
`0`. Typeful Programming (§4.5) never assigns through `!`, but everything nearby points the same way:

- An option is a tag and a binding, and a case's binder is bound to that binding, the option's contents.
- The paper calls `!` "coercing to a given label".
- An option type whose common components come first in a `with` clause is equivalent to one that repeats them in each
  case, and the paper says the two differ only in whether selecting a component needs `!` first.
- `var` components keep their `Var` type through `!`, and both typecheckers already type the assignment as a store
  to a `Var` component. Only the copy makes it change nothing.

**The rule** (type-system.md §6.8). A selection through an extraction, `o!tag.f` used as a location (the target of
`:=`, or an `@` argument), is the option's own component `f`. It means the same as:

```
case o when tag with c then c.f := v else (o!tag raises) end
```

So `o` is evaluated first, then its case is checked, raising as `o!tag` does (the same exception, at the same
location). Then `v` is evaluated, and it is stored. This is the order today's lowering already uses: the target's
base, then the value.

**What stays a copy.** `opt!tag` as a value is still a new tuple: its first component is the ordinal, which depends on
the static type of `o`, so it cannot be the option itself. `let t = o!made` then `t.x := v` changes `t` alone, as
today, and so does passing `o!made` to a function that assigns its components. Reading `o!made.x` is unchanged: the
copy's component and the option's are equal. The nested forms (`o!made.inner.y := v`, `o!made.a[i] := v`) already
change the option through the shared component, and stay as they are. Variants are not affected: `v!p` is already
their payload.

**Change.**

1. **The typecheckers.** Remove step 1's refusal: `refuseExtractionTarget` in `questlang/typechecker/control.mod.quest`
   and `_refuse_extraction_target` in `bootstrap/python/quest/typechecker/control.py`, with their calls. The
   assignment and the `@` argument (`application.mod.quest`'s `exprTupleSelectRef`, and the bootstrap's
   `TypedTupleSelectRef`) already typecheck. Nothing else changes in the typed AST.
2. **The lowering, in both compilers** (`assign` and the `exprTupleSelectRef` arm of `value` in
   `questlang/ir/lower.mod.quest`; `assign` and `TypedTupleSelectRef` in `bootstrap/python/quest/ir/lower.py`). When
   the selection's base is an option extraction (`exprVariantAssert` of an option type, a bounded type parameter's
   included, decided as step 1's check decides it), lower it as the rule's `case` rather than through `opPayload`:
   - an `sSwitch` on `o` with one case, `tag`, whose binder is a fresh variable of the case's payload type (the
     extraction's tuple type without its first, ordinal component);
   - in that case, `v`'s lowering, then `sStoreComponent` into the binder, at the component's index in the payload
     type, which is one less than its index in the extraction's type;
   - for `@o!tag.f`, the case instead produces `opAddrComponent` of the binder, and the switch's value joins as
     `exprCase`'s does (`branchValue`);
   - the else body is `o!tag` itself, an `opPayload` that always raises there. `opPayload` is not pure (simplify's
     list), so no pass removes it. If a reviewer finds this indirect, the alternative is a raise statement carrying
     the extraction's offset, which every backend would then need.

   Every backend already makes a case binder the option's own payload: the C printer's switch, the SSA builder
   (`quest_view_option_payload` through a bounded type parameter's view map, `optionCasePayload` otherwise), the
   proxies' `quest_proxy_option_payload`, the write barrier's rule for a store into a binder, the wasm codegen, and the
   IR interpreter. So C, arm64, the JIT, ssac, wasm, and `irinterp` need no change, and none is planned. Read the
   wasm codegen's and the C printer's switch with a binder to confirm it.
3. **The interpreters** evaluate the typed AST, so they change on their own (`questlang/interpreter/treewalk.mod.quest`
   and `bootstrap/python/quest/interpreter/treewalk.py`): the assignment, and the `@` argument, whose base is an
   option extraction, evaluate the option, raise `variantError` at the extraction's offset if it is another case,
   evaluate `v`, and store into the option's own binding, the one a case's binder is defined to.
4. **The C printer's "Payloads Not Made"** reads `opt!tag.field` from the option without making the tuple. It is a
   read, so it is unaffected. Check that it never fires on the new switch.

**Tests.**

- `tests/errors/typecheck/aggregates/option_extraction_assign.quest` and its `.error` are deleted.
- `language/option_extraction_copies` is rewritten and renamed `language/option_extraction_assign`, covering:
  - the direct assignment, seen by a later case and by `o!made.x`;
  - `@o!made.x` passed to an `out` and a `var` parameter;
  - the wrong case, raising the extraction's error, with `v` not evaluated (it prints if it is);
  - a bounded type parameter's option (`A <: Option made with var x: Int end end`);
  - an option reached through an upcast (a proxy, c-representation.md §5.8);
  - a heap value stored into the option this way, read after allocating enough to collect (`--stress` in
    `tools/check` covers the barrier);
  - and, unchanged, the copy through a variable, the nested component, the case binder, and the variant.
- Its goldens in every mode: run, the self-hosted IR and SSA, and wasm's `.wat` if it has one.
- `language/option_payload_sharing` keeps passing unchanged.

**Documents.**

- type-system.md §6.8: "Assigning Through an Extraction" states the rule above. "Payload Sharing" says that a
  selection through `opt!tag` used as a location is the option's own, like a binder.
- c-representation.md §5.3, "Case Binders Share the Payload": a selection through an extraction used as a location is
  lowered as a case binder.
- ir.md, the operations table's row for `payload`: a selection through an extraction used as a location lowers to a
  switch, not to `opPayload`.
- iter-plan.md's decision 4: the sentence that now says `s.slot!made.x := x` is refused says it changes the slot.

---

## 3. Undoing the Single-Word Rule for Options

**Now.** Two options of a single-word type are `is` each other when their components are ([extensions.md](
extensions.md), "Options as Values"). The nullable-pointer representation that the rule was meant for was dropped on
2026-11-19 ([option-values.md](option-values.md)).

**Keep.** A case without components is compared by its case, and its options are shared constants. Variants keep
comparing by case and value, as decided on 2026-11-19 ("Variants as Values"). Abstract types compare as their
representations do.

**Change.** A single-word option with its component is compared by identity, as every other option with components
is, and hashed by its address.

1. **The rule's type.** `reduce.OptionIdentity` (`questlang/types/reduce`, the bootstrap's `types/reduce.py`) loses
   `single` and `component`. It becomes the set of cases without components. `optionIdentity` stops looking for the
   single case.
2. **The interpreters.** `is` and `hash.identityHash` lose their single-word branch: `questlang/interpreter/builtins`
   and `primitives`, the bootstrap's `interpreter/builtins.py` and `values/model.py`.
3. **Describe.** Describe calls the runtime for an option's `is` only when the type has a case without components:
   `questlang/ir/describe`, the bootstrap's `ir/describe.py`. Any other option type compares by pointer, inline.
   Read the C printers' and the SSA builder's uses (`printer.mod.quest`, `printer.py`, `ssa/build/calls`) to confirm
   that they follow describe's choice and need no change of their own.
4. **The runtimes.**
   - `runtime/quest_views.c`: `quest_single_word_case` goes. `quest_option_is` is unproxied pointer equality, or the
     same tag for a case without components. `quest_option_identity_hash` hashes the case for a case without
     components, and the address otherwise.
   - `runtime/quest_runtime.h`: the comments describing the rule.
   - `runtime/wasm/core`: `singleWordCase` goes, and `valIs` and the identity hash change to match.
5. **The wasm backend.** `questlang/wasm/codegen`'s `optionIs` loses its `singleWord` case.
6. **Code that relied on the rule.** Search `lib/`, `questlang/`, `tests/`, and `benchmarks/` for `is`, `isnot`,
   and identity maps applied to options of a single-word type, `maybe.T` above all, and rewrite each one to compare
   components. The suites find the rest.
7. **The ABI.** `quest_runtime.h` changes, so `ABI_VERSION` is bumped to the next version, in
   `bootstrap/python/quest/config/abi.py` and `questlang/config/abi.mod.quest`. The two corpora are regenerated
   (`tests/abi/corpus.py --update`, and `--update --compiler` with stage 2).
8. **Tests.**
   - `language/option_identity`: sections 5 and 6 change from "compare by component" to "distinct objects", and the
     hashing section changes with them.
   - `language/dynamic_runtime_ports`: its single-word hash case.
   - Re-record the goldens that change in every mode: the run goldens, the self-hosted IR and SSA goldens, and the
     wasm `.wat` goldens.
9. **Documents.**
   - extensions.md: the single-word bullet and the closing paragraph of "Options as Values" go. "Variants as Values"
     gives its own reason alone: a compiled variant is two words, with no location to compare.
   - c-representation.md §5.3, runtime-design.md's identity bullets, wasm.md's hashing line, and README.md's link
     change to match.
   - option-values.md is deleted.

---

## 4. Reading On After a Refused Document

**Now.** `dynamic.intern` refuses a document when an object in it repeats a key (dynamic.md §2.1), or when the
document does not decode. On some readers, every later read from the same reader fails too. The C runtime raises in
the middle of parsing (`quest_parse_json_object`), so the rest of the document is left unread and the next read
starts inside it. The bootstrap first reads a document's whole text, counting brackets outside strings, and only
then decodes it, so it may already behave correctly.

**First, reproduce on every target.** Feed three documents on standard input, one per line, the second one repeating
a key. Do the same with a second document that is well-formed but does not decode (a wrong `quest` version). Run each
input under every target:

- compiled, arm64 and C;
- the JIT;
- both interpreters;
- wasm: wasmtime, node, and the page's REPL.

Note which targets fail.

**The rule,** written into dynamic.md §2.1 and §3.2: a read takes the whole document, which is the JSON value that
starts at the first character after whitespace and ends where its brackets balance (counted outside strings, with
`\"` not ending a string). It then refuses the document or decodes it. A refusal leaves the reader just after the
document, so the next read starts at the next document. Text that is not JSON at all leaves the reader wherever the
scan stopped: at the end of the input, or after the character that broke the scan.

**Change,** in each reader that fails:

- **The C runtime** (`runtime/quest_serialization.c`): note a repeated key and keep parsing, raising only once the
  whole value has been read. Do the same for the other refusals that happen mid-parse, so the parse always reaches the
  value's end before `quest_raise_dynamic_error`. The checks after the parse (version, members, decoding) already run
  once the document has been consumed.
- **The wasm runtime** (`runtime/wasm/dynamic`), the same way.
- **The self-hosted interpreter** (`dynamicIntern` in `questlang/interpreter/builtins`, through `util/json`'s
  `json.read` with `parsingDynamic`). If `util/json` refuses a repeated key mid-parse, defer that refusal in its
  dynamic mode, or have `dynamicIntern` take the document's text first, by the same bracket count, and then parse it.
- **The bootstrap** (`_dynamic_intern`): only if it fails.

**Tests.**

- `tests/source/stdlib/dynamic_repeated_keys.quest` reads its documents from standard input (a test's `@stdin`), with
  a refused document between two good ones, and reads on after each refusal.
- The same test runs in every mode, so the shared golden covers every target.

---

## 5. Locating a Missing Interface at Its Import

**Now.** A module that a program imports may itself import an interface that cannot be found. A `-o` build with
either compiler, and the JIT's run, report the error at the module's `1:1`. A run with `--no-jit` and the
bootstrap's run report it at the import. The reason: step 2 of the module compiler loads each import's interface
outside `atImport`, so the error keeps offset 0.

**Change.** Wrap each import's interface load in the import's location, in both compilers:

- `questlang/modules/artifacts/modulecompiler.mod.quest`, `elaborate`, step 2: `elaboration.loadInterface(ifacePath
  e)` inside `env.atImport(e imp.offset 1 fun(): ...)`. Step 1, the interface the module implements, is left alone:
  its error has no import to point at.
- `bootstrap/python/quest/modules/artifacts/module_compiler.py`, step 2: `load_interface(iface_path, env)` inside
  `with at_import(imp.offset, source_map)`, as `elaboration.py` does.

Check whether the JIT's path (`questlang/jit/session`, which compiles the module as a build does) goes through the
same `elaborate`. If it does not, give it the same wrapping.

Both compilers change together, since they must agree on `-o`.

**Tests.** A case `tests/self-hosted/build-errors/missing_import_interface/` (`main.quest`, `a.int.quest`,
`a.mod.quest` with a comment on its first line and `import bad : Bad` on line 4, and no `bad.int.quest`).
`build_errors.py` compares the bootstrap's diagnostics with the driver's on every path: `-o`, the JIT's run, and
`--no-jit`. Each must locate the error at `a.mod.quest:4:9`, quoting the import line.

---

## 6. Character I/O Without a Lock per Character

**Now.** `quest_reader_more` and `quest_reader_get_char` call `fgetc`, and `quest_writer_put_char` calls `fputc`
(`runtime/quest_stdlib.c`). Each call locks and unlocks the stream, which was two thirds of wc-input1's and
output1's samples ([benchmarks.md](benchmarks.md) §3.4). `getc_unlocked`, tried once, took wc-input1 from 42.5 s
to 8.5 s.

**Change.** Use `getc_unlocked` in the reader and `putc_unlocked` in the writer. This is safe because the runtime
runs Quest code on one thread: nothing in `runtime/` or `questlang/` starts a thread, and the JIT and the kernel run
in the driver's own thread. Reads of several characters (`fread`, `fwrite`) stay as they are, since they take the
lock once per call. Unlocked and locked calls on one stream may be mixed on a single thread. Record the
single-thread condition in a comment, so that a future thread knows to revisit it. Error handling is unchanged: `EOF`
from either call raises as before.

wasm has its own readers and writers (`runtime/wasm/core`), with no stdio lock, so it does not change.

**Tests and measurement.**

- The suites cover behavior: reader and writer goldens, REPL transcripts, and the pty tests.
- Measure wc-input1 and output1 before and after, on a quiet machine, with `benchmarks/mlton/run.py time --clean
  --scale 0.25`, one run each (the runtime changed). Also measure the driver build's time, since the compiler reads
  its sources through these functions.
- Record the times in a new benchmarks.md section, and point §3.4 at it.

---

## 7. Each Step's Check and Push

1. The step's own tests pass, natively and in the modes they run in.
2. Wait until the load average has stayed under 5 for three minutes, then run `tools/check`, which chooses every
   suite when the change touches anything outside the self-hosted compiler and the docs. Nothing else of mine runs
   during it.
3. A timeout or pty failure is rerun alone on a quiet machine. Any other failure is fixed and the check is run again.
4. Commit the change with its tasklist.md entry removed and its documents updated.
5. `git fetch` and rebase onto `origin/main`. If others' commits came in, rerun the step's own tests, and rerun
   `tools/check` if those commits touch the same files. Then push to `main`.

Step 3 changes the runtime and the ABI. A release afterwards (`tools/release`, from a clean worktree) keeps later
checks seeded by a compiler with the same runtime. Step 6 changes the runtime too, and a release at the end gives
the faster I/O to the compiler everyone runs.
