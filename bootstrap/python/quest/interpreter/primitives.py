"""The interpreters' primitive operations and runtime errors, shared by the tree-walking interpreter
(quest.interpreter.treewalk), the IR interpreter (quest.interpreter.ir_interp), and the standard library's Python
implementations (quest.interpreter.builtins): integer and real arithmetic and comparisons with the semantics compiled
code has (C-style truncating division, real.error for NaN results), and the standard library's error exceptions.
"""

from __future__ import annotations

import math
from typing import Optional

from quest.diagnostics import Diagnostic, DiagnosticLabel, QuestCompilerError, Severity
from quest.values.model import QExceptionVal, QuestException


class QuestRuntimeError(QuestCompilerError):
    """System-level runtime evaluation error (e.g. undefined symbol)."""

    def __init__(self, message: str, offset: Optional[int] = None, length: int = 1):
        super().__init__(message=message, offset=offset, length=length)

    def to_diagnostic(self, length: Optional[int] = None) -> Diagnostic:
        len_val = length if length is not None else self.length
        label = DiagnosticLabel(offset=self.offset, length=len_val) if self.offset is not None else None
        return Diagnostic(
            severity=Severity.ERROR,
            message=self.message,
            primary_label=label,
        )


ARRAY_OP_ERROR_EXC = QExceptionVal("arrayOp.error")
WRITER_ERROR_EXC = QExceptionVal("writer.error")
READER_ERROR_EXC = QExceptionVal("reader.error")
ASCII_ERROR_EXC = QExceptionVal("ascii.error")
INT_ERROR_EXC = QExceptionVal("int.error")
REAL_ERROR_EXC = QExceptionVal("real.error")
WORD_ERROR_EXC = QExceptionVal("word.error")
STRING_ERROR_EXC = QExceptionVal("string.error")
SYSTEM_ERROR_EXC = QExceptionVal("system.error")
READLINE_ERROR_EXC = QExceptionVal("readline.error")
READLINE_END_OF_INPUT_EXC = QExceptionVal("readline.endOfInput")
READLINE_INTERRUPTED_EXC = QExceptionVal("readline.interrupted")
VARIANT_ERROR_EXC = QExceptionVal("variant.tagMismatch")


def truncating_div(a: int, b: int) -> int:
    """a / b rounded toward zero, as in C; exact, unlike int(a / b), which divides as floats."""
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) else -q


def int_arithmetic(op: str, a: int, b: int, offset: Optional[int] = None) -> int:
    """Evaluates integer arithmetic with C-style truncation and an int.error check."""
    match op:
        case "+":
            return a + b
        case "-":
            return a - b
        case "*":
            return a * b
        case "/":
            if b == 0:
                raise QuestException(INT_ERROR_EXC, offset=offset)
            return truncating_div(a, b)
        case "mod" | "%":
            if b == 0:
                raise QuestException(INT_ERROR_EXC, offset=offset)
            # C-style modulo: a - trunc(a / b) * b
            return a - truncating_div(a, b) * b
        case _:
            raise QuestRuntimeError(f"Unknown integer arithmetic operator '{op}'", offset=offset)


def int_relational(op: str, a: int, b: int, offset: Optional[int] = None) -> bool:
    """Evaluates integer relational comparisons (<, <=, >, >=)."""
    match op:
        case "<":
            return a < b
        case "<=":
            return a <= b
        case ">":
            return a > b
        case ">=":
            return a >= b
        case _:
            raise QuestRuntimeError(f"Unknown integer relational operator '{op}'", offset=offset)


def real_result(r: float, offset: Optional[int] = None) -> float:
    """Keeps NaN out of Quest: an operation whose IEEE result would be NaN raises real.error.

    Infinities are ordinary Real values (docs/type-system.md §6.3.1)."""
    if math.isnan(r):
        raise QuestException(REAL_ERROR_EXC, offset=offset)
    return r


def real_divide(a: float, b: float, offset: Optional[int] = None) -> float:
    """Real division (// and real.div): a zero divisor or a NaN result raises real.error."""
    if b == 0.0:
        raise QuestException(REAL_ERROR_EXC, offset=offset)
    return real_result(a / b, offset)


def real_pow(a: float, b: float, offset: Optional[int] = None) -> float:
    """Real exponentiation (^^ and real.exp) with C pow semantics, except that a zero base with a negative
    exponent (a pole, like division by zero) or a NaN result raises real.error. Overflow yields an infinity."""
    if a == 0.0 and b < 0.0:
        raise QuestException(REAL_ERROR_EXC, offset=offset)
    try:
        return real_result(math.pow(a, b), offset)
    except ValueError:
        # A negative finite base with a non-integral exponent: C's pow returns NaN.
        raise QuestException(REAL_ERROR_EXC, offset=offset)
    except OverflowError:
        negative = a < 0.0 and b.is_integer() and int(b) % 2 == 1
        return -math.inf if negative else math.inf


def real_arithmetic(op: str, a: float, b: float, offset: Optional[int] = None) -> float:
    """Evaluates real floating-point arithmetic (++, --, **, //, ^^)."""
    match op:
        case "++":
            return real_result(a + b, offset)
        case "--":
            return real_result(a - b, offset)
        case "**":
            return real_result(a * b, offset)
        case "//":
            return real_divide(a, b, offset)
        case "^^":
            return real_pow(a, b, offset)
        case _:
            raise QuestRuntimeError(f"Unknown real arithmetic operator '{op}'", offset=offset)


def real_relational(op: str, a: float, b: float, offset: Optional[int] = None) -> bool:
    """Evaluates real relational comparisons (<<, <<=, >>, >>=)."""
    match op:
        case "<<":
            return a < b
        case "<<=":
            return a <= b
        case ">>":
            return a > b
        case ">>=":
            return a >= b
        case _:
            raise QuestRuntimeError(f"Unknown real relational operator '{op}'", offset=offset)
