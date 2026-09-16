import pytest

from data_sources.modules.source_support_guard import check_content


def test_genuine_imperative_advice_is_not_an_unsupported_recommendation() -> None:
    content = "# Drafting guide\n\nExplain what readers should do next.\n"

    assert check_content(content) == []


def test_genuine_checklist_items_are_not_unsupported_recommendations() -> None:
    content = """# Drafting guide

## Draft checklist

- [ ] Explain what readers should do next.
- [ ] State which decision the reader should make.
"""

    assert check_content(content) == []


def test_what_to_write_table_is_not_an_unsupported_recommendation() -> None:
    content = """# Drafting guide

| Section | What to write |
|---|---|
| Opening | Explain the reader's problem and the next action. |
| Close | State the decision the reader should make. |
"""

    assert check_content(content) == []


@pytest.mark.parametrize(
    "instruction",
    (
        "State that the plan costs $99 per user.",
        "Explain how the workflow reduces delays.",
        "State that state law requires a license before work begins.",
        "State that the plan is free for every user.",
        "State that the service fee is waived.",
        "State that the add-on is currently available.",
    ),
)
def test_instructional_context_does_not_exempt_high_risk_claims(
    instruction: str,
) -> None:
    content = f"""# Drafting guide

## Draft checklist

- [ ] {instruction}
"""

    assert check_content(content)
