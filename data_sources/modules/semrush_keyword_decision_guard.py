"""Validate Semrush keyword-decision artifacts for blog workflows."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import Any

try:
    from .blog_assembly_contract import canonical_json_sha256
    from .execution_attestation import attest_mapping, verify_mapping_attestation
    from .frontmatter import FrontmatterError, split_frontmatter
except ImportError:  # pragma: no cover - supports direct script execution.
    from blog_assembly_contract import canonical_json_sha256
    from execution_attestation import attest_mapping, verify_mapping_attestation
    from frontmatter import FrontmatterError, split_frontmatter


Finding = dict[str, Any]

SCHEMA = "simpro-semrush-keyword-decision/v1"
ATTESTATION_PURPOSE = SCHEMA
SOURCE_BOUNDARY = (
    "Semrush is third-party opportunity/SERP context; "
    "GSC remains first-party performance truth."
)
REQUIRED_REPORTS = frozenset(
    {
        "_keyword_research",
        "_get_report_schema",
        "phrase_these",
        "phrase_related",
        "phrase_questions",
        "phrase_organic",
        "phrase_this",
    }
)
REPORTS_WITH_DATABASE = frozenset(
    {
        "phrase_these",
        "phrase_related",
        "phrase_questions",
        "phrase_organic",
        "phrase_this",
    }
)
FIELDS = frozenset(
    {
        "schema",
        "brand",
        "market",
        "database",
        "collection_date",
        "source_boundary",
        "seed_terms",
        "connector_reports",
        "candidate_metrics",
        "serp_finalists",
        "question_candidates",
        "related_candidates",
        "selected_primary_keyword",
        "selected_secondary_keywords",
        "rejected_keywords",
        "selection_rationale",
        "evidence_hash",
        "execution_attestation",
    }
)
SERP_RESULT_FIELDS = frozenset(
    {
        "position",
        "position_type",
        "domain",
        "url",
        "triggered_serp_features",
    }
)
SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")


def build_keyword_decision(
    *,
    brand: str,
    market: str,
    database: str,
    collection_date: str,
    source_boundary: str,
    seed_terms: Sequence[str],
    connector_reports: Sequence[Mapping[str, Any]],
    candidate_metrics: Sequence[Mapping[str, Any]],
    serp_finalists: Sequence[Mapping[str, Any]],
    question_candidates: Sequence[Mapping[str, Any]],
    related_candidates: Sequence[Mapping[str, Any]],
    selected_primary_keyword: str,
    selected_secondary_keywords: Sequence[str],
    rejected_keywords: Sequence[Mapping[str, Any]],
    selection_rationale: str,
    workspace_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build one canonical, locally attested Semrush keyword decision artifact."""
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "brand": brand,
        "market": market,
        "database": database,
        "collection_date": collection_date,
        "source_boundary": source_boundary,
        "seed_terms": list(seed_terms),
        "connector_reports": [dict(row) for row in connector_reports],
        "candidate_metrics": [dict(row) for row in candidate_metrics],
        "serp_finalists": [dict(row) for row in serp_finalists],
        "question_candidates": [dict(row) for row in question_candidates],
        "related_candidates": [dict(row) for row in related_candidates],
        "selected_primary_keyword": selected_primary_keyword,
        "selected_secondary_keywords": list(selected_secondary_keywords),
        "rejected_keywords": [dict(row) for row in rejected_keywords],
        "selection_rationale": selection_rationale,
    }
    payload["evidence_hash"] = canonical_json_sha256(payload)
    return attest_mapping(
        payload,
        purpose=ATTESTATION_PURPOSE,
        workspace_root=workspace_root,
    )


