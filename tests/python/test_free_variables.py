"""Free-variable metadata follows each binder's substitution rules, and substitution preserves sharing."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.types import (
    INT_TYPE,
    TYPE_KIND,
    QAllType,
    QArrayType,
    QAutoType,
    QFunType,
    QParam,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecordField,
    QRecType,
    QTupleField,
    QTupleType,
    QTupleTypeFormal,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QTypeMeta,
    QTypeVar,
    structurally_equal,
)

A = QTypeVar("A", 501, TYPE_KIND)
B = QTypeVar("B", 502, TYPE_KIND)


def fv(t) -> list[int]:
    return sorted(t._fv)


class TestFreeVariables(unittest.TestCase):
    def test_composites_union_their_parts(self) -> None:
        self.assertEqual(fv(QFunType((QParam("x", A),), QArrayType(B))), [501, 502])
        self.assertEqual(fv(QTypeApp(A, (B, INT_TYPE))), [501, 502])
        self.assertEqual(fv(INT_TYPE), [])

    def test_binders_remove_their_own_ids(self) -> None:
        self.assertEqual(fv(QRecType("A", 501, TYPE_KIND, QTupleType((A, B)))), [502])
        self.assertEqual(fv(QTypeFun((QTypeFormal("A", 501, TYPE_KIND),), QTupleType((A, B)))), [502])
        group = QRecGroupType((("A", 501, TYPE_KIND, QTupleType((B,))), ("B", 502, TYPE_KIND, QTupleType((A,)))))
        self.assertEqual(fv(group), [])
        auto = QAutoType("A", 501, TYPE_KIND, (QRecordField("f", A), QRecordField("g", B)))
        self.assertEqual(fv(auto), [502])

    def test_quantifier_bounds_are_outside_the_binder(self) -> None:
        # All(A <: B) A: the bound sees B; the body's A is bound.
        t = QAllType((QQuantifier("A", 501, QPowerKind(B)),), A)
        self.assertEqual(fv(t), [502])
        # All(A <: A) Int: a quantifier's own id in its bound is free (substitute does not remove it there).
        self.assertEqual(fv(QAllType((QQuantifier("A", 501, QPowerKind(A)),), INT_TYPE)), [501])

    def test_tuple_formals_bind_later_components(self) -> None:
        # Tuple A::POWER(B) x: A end
        t = QTupleType((QTupleTypeFormal("A", 501, QPowerKind(B)), QTupleField("x", A)))
        self.assertEqual(fv(t), [502])
        # Tuple y: A  A::TYPE end: the earlier field's A is free.
        t2 = QTupleType((QTupleField("y", A), QTupleTypeFormal("A", 501, TYPE_KIND)))
        self.assertEqual(fv(t2), [501])

    def test_unrelated_substitution_returns_self(self) -> None:
        t = QFunType((QParam("x", A),), QArrayType(B))
        self.assertIs(t.substitute({999: INT_TYPE}), t)
        replaced = t.substitute({501: INT_TYPE})
        self.assertIs(replaced.params[0].type_val, INT_TYPE)
        self.assertIs(replaced.result_type, t.result_type)

    def test_metavariables_are_never_skipped(self) -> None:
        meta = QTypeMeta()
        t = QArrayType(meta)
        self.assertTrue(t._has_meta)
        meta.instance = INT_TYPE
        resolved = t.substitute({})
        self.assertIs(resolved.element_type, INT_TYPE)

    def test_structural_equality(self) -> None:
        self.assertTrue(structurally_equal(QTupleType((A, INT_TYPE)), QTupleType((A, INT_TYPE))))
        self.assertFalse(structurally_equal(QTupleType((A,)), QTupleType((B,))))
        rec1 = QRecType("A", 501, TYPE_KIND, QTupleType((A,)))
        rec2 = QRecType("A", 501, TYPE_KIND, QTupleType((A,)))
        rec1.unfold_lazily()
        self.assertTrue(structurally_equal(rec1, rec2))


if __name__ == "__main__":
    unittest.main()
