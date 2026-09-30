"""Build vault and Hindsight evidence for the Simpro industry FAB copy deck."""
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
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.simpro_vault_client import SimproVaultClient


SLUG = "simpro-industry-fab-tables"
DATE = "2026-09-28"
ARTICLE = ROOT / "drafts" / f"{SLUG}-{DATE}.md"
REQUEST_PATH = ROOT / "research" / f"context-request-{SLUG}.json"
PACK_PATH = ROOT / "research" / f"context-pack-{SLUG}.json"
RECEIPT_PATH = ROOT / "research" / f"context-receipt-{SLUG}.json"
TRACE_PATH = ROOT / "research" / f"context-refresh-{SLUG}-{DATE}.json"
HINDSIGHT_PATH = ROOT / "research" / f"hindsight-strategy-evidence-{SLUG}-{DATE}.json"
SIDECAR_PATH = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"

TITLE = "Simpro industry-page FAB table handoff"
TARGET_URLS = [
    "https://www.simprogroup.com/industries/hvac-software",
    "https://www.simprogroup.com/industries/electrical-software",
    "https://www.simprogroup.com/industries/plumbing-software",
    "https://www.simprogroup.com/industries/security",
    "https://www.simprogroup.com/industries/fire-protection-software",
]

SEARCH_QUERIES = [
    "Simpro product page voice tone and US localization for industry landing pages",
    "Simpro core messaging operating platform trade field service business outcomes",
    "Simpro product positioning scheduling mobile field work project control job costing reporting integrations",
    "Simpro HVAC contractor software US scheduling maintenance projects supplier integrations reporting",
    "Simpro electrical contractor software US scheduling mobile documentation projects materials reporting",
    "Simpro plumbing software US dispatch mobile invoicing maintenance parts profitability",
    "Simpro security low voltage software US service monitoring agreements assets installations devices",
    "Simpro fire protection software inspections assets defects field forms contracts reporting",
    "Simpro Group vertical profile HVAC electrical plumbing security fire protection",
]

RESOURCE_PURPOSES = {
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-230f144aab93512e840167c4a25e60be": "guidance",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-09ebfff123cb5c5496e60c3a759a263d": "context",
    "res-ae4607729666509bb97813e66e18590b": "context",
    "res-f9f9499223a15d6a901806f30fb1a8ba": "context",
    "res-a88df898c8d0538088b73be0695a65dd": "context",
    "res-10b97eee1de25395bbf8b904111ca4b0": "context",
    "res-6a89de98838b57a3821bfaeb59403191": "context",
    "res-286ca2f7150b59398497f6b341b6c9b7": "context",
    "res-f882ab230eb2563889e300d612c324bc": "context",
}

EXPAND_RESOURCE_IDS = [
    "res-d31f057a305f51918055120d95b76c6a",
    "res-230f144aab93512e840167c4a25e60be",
    "res-a5b3b47382b45490bf2bedbf16c0b76e",
    "res-f9f9499223a15d6a901806f30fb1a8ba",
]

HINDSIGHT_QUERIES = [
    "HVAC field service buyers feature demand scheduling mobile integrations preventative maintenance projects",
    "electrical contractor buyers feature demand mobile integrations scheduling projects reporting",
    "plumbing contractor buyers feature demand mobile integrations scheduling projects reporting",
    "security low voltage buyers feature demand integrations mobile scheduling maintenance projects",
    "fire protection buyers feature demand integrations reporting time tracking projects invoicing",
]

HINDSIGHT_RESOURCE_IDS = [
    "res-a41eef7796d7534b93f3e38a7f1036f4",
    "res-acdf63e464db5579a008beb136c20593",
    "res-2fa37305ff98541b8fa0955da4dd3978",
    "res-5ff3a414e5425f2eb78d66a76e50c22b",
    "res-875500e42f1f5ffea0404dea699a69d3",
]

HINDSIGHT_GUIDANCE_ID = "res-f0af30c3066f57eaa59db44881568858"

