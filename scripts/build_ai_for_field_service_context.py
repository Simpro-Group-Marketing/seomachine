"""Build current vault context for the AI field service canonical rewrite."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.simpro_vault_client import SimproVaultClient


SLUG = "ai-for-field-service"
DATE = "2026-09-28"
RESEARCH = ROOT / "research"
REQUEST_PATH = RESEARCH / f"context-request-{SLUG}.json"
PACK_PATH = RESEARCH / f"context-pack-{SLUG}.json"
RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}.json"
TRACE_PATH = RESEARCH / f"context-refresh-{SLUG}-{DATE}.json"
SELECTOR_PACK_PATH = RESEARCH / f"context-pack-{SLUG}-selection.json"
SELECTOR_RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}-selection.json"

TITLE = "AI in Field Service Management: How to Run Smarter, Faster, More Proactive Operations"
OBJECTIVE = (
    "Help US trade-business owners and field service leaders evaluate AI-powered field "
    "service management software by operational fit, understand where AI can support the "
    "job lifecycle, and decide whether Simpro belongs on their demo shortlist."
)

REQUEST = {
    "schema": "simpro-context-request/v1",
    "task": f"Build current connector-bound context for the focused rewrite titled {TITLE}.",
    "scope": {
        "brand": "Simpro",
        "market": "US",
        "region": "US",
        "artifact_type": "blog",
        "workflow_mode": "rewrite",
        "title": TITLE,
        "canonical_url": "https://www.simprogroup.com/blog/ai-for-field-service",
        "audience": (
            "US trade-business owners, operations leaders, dispatch leaders, and software "
            "evaluators across HVAC, electrical, plumbing, fire and security, and mixed "
            "field-service operations"
        ),
        "objective": OBJECTIVE,
        "intended_public_use_modes": ["public_paraphrase"],
    },
}

SEARCH_QUERIES = [
    "current Simpro blog voice and tone for a US field service software buyer guide with no named author",
    "Simpro AI field service management software positioning connected office and field workflows Lightning RAIN human control",
    "Intelligent AI Scheduler AI-Guided Forms RAIN feature timing availability region package release status",
    "Simpro field service management estimating scheduling job execution documentation invoicing reporting integrations implementation",
    "AI for field service current blog editorial revision unsafe metrics proof requirements",
    "Product Positioning",
    "ICP customer archetypes field service owner operations manager dispatcher software evaluator",
]

RESOURCE_PURPOSES = {
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-47015608c0d4556a854fca7544b4a040": "guidance",
    "res-25accbf58dc75e7c8d256027288b93c7": "context",
    "res-f08edc074fb6554c893aeba214e70c49": "context",
    "res-f7b556dd8a1156dfbefbbf014eb72df5": "context",
    "res-16c113c993565a4c84150d131c034c57": "guidance",
    "res-52541b6834d85a7ba6c91740a159647a": "context",
    "res-dfc67c5cef87541d856a765f2747a2cb": "guidance",
    "res-92348f8056165d4ba81a3c91738604e2": "context",
}

EXPAND_RESOURCE_IDS = [
    "res-b34b392d22b9507089ade3fec47ee9e0",
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
    "res-47015608c0d4556a854fca7544b4a040",
    "res-25accbf58dc75e7c8d256027288b93c7",
    "res-f7b556dd8a1156dfbefbbf014eb72df5",
    "res-16c113c993565a4c84150d131c034c57",
]

CLAIM_REQUESTS: list[dict[str, str]] = []

SELECTOR_CLAIM_REQUESTS = [
    {
        "claim_id": "claim-metric-MET-0064",
        "query": "Quorum estimating speed and project cost visibility field service case study",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0066",
        "query": "TEAMWired manual invoicing workflow field service case study",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0072",
        "query": "AlarmQuest invoice generation field service case study",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0077",
        "query": "Audem Electrical field service operational efficiency case study",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0095",
        "query": "Infinite Audio Video Solutions field service administration case study",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0001",
        "query": "Fred Voccola Simpro Group CEO AI field service economics",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0006",
        "query": "Fred Voccola Simpro AI in the Commercial Trades plumbers electricians HVAC contractors",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]

CONSTRAINTS = [
    "Preserve the canonical URL and existing H1 while adding two early commercial-selection answers.",
    "Use US spelling, current Simpro blog voice, no named author, no first-person authority language, and no em dash.",
    "Define best by buyer workflow fit; do not publish a vendor ranking or universal-best claim.",
    "Do not use public paraphrase RAIN claim decisions in the article body because the release public-research gate requires non-owned inline proof for numeric feature-count phrasing.",
    "Route RAIN to reader demo verification only; advise buyers to confirm region, package, availability, and release status during a demo.",
    "Do not retain unsupported profit, speed, first-time-fix, paperwork, payment, dispute, or autonomous-action claims from the live article.",
    "Keep GSC, Peec, GA4, workflow, strategy, and readiness evidence out of public copy.",
]


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def resource_ids(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        row["resource_id"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("resource_id"), str)
    }


def main() -> int:
    client = SimproVaultClient()
    status = client.status()
    describe = client.describe()
    if status.get("status") != "ready":
        raise RuntimeError(f"vault is not ready: {status}")

    searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}
    discovered = set().union(*(resource_ids(rows) for rows in searches.values()))
    missing = sorted(set(RESOURCE_PURPOSES) - discovered)
    if missing:
        raise RuntimeError(f"selected resources were not rediscovered: {missing}")

    expansions = {
        resource_id: client.expand(resource_id, purpose=RESOURCE_PURPOSES[resource_id])
        for resource_id in EXPAND_RESOURCE_IDS
    }
    reads = {
        resource_id: client.read(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCE_PURPOSES.items()
    }
    all_claim_requests = CLAIM_REQUESTS + SELECTOR_CLAIM_REQUESTS
    claim_lookups = {
        item["claim_id"]: client.claims(
            item["query"],
            use_mode=item["use_mode"],
            brand_scope=item["brand_scope"],
            limit=50,
        )
        for item in all_claim_requests
    }

    build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "constraints": CONSTRAINTS,
        "claim_requests": CLAIM_REQUESTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    built = client.build_context(build_input)
    pack = built["pack"]
    receipt = built["receipt"]
    validation = client.validate_context(REQUEST, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"context validation failed: {validation}")

    selector_build_input = {
        **build_input,
        "claim_requests": SELECTOR_CLAIM_REQUESTS,
    }
    selector_built = client.build_context(selector_build_input)
    selector_pack = selector_built["pack"]
    selector_receipt = selector_built["receipt"]
    selector_validation = client.validate_context(
        REQUEST,
        selector_pack,
        selector_receipt,
    )
    if selector_validation.get("valid") is not True:
        raise RuntimeError(
            f"selector context validation failed: {selector_validation}"
        )

    write_json(REQUEST_PATH, REQUEST)
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    write_json(SELECTOR_PACK_PATH, selector_pack)
    write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-ai-for-field-service-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "approved_claim_lookups": claim_lookups,
            "build_input": build_input,
            "build_output": built,
            "validation": validation,
            "selector_build_input": selector_build_input,
            "selector_build_output": selector_built,
            "selector_validation": selector_validation,
        },
        workspace_root=ROOT,
        generated_at=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "status": status["status"],
                "manifest_revision": status["revisions"]["manifest_revision"],
                "claim_registry_revision": status["revisions"]["claim_registry_revision"],
                "pack_sha256": receipt.get("pack_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "validation": validation,
                "selector_pack_sha256": selector_receipt.get("pack_sha256"),
                "selector_receipt_sha256": selector_receipt.get("receipt_sha256"),
                "selector_validation": selector_validation,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
