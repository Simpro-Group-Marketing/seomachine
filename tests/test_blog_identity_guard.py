from __future__ import annotations

from tests.fixture_text import fixture_text

from datetime import date

from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_identity_guard import check_article


VALID = fixture_text("content_evidence:test_blog_identity_guard-9-1")


def _rules(content: str) -> set[str]:
    return {finding["rule_id"] for finding in check_article(content)}


def test_valid_blog_identity_passes():
    assert check_article(VALID) == []


def test_missing_required_blog_identity_field_fails():
    content = VALID.replace("objective: Help field service leaders choose a workflow\n", "")

    assert "blog_identity_objective_missing" in _rules(content)


def test_placeholder_blog_identity_value_fails():
    content = VALID.replace("audience: Field service leaders", "audience: Not provided")

    assert "blog_identity_audience_placeholder" in _rules(content)


def test_placeholder_author_is_not_a_named_author():
    content = VALID.replace(
        "schema_notes:\n",
        "author: Not provided\nschema_notes:\n",
    )

    assert "blog_identity_author_placeholder" in _rules(content)


def test_explicit_empty_author_must_be_omitted():
    content = VALID.replace(
        "schema_notes:\n",
        'author: ""\nschema_notes:\n',
    )

    assert "blog_identity_author_empty" in _rules(content)


def test_invalid_freshness_date_fails():
    content = VALID.replace("last_updated: 2026-08-11", "last_updated: yesterday")

    assert "blog_identity_last_updated_invalid" in _rules(content)


def test_last_updated_after_assembly_date_fails():
    assert "blog_identity_last_updated_mismatch" in {
        finding["rule_id"]
        for finding in check_article(VALID, assembly_date=date(2026, 8, 10))
    }


def test_last_updated_before_assembly_date_passes():
    assert "blog_identity_last_updated_mismatch" not in {
        finding["rule_id"]
        for finding in check_article(VALID, assembly_date=date(2026, 8, 12))
    }


def test_past_and_future_assembly_dates_fail_against_injected_utc_date(monkeypatch):
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    for assembly_date in (date(2026, 8, 10), date(2026, 8, 12)):
        content = VALID.replace("2026-08-11", assembly_date.isoformat())
        rules = {
            finding["rule_id"]
            for finding in check_article(content, assembly_date=assembly_date)
        }
        assert "blog_identity_assembly_date_not_current" in rules


def test_landing_page_does_not_inherit_blog_field_contract():
    content = "---\nartifact_type: landing_page\nbrand: Simpro\ntitle: Page\n---\n# Page\n"

    assert check_article(content) == []
