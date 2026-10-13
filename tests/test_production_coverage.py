"""Coverage checks: the finished article delivers what the production BOM marked must or should."""

from __future__ import annotations

import copy
from typing import Any

from data_sources.modules.production.coverage import check_coverage
from data_sources.modules.production.serp_coverage import heading_tokens
from tests.production_bom_support import FACT_URL, PAA_QUESTION, PILLAR_URL
from tests.production_truth_support import CUSTOMER_QUOTE, PROOF_URL, article, blocks, bom, warns

KEYWORD = "field service software"
OTHER_URL = "https://www.simprogroup.com/blog/other"
THEME_URL = "https://www.simprogroup.com/customers/theme-story"
HOW_TO = "How to choose field service software"
PROOF_PARAGRAPH = (
    f"Acme Electrical saw [30% faster invoicing]({PROOF_URL}) after the switch to field service software.\n\n"
)
BODY = (
    f"## {HOW_TO.upper()}!\n\nPick the tool your crews will open every day. Read the "
    f"[other post]({OTHER_URL}) for a deeper comparison.\n\n" + PROOF_PARAGRAPH
)


def full_bom() -> dict[str, Any]:
    value = bom()
    value["keyword"] = {"primary": KEYWORD, "secondary": []}
    value["sections"] = [
        {"heading": "What it is", "purpose": "define the category", "priority": "must"},
        {"heading": HOW_TO, "purpose": "help the reader choose", "priority": "should"},
    ]
    value["links"][1]["url"] = OTHER_URL
    return value


def empty_bom(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "identity": {"brand": "Simpro", "date": "2026-10-13"}, "keyword": {"primary": KEYWORD},
        "sections": [], "facts": [], "proof": [], "paa": {"questions": []}, "links": [],
    }
    value.update(overrides)
    return value


def compliant() -> str:
    return article(BODY)


def cov(text: str, value: dict[str, Any] | None = None) -> list[Any]:
    return check_coverage(text, value if value is not None else full_bom())


def plain(*, title: str = "Field Service Software Guide", h1: str = "Field Service Software Guide",
          lead: str = "Field service software runs the day.") -> str:
    return f'---\ntitle: "{title}"\n---\n\n# {h1}\n\n{lead}\n\n'


def with_proof(**fields: Any) -> dict[str, Any]:
    value = empty_bom()
    value["proof"] = [{"id": "pr1", "claim_id": "c1", "kind": "theme", "priority": "must",
                       "text": "Crews stopped chasing paperwork.", "url": THEME_URL, **fields}]
    return value


def test_fully_compliant_article_has_no_findings():
    assert cov(compliant()) == []


def test_missing_must_section_blocks_and_names_the_heading():
    value = full_bom()
    value["sections"].append({"heading": "Pricing and ROI", "purpose": "cost", "priority": "must"})
    found = blocks(cov(compliant(), value), "coverage_section")
    assert len(found) == 1 and "Pricing and ROI" in found[0].message


def test_missing_should_section_warns_instead_of_blocking():
    value = full_bom()
    value["sections"].append({"heading": "Integrations", "purpose": "fit", "priority": "should"})
    found = cov(compliant(), value)
    assert blocks(found) == []
    assert len(warns(found, "coverage_section")) == 1 and "Integrations" in warns(found)[0].message


def test_heading_with_other_case_and_punctuation_still_matches():
    assert blocks(cov(compliant()), "coverage_section") == [] and warns(cov(compliant())) == []


def test_h3_heading_counts_as_a_section():
    text = article("### What's in it?\n\nStuff.\n\n")
    value = empty_bom(sections=[{"heading": "Whats in it", "purpose": "x", "priority": "must"}])
    assert cov(text, value) == []


def test_section_matches_when_one_heading_holds_every_content_token():
    text = article("## Pricing, costs and the ROI of the whole thing\n\nNumbers.\n\n")
    value = empty_bom(sections=[{"heading": "Pricing and ROI", "purpose": "x", "priority": "must"}])
    assert cov(text, value) == []


def test_section_with_only_some_tokens_in_a_heading_does_not_match():
    text = article("## Pricing for everyone\n\nNumbers.\n\n")
    value = empty_bom(sections=[{"heading": "Pricing and ROI", "purpose": "x", "priority": "must"}])
    assert len(blocks(cov(text, value), "coverage_section")) == 1


def test_section_heading_in_a_comment_or_code_does_not_count():
    text = article("<!--\n## Pricing and ROI\n-->\n\n```\n## Pricing and ROI\n```\n\n")
    value = empty_bom(sections=[{"heading": "Pricing and ROI", "purpose": "x", "priority": "must"}])
    assert len(blocks(cov(text, value), "coverage_section")) == 1


