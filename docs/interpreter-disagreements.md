# The Interpreters Against Compiled Code: Three Disagreements

Found 2026-11-15 by the WasmGC plan's step 26 tests (`language/dynamic_runtime_ports`, `modules/echo_stored_views`),
when `tools/check` ran their interpreter phases. Both compilers' interpreters give one answer and compiled code
(arm64, C, ssac, the JIT, and the wasm backend, which ports the C runtime) gives another. Both tests now skip the
interpreter phases (`@skip-phase: interpret, run_ir_*`), with a comment pointing here, until these are settled.

None of the three is new. The release (3a45d707, 2026-11-13) and the bootstrap from before
[shared-faults-plan.md](shared-faults-plan.md)'s second batch give the interpreters' answers too. The step 26 tests
were first recorded through the bootstrap's `--update-golden`, whose summary did not show the interpreter phases
failing; `tools/check` was the first full run.

**Resolved 2026-11-15** on main, each in the direction given under "Resolution" below: the interpreters changed for 1,
compiled code for 2 and 3. The programs here, and the tests each resolution names, now give one answer everywhere.
The wasm branch still needs the runtime half of 2 and 3 (its `isSubtype` and its printer), after which its two
step 26 tests can drop their interpreter skips.

| | Compiled code | Interpreters (both) | Now |
|---|---|---|---|
| 1. An option key whose `var` component changed, in an identity map | `kept` | `lost` | `kept` |
| 2. `dynamic.be` at a function type whose quantifier's bound differs | `dynamic.error` | `accepted` | `accepted` |
| 3. Echo of a nested auto value's reference to the outer parameter | `a2=<hidden>` | `a2=6` | `a2=6` |

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

**Resolution:** the interpreters' `quest_identity_hash` takes its type argument, resolved (`builtins.callExternal`,
`call_external`: an external call passes its type arguments, as compiled code passes descriptors), and hashes options
and variants by the rule `is` uses at that type (`reduce.optionIdentity`, `variantCases`). An option or variant not
compared by content hashes by its object. Test: `language/option_identity` §10, which also covers a variant holding
such an option.

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

**The rule** the WASM session took was C's `quest_is_subtype`, which required equal bounds; the wasm runtime's
`isSubtype` follows it since step 26. But that rule was C's alone (docs/c-representation.md). The language's rule,
Cardelli's [TIncl Π], takes bounds contravariantly, and both type checkers do: `let g: All(A <: Big x: A) A = idS`
compiles. The interpreters' run-time subtyping is the checkers' own, so they agreed with static typing and compiled
code did not.

Nor was it only bounds: C compared the parameter and result types with a type parameter opaque, never a subtype of its
bound. So `dynamic.be(:All(A <: Small x: A) Int dynamic.new(:All(A <: Small x: Small) Int f))` was refused by compiled
code, with equal bounds, and accepted by the interpreters and by static typing.

**Resolution** (the user's choice: the static rule): `quest_is_subtype` compares bounds contravariantly and the bodies
under the quantifiers, as one binder per quantifier with the supertype's bound, where a type parameter is a subtype of
its bound. Each side has its own scope of binders, since a bound is described under fewer binders than the type it is
compared with; the trail records the scopes with each pair. Auto types' components are compared under one binder with
the subtype's bound, as the checkers do. Like the checkers, a proof may compare only so many polymorphic function
types (fuel), since full F<: is undecidable. Test: `language/dynamic_quantifier_bounds`, with cases refused as well as
accepted. The wasm runtime's `isSubtype` needs the same.

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

**The interpreters** write the value itself, `6`, having the value in hand.

**Resolution:** compiled code follows the interpreters, whose answer is more useful (and `quest_put_value` says it
writes values as the interpreter does). Its `witness` is now a stack of the type components of the auto values being
written, innermost first, and `quest_type_bound_vars[i]` is written at the `i`'th; `<hidden>` remains for a variable
with no witness. `dynamic.extern` already wrote a component at the `N`th enclosing witness (dynamic.md §2.4). Test:
`language/nested_auto_echo`, three levels deep and inside an array and a tuple. The wasm runtime's printer needs the
same.

## Reproducing

The three programs are above. Run each compiled (`quest -o p FILE && ./p`), by the self-hosted interpreter
(`quest --no-jit FILE`), and by the bootstrap (`questboot FILE`), with `--echo` for the third. On 2026-11-15 the
results were as the table gives, on this branch's tree, on the release, and on the bootstrap from before the second
batch.
