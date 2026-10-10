"""Unit tests for Phase 5: Exceptions, Dynamic Types, and Type Inspection."""

import unittest

from quest.env import Environment, ValueSymbol
from quest.typed_ast import (
    TypedException,
    TypedInspect,
    TypedRaise,
    TypedTry,
)
from quest.types import (
    BOTTOM_TYPE,
    DYNAMIC_TYPE,
    INT_TYPE,
    OK_TYPE,
    QExceptionType,
    REAL_TYPE,
    STRING_TYPE,
    is_subtype,
)
from tests.python.helpers import assert_pipeline_success, check_test_expr, synth_test_expr


class Phase5ExceptionsDynamicTest(unittest.TestCase):
    """Test suite for exceptions, divergent raise typing, dynamic values, and inspect."""

    def test_bottom_subtyping(self) -> None:
        """Bottom is a subtype of every type (Int, String, Dynamic, etc.)."""
        self.assertTrue(is_subtype(BOTTOM_TYPE, INT_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, REAL_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, STRING_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, DYNAMIC_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, OK_TYPE))

    def test_exception_declaration_and_payload(self) -> None:
        """exception DivByZero: Ok end and exception Fail: String end."""
        env = Environment()

        # exception DivByZero: Ok end
        typed_exc1 = synth_test_expr("exception DivByZero: Ok end", env)
        self.assertIsInstance(typed_exc1, TypedException)
        self.assertEqual(typed_exc1.type_val, QExceptionType(OK_TYPE))

        # Check declared in env
        sym1 = env.lookup_value("DivByZero")
        self.assertIsNotNone(sym1)
        self.assertEqual(sym1.type_val, QExceptionType(OK_TYPE))

        # exception Fail: String end
        typed_exc2 = synth_test_expr("exception Fail: String end", env)
        self.assertEqual(typed_exc2.type_val, QExceptionType(STRING_TYPE))

    def test_raise_divergent_control_flow(self) -> None:
        """raise in checking mode satisfies any expected type via bottom divergence."""
        env = Environment()
        env.current_scope.declare_value(ValueSymbol(name="DivByZero", type_val=QExceptionType(OK_TYPE)))

        # if cond then raise DivByZero end else 42 end
        checked_if = check_test_expr("if true then raise DivByZero end else 42 end", INT_TYPE, env)
        self.assertEqual(checked_if.type_val, INT_TYPE)

        # In synthesis mode: raise without as Type synthesizes Ok
        typed_raise = synth_test_expr("raise DivByZero end", env)
        self.assertIsInstance(typed_raise, TypedRaise)
        self.assertEqual(typed_raise.type_val, OK_TYPE)

        # raise with explicit as Real
        typed_raise_as = synth_test_expr("raise DivByZero as Real end", env)
        self.assertEqual(typed_raise_as.type_val, REAL_TYPE)

    def test_raise_payload_verification(self) -> None:
        """raise with payload checks payload type against exception definition. A wrong or missing payload is an
        error test (tests/errors/typecheck/exceptions)."""
        env = Environment()
        env.current_scope.declare_value(ValueSymbol(name="Fail", type_val=QExceptionType(STRING_TYPE)))

        # Valid payload: raise Fail with "error" end
        typed_ok = synth_test_expr('raise Fail with "error" end', env)
        self.assertIsInstance(typed_ok, TypedRaise)

    def test_try_when_handling(self) -> None:
        """try body when DivByZero then 0 when Fail with msg then 1 else 2 end."""
        env = Environment()
        env.current_scope.declare_value(ValueSymbol(name="DivByZero", type_val=QExceptionType(OK_TYPE)))
        env.current_scope.declare_value(ValueSymbol(name="Fail", type_val=QExceptionType(STRING_TYPE)))

        typed_try = synth_test_expr(
            "try 100 when DivByZero then 0 when Fail with msg then 1 else 2 end",
            env,
        )
        self.assertIsInstance(typed_try, TypedTry)
        self.assertEqual(typed_try.type_val, INT_TYPE)

    def test_dynamic_polymorphic_constructor(self) -> None:
        """dynamic.new(42), dynamic.new("text"), and dynamic.new(:Int 42) have type Dynamic."""
        env = Environment()
        assert_pipeline_success(
            """
            import dynamic: Dynamic;
            let d1 = dynamic.new(42);
            let d2 = dynamic.new("text");
            let d3 = dynamic.new(:Int 42);
            """,
            env=env,
        )
        for name in ("d1", "d2", "d3"):
            self.assertEqual(env.lookup_value(name).type_val.evaluate_lazily(env), DYNAMIC_TYPE)

    def test_inspect_dynamic(self) -> None:
        """inspect d when Int with n then n.a when String with s then 0 end (optional else): the binder is the
        dynamic value's component tuple. A target without an auto type is an error test
        (tests/errors/typecheck/dynamic/inspect_non_auto)."""
        env = Environment()
        env.current_scope.declare_value(ValueSymbol(name="d", type_val=DYNAMIC_TYPE))

        # inspect without else clause
        typed_inspect = synth_test_expr(
            "inspect d when Int with n then n.a when String with s then 0 end",
            env,
        )
        self.assertIsInstance(typed_inspect, TypedInspect)
        self.assertEqual(typed_inspect.type_val, INT_TYPE)


if __name__ == "__main__":
    unittest.main()
