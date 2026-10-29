"""The C backend's text: its literals, and the rules that keep its formatting of
C translatable to Quest line by line (docs/converting-python-to-quest.md, rule
6)."""

import ast
import math
import unittest
from pathlib import Path

from quest.codegen.syntax import c_char, c_int, c_int_literal, c_real, c_string, call, comma, index_table
from quest.diagnostics import QuestCompilerError
from quest.interpreter.builtins import _conv_real
from quest.syntax.tokenizer import Tokenizer
from quest.syntax.tokens import TokenKind
from quest.values.model import QReal

_ROOT = Path(__file__).resolve().parents[2]
_CODEGEN = _ROOT / "bootstrap" / "python" / "quest" / "codegen"
# The files that spell C (syntax.py, which defines the vocabulary, may join and
# format)
_FILES = [
    _CODEGEN / "c" / "printer.py",
    _CODEGEN / "c" / "declarations.py",
    _CODEGEN / "c" / "types.py",
    _CODEGEN / "c" / "headers.py",
    _CODEGEN / "layout.py",
    _CODEGEN / "symbols.py",
    _CODEGEN / "descriptors.py",
]


class TestLiterals(unittest.TestCase):
    def test_strings_escape_by_letter_or_three_digit_octal(self):
        self.assertEqual(c_string("a\"b\\c\n\t\r"), '"a\\"b\\\\c\\n\\t\\r"')
        # An escaped character followed by a hex or octal digit stays a
        # character of its own
        self.assertEqual(c_string("\x01a"), '"\\001a"')
        self.assertEqual(c_string("\x017"), '"\\0017"')
        self.assertEqual(c_string("\x7f\xff0"), '"\\177\\3770"')
        self.assertEqual(c_string("it's"), '"it\'s"')

    def test_characters(self):
        self.assertEqual(c_char("a"), "'a'")
        self.assertEqual(c_char("'"), "'\\''")
        self.assertEqual(c_char('"'), "'\"'")
        self.assertEqual(c_char("\\"), "'\\\\'")
        self.assertEqual(c_char("\n"), "'\\n'")
        self.assertEqual(c_char("\x01"), "'\\001'")
        self.assertEqual(c_char("\xff"), "'\\377'")

    def test_numbers(self):
        self.assertEqual(c_int(0), "0")
        self.assertEqual(c_int(42), "42")
        with self.assertRaises(AssertionError):
            c_int(-1)
        self.assertEqual(c_int_literal(5), "5LL")
        self.assertEqual(c_int_literal(-5), "(-5LL)")
        self.assertEqual(c_int_literal(-9223372036854775807), "(-9223372036854775807LL)")
        self.assertEqual(c_real(1.0), "1.0")
        self.assertEqual(c_real(-2.5), "-2.5")
        self.assertEqual(c_real(1e100), "1e+100")
        self.assertEqual(c_real(float("inf")), "INFINITY")
        self.assertEqual(c_real(float("-inf")), "(-INFINITY)")

    def test_reals_are_conv_reals_with_a_c_sign(self):
        """c_real's port formats the magnitude with conv.real (the runtime's
        quest_format_real, as the interpreter's _conv_real mirrors it) and
        writes the sign as C does: so the two must agree on every real, here
        every real constant of the test corpus and the library (but infinities),
        and the edge cases."""
        values = {0.0, -0.0, 1.0, 1e-5, 9.99e-6, 1e16, 9999999999999998.0, 1e100, -1e-300, 0.1, 2.0 / 3.0}
        for directory in (_ROOT / "tests" / "source", _ROOT / "lib"):
            for path in directory.rglob("*.quest"):
                try:
                    tokens = Tokenizer(path.read_text(), str(path)).tokenize_all()
                except QuestCompilerError:
                    continue
                values.update(t.value for t in tokens if t.kind == TokenKind.REAL_LIT)
        self.assertGreater(len(values), 20)
        # (An infinity is INFINITY in C, which test_numbers tests)
        for r in sorted(v for v in values if not math.isinf(v)):
            for v in (r, -r):
                digits = _conv_real(QReal(abs(v))).value
                ported = ("-" if math.copysign(1.0, v) < 0 else "") + digits
                self.assertEqual(c_real(v), ported, v)

    def test_forms(self):
        self.assertEqual(comma(["a", "b"]), "a, b")
        self.assertEqual(call("f", []), "f()")
        self.assertEqual(call("f", ["a", "b"]), "f(a, b)")
        self.assertEqual(index_table([2, 0, 1]), "((const int64_t[]){ 2LL, 0LL, 1LL })")


class TestBackendFormatting(unittest.TestCase):
    """Every value the backend interpolates into C text is a string, joined only
    by syntax.py: no f-string formats a value with a format spec or a
    conversion, and nothing else joins."""

    def test_no_format_specs_or_conversions(self):
        found = []
        for path in _FILES:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.FormattedValue) and (node.conversion != -1 or node.format_spec is not None):
                    found.append(f"{path.name}:{node.lineno}")
        self.assertEqual(found, [])

    def test_no_joins(self):
        found = []
        for path in _FILES:
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Attribute) and node.attr == "join":
                    found.append(f"{path.name}:{node.lineno}")
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
