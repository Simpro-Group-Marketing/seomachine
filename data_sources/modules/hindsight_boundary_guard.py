"""Publish-readiness guard for Hindsight internal-strategy boundaries."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Sequence

try:
    from .context_binding_guard import visible_public_content
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from context_binding_guard import visible_public_content
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Hindsight Strategy Selection:?\s*$",
    re.IGNORECASE,
)
MARKDOWN_HEADING_RE = re.compile(r"^\s*#{1,6}\s+\S")
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")
HINDSIGHT_ID_RE = re.compile(
    r"\b(?:HSI|HINDSIGHT|DEAL|ING|INTSTRAT)-[A-Za-z0-9][A-Za-z0-9_.:-]*\b",
    re.IGNORECASE,
)
PUBLIC_LEAK_PATTERNS = (
    (
        "hindsight_label_public_copy",
        re.compile(r"\bHindsight\b"),
        "Public article copy mentions Hindsight internal strategy material.",
    ),
    (
        "deal_intelligence_public_copy",
        re.compile(r"\bdeal[-\s]+intelligence\b", re.IGNORECASE),
        "Public article copy mentions deal-intelligence material.",
    ),
    (
        "internal_strategy_public_copy",
        re.compile(r"\binternal[-\s]+strategy\b", re.IGNORECASE),
        "Public article copy mentions internal strategy evidence.",
    ),
    (
        "raw_deal_count_public_copy",
        re.compile(r"\b\d{1,6}\s+(?:deals?|opportunities|sales\s+opportunities)\b", re.IGNORECASE),
        "Public article copy contains a raw deal-count style claim.",
    ),
    (
        "hindsight_id_public_copy",
        HINDSIGHT_ID_RE,
        "Public article copy contains a Hindsight or deal-intelligence identifier.",
    ),
)
ALLOWED_STATUSES = {"internal_strategy_only", "not_applicable", "blocked"}
INTERNAL_ONLY_REQUIRED_MARKERS = (
    "public_claim_use: prohibited",
    "claim_support_allowed: false",
)
INTERNAL_ONLY_EVIDENCE_MARKERS = (
    "source_pack_sha256",
    "source_receipt_sha256",
    "pack_sha256",
    "receipt_sha256",
    "evidence_output",
)


def check_content(
    content: str,
    *,
    proof_content: str | None = None,
) -> List[Finding]:
    """Return findings when Hindsight internal strategy crosses a public boundary."""
    findings: List[Finding] = []
    public_content = visible_public_content(content)
    for line_number, line in enumerate(public_content.splitlines(), start=1):
        if _is_canonical_media_placeholder(line.strip()):
            continue
        for rule_id, pattern, message in PUBLIC_LEAK_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(
                    make_finding(
                        rule_id,
                        "error",
                        line_number,
                        column=match.start() + 1,
                        match=match.group(0),
                        message=message,
                        suggestion=(
                            "Remove Hindsight/deal-intelligence material from public copy, "
                            "or support the public claim through the approved claim registry."
                        ),
                    )
                )

    block = _extract_selection_block(proof_content or "")
    if block is None:
        return findings
    fields = block["fields"]
    line = int(block["line"])
    status = fields.get("status", "").strip().lower()
    if status not in ALLOWED_STATUSES:
        findings.append(
            _finding(
                "hindsight_selection_status_invalid",
                line,
                "Hindsight Strategy Selection has an invalid or missing status.",
                "Use Status: internal_strategy_only, Status: not_applicable, or Status: blocked.",
                match=status,
            )
        )
        return _sorted(findings)
    if status == "internal_strategy_only":
        normalized = _normalize_block_text(block["text"])
        for marker in INTERNAL_ONLY_REQUIRED_MARKERS:
            if marker not in normalized:
                findings.append(
                    _finding(
                        "hindsight_public_use_boundary_missing",
                        line,
                        f"Hindsight internal strategy evidence is missing required boundary marker: {marker}.",
                        "Record public_claim_use: prohibited and claim_support_allowed: false in the selection block.",
                        match=marker,
                    )
                )
        if not any(marker in normalized for marker in INTERNAL_ONLY_EVIDENCE_MARKERS):
            findings.append(
                _finding(
                    "hindsight_internal_evidence_binding_missing",
                    line,
                    "Hindsight internal strategy use is missing evidence binding.",
                    "Record pack and receipt hashes, or the evidence output path, in the selection block.",
                )
            )
    return _sorted(findings)


def check_file(
    path: str | Path,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    **_: object,
) -> List[Finding]:
    """Check an article file and optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article_path = Path(path)
    proof_content = load_sidecar_content(article_path, proof_sidecar)
    return check_content(
        article_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
    )


def _extract_selection_block(content: str) -> dict[str, object] | None:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not HEADING_RE.match(line.strip()):
            continue
        block_lines: list[str] = []
        fields: dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            if MARKDOWN_HEADING_RE.match(block_line):
                break
            block_lines.append(block_line)
            field_match = BULLET_FIELD_RE.match(block_line)
            if field_match:
                key = re.sub(r"\s+", " ", field_match.group("key").strip().lower())
                fields[key] = field_match.group("value").strip()
        return {
            "line": index + 1,
            "text": "\n".join(block_lines),
            "fields": fields,
        }
    return None


def _normalize_block_text(value: str) -> str:
    normalized = value.casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\s*:\s*", ": ", normalized)
    return normalized


def _is_canonical_media_placeholder(stripped: str) -> bool:
    return stripped.startswith("[IMAGE PLACEHOLDER |") or stripped.startswith(
        "[VIDEO PLACEHOLDER |"
    )


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    *,
    match: str = "",
) -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        match=match,
        message=message,
        suggestion=suggestion,
    )


def _sorted(findings: List[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda finding: (finding["line"], finding["rule_id"]))


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check public copy for Hindsight internal-strategy leakage."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument("--proof-sidecar", help="Validation sidecar path")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    args = parser.parse_args(argv)

    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
    )
    payload = {
        "path": args.path,
        "proof_sidecar": args.proof_sidecar,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    import json

    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(_main())
