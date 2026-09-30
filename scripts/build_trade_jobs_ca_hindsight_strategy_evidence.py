"""Build brief-bound internal Hindsight strategy evidence for the California trade-jobs rewrite.

Topic-specific adaptation of scripts/build_fsm_hindsight_strategy_evidence.py.
The generated evidence is internal strategy input only. It cannot support
public claims; salary, training, licensing, and demand facts come from current
official public sources.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient


SLUG = "best-trade-jobs-california"
DATE = "2026-09-24"
TITLE = "18 Highest-Paying Trade Jobs in California for 2026"
BRIEF = ROOT / "research" / f"content-brief-{SLUG}-{DATE}.md"
OUTPUT = ROOT / "research" / f"hindsight-strategy-evidence-{SLUG}-{DATE}.json"

SEARCH_QUERIES = [
    "electrician plumbing HVAC low voltage telecom trade contractor buying signals and owner growth objections",
    "multi-trade contractor portfolio career ladder service manager estimator owner",
    "licensing service maintenance recurring revenue trade contractor",
]

RESOURCE_IDS = [
    "res-17c15b5543db589b87f6803e32251cdf",  # Hindsight Internal Strategy Hub
    "res-8e0e276d13c95a7ea5bfb45bd57dfde2",  # Hindsight Portfolio Strategy Overview
    "res-01a755c114965914b704f29dd70ae1fc",  # Hindsight Multi-Trade Strategy
    "res-acdf63e464db5579a008beb136c20593",  # Hindsight Electrical/Data Strategy
    "res-2fa37305ff98541b8fa0955da4dd3978",  # Hindsight Plumbing Strategy
    "res-a41eef7796d7534b93f3e38a7f1036f4",  # Hindsight HVAC/Airconditioning Strategy
    "res-5ff3a414e5425f2eb78d66a76e50c22b",  # Hindsight Low Voltage Strategy
]

# Governance guidance for Hindsight use. It is a public-context vault resource,
# not an internal-strategy resource, so it is read with the normal read path and
# recorded as governance provenance rather than packed.
GUIDANCE_RESOURCE_ID = "res-f0af30c3066f57eaa59db44881568858"

CONSTRAINTS = [
    "Internal strategy and discovery use only.",
    "Public claim use is prohibited and claim support is not allowed.",
    "Permit effects only on section depth, pay-factor framing emphasis, career-ladder emphasis, and CTA audience framing.",
    "Do not expose names, amounts, deal counts, win rates, URLs, direct quotes, deal IDs, or public claims.",
    "Salary, training, licensing, and demand facts require current official public sources.",
]

PERMITTED_EFFECTS = [
    "section depth",
    "pay-factor framing emphasis",
    "career-ladder emphasis",
    "CTA audience framing",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def main() -> int:
    brief_sha256 = sha256_file(BRIEF)
    client = SimproVaultClient()
    status = client.status()
    if status.get("status") != "ready":
        raise RuntimeError(f"Vault status is not ready: {status}")
    searches = {
        query: client.search_internal_strategy(query, limit=50)
        for query in SEARCH_QUERIES
    }
    discovered: set[str] = set()
    for rows in searches.values():
        discovered.update(result_ids(rows))
    missing = sorted(set(RESOURCE_IDS) - discovered)
    if missing:
        raise RuntimeError(f"Selected internal strategy resources were not rediscovered: {missing}")

    reads = {
        resource_id: client.read_internal_strategy(resource_id)
        for resource_id in RESOURCE_IDS
    }
    guidance_search = client.search("Hindsight and Deal Intelligence Guidance", limit=20)
    if GUIDANCE_RESOURCE_ID not in result_ids(guidance_search):
        raise RuntimeError("Hindsight governance guidance resource was not rediscovered")
    guidance = client.read(GUIDANCE_RESOURCE_ID, purpose="context")

    request = {
        "task": (
            "Use internal Hindsight strategy to set section depth, pay-factor framing, "
            "career-ladder emphasis, and owner-operator CTA framing in a US career guide "
            "without using internal material as public proof."
        ),
        "scope": {
            "brand": "Simpro",
            "market": "US",
            "artifact_type": "blog",
            "workflow_mode": "rewrite",
            "title": TITLE,
            "canonical_url": f"https://www.simprogroup.com/blog/{SLUG}",
            "brief_path": BRIEF.relative_to(ROOT).as_posix(),
            "brief_sha256": brief_sha256,
            "permitted_effects": PERMITTED_EFFECTS,
        },
    }
    packed = client.pack_internal_strategy(
        {
            "request": request,
            "resource_ids": RESOURCE_IDS,
            "search_queries": SEARCH_QUERIES,
            "constraints": CONSTRAINTS,
            "unresolved_gaps": [],
            "task_satisfaction": "satisfied",
        }
    )
    expected = {
        "pack": "simpro-internal-strategy-pack/v1",
        "receipt": "simpro-internal-strategy-receipt/v1",
        "sidecar": "simpro-content-validation-sidecar/v1",
    }
    for key, schema in expected.items():
        value = packed.get(key)
        if not isinstance(value, dict) or value.get("schema") != schema:
            raise RuntimeError(f"Internal strategy {key} did not use {schema}")
    sidecar = packed["sidecar"]
    if sidecar.get("public_claim_use") != "prohibited":
        raise RuntimeError("Internal strategy sidecar must prohibit public claim use")
    if sidecar.get("claim_support_allowed") is not False:
        raise RuntimeError("Internal strategy sidecar cannot allow claim support")

    payload = {
        "pack": packed["pack"],
        "receipt": packed["receipt"],
        "sidecar": packed["sidecar"],
        "discovery_provenance": {
            "classification": "compiled_internal_strategy_pages",
            "public_use_status": "prohibited",
            "claim_support_allowed": False,
            "approved_source_node": "Hindsight Simpro intelligence snapshot 2026-08-31 (connector-resolved approved source node)",
            "snapshot_revisions": sorted(
                {
                    match.group(1)
                    for read in reads.values()
                    if isinstance(read, dict)
                    for match in [
                        re.search(
                            r"^snapshot_revision:\s*([0-9a-f]{64})\s*$",
                            str(read.get("content") or ""),
                            re.MULTILINE,
                        )
                    ]
                    if match
                }
            ),
            "resource_content_sha256": {
                resource_id: read.get("content_sha256")
                for resource_id, read in reads.items()
                if isinstance(read, dict)
            },
            "governance_guidance": {
                "resource_id": GUIDANCE_RESOURCE_ID,
                "title": guidance.get("title"),
                "content_sha256": guidance.get("content_sha256"),
                "read_purpose": "context",
                "note": "Governance rule sheet for Hindsight use; read through the public-context path because it is not an internal-strategy resource.",
            },
            "brief_sha256": brief_sha256,
            "note": "Evidence is bound to the rewrite brief because the rewrite article did not exist when the strategy pack was built.",
        },
        "retrieval_trace": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "vault_status": status,
            "search_queries": SEARCH_QUERIES,
            "selected_resource_ids": RESOURCE_IDS,
            "read_resource_ids": sorted(reads),
            "governance_read_resource_ids": [GUIDANCE_RESOURCE_ID],
        },
    }
    write_json(OUTPUT, payload)
    print(
        json.dumps(
            {
                "output": OUTPUT.relative_to(ROOT).as_posix(),
                "brief_sha256": brief_sha256,
                "pack_sha256": packed["receipt"].get("pack_sha256"),
                "receipt_sha256": packed["receipt"].get("receipt_sha256"),
                "selected_resource_ids": RESOURCE_IDS,
                "snapshot_revisions": payload["discovery_provenance"]["snapshot_revisions"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
