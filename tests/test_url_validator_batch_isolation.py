from __future__ import annotations

import pytest
import requests

from data_sources.modules.public_http.snapshot import ResponseLimitError
from data_sources.modules.url_validator import UrlValidator


def _response(url: str, status: int) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = b""
    response._content_consumed = True
    return response


def test_batch_failure_falls_back_to_per_url_results() -> None:
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

    results = UrlValidator(
        transport=PartiallyUnavailableTransport(),
        rate_limit_retry_seconds=0,
    ).validate_many([one, two])

    by_url = {result.url: result for result in results}
    assert by_url[one].status == "unresolved"
    assert by_url[one].status_code is None
    assert "offline" in by_url[one].reason
    assert by_url[two].passed


def test_response_limit_error_in_batch_becomes_unresolved() -> None:
    url = "https://example.com/huge"

    class OversizeTransport:
        def request_many(self, method, urls, **kwargs):
            raise ResponseLimitError("public HTTP batch exceeds aggregate response byte limit")

        def request(self, method, url, **kwargs):
            raise ResponseLimitError("public HTTP response exceeds policy byte limit")

    [result] = UrlValidator(
        transport=OversizeTransport(), rate_limit_retry_seconds=0
    ).validate_many([url])
    assert result.status == "unresolved"
    assert "byte limit" in result.reason


def test_programming_value_error_still_aborts_the_run() -> None:
    class BrokenTransport:
        def request_many(self, method, urls, **kwargs):
            raise requests.ConnectionError("batch failed")

        def request(self, method, url, **kwargs):
            raise ValueError("HTTP header is not declared by policy")

    with pytest.raises(ValueError, match="not declared by policy"):
        UrlValidator(
            transport=BrokenTransport(), rate_limit_retry_seconds=0
        ).validate_many(["https://example.com/one"])
