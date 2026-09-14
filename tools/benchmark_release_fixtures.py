"""Deterministic offline fixtures for the release benchmark harness."""

from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

from data_sources.modules import artifact_release, blog_assembly_contract, blog_release_impl
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.readiness import pipeline_tail as readiness_pipeline_tail
from data_sources.modules.readiness import runner as readiness_runner
from data_sources.modules.readiness.finalization_dependencies import (
    FinalizationDependencies,
)
from data_sources.modules.release_authorization import load_publish_authorization
from data_sources.modules.semrush_keyword_decision_guard import build_keyword_decision
from data_sources.modules.machine_review import (
    AGENT_ROSTER,
    build_machine_review,
    write_machine_review,
)


BLOG_ARTICLE = """---
artifact_type: blog
brand: BigChange
title: Scheduling guide
meta_title: Field Service Scheduling Guide for Dispatch | BigChange
primary_keyword: field service scheduling guide
objective: Help service leaders improve scheduling decisions
audience: Field service leaders
region: US
last_updated: 2026-08-11
schema_notes:
  - BlogPosting
  - BreadcrumbList
  - ImageObject for the featured image or logo
  - Organization as publisher reference only, not a separate full schema block
---
# Field service scheduling guide

This guide helps readers use a repeatable dispatch routine. Apply the field service scheduling guide to check scope, capacity, handoffs, schedule changes, and follow-up before the day gets messy. Make decisions visible, give technicians cleaner notes, and explain exceptions in plain language. Use it daily with one simple review.

Make the review clear. Show the owner in the open. You'll move faster with short notes. It isn't a longer meeting.

| Review point | Dispatcher action | Ready signal |
|---|---|---|
| Scope | Read the work request | The requested outcome is clear |
| Ownership | Name a coordinator | The coordinator owns the next decision |
| Timing | Compare the available windows | Select a workable window |
| Handoff | Record the essential notes | The assigned technician has context |

## Start with a complete request

Add enough request context for the dispatcher to make a first decision. Include the place, contact, requested outcome, access notes, and timing constraint. When something is missing, don't guess. Ask one clear question before the job enters the schedule, then keep the answer beside the request for the next handoff too.

- Read the request from beginning to end. Check the location, contact, requested outcome, access notes, and scheduling constraint. Return an unclear request for clarification. Save the answer beside the original request.
- Separate urgent work from work that simply arrived first. Write the reason for urgency in plain language. Give the coordinator enough context to review the decision later. Don't hide the reason in a private message or a separate conversation.
- Name one owner for the next decision. Keep ownership visible beside the request. When ownership changes, save the handoff and the next action together. Use a short status that tells the reader exactly what remains incomplete.

## Review capacity with your field service scheduling guide

Review fixed commitments before new requests. Check urgent work, planned visits, and follow-up tasks in the same pass, then record every exception with the reason it moved ahead. Don't assign work when the request lacks an owner, a time, or a next action for the technician. Repeat the same order tomorrow and the next day.

Start with fixed commitments. Then check urgent requests, planned work, and follow-up work. Track each exception and write down why it moved ahead. Don't assign work without an owner, a time, or a clear next action.

Use a small decision checklist during the review:

- Verify the requested outcome.
- Check the location and access notes.
- Select the available work window.
- Name the assigned owner.
- Give the technician the essential context.

Use the checklist to expose missing information before assignment. It's a prompt, not a substitute for judgment. After the review, record the decision and move the request into the next clear state.

## Build a useful technician handoff

Create a technician handoff with the destination, contact, expected outcome, and open question before travel starts. Remove internal discussion that doesn't help the technician. Lead with urgent details, and keep history nearby for arrival, callback prevention, and the next clean schedule decision. Don't bury the answer where nobody looks later.

- Put the customer request, location, contact, access notes, and expected outcome in one readable handoff. Remove internal discussion that doesn't help the technician complete the work. Keep any unresolved question visible at the top.
- Choose direct words for notes. Name the object, location, or action instead of using vague references. Put the first screen focus on the information needed before travel and arrival. Place supporting history after the immediate instructions.

Take the technician's perspective during a handoff review. Point to the destination, contact, requested work, and next action. When an answer isn't available, revise the note before assignment.

Reuse consistent field names across common requests. Keep optional details optional, but keep essential details in predictable locations. Review the handoff when a technician returns a request for clarification and improve the template where the same gap appears again.

## Keep changes controlled

Store the active request, owner, time, and next action in one place when priorities shift. Update the handoff before the technician acts on stale information. Keep earlier decisions available for review. Don't leave old instructions in the current work notes, because the exception needs a clean record for everyone later.

Place each schedule change beside the affected request. Add the new owner, the new time, and the next action. Retain the earlier decision for review. Confirm the change before dispatch begins that day.

When priorities change, review the requests affected by the change. Contact the relevant owner, update the handoff, and confirm the revised next step. Don't rely on memory or an unrecorded chat message.

Reserve a short review window for exceptions. Use it to resolve missing access details, ownership conflicts, and unclear outcomes. Don't leave without a named owner and one visible next action.

### Keep reference pages nearby

- [NIST](https://www.nist.gov/)
- [W3C](https://www.w3.org/)
- [BigChange work order software](https://www.bigchange.com/work-order-software/)

## Close the scheduling loop

Match completed work to the requested outcome before closing the request. Capture the result, owner, and follow-up action in one visible place. Move unfinished work into a clear follow-up state. Use the final review to give the next dispatcher a clean starting point without a hunt the next morning for review.

Review completed work against the requested outcome. Record the result and any follow-up task. Move unfinished work into a clear follow-up state. Close the request only when its outcome and next action are easy to find.

Finish with a simple operating review. The review is easier to inspect when the table, checklist, exceptions, and owner handoffs all line up. Explore [field service management software](https://www.bigchange.com/solutions/field-service-management-software/) before comparing that workflow with [BigChange field service management software](https://www.bigchange.com/field-service-management-software/).
"""

