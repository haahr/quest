# quest fmt, the Formatter

`quest fmt` lays Quest source out in one style, as `go fmt` does for Go. A program, module, or interface goes in, and
the same tokens come out in the same order, with:

- their spacing and indentation normalized (§2.1–2.8);
- optional semicolons removed (§2.9);
- imports sorted, in sections (§2.7);
- a `then` or `do` that starts a line moved to the end of the line before, and an infix operator that ends a line
  moved to the start of the next (§2.0);
- a broken construct broken throughout: its `end` on a line of its own, and each field of a tuple or arm of an `if`
  on one too (§2.0);
- a multi-line `if`, `case`, `inspect`, or `try` after `=` or `:=` moved to a line of its own (§2.4);
- lines over 120 columns broken (§3).

Like go fmt, it keeps the programmer's line breaks. It joins lines only to move `then`, `do`, and operators, and to
put back a short value that was alone after an `=` (§2.0). It adds breaks only to a construct already broken and to
lines too long to fit. The tree is formatted, and tools/check fails on a file `quest fmt` would change (§5).

```
quest fmt FILE...            # print each file formatted
quest fmt -w FILE...         # rewrite each file that changes
quest fmt --check FILE...    # name the files that would change; fail if any
quest fmt                    # standard input to standard output
```

A directory stands for the `.quest` files under it. A file that does not parse is reported with the compiler's own
syntax error and left alone.

## 1. Sources of the style

The style comes from three places, in this order:

1. **Cardelli's "Typeful Programming"** (docs/TypefulProg.pdf; docs/TypefulProgramming.md loses the layout), for what it
   settles consistently.
2. **The tree as it was** (981 `.quest` files, 175k lines, measured 2026-11-21) where the paper is silent or
   inconsistent, so that formatting changed as little as it could.
3. **Decisions made for the formatter** where neither settles a matter, each with its example below.

### 1.1. What the paper settles

The paper's own examples are shown as printed, in its 3-space indentation and tight spacing; §1.2 says what the
formatter uses instead. Page numbers are the PDF's.

- **Bracketing constructs** (`begin`, `tuple`, `Tuple`, `Option`, `Record`, `case`, `try`), when broken:
  - the opening keyword ends its line or stands alone;
  - the contents go one indentation deeper;
  - `end` returns to the column of the line that opened the construct.

  ```
  Option
     a
     b with x:Bool end
  end;
  ```

  (p23)
- **A declaration broken after `=`** puts its body on the next line, one level deeper (`let gcd(n,m:Int):Int =` /
  `begin`, p28).
- **`if`:** `then` ends the condition's line; `elsif`, `else`, and `end` line up with the `if` (p17).
- **Loops:** `do` ends the head's line; the body goes one level deeper; `end` lines up with `while` or `for` (p28–29).
- **Interfaces and modules:** `interface`, `import`, `export`, and `end` share a column, and only the items are
  indented (p44).
- **`let ... and`:** `and` lines up with the `let` (p21, p28).
- **Calls:** no space before `(` or inside the parentheses, and arguments are separated by spaces.
- **Long signatures** break between parameters and continue at a fixed indentation, not under the `(` (p63).
- **Semicolons** only end top-level phrases (p13).
- **Alignment:** `:` and `=` are not aligned in columns; end-of-line comments may be (p41).
- **Naming** follows the paper: lowerCamel for values, Capitalized for types, capitals for kinds. The formatter renames
  nothing, so this is not enforced.

### 1.2. Where the paper and the tree disagreed

| Matter | The paper | The tree | quest fmt |
|---|---|---|---|
| Indentation unit | 3 spaces (once 2) | 4 spaces in every directory | 4 |
| `x: T` | `x:T`, with exceptions (`let t: Tuple`, p21) | `x: T`, 18,725 to 0 | `x: T` |
| Infix operators | mostly tight (`x+1`), sometimes spaced (`s1 <> s2`) | spaced | spaced |
| `=`, `:=` | spaced on lines of their own, tight inline | spaced | spaced |
| `::` | tight | tight | tight |
| `<:` | tight (`A<:Object`, p35) | spaced, 29 to 1 | spaced |
| `case` arms | one level under `case` | one level under `case` | one level under `case` |
| `try`'s `when` and `else` | one level under `try` | at the `try` line's column | at the `try` line's column |

## 2. The style

### 2.0. What changes and what is kept

