"""Safe typed transport for bounded, unauthenticated public HTTP."""

from __future__ import annotations

import hashlib
import json
import socket
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests

try:
    from ..artifact_runtime.paths import cache_path
    from ..artifact_runtime.limits import HTTP_MEMO_MAX_BYTES
    from ..public_url_safety import request_public_url, validate_public_url_syntax
except ImportError:  # pragma: no cover - supports direct module-path execution.
    from artifact_runtime.paths import cache_path
    from artifact_runtime.limits import HTTP_MEMO_MAX_BYTES
    from public_url_safety import request_public_url, validate_public_url_syntax
from .cache import ResponseCache, ResponseMemoryCache
from .batch import HttpBatchPolicy, Observer, execute_many, resolve_batch_policy
from .policies import (
    MAX_CACHE_BYTES,
    MAX_PER_HOST,
    MAX_WORKERS,
    TRANSPORT_VERSION,
    HttpRequestPolicy,
    URL_RESOLUTION_POLICY,
)
from .snapshot import ResponseSnapshot


SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})


@dataclass(slots=True)
class _Gate:
    semaphore: threading.BoundedSemaphore
    users: int = 0


class PublicHttpTransport:
    """Share bounded public HTTP work within one workflow."""

    def __init__(
        self,
        *,
        cache_dir: str | Path | None = None,
        persistent_cache: bool = True,
        requester=request_public_url,
        resolver=socket.getaddrinfo,
        max_workers: int = MAX_WORKERS,
        max_per_host: int = MAX_PER_HOST,
        batch_policy: HttpBatchPolicy | None = None,
        observer: Observer | None = None,
        memo_max_bytes: int = HTTP_MEMO_MAX_BYTES,
    ) -> None:
        resolved_batch = resolve_batch_policy(
            batch_policy,
            max_workers=max_workers,
            max_per_host=max_per_host,
        )
        if observer is not None and not callable(observer):
            raise ValueError("observer must be callable")
        self._requester = requester
        self._resolver = resolver
        self._batch_policy = resolved_batch
        self._observer = observer
        self._max_workers = resolved_batch.max_workers
        self._global_limit = threading.BoundedSemaphore(resolved_batch.max_workers)
        self._max_per_host = resolved_batch.max_per_host
        self._host_limits: dict[str, _Gate] = {}
        self._memo = ResponseMemoryCache(
            max_bytes=memo_max_bytes,
            observer=lambda amount: self._observe("memo_bytes_delta", amount),
        )
        self._flights: dict[str, _Gate] = {}
        self._sessions: list[requests.Session] = []
        self._local = threading.local()
        self._lock = threading.RLock()
        self._closed = False
        self._counts = {"requests": 0, "cache_hits": 0, "cache_misses": 0}
        self._cache = (
            ResponseCache(
                Path(cache_dir) if cache_dir is not None else cache_path("public_http", "v2"),
                size_limit=MAX_CACHE_BYTES,
            )
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

    @property
    def batch_policy(self) -> HttpBatchPolicy:
        return self._batch_policy

    @property
    def reports_events(self) -> bool:
        """Return whether lifecycle telemetry is emitted directly."""
        return self._observer is not None

    def request(
        self,
        method: str,
        url: str,
        *,
        policy: HttpRequestPolicy = URL_RESOLUTION_POLICY,
        headers: Mapping[str, str] | None = None,
        body: bytes | str | None = None,
    ) -> requests.Response:
        self._require_open()
        if not isinstance(policy, HttpRequestPolicy):
            raise ValueError("HTTP request requires a declared typed policy")
        normalized_method = method.upper()
        if normalized_method not in policy.allowed_methods:
            raise ValueError("HTTP method is not allowed by policy")
        if body is not None:
            raise ValueError("public HTTP request body is prohibited")
        normalized_headers = _normalize_headers(headers, policy=policy)
        validate_public_url_syntax(url)
        canonical = _canonical_url(url)
        key = _request_key(normalized_method, canonical, normalized_headers, policy)
        with self._single_flight(key):
            snapshot = self._lookup(key, policy=policy)
            if snapshot is not None:
                return snapshot.response()
            if self._cache is None:
                return self._request_miss(key, normalized_method, url, normalized_headers, policy)
            with self._cache.lock(key) as cache_locked:
                if cache_locked:
                    snapshot = self._lookup(key, policy=policy)
                    if snapshot is not None:
                        return snapshot.response()
                return self._request_miss(
                    key,
                    normalized_method,
                    url,
                    normalized_headers,
                    policy,
                    allow_persist=cache_locked,
                )

    def request_many(
        self,
        method: str,
        urls: Iterable[str],
        *,
        policy: HttpRequestPolicy = URL_RESOLUTION_POLICY,
        headers: Mapping[str, str] | None = None,
    ) -> list[requests.Response]:
        self._require_open()
        return execute_many(
            method,
            urls,
            request=self.request,
            key_for=_canonical_url,
            host_for=_request_host,
            request_policy=policy,
            batch_policy=self._batch_policy,
            headers=headers,
            observer=self._observe,
        )

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            sessions = tuple(self._sessions)
            self._sessions.clear()
            self._memo.clear()
            self._flights.clear()
            self._host_limits.clear()
        for session in sessions:
            session.close()
        if self._cache is not None:
            self._cache.close()

    def _lookup(
        self,
        key: str,
        *,
        policy: HttpRequestPolicy,
    ) -> ResponseSnapshot | None:
        existing = self._memo.get(key)
        if existing is not None:
            self._increment("cache_hits")
            return existing
        if self._cache is None:
            return None
        value = self._cache.get(key)
        if value is None:
            return None
        digest = _policy_digest(policy)
        snapshot = ResponseSnapshot.from_value(
            value,
            policy=policy,
            policy_digest=digest,
        )
        if snapshot is None:
            self._cache.delete(key)
            return None
        self._memo.set(key, snapshot, weight=_snapshot_weight(snapshot))
        self._increment("cache_hits")
        return snapshot

    def _request_miss(
        self,
        key: str,
        method: str,
        url: str,
        headers: Mapping[str, str],
        policy: HttpRequestPolicy,
        allow_persist: bool = True,
    ) -> requests.Response:
        self._increment("cache_misses")
        self._observe("in_flight_requests_delta", 1)
        try:
            response = self._requester(
                self._session(),
                method,
                url,
                headers=headers or None,
                timeout=(policy.connect_timeout, policy.read_timeout),
                max_redirects=policy.redirect_limit,
                max_response_bytes=policy.max_response_bytes,
                total_timeout_seconds=policy.total_deadline,
                resolver=self._resolve,
                request_guard=self._request_guard,
            )
            snapshot = ResponseSnapshot.capture(response, policy=policy)
        except Exception:
            self._increment("requests")
            raise
        finally:
            self._observe("in_flight_requests_delta", -1)
        self._increment("requests")
        self._observe("response_bytes", len(snapshot.body))
        if policy.ttl_for(snapshot.status_code) is not None:
            self._memo.set(key, snapshot, weight=_snapshot_weight(snapshot))
            if allow_persist:
                self._persist(key, snapshot, policy=policy)
        return snapshot.response()

    def _persist(
        self,
        key: str,
        snapshot: ResponseSnapshot,
        *,
        policy: HttpRequestPolicy,
    ) -> None:
        ttl = policy.ttl_for(snapshot.status_code)
        if ttl is None or self._cache is None:
            return
        digest = _policy_digest(policy)
        self._cache.set(
            key,
            snapshot.persistent_value(policy_digest=digest),
            ttl=ttl,
        )

    @contextmanager
    def _single_flight(self, key: str) -> Iterator[None]:
        with self._lock:
            gate = self._flights.get(key)
            if gate is None:
                gate = _Gate(threading.BoundedSemaphore(1))
                self._flights[key] = gate
            gate.users += 1
        gate.semaphore.acquire()
        try:
            yield
        finally:
            gate.semaphore.release()
            with self._lock:
                gate.users -= 1
                if gate.users == 0 and self._flights.get(key) is gate:
                    self._flights.pop(key, None)

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
            with self._lock:
                self._sessions.append(session)
        return session

    def _resolve(self, hostname: str, port: int, *args: object, **kwargs: object):
        self._observe("dns_resolution", 1)
        return self._resolver(hostname, port, *args, **kwargs)

    @contextmanager
    def _request_guard(self, hostname: str) -> Iterator[None]:
        key = hostname.rstrip(".").casefold()
        with self._lock:
            gate = self._host_limits.get(key)
            if gate is None:
                gate = _Gate(threading.BoundedSemaphore(self._max_per_host))
                self._host_limits[key] = gate
            gate.users += 1
        self._global_limit.acquire()
        gate.semaphore.acquire()
        try:
            yield
        finally:
            gate.semaphore.release()
            self._global_limit.release()
            with self._lock:
                gate.users -= 1
                if gate.users == 0 and self._host_limits.get(key) is gate:
                    self._host_limits.pop(key, None)

    def _increment(self, name: str) -> None:
        with self._lock:
            self._counts[name] += 1
        self._observe(name, 1)

    def _observe(self, name: str, amount: int) -> None:
        observer = self._observer
        if observer is None:
            return
        try:
            observer(name, amount)
        except Exception:
            return

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


def _request_host(url: str) -> str:
    return (urlsplit(url).hostname or "").rstrip(".").casefold()


def _normalize_headers(
    headers: Mapping[str, str] | None,
    *,
    policy: HttpRequestPolicy,
) -> dict[str, str]:
    normalized = {str(name).casefold(): str(value) for name, value in (headers or {}).items()}
    names = set(normalized)
    if names.intersection(SENSITIVE_HEADERS):
        raise ValueError("credential and cookie headers are prohibited")
    undeclared = names.difference(policy.vary_headers)
    if undeclared:
        raise ValueError(f"HTTP header is not declared by policy: {sorted(undeclared)[0]}")
    return dict(sorted(normalized.items()))


def _policy_digest(policy: HttpRequestPolicy) -> str:
    serialized = json.dumps(
        policy.canonical_value(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _snapshot_weight(snapshot: ResponseSnapshot) -> int:
    return (
        len(snapshot.body)
        + len(snapshot.content_type.encode("utf-8"))
        + len(snapshot.final_url.encode("utf-8"))
    )


def _request_key(
    method: str,
    canonical_url: str,
    headers: Mapping[str, str] | None,
    policy: HttpRequestPolicy,
) -> str:
    payload = {
        "transport_version": TRANSPORT_VERSION,
        "policy": policy.canonical_value(),
        "method": method.upper(),
        "url": canonical_url,
        "headers": sorted((headers or {}).items()),
    }
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def canonical_request_identity(
    method: str,
    url: str,
    *,
    headers: Mapping[str, str] | None,
    policy: HttpRequestPolicy,
) -> str:
    """Return the complete typed identity used by transport and derived caches."""
    if not isinstance(policy, HttpRequestPolicy):
        raise ValueError("HTTP request identity requires a declared typed policy")
    normalized_method = method.upper()
    if normalized_method not in policy.allowed_methods:
        raise ValueError("HTTP method is not allowed by policy")
    normalized_headers = _normalize_headers(headers, policy=policy)
    return _request_key(
        normalized_method,
        _canonical_url(url),
        normalized_headers,
        policy,
    )
