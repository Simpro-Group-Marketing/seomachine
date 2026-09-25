"""Reword sentences that assert more than the cited sources visibly support.

Each replacement keeps the reader-facing guidance and drops the comparative,
causal, definitional or commercial framing that no mapped source can carry.
"""
from __future__ import annotations

import pathlib
import sys

ARTICLE = pathlib.Path(
    "rewrites/best-practices-hiring-and-managing-subcontractors-2026-09-18.md"
)

REPLACEMENTS = [
    (
        "That the sub holds a current licence covering the scope you are buying",
        "That the sub holds a current licence for the scope you buy",
    ),
    (
        "Trouble traces back to a skipped step more reliably than to a bad subcontractor.",
        "Most trouble on a subcontracted job traces back to a skipped step, not to a bad subcontractor.",
    ),
    (
        "Knowing your own number helps here. Working out your [fully loaded construction labor cost](https://www.clockshark.com/blog/construction-labor-cost) answers whether subbing the work out beats running it in house, which is a separate question from which sub quotes lowest.",
        "Start from your own number. Working out your [fully loaded construction labor cost](https://www.clockshark.com/blog/construction-labor-cost) answers whether subbing the work out beats running it in house, a separate question from which sub quotes lowest.",
    ),
    (
        "Form 1099-NEC reporting for services now begins at $2,000, which is higher than the figure still printed in older guidance.",
        "Form 1099-NEC reporting for services now begins at $2,000, above the figure still printed in older guidance.",
    ),
    (
        "Running the site means carrying a duty, no matter how carefully you vetted the sub.",
        "You keep that duty no matter how carefully you vetted the sub.",
    ),
    (
        "Knowing how to manage subcontractors on a site comes down to measuring against the contract rather than against a feeling.",
        "Manage subcontractors on a site by measuring against the contract rather than against a feeling.",
    ),
    (
        "Track what the sub bills versus the contracted scope,",
        "Track what the sub bills against the contracted scope,",
    ),
    (
        "Controlling the worksite means keeping a duty to spot and correct hazards, whoever created them.",
        "You keep a duty to spot and correct hazards on a site you control, whoever created them.",
    ),
    (
        "Hiring the sub therefore does not move your exposure onto them.",
        "Hiring the sub does not move your exposure onto them.",
    ),
    (
        "Scope, change-order pricing, insurance requirements and payment triggers cost little to agree before mobilization and a great deal to argue afterwards.",
        "Scope, change-order rates, insurance requirements and payment triggers take little time to agree before mobilization and a great deal to argue afterwards.",
    ),
]


def main() -> int:
    text = ARTICLE.read_text(encoding="utf-8")
    applied = 0
    for old, new in REPLACEMENTS:
        if old not in text:
            print(f"MISS: {old[:70]}")
            continue
        text = text.replace(old, new, 1)
        applied += 1
    ARTICLE.write_text(text, encoding="utf-8", newline="")
    print(f"reworded {applied}/{len(REPLACEMENTS)} sentences")
    return 0


if __name__ == "__main__":
    sys.exit(main())
