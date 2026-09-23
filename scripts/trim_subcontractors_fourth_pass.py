"""Final trim pass into the brief's 2,200-2,500 word band.

Condenses the prequalification table's verification cells and the two longest
practices. Cited quotes, proof links and the capsules are untouched.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    (
        "| Certificate of general liability insurance | That a policy existed on the issue date, and nothing more | Call the producer named on the certificate, then check the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
        "| Certificate of general liability insurance | That a policy existed on the issue date, and nothing more | The producer named on it, then the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
    ),
    (
        "| Additional insured endorsement | That your business carries cover under the sub's policy | Request the endorsement form number and read it. A certificate does not amend a policy | Before mobilization |",
        "| Additional insured endorsement | That your business carries cover under the sub's policy | Ask for the endorsement form number and read it. A certificate does not amend a policy | Before mobilization |",
    ),
    (
        "| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt | Your state workers compensation agency, and the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
        "| Workers compensation certificate or state exemption | Whether you inherit the claim when a sub's worker gets hurt | Your state workers compensation agency, and the carrier through [your state insurance department](https://content.naic.org/consumer) | Before mobilization |",
    ),
    (
        "| Recordable injury rates | Injury frequency rather than a claim about safety culture | [OSHA public injury tracking data](https://www.osha.gov/itadata) | During prequalification |",
        "| Recordable injury rates | Injury frequency, not safety culture | [OSHA public injury tracking data](https://www.osha.gov/itadata) | During prequalification |",
    ),
    (
        "| OSHA inspection history | Federal or state-plan enforcement at the sub's establishments | [OSHA Establishment Search](https://www.osha.gov/ords/imis/establishment.html) | During prequalification |",
        "| OSHA inspection history | Federal or state-plan enforcement at their establishments | [OSHA Establishment Search](https://www.osha.gov/ords/imis/establishment.html) | During prequalification |",
    ),
    (
        "The subcontract carries scope, schedule, price, change-order pricing, insurance requirements, payment triggers, retainage, lien waivers and termination. Get specific about insurance: name the limits, require the endorsement rather than a certificate, and set a date by which both arrive.",
        "The subcontract carries scope, schedule, price, change-order pricing, insurance requirements, payment triggers, retainage, lien waivers and termination. Name the insurance limits, require the endorsement rather than a certificate, and set a date by which both arrive.",
    ),
    (
        "An investigator and a plaintiff's attorney apply different tests, and for most contractors the lawsuit is the larger risk. The IRS runs its own test on behavioral control, financial control and the type of relationship, and its guidance on [worker status](https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee) states plainly that there is \"no 'magic' or set number of factors\" that settles it. For an unclear case, ask the IRS to decide using [Form SS-8](https://www.irs.gov/forms-pubs/about-form-ss-8) rather than guessing. This section gives general information rather than legal or tax advice.",
        "An investigator and a plaintiff's attorney apply different tests, and for most contractors the lawsuit is the larger risk. The IRS runs its own test, and its guidance on [worker status](https://www.irs.gov/businesses/small-businesses-self-employed/independent-contractor-self-employed-or-employee) states plainly that there is \"no 'magic' or set number of factors\" that settles it. For an unclear case, ask the IRS to decide using [Form SS-8](https://www.irs.gov/forms-pubs/about-form-ss-8). This section gives general information rather than legal or tax advice.",
    ),
    (
        "Manage against written scope and verifiable records rather than conversations. Track what the sub bills against the contracted scope, how their hours land against your job budget, and how they absorb schedule changes, so a cost problem surfaces while the job runs.",
        "Manage against written scope and verifiable records rather than conversations. Track what the sub bills against the contracted scope, how their hours land against your job budget, and how they absorb schedule changes, so overruns surface while the job runs.",
    ),
    (
        "| Change-order behavior | How extras surfaced and got priced | Surprise extras after the fact | Raised early and priced fairly |",
        "| Change-order behavior | How extras surfaced and got priced | Surprise extras after the fact | Raised early, priced fairly |",
    ),
    (
        "Look the firm up through your state licensing board's online lookup rather than trusting a licence number on a letterhead, and confirm the legal entity name matches the name on the [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) and on the insurance certificate.",
        "Look the firm up through your state licensing board rather than trusting a licence number on a letterhead, and confirm the legal entity name matches the name on the [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) and on the insurance certificate.",
    ),
    (
        "Prequalification is cheaper than a default. Screen on six fronts before you spend time on pricing: entity and licence, insurance, workers compensation, safety record, financial stability and quality control. Use the pack above as the collection list.",
        "Prequalification is cheaper than a default. Screen on six fronts before you spend time on pricing: entity and licence, insurance, workers compensation, safety record, financial stability and quality control, using the pack above as the collection list.",
    ),
    (
        "Pay against the milestones and retainage in the subcontract, after an approved invoice and a signed lien waiver. Check billed hours against the record first, using a format that [captures hours by job and cost code](https://www.clockshark.com/blog/construction-timesheet-template) so an invoice can be compared with real time rather than accepted on trust.",
        "Pay against the milestones and retainage in the subcontract, after an approved invoice and a signed lien waiver. Check billed hours against the record first, using a format that [captures hours by job and cost code](https://www.clockshark.com/blog/construction-timesheet-template) so an invoice meets real time rather than trust.",
    ),
    (
        "Subs cannot plan around dates you have not given them. Publish one schedule, show each trade what has to finish before they mobilize, and tell them early when a predecessor slips. A sub who learns on Monday that the slab is not ready has already lost the crew to another job.",
        "Subs cannot plan around dates you have not given them. Publish one schedule, show each trade what has to finish before they mobilize, and warn them early when a predecessor slips. A sub who learns on Monday that the slab is not ready has already lost the crew.",
    ),
    (
        "Name one person on each side who can decide. Put change-order requests in writing before the work happens, not after the invoice, and price them against the rates already in the subcontract. Raise problems on the day rather than at closeout, when the only remaining leverage is money you still owe. A dispute two months later is settled by what was written down at the time, not by what either side remembers.",
        "Name one person on each side who can decide. Put change-order requests in writing before the work happens, not after the invoice, and price them against the rates already in the subcontract. Raise problems on the day rather than at closeout, when the only leverage left is money you still owe. A dispute two months later turns on what was written down at the time.",
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
