"""Machine-review checks owned by blog assembly BOM validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


def check_machine_reviews(
    guard: Any,
    bom: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    proof_sidecar_path: str | Path | None,
    captured: Any,
) -> list[dict[str, Any]]:
    """Validate the strict plan/article review pair."""
    schema = bom.get("schema")
    reviews = bom.get("machine_reviews")
    if schema == guard["BOM_SCHEMA_V1"]:
        if reviews is not None:
            return [guard["_finding"](
                "bom_machine_reviews_unexpected",
                "BOM v1 cannot include machine_reviews.",
            )]
        return []
    if schema not in {guard["BOM_SCHEMA_V2"], guard["BOM_SCHEMA_V3"]}:
        return []
    if not isinstance(reviews, Mapping) or set(reviews) != {"plan", "article"}:
        return [guard["_finding"](
            "bom_machine_reviews_invalid",
            "BOM v2 and v3 require machine_reviews.plan and machine_reviews.article path/hash bindings.",
        )]
    if captured is not None:
        return guard["blog_assembly_bom_snapshot"].check_captured_machine_reviews(
            guard, reviews, artifacts, captured,
        )
    return _check_legacy_reviews(
        guard,
        reviews,
        artifacts,
        root,
        proof_sidecar_path=proof_sidecar_path,
    )


def _check_legacy_reviews(
    guard: Any,
    reviews: Mapping[str, Any],
    artifacts: Mapping[str, Any],
    root: Path,
    *,
    proof_sidecar_path: str | Path | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    plan_row = artifacts.get("editorial_plan")
    article_row = artifacts.get("article")
    sidecar_row = artifacts.get("validation_sidecar")
    if not all(isinstance(row, Mapping) for row in (
        plan_row, article_row, sidecar_row,
    )):
        return [guard["_finding"](
            "bom_machine_reviews_inputs_missing",
            "Machine reviews require bound article, editorial_plan, and validation_sidecar artifacts.",
        )]
    try:
        plan_path = guard["verify_artifact"](
            plan_row, workspace_root=root, field="artifacts.editorial_plan",
        )
        article_path = guard["verify_artifact"](
            article_row, workspace_root=root, field="artifacts.article",
        )
        sidecar_path = _sidecar_path(
            guard, sidecar_row, proof_sidecar_path, root,
        )
    except ValueError as error:
        return [guard["_finding"](
            "bom_machine_reviews_inputs_invalid",
            f"Machine review inputs are invalid: {error}",
        )]
    review_paths: dict[str, Path] = {}
    for phase in ("plan", "article"):
        row = reviews.get(phase)
        findings.extend(guard["_verify_row"](
            row, f"machine_reviews.{phase}", root,
        ))
        if not isinstance(row, Mapping):
            continue
        try:
            review_path = guard["verify_artifact"](
                row, workspace_root=root, field=f"machine_reviews.{phase}",
            )
        except ValueError as error:
            findings.append(guard["_finding"](
                "bom_machine_review_artifact_invalid",
                f"Machine review {phase} artifact is invalid: {error}",
            ))
            continue
        review_paths[phase] = review_path
        review_findings = guard["machine_review"].check_machine_review_file(
            review_path,
            proof_sidecar_path=sidecar_path,
            editorial_plan_path=plan_path,
            article_path=article_path,
            expected_phase=phase,
        )
        findings.extend(_wrap(guard, review_findings, "machine_review_invalid"))
    if set(review_paths) == {"plan", "article"}:
        pair_findings = guard["machine_review"].check_machine_review_pair(
            review_paths["plan"], review_paths["article"],
        )
        findings.extend(_wrap(
            guard, pair_findings, "machine_review_pair_invalid",
        ))
    return findings


def _sidecar_path(
    guard: Any,
    sidecar_row: Mapping[str, Any],
    supplied: str | Path | None,
    root: Path,
) -> Path:
    if supplied is None:
        return guard["resolve_artifact"](
            sidecar_row.get("path"), workspace_root=root,
        )
    if guard["_is_workspace_file"](supplied, root):
        return Path(supplied).resolve()
    raise ValueError("validation sidecar is not a workspace file")


def _wrap(
    guard: Any,
    findings: list[Mapping[str, Any]],
    fallback: str,
) -> list[dict[str, Any]]:
    return [
        guard["_finding"](
            str(finding.get("rule_id") or fallback),
            str(finding.get("message") or "Machine review is invalid."),
        )
        for finding in findings
    ]


__all__ = ["check_machine_reviews"]
