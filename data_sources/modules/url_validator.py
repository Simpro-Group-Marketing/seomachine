"""
URL Validator

Extracts article-body URLs and verifies that each destination resolves before
optimization or publishing. This module checks that a URL exists; source-map and
proof review still decide whether the page supports the article claim.
"""

from __future__ import annotations

import argparse
import socket
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests

try:
    from .artifact_runtime.paths import cache_path
    from .public_http import URL_RESOLUTION_POLICY
    from .public_url_safety import PublicUrlSafetyError, request_public_url
    from .public_http import markdown_urls as _markdown_urls
    from .public_http.url_cache import NullUrlResolutionCache, UrlResolutionCache
except ImportError:  # pragma: no cover - supports direct script execution.
    from artifact_runtime.paths import cache_path
    from public_http import URL_RESOLUTION_POLICY
    from public_url_safety import PublicUrlSafetyError, request_public_url
    import public_http.markdown_urls as _markdown_urls
    from public_http.url_cache import NullUrlResolutionCache, UrlResolutionCache

DEFAULT_BASE_URL = _markdown_urls.DEFAULT_BASE_URL
ExtractedUrl = _markdown_urls.ExtractedUrl
extract_urls = _markdown_urls.extract_urls


DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 SEO-Machine-URL-Validator/1.0"
)
RESOLUTION_CACHE_SECONDS = 60 * 60 * 24
RESOLUTION_CACHE_FUTURE_SKEW_SECONDS = 60
RATE_LIMIT_RETRY_SECONDS = 1.0

@dataclass(frozen=True)
class UrlValidationResult:
    """Resolution status for one extracted URL."""

    url: str
    status: str
    status_code: Optional[int]
    reason: str
    line: Optional[int] = None
    anchor: str = ""
    final_url: str = ""

    @property
    def passed(self) -> bool:
        return self.status == "resolved"


class UrlValidationSummary:
    """Collection of URL validation results with blocker helpers."""

    def __init__(self, results: Iterable[UrlValidationResult]):
        self.results = list(results)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> bool:
        return not self.blockers

    @property
    def blockers(self) -> List[UrlValidationResult]:
        return [result for result in self.results if not result.passed]

    @property
    def resolved_count(self) -> int:
        return len([result for result in self.results if result.status == "resolved"])

    @property
    def unresolved_count(self) -> int:
        return len([result for result in self.results if result.status == "unresolved"])

    @property
    def manual_review_count(self) -> int:
        return len([result for result in self.results if result.status == "manual_review"])


