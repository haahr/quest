# Plan: Improving the SSA and Native Backend

A review (2026-10-30, after [arm64.md](arm64.md) step 11) of `questlang/ssa/`, `questlang/codegen/regalloc`,
`questlang/codegen/arm64/`, and `questlang/codegen/ssac`, as an expert compiler engineer would read them, turned into
a plan. Its priorities, in order:

1. **Clarity and readability.**
2. **The ability to add optimizations.**
3. **Long-term maintainability and flexibility:** other targets (x86-64, LLVM, WASM), and a precise collector's stack
   maps.
4. **The performance of the compiler itself.**

The code is careful and well commented, and its design (block arguments, the `ssac` oracle, linear scan on SSA, the
verifier) is sound. Its weaknesses are structural: dispatch on strings rather than options, no machine-level
representation between the SSA and the assembly text, analyses that each pass recomputes for itself, no pass
pipeline, and no way to test one pass on its own. Each is cheap to fix now and costly once more passes and targets
depend on it.

This plan changes how the backend is written, not what it compiles: every step keeps the generated programs'
behavior, and every step but those that say otherwise keeps the SSA's goldens.

---

## 1. Decisions

- **The SSA stays one target-independent representation,** with one `Opcode` option. It is not parameterized by a
  target's operations, and targets' operations are not subtypes of a shared subset (§3.8). What is specific to a
  target happens after the SSA, in instruction selection.
- **Each target has its own machine instructions,** an option of its own (`arm64.Op`), cased on without `else` by
  that target's selection, printer, and encoder only.
- **Shared machine-level code is structural:** register allocation, liveness, parallel moves, frames, and branch
  relaxation see each machine instruction's operands and a small shared kind, never its opcode (§3.8), as the SSA's
  structural passes see only its arrays (arm64.md §3.15).
- **Cases are exhaustive.** A `case` on an option of the backend's (an opcode, a terminator, a representation, a
  machine instruction) has no `else`, so that a new case is a type error wherever it is not handled. Strings are
  for names and text, not for kinds.
- **Analyses are shared, and passes run in a pipeline** that can dump, verify, and skip each one (§3.3).
- **Each pass is tested on its own** through the SSA's textual form, read as well as printed (§3.4).
- **The bootstrap is unaffected:** it has no SSA. Where a change reaches the self-hosted IR (§3.2), the IR's printed
  form, and so its goldens, stay as they are.

## 2. What the Review Found

### 2.1. Clarity and readability

1. **A stale header:** `codegen/arm64/codegen.int.quest` still describes the trivial allocator and a `try` through
   `_setjmp`, both replaced (arm64.md steps 8 and 11).
2. **Instructions built field by field:** `nodes` has no constructors for `slot`, `realConst`, or a symbol plus an
   offset, so the builder spells out all ten fields of `Inst` in at least eight places; `call`, `callNarrow`, and
   `callWithMemory` cover some combinations of `pairs`, `narrow`, and `memory` and not others; `none` and `noMemory`
   are the same array.
3. **`ssa/build` is 2,744 lines:** representations, variables, atoms and descriptors, primitives, calls, aggregates,
   conversions, statements, function-type adapters, static data, and the unit.
4. **Dispatch on strings:**
   - the SSA's parts of a value come from C's type names (`parts` compares `layout.representation` with `"QInt"`,
     `"QBool"`, `"QRecordVal"`, ...);
   - conversion plans' kinds, shapes' kinds, access modes, and primitive operators (`"+"`, `"<<"`) are compared as
     strings in `if`/`elsif` chains;
   - registers are strings, memory is `""`, and a register's class is its name's first letter;
   - branch relaxation parses the assembly text it emitted.
5. **`else` arms that defeat exhaustiveness:** `codegen.compute` compiles any opcode it does not name as a copy, so a
   new opcode would be miscompiled silently; the verifier, `promote`, and `tailCalls` end their cases with `else ok`.
6. **Long functions:** `promoteFunction` (about 300 lines), `regalloc.allocate` (about 220: liveness, numbering,
   intervals, the scan, and the result), `codegen.function` (about 130).
7. **Smaller points:**
   - `codegen` defines two types named `Place`;
   - a variable's binding is spread over five maps (`handlerVars`, `values`, `pointers`, globals, `slots`), and the
     order `read` consults them in is its meaning;
   - closures' and records' fields are read at literal offsets 0 and 8 in places (`typeApp`, `moduleMember`) and
     through `runtimeLayout.offset` elsewhere;
   - `statics` writes a descriptor's words in a fixed order rather than at its fields' offsets.

