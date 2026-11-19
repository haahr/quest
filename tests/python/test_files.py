"""os/files' walk and glob against Python's (docs/files-plan.md section 5),
as tests/python/test_datetime.py checks util/datetime.

A random tree of a few hundred entries (directories, files, hidden ones, and
empty directories; no symlinks, which Python's glob follows through ** and
os/files' does not) is made in a temporary directory. tests/files/globber.quest,
compiled once with ./quest, walks it and globs a few dozen patterns in it; this
test computes the same with os.listdir (walk's pre-order, by sorted names) and
glob.glob(recursive=True), and compares them.
"""

import glob
import os
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
GLOBBER = ROOT_DIR / "tests" / "files" / "globber.quest"
NAMES = ["a", "b", "ab", "abc", "x1", "x2", "y.q", "z.qt", "m.txt", "n.q", ".h", ".hq.q", "d", "e-f", "[a]"]


def make_tree(root: Path, rng: random.Random) -> None:
    """A tree four levels deep, each directory holding some of NAMES"""
    def fill(directory: Path, depth: int) -> None:
        for name in rng.sample(NAMES, rng.randrange(3, 8)):
            path = directory / name
            if depth < 4 and rng.random() < 0.4:
                path.mkdir()
                fill(path, depth + 1)
            else:
                path.write_text(name)
    fill(root, 0)


def walked(root: Path) -> list:
    """The lines globber.quest writes for walk: pre-order, names sorted"""
    lines = []

    def visit(path: Path, depth: int) -> None:
        kind = "directory" if path.is_dir() else "file"
        rel = "." if path == root else str(path.relative_to(root))
        lines.append(f"walk {depth} {kind} {rel}")
        if path.is_dir():
            for name in sorted(os.listdir(path)):
                visit(path / name, depth + 1)
    visit(root, 0)
    return lines


PATTERNS = ["*", "*/*", "**", "**/*", "**/", "*/", "**/*.q", "**/x*", "?", "??", "[a-m]*", "[!a-m]*", "*.[qt]*",
            ".*", "**/.*", "*/.*", "a/**", "d/**/*.q", "**/d/*", "**/ab*/**", "x?", "[ax]*/*", "e-f/*", "[[]a]",
            "*.q/", "nothing", "a/b", "*/*/*/*", "**/**/*.q", "[!.]*", "[a-]*", "\\*"]


def globbed(root: Path, pattern: str) -> list:
    """glob.glob's results for pattern in root, sorted, as globIn writes them:
    a directory's trailing / only for a pattern ending in one, and never
    the root itself"""
    found = glob.glob(pattern, root_dir=root, recursive=True)
    if not pattern.endswith("/"):
        found = [f.rstrip("/") for f in found]
    return ["= " + f for f in sorted(set(found)) if f not in ("", "/")]


class FilesTest(unittest.TestCase):

    def test_against_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp) / "globber"
            built = subprocess.run([str(ROOT_DIR / "quest"), "--build-dir", str(Path(tmp) / "build"), "-o",
                                    str(harness), str(GLOBBER)], capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            for seed in range(3):
                tree = Path(tmp) / f"tree{seed}"
                tree.mkdir()
                make_tree(tree, random.Random(1989 + seed))
                patterns = Path(tmp) / "patterns.txt"
                patterns.write_text("".join(p + "\n" for p in PATTERNS))
                done = subprocess.run([str(harness), str(tree), str(patterns)], capture_output=True, text=True,
                                      timeout=120)
                self.assertEqual(done.returncode, 0, done.stderr)
                want = walked(tree)
                for p in PATTERNS:
                    want.append("glob " + p)
                    want.extend(globbed(tree, p))
                have = done.stdout.split("\n")[:-1]
                self.assertEqual(have, want)


if __name__ == "__main__":
    unittest.main()
