"""Contracts responsibilities."""
# ruff: noqa: F403, F405

from .common import *  # noqa: F403


def _label_paths(values: Sequence[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("agent output arguments must use id=path")
        label, raw_path = value.split("=", 1)
        normalized = _required_string(label, "agent_output.id")
        if normalized in result:
            raise ValueError(f"duplicate agent output ID: {normalized}")
        result[normalized] = Path(_required_string(raw_path, "agent_output.path"))
    return result

def _is_supported_bom_schema(value: Any) -> bool:
    return value in ARCHIVED_BOM_SCHEMAS

def _machine_review_bindings(
    *,
    plan_review_path: str | Path | None,
    article_review_path: str | Path | None,
    editorial_plan_path: str | Path,
    article_path: str | Path,
    proof_sidecar_path: str | Path,
    workspace_root: Path,
    expected_run_id: str | None = None,
) -> dict[str, dict[str, str]]:
    if plan_review_path is None and article_review_path is None:
        raise ValueError(
            "New BOM assembly requires both plan_review_path and article_review_path; "
            "BOM v1 is read-only archived evidence."
        )
    if plan_review_path is None or article_review_path is None:
        raise ValueError(
            "BOM v2 requires both plan_review_path and article_review_path"
        )
    for phase, review_path in (
        ("plan", plan_review_path),
        ("article", article_review_path),
    ):
        findings = machine_review.check_machine_review_file(
            review_path,
            proof_sidecar_path=proof_sidecar_path,
            editorial_plan_path=editorial_plan_path,
            article_path=article_path,
            expected_phase=phase,
        )
        if findings:
            rule_ids = ", ".join(
                sorted({str(finding.get("rule_id") or "") for finding in findings})
            )
            raise ValueError(f"{phase} machine review is invalid: {rule_ids}")
    pair_findings = machine_review.check_machine_review_pair(
        plan_review_path,
        article_review_path,
        expected_run_id=expected_run_id,
    )
    if pair_findings:
        rule_ids = ", ".join(
            sorted({str(finding.get("rule_id") or "") for finding in pair_findings})
        )
        raise ValueError(f"machine review pair is invalid: {rule_ids}")
    return {
        "plan": canonical_artifact(plan_review_path, workspace_root=workspace_root),
        "article": canonical_artifact(article_review_path, workspace_root=workspace_root),
    }

def _optional_json_schema(path: str | Path | None) -> str:
    if path is None:
        return ""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"customer proof evidence is invalid: {error}") from error
    if not isinstance(payload, Mapping):
        raise ValueError("customer proof evidence must be a JSON object")
    return str(payload.get("schema") or "")

def _read_json_object(path: str | Path, field: str) -> dict[str, Any]:
    try:
        return load_json_object_snapshot(path, field=field).payload
    except ValueError as error:
        raise ValueError(f"{field} must be a readable JSON object: {error}") from error

def _required_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value

def _required_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    if value.strip().casefold() in PLACEHOLDER_VALUES:
        raise ValueError(f"{field} cannot be a placeholder")
    return value.strip()

def _validate_input_path(value: Any, *, field: str) -> str | Path:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        raise ValueError(f"{field} must be a path")
    return value

def _validate_path_sequence(value: Any, *, field: str) -> tuple[str | Path, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{field} must be a sequence of paths")
    normalized: list[str | Path] = []
    for index, item in enumerate(value):
        try:
            normalized.append(_validate_input_path(item, field=f"{field}[{index}]"))
        except ValueError as error:
            raise ValueError(f"{field} must be a sequence of paths: {error}") from error
    return tuple(normalized)

def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]

def _required_enum(value: Any, field: str, allowed: frozenset[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{field} must be one of: {', '.join(sorted(allowed))}")
    return value

def _iso_date(value: Any, field: str) -> date:
    return validate_current_assembly_date(value, field=field)

def _required_article_scalar(article: PublishableMarkdown, field: str) -> str:
    return _required_string(article.scalar(field), f"article.{field}")

def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())

def _is_number(value: Any) -> bool:
    return is_json_number(value)

def _visible_faq_questions(content: str) -> list[str]:
    structure = detect_faq_structure(content)
    if structure.unsupported_lines:
        raise ValueError(
            "FAQ-like details or bold-question markup is unsupported; use a recognized FAQ H2 with question headings"
        )
    return [entry.question for entry in structure.entries]

def _has_video_embed(content: str) -> bool:
    return inspect_video_embeds(content).has_supported_embed


__all__ = ['_has_video_embed', '_is_number', '_is_supported_bom_schema', '_iso_date', '_label_paths', '_machine_review_bindings', '_nonempty', '_optional_json_schema', '_read_json_object', '_required_article_scalar', '_required_enum', '_required_mapping', '_required_string', '_string_list', '_validate_input_path', '_validate_path_sequence', '_visible_faq_questions']
