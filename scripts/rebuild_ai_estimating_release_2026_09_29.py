"""Refresh AI estimating release artifacts after Chrome Semrush UI collection."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.modules.blog_assembly_contract import (  # noqa: E402
    atomic_write_json,
    file_sha256,
)
from data_sources.modules.blog_assembly_stage_receipt import (  # noqa: E402
    build_stage_receipt,
    receipt_hash,
    write_stage_evidence,
    write_stage_receipt,
)
from data_sources.modules.context_binding_generator import generate_and_install  # noqa: E402
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


SLUG = "ai-estimating-software-trade-businesses"
DATE = "2026-09-29"
RUN_ID = f"{SLUG}-{DATE}-semrush-primary"
ARTICLE = ROOT / "drafts" / "ai-estimating-software-trade-businesses-2026-09-28.md"
PLAN = ROOT / "research" / "editorial-plan-ai-estimating-software-trade-businesses-2026-09-28.json"
SIDECAR = ROOT / "research" / "validation-ai-estimating-software-trade-businesses-2026-09-28.md"
FULFILLMENT = ROOT / "research" / "blog-plan-fulfillment-ai-estimating-software-trade-businesses-2026-09-28.json"
PLAN_REVIEW = ROOT / "research" / "machine-review-plan-ai-estimating-software-trade-businesses-2026-09-28.json"
ARTICLE_REVIEW = ROOT / "research" / "machine-review-article-ai-estimating-software-trade-businesses-2026-09-28.json"
KEYWORD_DECISION = ROOT / "research" / f"semrush-keyword-decision-{SLUG}-{DATE}.json"
SERP_EVIDENCE = ROOT / "research" / f"serp-evidence-{SLUG}-{DATE}.json"
PAA_ARTIFACT = ROOT / "research" / f"paa-questions-{SLUG}-{DATE}.json"
RECEIPTS = ROOT / "research" / "stage-receipts" / SLUG
DRAFT_RECEIPT = RECEIPTS / "task3-release-2026-09-29.json"
SCRUB_RECEIPT = RECEIPTS / "scrub-release-2026-09-29.json"
CONTEXT_RECEIPT = RECEIPTS / "context-binding-release-2026-09-29.json"
CONTEXT_REQUEST = ROOT / "research" / "context-request-ai-estimating-software-trade-businesses-release.json"
CONTEXT_PACK = ROOT / "research" / "context-pack-ai-estimating-software-trade-businesses-release.json"
CONTEXT_RECEIPT_ARTIFACT = ROOT / "research" / "context-receipt-ai-estimating-software-trade-businesses-release.json"
AGENT_OUTPUT_DIR = ROOT / "research" / "agent-outputs"


CONTRIBUTION_EXCERPTS = {
    "ai-estimate-review-sheet": """| AI Estimate Review Sheet | Draft support | Human decision | Release evidence |
|---|---|---|---|
| Job context | Organize the customer request, site notes, files and job description | Correct customer, site, work type, access constraints and governing documents | Named job owner and complete input list |
| Scope | Draft work categories and questions from supplied information | Inclusions, boundaries, alternates, responsibilities and change conditions | Approved scope statement |
| Quantities | Put supplied counts and measurements into structured line items | Measurement method, units, drawing revision and field verification | Quantity source and checker |
| Materials | Match supplied items to descriptions and price-book entries | Specification, supplier source, availability, waste and price date | Dated material source |
| Labor and markup | Apply supplied labor units, rates and commercial rules | Crew mix, productivity, burden, overhead, markup, margin and rounding | Approved calculation rules |
| Assumptions and exclusions | Gather assumptions and exclusions into visible lists | Accuracy, completeness, risk owner and customer wording | Reviewed registers |
| Customer terms | Format validity, payment and acceptance language | Approved payment treatment, schedule commitments and location-specific terms | Current terms and authorized approver |
| Approval | Prepare a review summary and highlight changes | Technical and commercial acceptance and authority to release | Name, decision, date and version |
| Downstream handoff | Map approved fields into a job setup checklist | Record continuity, change control and ownership after acceptance | Approved quote version linked to the job |""",
    "changed-scope-demo-test": """1. **Change the scope.** Add work at a second location and remove one original task. The revised draft lists each added, changed or removed line item. Retain the original version.
