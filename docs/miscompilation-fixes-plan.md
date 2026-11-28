# Miscompilation Fixes Plan

This plan fixes the real bugs in [self_hosted_miscompilation_audit.md](self_hosted_miscompilation_audit.md), an
audit of `questlang/` at 83fa03c4 by another model. Each of its 37 claims was checked again here (2026-11-27, at
2af5baa3), and again after 95 refactoring commits (2026-11-27, at bdab6049), when every result below held: its code
read, and a reproducer run in the interpreter (`--no-jit`), the JIT, compiled arm64, c and ssac
binaries (`quest compile --backend B --print-result -o X F && ./X`), and wasm. Where a bug is in code both compilers
have, the bootstrap was tried too (`questboot`, interpreter and `--stop-after run_c_compiled`).

One thing to know when reproducing: in run mode `--backend c`, `ssac` and `arm64` all run the arm64 JIT (only wasm
differs), and `--whole-program` in run mode interprets. A backend is tested only by `quest compile`. Some of the
audit's "every backend" results were the JIT alone.

## 1. Verdicts

28 are real, 4 are real but latent (no program found that shows them), 3 are real in a different form than the audit
says, and 2 are not bugs. "Boot" says whether the bootstrap compiler has the same bug.

| # | Verdict | Where it shows | Boot | What it is |
| :-: | :--- | :--- | :-: | :--- |
| 1 | real | all compiled: compiler crash; interpreter: wrong static type | yes | second `module m` reuses the first's export scope |
| 2 | real | `--whole-program --apart`: wrong answer (9.25 for 3.5), wasm link error | n/a | apart module laid out transparent |
| 3 | real, wider | **every compiled mode loses writes to an exported `var`, valid code too** | yes | conformance ignores `isVar`; `.qi` drops it |
| 4 | latent | `.int.h` guards collide; nothing generated depends on both | yes | `programDir` not passed |
| 5 | real | valid `Auto` with a bound rejected; `Box(Int) <: Box(String)` accepted | yes | substitution skips kind bounds |
| 6 | real, half | ill-kinded tuple component accepted through subsumption | yes | non-`POWER` bounds unchecked (one-way manifest half: not a bug) |
| 7 | real | compiler hangs (bootstrap: RecursionError) | yes | `Rec(T) F(T)` with abstract `F` passes contractiveness |
| 8 | real, different | valid equi-recursive subtyping rejected (no overflow) | yes | kind comparisons restart trail and fuel |
| 9 | real | JIT/arm64/ssac wrong answer, c clang error, wasm invalid | yes (c) | `@r.c` on a field of type `Var(Int)` |
| 10 | real | compiler crash on valid code | yes | array literal's annotation checked covariantly |
| 11 | real | ill-typed program accepted; segfault | (types) | path type escapes through a solved metavariable |
| 12 | real | c clang error, ssac segfault, wasm invalid | yes | forwarded `var`/`out` argument typed without `Var`/`Out` |
| 13 | real | all compiled: `dynamic.be` makes an immutable record mutable | yes | descriptor key omits `isVar` |
| 14 | not a bug | — | — | descriptor tag differs, but `dynamic.be` decides structurally |
| 15 | real, different cause | compiler crash on valid code | yes | `viewPlan` has no case for a function-bounded type parameter |
| 16 | real | all compiled: wrong field read | yes | `var(e)` initializer not converted to the cell's type |
| 17 | real | all compiled: wrong field read | yes | `out`/`var` parameters skipped by `adaptPlan`/`typeAppPlans` |
| 18 | real | all compiled: wrong `is` result | yes | `is` compares raw tags of subtype-related variants |
| 19 | real | JIT, c, wasm: compiler crash on valid code | no | `specialize` drops parameter modes |
| 20 | real | compiler error "captures mutable variable" on valid code | no | `specialize` binds a static argument to a mutable var |
| 21 | real | `--inline-module`: compiler error on valid code | n/a | `opened.copyOf` drops `sLetRec` without marking it lost |
| 22 | real | `--inline-module`: SSA/clang/wasm failure on valid code | n/a | var parameter of abstract type inlined unconverted |
| 23 | real | JIT, arm64, ssac: wrong answer (194 for 84) | n/a | `forwardedExternal` ignores what the wrapper returns |
| 24 | real | c segfault; arm64, ssac, JIT, wasm compiler error | ? | nested `sLetRec` overwrites `deferred` |
| 25 | latent | — | n/a | adapter thunks skip `zext8` on narrow parameters |
| 26 | latent | — | n/a | `scalars` copies `base = ~1` for an early derived pointer |
| 27 | real | JIT, arm64, ssac: bounds check removed, reads the length word | n/a | `nonNegative` trusts any offset-0 load |
| 28 | real | JIT, arm64, ssac: bounds check removed at `INT64_MIN` | n/a | `nonNegative` ignores wrap-around |
| 29 | latent on Darwin | — | n/a | tail call drops `zext8` for a byte-returning callee |
| 30 | latent | — | n/a | `conditions` keys `opSymbol` without its addend |
| 31 | real | c: global's second word not a GC root (`QUEST_GC_CHECK=stress,roots`) | no | root word count ignores unboxed tuples |
| 32 | real, wider | c, ssac, arm64, JIT: wrong field or segfault; wasm cast failure | yes | function adapters don't convert `out` values |
| 33 | real | c: wrong answer (0 for 1) at -O2 | yes | `volatileVars` misses `@x` inside `try` |
| 34 | real | JIT: segfault at an exact 4096-byte frame | n/a | `<= 4096`, and the encoder doesn't range-check |
| 35 | real | JIT REPL: reads the aborted module instance | n/a | loader keeps stale GOT slots |
| 36 | not a bug | — | — | located Record/Variant var params are unboxed by the IR's convert |
| 37 | real | wasm: wrong answer (3 for 6) | n/a | `accumulateSite` reads a var before the recursive call |

