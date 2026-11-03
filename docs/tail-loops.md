# Plan: Loops of Mutual Tail Calls and of Accumulated Recursion in the SSA

Two passes of the SSA that turn recursion into loops, as clang does to the C backend's output and the SSA's backends
(`ssac` and `arm64`) do not, after [benchmarks.md](benchmarks.md) §13 found that what arm64 loses to C is mostly four
small recursions. Two of those (tak and tailfib) are not losses: clang calls `tak(33 22 11)` once for the whole
count, and folds `fib(44)` to a constant, which no pass here is meant to match. The other two are:

- **even-odd** (3.36 of C's time through arm64): `even1` and `odd1` tail-call each other. arm64 branches from each
  to the other, pushing and popping a frame at each step; clang inlines one into the other, and the self tail call
  left becomes a loop that does two steps in three instructions.
- **fib** (8.89 of C's time, of which a factor of 8 is the count clang hoists): `fib(n - 1) + fib(n - 2)`. clang
  keeps the first call and makes the second a loop, adding into an accumulator (LLVM's tail recursion elimination
  of an associative operation), so that each level makes one call, not two.

The IR's contification ([ir.md](ir.md) §8.6) makes loops of local functions with one outside call; `even1` and
`odd1` are each called from outside once, but from different functions, and fib's calls are not tail calls, so
neither is its. The SSA's passes are the place: both backends that need the loops gain, and the JIT with arm64.

---

## 1. Decisions

- **Two passes of the pipeline** ([ssa.md](ssa.md) §4.1): `accumulate` (§2), after `valueNumbers` and before
  `tailCalls`, since it rewrites returns and calls that `tailCalls` would otherwise mark; and `tailJumps` (§3), after
  `tailCalls`, since it acts on what `tailCalls` marks. Each can be left out with `QUEST_SKIP_PASSES` and has its dump
  (`ssa_accumulate`, `ssa_tailJumps`).
- **A self tail call stays a tail call.** arm64's selection already makes a tail call of the function itself a jump
  to its first block, and clang does the same to `ssac`'s `return f(...)`; neither pass makes one a jump in the SSA,
  except `accumulate`, whose loop is not the function's first block.
- **Copies, not merged functions.** `tailJumps` copies into a function the functions it is mutually tail-recursive
  with, rather than merging a group into one function with an entry per member (MLton's approach), which would
  change the functions' symbols and closures. A function's own callers, closures, and symbol are left as they are.
- **Integers only, for `accumulate`.** `Int` arithmetic wraps, so `add`, `mul`, `and`, `or`, and `xor` are
  associative and commutative and an accumulator gives the same result in any order; real arithmetic is neither.
- **The self-hosted compiler's alone,** as its SSA is ([testing.md](testing.md) §2.8).

## 2. Accumulated Recursion (`ssa/accumulate`)

A function qualifies when it returns one `int` (passed as a word), no stack slot's address escapes from it
(`tailCalls`' test, which covers a `try`: a loop reuses the frame that a call would have made anew), and it has a
**site**: a block whose last two instructions are a call of the function itself, `r = call f(args)`, and `t = op x r`
(or `op r x`), with `op` one of the five and `x` not `r`, and which returns `t`, directly or through blocks that only
pass it on (`tailCalls`' `returnsThrough`). The first site's `op` is the function's; sites of another are left.

The function becomes:

- **A loop header.** A new block takes the entry's instructions and terminator, with parameters of its own for the
  function's parameters, which replace them everywhere, and one more, the accumulator. The entry jumps to it with its
  parameters and `op`'s identity (0, or 1 for `mul`, or all ones for `and`).
- **Each site** loses its two instructions and jumps to the header with the call's arguments and `acc op x`.
- **Each self tail call** (a call of the function whose result the block returns, as for a site) jumps to the header
  with its arguments and the accumulator unchanged; left a tail call, arm64 would jump to the entry and lose the
  accumulator.
- **Each return** of `v` returns `acc op v`. A call of another function whose result is returned is no longer in
  tail position, as it must not be: its result is combined with the accumulator.

fib then makes one call a level, in a loop down the other. A call that is neither a site nor a tail call, like fib's
first, is left; it starts from the entry, with the identity.

## 3. Mutual Tail Calls (`ssa/tailJumps`)

The unit's functions and the tail calls between them (direct calls, by symbol, of the unit's own functions) form a
graph; its strongly connected components are the groups of mutually tail-recursive functions (Tarjan's algorithm).
In a function `f` of a group of more than one, each other member `g` is **copied** into `f` when:

- `g` has no stack slots and no `try`, so that its blocks need nothing of a frame;
- each of `g`'s parameters is passed as a word, a real, or a pair's word (not a byte, a C int, or memory), so that
  a jump passes it as a call would;
- `g`'s results and their passing are `f`'s, so that its returns are `f`'s;
- and the copies' instructions total at most 100 (`budget`), so that a large group grows no function by much.

A copy is `g`'s blocks, values, and instructions renumbered into `f`. Then each tail call, in `f`'s blocks and the
copies, of a member copied into `f` becomes a jump to its copy's first block, with the call's arguments; a tail call
of `f` itself stays, for the backends to make a jump. even-odd's `even1` then holds a copy of `odd1`, whose tail call
of `even1` is a self tail call: one loop, without a frame at each step.

## 4. Measurement

- **Counts:** a temporary count, not kept, of the functions each pass changes, over the 46 programs and the compiler
  itself, to see what else the passes reach (the lists' `length`s and folds may be sites).
- **Times:** even-odd and fib, and any program the counts show changed in a loop, through arm64 and `ssac`, with
  `tools/perf/variants.py` and `tools/perf/timeit.py --rounds 5`, each pass against `QUEST_SKIP_PASSES` without it.
- **Compile times** of the driver, through arm64, before and after: neither pass should take a measurable share.

## 5. Testing

- `tests/source/questlang/ssa_accumulate.quest` and `ssa_tailjumps.quest`, as `ssa_tailcalls`: small functions as
  text, each printed before and after its pass and verified, with every condition's case, met and not.
- A program of each, `tests/source/language/accumulated_recursion.quest` and `mutual_tail_calls.quest`, run through
  every backend by the usual phases (the interpreters' among them, so no deeper than they recurse), with their SSA
  golden showing the loops.
- The SSA goldens regenerated, and tools/check.

## 6. Steps

1. This plan.
2. `ssa/accumulate`, its tests, the SSA goldens, and ssa.md §4.1.
3. `ssa/tailJumps`, its tests, the SSA goldens, and ssa.md §4.1.
4. The counts and times (§4), recorded here; then this plan retired into ssa.md and benchmarks.md.
