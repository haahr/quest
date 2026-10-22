"""Whether values laid out natively agree with the layout generic code gives them (generic_layout_agrees)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
# Checks canonical forms, as the other tests do (see helpers.py)
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import quest.syntax.ast as ast
from quest.codegen.c_types import generic_layout_agrees
from quest.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.env import Environment, TypeSymbol
from quest.types import TYPE_KIND, QPowerKind, QTypeVar
from tests.python.helpers import elaborate_test_type, parse_phrase


class TestGenericLayoutAgrees(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment()
        self.a = self.declare_param("A", TYPE_KIND)
        for source in (
            "Let Box = Fun(A::TYPE) Tuple x: A end;",
            "Let Maybe = Fun(A::TYPE) Option none some with value: A end end;",
            "Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end;",
            "Let Rec Tree(A::TYPE) = Variant leaf: A node: Forest(A) end and Forest(A::TYPE) = Tuple trees: List(Tree(A)) end;",
            "Let P = Record a: Int end;",
            "Let V = Variant p: Int q: Bool end;",
        ):
            binding = parse_phrase(source)
            if isinstance(binding, ast.TypeBindingGroup):
                elaborate_type_binding_group(binding, self.env)
            else:
                elaborate_type_binding(binding, self.env)

    def declare_param(self, name: str, kind) -> QTypeVar:
        symbol = self.env.current_scope.declare_type(
            TypeSymbol(name=name, symbol_id=self.env.fresh_symbol_id(), kind=kind)
        )
        return QTypeVar(name=name, symbol_id=symbol.symbol_id, bound=kind)

    def agrees(self, generic: str, arg: str, param: QTypeVar | None = None) -> bool:
        param = param or self.a
        return generic_layout_agrees(elaborate_test_type(generic, self.env), {param.symbol_id: elaborate_test_type(arg, self.env)})

    def test_scalars_and_pointers_agree_in_memory(self) -> None:
        for generic in ("Tuple x: A end", "Box(A)", "Maybe(A)", "Option none some with value: A end end", "List(A)",
                        "Tree(A)", "Forest(A)", "Tuple first: Box(A) second: Int end", "Array(Box(A))"):
            for arg in ("Int", "Real", "Bool", "Char", "String", "Box(Int)", "List(Bool)", "All(x: Int) Bool"):
                with self.subTest(generic=generic, arg=arg):
                    self.assertTrue(self.agrees(generic, arg))

    def test_records_and_variants_do_not(self) -> None:
        for generic in ("Box(A)", "Maybe(A)", "List(A)", "Tree(A)", "Forest(A)", "Tuple first: Box(A) end"):
            for arg in ("P", "V"):
                with self.subTest(generic=generic, arg=arg):
                    self.assertFalse(self.agrees(generic, arg))

    def test_in_registers_only_integers_and_pointers_agree(self) -> None:
        for arg, agrees in (("Int", True), ("String", True), ("Box(Bool)", True), ("Real", False), ("Bool", False),
                            ("Char", False), ("P", False)):
            with self.subTest(arg=arg):
                self.assertEqual(self.agrees("Tuple f: All(x: A) A end", arg), agrees)
                # A var parameter is a pointer to a slot, which agrees in memory
                self.assertEqual(self.agrees("Tuple f: All(var x: A) Int end", arg), arg != "P")

    def test_types_without_the_parameter_agree(self) -> None:
        self.assertTrue(self.agrees("Tuple x: P y: V end", "P"))

    def test_bounded_parameter_is_stored_as_its_bound(self) -> None:
        b = self.declare_param("B", QPowerKind(elaborate_test_type("Int", self.env)))
        self.assertTrue(self.agrees("Box(B)", "Int", b))
        p = self.declare_param("C", QPowerKind(elaborate_test_type("P", self.env)))
        self.assertFalse(self.agrees("Box(C)", "P", p))


if __name__ == "__main__":
    unittest.main()
