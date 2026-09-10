"""Claim Matching responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _general_claim_type(text: str) -> str:
    if SELF_NAVIGATION_RE.search(text.strip()):
        return ""
    for claim_type, pattern in GENERAL_CLAIM_PATTERNS:
        if pattern.search(text):
            return claim_type
    return ""

def _is_general_claim_exempt(sentence: str) -> bool:
    """Apply only language-observable exemptions, never writer-provided labels."""
    text = _claim_text_for_detection(sentence).strip()
    if text.endswith("?"):
        return True
    if OPINION_SIGNAL_RE.search(text):
        return True
    if IMPERATIVE_INSTRUCTION_RE.search(text):
        return True
    if SCENARIO_SIGNAL_RE.search(text):
        return not (
            OUTCOME_SIGNAL_RE.search(text)
            or any(
                claim_type in {"absolute", "causal", "comparative", "guarantee"}
                and pattern.search(text)
                for claim_type, pattern in GENERAL_CLAIM_PATTERNS
            )
        )
    return False


__all__ = [
    "_general_claim_type", "_is_general_claim_exempt",
    "_validate_source_text_contains_evidence", "_validate_evidence_claim_fit",
    "_evidence_contradicts_claim",
]

def _validate_source_text_contains_evidence(
    source_text: str,
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    if not _contains_evidence(source_text, proof.evidence):
        return _finding(
            "source_evidence_not_found",
            candidate,
            "Proof evidence was not found in the cited source.",
            "Replace the claim with source-visible wording, update Evidence to an exact visible snippet, or remove the claim.",
            proof,
        )
    return None

def _validate_evidence_claim_fit(
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    if _evidence_contradicts_claim(proof.claim, proof.evidence):
        return _finding(
            "source_evidence_contradicts_claim",
            candidate,
            "The mapped source evidence contradicts the public claim.",
            "Remove or rewrite the claim so it follows the source-visible evidence.",
            proof,
        )
    claim_words = _significant_words(proof.claim)
    evidence_words = _significant_words(proof.evidence)
    minimum_overlap = max(3, math.ceil(len(claim_words) * 0.5))
    if len(claim_words.intersection(evidence_words)) < minimum_overlap:
        return _finding(
            "source_evidence_claim_fit_insufficient",
            candidate,
            "The evidence snippet does not directly support enough of the mapped claim.",
            "Use source-visible evidence that directly entails the complete claim, not a topical fragment.",
            proof,
        )
    return None

def _evidence_contradicts_claim(claim: str, evidence: str) -> bool:
    claim_text = _normalize_text(claim)
    evidence_text = _normalize_text(evidence)
    negations = (" no ", " not ", " never ", " cannot ", " without ", " fails to ")
    padded_claim = f" {claim_text} "
    padded_evidence = f" {evidence_text} "
    claim_negated = any(token in padded_claim for token in negations)
    evidence_negated = any(token in padded_evidence for token in negations)
    if claim_negated != evidence_negated:
        return True
    opposites = (
        ("increase", "decrease"),
        ("improve", "worsen"),
        ("reduce", "increase"),
        ("higher", "lower"),
        ("more", "less"),
        ("faster", "slower"),
        ("better", "worse"),
        ("enable", "prevent"),
    )
    claim_words = set(claim_text.split())
    evidence_words = set(evidence_text.split())
    for left, right in opposites:
        claim_has_left = any(word.startswith(left) for word in claim_words)
        claim_has_right = any(word.startswith(right) for word in claim_words)
        evidence_has_left = any(word.startswith(left) for word in evidence_words)
        evidence_has_right = any(word.startswith(right) for word in evidence_words)
        if (claim_has_left and evidence_has_right) or (claim_has_right and evidence_has_left):
            return True
    return False
