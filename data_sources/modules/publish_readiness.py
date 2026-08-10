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
        blog_assembly_bom_guard,
        context_binding_guard,
        customer_proof_diversity_guard,
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
        source_support_guard,
        vault_brand_language_guard,
    )
    from .content_scorer import ContentScorer
    from .landing_page_scorer import LandingPageScorer
    from .publishable_markdown import FrontmatterError, read_publishable_markdown
    from .guard_common import should_fail, summarize_findings
    from .url_validator import UrlValidationSummary, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import answer_withholding_guard
    import blog_assembly_bom_guard
    import context_binding_guard
    import customer_proof_diversity_guard
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
    import source_support_guard
    import vault_brand_language_guard
    from content_scorer import ContentScorer
    from landing_page_scorer import LandingPageScorer
    from publishable_markdown import FrontmatterError, read_publishable_markdown
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
        "fred_authority",
        "Fred Voccola Authority",
        fred_authority_guard,
    ),
)


SIMPRO_CONTEXT_GATE_NAMES = frozenset({
    "vault_brand_language",
    "named_feature_status",
})


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    context_request: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    assembly_bom: str | Path | None = None,
    vault_root: str | Path | None = None,
    ai_profile: str = "simpro-web",
) -> ReadinessResult:
    """Run the full publish-readiness stack and return structured results."""
    article_path = Path(file_path)
    proof_sidecar_path = str(proof_sidecar) if proof_sidecar is not None else None
    context_request_path = str(context_request) if context_request is not None else None
    context_pack_path = str(context_pack) if context_pack is not None else None
    context_receipt_path = str(context_receipt) if context_receipt is not None else None
    assembly_bom_path = str(assembly_bom) if assembly_bom is not None else None
    try:
        article = read_publishable_markdown(article_path)
    except FrontmatterError as exc:
        gate = _gate_from_findings(
            "frontmatter_metadata",
            "Frontmatter Metadata",
            [{
                "rule_id": "frontmatter_invalid",
                "severity": "error",
                "line": 1,
                "column": 1,
                "message": str(exc),
                "suggestion": "Repair the YAML frontmatter before publishing.",
            }],
        )
        return {
            "file": str(article_path),
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": None,
            "gates": [gate],
            "score": None,
            "score_threshold": 85,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {"dimension": "frontmatter_metadata", "issue": str(exc)}
            ],
        }
    article_content = article.raw
    artifact_kind = context_binding_guard.resolve_artifact_kind(
        article_content,
        article_path=article_path,
    )
    score_threshold = 75 if artifact_kind == "landing_page" else 85
    gates: List[GateResult] = []

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
            "proof_sidecar": proof_sidecar_path,
            "context_request": context_request_path,
            "context_pack": context_pack_path,
            "context_receipt": context_receipt_path,
            "assembly_bom": assembly_bom_path,
            "passed": False,
            "artifact_kind": artifact_kind,
            "gates": gates,
            "score": None,
            "score_threshold": score_threshold,
            "aeo_geo": {"score": None, "threshold": 90, "passed": False},
            "priority_fixes": [
                {
                    "dimension": "context_binding",
                    "issue": blocker,
                }
                for blocker in context_gate.get("blockers", [])
            ],
        }

    if assembly_bom_path is not None:
        bom_gate = _gate_from_findings(
            "blog_assembly_bom",
            "Blog Assembly BOM",
            blog_assembly_bom_guard.check_bom_file(
                assembly_bom_path,
                article_path=article_path,
                validation_sidecar_path=proof_sidecar_path or "",
                context_request_path=context_request_path or "",
                context_pack_path=context_pack_path or "",
                context_receipt_path=context_receipt_path or "",
            ),
        )
        gates.append(bom_gate)
        if not bom_gate["passed"]:
            return {
                "file": str(article_path),
                "proof_sidecar": proof_sidecar_path,
                "context_request": context_request_path,
                "context_pack": context_pack_path,
                "context_receipt": context_receipt_path,
                "assembly_bom": assembly_bom_path,
                "passed": False,
                "artifact_kind": artifact_kind,
                "gates": gates,
                "score": None,
                "score_threshold": score_threshold,
                "aeo_geo": {"score": None, "threshold": 90, "passed": False},
                "priority_fixes": [
                    {
                        "dimension": "blog_assembly_bom",
                        "issue": blocker,
                    }
                    for blocker in bom_gate.get("blockers", [])
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

    simpro_context_required = context_binding_guard.requires_context(article_content)
    for name, label, guard_module in ARTICLE_GATES:
        if name in SIMPRO_CONTEXT_GATE_NAMES and not simpro_context_required:
            continue
        if name == "fred_authority" and not fred_authority_guard.requires_authority_review(
            article_content
        ):
            continue
        guard_kwargs: Dict[str, Any] = {
            "fail_on": "error",
            "proof_sidecar": proof_sidecar_path,
        }
        if name in {
            "named_feature_status",
            "customer_proof_diversity",
            "fred_authority",
            "vault_brand_language",
        }:
            guard_kwargs.update(
                {
                    "context_pack": context_pack_path,
                    "context_receipt": context_receipt_path,
                }
            )
        if name == "named_feature_status":
            guard_kwargs["vault_root"] = vault_root
        if name == "fred_authority":
            guard_kwargs["vault_root"] = vault_root
        findings = guard_module.check_file(str(article_path), **guard_kwargs)
        gates.append(_gate_from_findings(name, label, findings))

    scorer_result = _score_content(
        article_path,
        proof_sidecar_path,
        artifact_kind=artifact_kind or "blog",
    )
    gates.append(_gate_from_score(scorer_result))

    passed = all(gate["passed"] for gate in gates)
    return {
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
        "context_request": context_request_path,
        "context_pack": context_pack_path,
        "context_receipt": context_receipt_path,
        "assembly_bom": assembly_bom_path,
        "passed": passed,
        "artifact_kind": artifact_kind,
        "gates": gates,
        "score": _content_score(scorer_result),
        "score_threshold": scorer_result.get("threshold", 85),
        "aeo_geo": scorer_result.get("aeo_geo", {}),
        "priority_fixes": scorer_result.get("priority_fixes", []),
    }


def format_text_report(result: ReadinessResult) -> str:
    """Return a human-readable publish-readiness report."""
    lines = [
        "PUBLISH READINESS",
        "=" * 50,
        f"File: {result['file']}",
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
        f"Context request: {result.get('context_request') or 'not required/provided'}",
        f"Context pack: {result.get('context_pack') or 'not required/provided'}",
        f"Context receipt: {result.get('context_receipt') or 'not required/provided'}",
        f"Assembly BOM: {result.get('assembly_bom') or 'not required/provided'}",
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

    content_score = result.get("score")
    content_threshold = result.get("score_threshold", 85)
    content_passed = bool(
        content_score is not None and content_score >= content_threshold
    )
    aeo_geo = result.get("aeo_geo", {})
    aeo_geo_score = aeo_geo.get("score")
    aeo_geo_threshold = aeo_geo.get("threshold", 90)
    aeo_geo_passed = bool(aeo_geo.get("passed", False))

    lines.extend(
        [
            "",
            _score_report_line(
                "Content score",
                content_score,
                content_threshold,
                content_passed,
            ),
            _score_report_line(
                "AEO/GEO score",
                aeo_geo_score,
                aeo_geo_threshold,
                aeo_geo_passed,
            ),
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
    parser.add_argument("--assembly-bom", help="Current blog assembly BOM JSON.")
    parser.add_argument("--vault-root", help="Configured Simpro vault root override.")
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
        assembly_bom=args.assembly_bom,
        vault_root=args.vault_root,
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
        "name": score_result.get("gate_name", "content_scorer"),
        "label": score_result.get("gate_label", "Content Scorer"),
        "passed": passed,
        "errors": 0 if passed else 1,
        "warnings": len(priority_fixes) if passed else 0,
        "findings": [],
        "blockers": _priority_fix_lines(priority_fixes) if not passed else [],
    }


def _score_content(
    article_path: Path,
    proof_sidecar: Optional[str],
    *,
    artifact_kind: str = "blog",
) -> Dict[str, Any]:
    content = article_path.read_text(encoding="utf-8")
    if artifact_kind == "landing_page":
        artifact = read_publishable_markdown(article_path)
        page_type = artifact.scalar("page_type").casefold()
        conversion_goal = artifact.scalar("conversion_goal").casefold()
        if page_type not in {"seo", "ppc"} or conversion_goal not in {
            "trial",
            "demo",
            "lead",
        }:
            return {
                "passed": False,
                "content_quality_score": None,
                "threshold": 75,
                "aeo_geo": {
                    "score": None,
                    "threshold": None,
                    "passed": True,
                    "not_applicable": True,
                },
                "priority_fixes": [
                    {
                        "dimension": "landing_page_metadata",
                        "issue": "Landing pages require page_type seo|ppc and conversion_goal trial|demo|lead.",
                    }
                ],
                "gate_name": "landing_page_scorer",
                "gate_label": "Landing Page Scorer",
            }
        result = LandingPageScorer(page_type, conversion_goal).score(
            content,
            meta_title=artifact.scalar("meta_title", "title"),
            meta_description=artifact.scalar("meta_description"),
            primary_keyword=artifact.scalar("primary_keyword", "target_keyword"),
        )
        issues = [
            {"dimension": "landing_page", "issue": str(issue)}
            for issue in result.get("critical_issues", [])
        ]
        if not issues and not result.get("publishing_ready"):
            issues = [
                {"dimension": "landing_page", "issue": str(issue)}
                for issue in result.get("suggestions", [])[:5]
            ]
        return {
            "passed": bool(result.get("publishing_ready")),
            "content_quality_score": result.get("overall_score"),
            "threshold": 75,
            "aeo_geo": {
                "score": None,
                "threshold": None,
                "passed": True,
                "not_applicable": True,
            },
            "priority_fixes": issues,
            "gate_name": "landing_page_scorer",
            "gate_label": "Landing Page Scorer",
            "landing_page": result,
        }
    scorer = ContentScorer()
    return scorer.score(
        content,
        validate_urls=False,
        validate_source_support=False,
        source_path=str(article_path),
        proof_sidecar=proof_sidecar,
    )


def _content_score(score_result: Dict[str, Any]) -> Any:
    return score_result.get("content_quality_score", score_result.get("composite_score"))


def _score_report_line(
    label: str,
    score: Any,
    threshold: Any,
    passed: bool,
) -> str:
    if score is None:
        return f"{label}: n/a"
    status = "PASS" if passed else "FAIL"
    return f"{label}: {score}/100 (threshold: {threshold}, {status})"


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


if __name__ == "__main__":
    sys.exit(main())
