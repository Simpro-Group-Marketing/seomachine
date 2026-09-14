"""Validated immutable response snapshots for the public HTTP transport."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping

import requests

from .policies import HttpRequestPolicy


CACHE_SCHEMA = "simpro-public-http-cache/v2"


@dataclass(frozen=True, slots=True)
class ResponseSnapshot:
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
    ) -> "ResponseSnapshot":
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
    ) -> "ResponseSnapshot" | None:
        expected = {
            "schema",
            "policy_digest",
            "status_code",
            "body",
            "body_digest",
            "byte_count",
            "content_type",
            "final_url",
        }
        if set(value) != expected or value.get("schema") != CACHE_SCHEMA:
            return None
        status = value.get("status_code")
        body = value.get("body")
        if not _valid_cached_fields(value, status=status, body=body, policy_digest=policy_digest):
            return None
        snapshot = cls(status, body, str(value["content_type"]), str(value["final_url"]))
        try:
            snapshot.validate(policy)
        except ValueError:
            return None
        return snapshot


def _valid_cached_fields(
    value: Mapping[str, Any],
    *,
    status: Any,
    body: Any,
    policy_digest: str,
) -> bool:
    return bool(
        not isinstance(status, bool)
        and isinstance(status, int)
        and isinstance(body, bytes)
        and isinstance(value.get("content_type"), str)
        and isinstance(value.get("final_url"), str)
        and value.get("policy_digest") == policy_digest
        and value.get("byte_count") == len(body)
        and value.get("body_digest") == hashlib.sha256(body).hexdigest()
    )
