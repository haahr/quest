"""C representations of recursive types are those of their unfoldings, and equal recursive types (however written)
share one C representation."""

from __future__ import annotations

import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
# Checks canonical forms, as the other tests do (see helpers.py)
os.environ["QUEST_CHECK_CANONICAL"] = "1"

from quest.codegen import c_types
from quest.codegen.c_types import (
    _canonical_type,
    descriptor_form,
    normalize_type,
    qtype_to_c_type,
    tuple_struct_name,
    type_to_c_tag,
)
from quest.types import (
    BOOL_TYPE,
    INT_TYPE,
    TYPE_KIND,
    QAllKind,
    QAllType,
    QArrayType,
    QAutoType,
    QFunType,
    QOptionField,
    QOptionType,
    QParam,
    QPathType,
    QPowerKind,
    QQuantifier,
    QRecGroupType,
    QRecordField,
    QRecordType,
    QRecType,
    QTupleField,
    QTupleType,
    QTypeFormal,
    QTypeFun,
    QTypeVar,
    QVariantField,
    QVariantType,
    resolve_record_bound,
    resolve_variant_bound,
)


def _tree(name: str, symbol_id: int) -> QRecType:
    """Rec(T) Tuple v: Int kids: Array(T) end"""
    var = QTypeVar(name, symbol_id, TYPE_KIND)
    body = QTupleType((QTupleField("v", INT_TYPE), QTupleField("kids", QArrayType(var))))
    return QRecType(name, symbol_id, TYPE_KIND, body)


def _p_q() -> QRecGroupType:
    """Let Rec P = Tuple v: Int q: Array(Q) end and Q = Tuple w: Int p: Array(P) end"""
    p = QTypeVar("P", 9201, TYPE_KIND)
    q = QTypeVar("Q", 9202, TYPE_KIND)
    p_body = QTupleType((QTupleField("v", INT_TYPE), QTupleField("q", QArrayType(q))))
    q_body = QTupleType((QTupleField("w", INT_TYPE), QTupleField("p", QArrayType(p))))
    return QRecGroupType((("P", 9201, TYPE_KIND, p_body), ("Q", 9202, TYPE_KIND, q_body)), 0)


class TestRecursiveCTypes(unittest.TestCase):
    def test_recursive_tuple_is_its_unfoldings_struct_pointer(self) -> None:
        tree = _tree("Tree", 9301)
        unfolded = tree.unfold_lazily()
        self.assertIs(normalize_type(tree), unfolded)
        self.assertEqual(qtype_to_c_type(tree), f"{tuple_struct_name(unfolded)} *")
        # The struct of the unfolding names the recursive occurrence by the recursive type's own tag
        self.assertIn(type_to_c_tag(tree), tuple_struct_name(unfolded))

    def test_recursive_tags_are_alpha_invariant_and_distinct(self) -> None:
        self.assertEqual(type_to_c_tag(_tree("Tree", 9302)), type_to_c_tag(_tree("Other", 9303)))
        var = QTypeVar("X", 9304, TYPE_KIND)
        plain = QTupleType((QTupleField("v", INT_TYPE), QTupleField("kids", QArrayType(var))))
        self.assertNotEqual(type_to_c_tag(_tree("Tree", 9305)), type_to_c_tag(plain))

    def test_nested_recursive_variables_are_distinguished(self) -> None:
        """Rec(X) Tuple Array(Rec(Y) Tuple Array(X) end) end differs from the same with Array(Y) inside."""

        def nested(inner_refers_to_outer: bool) -> QRecType:
            x = QTypeVar("X", 9311, TYPE_KIND)
            y = QTypeVar("Y", 9312, TYPE_KIND)
            inner_body = QTupleType((QTupleField("a", QArrayType(x if inner_refers_to_outer else y)),))
            inner = QRecType("Y", 9312, TYPE_KIND, inner_body)
            return QRecType("X", 9311, TYPE_KIND, QTupleType((QTupleField("b", QArrayType(inner)),)))

        self.assertNotEqual(type_to_c_tag(nested(True)), type_to_c_tag(nested(False)))

    def test_mutually_recursive_tuples(self) -> None:
        p = _p_q()
        q = p.siblings()[1]
        self.assertIs(normalize_type(p), p.unfold_lazily())
        self.assertEqual(qtype_to_c_type(p), f"{tuple_struct_name(p.unfold_lazily())} *")
        self.assertEqual(qtype_to_c_type(q), f"{tuple_struct_name(q.unfold_lazily())} *")
        # P and Q differ only in their field names, so they share a struct (as non-recursive tuples do), but not
        # a descriptor
        self.assertEqual(type_to_c_tag(p), type_to_c_tag(q))
        self.assertNotEqual(descriptor_form(p).tag, descriptor_form(q).tag)

    def test_recursive_record_and_variant_resolve_to_their_unfoldings(self) -> None:
        n = QTypeVar("N", 9321, TYPE_KIND)
        node_body = QRecordType((QRecordField("v", INT_TYPE), QRecordField("kids", QArrayType(n))))
        node = QRecType("N", 9321, TYPE_KIND, node_body)
        self.assertIs(resolve_record_bound(node), node.unfold_lazily())
        self.assertEqual(qtype_to_c_type(node), "QRecordVal")
        self.assertEqual(qtype_to_c_type(QArrayType(node)), "QArrayWideRecord *")

        e = QTypeVar("E", 9322, TYPE_KIND)
        expr_body = QVariantType((QVariantField("num", INT_TYPE), QVariantField("neg", e)))
        expr = QRecType("E", 9322, TYPE_KIND, expr_body)
        self.assertIs(resolve_variant_bound(expr), expr.unfold_lazily())
        self.assertEqual(qtype_to_c_type(expr), "QVariantVal")
        self.assertEqual(qtype_to_c_type(QArrayType(expr)), "QArrayWideVariant *")


