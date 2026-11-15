# questlang/syntax: from source text to syntax tree

This directory is the front end of the self-hosted compiler: it turns the text of a Quest source file into an abstract
syntax tree (AST) that the type checker can read. It is the lowest layer above `questlang/common` (source maps and
diagnostics) and knows nothing of types, scopes or code generation. Three steps run in order: the tokenizer splits the
text into tokens, the parser builds a tree from them, and desugaring rewrites a few convenient forms into the core forms
the type checker understands. The result goes to `questlang/typechecker`, usually by way of `parseUnit` in
[`../modules/units.mod.quest`](../modules/units.mod.quest), which every path that loads a unit or program goes through.

```
source text ──tokenizer──▶ tokens ──parser──▶ AST ──desugar──▶ AST without sugar ──▶ typechecker
```

The driver exposes each step as a phase: `quest --stop-after tokenize`, `--stop-after parse` and `--stop-after desugar`
print the tokens, the tree, and the desugared tree.

## Tokens

A token ([`tokens.int.quest`](tokens.int.quest)) is a kind, its lexeme (the exact source text), the decoded value of a
literal, and its span, the file and the character offsets it covers. Spans are only turned into lines and columns for
output and error messages. The token kinds' printed names (`KW_LET`, `SYMBOLIC_INFIX`, from `tokenKindName`) are
those of the bootstrap compiler, because the tokenize phase's output and the parser's error messages show them and both
compilers must print the same text.

The tokenizer ([`tokenizer.mod.quest`](tokenizer.mod.quest)) reflects a few distinctive features of Quest's lexical
syntax:

- Keywords come in three families by case, matching Quest's three levels: ALL CAPS for kinds (`TYPE`, `POWER`), an
  initial capital for types (`Tuple`, `Option`, `All`), lower case for values (`let`, `if`, `case`).
- Operators are not a fixed set. Any run of symbolic characters is one token, so `a+-b` is `a`, `+-`, `b`; a program
  can define its own operators. A handful of runs are reserved punctuation (`:=`, `::`, `<:`, `=`, `:`, `_`, ...), and
  brackets, comma, semicolon and dot are always single-character delimiters.
- Negative numeric literals are written with a tilde, `~3`, so that `-` stays an ordinary operator.
- Comments `(* ... *)` nest, and a character is a byte.

A malformed literal or an unexpected character is reported to a diagnostic bag and lexing continues; the caller checks
the bag. The REPL uses this to tell an unterminated string or comment (read another line) from a real error.

## The syntax tree

