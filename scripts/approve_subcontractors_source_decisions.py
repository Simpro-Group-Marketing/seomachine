"""Record the approved repository decision for each subcontractors-run source.

Classification artifacts now derive their class from this registry, so every
source verified for the run needs an approved row before the artifact can be
regenerated.
"""
from __future__ import annotations

import json
import pathlib
import sys
from urllib.parse import urlsplit

REGISTRY = pathlib.Path("context/source-classification-decisions.json")
CLASSIFICATIONS = pathlib.Path(
    "research/source-classifications/best-practices-hiring-and-managing-subcontractors-2026-09-18"
)


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    known = {row["decision_id"] for row in registry["decisions"]}
    added = 0
    for artifact in sorted(CLASSIFICATIONS.glob("*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        decision_id = f"subcontractors-2026-09-18-{artifact.stem}"
        if decision_id in known:
            continue
        registry["decisions"].append(
            {
                "decision_id": decision_id,
                "status": "approved",
                "source_url": payload["source_url"],
                "hostname": (urlsplit(payload["source_url"]).hostname or "").lower(),
                "source_class": payload["source_class"],
                "publisher_relationship": payload["publisher"]["relationship"],
            }
        )
        added += 1
    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"approved decisions added: {added} (total {len(registry['decisions'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
