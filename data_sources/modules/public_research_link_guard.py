"""
Public Research Link Guard

Blocks sidecar-only handling of public research, compliance, legal,
regulatory, or statistical proof. If a public article makes high-risk source-
backed claims, the article body must carry visible resolved non-owned public
research links in the relevant section or FAQ answer.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
    from .url_validator import UrlValidationSummary, extract_urls, validate_file_urls
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content
    from url_validator import UrlValidationSummary, extract_urls, validate_file_urls


OWNED_PUBLIC_DOMAINS = {
    "simprogroup.com",
    "www.simprogroup.com",
    "simpro.ai",
    "www.simpro.ai",
    "clockshark.com",
    "www.clockshark.com",
}

REPLACEMENT_RULE_MESSAGE = (
    "Replace this source with an equivalent resolved public source or remove the supported claim."
)
REPLACEMENT_RULE_SUGGESTION = (
    "Do not remove the citation without replacing it with a resolved source supporting "
    "the same claim."
)

STRICT_HIGH_RISK_TERM_RE = re.compile(
    r"\b("
    r"flsa|department\s+of\s+labor|dol|e-?cfr|recordkeeping|records?\s+for\s+covered|"
    r"rounding|7\s*minute\s+rule|hours?\s+worked|minimum\s+wage|"
    r"wage[-\s]?hour|non[-\s]?exempt|exempt\s+employee|salaried\s+employees?|"
    r"covered\s+employees?|regulator(?:y|s|y)?|regulation|legal|compliance"
    r")\b",
    re.IGNORECASE,
)
CONTEXTUAL_HIGH_RISK_TERM_RE = re.compile(
    r"\b("
    r"work\s+time|overtime|statistic|statistics|study|survey|research|benchmark|"
    r"industry\s+report|government\s+report"
    r")\b",
    re.IGNORECASE,
)
HIGH_RISK_TERM_RE = re.compile(
    rf"(?:{STRICT_HIGH_RISK_TERM_RE.pattern}|{CONTEXTUAL_HIGH_RISK_TERM_RE.pattern})",
    re.IGNORECASE,
)
SOURCE_SECTION_HEADING_RE = re.compile(
    r"^\s*#{1,4}\s+(Source Map|FAQ Proof Map|FAQ Proof)\s*$",
    re.IGNORECASE,
)
ANY_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
FAQ_H2_RE = re.compile(r"^##\s+(?:Frequently Asked Questions|FAQ)\s*$", re.IGNORECASE)
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
PUBLIC_URL_RE = re.compile(r"https?://[^\s)\]|<>\"']+", re.IGNORECASE)


@dataclass(frozen=True)
class ArticleSection:
    heading: str
    start_line: int
    text: str
    is_faq_answer: bool = False


@dataclass(frozen=True)
class SidecarResearchRow:
    line: int
    section: str
    text: str
    urls: tuple[str, ...]


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    url_summary: Optional[UrlValidationSummary] = None,
) -> List[Finding]:
    """Return findings for missing or blocked public research links."""
    findings: List[Finding] = []
    findings.extend(_manual_review_findings(url_summary))
    findings.extend(_section_source_findings(content, url_summary))

    if proof_content and not _external_research_not_applicable(proof_content):
        findings.extend(_sidecar_source_findings(content, proof_content, url_summary))

    return sorted(
        findings,
        key=lambda finding: (
            int(finding.get("line") or 0),
            str(finding.get("rule_id") or ""),
        ),
    )


def check_file(
    path: str | Path,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    url_summary: Optional[UrlValidationSummary] = None,
    validate_urls: bool = False,
) -> List[Finding]:
    """Check a Markdown file for public research link guardrail failures."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    article_path = Path(path)
    content = article_path.read_text(encoding="utf-8")
    proof_content = load_sidecar_content(article_path, proof_sidecar)
    if validate_urls and url_summary is None:
        url_summary = validate_file_urls(article_path)

    return check_content(
        content,
        proof_content=proof_content,
        url_summary=url_summary,
    )


