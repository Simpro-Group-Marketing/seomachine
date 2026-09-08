"""Verified commercial pillar destination index.

The index binds a commercial destination to a live-page title, a market-
specific Semrush keyword record, repo evidence rows, and vault routing. It
approves SEO destination eligibility only. It never approves product claims,
feature availability, customer proof, or public brand language.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence
from urllib.parse import urlparse

try:
    from .guard_common import Finding, make_finding, summarize_findings
except ImportError:  # pragma: no cover - direct script execution.
    from guard_common import Finding, make_finding, summarize_findings


SCHEMA_VERSION = "commercial-pillar-index/v1"
ALLOWED_PILLAR_TYPES = {"solution", "industry", "feature", "industries_hub"}
ALLOWED_MARKETS = {"US", "UK", "AU", "NZ", "CA", "IE"}
SEMRUSH_DATABASE_BY_MARKET = {
    "US": "us",
    "UK": "uk",
    "AU": "au",
    "NZ": "nz",
    "CA": "ca",
    "IE": "ie",
}
ALLOWED_STATUSES = {"verified", "stale", "blocked", "retired"}
ALLOWED_SEMRUSH_STATUSES = {"exact", "zero", "unavailable"}
EXPECTED_HOST_BY_BRAND = {"simpro": "www.simprogroup.com"}
EXPECTED_PATH_PREFIX = {
    "solution": "/solutions/",
    "industry": "/industries/",
    "feature": "/features/",
    "industries_hub": "/industries",
}
LIST_FIELDS = {"evidence_path", "evidence_locator", "evidence_sha256", "vault_routes"}
INTAKE_FIELDS = (
    "destination_id",
    "brand",
    "market",
    "pillar_type",
    "canonical_url",
    "page_title",
    "title_checked",
    "title_valid_through",
    "main_keyword",
    "semrush_database",
    "semrush_report",
    "semrush_checked",
    "semrush_valid_through",
    "semrush_result_status",
    "volume",
    "keyword_difficulty",
    "evidence_path",
    "evidence_locator",
    "evidence_sha256",
    "vault_routes",
    "status",
)
PLACEHOLDER_RE = re.compile(r"\b(?:tbd|todo|unknown|placeholder|fill[ -]?in)\b", re.IGNORECASE)
LOCATOR_RE = re.compile(
    r"^(?:line:(?P<line>[1-9][0-9]*)|lines:(?P<start>[1-9][0-9]*)-(?P<end>[1-9][0-9]*))$"
)


class CommercialPillarIndexError(ValueError):
    """Raised when a destination cannot be safely loaded or resolved."""


@dataclass(frozen=True)
class CommercialPillarRecord:
    destination_id: str
    brand: str
    market: str
    pillar_type: str
    canonical_url: str
    page_title: str
    title_checked: str
    title_valid_through: str
    main_keyword: str
    semrush_database: str
    semrush_report: str
    semrush_checked: str
    semrush_valid_through: str
    semrush_result_status: str
    volume: int
    keyword_difficulty: int
    evidence_path: tuple[str, ...]
    evidence_locator: tuple[str, ...]
    evidence_sha256: tuple[str, ...]
    vault_routes: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class CommercialPillarIndex:
    schema_version: str
    updated_at: str
    records: tuple[CommercialPillarRecord, ...]
    source_path: Optional[Path] = None


def load_index(path: str | Path) -> CommercialPillarIndex:
    """Load a commercial pillar index without silently dropping bad fields."""
    source_path = Path(path).resolve()
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CommercialPillarIndexError(f"Unable to load commercial pillar index: {exc}") from exc
    if not isinstance(payload, dict):
        raise CommercialPillarIndexError("Commercial pillar index root must be a JSON object.")
    raw_records = payload.get("records", [])
    if not isinstance(raw_records, list):
        raise CommercialPillarIndexError("Commercial pillar index records must be a JSON array.")
    records: list[CommercialPillarRecord] = []
    for offset, raw_record in enumerate(raw_records, start=1):
        if not isinstance(raw_record, dict):
            raise CommercialPillarIndexError(f"Record {offset} must be a JSON object.")
        records.append(_record_from_mapping(raw_record, row=offset))
    return CommercialPillarIndex(
        schema_version=str(payload.get("schema_version", "")).strip(),
        updated_at=str(payload.get("updated_at", "")).strip(),
        records=tuple(records),
        source_path=source_path,
    )


def validate_index(index: CommercialPillarIndex, *, today: date) -> list[Finding]:
    """Return deterministic, fail-closed findings for an executable index."""
    findings: list[Finding] = []
    if index.schema_version != SCHEMA_VERSION:
        findings.append(
            _finding(
                "commercial_pillar_schema_unsupported",
                1,
                f"Unsupported commercial pillar schema: {index.schema_version or '[missing]' }.",
            )
        )
        return findings

    seen_ids: dict[str, int] = {}
    seen_urls: dict[tuple[str, str, str], int] = {}
    seen_locators: dict[tuple[str, str], int] = {}
    for row, record in enumerate(index.records, start=1):
        findings.extend(_validate_record(index, record, row=row, today=today))

        destination_key = record.destination_id.casefold()
        if destination_key in seen_ids:
            findings.append(
                _finding(
                    "commercial_pillar_destination_id_duplicate",
                    row,
                    f"Duplicate destination ID also used by record {seen_ids[destination_key]}: {record.destination_id}",
                )
            )
        else:
            seen_ids[destination_key] = row

        url_key = (record.brand.casefold(), record.market.casefold(), record.canonical_url.casefold())
        if url_key in seen_urls:
            findings.append(
                _finding(
                    "commercial_pillar_canonical_url_duplicate",
                    row,
                    f"Duplicate canonical URL in the same brand and market as record {seen_urls[url_key]}.",
                )
            )
        else:
            seen_urls[url_key] = row

        for evidence_path, locator in zip(record.evidence_path, record.evidence_locator):
            locator_key = (evidence_path.casefold(), locator.casefold())
            if locator_key in seen_locators:
                findings.append(
                    _finding(
                        "commercial_pillar_evidence_locator_duplicate",
                        row,
                        f"Evidence locator is reused by record {seen_locators[locator_key]}: {evidence_path} {locator}",
                    )
                )
            else:
                seen_locators[locator_key] = row

    return sorted(findings, key=lambda finding: (int(finding["line"]), str(finding["rule_id"])))


def get_verified_destination(
    index: CommercialPillarIndex,
    *,
    destination_id: str,
    brand: str,
    market: str,
) -> CommercialPillarRecord:
    """Resolve one verified destination with exact brand and market scope."""
    matching_ids = [record for record in index.records if record.destination_id == destination_id]
    if len(matching_ids) != 1:
        raise CommercialPillarIndexError(
            f"Destination ID must resolve exactly once: {destination_id}"
        )
    record = matching_ids[0]
    if record.brand.casefold() != brand.strip().casefold() or record.market != market.strip().upper():
        raise CommercialPillarIndexError(
            f"Destination brand/market does not match article scope: {brand}/{market}."
        )
    if record.status != "verified":
        raise CommercialPillarIndexError(
            f"Destination is not verified: {destination_id} ({record.status})."
        )
    return record


def validate_intake_file(
    input_path: str | Path,
    *,
    index_path: str | Path = "context/commercial-pillar-index.json",
    today: Optional[date] = None,
) -> list[Finding]:
    """Validate intake rows under the same contract as the JSON index."""
    try:
        rows, header_findings = _read_intake(input_path)
    except (OSError, csv.Error) as exc:
        return [_finding("commercial_pillar_intake_read_failed", 1, f"Unable to read intake CSV: {exc}")]
    if header_findings:
        return header_findings
    try:
        current = load_index(index_path)
    except CommercialPillarIndexError as exc:
        return [_finding("commercial_pillar_index_load_failed", 1, str(exc))]
    incoming_records: list[tuple[int, CommercialPillarRecord]] = []
    row_findings: list[Finding] = []
    for line, row in rows:
        try:
            incoming_records.append((line, _record_from_mapping(row, row=line)))
        except CommercialPillarIndexError as exc:
            row_findings.append(_finding("commercial_pillar_intake_row_invalid", line, str(exc)))
    seen_incoming_ids: dict[str, int] = {}
    for line, record in incoming_records:
        destination_key = record.destination_id.casefold()
        if destination_key in seen_incoming_ids:
            row_findings.append(
                _finding(
                    "commercial_pillar_destination_id_duplicate",
                    line,
                    f"Duplicate destination ID also used by intake row {seen_incoming_ids[destination_key]}: {record.destination_id}",
                )
            )
        else:
            seen_incoming_ids[destination_key] = line
    if row_findings:
        return row_findings
    incoming = tuple(record for _, record in incoming_records)
    merged = _merge_records(current, incoming)
    return validate_index(merged, today=today or date.today())


def merge_intake_file(
    input_path: str | Path,
    *,
    index_path: str | Path = "context/commercial-pillar-index.json",
    out_path: str | Path = "context/commercial-pillar-index.json",
    today: Optional[date] = None,
) -> dict[str, Any]:
    """Validate and merge intake rows without writing when any blocker exists."""
    effective_today = today or date.today()
    findings = validate_intake_file(input_path, index_path=index_path, today=effective_today)
    if findings:
        return {
            "passed": False,
            "errors": len(findings),
            "warnings": 0,
            "updated": 0,
            "appended": 0,
            "findings": findings,
        }
    current = load_index(index_path)
    rows, _ = _read_intake(input_path)
    incoming = tuple(_record_from_mapping(row, row=line) for line, row in rows)
    existing_ids = {record.destination_id for record in current.records}
    merged = _merge_records(current, incoming)
    output = {
        "schema_version": SCHEMA_VERSION,
        "updated_at": effective_today.isoformat(),
        "records": [_record_to_dict(record) for record in merged.records],
    }
    Path(out_path).write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    updated = sum(1 for record in incoming if record.destination_id in existing_ids)
    return {
        "passed": True,
        "errors": 0,
        "warnings": 0,
        "updated": updated,
        "appended": len(incoming) - updated,
        "record_count": len(merged.records),
        "findings": [],
    }


def _validate_record(
    index: CommercialPillarIndex,
    record: CommercialPillarRecord,
    *,
    row: int,
    today: date,
) -> list[Finding]:
    findings: list[Finding] = []
    required_text = {
        "destination_id": record.destination_id,
        "brand": record.brand,
        "market": record.market,
        "canonical_url": record.canonical_url,
        "page_title": record.page_title,
        "main_keyword": record.main_keyword,
        "semrush_report": record.semrush_report,
    }
    for field, value in required_text.items():
        if not value or PLACEHOLDER_RE.search(value):
            rule = "commercial_pillar_page_title_missing" if field == "page_title" else "commercial_pillar_required_field_missing"
            findings.append(_finding(rule, row, f"Commercial pillar field is missing or placeholder: {field}."))

    if record.pillar_type not in ALLOWED_PILLAR_TYPES:
        findings.append(_finding("commercial_pillar_type_invalid", row, f"Unknown pillar type: {record.pillar_type}"))
    if record.market not in ALLOWED_MARKETS:
        findings.append(_finding("commercial_pillar_market_invalid", row, f"Unknown article market: {record.market}"))
    if record.status not in ALLOWED_STATUSES:
        findings.append(_finding("commercial_pillar_status_invalid", row, f"Unsupported destination status: {record.status or '[missing]'}."))
    if record.semrush_result_status not in ALLOWED_SEMRUSH_STATUSES or (
        record.status == "verified" and record.semrush_result_status != "exact"
    ):
        findings.append(_finding("commercial_pillar_semrush_status_invalid", row, "Verified destinations require an exact Semrush result."))

    findings.extend(_url_findings(record, row=row))
    findings.extend(
        _date_findings(
            record,
            row=row,
            today=today,
            enforce_freshness=record.status == "verified",
        )
    )

    expected_database = SEMRUSH_DATABASE_BY_MARKET.get(record.market)
    if expected_database and record.semrush_database != expected_database:
        findings.append(
            _finding(
                "commercial_pillar_semrush_market_mismatch",
                row,
                f"Market {record.market} requires Semrush database {expected_database}, not {record.semrush_database}.",
            )
        )

    if record.volume < 0:
        findings.append(_finding("commercial_pillar_volume_invalid", row, "Semrush volume must be zero or greater."))
    if not 0 <= record.keyword_difficulty <= 100:
        findings.append(_finding("commercial_pillar_keyword_difficulty_invalid", row, "Keyword difficulty must be between 0 and 100."))
    if record.pillar_type in {"solution", "industry", "feature"} and not record.vault_routes:
        findings.append(_finding("commercial_pillar_vault_routes_missing", row, "Solution, industry, and feature destinations require vault routes."))
    if record.page_title and record.main_keyword and not _title_keyword_fit(record.page_title, record.main_keyword):
        findings.append(_finding("commercial_pillar_title_keyword_mismatch", row, "Destination main keyword does not fit the recorded page title."))

    evidence_count = len(record.evidence_path)
    if evidence_count < 2 or len(record.evidence_locator) != evidence_count or len(record.evidence_sha256) != evidence_count:
        findings.append(
            _finding(
                "commercial_pillar_evidence_binding_invalid",
                row,
                "Evidence paths, locators, and hashes must contain matching source-row bindings for keyword and URL/title evidence.",
            )
        )
    else:
        for evidence_path, locator, expected_hash in zip(
            record.evidence_path,
            record.evidence_locator,
            record.evidence_sha256,
        ):
            findings.extend(
                _evidence_findings(
                    index,
                    evidence_path=evidence_path,
                    locator=locator,
                    expected_hash=expected_hash,
                    row=row,
                )
            )
        bound_lines = _bound_evidence_lines(index, record)
        if len(bound_lines) == evidence_count:
            if record.status == "verified" and not any(
                _line_binds_keyword_metrics(line, record) for line in bound_lines
            ):
                findings.append(
                    _finding(
                        "commercial_pillar_keyword_evidence_mismatch",
                        row,
                        "No bound evidence row contains the indexed keyword, volume, and keyword difficulty.",
                    )
                )
            if record.status == "verified" and not any(
                _line_binds_market_report(line, record) for line in bound_lines
            ):
                findings.append(
                    _finding(
                        "commercial_pillar_market_evidence_mismatch",
                        row,
                        "No bound evidence row contains the recorded Semrush report and market database.",
                    )
                )
            if not any(record.canonical_url in line for line in bound_lines):
                findings.append(
                    _finding(
                        "commercial_pillar_url_evidence_mismatch",
                        row,
                        "No bound evidence row contains the canonical destination URL.",
                    )
                )
            if not any(_line_binds_title(line, record.page_title) for line in bound_lines):
                findings.append(
                    _finding(
                        "commercial_pillar_title_evidence_mismatch",
                        row,
                        "No bound evidence row contains the recorded live-page title.",
                    )
                )
    return findings


def _url_findings(record: CommercialPillarRecord, *, row: int) -> list[Finding]:
    parsed = urlparse(record.canonical_url)
    findings: list[Finding] = []
    if parsed.scheme != "https" or not parsed.netloc or not parsed.path.startswith("/"):
        findings.append(_finding("commercial_pillar_url_invalid", row, "Canonical URL must be an absolute HTTPS URL."))
        return findings
    if parsed.query or parsed.fragment or parsed.params or parsed.username or parsed.password:
        findings.append(_finding("commercial_pillar_url_noncanonical", row, "Canonical URL cannot contain credentials, parameters, query strings, or fragments."))
    if (
        parsed.netloc != parsed.netloc.lower()
        or parsed.path != parsed.path.lower()
        or (parsed.path != "/" and parsed.path.endswith("/"))
        or "//" in parsed.path
    ):
        findings.append(_finding("commercial_pillar_url_noncanonical", row, "Canonical URL casing and path shape are not canonical."))
    expected_host = EXPECTED_HOST_BY_BRAND.get(record.brand.casefold())
    if not expected_host or parsed.netloc != expected_host:
        findings.append(_finding("commercial_pillar_brand_domain_mismatch", row, f"Destination host does not match brand {record.brand}."))
    expected_prefix = EXPECTED_PATH_PREFIX.get(record.pillar_type)
    if expected_prefix:
        if record.pillar_type == "industries_hub":
            path_matches = parsed.path == expected_prefix
        else:
            path_matches = parsed.path.startswith(expected_prefix) and parsed.path != expected_prefix
        if not path_matches:
            findings.append(_finding("commercial_pillar_url_family_mismatch", row, f"URL path does not match pillar type {record.pillar_type}."))
    return findings


def _date_findings(
    record: CommercialPillarRecord,
    *,
    row: int,
    today: date,
    enforce_freshness: bool,
) -> list[Finding]:
    findings: list[Finding] = []
    parsed_dates: dict[str, date] = {}
    for field, value in (
        ("title_checked", record.title_checked),
        ("title_valid_through", record.title_valid_through),
        ("semrush_checked", record.semrush_checked),
        ("semrush_valid_through", record.semrush_valid_through),
    ):
        try:
            parsed_dates[field] = date.fromisoformat(value)
        except ValueError:
            findings.append(_finding("commercial_pillar_date_invalid", row, f"{field} must use YYYY-MM-DD."))
    for checked_field in ("title_checked", "semrush_checked"):
        checked = parsed_dates.get(checked_field)
        if checked and checked > today:
            findings.append(_finding("commercial_pillar_checked_date_future", row, f"{checked_field} cannot be in the future."))
    title_expiry = parsed_dates.get("title_valid_through")
    semrush_expiry = parsed_dates.get("semrush_valid_through")
    if enforce_freshness and title_expiry and title_expiry < today:
        findings.append(_finding("commercial_pillar_title_evidence_expired", row, "Live-page title evidence has expired."))
    if enforce_freshness and semrush_expiry and semrush_expiry < today:
        findings.append(_finding("commercial_pillar_semrush_evidence_expired", row, "Semrush evidence has expired."))
    if parsed_dates.get("title_checked") and title_expiry and title_expiry < parsed_dates["title_checked"]:
        findings.append(_finding("commercial_pillar_date_order_invalid", row, "Title validity cannot end before it was checked."))
    if parsed_dates.get("semrush_checked") and semrush_expiry and semrush_expiry < parsed_dates["semrush_checked"]:
        findings.append(_finding("commercial_pillar_date_order_invalid", row, "Semrush validity cannot end before it was checked."))
    return findings


def _evidence_findings(
    index: CommercialPillarIndex,
    *,
    evidence_path: str,
    locator: str,
    expected_hash: str,
    row: int,
) -> list[Finding]:
    if not evidence_path or not locator or not expected_hash:
        return [_finding("commercial_pillar_evidence_binding_missing", row, "Evidence path, locator, and hash are required.")]
    locator_match = LOCATOR_RE.match(locator)
    if not locator_match:
        return [_finding("commercial_pillar_evidence_locator_invalid", row, f"Unsupported evidence locator: {locator}")]
    source_path = _resolve_evidence_path(index, evidence_path)
    if not _path_is_under_root(index, source_path):
        return [_finding("commercial_pillar_evidence_path_outside_root", row, f"Evidence path resolves outside the index root: {evidence_path}")]
    if not source_path.exists():
        return [_finding("commercial_pillar_evidence_path_missing", row, f"Evidence path does not exist: {evidence_path}")]
    source_lines = source_path.read_text(encoding="utf-8-sig").splitlines()
    evidence_text = _locator_text(source_lines, locator_match)
    if evidence_text is None:
        return [_finding("commercial_pillar_evidence_locator_missing", row, f"Evidence locator is outside the source: {locator}")]
    actual_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or actual_hash != expected_hash:
        return [_finding("commercial_pillar_evidence_hash_mismatch", row, f"Evidence hash no longer matches {evidence_path} {locator}.")]
    return []


def _bound_evidence_lines(
    index: CommercialPillarIndex,
    record: CommercialPillarRecord,
) -> list[str]:
    lines: list[str] = []
    for evidence_path, locator in zip(record.evidence_path, record.evidence_locator):
        locator_match = LOCATOR_RE.match(locator)
        if not locator_match:
            continue
        source_path = _resolve_evidence_path(index, evidence_path)
        if not _path_is_under_root(index, source_path):
            continue
        if not source_path.exists():
            continue
        source_lines = source_path.read_text(encoding="utf-8-sig").splitlines()
        evidence_text = _locator_text(source_lines, locator_match)
        if evidence_text is not None:
            lines.append(evidence_text)
    return lines


def _locator_text(source_lines: list[str], locator_match: re.Match[str]) -> Optional[str]:
    if locator_match.group("line"):
        start = end = int(locator_match.group("line"))
    else:
        start = int(locator_match.group("start"))
        end = int(locator_match.group("end"))
    if end < start or end > len(source_lines):
        return None
    return "\n".join(source_lines[start - 1 : end])


def _line_binds_keyword_metrics(line: str, record: CommercialPillarRecord) -> bool:
    normalized_keyword = _normalize_evidence_cell(record.main_keyword)
    saw_table_row = False
    for physical_line in line.splitlines():
        cells = _markdown_cells(physical_line)
        if len(cells) >= 3:
            saw_table_row = True
            if _normalize_evidence_cell(cells[0]) != normalized_keyword:
                continue
            return (
                _numeric_cell_value(cells[1]) == record.volume
                and _numeric_cell_value(cells[2]) == record.keyword_difficulty
            )
    if saw_table_row:
        return False
    normalized_line = re.sub(r"\s+", " ", line.casefold())
    volume_values = {str(record.volume), f"{record.volume:,}"}
    volume_matches = any(
        re.search(rf"(?<!\d){re.escape(value)}(?!\d)", line)
        for value in volume_values
    )
    difficulty_matches = bool(
        re.search(rf"(?<!\d){record.keyword_difficulty}(?!\d)", line)
    )
    return re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", normalized_line) is not None and volume_matches and difficulty_matches


def _line_binds_title(line: str, page_title: str) -> bool:
    evidence_text = re.sub(r"^\s*#{1,6}\s+", "", line)
    evidence_text = re.sub(r"[*_`]", "", evidence_text)
    normalize = lambda value: re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return normalize(evidence_text) == normalize(page_title)


def _line_binds_market_report(line: str, record: CommercialPillarRecord) -> bool:
    normalized = line.casefold().replace("`", "")
    report_pattern = rf"(?<![a-z0-9_]){re.escape(record.semrush_report.casefold())}(?![a-z0-9_])"
    return (
        re.search(report_pattern, normalized) is not None
        and f"database={record.semrush_database.casefold()}" in normalized
    )


def _resolve_evidence_path(index: CommercialPillarIndex, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    root = _evidence_root(index)
    candidates = [root / candidate, Path.cwd() / candidate]
    if index.source_path:
        candidates.extend([index.source_path.parent / candidate, index.source_path.parent.parent / candidate])
    for resolved in candidates:
        if resolved.exists():
            return resolved.resolve()
    return candidates[0].resolve()


def _evidence_root(index: CommercialPillarIndex) -> Path:
    if index.source_path is None:
        return Path.cwd().resolve()
    parent = index.source_path.parent.resolve()
    if parent.name.casefold() == "context":
        return parent.parent
    return parent


def _path_is_under_root(index: CommercialPillarIndex, path: Path) -> bool:
    root = _evidence_root(index)
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _markdown_cells(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _normalize_evidence_cell(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _numeric_cell_value(value: str) -> int | None:
    digits = re.sub(r"[^\d]", "", value)
    return int(digits) if digits else None


def _title_keyword_fit(page_title: str, keyword: str) -> bool:
    title_tokens = set(re.findall(r"[a-z0-9]+", page_title.casefold()))
    keyword_tokens = set(re.findall(r"[a-z0-9]+", keyword.casefold()))
    generic = {"simpro", "software", "solution", "solutions", "industry", "industries", "feature", "features", "for", "management"}
    significant_title_tokens = title_tokens - generic
    return bool(significant_title_tokens) and significant_title_tokens.issubset(keyword_tokens)


def _record_from_mapping(raw: Mapping[str, Any], *, row: int) -> CommercialPillarRecord:
    def text(field: str) -> str:
        value = raw.get(field, "")
        return str(value).strip() if value is not None else ""

    def integer(field: str) -> int:
        value = raw.get(field, 0)
        try:
            return int(str(value).replace(",", "").strip())
        except ValueError as exc:
            raise CommercialPillarIndexError(f"Record {row} field {field} must be an integer.") from exc

    def values(field: str) -> tuple[str, ...]:
        value = raw.get(field, [])
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split("|") if item.strip())
        if isinstance(value, list) or isinstance(value, tuple):
            return tuple(str(item).strip() for item in value if str(item).strip())
        raise CommercialPillarIndexError(f"Record {row} field {field} must be a list or pipe-delimited string.")

    return CommercialPillarRecord(
        destination_id=text("destination_id"),
        brand=text("brand"),
        market=text("market").upper(),
        pillar_type=text("pillar_type").lower(),
        canonical_url=text("canonical_url"),
        page_title=text("page_title"),
        title_checked=text("title_checked"),
        title_valid_through=text("title_valid_through"),
        main_keyword=text("main_keyword"),
        semrush_database=text("semrush_database").lower(),
        semrush_report=text("semrush_report"),
        semrush_checked=text("semrush_checked"),
        semrush_valid_through=text("semrush_valid_through"),
        semrush_result_status=text("semrush_result_status").lower(),
        volume=integer("volume"),
        keyword_difficulty=integer("keyword_difficulty"),
        evidence_path=values("evidence_path"),
        evidence_locator=values("evidence_locator"),
        evidence_sha256=values("evidence_sha256"),
        vault_routes=values("vault_routes"),
        status=text("status").lower(),
    )


def _record_to_dict(record: CommercialPillarRecord) -> dict[str, Any]:
    return {
        "destination_id": record.destination_id,
        "brand": record.brand,
        "market": record.market,
        "pillar_type": record.pillar_type,
        "canonical_url": record.canonical_url,
        "page_title": record.page_title,
        "title_checked": record.title_checked,
        "title_valid_through": record.title_valid_through,
        "main_keyword": record.main_keyword,
        "semrush_database": record.semrush_database,
        "semrush_report": record.semrush_report,
        "semrush_checked": record.semrush_checked,
        "semrush_valid_through": record.semrush_valid_through,
        "semrush_result_status": record.semrush_result_status,
        "volume": record.volume,
        "keyword_difficulty": record.keyword_difficulty,
        "evidence_path": list(record.evidence_path),
        "evidence_locator": list(record.evidence_locator),
        "evidence_sha256": list(record.evidence_sha256),
        "vault_routes": list(record.vault_routes),
        "status": record.status,
    }


def _read_intake(path: str | Path) -> tuple[list[tuple[int, dict[str, str]]], list[Finding]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [field for field in INTAKE_FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            return [], [_finding("commercial_pillar_intake_column_missing", 1, f"Intake CSV is missing columns: {', '.join(missing)}")]
        rows = [
            (line, {key: (value or "").strip() for key, value in row.items()})
            for line, row in enumerate(reader, start=2)
            if any((value or "").strip() for value in row.values())
        ]
    return rows, []


def _merge_records(
    current: CommercialPillarIndex,
    incoming: Iterable[CommercialPillarRecord],
) -> CommercialPillarIndex:
    records = {record.destination_id: record for record in current.records}
    for record in incoming:
        records[record.destination_id] = record
    return CommercialPillarIndex(
        schema_version=current.schema_version,
        updated_at=current.updated_at,
        records=tuple(records.values()),
        source_path=current.source_path,
    )


def _finding(rule_id: str, line: int, message: str) -> Finding:
    return make_finding(
        rule_id,
        "error",
        line,
        message=message,
        suggestion="Correct the verified commercial pillar evidence or keep the destination blocked.",
    )


def _cli(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and maintain the verified commercial pillar index.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an index JSON file.")
    validate_parser.add_argument("--index", default="context/commercial-pillar-index.json")

    intake_parser = subparsers.add_parser("validate-intake", help="Validate an intake CSV.")
    intake_parser.add_argument("input_path")
    intake_parser.add_argument("--index", default="context/commercial-pillar-index.json")

    merge_parser = subparsers.add_parser("merge", help="Merge a valid intake CSV.")
    merge_parser.add_argument("input_path")
    merge_parser.add_argument("--index", default="context/commercial-pillar-index.json")
    merge_parser.add_argument("--out", default="context/commercial-pillar-index.json")
    args = parser.parse_args(argv)

    try:
        if args.command == "validate":
            findings = validate_index(load_index(args.index), today=date.today())
            payload = {"passed": not findings, "summary": summarize_findings(findings), "findings": findings}
        elif args.command == "validate-intake":
            findings = validate_intake_file(args.input_path, index_path=args.index)
            payload = {"passed": not findings, "summary": summarize_findings(findings), "findings": findings}
        else:
            payload = merge_intake_file(args.input_path, index_path=args.index, out_path=args.out)
    except CommercialPillarIndexError as exc:
        payload = {"passed": False, "errors": 1, "findings": [_finding("commercial_pillar_index_load_failed", 1, str(exc))]}
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    sys.exit(_cli())
