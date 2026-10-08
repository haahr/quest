"""A type's C representation is computed once per canonical type and never cached through a metavariable."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import tests.python.helpers  # noqa: F401
from quest import shadow
from quest.codegen import c_types
from quest.codegen.c_types import lower_type, qtype_to_c_type, type_to_c_tag
from quest.types import INT_TYPE, STRING_TYPE, QTupleField, QTupleType, QTypeMeta


def _pair(a, b):
    return QTupleType((QTupleField(name="a", type_val=a), QTupleField(name="b", type_val=b)))


class TestCLowering(unittest.TestCase):
    def tearDown(self) -> None:
        shadow.disable_all()

    def test_representation_is_shared_per_canonical_type(self) -> None:
        t = _pair(INT_TYPE, STRING_TYPE)
        self.assertIs(lower_type(t), lower_type(_pair(INT_TYPE, STRING_TYPE)))
        self.assertEqual(type_to_c_tag(t), "QTuple_Int_String")
        self.assertEqual(qtype_to_c_type(t), "QTuple_Int_String *")

    def test_types_with_metavariables_are_not_cached(self) -> None:
        meta = QTypeMeta()
        t = _pair(INT_TYPE, meta)
        self.assertIsNot(lower_type(t), lower_type(t))
        meta.instance = STRING_TYPE
        self.assertEqual(type_to_c_tag(t), "QTuple_Int_String")

    def test_shadow_check_detects_a_wrong_cached_part(self) -> None:
        t = _pair(STRING_TYPE, INT_TYPE)
        type_to_c_tag(t)
        c_types._LOWERED[id(t)]._tag = "wrong"
        shadow.enable(c_types.SHADOW_C_LOWERING)
        with self.assertRaises(shadow.ShadowMismatch):
            type_to_c_tag(t)
        del c_types._LOWERED[id(t)]


if __name__ == "__main__":
    unittest.main()
