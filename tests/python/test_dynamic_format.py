"""The serialized form of dynamic values (docs/dynamic.md §2): canonical type tables and strict reading."""

from __future__ import annotations

import io
import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import tests.python.helpers  # noqa: F401
from quest.dynamic_json import jsog_decode, jsog_encode, parse_type_string
from quest.interpreter import DYNAMIC_ERROR_EXC, QuestException
from quest.runtime import (
    OK_VALUE,
    QArray,
    QAutoVal,
    QInt,
    QOption,
    QReader,
    QReal,
    QRecord,
    QString,
    QTuple,
    QVariant,
    QWriter,
)
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
        # Infinities extern as the strings "Infinity" and "-Infinity"
        self.assertIn('"value":"Infinity"', jsog_encode(_dynamic(QReal(math.inf), "Real")))
        with self.assertRaises(QuestException):
            jsog_encode(_dynamic(QReal(math.nan), "Real"))
        for value in ('"NaN"', "NaN", "Infinity", "-Infinity"):  # NaN is not a Real; bare tokens are not JSON
            with self.assertRaises(QuestException) as cm:
                jsog_decode('{"quest":1,"types":[],"type":"Real","value":' + value + "}")
            self.assertEqual(cm.exception.exc_val.name, "dynamic.error")
        # An overflowing number interns as an infinity
        overflow = jsog_decode('{"quest":1,"types":[],"type":"Real","value":1e999}')
        self.assertEqual(overflow.value.elements[0].value, math.inf)

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


    def test_extern_and_intern_through_streams(self) -> None:
        """dynamic.extern writes the JSON format of docs/dynamic.md §2 and dynamic.intern reads it."""
        from quest.builtins import BuiltinModuleRegistry

        # The runtime operations of lib/dynamic.mod.quest, by the C symbols it declares them with
        extern_fn = BuiltinModuleRegistry.resolve_external_symbol("quest_dynamic_extern").fn
        intern_fn = BuiltinModuleRegistry.resolve_external_symbol("quest_dynamic_intern").fn

        def new_dynamic(value, type_str):
            """A dynamic value: an auto value whose one component a is the value."""
            return QAutoVal(QTuple((value,), labels=("a",)), parse_type_string(type_str))

        # 1. Primitive dynamic value
        d = new_dynamic(QInt(42), "Int")
        str_out = io.StringIO()
        wr = QWriter(stream=str_out, is_file=False)
        extern_fn(wr, d)
        self.assertEqual(str_out.getvalue(), '{"quest":1,"types":[],"type":"Int","value":42}')

        str_in = io.StringIO(str_out.getvalue())
        rd = QReader(stream=str_in, is_file=False)
        d_interned = intern_fn(rd)
        self.assertIsInstance(d_interned, QAutoVal)
        self.assertEqual(d_interned.value.elements[0], QInt(42))

        # 2. Cyclic record
        cyc_rec = QRecord({"name": QString("loop")})
        cyc_rec.fields["next"] = cyc_rec
        d_cyc = new_dynamic(cyc_rec, "Rec(R :: TYPE) Record name: String next: R end")
        s_out = io.StringIO()
        extern_fn(QWriter(stream=s_out, is_file=False), d_cyc)
        json_cyc = s_out.getvalue()
        self.assertIn('"types":[{"record":{"name":"String","next":0}}]', json_cyc)
        self.assertIn('"@id":1', json_cyc)
        self.assertIn('"@ref":1', json_cyc)

        d_cyc_in = intern_fn(QReader(stream=io.StringIO(json_cyc), is_file=False))
        rec_in = d_cyc_in.value.elements[0]
        self.assertIsInstance(rec_in, QRecord)
        self.assertEqual(rec_in.fields["name"], QString("loop"))
        self.assertIs(rec_in.fields["next"], rec_in)

        # 3. Shared array
        shared_arr = QArray([QInt(100)])
        d_arr = new_dynamic(QTuple((shared_arr, shared_arr)), "Tuple :Array(Int) :Array(Int) end")
        s_arr_out = io.StringIO()
        extern_fn(QWriter(stream=s_arr_out, is_file=False), d_arr)
        json_arr = s_arr_out.getvalue()
        self.assertIn('"value":[{"@id":1,"@items":[100]},{"@ref":1}]', json_arr)

        d_arr_in = intern_fn(QReader(stream=io.StringIO(json_arr), is_file=False))
        tup_in = d_arr_in.value.elements[0]
        self.assertIsInstance(tup_in.elements[0], QArray)
        self.assertEqual(tup_in.elements[0].elements[0], QInt(100))
        self.assertIs(tup_in.elements[1], tup_in.elements[0])

        # 4. Serde-style variant
        v = QVariant("red", QInt(255))
        d_var = new_dynamic(v, "Variant red: Int green: Ok end")
        s_var_out = io.StringIO()
        extern_fn(QWriter(stream=s_var_out, is_file=False), d_var)
        self.assertEqual(
            s_var_out.getvalue(),
            '{"quest":1,"types":[{"variant":{"red":"Int","green":"Ok"}}],"type":0,"value":{"red":255}}',
        )
        d_var_in = intern_fn(QReader(stream=io.StringIO(s_var_out.getvalue()), is_file=False))
        var_in = d_var_in.value.elements[0]
        self.assertIsInstance(var_in, QVariant)
        self.assertEqual(var_in.tag, "red")
        self.assertEqual(var_in.payload, QInt(255))

        # 5. Non-externable type raises error
        with self.assertRaises(QuestException) as cm:
            extern_fn(wr, new_dynamic(wr, "Int"))
        self.assertEqual(cm.exception.exc_val, DYNAMIC_ERROR_EXC)

        # 6. Malformed JSON raises error on intern
        with self.assertRaises(QuestException) as cm2:
            intern_fn(QReader(stream=io.StringIO("{not valid json"), is_file=False))
        self.assertEqual(cm2.exception.exc_val, DYNAMIC_ERROR_EXC)

if __name__ == "__main__":
    unittest.main()
