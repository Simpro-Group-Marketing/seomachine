"""Build verified vault context for the AI estimating software research package."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.content_store import write_context_trace  # noqa: E402
from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.simpro_vault_client import SimproVaultClient  # noqa: E402


SLUG = "ai-estimating-software-trade-businesses"
DATE = "2026-09-28"
RESEARCH = ROOT / "research"
REQUEST_PATH = RESEARCH / f"context-request-{SLUG}.json"
PACK_PATH = RESEARCH / f"context-pack-{SLUG}.json"
RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}.json"
TRACE_PATH = RESEARCH / f"context-refresh-{SLUG}-{DATE}.json"

TITLE = "AI Estimating Software for Trade Businesses: A Human-Reviewed Workflow"
OBJECTIVE = (
    "Help US trade-business owners, estimators, operations leaders, and office "
    "managers understand a human-reviewed AI estimating workflow, evaluate inputs "
    "and controls, and connect estimating decisions to downstream job operations."
)

REQUEST = {
    "schema": "simpro-context-request/v1",
    "task": (
        "Build the current connector-bound research context required before drafting "
        f"the new Simpro US blog titled {TITLE}."
    ),
    "scope": {
        "brand": "Simpro",
        "market": "US",
        "region": "US",
        "artifact_type": "blog",
        "workflow_mode": "new",
        "topic_slug": SLUG,
        "title": TITLE,
        "target_url": "/blog/ai-estimating-software-trade-businesses",
        "primary_keyword": "ai estimating software",
        "commercial_pillar_candidate": (
            "https://www.simprogroup.com/features/estimating-software"
        ),
        "audience": (
            "Owners, estimators, operations leaders, and office managers in HVAC, "
            "plumbing, electrical, and adjacent US trades"
        ),
        "objective": OBJECTIVE,
        "required_context_topics": [
            "current blog voice and tone",
            "US trade-business ICP",
            "estimating and quoting workflows",
            "estimating feature positioning",
            "AI capability and status boundaries",
            "customer proof candidates",
            "Fred Voccola authority candidates",
        ],
        "intended_public_use_modes": [
            "public_paraphrase",
            "public_metric",
            "exact_quote",
            "authority_support",
        ],
    },
    "context_needs": [
        "Current Simpro US blog voice and localization guidance.",
        "Verified audience and workflow context for trade-business estimating.",
        "Current product-positioning language for estimating and quoting.",
        "Current AI messaging, human-oversight, and availability boundaries.",
        "Connector-approved proof and Fred candidates for mandatory selector review.",
    ],
    "constraints": [
        "Do not draft the public article in this task.",
        "Do not state or imply that Simpro currently generates estimates with AI unless an approved current claim directly supports that capability.",
        "Treat customer outcomes as product-workflow proof, not as evidence that AI caused the outcome.",
        "Default to no public customer proof and no public Fred proof unless direct topical fit and every mining and citation requirement are satisfied.",
        "No public competitor comparison; competitor pages are format research only.",
        "Keep Peec metrics and competitor observations private in the AI-citation research artifact.",
        "Use US spelling and prohibit em dashes in future public copy.",
    ],
    "unresolved_gaps": [
        "No connector-approved claim was discovered that directly proves a current Simpro AI-estimating capability.",
    ],
}

SEARCH_QUERIES = [
    "current Simpro blog voice and tone guidance for a US article",
    "Simpro ideal customer profile trade business owners estimators operations leaders office managers HVAC plumbing electrical",
    "Simpro estimating and quoting workflow price books proposals approvals estimate to invoice",
    "Simpro estimating software feature page US product positioning",
    "Simpro product positioning estimating quoting job management invoicing reporting",
    "Simpro artificial intelligence estimating quotes human review capability current status",
    "human review approval AI generated estimates trade business",
    "Simpro customer proof estimating quoting trade businesses",
    "Fred Voccola AI estimating quoting trade businesses",
]

RESOURCE_PURPOSES = {
    "res-641679c4b6c65e93951cb8d8e1ab88af": "context",
    "res-d31f057a305f51918055120d95b76c6a": "context",
    "res-329967c98bb351628aed830575fd8496": "context",
    "res-42f75ba4858d58babd6810e6e6fdf4fa": "context",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "context",
    "res-6716e1bab324565aa8a906b05b0aa502": "context",
    "res-1825898a11855f89be9bb69c544a6aa3": "context",
    "res-0dd3c26cb00d5e63b80c10af80d114e1": "context",
    "res-6c64056014705c1ebdc9076981442862": "context",
    "res-47015608c0d4556a854fca7544b4a040": "context",
    "res-c027b4f595a5549b8c29545379e0adf0": "context",
    "res-15f3055bbe9850d0974573791ce80840": "context",
}

CLAIM_REQUESTS = [
    {
        "claim_id": "claim-metric-MET-0194",
        "query": "BGE Digital estimates more than 10X faster",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0102",
        "query": "Quorum estimates completed 60% faster",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0200",
        "query": "Audem Electrical quoting 8X faster and quote volume doubled",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1245",
        "query": "estimating proposals service project management invoicing single application",
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0006",
        "query": "Fred Voccola Simpro AI in the Commercial Trades",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]


def _resource_ids(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        str(row["resource_id"])
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("resource_id"), str)
    }


def main() -> int:
    client = SimproVaultClient()
    status = client.status()
    print("vault_status complete", flush=True)
    if status.get("status") != "ready":
        raise RuntimeError(f"vault is not ready: {status}")
    describe = client.describe()
    print("vault_describe complete", flush=True)
    searches = {}
    for query in SEARCH_QUERIES:
        searches[query] = client.search(query, limit=50)
        print(f"vault_search complete: {query}", flush=True)
    discovered = set().union(*(_resource_ids(rows) for rows in searches.values()))
    missing = sorted(set(RESOURCE_PURPOSES) - discovered)
    if missing:
        raise RuntimeError(f"selected resources were not rediscovered: {missing}")

    reads = {}
    expansions = {}
    for resource_id, purpose in RESOURCE_PURPOSES.items():
        reads[resource_id] = client.read(resource_id, purpose=purpose)
        print(f"vault_read complete: {resource_id}", flush=True)
        expansions[resource_id] = client.expand(resource_id, purpose=purpose)
        print(f"vault_expand complete: {resource_id}", flush=True)
    claim_lookups = {}
    for request in CLAIM_REQUESTS:
        claim_lookups[request["claim_id"]] = client.claims(
            request["query"],
            use_mode=request["use_mode"],
            brand_scope=request["brand_scope"],
            limit=50,
        )
        print(f"vault_claims complete: {request['claim_id']}", flush=True)

    build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": CLAIM_REQUESTS,
        "constraints": REQUEST["constraints"],
        "unresolved_gaps": REQUEST["unresolved_gaps"],
        "task_satisfaction": "partial",
    }
    built = client.build_context(build_input)
    print("vault_build_context complete", flush=True)
    validation = client.validate_context(
        REQUEST, built["pack"], built["receipt"]
    )
    print("vault_validate_context complete", flush=True)
    if validation.get("valid") is not True:
        raise RuntimeError(f"context validation failed: {validation}")

    atomic_write_json(REQUEST_PATH, REQUEST)
    atomic_write_json(PACK_PATH, built["pack"])
    atomic_write_json(RECEIPT_PATH, built["receipt"])
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-ai-estimating-software-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "reads": reads,
            "expansions": expansions,
            "approved_claim_lookups": claim_lookups,
            "build_input": build_input,
            "build_output": built,
            "validation": validation,
        },
        workspace_root=ROOT,
        generated_at=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "status": status["status"],
                "manifest_revision": status["revisions"]["manifest_revision"],
                "claim_registry_revision": status["revisions"][
                    "claim_registry_revision"
                ],
                "pack_sha256": built["receipt"].get("pack_sha256"),
                "receipt_sha256": built["receipt"].get("receipt_sha256"),
                "validation": validation,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
