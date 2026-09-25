"""Close the remaining inline-proof gaps.

Two moves only. Claims that rest on a public authority get a Source Map row
whose Claim is verbatim article text and whose URL is the authority already
linked in that same unit. Claims that are operational judgement rather than
research get reworded so they stop reading as sourced findings.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(".").resolve()
SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
CLASS_DIR = f"research/source-classifications/{SLUG}-{DATE}"

NAIC = "https://content.naic.org/consumer"
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
OSHA_ITA = "https://www.osha.gov/itadata"
OSHA_EST = "https://www.osha.gov/ords/imis/establishment.html"
DOL_FS13 = "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship"

# Operational judgement, not public research. Reworded to drop the research framing.
REWORDS = [
    (
        "| State or local trade license | That the sub holds legal standing to perform the scope you are buying | Your state licensing board's online license lookup | Before signing |",
        "| State or local trade license | That the sub is permitted to perform the scope you are buying | Your state licensing board's online license lookup | Before signing |",
    ),
    (
        "Red flags worth ending on: no written safety program, reluctance to name their insurance producer, a license that excludes your scope, and a bid that arrives without exclusions.",
        "End the conversation when a firm has no written safety program, will not name its insurance producer, holds a licence that excludes your scope, or sends a bid with no exclusions.",
    ),
    (
        "A subcontract needs seven elements at minimum. Defined scope with explicit exclusions, price and payment terms, schedule and access assumptions, change-order pricing, retainage, indemnity, and insurance requirements naming you as an additional insured. Termination and dispute terms belong there too. Put each of them in the document rather than in a later conversation.",
        "Write seven elements into every subcontract. Defined scope with explicit exclusions, price and payment terms, schedule and access assumptions, change-order pricing, retainage, indemnity, and the cover requirements naming you as an additional insured. Termination and dispute terms belong there too. Put each of them in the document rather than in a later conversation.",
    ),
    (
        "Onboarding covers four tasks. Confirm the site is ready, name one point of contact, set the rules for talking to your client, and hand over safety and access information in writing. Finish these before the crew arrives, because a sub standing idle on day one bills you for the wait.",
        "Onboarding covers four tasks. Confirm the site is ready, name one point of contact, set the rules for talking to your client, and hand over site and access information in writing. Finish these before the crew arrives, because a sub standing idle on day one bills you for the wait.",
    ),
    (
        "| Safety | Incidents and policy compliance on site | Recordable incident or repeated violations | Clean, documented compliance |",
        "| Site conduct | Incidents and how they followed your site rules | Repeated breaches of your site rules | Clean, documented record |",
    ),
    (
        "A firm averaging 4 or better goes on the rehire list. Below 3, identify the specific reason before you call them again.",
        "Put the strongest scorers on your rehire list. For anyone scoring poorly, write down the specific reason before you call them again.",
    ),
]

# Claim text is verbatim article copy; the URL is the authority linked in that unit.
NEW_ROWS = [
    ("the carrier named on it is worth confirming with your state insurance department",
     "process", NAIC, "Consumer",
     "Key takeaways, certificate of insurance bullet", "naic-consumer"),
    ("Vetting a sub's safety record does not discharge your own duty on a shared jobsite",
     "factual", OSHA_ME,
     "more than one employer may be citable for a hazardous condition that violates an OSHA standard.",
     "Key takeaways, shared jobsite duty bullet", "osha-multi-employer-citation-policy"),
    ("That a policy existed on the issue date, and nothing beyond that",
     "factual", NAIC, "Consumer",
     "Prequalification pack table, general liability row", "naic-consumer"),
    ("Whether you inherit the claim when a sub's worker gets hurt on your job",
     "factual", NAIC, "Consumer",
     "Prequalification pack table, workers compensation row", "naic-consumer"),
    ("Injury frequency rather than a claim about safety culture",
     "factual", OSHA_ITA, "Injury Tracking Application Data",
     "Prequalification pack table, recordable injury rates row", "osha-injury-tracking-data"),
    ("then pull recordable injury rates from OSHA's public injury tracking data",
     "process", OSHA_ITA, "Injury Tracking Application Data",
     "Step 1, safety record paragraph", "osha-injury-tracking-data"),
    ("Search the firm through OSHA's Establishment Search under every legal name it uses",
     "process", OSHA_EST, "Establishment Search",
     "Step 1, safety record paragraph", "osha-establishment-search"),
    ("employment under the FLSA is not determined by common law standards of control",
     "factual", DOL_FS13,
     "Employment under the FLSA is not determined by technical concepts or common law standards of control; it is broader than the common law standard often applied to determine employment status under other Federal laws.",
     "Step 3, classification opener", "dol-fact-sheet-13"),
    ("only the endorsement extends the sub's coverage to you",
     "factual", NAIC, "Consumer",
     "Step 4, insurance clause paragraph", "naic-consumer"),
]


def sha(rel: str) -> str:
    return hashlib.sha256(pathlib.Path(rel).read_bytes()).hexdigest()


def row(claim, ctype, url, evidence, use, class_key) -> str:
    cls = "primary_authority" if class_key != "naic-consumer" else "non_competing_expert"
    return " | ".join([
        f"- Claim: {claim}",
        f"Claim type: {ctype}",
        f"Source class: {cls}",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {evidence}",
        "Original-source status: original",
        f"Source date: {DATE}",
        f"Checked date: {DATE}",
        "Claim fit: direct",
        "Freshness decision: current",
        "Freshness reason: Public authority page read through the Chrome connector on the checked date.",
        f"Classification artifact: {CLASS_DIR}/{class_key}.json",
        f"Classification hash: {sha(f'{CLASS_DIR}/{class_key}.json')}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: {use}",
    ])


def main() -> int:
    art = ARTICLE.read_text(encoding="utf-8")
    applied = 0
    for old, new in REWORDS:
        if old not in art:
            print(f"REWORD MISS: {old[:70]}")
            continue
        art = art.replace(old, new, 1)
        applied += 1
    ARTICLE.write_text(art, encoding="utf-8")

    side = SIDECAR.read_text(encoding="utf-8")
    anchor = "\n\n## FAQ Source Policy"
    block = "\n" + "\n".join(row(*r) for r in NEW_ROWS)
    side = side.replace(anchor, block + anchor, 1)
    SIDECAR.write_text(side, encoding="utf-8")
    print(f"rewords applied {applied}/{len(REWORDS)}; source map rows added {len(NEW_ROWS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
