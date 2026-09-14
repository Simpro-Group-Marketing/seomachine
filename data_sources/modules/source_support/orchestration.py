"""Orchestration responsibilities."""
from collections.abc import Mapping
from typing import Any, Callable, Optional

from .claim_matching import _general_claim_type
from .common import (
    GENERAL_CLAIM_TYPES,
    CitationRequirement,
    ClaimCandidate,
    Fetcher,
    Finding,
    List,
    Path,
    ProofEntry,
    ProofLinkReport,
    Sequence,
    _claim_text_for_detection,
    _extract_numeric_tokens,
    _normalize_numeric_token,
    analyze_proof_links,
    compose_with_sidecar,
    load_sidecar_content,
    should_fail,
    summarize_findings,
)
from .evidence_validation import _matching_proofs, _validate_proof_entry
from .findings import _finding, _known_customer_names
from .proof_parsing import _extract_claim_candidates, _extract_proof_entries
from .text_matching import (
    _normalize_text,
    _proof_matches_customer,
    _text_overlaps,
)


def _quote_candidate_finding(
    candidate: ClaimCandidate,
    matching_proofs: Sequence[ProofEntry],
    *,
    base_path: Path,
    fetcher: Optional[Fetcher],
    classification_options: dict[str, object],
) -> tuple[bool, Optional[Finding]]:
    if not candidate.requires_approved_quote:
        return False, None
    approved = [
        proof for proof in matching_proofs
        if proof.kind == "approved_quote" and proof.section == "customer proof pack"
    ]
    if approved:
        return True, _validate_proof_entry(
            approved[0], candidate, base_path=base_path, fetcher=fetcher,
            **classification_options,
        )
    return True, _finding(
        "quote_requires_approved_quote", candidate,
        "Exact quote or testimonial language requires an approved Customer Proof Pack quote row.",
        "Add an Approved quote row with Customer/brand, URL, Evidence, Status: approved, and source-visible quote evidence.",
    )


def _customer_metric_finding(
    candidate: ClaimCandidate,
    matching_proofs: Sequence[ProofEntry],
    *,
    base_path: Path,
    fetcher: Optional[Fetcher],
    classification_options: dict[str, object],
) -> tuple[bool, Optional[Finding]]:
    if not candidate.is_named_customer_metric:
        return False, None
    approved = [
        proof for proof in matching_proofs
        if proof.kind == "approved_metric" and proof.section == "customer proof pack"
    ]
    if approved:
        return True, _validate_proof_entry(
            approved[0], candidate, base_path=base_path, fetcher=fetcher,
            **classification_options,
        )
    proof_findings = [
        finding for finding in (
            _validate_proof_entry(
                proof, candidate, base_path=base_path, fetcher=fetcher,
                **classification_options,
            )
            for proof in matching_proofs
        )
        if finding is not None
    ]
    if proof_findings:
        return True, proof_findings[0]
    if matching_proofs:
        return True, _finding(
            "named_customer_metric_requires_approved_metric", candidate,
            "Named customer metrics must be approved in Customer Proof Pack Approved metrics.",
            "Move the customer metric into an Approved metric row with Customer/brand, URL, Evidence, and Status: approved.",
        )
    return True, _finding(
        "missing_strict_proof", candidate,
        "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
        "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
    )


def _general_candidate_finding(
    candidate: ClaimCandidate,
    matching_proofs: Sequence[ProofEntry],
    *,
    base_path: Path,
    fetcher: Optional[Fetcher],
    classification_options: dict[str, object],
) -> Optional[Finding]:
    if not matching_proofs:
        general = candidate.claim_type in GENERAL_CLAIM_TYPES
        return _finding(
            "general_claim_source_missing" if general else "missing_strict_proof",
            candidate,
            "General factual claims require a claim-fit approved Source Map row."
            if general else "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
            "Add Claim type, Source class, public URL, exact evidence, and approved status."
            if general else "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
        )
    proof_findings = [
        _validate_proof_entry(
            proof, candidate, base_path=base_path, fetcher=fetcher,
            **classification_options,
        )
        for proof in matching_proofs
    ]
    if any(finding is None for finding in proof_findings):
        return None
    return next(finding for finding in proof_findings if finding is not None)


