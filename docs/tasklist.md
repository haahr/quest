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

**Decided.** A tuple type prints its definitions as a tuple value's type does, `Let K::TYPE = Int`, not as `Def`.

**Done when.** The program above prints `Let T::TYPE = Tuple Let K::TYPE = Int k: K end` and `let tk:Int = 2`, and a golden test covers both.

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

**Decided.** Adopt the full contravariant rule, kept terminating by the `fuel` already passed: a search that runs
out of fuel fails as not a subtype. Compiled code needs the adaptation where the bounds' views differ.

**Done when.** A function whose type parameters have weaker bounds is a subtype as [TIncl Π] says, in both backends,
the check still terminates on the existing tests and on a known diverging example, and `type-system.md` §3 and §6.9
describe the rule.

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

**Decided.** A named exception is made where its scope begins, as the IR's `declare` already places it, so every
exception a scope names exists throughout it; the program above prints `2` in every backend. Making an exception has
no other effect, so nothing else observes the change.

**Done when.** The program above prints `2` in every backend, a golden test covers it, and the language's
description of exceptions says where a named exception is made.

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

**Decided.** `quest_instantiate_descriptor` names each instance, from the template's name with its holes replaced
by the arguments' names, memoized with the instance; the printer is unchanged.

**Done when.** Compiled code prints the program above as the interpreter does, and a golden test covers it.


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


---

## A proxy can be left in a slot whose type is never a proxy

**Problem.** A tuple type none of whose components can change view (`Tuple s: String end`, a tuple of scalars) is
never a proxy (`may_be_proxied`), so C reads its components directly. But an upcast of a *container* whose component
goes from a type that may be a proxy to such a type converts nothing in memory, and leaves the proxy in the slot: the
represent pass treats the component's `unproxy` plan as a cast in an option (`_option_cases_agree`), and the
runtime's `quest_convert` returns a tuple or option unchanged when `quest_layout_equivalent` says the layouts agree
(a static `view` plan of a tuple whose target cannot be proxied goes there). Reading a component through the tagged
pointer then reads the proxy's memory: a wrong `Int`, or a crash for a pointer. Identity breaks too (`is` of two
values of the never-proxied type compares a proxy with its original). Echo, `is` across types, generic code (whose
`Tuple s: A end` may be proxied), record fields (read through stored types), and function results (adapted) are
right.

**Reproduce.**

```quest
import writer: Writer;
import conv: Conv;
let print(s: String): Ok = writer.putString(writer.output s <> "\n");
Let Big = Record a: Int b: Int end;
Let Small = Record a: Int end;
Let TS = Tuple n: Int x: Small end;
Let T0 = Tuple n: Int end;
let tb: Tuple n: Int x: Big end = tuple let n = 7 let x = record a = 1 b = 2 end end;
let ts: TS = tb;  (* a proxy of tb *)
let o: Option some with p: TS end end = option some of Option some with p: TS end end with let p = ts end;
let o0: Option some with p: T0 end end = o;  (* a cast: o0!some.p is the proxy, typed T0 *)
let p0: T0 = o0!some.p;
let q: T0 = tb;
print(conv.int(p0.n) <> " " <> conv.bool(p0 is q));
Let Rec L(A::TYPE) = Option nil cons with head: A tail: L(A) end end;
let l: L(TS) = option cons of L(TS) with let head = ts let tail = option nil of L(TS) end end;
let l0: L(T0) = l;
print(conv.int(l0!cons.head.n));
let w: Tuple q: TS end = tuple let q = ts end;
let w0: Tuple q: T0 end = w;  (* quest_convert returns w: the layouts agree *)
print(conv.int(w0.q.n))
```

prints `7 true`, `7`, `7` interpreted; compiled, each read prints a number like `~3458764513803562161` (the
proxy's memory) and `p0 is q` prints `false`. With a `String` component instead of `n: Int`, the reads crash (signal 11), as do
storing `p0` into an array or a tuple's `var` component and reading it back, and `dynamic.be(:T0 dynamic.new(:T0
p0))`. A variant payload converted the same way (`Variant k: TS end` to `Variant k: T0 end`) crashes too.

**Fix options.**

- *(a) Make the container a proxy.* Count a component going from may-be-proxied to never-proxied as a view change,
  statically (`_option_cases_agree`, as tuples already do) and at run time (a variant of `quest_layout_equivalent`
  for `quest_convert`'s shortcut), so the container is proxied and its reads convert the component (the runtime
  unwraps a proxy viewed at a type that cannot be one). Keeps identity, costs nothing on reads, but only works when
  the target container may be a proxy: lists and options of two or more cases, tuples with a view-sensitive
  component. Not `Option some with p: T0 end end` or `Tuple q: T0 end`.
- *(b) Widen `may_be_proxied` to every type that can be reached this way.* Every nonempty tuple is a prefix supertype
  of a tuple with a record component, so every nonempty tuple (and option with a tuple payload) would be read
  through `quest_unproxy` (a test and a branch per read; A2 measured proxy checks at 9 to 13% on hot reads of
  view-sensitive tuples, and this would reach tuples of scalars, which the tokenizer benchmark uses heavily). Expensive.
- *(b') Widen it narrowly, combined with (a).* A tuple or option also may be proxied when one of its components is a
  nonempty tuple or an option with a payload (the components that can be reached by such an upcast); then (a) applies
  to every container, identity is kept, and only reads of components of containers of aggregates pay (an `ORIGINAL`
  access, `quest_unproxy`, for components that cannot change view). Tuples of scalars and strings stay direct.
  Needs the same change in `quest_may_be_proxied` and the runtime shortcut, and an `ABI_VERSION` bump only if
  compiled units disagreeing about the predicate can meet (they can: a proxy made by one unit read directly by an
  older one), so probably yes. My recommendation.
- *(c) Copy the container, unwrapping the component.* Only in this case; loses the container's identity (`is`
  differs from the interpreter for those values), and must be rejected when the copy would hold `var` components
  (`quest_copy_viewed` already fails at run time for them).
- *(d) Reject statically.* Upcasts whose nested component goes from may-be-proxied to never-proxied, inside a
  container that cannot be proxied. Simple, but rejects programs the interpreter runs, and does not cover the
  run-time path through generic code by itself.

**Where to start.** `_option_cases_agree` and `_plan`'s tuple case in `bootstrap/python/quest/ir/represent.py`,
`may_be_proxied` and `_view_sensitive` in `codegen/layout.py`, and `quest_convert`, `quest_may_be_proxied_rec`, and
`quest_layout_equivalent` in `runtime/quest_runtime.c`.

**Done when.** The program above prints the same in both phases, as do its `String` variants, and a golden test
covers option, list, tuple, and variant containers.
