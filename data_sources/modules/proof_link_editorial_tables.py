"""Header recognition for editorial buyer-guidance tables in proof-link analysis."""

from __future__ import annotations


def editorial_guidance_table_contract(line: str) -> str:
    cells = tuple(cell.strip().casefold() for cell in line.strip().strip("|").split("|"))
    return {
        ("tool", "best fit", "avoid when", "validate before buying"): "buyer_decision_matrix",
        ("criterion", "evidence to collect", "pass signal"): "buyer_scorecard",
    }.get(cells, "")
