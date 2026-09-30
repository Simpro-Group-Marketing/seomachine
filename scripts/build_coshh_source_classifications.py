"""Export registry-bound source classifications for the BigChange COSHH regulations rewrite."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping

SLUG = "coshh-regulations"
DATE = "2026-09-24"
REGISTRY = ROOT / "context" / "source-classification-decisions.json"
OUT_DIR = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}"

URLS = tuple(
    row["source_url"]
    for row in json.loads(REGISTRY.read_text(encoding="utf-8"))["decisions"]
    if row["decision_id"].startswith("coshh-regulations-2026-09-24-")
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    decisions = {
        row["source_url"]: row
        for row in registry["decisions"]
        if row.get("status") == "approved"
    }
    missing = sorted(set(URLS) - set(decisions))
    if missing:
        raise ValueError(f"source registry is missing approved rows: {missing}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    registry_hash = sha256_file(REGISTRY)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for url in URLS:
        decision = decisions[url]
        payload = {
            "schema": "simpro-source-classification/v1",
            "classified_at": now,
            "emitter": {"name": "source_registry_export", "version": "1.0.0"},
            "publisher": {
                "hostname": urlparse(url).hostname,
                "relationship": decision["publisher_relationship"],
            },
            "registry": {
                "authority_mode": "repository_decision",
                "decision_path": "context/source-classification-decisions.json",
                "decision_sha256": registry_hash,
                "record_id": decision["decision_id"],
                "revision": registry["revision"],
            },
            "source_class": decision["source_class"],
            "source_url": url,
        }
        filename = f"source-classification-{hashlib.sha256(url.encode('utf-8')).hexdigest()}.json"
        atomic_write_json(
            OUT_DIR / filename,
            attest_mapping(
                payload,
                purpose="simpro-source-classification/v1",
                workspace_root=ROOT,
            ),
        )
        print(filename)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
