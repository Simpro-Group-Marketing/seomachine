"""Page-text captures taken in the user's main Chrome window for fact pages that block bots.

Usage: python -m data_sources.modules.production.page_capture record --url URL --title TITLE
       --text-file FILE --output RECEIPT --client {claude_code,codex} [--workspace-root DIR]

The page is read with the running client's live-browser tools (see ``capture_client``). A receipt
(``simpro-chrome-page-capture/v1``) binds saved page text to its URL, capture time, client, and
SHA-256, and ``load_capture`` refuses any edit made after capture. The receipt proves the text is
unchanged since it was captured, not where it came from: ``surface`` and ``client`` are
self-declared, and no automated check can tell a faithful Chrome capture from typed text. A receipt
recorded before the client field shipped loads with client ``unrecorded``; a later one must name it. The text and the receipt must
both live under ``research/source-captures/``. A capture may stand in only for a fact page whose live
fetch was blocked (``facts.verify_quotes`` decides), and never for a gone or reachable page.
Exit codes: 0 recorded, 2 error (one line on stderr).
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
from data_sources.modules.capture_client import CLIENTS, UNRECORDED, client_error, client_required, declared_client

SCHEMA = "simpro-chrome-page-capture/v1"
SURFACE = "chrome_main_window"
_KEYS = frozenset({"schema", "url", "captured_at", "surface", "page_title", "text_path", "text_sha256"})
_OPTIONAL_KEYS = frozenset({"client"})  # absent on receipts recorded before the client field existed
_STAMP = "%Y-%m-%dT%H:%M:%SZ"
CAPTURE_DIR = "research/source-captures"
_CLOCK_SKEW = datetime.timedelta(minutes=5)


def utc_now() -> datetime.datetime:
    """The current UTC time; tests replace this to move the clock."""
    return datetime.datetime.now(datetime.timezone.utc)


@dataclass(frozen=True)
class PageCapture:
    url: str
    captured_at: str
    page_title: str
    text: str
    text_sha256: str
    path: str  # workspace-relative posix path of the receipt
    receipt_sha256: str
    client: str = UNRECORDED

    def age(self) -> datetime.timedelta:
        """Time since capture, by the module clock."""
        taken = datetime.datetime.strptime(self.captured_at, _STAMP).replace(tzinfo=datetime.timezone.utc)
        return utc_now() - taken


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


def _in_capture_dir(root: Path, path: Path, label: str) -> Path:
    try:
        path.relative_to(root / CAPTURE_DIR)
    except ValueError as error:
        raise ValueError(f"{label} must be under {CAPTURE_DIR}/: {path.relative_to(root).as_posix()}") from error
    return path


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
    *, url: str, title: str, text_file: str | Path, output: str | Path, workspace_root: str | Path, client: str
) -> Path:
    """Hash the saved page text and write its receipt atomically; returns the receipt path."""
    root = Path(workspace_root).resolve()
    client = declared_client(client)
    _require_http_url(url)
    if not isinstance(title, str) or not title.strip():
        raise ValueError("capture title must be non-empty text")
    text_path = _in_capture_dir(root, _inside(root, text_file, "text file"), "text file")
    destination = _in_capture_dir(root, _inside(root, output, "receipt"), "receipt")
    relative_text = text_path.relative_to(root).as_posix()
    resolve_artifact(relative_text, workspace_root=root)  # canonical spelling: no spaces, case aliases, or dots
    raw, text = _read_text(text_path, "text file")
    if not text.strip():
        raise ValueError(f"captured text is empty: {text_file}")
    payload = {
        "schema": SCHEMA,
        "url": url,
        "captured_at": utc_now().strftime(_STAMP),
        "surface": SURFACE,
        "client": client,
        "page_title": title.strip(),
        "text_path": relative_text,
        "text_sha256": hashlib.sha256(raw).hexdigest(),
    }
    atomic_write_json(destination, payload)
    return destination


def _receipt_errors(payload: Mapping[str, Any]) -> list[str]:
    errors = [f"missing {key}" for key in sorted(_KEYS - set(payload))]
    errors += [f"unexpected key {key}" for key in sorted(set(payload) - _KEYS - _OPTIONAL_KEYS)]
    if "client" in payload and client_error(payload["client"]):
        errors.append(client_error(payload["client"]))
    if "client" not in payload and client_required(payload.get("captured_at")):
        errors.append("missing client (a receipt made after the client field shipped must name claude_code or codex)")
    if payload.get("schema") != SCHEMA:
        errors.append(f"schema must be {SCHEMA}, found: {payload.get('schema')!r}")
    if payload.get("surface") != SURFACE:
        errors.append(f"surface must be {SURFACE}, found: {payload.get('surface')!r}")
    return errors


def _stamp_error(value: Any) -> str | None:
    try:
        taken = datetime.datetime.strptime(value if isinstance(value, str) else "", _STAMP)
    except ValueError:
        return f"captured_at must be a UTC time like 2026-10-14T08:00:00Z, found: {value!r}"
    if taken.replace(tzinfo=datetime.timezone.utc) > utc_now() + _CLOCK_SKEW:
        return f"captured_at {value} is in the future"
    return None


def _field_errors(payload: Mapping[str, Any]) -> list[str]:
    problems = [_stamp_error(payload["captured_at"])]
    for field in ("page_title", "text_sha256"):
        if not (isinstance(payload[field], str) and payload[field].strip()):
            problems.append(f"{field} must be non-empty text")
    return [problem for problem in problems if problem]


def _read_receipt(root: Path, path: str | Path) -> tuple[dict[str, Any], str, bytes]:
    """Parse a receipt under the capture folder and check its shape; returns payload, label, raw bytes."""
    receipt = _in_capture_dir(root, _inside(root, path, "capture receipt"), "capture receipt")
    raw, text = _read_text(receipt, "capture receipt")
    label = receipt.relative_to(root).as_posix()
    try:
        payload = json.loads(text)
    except ValueError as error:
        raise ValueError(f"capture receipt {label} is not valid JSON: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"capture receipt {label} is not a JSON object")
    errors = _receipt_errors(payload) or _field_errors(payload)
    if errors:
        raise ValueError(f"capture receipt {label}: {'; '.join(errors)}")
    return payload, label, raw


def load_capture(path: str | Path, workspace_root: str | Path) -> PageCapture:
    """Read a receipt, re-hash its saved text, and return the capture; any inconsistency raises ValueError."""
    root = Path(workspace_root).resolve()
    payload, label, receipt_raw = _read_receipt(root, path)
    _require_http_url(payload["url"])
    try:
        text_file = _in_capture_dir(root, resolve_artifact(payload["text_path"], workspace_root=root), "text_path")
    except ValueError as error:
        raise ValueError(f"capture receipt {label} text_path is not usable: {error}") from error
    raw, text = _read_text(text_file, "captured text")
    if hashlib.sha256(raw).hexdigest() != payload["text_sha256"]:
        raise ValueError(f"capture {label} text hash does not match its receipt: the saved text was edited")
    if not text.strip():
        raise ValueError(f"capture {label} captured text is empty")
    return PageCapture(
        url=payload["url"], captured_at=payload["captured_at"], page_title=payload["page_title"],
        text=text, text_sha256=payload["text_sha256"], path=label,
        receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(), client=payload.get("client", UNRECORDED),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="page_capture", description=__doc__)
    parser.add_argument("command", choices=["record"])
    parser.add_argument("--url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--text-file", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--client", required=True, choices=sorted(CLIENTS))
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
            url=args.url, title=args.title, text_file=args.text_file, output=args.output, workspace_root=root,
            client=args.client,
        )
    except (ValueError, OSError) as error:
        print(f"page_capture: {' '.join(str(error).split())}", file=sys.stderr)
        return 2
    print(f"page_capture: recorded {receipt.relative_to(root).as_posix()}")
    return 0


__all__ = ["PageCapture", "SCHEMA", "SURFACE", "load_capture", "record_capture"]

if __name__ == "__main__":
    raise SystemExit(main())
