import pytest
from tests.production_bom_support import FACT_URL, PAA_QUESTION, response
from tests.production_truth_support import (
    CUSTOMER_QUOTE,
    PROOF_TEXT,
    article,
    blocks,
    bom,
    check_truth_for,
    transport,
)

FACT_QUOTE_TEXT = "Trusted by more than 24,000 trade businesses worldwide"


def gate(text):
    return blocks(check_truth_for(text), "number_gate")


def quoted(text):
    return blocks(check_truth_for(text), "quoted_passage")


def test_uncited_percentage_in_the_body_blocks_with_line():
    found = gate(article("Crews save 40% of admin time.\n\n"))
    assert len(found) == 1 and "40" in found[0].message and found[0].line == 15


def test_bare_small_integers_are_exempt_but_attached_ones_are_not():
    assert gate(article("Teams get started in 5 steps and 10 minutes.\n\n")) == []
    for attached in ("6%", "$6", "£6", "€6", "A$6", "6k", "6 million", "6 bn", "6 percent"):
        assert gate(article(f"Teams pay {attached} a month.\n\n")), attached


def test_integers_above_ten_and_decimals_need_a_source():
    assert gate(article("Teams have 11 seats.\n\n"))
    assert gate(article("Teams have 2.5 seats.\n\n"))


def test_numbers_from_bom_quotes_proof_and_the_article_year_pass():
    assert gate(article("In 2026, 24k firms and 30% faster invoicing and 5 hours saved appear here.\n\n")) == []


def test_list_numbering_and_24_7_are_exempt():
    body = "1. First step\n2. Second step\n11. Eleventh step\n\n## Step 12 of the plan\n\nSupport runs 24/7 for crews.\n\n"
    assert gate(article(body)) == []


def test_heading_markers_do_not_hide_numbers():
    assert gate(article("## 12 ways to save\n\n"))


def test_dates_are_not_numbers():
    assert gate(article("Updated 2026-10-13 for crews.\n\n")) == []


def test_urls_code_comments_and_other_frontmatter_are_not_public_copy():
    guide = "https://example.org/a/9999"
    body = (
        f"See [the guide]({guide}) and ![chart](img/55555.png).\n\n"
        "Run `top -n 7777` now.\n\n```\nprice = 8888\n```\n\n<!-- note 6666 -->\n\n"
    )
    tr = transport(**{guide: response(guide, 200)})
    found = blocks(check_truth_for(article(body, extra_front="reviewer_id: 4444\n"), tr=tr), "number_gate")
    assert found == []


def test_title_and_description_numbers_are_checked():
    found = gate(article(title="77 Field Service Tips"))
    assert found and found[0].line == 2


def test_link_text_and_headings_count_as_public_copy():
    assert gate(article(f"See [99% uptime]({FACT_URL}) today.\n\n"))
    assert gate(article("## Why 73 firms switch\n\n"))


@pytest.mark.parametrize("quote", ['"invoicing went from a fantasy to a nightmare overnight"',
                                   "“invoicing went from a fantasy to a nightmare overnight”"])
def test_invented_quote_of_four_words_or_more_blocks(quote):
    found = quoted(article(f"One owner said {quote} after switching.\n\n"))
    assert len(found) == 1 and found[0].line == 15


def test_verbatim_quote_from_bom_sources_passes_in_any_case_and_quote_style():
    for source in (CUSTOMER_QUOTE, PROOF_TEXT, FACT_QUOTE_TEXT):
        for wrapped in (f'"{source}"', f"“{source.upper()}”", f'"{source},"'):
            text = article(f"One owner said {wrapped} after switching.\n\n")
            assert quoted(text) == [], wrapped


def test_short_quotes_and_scare_quotes_pass():
    assert quoted(article('A "smart" tool, or "good enough" here.\n\n')) == []


def test_blockquote_must_be_verbatim_in_the_bom():
    assert quoted(article("> Totally made up praise.\n\n"))
    assert quoted(article(f"> {CUSTOMER_QUOTE}\n\n")) == []


def test_wrapped_blockquote_passes_when_the_whole_passage_is_verbatim():
    assert quoted(article("> invoicing went from a weekly chore\n> to a same-day task\n\n")) == []


def test_faq_question_must_match_a_bom_paa_question_ignoring_case_and_punctuation():
    ok = article().replace(PAA_QUESTION, "WHAT is   field service software ??")
    assert blocks(check_truth_for(ok), "faq_question") == []
    bad = article().replace(PAA_QUESTION, "Is field service software worth it?")
    found = blocks(check_truth_for(bad), "faq_question")
    assert len(found) == 1 and "Is field service software worth it?" in found[0].message


def test_every_faq_question_blocks_when_the_bom_has_no_paa():
    value = bom()
    value["paa"] = {"artifact": None, "questions": []}
    assert blocks(check_truth_for(article(), value), "faq_question")
