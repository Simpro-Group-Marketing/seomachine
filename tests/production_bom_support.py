"""Shared fixtures for the production BOM tests: a tmp workspace, fakes, and specs."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import requests
from data_sources.modules.production.bom_build import is_nonconnector
from data_sources.modules.production.layout import Layout, load_or_create_run_id
from data_sources.modules.vault_claim_receipts import ApprovedClaim, ValidatedClaimSet

FROZEN = Path(__file__).resolve().parent / "fixtures" / "production_bom"
TODAY = "2026-10-13"
ARTICLE = "drafts/field-service-software-2026-10-13.md"
FACT_URL = "https://example.org/report"
FACT_QUOTE = "Trusted by more than 24,000 trade businesses worldwide"
FACT_CLAIM = "More than 24,000 trade businesses worldwide trust it"
FACT_PAGE = (
    "<html><body><p>Trusted by more than 24,000 trade businesses worldwide.</p>"
    "<p>Crews log time from any phone on every job site.</p></body></html>"
)
PILLAR_URL = "https://www.simprogroup.com/"
PILLAR_ID = "simpro-us-homepage-field-service-management-software"
PILLAR_KEYWORD = "field service management software"
PAA_QUESTION = "What is field service software?"
CLAIM_ID = "claim-metric-1"
NONVAULT_ID = "clockshark-customer-story-chesapeake"
STORY_ID = "clockshark-story-row"
CONNECTOR_EVIDENCE_SCHEMA = "simpro-customer-proof-selector-evidence/v2"
NONVAULT_EVIDENCE_SCHEMA = "simpro-nonvault-customer-proof-selector-evidence/v1"
SLATE_ROLES = ("metric", "quote", "theme", "experience_story")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1), encoding="utf-8", newline="\n")


def response(url: str, status: int, body: str = "") -> requests.Response:
    reply = requests.Response()
    reply.status_code, reply.url = status, url
    reply._content, reply._content_consumed = body.encode("utf-8"), True
    reply.headers["Content-Type"] = "text/html; charset=utf-8"
    return reply


class FakeTransport:
    def __init__(self, replies: dict[str, Any]):
        self.replies, self.calls = replies, []

    def request_many(self, method, urls, **kwargs):
        self.calls.append(list(urls))
        out = []
        for url in urls:
            reply = self.replies[url]
            if isinstance(reply, Exception):
                raise reply
            out.append(reply)
        return out


def good_transport() -> FakeTransport:
    return FakeTransport({FACT_URL: response(FACT_URL, 200, FACT_PAGE)})


def approved_claim(claim_id: str = CLAIM_ID, **overrides: Any) -> ApprovedClaim:
    fields = dict(
        claim_id=claim_id,
        selector_id="sel-1",
        assertion="Customers report 30% faster invoicing.",
        use_mode="public_metric",
        brand_scope=("Simpro",),
        source_hash="hash",
        public_url="https://www.simprogroup.com/customers/acme",
        approval_source="connector_claim_result",
        receipt_revision="rev-7",
        claim_type="public_metric",
        evidence={"customer": "Acme Electrical"},
    )
    fields.update(overrides)
    return ApprovedClaim(**fields)


class FakeLoader:
    def __init__(self, claim_set: ValidatedClaimSet):
        self.claim_set, self.calls = claim_set, []

    def __call__(self, pack, receipt):
        self.calls.append((pack, receipt))
        return self.claim_set


def good_loader() -> FakeLoader:
    return FakeLoader(ValidatedClaimSet([approved_claim()], receipt_revision="rev-7"))


def connector_spec() -> dict[str, Any]:
    return {
        "schema": "simpro-production-bom-spec/v1",
        "brand": "Simpro",
        "market": "US",
        "title": "Field Service Software Guide",
        "objective": "Help owners choose software",
        "audience": "Trade business owners",
        "sections": [{"heading": "What it is", "purpose": "Define the term", "priority": "must"}],
        "facts": [
            {"id": "f1", "claim": FACT_CLAIM,
             "url": FACT_URL, "quote": FACT_QUOTE, "priority": "must"}
        ],
        "proof": [{"id": "p1", "claim_id": CLAIM_ID, "kind": "metric", "priority": "should"}],
        "paa_questions": [{"question": PAA_QUESTION, "priority": "should"}],
        "links": [
            {"url": PILLAR_URL, "anchor": "field service management software",
             "kind": "commercial_pillar", "priority": "must", "destination_id": PILLAR_ID},
            {"url": "https://www.simprogroup.com/blog/other", "anchor": "other post",
             "kind": "internal", "priority": "should"},
        ],
        "cta": {"text": "Book a demo", "url": "https://www.simprogroup.com/demo"},
        "schema_notes": ["BlogPosting", "BreadcrumbList"],
    }


def nonconnector_spec() -> dict[str, Any]:
    spec = connector_spec()
    spec.update(brand="ClockShark", title="Crew Time Tracking Guide")
    spec["links"] = [
        {"url": "https://clockshark.com/time-tracking", "anchor": "time tracking",
         "kind": "internal", "priority": "should"}
    ]
    spec["cta"] = {"text": "Try it", "url": "https://clockshark.com/demo"}
    spec["proof"] = [{"id": "p1", "claim_id": NONVAULT_ID, "kind": "theme", "priority": "should"}]
    spec["not_applicable_context_reason"] = "ClockShark workflow with no brand-vault signal"
    return spec


def nonvault_row(proof_id: str = NONVAULT_ID, **overrides: Any) -> dict[str, Any]:
    row = {
        "proof_id": proof_id,
        "approval_status": "approved",
        "public_copy_allowed": True,
        "source_type": "customer_story",
        "region": ["US"],
        "customer": "Chesapeake Lawn and Home",
        "public_url": "https://www.clockshark.com/testimonials/chesapeake",
        "evidence": "ClockShark page states: payroll and time tracking for mobile crews.",
        "restrictions": ["Paraphrase only"],
        "approved_quotes": [
            {"quote": "easy to use", "status": "approved", "url": "https://x.example/q"},
            {"quote": "draft quote", "status": "pending", "url": "https://x.example/q2"},
        ],
        "approved_metrics": [{"metric": "5 hours saved", "status": "approved"}],
    }
    row.update(overrides)
    return row


def nonvault_rows() -> list[dict[str, Any]]:
    return [
        nonvault_row(),
        nonvault_row("clockshark-pending", approval_status="pending"),
        nonvault_row("clockshark-nopublic", public_copy_allowed=False),
        nonvault_row("bigchange-story", public_url="https://www.bigchange.com/customers/x"),
        nonvault_row("clockshark-uk", region=["UK"]),
        nonvault_row("clockshark-global", region=["Global"]),
        nonvault_row("clockshark-noregion", region=[]),
        nonvault_row("clockshark-plain", approved_quotes=[], approved_metrics=[]),
        nonvault_row(STORY_ID, review_story={"story_allowed": True, "workflow_story": "x"}),
    ]


def pillar_record(**overrides: Any) -> dict[str, Any]:
    """Return the frozen commercial pillar record (a snapshot that passes index validation)."""
    record = json.loads((FROZEN / "pillar-record.json").read_text(encoding="utf-8"))
    record.update(overrides)
    return record


def write_pillar_index(root: Path, record: dict[str, Any] | None = None) -> None:
    """Write a one-record index plus the frozen evidence files its hashes bind to."""
    record = record or pillar_record()
    for relative in set(record["evidence_path"]):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FROZEN / Path(relative).name, target)
    write_json(root / "context" / "commercial-pillar-index.json", {
        "schema_version": "commercial-pillar-index/v1", "updated_at": "2026-10-01",
        "records": [record]})


def selector_evidence(spec: dict[str, Any], *, nonconnector: bool) -> dict[str, Any]:
    """Selector evidence whose selected ids are exactly the spec's proof claim ids, by kind."""
    roles = []
    for role in SLATE_ROLES:
        ids = [item["claim_id"] for item in spec["proof"] if item.get("kind") == role]
        roles.append({"role": role, "candidate_ids": ids, "claim_ids": [] if nonconnector else ids,
                      "selected_id": ids[0] if ids else "none", "selected_candidate": None,
                      "rejected_overrides": {}})
    return {"schema": NONVAULT_EVIDENCE_SCHEMA if nonconnector else CONNECTOR_EVIDENCE_SCHEMA,
            "selection_outcome": "customer_proof_candidates_available",
            "inputs": {"article_slug": "field-service-software", "rejected_overrides": {}},
            "artifacts": {}, "roles": roles}