The AST is defined in one interface, [`ast.int.quest`](ast.int.quest), and the same types serve every phase that works
on source syntax: there is no separate tree per phase. Every node is a `Node(Form)`, a pair of a span (for error
messages) and a form, an `Option` (Quest's tagged union) whose tag says which construct the node is. The forms follow
Quest's levels:

| Level | Form | Covers |
|---|---|---|
| 0 | `ExprForm` | expressions and declarations (`Expr` and `Decl` are the same type) |
| 1 | `TypeForm` | types |
| 2 | `TypeForm` | kinds, the "types of types" (`TypeExpr` and `KindExpr` are the same type) |

`PhraseForm` and `Program` hold the top level of a file: imports, an interface or module, declarations and
expressions. Tags carry their category as a prefix (`exprIf`, `typeTuple`, `declLetVal`, `phraseModule`), which keeps
them distinct from keywords. Declarations share `ExprForm` with expressions because in Quest a block, a tuple and a
module body are all sequences in which declarations and expressions mix freely.

Two design choices shape the interface. Parts of a node that recur in several forms (a type parameter, a field of a
signature, a case branch) are written once as type operators over the type of the subterms, such as
`TypeFormalOf(T::TYPE)`, and applied to the node type afterwards; this lets the recursive `TypeForm` and `ExprForm` use
them before they are defined. And nodes are tuples rather than records: a tuple field is a single load at a fixed
offset, while a record pays for the structural subtyping it allows, which the AST does not need.

The tree mirrors the bootstrap compiler's AST node for node. [`astprint.mod.quest`](astprint.mod.quest) prints it as
the same indented S-expression the bootstrap prints, by first converting each node to a generic S-expression shaped
like the corresponding Python class and then rendering that with one set of layout rules. This is what lets both
parsers be compared on every Quest file in the tree.

## Parsing

[`parser.int.quest`](parser.int.quest) is the entry point: `parseProgram` for a file, and `parseType`, `parseKind` and
`parseValue` for a fragment. The interface compiler uses `parseType` and `parseKind` to read back the types and kinds
that compiled interface metadata (`.qi` files) stores as Quest syntax. The parser itself is in [`parser/`](parser/):
a generic packrat engine, the Quest grammar written as data, and the semantic actions that build AST nodes.
[`parser/README.md`](parser/README.md) explains it.

Two properties of Quest's grammar surprise newcomers. Every infix operator has the same precedence and groups to the
right, so `a - b - c` means `a - (b - c)` and `a + b * c` means `a + (b * c)`. And parentheses are for application and
parameter lists, never for grouping; braces group: `{a - b} - c`.

## Desugaring

[`desugar.int.quest`](desugar.int.quest) rewrites the parser's tree so that the type checker never has to rewrite
syntax. It needs neither types nor scopes, works bottom up, and gives each core form the span of the syntax it
replaces, so errors still point at the source as written. The rewrites are:

- `a andif b` and `a orif b` become conditionals marked `shortCircuit`, so the type checker can report a non-Bool
  operand as such rather than as a branch the programmer did not write.
- An infix operator that is not built in (`isBuiltinInfix`), `a op b`, becomes the call `op(a b)`. This is how
  user-defined operators work: an operator is just the name of a two-argument function.
- `a[i] := v` becomes `exprIndexAssign`; other assignments stay infix.
- An `elsif` chain becomes conditionals nested in the else branches, ending in `ok` if there is no else.
- A non-recursive function declaration `let f(params): T = e` becomes `let f = fun(params): T e`. A recursive or
  external one keeps its parameters, which declare its type before any body is checked.

For example, `let f(x: Int): Int = x - 1 - 2` parses (with `--stop-after parse`) as

```
(LetValueBinding
  :name 'f'
  :value (ExprInfix :left (ExprId 'x') :op '-' :right (ExprInfix :left (ExprInt 1 '1') :op '-' :right (ExprInt 2 '2')))
  :params ((FormalParam :name 'x' :type_annot (TypePath ('Int')) :mode VALUE))
  :type_annot (TypePath ('Int')))
```

(condensed here; the real dump puts each field on its own line), showing the right grouping of `-`. After
desugaring, the binding has no parameters and its value is an `ExprFun` with the parameter `x`, return type `Int`, and
that body.

## Connections

The consumers are the type checker (`questlang/typechecker`, which reads the desugared tree), the module system
(`questlang/modules`, which reads imports and unit declarations and calls `parseUnit`), and the driver
([`../driver/main.quest`](../driver/main.quest) for the tokenize, parse and desugar phases, and the REPL, which
parses each input and asks the parser whether an input is complete; the Jupyter kernel takes its completions from
`tokenizer.keywordNames`). The Python counterpart is
[`bootstrap/python/quest/syntax`](../../bootstrap/python/quest/syntax/README.md), with the same token names,
grammar, tree and error messages; the two differ mainly in that the bootstrap's tokenizer stops at its first error
and its tree nodes carry a start offset instead of a span.

## Further reading

- [docs/syntax.md](../../docs/syntax.md): lexical rules (§2), parsing mechanics and the grammar's notable forms (§3),
  the AST and its printed form (§4), desugaring (§5).
- [docs/grammar.txt](../../docs/grammar.txt): the grammar in EBNF.
- [docs/compiler-organization.md](../../docs/compiler-organization.md) §3 (the AST's design) and §4 (the parser's).
- [docs/testing.md](../../docs/testing.md) §2.3: how the two parsers are compared.
- [docs/TheQuestLanguageAndSystem.md](../../docs/TheQuestLanguageAndSystem.md): the language itself.
