# Quest Syntactic Front-End: Lexer, Parser, and AST Architecture

This document specifies the lexical syntax, parsing mechanics, and abstract syntax tree (AST) data structures for the
Quest compiler.

---

## 1. Overview of the Syntactic Front-End

The front-end pipeline translates Quest source text, which is ASCII (§2.3), into an immutable Abstract Syntax Tree:

```
  Source Text
       │
       ▼
 [ Tokenizer ]    Lexical scanning with 0-indexed character offsets
       │          Emits stream of Token objects
       ▼
 [ PEG Parser ]   Recursive descent / PEG grammar rules (quest/syntax/grammar.py)
       │          Uniform right-associativity, phrase separation
       ▼
  [ AST Tree ]    Immutable dataclasses (quest/syntax/ast.py)
       │          Emits canonical 2-space indented S-expressions (ast_dump)
       ▼
 [ Desugarer ]    Rewrites syntactic sugar into core forms (quest/syntax/desugar.py, §5)
       │
       ▼
  [ Core AST ]    The same dataclasses, without the sugar; the type checker's input
```

The formal EBNF grammar specification is preserved in [grammar.txt](grammar.txt).

---

## 2. Lexical Architecture (`quest/syntax/tokens.py` and `quest/syntax/tokenizer.py`)

### 2.1. Coordinate Tracking via Character Offsets
Rather than eagerly tracking lines and columns during scanning, every `Token` and `ASTNode` records only a 0-indexed
integer `offset` representing its absolute character offset from the beginning of the file.

When human-readable error messages are needed, `SourceMap.locate(offset)` maps offsets to 1-indexed `(line, column)`
coordinates on demand:
- **`Token(kind, lexeme, offset, value)`**: Immutable token representation.
- **`SourceMap(source_text, file_name)`**: Precomputes line boundary offsets for $O(\log N)$ binary-search coordinate
  resolution.

### 2.2. Identifiers and Keyword Rules
1. **Alphanumeric Identifiers (`IDENT`):**
   - Start with a letter, followed only by letters and digits: `[A-Za-z][A-Za-z0-9]*`.
   - Underscores are NOT part of alphanumeric identifiers. The underscore `_` is a reserved punctuation symbol.
   - Idiomatic Quest style uses camelCase (e.g. `x`, `point2D`, `addFive`, `List`), never snake_case.
   - Case-sensitive: `val`, `Val`, and `VAL` are distinct identifiers.
2. **Keywords:**
   - Reserved keywords must be written in exact casing:
      - Level 0/Value/Phrase keywords are lowercase: `let`, `var`, `out`, `fun`, `if`, `then`, `else`, `try`,
        `raise`, `not`, `extent`, `ordinal`, `of`, `for`, `while`, `loop`, `exit`, `case`, `inspect`,
        `auto`, `interface`, `module`, `import`, `export`, `unsound`, `external`.
     - Level 1/2 capital keywords are capitalized: `Let`, `Rec`, `All`, `Tuple`, `Record`, `Option`, `Variant`,
       `Auto`, `Array`, `Var`, `Out`, `TYPE`, `POWER`, `DEF`, `ALL`.
     - Note the distinction between parameter mode `out` (lowercase) and type operator `Out` (capitalized).
3. **Symbolic Identifiers & Operators (`SYMBOLIC_INFIX`):**
   - Composed of characters from `!@#$%&*_+=-|\`:<>/?^~`.
   - Reserved symbolic punctuation includes `:=`, `::`, `<:`, `=`, `:`, `?`, `!`, `@`, `_`.
   - All non-reserved symbolic character sequences are scanned as `SYMBOLIC_INFIX` tokens (e.g. `+`, `*`, `->`, `==`).
4. **Braced Operators:**
   - Stand-alone operator values must be enclosed in braces: `{+}`, `{-}`, `{++}`, `{#}`.
   - Operators can be applied in prefix notation with argument tuples: `+(1 2)`.

