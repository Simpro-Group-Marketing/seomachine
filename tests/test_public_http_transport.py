from __future__ import annotations
import os
import socket
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pytest
import requests
from diskcache import Cache
from data_sources.modules.public_http import cache as cache_module
from data_sources.modules.public_http.cache import ResponseCache
from data_sources.modules.public_http.transport import (
    PublicHttpTransport,
    _canonical_url,
    _request_key,
)
from data_sources.modules.public_http.policies import URL_RESOLUTION_POLICY
from data_sources.modules.public_url_safety import PublicUrlSafetyError

def _public_resolver(host: str, port: int, **_: object):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def _response(url: str, status: int = 200, body: bytes = b"ok") -> requests.Response:
    response = requests.Response()
    response.status_code = status
    response.url = url
    response._content = body
    response._content_consumed = True
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


def test_transport_memoizes_semantically_identical_requests() -> None:
    calls: list[tuple[str, str]] = []

    def requester(session, method, url, **kwargs):
        del session, kwargs
        calls.append((method, url))
        return _response(url)

    with PublicHttpTransport(
        requester=requester, resolver=_public_resolver, persistent_cache=False
    ) as transport:
        first = transport.request("GET", "https://example.com/source")
        second = transport.request("GET", "https://example.com/source")

    assert calls == [("GET", "https://example.com/source")]
    assert first is not second
    assert first.content == second.content == b"ok"
    assert transport.counters == {"requests": 1, "cache_hits": 1, "cache_misses": 1}


def test_transport_single_flight_deduplicates_concurrent_callers() -> None:
    calls = 0
    lock = threading.Lock()

    def requester(session, method, url, **kwargs):
        nonlocal calls
        del session, method, kwargs
        with lock:
            calls += 1
        time.sleep(0.03)
        return _response(url)

    with PublicHttpTransport(
        requester=requester, resolver=_public_resolver, persistent_cache=False
    ) as transport:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(
                pool.map(
                    lambda _: transport.request("GET", "https://example.com/source"),
                    range(8),
                )
            )

    assert calls == 1
    assert [result.content for result in results] == [b"ok"] * 8


def test_transport_batch_preserves_input_order() -> None:
    def requester(session, method, url, **kwargs):
        del session, method, kwargs
        if url.endswith("slow"):
            time.sleep(0.03)
        return _response(url, body=url.rsplit("/", 1)[-1].encode())

    urls = ["https://example.com/slow", "https://example.com/fast"]
    with PublicHttpTransport(
        requester=requester, resolver=_public_resolver, persistent_cache=False
    ) as transport:
        results = transport.request_many("GET", urls)

    assert [result.content for result in results] == [b"slow", b"fast"]


def test_transport_rejects_credentials_before_upstream_request() -> None:
    def requester(*args, **kwargs):
        raise AssertionError("unsafe URL reached requester")

    with PublicHttpTransport(
        requester=requester, resolver=_public_resolver, persistent_cache=False
    ) as transport:
        with pytest.raises(PublicUrlSafetyError, match="credentials"):
            transport.request("GET", "https://user:secret@example.com/source")


def test_transport_enforces_two_requests_per_host() -> None:
    active = 0
    maximum = 0
    lock = threading.Lock()

    def requester(session, method, url, **kwargs):
        nonlocal active, maximum
        del session, method
        guard = kwargs["request_guard"]
        host = url.split("/", 3)[2]
        with guard(host):
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with lock:
                active -= 1
        return _response(url)

    urls = [f"https://example.com/{index}" for index in range(8)]
    with PublicHttpTransport(
        requester=requester, resolver=_public_resolver, persistent_cache=False
    ) as transport:
        transport.request_many("GET", urls)

    assert maximum == 2


