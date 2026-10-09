"""Reserved symbol ids: each use has its own prefix, so ids of different uses (and metavariables) never coincide."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.codegen.c_types import (
    _rec_self_level,
    _rec_self_var,
    bound_var,
    bound_var_index,
    canonical_fun_type,
    type_to_c_tag,
)
from quest.types import (
    DYNAMIC_TYPE,
    INT_TYPE,
    RESERVED_INDEX_LIMIT,
    TYPE_KIND,
    QAllType,
    QFunType,
    QParam,
    QQuantifier,
    QTypeMeta,
    QTypeVar,
    ReservedSymbolUse,
    reserved_symbol_id,
    reserved_symbol_index,
    reserved_symbol_use,
)


class TestReservedSymbolIds(unittest.TestCase):
    def test_ids_decode_to_their_use_and_index(self) -> None:
        for use in ReservedSymbolUse:
            for index in (0, 1, 7, RESERVED_INDEX_LIMIT - 1):
                symbol_id = reserved_symbol_id(use, index)
                self.assertLess(symbol_id, 0)
                self.assertEqual(reserved_symbol_use(symbol_id), (use, index))
                self.assertEqual(reserved_symbol_index(symbol_id, use), index)

    def test_ids_of_different_uses_never_coincide(self) -> None:
        ids = {
            reserved_symbol_id(use, index)
            for use in ReservedSymbolUse
            for index in (0, 1, RESERVED_INDEX_LIMIT - 1)
        }
        self.assertEqual(len(ids), len(ReservedSymbolUse) * 3)
        for use in ReservedSymbolUse:
            for other in ReservedSymbolUse:
                if other is not use:
                    self.assertIsNone(reserved_symbol_index(reserved_symbol_id(use, 0), other))

    def test_other_ids_are_not_reserved(self) -> None:
        # Environment ids are positive; metavariable ids count down from -1 and have prefix 0
        for symbol_id in (0, 1, 12345, -1, -2, -(RESERVED_INDEX_LIMIT - 1)):
            self.assertIsNone(reserved_symbol_use(symbol_id))

    def test_index_out_of_range_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            reserved_symbol_id(ReservedSymbolUse.BOUND_VAR, -1)
        with self.assertRaises(ValueError):
            reserved_symbol_id(ReservedSymbolUse.BOUND_VAR, RESERVED_INDEX_LIMIT)

    def test_metavariables_stop_before_reserved_ids(self) -> None:
        saved = QTypeMeta._counter
        try:
            QTypeMeta._counter = RESERVED_INDEX_LIMIT - 2
            meta = QTypeMeta()
            self.assertIsNone(reserved_symbol_use(meta.symbol_id))
            with self.assertRaises(RuntimeError):
                QTypeMeta()
        finally:
            QTypeMeta._counter = saved

    def test_each_placeholder_uses_its_own_prefix(self) -> None:
        dynamic_param = DYNAMIC_TYPE.signature[0].type_val
        self.assertEqual(reserved_symbol_use(dynamic_param.symbol_id), (ReservedSymbolUse.DYNAMIC_PARAM, 0))
        # Dynamic's parameter once shared its id with the recursion placeholder at depth 0, and was tagged Self0
        self.assertIsNone(_rec_self_level(dynamic_param))
        self.assertEqual(type_to_c_tag(dynamic_param), "QVal")

        self.assertEqual(reserved_symbol_use(bound_var(3, None).symbol_id), (ReservedSymbolUse.BOUND_VAR, 3))
        self.assertEqual(reserved_symbol_use(_rec_self_var(2).symbol_id), (ReservedSymbolUse.REC_SELF, 2))
        self.assertIsNone(bound_var_index(_rec_self_var(2)))
        self.assertIsNone(_rec_self_level(bound_var(2, None)))

        a = QTypeVar("A", 9401, TYPE_KIND)
        poly = QAllType(
            quantifiers=(QQuantifier(name="A", symbol_id=9401, bound=TYPE_KIND),),
            body=QFunType(params=(QParam(name="x", type_val=a),), result_type=INT_TYPE),
        )
        canonical = canonical_fun_type(poly)
        self.assertEqual(
            reserved_symbol_use(canonical.quantifiers[0].symbol_id), (ReservedSymbolUse.CANONICAL_QUANTIFIER, 0)
        )


if __name__ == "__main__":
    unittest.main()
