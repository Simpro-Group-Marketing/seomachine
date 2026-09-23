"""Roll the Step 6 capsule back and forward so a stage receipt can bracket it."""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
BEFORE = (
    "Manage subcontractors on a site by measuring against the contract rather than "
    "against a feeling. Track what the sub bills against the contracted scope, how "
    "their hours land against your job budget, and how they absorb schedule changes. "
    "The aim is catching a cost problem while the job runs, well before the final "
    "invoice lands."
)
AFTER = (
    "Knowing how to manage subcontractors on a site starts with measuring against the "
    "contract rather than against a feeling. Track what the sub bills against the "
    "contracted scope, how their hours land against your job budget, and how they "
    "absorb schedule changes. Managing subcontractors well means catching a cost "
    "problem while the job runs, well before the final invoice lands."
)


def main() -> int:
    mode = sys.argv[1]
    old, new = (AFTER, BEFORE) if mode == "revert" else (BEFORE, AFTER)
    text = ARTICLE.read_text(encoding="utf-8")
    if old not in text:
        print(f"capsule already in the {mode} target state")
        return 0
    ARTICLE.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
    print(f"Step 6 capsule {mode}ed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
