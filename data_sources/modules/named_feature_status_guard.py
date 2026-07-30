"""Validate named Lightning feature status and commercial treatment."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


DEFAULT_VAULT_ROOT = Path(
    "C:/Users/patrick.grueschow/Desktop/Obsidian/Simpro Brand Context"
)
CLAIM_INDEX_PATH = Path("indexes/lightning-current-claim-status.csv")
TABLE_HEADING = "Named Feature Status and Commercial Treatment"
REQUIRED_COLUMNS = (
    "Name",
    "Capability claim ID",
    "Commercial claim ID",
    "Release status",
    "Commercial treatment",
    "Region or account boundary",
    "Public wording decision",
)
ALLOWED_RELEASE_STATUSES = {
    "current_public_context",
    "preview",
    "target_timed",
    "roadmap",
    "not_publicly_available",
}
ALLOWED_COMMERCIAL_TREATMENTS = {
    "included",
    "package_required",
    "add_on_or_upsell",
    "mixed",
    "not_asserted",
}
ALLOWED_WORDING_DECISIONS = {"use", "qualify", "omit"}
FEATURE_ALIASES = (
    ("Intelligent AI Scheduler", (r"\bIntelligent AI Scheduler\b",)),
    ("FieldReady", (r"\bFieldReady\b",)),
    ("JobReady", (r"\bJobReady\b",)),
    ("JobScribe", (r"\bJobScribe\b",)),
    ("JobBrief", (r"\bJobBrief\b",)),
    ("JustAsk", (r"\bJustAsk\b",)),
    ("Cooper", (r"\bCooper\b",)),
    ("Lightning", (r"\b(?:Simpro\s+)?Lightning\b",)),
    ("RAIN", (r"\b(?:Simpro\s+)?RAIN\b",)),
    ("FastCash", (r"\bFastCash\b",)),
    ("Delight", (r"\bDelight\b",)),
    ("Pulse", (r"\bPulse\b",)),
    ("Foresight", (r"\bForesight\b",)),
    ("Forge", (r"\bForge\b",)),
    ("Swift", (r"\bSwift\b",)),
    ("Sales Manager", (r"\bSales Manager\b",)),
    ("Shield", (r"\bShield\b",)),
    ("Spark", (r"\bSpark\b",)),
    ("Precision", (r"\bPrecision\b",)),
)
COMMERCIAL_RE = re.compile(
    r"\b(?:included|no additional cost|package|subscription|upgrade|upsell|"
    r"add[- ]on|extra cost|price|pricing|paid)\b",
    re.IGNORECASE,
)
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*", re.DOTALL)


def check_content(
    content: str,
    proof_content: str | None = None,
    vault_path: str | Path | None = None,
) -> List[Finding]:
    """Return status and commercial treatment findings for named features."""
    public_body = _public_body(content)
    detected = _detect_features(public_body)
    if not detected:
        return []

    findings: List[Finding] = []
    rows, table_findings = _parse_status_table(proof_content or "")
    findings.extend(table_findings)
    rows_by_name: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        rows_by_name[_normalize_name(row.get("Name", ""))].append(row)

    try:
        claims_by_id = _load_claim_index(_resolve_vault_root(vault_path))
    except (OSError, ValueError) as exc:
        findings.append(
            make_finding(
                "named_feature_claim_index_unavailable",
                "error",
                1,
                message=f"Named feature claim index could not be verified: {exc}",
                suggestion="Restore the vault claim index before publishing named feature copy.",
            )
        )
        claims_by_id = {}

    for name, line in detected.items():
        matching_rows = rows_by_name.get(_normalize_name(name), [])
        if not matching_rows:
            findings.append(
                make_finding(
                    "named_feature_status_row_missing",
                    "error",
                    line,
                    match=name,
                    message=f"{name} needs exactly one status and commercial treatment row.",
                    suggestion=f"Add one {TABLE_HEADING} row for {name}.",
                )
            )
            continue
        if len(matching_rows) > 1:
            findings.append(
                make_finding(
                    "named_feature_status_row_duplicate",
                    "error",
                    line,
                    match=name,
                    message=f"{name} has more than one status and commercial treatment row.",
                    suggestion=f"Keep exactly one {TABLE_HEADING} row for {name}.",
                )
            )
            continue

        row = matching_rows[0]
        findings.extend(
            _validate_row(
                name,
                line,
                row,
                public_body,
                claims_by_id,
            )
        )

    return sorted(
        findings,
        key=lambda finding: (
            int(finding.get("line", 1)),
            str(finding.get("rule_id", "")),
        ),
    )


def check_file(
    path: str | Path,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    vault_path: str | Path | None = None,
) -> List[Finding]:
    """Check an article and its validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(content, proof_content=proof_content, vault_path=vault_path)


def _public_body(content: str) -> str:
    body = FRONTMATTER_RE.sub(
        lambda match: "\n" * match.group(0).count("\n"),
        content,
        count=1,
    )
    return FENCE_RE.sub(
        lambda match: "\n" * match.group(0).count("\n"),
        body,
    )