def check_content(
    content: str,
    base_path: str | Path | None = None,
    fetcher: Optional[Fetcher] = None,
    proof_content: Optional[str] = None,
    fetch_many: Optional[Callable[[Sequence[str]], Mapping[str, Any]]] = None,
    registry_state: object | None = None,
    registry_snapshot: object | None = None,
    registry_verifier: Callable[..., None] | None = None,
) -> List[Finding]:
    """Return source-support findings for high-risk article claims."""
    base = Path(base_path) if base_path is not None else Path.cwd()
    proof_source = compose_with_sidecar(content, proof_content)
    proof_entries = _extract_proof_entries(proof_source)
    known_customer_names = _known_customer_names(proof_entries)
    candidates = _extract_claim_candidates(content, known_customer_names)
    policy_report = analyze_proof_links(content, proof_source)
    candidates = _policy_aligned_candidates(candidates, policy_report)
    fetcher = _resolve_source_fetcher(
        proof_entries,
        candidates,
        fetcher=fetcher,
        fetch_many=fetch_many,
    )
    classification_options = {
        "registry_state": registry_state,
        "registry_snapshot": registry_snapshot,
        "registry_verifier": registry_verifier,
    }

    findings: List[Finding] = []
    for candidate in candidates:
        matching_proofs = _matching_proofs(candidate, proof_entries)
        if candidate.has_numeric_tokens and not matching_proofs:
            cluster_applies, cluster_finding = _validate_numeric_proof_cluster(
                candidate,
                proof_entries,
                base_path=base,
                fetcher=fetcher,
                classification_options=classification_options,
            )
            if cluster_applies:
                if cluster_finding is not None:
                    findings.append(cluster_finding)
                continue
        handled, finding = _quote_candidate_finding(
            candidate, matching_proofs, base_path=base, fetcher=fetcher,
            classification_options=classification_options,
        )
        if handled:
            if finding:
                findings.append(finding)
            continue
        handled, finding = _customer_metric_finding(
            candidate, matching_proofs, base_path=base, fetcher=fetcher,
            classification_options=classification_options,
        )
        if handled:
            if finding:
                findings.append(finding)
            continue
        finding = _general_candidate_finding(
            candidate, matching_proofs, base_path=base, fetcher=fetcher,
            classification_options=classification_options,
        )
        if finding:
            findings.append(finding)

    return sorted(findings, key=lambda finding: (finding["line"], finding["column"], finding["rule_id"]))


def _resolve_source_fetcher(
    proof_entries: Sequence[ProofEntry],
    candidates: Sequence[ClaimCandidate],
    *,
    fetcher: Optional[Fetcher],
    fetch_many: Optional[Callable[[Sequence[str]], Mapping[str, Any]]],
) -> Optional[Fetcher]:
    if fetch_many is None:
        return fetcher
    return _prefetched_source_fetcher(
        proof_entries,
        candidates,
        fetch_many=fetch_many,
    )


def _prefetched_source_fetcher(
    proof_entries: Sequence[ProofEntry],
    candidates: Sequence[ClaimCandidate],
    *,
    fetch_many: Callable[[Sequence[str]], Mapping[str, Any]],
) -> Fetcher:
    """Fetch only candidate-matching HTML proof URLs once, preserving proof order."""
    urls: list[str] = []
    seen: set[str] = set()
    for proof in proof_entries:
        if (
            not proof.is_approved
            or proof.is_pdf
            or not proof.is_public_url
            or proof.url in seen
        ):
            continue
        if not any(_text_overlaps(candidate.text, proof) for candidate in candidates):
            continue
        seen.add(proof.url)
        urls.append(proof.url)
    fetched = dict(fetch_many(tuple(urls))) if urls else {}

    def fetch(url: str) -> str:
        value = fetched.get(url, RuntimeError("batched source result is missing"))
        if isinstance(value, Exception):
            raise value
        if not isinstance(value, str):
            raise TypeError("batched source result must be text or an Exception")
        return value

    return fetch

def _policy_aligned_candidates(
    candidates: Sequence[ClaimCandidate],
    report: ProofLinkReport,
) -> List[ClaimCandidate]:
    """Apply machine citation modes without weakening fail-closed claims."""
    proof_free_requirements = [
        requirement
        for requirement in report.requirements
        if requirement.owner == "public_research"
        and requirement.mode == "proof_not_required"
    ]
    faq_ranges = [
        (requirement.line, requirement.end_line)
        for requirement in report.requirements
        if requirement.owner == "faq"
    ]
    aligned = [
        candidate
        for candidate in candidates
        if not any(
            _requirement_has_candidate(requirement, (candidate,))
            for requirement in proof_free_requirements
        )
        and not any(start <= candidate.line <= end for start, end in faq_ranges)
        and not _candidate_is_proof_not_required(candidate)
    ]

    for requirement in report.requirements:
        if requirement.mode != "inline_required" or requirement.owner not in {
            "numeric_claim",
            "public_research",
        }:
            continue
        if _requirement_has_candidate(requirement, aligned):
            continue

        numeric_tokens = _extract_numeric_tokens(
            _claim_text_for_detection(requirement.claim)
        )
        aligned.append(
            ClaimCandidate(
                text=requirement.claim,
                line=requirement.line,
                numeric_tokens=numeric_tokens,
                normalized_tokens=frozenset(
                    _normalize_numeric_token(token) for token in numeric_tokens
                ),
                customer_names=frozenset(),
                has_case_study_link=False,
                requires_approved_quote=False,
                claim_type=(
                    ""
                    if numeric_tokens
                    else _general_claim_type(requirement.claim)
                ),
            )
        )

    return sorted(aligned, key=lambda candidate: (candidate.line, candidate.text))

