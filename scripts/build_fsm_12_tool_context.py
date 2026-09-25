from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient
from data_sources.modules.artifact_runtime.content_store import write_context_trace


REQUEST_PATH = ROOT / "research" / "context-request-best-field-service-management-software-2026-09-24.json"
ARTICLE_PATH = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
PACK_PATH = ROOT / "research" / "context-pack-best-field-service-management-software-2026-09-24.json"
RECEIPT_PATH = ROOT / "research" / "context-receipt-best-field-service-management-software-2026-09-24.json"
SELECTOR_PACK_PATH = (
    ROOT
    / "research"
    / "context-pack-best-field-service-management-software-customer-selector-2026-09-24.json"
)
SELECTOR_RECEIPT_PATH = (
    ROOT
    / "research"
    / "context-receipt-best-field-service-management-software-customer-selector-2026-09-24.json"
)
TRACE_PATH = (
    ROOT
    / "research"
    / "context-refresh-best-field-service-management-software-12-tools-2026-09-24.json"
)

SEARCH_QUERIES = [
    "Simpro US field service management software product positioning for growth-minded trade contractors and office-to-field workflows",
    "current Simpro blog voice tone and US localization guidance for a third-person software buyer guide with no named author",
    "Simpro homepage field service management software topic ownership and supporting blog internal linking",
    "Simpro competitive context for Jobber Joblogic FieldEdge BuildOps ServiceTitan FieldPulse Housecall Pro Service Fusion ServiceM8 Tradify Fergus",
    "Simpro job management software solution language for scheduling dispatch field operations inventory invoicing and reporting",
    "Simpro product positioning for trade contractors coordinating service and project work in one operating model",
    "Simpro comparison page competitive context for ServiceTitan BuildOps Joblogic and FieldPulse",
]

RESOURCE_PURPOSES = {
    "res-230f144aab93512e840167c4a25e60be": "guidance",
    "res-3887846244f05f16bfc0516889d340f3": "context",
    "res-5c1b34d7d2175caab4fb29a208e59ac0": "context",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-d7e3d5ca80955407a9d06be5f129e11b": "context",
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-f882ab230eb2563889e300d612c324bc": "context",
}

EXPAND_RESOURCE_IDS = [
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
    "res-d31f057a305f51918055120d95b76c6a",
    "res-e3ade596be645307ad4c1f84620ce021",
    "res-b34b392d22b9507089ade3fec47ee9e0",
    "res-f882ab230eb2563889e300d612c324bc",
    "res-5c1b34d7d2175caab4fb29a208e59ac0",
]

CONSTRAINTS = [
    "Connector-bound Simpro rewrite workflow.",
    "No named author, named reviewer, Person author schema, first-person authority language, or em dash.",
    "The canonical URL remains https://www.simprogroup.com/blog/best-field-service-management-software.",
    "The homepage owns the exact first-paragraph anchor field service management software under current user instruction.",
    "Use exactly the 12 user-selected tools and present them as a fit-based shortlist rather than a universal ranking.",
    "Use an early five-route decision table for small streamlined service, growing multi-crew trade, combined service and project, commercial or asset-heavy, and recurring maintenance operations.",
    "Use start-with and first-demo-list language; do not convert retrieval or citation counts into product rankings.",
    "Use Hindsight internal strategy only to prioritize demo-test emphasis and buyer objections; never use it as public claim support.",
    "Independently verify every publishable competitor fact against current official vendor documentation.",
    "Keep vendor cards text-only and retain one owned featured-image placeholder.",
    "Public vendor capabilities and pricing status require current official public sources.",
    "Public proof-sensitive claims require an exact use-mode approved-claim query and source verification.",
    "The job management solution link is a reader navigation route and low-risk category reference, not public proof.",
]

CUSTOMER_PROOF_SELECTOR_CLAIM = {
    "claim_id": "claim-metric-MET-1482",
    "query": "TEAMWired manual invoicing hours were reduced by 90%",
    "use_mode": "public_metric",
    "brand_scope": "Simpro",
}


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def result_ids(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        row["resource_id"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("resource_id"), str)
    }


