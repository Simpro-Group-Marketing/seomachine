"""Simpro AU defaults to the Semrush Australia database."""

from __future__ import annotations

import pytest
from data_sources.modules import semrush_keyword_decision_guard as guard


@pytest.mark.parametrize("market", ["AU", "au", "Australia"])
def test_simpro_au_defaults_to_au_database(market):
    assert guard.default_databases_for_brand_market("Simpro", market) == ("au",)


def test_simpro_us_default_is_unchanged():
    assert guard.default_databases_for_brand_market("Simpro", "US") == ("us",)
