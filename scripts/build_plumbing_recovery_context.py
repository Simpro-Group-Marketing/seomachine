from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient


OUTPUT_DIR = ROOT / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
RAW_DIR = OUTPUT_DIR / "raw" / "simpro-context"

SEARCH_QUERIES = [
    "Simpro blog voice and tone guidance for a US plumbing contractor software comparison",
    "US plumbing contractor ideal customer profile growth office field coordination",
    "plumbing software scheduling dispatch estimating invoicing maintenance inventory job costing",
    "Feature Datasheet Atlas plumbing vertical",
    "competitive comparison plumbing software ServiceTitan BuildOps Jobber Housecall Pro Workiz FieldPulse Service Fusion",
]

RESOURCE_PURPOSES = {
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-329967c98bb351628aed830575fd8496": "context",
    "res-c6446c5031c75caca952de485dc23cb4": "context",
    "res-1825898a11855f89be9bb69c544a6aa3": "guidance",
    "res-5c1b34d7d2175caab4fb29a208e59ac0": "context",
}

REQUEST = {
    "schema": "simpro-context-request/v1",
    "task": (
        "Rewrite https://www.simprogroup.com/blog/best-plumbing-job-management-software "
        "in place as a source-bound US buyer guide titled Best Plumbing Job Management "
        "Software for 2026 | Simpro. Recover plumbing job management intent, repair public "
        "publishing defects, improve decision support, and preserve concise answer coverage."
    ),
    "scope": {
        "artifact_type": "blog",
        "brand": "Simpro",
        "title": "Best Plumbing Job Management Software for 2026 | Simpro",
        "objective": (
            "Help growing US plumbing contractors compare job management platforms by business "
            "fit, workflow depth, rollout needs, and three-year cost."
        ),
        "audience": (
            "US plumbing owners and GMs, operations leaders, office managers, field supervisors, "
            "finance and controllers, and IT or system leads managing multiple crews or mixed workflows"
        ),
        "region": "US",
        "required_context_topics": [
            "industry:plumbing",
            "ideal customer profile",
            "product positioning",
            "voice and tone",
            "US localization",
            "feature and product collateral",
            "competitive context",
        ],
        "intended_public_use_modes": ["paraphrase"],
    },
    "context_needs": [
        "Clear, practical, trade-aware Simpro blog voice and US localization guidance.",
        "Internal ICP guidance for audience fit without exposing confidential size or revenue thresholds.",
        "US plumbing workflow and product context for qualified Simpro descriptions.",
        "Competitive guidance for a fit-based comparison without unsupported rankings or absence claims.",
    ],
    "constraints": [
        "Use official current vendor pages for public vendor capabilities and pricing routes.",
        "Do not claim hands-on testing, independence, an overall winner, guaranteed outcomes, or unsupported rankings.",
        "Do not publish internal ICP employee, revenue, qualification, routing, or win-zone thresholds.",
        "Do not publish internal battlecard language or unsupported competitor weaknesses.",
        "Do not carry forward FeaturedCustomers ratings, Kiely proof, customer metrics, quotes, or Fred authority automatically.",
        "Use no em dashes.",
        "Do not invent a named reviewer or Person author.",
    ],
    "unresolved_gaps": [],
}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = SimproVaultClient()

    status = client.status()
    describe = client.describe()
    searches = {query: client.search(query, limit=20) for query in SEARCH_QUERIES}

    discovered_ids = {
        row.get("resource_id")
        for rows in searches.values()
        for row in rows
        if isinstance(row, dict)
    }
    missing_ids = sorted(set(RESOURCE_PURPOSES) - discovered_ids)
    if missing_ids:
        raise RuntimeError(f"Selected resource IDs were not rediscovered: {missing_ids}")

    reads = {
        resource_id: client.read(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCE_PURPOSES.items()
    }

    build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": [],
        "constraints": REQUEST["constraints"],
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    build_output = client.build_context(build_input)
    pack = build_output["pack"]
    receipt = build_output["receipt"]
    validation = client.validate_context(REQUEST, pack, receipt)

    write_json(RAW_DIR / "vault-status.json", status)
    write_json(RAW_DIR / "vault-describe.json", describe)
    write_json(RAW_DIR / "vault-searches.json", searches)
    write_json(RAW_DIR / "vault-reads.json", reads)
    write_json(OUTPUT_DIR / "context-request.json", REQUEST)
    write_json(OUTPUT_DIR / "context-build-input.json", build_input)
    write_json(OUTPUT_DIR / "context-build-output.json", build_output)
    write_json(OUTPUT_DIR / "context-pack.json", pack)
    write_json(OUTPUT_DIR / "context-receipt.json", receipt)
    write_json(OUTPUT_DIR / "context-validation.json", validation)
    write_json(
        OUTPUT_DIR / "context-run-summary.json",
        {
            "schema": "simpro-plumbing-recovery-context-run/v1",
            "generated_at": datetime.now().astimezone().isoformat(),
            "status": status.get("status"),
            "revisions": status.get("revisions"),
            "search_query_count": len(SEARCH_QUERIES),
            "selected_resource_ids": list(RESOURCE_PURPOSES),
            "selected_resource_hashes": {
                resource_id: read.get("content_sha256")
                for resource_id, read in reads.items()
            },
            "pack_schema": pack.get("schema"),
            "receipt_schema": receipt.get("schema"),
            "validation": validation,
        },
    )

    print(
        json.dumps(
            {
                "status": status.get("status"),
                "resources": len(RESOURCE_PURPOSES),
                "pack_schema": pack.get("schema"),
                "receipt_schema": receipt.get("schema"),
                "validation": validation,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
