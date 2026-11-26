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
apart so that the collector's frame maps take a `ptr` as a pointer, precisely (arm64.md §3.13); converting between
them is explicit. `val` is apart from both because its descriptor, not its type, says whether it is a pointer, so a
frame map gives it as an ambiguous word, which the collector validates. A `val` is an `int` in registers, and `toVal`
and `fromVal` convert it.

## 2. Instructions

Every instruction has one shape (arm64.md §3.15): an opcode, an array of argument values, an array of result values, an
immediate integer, a symbol, and a source position (`loc`: a file, by its number in the unit's `files`, a line, and a
column, or none), for the native code's line table (arm64.md §3.16). The builder gives each instruction the position of
the IR statement it builds (ir.md §5), or of the last one that had a position; a block's terminator has one too
(`termLoc`), and a tail call its call's. Passes that care only about structure (the verifier, liveness, renaming,
register allocation) walk the arrays; only the passes that care what an instruction means case on its opcode.

| Opcode | Arguments → results | Meaning |
|---|---|---|
| `const` | → `int` | the immediate |
| `realConst` | → `real` | the double whose bits are the immediate |
| `symbol` | → `ptr` | the address of the symbol (static data, a function, a runtime global), plus the immediate in bytes |
| `null` | → `ptr` | the null pointer |
| `slot` | → `ptr` | the address of the stack slot numbered by the immediate |
| `ptrAdd` | `ptr int` → `ptr` | the pointer plus a byte offset: every field's, element's, and slot's address |
| `add`, `sub`, `mul` | `int int` → `int` | wrapping arithmetic ([type-system.md](type-system.md) §6.3.1) |
| `mulHiU` | `int int` → `int` | the high 64 bits of the unsigned 128-bit product (`word.mulHi`; arm64's `umulh`) |
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
| `intToReal` | `int` → `real` | the nearest double, ties to even (C's `(double)`, arm64's `scvtf`) |
| `sext8`, `zext8` | `int` → `int` | the low byte, sign- or zero-extended (a C `bool` or a `QChar`, an unsigned byte, received: `zext8`) |
| `load` | `ptr` → value | the immediate is the byte offset; the width and the result's type are the instruction's (§2.1) |
| `store` | `ptr value` → | likewise |
| `call` | args → results | a direct call of the symbol |
| `callIndirect` | `ptr` args → results | a call through a function pointer |
| `copy` | value → value | the same value (made by the builder; removed by later passes) |
| `select` | `int` x x → x | the second argument if the first is nonzero, else the third; x is `int`, `ptr`, or `val` (made by `ssa/passes/selects`, §4.1; ssac's `?:`, arm64's `csel` or `cset`) |
| `unproxy` | `ptr` → `ptr` | the object a tuple's or an option's pointer is: the proxy's original when its tag bit (`QUEST_PROXY_TAG`) is set, else the pointer itself (`quest_unproxy`; made by `representation.unproxy` for an `original` access, pure, so that value numbering merges one with its equal in a dominating block; lowered by `ssa/passes/unproxies`, §4.1, before the backends see it) |

### 2.1. Loads and Stores

A load or store names its width: 8 bytes (an `int`, `ptr`, or `real`), 4 (a C `int`, read sign-extended), or 1 (a C
`bool` or a `QChar`: read zero- or sign-extended, as the instruction says; the builder zero-extends both, since a
`Char` is an unsigned byte, arm64.md §3.9). Its address is its pointer argument plus the
immediate.

A load is **invariant** (`Inst.invariant`) when nothing writes what it reads once the object it reads from is made, so
that value numbering may reuse it across stores and calls (§4.1). The builder marks the loads it knows of
(`values.invariantWord`): a closure's code pointer and its words (a deferred capture of a `let rec` is stored before the
closure can run), an array's and a string's length and a string's data pointer (the
runtime writes a string's bytes, never these), a proxy's original, an option's tag, a record's offset table, a view
map's index, and a conversion's static map. A module's record is written while its module is initialized, and is not
marked. A field's static type does not make it invariant, since an immutable view may alias a `var` field (`Tuple var a:
A end <: Tuple a: A end`). The escape pass clears the mark on the accesses it moves to a stack slot, which a loop
reuses.

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
never returns), come from the table `ssa/runtimeFunctions`, which holds each one's C prototype and is checked
against `quest_runtime.h`; a Quest function's come from its parameters' and results' representations. A function extends
its byte parameters on entry, since a C caller leaves their upper bits unspecified. A C `bool` or `QChar` result is
extended by a `zext8` after the call, since AAPCS64 leaves a narrow result's upper bits unspecified; a function that
returns such an extension of a call's result can make the call in tail position, since its own caller extends it again.
So can one that returns a call's `ptr` result as a `val`, or the reverse (`toVal`, `fromVal`), as a direct call of a
closure's code at its own types does (ir.md §8.3, `adapt`): the register is the same, and `ssac` casts it.
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
| `tailCall` | a call in tail position (arm64.md §3.7, marked by `ssa/passes/tailCalls`): its results are the function's |
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
use only those before them: `values` (representations, the builder's state, emitting, variables, atoms, and words),
`representation` (slots, aggregates' components, proxies, and allocation), `descriptors`, `calls` (primitives, calls,
and modules' members), `aggregates` (conversions, tuples, records, variants and options, arrays, and type
applications), `control` (operations and statements), `adapters` (exported functions and function types' adapters),
and `unit` (functions, static data, registration, and the unit).

- **Variables.** Each variable has one binding (`values.Binding`): SSA values, a stack slot, the location a `var` or
  `out` parameter points to, a handler's copy of the exception state, or a global. An IR variable of a value is the
  SSA values of its representation; a boxed variable (a record or
  variant the represent pass holds in its box) is its box's pointer, and a boxed mutable one's value is its box's
  record or variant. A **mutable variable is a stack slot**, loaded and stored, as C at `-O0` keeps it: always correct,
  the rule `try` needs for free, and promoted to values afterwards (§4.1). A variable a top level binds outside loops
  that a function or another top level names, or that is a module's member, export, or record (`walk.globalVariables`,
  [ir.md](ir.md) §8.2), is a global (`g_<name>`), as in C, however it is bound: a join's parameter (the value of a
  top-level `if`, `case`, or `try`) is stored to its global at the join, as any binding is, so that the program's
  functions see it (`language/global_joins`).
- **Memory.** Every aggregate slot is a word (`layout`); a box or a global holds a record or variant's 16 bytes; a
  location (a cell, what a `var` or `out` parameter points to) holds a record or variant as its box's pointer
  (`layout.shapeLocationRepresentation`). Offsets come from `repr/layout`, `repr/staticdata`, and
  `repr/runtimeLayout`, which the C asserts.
- **Closures.** A closure is one object, its code pointer and then the descriptors of its type arguments and its
  captures, a word for each of their values: past the code pointer, private to the unit, which alone reads it
  ([arm64.md](arm64.md) §7.1). Its code takes the closure as its first argument. A call of a variable bound
  to a closure of one of the unit's functions calls the function directly, as the C printer does; when that function
  is an external's thunk (`qx_`, ir.md §8.4.1), which only forwards its arguments, the call is of the external C
  function itself, as the C compiler makes it by inlining the thunk. A call of an imported member that is one of the
  standard library's externals (`repr/externals`) calls the C function, as the C printer's `libraryExternal` does.
- **The exception state.** The handler chain and the current exception are the runtime's globals, whose addresses
  `symbol` takes. They were thread-locals, reached by an instruction of their own, until each use's call of the
  accessor proved costly (arm64.md §3.6).
- **Runtime helpers expanded inline,** as the C printer gets them from the header's `static inline` functions, so that
  `ssac` and arm64 both gain: an option's tag and unproxying, by a test of the proxy bit (`representation.choose`), the
  runtime called only for a proxy; real `+`, `-`, `*`, and `/` by their instruction and an `isNaN` test; `Int` `div` and
  `mod` with the test for zero inline; and the bounds, count, and ordinal checks. Each check branches to a block that
  computes the site and calls the runtime's raise (`values.check`), so that the common path computes no site. The word
  module's operations, `static inline` in the header, are their instructions wherever they are called
  (`calls.inlineExternal`): arithmetic, bitwise operations, unsigned comparisons, conversions, and shifts and rotations
  by a constant count; so is `ascii.val`, a conversion of a Char, which the SSA holds zero-extended, and so is
  `real.int` (`quest_real_from_int`), an `intToReal`, though the runtime defines it out of line: as a call it was 13%
  of mandelbrot's samples. The other string and `ascii` helpers are calls in C too, and stay calls.
- **The library's external functions that C inlines are their instructions** (`calls.libraryOperation`). The C
  printer calls a library member's C function in place of its wrapper (`libraryExternal`,
  [c-representation.md](c-representation.md) §6.2), and clang inlines the word module's `static inline` primitives;
  the SSA would call the wrapper, out of line. So for an import that resolves to `lib/`, at a signature of words and
  bytes, the builder calls the C function the C printer would, which for `word`'s operations is then
  `inlineExternal`'s instructions; `word.shift` by a count that is not a constant is a shift with branches for the
  direction and for a count of 64 or more; `ascii.val` is its argument and `ascii.char` a range check; and `string`'s
  `length`, `getChar`, and `setChar` are a load or a store after the runtime's null and bounds checks, raising
  through `quest_raise_string_error` and `quest_raise_ascii_error` as the runtime does. The rest of the library's
  externals call their C function, as the C printer does, and the others the wrapper. Through `ssac`, checksum takes
  0.17 times the C backend's time (clang vectorizes its loop), md5 0.76, and psdes-random 1.01, where calling the
  wrappers they took 3.65, 3.94, and 4.09 ([benchmarks.md](benchmarks.md) §11, 2026-11-02).
- **Blocks the entry does not reach are dropped** when a function is finished, and the rest renumbered.

What the builder cannot build raises `unsupported`, naming the construct; `--stop-after ssa` reports it as an
internal error.

### 4.1. The Pipeline and Its Passes

`questlang/ssa/pipeline` builds a unit and then runs its passes, by name, in order, each on every function:

- **`ssa/passes/escape`** makes each allocation that does not leave its function a stack slot (§4.2), which promotion
  then makes values where it can.
- **`ssa/passes/promote`** turns stack slots into values. A slot can be promoted when it is whole words and its address
  is only loaded from and stored to, a word at a time or a word's first byte (a `Bool` or `Char` variable's), never
  passed, stored, or offset otherwise. Each word becomes a variable of one type, stored all at one width, and loaded
  whole only if stored whole. A block that the definitions reaching it differ at gets a parameter (Cytron et al.'s
  placement at the iterated dominance frontier); then, along the dominator tree, a load becomes the value last stored,
  or, for a byte, its `zext8` or `sext8`, and one before any store reads a zero made in the entry. The slots left are
  renumbered. A slot accessed in a block that a `try`'s handler reaches keeps its memory, since the handler must see
  what the body stored (arm64.md §3.6), and no such block gets a parameter for a promoted variable, which it never
  loads; a variable captured by a closure is a heap cell, and one passed as a `var` argument keeps its slot, its
  address escaping. `language/mutable_locals` covers each kind.
- **`ssa/scalars`** replaces the objects that block parameters merge, which escape analysis leaves, by the values of
  their words (§4.3): a loop that carries a tuple carries its components. It runs after promotion, which makes the
  variables a loop carries its parameters, and before `ssa/passes/constants`.
- **`ssa/passes/constants`** makes constant the globals bound to constants. A global the unit does not export (another
  unit could store to one it does), a word of static data that starts as zero, is constant when the unit stores to it
  once, a whole word that is an `opConst` or a symbol's address, and otherwise only loads it, a whole word at a time, as
  the type of that value; when nothing that could read it runs on any path from its function's entry to the store; and
  when the store is in no loop. What could read it is a load of it, or a call of code that could: any call but of a
  function of the unit's own whose code, looked at in turn, could not; of a runtime function the effects table says
  writes no memory (Quest code is taken to write memory), as `quest_alloc_exception` for a module's exceptions; of one
  that registers types, functions, or dictionaries; or, from a module's initialization, of another module's. Modules
  import one another in no cycle, so the modules a module's initialization initializes first reach none of its code. The
  datum then holds the value from the start, read-only; the store goes, and each load becomes the value, which value
  numbering then folds into what uses it. A module's member bound to a literal or to what the builder makes a constant
  (a call of a standard library external it makes an instruction, as `word.fromInt(1)` for `util/bignum`'s `oneW`) is
  such a global: the module's initialization stores it, guarded by the module's flag, and each use would load it, in
  every iteration of a loop that uses it ([benchmarks.md](benchmarks.md) §15.5). Only a unit's own globals are seen, so
  only those are folded: another unit loads an exported member. `ssa_constants` shows each case.
- **`ssa/passes/concats`** joins chains of `<>` ([libraries.md](libraries.md) §1.2). A call of
  `quest_string_concat` whose argument is the result of another in the same block, used only there, with no store or
  call that may write memory between them, takes that one's parts, and the chain becomes one call of
  `quest_string_concat_n`, which allocates the whole string once and copies each part once; a chain of more than seven
  parts is joined seven at a time. `language/concat_chains` covers it.
- **`ssa/passes/nanChecks`** removes the NaN checks that a later check finds the NaN of. The builder checks each `++`,
  `--`, `**`, and `//` for a NaN result, which raises `real.error` at the operation (a test and a branch to a block that
  raises with its site): 126 of nucleic's `tfoCombine`'s 203 instructions over MLton's. A NaN operand makes each of the
  four's result NaN, so a check of a value whose uses are all such operations, each checked, is found again by a check
  that remains. The checks are removed only within a region: blocks that checks' good edges join, each entered only
  from the last, holding nothing that writes memory or calls, so that nothing a program could see happens between a
  removed check and the one that finds its NaN. Raising there would report the wrong site, so a remaining check that
  fails goes to the region's replay instead: its instructions again, computed from its inputs with every check it had,
  which raises at the first operation that makes a NaN with that operation's site, as before. Nothing in the region
  writes memory, so the replay computes the same values; only the region's inputs stay live to it, not the values
  between. No program's behavior changes, and the interpreters and the other backends need not follow; the error
  tests `nan_chain_*` raise at each operation of a chain. It takes nucleic's instructions retired to 0.82 through
  ssac and 0.86 through arm64 (benchmarks.md §39). It runs before value numbering, which removes the tests it leaves.
