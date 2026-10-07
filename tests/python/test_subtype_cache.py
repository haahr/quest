"""The subtype cache commits a proof's results only when they cannot depend on refuted assumptions."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import quest.types as types
from quest.env import Environment, TypeSymbol
from quest.types import (
    INT_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QRecordField,
    QRecordType,
    QRecType,
    QTypeMeta,
    QTypeVar,
    clear_subtype_cache,
    is_subtype,
    is_type_equal,
)


def _cached(sub, sup, env=None):
    entry = types._SUBTYPE_CACHE.get((id(sub), id(sup), env is None))
    return entry[2] if entry is not None and entry[0] is sub and entry[1] is sup else None


def _stream(var_id: int, last_field_type) -> QRecType:
    """Rec(X) Record f: X g: <last_field_type> end"""
    var = QTypeVar("X", var_id, TYPE_KIND)
    return QRecType("X", var_id, TYPE_KIND, QRecordType((QRecordField("f", var), QRecordField("g", last_field_type))))


class TestSubtypeCache(unittest.TestCase):
    def setUp(self) -> None:
        clear_subtype_cache()

    def test_conditional_true_of_a_failed_proof_is_not_cached(self) -> None:
        a, b = _stream(990001, INT_TYPE), _stream(990002, STRING_TYPE)
        self.assertFalse(is_subtype(a, b))
        # Field f was "proved" by assuming a <: b, which field g then refuted.
        self.assertIs(_cached(a, b), False)
        self.assertFalse(is_subtype(a, b))

    def test_successful_proof_caches_its_assumed_and_nested_pairs(self) -> None:
        a, b = _stream(990003, INT_TYPE), _stream(990004, INT_TYPE)
        self.assertTrue(is_subtype(a, b))
        self.assertIs(_cached(a, b), True)
        self.assertIs(_cached(a.unfold_lazily(), b.unfold_lazily()), True)

    def test_false_results_are_cached_even_mid_proof(self) -> None:
        a, b = _stream(990005, INT_TYPE), _stream(990006, STRING_TYPE)
        is_subtype(a, b)
        self.assertIs(_cached(INT_TYPE, STRING_TYPE), False)

    def test_type_equality_uses_one_proof(self) -> None:
        a, b = _stream(990007, INT_TYPE), _stream(990008, INT_TYPE)
        self.assertTrue(is_type_equal(a, b))
        self.assertIs(_cached(a, b), True)
        self.assertIs(_cached(b, a), True)

    def test_pairs_with_metavariables_are_not_cached(self) -> None:
        meta = QTypeMeta()
        record = QRecordType((QRecordField("x", meta),))
        self.assertTrue(is_subtype(QRecordType((QRecordField("x", INT_TYPE),)), record))
        self.assertIsNone(_cached(QRecordType((QRecordField("x", INT_TYPE),)), record))

    def test_cache_is_cleared_when_a_symbol_seen_undefined_gains_a_definition(self) -> None:
        env = Environment()
        sym_id = env.fresh_symbol_id()
        alias = QTypeVar("Later", sym_id, TYPE_KIND)
        self.assertFalse(is_subtype(alias, INT_TYPE, env))  # undeclared: opaque
        self.assertIs(_cached(alias, INT_TYPE, env), False)
        env.current_scope.declare_type(TypeSymbol("Later", sym_id, TYPE_KIND, definition=INT_TYPE))
        self.assertIsNone(_cached(alias, INT_TYPE, env))
        self.assertTrue(is_subtype(alias, INT_TYPE, env))

    def test_late_definition_clears_the_cache(self) -> None:
        env = Environment()
        sym = env.current_scope.declare_type(TypeSymbol("T", env.fresh_symbol_id(), TYPE_KIND))
        var = QTypeVar("T", sym.symbol_id, TYPE_KIND)
        self.assertFalse(is_subtype(var, INT_TYPE, env))  # abstract for now
        sym.definition = INT_TYPE
        self.assertTrue(is_subtype(var, INT_TYPE, env))


if __name__ == "__main__":
    unittest.main()
