# The SSA

The self-hosted compiler's low-level, target-independent intermediate form for its native backends
([arm64.md](arm64.md) §3.2): built from the described IR ([ir.md](ir.md) §8.4), printed as C by `ssac` (arm64.md
§3.14), and lowered to arm64. Its values are machine scalars, not Quest values; memory is reached by byte offsets; a
block's arguments stand for φ nodes. The bootstrap has no SSA.

---

## 1. Values and Types

A function numbers its **values** densely from 0; a value is an instruction's result or a block's parameter, defined
once. Each has a type:

| Type | What it holds |
|---|---|
| `int` | a 64-bit integer: `Int`, `Word`, `Bool` and `Char` (extended to 64 bits: `Bool` 0 or 1, `Char` 0 to 255), a tag, a size, an offset |
| `ptr` | a pointer the collector must see: a heap object, a closure, a descriptor, a static object, a stack slot's address |
| `real` | a 64-bit IEEE double |

There is no aggregate type: a 16-byte value (a record's `QRecordVal`, a variant's `QVariantVal`) is two values. There
is no boolean type: a comparison gives an `int` 0 or 1, and a branch tests an `int` for nonzero. `ptr` and `int` are
apart so that a later collector could find pointers precisely (arm64.md §3.13); converting between them is explicit.

## 2. Instructions

Every instruction has one shape (arm64.md §3.15): an opcode, an array of argument values, an array of result
values, an immediate integer, and a symbol. Passes that care only about structure (the verifier, liveness, renaming,
register allocation) walk the arrays; only the passes that care what an instruction means case on its opcode.

