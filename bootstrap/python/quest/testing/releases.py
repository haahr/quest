"""Where the releases of the self-hosted compiler live (docs/release-compiler.md
section 1): in the repository's common git directory, which every worktree of
the repository shares, so that one release seeds them all.

    <git common dir>/quest-release/
        COMMIT/               a release: questc, home/, and release.json
        current -> COMMIT     the release that seeds builds
        previous -> COMMIT    the one before it, which --rollback restores
        lock                  held while current or previous changes

QUEST_RELEASE_DIR names another directory. Outside a git checkout, the
releases are in the checkout's release/. A user of a release resolves current
once (current_release), so that a cut or rollback while it runs cannot give
it one release's compiler and another's home/.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def releases_dir(root: Path) -> Path:
    """The directory holding the releases, for the checkout at root."""
    named = os.environ.get("QUEST_RELEASE_DIR")
    if named:
        return Path(named).resolve()
    process = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True)
    if process.returncode != 0 or not process.stdout.strip():
        return root / "release"
    return Path(process.stdout.strip()) / "quest-release"


def current_release(root: Path) -> Path | None:
    """The current release's directory, with its symbolic link resolved, if
    there is one."""
    current = releases_dir(root) / "current"
    return current.resolve() if current.is_dir() else None