Found on the way, not in the audit:

- **Aliased interface imports.** `interface Both import :IA = :a/Item` with `IA.P` works in the interpreter. The JIT
  and compile fail: "Undefined identifier 'IA'", apparently because the alias is lost when the `.qi` is reloaded.
- **C export adapter.** `quest compile --backend c` of #22's `ctr` module fails even without `--inline-module`: its
  export adapter passes `QVal *` where `QReal *` is expected (`qf_bump(NULL, l_c_4)`). It is probably #32's cause.
- **Curried `All` equality.** type-system.md §6.4 says curried and uncurried types are one type, but
  `let k2: All(A::TYPE) All(B::TYPE) All(x: A y: B) A = k` is rejected.

## 2. Order and rules

Silent wrong answers come first, then crashes on valid code, then soundness holes, then hygiene. Each step is one
commit, or a few, with a regression test per bug (a golden test under `tests/source/`, its reproducer reduced) and
`tools/check` before the commit. Fixes go in both compilers where the bootstrap shares the bug (Boot = yes), and wasm
gets the matching change in the same step. Shared goldens come from the bootstrap; where the bootstrap has no such
feature (`--apart`, `--inline-module`, SSA), the test is self-hosted only.

Nothing is pushed until every step is done: the steps are committed one by one, then pushed together after a final
`tools/check` (decided 2026-11-27).

## 3. Steps

### Step 1: exported `var`s (#3)

The worst bug: in every compiled mode, a write to a module's exported `var` from outside is lost, even in a valid
program. `module c : C export let var count = 0 end` with `c.count := 5` then `c.count` prints 5 interpreted and 0
compiled. Separate compilation instead rejects the write ("Cannot assign to immutable record field"), because `.qi`
value records have no `isVar`.

- Find where compiled member access copies the `var` instead of sharing its cell. It's not pinned down yet; start
  from the module record's layout in `ir/lower` and `modules/elaboration`.
- `checkConformance` (`modules/elaboration.mod.quest:548`, bootstrap `elaboration.py`) requires `isVar` of the
  module's value when the interface's is `var`.
- `.qi` writes and reads `isVar`. That's an ABI bump.

### Step 2: representation conversions (#16, #17, #32, #18, #13)

All compiled backends, both compilers.

- **#16:** `var(e)`'s initializer is converted to the cell's element type: `represent.operation` gets an `opAddrCell`
  case, and `slots` boxes with the cell's type rather than `typeOf(init)`.
- **#17, #32:** a function conversion with `var`/`out` parameters whose types differ passes a temporary of the
  callee's type, then converts it back into the caller's location after the call. This covers `adaptPlan` and
  `typeAppPlans` in `ir/represent`, the C runtime adapters (`codegen/c/declarations.mod.quest:1028-1030`) and
  `ssa/build/adapters`. It should also fix the C export adapter above.
- **#18:** `primIs`/`primIsnot` on variants or options of different types converts both to the common type first, or
  compares tag names.
- **#13:** the record descriptor key in `repr/staticdata` includes `isVar`.

Tests: the audit's reproducers for #16, #17 and #18, plus these two:

