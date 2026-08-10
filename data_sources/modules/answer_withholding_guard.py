"""
Answer Withholding Guard

Deterministic guardrail against pages that withhold the answer the searcher
came for. Placeholder table scaffolds (cells like "Enter lender-approved
value", "TBD", "varies") always block publish. When the target query implies
a number, range, or template, the page must supply a concrete version —
disclaimers are fine, deferral is not.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional

try:
    from .artifact_detection import (
        countable_words,
        extract_bullet_block,
        extract_frontmatter,
        find_download_links,
        is_placeholder_cell,
        parse_tables,
        scaffold_columns,
        strip_frontmatter,
        table_has_numeric_cell,
        table_is_filled,
        table_is_scaffold,
    )
    from .guard_common import Finding, should_fail, summarize_findings
    from .proof_sidecar import compose_with_sidecar, load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_detection import (
        countable_words,
        extract_bullet_block,
        extract_frontmatter,
        find_download_links,
        is_placeholder_cell,
        parse_tables,
        scaffold_columns,
        strip_frontmatter,
        table_has_numeric_cell,
        table_is_filled,
        table_is_scaffold,
    )
    from guard_common import Finding, should_fail, summarize_findings
    from proof_sidecar import compose_with_sidecar, load_sidecar_content


NUMERIC_ANSWER_WORD_LIMIT = 500

NUMERIC_TRIGGERS = (
    "cost",
    "costs",
    "price",
    "prices",
    "pricing",
    "rate",
    "rates",
    "salary",
    "salaries",
    "wage",
    "wages",
    "fee",
    "fees",
    "how much",
    "how many",
    "percentage",
    "roi",
    "calculator",
)
TEMPLATE_TRIGGERS = (
    "template",
    "schedule",
    "checklist",
    "sample",
)

NUMERIC_TOKEN_RE = re.compile(
    r"\$\s?\d|\d+(?:\.\d+)?\s?%|"
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:to|-|–)\s?\$?\d|"
    r"\b\d+(?:\.\d+)?\s?(?:per\s+(?:hour|day|week|month|year)|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)

CHECK_HEADING_RE = re.compile(r"^(?:#{1,6}\s+)?Concrete Answer Check\s*$", re.IGNORECASE)


def check_content(content: str, proof_content: Optional[str] = None) -> List[Finding]:
    """Return answer-withholding findings for markdown content."""
    findings: List[Finding] = []

    body, body_start_line = strip_frontmatter(content)
    body_lines = body.splitlines()
    tables = parse_tables(body_lines, line_offset=body_start_line)

    for table in tables:
        if not table_is_scaffold(table):
            continue
        columns = scaffold_columns(table)
        if columns:
            column = columns[0]
            header = (
                table.header_cells[column]
                if column < len(table.header_cells)
                else f"column {column + 1}"
            )
            message = (
                f"Table column '{header}' withholds its answer: placeholder "
                "cells stand in for concrete values."
            )
        else:
            message = "Table is a placeholder scaffold: most cells withhold concrete values."
        findings.append(
            _finding(
                "placeholder_table_scaffold",
                table.start_line,
                message,
                (
                    "Fill the table with concrete sourced values — disclaimers "
                    "and 'one lender's example' framing are fine — or delete "
                    "the table. Placeholder scaffolds do not answer the query."
                ),
                match=_first_placeholder_cell(table),
            )
        )

    numeric_implied = _is_trigger_implied(content, NUMERIC_TRIGGERS)
    template_implied = _is_trigger_implied(content, TEMPLATE_TRIGGERS)

    if numeric_implied or template_implied:
        proof_source = compose_with_sidecar(content, proof_content)
        check_block = extract_bullet_block(proof_source, CHECK_HEADING_RE)
        if check_block is not None:
            requirement = check_block.fields.get("concrete answer requirement", "")
            if requirement.strip().lower() == "not applicable":
                if check_block.fields.get("reason", ""):
                    return findings
                findings.append(
                    _finding(
                        "concrete_answer_reason_missing",
                        check_block.line,
                        (
                            "Concrete Answer Check marks the requirement not "
                            "applicable but gives no reason."
                        ),
                        (
                            "Add a Reason explaining why the query does not need "
                            "a concrete number, range, or template."
                        ),
                    )
                )
                return findings

        filled_tables = [table for table in tables if table_is_filled(table)]
        download_links = find_download_links(body_lines, line_offset=body_start_line)

        if numeric_implied and not _has_numeric_answer(body_lines, filled_tables):
            findings.append(
                _finding(
                    "numeric_answer_missing",
                    _h1_line(content),
                    (
                        "The target query implies a number or range, but no "
                        f"concrete numeric answer appears in the first "
                        f"{NUMERIC_ANSWER_WORD_LIMIT} body words or in a filled "
                        "data table."
                    ),
                    (
                        "State a concrete number or range early — with "
                        "disclaimers as needed — or add a filled numeric table, "
                        "or mark `Concrete answer requirement: not applicable` "
                        "with a Reason in the Concrete Answer Check block of "
                        "the validation sidecar."
                    ),
                )
            )

        if template_implied and not filled_tables and not download_links:
            findings.append(
                _finding(
                    "template_answer_missing",
                    _h1_line(content),
                    (
                        "The target query implies a template, schedule, "
                        "checklist, or sample, but the body has no filled data "
                        "table and no download link."
                    ),
                    (
                        "Add a filled example table or a downloadable template, "
                        "or mark `Concrete answer requirement: not applicable` "
                        "with a Reason in the Concrete Answer Check block of "
                        "the validation sidecar."
                    ),
                )
            )

    return findings


def check_file(
    path: str,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
) -> List[Finding]:
    """Check a Markdown file for answer-withholding failures."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(content, proof_content=proof_content)


