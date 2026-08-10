from __future__ import annotations

from datetime import date

import pytest

from data_sources.modules.dataforseo import DataForSEO
from data_sources.modules.domain_identity import hostnames_equal, normalize_hostname
from scripts.seo_bofu_rankings import find_domain_ranking
from scripts.seo_competitor_analysis import collect_competitor_rankings


def test_hostname_identity_rejects_lookalikes_and_accepts_equivalent_hosts():
    assert normalize_hostname("https://WWW.Simpro.com./path") == "simpro.com"
    assert hostnames_equal("simpro.com", "www.simpro.com")
    assert not hostnames_equal("simpro.com", "notsimpro.com")
    assert not hostnames_equal("simpro.com", "simpro.com.example.org")


def test_bofu_consumer_does_not_report_lookalike_domain_as_owned_ranking():
    results = [
        {"domain": "notsimpro.com", "position": 1, "url": "https://notsimpro.com"},
        {"domain": "www.simpro.com", "position": 7, "url": "https://simpro.com"},
    ]

    assert find_domain_ranking(results, "https://simpro.com/") == results[1]


def test_competitor_consumer_assigns_only_exact_hostnames():
    results = [
        {"domain": "notcompetitor.com", "position": 1},
        {"domain": "www.competitor.com", "position": 4},
        {"domain": "example.com", "position": 6},
    ]

    assert collect_competitor_rankings(
        results,
        {"competitor.com": "Competitor", "www.example.com": "Owned"},
    ) == {"Competitor": 4, "Owned": 6}


def _history_client(payloads):
    client = object.__new__(DataForSEO)

    def post(endpoint, data):
        payloads.append((endpoint, data))
        return {
            "status_code": 20000,
            "tasks": [{"status_code": 20000, "result": [{"items": []}]}],
        }

    client._post = post
    return client


def test_ranking_history_month_window_changes_api_payload(monkeypatch):
    payloads = []
    client = _history_client(payloads)
    monkeypatch.setattr(
        "data_sources.modules.dataforseo._today",
        lambda: date(2026, 8, 10),
    )

    client.check_ranking_history("example.com", "field service", months_back=1)
    client.check_ranking_history("example.com", "field service", months_back=12)

    one_month = payloads[0][1][0]
    twelve_months = payloads[1][1][0]
    assert one_month["date_to"] == twelve_months["date_to"] == "2026-08-10"
    assert one_month["date_from"] == "2026-07-10"
    assert twelve_months["date_from"] == "2025-08-10"


@pytest.mark.parametrize("months_back", [0, -1, True, 1.5])
def test_ranking_history_rejects_invalid_month_windows(months_back):
    client = object.__new__(DataForSEO)
    client._post = lambda *args, **kwargs: pytest.fail("request should not be sent")

    with pytest.raises(ValueError, match="months_back"):
        client.check_ranking_history("example.com", "field service", months_back)


def test_ranking_history_does_not_turn_dependency_failure_into_empty_history():
    client = object.__new__(DataForSEO)
    client._post = lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("upstream unavailable")
    )

    with pytest.raises(RuntimeError, match="upstream unavailable"):
        client.check_ranking_history("example.com", "field service")


def test_ranking_history_does_not_swallow_cancellation():
    client = object.__new__(DataForSEO)
    client._post = lambda *args, **kwargs: (_ for _ in ()).throw(
        KeyboardInterrupt("cancelled")
    )

    with pytest.raises(KeyboardInterrupt, match="cancelled"):
        client.check_ranking_history("example.com", "field service")
