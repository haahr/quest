"""The IR's nodes, textual form, and verifier, on hand-built units (quest/ir,
docs/ir.md)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.ir import nodes as ir
from quest.ir.printer import format_unit
from quest.ir.shapes import shape
from quest.ir.verify import verify_unit
from quest.types import BOOL_TYPE, INT_TYPE, OK_TYPE, QFunType, QParam

INT = shape(INT_TYPE)
BOOL = shape(BOOL_TYPE)


def var(hint: str, t=INT_TYPE, mutable: bool = False) -> ir.Var:
    return ir.Var(hint, t, mutable)


def const(v) -> ir.Const:
    return ir.Const(v, INT if isinstance(v, int) and not isinstance(v, bool) else BOOL)


def body(*statements) -> ir.Body:
    return ir.Body(list(statements))


def abs_function() -> ir.Funs:
    """fun abs(n: Int): Int = if n < 0 then 0 - n else n"""
    fun_t = QFunType(params=(QParam("n", INT_TYPE),), result_type=INT_TYPE)
    n = var("n")
    neg = var("", BOOL_TYPE)
    r = var("r")
    m = var("")
    f = var("abs", fun_t)
    join_body = body(
        ir.Let(neg, ir.Prim("<", (n, const(0)))),
        ir.If(neg, body(ir.Let(m, ir.Prim("-", (const(0), n))), ir.Jump("k", (m,))), body(ir.Jump("k", (n,)))),
    )
    fb = body(ir.Join("k", (r,), body(ir.Return(r)), join_body))
    return ir.Funs((ir.Function(f, (), ((n, "value"),), INT_TYPE, fb),))


class TestIrNodes(unittest.TestCase):
    def test_a_well_formed_unit_prints_and_verifies(self) -> None:
        funs = abs_function()
        x = var("x")
        call = ir.Let(x, ir.Call(funs.functions[0].var, (), (const(-3),)))
        unit = ir.Unit(main=body(funs, call, ir.Echo(x, INT_TYPE)))
        self.assertEqual(verify_unit(unit), [])
        self.assertEqual(
            format_unit(unit),
            "main {\n"
            "  funs {\n"
            "    fun abs(n: Int): Int {\n"
            "      join k(r: Int) {\n"
            "        return r\n"
            "      } in {\n"
            "        let %1: Bool = prim <(n, 0)\n"
            "        if %1 {\n"
            "          let %2: Int = prim -(0, n)\n"
            "          jump k(%2)\n"
            "        } else {\n"
            "          jump k(n)\n"
            "        }\n"
            "      }\n"
            "    }\n"
            "  }\n"
            "  let x: Int = call abs(-3)\n"
            "  echo \"\" x : Int\n"
            "}\n",
        )

    def test_use_outside_scope(self) -> None:
        x, y = var("x"), var("y")
        inner = body(ir.Let(x, const(1)))
        unit = ir.Unit(main=body(ir.If(const(True), inner, body()), ir.Let(y, x)))
        self.assertTrue(any("'x' is used outside its scope" in p for p in verify_unit(unit)))

    def test_bound_twice(self) -> None:
        x = var("x")
        unit = ir.Unit(main=body(ir.Let(x, const(1)), ir.Let(x, const(2))))
        self.assertTrue(any("bound more than once" in p for p in verify_unit(unit)))

    def test_closures_do_not_capture_mutable_locals(self) -> None:
        fun_t = QFunType(params=(), result_type=INT_TYPE)
        m = var("m", mutable=True)
        inner = ir.Function(var("g", fun_t), (), (), INT_TYPE, body(ir.Return(m)))
        outer_body = body(ir.VarDecl(m, const(0)), ir.Funs((inner,)), ir.Return(m))
        outer = ir.Function(var("f", fun_t), (), (), INT_TYPE, outer_body)
        problems = verify_unit(ir.Unit(main=body(ir.Funs((outer,)))))
        self.assertTrue(any("mutable variable 'm' of an enclosing function" in p for p in problems), problems)
        # A top-level mutable variable is a global, which functions may use
        g = var("g", mutable=True)
        reader = ir.Function(var("h", fun_t), (), (), INT_TYPE, body(ir.Return(g)))
        self.assertEqual(verify_unit(ir.Unit(main=body(ir.VarDecl(g, const(0)), ir.Funs((reader,))))), [])

    def test_jumps_breaks_and_returns(self) -> None:
        problems = verify_unit(ir.Unit(main=body(ir.Loop("L", body(ir.Break("M"))), ir.Jump("k", ()))))
        self.assertTrue(any("not an enclosing loop" in p for p in problems))
        self.assertTrue(any("not an enclosing join point" in p for p in problems))
        returns = verify_unit(ir.Unit(main=body(ir.Return(const(1)))))
        self.assertTrue(any("return outside a function" in p for p in returns))
        r = var("r")
        arity = verify_unit(ir.Unit(main=body(ir.Join("k", (r,), body(), body(ir.Jump("k", ()))))))
        self.assertTrue(any("passes 0 values for 1 parameters" in p for p in arity))

    def test_terminators_are_last(self) -> None:
        x = var("x")
        unit = ir.Unit(main=body(ir.Loop("L", body(ir.Break("L"), ir.Let(x, const(1))))))
        self.assertTrue(any("followed by other statements" in p for p in verify_unit(unit)))

    def test_recursive_functions_see_one_another(self) -> None:
        fun_t = QFunType(params=(), result_type=OK_TYPE)
        f, g = var("f", fun_t), var("g", fun_t)
        ok = ir.Const(None, shape(OK_TYPE))
        r1, r2 = var("r", OK_TYPE), var("r", OK_TYPE)
        ff = ir.Function(f, (), (), OK_TYPE, body(ir.Let(r1, ir.Call(g, (), ())), ir.Return(ok)))
        gg = ir.Function(g, (), (), OK_TYPE, body(ir.Let(r2, ir.Call(f, (), ())), ir.Return(ok)))
        self.assertEqual(verify_unit(ir.Unit(main=body(ir.Funs((ff, gg), recursive=True)))), [])
        # Without rec, f does not see g
        f2, g2 = var("f", fun_t), var("g", fun_t)
        ff2_body = body(ir.Let(var("r", OK_TYPE), ir.Call(g2, (), ())), ir.Return(ok))
        ff2 = ir.Function(f2, (), (), OK_TYPE, ff2_body)
        gg2 = ir.Function(g2, (), (), OK_TYPE, body(ir.Return(ok)))
        self.assertTrue(verify_unit(ir.Unit(main=body(ir.Funs((ff2, gg2))))))


if __name__ == "__main__":
    unittest.main()
