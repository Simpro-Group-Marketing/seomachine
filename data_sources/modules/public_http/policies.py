"""Cache and concurrency policy for public HTTP requests."""

from __future__ import annotations


POLICY_VERSION = "public-http/v1"
SUCCESS_TTL_SECONDS = 24 * 60 * 60
NOT_FOUND_TTL_SECONDS = 15 * 60
AUTH_TTL_SECONDS = 5 * 60
MAX_CACHE_BYTES = 256 * 1024 * 1024
MAX_WORKERS = 8
MAX_PER_HOST = 2


def persistent_ttl(status_code: int) -> int | None:
    if 200 <= status_code < 400:
        return SUCCESS_TTL_SECONDS
    if status_code in {404, 410}:
        return NOT_FOUND_TTL_SECONDS
    if status_code in {401, 403}:
        return AUTH_TTL_SECONDS
    return None
