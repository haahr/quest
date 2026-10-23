"""Representation (quest/ir/represent.py, docs/ir.md §8.3).

Every golden test program is represented, verified (each value used in the representation its use requires), and
run (run_tests.py's run_ir_represented phase), and compiled to C (run_c_compiled); these tests check
the pass's plans on small programs."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.ir import nodes as ir
from quest.ir.closure import closure_convert_unit
from quest.ir.lower import lower_program
from quest.ir.represent import RejectedConversion, represent_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import verify_unit
from quest.ir.walk import walk_statements
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)


def represent(source: str) -> ir.Unit:
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = lower_program(res.artifacts["typecheck"], ctx.env, print_result=True)
    unit = represent_unit(closure_convert_unit(specialize_unit(unit)))
    problems = verify_unit(unit)
    assert not problems, problems
    return unit


def plans(unit: ir.Unit) -> list[str]:
    """The kinds of the unit's conversions, in order."""
    found = []
    for body in [unit.main, *(f.body for f in unit.functions)]:
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Let) and isinstance(s.value, ir.Convert):
                found.append(s.value.plan.kind)
    return found


class TestRepresent(unittest.TestCase):
    def test_type_parameters_hold_qval_words(self) -> None:
        # The argument boxed for the generic parameter, the result unboxed (no clone: Int calls for none)
        self.assertEqual(plans(represent("let id(A::TYPE x: A): A = x; id(:Int 3) + 1")), ["box", "unbox"])

    def test_records_viewed_at_supertypes(self) -> None:
        unit = represent(
            "Let Small = Record a: Int end; Let Big = Record a: Int b: Int end; "
            "let big: Big = record a = 1 b = 2 end; let small: Small = big; small.a"
        )
        self.assertEqual(plans(unit), ["record_view"])

    def test_variants_tags_remapped(self) -> None:
        unit = represent(
            "Let S = Variant two: Int end; Let L = Variant one: Int two: Int end; "
            "let s: S = variant two of S with 2 end; let l: L = s; l?two"
        )
        self.assertEqual(plans(unit), ["variant_tags"])

    def test_function_subtyping_adapts_closures(self) -> None:
        unit = represent(
            "Let Small = Record a: Int end; Let Big = Record a: Int b: Int end; "
            "let f(x: Small): Int = x.a; let g: All(x: Big) Int = f; g(record a = 1 b = 2 end)"
        )
        self.assertIn("adapt", plans(unit))

    def test_a_generic_var_parameter_takes_a_shadow_cell(self) -> None:
        # Called through a first-class value (a direct call would be specialized, for its var parameters)
        unit = represent(
            "let swap(A::TYPE var x: A var y: A): Ok = begin let t = x; x := y; y := t end; "
            "let s: All(A::TYPE var x: A var y: A) Ok = swap; let var a = 1; let var b = 2; s(:Int @a @b); a"
        )
        cells = [s for s in walk_statements(unit.main, into_functions=False)
                 if isinstance(s, ir.VarDecl) and s.var.hint == "cell"]
        self.assertEqual(len(cells), 2)
        stores = [s for s in walk_statements(unit.main, into_functions=False) if isinstance(s, ir.Store)]
        self.assertEqual(len(stores), 2)

    def test_layouts_that_agree_are_cast(self) -> None:
        unit = represent(
            "Let Box = Fun(A::TYPE) Tuple x: A end; let get(A::TYPE b: Box(A)): A = b.x; "
            "let f: All(A::TYPE b: Box(A)) A = get; f(:Int tuple let x = 5 end)"
        )
        self.assertIn("cast", plans(unit))

    def test_layouts_that_disagree_convert_at_run_time(self) -> None:
        unit = represent(
            "Let P = Record a: Int end; Let Box = Fun(A::TYPE) Tuple x: A end; "
            "let get(A::TYPE b: Box(A)): A = b.x; let f: All(A::TYPE b: Box(A)) A = get; "
            "f(:P tuple let x = record a = 5 end end).a"
        )
        self.assertIn("runtime", plans(unit))

    def test_copying_mutable_data_is_rejected(self) -> None:
        with self.assertRaises(RejectedConversion):
            represent(
                "Let P = Record a: Int end; let first(A::TYPE xs: Array(A)): A = xs[0]; "
                "let f: All(A::TYPE xs: Array(A)) A = first; f(:P array of record a = 1 end end).a"
            )


if __name__ == "__main__":
    unittest.main()
