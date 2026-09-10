"""Shared dependencies for content-scoring implementation mixins."""
# ruff: noqa: F401

from __future__ import annotations

import html
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from data_sources.modules.aeo_geo_rater import rate_aeo_geo as _rate_aeo_geo
from data_sources.modules.ai_copy_linter import lint_content as _lint_content
from data_sources.modules.customer_proof_diversity_guard import check_content as _check_customer_proof_diversity
from data_sources.modules.frontmatter import split_frontmatter as _split_frontmatter
from data_sources.modules.metric_proof_pack_guard import check_content as _check_metric_proof_pack
from data_sources.modules.proof_sidecar import load_sidecar_content as _load_sidecar_content
from data_sources.modules.proof_sidecar import resolve_sidecar_path as _resolve_sidecar_path
from data_sources.modules.readability_scorer import ReadabilityScorer as _ReadabilityScorer
from data_sources.modules.readiness_gate_context import trusted_readiness_findings as _trusted_readiness_findings
from data_sources.modules.review_story_identity_guard import check_content as _check_review_story_identity
from data_sources.modules.seo_quality_rater import PUBLISHING_THRESHOLD as SEO_PUBLISHING_THRESHOLD
from data_sources.modules.seo_quality_rater import SEO_TARGET_SCORE
from data_sources.modules.seo_quality_rater import SEOQualityRater as _SEOQualityRater
from data_sources.modules.source_support_guard import check_content as _check_source_support
from data_sources.modules.url_validator import validate_content_urls as _validate_content_urls


_DEFAULTS = {
    "ReadabilityScorer": _ReadabilityScorer,
    "SEOQualityRater": _SEOQualityRater,
    "rate_aeo_geo": _rate_aeo_geo,
    "lint_content": _lint_content,
    "check_customer_proof_diversity": _check_customer_proof_diversity,
    "split_frontmatter": _split_frontmatter,
    "check_metric_proof_pack": _check_metric_proof_pack,
    "load_sidecar_content": _load_sidecar_content,
    "resolve_sidecar_path": _resolve_sidecar_path,
    "trusted_readiness_findings": _trusted_readiness_findings,
    "check_review_story_identity": _check_review_story_identity,
    "check_source_support": _check_source_support,
    "validate_content_urls": _validate_content_urls,
}


def _dependency(name: str):
    facade = sys.modules.get("data_sources.modules.content_scorer")
    return getattr(facade, name, _DEFAULTS[name])


def ReadabilityScorer(*args: Any, **kwargs: Any):
    return _dependency("ReadabilityScorer")(*args, **kwargs)


def SEOQualityRater(*args: Any, **kwargs: Any):
    return _dependency("SEOQualityRater")(*args, **kwargs)


def rate_aeo_geo(*args: Any, **kwargs: Any):
    return _dependency("rate_aeo_geo")(*args, **kwargs)


def lint_content(*args: Any, **kwargs: Any):
    return _dependency("lint_content")(*args, **kwargs)


def check_customer_proof_diversity(*args: Any, **kwargs: Any):
    return _dependency("check_customer_proof_diversity")(*args, **kwargs)


def split_frontmatter(*args: Any, **kwargs: Any):
    return _dependency("split_frontmatter")(*args, **kwargs)


def check_metric_proof_pack(*args: Any, **kwargs: Any):
    return _dependency("check_metric_proof_pack")(*args, **kwargs)


def load_sidecar_content(*args: Any, **kwargs: Any):
    return _dependency("load_sidecar_content")(*args, **kwargs)


def resolve_sidecar_path(*args: Any, **kwargs: Any):
    return _dependency("resolve_sidecar_path")(*args, **kwargs)


def trusted_readiness_findings(*args: Any, **kwargs: Any):
    return _dependency("trusted_readiness_findings")(*args, **kwargs)


def check_review_story_identity(*args: Any, **kwargs: Any):
    return _dependency("check_review_story_identity")(*args, **kwargs)


def check_source_support(*args: Any, **kwargs: Any):
    return _dependency("check_source_support")(*args, **kwargs)


def validate_content_urls(*args: Any, **kwargs: Any):
    return _dependency("validate_content_urls")(*args, **kwargs)


def _copy_prevalidated_findings(
    findings_by_gate: Optional[Mapping[str, Sequence[Mapping[str, Any]]]],
    gate_name: str,
) -> Optional[List[Dict[str, Any]]]:
    if findings_by_gate is None or gate_name not in findings_by_gate:
        return None
    raw_findings = findings_by_gate[gate_name]
    if isinstance(raw_findings, (str, bytes)) or not isinstance(raw_findings, Sequence):
        raise TypeError(f"prevalidated findings for {gate_name!r} must be a sequence")
    copied: List[Dict[str, Any]] = []
    for index, finding in enumerate(raw_findings):
        if not isinstance(finding, Mapping):
            raise TypeError(f"prevalidated finding {gate_name}[{index}] must be a mapping")
        copied.append(dict(finding))
    return copied


__all__ = [name for name in globals() if not name.startswith("__")]
