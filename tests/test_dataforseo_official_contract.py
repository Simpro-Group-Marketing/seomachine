from __future__ import annotations

from datetime import date

import pytest

from data_sources.modules.dataforseo import (
    DataForSEO,
    DataForSEOAvailabilityError,
    DataForSEOContractError,
)


def _successful_response(result):
    return {
        "version": "0.1.20220216",
        "status_code": 20000,
        "status_message": "Ok.",
        "tasks_count": 1,
        "tasks_error": 0,
        "tasks": [
            {
                "status_code": 20000,
                "status_message": "Ok.",
                "result_count": 1,
                "result": [result],
            }
        ],
    }


def test_domain_metrics_uses_google_domain_rank_overview_documented_contract():
    calls = []
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: (
        calls.append((endpoint, data))
        or _successful_response(
            {
                "se_type": "google",
                "target": "simpro.com",
                "location_code": 2840,
                "language_code": "en",
                "total_count": 1,
                "items_count": 1,
                "items": [
                    {
                        "se_type": "google",
                        "location_code": 2840,
                        "language_code": "en",
                        "metrics": {
                            "organic": {
                                "pos_1": 11,
                                "pos_2_3": 28,
                                "pos_4_10": 100,
                                "pos_11_20": 135,
                                "pos_21_30": 157,
                                "pos_31_40": 174,
                                "pos_41_50": 203,
                                "pos_51_60": 220,
                                "pos_61_70": 232,
                                "pos_71_80": 202,
                                "pos_81_90": 200,
                                "pos_91_100": 126,
                                "etv": 3055.741419672966,
                                "count": 1788,
                                "estimated_paid_traffic_cost": 15078.99657046888,
                                "is_new": 661,
                                "is_up": 757,
                                "is_down": 418,
                                "is_lost": 547,
                            }
                        },
                    }
                ],
            }
        )
    )

    result = client.get_domain_metrics("https://WWW.Simpro.com/path")

    assert calls == [
        (
            "/v3/dataforseo_labs/google/domain_rank_overview/live",
            [
                {
                    "target": "simpro.com",
                    "location_code": 2840,
                    "language_code": "en",
                }
            ],
        )
    ]
    assert result == {
        "domain": "simpro.com",
        "location_code": 2840,
        "language_code": "en",
        "organic_keywords": 1788,
        "organic_traffic": 3055.741419672966,
        "organic_estimated_paid_traffic_cost": 15078.99657046888,
        "organic_position_distribution": {
            "pos_1": 11,
            "pos_2_3": 28,
            "pos_4_10": 100,
            "pos_11_20": 135,
            "pos_21_30": 157,
            "pos_31_40": 174,
            "pos_41_50": 203,
            "pos_51_60": 220,
            "pos_61_70": 232,
            "pos_71_80": 202,
            "pos_81_90": 200,
            "pos_91_100": 126,
        },
        "organic_movement": {
            "is_new": 661,
            "is_up": 757,
            "is_down": 418,
            "is_lost": 547,
        },
    }


@pytest.mark.parametrize(
    ("response", "error_type", "match"),
    [
        (
            {"status_code": 50000, "status_message": "Internal Error"},
            DataForSEOAvailabilityError,
            "50000.*Internal Error",
        ),
        (
            {
                "status_code": 20000,
                "tasks": [{"status_code": 40501, "status_message": "Invalid Field"}],
            },
            DataForSEOAvailabilityError,
            "40501.*Invalid Field",
        ),
        (
            {
                "status_code": 20000,
                "tasks": [
                    {
                        "status_code": 20000,
                        "status_message": "Ok.",
                        "result": [],
                    }
                ],
            },
            DataForSEOContractError,
            "result",
        ),
    ],
)
def test_domain_metrics_never_turns_api_task_or_contract_errors_into_empty_data(
    response, error_type, match
):
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: response

    with pytest.raises(error_type, match=match):
        client.get_domain_metrics("simpro.com")


def test_ranking_history_uses_documented_payload_and_month_window(monkeypatch):
    calls = []
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: (
        calls.append((endpoint, data))
        or _successful_response(
            {
                "se_type": "google",
                "keyword": "field service",
                "location_code": 2840,
                "language_code": "en",
                "total_count": 0,
                "items_count": 0,
                "items": [],
            }
        )
    )
    monkeypatch.setattr(
        "data_sources.modules.dataforseo._today",
        lambda: date(2026, 8, 10),
    )

    result = client.check_ranking_history(
        "example.com",
        "field service",
        months_back=12,
    )

    assert result == []
    assert calls == [
        (
            "/v3/dataforseo_labs/google/historical_serps/live",
            [
                {
                    "keyword": "field service",
                    "location_code": 2840,
                    "language_code": "en",
                    "date_from": "2025-08-10",
                    "date_to": "2026-08-10",
                }
            ],
        )
    ]


