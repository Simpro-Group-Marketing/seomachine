"""Build connector-bound context artifacts for the women-in-construction rewrite.

Topic-specific adaptation of scripts/build_trade_jobs_ca_context.py. It writes:

- the context request (simpro-context-request/v1)
- the public-copy context pack and receipt (no approved claims, because no
  connector claim is planned for public copy at context-build time)
- a customer-proof selector pack and receipt carrying claim_requests so the
  selector can rank real receipt-bound candidates
- a Fred authority evaluation pack and receipt carrying Fred authority claim
  requests so the Fred selector can rank real receipt-bound candidates
- the operation trace (status, describe, search, expand, read, claims,
  build_context, validate_context)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient
from data_sources.modules.artifact_runtime.content_store import write_context_trace


SLUG = "women-in-construction"
DATE = "2026-09-26"
RESEARCH = ROOT / "research"

REQUEST_PATH = RESEARCH / f"context-request-{SLUG}.json"
PACK_PATH = RESEARCH / f"context-pack-{SLUG}.json"
RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}.json"
SELECTOR_PACK_PATH = RESEARCH / f"context-pack-{SLUG}-customer-selector-{DATE}.json"
SELECTOR_RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}-customer-selector-{DATE}.json"
FRED_PACK_PATH = RESEARCH / f"context-pack-{SLUG}-fred-evaluation-{DATE}.json"
FRED_RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}-fred-evaluation-{DATE}.json"
TRACE_PATH = RESEARCH / f"context-refresh-{SLUG}-{DATE}.json"

TITLE = (
    "Bridging the Trades Labor Gap: A Contractor's Guide to Attracting and "
    "Retaining Women in Construction"
)
OBJECTIVE = (
    "Help US trade contractors close skilled-labor gaps by attracting, developing, "
    "and retaining women across field and office roles, using jobsite technology, "
    "transparent career pathways, and connected field service software."
)
AUDIENCE = "US trade contractor owners and operations leaders"

SEARCH_QUERIES = [
    "Simpro blog voice tone and US localization guidance for an educational guide with no named author",
    "Simpro core messaging and field service management software positioning for trade contractors",
    "Message House",
    "Product Positioning",
    "Guardrails and Boundaries",
    "Brand usage guide Simpro name spelling",
    "people retention technician workload burnout visibility",
    "skilled labor shortage workforce recruitment retention trade contractors",
    "women in trades women in construction",
    "ICP customer archetypes owner operator operations manager",
    "Simpro scheduling software feature dispatch board technician scheduling",
    "feature naming rules Simpro Mobile scheduling",
    "Simpro field service mobile app feature technicians in the field",
    "job costing reporting feature",
    "construction commercial contractor vertical solution guidance",
    "construction trades vertical profile",
    "Foster Plumbing Amy Carnrick",
    "Virtual FM Virtual Services Group Dawn Lawrie",
    "Vertac Wellington Frances Paku",
    "Fred Voccola skilled trades workforce authority media",
]

RESOURCE_PURPOSES = {
    # Voice, tone, localization, editorial blog voice
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",  # Voice and Tone
    "res-d31f057a305f51918055120d95b76c6a": "guidance",  # Tone Voice and Localization Rules
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",  # COD Editorial Blog Voice - 2026-07-29
    "res-339d828f9b875c738f530a65ccbc3587": "guidance",  # Simpro Group Brand Usage Guide
    # Core messaging, message house, product positioning, guardrails, pillars
    "res-09ebfff123cb5c5496e60c3a759a263d": "context",  # Simpro Core Messaging Repository - 05132026
    "res-230f144aab93512e840167c4a25e60be": "guidance",  # Message House
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",  # Product Positioning
    "res-69b54745e4715d75a655d5c86ba89c59": "guidance",  # Guardrails and Boundaries
    "res-ac34fbe2f00a50a69522c0864226ffb8": "context",  # Core Value Pillars
    # Audience
    "res-dfc67c5cef87541d856a765f2747a2cb": "guidance",  # ICP and Customer Archetypes
    "res-09b1f4509ed65855894bd5f481ec81b1": "guidance",  # Simpro Customer Personas
    # Feature context: scheduling and dispatching, mobile field workflows
    "res-1825898a11855f89be9bb69c544a6aa3": "context",  # Feature Datasheet Atlas
    "res-33deaefa546b56358549b9dfe84f72c6": "context",  # Simpro Datasheet (NA).pdf
    "res-f882ab230eb2563889e300d612c324bc": "context",  # Simpro Trade Services datasheet (US)
    # Trades and vertical scope
    "res-cb1c8e417b42532cb65e6e59893cf459": "context",  # Vertical Profile Library (wiki)
    "res-ae4607729666509bb97813e66e18590b": "context",  # Simpro Group Vertical Profile Library - 06082026
    # Customer proof routing context only (never public proof by itself)
    "res-6716e1bab324565aa8a906b05b0aa502": "context",  # Quotes
}

EXPAND_RESOURCE_IDS = [
    "res-e3ade596be645307ad4c1f84620ce021",
    "res-d31f057a305f51918055120d95b76c6a",
    "res-230f144aab93512e840167c4a25e60be",
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
    "res-1825898a11855f89be9bb69c544a6aa3",
    "res-cb1c8e417b42532cb65e6e59893cf459",
    "res-dfc67c5cef87541d856a765f2747a2cb",
]

CONSTRAINTS = [
    "Connector-bound Simpro rewrite workflow for a US commercial-investigation workforce guide.",
    "No named author, named reviewer, Person author schema, first-person authority language, or em dash.",
    "The legacy URL https://www.simprogroup.com/blog/women-in-construction-week is rewritten to the new slug https://www.simprogroup.com/blog/women-in-construction.",
    "The commercial pillar is https://www.simprogroup.com/ with the anchor field service management software (destination simpro-us-homepage-field-service-management-software).",
    "Frame Simpro as software for trade contractors who self-perform field work; never as general contractor project management, infrastructure construction software, or ERP.",
    "Feature links use function-bearing anchors to https://www.simprogroup.com/features/scheduling-software and https://www.simprogroup.com/features/field-service-mobile-app; no feature superiority, availability, or outcome claim.",
    "Frame field technology as support for technicians, not surveillance or micromanagement.",
    "Workforce, labor-shortage, demographic, apprenticeship, and pay facts require current authoritative non-owned public sources; vault resources are voice, positioning, and feature-language context only.",
    "Customer proof (Foster Plumbing, Virtual Services Group, Vertac Wellington) is used in public copy only through selector-bound, receipt-approved claims and source-visible public pages.",
    "Use Hindsight internal strategy only for section depth, feature emphasis, and CTA audience framing; never as public claim support.",
    "Public proof-sensitive claims require an exact use-mode approved-claim query and source verification.",
]

CUSTOMER_PROOF_SELECTOR_CLAIMS = [
    {
        "claim_id": "claim-metric-MET-0178",
        "query": "Foster Plumbing revenue grew from $1 million to $10 million",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1517",
        "query": "Enhanced Electrical technician team grew 2.5X from eight to 21",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1515",
        "query": "Shaffer Beacon Mechanical field-technician team increased by 40% with no office-staff increase",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1524",
        "query": "LDN Security Solutions team grew from three to 10 employees",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
]

PUBLIC_COPY_CLAIMS = [
    {
        "claim_id": "claim-metric-MET-0178",
        "query": "Foster Plumbing revenue grew from $1 million to $10 million",
        "use_mode": "public_metric",
        "brand_scope": "Simpro",
    },
]

FRED_EVALUATION_CLAIMS = [
    {
        "claim_id": "claim-fred-FVMI-0005",
        "query": "Fred Voccola on AI's Role in Revitalizing the Skilled Trades",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0207",
        "query": "Fred Voccola on AI in Skilled Trades, Digital Workforces & the Coming Robotics Boom",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0209",
        "query": "Fred Voccola: AI Is the Workforce's New Digital Colleague",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0004",
        "query": "Even blue-collar work isn't safe from AI, a CEO who makes tech for electricians and plumbers says",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0007",
        "query": "Smarter Jobsites: How AI Is Rewiring the Trades",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]

REQUEST = {
    "schema": "simpro-context-request/v1",
    "task": f"Build the current connector-bound context for a Simpro-owned US rewrite titled {TITLE}.",
    "scope": {
        "brand": "Simpro",
        "market": "US",
        "region": "US",
        "artifact_type": "blog",
        "workflow_mode": "rewrite",
        "title": TITLE,
        "canonical_url": f"https://www.simprogroup.com/blog/{SLUG}",
        "legacy_url": "https://www.simprogroup.com/blog/women-in-construction-week",
        "audience": AUDIENCE,
        "objective": OBJECTIVE,
        "voice_requirements": [
            "current Simpro blog voice and tone",
            "US spelling and localization (labor, organization, technician, dispatcher)",
            "practical, trade-aware, reader-first contractor guidance",
            "no named author",
            "no first-person authority language",
            "no em dash",
        ],
        "product_language_requirements": [
            "current Simpro field service management software positioning for trade contractors",
            "scheduling and dispatching language drawn from vault feature collateral",
            "mobile field workflow language drawn from vault feature collateral and personas",
            "technology framed as support for technicians, not surveillance",
            "trade contractor scope: self-performing trades, not general contractors or infrastructure construction",
            "feature details require relevant source or approved claim evidence",
        ],
        "internal_link_ownership": [
            "The article links https://www.simprogroup.com/ with the anchor field service management software; the homepage owns the general FSM category term.",
            "Feature links: https://www.simprogroup.com/features/scheduling-software and https://www.simprogroup.com/features/field-service-mobile-app with function-bearing anchors.",
        ],
        "intended_public_use_modes": [
            "guidance",
            "context",
            "public_paraphrase",
            "exact_quote",
            "public_metric",
            "authority_support",
        ],
        "public_proof_boundary": (
            "One public proof claim is bound in this public-copy context request: "
            "claim-metric-MET-0178 (Foster Plumbing revenue grew from $1 million to $10 million), "
            "used once as a public_metric with a same-paragraph link to "
            "https://www.simprogroup.com/case-studies/foster-plumbing. Workforce, "
            "labor-shortage, demographic, apprenticeship, and pay facts come from current "
            "authoritative public sources. Before drafting any proof-sensitive product, feature, "
            "pricing, customer, ranking, rating, quote, metric, or availability statement, "
            "retrieve approved claims for that exact proposed use."
        ),
        "retrieval_evidence": {
            "expansion_artifact": TRACE_PATH.relative_to(ROOT).as_posix(),
            "expanded_source_resource_ids": EXPAND_RESOURCE_IDS,
            "expansion_followed_by_reads": sorted(RESOURCE_PURPOSES),
        },
    },
    "requested_at": DATE,
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


def build_and_validate(
    client: SimproVaultClient,
    build_input: dict[str, Any],
    label: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    output = client.build_context(build_input)
    pack = output["pack"]
    receipt = output["receipt"]
    validation = client.validate_context(REQUEST, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"{label} context validation did not return valid: {validation}")
    return output, pack, receipt, validation


def lookup_claims(client: SimproVaultClient, requests: list[dict[str, str]]) -> dict[str, Any]:
    lookups: dict[str, Any] = {}
    for item in requests:
        rows = client.claims(
            item["query"],
            use_mode=item["use_mode"],
            brand_scope=item["brand_scope"],
            limit=20,
        )
        found = {
            row.get("claim_id")
            for row in rows
            if isinstance(row, dict)
        } if isinstance(rows, list) else set()
        if item["claim_id"] not in found:
            raise RuntimeError(
                f"Approved claim {item['claim_id']} was not returned for its exact use-mode query"
            )
        lookups[item["claim_id"]] = rows
    return lookups


def main() -> None:
    write_json(REQUEST_PATH, REQUEST)
    client = SimproVaultClient()

    status = client.status()
    if status.get("status") != "ready":
        raise RuntimeError(f"Vault status is not ready: {status}")
    describe = client.describe()
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
    product_claim_lookup = client.claims(
        "Simpro field service management software scheduling and mobile app for trade contractors",
        use_mode="public_paraphrase",
        brand_scope="Simpro",
        limit=20,
    )
    customer_story_claim_lookup = {
        query: client.claims(query, use_mode=use_mode, brand_scope="Simpro", limit=20)
        for query, use_mode in (
            ("Amy Carnrick Foster Plumbing", "exact_quote"),
            ("Dawn Lawrie Virtual Services Group", "exact_quote"),
            ("Vertac Wellington Frances Paku", "exact_quote"),
        )
    }
    customer_proof_claim_lookup = lookup_claims(client, CUSTOMER_PROOF_SELECTOR_CLAIMS)
    fred_claim_lookup = lookup_claims(client, FRED_EVALUATION_CLAIMS)

    shared_build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }

    selector_build_input = {**shared_build_input, "claim_requests": CUSTOMER_PROOF_SELECTOR_CLAIMS}
    selector_output, selector_pack, selector_receipt, selector_validation = build_and_validate(
        client, selector_build_input, "Customer-proof selector"
    )

    fred_build_input = {**shared_build_input, "claim_requests": FRED_EVALUATION_CLAIMS}
    fred_output, fred_pack, fred_receipt, fred_validation = build_and_validate(
        client, fred_build_input, "Fred evaluation"
    )

    build_input = {**shared_build_input, "claim_requests": PUBLIC_COPY_CLAIMS}
    build_output, pack, receipt, validation = build_and_validate(
        client, build_input, "Public-copy"
    )

    write_json(SELECTOR_PACK_PATH, selector_pack)
    write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
    write_json(FRED_PACK_PATH, fred_pack)
    write_json(FRED_RECEIPT_PATH, fred_receipt)
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-women-in-construction-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "approved_claim_lookup": product_claim_lookup,
            "customer_story_claim_lookup": customer_story_claim_lookup,
            "customer_proof_claim_lookup": customer_proof_claim_lookup,
            "fred_authority_claim_lookup": fred_claim_lookup,
            "approved_claim_use_decision": (
                "The customer-selector pack binds one Foster Plumbing claim (MET-0178) per public "
                "URL to avoid ambiguous URL binding. The public-copy context carries only "
                "MET-0178, the single customer metric used in public copy. Fred authority claims "
                "stay in the Fred evaluation pack and receipt. No "
                "connector claim exists for the toolbox-tech webinar, Heroes of the Trade Dawn "
                "Lawrie, or Heroes of the Trade Vertac pages, so those quotes are not "
                "connector-approved. Workforce and labor facts come from current authoritative "
                "public sources."
            ),
            "selector_build_input": selector_build_input,
            "selector_build_output": selector_output,
            "selector_validation": selector_validation,
            "fred_build_input": fred_build_input,
            "fred_build_output": fred_output,
            "fred_validation": fred_validation,
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
                "revisions": status.get("revisions"),
                "resource_count": len(RESOURCE_PURPOSES),
                "product_claim_lookup_rows": (
                    len(product_claim_lookup) if isinstance(product_claim_lookup, list) else None
                ),
                "customer_story_claim_rows": {
                    query: len(rows) if isinstance(rows, list) else None
                    for query, rows in customer_story_claim_lookup.items()
                },
                "selector_pack_sha256": selector_receipt.get("pack_sha256"),
                "selector_receipt_sha256": selector_receipt.get("receipt_sha256"),
                "fred_pack_sha256": fred_receipt.get("pack_sha256"),
                "fred_receipt_sha256": fred_receipt.get("receipt_sha256"),
                "pack_sha256": receipt.get("pack_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "request_sha256": receipt.get("request_sha256"),
                "receipt_revisions": receipt.get("revisions"),
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
