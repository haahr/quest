"""Unit files: an interface file (.int.quest) holds one interface declaration, and a module file (.mod.quest) one
module declaration (docs/modules.md)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import quest.syntax.ast as ast
from quest.diagnostics import QuestTypeError

INTERFACE_SUFFIX = ".int.quest"
MODULE_SUFFIX = ".mod.quest"


def unit_kind(path: Path) -> Optional[str]:
    """'interface' or 'module' for a unit file, by its name, and None for a program."""
    if path.name.endswith(INTERFACE_SUFFIX):
        return "interface"
    if path.name.endswith(MODULE_SUFFIX):
        return "module"
    return None


def unit_declaration(prog: ast.ASTNode, path: Path) -> ast.InterfaceDecl | ast.ModuleDecl:
    """The declaration a unit file's parsed program holds, which must be its only phrase, of the file's kind."""
    if unit_kind(path) == "interface":
        if not isinstance(prog, ast.Program) or len(prog.phrases) != 1:
            raise QuestTypeError(f"Interface file '{path.name}' must contain exactly one interface declaration")
        decl = prog.phrases[0]
        if not isinstance(decl, ast.InterfaceDecl):
            raise QuestTypeError(
                f"Expected interface declaration in '{path.name}', but found {type(decl).__name__}"
            )
        if decl.name.lower() != path.name.split(".")[0].lower():
            raise QuestTypeError(
                f"Interface declared in '{path.name}' has name '{decl.name}', which does not match file name",
                offset=decl.offset,
            )
        return decl
    if not isinstance(prog, ast.Program) or len(prog.phrases) != 1:
        raise QuestTypeError(f"Module file '{path.name}' must contain exactly one module declaration")
    decl = prog.phrases[0]
    if not isinstance(decl, ast.ModuleDecl):
        raise QuestTypeError(f"Expected module declaration in '{path.name}', found {type(decl).__name__}")
    return decl
