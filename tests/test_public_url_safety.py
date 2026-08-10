import socket
from unittest.mock import patch

import pytest
import requests
from urllib3.util import Timeout

from data_sources.modules import public_url_safety
from data_sources.modules.public_url_safety import (
    PublicUrlSafetyError,
    request_public_url,
    validate_public_url,
)


def resolver_for(address):
    def resolve(host, port, *, type=socket.SOCK_STREAM):
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        return [(family, type, 6, "", (address, port))]

    return resolve


def response(status_code=200, *, headers=None, content=b""):
    result = requests.Response()
    result.status_code = status_code
    result.headers.update(headers or {})
    result._content = content
    result._content_consumed = True
    return result


@pytest.mark.parametrize(
    "url,address",
    [
        ("http://localhost/admin", "127.0.0.1"),
        ("http://internal.test/", "10.0.0.7"),
        ("http://internal.test/", "172.16.4.2"),
        ("http://internal.test/", "192.168.1.9"),
        ("http://metadata.test/", "169.254.169.254"),
        ("http://loopback.test/", "::1"),
    ],
)
def test_validate_public_url_rejects_non_public_destinations(url, address):
    with pytest.raises(PublicUrlSafetyError, match="not public"):
        validate_public_url(url, resolver=resolver_for(address))


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "https://user:secret@example.com/private",
    ],
)
def test_validate_public_url_rejects_schemes_and_credentials(url):
    with pytest.raises(PublicUrlSafetyError, match="HTTP|credentials"):
        validate_public_url(url, resolver=resolver_for("93.184.216.34"))


def test_validate_public_url_accepts_public_https_host():
    assert (
        validate_public_url(
            "https://example.com/guide",
            resolver=resolver_for("93.184.216.34"),
        )
        == "https://example.com/guide"
    )


def test_request_pins_validated_ip_preserves_host_and_ignores_environment_proxy(
    monkeypatch,
):
    resolver_calls = []
    send_calls = []

    def changing_resolver(host, port, *, type=socket.SOCK_STREAM):
        resolver_calls.append((host, port))
        address = "93.184.216.34" if len(resolver_calls) == 1 else "127.0.0.1"
        return resolver_for(address)(host, port, type=type)

    def fake_send(adapter, prepared, **kwargs):
        send_calls.append(
            {
                "pinned_ip": adapter.pinned_ip,
                "server_hostname": adapter.server_hostname,
                "host": prepared.headers["Host"],
                "proxies": kwargs["proxies"],
            }
        )
        return response(content=b"safe")

    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8080")
    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        side_effect=fake_send,
    ):
        result = request_public_url(
            requests.Session(),
            "GET",
            "https://example.com/start",
            resolver=changing_resolver,
        )

    assert result.content == b"safe"
    assert resolver_calls == [("example.com", 443)]
    assert send_calls == [
        {
            "pinned_ip": "93.184.216.34",
            "server_hostname": "example.com",
            "host": "example.com",
            "proxies": {},
        }
    ]


def test_https_certificate_verification_cannot_be_disabled():
    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        return_value=response(content=b"unsafe"),
    ):
        with pytest.raises(PublicUrlSafetyError, match="certificate verification"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/guide",
                resolver=resolver_for("93.184.216.34"),
                verify=False,
            )


def test_https_pool_uses_pinned_destination_with_original_sni_and_certificate_name():
    class PoolManager:
        def __init__(self):
            self.calls = []

        def connection_from_host(self, **kwargs):
            self.calls.append(kwargs)
            return object()

    adapter = public_url_safety._PinnedHTTPAdapter(
        pinned_ip="93.184.216.34",
        server_hostname="example.com",
        port=443,
    )
    manager = PoolManager()
    adapter.poolmanager = manager
    prepared = requests.Request("GET", "https://example.com/guide").prepare()

    adapter.get_connection_with_tls_context(
        prepared, verify=True, proxies={}, cert=None
    )

    call = manager.calls[0]
    assert call["host"] == "93.184.216.34"
    assert call["port"] == 443
    assert call["scheme"] == "https"
    assert call["pool_kwargs"]["server_hostname"] == "example.com"
    assert call["pool_kwargs"]["assert_hostname"] == "example.com"


def test_legacy_requests_connection_hook_uses_the_same_pinned_tls_pool():
    class PoolManager:
        def __init__(self):
            self.calls = []

        def connection_from_host(self, **kwargs):
            self.calls.append(kwargs)
            return object()

    adapter = public_url_safety._PinnedHTTPAdapter(
        pinned_ip="93.184.216.34",
        server_hostname="example.com",
        port=443,
    )
    manager = PoolManager()
    adapter.poolmanager = manager

    adapter.get_connection("https://example.com/guide", proxies={})

    call = manager.calls[0]
    assert call["host"] == "93.184.216.34"
    assert call["port"] == 443
    assert call["scheme"] == "https"
    assert call["pool_kwargs"]["server_hostname"] == "example.com"
    assert call["pool_kwargs"]["assert_hostname"] == "example.com"


def test_request_revalidates_redirect_and_blocks_private_target():
    send_count = 0

    def fake_send(adapter, prepared, **kwargs):
        nonlocal send_count
        send_count += 1
        return response(302, headers={"Location": "http://127.0.0.1/internal"})

    def resolver(host, port, *, type=socket.SOCK_STREAM):
        address = "93.184.216.34" if host == "example.com" else "127.0.0.1"
        return resolver_for(address)(host, port, type=type)

    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        side_effect=fake_send,
    ):
        with pytest.raises(PublicUrlSafetyError, match="not public"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/start",
                resolver=resolver,
            )

    assert send_count == 1


