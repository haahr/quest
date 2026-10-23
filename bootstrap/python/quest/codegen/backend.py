"""The C backend (docs/ir.md): a typed program or module file is lowered to the IR, the IR's passes run, and the
represented IR printed as C."""

from __future__ import annotations

from typing import Any, Optional

from quest.codegen.c_printer import print_c
from quest.ir import nodes as ir
from quest.ir.closure import closure_convert_unit
from quest.ir.lower import lower_module_file, lower_program
from quest.ir.represent import represent_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import check_unit, ir_checks_enabled
from quest.typed_ast import TypedImport, TypedModule, TypedProgram

# The IR's passes after lowering (docs/ir.md §9), in order, by the stage each produces
IR_PASSES = (("specialized", specialize_unit), ("closed", closure_convert_unit), ("represented", represent_unit))


def run_passes(unit: ir.Unit) -> ir.Unit:
    """The unit, represented: every pass run, each result verified when QUEST_CHECK_IR=1."""
    for _, run_pass in IR_PASSES:
        unit = run_pass(unit)
        if ir_checks_enabled():
            check_unit(unit)
    return unit


def program_to_c(prog: TypedProgram, env: Any, echo: bool = False, print_result: bool = False) -> tuple[str, ir.Unit]:
    """A program's C translation, and its represented unit."""
    unit = lower_program(prog, env, echo=echo, print_result=print_result)
    if ir_checks_enabled():
        check_unit(unit)
    unit = run_passes(unit)
    return print_c(unit, env), unit


def module_file_to_c(mod: TypedModule, env: Any, interface_header: Optional[str] = None) -> str:
    """A module file's C translation, which exports its interface's members (codegen/c_declarations.py)."""
    unit = lower_module_file(mod, env)
    if ir_checks_enabled():
        check_unit(unit)
    return print_c(run_passes(unit), env, interface_header)


def implicit_imports(unit: ir.Unit, prog: TypedProgram) -> list[tuple[str, str]]:
    """The modules (by canonical name and interface) a program's unit uses without importing them: standard library
    modules, which it links against too."""
    imported = {name for phrase in prog.phrases if isinstance(phrase, TypedImport) for it in phrase.items
                for name in it.names}
    return [(imp.canonical_path, imp.interface_path) for imp in unit.imports if imp.name not in imported]
