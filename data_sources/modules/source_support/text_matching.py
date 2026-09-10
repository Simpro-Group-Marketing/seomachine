"""Text Matching responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _proof_matches_customer(candidate: ClaimCandidate, proof: ProofEntry) -> bool:
    candidate_names = set(candidate.customer_names)
    if proof.customer:
        proof_names = {proof.customer}
    else:
        proof_names = set(_known_customer_names([proof]))
    if candidate_names and any(
        _normalize_text(proof_name) in _normalize_text(candidate_name)
        or _normalize_text(candidate_name) in _normalize_text(proof_name)
        for candidate_name in candidate_names
        for proof_name in proof_names
    ):
        return True
    return bool(candidate.has_case_study_link and "/case-studies/" in proof.url)

def _text_overlaps(text: str, proof: ProofEntry) -> bool:
    if _normalize_text(_claim_text_for_detection(text)) == _normalize_text(proof.claim):
        return True
    text_words = _significant_words(text)
    proof_words = _significant_words(f"{proof.claim} {proof.evidence}")
    return len(text_words.intersection(proof_words)) >= 2

def _contains_evidence(source_text: str, evidence: str) -> bool:
    return _normalize_text(evidence) in _normalize_text(source_text)

def _extract_visible_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)

def _normalize_key(key: str) -> str:
    return re.sub(r"\s+", " ", key.strip().lower()).strip()

def _clean_field_value(value: str) -> str:
    return value.strip().strip('"').strip("'")

def _normalize_section(section: str) -> str:
    normalized = _normalize_key(section)
    if "customer proof pack" in normalized:
        return "customer proof pack"
    if "source map" in normalized:
        return "source map"
    if "faq proof" in normalized:
        return "faq proof"
    return normalized

def _normalize_text(text: str) -> str:
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[^a-z0-9%$]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()

def _significant_words(text: str) -> set[str]:
    stopwords = {
        "the", "and", "with", "that", "this", "from", "into", "using",
        "used", "can", "for", "its", "their", "same", "amount", "business",
        "resources", "mechanical", "beacon", "shaffer", "simpro",
    }
    return {
        word
        for word in re.findall(r"[a-z0-9%$]+", _normalize_text(text))
        if len(word) > 2 and word not in stopwords
    }

def _is_generic_name(name: str) -> bool:
    normalized = _normalize_text(name)
    generic = {
        "source map",
        "customer proof pack",
        "approved metric",
        "proof url",
        "status approved",
        "hvac operators",
        "specialty trade",
    }
    return normalized in generic


__all__ = [
    "_proof_matches_customer", "_text_overlaps", "_contains_evidence",
    "_extract_visible_text", "_normalize_key", "_clean_field_value",
    "_normalize_section", "_normalize_text", "_significant_words", "_is_generic_name",
]
