import dataclasses

import pytest
import requests
from data_sources.modules.production import truth
from data_sources.modules.production.truth import Finding
from tests.production_bom_support import FACT_URL, response
from tests.production_truth_support import (
    VERIFIED_AT,
    article,
    blocks,
    bom,
    check_truth_for,
    transport,
    warns,
    with_facts,
)

OTHER = "https://other.example.com/study"
CLAIM = "According to the report, 24,000 businesses use [tools]({url}) every day.\n\n"


def run(text, value=None, tr=None):
    return check_truth_for(text, value, tr)


def test_finding_is_frozen_record():
    finding = Finding("lint", "warn", "message", 3)
    assert (finding.check, finding.severity, finding.message, finding.line) == ("lint", "warn", "message", 3)
    with pytest.raises(dataclasses.FrozenInstanceError):
        finding.check = "x"  # type: ignore[misc]


def test_clean_compliant_article_has_no_blocks():
    assert blocks(run(article())) == []


def test_numeric_claim_citing_url_outside_bom_blocks_with_line_and_claim():
    text = article(CLAIM.format(url=OTHER))
    found = blocks(run(text, tr=transport(**{OTHER: response(OTHER, 200)})), "citation_source")
    assert len(found) == 1
    assert "claim cites a source outside the production BOM" in found[0].message
    assert "24,000 businesses" in found[0].message
    assert found[0].line == 15


def test_numeric_claim_with_no_link_blocks_on_the_number_and_only_warns_on_the_keyword_rule():
    findings = run(article("Reports show 24,000 businesses use it every day.\n\n"))
    assert blocks(findings, "citation_source") == []
    assert len(blocks(findings, "claim_numbers")) == 1
    assert warns(findings, "citation_source")


def test_url_only_in_bom_links_is_not_an_unverified_source_but_does_not_support_the_number():
    value = bom()
    value["links"].append({"url": OTHER, "anchor": "study", "kind": "external", "priority": "should"})
    findings = run(article(CLAIM.format(url=OTHER)), value, transport(**{OTHER: response(OTHER, 200)}))
    assert blocks(findings, "citation_source") == []
    assert len(blocks(findings, "claim_numbers")) == 1


def test_claim_citing_a_bom_proof_url_is_an_accepted_source():
    value = bom()
    value["proof"][0]["url"] = OTHER
    value["proof"][0]["text"] = "Customers report 24,000 businesses use it every day."
    findings = run(article(CLAIM.format(url=OTHER)), value, transport(**{OTHER: response(OTHER, 200)}))
    assert blocks(findings, "citation_source") == []
    assert blocks(findings, "claim_numbers") == []


def test_cited_fact_whose_page_lost_the_quote_blocks_naming_fact_and_url():
    changed = response(FACT_URL, 200, "<html><body><p>Nothing relevant here today.</p></body></html>")
    found = blocks(run(article(), tr=transport(**{FACT_URL: changed})), "fact_quote")
    assert len(found) == 1
    assert "f1" in found[0].message and FACT_URL in found[0].message


@pytest.mark.parametrize("status", [404, 410])
def test_cited_fact_on_a_gone_page_blocks(status):
    found = blocks(run(article(), tr=transport(**{FACT_URL: response(FACT_URL, status)})), "fact_quote")
    assert len(found) == 1 and "f1" in found[0].message and FACT_URL in found[0].message


@pytest.mark.parametrize("reply", [response(FACT_URL, 403), requests.Timeout("slow")])
def test_unreachable_fact_page_warns_with_verified_at_and_never_blocks(reply):
    findings = run(article(), tr=transport(**{FACT_URL: reply}))
    assert blocks(findings) == []
    assert warns(findings, "link_resolution")
    found = warns(findings, "fact_quote")
    assert len(found) == 1
    assert "f1" in found[0].message and FACT_URL in found[0].message and VERIFIED_AT in found[0].message


def _extra_fact(fact_id, url, quote):
    return {"id": fact_id, "claim": "c", "url": url, "quote": quote, "priority": "should",
            "verified_at": VERIFIED_AT, "check_detail": "d", "support": "quote_overlap"}


def test_fact_not_cited_by_the_article_is_not_fetched():
    unused = "https://example.org/unused"
    tr = transport(**{unused: response(unused, 200, "unused quote text")})
    run(article(), with_facts([_extra_fact("f2", unused, "unused quote text")]), tr)
    assert all(unused not in call for call in tr.calls)


