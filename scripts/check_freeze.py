#!/usr/bin/env python3
"""Every notebook must have COMMITTED frozen output.

    make check-freeze

publish.yml renders from _freeze/ and installs no R and no Jupyter kernel. A
notebook without frozen output therefore has to execute in CI, where it cannot,
and the build dies somewhere inside a lesson render with a message about a
missing engine rather than about a missing freeze.

This is not hypothetical. C-01 was pushed with its freeze generated locally but
UNTRACKED, and publish run #7 failed exactly that way. The guard that was
supposed to prevent it only checked that _freeze/ was non-empty, which it was --
full of every other lesson's output.

Two distinct failures, and the second is the one that bit:

  missing    no frozen output at all -> render, then add
  untracked  frozen output exists on this machine but is not in git, so it does
             not exist for anyone else -> `git add _freeze`

This target runs AFTER render in `make all`, never before. It was briefly wired
into `make check`, which runs before render -- so it failed on every new lesson
while advising `make all`, the command it was blocking. Do not move it back.

Being untracked is the more dangerous of the two, because everything works
locally and the repository looks clean.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def tracked():
    try:
        out = subprocess.run(["git", "ls-files", "_freeze"], cwd=ROOT,
                             capture_output=True, text=True, timeout=30)
        return {line.strip() for line in out.stdout.splitlines() if line.strip()}
    except Exception:                                    # noqa: BLE001
        return None            # no git available: fall back to existence only


def main():
    notebooks = sorted(ROOT.glob("lessons/*/notebook-*.qmd"))
    if not notebooks:
        print("  no notebooks found — nothing to check")
        return 0

    git_files = tracked()
    missing, untracked = [], []

    for nb in notebooks:
        rel = nb.relative_to(ROOT)
        result = (Path("_freeze") / rel.parent / nb.stem
                  / "execute-results" / "html.json")
        if not (ROOT / result).exists():
            missing.append(rel)
        elif git_files is not None and str(result) not in git_files:
            untracked.append(rel)

    print(f"  notebooks           : {len(notebooks)}")
    print(f"  frozen and committed: {len(notebooks) - len(missing) - len(untracked)}")
    if git_files is None:
        print("  (git unavailable — checked existence only, not tracking)")

    if not missing and not untracked:
        return 0

    print("\nFAIL  notebook output is not available to CI:\n")
    if missing:
        print("  NO FROZEN OUTPUT — these have never been executed here:")
        for m in missing:
            print(f"    - {m}")
        print("\n    Fix:  quarto render      (or `make render`)")
        print("          then: git add _freeze\n")
    if untracked:
        print("  NOT COMMITTED — frozen locally, invisible to everyone else:")
        for u in untracked:
            print(f"    - {u}")
        print("\n    Fix:  git add _freeze && git commit -m 'Refresh notebook freeze'\n")
    print("  publish.yml installs no R and no Jupyter kernel: it renders from")
    print("  the freeze. A notebook missing from it cannot be built there.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
