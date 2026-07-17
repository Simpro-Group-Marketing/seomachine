"""
Early Artifact Guard

Deterministic guardrail requiring a usable artifact — a filled data table,
a download link, a checklist deliverable, or a calculator/tool reference —
to start within the first 300 countable body words. Motivated by bounce
analysis: pages that hand the reader something usable early keep them.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

try:
    from .artifact_detection import (
        body_word_offsets,
        extract_bullet_block,
        find_download_links,
        parse_tables,
        strip_frontmatter,
        table_is_filled,
    )
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_detection import (
        body_word_offsets,
        extract_bullet_block,
        find_download_links,
        parse_tables,
        strip_frontmatter,
        table_is_filled,
    )
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content


EARLY_ARTIFACT_WORD_LIMIT = 300

PLAN_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?Early Artifact Plan\s*$", re.IGNORECASE)


def check_content(content: str, proof_content: Optional[str] = None) -> List[Finding]:
    """Return early-artifact findings for markdown content."""
    proof_source = compose_with_sidecar(content, proof_content)
    plan = extract_bullet_block(proof_source, PLAN_HEADING_RE)

    if plan is not None:
        requirement = plan.fields.get("early artifact requirement", "")
        if requirement.strip().lower() == "not applicable":
            if plan.fields.get("reason", ""):
                return []
            return [
                _finding(
                    "early_artifact_reason_missing",
                    plan.line,
                    "Early Artifact Plan marks the requirement not applicable but gives no reason.",
                    "Add a Reason explaining why no filled table, download, or tool reference fits this topic.",
                )
            ]

    body, body_start_line = strip_frontmatter(content)
    body_lines = body.splitlines()
    offsets = body_word_offsets(body_lines)

    earliest_offset: Optional[int] = None

    for table in parse_tables(body_lines, line_offset=body_start_line):
        if not table_is_filled(table):
            continue
        offset = offsets[table.start_line - body_start_line]
        if earliest_offset is None or offset < earliest_offset:
            earliest_offset = offset

    for link in find_download_links(body_lines, line_offset=body_start_line):
        offset = offsets[link.line - body_start_line]
        if earliest_offset is None or offset < earliest_offset:
            earliest_offset = offset

    if earliest_offset is not None and earliest_offset <= EARLY_ARTIFACT_WORD_LIMIT:
        return []

    h1_line = _h1_line(content)
    finding = _finding(
        "early_artifact_missing",
        h1_line,
        (
            "No usable artifact (filled data table, download link, checklist "
            f"deliverable, or calculator reference) starts within the first "
            f"{EARLY_ARTIFACT_WORD_LIMIT} words of body copy."
        ),
        (
            "Move a filled table, download link, or calculator reference into "
            f"the opening {EARLY_ARTIFACT_WORD_LIMIT} words, or mark "
            "`Early artifact requirement: not applicable` with a Reason in the "
            "Early Artifact Plan block of the validation sidecar."
        ),
    )
    if earliest_offset is not None:
        finding["word_offset"] = earliest_offset
    return [finding]


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a Markdown file for the early usable artifact requirement."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(content, proof_content=proof_content)


def _h1_line(content: str) -> int:
    for index, line in enumerate(content.splitlines(), start=1):
        if re.match(r"^#\s+", line):
            return index
    return 1


def _finding(rule_id: str, line: int, message: str, suggestion: str) -> Finding:
    return {
        "rule_id": rule_id,
        "severity": "error",
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that a usable artifact appears within the first 300 body words."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        default="error",
        choices=["error", "warning", "none"],
        help="Minimum finding severity that returns exit code 1",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing the Early Artifact Plan block.",
    )
    args = parser.parse_args(argv)

    findings = check_file(args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar)
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
