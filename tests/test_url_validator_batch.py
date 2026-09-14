from __future__ import annotations

import pytest
import requests

from data_sources.modules.url_validator import UrlValidator, validate_content_urls


def _response(url: str, status: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = b""
    response._content_consumed = True
    return response


class RecordingTransport:
    def __init__(self, statuses: dict[tuple[str, str], int]) -> None:
        self.statuses = statuses
        self.batches: list[tuple[str, list[str]]] = []

    def request_many(self, method, urls, **kwargs):
        del kwargs
        ordered = list(urls)
        self.batches.append((method, ordered))
        return [
            _response(url, self.statuses[(method, url)])
            for url in ordered
        ]


def test_validate_many_runs_all_heads_before_get_fallbacks_in_stable_order() -> None:
    one = "https://example.com/one"
    two = "https://example.com/two"
    three = "https://example.com/three"
    transport = RecordingTransport(
        {
            ("HEAD", one): 200,
            ("HEAD", two): 405,
            ("HEAD", three): 403,
            ("GET", two): 204,
            ("GET", three): 403,
        }
    )
    validator = UrlValidator(transport=transport)

    results = validator.validate_many([one, two, one, three])

    assert transport.batches == [
        ("HEAD", [one, two, three]),
        ("GET", [two, three]),
    ]
    assert [result.url for result in results] == [one, two, one, three]
    assert [result.status for result in results] == [
        "resolved", "resolved", "resolved", "manual_review"
    ]
    assert results[0] is not results[2]


def test_validate_content_urls_uses_one_batch_and_restores_link_context() -> None:
    one = "https://example.com/one"
    two = "https://example.com/two"
    transport = RecordingTransport(
        {
            ("HEAD", one): 200,
            ("HEAD", two): 200,
        }
    )
    content = f"[First]({one})\n\n[Second]({two})\n\n[Again]({one})\n"

    summary = validate_content_urls(content, validator=UrlValidator(transport=transport))

    assert transport.batches == [("HEAD", [one, two])]
    assert [(row.line, row.anchor) for row in summary.results] == [
        (1, "First"),
        (3, "Second"),
        (5, "Again"),
    ]


def test_validate_many_falls_back_to_legacy_single_url_behavior() -> None:
    calls: list[tuple[str, str]] = []

    def requester(session, method, url, **kwargs):
        del session, kwargs
        calls.append((method, url))
        return _response(url, 200 if method == "GET" else 405)

    validator = UrlValidator(requester=requester, rate_limit_retry_seconds=0)
    urls = ["https://example.com/one", "https://example.com/two"]

    results = validator.validate_many(urls)

    assert [result.status for result in results] == ["resolved", "resolved"]
    assert calls == [
        ("HEAD", urls[0]),
        ("HEAD", urls[1]),
        ("GET", urls[0]),
        ("GET", urls[1]),
    ]


def test_validate_many_fails_without_partial_results_on_batch_failure() -> None:
    one = "https://example.com/one"
    two = "https://example.com/two"

    class PartiallyUnavailableTransport:
        def request_many(self, method, urls, **kwargs):
            del method, urls, kwargs
            raise requests.ConnectionError("batch member failed")

        def request(self, method, url, **kwargs):
            del method, kwargs
            if url == one:
                raise requests.ConnectionError("offline")
            return _response(url, 200)

    with pytest.raises(requests.ConnectionError, match="batch member failed"):
        UrlValidator(
            transport=PartiallyUnavailableTransport(),
            rate_limit_retry_seconds=0,
        ).validate_many([one, two])
