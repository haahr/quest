# A Formatter for Quest: Design

`quest fmt` lays Quest source out in one canonical style, as `go fmt` does for Go: a program, module, or interface
goes in, and the same phrases come out with only their spacing and indentation changed, optional semicolons removed,
imports sorted, and lines over 120 columns broken. Like go fmt, it keeps the programmer's line breaks: it joins
lines only to put `then` and `do` back at the end of their heads, and splits only lines too long to fit. The
breaking of long lines uses util/prettyPrint (docs/libraries.md §1.22).

Status: a draft for discussion, 2026-11-21. §8 lists the decisions made and the questions still open.

## 1. Sources of the style

The style comes from three places, in this order:

1. **Cardelli's "Typeful Programming"** (docs/TypefulProg.pdf; docs/TypefulProgramming.md loses its layout), for
   everything it settles consistently: where `end`, `then`, `do`, `elsif`, and `when` go, how bracketing constructs
   nest, semicolons, and the shape of interfaces.
2. **The tree as it is**, measured over its 981 `.quest` files (175k lines), wherever the paper is silent or
   inconsistent, so that formatting the tree changes as little as it can.
3. **Decisions made here**, written down with examples, where neither settles a matter.

### 1.1. What the paper settles

Each rule with the paper's own example (page numbers are the PDF's; the paper's own spacing and 3-space indentation
are shown as printed, and §1.2 says what the formatter uses instead):

- **Bracketing constructs** (`begin`, `tuple`, `Tuple`, `Option`, `Record`, `case`, `try`): when broken, the opening
  keyword ends its line (or stands alone), the contents go one indentation deeper, and `end` returns to the column of
  the line that opened it (p23):

  ```
  Option
     a
     b with x:Bool end
  end;
  ```

- **A declaration that breaks after `=`** puts its body on the next line, one level deeper (`let gcd(n,m:Int):Int =` /
  `begin`, p28).
- **`if`:** `then` ends the condition's line; `elsif`, `else`, and `end` align with `if` (p17).
- **`case`, `try`, `inspect`:** `when` and `else` one level under the head, `end` back at the head's column (p23–24).
- **Loops:** `do` ends the head's line; the body one level deeper; `end` aligned with `while` or `for` (p28–29).
- **Interfaces and modules:** `interface`, `import`, `export`, and `end` share a column; only the items are indented
  (p44).
- **`let ... and`:** `and` aligns with `let` (p21, p28).
- **Calls:** no space before `(` or inside it; arguments separated by spaces.
- **Long signatures** break between parameters, continuing at a fixed indent, not under the `(` (p63):

  ```
  setSub(dest:String destStart:Int
     source:String sourceStart,sourceSize:Int):Ok
  ```

- **Semicolons** only end top-level phrases (p13).
- **No column alignment** of `:` or `=`; end-of-line comments may be aligned in a column (p41).
- **Naming** (lowerCamel values, Capitalized types, CAPS kinds) is the paper's; a formatter does not rename, so this
  is noted, not enforced.

### 1.2. Where the paper and the tree disagree

| Matter | The paper | The tree | Decided |
|---|---|---|---|
| Indentation unit | 3 spaces (once 2) | 4 spaces in every directory, no tabs | **4** |
| `x: T` | `x:T`, with exceptions (`let t: Tuple ...`, p21) | `x: T`, 18,725 to 0 | **`x: T`** |
| Infix operators | mostly tight (`x+1`), sometimes spaced (`s1 <> s2`) | spaced, all but real literals | **spaced** |
| `=`, `:=` | spaced on their own lines, tight inline (`tuple let x=3 end`) | always spaced | **spaced** |
| `A::TYPE`, `A<:B` | tight | tight | tight |
| Doc comments | after the item, indented | before the declaration, ` * ` continuations | as written (§3.8) |
| Two-space separators | p13, p42 | none | none |

## 2. What it is

- **`quest fmt FILE...`** prints the formatted text of each file. `-w` rewrites the files in place; `--check` prints
  nothing and fails, naming the files, if any would change (for tools/check). With no files it reads standard input.
