import pytest

from data_sources.modules.faq_structure import detect_faq_structure


@pytest.mark.parametrize(
    "heading",
    (
        "Questions field service leaders ask",
        "FAQs about scheduling",
        "Common scheduling questions",
        "Frequently asked questions: scheduling",
    ),
)
def test_clear_semantic_faq_h2_headings_are_recognized(heading: str):
    structure = detect_faq_structure(
        "# Scheduling guide\n\n"
        f"## {heading}\n\n"
        "### How should dispatchers assign urgent work?\n\n"
        "Use current capacity, skills, location, and job priority.\n"
    )

    assert structure.heading_present is True
    assert [entry.question for entry in structure.entries] == [
        "How should dispatchers assign urgent work?"
    ]
    assert structure.unsupported_lines == ()


@pytest.mark.parametrize(
    "heading",
    (
        "Questions to consider",
        "FAQ resources",
        "Common questions and objections",
    ),
)
def test_ambiguous_faq_like_h2_headings_fail_closed(heading: str):
    structure = detect_faq_structure(
        "# Scheduling guide\n\n"
        f"## {heading}\n\n"
        "### How should dispatchers assign urgent work?\n\n"
        "Use current capacity, skills, location, and job priority.\n"
    )

    assert structure.heading_present is False
    assert structure.entries == ()
    assert structure.unsupported_lines == (3,)


@pytest.mark.parametrize("fence", ("```text", "~~~text"))
def test_fenced_faq_governance_headings_are_not_visible_content(fence: str):
    closing_fence = fence[:3]
    structure = detect_faq_structure(
        "# Scheduling guide\n\n"
        f"{fence}\n"
        "## FAQ Source Policy\n"
        "## FAQ Proof Map\n"
        "**What source supports this answer?**\n"
        f"{closing_fence}\n"
    )

    assert structure.visible is False
    assert structure.entries == ()
    assert structure.unsupported_lines == ()
