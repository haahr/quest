"""Unit tests for existential tuple signature elaboration and type representation."""

import unittest

from quest.ast import (
    KindType,
    TypeFormal,
    TypeTuple,
)
from quest.elaborate_types import elaborate_type
from quest.env import Environment
from quest.types import (
    INT_TYPE,
    TYPE_KIND,
    KindError,
    QFunType,
    QTupleField,
    QTupleType,
    QTupleTypeBinding,
    QTupleTypeFormal,
    QTypeVar,
    is_subtype,
)
from tests.python.helpers import (
    assert_pipeline_success,
    elaborate_test_type,
)


class TestExistentialTuplesPhase1(unittest.TestCase):
    """Verifies Phase 1: tuple type representation and signature elaboration."""

    def setUp(self) -> None:
        self.env = Environment()

    def run_source(self, source: str) -> None:
        assert_pipeline_success(source, env=self.env)

    def test_cardelli_abstract_tuple_signature_elaboration(self) -> None:
        """Cardelli §5.3: Let T = Tuple A::TYPE a:A f(x:A):Int end;"""
        self.run_source("Let T = Tuple A::TYPE a:A f(x:A):Int end;")

        sym = self.env.lookup_type("T")
        self.assertIsNotNone(sym)
        self.assertIsNotNone(sym.definition)

        tup_type = sym.definition
        self.assertIsInstance(tup_type, QTupleType)
        self.assertTrue(tup_type.is_existential)
        self.assertEqual(len(tup_type.fields), 3)

        # Component 0: A::TYPE
        formal = tup_type.fields[0]
        self.assertIsInstance(formal, QTupleTypeFormal)
        self.assertEqual(formal.name, "A")
        self.assertEqual(formal.bound, TYPE_KIND)

        # Component 1: a:A
        field_a = tup_type.fields[1]
        self.assertIsInstance(field_a, QTupleField)
        self.assertEqual(field_a.name, "a")
        self.assertIsInstance(field_a.type_val, QTypeVar)
        self.assertEqual(field_a.type_val.symbol_id, formal.symbol_id)

        # Component 2: f(x:A):Int -> Fun(x:A):Int
        field_f = tup_type.fields[2]
        self.assertIsInstance(field_f, QTupleField)
        self.assertEqual(field_f.name, "f")
        self.assertIsInstance(field_f.type_val, QFunType)
        self.assertEqual(field_f.type_val.params[0].type_val, field_a.type_val)
        self.assertEqual(field_f.type_val.result_type, INT_TYPE)

    def test_nested_existential_tuple_dependent_scoping(self) -> None:
        """Type formal introduced in outer tuple is in scope in inner tuple."""
        self.run_source("Let T = Tuple A::TYPE pair:Tuple x:A y:A end end;")

        sym = self.env.lookup_type("T")
        self.assertIsNotNone(sym)
        tup_type = sym.definition
        self.assertIsInstance(tup_type, QTupleType)

        formal_a = tup_type.fields[0]
        pair_field = tup_type.fields[1]
        self.assertIsInstance(pair_field.type_val, QTupleType)

        inner_tup = pair_field.type_val
        self.assertEqual(len(inner_tup.fields), 2)
        self.assertEqual(inner_tup.fields[0].type_val.symbol_id, formal_a.symbol_id)
        self.assertEqual(inner_tup.fields[1].type_val.symbol_id, formal_a.symbol_id)

    def test_manifest_type_in_tuple_signature(self) -> None:
        """Tuple signature with manifest type definition: Tuple Def A::TYPE = Int a:A end."""
        self.run_source("Let T = Tuple Def A::TYPE = Int a:A end;")

        sym = self.env.lookup_type("T")
        self.assertIsNotNone(sym)
        tup_type = sym.definition
        self.assertIsInstance(tup_type, QTupleType)
        self.assertEqual(len(tup_type.fields), 2)

        comp_0 = tup_type.fields[0]
        self.assertIsInstance(comp_0, QTupleTypeBinding)
        self.assertEqual(comp_0.name, "A")
        self.assertEqual(comp_0.type_val, INT_TYPE)

    def test_anonymous_type_formal_rejected(self) -> None:
        """Anonymous type formal (::TYPE) in tuple signature must be rejected."""
        ast_tuple = TypeTuple(
            fields=(
                TypeFormal(name="_", bound=KindType(offset=10), offset=10),
            ),
            offset=0,
        )
        with self.assertRaises(KindError) as cm:
            elaborate_type(ast_tuple, self.env)
        self.assertIn("must have an identifier", str(cm.exception))

    def test_tuple_type_substitute_shadowing(self) -> None:
        """Substitution must shadow type formal symbol IDs for subsequent components."""
        formal_id = self.env.fresh_symbol_id()
        formal = QTupleTypeFormal(name="A", symbol_id=formal_id, bound=TYPE_KIND)
        field = QTupleField(name="a", type_val=QTypeVar("A", symbol_id=formal_id, bound=TYPE_KIND))
        tup = QTupleType((formal, field))

        # Attempt to substitute formal_id with INT_TYPE from outer scope
        subst = {formal_id: INT_TYPE}
        res = tup.substitute(subst)
        self.assertIsInstance(res, QTupleType)
        # field.type_val must remain QTypeVar, NOT substituted by INT_TYPE
        self.assertIsInstance(res.fields[1].type_val, QTypeVar)
        self.assertEqual(res.fields[1].type_val.symbol_id, formal_id)


