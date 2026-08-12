from __future__ import annotations

from pathlib import Path

import pytest

from data_sources.modules.blog_assembly_bom import build_blog_assembly_bom_from_files
from tests.test_blog_assembly_bom import _fixture


def _kwargs(tmp_path: Path) -> dict:
    paths = _fixture(tmp_path)
    return {
        "article_path": paths["article"],
        "validation_sidecar_path": paths["sidecar"],
        "editorial_plan_path": paths["editorial_plan"],
        "serp_evidence_path": paths["serp"],
        "paa_artifact_path": paths["paa"],
        "stage_receipt_paths": paths["stage_receipts"],
        "workflow_mode": "new",
        "assembly_date": "2026-08-11",
        "workspace_root": tmp_path,
    }


@pytest.mark.parametrize(
    "field",
    ("stage_receipt_paths", "optimizer_output_paths"),
)
def test_builder_rejects_a_scalar_where_a_path_collection_is_required(
    tmp_path: Path,
    field: str,
):
    kwargs = _kwargs(tmp_path)
    kwargs[field] = "research/not-a-collection.json"

    with pytest.raises(ValueError, match=rf"{field} must be a sequence of paths"):
        build_blog_assembly_bom_from_files(**kwargs)


def test_builder_reports_the_exact_required_path_field_for_invalid_types(
    tmp_path: Path,
):
    kwargs = _kwargs(tmp_path)
    kwargs["article_path"] = 42

    with pytest.raises(ValueError, match="article_path must be a path"):
        build_blog_assembly_bom_from_files(**kwargs)
