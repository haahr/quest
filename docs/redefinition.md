# Plan: Redefinition in Interactive Mode

Today a second definition of a name in the REPL shadows the first: functions compiled earlier keep the binding they
saw, so after `let f(n: Int): Int = 100 / n`, `let g(n: Int): Int = f(n) + 1`, `let f(n: Int): Int = n`, `g(0)` still
raises `int.error`. That is lexical scoping, which is right for programs, and wrong for interactive development, where
fixing a function should fix its callers without redefining each of them. This plan gives the REPL (and the file `-i`
loads) Python's and Lisp's behavior, redefinition in place, and changes nothing for programs, `-e`, or `quest FILE`.

**Status: step 1 done** (2026-11-02), behind `QUEST_REDEFINE=1`. Section 1 records the decisions, section 7 the
steps.

---

## 1. Decisions

Decided 2026-11-02:

1. **What is interactive:** the REPL's inputs, and the file `-i` runs before them, which is the first input. Not
   `-e`, not `quest FILE`, not compiled programs. The `-i` file is interactive because "load a file, fix a function,
   call it again" is the case this is for; its own top-level calls are then slot loads (decision 3) rather than
   direct calls, so a file runs slower under `-i` than as a program.
2. **The rule:** a top-level `let` of an interactive input whose name is currently bound to an *interactive slot*
   (§2) of the **same type** and the same `var`-ness **redefines** the slot: every use of it, earlier and later, sees
   the new value from then on. Any other rebinding (a different type, a `var` for a non-`var`, a name from a module or
   import) shadows, as now, with the warning of decision 4. Same type only: storing a subtype would be sound for the
   earlier uses, but later inputs would still see the slot's original type, a type the user did not write. Types
   that differ only in the names of their quantified variables are the same, as are a type and an alias of it. Types,
   modules, interfaces, and exceptions declared with `exception E end` are unchanged (§4).
3. **Late binding everywhere in interactive code:** a use of a slot is a load when it runs, in later inputs *and in
   the input that defines it*, inside functions too: never inlined, propagated, specialized, or called directly. So
   `-i`'s file, one input, is redefinable, and `let f() = 1; let g() = f(); let f() = 2; g()` on one line is 2, as
   in Python. The cost is in the JIT: jit.md §6 measured calls of an earlier input's `add1` at 2x a direct call and of
   a generic `twice` at 25x an inlined one; interactive code pays that for its top-level functions, including a
   function's calls of itself, so a recursive function of an `-i` file is slower than in the same file run as a
   program. That is accepted: it is the price of redefining it. A program pays nothing.
4. **A shadow with a different type warns.** When a top-level `let` of an interactive input shadows a slot because
   the type (or `var`-ness) differs, the REPL writes a warning on stderr, in the diagnostics' form:
   `warning: 'f' now has a different type; functions defined earlier keep the earlier 'f'`. After this plan it is the
   only shadowing left at an interactive top level, so it names exactly the case that surprises. No existing
   transcript changes a binding's type, so no golden changes. A warning for shadowing within one scope in programs
   is a separate question (§6).
5. **A redefinition is an assignment, and stays.** An input that fails after redefining a slot leaves the slot's
   new value, as it leaves a `:=` to a `var` (repl.md §5): `let var x = 5` and `x := 5` store to the same place, and
   rollback treats them alike. The environment and the values still agree, since a redefinition keeps the slot's type:
   the environment forgets the failed input's symbols, and the slot's earlier symbol reads the new value. (Revised
   2026-11-02 from restoring redefinitions, which needed a journal in each interpreter and a restore in the JIT
   session.)
6. **Every implementation:** the bootstrap's type checker, interpreter, and REPL (Python), the self-hosted type
   checker and interpreter, and the JIT. The REPL transcripts stay shared goldens (testing.md §2.7, §2.8).