def _manual_review_findings(
    url_summary: Optional[UrlValidationSummary],
) -> List[Finding]:
    if url_summary is None:
        return []

    findings: List[Finding] = []
    for result in url_summary.blockers:
        if result.status != "manual_review":
            continue
        if not _is_non_owned_public_url(result.url):
            continue
        findings.append(
            make_finding(
                "manual_review_public_research_link",
                "error",
                result.line or 1,
                match=result.url,
                message=REPLACEMENT_RULE_MESSAGE,
                suggestion=REPLACEMENT_RULE_SUGGESTION,
                url=result.url,
                status=result.status,
                status_code=result.status_code,
                anchor=result.anchor,
            )
        )
    return findings


def _section_source_findings(
    content: str,
    url_summary: Optional[UrlValidationSummary],
) -> List[Finding]:
    findings: List[Finding] = []
    for section in _iter_article_sections(content):
        source_text = _claim_detection_text(section.text)
        if not _has_high_risk_source_claim(source_text):
            continue
        if _has_resolved_external_research_link(section.text, url_summary):
            continue
        if not _has_public_article_links(section.text):
            suggestion = (
                "Add a resolved non-owned public research link in this section or remove "
                "the source-backed claim."
            )
        else:
            suggestion = (
                "Owned ClockShark/Simpro product links do not count as external research. "
                "Add a resolved non-owned public source in this section or remove the claim."
            )
        section_kind = "FAQ answer" if section.is_faq_answer else "article section"
        findings.append(
            make_finding(
                "public_research_link_missing",
                "error",
                section.start_line,
                match=section.heading,
                message=(
                    f"This {section_kind} contains compliance, legal, regulatory, "
                    "statistical, or research-backed terms but has no visible resolved "
                    "non-owned public research link."
                ),
                suggestion=suggestion,
            )
        )
    return findings


def _sidecar_source_findings(
    content: str,
    proof_content: str,
    url_summary: Optional[UrlValidationSummary],
) -> List[Finding]:
    article_has_research_link = any(
        _is_non_owned_public_url(link.url) and _url_is_resolved(link.url, url_summary)
        for link in extract_urls(content)
    )
    if article_has_research_link:
        return []

    findings: List[Finding] = []
    for row in _extract_sidecar_research_rows(proof_content):
        if not _has_high_risk_source_claim(row.text):
            continue
        if not any(_is_non_owned_public_url(url) for url in row.urls):
            continue
        findings.append(
            make_finding(
                "sidecar_research_requires_public_link",
                "error",
                row.line,
                match=row.text[:160],
                message=(
                    "The validation sidecar maps external research, compliance, legal, "
                    "regulatory, or statistical proof for a public claim, but the article "
                    "body has no resolved non-owned public research link."
                ),
                suggestion=(
                    "Add a visible resolved public source link supporting the same claim, "
                    "or remove the public claim and the sidecar proof row."
                ),
                sidecar_section=row.section,
            )
        )
        break
    return findings


def _extract_sidecar_research_rows(proof_content: str) -> List[SidecarResearchRow]:
    rows: List[SidecarResearchRow] = []
    current_section = ""
    in_source_section = False

    for line_number, line in enumerate(proof_content.splitlines(), start=1):
        stripped = line.strip()
        heading_match = SOURCE_SECTION_HEADING_RE.match(stripped)
        if heading_match:
            current_section = heading_match.group(1).lower()
            in_source_section = True
            continue

        if in_source_section and ANY_HEADING_RE.match(stripped):
            in_source_section = False
            current_section = ""

        if not in_source_section:
            continue

        urls = tuple(_normalize_url_match(url) for url in PUBLIC_URL_RE.findall(stripped))
        if not urls:
            continue
        rows.append(
            SidecarResearchRow(
                line=line_number,
                section=current_section,
                text=stripped,
                urls=urls,
            )
        )

    return rows