Every line break in the source is kept, with these exceptions:

- **`then` and `do`:** a line that starts with `then` or `do` is joined to the line before it. What followed the
  `then` keeps its own line, as the arm's body.
- **Operators lead:** an infix operator that ends a line moves to the start of the next, and a line holding nothing
  but an operator takes the next line onto it.
- **Values after `=`:** a value alone on the line after an `=` that ends a line goes back onto the `=`'s line if it
  fits there in 120 columns, with no comment in the way. A `begin`, `if`, or other construct of several lines is not
  alone on its line, so it stays.

```
(* source *)                      (* formatted *)
if {x > 0}                        if {x > 0} then
then f(x)                             f(x)
end                               end
let s = a <>                      let s = a
    b                                 <> b
let n =                           let n = 1
    1
```

Breaks are added, never removed, where a construct is already broken (§2.4, §2.6):

- **An end on its own line:** a body's phrase or a tuple's field that starts a line puts the `end` of its construct
  on a line of its own, at the construct's column. So does an `elsif`, `else`, or `when` after the first arm that
  starts a line, when the construct itself starts one (or follows only an operator that does).
- **Broken throughout:** an `if` whose first arm starts on a line of its own has every arm start on one. So does a
  two-arm `if` (no `elsif`) whose `else` body starts a line. An `elsif` or `else` starts a line when its body does,
  and when one `elsif` or `else` of an `if` starts a line, all do, so no arm follows another on a line. A tuple whose
  fields take more than one line has each field on one (§2.6).

```
(* source *)                      (* formatted *)
if c then                         if c then
    valid := false end                valid := false
                                  end
let t = tuple                     let t = tuple
    let a = 1 let b = 2               let a = 1
end                                   let b = 2
                                  end
```

Within that:

- **Spacing** within a line is normalized (§2.1).
- **Indentation** of each line is computed from the program's structure, not copied (§2.2–2.7). Each level is 4
  spaces.
- **Continuations:** a line that continues a phrase begun on an earlier line is a *continuation*, indented 8 past
  that phrase's first line, so it can't be mistaken for a body one level (4) deeper. A continuation that starts with
  an infix operator is indented 4, since the operator already marks it, except in an `if`, `elsif`, or `while`
  condition, where it stays at 8 past the keyword's line so that the line ending in `then` or `do` stands apart from
  the body under it.
- **Brackets:** a continuation inside a bracket that was opened on the phrase's line or after it, on an earlier line
  than this one, is indented from the line where the bracket opened.
