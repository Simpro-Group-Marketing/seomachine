"""
Metric Proof Pack Guard

Deterministic guardrail for making proof-sensitive articles research useful,
source-backed metrics before drafting. Numeric claim guards still own claims
that appear in public copy; this guard owns the presence and quality of the
metric proof pack itself.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
    from .source_support_guard import fetch_source_text
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content
    from source_support_guard import fetch_source_text


Fetcher = Callable[[str], str]

METRIC_PACK_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?Metric Proof Pack\s*$", re.IGNORECASE)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")

METRIC_REQUIRED_TRIGGERS = (
    "best",
    "software",
    "comparison",
    "pricing",
    "cost",
    "roi",
    "kpi",
    "profit",
    "margin",
    "guide",
    " vs ",
    "versus",
)


@dataclass
class ApprovedMetric:
    claim: str
    url: str
    evidence: str
    status: str
    use: str
    line: int


@dataclass
class MetricProofPack:
    line: int
    requirement: str
    reason: str
    search_log: str
    approved_metrics_none: bool
    approved_metrics: List[ApprovedMetric]


def check_content(
    content: str,
    source_path: Optional[str] = None,
    fetcher: Optional[Fetcher] = None,
    proof_content: Optional[str] = None,
) -> List[Finding]:
    """Return Metric Proof Pack findings for markdown content."""
    metric_required = _is_metric_required(content)
    proof_source = compose_with_sidecar(content, proof_content)
    pack = _extract_metric_proof_pack(proof_source)

    if pack is None:
        if metric_required:
            return [
                _finding(
                    "metric_proof_pack_missing",
                    1,
                    "Metric-required article has no Metric Proof Pack.",
                    (
                        "Add a Metric Proof Pack with Metric requirement, Search log, "
                        "and at least one Approved metric row before writing or publishing."
                    ),
                )
            ]
        return []

    if _is_not_applicable(pack.requirement):
        findings = []
        if not pack.reason:
            findings.append(
                _finding(
                    "metric_not_applicable_reason_missing",
                    pack.line,
                    "Metric Proof Pack marks metrics not applicable but gives no reason.",
                    "Add a Reason explaining why metrics are not useful for this article.",
                )
            )
        if not pack.search_log:
            findings.append(
                _finding(
                    "metric_search_log_missing",
                    pack.line,
                    "Metric Proof Pack marks metrics not applicable but gives no search log.",
                    "Add a Search log entry documenting the editorial classification.",
                )
            )
        return findings

    findings: List[Finding] = []

    if not pack.search_log:
        findings.append(
            _finding(
                "metric_search_log_missing",
                pack.line,
                "Metric Proof Pack does not include a Search log.",
                "Document the public pages or local artifacts checked for usable metrics.",
            )
        )

    if not pack.approved_metrics:
        if metric_required or pack.approved_metrics_none:
            findings.append(
                _finding(
                    "metric_proof_pack_no_approved_metrics",
                    pack.line,
                    "Metric Proof Pack has no approved metrics.",
                    (
                        "Add at least one source-backed Approved metric row, or mark "
                        "Metric requirement: not applicable with a documented reason."
                    ),
                )
            )
        return findings

    for metric in pack.approved_metrics:
        findings.extend(_validate_metric(metric, source_path, fetcher))

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a Markdown file for Metric Proof Pack requirements."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(content, source_path=path, proof_content=proof_content)


def _is_metric_required(content: str) -> bool:
    frontmatter = _extract_frontmatter(content)
    h1_match = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    h1 = h1_match.group(1) if h1_match else ""
    text = " ".join(
        [
            frontmatter.get("title", ""),
            frontmatter.get("meta_title", ""),
            frontmatter.get("primary_keyword", ""),
            frontmatter.get("secondary_keywords", ""),
            h1,
        ]
    ).lower()
    padded = f" {text} "
    return any(trigger in padded for trigger in METRIC_REQUIRED_TRIGGERS)


def _extract_frontmatter(content: str) -> Dict[str, str]:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*", content, re.DOTALL)
    if not match:
        return {}

    values = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower().replace("-", "_").replace(" ", "_")
        values[normalized_key] = value.strip().strip('"').strip("'")
    return values


def _extract_metric_proof_pack(content: str) -> Optional[MetricProofPack]:
    lines = content.splitlines()

    for index, line in enumerate(lines):
        if not METRIC_PACK_HEADING_RE.match(line.strip()):
            continue

        requirement = ""
        reason = ""
        search_log = ""
        approved_metrics_none = False
        approved_metrics: List[ApprovedMetric] = []

        for offset, block_line in enumerate(lines[index + 1 :], start=index + 2):
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if stripped and not stripped.startswith(("-", "*", "+")):
                break
            if not stripped:
                continue

            field_match = BULLET_FIELD_RE.match(block_line)
            if not field_match:
                continue

            key = field_match.group("key").strip().lower()
            value = field_match.group("value").strip()

            if key == "metric requirement":
                requirement = value
            elif key == "reason":
                reason = value
            elif key == "search log":
                search_log = value
            elif key == "approved metrics":
                approved_metrics_none = value.lower() == "none used"
            elif key == "approved metric":
                approved_metrics.append(_parse_approved_metric(value, offset))

        return MetricProofPack(
            line=index + 1,
            requirement=requirement,
            reason=reason,
            search_log=search_log,
            approved_metrics_none=approved_metrics_none,
            approved_metrics=approved_metrics,
        )

    return None


def _parse_approved_metric(value: str, line: int) -> ApprovedMetric:
    parts = [part.strip() for part in value.split("|")]
    claim = parts[0] if parts else ""
    fields: Dict[str, str] = {}
    for part in parts[1:]:
        if ":" not in part:
            continue
        key, field_value = part.split(":", 1)
        fields[key.strip().lower()] = field_value.strip()

    return ApprovedMetric(
        claim=claim,
        url=fields.get("url", "") or fields.get("proof artifact", ""),
        evidence=_strip_wrapping_quotes(fields.get("evidence", "")),
        status=fields.get("status", ""),
        use=fields.get("use", ""),
        line=line,
    )


def _validate_metric(
    metric: ApprovedMetric,
    source_path: Optional[str],
    fetcher: Optional[Fetcher],
) -> List[Finding]:
    findings: List[Finding] = []
    if not metric.claim:
        findings.append(
            _finding(
                "metric_claim_missing",
                metric.line,
                "Approved metric row does not include a metric claim.",
                "Put the source-backed metric claim immediately after Approved metric:",
            )
        )
    if not metric.url:
        findings.append(
            _finding(
                "metric_url_missing",
                metric.line,
                "Approved metric row does not include a URL or proof artifact.",
                "Add URL: [public URL or local proof artifact path].",
            )
        )
    if not metric.evidence:
        findings.append(
            _finding(
                "metric_evidence_missing",
                metric.line,
                "Approved metric row does not include source-visible Evidence.",
                "Add Evidence with the exact source-visible snippet that supports the metric.",
            )
        )
    if not metric.status or metric.status.lower() != "approved":
        findings.append(
            _finding(
                "metric_status_missing",
                metric.line,
                "Approved metric row is not marked Status: approved.",
                "Set Status: approved only after verifying the evidence against the source.",
            )
        )
    if not metric.use:
        findings.append(
            _finding(
                "metric_use_missing",
                metric.line,
                "Approved metric row does not include intended Use.",
                "Add Use: [where or how this metric can be used in the article].",
            )
        )

    if findings or not metric.evidence or not metric.url:
        return findings

    source_text, source_error = _read_source(metric.url, source_path, fetcher)
    if source_error:
        findings.append(
            _finding(
                "metric_source_unavailable",
                metric.line,
                f"Metric proof source could not be read: {metric.url}",
                "Use a readable public URL or save a local proof artifact with the source text.",
                match=source_error,
            )
        )
        return findings

    if _normalize_for_match(metric.evidence) not in _normalize_for_match(source_text):
        findings.append(
            _finding(
                "metric_evidence_not_found",
                metric.line,
                "Metric Evidence was not found in the proof source.",
                "Replace the metric, update Evidence to an exact visible snippet, or remove the row.",
                match=metric.evidence,
            )
        )

    return findings


def _read_source(
    url_or_path: str,
    source_path: Optional[str],
    fetcher: Optional[Fetcher],
) -> tuple[str, str]:
    if url_or_path.startswith(("http://", "https://")):
        if fetcher is not None:
            try:
                return fetcher(url_or_path), ""
            except Exception as exc:
                return "", str(exc)
        try:
            return fetch_source_text(url_or_path), ""
        except Exception as exc:
            return "", str(exc)

    path = _resolve_local_path(url_or_path, source_path)
    if path is None or not path.exists():
        return "", f"file not found: {url_or_path}"
    return path.read_text(encoding="utf-8"), ""


def _resolve_local_path(raw_path: str, source_path: Optional[str]) -> Optional[Path]:
    path = Path(raw_path)
    if path.is_absolute():
        return path

    candidates = [Path.cwd() / path]
    if source_path:
        source = Path(source_path).resolve()
        candidates.append(source.parent / path)
        candidates.append(source.parent.parent / path)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else None


def _is_not_applicable(requirement: str) -> bool:
    return requirement.strip().lower() == "not applicable"


def _strip_wrapping_quotes(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": "error",
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if match is not None:
        finding["match"] = match
    return finding


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check Metric Proof Pack completeness.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Metric Proof Pack rows.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
