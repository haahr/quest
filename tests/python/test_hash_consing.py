"""Hash-consing of types, and the per-alias definition objects that keep alias names printable."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.env import Environment, TypeSymbol
from quest.types import (
    QAliasType,
    alias_reference,
    is_subtype,
    strip_aliases,
    unalias,
    INT_TYPE,
    STRING_TYPE,
    TYPE_KIND,
    QArrayType,
    QIntType,
    QRecordField,
    QRecordType,
    QTupleField,
    QTupleType,
    QTypeApp,
    QTypeMeta,
    QTypeVar,
    format_type_compact,
    is_type_equal,
    structurally_equal,
)


class TestHashConsing(unittest.TestCase):
    def test_identical_structure_is_one_object(self) -> None:
        self.assertIs(QTupleType((INT_TYPE, QArrayType(STRING_TYPE))), QTupleType((INT_TYPE, QArrayType(STRING_TYPE))))
        self.assertIs(QIntType(), INT_TYPE)
        self.assertIs(QTupleField("x", INT_TYPE), QTupleField("x", INT_TYPE))

    def test_display_only_fields_keep_nodes_apart(self) -> None:
        r1 = QRecordType((QRecordField("x", INT_TYPE),), provenance="m1")
        r2 = QRecordType((QRecordField("x", INT_TYPE),), provenance="m2")
        self.assertIsNot(r1, r2)
        self.assertIsNot(QTypeVar("A", 7, TYPE_KIND), QTypeVar("B", 7, TYPE_KIND))

    def test_bool_and_int_fields_do_not_collide(self) -> None:
        self.assertIsNot(QTupleField("x", INT_TYPE, True), QTupleField("x", INT_TYPE, False))

    def test_nodes_with_metavariables_are_not_interned(self) -> None:
        meta = QTypeMeta()
        self.assertIsNot(QArrayType(meta), QArrayType(meta))

    def test_replace_returns_the_canonical_node(self) -> None:
        t = QRecordType((QRecordField("x", INT_TYPE),))
        self.assertIs(dataclasses.replace(t), t)


class TestAliasReferences(unittest.TestCase):
    def test_references_to_different_aliases_stay_apart(self) -> None:
        node = QTupleType((INT_TYPE, STRING_TYPE))
        expr = QAliasType("ast.Expr", 101, node)
        decl = QAliasType("ast.Decl", 102, node)
        self.assertIsNot(expr, decl)
        self.assertIs(expr, QAliasType("ast.Expr", 101, node))
        self.assertIsNot(expr, QAliasType("Expr", 101, node))  # spelled differently
        self.assertEqual(format_type_compact(expr), "ast.Expr")
        self.assertEqual(format_type_compact(decl), "ast.Decl")

    def test_alias_references_are_transparent(self) -> None:
        env = Environment()
        node = QTupleType((INT_TYPE, STRING_TYPE))
        expr = QAliasType("Expr", 101, node)
        self.assertIs(expr.evaluate_lazily(env), node)
        self.assertIs(unalias(expr), node)
        self.assertTrue(is_type_equal(expr, QAliasType("Decl", 102, node), env))
        self.assertTrue(is_subtype(node, expr, env))

    def test_builtin_primitive_names_are_not_alias_nodes(self) -> None:
        self.assertIs(alias_reference("Int", 1, INT_TYPE), INT_TYPE)
        self.assertIsInstance(alias_reference("Count", 2, INT_TYPE), QAliasType)

    def test_strip_aliases(self) -> None:
        node = QTupleType((INT_TYPE, STRING_TYPE))
        t = QArrayType(QAliasType("Pair", 103, node))
        self.assertIs(strip_aliases(t), QArrayType(node))
        self.assertIs(strip_aliases(QArrayType(node)), QArrayType(node))

    def test_substitution_that_changes_the_target_drops_the_alias(self) -> None:
        a = QTypeVar("A", 104, TYPE_KIND)
        alias = QAliasType("Box", 105, QTupleType((a,)))
        self.assertIs(alias.substitute({999: INT_TYPE}), alias)
        self.assertIs(alias.substitute({104: INT_TYPE}), QTupleType((INT_TYPE,)))

    def test_definitions_are_canonical_and_write_once(self) -> None:
        sym = TypeSymbol("T", Environment().fresh_symbol_id(), TYPE_KIND)
        pair = QTupleType((INT_TYPE, INT_TYPE))
        sym.definition = pair
        self.assertIs(sym.definition, pair)
        with self.assertRaises(RuntimeError):
            sym.definition = QTupleType((STRING_TYPE,))


if __name__ == "__main__":
    unittest.main()
