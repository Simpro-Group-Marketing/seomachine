"""SSRF-safe HTTP helpers for public evidence and competitor URLs."""

from __future__ import annotations

import ipaddress
import math
import socket
import time
from contextlib import nullcontext
from dataclasses import dataclass
from typing import Any, Callable, ContextManager, Mapping
from urllib.parse import urljoin, urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Timeout


Resolver = Callable[..., list[tuple[Any, ...]]]
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
DEFAULT_TIMEOUT_SECONDS = 12
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_RESPONSE_CHUNK_BYTES = 64 * 1024


class PublicUrlSafetyError(ValueError):
    """Raised when a URL is not a safe public HTTP(S) destination."""


@dataclass(frozen=True)
class _ResolvedPublicUrl:
    url: str
    hostname: str
    port: int
    address: str
    host_header: str


class _PinnedHTTPAdapter(HTTPAdapter):
    """Requests adapter that connects to one validated IP for one URL hop."""

    def __init__(self, *, pinned_ip: str, server_hostname: str, port: int) -> None:
        self.pinned_ip = pinned_ip
        self.server_hostname = server_hostname
        self.pinned_port = port
        super().__init__(
            pool_connections=1, pool_maxsize=1, max_retries=0, pool_block=True
        )

    def _connection_from_pinned_host(
        self,
        *,
        scheme: str,
        pool_kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Build a connection pool that never resolves the URL hostname again."""
        connection_kwargs = dict(pool_kwargs or {})
        if scheme == "https":
            connection_kwargs["server_hostname"] = self.server_hostname
            connection_kwargs["assert_hostname"] = self.server_hostname
        return self.poolmanager.connection_from_host(
            host=self.pinned_ip,
            port=self.pinned_port,
            scheme=scheme,
            pool_kwargs=connection_kwargs,
        )

    def get_connection(self, url, proxies=None):
        """Pin the legacy Requests <=2.32.1 connection path to the vetted IP."""
        del proxies
        return self._connection_from_pinned_host(
            scheme=urlsplit(url).scheme.casefold(),
        )

    def get_connection_with_tls_context(self, request, verify, proxies=None, cert=None):
        """Build a pool for the pinned IP while verifying the original hostname."""
        try:
            _, pool_kwargs = self.build_connection_pool_key_attributes(
                request,
                verify,
                cert,
            )
        except ValueError as error:
            raise requests.exceptions.InvalidURL(error, request=request) from error

        return self._connection_from_pinned_host(
            scheme=urlsplit(request.url).scheme.casefold(),
            pool_kwargs=pool_kwargs,
        )


def _resolve_public_url(url: str, *, resolver: Resolver) -> _ResolvedPublicUrl:
    candidate = str(url or "").strip()
    parsed = urlsplit(candidate)
    scheme = parsed.scheme.casefold()
    if scheme not in {"http", "https"}:
        raise PublicUrlSafetyError("Public evidence URLs must use HTTP or HTTPS.")
    if not parsed.hostname:
        raise PublicUrlSafetyError("Public evidence URL requires a hostname.")
    if parsed.username is not None or parsed.password is not None:
        raise PublicUrlSafetyError("Public evidence URLs must not contain credentials.")
    try:
        parsed_port = parsed.port
    except ValueError as error:
        raise PublicUrlSafetyError(
            "Public evidence URL has an invalid port."
        ) from error
    port = parsed_port or (443 if scheme == "https" else 80)

    hostname = parsed.hostname.rstrip(".")
    try:
        server_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise PublicUrlSafetyError(
            "Public evidence URL has an invalid hostname."
        ) from error

    try:
        answers = resolver(server_hostname, port, type=socket.SOCK_STREAM)
    except OSError as error:
        raise PublicUrlSafetyError(
            f"Public evidence hostname could not be resolved: {server_hostname}"
        ) from error

    addresses: list[str] = []
    for answer in answers:
        if len(answer) < 5 or not answer[4]:
            continue
        address = str(answer[4][0]).split("%", 1)[0]
        if address not in addresses:
            addresses.append(address)
    if not addresses:
        raise PublicUrlSafetyError(
            f"Public evidence hostname returned no addresses: {server_hostname}"
        )

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as error:
            raise PublicUrlSafetyError(
                f"Public evidence hostname returned an invalid address: {address}"
            ) from error
        if not ip.is_global:
            raise PublicUrlSafetyError(
                f"Public evidence destination is not public: {server_hostname} ({address})"
            )

    host_header = f"[{server_hostname}]" if ":" in server_hostname else server_hostname
    default_port = 443 if scheme == "https" else 80
    if parsed_port is not None and parsed_port != default_port:
        host_header = f"{host_header}:{port}"

    return _ResolvedPublicUrl(
        url=candidate,
        hostname=server_hostname,
        port=port,
        address=addresses[0],
        host_header=host_header,
    )


def validate_public_url(
    url: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> str:
    """Validate an HTTP(S) URL and require every resolved address to be public."""
    return _resolve_public_url(url, resolver=resolver).url


def _remaining_seconds(deadline: float) -> float:
    """Return deadline budget remaining or fail with a stable transport error."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise PublicUrlSafetyError(
            "Public evidence request exceeded the total deadline."
        )
    return remaining


