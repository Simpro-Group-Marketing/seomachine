"""Third trim pass to land inside the brief's 2,200-2,500 word band.

Removes restatement rather than substance: one self-evident prequalification
row, one key takeaway already covered by practice 6, and the mistakes bullets
that echo their own capsule. Every cited claim and same-paragraph proof link
survives.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    # The executed subcontract is self-evident; the pack drops to eight items.
    (
        "| Countersigned subcontract | The scope, schedule, price and risk everyone agreed | Your own executed copy | Before mobilization |\n",
        "",
    ),
    (
        "Gather nine items before a subcontractor mobilizes. Each proves something narrower than it appears to, so the table separates what a document establishes from where you confirm it yourself. Verify at the source rather than accepting a forwarded PDF, because the gap between those two habits is where most subcontractor disputes begin.",
        "Gather these eight items before a subcontractor mobilizes. Each proves something narrower than it appears to, so the table separates what a document establishes from where you confirm it yourself. Verify at the source rather than accepting a forwarded PDF, because the gap between those habits is where most subcontractor disputes begin.",
    ),
    (
        "Build the prequalification pack above and use it on the next sub you hire. Nine documents, each verified at its own source, is the cheapest risk control a contractor has.",
        "Build the prequalification pack above and use it on the next sub you hire. Eight documents, each verified at its own source, is the cheapest risk control a contractor has.",
    ),
    # Practice 6 already owns the pre-mobilization paperwork point.
    (
        "- Paperwork belongs in your file before mobilization, because final payment is the last moment anyone has to ask for it.\n",
        "",
    ),
    (
        "Federal and public work adds a fifth. The Small Business Administration sets out [prime and subcontracting](https://www.sba.gov/counseling/prime-and-subcontracting/) responsibilities for contractors working on government projects, which is the baseline for how those relationships are supposed to run.",
        "Public work adds a fifth channel. The Small Business Administration sets out [prime and subcontracting](https://www.sba.gov/counseling/prime-and-subcontracting/) responsibilities for government projects, which is a useful baseline for how the relationship should run.",
    ),
    (
        "Ask about capacity while you are there, because a sub with the right licence and the wrong backlog still misses your dates. Cover what else runs in your window, how many crews they field, and who supervises when the owner is elsewhere. End the conversation on four signals: no written safety program, a refusal to name the insurance producer, a licence that excludes your scope, and references only covering work half your size.",
        "Ask about capacity too, because a sub with the right licence and the wrong backlog still misses your dates. Cover what else runs in your window, how many crews they field, and who supervises when the owner is elsewhere. End the conversation on four signals: no written safety program, a refusal to name the insurance producer, a licence that excludes your scope, and references only covering work half your size.",
    ),
    (
        "Onboarding is the last checkpoint where missing paperwork is still cheap. Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file, then run the site orientation: access, hours, storage, waste, who signs for deliveries, the safety rules every trade follows, and how the sub reaches you when something changes.",
        "Onboarding is the last checkpoint where missing paperwork is still cheap. Confirm the certificate, endorsement, workers compensation proof and signed subcontract are in the file, then run the site orientation: access, hours, storage, waste, deliveries, the safety rules every trade follows, and how the sub reaches you when something changes.",
    ),
    (
        "- Taking the low bid without comparing scope line by line.\n- Reading a 1.00 experience modification as a safety record rather than as a firm too small to rate.\n- Letting a sub mobilize before the documents are in the file.\n- Agreeing change-order pricing after the work instead of before it.\n- Leaving closeout paperwork until final payment is the only leverage left.",
        "- Reading a 1.00 experience modification as a safety record rather than as a firm too small to rate.\n- Agreeing change-order pricing after the work instead of before it.\n- Leaving closeout paperwork until final payment is the only leverage left.",
    ),
    (
        "Then ask who supervises when the owner is on another site. That answer predicts your schedule better than the bid does.",
        "Then ask who supervises when the owner is on another site. That answer predicts your schedule better than the bid.",
    ),
    (
        "Subs adjust quickly once they see every firm on your list measured the same way.",
        "Subs adjust once they see every firm measured the same way.",
    ),
    (
        "Record the rating at closeout while the detail is fresh. The rehire decision then takes minutes.",
        "Record the rating at closeout while the detail is fresh, and the rehire decision takes minutes.",
    ),
    (
        "Crews that trust your payment terms hold dates for you, and that advantage compounds over seasons.",
        "Crews that trust your payment terms hold dates for you, and that compounds over seasons.",
    ),
    (
        "Hiring the sub does not move your exposure onto them. You keep a duty to spot and correct hazards on a site you control, whoever created them.",
        "Hiring the sub does not move your exposure onto them. You keep a duty to spot and correct hazards on a site you control.",
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
