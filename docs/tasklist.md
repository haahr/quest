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
`python run_tests.py -k <test>` passing in both `interpret` and `run_c_compiled`. Because of this bug,
`tests/source/modules/inline_module_imports.quest` skips `run_c_compiled`: remove its `@skip-phase` directive.

---

## Let compiled code use the list module without an import

**Problem.** A program may use the library modules `conv`, `int`, `ascii`, `string`, `arrayOp`, `reader`, `real`,
and `list` without importing them (Cardelli's prelinked modules). The interpreter and compiled code both accept that
for every module but `list`: compiled code that uses `list` without an import refers to `qv_list`, which nothing
declares, and the C compiler rejects it.

**Reproduce.** With `prelist.quest` containing

```quest
let l = list.cons(:Int 1 list.nil(:Int));
list.length(:Int l);
```

`python3.11 bootstrap/python/quest_driver.py --stop-after run_c_compiled prelist.quest` fails with
`error: use of undeclared identifier 'qv_list'`, while `--stop-after interpret` prints `1 : Int`. With
`import list: List;` added, both work.

**Where to start.** Compare how a prelinked module that works (`conv`, say) is declared and linked in C with how
`list` is: `list` is a polymorphic module compiled from `lib/list.mod.quest`. Look for the list of prelinked modules
in the C emitter and the build engine (`unit_module_refs` in `bootstrap/python/quest/build/engine.py`), and for where
an explicit import adds a module's declarations (`emit_precompiled_module_declarations` in `c_declarations.py`).

**Done when.** The program above runs in C, and `tests/source/stdlib/library_prelinked_dynamic_list.quest` uses
`list` without its `import list: List;` (and says so in its opening comment), passing in both `interpret` and
`run_c_compiled`.
