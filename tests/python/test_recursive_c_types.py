"""C representations of recursive tuple, record, and variant types are those of their unfoldings."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.c_types import normalize_type, qtype_to_c_type, tuple_struct_name, type_to_c_tag
from quest.types import (
    INT_TYPE,
    TYPE_KIND,
    QArrayType,
    QRecGroupType,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QTypeVar,
    QVariantField,
    QVariantType,
    resolve_record_bound,
    resolve_variant_bound,
)


def _tree(name: str, symbol_id: int) -> QRecType:
    """Rec(T) Tuple v: Int kids: Array(T) end"""
    var = QTypeVar(name, symbol_id, TYPE_KIND)
    body = QTupleType((QTupleField("v", INT_TYPE), QTupleField("kids", QArrayType(var))))
    return QRecType(name, symbol_id, TYPE_KIND, body)


def _p_q() -> QRecGroupType:
    """Let Rec P = Tuple v: Int q: Array(Q) end and Q = Tuple w: Int p: Array(P) end"""
    p = QTypeVar("P", 9201, TYPE_KIND)
    q = QTypeVar("Q", 9202, TYPE_KIND)
    p_body = QTupleType((QTupleField("v", INT_TYPE), QTupleField("q", QArrayType(q))))
    q_body = QTupleType((QTupleField("w", INT_TYPE), QTupleField("p", QArrayType(p))))
    return QRecGroupType((("P", 9201, TYPE_KIND, p_body), ("Q", 9202, TYPE_KIND, q_body)), 0)


class TestRecursiveCTypes(unittest.TestCase):
    def test_recursive_tuple_is_its_unfoldings_struct_pointer(self) -> None:
        tree = _tree("Tree", 9301)
        unfolded = tree.unfold_lazily()
        self.assertIs(normalize_type(tree), unfolded)
        self.assertEqual(qtype_to_c_type(tree), f"{tuple_struct_name(unfolded)} *")
        # The struct of the unfolding names the recursive occurrence by the recursive type's own tag
        self.assertIn(type_to_c_tag(tree), tuple_struct_name(unfolded))

    def test_recursive_tags_are_alpha_invariant_and_distinct(self) -> None:
        self.assertEqual(type_to_c_tag(_tree("Tree", 9302)), type_to_c_tag(_tree("Other", 9303)))
        var = QTypeVar("X", 9304, TYPE_KIND)
        plain = QTupleType((QTupleField("v", INT_TYPE), QTupleField("kids", QArrayType(var))))
        self.assertNotEqual(type_to_c_tag(_tree("Tree", 9305)), type_to_c_tag(plain))

    def test_nested_recursive_variables_are_distinguished(self) -> None:
        """Rec(X) Tuple Array(Rec(Y) Tuple Array(X) end) end differs from the same with Array(Y) inside."""

        def nested(inner_refers_to_outer: bool) -> QRecType:
            x = QTypeVar("X", 9311, TYPE_KIND)
            y = QTypeVar("Y", 9312, TYPE_KIND)
            inner_body = QTupleType((QTupleField("a", QArrayType(x if inner_refers_to_outer else y)),))
            inner = QRecType("Y", 9312, TYPE_KIND, inner_body)
            return QRecType("X", 9311, TYPE_KIND, QTupleType((QTupleField("b", QArrayType(inner)),)))

        self.assertNotEqual(type_to_c_tag(nested(True)), type_to_c_tag(nested(False)))

    def test_mutually_recursive_tuples(self) -> None:
        p = _p_q()
        q = p.siblings()[1]
        self.assertIs(normalize_type(p), p.unfold_lazily())
        self.assertEqual(qtype_to_c_type(p), f"{tuple_struct_name(p.unfold_lazily())} *")
        self.assertEqual(qtype_to_c_type(q), f"{tuple_struct_name(q.unfold_lazily())} *")
        self.assertNotEqual(type_to_c_tag(p), type_to_c_tag(q))

    def test_recursive_record_and_variant_resolve_to_their_unfoldings(self) -> None:
        n = QTypeVar("N", 9321, TYPE_KIND)
        node_body = QRecordType((QRecordField("v", INT_TYPE), QRecordField("kids", QArrayType(n))))
        node = QRecType("N", 9321, TYPE_KIND, node_body)
        self.assertIs(resolve_record_bound(node), node.unfold_lazily())
        self.assertEqual(qtype_to_c_type(node), "QRecordVal")
        self.assertEqual(qtype_to_c_type(QArrayType(node)), "QArrayWideRecord *")

        e = QTypeVar("E", 9322, TYPE_KIND)
        expr_body = QVariantType((QVariantField("num", INT_TYPE), QVariantField("neg", e)))
        expr = QRecType("E", 9322, TYPE_KIND, expr_body)
        self.assertIs(resolve_variant_bound(expr), expr.unfold_lazily())
        self.assertEqual(qtype_to_c_type(expr), "QVariantVal")
        self.assertEqual(qtype_to_c_type(QArrayType(expr)), "QArrayWideVariant *")


if __name__ == "__main__":
    unittest.main()
