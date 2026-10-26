"""What every backend does with a unit before writing its code (docs/ir.md): the
IR's passes after lowering, and the modules a unit uses without importing them.
The C backend is quest.codegen.c (c/backend.py)."""

from __future__ import annotations

from quest.ir import nodes as ir
from quest.ir.closure import closure_convert_unit
from quest.ir.describe import describe_unit
from quest.ir.represent import represent_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import check_unit, ir_checks_enabled
from quest.typechecker.typed_ast import TypedImport, TypedProgram

# The IR's passes after lowering (docs/ir.md §9), in order, by the stage each
# produces
IR_PASSES = (
    ("specialized", specialize_unit), ("closed", closure_convert_unit), ("represented", represent_unit),
    ("described", describe_unit),
)


def run_passes(unit: ir.Unit) -> ir.Unit:
    """The unit, described: every pass run, each result verified when
    QUEST_CHECK_IR=1."""
    for _, run_pass in IR_PASSES:
        unit = run_pass(unit)
        if ir_checks_enabled():
            check_unit(unit)
    return unit


def implicit_imports(unit: ir.Unit, prog: TypedProgram) -> list[tuple[str, str]]:
    """The modules (by canonical name and interface) a program's unit uses
    without importing them: standard library modules, which it links against
    too."""
    imported = {name for phrase in prog.phrases if isinstance(phrase, TypedImport) for it in phrase.items
                for name in it.names}
    return [(imp.canonical_path, imp.interface_path) for imp in unit.imports if imp.name not in imported]
