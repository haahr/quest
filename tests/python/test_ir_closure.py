"""Closure conversion (quest/ir/closure.py, docs/ir.md §8.2).

Every golden test program is closure-converted, verified, and run (run_tests.py's run_ir_closed phase), and the
interpreter gives lifted functions only the globals, so a missed capture fails; these tests check the pass's
decisions on small programs."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.ir.closure import closure_convert_unit
from quest.interpreter.ir_interp import run_unit
from quest.ir.lower import lower_program
from quest.ir.printer import format_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import verify_unit
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)


def convert(source: str) -> tuple[str, str]:
    """The closure-converted IR's text, and its output when run (which prints the last phrase's result)."""
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = lower_program(res.artifacts["typecheck"], ctx.env, print_result=True)
    unit = closure_convert_unit(specialize_unit(unit))
    problems = verify_unit(unit)
    assert not problems, problems
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        run_unit(unit, ctx.runtime_env)
    return format_unit(unit), out.getvalue()


class TestClosureConversion(unittest.TestCase):
    def test_top_level_functions_capture_nothing(self) -> None:
        text, out = convert("let k = 10; let f(x: Int): Int = x + k; f(1)")
        # k is a global, which f uses rather than captures
        self.assertIn("fun f(x: Int): Int {", text)
        self.assertIn("closure f {}", text)
        self.assertEqual(out, "11 : Int\n")

    def test_captures_through_nested_functions(self) -> None:
        text, out = convert(
            "let f(x: Int): Int = begin let g(): Int = begin let h(): Int = x * 2; h() end; g() end; f(5)"
        )
        # g captures x for h, which it makes
        self.assertRegex(text, r"fun g \{env(\.\d+)?\}\(\): Int \{")
        self.assertRegex(text, r"closure h \{x(\.\d+)?\}")
        self.assertRegex(text, r"closure g \{x(\.\d+)?\}")
        self.assertEqual(out, "10 : Int\n")

    def test_loop_variables_are_captured_each_iteration(self) -> None:
        text, out = convert(
            "let z = fun(): Int 0; let fs = array of z z z end; "
            "for i = 0 upto 2 do fs[i] := fun(): Int i * 10 end; fs[0]() + fs[1]() + fs[2]()"
        )
        self.assertIn("closure f {i", text)
        self.assertEqual(out, "30 : Int\n")

    def test_mutually_recursive_local_functions(self) -> None:
        text, out = convert(
            "let f(n: Int): Bool = begin "
            "let rec even(k: Int): Bool = if k is 0 then true else odd(k - 1) end "
            "and odd(k: Int): Bool = if k is 0 then false else even(k - 1) end; even(n) end; f(7)"
        )
        self.assertIn("let rec (even", text)
        self.assertEqual(out, "false : Bool\n")

    def test_enclosing_type_parameters(self) -> None:
        text, out = convert(
            "let f(A::TYPE x: A): A = begin let g(): A = x; g() end; f(:Int 3)"
        )
        # g's types mention f's A, which g's closure supplies
        self.assertIn("fun g {env} [A::TYPE](): A {", text)
        self.assertRegex(text, r"closure g \{x(\.\d+)?\} \[A\]")
        self.assertEqual(out, "3 : Int\n")

    def test_recursive_values(self) -> None:
        _, out = convert(
            "Let Rec T = Tuple me(): T n: Int end; "
            "let mk(k: Int): T = begin let rec self: T = tuple let me(): T = self let n = k end; self end; "
            "mk(4).me().me().n"
        )
        self.assertEqual(out, "4 : Int\n")


if __name__ == "__main__":
    unittest.main()
