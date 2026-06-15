"""
Review Story Identity Guard

Review-derived E-E-A-T story language can appear in public copy only when the
story is tied to a real person or business, has a public review URL, and the
article links that URL in the same paragraph as the paraphrased story.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content


DEFAULT_INDEX_PATH = Path("context/customer-proof-index.json")

REVIEW_STORY_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Review Story Selection:?\s*$",
    re.IGNORECASE,
)
REVIEW_SITE_THEME_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Review Site Theme Selection:?\s*$",
    re.IGNORECASE,
)
NEXT_PROOF_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Pack|E-E-A-T Proof Map|FAQ Proof Map|Structured data plan|"
    r"Review Story Selection|Review Site Theme Selection)\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
EXACT_QUOTE_RE = re.compile(r"(?:\"[^\"]{20,}\"|\u201c[^\u201d]{20,}\u201d)")
URL_RE = re.compile(r"https?://[^\s),|]+", re.IGNORECASE)
REVIEW_SITE_URL_RE = re.compile(
    r"https?://[^\s)]*(?:g2\.com|capterra\.com|softwareadvice\.com|getapp\.com|"
    r"trustradius\.com|gartner(?:digitalmarkets)?\.com|trustpilot\.com|"
    r"apps\.apple\.com|play\.google\.com)[^\s)]*",
    re.IGNORECASE,
)
REVIEW_LANGUAGE_RE = re.compile(
    r"\b(?:g2|capterra|software advice|softwareadvice|getapp|trustradius|"
    r"gartner|trustpilot|google review|app store|reviewer|reviewers|review-site|"
    r"review site|customer review|review story)\b",
    re.IGNORECASE,
)
REVIEW_RATING_RANKING_CLAIM_RE = re.compile(
    r"\b(?:star ratings?|ratings?|rated|ranking|rankings?|ranked|badges?|"
    r"named reviewer|reviewer name|reviewer-name|category claims?)\b|"
    r"\b\d+(?:\.\d+)?\s*(?:out of\s*)?(?:stars?|ratings?|reviews?|%)\b",
    re.IGNORECASE,
)
ALLOWED_IDENTITY_TYPES = {"person", "business", "person_and_business"}


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    source_path: str | Path | None = None,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
) -> List[Finding]:
    """Return review-story identity and public-link findings."""
    del source_path
    composed = compose_with_sidecar(content, proof_content)
    public_content = _public_copy_content(content)
    selection = _extract_review_story_selection(composed)
    theme_selection = _extract_review_site_theme_selection(composed)
    findings: List[Finding] = []
    has_review_story_signal = _has_review_story_signal(public_content)

    if has_review_story_signal and selection is None:
        return _review_signal_without_story_selection_findings(
            public_content,
            theme_selection,
            proof_content or "",
        )

    if selection is None:
        return findings

    findings.extend(
        _review_story_selection_findings(
            content,
            public_content,
            selection,
            proof_content or "",
            proof_index_path,
        )
    )

    return sorted(findings, key=lambda finding: (finding["severity"] != "error", finding["line"], finding["rule_id"]))


def _review_signal_without_story_selection_findings(
    public_content: str,
    theme_selection: Optional[Dict[str, object]],
    proof_content: str,
) -> List[Finding]:
    if theme_selection is not None:
        findings = _review_theme_findings(public_content, theme_selection, proof_content)
        return sorted(findings, key=lambda finding: (finding["severity"] != "error", finding["line"], finding["rule_id"]))
    return [
        _finding(
            "review_story_selection_missing",
            _first_review_signal_line(public_content),
            "Review-derived public copy appears without a Review Story Selection block.",
            (
                "Add a Review Story Selection block to the validation sidecar, "
                "or remove the review-derived story language from public copy."
            ),
        )
    ]


def _review_story_selection_findings(
    content: str,
    public_content: str,
    selection: Dict[str, object],
    proof_content: str,
    proof_index_path: str | Path,
) -> List[Finding]:
    findings: List[Finding] = []
    selected = selection.get("selected_story", {})
    proof_id = str(selected.get("proof_id", "")).strip()
    if not proof_id:
        return [
            _finding(
                "review_story_selection_incomplete",
                int(selection["line"]),
                "Review Story Selection is missing a selected proof_id.",
                "Use `Selected story: [proof_id] | Identity: ... | URL: ... | Status: approved`.",
            )
        ]

    index_row = _find_index_row(proof_index_path, proof_id)
    story = index_row.get("review_story", {}) if isinstance(index_row, dict) else {}
    if not isinstance(story, dict):
        story = {}

    sidecar_identity = str(selected.get("identity", "")).strip()
    index_identity = _story_identity(story)
    identity = sidecar_identity or index_identity
    identity_type = str(story.get("identity_type", "")).strip().lower()
    sidecar_url = str(selected.get("url", "")).strip()
    index_url = str(story.get("public_url") or (index_row or {}).get("public_url") or "").strip()
    public_url = sidecar_url or index_url
    status = str(selected.get("status", "")).strip().lower()
    story_allowed = story.get("story_allowed") is True

    if index_row is None:
        findings.append(
            _finding(
                "review_story_index_missing",
                int(selection["line"]),
                f"Selected review story was not found in customer-proof-index.json: {proof_id}",
                "Add the selected proof_id to context/customer-proof-index.json or choose an indexed story.",
                match=proof_id,
            )
        )

    if status != "approved":
        findings.append(
            _finding(
                "review_story_not_approved",
                int(selection["line"]),
                "Selected review story is not marked Status: approved.",
                "Mark the selected review story Status: approved only after identity and public URL checks pass.",
                match=status or "missing",
            )
        )

    if not identity or identity_type not in ALLOWED_IDENTITY_TYPES:
        findings.append(
            _finding(
                "review_story_identity_missing",
                int(selection["line"]),
                "Selected review story does not have a real person or business identity.",
                "Use a review row with identity_type person, business, or person_and_business and a named identity.",
                match=proof_id,
            )
        )

    if not public_url.startswith(("http://", "https://")):
        findings.append(
            _finding(
                "review_story_public_url_missing",
                int(selection["line"]),
                "Selected review story does not have a usable public review URL.",
                "Keep internal-only or no-URL review rows as research only until a public review URL exists.",
                match=proof_id,
            )
        )
    elif sidecar_url and index_url and _normalize_url(sidecar_url) != _normalize_url(index_url):
        findings.append(
            _finding(
                "review_story_url_mismatch",
                int(selection["line"]),
                "Review Story Selection URL does not match the indexed review story URL.",
                "Update the sidecar URL or customer-proof-index.json so they point to the same public review source.",
                match=sidecar_url,
            )
        )

    if not story_allowed:
        if public_url.startswith(("http://", "https://")) and identity:
            findings.append(
                _finding(
                    "review_story_not_public_copy_allowed",
                    int(selection["line"]),
                    "Indexed review story is not allowed for public E-E-A-T story use.",
                    "Set review_story.story_allowed true only after identity and public URL checks pass.",
                    match=proof_id,
                )
            )

    if public_url.startswith(("http://", "https://")) and identity:
        linked_paragraph = _paragraph_with_url_and_identity(public_content, public_url, identity)
        if linked_paragraph is None:
            findings.append(
                _finding(
                    "review_story_link_missing",
                    _first_review_signal_line(public_content),
                    "Selected review story URL is not linked in the same public paragraph as the review-derived paraphrase.",
                    "Link the selected public review URL in the same paragraph that names or paraphrases the review story.",
                    match=public_url,
                )
            )

    if _has_unapproved_review_quote(public_content, public_url, identity, proof_content or ""):
        findings.append(
            _finding(
                "review_quote_requires_approved_quote",
                _first_quote_line(content),
                "Exact review wording appears without an approved quote row.",
                (
                    "Add an Approved quote row with source type, URL or source ref, "
                    "Evidence, identity, Status: approved, and intended Use; otherwise paraphrase."
                ),
            )
        )

    return findings


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    proof_index_path: str | Path = DEFAULT_INDEX_PATH,
) -> List[Finding]:
    """Check a public article file plus optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        source_path=file_path,
        proof_index_path=proof_index_path,
    )


