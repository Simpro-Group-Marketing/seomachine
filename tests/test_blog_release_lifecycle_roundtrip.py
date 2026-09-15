from __future__ import annotations

import json
import hashlib
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from data_sources.modules import blog_assembly_contract, publish_readiness
from data_sources.modules.blog_assembly_bom import write_blog_assembly_bom
from data_sources.modules.public_http import PublicHttpTransport
from data_sources.modules.readiness import pipeline_tail as readiness_pipeline_tail
from data_sources.modules.readiness import runner as readiness_runner
from data_sources.modules.readiness.finalization_dependencies import (
    FinalizationDependencies,
)
from data_sources.modules.release_authorization import (
    load_publish_authorization,
    prepare_final_release_result,
)
from tests.test_blog_assembly_bom import (
    _build,
    _finalize_fixture_bom,
    _fixture,
    _refresh_normal_stage_receipts,
    _run_id,
)


_ARTICLE = """---
artifact_type: blog
brand: BigChange
title: Scheduling guide
meta_title: Field Service Scheduling Guide for Dispatch | BigChange
meta_description: A practical field service scheduling guide for reviewing requests, capacity, dispatch choices, technician handoffs, schedule changes, and completion follow-up.
url_slug: scheduling-guide
primary_keyword: field service scheduling guide
secondary_keywords:
  - capacity planning
  - dispatch constraints
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

_SIDECAR = """Author policy: no_author
No named author available.

## Metric Proof Pack
- Metric requirement: not applicable
- Reason: This article presents a non-quantitative operating checklist and makes no metric claim.
- Search log: Reviewed the article scope and found no metric necessary for the decision task.

