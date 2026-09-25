"""Build article-bound internal Hindsight strategy evidence for the FSM guide.

The generated evidence is discovery and strategy input only. It cannot support
public claims; official vendor documentation remains the authority for every
publishable competitor fact.
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


ARTICLE = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
OUTPUT = ROOT / "research" / "hindsight-strategy-evidence-best-field-service-management-software-2026-09-24.json"

SEARCH_QUERIES = [
    "field service management software buyer objections and first demo tests",
    "Jobber Joblogic FieldEdge ServiceTitan FieldPulse Service Fusion Tradify buyer objections",
    "commercial asset-heavy service project workflow evaluation",
]

RESOURCE_IDS = [
    "res-17c15b5543db589b87f6803e32251cdf",
    "res-0c176526ba255cdc84781594dbcb1d1f",
    "res-ab8acb78ff2050a787e8e17d234a3f3b",
    "res-123f609e3a7b5666b5c1db6ccd9cab49",
    "res-dd31b800a8c15dffbed1f1cba724e547",
    "res-8e0e276d13c95a7ea5bfb45bd57dfde2",
]

CONSTRAINTS = [
    "Internal strategy and discovery use only.",
    "Public claim use is prohibited and claim support is not allowed.",
    "Permit effects only on demo-test emphasis and buyer objections.",
    "Do not expose names, amounts, URLs, direct quotes, deal IDs, or public claims.",
    "Independently verify every publishable competitor fact against current official vendor documentation.",
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
    article_sha256 = sha256_file(ARTICLE)
    client = SimproVaultClient()
    status = client.status()
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
    request = {
        "task": "Use internal Hindsight strategy to sharpen buyer-owned demo tests in the neutral 12-tool FSM guide without using internal material as public proof.",
        "scope": {
            "brand": "Simpro",
            "market": "US",
            "artifact_type": "blog",
            "workflow_mode": "rewrite",
            "title": "Best Field Service Management Software: 2026 Buyer's Guide to 12 Tools",
            "article_path": ARTICLE.relative_to(ROOT).as_posix(),
            "article_sha256": article_sha256,
            "permitted_effects": ["demo-test emphasis", "buyer objections"],
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
            "classification": "secondary_hindsight_synthesis",
            "public_use_status": "prohibited",
            "claim_support_allowed": False,
            "google_doc_id": "1IIAz7beD0tqP3_zPud0pziwEYKq5q6N4LgtxwTESkoE",
            "google_doc_revision_id": "ANLCKQlwNfXTT01x9fZxMWX-4ekO7ILz_mkquHyZOhsYXuzNC-VhGqhpOgwup7xoKwAY3QnWCpgDYtIAIuJUSwBGQffQQwX8LNkAGW_J5Pk",
            "normalized_text_sha256": "5dd1185cd22e6ea9e6f912d2672dcfc53e449c818cfa247279e3dacbc7849fb4",
            "source_ingestion_id": "ING-20260924-001",
            "fresh_capture_ingestion_id": "ING-20260924-002",
            "fresh_capture_id": "HSI-SIMPRO-20260831-8A075E9979",
            "fresh_capture_period": {
                "from": "2025-09-01",
                "to": "2026-08-31",
            },
            "fresh_capture_markdown_sha256": "6edd11ba83504f49b03f1ca5bae6996659eb652599fc10ab08c5c720e81d647b",
            "fresh_capture_json_sha256": "7d78321e9594572f6f72107e6eb651da36709e42aa5c4514f814cab89706a69a",
            "article_sha256": article_sha256,
            "note": "The Google Doc source node records discovery provenance only. The formal internal-strategy pack does not validate every statement in that synthesis.",
        },
        "retrieval_trace": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "vault_status": status,
            "search_queries": SEARCH_QUERIES,
            "selected_resource_ids": RESOURCE_IDS,
            "read_resource_ids": sorted(reads),
        },
    }
    write_json(OUTPUT, payload)
    print(
        json.dumps(
            {
                "output": OUTPUT.relative_to(ROOT).as_posix(),
                "article_sha256": article_sha256,
                "pack_sha256": packed["receipt"].get("pack_sha256"),
                "receipt_sha256": packed["receipt"].get("receipt_sha256"),
                "selected_resource_ids": RESOURCE_IDS,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