def _bounded_socket_timeout(
    timeout: float | tuple[float, float],
    *,
    remaining: float,
) -> Timeout:
    """Bind connect and read waits to one remaining wall-clock budget."""
    if isinstance(timeout, tuple):
        if len(timeout) != 2:
            raise ValueError("timeout tuple must contain connect and read seconds")
        connect_value, read_value = (float(value) for value in timeout)
    else:
        connect_value = read_value = float(timeout)
    if any(
        not math.isfinite(value) or value <= 0 for value in (connect_value, read_value)
    ):
        raise ValueError("timeout values must be finite and positive")
    return Timeout(
        total=remaining,
        connect=min(connect_value, remaining),
        read=min(read_value, remaining),
    )


def _materialize_bounded_response(
    response: Any,
    *,
    method: str,
    max_response_bytes: int,
    deadline: float,
) -> Any:
    """Read a response within its byte and total-time budgets, then release it."""
    try:
        _remaining_seconds(deadline)
        if (
            method == "HEAD"
            or getattr(response, "status_code", None) in REDIRECT_STATUSES
        ):
            response._content = b""
            response._content_consumed = True
            return response

        content_length = getattr(response, "headers", {}).get("Content-Length")
        if content_length:
            try:
                if int(content_length) > max_response_bytes:
                    raise PublicUrlSafetyError(
                        f"Public evidence response size exceeds {max_response_bytes} bytes."
                    )
            except ValueError:
                pass

        chunks: list[bytes] = []
        total = 0
        if hasattr(response, "iter_content"):
            for chunk in response.iter_content(chunk_size=_RESPONSE_CHUNK_BYTES):
                _remaining_seconds(deadline)
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_response_bytes:
                    raise PublicUrlSafetyError(
                        f"Public evidence response size exceeds {max_response_bytes} bytes."
                    )
                chunks.append(bytes(chunk))
            content = b"".join(chunks)
        else:
            content = bytes(getattr(response, "content", b""))
            if len(content) > max_response_bytes:
                raise PublicUrlSafetyError(
                    f"Public evidence response size exceeds {max_response_bytes} bytes."
                )

        _remaining_seconds(deadline)
        response._content = content
        response._content_consumed = True
        return response
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()


