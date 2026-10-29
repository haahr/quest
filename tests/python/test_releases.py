"""Tests where the releases of the self-hosted compiler live, and how
tools/release changes which is current (docs/release-compiler.md section 1):
the links it points, the rollback that swaps them, and the removal of the
releases neither names, in a directory QUEST_RELEASE_DIR names."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from quest.testing import releases

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def load_release_tool(directory: Path):
    """tools/release.py, loaded with its releases in directory."""
    with mock.patch.dict(os.environ, {"QUEST_RELEASE_DIR": str(directory)}):
        spec = importlib.util.spec_from_file_location("release_tool", ROOT_DIR / "tools" / "release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


class ReleasesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = Path(tempfile.mkdtemp(prefix="quest-releases-")).resolve()
        self.addCleanup(shutil.rmtree, self.directory, True)
        self.tool = load_release_tool(self.directory)

    def release(self, commit: str) -> Path:
        """A release directory for commit, with a description show reads."""
        path = self.directory / commit
        path.mkdir()
        (path / "release.json").write_text(json.dumps({"commit": commit, "abi": 1, "producer": "test",
                                                       "date": "today"}), encoding="utf-8")
        return path

    def test_directory_named_by_the_environment(self) -> None:
        with mock.patch.dict(os.environ, {"QUEST_RELEASE_DIR": str(self.directory)}):
            self.assertEqual(releases.releases_dir(ROOT_DIR), self.directory)
            self.assertIsNone(releases.current_release(ROOT_DIR))
            self.tool.point(self.tool.CURRENT, self.release("a" * 40))
            self.assertEqual(releases.current_release(ROOT_DIR), self.directory / ("a" * 40))

    def test_directory_shared_by_worktrees(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("QUEST_RELEASE_DIR", None)
            self.assertEqual(releases.releases_dir(ROOT_DIR).name, "quest-release")

    def test_rollback_swaps_current_and_previous(self) -> None:
        old, new = self.release("a" * 40), self.release("b" * 40)
        self.tool.point(self.tool.PREVIOUS, old)
        self.tool.point(self.tool.CURRENT, new)
        with redirect_stdout(io.StringIO()):
            self.tool.rollback()
        self.assertEqual(self.tool.target(self.tool.CURRENT), old)
        self.assertEqual(self.tool.target(self.tool.PREVIOUS), new)
        # The links name the releases relatively, so the directory can move
        self.assertEqual(os.readlink(self.tool.CURRENT), "a" * 40)

    def test_removes_releases_neither_link_names(self) -> None:
        kept = [self.release("a" * 40), self.release("b" * 40)]
        stale = self.release("c" * 40)
        in_progress = self.directory / "new-cccccccc-1"
        in_progress.mkdir()
        self.tool.point(self.tool.PREVIOUS, kept[0])
        self.tool.point(self.tool.CURRENT, kept[1])
        with self.tool.locked():
            self.tool.remove_unnamed()
        self.assertTrue(all(path.is_dir() for path in kept))
        self.assertFalse(stale.exists())
        self.assertTrue(in_progress.is_dir())


if __name__ == "__main__":
    unittest.main()
