# Milestone 3: The Self-Hosted Tree-Walking Interpreter

This plan ports the bootstrap's tree-walking interpreter to Quest: the run-time values (`bootstrap/python/quest/values/`),
the interpreter (`interpreter/treewalk.py`, `primitives.py`, `formatting.py`, `builtins.py`), and `dynamic`
serialization (`values/dynamic_json.py`). At the end, a compiled self-hosted driver runs every program of the test
suite, as `quest --stop-after interpret` does, with the bootstrap's output, exit status, and run-time errors. It
follows Milestone 2 (the type checker, [milestone-2.md](milestone-2.md)) and precedes Milestone 4 (the IR and its
interpreter).

The decisions this plan rests on (2026-10-26):
- **Builtins.** The standard library's externals (`builtins.py`'s `EXTERNAL_FUNCTIONS` and `EXTERNAL_VALUES`, 159
  C symbols) call the real library: an interpreted string, word, reader, or writer is the native Quest value, and
  `quest_string_get_char` is `stringOp.getChar`. Their semantics are then compiled code's, which shares the run
  goldens with the interpreter. Only what acts on interpreted values themselves is ported: `dynamic.copy`, `extern`,
  and `intern`, the identity hash, `list`, and `system.args` (§2).
- **Driver.** The interpret phase as the tests use it (§3.1), and `-e`. The REPL and `--interactive` are not in this
  milestone.
- **JSON.** `dynamic.extern` and `intern` need JSON text, which the bootstrap gets from Python's `json`. The Quest
  JSON values, parser, and printer are private to `questlang/values/` (`json`), shaped for `dynamicjson`; they can
  become a library later.
- **Module values.** The bootstrap keeps a module's run-time value on its unit in `modules/graph`, which in Quest is
  below the values. Step 0 moves it to the interpreter's own state in the bootstrap first, so the layouts stay the
  same.
- Carried over from Milestone 2: golden tests only, the full goldens run against the compiled driver, `questlang/`
  follows the bootstrap module for module, divergences only where Quest cannot hold what Python does (each documented
  where it is made), and the steps run straight through, each pushed when its runs pass.

---

## 1. Layout

```
questlang/
├── types/         canonical (new, partial: normalize_type, resolve_type_bound, option_case_names; the rest is M4's)
├── values/        model, json (new, §1.2), dynamicjson
├── interpreter/   primitives, formatting, builtins, treewalk
└── driver/        main (the interpret phase and -e, §3.1)
```

`values` is above `types`, `typechecker` (`dynamicjson` parses and elaborates type strings, as the bootstrap's
lazy imports do), and `modules` (`dynamicjson` uses `abstracttypes`); `interpreter` is above `values` and `modules`
(it loads modules through the loader). The bootstrap's other lazy imports here (`treewalk` of `builtins`, `stdlib`,
`env`, and `loader`) go one way, so they become ordinary imports. The IR interpreter (`ir_interp.py`) is
Milestone 4's.

### 1.1. Step 0's refactoring

`UnitGraph`'s units hold `value`, the record a module's run makes, which `load_module_for_interpreter` reads and
writes and the REPL's rollback restores (`UnitGraph.snapshot`, `restore`). It moves to the interpreter: a table of
module values by canonical name, on the `RuntimeEnvironment`'s root state beside `call_stack`, which the REPL
snapshots and restores with the graph. No output changes.

### 1.2. Representations

