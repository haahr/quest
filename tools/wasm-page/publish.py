"""Publishes the REPL's page (tools/wasm-page/build) as the repository's GitHub
Pages site: the branch gh-pages, which GitHub Pages serves, as one commit with
no parent holding the built page and nothing else.

    tools/wasm-page/publish [COMMIT] [--push | --local]

COMMIT (origin/main unless given) must be on origin/main, so that the public
page is built from published source. It is checked out in a worktree of its
own, so no edit in this one reaches the page, and the page is built there with
--qi and --built-from, which names COMMIT in its about note. The site, the
page and an empty .nojekyll (so that Pages serves files as they are, rather
than through Jekyll), is committed in a repository made for it, not in this
one, so no build is kept here. --push force-pushes that commit to origin's
gh-pages: each publish replaces the branch, so the site has no history, and
earlier builds are reachable from nothing. Without --push the site is built
and committed, and left in .build/wasm-publish/ to look at first: site/ is the
site (`python3 -m http.server -d .build/wasm-publish/site` serves it), and
repo/ its commit. --local builds a COMMIT that is not on origin/main, to try
the page before its source is pushed; it is never pushed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WORK = ROOT / ".build" / "wasm-publish"
BRANCH = "gh-pages"


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.exit(f"publish: git {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
    return result.stdout.strip()


def remove_worktree(path: Path) -> None:
    """The worktree at path, if there is one, removed with what it holds"""
    if path.exists():
        git("worktree", "remove", "--force", str(path), check=False)
        shutil.rmtree(path, ignore_errors=True)
    git("worktree", "prune")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("commit", nargs="?", default="origin/main", help="the commit to build (origin/main)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--push", action="store_true", help=f"force-push the site to origin's {BRANCH}")
    group.add_argument("--local", action="store_true", help="build a commit not on origin/main, never pushed")
    options = parser.parse_args()

    git("fetch", "--quiet", "origin")
    commit = git("rev-parse", "--verify", f"{options.commit}^{{commit}}")
    published = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "origin/main"], cwd=ROOT).returncode == 0
    if not published and not options.local:
        sys.exit(f"publish: {options.commit} ({commit[:8]}) is not on origin/main; push it first")

    source, site, repo = WORK / "source", WORK / "site", WORK / "repo"
    WORK.mkdir(parents=True, exist_ok=True)
    remove_worktree(source)
    shutil.rmtree(repo, ignore_errors=True)
    git("worktree", "add", "--quiet", "--detach", str(source), commit)
    try:
        print(f"publish: building the page from {commit[:8]}, in {source.relative_to(ROOT)}", flush=True)
        # The build's own -o refuses to replace a directory it did not make
        shutil.rmtree(site, ignore_errors=True)
        built = subprocess.run([str(source / "tools" / "wasm-page" / "build"), "-o", str(site), "--qi",
                                "--built-from", commit], cwd=source)
        if built.returncode != 0:
            sys.exit("publish: the page did not build")
    finally:
        remove_worktree(source)
    (site / ".nojekyll").write_bytes(b"")

    # The site's one commit, in a repository of its own
    repo.mkdir(parents=True)
    git("init", "--quiet", "--initial-branch", BRANCH, cwd=repo)
    git("--work-tree", str(site), "add", "--all", cwd=repo)
    git("commit", "--quiet", "-m", f"The Quest REPL page, built from {commit}", cwd=repo)
    print(f"publish: committed the site as {git('rev-parse', '--short', 'HEAD', cwd=repo)} in "
          f"{repo.relative_to(ROOT)}")

    if not options.push:
        print(f"publish: not pushed; serve {site.relative_to(ROOT)} to try it, and rerun with --push to publish")
        return
    origin = git("remote", "get-url", "origin")
    git("push", "--quiet", "--force", origin, f"HEAD:refs/heads/{BRANCH}", cwd=repo)
    print(f"publish: pushed to {BRANCH}, replacing what was there")


if __name__ == "__main__":
    main()
