"""What was left open where a parse failed (docs/diagnostics.md §4.1).

The parser reports a syntax error where it stopped, which for a missing end or
bracket is often far from where the fix goes: the end of the file, or the next
declaration. After a parse has failed, find walks the tokens with a stack of
what is open, the keywords that end closes and the brackets, and returns the
first construct it can show was left open, or a closer with nothing to close:

- a closing bracket where something else is innermost, or an end where a
  bracket is: the innermost construct is not closed;
- an end that starts a line at the column of the line of an opener deeper than
  the innermost: the innermost is missing its end, since quest fmt lines an end
  up with the line its construct starts on (docs/formatter.md);
- a declaration (let, Let, Def, ...) that starts a line no further right than
  the line of the innermost opener: that opener is missing its end;
- the end of the file with something open: the innermost is not closed;
- an end or closing bracket with nothing it can close.

The keywords that end closes are the grammar's (docs/grammar.txt), with two
that open only in context: of, unless it is option's or variant's or is
followed by a parenthesis (array of(n x)), and with, inside an Option type.
The self-hosted counterpart is questlang/syntax/parser/unclosed."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from quest.common.location import SourceMap
from quest.syntax.tokens import Token, TokenKind as K

# The keywords whose construct end closes
_OPENERS = frozenset(
    {
        K.KW_INTERFACE, K.KW_MODULE, K.KW_TUPLE_TYPE, K.KW_OPTION_TYPE, K.KW_AUTO_TYPE, K.KW_RECORD_TYPE,
        K.KW_VARIANT_TYPE, K.KW_IF, K.KW_BEGIN, K.KW_LOOP, K.KW_WHILE, K.KW_FOR, K.KW_TUPLE, K.KW_AUTO,
        K.KW_OPTION, K.KW_RECORD, K.KW_VARIANT, K.KW_CASE, K.KW_INSPECT, K.KW_EXCEPTION, K.KW_RAISE, K.KW_TRY,
    }
)  # fmt: skip

_BRACKETS = {K.LPAREN: ")", K.LBRACKET: "]", K.LBRACE: "}"}
_CLOSING = {K.RPAREN: K.LPAREN, K.RBRACKET: K.LBRACKET, K.RBRACE: K.LBRACE}

# The keywords that start a declaration, which cannot continue a construct
# begun on a line no further left
_DECLARATIONS = frozenset({K.KW_LET, K.KW_LET_TYPE, K.KW_DEF, K.KW_DEF_KIND, K.KW_INTERFACE, K.KW_MODULE, K.KW_UNSOUND})


@dataclass(frozen=True)
class Unclosed:
    """A construct left open, or a closer with nothing to close: the token the
    error is located at, its message, and a note saying what shows it."""

    token: Token
    message: str
    note: Optional[str]
    # Whether token is a closer with nothing to close, rather than an opener
    closes_nothing: bool = False


@dataclass
class _Open:
    token: Token
    # The column of the first token of the line the opener is on
    indent: int
    # For option and variant, whether their of is still to come
    awaiting_of: bool = False


def _closer(token: Token) -> str:
    return _BRACKETS.get(token.kind, "end")


def _not_closed(entry: _Open, note: Optional[str]) -> Unclosed:
    return Unclosed(entry.token, f"'{entry.token.lexeme}' has no matching '{_closer(entry.token)}'", note)


def find(tokens: list[Token], source_map: SourceMap) -> Optional[Unclosed]:
    """The first construct left open in tokens (without the EOF token), or a
    closer with nothing to close, if the walk can show one."""

    def at(token: Token) -> str:
        loc = source_map.locate(token.offset)
        return f"{loc.line}:{loc.column}"

    def described(token: Token) -> str:
        return f"the '{token.lexeme}' at {at(token)}"

    stack: list[_Open] = []
    indent = 1
    previous_line = 0
    for i, token in enumerate(tokens):
        loc = source_map.locate(token.offset)
        starts_line = loc.line > previous_line
        previous_line = loc.line
        if starts_line:
            indent = loc.column
        kind = token.kind
        if starts_line and kind in _DECLARATIONS and stack and loc.column <= stack[-1].indent:
            return _not_closed(stack[-1], f"{described(token)} starts another declaration")
        if kind == K.KW_END:
            if not any(e.token.kind not in _BRACKETS for e in stack):
                return Unclosed(token, "'end' closes nothing", None, closes_nothing=True)
            top = stack[-1]
            if top.token.kind in _BRACKETS:
                opener = next(e for e in reversed(stack) if e.token.kind not in _BRACKETS)
                return _not_closed(top, f"{described(token)} closes {described(opener.token)}")
            if starts_line and loc.column != top.indent:
                for entry in reversed(stack[:-1]):
                    if entry.token.kind not in _BRACKETS and entry.indent == loc.column:
                        return _not_closed(top, f"{described(token)} lines up with {described(entry.token)}")
            stack.pop()
        elif kind in _CLOSING:
            opening = _CLOSING[kind]
            if not any(e.token.kind == opening for e in stack):
                return Unclosed(token, f"'{token.lexeme}' closes nothing", None, closes_nothing=True)
            top = stack[-1]
            if top.token.kind != opening:
                opener = next(e for e in reversed(stack) if e.token.kind == opening)
                return _not_closed(top, f"{described(token)} closes {described(opener.token)}")
            stack.pop()
        elif kind in _BRACKETS:
            stack.append(_Open(token, indent))
        elif kind == K.KW_OF:
            if stack and stack[-1].awaiting_of:
                stack[-1].awaiting_of = False
            elif i + 1 >= len(tokens) or tokens[i + 1].kind != K.LPAREN:
                stack.append(_Open(token, indent))
        elif kind == K.KW_WITH:
            if stack and stack[-1].token.kind == K.KW_OPTION_TYPE:
                stack.append(_Open(token, indent))
        elif kind in _OPENERS:
            stack.append(_Open(token, indent, awaiting_of=kind in (K.KW_OPTION, K.KW_VARIANT)))
    if stack:
        return _not_closed(stack[-1], None)
    return None
