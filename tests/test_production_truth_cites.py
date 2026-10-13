from types import SimpleNamespace

import pytest

from data_sources.modules.production import truth
from data_sources.modules.proof_link_policy import CitationRequirement
from tests.production_bom_support import FACT_URL, response
from tests.production_truth_support import PROOF_URL, article, blocks, check_truth_for, transport, warns

OTHER = "https://other.example.com/study"


def run(text, value=None, tr=None):
    return check_truth_for(text, value, tr)


def test_c1_number_that_only_an_unrelated_proof_contains_blocks_and_names_that_proof():
    text = article(f"Simpro cuts invoicing time by 30% for crews, per [the report]({FACT_URL}).\n\n")
    found = blocks(run(text), "claim_numbers")
    assert len(found) == 1
    assert "30" in found[0].message and "p1" in found[0].message and found[0].line == 15


def test_c1_unlinked_number_blocks():
    assert blocks(run(article("Simpro cuts invoicing time by 30% for crews.\n\n")), "claim_numbers")


def test_true_claim_citing_the_right_proof_passes():
    text = article(f"Acme saw 30% faster invoicing, per [Acme's story]({PROOF_URL}).\n\n")
    assert blocks(run(text)) == []


def test_number_linked_to_the_wrong_bom_source_blocks():
    text = article(f"Acme saw 30% faster invoicing, per [the report]({FACT_URL}).\n\n")
    assert len(blocks(run(text), "claim_numbers")) == 1


def test_owned_domain_citation_counts_as_a_cited_bom_source():
    text = article(f"Acme saved 30% on invoicing, per [Acme's story]({PROOF_URL}).\n\n")
    findings = run(text)
    assert blocks(findings, "claim_numbers") == [] and blocks(findings, "citation_source") == []


def test_list_items_and_table_rows_are_their_own_paragraphs():
    items = f"- Acme saw 30% faster invoicing, per [story]({PROOF_URL})\n- Crews gain 30% more time\n\n"
    assert len(blocks(run(article(items)), "claim_numbers")) == 1
    rows = f"| Metric | Source |\n|---|---|\n| 30% faster | [story]({PROOF_URL}) |\n| 31% faster | none |\n\n"
    found = blocks(run(article(rows)), "claim_numbers")
    assert len(found) == 1 and "31" in found[0].message


def test_faq_answer_is_one_paragraph_for_the_number_rule():
    answer = f"It helps crews.\n\nAcme saw 30% faster invoicing, per [story]({PROOF_URL}).\n"
    findings = run(article(faq=answer, faq_section=f"### What is field service software?\n\n{answer}"))
    assert blocks(findings, "claim_numbers") == []


def test_keyword_only_claim_without_a_number_only_warns():
    findings = run(article("Better scheduling helps crews finish sooner.\n\n"))
    assert blocks(findings) == []
    assert warns(findings, "citation_source")


def test_evidence_url_outside_the_bom_blocks_the_citation():
    text = article(f"Better scheduling helps crews finish sooner, per [a study]({OTHER}).\n\n")
    found = blocks(run(text, tr=transport(**{OTHER: response(OTHER, 200)})), "citation_source")
    assert len(found) == 1 and "claim cites a source outside the production BOM" in found[0].message


def _customer_report(monkeypatch, line_range=(15, 15)):
    requirement = CitationRequirement(
        mode="inline_required", owner="customer_proof", reason="r", line=line_range[0], end_line=line_range[1],
        section="s", claim="Acme loves it", approved_urls=(), visible_urls=(),
    )
    monkeypatch.setattr(truth, "analyze_proof_links",
                        lambda *a, **k: SimpleNamespace(requirements=(requirement,), links=()))


def test_customer_proof_requirement_needs_a_linked_bom_proof_url(monkeypatch):
    _customer_report(monkeypatch)
    found = blocks(run(article("Acme loves it.\n\n")), "citation_source")
    assert len(found) == 1 and "production BOM" in found[0].message


