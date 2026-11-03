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
| `val` | a `QVal` word, whose pointer-ness its type descriptor says: a value of a type parameter, a variant's payload, an aggregate's component in its word form, an `Ok` passed as a word, and the runtime's `QVal` parameters and results |

There is no aggregate type: a 16-byte value (a record's `QRecordVal`, a variant's `QVariantVal`) is two values. There
is no boolean type: a comparison gives an `int` 0 or 1, and a branch tests an `int` for nonzero. `ptr` and `int` are
apart so that a later collector could find pointers precisely (arm64.md §3.13); converting between them is explicit.
`val` is apart from both for the same reason: a precise collector resolves a `val` by its descriptor
(arm64.md §3.13). A `val` is an `int` in registers, and `toVal` and `fromVal` convert it.

## 2. Instructions

Every instruction has one shape (arm64.md §3.15): an opcode, an array of argument values, an array of result
values, an immediate integer, a symbol, and a source position (`loc`: a file, by its number in the unit's `files`, a
line, and a column, or none), for the native code's line table (arm64.md §3.16). The builder gives each instruction
the position of the IR statement it builds (ir.md §5), or of the last one that had a position; a block's terminator has
one too (`termLoc`), and a tail call its call's. Passes that care only about structure (the verifier, liveness, renaming,
register allocation) walk the arrays; only the passes that care what an instruction means case on its opcode.