def _extract_review_story_selection(content: str) -> Optional[Dict[str, object]]:
    return _extract_selection_block(content, REVIEW_STORY_HEADING_RE, parse_selected_story=True)


def _extract_review_site_theme_selection(content: str) -> Optional[Dict[str, object]]:
    return _extract_selection_block(content, REVIEW_SITE_THEME_HEADING_RE, parse_selected_story=False)


def _extract_selection_block(
    content: str,
    heading_re: re.Pattern[str],
    *,
    parse_selected_story: bool,
) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not heading_re.match(line.strip()):
            continue
        fields: Dict[str, object] = {}
        for offset, block_line in enumerate(lines[index + 1 :], start=index + 2):
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if NEXT_PROOF_HEADING_RE.match(stripped):
                break
            if stripped and not stripped.startswith(("-", "*", "+")) and re.match(r"^\s*(?:#{1,6}\s+)?[A-Za-z].*$", stripped):
                break
            match = BULLET_FIELD_RE.match(block_line)
            if not match:
                continue
            key = _normalize_key(match.group("key"))
            value = match.group("value").strip()
            if parse_selected_story and key == "selected story":
                fields["selected_story"] = _parse_selected_story(value)
                fields["selected_story_line"] = offset
            else:
                fields[key] = value
        return {"line": index + 1, **fields}
    return None


