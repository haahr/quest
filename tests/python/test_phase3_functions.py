"""Unit tests for function typing that source text cannot express: a lambda or recursive function whose parameters
lack types, built as an AST, and an All type elaborated directly. Function typing expressed in source is the golden test
tests/source/language/core_functions."""

import unittest

import quest.ast as ast
from quest.diagnostics import QuestTypeError as TypeError
from quest.typechecker import check_expr, synth_expr
from quest.typed_ast import TypedFun
from quest.types import (
    INT_TYPE,
    QFunType,
    QParam,
)
from tests.python.helpers import (
    elaborate_test_type,
    parse_expr,
)


class Phase3FunctionsTest(unittest.TestCase):
    """Function typing on ASTs the grammar does not produce."""

    def test_fun_abstraction_checking_mode(self) -> None:
        """fun(x) x + 1 checked against (Int) -> Int infers parameter type."""
        expected_type = QFunType(params=(QParam("x", INT_TYPE),), result_type=INT_TYPE)
        # AST with unannotated parameter for checking mode
        fn_expr = ast.ExprFun(
            params=(
                ast.FormalParam(name="x", type_annot=None, mode=ast.ParamMode.VALUE),
            ),
            return_type=None,
            body=parse_expr("x + 1"),
        )
        typed = check_expr(fn_expr, expected_type)
        self.assertIsInstance(typed, TypedFun)
        self.assertEqual(typed.params[0].type_val, INT_TYPE)
        self.assertEqual(typed.type_val, expected_type)

    def test_let_rec_missing_param_type_raises_type_error(self) -> None:
        """let rec f(n) : Int = ... with unannotated parameter raises TypeError."""
        # Grammar requires parameter annotations, but typechecker defends against AST without annotations.
        binding = ast.LetValueBinding(
            name="fib",
            params=(
                ast.FormalParam(
                    name="n",
                    type_annot=None,
                    mode=ast.ParamMode.VALUE,
                ),
            ),
            type_annot=ast.TypePath(path=("Int",)),
            value=ast.ExprId(name="n"),
            is_rec=True,
        )
        block = ast.ExprBlock(bindings=(binding, ast.ExprStmt(expr=ast.ExprInt(value=1, lexeme="1"))))
        with self.assertRaises(TypeError) as ctx:
            synth_expr(block)
        self.assertIn(
            "Parameter 'n' in recursive function 'fib' requires an explicit type annotation",
            str(ctx.exception),
        )

    def test_all_type_as_function_type_elaboration(self) -> None:
        """All(y: Int) Int in elaborate_type elaborates to QFunType(y: Int) -> Int."""
        elaborated = elaborate_test_type("All(y: Int) Int")
        self.assertIsInstance(elaborated, QFunType)
        self.assertEqual(len(elaborated.params), 1)
        self.assertEqual(elaborated.params[0].name, "y")
        self.assertEqual(elaborated.params[0].type_val, INT_TYPE)
        self.assertEqual(elaborated.result_type, INT_TYPE)


if __name__ == "__main__":
    unittest.main()