- **`ssa/passes/valueNumbers`** removes redundant values along the dominator tree, in the manner of Briggs, Cooper, and
  Simpson: a pure instruction or a load whose equal dominates it becomes that equal, by a key of its opcode, immediate,
  symbol, result type, and arguments' numbers (a constant's by its value; commutative ones ordered; a load's address
  taken apart into a base, an index, and a constant offset through `ptrAdd`s, so that `load8 %4 + 0` of `%4 = ptrAdd %1,
  const 8` is `load8 %1 + 8`). An invariant load (§2.1) is available across anything; an ordinary one only within a
  memory generation, which a store, a call that may write memory (any but of a runtime function whose effects say it
  does not, `quest_alloc` among them), and a try's handler start anew, and which a block continues from its predecessors
  when they all end in the same one and have all been walked (the dominator tree in preorder): a join no path into
  which writes continues the generation, while a loop's header, which its back edge reaches unwalked, starts anew. The
  rule for joins (2026-11-25) took 3.4% of wc-scanStream's instructions through arm64 and 0.69% of the compiler's. A whole word's store makes its value what a load of its address reads in the generation it starts. A
  whole word's load whose neighbor its block also loads is kept though an equal is available from another block, so that
  arm64 loads the two as a pair: a lone load of half of a pair just stored, after `quest_alloc` cleared its first word,
  took psdes-random's loop from 1.39 to 1.90 of C's time. A `copy` becomes its argument; and a block's parameter that
  every jump binds to one value that value. The comparisons, `and`s, `mul`s, and `ptrAdd`s arm64's selection fuses into
  the branch or access using them in their block are replaced only by an equal in their own block, and so are constants,
  symbols, and nulls: shared across a function, they were live longer and spilled (hamlet's stack accesses rose from
  8,129 to 10,022, mlyacc's from 4,522 to 5,713, and neither ran faster). The pure instructions and loads then left
  without uses are removed. `ssa_valuenumbers` shows each case.
  Hoisting loop-invariant pure values and invariant loads to preheaders was tried after it (2026-11-03) and not kept:
  it found almost nothing to move, since a loop's invariant loads sit behind null and bounds checks inside the loop,
  and its constants are rematerialized. `ssa/passes/loops` hoists them now, by rotating the loop so that those checks
  run once before it.
- **`ssa/passes/conditions`** decides a branch on a comparison that a dominating branch on the same comparison has
  decided: a block that only one edge of a branch enters knows the comparison's value, and so does every block it
  dominates, where a branch on the same comparison becomes a jump to the target that value chooses, and the blocks no
  longer reached are dropped. Comparisons are the same by opcode, immediate, and operands, where a constant, a null, or
  a symbol is compared by what it is and an invariant load by its address, since value numbering keeps those apart in
  each block; an equality known gives its negation too. The builder checks an array for null and its index against its
  length at every access, as it does a string, and value numbering compares only within a block, so fft's butterfly made
  24 null checks and 24 bounds checks for its 8 elements, and this takes its arm64 instructions retired to 0.81
  (benchmarks.md §39). A null test of a pointer that cannot be null is decided too: a symbol's address, or a new object
  (from `quest_alloc`, `quest_array_new`, or a runtime function that returns a string, each of which returns a new one;
  `conditions.allocates`), so an array that a loop fills as it makes it is not checked on every pass (benchmarks.md
  §46). It then numbers the values again of each function it changed, which merges the loads that the checks kept in
  separate generations.
- **`ssa/passes/selects`** makes selects of branches (if-conversion): a branch whose two arms only pass values to one
  block, each arm directly or through a block of its own (one with no parameters, reached only from the branch, that
  only jumps on), becomes a jump to that block, each argument the arms pass differently a `select` by the branch's
  condition, at most two of them and none a `real`. An arm's block may have up to two instructions that can run before
  the branch whichever arm it takes: they write nothing, cannot trap, and read nothing the branch could change
  (arithmetic but division, comparisons, conversions, constants, and a load of static data at a symbol, a module's
  global); they move into the branch's block. A carry in a loop of arbitrary-precision arithmetic (`util/bignum`'s
  `bit(word.lt(sum operand))`) is such a branch, taken as often as not, half of which arm64 mispredicted as a branch; it
  makes each a `cset` of the comparison's flags, as C's compiler does ([benchmarks.md](benchmarks.md) §15).
  A function the pass changed has, after the SSA's last pass (`straightenUnit`), its blocks that only jump to a block
  whose sole predecessor they are merged with it, the successor's parameters taking the jump's arguments ; only a
  block that ends in a conversion's selects is merged, since merging every chain in such a function changed arm64's
  layout of wc-scanStream's loop and others, and cost it 3.5% and the compiler 0.9% more instructions): one diamond after another was left a chain of blocks,
  and what is decided within a block stopped at each jump (arm64 makes a carry `adds` and `cset hs` only in its add's
  block, arm64.md §3.1; with both of a limb's carries in one block, smith-normal-form's instructions through arm64 were
  0.955 of what fusing the first alone left, 2026-11-25). `ssa_selects` shows each case.
