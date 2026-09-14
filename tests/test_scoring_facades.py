from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock

import pytest

from data_sources.modules import aeo_geo_rater, content_scorer, seo_quality_rater
from data_sources.modules.content_scoring.aeo_orchestration import rate_aeo_geo
from data_sources.modules.content_scoring.aeo_metadata_schema import (
    CANONICAL_SCHEMA_ENTITIES,
)
from data_sources.modules.content_scoring.common import ScoringDependencies
from data_sources.modules.content_scoring.scorer import ContentScorer
from data_sources.modules.content_scoring.seo_rater_orchestration import SEOQualityRater


ROOT = Path(__file__).resolve().parents[1]


def _dependencies() -> ScoringDependencies:
    noop = Mock(return_value=[])
    return ScoringDependencies(
        readability_scorer_factory=Mock(return_value=object()),
        seo_rater_factory=Mock(return_value=object()),
        rate_aeo_geo=Mock(return_value={"passed": True, "checks": {}}),
        lint_content=noop,
        check_customer_proof_diversity=noop,
        split_frontmatter=Mock(return_value=({}, "", 1)),
        check_metric_proof_pack=noop,
        load_sidecar_content=Mock(return_value=""),
        resolve_sidecar_path=Mock(return_value=None),
        trusted_readiness_findings=Mock(return_value=None),
        check_review_story_identity=noop,
        check_source_support=noop,
        validate_content_urls=Mock(),
    )


def test_scoring_dependencies_are_frozen_and_factories_are_injected() -> None:
    dependencies = _dependencies()

    scorer = ContentScorer(dependencies=dependencies)

    assert scorer.dependencies is dependencies
    dependencies.readability_scorer_factory.assert_called_once_with()
    dependencies.seo_rater_factory.assert_called_once_with()
    with pytest.raises(FrozenInstanceError):
        dependencies.rate_aeo_geo = Mock()  # type: ignore[misc]


def test_facades_preserve_canonical_public_objects() -> None:
    assert content_scorer.ContentScorer is ContentScorer
    assert aeo_geo_rater.rate_aeo_geo is rate_aeo_geo
    assert aeo_geo_rater.CANONICAL_SCHEMA_ENTITIES is CANONICAL_SCHEMA_ENTITIES
    assert seo_quality_rater.SEOQualityRater is SEOQualityRater
    assert seo_quality_rater.PUBLISHING_THRESHOLD == 90
    assert seo_quality_rater.SEO_TARGET_SCORE == 95


def test_importing_content_scorer_facade_keeps_heavy_readability_lazy() -> None:
    script = (
        "import json,sys; import data_sources.modules.content_scorer; "
        "print(json.dumps([name for name in "
        "('data_sources.modules.readability_scorer','textstat') "
        "if name in sys.modules]))"
    )

    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []


def test_lazy_readability_facade_resolves_the_canonical_class() -> None:
    from data_sources.modules.readability_scorer import ReadabilityScorer

    assert content_scorer.ReadabilityScorer is ReadabilityScorer


def test_common_has_no_wildcard_or_sys_modules_dependency_proxy() -> None:
    source = (ROOT / "data_sources" / "modules" / "content_scoring" / "common.py").read_text(
        encoding="utf-8"
    )

    assert "import *" not in source
    assert "sys.modules" not in source
