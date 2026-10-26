"""Unit tests for Quest builtins external symbol bridge, qchecked decorator, and
registry."""

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
from quest.values.model import QuestException, QArray, QBuiltinFun, QExceptionVal, QInt, QString, QValue


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
        self.assertIn("quest_system_args", EXTERNAL_VALUES)
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
        orig_args = EXTERNAL_VALUES.get("quest_system_args")
        try:
            set_system_args(["foo", "bar"])
            args_val = resolve_external_symbol("quest_system_args")
            self.assertIsInstance(args_val, QArray)
            self.assertEqual(len(args_val.elements), 2)
            self.assertEqual([e.value for e in args_val.elements], ["foo", "bar"])
        finally:
            EXTERNAL_VALUES["quest_system_args"] = orig_args

    def test_ensure_interface_and_module(self):
        iface = BuiltinModuleRegistry.ensure_interface("Writer")
        self.assertIsNotNone(iface)
        self.assertIn("putString", iface.values)

        mod = BuiltinModuleRegistry.ensure_module("writer")
        self.assertIsNotNone(mod)
        self.assertIn("putString", mod.values)


class TestByteCharacters(unittest.TestCase):
    """A character is a byte, as in Typeful Programming and C: the builtins pass
    bytes above 127 through unchanged."""

    def call(self, name: str, *args: QValue) -> QValue:
        return EXTERNAL_FUNCTIONS[name](*args)

    def directory(self) -> str:
        directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, directory)
        return directory

    def test_ascii_char_range(self):
        self.assertEqual(self.call("quest_ascii_char", QInt(255)).value, "\xff")
        with self.assertRaises(QuestException) as ctx:
            self.call("quest_ascii_char", QInt(256))
        self.assertEqual(ctx.exception.exc_val, EXTERNAL_VALUES["quest_exc_ascii_error"])

    def test_files_are_read_and_written_a_byte_per_character(self):
        # The file's name is bytes too: the UTF-8 of é, as the OS sees it
        path = os.path.join(self.directory(), "caf\u00e9").encode()
        name = QString(path.decode("latin-1"))
        w = self.call("quest_writer_file", name)
        self.call("quest_writer_put_string", w, QString("a\xc3\xa9\xff"))
        self.call("quest_writer_close", w)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"a\xc3\xa9\xff")
        rd = self.call("quest_reader_file", name)
        self.addCleanup(self.call, "quest_reader_close", rd)
        self.assertEqual(self.call("quest_reader_get_char", rd).value, "a")
        self.assertEqual(self.call("quest_reader_get_string", rd, QInt(3)).value, "\xc3\xa9\xff")

    def test_os_strings_are_bytes(self):
        directory = self.directory()
        open(os.path.join(directory, "caf\u00e9"), "w").close()
        names = self.call("quest_system_list_directory", QString(directory))
        self.assertEqual([n.value for n in names.elements], ["caf\xc3\xa9"])
        os.environ["QUEST_TEST_BYTES"] = "na\u00efve"
        self.addCleanup(os.environ.pop, "QUEST_TEST_BYTES")
        self.assertEqual(self.call("quest_system_getenv", QString("QUEST_TEST_BYTES")).value, "na\xc3\xafve")
        try:
            set_system_args(["program", "caf\u00e9"])
            args = resolve_external_symbol("quest_system_args")
            self.assertEqual([a.value for a in args.elements], ["program", "caf\xc3\xa9"])
        finally:
            set_system_args(sys.argv)

    def test_dynamic_strings_are_bytes(self):
        document = '{"quest":1,"types":[],"type":"String","value":%s}'
        path = os.path.join(self.directory(), "document.json")
        for value, expected in (('"\\u00e9\xe9"', "\xe9\xc3\xa9"), ('"\\u0100"', None)):
            with open(path, "w", encoding="utf-8") as f:
                f.write(document % value)
            rd = self.call("quest_reader_file", QString(path))
            self.addCleanup(self.call, "quest_reader_close", rd)
            if expected is None:
                with self.assertRaises(QuestException) as ctx:
                    self.call("quest_dynamic_intern", rd)
                self.assertEqual(ctx.exception.exc_val, EXTERNAL_VALUES["quest_exc_dynamic_error"])
            else:
                self.assertEqual(self.call("quest_dynamic_intern", rd).value.elements[0].value, expected)


if __name__ == "__main__":
    unittest.main()