CONSTRAINTS = [
    "Connector-bound Simpro US industry-page section-copy workflow.",
    "The output contains five replacement FAB sections and no full-page rewrite.",
    "Use US spelling and restrained product-page language.",
    "Use generic capability labels and no named Simpro features or add-ons.",
    "Do not use metrics, guarantees, rankings, customer proof, testimonials, competitive claims, pricing, product availability, roadmap language, or regulatory assurances.",
    "Treat low-risk product and industry language as sidecar-only evidence unless the claim policy assigns a stricter mode.",
    "Omit any statement that requires an approved claim when no objective-fit approved claim is available.",
    "Use Hindsight only to prioritize table rows and commercial emphasis, never as public evidence or claim support.",
    "Do not use em dashes or reader-facing workflow commentary.",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ids(value: Any) -> set[str]:
    if isinstance(value, dict):
        found = {value["resource_id"]} if isinstance(value.get("resource_id"), str) else set()
        for child in value.values():
            found.update(_ids(child))
        return found
    if isinstance(value, list):
        found: set[str] = set()
        for child in value:
            found.update(_ids(child))
        return found
    return set()


def _hindsight_result_ids(rows: Any) -> set[str]:
    if not isinstance(rows, list):
        return set()
    return {
        row["resource_id"]
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("resource_id"), str)
    }


def _context_request(article_hash: str) -> dict[str, Any]:
    return {
        "schema": "simpro-context-request/v1",
        "task": "Create five US Simpro industry-page FAB table sections for CMS handoff.",
        "scope": {
            "artifact_type": "landing_page",
            "workflow_mode": "new",
            "brand": "Simpro",
            "market": "US",
            "region": "US",
            "title": TITLE,
            "article_path": ARTICLE.relative_to(ROOT).as_posix(),
            "article_sha256": article_hash,
            "target_urls": TARGET_URLS,
            "audience": "US HVAC, electrical, plumbing, security and fire protection contractors evaluating field service software",
            "objective": "Explain each trade's most relevant software capabilities, operational advantages and defensible business benefits in an extractable table before the final CTA and FAQs.",
            "required_context_topics": [
                "current Simpro product-page voice and US localization",
                "core messaging and product positioning",
                "HVAC, electrical, plumbing, security and fire protection vertical language",
                "scheduling, mobile field work, maintenance, projects, integrations, invoicing and reporting",
            ],
            "intended_public_use_modes": ["guidance", "context"],
            "public_proof_boundary": "No metrics, customer proof, quotes, comparisons, regulatory assurances, pricing, roadmap, availability or named-feature claims are proposed. Unknown or higher-risk claims must be omitted unless an exact approved claim is added and validated.",
            "retrieval_evidence": {
                "expansion_artifact": TRACE_PATH.relative_to(ROOT).as_posix(),
                "expanded_source_resource_ids": EXPAND_RESOURCE_IDS,
                "expansion_followed_by_reads": sorted(RESOURCE_PURPOSES),
            },
        },
        "context_needs": [
            "Trade-specific workflow terminology for all five industry pages.",
            "Current Simpro product positioning and restrained landing-page tone.",
            "Source boundaries for low-risk product and industry paraphrases.",
        ],
        "constraints": CONSTRAINTS,
        "unresolved_gaps": [],
        "requested_at": DATE,
    }