def _send_pinned_request(
    session: Any,
    method: str,
    resolved: _ResolvedPublicUrl,
    *,
    headers: Mapping[str, str] | None,
    timeout: float | tuple[float, float],
    max_response_bytes: int,
    deadline: float,
    request_kwargs: dict[str, Any],
) -> Any:
    prohibited = {"allow_redirects", "proxies", "stream"}.intersection(request_kwargs)
    if prohibited:
        names = ", ".join(sorted(prohibited))
        raise PublicUrlSafetyError(f"Pinned public requests do not accept: {names}.")

    request_fields = {
        key: request_kwargs.pop(key)
        for key in ("params", "data", "json")
        if key in request_kwargs
    }
    verify = request_kwargs.pop("verify", getattr(session, "verify", True))
    if verify is False:
        raise PublicUrlSafetyError(
            "HTTPS certificate verification cannot be disabled for public requests."
        )
    cert = request_kwargs.pop("cert", getattr(session, "cert", None))
    if request_kwargs:
        names = ", ".join(sorted(request_kwargs))
        raise TypeError(f"Unsupported pinned public request arguments: {names}")

    prepared = requests.Request(
        method=method,
        url=resolved.url,
        headers=dict(headers or {}),
        **request_fields,
    ).prepare()
    prepared.headers["Host"] = resolved.host_header

    adapter = _PinnedHTTPAdapter(
        pinned_ip=resolved.address,
        server_hostname=resolved.hostname,
        port=resolved.port,
    )
    try:
        socket_timeout = _bounded_socket_timeout(
            timeout, remaining=_remaining_seconds(deadline)
        )
        response = adapter.send(
            prepared,
            stream=True,
            timeout=socket_timeout,
            verify=verify,
            cert=cert,
            proxies={},
        )
        if not getattr(response, "url", None):
            response.url = resolved.url
        return _materialize_bounded_response(
            response,
            method=method,
            max_response_bytes=max_response_bytes,
            deadline=deadline,
        )
    finally:
        adapter.close()


def request_public_url(
    session: Any,
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT_SECONDS,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    total_timeout_seconds: float | None = None,
    resolver: Resolver = socket.getaddrinfo,
    request_guard: Callable[[str], ContextManager[Any]] | None = None,
    **request_kwargs: Any,
) -> Any:
    """Request a public URL through an IP-pinned, bounded, proxy-free transport."""
    if max_redirects < 0:
        raise ValueError("max_redirects must be non-negative")
    if max_response_bytes <= 0:
        raise ValueError("max_response_bytes must be positive")
    if total_timeout_seconds is None:
        if isinstance(timeout, tuple):
            total_timeout_seconds = sum(float(value) for value in timeout)
        else:
            total_timeout_seconds = float(timeout)
    total_timeout_seconds = float(total_timeout_seconds)
    if not math.isfinite(total_timeout_seconds) or total_timeout_seconds <= 0:
        raise ValueError("total_timeout_seconds must be finite and positive")

    deadline = time.monotonic() + total_timeout_seconds
    current = _resolve_public_url(url, resolver=resolver)
    _remaining_seconds(deadline)
    current_method = method.upper()
    for redirect_count in range(max_redirects + 1):
        guard = request_guard(current.hostname) if request_guard else nullcontext()
        with guard:
            response = _send_pinned_request(
                session,
                current_method,
                current,
                headers=headers,
                timeout=timeout,
                max_response_bytes=max_response_bytes,
                deadline=deadline,
                request_kwargs=dict(request_kwargs),
            )
        status_code = getattr(response, "status_code", None)
        location = getattr(response, "headers", {}).get("Location")
        if status_code not in REDIRECT_STATUSES or not location:
            return response
        if redirect_count >= max_redirects:
            raise PublicUrlSafetyError(
                "Public evidence URL exceeded the redirect limit."
            )
        _remaining_seconds(deadline)
        current = _resolve_public_url(urljoin(current.url, location), resolver=resolver)
        _remaining_seconds(deadline)
        if status_code == 303 and current_method != "HEAD":
            current_method = "GET"
    raise PublicUrlSafetyError("Public evidence URL exceeded the redirect limit.")
