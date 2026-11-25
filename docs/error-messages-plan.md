# Plan: Error Messages That Point at the Fix

Two kinds of error read badly today: a misused name (an interface for its module, a module for its type, a type
without its arguments) gets a message about the symptom, often somewhere else; and a syntax error is reported where
the parser gave up, with a list of everything it could have accepted there, which is often far from where the fix
goes. This plan makes both point at the fix, without new compiler machinery: the checker adds a help line where it
already reports a failed lookup, and the parser, once a parse has failed, looks again at the tokens to say what was
left open and lists what it expected in words.

Both compilers, with the same text, since the error tests and the shared goldens compare their output
([diagnostics.md](diagnostics.md) §1, [testing.md](testing.md) §3). The two-compilers policy holds: shared behavior
goldens are written by the bootstrap. Each step adds error tests for what it reports
(`tests/errors/<phase>/`), whose expectations match a diagnostic's message, notes, or help (testing.md §3.3).

Not in this plan: recovering from a syntax error to report the next one, a different parsing algorithm, and changes
to how diagnostics are rendered (§5).

## 1. What Is Reported Today

Each of these is what both compilers print, at the place shown.

| Program | Error | Where |
| :--- | :--- | :--- |
| `let sum(it: Iter.T(Int)): Int = ...` then `sum(vector.iter(v))` | `synthesized type 'iter.T(Int)' is not a subtype of expected type 'Iter.T(Int)'` | the call |
| `Iter.map(vector.iter(v) ...)` | `Undefined variable 'Iter'` | `Iter` |
| `let total(v: vector(Int)): Int = ...` | `Undefined type 'vector'` | `vector` |
| `let total(v: Vector(Int)): Int = ...` | `Undefined type 'Vector'` | `Vector` |
| `let total(v: vector.T): Int = vector.length(v)` | `synthesized type 'vector.T' is not a subtype of expected type 'vector.T(?A)'` | `v` in the body |
| `let v = vector.T(:Int)` | `Module 'vector' has no exported member 'T'` | `vector` |
| `vector(3)` | `Cannot invoke non-function type 'Module 'vector''` | `vector` |
| `if x > 3 then x else 0` without its `end`, in a `begin` block, two functions before the end of the file | `Unexpected token '' (EOF), expected: ASSIGN, AT, BANG, ...` (64 names) | the end of the file |
| `let f(n: Int): Int = (n + 1` without its `)` | `Unexpected token '(' (LPAREN), expected: AT, CHAR_LIT, ...` (37 names) | the `(` |
| a `case` without its `end`, last in the file | `Unexpected token '' (EOF), ...` (65 names) | the end of the file |
| `let f(a: Int, b: Int)` | `Unexpected token ',' (COMMA), expected: COLON, ..., HasKind, HasMutType, ...` | the `,` |

Three causes:

- **`Iter.T` names something.** A type path's first name is looked up among the modules and then the interfaces
  (`elaborate_types.py`, `questlang/typechecker/elaboratetypes`), so `Iter.T` is the interface's own abstract `T`,
  which no value has, and the mistake shows only where a value meets it. No `.quest` file in the tree writes a type
  through an interface's name.
- **A failed lookup says only that it failed.** The checker knows, where it reports `Undefined type 'vector'`, that
  `vector` is a module with a `T`; it does not say so. Every compiler error can carry help, which the renderer prints
  as `= help:` (diagnostics.md §2), but no type or kind error sets it.
- **The parser reports where it stopped, not what was left open.** It reports the farthest token any alternative
  reached (diagnostics.md §4.1), which for a missing `end` is wherever the next construct could no longer be read,
  often the end of the file. And what it lists as expected are the grammar's names: tokens by kind (`KW_END`,
  `RPAREN`) and nonterminals (`PrimaryValue`, `Linkage`, `Phrase`) together.

## 2. Names: Help Where a Lookup Fails

### Step 1. Near misses

