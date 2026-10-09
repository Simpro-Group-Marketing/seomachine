from datetime import date
from pathlib import Path

from data_sources.modules.commercial_pillar_index import load_index, validate_index
from tests.test_commercial_pillar_index import _sha, _write_index


def _bigchange_record(root: Path, **overrides: object) -> dict[str, object]:
    keyword_path = root / "bigchange-keyword.md"
    link_path = root / "bigchange-link.md"
    market_line = "Semrush report: keyword_overview_ui | database=uk"
    keyword_line = "| risk assessment software | 1,300 | 19 |"
    title_line = "### Simplify Compliance with Digital Risk Assessments and RAMS at the Point of Work"
    link_line = "- URL: https://www.bigchange.com/features/risk-assessment"
    keyword_path.write_text(f"{market_line}\n{keyword_line}\n", encoding="utf-8")
    link_path.write_text(f"{title_line}\n{link_line}\n", encoding="utf-8")
    record: dict[str, object] = {
        "destination_id": "bigchange-uk-feature-risk-assessment-software",
        "brand": "BigChange",
        "market": "UK",
        "pillar_type": "feature",
        "canonical_url": "https://www.bigchange.com/features/risk-assessment",
        "page_title": "Simplify Compliance with Digital Risk Assessments and RAMS at the Point of Work",
        "title_checked": "2026-09-25",
        "title_valid_through": "2026-12-24",
        "main_keyword": "risk assessment software",
        "semrush_database": "uk",
        "semrush_report": "keyword_overview_ui",
        "semrush_checked": "2026-09-25",
        "semrush_valid_through": "2026-12-24",
        "semrush_result_status": "exact",
        "volume": 1300,
        "keyword_difficulty": 19,
        "evidence_path": [str(keyword_path), str(link_path), str(link_path)],
        "evidence_locator": ["lines:1-2", "line:1", "line:2"],
        "evidence_sha256": [
            _sha(f"{market_line}\n{keyword_line}"),
            _sha(title_line),
            _sha(link_line),
        ],
        "vault_routes": [],
        "status": "verified",
    }
    record.update(overrides)
    return record


def test_bigchange_nonconnector_feature_accepts_empty_vault_routes(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(index_path, [_bigchange_record(tmp_path)])

    findings = validate_index(load_index(index_path), today=date(2026, 9, 25))

    assert findings == []


def test_bigchange_nonconnector_feature_rejects_vault_routes(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(
        index_path,
        [_bigchange_record(tmp_path, vault_routes=["wiki/product/Product Positioning.md"])],
    )

    findings = validate_index(load_index(index_path), today=date(2026, 9, 25))

    assert "commercial_pillar_vault_routes_unexpected" in {
        finding["rule_id"] for finding in findings
    }


def test_bigchange_feature_rejects_wrong_brand_domain(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    _write_index(
        index_path,
        [_bigchange_record(tmp_path, canonical_url="https://www.simprogroup.com/features/risk-assessment")],
    )

    findings = validate_index(load_index(index_path), today=date(2026, 9, 25))

    assert "commercial_pillar_brand_domain_mismatch" in {
        finding["rule_id"] for finding in findings
    }