- **`ssa/passes/tables`** makes a switch of constants a load from a table. A switch whose arms (each a case's target,
  directly or through blocks with no parameters that only make constants and jump on) all pass arguments to one
  block, the join, with at least 4 cases, dense (their range at most twice their number), becomes a check of the value
  less the least case against the range's size (`ult`), branching to the default when out of it, and a block that
  loads each argument the arms pass differently from a static table of the unit's (read-only data, a word for each
  value in the range, `qt_<function>_<n>`) at that index, then jumps to the join. An argument is an integer or a
  symbol's address (`opConst`, `opSymbol`), or a value every arm passes alike; a `real` keeps the switch. A value in
  the range that no case has takes the default's arguments, so a switch with such gaps is converted only when its
  default passes constants to the join too. A switch whose arms each return constants instead (through such blocks
  too) is taken as one whose arms jump to a join that returns them: the block that loads returns. A function whose
  body is a case has such arms, since the IR's simplifier turns a join whose continuation only returns into a return
  in each arm. `nodes.opcodeIndex`, a case of 54 arms each an integer and the whole of its function, was arm64's jump
  table to 54 blocks of a `mov` and an epilogue before this rule (1,682 of the arm64-built compiler's samples against the
  ssac-built one's 544, [benchmarks.md](benchmarks.md) §47; before §22, a compare and branch for each case, §21.5). A case whose arms each give a string literal is converted too, since
  a literal is its static object's address (`symbol qso_N + 8`, past its header word; [c-representation.md](c-representation.md)
  §3.2), so the table holds the literals' addresses. `ssa_tables` shows each case,
  `language/string_literals_read_only`'s SSA a case of literals, and `language/option_switch_returns`'s functions whose
  body is a case.