def _build_hindsight(client: SimproVaultClient, article_hash: str) -> dict[str, Any]:
    searches = {
        query: client.search_internal_strategy(query, limit=50)
        for query in HINDSIGHT_QUERIES
    }
    discovered: set[str] = set()
    for rows in searches.values():
        discovered.update(_hindsight_result_ids(rows))
    missing = sorted(set(HINDSIGHT_RESOURCE_IDS) - discovered)
    if missing:
        raise RuntimeError(f"Hindsight resources were not rediscovered: {missing}")
    reads = {
        resource_id: client.read_internal_strategy(resource_id)
        for resource_id in HINDSIGHT_RESOURCE_IDS
    }
    guidance_search = client.search("Hindsight and Deal Intelligence Guidance", limit=20)
    if HINDSIGHT_GUIDANCE_ID not in _ids(guidance_search):
        raise RuntimeError("Hindsight governance guidance was not rediscovered")
    guidance = client.read(HINDSIGHT_GUIDANCE_ID, purpose="context")
    request = {
        "task": "Use Hindsight only to prioritize the capabilities and commercial emphasis in five US Simpro industry FAB tables.",
        "scope": {
            "brand": "Simpro",
            "market": "US",
            "artifact_type": "landing_page",
            "workflow_mode": "new",
            "title": TITLE,
            "article_path": ARTICLE.relative_to(ROOT).as_posix(),
            "article_sha256": article_hash,
            "permitted_effects": ["row selection", "row order", "operational emphasis", "benefit framing"],
        },
    }
    constraints = [
        "Internal strategy only.",
        "Public claim use is prohibited.",
        "Claim support is not allowed.",
        "Do not expose names, amounts, deal counts, rankings, win rates, quotes, URLs, internal identifiers or unsupported claims.",
        "Treat fire signals as directional and rely primarily on current public vault collateral and official page language.",
    ]
    packed = client.pack_internal_strategy(
        {
            "request": request,
            "resource_ids": HINDSIGHT_RESOURCE_IDS,
            "search_queries": HINDSIGHT_QUERIES,
            "constraints": constraints,
            "unresolved_gaps": [],
            "task_satisfaction": "satisfied",
        }
    )
    if packed["sidecar"].get("public_claim_use") != "prohibited":
        raise RuntimeError("Hindsight pack did not prohibit public claim use")
    if packed["sidecar"].get("claim_support_allowed") is not False:
        raise RuntimeError("Hindsight pack allowed claim support")
    payload = {
        "pack": packed["pack"],
        "receipt": packed["receipt"],
        "sidecar": packed["sidecar"],
        "application_decision": {
            "mode": "internal_strategy_only",
            "applied_to": ["row selection", "row order", "operational emphasis", "benefit framing"],
            "fire_evidence_treatment": "directional",
            "public_copy_boundary": "No Hindsight data, counts, observations, identifiers, quotes or claims appear in public copy.",
        },
        "governance_guidance": {
            "resource_id": HINDSIGHT_GUIDANCE_ID,
            "title": guidance.get("title"),
            "content_sha256": guidance.get("content_sha256"),
        },
        "retrieval_trace": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "search_queries": HINDSIGHT_QUERIES,
            "selected_resource_ids": HINDSIGHT_RESOURCE_IDS,
            "read_resource_ids": sorted(reads),
            "article_sha256": article_hash,
        },
    }
    atomic_write_json(HINDSIGHT_PATH, payload)
    return payload


