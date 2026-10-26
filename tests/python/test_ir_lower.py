"""Lowering from the typed AST to Core IR (quest/ir/lower.py, docs/ir.md §12 step 3).

Every golden test program is lowered and verified by run_tests.py's ir_core phase; these tests check particular
decisions of the lowering on small programs."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.ir import nodes as ir
from quest.ir.lower import lower_program
from quest.ir.printer import format_unit
from quest.ir.verify import verify_unit
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)


def lower(source: str, echo: bool = False, print_result: bool = False) -> tuple[ir.Unit, str]:
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = lower_program(res.artifacts["typecheck"], ctx.env, echo=echo, print_result=print_result)
    problems = verify_unit(unit)
    assert not problems, problems
    return unit, format_unit(unit)


class TestLowering(unittest.TestCase):
    def test_values_on_several_paths_join(self) -> None:
        _, text = lower("let f(c: Bool): Int = if c then 1 else 2 end; f(true)")
        self.assertIn("join k1(r: Int) {", text)
        self.assertIn("jump k1(1)", text)
        # An if for its effect alone needs no join point
        _, text = lower("let var x = 0; if true then x := 1 else x := 2 end; x")
        self.assertNotIn("join", text)

    def test_mutable_variables_and_addresses(self) -> None:
        _, text = lower("let incr(var v: Int): Ok = v := v + 1; let var g = 0; incr(@g); g")
        self.assertIn("fun incr(var v: Int): Ok", text)
        self.assertIn("v := %1", text)
        self.assertIn("var g: Int = 0", text)
        self.assertIn("addr g", text)

    def test_loops(self) -> None:
        _, text = lower(
            "let var s = 0; for i = 1 upto 3 do s := s + i end; while s > 0 do s := s - 1 end; loop exit end; s"
        )
        self.assertEqual(text.count("loop L"), 3)
        self.assertIn("break L1", text)
        self.assertIn("let i: Int = i", text.replace("i.1", "i"))

    def test_exceptions_and_handlers(self) -> None:
        _, text = lower(
            "exception E: Int end; let f(x: Int): Int = try raise E with x end when E with n then n + 1 end; f(1)"
        )
        self.assertIn("let E: Exception(Int) = exception E: Int", text)
        self.assertIn("} handle (e: Exception) {", text)
        self.assertIn("exception_payload(e)", text)
        self.assertIn("raise e", text)

    def test_an_exception_made_inside_an_expression_is_visible_to_its_scope(self) -> None:
        _, text = lower("let g(x: Int): Int = try raise exception I: Int end with x end when I with n then n end; g(2)")
        # Made before the binding that makes it, outside the try, whose pattern is then computed before it
        self.assertIn("let I: Exception(Int) = exception I: Int\n", text)
        self.assertLess(text.index("let I: Exception(Int)"), text.index("try catching (I)"))
        # A nested function may use it: it is a value, not a mutable variable
        _, text = lower(
            "let f(x: Int): Int = begin "
            "let a: Int = try raise exception I: Int end with x end when I with n then n end "
            "let h(): Int = try raise I with 2 end when I with n then n end "
            "a + h() end; f(1)"
        )
        self.assertIn("raise I with 2", text)

    def test_tuple_labels_bind_for_later_components(self) -> None:
        _, text = lower("let t = tuple let x = 1 let y = x + 1 end; t.y")
        self.assertIn("let x: Int = 1", text)
        self.assertIn("let y: Int = prim +(x, 1)", text)
        self.assertIn("tuple(x, y)", text)
        self.assertIn("tuple_field(t, 1)", text)

    def test_recursive_values(self) -> None:
        _, text = lower(
            "Let Rec T = Tuple me(): T end; "
            "let mk(): T = begin let rec self: T = tuple let me(): T = self end self end; mk()"
        )
        self.assertIn("let rec (self: T) {", text)

    def test_builtins_and_modules(self) -> None:
        _, text = lower(
            "import conv: Conv; Let O = Option a b end; "
            "let n = ordinal(option b of O end); let p = not true; conv.int(n)"
        )
        self.assertIn("ordinal(", text)
        self.assertIn("prim not(true)", text)
        self.assertIn("call conv.int(n)", text)

    def test_echo(self) -> None:
        _, text = lower("let x = 1; let f(): Int = x; x + 1", echo=True)
        self.assertIn('echo "let x:Int = " x : Int', text)
        self.assertIn('echo "let f:Fun(): Int = <fun>"', text)
        _, text = lower("let x = 1; x + 1", print_result=True)
        self.assertEqual(text.count("echo"), 1)


if __name__ == "__main__":
    unittest.main()