BLOG_SIDECAR = """Author policy: no_author
No named author available.

## Metric Proof Pack
- Metric requirement: not applicable
- Reason: This article presents a non-quantitative operating checklist and makes no metric claim.
- Search log: Reviewed the article scope and found no metric necessary for the decision task.

## Early Artifact Plan
- Early artifact requirement: required
- Artifact: Filled scheduling review table in the opening section.
"""

LANDING_PARAGRAPHS = (
    "Organize incoming work in one clear queue so coordinators review priorities, assign ownership, and keep the next action visible to the team.",
    "Give technicians a concise view of the work requested, the location, the contact details, and the notes they need before travel begins.",
    "Keep scheduling decisions easy to review by grouping urgent work, planned work, and follow-up tasks in a consistent operating rhythm.",
    "Use a simple handoff between office and field teams so updates remain visible without relying on a separate explanation or hidden process.",
    "Review each request before assignment, confirm that the scope is understandable, and record the next action in language the whole team follows.",
    "Build a repeatable dispatch routine around clear ownership, practical notes, and a shared view of what is ready to move forward.",
    "Keep the request, decision, and assigned owner together from intake through completion to limit avoidable back-and-forth.",
    "Show managers the work that needs attention and give each team member a focused, readable view of current work.",
    "Keep the process flexible enough for changing priorities while preserving the context behind each scheduling and assignment decision.",
    "Make daily coordination easier with a straightforward review step, an explicit owner, and a visible outcome for every accepted request.",
    "Support a calm operating cadence by separating ready work from incomplete requests and returning unclear items for useful clarification.",
    "Close the loop by recording the outcome, checking the response to the request, and making completed work easy to review later.",
)


def run_blog_release_fixture(runtime_root: Path) -> dict[str, Any]:
    from tests.test_blog_assembly_bom import (
        _fixture,
        _prepare_optimized_workflow,
        _refresh_normal_stage_receipts,
        _run_id,
    )

    workspace = _fresh_workspace(runtime_root, "blog-release")
    paths = _fixture(workspace)
    Path(paths["article"]).write_text(BLOG_ARTICLE, encoding="utf-8")
    Path(paths["sidecar"]).write_text(BLOG_SIDECAR, encoding="utf-8")
    _bind_blog_plan(Path(paths["editorial_plan"]))
    _bind_keyword_decision_ui_surface(Path(paths["keyword_decision"]))
    started = time.perf_counter_ns()
    with deterministic_release_environment(
        preflight_started="2026-08-11T14:14:00Z",
        preflight_completed="2026-08-11T14:15:00Z",
        final_started="2026-08-11T14:16:00Z",
        final_completed="2026-08-11T14:17:00Z",
    ):
        _refresh_normal_stage_receipts(paths)
        prior_readiness, optimizer_outputs = _prepare_optimized_workflow(workspace, paths)
        run_id = _run_id(Path(paths["article"]))
        plan_review, article_review = _machine_reviews_for_run(
            workspace,
            editorial_plan=Path(paths["editorial_plan"]),
            article=Path(paths["article"]),
            sidecar=Path(paths["sidecar"]),
            run_id=run_id,
        )
        result = artifact_release.run_artifact_release(
            article=paths["article"],
            run_id=run_id,
            proof_sidecar=paths["sidecar"],
            editorial_plan=paths["editorial_plan"],
            plan_review=plan_review,
            article_review=article_review,
            keyword_decision=paths["keyword_decision"],
            scrub_receipt=paths["stage_receipts"][-2],
            serp_evidence=paths["serp"],
            paa_artifact=paths["paa"],
            stage_receipts=paths["stage_receipts"],
            workflow_mode="new",
            assembly_date="2026-08-11",
            output_dir=workspace / "research" / "releases" / "blog-release",
            workspace_root=workspace,
            optimizer_outputs=optimizer_outputs,
            prior_preflight_readiness=prior_readiness,
            agent_output_paths=paths["agent_outputs"],
        )
    return _release_payload(
        runtime_root=runtime_root,
        workspace=workspace,
        result=result,
        elapsed_ns=time.perf_counter_ns() - started,
    )


