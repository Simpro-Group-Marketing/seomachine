"""Shared helpers for deterministic content guard modules."""

from __future__ import annotations

import re
from typing import Dict, Sequence


Finding = Dict[str, object]


def make_finding(
    rule_id: str,
    severity: str,
    line: int,
    *,
    column: int = 1,
    match: str = "",
    message: str = "",
    suggestion: str = "",
    **extra: object,
) -> Finding:
    """Build a guard finding with the common JSON shape."""
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": column,
    }
    if match:
        finding["match"] = match
    if message:
        finding["message"] = message
    if suggestion:
        finding["suggestion"] = suggestion
    finding.update(extra)
    return finding


def should_fail(findings: Sequence[Finding], fail_on: str = "error") -> bool:
    """Return True when findings meet the configured failure threshold."""
    if fail_on == "none":
        return False
    if fail_on == "warning":
        return any(finding["severity"] in {"warning", "error"} for finding in findings)
    if fail_on == "error":
        return any(finding["severity"] == "error" for finding in findings)
    raise ValueError("fail_on must be one of: error, warning, none")


def summarize_findings(findings: Sequence[Finding]) -> Dict[str, int]:
    """Count guard findings by blocking severity."""
    summary = {"error": 0, "warning": 0}
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


def normalize_for_match(text: str) -> str:
    """Normalize text for loose artifact/question matching."""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def normalize_key(value: str) -> str:
    """Normalize proof keys and labels for identifier comparisons."""
    return normalize_for_match(value)


def normalize_whitespace(value: str) -> str:
    """Collapse whitespace and lowercase text for same-paragraph checks."""
    return re.sub(r"\s+", " ", value.strip().lower()).strip()
