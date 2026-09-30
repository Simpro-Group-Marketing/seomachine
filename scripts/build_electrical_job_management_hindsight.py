"""Build internal-only Hindsight strategy evidence for the electrical buyer guide."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.simpro_vault_client import SimproVaultClient

ARTICLE = ROOT / "published" / "best-electrical-job-management-software-2026-09-02.md"
OUT = ROOT / "research" / "hindsight-strategy-evidence-best-electrical-job-management-software-2026-09-28.json"
QUERIES = [
    "electrical contractor software buyer priorities product fit pricing implementation mobile integrations scheduling dispatch projects reporting",
    "ServiceTitan electrical contractor competitive strategy buyer objections",
    "portfolio strategy field service software job mix routing service maintenance projects",
]
RESOURCE_IDS = [
    "res-acdf63e464db5579a008beb136c20593",
    "res-0c176526ba255cdc84781594dbcb1d1f",
    "res-8e0e276d13c95a7ea5bfb45bd57dfde2",
]


def result_ids(rows):
    return {r["resource_id"] for r in rows if isinstance(r, dict) and isinstance(r.get("resource_id"), str)}


def main() -> int:
    client = SimproVaultClient(); status = client.status()
    searches = {q: client.search_internal_strategy(q, limit=50) for q in QUERIES}
    discovered = set().union(*(result_ids(v) for v in searches.values()))
    missing = sorted(set(RESOURCE_IDS) - discovered)
    if missing: raise RuntimeError(f"Internal resources were not rediscovered: {missing}")
    reads = {rid: client.read_internal_strategy(rid) for rid in RESOURCE_IDS}
    article_hash = hashlib.sha256(ARTICLE.read_bytes()).hexdigest()
    request = {"task": "Use Hindsight only to sharpen the electrical software buying strategy.",
        "scope": {"brand": "Simpro", "market": "US", "artifact_type": "blog", "workflow_mode": "rewrite",
                  "title": "Best Electrical Job Management Software by Job Type (2026)",
                  "article_path": ARTICLE.relative_to(ROOT).as_posix(), "article_sha256": article_hash,
                  "permitted_effects": ["comparison dimensions", "demo tests", "buyer objections", "job-mix routing", "CTA framing"]}}
    constraints = [
        "Internal strategy only.", "Public claim use is prohibited.", "Claim support is not allowed.",
        "Do not expose deal counts, quotes, names, URLs, amounts or internal observations.",
        "Verify every public competitor fact against current official public sources.",
    ]
    packed = client.pack_internal_strategy({"request": request, "resource_ids": RESOURCE_IDS,
        "search_queries": QUERIES, "constraints": constraints, "unresolved_gaps": [], "task_satisfaction": "satisfied"})
    if packed["sidecar"].get("public_claim_use") != "prohibited" or packed["sidecar"].get("claim_support_allowed") is not False:
        raise RuntimeError("Hindsight boundary was not enforced")
    payload = {"pack": packed["pack"], "receipt": packed["receipt"], "sidecar": packed["sidecar"],
        "application_decision": {"mode": "internal_strategy_only",
            "applied_to": ["job-mix routing", "comparison dimensions", "three live-demo scenarios", "pricing and implementation objections", "CTA framing"],
            "public_copy_boundary": "No Hindsight counts, observations, quotes or unsupported claims appear in public copy."},
        "retrieval_trace": {"generated_at": datetime.now(timezone.utc).isoformat(), "vault_status": status,
                            "search_queries": QUERIES, "selected_resource_ids": RESOURCE_IDS,
                            "read_resource_ids": sorted(reads), "article_sha256": article_hash}}
    atomic_write_json(OUT, payload)
    print(json.dumps({"output": OUT.relative_to(ROOT).as_posix(), "resources": RESOURCE_IDS,
                      "pack": packed["receipt"].get("pack_sha256")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
