"""Publish-readiness result validation responsibilities."""
import hmac
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .common import (
    FINAL_READINESS_RESULT_SCHEMA,
    FINAL_RELEASE_FIELDS,
    FrontmatterError,
    GATE_RESULT_FIELDS,
    PASSED_RESULT_FIELDS,
    READINESS_RESULT_SCHEMA,
    READINESS_TOOL,
    SEO_PUBLISHING_THRESHOLD,
    SEO_TARGET_SCORE,
    _ExecutedReadinessResult,
    _sign_readiness_execution,
    context_binding_guard,
    file_sha256,
    is_json_number,
    read_publishable_markdown,
    validate_sha256,
)
from .workspace_bindings import (
    _complete_readiness_input_hashes,
    _optional_result_path,
    _resolve_workspace_input,
    _result_workspace_root,
    _same_path,
    _verify_result_inputs_unchanged,
)
from .contracts import is_registered_execution
from .gate_inventory_validation import validate_blog_gate_inventory
from .release_lifecycle import artifact_release_policy, validate_final_bom_binding


def _validate_actual_readiness_execution(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    if not isinstance(result, _ExecutedReadinessResult):
        raise ValueError(
            "passed readiness output requires an actual publish-readiness execution"
        )
    if not is_registered_execution(result):
        raise ValueError("passed readiness output must be the original execution result")
    if os.path.normcase(str(result._workspace_root)) != os.path.normcase(
        str(workspace_root.resolve())
    ):
        raise ValueError("readiness execution workspace_root changed before persistence")
    expected = _sign_readiness_execution(result)
    if not hmac.compare_digest(result._execution_signature, expected):
        raise ValueError(
            "passed readiness output changed after its actual publish-readiness execution"
        )


def _validate_result_envelope(result: Mapping[str, Any]) -> str:
    phase = result.get("phase")
    expected_fields = set(PASSED_RESULT_FIELDS)
    schema = result.get("schema")
    if schema == FINAL_READINESS_RESULT_SCHEMA:
        expected_fields.update(FINAL_RELEASE_FIELDS)
    policy = artifact_release_policy(result.get("artifact_kind"))
    if phase == "final" and policy.requires_final_bom:
        expected_fields.add("final_bom_sha256")
    if set(result) != expected_fields:
        raise ValueError("passed readiness result must use the exact result field set")
    expected = {
        "tool": READINESS_TOOL,
        "verification_scope": "source_artifact",
        "passed": True,
    }
    if schema not in {READINESS_RESULT_SCHEMA, FINAL_READINESS_RESULT_SCHEMA}:
        raise ValueError("passed readiness result uses an unsupported schema")
    if schema == FINAL_READINESS_RESULT_SCHEMA and phase != "final":
        raise ValueError("publish-readiness result v2 is reserved for final release")
    if any(result.get(key) != value for key, value in expected.items()):
        messages = {
            "tool": "passed readiness result uses the wrong readiness tool identity",
            "verification_scope": "passed readiness result must declare source_artifact verification",
            "passed": "passed readiness result must declare passed true",
        }
        key = next(key for key, value in expected.items() if result.get(key) != value)
        raise ValueError(messages[key])
    if phase not in {"preflight", "final"}:
        raise ValueError("passed readiness result phase must be preflight or final")
    return phase


def _validate_result_article(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> tuple[Any, str]:
    file_value = result.get("file")
    if not isinstance(file_value, str):
        raise ValueError("passed readiness result file must identify the current article")
    file_path = _resolve_workspace_input(
        file_value, workspace_root=workspace_root, field="readiness article"
    )
    if not file_path.is_file():
        raise ValueError("passed readiness result file must identify the current article")
    try:
        article = read_publishable_markdown(file_path)
        actual_kind = context_binding_guard.require_artifact_kind(
            article.raw, article_path=file_path
        )
    except (FrontmatterError, ValueError) as error:
        raise ValueError(f"passed readiness result article identity is invalid: {error}") from error
    if result.get("artifact_kind") != actual_kind:
        raise ValueError("passed readiness artifact_kind does not match the article")
    return article, actual_kind


def _validate_result_gates(result: Mapping[str, Any]) -> list[str]:
    gates = result.get("gates")
    inventory = result.get("gate_inventory")
    if not isinstance(gates, list) or not gates:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("passed readiness result is missing the expected gate inventory")
    names: list[str] = []
    for index, gate in enumerate(gates):
        if not isinstance(gate, Mapping) or set(gate) != GATE_RESULT_FIELDS:
            raise ValueError(f"passed readiness gate {index} has an invalid shape")
        name = gate.get("name")
        label = gate.get("label")
        if not isinstance(name, str) or not name or not isinstance(label, str) or not label:
            raise ValueError(f"passed readiness gate {index} requires a name and label")
        completed = (
            gate.get("passed") is True
            and gate.get("errors") == 0
            and isinstance(gate.get("warnings"), int)
            and not isinstance(gate.get("warnings"), bool)
            and gate.get("warnings", -1) >= 0
            and isinstance(gate.get("findings"), list)
            and gate.get("blockers") == []
        )
        if not completed:
            raise ValueError(f"passed readiness gate {name} is not a completed pass")
        names.append(name)
    if len(names) != len(set(names)) or inventory != names:
        raise ValueError("passed readiness result has an invalid gate inventory")
    return names


def _validate_blog_gate_inventory(
    result: Mapping[str, Any],
    *,
    article: Any,
    artifact_kind: str,
    phase: str,
    names: Sequence[str],
    workspace_root: Path,
) -> None:
    validate_blog_gate_inventory(
        result,
        article=article,
        artifact_kind=artifact_kind,
        phase=phase,
        names=names,
        workspace_root=workspace_root,
        resolve_workspace_input=_resolve_workspace_input,
    )


def _validate_result_scores(result: Mapping[str, Any], artifact_kind: str) -> None:
    score = result.get("score")
    threshold = result.get("score_threshold")
    expected = 75 if artifact_kind == "landing_page" else 85
    if not _is_number(score) or threshold != expected or float(score) < expected:
        raise ValueError("passed readiness result does not meet its content score threshold")
    aeo_geo = result.get("aeo_geo")
    if not isinstance(aeo_geo, Mapping):
        raise ValueError("passed readiness result requires an AEO/GEO result")
    blog_passed = (
        _is_number(aeo_geo.get("score"))
        and aeo_geo.get("threshold") == 90
        and aeo_geo.get("passed") is True
        and float(aeo_geo["score"]) >= 90
    )
    if artifact_kind == "blog" and not blog_passed:
        raise ValueError("passed blog readiness does not meet the AEO/GEO threshold")
    if artifact_kind != "blog" and aeo_geo.get("passed") is not True:
        raise ValueError("passed readiness result contains a failed AEO/GEO result")
    _validate_passed_scorecard(result, artifact_kind=artifact_kind)
    if not isinstance(result.get("priority_fixes"), list):
        raise ValueError("passed readiness priority_fixes must be a list")
    if not isinstance(result.get("run_id"), str) or not str(result["run_id"]).strip():
        raise ValueError("passed readiness result requires a run_id")


def _validate_complete_input_inventory(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    expected = _complete_readiness_input_hashes(
        article=str(result["file"]),
        validation_sidecar=_optional_result_path(result, "proof_sidecar"),
        context_request=_optional_result_path(result, "context_request"),
        context_pack=_optional_result_path(result, "context_pack"),
        context_receipt=_optional_result_path(result, "context_receipt"),
        assembly_bom=_optional_result_path(result, "assembly_bom"),
        workspace_root=workspace_root,
    )
    if result.get("input_hashes") != expected:
        raise ValueError(
            "passed readiness result must bind the complete exact readiness input inventory"
        )


def _validate_release_manifest_binding(
    result: Mapping[str, Any],
    *,
    workspace_root: Path,
) -> None:
    if result.get("schema") != FINAL_READINESS_RESULT_SCHEMA:
        return
    manifest = result.get("release_manifest")
    digest = result.get("release_manifest_sha256")
    if not isinstance(manifest, str) or not manifest:
        raise ValueError("final release readiness requires a release manifest")
    validate_sha256(digest, field="release_manifest_sha256")
    path = _resolve_workspace_input(
        manifest,
        workspace_root=workspace_root,
        field="release_manifest",
    )
    if file_sha256(path) != digest:
        raise ValueError("final release manifest hash does not match")


def validate_passed_readiness_result(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Reject caller-invented pass payloads at both structural and live boundaries."""
    validate_passed_readiness_structure(result, workspace_root=workspace_root)
    verify_passed_readiness_inputs(result, workspace_root=workspace_root)


def validate_passed_readiness_structure(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Validate the result envelope without reading any input artifact."""
    phase = _validate_result_envelope(result)
    root = _result_workspace_root(result, workspace_root)
    artifact_kind = artifact_release_policy(result.get("artifact_kind")).artifact_kind
    _validate_result_gates(result)
    _validate_result_scores(result, artifact_kind)
    _validate_input_inventory_shape(result)
    if phase == "final":
        rows = result.get("input_hashes")
        if not isinstance(rows, Mapping):
            raise ValueError("passed readiness result requires input_hashes")
        validate_final_bom_binding(result, rows)
    _verify_result_path_bindings(result, workspace_root=root)


def verify_passed_readiness_inputs(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path | None = None,
) -> None:
    """Verify the result against current files after structural validation."""
    validate_passed_readiness_structure(result, workspace_root=workspace_root)
    root = _result_workspace_root(result, workspace_root)
    article, artifact_kind = _validate_result_article(result, workspace_root=root)
    phase = str(result.get("phase"))
    names = [str(gate.get("name")) for gate in result["gates"]]
    _validate_blog_gate_inventory(
        result,
        article=article,
        artifact_kind=artifact_kind,
        phase=phase,
        names=names,
        workspace_root=root,
    )
    _verify_result_inputs_unchanged(result, workspace_root=root)
    _validate_complete_input_inventory(result, workspace_root=root)
    _validate_release_manifest_binding(result, workspace_root=root)


def _validate_input_inventory_shape(result: Mapping[str, Any]) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping) or not rows:
        raise ValueError("passed readiness result requires input_hashes")
    for label, row in rows.items():
        if not isinstance(label, str) or not label:
            raise ValueError("readiness input labels must be non-empty strings")
        if not isinstance(row, Mapping) or set(row) != {"path", "sha256"}:
            raise ValueError(f"readiness input {label} must contain only path and sha256")
        if not isinstance(row.get("path"), str) or not row["path"]:
            raise ValueError(f"readiness input {label} path is invalid")
        validate_sha256(row.get("sha256"), field=f"input_hashes.{label}.sha256")

def _validate_passed_scorecard(
    result: Mapping[str, Any],
    *,
    artifact_kind: str,
) -> None:
    scorecard = result.get("scorecard")
    if not isinstance(scorecard, Mapping):
        raise ValueError("passed readiness result requires a scorecard")
    expected_fields = {"passed", "content_quality", "seo_quality", "aeo_geo"}
    if set(scorecard) != expected_fields:
        raise ValueError("passed readiness scorecard has an invalid shape")
    if scorecard.get("passed") is not True:
        raise ValueError("passed readiness scorecard is not a completed pass")

    expected_content_threshold = 75 if artifact_kind == "landing_page" else 85
    content_gate = _validate_scorecard_gate(
        scorecard,
        "content_quality",
        "content quality",
        expected_threshold=expected_content_threshold,
        require_numeric_score=True,
    )
    if not _same_number(content_gate.get("score"), result.get("score")):
        raise ValueError("passed readiness scorecard content score does not match the result")
    if content_gate.get("threshold") != result.get("score_threshold"):
        raise ValueError("passed readiness scorecard content threshold does not match the result")

    _validate_seo_scorecard(scorecard)
    _validate_aeo_scorecard(scorecard, result=result, artifact_kind=artifact_kind)


def _validate_seo_scorecard(scorecard: Mapping[str, Any]) -> None:
    gate = _scorecard_gate(scorecard, "seo_quality")
    if gate.get("not_applicable") is True:
        if gate.get("passed") is not True:
            raise ValueError("passed readiness scorecard SEO gate is not a pass")
    else:
        _validate_scorecard_gate(
            scorecard, "seo_quality", "SEO",
            expected_threshold=SEO_PUBLISHING_THRESHOLD,
            require_numeric_score=True,
        )
        target_fields = any(
            field in gate for field in ("target", "target_met", "target_status")
        )
        if target_fields and gate.get("target") != SEO_TARGET_SCORE:
            raise ValueError("passed readiness scorecard SEO gate has an invalid target")
        if target_fields and not isinstance(gate.get("target_met"), bool):
            raise ValueError("passed readiness scorecard SEO gate has an invalid target status")
        if target_fields and gate.get("target_status") not in {"met", "below_target"}:
            raise ValueError("passed readiness scorecard SEO gate has an invalid target status")
    issue_count = gate.get("critical_issue_count")
    if not isinstance(issue_count, int) or isinstance(issue_count, bool) or issue_count != 0:
        raise ValueError("passed readiness scorecard SEO gate has critical issues")
    issues = gate.get("critical_issues", [])
    if not isinstance(issues, list) or issues:
        raise ValueError("passed readiness scorecard SEO gate has critical issues")


def _validate_aeo_scorecard(
    scorecard: Mapping[str, Any],
    *,
    result: Mapping[str, Any],
    artifact_kind: str,
) -> None:
    aeo_gate = _scorecard_gate(scorecard, "aeo_geo")
    aeo_not_applicable = aeo_gate.get("not_applicable") is True
    if aeo_not_applicable and artifact_kind != "blog":
        if aeo_gate.get("passed") is not True:
            raise ValueError("passed readiness scorecard AEO/GEO gate is not a pass")
    else:
        _validate_scorecard_gate(
            scorecard,
            "aeo_geo",
            "AEO/GEO",
            expected_threshold=90 if artifact_kind == "blog" else None,
            require_numeric_score=True,
        )
        aeo_geo = result.get("aeo_geo")
        if not isinstance(aeo_geo, Mapping):
            raise ValueError("passed readiness result requires an AEO/GEO result")
        if not _same_number(aeo_gate.get("score"), aeo_geo.get("score")):
            raise ValueError("passed readiness scorecard AEO/GEO score does not match the result")
        if aeo_gate.get("threshold") != aeo_geo.get("threshold"):
            raise ValueError("passed readiness scorecard AEO/GEO threshold does not match the result")
        if aeo_gate.get("passed") != aeo_geo.get("passed"):
            raise ValueError("passed readiness scorecard AEO/GEO status does not match the result")

def _validate_scorecard_gate(
    scorecard: Mapping[str, Any],
    gate_name: str,
    label: str,
    *,
    expected_threshold: int | None,
    require_numeric_score: bool,
) -> Mapping[str, Any]:
    gate = scorecard.get(gate_name)
    if not isinstance(gate, Mapping):
        raise ValueError(f"passed readiness scorecard is missing the {label} gate")
    score = gate.get("score")
    threshold = gate.get("threshold")
    if expected_threshold is not None and threshold != expected_threshold:
        raise ValueError(f"passed readiness scorecard {label} threshold is invalid")
    if require_numeric_score and (not _is_number(score) or not _is_number(threshold)):
        raise ValueError(f"passed readiness scorecard {label} gate is missing a numeric score")
    if gate.get("passed") is not True:
        raise ValueError(f"passed readiness scorecard {label} gate is not a pass")
    if _is_number(score) and _is_number(threshold) and float(score) < float(threshold):
        raise ValueError(f"passed readiness scorecard {label} gate is below threshold")
    return gate

def _scorecard_gate(scorecard: Any, gate_name: str) -> Mapping[str, Any]:
    if not isinstance(scorecard, Mapping):
        return {}
    gate = scorecard.get(gate_name)
    if not isinstance(gate, Mapping):
        return {}
    return gate

def _same_number(left: Any, right: Any) -> bool:
    return _is_number(left) and _is_number(right) and float(left) == float(right)

def _verify_result_path_bindings(
    result: Mapping[str, Any],
    *,
    workspace_root: str | Path,
) -> None:
    rows = result.get("input_hashes")
    if not isinstance(rows, Mapping):
        raise ValueError("passed readiness result requires input_hashes")
    root = Path(workspace_root).resolve()
    bindings = {
        "article": "file",
        "validation_sidecar": "proof_sidecar",
        "context_request": "context_request",
        "context_pack": "context_pack",
        "context_receipt": "context_receipt",
        "assembly_bom": "assembly_bom",
    }
    for label, field in bindings.items():
        declared = result.get(field)
        row = rows.get(label)
        if declared is None:
            if row is not None:
                raise ValueError(f"readiness input {label} is not bound to {field}")
            continue
        if not isinstance(declared, str) or not isinstance(row, Mapping):
            raise ValueError(f"readiness input {label} is missing its path binding")
        stored = row.get("path")
        if not isinstance(stored, str):
            raise ValueError(f"readiness input {label} has an invalid path binding")
        try:
            bound_path = _lexical_workspace_path(declared, root)
            stored_path = _lexical_workspace_path(stored, root)
        except ValueError as error:
            raise ValueError(f"readiness input {label} has an invalid path binding") from error
        if not _same_path(bound_path, stored_path):
            raise ValueError(f"readiness input {label} does not match its declared path")


def _lexical_workspace_path(value: str, root: Path) -> Path:
    """Normalize a binding without consulting the filesystem."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path is required")
    raw = os.path.abspath(value if os.path.isabs(value) else os.path.join(root, value))
    try:
        common = os.path.commonpath((str(root), raw))
    except ValueError as error:
        raise ValueError("path is outside workspace") from error
    if os.path.normcase(common) != os.path.normcase(str(root)):
        raise ValueError("path is outside workspace")
    return Path(raw)

def _is_number(value: Any) -> bool:
    return is_json_number(value)


__all__ = [
    '_is_number',
    '_same_number',
    '_scorecard_gate',
    '_validate_actual_readiness_execution',
    '_validate_passed_scorecard',
    '_validate_scorecard_gate',
    '_verify_result_path_bindings',
    'validate_passed_readiness_result',
    'validate_passed_readiness_structure',
    'verify_passed_readiness_inputs',
]
