# bootstrap/python/quest/syntax: the bootstrap compiler's front end

This package is the front end of the Python bootstrap compiler: it turns Quest source text into the desugared syntax
tree that the bootstrap's type checker (`quest/typechecker`) elaborates. The steps are the same as in the self-hosted
compiler: tokenize, parse, desugar. Every path that loads a unit or program outside the phase pipeline goes through
`parse_unit` in [`../modules/units.py`](../modules/units.py), which runs all three, and the pipeline
([`../pipeline.py`](../pipeline.py)) runs them as its `tokenize`, `parse` and `desugar` phases. The package imports
nothing from later phases.

The self-hosted counterpart, `questlang/syntax`, was ported from this package and matches it in token names, grammar,
tree shape, printed output and error messages; shared golden tests hold both to the same text. Its
[README](../../../../questlang/syntax/README.md) and [the parser's](../../../../questlang/syntax/parser/README.md) give
the full introduction: Quest's lexical families of keywords, user-definable symbolic operators, the single right-
grouping precedence of infix operators, the AST's levels, PEG and packrat parsing, farthest-failure error reporting,
and what desugaring rewrites. This page covers how the Python code is organized and where it differs.

## The pieces

- **Tokens and tokenizer.** [`tokens.py`](tokens.py) defines `TokenKind`, whose member names (`KW_LET`, `IDENT`) are
  what the tokenize phase and syntax errors print, and the tables the tokenizer classifies lexemes by: `KEYWORDS`,
  `RESERVED_PUNCTUATION`, `DELIMITERS`, `SYMBOLIC_CHARS`. A token records the offset of its first character; offsets
  become lines and columns only when an error is printed. [`tokenizer.py`](tokenizer.py)'s `Tokenizer.tokenize_all`
  returns the token list, ending in EOF.
- **Parser engine.** [`parser.py`](parser.py) is a generic packrat parser that knows nothing of Quest. Its constructs
  (`MatchToken`, `Optional`, `Repeated`, `Sequence`, `SepBy`) and `SyntaxTarget`, a nonterminal with ordered `Rule`s,
  describe a grammar as data; `Parser`'s docstring explains the algorithm. Values flowing between constructs are plain
  Python objects (tokens, tuples, AST nodes), with `None` meaning failure.
- **Grammar.** [`grammar.py`](grammar.py) builds the Quest grammar when it is imported (`build_quest_grammar`), with
  each rule's action written inline as a lambda or a helper. `parse_quest_program` parses a token list from a start
  target, a whole program by default or a type, kind or value by name.
- **AST.** [`ast.py`](ast.py) defines the tree as frozen dataclasses deriving from `ASTNode`, one class per construct
  (`ExprIf`, `TypeTuple`, `LetValueBinding`, ...), each with the offset of the text it came from. `ast_fields` and
  `rebuild_ast` are the tree's one generic traversal, with a case per class.
  [`astprint.py`](astprint.py)'s `ast_dump` prints a tree as the parse phase's indented S-expression.
- **Desugaring.** [`desugar.py`](desugar.py) rewrites the sugar bottom up through `ast_fields` and `rebuild_ast`,
  returning a node unchanged (the same object) when there is nothing to rewrite. `BUILTIN_INFIX_OPERATORS` lists the
  operators that stay infix.

## Differences from questlang/syntax

- **Errors.** The tokenizer raises `TokenizerError` at the first malformed input; the self-hosted tokenizer reports
  every error to a diagnostic bag and continues. The parser raises `ParserError` where the self-hosted one adds to the
  bag and raises `diagbag.fatalError`. The message text is the same.
- **Nodes.** A Python node carries only a start offset and is its own class; a self-hosted node is a `Node(Form)` of
  a span (start and end) and a tagged form, with the classes becoming tags of `ExprForm`, `TypeForm` and `PhraseForm`.
- **Parser values and module split.** The engine passes untyped Python values, where the self-hosted engine has a
  typed `Val`. The rules and their actions live together in `grammar.py`; the self-hosted compiler separates them into
  `parser/grammar` and `parser/actions`, keeping the rules in the same order and the targets' names.
- **Traversal.** Desugaring here is one generic walk over `ast_fields`; the self-hosted desugar has an explicit case
  per form, since Quest has no reflection over a value's fields.

## Further reading

- [docs/syntax.md](../../../../docs/syntax.md): lexical rules, the grammar's notable forms, the AST hierarchy and its
  printed form, desugaring. Its paths are this package's.
- [docs/grammar.txt](../../../../docs/grammar.txt): the grammar in EBNF.
- [docs/pipeline.md](../../../../docs/pipeline.md): the phases and the driver.
- [docs/testing.md](../../../../docs/testing.md) §2.3 and §2.8: the golden tests and how the two compilers share them.
