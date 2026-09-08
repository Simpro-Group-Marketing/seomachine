"""Validate schema_notes as a later-CMS handoff, not rendered schema."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

try:
    from .artifact_detection import extract_frontmatter, strip_frontmatter
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - direct script execution.
    from artifact_detection import extract_frontmatter, strip_frontmatter
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*", re.DOTALL)
FAQ_HEADING_RE = re.compile(r"^\s{0,3}##\s+(?:Frequently Asked Questions|FAQs?|FAQ)\s*#*\s*$", re.IGNORECASE | re.MULTILINE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+(?P<title>.*?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
VIDEO_RE = re.compile(
    r"<video\b|<iframe\b(?=[^>]*\bsrc\s*=\s*['\"][^'\"]*(?:"
    r"youtube(?:-nocookie)?\.com|youtu\.be|player\.vimeo\.com|"
    r"fast\.wistia\.(?:net|com)|share\.vidyard\.com"
    r"))[^>]*>",
    re.IGNORECASE,
)
JSON_LD_RE = re.compile(r"<script\b[^>]*type\s*=\s*['\"]application/ld\+json['\"]", re.IGNORECASE)
IMPLEMENTATION_CLAIM_RE = re.compile(r"\b(?:rendered|implemented|deployed|live)\b.*\b(?:json-ld|schema)\b|\b(?:json-ld|schema)\b.*\b(?:rendered|implemented|deployed|live)\b", re.IGNORECASE)
NEGATED_IMPLEMENTATION_RE = re.compile(
    r"\b(?:not|never)\s+(?:yet\s+)?(?:be\s+)?"
    r"(?:rendered|implemented|deployed|live)"
    r"(?:\s+(?:or|and)\s+(?:rendered|implemented|deployed|live))*\b",
    re.IGNORECASE,
)


def check_content(content: str, *, proof_content: str | None = None) -> list[Finding]:
    """Return conditional schema handoff findings for a Markdown blog."""
    findings: list[Finding] = []
    frontmatter = extract_frontmatter(content)
    notes = _schema_notes(content)
    normalized_notes = _normalize(notes)
    body, _ = strip_frontmatter(content)
    has_faq = bool(FAQ_HEADING_RE.search(body))
    has_video = bool(VIDEO_RE.search(body))
    has_author = bool(frontmatter.get("author", "").strip())

    if not notes:
        return [
            _finding(
                "schema_handoff_notes_missing",
                "Public blog frontmatter requires schema_notes for the later CMS handoff.",
            )
        ]
    if "blogposting" not in normalized_notes:
        findings.append(_finding("schema_handoff_blogposting_missing", "schema_notes must include BlogPosting."))
    if "breadcrumblist" not in normalized_notes:
        findings.append(_finding("schema_handoff_breadcrumb_missing", "schema_notes must include BreadcrumbList."))
    if "imageobject" not in normalized_notes:
        findings.append(_finding("schema_handoff_imageobject_missing", "schema_notes must include ImageObject for the featured image or logo."))
    if not (
        "organization" in normalized_notes
        and "publisher reference" in normalized_notes
        and "not a separate full schema block" in normalized_notes
    ):
        findings.append(_finding("schema_handoff_publisher_reference_missing", "schema_notes must describe Organization as publisher reference only, not a separate full schema block."))

    has_faqpage = _has_schema_entity(notes, "FAQPage")
    has_question_answer = "question and answer" in normalized_notes
    if has_faq:
        if not has_faqpage:
            findings.append(_finding("schema_handoff_faqpage_missing", "Visible FAQs require FAQPage in schema_notes."))
        if not has_question_answer:
            findings.append(_finding("schema_handoff_question_answer_missing", "Visible FAQs require nested Question and Answer notes."))
    else:
        if has_faqpage:
            findings.append(_finding("schema_handoff_faqpage_without_faq", "FAQPage cannot be handed off when no visible FAQ section exists."))
        if has_question_answer:
            findings.append(_finding("schema_handoff_question_answer_without_faq", "Question and Answer cannot be handed off when no visible FAQ section exists."))

    has_person = "person as author" in normalized_notes
    if has_author and not has_person:
        findings.append(_finding("schema_handoff_person_missing", "An author in frontmatter requires Person as author in schema_notes."))
    if has_author and has_person and not _author_verified(
        str(frontmatter.get("author", "")),
        proof_content or "",
    ):
        findings.append(_finding("schema_handoff_author_unverified", "Person as author requires an explicit verified author proof row in the validation sidecar."))
    if not has_author and has_person:
        findings.append(_finding("schema_handoff_person_without_author", "Person as author cannot be handed off when article frontmatter has no author."))

    has_videoobject = "videoobject" in normalized_notes
    if has_video and not has_videoobject:
        findings.append(_finding("schema_handoff_videoobject_missing", "An embedded video requires VideoObject in schema_notes."))
    if not has_video and has_videoobject:
        findings.append(_finding("schema_handoff_videoobject_without_video", "VideoObject cannot be handed off when no video is embedded."))

    if JSON_LD_RE.search(body):
        findings.append(_finding("schema_handoff_rendered_jsonld_forbidden", "This workflow accepts schema notes only; rendered JSON-LD is a later CMS responsibility."))
    if _has_positive_implementation_claim(notes):
        findings.append(_finding("schema_handoff_implementation_claim_forbidden", "schema_notes cannot claim that JSON-LD or schema is rendered, implemented, deployed, or live."))
    return sorted(findings, key=lambda finding: str(finding["rule_id"]))


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
) -> list[Finding]:
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article_path = Path(path)
    proof_content = load_sidecar_content(article_path, proof_sidecar)
    return check_content(article_path.read_text(encoding="utf-8"), proof_content=proof_content)


def _schema_notes(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return ""
    lines = match.group("body").splitlines()
    for index, line in enumerate(lines):
        key_match = re.match(r"^schema_notes\s*:\s*(?P<value>.*)$", line, re.IGNORECASE)
        if not key_match:
            continue
        values = [key_match.group("value").strip()]
        for following in lines[index + 1 :]:
            if following and not following[0].isspace():
                break
            values.append(following.strip())
        return "\n".join(value for value in values if value)
    return ""


def _normalize(value: str) -> str:
    value = value.replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", value.casefold()).strip()


def _has_schema_entity(notes: str, entity: str) -> bool:
    normalized = _normalize(notes)
    target = _normalize(entity)
    for match in re.finditer(rf"(?<![a-z0-9]){re.escape(target)}(?![a-z0-9])", normalized):
        before = normalized[max(0, match.start() - 60) : match.start()]
        after = normalized[match.end() : match.end() + 40]
        if re.search(r"\binside\s*$", before):
            continue
        if re.search(
            r"\b(?:no|not|never|omit|omits|exclude|excludes|without)\b"
            r"(?:\s+[a-z0-9]+){0,5}\s*$",
            before,
        ):
            continue
        if re.match(
            r"\s+(?:(?:is|are|should|must|will|would|can)\s+)?not\b",
            after,
        ):
            continue
        return True
    return False


def _has_positive_implementation_claim(notes: str) -> bool:
    without_negated_status = NEGATED_IMPLEMENTATION_RE.sub("", notes)
    return bool(IMPLEMENTATION_CLAIM_RE.search(without_negated_status))


def _author_verified(author: str, proof_content: str) -> bool:
    normalized_author = _normalize(author)
    if not normalized_author:
        return False
    in_author_section = False
    for _, line in _executable_lines(proof_content):
        stripped = line.strip()
        heading = HEADING_RE.match(stripped)
        if heading:
            title = heading.group("title").strip().rstrip(":").casefold()
            in_author_section = title == "author verification"
            continue
        if stripped.rstrip(":").casefold() == "author verification":
            in_author_section = True
            continue
        if in_author_section and stripped and not stripped.startswith(("-", "|")):
            in_author_section = False
        if not in_author_section:
            continue
        normalized_line = _normalize(stripped)
        if normalized_author not in normalized_line:
            continue
        if not re.search(r"(?:^|\|)\s*Status\s*:\s*(?:verified|approved)\s*(?:\||$)", stripped, re.IGNORECASE):
            continue
        if not re.search(r"https?://", stripped, re.IGNORECASE):
            continue
        if "evidence:" not in stripped.casefold() or "checked date:" not in stripped.casefold():
            continue
        return True
    return False


def _executable_lines(content: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    in_fence = False
    in_comment = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        visible, in_comment = _strip_comments(line, in_comment=in_comment)
        if visible or not line.strip():
            lines.append((line_number, visible))
    return lines


def _strip_comments(line: str, *, in_comment: bool) -> tuple[str, bool]:
    output = line
    if in_comment:
        if "-->" not in output:
            return "", True
        output = output.split("-->", 1)[1]
        in_comment = False
    while "<!--" in output:
        before, after = output.split("<!--", 1)
        if "-->" not in after:
            return before, True
        output = before + after.split("-->", 1)[1]
    return output, in_comment


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        1,
        message=message,
        suggestion="Correct schema_notes in the top YAML frontmatter; do not add rendered JSON-LD in this workflow.",
    )


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate conditional schema handoff notes.")
    parser.add_argument("path")
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    parser.add_argument("--proof-sidecar")
    args = parser.parse_args(argv)
    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
    payload = {"path": args.path, "summary": summarize_findings(findings), "findings": findings}
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
