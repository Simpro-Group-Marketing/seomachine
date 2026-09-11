"""Safe typed transport for bounded, unauthenticated public HTTP."""

from __future__ import annotations

import hashlib
import json
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping
from urllib.parse import urlsplit, urlunsplit

import requests

try:
    from ..artifact_runtime.paths import cache_path
    from ..public_url_safety import request_public_url, validate_public_url
except ImportError:  # pragma: no cover - supports direct module-path execution.
    from artifact_runtime.paths import cache_path
    from public_url_safety import request_public_url, validate_public_url
from .cache import ResponseCache
from .policies import (
    MAX_CACHE_BYTES,
    MAX_PER_HOST,
    MAX_WORKERS,
    TRANSIENT_STATUSES,
    TRANSPORT_VERSION,
    HttpRequestPolicy,
    URL_RESOLUTION_POLICY,
)


CACHE_SCHEMA = "simpro-public-http-cache/v2"
SENSITIVE_HEADERS = frozenset({"authorization", "cookie", "proxy-authorization"})


@dataclass(frozen=True, slots=True)
class _ResponseSnapshot:
    status_code: int
    body: bytes
    content_type: str
    final_url: str

    @classmethod
    def capture(
        cls,
        response: Any,
        *,
        policy: HttpRequestPolicy,
    ) -> "_ResponseSnapshot":
        snapshot = cls(
            status_code=int(response.status_code),
            body=bytes(getattr(response, "content", b"")),
            content_type=str(getattr(response, "headers", {}).get("Content-Type", "")),
            final_url=str(getattr(response, "url", "")),
        )
        snapshot.validate(policy)
        return snapshot

    def validate(self, policy: HttpRequestPolicy) -> None:
        if len(self.body) > policy.max_response_bytes:
            raise ValueError("public HTTP response exceeds policy byte limit")
        mime = self.content_type.partition(";")[0].strip().casefold()
        accepted = {value.casefold() for value in policy.accepted_mime_types}
        if "*/*" not in accepted and mime not in accepted:
            raise ValueError("public HTTP response MIME type is not accepted by policy")

    def response(self) -> requests.Response:
        response = requests.Response()
        response.status_code = self.status_code
        response._content = self.body
        response._content_consumed = True
        response.url = self.final_url
        if self.content_type:
            response.headers["Content-Type"] = self.content_type
        return response

    def persistent_value(self, *, policy_digest: str) -> dict[str, Any]:
        return {
            "schema": CACHE_SCHEMA,
            "policy_digest": policy_digest,
            "status_code": self.status_code,
            "body": self.body,
            "body_digest": hashlib.sha256(self.body).hexdigest(),
            "byte_count": len(self.body),
            "content_type": self.content_type,
            "final_url": self.final_url,
        }

    @classmethod
    def from_value(
        cls,
        value: Mapping[str, Any],
        *,
        policy: HttpRequestPolicy,
        policy_digest: str,
    ) -> "_ResponseSnapshot" | None:
        expected = {
            "schema", "policy_digest", "status_code", "body", "body_digest",
            "byte_count", "content_type", "final_url",
        }
        if set(value) != expected or value.get("schema") != CACHE_SCHEMA:
            return None
        status = value.get("status_code")
        body = value.get("body")
        if (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not isinstance(body, bytes)
            or not isinstance(value.get("content_type"), str)
            or not isinstance(value.get("final_url"), str)
            or value.get("policy_digest") != policy_digest
            or value.get("byte_count") != len(body)
            or value.get("body_digest") != hashlib.sha256(body).hexdigest()
        ):
            return None
        snapshot = cls(status, body, str(value["content_type"]), str(value["final_url"]))
        try:
            snapshot.validate(policy)
        except ValueError:
            return None
        return snapshot


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
    ) -> None:
        if isinstance(max_workers, bool) or not isinstance(max_workers, int) or max_workers < 1:
            raise ValueError("max_workers must be a positive integer")
        if (
            isinstance(max_per_host, bool)
            or not isinstance(max_per_host, int)
            or max_per_host < 1
            or max_per_host > max_workers
        ):
            raise ValueError("max_per_host must be between one and max_workers")
        self._requester = requester
        self._resolver = resolver
        self._max_workers = max_workers
        self._global_limit = threading.BoundedSemaphore(max_workers)
        self._max_per_host = max_per_host
        self._host_limits: dict[str, _Gate] = {}
        self._memo: dict[str, _ResponseSnapshot] = {}
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
        validate_public_url(url, resolver=self._resolver)
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
        ordered = list(urls)
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = [
                executor.submit(self.request, method, url, policy=policy, headers=headers)
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
    ) -> _ResponseSnapshot | None:
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
        snapshot = _ResponseSnapshot.from_value(
            value,
            policy=policy,
            policy_digest=digest,
        )
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
        headers: Mapping[str, str],
        policy: HttpRequestPolicy,
        allow_persist: bool = True,
    ) -> requests.Response:
        self._increment("cache_misses")
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
                resolver=self._resolver,
                request_guard=self._request_guard,
            )
            snapshot = _ResponseSnapshot.capture(response, policy=policy)
        except Exception:
            self._increment("requests")
            raise
        self._increment("requests")
        if policy.ttl_for(snapshot.status_code) is not None:
            self._memo[key] = snapshot
            if allow_persist:
                self._persist(key, snapshot, policy=policy)
        return snapshot.response()

    def _persist(
        self,
        key: str,
        snapshot: _ResponseSnapshot,
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
