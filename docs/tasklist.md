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

---

## Attribute diagnostics in imported units to their own files

**Problem.** An error found while loading an imported interface or module is reported against the importing file, at
the offset the error has in the imported file. The file name, line, column, and quoted source line are all wrong, and
the line may not even exist in the importing file. Some messages also embed the raw offset (`at offset 49`).

**Reproduce.** In an empty directory, with `grp.int.quest` containing

```quest
interface Grp
export
    Def A = Record b: Array(Nope) end
    x: Int
end;
```

and `usegrp.quest` containing

```quest
import grp: Grp;
1;
```

```bash
PYTHONPATH=<repo>/bootstrap/python python3.11 <repo>/bootstrap/python/quest_driver.py --stop-after typecheck --build-dir /tmp/b usegrp.quest
```

reports `usegrp.quest:1:1: error: Undefined type 'Nope' at offset 49`, quoting `import grp: Grp;`, instead of an
error at `grp.int.quest:3:29`. A type error in an imported module body behaves the same way: with `cnt.int.quest`
exporting `get(): Int` and `cnt.mod.quest` defining `let get(): Int = "oops";` on its line 4, a program that imports
`cnt` gets `usecnt.quest:3:1: error: Type mismatch ...`: an offset in `cnt.mod.quest`, past the end of the
two-line `usecnt.quest`.

**Where to start.** Interfaces loaded from source are elaborated in `bootstrap/python/quest/modules.py` (the loop over
`decl.signatures`); units are loaded in `module_loader.py` and `pipeline.py`. A diagnostic carries only an offset, and
the driver renders it against the main file's source map (`diagnostics.py`). Errors raised while loading a unit need
that unit's source map, either attached where the unit is loaded or recorded on the diagnostic, and ideally a note
pointing at the `import` that loaded it. The `Undefined type ... at offset N` wording comes from type elaboration
(`elaborate_types.py`), which should drop the offset from the message once the location is right.

**Done when.** Errors in imported interfaces and modules name the imported file with the correct line and column, and
error tests under `tests/errors/` (which may import units placed beside them; `docs/testing.md`) pin the file and line
for both an interface and a module body.
