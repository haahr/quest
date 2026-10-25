# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Auto types may not mention type parameters inside mutable data

**Problem.** Generic code lays out values of types that mention its type parameters generically, and a value used
at a particular type argument is converted between layouts by copying (`quest_convert`, `docs/c-representation.md`
§6.4.5). A copy of mutable data would not share its updates, so the type checker rejects a type parameter inside
mutable data (arrays, var components and fields, var and out parameters) in an auto value's witness, in the types
of inspect's when clauses, and in the type arguments of `dynamic.new` and `dynamic.be`
(`docs/type-system.md` §6.11). Where it cannot see the type, as when one reaches `dynamic.new` as an ordinary type
argument, compiled code stops with a run-time error. The interpreter has no layouts and runs such programs.

**Reproduce.** `tests/errors/typecheck/auto/{witness,inspect,dynamic}_type_parameter_in_mutable_data.quest` are
rejected, and `tests/errors/run/layout_conversion_mutable_data.quest` runs interpreted but fails compiled
with `a value used at type Array(Tuple v: Record age: Int fuel: String end end) was laid out by generic code, and
converting it would copy mutable data`.

**Where to start.** `_check_closed_type` in `bootstrap/python/quest/typechecker/auto_values.py` makes the static
check; `quest_convert` and `quest_layout_conversion_error` in `runtime/quest_runtime.c` the run-time one. Lifting
the restriction needs conversion without copying: converting array elements and var slots lazily, through a view
that reads and writes the original's layout, or a uniform layout for type-parameter positions inside mutable data
(compare "Conversions that copy change object identity in C" above). With the IR (`docs/ir.md`), either is a
change to the represent pass.

**Done when.** The four tests above run (the error tests becoming golden tests) with the same results interpreted
and compiled.

---

## Auto types with var components may not have witnesses that mention type parameters

**Problem.** The type component of an auto value whose auto type has var components may be a type parameter of an
enclosing function, but not a larger type that mentions one: the binders of an inspect share the var components,
so converting them from the generic layout would lose updates. The type checker rejects such witnesses, open
compound types in when clauses for such auto types, and such type arguments of the dynamic operations.

**Reproduce.** `tests/errors/typecheck/auto/witness_type_parameter_with_var_components.quest`:

```quest
Let Cell = Auto A::TYPE with var a:A end;
let cell(A::TYPE x:A):Cell = auto :Tuple y: A end with tuple x end end;
```

**Where to start.** The `auto_type` check in `_check_closed_type` in
`bootstrap/python/quest/typechecker/auto_values.py`, and `inspect` in
`bootstrap/python/quest/codegen/c/printer.py`. Shares a solution with the task above: var components converted
without copying.

**Done when.** The test above becomes a golden test where an inspect updates a var component and the update is
seen through the auto value, in all backends.

---

## Options whose cases are listed in different orders

**Problem.** Option types are compared by their cases' names, unordered, so `Option a b end` and `Option b a end` are
equal types, but C lays them out (and numbers their tags) by the order written, and converts nothing between them: C
generation declares a variable of the second without its struct, which clang rejects. Relatedly, `ordinal` of an
option upcast to a supertype that lists its cases in another order gives the case's index in the original type
interpreted and in the supertype compiled (C did the same when it copied such options; with proxies it maps the tag).
Found while making views of options proxies (A2 of `docs/reorganization.md`).

**Reproduce.**

```quest
Let O1 = Option a b end;
Let O2 = Option b a end;
let o: O1 = option b of O1 end;
let p: O2 = o;
ordinal(p)
```

prints `1 : Int` interpreted and fails to compile with `--stop-after run_c_compiled` (`unknown type name
'QOption_b_a'`). With `Let O2 = Option b c a end` it compiles, and prints `0 : Int`.

**Where to start.** Decide what `ordinal` means at a type whose case order differs from the value's
([type-system.md](type-system.md) on options): the index at the static type seems the natural reading. Then either
make option types with different case orders unequal, or have shapes (`ir/shapes.py`, canonical forms in
`types/canonical.py`) order an option's cases canonically, with `ordinal` and option construction from an ordinal
mapping indices through the static type.

**Done when.** Both programs compile and print the same in both phases, and golden tests cover them.
