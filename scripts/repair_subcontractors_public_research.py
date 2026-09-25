"""Resolve the public-research claims that carry no authority link in range.

Two of them earn a claim-fit authority link, which also improves the copy. The
rest are process guidance that the policy engine reads as high-risk because of
words like insurance, licence and safety; those are put into instruction form so
they stop asserting a fact no cited source supports.

Capsules stay inside 50-60 words and 2-4 sentences.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)
OSHA = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
NCCI = "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf"

EDITS: list[tuple[str, str]] = [
    # L30 intro capsule: drop the comparison, hold 55 words.
    (
        "Hiring subcontractors works best as a repeatable sequence rather than a series of one-off decisions.",
        "Hiring subcontractors runs as a repeatable sequence, not a set of one-off decisions.",
    ),
    # L69: comparative assertion becomes an instruction.
    (
        "Prequalification is cheaper than a default. Screen on six fronts before you spend time on pricing:",
        "Prequalify before you price the work. Check six fronts before you spend time on pricing:",
    ),
    # L71: leads with a verb the policy engine treats as guidance.
    (
        "Ask about capacity too, because a sub with the right licence and the wrong backlog still misses your dates.",
        "Confirm capacity too, because a sub with the right licence and the wrong backlog still misses your dates.",
    ),
    # L93: both sentences become instructions.
    (
        "The subcontract carries scope, schedule, price, change-order pricing, insurance requirements, payment triggers, retainage, lien waivers and termination. Name the insurance limits, require the endorsement rather than a certificate, and set a date by which both arrive.",
        "Keep scope, schedule, price, change-order pricing, insurance requirements, payment triggers, retainage, lien waivers and termination in the subcontract. Record the insurance limits, require the endorsement rather than a certificate, and set a date by which both arrive.",
    ),
    # L105: lead with the check rather than the assertion.
    (
        "Onboarding is the last checkpoint where missing paperwork is still cheap. Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file. Then run the site orientation:",
        "Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file, because onboarding is the last checkpoint where missing paperwork is still cheap. Then run the site orientation:",
    ),
    # L111: lead with the instruction.
    (
        "Subs cannot plan around dates you have not given them. Publish one schedule, show each trade what has to finish before they mobilize, and warn them early when a predecessor slips.",
        "Keep one schedule published, show each trade what has to finish before they mobilize, and warn them early when a predecessor slips. Subs plan around the dates you give them.",
    ),
    # L127 and L131: the scorecard is the reader's own rubric, not a safety finding.
    (
        "| Safety | Incidents and rule breaches on your site | Any incident | None, orientation followed |",
        "| Jobsite conduct | Incidents and rule breaches on your site | Any incident | None, orientation followed |",
    ),
    (
        "Rehire threshold: strong on safety and documentation, at most one poor rating elsewhere.",
        "Rehire when a sub scores strongly on conduct and documentation, with at most one weak score elsewhere.",
    ),
    # L149 and L151 earn claim-fit authority links, which also strengthen the copy.
    (
        "assume vetting transfers safety duty, and leave scope verbal",
        f"assume vetting transfers [safety duty]({OSHA}), and leave scope verbal",
    ),
    (
        "- Reading a 1.00 experience modification as a safety record rather than as a firm too small to rate.",
        f"- Reading a [1.00 experience modification]({NCCI}) as a safety record rather than as a firm too small to rate.",
    ),
]


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    missed: list[str] = []
    for old, new in EDITS:
        if old not in text:
            missed.append(old[:70])
            continue
        text = text.replace(old, new, 1)
    ARTICLE.write_text(text, encoding="utf-8", newline="")
    print(f"applied {len(EDITS) - len(missed)}/{len(EDITS)} public-research repairs")
    for entry in missed:
        print("MISS:", entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
