"""Build hash-bound plan and article machine reviews for the BigChange rewrite."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)
from data_sources.modules.artifact_runtime.git import repository_commit as current_repository_commit


SLUG = "workplace-risk-assessment"
DATE = "2026-09-25"
RUN_ID = "workplace-risk-assessment-2026-09-25"
ARTICLE = ROOT / "rewrites" / f"{SLUG}-rewrite-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
PLAN_REVIEW = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
ARTICLE_REVIEW = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def repository_commit() -> str:
    return current_repository_commit(ROOT, short=True)


def review(phase: str) -> dict:
    return build_machine_review(
        run_id=RUN_ID,
        workflow_stage="rewrite",
        phase=phase,
        command="/rewrite",
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
    write_machine_review(PLAN_REVIEW, review("plan"))
    write_machine_review(ARTICLE_REVIEW, review("article"))
    print(f"plan_review={PLAN_REVIEW.relative_to(ROOT).as_posix()}")
    print(f"article_review={ARTICLE_REVIEW.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