- **Self-hosted only**, in `questlang/format/`, dispatched early in `questlang/driver/main.quest` as `compile` is
  (options.mod.quest:100). docs/instructions.md (the two-compilers policy) puts new tools in the self-hosted compiler
  alone, as the REPL and kernel are; the bootstrap and the shared goldens are untouched.
- **The compiler's own grammar and parser.** The formatter has none of its own: it runs the self-hosted tokenizer
  and parser (`questlang/syntax/`), stopping before desugaring, and lays out the AST they build.
- **What the AST drops is recorded, not reconstructed.** The tokenizer records the comments and line breaks it skips,
  and the parser's actions record the concrete syntax they normalize away (grouping braces, semicolons, curried
  groups, `<:`, `then` bodies), each in a side table (§5). The tokens, the AST, and every dump stay exactly as they
  are, so the parse and tokenize goldens shared with the bootstrap don't move, and the bootstrap needs nothing new.
  The tables are self-hosted output that only the formatter reads, which the two-compilers policy allows for a tool.
- **Safe by construction:** the output is parsed again and its AST dump (astprint, without offsets) must equal the
  input's; if not, the file is left alone and the formatter reports an internal error. Formatting is idempotent:
  formatting the output again changes nothing. Both are checked on every file in the tree by a test.
- **Width 120** for code (docs/instructions.md §4). Comments are not rewrapped (§3.8).

## 3. The style

### 3.0. What changes and what is kept

Every line break in the source is kept, with one exception: a line that starts with `then` or `do` is joined to the
line before it, since the paper always ends a head's line with them (106 such lines in benchmarks, 11 in questlang).
Within that:

- **Spacing within a line** is normalized (§3.1).
- **Indentation of each line** is computed from the structure, not copied (§3.2–3.7): a line that starts a phrase is
  indented by its nesting depth, 4 spaces a level; a line that continues a phrase begun on an earlier line is a
  *continuation*, indented **+8** from the phrase's first line, so that it can't be mistaken for a body one level
  (+4) deeper.
- **A line over 120 columns is broken** by the rules for its construct, below, with util/prettyPrint choosing where:
  only that line is broken, and the breaks it adds follow the same indentation rules.
- **Blank lines** are kept, runs of them reduced to one (§3.9).

So `let f(x: Int): Int = if x > 0 then` / `  x else 0 end` keeps its two lines and is reindented, and a leading
`then` is pulled back:

```
let f(x: Int): Int = if x > 0 then
    x else 0 end

(* source *)                      (* output *)
if {x > 0}                        if {x > 0} then
then f(x)                             f(x)
end                               end
```

In the second, the `f(x)` left behind by the moved `then` keeps its own line, one level deeper, as the arm's body.

### 3.1. Spacing

```
let f(x: Int s: String): Bool = {{x + 1} > 0} andif {s <> ""}
Def Pair = Fun(A::TYPE B::TYPE) Tuple first: A second: B end
fun(x: Int): Int x + 1
r.field := a[i] + 1
array of(n 0)
```

- One space around every infix operator, word or symbolic (`+`, `<>`, `is`, `andif`), around `=` and `:=`, and after
  `:` (none before). None around `::`, `<:`, or `.`; none before `(`, after `(`, or before `)`; none inside `{ }`.
- One space between arguments, parameters, fields, and import items; commas in identifier lists without a space
  (`fst,snd: A`), as written in the source.
- The ` : ` of module headers and imports keeps its spaces (`module prettyPrint : PrettyPrint`,
  `sb = util/stringBuilder : util/StringBuilder`).
- **Never** a space removed where the lexer needs one: two symbolic tokens stay apart (`x: -y`, not `x:-y`, which lexes
  `:-`); `(` before `*` keeps a space (`(*` opens a comment).

### 3.2. Declarations

```
let x = 1
let succ(a: Int): Int = a + 1
let gcd(n: Int m: Int): Int =
    begin
        let var vn = n
        ...
    end
let rec even(n: Int): Bool = if n is 0 then true else odd(n - 1) end
and odd(n: Int): Bool = if n is 0 then false else even(n - 1) end
```

