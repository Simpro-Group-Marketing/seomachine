"""Build and validate advisory post-publish measurement receipts."""

from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlsplit

try:
    from . import blog_assembly_bom_guard
    from .blog_assembly_contract import (
        atomic_write_json,
        canonical_artifact,
        canonical_json_sha256,
        resolve_artifact,
        validate_governance_output_path,
        validate_sha256,
        verify_artifact,
    )
    from .guard_common import Finding, make_finding, should_fail
except ImportError:  # pragma: no cover - supports direct script execution.
    import blog_assembly_bom_guard
    from blog_assembly_contract import (
        atomic_write_json,
        canonical_artifact,
        canonical_json_sha256,
        resolve_artifact,
        validate_governance_output_path,
        validate_sha256,
        verify_artifact,
    )
    from guard_common import Finding, make_finding, should_fail


SCHEMA = "simpro-post-publish-measurement-receipt/v1"
VERIFICATION_SCOPE = "recorded_observation_metadata"
STATUSES = frozenset({"observed", "blocked"})
LANES = ("gsc", "ga4", "third_party_context")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")
RECEIPT_FIELDS = frozenset(
    {
        "schema", "status", "collected_at", "verification_scope", "article_binding",
        "measurement_windows", "sources", "measurement_scope", "performance_report",
        "raw_data_artifacts", "optimization_recommendation", "receipt_hash",
    }
)
METADATA_FIELDS = RECEIPT_FIELDS - {"schema", "verification_scope", "performance_report", "receipt_hash"}
RELEASE_BINDING_FIELDS = frozenset({"mode", "canonical_url", "normalized_path", "article", "final_bom"})
LIVE_BINDING_FIELDS = frozenset({"mode", "canonical_url", "normalized_path", "verified_at", "verification_method", "limitations"})
WINDOW_FIELDS = frozenset({"start_date", "end_date"})
WINDOWS_FIELDS = frozenset({"primary", "comparison", "supplemental"})
SUPPLEMENTAL_FIELDS = frozenset({"label", "start_date", "end_date"})
SOURCE_FIELDS = frozenset({"source_id", "status", "property_id", "filters", "retrieved_at", "limitations", "blockers"})
BLOCKER_FIELDS = frozenset({"code", "detail"})
SCOPE_FIELDS = frozenset({"business_objective", "conversion_definition", "conversion_not_applicable_reason", "success_measure", "owner", "review_date"})
RAW_ARTIFACT_FIELDS = frozenset({"lane", "path", "sha256"})
RAW_METADATA_FIELDS = frozenset({"lane", "path"})
RECOMMENDATION_FIELDS = frozenset({"summary", "basis_lanes"})
PROHIBITED_FIELDS = frozenset({"forecast", "prediction", "projected_impact", "causal_claim", "caused_by", "recommendation"})
PERFORMANCE_OUTCOME_PATTERN = (
    r"(?:(?:organic\s+)?traffic|clicks?|impressions?|sessions?|views?|"
    r"active\s+users?|engagement|bounce\s+rate|conversions?|revenue|"
    r"rankings?|visibility|growth|decline)"
)
IMPACT_VERB_PATTERN = (
    r"(?:increase|decrease|improve|reduce|boost|lift|grow|decline|drive|"
    r"deliver|generate|raise|lower|rank|double|produce)"
)
CHANGE_SUBJECT_PATTERN = r"(?:rewrite|update|change|optimization|article|content)"
DIRECTIONAL_MODIFIER_PATTERN = (
    r"(?:more|less|higher|lower|additional|fewer|increased|decreased|better|worse)"
)
CHANGE_RESULT_PATTERN = (
    r"(?:increase|increased|decrease|decreased|improve|improved|reduce|reduced|"
    r"boost|boosted|lift|lifted|grow|grew|decline|declined|rise|rose|fall|fell|"
    r"double|doubled)"
)
UNSUPPORTED_ASSERTION_PROSE_RE = re.compile(
    rf"(?:^|[.!?][ \t]+)(?:forecast|predict|project)\b"
    rf"[^.!?\r\n]{{0,120}}\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b(?:we|the\s+(?:model|report|analysis|receipt|data))\s+"
    rf"(?:expect(?:s|ed|ing)?|anticipat(?:e|es|ed|ing)|foresee(?:s|n|ing)?|"
    rf"forecast(?:s|ed|ing)?|predict(?:s|ed|ing)?|project(?:s|ed|ing)?)\b"
    rf"[^.!?\r\n]{{0,40}}(?:"
    rf"\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,20}}"
    rf"\b(?:to[ \t]+)?{IMPACT_VERB_PATTERN}\b)|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,80}}\b"
    rf"(?:is|are|was|were)\s+(?:expected|anticipated|forecast|forecasted|"
    rf"predicted|projected)\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,40}}"
    rf"\b(?:will|would|should|could|may|might|expected\s+to|likely\s+to)\b"
    rf"[^.!?\r\n]{{0,30}}\b{IMPACT_VERB_PATTERN}\b|"
    rf"\b(?:will|would|should|could|may|might|expected\s+to|likely\s+to)\b"
    rf"[^.!?\r\n]{{0,30}}\b{IMPACT_VERB_PATTERN}\b"
    rf"[^.!?\r\n]{{0,40}}\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b(?:caus(?:e|es|ed|ing)|contribut(?:e|es|ed|ing)\s+to|"
    rf"result(?:s|ed)?\s+in|led\s+to|driven\s+by|yield(?:s|ed|ing)|"
    rf"spark(?:s|ed|ing)|prompt(?:s|ed|ing))\b"
    rf"[^.!?\r\n]{{0,20}}(?:\b(?:the|a|an)\b[ \t]+)?"
    rf"(?:\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+)?"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:increased|decreased|improved|reduced|boosted|lifted|drove|generated|"
    rf"raised|lowered|produced)\b[ \t]+(?:the[ \t]+)?"
    rf"(?:{DIRECTIONAL_MODIFIER_PATTERN}[ \t]+)?\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:brought|created|delivered|made|pushed|gained|is[ \t]+generating|"
    rf"was[ \t]+generating)\b[ \t]+(?:the[ \t]+)?"
    rf"\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:is|was|are|were)[ \t]+responsible[ \t]+for\b[ \t]+(?:the[ \t]+)?"
    rf"(?:\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[ \t]+"
    rf"\b(?:increase|growth|decline|drop|gain|lift)\b)|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:had[ \t]+(?:a[ \t]+)?(?:positive|negative|material)?[ \t]*impact[ \t]+on|"
    rf"helped)\b[^.!?\r\n]{{0,20}}\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:is|was)[ \t]+why\b[^.!?\r\n]{{0,20}}"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,20}}\b{CHANGE_RESULT_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\bpaid[ \t]+off[ \t]+with\b[ \t]+\b{DIRECTIONAL_MODIFIER_PATTERN}\b"
    rf"[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,60}}"
    rf"\b{CHANGE_RESULT_PATTERN}\b[^.!?\r\n]{{0,40}}"
    rf"\b(?:after|following|because[ \t]+of|due[ \t]+to|thanks[ \t]+to)\b"
    rf"[^.!?\r\n]{{0,30}}\b{CHANGE_SUBJECT_PATTERN}\b|"
    rf"\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b"
    rf"[^.!?\r\n]{{0,30}}\b(?:because[ \t]+of|due[ \t]+to|driven[ \t]+by|from|"
    rf"attributable[ \t]+to|thanks[ \t]+to)\b[^.!?\r\n]{{0,30}}"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[ \t]+"
    rf"\b(?:gains?|growth|improvements?|increase|lift)\b[^.!?\r\n]{{0,20}}"
    rf"\b(?:attributable[ \t]+to|from|because[ \t]+of|due[ \t]+to)\b"
    rf"[^.!?\r\n]{{0,30}}\b{CHANGE_SUBJECT_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[ \t]+"
    rf"\b(?:explains?|accounts?[ \t]+for|is[ \t]+the[ \t]+reason|"
    rf"brought[ \t]+about|was[ \t]+behind)\b[^.!?\r\n]{{0,20}}(?:"
    rf"(?:the[ \t]+)?\b(?:increase|decrease|rise|fall|growth|decline|gain|lift|"
    rf"improvement)\b[ \t]+in[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{DIRECTIONAL_MODIFIER_PATTERN}\b[ \t]+\b{PERFORMANCE_OUTCOME_PATTERN}\b|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[ \t]+\b(?:increase|decrease|rise|fall|"
    rf"growth|decline|gain|lift|improvement|increased|decreased|rose|fell|grew|"
    rf"declined|improved)\b)|"
    rf"\b{PERFORMANCE_OUTCOME_PATTERN}\b[^.!?\r\n]{{0,30}}"
    rf"\b(?:stems?[ \t]+from|stemmed[ \t]+from|came[ \t]+from|"
    rf"as[ \t]+a[ \t]+consequence[ \t]+of)\b[^.!?\r\n]{{0,30}}"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b|"
    rf"\b{CHANGE_SUBJECT_PATTERN}\b[^.!?\r\n]{{0,20}}\bperformed[ \t]+"
    rf"(?:better|worse)\b[^.!?\r\n]{{0,20}}\b(?:because[ \t]+of|due[ \t]+to|"
    rf"after|following)\b[^.!?\r\n]{{0,20}}\b{CHANGE_SUBJECT_PATTERN}\b",
    re.IGNORECASE | re.MULTILINE,
)
OBSERVED_REPORT_H2 = (
    "scope and evidence",
    "executive findings",
    "prioritized opportunity queue",
    "page and query evidence",
    "data-quality and causality limits",
    "recommended workflow handoffs",
    "measurement plan",
)
BLOCKED_REPORT_H2 = (
    "scope and evidence",
    "data-quality and causality limits",
)
MARKDOWN_HEADING_RE = re.compile(
    r"^(#{2,6})[ \t]+(.+?)[ \t]*#*[ \t]*$",
    re.MULTILINE,
)
BLOCKED_REPORT_LABEL_RE = re.compile(
    r"^[ \t]*(?:[-*][ \t]+)?(?:opportunity(?: queue)?|diagnosis|"
    r"(?:optimization )?recommendation|verdict|recommended action|"
    r"(?:workflow )?handoff|owning command|success claim)[ \t]*:",
    re.IGNORECASE | re.MULTILINE,
)
BLOCKED_REPORT_HEADING_MARKERS = (
    "opportunit",
    "diagnos",
    "recommend",
    "verdict",
    "action",
    "handoff",
    "success claim",
)
BLOCKED_REPORT_FORBIDDEN_PROSE_RE = re.compile(
    r"\b(?:opportunit(?:y|ies)|diagnos(?:e|is|tic)|recommend(?:s|ed|ing|ation)?|"
    r"verdict|handoff|success\s+claim|rewrite|optimi[sz](?:e|es|ed|ing|ation)|"
    r"edit(?:s|ed|ing)?|revis(?:e|es|ed|ing|ion)|repurpos(?:e|es|ed|ing)|"
    r"publish(?:es|ed|ing)?)\b|"
    r"/(?:analyze-existing|research|rewrite|optimize|repurpose|publish-readiness)\b",
    re.IGNORECASE,
)
HTML_COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
FENCE_LINE_RE = re.compile(r"^[ \t]*(?P<fence>`{3,}|~{3,})")
HOST_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
METRIC_PLACEHOLDER_RE = re.compile(
    r"^(?:n/?a|not[ -]?available|unavailable|unknown|blocked|none|null|-|\[\])\.?$",
    re.IGNORECASE,
)
METRIC_ERROR_RE = re.compile(
    r"\b(?:access\s+denied|error|failed|forbidden|permission|unavailable|blocked)\b",
    re.IGNORECASE,
)
METRIC_NON_OBSERVED_QUALIFIER_RE = re.compile(
    r"\b(?:forecast(?:ed)?|predicted|projected|estimated|model(?:l)?ed|synthetic)\b",
    re.IGNORECASE,
)
BLOCKER_EVIDENCE_RE = re.compile(
    r"\b(?:access|auth(?:entication|orization)?|credentials?|permissions?|denied|"
    r"forbidden|tokens?|api|connector|property|account|endpoint|https?|status|service|"
    r"down|robots(?:\.txt)?|collection|timeout|timed\s+out|errors?|"
    r"fail(?:ed|ure)?|unavailable|missing|not\s+found|no\s+data|zero\s+rows?|"
    r"no\s+rows?|empty\s+(?:response|result)|rate\s+limit|quota|"
    r"sampl(?:e|ed|ing)|stale|incompatible|"
    r"malformed|tracking|filters?|scope|consent)\b",
    re.IGNORECASE,
)
BLOCKER_CODE_RE = re.compile(
    r"(?:access|auth|credential|permission|denied|forbidden|token|api|connector|"
    r"property|account|endpoint|http|status|service|down|robots|collection|timeout|"
    r"error|fail|unavailable|missing|not_found|no_data|no_rows|empty|rate_limit|"
    r"quota|sample|stale|incompatible|malformed|tracking|filter|scope|consent)",
    re.IGNORECASE,
)
BLOCKER_ACTION_RE = re.compile(
    r"\b(?:consider|try|recommend(?:s|ed|ing|ation)?|should|must|would[ \t]+help|"
    r"needs?(?:[ \t]+to|[ \t]+\w+ing)?|add(?:s|ed|ing)?|chang(?:e|es|ed|ing)|"
    r"creat(?:e|es|ed|ing)|delet(?:e|es|ed|ing)|edit(?:s|ed|ing)?|"
    r"insert(?:s|ed|ing)?|optimi[sz](?:e|es|ed|ing)|publish(?:es|ed|ing)?|"
    r"remov(?:e|es|ed|ing)|replac(?:e|es|ed|ing)|repurpos(?:e|es|ed|ing)|"
    r"rewrit(?:e|es|ten|ing)|revis(?:e|es|ed|ing)|rout(?:e|es|ed|ing)|"
    r"run(?:s|ning)?|send(?:s|ing)?|updat(?:e|es|ed|ing)|use(?:s|d|ing)?|"
    r"cut(?:s|ting)?|prun(?:e|es|ed|ing)|trim(?:s|med|ming)?|drop(?:s|ped|ping)?|"
    r"omit(?:s|ted|ting)?|simplif(?:y|ies|ied|ying)|reword(?:s|ed|ing)?|"
    r"renam(?:e|es|ed|ing)|retitl(?:e|es|ed|ing)|link(?:s|ed|ing)?|"
    r"unlink(?:s|ed|ing)?|mov(?:e|es|ed|ing)|merg(?:e|es|ed|ing)|"
    r"split(?:s|ting)?|expand(?:s|ed|ing)?|shorten(?:s|ed|ing)?)\b",
    re.IGNORECASE,
)
RECOMMENDATION_START_RE = re.compile(
    r"^[ \t]*(?:analy[sz]e|assess|audit|compare|consider|inspect|investigate|"
    r"measure|monitor|prioriti[sz]e|review|test|validate|verify)\b",
    re.IGNORECASE,
)
RECOMMENDATION_SENTENCE_RE = re.compile(r"^[^.!?\r\n]+[.!?]?[ \t]*$")
RECOMMENDATION_HYPOTHESIS_RE = re.compile(
    rf"^[ \t]*(?:analy[sz]e|assess|consider|investigate|review|test|validate)"
    rf"[ \t]+whether[ \t]+(?:{DIRECTIONAL_MODIFIER_PATTERN}[ \t]+)?"
    rf"{PERFORMANCE_OUTCOME_PATTERN}(?:[ \t]+(?:gains?|growth|improvements?|"
    rf"increase|lift))?[ \t]+(?:is|are|was|were)[ \t]+(?:attributable[ \t]+to|"
    rf"caused[ \t]+by|driven[ \t]+by|due[ \t]+to)[ \t]+(?:the[ \t]+)?"
    rf"{CHANGE_SUBJECT_PATTERN}[.!?]?[ \t]*$",
    re.IGNORECASE,
)
GSC_REPORT_METRICS = (
    "clicks",
    "impressions",
    "ctr",
    "average position",
    "queries",
)
GA4_REPORT_METRICS = (
    "sessions",
    "views",
    "active users",
    "engagement",
    "bounce rate",
    "average session duration",
    "key events",
)


