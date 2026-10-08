"""Unit tests for auto types (Cardelli §4.6, §6.7): subtyping, payload types, and inspect matching."""

import unittest

from quest.types import (
    BOOL_TYPE,
    INT_TYPE,
    QAutoType,
    QTupleType,
    auto_matches_subtypes,
    auto_payload_type,
    is_subtype,
    is_type_equal,
)
from tests.python.helpers import elaborate_test_type


def auto(source: str) -> QAutoType:
    t = elaborate_test_type(source)
    assert isinstance(t, QAutoType)
    return t


class TestAutoSubtyping(unittest.TestCase):
    """§6.7: an auto type is a subtype of another if the respective components are in the subtype or
    subkind relation."""

    def test_alpha_equivalent_autos_are_equal(self) -> None:
        self.assertTrue(is_type_equal(
            auto("Auto A::TYPE with fst,snd:A end"),
            auto("Auto B::TYPE with fst,snd:B end"),
        ))

    def test_narrower_kind_bound_is_subtype(self) -> None:
        narrow = auto("Auto A<:Int with a:A end")
        wide = auto("Auto A::TYPE with a:A end")
        self.assertTrue(is_subtype(narrow, wide))
        self.assertFalse(is_subtype(wide, narrow))

    def test_components_are_covariant(self) -> None:
        sub = auto("Auto A::TYPE with a:A r:Record x:Int y:Int end end")
        sup = auto("Auto A::TYPE with a:A r:Record x:Int end end")
        self.assertTrue(is_subtype(sub, sup))
        self.assertFalse(is_subtype(sup, sub))

    def test_var_components_are_invariant(self) -> None:
        sub = auto("Auto A::TYPE with a:A var r:Record x:Int y:Int end end")
        sup = auto("Auto A::TYPE with a:A var r:Record x:Int end end")
        self.assertFalse(is_subtype(sub, sup))

    def test_component_names_and_order_must_match(self) -> None:
        self.assertFalse(is_subtype(
            auto("Auto A::TYPE with a:A b:Int end"),
            auto("Auto A::TYPE with b:Int a:A end"),
        ))

    def test_extra_trailing_components_as_for_tuples(self) -> None:
        self.assertTrue(is_subtype(
            auto("Auto A::TYPE with a:A b:Int end"),
            auto("Auto A::TYPE with a:A end"),
        ))


class TestAutoPayloads(unittest.TestCase):

    def test_payload_type_substitutes_the_type_component(self) -> None:
        payload = auto_payload_type(auto("Auto A::TYPE with fst,snd:A end"), BOOL_TYPE)
        self.assertIsInstance(payload, QTupleType)
        self.assertEqual([f.name for f in payload.value_fields], ["fst", "snd"])
        self.assertTrue(all(f.type_val is BOOL_TYPE for f in payload.value_fields))

    def test_stored_payload_type_is_independent_of_the_witness(self) -> None:
        a = auto("Auto A<:Int with a:A n:Int end")
        stored = auto_payload_type(a)
        self.assertIs(stored.value_fields[1].type_val, INT_TYPE)
        self.assertTrue(is_subtype(stored.value_fields[0].type_val, INT_TYPE))


class TestInspectMatching(unittest.TestCase):
    """Inspect selects by subtyping only when that is sound for the signature."""

    def test_direct_components_match_by_subtype(self) -> None:
        self.assertTrue(auto_matches_subtypes(auto("Auto A::TYPE with fst,snd:A end")))
        self.assertTrue(auto_matches_subtypes(auto("Auto A::TYPE with a:A n:Int end")))

    def test_other_occurrences_match_exactly(self) -> None:
        self.assertFalse(auto_matches_subtypes(auto("Auto A::TYPE with f(x:A):Int end")))
        self.assertFalse(auto_matches_subtypes(auto("Auto A::TYPE with g():A end")))
        self.assertFalse(auto_matches_subtypes(auto("Auto A::TYPE with var a:A end")))
        self.assertFalse(auto_matches_subtypes(auto("Auto A::TYPE with arr:Array(A) end")))

    def test_var_components_match_exactly(self) -> None:
        self.assertFalse(auto_matches_subtypes(auto("Auto A::TYPE with a:A var n:Int end")))


if __name__ == "__main__":
    unittest.main()
