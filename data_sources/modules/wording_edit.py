"""Classify an article edit as wording-only so it can chain a light receipt.

A wording-only edit changes sentence wording and nothing a gate or an earlier
artifact binds by structure: frontmatter, headings, links and anchors, numbers,
FAQ questions, quotes, media placeholders, mapped proof claims, and bound
context-claim passages all stay identical. Every readiness gate still runs on
the edited bytes; this classification only decides whether the expensive
regeneration steps (scrub, context binding, machine reviews) may be carried
forward instead of rerun.
"""

from __future__ import annotations

import difflib
import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

try:
    from .context_binding_guard import _json_block, _normalize_public_text, normalize_public_body
    from .faq_structure import detect_faq_structure
    from .frontmatter import FRONTMATTER_RE
    from .image_placeholder import (
        is_production_image_placeholder_line,
        is_production_video_placeholder_line,
    )
    from .numeric_claim_source_guard import (
        _blank_fenced_code,
        _extract_numeric_tokens,
        _strip_frontmatter_preserve_lines,
    )
    from .public_http.markdown_urls import extract_urls
    from .proof_link_policy import STRUCTURED_QUOTE_RE, _normalize_text, _proof_rows
except ImportError:  # pragma: no cover - supports direct script execution.
    from context_binding_guard import _json_block, _normalize_public_text, normalize_public_body
    from faq_structure import detect_faq_structure
    from frontmatter import FRONTMATTER_RE
    from image_placeholder import (
        is_production_image_placeholder_line,
        is_production_video_placeholder_line,
    )
    from numeric_claim_source_guard import (
        _blank_fenced_code,
        _extract_numeric_tokens,
        _strip_frontmatter_preserve_lines,
    )
    from public_http.markdown_urls import extract_urls
    from proof_link_policy import STRUCTURED_QUOTE_RE, _normalize_text, _proof_rows


WORDING_EDIT_REPORT_SCHEMA = "simpro-blog-wording-edit-report/v1"
HEADING_RE = re.compile(r"^#{1,6}\s+.*$", re.MULTILINE)


@dataclass(frozen=True)
class WordingEditReport:
    """The invariant check and word delta for one before/after article pair."""

    before_sha256: str
    after_sha256: str
    changed_words: int
    body_words: int
    violations: tuple[str, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "schema": WORDING_EDIT_REPORT_SCHEMA,
            "before_sha256": self.before_sha256,
            "after_sha256": self.after_sha256,
            "changed_words": self.changed_words,
            "body_words": self.body_words,
            "violations": list(self.violations),
        }


def classify_wording_edit(before: str, after: str, *, sidecar: str = "") -> WordingEditReport:
    """Return which wording-only invariants the edit breaks and its word delta."""
    checks = {
        "frontmatter": _frontmatter,
        "headings": _headings,
        "links": _links,
        "numbers": _numbers,
        "faq_questions": _faq_questions,
        "quotes": _quotes,
        "media_placeholders": _media_placeholders,
    }
    violations = [name for name, extract in checks.items() if extract(before) != extract(after)]
    if _lost_proof_claims(before, after, sidecar):
        violations.append("proof_claims")
    if not _context_claim_passages_intact(after, sidecar):
        violations.append("context_claim_passages")
    before_words = _body_words(before)
    return WordingEditReport(
        before_sha256=_sha256(before),
        after_sha256=_sha256(after),
        changed_words=_changed_words(before_words, _body_words(after)),
        body_words=len(before_words),
        violations=tuple(violations),
    )


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _frontmatter(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    return match.group(0) if match else ""


def _visible_body(content: str) -> str:
    return _blank_fenced_code(_strip_frontmatter_preserve_lines(content))


def _headings(content: str) -> list[str]:
    return [line.strip() for line in HEADING_RE.findall(_visible_body(content))]


def _links(content: str) -> Counter:
    return Counter((link.url, link.anchor) for link in extract_urls(content))


def _numbers(content: str) -> Counter:
    return Counter(_extract_numeric_tokens(_visible_body(content)))


def _faq_questions(content: str) -> list[str]:
    return [entry.question for entry in detect_faq_structure(content).entries]


def _quotes(content: str) -> Counter:
    return Counter(STRUCTURED_QUOTE_RE.findall(_visible_body(content)))


def _media_placeholders(content: str) -> list[str]:
    return [
        line.strip()
        for line in content.splitlines()
        if is_production_image_placeholder_line(line.strip())
        or is_production_video_placeholder_line(line.strip())
    ]


def _lost_proof_claims(before: str, after: str, sidecar: str) -> bool:
    normalized_before = _normalize_text(before)
    normalized_after = _normalize_text(after)
    return any(
        claim in normalized_before and claim not in normalized_after
        for claim in (_normalize_text(row.claim) for row in _proof_rows(sidecar))
        if claim
    )


def _context_claim_passages_intact(after: str, sidecar: str) -> bool:
    try:
        claim_map = _json_block(sidecar, "Context Claim Use Map")
    except ValueError:
        return True
    if not isinstance(claim_map, list):
        return False
    body = normalize_public_body(after)
    return all(
        isinstance(row, dict)
        and isinstance(row.get("public_text"), str)
        and body.count(_normalize_public_text(row["public_text"])) == 1
        for row in claim_map
    )


def _body_words(content: str) -> list[str]:
    return re.findall(r"\S+", _strip_frontmatter_preserve_lines(content))


def _changed_words(before: list[str], after: list[str]) -> int:
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    return sum(
        max(i2 - i1, j2 - j1)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes()
        if tag != "equal"
    )
