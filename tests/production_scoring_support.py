"""A compliant BigChange (nonconnector) article and the production BOM it was written from.

The article is the release round-trip fixture plus an E-E-A-T story paragraph and a FAQ.
The BOM's PAA block and customer-proof block are built with the real builder functions
from a real AnswerSocrates fixture artifact and real nonvault selector evidence.
"""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path
from typing import Any

from data_sources.modules.customer_proof.nonconnector_persistence import write_nonvault_selector_evidence
from data_sources.modules.production.bom import BOM_SCHEMA
from data_sources.modules.production.bom_artifacts import resolve_paa
from data_sources.modules.production.bom_selector import bind_selector_evidence
from data_sources.modules.production.layout import Layout, load_or_create_run_id
from tests.nonvault_proof_fixture import BIGCHANGE_CAPTERRA_URL, write_bigchange_review_proof_inputs
from tests.research_provenance_fixtures import build_answersocrates_fixture
from tests.test_blog_release_lifecycle_roundtrip import _ARTICLE

TODAY = "2026-08-11"
ARTICLE = f"drafts/scoring-scheduling-guide-{TODAY}.md"
RUN_ID = "4f0c2a0e-9a51-4c47-9f39-6a1d1b2c3d4e"
QUERY = "field service scheduling guide"
STORY_ID = "bigchange-review-capterra-owner-job-scheduling"
OWNED_URL = "https://www.bigchange.com/field-service-management-software/"
Q1 = "How often should a dispatcher review the field service schedule?"
Q2 = "What should a technician handoff include?"
ROLES = ["metric", "quote", "theme", "experience_story"]
SCHEMA_NOTES = [
    "BlogPosting",
    "BreadcrumbList",
    "ImageObject for the featured image or logo",
    "Organization as publisher reference only, not a separate full schema block",
    "FAQPage",
    "Question and Answer inside FAQPage",
]
STORY = (
    "Dana R, an operations manager, describes faster job scheduling and clearer engineer "
    f"visibility after switching to JobWatch in a [public Capterra account]({BIGCHANGE_CAPTERRA_URL}).\n"
)
FAQ = f"""
## Frequently asked questions

### {Q1}

Review the schedule at the start of each day and again whenever priorities change. Check fixed commitments first, then urgent requests, planned work, and follow-up tasks. Record each exception with its reason, name one owner for the next decision, and confirm the handoff before the technician travels to the job.

### {Q2}

A technician handoff should include the destination, contact, requested outcome, access notes, and any open question, placed before travel starts. Keep internal discussion out of it. Teams that dispatch in [BigChange field service management software]({OWNED_URL}) can keep the handoff beside the job record for the next schedule decision.
"""


def article_text() -> str:
    text = _ARTICLE.replace(
        "  - Organization as publisher reference only, not a separate full schema block\n",
        "  - Organization as publisher reference only, not a separate full schema block\n"
        "  - FAQPage\n  - Question and Answer inside FAQPage\n",
    )
    return text.replace("\n## Close the scheduling loop\n", f"\n{STORY}\n## Close the scheduling loop\n") + FAQ


def _write_evidence(layout: Layout) -> None:
    index, ledger = write_bigchange_review_proof_inputs(layout.root / "config")
    write_nonvault_selector_evidence(
        layout.nonvault_customer_proof_evidence, topic=QUERY, brand="BigChange", title="Scheduling guide",
        objective="Help service leaders improve scheduling decisions", article_slug=layout.slug, roles=ROLES,
        require_eeat_story=True, limit=10, reference_date=date.fromisoformat(TODAY),
        selected_overrides={"experience_story": STORY_ID}, rejected_overrides={},
        index_path=index, ledger_path=ledger,
    )


