"""Add inline authority links to the units public_research_link_guard flagged.

Every claim that names insurance, licensing, safety duty or federal status now
carries a visible non-owned authority in its own paragraph or table row.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path("rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md")

NAIC = "https://content.naic.org/consumer"
OSHA_ME = "https://www.osha.gov/enforcement/directives/cpl-02-00-124"
OSHA_ITA = "https://www.osha.gov/itadata"
DOL_FS13 = "https://www.dol.gov/agencies/whd/fact-sheets/13-flsa-employment-relationship"
FR = "https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical"

EDITS = [
    # Key takeaways: each carries its own authority.
    (
        "- A certificate of insurance proves a policy existed on the issue date. It does not make you an additional insured.",
        f"- A certificate of insurance proves a policy existed on the issue date. It does not make you an additional insured, and the carrier named on it is worth confirming with [your state insurance department]({NAIC}).",
    ),
    (
        "- Vetting a sub's safety record does not discharge your own duty on a shared jobsite.",
        f"- Vetting a sub's safety record does not discharge your own duty on a shared jobsite under [OSHA's multi-employer citation policy]({OSHA_ME}).",
    ),
    # Prequalification table: verification cells point at the actual authority.
    (
        "| Certificate of general liability insurance | That a policy existed on the issue date, and nothing beyond that | Call the producer named on the certificate, then confirm the carrier with your state insurance department | Before mobilization |",
        f"| Certificate of general liability insurance | That a policy existed on the issue date, and nothing beyond that | Call the producer named on the certificate, then confirm the carrier through [your state insurance department]({NAIC}) | Before mobilization |",
    ),
    (
        "| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt on your job | Your state workers compensation agency | Before mobilization |",
        f"| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt on your job | Your state workers compensation agency, and the carrier through [your state insurance department]({NAIC}) | Before mobilization |",
    ),
    (
        "| Recordable injury rates | Injury frequency rather than a claim about safety culture | OSHA public injury tracking data | During prequalification |",
        f"| Recordable injury rates | Injury frequency rather than a claim about safety culture | [OSHA public injury tracking data]({OSHA_ITA}) | During prequalification |",
    ),
    # Step 1: the injury-rate route gets its real destination.
    (
        "then pull recordable injury rates from OSHA's public injury tracking data.",
        f"then pull recordable injury rates from [OSHA's public injury tracking data]({OSHA_ITA}).",
    ),
    # Step 3 opener: the clearest statement of why the federal test differs from the IRS test.
    (
        "Classification turns on how the working relationship operates, not on what the contract calls it. A signed subcontract does not make someone a contractor.",
        f"Classification turns on how the working relationship operates, not on what the contract calls it. A signed subcontract does not make someone a contractor. The Labor Department's [Fact Sheet 13]({DOL_FS13}) states that employment under the FLSA is not determined by common law standards of control, which is why the federal answer and the tax answer can differ.",
    ),
    # Step 3: the enforcement paragraph carries its own source rather than leaning on the one above it.
    (
        "**Paused enforcement is not reduced exposure.** Contractors get this part wrong. The same rulemaking document records",
        f"**Paused enforcement is not reduced exposure.** Contractors get this part wrong. The [same rulemaking document]({FR}) records",
    ),
    # Step 4: the endorsement distinction is an insurance claim, so it cites the regulator route.
    (
        "Get specific about insurance. Requiring a certificate differs from requiring an endorsement, and only the endorsement extends the sub's coverage to you.",
        f"Get specific about insurance. Requiring a certificate differs from requiring an endorsement, and only the endorsement extends the sub's coverage to you. Confirm the carrier behind both through [your state insurance department]({NAIC}).",
    ),
]


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    applied = 0
    for old, new in EDITS:
        if old not in text:
            print(f"MISS: {old[:78]}")
            continue
        text = text.replace(old, new, 1)
        applied += 1
    ARTICLE.write_text(text, encoding="utf-8")
    print(f"applied {applied}/{len(EDITS)} inline-proof edits")
    return 0 if applied == len(EDITS) else 1


if __name__ == "__main__":
    sys.exit(main())
