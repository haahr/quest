"""Type symbols are resolved by globally unique symbol id, independent of the current scope."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.env import Environment, KindSymbol, TypeSymbol
from quest.types import INT_TYPE, STRING_TYPE, TYPE_KIND, QKindVar, QPowerKind, QTypeVar


class TestSymbolIndex(unittest.TestCase):
    def test_lookup_by_id_works_outside_the_declaring_scope(self) -> None:
        env = Environment()
        sym_id = env.fresh_symbol_id()
        with env.scoped("inner"):
            env.current_scope.declare_type(TypeSymbol("Alias", sym_id, TYPE_KIND, definition=INT_TYPE))
        self.assertIsNone(env.lookup_type("Alias"))
        sym = env.lookup_type_by_id(sym_id)
        self.assertIsNotNone(sym)
        self.assertIs(sym.definition, INT_TYPE)
        self.assertIs(QTypeVar("Alias", sym_id).evaluate_lazily(env), INT_TYPE)

    def test_lookup_by_id_is_shared_across_environments(self) -> None:
        env_a, env_b = Environment(), Environment()
        sym_id = env_a.fresh_symbol_id()
        env_a.current_scope.declare_type(TypeSymbol("T", sym_id, TYPE_KIND))
        self.assertIs(env_b.lookup_type_by_id(sym_id), env_a.lookup_type_by_id(sym_id))

    def test_kind_lookup_by_id_works_outside_the_declaring_scope(self) -> None:
        env = Environment()
        sym_id = env.fresh_symbol_id()
        power = QPowerKind(INT_TYPE)
        with env.scoped("inner"):
            env.current_scope.declare_kind(KindSymbol("K", sym_id, power))
        self.assertIsNone(env.lookup_kind("K"))
        self.assertIs(env.lookup_kind_by_id(sym_id).kind, power)
        self.assertIs(QKindVar("K", sym_id).evaluate_lazily(env).bound, INT_TYPE)

    def test_definition_can_be_supplied_once_but_not_replaced(self) -> None:
        sym = TypeSymbol("T", Environment().fresh_symbol_id(), TYPE_KIND)
        sym.definition = INT_TYPE
        sym.definition = INT_TYPE
        with self.assertRaises(RuntimeError):
            sym.definition = STRING_TYPE


if __name__ == "__main__":
    unittest.main()
