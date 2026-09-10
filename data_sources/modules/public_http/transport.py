"""Safe, bounded, run-scoped transport for unauthenticated public HTTP."""

from __future__ import annotations

import hashlib
import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests

try:
    from ..public_url_safety import request_public_url, validate_public_url
except ImportError:  # pragma: no cover - supports direct module-path execution.
    from public_url_safety import request_public_url, validate_public_url
from .cache import ResponseCache
from .policies import (
    MAX_CACHE_BYTES,
    MAX_PER_HOST,
    MAX_WORKERS,
    POLICY_VERSION,
    persistent_ttl,
)


@dataclass(frozen=True)
class _ResponseSnapshot:
    status_code: int
    body: bytes
    content_type: str
    final_url: str

    @classmethod
    def capture(cls, response: Any) -> "_ResponseSnapshot":
        return cls(
            status_code=int(response.status_code),
            body=bytes(getattr(response, "content", b"")),
            content_type=str(getattr(response, "headers", {}).get("Content-Type", "")),
            final_url=str(getattr(response, "url", "")),
        )

    def response(self) -> requests.Response:
        response = requests.Response()
        response.status_code = self.status_code
        response._content = self.body
        response._content_consumed = True
        response.url = self.final_url
        if self.content_type:
            response.headers["Content-Type"] = self.content_type
        return response

    def persistent_value(self) -> dict[str, Any]:
        return {
            "schema": "simpro-public-http-cache/v1",
            "status_code": self.status_code,
            "body": self.body,
            "content_type": self.content_type,
            "final_url": self.final_url,
        }

    @classmethod
    def from_value(cls, value: Mapping[str, Any]) -> "_ResponseSnapshot" | None:
        if value.get("schema") != "simpro-public-http-cache/v1":
            return None
        status = value.get("status_code")
        body = value.get("body")
        content_type = value.get("content_type")
        final_url = value.get("final_url")
        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not isinstance(body, bytes)
            or not isinstance(content_type, str)
            or not isinstance(final_url, str)
        ):
            return None
        return cls(status, body, content_type, final_url)


