"""Build connector-bound context artifacts for the new "What Is Simpro?" US blog.

Topic-specific adaptation of scripts/build_women_in_construction_context.py. It writes:

- the context request (simpro-context-request/v1)
- the public-copy context pack and receipt (no approved claims; public claims are
  bound after the draft exists)
- a customer-proof selector pack and receipt carrying one approved claim per
  public URL so the selector can rank real receipt-bound candidates
- a customer-proof claim lookup artifact (simpro-customer-proof-claim-lookup/v1)
  recording complete task-specific SimproVaultClient.claims searches for
  public_metric, exact_quote, and public_paraphrase, because the current
  connector receipt emits an empty claim_searches list
- a Fred authority evaluation pack and receipt carrying Fred authority claim
  requests so the Fred selector can rank real receipt-bound candidates
- the operation trace (status, describe, search, expand, read, claims,
  build_context, validate_context)
"""
from __future__ import annotations

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


SLUG = "what-is-simpro"
DATE = "2026-10-05"
RESEARCH = ROOT / "research"

REQUEST_PATH = RESEARCH / f"context-request-{SLUG}.json"
PACK_PATH = RESEARCH / f"context-pack-{SLUG}.json"
RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}.json"
SELECTOR_PACK_PATH = RESEARCH / f"context-pack-{SLUG}-customer-selector-{DATE}.json"
SELECTOR_RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}-customer-selector-{DATE}.json"
CLAIM_LOOKUP_PATH = RESEARCH / f"customer-proof-claim-lookup-{SLUG}-{DATE}.json"
FRED_PACK_PATH = RESEARCH / f"context-pack-{SLUG}-fred-evaluation-{DATE}.json"
FRED_RECEIPT_PATH = RESEARCH / f"context-receipt-{SLUG}-fred-evaluation-{DATE}.json"
TRACE_PATH = RESEARCH / f"context-refresh-{SLUG}-{DATE}.json"
# --resume reuses selector and Fred packs already written for this DATE and revalidates them.
RESUME = "--resume" in sys.argv

TITLE = "What Is Simpro? What Sets It Apart for Trade Businesses"
OBJECTIVE = (
    "Help US trade business owners and operations leaders understand what Simpro is, "
    "how it runs a job from quote to payment, and what customers say sets it apart, "
    "so they can judge whether it fits their business."
)
AUDIENCE = (
    "US trade business owners, operations leaders and office managers evaluating "
    "field service management software"
)
PRIMARY_KEYWORD = "what is simpro"
CANONICAL_URL = f"https://www.simprogroup.com/blog/{SLUG}"
COMMERCIAL_PILLAR_URL = "https://www.simprogroup.com/"
COMMERCIAL_PILLAR_ANCHOR = "field service management software"
COMMERCIAL_PILLAR_DESTINATION = "simpro-us-homepage-field-service-management-software"

# build_context accepts at most 20 search queries; these are bound into the
# packs and receipts. Every selected resource is returned by these queries.
SEARCH_QUERIES = [
    "COD Editorial Blog Voice",
    "Message House",
    "Product Positioning",
    "Guardrails and Boundaries",
    "Brand usage guide Simpro name spelling",
    "ICP customer personas trade business owner operations manager office manager",
    "Simpro Core Messaging Repository",
    "Core Value Pillars",
    "Field Service Management in the Cloud",
    "Simpro job lifecycle quote schedule mobile invoice reporting",
    "Simpro field service mobile app feature technicians in the field",
    "scheduling software dispatch board feature page",
    "Simpro Trade Services Datasheet",
    "SIMPRO_2410_Implementation Guide_US_Final",
    "2026 Simpro Software Pricing",
    "Simpro Customer Stories",
    "SoftwareWorld 4-5-Star Simpro Review Snippet Refresh",
    "Simpro Lightning AI-first platform status",
    "Lightning Current Commercial and Availability Context",
    "Fred Voccola authority media",
]