def default_databases_for_brand_market(brand: str, market: str) -> tuple[str, ...]:
    """Return the default Semrush database sequence for supported brands."""
    normalized_brand = _normalize_token(brand)
    normalized_market = _normalize_token(market)
    if normalized_brand == "simpro" and normalized_market in {"us", "usa", "unitedstates"}:
        return ("us",)
    if normalized_brand == "clockshark" and normalized_market in {"us", "usa", "unitedstates"}:
        return ("us",)
    if normalized_brand == "bigchange" and normalized_market in {"uk", "gb", "unitedkingdom"}:
        return ("uk",)
    if normalized_brand == "aroflo":
        if normalized_market == "anz":
            return ("au", "nz")
        if normalized_market in {"au", "aus", "australia"}:
            return ("au",)
        if normalized_market in {"nz", "newzealand"}:
            return ("nz",)
    return ()


def check_file(
    path: str | Path,
    *,
    article_path: str | Path | None = None,
    editorial_plan_path: str | Path | None = None,
    assembly_date: str | None = None,
    fail_on: str = "error",
) -> list[Finding]:
    """Return blocking findings for one Semrush keyword-decision artifact."""
    if fail_on not in {"error", "warning", "none"}:
        raise ValueError("fail_on must be one of: error, warning, none")
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [_finding(
            "semrush_keyword_decision_missing",
            f"Semrush keyword decision artifact is unavailable: {source}",
            "/",
            "Run the Semrush connector workflow and bind the generated keyword decision artifact.",
        )]
    except (OSError, UnicodeError) as error:
        return [_finding(
            "semrush_keyword_decision_unreadable",
            f"Semrush keyword decision artifact cannot be read: {error}",
            "/",
            "Regenerate the keyword decision artifact as UTF-8 JSON.",
        )]
    except json.JSONDecodeError as error:
        return [_finding(
            "semrush_keyword_decision_json_invalid",
            f"Semrush keyword decision artifact contains invalid JSON: {error.msg}.",
            "/",
            "Regenerate the keyword decision artifact as valid JSON.",
        )]
    if not isinstance(payload, Mapping):
        return [_finding(
            "semrush_keyword_decision_root_invalid",
            "Semrush keyword decision artifact must be a JSON object.",
            "/",
            "Regenerate the artifact with build_keyword_decision().",
        )]
    findings = check_decision(
        payload,
        article_path=article_path,
        editorial_plan_path=editorial_plan_path,
        assembly_date=assembly_date,
    )
    return _sorted(findings)


