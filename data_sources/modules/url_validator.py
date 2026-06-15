"""
URL Validator

Extracts article-body URLs and verifies that each destination resolves before
optimization or publishing. This module checks that a URL exists; source-map and
proof review still decide whether the page supports the article claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional
from urllib.parse import urljoin, urlparse

import requests


DEFAULT_BASE_URL = "https://www.simprogroup.com"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36 SEO-Machine-URL-Validator/1.0"
)
RESOLUTION_CACHE_SECONDS = 60 * 60 * 24
RATE_LIMIT_RETRY_SECONDS = 1.0

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]+\)")
BARE_URL_RE = re.compile(r"https?://[^\s<>\]\"')]+")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FRONTMATTER_RE = re.compile(r"\A---\s*\n.*?\n---\s*", re.DOTALL)

SKIPPED_SCHEMES = {"mailto", "tel"}


@dataclass(frozen=True)
class ExtractedUrl:
    """A URL found in article content."""

    url: str
    line: int
    source: str
    anchor: str = ""
    raw_url: str = ""


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
    ):
        self.session = session or requests.Session()
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}
        if session is not None and cache_dir is None:
            self.cache = _NullUrlResolutionCache()
        else:
            self.cache = _UrlResolutionCache(cache_dir or Path(".cache") / "url_validator")
        self.rate_limit_retry_seconds = rate_limit_retry_seconds

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

    def _request(self, method: str, url: str):
        try:
            response = self.session.request(
                method,
                url,
                allow_redirects=True,
                timeout=self.timeout,
                headers=self.headers,
            )
            if getattr(response, "status_code", None) == 429:
                self._sleep_after_rate_limit(response)
                response = self.session.request(
                    method,
                    url,
                    allow_redirects=True,
                    timeout=self.timeout,
                    headers=self.headers,
                )
            return response
        except requests.exceptions.RequestException as exc:
            return UrlValidationResult(
                url=url,
                status="unresolved",
                status_code=None,
                reason=str(exc),
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


def extract_urls(content: str, base_url: str = DEFAULT_BASE_URL) -> List[ExtractedUrl]:
    """Extract Markdown and bare URLs from article body content."""
    prepared = _strip_frontmatter_preserve_lines(content)
    prepared = _blank_fenced_code(prepared)
    prepared = INLINE_CODE_RE.sub("", prepared)
    prepared = MARKDOWN_IMAGE_RE.sub(lambda match: " " * (match.end() - match.start()), prepared)

    markdown_links: List[ExtractedUrl] = []

    def blank_markdown_link(match: re.Match) -> str:
        anchor = match.group(1).strip()
        raw_url = _normalize_markdown_destination(match.group(2))
        normalized = _normalize_url(raw_url, base_url)
        if normalized:
            markdown_links.append(
                ExtractedUrl(
                    url=normalized,
                    line=_line_number(prepared, match.start()),
                    source="markdown",
                    anchor=anchor,
                    raw_url=raw_url,
                )
            )
        return " " * (match.end() - match.start())

    without_markdown = MARKDOWN_LINK_RE.sub(blank_markdown_link, prepared)

    bare_links = []
    for match in BARE_URL_RE.finditer(without_markdown):
        raw_url = _strip_trailing_url_punctuation(match.group(0))
        normalized = _normalize_url(raw_url, base_url)
        if normalized:
            bare_links.append(
                ExtractedUrl(
                    url=normalized,
                    line=_line_number(without_markdown, match.start()),
                    source="bare",
                    raw_url=raw_url,
                )
            )

    return markdown_links + bare_links


def validate_content_urls(
    content: str,
    validator: Optional[UrlValidator] = None,
    base_url: str = DEFAULT_BASE_URL,
) -> UrlValidationSummary:
    """Validate all URLs in a content string."""
    validator = validator or UrlValidator()
    results = []
    cache = {}

    for extracted in extract_urls(content, base_url=base_url):
        if extracted.url not in cache:
            cache[extracted.url] = validator.validate_url(
                extracted.url,
                line=extracted.line,
                anchor=extracted.anchor,
            )
        result = cache[extracted.url]
        if result.line != extracted.line or result.anchor != extracted.anchor:
            result = UrlValidationResult(
                url=result.url,
                status=result.status,
                status_code=result.status_code,
                reason=result.reason,
                line=extracted.line,
                anchor=extracted.anchor,
                final_url=result.final_url,
            )
        results.append(result)

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
            lines.append(f"  - {location}{result.url}{anchor} ({result.status}: {code})")

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


class _UrlResolutionCache:
    """Small file cache for successfully resolved URLs."""

    def __init__(self, cache_dir: Path, expire_seconds: int = RESOLUTION_CACHE_SECONDS):
        self.cache_dir = cache_dir
        self.expire_seconds = expire_seconds

    def get(self, url: str) -> Optional[UrlValidationResult]:
        path = self._path(url)
        if not path.exists():
            return None
        if time.time() - path.stat().st_mtime > self.expire_seconds:
            try:
                path.unlink()
            except OSError:
                pass
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if payload.get("status") != "resolved":
            return None
        return UrlValidationResult(
            url=payload.get("url", url),
            status="resolved",
            status_code=payload.get("status_code"),
            reason=payload.get("reason", "cached resolved URL"),
            final_url=payload.get("final_url", payload.get("url", url)),
        )

    def set(self, result: UrlValidationResult) -> None:
        if not result.passed:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "url": result.url,
            "status": result.status,
            "status_code": result.status_code,
            "reason": result.reason,
            "final_url": result.final_url or result.url,
        }
        self._path(result.url).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    def _path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key}.json"


class _NullUrlResolutionCache:
    """No-op cache used for injected test sessions unless a cache is requested."""

    def get(self, url: str) -> Optional[UrlValidationResult]:
        return None

    def set(self, result: UrlValidationResult) -> None:
        return None


def _strip_frontmatter_preserve_lines(content: str) -> str:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return content
    return "\n" * match.group(0).count("\n") + content[match.end():]


def _blank_fenced_code(content: str) -> str:
    return FENCED_CODE_RE.sub(lambda match: "\n" * match.group(0).count("\n"), content)


def _line_number(content: str, index: int) -> int:
    return content.count("\n", 0, index) + 1


def _normalize_markdown_destination(destination: str) -> str:
    cleaned = destination.strip()
    if cleaned.startswith("<") and ">" in cleaned:
        return cleaned[1:cleaned.index(">")]
    return cleaned.split()[0].strip("<>") if cleaned else ""


def _normalize_url(raw_url: str, base_url: str) -> str:
    cleaned = _strip_trailing_url_punctuation(raw_url.strip())
    if not cleaned:
        return ""

    parsed = urlparse(cleaned)
    if parsed.scheme in SKIPPED_SCHEMES or cleaned.startswith("#"):
        return ""
    if parsed.scheme in {"http", "https"}:
        return cleaned
    if cleaned.startswith("www."):
        return f"https://{cleaned}"
    if parsed.scheme:
        return ""
    return urljoin(base_url.rstrip("/") + "/", cleaned)


def _strip_trailing_url_punctuation(url: str) -> str:
    return url.rstrip(".,;:!?")


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