- **Nested continuations:** a phrase nested in a continued one (a field of a tuple type inside a field's type)
  continues at its line's indentation, without stepping further right on every line.
- **Long lines:** a line over 120 columns is broken (§3).
- **Blank lines:** runs of them become one (§2.9).

### 2.1. Spacing

```
let f(x: Int s: String): Bool = {{x + 1} > 0} andif {s <> ""}
Def Pair = Fun(A::TYPE B::TYPE) Tuple first: A second: B end
let found = locate(:K :V t key)
r.field := a[i] + 1
module prettyPrint : PrettyPrint
```

- **One space** around every infix operator, word or symbolic (`+`, `<>`, `is`, `andif`), around `=`, `:=`, and `<:`,
  and after a type annotation's `:`.
- **No space:**
  - around `.`, `::`, `?`, and `!`;
  - after `@`;
  - before `(` or `[`, or inside brackets and braces;
  - before a `,`. After a `,` the source's spacing is kept (`fst,snd: A`).
- **Colons:**
  - A colon written against the type after it but not against what precedes it is a type argument (`:K :V`,
    `array of :Int end`), and keeps its spacing.
  - The colons of module and interface headers and of import items keep a space on both sides.
- **The slashes of import paths** take no spaces (`util/stringBuilder`).
- **Tokens that must stay apart:** a space is never removed where the lexer needs one. Two symbolic tokens stay
  apart (`x: -y`, not `x:-y`, which lexes as `:-`), and so does a `(` before a `*`, since `(*` opens a comment.

### 2.2. Declarations

```
let succ(a: Int): Int = a + 1
let gcd(n: Int m: Int): Int =
    begin
        let var vn = n
        vn
    end
let rec even(n: Int): Bool = if n is 0 then true else odd(n - 1) end
and odd(n: Int): Bool = if n is 0 then false else even(n - 1) end
```

- **Body:** the body after an `=` that ends its line is one level deeper than the declaration.
- **`and`:** starts at its `let`'s column. In an interface's type group, it starts at the first `Let`'s.
- **Continued signatures:** a continued signature, in either of the tree's two forms, is a continuation at +8:

  ```
  let lowerModule(environment: Env unit: ast.Module imports: Array(Import) tables: Tables options: Options
          more: Int): ir.Module =
      begin go() end
  ```

### 2.3. Types

```
Let Point = Tuple x: Int y: Int end
Let Rec Doc = Option
    empty
    text with s: String end
    pair with a: Doc
        b: Doc end
end
```

- **Fields and tags:** those of a broken `Tuple`, `Record`, `Variant`, `Option`, or `Auto` type go one level deeper,
  with `end` at the declaration's column. How many go to a line stays as written.
- **A tag's payload** (`with ... end`) continues one level past the tag.

### 2.4. Control

```
if c then
    a
elsif d then
    b
else
    e
end

case x
    when a then 10
    when b then
        f(x)
        20
    else 0
end

try
    g(1)
when e then 2
end

for i = 0 upto n - 1 do total := total + a[i] end
```

- **`if`:** `elsif`, `else`, and `end` go at the `if`'s line's column. When its first arm's body starts a line, each
  arm's does (§2.0); an `if` whose first arm stays on the `if`'s line keeps its arms as written, one to a line.
- **`end`:** a construct (`if`, `case`, `while`, `for`, `begin`, `try`, `tuple`, ...) any of whose bodies or fields
  starts a line ends with `end` on a line of its own. So does an `if`, `case`, `inspect`, or `try` that starts a line
  and has a later `elsif`, `else`, or `when` starting one. A compact `if` in the middle of a line keeps `else z end`.
- **Lifted:** an `if`, `case`, `inspect`, or `try` of several lines after a `let`'s `=` or an assignment's `:=` starts
  a line of its own, one level deeper. An `if` qualifies when its first arm's body starts a line; the others when they
  break anywhere. A compact `if` stays where it is:

  ```
  let kind =
      if x > 0 then
          "positive"
      else
          "other"
      end
  let sign = if x > 0 then 1 else ~1 end
  ```

- **After an operator:** an `if` of several lines that is an infix operator's right operand (other than `:=`'s) starts
  a line with that operator: `<> if c then`. One on a single line stays inline.
- **`case` and `inspect`:** `when` and `else` go one level deeper than the head, and a `when` arm's body on lines of
  its own goes one level further.
- **`try`:** `when` and `else` go at the `try` line's column, as the tree writes them.
- **Loop bodies:** go one level deeper.
- **Continued conditions:** a condition continued onto a later line is a continuation, at +8, below a body at +4,
  even when the line starts with an operator:

  ```
  if {slot >= 0} andif {word.toInt(word.xorBits(t.hashes[slot] h)) is 0}
          andif m.equal(t.keys[slot] key) then
      result := slot
  end
  ```

- **A compact `if`** is one in the middle of a line whose first arm is on that same line (`let a = if c then x`). It
  continues: its `elsif`, `else`, and `end` go one level deeper than its line, and an arm's body on a later line goes
  one level past its `elsif` or `else`. Whether an `if` is compact depends on the output's lines, not the source's:

  ```
  let a = if c then x
      elsif d then y
      else z end
  ```

### 2.5. Expressions

- **Payloads:** the payload after a `raise`'s, an option's, or a variant's `with` on a line of its own is a body, one
  level deeper. A `with let ... end` payload's fields are indented as a tuple's.
- **Operators** lead their lines: a broken chain has each later operand on a line starting with its operator, 4 past
  the chain's first line (§2.0).

  ```
  diagnostics.fail("Case target must have Option or Variant type, got '" <> model.show(targetType)
      <> "'" target.span.startOffset)
  ```

- **Call arguments:** an argument on a later line is a continuation. A `fun`'s or a `begin`'s body hangs from the
  line it starts on, and its `end` can close the call (`end)`).
- **Literals** are copied as written (`0x1F`, `~3`, `1.5e~2`, escapes, strings spanning lines), never re-rendered.
- **Braces:** every brace the source wrote is kept, whether or not the parse needs it.

### 2.6. Aggregates

- **`tuple let ... end`:** a broken one has its fields one level deeper and its `end` at the opening line's column.
  If its fields take more than one line, `tuple` ends its line and each field gets a line of its own (§2.0). The
  `with let ... end` payload of an option, a variant, or a `raise` is laid out the same way.
