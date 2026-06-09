"""
Numeric Claim Source Guard

Deterministic guardrail for high-risk numeric business claims in public content.
This module verifies proof placement, not semantic truth. Human review still
decides whether the linked source supports the exact claim.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


Finding = Dict[str, object]


FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*", re.DOTALL)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
BARE_URL_RE = re.compile(r"https?://[^\s<>\]\"')]+")
FDD_ITEM_RE = re.compile(r"\bItem\s+\d+\b", re.IGNORECASE)
LOCAL_ARTIFACT_RE = re.compile(
    r"(?:^|[\s|(])(?:\.{0,2}[\\/])?[A-Za-z0-9_.\\/ -]+"
    r"\.(?:md|csv|tsv|xlsx|xlsm|json|pdf)(?:$|[\s|),])",
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")
LIST_ITEM_RE = re.compile(r"^\s*(?:>\s*)?(?:[-*+]\s+|\d+[.)]\s+)")

PERCENT_RE = re.compile(r"\b\d+(?:\.\d+)?\s?%")
MONEY_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:K|M|B|k|m|b|million|billion))?",
    re.IGNORECASE,
)
MULTIPLE_RE = re.compile(r"\b\d+(?:\.\d+)?\s?x\b", re.IGNORECASE)
SCALE_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\+?\s?(?:K|M|B|k|m|b|million|billion)?"
    r"(?:\s+[A-Za-z-]+){0,3}\s+"
    r"(?:businesses|customers|users|locations|franchisees|companies|contracts|"
    r"jobs|revenue|profit|profits|margin|margins|royalty|royalties|investment|"
    r"investments|valuation|valuations|cost|costs|savings|fees|assets|sales)\b",
    re.IGNORECASE,
)
NUMERIC_TOKEN_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:K|M|B|k|m|b|million|billion))?"
    r"|\b\d+(?:\.\d+)?\s?%"
    r"|\b\d+(?:\.\d+)?\s?x\b"
    r"|\b\d[\d,]*(?:\.\d+)?\+?\s?(?:K|M|B|k|m|b|million|billion)?\b",
    re.IGNORECASE,
)

BUSINESS_KEYWORD_RE = re.compile(
    r"\b(?:EBITDA|SDE|margin|margins|profit|profits|profitable|royalty|"
    r"royalties|investment|investments|valuation|valuations|revenue|revenues|"
    r"cost|costs|saving|savings|fee|fees|franchise fee|gross revenue|"
    r"owner income|owner compensation|public-facing|businesses|customers|"
    r"users|locations|franchisees|companies|contracts|assets|sales)\b",
    re.IGNORECASE,
)
INSUFFICIENT_PROOF_RE = re.compile(
    r"\b(?:industry standard|FDD conventions|no anchor)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Paragraph:
    text: str
    line: int


@dataclass(frozen=True)
class ProofEntry:
    text: str
    normalized_tokens: frozenset[str]


def check_content(content: str) -> List[Finding]:
    """Return unsupported numeric business-claim findings for markdown content."""
    proof_entries = _extract_proof_entries(content)
    body = _strip_frontmatter_preserve_lines(content)
    body = _blank_fenced_code(body)
    body = INLINE_CODE_RE.sub("", body)

    findings: List[Finding] = []
    for paragraph in _iter_paragraphs(body):
        if not _is_candidate_claim(paragraph.text):
            continue

        numeric_tokens = _extract_numeric_tokens(_claim_text_for_detection(paragraph.text))
        if not numeric_tokens:
            continue

        if _has_same_paragraph_public_link(paragraph.text):
            continue

        normalized_tokens = {_normalize_numeric_token(token) for token in numeric_tokens}
        if _has_matching_proof(normalized_tokens, proof_entries):
            continue

        findings.append(
            {
                "rule_id": "unsupported_numeric_claim",
                "severity": "error",
                "line": paragraph.line,
                "column": 1,
                "match": paragraph.text.strip(),
                "numeric_tokens": numeric_tokens,
                "message": (
                    "High-risk numeric business claims need a public source link in "
                    "the same paragraph or matching Source Map / Proof Pack proof."
                ),
                "suggestion": (
                    "Add a public-facing proof URL next to the claim, map the same "
                    "numeric claim to a Source Map / Proof Pack row with a URL or "
                    "local proof artifact, or remove the unsupported number."
                ),
            }
        )

    return sorted(findings, key=lambda item: (item["line"], item["column"], item["rule_id"]))


def check_file(
    path: str,
    fail_on: str = "error",
) -> List[Finding]:
    """
    Check a file and return structured findings.

    Args:
        path: Markdown file path.
        fail_on: Included for CLI/API symmetry. Does not change returned findings.
    """
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")

    return check_content(Path(path).read_text(encoding="utf-8"))


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
    """Count findings by severity."""
    summary = {"error": 0, "warning": 0}
    for finding in findings:
        severity = str(finding["severity"])
        if severity in summary:
            summary[severity] += 1
    return summary


def _strip_frontmatter_preserve_lines(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return content
    return "\n" * match.group(0).count("\n") + content[match.end():]


def _blank_fenced_code(content: str) -> str:
    return FENCED_CODE_RE.sub(lambda match: "\n" * match.group(0).count("\n"), content)


def _iter_paragraphs(content: str) -> Iterable[Paragraph]:
    pending: List[str] = []
    pending_line = 0

    def flush() -> Paragraph | None:
        nonlocal pending, pending_line
        if not pending:
            return None
        paragraph = Paragraph(text=" ".join(line.strip() for line in pending), line=pending_line)
        pending = []
        pending_line = 0
        return paragraph

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or HEADING_RE.match(stripped) or TABLE_SEPARATOR_RE.match(stripped):
            paragraph = flush()
            if paragraph:
                yield paragraph
            continue
        if LIST_ITEM_RE.match(stripped):
            paragraph = flush()
            if paragraph:
                yield paragraph
            yield Paragraph(text=stripped, line=line_number)
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            paragraph = flush()
            if paragraph:
                yield paragraph
            yield Paragraph(text=stripped, line=line_number)
            continue
        if not pending:
            pending_line = line_number
        pending.append(line)

    paragraph = flush()
    if paragraph:
        yield paragraph


def _extract_proof_entries(content: str) -> List[ProofEntry]:
    entries: List[ProofEntry] = []
    for line in content.splitlines():
        if not _line_has_public_url_or_artifact(line):
            continue
        if INSUFFICIENT_PROOF_RE.search(line):
            continue
        line_text = _claim_text_for_detection(line)
        tokens = _extract_numeric_tokens(line_text)
        if not tokens:
            continue
        entries.append(
            ProofEntry(
                text=line.strip(),
                normalized_tokens=frozenset(_normalize_numeric_token(token) for token in tokens),
            )
        )
    return entries


def _line_has_public_url_or_artifact(text: str) -> bool:
    return bool(BARE_URL_RE.search(text) or LOCAL_ARTIFACT_RE.search(text))


def _is_candidate_claim(text: str) -> bool:
    if not BUSINESS_KEYWORD_RE.search(text):
        return False
    detection_text = _claim_text_for_detection(text)
    return bool(
        PERCENT_RE.search(detection_text)
        or MONEY_RE.search(detection_text)
        or MULTIPLE_RE.search(detection_text)
        or SCALE_RE.search(detection_text)
    )


def _claim_text_for_detection(text: str) -> str:
    text = MARKDOWN_LINK_RE.sub(lambda match: match.group(1), text)
    text = BARE_URL_RE.sub("", text)
    text = FDD_ITEM_RE.sub("Item", text)
    return text


def _has_same_paragraph_public_link(text: str) -> bool:
    return bool(
        any(_is_public_url(match.group(2)) for match in MARKDOWN_LINK_RE.finditer(text))
        or any(_is_public_url(match.group(0)) for match in BARE_URL_RE.finditer(text))
    )


def _is_public_url(url: str) -> bool:
    return url.startswith("http://") or url.startswith("https://")


def _extract_numeric_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for match in NUMERIC_TOKEN_RE.finditer(text):
        token = match.group(0).strip()
        if _is_date_like_token(token):
            continue
        tokens.append(token)
    return tokens


def _is_date_like_token(token: str) -> bool:
    stripped = token.strip()
    return bool(re.fullmatch(r"(?:19|20)\d{2}(?:-\d{2})?(?:-\d{2})?", stripped))


def _normalize_numeric_token(token: str) -> str:
    token = token.strip().lower().replace(",", "").replace(" ", "")
    token = token.replace("$", "")
    token = token.replace("+", "")

    multiplier = 1.0
    if token.endswith("million"):
        multiplier = 1_000_000.0
        token = token[:-7]
    elif token.endswith("billion"):
        multiplier = 1_000_000_000.0
        token = token[:-7]
    elif token.endswith("k"):
        multiplier = 1_000.0
        token = token[:-1]
    elif token.endswith("m"):
        multiplier = 1_000_000.0
        token = token[:-1]
    elif token.endswith("b"):
        multiplier = 1_000_000_000.0
        token = token[:-1]

    suffix = ""
    if token.endswith("%"):
        suffix = "%"
        token = token[:-1]
    elif token.endswith("x"):
        suffix = "x"
        token = token[:-1]

    try:
        numeric_value = float(token) * multiplier
    except ValueError:
        return token + suffix

    if numeric_value.is_integer():
        normalized = str(int(numeric_value))
    else:
        normalized = str(numeric_value).rstrip("0").rstrip(".")
    return normalized + suffix


def _has_matching_proof(
    normalized_tokens: set[str],
    proof_entries: Sequence[ProofEntry],
) -> bool:
    if not normalized_tokens:
        return False
    for entry in proof_entries:
        if normalized_tokens.issubset(entry.normalized_tokens):
            return True
    return False


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check numeric claims for source proof.")
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
    sys.exit(main())
