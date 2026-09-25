"""Rebuild the field-service-management-training context pack and receipt.

The vault selection is unchanged. The task satisfaction assessment is corrected
to `satisfied` with no unresolved gaps, because the request asks only for Simpro
voice, tone, localization and feature-naming guidance and declares no intended
public use modes. The three boundary notes previously recorded as unresolved gaps
are downstream editorial decisions that the supplied guidance produced, and they
remain documented in the validation sidecar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient

SLUG = "field-service-management-training"
REQUEST_PATH = ROOT / "research" / f"context-request-{SLUG}.json"
PACK_PATH = ROOT / "research" / f"context-pack-{SLUG}.json"
RECEIPT_PATH = ROOT / "research" / f"context-receipt-{SLUG}.json"

SEARCH_QUERIES = [
    "Simpro core messaging brand voice tone positioning field service management platform",
    "tone voice localization rules regional terminology UK spelling market",
    "JustAsk conversational interface business intelligence entity feature page",
    "industries verticals electrical plumbing HVAC trade vertical profiles",
]

RESOURCE_PURPOSES = {
    "res-09ebfff123cb5c5496e60c3a759a263d": "context",
    "res-152e6d1050b25ef78cab5614d97beb2c": "guidance",
    "res-1825898a11855f89be9bb69c544a6aa3": "guidance",
    "res-47015608c0d4556a854fca7544b4a040": "guidance",
    "res-641679c4b6c65e93951cb8d8e1ab88af": "guidance",
    "res-92348f8056165d4ba81a3c91738604e2": "context",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-b2973183861050c881ccd2ef3a8014f7": "guidance",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
}

CLAIM_QUERY = (
    "training onboarding new starter adoption ease of learning field service software"
)

CONSTRAINTS = [
    "Public copy names features for navigation only and asserts no capability, packaging, availability or price.",
    "Public copy carries one approved Capterra review snippet as an exact quote with the Joe H. attribution label and a same-paragraph link to the review URL.",
    "Public copy omits named customer metrics, testimonials, ratings, rankings and any proof beyond that single approved review snippet.",
    "Keep AroFlo and BigChange terminology separate from Simpro terminology.",
    "Em dashes prohibited.",
]


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


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    client = SimproVaultClient()

    client.status()
    client.describe()
    searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}

    discovered: set[str] = set()
    for rows in searches.values():
        discovered.update(result_ids(rows))

    expansions: dict[str, Any] = {}
    for resource_id in sorted(set(RESOURCE_PURPOSES) & discovered):
        expansion = client.expand(resource_id, purpose=RESOURCE_PURPOSES[resource_id])
        expansions[resource_id] = expansion
        discovered.update(relationship_ids(expansion))

    missing = sorted(set(RESOURCE_PURPOSES) - discovered)
    if missing:
        raise RuntimeError(f"Selected resource IDs were not rediscovered: {missing}")

    for resource_id, purpose in RESOURCE_PURPOSES.items():
        client.read(resource_id, purpose=purpose)

    client.claims(
        CLAIM_QUERY,
        use_mode="exact_quote",
        brand_scope="Simpro",
        limit=40,
    )

    build_input = {
        "request": request,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": [
            {
                "claim_id": "claim-metric-MET-0303",
                "query": CLAIM_QUERY,
                "use_mode": "exact_quote",
                "brand_scope": "Simpro",
            }
        ],
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    build_output = client.build_context(build_input)
    pack = build_output["pack"]
    receipt = build_output["receipt"]

    validation = client.validate_context(request, pack, receipt)
    if validation.get("valid") is not True:
        raise RuntimeError(f"Context validation did not return valid: {validation}")

    write_json(PACK_PATH, pack)
    write_json(RECEIPT_PATH, receipt)
    print(
        json.dumps(
            {
                "resources": len(RESOURCE_PURPOSES),
                "task_satisfaction": receipt.get("task_satisfaction"),
                "unresolved_gaps": receipt.get("unresolved_gaps"),
                "pack_sha256": receipt.get("pack_sha256"),
                "receipt_sha256": receipt.get("receipt_sha256"),
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
