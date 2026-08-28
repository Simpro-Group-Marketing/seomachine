from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_assembly_bom import write_blog_assembly_bom
from data_sources.modules.blog_assembly_contract import canonical_json_sha256
from data_sources.modules.post_publish_measurement_receipt import (
    build_receipt,
    check_receipt,
)
from tests.test_blog_assembly_bom import (
    _build as _build_blog_bom,
    _finalize_fixture_bom,
    _fixture as _blog_fixture,
    _preflight as _build_preflight,
)


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _observed_report(
    *,
    ga4_line: str = (
        "GA4 sessions: 120\n"
        "GA4 views: 140\n"
        "GA4 active users: 95\n"
        "GA4 engagement: 62%\n"
        "GA4 bounce rate: 38%\n"
        "GA4 average session duration: 00:02:10\n"
        "GA4 key events: 8"
    ),
) -> str:
    return (
        "# Performance review\n\n"
        "## Scope and evidence\n\n"
        "GSC google_search_console property-123 and GA4 google_analytics_4 property-123.\n\n"
        "## Executive findings\n\n"
        "Observed first-party evidence is available.\n\n"
        "## Prioritized opportunity queue\n\n"
        "Review the evidence-bound content opportunity.\n\n"
        "## Page and query evidence\n\n"
        "GSC clicks: 20\n"
        "GSC impressions: 400\n"
        "GSC CTR: 5%\n"
        "GSC average position: 8\n"
        "GSC queries: measurement receipt\n\n"
        f"{ga4_line}\n\n"
        "## Data-quality and causality limits\n\n"
        "The receipt records observation metadata only.\n\n"
        "## Recommended workflow handoffs\n\n"
        "Use the owning command after human review.\n\n"
        "## Measurement plan\n\n"
        "Review the same comparison windows.\n"
    )


def _blocked_report() -> str:
    return (
        "# Performance review\n\n"
        "## Scope and evidence\n\n"
        "Status: blocked.\n\n"
        "google_search_console | property-123 | access_denied | Access was not granted.\n\n"
        "google_analytics_4 | property-123 | access_denied | Access was not granted.\n\n"
        "## Data-quality and causality limits\n\n"
        "No first-party observation was available.\n"
    )


def _source(source_id: str, page_filter: dict[str, object], *, status: str = "observed") -> dict[str, object]:
    return {
        "source_id": source_id,
        "status": status,
        "property_id": "property-123",
        "filters": page_filter,
        "retrieved_at": "2026-08-21T12:00:00Z",
        "limitations": [],
        "blockers": [] if status == "observed" else [{"code": "access_denied", "detail": "Access was not granted."}],
    }


def _metadata(*, mode: str = "release_artifact", status: str = "observed") -> dict[str, object]:
    url = "https://www.example.com/blog/scheduling-guide/"
    binding: dict[str, object] = {
        "mode": mode,
        "canonical_url": url,
        "normalized_path": "/blog/scheduling-guide/",
    }
    if mode == "live_url":
        binding.update(
            {
                "verified_at": "2026-08-21T11:00:00Z",
                "verification_method": "live_canonical_observation",
                "limitations": ["No local release artifact was available for this observation."],
            }
        )
    return {
        "status": status,
        "collected_at": "2026-08-21T12:30:00Z",
        "article_binding": binding,
        "measurement_windows": {
            "primary": {"start_date": "2026-08-15", "end_date": "2026-08-21"},
            "comparison": {"start_date": "2026-08-08", "end_date": "2026-08-14"},
            "supplemental": [{"label": "launch_week", "start_date": "2026-08-15", "end_date": "2026-08-21"}],
        },
        "sources": {
            "gsc": [_source("google_search_console", {"page": url}, status=status)],
            "ga4": [_source("google_analytics_4", {"page_path": "/blog/scheduling-guide/"}, status=status)],
            "third_party_context": [],
        },
        "measurement_scope": {
            "business_objective": "Evaluate organic discovery after publication.",
            "conversion_definition": "Qualified demo request attributed to the article.",
            "conversion_not_applicable_reason": None,
            "success_measure": "Search visibility and qualified conversion trend.",
            "owner": "SEO team",
            "review_date": "2026-09-21",
        },
        "raw_data_artifacts": [{"lane": "gsc", "path": "research/raw-gsc.json"}],
        "optimization_recommendation": (
            {"summary": "Review search-query coverage.", "basis_lanes": ["gsc", "ga4"]}
            if status == "observed"
            else None
        ),
    }


@pytest.fixture
def artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )
    blog_paths = _blog_fixture(tmp_path)
    provisional = _build_blog_bom(tmp_path, blog_paths)
    provisional_path = tmp_path / "research" / "provisional-bom.json"
    write_blog_assembly_bom(provisional_path, provisional)
    preflight_path = _build_preflight(tmp_path, provisional_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=provisional_path,
        preflight_readiness_path=preflight_path,
        workspace_root=tmp_path,
    )
    bom = tmp_path / "research" / "final-bom.json"
    write_blog_assembly_bom(bom, final)

    article = blog_paths["article"]
    raw_data = _write(tmp_path / "research" / "raw-gsc.json", '{"rows": []}\n')
    report = _write(
        tmp_path / "research" / "performance.md",
        _observed_report(),
    )
    return {"article": article, "raw_data": raw_data, "report": report, "bom": bom}


