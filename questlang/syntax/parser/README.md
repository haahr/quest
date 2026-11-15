# questlang/syntax/parser: the packrat parser

This directory holds the parser behind [`../parser.int.quest`](../parser.int.quest). It takes the token vector the
tokenizer produces and builds the AST of [`../ast.int.quest`](../ast.int.quest), which goes on to desugaring and the
type checker. It is split into three modules with one job each: a generic parsing engine that knows nothing about
Quest, the Quest grammar written as data for that engine, and the semantic actions that turn what a grammar rule
matched into AST nodes. The split, and the grammar rule for rule, follow the bootstrap compiler's `parser.py` and
`grammar.py`, so that the two compilers accept the same programs, build the same trees, and report syntax errors in
the same words.

## Parsing expression grammars and packrat parsing

The grammar is a parsing expression grammar (PEG). A PEG looks like a context-free grammar, but its alternatives are
ordered: a nonterminal (here a *syntax target*) tries its rules in order and commits to the first that matches. A PEG
is therefore never ambiguous, but the order of rules is part of their meaning, since a rule that matches a prefix of
what a later rule would match hides it. A rule that fails consumes nothing, and the parser backtracks to try the next.

Unrestricted backtracking can take exponential time, so the engine is a *packrat* parser: it memoizes the outcome of
each target at each token position, so each is computed at most once and parsing is linear in the number of tokens.
The memo also guards against left recursion, which a PEG cannot express: a target that is reached again at the
position where it is already being tried fails instead of recursing forever. The grammar is written accordingly, with
a chain of operators as a repetition rather than a rule that begins with itself.

## The engine

[`engine.int.quest`](engine.int.quest) provides the building blocks. A `Construct` is one element of a rule: a token of
a given kind (`t`, or `tLex` for a specific lexeme), a target, an optional group (`opt`), a repetition (`rep`), or a
separated list (`sepBy`). The `p` and `pLex` forms are *silent*: punctuation that must match but whose token is not
passed on. `rule(target action) of items end` adds a rule to a target: when the items match, the action receives the
values of the non-silent ones.

Values passed between constructs and actions have the type `Val`, an `Option` with a case for each kind of thing a
rule can produce: an absent optional, a token, a string, a list, or one of the AST's types (`typeExpr`, `expr`,
`phrase`, ...). A dynamically typed value would be simpler, but the compiler avoids `dynamic.T` wherever a precise
type will do; an action that receives the wrong case raises `engine.error`, which always indicates a bug in the
grammar. Each action also gets a `Ctx` with the source range the rule matched, so the node it builds can carry its
span, and the diagnostic bag.

The parser itself ([`engine.mod.quest`](engine.mod.quest), `parseTarget` and `parse`) holds the memo as one flat array
indexed by position times the number of targets plus the target's number, which `newGrammar` and `target` assign as
the grammar is built. Each entry is not yet tried, in progress, or the known outcome. The array is reused from one
parse to the next, so that each parse does not allocate a fresh table of tokens times targets.

## Syntax errors

Because every alternative backtracks, a failed parse leaves no single point of failure. The engine records the
farthest token position at which any construct failed, and the names of everything that was expected there (token
kinds and target names). When no parse covers all the tokens, the error is reported at that token:

```
error: Unexpected token '(' (LPAREN), expected: AT, CHAR_LIT, IDENT, ..., PostfixValue, PrimaryValue, ..., Value
```

This is why targets have names (`"Value"`, `"PostfixValue"`): they appear in messages, and must match the bootstrap's.
The error goes to the bag and `diagbag.fatalError` is raised. The REPL relies on the farthest position too: if it is
the end of the input, the input is incomplete and the REPL reads another line.

## The grammar and its actions

[`grammar.mod.quest`](grammar.mod.quest) creates the targets (`Program`, `Phrase`, `Type`, `Kind`, `Value`, `Binding`,
and so on) and adds their rules, grouped by level: identifiers and imports, kinds, types, signatures, values and
bindings. Because the engine's combinators are ordinary Quest functions, a rule reads close to the EBNF it implements:

```
(* PostfixValue [ InfixOp Value ] *)
rule(x.value actions.valueInfix) of x.postfixValue opt of x.infixOp x.value end end
rule(x.postfixValue actions.valuePostfix) of x.primaryValue rep of x.postfixOp end end
```

The first rule gives Quest its single precedence level for infix operators with grouping to the right: the right
operand is a whole `Value`. The second shows how left recursion is avoided for postfix operators (`.field`, `(args)`,
`[index]`, `?tag`, `!tag`): a primary value followed by a repetition of operators. Each `PostfixOp` rule's action
returns a function from its operand to the node, and `valuePostfix` applies them left to right, so `a.b(c)` becomes a
call of a selection. [`grammar.int.quest`](grammar.int.quest) exports the targets parsing can start from.

[`actions.mod.quest`](actions.mod.quest) has one action per kind of rule; [`actions.int.quest`](actions.int.quest)
lists them, each with a comment giving the rule's non-silent items, which are its arguments. Actions only build nodes,
since a memoized match may be reused or belong to an alternative that is later abandoned. They follow the bootstrap's
actions closely, including where each node's span starts. Where the bootstrap parses something its later phases reject
but this AST has no place for (an interface or module below the top level, a declaration in an `Auto` type), the
action reports the error itself.

## Connections

[`../parser.mod.quest`](../parser.mod.quest) builds the grammar once and exposes `parseProgram`, `parseType`,
`parseKind` and `parseValue`. Its callers are described in [`../README.md`](../README.md). The bootstrap counterpart
is `bootstrap/python/quest/syntax/parser.py` (the engine) and `grammar.py` (rules and actions together); see
[its README](../../../bootstrap/python/quest/syntax/README.md). `tests/parser` compares the two parsers case by case,
and the test `syntax_parser_engine.quest` exercises the engine with a small grammar of its own.

## Further reading

- [docs/compiler-organization.md](../../../docs/compiler-organization.md) §4: the parser's architecture, `Val`, and
  the memo.
- [docs/syntax.md](../../../docs/syntax.md) §3: the PEG framework and the grammar's notable forms.
- [docs/grammar.txt](../../../docs/grammar.txt): the grammar in EBNF.
- [docs/testing.md](../../../docs/testing.md) §2.3: the self-hosted parser's tests.
