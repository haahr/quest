# One Object per Closure

A plan for the task-list entry "A closure and its environment are two allocations": a closure becomes one object, its
code pointer in the first word and its environment inline after it, in every native backend and both compilers. wasm
already builds closures this way ([wasm.md](wasm.md) §3.1), and nothing above the backends changes: the IR keeps
`closure f {captures}` and `env_field(env, i)` ([ir.md](ir.md) §8.2), and the interpreters keep theirs.

---

## 1. Today

A closure that captures anything, or carries descriptors, is two heap objects:

- **The closure,** `QClosure { void *fn; void *env; }` (`runtime/quest_runtime.h`), 16 bytes with the shared layout
  `quest_layout_closure` (P, P).
- **Its environment,** one object per function's closures, its layout `env_<code>` per function: the descriptors the
  closure supplies, then the captures. C lays it out as `struct QEnv_<code>` (`codegen/c/printer`'s `envStruct`), and
  the SSA builder as a word per part (`ssa/build/control`'s `makeClosure`); each unit's environments are its own, so
  the two may differ ([arm64.md](arm64.md) §7).

The code takes the environment as its first argument: an indirect call loads `fn` and `env` and calls `fn(env, ...)`;
a direct call of a known closure passes `callee->env`, or null when it captures nothing. Three other kinds of closure:

- **Static closures,** `{code, NULL}` in static data, for a function that captures nothing: each lifted function's
  `<code>_closure`, externals' thunks, and the runtime's 22 operator closures (`qv_sym_plus_closure`, ...).
- **Adapt plans** (a function value converted to a supertype, `ssa/build/aggregates`, the C printer's adapt plan): a
  `QClosure` `{qa_adapt..., orig}`, whose environment *is* the adapted closure.
- **Run-time adapters** (`quest_adapt_<tag>`, `codegen/c/declarations` and `ssa/build/adapters`): a `QFunAdapterEnv
  { orig, from, to, direct }` (`runtime/quest_types.h`, layout `quest_layout_adapter_env`) and a `QClosure` over it.

Every closure of a let-rec group has its own environment; a capture of a group member is stored into the environment
after the group is made (the deferred captures). No environment is shared.

### 1.1. What it costs

Counted 2026-11-20 at 918f334c, with a temporary counter by layout in the runtime's `allocations` mode (each heap
allocation whose layout is `QClosure`, and each whose is an `env_` one):

| Program | Allocations | Closures | Environments | Up to, merged |
|---|--:|--:|--:|--:|
| The compiler's build (stage 2 compiling the driver) | 1,097 million | 77.5 million | 35.8 million | 3.3% |
| The MLton benchmarks, all 46, `--scale 0.05` | 8,410 million | 1,382 million | 1,426 million | 16.3% |

- **The share that merging removes** is the heap closures that have a heap environment: at most the lesser of the two
  counts in each program. ratio-regions 38.9 percent of its allocations, knuth-bendix 36.1, peek 22.2, logic 21.0, ray
  20.0, model-elimination 19.6, tsp 14.2, boyer 13.9, hamlet 13.6, vliw 11.2.
- **The compiler's closures** are 41.7 million more than its environments: adapt plans, which have no environment of
  their own and which merging does not remove (they stay two words). They are 3.8 percent of the build's allocations,
  more than the merge saves there, and worth a look of their own (§7).
- **Where environments outnumber closures** (count-graphs 52.5 million environments against 13.5 million closures, tsp,
  zebra, logic, smith-normal-form), escape analysis has put the closure on the stack and its environment escaped:
  the environment is passed to the code, and a call's argument escapes ([ssa.md](ssa.md) §4.2). Merged, such a closure
  is one heap object, as its environment is now; §5 is what would put it on the stack.
- **Bytes** fall by 16 a merged closure (the environment's header and the `env` word): about 1.1 percent of the
  compiler's.

## 2. The Representation

A closure is one object:

```
word 0      the code pointer
words 1..   the descriptors the closure supplies (d_0, ...), then the captures (c_0, ...), as the environment held them
```

- **`QClosure` is the common prefix,** `typedef struct QClosure { void *fn; } QClosure;`, 8 bytes: what code outside
  the closure's unit may read, and all it may read. A unit's own closures are `struct QClosure_<code> { void *fn;
  descriptors; captures; }` in C, and the same words in the SSA, each laid out by its own unit as environments are
  now: a closure crosses units only as a pointer whose word 0 is read.
- **The code's first argument is the closure itself.** The prologue reads descriptors and captures from it at
  `8 * (1 + i)` in the SSA, `((struct QClosure_<code> *)_raw_env)->c_i` in C. `env_field(env, i)`'s offsets gain
  the code pointer's word, and that is the whole change to the code's body.
- **The layout** is one per function, `closure_<code>` (renaming `env_<code>`), FIXED, word 0 scalar: the code pointer
  is never a heap address (code is static or the JIT's executable memory, outside the heap), so the collector need
  not look at it. `quest_layout_closure` becomes the adapt plan's two words, S, P.
- **Static closures** are `{code}`, one word, as before headerless in static data; their code ignores its first
  argument, as now.
- **Adapt plans** stay two words, `{qa_adapt..., orig}`, now an ordinary one-capture closure: the adapter's code reads
  `orig` at offset 8 of its first argument instead of taking it as the argument.
- **Run-time adapters** become one object: `QFunAdapterEnv` gains `fn` as its first word (`{ fn, orig, from, to,
  direct }`, 40 bytes, layout S, P, P, P, S), and `quest_adapt_<tag>` allocates it alone. `QFunAdapter` and
  `QFunInvoker` keep their signatures.
- **Identity** is unchanged: `is` and `identityHash` take the closure's address, which is now the one object's.

## 3. Calls

- **Indirect:** load word 0, call it with the closure as the first argument. One load instead of two (on arm64 the two
  may already be one load pair, so the gain there is the register).
- **Direct, of a known closure:** pass the callee closure itself, or null when it captures nothing, as now. The load
  of `callee->env` goes.
- **Type applications that are not thunks** (`callClosureWith`, the C printer's `clos->fn(clos->env, descs)`) and the
  exported wrappers `qv_<module>_<member>` (`ssa/build/adapters`, the C printer's `exportedFunctions`) pass the
  closure as indirect calls do.
- **The runtime** calls no closure itself; it calls `meta->adapt` and `meta->invoke`, which compiled code supplies.

## 4. Making One

- **The SSA builder** (`ssa/build/control`'s `makeClosure`) allocates `8 * (1 + parts)` bytes with `closure_<code>`,
  stores the code pointer and the parts in its initializing stores, and no longer allocates the `QClosure`.
- **The C printers** (both compilers) do the same with `struct QClosure_<code>`: one `quest_alloc`, `->fn` and the
  parts inside `beginInit`/`initBarrier`.
- **Let rec:** every closure of the group is made first, then the deferred captures are stored into the closures, as
  they are stored into the environments now, each followed by the barrier (`quest_barrier`), since other allocations
  came between. A closure capturing itself stores its own address into itself.
- **Escape analysis** sees one candidate where it saw two. A merged closure stays on the stack exactly when its
  environment would have: when it is never passed, stored, or returned, which a closure that is called is not (§5).

## 5. A Later Step: the First Argument Does Not Escape

A call's argument escapes ([ssa.md](ssa.md) §4.2), so a closure passed to its own code is a heap object even when it is
made, called, and dropped in one function: count-graphs 18.3 percent of its allocations, tsp 14.3, smith-normal-form
5.6, zebra 2.7, logic 1.9, 0.7 percent of the MLton benchmarks in all (the environments in excess of closures in
§1.1). The rule that would keep it on the stack: an argument passed at position 0 of a direct, non-tail call to a
function of the same unit does not escape when that function uses its parameter 0 only as the address of loads. A
lifted function's code does (its parameter 0 is read only by `env_field` loads, and an adapter's by the load of
`orig`); a tail call's arguments still escape, since the caller's frame is gone. The pass would compute, per function
of the unit, whether its parameter 0 is load-only, before its rounds.

It depends on §2–4 and is measured by itself, so it is a step of its own.

## 6. Steps

1. **The representation, in one change** (an ABI change, 88), since C units and SSA units are linked together and
   both compilers' C runs on the same runtime. **Done**, with `language/closure_objects` as its test:
   - the runtime: `QClosure` (one word), its static asserts, the 22 operator closures and their trampolines,
     `QFunAdapterEnv` with `fn`, `quest_layout_closure` (S, P) and `quest_layout_adapter_env` (S, P, P, P, S), and the
     function-type descriptor's size (`quest_types.c`'s `sizeof(QClosure)`, which then agrees with
     `quest_serialization.c`'s `sizeof(QClosure *)`);
   - the self-hosted compiler: `repr/runtimeLayout` (`QClosure`'s words), `repr/objectLayout` (`closure_<code>`), the
     SSA builder (`control`'s `makeClosure`, `envField`, the deferred captures, `unit`'s prologue and static closures,
     `calls`' direct and indirect calls, `aggregates`' adapt plan and `callClosureWith`, `adapters`' exported wrappers
     and run-time adapters), and the C printer (`makeClosure`, `envStruct`, `envLayoutOf`, the prologue, the deferred
     captures, `callClosure`, the type application, `exportedFunctions`, the adapt plan, and `declarations`' run-time
     adapters); arm64, ssac, and the JIT follow from the SSA;
   - the bootstrap: `codegen/c/printer.py` and `declarations.py` the same way, `repr/objectlayout.py`;
   - wasm: nothing, its closures are already one object; the IR, the interpreters: nothing.
2. **The measurement:** the counts of §1.1 again, the MLton benchmarks' times at `--scale 0.25` (run.py `--clean`),
   and the compiler's build, recorded in benchmarks.md as a section of their own.
3. **The first argument that does not escape** (§5), measured the same way.

## 7. Tests and Docs

- **Tests:** the suites as they are, which make and call closures of every kind on every backend (`tools/check`, its
  stress tier first: a wrong layout or a missed barrier on a deferred capture is what `layouts` and `stress` catch); a
  test of a let-rec group whose members capture each other and themselves, called after collections; the SSA goldens
  that show closures (19 under `tests/golden/ssa/`), `codegen_runtime_layout`'s golden, both ABI corpora, and
  `tests/python/test_runtime_layout.py`, whose negative test names `offsetof(QClosure, env)` and needs another field.
- **Docs:** c-representation.md §6.1–6.3, codegen-c.md §7.1, runtime-design.md (closures), arm64.md §7, collector.md
  §1 and §3.2 (the closure's words), ir.md §8.2's note on what the backends make of `closure`, `runtime/README.md`, and
  benchmarks.md §3.2's last bullet, which this does.
- **Adapt plans,** 3.8 percent of the compiler's allocations, are a separate question: which conversions make them,
  and whether a known function's could be static, as the thunk pass already makes a known function's adapter
  (`ir/thunks`). A task-list entry once this lands, with their sites from `allocations.py --sites`.

## 8. Done When

A closure is one object on every native backend and in both compilers, the suites pass, and §1.1's counts show the
environments gone (a heap closure for each heap environment of before), with the times recorded; or the idea is
dropped with its measurement.