class TestExistentialTuplesPhase2(unittest.TestCase):
    """Verifies Phase 2: tuple subtyping & extended subsignatures."""

    def setUp(self) -> None:
        self.env = Environment()

    def test_prefix_subtyping_simple_tuples(self) -> None:
        """Cardelli §7.1: Vehicle <: Object (prefix subtyping)."""
        object_tup = elaborate_test_type("Tuple age: Int end", self.env)
        vehicle_tup = elaborate_test_type("Tuple age: Int speed: Int end", self.env)

        # Vehicle <: Object
        self.assertTrue(is_subtype(vehicle_tup, object_tup, self.env))
        # Object is NOT a subtype of Vehicle
        self.assertFalse(is_subtype(object_tup, vehicle_tup, self.env))

    def test_cardelli_abstract_tuple_subtyping(self) -> None:
        """Cardelli §7.1: ColorPoint <: Point."""
        point_type = elaborate_test_type(
            "Tuple A::TYPE new(x:Int y:Int):A x(p:A):Int end",
            self.env,
        )
        color_point_type = elaborate_test_type(
            "Tuple A::TYPE new(x:Int y:Int):A x(p:A):Int paint(p:A c:Int):Ok color(p:A):Int end",
            self.env,
        )

        # ColorPoint <: Point
        self.assertTrue(is_subtype(color_point_type, point_type, self.env))
        # Point is NOT a subtype of ColorPoint
        self.assertFalse(is_subtype(point_type, color_point_type, self.env))

    def test_component_name_mismatch_rejected(self) -> None:
        """Rule 4: Component names must match identically (no alpha-conversion)."""
        t1 = elaborate_test_type("Tuple A::TYPE a:A end", self.env)
        t2 = elaborate_test_type("Tuple B::TYPE a:B end", self.env)

        # Distinct type formal names A vs B: must NOT be subtypes
        self.assertFalse(is_subtype(t1, t2, self.env))
        self.assertFalse(is_subtype(t2, t1, self.env))

    def test_value_field_name_mismatch_rejected(self) -> None:
        """Value field names must match if present in supertype."""
        t1 = elaborate_test_type("Tuple x: Int end", self.env)
        t2 = elaborate_test_type("Tuple y: Int end", self.env)
        self.assertFalse(is_subtype(t1, t2, self.env))

    def test_type_formal_subkinding(self) -> None:
        """Type formal subkinding: POWER(Int) <:: TYPE."""
        sub_tup = elaborate_test_type("Tuple A::POWER(Int) a:A end", self.env)
        sup_tup = elaborate_test_type("Tuple A::TYPE a:A end", self.env)

        # A::POWER(Int) <: A::TYPE
        self.assertTrue(is_subtype(sub_tup, sup_tup, self.env))
        # A::TYPE is NOT subtype of A::POWER(Int)
        self.assertFalse(is_subtype(sup_tup, sub_tup, self.env))

    def test_manifest_type_binding_subtype_of_formal(self) -> None:
        """Manifest type binding Tuple Def A::TYPE = Int a:A end <: Tuple A::TYPE a:A end."""
        manifest_sub = elaborate_test_type("Tuple Def A::TYPE = Int a:A end", self.env)
        sup_tup = elaborate_test_type("Tuple A::TYPE a:A end", self.env)

        self.assertTrue(is_subtype(manifest_sub, sup_tup, self.env))


if __name__ == "__main__":
    unittest.main()

