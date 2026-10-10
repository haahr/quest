"""Simultaneous type declarations: Let [Rec] A = ... and B = ..., and the same with Def."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

import quest.ast as ast
from quest.codegen.c_types import qtype_to_c_type, type_to_c_tag
from quest.elaborate_types import elaborate_type_binding, elaborate_type_binding_group
from quest.env import Environment
from quest.types import (
    BOOL_TYPE,
    INT_TYPE,
    QAliasType,
    QArrayType,
    QRecGroupType,
    QRecordType,
    QVariantType,
    format_type_compact,
    strip_aliases,
)
from tests.python.helpers import elaborate_test_type, parse_phrase


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



class TestTypeBindingGroupElaboration(unittest.TestCase):
    def setUp(self) -> None:
        self.env = Environment()

    def declare(self, source: str) -> list:
        binding = parse_phrase(source)
        if isinstance(binding, ast.TypeBindingGroup):
            return elaborate_type_binding_group(binding, self.env)
        return [elaborate_type_binding(binding, self.env)]

    def test_rec_group_members_are_siblings_of_one_group(self) -> None:
        forest, tree = self.declare(
            "Let Rec Forest = Record trees: Array(Tree) end and Tree = Variant leaf: Int node: Forest end;"
        )
        self.assertIsInstance(forest.definition, QRecGroupType)
        self.assertIsInstance(tree.definition, QRecGroupType)
        self.assertIs(forest.definition.bindings, tree.definition.bindings)
        self.assertEqual((forest.definition.active_index, tree.definition.active_index), (0, 1))
        # Each unfolds to its body, with the sibling's variable bound to the sibling
        forest_body = forest.definition.unfold_lazily()
        self.assertIsInstance(forest_body, QRecordType)
        element = forest_body.fields[0].type_val
        self.assertIsInstance(element, QArrayType)
        self.assertIs(element.element_type, tree.definition.siblings()[1])
        self.assertIsInstance(tree.definition.unfold_lazily(), QVariantType)

    def test_unfolding_a_reference_names_the_other_members(self) -> None:
        self.declare("Let Rec Forest = Record trees: Array(Tree) end and Tree = Variant leaf: Int node: Forest end;")
        forest = elaborate_test_type("Forest", self.env)
        tree = elaborate_test_type("Tree", self.env)
        self.assertIsInstance(forest, QAliasType)
        body = forest.unfold_lazily()
        self.assertEqual(str(body), "Record trees: Array(Tree) end")
        # The sibling in the unfolding is the node that a reference to Tree elaborates to, and its unfolding
        # refers back to the reference to Forest: one finite graph
        self.assertIs(body.fields[0].type_val.element_type, tree)
        self.assertIs(tree.unfold_lazily().variants[1].type_val, forest)

    def test_unfolding_a_qualified_reference_qualifies_the_other_members(self) -> None:
        forest, _ = self.declare(
            "Let Rec Forest = Record trees: Array(Tree) end and Tree = Variant leaf: Int node: Forest end;"
        )
        qualified = QAliasType(name="m.Forest", symbol_id=forest.symbol_id, target=forest.definition)
        self.assertEqual(str(qualified.unfold_lazily()), "Record trees: Array(m.Tree) end")

    def test_a_member_prints_like_a_single_recursive_type(self) -> None:
        forest, tree = self.declare(
            "Let Rec Forest = Record trees: Array(Tree) end and Tree = Variant leaf: Int node: Forest end;"
        )
        self.assertEqual(str(tree.definition), "Rec(Tree :: TYPE) Variant leaf: Int node: Forest end")
        self.assertEqual(
            format_type_compact(forest.definition), "Rec(Forest :: TYPE) Record trees: Array(Tree) end"
        )

    def test_members_without_rec_see_the_enclosing_scope_not_each_other(self) -> None:
        self.declare("Let Size = Bool;")
        size, other = self.declare("Let Size = Int and Other = Size;")
        self.assertIs(size.definition, INT_TYPE)
        self.assertIs(strip_aliases(other.definition), BOOL_TYPE)  # The outer Size
        # After the group, both are declared
        self.assertIs(elaborate_test_type("Size", self.env).evaluate_lazily(self.env), INT_TYPE)

    def test_member_of_a_rec_group_that_does_not_recur_is_represented_as_its_body_in_c(self) -> None:
        ints, count = self.declare("Let Rec Ints = Array(Count) and Count = Int;")
        self.assertEqual(qtype_to_c_type(count.definition), qtype_to_c_type(INT_TYPE))
        self.assertEqual(type_to_c_tag(count.definition), type_to_c_tag(INT_TYPE))
        self.assertEqual(qtype_to_c_type(ints.definition), qtype_to_c_type(QArrayType(INT_TYPE)))

    def test_single_rec_type_that_does_not_recur_is_represented_as_its_body_in_c(self) -> None:
        (c,) = self.declare("Let Rec C = Int;")
        self.assertEqual(qtype_to_c_type(c.definition), qtype_to_c_type(INT_TYPE))


if __name__ == "__main__":
    unittest.main()
