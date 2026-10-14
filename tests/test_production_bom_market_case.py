"""Spec market and keyword decision agree regardless of letter case."""

from __future__ import annotations

from data_sources.modules.production.bom_artifacts import _market_errors


def test_market_and_database_compare_case_insensitively():
    assert _market_errors({"market": "au", "database": "AU"}, "AU") == []
    assert _market_errors({"market": "AU", "database": "au"}, "au") == []


def test_a_different_market_or_database_still_refuses():
    assert _market_errors({"market": "US", "database": "us"}, "AU")
    assert _market_errors({"market": "AU", "database": "us"}, "AU")
