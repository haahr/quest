"""Quest Tokenizer (Lexical Analyzer)."""

from __future__ import annotations

from typing import Callable, Iterator
from quest.tokens import (
    DELIMITERS,
    KEYWORDS,
    RESERVED_PUNCTUATION,
    SYMBOLIC_CHARS,
    SourceMap,
    Token,
    TokenKind,
)
from quest.diagnostics import QuestCompilerError


class TokenizerError(QuestCompilerError):
    """Raised on lexical errors (unterminated literals, invalid characters, etc.)."""


class IncompleteInputError(TokenizerError):
    """Raised by InteractiveTokenizer when input ends inside an unclosed comment or literal."""
    pass


# Single-character escapes: \n \t \r \b \f \\ \' \"
SIMPLE_ESCAPES: dict[str, str] = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "b": "\b",
    "f": "\f",
    "\\": "\\",
    "'": "'",
    '"': '"',
}

HEX_DIGITS = frozenset("0123456789abcdefABCDEF")


class Tokenizer:
    """Batch tokenizer for strings and files."""

    def __init__(self, source_text: str, file_name: str = "<string>"):
        self.source_text = source_text
        self.file_name = file_name
        self.cursor = 0
        self.length = len(source_text)
        self.source_map = SourceMap(source_text, file_name)

    @classmethod
    def from_file(cls, path: str) -> "Tokenizer":
        with open(path, "r", encoding="utf-8") as f:
            return cls(f.read(), path)

    def _peek(self, offset: int = 0) -> str:
        """The character at cursor + offset, or "" past the end of the input."""
        index = self.cursor + offset
        if index < self.length:
            return self.source_text[index]
        return ""

    def _advance(self) -> str:
        if self.cursor < self.length:
            char = self.source_text[self.cursor]
            self.cursor += 1
            return char
        return ""

    def _skip_while(self, predicate: Callable[[str], bool], limit: int | None = None) -> str:
        """Consumes characters (at most limit of them) while predicate holds; returns them."""
        start = self.cursor
        while self.cursor < self.length and (limit is None or self.cursor - start < limit):
            if not predicate(self.source_text[self.cursor]):
                break
            self.cursor += 1
        return self.source_text[start:self.cursor]

    def _at_comment_start(self) -> bool:
        return self._peek() == "(" and self._peek(1) == "*"

    def _skip_whitespace_and_comments(self) -> None:
        while self.cursor < self.length:
            # Whitespace
            if self._skip_while(lambda c: c in " \t\r\n\f\v"):
                continue

            # Nested Comments (* ... *)
            if self._at_comment_start():
                start_offset = self.cursor
                self.cursor += 2
                depth = 1
                while self.cursor < self.length and depth > 0:
                    if self._at_comment_start():
                        depth += 1
                        self.cursor += 2
                    elif self._peek() == "*" and self._peek(1) == ")":
                        depth -= 1
                        self.cursor += 2
                    else:
                        self.cursor += 1

                if depth > 0:
                    raise TokenizerError("Unclosed comment", start_offset, self.cursor - start_offset)
                continue

            break

    def _lex_number(self) -> Token:
        start = self.cursor
        if self._peek() == "~":
            self.cursor += 1
        self._skip_while(str.isdigit)

        # Check for decimal point followed by a digit: e.g. 2.0 or ~2.0
        if self._peek() == "." and self._peek(1).isdigit():
            self.cursor += 1  # Consume '.'
            self._skip_while(str.isdigit)

            # Optional exponent: e.g. 2.0e-5, 3.14E+2, ~5.1E~4
            if self._peek() in ("e", "E"):
                exponent_start = self.cursor
                self.cursor += 1
                if self._peek() in ("+", "-", "~"):
                    self.cursor += 1
                if not self._peek().isdigit():
                    raise TokenizerError(
                        "Malformed real exponent",
                        exponent_start,
                        self.cursor - exponent_start,
                    )
                self._skip_while(str.isdigit)

            kind, convert, what = TokenKind.REAL_LIT, float, "real"
        else:
            kind, convert, what = TokenKind.INT_LIT, int, "integer"

        lexeme = self.source_text[start:self.cursor]
        try:
            number_value = convert(lexeme.replace("~", "-"))
        except ValueError:
            raise TokenizerError(f"Invalid {what} literal '{lexeme}'", start, len(lexeme))
        return Token(kind, lexeme, number_value, start)

    def _lex_escape_sequence(self) -> str:
        """Lexes the escape sequence after a backslash (already consumed) and returns its character."""
        escape_start = self.cursor - 1
        if self.cursor >= self.length:
            raise TokenizerError("Unterminated escape sequence", escape_start, 1)

        char = self._advance()
        if char in SIMPLE_ESCAPES:
            return SIMPLE_ESCAPES[char]
        if char == "x":
            # Hexadecimal escape \xhh (1 or 2 hex digits)
            hex_digits = self._skip_while(lambda c: c in HEX_DIGITS, limit=2)
            if not hex_digits:
                raise TokenizerError(
                    "Invalid hexadecimal escape sequence",
                    escape_start,
                    self.cursor - escape_start,
                )
            return chr(int(hex_digits, 16))
        if char.isdigit():
            # Decimal character code \ddd (up to 3 decimal digits)
            char_code = int(char + self._skip_while(str.isdigit, limit=2))
            if char_code > 255:
                raise TokenizerError(
                    f"Character code {char_code} out of byte range",
                    escape_start,
                    self.cursor - escape_start,
                )
            return chr(char_code)
        raise TokenizerError(f"Unknown escape sequence '\\{char}'", escape_start, 2)

    def _lex_char(self) -> Token:
        start = self.cursor
        self.cursor += 1  # Consume opening quote '
        if self.cursor >= self.length or self._peek() == "'":
            raise TokenizerError("Empty character literal", start, self.cursor - start)

        if self._peek() == "\\":
            self.cursor += 1
            char_value = self._lex_escape_sequence()
        else:
            char_value = self._advance()

        if self._peek() != "'":
            raise TokenizerError("Unterminated character literal", start, self.cursor - start)

        self.cursor += 1  # Consume closing quote '
        lexeme = self.source_text[start:self.cursor]
        return Token(TokenKind.CHAR_LIT, lexeme, char_value, start)

    def _lex_string(self) -> Token:
        start = self.cursor
        self.cursor += 1  # Consume opening quote "
        chars: list[str] = []

        while self.cursor < self.length and self._peek() != '"':
            if self._peek() == "\\":
                self.cursor += 1
                chars.append(self._lex_escape_sequence())
            else:
                chars.append(self._advance())

        if self.cursor >= self.length:
            raise TokenizerError("Unterminated string literal", start, self.cursor - start)

        self.cursor += 1  # Consume closing quote "
        lexeme = self.source_text[start:self.cursor]
        return Token(TokenKind.STRING_LIT, lexeme, "".join(chars), start)

    def _lex_ident_or_keyword(self) -> Token:
        start = self.cursor
        lexeme = self._skip_while(str.isalnum)
        return Token(KEYWORDS.get(lexeme, TokenKind.IDENT), lexeme, None, start)

    def _lex_symbolic_or_punctuation(self) -> Token:
        start = self.cursor
        # Stop before ~ followed by a digit (the start of a negative number literal)
        while self._peek() in SYMBOLIC_CHARS and not (self._peek() == "~" and self._peek(1).isdigit()):
            self.cursor += 1

        lexeme = self.source_text[start:self.cursor]
        return Token(RESERVED_PUNCTUATION.get(lexeme, TokenKind.SYMBOLIC_INFIX), lexeme, None, start)

    def next_token(self) -> Token:
        """Returns the next Token from the input stream, returning EOF at end."""
        self._skip_whitespace_and_comments()

        if self.cursor >= self.length:
            return Token(TokenKind.EOF, "", None, self.cursor)

        start = self.cursor
        char = self._peek()

        # 1. Delimiters (single characters); a comment opener (* was already skipped
        if char in DELIMITERS:
            self.cursor += 1
            return Token(DELIMITERS[char], char, None, start)

        # 2. Dot operator
        if char == ".":
            self.cursor += 1
            return Token(TokenKind.DOT, ".", None, start)

        # 3. Numeric literals (unsigned or negative with Cardelli tilde ~)
        if char.isdigit() or (char == "~" and self._peek(1).isdigit()):
            return self._lex_number()

        # 4. Character literal
        if char == "'":
            return self._lex_char()

        # 5. String literal
        if char == '"':
            return self._lex_string()

        # 6. Alphanumeric identifiers and keywords
        if char.isalpha():
            return self._lex_ident_or_keyword()

        # 7. Symbolic operators and reserved punctuation
        if char in SYMBOLIC_CHARS:
            return self._lex_symbolic_or_punctuation()

        # 8. Unrecognized character
        self.cursor += 1
        raise TokenizerError(f"Unexpected character {char!r}", start, 1)

    def tokenize_all(self) -> list[Token]:
        """Eagerly consumes and returns all tokens up to and including EOF."""
        return list(self)

    def __iter__(self) -> Iterator[Token]:
        while True:
            token = self.next_token()
            yield token
            if token.kind == TokenKind.EOF:
                break


