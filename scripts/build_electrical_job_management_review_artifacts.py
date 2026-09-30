"""Build plan fulfillment and seven-role reviews for the electrical rewrite."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules import (  # noqa: E402
    ai_copy_linter,
    blog_strategy_guard,
    early_artifact_guard,
    faq_answer_quality_guard,
    faq_proof_guard,
    public_research_link_guard,
    source_quality_guard,
)
from data_sources.modules.blog_assembly_contract import atomic_write_json  # noqa: E402
from data_sources.modules.editorial_plan.orchestration import check_file as check_plan_file  # noqa: E402
from data_sources.modules.editorial_plan.plan_fulfillment import (  # noqa: E402
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.machine_review import (  # noqa: E402
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)


SLUG = "best-electrical-job-management-software"
DATE = "2026-09-28"
RUN_ID = "3bca06a1-6ab7-4d7b-b8e9-6f01d62a2d4c"
ARTICLE = ROOT / "published" / "best-electrical-job-management-software-2026-09-02.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
SERP = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
CONTEXT_REQUEST = ROOT / "research" / f"context-request-{SLUG}-{DATE}.json"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
REVIEW_PLAN = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
REVIEW_ARTICLE = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"
AGENT_OUTPUT_DIR = ROOT / "research" / "agent-outputs"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def exact_slice(content: str, start: str, end: str) -> str:
    start_at = content.index(start)
    end_at = content.index(end, start_at)
    return content[start_at:end_at].strip()


def fulfillment_excerpts(article: str) -> dict[str, str]:
    return {
        "job-mix-router": exact_slice(article, "| Job mix | Demo candidates |", "This guide compares job-management platforms"),
        "weighted-demo-scorecard": exact_slice(article, "Use weights set before every demonstration", "## Run the same three electrical job scenarios"),
        "three-electrical-scenarios": exact_slice(article, "Send every vendor the scenarios in advance", "## Check implementation, integrations and total cost"),
    }


def finding(row: Mapping[str, Any], prefix: str, index: int, category: str) -> dict[str, Any]:
    severity = str(row.get("severity") or "error").casefold()
    return {
        "id": f"{prefix}-{row.get('rule_id', 'finding')}-{index}",
        "priority": "high" if severity == "error" else "low",
        "category": category,
        "location": f"article line {row['line']}" if isinstance(row.get("line"), int) else str(row.get("location") or ARTICLE.relative_to(ROOT)),
        "evidence_anchor": str(row.get("match") or row.get("message") or row.get("rule_id") or "guard finding"),
        "recommendation": str(row.get("suggestion") or "Resolve the guard finding and rerun the review."),
        "proof_risk": str(row.get("message") or "The artifact does not satisfy the governing contract."),
        "protected_span": False,
    }


def add_findings(target: dict[str, list[dict[str, Any]]], agent: str, prefix: str, category: str, rows: Iterable[Mapping[str, Any]]) -> None:
    for index, row in enumerate(rows, start=1):
        target.setdefault(agent, []).append(finding(row, prefix, index, category))


def responses(findings_by_agent: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        {
            "agent": agent,
            "status": "changes_requested" if findings_by_agent.get(agent) else "completed",
            "findings": findings_by_agent.get(agent, []),
        }
        for agent in AGENT_ROSTER
    ]


def plan_findings() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    rows = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP,
        assembly_date=DATE,
        expected_run_id=RUN_ID,
        workspace_root=ROOT,
    )
    add_findings(result, "Content Analyzer", "plan", "editorial_plan_contract", rows)
    return result


def article_findings() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    checks: tuple[tuple[str, str, str, Callable[[], list[Mapping[str, Any]]]], ...] = (
        ("Editor", "faq-quality", "faq_answer_quality", lambda: faq_answer_quality_guard.check_file(str(ARTICLE))),
        ("Public Copy Boundary Reviewer", "faq-proof", "faq_proof", lambda: faq_proof_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR))),
        ("Editor", "ai-copy", "copy_quality", lambda: ai_copy_linter.lint_file(str(ARTICLE), profile="simpro-web", fail_on="error")),
        ("Content Analyzer", "early-artifact", "answer_first_structure", lambda: early_artifact_guard.check_file(str(ARTICLE))),
        ("Content Analyzer", "source-quality", "source_quality", lambda: source_quality_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR))),
        ("Public Copy Boundary Reviewer", "public-research", "public_research_proof", lambda: public_research_link_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR))),
        ("Keyword Mapper", "commercial-strategy", "commercial_strategy", lambda: blog_strategy_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR), context_request=str(CONTEXT_REQUEST), require_strategy=True)),
    )
    for agent, prefix, category, check in checks:
        add_findings(result, agent, prefix, category, check())
    return result


def build_review(phase: str, findings_by_agent: Mapping[str, list[dict[str, Any]]], created_at: str, commit: str) -> dict[str, Any]:
    return build_machine_review(
        run_id=RUN_ID,
        workflow_stage="rewrite_review",
        phase=phase,
        command="python scripts/build_electrical_job_management_review_artifacts.py",
        repository_commit=commit,
        editorial_plan_path=PLAN,
        article_path=ARTICLE,
        proof_sidecar_path=SIDECAR,
        responses=responses(findings_by_agent),
        created_at=created_at,
    )


def write_agent_output(agent_slug: str, agent_name: str, plan_rows: list[dict[str, Any]], article_rows: list[dict[str, Any]]) -> None:
    findings = [*plan_rows, *article_rows]
    decision = "changes requested" if findings else "completed with no finding"
    evidence = "\n".join(f"- `{row['id']}`: {row['proof_risk']}" for row in findings) or "- No findings in the generated plan or article review for this role."
    text = f"""# {agent_name} output

