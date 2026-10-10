"""Simultaneous value declarations: let [rec] x = ... and y = ...."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import quest.ast as ast
from tests.python.helpers import parse_phrase


class TestValueBindingGroups(unittest.TestCase):
    def test_members_share_rec_and_keep_their_positions(self) -> None:
        source = "let rec f(n: Int): Int = g(n) and g(n: Int): Int = n;"
        group = parse_phrase(source)
        self.assertIsInstance(group, ast.LetValueBindingGroup)
        self.assertEqual(group.offset, 0)
        self.assertEqual([member.name for member in group.bindings], ["f", "g"])
        self.assertTrue(all(member.is_rec for member in group.bindings))
        self.assertEqual(group.bindings[0].offset, source.index("f("))
        self.assertEqual(group.bindings[1].offset, source.index("g(n: Int)"))

    def test_group_without_rec(self) -> None:
        group = parse_phrase("let x = 1 and y = 2;")
        self.assertIsInstance(group, ast.LetValueBindingGroup)
        self.assertFalse(any(member.is_rec for member in group.bindings))

    def test_single_declaration_is_a_value_binding_at_its_keyword(self) -> None:
        binding = parse_phrase("let rec f(n: Int): Int = n;")
        self.assertIsInstance(binding, ast.LetValueBinding)
        self.assertTrue(binding.is_rec)
        self.assertEqual(binding.offset, 0)


if __name__ == "__main__":
    unittest.main()
