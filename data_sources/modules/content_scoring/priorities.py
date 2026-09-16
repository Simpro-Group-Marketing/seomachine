"""Priority-fix construction for content scoring results."""

from typing import Any, Dict, List, Mapping, Sequence, Tuple


def build_priority_fixes(
    dimensions: Sequence[Tuple[str, Dict[str, Any]]],
    gate_context: Mapping[str, Any],
    *,
    weights: Mapping[str, float],
) -> List[Dict[str, Any]]:
    """Build capped fixes, always placing failed hard gates before soft advice."""
    all_issues = []
    for dim_name, dim_data in dimensions:
        for issue in dim_data.get("issues", []):
            issue["dimension"] = dim_name
            issue["dimension_score"] = dim_data["score"]
            issue["impact"] = weights[dim_name] * (100 - issue["dimension_score"])
            all_issues.append(issue)

    soft_fixes = sorted(all_issues, key=lambda issue: -issue["impact"])
    gate_fixes = _build_gate_fixes(gate_context)
    return (gate_fixes + soft_fixes)[:5]


def _build_gate_fixes(gate_context: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """Return failed gates in the order operators should resolve them."""
    fixes = []
    if _has_independent_aeo_geo_blocker(gate_context):
        aeo_issues = gate_context["aeo_geo"].get("issues", [])
        aeo_summary = _issue_summary(aeo_issues, key="message")
        fixes.append(
            _gate_fix(
                "AEO/GEO blockers detected",
                (
                    "Resolve the failed AEO/GEO checks before optimizing soft content issues"
                    f": {aeo_summary}"
                ),
                "aeo_geo",
            )
        )

    if not gate_context["source_support_passed"]:
        blocker_lines = _line_summary(gate_context["source_support_findings"])
        fixes.append(
            _gate_fix(
                "Source support blockers detected",
                "Add approved proof rows with source-visible Evidence snippets, "
                f"or remove unsupported claims: {blocker_lines}",
                "source_support",
            )
        )

    if not gate_context["paa_provenance_passed"]:
        paa_findings = gate_context["paa_provenance_check"].get("details", {}).get(
            "findings", []
        )
        paa_questions = ", ".join(
            str(finding.get("question") or finding.get("match") or "unknown FAQ")
            for finding in paa_findings[:3]
        )
        fixes.append(
            _gate_fix(
                "PAA provenance blockers detected",
                "Add a PAA/FAQ Provenance block with an allowed source label, "
                f"a real artifact path, and exact selected questions: {paa_questions}",
                "paa_provenance",
            )
        )

    if not gate_context["faq_proof_passed"]:
        faq_findings = gate_context["faq_proof_check"].get("details", {}).get(
            "findings", []
        )
        faq_questions = ", ".join(
            str(finding.get("question", "unknown FAQ")) for finding in faq_findings[:3]
        )
        fixes.append(
            _gate_fix(
                "FAQ proof blockers detected",
                "Resolve each finding according to its machine-assigned citation_mode. "
                "For inline_required, use a natural descriptive anchor to an "
                "authoritative owned or non-owned source in the first visible answer "
                "paragraph, map it in the FAQ Proof Map, and do not use competitor-owned "
                "FAQ sources. For lower-risk modes, satisfy the assigned mode without "
                "quota-only links; a sidecar cannot replace inline evidence when "
                f"inline_required applies: {faq_questions}",
                "faq_proof",
            )
        )

    if not gate_context["metric_proof_pack_passed"]:
        metric_lines = _line_summary(gate_context["metric_proof_pack_findings"])
        fixes.append(
            _gate_fix(
                "Metric Proof Pack blockers detected",
                "Add a Metric Proof Pack with a search log and approved metrics "
                f"with source-visible Evidence, or document not applicable: {metric_lines}",
                "metric_proof_pack",
            )
        )

    if not gate_context["review_story_passed"]:
        review_story_lines = _line_summary(gate_context["review_story_findings"])
        fixes.append(
            _gate_fix(
                "Review story identity blockers detected",
                "Add a Review Story Selection with a real person or business identity, "
                "public review URL, and same-paragraph article link; or remove review-derived copy: "
                f"{review_story_lines}",
                "review_story_identity",
            )
        )

    if not gate_context["customer_proof_passed"]:
        customer_lines = _line_summary(gate_context["customer_proof_findings"])
        fixes.append(
            _gate_fix(
                "Customer proof diversity blockers detected",
                "Add Quote Matrix, Reference, Customer Story, or review-site search evidence, "
                f"or document a Reuse reason for repeated customer proof: {customer_lines}",
                "customer_proof_diversity",
            )
        )

    url_validation = gate_context["url_validation"]
    if url_validation is not None and not url_validation.passed:
        blocker_urls = ", ".join(result.url for result in url_validation.blockers[:3])
        fixes.append(
            _gate_fix(
                "URL validation blockers detected",
                "Replace or verify unresolved/manual-review URLs before optimize or publish: "
                f"{blocker_urls}",
                "url_validation",
            )
        )

    if not gate_context["minimum_visible_words_passed"]:
        minimum_visible_words = gate_context["minimum_visible_words"]
        fixes.append(
            _gate_fix(
                "Minimum visible article length blocker detected",
                "Expand the reader-facing article body to at least "
                f"{minimum_visible_words['threshold']} words before final release. "
                f"Current visible words: {minimum_visible_words['word_count']}.",
                "minimum_visible_words",
            )
        )

    return fixes


def _gate_fix(issue: str, fix: str, dimension: str) -> Dict[str, Any]:
    return {
        "issue": issue,
        "fix": fix,
        "severity": "high",
        "dimension": dimension,
        "dimension_score": 0,
        "impact": 100,
    }


def _line_summary(findings: Sequence[Mapping[str, Any]]) -> str:
    return ", ".join(f"line {finding.get('line', '?')}" for finding in findings[:3])


def _has_independent_aeo_geo_blocker(gate_context: Mapping[str, Any]) -> bool:
    """Avoid duplicating AEO/GEO failures represented by dedicated gate fixes."""
    if gate_context["aeo_geo_passed"]:
        return False
    delegated_checks = {"eeat_proof", "faq_proof", "paa_provenance"}
    return any(
        not isinstance(issue, Mapping) or issue.get("check") not in delegated_checks
        for issue in gate_context["aeo_geo"].get("issues", [])
    )


def _issue_summary(issues: Sequence[Any], *, key: str) -> str:
    summary = ", ".join(
        str(issue.get(key) or issue.get("issue") or "unknown issue")
        if isinstance(issue, Mapping)
        else str(issue)
        for issue in issues[:3]
    )
    return summary or "review the failed checks"