| Opcode | Arguments → results | Meaning |
|---|---|---|
| `const` | → `int` | the immediate |
| `realConst` | → `real` | the double whose bits are the immediate |
| `symbol` | → `ptr` | the address of the symbol (static data, a function, a runtime global), plus the immediate in bytes |
| `threadLocal` | → `ptr` | the address of the runtime's thread-local variable the symbol names, in this thread |
| `null` | → `ptr` | the null pointer |
| `slot` | → `ptr` | the address of the stack slot numbered by the immediate |
| `ptrAdd` | `ptr int` → `ptr` | the pointer plus a byte offset: every field's, element's, and slot's address |
| `add`, `sub`, `mul` | `int int` → `int` | wrapping arithmetic ([type-system.md](type-system.md) §6.3.1) |
| `div`, `rem` | `int int` → `int` | signed, truncating; the divisor is neither 0 nor -1 (the SSA's builder tests both first) |
| `and`, `or`, `xor`, `shl`, `lshr`, `ashr` | `int int` → `int` | bitwise; shift counts are 0 to 63 |
| `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `ult` | `int int` → `int` | comparisons, signed but for `ult` |
| `peq`, `pne` | `ptr ptr` → `int` | pointer identity |
| `fadd`, `fsub`, `fmul`, `fdiv` | `real real` → `real` | IEEE arithmetic |
| `feq`, `flt`, `fle`, `fgt`, `fge` | `real real` → `int` | IEEE comparisons |
| `isNaN` | `real` → `int` | whether the double is a NaN |
| `intToPtr`, `ptrToInt` | → | a pointer's bits as an integer, and back, for what is truly an integer (a proxy's tag bit); a derived pointer is a `ptrAdd`, so that it stays a `ptr` |
| `toVal`, `fromVal` | `int` or `ptr` → `val`, and back | a value as a `QVal` word, and a `QVal` word as the `int` or `ptr` its type says |
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
an unsigned byte, arm64.md §3.9). Its address is its pointer argument plus the
immediate.

### 2.2. Calls

A call's arguments and results are values in the order of the C function's parameters; an `Ok` argument, which has no
values, is a zero `val`, since C passes `Q_OK_VAL` to the `QVal` parameter a function declares for it. A call and a
function have a **signature** (`nodes.Signature`): how C passes each parameter and result, which the backends lower
the ABI by and `ssac` writes C's types from (`nodes.Passed`):

- a word (an integer or a pointer) or a real (a double);
- a **pair**, the two words of a 16-byte composite (a `QRecordVal`, a `QVariantVal`), which AAPCS64 passes in two
  consecutive registers or wholly on the stack, never split; two results are a pair;
- a **byte** (`narrow`: a `bool` or a `char`, from a `Bool` or a `Char`), which Darwin's AAPCS64 packs on the stack,
  a byte each, where it passes others in 8 aligned bytes, and leaves the upper bits of in a register;
- a **C `int`** (`int32`: `main`'s `argc` and result), which a function extends on entry;
- a composite of more than 16 bytes, passed through **memory** (a `QExceptionState`, to `quest_reraise`): a stack slot
  whose address the builder passes, as AAPCS64 passes the address of a copy, and whose contents `ssac` passes.

The runtime's functions' signatures, with their effects (what each does to memory, whether it may raise, allocates, or
never returns), come from the table `codegen/runtimeFunctions`, which holds each one's C prototype and is checked
against `quest_runtime.h`; a Quest function's come from its parameters' and results' representations. A function extends
its byte parameters on entry, since a C caller leaves their upper bits unspecified. A C `bool` or `QChar` result is
extended by a `zext8` after the call, since AAPCS64 leaves a narrow result's upper bits unspecified; a function that
returns such an extension of a call's result can make the call in tail position, since its own caller extends it again.
A call of a function that does not return (a raise) ends its block with `unreachable`.

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

**`try`.** A `try` is defined by its control flow: it enters an exception handler (its record a stack slot, the
immediate, which the builder has pushed on the runtime's chain, `quest_current_exception_handler`, with what it
catches), and control goes on to its body block; when an exception is raised in the body, or in anything the body calls,
control transfers to the handler block, with the values that dominate the `try`. How a backend implements the transfer
is its own: `ssac` calls `_setjmp`, which returns a second time, and the arm64 backend records a native handler's resume
address, stack pointer, and frame pointer; a WASM backend would use its exception handling. The handler block's one
predecessor is the `try`'s block, so dominance gives the rule the handler's resumption needs (arm64.md §3.6): the values
a handler uses were defined before the `try`. A mutable variable assigned in a `try`'s body lives in a stack slot, not
in values, as C makes it `volatile`. Every way out of the body (falling off its end, a jump, a return) first leaves the
handler (`call` of the runtime, or the native handler's pop), as the C printer pops it.

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
  record or variant. A **mutable variable is a stack slot**, loaded and stored, as C at `-O0` keeps it: always correct,
  the rule `try` needs for free, and promoted to values afterwards (§4.1). A variable a top level binds outside loops
  that a function or another top level names, or that is a module's member, export, or record (`walk.globalVariables`,
  [ir.md](ir.md) §8.2), is a global (`g_<name>`), as in C, however it is bound: a join's parameter (the value of a
  top-level `if`, `case`, or `try`) is stored to its global at the join, as any binding is, so that the program's
  functions see it (once bound as a local, it left the global unset, which the compiler built by the arm64 backend found
  at once: `language/global_joins`).
- **Memory.** Every aggregate slot is a word (`layout`); a box or a global holds a record or variant's 16 bytes; a
  location (a cell, what a `var` or `out` parameter points to) holds a record or variant as its box's pointer
  (`layout.shapeLocationRepresentation`). Offsets come from `codegen/layout`, `codegen/staticdata`, and
  `codegen/runtimeLayout`, which the C asserts.
- **Closures.** A closure's environment is the descriptors of its type arguments then its captures, a word for each
  of their values: private to the unit, which alone reads it ([arm64.md](arm64.md) §7.1). A call of a variable bound
  to a closure of one of the unit's functions calls the function directly, as the C printer does; when that function
  is an external's thunk (`qx_`, ir.md §8.4.1), which only forwards its arguments, the call is of the external C
  function itself, as the C compiler makes it by inlining the thunk. A call of an imported member that is one of the
  standard library's externals (`codegen/externals`) calls the C function, as the C printer's `libraryExternal` does.
- **Thread-locals.** The handler chain and the current exception are the runtime's thread-local variables, whose
  addresses `threadLocal` takes: the native backend calls their accessor (arm64.md §3.6), which clobbers what a call
  does and is not rematerialized, and `ssac` takes the address with `&`; neither keeps a list of their names.
- **Runtime helpers expanded inline,** as the C printer gets them from the header's `static inline` functions, so
  that `ssac` and arm64 both gain: an option's tag and unproxying, by a test of the proxy bit (`values.choose`), the
  runtime called only for a proxy; real `+`, `-`, `*`, and `/` by their instruction and an `isNaN` test; `Int` `div`
  and `mod` with the test for zero inline; and the bounds, count, and ordinal checks. Each check branches to a block
  that computes the site and calls the runtime's raise (`values.check`), so that the common path computes no site.
  The word module's operations, `static inline` in the header, are their instructions wherever they are called
  (`calls.inlineExternal`): arithmetic, bitwise operations, unsigned comparisons, conversions, and shifts and rotations
  by a constant count; so is `ascii.val`, a conversion of a Char, which the SSA holds zero-extended. The other string
  and `ascii` helpers are calls in C too, and stay calls.
- **The library's external functions that C inlines are their instructions** (`calls.libraryOperation`). The C
  printer calls a library member's C function in place of its wrapper (`libraryExternal`,
  [c-representation.md](c-representation.md) §6.2), and clang inlines the word module's `static inline` primitives;
  the SSA would call the wrapper, out of line. So for an import that resolves to `lib/`, at a signature of words and
  bytes, the builder makes `word`'s bitwise operations, arithmetic, conversions, and unsigned comparisons their
  instructions, and `word.shift` a shift (by a constant, one instruction or none; otherwise branches for the
  direction and for a count of 64 or more); `ascii.val` its argument and `ascii.char` a range check; and `string`'s
  `length`, `getChar`, and `setChar` a load or a store after the runtime's null and bounds checks, raising through
  `quest_raise_string_error` and `quest_raise_ascii_error` as the runtime does. The rest of the library's externals
  call their C function, as the C printer does, and the others the wrapper. Through `ssac`, checksum took 3.65 times
  the C backend's time and takes 0.17 (clang vectorizes its loop), md5 3.94 and 0.76, and psdes-random 4.09 and 1.01
  ([benchmarks.md](benchmarks.md) §11).
- **Blocks the entry does not reach are dropped** when a function is finished, and the rest renumbered.

What the builder does not yet build raises `unsupported`, naming the construct; `--stop-after ssa` reports it as an
internal error.

### 4.1. The Pipeline: Escape Analysis, Promotion, and Tail Calls

`questlang/ssa/pipeline` builds a unit and then runs its passes, by name, in order, each on every function:

- **`ssa/escape`** makes each allocation that does not leave its function a stack slot (§4.2), which promotion then
  makes values where it can.
- **`ssa/promote`** turns stack slots into values. A slot can be promoted when it is whole words and its address is
  only loaded from and stored to, a word at a time or a word's first byte (a `Bool` or `Char` variable's), never
  passed, stored, or offset otherwise. Each word becomes a variable of one type, stored all at one width, and loaded
  whole only if stored whole. A block that the definitions reaching it differ at gets a parameter (Cytron et al.'s
  placement at the iterated dominance frontier); then, along the dominator tree, a load becomes the value last
  stored, or, for a byte, its `zext8` or `sext8`, and one before any store reads a zero made in the entry. The slots
  left are renumbered. A function that enters a `try` keeps all its slots, since its handler must see what the body
  stored (arm64.md §3.6); a variable captured by a closure is a heap cell, and one passed as a `var` argument keeps
  its slot, its address escaping. `language/mutable_locals` covers each kind.
- **`ssa/tailCalls`** marks calls in tail position (§3, arm64.md §3.7): a call whose block returns its results (or the
  extension of its byte), or jumps, through blocks that do nothing else, to one that does. A block's parameters are
  taken as what the jump passes them, so that a join's parameter that its block does not return (as a contified
  loop's exit leaves) does not keep the call from being a tail call: zern's `lp1` and `lp2`, which call each other
  through their closures, were nested calls, 16,384 deep for each array they filled.
- **`ssa/interrupts`**, last and only when the Jupyter kernel's driver asks (`pipeline.setInterruptChecks`, under
  `--kernel`, for the code its JIT compiles; [jupyter.md](jupyter.md) step 5), checks the runtime's interrupt flag at
  each function's entry and each loop's head (a block a back edge goes to): it splits the block, loading
  `quest_interrupt_pending` and branching to a block that calls `quest_interrupt_raise`, or on to the block's old
  instructions. It isn't in `passes`, so no phase dumps it, and no golden sees it.

Neither removes values that become dead, such as parameters no load reads; the trivial allocator gives them slots,
and linear scan none.

The passes share their analyses: `ssa/cfg` (predecessors, successors, reverse postorder, the dominator tree with
preorder and postorder numbers, dominance frontiers, and loop depths) and `ssa/liveness` (each block's live-in and
live-out values, which the register allocator uses); `nodes` has the mutators (`targets`, `mapTargets`, `mapBlocks`,
`replaceUses`). The driver dumps the SSA after the builder (`--dump-after ssa_built`), after each pass
(`ssa_escape`, `ssa_promote`, `ssa_tailCalls`), and at the end (`ssa`); `QUEST_SKIP_PASSES`, a comma-separated list of passes'
names, leaves passes out, for a test or a bisection.

### 4.2. Escape Analysis

`ssa/escape` removes allocations whose pointers never leave the function that makes them: a tuple made only to be
taken apart, the tuple `o!tag` makes to read one component of, an option's payload tuple copied into the option, a
record's box only read. Inlining ([ir.md](ir.md) §8.6) is what brings producer and consumer into one function. The
pass is local and conservative, one function at a time with no summaries of others, and reuses promotion rather than
repeating it. `benchmarks/mlton/allocations.py` counts a program's allocations by function, to see what it removes
and what still escapes ([benchmarks.md](benchmarks.md) §9).

**What escapes.** A candidate is a call of `quest_alloc` with a constant size (`vals.alloc`); `quest_array_new`,
exceptions, and the runtime's other allocators are not. Its result is one of *its pointers*, and so is:

- a `ptrAdd` of one of them by a constant;
- a whole load of a word of the allocation whose stores all store one of its pointers at one offset (as a tuple's
  first word holds the address of its fields);
- a block's parameter that every edge taken binds to that one value (as the merge after a folded proxy test is).

The allocation does not escape when every use of each of its pointers is the address of a load or store at a constant
offset within its size, such a store into a word holding its pointer, or a proxy test (`vals.isProxy`:
`and(ptrToInt(p), QUEST_PROXY_TAG)`). A fresh allocation is never a proxy, so the test folds to zero, and the branches
`vals.unproxy` and the tuple and option readers make on it go to their direct arm; the fold is the pass's own, since
nothing else in the SSA knows that `quest_alloc` returns an aligned pointer. Anything else is an escape: an argument to
a call (the runtime's included: `quest_option_is`, `quest_val_is`, a conversion), a value stored elsewhere, a return,
a parameter bound to other values too, a comparison (`peq`, which could fold but does not yet), a `toVal`, any other
`ptrToInt`, or an access of part of a word holding a pointer. Since the folds decide which blocks are reached, and a
parameter's binding depends on the edges reached, the analysis starts with every candidate thought not to escape,
finds its pointers and the blocks reached to a fixed point, drops those that escape, and repeats until none more does.
`analyze` reports each candidate's verdict without changing the function.

**The transformation.** Each allocation that does not escape becomes a stack slot of its size, in whole words. Where
the call was, each of its words is stored zero, as `quest_alloc`'s memory is, each zero of the type its word is stored
(or else loaded) as, so that promotion sees one type, and one byte wide if only its first byte is accessed. Its
accesses go through the slot's address, its derived pointers' offsets added to their own; its derived pointers, the
words holding its pointer with their stores and loads, its `ptrToInt`s, and the parameters bound to its pointers, with
their arguments, are dropped; its proxy tests fold, and the blocks they no longer reach are dropped and the rest
renumbered. Promotion then makes values of what it can. A slot is per function, not per execution, so an allocation
in a loop reuses its slot, zeroed each time round; that is sound because a parameter that is one of its pointers is
bound to that one value on every edge, so no pointer from one iteration is live in the next. A slot whose word is
stored and loaded as different types (a type parameter's value stored as a `val` and loaded as a `ptr`) is not
promoted and stays a slot, which is still cheaper than the heap, as is one in a function that enters a `try`.

The C printer has its own, narrower forms of this, by pattern ([c-representation.md](c-representation.md) §5.3,
"Payloads Not Made"), since clang cannot remove a `GC_malloc`; the SSA's pass allocates no more than they do on the
benchmarks that need them, and less on zebra. The questlang test `ssa_escape` shows functions before and after the
pass and after promotion, and `language/escaping_allocations` checks that values survive each kind of escape and
that fresh tuples and options keep their identity.

## 5. Functions and Units

A **function** has a symbol (its C name), whether other units call it, its parameters (the entry block's), its result
types, its signature (§2.2), its blocks, and its stack slots (each a size and an alignment in bytes). A **unit** has its
functions and its **data**: each datum a symbol, whether other units refer to it, whether it is written at run time, and
its contents, 8-byte aligned: zeros (a global, a module's record and its initialized flag), a C string's text and its
NUL (a literal, a name in a descriptor or the function table), or words, each an integer or a symbol's address plus a
byte offset (a descriptor and what its extra field points at, an offset table, a tag map, a static closure, the function
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
function's stack slots as `bytes:alignment`, a load or store with its width (`load1s` sign-extends a byte), and a call
or a function with its signature where it is not words and reals (`pairs [0]`, `narrow [2]`, `memory [0:32]`,
`int32 [0]`, `result narrow`, `result int32`); the unit's data follows its functions, a
datum per line (`data qs_1 text "add1"`, `data g_res writable zero 8`, `data qf_f_closure words [qf_f, 0]`). A
position goes on a line of its own before the instructions at it, where it differs from the one before in its block
(`@line:col` in the unit's first file, `@file:line:col` in another, `@-` for none; a block starts at none):

```
function qf_f(%0: ptr, %1: int): int slots [16:8] {
b0(%0: ptr, %1: int):
  @3:29
  %2: int = const 1
  %3: int = add %1, %2
  return %3
}
```

`questlang/ssa/parser` reads the text back into a unit, values keeping their numbers, so that printing what it reads
prints what it read: with `QUEST_CHECK_IR=1` the driver reads back the SSA it prints and reports any difference, so
every golden is checked to read back as itself. A pass is tested on SSA written as text: the questlang tests
`ssa_promote`, `ssa_escape`, and `ssa_tailcalls` read small functions, run their pass and the verifier, and print the
functions before and after; and a program's SSA can be cut down to the functions that show a bug.

## 7. The Verifier

After the pipeline, and when `QUEST_CHECK_IR=1` after the builder and after every pass too, the verifier checks that
each value is defined once and its definition dominates its uses; that every instruction has the number and types of
arguments and results its opcode takes, a narrow load's result and a narrow store's value being ints; that a call's
and a function's signatures fit their arguments and results, and a call of the unit's own function matches its
parameters and results; that jumps pass their blocks' parameters' number and types; that a switch's cases are
distinct; that returns and tail calls give the function's results; that each block ends in one terminator; that a
`try`'s handler has the `try`'s block as its only predecessor and no parameters; and that slots and blocks referred
to exist. The questlang test `ssa_verify` builds well-formed and malformed functions by hand and checks the problems
it reports.

## 8. The C Printer

`codegen/ssac` prints a unit's SSA as C (arm64.md §3.14), an oracle for the SSA and the backends after it: with
`--backend ssac`, or `--unit-backend UNIT=ssac` for one unit, a build compiles units through it (arm64.md §3.12). The
questlang test `ssac_print` prints a unit built by hand, and `tests/python/test_ssac.py` compiles its golden.
