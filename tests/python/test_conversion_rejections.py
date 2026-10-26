"""Cells of the conversion matrix (tests/conversions/generate.py) that C
generation rejects: unspecialized calls that would have to copy mutable data
laid out differently. The error suite cannot express errors of C generation, so
they are checked here."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "bootstrap" / "python"))
sys.path.insert(0, str(ROOT_DIR / "tests" / "conversions"))
os.environ["QUEST_CHECK_CANONICAL"] = "1"

import generate  # noqa: E402
from quest.pipeline import compile_pipeline  # noqa: E402


class TestConversionRejections(unittest.TestCase):
    def test_rejected_cells(self) -> None:
        self.assertTrue(generate.REJECTED)
        for (context, shape, arg), message in sorted(generate.REJECTED.items()):
            with self.subTest(context=context, shape=shape, arg=arg):
                res = compile_pipeline().execute(generate.program_for(context, shape, arg), "<conversion>")
                self.assertFalse(res.success)
                self.assertIn(message, " ".join(d.message for d in res.diagnostics))

    def test_rejected_and_known_cells_exist(self) -> None:
        cells = {
            (context.name, shape.name, arg.name) for context in generate.CONTEXTS
            for shape, arg in generate.cells_of(context)
        }
        self.assertLessEqual(set(generate.REJECTED), cells)
        self.assertLessEqual(set(generate.KNOWN_FAILURES), cells)


if __name__ == "__main__":
    unittest.main()
