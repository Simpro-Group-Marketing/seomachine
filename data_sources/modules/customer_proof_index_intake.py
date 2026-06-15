"""
Customer Proof Index Intake

Validates compact CSV intake rows before they are merged into
context/customer-proof-index.json. This keeps the curated proof index usable
without turning it into a raw Quote Matrix or review-export mirror.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


ALLOWED_SOURCE_TYPES = {
    "case_study",
    "customer_story",
    "quote_matrix",
    "reference",
    "review_site",
}
ALLOWED_APPROVAL_STATUSES = {"approved", "blocked", "candidate", "ready", "rejected"}
LIST_FIELDS = {"industry", "region", "workflow_fit", "themes", "restrictions"}
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n", ""}

REQUIRED_COLUMNS = [
    "proof_id",
    "customer",
    "source_type",
    "industry",
    "region",
    "workflow_fit",
    "themes",
    "public_url",
    "internal_source_ref",
    "approval_status",
    "public_copy_allowed",
    "evidence",
    "last_verified",
    "restrictions",
    "approved_quote",
    "approved_quote_evidence",
    "approved_quote_url",
    "approved_quote_status",
    "approved_metric_claim",
    "approved_metric_evidence",
    "approved_metric_url",
    "approved_metric_status",
    "review_story_allowed",
    "review_identity_type",
    "review_identity_display",
    "review_business_name",
    "review_person_name",
    "review_role_title",
    "review_platform",
    "review_source_row_ref",
    "review_public_url",
    "review_workflow_story",
    "review_copy_use",
    "review_verification_status",
]
OPTIONAL_COLUMNS = [
    "review_objective_fit",
    "company_size",
]

Finding = Dict[str, Any]


def validate_intake_file(input_path: str | Path, *, index_path: str | Path) -> List[Finding]:
    """Return row-level validation findings for a customer proof intake CSV."""
    rows, header_findings = _read_csv(input_path)
    if header_findings:
        return header_findings
    existing_index = _load_index(index_path)
    findings: List[Finding] = []
    findings.extend(_existing_index_findings(existing_index))
    findings.extend(_duplicate_csv_findings(rows))
    for row_number, row in rows:
        findings.extend(_validate_row(row_number, row))
    return findings


def merge_intake_file(
    input_path: str | Path,
    *,
    index_path: str | Path,
    out_path: str | Path,
) -> Dict[str, Any]:
    """Validate and merge an intake CSV into a proof index JSON file."""
    findings = validate_intake_file(input_path, index_path=index_path)
    errors = [finding for finding in findings if finding.get("severity") == "error"]
    if errors:
        return {
            "passed": False,
            "errors": len(errors),
            "warnings": _warning_count(findings),
            "updated": 0,
            "appended": 0,
            "findings": findings,
        }

    existing_index = _load_index(index_path)
    rows, _ = _read_csv(input_path)
    normalized_rows = [_normalize_row(row) for _, row in rows]
    merged, updated, appended = _merge_index(existing_index, normalized_rows)
    out_file = Path(out_path)
    out_file.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "passed": True,
        "errors": 0,
        "warnings": _warning_count(findings),
        "updated": updated,
        "appended": appended,
        "proof_count": len(merged.get("proof", [])),
        "findings": findings,
    }


def _read_csv(input_path: str | Path) -> tuple[List[tuple[int, Dict[str, str]]], List[Finding]]:
    path = Path(input_path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [field for field in REQUIRED_COLUMNS if field not in fieldnames]
        if missing:
            return [], [
                _finding(
                    1,
                    "required_column_missing",
                    "error",
                    f"CSV is missing required columns: {', '.join(missing)}",
                )
            ]
        rows = [
            (line_number, {key: (value or "").strip() for key, value in row.items()})
            for line_number, row in enumerate(reader, start=2)
            if any((value or "").strip() for value in row.values())
        ]
    return rows, []


def _load_index(index_path: str | Path) -> Dict[str, Any]:
    path = Path(index_path)
    if not path.exists():
        return {"version": 1, "proof": []}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _existing_index_findings(index: Dict[str, Any]) -> List[Finding]:
    proof_ids: Dict[str, int] = {}
    findings: List[Finding] = []
    for offset, row in enumerate(index.get("proof", []), start=1):
        proof_id = str(row.get("proof_id", "")).strip()
        if not proof_id:
            continue
        if proof_id in proof_ids:
            findings.append(
                _finding(
                    offset,
                    "existing_duplicate_proof_id",
                    "error",
                    f"Existing index contains duplicate proof_id: {proof_id}",
                )
            )
        proof_ids[proof_id] = offset
    return findings


def _duplicate_csv_findings(rows: Sequence[tuple[int, Dict[str, str]]]) -> List[Finding]:
    seen: Dict[str, int] = {}
    findings: List[Finding] = []
    for line_number, row in rows:
        proof_id = row.get("proof_id", "").strip()
        if not proof_id:
            continue
        if proof_id in seen:
            findings.append(
                _finding(
                    line_number,
                    "duplicate_proof_id",
                    "error",
                    f"Duplicate proof_id in CSV: {proof_id} also appears on row {seen[proof_id]}",
                )
            )
        seen[proof_id] = line_number
    return findings


def _validate_row(row_number: int, row: Dict[str, str]) -> List[Finding]:
    findings: List[Finding] = []
    proof_id = row.get("proof_id", "").strip()
    source_type = row.get("source_type", "").strip()
    approval_status = row.get("approval_status", "").strip()
    public_copy_allowed = _parse_bool(row.get("public_copy_allowed", ""))
    story_allowed = _parse_bool(row.get("review_story_allowed", ""))
    platform = row.get("review_platform", "").strip()

    for field in ("proof_id", "customer", "source_type", "approval_status", "evidence", "last_verified"):
        if not row.get(field, "").strip():
            findings.append(
                _finding(row_number, f"{field}_missing", "error", f"{field} is required.")
            )

    if not row.get("public_url", "").strip() and not row.get("internal_source_ref", "").strip():
        findings.append(
            _finding(
                row_number,
                "source_reference_missing",
                "error",
                "At least one of public_url or internal_source_ref is required.",
            )
        )

    if source_type and source_type not in ALLOWED_SOURCE_TYPES:
        findings.append(
            _finding(
                row_number,
                "unsupported_source_type",
                "error",
                f"Unsupported source_type for {proof_id}: {source_type}",
            )
        )

    if approval_status and approval_status not in ALLOWED_APPROVAL_STATUSES:
        findings.append(
            _finding(
                row_number,
                "unsupported_approval_status",
                "error",
                f"Unsupported approval_status for {proof_id}: {approval_status}",
            )
        )

    if public_copy_allowed is None:
        findings.append(
            _finding(
                row_number,
                "public_copy_allowed_invalid",
                "error",
                "public_copy_allowed must be true or false.",
            )
        )

    public_url = row.get("public_url", "").strip()
    review_public_url = row.get("review_public_url", "").strip()
    if public_copy_allowed and not public_url and not review_public_url:
        findings.append(
            _finding(
                row_number,
                "public_copy_url_missing",
                "error",
                "public_copy_allowed rows require public_url or review_public_url.",
            )
        )

    if source_type == "review_site":
        findings.extend(_review_row_findings(row_number, row, public_copy_allowed, story_allowed))

    if _is_google_review(platform) and not public_url and not review_public_url:
        if public_copy_allowed or story_allowed:
            findings.append(
                _finding(
                    row_number,
                    "google_review_public_url_missing",
                    "error",
                    "Google review rows without a usable public URL must remain internal-only with public_copy_allowed false.",
                )
            )

    if row.get("approved_quote", "").strip():
        findings.extend(_approved_quote_findings(row_number, row))

    if row.get("approved_metric_claim", "").strip():
        findings.extend(_approved_metric_findings(row_number, row))

    return findings


def _review_row_findings(
    row_number: int,
    row: Dict[str, str],
    public_copy_allowed: Optional[bool],
    story_allowed: Optional[bool],
) -> List[Finding]:
    findings: List[Finding] = []
    if story_allowed is None:
        findings.append(
            _finding(
                row_number,
                "review_story_allowed_invalid",
                "error",
                "review_story_allowed must be true or false when provided.",
            )
        )
        return findings
    if not story_allowed:
        return findings

    identity = (
        row.get("review_identity_display", "").strip()
        or row.get("review_business_name", "").strip()
        or row.get("review_person_name", "").strip()
    )
    if not identity:
        findings.append(
            _finding(
                row_number,
                "review_story_identity_missing",
                "error",
                "Review story rows require a real person or business identity.",
            )
        )
    if not row.get("review_public_url", "").strip():
        findings.append(
            _finding(
                row_number,
                "review_story_public_url_missing",
                "error",
                "Review story rows require review_public_url.",
            )
        )
    for field in ("review_platform", "review_source_row_ref", "review_workflow_story"):
        if not row.get(field, "").strip():
            findings.append(
                _finding(row_number, f"{field}_missing", "error", f"{field} is required for review stories.")
            )
    if public_copy_allowed is False:
        findings.append(
            _finding(
                row_number,
                "review_story_public_copy_not_allowed",
                "error",
                "story_allowed review rows must set public_copy_allowed true.",
            )
        )
    return findings


def _approved_quote_findings(row_number: int, row: Dict[str, str]) -> List[Finding]:
    findings: List[Finding] = []
    if not row.get("approved_quote_evidence", "").strip():
        findings.append(
            _finding(
                row_number,
                "approved_quote_evidence_missing",
                "error",
                "Approved quote rows require source-visible approved_quote_evidence.",
            )
        )
    if row.get("approved_quote_status", "").strip() != "approved":
        findings.append(
            _finding(
                row_number,
                "approved_quote_status_missing",
                "error",
                "Approved quote rows require approved_quote_status=approved.",
            )
        )
    if not row.get("approved_quote_url", "").strip() and not row.get("public_url", "").strip() and not row.get("internal_source_ref", "").strip():
        findings.append(
            _finding(
                row_number,
                "approved_quote_source_missing",
                "error",
                "Approved quote rows require approved_quote_url, public_url, or internal_source_ref.",
            )
        )
    return findings


def _approved_metric_findings(row_number: int, row: Dict[str, str]) -> List[Finding]:
    findings: List[Finding] = []
    if not row.get("approved_metric_evidence", "").strip():
        findings.append(
            _finding(
                row_number,
                "approved_metric_evidence_missing",
                "error",
                "Approved metric rows require source-visible approved_metric_evidence.",
            )
        )
    if row.get("approved_metric_status", "").strip() != "approved":
        findings.append(
            _finding(
                row_number,
                "approved_metric_status_missing",
                "error",
                "Approved metric rows require approved_metric_status=approved.",
            )
        )
    if not row.get("approved_metric_url", "").strip() and not row.get("public_url", "").strip():
        findings.append(
            _finding(
                row_number,
                "approved_metric_url_missing",
                "error",
                "Approved metric rows require approved_metric_url or public_url.",
            )
        )
    return findings


def _normalize_row(row: Dict[str, str]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for field in (
        "proof_id",
        "customer",
        "source_type",
        "public_url",
        "internal_source_ref",
        "approval_status",
        "evidence",
        "last_verified",
        "company_size",
    ):
        value = row.get(field, "").strip()
        if value:
            normalized[field] = value

    for field in LIST_FIELDS:
        normalized[field] = _split_list(row.get(field, ""))

    normalized["public_copy_allowed"] = bool(_parse_bool(row.get("public_copy_allowed", "")))

    quote = row.get("approved_quote", "").strip()
    normalized["approved_quotes"] = []
    if quote:
        normalized["approved_quotes"].append(
            {
                "quote": quote,
                "evidence": row.get("approved_quote_evidence", "").strip(),
                "url": row.get("approved_quote_url", "").strip() or row.get("public_url", "").strip(),
                "status": row.get("approved_quote_status", "").strip(),
            }
        )

    metric = row.get("approved_metric_claim", "").strip()
    normalized["approved_metrics"] = []
    if metric:
        normalized["approved_metrics"].append(
            {
                "claim": metric,
                "evidence": row.get("approved_metric_evidence", "").strip(),
                "url": row.get("approved_metric_url", "").strip() or row.get("public_url", "").strip(),
                "status": row.get("approved_metric_status", "").strip(),
            }
        )

    review_story = _normalize_review_story(row)
    if review_story:
        normalized["review_story"] = review_story

    return normalized


def _normalize_review_story(row: Dict[str, str]) -> Dict[str, Any]:
    review_fields = {
        "story_allowed": _parse_bool(row.get("review_story_allowed", "")),
        "identity_type": row.get("review_identity_type", "").strip(),
        "identity_display": row.get("review_identity_display", "").strip(),
        "business_name": row.get("review_business_name", "").strip(),
        "person_name": row.get("review_person_name", "").strip(),
        "role_title": row.get("review_role_title", "").strip(),
        "platform": row.get("review_platform", "").strip(),
        "source_row_ref": row.get("review_source_row_ref", "").strip(),
        "public_url": row.get("review_public_url", "").strip(),
        "workflow_story": row.get("review_workflow_story", "").strip(),
        "objective_fit": _split_list(row.get("review_objective_fit", "")),
        "copy_use": row.get("review_copy_use", "").strip(),
        "verification_status": row.get("review_verification_status", "").strip(),
    }
    if not any(value not in ("", None, False) for value in review_fields.values()):
        return {}
    review_fields["story_allowed"] = bool(review_fields["story_allowed"])
    return {key: value for key, value in review_fields.items() if value not in ("", None, [])}


def _merge_index(index: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> tuple[Dict[str, Any], int, int]:
    merged = dict(index)
    proof = list(index.get("proof", []))
    positions = {
        str(row.get("proof_id", "")): offset
        for offset, row in enumerate(proof)
        if isinstance(row, dict) and row.get("proof_id")
    }
    updated = 0
    appended = 0
    for row in rows:
        proof_id = str(row.get("proof_id", ""))
        if proof_id in positions:
            existing = proof[positions[proof_id]]
            proof[positions[proof_id]] = _merge_existing_row(existing, row)
            updated += 1
        else:
            positions[proof_id] = len(proof)
            proof.append(row)
            appended += 1
    merged["version"] = index.get("version", 1)
    merged["updated_at"] = date.today().isoformat()
    merged["source_boundary"] = index.get(
        "source_boundary",
        "Curated customer proof index. Exact quotes, metrics, ratings, rankings, and reviewer-name claims require approved source-visible proof.",
    )
    merged["proof"] = proof
    return merged, updated, appended


def _merge_existing_row(existing: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    for key, value in incoming.items():
        if key == "review_story" and isinstance(value, dict):
            existing_story = merged.get("review_story", {})
            if isinstance(existing_story, dict):
                story = dict(existing_story)
                story.update(value)
                merged[key] = story
            else:
                merged[key] = value
            continue
        if isinstance(value, list) and value == [] and merged.get(key):
            continue
        merged[key] = value
    return merged


def _split_list(value: str) -> List[str]:
    if not value:
        return []
    return [
        item.strip()
        for chunk in value.split("|")
        for item in chunk.split(";")
        if item.strip()
    ]


def _parse_bool(value: str) -> Optional[bool]:
    normalized = str(value or "").strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return None


def _is_google_review(platform: str) -> bool:
    normalized = platform.lower().replace("-", " ")
    return "google" in normalized


def _warning_count(findings: Iterable[Finding]) -> int:
    return sum(1 for finding in findings if finding.get("severity") == "warning")


def _finding(row: int, rule_id: str, severity: str, message: str) -> Finding:
    return {
        "row": row,
        "line": row,
        "rule_id": rule_id,
        "severity": severity,
        "message": message,
    }


def _summary(findings: Sequence[Finding]) -> Dict[str, Any]:
    errors = sum(1 for finding in findings if finding.get("severity") == "error")
    warnings = sum(1 for finding in findings if finding.get("severity") == "warning")
    return {
        "passed": errors == 0,
        "errors": errors,
        "warnings": warnings,
        "findings": list(findings),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or merge customer proof index intake CSV rows.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a proof intake CSV without writing files.")
    validate.add_argument("input_csv")
    validate.add_argument("--index", default="context/customer-proof-index.json")

    merge = subparsers.add_parser("merge", help="Validate and merge a proof intake CSV into an index JSON.")
    merge.add_argument("input_csv")
    merge.add_argument("--index", default="context/customer-proof-index.json")
    merge.add_argument("--out", default="context/customer-proof-index.json")
    return parser


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "validate":
        findings = validate_intake_file(args.input_csv, index_path=args.index)
        summary = _summary(findings)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if summary["passed"] else 1

    result = merge_intake_file(args.input_csv, index_path=args.index, out_path=args.out)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(_main())
