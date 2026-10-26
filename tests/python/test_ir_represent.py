"""Representation (quest/ir/represent.py, docs/ir.md §8.3).

Every golden test program is represented, verified (each value used in the representation its use requires), and
run (run_tests.py's run_ir_represented phase), and compiled to C (run_c_compiled); these tests check
the pass's plans on small programs."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.ir import nodes as ir
from quest.ir.closure import closure_convert_unit
from quest.ir.lower import lower_program
from quest.ir.represent import RejectedConversion, represent_unit
from quest.ir.specialize import specialize_unit
from quest.ir.verify import verify_unit
from quest.ir.walk import walk_statements
from quest.pipeline import CompilerContext, default_pipeline
import tests.python.helpers  # noqa: F401  (enables the invariant checks)


def represent(source: str) -> ir.Unit:
    options = CompilerOptions(stop_after="typecheck")
    ctx = CompilerContext.create(source_text=source, file_name="<test>", options=options)
    res = default_pipeline().execute(source, "<test>", options=options, ctx=ctx)
    assert res.success, [d.message for d in res.diagnostics]
    unit = lower_program(res.artifacts["typecheck"], ctx.env, print_result=True)
    unit = represent_unit(closure_convert_unit(specialize_unit(unit)))
    problems = verify_unit(unit)
    assert not problems, problems
    return unit


def plans(unit: ir.Unit, slots: bool = False) -> list[str]:
    """The kinds of the unit's conversions, in order (with slots, also its records' and variants' boxing at slots)."""
    found = []
    for body in [unit.main, *(f.body for f in unit.functions)]:
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, ir.Let) and isinstance(s.value, ir.Convert):
                if slots or s.value.plan.kind not in ("slot_box", "slot_unbox"):
                    found.append(s.value.plan.kind)
    return found


def operations(unit: ir.Unit, kind: type) -> list:
    """The unit's operations of a kind, in order."""
    found = []
    for body in [unit.main, *(f.body for f in unit.functions)]:
        for s in walk_statements(body, into_functions=False):
            if isinstance(s, (ir.Let, ir.Do)) and isinstance(s.value, kind):
                found.append(s.value)
            elif isinstance(s, kind):
                found.append(s)
    return found


