from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.simpro_vault_client import SimproVaultClient
from scripts.build_ai_field_service_economics_context import (
    CONSTRAINTS,
    PACK_PATH,
    RECEIPT_PATH,
    REQUEST,
    REQUEST_PATH,
    RESOURCE_PURPOSES,
    SEARCH_QUERIES,
    SELECTOR_CLAIM_REQUESTS,
    SELECTOR_PACK_PATH,
    SELECTOR_RECEIPT_PATH,
)


TRACE_PATH = (
    ROOT
    / "research"
    / "context-rebind-ai-field-service-economics-2026-09-08.json"
)
FULL_REFRESH_TRACE_PATH = (
    ROOT
    / "research"
    / "context-refresh-ai-field-service-economics-2026-09-08.json"
)


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def main() -> None:
    client = SimproVaultClient()
    status = client.status()
    article_build_input = {
        "request": REQUEST,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": [
            item
            for item in SELECTOR_CLAIM_REQUESTS
            if item["claim_id"] == "claim-fred-FVMI-0001"
        ],
        "constraints": CONSTRAINTS,
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    article_build_output = client.build_context(article_build_input)
    article_pack = article_build_output["pack"]
    article_receipt = article_build_output["receipt"]
    article_validation = client.validate_context(
        REQUEST,
        article_pack,
        article_receipt,
    )
    if article_validation.get("valid") is not True:
        raise RuntimeError(
            "Article context validation did not return valid: "
            f"{article_validation}"
        )
    atomic_write_json(REQUEST_PATH, REQUEST)
    atomic_write_json(PACK_PATH, article_pack)
    atomic_write_json(RECEIPT_PATH, article_receipt)

    selector_build_input = {
        **article_build_input,
        "claim_requests": SELECTOR_CLAIM_REQUESTS,
    }
    selector_build_output = client.build_context(selector_build_input)
    selector_pack = selector_build_output["pack"]
    selector_receipt = selector_build_output["receipt"]
    selector_validation = client.validate_context(
        REQUEST,
        selector_pack,
        selector_receipt,
    )
    if selector_validation.get("valid") is not True:
        raise RuntimeError(
            "Selector context validation did not return valid: "
            f"{selector_validation}"
        )
    atomic_write_json(SELECTOR_PACK_PATH, selector_pack)
    atomic_write_json(SELECTOR_RECEIPT_PATH, selector_receipt)
    write_context_trace(
        TRACE_PATH,
        {
            "schema": "simpro-ai-field-service-economics-context-rebind/v1",
            "status": status,
            "selector_validation": selector_validation,
            "article_build_input": article_build_input,
            "article_build_output": article_build_output,
            "article_validation": article_validation,
        },
        workspace_root=ROOT,
        generated_at=datetime.now(timezone.utc),
    )
    print(json.dumps({
        "vault_status": status.get("status"),
        "selector_pack_sha256": selector_receipt.get("pack_sha256"),
        "selector_receipt_sha256": selector_receipt.get("receipt_sha256"),
        "article_pack_sha256": article_receipt.get("pack_sha256"),
        "article_receipt_sha256": article_receipt.get("receipt_sha256"),
        "article_validation": article_validation,
    }, indent=2))


if __name__ == "__main__":
    main()
