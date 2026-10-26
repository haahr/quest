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

**Status: in progress.** Phase 1 is done.

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

**2a. Add `codegen/c/syntax.py` with literal formatters.** Move `c_string_literal` and `c_char_literal` there (as
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

**4b. Other unions in the IR.** Decide, case by case, how these translate, and change the Python where a variant reads
better:

- `Const.value: int | float | bool | str | None`, already tagged by the constant's shape: in Quest a variant with a case
  per shape.
- `Try.catches: None | str | tuple[Atom, ...]`: three meanings in one field; make it explicit (a small class or
  separate fields).

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

---

## 5. Not in This Plan

- **Porting.** No Quest code is written here.
- **The interpreter, REPL, and test harness** (`interpreter/`, `repl.py`, `testing/`), which the self-hosted compiler
  does not need.
- **Spelling changes to generated C** beyond 1a, such as normalizing parenthesization.
