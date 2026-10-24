"""Recursive type operators: Let Rec T(A::K) = ... T(A) ..., alone or as a group, means Fun(A::K) Rec(T) ...."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
# Checks canonical forms, as the other tests do (see helpers.py)
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import quest.syntax.ast as ast
from quest.codegen.c_types import qtype_to_c_type, type_to_c_tag
from quest.typechecker.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.types.env import Environment
from quest.types import (
    TYPE_KIND,
    KindError,
    QAllKind,
    QRecGroupType,
    QRecType,
    QTypeFun,
    is_type_equal,
)
from tests.python.helpers import elaborate_test_type, parse_phrase


class TestRecursiveTypeOperators(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment()

    def declare(self, source: str) -> list:
        binding = parse_phrase(source)
        if isinstance(binding, ast.TypeBindingGroup):
            return elaborate_type_binding_group(binding, self.env)
        return [elaborate_type_binding(binding, self.env)]

    def assert_same_type(self, a: str, b: str) -> None:
        t1 = elaborate_test_type(a, self.env)
        t2 = elaborate_test_type(b, self.env)
        self.assertTrue(is_type_equal(t1, t2, self.env), f"{a} and {b} differ")
        self.assertEqual(qtype_to_c_type(t1), qtype_to_c_type(t2))
        self.assertEqual(type_to_c_tag(t1), type_to_c_tag(t2))

    def test_operator_is_a_function_returning_a_recursive_type(self) -> None:
        (lst,) = self.declare("Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end;")
        self.assertIsInstance(lst.kind, QAllKind)
        self.assertIs(lst.kind.result_kind, TYPE_KIND)
        self.assertIsInstance(lst.definition, QTypeFun)
        self.assertIsInstance(lst.definition.body, QRecType)
        self.assertEqual(
            str(lst.definition), "Fun(A :: TYPE) Rec(List :: TYPE) Option nil cons with Tuple head: A tail: List end end"
        )

    def test_applied_operator_equals_fun_rec_form_and_recursive_type(self) -> None:
        self.declare("Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end;")
        self.declare("Let FunList = Fun(A::TYPE) Rec(L::TYPE) Option nil cons with head: A tail: L end end;")
        self.declare("Let Rec IntList = Option nil cons with head: Int tail: IntList end end;")
        self.assert_same_type("List(Int)", "FunList(Int)")
        self.assert_same_type("List(Int)", "IntList")
        self.assertFalse(
            is_type_equal(elaborate_test_type("List(Int)", self.env), elaborate_test_type("List(Bool)", self.env))
        )

    def test_group_members_share_parameters_and_one_group(self) -> None:
        tree, forest = self.declare(
            "Let Rec Tree(A::TYPE) = Variant leaf: A node: Forest(A) end "
            "and Forest(A::TYPE) = Record trees: Array(Tree(A)) end;"
        )
        for member in (tree, forest):
            self.assertIsInstance(member.definition, QTypeFun)
            self.assertIsInstance(member.definition.body, QRecGroupType)
        self.assertIs(tree.definition.params, forest.definition.params)
        self.assertIs(tree.definition.body.bindings, forest.definition.body.bindings)
        self.assertEqual((tree.definition.body.active_index, forest.definition.body.active_index), (0, 1))

    def test_applied_group_equals_group_at_the_argument(self) -> None:
        self.declare(
            "Let Rec Tree(A::TYPE) = Variant leaf: A node: Forest(A) end "
            "and Forest(A::TYPE) = Record trees: Array(Tree(A)) end;"
        )
        self.declare(
            "Let Rec IntTree = Variant leaf: Int node: IntForest end "
            "and IntForest = Record trees: Array(IntTree) end;"
        )
        self.assert_same_type("Tree(Int)", "IntTree")
        self.assert_same_type("Forest(Int)", "IntForest")

    def test_operator_written_with_fun(self) -> None:
        self.declare("Let Rec Stream = Fun(A::TYPE) Option done more with head: A rest: Stream(A) end end;")
        self.declare("Let Rec Ints = Option done more with head: Int rest: Ints end end;")
        self.assert_same_type("Stream(Int)", "Ints")

    def test_non_uniform_recursion_is_rejected(self) -> None:
        for source in (
            "Let Rec Nest(A::TYPE) = Option nil cons with head: A tail: Nest(Array(A)) end end;",
            "Let Rec T(A::TYPE) = Variant leaf: A node: Array(T) end;",
            "Let Rec T(A::TYPE B::TYPE) = Variant leaf: A node: T(B A) end;",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(KindError, "non-uniform recursion"):
                self.declare(source)

    def test_shadowed_parameter_is_not_the_operators_own(self) -> None:
        with self.assertRaisesRegex(KindError, "non-uniform recursion"):
            self.declare("Let Rec T(A::TYPE) = Variant leaf: A node: Fun(A::TYPE) T(A) end;")

    def test_group_members_must_have_the_same_parameters(self) -> None:
        for source in (
            "Let Rec T(A::TYPE) = Array(U(A)) and U = Int;",
            "Let Rec T(A::TYPE) = Array(U(A)) and U(B::TYPE) = Array(T(B));",
            "Let Rec T(A::TYPE) = Array(U(A)) and U(A::TYPE B::TYPE) = Array(T(A));",
        ):
            with self.subTest(source=source), self.assertRaisesRegex(KindError, "same type parameters"):
                self.declare(source)


if __name__ == "__main__":
    unittest.main()
