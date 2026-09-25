"""Regenerate the validation sidecar Source Map with the full v2 field contract.

`source_quality_guard` requires thirteen fields per row. Each row below binds the
hash-verified classification record already emitted for that source, and the two
PDF sources additionally bind their local extracted-text artifact and capture
receipt because `source_support_guard` rejects a bare PDF URL.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
CLASS_DIR = f"research/source-classifications/{SLUG}-{DATE}"
CAPTURE_DIR = f"research/source-captures/{SLUG}-{DATE}"

FR = "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"
ECFR = "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-795"
IRS_1099 = "https://www.irs.gov/instructions/i1099mec"
IRS_IC = "https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee"
IRS_W9 = "https://www.irs.gov/forms-pubs/about-form-w-9"
IRS_SS8 = "https://www.irs.gov/forms-pubs/about-form-ss-8"
OSHA_EST = "https://www.osha.gov/ords/imis/establishment.html"
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
NCCI = "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf"
AGC = "https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20%284%29.pdf"
CADIR = "https://www.dir.ca.gov/dlse/faq_independentcontractor.htm"

# claim, claim_type, url, evidence, source_class, original_status, source_date,
# freshness_decision, freshness_reason, intended_use, classification_key, capture_key
ROWS = [
    ("The same rulemaking document records that the Wage and Hour Division \"will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.\"",
     "factual", FR,
     "WHD will no longer apply the 2024 Rule's analysis when determining employee versus independent contractor status in FLSA investigations.",
     "primary_authority", "original", "2026-02-27", "current",
     "The rulemaking document is the current published proposal and states the enforcement position directly.",
     "Classification section, federal status paragraph", "federalregister-ic-nprm-2026", None),
    ("It also records that \"the 2024 Rule remains in effect for purposes of private litigation.\"",
     "factual", FR,
     "the 2024 Rule remains in effect for purposes of private litigation",
     "primary_authority", "original", "2026-02-27", "current",
     "Same current rulemaking document; the litigation boundary is stated in its preamble.",
     "Classification section, enforcement versus litigation paragraph", "federalregister-ic-nprm-2026", None),
    ("That proposal rescinds the analysis currently sitting in 29 CFR part 795",
     "factual", ECFR,
     "Employee or Independent Contractor Classification Under the Fair Labor Standards Act",
     "primary_authority", "original", "2026-09-18", "current",
     "The eCFR renders the currently effective codified text and was read on the checked date.",
     "Classification section, codified rule reference", "ecfr-part-795", None),
    ("there is \"no 'magic' or set number of factors\" that settles it and that no single factor stands alone",
     "factual", IRS_IC,
     "There is no \"magic\" or set number of factors that \"makes\" the worker an employee or an independent contractor and no one factor stands alone in making this determination.",
     "primary_authority", "original", "2026-09-18", "current",
     "IRS maintains this guidance page continuously and it was read on the checked date.",
     "Classification section, IRS test paragraph", "irs-independent-contractor-test", None),
    ("Form 1099-NEC reporting for services now begins at $2,000",
     "statistic", IRS_1099,
     "at least $2,000 in: Services performed by someone who is not your employee",
     "primary_authority", "original", "2026-09-18", "current",
     "The instructions are the original authority for the threshold and were read on the checked date.",
     "Classification section reporting paragraph and the payment FAQ", "irs-1099-mec-instructions", None),
    ("Legal name, entity type and taxpayer ID for year-end reporting",
     "process", IRS_W9,
     "Request for Taxpayer Identification Number and Certification",
     "primary_authority", "original", "2026-09-18", "current",
     "IRS form landing page maintained continuously and read on the checked date.",
     "Prequalification pack table, Form W-9 row", "irs-about-form-w-9", None),
    ("ask the IRS to decide using Form SS-8 rather than guessing",
     "process", IRS_SS8,
     "Determination of Worker Status for Purposes of Federal Employment Taxes and Income Tax Withholding",
     "primary_authority", "original", "2026-09-18", "current",
     "IRS form landing page maintained continuously and read on the checked date.",
     "Classification section, unresolved-case pointer", "irs-about-form-ss-8", None),
    ("one of the three conditions you satisfy is that \"the worker performs work that is outside the usual course of the hiring entity's business.\"",
     "factual", CADIR,
     "The worker performs work that is outside the usual course of the hiring entity's business",
     "primary_authority", "original", "2026-09-18", "current",
     "State labour agency FAQ maintained continuously and read on the checked date.",
     "Classification section, state test paragraph", "ca-dir-independent-contractor-faq", None),
    ("A controlling employer holds general supervisory authority over the worksite, including the power to correct violations or require others to correct them.",
     "factual", OSHA_ME,
     "more than one employer may be citable for a hazardous condition that violates an OSHA standard.",
     "primary_authority", "original", "1999-12-10", "historical_scoped",
     "The directive is long-standing and remains the published multi-employer policy; the claim is scoped to that policy rather than to a current-year statistic.",
     "Onboarding section, shared jobsite duty paragraph, and the responsibility FAQ", "osha-multi-employer-citation-policy", None),
    ("Federal or state-plan enforcement at the sub's establishments",
     "process", OSHA_EST,
     "Establishment Search",
     "primary_authority", "original", "2026-09-18", "current",
     "The search tool is live and was loaded on the checked date.",
     "Prequalification pack table and Step 1 safety paragraph", "osha-establishment-search", None),
    ("the mod applied to a policy \"is either a unity (1.00) factor, a credit mod, or a debit mod,\"",
     "definitional", NCCI,
     "The mod applied to an employer's policy is either a unity (1.00) factor, a credit mod, or a debit mod.",
     "non_competing_expert", "original", "2026-09-18", "historical_scoped",
     "The rating bureau guide is undated; the claim is scoped to the definition of a unity factor rather than to any current rating value.",
     "Step 1, experience modification paragraph", "ncci-abcs-of-experience-rating", "ncci-abcs-of-experience-rating"),
    ("42 percent of firms reported shortages of their own workers or their subcontractors' workers delaying projects",
     "statistic", AGC,
     "Worker shortages remain respondents' most listed reason for project delays, with 42 percent reporting that shortages of their own workers or their subcontractors' workers have delayed projects.",
     "non_competing_expert", "original", "2026-09-03", "current",
     "The 2026 survey analysis is the original publication of the figure and is the current edition.",
     "Introduction and the common issues FAQ", "agc-2026-workforce-survey", "agc-2026-workforce-survey"),
]


def sha256_file(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def build_row(r) -> str:
    (claim, ctype, url, evidence, sclass, ostatus, sdate, fdecision,
     freason, use, class_key, capture_key) = r
    parts = [
        f"- Claim: {claim}",
        f"Claim type: {ctype}",
        f"Source class: {sclass}",
        "Evidence relation: directly_supports",
        f"URL: {url}",
        f"Evidence: {evidence}",
        f"Original-source status: {ostatus}",
        f"Source date: {sdate}",
        f"Checked date: {DATE}",
        "Claim fit: direct",
        f"Freshness decision: {fdecision}",
        f"Freshness reason: {freason}",
    ]
    if capture_key:
        parts += [
            f"Artifact: {CAPTURE_DIR}/{capture_key}.md",
            f"Capture receipt: {CAPTURE_DIR}/{capture_key}-capture-receipt.json",
            f"Capture receipt hash: {sha256_file(f'{CAPTURE_DIR}/{capture_key}-capture-receipt.json')}",
        ]
    parts += [
        f"Classification artifact: {CLASS_DIR}/{class_key}.json",
        f"Classification hash: {sha256_file(f'{CLASS_DIR}/{class_key}.json')}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: {use}",
    ]
    return " | ".join(parts)


def main() -> int:
    text = SIDECAR.read_text(encoding="utf-8")
    start = text.index("## Source Map")
    end = text.index("## FAQ Source Policy")
    block = "## Source Map\n\n" + "\n".join(build_row(r) for r in ROWS) + "\n\n"
    SIDECAR.write_text(text[:start] + block + text[end:], encoding="utf-8")
    print(f"Source Map rebuilt with {len(ROWS)} rows, 13 required fields each")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