## Early Artifact Plan
- Early artifact requirement: required
- Artifact: Filled scheduling review table in the opening section.
"""


def test_unmocked_blog_release_lifecycle_round_trip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    monkeypatch.setattr(
        PublicHttpTransport,
        "request_many",
        lambda _self, _method, urls, **_kwargs: [
            SimpleNamespace(status_code=200, url=url, headers={}) for url in urls
        ],
    )
    monkeypatch.setattr(
        readiness_runner,
        "_utc_now",
        lambda: "2026-08-11T14:06:00Z",
    )
    monkeypatch.setattr(
        readiness_pipeline_tail,
        "_utc_now",
        lambda: "2026-08-11T14:07:00Z",
    )
    monkeypatch.setattr(
        readiness_pipeline_tail,
        "_score_content",
        lambda *args, **kwargs: {
            "passed": True,
            "content_quality_score": 95,
            "threshold": 85,
            "priority_fixes": [],
            "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
            "quality_gates": {
                "content_quality": {"score": 95, "threshold": 85, "passed": True},
                "seo_quality": {
                    "score": 95,
                    "threshold": 90,
                    "passed": True,
                    "critical_issues": [],
                },
                "aeo_geo": {"score": 95, "threshold": 90, "passed": True},
            },
        },
    )
    paths = _fixture(tmp_path)
    Path(paths["article"]).write_text(_ARTICLE, encoding="utf-8")
    Path(paths["sidecar"]).write_text(_SIDECAR, encoding="utf-8")
    plan = json.loads(Path(paths["editorial_plan"]).read_text(encoding="utf-8"))
    plan["schema"] = "simpro-blog-editorial-plan/v2"
    plan["original_contributions"] = [
        {
            "contribution_id": "repeatable-dispatch-routine",
            "planned_contribution": "A repeatable dispatch review routine.",
            "purpose": "Help readers make scheduling decisions consistently.",
            "evidence_source": "Bound article research and workflow evidence.",
            "target_section": "Field service scheduling guide",
        }
    ]
    plan["sections"][0].update(
        {
            "heading": "Field service scheduling guide",
            "reader_question": "How can I make dispatch decisions consistently?",
            "section_payoff": "A repeatable routine for reviewing dispatch constraints.",
            "bridge_from_previous": None,
            "bridge_to_next": None,
        }
    )
    plan["meta"].update(
        {
            "meta_title": "Field Service Scheduling Guide for Dispatch | BigChange",
            "meta_description": (
                "A practical field service scheduling guide for reviewing requests, "
                "capacity, dispatch choices, technician handoffs, schedule changes, "
                "and completion follow-up."
            ),
            "title_options": ["Scheduling guide", "Field service scheduling guide"],
        }
    )
    plan["search_strategy"] = {
        "primary_query": "field service scheduling guide",
        "searcher_task": "Choose a repeatable scheduling workflow.",
        "intent_class": "informational",
        "funnel_stage": "tofu",
        "serp_evidence_artifact": "research/serp-evidence.json",
        "dominant_content_type": "General Article",
        "selected_content_type": "General Article",
        "observed_serp_features": ["featured snippet"],
        "related_query_paa_artifact": "research/paa.json",
        "format_decision": "match_dominant",
        "exception_reason": "none",
        "status": "ready",
    }
    plan["commercial_strategy"] = {
        "article_title": "Scheduling guide",
        "article_primary_keyword": "field service scheduling guide",
        "article_intent": "informational",
        "destination_id": "bigchange-field-service-management-software",
        "commercial_pillar_url": "https://www.bigchange.com/field-service-management-software/",
        "planned_anchor_text": "BigChange field service management software",
        "planned_h2_section": "Field service scheduling guide",
        "existing_overlapping_urls_checked": ["https://www.bigchange.com/blog/"],
        "pillar_versus_blog_intent_difference": "The article informs while the destination supports product evaluation.",
        "cannibalization_decision": "different_intent",
        "incoming_link_candidates": ["https://www.bigchange.com/blog/"],
        "status": "aligned",
    }
    plan["lifecycle"] = {
        "last_updated_date": "2026-08-11",
        "volatility": "standard",
        "next_review_date": "2027-02-01",
        "review_command": "/performance-review published/scheduling-guide.md",
        "gsc_lane": "unavailable: new article has no performance data",
        "ga4_lane": "unavailable: new article has no performance data",
        "semrush_lane": "available: bound keyword decision",
        "ai_citation_lane": "unavailable: new article has no citation data",
        "decision": "retain",
        "status": "scheduled",
    }
    del plan["serp_strategy"]
    del plan["query_ownership"]
    Path(paths["editorial_plan"]).write_text(
        json.dumps(plan, indent=2) + "\n",
        encoding="utf-8",
    )
    fulfillment = tmp_path / "research" / "plan-fulfillment.json"
    fulfillment.write_text(
        json.dumps(
            {
                "schema": "simpro-blog-plan-fulfillment/v1",
                "editorial_plan_sha256": hashlib.sha256(
                    Path(paths["editorial_plan"]).read_bytes()
                ).hexdigest(),
                "article_sha256": hashlib.sha256(
                    Path(paths["article"]).read_bytes()
                ).hexdigest(),
                "contributions": [
                    {
                        "contribution_id": "repeatable-dispatch-routine",
                        "actual_excerpt": "This guide helps readers use a repeatable dispatch routine.",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    commercial_index = tmp_path / "context" / "commercial-pillar-index.json"
    commercial_index.parent.mkdir(exist_ok=True)
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "context" / "commercial-pillar-index.json",
        commercial_index,
    )
    paths["plan_fulfillment"] = fulfillment
    paths["commercial_pillar_index"] = commercial_index
    _refresh_normal_stage_receipts(paths)

    provisional = _build(
        tmp_path,
        paths,
        plan_fulfillment_path=fulfillment,
        commercial_pillar_index_path=commercial_index,
    )
    bom_path = tmp_path / "research" / "real-provisional-bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = publish_readiness.run_publish_readiness(
        paths["article"],
        proof_sidecar=paths["sidecar"],
        assembly_bom=bom_path,
        phase="preflight",
        workspace_root=tmp_path,
        run_id=_run_id(paths["article"]),
    )
    assert preflight["passed"] is True, [
        (gate["name"], gate["blockers"])
        for gate in preflight["gates"]
        if not gate["passed"]
    ]
    preflight_path = tmp_path / "research" / "real-preflight-readiness.json"
    publish_readiness.write_readiness_result(
        preflight_path,
        preflight,
        workspace_root=tmp_path,
    )

    finalized = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight_path,
        workspace_root=tmp_path,
    )
    final_bom_path = tmp_path / "research" / "final-bom-round-trip.json"
    write_blog_assembly_bom(final_bom_path, finalized)
    final = publish_readiness.build_final_readiness_attestation(
        preflight,
        final_bom=final_bom_path,
        run_id=_run_id(paths["article"]),
        workspace_root=tmp_path,
        dependencies=FinalizationDependencies(
            now=iter(
                (
                    "2026-08-11T14:08:00Z",
                    "2026-08-11T14:09:00Z",
                )
            ).__next__,
        ),
    )
    release_dir = tmp_path / "research" / "releases" / "blog-round-trip"
    manifest_path = release_dir / "release-manifest.json"
    previous_hash = finalized["workflow"]["stage_receipts"][-1]["receipt_hash"]
    final = prepare_final_release_result(
        final,
        release_manifest_path=manifest_path,
        previous_receipt_hash=previous_hash,
        workspace_root=tmp_path,
    )
    readiness_path = release_dir / "final-readiness.json"
    receipt_path = release_dir / "final-readiness-stage-receipt.json"
    publish_readiness.write_readiness_result(
        readiness_path,
        final,
        receipt_path=receipt_path,
        workspace_root=tmp_path,
    )

    authorization = load_publish_authorization(
        final_readiness_path=readiness_path,
        final_receipt_path=receipt_path,
        release_manifest_path=manifest_path,
        workspace_root=tmp_path,
    )
    calls: list[bytes] = []
    returned = authorization.with_final_input_seal(
        lambda article_bytes, _inventory: calls.append(article_bytes) or "published"
    )

    assert returned == "published"
    assert calls == [Path(paths["article"]).read_bytes()]
