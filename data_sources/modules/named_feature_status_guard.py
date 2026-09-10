"""Validate named Lightning feature status and commercial treatment."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import urlparse

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_link_policy import (
        ProofLinkReport,
        analyze_proof_links,
        canonicalize_link_identity,
        is_generic_proof_anchor,
    )
    from .proof_sidecar import load_sidecar_content
    from .vault_claim_receipts import (
        VaultClaimReceiptError,
        ValidatedClaimSet,
        load_validated_claim_set,
    )
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_link_policy import (
        ProofLinkReport,
        analyze_proof_links,
        canonicalize_link_identity,
        is_generic_proof_anchor,
    )
    from proof_sidecar import load_sidecar_content
    from vault_claim_receipts import (
        VaultClaimReceiptError,
        ValidatedClaimSet,
        load_validated_claim_set,
    )

TABLE_HEADING = "Named Feature Status and Commercial Treatment"
LINK_TABLE_HEADING = "Named Feature/Add-On Link Check"
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
ALLOWED_WORDING_DECISIONS = {"use", "qualify", "omit", "navigation_only"}
LINK_REQUIRED_COLUMNS = ("Name", "Resource ID", "Link decision", "Target URL", "Reason")
ALLOWED_LINK_DECISIONS = {"link", "do_not_link"}
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
CONTEXT_FEATURE_ROLE_MARKERS = {
    "add on",
    "addon",
    "feature",
    "feature guidance",
    "feature status",
    "named feature",
    "product feature",
}
NON_FEATURE_ENTITIES = {
    "aroflo",
    "bigchange",
    "clockshark",
    "simpro",
    "field service",
    "field service management",
}
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[([^\]]+)\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+['\"][^)]*['\"])?\s*\)"
)
RESOURCE_FRONTMATTER_RE = re.compile(
    r"\A---\s*\r?\n(?P<metadata>.*?)\r?\n---(?:\r?\n|\Z)",
    re.DOTALL,
)


def check_content(
    content: str,
    proof_content: str | None = None,
    vault_path: str | Path | None = None,
    vault_root: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    validated_claim_set: ValidatedClaimSet | None = None,
) -> List[Finding]:
    """Return status, evidence-binding, and article-link findings for named features."""
    public_body = _public_body(content)
    detected = _detect_features(public_body)
    feature_resources: Dict[str, set[str]] = defaultdict(set)
    findings: List[Finding] = []

    explicit_vault_root = vault_root if vault_root is not None else vault_path
    receipt_claims = ValidatedClaimSet(
        blocker="context pack and receipt are required for public proof eligibility"
    )
    if validated_claim_set is not None:
        receipt_claims = validated_claim_set
    elif detected or context_pack or context_receipt:
        try:
            receipt_claims = load_validated_claim_set(
                context_pack,
                context_receipt,
                vault_root=explicit_vault_root,
            )
        except VaultClaimReceiptError as exc:
            findings.append(
                make_finding(
                    "named_feature_context_receipt_invalid",
                    "error",
                    1,
                    message=f"Named feature context receipt could not be verified: {exc}",
                    suggestion=(
                        "Regenerate the vault context pack and receipt before using "
                        "named feature claims."
                    ),
                )
            )
            receipt_claims = ValidatedClaimSet(blocker=str(exc))

    context_pack_object = _load_context_pack_object(context_pack) if context_pack else {}
    bound_context_resource_ids = _all_resource_ids(context_pack_object)
    if receipt_claims.available and context_pack:
        context_detected, context_resources = _detect_context_features(
            public_body,
            context_pack_object,
        )
        for name, line in context_detected.items():
            existing_name = next(
                (
                    detected_name
                    for detected_name in detected
                    if _normalize_name(detected_name) == _normalize_name(name)
                ),
                None,
            )
            detected.setdefault(existing_name or name, line)
            feature_resources[existing_name or name].update(context_resources.get(name, set()))

    if not detected:
        return []

    proof_text = proof_content or ""
    proof_link_report = analyze_proof_links(
        public_body,
        proof_text,
        brand="Simpro",
    )
    rows, table_findings = _parse_status_table(proof_text)
    findings.extend(table_findings)
    link_rows, link_findings = _parse_link_table(proof_text)
    findings.extend(link_findings)
    rows_by_name: Dict[str, List[dict]] = defaultdict(list)
    for row in rows:
        rows_by_name[_normalize_name(row.get("Name", ""))].append(row)
    link_rows_by_name: Dict[str, List[dict]] = defaultdict(list)
    for row in link_rows:
        link_rows_by_name[_normalize_name(row.get("Name", ""))].append(row)

    if not receipt_claims.available:
        findings.append(
            make_finding(
                "named_feature_context_receipt_missing",
                "error",
                1,
                message="Named feature public eligibility requires a validated context receipt.",
                suggestion="Provide simpro-product-context-pack/v2 and simpro-context-receipt/v1 inputs.",
            )
        )

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
                receipt_claims,
            )
        )
        findings.extend(
            _validate_link_row(
                name,
                line,
                row,
                link_rows_by_name.get(_normalize_name(name), []),
                receipt_claims,
                public_body,
                feature_resources.get(name, set()),
                bound_context_resource_ids,
                proof_link_report,
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
    vault_root: str | Path | None = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
    validated_claim_set: ValidatedClaimSet | None = None,
) -> List[Finding]:
    """Check an article and its validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    content = Path(path).read_text(encoding="utf-8")
    proof_content = load_sidecar_content(path, proof_sidecar)
    return check_content(
        content,
        proof_content=proof_content,
        vault_path=vault_path,
        vault_root=vault_root,
        context_pack=context_pack,
        context_receipt=context_receipt,
        validated_claim_set=validated_claim_set,
    )


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


