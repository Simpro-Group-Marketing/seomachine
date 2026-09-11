"""Typed request and cache policy for unauthenticated public HTTP."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


TRANSPORT_VERSION = "public-http/v2"
MAX_CACHE_BYTES = 256 * 1024 * 1024
MAX_WORKERS = 8
MAX_PER_HOST = 2
TRANSIENT_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


@dataclass(frozen=True, slots=True)
class HttpRequestPolicy:
    profile_id: str
    policy_version: str
    allowed_methods: tuple[str, ...]
    connect_timeout: float
    read_timeout: float
    total_deadline: float
    redirect_limit: int
    max_response_bytes: int
    accepted_mime_types: tuple[str, ...]
    retryable_statuses: frozenset[int]
    positive_ttl_seconds: int
    stable_negative_ttls: tuple[tuple[int, int], ...]
    vary_headers: tuple[str, ...]

    def __post_init__(self) -> None:
        methods = _validate_identity_and_methods(self)
        _validate_limits(self)
        _validate_cache_policy(self)
        normalized_headers = _validate_vary_headers(self.vary_headers)
        object.__setattr__(self, "allowed_methods", methods)
        object.__setattr__(self, "vary_headers", normalized_headers)

    def canonical_value(self) -> dict[str, Any]:
        value = asdict(self)
        value["retryable_statuses"] = sorted(self.retryable_statuses)
        value["stable_negative_ttls"] = [list(row) for row in self.stable_negative_ttls]
        return value

    def ttl_for(self, status_code: int) -> int | None:
        if 200 <= status_code < 400:
            return self.positive_ttl_seconds
        return dict(self.stable_negative_ttls).get(status_code)


def _validate_identity_and_methods(policy: HttpRequestPolicy) -> tuple[str, ...]:
    methods = tuple(method.upper() for method in policy.allowed_methods)
    if not policy.profile_id or not policy.policy_version:
        raise ValueError("HTTP policy identity must be non-empty")
    if not methods or any(method not in {"GET", "HEAD"} for method in methods):
        raise ValueError("HTTP policy methods must contain only GET or HEAD")
    if len(set(methods)) != len(methods):
        raise ValueError("HTTP policy methods must be distinct")
    return methods


def _validate_limits(policy: HttpRequestPolicy) -> None:
    for value in (policy.connect_timeout, policy.read_timeout, policy.total_deadline):
        if not math.isfinite(value) or value <= 0:
            raise ValueError("HTTP policy deadlines must be finite and positive")
    if policy.redirect_limit < 0 or policy.max_response_bytes < 1:
        raise ValueError("HTTP policy limits are invalid")


def _validate_cache_policy(policy: HttpRequestPolicy) -> None:
    if policy.positive_ttl_seconds < 1:
        raise ValueError("HTTP positive TTL must be positive")
    negative = dict(policy.stable_negative_ttls)
    if len(negative) != len(policy.stable_negative_ttls):
        raise ValueError("HTTP stable-negative statuses must be distinct")
    if any(status in TRANSIENT_STATUSES or ttl < 1 for status, ttl in negative.items()):
        raise ValueError("HTTP stable-negative policy includes a retryable status")
    if policy.retryable_statuses != TRANSIENT_STATUSES:
        raise ValueError("HTTP retryable statuses must match the transport contract")


def _validate_vary_headers(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = tuple(name.casefold() for name in values)
    if len(set(normalized)) != len(normalized):
        raise ValueError("HTTP vary headers must be distinct")
    return normalized


def _policy(
    profile_id: str,
    *,
    max_response_bytes: int,
    accepted_mime_types: tuple[str, ...],
) -> HttpRequestPolicy:
    return HttpRequestPolicy(
        profile_id=profile_id,
        policy_version="1",
        allowed_methods=("GET", "HEAD"),
        connect_timeout=5.0,
        read_timeout=15.0,
        total_deadline=30.0,
        redirect_limit=5,
        max_response_bytes=max_response_bytes,
        accepted_mime_types=accepted_mime_types,
        retryable_statuses=TRANSIENT_STATUSES,
        positive_ttl_seconds=24 * 60 * 60,
        stable_negative_ttls=((401, 300), (403, 300), (404, 900), (410, 900)),
        vary_headers=("accept", "user-agent"),
    )


URL_RESOLUTION_POLICY = _policy(
    "url-resolution",
    max_response_bytes=2 * 1024 * 1024,
    accepted_mime_types=("*/*",),
)
SOURCE_VISIBLE_TEXT_POLICY = _policy(
    "source-visible-text",
    max_response_bytes=4 * 1024 * 1024,
    accepted_mime_types=("text/html", "text/plain", "application/xhtml+xml"),
)
COMPETITOR_CONTENT_POLICY = _policy(
    "competitor-content",
    max_response_bytes=4 * 1024 * 1024,
    accepted_mime_types=("text/html", "text/plain", "application/xhtml+xml"),
)

NAMED_POLICIES = {
    policy.profile_id: policy
    for policy in (
        URL_RESOLUTION_POLICY,
        SOURCE_VISIBLE_TEXT_POLICY,
        COMPETITOR_CONTENT_POLICY,
    )
}
