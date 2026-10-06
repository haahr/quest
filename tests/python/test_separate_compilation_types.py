"""Separate compilation must type programs exactly as elaborating module and interface sources does.

In C compilation mode imported interfaces are read back from compiled .qi files and imported modules
are known only through their interfaces. These tests check that this path agrees with the source
path both semantically (abstract types stay abstract and distinct per module) and in the typed AST
dump (type names print identically).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DRIVER = ROOT_DIR / "bootstrap" / "python" / "quest_driver.py"

FIXTURES = {
    "geo/coord.int.quest": """
interface Coord
export
    Def Pair = Tuple x: Int y: Int end
    P::TYPE
    make(x: Int y: Int): P
    pair(p: P): Pair
end;
""",
    "geo/coord.mod.quest": """
module coord : Coord
export
    Let Pair = Tuple x: Int y: Int end;
    Let P = Pair;
    let make(x: Int y: Int): P = tuple let x = x let y = y end;
    let pair(p: P): Pair = p;
end;
""",
    "geo/region.int.quest": """
interface Region
import
    geo/coord : geo/Coord
export
    R::TYPE
    around(p: coord.P): R
    corner(r: R): coord.Pair
end;
""",
    "geo/region.mod.quest": """
module region : Region
import
    geo/coord : geo/Coord
export
    Let R = coord.P;
    let around(p: coord.P): R = p;
    let corner(r: R): coord.Pair = coord.pair(r);
end;
""",
    "counter.int.quest": """
interface Counter
export
    T::TYPE
    new(): T
    get(c: T): Int
end;
""",
    "ca.mod.quest": """
module ca : Counter
export
    Let T = Int;
    let new(): T = 1;
    let get(c: T): Int = c;
end;
""",
    "cb.mod.quest": """
module cb : Counter
export
    Let T = Int;
    let new(): T = 2;
    let get(c: T): Int = c;
end;
""",
    "cnt/counter.int.quest": """
interface Counter
export
    T::TYPE
    new(): T
    get(c: T): Int
end;
""",
    "cnt/ha.mod.quest": """
module ha : cnt/Counter
export
    Let T = Int;
    let new(): T = 1;
    let get(c: T): Int = c;
end;
""",
    "cnt/hb.mod.quest": """
module hb : cnt/Counter
export
    Let T = Int;
    let new(): T = 2;
    let get(c: T): Int = c;
end;
""",
    "mix_hierarchical_counters.quest": """
import
    cnt/ha : cnt/Counter
    cnt/hb : cnt/Counter
;
let x = ha.get(hb.new());
""",
    "uses_geo.quest": """
import
    geo/coord : geo/Coord
    geo/region : geo/Region
    list : List
;
let p = coord.make(1 2);
let r = region.around(p);
let c = region.corner(r);
let l = list.cons(c.x list.nil(:Int));
""",
    "mix_counters.quest": """
import ca, cb : Counter
let x = ca.get(cb.new());
""",
    "same_counter.quest": """
import ca, cb : Counter
let x = ca.get(ca.new()) + cb.get(cb.new());
""",
}


class TestSeparateCompilationTypes(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for rel, text in FIXTURES.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text.lstrip(), encoding="utf-8")
        self.build_dir = self.root / "build"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _driver(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT_DIR / "bootstrap" / "python")
        return subprocess.run(
            [sys.executable, str(DRIVER), "-I", str(self.root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=self.root,
        )

    def _typecheck_dumps(self, program: str) -> tuple[str, str]:
        """Returns the typecheck dump from source interfaces and from compiled .qi files."""
        src = self._driver("--stop-after", "typecheck", str(self.root / program))
        self.assertEqual(src.returncode, 0, src.stderr)
        sep = self._driver(
            "--stop-after", "codegen_c", "--dump-after", "typecheck",
            "--build-dir", str(self.build_dir), str(self.root / program),
        )
        self.assertEqual(sep.returncode, 0, sep.stderr)
        # The C source follows the typecheck dump; compare only the dump.
        return src.stdout, sep.stdout[: len(src.stdout)]

    def test_typecheck_dump_agrees_with_source(self) -> None:
        from_source, from_qi = self._typecheck_dumps("uses_geo.quest")
        self.assertTrue(any(qi.suffix == ".qi" for qi in self.build_dir.rglob("*.qi")))
        self.assertEqual(from_qi, from_source)

    def test_typecheck_dump_agrees_with_source_when_qi_is_reused(self) -> None:
        self._typecheck_dumps("uses_geo.quest")
        from_source, from_qi = self._typecheck_dumps("uses_geo.quest")
        self.assertEqual(from_qi, from_source)

    def test_abstract_types_of_distinct_modules_are_distinct(self) -> None:
        cases = (
            ("mix_counters.quest", "'cb.T' is not a subtype of expected type 'ca.T'"),
            ("mix_hierarchical_counters.quest", "'hb.T' is not a subtype of expected type 'ha.T'"),
        )
        modes = (
            ("--stop-after", "typecheck"),
            ("--stop-after", "interpret"),
            ("--stop-after", "codegen_c", "--build-dir", str(self.build_dir)),
        )
        for program, message in cases:
            for args in modes:
                with self.subTest(program=program, mode=args[1]):
                    proc = self._driver(*args, str(self.root / program))
                    self.assertNotEqual(proc.returncode, 0, proc.stdout)
                    self.assertIn(message, proc.stderr)

    def test_abstract_types_of_one_module_agree(self) -> None:
        proc = self._driver(
            "--stop-after", "run_c_compiled", "--build-dir", str(self.build_dir),
            str(self.root / "same_counter.quest"),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("let x:Int = 3", proc.stdout)


if __name__ == "__main__":
    unittest.main()
