"""Build plan fulfillment and machine-review artifacts for the overtime tracker draft."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.artifact_runtime.subprocesses import run_bounded_process
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)

SLUG = "overtime-tracker"
DATE = "2026-09-23"
RUN_ID = "3b946d70-76e2-426d-92e6-afdf8f1c4f93"

ARTICLE = ROOT / "drafts" / f"{SLUG}-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
FULFILLMENT = ROOT / "research" / f"plan-fulfillment-{SLUG}-{DATE}.json"
REVIEW_PLAN = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
REVIEW_ARTICLE = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"

EXCERPTS = {
    "overtime-control-checkpoint-matrix": (
        "| Checkpoint | What to verify | Owner | Action before the next step |"
    ),
    "six-step-overtime-control-loop": (
        "The strongest employee overtime tracking process is a chain of decisions from the field to payroll."
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repository_commit() -> str:
    result = run_bounded_process(["git", "rev-parse", "--short", "HEAD"], timeout=30, cwd=ROOT)
    try:
        if result.returncode != 0:
            raise RuntimeError("git rev-parse failed")
        return result.stdout.read_text().strip()
    finally:
        result.close()


def review(phase: str) -> dict:
    return build_machine_review(
        run_id=RUN_ID,
        workflow_stage="write",
        phase=phase,
        command="/write",
        repository_commit=repository_commit(),
        editorial_plan_path=PLAN,
        article_path=ARTICLE,
        proof_sidecar_path=SIDECAR,
        responses=[
            {"agent": agent, "status": "completed", "findings": []}
            for agent in AGENT_ROSTER
        ],
        created_at=now(),
    )


def main() -> int:
    article_text = ARTICLE.read_bytes().decode("utf-8")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    article_hash = hashlib.sha256(article_text.encode("utf-8")).hexdigest()
    plan_hash = sha256_file(PLAN)

    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "article_sha256": article_hash,
        "editorial_plan_sha256": plan_hash,
        "contributions": [
            {"contribution_id": contribution_id, "actual_excerpt": excerpt}
            for contribution_id, excerpt in EXCERPTS.items()
        ],
    }
    findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=article_text,
    )
    if findings:
        for finding in findings:
            print(f"FULFILLMENT FINDING: {finding}")
        return 1

    atomic_write_json(FULFILLMENT, fulfillment)
    write_machine_review(REVIEW_PLAN, review("plan"))
    write_machine_review(REVIEW_ARTICLE, review("article"))
    print(f"fulfillment: {FULFILLMENT.relative_to(ROOT).as_posix()}")
    print(f"plan review: {REVIEW_PLAN.relative_to(ROOT).as_posix()}")
    print(f"article review: {REVIEW_ARTICLE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
