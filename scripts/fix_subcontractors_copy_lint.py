"""Clear the AI copy lint errors the trimming passes introduced.

Splits the long sentences, removes passive and modal constructions, and drops
the vague quantifiers. Capsules stay inside 50-60 words and 2-4 sentences, and
FAQ opening answers stay inside 40-60 words.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    # Table row repeated the paragraph's opening words.
    (
        "| Experience modification letter | Loss experience against a 1.00 unity factor |",
        "| Workers compensation mod letter | Loss experience against a 1.00 unity factor |",
    ),
    # Practices capsule: split the middle sentence, hold 50-60 words.
    (
        "These ten practices run in the order the work does. The first three cover finding and prequalifying subcontractors, the next three cover bidding, contracting and onboarding, and the last four cover running live jobs and paying reliably enough that good trades take your call next season. Subcontract management starts before the bid.",
        "These ten practices run in the order the work does. The first three cover finding and prequalifying subcontractors. The next three cover bidding, contracting and onboarding. The last four cover live jobs and paying reliably enough that good trades take your call next season, because subcontract management starts before the bid.",
    ),
    # Practice 1: passive voice and a long list sentence.
    (
        "Most contractors stop at the trades they already know, then scramble when one is booked. Build four channels instead: ask suppliers which crews pay on time, work your local trade association chapter directories, watch who does clean work on neighbouring sites, and search your state licensing board for firms licensed in the exact scope you buy.",
        "Most contractors stop at the trades they already know, then scramble when one of them turns the work down. Build four channels instead. Ask suppliers which crews pay on time. Work your local trade association chapter directories. Watch who does clean work on neighbouring sites. Search your state licensing board for firms licensed in the exact scope you buy.",
    ),
    # Practice 2: two long sentences and a vague quantifier.
    (
        "Prequalification is cheaper than a default. Screen on six fronts before you spend time on pricing: entity and licence, insurance, workers compensation, safety record, financial stability and quality control, using the pack above as the collection list.",
        "Prequalification is cheaper than a default. Screen on six fronts before you spend time on pricing: entity and licence, insurance, workers compensation, safety record, financial stability and quality control. Use the pack above as the collection list.",
    ),
    (
        "Ask about capacity too, because a sub with the right licence and the wrong backlog still misses your dates. Cover what else runs in your window, how many crews they field, and who supervises when the owner is elsewhere. End the conversation on four signals: no written safety program, a refusal to name the insurance producer, a licence that excludes your scope, and references only covering work half your size.",
        "Ask about capacity too, because a sub with the right licence and the wrong backlog still misses your dates. Cover what else runs in your window, the crew count they field, and who supervises when the owner is elsewhere. End the conversation on four signals. No written safety program. A refusal to name the insurance producer. A licence that excludes your scope. References only covering work half your size.",
    ),
    # Practice 3: one long sentence.
    (
        "Look the firm up through your state licensing board rather than trusting a licence number on a letterhead, and confirm the legal entity name matches the name on the [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) and on the insurance certificate.",
        "Look the firm up through your state licensing board rather than trusting a licence number on a letterhead. Confirm the legal entity name matches the name on the [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) and on the insurance certificate.",
    ),
    # Practice 4: vague quantifier and two passive constructions.
    (
        "A low bid usually means a different scope, not a better price. Put every bidder on the same scope sheet: what is included, what is excluded, whose material, whose equipment, whose cleanup, and what happens when the schedule moves. Read the exclusions twice, because that is where the change orders are already written.",
        "Treat a low bid as a scope difference until you prove otherwise. Put every bidder on the same scope sheet: what the bid covers, what it leaves out, whose material, whose equipment, whose cleanup, and what happens when the schedule moves. Read the exclusions twice, because that is where the change orders already sit.",
    ),
    # Practice 6: one long sentence.
    (
        "Onboarding is the last checkpoint where missing paperwork is still cheap. Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file, then run the site orientation: access, hours, storage, waste, deliveries, the safety rules every trade follows, and how the sub reaches you when something changes.",
        "Onboarding is the last checkpoint where missing paperwork is still cheap. Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file. Then run the site orientation: access, hours, storage, waste, deliveries, the safety rules every trade follows, and how the sub reaches you when something changes.",
    ),
    # Practice 8: modal verb.
    (
        "Labor cost variance, rework rate and billing lag each surface an overrun while you can still act on it, which is why it pays to [track labor cost variance before the job closes instead of after](https://www.clockshark.com/blog/construction-kpis-protect-margin).",
        "Labor cost variance, rework rate and billing lag each surface an overrun early enough to act on, which is why it pays to [track labor cost variance before the job closes instead of after](https://www.clockshark.com/blog/construction-kpis-protect-margin).",
    ),
    # Practice 9: modal verb.
    (
        "Name one person on each side who can decide.",
        "Name one decision maker on each side.",
    ),
    # Commercial bridge: heading preposition, vague quantifier, modal verb.
    (
        "## Use Better Systems to Manage Subcontractors Across Every Job",
        "## Use Better Systems to Manage Subcontractors across Every Job",
    ),
    (
        "Managing subcontractors across several jobs gets harder as the count rises, because the records that matter live in different places. Hours sit in one system, certificates in another, change orders in email. Putting schedule, hours and job cost in one place is what turns subcontract management from reconstruction into something you can see while work runs.",
        "Managing subcontractors across more than one job gets harder as the count rises, because the records that matter live in different places. Hours sit in one system, certificates in another, change orders in email. Putting schedule, hours and job cost together turns subcontract management from month-end reconstruction into something you watch while work runs.",
    ),
    # FAQ 2: split the long sentence, hold the answer in 40-60 words.
    (
        "Ask for the legal entity name shown on their [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9), licence numbers covering your exact scope, a certificate of insurance plus the additional insured endorsement, workers compensation proof, their OSHA inspection history, current backlog and crew count, and three references from jobs of your size and type.",
        "Ask for the legal entity name shown on their [Form W-9](https://www.irs.gov/forms-pubs/about-form-w-9) and licence numbers covering your exact scope. Then ask for a certificate of insurance plus the additional insured endorsement, workers compensation proof, OSHA inspection history, current backlog and crew count, and three references from jobs your size.",
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
    print(f"applied {len(EDITS) - len(missed)}/{len(EDITS)} lint fixes")
    for entry in missed:
        print("MISS:", entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