A function in each compiler, `nearMiss(env, name, place)`, that a failed lookup calls for its help text. `place`
says what was looked for (a type, a value, a member of a module), and the function looks in the other namespaces for
the same name, or for the name with its first letter's case changed:

| Looked for | Found instead | Help |
| :--- | :--- | :--- |
| type `vector` | a module `vector` with a type `T` | `'vector' is a module; its type is vector.T` (with `(...)` when the use applied it) |
| type `Vector` | an interface `Vector`, implemented by an imported module `vector` | `'Vector' is an interface; the module that implements it is imported as 'vector': its type is vector.T` |
| value `Iter` | an interface `Iter`, implemented by an imported module `iter` | `'Iter' is an interface; the module is imported as 'iter'` |
| value `vector` | nothing, and no import of `vector` | `nothing named 'vector' is imported; collections/vector : collections/Vector imports the collection` (only for the library's own modules, from the library's index) |
| member `T` of module `vector` | a type `T` | `vector.T is a type, not a value` |
| a call of module `vector` | a module | `'vector' is a module; call one of its functions, such as vector.new` (only when the module has a `new`) |

The calls are the places that raise `Undefined type`, `Undefined variable`, `has no exported member`, and `Cannot
invoke non-function type` for a module: in the bootstrap `typechecker/elaborate_types.py` (3), `application.py` (2),
`typecheck.py` (2), `control.py` (1), and `aggregates.py` (1); in the self-hosted compiler the matching places in
`questlang/typechecker/`. The messages stay as they are, so the existing expectations still match; each case in the
table gets an error test that matches its help.

The library index for the missing-import row is the list of `lib/` interfaces, which the loader already searches; if
reading it at that point is awkward in either compiler, that row is left out.

### Step 2. A type through an interface's name, when its module is imported

When a type path's first name is an interface and a module implementing that interface is imported, the path is an
error at the annotation: `'Iter.T' names the interface's type, not the module's`, with the help `write iter.T`. An
interface's name in a path stays legal where no implementing module is in scope. This is the plan's one change to what
programs are accepted; the user decides it (§6). Nothing in the tree is affected (§1).

### Step 3. A type operator without its arguments

Where a value's declared type is an operator that takes arguments (`vector.T`, of kind `ALL(A::TYPE) TYPE`), report
it there: `vector.T takes 1 type argument`, with the help `for example, vector.T(Int)`. Today the declaration is
accepted and the error is a subtype failure at the first use. The check belongs where a parameter's or a binding's
type annotation is elaborated, and asks only whether the elaborated type's kind is an operator kind. If the type
system means an unapplied operator to be a type there, which the bootstrap's acceptance suggests it might
([type-system.md](type-system.md)), this step becomes help on the subtype failure instead: `'vector.T' is missing
its type argument`.

## 3. Syntax: What Was Left Open

Both steps run only after a parse has failed, so they cost nothing for programs that parse and do not change the
grammar or the engine. They live beside the engine (`syntax/parser.py`, `questlang/syntax/parser/engine`), and their
result becomes the error's message or note.

### Step 4. Unclosed constructs

One pass over the tokens with a stack of what is open: the keywords that `end` closes (`begin`, `if`, `case`,
`inspect`, `try`, `while`, `for`, `loop`, `tuple`, `record`, `variant`, `option`, `interface`, `module`, `array of`,
and the rest the grammar has) and the brackets `(`, `[`, `{`. Each entry records the opener's token and the column of
the line it starts. Then:

- **A bracket closed by the wrong bracket, or never closed**, is the error: `'(' at 2:22 is not closed`, located at
  the `(`.
- **An `end` that lines up with an opener other than the innermost** means the innermost is missing its `end`:
  `'if' has no matching 'end'`, located at the `if`, with the note `the 'end' at 5:5 lines up with the 'begin' at
  2:5`. "Lines up" is the column of the line the opener starts, which [formatter.md](formatter.md) makes reliable
  for code that has been formatted; for other code the check is only a guess, and says so by being a note on the
  usual error rather than replacing it (below).
