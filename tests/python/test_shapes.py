"""Shapes, the backend's view of types (quest/ir/shapes.py, docs/ir.md §4.1)."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import quest.syntax.ast as ast
from quest.config import CompilerOptions
from quest.typechecker.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.env import Environment, TypeSymbol, ValueSymbol
from quest.pipeline import default_pipeline
from quest.ir.shapes import KINDS, shape, shapes_reachable
from quest.typechecker.typed_ast import TypedNode
from quest.types import TYPE_KIND, QType, QTypeFun
from tests.python.helpers import elaborate_test_type, parse_phrase

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
# Programs whose types cover every kind of shape
SWEEP_PROGRAMS = (
    "tests/source/conversions/first_class.quest",
    "tests/source/conversions/dynamic.quest",
    "tests/source/language/recursive_type_operators.quest",
    "tests/source/language/type_parameters_in_aggregates.quest",
    "tests/source/modules/recursive_type_operators_in_interface.quest",
    "tests/source/modules/bounded_abstract_types.quest",
)


def _types_in(node, seen: set[int], out: list[QType]) -> None:
    if node is None or isinstance(node, (str, int, float, bool)) or id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, QType):
        out.append(node)
    elif isinstance(node, ValueSymbol):
        out.append(node.type_val)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _types_in(item, seen, out)
    elif isinstance(node, TypedNode):
        for f in dataclasses.fields(node):
            _types_in(getattr(node, f.name), seen, out)

DECLS = (
    "Let P = Record b: Bool a: Int end;",
    "Let Box = Fun(A::TYPE) Tuple x: A end;",
    "Let Pair = Fun(A::TYPE) Tuple first: Box(A) second: Int end;",
    "Let Rec List(A::TYPE) = Option nil cons with head: A tail: List(A) end end;",
    "Let FunList = Fun(A::TYPE) Rec(L::TYPE) Option nil cons with head: A tail: L end end;",
    "Let Rec IntList = Option nil cons with head: Int tail: IntList end end;",
    "Let Rec Tree = Variant leaf: Int node: Forest end and Forest = Tuple trees: Array(Tree) end;",
)


class TestShapes(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment()
        self.a = self.env.current_scope.declare_type(
            TypeSymbol(name="A", symbol_id=self.env.fresh_symbol_id(), kind=TYPE_KIND)
        )
        for source in DECLS:
            binding = parse_phrase(source)
            if isinstance(binding, ast.TypeBindingGroup):
                elaborate_type_binding_group(binding, self.env)
            else:
                elaborate_type_binding(binding, self.env)

    def s(self, source: str):
        return shape(elaborate_test_type(source, self.env))

    def test_scalars(self) -> None:
        for source, kind in (("Int", "int"), ("Real", "real"), ("Bool", "bool"), ("Char", "char"),
                             ("String", "string"), ("Ok", "ok")):
            with self.subTest(source=source):
                self.assertEqual(self.s(source).kind, kind)
                self.assertTrue(self.s(source).is_scalar)

    def test_aliases_and_applications_reduce(self) -> None:
        box = self.s("Box(Int)")
        self.assertEqual(box.kind, "tuple")
        self.assertEqual([c.name for c in box.components], ["x"])
        self.assertEqual(box.components[0].shape.kind, "int")
        self.assertIs(box, self.s("Tuple x: Int end"))
        pair = self.s("Pair(Bool)")
        self.assertEqual(pair.component("first").shape.component("x").shape.kind, "bool")
        record = self.s("P")
        self.assertEqual(record.kind, "record")
        self.assertEqual([c.name for c in record.sorted_components()], ["a", "b"])

    def test_equal_types_share_one_shape(self) -> None:
        self.assertIs(self.s("List(Int)"), self.s("FunList(Int)"))
        self.assertIs(self.s("List(Int)"), self.s("IntList"))
        self.assertIsNot(self.s("List(Int)"), self.s("List(Bool)"))

    def test_recursion_is_a_cycle(self) -> None:
        lst = self.s("List(Int)")
        self.assertEqual(lst.kind, "option")
        cons = lst.case("cons").shape
        self.assertEqual(cons.kind, "tuple")
        self.assertIs(cons.component("tail").shape, lst)
        self.assertIsNone(lst.case("nil").shape)
        tree = self.s("Tree")
        forest = tree.case("node").shape
        self.assertEqual(forest.kind, "tuple")
        self.assertIs(forest.component("trees").shape.element, tree)

    def test_type_parameters_functions_and_quantifiers(self) -> None:
        a = self.s("A")
        self.assertEqual((a.kind, a.symbol_id), ("typevar", self.a.symbol_id))
        fun = self.s("All(x: A var y: Int) Bool")
        self.assertEqual(fun.kind, "fun")
        self.assertEqual(
            [(p.name, p.mode, p.shape.kind) for p in fun.params], [("x", "value", "typevar"), ("y", "var", "int")]
        )
        self.assertEqual(fun.result.kind, "bool")
        poly = self.s("All(B::TYPE C <: P x: C) B")
        self.assertEqual(poly.kind, "all")
        b, c = poly.type_params
        self.assertIsNone(b.bound)
        self.assertEqual(c.bound.kind, "record")
        self.assertEqual(poly.body.result.symbol_id, b.symbol_id)

    def test_other_kinds(self) -> None:
        self.assertEqual(self.s("Array(Box(Int))").element.kind, "tuple")
        self.assertEqual(self.s("Var(Int)").element.kind, "int")
        existential = self.s("Tuple B::TYPE v: B n: Int end")
        self.assertEqual([c.name for c in existential.components], ["v", "n"])
        self.assertEqual(existential.components[0].shape.kind, "typevar")
        variant = self.s("Variant p: Int q: Ok end")
        self.assertEqual([(c.name, c.shape.kind) for c in variant.cases], [("p", "int"), ("q", "ok")])

    def test_every_reachable_shape_is_complete(self) -> None:
        for source in ("List(Box(Int))", "Tree", "Pair(List(Bool))", "All(B::TYPE x: List(B)) Array(B)"):
            with self.subTest(source=source):
                for s in shapes_reachable(self.s(source)):
                    self.assertIn(s.kind, KINDS)


    def test_every_type_of_some_programs_has_a_shape(self) -> None:
        kinds: set[str] = set()
        for program in SWEEP_PROGRAMS:
            path = ROOT_DIR / program
            # Named by its path, so that the interfaces and modules beside it are found
            options = CompilerOptions(stop_after="typecheck")
            res = default_pipeline().execute(path.read_text(), str(path), options=options)
            self.assertTrue(res.success, program)
            types: list[QType] = []
            _types_in(res.artifacts["typecheck"], set(), types)
            for t in types:
                # Type operators (in type declarations) are not the types of values, and have no shapes
                if isinstance(t, QTypeFun) or getattr(t, "_has_meta", False):
                    continue
                kinds.update(s.kind for s in shapes_reachable(shape(t)))
        # (Abstract types of modules are type variables too: see the typevar kind)
        self.assertLessEqual({"tuple", "record", "variant", "option", "array", "fun", "all", "auto", "typevar"}, kinds)


if __name__ == "__main__":
    unittest.main()
