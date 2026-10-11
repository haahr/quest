# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Recursive and simultaneous declarations inside tuples

**Problem.** A tuple or tuple type cannot contain recursive declarations: `Let Rec` (single or a group) in a tuple or
tuple type gets "Recursive type declarations are not supported in tuples", and `let rec` (single or a group) in a
tuple gets "Recursive value declarations are not supported in tuples". Value declarations joined by `and` without
`rec`, which work elsewhere (`docs/type-system.md` §6.10), get "Value declarations joined by 'and' are not supported
in tuples yet". Non-recursive declarations, and type groups without `Rec`, work there.

**Reproduce.** The error tests `rec_type_in_tuple.quest`, `type_binding_group_rec_in_tuple.quest`,
`type_binding_group_rec_in_tuple_type.quest`, `rec_value_in_tuple.quest`, `value_group_in_tuple.quest`, and
`value_group_without_rec_in_tuple.quest` in `tests/errors/typecheck/` pin the rejections.

**Where to start.** Types: `tuple_type_binding_members` in `bootstrap/python/quest/elaborate_types.py` rejects them,
for the tuple-type case of `elaborate_type` and for `_synth_tuple_expr` and `_check_tuple_expr` in `typechecker.py`.
A recursive type component is a `QTupleTypeBinding` whose type is a `QRecType` or `QRecGroupType`; check what path
types (`p.T`, `QPathType`) and tuple subtyping do with it. Values: `_process_tuple_bindings` in `grammar.py` passes
recursive bindings through, and `_reject_value_declarations_in_tuple` in `typechecker.py` rejects them. A recursive
function component must see its own name (and its group's) while its value is checked, although tuple components
are otherwise sequential, and in C its closure must capture the others after they exist, as `_emit_rec_bindings`
does for blocks. A simultaneous group's members are components whose values must all be computed before any of
their names is bound for the later components, as `_emit_simultaneous_bindings` does for blocks.

**Done when.** Recursive types and functions, and simultaneous value declarations, work as tuple components in
`interpret` and `run_c_compiled`, a golden test covers them, and the error tests above are removed or converted.

---

## Recursive type operators

**Problem.** A recursive type cannot have type parameters: `Let Rec T(A::TYPE) = ...`, alone or in a group, gets
"Recursive type 'T' cannot have type parameters". Writing the parameter outside the recursion works when the
recursion is uniform (`Let List = Fun(A::TYPE) Rec(L::TYPE) Option nil cons with head: A tail: L end end`,
`tests/source/language/recursive_options.quest`), but `Let Rec List(A::TYPE) = Option nil cons with head: A
tail: List(A) end end` should mean the same.

**Reproduce.** `tests/errors/typecheck/rec_type_params.quest` and `type_binding_group_rec_params.quest`.

**Where to start.** `_reject_recursive_type_operator` in `bootstrap/python/quest/elaborate_types.py`, called from
`_elaborate_type_binding_symbol` and `elaborate_type_binding_group`. When every recursive occurrence applies the
operator to exactly its own parameters (uniform recursion), `Let Rec T(A) = body` can be elaborated as
`Fun(A) Rec(T') body[T(A) := T']`, and a group likewise, with one `QRecGroupType` under the shared parameters
(members must then take the same parameters). Non-uniform recursion (`Nest(A) = ... Nest(Array(A)) ...`) denotes
non-regular types, which equi-recursive equality and C canonical forms (`codegen/c_types.py`) cannot handle as
they stand; reject it with its own clear error.

**Done when.** Uniform recursive type operators, single and in groups, work in `interpret` and `run_c_compiled`, and
equal the `Fun(A) Rec(...)` form (same C representation); a golden test covers them; non-uniform recursion gets a
specific error test; and `docs/type-system.md` §3.4 no longer lists them as unsupported.

---

## Top-level rebindings change what earlier functions see

**Problem.** Rebinding a name at the top level changes the value that earlier top-level functions (and closures)
read through it, in both backends, so the function sees the later binding instead of the one in scope where it was
defined. Inside blocks, both backends keep the earlier binding.

**Reproduce.** With `rebind.quest` containing

```quest
let x = 1;
let f(): Int = x;
let x = 2;
{f() * 10} + x
```

both `--stop-after interpret` and `--stop-after run_c_compiled` print `22 : Int`; lexical scoping gives `12`.

**Where to start.** The interpreter evaluates top-level phrases in one `RuntimeEnvironment` frame (`pipeline.py`
and `eval_binding` in `interpreter.py`), and `define` overwrites a name in place; the `TypedBlock` case of
`eval_expr` instead binds a rebound name in a new frame. In C, top-level values are file-scope globals named by
the binding's name (`c_analysis.py` collects them; `_emit_phrase` in `codegen/c_emitter.py` assigns them), so a
rebinding assigns the same global, which top-level functions read; distinct globals per top-level binding, chosen
by symbol (as top-level functions now are), would fix it. The echo of a rebound name and module initializers need
the same care.

**Done when.** The program above prints `12 : Int` in both phases, and a golden test covers rebinding a value and a
function at the top level after functions and closures that refer to them.
