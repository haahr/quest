"""Polymorphic functions checked against an expected type (a let-function's header, or an annotation): the function's
type is the expected one with its quantifiers renamed, and its parameters and body refer to those quantifiers."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.typed_ast import TypedFun
from quest.types import QAllType, QFunType
from tests.python.helpers import run_source


def _typed_funs(node: Any, found: list[TypedFun], seen: set[int]) -> list[TypedFun]:
    if id(node) in seen:
        return found
    seen.add(id(node))
    if isinstance(node, TypedFun):
        found.append(node)
    if isinstance(node, (tuple, list)):
        for item in node:
            _typed_funs(item, found, seen)
    elif dataclasses.is_dataclass(node) and not isinstance(node, type) and type(node).__module__ == "quest.typed_ast":
        for f in dataclasses.fields(node):
            _typed_funs(getattr(node, f.name), found, seen)
    return found


class TestCheckedPolymorphicFunctions(unittest.TestCase):
    def polymorphic_funs(self, source: str) -> list[TypedFun]:
        res = run_source(source, options=CompilerOptions(stop_after="typecheck"))
        self.assertTrue(res.success, [d.message for d in res.diagnostics])
        funs = [f for f in _typed_funs(res.artifacts["typecheck"], [], set()) if isinstance(f.type_val, QAllType)]
        self.assertTrue(funs)
        return funs

    def assert_consistent(self, fun: TypedFun) -> None:
        quants = fun.type_val.quantifiers
        self.assertEqual(fun.type_param_ids, tuple(q.symbol_id for q in quants))
        inner = fun.type_val.body
        if fun.params:
            self.assertIsInstance(inner, QFunType)
            for param, q_param in zip(fun.params, inner.params):
                self.assertEqual(param.type_val, q_param.type_val, f"parameter '{param.name}'")

    def test_let_function(self) -> None:
        for fun in self.polymorphic_funs("Let Box = Fun(A::TYPE) Tuple x: A end; let get(A::TYPE b: Box(A)): A = b.x;"):
            self.assert_consistent(fun)
            self.assertEqual(fun.type_val.quantifiers[0].name, "A")

    def test_annotated_literal_with_other_names(self) -> None:
        (fun,) = self.polymorphic_funs("let f: All(B::TYPE x: B) B = fun(A::TYPE x: A): A x;")
        self.assert_consistent(fun)
        self.assertEqual(fun.type_val.quantifiers[0].name, "A")

    def test_annotated_literal_without_type_parameters(self) -> None:
        (fun,) = self.polymorphic_funs("let f: All(B::TYPE x: B) B = fun(x: B): B x;")
        self.assert_consistent(fun)
        self.assertEqual(fun.type_val.quantifiers[0].name, "B")

    def test_bound_of_a_later_parameter_refers_to_the_renamed_earlier_one(self) -> None:
        (fun,) = self.polymorphic_funs("let g(A::TYPE B <: A x: B): A = x;")
        self.assert_consistent(fun)
        a, b = fun.type_val.quantifiers
        self.assertEqual(b.bound.bound.symbol_id, a.symbol_id)

    def test_body_is_checked_under_the_expected_bound(self) -> None:
        (fun,) = self.polymorphic_funs(
            "Let P = Record a: Int end; Let Q = Record a: Int b: Int end;"
            "let f: All(X <: Q x: X) Int = fun(X <: P x: X): Int x.a;"
        )
        self.assert_consistent(fun)
        self.assertEqual(str(fun.type_val.quantifiers[0].bound.bound), "Q")

    def test_nested_polymorphic_functions(self) -> None:
        funs = self.polymorphic_funs(
            "let outer(A::TYPE x: A): A = begin let inner(B::TYPE y: B): B = y; inner(:A x) end;"
        )
        self.assertEqual(len(funs), 2)
        for fun in funs:
            self.assert_consistent(fun)


if __name__ == "__main__":
    unittest.main()
