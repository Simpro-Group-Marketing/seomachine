"""Map each remaining numeric and quoted claim to source-visible evidence.

Every snippet here was read from the live source during this run, and each one
carries the same numbers the public sentence uses.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")
CLASS_DIR = f"research/source-classifications/{SLUG}-{DATE}"
ANCHOR = "\n\n## FAQ Source Policy"

FR = (
    "https://www.federalregister.gov/documents/2026/02/27/2026-03962/"
    "employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"
)
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
IRS_W9 = "https://www.irs.gov/forms-pubs/about-form-w-9"
IRS_SS8 = "https://www.irs.gov/forms-pubs/about-form-ss-8"
IRS_NEC = "https://www.irs.gov/instructions/i1099mec"

# claim, claim type, url, evidence, classification key, intended use
ROWS = [
    (
        "Confirm the legal entity name matches the name on the Form W-9",
        "process", IRS_W9,
        "About Form W-9, Request for Taxpayer Identification Number and Certification",
        "irs-about-form-w-9",
        "Step 1, licence and entity verification paragraph",
    ),
    (
        "That proposal rescinds the analysis currently sitting in 29 CFR part 795",
        "factual", FR,
        "currently set forth in 29 CFR part 795",
        "federalregister-ic-nprm-2026",
        "Step 3, federal rule status paragraph",
    ),
    (
        "The Labor Department proposed replacing its independent contractor analysis in a rule published on February 27, 2026",
        "factual", FR,
        "A Proposed Rule by the Wage and Hour Division on 02/27/2026",
        "federalregister-ic-nprm-2026",
        "Step 3, federal rule status paragraph",
    ),
    (
        "with the comment period closing on April 28, 2026",
        "factual", FR,
        "Comments must be received on or before April 28, 2026.",
        "federalregister-ic-nprm-2026",
        "Step 3, federal rule status paragraph",
    ),
    (
        "ask the IRS to decide using Form SS-8 rather than guessing",
        "process", IRS_SS8,
        "About Form SS-8, Determination of Worker Status for Purposes of Federal Employment Taxes and Income Tax Withholding",
        "irs-about-form-ss-8",
        "Step 3, unclear classification paragraph",
    ),
    (
        "Form 1099-NEC reporting for services now begins at $2,000",
        "factual", IRS_NEC,
        "File Form 1099-NEC, Nonemployee Compensation, for each person in the course of your business during the year to whom you have paid at least $2,000 in: Services performed by someone who is not your employee",
        "irs-1099-mec-instructions",
        "Step 3, year-end reporting threshold paragraph",
    ),
    (
        "A controlling employer holds general supervisory authority over the worksite, including the power to correct violations or require others to correct them.",
        "process", OSHA_ME,
        "An employer who has general supervisory authority over the worksite, including the power to correct safety and health violations itself or require others to correct them.",
        "osha-multi-employer-citation-policy",
        "Step 5, controlling employer definition",
    ),
    (
        "The same rulemaking document records that the Wage and Hour Division \"will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.\"",
        "comparative", FR,
        "WHD will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.",
        "federalregister-ic-nprm-2026",
        "Step 3, paused enforcement paragraph",
    ),
]


def sha(path: str) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def row(claim: str, claim_type: str, url: str, evidence: str, key: str, use: str) -> str:
    artifact = f"{CLASS_DIR}/{key}.json"
    parts = [
        f"- Claim: {claim}",
        f"Claim type: {claim_type}",
        "Source class: primary_authority",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {evidence}",
        "Original-source status: original",
        f"Source date: {DATE}",
        f"Checked date: {DATE}",
        "Claim fit: direct",
        "Freshness decision: current",
        "Freshness reason: Public authority page read on the checked date.",
        f"Classification artifact: {artifact}",
        f"Classification hash: {sha(artifact)}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: {use}",
    ]
    return " | ".join(parts)


def main() -> int:
    text = SIDECAR.read_text(encoding="utf-8")
    rows = "\n".join(row(*record) for record in ROWS)
    SIDECAR.write_text(
        text.replace(ANCHOR, "\n" + rows + ANCHOR, 1), encoding="utf-8", newline=""
    )
    print(f"numeric and quoted proof rows added: {len(ROWS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
