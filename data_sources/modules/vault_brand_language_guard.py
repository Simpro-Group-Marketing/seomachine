"""
Vault brand-language guard.

Validates that Simpro product, feature, add-on, solution, and vertical copy has
a validation-sidecar record showing the writer used the Simpro vault connector's
current brand/product context before publish readiness. The guard validates
connector evidence and resource IDs rather than hard-coded vault routes.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

try:
    from .guard_common import Finding, make_finding, should_fail, summarize_findings
    from .proof_sidecar import load_sidecar_content
except ImportError:  # pragma: no cover - supports direct script execution.
    from guard_common import Finding, make_finding, should_fail, summarize_findings
    from proof_sidecar import load_sidecar_content


ALIGNMENT_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?Vault Brand Language Alignment:?\s*$",
    re.IGNORECASE,
)
NEXT_HEADING_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?(?:PAA/FAQ Provenance|Metric Proof Pack|Source Map|"
    r"Customer Proof Slate|Selected Customer Proof Mining|Customer Proof Pack|"
    r"Customer Proof Selection Decision|E-E-A-T Proof Map|FAQ Proof Map|"
    r"Review Story Selection|Review Site Theme Selection|Structured data plan|"
    r"Early Artifact Plan|Concrete Answer Check|Competitive Shortlist Decision|"
    r"Named Feature/Add-On Link Check|Fred Voccola Authority Selection)\s*$",
    re.IGNORECASE,
)
BULLET_FIELD_RE = re.compile(r"^\s*[-*+]\s*(?P<key>[^:]+):\s*(?P<value>.*?)\s*$")

PRODUCT_URL_RE = re.compile(
    r"https?://(?:www\.)?simprogroup\.com/(?:features|solutions|industries)/[^\s),]*",
    re.IGNORECASE,
)
SIMPRO_PRODUCT_CONTEXT_RE = re.compile(
    r"\bSimpro\b.{0,90}\b(?:platform|software|feature|features|add-?on|add-?ons|"
    r"solution|solutions|industr(?:y|ies)|quoting|scheduling|invoicing|payments|"
    r"job costing|recurring maintenance|field service management)\b",
    re.IGNORECASE | re.DOTALL,
)
PRODUCT_TERM_CONTEXT_RE = re.compile(
    r"\b(?:Simpro field service management software|Simpro job management software|"
    r"Simpro platform|Simpro software)\b",
    re.IGNORECASE,
)
SOLUTION_CONTEXT_RE = re.compile(
    r"\b(?:solution|solutions|industr(?:y|ies)|vertical|verticals)\b",
    re.IGNORECASE,
)
CONNECTOR_EVIDENCE_RE = re.compile(
    r"\b(?:context_pack_hash|receipt_hash|resource_id|claim_id|manifest_revision|"
    r"vault_status|vault_search|vault_read|vault_expand|vault_claims|vault_validate_context)\b",
    re.IGNORECASE,
)
CONTEXT_PACK_HASH_RE = re.compile(
    r"\bcontext_pack_hash(?:(?:\s*(?:=|:)\s*)|\s+)`?(?:sha256:)?[0-9a-f]{64}`?(?=$|[\s;,])",
    re.IGNORECASE,
)
RECEIPT_HASH_RE = re.compile(
    r"\breceipt_hash(?:(?:\s*(?:=|:)\s*)|\s+)`?(?:sha256:)?[0-9a-f]{64}`?(?=$|[\s;,])",
    re.IGNORECASE,
)
RESOURCE_ID_RE = re.compile(
    r"\bresource_id(?:(?:\s*(?:=|:)\s*)|\s+)`?(res-[0-9a-f]{32})`?(?=$|[\s;,])",
    re.IGNORECASE,
)
MANIFEST_REVISION_RE = re.compile(
    r"\bmanifest_revision(?:(?:\s*(?:=|:)\s*)|\s+)`?[0-9a-f]{64}`?(?=$|[\s;,])",
    re.IGNORECASE,
)
CLAIM_ID_RE = re.compile(
    r"\bclaim_id(?:(?:\s*(?:=|:)\s*)|\s+)`?(claim-[a-z0-9][a-z0-9._-]{2,})`?(?=$|[\s;,])",
    re.IGNORECASE,
)
PLACEHOLDER_TERMS = ("example", "fake", "placeholder", "test")
NO_PROOF_DECLARATION_RE = re.compile(
    r"^(?:none|no claims?|not applicable|not_applicable|n/?a)$",
    re.IGNORECASE,
)
FEATURE_RESOURCE_EVIDENCE_RE = re.compile(
    r"\b(?:feature|add-?on).{0,80}\bresource_id\b|\bresource_id\b.{0,80}\b(?:feature|add-?on)\b",
    re.IGNORECASE,
)
VERTICAL_RESOURCE_EVIDENCE_RE = re.compile(
    r"\b(?:vertical|industry|solution).{0,80}\bresource_id\b|\bresource_id\b.{0,80}\b(?:vertical|industry|solution)\b",
    re.IGNORECASE,
)
SEMANTIC_METADATA_FIELDS = (
    "title",
    "aliases",
    "headings",
    "topics",
    "semantic_roles",
)
FEATURE_EVIDENCE_TERM_RE = re.compile(r"\b(?:feature|add-?on)\b", re.IGNORECASE)
VERTICAL_EVIDENCE_TERM_RE = re.compile(
    r"\b(?:vertical|industry|industries|solution|solutions)\b",
    re.IGNORECASE,
)
VERTICAL_SEMANTIC_TERMS = {
    "vertical",
    "verticals",
    "industry",
    "industries",
    "solution",
    "solutions",
}
VERTICAL_TARGET_STOPWORDS = {
    "software",
    "business",
    "businesses",
    "contractor",
    "contractors",
    "field",
    "service",
    "services",
    "for",
    "and",
    "the",
    "simpro",
}

NAMED_FEATURES = (
    "AI Mobile Work Notes",
    "Data Feed",
    "Delight",
    "Digital Forms",
    "Fast Cash",
    "FieldReady",
    "GPS Time Tracking",
    "JobBrief",
    "JobReady",
    "JobScribe",
    "JustAsk",
    "Maintenance Planner",
    "Multi-Company",
    "Private Cloud",
    "Simpro Payments",
    "Simtrac",
    "SMS Messaging",
    "Takeoffs",
    "Two-Way Messaging",
)

REQUIRED_FIELDS = (
    "article title",
    "product/solution language scope",
    "vault connector evidence",
    "product/feature language applied",
    "solution/industry language applied",
    "fallback context use",
    "claims requiring source verification",
    "status",
)
VALID_SCOPES = {"product/feature", "solution/industry", "mixed"}
FALLBACK_BLOCKER_TERMS = (
    "vault unavailable",
    "vault-unavailable",
    "vault blocker",
    "vault unavailable blocker",
)


def check_content(
    content: str,
    *,
    proof_content: Optional[str] = None,
    context_pack: Mapping[str, Any] | str | Path | None = None,
    context_receipt: Mapping[str, Any] | str | Path | None = None,
) -> List[Finding]:
    """Return findings for missing or incomplete vault brand-language alignment."""
    if not _is_triggered(content, proof_content or ""):
        return []

    block = _extract_alignment_block(proof_content or "")
    if block is None:
        return [
            _finding(
                "vault_brand_language_alignment_missing",
                1,
                "Simpro product, feature, add-on, solution, or industry language appears without a Vault Brand Language Alignment block.",
                (
                    "Add Vault Brand Language Alignment to the validation sidecar with connector evidence, "
                    "language applied, fallback context use, source-verification boundary, and Status: aligned."
                ),
            )
        ]

    findings: List[Finding] = []
    fields = block["fields"]
    for required_field in REQUIRED_FIELDS:
        if not fields.get(required_field):
            findings.append(
                _finding(
                    "vault_brand_language_required_field_missing",
                    block["line"],
                    f"Vault Brand Language Alignment is missing required field: {required_field}.",
                    "Add the complete Vault Brand Language Alignment block to the validation sidecar.",
                    match=required_field,
                )
            )

    connector_evidence = fields.get("vault connector evidence", "")
    if connector_evidence and not CONNECTOR_EVIDENCE_RE.search(connector_evidence):
        findings.append(
            _finding(
                "vault_brand_language_connector_evidence_invalid",
                block["line"],
                "Vault Brand Language Alignment does not cite connector-derived evidence.",
                (
                    "Document connector-derived context such as context_pack_hash, receipt_hash, "
                    "resource_id, claim_id, manifest_revision, or the vault operations used."
                ),
                match=connector_evidence,
            )
        )
    if connector_evidence:
        proof_declaration = fields.get(
            "claims requiring source verification", ""
        ).strip()
        proof_sensitive = bool(
            proof_declaration
            and not NO_PROOF_DECLARATION_RE.fullmatch(proof_declaration)
        )
        findings.extend(
            _connector_evidence_findings(
                connector_evidence,
                line=int(block["line"]),
                proof_sensitive=proof_sensitive,
            )
        )
        findings.extend(
            _bound_connector_evidence_findings(
                connector_evidence,
                context_pack=context_pack,
                context_receipt=context_receipt,
                line=int(block["line"]),
            )
        )

    scope = fields.get("product/solution language scope", "").strip().lower()
    if scope and scope not in VALID_SCOPES:
        findings.append(
            _finding(
                "vault_brand_language_invalid_scope",
                block["line"],
                "Vault Brand Language Alignment has an invalid product/solution language scope.",
                "Use product/feature, solution/industry, or mixed.",
                match=fields.get("product/solution language scope", ""),
            )
        )

    status = fields.get("status", "").strip().lower()
    if status and status != "aligned":
        findings.append(
            _finding(
                "vault_brand_language_status_not_aligned",
                block["line"],
                "Vault Brand Language Alignment status is not aligned.",
                "Set Status: aligned only after vault product language has been checked and applied.",
                match=fields.get("status", ""),
            )
        )

    fallback = fields.get("fallback context use", "").strip().lower()
    if (
        fallback
        and fallback != "none"
        and not any(term in fallback for term in FALLBACK_BLOCKER_TERMS)
    ):
        findings.append(
            _finding(
                "vault_brand_language_fallback_without_blocker",
                block["line"],
                "Repo-local fallback context was used without documenting a vault-unavailable blocker.",
                "Use the vault first, or document the vault-unavailable blocker alongside the fallback context used.",
                match=fields.get("fallback context use", ""),
            )
        )

    named_features = _named_features_in_content(content, proof_content or "")
    if named_features:
        if not FEATURE_RESOURCE_EVIDENCE_RE.search(connector_evidence):
            findings.append(
                _finding(
                    "vault_brand_language_feature_resource_missing",
                    block["line"],
                    "Named Simpro feature or add-on language appears without feature-specific connector resource evidence.",
                    "Add the feature or add-on resource_id selected through vault_search/vault_read/vault_expand.",
                )
            )
        else:
            semantic_finding = _semantic_resource_finding(
                evidence=connector_evidence,
                context_pack=context_pack,
                context_receipt=context_receipt,
                line=int(block["line"]),
                requirement="feature",
                required_phrases=named_features,
                content=content,
            )
            if semantic_finding is not None:
                findings.append(semantic_finding)

    requires_vertical = _requires_vertical_resource(content, scope)
    if requires_vertical:
        if not VERTICAL_RESOURCE_EVIDENCE_RE.search(connector_evidence):
            findings.append(
                _finding(
                    "vault_brand_language_vertical_resource_missing",
                    block["line"],
                    "Solution or industry language appears without solution or vertical connector resource evidence.",
                    "Add the solution, industry, or vertical resource_id selected through vault_search/vault_read/vault_expand.",
                )
            )
        else:
            semantic_finding = _semantic_resource_finding(
                evidence=connector_evidence,
                context_pack=context_pack,
                context_receipt=context_receipt,
                line=int(block["line"]),
                requirement="vertical",
                required_phrases=set(),
                content=content,
            )
            if semantic_finding is not None:
                findings.append(semantic_finding)

    return sorted(
        findings,
        key=lambda finding: (
            finding["severity"] != "error",
            finding["line"],
            finding["rule_id"],
        ),
    )


def check_file(
    path: str | Path,
    *,
    fail_on: str = "error",
    proof_sidecar: Optional[str] = None,
    context_pack: str | Path | None = None,
    context_receipt: str | Path | None = None,
) -> List[Finding]:
    """Check a public article file plus optional validation sidecar."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    file_path = Path(path)
    proof_content = load_sidecar_content(file_path, proof_sidecar)
    return check_content(
        file_path.read_text(encoding="utf-8"),
        proof_content=proof_content,
        context_pack=context_pack,
        context_receipt=context_receipt,
    )


