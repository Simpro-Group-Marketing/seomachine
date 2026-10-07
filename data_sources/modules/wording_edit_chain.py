"""Stage-chain rules for chained wording-only edit receipts.

Zero or more ``wording_edit`` receipts may follow ``context_binding`` or
``post_optimization_context_binding``. Sequence checks compare the chain with
those edits removed; a misplaced edit is kept so every closed-sequence check
fails on it. Artifacts bound before the edits (context binding, machine
reviews, plan fulfillment, optimizer output, scrub) stay valid only for the
article hashes of that trailing edit run.

This module is a leaf so every receipt validator can import it.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

WORDING_EDIT_STAGE = "wording_edit"
WORDING_EDIT_TOOL = ("wording_edit", "1.0.0")
WORDING_EDIT_ANCHOR_STAGES = frozenset(
    {"context_binding", "post_optimization_context_binding"}
)
MAX_CUMULATIVE_CHANGED_WORD_RATIO = 0.10


def base_stages(stages: Iterable[str]) -> tuple[str, ...]:
    """Return the closed-sequence stages with validly placed edits removed."""
    kept: list[str] = []
    previous = ""
    for stage in stages:
        placed = previous in WORDING_EDIT_ANCHOR_STAGES or previous == WORDING_EDIT_STAGE
        if not (stage == WORDING_EDIT_STAGE and placed):
            kept.append(stage)
        previous = stage
    return tuple(kept)


def accepted_article_sha256s(
    receipts: Sequence[Mapping[str, Any]], final_sha256: str
) -> frozenset[str]:
    """Return the article hashes earlier artifacts may bind for this chain."""
    accepted = {final_sha256}
    expected_output = final_sha256
    for receipt in reversed(receipts):
        stage = receipt.get("stage")
        article_out = _article(receipt, "output_artifact_hashes")
        if stage != WORDING_EDIT_STAGE:
            if stage in WORDING_EDIT_ANCHOR_STAGES and article_out == expected_output:
                return frozenset(accepted)
            return frozenset({final_sha256})
        article_in = _article(receipt, "input_artifact_hashes")
        if article_out != expected_output or not article_in:
            return frozenset({final_sha256})
        accepted.add(article_in)
        expected_output = article_in
    return frozenset({final_sha256})


def _article(receipt: Mapping[str, Any], field: str) -> str:
    hashes = receipt.get(field)
    value = hashes.get("article") if isinstance(hashes, Mapping) else None
    return value if isinstance(value, str) else ""
