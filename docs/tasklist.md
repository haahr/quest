# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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