class UrlValidator:
    """Validates URL resolution with HEAD first and GET fallback."""

    def __init__(
        self,
        session: Optional[requests.Session] = None,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        user_agent: str = DEFAULT_USER_AGENT,
        cache_dir: Optional[Path] = None,
        rate_limit_retry_seconds: float = RATE_LIMIT_RETRY_SECONDS,
        resolver=socket.getaddrinfo,
        requester=request_public_url,
        *,
        transport=None,
    ):
        if transport is not None and session is not None:
            raise ValueError("transport and session are mutually exclusive")
        self.transport = transport
        self.session = None if transport is not None else session or requests.Session()
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}
        if transport is not None or (session is not None and cache_dir is None):
            self.cache = NullUrlResolutionCache()
        else:
            self.cache = UrlResolutionCache(
                cache_dir or cache_path("url_validator"),
                result_factory=UrlValidationResult,
                expire_seconds=RESOLUTION_CACHE_SECONDS,
            )
        self.rate_limit_retry_seconds = rate_limit_retry_seconds
        self.resolver = resolver
        self.requester = requester

    def validate_url(
        self,
        url: str,
        line: Optional[int] = None,
        anchor: str = "",
    ) -> UrlValidationResult:
        cached = self.cache.get(url)
        if cached is not None:
            return _copy_context(cached, line=line, anchor=anchor)

        head = self._request("HEAD", url)
        if isinstance(head, UrlValidationResult):
            return _copy_context(head, line=line, anchor=anchor)

        if _is_resolved_status(head.status_code):
            result = UrlValidationResult(
                url=url,
                status="resolved",
                status_code=head.status_code,
                reason=f"HTTP {head.status_code}",
                line=line,
                anchor=anchor,
                final_url=getattr(head, "url", "") or url,
            )
            self.cache.set(result)
            return result

        get = self._request("GET", url)
        if isinstance(get, UrlValidationResult):
            return _copy_context(get, line=line, anchor=anchor)

        if _is_resolved_status(get.status_code):
            result = UrlValidationResult(
                url=url,
                status="resolved",
                status_code=get.status_code,
                reason=f"HTTP {get.status_code}",
                line=line,
                anchor=anchor,
                final_url=getattr(get, "url", "") or url,
            )
            self.cache.set(result)
            return result

        status_code = get.status_code
        final_url = getattr(get, "url", "") or url

        status = _status_for_http_code(status_code)
        return UrlValidationResult(
            url=url,
            status=status,
            status_code=status_code,
            reason=f"HTTP {status_code}",
            line=line,
            anchor=anchor,
            final_url=final_url,
        )

    def validate_many(self, urls: Iterable[str]) -> list[UrlValidationResult]:
        """Validate unique URLs in two stable HEAD-then-GET batch phases."""
        ordered = list(urls)
        unique = list(dict.fromkeys(ordered))
        resolved = self._cached_results(unique)
        uncached = [url for url in unique if url not in resolved]
        heads = dict(zip(uncached, self._request_many("HEAD", uncached)))
        fallback = [
            url
            for url in uncached
            if not isinstance(heads[url], UrlValidationResult)
            and not _is_resolved_status(heads[url].status_code)
        ]
        gets = dict(zip(fallback, self._request_many("GET", fallback)))
        for url in uncached:
            resolved[url] = self._result_from_phases(url, heads[url], gets.get(url))
        return [_copy_context(resolved[url], line=None, anchor="") for url in ordered]

    def _cached_results(self, urls: Iterable[str]) -> dict[str, UrlValidationResult]:
        values: dict[str, UrlValidationResult] = {}
        for url in urls:
            cached = self.cache.get(url)
            if cached is not None:
                values[url] = cached
        return values

    def _request_many(self, method: str, urls: list[str]) -> list[object]:
        if not urls:
            return []
        if self.transport is None:
            return [self._request(method, url) for url in urls]
        responses = self.transport.request_many(
            method,
            urls,
            headers=self.headers,
            policy=URL_RESOLUTION_POLICY,
        )
        return [
            self._retry_rate_limited(method, url, response)
            for url, response in zip(urls, responses)
        ]

    def _retry_rate_limited(self, method: str, url: str, response: object) -> object:
        if getattr(response, "status_code", None) != 429:
            return response
        self._sleep_after_rate_limit(response)
        return self._request(method, url)

    def _result_from_phases(
        self,
        url: str,
        head: object,
        get: object | None,
    ) -> UrlValidationResult:
        outcome = head if get is None else get
        if isinstance(outcome, UrlValidationResult):
            return outcome
        status_code = int(outcome.status_code)
        result = UrlValidationResult(
            url=url,
            status=_status_for_http_code(status_code),
            status_code=status_code,
            reason=f"HTTP {status_code}",
            final_url=getattr(outcome, "url", "") or url,
        )
        if result.passed:
            self.cache.set(result)
        return result

    def _request(self, method: str, url: str):
        try:
            response = self._send(method, url)
            if getattr(response, "status_code", None) == 429:
                self._sleep_after_rate_limit(response)
                response = self._send(method, url)
            return response
        except (requests.exceptions.RequestException, PublicUrlSafetyError) as exc:
            return UrlValidationResult(
                url=url,
                status="unresolved",
                status_code=None,
                reason=str(exc),
            )

    def _send(self, method: str, url: str):
        if self.transport is not None:
            return self.transport.request(
                method,
                url,
                headers=self.headers,
                policy=URL_RESOLUTION_POLICY,
            )
        return self.requester(
            self.session,
            method,
            url,
            timeout=self.timeout,
            headers=self.headers,
            resolver=self.resolver,
        )

    def _sleep_after_rate_limit(self, response) -> None:
        retry_after = getattr(response, "headers", {}).get("Retry-After")
        delay = self.rate_limit_retry_seconds
        if retry_after:
            try:
                delay = min(float(retry_after), max(self.rate_limit_retry_seconds, 5.0))
            except ValueError:
                delay = self.rate_limit_retry_seconds
        if delay > 0:
            time.sleep(delay)


