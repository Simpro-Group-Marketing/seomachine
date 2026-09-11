from __future__ import annotations

import socket

import pytest
import requests

from data_sources.modules.public_http.policies import (
    COMPETITOR_CONTENT_POLICY,
    HttpRequestPolicy,
    URL_RESOLUTION_POLICY,
)
from data_sources.modules.public_http.transport import PublicHttpTransport, _request_key


def _resolver(host: str, port: int, **_: object):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _response(url: str, status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = b"ok"
    response._content_consumed = True
    response.headers["Content-Type"] = "text/plain"
    return response


def test_transport_policy_changes_cache_identity() -> None:
    first = _request_key("GET", "https://example.com/source", None, URL_RESOLUTION_POLICY)
    second = _request_key("GET", "https://example.com/source", None, COMPETITOR_CONTENT_POLICY)
    assert first != second


def test_transient_response_retries_within_same_transport() -> None:
    statuses = iter((503, 200))

    def requester(session, method, url, **kwargs):
        del session, method, kwargs
        return _response(url, status=next(statuses))

    with PublicHttpTransport(
        requester=requester, resolver=_resolver, persistent_cache=False
    ) as transport:
        assert transport.request("GET", "https://example.com/source").status_code == 503
        assert transport.request("GET", "https://example.com/source").status_code == 200
    assert transport.counters["requests"] == 2


def test_request_exception_is_never_memoized() -> None:
    calls = 0

    def requester(session, method, url, **kwargs):
        nonlocal calls
        del session, method, url, kwargs
        calls += 1
        raise requests.ConnectionError("offline")

    with PublicHttpTransport(
        requester=requester, resolver=_resolver, persistent_cache=False
    ) as transport:
        for _ in range(2):
            with pytest.raises(requests.ConnectionError):
                transport.request("GET", "https://example.com/source")
    assert calls == 2


def test_transport_rejects_undeclared_headers_and_request_bodies() -> None:
    with PublicHttpTransport(
        requester=lambda *args, **kwargs: _response("https://example.com"),
        resolver=_resolver,
        persistent_cache=False,
    ) as transport:
        with pytest.raises(ValueError, match="header"):
            transport.request("GET", "https://example.com/source", headers={"X-Secret": "value"})
        with pytest.raises(ValueError, match="body"):
            transport.request("GET", "https://example.com/source", body=b"payload")


def test_http_policy_rejects_retryable_negative_cache_status() -> None:
    values = URL_RESOLUTION_POLICY.canonical_value()
    values["retryable_statuses"] = frozenset(values["retryable_statuses"])
    values["stable_negative_ttls"] = ((503, 60),)
    with pytest.raises(ValueError, match="retryable"):
        HttpRequestPolicy(**values)