def _parse_selected_story(value: str) -> Dict[str, str]:
    parts = [part.strip() for part in value.split("|")]
    selected: Dict[str, str] = {"proof_id": parts[0].strip() if parts else ""}
    for part in parts[1:]:
        if ":" not in part:
            continue
        key, item_value = part.split(":", 1)
        selected[_normalize_key(key).replace(" ", "_")] = item_value.strip()
    return selected


def _find_index_row(path: str | Path, proof_id: str) -> Optional[Dict[str, object]]:
    index_path = Path(path)
    if not index_path.exists():
        return None
    data = json.loads(index_path.read_text(encoding="utf-8"))
    for row in data.get("proof", []):
        if isinstance(row, dict) and str(row.get("proof_id", "")) == proof_id:
            return row
    return None


def _story_identity(story: Dict[str, object]) -> str:
    return (
        str(story.get("identity_display", "")).strip()
        or str(story.get("person_name", "")).strip()
        or str(story.get("business_name", "")).strip()
    )


def _has_review_story_signal(content: str) -> bool:
    return bool(REVIEW_SITE_URL_RE.search(content) or REVIEW_LANGUAGE_RE.search(_plain_text(content)))


def _review_theme_findings(
    public_content: str,
    selection: Dict[str, object],
    proof_content: str,
) -> List[Finding]:
    findings: List[Finding] = []
    line = int(selection["line"])
    platform = str(selection.get("platform", "")).strip().lower()
    source_row_ref = str(selection.get("source row ref", "")).strip()
    public_url = str(selection.get("public review-site url", "")).strip()
    workflow_theme = str(selection.get("workflow theme", "")).strip()
    status = str(selection.get("status", "")).strip().lower()

    if platform != "capterra":
        findings.append(
            _finding(
                "review_theme_platform_unsupported",
                line,
                "Review Site Theme Selection currently supports Capterra review-theme routing only.",
                "Use Platform: Capterra or switch to Review Story Selection for identity-backed review stories.",
                match=platform or "missing",
            )
        )
    if not re.match(r"^Capterra tab row \d+$", source_row_ref, flags=re.IGNORECASE):
        findings.append(
            _finding(
                "review_theme_source_row_missing",
                line,
                "Review Site Theme Selection must cite the exact Quote Matrix Capterra tab row.",
                "Use `Source row ref: Capterra tab row [n]` from the Quote Matrix.",
                match=source_row_ref or "missing",
            )
        )
    if not _is_capterra_reviews_url(public_url):
        findings.append(
            _finding(
                "review_theme_public_url_missing",
                line,
                "Review Site Theme Selection must use the public Simpro Capterra reviews page.",
                "Use `Public review-site URL: https://www.capterra.com/p/10529/Simpro-Enterprise/reviews/`.",
                match=public_url or "missing",
            )
        )
    if not workflow_theme:
        findings.append(
            _finding(
                "review_theme_workflow_theme_missing",
                line,
                "Review Site Theme Selection is missing a workflow theme.",
                "Add a short paraphrased workflow theme from the selected Capterra row.",
            )
        )
    if status != "approved for paraphrased review-theme use":
        findings.append(
            _finding(
                "review_theme_not_approved",
                line,
                "Review Site Theme Selection is not approved for paraphrased review-theme use.",
                "Use `Status: approved for paraphrased review-theme use` after checking the selected Capterra row.",
                match=status or "missing",
            )
        )

    linked_paragraph = _paragraph_with_url_and_review_theme(public_content, public_url)
    if _is_capterra_reviews_url(public_url) and linked_paragraph is None:
        findings.append(
            _finding(
                "review_theme_link_missing",
                _first_review_signal_line(public_content),
                "Capterra review-theme copy does not link the public Capterra review-site URL in the same paragraph.",
                "Link the Capterra reviews page in the same paragraph as the paraphrased review-theme language.",
                match=public_url,
            )
        )

    for line_number, paragraph in _paragraphs_with_start_lines(public_content):
        if not _paragraph_has_review_signal(paragraph):
            continue
        if EXACT_QUOTE_RE.search(paragraph) and not _has_approved_quote(proof_content):
            findings.append(
                _finding(
                    "review_quote_requires_approved_quote",
                    line_number,
                    "Exact review wording appears without an approved quote row.",
                    (
                        "Add an Approved quote row with source type, URL or source ref, "
                        "Evidence, identity, Status: approved, and intended Use; otherwise paraphrase."
                    ),
                )
            )
        if REVIEW_RATING_RANKING_CLAIM_RE.search(paragraph) and not _has_approved_review_claim(proof_content):
            findings.append(
                _finding(
                    "review_rating_claim_requires_approved_proof",
                    line_number,
                    "Review rating, ranking, reviewer-name, aggregate, or metric-style language appears without separate approved proof.",
                    "Remove the claim or add a separate approved proof row for the exact rating, ranking, reviewer, or metric claim.",
                )
            )
    return findings