def _load_context_pack_object(context_pack: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(context_pack).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _detect_context_features(
    content: str,
    pack: Mapping[str, Any],
) -> tuple[Dict[str, int], Dict[str, set[str]]]:
    """Find article feature names from connector-validated semantic evidence."""
    sections = pack.get("sections")
    if not isinstance(sections, Mapping):
        return {}, {}

    candidates: Dict[str, set[str]] = defaultdict(set)
    guidance = sections.get("Retrieved Guidance")
    if isinstance(guidance, list):
        for resource in guidance:
            if not isinstance(resource, Mapping):
                continue
            resource_id = _valid_resource_id(resource.get("resource_id"))
            metadata = _resource_frontmatter(str(resource.get("content") or ""))
            roles = _record_values(resource, "semantic_roles", "roles")
            roles.extend(_metadata_values(metadata, "semantic_roles", "roles"))
            if not _has_feature_semantics(roles):
                continue
            names = _record_values(
                resource,
                "feature_names",
                "named_features",
                "entities",
                "aliases",
            )
            names.extend(
                _metadata_values(
                    metadata,
                    "feature_names",
                    "named_features",
                    "entities",
                    "aliases",
                )
            )
            _add_feature_candidates(candidates, names, resource_id)

    evidence = sections.get("Approved Claim Evidence")
    if isinstance(evidence, list):
        for claim in evidence:
            if not isinstance(claim, Mapping):
                continue
            semantics = _record_values(claim, "semantic_roles", "topics")
            semantics.append(str(claim.get("claim_type") or ""))
            if not _has_feature_semantics(semantics):
                continue
            resource_id = _valid_resource_id(claim.get("authority_resource_id"))
            _add_feature_candidates(
                candidates,
                _record_values(
                    claim,
                    "feature_names",
                    "named_features",
                    "entities",
                    "aliases",
                ),
                resource_id,
            )

    detected: Dict[str, int] = {}
    resources: Dict[str, set[str]] = {}
    for name, resource_ids in candidates.items():
        match = _feature_name_match(content, name)
        if match is None:
            continue
        detected[name] = content.count("\n", 0, match.start()) + 1
        resources[name] = set(resource_ids)
    return detected, resources


def _valid_resource_id(value: object) -> str:
    resource_id = str(value or "").strip()
    return resource_id if re.fullmatch(r"res-[0-9a-f]{32}", resource_id) else ""


def _all_resource_ids(value: Any) -> set[str]:
    resource_ids: set[str] = set()
    if isinstance(value, Mapping):
        for field in ("resource_id", "authority_resource_id"):
            resource_id = _valid_resource_id(value.get(field))
            if resource_id:
                resource_ids.add(resource_id)
        support_resource_ids = value.get("support_resource_ids")
        if isinstance(support_resource_ids, list):
            resource_ids.update(
                resource_id
                for item in support_resource_ids
                if (resource_id := _valid_resource_id(item))
            )
        for nested in value.values():
            resource_ids.update(_all_resource_ids(nested))
    elif isinstance(value, list):
        for nested in value:
            resource_ids.update(_all_resource_ids(nested))
    return resource_ids


def _record_values(record: Mapping[str, Any], *fields: str) -> List[str]:
    values: List[str] = []
    for field in fields:
        raw = record.get(field)
        if isinstance(raw, str):
            values.append(raw)
        elif isinstance(raw, list):
            values.extend(str(item) for item in raw if isinstance(item, str))
    return values


def _resource_frontmatter(content: str) -> str:
    match = RESOURCE_FRONTMATTER_RE.match(content)
    return match.group("metadata") if match else ""


def _metadata_values(metadata: str, *fields: str) -> List[str]:
    values: List[str] = []
    lines = metadata.splitlines()
    wanted = {_normalize_name(field).replace(" ", "_") for field in fields}
    index = 0
    while index < len(lines):
        match = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", lines[index])
        if not match or match.group(1).casefold().replace("-", "_") not in wanted:
            index += 1
            continue
        inline = match.group(2).strip()
        if inline.startswith("[") and inline.endswith("]"):
            values.extend(
                item.strip().strip("'\"")
                for item in inline[1:-1].split(",")
                if item.strip().strip("'\"")
            )
        elif inline:
            values.append(inline.strip("'\""))
        index += 1
        while index < len(lines):
            item = re.match(r"^\s+-\s+(.+?)\s*$", lines[index])
            if not item:
                break
            value = item.group(1).strip().strip("'\"")
            if value:
                values.append(value)
            index += 1
    return values


def _has_feature_semantics(values: Sequence[str]) -> bool:
    normalized = {_normalize_name(value) for value in values if str(value).strip()}
    return any(
        marker == value or marker in value
        for value in normalized
        for marker in CONTEXT_FEATURE_ROLE_MARKERS
    )


def _add_feature_candidates(
    candidates: Dict[str, set[str]],
    values: Sequence[str],
    resource_id: str,
) -> None:
    known_names = {_normalize_name(name): name for name, _aliases in FEATURE_ALIASES}
    for raw in values:
        name = re.sub(r"\s+", " ", str(raw or "")).strip()
        if name.casefold().startswith("simpro "):
            name = name[7:].strip()
        normalized = _normalize_name(name)
        if (
            not normalized
            or normalized in NON_FEATURE_ENTITIES
            or len(name) > 80
            or len(name.split()) > 8
            or not re.search(r"[A-Za-z]", name)
            or "://" in name
        ):
            continue
        canonical = known_names.get(normalized, name)
        if resource_id:
            candidates[canonical].add(resource_id)
        else:
            candidates.setdefault(canonical, set())


def _feature_name_match(content: str, name: str) -> re.Match[str] | None:
    aliases = dict(FEATURE_ALIASES).get(name)
    patterns = aliases or (rf"(?<!\w)(?:Simpro\s+)?{re.escape(name)}(?!\w)",)
    matches = [
        match
        for pattern in patterns
        if (match := re.search(pattern, content, re.IGNORECASE)) is not None
    ]
    return min(matches, key=lambda match: match.start()) if matches else None

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


def _parse_link_table(proof_content: str) -> tuple[List[dict], List[Finding]]:
    lines = proof_content.splitlines()
    heading_index = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(
                rf"^\s*#{{1,6}}\s+{re.escape(LINK_TABLE_HEADING)}\s*$",
                line,
                re.IGNORECASE,
            )
        ),
        None,
    )
    if heading_index is None:
        return [], [
            make_finding(
                "named_feature_link_check_missing",
                "error",
                1,
                message=f"Validation sidecar is missing {LINK_TABLE_HEADING}.",
                suggestion="Add one receipt-bound link decision row per detected feature.",
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
                "named_feature_link_check_invalid",
                "error",
                heading_index + 1,
                message=f"{LINK_TABLE_HEADING} must contain a Markdown table.",
                suggestion="Add the required link-check columns and feature rows.",
            )
        ]
    headers = _split_table_row(table_lines[0])
    if tuple(headers) != LINK_REQUIRED_COLUMNS:
        return [], [
            make_finding(
                "named_feature_link_check_columns_invalid",
                "error",
                heading_index + 2,
                match=" | ".join(headers),
                message=f"{LINK_TABLE_HEADING} has invalid columns.",
                suggestion="Use Name, Resource ID, Link decision, Target URL, and Reason.",
            )
        ]
    rows: List[dict] = []
    for offset, line in enumerate(table_lines[2:], start=heading_index + 4):
        values = _split_table_row(line)
        if len(values) != len(headers):
            return [], [
                make_finding(
                    "named_feature_link_check_row_invalid",
                    "error",
                    offset,
                    match=line.strip(),
                    message="Named feature link-check row has the wrong number of cells.",
                    suggestion="Provide every required link-check cell.",
                )
            ]
        row = dict(zip(headers, values))
        row["_line"] = offset
        rows.append(row)
    return rows, []


