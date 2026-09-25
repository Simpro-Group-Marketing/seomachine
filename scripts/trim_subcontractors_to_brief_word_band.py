"""Trim body prose to the brief's 2,200-2,500 word band.

Capsules, FAQ opening answers, cited claims and their same-paragraph links are
left alone. The cuts come out of restatement.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    (
        "Most contractors stop at the trades they already know, then scramble when one is booked. Build four channels instead. Ask your suppliers which crews pay on time and return tools. Work the member directories of your local trade association chapters. Watch who does clean work on sites next to yours. Search your state licensing board for firms licensed in the exact scope you buy.",
        "Most contractors stop at the trades they already know, then scramble when one is booked. Build four channels instead: ask suppliers which crews pay on time and return tools, work the member directories of your local trade association chapters, watch who does clean work on neighbouring sites, and search your state licensing board for firms licensed in the exact scope you buy.",
    ),
    (
        "Ask about capacity while you are there. A sub with the right licence and the wrong backlog will still miss your dates. Ask what else they have running in your window, how many crews they can field, and who supervises when the owner is on another job. Close on four warning signs: no written safety program, a refusal to name the insurance producer, a licence that excludes your scope, and references that only cover work half your size.",
        "Ask about capacity while you are there, because a sub with the right licence and the wrong backlog still misses your dates. Cover what else runs in your window, how many crews they field, and who supervises when the owner is elsewhere. End the conversation on four signals: no written safety program, a refusal to name the insurance producer, a licence that excludes your scope, and references only covering work half your size.",
    ),
    (
        "Verify each claim at its own source rather than accepting a claim about it. Look the firm up",
        "Look the firm up",
    ),
    (
        "A low bid usually means a different scope, not a better price. Put every bidder on the same scope sheet and compare line by line: what is included, what is excluded, whose material, whose equipment, whose cleanup, and what happens when the schedule moves. Then read the exclusions twice, because that is where the change orders are already written.",
        "A low bid usually means a different scope, not a better price. Put every bidder on the same scope sheet: what is included, what is excluded, whose material, whose equipment, whose cleanup, and what happens when the schedule moves. Read the exclusions twice, because that is where the change orders are already written.",
    ),
    (
        "require the additional insured endorsement rather than a certificate, and set a date by which both arrive.",
        "require the endorsement rather than a certificate, and set a date by which both arrive.",
    ),
    (
        "An investigator and a plaintiff's attorney apply different tests, and for most contractors the lawsuit is the larger risk. For tax purposes the IRS weighs behavioral control, financial control and the type of relationship. Its guidance on",
        "An investigator and a plaintiff's attorney apply different tests, and for most contractors the lawsuit is the larger risk. The IRS runs its own test on behavioral control, financial control and the type of relationship, and its guidance on",
    ),
    (
        "that settles it. For a genuinely unclear case, ask the IRS to decide using",
        "that settles it. For an unclear case, ask the IRS to decide using",
    ),
    (
        "Confirm the certificate, endorsement, workers compensation proof and signed subcontract are all in the file, then run the site orientation: access and parking, hours, storage, waste, who signs for deliveries, the safety rules that apply to every trade, and how the sub reaches you when something changes.",
        "Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file, then run the site orientation: access, hours, storage, waste, who signs for deliveries, the safety rules every trade follows, and how the sub reaches you when something changes.",
    ),
    (
        "A sub who learns on Monday morning that the slab is not ready has already lost the crew to another job.",
        "A sub who learns on Monday that the slab is not ready has already lost the crew to another job.",
    ),
    (
        "Set predecessors and milestones before you commit anyone to dates. A worked example of how to",
        "Set predecessors and milestones before committing anyone to dates. A worked example of how to",
    ),
    (
        "The aim is catching a cost problem while the job runs, well before the final invoice lands.\n\nWatch the numbers that move first. Labor cost variance, rework rate and billing lag all surface an overrun while you can still act on it, which is why it pays to",
        "Catch the cost problem while the job runs, well before the final invoice lands.\n\nLabor cost variance, rework rate and billing lag each surface an overrun while you can still act on it, which is why it pays to",
    ),
    (
        "When something goes wrong, raise it on the day rather than at closeout, when the only remaining leverage is money you still owe.\n\nKeep the record in one place. A dispute two months later is settled",
        "Raise problems on the day rather than at closeout, when the only remaining leverage is money you still owe. A dispute two months later is settled",
    ),
    (
        "Reliable payment is what builds the network. Trades talk to each other, and the contractors who pay on agreed terms get the first call when a good crew has a gap.",
        "Reliable payment builds the network. Trades talk, and contractors who pay on agreed terms get the first call when a good crew has a gap.",
    ),
    (
        "If you are still rebuilding job cost from paper at month end, it is worth seeing how teams [compare",
        "If you are still rebuilding job cost from paper at month end, [compare",
    ),
    (
        "That answer predicts more about your schedule than the bid does.",
        "That answer predicts your schedule better than the bid does.",
    ),
    (
        "Consistency is what makes this work. Subs adjust quickly once they see that every firm on your list gets measured the same way.",
        "Subs adjust quickly once they see every firm on your list measured the same way.",
    ),
    (
        "Use the scorecard above and record the rating at closeout, while the detail is still fresh. The rehire decision then takes minutes.",
        "Record the rating at closeout while the detail is fresh. The rehire decision then takes minutes.",
    ),
    (
        "Crews that trust your payment terms hold dates for you. That is the whole advantage, and it compounds over seasons.",
        "Crews that trust your payment terms hold dates for you, and that advantage compounds over seasons.",
    ),
    (
        "The rest of the process gets easier once that habit lands, because every later step draws on something the pack already gave you.",
        "Every later step draws on something the pack already gave you.",
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
