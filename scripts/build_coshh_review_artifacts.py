"""Build plan fulfillment and the two machine-review artifacts for the COSHH rewrite.

Fulfillment excerpts are copied verbatim out of the finished article. Machine
review responses come from research/machine-review-findings-*.json, which
records what the seven-role review pass actually found on this plan and draft.
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
from data_sources.modules.machine_review import build_machine_review, write_machine_review

SLUG = "coshh-regulations"
DATE = "2026-09-24"
RUN_ID = (ROOT / ".run-coshh.env").read_text(encoding="utf-8").split("RUN_ID=")[1].split("\n")[0].strip()

ARTICLE = ROOT / "rewrites" / f"{SLUG}-{DATE}.md"
PLAN = ROOT / "research" / f"editorial-plan-{SLUG}-{DATE}.json"
SIDECAR = ROOT / "research" / f"validation-{SLUG}-{DATE}.md"
FINDINGS = ROOT / "research" / f"machine-review-findings-{SLUG}-{DATE}.json"
FULFILLMENT = ROOT / "research" / f"blog-plan-fulfillment-{SLUG}-{DATE}.json"
REVIEW_PLAN = ROOT / "research" / f"machine-review-plan-{SLUG}-{DATE}.json"
REVIEW_ARTICLE = ROOT / "research" / f"machine-review-article-{SLUG}-{DATE}.json"

EXCERPTS = {
    "coshh-at-a-glance-table": (
        "| [Regulation 9](https://www.legislation.gov.uk/uksi/2002/2677/regulation/9) | Keep control "
        "measures in efficient working order | Inspect extraction, respirators, and PPE before use | "
        "Examination and test results, kept at least 5 years |"
    ),
    "lev-and-record-retention": (
        "Local exhaust ventilation needs a thorough examination at least once every 14 months, with "
        "records kept at least 5 years"
    ),
    "sds-is-not-an-assessment": (
        "The data sheet tells you about the product. The assessment tells you about your task, your "
        "site, and your people."
    ),
    "field-job-checklist": (
        "| Controls | Allocate extraction, PPE, and spill kit | Inspect PPE and extraction before "
        "starting | Report damaged or missing equipment |"
    ),
    "review-triggers": (
        "The same regulation requires an immediate review if you suspect the assessment is no longer valid, the work changes significantly, or monitoring shows a need."
    ),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def review(phase: str, responses: list[dict]) -> dict:
    return build_machine_review(
        run_id=RUN_ID,
        workflow_stage="rewrite_review",
        phase=phase,
        command="machine_review.build_machine_review",
        repository_commit="working-tree",
        editorial_plan_path=PLAN,
        article_path=ARTICLE,
        proof_sidecar_path=SIDECAR,
        responses=responses,
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
            {"contribution_id": cid, "actual_excerpt": text} for cid, text in EXCERPTS.items()
        ],
    }
    problems = check_fulfillment(
        fulfillment, editorial_plan=plan, editorial_plan_sha256=plan_hash, article_content=article_text,
    )
    for problem in problems:
        print("FULFILLMENT FINDING:", problem)
    if problems:
        return 1
    atomic_write_json(FULFILLMENT, fulfillment)

    findings = json.loads(FINDINGS.read_text(encoding="utf-8"))
    write_machine_review(REVIEW_PLAN, review("plan", findings["plan"]))
    write_machine_review(REVIEW_ARTICLE, review("article", findings["article"]))
    print(f"fulfillment   : {FULFILLMENT.relative_to(ROOT).as_posix()} (0 findings)")
    print(f"plan review   : {REVIEW_PLAN.relative_to(ROOT).as_posix()}")
    print(f"article review: {REVIEW_ARTICLE.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
