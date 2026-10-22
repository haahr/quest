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

## Tuples and options over type parameters across polymorphic calls in C

**Problem.** Compiled code fails to compile (clang reports incompatible pointer types) when a tuple or option type
that mentions a type parameter passes into or out of a polymorphic function, directly or inside a recursive type:
the generic code uses the type's struct with `QVal` in place of the parameter, and the caller the struct specialized
to the type argument. Records, variants, and arrays over type parameters work. The interpreter handles all of them.

**Reproduce.** With `box.quest` containing

```quest
Let Box = Fun(A::TYPE) Option none some with head: A end end;
let some(A::TYPE head: A): Box(A) = option some of Box(A) with head end;
let b: Box(Bool) = some(:Bool true);
b!some.head
```

`--stop-after interpret` prints `true : Bool`, while `--stop-after run_c_compiled` fails in clang, assigning a
`QOption_none_some_QTuple_QVal_end *` to a `QOption_none_some_QTuple_Bool_end *`. `Tuple x: A end` fails the same
way, as do arguments (`let get(A::TYPE b: Box(A) d: A): A = ...` called with a `Box(Bool)`) and recursive types
(`Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end` with `cons(:Bool true ...)`).

**Where to start.** Calls convert arguments and results between views in `codegen/c_emitter.py` (`_emit_call_arg`,
`_coerce_val`, `_coerce_tuple_val`, and the bound-view conversions `_held_view`, `_needs_bound_view` and
`_bound_view_conversion`), and C type names come from `qtype_to_c_type` in `codegen/c_types.py`. Records stay
representation-compatible through offset tables (`_coerce_record_val`); tuples and options are structs whose layout
depends on the element types (`docs/c-representation.md`), so either generic code must use the same struct as its
callers (for example, by representing a parameter's position uniformly as `QVal` in both) or each crossing must
convert, which for recursive types means converting the whole structure, so a uniform representation is likely the
better fix.

**Done when.** The programs above, and the same with `Tuple`, recursive options, and groups of recursive type
operators (`Tree(A)` and `Forest(A)` passed to and returned from polymorphic functions), print the same in
`interpret` and `run_c_compiled`, covered by a golden test.