```quest
(* #32 *)
import dynamic : Dynamic
Let Super = Record z: Int end
Let Sub = Record a: Int z: Int end
let fill(out r: Sub): Ok = r := record a = 10 z = 20 end
let d = dynamic.new(:All(out r: Sub) Ok fill)
let g = dynamic.be(:All(out r: Super) Ok d)
let var x: Super = record z = 1 end
g(@x)
x.z  (* 20 *)
```

```quest
(* #13: must raise dynamic.error *)
import dynamic : Dynamic
let r = record x = 1 end
let m = dynamic.be(:Record var x: Int end dynamic.new(r))
```

### Step 3: SSA bounds checks and forwarding (#27, #28, #23)

Self-hosted only.

- **#27:** `nonNegative` (now `ssa/passes/loops/bounds.mod.quest:102`) already asks for the length word's offset
  (`r.arrayLength`, `r.stringLength`), but any invariant 8-byte load at that offset still counts, a switch table's
  load included. Trust a length load only by what it loads from: an array or string, not a table.
- **#28:** at `bounds.mod.quest:109`, accept a constant only up to a bound such as 2^62, so a few small additions
  can't wrap.
- **#23:** `forwardedExternal` also requires the `sReturn` to return the `sLet`'s binder (or `ok` after an `sDo`).

Tests: the audit's #27 reproducer, and these two:

```quest
(* #28: arrayOp.error *)
let f(a: Array(Int)): Int =
    begin
        let var s = 0
        let var i = 9223372036854775806
        let var n = 0
        while n < 3 do
            i := i + 1
            if i < extent a then s := s + a[i] end
            n := n + 1
        end
        s
    end
f(array of 10 20 end)
```

```quest
(* #23: an unsound module m; main is m.g("abc"); needs QUEST_INLINE=size=-100 to keep f a call *)
let getChar(s: String i: Int): Char = external "quest_string_get_char"
let f(s: String i: Int): Int = begin let c = getChar(s i) 42 end
let g(s: String): Int = f(s 0) + f(s 0)  (* 84 *)
```

The #23 test needs a form that doesn't depend on the inlining knob. The recursive form in the verification's
scratch directory is one: it fails the SSA verifier instead.

### Step 4: nested recursive groups (#24)

`deferred` becomes a stack in the SSA builder (`ssa/build/control.mod.quest:305-310, 699-710`), the C printer
(`codegen/c/printer.mod.quest:224, 2349-2357`) and wasm. Each deferred capture is recorded against the group that
owns its variable. Check whether the bootstrap's C emitter shares it.

Test (12 interpreted; c segfaults; the rest fail "a use of variable g, which nothing binds"):

```quest
import writer: Writer
import conv: Conv
let rec f(n: Int): Int =
    if n > 100 then f(n - 100) + 1
    else
        begin
            let rec g: All(x: Int) Int =
                begin
                    let rec h(y: Int): Int = if y is 0 then n else g(y - 1) + h(0) end
                    h
                end
            g(n)
        end
    end
let var t = 3
writer.putString(writer.output conv.int(f(t)) <> "\n")
```

### Step 5: C backend (#33, #31)

- **#33**, both compilers: `volatileVars` marks every variable whose address is taken (`opAddrVar`) inside a `try`.
  The safer version marks every address-taken local of a function with a `try`. Test: the audit's reproducer.
- **#31:** a global's root word count comes from the representation `varCType` chose (all of an unboxed tuple's
  words, 1 for a boxed variable). Test: a top-level `let p = mk(12345)`, where `mk` returns
  `Tuple a: Int b: String end` and is big enough (about 40 statements) not to be inlined. `p.b` is then read from a
  recursive function. Under `QUEST_GC_CHECK=stress,roots` the C binary reports that `g_p` holds a heap pointer no root
  covers; the emitted C has `static QTuple_Int_String g_p;` next to `{ (void *)&g_p, 1 }`.

### Step 6: JIT (#34, #35)

- **#34:** fix it in the encoder (`codegen/arm64/encode.mod.quest:296-300`), as a second bug-hunting session also
  proposed. `opSubImm`, and `opAddImm` with shift 0, encode an immediate that is a multiple of 4096 up to 4095 × 4096
  in the shifted form, as `opCmpImm` already does, and raise `unencodable` for any other immediate of 4096 or more.
  The prologue's `size <= 4096` (`codegen/arm64/codegen.mod.quest:545`) is then right as written. Test: a generated
  function with 520 live `Int`s across calls, which gives an exact 4096-byte frame (518 call results do too).
