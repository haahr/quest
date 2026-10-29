"""The self-hosted compiler's table of the standard library's externals
(questlang/codegen/externals.mod.quest) is what tools/externals generates from
lib/ (docs/c-representation.md section 6.2)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools.externals import TABLE, table_text


class TestExternalsTable(unittest.TestCase):
    def test_table_matches_lib(self) -> None:
        self.assertEqual(
            TABLE.read_text(encoding="utf-8"), table_text(),
            "questlang/codegen/externals.mod.quest is out of date with lib/: run tools/externals, then bump "
            "ABI_VERSION and regenerate the ABI corpora (tests/abi/corpus.py)",
        )


if __name__ == "__main__":
    unittest.main()
