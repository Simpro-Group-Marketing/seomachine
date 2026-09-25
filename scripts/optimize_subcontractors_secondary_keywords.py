"""Restore the secondary keywords the demand data shows this page already earns.

GSC records 172 impressions on "managing subcontractors" and 880 US searches a
month for "how to manage subcontractors on a site", and both phrases were lost
when the Step 6 capsule was reworded. The replacement keeps the capsule inside
its 50-60 word band and states the same measurable guidance.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
OLD = (
    "Manage subcontractors on a site by measuring against the contract rather than "
    "against a feeling. Track what the sub bills against the contracted scope, how "
    "their hours land against your job budget, and how they absorb schedule changes. "
    "The aim is catching a cost problem while the job runs, well before the final "
    "invoice lands."
)
NEW = (
    "Knowing how to manage subcontractors on a site starts with measuring against the "
    "contract rather than against a feeling. Track what the sub bills against the "
    "contracted scope, how their hours land against your job budget, and how they "
    "absorb schedule changes. Managing subcontractors well means catching a cost "
    "problem while the job runs, well before the final invoice lands."
)


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    if OLD not in text:
        print("MISS: Step 6 capsule text not found")
        return 1
    ARTICLE.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="")
    print(f"Step 6 capsule rewritten ({len(NEW.split())} words)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