- **Encoder ranges** (hardening, from the same session): the encoder truncates PC-relative fields without a check
  (`field`, `distance` and `adrImmediate`, `encode.mod.quest:56, 73, 221`). Conditional branches are relaxed before
  encoding (`peephole.relaxBranches`), but `adr` is not, and it is used for jump tables and exception resume labels
  (`select.mod.quest:795, 942`). Past ±1 MB, which takes a single function over 1 MB of code, the AOT assembler
  rejects the program, but the JIT would encode a wrong address. Each field raises `unencodable` when its value
  doesn't fit. Two other cases need nothing: `opAddImm` of exactly 4096 can't arise, since `jumpTable` biases only
  for `least > ~4096` (`select.mod.quest:781`) and switch cases are tags, never negative; and a symbol address with a
  large offset fails at compile time rather than producing wrong code. Test: a unit test of the encoder's range
  errors.
- **#35:** when `loader.load` exports a name that already has a GOT slot, it writes the new address into the slot.
  The alternative is for `session.forget` to drop the forgotten module's slots and stubs. Test: a REPL golden (`-i`
  on stdin):

  ```
  import m : M m.x.v := 99 1 / 0
  import m : M m.x.v
  ```

  Here `m.x` is `tuple let var v = 1 end`; the second line must print 1.

### Step 7: wasm (#37)

`accumulateSite` doesn't accumulate an operand that the recursive call can change: a `var` parameter, a global, or
anything read through one. Test: the audit's reproducer.

### Step 8: type checker, var modes and arrays (#9, #12, #10)

Both compilers.

- **#9:** `Var` and `Out` values are not first-class, as the Quest papers say (§5.7.1: "types like Var(Var(A))
  cannot be produced"). Today both checkers give `var(e)` the type `Var(T)` anywhere (`typecheck.mod.quest:313`,
  `typecheck.py:425`) and accept written `Var(...)`/`Out(...)` types anywhere. So `let x = var(10)`,
  `record c = var(10) end` and `var(var(1))` all typecheck; compiled code prints pointers, and `@x` mutates an
  immutable `let`. Decided (2026-11-27): reject both.
  - `var(e)` is an error except as the argument for a `var` or `out` parameter, where `application.mod.quest:111`
    handles it.
  - `Var(...)` and `Out(...)` are errors as written types. Mutability is spelled with the `var` and `out` keywords on
    bindings, fields and parameters; the types stay internal.
  - With neither, no value or component can have a `Var` type, so `@r.c` on a `Var` field can't arise, and
    `checkLvalueModeType`'s unwrapping only ever sees parameters' own `Var`/`Out`.
  - Tests: an error test for each form (`let x = var(10)`, a record field, `var(var(1))`, `array of var(1) end`,
    `Tuple :Var(Int) end`, `f(o: Out(Int))`). `cardelli_operators.quest` drops its unused `MutTup1` and `f(o:
    Out(Int))`; the parser's syntax test (`tests/parser/forms.quest`) keeps them, since parsing doesn't change.
    Update type-system.md §6.2.2 and §6.5 to say this.
- **#12:** `mergeTypeOnlyFun` (`typechecker/bindings.mod.quest:255-259`) types a forwarded argument
  `Var(p.type)`/`Out(p.type)` by the parameter's mode.
- **#10:** with an expected element type, the annotation must be equal to it, or the node is typed with the expected
  type after checking the elements against the annotation.

Test for #12 (2.5):

```quest
let mk(A::TYPE): All(out x: Bool var y: Real) Ok = fun(out x: Bool var y: Real): Ok begin x := true y := 2.5 end
let var keep = mk
let set(A::TYPE): All(out x: Bool var y: Real) Ok = keep(:A)
let var b = false
let var r = 1.25
set(:Int @b @r)
if b then r else 0.0 end
```

Test for #10 (2):

```quest
Let Super = Option a b end
Let Sub = Option b end
let f(x: Sub): Array(Super) = array of :Sub x end
case f(option b of Sub end)[0] when a then 1 when b then 2 end
```

### Step 9: inliner and inlined modules (#19, #20, #21, #22)

Self-hosted only.

- **#19:** `inline.specialize` copies each parameter's mode (`inline.mod.quest:462-467`).
- **#20:** a static argument that is a mutable variable is bound through a fresh immutable `let`, as constants are.
- **#21:** `opened.copyOf` adds a dropped `sLetRec`'s variables to `lost`.
- **#22:** `simplify` refuses to inline a call whose `var`/`out` parameter has an abstract type laid out differently
  at the call. Going through a converted temporary also works.

Tests:

```quest
(* #19: 6 *)
let rec count(f: All(x: Int) Bool var n: Int i: Int): Ok =
    if i > 0 then begin if f(i) then n := n + 1 end count(f @n i - 1) end end
let even(x: Int): Bool = x > 4
let main(): Int = begin let var c = 0 count(even @c 10) c end
main()
```

