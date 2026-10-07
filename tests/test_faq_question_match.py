from datetime import date
from pathlib import Path

import pytest

from data_sources.modules import blog_assembly_contract
from data_sources.modules.faq_structure import faq_question_match_key, faq_questions_match
from tests.test_blog_assembly_bom import _build, _fixture
from tests.test_blog_assembly_bom_guard import _rules


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


def test_questions_match_in_order_only() -> None:
    assert faq_questions_match(
        ["Is simpro a CRM system?", "Is simpro a good system?"],
        ["Is Simpro a CRM system?", "Is Simpro a good system?"],
        source_kind="answersocrates",
    )
    assert not faq_questions_match(["A one?", "B two?"], ["B two?", "A one?"], source_kind="answersocrates")


def test_different_wording_still_fails() -> None:
    assert not faq_questions_match(["Is Simpro a CRM?"], ["Is Simpro a CRM system?"], source_kind="answersocrates")


def test_brief_paa_stays_exact_except_outer_whitespace() -> None:
    assert not faq_questions_match(["is simpro a crm system?"], ["Is Simpro a CRM system?"], source_kind="brief_paa")
    assert faq_questions_match([" Is Simpro a CRM system? "], ["Is Simpro a CRM system?"], source_kind="brief_paa")


def test_paa_selected_questions_match_visible_headings_case_insensitively(tmp_path: Path):
    paths = _fixture(tmp_path, visible_faq=True)
    bom = _build(tmp_path, paths)
    bom["paa_policy"]["selected_questions"] = [
        question.lower() for question in bom["paa_policy"]["selected_questions"]
    ]

    rules = _rules(tmp_path, bom, paths)

    assert "bom_paa_questions_mismatch" not in rules