### 2.2. Adding optimizations

1. **No shared analyses:** dominance lives in the verifier; `promote` computes dominance frontiers and has its own
   list of a terminator's targets; `regalloc` computes liveness; `tailCalls` has its own escape analysis; the
   builder's `finish` rewrites targets by hand. The next pass would copy each again.
2. **No pipeline:** `buildUnit` runs `promote` and `tailCalls` itself, so the SSA cannot be dumped between them, a
   pass cannot be turned off, and the verifier does not run after each.
3. **No reader for the textual SSA:** a pass is tested by building SSA in Quest by hand (`regalloc_scan`) or through
   whole programs, never as input SSA and expected output SSA.
4. **Calls carry no attributes:** dead code elimination, value numbering, hoisting, and entering fewer handlers
   (arm64.md §6) need to know which calls are pure, read memory only, may raise, allocate, or do not return. The
   builder names about sixty runtime functions inline, each call restating its argument and result types.
5. **Thread-locals are `opSymbol`s,** though their address is a call that clobbers registers; the arm64 backend
   recognizes them by name in three places (the allocator's clobbers, rematerialization, `asm.addressOf`), and any
   pass that treats a symbol's address as a constant would be wrong for them.
6. **Instructions have no identity:** an instruction is its position in its block's vector, so a pass that inserts or
   deletes rebuilds vectors (`promote` does twice), and nothing maps a value to its definition. Every instruction also
   carries the fields of loads (`width`, `signed`) and calls (`pairs`, `memory`, `narrow`).
7. **Coarse limits,** acceptable now, to revisit with the analyses: `promote` skips every function that enters a
   `try`, and `tailCalls` marks none in a function where any slot's address escapes.

### 2.3. Flexibility: other targets and a precise collector

1. **No machine IR:** the arm64 backend goes from the SSA and its allocation straight to text. Instruction selection
   (arm64.md §3.5 describes machine SSA over virtual registers), peepholes, scheduling, relaxation without parsing,
   and the JIT's encoder (roadmap step 7) all need machine instructions as data.
2. **No target description:** the scratch registers (`x9`, `x10`, `x11`, `x16`, `x17`) are spelled throughout
   `codegen`; the allocator has no fixed-register constraints or hints, so `x0` to `x11` are never allocated and every
   call shuffles its arguments. arm64 can afford that; x86-64, with 16 registers, cannot.
3. **The C ABI as loose fields:** `pairs`, `memory`, and `narrow` on each call and function, and `main` recognized by
   its name in both native backends (`sxtw` in arm64, `(int)` in `ssac`). WASM's `call_indirect` and LLVM's function
   types need a signature as a value, and arm64.md §6's calling convention of Quest's own needs a place to live.
4. **Derived pointers pass through `int`:** `offsetPtr` and `indexPtr` are `ptrToInt`, `add`, `intToPtr`, so every
   field's address is briefly an integer, which a precise or moving collector would lose.
5. **`try` is defined by `_setjmp`** ("resumes as `_setjmp` returns a second time", ssa.md §3), which WASM cannot
   express; its meaning is control flow, which every target can implement its own way.

### 2.4. The compiler's performance

1. **Opcodes allocated at each use:** `option opAdd of ssa.Opcode end` throughout, though arm64.md §3.15 says to make
   each once, as a constant.
2. **Recursion over the dominator tree:** `promote`'s `rename` recurses, against §3.15's "iteration, not recursion";
   a large function's tree is deep, and compiled Quest uses about 2 KB of stack a call.
3. **Text built by concatenation:** every assembly line is a string, joined at the end; relaxation rescans every line
   with a map of label strings each round; the SSA printer's `values` is quadratic in `<>`.
4. **Linear searches:** the verifier's `dominates` walks the dominator chain for every use; the allocator's
   `calleeUsed` compares strings over registers, values, and pieces, and `blocked` scans every handler for every
   interval; the builder keys dense variable ids through hash maps.

### 2.5. The verifier's gaps

It does not check a tail call's results against its function's, calls' result counts and types, a load's width and
signedness against its result, a store's value against its width, `pairs`, `narrow`, and `memory` indices, or a
`switch`'s duplicate cases; and it compares types by their names.

## 3. Design

### 3.1. Cleanups

- **Constructors in `nodes`** for every instruction (`slotAddress`, `realConstant`, `symbolPlus`, ...), so that no
  other module writes an `Inst` tuple; one `call` taking the call's signature (§3.5); opcodes and terminator kinds
  made once, as constants of `nodes`.
- **No `else`** in a case on `Opcode`, `Terminator`, or any option of §3.2: the verifier checks each opcode's
  arguments and results, and `codegen` names every opcode it copies.
- **`ssa/build` split by concern:** `build/values` (representations, variables, atoms, words), `build/descriptors`,
  `build/calls`, `build/aggregates` (tuples, records, options, variants, arrays, conversions), `build/control`
  (statements, `try`, `switch`, `inspect`), `build/adapters` (function-type adapters, exported functions), and
  `build/unit` (static data, initializers, `main`).
- **A variable's binding as one option** (`bindValues`, `bindSlot`, `bindPointer`, `bindGlobal`, `bindHandler`), in
  one table, so that `read` and `write` are a `case`.
- **Every runtime offset through `runtimeLayout`,** and `statics` placing each word at its field's offset.
- **Iteration, not recursion,** in `promote`'s renaming (an explicit stack of blocks and saved definitions).

### 3.2. Options rather than strings

- **Representations:** `layout` gains a `Representation` option (`repVoid`, `repInt`, `repWord`, `repBool`,
  `repChar`, `repReal`, `repRecord`, `repVariant`, `repPointer`, `repQVal`), which the SSA's builder cases on; the C
  printer spells each as C (`codegen/c/types`). `layout.representation`'s strings remain only as that spelling.
- **The IR's kinds:** conversion plans' kinds, shapes' kinds, access modes, catch modes, and primitive operators
  become options in the self-hosted IR. The IR's printed form, and so its goldens, are unchanged; the bootstrap keeps
  its strings.
- **Registers:** a target numbers its registers; a register is an `Int` (or, in a machine instruction, an operand of
  §3.8), with its class and name from the target description, and memory is not a register.

### 3.3. Analyses and the pipeline

- **`ssa/cfg`:** predecessors, successors, reverse postorder, the dominator tree (with preorder and postorder
  numbers, so that `dominates` is two comparisons), dominance frontiers, and loop nesting.
- **`ssa/liveness`:** live-in and live-out sets, which `regalloc` and later passes use.
- **`ssa/uses`:** each value's definition (block and index, or block parameter) and its uses, or a count of them.
- **Mutators in `nodes`:** `targets` (a terminator's targets, changeable in place), `mapTargets`, `replaceUses`, and
  inserting and removing instructions without each pass rebuilding vectors itself.
- **`ssa/pipeline`:** the SSA's passes by name (`promote`, `tailCalls`, and those to come), run in order after the
  builder. `--dump-after` takes their names, as it takes the IR's (pipeline.md); `QUEST_CHECK_IR=1` verifies after
  each; a pass can be left out for a test or a bisection.
- **The verifier closes §2.5's gaps,** and compares types as options.

### 3.4. Reading the textual SSA

`ssa/reader` parses what `ssa/printer` prints (ssa.md §6) into a unit, so that `read(print(u))` prints as `u` does.
Tests of a pass are then a directory of `.ssa` inputs with their expected outputs, run by a questlang test that reads
each, runs the pass (and the verifier), and prints; and a bug found in a program can be cut down to the SSA that
shows it. The goldens are the self-hosted compiler's (testing.md §2.8).

### 3.5. Signatures and runtime functions

- **A signature as a value:** for each parameter and result, how C passes it: a word, a real, the first or second
  half of a 16-byte composite, a byte (`narrow`), a 32-bit integer, or a composite through memory of so many bytes.
  It replaces `pairs`, `memory`, and `narrow` on calls and functions; `main`'s `argc` is a 32-bit integer in its
  signature, not a name both backends recognize; `placeArguments` and `ssac`'s call types read it. It is where
  arm64.md §6's calling convention of Quest's own would be recorded, and what a WASM or LLVM backend needs for its
  function types.
- **A table of the runtime's functions** (`codegen/runtimeFunctions`): each one's name, signature, and attributes:
  pure, reads memory only, may raise, allocates, does not return. The builder calls them through the table, never
  naming a signature again; optimizations read the attributes; a test checks each signature against
  `quest_runtime.h`, as `codegen_runtime_layout` checks the structs.

### 3.6. New opcodes

- **`ptrAdd`** (`ptr int → ptr`): a pointer plus a byte offset, for every field's, element's, and slot's address, so
  that a derived pointer is always a `ptr` (§2.3), and instruction selection can fold it into an addressing mode.
  `ptrToInt` and `intToPtr` remain for what is truly an integer (a proxy's tag bit, a `QVal` word).
- **`threadLocal`** (`→ ptr`): a thread-local's address, which the arm64 backend computes by calling its accessor and
  `ssac` takes with `&`; it is not rematerialized and it clobbers what a call clobbers, without any list of names.
- **`try` defined by its control flow** in ssa.md: control enters the body; an exception raised in it, or in what it
  calls, transfers to the handler with the values that dominate the `try`; `_setjmp` and the native handler record
  are two implementations of it.

### 3.7. A target description

`codegen/target` describes a target to the shared machine-level code: its registers (numbers, classes, names), which
are allocatable, caller-saved, and callee-saved, its argument and result registers by class, its scratch registers,
its stack alignment, and its word size. `codegen/arm64/target` is the first; nothing outside a target's own modules
names a register.

### 3.8. Machine instructions

**Not a parameterized SSA, and no shared subset of opcodes.** Each target's operations are an option of its own.
Making them subtypes of a shared option (copies, arithmetic, allocation) fits Quest badly: an option with fewer cases
is the subtype, so a shared subset would be a subtype of each target's option, not a supertype a target extends; a
pass generic over "some target's operations" would need a bounded type parameter, which compiled Quest implements
with view maps and tag maps at run time (the cost §3.15 keeps out of inner loops); and a shared pass casing on the
subset would need `else` for the rest.

**Three layers instead:**

1. **The SSA,** target-independent, as now.
2. **A target's machine instructions** (`codegen/arm64/minst`): `arm64.Op`, an option of the target's operations with
   their immediates, conditions, and addressing modes, made by instruction selection over virtual registers and cased
   on only by that target's selection, printer, and encoder.
3. **Shared machine-level code over a structural shape** (`codegen/machine`): a machine function's blocks hold
   instructions, each with its operands (each a virtual or physical register, used or defined, with a fixed-register
   constraint or a hint where the ABI requires one) and a shared kind (`kindOrdinary`, `kindMove`, `kindJump`,
   `kindBranch`, `kindCall`, `kindReturn`); the target's `Op` sits in a table beside them, indexed by instruction, which
   shared code never reads. The register allocator, liveness over virtual registers, parallel moves, frame layout,
   and branch relaxation work on that shape; when they must make an instruction (a move, a spill, a reload, a jump),
   they ask the target, through a record of its functions.

**The arm64 backend becomes:** selection (SSA to `minst` over virtual registers, with arm64.md §3.5's patterns:
immediates, fused comparisons, addressing modes, `ptrAdd` folded); allocation on the machine function, with
constraints at calls, returns, and parameters and hints that coalesce block arguments' moves; frames; relaxation on
instructions, not text; and a printer to assembly text. An encoder to bytes (roadmap step 7) is then another consumer
of `minst`, testable instruction by instruction against the assembler. An x86-64 backend would be a selection, a
printer, and a target description, reusing everything in `codegen/machine`.

### 3.9. The compiler's performance

Measured before and after (compile times of the driver build and of `arm64_assemble`, recorded in benchmarks.md with
their dates): opcodes as constants (§3.1); assembly written through a string builder; the SSA printer through one;
`dominates` by tree numbers (§3.3); the allocator's registers as integers (§3.2) and its handler and call lists
searched by position; the builder's per-variable tables as arrays where variable ids are dense.

## 4. Testing

- **Every step:** `tools/check` before a push, with every backend mode; generated programs' behavior unchanged.
- **The SSA's goldens** change only in steps that say so (§3.5's signature in the printed form, §3.6's opcodes), and
  then by regeneration reviewed in the diff.
- **Per-pass goldens** (§3.4) for `promote`, `tailCalls`, and each pass to come, and for the verifier's new checks
  (malformed SSA in, its problems out).
- **The runtime functions' table** checked against `quest_runtime.h` (§3.5).
- **The machine layer:** `regalloc_scan`'s cases on machine functions, with a toy target description; selection's
  patterns through goldens of `arm64_asm` dumps for a curated set (arm64.md §3.2).

## 5. Steps

Each step lands on its own and passes `tools/check`; the plan interleaves with arm64.md's steps 12 to 15, which touch
the same modules, so each step starts from a fresh rebase.

1. **Cleanups** (§3.1): the stale header, `nodes`' constructors and opcode constants, no `else` on the SSA's options,
   one `Place`, offsets through `runtimeLayout`, `statics` by field offsets, iterative renaming. *Done when* no module
   but `nodes` writes an `Inst` tuple, no case on `Opcode` or `Terminator` has `else`, and the SSA's goldens are
   unchanged. *Done* (2026-10-30, d34627bc): passes that single out one opcode test it with `isOp`, where a default is
   conservative; every case on `Opcode` and `Terminator` names each.
2. **Options for kinds** (§3.2): `layout`'s representations, the IR's plan, shape, access, and catch kinds and
   primitive operators. *Done when* the SSA's builder compares no kind as a string, and the IR's and SSA's goldens are
   unchanged. *Done* (2026-10-30, b8f5d9fc): `Access`, `Catching`, `Prim`, `PlanKind`, `shapes.ShapeKind`, and
   `layout.Representation`. Two kinds stay strings, outside §3.2's list: `codegen/staticdata`'s descriptor forms
   (`base`, `bound_var`, `fun`, ...), codegen's own and shared with the C printer, and functions' parameter modes
   (`value`, `var`, `out`).
3. **The builder split** (§3.1), with variables' bindings as one option. *Done when* `ssa/build` is the modules of
   §3.1, none over about 800 lines, and the goldens are unchanged. *Done* (2026-10-30, 4aaf6e9a): seven modules in
   `questlang/ssa/build/` (imported as `vals` and `units` where locals are named `values` and `unit`), the largest
   790 lines; tuples went to `aggregates` and modules' members to `calls`.
4. **Analyses and the pipeline** (§3.3), with `promote`, `tailCalls`, and `regalloc` using them, and the verifier's gaps
   closed. *Done when* no pass computes dominance, liveness, or a terminator's targets itself, `--dump-after promote`
   works, and `QUEST_CHECK_IR=1` verifies after each pass. *Done* (2026-10-30, f68cedd8): `ssa/cfg`, `ssa/liveness`, and
   `ssa/pipeline`; the dump phases are `ssa_built`, `ssa_promote`, and `ssa_tailCalls`, as the IR's are `ir_NAME`, and
   `QUEST_SKIP_PASSES` leaves passes out. `ssa/uses` waits for the first pass that needs it: the verifier finds bad
   definitions itself.
5. **The SSA reader and per-pass goldens** (§3.4). *Done when* every SSA golden round-trips, and `promote` and
   `tailCalls` have goldens of their own. *Done* (2026-10-30, 7da9edda): the reader is `ssa/parser`, since the standard
   library has an interface `Reader`; with `QUEST_CHECK_IR=1` the driver reads back every SSA it prints. The goldens
   of `promote` and `tailCalls` are the questlang tests `ssa_promote` and `ssa_tailcalls`, SSA written as text.
6. **Signatures and the runtime functions' table** (§3.5). *Done when* calls and functions carry signatures, no backend
   recognizes `main` by name, and the builder names no runtime function's signature itself. *Done* (2026-10-30,
   a6db41fb): `ssac` still recognizes `main`, only to spell its argument array `char **`, as C requires; the table found
   that `quest_record_box`'s and `quest_variant_box`'s struct had not been marked a pair.
7. **`ptrAdd`, `threadLocal`, and `try` by control flow** (§3.6). *Done when* no derived pointer passes through
   `int`, no backend keeps a list of thread-locals' names, and ssa.md defines `try` without `_setjmp`. *Done*
   (2026-10-30, 8130949e).
8. **The target description and machine instructions** (§3.7, §3.8): `codegen/target`, `codegen/machine`,
   `codegen/arm64/minst`, selection, the allocator on machine functions with constraints and hints, relaxation on
   instructions, and the printer. *Done when* the arm64 backend emits text only in its printer, `regalloc` reads no
   register names, the suite passes in every mode, and benchmarks.md records run and compile times before and after.
   This step subsumes most of arm64.md §6's list of what step 11's code does badly (immediates, fused branches,
   rematerialized arguments, blocks that only jump).
9. **The compiler's performance** (§3.9). *Done when* each change's compile time is recorded in benchmarks.md, and the
   ones that do not pay are reverted.

## 6. Not Part of This Plan

- **Other backends** (x86-64, LLVM, WASM): this plan makes them a target description, a selection, and a printer
  (x86-64), or a printer of the SSA with signatures (LLVM, WASM); WASM would also need `try` through its exception
  handling, slots on a shadow stack, and precise roots, since it cannot scan its stack.
- **A precise collector's stack maps:** after this plan, each value's type is known through allocation, derived
  pointers are `ptr`s, and a spilled value has a slot of its own, so maps at calls are a frame-layout addition.
- **Optimizations** themselves (arm64.md §6), which this plan prepares for.
