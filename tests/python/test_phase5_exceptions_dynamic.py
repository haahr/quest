"""Unit tests for the Bottom type. Typing exceptions, raise, try, dynamic values, and inspect is the golden test
tests/source/language/core_exceptions_dynamic, and rejecting them the error tests in tests/errors/typecheck."""

import unittest

from quest.types import (
    BOTTOM_TYPE,
    DYNAMIC_TYPE,
    INT_TYPE,
    OK_TYPE,
    REAL_TYPE,
    STRING_TYPE,
    is_subtype,
)


class Phase5ExceptionsDynamicTest(unittest.TestCase):
    """Bottom, the type of a raise, is a subtype of every type."""

    def test_bottom_subtyping(self) -> None:
        """Bottom is a subtype of every type (Int, String, Dynamic, etc.)."""
        self.assertTrue(is_subtype(BOTTOM_TYPE, INT_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, REAL_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, STRING_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, DYNAMIC_TYPE))
        self.assertTrue(is_subtype(BOTTOM_TYPE, OK_TYPE))


if __name__ == "__main__":
    unittest.main()