def _identity(layout: Layout) -> dict[str, Any]:
    return {
        "slug": layout.slug, "date": layout.date, "run_id": RUN_ID, "brand": "BigChange", "market": "US",
        "workflow_mode": layout.workflow_mode, "article_path": ARTICLE, "title": "Scheduling guide",
        "objective": "Help service leaders improve scheduling decisions", "audience": "Field service leaders",
        "cta": {"text": "Explore", "url": OWNED_URL}, "schema_notes": SCHEMA_NOTES,
        "spec": {"path": f"research/production-bom-spec-{layout.slug}-{layout.date}.json", "sha256": "0" * 64},
    }


def _proof_item() -> dict[str, Any]:
    return {
        "id": "p1", "claim_id": STORY_ID, "kind": "experience_story", "priority": "must",
        "text": "The public Capterra review describes faster job scheduling and real-time visibility for field engineers.",
        "customer": "Dana R", "url": BIGCHANGE_CAPTERRA_URL, "restrictions": [],
        "approved_quotes": [], "approved_metrics": [],
    }


def _fact() -> dict[str, Any]:
    return {
        "id": "f1", "claim": "BigChange sells field service management software", "url": OWNED_URL,
        "quote": "field service management software", "priority": "should",
        "verified_at": f"{TODAY}T08:00:00Z", "check_detail": "quote found on page", "support": "quote_overlap",
    }


def make_scoring_workspace(root: Path) -> tuple[Path, dict[str, Any]]:
    """Write the article and its bound research artifacts; return (article path, BOM)."""
    layout = Layout.for_article(ARTICLE, root)
    layout.article.parent.mkdir(parents=True, exist_ok=True)
    layout.article.write_text(article_text(), encoding="utf-8", newline="\n")
    layout.paa_artifact.parent.mkdir(parents=True, exist_ok=True)
    capture = build_answersocrates_fixture(
        root, query=QUERY, collection_date=TODAY, questions=[Q1, Q2, "What is dispatch?"], run_id=RUN_ID
    )
    layout.paa_artifact.write_text(json.dumps(capture, indent=2) + "\n", encoding="utf-8", newline="\n")
    load_or_create_run_id(layout, run_id=RUN_ID)
    _write_evidence(layout)
    proof = [_proof_item()]
    questions = [{"question": Q1, "priority": "must"}, {"question": Q2, "priority": "should"}]
    bom = {
        "schema": BOM_SCHEMA, "identity": _identity(layout),
        "keyword": {"primary": QUERY, "secondary": ["capacity planning", "dispatch constraints"]},
        "serp": {"query": QUERY}, "sections": [], "facts": [_fact()], "proof": proof,
        "paa": resolve_paa({"paa_questions": questions}, layout),
        "links": [{"url": OWNED_URL, "anchor": "BigChange field service management software",
                   "kind": "internal", "priority": "must"}],
        "context": {"status": "not_applicable", "reason": "BigChange workflow with no brand-vault signal"},
        "customer_proof": bind_selector_evidence(layout, proof, True),
    }
    return layout.article, bom


def without_question(bom: dict[str, Any], question: str) -> dict[str, Any]:
    changed = copy.deepcopy(bom)
    changed["paa"]["questions"] = [q for q in changed["paa"]["questions"] if q["question"] != question]
    return changed


def scorer_result(*, content: float = 95, seo: float = 95, critical: list[str] | None = None,
                  aeo: float = 95, aeo_passed: bool = True) -> dict[str, Any]:
    """A scorer result shaped like ContentScorer.score output, for gate-logic tests."""
    return {
        "priority_fixes": [{"dimension": "seo", "issue": "x"}],
        "aeo_geo": {"score": aeo, "threshold": 90, "passed": aeo_passed, "checks": {}},
        "quality_gates": {
            "content_quality": {"score": content, "threshold": 85, "passed": content >= 85},
            "seo_quality": {"score": seo, "threshold": 90, "passed": seo >= 90 and not critical,
                            "critical_issues": list(critical or []), "critical_issue_count": len(critical or [])},
            "aeo_geo": {"score": aeo, "threshold": 90, "passed": aeo_passed},
        },
    }


__all__ = [
    "OWNED_URL", "Q1", "Q2", "RUN_ID", "TODAY", "article_text", "make_scoring_workspace", "scorer_result",
    "without_question",
]
