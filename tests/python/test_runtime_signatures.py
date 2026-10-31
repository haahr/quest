"""Unit test that the runtime's functions take and return no C type narrower
than a word but bool and QChar (docs/arm64.md section 10, hazard 3).

The arm64 backend places arguments past the registers as Darwin does, at their
C types' sizes and alignments, and extends a narrow result after a call; it
knows a C bool or QChar as narrow (the SSA's narrow arguments, ssa.md section
2.2) and every other type as 8 bytes or a 16-byte composite. A runtime function
that took or returned an int, a float, or a short would be passed wrongly, so
this test fails first."""

import re
import unittest
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent.parent / "runtime"

# The C types narrower than a word that the backend does not know (bool and
# QChar it does)
NARROW = {"int", "unsigned", "unsigned int", "signed", "short", "unsigned short", "char", "signed char",
          "unsigned char", "int8_t", "uint8_t", "int16_t", "uint16_t", "int32_t", "uint32_t", "float"}

# Functions that take a C int, which a call passes in a register (one of the
# first eight integer arguments' places), where Darwin's ABI leaves a 32-bit
# value the callee reads: argc, which the program's main passes on, as main
# received it, in the first parameter
REGISTER_INTS = {("quest_system_init", 0), ("quest_builtins_init", 0)}

# A function's declaration, or an inline function's definition, whose
# out-of-line copy (runtime/quest_inline.c) native code calls: its result type,
# its name, and its parameters
DECLARATION = re.compile(r"^([A-Za-z_][\w \t*]*?[\s*])(quest_\w+)\s*\(([^;{]*?)\)\s*[;{]", re.MULTILINE | re.DOTALL)


def without_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", " ", re.sub(r"//[^\n]*", "", text), flags=re.DOTALL)


def by_value(declared: str) -> str:
    """The type a parameter or result is passed as, without its name and
    qualifiers, or "" if it is a pointer (a word, whatever it points to)."""
    if "*" in declared or "[" in declared:
        return ""
    words = [w for w in declared.split() if w not in ("const", "volatile", "static", "extern", "inline")]
    return " ".join(words)


def declarations() -> list[tuple[str, str, list[str]]]:
    """Each runtime function's name, result type, and parameters' types."""
    found = []
    for header in sorted(RUNTIME_DIR.glob("*.h")):
        for result, name, params in DECLARATION.findall(without_comments(header.read_text(encoding="utf-8"))):
            if "(" in params:
                continue  # a parameter of function type: a pointer
            types = []
            for param in params.split(","):
                param = " ".join(param.split())
                if param in ("", "void", "..."):
                    continue
                # Without the parameter's name, when it has one
                parts = param.rsplit(None, 1)
                declared = parts[0] if len(parts) == 2 and not parts[1].startswith("*") and parts[1] not in NARROW \
                    else param
                if len(parts) == 2 and parts[1].startswith("*"):
                    declared = parts[0] + " *"
                types.append(declared)
            found.append((name, result.strip(), types))
    return found


class TestRuntimeSignatures(unittest.TestCase):
    def test_it_finds_the_runtimes_functions(self) -> None:
        names = {name for name, _, _ in declarations()}
        self.assertGreater(len(names), 150)
        for name in ("quest_ascii_char", "quest_string_alloc", "quest_proxy_element", "quest_writer_put_char"):
            self.assertIn(name, names)

    def test_no_narrow_types_but_bool_and_qchar(self) -> None:
        problems = []
        for name, result, params in declarations():
            if by_value(result) in NARROW:
                problems.append(f"{name}: its result is {result!r}")
            for i, declared in enumerate(params):
                if by_value(declared) in NARROW and (name, i) not in REGISTER_INTS:
                    problems.append(f"{name}: parameter {i} is {declared!r}")
        self.assertEqual(problems, [], "a runtime function takes or returns a narrow C type the arm64 backend does "
                         "not place (docs/arm64.md section 10, hazard 3)")

    def test_the_check_can_fail(self) -> None:
        self.assertEqual(by_value("int"), "int")
        self.assertEqual(by_value("const unsigned char"), "unsigned char")
        self.assertEqual(by_value("const char *"), "")
        self.assertIn(by_value("uint32_t"), NARROW)
        self.assertNotIn(by_value("QChar"), NARROW)


if __name__ == "__main__":
    unittest.main()