def test_ranking_history_traverses_months_and_matches_only_exact_organic_hostname():
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: _successful_response(
        {
            "se_type": "google",
            "keyword": "field service",
            "location_code": 2840,
            "language_code": "en",
            "total_count": 2,
            "items_count": 2,
            "items": [
                {
                    "type": "organic",
                    "datetime": "2026-06-01 08:05:11 +00:00",
                    "items_count": 3,
                    "items": [
                        {
                            "type": "paid",
                            "domain": "simpro.com",
                            "url": "https://simpro.com/ad",
                            "rank_group": 1,
                            "rank_absolute": 1,
                        },
                        {
                            "type": "organic",
                            "domain": "notsimpro.com",
                            "url": "https://notsimpro.com/result",
                            "rank_group": 1,
                            "rank_absolute": 2,
                        },
                        {
                            "type": "organic",
                            "domain": "www.simpro.com",
                            "url": "https://www.simpro.com/result",
                            "rank_group": 4,
                            "rank_absolute": 7,
                        },
                    ],
                },
                {
                    "type": "organic",
                    "datetime": "2026-07-01 08:05:11 +00:00",
                    "items_count": 1,
                    "items": [
                        {
                            "type": "organic",
                            "domain": "simpro.com.example.org",
                            "url": "https://simpro.com.example.org/result",
                            "rank_group": 2,
                            "rank_absolute": 2,
                        }
                    ],
                },
            ],
        }
    )

    result = client.check_ranking_history(
        "https://WWW.Simpro.com/path",
        "field service",
        months_back=3,
    )

    assert result == [
        {
            "keyword": "field service",
            "domain": "simpro.com",
            "datetime": "2026-06-01 08:05:11 +00:00",
            "position": 4,
            "rank_group": 4,
            "rank_absolute": 7,
            "url": "https://www.simpro.com/result",
            "ranking": True,
        },
        {
            "keyword": "field service",
            "domain": "simpro.com",
            "datetime": "2026-07-01 08:05:11 +00:00",
            "position": None,
            "rank_group": None,
            "rank_absolute": None,
            "url": None,
            "ranking": False,
        },
    ]


@pytest.mark.parametrize(
    ("response", "error_type"),
    [
        (
            {"status_code": 50000, "status_message": "Internal Error"},
            DataForSEOAvailabilityError,
        ),
        (
            {
                "status_code": 20000,
                "tasks": [{"status_code": 40501, "status_message": "Invalid Field"}],
            },
            DataForSEOAvailabilityError,
        ),
        (
            {
                "status_code": 20000,
                "tasks": [{"status_code": 20000, "result": []}],
            },
            DataForSEOContractError,
        ),
    ],
)
def test_ranking_history_never_turns_api_task_or_contract_errors_into_empty_data(
    response, error_type
):
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: response

    with pytest.raises(error_type):
        client.check_ranking_history("simpro.com", "field service")


def test_keyword_ideas_labels_serp_result_count_without_claiming_average_position():
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: _successful_response(
        {
            "se_type": "google",
            "keyword": "field service",
            "location_code": 2840,
            "language_code": "en",
            "total_count": 1,
            "items_count": 1,
            "items": [
                {
                    "keyword_data": {
                        "keyword": "field service software",
                        "keyword_info": {
                            "search_volume": 90,
                            "cpc": 3.2,
                            "competition": 0.4,
                        },
                    },
                    "serp_info": {"se_results_count": 123456},
                }
            ],
        }
    )

    result = client.get_keyword_ideas("field service")

    assert result == [
        {
            "keyword": "field service software",
            "search_volume": 90,
            "cpc": 3.2,
            "competition": 0.4,
            "serp_results_count": 123456,
        }
    ]


def test_missing_api_or_task_status_is_a_contract_error_not_an_availability_result():
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: {"tasks": []}

    with pytest.raises(DataForSEOContractError, match="status_code"):
        client.get_domain_metrics("simpro.com")

    client._post = lambda endpoint, data: {
        "status_code": 20000,
        "tasks": [{"result": [{"items": []}]}],
    }
    with pytest.raises(DataForSEOContractError, match="status_code"):
        client.get_domain_metrics("simpro.com")
