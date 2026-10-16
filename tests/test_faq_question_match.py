from datetime import date

import pytest

from data_sources.modules import blog_assembly_contract
from data_sources.modules.faq_structure import faq_question_match_key


@pytest.fixture(autouse=True)
def _freeze_workflow_clock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )


def test_key_ignores_case_spacing_and_apostrophe_style() -> None:
    assert faq_question_match_key("Is simpro a CRM system?") == faq_question_match_key("Is Simpro a CRM  system?")
    assert faq_question_match_key("What’s Simpro?") == faq_question_match_key("What's Simpro?")

