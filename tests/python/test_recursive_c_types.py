"""C representations of recursive tuple, record, and variant types are those of their unfoldings, and equal recursive
types (however written) share one C representation."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.c_types import (
    _canonical_type,
    descriptor_form,
    normalize_type,
    qtype_to_c_type,
    tuple_struct_name,
    type_to_c_tag,
)
from quest.types import (
    BOOL_TYPE,
    INT_TYPE,
    TYPE_KIND,
    QArrayType,
    QFunType,
    QOptionField,
    QOptionType,
    QParam,
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
        # P and Q differ only in their field names, so they share a struct (as non-recursive tuples do), but not
        # a descriptor
        self.assertEqual(type_to_c_tag(p), type_to_c_tag(q))
        self.assertNotEqual(descriptor_form(p).tag, descriptor_form(q).tag)

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


def _int_list(symbol_id: int, period: int) -> QRecType:
    """Rec(L) Option nil cons with head: Int tail: ... end end, with the cons cell written out period times."""
    var = QTypeVar("L", symbol_id, TYPE_KIND)
    t = var
    for _ in range(period):
        t = QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType((
            QTupleField("head", INT_TYPE), QTupleField("tail", t))))))
    return QRecType("L", symbol_id, TYPE_KIND, t)


class TestCanonicalRecursiveTypes(unittest.TestCase):
    """Equal recursive types with different periods, and their unfoldings, share tags and descriptors."""

    def assert_same_representation(self, a, b) -> None:
        self.assertEqual(type_to_c_tag(a), type_to_c_tag(b))
        self.assertEqual(qtype_to_c_type(a), qtype_to_c_type(b))
        self.assertEqual(descriptor_form(a).tag, descriptor_form(b).tag)

    def test_periods_and_unfoldings_share_a_representation(self) -> None:
        one = _int_list(9401, 1)
        self.assertEqual(type_to_c_tag(one), "Rec0_QOption_nil_cons_QTuple_Int_Self0")
        for period in (2, 3):
            self.assert_same_representation(one, _int_list(9402, period))
        self.assert_same_representation(one, _int_list(9403, 2).unfold_lazily())

    def test_canonical_form_is_a_fixed_point(self) -> None:
        canonical = _canonical_type(_int_list(9411, 3))
        self.assertIsNotNone(canonical)
        self.assertIs(_canonical_type(_int_list(9412, 2)), canonical)
        self.assertIsNone(_canonical_type(canonical))
        self.assertIs(_canonical_type(canonical.unfold_lazily()), canonical)

    def test_types_without_recursion_are_their_own_canonical_forms(self) -> None:
        self.assertIsNone(_canonical_type(QTupleType((QTupleField("a", INT_TYPE), QTupleField("b", BOOL_TYPE)))))

    def test_aggregates_containing_recursive_types(self) -> None:
        pair = QTupleType((QTupleField(None, INT_TYPE), QTupleField(None, _int_list(9421, 1))))
        unrolled = QTupleType((QTupleField(None, INT_TYPE), QTupleField(None, _int_list(9422, 2))))
        self.assert_same_representation(pair, unrolled)

    def test_cycles_through_function_types(self) -> None:
        """Rec(L) Option nil cons with f: Fun(L) Int end end, unrolled or not; recursion variables bind options."""

        def through_fun(symbol_id: int, period: int) -> QRecType:
            t = QTypeVar("L", symbol_id, TYPE_KIND)
            for _ in range(period):
                fun = QFunType((QParam("x", t),), INT_TYPE)
                t = QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType((QTupleField("f", fun),)))))
            return QRecType("L", symbol_id, TYPE_KIND, t)

        self.assert_same_representation(through_fun(9431, 1), through_fun(9432, 2))
        fun = through_fun(9433, 2).unfold_lazily().options[1].payload_type.value_fields[0].type_val
        self.assertEqual(type_to_c_tag(fun), "QClosure")
        self.assertEqual(qtype_to_c_type(fun), "QClosure *")

    def test_two_cycle_entries_make_a_recursive_group(self) -> None:
        """Rec(A) Tuple Int Array(Rec(B) Tuple Bool Array(B) Array(A) end) end: both A and B are re-entered."""
        a = QTypeVar("A", 9441, TYPE_KIND)
        b = QTypeVar("B", 9442, TYPE_KIND)
        inner = QRecType("B", 9442, TYPE_KIND, QTupleType((
            QTupleField(None, BOOL_TYPE), QTupleField(None, QArrayType(b)), QTupleField(None, QArrayType(a)))))
        outer = QRecType("A", 9441, TYPE_KIND, QTupleType((
            QTupleField(None, INT_TYPE), QTupleField(None, QArrayType(inner)))))
        canonical = _canonical_type(outer)
        self.assertIsInstance(canonical, QRecGroupType)
        self.assertIsNone(_canonical_type(canonical))
        self.assert_same_representation(outer, outer.unfold_lazily())
        self.assertTrue(type_to_c_tag(outer).startswith("RecGroup0_0_"))


if __name__ == "__main__":
    unittest.main()
