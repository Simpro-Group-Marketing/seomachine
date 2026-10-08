"""serp_capture re-exports the shared SERP helpers instead of redefining them."""

import ast
from pathlib import Path

import pytest

from data_sources.modules.editorial_plan import serp_capture, serp_raw

SHARED_HELPERS = (
    "load_json_text",
    "_artifact_workspace_root",
    "_load_valid_serp_raw_capture",
    "load_normalized_serp_raw_capture",
    "_validate_serp_raw_snapshot",
    "_validated_capture_payload",
    "_validate_capture_identity",
    "_validate_capture_request",
    "_dataforseo_request_valid",
    "_semrush_request_valid",
    "_playwright_request_valid",
    "_normalize_serp_raw_response",
    "_decode_playwright_response",
    "_normalize_dataforseo_response",
    "_normalize_dataforseo_items",
    "_validate_normalized_response",
    "_unique_strings",
    "_serp_content_type",
)


@pytest.mark.parametrize("name", SHARED_HELPERS)
def test_serp_capture_reuses_the_serp_raw_helper(name):
    assert getattr(serp_capture, name) is getattr(serp_raw, name)


@pytest.mark.parametrize("name", SHARED_HELPERS)
def test_serp_capture_exports_the_shared_helper(name):
    assert name in serp_capture.__all__


def test_serp_capture_defines_only_its_own_functions():
    source = Path(serp_capture.__file__).read_text(encoding="utf-8")
    defined = {
        node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)
    }
    assert defined == {"build_serp_evidence"}
