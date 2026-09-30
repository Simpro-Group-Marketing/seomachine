"""Build current Simpro vault context for the AI scheduling rewrite."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.content_store import write_context_trace  # noqa: E402
from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.simpro_vault_client import SimproVaultClient  # noqa: E402


SLUG = "ai-scheduling-dispatch-field-service"
DATE = "2026-09-28"
ARTICLE = ROOT / "published" / "ai-scheduling-dispatch-field-service-2026-07-17.md"
REQUEST = ROOT / "research" / f"context-request-{SLUG}-{DATE}.json"
PACK = ROOT / "research" / f"context-pack-{SLUG}-{DATE}.json"
RECEIPT = ROOT / "research" / f"context-receipt-{SLUG}-{DATE}.json"
CUSTOMER_PACK = ROOT / "research" / f"context-pack-{SLUG}-customer-selector-{DATE}.json"
CUSTOMER_RECEIPT = ROOT / "research" / f"context-receipt-{SLUG}-customer-selector-{DATE}.json"
FRED_PACK = ROOT / "research" / f"context-pack-{SLUG}-fred-selector-{DATE}.json"
FRED_RECEIPT = ROOT / "research" / f"context-receipt-{SLUG}-fred-selector-{DATE}.json"
TRACE = ROOT / "research" / f"context-refresh-{SLUG}-{DATE}.json"

QUERIES = [
    "Simpro voice and tone guidance for a US field service blog",
    "Simpro AI positioning human oversight scheduling dispatch field service",
    "Simpro field service scheduling software product positioning",
    "Intelligent AI Scheduler RAIN Lightning current status and claim boundary",
    "Microsoft Salesforce competitive context for field service scheduling",
]

RESOURCES = {
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-47015608c0d4556a854fca7544b4a040": "guidance",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-517ad5ccb2cd5c3985831d8aba4cedaa": "guidance",
    "res-25accbf58dc75e7c8d256027288b93c7": "guidance",
}

CUSTOMER_CLAIMS = [
    {
        "claim_id": "claim-metric-MET-1482",
        "query": "TEAMWired manual invoicing hours were reduced by 90%",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    }
]

FRED_CLAIMS = [
    {
        "claim_id": "claim-fred-FVMI-0003",
        "query": "Fred Voccola AI scheduling dispatch field service human oversight",
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


def main() -> int:
    request = {
        "schema": "simpro-context-request/v1",
        "task": (
            "Rewrite the existing AI scheduling and dispatch article in place, preserve its "
            "canonical URL and original publication date, and prepare source-safe public copy."
        ),
        "scope": {
            "artifact_type": "blog",
            "brand": "Simpro",
            "title": "AI Scheduling and Dispatch for Field Service | Simpro",
            "objective": (
                "Explain how AI-assisted scheduling works, the operating data and human controls "
                "it requires, how to evaluate vendor examples, and how to run a controlled pilot."
            ),
            "audience": (
                "US field service owners, operations managers, schedulers, and dispatchers "
                "evaluating AI-assisted scheduling"
            ),
            "region": "US",
            "article_sha256": hashlib.sha256(ARTICLE.read_bytes()).hexdigest(),
            "required_context_topics": [
                "voice and tone",
                "AI positioning",
                "product positioning",
                "scheduling and dispatch",
                "competitive context",
                "named-feature status boundary",
            ],
            "intended_public_use_modes": ["paraphrase"],
        },
        "context_needs": [
            "Current no-author Simpro blog voice and US localization guidance.",
            "Current AI messaging boundaries for recommendations, oversight, and proof.",
            "Product language for scheduling and dispatch without unsupported outcomes.",
            "Competitive-context guidance for a nonranking Microsoft and Salesforce matrix.",
            "Current vault boundary for RAIN, Lightning, and Intelligent AI Scheduler wording.",
        ],
        "constraints": [
            "No named author or Person schema.",
            "No em dashes.",
            "Do not publish vault-only competitive intelligence.",
            "Do not publish customer proof or Fred authority without direct selector fit.",
            "Do not publish RAIN, Lightning, or Intelligent AI Scheduler status language when the current claim receipt cannot support every required status dependency.",
            "Use current official public sources for Microsoft and Salesforce facts.",
        ],
        "unresolved_gaps": [],
    }
    atomic_write_json(REQUEST, request)

    client = SimproVaultClient()
    status = client.status()
    if status.get("status") != "ready":
        raise RuntimeError(status)
    describe = client.describe()
    searches = {query: client.search(query, limit=50) for query in QUERIES}
    reads = {
        resource_id: client.read(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCES.items()
    }
    expansions = {
        resource_id: client.expand(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCES.items()
    }
    build_input = {
        "request": request,
        "resource_ids": list(RESOURCES),
        "resource_purposes": RESOURCES,
        "claim_requests": [],
        "search_queries": QUERIES,
        "constraints": request["constraints"],
        "unresolved_gaps": [],
        "task_satisfaction": "satisfied",
    }
    customer_claim_lookup = {
        claim["claim_id"]: client.claims(
            claim["query"],
            use_mode=claim["use_mode"],
            brand_scope=claim["brand_scope"],
            limit=20,
        )
        for claim in CUSTOMER_CLAIMS
    }
    fred_claim_lookup = {
        claim["claim_id"]: client.claims(
            claim["query"],
            use_mode=claim["use_mode"],
            brand_scope=claim["brand_scope"],
            limit=20,
        )
        for claim in FRED_CLAIMS
    }

    customer_built = client.build_context(
        {**build_input, "claim_requests": CUSTOMER_CLAIMS}
    )
    customer_validation = client.validate_context(
        request,
        customer_built["pack"],
        customer_built["receipt"],
    )
    if customer_validation.get("valid") is not True:
        raise RuntimeError(customer_validation)

    fred_built = client.build_context({**build_input, "claim_requests": FRED_CLAIMS})
    fred_validation = client.validate_context(
        request,
        fred_built["pack"],
        fred_built["receipt"],
    )
    if fred_validation.get("valid") is not True:
        raise RuntimeError(fred_validation)

    built = client.build_context(build_input)
    validation = client.validate_context(request, built["pack"], built["receipt"])
    if validation.get("valid") is not True:
        raise RuntimeError(validation)
    atomic_write_json(PACK, built["pack"])
    atomic_write_json(RECEIPT, built["receipt"])
    atomic_write_json(CUSTOMER_PACK, customer_built["pack"])
    atomic_write_json(CUSTOMER_RECEIPT, customer_built["receipt"])
    atomic_write_json(FRED_PACK, fred_built["pack"])
    atomic_write_json(FRED_RECEIPT, fred_built["receipt"])
    write_context_trace(
        TRACE,
        {
            "schema": "simpro-ai-scheduling-dispatch-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "reads": reads,
            "expansions": expansions,
            "customer_claim_lookup": customer_claim_lookup,
            "fred_claim_lookup": fred_claim_lookup,
            "build_input": build_input,
            "build_output": built,
            "validation": validation,
            "customer_selector_build_output": customer_built,
            "customer_selector_validation": customer_validation,
            "fred_selector_build_output": fred_built,
            "fred_selector_validation": fred_validation,
        },
        workspace_root=ROOT,
        generated_at=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "status": status["status"],
                "pack_sha256": built["receipt"]["pack_sha256"],
                "receipt_sha256": built["receipt"]["receipt_sha256"],
                "resources": len(RESOURCES),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
