"""Whether values laid out natively agree with the layout generic code gives them (generic_layout_agrees)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
# Checks canonical forms, as the other tests do (see helpers.py)
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import quest.syntax.ast as ast
from quest.codegen.c_types import generic_layout_agrees, generic_layout_copies_mutable_data
from quest.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.env import Environment, TypeSymbol
from quest.pipeline import compile_pipeline
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


class TestGenericLayoutsCopyingMutableData(TestGenericLayoutAgrees):
    def copies(self, generic: str, arg: str) -> bool:
        return generic_layout_copies_mutable_data(
            elaborate_test_type(generic, self.env), {self.a.symbol_id: elaborate_test_type(arg, self.env)}
        )

    def test_mutable_data_whose_layout_differs(self) -> None:
        for generic in ("Array(Box(A))", "Array(A)", "Tuple var x: A end", "Var(Box(A))", "Box(Array(Box(A)))"):
            with self.subTest(generic=generic):
                self.assertTrue(self.copies(generic, "P"))
                self.assertFalse(self.copies(generic, "Bool"))

    def test_immutable_data_is_copied(self) -> None:
        for generic in ("Box(A)", "List(A)", "Tree(A)", "Tuple f: All(x: A) A end"):
            with self.subTest(generic=generic):
                self.assertFalse(self.copies(generic, "P"))


class TestPolymorphicCallsInC(unittest.TestCase):
    """The code generated for values passed to and returned from polymorphic functions."""

    PRELUDE = """
        Let P = Record a: Int end;
        Let Box = Fun(A::TYPE) Tuple x: A end;
        let mkBox(A::TYPE v: A): Box(A) = tuple let x = v end;
        let getBox(A::TYPE b: Box(A)): A = b.x;
        let mkB: All(A::TYPE v: A) Box(A) = mkBox;
    """

    def generate(self, source: str):
        return compile_pipeline().execute(self.PRELUDE + source, "<test>")

    def c_code(self, source: str) -> str:
        res = self.generate(source)
        self.assertTrue(res.success, [d.message for d in res.diagnostics])
        return res.artifacts["codegen_c"]

    def test_agreeing_layouts_are_cast(self) -> None:
        main = self.c_code("let b: Box(Bool) = mkBox(:Bool true); getBox(:Bool b)").split("int main")[1]
        self.assertIn("((QTuple_Bool *)", main)
        self.assertIn("((QTuple_QVal *)", main)
        self.assertNotIn("quest_convert(", main)

    def test_differing_layouts_are_converted(self) -> None:
        main = self.c_code("let b: Box(P) = mkB(:P record a = 1 end); b.x.a").split("int main")[1]
        self.assertIn("quest_convert(", main)

    def test_mutable_data_is_not_copied(self) -> None:
        for source in (
            "let first(A::TYPE a: Array(Box(A))): A = a[0].x;"
            "let f: All(A::TYPE a: Array(Box(A))) A = first;"
            "f(:P array of mkBox(:P record a = 5 end) end).a",
            "let set(A::TYPE t: Tuple var x: A end v: A): Ok = t.x := v;"
            "let f: All(A::TYPE t: Tuple var x: A end v: A) Ok = set;"
            "f(:P tuple let var x = record a = 1 end end record a = 2 end)",
        ):
            with self.subTest(source=source):
                res = self.generate(source)
                self.assertFalse(res.success)
                self.assertIn("would copy mutable data", " ".join(d.message for d in res.diagnostics))


if __name__ == "__main__":
    unittest.main()