def run_landing_release_fixture(runtime_root: Path) -> dict[str, Any]:
    workspace = _fresh_workspace(runtime_root, "landing-release")
    article = _write(
        workspace / "landing-pages" / "dispatch.md",
        "---\nartifact_type: landing_page\nbrand: AroFlo\npage_type: ppc\n"
        "conversion_goal: demo\ntitle: Clear Dispatch Workflows\n---\n"
        "# Reduce scheduling friction with a clear dispatch workflow\n\n"
        "Plan work around a visible next step. Choose a service that lets you **cancel any time.**\n\n"
        "[Book a demo today](#demo)\n\n"
        "## Keep work clear from intake to completion\n\n"
        + "\n\n".join(LANDING_PARAGRAPHS[:6])
        + "\n\n- **Review** each request.\n- **Assign** one owner.\n- **Confirm** the next action.\n\n"
        "## Give every team member a useful handoff\n\n"
        + "\n\n".join(LANDING_PARAGRAPHS[6:])
        + "\n\n[Schedule a demo today](#demo)\n\n"
        "See the workflow in context and decide whether it fits your operating model.\n\n"
        "[Book a demo now](#demo)\n",
    )
    sidecar = _write(
        workspace / "research" / "validation-dispatch.md",
        "# Validation\n\nNo proof-sensitive public claims are present.\n\n"
        "## Early Artifact Plan\n"
        "- Early artifact requirement: not applicable\n"
        "- Reason: This concise conversion page has no data deliverable that fits its purpose.\n",
    )
    started = time.perf_counter_ns()
    with deterministic_release_environment(
        preflight_started="2026-08-11T14:00:00Z",
        preflight_completed="2026-08-11T14:01:00Z",
        final_started="2026-08-11T14:02:00Z",
        final_completed="2026-08-11T14:03:00Z",
    ):
        result = artifact_release.run_artifact_release(
            article=article,
            run_id="landing-benchmark",
            proof_sidecar=sidecar,
            output_dir=workspace / "research" / "releases" / "landing-release",
            workspace_root=workspace,
        )
    return _release_payload(
        runtime_root=runtime_root,
        workspace=workspace,
        result=result,
        elapsed_ns=time.perf_counter_ns() - started,
    )


