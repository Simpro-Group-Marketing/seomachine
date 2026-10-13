import pytest
from tests.production_bom_support import PAA_QUESTION
from tests.production_truth_support import article, blocks, check_truth_for

ANSWER = "Field service software schedules jobs and dispatches crews for trade businesses.\n"
VALID = f"### {PAA_QUESTION}\n\n{ANSWER}\n"
INVENTED = "Is it worth the price"


def faq_blocks(text):
    return blocks(check_truth_for(text), "faq_question")


@pytest.mark.parametrize("line", [
    f"- {INVENTED}?",
    f"- **{INVENTED}?**",
    f"{INVENTED}?",
    f"*{INVENTED}?*",
    f"__{INVENTED}?__",
    f"_{INVENTED}?_",
    f"| {INVENTED}? |",
    f"| {INVENTED}? | Yes, for most crews. |",
    f"1. {INVENTED}?",
    f"Q: {INVENTED}?",
    f"**Q:** {INVENTED}?",
])
def test_invented_questions_in_other_formats_inside_the_faq_block_are_blocked(line):
    found = faq_blocks(article(faq_section=f"{VALID}{line}\n\nYes it is.\n"))
    assert any(INVENTED in f.message or "question headings" in f.message for f in found), line


def test_bold_rhetorical_questions_and_q_lines_in_the_body_do_not_block():
    body = f"**{INVENTED}?**\n\nQ: {INVENTED}?\n\nPlain text here.\n\n"
    assert faq_blocks(article(body)) == []


def test_question_lines_after_the_faq_section_ends_are_not_in_the_faq_block():
    tail = f"{VALID}## Next steps\n\n**{INVENTED}?**\n\nBook a demo.\n"
    assert faq_blocks(article(faq_section=tail)) == []


def test_answers_that_end_without_a_question_mark_are_fine():
    assert faq_blocks(article(faq_section=VALID + "Plain extra answer text for the crew.\n")) == []
