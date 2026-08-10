"""
Public Artifact Guard

Blocks internal validation/proof appendices from public blog copy artifacts.
Proof maps belong in validation sidecars, not in the publishable draft body.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings


BANNED_HEADINGS = (
    "Editorial Validation Appendix",
    "PAA/FAQ Provenance",
    "Metric Proof Pack",
    "Source Map",
    "Customer Proof Pack",
    "Customer Proof Slate",
    "Selected Customer Proof Mining",
    "Customer Proof Selection Decision",
    "Review Story Selection",
    "Review Site Theme Selection",
    "Competitive Shortlist Decision",
    "Named Feature/Add-On Link Check",
    "E-E-A-T Proof Map",
    "FAQ Proof Map",
    "Structured data plan",
    "Early Artifact Plan",
    "Concrete Answer Check",
    "Vault Brand Language Alignment",
    "Source Routing Decision",
    "Fred Voccola Authority Selection",
    "Named Feature Status and Commercial Treatment",
    "Context Binding",
    "Context Claim Use Map",
    "Discovery Trace",
    "Selected Resource Inventory",
    "Context Recovery Report",
    "Approved Claim Evidence",
    "Constraints and Unresolved Gaps",
    "Retrieved Guidance",
)

EDITORIAL_REVIEW_SYMBOL_RE = re.compile(r"\N{LEFT-POINTING MAGNIFYING GLASS}")
EDITORIAL_REVIEW_LABEL_RE = re.compile(
    r"\[\s*(?:PMM\s+REVIEW|COD\s+NOTE|NEEDS\s+REVIEW)(?:\s*:[^\]]*)?\s*\]",
    re.IGNORECASE,
)
PUBLICATION_CONFIRMATION_RE = re.compile(r"\bbefore publication\b", re.IGNORECASE)
UNRESOLVED_AVAILABILITY_RE = re.compile(r"\bmay now be live\b", re.IGNORECASE)
DRAFT_PLACEHOLDER_RE = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:\[(?:x| )\]\s*)?"
    r"(?:TODO|TBD|TK)(?:\s*:\s*[^|\n]+)?\s*$",
    re.IGNORECASE,
)
CONTEXT_INTERNAL_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:claim use map|(?:simpro\s+(?:product\s+)?|product\s+)?context\s+"
    r"(?:binding|pack|request|receipt|validation(?: receipt)?|claim use map|discovery trace|"
    r"(?:resource )?inventory|recovery report))\s*:?\s*$",
    re.IGNORECASE,
)
CONNECTOR_SCHEMA_RE = re.compile(
    r"\b(?:seomachine-context-binding|simpro-product-context-pack|"
    r"simpro-context-receipt)/v\d+\b",
    re.IGNORECASE,
)
CONNECTOR_FIELD_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[\"'`])?"
    r"(?:context_pack_hash|receipt_hash|resource_id|claim_id|manifest_revision|"
    r"claim_registry_revision|approval_policy_revision|receipt_sha256|pack_sha256|"
    r"request_sha256|support_resource_hashes)"
    r"(?:[\"'`])?\s*(?::|=)",
    re.IGNORECASE,
)


def check_content(content: str) -> List[Finding]:
    """Return findings for internal validation artifacts in public copy."""
    findings: List[Finding] = []
    in_fence = False
    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        normalized_heading = _normalize_heading(stripped)

        connector_match = CONNECTOR_SCHEMA_RE.search(line) or CONNECTOR_FIELD_RE.search(
            line
        )
        if connector_match:
            findings.append(
                make_finding(
                    "internal_connector_artifact",
                    "error",
                    line_number,
                    match=connector_match.group(0),
                    message="Public article copy contains internal connector binding data.",
                    suggestion="Move connector schemas, hashes, resource IDs, claim IDs, and revisions to the validation sidecar.",
                )
            )
        matched_heading = False
        for heading in BANNED_HEADINGS:
            if normalized_heading.casefold() == heading.casefold():
                findings.append(
                    make_finding(
                        "internal_validation_artifact",
                        "error",
                        line_number,
                        match=stripped,
                        message=(
                            f"Public article copy contains internal validation heading: {heading}."
                        ),
                        suggestion=(
                            "Move proof infrastructure to "
                            "research/validation-[topic-slug]-[YYYY-MM-DD].md "
                            "and run proof gates with --proof-sidecar."
                        ),
                    )
                )
                matched_heading = True
                break
        if not matched_heading and CONTEXT_INTERNAL_HEADING_RE.match(
            normalized_heading
        ):
            findings.append(
                make_finding(
                    "internal_validation_artifact",
                    "error",
                    line_number,
                    match=stripped,
                    message="Public article copy contains an internal context validation heading.",
                    suggestion="Move context bindings and receipts to the research validation sidecar.",
                )
            )

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if EDITORIAL_REVIEW_SYMBOL_RE.search(line) or EDITORIAL_REVIEW_LABEL_RE.search(
            line
        ):
            findings.append(
                make_finding(
                    "editorial_review_marker",
                    "error",
                    line_number,
                    match=stripped,
                    message="Public article copy contains an internal editorial review marker.",
                    suggestion="Resolve the note in the validation sidecar and remove it from public copy.",
                )
            )

        if _is_quoted_source_line(stripped):
            continue

        if PUBLICATION_CONFIRMATION_RE.search(line):
            findings.append(
                make_finding(
                    "publication_confirmation_note",
                    "error",
                    line_number,
                    match=stripped,
                    message="Public article copy contains an unresolved publication confirmation note.",
                    suggestion="Complete the confirmation and replace the note with approved public wording.",
                )
            )
        if UNRESOLVED_AVAILABILITY_RE.search(line):
            findings.append(
                make_finding(
                    "unresolved_availability_note",
                    "error",
                    line_number,
                    match=stripped,
                    message="Public article copy contains unresolved feature availability wording.",
                    suggestion="Verify current availability in approved evidence or omit the feature statement.",
                )
            )
        if DRAFT_PLACEHOLDER_RE.match(stripped):
            findings.append(
                make_finding(
                    "draft_placeholder_note",
                    "error",
                    line_number,
                    match=stripped,
                    message="Public article copy contains a standalone draft placeholder.",
                    suggestion="Resolve or remove the TODO, TBD, or TK marker before publication.",
                )
            )

    return findings


def _normalize_heading(line: str) -> str:
    """Remove Markdown heading and balanced inline decoration safely."""
    value = line.strip()
    html_heading_match = re.match(
        r"^<h[1-6]\b[^>]*>(?P<text>.*?)</h[1-6]>\s*$",
        value,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if html_heading_match:
        value = html_heading_match.group("text").strip()
    heading_match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", value)
    if heading_match:
        value = heading_match.group(1).strip()
    value = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    value = re.sub(r"\{[^}]+\}\s*$", " ", value).strip()
    value = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    for _ in range(4):
        undecorated = value
        for pattern in (
            r"\*\*(.+?)\*\*",
            r"__(.+?)__",
            r"~~(.+?)~~",
            r"`+(.+?)`+",
            r"(?<!\w)\*(.+?)\*(?!\w)",
            r"(?<!\w)_(.+?)_(?!\w)",
        ):
            value = re.sub(pattern, r"\1", value)
        if value == undecorated:
            break
    value = value.rstrip(":").strip()
    pairs = (
        ("**", "**"),
        ("__", "__"),
        ("~~", "~~"),
        ("`", "`"),
        ("*", "*"),
        ("_", "_"),
    )
    changed = True
    while changed:
        changed = False
        for opening, closing in pairs:
            if (
                value.startswith(opening)
                and value.endswith(closing)
                and len(value) > len(opening) + len(closing)
            ):
                value = value[len(opening) : -len(closing)].strip()
                changed = True
                break
    value = re.sub(r"\s+", " ", value)
    return value.rstrip(":").strip()


def _is_quoted_source_line(stripped: str) -> bool:
    if stripped.startswith(">"):
        return True
    quote_pairs = (
        ('"', '"'),
        ("'", "'"),
        ("\N{LEFT DOUBLE QUOTATION MARK}", "\N{RIGHT DOUBLE QUOTATION MARK}"),
    )
    return any(
        stripped.startswith(opening) and stripped.endswith(closing)
        for opening, closing in quote_pairs
        if len(stripped) >= 2
    )


def check_file(path: str | Path, fail_on: str = "error") -> List[Finding]:
    """Check a markdown file for internal validation artifacts."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    return check_content(Path(path).read_text(encoding="utf-8"))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check public copy artifacts for internal validation headings."
    )
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
