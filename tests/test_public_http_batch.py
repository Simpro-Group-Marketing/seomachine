from __future__ import annotations

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace

import pytest
import requests

from data_sources.modules.public_http import HttpBatchPolicy, URL_RESOLUTION_POLICY
from data_sources.modules.public_http.transport import PublicHttpTransport


MIB = 1024 * 1024


def _public_resolver(host: str, port: int, **_: object):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _response(url: str, body: bytes = b"ok", status: int = 200) -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = body
    response._content_consumed = True
    response.headers["Content-Type"] = "text/plain"
    return response


def test_batch_policy_has_strict_frozen_defaults() -> None:
    policy = HttpBatchPolicy()

    assert policy.max_workers == 8
    assert policy.max_per_host == 2
    assert policy.max_aggregate_response_bytes == 32 * MIB
    with pytest.raises(FrozenInstanceError):
        policy.max_workers = 4  # type: ignore[misc]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_workers": True},
        {"max_workers": 0},
        {"max_per_host": False},
        {"max_per_host": 0},
        {"max_workers": 2, "max_per_host": 3},
        {"max_aggregate_response_bytes": True},
        {"max_aggregate_response_bytes": 0},
    ],
)
def test_batch_policy_rejects_invalid_limits(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        HttpBatchPolicy(**kwargs)  # type: ignore[arg-type]


def test_transport_preserves_legacy_concurrency_constructor_arguments() -> None:
    with PublicHttpTransport(
        max_workers=3,
        max_per_host=1,
        resolver=_public_resolver,
        persistent_cache=False,
    ) as transport:
        assert transport.batch_policy == HttpBatchPolicy(max_workers=3, max_per_host=1)

    with pytest.raises(ValueError, match="legacy concurrency"):
        PublicHttpTransport(
            batch_policy=HttpBatchPolicy(max_workers=4, max_per_host=2),
            max_workers=3,
            resolver=_public_resolver,
            persistent_cache=False,
        )


def test_request_many_deduplicates_and_preserves_input_order() -> None:
    calls: list[str] = []
    events: list[tuple[str, int]] = []

    def requester(session, method, url, **kwargs):
        del session, method, kwargs
        calls.append(url)
        if url.endswith("slow"):
            time.sleep(0.03)
        return _response(url, body=url.rsplit("/", 1)[-1].encode())

    urls = [
        "https://example.com/slow",
        "https://example.com/fast",
        "https://example.com/slow",
    ]
    with PublicHttpTransport(
        requester=requester,
        resolver=_public_resolver,
        persistent_cache=False,
        observer=lambda name, amount: events.append((name, amount)),
    ) as transport:
        results = transport.request_many("GET", urls)

    assert sorted(calls) == sorted(set(urls))
    assert [result.content for result in results] == [b"slow", b"fast", b"slow"]
    assert results[0] is not results[2]
    assert ("deduplicated_requests", 1) in events
    assert sum(amount for name, amount in events if name == "requests") == 2
    assert sum(amount for name, amount in events if name == "response_bytes") == 8


def test_request_many_consumes_a_sliding_window() -> None:
    release = threading.Event()
    two_started = threading.Event()
    started = 0
    yielded = 0
    lock = threading.Lock()

    def urls():
        nonlocal yielded
        for index in range(6):
            yielded += 1
            yield f"https://example.com/{index}"

    def requester(session, method, url, **kwargs):
        nonlocal started
        del session, method, kwargs
        with lock:
            started += 1
            if started == 2:
                two_started.set()
        assert release.wait(timeout=5)
        return _response(url)

    with PublicHttpTransport(
        requester=requester,
        resolver=_public_resolver,
        persistent_cache=False,
        batch_policy=HttpBatchPolicy(max_workers=2, max_per_host=2),
    ) as transport:
        with ThreadPoolExecutor(max_workers=1) as caller:
            future = caller.submit(transport.request_many, "GET", urls())
            assert two_started.wait(timeout=5)
            assert yielded == 2
            release.set()
            assert len(future.result(timeout=5)) == 6


def test_request_many_rejects_work_that_cannot_fit_aggregate_budget() -> None:
    calls = 0
    request_policy = replace(URL_RESOLUTION_POLICY, max_response_bytes=8)

    def requester(session, method, url, **kwargs):
        nonlocal calls
        del session, method, kwargs
        calls += 1
        return _response(url, body=b"123456")

    with PublicHttpTransport(
        requester=requester,
        resolver=_public_resolver,
        persistent_cache=False,
        batch_policy=HttpBatchPolicy(
            max_workers=1,
            max_per_host=1,
            max_aggregate_response_bytes=10,
        ),
    ) as transport:
        with pytest.raises(ValueError, match="aggregate response byte limit"):
            transport.request_many(
                "GET",
                ["https://example.com/one", "https://example.com/two"],
                policy=request_policy,
            )

    assert calls == 1


def test_observer_failures_do_not_change_transport_results() -> None:
    def observer(name: str, amount: int) -> None:
        del name, amount
        raise RuntimeError("telemetry unavailable")

    with PublicHttpTransport(
        requester=lambda session, method, url, **kwargs: _response(url),
        resolver=_public_resolver,
        persistent_cache=False,
        observer=observer,
    ) as transport:
        assert transport.request("GET", "https://example.com/source").content == b"ok"


def test_observer_emits_balanced_request_and_batch_memory_deltas() -> None:
    events: list[tuple[str, int]] = []
    policy = replace(URL_RESOLUTION_POLICY, max_response_bytes=16)

    with PublicHttpTransport(
        requester=lambda session, method, url, **kwargs: _response(url, body=b"data"),
        resolver=_public_resolver,
        persistent_cache=False,
        batch_policy=HttpBatchPolicy(
            max_workers=2,
            max_per_host=2,
            max_aggregate_response_bytes=32,
        ),
        observer=lambda name, amount: events.append((name, amount)),
    ) as transport:
        responses = transport.request_many(
            "GET",
            ["https://example.com/one", "https://example.com/two"],
            policy=policy,
        )

    assert [response.content for response in responses] == [b"data", b"data"]
    assert sum(amount for name, amount in events if name == "in_flight_requests_delta") == 0
    assert sum(amount for name, amount in events if name == "reserved_bytes_delta") == 0
    assert sum(amount for name, amount in events if name == "retained_bytes_delta") == 0
    assert ("in_flight_requests_delta", 1) in events
    assert ("in_flight_requests_delta", -1) in events
    assert ("reserved_bytes_delta", 16) in events
    assert ("reserved_bytes_delta", -16) in events
    assert sum(amount for name, amount in events if name == "retained_bytes_delta" and amount > 0) == 8


def test_batch_releases_observed_reservations_when_a_request_fails() -> None:
    events: list[tuple[str, int]] = []
    policy = replace(URL_RESOLUTION_POLICY, max_response_bytes=16)

    def requester(session, method, url, **kwargs):
        del session, method, kwargs
        if url.endswith("fail"):
            raise requests.ConnectionError("offline")
        time.sleep(0.02)
        return _response(url, body=b"data")

    with PublicHttpTransport(
        requester=requester,
        resolver=_public_resolver,
        persistent_cache=False,
        batch_policy=HttpBatchPolicy(
            max_workers=2,
            max_per_host=2,
            max_aggregate_response_bytes=32,
        ),
        observer=lambda name, amount: events.append((name, amount)),
    ) as transport:
        with pytest.raises(requests.ConnectionError, match="offline"):
            transport.request_many(
                "GET",
                ["https://example.com/fail", "https://example.com/slow"],
                policy=policy,
            )

    assert sum(amount for name, amount in events if name == "in_flight_requests_delta") == 0
    assert sum(amount for name, amount in events if name == "reserved_bytes_delta") == 0
    assert sum(amount for name, amount in events if name == "retained_bytes_delta") == 0
