# Self-Hosted Compiler (`questlang/`) Miscompilation Audit

Audited `questlang/` at `83fa03c4d` (2026-11-27) for bugs that cause compiled Quest programs to produce wrong results, corrupt memory or GC state, crash/trap unexpectedly, or diverge from the interpreter.

Every finding below was **independently reproduced** against `./quest` across the relevant backend(s) (`c`, `ssac`, `arm64`, `wasm`, `jit`, `--whole-program`, `--inline-module`) and compared against `--no-jit` (interpreter) or the language specification.

- **Reproduced bugs:** 37 (**28 high**, **8 medium**, **1 low**)
- **False positives filtered out:** 3 (`sym_` mangling collision impossible because Quest forbids `_` in identifiers; `opSymbolAddress` large-offset encoding guarded; WASM uninitialized located `sVarDecl` guarded)

---

## Summary Table

| # | Severity | Scope / Backends | Location | Summary |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **high** | all | [elaboration.mod.quest:771-825](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/modules/elaboration.mod.quest#L771) | `elaborateModule` reuses stale `Unit.exportScope` on module name collision |
| 2 | **high** | whole-program | [whole.mod.quest:123-160](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/driver/whole.mod.quest#L123) | `--whole-program --apart` leaves apart modules transparent in shapes (ABI mismatch) |
| 3 | **high** | all | [elaboration.mod.quest:591-606](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/modules/elaboration.mod.quest#L591) | `var` interface values unchecked in conformance, silently lost on write, stripped in `.qi` |
| 4 | **medium** | c | [headers.mod.quest:48-51](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/build/headers.mod.quest#L48) | `writeInterfaceHeader` omits `programDir`, causing `.int.h` include-guard collisions |
| 5 | **high** | all | [model.mod.quest:256-290](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/types/model.mod.quest#L256) | `formFree`, `substituteFull`, `applyOperator` omit bounds on `typeVariable`/`typeAuto`/`typeOperator`/`typeRec` |
| 6 | **high** | all | [subtyping.mod.quest:625-642](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/types/subtyping.mod.quest#L625) | `subtyping.tuples` skips non-`POWER` kind checks and checks manifest bindings one-way |
| 7 | **medium** | all | [contractiveness.mod.quest:94](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/types/contractiveness.mod.quest#L94) | Contractiveness accepts unguarded `Rec(T) F(T)` through abstract operator `F` |
| 8 | **medium** | all | [subtyping.mod.quest:513](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/types/subtyping.mod.quest#L513) | Recursive `isSubkind`/`isKindEqual`/`isTypeEqual` inside subtyping drop trail & reset fuel |
| 9 | **high** | all | [application.mod.quest:45-70](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/application.mod.quest#L45) | Lvalue check unwraps `Var`/`Out`, passing slot address (`T **`) as element pointer (`T *`) |
| 10 | **high** | all | [aggregates.mod.quest:688-728](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/aggregates.mod.quest#L688) | `elaborateArray` checks explicit element annotation covariantly against `Array(Super)` |
| 11 | **high** | all | [bindings.mod.quest:555-558](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/bindings.mod.quest#L555) | Path-type escape check bypassed when expected type is an inference metavariable (segfault) |
| 12 | **medium** | all | [bindings.mod.quest:239-275](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/bindings.mod.quest#L239) | `mergeTypeOnlyFun` types forwarded `var`/`out` `exprVar` as `p.type` instead of `Var`/`Out` |
| 13 | **high** | all | [staticdata.mod.quest:108-132](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/repr/staticdata.mod.quest#L108) | Record descriptor key omits `isVar`, letting `dynamic.be` cast immutable record to mutable |
| 14 | **high** | all | [descriptors.mod.quest:166-190](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/repr/descriptors.mod.quest#L166) | `canonicalFunType` skips nested `typeAll` bodies, breaking `dynamic.be` on curried `All` |
| 15 | **high** | all | [genericlayout.mod.quest:72-79](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/repr/genericlayout.mod.quest#L72) | `storedValueAgrees` returns true for any bounded `Fun` type parameter |
| 16 | **high** | all | [represent.mod.quest:1192-1286](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L1192) | `opAddrCell` (`var(e)`) initializer never converted to cell element type (wrong field/tag) |
| 17 | **high** | all | [represent.mod.quest:437-441](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L437) | `adaptPlan` and `typeAppPlans` skip `var`/`out` parameters (wrong field on `out` subtyping) |
| 18 | **high** | all | [represent.mod.quest:1192-1286](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L1192) | `is`/`isnot` on subtype-related variants/options compares mismatched raw tag indices |
| 19 | **high** | all | [inline.mod.quest:461-469](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/inline.mod.quest#L461) | `inline.specialize` drops `var`/`out` mode on non-static parameters |
| 20 | **high** | all | [inline.mod.quest:449-459](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/inline.mod.quest#L449) | `inline.specialize` binds static value params directly to mutable caller variables |
| 21 | **medium** | `--inline-module` | [opened.mod.quest:255-280](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/opened.mod.quest#L255) | `opened.copyOf` drops top-level `sLetRec` without marking its binders as `lost` |
| 22 | **medium** | `--inline-module` | [simplify.mod.quest:880-889](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/simplify.mod.quest#L880) | Cross-module inlining of `var`/`out` params substitutes opaque abstract var into concrete body |
| 23 | **high** | arm64, ssac, jit | [calls.mod.quest:370-401](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/build/calls.mod.quest#L370) | `forwardedExternal` ignores return value, miscompiling 2-stmt wrappers calling an external |
| 24 | **high** | all (c, arm64, ssac, jit) | [control.mod.quest:302-312](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/build/control.mod.quest#L302) | Nested `sLetRec` shadows `deferred`, leaving outer recursive captures NULL (SIGSEGV in C) |
| 25 | **medium** | arm64, jit | [adapters.mod.quest:185-193](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/build/adapters.mod.quest#L185) | Function-type adapter thunks omit `zext8` on narrow (`Bool`/`Char`) parameters on entry |
| 26 | **low** | arm64, ssac, jit | [scalars.mod.quest:859-891](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/scalars.mod.quest#L859) | `scalars.replaceFunction` propagates `base = ~1` for `ptr_add`/`unproxy` before `lastStore` |
| 27 | **high** | arm64, ssac, jit | [loops.mod.quest:1144-1147](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/loops.mod.quest#L1144) | `loops.nonNegative` treats any invariant offset-0 load (e.g. `tables` lookup) as non-negative |
| 28 | **high** | arm64, ssac, jit | [loops.mod.quest:1143-1181](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/loops.mod.quest#L1143) | `loops.nonNegative` ignores signed 64-bit wrap-around, eliminating bounds checks |
| 29 | **high** | arm64, jit | [tailcalls.mod.quest:133-163](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/tailcalls.mod.quest#L133) | `tailCalls` drops `zext8`/`sext8` and tail-calls `passByte` callees from `passWord` callers |
| 30 | **medium** | arm64, ssac, jit | [conditions.mod.quest:83-108](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/conditions.mod.quest#L83) | `conditions.operand` omits `i.imm` addend when keying `opSymbol` |
| 31 | **high** | c | [printer.mod.quest:3094-3106](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/printer.mod.quest#L3094) | Wrong GC root word count in `qr_roots[]` for unboxed tuple / boxed record globals |
| 32 | **high** | c | [declarations.mod.quest:1027-1045](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/declarations.mod.quest#L1027) | Runtime function adapters forward `var`/`out` pointers without `out` conversion (SIGSEGV) |
| 33 | **high** | c | [printer.mod.quest:2807-2834](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/printer.mod.quest#L2807) | `volatileVars` misses locals modified via `opAddrVar` (`@x`) inside `try` blocks |
| 34 | **high** | jit (arm64) | [codegen.mod.quest:502-505](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/arm64/codegen.mod.quest#L502) | Exact 4096-byte stack frame silently encodes `sub sp, sp, #0` in JIT encoder (SIGSEGV) |
| 35 | **high** | jit (arm64) | [loader.mod.quest:88-99, 234-243](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/jit/loader.mod.quest#L88) | JIT loader caches stale GOT slots across reloaded modules after failed REPL inputs |
| 36 | **high** | wasm | [codegen.mod.quest:1318-1335](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/wasm/codegen.mod.quest#L1318) | Reading located `Record`/`Variant` `var` params leaves boxed `eqref` on stack (invalid Wasm) |
| 37 | **high** | wasm | [codegen.mod.quest:4785-4841](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/wasm/codegen.mod.quest#L4785) | `accumulateSite` evaluates mutable/global operand before recursive call (wrong answer) |

---

## Detailed Findings

### Silent Wrong Answers & Memory / GC Corruption (Highest Priority)

#### #2. Whole-program `--apart` modules remain transparent in shapes (ABI mismatch)
- **Location:** [questlang/driver/whole.mod.quest:123-160](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/driver/whole.mod.quest#L123)
- **Affected:** `--whole-program --apart` (`c`, `ssac`, `arm64`)
- **Mechanism:** Whole-program mode enables `shapes.setTransparentAbstractTypes(true)` during elaboration, registering concrete representations for `--apart` modules' abstract types without marking them in `abstractTypes.apartNames`. `whole.mergeImports` keeps `--apart` modules as separately compiled objects (which use opaque `QVal` at the ABI boundary), so `main` calls `box.make`/`box.get` expecting `QReal` in `d0` while `box.o` passes `QVal` in `x0`.
- **Observed vs. Expected:** `--no-jit` prints `3.5 : Real`; `compile --whole-program --apart box` prints **`9.25 : Real`** on `c`, `arm64`, and `ssac`.
- **Reproducer:**
```quest
(* box.int.quest: interface Box export T::TYPE make(x: Real): T get(b: T): Real end *)
(* box.mod.quest: module box : Box export Let T = Real let make(x: Real): T = x let get(b: T): Real = b end *)
import box : Box
let a = box.make(3.5)
let b = box.make(9.25)
box.get(a)
```

#### #9. Lvalue checking unwraps `Var`/`Out` on fields, array elements, and `var` variables
- **Location:** [questlang/typechecker/application.mod.quest:45-70, 166-273](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/application.mod.quest#L45)
- **Affected:** all
- **Mechanism:** `checkLvalueModeType` unconditionally unwraps `typeVar`/`typeOut` and `checkLvalueTarget` accepts fields/elements holding `Var(Int)`, lowering `@r.c` to `opAddrField` (`QInt **`) and passing it where `QInt *` is expected. The callee increments the pointer itself.
- **Observed vs. Expected:** `--no-jit`: `11 : Int`; `--jit`: **`0 : Int`**; `--backend arm64`: **`-8646911284551352320 : Int`**; `--backend c`: clang incompatible pointer type error (`QInt **` vs `QInt *`).
- **Reproducer:**
```quest
let inc(var x: Int): Ok = x := x + 1
let r = record c = var(10) end
inc(@r.c)
@r.c
```

#### #11. Path-type escape checks bypassed when expected type is a metavariable
- **Location:** [questlang/typechecker/bindings.mod.quest:555-558](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/typechecker/bindings.mod.quest#L555)
- **Affected:** all
- **Mechanism:** `elaborateFunBody` calls `escape.checkNoEscapingPathTypes` on `maybe.unwrapOr(b.expected b.ret)` without pruning solved `typeMeta`, and `model.findPathTypes` has no `typeMeta` branch. An existential `p.T` escapes its scope and unifies `Int` and `String` across calls.
- **Observed vs. Expected:** Should be a static type error; instead `--jit` and `--backend c` **segfault (exit 139)**.
- **Reproducer:**
```quest
Let Pkg = Tuple T::TYPE v: T use: All(x: T) Int end
let apply(R::TYPE f: All(p: Pkg) R): All(p: Pkg) R = f
let unpack = apply(fun(p: Pkg) tuple let v = p.v let use = p.use end)
let intPkg: Pkg = tuple Let T = Int let v = 42 let use(x: Int): Int = x + 1 end
let strPkg: Pkg = tuple Let T = String let v = "hi" let use(x: String): Int = string.length(x) end
unpack(strPkg).use(unpack(intPkg).v)
```

#### #13. Record descriptor key omits `isVar`, aliasing immutable and mutable record descriptors
- **Location:** [questlang/repr/staticdata.mod.quest:108-132, 258-261](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/repr/staticdata.mod.quest#L108)
- **Affected:** all (`c`, `ssac`, `arm64`, `jit`, `wasm`)
- **Mechanism:** `shapeKey` omits `f.isVar`, deduplicating `Record x: Int end` and `Record var x: Int end` into one `QTypeDescriptor`. Pointer equality short-circuits `quest_subtype_in` to `true`, letting `dynamic.be` cast an immutable record to a mutable one.
- **Observed vs. Expected:** `--no-jit` raises `dynamic.error`; `--jit`, `c`, `ssac`, and `wasm` silently mutate `r.x` and print **`99 : Int`**.
- **Reproducer:**
```quest
import dynamic : Dynamic
let r = record x = 1 end
let d = dynamic.new(r)
let m = dynamic.be(:Record var x: Int end d)
m.x := 99
r.x
```

#### #16. `opAddrCell` (`var(e)`) initializer never converted to cell element type
- **Location:** [questlang/ir/represent.mod.quest:1192-1286](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L1192)
- **Affected:** all (`c`, `ssac`, `arm64`, `wasm`, `jit`)
- **Mechanism:** `operation()` has no `opAddrCell` case, and `slots.mod.quest:454-456` boxes `x.init` using `typeOf(x.init)` rather than the cell's element type. Passing `var(sub)` to `var r: Super` reads the wrong record field or variant tag.
- **Observed vs. Expected:** `--no-jit`: `20 : Int`; `--jit`, `c`, `ssac`, and `arm64`: **`10 : Int`**.
- **Reproducer:**
```quest
Let Super = Record z: Int end
Let Sub = Record a: Int z: Int end
let f(var r: Super): Int = r.z
let var fRef = f
let var sub: Sub = record a = 10 z = 20 end
fRef(var(sub))
```

#### #17 & #32. `adaptPlan`, `typeAppPlans`, and C runtime function adapters skip `var`/`out` conversions
- **Location:** [questlang/ir/represent.mod.quest:437-441, 890-894](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L437), [questlang/codegen/c/declarations.mod.quest:1027-1045](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/declarations.mod.quest#L1027)
- **Affected:** all (`c`, `ssac`, `arm64`, `wasm`, `jit`)
- **Mechanism:** Both static thunks (`adaptPlan`/`typeAppPlans`) and C runtime adapters (`emitFunTypeAdapters`) forward `var`/`out` pointers directly without converting `out` values on return or checking layouts.
- **Observed vs. Expected:**
  - Covariant `out` subtyping (`All(out r: Sub) Ok <: All(out r: Super) Ok`): `--no-jit`: `20 : Int`; `--jit`, `c`, `ssac`, `arm64`: **`10 : Int`**.
  - Dynamic `out` subtyping via `dynamic.be` (#32): `--no-jit`: `"ok" : String`; `--backend c`: **SIGSEGV (exit 139)**.
  - `opTypeApp` on `var` param (`set(:Bool)`): `--backend c` fails clang compilation (`QBool *` vs `QVal *`).
- **Reproducer:**
```quest
Let Super = Record z: Int end
Let Sub = Record a: Int z: Int end
let fill(out r: Sub): Ok = r := record a = 10 z = 20 end
let var g: All(out r: Super) Ok = fill
let var x: Super = record z = 1 end
g(@x)
x.z
```

#### #18. `is`/`isnot` on subtype-related variants or options compares mismatched tag numberings
- **Location:** [questlang/ir/represent.mod.quest:1192-1286](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ir/represent.mod.quest#L1192)
- **Affected:** all (`c`, `ssac`, `arm64`, `wasm`, `jit`)
- **Mechanism:** `represent.operation()` has no `opPrim` case, so `primIs`/`primIsnot` never converts subtype variants/options to a common tag numbering before comparing raw tags.
- **Observed vs. Expected:** `--no-jit`: `tuple xy=true xz=false end`; `--jit`, `c`, `ssac`, `arm64`: **`tuple xy=false xz=true end`**.
- **Reproducer:**
```quest
Let Sub = Variant z: Int end
Let Super = Variant a: Int z: Int end
let var x = variant z of Sub with 1 end
let var y = variant z of Super with 1 end
let var z = variant a of Super with 1 end
tuple let xy = x is y let xz = x is z end
```

#### #23. `forwardedExternal` ignores return value, miscompiling 2-statement external wrappers
- **Location:** [questlang/ssa/build/calls.mod.quest:370-401, 421-439](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/build/calls.mod.quest#L370)
- **Affected:** `arm64`, `ssac`, `jit`
- **Mechanism:** `forwardedExternal(f)` matches a 2-statement function `[let c = ext(params...); return expr]` without checking that `sReturn.value` is `c`. When `f` is not inlined, callers substitute `ext(params...)` directly and return its result instead of `expr`.
- **Observed vs. Expected:** Returning `42` after calling `quest_string_get_char("abc", 0)`: `--no-jit` and `--backend c` return `84 : Int` (`42 + 42`); `--jit`, `arm64`, and `ssac` return **`194 : Int`** (`97 + 97`).

#### #24. Nested `sLetRec` shadows `deferred`, leaving outer recursive captures NULL/unbound
- **Location:** [questlang/ssa/build/control.mod.quest:302-312, 592-608](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/build/control.mod.quest#L302), [questlang/codegen/c/printer.mod.quest:2422-2435](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/printer.mod.quest#L2422)
- **Affected:** all (`c`, `arm64`, `ssac`, `jit`)
- **Mechanism:** `deferred` holds only a single `maybe.T(Deferred)` instead of a stack. An inner `sLetRec` overwrites the outer one, so closures in the inner group capturing an outer `sLetRec` variable either fail SSA lowering (`unbound`) or capture uninitialized NULL in C and segfault at runtime.
- **Observed vs. Expected:** `--no-jit`: `4 : Int`; `--backend c`: **SIGSEGV (exit 139)**; `--jit`/`arm64`: compile failure (`a use of variable g, which nothing binds`).

#### #27 & #28. `loops.nonNegative` eliminates needed array bounds checks
- **Location:** [questlang/ssa/passes/loops.mod.quest:1143-1181](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/loops.mod.quest#L1143)
- **Affected:** `arm64`, `ssac`, `jit`
- **Mechanism:**
  - **#27:** Treats any invariant 8-byte `Int` load at offset 0 as non-negative (assuming `QArray.length`/`QString.length`), but `tables.convert` emits invariant offset-0 loads for dense switch lookup tables that can hold negative constants (e.g. `~1`).
  - **#28:** Ignores signed 64-bit wrap-around on `opAdd` with small positive constants (`INT64_MAX + 1` wraps to `INT64_MIN`).
- **Observed vs. Expected:**
  - **#27:** `--no-jit` raises `arrayOp.error`; `--jit`, `arm64`, and `ssac` read `a[~1]` (array length header) and return **`2 : Int`**.
  - **#28:** `--no-jit` raises `arrayOp.error`; `--jit`, `arm64`, and `ssac` index `a[INT64_MIN]` (wrapping byte offset to 0) and return **`10 : Int`**.
- **Reproducer (#27):**
```quest
Let Tag = Option a b c d end
let f(a: Array(Int) k: Tag): Int =
    begin
        let idx = case k when a then ~1 when b then 0 when c then 1 when d then 2 end
        if idx < extent a then a[idx] else 0 end
    end
let var t = option a of Tag end
f(array of 10 20 end t)
```

#### #29. `tailCalls` drops `opZext8`/`opSext8` when tail-calling a `passByte` callee from a `passWord` caller
- **Location:** [questlang/ssa/passes/tailcalls.mod.quest:133-163](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/ssa/passes/tailcalls.mod.quest#L133)
- **Affected:** `arm64`, `jit`
- **Mechanism:** `tailPops` strips trailing `zext8`/`sext8` and turns `call quest_reader_get_char(...) result narrow; zext8; return` into `b _quest_reader_get_char` even when the enclosing function returns `Int` (`passWord`). Under AAPCS64, a `uint8_t` callee may leave garbage in bits 8..63 of `x0`.

#### #31. Wrong GC root word count in `qr_roots[]` for unboxed tuple globals
- **Location:** [questlang/codegen/c/printer.mod.quest:3094-3106](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/printer.mod.quest#L3094)
- **Affected:** `c`
- **Mechanism:** `globalDeclarations` emits `static QTuple_Int_String g_p;` (2 words) using `varCType`, but computes root word count via `representationKinds(shapeOf(v.type))` (1 word), ignoring `v.unboxed`/`v.boxed`. The second field (`QString *`) is unregistered as a GC root.
- **Observed vs. Expected:** Compiled C binary immediately aborts under `QUEST_GC_CHECK=roots,poison`: `root 0x... (g_p, in __DATA) holds the heap pointer 0x... but no root table or listed root covers it`.

#### #33. `volatileVars` misses locals modified via `opAddrVar` (`@x`) inside `try` blocks
- **Location:** [questlang/codegen/c/printer.mod.quest:2807-2834](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/c/printer.mod.quest#L2807)
- **Affected:** `c`
- **Mechanism:** `volatileVars` ignores `opAddrVar` inside `sTry`, emitting non-volatile `QInt l_x;`. Clang `-O2` inlines a static callee taking `&l_x` and drops the update across `setjmp`/`longjmp`.
- **Observed vs. Expected:** `--no-jit`: `1 : Int`; `--backend c`: **`0 : Int`**.
- **Reproducer:**
```quest
let e = exception e end
let rec inc(var n: Int k: Int): Ok =
    begin if k > 0 then inc(@n k - 1) else n := n + 1 end ok end
let test(): Int =
    begin
        let var x = 0
        try inc(@x 0) raise e end when e then x end
    end
test()
```

#### #34. Exact 4096-byte stack frame silently encodes `sub sp, sp, #0` in JIT encoder
- **Location:** [questlang/codegen/arm64/codegen.mod.quest:502-505](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/codegen/arm64/codegen.mod.quest#L502)
- **Affected:** `jit` (arm64)
- **Mechanism:** Prologue uses `size <= 4096` instead of `size < 4096`. In `encode.mod.quest:284`, `shl(4096, 10)` overflows `imm12` into bit 22 (`sh = 1`), leaving `imm12 = 0` (`sub sp, sp, #0, lsl #12`). Subsequent spill stores clobber `fp`/`lr`.
- **Observed vs. Expected:** Function with 520 live `Int` locals across calls (exact 4096-byte frame): `--no-jit` prints `135460 : Int`; `--jit` **crashes with SIGSEGV (exit 139)** (while 518 locals / 4080 bytes and 522 locals / `> 4096` succeed).

#### #35. JIT loader caches stale GOT slots across reloaded modules after failed REPL inputs
- **Location:** [questlang/jit/loader.mod.quest:88-99, 234-243](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/jit/loader.mod.quest#L88)
- **Affected:** `jit` (arm64)
- **Mechanism:** When a REPL input raises an exception, `session.forget()` forgets loaded modules so the next import reloads them, and `loader.load` updates `l.exported` but never invalidates `l.slots`. Relocations reuse the stale GOT slot pointing to the aborted load's mutated state.
- **Observed vs. Expected:** Input 1 mutates `m.x.v := 99; 1 / 0`; Input 2 imports `m` and reads `m.x.v`: `--no-jit` prints `1 : Int`, `--jit` prints **`99 : Int`**.

#### #37. WASM `accumulateSite` evaluates mutable/global operand before recursive call
- **Location:** [questlang/wasm/codegen.mod.quest:4785-4841](file:///Users/haahr/Dropbox/Paul/src/quest/.claude/worktrees/docs-08571e/questlang/wasm/codegen.mod.quest#L4785)
- **Affected:** `wasm`
- **Mechanism:** `accumulateSite` folds `other` in `f(...) + other` into `accLocal` *before* branching back to the loop header, without checking whether `other` is a mutable variable that the recursive call modifies.
- **Observed vs. Expected:** `--no-jit`: `6 : Int`; `--backend wasm`: **`3 : Int`**.
- **Reproducer:**
```quest
let rec f(n: Int var g: Int): Int =
    begin g := g + 1 if n <= 0 then 0 else f(n - 1 @g) + g end end
let var g = 0
f(2 @g)
```

---

### Additional Confirmed & Reproduced Bugs (Type Soundness, Rejecting/Crashing on Valid Code, Edge Cases)

- **#1 (`modules/elaboration.mod.quest:771-825`):** Reusing `Unit.exportScope` when a second module shares a name with a different interface lets `m.x + 1` pass typechecking when `m.x` is a `String` (runtime error in interpreter, codegen error in compiled backends).
- **#3 (`modules/elaboration.mod.quest:591-606`):** `checkConformance` ignores `isVar`, letting immutable `let count = 0` satisfy `var count: Int` (writes silently lost); `.qi` files also strip `isVar`, rejecting valid separate-compilation writes.
- **#4 (`build/headers.mod.quest:48-51`):** `writeInterfaceHeader` passes `maybe.none()` instead of `programDir` to `canonicalizeInterfaceName`, giving `a/item.int.h` and `b/item.int.h` the identical `#ifndef QUEST_INTF_ITEM_H` guard.
- **#5 (`types/model.mod.quest:256-290, 961-1015, 1193-1212`):** `formFree`, `substituteFull`, and `applyOperator` omit bounds on `typeVariable`, `typeAuto`, `typeOperator`, and `typeRec`, causing C pointer-type ABI mismatches on `Pkg(Point)`, unsound `Box(Int) <: Box(String)` on parameterized `Auto`, and false rejection of valid `Auto` introductions.
- **#6 (`types/subtyping.mod.quest:625-642`):** `subtyping.tuples` skips non-`POWER` kind checks (accepting `Int` for `F::ALL(A::TYPE) TYPE`) and checks manifest `tupleTypeBinding` pairs one-way (`Sub` for `Super`).
- **#7 (`types/contractiveness.mod.quest:94`):** Accepts `Rec(T::TYPE) F(T)` for abstract `F::ALL(A::TYPE) TYPE`; instantiating with identity hangs the compiler in unbounded unfolding.
- **#8 (`types/subtyping.mod.quest:513, 556, 568, 617, 691`):** Recursive calls to `isSubkind`/`isKindEqual`/`isTypeEqual` drop the coinductive trail and reset fuel, causing `stack.overflow` on valid `Let Rec T1 = Auto A <: T1 with a: A end`.
- **#10 (`typechecker/aggregates.mod.quest:688-728`):** `elaborateArray` checks explicit `:Sub` element annotation covariantly against `Array(Super)`, crashing `ir/represent` on compiled backends.
- **#12 (`typechecker/bindings.mod.quest:239-275`):** `mergeTypeOnlyFun` types forwarded `var`/`out` `exprVar` as `p.type` instead of `Var(p.type)`/`Out(p.type)`, failing SSA verification, clang, and Wasm validation on valid code.
- **#14 (`repr/descriptors.mod.quest:166-190`):** `canonicalFunType` only recurses into `typeFun`, not nested `typeAll`, causing `dynamic.be` to falsely raise `dynamic.error` on alpha-equivalent curried `All` types across all compiled backends.
- **#15 (`repr/genericlayout.mod.quest:72-79`):** `storedValueAgrees` returns `true` for any bounded `Fun` type parameter, causing valid bounded function upcasts to fail compilation across all backends.
- **#19 (`ir/inline.mod.quest:461-469`):** `inline.specialize` hardcodes `isVar = false, isOut = false` on non-static parameters, failing compilation of recursive functions taking both a static function argument and a `var`/`out` parameter.
- **#20 (`ir/inline.mod.quest:449-459`):** `inline.specialize` binds static value parameters directly to mutable caller variables, failing closure conversion with `captures mutable variable`.
- **#21 (`ir/opened.mod.quest:255-280`):** `opened.copyOf` drops top-level `sLetRec` without adding its binders to `lost`, leaving unbound variables in `--inline-module` builds.
- **#22 (`ir/simplify.mod.quest:880-889`):** Cross-module inlining of `var`/`out` parameters from `--inline-module` substitutes opaque abstract-typed variables into concrete-typed bodies, crashing `ir/slots`.
- **#25 (`ssa/build/adapters.mod.quest:185-193, 226-235`):** Function-type adapter thunks omit `zext8` on narrow (`Bool`/`Char`) parameters before wrapping into `QVal` on ARM64/JIT.
- **#26 (`ssa/scalars.mod.quest:859-891`):** `scalars.replaceFunction` propagates `base = ~1` for `ptr_add`/`unproxy` before `lastStore`, crashing `hashMap.find` on valid SSA (latent in current pass order).
- **#30 (`ssa/passes/conditions.mod.quest:83-108`):** `conditions.operand` omits `i.imm` when keying `opSymbol`, conflating `sym + 0` and `sym + 8` in `decideFunction`.
- **#36 (`wasm/codegen.mod.quest:1318-1335`):** Reading located `Record`/`Variant` `var` parameters leaves a boxed `eqref` on the stack instead of 2-part `(eqref, eqref)`, producing invalid WebAssembly bytecode.
