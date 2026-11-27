"""The self-hosted driver's --report-inferable (docs/type-system.md section
6.9): the calls whose written type arguments inference finds, in a program and
the module it imports, compiled by the build engine, in each mode. It runs
./quest, which builds the compiler's stages first if they are stale."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

INTERFACE = """interface Calls
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
export
    Def Point = Tuple x: Int y: Int end
    total(v: vector.T(Int)): Int
    first(v: vector.T(Point)): Point
    nothing(): maybe.T(Int)
end
"""

MODULE = """module calls : Calls
import
    collections/vector : collections/Vector
    util/maybe : util/Maybe
export
    Let Point = Tuple x: Int y: Int end
    Let Base = Tuple x: Int end
    let total(v: vector.T(Int)): Int =
        begin
            let var sum = 0
            for i = 0 upto {vector.length(:Int v) - 1} do sum := sum + vector.get(:Int v i) end
            sum
        end
    let first(v: vector.T(Point)): Point = vector.get(:Point v 0)
    let nothing(): maybe.T(Int) = maybe.none(:Int)
    let widened(p: Point): maybe.T(Base) = maybe.some(:Base p)
    let nested(): Int = maybe.unwrap(maybe.some(:Int 3))
end
"""

PROGRAM = """import calls : Calls
import collections/vector : collections/Vector

let v = vector.new(:Int)
vector.append(:Int v 3)
calls.total(v)
"""

LINE = re.compile(r"^(.*?):(\d+):(\d+): type arguments can be inferred (from the arguments|with the expected type) "
                  r"\[(\d+) (\d+)\]$")


class TestReportInferable(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory(prefix="quest-report-inferable-")
        cls.dir = Path(cls.tmp.name)
        for name, text in (("calls.int.quest", INTERFACE), ("calls.mod.quest", MODULE), ("main.quest", PROGRAM)):
            (cls.dir / name).write_text(text)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def report(self, *flag: str, wasm: bool = False) -> dict[str, list[tuple[int, int, str, str]]]:
        """Each of the test's files' reported calls: line, column, class, and
        the text of their type arguments. The build directory is shared, so
        that a second build finds the first's artifacts fresh, as a warm build
        would; with wasm, the program is written as a WebAssembly bundle, in a
        build directory of its own."""
        build = ["--backend", "wasm", "--build-dir", str(self.dir / "wasm-build"), "-o", str(self.dir / "main.wasm")] \
            if wasm else ["compile", "--build-dir", str(self.dir / "build"), "-o", str(self.dir / "main")]
        process = subprocess.run(
            [str(ROOT_DIR / "quest"), *build, *flag, "-j", "2", "-I", str(self.dir), str(self.dir / "main.quest")],
            capture_output=True, text=True, cwd=ROOT_DIR, timeout=1800)
        self.assertEqual(process.returncode, 0, process.stderr)
        found: dict[str, list[tuple[int, int, str, str]]] = {}
        for line in process.stderr.splitlines():
            m = LINE.match(line)
            if m and Path(m.group(1)).parent == self.dir:
                name = Path(m.group(1)).name
                data = (self.dir / name).read_bytes()
                text = data[int(m.group(5)):int(m.group(6))].decode()
                found.setdefault(name, []).append((int(m.group(2)), int(m.group(3)), m.group(4), text))
        return found

    def test_equal(self) -> None:
        found = self.report("--report-inferable")
        self.assertEqual(found["main.quest"], [(5, 1, "from the arguments", ":Int ")])
        self.assertEqual(found["calls.mod.quest"], [
            (11, 29, "from the arguments", ":Int "),
            (11, 72, "from the arguments", ":Int "),
            # An alias: an equal type, though not the same node
            (14, 44, "from the arguments", ":Point "),
            (15, 35, "with the expected type", ":Int"),
        ])
        # Not reported: maybe.some(:Base p), which inference would make a
        # maybe.T(Point), and maybe.some(:Int 3), in a call whose own type
        # arguments are inferred

    def test_wasm(self) -> None:
        """The wasm backend's build engine reports its modules' calls too"""
        found = self.report("--report-inferable", wasm=True)
        self.assertEqual(found["main.quest"], [(5, 1, "from the arguments", ":Int ")])
        self.assertEqual([call[:2] for call in found.get("calls.mod.quest", [])],
                         [(11, 29), (11, 72), (14, 44), (15, 35)])

    def test_exact(self) -> None:
        found = self.report("--report-inferable=exact")
        self.assertEqual([call[:2] for call in found["calls.mod.quest"]], [(11, 29), (11, 72), (15, 35)])

    def test_without_the_flag(self) -> None:
        self.report("--report-inferable")
        self.assertEqual(self.report(), {})

    def test_a_misspelled_mode(self) -> None:
        process = subprocess.run([str(ROOT_DIR / "quest"), "--report-inferable=same", "-e", "ok"], capture_output=True,
                                 text=True, cwd=ROOT_DIR, timeout=1800)
        self.assertEqual(process.returncode, 2)
        self.assertIn("--report-inferable takes equal or exact, not 'same'", process.stderr)


if __name__ == "__main__":
    unittest.main()
