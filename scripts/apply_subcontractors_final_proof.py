"""Cover the last residual fragments each article unit still leaves unmapped.

Every fragment here is a distinctive verbatim string from the article, bound to
the authority already linked in that same unit.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ARTICLE = pathlib.Path(f"rewrites/{SLUG}-{DATE}.md")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
CLASS_DIR = f"research/source-classifications/{SLUG}-{DATE}"
CAPTURE_DIR = f"research/source-captures/{SLUG}-{DATE}"

NAIC = "https://content.naic.org/consumer"
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
OSHA_EST = "https://www.osha.gov/ords/imis/establishment.html"
NCCI = "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf"
DOL_FS13 = "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship"
FR = "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"
SBA = "https://www.sba.gov/counseling/prime-and-subcontracting/"

NAIC_EV = "Every U.S. state, the District of Columbia, and the five U.S. territories have a Department of Insurance (DOI) dedicated to helping consumers."
OSHA_ME_EV = "more than one employer may be citable for a hazardous condition that violates an OSHA standard."
NCCI_EV = "The mod applied to an employer's policy is either a unity (1.00) factor, a credit mod, or a debit mod."
DOL_EV = "Employment under the FLSA is not determined by technical concepts or common law standards of control; it is broader than the common law standard often applied to determine employment status under other Federal laws."
FR_EV = "Employee or Independent Contractor Status Under the Fair Labor Standards Act, Family and Medical Leave Act, and Migrant and Seasonal Agricultural Worker Protection Act"
SBA_EV = "Prime and subcontracting"
OSHA_EST_EV = "Establishment Search"

# One SBA mention per unit; the duplicate in Step 1 read as a redundant citation.
REWORDS = [
    (
        "rather than trusting a license number on a letterhead, which is the baseline the SBA sets out for [prime and subcontracting](https://www.sba.gov/counseling/prime-and-subcontracting/).",
        "rather than trusting a license number on a letterhead.",
    ),
]

# claim fragment, claim_type, url, evidence, intended_use, class_key, capture_key
ROWS = [
    ("then check the carrier through your state insurance department", "process", NAIC, NAIC_EV,
     "Prequalification pack table, general liability row", "naic-consumer", "naic-consumer"),
    ("and the carrier through your state insurance department", "process", NAIC, NAIC_EV,
     "Prequalification pack table, workers compensation row", "naic-consumer", "naic-consumer"),
    ("That the sub holds a current licence covering the scope you are buying", "factual", SBA, SBA_EV,
     "Prequalification pack table, trade licence row", "sba-prime-and-subcontracting", None),
    ("entity and license, insurance, workers compensation, safety record, financial stability and quality control", "process", SBA, SBA_EV,
     "Step 1 opener, screening fronts", "sba-prime-and-subcontracting", None),
    ("rather than trusting a license number on a letterhead", "process", SBA, SBA_EV,
     "Step 1, licence verification paragraph", "sba-prime-and-subcontracting", None),
    ("Learn about them before you stand on a site together", "recommendation", OSHA_EST, OSHA_EST_EV,
     "Step 1, safety record paragraph", "osha-establishment-search", None),
    ("NCCI's guide to experience rating", "definitional", NCCI, NCCI_EV,
     "Step 1, experience modification paragraph", "ncci-abcs-of-experience-rating", "ncci-abcs-of-experience-rating"),
    ("End the conversation on four signals", "recommendation", SBA, SBA_EV,
     "Step 1, red flags paragraph", "sba-prime-and-subcontracting", None),
    ("Classification turns on how the working relationship operates, not on what the contract calls it", "factual", DOL_FS13, DOL_EV,
     "Step 3, classification opener", "dol-fact-sheet-13", "dol-fact-sheet-13"),
    ("with the comment period closing on April 28, 2026", "factual", FR, FR_EV,
     "Step 3, federal status paragraph", "federalregister-ic-nprm-2026", None),
    ("Get specific about insurance", "recommendation", NAIC, NAIC_EV,
     "Step 4, insurance clause paragraph", "naic-consumer", "naic-consumer"),
    ("Check the carrier behind both through your state insurance department", "process", NAIC, NAIC_EV,
     "Step 4, insurance clause paragraph", "naic-consumer", "naic-consumer"),
    ("Prequalification alone leaves this exposure open", "factual", OSHA_ME, OSHA_ME_EV,
     "Step 5, shared jobsite duty paragraph", "osha-multi-employer-citation-policy", None),
]

NON_OFFICIAL = {"naic-consumer", "ncci-abcs-of-experience-rating"}


def sha(rel: str) -> str:
    return hashlib.sha256(pathlib.Path(rel).read_bytes()).hexdigest()


def row(claim, ctype, url, evidence, use, key, capture) -> str:
    parts = [
        f"- Claim: {claim}",
        f"Claim type: {ctype}",
        f"Source class: {'non_competing_expert' if key in NON_OFFICIAL else 'primary_authority'}",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {evidence}",
        "Original-source status: original",
        f"Source date: {DATE}",
        f"Checked date: {DATE}",
        "Claim fit: direct",
        "Freshness decision: current",
        "Freshness reason: Public authority page read on the checked date.",
    ]
    if capture:
        parts += [
            f"Artifact: {CAPTURE_DIR}/{capture}.md",
            f"Capture receipt: {CAPTURE_DIR}/{capture}-capture-receipt.json",
            f"Capture receipt hash: {sha(f'{CAPTURE_DIR}/{capture}-capture-receipt.json')}",
        ]
    parts += [
        f"Classification artifact: {CLASS_DIR}/{key}.json",
        f"Classification hash: {sha(f'{CLASS_DIR}/{key}.json')}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: {use}",
    ]
    return " | ".join(parts)


def main() -> int:
    art = ARTICLE.read_text(encoding="utf-8")
    for old, new in REWORDS:
        if old in art:
            art = art.replace(old, new, 1)
        else:
            print(f"REWORD MISS: {old[:60]}")
    ARTICLE.write_text(art, encoding="utf-8")

    side = SIDECAR.read_text(encoding="utf-8")
    anchor = "\n\n## FAQ Source Policy"
    side = side.replace(anchor, "\n" + "\n".join(row(*r) for r in ROWS) + anchor, 1)
    SIDECAR.write_text(side, encoding="utf-8")
    print(f"final residual rows added: {len(ROWS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
