# questlang/codegen/arm64: the native backend

This directory compiles a unit's SSA ([`../../ssa`](../../ssa)) to 64-bit ARM machine code for Darwin (macOS on Apple
silicon). It is the compiler's default backend: the compiler itself, the standard library, and user programs are all
compiled through it unless `--backend` says otherwise. Its input is an `ssa.Unit` whose SSA passes have run, so its
values are already machine words (`int`, `ptr`, `real`, and `val`, a tagged-or-pointer `QVal` word), its memory
accesses byte offsets, and its calls carry C signatures. Its output takes two forms: assembly text (`.s`), which clang
assembles and the build links with C units and the runtime, and encoded machine words with relocations, which the
JIT ([`../../jit`](../../jit)) loads into memory directly. Both come from the same instructions.

## From SSA to machine code

[`codegen`](codegen.int.quest) drives each function through a fixed sequence, then assembles the unit
(`assembleUnit` for text, `encodeUnit` for the JIT):

| step | where | what it does |
|---|---|---|
| select | [`select`](select.int.quest) | SSA instructions become arm64 instructions over virtual registers |
| allocate | [`../machine/regalloc`](../machine/regalloc.int.quest) | a jump's arguments joined with its parameters where they can be (`coalesceAndAllocate`), then virtual registers get registers or frame slots |
| rewrite | `regalloc.rewrite` | spill loads and stores, and moves between registers, are added |
| frame | `codegen` | prologue, epilogues, slot offsets, callee-saved registers, frame maps |
| peephole | [`peephole`](peephole.int.quest) | far conditional branches relaxed; adjacent loads and stores paired |
| emit | [`printer`](printer.int.quest), [`asm`](asm.int.quest) or [`encode`](encode.int.quest) | text, or words |

**Instruction selection** is where arm64's own idioms appear. A constant that fits becomes an immediate operand; a
comparison used only by the branch after it becomes a compare-and-branch (`cbz` when comparing with zero); a load
from a pointer plus a constant folds the constant into the addressing mode. The calling convention, Apple's variant
of AAPCS64 (the ARM procedure call standard: integer arguments in `x0`–`x7`, reals in `d0`–`d7`, the rest on the
stack), is expressed as moves to and from fixed physical registers around each call and at the function's entry, so
that the register allocator, which knows nothing of arm64, sees them as constraints.

**The instructions are data.** [`minst`](minst.int.quest) defines `Op`, an option with one case per operation (with
its immediates, condition, addressing mode, or label), and `Inst`, an `Op` with its registers. Only this directory's
modules case on `Op`: `minst` itself, selection, `codegen` (frames, calls, and jump tables), the peephole pass, the
printer, and the encoder. The shared code sees an instruction through the machine-function view in
[`../machine`](../machine/README.md), with the `Op` in a side table. Labels, unwind directives, and source
positions are instructions too, so a function's code is one sequence. [`target`](target.int.quest) numbers arm64's
registers for that shared code and says which are allocatable, which a call preserves, and which are kept as scratch.

For example, the recursive factorial

```quest
let rec fact(n: Int): Int = if n is 0 then 1 else n * fact(n - 1) end
```

compiles to a loop with no call and no frame, because an SSA pass made the recursion an accumulating loop:

```
_qf_fact:
	mov x12, #1           ; the accumulator
Lf0_b4:
	cbz x1, Lf0_b2        ; n is 0?  (x0 is the closure, x1 is n)
	sub x13, x1, #1
	mul x12, x12, x1
	mov x1, x13
	b Lf0_b4
Lf0_b2:
	...                   ; x0 := x12 * 1; ret
```

## What compiled Quest needs from the backend

Beyond ordinary code generation, three features of the runtime shape this backend.

- **Exceptions.** A `try` stores a handler record and pushes it on the runtime's handler chain; a `raise` resumes
  execution beside the `try`, in a block that a raise enters with every register dead, so the handler reloads what it
  needs from the frame. A function that enters a `try` saves every callee-saved register, since the raise skips the
  epilogues of the functions in between ([docs/arm64.md](../../../docs/arm64.md) §3.6).
- **The garbage collector.** The collector must find the pointers in each compiled frame. For each call, the backend
  records which callee-saved registers and frame words hold live values across it, each as a pointer or as an
  *ambiguous* word (an `int` or a `QVal`, which may or may not hold a pointer, and which the collector validates
  before treating it as one), and emits a per-unit *frame table* of these maps for the collector (`frameMaps`; §3.13).
- **Debugging.** Each instruction can carry its source position, which becomes `.loc` directives and a DWARF line
  table, so lldb can step through Quest source ([`asm`](asm.int.quest)'s `debugInfo`; §3.16).

## Spelling and encoding

[`printer`](printer.int.quest) is the only module that writes instructions as text; it expands the
pseudo-instructions (an arbitrary 64-bit constant as `mov` and `movk`s, a symbol's address as `adrp` and `add`).
[`asm`](asm.int.quest) holds everything specific to Darwin's assembler and object format: symbol names with their
leading underscore, sections, the relocations that address a symbol (directly, or through the GOT for one defined
elsewhere), and data directives, so that another object format would replace
only it.

[`encode`](encode.int.quest) does the assembler's job for the JIT: each instruction becomes its 32-bit word, labels
are resolved, and references to symbols are left as relocations for the JIT's loader, as in an object file. The
encoder's check (`tests/self-hosted/encoder.py`) compares its words with what the system assembler makes of the
printer's text, which keeps the two forms in agreement.

## Connections

[`../native`](../native.int.quest) calls `assembleUnit` after the SSA pipeline, for
[`../backend`](../backend.int.quest), and [`../../jit/target`](../../jit/target.int.quest) calls `encodeUnit`. What
the backend cannot compile raises `unsupported`, naming the construct; there is no fallback to C. Units it compiles
link with units the C backend compiles, since both follow the same C ABI and the shared layouts of
[`../../repr`](../../repr); mixed builds and the ssac printer ([`../c`](../c/README.md)) are how its bugs are located.
The bootstrap compiler has no counterpart.

## Further reading

- [docs/arm64.md](../../../docs/arm64.md): the backend's design, in particular §3.3 (layout and the ABI), §3.5
  (instruction selection), §3.6 (exceptions), §3.7 (tail calls), §3.10–3.11 (frames and emission), §3.13 (the
  collector), and §3.17 (machine instructions and targets)
- [docs/jit.md](../../../docs/jit.md) §3.5, the encoder
- [docs/benchmarks.md](../../../docs/benchmarks.md), the backend's performance against C and MLton