class InteractiveTokenizer:
    """Incremental tokenizer for REPL sessions, maintaining continuous offsets."""

    def __init__(self, file_name: str = "<stdin>"):
        self.file_name = file_name
        self.buffer = ""
        self.cursor = 0
        self.comment_depth = 0
        self.source_map = SourceMap("", file_name)

    def feed(self, line: str) -> list[Token]:
        """Appends a new input line and yields all fully completed tokens."""
        self.buffer += line + "\n"
        self.source_map = SourceMap(self.buffer, self.file_name)
        tokenizer = Tokenizer(self.buffer, self.file_name)
        tokenizer.cursor = self.cursor

        tokens: list[Token] = []
        try:
            while True:
                # Save position before attempting next token
                pos_before = tokenizer.cursor
                tokenizer._skip_whitespace_and_comments()
                if tokenizer.cursor >= len(self.buffer):
                    # Reached end of buffer without trailing partial tokens
                    self.cursor = tokenizer.cursor
                    break

                token = tokenizer.next_token()
                if token.kind == TokenKind.EOF:
                    self.cursor = tokenizer.cursor
                    break
                tokens.append(token)
                self.cursor = tokenizer.cursor
        except TokenizerError:
            # If error is due to unclosed literal/comment at end of buffer, wait for more input
            pass

        return tokens

    def is_complete(self) -> bool:
        """Returns True if no comments or literals are pending completion."""
        tokenizer = Tokenizer(self.buffer, self.file_name)
        try:
            tokenizer.tokenize_all()
            return True
        except TokenizerError:
            return False
