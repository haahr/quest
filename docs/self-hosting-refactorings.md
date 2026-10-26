# Refactorings for Self-Hosting

This plan reshapes the Python bootstrap compiler (`bootstrap/python/quest/`) so that translating it to Quest, the
self-hosted compiler of [roadmap.md](roadmap.md), is line-by-line work rather than redesign. It changes no language
behavior. The constraints are the reorganization's: golden output and errors change only where a step says so, every
benchmark stays within 10% of main (`tests/perf/measure.py`), and both suites pass at every commit.

[converting-python-to-quest.md](converting-python-to-quest.md) already covers the ordinary translations (classes to
options, `id()`-keyed dictionaries to `hash.identityEqual`/`identityHash`, `with` blocks to higher-order functions,
generators to callbacks or vectors, `match` to `case`). This plan is about the places where the compiler relies on
Python features that have no line-by-line Quest counterpart:

- **Formatting C.** The C backend builds C text with about 600 f-strings and 40 `', '.join(...)` calls. Interpolating
  strings translates mechanically to `<>`, which is right-associative. Interpolating anything else does not: Quest's
  `conv.int` writes negative numbers with `~`, C needs reals spelled as Python's `repr` spells them (with `-` and `INFINITY`), and joins over
  comprehensions become a `vector.map` and a `strutil.join` each.
- **Reflection.** About fifteen generic traversals walk nodes with `dataclasses.fields` and `getattr`, and one
  rebuilds them with `type(node)(**...)`. Quest has no reflection.
- **Nodes discriminated by which fields are set.** `ir.Addr` and `ir.Store` each have several forms told apart by
  which optional fields are `None`, and an `index` that is an `int` or an atom, told apart by `isinstance`.
- **Duck typing.** `hasattr(t, "prune")`, `getattr(t, "_fv", None)`, `hasattr(env, "lookup_type_by_id")` and the like
  ask at run time what type a value has. Quest needs the answer in the type.

The phases are independent of one another; the steps within a phase are ordered.

**Status: complete** (October 2026). Each step's **Done** note says what it did.

---

## 1. Phase 1: Fixes

**1a. Escape non-printable characters in C literals as three-digit octal.** `c_string_literal` and `c_char_literal`
(`codegen/c/types.py`) write a character outside printable ASCII as `\xHH`. A C hex escape consumes every hex digit
that follows it, so the Quest string `"\x01a"` becomes the C literal `"\x01a"`, which C reads as the single character
0x1a: a silent miscompilation. Write every such character as a three-digit octal escape, `\ooo` (`\001`). An octal
escape takes at most three digits, so always writing three makes the escape end where it should whatever follows.
Character literals don't have the problem (the quote ends the escape), but use the same spelling, so one helper
serves both.

- Add a language golden test printing strings in which an escaped character is followed by a hex digit and by an
  octal digit (`"\x01a"`, `"\x017"`), with their lengths, so the three backends are checked against one another, and
  a unit test of both helpers.
- Goldens of generated C change only where a literal holds such a character.
- Not in scope: `values/model.py` and the runtime's `quest_put_escaped_char` write `\xHH` too, but they display Quest
  values in Quest syntax, not C, and Quest's `\xHH` takes at most two digits.