def _int_list(symbol_id: int, period: int) -> QRecType:
    """Rec(L) Option nil cons with head: Int tail: ... end end, with the cons cell written out period times."""
    var = QTypeVar("L", symbol_id, TYPE_KIND)
    t = var
    for _ in range(period):
        t = QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType((
            QTupleField("head", INT_TYPE), QTupleField("tail", t))))))
    return QRecType("L", symbol_id, TYPE_KIND, t)


class TestCanonicalRecursiveTypes(unittest.TestCase):
    """Equal recursive types with different periods, and their unfoldings, share tags and descriptors."""

    def assert_same_representation(self, a, b) -> None:
        self.assertEqual(type_to_c_tag(a), type_to_c_tag(b))
        self.assertEqual(qtype_to_c_type(a), qtype_to_c_type(b))
        self.assertEqual(descriptor_form(a).tag, descriptor_form(b).tag)

    def test_periods_and_unfoldings_share_a_representation(self) -> None:
        one = _int_list(9401, 1)
        self.assertEqual(type_to_c_tag(one), "Rec0_QOption_nil_cons_QTuple_Int_Self0_end")
        for period in (2, 3):
            self.assert_same_representation(one, _int_list(9402, period))
        self.assert_same_representation(one, _int_list(9403, 2).unfold_lazily())

    def test_canonical_form_is_a_fixed_point(self) -> None:
        canonical = _canonical_type(_int_list(9411, 3))
        self.assertIsNotNone(canonical)
        self.assertIs(_canonical_type(_int_list(9412, 2)), canonical)
        self.assertIsNone(_canonical_type(canonical))
        self.assertIs(_canonical_type(canonical.unfold_lazily()), canonical)

    def test_types_without_recursion_are_their_own_canonical_forms(self) -> None:
        self.assertIsNone(_canonical_type(QTupleType((QTupleField("a", INT_TYPE), QTupleField("b", BOOL_TYPE)))))

    def test_aggregates_containing_recursive_types(self) -> None:
        pair = QTupleType((QTupleField(None, INT_TYPE), QTupleField(None, _int_list(9421, 1))))
        unrolled = QTupleType((QTupleField(None, INT_TYPE), QTupleField(None, _int_list(9422, 2))))
        self.assert_same_representation(pair, unrolled)

    def test_cycles_through_function_types(self) -> None:
        """Rec(L) Option nil cons with f: Fun(L) Int end end, unrolled or not; recursion variables bind options."""

        def through_fun(symbol_id: int, period: int) -> QRecType:
            t = QTypeVar("L", symbol_id, TYPE_KIND)
            for _ in range(period):
                fun = QFunType((QParam("x", t),), INT_TYPE)
                t = QOptionType((QOptionField("nil"), QOptionField("cons", QTupleType((QTupleField("f", fun),)))))
            return QRecType("L", symbol_id, TYPE_KIND, t)

        self.assert_same_representation(through_fun(9431, 1), through_fun(9432, 2))
        fun = through_fun(9433, 2).unfold_lazily().options[1].payload_type.value_fields[0].type_val
        self.assertEqual(type_to_c_tag(fun), "QClosure")
        self.assertEqual(qtype_to_c_type(fun), "QClosure *")

    def test_two_cycle_entries_make_a_recursive_group(self) -> None:
        """Rec(A) Tuple Int Array(Rec(B) Tuple Bool Array(B) Array(A) end) end: both A and B are re-entered."""
        a = QTypeVar("A", 9441, TYPE_KIND)
        b = QTypeVar("B", 9442, TYPE_KIND)
        inner = QRecType("B", 9442, TYPE_KIND, QTupleType((
            QTupleField(None, BOOL_TYPE), QTupleField(None, QArrayType(b)), QTupleField(None, QArrayType(a)))))
        outer = QRecType("A", 9441, TYPE_KIND, QTupleType((
            QTupleField(None, INT_TYPE), QTupleField(None, QArrayType(inner)))))
        canonical = _canonical_type(outer)
        self.assertIsInstance(canonical, QRecGroupType)
        self.assertIsNone(_canonical_type(canonical))
        self.assert_same_representation(outer, outer.unfold_lazily())
        self.assertTrue(type_to_c_tag(outer).startswith("RecGroup0_0_"))


