"""A top-level declaration as the REPL echoes it, in Cardelli's interactive
notation: let var x:T for a value, Let T::K = U for a type, DEF K = K' for a
kind, and exception e. The interpreter's formatting
(quest.interpreter.formatting) and the IR's lowering of echoed phrases
(quest.ir.lower) both write them here, so that the interpreter's echo and
compiled code's agree byte for byte.

The self-hosted counterpart is questlang/types/echo.
"""

from __future__ import annotations

from quest.types.model import QKind, QType
from quest.types.symbols import TypeSymbol, ValueSymbol


def value_declaration(name: str, symbol: ValueSymbol) -> str:
    """let x:T, or let var x:T for a var, which the echo follows with " = "
    and the value."""
    return f"let {'var ' if symbol.is_var else ''}{name}:{symbol.type_val}"


def function_declaration(name: str, t: QType) -> str:
    """A function's echo, whose value prints as <fun>: let f:T = <fun>."""
    return f"let {name}:{t} = <fun>"


def type_declaration(name: str, symbol: TypeSymbol) -> str:
    """Let T::K = U, or Let T::K for an abstract type."""
    if symbol.definition is not None:
        return f"Let {name}::{symbol.kind} = {symbol.definition}"
    return f"Let {name}::{symbol.kind}"


def kind_definition(name: str, kind: QKind) -> str:
    """DEF K = K'."""
    return f"DEF {name} = {kind}"


def exception_declaration(name: str) -> str:
    """exception e."""
    return f"exception {name}"