def _is_triggered(content: str, proof_content: str = "") -> bool:
    public_content = _blank_fenced_code(content)
    return bool(
        PRODUCT_URL_RE.search(public_content)
        or SIMPRO_PRODUCT_CONTEXT_RE.search(public_content)
        or PRODUCT_TERM_CONTEXT_RE.search(public_content)
        or _has_named_feature(public_content, proof_content)
    )


def _named_features_in_content(content: str, proof_content: str = "") -> set[str]:
    public_content = _blank_fenced_code(content)
    matched: set[str] = set()
    for feature in (*NAMED_FEATURES, *_declared_feature_names(proof_content)):
        if re.search(
            rf"(?<!\w){re.escape(feature)}(?!\w)", public_content, re.IGNORECASE
        ):
            matched.add(feature)
    return matched


def _has_named_feature(content: str, proof_content: str = "") -> bool:
    return bool(_named_features_in_content(content, proof_content))


def _declared_feature_names(proof_content: str) -> set[str]:
    lines = proof_content.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.match(
                r"^\s*#{1,6}\s+Named Feature Status and Commercial Treatment\s*$",
                line,
                re.IGNORECASE,
            )
        ),
        None,
    )
    if start is None:
        return set()
    table_lines: list[str] = []
    for line in lines[start + 1 :]:
        if re.match(r"^\s*#{1,6}\s+", line):
            break
        if line.strip().startswith("|"):
            table_lines.append(line)
        elif table_lines and line.strip():
            break
    names: set[str] = set()
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and cells[0]:
            names.add(cells[0])
    return names