def test_request_rejects_excessive_redirects():
    def fake_send(adapter, prepared, **kwargs):
        return response(302, headers={"Location": "/again"})

    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        side_effect=fake_send,
    ):
        with pytest.raises(PublicUrlSafetyError, match="redirect"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/start",
                resolver=resolver_for("93.184.216.34"),
                max_redirects=1,
            )


def test_request_blocks_oversized_decompressed_chunked_body_and_closes_response():
    class ChunkedResponse:
        status_code = 200
        headers = {}
        url = "https://example.com/large"

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            yield b"a" * 6
            yield b"b" * 6

        def close(self):
            self.closed = True

    streamed = ChunkedResponse()

    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        return_value=streamed,
    ):
        with pytest.raises(PublicUrlSafetyError, match="response size"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/large",
                resolver=resolver_for("93.184.216.34"),
                max_response_bytes=10,
            )

    assert streamed.closed is True


def test_successful_chunked_response_is_materialized_then_closed():
    class ChunkedResponse:
        status_code = 200
        headers = {}
        url = "https://example.com/content"

        def __init__(self):
            self.closed = False
            self._content = False
            self._content_consumed = False

        def iter_content(self, chunk_size):
            yield b"bounded"
            yield b" content"

        def close(self):
            self.closed = True

    streamed = ChunkedResponse()

    with patch.object(
        public_url_safety._PinnedHTTPAdapter,
        "send",
        autospec=True,
        return_value=streamed,
    ):
        result = request_public_url(
            requests.Session(),
            "GET",
            "https://example.com/content",
            resolver=resolver_for("93.184.216.34"),
        )

    assert result._content == b"bounded content"
    assert result._content_consumed is True
    assert streamed.closed is True


def test_request_enforces_total_deadline_across_streamed_chunks():
    class SlowStreamingResponse:
        status_code = 200
        headers = {}
        url = "https://example.com/slow"

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            yield b"first"
            yield b"second"

        def close(self):
            self.closed = True

    streamed = SlowStreamingResponse()
    monotonic_values = iter([10.0, 10.1, 10.2, 10.8, 11.1])

    with (
        patch.object(
            public_url_safety._PinnedHTTPAdapter,
            "send",
            autospec=True,
            return_value=streamed,
        ),
        patch.object(
            public_url_safety.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values),
        ),
    ):
        with pytest.raises(PublicUrlSafetyError, match="total deadline"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/slow",
                resolver=resolver_for("93.184.216.34"),
                total_timeout_seconds=1.0,
            )

    assert streamed.closed is True


def test_request_checks_total_deadline_after_stream_completion():
    class SlowEmptyResponse:
        status_code = 200
        headers = {}
        url = "https://example.com/slow-empty"

        def __init__(self):
            self.closed = False

        def iter_content(self, chunk_size):
            assert chunk_size > 0
            if False:
                yield b""

        def close(self):
            self.closed = True

    streamed = SlowEmptyResponse()
    monotonic_values = iter([10.0, 10.1, 10.2, 10.3, 11.1])

    with (
        patch.object(
            public_url_safety._PinnedHTTPAdapter,
            "send",
            autospec=True,
            return_value=streamed,
        ),
        patch.object(
            public_url_safety.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values),
        ),
    ):
        with pytest.raises(PublicUrlSafetyError, match="total deadline"):
            request_public_url(
                requests.Session(),
                "GET",
                "https://example.com/slow-empty",
                resolver=resolver_for("93.184.216.34"),
                total_timeout_seconds=1.0,
            )

    assert streamed.closed is True


def test_request_passes_remaining_wall_clock_budget_to_urllib3_transport():
    captured = {}

    def fake_send(adapter, prepared, **kwargs):
        captured["timeout"] = kwargs["timeout"]
        return response(content=b"bounded")

    monotonic_values = iter([10.0, 10.1, 10.2, 10.3, 10.4, 10.5])
    with (
        patch.object(
            public_url_safety._PinnedHTTPAdapter,
            "send",
            autospec=True,
            side_effect=fake_send,
        ),
        patch.object(
            public_url_safety.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values),
        ),
    ):
        request_public_url(
            requests.Session(),
            "GET",
            "https://example.com/guide",
            resolver=resolver_for("93.184.216.34"),
            timeout=(4.0, 5.0),
            total_timeout_seconds=3.0,
        )

    transport_timeout = captured["timeout"]
    assert isinstance(transport_timeout, Timeout)
    assert transport_timeout.total == pytest.approx(2.8)
    assert transport_timeout.connect_timeout == pytest.approx(2.8)
    assert transport_timeout.read_timeout == pytest.approx(2.8)


@pytest.mark.parametrize(
    "total_timeout_seconds",
    [0, -1, float("inf"), float("nan")],
)
def test_request_rejects_nonfinite_or_nonpositive_total_deadline(
    total_timeout_seconds,
):
    with (
        patch.object(
            public_url_safety._PinnedHTTPAdapter,
            "send",
            autospec=True,
            return_value=response(content=b"unexpected request"),
        ) as send,
        pytest.raises(ValueError, match="finite and positive"),
    ):
        request_public_url(
            requests.Session(),
            "GET",
            "https://example.com/guide",
            resolver=resolver_for("93.184.216.34"),
            total_timeout_seconds=total_timeout_seconds,
        )
    send.assert_not_called()
