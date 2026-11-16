# The Interpreters Against Compiled Code: Three Disagreements

Found 2026-11-15 by the WasmGC plan's step 26 tests (`language/dynamic_runtime_ports`, `modules/echo_stored_views`),
when `tools/check` ran their interpreter phases. Both compilers' interpreters give one answer and compiled code
(arm64, C, ssac, the JIT, and the wasm backend, which ports the C runtime) gives another. Both tests now skip the
interpreter phases (`@skip-phase: interpret, run_ir_*`), with a comment pointing here, until these are settled.

None of the three is new. The release (3a45d707, 2026-11-13) and the bootstrap from before
[shared-faults-plan.md](shared-faults-plan.md)'s second batch give the interpreters' answers too. The step 26 tests
were first recorded through the bootstrap's `--update-golden`, whose summary did not show the interpreter phases
failing; `tools/check` was the first full run.

In each case compiled code follows the rule the language documents, so the interpreters are the ones to change. Each
needs both interpreters changed (two-compilers policy): the bootstrap's (`bootstrap/python/quest/interpreter`,
`values`) and the self-hosted one (`questlang/interpreter`).

| | Compiled code | Interpreters (both) |
|---|---|---|
| 1. An option key whose `var` component changed, in an identity map | `kept` | `lost` |
| 2. `dynamic.be` at a function type whose quantifier's bound differs | `dynamic.error` | `accepted` |
| 3. Echo of a nested auto value's reference to the outer parameter | `a2=<hidden>` | `a2=6` |

## 1. An option's identity hash with a `var` component

```
import writer: Writer;
import hashMap: HashMap = collections/hashmap : collections/HashMap;
Def MV = Option none some with var v: Int end end;
let m: MV = option some of MV with let var v = 1 end;
let map = hashMap.newIdentityMap(:MV :Int);
hashMap.insert(:MV :Int map m 5);
case m when some with c then c.v := 2 when none then ok end;
writer.putString(writer.output if hashMap.contains(:MV :Int map m) then "kept\n" else "lost\n" end)
```

**The rule** (docs/extensions.md, Options as Values; `quest_option_is` and `quest_option_identity_hash`): `is`
compares an option by its component only in a single-word option type's case, the one case with one component
that is not `var`. Any other option, this one included, compares and hashes by identity. So `m is m` holds after
the store, and the hash must not change either.

**The interpreters** hash an option whose payload is a one-element tuple by that element, whether it is `var` or
not. The store changes the hash, and the map no longer finds its key, though `m is m` still holds.
- `questlang/interpreter/builtins.mod.quest`, `identityHash`: the `vOption` arm's `extent t.t.elements is 1`
  branch.
- `bootstrap/python/quest/interpreter/builtins.py`, `_quest_identity_hash`: the same branch
  (`payload.elements[0]`).

**Fix:** hash by the single-word rule, which needs the option's type (whether the component is `var`, and whether
the other cases have components), as compiled code's identity hash takes it (`quest_identity_hash(t, x)`). The
interpreters' `is` on options should be checked against the same rule.

## 2. A quantifier's bound in run-time subtyping

```
import writer: Writer;
import dynamic: Dynamic;
Def Small = Record y: Int end;
Def Big = Record name: String y: Int end;
let idS(A <: Small x: A): A = x;
writer.putString(writer.output try
    begin
        let g = dynamic.be(:All(A <: Big x: A) A dynamic.new(:All(A <: Small x: A) A idS))
        "accepted\n"
    end
    when dynamic.error then "dynamic.error\n"
    end)
```

**The rule** (C's `quest_is_subtype` for function types; the wasm runtime's `isSubtype` since step 26): two
function types' quantifiers must have equal bounds.

**The interpreters** accept a bound taken contravariantly (`Small` where `Big` is asked), as the wasm runtime did
before step 26 (wasm-review.md §2.4, 6). The interpreters' run-time subtyping, which `dynamic.be` calls, should
compare bounds both ways.

## 3. Echo of an outer parameter inside a nested auto value

```
Let Nest = Auto A::TYPE with a: A inner: Auto B::TYPE with b: B a2: A end end;
let n: Nest = auto :Int with 5 auto :String with "s" 6 end end;
n
```

run with `--echo`.

**The rule** (`quest_put_value`): a component of a bound variable's type is written at the witness only for the
innermost auto value's own parameter (bound variable index 0). A reference to an enclosing auto type's parameter
(index 1, `a2` here) is written `<hidden>`, as the wasm runtime does since step 26 (wasm-review.md §2.4, 5).

**The interpreters** write the value itself, `6`, having the value in hand. Whether echo should show it is a
choice: showing it is more useful, and compiled code could follow by keeping a stack of witnesses, as the wasm
runtime's printer does. The two should agree either way; `quest_put_value` is the one to change if the interpreters'
answer is preferred.

## Reproducing

The three programs are above. Run each compiled (`quest -o p FILE && ./p`), by the self-hosted interpreter
(`quest --no-jit FILE`), and by the bootstrap (`questboot FILE`), with `--echo` for the third. On 2026-11-15 the
results were as the table gives, on this branch's tree, on the release, and on the bootstrap from before the second
batch.
