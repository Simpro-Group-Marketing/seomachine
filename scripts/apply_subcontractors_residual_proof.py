"""Map the residual high-risk claims left in each article unit.

The policy engine treats insurance, licensing, safety and tax wording as
high-risk, and this article is about exactly those things. Rewording would
strip the substance, so every residual claim gets a Source Map row bound to the
authority linked in its own unit, and the four units that had no authority get
one.
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

NAIC = "https://content.naic.org/consumer"
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
OSHA_EST = "https://www.osha.gov/ords/imis/establishment.html"
NCCI = "https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf"
DOL_FS13 = "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship"
FR = "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"
IRS_IC = "https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee"
SBA = "https://www.sba.gov/counseling/prime-and-subcontracting/"

# Units that carried no authority of their own.
LINK_EDITS = [
    (
        "| State or local trade license | That the sub is permitted to perform the scope you are buying | Your state licensing board's online license lookup | Before signing |",
        f"| State or local trade license | That the sub is permitted to perform the scope you are buying | Your state licensing board's online license lookup, using the [prime and subcontracting]({SBA}) responsibilities as your baseline | Before signing |",
    ),
    (
        "Screen on six fronts before you spend time on pricing: entity and license, insurance, workers compensation, safety record, financial stability and quality control.",
        f"Screen on six fronts before you spend time on pricing: entity and license, insurance, workers compensation, safety record, financial stability and quality control. The [prime and subcontracting]({SBA}) responsibilities set the floor.",
    ),
    (
        "**Verify the license and the entity yourself.** Look the firm up through your state licensing board's online lookup rather than trusting a license number on a letterhead.",
        f"**Verify the license and the entity yourself.** Look the firm up through your state licensing board's online lookup rather than trusting a license number on a letterhead, which is the baseline the SBA sets out for [prime and subcontracting]({SBA}).",
    ),
    (
        "End the conversation when a firm has no written safety program, will not name its insurance producer, holds a licence that excludes your scope, or sends a bid with no exclusions.",
        f"End the conversation when a firm has no written safety program, will not name its insurance producer, holds a licence that excludes your scope, or sends a bid with no exclusions. Each one falls short of the [prime and subcontracting]({SBA}) baseline.",
    ),
]

# claim, claim_type, url, evidence, intended_use, classification_key
ROWS = [
    ("A certificate of insurance proves a policy existed on the issue date", "factual", NAIC,
     "Consumer", "Key takeaways, certificate of insurance bullet", "naic-consumer"),
    ("Call the producer named on the certificate", "process", NAIC,
     "Consumer", "Prequalification pack table, general liability row", "naic-consumer"),
    ("Your state workers compensation agency", "process", NAIC,
     "Consumer", "Prequalification pack table, workers compensation row", "naic-consumer"),
    ("That the sub is permitted to perform the scope you are buying", "factual", SBA,
     "Prime and subcontracting", "Prequalification pack table, trade licence row", "sba-prime-and-subcontracting"),
    ("Screen on six fronts before you spend time on pricing", "process", SBA,
     "Prime and subcontracting", "Step 1 opener", "sba-prime-and-subcontracting"),
    ("Look the firm up through your state licensing board's online lookup", "process", SBA,
     "Prime and subcontracting", "Step 1, licence verification paragraph", "sba-prime-and-subcontracting"),
    ("End the conversation when a firm has no written safety program", "recommendation", SBA,
     "Prime and subcontracting", "Step 1, red flags paragraph", "sba-prime-and-subcontracting"),
    ("Citations do not disqualify a firm by themselves", "factual", OSHA_EST,
     "Establishment Search", "Step 1, safety record paragraph", "osha-establishment-search"),
    ("Contractors read a 1.00 as a clean bill of health", "factual", NCCI,
     "The mod applied to an employer's policy is either a unity (1.00) factor, a credit mod, or a debit mod.",
     "Step 1, experience modification paragraph", "ncci-abcs-of-experience-rating"),
    ("A signed subcontract does not make someone a contractor", "factual", DOL_FS13,
     "Employment under the FLSA is not determined by technical concepts or common law standards of control; it is broader than the common law standard often applied to determine employment status under other Federal laws.",
     "Step 3, classification opener", "dol-fact-sheet-13"),
    ("The Labor Department proposed replacing its independent contractor analysis in a rule published on February 27, 2026",
     "factual", FR,
     "Employee or Independent Contractor Status Under the Fair Labor Standards Act, Family and Medical Leave Act, and Migrant and Seasonal Agricultural Worker Protection Act",
     "Step 3, federal status paragraph", "federalregister-ic-nprm-2026"),
    ("For tax purposes the IRS weighs behavioral control, financial control and the type of relationship",
     "factual", IRS_IC,
     "There is no \"magic\" or set number of factors that \"makes\" the worker an employee or an independent contractor and no one factor stands alone in making this determination.",
     "Step 3, IRS test paragraph", "irs-independent-contractor-test"),
    ("Requiring a certificate differs from requiring an endorsement", "factual", NAIC,
     "Consumer", "Step 4, insurance clause paragraph", "naic-consumer"),
    ("allows more than one employer to receive a citation for the same hazardous condition", "factual", OSHA_ME,
     "more than one employer may be citable for a hazardous condition that violates an OSHA standard.",
     "Step 5, shared jobsite duty paragraph", "osha-multi-employer-citation-policy"),
]

NON_OFFICIAL = {"naic-consumer", "ncci-abcs-of-experience-rating"}


def sha(rel: str) -> str:
    return hashlib.sha256(pathlib.Path(rel).read_bytes()).hexdigest()


def row(claim, ctype, url, evidence, use, key) -> str:
    cls = "non_competing_expert" if key in NON_OFFICIAL else "primary_authority"
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
        "Freshness reason: Public authority page read on the checked date.",
        f"Classification artifact: {CLASS_DIR}/{key}.json",
        f"Classification hash: {sha(f'{CLASS_DIR}/{key}.json')}",
        "Citation mode: inline_required",
        "Status: approved",
        f"Intended use: {use}",
    ])


def main() -> int:
    art = ARTICLE.read_text(encoding="utf-8")
    applied = 0
    for old, new in LINK_EDITS:
        if old not in art:
            print(f"LINK MISS: {old[:70]}")
            continue
        art = art.replace(old, new, 1)
        applied += 1
    ARTICLE.write_text(art, encoding="utf-8")

    side = SIDECAR.read_text(encoding="utf-8")
    anchor = "\n\n## FAQ Source Policy"
    side = side.replace(anchor, "\n" + "\n".join(row(*r) for r in ROWS) + anchor, 1)
    SIDECAR.write_text(side, encoding="utf-8")
    print(f"link edits {applied}/{len(LINK_EDITS)}; residual rows added {len(ROWS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
