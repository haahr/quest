"""The artifact contract may change only together with ABI_VERSION (docs/build-process.md §5.2.3)."""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "bootstrap", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from quest.build.abi import ABI_VERSION
from tests.abi.corpus import generate, read_checked_in

UPDATE_HINT = "then run `python tests/abi/corpus.py --update` and commit tests/abi/corpus"


class TestAbiCorpus(unittest.TestCase):
    def test_contract_changes_bump_the_abi_version(self) -> None:
        checked_in = read_checked_in()
        current = generate()
        recorded = checked_in.get("ABI_VERSION", "").strip()
        changed = sorted(
            rel for rel in set(checked_in) | set(current)
            if rel != "ABI_VERSION" and checked_in.get(rel) != current.get(rel)
        )
        if recorded == str(ABI_VERSION):
            self.assertEqual(
                changed, [],
                "The artifact contract changed without an ABI version bump. If these changes are intended, "
                f"bump ABI_VERSION in bootstrap/python/quest/build/abi.py, {UPDATE_HINT}.",
            )
        else:
            self.fail(
                f"ABI_VERSION is {ABI_VERSION} but the corpus was generated for version {recorded or 'none'}; "
                f"{UPDATE_HINT}. Changed corpus files: {changed or 'none'}"
            )


if __name__ == "__main__":
    unittest.main()
