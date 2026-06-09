"""
Source Support Guard

Strict source-support validation for high-risk public claims. This guard goes
beyond link presence: a claim must map to an approved proof row whose evidence
snippet is visible in the cited source text or local proof artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import requests
from bs4 import BeautifulSoup

try:
    from diskcache import Cache
except ImportError:  # pragma: no cover - dependency is declared, fallback is defensive.
    Cache = None

try:
    from .numeric_claim_source_guard import (
        MARKDOWN_LINK_RE,
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _normalize_numeric_token,
        _strip_frontmatter_preserve_lines,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from numeric_claim_source_guard import (
        MARKDOWN_LINK_RE,
        _blank_fenced_code,
        _claim_text_for_detection,
        _extract_numeric_tokens,
        _is_candidate_claim,
        _iter_paragraphs,
        _normalize_numeric_token,
        _strip_frontmatter_preserve_lines,
    )


Finding = Dict[str, object]
Fetcher = Callable[[str], str]


DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 SEO-Machine-Source-Support/1.0"
)
PDF_EXTENSION_RE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)
LOCAL_ARTIFACT_EXTENSION_RE = re.compile(r"\.(?:md|txt|csv|tsv|json)$", re.IGNORECASE)
PROOF_ROW_RE = re.compile(r"^\s*(?:[-*+]\s+)?(?P<body>(?:Claim|Approved metric)\s*:.*)$", re.IGNORECASE)
SECTION_RE = re.compile(r"^\s*(?:#{1,4}\s+)?(?P<section>[A-Za-z][A-Za-z /-]+):?\s*$")

OUTCOME_SIGNAL_RE = re.compile(
    r"\b(?:achieved|increased|improved|reduced|saved|generated|lifted|grew|"
    r"doubled|tripled|processed?|centralized|transformed|can process|"
    r"profit|profits|margin|margins|revenue|resources|efficiency|"
    r"productivity|business)\b",
    re.IGNORECASE,
)

INSUFFICIENT_SOURCE_RE = re.compile(
    r"\b(?:context/|@context|source map|proof pack|industry standard|"
    r"FDD conventions|no anchor)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClaimCandidate:
    text: str
    line: int
    numeric_tokens: List[str]
    normalized_tokens: frozenset[str]
    customer_names: frozenset[str]
    has_case_study_link: bool

    @property
    def has_numeric_tokens(self) -> bool:
        return bool(self.numeric_tokens)

    @property
    def is_named_customer_claim(self) -> bool:
        return self.has_case_study_link or bool(self.customer_names)

    @property
    def is_named_customer_metric(self) -> bool:
        return self.is_named_customer_claim and self.has_numeric_tokens


@dataclass(frozen=True)
class ProofEntry:
    kind: str
    claim: str
    url: str
    evidence: str
    status: str
    line: int
    section: str
    customer: str = ""
    artifact: str = ""
    use: str = ""

    @property
    def is_approved(self) -> bool:
        return self.status.lower() == "approved"

    @property
    def is_public_url(self) -> bool:
        return self.url.startswith("http://") or self.url.startswith("https://")

    @property
    def is_pdf(self) -> bool:
        return bool(PDF_EXTENSION_RE.search(self.url))

    @property
    def normalized_numeric_tokens(self) -> frozenset[str]:
        tokens = _extract_numeric_tokens(_claim_text_for_detection(self.evidence))
        return frozenset(_normalize_numeric_token(token) for token in tokens)


class SourceSupportError(Exception):
    """Raised when source-support validation blocks publishing."""


def check_content(
    content: str,
    base_path: str | Path | None = None,
    fetcher: Optional[Fetcher] = None,
) -> List[Finding]:
    """Return source-support findings for high-risk article claims."""
    base = Path(base_path) if base_path is not None else Path.cwd()
    proof_entries = _extract_proof_entries(content)
    known_customer_names = _known_customer_names(proof_entries)
    candidates = _extract_claim_candidates(content, known_customer_names)

    findings: List[Finding] = []
    for candidate in candidates:
        matching_proofs = _matching_proofs(candidate, proof_entries)
        if candidate.is_named_customer_metric:
            approved_metric_proofs = [
                proof
                for proof in matching_proofs
                if proof.kind == "approved_metric" and proof.section == "customer proof pack"
            ]
            if approved_metric_proofs:
                proof_finding = _validate_proof_entry(
                    approved_metric_proofs[0],
                    candidate,
                    base_path=base,
                    fetcher=fetcher,
                )
                if proof_finding:
                    findings.append(proof_finding)
                continue

            proof_findings = [
                proof_finding
                for proof_finding in (
                    _validate_proof_entry(
                        proof,
                        candidate,
                        base_path=base,
                        fetcher=fetcher,
                    )
                    for proof in matching_proofs
                )
                if proof_finding is not None
            ]
            if proof_findings:
                findings.append(proof_findings[0])
                continue

            if matching_proofs:
                findings.append(_finding(
                    "named_customer_metric_requires_approved_metric",
                    candidate,
                    "Named customer metrics must be approved in Customer Proof Pack Approved metrics.",
                    (
                        "Move the customer metric into an Approved metric row with "
                        "Customer/brand, URL, Evidence, and Status: approved."
                    ),
                ))
                continue
            findings.append(_finding(
                "missing_strict_proof",
                candidate,
                "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
                "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
            ))
            continue

        if not matching_proofs:
            findings.append(_finding(
                "missing_strict_proof",
                candidate,
                "High-risk claims need an approved strict proof row with Claim, URL, Evidence, and Status: approved.",
                "Add a structured proof row with public URL, exact evidence snippet, and approved status.",
            ))
            continue

        selected_proof = matching_proofs[0]
        proof_finding = _validate_proof_entry(
            selected_proof,
            candidate,
            base_path=base,
            fetcher=fetcher,
        )
        if proof_finding:
            findings.append(proof_finding)

    return sorted(findings, key=lambda finding: (finding["line"], finding["column"], finding["rule_id"]))


def check_file(
    path: str | Path,
    fail_on: str = "error",
    fetcher: Optional[Fetcher] = None,
) -> List[Finding]:
    """Check a Markdown file for strict source-support findings."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    file_path = Path(path)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        base_path=file_path.parent,
        fetcher=fetcher,
    )