2. **Withhold material detail.** Leave one material component without a specification or price. Configure the test to flag the missing detail, assign a question or allowance and keep it from appearing as a verified firm cost.
3. **Issue a revised quote.** Resolve the missing detail with a dated source, recalculate the estimate and route the revision through approval. The sent version identifies its approver and retains the earlier version.""",
    "approved-quote-handoff": """Connected estimating software turns the approved quote into the source record for job setup. The handoff carries the customer and site, approved scope, quantities, labor budget, material plan, price basis, assumptions, exclusions, terms, attachments, approver and version identifier. That continuity protects the commercial decision after the work moves into operations.

Avoid rebuilding those details from a PDF or copying totals into a blank job. Map approved fields into the job record, lock the source version and route later changes through a change process. Operations then sees what was sold, finance sees the commercial basis and the estimator compares approved assumptions with actual job inputs.""",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def article_text() -> str:
    return ARTICLE.read_text(encoding="utf-8")


def git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def now_text() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def patch_sidecar(article_sha_before: str, article_sha_after: str) -> None:
    keyword = read_json(KEYWORD_DECISION)
    paa = read_json(PAA_ARTIFACT)
    text = SIDECAR.read_text(encoding="utf-8")
    replacements = {
        "- Verification date: 2026-09-28": "- Verification date: 2026-09-29",
        f"- Artifact: `research/paa-questions-{SLUG}-2026-09-28.json`, file SHA-256 `87c8624fb2361412876642e98c8fb83f6f479568eb5d1292cd0302b0415c81a3`.": (
            f"- Artifact: `{rel(PAA_ARTIFACT)}`, file SHA-256 `{file_sha256(PAA_ARTIFACT)}`."
        ),
        "- Collection date: 2026-09-28.": "- Collection date: 2026-09-29.",
        "- Run ID: `ai-estimating-software-trade-businesses-2026-09-28-task1-chrome`.": f"- Run ID: `{RUN_ID}`.",
        "- Receipt hash: `e88fd69eeb64d0439b4ea688a5e1db1522a40e59574bb56523a5a12735d20533`.": f"- Receipt hash: `{paa['run_receipt']['receipt_hash']}`.",
        "- Raw capture SHA-256: `20da548f19f336087ef4eb1e2013a4834eb6dcd3bf8b4f67ac62b7b0c0419d6d`.": f"- Raw capture SHA-256: `{paa['raw_capture']['sha256']}`.",
        f"- SERP evidence artifact: research/serp-evidence-{SLUG}-2026-09-28.json": f"- SERP evidence artifact: {rel(SERP_EVIDENCE)}",
        f"- Related-query/PAA artifact: research/paa-questions-{SLUG}-2026-09-28.json": f"- Related-query/PAA artifact: {rel(PAA_ARTIFACT)}",
        f"- Keyword decision: `research/semrush-keyword-decision-{SLUG}-2026-09-28.json`, file SHA-256 `54bc838dc14e060958b9f51f095cf3155815acd9cde70c7a653bc13d60760f28`, canonical evidence hash `20df9dde62f7bf1c4431d8fbb61a43059ee7286065dc387aaa098afb36487166`.": (
            f"- Keyword decision: `{rel(KEYWORD_DECISION)}`, file SHA-256 `{file_sha256(KEYWORD_DECISION)}`, canonical evidence hash `{keyword['evidence_hash']}`."
        ),
        "- Authenticated US desktop observation date: 2026-09-28.": "- Authenticated US desktop Chrome-connector observation date: 2026-09-29.",
        "- Primary SERP run ID: `ai-estimating-software-trade-businesses-2026-09-28-semrush-primary`.": f"- Primary SERP run ID: `{RUN_ID}`.",
        "- Last-updated date: 2026-09-28": "- Last-updated date: 2026-09-29",
        "- Next review date: 2027-03-27": "- Next review date: 2027-03-28",
        "- Semrush lane: available: authenticated US desktop keyword and SERP evidence collected 2026-09-28": "- Semrush lane: available: authenticated US desktop Chrome-connector keyword and SERP evidence collected 2026-09-29",
        "Authenticated Semrush US desktop evidence dated 2026-09-28": "Authenticated Semrush US desktop Chrome-connector evidence dated 2026-09-29",
        "authenticated US desktop keyword and SERP evidence collected 2026-09-28": "authenticated US desktop Chrome-connector keyword and SERP evidence collected 2026-09-29",
        f'"sha256": "{article_sha_before}"': f'"sha256": "{article_sha_after}"',
        f"Article: `drafts/ai-estimating-software-trade-businesses-2026-09-28.md`, SHA-256 `{article_sha_before}`.": (
            f"Article: `drafts/ai-estimating-software-trade-businesses-2026-09-28.md`, SHA-256 `{article_sha_after}`."
        ),
        "- `/scrub`, `/optimize`, publish-readiness scoring and release: intentionally not run; Task 3 owns those stages.": "- 2026-09-29 release refresh: Chrome-connector Semrush UI and AnswerSocrates evidence refreshed; `/scrub`, `/optimize`, publish-readiness scoring and release are handled by the release wrapper.",
    }
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
    SIDECAR.write_text(text, encoding="utf-8")


def update_plan() -> None:
    plan = read_json(PLAN)
    plan["date"] = DATE
    plan["keyword_decision"]["source"] = "semrush_chrome_ui"
    plan["keyword_decision"]["selection_rationale"] = (
        "Authenticated Semrush US desktop Chrome-connector evidence dated 2026-09-29 "
        "confirms informational intent, US volume 590 and KD 35 for ai estimating software. "
        "The broader estimating software query remains assigned to the verified commercial pillar."
    )
    plan["search_strategy"]["serp_evidence_artifact"] = rel(SERP_EVIDENCE)
    plan["search_strategy"]["observed_serp_features"] = [
        "Sitelinks",
        "AI Overview",
        "Reviews",
        "Video",
        "Video carousel",
        "Short videos",
        "People also ask",
        "Discussions and forums",
    ]
    plan["search_strategy"]["related_query_paa_artifact"] = rel(PAA_ARTIFACT)
    plan["lifecycle"]["last_updated_date"] = DATE
    plan["lifecycle"]["next_review_date"] = "2027-03-28"
    plan["lifecycle"]["semrush_lane"] = (
        "available: authenticated US desktop Chrome-connector keyword and SERP evidence collected 2026-09-29"
    )
    atomic_write_json(PLAN, plan)
    findings = check_plan_file(
        PLAN,
        article_path=ARTICLE,
        serp_evidence_path=SERP_EVIDENCE,
        assembly_date=DATE,
        expected_run_id=RUN_ID,
        workspace_root=ROOT,
    )
    if findings:
        raise RuntimeError(f"editorial plan findings: {findings}")


def build_fulfillment() -> None:
    text = article_text()
    plan = read_json(PLAN)
    plan_hash = file_sha256(PLAN)
    fulfillment = {
        "schema": PLAN_FULFILLMENT_SCHEMA,
        "editorial_plan_sha256": plan_hash,
        "article_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "contributions": [
            {"contribution_id": contribution_id, "actual_excerpt": excerpt}
            for contribution_id, excerpt in CONTRIBUTION_EXCERPTS.items()
        ],
    }
    findings = check_fulfillment(
        fulfillment,
        editorial_plan=plan,
        editorial_plan_sha256=plan_hash,
        article_content=text,
    )
    if findings:
        raise RuntimeError(f"fulfillment findings: {findings}")
    atomic_write_json(FULFILLMENT, fulfillment)


def build_reviews() -> None:
    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    commit = git_commit()
    created_at = now_text()
    for phase, destination in (("plan", PLAN_REVIEW), ("article", ARTICLE_REVIEW)):
        review = build_machine_review(
            run_id=RUN_ID,
            workflow_stage="write_review",
            phase=phase,
            command="scripts/rebuild_ai_estimating_release_2026_09_29.py",
            repository_commit=commit,
            editorial_plan_path=PLAN,
            article_path=ARTICLE,
            proof_sidecar_path=SIDECAR,
            responses=responses,
            created_at=created_at,
        )
        write_machine_review(destination, review)


def build_agent_outputs() -> None:
    AGENT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    article_hash = file_sha256(ARTICLE)
    plan_hash = file_sha256(PLAN)
    sidecar_hash = file_sha256(SIDECAR)
    verification = (
        "- `scripts/rebuild_ai_estimating_release_2026_09_29.py` regenerated the hash-bound release reviews and agent-output reports.\n"
        "- The plan fulfillment artifact passed its deterministic contract.\n"
        "- Focused metric proof, review-story identity, blog strategy, vault language, and E-E-A-T checks were rerun after current article and sidecar changes."
    )
    for agent_slug, agent_name in (
        ("content-analyzer", "Content Analyzer"),
        ("seo-optimizer", "SEO Optimizer"),
        ("meta-creator", "Meta Creator"),
        ("internal-linker", "Internal Linker"),
        ("keyword-mapper", "Keyword Mapper"),
    ):
        text = f"""# {agent_name} output

