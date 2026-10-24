"""Unit tests for Quest builtins external symbol bridge, qchecked decorator, and registry."""

import os
import sys
import unittest

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.interpreter.builtins import EXTERNAL_SYMBOLS, qchecked, resolve_external_symbol, set_system_args
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.interpreter.primitives import QuestRuntimeError
from quest.values.model import QuestException, QArray, QBuiltinFun, QExceptionVal, QInt, QString


class TestBuiltinWrappers(unittest.TestCase):
    """Tests for qchecked decorator and ModuleBuilder."""

    def test_qchecked_success(self):
        err_exc = QExceptionVal("test.error")

        @qchecked(err_exc, QInt, QString)
        def dummy(n: QInt, s: QString) -> str:
            return f"{s.value}:{n.value}"

        res = dummy(QInt(42), QString("answer"))
        self.assertEqual(res, "answer:42")

    def test_qchecked_type_mismatch_raises_error_exc(self):
        err_exc = QExceptionVal("test.error")

        @qchecked(err_exc, QInt, QString)
        def dummy(n: QInt, s: QString) -> str:
            return f"{s.value}:{n.value}"

        with self.assertRaises(QuestException) as ctx:
            dummy(QString("not-int"), QString("valid"))
        self.assertEqual(ctx.exception.exc_val, err_exc)

    def test_qchecked_arg_count_mismatch_raises_error_exc(self):
        err_exc = QExceptionVal("test.error")

        @qchecked(err_exc, QInt)
        def dummy(n: QInt) -> int:
            return n.value

        with self.assertRaises(QuestException) as ctx:
            dummy()
        self.assertEqual(ctx.exception.exc_val, err_exc)

        with self.assertRaises(QuestException) as ctx:
            dummy(QInt(1), QInt(2))
        self.assertEqual(ctx.exception.exc_val, err_exc)

    def test_qchecked_without_error_exc_raises_descriptive_error(self):
        @qchecked(None, QInt)
        def dummy(n: QInt) -> int:
            return n.value

        with self.assertRaises(QuestRuntimeError) as ctx:
            dummy(QString("hello"))
        self.assertIn("Expected argument of type QInt, got QString", str(ctx.exception))

        with self.assertRaises(QuestRuntimeError) as ctx:
            dummy()
        self.assertIn("Expected 1 arguments, got 0", str(ctx.exception))

    def test_external_symbols_populated(self):
        self.assertGreaterEqual(len(EXTERNAL_SYMBOLS), 150)
        self.assertIn("quest_writer_put_string", EXTERNAL_SYMBOLS)
        self.assertIn("quest_system_args", EXTERNAL_SYMBOLS)
        self.assertIn("QUEST_INT_MIN", EXTERNAL_SYMBOLS)
        self.assertIn("(&quest_exc_writer_error)", EXTERNAL_SYMBOLS)

    def test_resolve_external_symbol_function(self):
        sym_val = resolve_external_symbol("quest_writer_put_string")
        self.assertIsInstance(sym_val, QBuiltinFun)

    def test_resolve_external_symbol_exception(self):
        exc_val = resolve_external_symbol("(&quest_exc_writer_error)")
        self.assertIsInstance(exc_val, QExceptionVal)
        self.assertEqual(exc_val.name, "writer.error")

        exc_val2 = resolve_external_symbol("quest_exc_writer_error")
        self.assertEqual(exc_val2, exc_val)

    def test_resolve_external_symbol_constant(self):
        int_min = resolve_external_symbol("QUEST_INT_MIN")
        self.assertIsInstance(int_min, QInt)
        self.assertEqual(int_min.value, -(2**63))

    def test_resolve_external_symbol_unknown_raises(self):
        with self.assertRaises(QuestRuntimeError) as ctx:
            resolve_external_symbol("quest_nonexistent_symbol_xyz")
        self.assertIn("Undefined external symbol", str(ctx.exception))

    def test_set_system_args(self):
        orig_args = EXTERNAL_SYMBOLS.get("quest_system_args")
        try:
            set_system_args(["foo", "bar"])
            args_val = resolve_external_symbol("quest_system_args")
            self.assertIsInstance(args_val, QArray)
            self.assertEqual(len(args_val.elements), 2)
            self.assertEqual([e.value for e in args_val.elements], ["foo", "bar"])
        finally:
            EXTERNAL_SYMBOLS["quest_system_args"] = orig_args

    def test_ensure_interface_and_module(self):
        iface = BuiltinModuleRegistry.ensure_interface("Writer")
        self.assertIsNotNone(iface)
        self.assertIn("putString", iface.values)

        mod = BuiltinModuleRegistry.ensure_module("writer")
        self.assertIsNotNone(mod)
        self.assertIn("putString", mod.values)



if __name__ == "__main__":
    unittest.main()
