"""The C backend's entry points: a typed program or module file lowered to the
IR, the IR's passes run (codegen/backend.py), and the described IR printed as C
(c/printer.py)."""

from __future__ import annotations

from typing import Any, Optional

from quest.codegen.backend import run_passes
from quest.codegen.c.printer import print_c
from quest.ir import nodes as ir
from quest.ir.lower import lower_module_file, lower_program
from quest.ir.verify import check_unit, ir_checks_enabled
from quest.typechecker.typed_ast import TypedModule, TypedProgram


def program_to_c(prog: TypedProgram, env: Any, echo: bool = False, print_result: bool = False) -> tuple[str, ir.Unit]:
    """A program's C translation, and its described unit."""
    unit = lower_program(prog, env, echo=echo, print_result=print_result)
    if ir_checks_enabled():
        check_unit(unit)
    unit = run_passes(unit)
    return print_c(unit, env), unit


def module_file_to_c(mod: TypedModule, env: Any, interface_header: Optional[str] = None) -> str:
    """A module file's C translation, which exports its interface's members
    (c/declarations.py)."""
    unit = lower_module_file(mod, env)
    if ir_checks_enabled():
        check_unit(unit)
    return print_c(run_passes(unit), env, interface_header)