def _requires_vertical_resource(content: str, scope: str) -> bool:
    if scope in {"solution/industry", "mixed"}:
        return True
    return bool(PRODUCT_URL_RE.search(content) and SOLUTION_CONTEXT_RE.search(content))


def _connector_evidence_findings(
    evidence: str,
    *,
    line: int,
    proof_sensitive: bool,
) -> List[Finding]:
    """Validate sidecar audit metadata without replacing live Context Binding."""
    requirements = (
        (
            CONTEXT_PACK_HASH_RE,
            "vault_brand_language_context_pack_hash_invalid",
            "Vault Brand Language Alignment needs a SHA-256 context_pack_hash.",
        ),
        (
            RECEIPT_HASH_RE,
            "vault_brand_language_receipt_hash_invalid",
            "Vault Brand Language Alignment needs a SHA-256 receipt_hash.",
        ),
        (
            RESOURCE_ID_RE,
            "vault_brand_language_resource_id_invalid",
            "Vault Brand Language Alignment needs at least one connector-shaped resource_id.",
        ),
        (
            MANIFEST_REVISION_RE,
            "vault_brand_language_manifest_revision_invalid",
            "Vault Brand Language Alignment needs the connector manifest revision digest.",
        ),
    )
    findings = [
        _finding(
            rule_id,
            line,
            message,
            (
                "Record the exact connector-produced value in this audit block. "
                "This sidecar evidence does not replace live Context Binding validation."
            ),
            match=evidence,
        )
        for pattern, rule_id, message in requirements
        if not pattern.search(evidence)
    ]
    claim_ids = [match.group(1) for match in CLAIM_ID_RE.finditer(evidence)]
    has_current_claim_id = any(
        not set(re.split(r"[-._]+", claim_id.casefold())).intersection(
            PLACEHOLDER_TERMS
        )
        for claim_id in claim_ids
    )
    if proof_sensitive and not has_current_claim_id:
        findings.append(
            _finding(
                "vault_brand_language_claim_id_missing",
                line,
                "Proof-sensitive language is declared without a connector claim_id.",
                (
                    "Record the receipt-approved connector claim_id used for the declared proof. "
                    "This sidecar evidence does not replace live Context Binding validation."
                ),
                match=evidence,
            )
        )
    return findings