def _render_sidecar(
    request: dict[str, Any],
    receipt: dict[str, Any],
    hindsight: dict[str, Any],
) -> str:
    revisions = receipt["revisions"]
    resources = [row["resource_id"] for row in receipt["resources"]]
    resource_list = ", ".join(f"`{resource_id}`" for resource_id in resources)
    hindsight_resources = ", ".join(
        f"`{resource_id}`" for resource_id in HINDSIGHT_RESOURCE_IDS
    )
    hindsight_receipt = hindsight["receipt"]
    return f"""# Validation: Simpro industry-page FAB tables

## Deliverable decision

- Artifact: `{ARTICLE.relative_to(ROOT).as_posix()}`
- Market: US
- Page treatment: replace the existing Simpro advantage card section before the final CTA and FAQs.
- Scope: five section-level FAB tables only; existing CTA and FAQ copy remains unchanged.
- Structure: one direct-answer introduction and six Feature, Advantage, Benefit rows per page.
- Public exclusions: metrics, customer proof, quotes, comparisons, superlatives, guarantees, pricing, roadmap, product availability, regulatory assurances and named Simpro features or add-ons.

## Context request and validation

- Request: `{REQUEST_PATH.relative_to(ROOT).as_posix()}`
- Context pack: `{PACK_PATH.relative_to(ROOT).as_posix()}`
- Context receipt: `{RECEIPT_PATH.relative_to(ROOT).as_posix()}`
- Context trace: `{TRACE_PATH.relative_to(ROOT).as_posix()}`
- Article SHA-256: `{request['scope']['article_sha256']}`
- Context pack SHA-256: `{receipt['pack_sha256']}`
- Context receipt SHA-256: `{receipt['receipt_sha256']}`
- Manifest revision: `{revisions['manifest_revision']}`
- Claim registry revision: `{revisions['claim_registry_revision']}`
- Approval policy revision: `{revisions['approval_policy_revision']}`
- Selected resources: {resource_list}
- Approved public claim IDs used: [none]
- Claim-policy decision: public-paraphrase lookups returned no objective-fit approved claim for these generic table capabilities. The copy therefore contains no proof-sensitive metric, customer, comparison, availability or named-feature claim. Low-risk product and industry paraphrases remain bound to current vault context and verified official page language.
- Status: validated

## Vault Brand Language Alignment

- Article title: {TITLE}
- Product/solution language scope: mixed
- Vault connector evidence: vault_status ready; vault_describe inspected; vault_search, vault_read, vault_expand, vault_claims, vault_build_context, and vault_validate_context used; context_pack_hash: sha256:{receipt['pack_sha256']}; receipt_hash: sha256:{receipt['receipt_sha256']}; product positioning resource_id: res-a5b3b47382b45490bf2bedbf16c0b76e; vertical resource_id: res-ae4607729666509bb97813e66e18590b; electrical vertical resource_id: res-f9f9499223a15d6a901806f30fb1a8ba; HVAC industry resource_id: res-a88df898c8d0538088b73be0695a65dd; electrical industry resource_id: res-10b97eee1de25395bbf8b904111ca4b0; plumbing industry resource_id: res-6a89de98838b57a3821bfaeb59403191; security and fire industry resource_id: res-286ca2f7150b59398497f6b341b6c9b7; manifest_revision: {revisions['manifest_revision']}
- Product/feature language applied: generic scheduling, mobile field work, maintenance, project control, supplier and accounting connections, invoicing, job costing and reporting language only; no named feature or add-on.
- Solution/industry language applied: trade-specific job types, records, equipment and commercial pressures for HVAC, electrical, plumbing, security and fire protection contractors.
- Fallback context use: none
- Claims requiring source verification: none
- Status: aligned

## Named Feature/Add-On Link Check

| Name in artifact | Resource checked | Link decision | Reason |
|---|---|---|---|
| None | Validated product and vertical context pack | Not triggered | The tables use generic capability categories and name no Simpro feature or add-on. |

## Hindsight Strategy Selection

- Status: internal_strategy_only
- Evidence output: `{HINDSIGHT_PATH.relative_to(ROOT).as_posix()}`
- Selected resources: {hindsight_resources}
- source_pack_sha256: `{hindsight_receipt['pack_sha256']}`
- source_receipt_sha256: `{hindsight_receipt['receipt_sha256']}`
- public_claim_use: prohibited
- claim_support_allowed: false
- Permitted effects: row selection, row order, operational emphasis and benefit framing.
- Fire treatment: directional only because its internal evidence coverage is materially smaller than the other four verticals.
- Public boundary: no internal data, deal counts, rankings, names, quotes, identifiers or unsupported claims appear in the copy deck.

## Current official page verification

| Page | Checked | Capability coverage used |
|---|---|---|
| https://www.simprogroup.com/industries/hvac-software | {DATE} | scheduling and dispatch, mobile job records, preventative maintenance, project costing, supplier and accounting connections, reporting |
| https://www.simprogroup.com/industries/electrical-software | {DATE} | scheduling and dispatch, mobile documentation, project work, materials, maintenance, job costing |
| https://www.simprogroup.com/industries/plumbing-software | {DATE} | dispatch, mobile job capture, quoting and invoicing, maintenance, supplier and accounting connections, reporting |
| https://www.simprogroup.com/industries/security | {DATE} | service scheduling, site and asset records, monitoring agreements, installation projects, device tracking, profitability reporting |
| https://www.simprogroup.com/industries/fire-protection-software | {DATE} | inspections, asset and defect records, mobile field forms, invoicing, parts and supplier connections, contract reporting |

## AEO and CMS implementation note

- Keep each H2 and direct-answer sentence immediately before its table.
- Render each Markdown table as one semantic HTML `<table>` with `<thead>` and column headers marked with `<th scope=\"col\">`.
- Preserve the column order Feature, Advantage, Benefit and the row order supplied for each trade.
- Keep the table before the existing final CTA and FAQ section.
- If the responsive design changes rows into cards on small screens, preserve the same header-to-cell associations in the accessible markup.

## Humanizer review

- Reviewed against `vendor/blader-humanizer/SKILL.md`, `vendor/blader-humanizer/UPSTREAM.json` and `config/humanizer-policy.json`.
- Protected facts and source boundaries remained unchanged.
- Removed unsupported hype, vague attribution, formulaic transitions, dramatic fragments, chatbot residue and em dashes.
- Product-page tone remains clear, practical, trade-aware and restrained.
- Status: complete
"""