@contextmanager
def deterministic_release_environment(
    *,
    preflight_started: str,
    preflight_completed: str,
    final_started: str,
    final_completed: str,
) -> Iterator[None]:
    original = {
        "current_utc_date": blog_assembly_contract.current_utc_date,
        "runner_now": readiness_runner._utc_now,
        "pipeline_now": readiness_pipeline_tail._utc_now,
        "transport_request_many": PublicHttpTransport.request_many,
        "blog_final": blog_release_impl.publish_readiness.build_final_readiness_attestation,
        "landing_final": artifact_release.publish_readiness.build_final_readiness_attestation,
    }

    def final_attestation(preflight: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        timestamps = iter((final_started, final_completed))
        kwargs["dependencies"] = FinalizationDependencies(now=timestamps.__next__)
        return original["blog_final"](preflight, **kwargs)

    blog_assembly_contract.current_utc_date = lambda: __import__(
        "datetime"
    ).date(2026, 8, 11)
    readiness_runner._utc_now = lambda: preflight_started
    readiness_pipeline_tail._utc_now = lambda: preflight_completed
    PublicHttpTransport.request_many = (
        lambda _self, _method, urls, **_kwargs: [
            SimpleNamespace(status_code=200, url=url, headers={})
            for url in urls
        ]
    )
    blog_release_impl.publish_readiness.build_final_readiness_attestation = (
        final_attestation
    )
    artifact_release.publish_readiness.build_final_readiness_attestation = (
        final_attestation
    )
    try:
        yield
    finally:
        blog_assembly_contract.current_utc_date = original["current_utc_date"]
        readiness_runner._utc_now = original["runner_now"]
        readiness_pipeline_tail._utc_now = original["pipeline_now"]
        PublicHttpTransport.request_many = original["transport_request_many"]
        blog_release_impl.publish_readiness.build_final_readiness_attestation = (
            original["blog_final"]
        )
        artifact_release.publish_readiness.build_final_readiness_attestation = (
            original["landing_final"]
        )


def _bind_blog_plan(path: Path) -> None:
    plan = json.loads(path.read_text(encoding="utf-8"))
    plan["original_contributions"][0].update(
        {
            "visible_evidence": (
                "This guide helps readers use a repeatable dispatch routine."
            ),
            "final_section": "Field service scheduling guide",
        }
    )
    plan["sections"][0]["heading"] = "Field service scheduling guide"
    plan["meta"].update(
        {
            "meta_title": "Field Service Scheduling Guide for Dispatch | BigChange",
            "meta_description": (
                "A practical field service scheduling guide for reviewing requests, "
                "capacity, dispatch choices, technician handoffs, schedule changes, "
                "and completion follow-up."
            ),
        }
    )
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")


def _bind_keyword_decision_ui_surface(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    reports = []
    for row in payload["connector_reports"]:
        parameters = dict(row.get("parameters") or {})
        parameters["execution_surface"] = "semrush_ui_chrome_main_browser"
        reports.append({**row, "parameters": parameters})
    rebuilt = build_keyword_decision(
        brand=payload["brand"],
        market=payload["market"],
        database=payload["database"],
        collection_date=payload["collection_date"],
        source_boundary=payload["source_boundary"],
        seed_terms=payload["seed_terms"],
        connector_reports=reports,
        candidate_metrics=payload["candidate_metrics"],
        serp_finalists=payload["serp_finalists"],
        question_candidates=payload["question_candidates"],
        related_candidates=payload["related_candidates"],
        selected_primary_keyword=payload["selected_primary_keyword"],
        selected_secondary_keywords=payload["selected_secondary_keywords"],
        rejected_keywords=payload["rejected_keywords"],
        selection_rationale=payload["selection_rationale"],
    )
    path.write_text(json.dumps(rebuilt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _machine_reviews_for_run(
    workspace_root: Path,
    *,
    editorial_plan: Path,
    article: Path,
    sidecar: Path,
    run_id: str,
) -> tuple[Path, Path]:
    responses = [
        {"agent": agent, "status": "completed", "findings": []}
        for agent in AGENT_ROSTER
    ]
    reviews: list[Path] = []
    for phase in ("plan", "article"):
        review_path = workspace_root / "research" / f"machine-review-{phase}.json"
        write_machine_review(
            review_path,
            build_machine_review(
                run_id=run_id,
                workflow_stage="write",
                phase=phase,
                command="/write",
                repository_commit="benchmark-fixture",
                editorial_plan_path=editorial_plan,
                article_path=article,
                proof_sidecar_path=sidecar,
                responses=responses,
                created_at="2026-08-11T14:06:00Z",
            ),
        )
        reviews.append(review_path)
    return reviews[0], reviews[1]


def _release_payload(
    *,
    runtime_root: Path,
    workspace: Path,
    result: Any,
    elapsed_ns: int,
) -> dict[str, Any]:
    if result.exit_code != 0 or result.phase != "final_readiness":
        raise RuntimeError(
            "benchmark release fixture did not reach final readiness: "
            f"exit_code={result.exit_code} phase={result.phase} message={result.message}"
        )
    telemetry_path = result.output_dir / "release-telemetry.json"
    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    authorization = load_publish_authorization(
        final_readiness_path=result.output_dir / "final-readiness.json",
        final_receipt_path=result.output_dir / "final-readiness-stage-receipt.json",
        release_manifest_path=result.output_dir / "release-manifest.json",
        workspace_root=workspace,
    )
    final_authorization = authorization.with_final_input_seal(
        lambda article_bytes, _inventory: {
            "status": "authorized",
            "article_sha256": hashlib.sha256(article_bytes).hexdigest(),
        }
    )
    return {
        "fixture_elapsed_ms": round(elapsed_ns / 1_000_000, 3),
        "counters": telemetry.get("counters", {}),
        "gauges": telemetry.get("gauges", {}),
        "scoring_imports": [],
        "exit_phase": result.phase,
        "exit_code": result.exit_code,
        "final_authorization_result": final_authorization,
        "output_dir": str(result.output_dir.resolve().relative_to(runtime_root.resolve())),
    }


def _fresh_workspace(runtime_root: Path, name: str) -> Path:
    for index in range(100):
        suffix = "" if index == 0 else f"-{index}"
        candidate = runtime_root / f"{name}{suffix}"
        try:
            candidate.mkdir(parents=True)
            return candidate
        except FileExistsError:
            continue
    raise RuntimeError(f"could not allocate benchmark workspace for {name}")


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
