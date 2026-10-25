"""Unit tests for the desugaring pass (quest/syntax/desugar.py)."""

import unittest

import quest.syntax.ast as ast
from quest.syntax.desugar import desugar
from tests.python.helpers import parse_expr, parse_phrase


class TestDesugar(unittest.TestCase):
    """Each sugared form becomes its core form, positioned at the syntax it replaces."""

    def test_unchanged_node_is_returned_as_is(self) -> None:
        expr = parse_expr("begin let x = 1 + 2; if x is 3 then x end end")
        self.assertIs(desugar(expr), expr)

    def test_elsif_chain_with_else(self) -> None:
        source = "if a then 1 elsif b then 2 elsif c then 3 else 4 end"
        expr = desugar(parse_expr(source))
        self.assertIsInstance(expr, ast.ExprIf)
        self.assertEqual(expr.elsifs, ())
        inner = expr.else_branch
        self.assertIsInstance(inner, ast.ExprIf)
        self.assertEqual(inner.cond, ast.ExprId(name="b", offset=source.index("b then")))
        self.assertEqual(inner.offset, source.index("b then"))
        innermost = inner.else_branch
        self.assertIsInstance(innermost, ast.ExprIf)
        self.assertEqual(innermost.offset, source.index("c then"))
        self.assertIsInstance(innermost.else_branch, ast.ExprInt)
        self.assertEqual(innermost.else_branch.offset, source.index("4"))

    def test_elsif_chain_without_else_ends_with_ok(self) -> None:
        expr = desugar(parse_expr("if a then 1 elsif b then 2 end"))
        self.assertIsInstance(expr.else_branch, ast.ExprIf)
        self.assertEqual(expr.else_branch.else_branch, ast.ExprOk(offset=expr.offset))

    def test_if_without_elsif_or_else_stays_a_statement(self) -> None:
        expr = parse_expr("if a then 1 end")
        self.assertIs(desugar(expr), expr)
        self.assertIsNone(expr.else_branch)

    def test_andif(self) -> None:
        expr = desugar(parse_expr("a andif b"))
        self.assertEqual(
            expr,
            ast.ExprIf(
                cond=ast.ExprId(name="a", offset=0),
                then_branch=ast.ExprId(name="b", offset=8),
                else_branch=ast.ExprBool(value=False, offset=0),
                offset=0,
            ),
        )

    def test_orif(self) -> None:
        expr = desugar(parse_expr("a orif b"))
        self.assertEqual(
            expr,
            ast.ExprIf(
                cond=ast.ExprId(name="a", offset=0),
                then_branch=ast.ExprBool(value=True, offset=0),
                else_branch=ast.ExprId(name="b", offset=7),
                offset=0,
            ),
        )

    def test_nested_sugar_is_desugared(self) -> None:
        program = desugar(parse_phrase("let f = fun(): Int if a then 1 elsif b then 2 else 3 end;", target="program"))
        fun = program.phrases[0].value
        self.assertEqual(fun.body.elsifs, ())
        self.assertIsInstance(fun.body.else_branch, ast.ExprIf)


if __name__ == "__main__":
    unittest.main()
