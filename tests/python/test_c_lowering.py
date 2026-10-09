"""A type's C representation is computed once per canonical type and never cached through a metavariable.

Type digests stand for the printed type without printing it.
"""

from __future__ import annotations

import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import tests.python.helpers  # noqa: F401
from quest.codegen.c_types import (
    _PRINTED_TEXT_LIMIT,
    _printed,
    _type_digest,
    descriptor_form,
    lower_type,
    qtype_to_c_type,
    type_to_c_tag,
)
from quest.types import (
    BOOL_TYPE,
    INT_TYPE,
    OK_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QAbstractType,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QExceptionType,
    QFunType,
    QOptionField,
    QOptionType,
    QOutType,
    QParam,
    QPowerKind,
    QQuantifier,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QTypeApp,
    QTypeFormal,
    QTypeFun,
    QTypeMeta,
    QTypeVar,
    QVariantField,
    QVariantType,
    QVarType,
)


def _pair(a, b):
    return QTupleType((QTupleField(name="a", type_val=a), QTupleField(name="b", type_val=b)))


class TestCLowering(unittest.TestCase):
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



def _doubled(leaf, depth):
    """A type that prints as 2**depth copies of leaf but has only depth + 1 distinct nodes."""
    t = leaf
    for _ in range(depth):
        t = _pair(t, t)
    return t


def _every_kind_of_node():
    x = QTypeVar(name="X", symbol_id=9001)
    power = QPowerKind(_pair(INT_TYPE, x))
    operator_kind = QAllKind(param_name="K", param_id=9002, param_kind=TYPE_KIND, result_kind=TYPE_KIND)
    record = QRecordType((QRecordField("f", INT_TYPE), QRecordField("g", x, is_var=True)))
    variant = QVariantType((QVariantField("v", record), QVariantField("w"), QVariantField("u", STRING_TYPE, is_var=True)))
    option = QOptionType((QOptionField("a"), QOptionField("b", variant)))
    fun = QFunType(
        (QParam("p", option), QParam("q", INT_TYPE, is_var=True), QParam("r", BOOL_TYPE, is_out=True)),
        QExceptionType(STRING_TYPE),
    )
    tuple_t = QTupleType((
        QTupleTypeFormal(name="T", symbol_id=9003, bound=power),
        QTupleTypeBinding(name="U", type_val=INT_TYPE, bound=TYPE_KIND),
        QTupleTypeBinding(name="V", type_val=x),
        QTupleField(name=None, type_val=QArrayType(fun)),
        QTupleField(name="n", type_val=QVarType(x), is_var=True),
    ))
    all_t = QAllType(
        (QQuantifier("X", 9001, power), QQuantifier("Y", 9004, TYPE_KIND)), QFunType((QParam("t", tuple_t),), x)
    )
    auto_power = QAutoType("A", 9005, power, (QRecordField("get", all_t), QRecordField("set", QOutType(x), is_var=True)))
    auto_kind = QAutoType("B", 9006, operator_kind, ())
    operator = QTypeFun((QTypeFormal("F", 9007, operator_kind),), QTupleType((auto_power, auto_kind)))
    app = QTypeApp(operator, (QAbstractType("Z", 9008, TYPE_KIND), QExceptionType(OK_TYPE), QRecordType(())))
    rec = QRecType("R", 9009, TYPE_KIND, QOptionType((QOptionField("nil"), QOptionField("cons", app))))
    return [rec, QVariantType(()), QOptionType(()), QTupleType(()), QRecordType((), provenance="m")]


class TestTypeDigests(unittest.TestCase):
    def test_short_types_are_digested_from_their_text(self) -> None:
        t = _pair(INT_TYPE, QArrayType(STRING_TYPE))
        self.assertEqual(_type_digest(t), hashlib.sha256(str(t).encode("utf-8")).hexdigest()[:16])

    def test_printed_lengths_match_the_printer(self) -> None:
        for t in _every_kind_of_node():
            for wide in (t, _doubled(t, 6)):
                self.assertEqual(_printed(wide)[0], len(str(wide)), str(wide)[:200])

    def test_long_types_are_digested_without_printing(self) -> None:
        # Each of these prints as 2**60 copies of its leaf
        a, b = _doubled(INT_TYPE, 60), _doubled(STRING_TYPE, 60)
        self.assertGreater(_printed(a)[0], 2**60)
        self.assertNotEqual(_type_digest(a), _type_digest(b))
        self.assertEqual(_type_digest(a), _type_digest(_doubled(INT_TYPE, 60)))
        # One level past the text limit, a type differing deep inside still digests differently
        depth = next(d for d in range(20) if _printed(_doubled(INT_TYPE, d))[0] > _PRINTED_TEXT_LIMIT)
        deep_a = _pair(_doubled(INT_TYPE, depth - 1), _doubled(INT_TYPE, depth - 1))
        deep_b = _pair(_doubled(INT_TYPE, depth - 1), _pair(_doubled(INT_TYPE, depth - 2), _doubled(BOOL_TYPE, depth - 2)))
        self.assertNotEqual(_type_digest(deep_a), _type_digest(deep_b))

    def test_opaque_names_of_long_types_are_short_and_distinct(self) -> None:
        operator = QAbstractType("list.T", 9010, QAllKind("E", 9011, TYPE_KIND, TYPE_KIND))
        short = QTypeApp(operator, (INT_TYPE,))
        self.assertEqual(descriptor_form(short).name, "list.T(Int)")
        a = descriptor_form(QTypeApp(operator, (_doubled(INT_TYPE, 60),)))
        b = descriptor_form(QTypeApp(operator, (_doubled(STRING_TYPE, 60),)))
        self.assertLess(len(a.name), 200)
        self.assertNotEqual(a.name, b.name)
        self.assertNotEqual(a.tag, b.tag)


if __name__ == "__main__":
    unittest.main()