def _validate_link_row(
    name: str,
    line: int,
    status_row: dict,
    link_rows: List[dict],
    receipt_claims: ValidatedClaimSet,
    public_body: str,
    context_resource_ids: set[str],
    bound_context_resource_ids: set[str],
    proof_link_report: ProofLinkReport,
) -> List[Finding]:
    if not link_rows:
        return [
            make_finding(
                "named_feature_link_check_row_missing",
                "error",
                line,
                match=name,
                message=f"{name} has no feature/add-on link decision row.",
                suggestion="Add a receipt-bound resource ID, link decision, and reason.",
            )
        ]
    if len(link_rows) > 1:
        return [
            make_finding(
                "named_feature_link_check_row_duplicate",
                "error",
                line,
                match=name,
                message=f"{name} has more than one feature/add-on link decision row.",
                suggestion="Keep exactly one link decision row for the feature.",
            )
        ]
    row = link_rows[0]
    row_line = int(row.get("_line", line))
    findings: List[Finding] = []
    navigation_only = (
        str(status_row.get("Public wording decision") or "").strip().casefold()
        == "navigation_only"
    )
    resource_id = str(row.get("Resource ID") or "").strip()
    if not re.fullmatch(r"res-[0-9a-f]{32}", resource_id):
        findings.append(
            make_finding(
                "named_feature_link_resource_id_invalid",
                "error",
                row_line,
                match=resource_id,
                message=f"{name} link check requires one connector resource ID.",
                suggestion="Use the exact feature resource ID selected into the validated context.",
            )
        )
    selector_ids = set(
        _split_claim_ids(status_row.get("Capability claim ID", ""))
        + _split_claim_ids(status_row.get("Commercial claim ID", ""))
    )
    approved_claims = tuple(
        claim
        for claim in receipt_claims.approved_claims()
        if claim.selector_id in selector_ids
        and claim.use_mode in {"public_paraphrase", "public_metric"}
    )
    allowed_resources = {
        claim.authority_resource_id
        for claim in approved_claims
        if claim.authority_resource_id
    }
    if resource_id and resource_id not in allowed_resources and not (
        navigation_only and resource_id in bound_context_resource_ids
    ):
        findings.append(
            make_finding(
                "named_feature_link_resource_id_unbound",
                "error",
                row_line,
                match=resource_id,
                message=f"{name} link-check resource is not bound to its receipt-approved claims.",
                suggestion="Use the authority resource ID from the validated claim evidence.",
            )
        )
    if context_resource_ids and resource_id not in context_resource_ids:
        findings.append(
            make_finding(
                "named_feature_link_resource_not_feature_evidence",
                "error",
                row_line,
                match=resource_id,
                message=f"{name} link-check resource is not the context resource that identified the feature.",
                suggestion="Use the feature resource ID from the validated context pack.",
            )
        )

    approved_public_urls = {
        canonicalize_link_identity(claim.public_url)
        for claim in approved_claims
        if claim.authority_resource_id == resource_id and claim.public_url
    }
    status_requirements = tuple(
        requirement
        for requirement in proof_link_report.requirements
        if requirement.owner == "named_feature_status"
        and requirement.mode == "inline_required"
        and _feature_name_match(requirement.claim, name) is not None
    )
    for requirement in status_requirements:
        requirement_urls = set(requirement.approved_urls) & approved_public_urls
        natural_inline_urls = {
            link.canonical_url
            for link in proof_link_report.links
            if requirement.line <= link.line <= requirement.end_line
            and not is_generic_proof_anchor(link.anchor)
        }
        if not requirement_urls.intersection(natural_inline_urls):
            findings.append(
                make_finding(
                    "named_feature_inline_status_link_missing",
                    "error",
                    requirement.line,
                    match=name,
                    message=(
                        f"{name} status or availability wording requires a natural "
                        "same-paragraph or table-row link to its receipt-approved URL."
                    ),
                    suggestion=(
                        "Link descriptive feature-status wording to the canonical approved "
                        "public URL; do_not_link, generic anchors, and bare URLs cannot "
                        "satisfy an inline-required claim."
                    ),
                )
            )

    decision = str(row.get("Link decision") or "").strip().casefold()
    if decision not in ALLOWED_LINK_DECISIONS:
        findings.append(
            make_finding(
                "named_feature_link_decision_invalid",
                "error",
                row_line,
                match=decision,
                message=f"{name} has an invalid link decision.",
                suggestion="Use link or do_not_link.",
            )
        )
    target_url = str(row.get("Target URL") or "").strip()
    if decision == "link" and not target_url.startswith(("http://", "https://")):
        findings.append(
            make_finding(
                "named_feature_link_target_missing",
                "error",
                row_line,
                match=name,
                message=f"{name} is marked link but has no public HTTP(S) target.",
                suggestion="Add the selected public target URL or use do_not_link.",
            )
        )
    if decision == "link" and target_url.startswith(("http://", "https://")):
        normalized_target = _normalize_public_url(target_url)
        approved_urls = {
            _normalize_public_url(claim.public_url)
            for claim in approved_claims
            if claim.authority_resource_id == resource_id and claim.public_url
        }
        if normalized_target not in approved_urls and not (
            navigation_only
            and urlparse(target_url).hostname in {"simprogroup.com", "www.simprogroup.com"}
        ):
            findings.append(
                make_finding(
                    "named_feature_link_target_unbound",
                    "error",
                    row_line,
                    match=target_url,
                    message=f"{name} link target is not approved by its receipt-bound claim evidence.",
                    suggestion="Use the public URL on the approved feature claim.",
                )
            )
        article_links = _article_links(public_body)
        if normalized_target not in {
            _normalize_public_url(link["url"]) for link in article_links
        }:
            findings.append(
                make_finding(
                    "named_feature_link_target_not_in_article",
                    "error",
                    line,
                    match=target_url,
                    message=f"{name} link target does not appear in the public article.",
                    suggestion="Link the first meaningful feature mention to the audited target URL.",
                )
            )
        first_mention_link = _first_meaningful_mention_link(public_body, name, article_links)
        has_meaningful_mention = _has_meaningful_mention(public_body, name)
        if (
            first_mention_link is None
            or _normalize_public_url(first_mention_link) != normalized_target
        ) and not (
            navigation_only
            and first_mention_link is None
            and not has_meaningful_mention
            and normalized_target
            in {_normalize_public_url(link["url"]) for link in article_links}
        ):
            findings.append(
                make_finding(
                    "named_feature_first_mention_link_mismatch",
                    "error",
                    line,
                    match=name,
                    message=f"{name}'s first meaningful public mention is not linked to the audited target.",
                    suggestion="Use the receipt-approved target on the first prose mention of the feature.",
                )
            )
    if not str(row.get("Reason") or "").strip():
        findings.append(
            make_finding(
                "named_feature_link_reason_missing",
                "error",
                row_line,
                match=name,
                message=f"{name} link decision has no reason.",
                suggestion="Explain the connector-backed link or no-link decision.",
            )
        )
    return findings


