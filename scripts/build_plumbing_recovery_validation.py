"""Build source-bound quality-gate evidence for the plumbing recovery article."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data_sources.modules.ai_copy_linter import lint_file
from data_sources.modules.content_scorer import ContentScorer
from data_sources.modules.content_scrubber import scrub_content
from data_sources.modules.context_binding_guard import check_file as check_context_binding
from data_sources.modules.faq_proof_guard import check_file as check_faq_proof
from data_sources.modules.metric_proof_pack_guard import check_file as check_metric_proof
from data_sources.modules.paa_provenance_guard import check_file as check_paa_provenance
from data_sources.modules.public_artifact_guard import check_file as check_public_artifact


ARTICLE = REPO_ROOT / "published" / "best-plumbing-job-management-software-rewrite-2026-09-03.md"
SIDECAR = REPO_ROOT / "research" / "validation-best-plumbing-job-management-software-2026-09-03.md"
PACKAGE = REPO_ROOT / "research" / "best-plumbing-job-management-software-remediation-2026-09-03"
CONTEXT_REQUEST = PACKAGE / "context-request.json"
CONTEXT_PACK = PACKAGE / "context-pack.json"
CONTEXT_RECEIPT = PACKAGE / "context-receipt.json"
PAA_ARTIFACT = PACKAGE / "answersocrates-paa.json"
OUTPUT = PACKAGE / "quality-gate-report.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [finding for finding in findings if finding.get("severity", "error") == "error"]
    warnings = [finding for finding in findings if finding.get("severity") == "warning"]
    return {
        "passed": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "findings": findings,
    }


def _run_guard(function: Callable[..., list[dict[str, Any]]], *args: Any, **kwargs: Any) -> dict[str, Any]:
    return _finding_summary(function(*args, **kwargs))


def main() -> int:
    content = ARTICLE.read_text(encoding="utf-8")
    scorer = ContentScorer()
    score = scorer.score(
        content,
        validate_urls=True,
        source_path=str(ARTICLE),
        proof_sidecar=str(SIDECAR),
    )

    guards = {
        "ai_copy_linter": _run_guard(lint_file, str(ARTICLE)),
        "public_artifact": _run_guard(check_public_artifact, ARTICLE),
        "paa_provenance": _run_guard(
            check_paa_provenance,
            str(ARTICLE),
            proof_sidecar=str(SIDECAR),
            workflow_mode="rewrite",
            expected_query="plumbing job management software",
            expected_collection_date="2026-09-03",
            paa_artifact=str(PAA_ARTIFACT),
        ),
        "faq_proof": _run_guard(
            check_faq_proof,
            str(ARTICLE),
            proof_sidecar=str(SIDECAR),
        ),
        "metric_proof_pack": _run_guard(
            check_metric_proof,
            str(ARTICLE),
            proof_sidecar=str(SIDECAR),
        ),
        "context_binding": _run_guard(
            check_context_binding,
            ARTICLE,
            proof_sidecar=SIDECAR,
            context_request=CONTEXT_REQUEST,
            context_pack=CONTEXT_PACK,
            context_receipt=CONTEXT_RECEIPT,
        ),
    }
    scrubbed = scrub_content(content)
    guards["content_scrubber_idempotence"] = {
        "passed": scrubbed == content,
        "error_count": 0 if scrubbed == content else 1,
        "warning_count": 0,
        "findings": [] if scrubbed == content else [
            {
                "rule_id": "content_scrubber_not_idempotent",
                "severity": "error",
                "message": "The final article changes when the content scrubber runs.",
            }
        ],
    }

    aeo = score["aeo_geo"]
    failed_aeo_checks = [
        name for name, result in aeo.get("checks", {}).items() if not result.get("passed")
    ]
    expected_blocker_only = failed_aeo_checks == ["metadata"]
    static_render = json.loads(
        (PACKAGE / "raw" / "replacement-render" / "static-validation.json").read_text(
            encoding="utf-8"
        )
    )
    browser_render = json.loads(
        (PACKAGE / "raw" / "replacement-render" / "browser-validation.json").read_text(
            encoding="utf-8"
        )
    )

    report = {
        "schema": "plumbing-remediation-quality-gate-report/v1",
        "article": {
            "path": str(ARTICLE.relative_to(REPO_ROOT)),
            "sha256": _sha256(ARTICLE),
            "analysis_word_count_including_image_alt_text": len(
                scorer._clean_for_analysis(content).split()
            ),
            "visible_article_word_count_from_preview": static_render[
                "visible_article_word_count"
            ],
        },
        "sidecar": {
            "path": str(SIDECAR.relative_to(REPO_ROOT)),
            "sha256": _sha256(SIDECAR),
        },
        "content_score": score,
        "standalone_guards": guards,
        "render_validation": {
            "static": static_render["summary"],
            "browser": browser_render["summary"],
        },
        "predeployment_status": {
            "content_quality_threshold_met": score["content_quality_score"] >= score["threshold"],
            "seo_quality_passed": score["quality_gates"]["seo_quality"]["passed"],
            "aeo_score_threshold_met": aeo["score"] >= 90,
            "aeo_overall_passed": aeo["passed"],
            "failed_aeo_checks": failed_aeo_checks,
            "only_expected_freshness_blocker": expected_blocker_only,
            "actual_date_modified_available": False,
            "cms_deployment_performed": False,
            "publish_ready": False,
            "blocker": (
                "The actual remediation deployment date does not exist yet. Add that real date "
                "to visible metadata and BlogPosting.dateModified only after CMS deployment, "
                "then rerun the gates."
            ),
        },
        "summary": {
            "all_standalone_guards_passed": all(
                result["passed"] for result in guards.values()
            ),
            "static_render_passed": static_render["summary"]["all_passed"],
            "browser_render_passed": browser_render["summary"]["all_passed"],
            "content_composite_score": score["composite_score"],
            "aeo_geo_score": aeo["score"],
            "final_publish_gate_passed": score["passed"],
        },
    }
    OUTPUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(report["summary"], indent=2))
    print(json.dumps(report["predeployment_status"], indent=2))
    print(f"report={OUTPUT}")

    honest_predeployment_success = (
        report["summary"]["all_standalone_guards_passed"]
        and report["summary"]["static_render_passed"]
        and report["summary"]["browser_render_passed"]
        and report["predeployment_status"]["content_quality_threshold_met"]
        and report["predeployment_status"]["seo_quality_passed"]
        and report["predeployment_status"]["aeo_score_threshold_met"]
        and report["predeployment_status"]["only_expected_freshness_blocker"]
    )
    return 0 if honest_predeployment_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