7. **No way back.** Once the steps are done there is no option or environment variable for the lexical REPL: a second
   scoping mode is a maintenance and conceptual cost nobody wants to pay. `QUEST_REDEFINE=1` gates the work only
   while steps 1 and 2 are in progress, so that every commit keeps tools/check green, and step 3 removes it.

## 2. Semantics

An **interactive slot** is the binding of a top-level value `let` of an interactive input (decision 1): a phrase of
the input, not inside a block, function, tuple, or module. A slot has a type and a `var`-ness, fixed when it is made.

- A top-level `let` in an interactive input whose name's current binding is a slot of equal type (`isTypeEqual`) and
  equal `var`-ness **redefines** the slot; otherwise it **makes** a slot, shadowing whatever the name was, with the
  warning of decision 4 when what it shadows is a slot.
- A **use** of a slot reads it when the use runs. A function that names a slot reads it at each call; a closure
  keeps no copy. This holds within the defining input as across inputs (decision 3).
- `let rec f ... = ... f ...` redefining `f`: the body's `f` is the slot, so the new body calls itself, and old
  callers call it too. Mutual recursion across inputs follows: `let g(n: Int): Int = 0`, `let f(n: Int): Int = g(n)`,
  `let g(n: Int): Int = if n is 0 then 0 else f(n - 1) end`.
- `let x = 2 and y = x` (simultaneous): the members' values are computed before any member is bound (type-system.md
  §4), so `y` gets the `x` before the redefinition, and then `x`'s slot is redefined.
- A redefinition is an assignment to the slot's storage, and stays when the input fails later (decision 5). What it
  stored may be a closure of the failed input's other bindings, which the closure keeps alive as a closure of any
  input does.
- `let var x` makes a `var` slot; `x := e` and a redefinition `let var x = e` both store to it. A function still may
  not name a global `var` (the rule `checker.isGlobalVar` enforces, unchanged); it may name a non-`var` slot, which
  is where the new behavior lives.

## 3. Design

### 3.1. The type checker (both compilers)

- `env.T` gets `var interactive: Bool`, false unless the driver sets it (§3.5), and `slots: hashMap.T(Int Int)`, each
  value symbol made by an interactive top-level `let` mapped to its slot's id, the id of the first symbol bound to it.
  Both are in `env.Snapshot`, so a failed input's slots are forgotten with its symbols.
- Where a top-level `let` declares its symbol (`bindings`, the three `declareValue` sites for a let, a `let rec`, and
  a group's members): when `interactive` holds, `functionDepth` is 0, and the current scope is the unit's top-level
  scope, look the name up in that scope. If it is a symbol in `slots`, and `isTypeEqual` holds between its type and
  the new one, and `isVar` agrees, map the new symbol to the same slot and mark the binding; otherwise map it to a
  new slot (its own id) and, if the name was a slot, report the warning of decision 4, which does not stop the input:
  the checker's `warnings` (typecheck's `Result.warnings`, which the driver and the REPL report as
  `diagnostics.warningDiagnostic`s), the bootstrap's sink. This is `bindings.declareLet` (`_declare_let`), called
  for a plain `let`, a `let rec`, an external, and each member of a group.