def check_decision(
    payload: Mapping[str, Any],
    *,
    article_path: str | Path | None = None,
    editorial_plan_path: str | Path | None = None,
    assembly_date: str | None = None,
) -> list[Finding]:
    findings: list[Finding] = []
    if set(payload) != FIELDS:
        missing = sorted(FIELDS - set(payload))
        unknown = sorted(set(payload) - FIELDS)
        detail = []
        if missing:
            detail.append("missing: " + ", ".join(missing))
        if unknown:
            detail.append("unknown: " + ", ".join(unknown))
        findings.append(_finding(
            "semrush_keyword_decision_shape_invalid",
            "Semrush keyword decision artifact has an invalid field set"
            + (f" ({'; '.join(detail)})" if detail else "."),
            "/",
            "Regenerate the artifact with the current keyword-decision schema.",
        ))
    if payload.get("schema") != SCHEMA:
        findings.append(_finding(
            "semrush_keyword_decision_schema_invalid",
            f"Semrush keyword decision artifact must use {SCHEMA}.",
            "/schema",
            "Regenerate the artifact with the current keyword decision workflow.",
        ))
    _require_text(payload, "brand", findings, "/brand")
    _require_text(payload, "market", findings, "/market")
    database = _require_text(payload, "database", findings, "/database")
    if database and not re.fullmatch(r"[a-z]{2,3}", database):
        findings.append(_invalid("/database", "must be a lowercase Semrush database code"))
    defaults = default_databases_for_brand_market(
        str(payload.get("brand") or ""),
        str(payload.get("market") or ""),
    )
    if defaults and database and database not in defaults:
        findings.append(_finding(
            "semrush_keyword_decision_database_mismatch",
            "Semrush database does not match the default brand and market routing.",
            "/database",
            "Use the approved default database or document a market override before creating the artifact.",
        ))
    if payload.get("source_boundary") != SOURCE_BOUNDARY:
        findings.append(_finding(
            "semrush_keyword_decision_source_boundary_invalid",
            "Semrush keyword decisions must preserve the third-party source boundary.",
            "/source_boundary",
            f"Set source_boundary to: {SOURCE_BOUNDARY}",
        ))
    findings.extend(_check_collection_date(payload.get("collection_date"), assembly_date))
    findings.extend(_check_connector_reports(payload.get("connector_reports"), database))
    findings.extend(_check_string_list(payload.get("seed_terms"), "/seed_terms", required=True))
    candidate_keywords = _check_candidate_metrics(payload.get("candidate_metrics"), findings)
    primary = _require_text(
        payload,
        "selected_primary_keyword",
        findings,
        "/selected_primary_keyword",
        rule_id="semrush_keyword_decision_primary_missing",
    )
    if primary and _norm(primary) not in candidate_keywords:
        findings.append(_finding(
            "semrush_keyword_decision_primary_unmeasured",
            "Selected primary keyword must appear in candidate_metrics.",
            "/selected_primary_keyword",
            "Use a measured Semrush candidate as the selected primary keyword.",
        ))
    secondaries = _check_string_list(
        payload.get("selected_secondary_keywords"),
        "/selected_secondary_keywords",
    )
    findings.extend(secondaries)
    if isinstance(payload.get("selected_secondary_keywords"), list):
        for index, keyword in enumerate(payload["selected_secondary_keywords"]):
            if isinstance(keyword, str) and _norm(keyword) not in candidate_keywords:
                findings.append(_finding(
                    "semrush_keyword_decision_secondary_unmeasured",
                    "Selected secondary keywords must appear in candidate_metrics.",
                    f"/selected_secondary_keywords/{index}",
                    "Keep secondary keywords to measured Semrush candidates.",
                ))
    findings.extend(_check_serp_finalists(payload.get("serp_finalists"), primary, database))
    findings.extend(_check_keyword_rows(payload.get("question_candidates"), "/question_candidates", required=False))
    findings.extend(_check_keyword_rows(payload.get("related_candidates"), "/related_candidates", required=False))
    findings.extend(_check_rejected_keywords(payload.get("rejected_keywords")))
    _require_text(payload, "selection_rationale", findings, "/selection_rationale")
    findings.extend(_check_hash_and_attestation(payload))
    if editorial_plan_path is not None:
        findings.extend(_check_editorial_plan_binding(payload, editorial_plan_path))
    if article_path is not None:
        findings.extend(_check_article_binding(payload, article_path))
    return _sorted(findings)


def _check_collection_date(value: Any, assembly_date: str | None) -> list[Finding]:
    parsed = _parse_date(value)
    if parsed is None:
        return [_invalid("/collection_date", "must be a canonical ISO date")]
    if assembly_date is None:
        return []
    expected = _parse_date(assembly_date)
    if expected is None:
        return [_invalid("/assembly_date", "requires a canonical ISO assembly date")]
    if parsed != expected:
        return [_finding(
            "semrush_keyword_decision_stale",
            "Semrush keyword decision must be collected on the workflow assembly date.",
            "/collection_date",
            "Rerun the Semrush connector reports for this assembly run.",
        )]
    return []


