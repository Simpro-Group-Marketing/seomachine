from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient


TOPIC_SLUG = "ai-field-service-economics"
REQUEST_PATH = ROOT / "research" / f"context-request-{TOPIC_SLUG}.json"
PACK_PATH = ROOT / "research" / f"context-pack-{TOPIC_SLUG}.json"
RECEIPT_PATH = ROOT / "research" / f"context-receipt-{TOPIC_SLUG}.json"
TRACE_PATH = ROOT / "research" / f"context-refresh-{TOPIC_SLUG}-2026-09-08.json"

REQUEST = {
    "task": (
        "Create a new Simpro AEO/SEO blog explaining how field service leaders can "
        "measure the economics of AI before automating, using the verified Fred Voccola "
        "CEPro video as a lead media placeholder and routing qualified interest to Simpro Lightning."
    ),
    "scope": {
        "artifact_type": "blog",
        "brand": "Simpro",
        "title": "AI Field Service Economics: What to Measure Before You Automate",
        "objective": (
            "Help US field service leaders identify, baseline, pilot, and evaluate "
            "economically useful AI workflows while routing qualified commercial interest "
            "to Simpro Lightning."
        ),
        "audience": (
            "US trade-business owners, finance leaders, operations managers, and service "
            "managers evaluating AI investments"
        ),
        "region": "US",
        "intended_public_use_modes": ["authority_support"],
    },
}

SEARCH_QUERIES = [
    "Simpro AI field service economics for US trade business owners measuring capacity cost-to-serve rework admin time and billing velocity",
    "current Simpro blog voice and tone guidance for practical US trade business advice with no named author",
    "current Simpro Lightning Cooper JustAsk FieldReady JobReady JobScribe JobBrief positioning status and public product links",
    "Fred Voccola CEPro How Simpro and AI is reshaping field service economics video GU0pqwFXo4Q",
    "Simpro field service management scheduling reporting metrics internal link guidance for AI economics blog",
]

RESOURCE_PURPOSES = {
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-dfc67c5cef87541d856a765f2747a2cb": "guidance",
    "res-92348f8056165d4ba81a3c91738604e2": "context",
    "res-47015608c0d4556a854fca7544b4a040": "guidance",
    "res-0409dfe9b949599f99577d45bd7e7e25": "guidance",
    "res-aabdab4b40f85d748bf1cf2c754a36f8": "context",
    "res-16c113c993565a4c84150d131c034c57": "guidance",
    "res-15f3055bbe9850d0974573791ce80840": "guidance",
    "res-a275b848264f5d88ace06f5e420f73b3": "context",
    "res-d20b284debde5496a54d7bc67186760b": "context",
    "res-7b30f511fc345ff2bb5fd9e515f03d06": "context",
    "res-f882ab230eb2563889e300d612c324bc": "context",
}

EXPAND_RESOURCE_IDS = [
    "res-e3ade596be645307ad4c1f84620ce021",
    "res-dfc67c5cef87541d856a765f2747a2cb",
    "res-47015608c0d4556a854fca7544b4a040",
    "res-0409dfe9b949599f99577d45bd7e7e25",
    "res-15f3055bbe9850d0974573791ce80840",
    "res-aabdab4b40f85d748bf1cf2c754a36f8",
]

CLAIM_REQUESTS = [
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
        "claim_id": "claim-fred-FVMI-0006",
        "query": "Fred Voccola Simpro AI in the Commercial Trades plumbers electricians HVAC contractors",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
    {
        "claim_id": "claim-authority-AUTH-0023",
        "query": "Simpro Group launches Lightning AI-native operating platform for the field service trades",
        "use_mode": "authority_support",
        "brand_scope": "Simpro",
    },
]

CONSTRAINTS = [
    "Use US spelling and current Simpro blog voice guidance.",
    "Use no named author and omit Person author schema.",
    "Use the verified CEPro YouTube video GU0pqwFXo4Q as a reader-visible lead media placeholder.",
    "Treat FVMI-0105 as a playlist-verified embed or discovery asset, not independent earned-media authority.",
    "Do not quote or paraphrase the CEPro video without an approved exact-quote or public-paraphrase claim.",
    "Exclude unsupported margin averages, profit multipliers, business counts, customer counts, and efficiency guarantees from the transcript.",
    "Use current Lightning positioning without pricing, promotion, availability, roadmap, replacement-staff, or guaranteed-outcome claims.",
    "Differentiate the article from the existing AI field service management, automation, and KPI guides.",
]


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


def main() -> None:
    client = SimproVaultClient()
    status = client.status()
    describe = client.describe()
    searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}
    expansions = {
        resource_id: client.expand(
            resource_id,
            purpose=RESOURCE_PURPOSES[resource_id],
        )
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
    claim_lookups = {
        item["claim_id"]: client.claims(
            item["query"],
            use_mode=item["use_mode"],
            brand_scope=item["brand_scope"],
            limit=50,
        )
        for item in CLAIM_REQUESTS
    }

    build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": CLAIM_REQUESTS,
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    build_output = client.build_context(build_input)
    pack = build_output["pack"]
    receipt = build_output["receipt"]
    validation = client.validate_context(REQUEST, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"Context validation did not return valid: {validation}")

    write_json(REQUEST_PATH, REQUEST)
    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    write_json(
        TRACE_PATH,
        {
            "schema": "simpro-ai-field-service-economics-context-refresh/v1",
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status,
            "describe": describe,
            "searches": searches,
            "expansions": expansions,
            "reads": reads,
            "approved_claim_lookups": claim_lookups,
            "build_input": build_input,
            "build_output": build_output,
            "validation": validation,
        },
    )
    print(
        json.dumps(
            {
                "status": status.get("status"),
                "resource_count": len(RESOURCE_PURPOSES),
                "pack_sha256": receipt.get("pack_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "request_sha256": receipt.get("request_sha256"),
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