def _release_receipt(artifacts: dict[str, Path]) -> dict[str, object]:
    return build_receipt(
        _metadata(),
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )


def _assert_report_rejected(
    artifacts: dict[str, Path], metadata: dict[str, object] | None = None
) -> None:
    with pytest.raises(ValueError, match="measurement_receipt_report_invalid"):
        build_receipt(
            metadata or _metadata(),
            artifacts["report"],
            artifacts["article"].parents[1],
            article_path=artifacts["article"],
            final_bom_path=artifacts["bom"],
        )


def _rule_ids(findings: list[dict[str, object]]) -> set[str]:
    return {str(finding["rule_id"]) for finding in findings}


def test_builds_valid_release_artifact_observed_receipt(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    root = artifacts["article"].parents[1]

    assert receipt["schema"] == "simpro-post-publish-measurement-receipt/v1"
    assert receipt["verification_scope"] == "recorded_observation_metadata"
    assert receipt["article_binding"]["article"] == {"path": artifacts["article"].relative_to(root).as_posix(), "sha256": _sha256(artifacts["article"])}
    assert receipt["article_binding"]["final_bom"] == {"path": "research/final-bom.json", "sha256": _sha256(artifacts["bom"])}
    assert receipt["performance_report"] == {"path": "research/performance.md", "sha256": _sha256(artifacts["report"])}
    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_builder_rejects_lookalike_final_bom(artifacts: dict[str, Path]):
    root = artifacts["article"].parents[1]
    lookalike = root / "research" / "lookalike-final-bom.json"
    _write(
        lookalike,
        json.dumps(
            {
                "schema": "simpro-blog-assembly-bom/v1",
                "lifecycle_state": "final",
                "artifacts": {
                    "article": {
                        "path": artifacts["article"].relative_to(root).as_posix(),
                        "sha256": _sha256(artifacts["article"]),
                    }
                },
            },
            indent=2,
        )
        + "\n",
    )

    with pytest.raises(ValueError, match="strict final"):
        build_receipt(
            _metadata(),
            artifacts["report"],
            root,
            article_path=artifacts["article"],
            final_bom_path=lookalike,
        )


def test_builder_non_object_bom_error_names_current_and_archived_schemas(
    artifacts: dict[str, Path],
):
    root = artifacts["article"].parents[1]
    non_object = _write(root / "research" / "non-object-final-bom.json", "[]\n")

    with pytest.raises(ValueError) as raised:
        build_receipt(
            _metadata(),
            artifacts["report"],
            root,
            article_path=artifacts["article"],
            final_bom_path=non_object,
        )

    message = str(raised.value)
    assert "simpro-blog-assembly-bom/v2" in message
    assert "archived final simpro-blog-assembly-bom/v1" in message


def test_builds_valid_live_url_observed_receipt_without_local_artifacts(artifacts: dict[str, Path]):
    receipt = build_receipt(_metadata(mode="live_url"), artifacts["report"], artifacts["article"].parents[1])

    assert receipt["article_binding"]["mode"] == "live_url"
    assert "article" not in receipt["article_binding"]
    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_builds_valid_fully_blocked_receipt(artifacts: dict[str, Path]):
    artifacts["report"].write_text(_blocked_report(), encoding="utf-8")
    receipt = build_receipt(_metadata(status="blocked"), artifacts["report"], artifacts["article"].parents[1], article_path=artifacts["article"], final_bom_path=artifacts["bom"])

    assert receipt["optimization_recommendation"] is None
    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_rejects_blocked_receipt_bound_to_recommendation_report(
    artifacts: dict[str, Path],
):
    artifacts["report"].write_text(
        _blocked_report()
        + "\n## Recommended workflow handoffs\n\nUse `/rewrite`.\n",
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts, _metadata(status="blocked"))


@pytest.mark.parametrize(
    "unsafe_prose",
    [
        "The verdict is to rewrite the article now.",
        "GA4 recorded 120 sessions.",
        "Revise the title tag now.",
        "Edit the article now.",
        "Use /analyze-existing next.",
        "# Next steps",
    ],
)
def test_rejects_blocked_report_with_hidden_decision_or_metric_prose(
    artifacts: dict[str, Path], unsafe_prose: str
):
    artifacts["report"].write_text(
        _blocked_report() + f"\n{unsafe_prose}\n",
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts, _metadata(status="blocked"))


def test_rejects_blocked_report_without_exact_source_blockers(
    artifacts: dict[str, Path],
):
    artifacts["report"].write_text(
        "# Performance review\n\n"
        "## Scope and evidence\n\nStatus: blocked.\n\n"
        "## Data-quality and causality limits\n\nEvidence was unavailable.\n",
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts, _metadata(status="blocked"))


def test_rejects_observed_report_metrics_from_a_blocked_lane(
    artifacts: dict[str, Path],
):
    metadata = _metadata()
    metadata["sources"]["ga4"][0]["status"] = "blocked"
    metadata["sources"]["ga4"][0]["blockers"] = [
        {"code": "access_denied", "detail": "Access was not granted."}
    ]
    metadata["optimization_recommendation"]["basis_lanes"] = ["gsc"]

    _assert_report_rejected(artifacts, metadata)


def test_accepts_partial_observation_when_blocked_lane_metrics_are_omitted(
    artifacts: dict[str, Path],
):
    metadata = _metadata()
    metadata["sources"]["ga4"][0]["status"] = "blocked"
    metadata["sources"]["ga4"][0]["blockers"] = [
        {"code": "access_denied", "detail": "Access was not granted."}
    ]
    metadata["optimization_recommendation"]["basis_lanes"] = ["gsc"]
    artifacts["report"].write_text(
        _observed_report(
            ga4_line=(
                "google_analytics_4 | property-123 | access_denied | "
                "Access was not granted."
            )
        ),
        encoding="utf-8",
    )

    receipt = build_receipt(
        metadata,
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )

    assert receipt["status"] == "observed"
    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_requires_blocked_third_party_context_details_in_the_report(
    artifacts: dict[str, Path],
):
    metadata = _metadata()
    metadata["sources"]["third_party_context"] = [
        _source(
            "independent_serp_context",
            {"target": "/blog/scheduling-guide/"},
            status="blocked",
        )
    ]

    _assert_report_rejected(artifacts, metadata)


def test_rejects_observed_report_without_required_observed_lane_metrics(
    artifacts: dict[str, Path],
):
    content = _observed_report()
    content = "\n".join(
        line
        for line in content.splitlines()
        if not line.startswith(("GSC ", "GA4 "))
    )
    artifacts["report"].write_text(content + "\n", encoding="utf-8")

    _assert_report_rejected(artifacts)


@pytest.mark.parametrize("placeholder", ["unavailable", "", "Access denied (403)"])
def test_rejects_observed_report_with_placeholder_metric_values(
    artifacts: dict[str, Path], placeholder: str
):
    artifacts["report"].write_text(
        _observed_report().replace(": 20", f": {placeholder}")
        .replace(": 400", f": {placeholder}")
        .replace(": 5%", f": {placeholder}")
        .replace(": 8\n", f": {placeholder}\n")
        .replace(": measurement receipt", f": {placeholder}")
        .replace(": 120", f": {placeholder}")
        .replace(": 140", f": {placeholder}")
        .replace(": 95", f": {placeholder}")
        .replace(": 62%", f": {placeholder}")
        .replace(": 38%", f": {placeholder}")
        .replace(": 00:02:10", f": {placeholder}")
        .replace(": 8\n", f": {placeholder}\n"),
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts)


@pytest.mark.parametrize(
    "qualifier",
    ["projected", "estimated", "forecast", "predicted", "modelled", "synthetic"],
)
def test_rejects_non_observed_qualifiers_on_numeric_metrics(
    artifacts: dict[str, Path], qualifier: str
):
    artifacts["report"].write_text(
        _observed_report().replace("GSC clicks: 20", f"GSC clicks: 20 {qualifier}"),
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts)


def test_rejects_metrics_hidden_in_indented_markdown_code(
    artifacts: dict[str, Path],
):
    report = _observed_report()
    for prefix in ("GSC ", "GA4 "):
        report = "\n".join(
            f"    {line}" if line.startswith(prefix) else line
            for line in report.splitlines()
        )
    artifacts["report"].write_text(report + "\n", encoding="utf-8")

    _assert_report_rejected(artifacts)


@pytest.mark.parametrize("value", ["forecasted queries", "synthetic query set"])
def test_rejects_non_observed_query_sets(
    artifacts: dict[str, Path], value: str
):
    artifacts["report"].write_text(
        _observed_report().replace("GSC queries: measurement receipt", f"GSC queries: {value}"),
        encoding="utf-8",
    )

    _assert_report_rejected(artifacts)


def test_rejects_report_contract_evidence_hidden_in_code_or_comments(
    artifacts: dict[str, Path],
):
    artifacts["report"].write_text(
        "# Performance review\n\n```markdown\n"
        + _observed_report()
        + "\n```\n",
        encoding="utf-8",
    )
    _assert_report_rejected(artifacts)

    artifacts["report"].write_text(
        "# Performance review\n\n<!-- hidden through EOF\n" + _observed_report(),
        encoding="utf-8",
    )
    _assert_report_rejected(artifacts)

    artifacts["report"].write_text(
        "# Performance review\n\n"
        "## Scope and evidence\n\nStatus: blocked.\n\n"
        "<!-- google_search_console | property-123 | access_denied | "
        "Access was not granted. -->\n"
        "<!-- google_analytics_4 | property-123 | access_denied | "
        "Access was not granted. -->\n\n"
        "## Data-quality and causality limits\n\n"
        "No first-party observation was available.\n",
        encoding="utf-8",
    )
    _assert_report_rejected(artifacts, _metadata(status="blocked"))


def test_rejects_self_hash_tampering_even_after_semantic_rehash(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["receipt_hash"] = "0" * 64
    assert "measurement_receipt_hash_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))

    receipt = _release_receipt(artifacts)
    receipt["status"] = "blocked"
    receipt["receipt_hash"] = canonical_json_sha256({key: value for key, value in receipt.items() if key != "receipt_hash"})
    assert "measurement_receipt_status_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


@pytest.mark.parametrize("artifact_name", ["article", "bom", "report", "raw_data"])
def test_rejects_mutated_bound_artifacts(artifacts: dict[str, Path], artifact_name: str):
    receipt = _release_receipt(artifacts)
    artifacts[artifact_name].write_text("mutated\n", encoding="utf-8")

    assert "measurement_receipt_artifact_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_rejects_optional_path_mismatch_and_partial_release_pairs(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    other = _write(artifacts["article"].parents[1] / "articles" / "other.md", "# Other\n")

    findings = check_receipt(receipt, artifacts["article"].parents[1], article_path=other)
    assert "measurement_receipt_path_mismatch" in _rule_ids(findings)
    with pytest.raises(ValueError, match="both article_path and final_bom_path"):
        build_receipt(_metadata(), artifacts["report"], artifacts["article"].parents[1], article_path=artifacts["article"])
    assert "measurement_receipt_path_mismatch" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1], final_bom_path=artifacts["bom"])
    )


