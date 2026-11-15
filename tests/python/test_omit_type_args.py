"""The parts of tools/omit-type-args and tools/compare-codegen that need no
compiler: reading --report-inferable's lines, deleting type arguments by their
byte ranges, finding the call an error is in, and normalizing assembly."""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools"))

from compare_codegen import normalize  # noqa: E402
from omit_type_args import FROM_ARGUMENTS, WITH_EXPECTED, Call, enclosing, omit, parse_report  # noqa: E402

SOURCE = b"""let a = f(:Int x)
let b = g(:maybe.T(Int) y
    z)
let c = h(:Int)
"""


class TestOmitTypeArgs(unittest.TestCase):

    def report(self) -> list[Call]:
        text = "\n".join([
            "questlang/x.mod.quest:1:9: type arguments can be inferred from the arguments [10 15]",
            "questlang/x.mod.quest:2:9: type arguments can be inferred from the arguments [28 42]",
            "questlang/x.mod.quest:4:9: type arguments can be inferred with the expected type [61 65]",
            # Duplicates, other directories, and other lines are left out
            "questlang/x.mod.quest:1:9: type arguments can be inferred from the arguments [10 15]",
            "lib/util/maybe.mod.quest:3:5: type arguments can be inferred from the arguments [1 2]",
            "quest: building stage 2",
        ])
        return parse_report(text, Path("/root"), read=lambda path: SOURCE)

    def test_parse_report(self) -> None:
        calls = self.report()
        self.assertEqual([(c.offset, c.start, c.end, c.kind) for c in calls], [
            (8, 10, 15, FROM_ARGUMENTS), (26, 28, 42, FROM_ARGUMENTS), (59, 61, 65, WITH_EXPECTED)])
        self.assertEqual(SOURCE[calls[0].start:calls[0].end], b":Int ")
        self.assertEqual(SOURCE[calls[2].start:calls[2].end], b":Int")

    def test_absolute_paths_under_the_root(self) -> None:
        calls = parse_report("/root/questlang/x.mod.quest:1:9: type arguments can be inferred from the arguments "
                             "[10 15]\n/elsewhere/questlang/y.mod.quest:1:9: type arguments can be inferred from the "
                             "arguments [10 15]", Path("/root"), read=lambda path: SOURCE)
        self.assertEqual([c.file for c in calls], ["questlang/x.mod.quest"])

    def test_omit(self) -> None:
        edited = omit(SOURCE, self.report())
        self.assertEqual(edited.data, b"""let a = f(x)
let b = g(y
    z)
let c = h()
""")
        # Where each call starts in the edited text
        self.assertEqual(sorted(edited.offsets.values()), [8, 21, 40])
        self.assertEqual(edited.data[40:43], b"h()")

    def test_omit_requires_type_arguments(self) -> None:
        wrong = Call("questlang/x.mod.quest", 8, 11, 15, FROM_ARGUMENTS)
        with self.assertRaises(ValueError):
            omit(SOURCE, [wrong])

    def test_enclosing(self) -> None:
        calls = self.report()
        edited = omit(SOURCE, calls)
        # An error at g's second argument is in g's call; one before any call is in none
        self.assertEqual(enclosing(edited, edited.data.index(b"z")), calls[1])
        self.assertEqual(enclosing(edited, 2), None)


class TestCompareCodegen(unittest.TestCase):

    def test_normalize(self) -> None:
        tree = Path("/a/tree")
        text = "\n".join([
            ".file 1 \"/a/tree/questlang\" \"x.mod.quest\"",
            "\t.loc 1 20 25",
            "\tmov x0, x1",
            ".asciz \"questlang/x.mod.quest:51:49\"",
        ])
        self.assertEqual(normalize(text, tree), "\n".join([
            ".file 1 \"TREE/questlang\" \"x.mod.quest\"",
            "\tmov x0, x1",
            ".asciz \"questlang/x.mod.quest:L:C\"",
        ]) + "\n")


if __name__ == "__main__":
    unittest.main()