| Opcode | Arguments → results | Meaning |
|---|---|---|
| `const` | → `int` | the immediate |
| `realConst` | → `real` | the double whose bits are the immediate |
| `symbol` | → `ptr` | the address of the symbol (static data, a function, a runtime global), plus the immediate in bytes |
| `null` | → `ptr` | the null pointer |
| `slot` | → `ptr` | the address of the stack slot numbered by the immediate |
| `add`, `sub`, `mul` | `int int` → `int` | wrapping arithmetic ([type-system.md](type-system.md) §6.3.1) |
| `div`, `rem` | `int int` → `int` | signed, truncating; the divisor is neither 0 nor -1 (the SSA's builder tests both first) |
| `and`, `or`, `xor`, `shl`, `lshr`, `ashr` | `int int` → `int` | bitwise; shift counts are 0 to 63 |
| `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `ult` | `int int` → `int` | comparisons, signed but for `ult` |
| `peq`, `pne` | `ptr ptr` → `int` | pointer identity |
| `fadd`, `fsub`, `fmul`, `fdiv` | `real real` → `real` | IEEE arithmetic |
| `feq`, `flt`, `fle`, `fgt`, `fge` | `real real` → `int` | IEEE comparisons |
| `isNaN` | `real` → `int` | whether the double is a NaN |
| `intToPtr`, `ptrToInt` | → | a pointer's bits as an integer, and back (a proxy's tag bit, a `QVal` word) |
| `realBits`, `bitsReal` | → | a double's 64 bits as an integer, and back |
| `sext8`, `zext8` | `int` → `int` | the low byte, sign- or zero-extended (a C `bool` or a `QChar`, an unsigned byte, received: `zext8`) |
| `load` | `ptr` → value | the immediate is the byte offset; the width and the result's type are the instruction's (§2.1) |
| `store` | `ptr value` → | likewise |
| `call` | args → results | a direct call of the symbol |
| `callIndirect` | `ptr` args → results | a call through a function pointer |
| `copy` | value → value | the same value (made by the builder; removed by later passes) |

### 2.1. Loads and Stores

A load or store names its width: 8 bytes (an `int`, `ptr`, or `real`), 4 (a C `int`, read sign-extended), or 1 (a C
`bool` or a `QChar`: read zero- or sign-extended, as the instruction says; both are zero-extended now, since a `Char` is
an unsigned byte, arm64.md §10.4). Its address is its pointer argument plus the
immediate.

### 2.2. Calls

A call's arguments and results are values in the order of the C function's parameters; an `Ok` argument, which has no
values, is a zero word, since C passes `Q_OK_VAL` to the `QVal` parameter a function declares for it. The call records,
for the native backend's ABI lowering, where a 16-byte composite (a `QRecordVal`, a `QVariantVal`) starts: AAPCS64
passes one in two consecutive registers or wholly on the stack, never split. A composite larger than 16 bytes, which C
passes through memory (a `QExceptionState`, to `quest_reraise`), is a stack slot whose address the builder passes, and
the call records the argument among its `memory` arguments: AAPCS64 passes such a composite as the address of a copy,
and `ssac` passes the copy's contents. A call also records which arguments C passes as one byte (`narrow`: a `bool` or a
`char`, from a `Bool` or a `Char`), which Darwin's AAPCS64 packs on the stack, a byte each, where it passes others in 8
aligned bytes; a function records its own (`paramNarrow`), and extends them on entry, since a C caller leaves their
upper bits unspecified. A C `bool` or `QChar` result is extended by a `zext8` after the call, since AAPCS64
leaves a narrow result's upper bits unspecified; a function that returns such an extension of a call's result can make
the call in tail position, since its own caller extends it again. A call of a function that does not return (a raise)
ends its block with `unreachable`.

## 3. Blocks and Control

A function's **blocks** are numbered from 0, the entry first. A block has parameters (values), instructions, and one
terminator:

| Terminator | Meaning |
|---|---|
| `jump b(args)` | continue at block `b`, its parameters bound to the arguments |
| `branch v, b1(args), b2(args)` | `b1` if `v` is nonzero, else `b2` |
| `switch v, [k: b(args)...], default b(args)` | the block of the case whose integer is `v` |
| `return values` | return the values (none, one, or two for a 16-byte result) |
| `tailCall` | a call in tail position (arm64.md §3.7, marked by `ssa/tailCalls`): its results are the function's |
| `try slot, body(args), handler()` | enter a `try` (below) |
| `unreachable` | control does not reach the end of the block |

**`try`.** A `try` enters an exception handler (its record a stack slot, the immediate, which the builder has pushed on
the runtime's chain, `quest_current_exception_handler`, with what it catches) and goes on to its body block;
when an exception is raised in the body, or in anything the body calls, control resumes at the handler block, as
`_setjmp` returns a second time. The handler block's one predecessor is the `try`'s block, so dominance gives the
rule the handler's resumption needs (arm64.md §3.6): the values a handler uses were defined before the `try`. A mutable
variable assigned in a `try`'s body lives in a stack slot, not in values, as C makes it `volatile`. Every way out of
the body (falling off its end, a jump, a return) first leaves the handler (`call` of the runtime, or the native
handler's pop), as the C printer pops it.

## 4. Building the SSA

`questlang/ssa/build` builds a unit's SSA from its described IR (thunks included, [ir.md](ir.md) §8.4.1), doing for
each operation what the C printer prints ([arm64.md](arm64.md) §7.2). Its modules, in `questlang/ssa/build/`, each
use only those before them: `values` (representations, the builder's state, emitting, variables, atoms, words, and
aggregates' components), `descriptors`, `calls` (primitives, calls, and modules' members), `aggregates`
(conversions, tuples, records, variants and options, arrays, and type applications), `control` (operations and
statements), `adapters` (exported functions and function types' adapters), and `unit` (functions, static data,
registration, and the unit).

- **Variables.** Each variable has one binding (`values.Binding`): SSA values, a stack slot, the location a `var` or
  `out` parameter points to, a handler's copy of the exception state, or a global. An IR variable of a value is the
  SSA values of its representation; a boxed variable (a record or
  variant the represent pass holds in its box) is its box's pointer, and a boxed mutable one's value is its box's
  record or variant. A **mutable variable is a stack slot**, loaded and stored, as C at `-O0` keeps it: always
  correct, the rule `try` needs for free, and promoted to values afterwards (§4.1). A variable a top level binds
  outside loops is a global (`g_<name>`), as in C, however it is bound: a join's parameter (the value of a
  top-level `if`, `case`, or `try`) is stored to its global at the join, as any binding is, so that the program's
  functions see it (once bound as a local, it left the global unset, which the compiler built by the arm64 backend
  found at once: `language/global_joins`).
- **Memory.** Every aggregate slot is a word (`layout`); a box or a global holds a record or variant's 16 bytes; a
  location (a cell, what a `var` or `out` parameter points to) holds a record or variant as its box's pointer
  (`layout.shapeLocationRepresentation`). Offsets come from `codegen/layout`, `codegen/staticdata`, and
  `codegen/runtimeLayout`, which the C asserts.
- **Closures.** A closure's environment is the descriptors of its type arguments then its captures, a word for each
  of their values: private to the unit, which alone reads it ([arm64.md](arm64.md) §7.1). A call of a variable bound
  to a closure of one of the unit's functions calls the function directly, as the C printer does.
- **Thread-locals.** The handler chain and the current exception are the runtime's thread-local variables, which the
  SSA names as symbols; the native backend reaches them through their accessor (arm64.md §3.6).
- **Blocks the entry does not reach are dropped** when a function is finished, and the rest renumbered.

What the builder does not yet build raises `unsupported`, naming the construct; `--stop-after ssa` reports it as an
internal error.

### 4.1. The Pipeline: Promotion and Tail Calls

`questlang/ssa/pipeline` builds a unit and then runs its passes, by name, in order, each on every function:

- **`ssa/promote`** turns stack slots into values. A slot can be promoted when it is whole words and its address is
  only loaded from and stored to, a word at a time or a word's first byte (a `Bool` or `Char` variable's), never
  passed, stored, or offset otherwise. Each word becomes a variable of one type, stored all at one width, and loaded
  whole only if stored whole. A block that the definitions reaching it differ at gets a parameter (Cytron et al.'s
  placement at the iterated dominance frontier); then, along the dominator tree, a load becomes the value last
  stored, or, for a byte, its `zext8` or `sext8`, and one before any store reads a zero made in the entry. The slots
  left are renumbered. A function that enters a `try` keeps all its slots, since its handler must see what the body
  stored (arm64.md §3.6); a variable captured by a closure is a heap cell, and one passed as a `var` argument keeps
  its slot, its address escaping. `language/mutable_locals` covers each kind.
- **`ssa/tailCalls`** marks calls in tail position (§3, arm64.md §3.7).

Neither removes values that become dead, such as parameters no load reads; the trivial allocator gives them slots,
and linear scan none.

The passes share their analyses: `ssa/cfg` (predecessors, successors, reverse postorder, the dominator tree with
preorder and postorder numbers, dominance frontiers, and loop depths) and `ssa/liveness` (each block's live-in and
live-out values, which the register allocator uses); `nodes` has the mutators (`targets`, `mapTargets`, `mapBlocks`,
`replaceUses`). The driver dumps the SSA after the builder (`--dump-after ssa_built`), after each pass
(`ssa_promote`, `ssa_tailCalls`), and at the end (`ssa`); `QUEST_SKIP_PASSES`, a comma-separated list of passes'
names, leaves passes out, for a test or a bisection.

## 5. Functions and Units

A **function** has a symbol (its C name), whether other units call it, its parameters (the entry block's) with where
its 16-byte composites start (`paramPairs`, as a call's `pairs`: a function of two results returns one), its result
types, its blocks, and its stack slots (each a size and an alignment in bytes). A **unit** has its functions and its
**data**: each datum a symbol, whether other units refer to it, whether it is written at run time, and its contents,
8-byte aligned: zeros (a global, a module's record and its initialized flag), a C string's text and its NUL (a
literal, a name in a descriptor or the function table), or words, each an integer or a symbol's address plus a byte
offset (a descriptor and what its extra field points at, an offset table, a tag map, a static closure, the function
table). Words lay out the runtime's structs on a little-endian target, a narrow field in the low bytes of its word.

The builder makes, besides the IR's functions and the module initializers and `main`:

- the data of `ir.StaticData`'s descriptors (`ssa/statics`, from `codegen/staticdata`'s descriptions), offset
  tables, and tag maps, as the C printer's declarations define them;
- each function type's adapter, thunk, and invoker (`quest_adapt_<tag>`, `quest_thunk_<tag>`, `quest_invoke_<tag>`),
  as `codegen/c/declarations` writes them in C;
- a module file's exported functions (`qv_<module>_<member>`), at its interface's C signatures;
- the function table (`qr_funcs`) and `qr_register_dicts`, which registers it and the offset tables of records the
  unit views at supertypes;
- a static closure (`<function>_closure`) of each function, and the data of globals and strings.

What a unit refers to and does not define is another unit's or the runtime's; the runtime's thread-locals are
`runtimeLayout.threadLocals`.

## 6. The Textual Form

`--stop-after ssa` prints a program unit's SSA; its goldens (`tests/golden/ssa`) are the self-hosted compiler's own,
one for every run test that has an `ir_core` dump (arm64.md §3.2). Values print as `%n`, blocks as `bN`, a
function's stack slots as `bytes:alignment`, a load or store with its width (`load1s` sign-extends a byte), a call
with its `pairs` and `memory` arguments, and a function with its `pairs`; the unit's data follows its functions, a
datum per line (`data qs_1 text "add1"`, `data g_res writable zero 8`, `data qf_f_closure words [qf_f, 0]`):

```
function qf_f(%0: ptr, %1: int): int slots [16:8] {
b0(%0: ptr, %1: int):
  %2: int = const 1
  %3: int = add %1, %2
  return %3
}
```

`questlang/ssa/parser` reads the text back into a unit, values keeping their numbers, so that printing what it reads
prints what it read: with `QUEST_CHECK_IR=1` the driver reads back the SSA it prints and reports any difference, so
every golden is checked to read back as itself. A pass is tested on SSA written as text: the questlang tests
`ssa_promote` and `ssa_tailcalls` read small functions, run their pass and the verifier, and print the functions
before and after; and a program's SSA can be cut down to the functions that show a bug.

## 7. The Verifier

After the pipeline, and when `QUEST_CHECK_IR=1` after the builder and after every pass too, the verifier checks that
each value is defined once and its definition dominates its uses; that every instruction has the number and types of
arguments and results its opcode takes, a narrow load's result and a narrow store's value being ints; that a call's
`pairs`, `memory`, and `narrow` arguments are among its arguments, and a call of the unit's own function matches its
parameters and results; that jumps pass their blocks' parameters' number and types; that a switch's cases are
distinct; that returns and tail calls give the function's results; that each block ends in one terminator; that a
`try`'s handler has the `try`'s block as its only predecessor and no parameters; and that slots and blocks referred
to exist. The questlang test `ssa_verify` builds well-formed and malformed functions by hand and checks the problems
it reports.

## 8. The C Printer

`codegen/ssac` prints a unit's SSA as C (arm64.md §3.14), an oracle for the SSA and the backends after it: with
`--backend ssac`, or `--unit-backend UNIT=ssac` for one unit, a build compiles units through it (arm64.md §5, step
5). The questlang test `ssac_print` prints a unit built by hand, and `tests/python/test_ssac.py` compiles its golden.
