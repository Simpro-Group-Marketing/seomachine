"""
Vault brand-language guard.

Validates that Simpro product, feature, add-on, solution, and vertical copy has
a validation-sidecar record showing the writer used the Obsidian vault's current
brand/product language before publish readiness.
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


ALIGNMENT_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Vault Brand Language Alignment:?\s*$",
    re.IGNORECASE,
)
NEXT_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Pack|"
    r"Customer Proof Selection Decision|E-E-A-T Proof Map|FAQ Proof Map|"
    r"Review Story Selection|Review Site Theme Selection|Structured data plan|"
    r"Early Artifact Plan|Concrete Answer Check|Competitive Shortlist Decision|"
    r"Named Feature/Add-On Link Check)\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")

PRODUCT_URL_RE = re.compile(
    r"https?://(?:www\.)?simprogroup\.com/(?:features|solutions|industries)/[^\s),]*",
    re.IGNORECASE,
)
SIMPRO_PRODUCT_CONTEXT_RE = re.compile(
    r"\bSimpro\b.{0,90}\b(?:platform|software|feature|features|add-?on|add-?ons|"
    r"solution|solutions|industr(?:y|ies)|quoting|scheduling|invoicing|payments|"
    r"job costing|recurring maintenance|field service management)\b",
    re.IGNORECASE | re.DOTALL,
)
PRODUCT_TERM_CONTEXT_RE = re.compile(
    r"\b(?:Simpro field service management software|Simpro job management software|"
    r"Simpro platform|Simpro software)\b",
    re.IGNORECASE,
)
SOLUTION_CONTEXT_RE = re.compile(
    r"\b(?:solution|solutions|industr(?:y|ies)|vertical|verticals)\b",
    re.IGNORECASE,
)
FEATURE_SOURCE_ROUTE_RE = re.compile(
    r"\bwiki/features/source-docs/[\w./-]+|"
    r"\braw/(?:drive|source-intake|imported-content|extracted)/[\w./-]+",
    re.IGNORECASE,
)

NAMED_FEATURES = (
    "AI Mobile Work Notes",
    "Data Feed",
    "Delight",
    "Digital Forms",
    "Fast Cash",
    "FieldReady",
    "GPS Time Tracking",
    "JobBrief",
    "JobReady",
    "JobScribe",
    "JustAsk",
    "Maintenance Planner",
    "Multi-Company",
    "Payments",
    "Private Cloud",
    "Simpro Payments",
    "Simtrac",
    "SMS Messaging",
    "Takeoffs",
    "Two-Way Messaging",
)

REQUIRED_FIELDS = (
    "article title",
    "product/solution language scope",
    "vault routes checked",
    "product/feature language applied",
    "solution/industry language applied",
    "fallback context use",
    "claims requiring source verification",
    "status",
)
REQUIRED_CORE_ROUTES = (
    "AGENTS.md",
    "wiki/cache/hot.md",
    "wiki/Brand Graph Index.md",
    "wiki/messaging/Simpro Core Messaging Repository.md",
    "wiki/messaging/Message House.md",
    "wiki/messaging/Core Value Pillars.md",
    "wiki/product/Product Positioning.md",
    "wiki/features/Feature Library.md",
)
VALID_SCOPES = {"product/feature", "solution/industry", "mixed"}
FALLBACK_BLOCKER_TERMS = (
    "vault unavailable",
    "vault-unavailable",
    "vault blocker",
    "vault unavailable blocker",
)


def check_content(content: str, *, proof_content: Optional[str] = None) -> List[Finding]:
    """Return findings for missing or incomplete vault brand-language alignment."""
    if not _is_triggered(content):
        return []

    block = _extract_alignment_block(proof_content or "")
    if block is None:
        return [
            _finding(
                "vault_brand_language_alignment_missing",
                1,
                "Simpro product, feature, add-on, solution, or industry language appears without a Vault Brand Language Alignment block.",
                (
                    "Add Vault Brand Language Alignment to the validation sidecar with the vault routes checked, "
                    "language applied, fallback context use, source-verification boundary, and Status: aligned."
                ),
            )
        ]

    findings: List[Finding] = []
    fields = block["fields"]
    for required_field in REQUIRED_FIELDS:
        if not fields.get(required_field):
            findings.append(
                _finding(
                    "vault_brand_language_required_field_missing",
                    block["line"],
                    f"Vault Brand Language Alignment is missing required field: {required_field}.",
                    "Add the complete Vault Brand Language Alignment block to the validation sidecar.",
                    match=required_field,
                )
            )

    routes = fields.get("vault routes checked", "")
    for route in REQUIRED_CORE_ROUTES:
        if route.lower() not in routes.lower():
            findings.append(
                _finding(
                    "vault_brand_language_core_route_missing",
                    block["line"],
                    f"Vault Brand Language Alignment is missing required vault route: {route}.",
                    "Document the full vault read path used before drafting product or solution language.",
                    match=route,
                )
            )

    scope = fields.get("product/solution language scope", "").strip().lower()
    if scope and scope not in VALID_SCOPES:
        findings.append(
            _finding(
                "vault_brand_language_invalid_scope",
                block["line"],
                "Vault Brand Language Alignment has an invalid product/solution language scope.",
                "Use product/feature, solution/industry, or mixed.",
                match=fields.get("product/solution language scope", ""),
            )
        )

    status = fields.get("status", "").strip().lower()
    if status and status != "aligned":
        findings.append(
            _finding(
                "vault_brand_language_status_not_aligned",
                block["line"],
                "Vault Brand Language Alignment status is not aligned.",
                "Set Status: aligned only after vault product language has been checked and applied.",
                match=fields.get("status", ""),
            )
        )

    fallback = fields.get("fallback context use", "").strip().lower()
    if fallback and fallback != "none" and not any(term in fallback for term in FALLBACK_BLOCKER_TERMS):
        findings.append(
            _finding(
                "vault_brand_language_fallback_without_blocker",
                block["line"],
                "Repo-local fallback context was used without documenting a vault-unavailable blocker.",
                "Use the vault first, or document the vault-unavailable blocker alongside the fallback context used.",
                match=fields.get("fallback context use", ""),
            )
        )

    if _has_named_feature(content) and not FEATURE_SOURCE_ROUTE_RE.search(routes):
        findings.append(
            _finding(
                "vault_brand_language_feature_source_route_missing",
                block["line"],
                "Named Simpro feature or add-on language appears without a specific feature source-doc or raw route.",
                "Add a wiki/features/source-docs/ route or a specific raw source route for the named feature/add-on.",
            )
        )

    if _requires_vertical_route(content, scope) and "wiki/verticals/Vertical Profile Library.md".lower() not in routes.lower():
        findings.append(
            _finding(
                "vault_brand_language_vertical_route_missing",
                block["line"],
                "Solution or industry language appears without the Vertical Profile Library route.",
                "Add wiki/verticals/Vertical Profile Library.md and the relevant vertical profile/source route when applicable.",
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
    public_content = _blank_fenced_code(content)
    return bool(
        PRODUCT_URL_RE.search(public_content)
        or SIMPRO_PRODUCT_CONTEXT_RE.search(public_content)
        or PRODUCT_TERM_CONTEXT_RE.search(public_content)
        or _has_named_feature(public_content)
    )


def _has_named_feature(content: str) -> bool:
    public_content = _blank_fenced_code(content)
    for feature in NAMED_FEATURES:
        if re.search(rf"\b{re.escape(feature)}\b", public_content, re.IGNORECASE):
            return True
    return False


def _requires_vertical_route(content: str, scope: str) -> bool:
    if scope in {"solution/industry", "mixed"}:
        return True
    return bool(PRODUCT_URL_RE.search(content) and SOLUTION_CONTEXT_RE.search(content))


def _extract_alignment_block(content: str) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not ALIGNMENT_HEADING_RE.match(line.strip()):
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


def _blank_fenced_code(content: str) -> str:
    lines = content.splitlines()
    blanked: List[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            blanked.append("")
            continue
        blanked.append("" if in_fence else line)
    return "\n".join(blanked)


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
    parser = argparse.ArgumentParser(description="Check vault product-language alignment.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument("--proof-sidecar", help="Optional validation sidecar containing Vault Brand Language Alignment.")
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