def _article_links(content: str) -> List[dict[str, Any]]:
    links: List[dict[str, Any]] = []
    for match in MARKDOWN_LINK_RE.finditer(content):
        links.append(
            {
                "anchor": match.group(1),
                "url": (match.group(2) or match.group(3) or "").strip(),
                "start": match.start(),
                "end": match.end(),
                "anchor_start": match.start(1),
                "anchor_end": match.end(1),
            }
        )
    return links


def _first_meaningful_mention_link(
    content: str,
    name: str,
    links: Sequence[Mapping[str, Any]],
) -> str | None:
    match = _feature_name_match(_without_markdown_headings(content), name)
    if match is None:
        return None
    for link in links:
        if int(link["anchor_start"]) <= match.start() < int(link["anchor_end"]):
            return str(link["url"])
    return None


def _has_meaningful_mention(content: str, name: str) -> bool:
    return _feature_name_match(_without_markdown_headings(content), name) is not None


def _without_markdown_headings(content: str) -> str:
    searchable = list(content)
    offset = 0
    for line in content.splitlines(keepends=True):
        if re.match(r"^\s*#{1,6}\s+", line):
            for index in range(offset, offset + len(line.rstrip("\r\n"))):
                searchable[index] = " "
        offset += len(line)
    for link in MARKDOWN_LINK_RE.finditer(content):
        for group_index in (2, 3):
            start = link.start(group_index)
            end = link.end(group_index)
            if start >= 0 and end >= 0:
                for index in range(start, end):
                    searchable[index] = " "
    return "".join(searchable)


