"""Unit tests for Quest builtins external symbol bridge, qchecked decorator, and registry."""

import os
import shutil
import sys
import tempfile
import unittest

# Ensure bootstrap/python is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))

from quest.interpreter.builtins import (
    EXTERNAL_FUNCTIONS,
    EXTERNAL_VALUES,
    qchecked,
    resolve_external_symbol,
    set_system_args,
)
from quest.modules.stdlib import BuiltinModuleRegistry
from quest.interpreter.primitives import QuestRuntimeError
from quest.values.model import TRUE_VALUE, QuestException, QArray, QBuiltinFun, QExceptionVal, QInt, QString, QValue


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
        self.assertGreaterEqual(len(EXTERNAL_FUNCTIONS) + len(EXTERNAL_VALUES), 150)
        self.assertIn("quest_writer_put_string", EXTERNAL_FUNCTIONS)
        self.assertIsInstance(resolve_external_symbol("quest_system_args"), QArray)
        self.assertIn("QUEST_INT_MIN", EXTERNAL_VALUES)
        self.assertIn("(&quest_exc_writer_error)", EXTERNAL_VALUES)
        # Functions and values are told apart by their tables
        self.assertTrue(all(callable(f) and not isinstance(f, QValue) for f in EXTERNAL_FUNCTIONS.values()))
        self.assertTrue(all(isinstance(v, QValue) for v in EXTERNAL_VALUES.values()))
        self.assertEqual(set(EXTERNAL_FUNCTIONS) & set(EXTERNAL_VALUES), set())

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
        try:
            set_system_args(["foo", "bar"])
            args_val = resolve_external_symbol("quest_system_args")
            self.assertIsInstance(args_val, QArray)
            self.assertEqual(len(args_val.elements), 2)
            self.assertEqual([e.value for e in args_val.elements], ["foo", "bar"])
        finally:
            set_system_args(None)

    def test_non_ascii_system_arg_raises_system_error(self):
        try:
            set_system_args(["foo", "caf\u00e9"])
            with self.assertRaises(QuestException) as ctx:
                resolve_external_symbol("quest_system_args")
            self.assertEqual(ctx.exception.exc_val, resolve_external_symbol("quest_exc_system_error"))
        finally:
            set_system_args(None)

    def test_ensure_interface_and_module(self):
        iface = BuiltinModuleRegistry.ensure_interface("Writer")
        self.assertIsNotNone(iface)
        self.assertIn("putString", iface.values)

        mod = BuiltinModuleRegistry.ensure_module("writer")
        self.assertIsNotNone(mod)
        self.assertIn("putString", mod.values)



class TestAsciiCharacters(unittest.TestCase):
    """A character is ASCII, as in Typeful Programming: the builtins that would produce another raise their module's
    error."""

    def call(self, name: str, *args: QValue) -> QValue:
        return EXTERNAL_FUNCTIONS[name](*args)

    def assert_raises(self, exc_name: str, name: str, *args: QValue) -> None:
        with self.assertRaises(QuestException) as ctx:
            self.call(name, *args)
        self.assertEqual(ctx.exception.exc_val, EXTERNAL_VALUES[exc_name])

    def non_ascii_file(self, content: bytes) -> str:
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        path = os.path.join(directory, "input.txt")
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_ascii_char_range(self):
        self.assertEqual(self.call("quest_ascii_char", QInt(127)).value, "\x7f")
        self.assert_raises("quest_exc_ascii_error", "quest_ascii_char", QInt(128))

    def test_reader_get_char_rejects_non_ascii_byte(self):
        rd = self.call("quest_reader_file", QString(self.non_ascii_file(b"a\xc3\xa9")))
        self.addCleanup(self.call, "quest_reader_close", rd)
        self.assertEqual(self.call("quest_reader_get_char", rd).value, "a")
        self.assertEqual(self.call("quest_reader_more", rd), TRUE_VALUE)
        self.assert_raises("quest_exc_reader_error", "quest_reader_get_char", rd)

    def test_reader_get_string_rejects_non_ascii_byte(self):
        rd = self.call("quest_reader_file", QString(self.non_ascii_file(b"ab\xff")))
        self.addCleanup(self.call, "quest_reader_close", rd)
        self.assert_raises("quest_exc_reader_error", "quest_reader_get_string", rd, QInt(3))

    def test_dynamic_intern_rejects_non_ascii(self):
        document = '{"quest":1,"types":[],"type":"String","value":%s}'
        rd = self.call("quest_reader_file", QString(self.non_ascii_file((document % '"\\u00e9"').encode())))
        self.addCleanup(self.call, "quest_reader_close", rd)
        self.assert_raises("quest_exc_dynamic_error", "quest_dynamic_intern", rd)
        rd = self.call("quest_reader_file", QString(self.non_ascii_file((document % '"\xc3\xa9"').encode("latin-1"))))
        self.addCleanup(self.call, "quest_reader_close", rd)
        self.assert_raises("quest_exc_dynamic_error", "quest_dynamic_intern", rd)

    def test_getenv_rejects_non_ascii_value(self):
        os.environ["QUEST_TEST_NON_ASCII"] = "caf\u00e9"
        self.addCleanup(os.environ.pop, "QUEST_TEST_NON_ASCII")
        self.assert_raises("quest_exc_system_error", "quest_system_getenv", QString("QUEST_TEST_NON_ASCII"))

    def test_list_directory_rejects_non_ascii_name(self):
        path = self.non_ascii_file(b"")
        os.rename(path, os.path.join(os.path.dirname(path), "caf\u00e9"))
        self.assert_raises("quest_exc_system_error", "quest_system_list_directory", QString(os.path.dirname(path)))


if __name__ == "__main__":
    unittest.main()