def test_unlinked_must_fact_blocks_and_names_the_fact_id():
    text = compliant().replace(FACT_URL, OTHER_URL)
    found = blocks(cov(text), "coverage_fact")
    assert len(found) == 1 and "f1" in found[0].message and FACT_URL in found[0].message


def test_unlinked_should_fact_warns():
    value = full_bom()
    value["facts"][0]["priority"] = "should"
    found = cov(compliant().replace(FACT_URL, OTHER_URL), value)
    assert blocks(found, "coverage_fact") == [] and len(warns(found, "coverage_fact")) == 1


def test_fact_link_hidden_in_a_comment_or_code_does_not_count():
    hidden = f"<!-- [x]({FACT_URL}) -->\n\n`[y]({FACT_URL})`\n\n```\n[z]({FACT_URL})\n```"
    text = plain(lead=hidden)
    value = empty_bom(facts=full_bom()["facts"])
    assert len(blocks(cov(text, value), "coverage_fact")) == 1


def test_fact_url_variants_match_by_canonical_url():
    text = article().replace(FACT_URL, FACT_URL + "/?utm_source=x#top")
    assert blocks(cov(text), "coverage_fact") == []


def test_unlinked_must_proof_blocks_and_names_the_proof_id():
    value = full_bom()
    value["proof"][0]["priority"] = "must"
    found = blocks(cov(compliant().replace(PROOF_URL, OTHER_URL), value), "coverage_proof")
    assert len(found) == 1 and "p1" in found[0].message


def test_unlinked_should_proof_warns():
    found = cov(compliant().replace(PROOF_URL, OTHER_URL))
    assert blocks(found) == [] and len(warns(found, "coverage_proof")) == 1


def test_paraphrased_theme_proof_passes_with_only_its_link():
    text = article(f"Crews said they [stopped chasing paperwork]({THEME_URL}) once jobs were digital.\n\n")
    assert blocks(cov(text, with_proof()), "coverage_proof") == []
    assert blocks(cov(text, with_proof(kind="experience_story")), "coverage_proof") == []


def test_theme_proof_without_its_link_blocks():
    assert len(blocks(cov(article(), with_proof()), "coverage_proof")) == 1


def test_quote_proof_with_link_but_no_verbatim_text_blocks():
    text = article(f"A customer [spoke well of it]({PROOF_URL}).\n\n")
    value = with_proof(kind="quote", url=PROOF_URL, approved_quotes=[{"quote": CUSTOMER_QUOTE, "status": "approved"}])
    found = blocks(cov(text, value), "coverage_proof")
    assert len(found) == 1 and "pr1" in found[0].message and "quote" in found[0].message


def test_quote_proof_passes_with_the_approved_quote_verbatim_in_any_case_and_style():
    quote = CUSTOMER_QUOTE.upper()
    text = article(f"The owner said, “{quote},” in [her review]({PROOF_URL}).\n\n")
    value = with_proof(kind="quote", url=PROOF_URL, approved_quotes=[{"quote": CUSTOMER_QUOTE, "status": "approved"}])
    assert blocks(cov(text, value), "coverage_proof") == []


def test_connector_quote_proof_uses_its_text_when_no_approved_quote_exists():
    text = article(f'One owner said "{CUSTOMER_QUOTE}" ([source]({PROOF_URL})).\n\n')
    value = with_proof(kind="quote", url=PROOF_URL, text=CUSTOMER_QUOTE)
    assert blocks(cov(text, value), "coverage_proof") == []
    assert len(blocks(cov(article(f"[x]({PROOF_URL})\n\n"), value), "coverage_proof")) == 1


def test_metric_proof_needs_a_proof_number_in_the_paragraph_that_links_it():
    value = with_proof(kind="metric", url=PROOF_URL, text="Customers report 30% faster invoicing.")
    good = article(f"Invoices went out [30% sooner]({PROOF_URL}) for them.\n\n")
    assert blocks(cov(good, value), "coverage_proof") == []
    wrong = article(f"Invoices went out [sooner]({PROOF_URL}) for them.\n\nOther teams saw 30% gains.\n\n")
    found = blocks(cov(wrong, value), "coverage_proof")
    assert len(found) == 1 and "pr1" in found[0].message and "number" in found[0].message


def test_must_paa_question_missing_from_the_faq_blocks():
    value = full_bom()
    value["paa"]["questions"][0]["priority"] = "must"
    text = compliant().replace(PAA_QUESTION, "Why is the sky blue?")
    found = blocks(cov(text, value), "coverage_paa")
    assert len(found) == 1 and PAA_QUESTION in found[0].message


def test_should_paa_question_missing_warns():
    found = cov(compliant().replace(PAA_QUESTION, "Why is the sky blue?"))
    assert blocks(found) == [] and len(warns(found, "coverage_paa")) == 1


