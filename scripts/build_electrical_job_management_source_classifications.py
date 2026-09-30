"""Approve and export exact-URL classifications for the newly added Knowify sources."""
from __future__ import annotations

import hashlib
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.source_support.persistence import write_source_classification_artifact

REGISTRY = ROOT / "context" / "source-classification-decisions.json"
OUT = ROOT / "research" / "source-classifications" / "best-electrical-job-management-software-2026-09-28"
ROWS = [
    ("electrical-software-2026-09-28-knowify-electrical", "https://knowify.com/electrical-contractors/"),
    ("electrical-software-2026-09-28-knowify-pricing", "https://knowify.com/pricing/"),
    ("electrical-software-2026-09-28-knowify-quickbooks", "https://knowify.com/integrations/quickbooks/"),
]


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    existing = {row["decision_id"]: row for row in registry["decisions"]}
    for decision_id, url in ROWS:
        row = {"decision_id": decision_id, "status": "approved", "source_url": url,
               "hostname": "knowify.com", "source_class": "competitor",
               "publisher_relationship": "competitor"}
        if decision_id in existing and existing[decision_id] != row:
            raise ValueError(f"Conflicting registry decision: {decision_id}")
        if decision_id not in existing:
            registry["decisions"].append(row)
    registry["revision"] = "2026-09-28"
    atomic_write_json(REGISTRY, registry)
    OUT.mkdir(parents=True, exist_ok=True)
    for decision_id, url in ROWS:
        name = f"source-classification-{hashlib.sha256(url.encode()).hexdigest()}.json"
        payload = write_source_classification_artifact(OUT / name, source_url=url,
            decision_id=decision_id, decision_path=REGISTRY, workspace_root=ROOT)
        print(f"{url} -> {name} ({payload['source_class']})")
    return 0


def restore_registry() -> int:
    """Remove this uncommitted intake and restore the registry's committed key order."""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    remove_ids = {decision_id for decision_id, _url in ROWS}
    ordered_rows = []
    for row in registry["decisions"]:
        if row["decision_id"] in remove_ids:
            continue
        ordered_rows.append({
            "decision_id": row["decision_id"],
            "status": row["status"],
            "source_url": row["source_url"],
            "hostname": row["hostname"],
            "source_class": row["source_class"],
            "publisher_relationship": row["publisher_relationship"],
        })
    restored = {"schema": registry["schema"], "revision": "2026-09-25", "decisions": ordered_rows}
    with REGISTRY.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(restored, indent=2, ensure_ascii=False) + "\n")
    print("restored registry; Knowify decisions require a committed governance intake before classification export")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restore-registry", action="store_true")
    args = parser.parse_args()
    raise SystemExit(restore_registry() if args.restore_registry else main())