def relationship_ids(value: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        resource_id = value.get("resource_id")
        if isinstance(resource_id, str):
            ids.add(resource_id)
        for child in value.values():
            ids.update(relationship_ids(child))
    elif isinstance(value, list):
        for child in value:
            ids.update(relationship_ids(child))
    return ids


def main(*, reuse_current_discovery: bool = False) -> None:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    request["scope"]["article_sha256"] = hashlib.sha256(ARTICLE_PATH.read_bytes()).hexdigest()
    write_json(REQUEST_PATH, request)
    client = SimproVaultClient()

    status = client.status()
    describe = client.describe()
    if reuse_current_discovery:
        searches: dict[str, Any] = {}
        expansions: dict[str, Any] = {}
        reads: dict[str, Any] = {}
        claim_lookup: list[Any] = []
        customer_proof_claim_lookup: list[Any] = []
    else:
        searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}
        expansions = {
            resource_id: client.expand(resource_id, purpose=RESOURCE_PURPOSES[resource_id])
            for resource_id in EXPAND_RESOURCE_IDS
        }

        discovered_ids: set[str] = set()
        for rows in searches.values():
            discovered_ids.update(result_ids(rows))
        for expansion in expansions.values():
            discovered_ids.update(relationship_ids(expansion))
        missing_ids = sorted(set(RESOURCE_PURPOSES) - discovered_ids)
        if missing_ids:
            raise RuntimeError(f"Selected resource IDs were not rediscovered: {missing_ids}")

        reads = {
            resource_id: client.read(resource_id, purpose=purpose)
            for resource_id, purpose in RESOURCE_PURPOSES.items()
        }
        claim_lookup = client.claims(
            "Simpro field service management software scheduling dispatch inventory job costing invoicing reporting for trade contractors",
            use_mode="public_paraphrase",
            brand_scope="Simpro",
            limit=20,
        )
        customer_proof_claim_lookup = client.claims(
            CUSTOMER_PROOF_SELECTOR_CLAIM["query"],
            use_mode=CUSTOMER_PROOF_SELECTOR_CLAIM["use_mode"],
            brand_scope=CUSTOMER_PROOF_SELECTOR_CLAIM["brand_scope"],
            limit=20,
        )

    shared_build_input = {
        "request": request,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    selector_build_input = {
        **shared_build_input,
        "claim_requests": [CUSTOMER_PROOF_SELECTOR_CLAIM],
    }
    selector_build_output = client.build_context(selector_build_input)
    selector_pack = selector_build_output["pack"]
    selector_receipt = selector_build_output["receipt"]
    selector_validation = client.validate_context(
        request,
        selector_pack,
        selector_receipt,
    )
    if selector_validation.get("valid") is not True:
        raise RuntimeError(
            f"Selector context validation did not return valid: {selector_validation}"
        )

    build_input = {
        **shared_build_input,
        "claim_requests": [],
    }
    build_output = client.build_context(build_input)
    pack = build_output["pack"]
    receipt = build_output["receipt"]
    validation = client.validate_context(request, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"Context validation did not return valid: {validation}")

    write_json(SELECTOR_PACK_PATH, selector_pack)
    write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-fsm-12-tool-context-refresh/v1",
            "status": status,
            "describe": describe,
            "reuse_current_discovery": reuse_current_discovery,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "approved_claim_lookup": claim_lookup,
            "customer_proof_claim_lookup": customer_proof_claim_lookup,
            "approved_claim_use_decision": (
                "The customer-proof claim is retained only in the selector-specific pack and "
                "receipt. The final public-copy context has no approved claims because no "
                "connector claim is used in the article. Current official public product pages "
                "support vendor-card descriptions."
            ),
            "selector_build_input": selector_build_input,
            "selector_build_output": selector_build_output,
            "selector_validation": selector_validation,
            "build_input": build_input,
            "build_output": build_output,
            "validation": validation,
        },
        workspace_root=ROOT,
        generated_at=datetime.now(timezone.utc),
    )
    print(
        json.dumps(
            {
                "status": status.get("status"),
                "resource_count": len(RESOURCE_PURPOSES),
                "claim_lookup_rows": len(claim_lookup) if isinstance(claim_lookup, list) else None,
                "selector_pack_sha256": selector_receipt.get("pack_sha256"),
                "selector_receipt_sha256": selector_receipt.get("receipt_sha256"),
                "pack_sha256": receipt.get("pack_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "request_sha256": receipt.get("request_sha256"),
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reuse-current-discovery",
        action="store_true",
        help="Rebind the current task-selected resources after a copy-only article change.",
    )
    args = parser.parse_args()
    main(reuse_current_discovery=args.reuse_current_discovery)
