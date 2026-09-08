import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from data_sources.modules.commercial_pillar_index import (
    CommercialPillarIndexError,
    get_verified_destination,
    load_index,
    merge_intake_file,
    validate_index,
    validate_intake_file,
)


def _write_evidence(root: Path) -> tuple[Path, Path, str, str, str, str]:
    keyword_path = root / "target-keywords.md"
    link_path = root / "internal-links-map.md"
    keyword_line = "| field service management software | 6,600 | 47 |"
    market_line = "**Source boundary**: Semrush Exact US Keyword Metrics using `phrase_these` with `database=us`."
    title_line = "### Field Service Management Software"
    link_line = "- **URL**: https://www.simprogroup.com/solutions/field-service-management-software"
    keyword_path.write_text(f"{market_line}\n{keyword_line}\n", encoding="utf-8")
    link_path.write_text(f"{title_line}\n{link_line}\n", encoding="utf-8")
    return keyword_path, link_path, keyword_line, market_line, title_line, link_line


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _record(root: Path, **overrides: object) -> dict[str, object]:
    keyword_path, link_path, keyword_line, market_line, title_line, link_line = _write_evidence(root)
    record: dict[str, object] = {
        "destination_id": "simpro-us-solution-field-service-management-software",
        "brand": "Simpro",
        "market": "US",
        "pillar_type": "solution",
        "canonical_url": "https://www.simprogroup.com/solutions/field-service-management-software",
        "page_title": "Field Service Management Software",
        "title_checked": "2026-08-01",
        "title_valid_through": "2026-11-01",
        "main_keyword": "field service management software",
        "semrush_database": "us",
        "semrush_report": "phrase_these",
        "semrush_checked": "2026-08-01",
        "semrush_valid_through": "2026-09-01",
        "semrush_result_status": "exact",
        "volume": 6600,
        "keyword_difficulty": 47,
        "evidence_path": [str(keyword_path), str(link_path), str(link_path)],
        "evidence_locator": ["lines:1-2", "line:1", "line:2"],
        "evidence_sha256": [_sha(f"{market_line}\n{keyword_line}"), _sha(title_line), _sha(link_line)],
        "vault_routes": [
            "wiki/product/Product Positioning.md",
            "wiki/messaging/Simpro Core Messaging Repository.md",
        ],
        "status": "verified",
    }
    record.update(overrides)
    return record


def _write_index(path: Path, records: list[dict[str, object]], **overrides: object) -> None:
    payload: dict[str, object] = {
        "schema_version": "commercial-pillar-index/v1",
        "updated_at": "2026-08-01",
        "records": records,
    }
    payload.update(overrides)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_and_resolve_verified_destination(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path, [_record(tmp_path)])

    index = load_index(index_path)
    findings = validate_index(index, today=date(2026, 8, 6))
    destination = get_verified_destination(
        index,
        destination_id="simpro-us-solution-field-service-management-software",
        brand="Simpro",
        market="US",
    )

    assert findings == []
    assert destination.main_keyword == "field service management software"
    assert destination.volume == 6600


@pytest.mark.parametrize(
    ("mutation", "rule_id"),
    [
        ({"pillar_type": "blog"}, "commercial_pillar_type_invalid"),
        ({"market": "Mars"}, "commercial_pillar_market_invalid"),
        ({"canonical_url": "http://www.simprogroup.com/solutions/test"}, "commercial_pillar_url_invalid"),
        ({"canonical_url": "https://www.simprogroup.com/solutions/test?x=1"}, "commercial_pillar_url_noncanonical"),
        ({"canonical_url": "https://www.simprogroup.com/Solutions/test"}, "commercial_pillar_url_noncanonical"),
        ({"page_title": ""}, "commercial_pillar_page_title_missing"),
        ({"title_valid_through": "2026-08-05"}, "commercial_pillar_title_evidence_expired"),
        ({"semrush_valid_through": "2026-08-05"}, "commercial_pillar_semrush_evidence_expired"),
        ({"semrush_database": "uk"}, "commercial_pillar_semrush_market_mismatch"),
        ({"vault_routes": []}, "commercial_pillar_vault_routes_missing"),
        ({"status": "active"}, "commercial_pillar_status_invalid"),
        ({"page_title": "Scheduling"}, "commercial_pillar_title_keyword_mismatch"),
    ],
)
def test_validator_fails_closed_on_invalid_record(
    tmp_path: Path,
    mutation: dict[str, object],
    rule_id: str,
) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path, [_record(tmp_path, **mutation)])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert rule_id in {finding["rule_id"] for finding in findings}


