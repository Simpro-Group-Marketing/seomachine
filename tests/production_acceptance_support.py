"""Judgment files for the production release acceptance test: a BigChange spec, captures, and a fake web.

Everything here is what a person or Claude supplies by hand (the BOM spec, the article, a saved Semrush
transcript and keyword decision, and saved research captures); the pipeline builds all the rest.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from data_sources.modules import semrush_keyword_decision_guard as guard
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.production.layout import Layout, load_or_create_run_id
from tests.production_release_support import PageTransport
from tests.production_scoring_support import (
    ARTICLE,
    OWNED_URL,
    Q1,
    Q2,
    QUERY,
    RUN_ID,
    TODAY,
    _write_evidence,
    article_text,
    write_paa_capture,
)
from tests.research_provenance_fixtures import build_serp_fixture

FACT_ID = "f1"
FACT_QUOTE = "BigChange sells field service management software for engineers and office teams"
FACT_PAGE = f"<html><body><h1>BigChange</h1><p>{FACT_QUOTE}.</p><p>Plan jobs, route engineers, and report on site work.</p></body></html>"
GENERIC_PAGE = "<html><body><p>A public reference page.</p></body></html>"
SECONDARY = ("capacity planning", "dispatch constraints")
SECTIONS = ("Start with a complete request", "Build a useful technician handoff", "Keep changes controlled")
SERP_PAGES = {
    f"https://serp{n}.example.com/field-service-scheduling": [*SECTIONS[: 3 - n % 2], f"Extra topic {n}"]
    for n in range(1, 5)
}
TRANSCRIPT_PATH = "research/semrush-transcript-scheduling.txt"
DECISION_PATH = "research/semrush-decision-input-scheduling.json"
OFF_BOM_SENTENCE = "\n[Independent studies](https://off-bom.example.net/report) show 73% of dispatch teams reopen schedules each week.\n"


def acceptance_article() -> str:
    """The compliant BigChange article with the primary keyword in its frontmatter title."""
    text = article_text().replace("title: Scheduling guide\n", "title: Field service scheduling guide\n", 1)
    return text.replace("region: US\n", "region: UK\n", 1)


def spec() -> dict[str, Any]:
    return {
        "schema": "simpro-production-bom-spec/v1", "brand": "BigChange", "market": "UK",
        "title": "Field service scheduling guide", "objective": "Help service leaders improve scheduling decisions",
        "audience": "Field service leaders",
        "sections": [{"heading": heading, "purpose": "Cover the topic", "priority": "must"} for heading in SECTIONS],
        "facts": [{"id": FACT_ID, "claim": "BigChange sells field service management software",
                   "url": OWNED_URL, "quote": FACT_QUOTE, "priority": "should"}],
        "proof": [{"id": "p1", "claim_id": "bigchange-review-capterra-owner-job-scheduling",
                   "kind": "experience_story", "priority": "must"}],
        "paa_questions": [{"question": Q1, "priority": "must"}, {"question": Q2, "priority": "should"}],
        "links": [{"url": OWNED_URL, "anchor": "BigChange field service management software",
                   "kind": "internal", "priority": "must"}],
        "cta": {"text": "Explore", "url": OWNED_URL},
        "schema_notes": ["BlogPosting", "BreadcrumbList", "ImageObject", "Organization as publisher reference",
                         "FAQPage", "Question and Answer inside FAQPage"],
        "not_applicable_context_reason": "BigChange workflow with no brand-vault signal",
    }


def _candidate(keyword: str, volume: int) -> dict[str, Any]:
    return {"keyword": keyword, "volume": volume, "keyword_difficulty": 30, "cpc": 8.5,
            "competitive_density": 0.1, "results": 500000 + volume}


def transcript() -> str:
    rows = "".join(f"{row['keyword']}\n{row['volume']}\n30\n8.5\n0.1\n{row['results']:,}\n\n"
                   for row in (_candidate(QUERY, 720), *(_candidate(word, 90) for word in SECONDARY)))
    return ("Semrush phrase_these, database uk\nKeyword Volume KD CPC Density Results\n" + rows
            + "example.com\nhttps://example.com/field-service-scheduling-guide\n")


def _report(name: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"report": name, "parameters": parameters or {}, "status": "completed"}


def keyword_decision_input() -> dict[str, Any]:
    phrase = {"phrase": QUERY, "database": "uk"}
    return {
        "brand": "BigChange", "market": "UK", "database": "uk", "collection_date": TODAY,
        "source_boundary": guard.SOURCE_BOUNDARY, "seed_terms": [QUERY, *SECONDARY],
        "connector_reports": [
            _report("_keyword_research"), _report("_get_report_schema", {"report": "phrase_these"}),
            _report("phrase_these", {"phrase": ";".join([QUERY, *SECONDARY]), "database": "uk"}),
            _report("phrase_related", phrase), _report("phrase_questions", phrase),
            _report("phrase_organic", phrase), _report("phrase_this", phrase),
        ],
        "candidate_metrics": [_candidate(QUERY, 720), *(_candidate(word, 90) for word in SECONDARY)],
        "serp_finalists": [{"keyword": QUERY, "database": "uk", "results": [{
            "position": 1, "position_type": "organic", "domain": "example.com",
            "url": "https://example.com/field-service-scheduling-guide", "triggered_serp_features": []}]}],
        "question_candidates": [], "related_candidates": [],
        "selected_primary_keyword": QUERY, "selected_secondary_keywords": list(SECONDARY),
        "rejected_keywords": [{"keyword": "employee scheduling software", "reason": "Different buyer lane."}],
        "selection_rationale": "Intent fit and SERP feasibility support the target.",
        "decision_rule": "Highest volume with keyword difficulty under 40.",
    }


def write_judgment_files(root: Path) -> Layout:
    """Write only what a person supplies, plus the saved captures; return the article layout."""
    layout = Layout.for_article(ARTICLE, root)
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(acceptance_article(), encoding="utf-8", newline="\n")
    atomic_write_json(layout.bom_spec, spec())
    (root / TRANSCRIPT_PATH).write_text(transcript(), encoding="utf-8", newline="\n")
    atomic_write_json(root / DECISION_PATH, keyword_decision_input())
    load_or_create_run_id(layout, run_id=RUN_ID)
    write_paa_capture(layout)
    _write_evidence(layout)
    shutil.copyfile(root / "config" / "customer-proof-index.json", root / "config" / "nonvault-customer-proof-index.json")
    serp = build_serp_fixture(
        root, query=QUERY, collection_date=TODAY, run_id=RUN_ID, features=["featured snippet"],
        results=[{"url": url, "title": f"Scheduling {n}", "description": "Scheduling"}
                 for n, url in enumerate(SERP_PAGES, 1)],
        must_have_sections=list(SECTIONS),
    )
    atomic_write_json(layout.serp_evidence, serp)
    return layout


def pages() -> dict[str, tuple[int, str]]:
    web: dict[str, tuple[int, str]] = {url: (200, html_outline(headings)) for url, headings in SERP_PAGES.items()}
    web.update({OWNED_URL: (200, FACT_PAGE)})
    return web


def html_outline(headings: list[str]) -> str:
    return "<html><body><main>" + "".join(f"<h2>{heading}</h2><p>text</p>" for heading in headings) + "</main></body></html>"


class FakeWeb(PageTransport):
    """Fresh response per request; unknown public pages answer 200 with a plain page."""

    def __init__(self, replies: dict[str, Any] | None = None):
        super().__init__(replies if replies is not None else pages())
        self.requested: list[str] = []

    def _one(self, url: str):
        self.requested.append(url)
        self.replies.setdefault(url, (200, GENERIC_PAGE))
        return super()._one(url)


class Scope:
    """Stands in for ``PublicHttpTransport()`` as a context manager over a fake web."""

    def __init__(self, web: FakeWeb):
        self.web = web

    def __enter__(self) -> FakeWeb:
        return self.web

    def __exit__(self, *_exc: Any) -> None:
        return None

