"""Bring the article under the brief's 2,500-word ceiling.

Small cuts spread across takeaways, FAQ closers and scorecard framing. No capsule,
cited quote or proof link is touched.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

EDITS: list[tuple[str, str]] = [
    (
        "- A certificate of insurance proves a policy existed on the issue date. It does not make you an additional insured, and the carrier named on it is worth confirming with [your state insurance department](https://content.naic.org/consumer).",
        "- A certificate of insurance proves a policy existed on the issue date. It does not make you an additional insured, and the carrier is worth confirming with [your state insurance department](https://content.naic.org/consumer).",
    ),
    (
        "- Vetting a sub's safety record does not discharge your own duty on a shared jobsite under [OSHA's multi-employer citation policy](https://www.osha.gov/enforcement/directives/cpl-02-00-124).",
        "- Vetting a sub's safety record does not discharge your own duty under [OSHA's multi-employer citation policy](https://www.osha.gov/enforcement/directives/cpl-02-00-124).",
    ),
    (
        "Most of the risk in that arc stays invisible at the handshake. A sub's crew shortage becomes your schedule problem. The [2026 AGC workforce survey](https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20%284%29.pdf) found that 42 percent of firms reported shortages of their own workers or their subcontractors' workers delaying projects.",
        "Most of that risk stays invisible at the handshake. A sub's crew shortage becomes your schedule problem. The [2026 AGC workforce survey](https://www.agc.org/sites/default/files/users/user21902/2026%20Workforce%20Survey%20Analysis%20%284%29.pdf) found that 42 percent of firms reported shortages of their own workers or their subcontractors' workers delaying projects.",
    ),
    (
        "Most contractors stop at the trades they already know, then scramble when one is booked. Build four channels instead: ask suppliers which crews pay on time and return tools, work the member directories of your local trade association chapters, watch who does clean work on neighbouring sites, and search your state licensing board for firms licensed in the exact scope you buy.",
        "Most contractors stop at the trades they already know, then scramble when one is booked. Build four channels instead: ask suppliers which crews pay on time, work your local trade association chapter directories, watch who does clean work on neighbouring sites, and search your state licensing board for firms licensed in the exact scope you buy.",
    ),
    (
        "Score every sub on the same five criteria and let the score drive the rehire decision.",
        "Score every sub on the same five criteria.",
    ),
    (
        "Rehire threshold: strong on safety and documentation, and at most one poor rating elsewhere.",
        "Rehire threshold: strong on safety and documentation, at most one poor rating elsewhere.",
    ),
    (
        "Then ask who supervises when the owner is on another site. That answer predicts your schedule better than the bid.",
        "Then ask who supervises when the owner is on another site.",
    ),
    (
        "Subs adjust once they see every firm measured the same way.",
        "Subs adjust once they see every firm measured the same way.",
    ),
    (
        "Record the rating at closeout while the detail is fresh, and the rehire decision takes minutes.",
        "Record the rating at closeout, while the detail is fresh.",
    ),
    (
        "Crews that trust your payment terms hold dates for you, and that compounds over seasons.",
        "Crews that trust your payment terms hold dates for you.",
    ),
    (
        "Hiring the sub does not move your exposure onto them. You keep a duty to spot and correct hazards on a site you control.",
        "Hiring the sub does not move your exposure onto them.",
    ),
    (
        "Reliable payment builds the network. Trades talk, and contractors who pay on agreed terms get the first call when a good crew has a gap.",
        "Reliable payment builds the network. Contractors who pay on agreed terms get the first call when a good crew has a gap.",
    ),
    (
        "Build the prequalification pack above and use it on the next sub you hire. Eight documents, each verified at its own source, is the cheapest risk control a contractor has.\n\nEvery later step draws on something the pack already gave you.",
        "Build the prequalification pack above and use it on the next sub you hire. Eight documents, each verified at its own source, is the cheapest risk control a contractor has, and every later step draws on something the pack already gave you.",
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