def test_paa_question_matches_ignoring_case_and_punctuation():
    value = full_bom()
    value["paa"]["questions"][0]["priority"] = "must"
    text = compliant().replace(PAA_QUESTION, "WHAT is field-service software?")
    assert blocks(cov(text, value), "coverage_paa") == []


def test_missing_commercial_pillar_url_blocks():
    found = blocks(cov(compliant().replace(PILLAR_URL, OTHER_URL)), "coverage_pillar")
    assert len(found) == 1 and "commercial pillar link missing" in found[0].message and PILLAR_URL in found[0].message


def test_commercial_pillar_with_a_different_anchor_blocks_quoting_both_anchors():
    found = blocks(cov(compliant().replace("[field service management software]", "[our platform]")), "coverage_pillar")
    assert len(found) == 1 and "commercial pillar anchor differs" in found[0].message
    assert "our platform" in found[0].message and "field service management software" in found[0].message


def test_pillar_anchor_with_bold_markup_or_entities_or_case_passes():
    for anchor in ("**field service management software**", "Field Service Management Software.", "field  service\tmanagement software"):
        assert blocks(cov(compliant().replace("field service management software]", anchor + "]")), "coverage_pillar") == [], anchor
    value = full_bom()
    value["links"][0]["anchor"] = "field service & management software"
    text = compliant().replace("[field service management software]", "[field service &amp; management software]")
    assert blocks(cov(text, value), "coverage_pillar") == []


def test_one_exact_pillar_anchor_is_enough_when_other_variants_exist():
    text = compliant() + f"\nMore on [our platform]({PILLAR_URL}).\n"
    assert blocks(cov(text), "coverage_pillar") == []


def test_pillar_link_hidden_in_a_comment_does_not_count():
    text = compliant().replace(f"[field service management software]({PILLAR_URL})", f"<!-- [field service management software]({PILLAR_URL}) -->")
    assert len(blocks(cov(text), "coverage_pillar")) == 1


def test_other_must_link_absent_blocks_and_should_link_warns():
    value = full_bom()
    value["links"][1]["priority"] = "must"
    text = compliant().replace(OTHER_URL, "https://www.simprogroup.com/blog/elsewhere")
    found = blocks(cov(text, value), "coverage_link")
    assert len(found) == 1 and OTHER_URL in found[0].message
    soft = cov(text)
    assert blocks(soft) == [] and len(warns(soft, "coverage_link")) == 1


def test_keyword_missing_from_the_title_blocks():
    found = blocks(cov(plain(title="A Short Guide"), empty_bom()), "coverage_keyword")
    assert len(found) == 1 and "title" in found[0].message and KEYWORD in found[0].message


def test_keyword_missing_from_the_h1_blocks():
    found = blocks(cov(plain(h1="A Short Guide"), empty_bom()), "coverage_keyword")
    assert len(found) == 1 and "H1" in found[0].message


def test_keyword_missing_from_the_first_100_words_blocks():
    found = blocks(cov(plain(lead="The day runs itself."), empty_bom()), "coverage_keyword")
    assert len(found) == 1 and "first 100 words" in found[0].message


def test_keyword_must_sit_inside_the_first_100_words():
    def lead(filler: int) -> str:
        return " ".join(["alpha"] * filler) + " field service software helps."

    assert blocks(cov(plain(lead=lead(97)), empty_bom()), "coverage_keyword") == []
    assert len(blocks(cov(plain(lead=lead(98)), empty_bom()), "coverage_keyword")) == 1


def test_keyword_in_headings_or_comments_does_not_count_as_lead_prose():
    text = plain(lead="<!-- field service software -->\n\n## Field service software\n\nThe day runs itself.")
    assert len(blocks(cov(text, empty_bom()), "coverage_keyword")) == 1


def test_each_missing_keyword_place_is_its_own_block():
    found = blocks(cov(plain(title="x", h1="y", lead="z"), empty_bom()), "coverage_keyword")
    assert [place for place in ("title", "H1", "first 100 words") if any(place in f.message for f in found)] == [
        "title", "H1", "first 100 words"]
    assert len(found) == 3


def test_keyword_matches_as_a_contiguous_phrase_in_any_case_and_punctuation():
    text = plain(title="Field-Service Software: a guide", h1="FIELD SERVICE SOFTWARE", lead="Our field service, software.")
    assert blocks(cov(text, empty_bom()), "coverage_keyword") == []
    assert len(blocks(cov(plain(title="Software for field service"), empty_bom()), "coverage_keyword")) == 1


def test_coverage_does_not_mutate_the_bom():
    value = full_bom()
    before = copy.deepcopy(value)
    cov(compliant(), value)
    assert value == before


