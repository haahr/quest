# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Compiled echo expands aliases in type components within recursive types

**Problem.** Compiled echo writes a tuple's type components (`Let X = P`) with their alias names, as the interpreter
does, except within a recursive type, where it writes the type with its aliases expanded and recursive types in their
canonical form. Echo output then differs between the backends.

**Reproduce.** With `rec_echo.quest` containing

```quest
Let P = Tuple a: Int end;
Let Rec R = Option nil cons with Def X = P h: Int t: R end end;
let rr = option cons of R with Let X = P let h = 1 let t: R = option nil of R end end;
```

`--echo --stop-after interpret` prints `... tuple Let X = P h=1 ...`, while `--echo --stop-after run_c_compiled`
prints `... tuple Let X = Tuple a: Int end h=1 ...`.

**Where to start.** Echo writes type components from its own descriptors (`echo_descriptor_form` in
`codegen/c/types.py`), made from the type as written, but stops at a recursive type (`echo_children`) and uses its
shared descriptor, whose component text comes from the canonical type. The interpreter unfolds recursive types as it
goes (`_exposed_type` in `interpreter/treewalk.py`). Echo-only descriptors would have to unfold them too, referring
back to a descriptor already being made where the unfolding repeats, as shared descriptors of recursive types do.

**Done when.** `language/tuple_type_component_echo` (or a test beside it) echoes a value of a recursive type with
an aliased type component, and `interpret` and `run_c_compiled` agree.

---

## Type definitions in tuple types print oddly, and their names escape

