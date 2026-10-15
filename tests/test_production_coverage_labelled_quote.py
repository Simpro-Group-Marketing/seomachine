"""A connector exact-quote proof whose approved text carries a vault label prefix still counts as used."""

from __future__ import annotations

from tests.test_production_coverage import blocks, cov, plain, with_proof

URL = "https://www.g2.com/products/simpro/reviews/simpro-review-1"
LABELLED = (
    "G2 public filtered 4-5-star review metric or word metric candidate: - Single source of truth: "
    "Quoting, scheduling, job costing, purchasing, invoicing, and asset management all sit in one system, "
    "reducing duplication and errors."
)
QUOTE = (
    "Single source of truth: Quoting, scheduling, job costing, purchasing, invoicing, and asset management "
    "all sit in one system, reducing duplication and errors."
)


def _bom():
    return with_proof(kind="quote", text=LABELLED, url=URL, use_mode="exact_quote")


def test_quoted_passage_inside_the_labelled_approved_text_counts_as_used():
    text = plain() + f'One user put it this way: "{QUOTE}" ([G2 review]({URL})).\n'
    assert blocks(cov(text, _bom()), "coverage_proof") == []


def test_a_short_fragment_of_the_approved_text_does_not_count():
    text = plain() + f'One user said "Single source of truth" ([G2 review]({URL})).\n'
    assert len(blocks(cov(text, _bom()), "coverage_proof")) == 1


def test_quoting_the_vault_label_does_not_count():
    label = "G2 public filtered 4-5-star review metric or word metric candidate"
    text = plain() + f'One user said "{label}" ([G2 review]({URL})).\n'
    assert len(blocks(cov(text, _bom()), "coverage_proof")) == 1
    text = plain() + f'One user said "{LABELLED}" ([G2 review]({URL})).\n'
    assert len(blocks(cov(text, _bom()), "coverage_proof")) == 1


def test_a_single_quoted_passage_counts_like_a_double_quoted_one():
    text = plain() + f"One user put it this way: '{QUOTE}' ([G2 review]({URL})).\n"
    assert blocks(cov(text, _bom()), "coverage_proof") == []


def test_an_unquoted_paraphrase_does_not_count_for_a_quote_item():
    text = plain() + f"Users like having one system for quoting and invoicing ([G2 review]({URL})).\n"
    assert len(blocks(cov(text, _bom()), "coverage_proof")) == 1