- **A top-level phrase at column 1** (`let`, `import`, `interface`, `module`, `Let`, `Def`) while something is open
  means that thing is missing its `end`: `'begin' at 2:5 has no matching 'end' before the 'let' at 7:1`.
- **An `end` with nothing open** is extra: `'end' at 6:5 closes nothing`.

When the pass finds one of these and it lies at or before the farthest token, it replaces the farthest-token message,
and the farthest token becomes a secondary label (`parsing stopped here`). When the pass finds nothing, the error is
reported as today, with step 5's wording. When the two disagree in a way the pass cannot settle (a construct open,
but no line-up or column-1 evidence), the farthest-token error stays and the open construct is a note: `the 'case' at
3:5 is still open here`.

### Step 5. What was expected, in words

The expected list is printed as source text, without the grammar's internal names:

- tokens as written: `'end'`, `')'`, `'then'`, an identifier, a string;
- nonterminals left out when a token they start with is listed, and otherwise named by a short description kept with
  the nonterminal in the grammar (`a type`, `an expression`, `a binding`);
- the tokens that can start an expression, when all or nearly all of them are expected, collapsed into `an
  expression`;
- the message `expected 'end', ')', or an expression, found 'let'`, located at the found token, with `the end of the
  file` for EOF.

This changes the text of every syntax error, so the parse error tests (14) and any parse goldens with errors are
written again, by the bootstrap. Each grammar's descriptions are data beside its rules, the same in both grammars
(`syntax/grammar.py`, `questlang/syntax/parser/grammar`).

### Step 6. Common slips

A short table, matched against the found token and what was expected, gives a help line for mistakes carried over
from other languages:

| Found | Where | Help |
| :--- | :--- | :--- |
| `,` | between parameters, arguments, or type arguments | `Quest separates parameters and arguments with spaces, not commas` |
| `=` | where `:=` assigns a `var` | `a variable is assigned with ':='` |
| `;` | where the existing semicolon tests report it | the tests in `tests/errors/parse/semicolon_*` say what each one means |
| `)` or `]` | where a different bracket is open | `the '[' at L:C is still open` (from step 4) |

Only slips seen in practice go in the table; each gets an error test.

## 4. Order and Testing

Steps 1 to 3 (names) and 4 to 6 (syntax) are independent; within each part, the order is the one above. Step 5
changes every syntax error's text, so it goes in before step 4's messages are written into tests, or step 4's tests
are written twice.

Each step: both compilers, the new error tests, `run_tests.py` for the error suites in both, and `tools/check` as it
picks suites from the diff. The REPL and the language server print the same diagnostics (repl.md, lsp.md), so their
tests that show an error are run too; the language server sends the help and notes as related information if it
already does so for others, and is otherwise left alone.

## 5. Not in This Plan

- **Reporting several syntax errors.** It needs recovery points in the grammar and the engine, and the unclosed
  constructs of step 4 cover the commonest case.
- **A different parser.** The packrat engine's farthest-token rule is kept; this plan only adds to what it reports.
- **Rendering.** Colors, a wider source excerpt, or underlining the whole span are separate.
- **Rewording other type errors.** The subtype failure's text (`synthesized type ... is not a subtype of expected
  type ...`) is a candidate too, but its wording is tested widely and it is not one of the cases above.

## 6. Decisions for the User

1. **Step 2's rule.** Make `Iter.T` an error when a module implementing `Iter` is imported (the plan), make it an
   error everywhere, or only add help to the subtype failure.
2. **Step 3.** Whether an unapplied operator as a value's declared type should be an error at the annotation (the
   plan) or only get help where it fails.
3. **Step 5's form.** The plan drops the token kinds (`KW_END`) from syntax errors. Keeping them, after the words,
   would help someone reading the grammar, at the cost of length.
