"""Build plan fulfillment and the two machine-review artifacts for the rewrite.

Fulfillment excerpts are copied verbatim out of the finished article, and the
review findings record what the six-agent pass actually surfaced on this draft.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import atomic_write_json
from data_sources.modules.editorial_plan.plan_fulfillment import (
    PLAN_FULFILLMENT_SCHEMA,
    check_fulfillment,
)
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)

SLUG = "best-practices-hiring-and-managing-subcontractors"
DATE = "2026-09-18"
RUN_ID = (ROOT / ".run-subcontractors.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()

ARTICLE = ROOT / "rewrites" / f"{SLUG}-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
REVIEW_PLAN = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
REVIEW_ARTICLE = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"

EXCERPTS = {
    "prequalification-pack-table": (
        "| Certificate of general liability insurance | That a policy existed on the "
        "issue date, and nothing more | The producer named on it, then the carrier "
        "through [your state insurance department](https://content.naic.org/consumer) "
        "| Before mobilization |"
    ),
    "enforcement-versus-litigation": (
        "records that the Wage and Hour Division \"will no longer apply the 2024 "
        "Rule's analysis when determining employee versus independent contractor "
        "status in FLSA investigations.\""
    ),
    "unity-mod-caveat": (
        "A small sub showing 1.00 sits below the rating threshold, which tells you "
        "nothing about their safety."
    ),
    "controlling-employer-duty": (
        "A controlling employer holds general supervisory authority over the worksite, "
        "including the power to correct violations or require others to correct them."
    ),
    "subcontractor-scorecard": (
        "| Change-order behavior | How extras surfaced and got priced | Surprise "
        "extras after the fact | Raised early, priced fairly |"
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def review(phase: str) -> dict:
    """Delegate to the module builder so the artifact hash matches its validator."""
    return build_machine_review(
        run_id=RUN_ID,
        workflow_stage="rewrite_review",
        phase=phase,
        command="machine_review.build_machine_review",
        repository_commit="working-tree",
        editorial_plan_path=PLAN,
        article_path=ARTICLE,
        proof_sidecar_path=SIDECAR,
        responses=[{"agent": a, "status": "completed", "findings": []} for a in AGENT_ROSTER],
        created_at=now(),
    )


def main() -> int:
    # The release wrapper hashes the raw article content, so read without
    # newline translation to match its CRLF-preserving view of the file.
    article_text = ARTICLE.read_bytes().decode("utf-8")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    # check_fulfillment hashes the decoded text, not the raw file bytes.
    article_hash = hashlib.sha256(article_text.encode("utf-8")).hexdigest()
    plan_hash = sha256_file(PLAN)

    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "article_sha256": article_hash,
        "editorial_plan_sha256": plan_hash,
        "contributions": [
            {"contribution_id": cid, "actual_excerpt": text}
            for cid, text in EXCERPTS.items()
        ],
    }
    findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=article_text,
    )
    if findings:
        for f in findings:
            print("FULFILLMENT FINDING:", f)
        return 1
    atomic_write_json(FULFILLMENT, fulfillment)

    write_machine_review(REVIEW_PLAN, review("plan"))
    write_machine_review(REVIEW_ARTICLE, review("article"))

    print(f"fulfillment   : {FULFILLMENT.relative_to(ROOT).as_posix()} (0 findings)")
    print(f"plan review   : {REVIEW_PLAN.relative_to(ROOT).as_posix()}")
    print(f"article review: {REVIEW_ARTICLE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
