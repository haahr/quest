# questlang/codegen: the backends

This directory turns the compiler's intermediate representation into code a machine can run. Its input is a *unit*
(a program, a module file, or a REPL input) that the IR's passes in [`../ir`](../ir) have already lowered as far as
they go: closures converted, every value's representation chosen, every run-time type descriptor placed. Its output
is text that the build engine ([`../build`](../build)) hands to clang: C source for the C backends, Darwin arm64
assembly for the native one. The JIT ([`../jit`](../jit)) takes the native backend's output in a third form, encoded
machine words, and loads it into the running compiler.

## Three backends

A unit is compiled by one of three backends, named by strings the driver and the build pass around:

| backend | path | output |
|---|---|---|
| `c` | IR → [`c/printer`](c/printer.int.quest) | C |
| `ssac` | IR → SSA ([`../ssa`](../ssa)) → [`c/ssac`](c/ssac.int.quest) | C |
| `arm64` (the default) | IR → SSA → [`arm64/codegen`](arm64/codegen.int.quest) | arm64 assembly |

The **C backend** prints the IR's structured code as structured C, and leaves layout, the calling convention, and
`setjmp`-based exceptions to the C compiler and the runtime's headers. The two **SSA backends** first build the IR into
a low-level, target-independent SSA form (static single assignment: every value defined once, control flow as blocks
and edges), whose values are machine words and whose memory accesses are byte offsets, and run the SSA's own
optimizations on it. The **arm64 backend** then selects machine instructions, allocates registers, and lays out
frames itself. **ssac** prints the same SSA as low-level C instead; it exists as an oracle, so that a test that fails
under arm64 and passes under ssac points at a bug after the SSA, and one that fails under both at a bug in it or
before it.

The difference shows on a small function. Given

```quest
let rec fact(n: Int): Int = if n is 0 then 1 else n * fact(n - 1) end
```

the C backend prints a recursive C function, `qf_fact(void *_raw_env, QInt l_n)`, whose first argument is the
closure's (unused) environment. The arm64 backend's code for the same function has no call at all: the SSA's
accumulation pass ([`../ssa/passes/accumulate`](../ssa/passes/accumulate.int.quest)) made the recursion a loop
before instruction selection saw it.

## Choosing a backend

[`choice`](choice.int.quest) records which backend compiles each unit of a build: `--backend B` names one for every
unit, and each `--unit-backend UNIT=B` overrides it for one unit, named as the build's manifest names it (a module by
its canonical name, the program as `main`). Mixed builds, where some units are C and others arm64, work because both
follow the same C ABI and the same data layout; they are how a miscompile is narrowed to one unit. There is no
fallback: what the chosen backend cannot compile is an error, never silently compiled by another. `choice` also
knows each backend's file names (an arm64 unit writes `.s` where the others write `.c`), and the build records a
unit's backend in its manifest, so that changing it makes the unit stale.

[`ssaBackend`](ssabackend.int.quest) holds what the two SSA backends share: each one's policy for the SSA's passes
(`policyFor`), which the driver's SSA dumps follow too, and a unit's SSA built and lowered under it (`loweredSSA`),
which `native` and the JIT compile.

[`backend`](backend.int.quest) is the one entry point the driver, the build engine, and the module compiler call. It
lowers a typed program or module file to the IR (`ir/lower`), runs the IR's passes (`ir/pipeline`), and dispatches on
the backend's name. Each backend raises its own exception for what it cannot compile; `backend` raises each again as
its own `unsupported`, so callers handle one exception whatever the backend. For a module file it also adds a datum
holding the interface's fingerprint, by which the JIT checks that a module linked into the compiler matches its
source ([docs/jit.md](../../docs/jit.md) §3.3).

## The subdirectories

- [`c/`](c/README.md): the C printer, the declarations it writes (structs, offset tables, descriptors), interfaces'
  C headers, and ssac.
- [`machine/`](machine/README.md): what any native target shares: the shape of a machine function, liveness, and the
  linear-scan register allocator, parameterized by a target description.
- [`arm64/`](arm64/README.md): the arm64 target: instruction selection, the instructions as data, frames and calls,
  peephole passes, the assembly printer, and the encoder the JIT uses.

The bootstrap compiler has the C backend alone: its entry point is
[`bootstrap/python/quest/codegen/backend.py`](../../bootstrap/python/quest/codegen/backend.py), and its printer is in
[`bootstrap/python/quest/codegen/c`](../../bootstrap/python/quest/codegen/c/README.md).

## Further reading

- [docs/arm64.md](../../docs/arm64.md) §2 (the pipeline from the IR to each backend) and §3.12 (choosing backends and
  mixing units)
- [docs/codegen-c.md](../../docs/codegen-c.md), the C backend
- [docs/ssa.md](../../docs/ssa.md), the SSA the native backends share
- [docs/compiler-organization.md](../../docs/compiler-organization.md) §2, where the backends sit among the layers
