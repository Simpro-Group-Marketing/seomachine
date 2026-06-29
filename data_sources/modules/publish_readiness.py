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
        customer_proof_diversity_guard,
        faq_proof_guard,
        metric_proof_pack_guard,
        numeric_claim_source_guard,
        paa_provenance_guard,
        public_research_link_guard,
        public_artifact_guard,
        review_story_identity_guard,
        source_support_guard,
    )
    from .content_scorer import ContentScorer
    from .guard_common import should_fail, summarize_findings
    from .url_validator import UrlValidationSummary, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    import ai_copy_linter
    import customer_proof_diversity_guard
    import faq_proof_guard
    import metric_proof_pack_guard
    import numeric_claim_source_guard
    import paa_provenance_guard
    import public_research_link_guard
    import public_artifact_guard
    import review_story_identity_guard
    import source_support_guard
    from content_scorer import ContentScorer
    from guard_common import should_fail, summarize_findings
    from url_validator import UrlValidationSummary, validate_file_urls


GateResult = Dict[str, Any]
ReadinessResult = Dict[str, Any]


PROOF_AWARE_GATES = (
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
)


def run_publish_readiness(
    file_path: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    ai_profile: str = "simpro-web",
) -> ReadinessResult:
    """Run the full publish-readiness stack and return structured results."""
    article_path = Path(file_path)
    proof_sidecar_path = str(proof_sidecar) if proof_sidecar is not None else None
    gates: List[GateResult] = []

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

    for name, label, guard_module in PROOF_AWARE_GATES:
        findings = guard_module.check_file(
            str(article_path),
            fail_on="error",
            proof_sidecar=proof_sidecar_path,
        )
        gates.append(_gate_from_findings(name, label, findings))

    scorer_result = _score_content(article_path, proof_sidecar_path)
    gates.append(_gate_from_score(scorer_result))

    passed = all(gate["passed"] for gate in gates)
    return {
        "file": str(article_path),
        "proof_sidecar": proof_sidecar_path,
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
        f"Proof sidecar: {result.get('proof_sidecar') or 'auto/default'}",
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
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the text report.",
    )
    args = parser.parse_args(argv)

    result = run_publish_readiness(
        args.file_path,
        proof_sidecar=args.proof_sidecar,
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


if __name__ == "__main__":
    sys.exit(main())
