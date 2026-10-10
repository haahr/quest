# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Fix C calls to functions of inline modules

**Problem.** A program that declares an interface and a module inline (in the program itself, rather than in
`.int.quest` and `.mod.quest` files) and then uses a member of the module fails to compile to C, although the
interpreter runs it.

**Reproduce.** With `inline_mod.quest` containing

```quest
interface Counter export T::TYPE make(n: Int): T end;
module counter: Counter export Let T = Int; let make(n: Int): T = n; end;
let k = counter.make(4);
counter.make(5)
```

```bash
PYTHONPATH=bootstrap/python python3 bootstrap/python/quest_driver.py --stop-after run_c_compiled --build-dir /tmp/b inline_mod.quest
```

clang reports `use of undeclared identifier 'qv_counter'` at selections such as `qv_counter.val` and
`qv_counter.dict`: the selection from the module is emitted with the module's plain mangled name, which is not the
name of the module record declared for an inline module. With `--stop-after interpret` the program runs.

**Where to start.** `bootstrap/python/quest/codegen/c_emitter.py`: how `emit_program` declares the records of inline
modules, and how a `TypedSelect` whose target is a module is emitted (`self.all_modules`, `current_env_vars`). The
record names come from `module_record_ident` and `mangle_module_name` in `codegen/c_types.py`. Modules in separate
files work (`tests/source/modules/`); `tests/source/06_interfaces_modules.quest` declares an inline module but never
uses it, which is why the golden suite misses this.

**Done when.** Selecting values and calling functions of an inline module compiles and runs in C, and a golden test
(a new one under `tests/source/language/`, or an extension of `06_interfaces_modules.quest`) covers it, with
`python run_tests.py -k <test>` passing in both `interpret` and `run_c_compiled`.
