"""The serialized form of dynamic values (docs/dynamic.md §2): canonical type tables and strict reading."""

from __future__ import annotations

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import tests.python.helpers  # noqa: F401
from quest.dynamic_json import jsog_decode, jsog_encode, parse_type_string
from quest.interpreter import DYNAMIC_ERROR_EXC, QuestException
from quest.runtime import OK_VALUE, QAutoVal, QInt, QOption, QReal, QTuple
from quest.types import is_type_equal

INT_LIST = "Rec(L :: TYPE) Option nil cons with head: Int tail: L end end"
INT_LIST_TABLE = [{"option": {"nil": None, "cons": 1}}, {"tuple": [["head", "Int"], ["tail", 0]]}]


def _dynamic(value, type_str):
    return QAutoVal(QTuple((value,), labels=("a",)), parse_type_string(type_str))


def _list(*items):
    result = QOption("nil", OK_VALUE)
    for item in reversed(items):
        result = QOption("cons", QTuple((QInt(item), result), labels=("head", "tail")))
    return result


class TestDynamicFormat(unittest.TestCase):
    def test_recursive_type_is_a_cycle(self) -> None:
        doc = json.loads(jsog_encode(_dynamic(_list(1, 2), INT_LIST)))
        self.assertEqual(doc["types"], INT_LIST_TABLE)
        self.assertEqual(doc["value"], {"cons": [1, {"cons": [2, "nil"]}]})

    def test_equal_types_have_equal_tables(self) -> None:
        unfolded = f"Option nil cons with head: Int tail: {INT_LIST} end end"
        twice = f"Option nil cons with head: Int tail: {unfolded} end end"
        for type_str in (unfolded, twice):
            with self.subTest(type_str=type_str):
                doc = json.loads(jsog_encode(_dynamic(_list(1), type_str)))
                self.assertEqual(doc["types"], INT_LIST_TABLE)

    def test_read_type_equals_written_type(self) -> None:
        d = jsog_decode(jsog_encode(_dynamic(_list(3, 4), INT_LIST)))
        self.assertTrue(is_type_equal(d.type_val, parse_type_string(INT_LIST)))
        self.assertEqual(d.value.elements[0].payload.elements[0], QInt(3))

    def test_non_finite_reals(self) -> None:
        for r in (math.inf, -math.inf):
            text = jsog_encode(_dynamic(QReal(r), "Real"))
            self.assertEqual(jsog_decode(text).value.elements[0].value, r)
        with self.assertRaises(QuestException):
            jsog_encode(_dynamic(QReal(math.nan), "Real"))
        for value in ('"NaN"', "NaN", "Infinity", "-Infinity"):  # NaN is not a Real; bare tokens are not JSON
            with self.assertRaises(QuestException):
                jsog_decode('{"quest":1,"types":[],"type":"Real","value":' + value + "}")

    def test_malformed_documents_are_rejected(self) -> None:
        good = {"quest": 1, "types": INT_LIST_TABLE, "type": 0, "value": "nil"}
        jsog_decode(json.dumps(good))
        bad = [
            {**good, "quest": 2},
            {**good, "type": 2},
            {**good, "type": "Integer"},
            {**good, "types": [{"set": "Int"}]},
            {**good, "types": [{"option": {"nil": None, "cons": "Int"}}]},
            {**good, "value": "cons"},
            {**good, "value": {"cons": [1]}},
            {"quest": 1, "types": [{"record": {"x": "Int"}}], "type": 0, "value": {}},
            {"quest": 1, "types": [{"record": {"x": "Int"}}], "type": 0, "value": {"x": 1, "y": 2}},
            {"quest": 1, "types": [{"array": "Int"}], "type": 0, "value": [{"@ref": 1}]},
            {"quest": 1, "types": [], "type": "Char", "value": "ab"},
        ]
        for doc in bad:
            with self.subTest(doc=doc):
                with self.assertRaises(QuestException) as cm:
                    jsog_decode(json.dumps(doc))
                self.assertIs(cm.exception.exc_val, DYNAMIC_ERROR_EXC)

    def test_abstract_types_are_not_encodable_yet(self) -> None:
        from quest.types import TYPE_KIND, QAbstractType

        d = QAutoVal(QTuple((QInt(1),), labels=("a",)), QAbstractType(name="T", symbol_id=-77, bound=TYPE_KIND))
        with self.assertRaises(QuestException):
            jsog_encode(d)


if __name__ == "__main__":
    unittest.main()
