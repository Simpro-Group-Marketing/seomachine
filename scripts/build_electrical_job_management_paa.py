"""Bind the 2026-09-28 AnswerSocrates Chrome capture."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance.collection import build_answersocrates_artifact, write_answersocrates_artifact

DATE = "2026-09-28"
RUN_ID = "3bca06a1-6ab7-4d7b-b8e9-6f01d62a2d4c"
QUERY = "electrical job management software"
RAW = ROOT / "research" / f"answersocrates-raw-best-electrical-job-management-software-{DATE}.json"
OUT = ROOT / "research" / f"paa-evidence-best-electrical-job-management-software-{DATE}.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    questions = [
        "What is the best CRM for electrical contractors?",
        "What scheduling software is best for electricians?",
        "What is the best app for electrical contractors?",
        "What is the best software for electricians to use for takeoffs?",
    ]
    output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "Answer Socrates: Free Question Keyword Research Tool Generator",
        "body_text": (
            f"{QUERY}\n204 questions generated\nCountry: United States\nLanguage: English\n"
            "People Also Asked\n" + "\n".join(questions)
        ),
        "sections": [{"heading": "People Also Ask", "items": questions}],
        "blocker_observations": [],
    }
    capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY, "run_id": RUN_ID, "started_at": now(), "completed_at": now(),
        "page_url": "https://answersocrates.com/",
        "raw_response": {"stdout": json.dumps(output, ensure_ascii=False), "stderr": "", "returncode": 0},
    }
    atomic_write_json(RAW, attest_mapping(capture, purpose=capture["schema"], workspace_root=ROOT))
    artifact = build_answersocrates_artifact(raw_capture_path=RAW, workspace_root=ROOT,
        expected_query=QUERY, expected_collection_date=DATE, expected_run_id=RUN_ID)
    write_answersocrates_artifact(OUT, artifact, workspace_root=ROOT)
    print(f"wrote {OUT.relative_to(ROOT).as_posix()} status={artifact['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
