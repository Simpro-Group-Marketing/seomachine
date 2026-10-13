from types import SimpleNamespace

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

