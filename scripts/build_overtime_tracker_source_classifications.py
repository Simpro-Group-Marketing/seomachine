"""Export registry-bound source classifications for the overtime tracker draft."""
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

SLUG = "overtime-tracker"
DATE = "2026-09-23"
REGISTRY = ROOT / "context" / "source-classification-decisions.json"
OUT_DIR = ROOT / "research" / "source-classifications" / f"{SLUG}-{DATE}"

URLS = (
    "https://www.dol.gov/agencies/whd/fact-sheets/23-flsa-overtime-pay",
    "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-B/part-778/subpart-A/section-778.101",
    "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-B/part-778/subpart-B/section-778.107",
    "https://www.ecfr.gov/current/title-29/subtitle-B/chapter-V/subchapter-A/part-516/subpart-A/section-516.2",
    "https://www.clockshark.com/tour/time-tracking-software",
    "https://www.clockshark.com/tour/mobile-time-tracking",
    "https://www.clockshark.com/tour/timesheet-approvals",
    "https://www.clockshark.com/videos/overtime-rules-to-manage-california-overtime",
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