### 2.3. Literals and Escape Sequences
- **Integers (`INT_LIT`):** Decimal sequences (`0`, `42`, `1000`). Negative integers are prefixed with a tilde `~`
  (e.g. `~1`, `~42`).
- **Reals (`REAL_LIT`):** Decimal floats with fractional and/or exponential parts (`3.14`, `2.0e-5`, `1.0E+3`).
  Negative reals are prefixed with a tilde `~` (e.g. `~3.14`, `~2.0e-5`).
- **Strings (`STRING_LIT`):** Delimited by double quotes `"..."`. Supports escapes `\n`, `\t`, `\"`, `\\`, and
  embedded character codes, hexadecimal `\xH` or `\xHH` and decimal `\d`, `\dd`, or `\ddd`.
- **Characters (`CHAR_LIT`):** Delimited by single quotes `'a'`, with the same escapes.
- **Characters are ASCII**, as in Typeful Programming: a character's code is 0 to 127. A source file must be ASCII,
  comments included (`Non-ASCII character`, without its code, which the self-hosted compiler's reader cannot see), and
  an escape giving a code above 127 is an error (`Character code 128 out of ASCII range`). The library keeps to ASCII
  too: `ascii.char` of a code above 127, a reader reading a byte above 127, `dynamic.intern` of a string that is not
  ASCII, and a `system` string from the OS (an argument, an environment variable, a directory or file name) that is
  not ASCII raise the module's `error`.

### 2.4. Nested Block Comments
Quest comments nest to arbitrary depth using `(*` and `*)`:
```quest
(* Outer comment
   (* Nested comment *)
   still inside outer comment *)
```
Unclosed block comments at EOF trigger an `Unclosed comment` diagnostic.

---

## 3. Parsing Mechanics (`quest/syntax/grammar.py` and `quest/syntax/parser.py`)

### 3.1. Parsing Expression Grammar (PEG) Framework
The parser is constructed using composable PEG combinators defined in `bootstrap/python/quest/syntax/parser.py`:
- `SyntaxTarget(name)`: A non-terminal. Its rules are tried in order (ordered choice); each rule is a sequence of
  constructs plus a semantic action called with the sequence's results. Results are memoized per position (packrat).
- `MatchToken(kind, lexeme=None, silent=False)`: Matches a single token kind (and optionally an exact lexeme).
- `Sequence(items)`: Matches items in order, rolling back on failure.
- `Optional(*items)`: Matches 0 or 1 occurrences, yielding `None` when absent.
- `Repeated(*items)`: Matches 0 or more occurrences, yielding a tuple.
- `SepBy(item, separator)`: Matches one or more items separated by a separator, yielding a tuple of the items.

A construct marked **silent** (punctuation and keywords whose token the action does not need, written `P(kind)` in
`grammar.py`) must still match, but its result is left out of the action's arguments and of any enclosing sequence's
result. A sequence with exactly one non-silent item yields that item itself rather than a 1-tuple, so a
keyword-introduced optional clause such as `Optional(P(KW_WITH), VALUE)` yields the value or `None`.

### 3.2. Uniform Right-Associativity & Non-Overloaded Operators
In Quest, all infix operators share uniform precedence and are strictly **right-associative**:
```quest
a + b * c    ==>   a + (b * c)
2 * x + y    ==>   2 * (x + y)
```
To enforce explicit order of operations, sub-expressions must be grouped with parentheses: `(2 * x) + y`.

Quest does not overload operators across types; distinct operators exist for different types (Cardelli §4.2):
- **Integer arithmetic:** `+`, `-`, `*`, `/`, `%` / `mod`
- **Integer relations:** `<`, `<=`, `>`, `>=`
- **Real arithmetic:** `++`, `--`, `**`, `//`, `^^`
- **Real relations:** `<<`, `<<=`, `>>`, `>>=`
- **String concatenation:** `<>`
- **Boolean logic:** `/\` (and), `\/` (or)
- **Identity / Equality:** `is`, `isnot`

### 3.3. Monadic Operators
The monadic operators `not`, `extent`, and `ordinal` are keyword operators that bind tighter than dyadic infix
operators:
- `not b`: Boolean negation.
- `extent a`: Array length (number of elements).
- `ordinal opt`: Zero-based tag index of an option value.

### 3.4. Actual Parameter Bindings & Call Syntax
Function applications evaluate space-separated phrases inside argument lists `f(...)`:
- **Value arguments:** `f(x)`
- **Explicit type arguments:** `f(:Int x)` or `id(:Int)(42)`
- **Out reference coercion (`@`):** `@x` or `@r.field` passes the underlying mutable location.
- **On-the-fly out allocation (`var`):** `var(0)` creates a mutable cell on the fly.

### 3.5. Listfix Postfix Syntax
Quest supports listfix syntax for functions consuming array arguments:
- `f of a1 ... an end` desugars to `f(array a1 ... an end)`
- `f of(count init)` desugars to `f(array of(count init))`
- Explicit element type: `array of :Int 1 2 3 end` records the target element type.
- List aggregates similarly use listfix syntax with the `list` constructor (`list of 1 2 3 end`, `list of end`).

### 3.6. Curried Signatures & Anonymous Tuple Fields
- **Curried Signatures:** Functions and function-valued formals support multiple parameter lists:
  `fun(x: Int)(y: Int): Int x + y` and `f(x: Int)(y: Int): Int`, whose type is
  `All(x: Int) All(y: Int) Int`. (`Fun(...)` is only for type operators, whose parameters are
  type formals such as `A::TYPE` or `A <: B`.)
- **Anonymous Fields:** Tuple types and signatures allow anonymous fields:
  `Tuple :Int :Real end` or `Tuple x:Int :Var(Real) :Out(String) end`.

### 3.7. Option Construction and Extraction Syntax
Option types support both tag-based and ordinal-based operations (Cardelli §4.5):
- **Tag Construction:** `option tag of Type [with Binding] end`
- **Ordinal Construction:** `option ordinal(expr) of Type [with Binding] end`
  Allowed when all branches of the target option type share the same signature.
- **Tag Testing:** `opt?tag` returns `true` if `opt` carries tag `tag`, `false` otherwise.
- **Payload Extraction:** `opt!tag` extracts the payload as a tuple whose first component is the 0-based integer
  ordinal of the option (e.g. `tuple 1 let x=true end : Tuple :Int x:Bool end`).

### 3.8. External Types and Value Bindings
This implementation of Quest provides `external` syntax for declaring opaque native C data structures and native C
symbols:
- **External Types (`PRIMARY_TYPE`):** `type T = external "C_TYPE"` or `Let T = external "C_TYPE"`.
  Binds `T` to an opaque C data type (e.g. `external "QWriter *"`).
- **External Values (`PRIMARY_VALUE`):** `let x: Type = external "C_SYMBOL"`.
  Binds `x` to a C runtime symbol or constant (e.g. `let stdout: Handle = external "quest_writer_output"`).

### 3.9. Auto Values and Inspect
Auto types and values follow Cardelli's grammar (*Typeful Programming* §4.6, §6.7, and the value grammar in its
appendix):
- **Auto Type (`PRIMARY_TYPE`):** `Auto A HasKind with Signature end`, e.g. `Auto A::TYPE with fst,snd:A end` or
  `Auto A<:Object with a:A end`.
- **Auto Value (`PRIMARY_VALUE`):** `auto [let A [HasKind] =] :Type with Binding end`, e.g.
  `auto :Bool with false true end`. The type after the colon is the value's type component; the binding supplies
  its components, positionally or by name, like a tuple's. The optional `let A [HasKind] =` names the type component
  inside the binding (`auto let T = :String with let x:T = "hi" end`) and may restate a kind it must have.
- **Inspect (`PRIMARY_VALUE`):** `inspect Value {when Type [with IdeList [:Type]] then Binding} [else Binding] end`
  discriminates on the type component of an auto value (or on the type in a `Dynamic`). The identifiers after
  `with` are bound to the components; an optional `:Type` gives them a supertype.

See [type-system.md](type-system.md) §6.11 for the typing rules.

### 3.10. Initial/Final Keyword Block Disambiguation
Complex expressions (conditionals, loops, records, tuples, options) employ explicit terminating keywords:
- `if ... then ... else ... end`
- `while ... do ... end`
- `try ... when ... else ... end`
- `record ... end`, `tuple ... end`, `option ... end`

This eliminates dangling-else ambiguities and allows whitespace to be freely used for aesthetic formatting.

---

## 4. Abstract Syntax Tree (AST) Hierarchy (`quest/syntax/ast.py`)

All AST nodes are defined using Python immutable frozen dataclasses (`@dataclass(frozen=True)`), deriving from the base
class `ASTNode(offset: int)`:

```
ASTNode
  ├── Phrase                  (Top-level statements & declarations)
  │     ├── LetValueBinding   (let [var] [rec] x [: T] = e)
  │     ├── LetValueBindingGroup (let [rec] x = e and y = e' ...: two or more LetValueBindings sharing rec,
  │     │                      declared simultaneously; with rec, mutually recursive)
  │     ├── TypeBinding       (Let [Rec] T [:: K] = Type, or Def [Rec] ... with is_def)
  │     ├── TypeBindingGroup  (Let [Rec] T = Type and U = Type ...: two or more TypeBindings sharing Rec and Def,
  │     │                      declared simultaneously; with Rec, mutually recursive)
  │     ├── DefKindBinding    (DEF K = Kind)
  │     ├── InterfaceDecl     (interface I [import ...] export ... end)
  │     ├── ModuleDecl        (module M : I [import ...] export ... end)
  │     ├── ImportDecl        (import M1, M2 : I)
  │     └── TopExpr           (Expression evaluated at top level)
  ├── Expr                    (Level 0 term expressions)
  │     ├── ExprInt, ExprReal, ExprString, ExprChar, ExprBool
  │     ├── ExprIdent         (Variable lookup)
  │     ├── ExprFun           (fun(params) body)
  │     ├── ExprApp           (Function / operator call)
  │     ├── ExprIf, ExprWhile, ExprLoop, ExprTry, ExprRaise
  │     ├── ExprRecord        (record x = 1, y = 2 end)
  │     ├── ExprTuple         (tuple 1, 2, 3 end; components are TupleBindings, TupleBindingGroups for let ... and
  │     │                      ..., type bindings, and let rec declarations, which keep their annotations)
  │     ├── ExprArray         (array of [:T] a1 ... an end)
  │     ├── ExprArrayRep      (array of(n init))
  │     ├── ExprOption        (option (tag | ordinal(n)) of T [with Binding] end)
  │     ├── ExprVariant       (variant tag of T [with Value] end)
  │     ├── ExprVariantCheck  (target?tag)
  │     ├── ExprVariantAssert (target!tag)
  │     ├── ExprCase          (case target when ... else ... end)
  │     ├── ExprAuto          (auto [let A [HasKind] =] :T with Binding end)
  │     ├── ExprInspect       (inspect target when T with x then ... else ... end)
  │     ├── ExprDerefCell     (@target)
  │     └── ExprVarCell       (var(e))
  ├── Type                    (Level 1 types and type operators)
  │     ├── TypePath          (Named type or projection: Int, M.T)
  │     ├── TypeTuple         (Tuple x:Int, y:Real end)
  │     ├── TypeRecord        (Record x:Int, y:Real end)
  │     ├── TypeOption        (Option red, green with v:Int end)
  │     ├── TypeAuto          (Auto A<:B with a:A end)
  │     ├── TypeAll           (All(X <: B) T)
  │     ├── TypeFun           (Fun(X::K) T)
  │     └── TypeRec           (Rec(X <: B) T)
  └── Kind                    (Level 2 kinds)
        ├── KindType          (TYPE)
        ├── KindPower         (POWER(T))
        └── KindAll           (ALL(X::K1) K2)
```

### 4.1. Canonical S-Expression Serialization (`ast_dump`)
The parser outputs deterministic S-expressions formatted with **2 spaces of indentation per nesting level**:

```lisp
(Program
  :phrases (
    (LetValueBinding
      :name 'x'
      :type_annot (TypePath 'Int')
      :value (ExprInt 10 '10')
    )
  )
)
```

---

## 5. Desugaring (`quest/syntax/desugar.py`)

Between parsing and type checking, `desugar` rewrites syntactic sugar into the core forms the type checker
elaborates, so that the type checker does not rewrite syntax. It runs as the pipeline's `desugar` phase
([pipeline.md](pipeline.md) §2), and in `parse_unit` (`quest/modules/units.py`), through which every other path that
parses source to check it goes (the unit loader, the interface and module compilers, and the build engine's main
routines). The pass is purely syntactic, needing neither types nor scopes (`quest.syntax` imports nothing from later
phases, which `test_dependencies.py` checks), and each core form takes the offset of the syntax it replaces, so that
errors point at the source as written. It rewrites bottom up, returning a node unchanged (the same object) when
there is nothing to desugar.

| Written | Core form |
|---|---|
| `a andif b` | `if a then b else false end` |
| `a orif b` | `if a then true else b end` |
| `a op b`, for an operator `op` that is not built in | the call `op(a b)` (`ExprApp`) |
| `a[i] := v` | `ExprIndexAssign` |
| `if c1 then e1 elsif c2 then e2 ... [else e] end` | `if c1 then e1 else if c2 then e2 ... else e end end` |
| `let f(S): T = e`, neither `rec` nor external | `let f = fun(S): T e` |

Each conditional an elsif chain nests is positioned at its elsif's condition; a chain without an else branch ends in
`else ok`. The conditional of `andif` or `orif` is marked `short_circuit`: the type checker checks its operands
against Bool and gives it type Bool, so that an operand that is not Bool is reported as such, at the operand, rather
than as conditional branches the reader did not write.

The built-in infix operators, which stay infix (`BUILTIN_INFIX_OPERATORS`), are the arithmetic, relational,
concatenation, and eager boolean operators of [type-system.md](type-system.md) §6.3, `is`, `isnot`, `:=`, and `==`
and `!=` (which the type checker rejects with a suggestion). The table of their types, `INFIX_OPERATORS`, stays in
`quest/types/env.py`, which declares them, and a unit test checks that the two name the same operators. A conditional with neither
elsif nor else branches stays as it is: it is a statement, of type Ok. A recursive `let` with parameters keeps them,
since its parameters and result annotation declare its type before any value is checked
([type-system.md](type-system.md) §6.10); so does an external one, whose parameters declare the external function's
type. The parser already makes function values of the parameters of a tuple's non-recursive components, and keeps
recursive ones as declarations ([type-system.md](type-system.md) §4.1).

The type checker rejects the sugared forms as internal errors (`not_desugared` in `typechecker/checks.py`), so a path
that skips the pass fails loudly. The `desugar` phase's dump is the core AST, printed as the parse phase's is; it has
no golden tests.

---

## See Also
- [README.md](../README.md): Project overview and quickstart.
- [grammar.txt](grammar.txt): Canonical EBNF grammar.
- [type-system.md](type-system.md): Type system, kinds, and term elaboration.
- [pipeline.md](pipeline.md): Compiler pipeline framework and CLI driver.
- [testing.md](testing.md): Testing framework and golden outputs.
