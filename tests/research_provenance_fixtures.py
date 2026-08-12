from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan_guard import build_serp_evidence
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.paa_provenance_guard import build_answersocrates_artifact


def build_answersocrates_fixture(
    root: Path,
    *,
    query: str,
    collection_date: str,
    questions: Iterable[str],
    run_id: str,
) -> dict:
    raw_path = root / "research" / f"answersocrates-raw-{run_id}.json"
    capture = attest_mapping(
        {
            "schema": "simpro-answersocrates-playwright-capture/v1",
            "collector": {
                "name": "answersocrates_playwright_collector",
                "version": "1.0.0",
            },
            "query": query,
            "run_id": run_id,
            "started_at": f"{collection_date}T14:00:00Z",
            "completed_at": f"{collection_date}T14:01:00Z",
            "page_url": "https://answersocrates.com/paa-extractor",
            "raw_response": {
                "visible_sections": [
                    {"heading": "People Also Ask", "items": list(questions)}
                ],
                "blocker_output": "",
            },
        },
        purpose="simpro-answersocrates-playwright-capture/v1",
        workspace_root=root,
    )
    atomic_write_json(raw_path, capture)
    return build_answersocrates_artifact(
        raw_capture_path=raw_path,
        workspace_root=root,
        expected_query=query,
        expected_collection_date=collection_date,
        expected_run_id=run_id,
    )


def build_serp_fixture(
    root: Path,
    *,
    query: str,
    collection_date: str,
    run_id: str,
    results: list[dict],
    features: list[str],
    must_have_sections: list[str],
    competitor_gaps: list[str] | None = None,
) -> dict:
    raw_path = root / "research" / f"serp-raw-{run_id}.json"
    capture = attest_mapping(
        {
            "schema": "simpro-serp-raw-capture/v1",
            "collector": {
                "name": "research_serp_analysis:dataforseo",
                "version": "1.0.0",
            },
            "query": query,
            "collected_at": f"{collection_date}T14:00:00Z",
            "run_id": run_id,
            "request": {
                "url": "dataforseo://serp/google/organic/live/advanced",
                "locale": {"language_code": "en", "location_code": 2840},
            },
            "raw_response": {
                "organic_results": results,
                "features": features,
            },
        },
        purpose="simpro-serp-raw-capture/v1",
        workspace_root=root,
    )
    atomic_write_json(raw_path, capture)
    return build_serp_evidence(
        raw_capture_path=raw_path,
        workspace_root=root,
        must_have_sections=must_have_sections,
        competitor_gaps=competitor_gaps or [],
    )


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