def _detect_features(content: str) -> Dict[str, int]:
    detected: Dict[str, int] = {}
    for name, aliases in FEATURE_ALIASES:
        first_match = None
        for alias in aliases:
            match = re.search(alias, content, re.IGNORECASE)
            if match and (first_match is None or match.start() < first_match.start()):
                first_match = match
        if first_match:
            detected[name] = content.count("\n", 0, first_match.start()) + 1
    return detected


def _parse_status_table(proof_content: str) -> tuple[List[dict], List[Finding]]:
    lines = proof_content.splitlines()
    heading_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(
                rf"^\s*#{{1,6}}\s+{re.escape(TABLE_HEADING)}\s*$",
                line,
                re.IGNORECASE,
            )
        ),
        None,
    )
    if heading_index is None:
        return [], [
            make_finding(
                "named_feature_status_table_missing",
                "error",
                1,
                message=f"Validation sidecar is missing {TABLE_HEADING}.",
                suggestion=f"Add the required {TABLE_HEADING} table to the sidecar.",
            )
        ]

    table_lines: List[str] = []
    for line in lines[heading_index + 1 :]:
        if re.match(r"^\s*#{1,6}\s+", line):
            break
        if line.strip().startswith("|"):
            table_lines.append(line)
        elif table_lines and line.strip():
            break
    if len(table_lines) < 2:
        return [], [
            make_finding(
                "named_feature_status_table_invalid",
                "error",
                heading_index + 1,
                message=f"{TABLE_HEADING} must contain a Markdown table.",
                suggestion="Add the required header, separator, and one row per detected name.",
            )
        ]

    headers = _split_table_row(table_lines[0])
    if tuple(headers) != REQUIRED_COLUMNS:
        return [], [
            make_finding(
                "named_feature_status_columns_invalid",
                "error",
                heading_index + 2,
                match=" | ".join(headers),
                message=f"{TABLE_HEADING} has invalid columns.",
                suggestion="Use the required columns in the documented order.",
            )
        ]

    rows = []
    for offset, line in enumerate(table_lines[2:], start=heading_index + 4):
        values = _split_table_row(line)
        if len(values) != len(headers):
            return [], [
                make_finding(
                    "named_feature_status_row_invalid",
                    "error",
                    offset,
                    match=line.strip(),
                    message="Named feature status table row has the wrong number of cells.",
                    suggestion="Provide all required status and commercial treatment cells.",
                )
            ]
        row = dict(zip(headers, values))
        row["_line"] = offset
        rows.append(row)
    return rows, []