@pytest.mark.parametrize("status", [200, 404, 410, 401, 403])
def test_transport_persists_positive_and_stable_negative_responses(
    tmp_path: Path,
    status: int,
) -> None:
    calls = 0

    def requester(session, method, url, **kwargs):
        nonlocal calls
        del session, method, kwargs
        calls += 1
        return _response(url, status=status)

    options = {
        "cache_dir": tmp_path / "cache",
        "requester": requester,
        "resolver": _public_resolver,
    }
    with PublicHttpTransport(**options) as first:
        first.request("GET", "https://example.com/source")
    with PublicHttpTransport(**options) as second:
        response = second.request("GET", "https://example.com/source")

    assert response.status_code == status
    assert calls == 1
    assert second.counters["cache_hits"] == 1


@pytest.mark.parametrize("status", [429, 500, 503])
def test_transport_does_not_persist_transient_negative_responses(
    tmp_path: Path,
    status: int,
) -> None:
    calls = 0

    def requester(session, method, url, **kwargs):
        nonlocal calls
        del session, method, kwargs
        calls += 1
        return _response(url, status=status)

    options = {
        "cache_dir": tmp_path / "cache",
        "requester": requester,
        "resolver": _public_resolver,
    }
    with PublicHttpTransport(**options) as first:
        first.request("GET", "https://example.com/source")
    with PublicHttpTransport(**options) as second:
        second.request("GET", "https://example.com/source")

    assert calls == 2


def test_transport_treats_corrupt_persistent_entry_as_a_miss(tmp_path: Path) -> None:
    url = "https://example.com/source"
    key = _request_key(
        "GET", _canonical_url(url), None, URL_RESOLUTION_POLICY
    )
    with Cache(str(tmp_path / "cache")) as cache:
        cache.set(key, {"schema": "wrong"}, expire=60)
    calls = 0

    def requester(session, method, requested_url, **kwargs):
        nonlocal calls
        del session, method, kwargs
        calls += 1
        return _response(requested_url)

    with PublicHttpTransport(
        cache_dir=tmp_path / "cache",
        requester=requester,
        resolver=_public_resolver,
    ) as transport:
        response = transport.request("GET", url)

    assert response.status_code == 200
    assert calls == 1


def test_response_cache_lock_failure_degrades_to_unlocked_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenLock:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def acquire(self) -> None:
            raise OSError("lock backend unavailable")

    monkeypatch.setattr(cache_module, "Lock", BrokenLock)
    cache = ResponseCache(tmp_path / "cache", size_limit=1024 * 1024)

    entered = False
    with cache.lock("request"):
        entered = True

    cache.close()
    assert entered is True


def test_transport_disk_lock_single_flights_across_processes(tmp_path: Path) -> None:
    script = tmp_path / "transport_process.py"
    script.write_text(
        """from pathlib import Path
import socket
import sys
import time
import requests
from data_sources.modules.public_http.transport import PublicHttpTransport

def resolver(host, port, **kwargs):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))]

def requester(session, method, url, **kwargs):
    with Path(sys.argv[2]).open('a', encoding='utf-8') as handle:
        handle.write('request\\n')
        handle.flush()
    time.sleep(0.25)
    response = requests.Response()
    response.status_code = 200
    response.url = url
    response._content = b'ok'
    response._content_consumed = True
    response.headers['Content-Type'] = 'text/plain'
    return response

with PublicHttpTransport(cache_dir=Path(sys.argv[1]), requester=requester, resolver=resolver) as transport:
    assert transport.request('GET', 'https://example.com/source').content == b'ok'
""",
        encoding="utf-8",
    )
    cache_dir = tmp_path / "cache"
    call_log = tmp_path / "calls.txt"
    command = [sys.executable, str(script), str(cache_dir), str(call_log)]
    environment = dict(os.environ)
    project_root = str(Path(__file__).resolve().parents[1])
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (project_root, environment.get("PYTHONPATH", "")))
    )

    first = subprocess.Popen(command, env=environment)
    time.sleep(0.05)
    second = subprocess.Popen(command, env=environment)
    assert first.wait(timeout=20) == 0
    assert second.wait(timeout=20) == 0

    assert call_log.read_text(encoding="utf-8").splitlines() == ["request"]
