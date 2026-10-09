"""Build current vault context for the best apps for electricians rewrite."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.simpro_vault_client import SimproVaultClient


SLUG = "best-apps-electricians"
DATE = "2026-09-30"
ARTICLE = ROOT / "rewrites" / "electrician-apps-2026-09-30.md"
RESEARCH = ROOT / "research"
REQUEST_PATH = RESEARCH / "context-request-best-apps-electricians.json"
PACK_PATH = RESEARCH / "context-pack-best-apps-electricians.json"
RECEIPT_PATH = RESEARCH / "context-receipt-best-apps-electricians.json"
TRACE_PATH = RESEARCH / f"context-refresh-{SLUG}-{DATE}.json"
SELECTOR_PACK_PATH = RESEARCH / "context-pack-best-apps-electricians-customer-selector.json"
SELECTOR_RECEIPT_PATH = RESEARCH / "context-receipt-best-apps-electricians-customer-selector.json"
CLAIM_LOOKUP_PATH = RESEARCH / "customer-proof-claim-lookup-best-apps-electricians-2026-09-30.json"

TITLE = "Best Apps for Electricians: 10 Tools for Fieldwork and Business Management"
OBJECTIVE = (
    "Help US electricians and electrical contractor owners choose an app stack by "
    "job-to-be-done, team size and workflow complexity."
)
AUDIENCE = (
    "US electricians, electrical contractor owners, operations leaders and field "
    "supervisors comparing technical field tools and business-management apps"
)

CONSTRAINTS = [
    "No universal winner or independent ranking claim.",
    "Use current official public vendor sources for competitor facts.",
    "Do not publish Hindsight or internal competitive intelligence as proof.",
    "Do not use customer or Fred proof unless selectors establish direct topical fit.",
    "No named author or Person schema without verified authorship.",
    "No em dashes.",
]

SEARCH_QUERIES = [
    "Simpro voice and tone for a practical US electrical contractor software comparison blog",
    "Simpro electrical contractor audience workflows mobile estimating scheduling dispatch job costing invoicing",
    "Simpro product positioning for office and field service management workflows",
    "Simpro competitive context for electrician apps ServiceTitan Housecall Pro Workyard Fieldwire Joist",
]

RESOURCE_PURPOSES = {
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-f9f9499223a15d6a901806f30fb1a8ba": "context",
    "res-10b97eee1de25395bbf8b904111ca4b0": "context",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-517ad5ccb2cd5c3985831d8aba4cedaa": "guidance",
}

EXPAND_RESOURCE_IDS = [
    "res-d31f057a305f51918055120d95b76c6a",
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
]

SELECTOR_CLAIM_REQUESTS = [
    {
        "brand_scope": "Simpro",
        "claim_id": "claim-metric-MET-1024",
        "query": "Simpro electrician contractor customer quote mobile app scheduling dispatch invoicing",
        "use_mode": "exact_quote",
    }
]

PROOF_LOOKUP_REQUESTS = [
    {
        "brand_scope": "Simpro",
        "query": "Simpro electrician contractor customer proof metric scheduling dispatch invoicing job costing",
        "use_mode": "public_metric",
        "limit": 20,
    },
    {
        "brand_scope": "Simpro",
        "query": "Simpro electrician contractor customer quote mobile app scheduling dispatch invoicing",
        "use_mode": "exact_quote",
        "limit": 20,
    },
    {
        "brand_scope": "Simpro",
        "query": "Simpro electrician contractor customer paraphrase scheduling dispatch invoicing job costing",
        "use_mode": "public_paraphrase",
        "limit": 20,
    },
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def build_request() -> dict[str, Any]:
    return {
        "schema": "simpro-context-request/v1",
        "task": (
            "Rewrite the existing Simpro electrician-app article at its current "
            "canonical URL as a proof-safe 10-app job-to-be-done comparison."
        ),
        "scope": {
            "article_sha256": sha256_file(ARTICLE),
            "artifact_type": "blog",
            "audience": AUDIENCE,
            "brand": "Simpro",
            "intended_public_use_modes": ["paraphrase"],
            "objective": OBJECTIVE,
            "region": "US",
            "required_context_topics": [
                "voice and tone",
                "industry:electrical",
                "product positioning",
                "competitive context",
            ],
            "title": TITLE,
        },
        "constraints": CONSTRAINTS,
        "context_needs": [
            "Trade-aware US editorial voice for owners and field leaders.",
            (
                "Electrical workflow language that distinguishes individual field "
                "tools from business-management platforms."
            ),
            "Conservative Simpro category and office-field workflow positioning.",
            (
                "Private competitive context for documenting a job-to-be-done "
                "shortlist without publishing battlecard intelligence."
            ),
        ],
        "unresolved_gaps": [],
    }


def build_lookup_artifact(client: SimproVaultClient) -> dict[str, Any]:
    lookups: list[dict[str, Any]] = []
    for request in PROOF_LOOKUP_REQUESTS:
        rows = client.claims(
            request["query"],
            use_mode=request["use_mode"],
            brand_scope=request["brand_scope"],
            limit=request["limit"],
        )
        lookups.append(
            {
                **request,
                "source": "SimproVaultClient.claims",
                "status": "complete",
                "truncated": False,
                "result_count": len(rows) if isinstance(rows, list) else 0,
                "claim_ids": [
                    row.get("claim_id")
                    for row in rows
                    if isinstance(row, dict) and isinstance(row.get("claim_id"), str)
                ],
                "rows": rows,
            }
        )
        print(
            f"vault_claim_lookup complete: {request['use_mode']} ({lookups[-1]['result_count']} rows)",
            flush=True,
        )
    return {
        "schema": "simpro-customer-proof-claim-lookup/v1",
        "source": "SimproVaultClient.claims",
        "article_slug": SLUG,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lookups": lookups,
    }


def main() -> int:
    client = SimproVaultClient()
    status = client.status()
    describe = client.describe()
    print("vault_describe complete", flush=True)
    if status.get("status") != "ready":
        raise RuntimeError(f"vault is not ready: {status}")

    searches = {}
    for query in SEARCH_QUERIES:
        searches[query] = client.search(query, limit=50)
        print(f"vault_search complete: {query}", flush=True)

    discovered = set().union(*(resource_ids(rows) for rows in searches.values()))
    missing = sorted(set(RESOURCE_PURPOSES) - discovered)
    if missing:
        raise RuntimeError(f"selected resources were not rediscovered: {missing}")

    expansions = {}
    for resource_id in EXPAND_RESOURCE_IDS:
        expansions[resource_id] = client.expand(
            resource_id,
            purpose=RESOURCE_PURPOSES[resource_id],
        )
        print(f"vault_expand complete: {resource_id}", flush=True)

    reads = {}
    for resource_id, purpose in RESOURCE_PURPOSES.items():
        reads[resource_id] = client.read(resource_id, purpose=purpose)
        print(f"vault_read complete: {resource_id}", flush=True)

    request = build_request()
    build_input = {
        "request": request,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "constraints": CONSTRAINTS,
        "claim_requests": [],
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    selector_build_input = {
        **build_input,
        "claim_requests": SELECTOR_CLAIM_REQUESTS,
    }

    claim_lookup_artifact = build_lookup_artifact(client)
    selector_built = client.build_context(selector_build_input)
    selector_pack = selector_built["pack"]
    selector_receipt = selector_built["receipt"]
    selector_validation = client.validate_context(request, selector_pack, selector_receipt)
    if selector_validation.get("valid") is not True:
        raise RuntimeError(f"selector context validation failed: {selector_validation}")
    print("vault_build_context customer selector complete", flush=True)
    print("vault_validate_context customer selector complete", flush=True)

    built = client.build_context(build_input)
    pack = built["pack"]
    receipt = built["receipt"]
    validation = client.validate_context(request, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"context validation failed: {validation}")
    print("vault_build_context complete", flush=True)
    print("vault_validate_context complete", flush=True)

    write_json(REQUEST_PATH, request)
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    write_json(SELECTOR_PACK_PATH, selector_pack)
    write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
    write_json(CLAIM_LOOKUP_PATH, claim_lookup_artifact)
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-best-apps-electricians-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "claim_lookup_artifact": claim_lookup_artifact,
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
                "article_sha256": request["scope"]["article_sha256"],
                "pack_sha256": sha256_file(PACK_PATH),
                "receipt_sha256": sha256_file(RECEIPT_PATH),
                "selector_pack_sha256": sha256_file(SELECTOR_PACK_PATH),
                "selector_receipt_sha256": sha256_file(SELECTOR_RECEIPT_PATH),
                "claim_lookup_sha256": sha256_file(CLAIM_LOOKUP_PATH),
                "resource_count": len(RESOURCE_PURPOSES),
            },
            indent=2,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
