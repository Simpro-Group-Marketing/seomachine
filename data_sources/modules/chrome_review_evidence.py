"""Chrome-backed review evidence for guarded URL-validation fallbacks.

This module is intentionally narrow. It exists for review-platform pages that
are reachable in a connected Chrome session but blocked by unauthenticated
HTTP validation, such as G2 pages protected by DataDome.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional
from urllib.parse import urlparse

try:
    from .blog_assembly_contract import validate_sha256
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import validate_sha256


SCHEMA = "chrome_review_evidence/v1"
APPROVED_STATUS = "approved for G2 403 validation fallback"
G2_REVIEW_URL_RE = re.compile(
    r"^https://www\.g2\.com/products/simpro/reviews/simpro-review-\d+/?$",
    re.IGNORECASE,
)
EVIDENCE_ARTIFACT_RE = re.compile(
    r"Evidence artifact:\s*`?(?P<path>[^`|\n]+?)`?\s*\|\s*SHA-256:\s*`?(?P<sha>[a-f0-9]{64})`?",
    re.IGNORECASE,
)
EVIDENCE_BINDING_RE = re.compile(
    r"URL:\s*`?(?P<url>https://www\.g2\.com/products/simpro/reviews/simpro-review-\d+/?)`?"
    r"\s*\|\s*Proof ID:\s*`?(?P<proof_id>[^`|\n]+?)`?"
    r"\s*\|\s*Claim ID:\s*`?(?P<claim_id>[^`|\n]+?)`?"
    r"\s*\|\s*Status:\s*(?P<status>[^|\n]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ChromeReviewEvidenceBinding:
    """A sidecar-bound Chrome review evidence artifact."""

    path: Path
    sha256: str
    url: str
    proof_id: str
    claim_id: str
    status: str


@dataclass(frozen=True)
class ChromeReviewEvidenceValidation:
    """Validation result for a single sidecar-bound evidence artifact."""

    passed: bool
    reason: str
    binding: Optional[ChromeReviewEvidenceBinding] = None


def apply_chrome_review_evidence_fallbacks(
    summary,
    *,
    proof_sidecar: str | Path | None,
    workspace_root: str | Path | None = None,
):
    """Return a URL summary with approved Chrome-backed G2 403s resolved.

    The return type is intentionally duck-typed to avoid importing the URL
    validator at module import time and creating cycles.
    """

    if proof_sidecar is None:
        return summary
    try:
        from .url_validator import UrlValidationResult, UrlValidationSummary
    except ImportError:  # pragma: no cover - supports direct script execution.
        from url_validator import UrlValidationResult, UrlValidationSummary

    root = Path(workspace_root or Path.cwd()).resolve()
    try:
        proof_content = Path(proof_sidecar).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return summary

    results = []
    for result in summary.results:
        if not _is_g2_datadome_block(result):
            results.append(result)
            continue
        validation = validate_sidecar_binding_for_url(
            proof_content,
            result.url,
            workspace_root=root,
        )
        if not validation.passed:
            results.append(result)
            continue
        results.append(
            UrlValidationResult(
                url=result.url,
                status="resolved",
                status_code=result.status_code,
                reason=f"{result.reason}; resolved by Chrome review evidence",
                line=result.line,
                anchor=result.anchor,
                final_url=result.final_url or result.url,
            )
        )
    return UrlValidationSummary(results)


def validate_sidecar_binding_for_url(
    proof_content: str,
    url: str,
    *,
    workspace_root: str | Path | None = None,
) -> ChromeReviewEvidenceValidation:
    """Validate that a sidecar binds approved Chrome evidence for a URL."""

    if not G2_REVIEW_URL_RE.match(_normalize_review_url(url)):
        return ChromeReviewEvidenceValidation(False, "url is not an approved G2 review URL")

    bindings = tuple(_sidecar_bindings(proof_content, workspace_root=workspace_root))
    matching = [binding for binding in bindings if _same_url(binding.url, url)]
    if not matching:
        return ChromeReviewEvidenceValidation(False, "sidecar has no matching Chrome review evidence binding")
    for binding in matching:
        validation = validate_evidence_artifact(binding)
        if validation.passed:
            return validation
    return ChromeReviewEvidenceValidation(False, "no matching Chrome review evidence artifact passed validation")


def validate_evidence_artifact(
    binding: ChromeReviewEvidenceBinding,
) -> ChromeReviewEvidenceValidation:
    """Validate one Chrome review evidence artifact and sidecar binding."""

    if binding.status.strip().casefold() != APPROVED_STATUS.casefold():
        return ChromeReviewEvidenceValidation(False, "sidecar binding status is not approved", binding)
    try:
        validate_sha256(binding.sha256, field="chrome_review_evidence.sha256")
    except ValueError as error:
        return ChromeReviewEvidenceValidation(False, str(error), binding)
    if not binding.path.is_file():
        return ChromeReviewEvidenceValidation(False, "chrome review evidence artifact is missing", binding)
    actual_sha = hashlib.sha256(binding.path.read_bytes()).hexdigest()
    if actual_sha != binding.sha256:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence artifact hash mismatch", binding)
    try:
        payload = json.loads(binding.path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return ChromeReviewEvidenceValidation(False, f"chrome review evidence artifact is unreadable: {error}", binding)

    if payload.get("schema") != SCHEMA:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence schema is unsupported", binding)
    if payload.get("status") != "evidence_captured":
        return ChromeReviewEvidenceValidation(False, "chrome review evidence status is not captured", binding)
    if not _same_url(str(payload.get("url") or ""), binding.url):
        return ChromeReviewEvidenceValidation(False, "chrome review evidence URL does not match sidecar binding", binding)
    if not _same_url(str(payload.get("final_url") or ""), binding.url):
        return ChromeReviewEvidenceValidation(False, "chrome review evidence final URL does not match sidecar binding", binding)
    if str(payload.get("proof_id") or "").strip() != binding.proof_id:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence proof ID does not match sidecar binding", binding)
    if str(payload.get("claim_id") or "").strip() != binding.claim_id:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence claim ID does not match sidecar binding", binding)
    if str(payload.get("browser_surface") or "").strip().casefold() != "connected_chrome":
        return ChromeReviewEvidenceValidation(False, "chrome review evidence browser surface is not connected_chrome", binding)

    required_text_fields = (
        "reviewer",
        "role",
        "segment",
        "review_date",
        "headline",
        "positive_text",
        "negative_text",
    )
    for field in required_text_fields:
        if not str(payload.get(field) or "").strip():
            return ChromeReviewEvidenceValidation(False, f"chrome review evidence missing {field}", binding)

    badges = payload.get("badges")
    if not isinstance(badges, list) or not badges:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence missing badges", binding)

    snapshot = str(payload.get("accessibility_snapshot") or "")
    snapshot_sha = str(payload.get("accessibility_snapshot_sha256") or "")
    if not snapshot.strip():
        return ChromeReviewEvidenceValidation(False, "chrome review evidence missing accessibility snapshot", binding)
    if hashlib.sha256(snapshot.encode("utf-8")).hexdigest() != snapshot_sha:
        return ChromeReviewEvidenceValidation(False, "chrome review evidence snapshot hash mismatch", binding)
    if str(payload.get("source_access") or "").strip().casefold() != "connected_chrome_loaded":
        return ChromeReviewEvidenceValidation(False, "chrome review evidence source access is not connected_chrome_loaded", binding)
    return ChromeReviewEvidenceValidation(True, "chrome review evidence validated", binding)


def _sidecar_bindings(
    proof_content: str,
    *,
    workspace_root: str | Path | None,
) -> Iterable[ChromeReviewEvidenceBinding]:
    root = Path(workspace_root or Path.cwd()).resolve()
    lines = proof_content.splitlines()
    for index, line in enumerate(lines):
        artifact_match = EVIDENCE_ARTIFACT_RE.search(line)
        if artifact_match is None:
            continue
        path = Path(artifact_match.group("path").strip())
        if not path.is_absolute():
            path = root / path
        sha = artifact_match.group("sha").strip().lower()
        for follow in lines[index + 1 : index + 4]:
            binding_match = EVIDENCE_BINDING_RE.search(follow)
            if binding_match is None:
                continue
            yield ChromeReviewEvidenceBinding(
                path=path.resolve(strict=False),
                sha256=sha,
                url=_normalize_review_url(binding_match.group("url")),
                proof_id=binding_match.group("proof_id").strip(),
                claim_id=binding_match.group("claim_id").strip(),
                status=binding_match.group("status").strip(),
            )
            break


def _is_g2_datadome_block(result) -> bool:
    return (
        str(getattr(result, "status", "")).casefold() == "manual_review"
        and getattr(result, "status_code", None) == 403
        and G2_REVIEW_URL_RE.match(_normalize_review_url(str(getattr(result, "url", "") or ""))) is not None
    )


def _same_url(left: str, right: str) -> bool:
    return _normalize_review_url(left) == _normalize_review_url(right)


def _normalize_review_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return f"{scheme}://{netloc}{path}"
