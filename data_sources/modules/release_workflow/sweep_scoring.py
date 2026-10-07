"""Turn a release scorer result into sweep finding rows."""

from __future__ import annotations

from typing import Any, Mapping

try:
    from ..readiness.adapters import _scorecard_from_scorer_result
except ImportError:  # pragma: no cover - supports direct script execution.
    from readiness.adapters import _scorecard_from_scorer_result

SCORE_THRESHOLDS = "content 85, AEO/GEO 90"
# AEO/GEO checks that re-verify evidence against the vault claim set; offline they
# cannot be verified, so their failures are warnings in an offline sweep.
OFFLINE_UNVERIFIABLE_SCORER_CHECKS = frozenset({"eeat_proof"})
OFFLINE_PREFIX = "unverified offline (needs vault connector): "
SCORE_KEYS = ("content_quality", "seo_quality", "aeo_geo")


def _score_text(scorecard: Mapping[str, Any], key: str) -> str:
    gate = scorecard.get(key)
    gate = gate if isinstance(gate, Mapping) else {}
    score = gate.get("score")
    return f"{key} {'n/a' if score is None else score}/{gate.get('threshold')}"


def _meets_threshold(scorecard: Mapping[str, Any], key: str) -> bool:
    gate = scorecard.get(key)
    if not isinstance(gate, Mapping):
        return False
    score, threshold = gate.get("score"), gate.get("threshold")
    numeric = (int, float)
    if isinstance(score, bool) or isinstance(threshold, bool):
        return False
    return isinstance(score, numeric) and isinstance(threshold, numeric) and score >= threshold


def _failed_checks(result: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    checks = (result.get("aeo_geo") or {}).get("checks") or {}
    return {
        name: check for name, check in checks.items()
        if isinstance(check, Mapping) and check.get("passed") is False
    }


def _not_passed_row(
    result: Mapping[str, Any], failed: Mapping[str, Any], *, offline: bool
) -> dict[str, Any]:
    scorecard = _scorecard_from_scorer_result(result, artifact_kind="blog")
    message = (
        "Release scorer did not pass ("
        + ", ".join(_score_text(scorecard, key) for key in SCORE_KEYS)
        + f"; required: {SCORE_THRESHOLDS})"
    )
    only_unverifiable = bool(failed) and set(failed) <= OFFLINE_UNVERIFIABLE_SCORER_CHECKS
    seo = scorecard.get("seo_quality")
    seo_ok = isinstance(seo, Mapping) and seo.get("passed") is True
    downgrade = offline and only_unverifiable and seo_ok and all(
        _meets_threshold(scorecard, key) for key in ("content_quality", "aeo_geo")
    )
    return {
        "rule_id": "content_scorer.not_passed",
        "severity": "warning" if downgrade else "error",
        "line": None,
        "message": OFFLINE_PREFIX + message if downgrade else message,
    }


def scorer_findings(result: Mapping[str, Any], *, offline: bool = False) -> list[dict[str, Any]]:
    failed = _failed_checks(result)
    rows: list[dict[str, Any]] = []
    if result.get("passed") is False:
        rows.append(_not_passed_row(result, failed, offline=offline))
    for name, check in failed.items():
        unverifiable = offline and name in OFFLINE_UNVERIFIABLE_SCORER_CHECKS
        message = str(check.get("issue") or check.get("fix") or "check failed")
        rows.append({
            "rule_id": f"aeo_geo.{name}",
            "severity": "warning" if unverifiable else "error",
            "line": None,
            "message": OFFLINE_PREFIX + message if unverifiable else message,
        })
    return rows
