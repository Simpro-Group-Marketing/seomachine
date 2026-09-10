from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.simpro_vault_client import SimproVaultClient


OUTPUT_DIR = ROOT / "research" / "best-plumbing-job-management-software-remediation-2026-09-08"
REQUEST_PATH = OUTPUT_DIR / "context-request-g2-proof.json"

SEARCH_QUERIES = [
    "plumbing job management software customer proof G2 commercial plumbing call to invoice Fergus Simpro",
    "Simpro customer proof plumbing review quote workflow setup prebuilds reporting",
    "Custom workflow set up prebuilds deep reporting Matthew N G2 Simpro",
]

RESOURCE_PURPOSES = {
    "res-c6446c5031c75caca952de485dc23cb4": "context",
    "res-1825898a11855f89be9bb69c544a6aa3": "guidance",
    "res-d31f057a305f51918055120d95b76c6a": "guidance",
    "res-329967c98bb351628aed830575fd8496": "context",
    "res-5c1b34d7d2175caab4fb29a208e59ac0": "context",
    "res-6b127060c8ec5af3b35b5f6dda5fd5c5": "context",
    "res-177020d87b8c5c2581a0b728bc1fe114": "context",
    "res-00a2b19bd4ac503b9b560dc2d1af16aa": "context",
    "res-641679c4b6c65e93951cb8d8e1ab88af": "guidance",
}

CLAIM_QUERY = "Custom workflow set up, prebuilds and deep reporting Matthew N G2 simpro-review-4999982"
CLAIM_ID = "claim-metric-MET-1148"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    request = json.loads(REQUEST_PATH.read_text(encoding="utf-8"))
    client = SimproVaultClient()

    status = client.status()
    describe = client.describe()
    searches = {query: client.search(query, limit=50) for query in SEARCH_QUERIES}
    reads = {
        resource_id: client.read(resource_id, purpose=purpose)
        for resource_id, purpose in RESOURCE_PURPOSES.items()
    }
    claims = client.claims(
        CLAIM_QUERY,
        brand_scope="Simpro",
        use_mode="exact_quote",
        limit=50,
    )

    build_input = {
        "request": request,
        "search_queries": SEARCH_QUERIES,
        "resource_ids": list(RESOURCE_PURPOSES),
        "resource_purposes": RESOURCE_PURPOSES,
        "claim_requests": [
            {
                "query": CLAIM_QUERY,
                "brand_scope": "Simpro",
                "use_mode": "exact_quote",
                "claim_id": CLAIM_ID,
            }
        ],
        "constraints": [
            "Use official current vendor pages for public vendor capabilities and pricing routes.",
            "Do not claim hands-on testing, independence, an overall winner, guaranteed outcomes, or unsupported rankings.",
            "Use only the exact approved excerpt from claim-metric-MET-1148.",
            "Attribute the quote to Matthew N. and link the G2 review in the same paragraph.",
            "Do not claim Matthew N. is a plumber or that this is a universal Simpro outcome.",
        ],
        "task_satisfaction": "satisfied",
        "unresolved_gaps": [],
    }
    build_output = client.build_context(build_input)
    pack = build_output["pack"]
    receipt = build_output["receipt"]
    validation = client.validate_context(request, pack, receipt)

    write_json(OUTPUT_DIR / "vault-status-g2-proof-current.json", status)
    write_json(OUTPUT_DIR / "vault-describe-g2-proof-current.json", describe)
    write_json(OUTPUT_DIR / "vault-searches-g2-proof-current.json", searches)
    write_json(OUTPUT_DIR / "vault-reads-g2-proof-current.json", reads)
    write_json(OUTPUT_DIR / "vault-claims-g2-met-1148-current.json", claims)
    write_json(OUTPUT_DIR / "context-build-input-g2-proof.json", build_input)
    write_json(OUTPUT_DIR / "context-build-output-g2-proof.json", build_output)
    write_json(OUTPUT_DIR / "context-pack-g2-proof.json", pack)
    write_json(OUTPUT_DIR / "context-receipt-g2-proof.json", receipt)
    write_json(OUTPUT_DIR / "context-validation-g2-proof.json", validation)
    summary = {
        "schema": "simpro-plumbing-g2-context-run/v1",
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": status.get("status"),
        "revisions": status.get("revisions"),
        "selected_claim_id": CLAIM_ID,
        "pack_sha256": sha256(OUTPUT_DIR / "context-pack-g2-proof.json"),
        "receipt_sha256": sha256(OUTPUT_DIR / "context-receipt-g2-proof.json"),
        "validation": validation,
    }
    write_json(OUTPUT_DIR / "context-run-summary-g2-proof.json", summary)
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
