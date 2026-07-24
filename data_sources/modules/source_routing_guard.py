"""
Source routing guard.

Validates that Simpro article sidecars identify which inputs came from the
Simpro Brand Context vault and which came from repo-local context files. The
guard keeps vault-first facts from being silently replaced by repo mirrors.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


DECISION_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Source Routing Decision:?\s*$",
    re.IGNORECASE,
)
NEXT_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:Vault Context Read Path|Vault Brand Language Alignment|"
    r"PAA/FAQ Provenance|Metric Proof Pack|Source Map|Customer Proof Slate|"
    r"Selected Customer Proof Mining|Customer Proof Pack|Customer Proof Selection Decision|"
    r"E-E-A-T Proof Map|FAQ Proof Map|Review Story Selection|Review Site Theme Selection|"
    r"Structured data plan|Early Artifact Plan|Concrete Answer Check|"
    r"Competitive Shortlist Decision|Named Feature/Add-On Link Check|Hindsight Boundary)\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
SIMPRO_ARTICLE_RE = re.compile(r"\bSimpro\b|https?://(?:www\.)?simprogroup\.com/", re.IGNORECASE)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)

REQUIRED_FIELDS = (
    "article title",
    "vault-sourced data types",
    "repo-context-sourced data types",
    "vault routes checked",
    "repo context files checked",
    "fallback context use",
    "conflicts found",
    "status",
)
REQUIRED_CORE_ROUTES = (
    "AGENTS.md",
    "wiki/cache/hot.md",
    "wiki/Brand Graph Index.md",
)
FALLBACK_BLOCKER_TERMS = (
    "vault unavailable",
    "vault-unavailable",
    "vault blocker",
    "vault unavailable blocker",
    "vault inaccessible",
    "vault missing",
)
VAULT_FIRST_PATTERNS = (
    r"\bbrand voice\b",
    r"\baudience\b",
    r"\bicp\b",
    r"\bmessage pillars?\b",
    r"\btone\b",
    r"\bproduct\b",
    r"\bfeatures?\b",
    r"\badd-?ons?\b",
    r"\bsolutions?\b",
    r"\bindustr(?:y|ies)\b",
    r"\blightning\b",
    r"\bcompetitor\b",
    r"\bhindsight\b",
    r"\bbattlecard\b",
    r"\bcustomer proof\b",
    r"\bquotes?\b",
    r"\bmetrics?\b",
    r"\breview stories\b",
    r"\bapproval status\b",
    r"\bpublic factual\b",
    r"\bstatistical claims?\b",
)


def check_content(content: str, *, proof_content: Optional[str] = None) -> List[Finding]:
    """Return findings for missing or invalid source-routing decisions."""
    if not _is_triggered(content):
        return []

    block = _extract_decision_block(proof_content or "")
    if block is None:
        return [
            _finding(
                "source_routing_decision_missing",
                1,
                "Simpro article copy has no Source Routing Decision in the validation sidecar.",
                (
                    "Add Source Routing Decision to the validation sidecar with vault-sourced data types, "
                    "repo-context-sourced data types, routes checked, fallback use, conflicts, and Status: aligned."
                ),
            )
        ]

    findings: List[Finding] = []
    fields = block["fields"]
    for required_field in REQUIRED_FIELDS:
        if not fields.get(required_field):
            findings.append(
                _finding(
                    "source_routing_required_field_missing",
                    block["line"],
                    f"Source Routing Decision is missing required field: {required_field}.",
                    "Add the complete Source Routing Decision block to the validation sidecar.",
                    match=required_field,
                )
            )

    routes = fields.get("vault routes checked", "")
    for route in REQUIRED_CORE_ROUTES:
        if route.lower() not in routes.lower():
            findings.append(
                _finding(
                    "source_routing_core_route_missing",
                    block["line"],
                    f"Source Routing Decision is missing required vault route: {route}.",
                    "Document the vault read path used for Simpro source routing.",
                    match=route,
                )
            )

    status = fields.get("status", "").strip().lower()
    if status and status != "aligned":
        findings.append(
            _finding(
                "source_routing_status_not_aligned",
                block["line"],
                "Source Routing Decision status is not aligned.",
                "Set Status: aligned only after vault and repo context routing are reconciled.",
                match=fields.get("status", ""),
            )
        )

    fallback = fields.get("fallback context use", "").strip().lower()
    fallback_has_blocker = _has_fallback_blocker(fallback)
    if fallback and fallback != "none" and not fallback_has_blocker:
        findings.append(
            _finding(
                "source_routing_fallback_without_blocker",
                block["line"],
                "Repo-local fallback context was used without a vault-unavailable blocker.",
                "Use the vault first, or document the vault-unavailable blocker alongside the fallback context used.",
                match=fields.get("fallback context use", ""),
            )
        )

    repo_data_types = fields.get("repo-context-sourced data types", "")
    if _contains_vault_first_data(repo_data_types) and not fallback_has_blocker:
        findings.append(
            _finding(
                "source_routing_repo_primary_vault_first_data",
                block["line"],
                "Repo context is listed as the source for data that must be vault-first.",
                (
                    "Move brand, product, feature, competitor, customer-proof, metric, review-story, "
                    "approval, and public-factual claim routing to Vault-sourced data types, or document a vault blocker."
                ),
                match=repo_data_types,
            )
        )

    return sorted(findings, key=lambda finding: (finding["severity"] != "error", finding["line"], finding["rule_id"]))


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a public article file plus optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(file_path.read_text(encoding="utf-8"), proof_content=proof_content)


def _is_triggered(content: str) -> bool:
    public_content = FENCED_CODE_RE.sub("", content)
    return bool(SIMPRO_ARTICLE_RE.search(public_content))


def _contains_vault_first_data(value: str) -> bool:
    for pattern in VAULT_FIRST_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return True
    return False


def _has_fallback_blocker(value: str) -> bool:
    return any(term in value for term in FALLBACK_BLOCKER_TERMS)


def _extract_decision_block(content: str) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not DECISION_HEADING_RE.match(line.strip()):
            continue
        fields: Dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if NEXT_HEADING_RE.match(stripped):
                break
            if not stripped and fields:
                break
            if not stripped:
                continue
            match = BULLET_FIELD_RE.match(block_line)
            if match:
                fields[_normalize_key(match.group("key"))] = match.group("value").strip()
                continue
            if fields and re.match(r"^\s*(?:#{1,6}\s+)?[A-Za-z].*$", stripped):
                break
        return {"line": index + 1, "fields": fields}
    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    match: str = "",
) -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        match=match,
        message=message,
        suggestion=suggestion,
    )


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check source routing between the vault and repo context.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument("--proof-sidecar", help="Optional validation sidecar containing Source Routing Decision.")
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
