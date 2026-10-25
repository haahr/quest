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

    def test_user_infix_operator_is_a_call(self) -> None:
        expr = desugar(parse_expr("a <+> b"))
        self.assertEqual(
            expr,
            ast.ExprApp(
                func=ast.ExprId(name="<+>", offset=0),
                args=(ast.ExprId(name="a", offset=0), ast.ExprId(name="b", offset=6)),
                offset=0,
            ),
        )

    def test_builtin_infix_operators_stay_infix(self) -> None:
        for op in ("+", "<>", "++", "/\\", "is", "isnot", "==", ":="):
            expr = parse_expr(f"a {op} b")
            self.assertIs(desugar(expr), expr, op)

    def test_index_assignment(self) -> None:
        expr = desugar(parse_expr("a[i] := v"))
        self.assertEqual(
            expr,
            ast.ExprIndexAssign(
                target=ast.ExprId(name="a", offset=0),
                index=ast.ExprId(name="i", offset=2),
                value=ast.ExprId(name="v", offset=8),
                offset=0,
            ),
        )

    def test_let_with_parameters_is_a_function_value(self) -> None:
        source = "let var f(x: Int): Int = x;"
        binding = desugar(parse_phrase(source, target="program")).phrases[0]
        self.assertIsInstance(binding, ast.LetValueBinding)
        self.assertEqual((binding.name, binding.params, binding.type_annot, binding.is_var), ("f", (), None, True))
        fun = binding.value
        self.assertIsInstance(fun, ast.ExprFun)
        self.assertEqual(fun.offset, binding.offset)
        self.assertEqual([p.name for p in fun.params], ["x"])
        self.assertEqual(fun.return_type, ast.TypePath(path=("Int",), offset=source.index("Int =")))

    def test_simultaneous_let_members_with_parameters(self) -> None:
        group = desugar(parse_phrase("let f(x: Int): Int = x and g(y: Int): Int = y;", target="program")).phrases[0]
        self.assertIsInstance(group, ast.LetValueBindingGroup)
        self.assertTrue(all(isinstance(m.value, ast.ExprFun) and not m.params for m in group.bindings))

    def test_recursive_and_external_lets_keep_their_parameters(self) -> None:
        for source in (
            "let rec f(x: Int): Int = f(x);",
            "let rec f(x: Int): Int = x and g(y: Int): Int = f(y);",
            'let f(x: Int): Int = external "f";',
        ):
            program = parse_phrase(source, target="program")
            self.assertIs(desugar(program), program, source)

    def test_nested_sugar_is_desugared(self) -> None:
        program = desugar(parse_phrase("let f = fun(): Int if a then 1 elsif b then 2 else 3 end;", target="program"))
        fun = program.phrases[0].value
        self.assertEqual(fun.body.elsifs, ())
        self.assertIsInstance(fun.body.else_branch, ast.ExprIf)


if __name__ == "__main__":
    unittest.main()
