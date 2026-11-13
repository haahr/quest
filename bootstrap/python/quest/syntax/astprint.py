"""The syntax tree printed as the parse phase dumps it (--stop-after parse): a
node per line, as a canonical 2-space indented S-expression of its class and
its fields, each simple field inline. The self-hosted counterpart is
questlang/syntax/astprint."""

from __future__ import annotations

from dataclasses import fields
from enum import Enum
from typing import Any

from quest.syntax.ast import ASTNode


def _is_simple_leaf(value: Any) -> bool:
    """Checks if an AST value is a simple leaf that can be printed inline."""
    match value:
        case None | int() | float() | bool() | str() | Enum():
            return True
        case tuple() if all(isinstance(item, str) for item in value):
            return True
        case ASTNode() if len(fields(value)) == 0:
            return True
        case _:
            return False


def ast_dump(node: Any, indent: int = 0, show_offsets: bool = False) -> str:
    """Recursively formats an AST node into a canonical 2-space indented
    S-expression string."""
    padding = "  " * indent
    child_padding = "  " * (indent + 1)

    if not isinstance(node, ASTNode):
        match node:
            case tuple():
                if not node:
                    return "()"
                if all(_is_simple_leaf(item) for item in node):
                    return "(" + " ".join(repr(item) if isinstance(item, str) else str(item) for item in node) + ")"
                lines = ["("]
                for element in node:
                    lines.append(f"{child_padding}{ast_dump(element, indent + 1, show_offsets)}")
                lines.append(f"{padding})")
                return "\n".join(lines)
            case Enum(name=enum_name):
                return enum_name
            case str():
                return repr(node)
            case None:
                return "nil"
            case _:
                return str(node)

    class_name = node.__class__.__name__
    node_fields = fields(node)

    # Filter out offset field unless show_offsets is True
    active_fields = [field for field in node_fields if show_offsets or field.name != "offset"]

    if not active_fields:
        if show_offsets:
            return f"({class_name} :offset {node.offset})"
        return f"({class_name})"

    # Check if all fields are simple leaves
    all_simple = True
    field_values = []
    for field in active_fields:
        field_value = getattr(node, field.name)
        field_values.append((field.name, field_value))
        if not _is_simple_leaf(field_value):
            all_simple = False

    if all_simple:
        parts = [class_name]
        for name, field_value in field_values:
            match field_value:
                case Enum(name=enum_name):
                    parts.append(enum_name)
                case str():
                    parts.append(repr(field_value))
                case tuple():
                    parts.append("(" + " ".join(repr(item) for item in field_value) + ")")
                case None:
                    continue  # omit None in simple leaf inline
                case _:
                    parts.append(str(field_value))
        return f"({ ' '.join(parts) })"

    # Multi-line indented S-expression
    lines = [f"({class_name}"]
    for name, field_value in field_values:
        if field_value is None or field_value == () or field_value is False:
            # Skip empty optional values to keep trees compact
            continue
        if _is_simple_leaf(field_value):
            match field_value:
                case Enum(name=enum_name):
                    lines.append(f"{child_padding}:{name} {enum_name}")
                case str():
                    lines.append(f"{child_padding}:{name} {field_value!r}")
                case tuple():
                    lines.append(f"{child_padding}:{name} ({ ' '.join(repr(item) for item in field_value) })")
                case _:
                    lines.append(f"{child_padding}:{name} {field_value}")
        else:
            if isinstance(field_value, tuple):
                lines.append(f"{child_padding}:{name} (")
                for item in field_value:
                    lines.append(f"{child_padding}  {ast_dump(item, indent + 2, show_offsets)}")
                lines.append(f"{child_padding})")
            else:
                lines.append(f"{child_padding}:{name} {ast_dump(field_value, indent + 1, show_offsets)}")

    lines.append(f"{padding})")
    return "\n".join(lines)