def test_customer_proof_requirement_passes_with_the_proof_url_linked(monkeypatch):
    _customer_report(monkeypatch)
    assert blocks(run(article(f"Acme loves [it]({PROOF_URL}).\n\n")), "citation_source") == []



@pytest.mark.parametrize("url", [
    "https://www.simprogroup.com/case-studies/foster",
    "https://www.simprogroup.com/customers/foster",
    "https://www.simprogroup.com/customer-stories/foster",
    "https://www.simprogroup.com/testimonials/foster",
    "https://www.simprogroup.com/success-stories/foster",
    "https://www.g2.com/products/simpro/reviews",
    "https://www.capterra.com/p/1234/simpro/",
    "https://www.trustpilot.com/review/simprogroup.com",
    "https://www.getapp.com/x/simpro",
    "https://www.softwareadvice.com/x/simpro",
])
def test_customer_story_link_without_a_bom_proof_blocks_without_any_monkeypatch(url):
    text = article(f"A [Foster Plumbing case study]({url}) shows the contractor scaled.\n\n")
    found = blocks(run(text, tr=transport(**{url: response(url, 200)})), "citation_source")
    assert len(found) == 1 and url.rstrip("/") in found[0].message and found[0].line == 15


def test_customer_story_link_that_is_a_bom_proof_passes():
    text = article(f"A [Acme case study]({PROOF_URL}) shows the contractor scaled.\n\n")
    assert blocks(run(text), "citation_source") == []


def test_heading_number_needs_a_linked_source_in_the_heading_or_the_next_unit():
    assert len(blocks(run(article("## Simpro cuts fuel costs 30%\n\n")), "claim_numbers")) == 1
    linked = article(f"## Simpro cuts fuel costs 30%\n\nAcme's [story]({PROOF_URL}) covers it.\n\n")
    assert blocks(run(linked)) == []
    in_heading = article(f"## Simpro cuts fuel costs 30% ([story]({PROOF_URL}))\n\nMore detail follows.\n\n")
    assert blocks(run(in_heading)) == []


def test_heading_next_unit_skips_following_headings_and_ignores_later_paragraphs():
    later = article(f"## Simpro cuts fuel costs 30%\n\nNothing linked here.\n\nAcme's [story]({PROOF_URL}) covers it.\n\n")
    assert len(blocks(run(later), "claim_numbers")) == 1


def test_title_and_meta_numbers_need_a_supporting_source_linked_in_the_body():
    assert len(blocks(run(article(title="Cut fuel costs 30% with Simpro")), "claim_numbers")) == 1
    assert len(blocks(run(article(description="Cut fuel costs 30% today")), "claim_numbers")) == 1
    assert len(blocks(run(article(extra_front='meta_title: "Cut costs 30%"\n')), "claim_numbers")) == 1
    body = f"Acme's [story]({PROOF_URL}) covers it.\n\n"
    assert blocks(run(article(body, title="Cut fuel costs 30% with Simpro"))) == []


def test_links_hidden_in_comments_or_code_are_not_citations():
    hidden = f"Simpro cuts fuel costs by 30%. <!-- [x]({PROOF_URL}) -->\n\n"
    assert len(blocks(run(article(hidden)), "claim_numbers")) == 1
    code = f"Simpro cuts fuel costs by 30%. `[x]({PROOF_URL})`\n\n"
    assert len(blocks(run(article(code)), "claim_numbers")) == 1
    fenced = f"Simpro cuts fuel costs by 30%.\n\n```\n[x]({PROOF_URL})\n```\n\n"
    assert len(blocks(run(article(fenced)), "claim_numbers")) == 1


def test_links_inside_double_backtick_spans_are_not_citations():
    text = article(f"Simpro cuts fuel costs by 30%. ``[x]({PROOF_URL})``\n\n")
    assert len(blocks(run(text), "claim_numbers")) == 1
