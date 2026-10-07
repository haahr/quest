"""Hash-consing of types, and the per-alias definition objects that keep alias names printable."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.env import Environment, TypeSymbol
from quest.types import (
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


class TestAliasDefinitions(unittest.TestCase):
    def test_each_alias_has_its_own_definition_object(self) -> None:
        env = Environment()
        node = QTypeApp(QTypeVar("Node", env.fresh_symbol_id(), TYPE_KIND), (INT_TYPE,))
        expr = TypeSymbol("Expr", env.fresh_symbol_id(), TYPE_KIND, definition=node)
        decl = TypeSymbol("Decl", env.fresh_symbol_id(), TYPE_KIND, definition=node)
        self.assertIsNot(expr.definition, decl.definition)
        self.assertTrue(structurally_equal(expr.definition, decl.definition))
        self.assertTrue(is_type_equal(expr.definition, decl.definition, env))

    def test_reexported_alias_keeps_the_same_definition_object(self) -> None:
        env = Environment()
        span = TypeSymbol("Span", env.fresh_symbol_id(), TYPE_KIND, definition=QTupleType((STRING_TYPE, INT_TYPE)))
        exported = TypeSymbol("Span", env.fresh_symbol_id(), TYPE_KIND, definition=span.definition)
        self.assertIs(exported.definition, span.definition)

    def test_primitive_singletons_are_not_copied(self) -> None:
        sym = TypeSymbol("Count", Environment().fresh_symbol_id(), TYPE_KIND, definition=INT_TYPE)
        self.assertIs(sym.definition, INT_TYPE)

    def test_late_definition_is_copied_and_write_once(self) -> None:
        sym = TypeSymbol("T", Environment().fresh_symbol_id(), TYPE_KIND)
        pair = QTupleType((INT_TYPE, INT_TYPE))
        sym.definition = pair
        self.assertIsNot(sym.definition, pair)
        sym.definition = pair  # the same definition again is allowed
        with self.assertRaises(RuntimeError):
            sym.definition = QTupleType((STRING_TYPE,))

    def test_aliases_print_under_their_own_names(self) -> None:
        env = Environment()
        scope = env.current_scope
        node = QTupleType((INT_TYPE, STRING_TYPE))
        scope.declare_type(TypeSymbol("Expr", env.fresh_symbol_id(), TYPE_KIND, definition=node))
        scope.declare_type(TypeSymbol("Decl", env.fresh_symbol_id(), TYPE_KIND, definition=node))
        env.register_interface("Ast", scope)
        self.assertEqual(format_type_compact(scope.lookup_type("Expr").definition, env), "Ast.Expr")
        self.assertEqual(format_type_compact(scope.lookup_type("Decl").definition, env), "Ast.Decl")


if __name__ == "__main__":
    unittest.main()
