"""Shared fixtures for the production truth-check tests: a BOM, a compliant article, fakes."""

from __future__ import annotations

import copy
from typing import Any

from tests.production_bom_support import (
    FACT_PAGE,
    FACT_QUOTE,
    FACT_URL,
    PAA_QUESTION,
    PILLAR_URL,
    FakeTransport,
    response,
)

DEMO_URL = "https://www.simprogroup.com/demo"
PROOF_URL = "https://www.simprogroup.com/customers/acme"
PROOF_TEXT = "Customers report 30% faster invoicing."
VERIFIED_AT = "2026-10-12T08:00:00Z"
CUSTOMER_QUOTE = "invoicing went from a weekly chore to a same-day task"


def bom() -> dict[str, Any]:
    return {
        "schema": "simpro-production-bom/v1",
        "identity": {
            "brand": "Simpro", "date": "2026-10-13",
            "cta": {"text": "Book a demo", "url": DEMO_URL},
        },
        "facts": [{
            "id": "f1", "claim": "More than 24,000 trade businesses worldwide trust it",
            "url": FACT_URL, "quote": FACT_QUOTE, "priority": "must",
            "verified_at": VERIFIED_AT, "check_detail": "quote found on page", "support": "quote_overlap",
        }],
        "proof": [{
            "id": "p1", "claim_id": "claim-metric-1", "kind": "metric", "priority": "should",
            "text": PROOF_TEXT, "url": PROOF_URL, "customer": "Acme Electrical",
            "approved_quotes": [{"quote": CUSTOMER_QUOTE, "status": "approved"}],
            "approved_metrics": [{"metric": "5 hours saved", "status": "approved"}],
        }],
        "paa": {"artifact": None, "questions": [{"question": PAA_QUESTION, "priority": "should"}]},
        "links": [
            {"url": PILLAR_URL, "anchor": "field service management software",
             "kind": "commercial_pillar", "priority": "must"},
            {"url": "https://www.simprogroup.com/blog/other", "anchor": "other post",
             "kind": "internal", "priority": "should"},
        ],
    }


def with_facts(extra: list[dict[str, Any]]) -> dict[str, Any]:
    value = bom()
    value["facts"] += copy.deepcopy(extra)
    return value


def article(body: str = "", *, faq: str | None = None, title: str = "Field Service Software Guide 2026",
            extra_front: str = "") -> str:
    answer = faq if faq is not None else (
        f"Field service software schedules jobs and dispatches crews. [More than 24,000 trade "
        f"businesses worldwide]({FACT_URL}) use it, and teams get started in 3 steps."
    )
    return (
        f'---\ntitle: "{title}"\ndescription: "How trade owners choose field service software."\n'
        f"last_updated: 2026-10-13\n{extra_front}---\n\n"
        "# Field Service Software Guide\n\n"
        "## What it is\n\n"
        f"Field service software runs scheduling and dispatch for crews. More than 24,000 trade "
        f"businesses worldwide use [field service tools]({FACT_URL}) to run jobs.\n\n"
        "Crews log time from any phone on every job site. See "
        f"[field service management software]({PILLAR_URL}) in action or [book a demo]({DEMO_URL}).\n\n"
        f"{body}"
        "## Frequently asked questions\n\n"
        f"### {PAA_QUESTION}\n\n{answer}\n"
    )


class IsolatingTransport(FakeTransport):
    """FakeTransport that also answers single requests, as the URL validator falls back to them."""

    def request(self, method, url, **kwargs):
        reply = self.replies[url]
        if isinstance(reply, Exception):
            raise reply
        return reply


def transport(**overrides: Any) -> FakeTransport:
    replies: dict[str, Any] = {
        FACT_URL: response(FACT_URL, 200, FACT_PAGE),
        PILLAR_URL: response(PILLAR_URL, 200),
        DEMO_URL: response(DEMO_URL, 200),
    }
    replies.update(overrides)
    return IsolatingTransport(replies)


def blocks(findings: list[Any], check: str | None = None) -> list[Any]:
    return [f for f in findings if f.severity == "block" and (check is None or f.check == check)]


def warns(findings: list[Any], check: str | None = None) -> list[Any]:
    return [f for f in findings if f.severity == "warn" and (check is None or f.check == check)]


def check_truth_for(text: str, value: dict[str, Any] | None = None, tr: FakeTransport | None = None) -> list[Any]:
    from data_sources.modules.production.truth import check_truth

    return check_truth(text, value if value is not None else bom(), transport=tr or transport())