def build_receipt(
    metadata: Mapping[str, Any],
    performance_report_path: str | Path,
    workspace_root: str | Path,
    article_path: str | Path | None = None,
    final_bom_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a hash-bound internal measurement receipt from supplied observations."""
    if not isinstance(metadata, Mapping) or set(metadata) != METADATA_FIELDS:
        raise ValueError("metadata must contain the exact post-publish receipt field set")
    if (article_path is None) != (final_bom_path is None):
        raise ValueError("both article_path and final_bom_path are required together")

    root = Path(workspace_root).resolve()
    binding = metadata.get("article_binding")
    if not isinstance(binding, Mapping):
        raise ValueError("article_binding must be an object")
    mode = binding.get("mode")
    if mode == "release_artifact":
        if set(binding) != {"mode", "canonical_url", "normalized_path"}:
            raise ValueError("release_artifact metadata binding cannot contain computed article or BOM rows")
        if article_path is None or final_bom_path is None:
            raise ValueError("release_artifact requires both article_path and final_bom_path")
        article_path = _input_artifact_path(article_path, root)
        final_bom_path = _input_artifact_path(final_bom_path, root)
        article = canonical_artifact(article_path, workspace_root=root)
        bom = canonical_artifact(final_bom_path, workspace_root=root)
        _validate_final_bom(
            final_bom_path,
            article,
            root,
            normalized_path=binding.get("normalized_path"),
        )
        binding = {**binding, "article": article, "final_bom": bom}
    elif mode == "live_url":
        if set(binding) != LIVE_BINDING_FIELDS:
            raise ValueError("live_url metadata binding must contain the exact required field set")
        if article_path is not None or final_bom_path is not None:
            raise ValueError("live_url receipts cannot use article_path or final_bom_path")
    else:
        raise ValueError("article_binding.mode must be release_artifact or live_url")

    raw_rows = metadata.get("raw_data_artifacts")
    if not isinstance(raw_rows, list):
        raise ValueError("raw_data_artifacts must be a list")
    raw_data: list[dict[str, str]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping) or set(row) != RAW_METADATA_FIELDS:
            raise ValueError(f"raw_data_artifacts[{index}] must contain only lane and path")
        snapshot = canonical_artifact(
            resolve_artifact(row.get("path"), workspace_root=root),
            workspace_root=root,
        )
        raw_data.append({"lane": row.get("lane"), **snapshot})

    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "status": metadata.get("status"),
        "collected_at": metadata.get("collected_at"),
        "verification_scope": VERIFICATION_SCOPE,
        "article_binding": copy.deepcopy(dict(binding)),
        "measurement_windows": copy.deepcopy(metadata.get("measurement_windows")),
        "sources": copy.deepcopy(metadata.get("sources")),
        "measurement_scope": copy.deepcopy(metadata.get("measurement_scope")),
        "performance_report": canonical_artifact(
            _input_artifact_path(performance_report_path, root),
            workspace_root=root,
        ),
        "raw_data_artifacts": raw_data,
        "optimization_recommendation": copy.deepcopy(metadata.get("optimization_recommendation")),
    }
    receipt["receipt_hash"] = canonical_json_sha256(receipt)
    findings = check_receipt(receipt, root)
    if findings:
        raise ValueError("invalid post-publish measurement receipt: " + "; ".join(str(finding["rule_id"]) for finding in findings))
    return receipt


def check_receipt(
    receipt: Any,
    workspace_root: str | Path,
    article_path: str | Path | None = None,
    final_bom_path: str | Path | None = None,
    performance_report_path: str | Path | None = None,
) -> list[Finding]:
    """Return deterministic error findings for an untrusted receipt without mutation."""
    findings: list[Finding] = []
    root = Path(workspace_root).resolve()
    if (article_path is None) != (final_bom_path is None):
        findings.append(_finding("measurement_receipt_path_mismatch", "article_path and final_bom_path must be supplied together"))
    if not isinstance(receipt, Mapping):
        return [_finding("measurement_receipt_schema_invalid", "receipt must be a JSON object")]
    if set(receipt) != RECEIPT_FIELDS:
        findings.append(_finding("measurement_receipt_schema_invalid", "receipt must contain the exact required top-level field set"))
    _reject_prohibited_fields(receipt, findings)
    _validate_receipt_prose(receipt, findings)
    if receipt.get("schema") != SCHEMA:
        findings.append(_finding("measurement_receipt_schema_invalid", "receipt schema is invalid"))
    if receipt.get("verification_scope") != VERIFICATION_SCOPE:
        findings.append(_finding("measurement_receipt_schema_invalid", "verification_scope must be recorded_observation_metadata"))
    collected_at = _timestamp(receipt.get("collected_at"), "collected_at", findings)
    if collected_at is not None and collected_at > datetime.now(timezone.utc):
        findings.append(
            _finding(
                "measurement_receipt_schema_invalid",
                "collected_at cannot be in the future",
            )
        )
    _validate_hash(receipt, findings)

    binding = receipt.get("article_binding")
    mode = _validate_binding(binding, root, findings, collected_at)
    primary_range = _validate_windows(
        receipt.get("measurement_windows"), findings, collected_at
    )
    lane_states = _validate_sources(
        receipt.get("sources"),
        binding,
        findings,
        collected_at,
        primary_range[1] if primary_range else None,
    )
    _validate_scope(receipt.get("measurement_scope"), findings)
    _validate_artifacts(receipt, root, article_path, final_bom_path, performance_report_path, mode, findings)
    _validate_status_and_recommendation(receipt, lane_states, findings)
    return _sorted(findings)


def _validate_final_bom(
    path: str | Path,
    article: Mapping[str, str],
    root: Path,
    *,
    normalized_path: Any = None,
) -> None:
    try:
        bom = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("final_bom must be readable JSON") from error
    if not isinstance(bom, Mapping):
        raise ValueError("final_bom must be a strict final simpro-blog-assembly-bom/v1 artifact")
    artifacts = bom.get("artifacts")
    if not isinstance(artifacts, Mapping) or artifacts.get("article") != dict(article):
        raise ValueError("final_bom.artifacts.article must exactly match the article snapshot")
    article_path = resolve_artifact(article.get("path"), workspace_root=root)
    findings = blog_assembly_bom_guard.check_archived_final_bom(
        bom,
        article_path=article_path,
        workspace_root=root,
    )
    if findings:
        rules = ", ".join(
            sorted({str(finding.get("rule_id")) for finding in findings})
        )
        raise ValueError(f"final_bom must be a strict final BOM: {rules}")
    if not isinstance(normalized_path, str):
        raise ValueError("release_artifact normalized_path must be a string")
    editorial_plan = artifacts.get("editorial_plan")
    try:
        plan_path = verify_artifact(
            editorial_plan,
            workspace_root=root,
            field="final_bom.artifacts.editorial_plan",
        )
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        slug = plan["meta"]["url_slug"]
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ValueError(
            "final_bom editorial plan must expose its sealed URL slug"
        ) from error
    path_slug = normalized_path.rstrip("/").rsplit("/", 1)[-1]
    if not isinstance(slug, str) or not slug or path_slug != slug:
        raise ValueError(
            "release_artifact normalized_path must end with the sealed editorial-plan URL slug"
        )


def _input_artifact_path(path: str | Path, root: Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _validate_hash(receipt: Mapping[str, Any], findings: list[Finding]) -> None:
    value = receipt.get("receipt_hash")
    try:
        validate_sha256(value, field="receipt_hash")
    except ValueError:
        findings.append(_finding("measurement_receipt_hash_invalid", "receipt_hash must be a lowercase SHA-256 digest"))
        return
    try:
        expected = canonical_json_sha256(
            {key: child for key, child in receipt.items() if key != "receipt_hash"}
        )
    except (TypeError, ValueError, OverflowError, RecursionError):
        findings.append(
            _finding(
                "measurement_receipt_hash_invalid",
                "receipt content must contain only canonical JSON values",
            )
        )
        return
    if value != expected:
        findings.append(_finding("measurement_receipt_hash_invalid", "receipt_hash does not match the canonical receipt content"))


def _validate_binding(
    value: Any,
    root: Path,
    findings: list[Finding],
    collected_at: datetime | None,
) -> str | None:
    if not isinstance(value, Mapping):
        findings.append(_finding("measurement_receipt_binding_invalid", "article_binding must be an object"))
        return None
    mode = value.get("mode")
    expected = RELEASE_BINDING_FIELDS if mode == "release_artifact" else LIVE_BINDING_FIELDS if mode == "live_url" else None
    if expected is None or set(value) != expected:
        findings.append(_finding("measurement_receipt_binding_invalid", "article_binding fields or mode are invalid"))
        return None
    url = value.get("canonical_url")
    path = value.get("normalized_path")
    if not _canonical_url_path(url, path):
        findings.append(_finding("measurement_receipt_binding_invalid", "canonical_url and normalized_path must be the same canonical HTTPS path"))
    if mode == "live_url":
        verified_at = _timestamp(
            value.get("verified_at"),
            "article_binding.verified_at",
            findings,
            code="measurement_receipt_binding_invalid",
        )
        if collected_at is not None and verified_at is not None and verified_at > collected_at:
            findings.append(
                _finding(
                    "measurement_receipt_binding_invalid",
                    "article_binding.verified_at cannot be later than collected_at",
                )
            )
        if value.get("verification_method") != "live_canonical_observation":
            findings.append(_finding("measurement_receipt_binding_invalid", "live_url verification_method is invalid"))
        limitations = value.get("limitations")
        if not _string_list(limitations) or not any("no local release artifact was available" in item.casefold() for item in limitations):
            findings.append(_finding("measurement_receipt_binding_invalid", "live_url limitations must state that no local release artifact was available"))
    return str(mode)


def _canonical_url_path(url: Any, normalized_path: Any) -> bool:
    if not isinstance(url, str) or not isinstance(normalized_path, str) or not _canonical_path(normalized_path):
        return False
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    try:
        port = parsed.port
    except ValueError:
        return False
    hostname = parsed.hostname
    authority = parsed.netloc
    if not isinstance(hostname, str):
        return False
    expected_authority = f"[{hostname}]" if ":" in hostname else hostname
    return bool(
        not any(character.isspace() for character in url)
        and "\\" not in url
        and "?" not in url
        and "#" not in url
        and "%" not in authority
        and parsed.scheme == "https"
        and authority == expected_authority
        and _canonical_hostname(hostname)
        and port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.query
        and not parsed.fragment
        and parsed.path
        and parsed.path == normalized_path
    )


def _canonical_hostname(hostname: str) -> bool:
    if hostname != hostname.casefold() or len(hostname) > 253:
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if hostname.replace(".", "").isdigit():
            return False
        try:
            hostname.encode("ascii")
        except UnicodeEncodeError:
            return False
        labels = hostname.split(".")
        return bool(labels and all(HOST_LABEL_RE.fullmatch(label) for label in labels))
    return str(address) == hostname


def _canonical_path(value: str) -> bool:
    if (
        not value.startswith("/")
        or "\\" in value
        or any(character.isspace() for character in value)
        or re.search(r"%(?![0-9A-Fa-f]{2})", value)
    ):
        return False
    parts = value[1:].split("/")
    for index, part in enumerate(parts):
        if not part and index != len(parts) - 1:
            return False
        decoded = part
        for _ in range(10):
            next_value = unquote(decoded)
            if next_value == decoded:
                break
            decoded = next_value
        else:
            return False
        if decoded in {".", ".."} or any(
            character in "/\\"
            or character.isspace()
            or ord(character) < 32
            for character in decoded
        ):
            return False
    return True


def _validate_windows(
    value: Any,
    findings: list[Finding],
    collected_at: datetime | None,
) -> tuple[date, date] | None:
    if not isinstance(value, Mapping) or set(value) != WINDOWS_FIELDS:
        findings.append(_finding("measurement_receipt_windows_invalid", "measurement_windows must contain primary, comparison, and supplemental"))
        return None
    primary = _date_range(value.get("primary"), "measurement_windows.primary", findings)
    comparison = _date_range(value.get("comparison"), "measurement_windows.comparison", findings)
    supplemental = value.get("supplemental")
    supplemental_ranges: list[tuple[date, date]] = []
    if not isinstance(supplemental, list):
        findings.append(_finding("measurement_receipt_windows_invalid", "measurement_windows.supplemental must be a list"))
    else:
        labels: set[str] = set()
        for index, row in enumerate(supplemental):
            if not isinstance(row, Mapping) or set(row) != SUPPLEMENTAL_FIELDS or not isinstance(row.get("label"), str) or not row["label"].strip():
                findings.append(_finding("measurement_receipt_windows_invalid", f"supplemental window {index} is invalid"))
                continue
            label = row["label"]
            if label in labels:
                findings.append(_finding("measurement_receipt_windows_invalid", "supplemental window labels must be unique"))
            labels.add(label)
            date_range = _date_range(
                {"start_date": row.get("start_date"), "end_date": row.get("end_date")},
                f"measurement_windows.supplemental[{index}]",
                findings,
            )
            if date_range:
                supplemental_ranges.append(date_range)
    if primary and comparison:
        primary_start, primary_end = primary
        comparison_start, comparison_end = comparison
        if comparison_end.toordinal() != primary_start.toordinal() - 1 or (primary_end - primary_start).days != (comparison_end - comparison_start).days:
            findings.append(_finding("measurement_receipt_windows_invalid", "comparison window must immediately precede primary and have equal inclusive length"))
    if collected_at is not None:
        collection_date = collected_at.date()
        dated_ranges = [item for item in (primary, comparison) if item]
        dated_ranges.extend(supplemental_ranges)
        if any(end > collection_date for _, end in dated_ranges):
            findings.append(
                _finding(
                    "measurement_receipt_windows_invalid",
                    "measurement windows cannot end after collected_at",
                )
            )
    return primary


def _date_range(value: Any, field: str, findings: list[Finding]) -> tuple[date, date] | None:
    if not isinstance(value, Mapping) or set(value) != WINDOW_FIELDS:
        findings.append(_finding("measurement_receipt_windows_invalid", f"{field} must contain only start_date and end_date"))
        return None
    start = _iso_date(value.get("start_date"))
    end = _iso_date(value.get("end_date"))
    if not start or not end or start > end:
        findings.append(_finding("measurement_receipt_windows_invalid", f"{field} must be a non-inverted ISO date range"))
        return None
    return start, end


def _validate_sources(
    value: Any,
    binding: Any,
    findings: list[Finding],
    collected_at: datetime | None,
    primary_end: date | None,
) -> dict[str, bool]:
    observed = {lane: False for lane in LANES}
    if not isinstance(value, Mapping) or set(value) != set(LANES):
        findings.append(_finding("measurement_receipt_sources_invalid", "sources must contain exactly gsc, ga4, and third_party_context"))
        return observed
    canonical_url = binding.get("canonical_url") if isinstance(binding, Mapping) else None
    normalized_path = binding.get("normalized_path") if isinstance(binding, Mapping) else None
    for lane in LANES:
        rows = value.get(lane)
        if not isinstance(rows, list) or (lane in {"gsc", "ga4"} and not rows):
            findings.append(_finding("measurement_receipt_sources_invalid", f"{lane} must contain required source rows"))
            continue
        identities: set[tuple[str, str]] = set()
        lane_statuses: set[str] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, Mapping) or set(row) != SOURCE_FIELDS:
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}] has invalid fields"))
                continue
            source_id = row.get("source_id")
            property_id = row.get("property_id")
            if not isinstance(source_id, str) or not source_id.strip() or not isinstance(property_id, str) or not property_id.strip():
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}] requires source_id and property_id"))
            if lane == "gsc" and source_id != "google_search_console":
                findings.append(_finding("measurement_receipt_sources_invalid", "gsc source_id must be google_search_console"))
            if lane == "ga4" and source_id != "google_analytics_4":
                findings.append(_finding("measurement_receipt_sources_invalid", "ga4 source_id must be google_analytics_4"))
            if lane == "third_party_context" and isinstance(source_id, str) and source_id in {"google_search_console", "google_analytics_4"}:
                findings.append(_finding("measurement_receipt_sources_invalid", "third_party_context cannot impersonate a first-party source"))
            if isinstance(source_id, str) and isinstance(property_id, str):
                identity = (source_id, property_id)
                if identity in identities:
                    findings.append(_finding("measurement_receipt_sources_invalid", f"{lane} has duplicate source/property identity"))
                identities.add(identity)
            filters = row.get("filters")
            required_filter = "page" if lane == "gsc" else "page_path" if lane == "ga4" else "target"
            expected_target = canonical_url if lane == "gsc" else normalized_path
            target_value = filters.get(required_filter) if isinstance(filters, Mapping) else None
            target_matches = isinstance(filters, Mapping) and (
                target_value == canonical_url or target_value == normalized_path
                if lane == "third_party_context"
                else target_value == expected_target
            )
            if not _filters_valid(filters) or not target_matches:
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}] filters do not bind to the article identity"))
            retrieved_at = _timestamp(
                row.get("retrieved_at"),
                f"{lane}[{index}].retrieved_at",
                findings,
                code="measurement_receipt_sources_invalid",
            )
            if (
                collected_at is not None
                and retrieved_at is not None
                and retrieved_at > collected_at
            ):
                findings.append(
                    _finding(
                        "measurement_receipt_sources_invalid",
                        f"{lane}[{index}].retrieved_at cannot be later than collected_at",
                    )
                )
            if (
                primary_end is not None
                and retrieved_at is not None
                and retrieved_at.date() < primary_end
            ):
                findings.append(
                    _finding(
                        "measurement_receipt_sources_invalid",
                        f"{lane}[{index}].retrieved_at cannot predate the primary window end",
                    )
                )
            if not _string_list(row.get("limitations")):
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}].limitations must be a string list"))
            blockers = row.get("blockers")
            valid_blockers = _blockers_valid(blockers)
            if not valid_blockers:
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}].blockers must be exact code/detail rows"))
            source_status = row.get("status")
            if not isinstance(source_status, str) or source_status not in STATUSES:
                findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}].status is invalid"))
            elif source_status == "observed":
                lane_statuses.add(source_status)
                observed[lane] = True
                if blockers != []:
                    findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}] observed rows require empty blockers"))
            else:
                lane_statuses.add(source_status)
                if not blockers:
                    findings.append(_finding("measurement_receipt_sources_invalid", f"{lane}[{index}] blocked rows require specific blockers"))
        if len(lane_statuses) > 1:
            findings.append(
                _finding(
                    "measurement_receipt_sources_invalid",
                    f"{lane} rows must use one homogeneous status",
                )
            )
    return observed


def _filters_valid(value: Any) -> bool:
    if not isinstance(value, Mapping) or not value:
        return False
    for key, child in value.items():
        if not isinstance(key, str) or not key.strip() or not _json_scalar_or_scalar_list(child):
            return False
    return True


def _json_scalar_or_scalar_list(value: Any) -> bool:
    return _json_scalar(value) or (isinstance(value, list) and all(_json_scalar(item) for item in value))


def _json_scalar(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, (str, int, bool)) or value is None:
        return True
    return False


def _blockers_valid(value: Any) -> bool:
    if not isinstance(value, list):
        return False
    return all(
        isinstance(row, Mapping)
        and set(row) == BLOCKER_FIELDS
        and isinstance(row.get("code"), str)
        and bool(row["code"].strip())
        and BLOCKER_CODE_RE.search(row["code"]) is not None
        and isinstance(row.get("detail"), str)
        and bool(row["detail"].strip())
        and BLOCKER_EVIDENCE_RE.search(row["detail"]) is not None
        and BLOCKER_ACTION_RE.search(row["detail"]) is None
        for row in value
    )


def _validate_scope(value: Any, findings: list[Finding]) -> None:
    if not isinstance(value, Mapping) or set(value) != SCOPE_FIELDS:
        findings.append(_finding("measurement_receipt_scope_invalid", "measurement_scope must contain the exact required field set"))
        return
    for key in ("business_objective", "success_measure", "owner"):
        if not isinstance(value.get(key), str) or not value[key].strip():
            findings.append(_finding("measurement_receipt_scope_invalid", f"measurement_scope.{key} must be non-empty"))
    if not _iso_date(value.get("review_date")):
        findings.append(_finding("measurement_receipt_scope_invalid", "measurement_scope.review_date must be an ISO date"))
    definition = value.get("conversion_definition")
    reason = value.get("conversion_not_applicable_reason")
    definition_ok = isinstance(definition, str) and definition.strip() and reason is None
    reason_ok = isinstance(reason, str) and reason.strip() and definition is None
    if not definition_ok and not reason_ok:
        findings.append(_finding("measurement_receipt_scope_invalid", "measurement_scope requires exactly one conversion definition or not-applicable reason"))


def _validate_artifacts(
    receipt: Mapping[str, Any], root: Path, article_path: str | Path | None,
    final_bom_path: str | Path | None, report_path: str | Path | None,
    mode: str | None, findings: list[Finding],
) -> None:
    report = receipt.get("performance_report")
    verified_report_path = _verify_row(
        report,
        root,
        "performance_report",
        findings,
    )
    if verified_report_path is not None:
        _validate_performance_report(
            receipt,
            verified_report_path,
            findings,
        )
    if report_path is not None:
        _compare_optional_path(report, report_path, root, "performance_report", findings)
    binding = receipt.get("article_binding")
    if mode == "release_artifact" and isinstance(binding, Mapping):
        article = binding.get("article")
        bom = binding.get("final_bom")
        _verify_row(article, root, "article_binding.article", findings)
        _verify_row(bom, root, "article_binding.final_bom", findings)
        if article_path is not None:
            _compare_optional_path(article, article_path, root, "article", findings)
            _compare_optional_path(bom, final_bom_path, root, "final_bom", findings)
        try:
            if isinstance(article, Mapping) and isinstance(bom, Mapping):
                bom_path = resolve_artifact(bom.get("path"), workspace_root=root)
                _validate_final_bom(
                    bom_path,
                    article,
                    root,
                    normalized_path=binding.get("normalized_path"),
                )
        except (OSError, UnicodeError, ValueError):
            findings.append(_finding("measurement_receipt_binding_invalid", "stored final BOM is not final or does not bind the stored article snapshot"))
    elif mode == "live_url" and (article_path is not None or final_bom_path is not None):
        findings.append(_finding("measurement_receipt_path_mismatch", "live_url receipt cannot be checked against article or BOM paths"))
    raw_rows = receipt.get("raw_data_artifacts")
    if not isinstance(raw_rows, list):
        findings.append(_finding("measurement_receipt_artifact_invalid", "raw_data_artifacts must be a list"))
        return
    paths: set[str] = set()
    for index, row in enumerate(raw_rows):
        lane = row.get("lane") if isinstance(row, Mapping) else None
        if not isinstance(row, Mapping) or set(row) != RAW_ARTIFACT_FIELDS or not isinstance(lane, str) or lane not in LANES:
            findings.append(_finding("measurement_receipt_artifact_invalid", f"raw_data_artifacts[{index}] fields or lane are invalid"))
            continue
        path = row.get("path")
        if not isinstance(path, str):
            findings.append(_finding("measurement_receipt_artifact_invalid", f"raw_data_artifacts[{index}].path must be a string"))
            continue
        if path in paths:
            findings.append(_finding("measurement_receipt_artifact_invalid", "raw_data_artifact paths must be unique"))
        paths.add(path)
        _verify_row(
            row,
            root,
            f"raw_data_artifacts[{index}]",
            findings,
            expected_fields=RAW_ARTIFACT_FIELDS,
        )


def _verify_row(
    row: Any,
    root: Path,
    field: str,
    findings: list[Finding],
    *,
    expected_fields: frozenset[str] = frozenset({"path", "sha256"}),
) -> Path | None:
    try:
        if not isinstance(row, Mapping) or set(row) != expected_fields:
            raise ValueError(f"{field} has an invalid exact field set")
        return verify_artifact(row, workspace_root=root, field=field)
    except (OSError, ValueError):
        findings.append(_finding("measurement_receipt_artifact_invalid", f"{field} path or SHA-256 does not match current bytes"))
        return None


def _validate_performance_report(
    receipt: Mapping[str, Any],
    path: Path,
    findings: list[Finding],
) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        findings.append(
            _finding(
                "measurement_receipt_report_invalid",
                "performance report must be readable UTF-8 Markdown",
            )
        )
        return
    visible_content, has_fence, has_comment = _visible_markdown_text(content)
    headings = [
        (len(marker), _normalize_report_heading(title))
        for marker, title in MARKDOWN_HEADING_RE.findall(visible_content)
    ]
    h2 = tuple(title for level, title in headings if level == 2)
    status = receipt.get("status")
    sources = receipt.get("sources")
    blocked_values = (
        _blocked_report_values(sources)
        if isinstance(sources, Mapping)
        else []
    )
    if status == "observed" and h2 != OBSERVED_REPORT_H2:
        findings.append(
            _finding(
                "measurement_receipt_report_invalid",
                "observed performance report must use the exact seven-section H2 contract",
            )
        )
    if status == "blocked":
        if h2 != BLOCKED_REPORT_H2:
            findings.append(
                _finding(
                    "measurement_receipt_report_invalid",
                    "blocked performance report must use only the two allowed H2 sections",
                )
            )
        if (
            has_fence
            or has_comment
            or not _blocked_report_is_data_only(visible_content, blocked_values)
            or BLOCKED_REPORT_LABEL_RE.search(visible_content)
            or BLOCKED_REPORT_FORBIDDEN_PROSE_RE.search(visible_content)
            or any(
                level > 2
                for level, _ in headings
            )
        ):
            findings.append(
                _finding(
                    "measurement_receipt_report_invalid",
                    "blocked performance report cannot contain opportunity, diagnosis, recommendation, verdict, action, handoff, or success fields",
                )
            )
    if UNSUPPORTED_ASSERTION_PROSE_RE.search(visible_content):
        findings.append(
            _finding(
                "measurement_receipt_report_invalid",
                "performance report cannot contain forecast or causal assertions",
            )
        )
    if not isinstance(sources, Mapping):
        return
    for lane, metrics in (
        ("gsc", GSC_REPORT_METRICS),
        ("ga4", GA4_REPORT_METRICS),
    ):
        rows = sources.get(lane)
        if not isinstance(rows, list):
            continue
        has_blocked = any(
            isinstance(row, Mapping) and row.get("status") == "blocked"
            for row in rows
        )
        has_observed = any(
            isinstance(row, Mapping) and row.get("status") == "observed"
            for row in rows
        )
        if has_blocked and _report_has_metric_observation(
            visible_content, lane, metrics
        ):
            findings.append(
                _finding(
                    "measurement_receipt_report_invalid",
                    f"performance report cannot include {lane} metrics when that lane is blocked",
                )
            )
        if has_observed:
            missing_metrics = [
                metric
                for metric in metrics
                if not _metric_value_is_observed(
                    metric,
                    _report_metric_value(visible_content, lane, metric),
                )
            ]
            if missing_metrics:
                findings.append(
                    _finding(
                        "measurement_receipt_report_invalid",
                        f"performance report is missing required observed {lane} metrics: {', '.join(missing_metrics)}",
                    )
                )
    for lane in LANES:
        rows = sources.get(lane)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping) or row.get("status") != "blocked":
                continue
            required_values = [row.get("source_id"), row.get("property_id")]
            blockers = row.get("blockers")
            if isinstance(blockers, list):
                for blocker in blockers:
                    if isinstance(blocker, Mapping):
                        required_values.extend(
                            (blocker.get("code"), blocker.get("detail"))
                        )
            limitations = row.get("limitations")
            if isinstance(limitations, list):
                required_values.extend(limitations)
            if any(
                not isinstance(value, str)
                or not value.strip()
                or value not in visible_content
                for value in required_values
            ):
                findings.append(
                    _finding(
                        "measurement_receipt_report_invalid",
                        f"performance report must reproduce every {lane} blocker identity, code, detail, and limitation",
                    )
                )


def _normalize_report_heading(value: str) -> str:
    return re.sub(r"[ \t]+", " ", value.strip().strip("#").strip()).casefold()


def _report_has_metric_label(
    content: str,
    lane: str,
    metrics: Sequence[str],
) -> bool:
    choices = "|".join(re.escape(metric) for metric in metrics)
    pattern = re.compile(
        rf"(?:^[ \t]*(?:[-*][ \t]+)?(?:{re.escape(lane)}[ \t]+)?"
        rf"(?:{choices})[ \t]*:|\|[ \t]*(?:{choices})[ \t]*\|)",
        re.IGNORECASE | re.MULTILINE,
    )
    return pattern.search(content) is not None


def _report_metric_value(
    content: str,
    lane: str,
    metric: str,
) -> str | None:
    label = rf"(?:{re.escape(lane)}[ \t]+)?{re.escape(metric)}"
    line_pattern = re.compile(
        rf"^[ \t]*(?:[-*][ \t]+)?{label}[ \t]*:[ \t]*(.*?)[ \t]*$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = line_pattern.search(content)
    if match:
        return match.group(1).strip()
    normalized_labels = {
        metric.casefold(),
        f"{lane} {metric}".casefold(),
    }
    for line in content.splitlines():
        if "|" not in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        for index, cell in enumerate(cells[:-1]):
            if cell.casefold() in normalized_labels:
                return cells[index + 1].strip()
    return None


def _metric_value_is_observed(metric: str, value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().strip("`*_ ")
    if (
        not normalized
        or METRIC_PLACEHOLDER_RE.fullmatch(normalized)
        or METRIC_ERROR_RE.search(normalized)
    ):
        return False
    if METRIC_NON_OBSERVED_QUALIFIER_RE.search(normalized):
        return False
    if metric == "queries":
        return True
    return re.match(
        r"^(?:[<>~=][ \t]*)?(?:\d{1,2}:\d{2}(?::\d{2})?|\d[\d,.]*%?)(?:[ \t]|$)",
        normalized,
    ) is not None


def _report_has_metric_observation(
    content: str,
    lane: str,
    metrics: Sequence[str],
) -> bool:
    if _report_has_metric_label(content, lane, metrics):
        return True
    choices = "|".join(re.escape(metric) for metric in metrics)
    number = r"(?:\d{1,2}:\d{2}(?::\d{2})?|\d[\d,.]*%?)"
    pattern = re.compile(
        rf"(?:\b(?:{choices})\b[^.\r\n]{{0,64}}{number}|"
        rf"{number}[^.\r\n]{{0,64}}\b(?:{choices})\b)",
        re.IGNORECASE,
    )
    return pattern.search(content) is not None


def _blocked_report_values(sources: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for rows in sources.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, Mapping) or row.get("status") != "blocked":
                continue
            for value in (row.get("source_id"), row.get("property_id")):
                if isinstance(value, str) and value:
                    values.append(value)
            for field in ("limitations", "blockers"):
                children = row.get(field)
                if not isinstance(children, list):
                    continue
                for child in children:
                    if isinstance(child, str) and child:
                        values.append(child)
                    elif isinstance(child, Mapping):
                        for key in ("code", "detail"):
                            value = child.get(key)
                            if isinstance(value, str) and value:
                                values.append(value)
    return values


def _visible_markdown_text(content: str) -> tuple[str, bool, bool]:
    without_comments, comment_count = HTML_COMMENT_RE.subn("", content)
    unmatched_comment = "<!--" in without_comments
    if unmatched_comment:
        without_comments = without_comments.split("<!--", 1)[0]
    visible_lines: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    has_fence = False
    for line in without_comments.splitlines():
        fence_match = FENCE_LINE_RE.match(line)
        if fence_match:
            token = fence_match.group("fence")
            if fence_character is None:
                fence_character = token[0]
                fence_length = len(token)
                has_fence = True
                continue
            if token[0] == fence_character and len(token) >= fence_length:
                fence_character = None
                fence_length = 0
                continue
        if fence_character is None:
            if line.startswith("\t") or line.startswith("    "):
                continue
            visible_lines.append(line)
    return (
        "\n".join(visible_lines),
        has_fence,
        comment_count > 0 or unmatched_comment,
    )


def _blocked_report_is_data_only(content: str, values: Sequence[str]) -> bool:
    known_values = {value.strip() for value in values if value.strip()}
    allowed_headers = {
        "source",
        "source id",
        "property",
        "property id",
        "blocker",
        "blocker code",
        "blocker detail",
        "detail",
        "limitation",
        "limitations",
        "status",
    }
    allowed_sentences = {
        "status: blocked.",
        "status: blocked",
        "no first-party observation was available.",
        "no first-party observation was available",
    }
    allowed_headings = {
        "# performance review",
        "## scope and evidence",
        "## data-quality and causality limits",
    }
    label_pattern = re.compile(
        r"^(source(?: id)?|property(?: id)?|blocker(?: code| detail)?|detail|"
        r"limitations?|status):[ \t]*(.*?)$",
        re.IGNORECASE,
    )
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if stripped.casefold() in allowed_headings:
                continue
            return False
        if stripped.casefold() in allowed_sentences:
            continue
        if re.fullmatch(r"[-:| ]+", stripped):
            continue
        if "|" in stripped:
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and all(
                cell in known_values or cell.casefold() in allowed_headers
                for cell in cells
                if cell
            ):
                continue
            return False
        label_match = label_pattern.fullmatch(stripped)
        if label_match:
            label = label_match.group(1).casefold()
            value = label_match.group(2).strip()
            if label == "status" and value.rstrip(".").casefold() == "blocked":
                continue
            if value in known_values:
                continue
        if stripped in known_values:
            continue
        return False
    return True


def _compare_optional_path(row: Any, path: str | Path | None, root: Path, field: str, findings: list[Finding]) -> None:
    if path is None:
        return
    try:
        if row != canonical_artifact(_input_artifact_path(path, root), workspace_root=root):
            findings.append(_finding("measurement_receipt_path_mismatch", f"{field} does not exactly match the supplied path snapshot"))
    except ValueError:
        findings.append(_finding("measurement_receipt_path_mismatch", f"supplied {field} path is unavailable or outside workspace"))


def _validate_status_and_recommendation(receipt: Mapping[str, Any], observed: Mapping[str, bool], findings: list[Finding]) -> None:
    status = receipt.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        findings.append(_finding("measurement_receipt_status_invalid", "receipt status must be observed or blocked"))
    if status == "observed" and not (observed.get("gsc") or observed.get("ga4")):
        findings.append(_finding("measurement_receipt_status_invalid", "observed receipt requires observed GSC or GA4 evidence"))
    if status == "blocked":
        if observed.get("gsc") or observed.get("ga4"):
            findings.append(_finding("measurement_receipt_status_invalid", "blocked receipt cannot contain observed first-party evidence"))
        if receipt.get("optimization_recommendation") is not None:
            findings.append(_finding("measurement_receipt_status_invalid", "blocked receipt cannot contain an optimization recommendation"))
    recommendation = receipt.get("optimization_recommendation")
    if recommendation is None:
        return
    basis_lanes = recommendation.get("basis_lanes") if isinstance(recommendation, Mapping) else None
    valid_basis_lanes = (
        isinstance(basis_lanes, list)
        and bool(basis_lanes)
        and all(isinstance(lane, str) and lane in LANES for lane in basis_lanes)
        and len(set(basis_lanes)) == len(basis_lanes)
    )
    if not isinstance(recommendation, Mapping) or set(recommendation) != RECOMMENDATION_FIELDS or not isinstance(recommendation.get("summary"), str) or not recommendation["summary"].strip() or not valid_basis_lanes:
        findings.append(_finding("measurement_receipt_recommendation_invalid", "optimization_recommendation must contain a non-empty summary and unique valid basis lanes"))
        return
    if (
        RECOMMENDATION_START_RE.search(recommendation["summary"]) is None
        or RECOMMENDATION_SENTENCE_RE.fullmatch(recommendation["summary"]) is None
        or (
            RECOMMENDATION_HYPOTHESIS_RE.search(recommendation["summary"]) is None
            and UNSUPPORTED_ASSERTION_PROSE_RE.search(recommendation["summary"])
        )
    ):
        findings.append(
            _finding(
                "measurement_receipt_recommendation_invalid",
                "optimization_recommendation.summary must be an evidence-review action without forecast or causal assertions",
            )
        )
    if status == "observed" and any(not observed.get(lane, False) for lane in basis_lanes):
        findings.append(_finding("measurement_receipt_recommendation_invalid", "optimization recommendation basis lanes must be observed"))


def _timestamp(
    value: Any,
    field: str,
    findings: list[Finding],
    code: str = "measurement_receipt_schema_invalid",
) -> datetime | None:
    if not isinstance(value, str) or not RFC3339_UTC_RE.fullmatch(value):
        findings.append(_finding(code, f"{field} must be RFC 3339 UTC ending in Z"))
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        findings.append(_finding(code, f"{field} is not a valid RFC 3339 timestamp"))
        return None


def _iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _reject_prohibited_fields(
    value: Any,
    findings: list[Finding],
    path: str = "",
) -> None:
    active_ids: set[int] = set()
    stack: list[tuple[str, Any, str]] = [("enter", value, path)]
    while stack:
        action, current, current_path = stack.pop()
        if action == "exit":
            active_ids.discard(id(current))
            continue
        if not isinstance(current, (Mapping, list)):
            continue
        current_id = id(current)
        if current_id in active_ids:
            findings.append(
                _finding(
                    "measurement_receipt_schema_invalid",
                    "receipt contains a recursive container at "
                    f"{current_path.rstrip('.') or '<root>'}",
                )
            )
            continue
        active_ids.add(current_id)
        stack.append(("exit", current, current_path))
        if isinstance(current, Mapping):
            children = list(current.items())
            for key, child in reversed(children):
                if isinstance(key, str) and _is_prohibited_field_name(
                    key, current_path
                ):
                    findings.append(
                        _finding(
                            "measurement_receipt_prohibited_field",
                            "unsupported forecast or causal field: "
                            f"{current_path}{key}",
                        )
                    )
                stack.append(
                    ("enter", child, f"{current_path}{key}.")
                )
        else:
            for index in range(len(current) - 1, -1, -1):
                stack.append(
                    ("enter", current[index], f"{current_path}{index}.")
                )


def _validate_receipt_prose(
    receipt: Mapping[str, Any], findings: list[Finding]
) -> None:
    prose: list[tuple[str, Any]] = []
    binding = receipt.get("article_binding")
    if isinstance(binding, Mapping):
        limitations = binding.get("limitations")
        if isinstance(limitations, list):
            prose.extend(
                (f"article_binding.limitations[{index}]", value)
                for index, value in enumerate(limitations)
            )
    scope = receipt.get("measurement_scope")
    if isinstance(scope, Mapping):
        prose.extend(
            (f"measurement_scope.{field}", scope.get(field))
            for field in (
                "business_objective",
                "conversion_definition",
                "conversion_not_applicable_reason",
                "success_measure",
            )
        )
    sources = receipt.get("sources")
    if isinstance(sources, Mapping):
        for lane in LANES:
            rows = sources.get(lane)
            if not isinstance(rows, list):
                continue
            for row_index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    continue
                limitations = row.get("limitations")
                if isinstance(limitations, list):
                    prose.extend(
                        (
                            f"sources.{lane}[{row_index}].limitations[{index}]",
                            value,
                        )
                        for index, value in enumerate(limitations)
                    )
                blockers = row.get("blockers")
                if isinstance(blockers, list):
                    for blocker_index, blocker in enumerate(blockers):
                        if isinstance(blocker, Mapping):
                            prose.append(
                                (
                                    f"sources.{lane}[{row_index}].blockers[{blocker_index}].detail",
                                    blocker.get("detail"),
                                )
                            )
    recommendation = receipt.get("optimization_recommendation")
    if isinstance(recommendation, Mapping):
        prose.append(
            ("optimization_recommendation.summary", recommendation.get("summary"))
        )
    for field, value in prose:
        if (
            isinstance(value, str)
            and not (
                field == "optimization_recommendation.summary"
                and RECOMMENDATION_HYPOTHESIS_RE.search(value)
            )
            and UNSUPPORTED_ASSERTION_PROSE_RE.search(value)
        ):
            findings.append(
                _finding(
                    "measurement_receipt_prohibited_assertion",
                    f"{field} cannot contain a forecast or causal assertion",
                )
            )


def _is_prohibited_field_name(key: str, path: str) -> bool:
    if path == "" and key == "optimization_recommendation":
        return False
    normalized = re.sub(r"[^a-z0-9]+", "", key.casefold())
    return any(
        marker in normalized
        for marker in (
            "forecast",
            "predict",
            "projection",
            "causal",
            "causedby",
            "recommendation",
        )
    ) or normalized.startswith(
        (
            "projected",
            "expected",
            "anticipated",
            "estimated",
        )
    ) or key.casefold() in PROHIBITED_FIELDS


def _finding(rule_id: str, message: str) -> Finding:
    return make_finding(rule_id, "error", 1, message=message, suggestion="Regenerate the advisory measurement receipt from current observation metadata.")


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    unique = {(str(item["rule_id"]), str(item.get("message", ""))): item for item in findings}
    return [unique[key] for key in sorted(unique)]


def _read_json(path: str | Path, label: str) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_nonstandard_json_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError(f"{label} must be readable JSON") from error


def _reject_nonstandard_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is prohibited: {value}")


def _validate_strict_json_output(value: Any) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("receipt cannot be written as strict JSON") from error


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create and verify advisory post-publish measurement receipts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build")
    build.add_argument("--metadata", required=True)
    build.add_argument("--performance-report", required=True)
    build.add_argument("--article")
    build.add_argument("--final-bom")
    build.add_argument("--output", required=True)
    build.add_argument("--workspace-root", default=".")
    check = subparsers.add_parser("check")
    check.add_argument("receipt")
    check.add_argument("--article")
    check.add_argument("--final-bom")
    check.add_argument("--performance-report")
    check.add_argument("--workspace-root", default=".")
    check.add_argument("--fail-on", choices=("error", "warning", "none"), default="error")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            metadata = _read_json(args.metadata, "metadata")
            inputs: dict[str, str | Path] = {
                "metadata": args.metadata,
                "performance_report": args.performance_report,
            }
            if args.article:
                inputs["article"] = args.article
            if args.final_bom:
                inputs["final_bom"] = args.final_bom
            raw_rows = metadata.get("raw_data_artifacts") if isinstance(metadata, Mapping) else None
            if isinstance(raw_rows, list):
                root = Path(args.workspace_root).resolve()
                for index, row in enumerate(raw_rows):
                    if isinstance(row, Mapping) and isinstance(row.get("path"), str):
                        inputs[f"raw_data_artifact_{index}"] = root / row["path"]
            validate_governance_output_path(args.output, inputs=inputs)
            receipt = build_receipt(metadata, args.performance_report, args.workspace_root, args.article, args.final_bom)
            _validate_strict_json_output(receipt)
            atomic_write_json(args.output, receipt)
            return 0
        receipt = _read_json(args.receipt, "receipt")
        findings = check_receipt(receipt, args.workspace_root, args.article, args.final_bom, args.performance_report)
        print(json.dumps(findings, ensure_ascii=True, indent=2, sort_keys=True, allow_nan=False))
        return 1 if should_fail(findings, args.fail_on) else 0
    except ValueError as error:
        parser.error(str(error))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