- **`array of ... end`:** items go one level deeper, as many to a line as written.

### 2.7. Modules, interfaces, imports

```
module m : M
import
    stringOp = string : StringOp
    writer : Writer

    collections/vector : collections/Vector
    util/maybe : util/Maybe

    (* the AST *)
    questlang/syntax/ast : questlang/syntax/AST
    support/bench : support/Bench
export
    let x = 1
end
```

- **Layout:** `module` or `interface`, `import`, `export`, and `end` are at column 0, with the items one level deeper.
  Programs keep the import form they use (tests write `import writer : Writer;` one per line).
- **Sorting:** imports are sorted in three sections:
  1. unqualified names: the units of Typeful Programming's own library, such as `string` and `writer`, and sibling
     modules such as a test's `joiner`;
  2. paths that resolve to a unit in lib/, such as `util/maybe`;
  3. every other path: `questlang/` and a program's own units, such as a benchmark's `support/bench`.

  Within a section, imports go in order of module path, ignoring any alias (`stringOp = string` sorts as `string`).
  A path's section is found as the compiler would find its unit, from the file's directory.
- **Blank lines:** a list written one import to a line has one blank line between two sections and none inside
  one. A list with several imports on a line keeps its line breaks.
- **Comments:** a comment on the lines just before an item, or at the end of its line, moves with it.
- **Programs:** a program's `import` phrase of several items is sorted as a module's list is, and a run of
  consecutive top-level `import ...;` phrases is sorted as one list, each phrase keyed by its least import.
- **Why sorting is safe:** a module's initializer runs those of the modules it imports first (docs/modules.md §7),
  so a dependency always initializes before its dependents, in any order. The order only decides which of two
  independent imports initializes first. That is visible only if both initializers have visible effects, and none in
  the tree do: the formatted tree's tests give the same results.

### 2.8. Comments

- **Text:** every comment is kept with its text unchanged; none is reflowed.
- **Own-line comments:** a comment on lines of its own is indented as the token after it would be, or one level past
  an `end` that follows it. Each of its lines moves by the same number of columns as the first, so a ` * `
  continuation stays under its `*`.
- **End-of-line comments** stay at the end of their lines:
  - they go two spaces past the code;
  - those on consecutive lines are aligned in a column two spaces past the longest code of the run;
  - a blank line, or a line without one, ends the run;
  - a line made too long only by its comment is left long.

  ```
  let y = x           (* why *)
  let longer = y + 1  (* and why *)
  ```

- **Not normalized:** comment forms such as `*)` alone on a line, or continuation lines without stars, stay as
  written. Nothing reports a comment line that reindentation pushes past 80 columns.

### 2.9. Blank lines, semicolons, and trailing spaces

- **Blank lines:** a run of blank lines becomes one. Blank lines at the start or end of a file are removed, and so
  are those after a line that ends with `begin`, `then`, `do`, `else`, `import`, or `export`, or before an `end`.
- **Semicolons** are removed if the program parses to the same AST without any of them, as it does whenever none is
  needed (docs/instructions.md §5). Otherwise the file keeps them all. No file in the tree keeps them: the one test
  that needs its semicolons, language/top_level_semicolons.quest, is left alone by `@no-format` (§2.10).
- **Line ends:** no line ends in spaces, a comment's inner lines included. The inside of a string literal is never
  touched.

### 2.10. Files left as they are

A file holding a comment with `@no-format`, as the tests' `@skip-phase` directives are written, is left exactly as it
is. It is for files whose layout is their point:

- the generated tests, whose generators write the marker, so that regenerating them stays exact;
- language/top_level_semicolons.quest, which tests semicolons;
- benchmarks/mlton/logic.quest, whose continuations nest dozens deep and are written flat.

## 3. Long lines

A line whose code passes 120 columns is broken: a break is added before one token, the new line is indented by the
rules of §2 like any other, and this is repeated until no line can be shortened. The places a break may go are
between tokens. A break never goes:

- before `)`, `]`, `}`, `,`, `.`, `:`, `::`, `=`, `:=`, `(`, `[`, `then`, `do`, `end`, `of`, or `with`;
- after an opening bracket, `.`, `:`, `::`, `@`, `?`, `!`, or an infix operator;
- after a keyword other than `then`, `do`, `else`, `begin`, and `with`;
- inside an import path;
- next to a comment.