**Done.** Before the fix, `"\x01a"` silently became one character in C, and `"\xff0"` did not compile at all ("hex
escape sequence out of range"). `language/string_escapes` and `tests/python/test_c_text.py` test the escapes.

**1b. Delete external templates.** `TypedExternal.inline_template` and `TypedNativeBinding.inline_template`
(`typechecker/typed_ast.py`) are never set, so `ir.External.inline_template`, `ir.CallExternal.inline_template`, their
lowering (`ir/lower.py`), and the printer's `o.inline_template.format(*descs, *args)` and its thunk cache key
(`codegen/c/printer.py`) are dead. Left in place, the Quest compiler would need an interpreter of Python format
strings. Delete them and update [ir.md](ir.md) where it mentions them. No golden changes.

**Done.** `TypedNativeBinding` itself was never constructed, so it is gone too, with `ir.External.pass_type_descriptors`
(only a native binding set it) and `TypedExternal.c_val`. [ir.md](ir.md) did not mention templates.

---

## 2. Phase 2: A Vocabulary for C Text

The C printer stays a printer of strings. Writing into a builder or writer as it goes is not an option: printing an
operation can emit temporaries before the expression it returns (`make_closure`, `Addr` of a cell), and the returned
expression is often placed later or used twice (the base `b` in the proxy checks). A tree of C syntax is not worth it
either: it would centralize parenthesization, but it means rewriting all of the backend and every golden, and without
overloading or varargs, building trees in Quest is no shorter than building strings.

What changes is that every piece of C text comes from a small set of named helpers, so that each Python line has a
one-line Quest counterpart.

**2a. Add `codegen/syntax.py` with literal formatters.** Move `c_string_literal` and `c_char_literal` there (as
`c_string` and `c_char`), and add:

- `c_int(n)`: a nonnegative integer in decimal, for indices, counts, and field numbers (`_{index}`, `c{i}`, `d{i}`).
  It asserts `n >= 0`. In Quest it is `conv.int`.
- `c_int_literal(n)`: an `int64_t` constant as the printer writes it now (`5LL`, `(-5LL)`). In Quest it is the one
  place that spells negative numbers with `-`.
- `c_real(r)`: a `double` constant as the printer writes it now (`printer.const`: `repr`, `.0` appended when needed,
  `INFINITY`, `(-INFINITY)`). Its Quest counterpart needs no new primitive: `conv.real` already writes `repr`'s
  shortest round-trip digits (`quest_format_real` in the runtime, [type-system.md](type-system.md) §6.3.1), so it
  formats the magnitude with `conv.real` and writes the sign as `-`. Check that the two agree on the boundary between
  fixed and exponent notation, and on `.0`, with a unit test over the corpus's real constants.
- `index_table(entries)`: the compound literal `_index_table` builds, the one place a C brace is written inside an
  f-string with `{{`.

**2b. Add combinators for the C forms the backend repeats.** All take and return strings, and spell exactly what the
code they replace spells, so output is byte-identical:

- `comma(args)`: `', '.join(args)`.
- `call(f, args)`: `f(a, b, c)`.
- `cast(c_type, e)`: `((T)e)`; `paren(e)`: `(e)`.
- `deref(e)`: `(*e)`; `addr(e)`: `(&e)`; `arrow(e, field)`: `e->field`; `dot(e, field)`: `e.field`.
- `index(e, i)`: `e[i]`.

Where existing code spells the same form two ways (for example `*{ptr} = ...` as a statement but `(*{name})` as an
expression), keep both spellings as two helpers or as plain concatenation in this step. Normalizing them, if wanted, is
a separate commit that only regenerates goldens.

**2c. Convert the backend.** Rewrite `codegen/c/printer.py`, `codegen/c/declarations.py`, `codegen/c/types.py`,
`codegen/c/headers.py`, and the C-spelling parts of `codegen/layout.py` and `codegen/symbols.py` to the helpers, a file
per commit. When done:

- every value interpolated into an f-string in these files is a `str` (literals go through 2a's formatters);
- no f-string has a format spec or conversion (`:02x`, `!r`) or a doubled brace;
- `.join(` appears only in `syntax.py`.

Add a unit test that checks the last two rules with the `ast` module, so they don't erode. The first can't be checked
statically; review it per file. In Quest, `call` takes its arguments as an array, so listfix syntax replaces the joins:
`call("quest_view_tuple_slot" of b vm conv.int(index) end)`.

**2d. Document the idiom.** Add a section on generating text to [converting-python-to-quest.md](converting-python-to-quest.md):
interpolated strings become `<>` chains, numbers go through the C formatters (never `conv.int` for a C integer constant),
`call`/`comma` take arrays by listfix, and a `printf`-style helper (`fmt of "$->_$ = $;" b i v end`) is an option where
a line has many holes. Note in it that the IR printer (`ir/printer.py`, 100 f-strings) follows the same rules if it is
ported; whether the self-hosted compiler needs it is a decision for then.

**Done**, in one commit, with the generated C of the whole corpus byte-identical. It differs from the plan in three ways:

- **Doubled braces are allowed.** In Quest a brace is just a character of a string literal (`f"{{ {args} }}"` is
  `"{ " <> args <> " }"`), so banning them would change nothing about translating.
- **Only the combinators that replace joins exist:** `comma`, `call`, `joined` (names' parts), and `lines_text`.
  `cast`, `deref`, `addr`, `arrow`, `dot`, `index`, and `paren` would only restyle f-strings of strings, which already
  translate as they are.
- **Finding the integers.** Running both suites with every interpolation in the backend wrapped by a recorder of its
  value's type found the integers (about 120 sites, all `int`); the sites the corpus does not reach were reviewed by
  hand. The declarations' own escaping of descriptor names became `c_string`.

`tests/python/test_c_text.py` checks the literals (including `c_real` against `conv.real` over every real constant in
the corpus and the library) and the two rules.

---

## 3. Phase 3: Explicit Traversals

Each node family gets one explicit traversal, written as a `match` with a case for every node class, and every generic
walker is rebuilt on it. The Quest version then writes each traversal once, as a `case`.

For each step: first add the explicit traversal and a unit test that runs it and the reflective walker it replaces
side by side over the IR (or typed AST, or types) of the whole golden corpus and requires them to agree, and a test that
every node class in the family has a case (the tests may use reflection; only the compiler may not). Then switch the
callers and delete the reflective walker. Measure: explicit cases should be no slower than `dataclasses.fields`.

**3a. IR.** In `ir/walk.py`, add `operands(node)` (the atoms, descriptors, and nested bodies of an operation or
statement, in field order) and `map_operands(node, f)` (a copy with each atom replaced), replacing:

- `_atoms_of` in `ir/walk.py`;
- the two `visit` walkers in `ir/describe.py` (lines 103, 488);
- `_rename_fields` in `ir/closure.py`, which also mutates with `setattr`; rebuild with `map_operands` instead;
- the field loop in `ir/verify.py` (line 116);
- `copy` in `ir/specialize.py`, which rebuilds any IR node with `type(node)(**...)`;
- the `getattr(o, "view_map", None)` reads in `ir/verify.py` and `ir/printer.py`, which become cases.

**3b. Typed AST.** In `typechecker/typed_ast.py`, add `children(node)`, replacing the four walkers in
`typechecker/scoping.py` (lines 89, 119, 150, 204) and `visit_node` in `codegen/c/declarations.py` (lines 205–231),
which finds types by probing for `type_val`, `symbol`, and `definition` attributes with `hasattr`.

**3c. Types.** In `types/model.py`, add `type_children(t)` and `map_type_children(t, f)`, replacing the interning key
(line 181), the two rebuilds (lines 1392, 1421), the walker at line 1633, `_type_vars` in `ir/represent.py` (line 127),
and the walker in `codegen/descriptors.py` (line 97). Check `types/kinds.py`, `types/canonical.py`, and
`types/dump.py`, which use `getattr` too, and convert what is generic traversal.

**Done**, in one commit with phase 4, which changes the IR's classes. The traversals are less specific than planned:
each family has an accessor of its nodes' field values, in order, and a rebuilder of a node from such values, written
once from the dataclasses' fields and kept as ordinary code. The walkers kept their logic and read fields through
these instead of `dataclasses.fields`, `getattr`, and `type(node)(**...)`. A `children`/`operands` per walker would
have meant a dozen traversals per family where one serves.

Each is a table with an explicit entry per class (`{ir.Var: lambda node: (node.hint, ...), ...}`) rather than a
`match`: a `match` tests classes in turn, so for the families' 40 to 80 classes it was slower than reflection (C
generation took 18% longer than main, interning a late class 1.7µs rather than 0.6µs), and a table is 5 times faster
than reflection. A types' class registers its entries right after its definition, so that interning its first
instance finds them. Measured on the corpus (CPU time, interleaved), type checking takes 0.96 of main's time and C
generation 0.83 (with `fresh_name` made linear: its search for a base's next name now starts where the last stopped).

- **Types** (`types/model.py`): `type_fields` and `rebuild_type`, used by interning, `map_aliases`, `strip_aliases`,
  `unsolved_metas`, `structurally_equal`, `canonical._may_recur`, `represent._type_vars`, `describe.free_type_vars`,
  the descriptors' bound-variable walker, and `collect_aggregate_types` (whose typed-AST branches were dead: every
  caller passes types). `QTypeFormal` records its free variables (its bound's), as every other component does.
- **IR** (`ir/walk.py`): `fields_of` and `rebuild` (specialization's copy), `contents` (the fields but descriptor
  operands: `_atoms_of`, the verifier, `unit_types`), `replace_vars` (closure conversion's renaming, in place), and
  `view_map_of`.
- **Typed AST** (`typed_fields`, `rebuild_typed`): the scope checker's four walkers, `named_exceptions_in`, and
  `resolve_typed_metas`.
- **Syntax tree** (`ast_fields`, `rebuild_ast`): desugaring's walk. The tree's printer (`ast_dump`, for `parse`
  goldens) still reads fields by name, as the IR's and typed AST's printers do their own: debugging printers, to be
  written per class if they are ported.

`tests/python/test_traversals.py` checks that every class has an entry in each table, and that each agrees
with the dataclass fields on every node of the `language/` programs (about 80,000 nodes: all of the typed AST's and
types' classes, 71 of the IR's 75, 77 of the syntax tree's 83).

---

## 4. Phase 4: Node Shapes and Duck Typing

**4a. Split `ir.Addr` and `ir.Store` by form.** `ir.Addr` is the address of a mutable variable (`var`), a fresh cell
(`cell`), a record field (`base`, `name`), a tuple component (`base`, an `int` `index`), or an array element (`base`, an
atom `index`); `ir.Store` likewise stores through an address, into a field, a component, or an element. Make each form
its own node class: `AddrVar`, `AddrCell`, `AddrField`, `AddrComponent`, `AddrElement`, and `StoreAt`, `StoreField`,
`StoreComponent`, `StoreElement`, each with only the fields it uses (`access` on the component forms, `offset` on the
element forms, `view_map` on the field and component forms). The printer's guarded cases (`case ir.Addr(...) if
isinstance(index, int) and vm is not None`) become plain ones. Keep the IR printer's text for them unchanged, so IR
goldens don't change. Update [ir.md](ir.md).

**Done** as planned (`AddrCell`'s field is `init`). The IR interpreter's `address` and `store` became matches too.

**4b. Other unions in the IR.** Decide, case by case, how these translate, and change the Python where a variant reads
better:

- `Const.value: int | float | bool | str | None`, already tagged by the constant's shape: in Quest a variant with a case
  per shape.
- `Try.catches: None | str | tuple[Atom, ...]`: three meanings in one field; make it explicit (a small class or
  separate fields).

**Done.** `Const.value` stays a union: the constant's shape says which, as a Quest port's variant would. A try has
`catching`, one of `CATCH_LISTED`, `CATCH_ALL`, and `CATCH_UNKNOWN` (in the style of the IR's other tags, such as
`access`), and `catches`, a plain tuple of atoms.

**4c. Remove duck typing.** Make each of these questions answerable from the declared type:

- `t.prune() if hasattr(t, "prune")` (`ir/written.py` 135, 146; `ir/shapes.py` 183; `codegen/layout.py` 529, 712):
  give the type base class `prune`, or prune where the value enters.
- `getattr(t, "_fv", ...)` and `getattr(t, "_has_meta", ...)` (`ir/describe.py` 87; `ir/shapes.py` 187, 190;
  `codegen/layout.py` 530, 588; `ir/represent.py` 127, 138; `typechecker/scoping.py` 123; `types/model.py` 178, 1426):
  make them fields every type has, with defaults.
- `hasattr(env, "lookup_kind_by_id")`, `hasattr(env, "lookup_type_by_id")` (`types/model.py` 310, 1209): type the
  parameter as the environment, or as a protocol with those methods.
- `getattr(env, "source_map", None)`, `getattr(options, "echo", echo)` (`ir/lower.py` 144, 984): declared fields.
- `hasattr(q.bound, "bound")` (`ir/lower.py` 699), and `getattr(v, "type_val", None)`, `getattr(v, "is_var", False)`,
  `getattr(f, "name", None)` (`codegen/c/declarations.py` 459, 769, 785): test the class instead.

Leave the `type(x).__name__` uses in error messages; they become strings written per case in Quest, and nothing
depends on them.

**Done**, for these and every other `getattr` and `hasattr` in the compiler (the interpreter, REPL, and test harness
keep theirs): `pruned(t)` in `types/model.py` (only a metavariable prunes); `_fv` and `_has_meta` read directly; the
environment's methods and fields, the options' fields, and AST nodes' offsets read directly (their classes always
have them); a path type, which has no symbol of its own, told apart by class; the builtin registry's `ensure_module`
and `ensure_interface` in its protocol; a shape filled in from another by `Shape.fill_from` rather than by its slots'
names; the parser's signature items by a match (`_signature_name`). Along the way: `format_type_for_qi` named
`QTupleTypeFormal` and `QTupleTypeBinding` without importing them, so writing a `.qi` type of a tuple with type
components raised `NameError`; it imports them now, and `test_interface_compiler` tests it.

---

## 5. Phase 5: The Typed AST's Printer and the Interpreter

What phase 4c did for the compiler, for the parts of Milestones 2 and 3 it left out.

**5a. The typed AST's printer.** `TypedNode.dump` prints the `typecheck` goldens. It decides whether to show a node's
type with `hasattr(self, "type_val")` and `getattr(self, "type_val")`, and calls `dump_header` with an environment,
catching `TypeError` to call it without one, because 31 of its 36 overrides take none.

- Every `dump_header` takes `env` (unused by most), so `dump` calls it one way.
- `dump_show_type` becomes `dump_type()`, the type to show or None: None for a `TypedNode`, the node's `type_val` for
  a `TypedExpr` and a `TypedParam` (the only nodes with types), None for the ten classes that hide theirs.

The class name that heads each node stays `self.__class__.__name__`: a Quest printer writes it per case.

**Done** as planned.

**5b. The interpreter's, values', and REPL's probes.**

- `QReader` declares `peek: Optional[str]`, the character `reader.more` read ahead, which the builtins set on it as an
  undeclared `_peek_char` attribute and read with `getattr(r, "_peek_char", None)` (five places).
- `quest_conv_bool` reads its argument's `value` when it is a `QBool`, rather than `getattr(b, "value", False)`.
- `values_equal` (`values/model.py`) reads `v2.value` directly: it has checked that `v2` is of `v1`'s class.
- The tree-walking interpreter reads an unhandled expression's `offset` directly (every typed node has one), and
  whether a binding's members are bound already by `declared_name`, a match over the bindings that declare a name,
  rather than `getattr(member, "name", None)`.
- The REPL reads the interpret phase's results through the pipeline's `InterpretPhase`, rather than
  `getattr(interpret_phase, "last_phrase_results", [])`.

**Done** as planned; no `getattr` or `hasattr` is left outside the test harness. (`repl.py` also imports `Any` now,
which an annotation named without importing.)

**5c. The externals table.** `EXTERNAL_SYMBOLS` mixes the interpreter's builtin functions (124) and its constant
values (34: exceptions, readers and writers, numeric limits), told apart by `callable()` in
`resolve_external_symbol` and again in both interpreters' calls of externals. It becomes two tables,
`EXTERNAL_FUNCTIONS` and `EXTERNAL_VALUES`, and `resolve_external_symbol` returns a `QBuiltinFun` for a function and
the value for a value, so callers apply a `QBuiltinFun` and take anything else as it is. The builtins keep their
signatures and the `qchecked` decorator (by decision).

**Done** as planned; `test_builtins` checks that each table holds only its kind.

The interpreter's output, and so every golden, is unchanged; both suites pass at every commit.

---

## 6. Not in This Plan

- **Porting.** No Quest code is written here.
- **The test harness** (`testing/`), which the self-hosted system does not need. (This plan first left out the
  interpreter and REPL too, but the self-hosted system includes both: [compiler-organization.md](compiler-organization.md)
  Milestone 3. Phase 5 covers them.)
- **Spelling changes to generated C** beyond 1a, such as normalizing parenthesization.
- **The parser's grammar actions** (`syntax/grammar.py`), by decision: they stay as they are, though the Quest
  parser's actions take a uniform array of `engine.Val` ([compiler-organization.md](compiler-organization.md) §4.1) and
  the Python ones mixed positional values, and though the postfix operators' actions return closures. The Quest code
  may diverge there.
- **Exceptions**, by decision until there is more experience with the compiler in Quest: the Python errors' class
  hierarchy (`QuestCompilerError` and its subclasses, some caught by subclass) and the catches of Python's own errors
  (`ValueError` from `Path.relative_to` and `int`, `except Exception` in the pipeline), against the Quest side's one
  exception carrying a diagnostic (`diagbag.fatalError`).