def test_validator_detects_duplicate_ids_urls_and_locators(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    first = _record(tmp_path)
    second = dict(first)
    _write_index(index_path, [first, second])

    rule_ids = {
        finding["rule_id"]
        for finding in validate_index(load_index(index_path), today=date(2026, 8, 6))
    }

    assert "commercial_pillar_destination_id_duplicate" in rule_ids
    assert "commercial_pillar_canonical_url_duplicate" in rule_ids
    assert "commercial_pillar_evidence_locator_duplicate" in rule_ids


def test_validator_detects_tampered_evidence(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    record = _record(tmp_path)
    _write_index(index_path, [record])
    Path(record["evidence_path"][0]).write_text("heading\ntampered\n", encoding="utf-8")

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_evidence_hash_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_validator_rejects_valid_hashes_bound_to_the_wrong_evidence_content(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    base = tmp_path / "base"
    base.mkdir()
    record = _record(
        base,
        page_title="Dispatch Software",
        main_keyword="dispatch software",
    )
    _write_index(index_path, [record])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_keyword_evidence_mismatch" in {
        finding["rule_id"] for finding in findings
    }
    assert "commercial_pillar_title_evidence_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_keyword_metrics_must_come_from_the_same_keyword_row(tmp_path: Path) -> None:
    keyword_path = tmp_path / "target-keywords.md"
    link_path = tmp_path / "internal-links-map.md"
    market_line = "**Source boundary**: Semrush Exact US Keyword Metrics using `phrase_these` with `database=us`."
    field_row = "| field service management software | 6,600 | 47 |"
    hvac_row = "| HVAC software | 2,900 | 37 |"
    title_line = "### HVAC"
    link_line = "- **URL**: https://www.simprogroup.com/industries/hvac-software"
    keyword_text = f"{market_line}\n{field_row}\n{hvac_row}"
    keyword_path.write_text(keyword_text, encoding="utf-8")
    link_path.write_text(f"{title_line}\n{link_line}\n", encoding="utf-8")
    base = tmp_path / "base"
    base.mkdir()
    record = _record(
        base,
        destination_id="simpro-us-industry-hvac-software",
        pillar_type="industry",
        canonical_url="https://www.simprogroup.com/industries/hvac-software",
        page_title="HVAC",
        main_keyword="HVAC software",
        volume=6600,
        keyword_difficulty=47,
        evidence_path=[str(keyword_path), str(link_path), str(link_path)],
        evidence_locator=["lines:1-3", "line:1", "line:2"],
        evidence_sha256=[_sha(keyword_text), _sha(title_line), _sha(link_line)],
    )
    index_path = tmp_path / "index.json"
    _write_index(index_path, [record])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_keyword_evidence_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_semrush_report_must_match_exact_report_token(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path, [_record(tmp_path, semrush_report="phrase")])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_market_evidence_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_evidence_paths_cannot_escape_the_index_root(tmp_path: Path) -> None:
    root = tmp_path / "index-root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    keyword_path, link_path, keyword_line, market_line, title_line, link_line = _write_evidence(outside)
    record = _record(
        outside,
        evidence_path=[str(keyword_path), str(link_path), str(link_path)],
        evidence_locator=["lines:1-2", "line:1", "line:2"],
        evidence_sha256=[_sha(f"{market_line}\n{keyword_line}"), _sha(title_line), _sha(link_line)],
    )
    index_path = root / "index.json"
    _write_index(index_path, [record])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_evidence_path_outside_root" in {
        finding["rule_id"] for finding in findings
    }


def test_us_evidence_cannot_be_relabelled_as_another_market(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    record = _record(tmp_path, market="UK", semrush_database="uk")
    _write_index(index_path, [record])

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_market_evidence_mismatch" in {
        finding["rule_id"] for finding in findings
    }


@pytest.mark.parametrize(
    ("pillar_type", "path", "title", "keyword"),
    [
        ("solution", "/solutions/field-service-management-software", "Field Service Management Software", "field service management software"),
        ("industry", "/industries/hvac-software", "HVAC", "HVAC software"),
        ("feature", "/features/scheduling-dispatch", "Scheduling Dispatch", "scheduling dispatch software"),
    ],
)
def test_solution_industry_and_feature_destinations_validate(
    tmp_path: Path,
    pillar_type: str,
    path: str,
    title: str,
    keyword: str,
) -> None:
    record = _record(tmp_path)
    keyword_path = tmp_path / "target-keywords.md"
    link_path = tmp_path / "internal-links-map.md"
    keyword_line = f"| {keyword} | 1,000 | 25 |"
    title_line = f"### {title}"
    url = f"https://www.simprogroup.com{path}"
    url_line = f"- **URL**: {url}"
    market_line = "**Source boundary**: Semrush Exact US Keyword Metrics using `phrase_these` with `database=us`."
    keyword_path.write_text(f"{market_line}\n{keyword_line}\n", encoding="utf-8")
    link_path.write_text(f"{title_line}\n{url_line}\n", encoding="utf-8")
    record.update(
        {
            "destination_id": f"simpro-us-{pillar_type}-test",
            "pillar_type": pillar_type,
            "canonical_url": url,
            "page_title": title,
            "main_keyword": keyword,
            "volume": 1000,
            "keyword_difficulty": 25,
            "evidence_path": [str(keyword_path), str(link_path), str(link_path)],
            "evidence_locator": ["lines:1-2", "line:1", "line:2"],
            "evidence_sha256": [_sha(f"{market_line}\n{keyword_line}"), _sha(title_line), _sha(url_line)],
        }
    )
    index_path = tmp_path / "index.json"
    _write_index(index_path, [record])

    assert validate_index(load_index(index_path), today=date(2026, 8, 6)) == []


def test_a_blog_url_cannot_be_a_commercial_pillar(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(
        index_path,
        [_record(tmp_path, canonical_url="https://www.simprogroup.com/blog/field-service-management-software")],
    )

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert "commercial_pillar_url_family_mismatch" in {
        finding["rule_id"] for finding in findings
    }


def test_get_verified_destination_rejects_cross_market_and_blocked_records(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path, [_record(tmp_path, status="blocked")])
    index = load_index(index_path)

    with pytest.raises(CommercialPillarIndexError, match="brand/market"):
        get_verified_destination(
            index,
            destination_id="simpro-us-solution-field-service-management-software",
            brand="Simpro",
            market="UK",
        )

    with pytest.raises(CommercialPillarIndexError, match="brand/market"):
        get_verified_destination(
            index,
            destination_id="simpro-us-solution-field-service-management-software",
            brand="ClockShark",
            market="US",
        )

    with pytest.raises(CommercialPillarIndexError, match="not verified"):
        get_verified_destination(
            index,
            destination_id="simpro-us-solution-field-service-management-software",
            brand="Simpro",
            market="US",
        )


def test_blocked_and_stale_records_can_remain_indexed_but_cannot_be_selected(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    blocked_root = tmp_path / "blocked"
    stale_root = tmp_path / "stale"
    blocked_root.mkdir()
    stale_root.mkdir()
    blocked = _record(
        blocked_root,
        destination_id="simpro-uk-solution-field-service-management-software",
        market="UK",
        semrush_database="uk",
        semrush_result_status="unavailable",
        volume=0,
        keyword_difficulty=0,
        status="blocked",
    )
    stale = _record(
        stale_root,
        destination_id="simpro-us-solution-stale",
        status="stale",
        title_valid_through="2026-08-05",
        semrush_valid_through="2026-08-05",
    )
    _write_index(index_path, [blocked, stale])
    index = load_index(index_path)

    assert validate_index(index, today=date(2026, 8, 6)) == []
    for destination_id, market in (
        ("simpro-uk-solution-field-service-management-software", "UK"),
        ("simpro-us-solution-stale", "US"),
    ):
        with pytest.raises(CommercialPillarIndexError, match="not verified"):
            get_verified_destination(
                index,
                destination_id=destination_id,
                brand="Simpro",
                market=market,
            )

def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(
        index_path,
        [_record(tmp_path)],
        schema_version="commercial-pillar-index/v2",
    )

    findings = validate_index(load_index(index_path), today=date(2026, 8, 6))

    assert findings[0]["rule_id"] == "commercial_pillar_schema_unsupported"


INTAKE_FIELDS = [
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
]


def test_intake_validation_and_merge_use_same_fail_closed_contract(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    out_path = tmp_path / "merged.json"
    intake_path = tmp_path / "intake.csv"
    _write_index(index_path, [])
    record = _record(tmp_path)
    row = {
        key: " | ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for key, value in record.items()
    }
    with intake_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTAKE_FIELDS)
        writer.writeheader()
        writer.writerow(row)

    assert validate_intake_file(intake_path, index_path=index_path, today=date(2026, 8, 6)) == []
    result = merge_intake_file(
        intake_path,
        index_path=index_path,
        out_path=out_path,
        today=date(2026, 8, 6),
    )

    assert result["passed"] is True
    assert result["appended"] == 1
    assert load_index(out_path).records[0].destination_id == record["destination_id"]


def test_intake_validation_rejects_duplicate_incoming_destination_ids(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    intake_path = tmp_path / "intake.csv"
    _write_index(index_path, [])
    record = _record(tmp_path)
    row = {
        key: " | ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for key, value in record.items()
    }
    with intake_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTAKE_FIELDS)
        writer.writeheader()
        writer.writerow(row)
        writer.writerow(row)

    findings = validate_intake_file(
        intake_path,
        index_path=index_path,
        today=date(2026, 8, 6),
    )

    assert "commercial_pillar_destination_id_duplicate" in {
        finding["rule_id"] for finding in findings
    }


def test_malformed_intake_row_returns_a_finding_instead_of_crashing(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    intake_path = tmp_path / "intake.csv"
    _write_index(index_path, [])
    record = _record(tmp_path, volume="not-a-number")
    row = {
        key: " | ".join(str(item) for item in value) if isinstance(value, list) else str(value)
        for key, value in record.items()
    }
    with intake_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=INTAKE_FIELDS)
        writer.writeheader()
        writer.writerow(row)

    findings = validate_intake_file(
        intake_path,
        index_path=index_path,
        today=date(2026, 8, 6),
    )

    assert findings[0]["rule_id"] == "commercial_pillar_intake_row_invalid"