- **`ssa/passes/accumulate`** makes loops of recursion through an associative operation (LLVM's accumulator recursion
  elimination; [benchmarks.md](benchmarks.md) §14): in a function of one `int` result, from which no slot's address
  escapes, a block whose last instructions are a call of the function itself and an `add`, `mul`, `and`, `or`, or `xor`
  of its result and another value, and which returns that (directly or through blocks that pass it on, as for
  `tailCalls`), jumps instead to a loop header with the call's arguments and the accumulator combined with the other
  value. The header takes the entry's instructions, with a parameter for each of the function's, which replace them, and
  one for the accumulator, which the entry passes the operation's identity; every return combines what it returns with
  the accumulator, and every tail call of the function itself jumps to the header with the accumulator as it is (left a
  tail call, arm64 would jump to the entry and start it again). `Int` arithmetic wraps, so the five are associative and
  commutative and the result is the same. fib's `fib(n - 1) + fib(n - 2)` keeps its first call and loops down the
  second; a runaway `1 + f(n + 1)` loops forever rather than overflowing the stack, as clang already made it in C
  ([exceptions.md](exceptions.md) §6), and a traceback through the loop's levels shows one frame, as through tail calls
  (`repl/module_errors` subtracts, to keep its frames). `ssa_accumulate` shows each case.
