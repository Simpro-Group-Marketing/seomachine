"""Focused aeo eeat scoring."""

from __future__ import annotations

from .aeo_customer_evidence import _validated_customer_experience_binding
from .aeo_no_fit import _has_documented_no_fit_experience_boundary
from .aeo_text import _extract_markdown_links
from .aeo_text import _normalize_key
from .aeo_text import _normalize_url
from .aeo_text import _unwrap_bracketed_value
from typing import Any
from typing import Dict
from typing import Optional
import re

def _check_eeat_proof(
    content: str,
    body: str,
    metadata: Dict[str, Any],
    proof_sidecar_content: Optional[str] = None,
    proof_sidecar_path: Optional[str] = None,
) -> Dict[str, Any]:
    links = _extract_markdown_links(content)
    normalized = {_normalize_key(str(key)): value for key, value in metadata.items()}

    case_study_links = [url for _, url in links if _is_case_study_link(url)]
    review_site_links = [url for _, url in links if _is_review_site_link(url)]
    simpro_product_links = [
        url for _, url in links if _is_simpro_product_or_workflow_link(url)
    ]
    clockshark_workflow_links = [
        url for _, url in links if _is_clockshark_product_or_workflow_link(url)
    ]

    experience_signals = []
    validated_customer_experience = _validated_customer_experience_binding(
        content,
        proof_sidecar_content,
        proof_sidecar_path,
    )
    if validated_customer_experience:
        experience_signals.append("validated_customer_experience")
    has_documented_no_fit_boundary = _has_documented_no_fit_experience_boundary(
        proof_sidecar_content,
        proof_sidecar_path=proof_sidecar_path,
    )
    if has_documented_no_fit_boundary:
        experience_signals.append("documented_no_fit_experience_boundary")

    expertise_signals = []
    if normalized.get("author"):
        expertise_signals.append("author_metadata")
    if _has_expert_quote(body):
        expertise_signals.append("expert_quote")
    if _has_valid_fred_authority_expertise(body, proof_sidecar_content):
        expertise_signals.append("fred_authority")

    has_experience = bool(experience_signals)
    has_expertise = bool(expertise_signals)
    passed = has_experience

    return {
        "passed": passed,
        "issue": "The draft is missing required first-hand experience proof.",
        "fix": (
            "Use a hash-verified customer-proof selector experience_story binding, "
            "an approved Selected Customer Proof Mining record, and the selected "
            "identity and public URL in the same visible article paragraph. A bare "
            "case-study link or self-asserted proof label does not establish Experience. "
            "If no story fits, document a substantive "
            "First-hand evidence decision with Selected: [none] in the E-E-A-T "
            "Proof Map and a matching experience_story slate row with rejected-"
            "candidate reasons. Generic review-site experience evidence "
            "and VoC themes are research inputs, not E-E-A-T story proof. Named "
            "authors and receipt-approved Fred authority are optional positive "
            "expertise signals, not required AEO pass conditions. A bare owned "
            "product link does not establish Expertise."
        ),
        "severity": "high",
        "details": {
            "case_study_links": case_study_links,
            "review_site_links": review_site_links,
            "simpro_product_links": simpro_product_links,
            "clockshark_workflow_links": clockshark_workflow_links,
            "experience_signals": experience_signals,
            "expertise_signals": expertise_signals,
            "has_experience": has_experience,
            "has_expertise": has_expertise,
            "has_review_story_selection": False,
            "validated_customer_experience": validated_customer_experience,
            "has_documented_no_fit_boundary": has_documented_no_fit_boundary,
        },
    }

def _is_review_site_link(url: str) -> bool:
    lower = url.lower()
    review_domains = (
        "g2.com",
        "capterra.com",
        "softwareadvice.com",
        "getapp.com",
        "trustradius.com",
        "gartner.com",
        "gartnerdigitalmarkets.com",
        "trustpilot.com",
        "apps.apple.com",
        "play.google.com",
    )
    return any(domain in lower for domain in review_domains)

def _is_case_study_link(url: str) -> bool:
    lower = url.lower()
    return bool(
        re.search(r"/case-stud(?:y|ies)/", lower) or "/resources/case-study-" in lower
    )

def _is_simpro_product_or_workflow_link(url: str) -> bool:
    lower = url.lower()
    if "simprogroup.com" not in lower:
        return False

    product_paths = (
        "/features/",
        "/solutions/",
        "/industries/",
        "/product/",
        "/products/",
        "/tour/",
    )
    return any(path in lower for path in product_paths)

def _is_clockshark_product_or_workflow_link(url: str) -> bool:
    lower = url.lower()
    if "clockshark.com" not in lower:
        return False

    workflow_paths = (
        "/industries/",
        "/tour/",
        "/blog/",
    )
    return any(path in lower for path in workflow_paths)

def _has_expert_quote(body: str) -> bool:
    quote_pattern = (
        r'"[^"]{20,240}"\s*(?:,?\s*(?:said|says|according to|explained|wrote)\b)'
    )
    attribution_pattern = (
        r'(?:said|says|according to|explained|wrote)\s+[^.]{3,80}:\s*"[^"]{20,240}"'
    )
    return bool(
        re.search(quote_pattern, body, re.IGNORECASE)
        or re.search(attribution_pattern, body, re.IGNORECASE)
    )

def _has_valid_fred_authority_expertise(
    body: str,
    proof_sidecar_content: Optional[str],
) -> bool:
    if not proof_sidecar_content:
        return False
    fields = _extract_fred_authority_selection_fields(proof_sidecar_content)
    if not fields:
        return False
    if fields.get("evaluation_status", "").strip().casefold() != "completed":
        return False
    selected = _unwrap_bracketed_value(fields.get("selected", ""))
    if not selected or selected.casefold() == "none":
        return False
    intended_use = fields.get("intended_use", "").strip().casefold()
    if not intended_use or intended_use == "none":
        return False
    evidence_status = fields.get("evidence_status", "").strip().casefold()
    if evidence_status != "receipt_approved":
        return False
    public_url = fields.get("public_url", "").strip()
    if not public_url.startswith(("http://", "https://")):
        return False
    expected = _normalize_url(public_url)
    return any(
        _normalize_url(url) == expected
        for _, url in _extract_markdown_links(body)
    )

def _extract_fred_authority_selection_fields(
    proof_sidecar_content: str,
) -> Dict[str, str]:
    in_block = False
    fields: Dict[str, str] = {}
    for line in proof_sidecar_content.splitlines():
        stripped = line.strip()
        if re.match(
            r"^(?:#{1,6}\s+)?Fred Voccola Authority Selection:?\s*$",
            stripped,
            re.IGNORECASE,
        ):
            in_block = True
            continue
        if not in_block:
            continue
        if stripped.startswith("```") or re.match(r"^#{1,6}\s+", stripped):
            break
        match = re.match(r"^[-*+]\s*([^:]+):\s*(.+?)\s*$", stripped)
        if match:
            fields[_normalize_key(match.group(1))] = match.group(2).strip()
    return fields


__all__ = [
    "_check_eeat_proof",
    "_is_review_site_link",
    "_is_case_study_link",
    "_is_simpro_product_or_workflow_link",
    "_is_clockshark_product_or_workflow_link",
    "_has_expert_quote",
    "_has_valid_fred_authority_expertise",
    "_extract_fred_authority_selection_fields",
]