# Additional discovery searches recorded in the trace only.
DISCOVERY_ONLY_QUERIES = [
    "Simpro blog voice tone and US localization guidance",
    "Simpro reporting business intelligence feature",
    "Simpro projects project management feature",
    "Simpro integrations accounting",
    "Simpro - Implementation Packages - Smart Start and Premium",
    "RED Electrical case study",
    "Norberg Electric case study",
    "McCarthy Plumbing Group case study",
    "Prime Atlantic Group case study",
    "SL Security Pros case study",
    "Enhanced Electrical case study",
    "Buchanan & Hall case study",
    "Blue Wave Communications case study",
    "Simpro Group company facts headquarters",
]

RESOURCE_PURPOSES = {
    # Voice, tone, and US localization guidance.
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",  # Voice and Tone
    "res-d31f057a305f51918055120d95b76c6a": "guidance",  # Tone Voice and Localization Rules
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",  # COD Editorial Blog Voice - 2026-07-29
    # Product language, category, and value framing.
    "res-230f144aab93512e840167c4a25e60be": "guidance",  # Message House
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",  # Product Positioning
    "res-92348f8056165d4ba81a3c91738604e2": "context",  # Simpro Core Messaging Repository
    "res-ac34fbe2f00a50a69522c0864226ffb8": "context",  # Core Value Pillars
    "res-69b54745e4715d75a655d5c86ba89c59": "guidance",  # Guardrails and Boundaries
    "res-339d828f9b875c738f530a65ccbc3587": "guidance",  # Simpro Group Brand Usage Guide
    # Audience and ICP.
    "res-dfc67c5cef87541d856a765f2747a2cb": "guidance",  # ICP and Customer Archetypes
    "res-09b1f4509ed65855894bd5f481ec81b1": "guidance",  # Simpro Customer Personas
    # Named features, solution, and industry language.
    "res-1825898a11855f89be9bb69c544a6aa3": "guidance",  # Feature Datasheet Atlas
    "res-0dd3c26cb00d5e63b80c10af80d114e1": "context",  # Simpro Trade Services Datasheet - NA July 2026
    "res-c5e0bc9b067157d991bf452e350766ca": "guidance",  # Field Service Management in the Cloud
    # AI and Simpro Lightning boundaries.
    "res-47015608c0d4556a854fca7544b4a040": "guidance",  # AI Positioning And Messaging Rules
    "res-16c113c993565a4c84150d131c034c57": "guidance",  # Lightning Current Commercial And Availability Context
    # Implementation, onboarding, and pricing boundaries.
    "res-6fcbe410d7e65cd487d6212fd0ab4932": "context",  # SIMPRO_2410_Implementation Guide_US_Final.pdf
    "res-3250ad4272305976ab4e7b5dda27309d": "guidance",  # Pricing and Packaging
    # Proof routing and authority.
    "res-c027b4f595a5549b8c29545379e0adf0": "guidance",  # Customer Proof and Quotes
    "res-c37f265e6e385a8b9b4eeb65fb856910": "guidance",  # Simpro Customer Stories
    "res-ad708a5d6b6756d29d81e9cdc7ebca48": "context",  # SoftwareWorld 4-5-Star Simpro Review Snippet Refresh
    "res-15f3055bbe9850d0974573791ce80840": "guidance",  # Fred Voccola Media Authority Hub
}

EXPAND_RESOURCE_IDS = [
    "res-e3ade596be645307ad4c1f84620ce021",
    "res-d31f057a305f51918055120d95b76c6a",
    "res-230f144aab93512e840167c4a25e60be",
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
    "res-69b54745e4715d75a655d5c86ba89c59",
    "res-1825898a11855f89be9bb69c544a6aa3",
    "res-47015608c0d4556a854fca7544b4a040",
    "res-dfc67c5cef87541d856a765f2747a2cb",
]