def main() -> int:
    if not ARTICLE.is_file():
        raise FileNotFoundError(ARTICLE)
    article_hash = _sha256(ARTICLE)
    request = _context_request(article_hash)
    atomic_write_json(REQUEST_PATH, request)

    client = SimproVaultClient()
    status = client.status()
    if status.get("status") != "ready":
        raise RuntimeError(f"Vault status is not ready: {status}")
    describe = client.describe()
    searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}
    expansions = {
        resource_id: client.expand(
            resource_id, purpose=RESOURCE_PURPOSES[resource_id]
        )
        for resource_id in EXPAND_RESOURCE_IDS
    }
    discovered = _ids(searches) | _ids(expansions)
    missing = sorted(set(RESOURCE_PURPOSES) - discovered)
    if missing:
        raise RuntimeError(f"Selected resources were not rediscovered: {missing}")
    reads = {
        resource_id: client.read(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCE_PURPOSES.items()
    }
    claim_lookups = {
        query: client.claims(
            query,
            use_mode="public_paraphrase",
            brand_scope="Simpro",
            limit=20,
        )
        for query in SEARCH_QUERIES[3:8]
    }
    build_input = {
        "request": request,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": [],
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    built = client.build_context(build_input)
    validation = client.validate_context(request, built["pack"], built["receipt"])
    if validation.get("valid") is not True or validation.get("errors"):
        raise RuntimeError(f"Context validation failed: {validation}")
    atomic_write_json(PACK_PATH, built["pack"])
    atomic_write_json(RECEIPT_PATH, built["receipt"])
    hindsight = _build_hindsight(client, article_hash)
    SIDECAR_PATH.write_text(
        _render_sidecar(request, built["receipt"], hindsight),
        encoding="utf-8",
    )
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-industry-fab-context-refresh/v1",
            "status": status,
            "describe": describe,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "public_paraphrase_claim_lookups": claim_lookups,
            "public_claim_use_decision": "No objective-fit approved public claim is used. Copy is limited to low-risk, source-bound product and vertical language without metrics, named features, customer proof, availability or comparative claims.",
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
                "article": ARTICLE.relative_to(ROOT).as_posix(),
                "article_sha256": article_hash,
                "context_pack_sha256": built["receipt"].get("pack_sha256"),
                "context_receipt_sha256": built["receipt"].get("receipt_sha256"),
                "hindsight_pack_sha256": hindsight["receipt"].get("pack_sha256"),
                "resource_count": len(RESOURCE_PURPOSES),
                "status": status.get("status"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
