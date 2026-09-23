"""Regenerate the run's classification artifacts from the approved decisions."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

sys.path.insert(0, ".")

from data_sources.modules.source_support.common import SOURCE_DECISIONS_PATH
from data_sources.modules.source_support.persistence import (
    write_source_classification_artifact,
)

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
ROOT = pathlib.Path(".").resolve()
CLASSIFICATIONS = pathlib.Path(f"research/source-classifications/{SLUG}-{DATE}")
SIDECAR = pathlib.Path(f"research/validation-{SLUG}-{DATE}.md")


def main() -> int:
    rehash: dict[str, str] = {}
    for artifact in sorted(CLASSIFICATIONS.glob("*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        write_source_classification_artifact(
            artifact,
            source_url=payload["source_url"],
            decision_id=f"subcontractors-{DATE}-{artifact.stem}",
            decision_path=SOURCE_DECISIONS_PATH,
            workspace_root=ROOT,
        )
        rehash[artifact.as_posix()] = hashlib.sha256(artifact.read_bytes()).hexdigest()
        print("rebuilt", artifact.name)

    text = SIDECAR.read_text(encoding="utf-8")
    for path, digest in rehash.items():
        text = re.sub(
            rf"(Classification artifact: {re.escape(path)} \| Classification hash: )[0-9a-f]{{64}}",
            rf"\g<1>{digest}",
            text,
        )
    SIDECAR.write_text(text, encoding="utf-8")
    print(f"rebound {len(rehash)} classification hashes in the sidecar")
    return 0


if __name__ == "__main__":
    sys.exit(main())