def _is_trigger_implied(content: str, triggers: tuple) -> bool:
    frontmatter = extract_frontmatter(content)
    h1_match = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
    h1 = h1_match.group(1) if h1_match else ""
    text = " ".join(
        [
            frontmatter.get("title", ""),
            frontmatter.get("meta_title", ""),
            frontmatter.get("primary_keyword", ""),
            frontmatter.get("secondary_keywords", ""),
            h1,
        ]
    ).lower()
    words = set(re.findall(r"[a-z]+", text))
    padded = f" {text} "
    for trigger in triggers:
        if " " in trigger:
            if f" {trigger} " in padded or padded.rstrip().endswith(f" {trigger}"):
                return True
        elif trigger in words:
            return True
    return False


def _has_numeric_answer(body_lines: List[str], filled_tables: List) -> bool:
    words_seen = 0
    for line in body_lines:
        line_words = countable_words(line)
        if line_words:
            if NUMERIC_TOKEN_RE.search(line):
                return True
            words_seen += line_words
            if words_seen >= NUMERIC_ANSWER_WORD_LIMIT:
                break
    return any(table_has_numeric_cell(table) for table in filled_tables)


def _first_placeholder_cell(table) -> Optional[str]:
    for row in table.data_rows:
        for cell in row:
            if cell.strip() and is_placeholder_cell(cell):
                return cell
    for row in table.data_rows:
        for cell in row:
            if is_placeholder_cell(cell):
                return cell
    return None


def _h1_line(content: str) -> int:
    for index, line in enumerate(content.splitlines(), start=1):
        if re.match(r"^#\s+", line):
            return index
    return 1


def _finding(
    rule_id: str,
    line: int,
    message: str,
    suggestion: str,
    match: Optional[str] = None,
) -> Finding:
    finding: Finding = {
        "rule_id": rule_id,
        "severity": "error",
        "line": line,
        "column": 1,
        "message": message,
        "suggestion": suggestion,
    }
    if match is not None:
        finding["match"] = match
    return finding


def _main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that the page supplies the concrete answer its query implies."
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
        help="Optional validation sidecar containing the Concrete Answer Check block.",
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
