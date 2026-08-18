"""Opt-in live checks for the paid DataForSEO API contract.

Run explicitly with valid credentials:
RUN_DATAFORSEO_LIVE_CANARY=1 python -m pytest tests/test_dataforseo_live_canary.py -q
"""

from __future__ import annotations

import os

import pytest

from data_sources.modules.dataforseo import DataForSEO


LIVE_ENABLED = os.getenv("RUN_DATAFORSEO_LIVE_CANARY") == "1"
HAS_CREDENTIALS = bool(
    os.getenv("DATAFORSEO_LOGIN") and os.getenv("DATAFORSEO_PASSWORD")
)
pytestmark = pytest.mark.skipif(
    not (LIVE_ENABLED and HAS_CREDENTIALS),
    reason=(
        "paid live canary requires RUN_DATAFORSEO_LIVE_CANARY=1 plus "
        "DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD"
    ),
)


def test_live_google_domain_rank_overview_contract():
    result = DataForSEO().get_domain_metrics("dataforseo.com")

    assert result["domain"] == "dataforseo.com"
    assert result["location_code"] == 2840
    assert result["language_code"] == "en"
    assert result["organic_keywords"] is None or isinstance(
        result["organic_keywords"], int
    )
    assert result["organic_traffic"] is None or isinstance(
        result["organic_traffic"], (int, float)
    )
    assert isinstance(result["organic_position_distribution"], dict)
    assert isinstance(result["organic_movement"], dict)


def test_live_google_historical_serps_contract():
    history = DataForSEO().check_ranking_history(
        "dataforseo.com",
        "dataforseo",
        months_back=1,
    )

    assert isinstance(history, list)
    for row in history:
        assert row["keyword"] == "dataforseo"
        assert row["domain"] == "dataforseo.com"
        assert isinstance(row["datetime"], str)
        assert row["position"] is None or isinstance(row["position"], int)
        assert isinstance(row["ranking"], bool)
