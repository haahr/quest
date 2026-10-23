"""The IR interpreter (quest/interpreter/ir_interp.py, docs/ir.md §12 step 4).

Every golden test program runs through it in run_tests.py's run_ir phases, compared with the source interpreter's
output; these tests check particular decisions of the interpreter on small programs."""

from __future__ import annotations

import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.interpreter.treewalk import QuestRuntimeError
from quest.interpreter.ir_interp import run_unit
from quest.ir.lower import lower_program
from quest.ir.verify import verify_unit
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)


def run(source: str) -> str:
    """The output of running source's Core IR, which prints the last phrase's result."""
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = lower_program(res.artifacts["typecheck"], ctx.env, print_result=True)
    problems = verify_unit(unit)
    assert not problems, problems
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        run_unit(unit, ctx.runtime_env)
    return out.getvalue()


class TestInterpreter(unittest.TestCase):
    def test_a_closure_keeps_its_loop_iteration_values(self) -> None:
        out = run(
            "let z = fun(): Int 0; let fs = array of z z z end; "
            "for i = 0 upto 2 do fs[i] := fun(): Int i * 10 end; "
            "fs[0]() + fs[1]() + fs[2]()"
        )
        self.assertEqual(out, "30 : Int\n")

    def test_mutable_variables_by_address(self) -> None:
        out = run("let incr(var v: Int): Ok = v := v + 1; let var g = 0; incr(@g); incr(@g); g")
        self.assertEqual(out, "2 : Int\n")

    def test_raising_a_handlers_exception_keeps_its_payload(self) -> None:
        out = run(
            "exception E: Int end; exception F end; "
            "let f(): Int = try try raise E with 7 end when F then 0 end when E with n then n end; f()"
        )
        self.assertEqual(out, "7 : Int\n")

    def test_a_declared_exception_read_before_it_is_made(self) -> None:
        with self.assertRaises(QuestRuntimeError):
            run(
                "let f(c: Bool): Int = begin "
                "let e: Exception = if c then exception I end else exception J end end; "
                "try raise I end when I then 1 when J then 2 end end; f(false)"
            )

    def test_library_modules(self) -> None:
        # The standard library's modules are loaded and run by the source interpreter
        out = run("import list: List; list.length(:Int list.cons(:Int 1 list.cons(:Int 2 list.nil(:Int))))")
        self.assertEqual(out, "2 : Int\n")


if __name__ == "__main__":
    unittest.main()
