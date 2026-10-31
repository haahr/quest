"""The spelling of C text (docs/converting-python-to-quest.md, rule 6):
literals and the forms the C backend repeats.

Every piece of C the backend writes is a string built from these and from
strings: a value interpolated into C text is a string (numbers go through c_int
or c_int_literal), and lists of C are joined only here. This keeps each line of
the backend a line of Quest when it is ported, where text is concatenated with
`<>` and a number is never spelled by `conv.int` alone (which writes negative
numbers with `~`).
"""

from __future__ import annotations

import math
from typing import Iterable


# Literals

def c_int(n: int) -> str:
    """A nonnegative integer in decimal: an index, a count, or a number in a
    name (`_0`, `c1`, `d2`)."""
    assert n >= 0, n
    return str(n)


def c_int_literal(n: int) -> str:
    """An int64_t constant: `5LL`, or `(-5LL)` for a negative one."""
    return f"{c_int(n)}LL" if n >= 0 else f"(-{c_int(-n)}LL)"


def c_real(r: float) -> str:
    """A double constant: Python's repr of it (the shortest digits that read
    back as it, as conv.real writes them), with `.0` appended when it would read
    as an integer; an infinity is `INFINITY` or `(-INFINITY)`."""
    if math.isinf(r):
        return "INFINITY" if r > 0 else "(-INFINITY)"
    s = repr(r)
    return s if "e" in s or "." in s else s + ".0"


# The escapes of characters that C writes with a backslash and a letter
_ESCAPES = {"\"": "\\\"", "'": "\\'", "\\": "\\\\", "\n": "\\n", "\t": "\\t", "\r": "\\r"}


def _c_char_text(ch: str, quote: str) -> str:
    """A character as it appears inside a C literal delimited by quote:
    printable ASCII as itself (the quote and the backslash escaped), the common
    control characters by their letter escapes, and any other character as a
    three-digit octal escape, which ends where it should whatever character
    follows (a hex escape does not)."""
    if ch == quote or ch == "\\" or ch in "\n\t\r":
        return _ESCAPES[ch]
    code = ord(ch)
    if 32 <= code < 127:
        return ch
    assert code < 256, code
    return "\\" + c_int(code // 64) + c_int(code // 8 % 8) + c_int(code % 8)


def c_string(s: str) -> str:
    """A C string literal of s."""
    return "\"" + joined("", (_c_char_text(ch, "\"") for ch in s)) + "\""


def c_char(ch: str) -> str:
    """A C character literal of ch, cast to QChar above 127, since a C
    character literal is an int of the platform's char, which may be signed:
    without the cast, '\\310' would compare unequal to a QChar of 200."""
    literal = "'" + _c_char_text(ch, "'") + "'"
    return literal if ord(ch) < 128 else "((QChar)" + literal + ")"


def index_table(entries: Iterable[int]) -> str:
    """A C array of int64_t indices, to be indexed by a tag or an ordinal."""
    return "((const int64_t[]){ " + comma(c_int_literal(e) for e in entries) + " })"


# Forms

def comma(items: Iterable[str]) -> str:
    """C items separated by commas: arguments, parameters, initializers."""
    return joined(", ", items)


def call(f: str, args: Iterable[str]) -> str:
    """A call of f with the arguments."""
    return f + "(" + comma(args) + ")"


def joined(separator: str, items: Iterable[str]) -> str:
    """Pieces of text (parts of a name, say) separated by separator."""
    return separator.join(items)


def lines_text(items: Iterable[str]) -> str:
    """Lines of C separated by newlines."""
    return joined("\n", items)