def _split_table_row(line: str) -> List[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _resolve_vault_root(vault_path: str | Path | None) -> Path:
    if vault_path is not None:
        return Path(vault_path)
    env_path = os.environ.get("SIMPRO_BRAND_CONTEXT_VAULT")
    if env_path:
        return Path(env_path)
    return DEFAULT_VAULT_ROOT


def _load_claim_index(vault_root: Path) -> Dict[str, List[dict]]:
    path = vault_root / CLAIM_INDEX_PATH
    if not path.exists():
        raise OSError(f"missing {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "claim_id" not in rows[0]:
        raise ValueError(f"invalid columns in {path}")
    by_id: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        claim_id = row.get("claim_id", "").strip()
        if claim_id:
            by_id[claim_id].append(row)
    return by_id


def _validate_row(
    name: str,
    line: int,
    row: dict,
    public_body: str,
    claims_by_id: Dict[str, List[dict]],
) -> List[Finding]:
    findings: List[Finding] = []
    row_line = int(row.get("_line", line))
    release_status = row.get("Release status", "").strip()
    treatment = row.get("Commercial treatment", "").strip()
    wording = row.get("Public wording decision", "").strip()

    if release_status not in ALLOWED_RELEASE_STATUSES:
        findings.append(
            make_finding(
                "named_feature_release_status_invalid",
                "error",
                row_line,
                match=release_status,
                message=f"{name} has an invalid release status.",
                suggestion="Use an allowed release status value.",
            )
        )
    if treatment not in ALLOWED_COMMERCIAL_TREATMENTS:
        findings.append(
            make_finding(
                "named_feature_commercial_treatment_invalid",
                "error",
                row_line,
                match=treatment,
                message=f"{name} has an invalid commercial treatment.",
                suggestion="Use an allowed commercial treatment value.",
            )
        )
    if wording not in ALLOWED_WORDING_DECISIONS:
        findings.append(
            make_finding(
                "named_feature_public_wording_invalid",
                "error",
                row_line,
                match=wording,
                message=f"{name} has an invalid public wording decision.",
                suggestion="Use use, qualify, or omit.",
            )
        )
    if not row.get("Region or account boundary", "").strip():
        findings.append(
            make_finding(
                "named_feature_boundary_missing",
                "error",
                row_line,
                match=name,
                message=f"{name} is missing a region or account boundary.",
                suggestion="Document the applicable region, package, account, or availability boundary.",
            )
        )

    capability_ids = _split_claim_ids(row.get("Capability claim ID", ""))
    commercial_ids = _split_claim_ids(row.get("Commercial claim ID", ""))
    unusable_claim = False
    if not capability_ids:
        findings.append(
            make_finding(
                "named_feature_capability_claim_missing",
                "error",
                row_line,
                match=name,
                message=f"{name} is missing a capability claim ID.",
                suggestion="Add the current usable vault claim ID or set the wording decision to omit.",
            )
        )
        unusable_claim = True

    for claim_id in capability_ids + commercial_ids:
        claim_findings = _validate_claim_id(claim_id, row_line, claims_by_id)
        if claim_findings:
            unusable_claim = True
            findings.extend(claim_findings)

    commercial_asserted = _commercial_asserted_for_name(public_body, name)
    if commercial_asserted and treatment == "not_asserted":
        findings.append(
            make_finding(
                "named_feature_commercial_treatment_required",
                "error",
                row_line,
                match=name,
                message=f"Public copy makes a commercial statement about {name}.",
                suggestion="Record the supported commercial treatment and current claim ID.",
            )
        )
    if treatment in ALLOWED_COMMERCIAL_TREATMENTS - {"not_asserted"} and not commercial_ids:
        findings.append(
            make_finding(
                "named_feature_commercial_claim_missing",
                "error",
                row_line,
                match=name,
                message=f"{name} asserts commercial treatment without a commercial claim ID.",
                suggestion="Add a current usable commercial claim ID or remove the commercial assertion.",
            )
        )

    if name == "Intelligent AI Scheduler":
        if release_status != "target_timed" or not {"LCUR-0022", "LCUR-0023"}.issubset(
            set(capability_ids)
        ):
            findings.append(
                make_finding(
                    "named_feature_scheduler_requirement_missing",
                    "error",
                    row_line,
                    match=name,
                    message=(
                        "Intelligent AI Scheduler requires the current capability row, "
                        "target timing, and the RAIN Lightning requirement row."
                    ),
                    suggestion="Use target_timed with LCUR-0023 and LCUR-0022, or omit the feature.",
                )
            )
    if unusable_claim and wording != "omit":
        findings.append(
            make_finding(
                "named_feature_public_wording_must_omit",
                "error",
                row_line,
                match=name,
                message=f"{name} lacks current usable evidence but is not marked omit.",
                suggestion="Set Public wording decision to omit and remove the unsupported public copy.",
            )
        )
    return findings


def _split_claim_ids(value: str) -> List[str]:
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def _validate_claim_id(
    claim_id: str,
    line: int,
    claims_by_id: Dict[str, List[dict]],
) -> List[Finding]:
    rows = claims_by_id.get(claim_id, [])
    if len(rows) != 1:
        rule_id = (
            "named_feature_claim_id_missing"
            if not rows
            else "named_feature_claim_id_duplicate"
        )
        return [
            make_finding(
                rule_id,
                "error",
                line,
                match=claim_id,
                message=f"Claim ID {claim_id} does not resolve uniquely in the vault index.",
                suggestion="Use one current unique claim row from lightning-current-claim-status.csv.",
            )
        ]

    row = rows[0]
    evidence = row.get("evidence_status", "").strip().lower()
    public_status = row.get("public_use_status", "").strip().lower()
    allowed_use = row.get("agent_allowed_use", "").strip().lower()
    effective_to = row.get("effective_to", "").strip()
    expired = False
    if effective_to:
        try:
            expired = date.fromisoformat(effective_to) < date.today()
        except ValueError:
            expired = True
    blocked = (
        expired
        or "superseded" in evidence
        or "expired" in evidence
        or "internal" in evidence
        or "do_not_use" in evidence
        or public_status in {"internal_only", "do_not_use_current"}
        or not public_status.startswith("usable_public")
        or "do not use" in allowed_use
    )
    if not blocked:
        return []
    return [
        make_finding(
            "named_feature_claim_unusable",
            "error",
            line,
            match=claim_id,
            message=f"Claim ID {claim_id} is not current usable public evidence.",
            suggestion="Replace it with a current usable public claim row or omit the feature wording.",
        )
    ]


def _commercial_asserted_for_name(content: str, name: str) -> bool:
    alias_patterns = dict(FEATURE_ALIASES)[name]
    for paragraph in re.split(r"\n\s*\n", content):
        if not COMMERCIAL_RE.search(paragraph):
            continue
        if any(re.search(pattern, paragraph, re.IGNORECASE) for pattern in alias_patterns):
            return True
    return False


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate named feature status and commercial treatment."
    )
    parser.add_argument("path", help="Markdown article path")
    parser.add_argument("--proof-sidecar", help="Validation sidecar path")
    parser.add_argument("--vault-path", help="Simpro Brand Context vault path")
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
        vault_path=args.vault_path,
    )
    payload = {
        "path": args.path,
        "proof_sidecar": args.proof_sidecar,
        "vault_path": args.vault_path,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
