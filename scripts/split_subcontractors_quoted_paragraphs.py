"""Split the two quote-heavy paragraphs so each cited fact stands on its own.

A sentence that ends inside a quotation mark runs on into the next one, which
left several distinct facts sharing a single proof unit. Splitting them also
reads better at phone width.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
FR = (
    "https://www.federalregister.gov/documents/2026/02/27/2026-03962/"
    "employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"
)

REPLACEMENTS = [
    (
        f"**Paused enforcement is not reduced exposure.** Contractors get this part wrong. The [same rulemaking document]({FR}) records that the Wage and Hour Division \"will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.\" It also records that \"the 2024 Rule remains in effect for purposes of private litigation.\" An investigator and a plaintiff's attorney apply different tests. For most contractors the lawsuit is the larger risk.",
        f"**Paused enforcement is not reduced exposure.** Contractors get this part wrong.\n\nThe [same rulemaking document]({FR}) records that the Wage and Hour Division \"will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.\"\n\nIt also records that \"the 2024 Rule remains in effect for purposes of private litigation.\" An investigator and a plaintiff's attorney apply different tests. For most contractors the lawsuit is the larger risk.",
    ),
    (
        "\"at least $2,000 in: Services performed by someone who is not your employee.\" Gather the W-9 up front so the year-end filing stays clerical, and check [the ways you pay an independent contractor](https://www.clockshark.com/blog/ways-to-hire-and-pay-contractors) before you set the arrangement up.",
        "\"at least $2,000 in: Services performed by someone who is not your employee.\"\n\nGather the [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) carrying the sub's taxpayer identification number up front so the year-end filing stays clerical, and check [the ways you pay an independent contractor](https://www.clockshark.com/blog/ways-to-hire-and-pay-contractors) before you set the arrangement up.",
    ),
]


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    applied = 0
    for old, new in REPLACEMENTS:
        if old not in text:
            print(f"MISS: {old[:80]}")
            continue
        text = text.replace(old, new, 1)
        applied += 1
    ARTICLE.write_text(text, encoding="utf-8", newline="")
    print(f"split {applied}/{len(REPLACEMENTS)} paragraphs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
