from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules import ai_copy_linter
from data_sources.modules.editorial_plan_guard import check_file as check_plan_file
from data_sources.modules.frontmatter import split_frontmatter
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.semrush_keyword_decision_guard import (
    check_file as check_keyword_file,
)


RUN_ID = "blog-run-ae3ae7605f4f7f839cfa59730c8b0c0297136f4618ba041b2959a49bab37b497"
ASSEMBLY_DATE = "2026-09-09"
ARTICLE = ROOT / "drafts" / "ai-field-service-economics-2026-09-08.md"
PLAN = ROOT / "research" / "editorial-plan-ai-field-service-economics-2026-09-08.json"
SIDECAR = ROOT / "research" / "validation-ai-field-service-economics-2026-09-08.md"
KEYWORD = ROOT / "research" / "keyword-decision-ai-field-service-economics-2026-09-08.json"
SERP = ROOT / "research" / "serp-evidence-ai-field-service-economics-2026-09-08.json"
PLAN_REVIEW = ROOT / "research" / "machine-review-ai-field-service-economics-plan-2026-09-08.json"
ARTICLE_REVIEW = ROOT / "research" / "machine-review-ai-field-service-economics-article-2026-09-08.json"


def finding(rule_id: str, message: str) -> dict[str, str]:
    return {
        "severity": "error",
        "rule_id": rule_id,
        "message": message,
        "suggestion": "Repair the frozen plan or article and rerun all six reviewers.",
    }


def response(agent: str, findings: list[dict]) -> dict:
    return {
        "agent": agent,
        "status": "completed",
        "findings": findings,
    }


def plan_responses() -> list[dict]:
    plan_findings = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP,
        assembly_date=ASSEMBLY_DATE,
        expected_run_id=RUN_ID,
    )
    keyword_findings = check_keyword_file(
        KEYWORD,
        article_path=ARTICLE,
        editorial_plan_path=PLAN,
        assembly_date=ASSEMBLY_DATE,
    )
    grouped = {agent: [] for agent in AGENT_ROSTER}
    for item in plan_findings:
        grouped["Content Analyzer"].append(dict(item))
    for item in keyword_findings:
        grouped["Keyword Mapper"].append(dict(item))
    return [response(agent, grouped[agent]) for agent in AGENT_ROSTER]


def article_responses() -> list[dict]:
    content = ARTICLE.read_text(encoding="utf-8")
    metadata, body, _ = split_frontmatter(content)
    grouped = {agent: [] for agent in AGENT_ROSTER}

    required_headings = [
        "# AI Field Service Economics: What to Measure Before You Automate",
        "## The AI Field Service Economics Scorecard",
        "## What Field Service Economics Means for a Trade Business",
        "## Where AI Can Change the Economics of a Job",
        "## Build the Business Case With Your Own Numbers",
        "## What AI Cannot Fix",
        "## A 30-Day Field Service AI Pilot",
        "## Where Simpro Lightning Fits",
    ]
    missing_headings = [heading for heading in required_headings if heading not in body]
    if missing_headings:
        grouped["Content Analyzer"].append(finding(
            "required_article_sections_missing",
            "Missing required headings: " + ", ".join(missing_headings),
        ))
    if body.count("| Dispatch and travel |") != 1 or body.count("| Job closeout and invoice timing |") != 1:
        grouped["Content Analyzer"].append(finding(
            "scorecard_rows_missing",
            "The completed economics scorecard is incomplete or duplicated.",
        ))
    if not re.search(r"(?im)^##\s+(?:faq|frequently asked questions)\s*$", body):
        grouped["Content Analyzer"].append(finding(
            "faq_section_missing",
            "The article must contain the PAA-backed FAQ section selected in the validation sidecar.",
        ))

    grouped["Editor"].extend(
        item
        for item in ai_copy_linter.lint_file(
            str(ARTICLE),
            profile="simpro-web",
            fail_on="error",
        )
        if item.get("severity") == "error"
    )

    grouped["SEO Optimizer"].extend(check_keyword_file(
        KEYWORD,
        article_path=ARTICLE,
        editorial_plan_path=PLAN,
        assembly_date=ASSEMBLY_DATE,
    ))

    expected_meta = {
        "title": "AI Field Service Economics: What to Measure Before You Automate",
        "meta_title": "AI Field Service Economics: Practical Scorecard | Simpro",
        "meta_description": "Use an AI field service economics scorecard to decide where AI can improve capacity, control service costs and protect margins across field operations.",
        "slug": "/blog/ai-field-service-economics",
    }
    for key, expected in expected_meta.items():
        if metadata.get(key) != expected:
            grouped["Meta Creator"].append(finding(
                "metadata_mismatch",
                f"Frontmatter {key} does not match the approved value.",
            ))

    body_before_faq = re.split(
        r"(?im)^##\s+Frequently Asked Questions\s*$",
        body,
        maxsplit=1,
    )[0]
    urls = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", body_before_faq)
    internal_urls = [
        url
        for url in urls
        if urlparse(url).hostname in {"simprogroup.com", "www.simprogroup.com"}
    ]
    if len(internal_urls) != 5 or len(set(internal_urls)) != 5:
        grouped["Internal Linker"].append(finding(
            "internal_link_plan_mismatch",
            "The article must contain five unique approved Simpro internal links.",
        ))

    visible_text = re.sub(r"https?://\S+", " ", body).casefold()
    mapped_terms = [
        "ai field service economics",
        "ai field service management",
        "field service automation",
        "ai field service software",
        "field service profitability",
    ]
    missing_terms = [term for term in mapped_terms if term not in visible_text]
    if missing_terms:
        grouped["Keyword Mapper"].append(finding(
            "mapped_keyword_missing",
            "Missing mapped reader-visible terms: " + ", ".join(missing_terms),
        ))

    return [response(agent, grouped[agent]) for agent in AGENT_ROSTER]


def main() -> None:
    repository_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    created_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    reviews = {
        PLAN_REVIEW: ("plan", plan_responses()),
        ARTICLE_REVIEW: ("article", article_responses()),
    }
    for path, (phase, responses) in reviews.items():
        write_machine_review(
            path,
            build_machine_review(
                run_id=RUN_ID,
                workflow_stage="draft",
                phase=phase,
                command="/write",
                repository_commit=repository_commit,
                editorial_plan_path=PLAN,
                article_path=ARTICLE,
                proof_sidecar_path=SIDECAR,
                responses=responses,
                created_at=created_at,
            ),
        )
    summary = {
        path.relative_to(ROOT).as_posix(): {
            response_row["agent"]: len(response_row["findings"])
            for response_row in responses
        }
        for path, (_, responses) in reviews.items()
    }
    print(json.dumps(summary, indent=2))
    if any(
        response_row["findings"]
        for _, responses in reviews.values()
        for response_row in responses
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
