"""Roll the in-body image alt text between its pre- and post-optimizer wording.

The alt named the documents but not the artifact the reader had just worked
through, and opened on a vague "including". Naming the prequalification pack ties
the image to the table above it for screen-reader users and image search. Alt
text is not plan-pinned metadata and is excluded from claim detection, so it is
the safe surface for this pass.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
BEFORE = (
    "![Subcontractor prequalification documents including Form W-9, certificate of "
    "insurance, workers compensation certificate and state trade license]"
)
AFTER = (
    "![Documents from the subcontractor prequalification pack: Form W-9, certificate "
    "of insurance, workers compensation certificate and state trade license]"
)


def main() -> int:
    mode = sys.argv[1]
    old, new = (AFTER, BEFORE) if mode == "revert" else (BEFORE, AFTER)
    text = ARTICLE.read_text(encoding="utf-8")
    if old not in text:
        print(f"pack image alt already in the {mode} target state")
        return 0
    ARTICLE.write_text(text.replace(old, new, 1), encoding="utf-8", newline="")
    print(f"pack image alt {mode}ed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
