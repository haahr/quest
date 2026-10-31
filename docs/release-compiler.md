# Releases of the Self-Hosted Compiler

A *released* self-hosted compiler, a binary kept beside the repository and shared by all its worktrees (§1), builds
each new self-hosted compiler from the working tree. The bootstrap is the fallback: it made the first release, and it
can still build the tree's compiler from nothing (§4).

Building from a release is fast. The self-hosted compiler builds `questlang/driver/main` from nothing in under a
minute, compiling modules in parallel ([build-process.md](build-process.md) §7.4), against the bootstrap's ten, so a
seeded build's two stages take about two minutes. Incremental builds (`./quest` rebuilds only stale units) take
seconds.

---

## 1. The Release

```
.git/quest-release/       in the repository's common git directory, which every worktree shares
├── COMMIT/               a release, named by the commit it was cut from
│   ├── quest             the compiler binary (stage 2 of the commit)
│   ├── home/             a snapshot of the commit's lib/ and runtime/, which quest compiles against
│   └── release.json      what it is: commit, ABI, producer, sha256 of quest, date, seed, how it was checked
├── current -> COMMIT     the release in use
├── previous -> COMMIT    the release before it, kept so that a bad release can be rolled back
└── lock                  held while current or previous changes
```

- **One set of releases serves every worktree.** A release is cut from a commit on main, which they all share, so
  each worktree finds it in the common git directory (`git rev-parse --git-common-dir`), and a release cut in one
  is the seed in all. `QUEST_RELEASE_DIR` names another directory; outside a git checkout, the releases are in the
  checkout's `release/`. `bootstrap/python/quest/testing/releases.py` finds them for the runner and `tools/release`,
  and `./quest` the same way.
- **A user of a release resolves `current` once,** to the release's own directory, and uses that directory's
  `quest` and `home/` throughout, so that a cut or rollback in another worktree while it runs cannot give it one
  release's compiler and another's `home/`.
- **A release is a commit's stage 2.** It is cut only from a clean tree at a commit on main. `release.json` records
  the commit, so the release can be rebuilt from its sources: from the release before it, or from the bootstrap while
  it lasts.
- **The release carries its own `lib/` and `runtime/`** (`home/`, run as its `QUEST_HOME`). The binary was compiled
  against them, and the C it generates is for their ABI. So the working tree's runtime can change, ABI version
  included, without breaking the seed. Copying the snapshot is cheap: both are small.
- **Cutting a release** (`tools/release`):
  1. Check that the tree is clean and HEAD is on `origin/main`, and that the current release is sound, as `--verify`
     checks it.
  2. Run the self-hosting check and the self-hosted suite with stage 2 (`run_tests.py --self-hosting --seed release`,
     §3), building in `.build/release-check` (`--check-dir`). The current release builds stage 1, so each release is
     built from the one before it. The check still builds the driver with the bootstrap too, to compare artifacts.
     `--seed bootstrap` seeds the check from the bootstrap instead, for the first release, or when the current release
     cannot compile the commit (§2).
  3. If both pass, write the new release into a directory of its own beside the releases (`new-COMMIT-PID`): stage 2
     as `quest`, `git archive` of the commit's `lib/` and `runtime/` as `home/`, and `release.json`, which records
     the seed: `release COMMIT` or `bootstrap`.
  4. Check it as `--verify` does: its digest, and a small program it builds against its own `home/` and runs.
  5. With the lock held, rename it to `COMMIT`, point `previous` at the old current release and `current` at the new
     one, and remove the releases neither names. Each link is replaced by renaming a new one over it, which is
     atomic, so an interrupted release never leaves `current` naming a half-written release.

  `tools/release --verify` checks the current release, `--rollback` swaps `previous` and `current` (with the lock
  held), and `--show` describes both. A release removed while a build in another worktree still uses it can only be
  one two cuts old.
- **When to cut one:** by hand, when the working tree needs something the current release cannot compile (§2), and
  otherwise when convenient, for example after a larger piece of work. A release is never cut automatically by a push.

## 2. Building With It

The seed (the release) builds the compiler in two stages, as rustc's stage 0 does:

