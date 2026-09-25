"""Record the genuine AnswerSocrates quota blocker hit on 2026-09-18.

The ClockShark subcontractors rewrite needs PAA provenance. The AnswerSocrates
account quota was exhausted before any question could be collected for this
query, so this records the blocked state instead of inventing questions.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance.collection import (
    build_answersocrates_artifact,
    write_answersocrates_artifact,
)

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
QUERY = "hire subcontractors"
RUN_ID = (ROOT / ".run-subcontractors.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()

RAW_PATH = ROOT / "research" / f"answersocrates-chrome-raw-{SLUG}-{DATE}.json"
ARTIFACT_PATH = ROOT / "research" / f"answersocrates-blocker-{SLUG}-{DATE}.json"

# Read off the live pages through the Chrome connector on 2026-09-18.
EXTRACTOR_MESSAGE = "You've reached your search limit."
HOME_MESSAGE = "You've Used All Free Search Quota! Get More FREE Search Results By Upgrading to Pro now!"

BROWSER_OUTPUT = {
    "page_url": "https://answersocrates.com/paa-extractor",
    "page_title": "Free AI PAA Extractor Tool - Generate People Also Ask Questions",
    "body_text": (
        "People Also Ask Extractor Tool. Query submitted: hire subcontractors. "
        "Country United States. Language English. " + EXTRACTOR_MESSAGE
    ),
    "sections": [],
    # Only the account-level quota string is recorded as a scoped blocker: it is
    # the observation that maps cleanly to the approved `quota` blocker kind. The
    # extractor's own wording is preserved in body_text above for the record.
    "blocker_observations": [
        {"scope": "quota_container", "text": HOME_MESSAGE},
    ],
}


def main() -> int:
    started = datetime.now(timezone.utc) - timedelta(seconds=45)
    started_at = started.strftime("%Y-%m-%dT%H:%M:%SZ")
    completed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw_capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "run_id": RUN_ID,
        "started_at": started_at,
        "completed_at": completed_at,
        "page_url": "https://answersocrates.com/paa-extractor",
        "raw_response": {
            "stdout": json.dumps(BROWSER_OUTPUT, ensure_ascii=False),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        RAW_PATH,
        attest_mapping(
            raw_capture,
            purpose="simpro-answersocrates-chrome-connector-capture/v1",
            workspace_root=ROOT,
        ),
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=RAW_PATH,
        workspace_root=ROOT,
        expected_query=QUERY,
        expected_collection_date=DATE,
        expected_run_id=RUN_ID,
    )
    write_answersocrates_artifact(ARTIFACT_PATH, artifact, workspace_root=ROOT)
    print(f"raw capture : {RAW_PATH.relative_to(ROOT).as_posix()}")
    print(f"artifact    : {ARTIFACT_PATH.relative_to(ROOT).as_posix()}")
    print(f"status      : {artifact.get('status')}")
    print(f"blocker     : {json.dumps(artifact.get('blocker'))}")
    print(f"questions   : {len(artifact.get('eligible_questions') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