def _check_connector_reports(value: Any, database: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, list) or not value:
        return [_invalid("/connector_reports", "must be a non-empty report execution log")]
    reports: set[str] = set()
    for index, row in enumerate(value):
        location = f"/connector_reports/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid(location, "must be an object"))
            continue
        report = row.get("report")
        parameters = row.get("parameters")
        if not isinstance(report, str) or not report.strip():
            findings.append(_invalid(f"{location}/report", "must identify the Semrush report"))
            continue
        reports.add(report.strip())
        if not isinstance(parameters, Mapping):
            findings.append(_invalid(f"{location}/parameters", "must contain the exact connector params"))
        if row.get("status") != "completed":
            findings.append(_invalid(f"{location}/status", "must be completed"))
        if report in REPORTS_WITH_DATABASE and isinstance(parameters, Mapping):
            if parameters.get("database") != database:
                findings.append(_finding(
                    "semrush_keyword_decision_report_database_mismatch",
                    f"Report {report} must use the artifact database.",
                    f"{location}/parameters/database",
                    "Rerun the connector report with the selected Semrush database.",
                ))
    missing_reports = sorted(REQUIRED_REPORTS - reports)
    if missing_reports:
        findings.append(_finding(
            "semrush_keyword_decision_reports_missing",
            "Semrush connector execution log is missing required reports: "
            + ", ".join(missing_reports),
            "/connector_reports",
            "Run discovery, schema lookup, batch metrics, related, questions, organic SERP, and final exact-primary reports.",
        ))
    return findings


def _check_candidate_metrics(value: Any, findings: list[Finding]) -> set[str]:
    if not isinstance(value, list) or not value:
        findings.append(_invalid("/candidate_metrics", "must contain Semrush keyword metrics"))
        return set()
    keywords: set[str] = set()
    for index, row in enumerate(value):
        location = f"/candidate_metrics/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid(location, "must be an object"))
            continue
        keyword = row.get("keyword")
        if not isinstance(keyword, str) or not keyword.strip():
            findings.append(_invalid(f"{location}/keyword", "must be a non-empty string"))
            continue
        normalized = _norm(keyword)
        if normalized in keywords:
            findings.append(_finding(
                "semrush_keyword_decision_candidate_duplicate",
                f"Candidate keyword is duplicated: {keyword}.",
                f"{location}/keyword",
                "Keep one normalized metric row per candidate keyword.",
            ))
        keywords.add(normalized)
        if not any(key in row for key in ("volume", "keyword_difficulty", "cpc", "competitive_density", "results")):
            findings.append(_invalid(location, "must include at least one Semrush metric field"))
    return keywords


def _check_serp_finalists(value: Any, primary: str, database: str) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(value, list) or not value:
        return [_invalid("/serp_finalists", "must contain SERP rows for finalist keywords")]
    primary_seen = False
    for index, row in enumerate(value):
        location = f"/serp_finalists/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid(location, "must be an object"))
            continue
        keyword = row.get("keyword")
        if isinstance(keyword, str) and primary and _norm(keyword) == _norm(primary):
            primary_seen = True
        else:
            _require_mapping_text(row, "keyword", findings, f"{location}/keyword")
        if row.get("database") != database:
            findings.append(_finding(
                "semrush_keyword_decision_serp_database_mismatch",
                "SERP finalist database must match the artifact database.",
                f"{location}/database",
                "Rerun phrase_organic with the artifact database.",
            ))
        results = row.get("results")
        if not isinstance(results, list) or not results:
            findings.append(_invalid(f"{location}/results", "must contain organic result rows"))
            continue
        for result_index, result in enumerate(results):
            result_location = f"{location}/results/{result_index}"
            if not isinstance(result, Mapping) or set(result) != SERP_RESULT_FIELDS:
                findings.append(_invalid(result_location, "must use the exact SERP result shape"))
                continue
            if not isinstance(result.get("position"), int) or isinstance(result.get("position"), bool) or result.get("position") <= 0:
                findings.append(_invalid(f"{result_location}/position", "must be a positive integer"))
            for text_field in ("position_type", "domain", "url"):
                _require_mapping_text(result, text_field, findings, f"{result_location}/{text_field}")
            features = result.get("triggered_serp_features")
            if not isinstance(features, list) or any(not isinstance(item, str) for item in features):
                findings.append(_invalid(f"{result_location}/triggered_serp_features", "must be a list of strings"))
    if primary and not primary_seen:
        findings.append(_finding(
            "semrush_keyword_decision_primary_serp_missing",
            "Selected primary keyword must have a phrase_organic SERP finalist row.",
            "/serp_finalists",
            "Run phrase_organic for the selected primary keyword.",
        ))
    return findings