CONSTRAINTS = [
    "Connector-bound Simpro workflow for a new US commercial-investigation brand explainer blog (workflow_mode new).",
    "Simpro only: no competitor names and no comparison language in public copy, including the words competitor, alternative, vs, and versus.",
    "No leader, leading, best, better, #1, ranked, unparalleled, or other superiority or ranking claims in Simpro's voice.",
    "No customer metrics: the claim registry currently has 0 approved public_metric claims.",
    "No named author, named reviewer, Person author schema, or first-person authority language.",
    "No em dash. US spelling and localization (organization, labor, color, technician, dispatcher).",
    "Frame Simpro as an operating platform for trade and field service businesses that runs work from quote to payment; never as ERP, generic contractor project management, industrial asset management, infrastructure construction software, or an accounting replacement.",
    "Use Simpro (product brand) for product copy; use Simpro Group only for corporate or portfolio context.",
    "The commercial pillar is https://www.simprogroup.com/ with the anchor field service management software (destination simpro-us-homepage-field-service-management-software).",
    "Simpro Lightning may appear only if receipt-approved claims support the exact wording, and always with the full prefix Simpro Lightning; never standalone Lightning.",
    "Pricing, package terms, implementation package names, and commercial details are internal context only unless a current approved public source supports them.",
    "Customer review quotes appear in public copy only as receipt-bound approved exact_quote claims with attribution and the direct public review URL in the same paragraph.",
    "Use Hindsight internal strategy only for angle, section emphasis, and FAQ framing; never as public proof, rankings, metrics, or claims.",
    "Public proof-sensitive claims require an exact use-mode approved-claim query and source verification.",
]