def test_rejects_each_optional_artifact_path_mismatch(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    root = artifacts["article"].parents[1]
    other_bom = _write(root / "research" / "other-bom.json", "{}\n")
    other_report = _write(root / "research" / "other-report.md", "# Other\n")

    assert "measurement_receipt_path_mismatch" in _rule_ids(
        check_receipt(receipt, root, article_path=artifacts["article"], final_bom_path=other_bom)
    )
    assert "measurement_receipt_path_mismatch" in _rule_ids(
        check_receipt(receipt, root, performance_report_path=other_report)
    )


def test_live_url_builder_rejects_local_release_arguments(artifacts: dict[str, Path]):
    with pytest.raises(ValueError, match="live_url receipts cannot"):
        build_receipt(
            _metadata(mode="live_url"),
            artifacts["report"],
            artifacts["article"].parents[1],
            article_path=artifacts["article"],
            final_bom_path=artifacts["bom"],
        )


def test_rejects_url_path_and_measurement_window_contract_breaks(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["article_binding"]["normalized_path"] = "/wrong/"
    assert "measurement_receipt_binding_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))

    for comparison in (
        {"start_date": "2026-08-16", "end_date": "2026-08-14"},
        {"start_date": "2026-08-07", "end_date": "2026-08-13"},
        {"start_date": "2026-08-09", "end_date": "2026-08-14"},
    ):
        receipt = _release_receipt(artifacts)
        receipt["measurement_windows"]["comparison"] = comparison
        assert "measurement_receipt_windows_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_release_binding_rejects_a_different_url_even_when_its_filters_match(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    receipt["article_binding"]["canonical_url"] = (
        "https://www.example.com/blog/different-page/"
    )
    receipt["article_binding"]["normalized_path"] = "/blog/different-page/"
    receipt["sources"]["gsc"][0]["filters"]["page"] = (
        "https://www.example.com/blog/different-page/"
    )
    receipt["sources"]["ga4"][0]["filters"]["page_path"] = (
        "/blog/different-page/"
    )
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_binding_invalid" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


@pytest.mark.parametrize(
    ("canonical_url", "normalized_path"),
    [
        ("https://www.example.com:99999/blog/measurement/", "/blog/measurement/"),
        ("https://www.example.com:bad/blog/measurement/", "/blog/measurement/"),
        ("https://www.example.com:/blog/measurement/", "/blog/measurement/"),
        ("https://@www.example.com/blog/measurement/", "/blog/measurement/"),
        ("https://www%2eexample%2ecom/blog/measurement/", "/blog/measurement/"),
        ("https://www.example.com./blog/measurement/", "/blog/measurement/"),
        ("https://-www.example.com/blog/measurement/", "/blog/measurement/"),
        ("https://www_example.com/blog/measurement/", "/blog/measurement/"),
        ("https://www.example.com/blog/measurement/?", "/blog/measurement/"),
        ("https://www.example.com/blog/measurement/#", "/blog/measurement/"),
        ("https://www.example.com/blog/%2e%2e/admin/", "/blog/%2e%2e/admin/"),
        ("https://www.example.com/blog/%2Fadmin/", "/blog/%2Fadmin/"),
        (
            "https://www.example.com/blog/%2525252e%2525252e/admin/",
            "/blog/%2525252e%2525252e/admin/",
        ),
    ],
)
def test_rejects_malformed_or_encoded_noncanonical_url_identity(
    artifacts: dict[str, Path], canonical_url: str, normalized_path: str
):
    receipt = _release_receipt(artifacts)
    receipt["article_binding"]["canonical_url"] = canonical_url
    receipt["article_binding"]["normalized_path"] = normalized_path
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_binding_invalid" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


def test_requires_observed_first_party_evidence_and_valid_source_rows(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["status"] = "blocked"
    receipt["sources"]["gsc"][0]["blockers"] = [{"code": "denied", "detail": "Denied."}]
    receipt["sources"]["ga4"][0]["status"] = "blocked"
    receipt["sources"]["ga4"][0]["blockers"] = [{"code": "denied", "detail": "Denied."}]
    receipt["sources"]["third_party_context"] = [_source("independent_context", {"target": "https://www.example.com/blog/scheduling-guide/"})]
    assert "measurement_receipt_status_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))

    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"].append(copy.deepcopy(receipt["sources"]["gsc"][0]))
    receipt["sources"]["gsc"][0].pop("property_id")
    receipt["sources"]["ga4"][0]["retrieved_at"] = "2026-08-21T12:00:00+00:00"
    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_rejects_mixed_statuses_within_one_source_lane(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    blocked_row = copy.deepcopy(receipt["sources"]["gsc"][0])
    blocked_row.update(
        {
            "status": "blocked",
            "property_id": "property-456",
            "blockers": [{"code": "access_denied", "detail": "Access was denied."}],
        }
    )
    receipt["sources"]["gsc"].append(blocked_row)

    assert "measurement_receipt_sources_invalid" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


def test_rejects_missing_filters_and_noncanonical_source_filter(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0].pop("filters")
    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))

    receipt = _release_receipt(artifacts)
    receipt["sources"]["ga4"][0]["filters"] = {"page_path": "/wrong/"}
    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_requires_specific_blockers_and_forbids_blocked_recommendation(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["status"] = "blocked"
    for lane in ("gsc", "ga4"):
        receipt["sources"][lane][0]["status"] = "blocked"
        receipt["sources"][lane][0]["blockers"] = []
    receipt["optimization_recommendation"] = {"summary": "Do this.", "basis_lanes": ["gsc"]}

    assert "measurement_receipt_status_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_rejects_blocked_receipt_with_empty_first_party_blockers(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["status"] = "blocked"
    receipt["optimization_recommendation"] = None
    for lane in ("gsc", "ga4"):
        receipt["sources"][lane][0]["status"] = "blocked"
        receipt["sources"][lane][0]["blockers"] = []

    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


@pytest.mark.parametrize(
    "mutation",
    [
        lambda receipt: receipt.update({"unexpected": True}),
        lambda receipt: receipt["sources"]["gsc"][0].update({"forecast": "up"}),
        lambda receipt: receipt["measurement_windows"]["primary"].update({"end_date": "not-a-date"}),
        lambda receipt: receipt["performance_report"].update({"sha256": "A" * 64}),
    ],
)
def test_rejects_unknown_malformed_and_unsupported_predictive_fields(artifacts: dict[str, Path], mutation):
    receipt = _release_receipt(artifacts)
    mutation(receipt)

    assert check_receipt(receipt, artifacts["article"].parents[1])


def test_rejects_unsupported_causal_field_independently(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["optimization_recommendation"]["causal_claim"] = "The update caused growth."

    assert "measurement_receipt_prohibited_field" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


@pytest.mark.parametrize(
    "summary",
    [
        "The rewrite caused growth and will increase clicks by 25%.",
        "Forecast a ranking lift from the optimization.",
        "Traffic is projected to double because of this change.",
        "Clicks should increase by 25% after the rewrite.",
        "We anticipate more traffic after the update.",
        "The rewrite increased clicks.",
        "The update contributed to higher rankings.",
        "We expect more organic traffic.",
        "Traffic is likely to grow.",
        "The update produced higher rankings.",
        "Higher traffic is attributable to the rewrite.",
        "The update yielded higher rankings.",
        "The rewrite sparked traffic growth.",
        "The change prompted more clicks.",
        "We foresee more organic traffic.",
        "The rewrite brought more traffic.",
        "The article created higher visibility.",
        "The optimization delivered more clicks.",
        "The rewrite was responsible for the traffic increase.",
        "Traffic increased after the rewrite.",
        "Clicks rose following the update.",
        "Rankings improved after optimization.",
        "Sessions fell after the change.",
        "Traffic doubled after the rewrite.",
        "Review evidence. The rewrite explains the increase in traffic.",
        "Review evidence. The update accounts for higher traffic.",
        "Review evidence. The content is the reason clicks increased.",
        "Review evidence. The article brought about traffic growth.",
        "Review evidence. The optimization was behind the rise in rankings.",
        "Review evidence. Traffic gains stem from the rewrite.",
        "Review evidence. Traffic growth came from the update.",
        "Review evidence. Clicks rose as a consequence of the content change.",
        "Review the traffic gain attributable to the rewrite.",
        "Review higher traffic from the rewrite.",
        "Review traffic improvements from the rewrite.",
        "Review whether traffic gains are attributable to the rewrite and note that the rewrite caused traffic growth.",
        "Review whether traffic gains are attributable to the rewrite, as the rewrite caused higher traffic.",
        "Review whether traffic gains are attributable to the rewrite and expect traffic to grow.",
    ],
)
def test_rejects_forecast_or_causal_recommendation_prose(
    artifacts: dict[str, Path], summary: str
):
    receipt = _release_receipt(artifacts)
    receipt["optimization_recommendation"]["summary"] = summary
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_recommendation_invalid" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


def test_allows_legitimate_forecasting_software_topic_language(
    artifacts: dict[str, Path],
):
    artifacts["report"].write_text(
        _observed_report().replace(
            "GSC queries: measurement receipt",
            "GSC queries: workforce forecasting software",
        ),
        encoding="utf-8",
    )
    metadata = _metadata()
    metadata["measurement_scope"]["business_objective"] = (
        "Evaluate workforce forecasting software coverage."
    )
    receipt = build_receipt(
        metadata,
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )

    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_allows_nonassertive_recommendation_hypothesis(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    receipt["optimization_recommendation"]["summary"] = (
        "Review whether traffic gains are attributable to the rewrite."
    )
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


@pytest.mark.parametrize(
    "text",
    [
        "The article was created to explain organic traffic.",
        "The article explains traffic measurement.",
        "Content explains traffic sources.",
        "The content was created from GA4 traffic data.",
        "The update generated a report of traffic observations.",
        "The article delivered a definition of organic traffic.",
        "The content made traffic metrics easier to read.",
        "The rewrite was responsible for the traffic section.",
        "The article should explain organic traffic.",
        "The report should list clicks and impressions.",
        "We may review traffic data.",
        "The content could define bounce rate.",
        "The analyst might inspect conversions.",
    ],
)
def test_allows_noncausal_scope_language(
    artifacts: dict[str, Path], text: str
):
    receipt = _release_receipt(artifacts)
    receipt["measurement_scope"]["business_objective"] = text
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


@pytest.mark.parametrize(
    ("target", "assertion"),
    [
        ("success_measure", "The rewrite should increase qualified traffic."),
        ("business_objective", "The update contributed to higher rankings."),
        ("source_limitation", "Consent mode caused the session decline."),
        ("blocker_detail", "Access loss will reduce reported conversions."),
    ],
)
def test_rejects_forecast_or_causal_assertions_in_any_receipt_prose(
    artifacts: dict[str, Path], target: str, assertion: str
):
    receipt = _release_receipt(artifacts)
    if target == "source_limitation":
        receipt["sources"]["ga4"][0]["limitations"] = [assertion]
    elif target == "blocker_detail":
        receipt["sources"]["ga4"][0]["status"] = "blocked"
        receipt["sources"]["ga4"][0]["blockers"] = [
            {"code": "access_denied", "detail": assertion}
        ]
        receipt["optimization_recommendation"]["basis_lanes"] = ["gsc"]
    else:
        receipt["measurement_scope"][target] = assertion
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_prohibited_assertion" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


@pytest.mark.parametrize(
    "detail",
    [
        "Remove the FAQ now.",
        "Change the title tag now.",
        "Add internal links.",
        "Delete the final section.",
        "Access was denied. Consider removing the FAQ.",
        "Access was denied; try adding internal links.",
        "Access unavailable and add internal links.",
        "Permission failed, so remove the final section.",
        "The connector failed; the title needs changing.",
        "Access unavailable. A new title would help.",
        "Access denied. Cut the FAQ.",
        "Access denied. Prune the FAQ.",
        "Access denied. Shorten the article.",
        "Access denied. Link to another page.",
    ],
)
def test_rejects_action_text_disguised_as_a_source_blocker(
    artifacts: dict[str, Path], detail: str
):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["status"] = "blocked"
    receipt["sources"]["gsc"][0]["blockers"] = [
        {"code": "access_denied", "detail": detail}
    ]
    receipt["optimization_recommendation"]["basis_lanes"] = ["ga4"]
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_sources_invalid" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


@pytest.mark.parametrize(
    ("code", "detail"),
    [
        ("http_503", "The endpoint returned HTTP 503."),
        ("no_rows", "GSC returned no rows."),
        ("robots_blocked", "robots.txt prevented collection."),
        ("service_down", "The service was down."),
    ],
)
def test_allows_specific_action_free_source_blockers(
    artifacts: dict[str, Path], code: str, detail: str
):
    metadata = _metadata(status="blocked")
    for lane in ("gsc", "ga4"):
        metadata["sources"][lane][0]["blockers"] = [{"code": code, "detail": detail}]
    artifacts["report"].write_text(
        _blocked_report()
        .replace("access_denied", code)
        .replace("Access was not granted.", detail),
        encoding="utf-8",
    )

    receipt = build_receipt(
        metadata,
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )

    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_rejects_future_windows_and_post_collection_observation_timestamps(
    artifacts: dict[str, Path]
):
    root = artifacts["article"].parents[1]

    receipt = _release_receipt(artifacts)
    receipt["measurement_windows"]["primary"] = {
        "start_date": "2026-08-16",
        "end_date": "2026-08-22",
    }
    receipt["measurement_windows"]["comparison"] = {
        "start_date": "2026-08-09",
        "end_date": "2026-08-15",
    }
    assert "measurement_receipt_windows_invalid" in _rule_ids(
        check_receipt(receipt, root)
    )

    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["retrieved_at"] = "2026-08-21T12:31:00Z"
    assert "measurement_receipt_sources_invalid" in _rule_ids(
        check_receipt(receipt, root)
    )

    live = build_receipt(
        _metadata(mode="live_url"),
        artifacts["report"],
        root,
    )
    live["article_binding"]["verified_at"] = "2026-08-21T12:31:00Z"
    assert "measurement_receipt_binding_invalid" in _rule_ids(
        check_receipt(live, root)
    )

    receipt = _release_receipt(artifacts)
    receipt["collected_at"] = "2099-01-01T00:00:00Z"
    assert "measurement_receipt_schema_invalid" in _rule_ids(
        check_receipt(receipt, root)
    )

    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["retrieved_at"] = "2026-08-14T23:59:59Z"
    assert "measurement_receipt_sources_invalid" in _rule_ids(
        check_receipt(receipt, root)
    )


def test_raw_data_artifacts_remain_optional_for_observed_receipts(
    artifacts: dict[str, Path],
):
    metadata = _metadata()
    metadata["raw_data_artifacts"] = []

    receipt = build_receipt(
        metadata,
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )

    assert receipt["raw_data_artifacts"] == []
    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_allows_third_party_context_filter_bound_to_normalized_path(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["third_party_context"] = [
        _source("independent_serp_context", {"target": "/blog/scheduling-guide/"})
    ]
    receipt["receipt_hash"] = canonical_json_sha256({key: value for key, value in receipt.items() if key != "receipt_hash"})

    assert check_receipt(receipt, artifacts["article"].parents[1]) == []


def test_rejects_unknown_artifact_and_generic_recommendation_fields_after_rehash(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["performance_report"]["unexpected"] = True
    receipt["optimization_recommendation"]["recommendation"] = "Do more."
    receipt["receipt_hash"] = canonical_json_sha256({key: value for key, value in receipt.items() if key != "receipt_hash"})

    rule_ids = _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))
    assert "measurement_receipt_artifact_invalid" in rule_ids
    assert "measurement_receipt_prohibited_field" in rule_ids


def test_rejects_unhashable_third_party_target_without_raising(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["third_party_context"] = [
        _source("independent_serp_context", {"target": ["/blog/scheduling-guide/"]})
    ]

    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_builder_rejects_release_metadata_computed_rows_and_copies_metadata(artifacts: dict[str, Path]):
    metadata = _metadata()
    metadata["article_binding"]["article"] = {"path": "articles/measurement.md", "sha256": "0" * 64}
    with pytest.raises(ValueError, match="cannot contain computed"):
        build_receipt(
            metadata,
            artifacts["report"],
            artifacts["article"].parents[1],
            article_path=artifacts["article"],
            final_bom_path=artifacts["bom"],
        )

    metadata = _metadata()
    receipt = build_receipt(
        metadata,
        artifacts["report"],
        artifacts["article"].parents[1],
        article_path=artifacts["article"],
        final_bom_path=artifacts["bom"],
    )
    metadata["sources"]["gsc"][0]["filters"]["page"] = "https://changed.example/"
    assert receipt["sources"]["gsc"][0]["filters"]["page"] == "https://www.example.com/blog/scheduling-guide/"


@pytest.mark.parametrize("normalized_path", ["/blog/../measurement/", "/blog\\measurement/", "/blog/measurement path/"])
def test_rejects_noncanonical_normalized_paths(artifacts: dict[str, Path], normalized_path: str):
    receipt = _release_receipt(artifacts)
    receipt["article_binding"]["normalized_path"] = normalized_path

    assert "measurement_receipt_binding_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_rejects_unhashable_recommendation_basis_lane_without_raising(artifacts: dict[str, Path]):
    receipt = _release_receipt(artifacts)
    receipt["optimization_recommendation"]["basis_lanes"] = [{"lane": "gsc"}]

    assert "measurement_receipt_recommendation_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_check_receipt_returns_findings_for_non_json_python_values(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    receipt["status"] = {"observed"}

    findings = check_receipt(receipt, artifacts["article"].parents[1])

    assert "measurement_receipt_hash_invalid" in _rule_ids(findings)
    assert "measurement_receipt_status_invalid" in _rule_ids(findings)


@pytest.mark.parametrize("malformed_value", [[], {}])
@pytest.mark.parametrize(
    ("target", "expected_rule"),
    [
        ("receipt_status", "measurement_receipt_status_invalid"),
        ("source_status", "measurement_receipt_sources_invalid"),
        ("third_party_source_id", "measurement_receipt_sources_invalid"),
        ("raw_artifact_path", "measurement_receipt_artifact_invalid"),
    ],
)
def test_check_receipt_returns_findings_for_json_container_values(
    artifacts: dict[str, Path], target: str, expected_rule: str, malformed_value: object
):
    receipt = _release_receipt(artifacts)
    if target == "receipt_status":
        receipt["status"] = malformed_value
    elif target == "source_status":
        receipt["sources"]["gsc"][0]["status"] = malformed_value
    elif target == "third_party_source_id":
        receipt["sources"]["third_party_context"] = [
            _source("independent_context", {"target": "/blog/scheduling-guide/"})
        ]
        receipt["sources"]["third_party_context"][0]["source_id"] = malformed_value
    else:
        receipt["raw_data_artifacts"][0]["path"] = malformed_value

    assert expected_rule in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


@pytest.mark.parametrize(
    "field_name",
    [
        "traffic_forecast",
        "trafficForecast",
        "traffic_projection",
        "predicted_impact",
        "expected_impact",
        "projected_clicks",
        "anticipated_traffic",
        "estimated_rankings",
        "causedBy",
    ],
)
def test_rejects_normalized_prohibited_field_names_after_rehash(artifacts: dict[str, Path], field_name: str):
    receipt = _release_receipt(artifacts)
    receipt["optimization_recommendation"][field_name] = "unsupported"
    receipt["receipt_hash"] = canonical_json_sha256({key: value for key, value in receipt.items() if key != "receipt_hash"})

    assert "measurement_receipt_prohibited_field" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_rejects_projected_fields_hidden_in_flexible_source_filters(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["filters"]["projected_clicks"] = 500
    receipt["receipt_hash"] = canonical_json_sha256(
        {key: value for key, value in receipt.items() if key != "receipt_hash"}
    )

    assert "measurement_receipt_prohibited_field" in _rule_ids(
        check_receipt(receipt, artifacts["article"].parents[1])
    )


def test_check_receipt_returns_findings_for_recursive_python_mapping(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    recursive: dict[str, object] = {}
    recursive["self"] = recursive
    receipt["measurement_scope"]["owner"] = recursive

    findings = check_receipt(receipt, artifacts["article"].parents[1])

    assert "measurement_receipt_schema_invalid" in _rule_ids(findings)
    assert "measurement_receipt_hash_invalid" in _rule_ids(findings)


def test_check_receipt_returns_findings_for_deep_python_containers(
    artifacts: dict[str, Path],
):
    receipt = _release_receipt(artifacts)
    nested: object = None
    for _ in range(1500):
        nested = [nested]
    receipt["unexpected"] = nested

    findings = check_receipt(receipt, artifacts["article"].parents[1])

    assert "measurement_receipt_schema_invalid" in _rule_ids(findings)
    assert "measurement_receipt_hash_invalid" in _rule_ids(findings)


def test_cli_rejects_deep_json_without_traceback(
    artifacts: dict[str, Path],
):
    root = artifacts["article"].parents[1]
    receipt_path = root / "research" / "deep-receipt.json"
    receipt_path.write_text(
        '{"unexpected":' + "[" * 1500 + "null" + "]" * 1500 + "}",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_sources.modules.post_publish_measurement_receipt",
            "check",
            str(receipt_path),
            "--workspace-root",
            str(root),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "measurement_receipt_schema_invalid" in result.stdout


@pytest.mark.parametrize("filter_value", [float("nan"), float("inf"), float("-inf"), [float("nan")], [float("inf")]])
def test_rejects_nonfinite_filter_values(artifacts: dict[str, Path], filter_value: object):
    receipt = _release_receipt(artifacts)
    receipt["sources"]["gsc"][0]["filters"] = {"page": "https://www.example.com/blog/scheduling-guide/", "metric": filter_value}

    assert "measurement_receipt_sources_invalid" in _rule_ids(check_receipt(receipt, artifacts["article"].parents[1]))


def test_cli_check_malformed_container_emits_json_findings_without_traceback(artifacts: dict[str, Path]):
    root = artifacts["article"].parents[1]
    receipt_path = root / "research" / "malformed-receipt.json"
    receipt = _release_receipt(artifacts)
    receipt["status"] = []
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_sources.modules.post_publish_measurement_receipt",
            "check",
            str(receipt_path),
            "--workspace-root",
            str(root),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "measurement_receipt_status_invalid" in _rule_ids(json.loads(result.stdout))


def test_cli_rejects_nonstandard_json_constants(artifacts: dict[str, Path]):
    root = artifacts["article"].parents[1]
    receipt_path = root / "research" / "nonstandard-receipt.json"
    receipt = _release_receipt(artifacts)
    receipt_path.write_text(
        json.dumps(receipt).replace('"status": "observed"', '"status": NaN'),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_sources.modules.post_publish_measurement_receipt",
            "check",
            str(receipt_path),
            "--workspace-root",
            str(root),
        ],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert "non-standard JSON constant" in result.stderr


def test_cli_build_and_check_and_tamper_failure(artifacts: dict[str, Path]):
    root = artifacts["article"].parents[1]
    metadata_path = _write(root / "research" / "metadata.json", json.dumps(_metadata()) + "\n")
    receipt_path = root / "research" / "receipt.json"
    command = [
        sys.executable,
        "-m",
        "data_sources.modules.post_publish_measurement_receipt",
        "build",
        "--metadata", str(metadata_path),
        "--performance-report", str(artifacts["report"]),
        "--article", str(artifacts["article"]),
        "--final-bom", str(artifacts["bom"]),
        "--output", str(receipt_path),
        "--workspace-root", str(root),
    ]
    repo_root = Path(__file__).parents[1]
    assert subprocess.run(command, cwd=repo_root, capture_output=True, text=True).returncode == 0
    check_command = command[:3] + ["check", str(receipt_path), "--workspace-root", str(root)]
    assert subprocess.run(check_command, cwd=repo_root, capture_output=True, text=True).returncode == 0

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["status"] = "blocked"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert subprocess.run(check_command, cwd=repo_root, capture_output=True, text=True).returncode != 0
