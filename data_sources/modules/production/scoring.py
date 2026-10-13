"""Score gate: the existing content scorer fed a proof view rendered from the production BOM.

One ``ContentScorer.score`` call yields all three gates. With ``workers > 1`` that call
runs in a process pool so it overlaps the release check's truth and coverage threads.
The gates mirror ``readiness/adapters.py``: each passes only when the scorer's own
verdict passes and the score meets the threshold; SEO also needs zero critical issues.
Scoring needs no network: URL resolution and source support belong to the truth layer.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from data_sources.modules.blog_assembly_contract import current_utc_date
from data_sources.modules.production.proof_view import render_proof_view

CONTENT_MIN = 85
SEO_MIN = 90
AEO_MIN = 90


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _meets(value: Any, threshold: int) -> bool:
    number = _number(value)
    return number is not None and number >= threshold


def _gate(source: Mapping[str, Any], threshold: int) -> dict[str, Any]:
    score = source.get("score")
    return {"score": score, "threshold": threshold, "passed": bool(source.get("passed")) and _meets(score, threshold)}


def _failed_checks(aeo: Mapping[str, Any]) -> list[str]:
    checks = aeo.get("checks") if isinstance(aeo.get("checks"), Mapping) else {}
    return [name for name, check in checks.items() if isinstance(check, Mapping) and not check.get("passed")]


def score_gates(result: Mapping[str, Any]) -> dict[str, Any]:
    """Turn one scorer result into the three release gates and the summary record."""
    gates = result.get("quality_gates") if isinstance(result.get("quality_gates"), Mapping) else {}
    content = _gate(gates.get("content_quality") or {}, CONTENT_MIN)
    seo_source = gates.get("seo_quality") or {}
    critical = list(seo_source.get("critical_issues") or [])
    seo = {**_gate(seo_source, SEO_MIN), "critical_issue_count": len(critical), "critical_issues": critical}
    seo["passed"] = seo["passed"] and not critical
    aeo_source = result.get("aeo_geo") if isinstance(result.get("aeo_geo"), Mapping) else {}
    aeo = {**_gate(gates.get("aeo_geo") or aeo_source, AEO_MIN), "failed_checks": _failed_checks(aeo_source)}
    return {
        "content": _number(content["score"]) or 0.0,
        "seo": _number(seo["score"]) or 0.0,
        "seo_critical": len(critical),
        "aeo_geo": _number(aeo["score"]) or 0.0,
        "priority_fixes": list(result.get("priority_fixes") or []),
        "passed": content["passed"] and seo["passed"] and aeo["passed"],
        "gates": {"content_quality": content, "seo_quality": seo, "aeo_geo": aeo},
    }


def scoring_metadata(bom: Mapping[str, Any]) -> dict[str, Any]:
    """Scorer metadata and PAA expectations, taken only from the BOM (JSON-safe, picklable)."""
    identity, keyword, paa = bom["identity"], bom["keyword"], bom.get("paa") or {}
    secondary = keyword.get("secondary")
    return {
        "scorer": {
            "primary_keyword": keyword["primary"],
            "secondary_keywords": list(secondary) if isinstance(secondary, list) else [],
            "faq_policy_status": "required" if paa.get("questions") else "not_applicable",
        },
        "paa": {
            "workflow_mode": identity["workflow_mode"],
            "expected_query": str((bom.get("serp") or {}).get("query") or ""),
            "expected_collection_date": str(paa.get("collection_date") or ""),
            "expected_run_id": identity["run_id"],
        },
    }


def _verify_bound(root: Path, binding: Any) -> None:
    if not isinstance(binding, Mapping):
        return
    path = root / binding["path"]
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
    if actual != binding["sha256"]:
        raise ValueError(f"bound artifact changed since the BOM was built: {binding['path']}")


def score_in_process(article_path: str, proof_view: str, paa_artifact: str | None, metadata: dict) -> dict:
    """Run one ContentScorer call; top level and primitive-argument so a process pool can pickle it."""
    from data_sources.modules.content_scoring.scorer import ContentScorer

    article = Path(article_path)
    paa = metadata["paa"]
    result = ContentScorer().score(
        article.read_text(encoding="utf-8"),
        metadata=dict(metadata["scorer"]),
        validate_urls=False,
        validate_source_support=False,
        source_path=str(article),
        # Never written: the view is passed as content; the path only anchors rater lookups.
        proof_sidecar=str(article.parents[1] / "research" / f"production-proof-view-{article.stem}.md"),
        proof_content=proof_view,
        assembly_date=metadata["assembly_date"],
        paa_workflow_mode=paa["workflow_mode"] or None,
        paa_expected_query=paa["expected_query"] or None,
        paa_expected_collection_date=paa["expected_collection_date"] or None,
        paa_expected_run_id=paa["expected_run_id"] or None,
        paa_artifact=paa_artifact,
    )
    return score_gates(result)


def score_article(article_path: Path, bom: Mapping[str, Any], *, workers: int) -> dict[str, Any]:
    """Score the article against its BOM; one scorer call, in a process pool when workers > 1."""
    article = Path(article_path).resolve()
    root = article.parents[1]
    paa_binding = (bom.get("paa") or {}).get("artifact")
    _verify_bound(root, paa_binding)
    _verify_bound(root, (bom.get("customer_proof") or {}).get("evidence"))
    view = render_proof_view(bom, article=article.read_text(encoding="utf-8"), root=root)
    paa_path = str(root / paa_binding["path"]) if isinstance(paa_binding, Mapping) else None
    metadata = {**scoring_metadata(bom), "assembly_date": current_utc_date().isoformat()}
    args = (str(article), view, paa_path, metadata)
    if workers <= 1:
        return score_in_process(*args)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return pool.submit(score_in_process, *args).result()
