from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from datetime import date

import pytest
from unittest.mock import patch

from data_sources.modules import blog_assembly_bom_guard
from data_sources.modules import blog_assembly_contract
from data_sources.modules.blog_assembly_bom_guard import check_bom
from data_sources.modules.blog_assembly_bom import (
    finalize_blog_assembly_bom,
    write_blog_assembly_bom,
)
from data_sources.modules.blog_assembly_stage_receipt import (
    build_stage_receipt,
    receipt_hash,
    write_stage_receipt,
)


from tests.test_blog_assembly_bom import (
    _build,
    _finalize_fixture_bom,
    _fixture,
    _preflight,
    _prepare_optimized_workflow,
)



@pytest.fixture(autouse=True)
def _freeze_workflow_clock(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        blog_assembly_contract,
        "current_utc_date",
        lambda: date(2026, 8, 11),
    )


def _rules(tmp_path: Path, bom: dict, paths: dict[str, Path], **kwargs) -> set[str]:
    return {
        str(finding["rule_id"])
        for finding in check_bom(
            bom,
            article_path=paths["article"],
            validation_sidecar_path=paths["sidecar"],
            workspace_root=tmp_path,
            **kwargs,
        )
    }


def test_stale_article_hash_is_blocking(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    paths["article"].write_text(
        paths["article"].read_text(encoding="utf-8") + "Tampered.\n",
        encoding="utf-8",
    )

    assert "bom_article_hash_mismatch" in _rules(tmp_path, bom, paths)


def test_workflow_chain_missing_canonical_article_identity_is_blocking(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["assembly_date"] = "not-a-date"

    assert "bom_stage_canonical_identity_invalid" in _rules(
        tmp_path,
        bom,
        paths,
    )


def test_valid_provisional_bom_passes_strict_guard(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)

    assert _rules(
        tmp_path,
        bom,
        paths,
        expected_lifecycle_state="provisional",
    ) == set()


def test_guard_rejects_definition_changed_after_bom_build(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    definition = tmp_path / ".claude" / "commands" / "article.md"
    definition.write_text(
        definition.read_text(encoding="utf-8") + "\nRepository change.\n",
        encoding="utf-8",
    )

    assert "capability_definition_stale" in _rules(tmp_path, bom, paths)


def test_guard_rejects_historical_receipt_without_capability_bindings(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    draft_path = paths["stage_receipts"][0]
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    draft["evidence_hashes"] = {
        "serp_evidence": draft["evidence_hashes"]["serp_evidence"]
    }
    draft_path.write_text(json.dumps(draft, indent=2) + "\n", encoding="utf-8")
    bom["workflow"]["stage_receipts"][0] = draft
    bom["artifacts"]["stage_receipts"][0]["sha256"] = hashlib.sha256(
        draft_path.read_bytes()
    ).hexdigest()

    assert "bom_draft_capability_evidence_unbound" in _rules(
        tmp_path,
        bom,
        paths,
    )


def test_editorial_plan_duplicate_key_is_a_blocker_not_silently_ignored(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    plan_path = paths["editorial_plan"]
    raw = plan_path.read_text(encoding="utf-8")
    plan_path.write_text(
        raw.replace(
            '"schema": "simpro-blog-editorial-plan/v1",',
            '"schema": "simpro-blog-editorial-plan/v1",\n'
            '  "schema": "simpro-blog-editorial-plan/v1",',
            1,
        ),
        encoding="utf-8",
    )
    bom["artifacts"]["editorial_plan"]["sha256"] = hashlib.sha256(
        plan_path.read_bytes()
    ).hexdigest()

    assert "bom_editorial_plan_invalid" in _rules(tmp_path, bom, paths)


def test_editorial_plan_validation_consumes_the_bound_snapshot_bytes(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    real_loader = blog_assembly_bom_guard.load_json_object_snapshot

    def replace_after_snapshot(path: object, *, field: str):
        snapshot = real_loader(path, field=field)
        if Path(path).resolve() == paths["editorial_plan"].resolve():
            paths["editorial_plan"].write_text("{}\n", encoding="utf-8")
        return snapshot

    with patch.object(
        blog_assembly_bom_guard,
        "load_json_object_snapshot",
        side_effect=replace_after_snapshot,
    ):
        rules = _rules(tmp_path, bom, paths)

    assert not any(rule.startswith("bom_editorial_plan_") for rule in rules)


def test_non_connector_bom_reason_must_match_context_binding_receipt(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["connector_binding"]["reason"] = (
        "Article review found no connector-sensitive claims."
    )

    assert "bom_context_not_applicable_reason_unbound" in _rules(
        tmp_path,
        bom,
        paths,
        expected_lifecycle_state="provisional",
    )


def test_valid_final_bom_with_real_preflight_receipt_passes(tmp_path: Path):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )

    assert _rules(
        tmp_path,
        final,
        paths,
        expected_lifecycle_state="final",
    ) == set()


def test_final_bom_requires_unchanged_historical_provisional_bom(tmp_path: Path):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )


@pytest.mark.parametrize(
    ("raw", "strict_error"),
    (
        (b'{"schema":"one","schema":"two"}\n', "duplicate key"),
        (b'{"score":NaN}\n', "non-finite"),
    ),
)
def test_bound_preflight_readiness_rejects_permissive_json(
    tmp_path: Path,
    raw: bytes,
    strict_error: str,
):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )
    preflight.write_bytes(raw)
    final["artifacts"]["preflight_readiness"]["sha256"] = hashlib.sha256(
        raw
    ).hexdigest()

    findings = blog_assembly_bom_guard.check_bom(
        final,
        article_path=paths["article"],
        validation_sidecar_path=paths["sidecar"],
        workspace_root=tmp_path,
        expected_lifecycle_state="final",
    )
    blockers = [
        finding
        for finding in findings
        if finding["rule_id"] == "bom_preflight_invalid"
    ]
    assert blockers
    assert strict_error in blockers[0]["message"]


@pytest.mark.parametrize(
    "raw",
    (
        b'{"schema":"one","schema":"two"}\n',
        b'{"score":NaN}\n',
    ),
)
def test_historical_provisional_bom_rejects_permissive_json(
    tmp_path: Path,
    raw: bytes,
):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )
    bom_path.write_bytes(raw)
    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    readiness["input_hashes"]["assembly_bom"]["sha256"] = hashlib.sha256(
        raw
    ).hexdigest()
    preflight.write_text(
        json.dumps(readiness, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    final["artifacts"]["preflight_readiness"]["sha256"] = hashlib.sha256(
        preflight.read_bytes()
    ).hexdigest()

    assert "bom_preflight_bom_artifact_invalid" in _rules(
        tmp_path,
        final,
        paths,
        expected_lifecycle_state="final",
    )
    bom_path.write_text('{"tampered": true}\n', encoding="utf-8")

    assert "bom_preflight_bom_artifact_invalid" in _rules(
        tmp_path,
        final,
        paths,
        expected_lifecycle_state="final",
    )


def test_final_bom_rejects_base_policy_changed_after_preflight(tmp_path: Path):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )

    final["faq_policy"]["rationale"] = "Changed after the passed preflight."

    assert "bom_preflight_bom_hash_mismatch" in _rules(
        tmp_path,
        final,
        paths,
        expected_lifecycle_state="final",
    )


def test_final_bom_rejects_preflight_receipt_not_bound_to_readiness_output(
    tmp_path: Path,
):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )
    receipt_row = final["artifacts"]["stage_receipts"][-1]
    receipt_path = tmp_path / receipt_row["path"]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["output_artifact_hashes"]["readiness_output"] = "0" * 64
    receipt["receipt_hash"] = receipt_hash(receipt)
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    receipt_row["sha256"] = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    final["workflow"]["stage_receipts"][-1] = receipt

    assert "bom_preflight_stage_receipt_invalid" in _rules(
        tmp_path,
        final,
        paths,
        expected_lifecycle_state="final",
    )


def test_lifecycle_state_must_match_readiness_phase(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)

    assert "bom_lifecycle_state_mismatch" in _rules(
        tmp_path,
        bom,
        paths,
        expected_lifecycle_state="final",
    )


def test_author_policy_is_compared_with_final_frontmatter(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["author_policy"]["status"] = "named_author"

    assert "bom_author_policy_mismatch" in _rules(tmp_path, bom, paths)


def test_schema_policy_is_compared_with_actual_visible_faq_state(tmp_path: Path):
    paths = _fixture(tmp_path, visible_faq=True)
    bom = _build(tmp_path, paths)
    bom["schema_policy"]["required_entities"].remove("FAQPage")

    assert "bom_schema_policy_mismatch" in _rules(tmp_path, bom, paths)


def test_topology_tokens_are_rejected_anywhere_outside_connector_artifacts(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["identity"]["title"] = "wiki/authority_root/voice.md"

    assert "bom_hard_coded_vault_topology" in _rules(tmp_path, bom, paths)


def test_topology_tokens_are_rejected_in_nested_mapping_keys(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["workflow"]["stage_receipts"][0]["evidence_hashes"][
        "wiki/internal-note.md"
    ] = "0" * 64

    rules = {
        finding["rule_id"]
        for finding in blog_assembly_bom_guard._check_topology(bom)
    }

    assert "bom_hard_coded_vault_topology" in rules


def test_path_shaped_non_artifact_string_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["connector_binding"]["reason"] = "C:/internal/context.json"

    assert "bom_path_leakage" in _rules(tmp_path, bom, paths)


def test_missing_bound_paa_artifact_is_blocking(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["artifacts"]["paa_artifact"] = None

    assert "bom_paa_artifact_missing" in _rules(tmp_path, bom, paths)


def test_invalid_collection_type_yields_stable_finding_not_exception(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["artifacts"]["stage_receipts"] = "not-a-list"

    assert "bom_stage_receipts_invalid" in _rules(tmp_path, bom, paths)


def test_loose_v1_shape_and_artifact_rows_are_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["legacy_note"] = "accepted by the old loose v1"
    bom["artifacts"]["article"]["caller_supplied"] = True

    rules = _rules(tmp_path, bom, paths)

    assert "bom_shape_unknown_fields" in rules
    assert "bom_article_invalid" in rules


def test_identity_rejects_unknown_nested_fields(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["identity"]["invented"] = "not part of v1"

    assert "bom_identity_shape_invalid" in _rules(tmp_path, bom, paths)


def test_connector_binding_rejects_unknown_nested_fields(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["connector_binding"]["invented"] = "not part of v1"

    assert "bom_connector_binding_shape_invalid" in _rules(tmp_path, bom, paths)


def test_workflow_rejects_unknown_nested_fields(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["workflow"]["invented"] = "not part of v1"

    assert "bom_workflow_shape_invalid" in _rules(tmp_path, bom, paths)


def test_faq_policy_rejects_unknown_nested_fields(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["faq_policy"]["invented"] = "not part of v1"

    assert "bom_faq_policy_shape_invalid" in _rules(tmp_path, bom, paths)


def test_faq_policy_must_exactly_match_bound_editorial_plan(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["faq_policy"]["rationale"] = "Caller-supplied replacement rationale."

    assert "bom_faq_policy_mismatch" in _rules(tmp_path, bom, paths)


def test_unknown_artifact_inventory_fields_are_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["artifacts"]["invented_evidence"] = bom["artifacts"]["serp_evidence"]

    assert "bom_artifacts_unknown_fields" in _rules(tmp_path, bom, paths)


def test_path_key_outside_declared_artifact_fields_is_not_exempt(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["connector_binding"]["debug"] = {"path": "C:/private/context.json"}

    assert "bom_path_leakage" in _rules(tmp_path, bom, paths)


def test_editorial_plan_escape_is_rejected_before_any_read(tmp_path: Path):
    outside = tmp_path.parent / "outside-editorial-plan.json"
    outside.write_text("{}", encoding="utf-8")
    artifacts = {
        "editorial_plan": {
            "path": "../outside-editorial-plan.json",
            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
        }
    }
    try:
        with patch.object(Path, "read_text", side_effect=AssertionError("unsafe read")):
            findings = blog_assembly_bom_guard._check_editorial_plan(
                {},
                artifacts,
                tmp_path,
            )
    finally:
        outside.unlink(missing_ok=True)

    assert {finding["rule_id"] for finding in findings} == {
        "bom_editorial_plan_invalid"
    }


def test_stage_receipt_escape_is_rejected_before_any_read(tmp_path: Path):
    outside = tmp_path.parent / "outside-stage-receipt.json"
    outside.write_text("{}", encoding="utf-8")
    artifacts = {
        "article": None,
        "optimizer_outputs": [],
        "stage_receipts": [
            {
                "path": "../outside-stage-receipt.json",
                "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            }
        ],
    }
    try:
        with patch.object(Path, "read_text", side_effect=AssertionError("unsafe read")):
            findings = blog_assembly_bom_guard._check_workflow(
                {"workflow": {"stage_receipts": []}},
                artifacts,
                tmp_path,
            )
    finally:
        outside.unlink(missing_ok=True)

    assert "bom_stage_receipts_mismatch" not in {
        finding["rule_id"] for finding in findings
    }


def test_guard_rejects_context_receipt_without_sidecar_output_binding(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    scrub = bom["workflow"]["stage_receipts"][1]
    receipt = build_stage_receipt(
        run_id="run-1",
        stage="context_binding",
        tool_name="context_binding_generator",
        tool_version="1.0.0",
        started_at="2026-08-11T14:04:00Z",
        completed_at="2026-08-11T14:05:00Z",
        mutation=False,
        input_artifact_hashes={"article": bom["artifacts"]["article"]["sha256"]},
        output_artifact_hashes={"article": bom["artifacts"]["article"]["sha256"]},
        evidence_hashes={"context_binding": "e" * 64},
        previous_receipt_hash=scrub["receipt_hash"],
    )
    receipt_path = paths["stage_receipts"][2]
    write_stage_receipt(receipt_path, receipt)
    bom["artifacts"]["stage_receipts"][2]["sha256"] = hashlib.sha256(
        receipt_path.read_bytes()
    ).hexdigest()
    bom["workflow"]["stage_receipts"][2] = receipt

    assert "bom_context_binding_sidecar_unbound" in _rules(tmp_path, bom, paths)


def test_direct_import_fallback_loads_stage_receipt_validator():
    modules = Path(blog_assembly_bom_guard.__file__).resolve().parent
    command = (
        "import sys; "
        f"sys.path.insert(0, {str(modules)!r}); "
        "import blog_assembly_bom_guard as guard; "
        "print(guard.blog_assembly_stage_receipt.__name__)"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "blog_assembly_stage_receipt"


def test_bom_file_outside_explicit_workspace_is_rejected_before_read(tmp_path: Path):
    outside = tmp_path.parent / "outside-bom.json"
    outside.write_text("{}", encoding="utf-8")
    try:
        with patch.object(Path, "read_text", side_effect=AssertionError("unsafe read")):
            findings = blog_assembly_bom_guard.check_bom_file(
                outside,
                article_path=tmp_path / "article.md",
                validation_sidecar_path=tmp_path / "sidecar.md",
                workspace_root=tmp_path,
            )
    finally:
        outside.unlink(missing_ok=True)

    assert {finding["rule_id"] for finding in findings} == {"bom_path_invalid"}


def test_optimizer_evidence_without_optimization_stage_is_rejected(tmp_path: Path):
    paths = _fixture(tmp_path)
    bom = _build(tmp_path, paths)
    bom["artifacts"]["optimizer_outputs"] = [bom["artifacts"]["serp_evidence"]]

    assert "bom_optimizer_evidence_unexpected" in _rules(tmp_path, bom, paths)


def test_valid_optimized_bom_binds_prior_preflight_and_passes_guard(tmp_path: Path):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer_outputs = _prepare_optimized_workflow(tmp_path, paths)
    bom = _build(
        tmp_path,
        paths,
        optimizer_output_paths=optimizer_outputs,
        prior_preflight_readiness_path=prior_readiness,
    )

    assert _rules(
        tmp_path,
        bom,
        paths,
        expected_lifecycle_state="provisional",
    ) == set()


def test_optimized_bom_without_prior_preflight_is_blocking(tmp_path: Path):
    paths = _fixture(tmp_path)
    prior_readiness, optimizer_outputs = _prepare_optimized_workflow(tmp_path, paths)
    bom = _build(
        tmp_path,
        paths,
        optimizer_output_paths=optimizer_outputs,
        prior_preflight_readiness_path=prior_readiness,
    )
    bom["artifacts"]["prior_preflight_readiness"] = None

    assert "bom_prior_preflight_readiness_missing" in _rules(tmp_path, bom, paths)


def test_final_bom_preflight_record_must_match_bound_readiness(tmp_path: Path):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )
    final["preflight"]["verification_scope"] = "rendered_page"

    assert "bom_preflight_record_mismatch" in _rules(tmp_path, final, paths)


def test_final_bom_guard_rejects_invented_gate_pass_and_low_scores(tmp_path: Path):
    paths = _fixture(tmp_path)
    provisional = _build(tmp_path, paths)
    bom_path = tmp_path / "research" / "bom.json"
    write_blog_assembly_bom(bom_path, provisional)
    preflight = _preflight(tmp_path, bom_path, provisional)
    final = _finalize_fixture_bom(
        bom_path=bom_path,
        preflight_readiness_path=preflight,
        workspace_root=tmp_path,
    )
    readiness = json.loads(preflight.read_text(encoding="utf-8"))
    readiness["gates"][0]["passed"] = False
    readiness["gates"][0]["errors"] = 1
    readiness["score"] = 84
    preflight.write_text(json.dumps(readiness), encoding="utf-8")
    readiness_hash = hashlib.sha256(preflight.read_bytes()).hexdigest()
    final["artifacts"]["preflight_readiness"]["sha256"] = readiness_hash
    final["preflight"] = {
        "path": final["artifacts"]["preflight_readiness"]["path"],
        "sha256": readiness_hash,
        "tool": readiness["tool"],
        "verification_scope": readiness["verification_scope"],
        "gate_inventory": readiness["gate_inventory"],
        "input_hashes": readiness["input_hashes"],
    }

    rules = {
        finding["rule_id"]
        for finding in blog_assembly_bom_guard._check_preflight(
            final,
            final["artifacts"],
            tmp_path,
        )
    }

    assert "bom_preflight_gate_results_invalid" in rules
    assert "bom_preflight_scores_invalid" in rules


def test_paa_policy_requires_exact_source_shape_and_visible_question_binding(tmp_path: Path):
    paths = _fixture(tmp_path, visible_faq=True)
    bom = _build(tmp_path, paths)
    bom["paa_policy"]["source_kind"] = "serp"
    bom["paa_policy"]["selected_questions"] = []
    bom["paa_policy"]["invented"] = True

    rules = _rules(tmp_path, bom, paths)

    assert "bom_paa_policy_shape_invalid" in rules
    assert "bom_paa_source_kind_invalid" in rules
    assert "bom_paa_questions_mismatch" in rules
