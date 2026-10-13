import pytest
from tests.production_truth_support import CUSTOMER_QUOTE, article, blocks, check_truth_for

FAKE = "invoicing became painless and our crews love every minute"
PLACEHOLDER = (
    '[IMAGE PLACEHOLDER | source: Simpro library | alt: "A busy crew inspecting the whole job site today" '
    "| render target: 1200x630 | resize and compress to 80 kb]"
)


def quoted(text):
    return blocks(check_truth_for(text), "quoted_passage")


@pytest.mark.parametrize("wrapped", [
    f'"{FAKE}"', f"“{FAKE}”", f"'{FAKE}'", f"‘{FAKE}’", f"«{FAKE}»",
    f"„{FAKE}“", f"‚{FAKE}‘",
])
def test_every_quote_style_blocks_a_fabricated_quote(wrapped):
    found = quoted(article(f"The owner replied {wrapped} after switching.\n\n"))
    assert len(found) == 1 and found[0].line == 15, wrapped


def test_apostrophes_and_possessives_do_not_start_a_quote():
    text = article("The crews' schedules don’t clash and the owner's view is that it's fine to wait.\n\n")
    assert quoted(text) == []


def test_two_word_quote_blocks_when_the_sentence_has_an_attribution_cue():
    assert quoted(article('Acme said "Simpro saved us" last week.\n\n'))
    assert quoted(article('Per the owner, "Simpro saved us" last week.\n\n')) == []
    assert quoted(article('Then Acme Electrical called it "pure gold" in a review.\n\n'))
    assert quoted(article('It helps crews "stay on time" — always.\n\n'))
    assert quoted(article('According to the owner, "never again" will it slip.\n\n'))


def test_media_placeholder_lines_are_exempt_from_the_quote_check():
    assert quoted(article(PLACEHOLDER + "\n\n")) == []


def test_trailing_attribution_is_stripped_before_matching():
    assert quoted(article(f"> {CUSTOMER_QUOTE} — Jane, Acme Electrical\n\n")) == []
    assert quoted(article(f"> {CUSTOMER_QUOTE}\n> — Jane, Acme Electrical\n\n")) == []
    assert quoted(article(f"> {CUSTOMER_QUOTE} - Jane, Acme Electrical\n\n")) == []
    assert quoted(article(f'"{CUSTOMER_QUOTE}" – Jane, Acme Electrical\n\n')) == []
    assert quoted(article(f"> {FAKE} — Jane\n\n"))


def test_blockquote_cannot_splice_two_bom_sources():
    spliced = f"> {CUSTOMER_QUOTE}\n> Trusted by more than 24,000 trade businesses worldwide\n\n"
    assert quoted(article(spliced))


def test_elided_quote_needs_every_fragment_in_the_same_source():
    assert quoted(article('One owner said "invoicing went from a weekly chore … a same-day task" often.\n\n')) == []
    assert quoted(article('One owner said "invoicing went from a weekly chore ... a same-day task" often.\n\n')) == []
    cross = 'One owner said "invoicing went from a weekly chore … more than 24,000 trade businesses" often.\n\n'
    assert quoted(article(cross))


def test_html_quote_elements_are_public_copy():
    assert quoted(article("<q>made up praise for the whole team</q>\n\n"))
    assert quoted(article("<blockquote>made up praise</blockquote>\n\n"))
    assert quoted(article(f"<blockquote>{CUSTOMER_QUOTE}</blockquote>\n\n")) == []


def test_footnotes_and_html_alt_text_are_public_copy_for_numbers():
    assert blocks(check_truth_for(article("Crews log time.[^1]\n\n[^1]: Over 77 firms agree.\n\n")), "number_gate")
    assert blocks(check_truth_for(article('<img src="a.png" alt="Chart of 88 crews">\n\n')), "number_gate")
    assert blocks(check_truth_for(article('<img src="a.png" alt="Chart of crews">\n\n[^1]: ok text\n\n')), "number_gate") == []
