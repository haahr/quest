# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Let bindings shadow imported module names in compiled code

**Problem.** In compiled code, a name bound to a module (by an import, or a prelinked library module such as `list`
used without one) keeps referring to the module record after a `let` shadows it, whether the `let` is at top level or
inside a function. The C emitter maps the module name to its record (`qm_<name>`) in `current_env_vars`, and a
`TypedVar` lookup consults that map before anything else, so the shadowing binding's uses compile to the module
record. The interpreter gets this right.

**Reproduce.** With `shadow.quest` containing

```quest
import writer: Writer;
let f(): Int = begin let writer = 3; writer + 1 end;
f();
let writer = 7;
writer + 1
```

`python3.11 bootstrap/python/quest_driver.py --stop-after run_c_compiled shadow.quest` fails in the C compiler with
`invalid operands to binary expression ('QRecordVal' ... and 'long long')` at both additions, while
`--stop-after interpret` prints `8 : Int`.

**Where to start.** The `TypedVar` case of expression emission in `bootstrap/python/quest/codegen/c_emitter.py`
returns `self.current_env_vars[name]` first; the import handling in `emit_program` fills that map with module records.
Resolving by symbol (each `TypedVar` carries its `ValueSymbol`) rather than by name would distinguish the module from
a binding that shadows it.

**Done when.** The program above prints `8 : Int` in `run_c_compiled`, as in `interpret`, and a golden
test covers shadowing an imported module and a prelinked one (`list`), at top level and in a function.

---

## Value declarations joined by `and` without `rec`

**Problem.** Cardelli's grammar allows `let ValueDecl and ValueDecl`, and `let x = 1 and y = 2;` parses (into an
`ast.LetValueBindingGroup`), but the typechecker rejects it: "Simultaneous value declarations with 'and' ('x', 'y')
are not supported yet". Only `let rec ... and ...` works. Type declarations joined by `and` without `Rec` are
simultaneous (`docs/type-system.md` §3.4), and values should match: each member's value is elaborated and evaluated
in the enclosing scope, so a member does not see the others (in `let x = 1; let x = 2 and y = x;`, `y` is 1), and all
names are bound once every value has been computed.

**Reproduce.** `tests/errors/typecheck/value_group_without_rec.quest` pins the rejection.

**Where to start.** `_elaborate_value_group` in `bootstrap/python/quest/typechecker.py` raises the error
(`_simultaneous_values_message`). The typechecker can elaborate each member through the single-binding path in a
throwaway child scope and then declare all the symbols, as `elaborate_type_binding_group` does for types
(`elaborate_types.py`). The work is in the backends, which bind by name, so translating the members in sequence
would let `y` see the new `x`:
- the interpreter (`eval_binding` in `interpreter.py`) must evaluate every value before defining any name;
- the C emitter (`codegen/c_emitter.py`) must compute every value into a temporary before assigning the members'
  variables, in blocks (the `TypedBlock` case, next to `_emit_rec_bindings`), at top level (`_emit_phrase`, where
  names are file-scope globals), and in module initializers (`_emit_single_module_definition`);
- echo prints one `let` line per member, as for `TypedLetValueGroup`.

A typed group node is needed for this, either `TypedLetValueGroup` with an `is_rec` flag or a separate node; its
other consumers already flatten groups (`binding_members` in `typed_ast.py`). Groups in tuples
(`_reject_value_declarations_in_tuple`) can follow the type groups, which tuples allow without `Rec`.

**Done when.** A golden test covers simultaneous value declarations at top level, in a block, in a function, and in
a module, including a member that refers to an outer binding another member shadows, with the same output in
`interpret` and `run_c_compiled`; `value_group_without_rec.quest` is removed; and `docs/type-system.md` (§6.10 and
§3.4) and `docs/syntax.md` (`LetValueBindingGroup`) describe them.

---

## Recursive declarations inside tuples

**Problem.** A tuple or tuple type cannot contain recursive declarations: `Let Rec` (single or a group) in a tuple or
tuple type gets "Recursive type declarations are not supported in tuples", and `let rec` (single or a group) in a
tuple gets "Recursive value declarations are not supported in tuples". Non-recursive declarations, and type groups
without `Rec`, work there.

**Reproduce.** The error tests `rec_type_in_tuple.quest`, `type_binding_group_rec_in_tuple.quest`,
`type_binding_group_rec_in_tuple_type.quest`, `rec_value_in_tuple.quest`, and `value_group_in_tuple.quest` in
`tests/errors/typecheck/` pin the rejections.

**Where to start.** Types: `tuple_type_binding_members` in `bootstrap/python/quest/elaborate_types.py` rejects them,
for the tuple-type case of `elaborate_type` and for `_synth_tuple_expr` and `_check_tuple_expr` in `typechecker.py`.
A recursive type component is a `QTupleTypeBinding` whose type is a `QRecType` or `QRecGroupType`; check what path
types (`p.T`, `QPathType`) and tuple subtyping do with it. Values: `_process_tuple_bindings` in `grammar.py` passes
recursive bindings through, and `_reject_value_declarations_in_tuple` in `typechecker.py` rejects them. A recursive
function component must see its own name (and its group's) while its value is checked, although tuple components
are otherwise sequential, and in C its closure must capture the others after they exist, as `_emit_rec_bindings`
does for blocks.

**Done when.** Recursive types and functions work as tuple components in `interpret` and `run_c_compiled`, a golden
test covers them, and the error tests above are removed or converted.

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
