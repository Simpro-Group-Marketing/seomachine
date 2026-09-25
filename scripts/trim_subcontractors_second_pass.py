"""Second trim pass: tighten the two artifact tables and the longest practices.

Targets the heaviest sections without dropping a prequalification row, a cited
claim, or any same-paragraph proof link.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    # Prequalification table: same nine rows, shorter cells.
    (
        "| Signed Form W-9 | Legal name, entity type and taxpayer ID for year-end reporting | [IRS Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) | Before first payment |",
        "| Signed Form W-9 | Legal name, entity type and taxpayer ID for year-end reporting | [IRS Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) | Before first payment |",
    ),
    (
        "| Certificate of general liability insurance | That a policy existed on the issue date, and nothing beyond that | Call the producer named on the certificate, then check the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
        "| Certificate of general liability insurance | That a policy existed on the issue date, and nothing more | Call the producer named on the certificate, then check the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
    ),
    (
        "| Additional insured endorsement | That your business carries cover under the sub's policy | Request the endorsement form number and read it, because a certificate does not amend a policy | Before mobilization |",
        "| Additional insured endorsement | That your business carries cover under the sub's policy | Request the endorsement form number and read it. A certificate does not amend a policy | Before mobilization |",
    ),
    (
        "| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt on your job | Your state workers compensation agency, and the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
        "| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt | Your state workers compensation agency, and the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
    ),
    (
        "| State or local trade license | That the sub holds a current licence for the scope you buy | Your state licensing board's online license lookup, using the [prime and subcontracting](https://www.sba.gov/counseling/prime-and-subcontracting/) responsibilities as your baseline | Before signing |",
        "| State or local trade license | That the sub holds a current licence for the scope you buy | Your state licensing board's online lookup, against the [prime and subcontracting](https://www.sba.gov/counseling/prime-and-subcontracting/) baseline | Before signing |",
    ),
    (
        "| Experience modification letter | Workers compensation loss experience against a 1.00 unity factor | The sub's carrier or agent, read with the caveat in practice 3 | During prequalification |",
        "| Experience modification letter | Loss experience against a 1.00 unity factor | The sub's carrier or agent, read with the caveat in practice 3 | During prequalification |",
    ),
    (
        "| Countersigned subcontract | The scope, schedule, price and risk allocation everyone agreed to | Your own executed copy | Before mobilization |",
        "| Countersigned subcontract | The scope, schedule, price and risk everyone agreed | Your own executed copy | Before mobilization |",
    ),
    # Practice 3: drop the restated verification instruction.
    (
        "Read the safety record instead of accepting a claim about it. Search the firm through [OSHA's Establishment Search](https://www.osha.gov/ords/imis/establishment.html) under every legal name it uses, then pull recordable injury rates from [OSHA's public injury tracking data](https://www.osha.gov/itadata).",
        "Search the firm through [OSHA's Establishment Search](https://www.osha.gov/ords/imis/establishment.html) under every legal name it uses, then pull recordable injury rates from [OSHA's public injury tracking data](https://www.osha.gov/itadata).",
    ),
    (
        "Treat the experience modification factor carefully. Contractors read a 1.00 as a clean bill of health. [NCCI's guide to experience rating](https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf) explains that the mod applied to a policy \"is either a unity (1.00) factor, a credit mod, or a debit mod,\" and that an employer receives that same unity factor when \"it does not meet eligibility requirements for experience rating\" at all. A small sub showing 1.00 sits below the rating threshold, which tells you nothing about their safety.",
        "Contractors read a 1.00 experience modification as a clean bill of health. [NCCI's guide to experience rating](https://www.ncci.com/Articles/Documents/UW_ABC_Exp_Rating.pdf) explains that the mod applied to a policy \"is either a unity (1.00) factor, a credit mod, or a debit mod,\" and that an employer receives that same unity factor when \"it does not meet eligibility requirements for experience rating\" at all. A small sub showing 1.00 sits below the rating threshold, which tells you nothing about their safety.",
    ),
    # Practice 5: tighten the classification prose around the quotes.
    (
        "A signed subcontract does not make someone a contractor. Classification turns on how the working relationship operates, not on what the contract calls it. The Labor Department proposed replacing its independent contractor analysis in a [rule published on February 27, 2026](https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical), with the comment period closing on April 28, 2026. That proposal rescinds the analysis currently sitting in [29 CFR part 795](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-795) and returns to an earlier economic realities test built around control and the worker's opportunity for profit or loss.",
        "A signed subcontract does not make someone a contractor. Classification turns on how the working relationship operates, not on what the contract calls it. The Labor Department proposed replacing its independent contractor analysis in a [rule published on February 27, 2026](https://www.federalregister.gov/documents/2026/02/27/2026-03962/employee-or-independent-contractor-status-under-the-fair-labor-standards-act-family-and-medical), with the comment period closing on April 28, 2026. That proposal rescinds the analysis currently sitting in [29 CFR part 795](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-795) and returns to an earlier economic realities test built around control.",
    ),
    # Practice 8: the scorecard rows carry the detail, so the lead can shorten.
    (
        "Manage against written scope and verifiable records rather than conversations. Track what the sub bills against the contracted scope, how their hours land against your job budget, and how they absorb schedule changes. Catch the cost problem while the job runs, well before the final invoice lands.",
        "Manage against written scope and verifiable records rather than conversations. Track what the sub bills against the contracted scope, how their hours land against your job budget, and how they absorb schedule changes, so a cost problem surfaces while the job runs.",
    ),
    (
        "Score every sub on the same five criteria, then let the score drive the rehire decision.",
        "Score every sub on the same five criteria and let the score drive the rehire decision.",
    ),
    (
        "| Schedule adherence | Days late against the agreed milestone | More than 3 days late, no warning | On time, or early warning given |",
        "| Schedule adherence | Days late against the agreed milestone | Over 3 days late, no warning | On time, or warned early |",
    ),
    (
        "| Rework | Items on your punch list from their scope | More than 5 items | 0 to 2 items |",
        "| Rework | Punch list items from their scope | Over 5 items | 0 to 2 items |",
    ),
    (
        "| Safety | Recordable incidents and rule breaches on your site | Any recordable incident | None, orientation followed |",
        "| Safety | Recordable incidents and rule breaches | Any recordable incident | None, orientation followed |",
    ),
    (
        "| Documentation | Certificates, waivers and invoices on time | Chased more than twice | Arrived without chasing |",
        "| Documentation | Certificates, waivers and invoices on time | Chased twice or more | Arrived without chasing |",
    ),
    (
        "Rehire threshold: strong on safety and documentation, and no more than one poor rating across the other three.",
        "Rehire threshold: strong on safety and documentation, and at most one poor rating elsewhere.",
    ),
    # Mistakes: the capsule already names four, so the list can lose its echoes.
    (
        "- Taking the low bid without comparing scope line by line.\n- Accepting a certificate of insurance and never asking for the additional insured endorsement.\n- Reading a 1.00 experience modification as a safety record rather than as a firm too small to rate.\n- Letting a sub mobilize before the documents are in the file.\n- Agreeing change-order pricing after the work instead of before it.\n- Holding final payment as the first moment anyone asks for the closeout paperwork.",
        "- Taking the low bid without comparing scope line by line.\n- Reading a 1.00 experience modification as a safety record rather than as a firm too small to rate.\n- Letting a sub mobilize before the documents are in the file.\n- Agreeing change-order pricing after the work instead of before it.\n- Leaving closeout paperwork until final payment is the only leverage left.",
    ),
    # Practice 10 and the close.
    (
        "Pay against the milestones and retainage written into the subcontract, after an approved invoice and a signed lien waiver for the work being paid. Check billed hours against the record before you approve anything, using a format that",
        "Pay against the milestones and retainage in the subcontract, after an approved invoice and a signed lien waiver. Check billed hours against the record first, using a format that",
    ),
    (
        "Build the prequalification pack above and use it on the next sub you hire. Nine documents, each verified at its own source, is the cheapest risk control available to a contractor.",
        "Build the prequalification pack above and use it on the next sub you hire. Nine documents, each verified at its own source, is the cheapest risk control a contractor has.",
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
    print(f"applied {len(EDITS) - len(missed)}/{len(EDITS)} trims")
    for entry in missed:
        print("MISS:", entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