def _bound_connector_evidence_findings(
    evidence: str,
    *,
    context_pack: Mapping[str, Any] | str | Path | None,
    context_receipt: Mapping[str, Any] | str | Path | None,
    line: int,
) -> List[Finding]:
    """Bind the human-readable audit line to already validated context artifacts."""
    if context_pack is None and context_receipt is None:
        return []
    if context_pack is None or context_receipt is None:
        return [
            _finding(
                "vault_brand_language_context_artifacts_incomplete",
                line,
                "Vault Brand Language Alignment requires both the context pack and receipt.",
                "Provide the exact pack and receipt already validated by Context Binding.",
            )
        ]
    try:
        pack = _context_mapping(context_pack, "pack")
        receipt = _context_mapping(context_receipt, "receipt")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        return [
            _finding(
                "vault_brand_language_context_artifacts_invalid",
                line,
                f"Vault Brand Language Alignment context artifacts are invalid: {error}",
                "Regenerate and validate the context pack and receipt.",
            )
        ]

    findings: List[Finding] = []
    cited_pack_hash = _evidence_digest(evidence, "context_pack_hash")
    expected_pack_hash = str(receipt.get("pack_sha256") or "").casefold()
    if cited_pack_hash and cited_pack_hash != expected_pack_hash:
        findings.append(
            _finding(
                "vault_brand_language_context_pack_hash_unbound",
                line,
                "Vault Brand Language Alignment context_pack_hash does not match the validated receipt.",
                "Copy the receipt's exact canonical pack hash into the audit block.",
                match=cited_pack_hash,
            )
        )

    cited_receipt_hash = _evidence_digest(evidence, "receipt_hash")
    expected_receipt_hash = str(receipt.get("receipt_sha256") or "").casefold()
    if cited_receipt_hash and cited_receipt_hash != expected_receipt_hash:
        findings.append(
            _finding(
                "vault_brand_language_receipt_hash_unbound",
                line,
                "Vault Brand Language Alignment receipt_hash does not match the validated receipt.",
                "Copy the receipt's exact canonical receipt hash into the audit block.",
                match=cited_receipt_hash,
            )
        )

    cited_manifest = _evidence_digest(evidence, "manifest_revision")
    revisions = receipt.get("revisions")
    expected_manifest = (
        str(revisions.get("manifest_revision") or "").casefold()
        if isinstance(revisions, Mapping)
        else ""
    )
    if cited_manifest and cited_manifest != expected_manifest:
        findings.append(
            _finding(
                "vault_brand_language_manifest_revision_unbound",
                line,
                "Vault Brand Language Alignment manifest_revision does not match the validated receipt.",
                "Copy the validated receipt revision into the audit block.",
                match=cited_manifest,
            )
        )

    allowed_resources = _context_resource_ids(pack, receipt)
    for resource_id in {match.group(1) for match in RESOURCE_ID_RE.finditer(evidence)}:
        if resource_id not in allowed_resources:
            findings.append(
                _finding(
                    "vault_brand_language_resource_id_unbound",
                    line,
                    f"Vault Brand Language Alignment resource ID is absent from the validated context: {resource_id}",
                    "Use only resource IDs selected into the validated pack and receipt.",
                    match=resource_id,
                )
            )

    allowed_claims = {
        str(row.get("claim_id"))
        for row in receipt.get("claim_decisions", [])
        if isinstance(row, Mapping)
        and row.get("approved") is True
        and row.get("claim_id")
    }
    for claim_id in {match.group(1) for match in CLAIM_ID_RE.finditer(evidence)}:
        if claim_id not in allowed_claims:
            findings.append(
                _finding(
                    "vault_brand_language_claim_id_unbound",
                    line,
                    f"Vault Brand Language Alignment claim ID is absent from approved receipt decisions: {claim_id}",
                    "Use only claim IDs approved in the validated receipt.",
                    match=claim_id,
                )
            )
    return findings