- **`ssa/passes/loops`** makes the loop that recursion is visible to the SSA, and keeps module cells in registers across
  loops (benchmarks.md §44). A recursive loop that stays a function, because the IR could not contify it (mandelbrot's
  `loop1`, called from `doit` and the top level), is a self tail call, which only the backends made a jump. A function
  that calls itself in tail position once, from which no slot's address escapes, gets a header as `accumulate`'s, and
  the call becomes a jump to it. One that calls itself so twice or more is left to the backends: its calls are usually
  nested loops in one function (zern's `lp2`, into which `lp1` is inlined), which one header merges into a shape that
  clang does not take apart again (zern took 1.09 of its instructions through `ssac`). Then a module cell's word that a
  loop stores to (a top-level tuple's `var` field, reached through its global's load, which only its module's
  initialization writes) is kept in a stack slot across the loop, which promotion makes a register: loaded where the
  loop is entered, stored back on every edge that leaves it (a raise's too, from the block before the raise). It must be
  an `Int` or a `Real`, read and written whole; no other access in the loop can reach it (one at an overlapping offset
  through another address but a slot's or a global's own word, or an invariant load); the loop stores nothing to the
  global, calls only runtime functions that write no memory and cannot raise, and enters no try. mandelbrot retires 0.90
  of its instructions through `ssac` and 0.89 through arm64. Last, what a loop computes the same on every pass moves
  before it, into a preheader (benchmarks.md §44): pure operations (constants, symbols, and nulls copied, not moved, and
  comparisons left with the branches arm64 fuses them into) and loads that cannot fault there (a slot's, a global's the
  loop does not store to, an invariant load of an object a check before the loop found not null, or of a new object).
  When the loop's header only tests whether to leave and its first pass checks invariant values before it stores, calls,
  or tests what varies, the loop is rotated: a copy of the header's test leaves where the header would, or runs those
  checks once and enters the header's successor, and the header becomes the test at the loop's bottom. The checks raise
  as the first pass would have, `conditions` decides the loop's own copies, and the loads they guarded move too; the
  header's values used elsewhere are kept in slots, stored by the header and the guard, which promotion joins; and the
  block parameters promotion leaves unused are dropped (a loop's dead closure argument among them). A derived pointer
  (`ptrAdd`) moves only out of a loop that calls nothing, so that none is live across a collection without its object's
  own pointer. Through arm64, matrix-multiply retires 0.84 of its instructions, fft 0.87, pidigits and vector-rev 0.88,
  smith-normal-form 0.90; through `ssac`, whose clang hoisted most of it already, tensor 0.95. Then a bounds check goes
  when the comparisons before it decide it (benchmarks.md §44): its index is never negative (a constant, a length,
  either plus a small constant, or a block parameter that every jump binds such a value to) and at most the length less
  one, by a comparison on a branch that dominates it or, for a block parameter, on every jump into the block, by the
  value bound there or, for a jump binding x + 1, by a test there that x is not the bound (a `for` loop's, by
  induction). Values compare by form, a base and a constant offset, loads by address and symbols by name, so the guard's
  copy of `len - 1` is the header's; and `string.length`'s test for a null string counts as the length, since under its
  bound of 0 - 1 no index that is not negative reaches the check. Through arm64, vector32- and vector64-concat retire
  0.83 of their instructions, matrix-multiply 0.91, smith-normal-form 0.93; through `ssac`, smith-normal-form 0.94 and
  the vector programs 0.95. Through arm64 (not `ssac`: clang rotates loops itself, and one rotated before it can compile
  worse, fib by 20%) a loop is rotated whether or not it has checks to move, when its header only tests whether to
  leave, so that each pass ends in the test rather than in a jump back to it (the guard binding the parameters of the
  header's successor from its copies); and a Real constant used in a loop that calls nothing, which takes two
  instructions to make, is made once before it (benchmarks.md §44): imp-for retires 0.77 of its instructions, fib, tak,
  and mandelbrot 0.87, the vector programs 0.90. `language/module_cells_in_loops`, `language/hoisted_loop_checks`, and
  `language/decided_bounds_checks` show each case.
- **`ssa/passes/tailCalls`** marks calls in tail position (§3, arm64.md §3.7): a call whose block returns its results
  (or the extension of its byte), or jumps, through blocks that do nothing else, to one that does. A block's parameters
  are taken as what the jump passes them, so that a join's parameter that its block does not return (as a contified
  loop's exit leaves) does not keep the call from being a tail call: zern's `lp1` and `lp2`, which call each other
  through their closures, would otherwise be nested calls, 16,384 deep for each array they fill. The blocks a tail call
  leaves unreached are dropped (`cfg.dropUnreached`, as the builder drops its own), since they may return a value that
  value numbering put in place of their parameter, and that the call no longer defines.
- **`ssa/passes/tailJumps`** makes loops of mutual tail calls ([benchmarks.md](benchmarks.md) §14). The unit's functions
  and the direct tail calls between them form a graph, whose strongly connected components (Tarjan's) are the groups
  of mutually tail-recursive functions. Into each function of a group of more than one are copied the other members it
  reaches through tail calls, its own and its copies', each once, while the copies total at most 100 instructions: a
  member without stack slots or a `try`, whose parameters are passed in registers (as a word, a real, or a pair's
  word, as a jump passes them) and whose results are passed as the function's, so that its returns are the
  function's. Copies are made from each function's blocks as they were before the pass, and then each tail call of a
  member copied in jumps to its copy's first block; a tail call of the function itself is left, which arm64 makes a
  jump to its first block and clang a loop. even-odd's `even1` holds a copy of `odd1`, whose tail call of `even1` is
  then a self tail call: one loop, without pushing and popping a frame at each step. A call through a closure is
  indirect and is left. `ssa_tailjumps` shows each case.
- **`ssa/passes/trampolines`**, after it, makes an export its function ([benchmarks.md](benchmarks.md) §22).
  Another unit calls a module's function through its export (`qv_`), which passes a null environment and tail-calls the
  function, often through an adapter that tail-calls it in turn ([ir.md](ir.md) §8.4.1): vector.get was three branches
  on arm64, where clang made the C build's export the function. An exported function of one block that ends in a tail
  call of a function of the unit gets a copy of that function in place of the call (`tailJumps.spliceInto`: the callee's
  first block appended to the export's, with the call's arguments for its parameters, its other blocks after), again
  while that block ends in such a call, up to four times, so that an adapter is copied in and then the function it
  calls. A function is copied when it has at most 64 instructions, every call it makes is a tail call or one in a block
  that never ends (a raise), no block goes to its first, it takes the call's arguments with their types, its results are
  passed as the export's, and `tailJumps.copiable` holds. A function too large is still called directly once its adapter
  is copied in. The unit's own callers still call the function, and nothing else is inlined. Since a traceback names a
  frame by its function's exact start, the unit's table of names (`qr_funcs`) gets an entry for each such export, the
  last function copied into it that has a name, and the count `qr_register_dicts` registers grows to match.
  `ssa_trampolines` shows each case.
- **`ssa/passes/unproxies`**, run by the SSA's backends after the passes (`pipeline.lower`, before inline allocation),
  lowers each `unproxy` to a test of the proxy bit: the block is split at it, and branches
  on the pointer's tag bit to a block that loads the proxy's original (an invariant load of `QProxy`'s `orig`, less the
  tag) or to one that passes the pointer on, both jumping to the rest of the block, whose parameter is the object. Until
  then an `unproxy` is a pure instruction, which value numbering merges along the dominator tree: hashmap's `findIndex`
  tests its record once, before its loop, rather than before each field the loop loads. Escape analysis and scalar
  replacement take an `unproxy` of one of an allocation's pointers as that pointer, since a fresh object is never a
  proxy; `selects` does not speculate one, since it may load. `ssa_unproxies` shows the merge and the lowering.
- **`ssa/passes/interrupts`**, at the end of `pipeline.run`, after the passes and before `pipeline.lower` (so before
  unproxies and inline allocation), and only when the Jupyter kernel's driver asks (`pipeline.setInterruptChecks`,
  under `--kernel`, for the code its JIT compiles; [jupyter-kernel.md](jupyter-kernel.md) §5), checks the runtime's
  interrupt flag at each function's entry and each loop's head (a block a back edge goes to): it splits the block,
  loading `quest_interrupt_pending` and branching to a block that calls `quest_interrupt_raise`, or on to the block's
  old instructions. It isn't in `passes`, so no phase dumps it, and no golden sees it.
- **Inline allocation** (`ssa/passes/allocations`, `pipeline.inlineAllocation`), run by the SSA's backends after the
  passes: arm64 and the JIT cannot get the collector's fast path from the runtime's header as the C printer does, and
  ssac's printer calls every runtime function out of line, `quest_alloc` included (§8), which cost it a third of what C
  gained on the allocation-heavy programs (benchmarks.md §16.2). Each call of `quest_alloc` of a constant size becomes
  the sequence of docs/collector.md §3.4. The block is split at the call: it loads `quest_gc_check_flags` and the cursor
  and limit of the object's space (`quest_gc_cursor`, `quest_gc_limit`; the noscan space's for a layout of scalars
  alone, read from the unit's layout data) and branches, when a checking mode is on or the hole has no room, to a block
  that calls `quest_gc_alloc_slow`, else to one that bumps the cursor and stores the header word (the layout's address)
  where the cursor was; both jump to the rest of the block with the allocation's base, an `int`, which makes the object
  (`intToPtr` of the base plus 8, the call's result) and sets its start bit in `quest_gc_start_bits`. The slow path
  stores the header word itself, since while a full collection marks in slices it takes every allocation (the limits are
  hidden) and the word carries the collector's flags (collector.md §3.10). The base is never a `ptr` the rest of the
  block has: selection folds the object's offsets into whatever pointer they come from, so a `ptr` at the header would
  be the value live across later calls, and the collector takes a `ptr` in a frame for the object it is at, inside, or
  at the end of, which for the header's address is the object before (arm64.md §3.13).
  `QUEST_SKIP_PASSES=inlineAllocation` leaves the calls, which `quest_inline.o`'s definition of `quest_alloc` serves,
  for measuring the inline path ([collector.md](collector.md) §3.4). The questlang test `ssa_allocations` shows
  functions before and after.

Only value numbering removes values that become dead; parameters no load reads stay, which the trivial allocator gives
slots, and linear scan none.

The passes share their analyses: `ssa/cfg` (predecessors, successors, reverse postorder, the dominator tree with
preorder and postorder numbers, dominance frontiers, and loop depths); the register allocator computes liveness on the
machine layer's instructions (`codegen/machine/machine`), not on the SSA. `nodes` has the mutators (`targets`,
`mapTargets`, `mapBlocks`, `replaceUses`). The driver dumps the SSA after the builder (`--dump-after ssa_built`), after
each pass (`ssa_NAME`, for each name in `ssa/passNames`, the one list of the passes, from which the pipeline and the
driver's phases and usage text are derived), and at the end (`ssa`); `QUEST_SKIP_PASSES`, a comma-separated list of
passes' names, leaves passes out, for a test or a bisection.

### 4.2. Escape Analysis

`ssa/passes/escape` removes allocations whose pointers never leave the function that makes them: a tuple made only to be
taken apart, the tuple `o!tag` makes to read one component of, an option's payload tuple copied into the option, a
record's box only read. Inlining ([ir.md](ir.md) §8.6) is what brings producer and consumer into one function. The
pass is local and conservative, one function at a time with one fact about the unit's others (whether each uses its
first parameter only to load from), and reuses promotion rather than repeating it. `benchmarks/mlton/allocations.py` counts a program's allocations by function, to see what it removes
and what still escapes ([benchmarks.md](benchmarks.md) §9).

**What escapes.** A candidate is a call of `quest_alloc` with a constant size and a layout's address; `quest_array_new`,
exceptions, and the runtime's other allocators are not. Its result is one of *its pointers*, and so is:

- a `ptrAdd` of one of them by a constant;
- an `unproxy` of one of them, which is the allocation, since a fresh object is never a proxy;
- a whole load of a word of the allocation whose stores all store one of its pointers at one offset (as a tuple's
  first word holds the address of its fields);
- a block's parameter that every edge taken binds to that one value (as the merge after a folded proxy test is).

The allocation does not escape when every use of each of its pointers is the address of a load or store at a constant
offset within its size, such a store into a word holding its pointer, a proxy test (`proxyFold.isProxyTest`:
`and(ptrToInt(p), QUEST_PROXY_TAG)`), or an argument to a write barrier (`quest_barrier` among and after an
aggregate's initializing stores when a call came between them and its allocation, `quest_barrier_slot` after a pointer
store into a field or element; [collector.md](collector.md) §3.5), which keeps no pointer, or the first argument of a
direct call, not a tail call, of a function of the unit that uses its first parameter only as the address of loads,
directly or through the block parameters it is passed to (`firstLoadOnly`): a closure passed to its own code, which
reads its captures and keeps nothing once it returns. The allocation itself is passed there, not a pointer derived
from it, and only when no word of it holds its own pointer, which the callee could load and keep (a `let rec`
closure capturing itself). Nor in a function with a call `tailCalls` would make a tail call (`tailCalls.hasTailCalls`)
or a call of itself, which `accumulate` may make one: `tailCalls` makes no tail call in a function a slot's address
escapes from, so a recursion there would grow the stack (life's `nthgen` did, 8 percent slower, when this was
tried without the condition). Measured in [benchmarks.md](benchmarks.md) §32. A fresh allocation is
never a proxy, so the test folds to zero, and the branches the builder's `representation.unproxy` and the tuple and
option readers make on it go to their direct arm. The fold is escape analysis's and scalar replacement's alone (§4.3),
which share it in `ssa/passes/proxyFold` (the values' definitions, the proxy tests of the pointers each tracks, and
the blocks reached once they fold), since nothing else in the SSA knows that `quest_alloc` returns an aligned
pointer.
Anything else is an escape: an argument to any other call (a tail call's, which outlives the caller's frame, and the
runtime's included: `quest_option_is`, `quest_val_is`,
a conversion), a value stored elsewhere, a return,
a parameter bound to other values too, a comparison (`peq`, which could fold but does not), a `toVal`, any other
`ptrToInt`, or an access of part of a word holding a pointer. Since the folds decide which blocks are reached, and a
parameter's binding depends on the edges reached, the analysis starts with every candidate thought not to escape,
finds its pointers and the blocks reached to a fixed point, drops those that escape, and repeats until none more does.
`analyze` reports each candidate's verdict without changing the function.

**The transformation.** Each allocation that does not escape becomes a stack slot of its size, in whole words, and
its barriers are dropped: a slot is a root, and has no header word for `quest_barrier` to read. Where
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
"Payloads Not Made"), since clang cannot remove an allocation; the SSA's pass allocates no more than they do on the
benchmarks that need them, and less on zebra. The questlang test `ssa_escape` shows functions before and after the
pass and after promotion, and `language/escaping_allocations` checks that values survive each kind of escape and
that fresh tuples and options keep their identity.

### 4.3. Scalar Replacement

`ssa/scalars` replaces by the values of their words the objects that escape analysis leaves because a block parameter
merges them: wc-scanStream's loop carries its stream, a tuple of a chunk and a position, as a parameter bound to a new
tuple on every edge, and its reader's inlined returns join an allocated option and a constant one, a datum of the
unit's static data, at another ([benchmarks.md](benchmarks.md) §20). MLton's SSA passes
tuples flattened (its `localFlatten` and `deepFlatten` passes); LLVM's SROA splits only allocas, which do not flow
through phis.

**Origins and groups.** An *origin* makes an object: a `quest_alloc` of a constant size and a layout, or the address of
a datum that is never written (`symbol`, plus a constant offset into a table of constants). A value points into an
origin's object when it is the origin's, a `ptrAdd` of a constant to such a value, a word's load whose objects store
pointers there, or a block parameter that every edge taken binds to such values, at one offset. Parameters may be bound
to one another: a search carries `maybe.none` round a loop that may replace it with a `some`, so the loop header's
parameter and the body's join are each bound to the other. Every parameter is assumed to be one until an edge binds it
to a value that is neither a pointer nor such a parameter, so that a cycle of them is found whole; a parameter one of
whose bindings found no group leaves its group. Origins whose pointers meet are in one *group* (a union-find forest), whose objects have one layout: each word holds values of one type, or
pointers into another group's objects, which it stands for in turn (an option holding a tuple is replaced by the
option's tag and the tuple's words). A word some objects do not store, or a constant does not reach, is a zero there.

**What is left.** An allocation's words must be stored once, in its block, through its own pointers, and not read
through them before its last store; a constant's never. A group's pointers may only be loaded from by whole words,
offset, tested for being a proxy (which folds, as in §4.2), stored into another group's object as it is made, passed
to parameters of their own group, and passed to a write barrier (`quest_barrier`, `quest_barrier_slot`), which keeps no
pointer and goes with the object, as in §4.2. Anything else leaves the whole group: a call, a return, a comparison, a
store after the object is made (a `var` field's), a parameter also bound to another value, words of different types, or
a group nesting in itself (a list's cells), whose values would have no end. The analysis repeats until none more is
left, the blocks reached depending on which proxy tests fold, as in §4.2.

**The replacement.** Each pointer parameter becomes its group's values; each edge passes the values of the pointer it
bound; each load becomes the word's value, or, for a nested pointer, its object's values; an allocation's values are
its stored ones (and zeros for the rest), known at its last store; a constant's are its datum's words. The objects,
their stores, offsets, loads, and proxy tests go, and the blocks only a proxy's arm reached are dropped. First, the
parameters nothing uses but jumps to parameters nothing uses are dropped: promotion leaves them where a variable's slot
is live across a loop its value is not (the last of a loop's tuples, carried round an outer loop from a null at the
entry), and such a parameter, bound to a pointer and to a null, would leave its group whole. The questlang test
`ssa_scalars` shows each case.

## 5. Functions and Units

A **function** has a symbol (its C name), whether other units call it, its parameters (the entry block's), its result
types, its signature (§2.2), its blocks, and its stack slots (each a size and an alignment in bytes). A **unit** has its
functions and its **data**: each datum a symbol, whether other units refer to it, whether it is written at run time, and
its contents, 8-byte aligned: zeros (a global, a module's record and its initialized flag), a C string's text and its
NUL (a literal, a name in a descriptor or the function table), or words, each an integer or a symbol's address plus a
byte offset (a descriptor and what its extra field points at, an offset table, a tag map, a static closure, the function
table, the layouts of the objects the unit allocates: a `quest_layout_<tag>` and its kinds `qlk_<tag>`, packed eight to
a word, laid out by `ssa/statics` from `repr/objectLayout`, docs/collector.md §3.2, and the unit's root table
`qr_roots`: the address and words of each global that may hold a pointer and of each module record, ended by a null
slot, which `qr_register_dicts` registers). A store of a `ptr` or `val` word into an existing object is followed by a
call of `quest_barrier` or `quest_barrier_slot`, with no other call between the two (docs/collector.md §3.5). Words lay
out the runtime's structs on a little-endian target, a narrow field in the low bytes of its word.

The builder makes, besides the IR's functions and the module initializers and `main`:

- the data of `ir.StaticData`'s descriptors (`ssa/statics`, from `repr/staticdata`'s descriptions), offset
  tables, and tag maps, as the C printer's declarations define them, and of the layouts the unit's allocations
  registered (`objectLayout.Table` in the unit builder), added once every function is built;
- each function type's adapter, thunk, and invoker (`quest_adapt_<tag>`, `quest_thunk_<tag>`, `quest_invoke_<tag>`),
  as `codegen/c/declarations` writes them in C;
- a module file's exported functions (`qv_<module>_<member>`), at its interface's C signatures;
- the function table (`qr_funcs`) and `qr_register_dicts`, which registers it and the offset tables of records the
  unit views at supertypes;
- a static closure (`<function>_closure`) of each function, and the data of globals and strings.

What a unit refers to and does not define is another unit's or the runtime's.

## 6. The Textual Form

`--stop-after ssa` prints a program unit's SSA; its goldens (`tests/golden/ssa`) are the self-hosted compiler's own,
one for every run test that has an `ir_core` dump (arm64.md §3.2). Values print as `%n`, blocks as `bN`, a
function's stack slots as `bytes:alignment`, a load or store with its width (`load1s` sign-extends a byte; an invariant
load, §2.1, ends `invariant`), and a call
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
`ssa_promote`, `ssa_escape`, `ssa_scalars`, `ssa_constants`, `ssa_valuenumbers`, `ssa_selects`, `ssa_tables`,
`ssa_accumulate`, `ssa_tailcalls`, `ssa_tailjumps`, `ssa_trampolines`, `ssa_unproxies`, and `ssa_allocations` read small
functions, run their pass and the verifier, and print the functions before and after; and a program's SSA can be cut
down to the functions that show a bug.

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

**The barrier check** (`ssa/barriers`) runs with the verifier. The collector's generations need a write barrier
after every store of a pointer into an object a collection may have seen, before the next call that may collect
([collector.md](collector.md) §3.5), and the builder emits them so (§4): a store's barrier follows it, and an object
still being initialized when a call intervenes is logged before each later call and after its last store. The
check holds the passes to that, by a forward dataflow over each function with stores: the allocations still young
(a `quest_alloc`'s result, until a call that may collect: a function's of the program, or a runtime function's that
allocates), met by intersection, and the stores owed a barrier, met by union. A store of a `ptr` or a `val` that is
not a symbol's address or null, at an address that comes (through `ptrAdd` and `copy`) from a value that is neither
young nor a slot's or a symbol's address, is owed one; the object's barrier on that value
answers every store into it, the slot's the stores at its address; and a store still owed at a call that may
collect, a return, or a tail call is a problem, reported with its block and instruction. A missed barrier otherwise
shows only when a collection falls between the store and the next barrier, which the `stress` mode makes likely
and this makes certain, at compile time, for every function compiled. The questlang test `ssa_barriers` checks the
problems it reports on functions built by hand.

## 8. The C Printer

`codegen/c/ssac` prints a unit's SSA as C (arm64.md §3.14), an oracle for the SSA and the backends after it: with
`--backend ssac`, or `--unit-backend UNIT=ssac` for one unit, a build compiles units through it (arm64.md §3.12). The
questlang test `ssac_print` prints a unit built by hand, and `tests/python/test_ssac.py` compiles its golden.
