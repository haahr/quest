"""tools/perf/crosscalls.py, on a build directory of assembly written here:
which calls are between modules, whose member they call, and how big that
member's code is."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "tools" / "perf"))

from crosscalls import owner, scan, unitName  # noqa: E402

# A module whose exported entry tail-calls its static function, and one whose
# entry is the function itself
VECTOR = """\
.globl _qv_collections__vector_get
_qv_collections__vector_get:
\tmov x1, x0
\tb _qf_get
_qf_get:
\tldr x0, [x1]
\tldr x0, [x0, #8]
\tret
_qv_collections__vector_length:
\tldr x0, [x0, #16]
\tret
"""
MAIN = """\
_main:
\tbl _qv_collections__vector_get
\tbl _qv_collections__vector_get
\tbl _qv_collections__vector_length
\tbl _qv_main_local
\tret
"""


class TestCrossCalls(unittest.TestCase):

    def test_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build = Path(tmp)
            (build / "collections").mkdir()
            (build / "collections" / "vector.mod.s").write_text(VECTOR)
            (build / "main.main.s").write_text(MAIN)
            self.assertEqual(unitName(build, build / "collections" / "vector.mod.s"), "collections__vector")
            by_module, by_member, sizes, callers = scan(build)
            self.assertEqual(by_module["collections__vector"], 3)
            self.assertEqual(by_member["qv_collections__vector_get"], 2)
            # The static function the entry jumps to, three instructions
            self.assertEqual(sizes["qv_collections__vector_get"], 3)
            self.assertEqual(sizes["qv_collections__vector_length"], 2)
            self.assertEqual(callers["collections__vector"], {"main"})
            # A call of the unit's own member is not between modules
            self.assertNotIn("main", by_module)

    def test_owner_is_the_longest_module_prefix(self) -> None:
        modules = ["util", "util__maybe"]
        self.assertEqual(owner("qv_util__maybe_isSome", modules), "util__maybe")
        self.assertIsNone(owner("qv_other_f", modules))


if __name__ == "__main__":
    unittest.main()