**Problem.** A type definition written in a tuple type (`Def K = Int`, in a tuple type or an option case's payload)
prints as `Let K= Int`, with no space before `=` and no kind, while the same component of a tuple value's type prints
as `Let K::TYPE = Int`. And selecting a field whose type is the defined name gives the name as its type, outside the
tuple where it means nothing: `tt.k` below has type `K`, not `Int` (though `tt.k + 1` typechecks).

**Reproduce.** With `def_in_tuple.quest` containing

```quest
Let T = Tuple Def K = Int k: K end;
let tt: T = tuple Let K = Int let k: K = 2 end;
let tk = tt.k;
```

`--echo --stop-after interpret` prints `Let T::TYPE = Tuple Let K= Int k: K end` and `let tk:K = 2`.

**Where to start.** `QTupleTypeBinding.__str__` (`bootstrap/python/quest/types/model.py`) leaves out the space when
the binding has no bound; elaborating a `Def` in a tuple type (`elaborate_tuple_type_bindings` in
`typechecker/elaborate_types.py`) gives none. A tuple value's type has its definitions already substituted into
its fields' types (`x: Int`), which is why selecting from one is fine; selecting a field of a tuple type written with
`Def` (`_synth_select_expr` in `typechecker/aggregates.py`) should substitute them too. Fixing the printing changes
goldens that show such types (`language/option_payload_components`).

**Done when.** The program above prints `Let T::TYPE = Tuple Let K::TYPE = Int k: K end` (or as `Def`, if that is
how a tuple type should print its definitions) and `let tk:Int = 2`, and a golden test covers both.

---

## Subtyping between `All` types requires equal bounds

**Problem.** `All(X <: K) B <: All(X <: K') B'` holds only when `K` and `K'` are equal (and `B <: B'`), as in Cardelli
and Wegner's Kernel Fun. Cardelli's Quest is contravariant in the bound: its rule [TIncl Π] (*A Semantic Basis for
Quest* §2, validated by Theorem 3.4.1) needs only `K' <:: K` and `B <: B'` under `X::K'`, so a polymorphic function
whose type parameter has a weaker bound can be used where a stronger one is expected. Function literals checked
against an annotation already follow that rule (`type-system.md` §6.9); values of `All` types in general do not.

**Reproduce.** With `Let P = Record a: Int end; Let Q = Record a: Int b: Int end;`,
`let f(X <: P x: X): Int = x.a; let g: All(X <: Q x: X) Int = f;` is rejected, while the same function written as a
literal against the annotation is accepted.

**Where to start.** The `QAllType` case of `_prove_subtype` in `bootstrap/python/quest/types/subtyping.py`, which
compares bounds with `is_kind_equal`. The contravariant rule makes subtyping undecidable in F<: (Pierce, *Bounded
quantification is undecidable*, 1992), because comparing bodies under the supertype's bound can rename variables
without end; a bound on the search (the `fuel` already passed), or a restriction such as requiring the bounds not to
mention the quantified variables, would keep the check terminating. In C, a value of a bounded type parameter is held
viewed at its bound (`docs/c-representation.md` §5.1), so a function used at a stronger bound needs its arguments
converted to the weaker bound's view (a closure adaptation thunk) unless the views agree.

**Done when.** A function whose type parameters have weaker bounds is a subtype as [TIncl Π] says, in both backends,
the check still terminates on the existing tests and on a known diverging example, and `type-system.md` §3 and §6.9
describe the rule.

---

## Conversions that copy change object identity in C

**Problem.** `is` compares tuples, records, and arrays by identity. When a value passed to or returned from a
polymorphic function is laid out differently from the callee's generic layout, and the layouts do not agree in
memory (a type parameter standing for a record or a variant), C copies the tuple or option
(`docs/c-representation.md` §5.1, Polymorphic Calls), and the copy is a different object. The interpreter has no
layouts, so the two backends disagree. This is documented as a limitation for now (`docs/ir.md` §8.3).

**Reproduce.**

```quest
Let P = Record a: Int end;
let id(A::TYPE t: Tuple x: A end): Tuple x: A end = t;
let f: All(A::TYPE t: Tuple x: A end) Tuple x: A end = id;
let t: Tuple x: P end = tuple let x = record a = 1 end end;
f(:P t) is t
```

prints `true` interpreted and `false` compiled. At `Bool` the conversion is a cast and both print `true`.

**Where to start.** The choice is between rejecting such conversions of aggregates statically (as conversions that
would copy mutable data are rejected), which rejects more programs where calls are not specialized (first-class
polymorphic values, functions of other units), and representing type-parameter positions uniformly (records and
variants boxed inside tuples and options), which removes the copies and revisits the dual C representation
(`docs/c-representation.md` §1). With the IR (`docs/ir.md`), either is a change to the represent pass's plans.

**Done when.** Compiled code and the interpreter agree on `is` for converted values, or the language documents where
they may differ, and the conversion matrix's identity column checks the rule.

---

## An exception made on a branch that does not run can be named later

**Problem.** A named exception made inside an expression (`exception I end`) binds its name for the rest of the
enclosing scope, whether or not the expression that makes it runs. The type checker accepts a later use of the name
after a branch that did not make it: the interpreter fails with an undefined runtime symbol, and compiled C reads an
exception that was never made (a null pointer), so `raise I` there matches whichever handler compares equal to it.
The IR declares such an exception before the binding that makes it (`declare`, `docs/ir.md` §5), and reading it before
its let has run is undefined.

**Reproduce.**

```quest
let f(c: Bool): Int = begin
  let e: Exception = if c then exception I end else exception J end end;
  try raise I end when I then 1 when J then 2 end
end;
f(false)
```

fails interpreted (`Undefined runtime symbol 'I'`) and prints `1` compiled.

**Where to start.** `_synth_exception_expr` in `bootstrap/python/quest/typechecker/exceptions.py`, which declares the
exception's name in the enclosing scope. Either the name should be visible only when the exception is made on every
path to the use (a definite-assignment check), or only within the expression that makes it, or a named exception
should be made where its scope begins rather than where it is written.

**Done when.** The type checker rejects the program above (or the language defines its meaning and both backends
agree), and an error test covers it.

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

## Only `Dynamic.T` among auto types can be externed

**Problem.** The serialization format writes `Dynamic.T` by its built-in name, but no other auto type is encodable
(`docs/dynamic.md` §2.2), so `dynamic.extern` raises `dynamic.error` on a value whose type contains any other auto
type, such as a dynamic holding a value of `Auto A::TYPE with a:A b:A end`.

**Reproduce.**

```quest
import dynamic: Dynamic;
import writer: Writer;
Let Pair = Auto A::TYPE with a:A b:A end;
dynamic.extern(writer.output dynamic.new(:Pair auto :Int with 1 2 end))
```

raises `dynamic.error` in every backend.

**Where to start.** A type node for auto types in `docs/dynamic.md` §2.2 (the kind bound, and the components'
names, var-ness, and types with the bound type variable), each value written with its witness type; then the
encoders and decoders in `bootstrap/python/quest/values/dynamic_json.py` and `runtime/quest_serialization.c`
(`QTYPE_KIND_AUTO` in the encodability check, writer, and reader), which already write and read `Dynamic.T`'s
witness. Bump the format version if the change is not backward compatible.

**Done when.** Values of auto types round-trip through `extern` and `intern` in all backends, including autos whose
witnesses were built in generic code, and `tests/source/stdlib/dynamic_extern.quest` (or a new golden test) covers
them.

---

## Auto values built in generic code print `?0` for their witness in C

**Problem.** A type descriptor that generic code builds from a template at run time
(`quest_instantiate_descriptor`, `docs/c-representation.md` §6.4.5) keeps the template's name, in which each type
parameter is a hole named `?0`, `?1`, …. Printing an auto value prints its witness by that name.

**Reproduce.**

```quest
import dynamic: Dynamic;
let f(A::TYPE x: A): Dynamic = dynamic.new(:Tuple v: A w: Int end tuple x 1 end);
let g: All(A::TYPE x: A) Dynamic = f;
g(:String "hi")
```

with `--print-result` prints `auto :Tuple v: String w: Int end with …` interpreted but
`auto :Tuple v: ?0 w: Int end with …` with `--stop-after run_c_compiled`. Serialization is
structural and not affected.

**Where to start.** `quest_instantiate_descriptor` in `runtime/quest_runtime.c` could build the instance's name
from the template's with the holes replaced by the arguments' names (memoized with the instance), or the printer
(the `QTYPE_KIND_AUTO` case near `printf("auto :%s with"`) could print descriptors structurally. `hole_var` in
`bootstrap/python/quest/codegen/descriptors.py` names the holes.

**Done when.** Compiled code prints the program above as the interpreter does, and a golden test covers it.


---

## Upcasting a tuple whose components change view copies it in C

**Problem.** Upcasting a tuple or option whose immutable components change representation (a record viewed at a
supertype, a variant whose supertype numbers its cases differently) copies the aggregate in C, even without
polymorphism. The copy does not see later updates of the original's `var` components, and is not `is` the original.
The interpreter shares the value. This is a miscompilation; the plan is to fix it with the representation change of
`docs/reorganization.md` (0a, step A2) rather than before.

**Reproduce.**

```quest
Let Big = Record a: Int b: Int end;
Let Small = Record a: Int end;
let t: Tuple x: Big var n: Int end = tuple let x = record a = 1 b = 2 end let var n = 0 end;
let s: Tuple x: Small var n: Int end = t;
t.n := 1;
s.n
```

prints `1 : Int` interpreted and `0 : Int` with `--stop-after run_c_compiled`. A variant component
(`Variant p: Int q: Bool end` upcast to `Variant q: Bool r: Ok p: Int end`) behaves the same. Record fields of
records do not: records' offset tables carry stored types, and reads convert.

**Where to start.** `docs/reorganization.md` §2, 0a.

**Done when.** The program above prints `1 : Int` in both phases, for record and variant components, and a golden
test covers both.

---

## `is` between tuples of different types does not compile in C

**Problem.** `s is t`, with `s` and `t` tuples of different (subtype-related) types, prints a C comparison of
distinct pointer types, which clang rejects with `-pedantic-errors`.

**Reproduce.**

```quest
Let Big = Record a: Int b: Int end;
Let Small = Record a: Int end;
let t: Tuple x: Big end = tuple let x = record a = 1 b = 2 end end;
let s: Tuple x: Small end = t;
s is t
```

fails with `comparison of distinct pointer types` under `--stop-after run_c_compiled`.

**Where to start.** The `prim is` case of the C printer (`prim` in `bootstrap/python/quest/codegen/c/printer.py`):
compare the pointers as `void *`, or have represent convert both operands to one type.

**Done when.** The program compiles and prints what the interpreter prints (which after the copy is `false` in C
until the representation change), and a golden test covers `is` on tuples, options, and arrays of different types.