# One approved claim per public URL so selector binding is unambiguous.
# One approved claim per public URL so selector binding is unambiguous.
# Six claims planned for public copy plus three evaluated alternatives.
CUSTOMER_PROOF_SELECTOR_CLAIMS = [
    {
        "claim_id": "claim-metric-MET-1809",
        "query": 'Simpro has made everyone accountable from the very beginning, from the lead and quote stage all the way through to collecting the final payment for the job',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1816",
        "query": 'improved communication between the office and field technicians, streamlined dispatching and scheduling, and given us better visibility into jobs, quotes, inventory, and invoicing',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1302",
        "query": 'We went from carbonless service call forms and a whiteboard calendar to Simpro',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1849",
        "query": 'As an owner, it gives me great real-time insight into my business, from work orders to quotes',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1755",
        "query": 'keeping our quoting, job management, and invoicing tied together in one single source of truth',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1271",
        "query": 'manage quotes, jobs, invoicing, and business reporting efficiently in one place',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1179",
        "query": 'Our business runs on SimPRO. We quote jobs with it, we manage stock and inventory with it',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1033",
        "query": 'covers almost all aspects of running a Plumbing ( or any field service ) Company',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-0299",
        "query": 'powerful all-in-one platform that really helps streamline job management, from quoting through to completion and invoicing',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
]

PUBLIC_COPY_CLAIMS: list[dict[str, str]] = [
    {
        "claim_id": "claim-metric-MET-1809",
        "query": 'Simpro has made everyone accountable from the very beginning, from the lead and quote stage all the way through to collecting the final payment for the job',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1816",
        "query": 'improved communication between the office and field technicians, streamlined dispatching and scheduling, and given us better visibility into jobs, quotes, inventory, and invoicing',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1302",
        "query": 'We went from carbonless service call forms and a whiteboard calendar to Simpro',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1849",
        "query": 'As an owner, it gives me great real-time insight into my business, from work orders to quotes',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1755",
        "query": 'keeping our quoting, job management, and invoicing tied together in one single source of truth',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-metric-MET-1271",
        "query": 'manage quotes, jobs, invoicing, and business reporting efficiently in one place',
        "use_mode": "exact_quote",
        "brand_scope": "Simpro",
    },
]

FRED_EVALUATION_CLAIMS = [
    {
        "claim_id": "claim-fred-FVMI-0210",
        "query": "Fred Voccola: His Simpro Group built AI operating platform for trades",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0206",
        "query": "Interview with Fred Voccola, CEO of Simpro",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-fred-FVMI-0006",
        "query": "Fred Voccola Simpro AI in the Commercial Trades",
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
        "claim_id": "claim-fred-FVMI-0001",
        "query": "Simpro Group CEO on How AI Is Driving SMB Margin Expansion",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]

# Trace-only authority lookup (not bound into any pack).
TRACE_ONLY_AUTHORITY_CLAIMS = [
    {
        "claim_id": "claim-authority-AUTH-0025",
        "query": "Simpro wins 2026 Best in SaaS Award for Best Product in Field Service Management",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]

# Complete task-specific claim searches for the customer proof selector.
PROOF_LOOKUP_REQUESTS = [
    {
        "brand_scope": "Simpro",
        "query": "Simpro trade business customer metric quote to payment scheduling mobile invoicing",
        "use_mode": "public_metric",
        "limit": 50,
    },
    {
        "brand_scope": "Simpro",
        "query": "Simpro one system quoting job management invoicing mobile app technicians implementation support",
        "use_mode": "exact_quote",
        "limit": 50,
    },
    {
        "brand_scope": "Simpro",
        "query": "LCUR-0052",
        "use_mode": "public_paraphrase",
        "limit": 50,
    },
]

REQUEST = {
    "schema": "simpro-context-request/v1",
    "task": f"Build the current connector-bound context for a new Simpro-owned US blog titled {TITLE}.",
    "scope": {
        "brand": "Simpro",
        "market": "US",
        "region": "US",
        "artifact_type": "blog",
        "workflow_mode": "new",
        "topic_slug": SLUG,
        "title": TITLE,
        "canonical_url": CANONICAL_URL,
        "primary_keyword": PRIMARY_KEYWORD,
        "commercial_pillar": {
            "url": COMMERCIAL_PILLAR_URL,
            "anchor": COMMERCIAL_PILLAR_ANCHOR,
            "destination_id": COMMERCIAL_PILLAR_DESTINATION,
        },
        "audience": AUDIENCE,
        "objective": OBJECTIVE,
        "voice_requirements": [
            "current Simpro blog voice and tone",
            "US spelling and localization (organization, labor, technician, dispatcher)",
            "practical, direct, trade-aware, reader-first explainer",
            "no named author",
            "no first-person authority language",
            "no em dash",
        ],
        "product_language_requirements": [
            "Simpro as an operating platform for trade and field service businesses, spanning office and field workflows",
            "quote-to-payment lifecycle language: estimating and quoting, scheduling and dispatch, mobile field execution, invoicing and payments, reporting and job costing",
            "feature names and descriptions drawn from current US vault feature collateral",
            "no ERP, generic project-management, industrial asset, infrastructure construction, or accounting-replacement framing",
            "Simpro Lightning only with receipt-approved claims and the full Simpro Lightning prefix",
            "feature details require relevant source or approved claim evidence",
        ],
        "internal_link_ownership": [
            "The article links https://www.simprogroup.com/ with the anchor field service management software; the homepage owns the general FSM category term.",
            "Feature and solution links use function-bearing anchors and must be checked against connector-discovered feature resources.",
        ],
        "required_context_topics": [
            "current blog voice and tone",
            "US trade-business ICP and personas",
            "core field service management positioning",
            "quote-to-payment job lifecycle",
            "named feature language",
            "implementation and onboarding boundaries",
            "pricing boundaries",
            "Simpro Lightning status boundaries",
            "customer review proof candidates",
            "Fred Voccola authority candidates",
        ],
        "intended_public_use_modes": [
            "guidance",
            "context",
            "exact_quote",
            "public_paraphrase",
            "authority_support",
        ],
        "public_proof_boundary": (
            "Six approved exact_quote review claims are bound in this public-copy context request: "
            "claim-metric-MET-1809, MET-1816, MET-1302, MET-1849 and MET-1271 (G2) and MET-1755 (Capterra), "
            "each quoted verbatim with attribution and the direct public review URL in the same paragraph. "
            "The registry has 0 approved public_metric claims, so no customer metric may appear. No approved "
            "case-study exact_quote claim on a simprogroup.com case-study URL was returned, so case-study "
            "quotes and stories are not connector-approved. The only approved public_paraphrase claim is a "
            "Simpro Lightning product-context row, not customer proof, and is not used. Before drafting any "
            "other proof-sensitive product, feature, pricing, customer, ranking, rating, quote, metric, or "
            "availability statement, retrieve approved claims for that exact proposed use."
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


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def compact_search(rows: Any) -> dict[str, Any]:
    ids = [
        row.get("resource_id")
        for row in rows
        if isinstance(row, dict)
    ] if isinstance(rows, list) else []
    return {
        "result_resource_ids": ids,
        "results_sha256": hashlib.sha256(
            json.dumps(rows, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
    }


def compact_read(read: Any) -> dict[str, Any]:
    if not isinstance(read, dict):
        return {}
    keep = (
        "resource_id", "title", "locator", "content_sha256", "read_purpose",
        "retrieval_tier", "authority_state", "public_claim_use", "content_truncated", "revisions",
    )
    return {key: read.get(key) for key in keep if key in read}


def compact_claims(rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    keep = ("claim_id", "assertion", "permitted_use_modes", "public_url", "source_collection",
            "customer_or_company", "identity", "approval_status", "source_hash")
    return [
        {key: row.get(key) for key in keep if key in row}
        for row in rows
        if isinstance(row, dict)
    ]


def compact_build_output(output: Any) -> dict[str, Any]:
    if not isinstance(output, dict):
        return {}
    receipt = output.get("receipt") if isinstance(output.get("receipt"), dict) else {}
    return {
        "pack_sha256": receipt.get("pack_sha256"),
        "receipt_sha256": receipt.get("receipt_sha256"),
        "request_sha256": receipt.get("request_sha256"),
        "revisions": receipt.get("revisions"),
        "claim_decision_ids": [
            d.get("claim_id") for d in receipt.get("claim_decisions") or [] if isinstance(d, dict)
        ],
        "note": "Full pack and receipt are written to their own research files.",
    }


def relationship_ids_list(value: Any) -> list[dict[str, str]]:
    return [{"resource_id": rid} for rid in sorted(relationship_ids(value))]


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
    print(f"vault_build_context and validate complete: {label}", flush=True)
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


def assert_unique_public_urls(lookups: dict[str, Any], requests: list[dict[str, str]]) -> None:
    urls: dict[str, str] = {}
    for item in requests:
        claim_id = item["claim_id"]
        row = next(
            (r for r in lookups[claim_id] if isinstance(r, dict) and r.get("claim_id") == claim_id),
            None,
        )
        url = str((row or {}).get("public_url") or "")
        if url in urls:
            raise RuntimeError(
                f"Selector claims {urls[url]} and {claim_id} share public_url {url}"
            )
        urls[url] = claim_id


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


def main() -> None:
    write_json(REQUEST_PATH, REQUEST)
    client = SimproVaultClient()

    status = client.status()
    if status.get("status") != "ready":
        raise RuntimeError(f"Vault status is not ready: {status}")
    describe = client.describe()
    print("vault_status and vault_describe complete", flush=True)
    claim_health = describe.get("claim_health") if isinstance(describe, dict) else None
    searches = {}
    for query in SEARCH_QUERIES:
        searches[query] = client.search(query, limit=50)
        print(f"vault_search complete: {query}", flush=True)
    discovery_only_searches = {}
    for query in DISCOVERY_ONLY_QUERIES:
        discovery_only_searches[query] = client.search(query, limit=50)
        print(f"vault_search (discovery only) complete: {query}", flush=True)
    expansions = {}
    for resource_id in EXPAND_RESOURCE_IDS:
        expansions[resource_id] = client.expand(resource_id, purpose=RESOURCE_PURPOSES[resource_id])
        print(f"vault_expand complete: {resource_id}", flush=True)

    discovered_ids: set[str] = set()
    for rows in searches.values():
        discovered_ids.update(result_ids(rows))
    for expansion in expansions.values():
        discovered_ids.update(relationship_ids(expansion))
    missing_ids = sorted(set(RESOURCE_PURPOSES) - discovered_ids)
    if missing_ids:
        raise RuntimeError(f"Selected resource IDs were not rediscovered: {missing_ids}")

    reads = {}
    for resource_id, purpose in RESOURCE_PURPOSES.items():
        reads[resource_id] = client.read(resource_id, purpose=purpose)
        print(f"vault_read complete: {resource_id}", flush=True)

    product_claim_lookup = client.claims(
        "Simpro field service management operating platform quote to payment scheduling mobile app",
        use_mode="public_paraphrase",
        brand_scope="Simpro",
        limit=20,
    )
    lightning_claim_lookup = {
        use_mode: client.claims(
            "Simpro Lightning AI intelligence layer operating platform",
            use_mode=use_mode,
            brand_scope="Simpro",
            limit=20,
        )
        for use_mode in ("public_paraphrase", "exact_quote")
    }
    customer_metric_lookup = client.claims(
        "Simpro customer metric trade business results",
        use_mode="public_metric",
        brand_scope="Simpro",
        limit=50,
    )
    case_study_quote_lookup = {
        query: client.claims(query, use_mode="exact_quote", brand_scope="Simpro", limit=50)
        for query in (
            "RED Electrical",
            "Norberg Electric",
            "McCarthy Plumbing Group",
            "Prime Atlantic Group",
            "SL Security Pros",
            "Enhanced Electrical",
            "Buchanan & Hall",
            "Blue Wave Communications",
        )
    }
    case_study_quote_hits = {
        query: [
            row.get("claim_id")
            for row in rows
            if isinstance(row, dict) and "simprogroup.com" in str(row.get("public_url") or "")
        ]
        for query, rows in case_study_quote_lookup.items()
    }
    customer_proof_claim_lookup = lookup_claims(client, CUSTOMER_PROOF_SELECTOR_CLAIMS)
    assert_unique_public_urls(customer_proof_claim_lookup, CUSTOMER_PROOF_SELECTOR_CLAIMS)
    fred_claim_lookup = lookup_claims(client, FRED_EVALUATION_CLAIMS)
    trace_only_authority_lookup = lookup_claims(client, TRACE_ONLY_AUTHORITY_CLAIMS)
    claim_lookup_artifact = build_lookup_artifact(client)
    print("vault_claims lookups complete", flush=True)

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
    if RESUME and SELECTOR_PACK_PATH.exists() and SELECTOR_RECEIPT_PATH.exists():
        selector_pack = json.loads(SELECTOR_PACK_PATH.read_text(encoding="utf-8"))
        selector_receipt = json.loads(SELECTOR_RECEIPT_PATH.read_text(encoding="utf-8"))
        selector_output = {"pack": selector_pack, "receipt": selector_receipt}
        selector_validation = client.validate_context(REQUEST, selector_pack, selector_receipt)
        if selector_validation.get("valid") is not True:
            raise RuntimeError(f"Saved selector context no longer validates: {selector_validation}")
        print("selector pack reused and revalidated", flush=True)
    else:
        selector_output, selector_pack, selector_receipt, selector_validation = build_and_validate(
            client, selector_build_input, "Customer-proof selector"
        )
        write_json(SELECTOR_PACK_PATH, selector_pack)
        write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
        write_json(CLAIM_LOOKUP_PATH, claim_lookup_artifact)
        print("selector pack and receipt written", flush=True)

    fred_build_input = {**shared_build_input, "claim_requests": FRED_EVALUATION_CLAIMS}
    if RESUME and FRED_PACK_PATH.exists() and FRED_RECEIPT_PATH.exists():
        fred_pack = json.loads(FRED_PACK_PATH.read_text(encoding="utf-8"))
        fred_receipt = json.loads(FRED_RECEIPT_PATH.read_text(encoding="utf-8"))
        fred_output = {"pack": fred_pack, "receipt": fred_receipt}
        fred_validation = client.validate_context(REQUEST, fred_pack, fred_receipt)
        if fred_validation.get("valid") is not True:
            raise RuntimeError(f"Saved Fred context no longer validates: {fred_validation}")
        print("fred pack reused and revalidated", flush=True)
    else:
        fred_output, fred_pack, fred_receipt, fred_validation = build_and_validate(
            client, fred_build_input, "Fred evaluation"
        )
        write_json(FRED_PACK_PATH, fred_pack)
        write_json(FRED_RECEIPT_PATH, fred_receipt)
        print("fred pack and receipt written", flush=True)

    build_input = {**shared_build_input, "claim_requests": PUBLIC_COPY_CLAIMS}
    build_output, pack, receipt, validation = build_and_validate(
        client, build_input, "Public-copy"
    )
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    print("public pack and receipt written", flush=True)

    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-what-is-simpro-context-refresh/v1",
            "status": status,
            "describe": {k: describe.get(k) for k in ("schema", "capabilities", "claim_health")} if isinstance(describe, dict) else describe,
            "searches": {q: compact_search(r) for q, r in searches.items()},
            "discovery_only_searches": {q: compact_search(r) for q, r in discovery_only_searches.items()},
            "expansions": {rid: compact_search(relationship_ids_list(e)) for rid, e in expansions.items()},
            "reads": {rid: compact_read(r) for rid, r in reads.items()},
            "approved_claim_lookup": compact_claims(product_claim_lookup),
            "lightning_claim_lookup": {m: compact_claims(r) for m, r in lightning_claim_lookup.items()},
            "customer_metric_lookup": compact_claims(customer_metric_lookup),
            "case_study_quote_lookup": {q: [x.get("claim_id") for x in compact_claims(r)] for q, r in case_study_quote_lookup.items()},
            "case_study_quote_simprogroup_hits": case_study_quote_hits,
            "customer_proof_claim_lookup": {c: compact_claims(r) for c, r in customer_proof_claim_lookup.items()},
            "fred_authority_claim_lookup": {c: compact_claims(r) for c, r in fred_claim_lookup.items()},
            "trace_only_authority_claim_lookup": {c: compact_claims(r) for c, r in trace_only_authority_lookup.items()},
            "claim_lookup_artifact": {
                "path": CLAIM_LOOKUP_PATH.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(CLAIM_LOOKUP_PATH),
            },
            "approved_claim_use_decision": (
                "The customer-selector pack binds one approved exact_quote claim per public URL: the six "
                "review claims planned for public copy (MET-1809, MET-1816, MET-1302, MET-1849 and MET-1271 "
                "on G2, MET-1755 on Capterra) plus three evaluated alternatives (MET-1179, MET-1033, "
                "MET-0299). The registry single approved public_paraphrase claim, "
                "claim-lightning-LCUR-0052, is Simpro Lightning product context rather than customer proof, "
                "so it is not bound. MET-1300 was excluded for superlative wording (unparalleled) and "
                "MET-0337 for comparative wording. Older Capterra rows (MET-0442, MET-0463, MET-0283) were "
                "not used because their quotes are not visible on the vault public URL. The registry has 0 "
                "approved public_metric claims and returned no approved case-study exact_quote claim on a "
                "simprogroup.com URL. The public-copy context binds the six planned review claims. Fred "
                "authority claims stay in the Fred evaluation pack and receipt. AUTH-0025 is recorded in "
                "this trace only."
            ),
            "selector_build_input": selector_build_input,
            "selector_build_output": compact_build_output(selector_output),
            "selector_validation": selector_validation,
            "fred_build_input": fred_build_input,
            "fred_build_output": compact_build_output(fred_output),
            "fred_validation": fred_validation,
            "build_input": build_input,
            "build_output": compact_build_output(build_output),
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
                "claim_health": claim_health,
                "resource_count": len(RESOURCE_PURPOSES),
                "product_claim_lookup_rows": (
                    len(product_claim_lookup) if isinstance(product_claim_lookup, list) else None
                ),
                "customer_metric_lookup_rows": (
                    len(customer_metric_lookup) if isinstance(customer_metric_lookup, list) else None
                ),
                "case_study_quote_simprogroup_hits": case_study_quote_hits,
                "selector_pack_sha256": selector_receipt.get("pack_sha256"),
                "selector_receipt_sha256": selector_receipt.get("receipt_sha256"),
                "claim_lookup_file_sha256": sha256_file(CLAIM_LOOKUP_PATH),
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