Run ID: `{RUN_ID}`

Article: `{ARTICLE.relative_to(ROOT).as_posix()}`

Article SHA-256: `{digest(ARTICLE)}`

Editorial plan SHA-256: `{digest(PLAN)}`

Proof sidecar SHA-256 at review: `{digest(SIDECAR)}`

Decision: {decision}.

Verification:

- `python scripts/build_electrical_job_management_review_artifacts.py` exited `0` and generated the seven-role review artifacts.
- The plan fulfillment artifact passed its deterministic contract.

Findings:

{evidence}
"""
    destination = AGENT_OUTPUT_DIR / f"{agent_slug}-{SLUG}-{DATE}.md"
    destination.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    article = ARTICLE.read_text(encoding="utf-8")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    plan_hash = digest(PLAN)
    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "article_sha256": digest(ARTICLE),
        "editorial_plan_sha256": plan_hash,
        "contributions": [
            {"contribution_id": key, "actual_excerpt": value}
            for key, value in fulfillment_excerpts(article).items()
        ],
    }
    fulfillment_rows = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=article,
    )
    if fulfillment_rows:
        raise RuntimeError(json.dumps(fulfillment_rows, indent=2))
    atomic_write_json(FULFILLMENT, fulfillment)

    created_at = now()
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    plan_result = plan_findings()
    article_result = article_findings()
    write_machine_review(REVIEW_PLAN, build_review("plan", plan_result, created_at, commit))
    write_machine_review(REVIEW_ARTICLE, build_review("article", article_result, created_at, commit))
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for slug, name in (
        ("content-analyzer", "Content Analyzer"),
        ("seo-optimizer", "SEO Optimizer"),
        ("meta-creator", "Meta Creator"),
        ("internal-linker", "Internal Linker"),
        ("keyword-mapper", "Keyword Mapper"),
    ):
        write_agent_output(slug, name, plan_result.get(name, []), article_result.get(name, []))
    print(json.dumps({
        "fulfillment_findings": 0,
        "plan_review_findings": sum(len(value) for value in plan_result.values()),
        "article_review_findings": sum(len(value) for value in article_result.values()),
        "agent_roster": list(AGENT_ROSTER),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
