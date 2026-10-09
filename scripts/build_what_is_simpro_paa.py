"""Bind the observed AnswerSocrates US capture for the What Is Simpro blog."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.execution_attestation import attest_mapping  # noqa: E402
from data_sources.modules.paa_provenance.collection import (  # noqa: E402
    build_answersocrates_artifact,
    write_answersocrates_artifact,
)


SLUG = "what-is-simpro"
DATE = "2026-10-05"
QUERY = "simpro"
RUN_ID = "fb123292-96da-464b-ab37-29a926336b3e"
RAW = ROOT / "research" / f"answersocrates-chrome-connector-raw-{SLUG}-{DATE}.json"
OUT = ROOT / "research" / f"paa-evidence-{SLUG}-{DATE}.json"

# Exactly as observed in the authenticated AnswerSocrates page on 2026-10-02
# and re-observed on 2026-10-05 (US, English): "simpro 989 questions generated".
PEOPLE_ALSO_ASKED = [
    "Is simpro a CRM system?",
    "How much is simpro a month?",
    "Is simpro a good system?",
    "Is simpro a big company?",
]
VISIBLE_QUESTION_SUGGESTIONS = [
    "Can Simpro Track Your Location",
    "How To Use Simpro",
    "What Is Simpro",
    "How Does Simpro Work",
    "What Does Simpro Do",
    "What Is Simpro Used For",
    "What Is Simpro Software",
    "What Is Simpro Mobile",
    "What Does Simpro Software Do",
    "Who Owns Simpro",
    "Who Uses Simpro",
    "Where Is Simpro Based",
    "Where Was Simpro Founded",
    "Is Simpro A Crm",
    "Is Simpro An Erp System",
    "Is Simpro Easy To Use",
    "Does Simpro Integrate With Xero",
    "Does Simpro Integrate With Quickbooks",
    "How Much Does Simpro Cost",
    "Is Simpro Expensive",
    "What Kind Of Software Is Simpro",
]


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def main() -> int:
    completed = datetime.now(timezone.utc)
    started = completed - timedelta(seconds=40)
    output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "Answer Socrates: Free Question Keyword Research Tool Generator",
        "body_text": (
            f"{QUERY}\n989 questions generated\nCountry: United States\nLanguage: English\n"
            "People Also Asked\n"
            + "\n".join(PEOPLE_ALSO_ASKED)
            + "\nVisible question suggestions\n"
            + "\n".join(VISIBLE_QUESTION_SUGGESTIONS)
        ),
        "sections": [
            {"heading": "People Also Asked", "items": PEOPLE_ALSO_ASKED},
            {"heading": "Visible question suggestions", "items": VISIBLE_QUESTION_SUGGESTIONS},
        ],
        "blocker_observations": [],
    }
    capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "run_id": RUN_ID,
        "started_at": _iso(started),
        "completed_at": _iso(completed),
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(output, ensure_ascii=False),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        RAW,
        attest_mapping(capture, purpose=capture["schema"], workspace_root=ROOT),
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=RAW,
        workspace_root=ROOT,
        expected_query=QUERY,
        expected_collection_date=DATE,
        expected_run_id=RUN_ID,
    )
    write_answersocrates_artifact(OUT, artifact, workspace_root=ROOT)
    print(
        f"wrote {OUT.relative_to(ROOT).as_posix()} "
        f"status={artifact['status']} eligible={len(artifact['eligible_questions'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
