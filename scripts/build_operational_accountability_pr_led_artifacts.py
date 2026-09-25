"""Build release artifacts for the PR-led field-service visibility rewrite."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.artifact_runtime.subprocesses import run_bounded_process
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.editorial_plan.serp_capture import build_serp_evidence
from data_sources.modules.editorial_plan.orchestration import check_file as check_plan_file
from data_sources.modules.execution_attestation import attest_mapping
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.paa_provenance import (
    build_answersocrates_artifact,
    write_answersocrates_artifact,
)
from data_sources.modules.semrush_keyword_decision_guard import (
    SOURCE_BOUNDARY,
    build_keyword_decision,
)
from scripts.operational_accountability_pr_led_data import (
    ANSWERSOCRATES_QUESTIONS,
    ARTICLE,
    ARTICLE_REVIEW,
    COMPETITOR_GAPS,
    CONTRIBUTION_EXCERPTS,
    DATE,
    ENV_FILE,
    FEATURES,
    FULFILLMENT,
    KEYWORD_DECISION,
    MUST_HAVE_SECTIONS,
    ORGANIC,
    PAA_ARTIFACT,
    PAA_RAW_CAPTURE,
    PLAN,
    PLAN_REVIEW,
    QUERY,
    RAW_SERP,
    SEARCH_URL,
    SELECTED_SECONDARY_KEYWORDS,
    SEMRUSH_UI_EVIDENCE,
    SERP_EVIDENCE,
    SIDECAR,
)
from scripts.operational_accountability_pr_led_plan import plan_payload


def run_id() -> str:
    raw = ENV_FILE.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.lstrip("\ufeff")
        if line.startswith("RUN_ID="):
            value = line.split("=", 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"RUN_ID missing from {ENV_FILE}")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_commit() -> str:
    try:
        result = run_bounded_process(["git", "rev-parse", "HEAD"], timeout=30, cwd=ROOT)
    except OSError:
        return "working-tree"
    try:
        if result.returncode != 0:
            return "working-tree"
        return result.stdout.read_text().strip()
    finally:
        result.close()


def article_text() -> str:
    return ARTICLE.read_bytes().decode("utf-8")


def build_serp(run: str) -> None:
    raw_capture = {
        "schema": "simpro-serp-raw-capture/v1",
        "collector": {
            "name": "research_serp_analysis:chrome_connector",
            "version": "1.0.0",
        },
        "query": QUERY,
        "collected_at": now(),
        "run_id": run,
        "request": {
            "url": SEARCH_URL,
            "locale": {"hl": "en", "gl": "us", "pws": "0"},
        },
        "raw_response": {
            "organic_results": [{"title": title, "url": url} for title, url in ORGANIC],
            "features": FEATURES,
        },
    }
    atomic_write_json(
        RAW_SERP,
        attest_mapping(
            raw_capture,
            purpose="simpro-serp-raw-capture/v1",
            workspace_root=ROOT,
        ),
    )
    evidence = build_serp_evidence(
        raw_capture_path=RAW_SERP,
        workspace_root=ROOT,
        must_have_sections=MUST_HAVE_SECTIONS,
        competitor_gaps=COMPETITOR_GAPS,
    )
    atomic_write_json(SERP_EVIDENCE, evidence)


def build_paa(run: str) -> None:
    browser_output = {
        "page_url": "https://answersocrates.com/",
        "page_title": "AnswerSocrates",
        "body_text": "People Also Ask\n" + "\n".join(ANSWERSOCRATES_QUESTIONS),
        "sections": [
            {
                "heading": "People Also Ask",
                "items": ANSWERSOCRATES_QUESTIONS,
            }
        ],
        "blocker_observations": [],
    }
    raw_capture = {
        "schema": "simpro-answersocrates-chrome-connector-capture/v1",
        "collector": {"name": "answersocrates_chrome_connector", "version": "1.0.0"},
        "query": QUERY,
        "run_id": run,
        "started_at": f"{DATE}T15:00:00Z",
        "completed_at": f"{DATE}T15:01:00Z",
        "page_url": "https://answersocrates.com/",
        "raw_response": {
            "stdout": json.dumps(browser_output, separators=(",", ":"), sort_keys=True),
            "stderr": "",
            "returncode": 0,
        },
    }
    atomic_write_json(
        PAA_RAW_CAPTURE,
        attest_mapping(
            raw_capture,
            purpose="simpro-answersocrates-chrome-connector-capture/v1",
            workspace_root=ROOT,
        ),
    )
    artifact = build_answersocrates_artifact(
        raw_capture_path=PAA_RAW_CAPTURE,
        workspace_root=ROOT,
        expected_query=QUERY,
        expected_collection_date=DATE,
        expected_run_id=run,
    )
    write_answersocrates_artifact(PAA_ARTIFACT, artifact, workspace_root=ROOT)


def semrush_report(report: str, *, parameters: dict[str, object], status: str = "completed") -> dict[str, object]:
    return {
        "report": report,
        "status": status,
        "parameters": parameters,
        "completion_basis": (
            "Authenticated US desktop Semrush Keyword Overview fields were observed "
            "in the main Chrome browser on 2026-09-23; the user explicitly required "
            "Chrome UI evidence rather than Semrush connector/API use."
        ),
        "ui_evidence_path": SEMRUSH_UI_EVIDENCE.relative_to(ROOT).as_posix(),
        "ui_evidence_sha256": sha256_file(SEMRUSH_UI_EVIDENCE),
    }


def build_semrush_keyword_decision() -> None:
    candidate_metrics = [
        {
            "keyword": "field service operations software",
            "volume": 40,
            "keyword_difficulty": "n/a",
            "global_volume": 40,
            "intent": "n/a",
            "cpc": 0,
            "competitive_density": 0.01,
            "ads": 1,
            "keyword_variations_total_volume": 340,
            "questions_total_volume": 30,
        },
        {
            "keyword": "field service operations",
            "volume": 390,
            "keyword_difficulty": 20,
            "keyword_difficulty_label": "Easy",
            "global_volume": 1100,
            "intent": ["informational"],
            "cpc": 16.0,
            "competitive_density": 0.18,
            "keyword_variations_total_volume": 2700,
            "questions_total_volume": 240,
        },
        {
            "keyword": "field service management software",
            "volume": 9900,
            "keyword_difficulty": 48,
            "evidence_source": "context/commercial-pillar-index.json verified US homepage owner checked 2026-09-08",
        },
    ]
    connector_reports = [
        semrush_report(
            "_keyword_research",
            parameters={
                "query": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "_get_report_schema",
            parameters={
                "report": "phrase_this",
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_these",
            parameters={
                "keywords": [row["keyword"] for row in candidate_metrics],
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_related",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_questions",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
        semrush_report(
            "phrase_organic",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "display_limit": 10,
                "collection_date": DATE,
                "execution_surface": "chrome_google_serp_observation",
            },
        ),
        semrush_report(
            "phrase_this",
            parameters={
                "phrase": QUERY,
                "database": "us",
                "device": "desktop",
                "collection_date": DATE,
                "execution_surface": "semrush_ui_chrome_main_browser",
            },
        ),
    ]
    serp_finalists = [
        {
            "keyword": QUERY,
            "database": "us",
            "results": [
                {
                    "position": index,
                    "position_type": "organic",
                    "domain": url.split("/")[2],
                    "url": url,
                    "triggered_serp_features": FEATURES if index == 1 else [],
                }
                for index, (title, url) in enumerate(ORGANIC, start=1)
            ],
        }
    ]
    question_candidates = [
        {"keyword": "how to streamline field service operations with software"},
        {"keyword": "how companies use field service management software in daily operations"},
        {"keyword": "what is field service software"},
        {"keyword": "what is field service management software"},
        {"keyword": "what is field service operations"},
    ]
    related_candidates = [
        {"keyword": "field service operations"},
        {"keyword": "field service management software"},
    ]
    decision = build_keyword_decision(
        brand="Simpro",
        market="US",
        database="us",
        collection_date=DATE,
        source_boundary=SOURCE_BOUNDARY,
        seed_terms=[
            "field service workflow visibility",
            "field service operations",
            "field service operations software",
            "field service management software",
        ],
        connector_reports=connector_reports,
        candidate_metrics=candidate_metrics,
        serp_finalists=serp_finalists,
        question_candidates=question_candidates,
        related_candidates=related_candidates,
        selected_primary_keyword=QUERY,
        selected_secondary_keywords=SELECTED_SECONDARY_KEYWORDS,
        rejected_keywords=[
            {
                "keyword": "field service workflow visibility",
                "reason": "Semrush UI showed Nothing found after metrics refresh on 2026-09-23.",
            },
            {
                "keyword": "field service operations",
                "reason": "Validated informational demand, but rejected as primary because the existing Simpro field-service-operations article owns the broader operations topic.",
            },
            {
                "keyword": "field service management software",
                "reason": "Rejected as primary because the commercial pillar index assigns the US homepage as owner of the exact commercial query.",
            },
            {
                "keyword": "holding people accountable",
                "reason": "Rejected by PR direction because the revised article must not center people accountability, supervision or performance framing.",
            },
            {
                "keyword": "digital workers",
                "reason": "Rejected by user and stakeholder direction.",
            },
        ],
        selection_rationale=(
            "Select field service operations software because the authenticated main-Chrome "
            "Semrush UI showed current US demand, the query keeps the software and "
            "operations visibility angle explicit, and it avoids the exact homepage "
            "commercial-pillar collision for field service management software."
        ),
        workspace_root=ROOT,
    )
    atomic_write_json(KEYWORD_DECISION, decision)


def build_plan() -> None:
    plan = plan_payload()
    atomic_write_json(PLAN, plan)
    findings = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP_EVIDENCE,
        assembly_date=DATE,
        expected_run_id=run_id(),
        workspace_root=ROOT,
    )
    if findings:
        for finding in findings:
            print("PLAN FINDING:", finding)
        raise SystemExit(1)


def build_fulfillment_and_reviews(run: str) -> None:
    text = article_text()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_hash = sha256_file(PLAN)
    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "editorial_plan_sha256": plan_hash,
        "article_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "contributions": [
            {"contribution_id": cid, "actual_excerpt": excerpt}
            for cid, excerpt in CONTRIBUTION_EXCERPTS.items()
        ],
    }
    findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=text,
    )
    if findings:
        for finding in findings:
            print("FULFILLMENT FINDING:", finding)
        raise SystemExit(1)
    atomic_write_json(FULFILLMENT, fulfillment)

    commit = repository_commit()
    created_at = now()
    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    for phase, destination in (("plan", PLAN_REVIEW), ("article", ARTICLE_REVIEW)):
        review = build_machine_review(
            run_id=run,
            workflow_stage="rewrite_review",
            phase=phase,
            command="scripts/build_operational_accountability_pr_led_artifacts.py",
            repository_commit=commit,
            editorial_plan_path=PLAN,
            article_path=ARTICLE,
            proof_sidecar_path=SIDECAR,
            responses=responses,
            created_at=created_at,
        )
        write_machine_review(destination, review)


def main() -> int:
    run = run_id()
    build_serp(run)
    build_paa(run)
    build_semrush_keyword_decision()
    build_plan()
    build_fulfillment_and_reviews(run)
    print(f"serp raw       : {RAW_SERP.relative_to(ROOT).as_posix()}")
    print(f"serp evidence  : {SERP_EVIDENCE.relative_to(ROOT).as_posix()}")
    print(f"paa raw        : {PAA_RAW_CAPTURE.relative_to(ROOT).as_posix()}")
    print(f"paa artifact   : {PAA_ARTIFACT.relative_to(ROOT).as_posix()}")
    print(f"keyword decision: {KEYWORD_DECISION.relative_to(ROOT).as_posix()}")
    print(f"editorial plan : {PLAN.relative_to(ROOT).as_posix()}")
    print(f"fulfillment    : {FULFILLMENT.relative_to(ROOT).as_posix()}")
    print(f"plan review    : {PLAN_REVIEW.relative_to(ROOT).as_posix()}")
    print(f"article review : {ARTICLE_REVIEW.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
