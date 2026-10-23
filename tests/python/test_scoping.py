"""The well-scopedness check of typed programs (quest/typechecker/scoping.py)."""

from __future__ import annotations

import dataclasses
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.config import CompilerOptions
from quest.env import ValueSymbol
from quest.typed_ast import TypedBlock, TypedFun, TypedLetValue, TypedVar
from quest.typechecker.scoping import check_well_scoped
from quest.types import INT_TYPE, TYPE_KIND, QAllType, QPowerKind, QQuantifier, QTypeVar
from tests.python.helpers import run_source


def _typecheck(source: str):
    # The check runs inside the type checker in tests; it is called directly here on altered programs
    saved = os.environ.pop("QUEST_CHECK_SCOPES", None)
    try:
        res = run_source(source, options=CompilerOptions(stop_after="typecheck"))
    finally:
        if saved is not None:
            os.environ["QUEST_CHECK_SCOPES"] = saved
    assert res.success, [d.message for d in res.diagnostics]
    return res.artifacts["typecheck"]


def _replace_first(node, cls, fn):
    """node with the first node of class cls (in field order) replaced by fn(it)."""
    done = [False]

    def walk(n):
        if done[0]:
            return n
        if isinstance(n, cls):
            done[0] = True
            return fn(n)
        if isinstance(n, tuple):
            return tuple(walk(x) for x in n)
        if dataclasses.is_dataclass(n) and not isinstance(n, type) and type(n).__module__ == "quest.typed_ast":
            return dataclasses.replace(n, **{f.name: walk(getattr(n, f.name)) for f in dataclasses.fields(n)})
        return n

    result = walk(node)
    assert done[0]
    return result


class TestScoping(unittest.TestCase):
    def test_well_scoped_programs(self) -> None:
        for source in (
            "let f(x: Int): Int = begin let y = x + 1; let rec g(n: Int): Int = if n is 0 then y else g(n - 1) end; g(x) end; f(2)",
            "let id(A::TYPE x: A): A = begin let inner(B::TYPE y: B): B = y; inner(:A x) end; id(:Int 1)",
            "let g(A::TYPE B <: A x: B): A = x; g(:Int :Int 4)",
            "let x = 1; let x = x + 1 and y = x; for i = 0 upto 2 do ok end; x + y",
            "let f: All(B::TYPE x: B) B = fun(A::TYPE x: A): A x; f(:Int 3)",
        ):
            with self.subTest(source=source):
                self.assertEqual(check_well_scoped(_typecheck(source)), [])

    def test_variable_outside_its_block(self) -> None:
        prog = _typecheck("let f(x: Int): Int = begin let y = x + 1; y end; let z = 0; f(z)")
        # Give the program's last use of a top-level variable the symbol of the block-local y
        fun = prog.phrases[0].value
        local_y = fun.body.bindings[0].symbol
        broken = _replace_first(
            prog.phrases[2], TypedVar, lambda v: dataclasses.replace(v, symbol=local_y, name="y")
        )
        prog = dataclasses.replace(prog, phrases=prog.phrases[:2] + (broken,))
        problems = check_well_scoped(prog)
        self.assertEqual(len(problems), 1)
        self.assertIn("'y'", problems[0])
        self.assertIn("outside the scope of its binder", problems[0])

    def test_parameter_annotations_with_other_symbols(self) -> None:
        # The bug the check was made for: a function's parameters naming its type parameter by another symbol
        prog = _typecheck("let id(A::TYPE x: A): A = x; id(:Int 1)")
        fun = prog.phrases[0].value
        (quant,) = fun.type_val.quantifiers
        other = QQuantifier(name="A", symbol_id=quant.symbol_id + 100000, bound=quant.bound)
        renamed = QTypeVar(name="A", symbol_id=other.symbol_id, bound=other.bound)
        stray_type = dataclasses.replace(fun, type_val=QAllType(quantifiers=(other,), body=fun.type_val.body.substitute({quant.symbol_id: renamed})))
        problems = check_well_scoped(dataclasses.replace(prog, phrases=(dataclasses.replace(prog.phrases[0], value=stray_type),) + prog.phrases[1:]))
        self.assertTrue(any("are not the quantifiers" in p for p in problems), problems)
        self.assertTrue(any("outside their function" in p for p in problems), problems)


class TestQuantifierTelescopes(unittest.TestCase):
    def test_a_bound_referring_to_an_earlier_quantifier_is_bound_there(self) -> None:
        a = QQuantifier(name="A", symbol_id=910001, bound=TYPE_KIND)
        a_var = QTypeVar(name="A", symbol_id=a.symbol_id, bound=TYPE_KIND)
        b = QQuantifier(name="B", symbol_id=910002, bound=QPowerKind(a_var))
        t = QAllType(quantifiers=(a, b), body=QTypeVar(name="B", symbol_id=b.symbol_id, bound=b.bound))
        self.assertEqual(set(t._fv), set())
        # Substituting for A from outside does not reach the bound that refers to the quantifier A
        self.assertIs(t.substitute({a.symbol_id: INT_TYPE}), t)
        # A free variable in a bound is still free, and substituted
        c_var = QTypeVar(name="C", symbol_id=910003, bound=TYPE_KIND)
        u = QAllType(quantifiers=(QQuantifier(name="D", symbol_id=910004, bound=QPowerKind(c_var)),), body=INT_TYPE)
        self.assertEqual(set(u._fv), {c_var.symbol_id})
        self.assertIs(u.substitute({c_var.symbol_id: INT_TYPE}).quantifiers[0].bound.bound, INT_TYPE)


if __name__ == "__main__":
    unittest.main()
