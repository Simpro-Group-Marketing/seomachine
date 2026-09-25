"""Roll the meta description between its pre- and post-optimizer wording.

The optimizer pass adds the "managing subcontractors" secondary keyword, which
the page already earns impressions on, to the meta description. Frontmatter is
metadata rather than body copy, so the phrase lands without turning a sentence
into an unsupported public claim.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
BEFORE = (
    'meta_description: "Prequalify, classify, contract, onboard, manage and pay '
    'subcontractors with a nine-document checklist and the current federal worker '
    'classification rules."'
)
AFTER = (
    'meta_description: "Prequalify, classify and contract subs with a nine-document '
    'checklist, the current federal classification rules and a scorecard for '
    'managing subcontractors."'
)


def main() -> int:
    mode = sys.argv[1]
    old, new = (AFTER, BEFORE) if mode == "revert" else (BEFORE, AFTER)
    text = ARTICLE.read_text(encoding="utf-8")
    if old not in text:
        print(f"meta description already in the {mode} target state")
        return 0
    ARTICLE.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
    length = len(new.split('"', 1)[1].rstrip('"'))
    print(f"meta description {mode}ed ({length} characters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
