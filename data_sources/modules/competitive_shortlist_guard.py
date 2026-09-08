"""Validate vault-authorized competitive shortlist decisions for blog copy.

Public SERP pages can shape article format, but only a connector-validated
context pack and receipt can authorize the named competitive shortlist.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .blog_assembly_contract import load_json_object_snapshot
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
    from .vault_claim_receipts import (
        VaultClaimReceiptError,
        ValidatedClaimSet,
        load_validated_claim_set,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import load_json_object_snapshot
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content
    from vault_claim_receipts import (
        VaultClaimReceiptError,
        ValidatedClaimSet,
        load_validated_claim_set,
    )


HEADING_RE = re.compile(r"^##\s+Competitive Shortlist Decision\s*$", re.IGNORECASE)
NEXT_H2_RE = re.compile(r"^##\s+")
FIELD_RE = re.compile(r"^\s*[-*+]\s*([^:]+):\s*(.*?)\s*$")
COMPETITOR_TRIGGER_RE = re.compile(
    r"\b(?:competitors?|alternatives?|compare|comparison|versus|vs\.?)\b",
    re.IGNORECASE,
)
SIMPRO_VS_RE = re.compile(
    r"\bSimpro\s+(?:vs\.?|versus)\s+([A-Z][A-Za-z0-9&.+ -]{1,60})|"
    r"\b([A-Z][A-Za-z0-9&.+ -]{1,60})\s+(?:vs\.?|versus)\s+Simpro\b",
    re.IGNORECASE,
)
PUBLIC_CLAIM_SIGNAL_RE = re.compile(
    r"\b(?:is|are|offers?|provides?|includes?|supports?|costs?|charges?|"
    r"better|worse|faster|slower|more|less|guarantees?|ensures?|always|never)\b",
    re.IGNORECASE,
)
RESOURCE_ID_RE = re.compile(r"^res-[0-9a-f]{32}$")
TABLE_COLUMNS = (
    "Competitor",
    "Decision",
    "Reason",
    "Resource ID",
    "Claim ID",
    "Public URL",
)
ALLOWED_PUBLIC_USE_MODES = frozenset(
    {"public_paraphrase", "public_metric", "exact_quote"}
)


@dataclass(frozen=True)
class ShortlistRow:
    competitor: str
    decision: str
    reason: str
    resource_id: str
    claim_id: str
    public_url: str
    line: int


def check_content(
    content: str,
    *,
    proof_content: str | None = None,
    context_pack: Mapping[str, Any] | str | Path | None = None,
    context_receipt: Mapping[str, Any] | str | Path | None = None,
    vault_root: str | Path | None = None,
) -> list[Finding]:
    """Return competitive-shortlist findings for the exact public snapshot."""
    if not _is_competitor_aware(content):
        return []
    block = _extract_block(proof_content or "")
    if block is None:
        return [_finding(
            "competitive_shortlist_missing",
            1,
            "Competitor-aware public copy has no Competitive Shortlist Decision.",
            "Add a connector-bound selected and rejected shortlist decision to the validation sidecar.",
        )]

    fields, rows, line = block
    findings: list[Finding] = []
    objective = _frontmatter_field(content, "objective")
    if fields.get("article objective", "") != objective:
        findings.append(_finding(
            "competitive_shortlist_objective_mismatch",
            line,
            "Competitive shortlist objective does not match the exact article objective.",
            "Use the unchanged frontmatter objective in the shortlist decision.",
        ))
    if fields.get("authority", "").casefold() != "vault connector":
        findings.append(_finding(
            "competitive_shortlist_authority_invalid",
            line,
            "Competitive shortlist authority must be the vault connector.",
            "Use public SERP pages for format research only, then select competitors from connector evidence.",
        ))
    if fields.get("status", "").casefold() != "approved":
        findings.append(_finding(
            "competitive_shortlist_status_invalid",
            line,
            "Competitive shortlist status is not approved.",
            "Set Status: approved only after connector evidence and the article snapshot agree.",
        ))
    selected = [row for row in rows if row.decision == "selected"]
    rejected = [row for row in rows if row.decision == "rejected"]
    if not selected or not rejected:
        findings.append(_finding(
            "competitive_shortlist_rows_missing",
            line,
            "Competitive shortlist must contain at least one selected and one rejected decision.",
            "Add objective-specific selected and rejected competitor rows.",
        ))
    for row in rows:
        if not row.competitor or not row.reason or row.decision not in {"selected", "rejected"}:
            findings.append(_finding(
                "competitive_shortlist_row_invalid",
                row.line,
                "Competitive shortlist row is incomplete.",
                "Provide competitor, selected or rejected decision, and an objective-specific reason.",
                match=row.competitor,
            ))

    pack = _load_mapping(context_pack, "context pack", findings, line)
    receipt = _load_mapping(context_receipt, "context receipt", findings, line)
    claims = _validated_claims(context_pack, context_receipt, findings, line, vault_root)
    pack_resources = _resource_records(pack)
    receipt_resource_ids = _resource_ids(receipt)
    for row in rows:
        record = pack_resources.get(row.resource_id)
        if (
            not RESOURCE_ID_RE.fullmatch(row.resource_id)
            or record is None
            or row.resource_id not in receipt_resource_ids
        ):
            findings.append(_finding(
                "competitive_shortlist_resource_unbound",
                row.line,
                "Competitive decision resource is not bound to the validated context pack and receipt.",
                "Use the connector resource ID that supplied competitive context for this competitor.",
                match=row.resource_id,
            ))
        elif row.competitor.casefold() not in _flatten_text(record).casefold():
            findings.append(_finding(
                "competitive_shortlist_resource_mismatch",
                row.line,
                "Competitive decision resource does not identify the named competitor.",
                "Use the competitor-specific resource selected by connector search and read/expand.",
                match=row.competitor,
            ))

    selected_names = {row.competitor.casefold(): row for row in selected}
    public_names = _public_competitor_names(content, claims)
    for public_name in public_names:
        row = selected_names.get(public_name.casefold())
        if row is None:
            findings.append(_finding(
                "competitive_shortlist_public_competitor_not_selected",
                1,
                f"Public copy names {public_name}, but the competitor is not selected.",
                "Select the public competitor with connector evidence or remove it from public copy.",
                match=public_name,
            ))
            continue
        if _has_public_competitor_claim(content, public_name):
            matching_claim = next(
                (
                    claim for claim in claims.approved_claims()
                    if claim.claim_id == row.claim_id
                    and claim.use_mode in ALLOWED_PUBLIC_USE_MODES
                ),
                None,
            )
            if matching_claim is None:
                findings.append(_finding(
                    "competitive_shortlist_claim_unapproved",
                    row.line,
                    "Public competitor claim is not approved by the validated context receipt.",
                    "Use the exact receipt-approved claim ID for the public competitor statement.",
                    match=row.claim_id,
                ))
            else:
                if matching_claim.public_url != row.public_url:
                    findings.append(_finding(
                        "competitive_shortlist_public_url_mismatch",
                        row.line,
                        "Competitive shortlist public URL does not match the approved claim.",
                        "Use the public URL on the receipt-approved claim.",
                        match=row.public_url,
                    ))
                if matching_claim.authority_resource_id != row.resource_id:
                    findings.append(_finding(
                        "competitive_shortlist_claim_resource_mismatch",
                        row.line,
                        "Competitive claim and shortlist decision use different authority resources.",
                        "Use the authority resource ID bound to the approved claim.",
                        match=row.resource_id,
                    ))
    return sorted(findings, key=lambda item: (item["line"], item["rule_id"]))


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    vault_root: str | Path | None = None,
) -> list[Finding]:
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    article = Path(path)
    return check_content(
        article.read_text(encoding="utf-8"),
        proof_content=load_sidecar_content(article, proof_sidecar),
        context_pack=context_pack,
        context_receipt=context_receipt,
        vault_root=vault_root,
    )


def _is_competitor_aware(content: str) -> bool:
    return bool(COMPETITOR_TRIGGER_RE.search(_public_body(content)))


def _extract_block(proof: str) -> tuple[dict[str, str], list[ShortlistRow], int] | None:
    lines = proof.splitlines()
    start = next((index for index, value in enumerate(lines) if HEADING_RE.match(value)), None)
    if start is None:
        return None
    block_lines: list[tuple[int, str]] = []
    for index, value in enumerate(lines[start + 1 :], start=start + 2):
        if NEXT_H2_RE.match(value):
            break
        block_lines.append((index, value))
    fields: dict[str, str] = {}
    table_lines: list[tuple[int, str]] = []
    for line_number, value in block_lines:
        match = FIELD_RE.match(value)
        if match:
            fields[match.group(1).strip().casefold()] = match.group(2).strip()
        if value.strip().startswith("|"):
            table_lines.append((line_number, value))
    rows: list[ShortlistRow] = []
    if len(table_lines) >= 2 and tuple(_split_table(table_lines[0][1])) == TABLE_COLUMNS:
        for line_number, value in table_lines[2:]:
            cells = _split_table(value)
            if len(cells) != len(TABLE_COLUMNS):
                continue
            rows.append(ShortlistRow(
                competitor=cells[0],
                decision=cells[1].casefold(),
                reason=cells[2],
                resource_id=cells[3],
                claim_id=cells[4],
                public_url=cells[5],
                line=line_number,
            ))
    return fields, rows, start + 1


def _split_table(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _load_mapping(value: Mapping[str, Any] | str | Path | None, label: str,
                  findings: list[Finding], line: int) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if value is None:
        findings.append(_finding(
            "competitive_shortlist_context_missing",
            line,
            f"Competitive shortlist requires the validated {label}.",
            "Provide the exact context pack and receipt used by Context Binding.",
        ))
        return {}
    try:
        return load_json_object_snapshot(value, field=label).payload
    except ValueError as error:
        findings.append(_finding(
            "competitive_shortlist_context_invalid",
            line,
            f"Competitive shortlist {label} is invalid: {error}",
            "Regenerate the connector context artifacts.",
        ))
        return {}


def _validated_claims(context_pack: Any, context_receipt: Any,
                      findings: list[Finding], line: int,
                      vault_root: str | Path | None = None) -> ValidatedClaimSet:
    try:
        claims = load_validated_claim_set(
            context_pack,
            context_receipt,
            vault_root=vault_root,
        )
    except (VaultClaimReceiptError, OSError, ValueError, TypeError) as error:
        findings.append(_finding(
            "competitive_shortlist_context_unverified",
            line,
            f"Competitive shortlist context could not be connector-validated: {error}",
            "Regenerate and validate the vault context pack and receipt.",
        ))
        return ValidatedClaimSet(blocker=str(error))
    if not claims.available:
        findings.append(_finding(
            "competitive_shortlist_context_unverified",
            line,
            f"Competitive shortlist context is unavailable: {claims.blocker}",
            "Restore connector validation before authorizing a shortlist.",
        ))
    return claims


def _resource_records(pack: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            resource_id = value.get("resource_id")
            if isinstance(resource_id, str) and RESOURCE_ID_RE.fullmatch(resource_id):
                records.setdefault(resource_id, value)
            for nested in value.values():
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)
    visit(pack)
    return records


def _resource_ids(receipt: Mapping[str, Any]) -> set[str]:
    return set(_resource_records(receipt))


def _flatten_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_text(item) for item in value)
    return str(value or "")


def _public_competitor_names(content: str, claims: ValidatedClaimSet) -> set[str]:
    body = _public_body(content)
    names: set[str] = set()
    for match in SIMPRO_VS_RE.finditer(body):
        name = (match.group(1) or match.group(2) or "").strip(" .:-")
        if name:
            names.add(name)
    for claim in claims.approved_claims():
        if claim.claim_type.casefold().startswith("competitive"):
            for token in re.findall(r"\b[A-Z][A-Za-z0-9&.+-]{2,}\b", claim.assertion):
                if token.casefold() != "simpro" and re.search(
                    rf"(?<!\w){re.escape(token)}(?!\w)", body, re.IGNORECASE
                ):
                    names.add(token)
                    break
    return names


def _has_public_competitor_claim(content: str, competitor: str) -> bool:
    for line in _public_body(content).splitlines():
        if line.lstrip().startswith("#"):
            continue
        if re.search(rf"(?<!\w){re.escape(competitor)}(?!\w)", line, re.IGNORECASE) and PUBLIC_CLAIM_SIGNAL_RE.search(line):
            return True
    return False


def _frontmatter_field(content: str, field: str) -> str:
    match = re.search(rf"(?m)^{re.escape(field)}:\s*['\"]?(.*?)['\"]?\s*$", content)
    return match.group(1).strip() if match else ""


def _public_body(content: str) -> str:
    return re.sub(r"\A---\s*\r?\n.*?\r?\n---\s*", "", content, count=1, flags=re.DOTALL)


def _finding(rule_id: str, line: int, message: str, suggestion: str, *, match: str = "") -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        match=match,
        message=message,
        suggestion=suggestion,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a vault-backed competitive shortlist.")
    parser.add_argument("path")
    parser.add_argument("--proof-sidecar")
    parser.add_argument("--context-pack")
    parser.add_argument("--context-receipt")
    parser.add_argument("--fail-on", choices=["error", "warning", "none"], default="error")
    args = parser.parse_args(argv)
    findings = check_file(
        args.path,
        fail_on=args.fail_on,
        proof_sidecar=args.proof_sidecar,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
    )
    print(json.dumps({"path": args.path, "summary": summarize_findings(findings), "findings": findings}, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
