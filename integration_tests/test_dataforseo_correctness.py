from __future__ import annotations

from data_sources.modules.dataforseo import DataForSEO


def _client_with_response(response):
    client = object.__new__(DataForSEO)
    client._post = lambda endpoint, data: response
    return client


def _serp_response(items, *, keyword="field service software"):
    return {
        "status_code": 20000,
        "status_message": "Ok.",
        "tasks": [
            {
                "status_code": 20000,
                "status_message": "Ok.",
                "data": {"keyword": keyword},
                "result": [
                    {
                        "items": items,
                        "items_count": len(items),
                        "keyword_data": {"keyword_info": {}},
                    }
                ],
            }
        ],
    }


def test_get_rankings_rejects_lookalike_hostname_and_uses_api_rank_fields():
    client = _client_with_response(
        _serp_response(
            [
                {
                    "type": "organic",
                    "domain": "notsimpro.com",
                    "url": "https://notsimpro.com/field-service",
                    "rank_group": 1,
                    "rank_absolute": 2,
                },
                {
                    "type": "organic",
                    "domain": "www.simpro.com",
                    "url": "https://www.simpro.com/field-service",
                    "rank_group": 4,
                    "rank_absolute": 9,
                },
            ]
        )
    )

    result = client.get_rankings("simpro.com", ["field service software"])

    assert result == [
        {
            "keyword": "field service software",
            "domain": "simpro.com",
            "position": 4,
            "rank_group": 4,
            "rank_absolute": 9,
            "url": "https://www.simpro.com/field-service",
            "ranking": True,
            "search_volume": None,
            "cpc": None,
        }
    ]


def test_get_rankings_falls_back_to_absolute_rank_when_group_rank_is_missing():
    client = _client_with_response(
        _serp_response(
            [
                {
                    "type": "organic",
                    "domain": "simpro.com",
                    "url": "https://simpro.com/field-service",
                    "rank_absolute": 11,
                }
            ]
        )
    )

    result = client.get_rankings("https://www.simpro.com/", ["field service software"])

    assert result[0]["position"] == 11
    assert result[0]["rank_group"] is None
    assert result[0]["rank_absolute"] == 11


def test_analyze_competitor_uses_exact_hostnames_and_api_group_ranks():
    client = _client_with_response(
        _serp_response(
            [
                {
                    "type": "organic",
                    "domain": "notcompetitor.com",
                    "url": "https://notcompetitor.com/result",
                    "rank_group": 1,
                    "rank_absolute": 2,
                },
                {
                    "type": "organic",
                    "domain": "competitor.com",
                    "url": "https://competitor.com/result",
                    "rank_group": 6,
                    "rank_absolute": 10,
                },
                {
                    "type": "organic",
                    "domain": "example.com",
                    "url": "https://example.com/result",
                    "rank_group": 8,
                    "rank_absolute": 13,
                },
            ]
        )
    )

    result = client.analyze_competitor(
        "competitor.com",
        ["field service software"],
        your_domain="www.example.com",
    )

    assert result["comparison"][0]["competitor_position"] == 6
    assert result["comparison"][0]["your_position"] == 8


def test_get_questions_requires_a_complete_question_word():
    client = _client_with_response(
        _serp_response(
            [
                {
                    "keyword_data": {
                        "keyword": "issue tracking software",
                        "keyword_info": {"search_volume": 90, "cpc": 3.2},
                    }
                },
                {
                    "keyword_data": {
                        "keyword": "is field service software worth it",
                        "keyword_info": {"search_volume": 40, "cpc": 2.1},
                    }
                },
            ],
            keyword="field service software",
        )
    )

    result = client.get_questions("field service software")

    assert [row["question"] for row in result] == [
        "is field service software worth it"
    ]


def test_get_serp_data_preserves_first_seen_feature_order_when_deduplicating():
    client = _client_with_response(
        _serp_response(
            [
                {"type": "z_feature"},
                {"type": "a_feature"},
                {"type": "m_feature"},
                {"type": "z_feature"},
            ]
        )
    )

    result = client.get_serp_data("field service software")

    assert result["features"] == ["z_feature", "a_feature", "m_feature"]


def test_get_serp_capture_returns_exact_response_and_existing_normalized_view():
    response = _serp_response(
        [
            {
                "type": "organic",
                "rank_absolute": 1,
                "url": "https://example.com/guide",
                "domain": "example.com",
                "title": "Field Service Guide",
                "description": "A practical guide.",
                "breadcrumb": "Guides",
            },
            {"type": "people_also_ask"},
        ]
    )
    response["provider_marker"] = {"request_id": "dfs-exact-123"}
    client = _client_with_response(response)

    raw, normalized = client.get_serp_capture("field service software")

    assert raw is response
    assert raw["provider_marker"] == {"request_id": "dfs-exact-123"}
    assert normalized == client.get_serp_data("field service software")


def test_post_uses_a_finite_positive_request_timeout():
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"status_code": 20000, "tasks": []}

    class Session:
        def __init__(self):
            self.timeout = None

        def post(self, url, *, json, timeout=None):
            self.timeout = timeout
            return Response()

    client = object.__new__(DataForSEO)
    client.base_url = "https://api.dataforseo.com"
    client.session = Session()

    result = client._post("/v3/test", [{"keyword": "test"}])

    assert result == {"status_code": 20000, "tasks": []}
    assert client.session.timeout is not None
    assert client.session.timeout > 0
