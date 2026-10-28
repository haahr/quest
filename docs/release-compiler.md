# A Released Compiler as the Seed

This plan replaces the bootstrap as the compiler that builds new self-hosted compilers. Once Milestone 5 ends
([milestone-5.md](milestone-5.md)), the self-hosted compiler compiles itself to a fixed point. From then on, a
*released* self-hosted compiler, a binary kept in `release/` (ignored by git), builds each new compiler from the
working tree. The bootstrap becomes a fallback for making the first release, and later for nothing. It is also the
step that lets `questlang/` and the bootstrap diverge, as the Milestone 5 decisions anticipate.

The plan expected builds to get faster too, and they have. The self-hosted compiler builds `questlang/driver/main`
from nothing in about a minute, against the bootstrap's 10, so a seeded build's two stages take about two minutes
(with a release cut after the speedups of 2026-10-27; an older release takes 8 minutes for stage 1). The release also
pays off in incremental builds (`./questc` rebuilds only stale units) and in freedom from the bootstrap. Parallel
builds ([tasklist.md](tasklist.md)) would make full builds faster still.

The decisions (2026-10-26): a release seeds in two stages, against its own `lib/` and `runtime/` (§2); releases are
cut by hand; one previous release is kept; and the plan is carried out after Milestone 5.

---

## 1. The Release

```
release/                  (in .gitignore)
├── current/              the release in use
│   ├── questc            the compiler binary (stage 2 of the commit it was built from)
│   ├── home/             a snapshot of that commit's lib/ and runtime/, which questc compiles against
│   └── release.json      what it is: commit, ABI version, producer, sha256 of questc, date, how it was checked
└── previous/             the release before it, kept so that a bad release can be rolled back
```

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
  3. If both pass, write the new release into `release/new/`: stage 2 as `questc`, `git archive` of the commit's
     `lib/` and `runtime/` as `home/`, and `release.json`, which records the seed: `release COMMIT` or `bootstrap`.
     The releases before 2026-10-28 were all seeded by the bootstrap and record no seed.
  4. Check it as `--verify` does: its digest, and a small program it builds against its own `home/` and runs.
  5. Rename `current` to `previous` and `new` to `current`. The renames are atomic, so an interrupted release never
     leaves a half-written `current`.

  `tools/release --verify` checks the current release, `--rollback` swaps `previous` and `current`, and `--show`
  describes both. A release lives in the checkout that cut it, so each checkout or worktree has its own.
- **When to cut one:** by hand, when the working tree needs something the current release cannot compile (§2), and
  otherwise when convenient, for example at the end of each milestone. A release is never cut automatically by a push.

## 2. Building With It

The seed (the release) builds the compiler in two stages, as rustc's stage 0 does:

1. **Stage 1:** the release compiles the working tree's `questlang/driver/main` against its own `home/` (its `lib/`
   and `runtime/`).
2. **Stage 2:** stage 1 compiles the same sources against the working tree's `lib/` and `runtime/`.

Stage 2 is the new compiler. Each stage has its own build directory, and the engine makes each build incremental.

- **`./questc`** checks that the release exists and that its `questc` has the sha256 its `release.json` records.
  Then it brings stages 1 and 2 up to date (when anything under `questlang/`, `lib/`, or `runtime/` is newer than
  stage 2) and runs stage 2. With no release, it says how to make one and falls back to the bootstrap seed
  (`QUESTC_SEED=bootstrap` forces that, and also watches `bootstrap/`). It records the seed that built its stages
  (`.build/questc/seed`) and starts over when the seed changes. A release's `home/` carries its commit's times, so
  artifacts built against one release could look fresh against the next one's older sources.
- **The release finds the tree's `questlang/` through `-I`,** because its `QUEST_HOME` is its own `home/`, which
  holds only `lib/` and `runtime/`.
- **The runner's `--self-hosted`** builds the driver it tests from the bootstrap by default, and from the release
  with `--seed release`. The plan had the release as the default. But the runner builds from nothing every time, where
  the bootstrap's single build is quicker than the release's two, and the goldens are the bootstrap's anyway while it
  is kept in step.
- **The one rule this imposes:** `questlang/` must be compilable by the current release against the release's own
  `lib/`. Using a new language feature, a new `lib/` function, or a new runtime primitive in `questlang/` takes two
  commits: one that adds the feature, then a release, then one that uses it. While the bootstrap is maintained, it
  can be used instead to build past such a gap (`QUESTC_SEED=bootstrap`).

## 3. Checking

- **The self-hosting check** (`run_tests.py --self-hosting`, with `--seed release` to start from the release) starts
  from the seed:
  1. The seed builds stage 1, stage 1 builds stage 2, and stage 2 builds stage 3. With the release as the seed, the
     bootstrap's build of the driver runs alongside stage 1, for the comparison in the next step.
  2. Stage 3's artifacts must equal stage 2's (the fixed point). Stage 2's must equal the bootstrap's only while the
     two compilers are kept in step.
  3. The self-hosted suite runs with stage 2.
- **The goldens.** While the bootstrap is kept in step, the goldens stay the bootstrap's, and the `codegen_c` digests
  are the bootstrap's C. Once the compilers diverge (a separate decision, §5), the goldens and digests become stage
  2's, written by `--update-golden` with the self-hosted driver.

## 4. Steps

1. **`release/` and `tools/release` (done):** cutting, verifying, and rolling back (`tools/release --rollback` swaps
   `previous` and `current`); `.gitignore` gains `/release/`. The first release was c21ae1aa.
2. **Seeding from a release (done):** `./questc` and the runner's `--self-hosted` build stages 1 and 2 from the
   release (`--seed`, `QUESTC_SEED`); `--self-hosting` starts from the seed.
3. **Documentation (done):** build-process.md, testing.md, and compiler-organization.md describe the release, the
   stages, and the rule of §2. instructions.md says when to cut a release.

## 5. Not in This Plan

- **Retiring the bootstrap** (deleting it, or no longer keeping it in step) and making the goldens the self-hosted
  compiler's. Once the bootstrap is not kept in step, the release is the only seed, and the chain of releases, each
  rebuildable from its commit by the one before, is the compiler's provenance.
- **Publishing releases** outside the checkout (GitHub releases, or a shared directory), for other machines or a CI.
