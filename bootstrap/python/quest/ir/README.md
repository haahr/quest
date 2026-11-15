# bootstrap/python/quest/ir: the bootstrap compiler's IR and its passes

This package is the bootstrap compiler's middle end. It lowers a typed program (from
[`../typechecker`](../typechecker)) into the intermediate representation that [`docs/ir.md`](../../../../docs/ir.md)
specifies, runs the passes that make specialization, closures, representations, and run-time type descriptors
explicit, and hands the resulting *described* unit to the C printer in [`../codegen/c`](../codegen/c). The C printer
is the bootstrap's only backend; it prints what the IR says and makes no representation decisions of its own.

The self-hosted compiler's [`questlang/ir`](../../../../questlang/ir/README.md) is a port of this package, module for
module, and its README is the full introduction to the IR: A-normal form, join points, variables as objects, shapes
versus types as written, and what each pass does. This page summarizes the flow and what differs here.

## The flow

[`pipeline.py`](pipeline.py) lists the passes after lowering in `IR_PASSES` and runs them in `run_passes`, verifying
the unit after each when `QUEST_CHECK_IR=1`; [`../codegen/backend.py`](../codegen/backend.py) calls it.

| Stage | Module | What it does |
|---|---|---|
| Core | [`lower.py`](lower.py), [`captures.py`](captures.py) | typed AST to ANF IR; captured mutable locals boxed |
| Specialized | [`specialize.py`](specialize.py) | clones polymorphic functions for some type arguments |
| Closed | [`closure.py`](closure.py) | lifts every function and makes closures of them |
| Represented | [`represent.py`](represent.py), [`slots.py`](slots.py) | inserts every representation conversion |
| Described | [`describe.py`](describe.py) | gives every run-time use of a type its descriptor; lists static data |

The nodes are plain mutable dataclasses in [`nodes.py`](nodes.py), with identity equality, built once by lowering and
rewritten in place. A small example, `twice(:Int addTo(1) 3)` for a polymorphic `twice(A::TYPE f: All(x: A) A x: A)`,
ends up described as (`questboot --stop-after ir_described`):

```
let %1: Fun(x: Int): Int = call addTo.1(1)
let %2: Fun(x: A): A = convert(%1, adapt)
let %3: A = convert(3, box)
let r: A = call twice.1 [descriptor(Int)](%2, %3)
let r.1: Int = convert(r, unbox)
```

`twice` is compiled once for every `A`, so `3` is boxed into a generic word, the closure is adapted to take and return
words, the type argument has become the static descriptor of `Int`, and the result is unboxed. The layouts and
representations these decisions rest on come from [`../repr`](../repr/README.md).

[`walk.py`](walk.py) holds the traversals the passes share, including the IR's explicit field tables (`fields_of`,
`rebuild`, `contents`, `replace_vars`), written out per node class rather than by reflection so that the Quest port
could follow them one for one; `tests/python/test_traversals.py` checks them against the dataclasses.
[`printer.py`](printer.py) writes the textual form, and [`verify.py`](verify.py) with
[`verify_core.py`](verify_core.py) checks each stage's invariants. The IR interpreter,
[`../interpreter/ir_interp.py`](../interpreter/ir_interp.py), runs a unit at any stage and serves as a test oracle
against the tree-walking interpreter.

## How it differs from questlang/ir

- **No simplifier.** The self-hosted compiler optimizes the Core IR (constant folding, inlining, contification into
  loops) before specialization; the bootstrap goes straight from Core to Specialized. Since its IR dumps therefore
  differ, the IR goldens are the self-hosted compiler's; the two share behavior goldens (program output).
- **No unboxed results** and **no thunks pass.** The C printer here makes the adapters, type-application thunks, and
  closures of external functions itself as it prints; the self-hosted compiler turns them into IR functions so that its
  several backends compile them alike.
- **Fewer globals and known closures.** Every variable a top level binds outside a loop is a global here; the
  self-hosted compiler keeps more of them local, and calls known closures directly.
- **No phrase units.** The bootstrap has no JIT, so lowering has no entry point for REPL inputs; its REPL interprets.
- **No source positions in dumps.** Nodes that can raise keep their source offset for error messages, but the printer
  shows none.

## Further reading

- [`docs/ir.md`](../../../../docs/ir.md): the IR's specification, which names this package's modules.
- [`docs/c-representation.md`](../../../../docs/c-representation.md): the ABI the represent and describe passes target.
- [`docs/codegen-c.md`](../../../../docs/codegen-c.md): the C printer that consumes the described IR.
- [`docs/testing.md`](../../../../docs/testing.md) §2: golden tests, including the IR stages and the `run_ir` phases.