class TestRepresent(unittest.TestCase):
    def test_type_parameters_hold_qval_words(self) -> None:
        # The argument boxed for the generic parameter, the result unboxed (no clone: Int calls for none)
        self.assertEqual(plans(represent("let id(A::TYPE x: A): A = x; id(:Int 3) + 1")), ["box", "unbox"])

    def test_records_viewed_at_supertypes(self) -> None:
        unit = represent(
            "Let Small = Record a: Int end; Let Big = Record a: Int b: Int end; "
            "let big: Big = record a = 1 b = 2 end; let small: Small = big; small.a"
        )
        self.assertEqual(plans(unit), ["record_view"])

    def test_variants_tags_remapped(self) -> None:
        unit = represent(
            "Let S = Variant two: Int end; Let L = Variant one: Int two: Int end; "
            "let s: S = variant two of S with 2 end; let l: L = s; l?two"
        )
        self.assertEqual(plans(unit), ["variant_tags"])

    def test_function_subtyping_adapts_closures(self) -> None:
        unit = represent(
            "Let Small = Record a: Int end; Let Big = Record a: Int b: Int end; "
            "let f(x: Small): Int = x.a; let g: All(x: Big) Int = f; g(record a = 1 b = 2 end)"
        )
        self.assertIn("adapt", plans(unit))

    def test_a_generic_var_parameter_takes_a_shadow_cell(self) -> None:
        # Called through a first-class value (a direct call would be specialized, for its var parameters)
        unit = represent(
            "let swap(A::TYPE var x: A var y: A): Ok = begin let t = x x := y y := t end; "
            "let s: All(A::TYPE var x: A var y: A) Ok = swap; let var a = 1; let var b = 2; s(:Int @a @b); a"
        )
        cells = [s for s in walk_statements(unit.main, into_functions=False)
                 if isinstance(s, ir.VarDecl) and s.var.hint == "cell"]
        self.assertEqual(len(cells), 2)
        stores = [s for s in walk_statements(unit.main, into_functions=False) if isinstance(s, ir.STORES)]
        self.assertEqual(len(stores), 2)

    def test_layouts_that_agree_are_cast(self) -> None:
        unit = represent(
            "Let Box = Fun(A::TYPE) Tuple x: A end; let get(A::TYPE b: Box(A)): A = b.x; "
            "let f: All(A::TYPE b: Box(A)) A = get; f(:Int tuple let x = 5 end)"
        )
        self.assertIn("cast", plans(unit))

    def test_records_in_slots_agree_with_generic_slots(self) -> None:
        # Slots hold records boxed, as a QVal does
        unit = represent(
            "Let P = Record a: Int end; Let Box = Fun(A::TYPE) Tuple x: A end; "
            "let get(A::TYPE b: Box(A)): A = b.x; let f: All(A::TYPE b: Box(A)) A = get; "
            "f(:P tuple let x = record a = 5 end end).a"
        )
        self.assertIn("cast", plans(unit))
        self.assertNotIn("runtime", plans(unit))

    def test_layouts_that_disagree_convert_at_run_time(self) -> None:
        # A closure returning a Bool, which a register holds differently from a QVal
        unit = represent(
            "let get(A::TYPE t: Tuple f: All(x: Int) A end): A = t.f(1); "
            "let g: All(A::TYPE t: Tuple f: All(x: Int) A end) A = get; g(:Bool tuple let f = fun(x: Int): Bool true end)"
        )
        self.assertIn("runtime", plans(unit))

    def test_bounded_parameters_are_held_at_their_own_view(self) -> None:
        # As the caller holds the type argument's values: nothing converts, mutable data included
        for source in (
            "Let P = Record a: Int end; Let Q = Record a: Int b: Int end; Let Box = Fun(A::TYPE) Tuple x: A end; "
            "let get(A <: P b: Box(A)): A = b.x; let f: All(A <: P b: Box(A)) A = get; "
            "f(:Q tuple let x = record a = 5 b = 6 end end).b",
            "Let P = Record a: Int end; Let Q = Record a: Int b: Int end; "
            "let first(A <: P xs: Array(A)): A = xs[0]; "
            "let f: All(A <: P xs: Array(A)) A = first; f(:Q array of record a = 1 b = 2 end end).b",
        ):
            with self.subTest(source=source):
                self.assertFalse({"runtime", "view", "record_view", "copy"} & set(plans(represent(source))))

    def test_copying_mutable_data_is_rejected(self) -> None:
        with self.assertRaises(RejectedConversion):
            represent(
                "let first(A::TYPE fs: Array(All(x: Int) A)): A = fs[0](1); "
                "let f: All(A::TYPE fs: Array(All(x: Int) A)) A = first; f(:Bool array of fun(x: Int): Bool true end)"
            )

    def test_records_read_from_slots_keep_their_boxes(self) -> None:
        # The record read from one tuple is stored into another in the box it was read from
        unit = represent(
            "Let P = Record a: Int end; let t = tuple let x = record a = 1 end end; "
            "let u = tuple let y = t.x end; u.y.a"
        )
        reads = [s for s in walk_statements(unit.main, into_functions=False)
                 if isinstance(s, ir.Let) and isinstance(s.value, ir.TupleField)]
        self.assertTrue(reads[0].var.boxed)
        made = operations(unit, ir.MakeTuple)
        self.assertIs(made[1].args[0], reads[0].var)
        self.assertEqual(made[1].embedded, ())
        self.assertNotIn("slot_box", plans(unit, slots=True))

    def test_records_not_read_from_slots_are_boxed_in_the_allocation(self) -> None:
        unit = represent("Let P = Record a: Int end; let p: P = record a = 1 end; let f(q: P): Int = "
                         "{tuple let x = q end}.x.a; f(p)")
        self.assertEqual([m.embedded for m in operations(unit, ir.MakeTuple)], [(0,)])

    def test_located_records_are_boxed(self) -> None:
        unit = represent(
            "Let P = Record a: Int end; let set(var r: P): Ok = r := record a = 2 end; "
            "let f(): Int = begin let var p: P = record a = 1 end set(@p) p.a end; f()"
        )
        decls = [s.var for f in unit.functions for s in walk_statements(f.body, into_functions=False)
                 if isinstance(s, ir.VarDecl)]
        self.assertTrue(all(v.boxed for v in decls if v.hint == "p"))
        self.assertTrue(any(v.boxed for f in unit.functions for v, mode in f.params if mode == "var"))

    def test_reads_of_tuples_that_may_be_proxies(self) -> None:
        unit = represent(
            "Let Big = Record a: Int b: Int end; Let Small = Record a: Int end; "
            "let get(s: Tuple x: Small n: Int end): Int = s.x.a + s.n; "
            "let t = tuple let x = record a = 1 b = 2 end let n = 3 end; get(t) + t.n"
        )
        access = {(f.index, f.access) for f in operations(unit, ir.TupleField)}
        # Through a proxy for the record, from the original for the Int; the tuple made here, directly
        self.assertIn((0, ir.PROXY), access)
        self.assertIn((1, ir.ORIGINAL), access)
        self.assertIn((1, ir.DIRECT), access)

    def test_auto_values_of_bounded_witnesses_are_stored_at_the_witness(self) -> None:
        # Generic code holds the witness's values at their own view, at which the payload stores them: no copy
        unit = represent(
            "Let Big = Variant a: Int b: Bool end; Let AnyBig = Auto A<:Big with a: A end; "
            "let mk0(A <: Big x: A): AnyBig = auto :A with x end; let mk: All(A <: Big x: A) AnyBig = mk0; "
            "mk(:Big variant a of Big with 1 end)"
        )
        self.assertEqual([c.plan for c in operations(unit, ir.Convert) if c.plan.kind == "copy"], [])

    def test_inspect_arms(self) -> None:
        unit = represent(
            "Let Big = Variant a: Int b: Bool end; Let Small = Variant b: Bool end; "
            "Let AnyBig = Auto A<:Big with a: A end; Let Counter = Auto A<:Big with a: A var n: Int end; "
            "let x: AnyBig = auto :Small with variant b of Small with true end end; "
            "let c: Counter = auto :Small with let a = variant b of Small with true end let var n = 0 end; "
            "let get(A <: Big v: AnyBig d: A): A = inspect v when A with t then t.a else d end; "
            "inspect x when Big with t then t.a?a else false end; "
            "inspect c when Small with t then t.n else 0 end"
        )
        arms = [c.arm for i in operations(unit, ir.Inspect) for c in i.cases]
        exact = next(a for a in arms if len(a.converted) == 2)
        # At the bounded parameter A, as at Big: the component converted by descriptor (A's own view, the witness's)
        others = [a for a in arms if a is not exact]
        self.assertEqual([a.converted for a in others + [exact]], [("component",)] * 2 + [("component", None)])
        self.assertFalse(any(a.exact for a in others))
        # Var components: inspected exactly, sharing the stored components, or a layout error
        self.assertTrue(exact.exact and exact.shared and exact.layout_error)

    def test_type_applications_record_their_thunks_plans(self) -> None:
        # The instance converts its argument to the generic layout (a cast) and its Int result not at all
        unit = represent(
            "Let Rec L(A::TYPE) = Option nil cons with head: A tail: L(A) end end; "
            "let rec length(A::TYPE l: L(A)): Int = if l?nil then 0 else 1 + length(:A l!cons.tail) end; "
            "let len: All(l: L(Bool)) Int = length(:Bool); len(option nil of L(Bool) end)"
        )
        self.assertEqual([[p and p.kind for p in t.plans] for t in operations(unit, ir.TypeApp)], [["cast", None]])

    def test_casts_to_types_that_cannot_be_proxies_unproxy(self) -> None:
        unit = represent(
            "Let Big = Record a: Int b: Int end; let t = tuple let x = record a = 1 b = 2 end let n = 3 end; "
            "let u: Tuple end = t; u is t"
        )
        self.assertIn("unproxy", plans(unit))
        self.assertEqual([p.access for p in operations(unit, ir.Prim) if p.op == "is"], [ir.ORIGINAL])


if __name__ == "__main__":
    unittest.main()