def _check_keyword_rows(value: Any, location: str, *, required: bool) -> list[Finding]:
    if not isinstance(value, list) or (required and not value):
        return [_invalid(location, "must be a list of keyword rows")]
    findings: list[Finding] = []
    for index, row in enumerate(value):
        row_location = f"{location}/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid(row_location, "must be an object"))
            continue
        _require_mapping_text(row, "keyword", findings, f"{row_location}/keyword")
    return findings


def _check_rejected_keywords(value: Any) -> list[Finding]:
    if not isinstance(value, list) or not value:
        return [_invalid("/rejected_keywords", "must document rejected keyword candidates")]
    findings: list[Finding] = []
    for index, row in enumerate(value):
        location = f"/rejected_keywords/{index}"
        if not isinstance(row, Mapping):
            findings.append(_invalid(location, "must be an object"))
            continue
        _require_mapping_text(row, "keyword", findings, f"{location}/keyword")
        _require_mapping_text(row, "reason", findings, f"{location}/reason")
    return findings


def _check_hash_and_attestation(payload: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    stored = payload.get("evidence_hash")
    unsigned = dict(payload)
    unsigned.pop("evidence_hash", None)
    unsigned.pop("execution_attestation", None)
    if (
        not isinstance(stored, str)
        or SHA256_RE.fullmatch(stored) is None
        or stored != canonical_json_sha256(unsigned)
    ):
        findings.append(_finding(
            "semrush_keyword_decision_hash_invalid",
            "Semrush keyword decision canonical hash does not match its evidence.",
            "/evidence_hash",
            "Regenerate the immutable keyword decision artifact.",
        ))
    if not verify_mapping_attestation(payload, purpose=ATTESTATION_PURPOSE):
        findings.append(_finding(
            "semrush_keyword_decision_execution_attestation_invalid",
            "Semrush keyword decision lacks a valid local execution attestation.",
            "/execution_attestation",
            "Regenerate the artifact through build_keyword_decision().",
        ))
    return findings


def _check_editorial_plan_binding(
    payload: Mapping[str, Any],
    editorial_plan_path: str | Path,
) -> list[Finding]:
    try:
        plan = json.loads(Path(editorial_plan_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return [_finding(
            "semrush_keyword_decision_plan_unreadable",
            f"Bound editorial plan cannot be read: {error}",
            "/",
            "Regenerate the BOM with a readable editorial plan.",
        )]
    if not isinstance(plan, Mapping):
        return [_finding(
            "semrush_keyword_decision_plan_invalid",
            "Bound editorial plan must be a JSON object.",
            "/",
            "Regenerate the editorial plan.",
        )]
    findings: list[Finding] = []
    meta = plan.get("meta")
    keyword_decision = plan.get("keyword_decision")
    primary = str(payload.get("selected_primary_keyword") or "")
    secondary = list(payload.get("selected_secondary_keywords") or [])
    if isinstance(meta, Mapping):
        if _norm(str(meta.get("primary_keyword") or "")) != _norm(primary):
            findings.append(_finding(
                "semrush_keyword_decision_plan_primary_mismatch",
                "Editorial-plan primary keyword must match the Semrush-selected primary keyword.",
                "/selected_primary_keyword",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
        if _normalized_list(meta.get("secondary_keywords")) != _normalized_list(secondary):
            findings.append(_finding(
                "semrush_keyword_decision_plan_secondary_mismatch",
                "Editorial-plan secondary keywords must match the Semrush-selected secondary keywords.",
                "/selected_secondary_keywords",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
    if isinstance(keyword_decision, Mapping):
        if keyword_decision.get("artifact_schema") != SCHEMA:
            findings.append(_finding(
                "semrush_keyword_decision_plan_schema_mismatch",
                "Editorial-plan keyword_decision must reference the current Semrush schema.",
                "/keyword_decision/artifact_schema",
                "Update the editorial-plan keyword_decision reference.",
            ))
        if _norm(str(keyword_decision.get("selected_primary_keyword") or "")) != _norm(primary):
            findings.append(_finding(
                "semrush_keyword_decision_plan_primary_mismatch",
                "Editorial-plan keyword_decision reference must match the Semrush artifact.",
                "/keyword_decision/selected_primary_keyword",
                "Regenerate the editorial plan from the current Semrush keyword decision.",
            ))
    else:
        findings.append(_finding(
            "semrush_keyword_decision_plan_reference_missing",
            "Editorial plan must include a keyword_decision reference.",
            "/keyword_decision",
            "Add the Semrush-backed keyword_decision object to the editorial plan.",
        ))
    return findings


def _check_article_binding(payload: Mapping[str, Any], article_path: str | Path) -> list[Finding]:
    try:
        raw = Path(article_path).read_text(encoding="utf-8")
        frontmatter, _, _ = split_frontmatter(raw)
    except (OSError, UnicodeError, FrontmatterError) as error:
        return [_finding(
            "semrush_keyword_decision_article_unreadable",
            f"Bound article cannot be read for keyword binding: {error}",
            "/",
            "Repair the article frontmatter before readiness.",
        )]
    primary = frontmatter.get("primary_keyword") or frontmatter.get("target_keyword")
    if isinstance(primary, str) and primary.strip():
        selected = str(payload.get("selected_primary_keyword") or "")
        if _norm(primary) != _norm(selected):
            return [_finding(
                "semrush_keyword_decision_article_primary_mismatch",
                "Article primary keyword metadata must match the Semrush-selected primary keyword.",
                "/primary_keyword",
                "Update article frontmatter or regenerate the Semrush keyword decision.",
            )]
    return []


def _require_text(
    value: Mapping[str, Any],
    key: str,
    findings: list[Finding],
    location: str,
    *,
    rule_id: str = "semrush_keyword_decision_field_invalid",
) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        findings.append(_finding(
            rule_id,
            f"Semrush keyword decision field {location} must be a non-empty string.",
            location,
            "Regenerate the artifact with complete keyword-decision metadata.",
        ))
        return ""
    return candidate.strip()


def _require_mapping_text(
    value: Mapping[str, Any],
    key: str,
    findings: list[Finding],
    location: str,
) -> str:
    candidate = value.get(key)
    if not isinstance(candidate, str) or not candidate.strip():
        findings.append(_invalid(location, "must be a non-empty string"))
        return ""
    return candidate.strip()


def _check_string_list(value: Any, location: str, *, required: bool = False) -> list[Finding]:
    if not isinstance(value, list) or (required and not value) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        qualifier = "non-empty " if required else ""
        return [_invalid(location, f"must be a {qualifier}list of non-empty strings")]
    return []


def _invalid(location: str, requirement: str) -> Finding:
    return _finding(
        "semrush_keyword_decision_field_invalid",
        f"Semrush keyword decision field {location} {requirement}.",
        location,
        "Regenerate the artifact with complete Semrush connector evidence.",
    )


def _finding(rule_id: str, message: str, location: str, suggestion: str) -> Finding:
    return {
        "severity": "error",
        "rule_id": rule_id,
        "message": message,
        "suggestion": suggestion,
        "location": location,
    }


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _normalized_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_norm(item) for item in value if isinstance(item, str)]


def _sorted(findings: Sequence[Finding]) -> list[Finding]:
    unique: dict[tuple[str, str, str], Finding] = {}
    for finding in findings:
        key = (
            str(finding.get("rule_id") or ""),
            str(finding.get("location") or ""),
            str(finding.get("message") or ""),
        )
        unique[key] = dict(finding)
    return sorted(
        unique.values(),
        key=lambda finding: (
            str(finding.get("location") or ""),
            str(finding.get("rule_id") or ""),
            str(finding.get("message") or ""),
        ),
    )
