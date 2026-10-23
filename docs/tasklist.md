# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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

---

## The driver ignores `--stop-after` for interface and module files

**Problem.** When an interface or module file is passed to the driver directly, it is compiled fully, writing
`.qi`, `.qm`, `.c` and `.o` files (next to the source unless `--build-dir` is given), whatever `--stop-after` says.

**Reproduce.** With `m.int.quest` containing `interface M export f(c: Bool): Ok end;` and `m.mod.quest` containing
`module m : M export let f(c: Bool): Ok = ok; end;`, `quest --stop-after typecheck m.mod.quest` writes `m.qi`,
`m.qm`, `m.mod.c` and `m.o` next to the source.

**Where to start.** `bootstrap/python/quest_driver.py` handles `.int.quest` and `.mod.quest` files in two places,
the default mode (around the `compile_interface_file` and `compile_module_file` calls) and `compile` mode, before
looking at `--stop-after`.

**Done when.** `--stop-after typecheck` on such a file stops after typechecking and writes no artifacts, and a test
in `tests/python/test_quest_driver.py` covers an interface file and a module file.

---

## Compiled echo omits a tuple value's type components

**Problem.** When compiled code echoes a tuple value whose type has manifest type components (`Let X = T` in a
tuple, `Def X = T` in a tuple type), it leaves them out, while the interpreter prints them. Echo output differs
between the backends for any such tuple, whether it is a top-level binding's value or nested in another value.

**Reproduce.** With `tuple_echo.quest` containing

```quest
let t = tuple Let A = Int let x: A = 1 end;
Let Rec L = Option nil cons with h: Int t: L end end;
let s = tuple Let M = L let l: M = option nil of L end end;
```

`--echo --stop-after interpret` prints `let t:Tuple Let A::TYPE = Int x: Int end = tuple Let A = Int x=1 end` (and
`s` with `Let M = L`), while `--echo --stop-after run_c_compiled` prints `... = tuple x=1 end`.

**Where to start.** The interpreter formats tuples in `_format_aggregate` (`bootstrap/python/quest/interpreter.py`),
writing `Let name = type` for each `QTupleTypeBinding` component. Compiled code prints non-existential values through
their type descriptors (`_print_value_call` in `codegen/c_emitter.py`, then `quest_put_tuple` and
`quest_put_elements` in `runtime/quest_runtime.c`), and a tuple's descriptor (`QTupleTypeDescriptor`) lists only its
value elements. Existential tuples are formatted statically instead (`_format_existential_tuple_val`). Recording
manifest components in tuple descriptors (their names and printed types, in order among the elements) covers nested
tuples too, but changes the descriptor layout, which the ABI version covers (`docs/build-process.md` §5.2); the type
must print as the interpreter prints it (`str` of the type, with alias names).

**Done when.** A golden test with `@echo` (or echoed phrases) shows the same output in `interpret` and
`run_c_compiled` for tuples with manifest type components, at the top level and nested in another tuple, record,
or array.

---

## C coercions treat variants that differ only in type arguments as needing tag maps

**Problem.** `_coerce_val` in `codegen/c_emitter.py` emits a variant upcast, which remaps tags through a tag map
table, whenever the source and target variant types are not equal. Variants whose types differ only in a type
parameter versus its argument (`Tree(Bool)` passed as `Tree(A)` to a polymorphic function) or in which symbol names
the same type parameter (as a function's parameters and its type did, before quantifiers were renamed by position
when functions are checked against their expected types) are not related by subtyping and need no remapping, but no table is
emitted for such pairs, so the C fails to compile with an undeclared `tagmap_...`. The variant branch does not
reduce types reached through type operators, which hides this today: the two types are type operator applications
(`Tree(A)`), not `QVariantType`s, so the branch is skipped. Reducing them, as the tuple and function branches now do,
exposes it.

**Reproduce.** In `_coerce_val`, test the variant branch with `normalize_type` of both types (as the tuple branch
does) and compile `tests/source/language/type_parameters_in_aggregates.quest`: clang reports undeclared identifiers
`tagmap_RecGroup0_0_QVariant_...` for conversions between `Tree(Bool)` and `Tree(A)`, and between two `Tree(A)`s whose
`A`s are the type parameters of a generic caller and of the generic function it calls.

**Where to start.** The variant branch of `_coerce_val` and `_emit_variant_upcast`. A remap is needed only when the
two variant types have different cases (names or order), which can be decided from their cases rather than from type
equality; payloads are always one `QVal` word, so differing payload types need no conversion of the variant itself.

**Done when.** The variant branch reduces types reached through type operators like the tuple branch, emits tag maps
only when the cases differ, and the golden tests pass in `run_c_compiled`.

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

## C specializes only calls of top-level and module functions

**Problem.** C compiles a specialized clone of a polymorphic function called with a record or variant type argument,
so that the record or variant is passed unboxed (`docs/c-representation.md` §6.4.3). Only calls of top-level and
module functions are specialized: a call of a local polymorphic function, of a parameter, or of a tuple component is
compiled as a call of the generic closure, which boxes records and variants and converts tuples and options over
them between layouts (`quest_convert`, §5.1). This is a restriction, not a bug: such calls are correct, but slower,
and a call that would have to convert mutable data laid out differently is rejected (§5.1, Polymorphic Calls) where
a specialized call would not need to convert it. Specializations were found and looked up by name, so a binding that
shadowed a top-level or module function used to get that function's specialization; `specializable_callee` in
`codegen/c_analysis.py` now checks that the callee is the top-level or module binding itself.

