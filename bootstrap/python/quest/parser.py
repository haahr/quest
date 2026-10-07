"""Generic, Data-Driven PEG / Packrat Parser Engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional as Opt, Union

from quest.tokens import SourceMap, Token, TokenKind
from quest.diagnostics import Diagnostic, DiagnosticRenderer, QuestCompilerError


# ============================================================================
# 1. Grammar Constructs & Rules
# ============================================================================

class Construct:
    """Base class for all PEG grammar constructs.

    A silent construct must still match, but its result is not passed to the enclosing
    rule's action or included in the enclosing sequence's result.
    """
    can_match_empty: bool = False
    silent: bool = False

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        """Evaluates this construct against the parser at token position pos."""
        raise NotImplementedError


@dataclass(frozen=True)
class MatchToken(Construct):
    """Matches a specific terminal TokenKind and optional lexeme."""
    kind: TokenKind
    lexeme: Opt[str] = None
    silent: bool = False

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        token = parser._peek(pos)
        if token.kind == self.kind and (self.lexeme is None or token.lexeme == self.lexeme):
            return token, pos + 1
        name = f"{self.kind.name}('{self.lexeme}')" if self.lexeme else self.kind.name
        parser._record_failure(pos, name)
        return None, pos


class SyntaxTarget(Construct):
    """A grammar non-terminal syntax target owning its production rules."""
    can_match_empty: bool = False

    def __init__(self, name: str):
        self.name = name
        self.rules: list[Rule] = []

    def add_rule(self, constructs: tuple[Construct, ...], action: Callable[..., Any]) -> Rule:
        rule = Rule(constructs, action)
        self.rules.append(rule)
        return rule

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        result, new_pos = parser.parse_target(self, pos)
        if result is None:
            parser._record_failure(pos, self.name)
            return None, pos
        return result, new_pos

    def __repr__(self) -> str:
        return f"SyntaxTarget({self.name!r})"


def _sequence_of(items: tuple[Construct, ...]) -> Construct:
    """Returns a single construct as-is, or a Sequence of several."""
    return items[0] if len(items) == 1 else Sequence(items)


class Optional(Construct):
    """Matches inner construct(s) 0 or 1 times: [...] in EBNF.

    Evaluates to the inner result, or None if the inner construct does not match. Since a
    Sequence with one non-silent item yields that item, Optional(silent_keyword, X) is X or None.
    """
    can_match_empty: bool = True

    def __init__(self, *items: Construct):
        self.inner = _sequence_of(items)
        self.silent = self.inner.silent

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        result, new_pos = self.inner.evaluate(parser, pos)
        if result is not None:
            return result, new_pos
        return None, pos

    def __repr__(self) -> str:
        return f"Optional({self.inner!r})"


class Repeated(Construct):
    """Matches inner construct(s) 0 or more times: {...} in EBNF."""
    can_match_empty: bool = True

    def __init__(self, *items: Construct):
        self.inner = _sequence_of(items)

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        results: list[Any] = []
        current_pos = pos
        while True:
            result, new_pos = self.inner.evaluate(parser, current_pos)
            if result is None or new_pos <= current_pos:
                # Enforce progress assertion to prevent zero-width infinite loops
                break
            results.append(result)
            current_pos = new_pos
        return tuple(results), current_pos

    def __repr__(self) -> str:
        return f"Repeated({self.inner!r})"


class Sequence(Construct):
    """Matches a sequence of constructs in order.

    Evaluates to the results of its non-silent items: the result itself if there is exactly
    one, otherwise a tuple of them. A sequence whose items are all silent is itself silent.
    """

    def __init__(self, items: tuple[Construct, ...]):
        self.items = items
        self.silent = all(item.silent for item in items)
        self._single = sum(not item.silent for item in items) == 1

    def match(self, parser: Parser, pos: int) -> tuple[Opt[list[Any]], int]:
        """Matches all items, returning the non-silent results (or None on failure)."""
        results: list[Any] = []
        current_pos = pos
        for item in self.items:
            result, current_pos = item.evaluate(parser, current_pos)
            if result is None and not item.can_match_empty:
                return None, pos
            if not item.silent:
                results.append(result)
        return results, current_pos

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        results, new_pos = self.match(parser, pos)
        if results is None:
            return None, pos
        return (results[0] if self._single else tuple(results)), new_pos

    def __repr__(self) -> str:
        return f"Sequence({self.items!r})"


class SepBy(Construct):
    """Matches one or more items separated by a (silent) separator: item {sep item}.

    Evaluates to a tuple of the item results. A trailing separator is not consumed.
    """

    def __init__(self, item: Construct, separator: Construct):
        self.item = item
        self.separator = separator

    def evaluate(self, parser: Parser, pos: int) -> tuple[Opt[Any], int]:
        result, current_pos = self.item.evaluate(parser, pos)
        if result is None:
            return None, pos
        results = [result]
        while True:
            separator, after_separator = self.separator.evaluate(parser, current_pos)
            if separator is None:
                break
            result, after_item = self.item.evaluate(parser, after_separator)
            if result is None:
                break
            results.append(result)
            current_pos = after_item
        return tuple(results), current_pos

    def __repr__(self) -> str:
        return f"SepBy({self.item!r}, {self.separator!r})"


class Rule:
    """An alternative production rule: a sequence and the semantic action applied to its
    non-silent results."""

    def __init__(self, constructs: tuple[Construct, ...], action: Callable[..., Any]):
        self.sequence = Sequence(constructs)
        self.action = action


# ============================================================================
# 2. Parser Exception
# ============================================================================

class ParserError(QuestCompilerError):
    """Raised when parsing fails, carrying location and message."""

    def __init__(
        self,
        message: str,
        offset: int,
        length: int = 1,
        token: Opt[Token] = None,
    ):
        super().__init__(message=message, offset=offset, length=length)
        self.token = token

    def to_diagnostic(self) -> Diagnostic:
        """Converts this error into a structured Diagnostic object."""
        return Diagnostic.make_error(message=self.message, offset=self.offset, length=self.length)

    def format_with_source(self, source_map: SourceMap) -> str:
        return DiagnosticRenderer.render_diagnostic(self.to_diagnostic(), source_map)


# Sentinel for packrat recursion detection
_IN_PROGRESS = object()


# ============================================================================
# 3. Generic Packrat Parser Engine
# ============================================================================

class Parser:
    """Generic data-driven PEG / Packrat parser engine."""

    def __init__(
        self,
        tokens: list[Token],
        source_map: SourceMap,
    ):
        # Keep all non-EOF tokens followed by a single EOF token
        self.tokens = [token for token in tokens if token.kind != TokenKind.EOF] + [
            tokens[-1] if tokens else Token(TokenKind.EOF, "", None, 0)
        ]
        self.source_map = source_map
        self.cache: dict[tuple[Any, int], Any] = {}
        self.farthest_pos = 0
        self.expected_at_farthest: set[str] = set()

    def _peek(self, pos: int) -> Token:
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]

    def _record_failure(self, pos: int, expected: str) -> None:
        if pos > self.farthest_pos:
            self.farthest_pos = pos
            self.expected_at_farthest = {expected}
        elif pos == self.farthest_pos:
            self.expected_at_farthest.add(expected)

    def parse(self, start_target: SyntaxTarget) -> Any:
        """Parses the entire token stream starting from start_target."""
        self.cache.clear()
        self.farthest_pos = 0
        self.expected_at_farthest.clear()

        result, pos = self.parse_target(start_target, 0)

        # Ensure all tokens up to EOF were consumed
        if result is not None:
            token = self._peek(pos)
            if token.kind == TokenKind.EOF:
                return result

        # Format diagnostic error on failure
        farthest_token = self._peek(self.farthest_pos)
        expected_string = (
            ", ".join(sorted(self.expected_at_farthest))
            if self.expected_at_farthest
            else "valid syntax"
        )
        message = (
            f"Unexpected token {farthest_token.lexeme!r} ({farthest_token.kind.name}), "
            f"expected: {expected_string}"
        )
        raise ParserError(
            message,
            farthest_token.offset,
            max(1, farthest_token.length),
            token=farthest_token,
        )

    def parse_target(self, target: SyntaxTarget, pos: int) -> tuple[Opt[Any], int]:
        """Evaluates a target at the given token position with packrat memoization."""
        key = (target, pos)
        if key in self.cache:
            cached = self.cache[key]
            if cached is _IN_PROGRESS:
                # Cycle / left-recursion detected: break cycle
                return None, pos
            return cached

        self.cache[key] = _IN_PROGRESS

        for rule in target.rules:
            result, new_pos = self._evaluate_rule(rule, pos)
            if result is not None:
                self.cache[key] = (result, new_pos)
                return result, new_pos

        self.cache[key] = (None, pos)
        return None, pos

    def _evaluate_rule(self, rule: Rule, pos: int) -> tuple[Opt[Any], int]:
        arguments, new_pos = rule.sequence.match(self, pos)
        if arguments is None:
            return None, pos
        return rule.action(*arguments), new_pos