def validate_content_urls(
    content: str,
    validator: Optional[UrlValidator] = None,
    base_url: str = DEFAULT_BASE_URL,
) -> UrlValidationSummary:
    """Validate all URLs in a content string."""
    validator = validator or UrlValidator()
    extracted_urls = extract_urls(content, base_url=base_url)
    validated = validator.validate_many(item.url for item in extracted_urls)
    results = [
        _copy_context(result, line=item.line, anchor=item.anchor)
        for item, result in zip(extracted_urls, validated)
    ]
    return UrlValidationSummary(results)


def validate_file_urls(
    path: str | Path,
    validator: Optional[UrlValidator] = None,
    base_url: str = DEFAULT_BASE_URL,
) -> UrlValidationSummary:
    """Validate all URLs in a Markdown file."""
    content = Path(path).read_text(encoding="utf-8")
    return validate_content_urls(content, validator=validator, base_url=base_url)


def format_summary(summary: UrlValidationSummary) -> str:
    """Format validation results for CLI and preflight errors."""
    lines = [
        "=== URL Validation Report ===",
        f"Total URLs: {summary.total}",
        f"Resolved: {summary.resolved_count}",
        f"Unresolved: {summary.unresolved_count}",
        f"Manual review: {summary.manual_review_count}",
    ]

    if summary.blockers:
        lines.append("")
        lines.append("Blockers:")
        for result in summary.blockers:
            location = f"line {result.line}: " if result.line else ""
            anchor = f" [{result.anchor}]" if result.anchor else ""
            code = f"HTTP {result.status_code}" if result.status_code is not None else result.reason
            blocker = f"  - {location}{result.url}{anchor} ({result.status}: {code})"
            if result.status == "manual_review":
                blocker += (
                    " Replace this source with an equivalent resolved public source "
                    "or remove the supported claim. Do not remove the citation without "
                    "replacing it with a resolved source supporting the same claim."
                )
            lines.append(blocker)

    return "\n".join(lines)


def require_valid_urls(path: str | Path, context: str = "publish") -> UrlValidationSummary:
    """Raise ValueError if a file contains unresolved or manual-review URLs."""
    summary = validate_file_urls(path)
    if not summary.passed:
        raise ValueError(f"URL validation failed before {context}:\n{format_summary(summary)}")
    return summary


def _is_resolved_status(status_code: int) -> bool:
    return 200 <= status_code < 400


def _status_for_http_code(status_code: int) -> str:
    if _is_resolved_status(status_code):
        return "resolved"
    if status_code in {401, 403}:
        return "manual_review"
    return "unresolved"


def _copy_context(
    result: UrlValidationResult,
    line: Optional[int],
    anchor: str,
) -> UrlValidationResult:
    return UrlValidationResult(
        url=result.url,
        status=result.status,
        status_code=result.status_code,
        reason=result.reason,
        line=line,
        anchor=anchor,
        final_url=result.final_url,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate article URLs resolve before publish.")
    parser.add_argument("path", help="Markdown file to validate.")
    parser.add_argument(
        "--fail-on",
        choices=["none", "unresolved"],
        default="unresolved",
        help="Exit non-zero when unresolved/manual-review URLs are found.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL used to resolve relative Simpro links.",
    )
    args = parser.parse_args(argv)

    summary = validate_file_urls(
        args.path,
        validator=UrlValidator(timeout=args.timeout),
        base_url=args.base_url,
    )
    print(format_summary(summary))

    if args.fail_on == "unresolved" and not summary.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
