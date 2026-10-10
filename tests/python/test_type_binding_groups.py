"""Parsing simultaneous type declarations: Let [Rec] A = ... and B = ..., and the same with Def."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import quest.ast as ast
from tests.python.helpers import parse_phrase


class TestTypeBindingGroups(unittest.TestCase):
    def test_members_share_rec_and_def_and_keep_their_positions(self) -> None:
        source = "Let Rec A = Record b: Array(B) end and B = Variant l: Int n: A end;"
        group = parse_phrase(source)
        self.assertIsInstance(group, ast.TypeBindingGroup)
        self.assertEqual(group.offset, 0)
        self.assertEqual([member.name for member in group.bindings], ["A", "B"])
        self.assertTrue(all(member.is_rec and not member.is_def for member in group.bindings))
        # The first member is positioned at its name, not at the keyword (that is the group's position)
        self.assertEqual(group.bindings[0].offset, source.index("A ="))
        self.assertEqual(group.bindings[1].offset, source.index("B ="))

    def test_def_group_without_rec(self) -> None:
        group = parse_phrase("Def A = Int and B::TYPE = String;")
        self.assertIsInstance(group, ast.TypeBindingGroup)
        self.assertTrue(all(member.is_def and not member.is_rec for member in group.bindings))
        self.assertIsInstance(group.bindings[1].bound, ast.KindType)

    def test_members_with_type_parameters_are_type_operators(self) -> None:
        group = parse_phrase("Let Box(A::TYPE)::TYPE = Tuple v: A end and Two(A::TYPE) = Tuple a, b: A end;")
        self.assertIsInstance(group, ast.TypeBindingGroup)
        self.assertTrue(all(isinstance(member.type_val, ast.TypeFun) for member in group.bindings))

    def test_single_declaration_is_a_type_binding_at_its_keyword(self) -> None:
        binding = parse_phrase("Let Rec L = Option nil cons with h: Int t: L end end;")
        self.assertIsInstance(binding, ast.TypeBinding)
        self.assertTrue(binding.is_rec)
        self.assertEqual(binding.offset, 0)


if __name__ == "__main__":
    unittest.main()
