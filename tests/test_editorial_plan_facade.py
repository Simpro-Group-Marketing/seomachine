from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from data_sources.modules import editorial_plan_guard
from data_sources.modules.editorial_plan.dependencies import default_editorial_plan_dependencies
from data_sources.modules.editorial_plan.orchestration import check_file
from data_sources.modules.editorial_plan.plan_validation import check_plan
from tests.test_editorial_plan_guard import article_plan


ROOT = Path(__file__).resolve().parents[1]


def test_editorial_plan_dependencies_are_frozen_and_injected() -> None:
    resolver = Mock(return_value={"required": False})
    dependencies = replace(
        default_editorial_plan_dependencies(),
        resolve_required_industry_policy=resolver,
    )

    assert check_plan(article_plan(), dependencies=dependencies) == []
    resolver.assert_called()
    with pytest.raises(FrozenInstanceError):
        dependencies.split_frontmatter = Mock()  # type: ignore[misc]


def test_facade_exports_canonical_public_functions() -> None:
    assert editorial_plan_guard.check_plan is check_plan
    assert editorial_plan_guard.check_file is check_file


def test_check_file_reads_the_plan_snapshot_once_through_dependencies(
    tmp_path: Path,
) -> None:
    loader = Mock(return_value=SimpleNamespace(payload=article_plan()))
    dependencies = replace(
        default_editorial_plan_dependencies(),
        load_json_object_snapshot=loader,
    )

    assert check_file(tmp_path / "plan.json", dependencies=dependencies) == []
    loader.assert_called_once_with(tmp_path / "plan.json", field="editorial plan")


def test_facade_and_package_avoid_dynamic_module_dispatch() -> None:
    sources = [
        ROOT / "data_sources" / "modules" / "editorial_plan_guard.py",
        *sorted((ROOT / "data_sources" / "modules" / "editorial_plan").glob("*.py")),
    ]

    for path in sources:
        source = path.read_text(encoding="utf-8")
        assert "sys.modules" not in source
        assert "import *" not in source
