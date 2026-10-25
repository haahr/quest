"""Whether values laid out natively agree with the layout generic code gives them (generic_layout_agrees): in
memory always, since every slot is one word, except where generic code views a bounded type parameter's values at
its bound; in registers and cells, only where the representations do."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
# Checks canonical forms, as the other tests do (see helpers.py)
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import quest.syntax.ast as ast
from quest.codegen.layout import generic_layout_agrees, generic_layout_copies_mutable_data
from quest.typechecker.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.types.env import Environment, TypeSymbol
from quest.pipeline import compile_pipeline
from quest.types import TYPE_KIND, QPowerKind, QTypeVar
from tests.python.helpers import elaborate_test_type, parse_phrase


# Where a program's main begins in its C (a prototype of it may come earlier)
MAIN_DEFINITION = "int main(int argc, char **argv) {"


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
            "Let Q = Record a: Int b: Int end;",
            "Let V = Variant p: Int q: Bool end;",
        ):
            binding = parse_phrase(source)
            if isinstance(binding, ast.TypeBindingGroup):
                elaborate_type_binding_group(binding, self.env)
            else:
                elaborate_type_binding(binding, self.env)
        # A type parameter bounded by a record type, whose values generic code views at the bound
        self.c = self.declare_param("C", QPowerKind(elaborate_test_type("P", self.env)))

    def declare_param(self, name: str, kind) -> QTypeVar:
        symbol = self.env.current_scope.declare_type(
            TypeSymbol(name=name, symbol_id=self.env.fresh_symbol_id(), kind=kind)
        )
        return QTypeVar(name=name, symbol_id=symbol.symbol_id, bound=kind)

    def agrees(self, generic: str, arg: str, param: QTypeVar | None = None) -> bool:
        param = param or self.a
        return generic_layout_agrees(elaborate_test_type(generic, self.env), {param.symbol_id: elaborate_test_type(arg, self.env)})

    def test_every_value_agrees_in_memory(self) -> None:
        # Every slot is one word: scalars and pointers in their bits, records and variants boxed
        for generic in ("Tuple x: A end", "Box(A)", "Maybe(A)", "Option none some with value: A end end", "List(A)",
                        "Tree(A)", "Forest(A)", "Tuple first: Box(A) second: Int end", "Array(Box(A))", "Array(A)",
                        "Tuple var x: A end"):
            for arg in ("Int", "Real", "Bool", "Char", "String", "Box(Int)", "List(Bool)", "All(x: Int) Bool", "P",
                        "V", "Box(P)"):
                with self.subTest(generic=generic, arg=arg):
                    self.assertTrue(self.agrees(generic, arg))

    def test_in_registers_only_integers_and_pointers_agree(self) -> None:
        for arg, agrees, in_cell in (("Int", True, True), ("String", True, True), ("Box(Bool)", True, True),
                                     ("Real", False, True), ("Bool", False, False), ("Char", False, False),
                                     ("P", False, True)):
            with self.subTest(arg=arg):
                self.assertEqual(self.agrees("Tuple f: All(x: A) A end", arg), agrees)
                # A var parameter points to a cell: natively a variable of the value's representation, a record boxed
                self.assertEqual(self.agrees("Tuple f: All(var x: A) Int end", arg), in_cell)

    def test_types_without_the_parameter_agree(self) -> None:
        self.assertTrue(self.agrees("Tuple x: P y: V end", "P"))

    def test_bounded_parameter_is_stored_as_its_bound(self) -> None:
        b = self.declare_param("B", QPowerKind(elaborate_test_type("Int", self.env)))
        self.assertTrue(self.agrees("Box(B)", "Int", b))
        # Viewed at the bound, which a record of another type is not
        self.assertFalse(self.agrees("Box(C)", "Q", self.c))


class TestGenericLayoutsCopyingMutableData(TestGenericLayoutAgrees):
    def copies(self, generic: str, arg: str, param: QTypeVar | None = None) -> bool:
        param = param or self.a
        return generic_layout_copies_mutable_data(
            elaborate_test_type(generic, self.env), {param.symbol_id: elaborate_test_type(arg, self.env)}
        )

    def test_mutable_data_whose_layout_differs(self) -> None:
        for generic in ("Array(Box(C))", "Array(C)", "Var(Box(C))", "Box(Array(Box(C)))"):
            with self.subTest(generic=generic):
                self.assertTrue(self.copies(generic, "Q", self.c))
        # A tuple is converted through a proxy, which shares its var components
        self.assertFalse(self.copies("Tuple var x: C end", "Q", self.c))
        for generic in ("Array(Box(A))", "Array(A)", "Tuple var x: A end", "Var(Box(A))", "Box(Array(Box(A)))"):
            with self.subTest(generic=generic):
                self.assertFalse(self.copies(generic, "P"))
                self.assertFalse(self.copies(generic, "Bool"))
        # A closure returning a value a register holds differently from a QVal, in mutable data
        self.assertTrue(self.copies("Array(All(x: Int) A)", "Bool"))

    def test_immutable_data_is_copied(self) -> None:
        for generic in ("Box(C)", "List(C)", "Tree(C)"):
            with self.subTest(generic=generic):
                self.assertFalse(self.copies(generic, "Q", self.c))
        self.assertFalse(self.copies("Tuple f: All(x: A) A end", "P"))


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
        main = self.c_code("let b: Box(Bool) = mkBox(:Bool true); getBox(:Bool b)").split(MAIN_DEFINITION)[1]
        self.assertIn("((QTuple_Bool *)", main)
        self.assertIn("((QTuple_QVal *)", main)
        self.assertNotIn("quest_convert(", main)

    def test_records_agree_in_slots(self) -> None:
        # A record in a slot is boxed, as a QVal holds it
        main = self.c_code("let b: Box(P) = mkB(:P record a = 1 end); b.x.a").split(MAIN_DEFINITION)[1]
        self.assertNotIn("quest_convert(", main)

    def test_differing_layouts_are_converted(self) -> None:
        main = self.c_code(
            "Let Q = Record a: Int b: Int end;"
            "let mkC(C <: P v: C): Box(C) = tuple let x = v end;"
            "let mkCF: All(C <: P v: C) Box(C) = mkC;"
            "let b: Box(Q) = mkCF(:Q record a = 1 b = 2 end); b.x.b"
        ).split(MAIN_DEFINITION)[1]
        self.assertIn("quest_convert(", main)

    def test_mutable_data_is_not_copied(self) -> None:
        for source in (
            "Let Q = Record a: Int b: Int end;"
            "let first(C <: P a: Array(Box(C))): C = a[0].x;"
            "let f: All(C <: P a: Array(Box(C))) C = first;"
            "f(:Q array of mkBox(:Q record a = 5 b = 6 end) end).b",
        ):
            with self.subTest(source=source):
                res = self.generate(source)
                self.assertFalse(res.success)
                self.assertIn("would copy mutable data", " ".join(d.message for d in res.diagnostics))


if __name__ == "__main__":
    unittest.main()
