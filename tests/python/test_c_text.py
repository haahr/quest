"""The C backend's literals."""

import unittest

from quest.codegen.c.types import c_char_literal, c_string_literal


class TestLiterals(unittest.TestCase):
    def test_strings_escape_by_letter_or_three_digit_octal(self):
        self.assertEqual(c_string_literal("a\"b\\c\n\t\r"), '"a\\"b\\\\c\\n\\t\\r"')
        # An escaped character followed by a hex or octal digit stays a character of its own
        self.assertEqual(c_string_literal("\x01a"), '"\\001a"')
        self.assertEqual(c_string_literal("\x017"), '"\\0017"')
        self.assertEqual(c_string_literal("\x7f\xff0"), '"\\177\\3770"')
        self.assertEqual(c_string_literal("it's"), '"it\'s"')

    def test_characters(self):
        self.assertEqual(c_char_literal("a"), "'a'")
        self.assertEqual(c_char_literal("'"), "'\\''")
        self.assertEqual(c_char_literal('"'), "'\"'")
        self.assertEqual(c_char_literal("\\"), "'\\\\'")
        self.assertEqual(c_char_literal("\n"), "'\\n'")
        self.assertEqual(c_char_literal("\x01"), "'\\001'")
        self.assertEqual(c_char_literal("\xff"), "'\\377'")


if __name__ == "__main__":
    unittest.main()
