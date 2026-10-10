# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

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
