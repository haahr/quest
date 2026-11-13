"""The typed AST printed as the typecheck phase dumps it (--stop-after
typecheck). Each class of typed node says what it prints (dump_header,
dump_children, dump_type, in typed_ast.py); typed_ast_dump lays it out. The
self-hosted counterpart is questlang/typechecker/typedAstPrint."""

from __future__ import annotations

from typing import Any, Optional

from quest.typechecker.typed_ast import TypedNode
from quest.types import format_type_compact


def typed_ast_dump(node: TypedNode, indent: int = 0, env: Optional[Any] = None) -> str:
    """Formats a typed node into a canonical 2-space indented S-expression: its
    class, its dump_header, and its dump_type as :type on the first line, and
    its dump_children labeled below, one per line, each node indented under
    its parent."""
    child_pad = "  " * (indent + 1)

    # 1. Construct header parts
    parts = [node.__class__.__name__]
    extra = node.dump_header(env=env)
    if extra:
        parts.append(extra)

    t_val = node.dump_type()
    if t_val is not None:
        parts.append(f":type {format_type_compact(t_val, env=env)}")

    header_str = " ".join(parts)
    children = node.dump_children()

    # 2. Leaf node: render compact single-line
    if not children:
        return f"({header_str})"

    # 3. Non-leaf node: format labeled children consistently
    lines = [f"({header_str}"]
    for label, child in children:
        match child:
            case TypedNode():
                lines.append(f"{child_pad}{label} {typed_ast_dump(child, indent + 1, env=env)}")
            case tuple() | list():
                if not child:
                    lines.append(f"{child_pad}{label} ()")
                else:
                    lines.append(f"{child_pad}{label} (")
                    for elem in child:
                        if isinstance(elem, TypedNode):
                            lines.append(f"{child_pad}  {typed_ast_dump(elem, indent + 2, env=env)}")
                        else:
                            lines.append(f"{child_pad}  {elem}")
                    lines.append(f"{child_pad})")
            case None:
                pass
            case _:
                lines.append(f"{child_pad}{label} {child}")

    lines[-1] = lines[-1] + ")"
    return "\n".join(lines)