```quest
(* #20: 108 *)
let rec count(f: All(x: Int) Bool k: Int i: Int): Int =
    if i > 0 then {if f(i + k) then 1 else 0 end} + count(f k i - 1) else 0 end
let big(x: Int): Bool = x > 4
let rec main(n: Int): Int =
    if n < 0 then main(n + 1) else
        begin
            let var k = 0
            for j = 1 upto n do k := k + 1 end
            let r = count(big k 10)
            k := 100
            r + k
        end
    end
main(string.length("ab"))
```

- **#21:** module `rv` with `let rec t: G = tuple let g = fun(n: Int): Int if n > 0 then t.g(n - 1) + 1 else 0 end end`
  and `depth(n) = t.g(n)`; the program is `rv.depth(5)`, which gives 5. Test it with `--inline-module rv`.
- **#22:** module `ctr` with an abstract `T = Real`, `bump(var c: T)` and `get`; the program bumps twice from 2.0,
  which gives 5.0. Test it with `--inline-module ctr`.

### Step 10: modules and the driver (#1, #2, #4)

- **#1**, both compilers: a second declaration of a module with the same canonical name is an error (decided
  2026-11-27), reported at the second declaration with the first one's location. Test: an error test with two
  `module m` declarations of different interfaces.
- **#2:** before elaboration, every `--apart` module's abstract types are marked apart (`apartNames`), so main is
  laid out as `box.o` is (`driver/main.quest:133, 476, 555 and 605`; `modules/abstracttypes.mod.quest:101-106`).
- **#4**, both compilers: `writeInterfaceHeader` passes `programDir`.
- Fix the aliased interface imports in `.qi` (found on the way) here too.

### Step 11: type soundness (#5, #6, #7, #8, #11, #15, curried `All`)

Both compilers.

- **#5:** `substitute` and `formFree` go into kind bounds: `typeAuto`'s `kindBound`, `typeRec`'s `bound`,
  `typeOperator`'s parameter bounds, and `typeVariable`'s bound.
- **#6:** a tuple component matched against a formal is kind-checked against `t.bound` for every kind, not only
  `POWER` (`types/subtyping.mod.quest:618`).
- **#7:** an application whose constructor is an abstract variable isn't contractive in its arguments.
- **#8:** kind comparisons inside subtyping share the trail and fuel (`isSubkindIn`).
- **#11:** `escape.checkNoEscapingPathTypes` prunes solved metavariables, and `model.findPathTypes` looks through
  `typeMeta`. The test must fail to typecheck.
- **#15:** `viewPlan` plans a type parameter bounded by a function type as a function adaptation to its bound.
- **Curried `All` equality** (found on the way; decided 2026-11-27 to fix here): `All(A::TYPE) All(B::TYPE) T` and
  `All(A::TYPE B::TYPE) T` are one type (type-system.md §6.4), in type equality and subtyping, as the merged
  application of type operators already is (operator-kinds-plan step 1). Test:
  `let k2: All(A::TYPE) All(B::TYPE) All(x: A y: B) A = k` for a type-only `k`, accepted, and applied both ways.

### Step 12: latent hygiene (#25, #26, #29, #30)

Each is a line or two, and none changes any program found:

- **#25:** thunks apply `vals.narrowed` to narrow parameters.
- **#26:** `base` is resolved through the exact origin.
- **#29:** a tail call drops the extension only when the function itself returns a byte.
- **#30:** the `opSymbol` key includes `imm`.

Decided 2026-11-27: make them. Where a bug can't be shown by a program, its test is a unit test of the pass or a
golden of the pass's output (`--dump-after`), whichever the pass's existing tests use.

## 4. Before starting

Rebased and re-verified on 2026-11-27 at bdab6049, after the 95 refactoring commits: every result in §1 held. No bug
was fixed or moved by them beyond line numbers (here updated), and #27's check had been narrowed to the length offset
without fixing it. Wait for the user's go-ahead before step 1. If main moves much again before then, rebase and rerun
the reproducers first (backends with `quest compile`, not run mode).

## 5. Decisions (2026-11-27)

1. #9: reject `var(e)` outside `var`/`out` arguments, and written `Var`/`Out` types (step 8).
2. #1: reject a second module with the same canonical name (step 10).
3. Make the four latent fixes (step 12).
4. When every step is done, delete the audit document and this plan, keeping what lasts in the current-state docs.
5. Curried `All` equality is fixed in step 11.
6. Push once, at the end, after every step and a final `tools/check`.
