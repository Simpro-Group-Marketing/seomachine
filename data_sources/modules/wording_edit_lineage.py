"""Verified wording-edit lineage for release consumers.

Earlier artifacts may bind an article hash from the trailing wording-edit run
only after every edit in that run re-verifies from its evidence. Without edits
these helpers read nothing, so captured readiness inputs are never reopened.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_stage_receipt import StageReceiptError, stage_evidence_path
    from .wording_edit import verify_wording_edits
    from .wording_edit_chain import accepted_article_sha256s, trailing_edit_indexes
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_stage_receipt import StageReceiptError, stage_evidence_path
    from wording_edit import verify_wording_edits
    from wording_edit_chain import accepted_article_sha256s, trailing_edit_indexes


def verified_lineage_from_paths(
    receipt_paths: Sequence[str | Path],
    *,
    article_path: str | Path,
    sidecar_path: str | Path | None,
) -> frozenset[str]:
    """Return lineage hashes only when every trailing wording edit verifies."""
    try:
        receipts = [json.loads(Path(path).read_text(encoding="utf-8")) for path in receipt_paths]
        if not all(isinstance(receipt, Mapping) for receipt in receipts) or not trailing_edit_indexes(receipts):
            return frozenset()
        article = Path(article_path).read_bytes().decode("utf-8")
        sidecar = Path(sidecar_path).read_bytes().decode("utf-8") if sidecar_path else ""
    except (OSError, UnicodeError, json.JSONDecodeError):
        return frozenset()
    return _verified(receipts, article, sidecar, paths=receipt_paths)[0]


def verified_bom_lineage(
    bom: Mapping[str, Any], root: str | Path, *, captured: Any = None
) -> tuple[frozenset[str], list[str]]:
    """Return a BOM's verified lineage hashes and any wording-edit verification errors."""
    artifacts = bom.get("artifacts") if isinstance(bom.get("artifacts"), Mapping) else {}
    workflow = bom.get("workflow") if isinstance(bom.get("workflow"), Mapping) else {}
    rows, receipts = artifacts.get("stage_receipts"), workflow.get("stage_receipts")
    if not isinstance(rows, list) or not isinstance(receipts, list) or len(rows) != len(receipts):
        return frozenset(), []
    if not all(isinstance(receipt, Mapping) for receipt in receipts) or not trailing_edit_indexes(receipts):
        return frozenset(), []
    try:
        if captured is None:
            article = (Path(root) / str(artifacts["article"]["path"])).read_bytes().decode("utf-8")
            sidecar = (Path(root) / str(artifacts["validation_sidecar"]["path"])).read_bytes().decode("utf-8")
            paths = [Path(root) / str(row["path"]) for row in rows]
            return _verified(receipts, article, sidecar, paths=paths)
        article = captured.text_row(artifacts["article"], field="artifacts.article")
        sidecar = captured.text_row(artifacts["validation_sidecar"], field="artifacts.validation_sidecar")
        evidence = {
            str(row.get("path")): row for row in artifacts.get("stage_evidence") or [] if isinstance(row, Mapping)
        }

        def load(index: int) -> Mapping[str, Any]:
            path = stage_evidence_path(Path(str(rows[index]["path"]))).as_posix()
            return captured.json_row(evidence[path], field="artifacts.stage_evidence").get("payload") or {}

        return _verified(receipts, article, sidecar, paths=[], evidence_loader=load)
    except (OSError, UnicodeError, KeyError, TypeError, ValueError, StageReceiptError) as error:
        return frozenset(), [f"wording edit evidence is unavailable: {error}"]


def _verified(
    receipts: Sequence[Mapping[str, Any]],
    article: str,
    sidecar: str,
    *,
    paths: Sequence[str | Path],
    evidence_loader: Any = None,
) -> tuple[frozenset[str], list[str]]:
    try:
        errors = verify_wording_edits(
            paths, receipts, final_article=article, sidecar=sidecar, evidence_loader=evidence_loader
        )
    except (KeyError, TypeError, AttributeError) as error:
        errors = [f"wording edit receipts are malformed: {error}"]
    if errors:
        return frozenset(), errors
    return accepted_article_sha256s(receipts, hashlib.sha256(article.encode("utf-8")).hexdigest()), []