- **Values** are an option, `model.Value`, with a case per `QValue` class. A scalar holds its Quest value (`Int`,
  `Real`, `Char`, `Bool`, `word.T`); a string, reader, writer, string builder, or list holds the native object, so
  `is` on interpreted values is `is` on what they hold (Cardelli's identity, `qvalue_is`). Records, tuples, arrays,
  closures, auto values, exception values, and type values are tuples whose identity is the interpreted value's;
  records are hash maps, printed in sorted order as `QRecord` is.
- **References** (`QRef` and its array-element and tuple-component forms) are an option of cells with `var`
  fields.
- **Environments** are the bootstrap's frames: a hash map of bindings, a parent, the type bindings, and the
  exceptions made in advance, sharing the root state (include paths, units, source map, call stack, module values).
- **Control** is Quest exceptions: the loop exit (`_LoopExit`), a raised Quest exception (`QuestException`, with its
  exception value, payload, payload type, offset, source map, and frames), and run-time errors (`QuestRuntimeError`,
  as `diagnostics.compilerError`).
- **Diagnostics** gain the bootstrap's `trace`, the frames rendered after the source line (docs/exceptions.md §2.1).

---

## 2. Builtins

`interpreter/builtins` is the table from external symbol to implementation, as the bootstrap's is: a function of the
argument values, or a value (`EXTERNAL_VALUES`, such as `quest_writer_output` and `QUEST_INT_MAX`). An
implementation unwraps its arguments, calls the library function the symbol names, and wraps the result.

- **Errors.** A library function raises its module's native exception (`stringOp.error`); the implementation
  catches it and raises the interpreted one (`STRING_ERROR_EXC`), which the interpreted library binds to `error`
  through the same table, so the program's `try` catches it. Arithmetic and real operations use `primitives`, as in
  the bootstrap, with Quest's own `Int` and `Real`.
- **Ported, not called:** `dynamic.copy`, `extern`, and `intern` (§4 Step 5), `quest_identity_hash` (the identity
  hash of what `is` compares), `list` (a native `list.T(Value)`), and `system.args` (the arguments after `--`).

---

## 3. Testing

### 3.1. The driver

`questlang/driver/main` gains the interpret phase, which runs the typed program and prints the last phrase's result
as `InterpretPhase.dump` does (`format_interactive_result`); it is the driver's default, as for the bootstrap. It
takes the options the runner passes to run phases: `--echo`, `--expected-exit`, and the program's arguments after
`--`. An uncaught exception or run-time error is printed as the bootstrap prints it, with its frames, and the exit
status is the bootstrap's. `-e PROGRAM` runs a program given as a string (`<string>`), printing its last result.

### 3.2. Runs

- **The self-hosted suite** adds `interpret` to its phases: the run goldens (`tests/golden/run`, 193) and run-time
  error tests (`tests/errors/run`, 16), with their directives (`@args`, `@stdin`, `@env`, `@exit`, `@echo`). The
  pending list starts with all of them and is empty when the milestone is done. This includes the ten questlang tests
  the bootstrap interprets: the self-hosted compiler's modules run in the self-hosted interpreter.
- **`-e`** has no goldens. A generated test, `tests/eval/generate.py`, runs the bootstrap's `quest -e` on the
  programs of `tests/eval/cases.quest` (one per line, covering each kind of result `format_interactive_result`
  prints, and an error) and records the output; the self-hosted suite compares the driver's.
- **The questlang tests** run compiled, and **the bootstrap's suites** run when a commit changes the bootstrap,
  `lib/`, or `runtime/` (Step 0 does), as in Milestone 2.

---

## 4. Steps

Each step is one or more commits; each ends with its runs passing.

### Step 0: Module values leave the unit graph (done)

§1.1, in the bootstrap. `tests/python/test_unit_graph.py`'s tests of the values a snapshot keeps and forgets move
to the interpreter's table, and both bootstrap suites pass.

### Step 1: Values, the core evaluator, and the interpret phase

Port `values/model`, `types/canonical`'s part (§1), `interpreter/primitives`, `formatting`, and the core of
`treewalk`: literals, variables and references, operators, blocks, functions and application, conditionals and
loops, records, tuples, arrays, variants, options, and `case`. Add the interpret phase and `--echo` to the driver,
`interpret` to the runner's self-hosted phases, and the run goldens and error tests to the pending list. Enough of
the builtins for output (`writer`, `conv`) lands here, so that goldens of programs without imports leave the list.

### Step 2: Exceptions and run-time errors

Exceptions (`exception`, `raise`, `try`, the exceptions a scope makes in advance), the checked operations' errors
(`int.error`, `arrayOp.error`, `variant.tagMismatch`, and the rest), closures' frame names and the call stack, and
diagnostics' traces. The run-time error tests leave the pending list.

### Step 3: Modules and the standard library

`load_module_for_interpreter`, imports, module declarations, the standard library modules a program uses without
importing them, and the complete builtins table (§2), with `--expected-exit` and program arguments. Goldens that
import the standard library or their own modules leave the list.

### Step 4: Types at run time

Type arguments (`type_bindings`, a closure's instantiation), auto values, type witnesses, `inspect`, and
`dynamic.new` and `be`, with the subtyping they use.

### Step 5: `dynamic` serialization

Port `values/json` (§1.2's decision) and `dynamicjson`: the canonical type table (the graph of types, merged by
bisimulation and numbered depth first), the writer, `parse_type_string` (through the self-hosted parser and
elaboration), the reader, sharing and cycles, and abstract types' representations. `dynamic.extern`, `intern`, and
`copy` join the builtins. The goldens that serialize leave the list; their text must be the bootstrap's, byte for
byte, which is also the C runtime's.

### Step 6: `-e`, and the interpreted questlang tests

Add `-e` and its generated test (§3.2). The questlang tests the bootstrap interprets run in the self-hosted
interpreter; any that take too long under the test timeout get `@timeout`, recorded here.

### Step 7: Done

Empty the pending list; update compiler-organization.md (§2's "so far", §6's Milestone 3 status), interpreter.md (the
self-hosted interpreter beside the bootstrap's), and testing.md; record the divergences in this document.

---

## 5. Done When

- The compiled self-hosted driver passes every run golden and run-time error test with the interpret phase, with the
  bootstrap's output, diagnostics, and exit status, and `-e` matches the bootstrap's on the generated test.
- The questlang tests pass compiled; the bootstrap's suites pass.
- `questlang/` has the layout of §1.

## 6. Not in This Plan

- The REPL and `--interactive`.
- The IR, `types/canonical` beyond §1's part, and the IR interpreter (Milestone 4).
- `.qi` and `.qm` artifacts, build directories, and code generation (Milestone 5).