def _has_high_risk_source_claim(text: str) -> bool:
    if STRICT_HIGH_RISK_TERM_RE.search(text):
        return True
    if not CONTEXTUAL_HIGH_RISK_TERM_RE.search(text):
        return False
    return bool(
        re.search(
            r"\b("
            r"according\s+to|federal|state|law|rule|regulation|regulated|"
            r"must\s+be\s+paid|required|requires|requirement|source|evidence|"
            r"data\s+shows|study\s+(?:found|shows)|survey\s+(?:found|shows)"
            r")\b",
            text,
            re.IGNORECASE,
        )
    )


def _iter_article_sections(content: str) -> Iterable[ArticleSection]:
    prepared = _strip_frontmatter_preserve_lines(content)
    prepared = _blank_fenced_code(prepared)
    lines = prepared.splitlines()

    current_heading = "intro"
    current_start = 1
    current_lines: List[str] = []
    in_faq_section = False
    current_is_faq_answer = False

    def flush() -> Optional[ArticleSection]:
        if not current_lines:
            return None
        return ArticleSection(
            heading=current_heading,
            start_line=current_start,
            text="\n".join(current_lines),
            is_faq_answer=current_is_faq_answer,
        )

    for index, line in enumerate(lines, start=1):
        h2 = H2_RE.match(line)
        h3 = H3_RE.match(line)
        starts_new_h2 = h2 is not None
        starts_new_faq_answer = h3 is not None and in_faq_section

        if starts_new_h2 or starts_new_faq_answer:
            section = flush()
            if section is not None:
                yield section
            current_lines = [line]
            current_start = index
            if starts_new_h2 and h2 is not None:
                current_heading = h2.group(1).strip()
                in_faq_section = bool(FAQ_H2_RE.match(line))
                current_is_faq_answer = False
            elif h3 is not None:
                current_heading = h3.group(1).strip()
                current_is_faq_answer = True
            continue

        current_lines.append(line)

    section = flush()
    if section is not None:
        yield section


def _claim_detection_text(text: str) -> str:
    text = INLINE_CODE_RE.sub("", text)
    text = MARKDOWN_IMAGE_RE.sub("", text)
    lines = [
        line
        for line in text.splitlines()
        if not line.lstrip().startswith(">")
    ]
    return "\n".join(lines)


def _has_resolved_external_research_link(
    text: str,
    url_summary: Optional[UrlValidationSummary],
) -> bool:
    for extracted in extract_urls(text):
        if not _is_non_owned_public_url(extracted.url):
            continue
        if _url_is_resolved(extracted.url, url_summary):
            return True
    return False


def _has_public_article_links(text: str) -> bool:
    return bool(list(extract_urls(text)))


def _url_is_resolved(
    url: str,
    url_summary: Optional[UrlValidationSummary],
) -> bool:
    if url_summary is None:
        return True
    matches = [result for result in url_summary.results if result.url == url]
    if not matches:
        return False
    return any(result.status == "resolved" for result in matches)


def _is_non_owned_public_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False
    return not _is_owned_hostname(hostname)


def _is_owned_hostname(hostname: str) -> bool:
    return (
        hostname in OWNED_PUBLIC_DOMAINS
        or hostname.endswith(".simprogroup.com")
        or hostname.endswith(".simpro.ai")
        or hostname.endswith(".clockshark.com")
    )


def _external_research_not_applicable(proof_content: str) -> bool:
    lowered = proof_content.lower()
    if "external research requirement: not applicable" not in lowered:
        return False
    return "reason:" in lowered


def _strip_frontmatter_preserve_lines(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return content
    return "\n" * match.group(0).count("\n") + content[match.end():]


def _blank_fenced_code(content: str) -> str:
    return FENCED_CODE_RE.sub(lambda match: "\n" * match.group(0).count("\n"), content)


def _normalize_url_match(url: str) -> str:
    return url.rstrip(".,;:!?")


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check public copy for visible resolved external research links."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Source Map / FAQ Proof Map rows.",
    )
    parser.add_argument(
        "--validate-urls",
        action="store_true",
        help="Validate article URLs before checking whether public research links resolve.",
    )
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1.",
    )
    args = parser.parse_args(argv)

    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        validate_urls=args.validate_urls,
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