def _context_mapping(
    value: Mapping[str, Any] | str | Path,
    label: str,
) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    parsed = json.loads(Path(value).read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise ValueError(f"Context {label} must contain a JSON object.")
    return parsed


def _evidence_digest(evidence: str, label: str) -> str:
    match = re.search(
        rf"\b{re.escape(label)}(?:(?:\s*(?:=|:)\s*)|\s+)`?(?:sha256:)?([0-9a-f]{{64}})`?(?=$|[\s;,])",
        evidence,
        re.IGNORECASE,
    )
    return match.group(1).casefold() if match else ""


def _context_resource_ids(
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> set[str]:
    resource_ids: set[str] = set()

    def add(value: Any) -> None:
        if isinstance(value, str) and value:
            resource_ids.add(value)

    sections = pack.get("sections")
    if isinstance(sections, Mapping):
        discovery = sections.get("Discovery Trace")
        if isinstance(discovery, Mapping):
            for value in discovery.get("selected_resource_ids", []):
                add(value)
        for section_name in ("Selected Resource Inventory", "Retrieved Guidance"):
            rows = sections.get(section_name, [])
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, Mapping):
                        add(row.get("resource_id"))
        evidence_rows = sections.get("Approved Claim Evidence", [])
        if isinstance(evidence_rows, list):
            for row in evidence_rows:
                if not isinstance(row, Mapping):
                    continue
                add(row.get("authority_resource_id"))
                for value in row.get("support_resource_ids", []):
                    add(value)
    resources = receipt.get("resources", [])
    if isinstance(resources, list):
        for row in resources:
            if isinstance(row, Mapping):
                add(row.get("resource_id"))
            else:
                add(row)
    return resource_ids


def _role_cited_resource_ids(evidence: str, role_pattern: re.Pattern[str]) -> set[str]:
    resource_ids: set[str] = set()
    for segment in re.split(r"[;\n]", evidence):
        if not role_pattern.search(segment):
            continue
        resource_ids.update(
            match.group(1) for match in RESOURCE_ID_RE.finditer(segment)
        )
    return resource_ids


def _selected_resource_metadata(
    pack: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, list[Mapping[str, Any]]]:
    sections = pack.get("sections")
    if not isinstance(sections, Mapping):
        return {}
    discovery = sections.get("Discovery Trace")
    if not isinstance(discovery, Mapping):
        return {}
    selected_values = discovery.get("selected_resource_ids")
    if not isinstance(selected_values, list):
        return {}
    selected = {value for value in selected_values if isinstance(value, str) and value}
    metadata: dict[str, list[Mapping[str, Any]]] = {
        resource_id: [] for resource_id in selected
    }

    def add_rows(rows: Any) -> None:
        if not isinstance(rows, list):
            return
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            resource_id = row.get("resource_id")
            if isinstance(resource_id, str) and resource_id in metadata:
                metadata[resource_id].append(row)

    add_rows(sections.get("Selected Resource Inventory"))
    add_rows(sections.get("Retrieved Guidance"))
    add_rows(receipt.get("resources"))
    return metadata


def _normalize_semantic_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _resource_semantic_values(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    values: list[str] = []
    for row in rows:
        for field in SEMANTIC_METADATA_FIELDS:
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                values.append(value)
            elif isinstance(value, list):
                values.extend(
                    item for item in value if isinstance(item, str) and item.strip()
                )
    return tuple(
        normalized
        for value in values
        if (normalized := _normalize_semantic_text(value))
    )


def _semantic_phrase_present(text: str, phrase: str) -> bool:
    normalized = _normalize_semantic_text(phrase)
    return bool(normalized and f" {normalized} " in f" {text} ")


def _vertical_targets(content: str) -> set[str]:
    targets: set[str] = set()
    for match in PRODUCT_URL_RE.finditer(_blank_fenced_code(content)):
        path_match = re.search(
            r"/(?:industries|solutions)/([^/?#\s)]+)",
            match.group(0),
            re.IGNORECASE,
        )
        if path_match:
            normalized = _normalize_semantic_text(path_match.group(1))
            if normalized:
                targets.add(normalized)
    return targets


def _vertical_target_matches(
    semantic_values: Sequence[str],
    target: str,
) -> bool:
    if any(_semantic_phrase_present(value, target) for value in semantic_values):
        return True
    target_tokens = [
        token
        for token in target.split()
        if token and token not in VERTICAL_TARGET_STOPWORDS
    ]
    if not target_tokens:
        return False
    semantic_tokens = {
        token for value in semantic_values for token in value.split()
    }
    return all(token in semantic_tokens for token in target_tokens)


def _semantic_resource_finding(
    *,
    evidence: str,
    context_pack: Mapping[str, Any] | str | Path | None,
    context_receipt: Mapping[str, Any] | str | Path | None,
    line: int,
    requirement: str,
    required_phrases: set[str],
    content: str,
) -> Finding | None:
    role_pattern = (
        FEATURE_EVIDENCE_TERM_RE
        if requirement == "feature"
        else VERTICAL_EVIDENCE_TERM_RE
    )
    cited_ids = _role_cited_resource_ids(evidence, role_pattern)
    metadata: dict[str, list[Mapping[str, Any]]] = {}
    if context_pack is not None and context_receipt is not None:
        try:
            pack = _context_mapping(context_pack, "pack")
            receipt = _context_mapping(context_receipt, "receipt")
            metadata = _selected_resource_metadata(pack, receipt)
        except (OSError, json.JSONDecodeError, ValueError):
            metadata = {}

    suitable = False
    vertical_targets = (
        _vertical_targets(content) if requirement == "vertical" else set()
    )
    for resource_id in cited_ids:
        semantic_values = _resource_semantic_values(metadata.get(resource_id, []))
        if not semantic_values:
            continue
        if requirement == "feature":
            if any(
                _semantic_phrase_present(value, phrase)
                for value in semantic_values
                for phrase in required_phrases
            ):
                suitable = True
                break
            continue
        semantic_tokens = {
            token for value in semantic_values for token in value.split()
        }
        has_vertical_signal = bool(semantic_tokens & VERTICAL_SEMANTIC_TERMS)
        target_matches = not vertical_targets or any(
            _vertical_target_matches(semantic_values, target)
            for target in vertical_targets
        )
        if has_vertical_signal and target_matches:
            suitable = True
            break

    if suitable:
        return None
    if requirement == "feature":
        return _finding(
            "vault_brand_language_feature_resource_semantics_invalid",
            line,
            "Feature or add-on evidence does not cite a selected resource with matching connector semantic metadata.",
            (
                "Select and cite a connector resource whose title, aliases, headings, topics, "
                "or semantic roles identify the named feature or add-on."
            ),
            match=", ".join(sorted(cited_ids)),
        )
    return _finding(
        "vault_brand_language_vertical_resource_semantics_invalid",
        line,
        "Solution or industry evidence does not cite a selected resource with suitable connector semantic metadata.",
        (
            "Select and cite a connector resource whose title, aliases, headings, topics, "
            "or semantic roles identify the applicable solution, industry, or vertical."
        ),
        match=", ".join(sorted(cited_ids)),
    )


def _extract_alignment_block(content: str) -> Optional[Dict[str, object]]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if not ALIGNMENT_HEADING_RE.match(line.strip()):
            continue
        fields: Dict[str, str] = {}
        for block_line in lines[index + 1 :]:
            stripped = block_line.strip()
            if stripped.startswith("```"):
                break
            if NEXT_HEADING_RE.match(stripped):
                break
            if not stripped and fields:
                break
            if not stripped:
                continue
            match = BULLET_FIELD_RE.match(block_line)
            if match:
                fields[_normalize_key(match.group("key"))] = match.group(
                    "value"
                ).strip()
                continue
            if fields and re.match(r"^\s*(?:#{1,6}\s+)?[A-Za-z].*$", stripped):
                break
        return {"line": index + 1, "fields": fields}
    return None


def _blank_fenced_code(content: str) -> str:
    lines = content.splitlines()
    blanked: List[str] = []
    in_fence = False
    for line in lines:
        if line.strip().startswith("```"):
            in_fence = not in_fence
            blanked.append("")
            continue
        blanked.append("" if in_fence else line)
    return "\n".join(blanked)


def _normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower()).strip()


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


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check vault product-language alignment."
    )
    parser.add_argument("path", help="Markdown file to check")
    parser.add_argument(
        "--fail-on",
        choices=["error", "warning", "none"],
        default="error",
        help="Finding severity that should produce a nonzero exit code.",
    )
    parser.add_argument(
        "--proof-sidecar",
        help="Optional validation sidecar containing Vault Brand Language Alignment.",
    )
    args = parser.parse_args(argv)

    findings = check_file(
        args.path, fail_on=args.fail_on, proof_sidecar=args.proof_sidecar
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