def sections(heading: str) -> dict[str, Any]:
    return empty_bom(sections=[{"heading": heading, "purpose": "x", "priority": "must"}])


def with_h2(heading: str) -> str:
    return article(f"## {heading}\n\nx.\n\n")


def test_heading_tokens_fold_plurals_and_drop_stopwords():
    assert heading_tokens("The FSM Software Costs and Integrations") == heading_tokens("fsm software cost integration")


def test_plural_bom_heading_matches_a_singular_article_heading_and_back():
    assert cov(with_h2("FSM software cost"), sections("FSM software costs")) == []
    assert cov(with_h2("FSM Software Costs"), sections("FSM software cost")) == []
    assert cov(with_h2("Integrations"), sections("Integration")) == []
    assert cov(with_h2("Integration"), sections("Integrations")) == []
    assert cov(with_h2("Policies"), sections("Policy")) == []


def test_plural_folding_does_not_make_different_words_match():
    assert len(blocks(cov(with_h2("FSM software costume"), sections("FSM software cost")))) == 1


def test_all_stopword_bom_heading_never_matches_an_arbitrary_heading():
    found = blocks(cov(with_h2("Anything else"), sections("How to")), "coverage_section")
    assert len(found) == 1 and "How to" in found[0].message
    assert blocks(cov(with_h2("How to"), sections("How to")), "coverage_section") == []


def test_blank_or_missing_primary_keyword_blocks_instead_of_skipping():
    for keyword in ({}, {"primary": ""}, {"primary": "   "}, None, "x"):
        value = empty_bom()
        value["keyword"] = keyword
        found = blocks(cov(plain(), value), "coverage_keyword")
        assert len(found) == 1 and "BOM keyword.primary missing" in found[0].message, keyword
    value = empty_bom()
    del value["keyword"]
    assert len(blocks(cov(plain(), value), "coverage_keyword")) == 1


def test_underscore_emphasis_and_entities_in_the_keyword_places_pass():
    assert blocks(cov(plain(lead="Start with _field service software_ today."), empty_bom()), "coverage_keyword") == []
    assert blocks(cov(plain(h1="__Field Service Software__"), empty_bom()), "coverage_keyword") == []
    value = empty_bom(keyword={"primary": "field &amp; service software"})
    text = plain(title="Field & Service Software", h1="Field &amp; Service Software", lead="Field &amp; service software wins.")
    assert blocks(cov(text, value), "coverage_keyword") == []


def test_keyword_stays_strict_about_plurals_and_word_boundaries():
    found = blocks(cov(plain(lead="Our field service softwares help."), empty_bom()), "coverage_keyword")
    assert len(found) == 1 and "first 100 words" in found[0].message
    assert len(blocks(cov(plain(title="Field Service Softwares"), empty_bom()), "coverage_keyword")) == 1


def test_fact_url_with_a_trailing_slash_or_tracking_parameter_still_matches():
    for variant in (FACT_URL + "/", FACT_URL + "?utm_source=x", FACT_URL + "/?utm_source=x"):
        assert blocks(cov(article().replace(FACT_URL, variant)), "coverage_fact") == [], variant


def test_unreferenced_reference_definition_does_not_count_as_a_citation():
    text = plain(lead=f"A claim with no link.\n\n[unused]: {FACT_URL}")
    assert len(blocks(cov(text, empty_bom(facts=full_bom()["facts"])), "coverage_fact")) == 1


def test_referenced_definition_counts_and_keeps_its_anchor():
    text = plain(lead=f"See [field service tools][ref] and [site] for more.\n\n[ref]: {FACT_URL}\n[site]: {PILLAR_URL}")
    link = {"url": PILLAR_URL, "anchor": "site", "kind": "commercial_pillar", "priority": "must"}
    value = empty_bom(facts=full_bom()["facts"], links=[link])
    assert blocks(cov(text, value), "coverage_fact") == [] and blocks(cov(text, value), "coverage_pillar") == []
    value["links"] = [{**link, "anchor": "other"}]
    assert len(blocks(cov(text, value), "coverage_pillar")) == 1


def test_footnote_definition_still_counts_as_a_citation():
    text = plain(lead=f"A claim.[^1]\n\n[^1]: Source {FACT_URL}")
    assert blocks(cov(text, empty_bom(facts=full_bom()["facts"])), "coverage_fact") == []


def test_unreadable_frontmatter_is_reported_as_such_not_as_a_missing_keyword():
    text = '---\ntitle: "unterminated\n---\n\n# Field Service Software Guide\n\nField service software runs.\n'
    found = blocks(cov(text, empty_bom()), "coverage_keyword")
    assert len(found) == 1 and "title unreadable (frontmatter error)" in found[0].message
    assert "missing from the title" not in found[0].message