class PublicHttpTransport:
    """Share public HTTP work within one workflow and close every resource."""

    def __init__(
        self,
        *,
        cache_dir: str | Path = Path(".cache") / "public_http" / "v1",
        persistent_cache: bool = True,
        requester=request_public_url,
        resolver=socket.getaddrinfo,
        max_workers: int = MAX_WORKERS,
        max_per_host: int = MAX_PER_HOST,
    ) -> None:
        self._requester = requester
        self._resolver = resolver
        self._max_workers = max_workers
        self._global_limit = threading.BoundedSemaphore(max_workers)
        self._max_per_host = max_per_host
        self._host_limits: dict[str, threading.BoundedSemaphore] = {}
        self._memo: dict[str, _ResponseSnapshot | BaseException] = {}
        self._flights: dict[str, threading.Lock] = {}
        self._sessions: list[requests.Session] = []
        self._local = threading.local()
        self._lock = threading.RLock()
        self._closed = False
        self._counts = {"requests": 0, "cache_hits": 0, "cache_misses": 0}
        self._cache = (
            ResponseCache(Path(cache_dir), size_limit=MAX_CACHE_BYTES)
            if persistent_cache
            else None
        )

    def __enter__(self) -> "PublicHttpTransport":
        self._require_open()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    @property
    def counters(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        response_profile: str = "default",
        **request_kwargs: Any,
    ) -> requests.Response:
        self._require_open()
        validate_public_url(url, resolver=self._resolver)
        canonical = _canonical_url(url)
        key = _request_key(method, canonical, headers, response_profile)
        flight = self._flight(key)
        with flight:
            snapshot = self._lookup(key, persistent=_persistable(url, headers))
            if snapshot is not None:
                return snapshot.response()
            if self._cache is None or not _persistable(url, headers):
                return self._request_miss(
                    key, method, url, headers, request_kwargs
                )
            with self._cache.lock(key):
                snapshot = self._lookup(key, persistent=True)
                if snapshot is not None:
                    return snapshot.response()
                return self._request_miss(
                    key, method, url, headers, request_kwargs
                )

    def request_many(
        self,
        method: str,
        urls: Iterable[str],
        **request_kwargs: Any,
    ) -> list[requests.Response]:
        ordered = list(urls)
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [
                executor.submit(self.request, method, url, **request_kwargs)
                for url in ordered
            ]
            return [future.result() for future in futures]

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            sessions = tuple(self._sessions)
            self._sessions.clear()
        for session in sessions:
            session.close()
        if self._cache is not None:
            self._cache.close()

    def _lookup(self, key: str, *, persistent: bool) -> _ResponseSnapshot | None:
        existing = self._memo.get(key)
        if isinstance(existing, BaseException):
            self._increment("cache_hits")
            raise existing
        if existing is not None:
            self._increment("cache_hits")
            return existing
        if not persistent or self._cache is None:
            return None
        value = self._cache.get(key)
        if value is None:
            return None
        snapshot = _ResponseSnapshot.from_value(value)
        if snapshot is None:
            self._cache.delete(key)
            return None
        self._memo[key] = snapshot
        self._increment("cache_hits")
        return snapshot

    def _request_miss(
        self,
        key: str,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
        request_kwargs: Mapping[str, Any],
    ) -> requests.Response:
        self._increment("cache_misses")
        try:
            response = self._requester(
                self._session(),
                method.upper(),
                url,
                headers=headers,
                resolver=self._resolver,
                request_guard=self._request_guard,
                **dict(request_kwargs),
            )
            self._increment("requests")
            snapshot = _ResponseSnapshot.capture(response)
            self._memo[key] = snapshot
            eligible = _persistable_response(url, headers, snapshot)
            self._persist(key, snapshot, eligible=eligible)
            return snapshot.response()
        except BaseException as error:
            self._increment("requests")
            self._memo[key] = error
            raise

    def _persist(self, key: str, snapshot: _ResponseSnapshot, *, eligible: bool) -> None:
        ttl = persistent_ttl(snapshot.status_code)
        if not eligible or ttl is None or self._cache is None:
            return
        self._cache.set(key, snapshot.persistent_value(), ttl=ttl)

    def _flight(self, key: str) -> threading.Lock:
        with self._lock:
            return self._flights.setdefault(key, threading.Lock())

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
            with self._lock:
                self._sessions.append(session)
        return session

    @contextmanager
    def _request_guard(self, hostname: str):
        key = hostname.rstrip(".").casefold()
        with self._lock:
            host_limit = self._host_limits.setdefault(
                key, threading.BoundedSemaphore(self._max_per_host)
            )
        with self._global_limit, host_limit:
            yield

    def _increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1

    def _require_open(self) -> None:
        if self._closed:
            raise RuntimeError("PublicHttpTransport is closed")


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    scheme = parsed.scheme.casefold()
    hostname = (parsed.hostname or "").rstrip(".").casefold()
    port = parsed.port
    default = (scheme == "https" and port == 443) or (scheme == "http" and port == 80)
    authority = hostname if port is None or default else f"{hostname}:{port}"
    return urlunsplit((scheme, authority, parsed.path or "/", parsed.query, ""))


def _request_key(
    method: str,
    canonical_url: str,
    headers: Mapping[str, str] | None,
    response_profile: str,
) -> str:
    normalized_headers = sorted(
        (str(name).casefold(), str(value)) for name, value in (headers or {}).items()
    )
    payload = json.dumps(
        [POLICY_VERSION, method.upper(), canonical_url, response_profile, normalized_headers],
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _persistable(url: str, headers: Mapping[str, str] | None) -> bool:
    names = {str(name).casefold() for name in (headers or {})}
    return not urlsplit(url).query and not names.intersection({"authorization", "cookie"})


def _persistable_response(
    url: str,
    headers: Mapping[str, str] | None,
    snapshot: _ResponseSnapshot,
) -> bool:
    return _persistable(url, headers) and not urlsplit(snapshot.final_url).query