1. **Stage 1:** the release compiles the working tree's `questlang/driver/main` against its own `home/` (its `lib/`
   and `runtime/`).
2. **Stage 2:** stage 1 compiles the same sources against the working tree's `lib/` and `runtime/`.

Stage 2 is the new compiler. Each stage has its own build directory, and the engine makes each build incremental.

- **`./quest`** checks that the release exists and that its `quest` has the sha256 its `release.json` records.
  Then it brings stages 1 and 2 up to date (when anything under `questlang/`, `lib/`, or `runtime/` is newer than
  stage 2) and runs stage 2. With no release, it says how to make one and falls back to the bootstrap seed
  (`QUEST_SEED=bootstrap` forces that, and also watches `bootstrap/`). It records the seed that built its stages
  (`.build/quest-stages/seed`: the release's commit and the digest of its `quest`) and starts over when the seed
  changes, as when a release is cut in another worktree. A release's `home/` carries its commit's times, so artifacts
  built against one release could look fresh against the next one's older sources.
- **`QUEST_BACKEND=ssac` or `arm64`** has stage 1 compile stage 2 through that backend, its stages kept apart in
  `.build/quest-stages-BACKEND` ([arm64.md](arm64.md) step 12). Stage 1 is the seed's, compiled by C, either way.
- **The release finds the tree's `questlang/` through `-I`,** because its `QUEST_HOME` is its own `home/`, which
  holds only `lib/` and `runtime/`.
- **Both stages build in parallel,** with `-j` set to the number of CPUs (`QUEST_JOBS` for `./quest`).
- **The runner's `--self-hosted`** builds the driver it tests from the bootstrap by default, and from the release
  with `--seed release`. The runner builds from nothing every time, and building with the bootstrap keeps it able to
  build the tree's compiler between releases. `tools/check` seeds the self-hosting check from the release.
- **The one rule this imposes:** `questlang/` must be compilable by the current release against the release's own
  `lib/`. Using a new language feature, a new `lib/` function, or a new runtime primitive in `questlang/` takes two
  commits: one that adds the feature, then a release, then one that uses it. While the bootstrap is maintained, it
  can be used instead to build past such a gap (`QUEST_SEED=bootstrap`), as long as the feature is in the bootstrap
  too.
- **A new library** in `lib/` that `questlang/` will use lands that way: a commit adding the interface and module,
  their natives in `runtime/` (with an ABI bump if there are any), both interpreters' builtins, goldens, a section in
  [new-libraries.md](new-libraries.md), and a snapshot of the interface in the ABI corpus's inputs; then a release;
  then a commit moving `questlang/`'s callers over. The self-hosted interpreter's builtins are the one use inside
  `questlang/` that cannot wait for the release, so until it is cut, `./quest` needs `QUEST_SEED=bootstrap`.

## 3. Checking

- **The self-hosting check** (`run_tests.py --self-hosting`, with `--seed release` to start from the release) starts
  from the seed:
  1. The seed builds stage 1, stage 1 builds stage 2, and stage 2 builds stage 3. With the release as the seed, the
     bootstrap's build of the driver runs alongside stage 1, and builds a stage 2 of its own.
  2. The artifacts stage 2 writes must equal those stage 1 wrote (the fixed point). With the release as the seed, the
     bootstrap's stage 1 must write the release's stage 1's artifacts: the bootstrap still builds the same compiler.
  3. The self-hosted suite runs with stage 2.
- **The goldens** ([testing.md](testing.md) §2.8). The goldens of what programs do are shared, and the bootstrap
  writes them; the self-hosted compiler's IR dumps are its own, written by `--update-golden`
  with the self-hosted driver. The generated C has no goldens (testing.md §2.9).

## 4. The Bootstrap's Place

The bootstrap is kept as a correct compiler rather than an identical one ([testing.md](testing.md) §2.8): it gets the
language's changes and bug fixes, not the self-hosted compiler's optimizations, and the self-hosting check confirms
that it still builds the compiler the release does. Deleting it would leave the chain of releases, each rebuildable
from its commit by the one before, as the compiler's only provenance.

Releases are not published outside the repository (as GitHub releases, for other machines or a CI).