- A body after a line-ending `=` is one level deeper than the declaration (3,171 of 3,171 such bodies in questlang).
- `and` starts at its `let`'s column.
- **A declaration over 120 columns** breaks after `=` first, its body on the next line one level deeper; if the
  signature alone is too long, it fills its parameters, continuing at **+8** so the continuation can't be mistaken
  for the body at +4:

  ```
  let lowerModule(env: Env module: ast.Module imports: Array(Import) tables: Tables
          options: Options): ir.Module =
      begin
  ```

  A signature the source already breaks is reindented to the same +8, whichever of the tree's two forms it uses
  (wrapped, about 46 in questlang, or one parameter per line after a line-ending `(`, about 32).

### 3.3. Types

```
Let Point = Tuple x: Int y: Int end
Let Options = Tuple
    width: Int
    initialIndent: String
end
Let Rec Doc = Option
    dEmpty
    dText with s: String end
end
```

- Fields and tags of a broken `Tuple`, `Record`, `Option`, or `Variant` type go one level deeper, `end` at the
  declaration's column. How many to a line stays as written (the tree has both one tag per line and several).
- A type over 120 columns breaks one field or tag per line.

### 3.4. Control

```
if c then a else b end

if c then
    a
elsif d then
    b
else
    e
end

if maybe.isNone(found)
        andif stringOp.equal(name "x") then
    report()
end

case d
    when dEmpty then 0
    when dText with t then
        let n = stringOp.length(t.s)
        n + 1
    else 1
end

for i = 0 upto n - 1 do total := total + a[i] end
```

- `elsif`, `else`, and `end` at the `if`'s column; `when` and a `case`'s `else` one level deeper than `case`; a
  `when` arm's broken body two levels deeper; loop bodies one level deeper, `end` at the loop's column.
- A condition continued on a later line is a continuation, at +8 (above, the body is at +4).
- **An `if` over 120 columns** breaks every arm: `then` ends the condition's line and each arm's body goes on its own
  line. A long `case` breaks each `when` onto its own line.

### 3.5. Expressions

- **A long infix chain breaks before the operator**, as a continuation, as many operands per line as fit (the tree:
  679 lines start with an operator, 240 end with one):

  ```
  let message = "module '" <> name <> "' imports '" <> other <> "', which is not compiled"
          <> conv.int(count) <> " times"
  ```

  A source line that ends with an operator keeps its break there.
- **A long call** fills its arguments as a continuation; a last argument that is a bracketing construct (`fun`,
  `begin`, `tuple`) hangs instead, its `end` closing the call:

  ```
  vector.sort(entries fun(a: Entry b: Entry): Bool
      begin
          ...
      end)
  ```

- **Literals** are copied as written (`0x1F`, `~3`, `1.5e~2`, escapes), never re-rendered. A string literal too long
  for the line stays whole, and the line runs long.

### 3.6. Aggregates

- `tuple let ... end`: a broken one has a `let` per line one level deeper, `end` at the opening line's column; one
  over 120 breaks that way.
- `array of ... end`: items one level deeper, as many to a line as written; one over 120 is filled.

### 3.7. Modules, interfaces, imports

```
module prettyPrint : PrettyPrint
import
    collections/vector : collections/Vector
    sb = util/stringBuilder : util/StringBuilder
export
    let error: Exception = exception error: Ok end
    ...
end
```