def require_source_support(
    path: str | Path,
    context: str = "publish",
    fetcher: Optional[Fetcher] = None,
) -> List[Finding]:
    """Raise ValueError if strict source support fails for a file."""
    findings = check_file(path, fail_on="error", fetcher=fetcher)
    if should_fail(findings, fail_on="error"):
        raise ValueError(
            f"Source support validation failed before {context}:\n"
            f"{format_findings(findings)}"
        )
    return findings


def should_fail(findings: Sequence[Finding], fail_on: str = "error") -> bool:
    """Return True when findings meet the configured failure threshold."""
    if fail_on == "none":
        return False
    if fail_on == "warning":
        return any(finding["severity"] in {"warning", "error"} for finding in findings)
    if fail_on == "error":
        return any(finding["severity"] == "error" for finding in findings)
    raise ValueError("fail_on must be one of: error, warning, none")


def summarize_findings(findings: Sequence[Finding]) -> Dict[str, int]:
    """Count source-support findings by severity."""
    summary = {"error": 0, "warning": 0}
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


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


def fetch_source_text(url: str) -> str:
    """Fetch and normalize visible source text from an HTML URL."""
    cache = _cache()
    cache_key = _cache_key(url)
    if cache is not None and cache_key in cache:
        return str(cache[cache_key])

    response = requests.get(
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    text = _extract_visible_text(response.text)
    if cache is not None:
        cache.set(cache_key, text, expire=60 * 60 * 24)
    return text


def _extract_proof_entries(content: str) -> List[ProofEntry]:
    entries: List[ProofEntry] = []
    section = ""

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        section_match = SECTION_RE.match(stripped)
        if section_match and not stripped.startswith("-"):
            section = _normalize_section(section_match.group("section"))

        row_match = PROOF_ROW_RE.match(stripped)
        if not row_match:
            continue

        fields = _parse_proof_fields(row_match.group("body"))
        kind = "approved_metric" if "approved metric" in fields else "claim"
        claim = fields.get("approved metric") or fields.get("claim", "")
        url = fields.get("url", "")
        evidence = fields.get("evidence", "")
        status = fields.get("status", "")
        if not claim or not evidence:
            continue

        entries.append(
            ProofEntry(
                kind=kind,
                claim=claim,
                url=url,
                evidence=evidence,
                status=status,
                line=line_number,
                section=section,
                customer=fields.get("customer/brand", "") or fields.get("customer", ""),
                artifact=(
                    fields.get("artifact", "")
                    or fields.get("proof artifact", "")
                    or fields.get("local proof artifact", "")
                ),
                use=fields.get("use", ""),
            )
        )

    return entries


def _parse_proof_fields(row_body: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    for segment in row_body.split("|"):
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        fields[_normalize_key(key)] = _clean_field_value(value)
    return fields


def _extract_claim_candidates(
    content: str,
    known_customer_names: Sequence[str],
) -> List[ClaimCandidate]:
    body = _strip_frontmatter_preserve_lines(content)
    body = _blank_fenced_code(body)
    candidates: List[ClaimCandidate] = []

    for paragraph in _iter_paragraphs(body):
        numeric_tokens = []
        if _is_candidate_claim(paragraph.text):
            numeric_tokens = _extract_numeric_tokens(_claim_text_for_detection(paragraph.text))

        names = _customer_names_in_text(paragraph.text, known_customer_names)
        has_case_study_link = _has_case_study_link(paragraph.text)
        is_named_outcome = (
            (has_case_study_link or bool(names))
            and bool(OUTCOME_SIGNAL_RE.search(_claim_text_for_detection(paragraph.text)))
        )

        if not numeric_tokens and not is_named_outcome:
            continue

        candidates.append(
            ClaimCandidate(
                text=paragraph.text.strip(),
                line=paragraph.line,
                numeric_tokens=numeric_tokens,
                normalized_tokens=frozenset(_normalize_numeric_token(token) for token in numeric_tokens),
                customer_names=frozenset(names),
                has_case_study_link=has_case_study_link,
            )
        )

    return candidates


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


def _validate_proof_entry(
    proof: ProofEntry,
    candidate: ClaimCandidate,
    base_path: Path,
    fetcher: Optional[Fetcher],
) -> Optional[Finding]:
    if not proof.url or INSUFFICIENT_SOURCE_RE.search(proof.url):
        return _finding(
            "missing_strict_proof",
            candidate,
            "Strict proof must use a public URL, not an internal context path or placeholder.",
            "Use the public source URL that visibly supports the claim.",
            proof,
        )

    if proof.is_pdf:
        if not proof.artifact:
            return _finding(
                "unsupported_pdf_source",
                candidate,
                "PDF sources require a local text proof artifact in v1.",
                "Add Artifact: path/to/proof.md with the extracted evidence snippet, or use an HTML source.",
                proof,
            )
        source_text = _read_artifact_text(proof, base_path)
        if source_text is None:
            return _finding(
                "proof_artifact_missing",
                candidate,
                "The local proof artifact for this PDF source does not exist or is unsupported.",
                "Create the referenced .md/.txt/.csv/.tsv/.json proof artifact or remove the claim.",
                proof,
            )
    else:
        try:
            source_text = fetcher(proof.url) if fetcher is not None else fetch_source_text(proof.url)
        except Exception as exc:  # fail closed on fetch errors
            return _finding(
                "source_fetch_failed",
                candidate,
                f"Could not fetch cited source text: {exc}",
                "Fix the source URL, add a local proof artifact for non-HTML evidence, or remove the claim.",
                proof,
            )

    if not _contains_evidence(source_text, proof.evidence):
        return _finding(
            "source_evidence_not_found",
            candidate,
            "Proof evidence was not found in the cited source.",
            "Replace the claim with source-visible wording, update Evidence to an exact visible snippet, or remove the claim.",
            proof,
        )

    if candidate.has_numeric_tokens and not candidate.normalized_tokens.issubset(proof.normalized_numeric_tokens):
        return _finding(
            "evidence_missing_numeric_token",
            candidate,
            "The proof evidence does not contain the numeric token used in the claim.",
            "Use evidence that contains the same number, or remove the unsupported number from the claim.",
            proof,
        )

    return None


def _read_artifact_text(proof: ProofEntry, base_path: Path) -> Optional[str]:
    artifact_path = Path(proof.artifact)
    if not artifact_path.is_absolute():
        artifact_path = base_path / artifact_path
    resolved = artifact_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        return None
    if not LOCAL_ARTIFACT_EXTENSION_RE.search(resolved.name):
        return None
    return resolved.read_text(encoding="utf-8")


def _finding(
    rule_id: str,
    candidate: ClaimCandidate,
    message: str,
    suggestion: str,
    proof: Optional[ProofEntry] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": "error",
        "line": candidate.line,
        "column": 1,
        "match": candidate.text,
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
        for value in (proof.customer, proof.claim):
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


def _cache():
    if Cache is None:
        return None
    return Cache(str(Path(".cache") / "source_support_guard"))


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


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


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check source evidence supports high-risk claims.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on)
    payload = {
        "path": args.path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
