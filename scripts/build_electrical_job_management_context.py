"""Build and validate current Simpro vault context for the electrical buyer guide."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.content_store import write_context_trace
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.simpro_vault_client import SimproVaultClient

SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
ARTICLE = ROOT / "published" / "best-electrical-job-management-software-2026-09-02.md"
REQUEST = ROOT / "research" / f"context-request-{SLUG}-{DATE}.json"
PACK = ROOT / "research" / f"context-pack-{SLUG}-{DATE}.json"
RECEIPT = ROOT / "research" / f"context-receipt-{SLUG}-{DATE}.json"
SELECTOR_PACK = ROOT / "research" / f"context-pack-{SLUG}-customer-selector-{DATE}.json"
SELECTOR_RECEIPT = ROOT / "research" / f"context-receipt-{SLUG}-customer-selector-{DATE}.json"
TRACE = ROOT / "research" / f"context-refresh-{SLUG}-{DATE}.json"

QUERIES = [
    "Simpro electrical contractor software US positioning for service maintenance and project workflows",
    "Simpro electrical vertical profile contractor job mix operational priorities United States",
    "current Simpro blog editorial voice tone comparison buyer guide no named author",
    "Simpro product positioning scheduling dispatch mobile inventory job costing reporting",
    "Simpro takeoffs estimating product feature language for electrical contractors",
    "Simpro competitive context ServiceTitan BuildOps Knowify FieldPulse Jobber Housecall Pro Service Fusion FieldEdge Tradify",
]
RESOURCES = {
    "res-10b97eee1de25395bbf8b904111ca4b0": "context",
    "res-f9f9499223a15d6a901806f30fb1a8ba": "context",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-e3ade596be645307ad4c1f84620ce021": "guidance",
    "res-b34b392d22b9507089ade3fec47ee9e0": "context",
    "res-a5b3b47382b45490bf2bedbf16c0b76e": "guidance",
    "res-c6e69419a82e59919b4af4731a7e496a": "context",
    "res-517ad5ccb2cd5c3985831d8aba4cedaa": "guidance",
}


def ids(value):
    if isinstance(value, dict):
        result = {value["resource_id"]} if isinstance(value.get("resource_id"), str) else set()
        for child in value.values(): result.update(ids(child))
        return result
    if isinstance(value, list):
        result = set()
        for child in value: result.update(ids(child))
        return result
    return set()


def main() -> int:
    request = {
        "schema": "simpro-context-request/v1",
        "task": "Rewrite the existing electrical job management software comparison in place as a 10-product, job-mix-led buying guide while preserving the canonical URL.",
        "scope": {
            "artifact_type": "blog", "brand": "Simpro",
            "title": "Best Electrical Job Management Software by Job Type (2026)",
            "objective": "Help US electrical contractors choose a short demo list by job mix, then compare workflow fit, pricing, implementation and integration requirements on equal terms.",
            "audience": "US electrical contractors evaluating software for residential service, recurring maintenance, mixed service and project work, or multi-stage commercial projects",
            "region": "US", "article_sha256": hashlib.sha256(ARTICLE.read_bytes()).hexdigest(),
            "required_context_topics": ["industry:electrical", "product positioning", "voice and tone", "US localization", "named features"],
            "intended_public_use_modes": ["paraphrase"],
        },
        "context_needs": [
            "Electrical vertical language and US-market positioning.",
            "Current product and feature language for scheduling, mobile, maintenance, projects, costing and takeoffs.",
            "Current editorial voice for a no-author comparison blog.",
            "Competitive context needed to document the approved shortlist without publishing vault intelligence.",
        ],
        "constraints": [
            "No named author or Person schema.", "No em dashes.",
            "Use exactly 10 products in the approved order, including Knowify fourth.",
            "Hindsight is internal strategy only and cannot support public claims.",
            "Current official public vendor pages support public competitor facts.",
            "Customer or executive proof is omitted unless selectors establish direct topical fit.",
        ], "unresolved_gaps": [],
    }
    atomic_write_json(REQUEST, request)
    client = SimproVaultClient()
    status = client.status()
    if status.get("status") != "ready": raise RuntimeError(status)
    describe = client.describe()
    searches = {q: client.search(q, limit=50) for q in QUERIES}
    expansions = {rid: client.expand(rid, purpose=purpose) for rid, purpose in RESOURCES.items()}
    discovered = ids(searches) | ids(expansions)
    missing = sorted(set(RESOURCES) - discovered)
    if missing: raise RuntimeError(f"Selected resource IDs were not rediscovered: {missing}")
    reads = {rid: client.read(rid, purpose=purpose) for rid, purpose in RESOURCES.items()}
    build_input = {
        "request": request, "search_queries": QUERIES,
        "resource_ids": list(RESOURCES), "resource_purposes": RESOURCES,
        "claim_requests": [],
        "constraints": request["constraints"], "task_satisfaction": "satisfied", "unresolved_gaps": [],
    }
    selector_input = {**build_input, "claim_requests": [{
        "claim_id": "claim-metric-MET-1482",
        "query": "TEAMWired manual invoicing hours were reduced by 90%",
        "use_mode": "public_metric", "brand_scope": "Simpro",
    }]}
    selector_built = client.build_context(selector_input)
    selector_validation = client.validate_context(request, selector_built["pack"], selector_built["receipt"])
    if selector_validation.get("valid") is not True: raise RuntimeError(selector_validation)
    atomic_write_json(SELECTOR_PACK, selector_built["pack"])
    atomic_write_json(SELECTOR_RECEIPT, selector_built["receipt"])
    built = client.build_context(build_input)
    validation = client.validate_context(request, built["pack"], built["receipt"])
    if validation.get("valid") is not True: raise RuntimeError(validation)
    atomic_write_json(PACK, built["pack"]); atomic_write_json(RECEIPT, built["receipt"])
    write_context_trace(TRACE, {"schema": "simpro-electrical-job-management-context-refresh/v1",
        "status": status, "describe": describe, "searches": searches, "expansions": expansions,
        "reads": reads, "selector_build_input": selector_input, "selector_build_output": selector_built,
        "selector_validation": selector_validation, "build_input": build_input, "build_output": built,
        "validation": validation},
        workspace_root=ROOT, generated_at=datetime.now(timezone.utc))
    print(json.dumps({"status": status["status"], "pack": built["receipt"].get("pack_sha256"),
                      "receipt": built["receipt"].get("receipt_sha256"), "resources": len(RESOURCES)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
