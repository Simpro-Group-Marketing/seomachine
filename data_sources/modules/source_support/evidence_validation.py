"""Evidence Validation responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _matching_proofs(
    candidate: ClaimCandidate,
    proof_entries: Sequence[ProofEntry],
) -> List[ProofEntry]:
    matches = []
    for proof in proof_entries:
        if not proof.is_approved:
            continue
        if candidate.has_numeric_tokens:
            if not candidate.normalized_tokens.issubset(proof.normalized_numeric_tokens):
                continue
            if not _text_overlaps(candidate.text, proof):
                continue
        if candidate.is_named_customer_claim and not _proof_matches_customer(candidate, proof):
            continue
        if not candidate.has_numeric_tokens and not _text_overlaps(candidate.text, proof):
            continue
        matches.append(proof)
    return matches


def _validate_general_source(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> Optional[Finding]:
    if proof.source_class not in SOURCE_CLASSES:
        return _finding(
            "source_class_invalid", candidate,
            "General claim proof must use one exact supported Source class.",
            "Use primary_authority, independent_research, non_competing_expert, or another contract class that fits the claim.", proof,
        )
    if proof.claim_type != candidate.claim_type:
        return _finding(
            "source_claim_type_mismatch", candidate,
            "Source Map Claim type does not fit the public claim.",
            f"Set Claim type to {candidate.claim_type} or use a different supporting row.", proof,
        )
    contract_finding = _validate_general_claim_contract(proof, candidate)
    if contract_finding:
        return contract_finding
    classification_finding = _validate_source_classification(proof, candidate, base_path)
    if classification_finding:
        return classification_finding
    allowed = set(GENERAL_SOURCE_CLASSES)
    if candidate.claim_type == "comparative":
        allowed.add("competitor")
    if (
        candidate.claim_type in OWNED_PRODUCT_GENERAL_CLAIM_TYPES
        and re.search(r"\bSimpro\b", candidate.text, re.IGNORECASE)
    ):
        allowed.add("owned_product")
    if proof.source_class in allowed:
        return None
    return _finding(
        "source_class_claim_fit_invalid", candidate,
        "The selected Source class cannot support this general claim type.",
        "Use an authority, independent research, or non-competing expert source with visible claim-fit evidence.", proof,
    )


def _load_html_source_text(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    fetcher: Optional[Fetcher],
) -> tuple[Optional[str], Optional[Finding], bool]:
    try:
        return (
            fetcher(proof.url) if fetcher is not None else fetch_source_text(proof.url),
            None,
            False,
        )
    except Exception as error:  # fail closed on fetch errors
        if not proof.artifact:
            return None, _finding(
                "source_fetch_failed", candidate,
                f"Could not fetch cited source text: {error}",
                "Fix the source URL, add a local proof artifact for non-HTML evidence, or remove the claim.", proof,
            ), False
        source_text = _read_artifact_text(proof, base_path)
        if source_text is None:
            return None, _finding(
                "proof_artifact_missing", candidate,
                "The local proof artifact for this source does not exist or is unsupported.",
                "Create the referenced .md/.txt/.csv/.tsv/.json proof artifact or remove the claim.", proof,
            ), False
        finding = _validate_capture_receipt(
            proof, candidate, base_path, expected_method="html_visible_text"
        )
        if finding:
            return None, finding, False
        return source_text, _validate_source_text_contains_evidence(
            source_text, proof, candidate
        ), True


def _load_pdf_source_text(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
) -> tuple[Optional[str], Optional[Finding], bool]:
    if not proof.artifact:
        return None, _finding(
            "unsupported_pdf_source", candidate,
            "PDF sources require a local text proof artifact in v1.",
            "Add Artifact: path/to/proof.md with the extracted evidence snippet, or use an HTML source.", proof,
        ), False
    source_text = _read_artifact_text(proof, base_path)
    if source_text is None:
        return None, _finding(
            "proof_artifact_missing", candidate,
            "The local proof artifact for this PDF source does not exist or is unsupported.",
            "Create the referenced .md/.txt/.csv/.tsv/.json proof artifact or remove the claim.", proof,
        ), False
    finding = _validate_capture_receipt(
        proof, candidate, base_path, expected_method="pdf_text"
    )
    return (None, finding, False) if finding else (source_text, None, False)


def _validate_public_source_url(
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    if not proof.url or INSUFFICIENT_SOURCE_RE.search(proof.url):
        return _finding(
            "missing_strict_proof", candidate,
            "Strict proof must use a public URL, not an internal context path or placeholder.",
            "Use the public source URL that visibly supports the claim.", proof,
        )
    if not proof.is_public_url:
        return _finding(
            "source_url_not_public", candidate,
            "Strict proof must use a public HTTP or HTTPS URL.",
            "Replace the source with its canonical public HTTP or HTTPS URL.", proof,
        )
    return None


def _validate_proof_entry(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    fetcher: Optional[Fetcher],
) -> Optional[Finding]:
    if candidate.claim_type in GENERAL_CLAIM_TYPES:
        finding = _validate_general_source(proof, candidate, base_path)
        if finding:
            return finding
    url_finding = _validate_public_source_url(proof, candidate)
    if url_finding:
        return url_finding

    source_text, source_finding, terminal = (
        _load_pdf_source_text(proof, candidate, base_path)
        if proof.is_pdf
        else _load_html_source_text(proof, candidate, base_path, fetcher)
    )
    if source_finding:
        return source_finding
    if terminal:
        return None
    assert source_text is not None

    evidence_finding = _validate_source_text_contains_evidence(source_text, proof, candidate)
    if evidence_finding:
        return evidence_finding

    if candidate.claim_type in GENERAL_CLAIM_TYPES:
        fit_finding = _validate_evidence_claim_fit(proof, candidate)
        if fit_finding:
            return fit_finding

    if candidate.has_numeric_tokens and not candidate.normalized_tokens.issubset(proof.normalized_numeric_tokens):
        return _finding(
            "evidence_missing_numeric_token",
            candidate,
            "The proof evidence does not contain the numeric token used in the claim.",
            "Use evidence that contains the same number, or remove the unsupported number from the claim.",
            proof,
        )

    return None


__all__ = ["_matching_proofs", "_validate_proof_entry", "_validate_general_claim_contract"]

def _validate_general_claim_contract(
    proof: ProofEntry,
    candidate: ClaimCandidate,
) -> Optional[Finding]:
    article_claim = _normalize_text(_claim_text_for_detection(candidate.text))
    mapped_claim = _normalize_text(proof.claim)
    if article_claim != mapped_claim:
        return _finding(
            "source_claim_binding_mismatch",
            candidate,
            "The Source Map Claim must exactly bind the public general claim.",
            "Copy the complete public claim into Claim or use a separate row for each claim.",
            proof,
        )
    if proof.evidence_relation != "directly_supports":
        return _finding(
            "source_evidence_relation_invalid",
            candidate,
            "General claim proof must declare Evidence relation: directly_supports.",
            "Use directly_supports only when the source-visible evidence entails the mapped claim.",
            proof,
        )
    return None
