"""Findings responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _finding(
    rule_id: str,
    candidate: ClaimCandidate,
    message: str,
    suggestion: str,
    proof: Optional[ProofEntry] = None,
    severity: str = "error",
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": candidate.line,
        "column": 1,
        "match": candidate.text if match is None else match,
        "message": message,
        "suggestion": suggestion,
    }
    if candidate.numeric_tokens:
        finding["numeric_tokens"] = candidate.numeric_tokens
    if proof is not None:
        finding["proof_line"] = proof.line
        finding["proof_url"] = proof.url
        finding["evidence"] = proof.evidence
    return finding

def _known_customer_names(proof_entries: Sequence[ProofEntry]) -> List[str]:
    names = set()
    for proof in proof_entries:
        values = [proof.customer]
        if (
            proof.section == "customer proof pack"
            or proof.source_class in {"customer_proof", "review_platform", "review_story"}
            or any(token in proof.use.casefold() for token in ("customer", "review"))
        ):
            values.append(proof.claim)
        for value in values:
            for name in re.findall(r"\b[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z&]+){1,4}\b", value):
                if not _is_generic_name(name):
                    names.add(name.strip())
    return sorted(names, key=len, reverse=True)

def _customer_names_in_text(text: str, known_customer_names: Sequence[str]) -> List[str]:
    normalized = _normalize_text(text)
    matches = []
    for name in known_customer_names:
        if _normalize_text(name) in normalized:
            matches.append(name)
    return matches

def _has_case_study_link(text: str) -> bool:
    return any("/case-studies/" in match.group(2) for match in MARKDOWN_LINK_RE.finditer(text))

def _is_exact_quote_claim(
    text: str,
    customer_names: Sequence[str],
    has_case_study_link: bool,
) -> bool:
    if not EXACT_QUOTE_RE.search(text):
        return False
    detection_text = _claim_text_for_detection(text)
    return (
        has_case_study_link
        or bool(customer_names)
        or bool(QUOTE_ATTRIBUTION_SIGNAL_RE.search(detection_text))
    )

def _is_review_authority_claim(text: str) -> bool:
    normalized = _normalize_text(text)
    negated_patterns = (
        "without naming a reviewer",
        "without using ratings",
        "without star ratings",
        "no reviewer",
        "no ratings",
        "not use ratings",
        "do not use ratings",
        "do not publish a universal ranking",
        "does not publish a universal ranking",
        "do not support a universal ranking",
        "does not support a universal ranking",
    )
    if any(pattern in normalized for pattern in negated_patterns):
        return False
    return bool(REVIEW_AUTHORITY_SIGNAL_RE.search(text))


__all__ = [
    "_finding", "_known_customer_names", "_customer_names_in_text",
    "_has_case_study_link", "_is_exact_quote_claim", "_is_review_authority_claim",
]