- `module`/`interface`, `import`, `export`, and `end` at column 0; items one level deeper.
- Programs keep whichever import form they use (tests write `import writer : Writer;` one per line, 840 times).
- **Imports are sorted**, in three groups: paths under `questlang/` (the compiler's own modules); then other
  qualified paths (`collections/hashMap`, `util/maybe`); then unqualified names (built-ins such as `string` and
  `writer`, and sibling modules such as a test's `joiner`). Within a group, items are in order of module path, an
  alias not counting (`stringOp = string` sorts as `string`); items with equal paths keep their order. The groups
  are not separated by blank lines.

  ```
  import
      questlang/common/diagnostics : questlang/common/Diagnostics
      questlang/syntax/desugar : questlang/syntax/Desugar
      questlang/types/env : questlang/types/Env
      collections/hashMap : collections/HashMap
      util/hash : util/Hash
      util/maybe : util/Maybe
      stringOp = string : StringOp
  ```

  This follows the tree's loose habit (questlang/ first, then lib, then built-ins), which only 49 of its 344 import
  blocks follow exactly. A program's run of consecutive `import ...;` phrases is sorted the same way, as one list; a
  declaration or comment line between them ends the run. A comment on an item's own line, or on the lines just
  before it, moves with the item.
- **Why sorting is safe.** Each module's initializer first runs the initializers of the modules it imports
  (docs/modules.md §7, item 5), so a dependency always initializes before its dependents, in any order of the list.
  The order only decides which of two *independent* imports initializes first, which a program can see only if both
  initializers have visible effects (output, a shared mutable value). Whether any module in the tree does is checked
  once, when the tree is formatted: every test's output must be unchanged. Names are unaffected: an import list
  binds distinct names, none of which another item's interface refers to.

### 3.8. Comments

- Every comment is kept, with its text unchanged; none is reflowed (as go fmt reflows none).
- A comment on lines of its own is reindented with the code it precedes: each of its lines moves by the same number
  of columns as the first, so a ` * ` continuation stays under its `*`. One whose lines would pass 80 columns after
  reindenting is reported as a warning, not rewrapped.
- An end-of-line comment stays at the end of its line, separated from the code by two spaces (the tree: 98 two-plus,
  10 one, in questlang); end-of-line comments on consecutive lines are aligned in a column, as the paper (p41) and
  syntax/parser/actions.int.quest do: a run's comments start two spaces past the longest code line in the run. A
  blank line or a line without a trailing comment ends a run. A line made too long by its comment is left long.
- Comment forms are not normalized: `*)` alone on a line (35 in lib) and star-less continuations (427 in tests) stay.

### 3.9. Blank lines, semicolons, braces

- **Blank lines:** each run becomes one; blank lines at the start or end of a file or body, after `begin`, or before
  `end` are removed. A file ends in one newline and no line in trailing spaces.
- **Semicolons:** removed wherever the parse doesn't need them, as docs/instructions.md §5 asks (tests write them
  in 661 of 957 files today). One is kept only where the next phrase could otherwise continue this one, which the
  formatter tells by parsing; the AST check (§2) guards it. A `;` alone on a line, if kept, joins the phrase it
  ends.
- **Braces:** every brace the source wrote is kept, whether or not the parse needs it (`if {c} then`, the paper's
  `{n isnot 0}`).

## 4. Line breaking

Decided: **go fmt's rule.** The source's line breaks are kept and only lines over 120 are broken. Rejected:

- *Width-driven with a few kept choices*: each construct on one line when it fits, otherwise broken; it would have
  unified the tree's styles (two signature forms, packed and unpacked option types) at the cost of a large first
  diff and of the programmer's choices.
- *Pure reflow* (Prettier, Black, ocamlformat): output depending only on the AST and the width.

Consequences: the formatter never makes a line longer than it was, except by reindenting; two layouts of one program
may stay different; and the rules of §3 for long lines only apply to the 711 questlang lines (and 321 elsewhere) over
120 columns today, and to new ones.

## 5. Implementation sketch

### 5.1. What the front end records

Two side tables, beside the token vector and the AST, which neither changes:

- **Trivia, from the tokenizer.** `skipWhitespaceAndComments` (questlang/syntax/tokenizer.mod.quest) already finds
  each comment, with its nesting, and each newline; it records them instead of only skipping them. Indexed by the
  token that follows: the span of each comment before it (and whether the comment began its own line), and the
  number of newlines before it. An end-of-line comment is one whose line holds the previous token. Roughly 20–30
  lines; `Token`, `tokens.make`, the tokenize dump, and its golden format are untouched.
- **Syntax facts, from the parser's actions.** Each action that drops concrete syntax records what it dropped, keyed
  by offset, in the one place the parser decides it:

  | Action (questlang/syntax/parser/) | What it records |
  |---|---|
  | `first` for `{ e }` (actions.mod.quest, grammar.mod.quest's brace rules) | the brace span around the node |
  | the top-level phrase rule | each `;` it skips |
  | signature and `fun` actions that curry `f(x)(y)` | where each parameter group starts and ends |
  | the bound action that stores `X <: B` as `X::POWER(B)` | that it was written `<:` |
  | `body`, which wraps a `then a b` body in a block | that the block is synthesized |
  | the option-payload action that unwraps a lone `with tuple ... end` | that it was unwrapped |

  Each is a line or two. Every recording site is marked by the one name that enables it (`keepSyntax` below), so a
  grep for it shows everything the formatter relies on.

**Always on, or behind a flag.** If the two tables cost little on a full build of the compiler, they are always kept,
and there is no flag and no second mode. Otherwise one option, `keepSyntax`, threaded through the tokenizer's and
parser's entry points, enables them, and each recording site tests it; with it off the cost is one boolean test per
site and no allocation. Step 1 measures this (the driver build's time and peak memory, with and without the tables)
and decides.

**Keeping them complete.** A grammar change that drops new concrete syntax must record it too. The round-trip test
(§6) catches a missed recording: the output's AST would differ from the input's, or formatting would not be
idempotent, on whichever file in the tree uses the construct.

### 5.2. Steps

1. **Record**: add the two tables (§5.1); measure them always on; decide on the flag.
2. **Tokenize and parse** with the tables kept, without desugaring.
3. **Lay out lines**: walk the AST with the tables, giving each source line its indentation from the node that starts
   it (a phrase at its depth, a continuation at +8 from its phrase), respacing its tokens (§3.1), placing comments
   (those before a node's first token lead it; one on the line of its last token trails it; any other inside its span
   goes before its closing `end`), and writing braces and semicolons from the syntax facts.
4. **Break long lines**: a line over 120 becomes a `pp.T` built from the nodes on it, with groups per §3, rendered at
   the room left after its indentation.
5. **Verify**: parse the output; compare astprint dumps without offsets, after sorting the input's import lists the
   same way; then format the output again and compare.

## 6. Tests

- Goldens: `tests/source/format/*.quest` input and expected output, one per construct and per comment placement.
- Idempotence and AST equality over every `.quest` file in the tree, run by tools/check for questlang/ changes.
- Adoption: one commit formats every `.quest` file (questlang/, lib/, tests/source/, benchmarks/, examples/),
  regenerating the goldens whose positions move (tokenize, parse, and the error goldens' line:column); from then on
  tools/check runs `quest fmt --check` over all of them.

## 7. Out of scope

- Renaming, reordering declarations, or rewriting sugar (`let f = fun...` stays as written). Imports are the one
  thing reordered (§3.7).
- Joining lines (but `then` and `do`), reflowing comments.
- UTF-8: widths count bytes, as in util/prettyPrint.

## 8. Decisions and questions

Decided 2026-11-21:

1. **Line breaking:** go fmt's: keep every break, break only lines over 120 (§4).
2. **Indentation:** 4 spaces, as the tree.
3. **Spacing:** as the tree: `x: Int`, `x + 1`, `a := b`; `::`, `<:`, `.` tight.
4. **Long signatures:** filled, continuing at +8 (§3.2).
5. **Continuations:** +8 everywhere (§3.0).
6. **Semicolons:** removed where optional (§3.9).
7. **Adoption:** format the whole tree in one commit, then enforce `quest fmt --check` in tools/check.
8. **`then` and `do`** at a line's start are joined to the line before (§3.0).
9. **End-of-line comments:** runs on consecutive lines aligned in a column (§3.8).
10. **Scope:** everything: questlang/, lib/, tests/source/, benchmarks/, with goldens regenerated (§6).
11. **Imports are sorted**: questlang/, then other qualified paths, then unqualified names, each by path (§3.7).

No question is open. Still to settle while building: whether the tables are always on or behind `keepSyntax` (§5.1),
and how a long line that holds several phrases (a one-line `if ... then ... else ... end` inside a call) chooses its
first break.
