import pytest
from tests.production_truth_support import CUSTOMER_QUOTE, article, blocks, bom, check_truth_for

FAKE = "invoicing became painless and our crews love every minute"
PLACEHOLDER = (
    '[IMAGE PLACEHOLDER | source: Simpro library | alt: "A busy crew inspecting the whole job site today" '
    "| render target: 1200x630 | resize and compress to 80 kb]"
)


def quoted(text, value=None):
    return blocks(check_truth_for(text, value), "quoted_passage")


@pytest.mark.parametrize("wrapped", [
    f'"{FAKE}"', f"“{FAKE}”", f"'{FAKE}'", f"‘{FAKE}’", f"«{FAKE}»",
    f"„{FAKE}“", f"‚{FAKE}‘",
])
def test_every_quote_style_blocks_a_fabricated_quote(wrapped):
    found = quoted(article(f"The owner said {wrapped} after switching.\n\n"))
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
    assert quoted(article("She said <q>made up praise for the whole team</q> today.\n\n"))
    assert quoted(article("<blockquote>made up praise</blockquote>\n\n"))
    assert quoted(article(f"<blockquote>{CUSTOMER_QUOTE}</blockquote>\n\n")) == []


def test_footnotes_and_html_alt_text_are_public_copy_for_numbers():
    assert blocks(check_truth_for(article("Crews log time.[^1]\n\n[^1]: Over 77 firms agree.\n\n")), "number_gate")
    assert blocks(check_truth_for(article('<img src="a.png" alt="Chart of 88 crews">\n\n')), "number_gate")
    assert blocks(check_truth_for(article('<img src="a.png" alt="Chart of crews">\n\n[^1]: ok text\n\n')), "number_gate") == []


def test_unattributed_inline_quote_only_warns():
    findings = check_truth_for(article(f'Search for "{FAKE}" to see results.\n\n'))
    assert [f.severity for f in findings if f.check == "quoted_passage"] == ["warn"]


def test_attributed_quotes_and_blockquotes_still_block():
    assert quoted(article(f'The owner said "{FAKE}" last week.\n\n'))
    assert quoted(article(f'Our crews love it \u2014 "{FAKE}".\n\n'))
    assert quoted(article(f'Acme Electrical called it "{FAKE}" in a review.\n\n'))
    assert quoted(article(f"> {FAKE}\n\n"))


@pytest.mark.parametrize("line", [
    '[CMS MODULE PLACEHOLDER | source: modules/cta | alt: "A busy crew inspecting the whole job site today"]',
    '> **Hero image placeholder:** "A busy crew inspecting the whole job site today" 1200x630',
    '> **Video placeholder:** "A busy crew inspecting the whole job site today" 1200x630',
    '[VIDEO PLACEHOLDER | source: yt | title: "A busy crew inspecting the whole job site today"]',
])
def test_media_and_cms_placeholders_are_exempt_from_the_quote_and_number_checks(line):
    findings = check_truth_for(article(f"{line}\n\n"))
    assert [f for f in findings if f.check in ("quoted_passage", "number_gate") and f.severity == "block"] == []


@pytest.mark.parametrize("line", ["> **Key takeaways**\n> Crews who log time catch more hours.",
                                  "> **Tip:** book the demo before the busy season starts"])
def test_bold_label_callouts_skip_only_the_quote_check(line):
    findings = check_truth_for(article(f"{line}\n\n"))
    assert [f for f in findings if f.check == "quoted_passage"] == []
    numbered = check_truth_for(article("> **Tip:** save 83% of admin time\n\n"))
    assert [f for f in numbered if f.check == "number_gate" and f.severity == "block"]


def test_a_bold_label_does_not_launder_a_fabricated_testimonial():
    assert quoted(article(f'> **"{FAKE}"** \u2014 Jane\n\n'))


def test_curly_apostrophes_match_straight_ones_in_the_source():
    value = bom()
    value["proof"][0]["approved_quotes"].append({"quote": "it's the best tool we've used on the job"})
    curly = "it\u2019s the best tool we\u2019ve used on the job"
    assert quoted(article(f"> {curly}\n\n"), value) == []
    assert quoted(article(f'The owner said "{curly}" often.\n\n'), value) == []