class TestRecursiveFunctionAndArrayTypes(unittest.TestCase):
    """Recursive types whose unfoldings are function or array types are represented like their unfoldings."""

    @staticmethod
    def _fun(symbol_id: int, period: int) -> QRecType:
        """Rec(F) All(n: Int) F, with the function type written out period times."""
        t = QTypeVar("F", symbol_id, TYPE_KIND)
        for _ in range(period):
            t = QFunType((QParam("n", INT_TYPE),), t)
        return QRecType("F", symbol_id, TYPE_KIND, t)

    def test_recursive_function_type_is_a_closure(self) -> None:
        f = self._fun(9501, 1)
        self.assertIs(normalize_type(f), f.unfold_lazily())
        self.assertEqual(type_to_c_tag(f), "QClosure")
        self.assertEqual(qtype_to_c_type(f), "QClosure *")
        self.assertEqual(qtype_to_c_type(f.unfold_lazily()), "QClosure *")

    def test_recursive_function_types_in_tuples_share_a_struct(self) -> None:
        def holder(t) -> QTupleType:
            return QTupleType((QTupleField("a", INT_TYPE), QTupleField("b", t)))

        f = self._fun(9511, 1)
        self.assertEqual(type_to_c_tag(holder(f)), type_to_c_tag(holder(f.unfold_lazily())))
        self.assertEqual(type_to_c_tag(holder(f)), type_to_c_tag(holder(self._fun(9512, 2))))
        # A cycle through function types alone has a recursive function type as its canonical form
        self.assertIsInstance(_canonical_type(f.unfold_lazily()), QRecType)

    def test_recursive_array_type_is_named_by_its_body(self) -> None:
        n = QTypeVar("N", 9521, TYPE_KIND)
        nest = QRecType("N", 9521, TYPE_KIND, QArrayType(n))
        self.assertEqual(type_to_c_tag(nest), "Rec0_QArray_Self0")
        self.assertEqual(qtype_to_c_type(nest), "QArray *")
        self.assertEqual(type_to_c_tag(nest.unfold_lazily()), type_to_c_tag(nest))
        self.assertEqual(type_to_c_tag(QArrayType(QArrayType(nest))), type_to_c_tag(nest))