**Reproduce.** `let f(n: Int): Int = begin let pick(A::TYPE x: A y: A): A = y; pick(:P r1 r2).a end`, with `P` a
record type: the generated C calls `pick`'s generic closure, with boxed records, rather than a specialized clone.

**Where to start.** `find_specialization_calls` and `specialize_typed_fun` in `codegen/c_analysis.py`, which key
specializations by name and clone a function from `funs_dict`; a local function would be keyed by its binding's
symbol, cloned where it is bound (it may capture variables of the enclosing function, so the clone is a closure built
alongside the original), and called directly at specialized call sites. Calls of parameters and tuple components
cannot be specialized statically, since the function is not known.

**Done when.** Calls of local polymorphic functions with record or variant type arguments use specialized clones,
golden tests cover local functions that capture variables of the enclosing function, and §6.4.3 describes them.
The IR's specialize pass (`docs/ir.md` §8.1) does this already; it is done for C when the C printer (§12, step 5)
replaces the current emitter.

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

**Where to start.** `_synth_exception_expr` in `bootstrap/python/quest/typechecker/typecheck.py`, which declares the
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
rejected, and `tests/errors/run/layout_conversion_mutable_data.quest` runs interpreted but fails in both C backends
with `a value used at type Array(Tuple v: Record age: Int fuel: String end end) was laid out by generic code, and
converting it would copy mutable data`.

**Where to start.** `_check_closed_type` in `bootstrap/python/quest/typechecker/typecheck.py` makes the static
check; `quest_convert` and `quest_layout_conversion_error` in `runtime/quest_runtime.c` the run-time one. Lifting
the restriction needs conversion without copying: converting array elements and var slots lazily, through a view
that reads and writes the original's layout, or a uniform layout for type-parameter positions inside mutable data
(compare "Conversions that copy change object identity in C" above). With the IR (`docs/ir.md`), either is a
change to the represent pass.

**Done when.** The four tests above run (the error tests becoming golden tests) with the same results interpreted
and in both C backends.

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
`bootstrap/python/quest/typechecker/typecheck.py`, and `_emit_auto_inspect` in
`bootstrap/python/quest/codegen/c_emitter.py`. Shares a solution with the task above: var components converted
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
encoders and decoders in `bootstrap/python/quest/dynamic_json.py` and `runtime/quest_serialization.c`
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
`auto :Tuple v: ?0 w: Int end with …` with `--stop-after run_c_compiled` and `run_c_ir`. Serialization is
structural and not affected.

**Where to start.** `quest_instantiate_descriptor` in `runtime/quest_runtime.c` could build the instance's name
from the template's with the holes replaced by the arguments' names (memoized with the instance), or the printer
(the `QTYPE_KIND_AUTO` case near `printf("auto :%s with"`) could print descriptors structurally. `hole_var` in
`bootstrap/python/quest/codegen/c_types.py` names the holes.

**Done when.** Both C backends print the program above as the interpreter does, and a golden test covers it.

---

## Uncaught exceptions are reported at the wrong place, or none

**Problem.** An exception that escapes the program should be reported where it was raised, with the source line, as
the interpreter does for `raise` in the program itself. Elsewhere it is not:

- Compiled code does not know where it raised. A binary run directly prints only `Exception: E`, and the
  `run_c_compiled` and `run_c_ir` phases report the binary's stderr at offset 0, so every uncaught exception
  appears to be at `1:1`, under the program's first line.
- In the interpreter, an exception raised inside a library module, such as `dynamic.error` from `dynamic.be`, is
  reported either with no location or at its offset in the module's source rendered against the program's, which
  can name a line past the end of the program.

**Reproduce.**

```quest
let a = 1;
let b = 2;
let e = exception E end;
let f(n: Int): Int = raise E end;
f(a)
```

is reported at `4:22` interpreted but at `1:1` by `--stop-after run_c_compiled` and `run_c_ir`, and as a bare
`Exception: E` by the binary that `-o` builds. With

```quest
import dynamic: Dynamic;
let f(A::TYPE x: A): Dynamic = dynamic.new(:Tuple v: A w: Int end tuple x 1 end);
let g: All(A::TYPE x: A) Dynamic = f;
let d = g(:String "hi");
let n = dynamic.be(:Int d);
```

the interpreter reports `dynamic.error` at `6:1` in a five-line file.

**Where to start.** In C, `quest_raise` and the uncaught-exception handler in `runtime/quest_runtime.c` (near
`fprintf(stderr, "Exception: %s\n", name)`) have no source position; the generated code could pass one to raises
(and to the run-time checks that raise, such as integer overflow), or keep the position of the outermost phrase
being run, and print `file:line:col`. The run phase (`run_c_compiled` in `bootstrap/python/quest/pipeline.py`)
should then parse that, or report without a location rather than at offset 0. In the interpreter, a
`QuestException` raised while running a module's code should carry that unit's source map (as `in_unit` in
`diagnostics.py` does for compile-time errors), or be relocated to the call in the program it escaped through.

**Done when.** Both programs above report a correct location (in the program, or in the library module with its
file name) in the interpreter and in both C backends, a binary run directly prints the location, and error tests
cover an exception raised in the program and one raised in a library module.