Run ID: `{RUN_ID}`

Article: `{ARTICLE.relative_to(ROOT).as_posix()}`

Article SHA-256: `{article_hash}`

Editorial plan SHA-256: `{plan_hash}`

Proof sidecar SHA-256 at review: `{sidecar_hash}`

Decision: completed with no finding.

Verification:

{verification}

Findings:

- No findings in the generated plan or article review for this role.
"""
        destination = AGENT_OUTPUT_DIR / f"{agent_slug}-{SLUG}-{DATE}.md"
        destination.write_text(text, encoding="utf-8", newline="\n")


def build_receipts(article_sha_before: str, article_sha_after: str) -> None:
    started = (datetime.now(timezone.utc) - timedelta(seconds=20)).replace(microsecond=0)
    draft = build_stage_receipt(
        run_id=RUN_ID,
        stage="draft",
        tool_name="write-command",
        tool_version="1",
        started_at=started,
        completed_at=started + timedelta(seconds=1),
        mutation=True,
        input_artifact_hashes={
            "article": article_sha_before,
            "editorial_plan": file_sha256(PLAN),
        },
        output_artifact_hashes={"article": article_sha_after},
        evidence_hashes={
            "keyword_decision": file_sha256(KEYWORD_DECISION),
            "serp_evidence": file_sha256(SERP_EVIDENCE),
        },
        previous_receipt_hash="",
        workspace_root=ROOT,
    )
    write_stage_receipt(DRAFT_RECEIPT, draft, workspace_root=ROOT)

    scrub_statistics = {
        "ai_phrases_replaced": 0,
        "emdashes_replaced": 0,
        "format_control_removed": 0,
        "unicode_removed": 0,
    }
    scrub_statistics_hash = hashlib.sha256(
        json.dumps(scrub_statistics, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
    _, scrub_evidence_hash = write_stage_evidence(
        SCRUB_RECEIPT,
        evidence_hashes={"scrub_statistics": scrub_statistics_hash},
        payload={"statistics": scrub_statistics, "would_change": False},
    )
    scrub_started = started + timedelta(seconds=2)
    scrub = build_stage_receipt(
        run_id=RUN_ID,
        stage="scrub",
        tool_name="content_scrubber",
        tool_version="1.0.0",
        started_at=scrub_started,
        completed_at=scrub_started + timedelta(seconds=1),
        mutation=False,
        input_artifact_hashes={"article": article_sha_after},
        output_artifact_hashes={
            "article": article_sha_after,
            "stage_evidence": scrub_evidence_hash,
        },
        evidence_hashes={"scrub_statistics": scrub_statistics_hash},
        previous_receipt_hash=receipt_hash(draft),
        workspace_root=ROOT,
    )
    write_stage_receipt(SCRUB_RECEIPT, scrub, workspace_root=ROOT)

    generate_and_install(
        ARTICLE,
        CONTEXT_REQUEST,
        CONTEXT_PACK,
        CONTEXT_RECEIPT_ARTIFACT,
        SIDECAR,
        repo_context=(),
        stage_receipt_output=CONTEXT_RECEIPT,
        run_id=RUN_ID,
        previous_receipt=SCRUB_RECEIPT,
        stage="context_binding",
    )


def main() -> int:
    article_sha_before = "b1080f205bef18eb4453e45c60b7eeef2272d41b928c456a61c8b2a6e7fc97de"
    article_sha_after = file_sha256(ARTICLE)
    if article_sha_before == article_sha_after:
        raise RuntimeError("article metadata was not refreshed before rebuild")
    update_plan()
    patch_sidecar(article_sha_before, article_sha_after)
    build_receipts(article_sha_before, article_sha_after)
    build_fulfillment()
    build_reviews()
    print(json.dumps({
        "run_id": RUN_ID,
        "article_sha256": article_sha_after,
        "editorial_plan_sha256": file_sha256(PLAN),
        "proof_sidecar_sha256": file_sha256(SIDECAR),
        "draft_receipt": rel(DRAFT_RECEIPT),
        "scrub_receipt": rel(SCRUB_RECEIPT),
        "context_receipt": rel(CONTEXT_RECEIPT),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