def _normalize_public_url(value: str) -> str:
    return canonicalize_link_identity(str(value or ""))

def _validate_row(
    name: str,
    line: int,
    row: dict,
    public_body: str,
    receipt_claims: ValidatedClaimSet,
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
            suggestion="Use use, qualify, omit, or navigation_only.",
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
    if not capability_ids and wording != "navigation_only":
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
        claim_findings = _validate_claim_id(
            claim_id,
            row_line,
            receipt_claims,
        )
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
    receipt_claims: ValidatedClaimSet,
) -> List[Finding]:
    approved_claim = receipt_claims.require_selector_claim(
        claim_id,
        use_modes={"public_paraphrase", "public_metric"},
    )
    if approved_claim is not None:
        return []
    return [
        make_finding(
            "named_feature_claim_not_receipt_approved",
            "error",
            line,
            match=claim_id,
            message=f"Claim ID {claim_id} is not approved by the validated context receipt.",
            suggestion="Use a receipt-approved connector claim result or omit the feature wording.",
        )
    ]


def _commercial_asserted_for_name(content: str, name: str) -> bool:
    alias_patterns = dict(FEATURE_ALIASES).get(
        name,
        (rf"(?<!\w){re.escape(name)}(?!\w)",),
    )
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
    parser.add_argument("--vault-root", help="Configured Simpro vault root override")
    parser.add_argument("--context-pack", help="simpro-product-context-pack/v2 JSON path")
    parser.add_argument("--context-receipt", help="simpro-context-receipt/v1 JSON path")
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
        vault_root=args.vault_root,
        context_pack=args.context_pack,
        context_receipt=args.context_receipt,
    )
    payload = {
        "path": args.path,
        "proof_sidecar": args.proof_sidecar,
        "vault_root": args.vault_root,
        "context_pack": args.context_pack,
        "context_receipt": args.context_receipt,
        "fail_on": args.fail_on,
        "summary": summarize_findings(findings),
        "findings": findings,
    }
    print(json.dumps(payload, indent=2))
    return 1 if should_fail(findings, fail_on=args.fail_on) else 0


if __name__ == "__main__":
    sys.exit(main())
