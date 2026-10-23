"""Specialization (quest/ir/specialize.py, docs/ir.md §8.1).

Every golden test program is specialized, verified, and run (run_tests.py's run_ir_specialized phase); these tests
check the pass's decisions on small programs."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.ir.interp import run_unit
from quest.ir.lower import lower_program
from quest.ir.printer import format_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import verify_unit
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)

PRELUDE = "Let P = Record a: Int end; "


def specialize(source: str) -> tuple[str, str]:
    """The specialized IR's text, and its output when run (which prints the last phrase's result)."""
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = specialize_unit(lower_program(res.artifacts["typecheck"], ctx.env, print_result=True))
    problems = verify_unit(unit)
    assert not problems, problems
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        run_unit(unit, ctx.runtime_env)
    return format_unit(unit), out.getvalue()


class TestSpecialization(unittest.TestCase):
    def test_record_type_arguments_specialize(self) -> None:
        text, out = specialize(PRELUDE + "let id(A::TYPE x: A): A = x; id(:P record a = 1 end).a + id(:Int 2)")
        self.assertIn("fun id_spec(x.1: P): P {", text)
        self.assertIn("call id_spec(", text)
        # A scalar type argument does not call for a clone
        self.assertIn("call id [Int](2)", text)
        self.assertEqual(out, "3 : Int\n")

    def test_one_clone_per_function_and_type_arguments(self) -> None:
        text, _ = specialize(
            PRELUDE + "let id(A::TYPE x: A): A = x; let r = record a = 1 end; id(:P r).a + id(:P r).a"
        )
        self.assertEqual(text.count("fun id_spec"), 1)

    def test_local_functions_capturing_variables(self) -> None:
        text, out = specialize(
            PRELUDE + "let f(n: Int): Int = begin let pick(A::TYPE x: A y: A): A = if n > 0 then x else y end; "
            "pick(:P record a = 1 end record a = 2 end).a end; f(1) + f(0)"
        )
        self.assertIn("fun pick_spec(", text)
        self.assertEqual(out, "3 : Int\n")

    def test_recursive_clones_call_themselves(self) -> None:
        text, out = specialize(
            PRELUDE + "let rec count(A::TYPE x: A n: Int): Int = if n is 0 then 0 else 1 + count(:A x n - 1) end; "
            "count(:P record a = 1 end 3)"
        )
        self.assertEqual(text.count("fun count_spec"), 1)
        self.assertIn("call count_spec(x", text)
        self.assertEqual(out, "3 : Int\n")

    def test_open_type_arguments_stay_generic(self) -> None:
        # The call in g mentions g's own A, for which a clone would have no descriptor; g's clone specializes it
        text, out = specialize(
            PRELUDE + "let id(A::TYPE x: A): A = x; let g(A::TYPE x: A): A = id(:A x); g(:P record a = 4 end).a"
        )
        self.assertIn("call id [A](x", text)
        self.assertIn("fun g_spec(", text)
        self.assertIn("fun id_spec(", text)
        self.assertEqual(out, "4 : Int\n")

    def test_polymorphic_recursion_is_bounded(self) -> None:
        text, out = specialize(
            PRELUDE + "let rec deep(A::TYPE x: A n: Int): Int = "
            "if n is 0 then 0 else 1 + deep(:Tuple y: A end tuple let y = x end n - 1) end; "
            "deep(:P record a = 1 end 40)"
        )
        self.assertLessEqual(text.count("fun deep_spec"), 16)
        self.assertEqual(out, "40 : Int\n")

    def test_module_functions_specialize_as_members(self) -> None:
        text, out = specialize(
            PRELUDE + "interface Pick export first(A::TYPE x: A y: A): A end; "
            "module pick: Pick export let first(A::TYPE x: A y: A): A = x; end; "
            "pick.first(:P record a = 5 end record a = 6 end).a"
        )
        self.assertIn("first_spec1 = first_spec", text)
        self.assertIn("call pick.first_spec1(", text)
        self.assertEqual(out, "5 : Int\n")


if __name__ == "__main__":
    unittest.main()
