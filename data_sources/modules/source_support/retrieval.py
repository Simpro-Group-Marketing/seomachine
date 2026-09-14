"""Public-source retrieval and visible-text normalization."""

from __future__ import annotations

import hashlib
import socket
from typing import Any, Callable, Dict, Optional, Sequence

from .common import (
    DEFAULT_USER_AGENT,
    SOURCE_VISIBLE_TEXT_POLICY,
    PublicHttpTransport,
    canonical_request_identity,
)
from .text_matching import _extract_visible_text


def fetch_source_text(
    url: str,
    *,
    resolver=socket.getaddrinfo,
    transport=None,
) -> str:
    """Fetch and normalize visible source text from an HTML URL."""
    if transport is None:
        with PublicHttpTransport(resolver=resolver) as owned_transport:
            return fetch_source_text(url, resolver=resolver, transport=owned_transport)
    response = transport.request(
        "GET",
        url,
        headers={"User-Agent": DEFAULT_USER_AGENT},
        policy=SOURCE_VISIBLE_TEXT_POLICY,
    )
    response.raise_for_status()
    return _extract_visible_text(response.text)


def fetch_source_text_many(
    urls: Sequence[str],
    *,
    transport: Any,
    normalize: Optional[Callable[[str, Callable[[], str]], str]] = None,
) -> Dict[str, Any]:
    """Fetch independent HTML sources concurrently and normalize each once."""
    ordered = list(dict.fromkeys(urls))
    if not ordered:
        return {}
    try:
        responses = transport.request_many(
            "GET",
            ordered,
            headers={"User-Agent": DEFAULT_USER_AGENT},
            policy=SOURCE_VISIBLE_TEXT_POLICY,
        )
    except Exception as error:
        return {url: error for url in ordered}
    results: Dict[str, Any] = {}
    for url, response in zip(ordered, responses, strict=True):
        try:
            response.raise_for_status()
            body_digest = hashlib.sha256(response.content).hexdigest()
            request_identity = canonical_request_identity(
                "GET",
                url,
                headers={"User-Agent": DEFAULT_USER_AGENT},
                policy=SOURCE_VISIBLE_TEXT_POLICY,
            )
            key = f"{request_identity}:{body_digest}"

            def loader(response: Any = response) -> str:
                return _extract_visible_text(response.text)

            results[url] = normalize(key, loader) if normalize is not None else loader()
        except Exception as error:
            results[url] = error
        finally:
            response.close()
            response._content = b""
    return results


__all__ = ["fetch_source_text", "fetch_source_text_many"]