The break goes, in this order:

1. **The least nesting:** among the places inside the fewest brackets.
2. **Before a body or a phrase,** the token that starts one with the earliest anchor. So a declaration breaks after
   its `=`, an arm after its `then`, and a tuple between its fields before it breaks inside one. Breaking there also
   breaks before every later token on the line with the same anchor (the other arms of an `if` and its `end`, the other
   fields of a tuple, the other phrases of a block), so the construct is broken throughout.
3. **Otherwise before the last infix operator** that leaves what comes before it within 120 columns. An operator that
   ends the line stays there.
4. **Otherwise at the last place that fits,** or the first if none does.

```
let check(x: Int): Ok =
    if x > 100000 then
        report("the value is far too large to be handled by this function or by any other one that we know of" x)
    else
        ok
    end
```

A line that can't be broken, such as one holding a long string, stays long.

## 4. How it works

The formatter is self-hosted only (questlang/format/). The two-compilers policy (docs/instructions.md) gives a tool
to the self-hosted compiler alone, as it does the REPL and the Jupyter kernel. `quest fmt` is dispatched from
questlang/driver/main.quest before anything else runs, and none of its arguments are parsed as the compiler's
options.

- **The compiler's own front end.** The formatter has no grammar of its own. It tokenizes and parses with
  questlang/syntax, without desugaring.
- **Comments.** The tokenizer records the span of each comment it skips (`tokenizer.comments`). The tokens and the AST
  are unchanged, and so is every dump, so the goldens shared with the bootstrap don't move.
- **Nothing reconstructed from the text.** The formatter prints the source's tokens themselves, so the concrete syntax
  the parser normalizes away (grouping braces, `<:`, `f(x)(y)`, a `then` arm of several phrases) is in the token
  stream, and the parser needs no record of it: no side table of what the parser's actions drop, and no flag
  making the parser keep it.
- **Structure** (questlang/format/structure) walks the AST once and records, by token offset, how a line starting
  with each token is indented:
  - a *rule*: another, earlier token's line plus 0 or 4, or a column at the top level;
  - otherwise a *continuation* of the innermost phrase holding the token.

  It finds a node's tokens from its span. It finds the parts that are not nodes (a field of a type, a branch, an
  `else`, an import item) between the nodes around them. A block of phrases the parser makes for a `then`, `when`, or
  `else` has the span of the construct around it, so its own extent is taken from its first and last phrases. The
  same walk records the colons that keep their spaces, the slashes of import paths, the sortable import lists, the
  `end` that closes each body's or field's construct, the parts (a tuple's fields, an `if`'s arms, its `elsif`s and
  `else`) that start lines together, the constructs to lift (§2.4), the values after `=` that may join their line,
  and the tokens of each condition.
- **Format** (questlang/format/format) makes one sequence of tokens and comments, each with the line breaks before
  it. It then sorts the imports, removes the semicolons, moves each `then` and `do`, moves operators to lead their
  lines, adds the breaks of §2.0 and §2.4 (until none is asked for, since one break can call for another, and again
  after each round of breaking long lines), breaks the long lines, joins values back after `=`, cuts the sequence
  into lines, indents and spaces them, and aligns end-of-line comments.
- **Checked before it is returned.** The output must tokenize to exactly the tokens intended, have the same number of
  comments, and parse. If it doesn't, `quest fmt` reports an internal error and leaves the file alone. Semicolons are
  removed only if the program without them parses to the same AST dump.

## 5. Tests and enforcement

- **tests/source/questlang/format_cases.quest** formats one case for each rule above and then formats each result
  again, which must change nothing.
- **The tree is formatted.** tools/check runs `quest fmt --check` over questlang/, lib/, tests/source/, and
  benchmarks/. A file the formatter would change fails the check, so formatting must also be idempotent over the
  whole tree. A file that does not parse fails too.
- **Generated tests** carry `@no-format` (§2.10) and are left as their generators write them.

## 6. Out of scope

- Renaming, reordering declarations, or rewriting sugar (`let f = fun ...` stays as written). Imports are the only
  thing reordered.
- Joining lines (except as §2.0 says), and reflowing comments.
- UTF-8: widths count bytes, as in util/prettyPrint. The long-line breaker doesn't use util/prettyPrint: a break added
  to the token sequence and indented by the rules does what a document would, and keeps one source of truth for
  indentation.
