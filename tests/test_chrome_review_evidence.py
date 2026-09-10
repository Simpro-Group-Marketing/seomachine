import hashlib
import json
from pathlib import Path

from data_sources.modules.chrome_review_evidence import (
    apply_chrome_review_evidence_fallbacks,
    validate_sidecar_binding_for_url,
)
from data_sources.modules.url_validator import UrlValidationResult, UrlValidationSummary


G2_URL = "https://www.g2.com/products/simpro/reviews/simpro-review-4999982"
PROOF_ID = "review-g2-commercial-plumbing-call-to-invoice-fergus"
CLAIM_ID = "claim-metric-MET-1148"
SNAPSHOT = """0 AXWebArea G2, URL: g2.com/products/simpro/reviews/simpro-review-4999982
55 container focused-review
57 text Matthew N.
58 text Managing Director
59 text Small-Business (50 or fewer emp.)
60 text 9/13/2021
62 text "Professional software for our commercial plumbing company"
65 text What do you like best about Simpro? Custom workflow set up, prebuilds and deep reporting.
67 text What do you dislike about Simpro? Scheduling is pretty clunky."""


def _write_evidence(tmp_path: Path, *, url: str = G2_URL, claim_id: str = CLAIM_ID) -> Path:
    payload = {
        "schema": "chrome_review_evidence/v1",
        "status": "evidence_captured",
        "url": url,
        "final_url": url,
        "proof_id": PROOF_ID,
        "claim_id": claim_id,
        "browser_surface": "connected_chrome",
        "source_access": "connected_chrome_loaded",
        "checked_at": "2026-09-08T18:57:00Z",
        "reviewer": "Matthew N.",
        "role": "Managing Director",
        "segment": "Small-Business (50 or fewer emp.)",
        "review_date": "2021-09-13",
        "headline": "Professional software for our commercial plumbing company",
        "positive_text": "Custom workflow set up, prebuilds and deep reporting.",
        "negative_text": "Scheduling is pretty clunky.",
        "badges": ["Current User", "Validated Reviewer"],
        "accessibility_snapshot": SNAPSHOT,
        "accessibility_snapshot_sha256": hashlib.sha256(SNAPSHOT.encode("utf-8")).hexdigest(),
    }
    path = tmp_path / "research" / "g2-review-chrome-evidence.json"
    path.parent.mkdir()
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    return path


def _sidecar(path: Path, *, url: str = G2_URL, claim_id: str = CLAIM_ID, sha: str | None = None) -> str:
    digest = sha or hashlib.sha256(path.read_bytes()).hexdigest()
    rel = path.as_posix()
    return f"""## Chrome Review Evidence

- Evidence artifact: `{rel}` | SHA-256: `{digest}`
- URL: `{url}` | Proof ID: `{PROOF_ID}` | Claim ID: `{claim_id}` | Status: approved for G2 403 validation fallback
"""


def test_g2_403_with_matching_chrome_evidence_passes(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path)
    summary = UrlValidationSummary([
        UrlValidationResult(
            url=G2_URL,
            status="manual_review",
            status_code=403,
            reason="HTTP 403",
            line=12,
            anchor="G2 review from Matthew N.",
        )
    ])
    proof = tmp_path / "validation.md"
    proof.write_text(_sidecar(evidence), encoding="utf-8")

    result = apply_chrome_review_evidence_fallbacks(
        summary,
        proof_sidecar=proof,
        workspace_root=tmp_path,
    )

    assert result.passed is True
    assert result.results[0].status == "resolved"
    assert "Chrome review evidence" in result.results[0].reason


def test_g2_403_without_chrome_evidence_stays_blocked(tmp_path: Path) -> None:
    proof = tmp_path / "validation.md"
    proof.write_text("## Chrome Review Evidence\n", encoding="utf-8")
    summary = UrlValidationSummary([
        UrlValidationResult(G2_URL, "manual_review", 403, "HTTP 403")
    ])

    result = apply_chrome_review_evidence_fallbacks(
        summary,
        proof_sidecar=proof,
        workspace_root=tmp_path,
    )

    assert result.passed is False
    assert result.results[0].status == "manual_review"


def test_g2_403_with_mismatched_claim_binding_stays_blocked(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path)
    proof = tmp_path / "validation.md"
    proof.write_text(_sidecar(evidence, claim_id="claim-other"), encoding="utf-8")

    validation = validate_sidecar_binding_for_url(
        proof.read_text(encoding="utf-8"),
        G2_URL,
        workspace_root=tmp_path,
    )

    assert validation.passed is False


def test_non_g2_403_stays_blocked_even_with_chrome_evidence(tmp_path: Path) -> None:
    evidence = _write_evidence(tmp_path)
    proof = tmp_path / "validation.md"
    proof.write_text(_sidecar(evidence), encoding="utf-8")
    summary = UrlValidationSummary([
        UrlValidationResult(
            "https://example.com/forbidden",
            "manual_review",
            403,
            "HTTP 403",
        )
    ])

    result = apply_chrome_review_evidence_fallbacks(
        summary,
        proof_sidecar=proof,
        workspace_root=tmp_path,
    )

    assert result.passed is False
    assert result.results[0].status == "manual_review"