def _candidate_is_proof_not_required(candidate: ClaimCandidate) -> bool:
    """Ask the policy engine whether one extracted sentence is fact-free advice."""
    fragment = f"# Editorial advice\n\n{candidate.text}\n"
    report = analyze_proof_links(fragment)
    return any(
        requirement.mode == "proof_not_required"
        and requirement.owner == "public_research"
        for requirement in report.requirements
    )

def _requirement_has_candidate(
    requirement: CitationRequirement,
    candidates: Sequence[ClaimCandidate],
) -> bool:
    requirement_text = _normalize_text(_claim_text_for_detection(requirement.claim))
    for candidate in candidates:
        if not requirement.line <= candidate.line <= requirement.end_line:
            continue
        candidate_text = _normalize_text(_claim_text_for_detection(candidate.text))
        if candidate_text in requirement_text or requirement_text in candidate_text:
            return True
    return False

def _validate_numeric_proof_cluster(
    candidate: ClaimCandidate,
    proof_entries: Sequence[ProofEntry],
    *,
    base_path: Path,
    fetcher: Optional[Fetcher],
    classification_options: dict[str, object],
) -> tuple[bool, Optional[Finding]]:
    """Validate multiple exact snippets that collectively prove one numeric unit."""
    partial_proofs: List[tuple[ProofEntry, List[str]]] = []
    covered_tokens: set[str] = set()
    for proof in proof_entries:
        if not proof.is_approved or not _text_overlaps(candidate.text, proof):
            continue
        if candidate.is_named_customer_claim and not _proof_matches_customer(candidate, proof):
            continue
        proof_tokens = proof.normalized_numeric_tokens
        matching_tokens = [
            token
            for token in candidate.numeric_tokens
            if _normalize_numeric_token(token) in proof_tokens
        ]
        if not matching_tokens:
            continue
        partial_proofs.append((proof, matching_tokens))
        covered_tokens.update(_normalize_numeric_token(token) for token in matching_tokens)

    if not candidate.normalized_tokens.issubset(covered_tokens):
        return False, None

    for proof, matching_tokens in partial_proofs:
        proof_candidate = ClaimCandidate(
            text=proof.claim,
            line=candidate.line,
            numeric_tokens=matching_tokens,
            normalized_tokens=frozenset(
                _normalize_numeric_token(token) for token in matching_tokens
            ),
            customer_names=candidate.customer_names,
            has_case_study_link=candidate.has_case_study_link,
            requires_approved_quote=False,
            claim_type="",
        )
        finding = _validate_proof_entry(
            proof,
            proof_candidate,
            base_path=base_path,
            fetcher=fetcher,
            **classification_options,
        )
        if finding is not None:
            return True, finding
    return True, None

def check_file(
    path: str | Path,
    fail_on: str = "error",
    fetcher: Optional[Fetcher] = None,
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a Markdown file for strict source-support findings."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        base_path=file_path.parent,
        fetcher=fetcher,
        proof_content=proof_content,
    )

def require_source_support(
    path: str | Path,
    context: str = "publish",
    fetcher: Optional[Fetcher] = None,
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Raise ValueError if strict source support fails for a file."""
    findings = check_file(
        path,
        fail_on="error",
        fetcher=fetcher,
        proof_sidecar=proof_sidecar,
    )
    if should_fail(findings, fail_on="error"):
        raise ValueError(
            f"Source support validation failed before {context}:\n"
            f"{format_findings(findings)}"
        )
    return findings

def format_findings(findings: Sequence[Finding]) -> str:
    """Format findings for preflight error output."""
    lines = [
        "=== Source Support Validation Report ===",
        f"Errors: {summarize_findings(findings)['error']}",
        f"Warnings: {summarize_findings(findings)['warning']}",
    ]
    if findings:
        lines.append("")
        lines.append("Blockers:")
        for finding in findings:
            lines.append(
                f"  - line {finding['line']}: {finding['rule_id']} - {finding['message']}"
            )
    return "\n".join(lines)

__all__ = [
    "check_content", "_policy_aligned_candidates", "_candidate_is_proof_not_required",
    "_requirement_has_candidate", "_validate_numeric_proof_cluster", "check_file",
    "require_source_support", "format_findings",
]