def test_verify_quotes_runs_once_for_many_cited_facts(monkeypatch):
    urls = [f"https://example.org/page{n}" for n in range(3)]
    quotes = [f"Over 4{n},000 businesses use the product" for n in range(3)]
    extra = [_extra_fact(f"x{n}", url, quotes[n]) for n, url in enumerate(urls)]
    body = "".join(f"Over 4{n},000 businesses use [it]({url}) daily.\n\n" for n, url in enumerate(urls))
    tr = transport(**{url: response(url, 200, quotes[n]) for n, url in enumerate(urls)})
    calls = []
    real = truth.verify_quotes
    monkeypatch.setattr(truth, "verify_quotes", lambda pairs, **kw: calls.append(list(pairs)) or real(pairs, **kw))
    run(article(body), with_facts(extra), tr)
    assert len(calls) == 1
    assert {url for url, _ in calls[0]} >= set(urls) | {FACT_URL}


def test_url_validator_runs_once_on_the_shared_transport(monkeypatch):
    tr = transport()
    seen = []
    real = truth.validate_content_urls

    def spy(content, validator=None, **kw):
        seen.append(validator.transport)
        return real(content, validator=validator, **kw)

    monkeypatch.setattr(truth, "validate_content_urls", spy)
    run(article(), tr=tr)
    assert seen == [tr]


def test_claim_number_missing_from_the_cited_quote_blocks_listing_it():
    found = blocks(run(article(CLAIM.format(url=FACT_URL).replace("24,000", "25,000"))), "claim_numbers")
    assert len(found) == 1
    assert "25000" in found[0].message and "24000" not in found[0].message


def test_24k_in_the_claim_matches_24_000_in_the_quote():
    findings = run(article(CLAIM.format(url=FACT_URL).replace("24,000", "24k")))
    assert blocks(findings) == []


def test_claim_numbers_use_the_same_small_integer_exemption_as_the_global_gate():
    ok = article(f"According to the report, 24,000 businesses in 4 states use [tools]({FACT_URL}) daily.\n\n")
    assert blocks(run(ok)) == []
    bad = article(f"According to the report, 24,000 businesses in 40% of states use [tools]({FACT_URL}) daily.\n\n")
    assert len(blocks(run(bad), "claim_numbers")) == 1


def test_unresolved_link_blocks_with_line():
    text = article(f"Read [more]({OTHER}) later.\n\n")
    found = blocks(run(text, tr=transport(**{OTHER: response(OTHER, 404)})), "link_resolution")
    assert len(found) == 1 and OTHER in found[0].message and found[0].line == 15


def test_off_bom_resolving_link_warns_but_bom_links_do_not():
    text = article(f"Read [more]({OTHER}) later.\n\n")
    findings = run(text, tr=transport(**{OTHER: response(OTHER, 200)}))
    off = warns(findings, "link_off_bom")
    assert len(off) == 1 and OTHER in off[0].message
    assert blocks(findings) == []


def test_cta_and_pillar_links_are_on_the_bom():
    assert warns(run(article()), "link_off_bom") == []


def test_editorial_process_leakage_blocks_and_other_lint_warns():
    leak = run(article("This article explains how the tool works.\n\n"))
    assert [f.severity for f in leak if f.check == "lint" and "editorial_process_leakage" in f.message] == ["block"]
    dash = run(article("Pick a tool — any tool.\n\n"))
    assert blocks(dash, "lint") == []
    assert [f.severity for f in dash if f.check == "lint" and "em_dash" in f.message] == ["warn"]


def test_check_names_are_the_documented_set():
    text = article("This article explains 40% more.\n\n" + f"[bad]({OTHER})\n\n")
    findings = run(text, tr=transport(**{OTHER: response(OTHER, 404)}))
    assert {f.check for f in findings} <= {
        "citation_source", "fact_quote", "claim_numbers", "number_gate", "quoted_passage",
        "faq_question", "link_resolution", "link_off_bom", "lint"}
    assert {f.severity for f in findings} <= {"block", "warn"}


def test_missing_verified_at_is_reported_as_unknown():
    value = bom()
    del value["facts"][0]["verified_at"]
    found = warns(run(article(), value, transport(**{FACT_URL: response(FACT_URL, 403)})), "fact_quote")
    assert len(found) == 1 and "verification date unknown" in found[0].message


def test_gone_fact_page_still_blocks_both_the_fact_and_the_link():
    findings = run(article(), tr=transport(**{FACT_URL: response(FACT_URL, 404)}))
    assert blocks(findings, "fact_quote") and blocks(findings, "link_resolution")
