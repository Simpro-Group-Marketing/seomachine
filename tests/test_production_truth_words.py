import pytest

from data_sources.modules.production.truth_numbers import number_tokens
from tests.production_truth_support import VERIFIED_AT, article, blocks, bom, check_truth_for, transport, with_facts
from tests.production_bom_support import response

STUDY_URL = "https://example.org/invoice-study"
STUDY_QUOTE = "70% of contractors miss invoices every month"


def _empty_bom():
    value = bom()
    value["facts"], value["proof"] = [], []
    return value


def _number_blocks(text, value=None, tr=None):
    found = check_truth_for(article(text + "\n\n"), value if value is not None else _empty_bom(), tr)
    return [f for f in blocks(found) if f.check in {"number_gate", "claim_numbers"}]


def _mentions(findings, written):
    return [f for f in findings if written.casefold() in f.message.casefold()]


@pytest.mark.parametrize(("sentence", "written"), [
    ("Seventy percent of contractors miss invoices every month.", "Seventy percent"),
    ("Half of all field jobs run late.", "Half of"),
    ("Seventy per cent of contractors miss invoices every month.", "Seventy per cent"),
    ("Nine out of ten crews run late.", "Nine"),
    ("One in five crews runs late.", "five"),
    ("Crews finish three times faster.", "three times"),
    ("Twenty-four crews run late.", "Twenty-four"),
])
def test_spelled_material_numbers_block_with_an_empty_bom(sentence, written):
    assert _mentions(_number_blocks(sentence), written), sentence


@pytest.mark.parametrize("sentence", [
    "Contractors waste nine hours each week.",
    "Contractors waste 9 hours each week.",
    "It is one of the best tools for crews.",
    "Hire a third party for the audit.",
    "The first step is a site visit.",
    "A one-off job still needs a quote.",
])
def test_bare_small_and_non_cardinal_words_stay_exempt(sentence):
    assert number_tokens(sentence, "2026") == [], sentence
    assert _number_blocks(sentence, bom()) == [], sentence


def test_spelled_percent_matches_a_digit_fact_quote_linked_in_the_same_paragraph():
    fact = {"id": "f2", "claim": "70% of contractors miss invoices", "url": STUDY_URL, "quote": STUDY_QUOTE,
            "priority": "should", "verified_at": VERIFIED_AT, "check_detail": "d", "support": "quote_overlap"}
    tr = transport(**{STUDY_URL: response(STUDY_URL, 200, f"<p>{STUDY_QUOTE}.</p>")})
    linked = f"Seventy percent of contractors miss invoices every month, per [the study]({STUDY_URL})."
    assert _number_blocks(linked, with_facts([fact]), tr) == []
    unlinked = "Seventy percent of contractors miss invoices every month."
    assert _mentions(_number_blocks(unlinked, with_facts([fact]), tr), "70")


def test_spelled_thousands_match_the_digit_fact():
    tokens = number_tokens("More than twenty-four thousand trade businesses", "2026")
    assert [(t.canonical, t.material) for t in tokens] == [("24000", True)]


def test_spelled_article_year_is_not_material():
    tokens = number_tokens("two thousand twenty-six", "2026")
    assert [(t.canonical, t.material) for t in tokens] == [("2026", False)]
