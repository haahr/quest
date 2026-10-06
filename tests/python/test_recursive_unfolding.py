"""Unfolding of recursive types is cached and shares one finite object graph."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.types import (
    INT_TYPE,
    TYPE_KIND,
    QOptionField,
    QOptionType,
    QRecGroupType,
    QRecType,
    QTupleType,
    QTypeVar,
    is_type_equal,
)


def _int_list() -> QRecType:
    """Rec(L) Option nil cons with Tuple Int L end end"""
    var = QTypeVar("L", 9001, TYPE_KIND)
    body = QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType((INT_TYPE, var)))))
    return QRecType("L", 9001, TYPE_KIND, body)


def _even_odd() -> QRecGroupType:
    """Let Rec Even = Option z s with Odd end and Odd = Option s with Even end"""
    even = QTypeVar("Even", 9101, TYPE_KIND)
    odd = QTypeVar("Odd", 9102, TYPE_KIND)
    even_body = QOptionType((QOptionField("z"), QOptionField("s", odd)))
    odd_body = QOptionType((QOptionField("s", even),))
    return QRecGroupType((("Even", 9101, TYPE_KIND, even_body), ("Odd", 9102, TYPE_KIND, odd_body)), 0)


class TestRecursiveUnfolding(unittest.TestCase):
    def test_rec_unfolding_is_cached_and_refers_back(self) -> None:
        rec = _int_list()
        unfolded = rec.unfold_lazily()
        self.assertIs(rec.unfold_lazily(), unfolded)
        cons_payload = unfolded.get_option("cons").payload_type
        self.assertIs(cons_payload.elements[1], rec)

    def test_group_unfoldings_share_sibling_nodes(self) -> None:
        even = _even_odd()
        odd = even.siblings()[1]
        self.assertIs(even.siblings()[0], even)
        self.assertIs(odd.siblings(), even.siblings())
        even_unfolded = even.unfold_lazily()
        self.assertIs(even.unfold_lazily(), even_unfolded)
        self.assertIs(even_unfolded.get_option("s").payload_type, odd)
        self.assertIs(odd.unfold_lazily().get_option("s").payload_type, even)

    def test_cache_is_not_a_dataclass_field(self) -> None:
        rec = _int_list()
        rec.unfold_lazily()
        self.assertEqual([f.name for f in dataclasses.fields(rec)], ["var_name", "symbol_id", "bound", "body"])
        copy = dataclasses.replace(rec)
        self.assertNotIn("_unfolded", copy.__dict__)

    def test_recursive_types_compare_equal(self) -> None:
        self.assertTrue(is_type_equal(_int_list(), _int_list()))
        self.assertTrue(is_type_equal(_even_odd(), _even_odd()))


if __name__ == "__main__":
    unittest.main()
