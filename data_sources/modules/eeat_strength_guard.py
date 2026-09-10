"""Commercial blog E-E-A-T strength guard.

This guard does not approve public proof claims. It adds a publish-readiness
quality layer: commercial-investigation blog posts need at least one positive
E-E-A-T signal, or an explicit internal decision that no suitable proof is
available and the article is safe but weaker.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from . import review_story_identity_guard
    from .frontmatter import FrontmatterError, split_frontmatter
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    import review_story_identity_guard
    from frontmatter import FrontmatterError, split_frontmatter
    from guard_common import Finding, make_finding, should_fail, summarize_findings


NO_FIT_CUSTOMER_PROOF_OUTCOME = "no_fit_customer_proof"
SAFE_TO_PUBLISH_DECISION = "proof_unavailable_safe_to_publish"
POSITIVE_SIGNAL_DECISION = "positive_eeat_signal_present"
STRENGTH_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?E-E-A-T Strength Decision:?\s*$",
    re.IGNORECASE,
)
SECTION_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
SELECTED_RE = re.compile(r"(?im)^-\s*Selected:\s*\[([^\]]+)\]\s*$")
REVIEW_SECTION_RE = re.compile(
    r"(?im)^\s*#{1,6}\s+(?:Review Story Selection|Review Site Theme Selection):?\s*$"
)
REVIEW_SIGNAL_RE = re.compile(
    r"https?://[^\s)]*(?:capterra\.com|g2\.com|softwareadvice\.com|getapp\.com|"
    r"trustradius\.com|gartner(?:digitalmarkets)?\.com|trustpilot\.com)[^\s)]*|"
    r"\b(?:review|reviewer|review-site|customer review|Capterra|G2)\b",
    re.IGNORECASE,
)
DIRECT_COMMERCIAL_TERMS_RE = re.compile(
    r"\b(?:best|compare|comparison|platform|platforms|versus)\b|(?:^|\s)vs(?:\s|$)",
    re.IGNORECASE,
)
SOFTWARE_TERM_RE = re.compile(r"\bsoftware\b", re.IGNORECASE)
BUYER_TERMS_RE = re.compile(
    r"\b(?:buy|buyer|buying|choose|compare|comparison|shortlist|vendor|vendors|"
    r"platform|platforms|pricing|demo)\b",
    re.IGNORECASE,
)
REQUIRED_BOUNDARY_TERMS = (
    "customer proof",
    "named customer claims",
    "review stories",
    "exact quotes",
    "testimonials",
    "customer metrics",
    "unsupported sme claims",
)
REQUIRED_STRENGTH_FIELDS = (
    "applicability",
    "intent",
    "positive signals",
    "decision",
    "reason",
    "public copy boundary",
    "status",
)
EMPTY_VALUES = {"", "none", "[none]", "n/a", "na", "not applicable", "not_applicable"}


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    editorial_plan: str | Path | Mapping[str, Any] | None = None,
    customer_proof_selector_evidence: str | Path | Mapping[str, Any] | None = None,
    fred_authority_evidence: str | Path | None = None,
) -> list[Finding]:
    """Return proof-strength findings for one public article file."""
    del fail_on
    content = Path(path).read_text(encoding="utf-8")
    return check_content(
        content,
        proof_content=_read_optional_text(proof_sidecar),
        editorial_plan=_load_jsonish(editorial_plan),
        customer_proof_evidence=_load_jsonish(customer_proof_selector_evidence),
        fred_authority_content=_read_optional_text(fred_authority_evidence),
    )


def check_content(
    content: str,
    *,
    proof_content: str | None = None,
    editorial_plan: Mapping[str, Any] | None = None,
    customer_proof_evidence: Mapping[str, Any] | None = None,
    fred_authority_content: str | None = None,
) -> list[Finding]:
    """Return findings for article content plus sidecar/evidence inputs."""
    context = _evaluate(
        content,
        proof_content=proof_content or "",
        editorial_plan=editorial_plan,
        customer_proof_evidence=customer_proof_evidence,
        fred_authority_content=fred_authority_content or "",
    )
    if context["applicability"] != "required":
        return []

    positive_signals = list(context["positive_signals"])
    decision = context["decision"]
    proof_candidates_available = bool(context["proof_candidates_available"])
    if positive_signals:
        if decision == SAFE_TO_PUBLISH_DECISION:
            return [
                _finding(
                    "eeat_strength_decision_mismatch",
                    context["line"],
                    (
                        "E-E-A-T Strength Decision says proof is unavailable, "
                        "but a positive E-E-A-T signal is present."
                    ),
                    (
                        "Use Decision: positive_eeat_signal_present, or remove "
                        "the invalid proof signal."
                    ),
                    severity="error",
                )
            ]
        return []

    if proof_candidates_available:
        return [
            _finding(
                "eeat_strength_available_proof_omitted",
                context["line"],
                "Customer proof candidates are available but no positive E-E-A-T signal was selected.",
                (
                    "Select an approved proof source, reject candidates with a "
                    "source-specific reason, or remove commercial-investigation intent."
                ),
                severity="error",
            )
        ]

    decision_findings = _fallback_decision_findings(context)
    if decision_findings:
        return decision_findings
    return [
        _finding(
            "eeat_strength_safe_but_weak",
            context["line"],
            (
                "Commercial-investigation article has no positive E-E-A-T signal; "
                "the sidecar explicitly records proof_unavailable_safe_to_publish."
            ),
            (
                "Publish may proceed, but strengthen the article when selected "
                "customer proof, a named author, Fred authority, review-theme "
                "evidence, or SME review becomes available."
            ),
            severity="warning",
        )
    ]


def summarize_policy(
    article: str | Path,
    *,
    proof_sidecar: str | Path | None = None,
    proof_content: str | None = None,
    editorial_plan: str | Path | Mapping[str, Any] | None = None,
    customer_proof_selector_evidence: str | Path | Mapping[str, Any] | None = None,
    fred_authority_evidence: str | Path | None = None,
) -> dict[str, Any]:
    """Return a deterministic BOM/preflight summary for the strength policy."""
    content = _read_text_or_content(article)
    proof = proof_content if proof_content is not None else _read_optional_text(proof_sidecar)
    context = _evaluate(
        content,
        proof_content=proof or "",
        editorial_plan=_load_jsonish(editorial_plan),
        customer_proof_evidence=_load_jsonish(customer_proof_selector_evidence),
        fred_authority_content=_read_optional_text(fred_authority_evidence) or "",
    )
    findings = check_content(
        content,
        proof_content=proof,
        editorial_plan=_load_jsonish(editorial_plan),
        customer_proof_evidence=_load_jsonish(customer_proof_selector_evidence),
        fred_authority_content=_read_optional_text(fred_authority_evidence),
    )
    status = "not_applicable"
    if context["applicability"] == "required":
        if any(str(finding.get("severity")) == "error" for finding in findings):
            status = "failed"
        elif any(str(finding.get("severity")) == "warning" for finding in findings):
            status = "warning"
        else:
            status = "passed"
    return {
        "applicability": context["applicability"],
        "intent": context["intent"],
        "intent_reasons": context["intent_reasons"],
        "positive_signals": context["positive_signals"],
        "decision": context["decision"],
        "sidecar_status": context["sidecar_status"],
        "status": status,
        "findings": [str(finding.get("rule_id") or "") for finding in findings],
        "customer_proof_selector_evidence": str(customer_proof_selector_evidence or ""),
        "fred_authority_evidence": str(fred_authority_evidence or ""),
    }


def _evaluate(
    content: str,
    *,
    proof_content: str,
    editorial_plan: Mapping[str, Any] | None,
    customer_proof_evidence: Mapping[str, Any] | None,
    fred_authority_content: str,
) -> dict[str, Any]:
    metadata = _frontmatter(content)
    intent_reasons = _commercial_intent_reasons(content, metadata, editorial_plan)
    decision_block = _extract_strength_decision(proof_content)
    positive_signals = _positive_signals(
        content,
        metadata,
        proof_content,
        customer_proof_evidence,
        fred_authority_content,
        decision_block,
    )
    decision = _normalized_field(decision_block, "decision")
    return {
        "applicability": "required" if intent_reasons else "not_applicable",
        "intent": "commercial_investigation" if intent_reasons else "not_applicable",
        "intent_reasons": intent_reasons,
        "positive_signals": positive_signals,
        "proof_candidates_available": _proof_candidates_available(customer_proof_evidence),
        "decision": decision,
        "sidecar_status": _normalized_field(decision_block, "status"),
        "decision_block": decision_block,
        "line": int(decision_block.get("__line", 1)) if decision_block else 1,
    }


def _commercial_intent_reasons(
    content: str,
    metadata: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
) -> list[str]:
    reasons: list[str] = []
    title_terms = " ".join(
        str(value or "")
        for value in (
            metadata.get("title"),
            _first_heading(content),
            _nested(plan, "topic"),
            _nested(plan, "meta", "primary_keyword"),
            " ".join(str(item) for item in _nested(plan, "meta", "title_options") or []),
        )
    )
    if DIRECT_COMMERCIAL_TERMS_RE.search(title_terms):
        reasons.append("title_or_query_commercial_term")

    plan_text = json.dumps(plan, sort_keys=True) if isinstance(plan, Mapping) else ""
    funnel_stage = str(_nested(plan, "reader_contract", "funnel_stage") or "").casefold()
    if funnel_stage in {"mofu", "bofu"} and (
        BUYER_TERMS_RE.search(plan_text) or SOFTWARE_TERM_RE.search(title_terms)
    ):
        reasons.append("mofu_bofu_buyer_intent")

    for cta in _iter_cta_values(plan):
        if cta.startswith("commercial_"):
            reasons.append("commercial_cta")
            break

    for section in _iter_sections(plan):
        section_type = str(section.get("type") or "").casefold()
        heading = str(section.get("heading") or "")
        if section_type in {"body_comparison", "body_list"} and (
            DIRECT_COMMERCIAL_TERMS_RE.search(heading)
            or BUYER_TERMS_RE.search(plan_text)
            or section_type == "body_comparison"
        ):
            reasons.append("comparison_or_list_section")
            break

    content_type = " ".join(
        str(_nested(plan, "serp_strategy", "content_type", key) or "")
        for key in ("observed", "selected")
    )
    if re.search(r"\b(?:comparison|compare|list|best)\b", content_type, re.IGNORECASE):
        reasons.append("serp_comparison_intent")
    if "commercial-investigation" in plan_text.casefold():
        reasons.append("declared_commercial_investigation")
    return _dedupe(reasons)


def _positive_signals(
    content: str,
    metadata: Mapping[str, Any],
    proof_content: str,
    customer_proof_evidence: Mapping[str, Any] | None,
    fred_authority_content: str,
    decision_block: Mapping[str, Any],
) -> list[str]:
    signals: list[str] = []
    if str(metadata.get("author") or "").strip():
        signals.append("named_author")
    if _has_selected_customer_proof(customer_proof_evidence):
        signals.append("selected_customer_proof")
    if _has_selected_fred_authority(fred_authority_content) or _has_selected_fred_authority(proof_content):
        signals.append("selected_fred_authority")
    if _has_visible_approved_review_evidence(content, proof_content):
        signals.append("visible_approved_review_evidence")
    if _has_approved_sme_review_note(decision_block):
        signals.append("approved_sme_review_note")
    return _dedupe(signals)


def _fallback_decision_findings(context: Mapping[str, Any]) -> list[Finding]:
    block = context["decision_block"]
    if not isinstance(block, Mapping) or not block:
        return [
            _finding(
                "eeat_strength_decision_missing",
                int(context["line"]),
                "Commercial-investigation article has no positive E-E-A-T signal and no E-E-A-T Strength Decision.",
                (
                    "Add selected proof, a named author, Fred authority, approved "
                    "review-theme evidence, an approved SME review note, or record "
                    "Decision: proof_unavailable_safe_to_publish."
                ),
                severity="error",
            )
        ]

    missing = [field for field in REQUIRED_STRENGTH_FIELDS if field not in block]
    if missing:
        return [
            _finding(
                "eeat_strength_decision_incomplete",
                int(block.get("__line", 1)),
                "E-E-A-T Strength Decision is missing required fields: " + ", ".join(missing),
                "Add Applicability, Intent, Positive signals, Decision, Reason, Public copy boundary, and Status.",
                severity="error",
            )
        ]

    findings: list[Finding] = []
    line = int(block.get("__line", 1))
    if _normalized_field(block, "applicability") != "required":
        findings.append(
            _finding(
                "eeat_strength_applicability_invalid",
                line,
                "Commercial-investigation article must mark E-E-A-T strength as required.",
                "Use Applicability: required.",
                severity="error",
            )
        )
    if _normalized_field(block, "intent") != "commercial_investigation":
        findings.append(
            _finding(
                "eeat_strength_intent_invalid",
                line,
                "Commercial-investigation article must record Intent: commercial_investigation.",
                "Use Intent: commercial_investigation.",
                severity="error",
            )
        )
    if _normalized_field(block, "positive signals") not in {"[none]", "none"}:
        findings.append(
            _finding(
                "eeat_strength_positive_signal_mismatch",
                line,
                "No positive E-E-A-T signal is present, but Positive signals is not [none].",
                "Use Positive signals: [none], or add a valid positive signal.",
                severity="error",
            )
        )
    if _normalized_field(block, "decision") != SAFE_TO_PUBLISH_DECISION:
        findings.append(
            _finding(
                "eeat_strength_decision_invalid",
                line,
                "No positive E-E-A-T signal requires Decision: proof_unavailable_safe_to_publish.",
                "Use the fallback decision only after the selector/Fred proof lanes return no fit.",
                severity="error",
            )
        )
    if _word_count(str(block.get("reason") or "")) < 8:
        findings.append(
            _finding(
                "eeat_strength_reason_too_thin",
                line,
                "E-E-A-T Strength Decision needs a substantive proof-unavailable reason.",
                "Explain which proof lanes were checked and why no signal fits the article objective.",
                severity="error",
            )
        )
    boundary = str(block.get("public copy boundary") or "").casefold()
    missing_terms = [term for term in REQUIRED_BOUNDARY_TERMS if term not in boundary]
    if missing_terms:
        findings.append(
            _finding(
                "eeat_strength_boundary_incomplete",
                line,
                "Public copy boundary is missing required omissions: " + ", ".join(missing_terms),
                (
                    "State that public copy omits customer proof, named customer "
                    "claims, review stories, exact quotes, testimonials, customer "
                    "metrics, and unsupported SME claims."
                ),
                severity="error",
            )
        )
    if _normalized_field(block, "status") != "approved":
        findings.append(
            _finding(
                "eeat_strength_status_invalid",
                line,
                "E-E-A-T Strength Decision must use Status: approved.",
                "Use Status: approved after the fallback decision is reviewed.",
                severity="error",
            )
        )
    return findings


def _has_selected_customer_proof(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("selection_outcome") == NO_FIT_CUSTOMER_PROOF_OUTCOME:
        return False
    roles = evidence.get("roles")
    if not isinstance(roles, list):
        return False
    for row in roles:
        if not isinstance(row, Mapping):
            continue
        selected = str(row.get("selected_id") or "").strip().casefold()
        if selected and selected != "none":
            return True
    return False


def _proof_candidates_available(evidence: Mapping[str, Any] | None) -> bool:
    if not isinstance(evidence, Mapping):
        return False
    if evidence.get("selection_outcome") == NO_FIT_CUSTOMER_PROOF_OUTCOME:
        return False
    inputs = evidence.get("inputs")
    rejected_overrides = (
        inputs.get("rejected_overrides")
        if isinstance(inputs, Mapping)
        else None
    )
    roles = evidence.get("roles")
    if not isinstance(roles, list):
        return False
    for row in roles:
        if not isinstance(row, Mapping):
            continue
        candidates = row.get("candidate_ids")
        selected = str(row.get("selected_id") or "").strip().casefold()
        if isinstance(candidates, list) and candidates and selected in {"", "none"}:
            role = str(row.get("role") or "").strip()
            role_rejections = (
                rejected_overrides.get(role)
                if isinstance(rejected_overrides, Mapping)
                else None
            )
            if not isinstance(role_rejections, Mapping):
                return True
            for candidate in candidates:
                candidate_id = str(candidate or "").strip()
                reason = str(role_rejections.get(candidate_id) or "").strip()
                if not candidate_id or _word_count(reason) < 8:
                    return True
    return False


def _has_selected_fred_authority(content: str) -> bool:
    if not content or "Fred Voccola Authority Selection" not in content:
        return False
    if not re.search(r"(?im)^-\s*Evaluation status:\s*completed\s*$", content):
        return False
    match = SELECTED_RE.search(content)
    if not match:
        return False
    return match.group(1).strip().casefold() != "none"


def _has_visible_approved_review_evidence(content: str, proof_content: str) -> bool:
    if not proof_content or not REVIEW_SECTION_RE.search(proof_content):
        return False
    try:
        findings = review_story_identity_guard.check_content(
            content,
            proof_content=proof_content,
        )
    except Exception:
        return False
    if any(str(finding.get("severity")) == "error" for finding in findings):
        return False
    return bool(REVIEW_SIGNAL_RE.search(content))


def _has_approved_sme_review_note(block: Mapping[str, Any]) -> bool:
    if not isinstance(block, Mapping) or not block:
        return False
    if _normalized_field(block, "status") != "approved":
        return False
    positive = _normalized_field(block, "positive signals")
    if "sme review note" not in positive:
        return False
    note = str(block.get("sme review note") or "")
    if not note:
        return False
    required = (
        "reviewer name",
        "role/title",
        "review date",
        "source of review",
        "status: approved",
    )
    lowered = note.casefold()
    return all(field in lowered for field in required)


def _extract_strength_decision(proof_content: str) -> dict[str, Any]:
    if not proof_content:
        return {}
    lines = proof_content.splitlines()
    in_section = False
    fields: dict[str, Any] = {}
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if STRENGTH_HEADING_RE.match(stripped):
            in_section = True
            fields = {"__line": index}
            continue
        if in_section and SECTION_HEADING_RE.match(stripped):
            break
        if not in_section:
            continue
        match = BULLET_FIELD_RE.match(stripped)
        if not match:
            continue
        key = _normalize_key(match.group("key"))
        fields[key] = match.group("value").strip()
    return fields


def _iter_cta_values(plan: Mapping[str, Any] | None) -> Iterable[str]:
    if not isinstance(plan, Mapping):
        return ()
    values: list[str] = []
    engagement = plan.get("engagement_map")
    ctas = engagement.get("ctas") if isinstance(engagement, Mapping) else None
    if isinstance(ctas, Mapping):
        values.extend(str(key).casefold() for key, value in ctas.items() if value)
    for section in _iter_sections(plan):
        cta = str(section.get("cta") or "").strip().casefold()
        if cta:
            values.append(cta)
    return values


def _iter_sections(plan: Mapping[str, Any] | None) -> Iterable[Mapping[str, Any]]:
    if not isinstance(plan, Mapping):
        return ()
    sections = plan.get("sections")
    if not isinstance(sections, list):
        return ()
    return [section for section in sections if isinstance(section, Mapping)]


def _frontmatter(content: str) -> dict[str, Any]:
    try:
        metadata, _body, _line = split_frontmatter(content)
    except FrontmatterError:
        return {}
    return dict(metadata)


def _first_heading(content: str) -> str:
    for line in content.splitlines():
        if line.startswith("# "):
            return line.lstrip("#").strip()
    return ""


def _nested(value: Mapping[str, Any] | None, *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _normalized_field(block: Mapping[str, Any], field: str) -> str:
    return str(block.get(_normalize_key(field)) or "").strip().casefold()


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value))


def _dedupe(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _load_jsonish(value: str | Path | Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return value
    path = Path(value)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None


def _read_optional_text(path: str | Path | None) -> str | None:
    if path is None:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _read_text_or_content(value: str | Path) -> str:
    if isinstance(value, Path):
        return value.read_text(encoding="utf-8")
    text = str(value)
    if "\n" in text:
        return text
    path = Path(text)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return text


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    severity: str,
) -> Finding:
    return make_finding(
        rule_id,
        severity,
        line,
        message=message,
        suggestion=suggestion,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate commercial blog E-E-A-T strength.")
    parser.add_argument("file")
    parser.add_argument("--proof-sidecar")
    parser.add_argument("--editorial-plan")
    parser.add_argument("--customer-proof-selector-evidence")
    parser.add_argument("--fred-authority-evidence")
    parser.add_argument("--fail-on", choices=("error", "warning", "none"), default="error")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    findings = check_file(
        args.file,
        proof_sidecar=args.proof_sidecar,
        editorial_plan=args.editorial_plan,
        customer_proof_selector_evidence=args.customer_proof_selector_evidence,
        fred_authority_evidence=args.fred_authority_evidence,
        fail_on=args.fail_on,
    )
    if args.json:
        print(json.dumps({"findings": findings, "summary": summarize_findings(findings)}, indent=2))
    else:
        for finding in findings:
            print(
                f"{finding['severity'].upper()} {finding['rule_id']} "
                f"line {finding['line']}: {finding.get('message', '')}"
            )
    return 1 if should_fail(findings, args.fail_on) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