def evidence_path(layout: Layout, spec: dict[str, Any]) -> Path:
    return layout.nonvault_customer_proof_evidence if is_nonconnector(spec) else layout.customer_proof_evidence


def paa_artifact(run_id: str, *, collection_date: str = TODAY) -> dict[str, Any]:
    return {"eligible_questions": [PAA_QUESTION, "Other?"], "collection_date": collection_date,
            "run_receipt": {"run_id": run_id}}


def make_workspace(root: Path, *, spec: dict[str, Any] | None = None,
                   paa: bool = True, context: bool = True) -> Layout:
    """Write every artifact a build needs and return the layout."""
    layout = Layout.for_article(ARTICLE, root)
    spec = copy.deepcopy(spec if spec is not None else connector_spec())
    write_json(layout.bom_spec, spec)
    write_json(layout.keyword_decision, {"schema": "decision", "primary": "fsm"})
    write_json(layout.keyword_shortlist, {
        "schema": "simpro-keyword-shortlist/v1", "primary": "field service software",
        "secondary": ["fsm software"], "candidates": [{"keyword": "fsm", "volume": 100}],
        "decision_rule": "highest volume under KD 50"})
    write_json(layout.serp_evidence, {"query": "field service software", "results": []})
    write_json(layout.serp_coverage, {
        "schema": "simpro-serp-coverage/v1", "query": "field service software",
        "pages": 9, "topics": [{"topic": "pricing", "heading": "Pricing", "pages": 6,
                                "suggested": "must"}],
        "uncovered_questions": ["Is it worth it?"], "unreachable": []})
    if paa:
        write_json(layout.paa_artifact, paa_artifact(load_or_create_run_id(layout)))
    write_json(evidence_path(layout, spec), selector_evidence(spec, nonconnector=is_nonconnector(spec)))
    if context:
        write_json(layout.context_pack, {"pack": True})
        write_json(layout.context_receipt, {"receipt": True})
    write_pillar_index(root)
    write_json(root / "config" / "nonvault-customer-proof-index.json", {
        "schema": "seomachine-nonvault-customer-proof-index/v1", "version": 1,
        "proof": nonvault_rows()})
    return layout
