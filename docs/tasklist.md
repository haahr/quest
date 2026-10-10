# Task List

Known problems and planned work that nobody has started yet. Each task describes what is wrong or missing, how to see
it, where to start, and when it is done. Remove a task when the work lands.

---

## Let bindings shadow imported module names in compiled code

**Problem.** In compiled code, a name bound to a module (by an import, or a prelinked library module such as `list`
used without one) keeps referring to the module record after a `let` shadows it, whether the `let` is at top level or
inside a function. The C emitter maps the module name to its record (`qm_<name>`) in `current_env_vars`, and a
`TypedVar` lookup consults that map before anything else, so the shadowing binding's uses compile to the module
record. The interpreter gets this right.

**Reproduce.** With `shadow.quest` containing

```quest
import writer: Writer;
let f(): Int = begin let writer = 3; writer + 1 end;
f();
let writer = 7;
writer + 1
```

`python3.11 bootstrap/python/quest_driver.py --stop-after run_c_compiled shadow.quest` fails in the C compiler with
`invalid operands to binary expression ('QRecordVal' ... and 'long long')` at both additions, while
`--stop-after interpret` prints `8 : Int`.

**Where to start.** The `TypedVar` case of expression emission in `bootstrap/python/quest/codegen/c_emitter.py`
returns `self.current_env_vars[name]` first; the import handling in `emit_program` fills that map with module records.
Resolving by symbol (each `TypedVar` carries its `ValueSymbol`) rather than by name would distinguish the module from
a binding that shadows it.

**Done when.** The program above prints `8 : Int` in `run_c_compiled`, as in `interpret`, and a golden
test covers shadowing an imported module and a prelinked one (`list`), at top level and in a function.
