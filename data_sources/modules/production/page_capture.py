"""Page-text captures taken in the user's main Chrome window for fact pages that block bots.

Usage: python -m data_sources.modules.production.page_capture record --url URL --title TITLE
       --text-file FILE --output RECEIPT [--workspace-root DIR]

A receipt (``simpro-chrome-page-capture/v1``) binds the exact page text Claude saved from Chrome to
its URL, capture time, and SHA-256. ``load_capture`` re-hashes the saved text and refuses any edit,
so a capture can only stand in for a page that the normal fetch could not read. The text itself is
never summarized or retyped. Exit codes: 0 recorded, 2 error (one line on stderr).
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from data_sources.modules.blog_assembly_contract import atomic_write_json, resolve_artifact

SCHEMA = "simpro-chrome-page-capture/v1"
SURFACE = "chrome_main_window"
_KEYS = frozenset({"schema", "url", "captured_at", "surface", "page_title", "text_path", "text_sha256"})
_STAMP = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(frozen=True)
class PageCapture:
    url: str
    captured_at: str
    page_title: str
    text: str
    text_sha256: str
    path: str  # workspace-relative posix path of the receipt
    receipt_sha256: str


def _inside(root: Path, path: str | Path, label: str) -> Path:
    """Resolve a path (relative paths start at the workspace root) and require it to stay inside."""
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{label} is outside the workspace: {path}") from error
    return candidate


def _require_http_url(url: Any) -> str:
    parsed = urlparse(url) if isinstance(url, str) else None
    if parsed is None or parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"capture url must be an absolute http(s) URL, found: {url!r}")
    return url


def _read_text(path: Path, label: str) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
        return raw, raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"{label} cannot be read as UTF-8 text: {error}") from error


def record_capture(
    *, url: str, title: str, text_file: str | Path, output: str | Path, workspace_root: str | Path
) -> Path:
    """Hash the saved page text and write its receipt atomically; returns the receipt path."""
    root = Path(workspace_root).resolve()
    _require_http_url(url)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("capture title must be non-empty text")
    text_path = _inside(root, text_file, "text file")
    destination = _inside(root, output, "receipt")
    raw, text = _read_text(text_path, "text file")
    if not text.strip():
        raise ValueError(f"captured text is empty: {text_file}")
    payload = {
        "schema": SCHEMA,
        "url": url,
        "captured_at": datetime.datetime.now(datetime.timezone.utc).strftime(_STAMP),
        "surface": SURFACE,
        "page_title": title.strip(),
        "text_path": text_path.relative_to(root).as_posix(),
        "text_sha256": hashlib.sha256(raw).hexdigest(),
    }
    atomic_write_json(destination, payload)
    return destination


def _receipt_errors(payload: Mapping[str, Any]) -> list[str]:
    errors = [f"missing {key}" for key in sorted(_KEYS - set(payload))]
    errors += [f"unexpected key {key}" for key in sorted(set(payload) - _KEYS)]
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}, found: {payload.get('schema')!r}")
    if payload.get("surface") != SURFACE:
        errors.append(f"surface must be {SURFACE}, found: {payload.get('surface')!r}")
    return errors


def _stamp_error(value: Any) -> str | None:
    try:
        datetime.datetime.strptime(value if isinstance(value, str) else "", _STAMP)
    except ValueError:
        return f"captured_at must be a UTC time like 2026-10-14T08:00:00Z, found: {value!r}"
    return None


def load_capture(path: str | Path, workspace_root: str | Path) -> PageCapture:
    """Read a receipt, re-hash its saved text, and return the capture; any inconsistency raises ValueError."""
    root = Path(workspace_root).resolve()
    receipt = _inside(root, path, "capture receipt")
    receipt_raw, receipt_text = _read_text(receipt, "capture receipt")
    label = receipt.relative_to(root).as_posix()
    try:
        payload = json.loads(receipt_text)
    except ValueError as error:
        raise ValueError(f"capture receipt {label} is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"capture receipt {label} is not a JSON object")
    errors = _receipt_errors(payload)
    if errors:
        raise ValueError(f"capture receipt {label}: {'; '.join(errors)}")
    problems = [_stamp_error(payload["captured_at"])]
    for field in ("page_title", "text_sha256"):
        if not (isinstance(payload[field], str) and payload[field].strip()):
            problems.append(f"{field} must be non-empty text")
    if any(problems):
        raise ValueError(f"capture receipt {label}: {'; '.join(p for p in problems if p)}")
    _require_http_url(payload["url"])
    try:
        text_file = resolve_artifact(payload["text_path"], workspace_root=root)
    except ValueError as error:
        raise ValueError(f"capture receipt {label} text_path is not usable: {error}") from error
    raw, text = _read_text(text_file, "captured text")
    if hashlib.sha256(raw).hexdigest() != payload["text_sha256"]:
        raise ValueError(f"capture {label} text hash does not match its receipt: the saved text was edited")
    return PageCapture(
        url=payload["url"], captured_at=payload["captured_at"], page_title=payload["page_title"],
        text=text, text_sha256=payload["text_sha256"], path=label,
        receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="page_capture", description=__doc__)
    parser.add_argument("command", choices=["record"])
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--workspace-root", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
    except SystemExit as exit_request:
        return int(exit_request.code or 0)
    root = (args.workspace_root or Path.cwd()).resolve()
    try:
        receipt = record_capture(
            url=args.url, title=args.title, text_file=args.text_file, output=args.output, workspace_root=root
        )
    except (ValueError, OSError) as error:
        print(f"page_capture: {' '.join(str(error).split())}", file=sys.stderr)
        return 2
    print(f"page_capture: recorded {receipt.relative_to(root).as_posix()}")
    return 0


__all__ = ["PageCapture", "SCHEMA", "SURFACE", "load_capture", "record_capture"]

if __name__ == "__main__":
    raise SystemExit(main())
