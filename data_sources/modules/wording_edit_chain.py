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

import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

WORDING_EDIT_STAGE = "wording_edit"
WORDING_EDIT_TOOL = ("wording_edit", "1.0.0")
WORDING_EDIT_ANCHOR_STAGES = frozenset(
    {"context_binding", "post_optimization_context_binding"}
)
READINESS_STAGES = frozenset(
    {"preflight_readiness", "final_preflight_readiness", "final_readiness_attestation"}
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
    end = len(receipts)
    while (
        end
        and receipts[end - 1].get("stage") in READINESS_STAGES
        and _article(receipts[end - 1], "output_artifact_hashes") == final_sha256
    ):
        end -= 1
    for receipt in reversed(receipts[:end]):
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


def accepted_article_sha256s_from_paths(
    receipt_paths: Iterable[str | Path], final_sha256: str
) -> frozenset[str]:
    """Load receipt JSON files and return the accepted article hashes."""
    receipts: list[Mapping[str, Any]] = []
    for path in receipt_paths:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return frozenset({final_sha256})
        if not isinstance(payload, Mapping):
            return frozenset({final_sha256})
        receipts.append(payload)
    return accepted_article_sha256s(receipts, final_sha256)


def trailing_edit_indexes(receipts: Sequence[Mapping[str, Any]]) -> range:
    """Return the index range of the edit run before any trailing readiness receipts."""
    end = len(receipts)
    while end and receipts[end - 1].get("stage") in READINESS_STAGES:
        end -= 1
    start = end
    while start and receipts[start - 1].get("stage") == WORDING_EDIT_STAGE:
        start -= 1
    return range(start, end)


def bom_accepted_article_sha256s(bom: Mapping[str, Any]) -> frozenset[str]:
    """Return the accepted article hashes for a BOM's embedded receipt chain."""
    workflow = bom.get("workflow")
    artifacts = bom.get("artifacts")
    receipts = workflow.get("stage_receipts") if isinstance(workflow, Mapping) else None
    article = artifacts.get("article") if isinstance(artifacts, Mapping) else None
    final = article.get("sha256") if isinstance(article, Mapping) else None
    if not isinstance(final, str) or not isinstance(receipts, list):
        return frozenset()
    rows = [receipt for receipt in receipts if isinstance(receipt, Mapping)]
    return accepted_article_sha256s(rows, final)


def _article(receipt: Mapping[str, Any], field: str) -> str:
    hashes = receipt.get(field)
    value = hashes.get("article") if isinstance(hashes, Mapping) else None
    return value if isinstance(value, str) else ""
