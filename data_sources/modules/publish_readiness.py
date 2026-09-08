"""Publish readiness runner.

Runs the existing blog proof and quality gates in one deterministic order so
agents do not have to copy the full command stack by hand.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:
    from . import (
        ai_copy_linter,
        answer_withholding_guard,
        blog_strategy_guard,
        customer_proof_diversity_guard,
        context_binding_guard,
        early_artifact_guard,
        faq_answer_quality_guard,
        fred_authority_guard,
        faq_proof_guard,
        metric_proof_pack_guard,
        named_feature_status_guard,
        numeric_claim_source_guard,
        paa_provenance_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        schema_handoff_guard,
        source_quality_guard,
        source_support_guard,
        source_routing_guard,
        vault_brand_language_guard,
    )
    from .content_scorer import ContentScorer
    from .guard_common import should_fail, summarize_findings
    from .url_validator import UrlValidationSummary, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_strategy_guard
    import customer_proof_diversity_guard
    import context_binding_guard
    import early_artifact_guard
    import faq_answer_quality_guard
    import fred_authority_guard
    import faq_proof_guard
    import metric_proof_pack_guard
    import named_feature_status_guard
    import numeric_claim_source_guard
    import paa_provenance_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import schema_handoff_guard
    import source_quality_guard
    import source_support_guard
    import source_routing_guard
    import vault_brand_language_guard
    from content_scorer import ContentScorer
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, validate_file_urls


GateResult = Dict[str, Any]
ReadinessResult = Dict[str, Any]


ARTICLE_GATES = (
    (
        "metric_proof_pack",
        "Metric Proof Pack",
        metric_proof_pack_guard,
    ),
    (
        "numeric_claim_source",
        "Numeric Claim Source",
        numeric_claim_source_guard,
    ),
    (
        "faq_answer_quality",
        "FAQ Answer Quality",
        faq_answer_quality_guard,
    ),
    (
        "faq_proof",
        "FAQ Proof",
        faq_proof_guard,
    ),
    (
        "paa_provenance",
        "PAA Provenance",
        paa_provenance_guard,
    ),
    (
        "source_support",
        "Source Support",
        source_support_guard,
    ),
    (
        "source_quality",
        "Source Quality and Lifecycle",
        source_quality_guard,
    ),
    (
        "customer_proof_diversity",
        "Customer Proof Diversity",
        customer_proof_diversity_guard,
    ),
    (
        "review_story_identity",
        "Review Story Identity",
        review_story_identity_guard,
    ),
    (
        "early_artifact",
        "Early Artifact",
        early_artifact_guard,
    ),
    (
        "answer_withholding",
        "Answer Withholding",
        answer_withholding_guard,
    ),
    (
        "vault_brand_language",
        "Vault Brand Language",
        vault_brand_language_guard,
    ),
    (
        "named_feature_status",
        "Named Feature Status",
        named_feature_status_guard,
    ),
    (
        "source_routing",
        "Source Routing",
        source_routing_guard,
    ),
    (
        "blog_strategy",
        "Blog Strategy",
        blog_strategy_guard,
    ),
    (
        "schema_handoff",
        "Schema Handoff",
        schema_handoff_guard,
    ),
    (
        "fred_authority",
        "Fred Voccola Authority",
        fred_authority_guard,
    ),
)

BLOG_ONLY_GATES = {"source_quality", "blog_strategy", "schema_handoff"}


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    vault_root: str | Path | None = None,
    artifact_kind: str = "blog",
    ai_profile: str = "simpro-web",
) -> ReadinessResult:
    """Run the full publish-readiness stack and return structured results."""
    article_path = Path(file_path)
    proof_sidecar_path = str(proof_sidecar) if proof_sidecar is not None else None
    context_request_path = str(context_request) if context_request is not None else None
    context_pack_path = str(context_pack) if context_pack is not None else None
    context_receipt_path = str(context_receipt) if context_receipt is not None else None
    gates: List[GateResult] = []

    article_content = article_path.read_text(encoding="utf-8")
    normalized_artifact_kind, artifact_rule, artifact_error = _resolve_artifact_kind(
        article_path, article_content, artifact_kind
    )
    if artifact_rule:
        context_gate = _gate_from_findings(
            "context_binding",
            "Context Binding",
            [{
                "rule_id": artifact_rule,
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": artifact_error,
                "suggestion": "Use the artifact type derived from the article, then regenerate context artifacts.",
            }],
        )
        gates.append(context_gate)
        return {
            "file": str(article_path), "artifact_kind": normalized_artifact_kind,
            "proof_sidecar": proof_sidecar_path, "context_request": context_request_path,
            "context_pack": context_pack_path, "context_receipt": context_receipt_path,
            "passed": False, "gates": gates, "score": None, "aeo_geo": {},
            "priority_fixes": [{"dimension": "context", "issue": blocker} for blocker in context_gate.get("blockers", [])],
        }
    if normalized_artifact_kind == "blog":
        context_gate = _gate_from_findings(
                "context_binding",
                "Context Binding",
                context_binding_guard.check_file(
                    str(article_path),
                    fail_on="error",
                    proof_sidecar=proof_sidecar_path,
                    context_request=context_request_path,
                    context_pack=context_pack_path,
                    context_receipt=context_receipt_path,
                    vault_root=vault_root,
                ),
        )
        gates.append(context_gate)
        if not context_gate["passed"]:
            return {
                "file": str(article_path),
                "artifact_kind": normalized_artifact_kind,
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "passed": False,
                "gates": gates,
                "score": None,
                "aeo_geo": {},
                "priority_fixes": [
                    {"dimension": "context", "issue": blocker}
                    for blocker in context_gate.get("blockers", [])
                ],
            }

    gates.append(
        _gate_from_findings(
            "public_artifact",
            "Public Artifact",
            public_artifact_guard.check_file(str(article_path), fail_on="error"),
        )
    )

    ai_findings = ai_copy_linter.lint_file(
        str(article_path),
        profile=ai_profile,
        fail_on="error",
    )
    gates.append(
        _gate_from_findings(
            "ai_copy_linter",
            "AI Copy Linter",
            ai_findings,
        )
    )

    url_summary = validate_file_urls(article_path)
    gates.append(_gate_from_url_summary(url_summary))

    gates.append(
        _gate_from_findings(
            "public_research_links",
            "Public Research Links",
            public_research_link_guard.check_file(
                str(article_path),
                fail_on="error",
                proof_sidecar=proof_sidecar_path,
                url_summary=url_summary,
            ),
        )
    )

    for name, label, guard_module in ARTICLE_GATES:
        if normalized_artifact_kind != "blog" and name in BLOG_ONLY_GATES:
            continue
        guard_kwargs: Dict[str, Any] = (
            {} if name == "blog_strategy" else {"fail_on": "error"}
        )
        guard_kwargs["proof_sidecar"] = proof_sidecar_path
        if name in {"named_feature_status", "fred_authority", "customer_proof_diversity", "review_story_identity"}:
            guard_kwargs.update(
                {
                    "context_pack": context_pack_path,
                    "context_receipt": context_receipt_path,
                }
            )
        if name == "fred_authority":
            guard_kwargs["vault_root"] = vault_root
        if name == "customer_proof_diversity":
            guard_kwargs["vault_root"] = vault_root
        if name == "blog_strategy":
            guard_kwargs.update(
                {
                    "context_request": context_request_path,
                    "context_pack": context_pack_path,
                    "context_receipt": context_receipt_path,
                    "url_summary": url_summary,
                    "require_strategy": normalized_artifact_kind == "blog",
                }
            )
        findings = guard_module.check_file(str(article_path), **guard_kwargs)
        gates.append(_gate_from_findings(name, label, findings))

    scorer_result = _score_content(article_path, proof_sidecar_path)
    gates.append(_gate_from_score(scorer_result))

    passed = all(gate["passed"] for gate in gates)
    return {
        "file": str(article_path),
        "artifact_kind": normalized_artifact_kind,
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "passed": passed,
        "gates": gates,
        "score": _content_score(scorer_result),
        "aeo_geo": scorer_result.get("aeo_geo", {}),
        "priority_fixes": scorer_result.get("priority_fixes", []),
    }


def format_text_report(result: ReadinessResult) -> str:
    """Return a human-readable publish-readiness report."""
    lines = [
        "PUBLISH READINESS",
        "=" * 50,
        f"File: {result['file']}",
        f"Artifact kind: {result.get('artifact_kind', 'blog')}",
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
        f"Context request: {result.get('context_request') or 'not required/provided'}",
        f"Context pack: {result.get('context_pack') or 'not required/provided'}",
        f"Context receipt: {result.get('context_receipt') or 'not required/provided'}",
        f"Overall: {'PASS' if result['passed'] else 'FAIL'}",
        "",
        "Gates:",
    ]

    for gate in result["gates"]:
        status = "PASS" if gate["passed"] else "FAIL"
        lines.append(
            f"  {status:4} {gate['label']:<28} "
            f"errors={gate['errors']} warnings={gate['warnings']}"
        )
        for blocker in gate.get("blockers", [])[:3]:
            lines.append(f"       - {blocker}")

    lines.extend(
        [
            "",
            f"Content score: {result.get('score', 'n/a')}",
            f"AEO/GEO score: {result.get('aeo_geo', {}).get('score', 'n/a')}",
        ]
    )

    priority_fixes = result.get("priority_fixes", [])
    if priority_fixes:
        lines.append("")
        lines.append("Priority fixes:")
        for index, fix in enumerate(priority_fixes[:5], start=1):
            issue = fix.get("issue", "Unknown issue")
            dimension = fix.get("dimension", "unknown")
            lines.append(f"  {index}. [{dimension}] {issue}")

    lines.append("=" * 50)
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the publish-readiness gate stack.")
    parser.add_argument("file_path", help="Path to the draft or rewrite markdown file.")
    parser.add_argument(
        "--proof-sidecar",
        help="Validation sidecar containing proof maps and proof packs.",
    )
    parser.add_argument(
        "--profile",
        default="simpro-web",
        help="AI copy linter profile. Defaults to simpro-web.",
    )
    parser.add_argument("--context-request", help="Current Simpro context request JSON.")
    parser.add_argument("--context-pack", help="Current Simpro v2 context pack JSON.")
    parser.add_argument("--context-receipt", help="Current Simpro context receipt JSON.")
    parser.add_argument("--vault-root", help="Configured Simpro vault root override.")
    parser.add_argument(
        "--artifact-kind",
        choices=["blog", "landing_page"],
        default="blog",
        help="Artifact class. Context enforcement is blog-only in this rollout.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args(argv)

    result = run_publish_readiness(
        args.file_path,
        proof_sidecar=args.proof_sidecar,
        context_request=args.context_request,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
        vault_root=args.vault_root,
        artifact_kind=args.artifact_kind,
        ai_profile=args.profile,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_text_report(result))
    return 0 if result["passed"] else 1


def _gate_from_findings(
    name: str,
    label: str,
    findings: List[Dict[str, Any]],
) -> GateResult:
    summary = summarize_findings(findings)
    passed = not should_fail(findings, fail_on="error")
    return {
        "name": name,
        "label": label,
        "passed": passed,
        "errors": summary["error"],
        "warnings": summary["warning"],
        "findings": findings,
        "blockers": _finding_lines(findings) if not passed else [],
    }


def _gate_from_url_summary(summary: UrlValidationSummary) -> GateResult:
    blockers = summary.blockers
    return {
        "name": "url_validator",
        "label": "URL Validator",
        "passed": summary.passed,
        "errors": len(blockers),
        "warnings": 0,
        "findings": [
            {
                "rule_id": "url_unresolved",
                "severity": "error",
                "line": result.line,
                "url": result.url,
                "status": result.status,
                "status_code": result.status_code,
                "reason": result.reason,
                "anchor": result.anchor,
            }
            for result in blockers
        ],
        "blockers": [
            _url_blocker_line(result)
            for result in blockers[:3]
        ],
    }


def _gate_from_score(score_result: Dict[str, Any]) -> GateResult:
    passed = bool(score_result.get("passed", False))
    priority_fixes = score_result.get("priority_fixes", [])
    return {
        "name": "content_scorer",
        "label": "Content Scorer",
        "passed": passed,
        "errors": 0 if passed else 1,
        "warnings": len(priority_fixes) if passed else 0,
        "findings": [],
        "blockers": _priority_fix_lines(priority_fixes) if not passed else [],
    }


def _score_content(article_path: Path, proof_sidecar: Optional[str]) -> Dict[str, Any]:
    content = article_path.read_text(encoding="utf-8")
    scorer = ContentScorer()
    return scorer.score(
        content,
        validate_urls=True,
        validate_source_support=True,
        source_path=str(article_path),
        proof_sidecar=proof_sidecar,
    )


def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _finding_lines(findings: List[Dict[str, Any]]) -> List[str]:
    blockers = [
        finding
        for finding in findings
        if finding.get("severity") == "error"
    ]
    if not blockers:
        blockers = findings
    lines = []
    for finding in blockers[:3]:
        line = finding.get("line", "?")
        rule = finding.get("rule_id", "finding")
        message = finding.get("message", "")
        lines.append(f"line {line}: {rule} - {message}".rstrip(" -"))
    return lines


def _url_blocker_line(result: Any) -> str:
    location = f"line {result.line}: " if result.line else ""
    anchor = f" [{result.anchor}]" if result.anchor else ""
    code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
    line = f"{location}{result.url}{anchor} ({result.status}: {code})"
    if result.status == "manual_review":
        line += (
            " Replace this source with an equivalent resolved public source "
            "or remove the supported claim. Do not remove the citation without "
            "replacing it with a resolved source supporting the same claim."
        )
    return line


def _priority_fix_lines(priority_fixes: List[Dict[str, Any]]) -> List[str]:
    lines = []
    for fix in priority_fixes[:3]:
        dimension = fix.get("dimension", "unknown")
        issue = fix.get("issue", "Unknown issue")
        lines.append(f"{dimension}: {issue}")
    return lines


def _artifact_kind(value: object) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "article": "blog",
        "post": "blog",
        "posts": "blog",
        "page": "landing_page",
        "pages": "landing_page",
        "landing": "landing_page",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"blog", "landing_page"}:
        return None
    return normalized


def _resolve_artifact_kind(
    path: Path,
    content: str,
    requested_value: object,
) -> tuple[str, str | None, str | None]:
    """Resolve kind from symmetric positive evidence, defaulting ambiguity to blog."""
    try:
        from .artifact_detection import extract_frontmatter, extract_frontmatter_values
    except ImportError:  # pragma: no cover - direct script execution.
        from artifact_detection import extract_frontmatter, extract_frontmatter_values

    frontmatter = extract_frontmatter(content)
    frontmatter_values = extract_frontmatter_values(content)
    evidence: list[tuple[str, str]] = []
    requested = _artifact_kind(requested_value)
    if requested is None:
        return (
            "blog",
            "context_artifact_kind_invalid",
            f"Caller artifact kind is unsupported: {requested_value!s}.",
        )
    for field in ("artifact_type", "artifact_kind"):
        declared_values = frontmatter_values.get(field, [])
        declared_kinds: list[str] = []
        for declared_value in declared_values:
            kind = _artifact_kind(declared_value)
            if kind is None:
                return (
                    "blog",
                    "context_artifact_kind_invalid",
                    f"Article {field} is unsupported: {declared_value}.",
                )
            declared_kinds.append(kind)
        if len(set(declared_kinds)) > 1:
            return (
                "blog",
                "context_artifact_kind_conflict",
                f"Article {field} frontmatter contains conflicting duplicate values.",
            )
        declared = frontmatter.get(field)
        if not declared:
            continue
        kind = _artifact_kind(declared)
        if kind is None:
            return (
                "blog",
                "context_artifact_kind_invalid",
                f"Article {field} is unsupported: {declared}.",
            )
        evidence.append((kind, f"article {field} frontmatter"))
    workflow = frontmatter.get("workflow")
    if workflow:
        normalized_workflow = str(workflow).strip().lower().replace("-", "_")
        if normalized_workflow in {
            "article", "blog", "post", "posts", "page", "pages", "landing", "landing_page"
        }:
            workflow_kind = _artifact_kind(workflow)
            if workflow_kind is not None:
                evidence.append((workflow_kind, "workflow frontmatter"))
    path_parts = {part.casefold().replace("-", "_") for part in path.parts}
    if path_parts.intersection({"drafts", "rewrites", "published", "blogs", "blog"}):
        evidence.append(("blog", "article path"))
    if path_parts.intersection({"landing_pages", "landing_page", "landingpages", "pages"}):
        evidence.append(("landing_page", "article path"))
    kinds = {kind for kind, _ in evidence}
    if len(kinds) > 1:
        return (
            "blog",
            "context_artifact_kind_conflict",
            "Artifact evidence conflicts between article frontmatter, workflow, or path.",
        )
    resolved = evidence[0][0] if evidence else "blog"
    if resolved != requested:
        source = evidence[0][1] if evidence else "generic Markdown default"
        return (
            resolved,
            "context_artifact_kind_conflict",
            f"Caller artifact kind conflicts with {resolved} evidence from {source}.",
        )
    return resolved, None, None


if __name__ == "__main__":
    sys.exit(main())