- `typedAst.LetValue` gets `redefines: Bool` (the bootstrap's `TypedLetValue.redefines`), false everywhere but the
  marked bindings; the dump shows it (`:redefines`). No interface, `.qi`, or ABI change: slots live in the
  environment, not in `ValueSymbol`.

### 3.2. The interpreters (both)

Frames bind by name (`Frame.bindings: hashMap.T(String Value)`, `lookup` walks the parents), and closures capture
the frame, so an interpreter is late-bound by nature. Lexical scoping comes from one rule: a binding that rebinds a
name of its frame runs in a frame of its own (`evalScopedBinding`'s `declaresName`, `eval_scoped_binding`'s
`push_scope`). The change:

- A `LetValue` with `redefines` gets no frame of its own; its value is bound by **replacing the binding in the frame
  that holds the name** (as `assignName` finds it), not by `define` in the current frame. A `var` slot's cell is
  replaced too, which is safe since no function holds it (§2).
- Nothing else changes: unmarked bindings, `makeScopeExceptions`, modules, and imports are as they are.

### 3.3. The JIT's lowering (self-hosted)

A phrase unit today lowers its top-level bindings as a program's: a function is an IR function (`sFuns`) called
directly by name, a value a variable the passes propagate, and the record that later inputs read is made when the
phrases have run (jit.md §3.2). For an interactive input, every top-level value binding is instead held in a **box**,
the one-component `var` tuple the lowering already uses for captured local `var`s (`capturedMutables`, `l.boxes`):

- **Defining** a slot allocates its box and stores the value. A function binding still makes its IR function, but a
  closure of it is made and boxed, and the symbol is never a known callee: `boxOf` is consulted before the known
  function paths in `value`, in calls, and in type applications. (The guards `symbol.isVar andif ... l.captured` at
  the binding and its uses become "is boxed".)
- **Using** a slot of the same input loads the box's component; closures capture the box, as they capture a
  local `var`'s. A box's loads are ordinary loads of a `var` cell, never marked invariant (value-numbering.md
  §2.2), so the passes treat them as they treat a captured `var`'s, within functions and at the top level.
- **The record** holds the boxes: member `v<slot>` is the box, named by the slot's id, so `lower.Earlier` is keyed
  by slot (`earlierBinding` maps a symbol through `env.slots`). `Earlier` gets `boxed: Bool`: a boxed binding is
  read by `opModuleMember` of the record and a component load, written (a `var` assignment, or a redefinition) by a
  component store; an unboxed one (a file's or `-e`'s unit, unchanged) as today.
- **Redefining** a slot of an earlier input stores to that input's box and adds no member; of the same input, stores
  to the local box. `session.boundSymbols` skips marked bindings, and `session.earlier` is keyed by slot.
- `lowerPhrases` boxes only when `env.interactive` holds, so `quest FILE` and `-e` lower exactly as now.

What this costs: a top-level function of interactive code is called through its closure, not inlined, specialized,
or called directly (decision 3). Polymorphic slots take the generic path a record member already takes (jit.md §6).

### 3.4. The JIT session

Nothing new: a redefinition's store to an earlier input's box stays when the input fails (decision 5), as a `:=` to
an earlier `var` does, and a failed input's own record is never made.

### 3.5. The drivers

The self-hosted driver (`options.interactive` in `driver/main`) and the bootstrap's set `env.interactive` for the
REPL and for `-i`'s file, under `QUEST_REDEFINE=1` until step 3; never for `-e` or a file run without `-i`. The REPL's
output is unchanged: a redefinition echoes as a `let` does.

## 4. What Does Not Change

- **Programs.** Nothing outside interactive mode: the lowering, the passes, the goldens.
- **Types.** `Let T = ...` again shadows. A function whose type names the old `T` is redefinable only with the old
  `T`; redefined with the new one, it shadows (its type differs), with the warning. Redefinition of types would need
  descriptors and layouts to agree, and is out of scope.
- **Modules and interfaces** declared in inputs: a module declared again replaces the first, as now (repl.md §5). A
  module's body is closed (it cannot name the bindings around it), so no module names a slot, and a module's members
  are never slots.
- **`exception E end`** is a declaration, not a `let`; it shadows, as now. `let e = exception e: String end` is a
  `let` of type `Exception(String)`, a slot, so it is redefinable and old handlers catch the new exception.
- **Side effects** of a failed input, other than its redefinitions, stay (repl.md §5).

## 5. Testing

- `tests/repl/redefine.quest`: a function redefined and its earlier caller sees it; a `var` and a non-`var` value
  redefined; `let rec` redefined (old callers reach the new body); mutual recursion across inputs; a polymorphic
  function redefined; a group member redefined and `let x = 2 and y = x`; a local that shadows a slot's name inside
  a function, unaffected; a redefinition with another type shadows, with the warning, and one with a `var` for a
  non-`var` likewise; a module declared twice.
- `tests/repl/redefine_rollback.quest`: an input that redefines two slots and then raises leaves both redefined, as
  a `:=` before the raise is left; one that redefines a function with a closure of its own new bindings, then raises,
  leaves the function callable.
- `tests/repl/redefine_load.quest` with a file in `tests/repl/files/`: a function of the `-i` file redefined, and a
  function of the file that calls it sees the new one.
- `tests/repl/rollback.quest` changes: after `let a = 99; 1 / 0` fails, `a` is 99, not 10;
  `let x = 1; let f(): Int = x; let x = 2; f() + x` becomes 4, and after `let x = 3; 1 / 0` fails, 6, since the
  redefinitions stay.
- The run goldens through `--backend jit-files` and `tests/eval` through the JIT: unchanged, since neither is
  interactive. Both hosts (`QUEST_BACKEND=c` and `arm64`), as jit.md §5.
- The cost of decision 3, for the record: jit.md §6's loops (200 million calls of `add1`, 100 million of `twice`)
  typed at the REPL, before and after, noted in repl.md's section on redefinition.

## 6. Later

- **Warning about shadowing within one scope in programs** (`let s = ...; let s = strip(s)` in a block, or two
  top-level `let x`s in a file). Legal in Cardelli's system, and a style some code may use; a warning would be a lint,
  not a semantic matter, and would need a count of how often the tree does it before being turned on. A tasklist
  item, if wanted, after step 1 counts the occurrences in `lib/`, `questlang/`, and the tests.
- Redefining a function with a different type, by giving a slot a new type and recompiling nothing: the earlier
  callers would need a run-time check or a recompilation, which is the hot-swapping the roadmap dropped.
- Redefining types, with the descriptors interned by the runtime (jit.md §3.6) checked for agreement.
- Direct calls and inlining of slots whose definition has not changed, undone when it does: the JIT would need to
  keep each input's IR and the dependents of each slot. Only if decision 3's cost matters in practice.

## 7. Steps

Each step ends with tools/check passing and its documentation.

1. **Checker and interpreters** (§3.1, §3.2, §3.5), in both compilers, behind `QUEST_REDEFINE=1`: slots in the
   environment, `redefines` on the typed let, the warning, in-place redefinition, the drivers' flag.
   The transcripts of §5 with `@env QUEST_REDEFINE=1`, marked to be skipped on the JIT (jit.md §5's marker) until
   step 2. *Done when:* the new transcripts pass in the bootstrap's REPL and the self-hosted one under `--no-jit`, and
   no existing golden changes.
2. **The JIT** (§3.3, §3.4): boxed slots, `Earlier.boxed`, redefinition stores; the markers
   come off the transcripts. *Done when:* the transcripts pass on the JIT in a C-built and an arm64-built driver, and
   the run and `-e` goldens through the JIT are unchanged.
3. **Default, and the documents.** The measurement of §5, for the record; then the REPL and `-i` redefine always,
   `QUEST_REDEFINE` and the transcripts' `@env` lines go (decision 7), and the `rollback` golden is updated. The
   documents: repl.md gains a section on redefinition (the rule, the warning, rollback, the cost); jit.md §1's
   "lexical semantics" decision and §3.2 are revised for slots and boxes; ir.md §3's phrase unit mentions the boxes;
   interpreter.md's scoping of REPL bindings; type-system.md §4 notes the interactive rule beside the shadowing
   rule; roadmap.md's step 7 drops "lexical semantics"; README.md's "Known Differences from *Typeful Programming*"
   gets an item: the paper's top level is lexically scoped, and here an interactive redefinition of a name at the same
   type updates it in place, for programs nothing changes; and this plan is deleted. *Done when:* tools/check passes
   and the documents describe the behavior.