def _paragraph_with_url_and_identity(content: str, public_url: str, identity: str) -> Optional[str]:
    normalized_identity = _normalize_text(identity)
    normalized_url = _normalize_url(public_url)
    for paragraph in _paragraphs(content):
        if normalized_url not in _normalize_url(paragraph):
            continue
        if normalized_identity and normalized_identity in _normalize_text(paragraph):
            return paragraph
    return None


def _paragraph_with_url_and_review_theme(content: str, public_url: str) -> Optional[str]:
    normalized_url = _normalize_url(public_url)
    for paragraph in _paragraphs(content):
        if normalized_url and normalized_url in _normalize_url(paragraph) and _paragraph_has_review_signal(paragraph):
            return paragraph
    return None


def _paragraph_has_review_signal(paragraph: str) -> bool:
    return bool(REVIEW_SITE_URL_RE.search(paragraph) or REVIEW_LANGUAGE_RE.search(_plain_text(paragraph)))


def _has_unapproved_review_quote(
    content: str,
    public_url: str,
    identity: str,
    proof_content: str,
) -> bool:
    if _has_approved_quote(proof_content):
        return False
    normalized_identity = _normalize_text(identity)
    normalized_url = _normalize_url(public_url)
    for paragraph in _paragraphs(content):
        if not EXACT_QUOTE_RE.search(paragraph):
            continue
        paragraph_url = _normalize_url(paragraph)
        paragraph_text = _normalize_text(paragraph)
        if normalized_url and normalized_url in paragraph_url:
            return True
        if normalized_identity and normalized_identity in paragraph_text and REVIEW_LANGUAGE_RE.search(paragraph):
            return True
        if REVIEW_LANGUAGE_RE.search(paragraph):
            return True
    return False


def _has_approved_quote(proof_content: str) -> bool:
    for line in proof_content.splitlines():
        if "approved quote:" in line.lower() and "status: approved" in line.lower():
            return True
    return False


def _has_approved_review_claim(proof_content: str) -> bool:
    for line in proof_content.splitlines():
        normalized = line.lower()
        if "status: approved" not in normalized:
            continue
        if "approved quote:" in normalized or "approved metric:" in normalized or "approved review claim:" in normalized:
            return True
    return False


def _paragraphs(content: str) -> Iterable[str]:
    chunks = re.split(r"\n\s*\n", content)
    for chunk in chunks:
        stripped = chunk.strip()
        if stripped:
            yield stripped


def _paragraphs_with_start_lines(content: str) -> Iterable[tuple[int, str]]:
    line_number = 1
    for chunk in re.split(r"(\n\s*\n)", content):
        if re.match(r"\n\s*\n", chunk):
            line_number += chunk.count("\n")
            continue
        stripped = chunk.strip()
        if stripped:
            leading_newlines = len(chunk) - len(chunk.lstrip("\n"))
            yield line_number + leading_newlines, stripped
        line_number += chunk.count("\n")


def _first_review_signal_line(content: str) -> int:
    for line_number, line in enumerate(content.splitlines(), start=1):
        if REVIEW_SITE_URL_RE.search(line) or REVIEW_LANGUAGE_RE.search(line):
            return line_number
    return 1


def _first_quote_line(content: str) -> int:
    for line_number, line in enumerate(content.splitlines(), start=1):
        if EXACT_QUOTE_RE.search(line):
            return line_number
    return 1


def _plain_text(markdown: str) -> str:
    text = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_`>]", "", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def _public_copy_content(content: str) -> str:
    return re.sub(r"```.*?```", "", content, flags=re.DOTALL)


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_url(value: str) -> str:
    urls = URL_RE.findall(value)
    if urls:
        value = urls[0]
    return value.strip().rstrip(".,)").lower()


def _is_capterra_reviews_url(value: str) -> bool:
    normalized = _normalize_url(value).rstrip("/")
    return normalized == "https://www.capterra.com/p/10529/simpro-enterprise/reviews"


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    severity: str = "error",
    match: str = "",
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": severity,
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if match:
        finding["match"] = match
    return finding


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check review-story identity and public-link governance.")
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument("--proof-sidecar", help="Optional validation sidecar containing Review Story Selection.")
    parser.add_argument("--proof-index", default=str(DEFAULT_INDEX_PATH), help="Customer proof index JSON path.")
    args = parser.parse_args(argv)

    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        proof_index_path=args.proof_index,
    )
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
