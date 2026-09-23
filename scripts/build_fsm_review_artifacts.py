"""Build plan fulfillment and machine reviews for the 2026 FSM rewrite.

The builder binds all outputs to the current article, editorial plan, and proof
sidecar. It also reruns the deterministic plan/content checks used to decide
whether each reviewer can truthfully return a completed, zero-finding result.
"""
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

from data_sources.modules import (
    ai_copy_linter,
    blog_strategy_guard,
    early_artifact_guard,
    faq_answer_quality_guard,
    faq_proof_guard,
    public_research_link_guard,
    source_quality_guard,
)
from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.orchestration import check_file as check_plan_file
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)

SLUG = "best-field-service-management-software"
DATE = "2026-09-22"
ASSEMBLY_DATE = "2026-09-23"
SERP_DATE = "2026-09-23"

ARTICLE = ROOT / "rewrites" / "best-field-service-management-software-rewrite-2026-08-28.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
SERP = ROOT / "research" / f"serp-evidence-{SLUG}-{SERP_DATE}.json"
CONTEXT_REQUEST = ROOT / "research" / f"context-request-{SLUG}.json"

FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
REVIEW_PLAN = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
REVIEW_ARTICLE = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"

RESPONSIVE_TABLE_HANDOFF_TYPES = (
    "responsive buyer-route matrix",
    "responsive comparison matrix",
    "responsive buyer scorecard",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_markdown_table_delimiter(line: str) -> bool:
    """Return whether a line is a complete Markdown table delimiter row."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return False
    cells = stripped[1:-1].split("|")
    if len(cells) < 2:
        return False
    for cell in cells:
        marker = cell.strip().strip(":")
        if len(marker) < 3 or set(marker) != {"-"}:
            return False
    return True


def responsive_table_handoffs(article: str) -> dict[str, int]:
    """Count complete task-approved responsive CMS handoffs by table type."""
    lines = [line.strip() for line in article.splitlines()]
    result: dict[str, int] = {}
    for handoff_type in RESPONSIVE_TABLE_HANDOFF_TYPES:
        prefix = f"[CMS MODULE PLACEHOLDER | type: {handoff_type} |"
        result[handoff_type] = sum(
            1
            for line in lines
            if line.startswith(prefix)
            and "narrow-screen treatment:" in line
            and "behavior:" in line
            and line.endswith("]")
        )
    return result


def repository_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def exact_slice(content: str, start: str, end: str) -> str:
    """Return one exact, visible article excerpt between unique anchors."""
    start_index = content.index(start)
    end_index = content.index(end, start_index)
    excerpt = content[start_index:end_index].strip()
    if len(excerpt.split()) < 4:
        raise ValueError(f"Excerpt beginning {start!r} is not substantive")
    return excerpt


def fulfillment_excerpts(article: str) -> dict[str, str]:
    return {
        "five-route-shortlist": exact_slice(
            article,
            "| Buyer situation | Starting shortlist | Why these tools merit evaluation | First disqualifying issue to test |",
            "For trade contractors coordinating service and project work in one operating model",
        ),
        "operating-model-matrix": exact_slice(
            article,
            "| Tool | Operating model | Team and workflow complexity | Orientation | Principal mismatch | First demo test |",
            "The matrix is a routing summary.",
        ),
        "role-based-demo-pack": exact_slice(
            article,
            "Build one reusable demo pack before contacting vendors.",
            "Ask each vendor to perform the work live.",
        ),
        "buyer-owned-scorecard": exact_slice(
            article,
            "Use the buyer scorecard after pass-or-fail requirements remove obvious mismatches.",
            "## Frequently asked questions",
        ),
    }


def finding(
    *,
    finding_id: str,
    priority: str,
    category: str,
    location: str,
    evidence_anchor: str,
    recommendation: str,
    proof_risk: str,
    protected_span: bool = False,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "priority": priority,
        "category": category,
        "location": location,
        "evidence_anchor": evidence_anchor,
        "recommendation": recommendation,
        "proof_risk": proof_risk,
        "protected_span": protected_span,
    }


def from_guard(
    row: Mapping[str, Any],
    *,
    prefix: str,
    index: int,
    default_category: str,
) -> dict[str, Any]:
    severity = str(row.get("severity") or "error").casefold()
    priority = "high" if severity == "error" else "low"
    line = row.get("line")
    location = f"article line {line}" if isinstance(line, int) else str(row.get("location") or ARTICLE.relative_to(ROOT))
    anchor = str(row.get("match") or row.get("message") or row.get("rule_id") or "guard finding")
    return finding(
        finding_id=f"{prefix}-{row.get('rule_id', 'finding')}-{index}",
        priority=priority,
        category=default_category,
        location=location,
        evidence_anchor=anchor,
        recommendation=str(row.get("suggestion") or "Resolve the guard finding and rerun the review."),
        proof_risk=str(row.get("message") or "The current artifact does not satisfy its governing contract."),
    )


def responses(findings_by_agent: Mapping[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for agent in AGENT_ROSTER:
        agent_findings = findings_by_agent.get(agent, [])
        result.append(
            {
                "agent": agent,
                "status": "changes_requested" if agent_findings else "completed",
                "findings": agent_findings,
            }
        )
    return result


def add_guard_findings(
    target: dict[str, list[dict[str, Any]]],
    *,
    agent: str,
    prefix: str,
    category: str,
    rows: Iterable[Mapping[str, Any]],
) -> None:
    for index, row in enumerate(rows, start=1):
        target.setdefault(agent, []).append(
            from_guard(row, prefix=prefix, index=index, default_category=category)
        )


def plan_review_findings(run_id: str) -> dict[str, list[dict[str, Any]]]:
    rows = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP,
        assembly_date=ASSEMBLY_DATE,
        expected_run_id=run_id,
        workspace_root=ROOT,
    )
    result: dict[str, list[dict[str, Any]]] = {}
    add_guard_findings(
        result,
        agent="Content Analyzer",
        prefix="plan",
        category="editorial_plan_contract",
        rows=rows,
    )
    return result


def article_review_findings() -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}

    deterministic_checks: tuple[
        tuple[str, str, str, Callable[[], list[Mapping[str, Any]]]], ...
    ] = (
        (
            "Editor",
            "article-faq-quality",
            "faq_answer_quality",
            lambda: faq_answer_quality_guard.check_file(str(ARTICLE)),
        ),
        (
            "Public Copy Boundary Reviewer",
            "article-faq-proof",
            "faq_proof",
            lambda: faq_proof_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR)),
        ),
        (
            "Editor",
            "article-ai-copy",
            "copy_quality",
            lambda: ai_copy_linter.lint_file(str(ARTICLE), profile="simpro-web", fail_on="error"),
        ),
        (
            "Content Analyzer",
            "article-early-artifact",
            "answer_first_structure",
            lambda: early_artifact_guard.check_file(str(ARTICLE)),
        ),
        (
            "Content Analyzer",
            "article-source-quality",
            "source_quality",
            lambda: source_quality_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR)),
        ),
        (
            "Public Copy Boundary Reviewer",
            "article-public-research",
            "public_research_proof",
            lambda: public_research_link_guard.check_file(str(ARTICLE), proof_sidecar=str(SIDECAR)),
        ),
        (
            "Keyword Mapper",
            "article-commercial-strategy",
            "commercial_strategy",
            lambda: blog_strategy_guard.check_file(
                str(ARTICLE),
                proof_sidecar=str(SIDECAR),
                context_request=str(CONTEXT_REQUEST),
                require_strategy=True,
            ),
        ),
    )
    for agent, prefix, category, check in deterministic_checks:
        add_guard_findings(
            result,
            agent=agent,
            prefix=prefix,
            category=category,
            rows=check(),
        )

    article = ARTICLE.read_text(encoding="utf-8")
    if "Supporting links appear where a factual claim requires public evidence." in article:
        result.setdefault("Public Copy Boundary Reviewer", []).append(
            finding(
                finding_id="article-public-copy-editorial-process-leakage",
                priority="high",
                category="reader_facing_boundary",
                location="Frequently asked questions introduction",
                evidence_anchor="Supporting links appear where a factual claim requires public evidence.",
                recommendation="Remove the source-governance sentence from public copy; keep proof-routing decisions in the validation sidecar.",
                proof_risk="The sentence explains the publishing workflow to readers instead of answering an ICP question.",
            )
        )

    markdown_tables = sum(
        1 for line in article.splitlines() if is_markdown_table_delimiter(line)
    )
    responsive_handoffs = responsive_table_handoffs(article)
    complete_handoffs = sum(responsive_handoffs.values())
    handoff_shape_valid = all(
        count == 1 for count in responsive_handoffs.values()
    )
    if markdown_tables != complete_handoffs or not handoff_shape_valid:
        handoff_summary = ", ".join(
            f"{name}={count}" for name, count in responsive_handoffs.items()
        )
        result.setdefault("Editor", []).append(
            finding(
                finding_id="article-editor-mobile-table-treatment-incomplete",
                priority="high",
                category="accessibility_and_usability",
                location="responsive CMS handoffs for article tables",
                evidence_anchor=(
                    f"Article contains {markdown_tables} Markdown tables and "
                    f"{complete_handoffs} complete responsive-table handoffs "
                    f"({handoff_summary})."
                ),
                recommendation="Add explicit accessible mobile card treatment for every table that lacks one, without changing the approved table content.",
                proof_risk="The implementation handoff does not yet guarantee usable table content on narrow screens, which is an acceptance criterion.",
            )
        )

    return result


def build_review(
    phase: str,
    *,
    run_id: str,
    created_at: str,
    commit: str,
    findings_by_agent: Mapping[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    return build_machine_review(
        run_id=run_id,
        workflow_stage="rewrite_review",
        phase=phase,
        command="scripts/build_fsm_review_artifacts.py",
        repository_commit=commit,
        editorial_plan_path=PLAN,
        article_path=ARTICLE,
        proof_sidecar_path=SIDECAR,
        responses=responses(findings_by_agent),
        created_at=created_at,
    )


def main() -> int:
    article = ARTICLE.read_bytes().decode("utf-8")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    serp = json.loads(SERP.read_text(encoding="utf-8"))
    run_id = str(serp.get("run_id") or "").strip()
    if not run_id:
        raise ValueError("SERP evidence must provide the canonical run_id")

    plan_hash = sha256_file(PLAN)
    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "article_sha256": hashlib.sha256(article.encode("utf-8")).hexdigest(),
        "editorial_plan_sha256": plan_hash,
        "contributions": [
            {"contribution_id": contribution_id, "actual_excerpt": excerpt}
            for contribution_id, excerpt in fulfillment_excerpts(article).items()
        ],
    }
    fulfillment_findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=article,
    )
    if fulfillment_findings:
        for row in fulfillment_findings:
            print("FULFILLMENT FINDING:", json.dumps(row, sort_keys=True))
        return 1
    atomic_write_json(FULFILLMENT, fulfillment)

    created_at = now()
    commit = repository_commit()
    plan_findings = plan_review_findings(run_id)
    article_findings = article_review_findings()
    write_machine_review(
        REVIEW_PLAN,
        build_review(
            "plan",
            run_id=run_id,
            created_at=created_at,
            commit=commit,
            findings_by_agent=plan_findings,
        ),
    )
    write_machine_review(
        REVIEW_ARTICLE,
        build_review(
            "article",
            run_id=run_id,
            created_at=created_at,
            commit=commit,
            findings_by_agent=article_findings,
        ),
    )

    plan_count = sum(len(rows) for rows in plan_findings.values())
    article_count = sum(len(rows) for rows in article_findings.values())
    print(f"run_id         : {run_id}")
    print(f"fulfillment     : {FULFILLMENT.relative_to(ROOT).as_posix()} (0 findings)")
    print(f"plan review     : {REVIEW_PLAN.relative_to(ROOT).as_posix()} ({plan_count} findings)")
    print(f"article review  : {REVIEW_ARTICLE.relative_to(ROOT).as_posix()} ({article_count} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
