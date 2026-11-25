"""What a syntax error says was expected, in words
(docs/error-messages-plan.md section 3).

The parser engine records the names of the constructs that failed at the
farthest token: token kinds (KW_END, or IDENT('foo') for a token with a fixed
lexeme) and the grammar's nonterminals (PrimaryValue). describe turns them into
what a reader writes: the nonterminals are left out, since the tokens that start
them are recorded too; a group of tokens that together mean "an expression", "a
type", "a declaration", or "an operator" becomes those words when every token of
the group is expected; literal and name tokens become words ("a name", "an
integer"); and every other token is quoted as written ('end', ')').

The self-hosted counterpart is questlang/syntax/parser/expected, whose groups
and words are the same."""

from __future__ import annotations

from typing import Iterable

from quest.syntax.tokens import DELIMITERS, KEYWORDS, RESERVED_PUNCTUATION, Token, TokenKind

# Each kind's name to its spelling, for the kinds that have one
_SPELLINGS: dict[str, str] = {
    kind.name: lexeme for table in (KEYWORDS, RESERVED_PUNCTUATION, DELIMITERS) for lexeme, kind in table.items()
}
_SPELLINGS[TokenKind.DOT.name] = "."

# The tokens that start an expression, a type, a declaration (in a block or at
# the top level), and the operators that continue an expression, each described
# by its words when all of its tokens are expected
_GROUPS: tuple[tuple[str, frozenset[str]], ...] = (
    (
        "an expression",
        frozenset(
            "AT CHAR_LIT IDENT INT_LIT KW_ARRAY KW_AUTO KW_BEGIN KW_CASE KW_EXCEPTION KW_EXIT KW_EXTENT KW_EXTERNAL"
            " KW_FALSE KW_FOR KW_FUN KW_IF KW_INSPECT KW_LOOP KW_NOT KW_OK KW_OPTION KW_ORDINAL KW_RAISE KW_RECORD"
            " KW_TRUE KW_TRY KW_TUPLE KW_VAR KW_VARIANT KW_WHILE LBRACE REAL_LIT STRING_LIT SYMBOLIC_INFIX".split()
        ),
    ),
    (
        "a type",
        frozenset(
            "IDENT KW_ALL KW_ARRAY_TYPE KW_AUTO_TYPE KW_EXCEPTION_TYPE KW_EXTERNAL KW_FUN_TYPE KW_OPTION_TYPE"
            " KW_OUT_TYPE KW_RECORD_TYPE KW_REC_TYPE KW_TUPLE_TYPE KW_VARIANT_TYPE KW_VAR_TYPE LBRACE"
            " SYMBOLIC_INFIX".split()
        ),
    ),
    (
        "a declaration",
        frozenset("KW_DEF KW_DEF_KIND KW_IMPORT KW_INTERFACE KW_LET KW_LET_TYPE KW_MODULE KW_UNSOUND".split()),
    ),
    (
        "an operator",
        frozenset(
            "ASSIGN BANG DOT KW_ANDIF KW_IS KW_ISNOT KW_ORIF LBRACKET LPAREN QUESTION SYMBOLIC_INFIX".split()
        ),
    ),
)

# The tokens without a fixed spelling, by what they are
_WORDS: dict[str, str] = {
    "IDENT": "a name",
    "INT_LIT": "an integer",
    "REAL_LIT": "a real number",
    "CHAR_LIT": "a character",
    "STRING_LIT": "a string",
    "SYMBOLIC_INFIX": "an operator",
    "EOF": "the end of the file",
}


def _is_token_name(name: str) -> bool:
    """Whether name is a token's (KW_END, IDENT('foo')) rather than a
    nonterminal's (PrimaryValue): its kind is all capitals and underscores."""
    kind = name.split("(", 1)[0]
    return kind != "" and all(c == "_" or "A" <= c <= "Z" for c in kind)


def _quoted(s: str) -> str:
    return "'" + s + "'"


def _phrases(names: Iterable[str]) -> list[str]:
    """The phrases for names: the quoted tokens, sorted, then the words,
    sorted."""
    tokens = {n for n in names if _is_token_name(n)}
    words: set[str] = set()
    covered: set[str] = set()
    for word, group in _GROUPS:
        if group <= tokens:
            words.add(word)
            covered |= group
    quoted: set[str] = set()
    for name in tokens - covered:
        if "('" in name and name.endswith("')"):
            quoted.add(_quoted(name[name.index("('") + 2 : -2]))
        elif name in _WORDS:
            words.add(_WORDS[name])
        elif name in _SPELLINGS:
            quoted.add(_quoted(_SPELLINGS[name]))
        else:
            words.add(name)
    return sorted(quoted) + sorted(words)


def _listed(phrases: list[str]) -> str:
    """phrases joined as a list in prose: a, b, or c."""
    if len(phrases) <= 2:
        return " or ".join(phrases)
    return ", ".join(phrases[:-1]) + ", or " + phrases[-1]


def found(token: Token) -> str:
    """What was found instead: the token as written, or the end of the
    file."""
    return "the end of the file" if token.kind == TokenKind.EOF else _quoted(token.lexeme)


def describe(names: Iterable[str], token: Token) -> str:
    """The message of a syntax error at token, where the constructs named by
    names were expected."""
    phrases = _phrases(names)
    if not phrases:
        return f"Unexpected {found(token)}"
    return f"Expected {_listed(phrases)}, found {found(token)}"
