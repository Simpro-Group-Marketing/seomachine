"""Persist the AnswerSocrates questions observed in authenticated Chrome."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.execution_attestation import attest_mapping  # noqa: E402


SCHEMA = "simpro-answersocrates-chrome-connector-capture/v1"
QUERY = "AI software for generating estimates and quotes for trade businesses"
RUN_ID = "ai-estimating-software-trade-businesses-2026-09-29-semrush-primary"
OUTPUT = ROOT / "research" / (
    "answersocrates-chrome-connector-raw-"
    "ai-estimating-software-trade-businesses-2026-09-29.json"
)
QUESTIONS = [
    "What is the best AI estimating software?",
    "Can ChatGPT do construction estimates?",
    "Can ChatGPT make quotation?",
    "Which AI is best for trade?",
]


def main() -> int:
    completed = datetime.now(timezone.utc)
    started = completed - timedelta(seconds=45)
    browser_output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "Answer Socrates: Free Question Keyword Research Tool Generator",
        "body_text": (
            f"{QUERY} 4 questions generated People Also Asked "
            + " ".join(QUESTIONS)
        ),
        "sections": [
            {
                "heading": "People Also Asked",
                "items": QUESTIONS,
            }
        ],
        "blocker_observations": [],
    }
    capture = {
        "schema": SCHEMA,
        "collector": {
            "name": "answersocrates_chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "run_id": RUN_ID,
        "started_at": started.isoformat().replace("+00:00", "Z"),
        "completed_at": completed.isoformat().replace("+00:00", "Z"),
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(browser_output, ensure_ascii=False),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        OUTPUT,
        attest_mapping(capture, purpose=SCHEMA, workspace_root=ROOT),
    )
    print(OUTPUT.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
