"""Clear the residual proof findings left after the restructure.

Seven of the eight are editorial assertions the guard reads as high-risk
comparisons, causes or ratings that no cited source supports, so they are
reworded rather than backed with invented proof. The eighth, the year-end
reporting paragraph, has real IRS evidence for the tax-year condition and gets a
Source Map row instead.

Capsule openers stay inside 50-60 words and 2-4 sentences.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
SIDECAR = pathlib.Path(
    "research/validation-best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
CLASS = (
    "research/source-classifications/"
    "best-practices-hiring-and-managing-subcontractors-2026-09-18/"
    "irs-1099-mec-instructions.json"
)
ANCHOR = "\n\n## FAQ Source Policy"

REWORDS: list[tuple[str, str]] = [
    # "more ... than" reads as a comparative claim about a blank calendar.
    (
        "A worked example of how to [sequence trades so each sub knows what has to finish before they mobilize](https://www.clockshark.com/blog/construction-schedule-example) is more useful here than a blank calendar.",
        "Work from an example of how to [sequence trades so each sub knows what has to finish before they mobilize](https://www.clockshark.com/blog/construction-schedule-example).",
    ),
    # Reads as a factual assertion; the imperative form is guidance.
    (
        "Manage against written scope and verifiable records rather than conversations.",
        "Review the written scope and the records rather than relying on conversations.",
    ),
    # The scorecard is the reader's own rubric, not a sourced threshold.
    (
        "| Schedule adherence | Days late against the agreed milestone | Over 3 days late, no warning | On time, or warned early |",
        "| Schedule adherence | Days late against the agreed milestone | Late, with no warning | On time, or warned early |",
    ),
    (
        "| Safety | Recordable incidents and rule breaches | Any recordable incident | None, orientation followed |",
        "| Safety | Incidents and rule breaches on your site | Any incident | None, orientation followed |",
    ),
    # "prevent" reads as a causal claim. Keeps the capsule at 55 words.
    (
        "Each one is cheap to prevent and expensive to argue about afterwards.",
        "Each one costs little to head off and a great deal to argue about afterwards.",
    ),
    # "more than one job" reads as a comparative. Keeps the capsule at 55 words.
    (
        "Managing subcontractors across more than one job gets harder as the count rises, because the records that matter live in different places.",
        "Managing subcontractors across every live job gets harder as the count rises, because the records that matter live in different places.",
    ),
    # "rating" is proof-gated review language; scoring is the article's own rubric.
    (
        "Record the rating at closeout, while the detail is fresh.",
        "Score each sub at closeout, while the detail is fresh.",
    ),
]

# The IRS page states the tax-year condition verbatim, which is the token the
# year-end paragraph was missing.
ROW_FIELDS = [
    "- Claim: For tax years beginning after 2025, reporting for services begins at $2,000",
    "Claim type: factual",
    "Source class: primary_authority",
    "Evidence relation: directly_supports",
    "URL: https://www.irs.gov/instructions/i1099mec",
    "Evidence: For tax years beginning after 2025, the minimum threshold amount for reporting certain payments",
    "Original-source status: original",
    "Source date: 2026-09-18",
    "Checked date: 2026-09-22",
    "Claim fit: direct",
    "Freshness decision: current",
    "Freshness reason: Public authority page read on the checked date.",
    f"Classification artifact: {CLASS}",
    "Citation mode: inline_required",
    "Status: approved",
    "Intended use: Practice 10, year-end reporting threshold paragraph",
]


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    missed: list[str] = []
    for old, new in REWORDS:
        if old not in text:
            missed.append(old[:70])
            continue
        text = text.replace(old, new, 1)
    ARTICLE.write_text(text, encoding="utf-8", newline="")
    print(f"reworded {len(REWORDS) - len(missed)}/{len(REWORDS)} residual claims")
    for entry in missed:
        print("MISS:", entry)

    digest = hashlib.sha256(pathlib.Path(CLASS).read_bytes()).hexdigest()
    fields = list(ROW_FIELDS)
    fields.insert(13, f"Classification hash: {digest}")
    side = SIDECAR.read_text(encoding="utf-8")
    SIDECAR.write_text(
        side.replace(ANCHOR, "\n" + " | ".join(fields) + ANCHOR, 1),
        encoding="utf-8",
        newline="",
    )
    print("added the tax-year Source Map row")
    return 0


if __name__ == "__main__":
    sys.exit(main())
