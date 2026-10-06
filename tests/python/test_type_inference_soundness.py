"""Soundness checks for implicit type argument inference and the subtyping proof trail."""

from __future__ import annotations

import dataclasses
import gc
import os
import sys
import unittest
import weakref

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.pipeline import CompilerOptions, default_pipeline
from quest.types import (
    INT_TYPE,
    TYPE_KIND,
    QAbstractType,
    QPathType,
    QTupleType,
    QTypeMeta,
    QTypeVar,
    SubtypeTrail,
    resolve_metas,
    unsolved_metas,
)


def _typecheck(source: str):
    result = default_pipeline().execute(source, "<test>", options=CompilerOptions(stop_after="typecheck"))
    return result


def _count_metas(root) -> int:
    count = 0
    seen: set[int] = set()

    def walk(node) -> None:
        nonlocal count
        if node is None or isinstance(node, (str, int, float, bool)) or id(node) in seen:
            return
        seen.add(id(node))
        if isinstance(node, QTypeMeta):
            count += 1
        elif isinstance(node, (tuple, list)):
            for item in node:
                walk(item)
        elif dataclasses.is_dataclass(node):
            for f in dataclasses.fields(node):
                walk(getattr(node, f.name))

    walk(root)
    return count


class TestImplicitTypeArguments(unittest.TestCase):
    def test_no_metavariables_remain_in_typed_ast(self) -> None:
        source = (
            "import list: List;\n"
            "let a = list.cons(3 list.nil());\n"
            "let b: list.T(Int) = list.nil();\n"
            "let c = list.cons(list.nil() list.cons(list.cons(1 list.nil()) list.nil()));\n"
            "let n: Int = extent array of 1 2 3 end;\n"
        )
        result = _typecheck(source)
        self.assertTrue(result.success, [d.message for d in result.diagnostics])
        self.assertEqual(_count_metas(result.artifacts["typecheck"]), 0)

    def test_uninferable_type_argument_is_an_error(self) -> None:
        result = _typecheck("import list: List;\nlet l = list.nil();\n")
        self.assertFalse(result.success)
        self.assertIn("Cannot infer type argument 'A'", " ".join(d.message for d in result.diagnostics))

    def test_resolve_metas_replaces_solved_metavariables(self) -> None:
        meta = QTypeMeta()
        t = QTupleType((meta, INT_TYPE))
        self.assertEqual(unsolved_metas(t), [meta])
        meta.instance = INT_TYPE
        self.assertEqual(unsolved_metas(t), [])
        resolved = resolve_metas(t)
        self.assertIs(resolved.elements[0], INT_TYPE)
        self.assertIs(resolve_metas(resolved), resolved)


class TestSubtypeTrail(unittest.TestCase):
    def test_named_types_are_keyed_by_symbol(self) -> None:
        a1 = QTypeVar("A", 7, TYPE_KIND)
        a2 = QAbstractType("A", 7, TYPE_KIND)
        self.assertEqual(SubtypeTrail.key(a1), SubtypeTrail.key(a2))
        p1 = QPathType("x", 3, "T", TYPE_KIND)
        p2 = QPathType("x", 3, "T", TYPE_KIND)
        self.assertEqual(SubtypeTrail.key(p1), SubtypeTrail.key(p2))
        self.assertNotEqual(SubtypeTrail.key(p1), SubtypeTrail.key(QPathType("x", 3, "U", TYPE_KIND)))

    def test_structural_types_are_keyed_by_identity(self) -> None:
        t1 = QTupleType((INT_TYPE,))
        t2 = QTupleType((INT_TYPE,))
        self.assertNotEqual(SubtypeTrail.key(t1), SubtypeTrail.key(t2))

    def test_assumed_types_stay_alive(self) -> None:
        trail = SubtypeTrail()
        sub = QTupleType((INT_TYPE,))
        sup = QTupleType((INT_TYPE, INT_TYPE))
        pair = trail.pair(sub, sup)
        trail.assume(pair, sub, sup)
        sub_ref, sup_ref = weakref.ref(sub), weakref.ref(sup)
        del sub, sup
        gc.collect()
        # While the trail lives, the ids in its keys cannot be reused by other objects.
        self.assertIsNotNone(sub_ref())
        self.assertIsNotNone(sup_ref())
        self.assertIn(pair, trail)


if __name__ == "__main__":
    unittest.main()
