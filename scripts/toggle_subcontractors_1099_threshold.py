"""Roll the payment FAQ between its pre- and post-optimizer wording.

The $2,000 Form 1099-NEC threshold applies to tax years beginning after 2025,
and the IRS instructions already cited in this answer say so. Scoping the
sentence replaces a vague comparison against "older guides" with the condition
a reader actually needs, and the answer stays inside the 40-60 word band.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
BEFORE = (
    "Reporting for services begins at $2,000 per the [IRS instructions for Form "
    "1099-NEC](https://www.irs.gov/instructions/i1099mec), which is higher than the "
    "figure older guides quote."
)
AFTER = (
    "For tax years beginning after 2025, reporting for services begins at $2,000 per "
    "the [IRS instructions for Form 1099-NEC](https://www.irs.gov/instructions/i1099mec)."
)


def main() -> int:
    mode = sys.argv[1]
    old, new = (AFTER, BEFORE) if mode == "revert" else (BEFORE, AFTER)
    text = ARTICLE.read_text(encoding="utf-8")
    if old not in text:
        print(f"payment FAQ already in the {mode} target state")
        return 0
    ARTICLE.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
    print(f"payment FAQ {mode}ed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
