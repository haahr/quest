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

## Source locations for errors in interface and module files given to the driver

**Problem.** When an interface or module file is passed to the driver directly, its errors are printed without a
location: no `file:line:col` and no source line with a caret. This happens for any error, such as "Cannot find
common supertype for conditional branches 'Ok' and 'Int'" or "Undefined variable". The same errors in a program file
are located. This made errors slow to track down while migrating StringBuilder callers. The driver also ignores
`--stop-after` for these files: it compiles them fully, writing `.qi`, `.qm`, `.c` and `.o` files next to the
source unless `--build-dir` is given.

**Reproduce.** With `m.int.quest` containing `interface M export f(c: Bool): Ok end;` and `m.mod.quest` containing

```quest
module m : M export
    let f(c: Bool): Ok = begin if c then ok else 3 end; ok end;
end;
```

`quest_driver.py --stop-after typecheck m.mod.quest` prints only `quest: error: Cannot find common supertype for
conditional branches 'Ok' and 'Int'`. The same function in a program file is reported at `3:9` with a caret.

**Where to start.** `bootstrap/python/quest_driver.py` handles `.int.quest` and `.mod.quest` files in two places,
the default mode (around the `compile_interface_file` and `compile_module_file` calls) and `compile` mode. Both
catch `Exception` and write `str(err)`. They should render a `QuestCompilerError` as programs do, through
`diagnostic_of` (`diagnostics.py`, which supplies the file's source map) and `DiagnosticRenderer.render_diagnostic`.
They should also honour `--stop-after`.

**Done when.** Errors in interface and module files given to the driver are located like errors in programs, in
both modes. `--stop-after typecheck` on such a file stops after typechecking and writes no artifacts. Tests (in the
error suite, or in `tests/python/test_quest_driver.py`) cover an interface file and a module file passed directly.

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