class TestCanonicalBinders(unittest.TestCase):
    """Equal types that differ inside binders (polymorphic and auto types) share canonical forms and descriptors."""

    @staticmethod
    def _poly(a_id: int, period: int, bound_by_list: bool = False) -> QAllType:
        """All(A::TYPE x: A l: IntList) A, with the list at the given period (or All(A <: IntList x: A) A)."""
        lst = _int_list(a_id + 1, period)
        kind = QPowerKind(lst) if bound_by_list else TYPE_KIND
        a = QTypeVar("A", a_id, kind)
        params = (QParam("x", a),) if bound_by_list else (QParam("x", a), QParam("l", lst))
        return QAllType((QQuantifier("A", a_id, kind),), QFunType(params, a))

    def assert_shared(self, a, b) -> None:
        self.assertIsNotNone(_canonical_type(a))
        self.assertIs(_canonical_type(a), _canonical_type(b))
        self.assertEqual(descriptor_form(a).tag, descriptor_form(b).tag)

    def test_polymorphic_function_types(self) -> None:
        self.assert_shared(self._poly(9701, 1), self._poly(9711, 2))
        self.assert_shared(self._poly(9721, 1, True), self._poly(9731, 3, True))
        # Different type parameters stay apart: All(A) Fun(x: A l: IntList) Int is not All(A) Fun(x: Int ...) A
        a = QTypeVar("A", 9741, TYPE_KIND)
        other = QAllType((QQuantifier("A", 9741, TYPE_KIND),),
                         QFunType((QParam("x", INT_TYPE), QParam("l", _int_list(9742, 1))), a))
        self.assertIsNot(_canonical_type(other), _canonical_type(self._poly(9751, 1)))

    def test_records_of_polymorphic_functions(self) -> None:
        def holder(t) -> QRecordType:
            return QRecordType((QRecordField("f", t),))

        self.assert_shared(holder(self._poly(9761, 1)), holder(self._poly(9771, 2)))

    def test_auto_types(self) -> None:
        def pack(x_id: int, period: int) -> QAutoType:
            x = QTypeVar("X", x_id, TYPE_KIND)
            return QAutoType("X", x_id, TYPE_KIND, (QRecordField("x", x), QRecordField("l", _int_list(x_id + 1, period))))

        self.assert_shared(pack(9781, 1), pack(9791, 2))
        self.assertEqual(type_to_c_tag(pack(9781, 1)), type_to_c_tag(pack(9791, 2)))

    def test_recursion_through_a_binder(self) -> None:
        """Rec(F) All(A::TYPE a: A f: F) A, alpha-renamed and unrolled."""

        def through(f_id: int, period: int) -> QRecType:
            t = QTypeVar("F", f_id, TYPE_KIND)
            for i in range(period):
                a = QTypeVar("A", f_id + 1 + i, TYPE_KIND)
                t = QAllType((QQuantifier("A", f_id + 1 + i, TYPE_KIND),),
                             QFunType((QParam("a", a), QParam("f", t)), a))
            return QRecType("F", f_id, TYPE_KIND, t)

        one, two = through(9801, 1), through(9811, 2)
        self.assert_shared(one, two)
        self.assertEqual(qtype_to_c_type(one), "QClosure *")
        self.assertIsNone(_canonical_type(_canonical_type(one)))

    def test_canonical_forms_not_equal_to_their_types_are_not_used(self) -> None:
        with mock.patch.object(c_types, "is_type_equal", return_value=False):
            with self.assertRaises(AssertionError):
                _canonical_type(self._poly(9821, 2))
            # Outside the tests, the type is named as written, with a warning
            with mock.patch.object(c_types, "_check_canonical", return_value=False), \
                    mock.patch.object(c_types.sys, "stderr", new_callable=io.StringIO) as stderr:
                self.assertIsNone(_canonical_type(self._poly(9831, 2)))
            self.assertIn("quest: warning: internal: canonical form", stderr.getvalue())


class TestCanonicalKindsAndVariables(unittest.TestCase):
    """Equal types that differ inside kinds, type variables' bounds, path types, or type operators share canonical
    forms and descriptors."""

    @staticmethod
    def _with_list(t) -> QTupleType:
        """Tuple t IntList end: a type with recursion, so that it has a canonical form."""
        return QTupleType((QTupleField(None, t), QTupleField(None, _int_list(9900, 1))))

    def assert_shared(self, a, b) -> None:
        self.assertIsNotNone(_canonical_type(a))
        self.assertIs(_canonical_type(a), _canonical_type(b))
        self.assertEqual(descriptor_form(a).tag, descriptor_form(b).tag)

    def test_free_type_variable_bounds(self) -> None:
        def bounded(period: int) -> QTupleType:
            return self._with_list(QTypeVar("A", 9901, QPowerKind(_int_list(9902 + period, period))))

        self.assert_shared(bounded(1), bounded(2))

    def test_operator_kinds(self) -> None:
        def operator(period: int, param_id: int) -> QTupleType:
            kind = QAllKind("X", param_id, TYPE_KIND, QPowerKind(_int_list(9910 + period, period)))
            return self._with_list(QTypeVar("F", 9920, kind))

        self.assert_shared(operator(1, 9921), operator(2, 9922))

    def test_type_operators(self) -> None:
        def operator(period: int, param_id: int) -> QTupleType:
            x = QTypeVar("X", param_id, TYPE_KIND)
            body = QTupleType((QTupleField(None, x), QTupleField(None, _int_list(9930 + period, period))))
            return self._with_list(QTypeFun((QTypeFormal("X", param_id, TYPE_KIND),), body))

        self.assert_shared(operator(1, 9941), operator(2, 9942))

    def test_path_types(self) -> None:
        def path(period: int) -> QTupleType:
            bound = QPowerKind(_int_list(9950 + period, period))
            return self._with_list(QPathType(root_name="m", root_symbol_id=9960, field_name="T", bound=bound))

        self.assert_shared(path(1), path(2))


if __name__ == "__main__":
    unittest.main()
